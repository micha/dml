"""HOST typed-description corruption AFTER real native validation, not native faults.

Each test uses imported frozen native success, positive real validators, then ONE
explicit response substitution to exercise the adapter's defensive boundary.
"""

from dataclasses import replace
from types import SimpleNamespace

import daggerml as d
from daggerml import builtin as b
import pytest

from test_captured_call_profiles import case, frozen
from test_captured_call_history_guards import last_phase
from test_captured_calls import app, bridge, leaf


@pytest.mark.parametrize("fault,message", [("prefix", "requires exact outer getter/call/input prefix"), ("submission", "actual public leaf submission differs")])
def test_ORIGINAL_native_positive_then_HOST_inspection_response_refusal(case, monkeypatch, fault, message):
    path, got = case
    with d.Repository(path) as repo, repo.read() as tx:
        call = tx.get_dag(got["got"]["calls"][0]).bindings
        slot = b.scalar(tx, call["selection-slot"], "string")
    assert app.inspect_leaf_success(path, commit=got["final"], slot=slot)[0].intent_uri == leaf.ADD
    if fault == "prefix":
        original = app.inspect_spine
        def wrong(*a, **k):
            actual = original(*a, **k)
            return dict(actual, getters=())
        monkeypatch.setattr(app, "inspect_spine", wrong)
    else:
        original = app.public_prepare
        def wrong(*a, **k):
            actual = original(*a, **k)
            return replace(actual, inputs=got["q"].closure["dag"])
        monkeypatch.setattr(app, "public_prepare", wrong)
    with pytest.raises(ValueError, match=message):
        app.inspect_leaf_success(path, commit=got["final"], slot=slot)


@pytest.mark.parametrize("fault,message", [("plan", "fresh completion decision/plan differs"), ("success-spine", "actual successful spine differs before return")])
def test_native_completion_positive_then_HOST_own_request_spine_response(case, monkeypatch, fault, message):
    path, got = case
    assert app.inspect_completion(path, commit=got["final"])["outcome"] == "success"
    if fault == "plan":
        original = app.inspect_request
        def wrong(*a, **k):
            actual = original(*a, **k)
            return replace(actual, plan=got["q"].closure["dag"])
        # Completion's spine still needs a valid request to certify prior calls.
        original_spine = app.inspect_spine
        monkeypatch.setattr(app, "inspect_spine", lambda *a, **k: original_spine(*a, **k))
        def selective(*a, **k):
            import inspect
            caller = inspect.currentframe().f_back.f_code.co_name
            return wrong(*a, **k) if caller == "inspect_completion" else original(*a, **k)
        monkeypatch.setattr(app, "inspect_request", selective)
        with pytest.raises(ValueError, match=message):
            app.inspect_completion(path, commit=got["final"])
    else:
        # TEST-PRIVATE cooperative state reconstruction over native original pre-return prefix.
        with d.Repository(path) as repo, repo.read() as tx:
            phase, _, _, _ = last_phase(tx, got["final"], "returned")
            before = tx.get_commit(phase).parents[0]
            aid = b.scalar(tx, tx.get_dag(got["got"]["initial"]).root, "string")
            actual = b.Inspector(tx, commit=before).node(got["got"]["leaf_result"])
        session = bridge.Session.__new__(bridge.Session)
        session.path, session.q, session.current = path, got["q"], before
        session.initial, session.aid = got["got"]["initial"], aid
        session.calls, session.getters = list(got["got"]["calls"]), list(got["got"]["getters"])
        session.seen, session.failed_call = set(), None
        node = bridge.Node(actual.value)
        session.last_result = node
        session.handles = {node: (actual.dag, actual.datum)}
        session.ended = session.poisoned = session.unknown = False
        original = app.inspect_spine
        def wrong(*a, **k):
            native = original(*a, **k)
            return dict(native, getters=()) if a[1] == before else native
        monkeypatch.setattr(app, "inspect_spine", wrong)
        with pytest.raises(ValueError, match=message):
            session.finish(node)
        assert session.unknown and session.poisoned


def test_pending_PUBLIC_Q_native_positive_then_HOST_dimension_response(case, monkeypatch):
    path, got = case
    with d.Repository(path) as repo, repo.read() as tx:
        commit, _, _, _ = last_phase(tx, got["final"], "leaf-pending", 3)
        aid = b.scalar(tx, tx.get_dag(got["got"]["initial"]).root, "string")
    assert app.inspect_spine(path, commit, got["q"].request, got["got"]["initial"], aid, set())["calls"] == []
    original = app.public_prepare
    def wrong(*a, **k):
        actual = original(*a, **k)
        return replace(actual, inputs=got["q"].closure["dag"])
    monkeypatch.setattr(app, "public_prepare", wrong)
    with pytest.raises(ValueError, match="pending public Q exact dimensions differ"):
        app.inspect_spine(path, commit, got["q"].request, got["got"]["initial"], aid, set())
