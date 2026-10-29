"""TEST ONLY: bounded owned old-story failure evidence, never execution/recovery.

Only synthetic story workspaces are read. No environment, record-byte dump,
serialized scratch traversal, process signaling, dispatch, retry or ref repair.
"""

import json
from pathlib import Path
import re

import daggerml as d

MAX_NOTE_BYTES = 8192
MAX_LOG_BYTES = 512
FILES = (
    "started",
    "launched",
    "worker-ready.json",
    "worker.dml",
    "worker.offline",
    "worker.stdout",
    "worker.stderr",
    "output.bundle",
    "completion.json",
)


def error_fields(error):
    result = {"type": type(error).__name__}
    for name in ("code", "native_code"):
        value = getattr(error, name, None)
        if type(value) is int or (type(value) is str and len(value) <= 32):
            result[name] = value
    return result


def context(error):
    owner = {}
    selected = None
    trace = error.__traceback__
    while trace is not None:
        frame = trace.tb_frame
        values = frame.f_locals
        if frame.f_code.co_name == "produce" and Path(
            frame.f_code.co_filename
        ).name in ("asynchronous_execution.py", "caller_requests.py"):
            owner = {
                key: values.get(key) for key in ("workspace", "phase", "launch", "spec")
            }
            snapshots = values.get("snapshots")
            if type(snapshots) is list and snapshots:
                selected = snapshots[-1]
        if (
            frame.f_code.co_name == "observe_exchange"
            and type(values.get("receipt")) is dict
        ):
            receipt = values["receipt"]
            selected = dict(receipt, commit=str(receipt.get("selected_commit")))
        trace = trace.tb_next
    owner["selected"] = selected
    return owner


def tail(path, limit):
    with path.open("rb") as stream:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - limit))
        data = stream.read(limit)
    return {
        "size": size,
        "truncated": size > len(data),
        "tail": data.decode("utf-8", "replace"),
    }


def scalar(tx, dag, name, kinds=("string",)):
    node = tx.get_node(tx.lookup_node(dag, name))
    if not isinstance(node, d.LiteralNode):
        raise ValueError("diagnostic field is not literal")
    datum = tx.get_datum(node.datum)
    if datum.kind not in kinds:
        raise ValueError("diagnostic scalar has wrong type")
    return datum.value


def typed_final(path, spec):
    with d.Repository(path) as repo, repo.read() as tx:
        head = tx.get_ref(spec.worker_ref)
        current = tx.get_tree(tx.get_commit(head).tree)
        base = tx.get_tree(tx.get_commit(spec.commit).tree)
        if len(current) > 64 or len(base) > 64:
            return {"state": "outside-small-story-profile"}
        names = [
            name
            for name in current
            if name.startswith("attempt-a-") and name not in base
        ]
        if len(names) != 1:
            return {"state": "no-unique-current-attempt", "count": len(names)}
        attempt = current[names[0]]
        fields = tx.get_dag(attempt).bindings
        if "status" not in fields:
            return {"state": "unknown"}
        result = {"state": str(scalar(tx, attempt, "status"))[:32], "head": str(head)}
        for field in ("outcome", "cleanup"):
            node = tx.get_node(fields[field])
            if not isinstance(node, d.SubDAGNode):
                raise ValueError("diagnostic final field is not a DAG")
            role = scalar(tx, node.dag, "role")
            details = {"role": str(role)[:64]}
            if field == "cleanup":
                if role != "local-cleanup-v1":
                    raise ValueError("wrong diagnostic cleanup role")
                details["disposition"] = str(scalar(tx, node.dag, "disposition"))[:32]
            else:
                if role not in ("local-success-v1", "local-failure-v1"):
                    raise ValueError("wrong diagnostic outcome role")
                details["exit_code"] = scalar(
                    tx, node.dag, "exit-code", ("i64", "null")
                )
                if role == "local-failure-v1":
                    details["reason"] = str(scalar(tx, node.dag, "reason"))[:64]
                    details["detail"] = str(scalar(tx, node.dag, "detail"))[:128]
            result[field] = details
        return result


def collect(story, values, limit=MAX_LOG_BYTES):
    report = {
        "phase": (
            values.get("phase")
            if values.get("phase") in ("initial", "publication", "completion")
            else "unknown"
        )
    }
    process = getattr(values.get("launch"), "process", None)
    report["owner"] = {"state": "unavailable", "returncode": None}
    if process is not None:
        try:
            code = process.poll()  # observation only; never wait/terminate/kill
            report["owner"] = {
                "state": "live" if code is None else "reaped",
                "returncode": code,
            }
        except BaseException as error:
            report["owner"]["poll_error"] = error_fields(error)
    selected = values.get("selected")
    if type(selected) is dict:
        report["selected"] = {
            key: str(selected[key])[:128]
            for key in ("phase", "commit", "request_id", "attempt_id")
            if key in selected
        }
    workspace = values.get("workspace")
    if workspace is None:
        report["workspace"] = "unavailable"
        return report
    workspace = Path(workspace).resolve()
    try:
        relative = workspace.relative_to(Path(story).resolve())
    except ValueError:
        report["workspace"] = "outside-owned-story"
        return report
    if re.fullmatch(r"workspace-[1-9][0-9]*", relative.as_posix()) is None:
        report["workspace"] = "outside-fixed-workspace-profile"
        return report
    report["workspace"] = str(relative)
    report["files"] = {name: (workspace / name).exists() for name in FILES}
    report["logs"] = {}
    for name in ("worker.stdout", "worker.stderr"):
        try:
            (workspace / name).resolve().relative_to(workspace)
            report["logs"][name] = tail(workspace / name, limit)
        except ValueError:
            report["logs"][name] = {"read_error": "outside-owned-workspace"}
        except OSError as error:
            report["logs"][name] = {"read_error": type(error).__name__}
    if report["owner"]["state"] != "reaped" or values.get("spec") is None:
        report["final"] = {"state": "skipped-live-or-unknown-owner"}
    else:
        try:
            report["final"] = typed_final(workspace / "worker.dml", values["spec"])
        except BaseException as error:
            report["final"] = {"inspection_error": error_fields(error)}
    return report


def note_failure(error, story):
    """Never mask/change/retry the original exception; caller bare-raises it."""
    try:
        values = context(error)
        report = collect(story, values)
        report["original"] = error_fields(error)
        note = "owned-story-diagnostic: " + json.dumps(
            report, ensure_ascii=True, sort_keys=True
        )
        if len(note.encode("utf-8")) > MAX_NOTE_BYTES:
            # Shrink the already-owned bytes only; no second native open/poll or
            # diagnostic retry that could conceal the first observed error.
            for log in report.get("logs", {}).values():
                if "tail" in log:
                    log["tail"] = log["tail"][-128:]
                    log["truncated"] = True
            note = "owned-story-diagnostic: " + json.dumps(
                report, ensure_ascii=True, sort_keys=True
            )
        if len(note.encode("utf-8")) > MAX_NOTE_BYTES:
            note = 'owned-story-diagnostic: {"capture_error":"profile-overflow"}'
        if hasattr(error, "add_note"):
            error.add_note(note)
        else:
            error.story_diagnostic = note
    except BaseException:
        # Diagnostic IO/native/allocation errors cannot replace the original error.
        pass


def run_story(function, story):
    """Run once; on failure attach bounded owned evidence and bare-raise original."""
    try:
        return function([str(story)])
    except BaseException as error:
        note_failure(error, story)
        raise
