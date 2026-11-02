"""Meaningful remaining normal-result/ledger/bridge/public-response negatives."""

from dataclasses import replace

import daggerml as d
from daggerml import builtin as b
import pytest

from test_builtin import state, publish
from test_builtin_profiles import recorded, forged
from test_builtin_workflow import state as workflow_state, success, request, reading, app, funcs, story
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged


def test_NATIVE_17argument_rows_and_trace_positions_reject_not_contentcount(recorded):
    path, commit, op, full, ledger = recorded
    with d.Repository(path) as repo, repo.write() as tx:
        args = b.link(tx, tx.get_dag(op).bindings["arguments"])
        rows = b.link(tx, tx.get_dag(args).bindings["entries"])
        row = tx.get_dag(rows).bindings["arg-00"]
        too_many = b.record(tx, b.ENTRIES_ROLE, nodes={"arg-%02d" % i: row for i in range(17)})
        bad_args = clone(tx, args, fields={"entries": tx.put_subdag(too_many)})
        bad_trace = b.record(tx, b.TRACE_ROLE, links={"call-%02d" % i: op for i in range(17)})
        entries = dict(tx.get_tree(tx.get_commit(commit).tree))
        entries.update(bad_args=bad_args, bad_trace=bad_trace)
        basis = tx.put_commit(tx.put_tree(entries), parents=(commit,))
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(b.BuiltinError, match="arguments exceed16"):
            b.Inspector(tx, commit=basis).arguments(bad_args)
        with pytest.raises(b.BuiltinError, match="positions exceed16"):
            b.Inspector(tx, commit=basis).trace(bad_trace)


@pytest.mark.parametrize("fault", ["return-value", "trace-owner", "actualQ"])
def test_explicit_normal_return_node_value_trace_owner_and_actualQ_native_controls(success, fault):
    path, base, bindings, lists, a, q, selected = success
    with d.Repository(path) as repo, repo.write() as tx:
        result = selected.result
        fields = tx.get_dag(result).bindings
        trace = b.link(tx, fields["trace"])
        bad_request = selected.inputs
        if fault == "return-value":
            wrong = b.literal(tx, 999)
            bad = clone(tx, result, fields={"value": wrong}, root=wrong)
        elif fault == "actualQ":
            original = tx.get_dag(selected.request)
            bad_request = clone(tx, selected.request, fields={"role": b.literal(tx, "not Q")})
            bad_trace = clone(tx, trace, fields={"request": tx.put_subdag(bad_request)})
            bad = clone(tx, result, fields={"request": tx.put_subdag(bad_request), "trace": tx.put_subdag(bad_trace)})
        else:
            bad = clone(tx, result, fields={"request": tx.put_subdag(bad_request)})
        entries = app.tree(tx, selected.commit)
        entries["bad-return"] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(selected.commit,))
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(b.BuiltinError, match="returned node/value" if fault == "return-value" else "owning Q" if fault == "trace-owner" else "actual Q"):
            b.Inspector(tx, commit=basis).node(bad)


def test_putchoice_default_name_capture_source_inspection_and_logical_I64_error(workflow_state):
    path, base, bindings, lists, a = workflow_state
    assert app.capture(bindings["get-v1"], bindings["index-v1"])
    with d.Repository(path) as repo, repo.write() as tx:
        got = app.inspect_choice(tx, app.tree(tx, base)["get-choice"])
        with pytest.raises(ValueError, match="label"):
            app.put_choice(tx, map_v1=got.map_v1, map_v2=got.map_v2, normal_v1=got.normal_v1,
                            normal_v2=got.normal_v2, list_v1=got.list_v1, logical_source=got.logical_source, default="unknown")
    assert app.inspect_node(path, commit=d.ObjectId.from_hex(a["commit"]), dag=d.ObjectId.from_hex(a["inputs"])).value.kind == "map"
    class Node:
        value = d.Datum.f64(13.0)
    class Ops:
        def map_get(self, *args):
            return Node()
        def list_get(self, *args):
            return Node()
    with pytest.raises(ValueError, match="I64"):
        funcs.sum_pair(Node(), Ops())


@pytest.mark.parametrize("fault", ["named-binding", "public-prepared", "S-intent", "S-owner", "own-Q-response", "reservation", "missing-reuse-ref", "present-name"])
def test_public_boundary_responses_not_authority_BEFORE_W(success, monkeypatch, fault):
    path = success[0]
    if fault == "named-binding":
        with d.Repository(path) as repo, repo.write() as tx:
            entries = app.tree(tx, success[-1].commit)
            entries["sum-v1"] = entries["sum-v2"]
            basis = tx.put_commit(tx.put_tree(entries), parents=(success[-1].commit,))
        with pytest.raises(ValueError, match="named normal"):
            request(success, commit=basis)
        return
    if fault in ("S-intent", "S-owner"):
        real = app.selection.inspect
        def substitute(*args, **kwargs):
            got = real(*args, **kwargs)
            return replace(got, **({"intent_uri": "urn:other"} if fault == "S-intent" else {"request": success[-1].inputs}))
        monkeypatch.setattr(app.selection, "inspect", substitute)
    elif fault == "public-prepared":
        real = app._prepare
        monkeypatch.setattr(app, "_prepare", lambda *a, **k: replace(real(*a, **k), inputs=success[-1].result))
    elif fault in ("own-Q-response", "reservation"):
        real = app.ex.record_exchange_request
        def substitute(*args, **kwargs):
            got = real(*args, **kwargs)
            if fault == "own-Q-response":
                return replace(got, intent_uri="urn:other")
            with d.Repository(path) as repo, repo.write() as tx:
                tx.update_ref("request-" + got.request_id, success[-1].commit)
            return got
        monkeypatch.setattr(app.ex, "record_exchange_request", substitute)
    elif fault == "present-name":
        existing = request(success, control="fresh", reuse_ref=None)
        with pytest.raises(ValueError, match="absent"):
            request(success, commit=existing.recorded.commit, decision_name=existing.decision.name)
        return
    monkeypatch.setattr(app, "_publish_reuse", lambda *a: pytest.fail("bad claims must reject BEFORE W"))
    with pytest.raises(ValueError):
        request(success, **({"reuse_ref": None} if fault == "missing-reuse-ref" else {}))
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("new-w")


@pytest.mark.parametrize("fault", ["decision-parent", "decision-tree", "Q-parent", "Q-prepared", "W-parent", "fresh-W"])
def test_native_spine_only_intended_tree_deltas_and_public_Q(success, monkeypatch, fault):
    path = success[0]
    got = request(success, **({"control": "fresh", "reuse_ref": None} if fault == "fresh-W" else {}))
    with d.Repository(path) as repo, repo.write() as tx:
        target = got.decision.commit if fault.startswith("decision") else got.recorded.commit if fault.startswith("Q") else got.reused.commit if got.reused is not None else got.recorded.commit
        entries = app.tree(tx, target)
        parents = tx.get_commit(target).parents
        if fault.endswith("parent"):
            parents = ()
        if fault == "decision-tree":
            entries["extra"] = got.decision.dag
        bad = tx.put_commit(tx.put_tree(entries), parents=parents)
    if fault == "Q-prepared":
        real = app._prepare
        def wrong_own_Q(*args, **kwargs):
            prepared = real(*args, **kwargs)
            return replace(prepared, binding=success[-1].inputs) if len(args) > 4 and args[4] is not None else prepared
        monkeypatch.setattr(app, "_prepare", wrong_own_Q)
    with pytest.raises(ValueError):
        if fault.startswith("decision"):
            app.inspect_decision(path, commit=bad, decision_name=got.decision.name)
        else:
            app.inspect_request(path, commit=bad if fault.startswith("Q") else got.recorded.commit,
                                 request=got.recorded.request, decision_name=got.decision.name,
                                 satisfaction_commit=bad if fault.startswith("W") or fault == "fresh-W" else None)


def test_coherently_captured_wrong_list_binding_rejects_UNSELECTED_and_SELECTED(workflow_state):
    path, base, bindings, lists, a = workflow_state
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        choice = app.inspect_choice(tx, entries["get-choice"])
        wrong_list = bindings["get-v1"]
        normals = {version: app.local.put_local_binding(tx, source=app.capture(bindings["get-" + version], wrong_list,
                    logical_source=choice.logical_source), interpreter=__import__("sys").executable, timeout_ms=10000) for version in ("v1", "v2")}
        corrupt = app.put_choice(tx, map_v1=choice.map_v1, map_v2=choice.map_v2, normal_v1=normals["v1"],
                                  normal_v2=normals["v2"], list_v1=wrong_list, logical_source=choice.logical_source)
        with pytest.raises(ValueError, match="choice list binding"):
            app.inspect_choice(tx, corrupt)
