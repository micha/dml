"""Exactly THREE real public native ref movements; no ordinary HOST/OS attempt."""

import daggerml as d
from daggerml import calls as c
import pytest

from test_implementation_calls import initial, p, bridge


def test_actual_request_reservation_move_refuses_before_initial_T(initial, tmp_path):
    path, basis = initial
    q = p.record_request(path, commit=basis, ref="outer")
    ref = "outer-request-" + q.request_id
    with d.Repository(path) as repo, repo.write() as tx:
        tx.update_ref(ref, q.base)
    baseline = (path / "data.mdb").read_bytes()  # AFTER the deliberate authorized reference movement.
    with pytest.raises(ValueError, match="actual outer request reservation differs before attempt"):
        bridge.Session(path, q, tmp_path / "owned-workspace")
    assert (path / "data.mdb").read_bytes() == baseline
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref(ref) == q.base
        assert not any(name.startswith(("outer-attempt-", "outer-completion-", "attempt-a-")) for name in p.tree(tx, q.commit))
    # Workspace may exist from owned setup BEFORE the refused native initial-T batch.
    assert (tmp_path / "owned-workspace").is_dir()


def test_actual_attempt_head_move_refuses_getter_phase_and_stays_UNKNOWN(initial, tmp_path):
    path, basis = initial
    q = p.record_request(path, commit=basis, ref="outer")
    session = bridge.Session(path, q, tmp_path / "owned-workspace")
    ref = "outer-head-" + session.aid
    with d.Repository(path) as repo, repo.write() as tx:
        tx.update_ref(ref, q.commit)
    baseline = (path / "data.mdb").read_bytes()
    with pytest.raises(RuntimeError, match="expected caught outer phase uncertainty"):
        with session.context:
            session.start()
            with pytest.raises(ValueError, match="outer phase head changed"):
                session.nodes.map_get(session.input, "a")
            assert session.unknown and session.poisoned and session.context.poisoned
            assert session.index == 0 and not session.getters and not session.calls
            with pytest.raises(RuntimeError, match="UNKNOWN"):
                session.fail(bridge.SessionError("ref changed during getter"))
            with pytest.raises(c.CallError, match="poison"):
                session.context.literal(42)
            raise RuntimeError("expected caught outer phase uncertainty")
    assert (path / "data.mdb").read_bytes() == baseline
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref(ref) == q.commit
        assert "status" not in tx.get_dag(session.initial).bindings
        for commit in p.history(tx, session.current):
            assert "outer-completion-" + session.aid not in p.tree(tx, commit)


def test_actual_attempt_head_move_refuses_known_error_terminal_no_fabricated_done(initial, tmp_path):
    path, basis = initial
    q = p.record_request(path, commit=basis, ref="outer")
    session = bridge.Session(path, q, tmp_path / "owned-workspace")
    ref = "outer-head-" + session.aid
    with d.Repository(path) as repo, repo.write() as tx:
        tx.update_ref(ref, q.commit)
    baseline = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="terminal head changed"):
        session.fail(bridge.SessionError("known cooperative failure"))
    assert (path / "data.mdb").read_bytes() == baseline
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref(ref) == q.commit
        assert "status" not in tx.get_dag(session.initial).bindings
        for commit in p.history(tx, session.current):
            assert "outer-completion-" + session.aid not in p.tree(tx, commit)
    assert not session.ended
