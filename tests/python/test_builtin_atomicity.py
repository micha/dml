"""Representative NEW node author/child trace/R batch rollback with native absence."""

from dataclasses import dataclass
import errno

import daggerml as d
from daggerml import builtin as b, transfer
import pytest

from test_builtin import state, construction
from test_builtin_workflow import success, request, funcs, story, app, workflow_state
from test_exchange import typed_oracle
from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts


@dataclass(frozen=True)
class Response:
    commit: d.ObjectId
    dag: d.ObjectId


def author(path, base, state, *, map_size=0):
    with d.Repository(path, map_size=map_size) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            sample = construction(rec, state)
            full = rec.arguments({"sample": sample})
            ledger = rec.trace()
            entries = dict(tx.get_tree(tx.get_commit(base).tree))
            entries.update(authored=rec.dag(full), ledger=ledger)
            commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
            tx.create_ref("authored", commit)
            response = Response(commit, rec.dag(full))
    return response


@pytest.mark.parametrize("fault", ["late-ref", "response", "commit", "map-full"])
def test_actual_NEW_node_args_operation_trace_batch_prediction_absent_BEFORE_AFTER(state, tmp_path, monkeypatch, core, fault):
    path, base, _, _, bindings, _ = state
    old = typed_oracle(path, (base,))
    prediction = tmp_path / "prediction"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(prediction, transfer.export_commit(path, commit=base))
    predicted = author(prediction, base, state)
    new = {key: raw for key, raw in typed_oracle(prediction, (predicted.commit,)).items() if key not in old}
    assert {"datum", "node", "dag", "tree", "commit"} <= {kind for kind, oid in new}
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    before = (path / "data.mdb").read_bytes()
    original = d.Transaction.create_ref
    def late(tx, name, target):
        if name == "authored":
            if fault == "late-ref":
                raise MemoryError("late explicit ref")
            if fault == "commit":
                core.native_fault(15, 1, errno.EIO)
            if fault == "map-full":
                tx.put_datum(b"x" * (2 * 1024 * 1024))
        return original(tx, name, target)
    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        monkeypatch.setattr(__import__(__name__), "Response", lambda *a: (_ for _ in ()).throw(MemoryError("precommit response")))
    try:
        with track_typed_puts(path, old) as puts:
            with pytest.raises((MemoryError, d.DmlError)):
                author(path, base, state, map_size=1048576 if fault == "map-full" else 0)
    finally:
        core.native_fault(0, 0, 0)
    assert puts == new
    if fault == "map-full":
        with d.Repository(path):
            pass
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
        with pytest.raises(d.NotFoundError):
            tx.get_ref("authored")


def test_actual_child_all_sources_arguments_ops_trace_return_publication_ONE_batch_late_abort(success, monkeypatch, tmp_path):
    path = success[0]
    changed = story.construct(path, success[-1].commit, success[2], success[3]["C"], "C")
    fresh = request(success, commit=d.ObjectId.from_hex(changed["commit"]), inputs_name="C-inputs", override="v2", control="fresh", reuse_ref=None)
    from types import SimpleNamespace
    context = SimpleNamespace(repository_path=path, pre_dispatch=fresh.recorded.commit,
                              inputs=fresh.recorded.inputs, request=fresh.recorded.request)
    captured = {}
    def put_host_snapshot(tx, ctx, result):
        entries = dict(tx.get_tree(tx.get_commit(ctx.pre_dispatch).tree))
        entries["test-new-result"] = result
        return tx.put_commit(tx.put_tree(entries), parents=(ctx.pre_dispatch,))
    old = typed_oracle(path, (context.pre_dispatch,))
    prediction = tmp_path / "prediction-child"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(prediction, transfer.export_commit(path, commit=context.pre_dispatch))
    predicted_context = SimpleNamespace(**{**context.__dict__, "repository_path": prediction})
    with monkeypatch.context() as guard:
        guard.setattr(local_module(), "publish_result", put_host_snapshot)
        predicted = b.publish_callable(predicted_context, funcs.sum_pair, map_binding=success[2]["get-v2"], list_binding=success[2]["index-v1"])
    expected_new = {key: raw for key, raw in typed_oracle(prediction, (predicted,)).items() if key not in old}
    roles = []
    with d.Repository(prediction) as repo, repo.read() as tx:
        for kind, oid in expected_new:
            if kind == "dag":
                roles.append(b.scalar(tx, tx.get_dag(oid).bindings["role"], "string"))
    assert roles.count(b.ARGUMENTS_ROLE) == roles.count(b.OPERATION_ROLE) == 4
    assert b.TRACE_ROLE in roles and b.RETURN_ROLE in roles
    with d.Repository(path) as repo, repo.read() as tx:
        for key in expected_new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    def fail(tx, ctx, result):
        captured["result"] = result
        fields = tx.get_dag(result).bindings
        assert b.scalar(tx, fields["role"], "string") == b.RETURN_ROLE
        trace = b.link(tx, fields["trace"])
        inspector = b.Inspector(tx, commit=context.pre_dispatch)
        # Actual new returned/trace are present INSIDE this write; inspect explicitly
        # after registering their owning retained carrier to a test-owned commit.
        entries = dict(tx.get_tree(tx.get_commit(ctx.pre_dispatch).tree))
        entries["test-new-result"] = result
        current = tx.put_commit(tx.put_tree(entries), parents=(ctx.pre_dispatch,))
        actual = b.Inspector(tx, commit=current)
        assert len(actual.trace(trace, request=ctx.request, inputs=ctx.inputs)) == 4
        assert actual.node(result).value == d.Datum.i64(43)
        captured["new"] = {key: raw for key, raw in _tx_oracle(tx, current).items() if key not in old}
        raise MemoryError("late child result publication")
    before = (path / "data.mdb").read_bytes()
    monkeypatch.setattr(local_module(), "publish_result", fail)
    with pytest.raises(MemoryError, match="late child"):
        b.publish_callable(context, funcs.sum_pair, map_binding=success[2]["get-v2"], list_binding=success[2]["index-v1"])
    assert captured["new"] == expected_new
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        for key in captured["new"]:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)


def local_module():
    from daggerml import local
    return local


def _tx_oracle(tx, commit):
    # Independent typed all-parent/composite traversal inside an authoring batch.
    pending, result = [("commit", commit)], {}
    while pending:
        kind, oid = pending.pop()
        if (kind, oid) in result:
            continue
        result[kind, oid] = tx.get_record(kind, oid)
        if kind == "commit":
            got = tx.get_commit(oid)
            pending.extend(("commit", p) for p in got.parents)
            pending.append(("tree", got.tree))
        elif kind == "tree":
            pending.extend(("dag", v) for v in tx.get_tree(oid).values())
        elif kind == "dag":
            got = tx.get_dag(oid)
            pending.extend(("node", v) for v in (got.root, *got.bindings.values()))
        elif kind == "node":
            got = tx.get_node(oid)
            pending.append(("datum", got.datum) if isinstance(got, d.LiteralNode) else ("dag", got.dag))
        else:
            got = tx.get_datum(oid)
            if got.kind in ("list", "set"):
                pending.extend(("datum", v) for v in got.value)
            elif got.kind == "map":
                pending.extend(("datum", v) for p in got.value for v in p)
    return result
