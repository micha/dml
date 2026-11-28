"""Expose command, native-dispatch and bundle-parser observations to Quint."""

from collections import defaultdict, deque
from contextlib import contextmanager
import json
from os import sep
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import replay_core
from run_histories import replay_history
from trace_support import Replay


def event(op, *args):
    return {"op": op, "args": list(args)}


class Commands:
    def __init__(self, events):
        self.events = events

    @contextmanager
    def history(self, directory):
        values = []

        def append_value(value):
            self.events.append(event("append_value", value))
            values.append(value)
            return {"length": len(values)}

        def read_value():
            self.events.append(event("read_value"))
            return {"value": values[-1]}

        self.events.append(event("enter", directory.name))
        try:
            yield Replay({"append_value": append_value, "read_value": read_value})
        finally:
            self.events.append(event("close", directory.name))


class NativeProbe:
    class Error(RuntimeError):
        pass

    def __init__(self, directory, replies, events):
        self.prefix = str(directory) + sep
        self.events = events
        self.replies = defaultdict(deque)
        for reply in replies:
            self.replies[reply["op"]].append(reply)
        self.handles = {}

    def operand(self, value):
        for name, handle in self.handles.items():
            if value is handle:
                return f"handle:{name}"
        if isinstance(value, bytes):
            return f"bytes:{value.hex()}"
        kind = "path" if isinstance(value, Path) else type(value).__name__
        text = str(value)
        if text.startswith(self.prefix):
            text = "<history>/" + text[len(self.prefix):]
        return f"{kind}:{text}"

    def __getattr__(self, op):
        def call(*args):
            self.events.append(event(op, *(self.operand(arg) for arg in args)))
            if not self.replies[op]:
                raise RuntimeError(f"unscripted native operation: {op}")
            reply = self.replies[op].popleft()
            if reply["status"]:
                exception = self.Error if reply["apiError"] else RuntimeError
                raise exception(reply["status"], reply["code"], reply["detail"])
            if reply["handle"]:
                return self.handles.setdefault(reply["handle"], object())
            return None

        return call

    def scan(self, scanner, repo):
        self.events.append(event("scan_inventory", self.operand(scanner), self.operand(repo)))
        return {}


def observe(request, directory):
    evidence = dict(events=[], commandAttempts=[], nativeAttempts=[], transactionSlots=[], bundleItems=[],
                    failure=dict(kind="", cause="", arguments=[]))
    try:
        match request["mode"]:
            case "commands":
                attempts = replay_history(Commands(evidence["events"]), directory, request["steps"])["attempts"]
                evidence["commandAttempts"] = [
                    dict(fields=sorted(attempt), length=attempt.get("length", 0), value=attempt.get("value", ""))
                    for attempt in attempts
                ]
            case "native":
                core = NativeProbe(directory, request["replies"], evidence["events"])
                history = replay_core.CoreHistory(core, "scanner", directory)
                try:
                    with patch.object(replay_core, "scan_inventory", core.scan):
                        for step in request["steps"]:
                            evidence["nativeAttempts"].append(
                                history.run(step["op"], *step["args"], include_error_detail=True),
                            )
                            evidence["transactionSlots"].append([
                                {"alias": alias, "handle": core.operand(handle)}
                                for alias, handle in history.values["txn"].items()
                            ])
                finally:
                    history.close()
            case "bundle":
                evidence["bundleItems"] = replay_core.bundle_items(bytes.fromhex("".join(request["bundle"])))
            case unknown:
                raise ValueError(f"unknown probe mode: {unknown}")
    except Exception as error:
        evidence["failure"] = dict(kind=type(error).__name__,
                                   cause=type(error.__cause__).__name__ if error.__cause__ else "",
                                   arguments=[str(arg).split() for arg in error.args])
    return evidence


def main():
    requests = json.load(sys.stdin)
    with TemporaryDirectory(prefix="dml-interpreter-dispatch-") as tmp:
        directory = Path(tmp)
        evidence = [observe(request, directory / f"history-{index}") for index, request in enumerate(requests, 1)]
    json.dump(evidence, sys.stdout)
    print()


if __name__ == "__main__":
    main()
