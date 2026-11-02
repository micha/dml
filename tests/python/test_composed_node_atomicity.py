"""Meaningful ABSENT-row composition batch and separate pending-Q/W failure gates."""

import errno

import daggerml as d
from daggerml import builtin as b, transfer
import pytest

from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_exchange import typed_oracle
from test_composed_node_calls import app, upstream, initial, downstream, request


def compose(path, basis, *, map_size=0):
    return app.compose_double(path, commit=basis, producer_slot="producer-1", inputs_name="new-inputs",
                              composition_name="new-C", ref="composed", map_size=map_size)


@pytest.mark.parametrize("fault", ["late-ref", "response", "commit", "map-full"])
def test_NEW_input_C_batch_prediction_native_absence_BEFORE_AFTER(upstream, tmp_path, monkeypatch, core, fault):
    path, base, q, selected = upstream
    basis = selected.commit
    old = typed_oracle(path, (basis,))
    prediction = tmp_path / "prediction"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(prediction, transfer.export_commit(path, commit=basis))
    predicted = compose(prediction, basis)
    new = {k: raw for k, raw in typed_oracle(prediction, (predicted.commit,)).items() if k not in old}
    assert {"datum", "node", "dag", "tree", "commit"} <= {kind for kind, oid in new}
    assert ("dag", predicted.inputs.dag) in new and ("dag", predicted.dag) in new
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    before = (path / "data.mdb").read_bytes()
    create = d.Transaction.create_ref
    def late(tx, name, target):
        if name == "composed":
            if fault == "late-ref":
                raise MemoryError("late explicit ref")
            if fault == "commit":
                core.native_fault(15, 1, errno.EIO)
            if fault == "map-full":
                tx.put_datum(b"x" * (2 * 1024 * 1024))
        return create(tx, name, target)
    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        monkeypatch.setattr(app, "Composition", lambda *a: (_ for _ in ()).throw(MemoryError("precommit response")))
    try:
        with track_typed_puts(path, old) as puts:
            with pytest.raises((MemoryError, d.DmlError)):
                compose(path, basis, map_size=1048576 if fault == "map-full" else 0)
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
            tx.get_ref("composed")


def test_author_only_postcommit_ack_loss_keeps_complete_input_C(upstream, monkeypatch):
    path, base, q, selected = upstream
    original = d.Transaction.commit
    def lose_ack(tx):
        try:
            tx.get_ref("composed")
            target_batch = True
        except d.NotFoundError:
            target_batch = False
        original(tx)
        if target_batch:
            raise RuntimeError("postcommit acknowledgement loss")
    monkeypatch.setattr(d.Transaction, "commit", lose_ack)
    with pytest.raises(RuntimeError, match="acknowledgement"):
        compose(path, selected.commit)
    with d.Repository(path) as repo, repo.read() as tx:
        committed = tx.get_ref("composed")
    assert app.inspect_composition(path, commit=committed, inputs_name="new-inputs", composition_name="new-C").producer.selected.result == selected.result


def test_W_late_failure_preserves_legitimate_pending_Q_not_whole_operation_rollback(downstream, monkeypatch):
    path, base, q1, s1, c2, q2, s2 = downstream
    c4 = app.compose_double(path, commit=s2.commit, producer_slot="producer-1", inputs_name="inputs-4",
                            composition_name="composition-4", ref="composed-4")
    created = d.Transaction.create_ref
    captured = {}
    def late(tx, name, target):
        if name == "satisfaction-4":
            fields = tx.get_dag(app.tree(tx, target)["reuse-" + captured["qid"]]).bindings
            captured["W"] = app.tree(tx, target)["reuse-" + captured["qid"]]
            assert b.link(tx, fields["attempt"]) == s2.attempt
            raise MemoryError("late W ref")
        return created(tx, name, target)
    original = app._publish_reuse
    def remember(path, recorded, selected, ref):
        captured.update(qid=recorded.request_id, commit=recorded.commit, request=recorded.request,
                        bytes=(path / "data.mdb").read_bytes())
        return original(path, recorded, selected, ref)
    monkeypatch.setattr(app, "_publish_reuse", remember)
    monkeypatch.setattr(d.Transaction, "create_ref", late)
    with pytest.raises(MemoryError, match="late W"):
        request(path, c4.commit, app.DOUBLE, 4, hit=True)
    assert_file_unchanged(path / "data.mdb", captured["bytes"])
    decision = app.inspect_request(path, commit=captured["commit"], request=captured["request"], decision_name="decision-4")
    assert decision.action == "reuse-selected"
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("submission-4") == captured["commit"]
        assert tx.get_ref("request-" + captured["qid"]) == captured["commit"]
        with pytest.raises(d.NotFoundError):
            tx.get_ref("satisfaction-4")
        with pytest.raises(d.NotFoundError):
            tx.get_dag(captured["W"])
