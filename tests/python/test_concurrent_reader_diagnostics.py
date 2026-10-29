"""Bounded fixed-owned old-reader diagnostics preserve original postcleanup failure."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import concurrent_reader_diagnostics as diagnostic


class CachedProcess:
    def __init__(self, code):
        self.returncode = code

    def poll(self):
        pytest.fail("diagnostic cannot observe/reap/retry/signal processes")

    wait = terminate = kill = poll


def note(error):
    text = error.__notes__[-1]
    assert len(text.encode("utf-8")) <= 8192
    assert "\x1b" not in text and "\0" not in text
    return json.loads(text[len(diagnostic.PREFIX) :])


def failure(root, original, events, processes):
    namespace = dict(
        WORKSPACE=root / "workspace",
        ORIGINAL=original,
        EVENTS=events,
        PROCESSES=processes,
    )
    exec(
        compile(
            """def test_concurrent_read_only_observers_distinct_immutable_packets():
 workspace=WORKSPACE
 processes=PROCESSES
 try:
  EVENTS.append('invoke')
  raise ORIGINAL
 finally:
  EVENTS.append('existing-cleanup')
""",
            str(root / "test_exchange_progress_process.py"),
            "exec",
        ),
        namespace,
    )
    return diagnostic.after_cleanup(
        namespace["test_concurrent_read_only_observers_distinct_immutable_packets"]
    )


def test_failure_only_capture_after_cleanup_cached_codes_and_exact_fixed_owned_tails(
    tmp_path, monkeypatch
):
    events = []
    original = AssertionError("original concurrent observer rc1")
    (tmp_path / "concurrent-errors-0").write_bytes(
        b"ignored" * 1000 + b"\x1b\0stderr-tail"
    )
    (tmp_path / "concurrent-errors-1").write_bytes(b"second reader traceback")
    (tmp_path / "concurrent-ready-0").touch()
    (tmp_path / "concurrent-ready-1").touch()
    (tmp_path / "concurrent-release").touch()
    old_tail = diagnostic.tail
    paths = []

    def owned_tail(path, limit):
        assert events == ["invoke", "existing-cleanup"]
        assert path.parent == tmp_path and path.name in (
            "concurrent-errors-0",
            "concurrent-errors-1",
        )
        assert limit == 512
        paths.append(path.name)
        return old_tail(path, limit)

    monkeypatch.setattr(diagnostic, "tail", owned_tail)
    with pytest.raises(AssertionError) as caught:
        failure(tmp_path, original, events, [CachedProcess(1), CachedProcess(0)])()
    assert (
        caught.value is original and str(original) == "original concurrent observer rc1"
    )
    assert events == ["invoke", "existing-cleanup"]
    report = note(original)
    assert report["cached_returncodes"] == [1, 0]
    assert all(report["ready_release"].values())
    assert report["logs"]["concurrent-errors-0"]["truncated"]
    assert report["logs"]["concurrent-errors-0"]["tail"].endswith("\x1b\0stderr-tail")
    assert paths == ["concurrent-errors-0", "concurrent-errors-1"]
    assert str(tmp_path) not in original.__notes__[-1]


def test_success_once_no_failure_capture(monkeypatch):
    events = []
    marker = object()

    def success():
        events.append("invoke")
        return marker

    monkeypatch.setattr(
        diagnostic, "note_failure", lambda *a: pytest.fail("failure-only diagnostic")
    )
    assert diagnostic.after_cleanup(success)() is marker and events == ["invoke"]


@pytest.mark.parametrize("fault", ["read", "allocation", "context", "note"])
def test_diagnostic_failure_cannot_mask_original_or_repeat_test(
    tmp_path, monkeypatch, fault
):
    original = RuntimeError("original unchanged")
    events = []
    if fault == "read":
        monkeypatch.setattr(
            diagnostic,
            "tail",
            lambda *a: (_ for _ in ()).throw(OSError("private owned IO failure")),
        )
    elif fault == "allocation":
        monkeypatch.setattr(
            diagnostic, "collect", lambda *a: (_ for _ in ()).throw(MemoryError())
        )
    elif fault == "context":
        monkeypatch.setattr(
            diagnostic, "context", lambda *a: (_ for _ in ()).throw(OSError())
        )
    else:

        class Original(RuntimeError):
            def add_note(self, note):
                raise MemoryError()

        original = Original("original unchanged")
    with pytest.raises(RuntimeError) as caught:
        failure(tmp_path, original, events, [CachedProcess(None)])()
    assert caught.value is original and str(original) == "original unchanged"
    assert events == ["invoke", "existing-cleanup"]
    if fault == "read":
        assert note(original)["logs"]["concurrent-errors-0"]["read_error"] == "OSError"


def test_note_bound_original8192_and_outside_symlink_never_read(tmp_path, monkeypatch):
    owned = tmp_path / "owned"
    owned.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"must-not-read")
    for name in ("concurrent-errors-0", "concurrent-errors-1"):
        (owned / name).write_bytes(b"\0" * 1000000)
    original = ValueError("primary bounded error")
    events = []
    with pytest.raises(ValueError) as caught:
        failure(owned, original, events, [CachedProcess(1), CachedProcess(None)])()
    assert caught.value is original and note(original)["cached_returncodes"] == [
        1,
        None,
    ]
    monkeypatch.setattr(diagnostic, "MAX_NOTE_BYTES", 128)
    original2 = ValueError("bounded original")
    with pytest.raises(ValueError):
        failure(owned, original2, [], [])()
    assert note(original2) == {"capture_error": "profile-overflow"}
    # Model resolved outside path on every platform, no symlink privileges/skip.
    resolve = Path.resolve

    def resolved(path, *a, **k):
        if path.name in ("concurrent-errors-0", "concurrent-ready-0"):
            return outside
        return resolve(path, *a, **k)

    monkeypatch.setattr(Path, "resolve", resolved)
    tail = diagnostic.tail

    def allowed(path, limit):
        assert path.name == "concurrent-errors-1"
        return tail(path, limit)

    monkeypatch.setattr(diagnostic, "tail", allowed)
    report = diagnostic.collect(owned / "workspace", [])
    assert report["logs"]["concurrent-errors-0"]["read_error"] == "outside-owned-root"
    assert report["ready_release"]["concurrent-ready-0"] == "outside-owned-root"


def test_unknown_context_no_files_or_process_access(monkeypatch):
    monkeypatch.setattr(
        diagnostic, "tail", lambda *a: pytest.fail("no unowned path reads")
    )
    report = diagnostic.collect(None, None)
    assert report["owned_root"] == "unavailable" and report["cached_returncodes"] == []
    original = ValueError("no matching trace")
    try:
        raise original
    except ValueError:
        diagnostic.note_failure(original)
    assert note(original)["owned_root"] == "unavailable"
