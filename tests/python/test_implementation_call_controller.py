"""Controller-envelope/native partial metadata and static no-default-activation contracts."""

import ast
import importlib.util
import json
from pathlib import Path
import sys

import daggerml as d
from daggerml import builtin as b
import pytest

from test_implementation_calls import initial, p, bridge

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "tests/implementation_calls/installed_story.py"
READER = ROOT / "tests/implementation_calls/offline_read.py"


def controller():
    before = list(sys.path)
    try:
        spec = importlib.util.spec_from_file_location("implementation_controller_test", CONTROLLER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = before


def test_event_reserved_key_reject_BEFORE_list_or_file_mutation(tmp_path):
    module = controller()
    events = []
    with pytest.raises(RuntimeError, match="reserved"):
        module.append_event(tmp_path, events, "phase", {"event": "wrong", "kind": "get-a"})
    assert events == [] and not (tmp_path / "events.jsonl").exists()
    module.append_event(tmp_path, events, "phase", {"kind": "get-a"})
    assert events == [{"event": "phase", "kind": "get-a"}]
    assert [json.loads(x) for x in (tmp_path / "events.jsonl").read_text().splitlines()] == events


def test_actual_partial_native1Q1T1getter_event_kind_preserved_ZERO_ordinary_LOCAL(initial, tmp_path, monkeypatch):
    path, commit = initial
    module = controller()
    events = []
    def event(category, row):
        module.append_event(tmp_path, events, category, row)
    def forbidden(*a, **k):
        pytest.fail("partial metadata event check cannot dispatch ordinary/LOCAL work")
    monkeypatch.setattr(p.ex, "execute_exchange", forbidden)
    q = p.record_request(path, commit=commit, ref="outer")
    session = bridge.Session(path, q, tmp_path / "session", event)
    with session.context:
        session.start()
        got = session.nodes.map_get(session.input, "a")
        assert got.value == d.Datum.i64(13)
    session.ended = True
    assert len(session.getters) == 1 and not session.calls
    phases = [event for event in events if event["event"] == "phase"]
    assert [event["kind"] for event in phases] == ["get-key-a", "get-arguments-a", "get-a"]
    with d.Repository(path) as repo, repo.read() as tx:
        entries = p.tree(tx, session.current)
        assert len([n for n in entries if n.startswith("outer-request-iq-")]) == 1
        assert len([n for n in entries if n.startswith("outer-attempt-ia-")]) == 1
        assert not any(n.startswith(("request-q-", "attempt-a-", "outer-completion-")) for n in entries)
        assert "status" not in tx.get_dag(session.initial).bindings
        for event in phases:
            phase = p.tree(tx, d.ObjectId.from_hex(event["commit"]))[p.phase_name(session.aid, event["index"])]
            assert b.scalar(tx, tx.get_dag(phase).bindings["kind"], "string") == event["kind"]


def test_controller_only_explicit_run_and_reader_controls_are_not_implicit_jobs():
    module = controller()
    assert len(module.SOURCE_NAMES) == 10 and "implementation_call_adapter.py" in module.SOURCE_NAMES
    with pytest.raises(ValueError, match="controls"):
        module.main([])
    # Compile actual source without executing reader audit hooks; syntax/route contract only.
    reader = ast.parse(READER.read_text())
    assert any(isinstance(n, ast.FunctionDef) and n.name == "activate" for n in reader.body)
    source = READER.read_text()
    assert 'story.c.Context.__init__ = story.c.Context.invoke = forbidden' in source
    assert 'story.adapter.invoke = story.adapter.execute' in source
    assert '"urllib.parse"' in source and '"urllib.request"' in source
    assert 'custody["direct"] != 6' in source
