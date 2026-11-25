"""Collect native inventory and CLI evidence for the versioned builtin replay."""

import argparse
from contextlib import nullcontext
from importlib import import_module
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from daggerml import builtin, core

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
READ_ONLY = """
import runpy
from pathlib import Path
import sys

def audit(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.posix_spawn', 'os.system',
                 'socket.connect', 'socket.getaddrinfo'}:
        raise RuntimeError(f'offline reader attempted {event}')

sys.addaudithook(audit)
from daggerml import builtin, core

def deny(*args, **kwargs):
    raise RuntimeError('offline reader tried to author a record')

begin = core.txn_begin
core.txn_begin = lambda repo, mode: begin(repo, mode) if mode == core.TXN_READ else deny()
builtin.Recorder = deny
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(sys.argv[0]).parent))
runpy.run_path(sys.argv[0], run_name='__main__')
"""


def observations(inventory, example):
    count = {label: 0 for label in ("requests", "attempts", "results")}
    labels = {example.REQUEST: "requests", example.ATTEMPT: "attempts", example.RESULT: "results"}
    for key, packed in inventory.items():
        if key.startswith(COMMIT_PREFIX):
            _, tree, _ = core.object_decode(bytes.fromhex(packed))
            tree_key = (b"objects/trees/" + tree.hex().encode("ascii")).hex()
            view, _, size = core.object_decode(bytes.fromhex(inventory[tree_key]))
            for i in range(size):
                _, name = core.object_view_entry(view, i)
                if name in labels:
                    count[labels[name]] += 1
    refs = [{"name": bytes.fromhex(key[len(REF_PREFIX):]).decode("ascii"), "target": value}
            for key, value in sorted(inventory.items()) if key.startswith(REF_PREFIX)]
    return {**count, "refs": refs}


def report_fields(report):
    def request(key):
        row = report.get(key, {})
        return {"commit": row.get("request", ""), "inputs": row.get("inputs", ""),
                "source": row.get("source", ""), "value": row.get("argument_map", ""),
                "binding": row.get("binding", "")}

    trace = [{"dag": row["operation"], "func": row["func"], "binding": row["binding"],
              "args": row["inputs"], "value": row["datum"],
              "source": next((row["sources"][key] for key in ("map", "list") if key in row["sources"]), "")}
             for row in report.get("trace", [])]
    return {"requested": request("requested"), "producing": request("producing"), "trace": trace,
            "outcome": report.get("outcome", ""), "selection": report.get("selection", ""),
            "attempt": report.get("attempt", ""), "result": report.get("result", ""),
            "returned": report.get("returned", ""), "value": report.get("value", 0)}


class History:
    def __init__(self, directory, example, scanner):
        self.directory = directory
        self.example = example
        self.scanner = scanner
        self.receipts = {}
        self.operations = {op: self.command(op) for op in (
            "define_choice", "promote", "compatibility", "request", "work", "inspect")}
        self.operations.update(replicate=self.replicate, fixture=self.fixture)

    def inventory(self, repo):
        return scan_inventory(self.scanner, repo) if (repo / "data.mdb").is_file() else {}

    def evidence(self, op, args, before, after, output, report=None, error="", code=0):
        report = {} if report is None else report
        if output and not re.fullmatch(r"[0-9a-f]{32}", output):
            raise ValueError(f"expected a commit ID in CLI output, got {output!r}")
        native = observations(after, self.example)
        if args[0] == "source":
            for entry in native["refs"]:
                self.receipts.setdefault(entry["name"], entry["target"])
        if error:
            print(error, file=sys.stderr)
        return {"op": op, "args": list(args), "code": code, "error": error,
                "commit": output, "unchanged": before == after, **native, **report_fields(report)}

    def command(self, op):
        def invoke(role, *args):
            repo = self.directory / role
            before = self.inventory(repo)
            argv = [RECEIPT.sub(lambda match: self.receipts[match[1]], arg) for arg in args]
            mode = ["-c", READ_ONLY] if op == "inspect" else []
            command = op.replace("_", "-")
            process = subprocess.run([sys.executable, "-B", *mode, self.example.__file__, command, repo, *argv],
                                     cwd=self.directory, capture_output=True, text=True, encoding="utf-8", timeout=30)
            output = process.stdout.strip()
            report = json.loads(output) if op == "inspect" and output else None
            return self.evidence(op, (role, *args), before, self.inventory(repo),
                                 report["commit"] if report is not None else output,
                                 report, process.stderr.strip(), process.returncode)
        return invoke

    def replicate(self, role, receipt, pin):
        source_path = self.directory / "source"
        with self.example.records._repository(source_path, create=False) as source:
            bundle = core.repo_export_commit(source, bytes.fromhex(self.receipts[receipt]))
        target = self.directory / role
        before = self.inventory(target)
        with self.example.records._repository(target, create=True) as replica:
            commit = core.repo_import_commit_staged(replica, bundle, pin.encode("ascii"))
        source_path.rename(self.directory / "retired")
        return self.evidence("replicate", (role, receipt, pin), before, self.inventory(target), commit.hex())

    def fixture(self, role, name):
        """Create structurally valid but wrongly associated traces, only in the replica."""
        ex = self.example
        path = self.directory / role
        before = self.inventory(path)
        with ex.records._write_transaction(path, create=False) as txn:
            decision = core.txn_ref_get(txn, b"snapshot")
            _, (requested, historical) = ex._snapshot(txn, decision, ex.DECISION)
            inspector = builtin.Inspector(txn)
            produced = ex._read_attempt(txn, inspector, historical)
            new_map, list_binding, new_args = ex._read_request(txn, inspector, requested)
            used_map, used_args = ((produced.binding, new_args) if name == "source-graft"
                                  else (new_map, produced.args))
            with builtin.Recorder(txn) as recorder:
                owner = recorder.load(produced.args.dag)
                actual = recorder.load(used_args.dag)
                result = ex._first(actual, recorder.operations(map_binding=used_map.dag, list_binding=list_binding.dag))
                forged = recorder.dag(recorder.returned(result, inputs=owner))
            if name == "version-graft":
                # Hide the equal-valued v2 operation in the second getter's source;
                # the two visible trace positions still have the v1/list bindings.
                form = inspector.returned(forged)
                trace_role = ex.records._put_literal(txn, core.DATUM_STRING, b"builtin-trace-v1")
                trace = ex._put_dag(txn, trace_role, {b"role": trace_role,
                    b"call-00": ex._link(txn, produced.returned.trace[0].dag),
                    b"call-01": ex._link(txn, form.trace[1].dag)})
                value = ex.records._put_object(txn, core.REC_NODE, core.NODE_LITERAL, form.datum)
                return_role = ex.records._put_literal(txn, core.DATUM_STRING, b"builtin-return-v1")
                forged = ex._put_dag(txn, value, {b"role": return_role, b"value": value,
                    b"inputs": ex._link(txn, form.inputs.dag), b"returned": ex._link(txn, form.returned.dag),
                    b"trace": ex._link(txn, trace)})
            # Check this control really parses natively, returns the same value,
            # and carries the expected bindings before testing workflow rejection.
            actual = inspector.returned(forged)
            if (actual.datum != produced.returned.datum or actual.inputs != produced.args
                    or tuple(op.binding for op in actual.trace) != (produced.binding, list_binding)):
                raise ValueError("test fixture did not retain plausible produced value and bindings")
            result = ex.records._put_snapshot(txn, ex.RESULT, forged, produced.request)
            root = ex.records._put_literal(txn, core.DATUM_STRING, b"12345678-abcd-4abc-8abc-123456789abc")
            commit = ex.records._publish(txn, name.encode("ascii"), ex.ATTEMPT, ex._put_dag(txn, root, {}),
                                         produced.request, result)
        return self.evidence("fixture", (role, name), before, self.inventory(path), commit.hex())


class Processes:
    def __init__(self, example, scanner):
        self.example = example
        self.scanner = scanner

    def history(self, directory):
        return nullcontext(History(directory, self.example, self.scanner))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("example", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.example.parent))
    example = import_module(args.example.stem)
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-builtins-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        processes = Processes(example, args.scanner)
        evidence = [{**replay_history(processes, directory / f"history-{i}", story), "scenario": i}
                    for i, story in enumerate(histories)]
        state = evaluate(quint, args.rules, directory, evidence, [args.histories])
        check_verdicts(histories, evidence, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"builtin replay failed: {error}") from error
