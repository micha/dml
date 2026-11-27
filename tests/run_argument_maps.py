"""Observe the recorded argument-map CLI and independent native inventory for Quint."""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from daggerml import core

from replay_core import WORKFLOW_NATIVE_DEFAULTS, WorkflowNative
from run_histories import (
    absolute_path,
    add_quint_arguments,
    check_verdicts,
    evaluate,
    quint_command,
    read_histories,
    replay_history,
)
from trace_support import scan_inventory


COMMIT_PREFIX = b"objects/commits/".hex()
REF_PREFIX = b"refs/heads/".hex()
RECEIPT = re.compile(r"@([a-z][a-z0-9-]*)")


def observations(inventory):
    def record(kind, identifier):
        key = (b"objects/" + kind + identifier.hex().encode("ascii")).hex()
        return core.object_decode(bytes.fromhex(inventory[key]))

    counts = dict(requests=0, executions=0, results=0, accesses=0)
    for key, packed in inventory.items():
        if not key.startswith(COMMIT_PREFIX):
            continue
        _, tree, _ = core.object_decode(bytes.fromhex(packed))
        view, _, size = record(b"trees/", tree)
        for i in range(size):
            dag, name = core.object_view_entry(view, i)
            if name == b"argument-map-request-v1":
                counts["requests"] += 1
            elif name == b"argument-map-attempt-v1":
                counts["executions"] += 1
            elif name == b"argument-map-result-v1":
                counts["results"] += 1
                counts["accesses"] += record(b"dags/", dag)[2]
    return {**counts, "refs": [{"name": bytes.fromhex(key[len(REF_PREFIX):]).decode("ascii"), "target": value}
                               for key, value in sorted(inventory.items()) if key.startswith(REF_PREFIX)]}


def report_evidence(report):
    requested = report.get("requested", {})
    producing = report.get("producing", {})
    gets = report.get("map_gets", [])
    # Keep the complete inspection comparable as well as exposing fields for semantic checks.
    digest = hashlib.sha256(json.dumps(report, sort_keys=True).encode("utf-8")).hexdigest() if report else ""
    return {"reportDigest": digest, "intent": report.get("intent", ""),
            "entries": [{"key": key, "attempt": attempt} for key, attempt in report.get("entries", {}).items()],
            "request": requested.get("request", ""), "input": requested.get("argument_map", ""),
            "construction": requested.get("construction", ""), "implementation": requested.get("implementation", ""),
            "sources": [arg["attempt"] for arg in requested.get("arguments", [])],
            "keyHex": [arg["key"].encode("utf-8").hex() for arg in requested.get("arguments", [])],
            "producingRequest": producing.get("request", ""), "producingInput": producing.get("argument_map", ""),
            "producingConstruction": producing.get("construction", ""),
            "producingImplementation": producing.get("implementation", ""),
            "attempt": report.get("attempt", ""), "result": report.get("result", ""), "value": report.get("value", 0),
            "gets": [arg["key"] for arg in gets], "getSources": [arg["attempt"] for arg in gets],
            "outcome": report.get("outcome", ""), "table": report.get("table", "")}


class History:
    def __init__(self, directory, example, scanner):
        self.directory = directory
        self.example = example
        self.scanner = scanner
        self.receipts = {}
        self.argument_maps = {}
        self.operations = {
            **{op: self.command(op) for op in ("request", "work", "define_table", "update_table", "inspect")},
            "replicate": self.replicate,
        }

    def inventory(self, repo):
        return scan_inventory(self.scanner, repo) if (repo / "data.mdb").is_file() else {}

    def evidence(self, op, args, output, code, stderr, before, after):
        report = json.loads(output) if op == "inspect" and output else {}
        commit = report.get("commit", output.strip() if not report else "")
        if commit and not re.fullmatch(r"[0-9a-f]{32}", commit):
            raise ValueError(f"expected a commit ID in CLI output, got {commit!r}")
        native = observations(after)
        if args[0] == "source":
            if op == "inspect" and "producing" in report:
                self.argument_maps[args[1]] = report["producing"]["argument_map"]
            for entry in native["refs"]:
                self.receipts.setdefault(entry["name"], entry["target"])
        command = op.replace("_", "-")
        if stderr:
            print(stderr, file=sys.stderr, end="")
        return {"op": op, "args": list(args), "code": code, "quiet": not stderr,
                "diagnosed": stderr.startswith(f"{command}: ") and "Traceback" not in stderr,
                "error": stderr.rstrip("\n"), "commit": commit, "unchanged": before == after,
                **report_evidence(report), **native}

    def cli_args(self, args):
        argv = []
        for i, arg in enumerate(args):
            if arg.startswith("map-of:"):
                argv.append(self.argument_maps[arg.removeprefix("map-of:")])
                continue
            value = RECEIPT.sub(lambda match: self.receipts[match[1]], arg)
            if i > 0 and args[i - 1] == "--arg" and value.startswith("key-hex:"):
                key, separator, descriptor = value.removeprefix("key-hex:").partition("=")
                value = bytes.fromhex(key).decode("utf-8") + separator + descriptor
            argv.append(value)
        return argv

    def command(self, op):
        def invoke(role, *args):
            repo = self.directory / role
            before = self.inventory(repo)
            argv = self.cli_args(args)
            process = subprocess.run([sys.executable, "-B", self.example, op.replace("_", "-"), repo, *argv],
                                     cwd=self.directory, capture_output=True, text=True, encoding="utf-8", timeout=30)
            return self.evidence(op, (role, *args), process.stdout, process.returncode, process.stderr, before,
                                 self.inventory(repo))
        return invoke

    def replicate(self, role, receipt, pin):
        commit = bytes.fromhex(self.receipts[receipt])
        source = core.repo_open(self.directory / "source", False)
        try:
            bundle = core.repo_export_commit(source, commit)
        finally:
            core.repo_close(source)
        repo = self.directory / role
        before = self.inventory(repo)
        destination = core.repo_open(repo, True)
        try:
            imported = core.repo_import_commit_staged(destination, bundle, pin.encode("ascii"))
        finally:
            core.repo_close(destination)
        return self.evidence("replicate", (role, receipt, pin), imported.hex(), 0, "", before, self.inventory(repo))


NATIVE_ATTEMPT_DEFAULTS = {
    "op": "", "args": [], "code": 0, "quiet": True, "diagnosed": False, "error": "", "commit": "",
    "unchanged": False, "addedRefs": [], "removedRefs": [], "requests": 0, "executions": 0,
    "results": 0, "accesses": 0, **report_evidence({}), **WORKFLOW_NATIVE_DEFAULTS,
}


class NativeHistory(History):
    def __init__(self, directory, example, scanner):
        super().__init__(directory, example, scanner)
        self.native = WorkflowNative(core, directory)
        self.operations["native"] = self.native_step

    def native_step(self, op, *args):
        return {**NATIVE_ATTEMPT_DEFAULTS, **self.native.run(op, *args)}

    def inventory(self, repo):
        self.native.require_closed()
        return super().inventory(repo)

    def evidence(self, op, args, output, code, stderr, before, after):
        row = super().evidence(op, args, output, code, stderr, before, after)
        del row["refs"]

        def ref_changes(old, new):
            return [{"name": bytes.fromhex(key[len(REF_PREFIX):]).decode("ascii"), "target": new[key]}
                    for key in sorted(new) if key.startswith(REF_PREFIX) and new[key] != old.get(key)]

        # Keep ref deltas rather than copying every old pin at every link of a long walk.
        return {**row, "addedRefs": ref_changes(before, after), "removedRefs": ref_changes(after, before),
                **WORKFLOW_NATIVE_DEFAULTS}


class Processes:
    def __init__(self, example, scanner, native):
        self.example = example
        self.scanner = scanner
        self.native = native

    @contextmanager
    def history(self, directory):
        if self.native:
            history = NativeHistory(directory, self.example, self.scanner)
            with history.native:
                yield history
        else:
            yield History(directory, self.example, self.scanner)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    parser.add_argument("--native", action="store_true", help="enable single-call native steps and ref deltas")
    for name in ("example", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-argument-maps-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        processes = Processes(args.example, args.scanner, args.native)
        evidence = [{**replay_history(processes, directory / f"history-{i}", history), "scenario": i}
                    for i, history in enumerate(histories)]
        # Full native ref snapshots overlap heavily across adjacent steps.
        state = evaluate(quint, args.rules, directory, evidence, [args.histories],
                         intern_refs=not args.native, attempt_defaults=NATIVE_ATTEMPT_DEFAULTS if args.native else None)
        check_verdicts(histories, evidence, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"argument-map replay failed: {error}") from error
