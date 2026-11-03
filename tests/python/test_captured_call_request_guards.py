"""Targeted native ownQ/control/ref and HOST response boundaries; metadata ONLY."""

from dataclasses import replace
from types import SimpleNamespace

import daggerml as d
from daggerml import builtin as b
import pytest

from test_exchange_records import clone
from test_captured_calls import app, bridge, initial


@pytest.mark.parametrize("fault,message", [("Q-tree", "own Q native tree"), ("D-tree", "own Q THIS decision"), ("plan-basis", "pinned call control basis"), ("plan-add", "pinned call control basis")])
def test_own_Q_native_parent_tree_and_pinned_plan_exact_guards(initial, fault, message):
    path, base = initial
    q = app.record_request(path, commit=base, ref="q")
    with d.Repository(path) as repo, repo.write() as tx:
        qfields = tx.get_dag(q.request).bindings
        decision = b.link(tx, qfields["decision"])
        decisions = app.tree(tx, q.decision_commit)
        if fault == "Q-tree":
            entries = app.tree(tx, q.commit)
            entries["outer-request-" + q.request_id] = q.closure["dag"]
            bad = tx.put_commit(tx.put_tree(entries), parents=(q.decision_commit,))
        elif fault == "D-tree":
            decisions["decision-" + q.request_id] = q.closure["dag"]
            dc = tx.put_commit(tx.put_tree(decisions), parents=(base,))
            entries = dict(decisions, **{"outer-request-" + q.request_id: q.request})
            bad = tx.put_commit(tx.put_tree(entries), parents=(dc,))
        else:
            changed = clone(tx, q.plan, fields={"basis" if fault == "plan-basis" else "add-control": b.literal(tx, q.commit.bytes if fault == "plan-basis" else "reuse-selected")})
            new_d = clone(tx, decision, fields={"plan": tx.put_subdag(changed)})
            decisions["decision-" + q.request_id] = new_d
            dc = tx.put_commit(tx.put_tree(decisions), parents=(base,))
            new_q = clone(tx, q.request, fields={"decision": tx.put_subdag(new_d)})
            entries = dict(decisions, **{"outer-request-" + q.request_id: new_q})
            bad = tx.put_commit(tx.put_tree(entries), parents=(dc,))
            q = replace(q, request=new_q)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        app.inspect_request(path, commit=bad, request=q.request)
    assert (path / "data.mdb").read_bytes() == before


def test_uuid_occurrence_collision_native_snapshot_no_partial_Q(initial, monkeypatch):
    path, base = initial
    marker = "b" * 32
    monkeypatch.setattr(app.uuid, "uuid4", lambda: SimpleNamespace(hex=marker))
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        entries["decision-cq-" + marker] = entries["outer"]
        basis = tx.put_commit(tx.put_tree(entries), parents=(base,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="occurrence collision"):
        app.record_request(path, commit=basis, ref="must-not-record")
    assert (path / "data.mdb").read_bytes() == before


def test_postcommit_actual_ref_reread_Host_response_mismatch_is_not_authority(initial, monkeypatch):
    path, base = initial
    original = d.Transaction.get_ref
    calls = []
    def changed(tx, name):
        result = original(tx, name)
        if name == "q-decision":
            calls.append(result)
            return base  # HOST read-response substitute; actual durable Q is preserved.
        return result
    monkeypatch.setattr(d.Transaction, "get_ref", changed)
    with pytest.raises(ValueError, match="actual outer Q/decision/reservation refs"):
        app.record_request(path, commit=base, ref="q")
    monkeypatch.setattr(d.Transaction, "get_ref", original)
    assert len(calls) == 1
    with d.Repository(path) as repo, repo.read() as tx:
        commit = tx.get_ref("q")
        entries = app.tree(tx, commit)
        request = next(v for n, v in entries.items() if n.startswith("outer-request-cq-"))
    assert app.inspect_request(path, commit=commit, request=request).base == base


def test_session_requires_exact_actual_request_response_before_initial_T(initial, tmp_path):
    path, base = initial
    q = app.record_request(path, commit=base, ref="q")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(bridge.SessionError, match="actual pending fresh"):
        bridge.Session(path, replace(q, base=q.commit), tmp_path / "absent")
    assert not (tmp_path / "absent").exists()
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("boundary,message", [("advance", "outer phase head changed"), ("complete", "terminal head changed")])
def test_moved_actual_native_outer_head_stops_publication(initial, tmp_path, boundary, message):
    path, base = initial
    q = app.record_request(path, commit=base, ref="q")
    session = bridge.Session(path, q, tmp_path / "session")
    with d.Repository(path) as repo, repo.write() as tx:
        tx.update_ref("outer-head-" + session.aid, q.commit)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        session._advance(q.commit) if boundary == "advance" else session._complete(app.ERROR_ROLE, "known error")
    assert (path / "data.mdb").read_bytes() == before


def test_native_argument_contract_rejects_actual_wrong_key_or_non_I64(initial):
    path, base = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        with b.Recorder(tx, commit=base) as recorder:
            wrong = recorder.dag(recorder.arguments({"a": recorder.literal(d.Datum.string("13")), "b": recorder.literal(d.Datum.i64(29))}))
        entries["wrong"] = wrong
        commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(ValueError, match="exact I64 argument contract"):
            app.arguments(tx, commit, wrong, ("a", "b"), set())
        with pytest.raises(ValueError, match="exact I64 argument contract"):
            app.arguments(tx, base, entries["inputs"], ("x",), set())


def test_owned_fabricated_node_direct_guard(initial, tmp_path):
    path, base = initial
    q = app.record_request(path, commit=base, ref="q")
    session = bridge.Session(path, q, tmp_path / "session")
    with pytest.raises(bridge.SessionError, match="foreign/fabricated/ended"):
        session._owned(bridge.Node(session.input.value))
