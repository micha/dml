"""Prediction proves genuinely ABSENT closure B/C rows, not deduplicated rollback."""

import errno

import daggerml as d
from daggerml import builtin as b, transfer
import pytest

from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_exchange import typed_oracle
from test_closure_calls import app, create, initial, request, successful


@pytest.mark.parametrize("fault", ["late-ref", "response", "commit", "map-full"])
def test_ABSENT_predicted_B_C_new_rows_real_native_faults(initial, tmp_path, monkeypatch, core, fault):
    path, base, first, commit = initial
    old = typed_oracle(path, (commit,))
    prediction = tmp_path / "prediction"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(prediction, transfer.export_commit(path, commit=commit))
    predicted = create(prediction, commit, "B", "v2", "B")
    new = {k: raw for k, raw in typed_oracle(prediction, (predicted.commit,)).items() if k not in old}
    assert {"datum", "node", "dag", "tree", "commit"} <= {kind for kind, oid in new}
    assert ("dag", predicted.binding) in new and ("dag", predicted.dag) in new
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    before = (path / "data.mdb").read_bytes()
    original = d.Transaction.create_ref
    def late(tx, name, target):
        if name == "created-B":
            if fault == "late-ref":
                raise MemoryError("late explicit ref")
            if fault == "commit":
                core.native_fault(15, 1, errno.EIO)
            if fault == "map-full":
                tx.put_datum(b"x" * (2 * 1024 * 1024))
        return original(tx, name, target)
    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        monkeypatch.setattr(app, "Created", lambda *a: (_ for _ in ()).throw(MemoryError("precommit response")))
    try:
        with track_typed_puts(path, old) as puts:
            with pytest.raises((MemoryError, d.DmlError)):
                create(path, commit, "B", "v2", "B", map_size=1048576 if fault == "map-full" else 0)
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
            tx.get_ref("created-B")


def test_author_postcommit_ack_loss_complete_B_C_no_automatic_retry(initial, monkeypatch):
    path, base, first, commit = initial
    original = d.Transaction.commit
    def lose(tx):
        try:
            tx.get_ref("created-B")
            batch = True
        except d.NotFoundError:
            batch = False
        original(tx)
        if batch:
            raise RuntimeError("postcommit acknowledgement loss")
    monkeypatch.setattr(d.Transaction, "commit", lose)
    with pytest.raises(RuntimeError, match="acknowledgement"):
        create(path, commit, "B", "v2", "B")
    with d.Repository(path) as repo, repo.read() as tx:
        committed = tx.get_ref("created-B")
        closure = app.inspect_closure(tx, committed, app.tree(tx, committed)["closure-B"])
        assert app.tree(tx, committed)["binding-B"] == closure.binding
        assert tx.get_commit(committed).parents == (commit,)


def test_W_late_failure_leaves_own_pending_Q_not_whole_driver_rollback(successful, monkeypatch):
    path, base, first, q, selected = successful
    original = d.Transaction.create_ref
    publish = app.publish_reuse
    captured = {}
    def remember(path, recorded, selected, ref):
        captured.update(qid=recorded.request_id, commit=recorded.commit, request=recorded.request,
                        before=(path / "data.mdb").read_bytes())
        return publish(path, recorded, selected, ref)
    def late(tx, name, target):
        if name == "reuse-2":
            captured["W"] = app.tree(tx, target)["reuse-" + captured["qid"]]
            fields = tx.get_dag(captured["W"]).bindings
            assert b.link(tx, fields["attempt"]) == selected.attempt
            raise MemoryError("late W ref")
        return original(tx, name, target)
    monkeypatch.setattr(app, "publish_reuse", remember)
    monkeypatch.setattr(d.Transaction, "create_ref", late)
    with pytest.raises(MemoryError, match="late W"):
        request(path, selected.commit, 2, control="require-selected", hit=True)
    assert_file_unchanged(path / "data.mdb", captured["before"])
    got = app.inspect_request(path, commit=captured["commit"], request=captured["request"], decision_name="decision-2")
    assert got.action == "reuse-selected"
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("submission-2") == tx.get_ref("request-" + captured["qid"]) == captured["commit"]
        with pytest.raises(d.NotFoundError):
            tx.get_ref("reuse-2")
        with pytest.raises(d.NotFoundError):
            tx.get_dag(captured["W"])
