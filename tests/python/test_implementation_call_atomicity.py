"""Genuinely NEW native rows/ref batches and incomplete outer UNKNOWN; ZERO children."""

import errno
from types import SimpleNamespace

import daggerml as d
from daggerml import transfer
import pytest

from test_binding_failures import core
from test_caller_requests import track_typed_puts
from test_exchange import typed_oracle
from test_implementation_calls import initial, p, bridge


@pytest.mark.parametrize("fault", ["late-ref", "response", "native-commit"])
def test_new_D_Q_atomic_refs_abort_actual_previously_ABSENT_rows(initial, tmp_path, monkeypatch, core, fault):
    path, commit = initial
    monkeypatch.setattr(p.uuid, "uuid4", lambda: SimpleNamespace(hex="1" * 32))
    old = typed_oracle(path, (commit,))
    predicted_path = tmp_path / "prediction.dml"
    with d.Repository(predicted_path, create=True):
        pass
    transfer.import_commit(predicted_path, transfer.export_commit(path, commit=commit))
    predicted = p.record_request(predicted_path, commit=commit, ref="outer")
    new = {key: raw for key, raw in typed_oracle(predicted_path, (predicted.commit,)).items() if key not in old}
    assert {"datum", "node", "dag", "tree", "commit"} <= {kind for kind, _ in new}
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    before = (path / "data.mdb").read_bytes()
    create = d.Transaction.create_ref
    def failing_ref(tx, name, target):
        if name == "outer":
            if fault == "late-ref":
                raise MemoryError("late explicit ref")
            if fault == "native-commit":
                core.native_fault(15, 1, errno.EIO)
        return create(tx, name, target)
    monkeypatch.setattr(d.Transaction, "create_ref", failing_ref)
    if fault == "response":
        def allocation(*args):
            raise MemoryError("precommit owned response allocation")
        monkeypatch.setattr(p, "Request", allocation)
    try:
        with track_typed_puts(path, old) as inserted:
            with pytest.raises((MemoryError, d.DmlError)):
                p.record_request(path, commit=commit, ref="outer")
    finally:
        core.native_fault(0, 0, 0)
    assert inserted == new
    assert (path / "data.mdb").read_bytes() == before
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
        for ref in ("outer", "outer-decision", "outer-request-iq-" + "1" * 32):
            with pytest.raises(d.NotFoundError):
                tx.get_ref(ref)


@pytest.mark.parametrize("fault", ["late-head", "native-commit"])
def test_new_getter_preparation_phase_rollback_and_native_unknown(initial, tmp_path, monkeypatch, core, fault):
    path, commit = initial
    q = p.record_request(path, commit=commit, ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    before = (path / "data.mdb").read_bytes()
    old = typed_oracle(path, (session.current,))
    update = d.Transaction.update_ref
    def failing_head(tx, name, target):
        if name == "outer-head-" + session.aid:
            if fault == "late-head":
                raise MemoryError("late phase head update")
            core.native_fault(15, 1, errno.EIO)
        return update(tx, name, target)
    monkeypatch.setattr(d.Transaction, "update_ref", failing_head)
    try:
        with track_typed_puts(path, old) as inserted:
            with pytest.raises((MemoryError, d.DmlError)):
                with session.context:
                    session.start()
                    session.nodes.map_get(session.input, "a")
    finally:
        core.native_fault(0, 0, 0)
    assert inserted and {"dag", "tree", "commit"} <= {kind for kind, _ in inserted}
    assert session.poisoned and session.unknown and not session.getters
    assert (path / "data.mdb").read_bytes() == before
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("outer-head-" + session.aid) == session.current
        assert "status" not in tx.get_dag(session.initial).bindings
        for key in inserted:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    with pytest.raises(RuntimeError, match="UNKNOWN"):
        session.fail(RuntimeError("native fault"))


def test_postcommit_ack_loss_retains_own_Q_not_failed_or_automatic_retry(initial, monkeypatch):
    path, commit = initial
    commit_tx = d.Transaction.commit
    def lose(tx):
        try:
            tx.get_ref("outer")
            ours = True
        except d.NotFoundError:
            ours = False
        commit_tx(tx)
        if ours:
            raise RuntimeError("postcommit ack loss")
    monkeypatch.setattr(d.Transaction, "commit", lose)
    with pytest.raises(RuntimeError, match="ack"):
        p.record_request(path, commit=commit, ref="outer")
    with d.Repository(path) as repo, repo.read() as tx:
        cq = tx.get_ref("outer")
        current, previous = p.tree(tx, cq), p.tree(tx, tx.get_commit(cq).parents[0])
        added = set(current) - set(previous)
        assert len(added) == 1
        q = current[added.pop()]
    assert p.inspect_request(path, commit=cq, request=q).action == "execute-fresh"
