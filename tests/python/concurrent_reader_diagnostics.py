"""TEST ONLY: failure evidence AFTER existing concurrent-reader cleanup.

Fixed owned stderr tails/existence and cached returncodes only. No process method,
repository/environment/record read, dispatch, retry, repair, signal or deadline change.
"""

from functools import wraps
import json
from pathlib import Path

from story_diagnostics import tail

MAX_NOTE_BYTES = 8192
MAX_TAIL_BYTES = 512
PREFIX = "concurrent-reader-diagnostic: "


def context(error):
    trace = error.__traceback__
    while trace is not None:
        frame = trace.tb_frame
        if (
            frame.f_code.co_name
            == "test_concurrent_read_only_observers_distinct_immutable_packets"
            and Path(frame.f_code.co_filename).name
            == "test_exchange_progress_process.py"
        ):
            return frame.f_locals.get("workspace"), frame.f_locals.get("processes")
        trace = trace.tb_next
    return None, None


def collect(workspace, processes):
    report = {"cached_returncodes": [], "ready_release": {}, "logs": {}}
    if type(processes) is list:
        for process in processes[:2]:
            code = getattr(process, "returncode", None)  # NO poll/wait/signal.
            report["cached_returncodes"].append(code if type(code) is int else None)
    if workspace is None:
        report["owned_root"] = "unavailable"
        return report
    root = Path(workspace).parent.resolve()
    for name in ("concurrent-ready-0", "concurrent-ready-1", "concurrent-release"):
        path = root / name
        if path.resolve().parent != root:
            report["ready_release"][name] = "outside-owned-root"
        else:
            report["ready_release"][name] = path.exists()
    for name in ("concurrent-errors-0", "concurrent-errors-1"):
        path = root / name
        try:
            if path.resolve().parent != root:
                report["logs"][name] = {"read_error": "outside-owned-root"}
            else:
                report["logs"][name] = tail(path, MAX_TAIL_BYTES)
        except OSError as error:
            report["logs"][name] = {"read_error": type(error).__name__[:64]}
    return report


def note_failure(error):
    try:
        workspace, processes = context(error)
        report = collect(workspace, processes)
        note = PREFIX + json.dumps(report, ensure_ascii=True, sort_keys=True)
        if len(note.encode("utf-8")) > MAX_NOTE_BYTES:
            note = PREFIX + '{"capture_error":"profile-overflow"}'
        if hasattr(error, "add_note"):
            error.add_note(note)
        else:
            error.concurrent_reader_diagnostic = note
    except BaseException:
        pass  # Diagnostics must never replace original failure.


def after_cleanup(function):
    """Call once; original finally cleanup completes before bounded note/bare raise."""

    @wraps(function)
    def run(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except BaseException as error:
            note_failure(error)
            raise

    return run
