"""Metadata/static controller barriers; NEVER call run/installed computation."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_captured_calls import ROOT

spec = importlib.util.spec_from_file_location("captured_story_tooling", ROOT / "tests/captured_calls/installed_story.py")
story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story)


@pytest.mark.parametrize("fault", ["no-dispatch", "no-spawn", "wait-missing", "wait-nonzero", "unreaped", "failure", "cleanup", "Q", "attempt", "pre", "already-verified"])
def test_leaf_run_barrier_STOPS_before_observation_import_on_wrong_actual_disposition(monkeypatch, fault):
    expected = dict(spawned=True, child_index=0, request="Q", workspace="inert")
    child = dict(waits=[dict(returned=True, exit=0)], request="Q", attempt_id="a", pre_dispatch="P")
    row = dict(outcome="success", cleanup="ok", request="Q", attempt_id="a", pre_dispatch="P")
    process = SimpleNamespace(returncode=0)
    if fault == "no-dispatch":
        expected = None
    elif fault == "no-spawn":
        expected["spawned"] = False
    elif fault == "wait-missing":
        child["waits"] = []
    elif fault == "wait-nonzero":
        child["waits"] = [dict(returned=True, exit=7)]
    elif fault == "unreaped":
        process.returncode = None
    elif fault == "already-verified":
        child["verified"] = True
    else:
        row[{"Q": "request", "attempt": "attempt_id", "pre": "pre_dispatch", "failure": "outcome", "cleanup": "cleanup"}[fault]] = "wrong"
    monkeypatch.setattr(story.d.Repository, "__init__", lambda *a, **k: pytest.fail("bad disposition BEFORE any native/observation/import"))
    with pytest.raises(RuntimeError):
        story.verify_leaf_run(expected, [(process, child)], row)


def custody_fixture(root):
    facts, rows, events = {}, [], []
    for i in range(5):
        aid = "a-%d" % i
        fact = dict(request="Q-%d" % i, attempt_id=aid, pre_dispatch="P-%d" % i, binding="B-%d" % i,
            inputs="I-%d" % i, initial_attempt="T-%d" % i, source_sha256="source-%d" % i,
            completion="F-%d" % i, publication_ref="attempt-" + aid, scratch="/owned/scratch-%d" % i)
        facts[aid] = fact
        command = ["/prefix/python", fact["scratch"] + "/entry.py", "/owned/work-%d/worker.dml" % i,
                   fact["pre_dispatch"], aid, fact["publication_ref"]]
        row = dict(fact, pid=1000 + i, command=command, workspace="/owned/work-%d" % i,
                   waits=[dict(returned=True, exit=0)], verified=True, absent=True)
        rows.append(row)
        events.extend((dict(event="dispatch", request=row["request"], workspace=row["workspace"]),
            dict(row, event="spawn"), dict(event="wait", pid=row["pid"], receipt=dict(returned=True, exit=0)),
            dict(event="leaf-disposition-verified", attempt_id=aid, completion=fact["completion"])))
    return facts, rows, events


@pytest.mark.parametrize("fault", [None, "duplicate-pid", "request", "attempt", "pre_dispatch", "source_sha256", "command", "interpreter", "wait", "absent", "unverified", "event-order", "event-request", "event-source", "extra-spawn"])
def test_custody_native_fact_and_incremental_primary_metadata_oracles(tmp_path, fault):
    facts, rows, events = custody_fixture(tmp_path)
    if fault == "duplicate-pid":
        rows[1]["pid"] = rows[0]["pid"]
    elif fault in ("request", "pre_dispatch", "source_sha256"):
        rows[0][fault] = "wrong"
    elif fault == "attempt":
        rows[0]["attempt_id"] = "wrong"
    elif fault in ("command", "interpreter"):
        rows[0]["command"] = list(rows[0]["command"])
        rows[0]["command"][0 if fault == "interpreter" else 4] = "wrong"
    elif fault == "wait":
        rows[0]["waits"] = []
    elif fault == "absent":
        rows[0]["absent"] = False
    elif fault == "unverified":
        rows[0]["verified"] = False
    elif fault == "event-order":
        events[0], events[1] = events[1], events[0]
    elif fault == "event-request":
        events[0]["request"] = "wrong"
    elif fault == "event-source":
        events[1]["source_sha256"] = "wrong"
    elif fault == "extra-spawn":
        events.append(dict(events[1]))
    (tmp_path / "custody.json").write_text(json.dumps(dict(children=rows)))
    (tmp_path / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    if fault is None:
        story.verify_custody(tmp_path, facts, "/prefix/python")
    else:
        with pytest.raises((ValueError, KeyError)):
            story.verify_custody(tmp_path, facts, "/prefix/python")


def test_controller_static_successful_leaf_barrier_and_exact_expected_Q_before_spawn():
    import ast
    tree = ast.parse((ROOT / "tests/captured_calls/installed_story.py").read_text())
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
    event = next(n for n in run.body if isinstance(n, ast.FunctionDef) and n.name == "event")
    assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "verify_leaf_run" for n in ast.walk(event))
    source = (ROOT / "tests/captured_calls/installed_story.py").read_text()
    assert 'str(spec.request) != expected["request"]' in source
    assert 'command != [sys.executable' in source
    assert 'pending_requests != leaf_qids or producing_attempts != leaf_attempts' in source
    assert '(entries["add-A"], entries["double-A"])' in source
    assert 'if __name__ == "__main__"' in source


def test_REAL_phase_receipt_category_payload_native_positive_and_legacy_collision(tmp_path, monkeypatch):
    """ONE metadata Q/T/getter; no ordinary/LOCAL/OS invocation. Same real row negative."""
    import ast
    import socket
    import subprocess
    from test_captured_calls import app, bridge
    def blocked(*args, **kwargs):
        pytest.fail("metadata regression forbids leafQ/dispatch/transport")
    # Before ANY authoring/invocation; no computational Popen permission.
    monkeypatch.setattr(subprocess, "Popen", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(app.ex, "record_exchange_request", blocked)
    monkeypatch.setattr(app.ex, "execute_exchange", blocked)
    monkeypatch.setattr(story.local, "run_request", blocked)
    path = tmp_path / "metadata.dml"
    base = app.initialize(path, __import__("sys").executable)
    base = app.prepare_arguments(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
    q = app.record_request(path, commit=base, ref="ONE-q")
    event_root = tmp_path / "receipts"
    event_root.mkdir()
    rows, actual_callbacks = [], []
    def callback(category, payload):
        actual_callbacks.append((category, dict(payload)))
        story.append_event(event_root, rows, category, payload)
    session = bridge.Session(path, q, tmp_path / "owned-session", receipt=callback)
    parent = session.current
    value = session.map_get(session.input, "a")
    assert value.value == story.d.Datum.i64(13)
    assert len(actual_callbacks) == 2 and [c for c, r in actual_callbacks] == ["initial", "phase"]
    category, real_row = actual_callbacks[-1]
    assert category == "phase" and real_row["kind"] == "get-a"
    records = [json.loads(line) for line in (event_root / "events.jsonl").read_text().splitlines()]
    assert records == rows and records[-1] == dict(event="phase", **real_row)
    assert records[-1]["event"] == "phase" and records[-1]["kind"] == "get-a"
    # Exact isolated OLD statement consumes SAME REAL _phase row; NOT old-controller replay.
    legacy_events = []
    legacy = "events.append(dict(kind=kind, **row))"
    with pytest.raises(TypeError, match="multiple values"):
        eval(compile(ast.parse(legacy, mode="eval"), "isolated old event append", "eval"),
             {"events": legacy_events, "kind": category, "row": real_row})
    assert legacy_events == []
    with story.d.Repository(path) as repo, repo.read() as tx:
        head = tx.get_ref("outer-head-" + session.aid)
        assert head == session.current and str(head) == real_row["commit"]
        assert tx.get_commit(head).parents == (parent,) and str(parent) == real_row["previous"]
        old, current = app.tree(tx, parent), app.tree(tx, head)
        phase_name = app.phase_name(session.aid, 0)
        payload_name = app.payload_names(session.aid, 0, "get-a")["node"]
        assert set(current) - set(old) == {phase_name, payload_name}
        assert all(current[n] == v for n, v in old.items())
        fields = tx.get_dag(current[phase_name]).bindings
        assert story.b.scalar(tx, fields["kind"], "string") == "get-a"
        getter = story.b.link(tx, fields["node"])
        assert current[payload_name] == getter and str(getter) == real_row["links"]["node"]
        assert story.b.scalar(tx, fields["index"], "i64") == real_row["index"] == 0
        assert story.b.link(tx, fields["request"]) == q.request
        assert story.b.link(tx, fields["initial-attempt"]) == session.initial
        _, stored = story.b.node_value(tx, tx.get_dag(getter).bindings["value"])
        assert stored == story.d.Datum.i64(13)
        assert not any(n.startswith(("request-q-", "attempt-a-", "publication-a-")) for n in current)
        assert len([n for n in current if n.startswith("outer-request-cq-")]) == 1
        assert len([n for n in current if n.startswith("outer-attempt-ca-")]) == 1
    session.ended = True  # Partial stopped metadata context; no handle/child owned.


def test_reserved_event_payload_key_rejects_BEFORE_list_or_log_mutation(tmp_path):
    rows = []
    story.append_event(tmp_path, rows, "phase", dict(kind="get-a", index=0))
    before = (tmp_path / "events.jsonl").read_bytes()
    original = list(rows)
    with pytest.raises(RuntimeError, match="reserved event category"):
        story.append_event(tmp_path, rows, "phase", dict(event="spoofed", kind="get-a"))
    assert rows == original and (tmp_path / "events.jsonl").read_bytes() == before

