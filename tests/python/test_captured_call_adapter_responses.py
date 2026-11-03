"""Explicit HOST delegate-response boundaries over real pinned native authority.

No native corruption or actual child custody is claimed for forged descriptions.
One frozen original history supplies valid expected descriptors; no source execution.
"""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import inspect

import daggerml as d
from daggerml import builtin as b
import pytest

from test_captured_call_profiles import case, frozen
from test_captured_call_reuse_guards import reused_case, reuse_history
from test_captured_call_history_guards import last_phase
from test_captured_calls import app, bridge, leaf


def original_leaf(path, got, slot=0):
    with d.Repository(path) as repo, repo.read() as tx:
        fields = tx.get_dag(got["got"]["calls"][slot]).bindings
        name = b.scalar(tx, fields["selection-slot"], "string")
    return name, app.inspect_leaf_success(path, commit=got["final"], slot=name)[0]


@pytest.mark.parametrize("fault,message", [("value", "ORIGINAL returned owner/value differs"), ("trace", "ORIGINAL getter positions differ")])
def test_native_profile_positive_then_HOST_Inspector_description_guard(case, monkeypatch, fault, message):
    path, got = case
    slot, selected = original_leaf(path, got)
    if fault == "value":
        original = b.Inspector.node
        def altered(self, dag):
            actual = original(self, dag)
            return replace(actual, value=d.Datum.string("not I64")) if dag == selected.result and inspect.currentframe().f_back.f_code.co_name == "inspect_leaf_success" else actual
        monkeypatch.setattr(b.Inspector, "node", altered)
    else:
        original = b.Inspector.trace
        def altered(self, dag, **kwargs):
            actual = original(self, dag, **kwargs)
            return () if inspect.currentframe().f_back.f_code.co_name == "inspect_leaf_success" else actual
        monkeypatch.setattr(b.Inspector, "trace", altered)
    with pytest.raises(ValueError, match=message):
        app.inspect_leaf_success(path, commit=got["final"], slot=slot)


@pytest.mark.parametrize("fault,message", [("F", "fresh call ORIGINAL Q/joined F differs"), ("binding", "call reuse exact captured binding/full MAP differs")])
def test_own_fresh_native_positive_then_HOST_selected_description_guard(case, monkeypatch, fault, message):
    path, got = case
    with d.Repository(path) as repo, repo.read() as tx:
        commit, _, _, _ = last_phase(tx, got["final"], "leaf-done", 6)
        aid = b.scalar(tx, tx.get_dag(got["got"]["initial"]).root, "string")
    assert len(app.inspect_spine(path, commit, got["q"].request, got["got"]["initial"], aid, set())["calls"]) == 1
    original = app.inspect_leaf_success
    def altered(*args, **kwargs):
        selected, result = original(*args, **kwargs)
        if kwargs["commit"] == commit and inspect.currentframe().f_back.f_code.co_name == "inspect_spine":
            selected = replace(selected, **{"completion": got["q"].base} if fault == "F" else {"binding": got["q"].closure["double"]["binding"]})
        return selected, result
    monkeypatch.setattr(app, "inspect_leaf_success", altered)
    with pytest.raises(ValueError, match=message):
        app.inspect_spine(path, commit, got["q"].request, got["got"]["initial"], aid, set())


def test_native_reuse_positive_then_HOST_pinned_witness_response_guard(reused_case, monkeypatch):
    path, got = reused_case
    assert len(app.inspect_spine(path, got["commit"], got["q"].request, got["initial"], got["aid"], set())["calls"]) == 2
    original = app.inspect_leaf_success
    def altered(*args, **kwargs):
        selected, result = original(*args, **kwargs)
        if kwargs["commit"] == got["commit"] and inspect.currentframe().f_back.f_code.co_name == "inspect_spine":
            selected = replace(selected, dag=got["q"].closure["dag"])
        return selected, result
    monkeypatch.setattr(app, "inspect_leaf_success", altered)
    with pytest.raises(ValueError, match="reused call must consume exact pinned selection"):
        app.inspect_spine(path, got["commit"], got["q"].request, got["initial"], got["aid"], set())


@pytest.mark.parametrize("fault,message", [("pinned", "pinned double selection changed"), ("match", "required double selection does not match")])
def test_Host_pinned_selected_response_guard_BEFORE_own_double_Q(reused_case, monkeypatch, fault, message):
    path, got = reused_case
    # TEST-PRIVATE reconstruct exact copied handles/state at retained double-input prefix.
    with d.Repository(path) as repo, repo.read() as tx:
        commit, _, phase, _ = last_phase(tx, got["commit"], "double-input")
        full = b.link(tx, tx.get_dag(phase).bindings["inputs"])
        actual = b.Inspector(tx, commit=commit).node(full)
    spine = app.inspect_spine(path, commit, got["q"].request, got["initial"], got["aid"], set())
    session = bridge.Session.__new__(bridge.Session)
    session.path, session.q, session.current = path, got["q"], commit
    session.initial, session.aid, session.seen = got["initial"], got["aid"], set()
    session.calls, session.getters = list(spine["calls"]), list(spine["getters"])
    session.tokens = (object(), object())
    node = bridge.Node(actual.value)
    session.double_input = node
    session.handles = {node: (actual.dag, actual.datum)}
    session.ended = session.poisoned = session.unknown = False
    original = app.inspect_leaf_success
    def altered(*args, **kwargs):
        selected, result = original(*args, **kwargs)
        if inspect.currentframe().f_back.f_code.co_name == "invoke":
            selected = replace(selected, **{"dag": got["q"].closure["dag"]} if fault == "pinned" else {"binding": got["q"].closure["add"]["binding"]})
        return selected, result
    monkeypatch.setattr(app, "inspect_leaf_success", altered)
    monkeypatch.setattr(app.ex, "record_exchange_request", lambda *a, **k: pytest.fail("guard BEFORE new ownQ"))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, bridge.SessionError), match=message):
        session.invoke(session.tokens[1], node)
    assert (path / "data.mdb").read_bytes() == before and session.poisoned


def test_native_pinned_reuse_positive_then_HOST_selection_binding_miss_in_reader(reused_case, monkeypatch):
    path, got = reused_case
    original = app.inspect_leaf_success
    def altered(*args, **kwargs):
        selected, result = original(*args, **kwargs)
        if kwargs["commit"] == got["q"].base and kwargs["slot"] == app.DOUBLE_SLOT and inspect.currentframe().f_back.f_code.co_name == "inspect_spine":
            selected = replace(selected, binding=got["q"].closure["add"]["binding"])
        return selected, result
    monkeypatch.setattr(app, "inspect_leaf_success", altered)
    with pytest.raises(ValueError, match="required pinned double selection mismatch"):
        app.inspect_spine(path, got["commit"], got["q"].request, got["initial"], got["aid"], set())
