"""Collect CLI, in-process, and independent native evidence for captured ordinary calls."""

import argparse
from collections import deque
from contextlib import ExitStack, contextmanager
from functools import partial
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

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
    replay_step,
)
from trace_support import scan_inventory


PREFIX, SUFFIX = "ordinary-example-", "-v1"
NO_MAP = {"dag": "", "datum": "", "sources": [], "args": []}
NO_RETURN = {"dag": "", "inputs": "", "returned": "", "value": 0, "trace": []}
NO_ENV = {"dag": "", "map": "", "mapSource": "", "list": "", "listSource": "",
          "add": "", "addMap": "", "double": "", "doubleMap": ""}
EMPTY = {"op": "", "args": [], "commit": "", "code": 0, "error": "", "head": "", "main": "",
         "refs": [], "created": [], "profiles": [], "report": [], "unchanged": True, "preserved": True,
         "transfer": False, "addedObjects": False, "calls": []}
EDITOR_OPS = {"txn_begin", "txn_ref_update", "txn_commit"}


class CallTrace:
    """Give each observed object a token on first sight, without comparing values."""

    def __init__(self):
        self.events = []
        self._objects = []

    def token(self, obj):
        for index, observed in enumerate(self._objects):
            if obj is observed:
                return index
        self._objects.append(obj)  # Keep objects alive across the whole observation.
        return len(self._objects) - 1

    def record(self, op, *objects, labels=()):
        self.events.append({"op": op, "handles": [self.token(obj) for obj in objects], "labels": list(labels)})

    @contextmanager
    def adapters(self, example):
        with patch.object(example, "_double_sum", self.outer(example._double_sum)), \
                patch.object(example, "_leaf_call", self.leaf(example._leaf_call)):
            yield

    def outer(self, adapter):
        def observe(arguments, get, make_arguments, invoke, add, double):
            def observed_map(entries):
                self.record("make-arguments", *entries.values(), labels=(key.decode("ascii") for key in entries))
                result = make_arguments(entries)
                self.record("arguments-return", result)
                return result

            def observed_invoke(target, node):
                self.record("invoke", target, node)
                result = invoke(target, node)
                self.record("invoke-return", result)
                return result

            self.record("outer", arguments, add, double)
            result = adapter(arguments, get, observed_map, observed_invoke, add, double)
            self.record("outer-return", result)
            return result

        return observe

    def leaf(self, adapter):
        def observe(kind, arguments, ops):
            self.record("leaf", labels=(kind.decode("ascii"),))
            return adapter(kind, arguments, ops)

        return observe


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
        self.operations.update(replicate=self.replicate, retire=self.retire, graft=self.graft,
                               invoke_observed=self.invoke_observed, inspect_observed=self.inspect_observed)

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

    def evidence(self, op, args, before, after, *, commit="", head="", report=None, code=0, error="",
                 transfer=False, remember=True, calls=()):
        if commit and not IDENTITY.fullmatch(commit):
            raise ValueError(f"expected a commit ID, got {commit!r}")
        if remember:
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
                "unchanged": before.rows == after.rows, "preserved": preserved, "transfer": transfer,
                "addedObjects": any(key.startswith(OBJECT_PREFIX) for key in after.rows.keys() - before.rows.keys()),
                "calls": list(calls)}

    def resolve(self, arg):
        return RECEIPT.sub(lambda match: self.receipts[match[1]], arg)

    def command(self, op):
        def invoke(role, *args):
            path = self.directory / role
            before = self.inventory(path)
            argv = [self.resolve(arg) for arg in args]
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

    def invoke_observed(self, role, capture, expected, output, a, b, *selection):
        example = import_module(self.script.stem)
        path = self.directory / role
        before = self.inventory(path)
        trace = CallTrace()
        outer = example.Selection()
        if selection:
            mode, ref, selected = selection
            outer = example.Selection(mode.encode("ascii"), ref.encode("ascii"), bytes.fromhex(self.resolve(selected)))
        commit, code, error = "", 0, ""
        with trace.adapters(example):
            try:
                commit = example.invoke(path, capture.encode("ascii"), bytes.fromhex(self.resolve(expected)),
                                        output.encode("ascii"), int(a), int(b), outer=outer).hex()
            except (ValueError, OverflowError, core.Error) as failure:
                code, error = 1, str(failure)
        after = self.inventory(path)
        return self.evidence("invoke_observed", (role, capture, expected, output, a, b, *selection), before, after,
                             commit=commit, head=after.refs.get(output, ""), code=code, error=error,
                             calls=trace.events)

    def inspect_observed(self, role, ref, expected):
        example = import_module(self.script.stem)
        path = self.directory / role
        before = self.inventory(path)
        trace = CallTrace()
        report, code, error = None, 0, ""
        with trace.adapters(example):
            try:
                report = example.inspect(path, ref.encode("ascii"), expected=bytes.fromhex(self.resolve(expected)))
            except (ValueError, OverflowError, core.Error) as failure:
                code, error = 1, str(failure)
        after = self.inventory(path)
        return self.evidence("inspect_observed", (role, ref, expected), before, after,
                             commit=report["commit"] if report is not None else "", head=after.refs.get(ref, ""),
                             report=report, code=code, error=error, calls=trace.events)

    def invoke_live(self, actor, role, capture, expected, output, a, b, mode, selected_ref, selected,
                    *, interleaving, editor_rows):
        example = import_module(self.script.stem)
        path = self.directory / role
        before = self.inventory(path)
        outer = example._double_sum

        def observe(arguments, get, make_arguments, invoke, add, double):
            def observed_invoke(target, node):
                result = invoke(target, node)
                if target is add:
                    # The real add has closed its batch. Double's batch has not opened yet.
                    editor_rows.extend(self.edit_bookmark(path, output, before, interleaving))
                return result

            return outer(arguments, get, make_arguments, observed_invoke, add, double)

        controls = example.Selection(mode.encode("ascii"), selected_ref.encode("ascii"),
                                     bytes.fromhex(self.resolve(selected)))
        commit, code, error = "", 0, ""
        with patch.object(example, "_double_sum", observe):
            try:
                commit = example.invoke(path, capture.encode("ascii"), bytes.fromhex(self.resolve(expected)),
                                        output.encode("ascii"), int(a), int(b), double=controls).hex()
            except (ValueError, OverflowError, core.Error) as failure:
                code, error = 1, str(failure)
        after = self.inventory(path)
        args = (actor, role, capture, expected, output, a, b, mode, selected_ref, selected)
        return self.evidence("invoke_live", args, before, after, commit=commit, head=after.refs.get(output, ""),
                             code=code, error=error)

    def edit_bookmark(self, path, output, before, interleaving):
        prefix = self.inventory(path)
        active = None
        with ExitStack() as resources:
            for request in interleaving:
                op = request["op"]
                args = request["args"]
                actor, handle, *operands = args
                if op == "txn_begin" and active is None:
                    (role,) = operands
                    edit_path = self.directory / role
                    repo = resources.enter_context(repository(edit_path))
                    txn = core.txn_begin(repo, core.TXN_WRITE)
                    resources.callback(core.txn_abort, txn)
                    active = (actor, handle)
                    yield self.evidence(op, args, before, prefix, head=prefix.refs.get(output, ""), remember=False)
                elif op == "txn_ref_update" and active == (actor, handle):
                    ref, target = operands
                    commit = self.resolve(target)
                    core.txn_ref_update(txn, ref.encode("ascii"), bytes.fromhex(commit))
                    yield {**EMPTY, "op": op, "args": args, "commit": commit,
                           "unchanged": scan_inventory(self.scanner, path) == prefix.rows}
                elif op == "txn_commit" and active == (actor, handle) and not operands:
                    core.txn_commit(txn)
                    resources.close()
                    active = None
                    after = self.inventory(path)
                    yield self.evidence(op, args, prefix, after, head=after.refs.get(output, ""), remember=False)
                else:
                    raise RuntimeError(f"invalid bookmark editor step: {request}")

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


def replay_ordinary(directory, script, scanner, requests):
    directory.mkdir()
    replay = History(directory, script, scanner)
    attempts = []
    pending = deque(enumerate(requests, 1))
    while pending:
        step, request = pending.popleft()
        if request["op"] == "invoke_live":
            # Schedule the contiguous editor steps at the live call's after-add checkpoint.
            interleaving, editor_rows = [], []
            while pending and pending[0][1]["op"] in EDITOR_OPS:
                _, edit = pending.popleft()
                interleaving.append(edit)
            invoke = partial(replay.invoke_live, interleaving=interleaving, editor_rows=editor_rows)
            attempts.append(replay_step({"invoke_live": invoke}, directory, step, request))
            attempts.extend(editor_rows)
        else:
            attempts.append(replay_step(replay.operations, directory, step, request))
    return {"attempts": attempts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("script", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    sys.path.insert(0, str(args.script.parent))
    with TemporaryDirectory(prefix="dml-ordinary-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        observations = [replay_ordinary(directory / f"history-{i}", args.script, args.scanner, story)
                        for i, story in enumerate(histories)]
        state = evaluate(quint, args.rules, directory, observations, [args.histories], attempt_defaults=EMPTY)
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"ordinary calls replay failed: {error}") from error
