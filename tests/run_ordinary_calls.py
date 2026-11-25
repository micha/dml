"""Collect CLI and independent native evidence for captured ordinary calls."""

import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from daggerml import core

from run_builtins import READ_ONLY
from run_closures import Inventory as ClosureInventory, contents, replacement_dag, snapshot
from run_composition import IDENTITY, OBJECT_PREFIX, RECEIPT, parents, replace_parents, repository
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


PREFIX, SUFFIX = "ordinary-example-", "-v1"
NO_MAP = {"dag": "", "datum": "", "sources": [], "args": []}
NO_RETURN = {"dag": "", "inputs": "", "returned": "", "value": 0, "trace": []}
NO_ENV = {"dag": "", "map": "", "mapSource": "", "list": "", "listSource": "",
          "add": "", "addMap": "", "double": "", "doubleMap": ""}
EMPTY = {"op": "", "args": [], "commit": "", "code": 0, "error": "", "head": "", "main": "",
         "refs": [], "created": [], "profiles": [], "report": [], "unchanged": True, "preserved": True,
         "transfer": False}


class Inventory(ClosureInventory):
    """Interpret packed records and named links without using the example or Inspector."""

    def read_environment(self, txn, dag):
        getter = self.link(txn, dag, b"map-get")
        list_getter = self.link(txn, dag, b"list-get")
        add = self.link(txn, dag, b"add")
        double = self.link(txn, dag, b"double")
        return {"dag": dag.hex(), "map": getter.hex(), "mapSource": self.binding_source(txn, getter),
                "list": list_getter.hex(), "listSource": self.binding_source(txn, list_getter),
                "add": add.hex(), "addMap": self.link(txn, add, b"map-get").hex(),
                "double": double.hex(), "doubleMap": self.link(txn, double, b"map-get").hex()}

    def read_map_view(self, txn, dag):
        view = self.read_map(txn, dag)
        return {"dag": view["inputs"], "datum": view["map"], "sources": view["sources"], "args": view["args"]}

    def read_trace_view(self, txn, dag):
        calls, bindings, keys, values = self.trace(txn, dag)
        return [{"dag": call["operation"], "func": call["func"], "binding": binding,
                 "source": call["binding"], "map": next(e["dag"] for e in call["sources"] if e["name"] == "map"),
                 "key": key, "value": value}
                for call, binding, key, value in zip(calls, bindings, keys, values, strict=True)]

    def read_return_view(self, txn, dag):
        return {"dag": dag.hex(), "inputs": self.link(txn, dag, b"inputs").hex(),
                "returned": self.link(txn, dag, b"returned").hex(), "value": self.i64(txn, dag, b"value"),
                "trace": self.read_trace_view(txn, self.link(txn, dag, b"trace"))}

    def read_commit(self, identifier, txn):
        commit = bytes.fromhex(identifier)
        dag, name = contents(txn, commit)
        entry = name.decode("ascii")
        if not entry.startswith(PREFIX) or not entry.endswith(SUFFIX):
            raise ValueError(f"unexpected ordinary call entry {entry}")
        role = entry[len(PREFIX):-len(SUFFIX)]
        row = {"id": identifier, "role": role, "dag": dag.hex(), "parents": [p.hex() for p in parents(txn, commit)],
               "env": NO_ENV, "inputs": NO_MAP, "target": "", "selected": "", "doubleSelected": "",
               "mode": "", "doubleMode": "", "invocation": "", "attempt": "", "result": NO_RETURN,
               "trace": []}
        if role == "defaults":
            row.update(env=self.read_environment(txn, dag))
        elif role == "capture":
            row.update(env=self.read_environment(txn, self.link(txn, dag, b"environment")))
        elif role in ("outer-request", "add-request", "double-request"):
            row.update(inputs=self.read_map_view(txn, self.link(txn, dag, b"inputs")),
                       invocation=self.string(txn, dag, b"invocation"))
            if role == "outer-request":
                row.update(selected=self.string(txn, dag, b"selected"),
                           doubleSelected=self.string(txn, dag, b"double-selected"),
                           mode=self.string(txn, dag, b"mode"), doubleMode=self.string(txn, dag, b"double-mode"))
            else:
                row.update(target=self.link(txn, dag, b"target").hex())
        elif role == "start":
            row.update(attempt=self.string(txn, dag, b"attempt"))
        elif role in ("add-attempt", "double-attempt"):
            row.update(attempt=self.string(txn, dag, b"attempt"),
                       result=self.read_return_view(txn, self.link(txn, dag, b"result")))
            if role == "add-attempt":
                row.update(trace=self.read_trace_view(txn, self.link(txn, dag, b"trace")))
        elif role == "finished":
            row.update(result=self.read_return_view(txn, dag))
        return row


def flat_report(report, path="", name=""):
    scope = f"{path}/{name}" if name else path
    if isinstance(report, dict):
        return [item for key, value in sorted(report.items()) for item in flat_report(value, scope, key)]
    if isinstance(report, list):
        return [item for index, value in enumerate(report) for item in flat_report(value, scope, str(index))]
    return [{"path": path, "name": name, "value": str(report)}]


def wrong_inputs(txn, request, from_request):
    own_dag, _ = contents(txn, request)
    wrong_dag, _ = contents(txn, from_request)
    old_input = core.txn_lookup_node(txn, wrong_dag, b"inputs")
    names = (b"role", b"invocation", b"target", b"inputs")
    forged = replacement_dag(txn, own_dag, names, b"inputs", old_input)
    return snapshot(txn, request, forged, *parents(txn, request))


def graft_finished(txn, inner_hit, _):
    (hit,) = parents(txn, inner_hit)
    own_request, selected = parents(txn, hit)
    (old_request,) = parents(txn, selected)
    wrong_request = wrong_inputs(txn, own_request, old_request)
    wrong_hit = replace_parents(txn, hit, wrong_request, selected)
    return replace_parents(txn, inner_hit, wrong_hit)


def graft_double(txn, old_double, inner_hit):
    (hit,) = parents(txn, inner_hit)
    alternate_request, _ = parents(txn, hit)
    (old_request,) = parents(txn, old_double)
    wrong_request = wrong_inputs(txn, old_request, alternate_request)
    return replace_parents(txn, old_double, wrong_request)


class History:
    def __init__(self, directory, script, scanner):
        self.directory = directory
        self.script = script
        self.scanner = scanner
        self.receipts = {}
        self.operations = {op: self.command(op) for op in ("defaults", "capture", "invoke", "select_double", "inspect")}
        self.operations.update(replicate=self.replicate, retire=self.retire, graft=self.graft)

    def inventory(self, path):
        if not (path / "data.mdb").is_file():
            return Inventory({})
        rows = scan_inventory(self.scanner, path)
        with repository(path) as repo:
            txn = core.txn_begin(repo, core.TXN_READ)
            try:
                return Inventory(rows, txn)
            finally:
                core.txn_abort(txn)

    def evidence(self, op, args, before, after, *, commit="", head="", report=None, code=0, error="", transfer=False):
        if commit and not IDENTITY.fullmatch(commit):
            raise ValueError(f"expected a commit ID, got {commit!r}")
        for name, target in after.refs.items():
            self.receipts.setdefault(name, target)
        if op == "defaults" and head:
            self.receipts[args[1]] = head
        refs = [{"name": name, "before": before.refs.get(name, ""), "after": after.refs.get(name, "")}
                for name in sorted(before.refs.keys() | after.refs.keys())
                if before.refs.get(name, "") != after.refs.get(name, "")]
        preserved = all(after.rows.get(key) == value for key, value in before.rows.items() if key.startswith(OBJECT_PREFIX))
        return {"op": op, "args": list(args), "commit": commit, "code": code, "error": error,
                "head": head, "main": after.refs.get("main", ""), "refs": refs,
                "created": [after.commits[key] for key in sorted(after.commits.keys() - before.commits.keys())],
                "profiles": after.added_builtin_profiles(before), "report": flat_report(report or {}),
                "unchanged": before.rows == after.rows, "preserved": preserved, "transfer": transfer}

    def command(self, op):
        def invoke(role, *args):
            path = self.directory / role
            before = self.inventory(path)
            argv = [RECEIPT.sub(lambda match: self.receipts[match[1]], arg) for arg in args]
            wrapper = ["-c", READ_ONLY] if op == "inspect" else []
            process = subprocess.run([sys.executable, "-B", *wrapper, self.script, op.replace("_", "-"), path, *argv],
                                     cwd=self.directory, capture_output=True, text=True, encoding="utf-8", timeout=30)
            output = process.stdout.strip()
            report = json.loads(output) if op == "inspect" and output else None
            after = self.inventory(path)
            ref = args[2] if op in ("capture", "invoke", "select_double") else args[0]
            return self.evidence(op, (role, *args), before, after, commit=report["commit"] if report else output,
                                 head=after.refs.get(ref, ""), report=report, code=process.returncode,
                                 error=process.stderr.strip())
        return invoke

    def graft(self, role, kind, from_ref, alternate_ref, output):
        path = self.directory / role
        before = self.inventory(path)
        with repository(path) as repo:
            txn = core.txn_begin(repo, core.TXN_WRITE)
            try:
                args = [bytes.fromhex(before.refs[ref]) if ref else None for ref in (from_ref, alternate_ref)]
                forge = {"finished": graft_finished, "double": graft_double}[kind]
                commit = forge(txn, *args)
                core.txn_ref_create(txn, output.encode("ascii"), commit)
                core.txn_commit(txn)
            finally:
                core.txn_abort(txn)
        return self.evidence("graft", (role, kind, from_ref, alternate_ref, output), before, self.inventory(path),
                             commit=commit.hex(), head=commit.hex())

    def replicate(self, role, receipt, pin):
        path = self.directory / role
        before = self.inventory(path)
        source_path = self.directory / "source"
        with repository(source_path) as source:
            bundle = core.repo_export_commit(source, bytes.fromhex(self.receipts[receipt]))
        with repository(path, create=True) as target:
            commit = core.repo_import_commit_staged(target, bundle, pin.encode("ascii"))
            exact = core.repo_export_commit(target, commit) == bundle
        source = self.inventory(source_path)
        after = self.inventory(path)
        exact = exact and all(source.rows.get(key) == value for key, value in after.rows.items()
                              if key.startswith(OBJECT_PREFIX))
        return self.evidence("replicate", (role, receipt, pin), before, after,
                             commit=commit.hex(), head=commit.hex(), transfer=exact)

    def retire(self, role):
        original = self.directory / role
        before = self.inventory(original)
        retired = original.rename(self.directory / "retired")
        return self.evidence("retire", (role,), before, self.inventory(retired), transfer=not original.exists())


class Processes:
    def __init__(self, script, scanner):
        self.script = script
        self.scanner = scanner

    def history(self, directory):
        return nullcontext(History(directory, self.script, self.scanner))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("script", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-ordinary-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        suite = Processes(args.script, args.scanner)
        observations = [replay_history(suite, directory / f"history-{i}", story) for i, story in enumerate(histories)]
        state = evaluate(quint, args.rules, directory, observations, [args.histories], attempt_defaults=EMPTY)
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"ordinary calls replay failed: {error}") from error
