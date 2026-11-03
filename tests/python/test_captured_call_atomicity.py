"""Predicted genuinely ABSENT new native rows, not deduplicated rollback claims."""

import errno
from types import SimpleNamespace

import daggerml as d
from daggerml import transfer
import pytest

from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_exchange import typed_oracle
from test_captured_calls import app, bridge, initial


@pytest.mark.parametrize("fault", ["late-ref", "response", "commit", "map-full"])
def test_new_outer_D_Q_two_refs_real_native_rollback(initial, tmp_path, monkeypatch, core, fault):
    path, commit = initial
    monkeypatch.setattr(app.uuid, "uuid4", lambda: SimpleNamespace(hex="1" * 32))
    old = typed_oracle(path, (commit,))
    prediction = tmp_path / "prediction"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(prediction, transfer.export_commit(path, commit=commit))
    predicted = app.record_request(prediction, commit=commit, ref="outer")
    new = {k: raw for k, raw in typed_oracle(prediction, (predicted.commit,)).items() if k not in old}
    assert {"datum", "node", "dag", "tree", "commit"} <= {kind for kind, oid in new}
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    before = (path / "data.mdb").read_bytes()
    original = d.Transaction.create_ref
    def late(tx, name, target):
        if name == "outer":
            if fault == "late-ref":
                raise MemoryError("late explicit ref")
            if fault == "commit":
                core.native_fault(15, 1, errno.EIO)
            if fault == "map-full":
                tx.put_datum(b"x" * (128 * 1024 * 1024))
        return original(tx, name, target)
    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        monkeypatch.setattr(app, "Request", lambda *a: (_ for _ in ()).throw(MemoryError("precommit response")))
    try:
        with track_typed_puts(path, old) as puts:
            with pytest.raises((MemoryError, d.DmlError)):
                app.record_request(path, commit=commit, ref="outer")
    finally:
        core.native_fault(0, 0, 0)
    if fault == "map-full":
        # Fault rows precede genuinely new oversized allocation under the CURRENT map.
        assert new.items() <= puts.items()
    else:
        assert puts == new
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
        for ref in ("outer", "outer-decision", "outer-request-cq-" + "1" * 32):
            with pytest.raises(d.NotFoundError):
                tx.get_ref(ref)


def test_postcommit_ack_loss_retains_complete_Q_not_an_automatic_retry(initial, monkeypatch):
    path, commit = initial
    original = d.Transaction.commit
    def lose(tx):
        try:
            tx.get_ref("outer")
            batch = True
        except d.NotFoundError:
            batch = False
        original(tx)
        if batch:
            raise RuntimeError("postcommit acknowledgment loss")
    monkeypatch.setattr(d.Transaction, "commit", lose)
    with pytest.raises(RuntimeError, match="acknowledgment"):
        app.record_request(path, commit=commit, ref="outer")
    with d.Repository(path) as repo, repo.read() as tx:
        cq = tx.get_ref("outer")
        old = app.tree(tx, tx.get_commit(cq).parents[0])
        current = app.tree(tx, cq)
        added = set(current) - set(old)
        assert len(added) == 1
        q = current[added.pop()]
    assert app.inspect_request(path, commit=cq, request=q).action == "execute-fresh"


@pytest.mark.parametrize("fault", ["late-head", "commit", "map-full"])
def test_new_getter_phase_native_rollback_leaves_initial_unknown(initial, tmp_path, monkeypatch, core, fault):
    path, commit = initial
    q = app.record_request(path, commit=commit, ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    before = (path / "data.mdb").read_bytes()
    old = typed_oracle(path, (session.current,))
    original = d.Transaction.update_ref
    inserted = {}
    def late(tx, name, target):
        if name == "outer-head-" + session.aid:
            inserted.update(app.tree(tx, target))
            if fault == "late-head":
                raise MemoryError("late head")
            if fault == "commit":
                core.native_fault(15, 1, errno.EIO)
            if fault == "map-full":
                tx.put_datum(b"y" * (128 * 1024 * 1024))
        return original(tx, name, target)
    monkeypatch.setattr(d.Transaction, "update_ref", late)
    try:
        with track_typed_puts(path, old) as puts:
            with pytest.raises((MemoryError, d.DmlError)):
                session.map_get(session.input, "a")
    finally:
        core.native_fault(0, 0, 0)
    assert puts and {"dag", "tree", "commit"} <= {kind for kind, oid in puts}
    assert session.poisoned and session.unknown and not session.getters
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        for key in puts:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
        assert tx.get_ref("outer-head-" + session.aid) == session.current
    with pytest.raises(RuntimeError, match="UNKNOWN"):
        session.fail(RuntimeError("native fault"))
