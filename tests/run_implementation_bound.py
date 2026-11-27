"""Collect live implementation-bound CLI, call-facade and native graph evidence."""

import argparse
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from importlib import import_module
from io import StringIO
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from daggerml import calls, core

from run_composition import repository
from run_histories import (
    absolute_path,
    add_quint_arguments,
    check_verdicts,
    evaluate,
    quint_command,
    read_histories,
    replay_history,
)
from run_ordinary_calls import EMPTY, History, Inventory
from trace_support import scan_inventory


class BoundInventory(Inventory):
    """Read each native closure independently of daggerml.calls and the example reader."""

    def __init__(self, rows, txn=None):
        self.closures = {}
        super().__init__(rows, txn)

    def describe_closure(self, txn, dag, names):
        _, root, fields = core.object_decode(self.packed(b"dags", dag))
        return {"dag": dag.hex(), "fields": fields, "roleAtRoot": root == self.node(txn, dag, b"role"),
                "role": self.literal(root, core.DATUM_STRING).decode("ascii"),
                "intent": self.uri(txn, dag, b"intent"), "implementation": self.uri(txn, dag, b"implementation"),
                "links": [{"name": name.decode("ascii"), "dag": self.link(txn, dag, name).hex()} for name in names]}

    def read_environment(self, txn, dag):
        env = super().read_environment(txn, dag)
        for identifier, names in (
            (env["dag"], (b"add", b"double", b"list-get", b"map-get")),
            (env["add"], (b"list-get", b"map-get")),
            (env["double"], (b"list-get", b"map-get")),
        ):
            if identifier not in self.closures:
                self.closures[identifier] = self.describe_closure(txn, bytes.fromhex(identifier), names)
        return env

    def read_commit(self, identifier, txn):
        row = super().read_commit(identifier, txn)
        if row["role"] == "implementation-defaults":
            row["env"] = self.read_environment(txn, bytes.fromhex(row["dag"]))
        return row


class AdapterTrace:
    """Observe real CLI execution; record nesting, not identities or expected outcomes."""

    def __init__(self):
        self.events = []
        self.depth = 0

    def record(self, op, labels=()):
        self.events.append({"op": op, "handles": [self.depth], "labels": list(labels)})

    def invoke(self, dispatch):
        def observe(scope, target, arguments):
            self.record("scope-invoke")
            self.depth += 1
            try:
                return dispatch(scope, target, arguments)
            finally:
                self.depth -= 1

        return observe

    def outer(self, adapter):
        def observe(*args, **kwargs):
            self.record("outer-adapter")
            return adapter(*args, **kwargs)

        return observe

    def leaf(self, adapter):
        def observe(kind, *args, **kwargs):
            self.record("leaf-adapter", (kind.decode("ascii"),))
            return adapter(kind, *args, **kwargs)

        return observe


class BoundHistory(History):
    def __init__(self, directory, script, scanner):
        super().__init__(directory, script, scanner)
        self.closures = {}
        self.operations["invoke_observed"] = self.invoke_observed

    def inventory(self, path):
        if not (path / "data.mdb").is_file():
            return BoundInventory({})
        rows = scan_inventory(self.scanner, path)
        with repository(path) as repo:
            txn = core.txn_begin(repo, core.TXN_READ)
            try:
                result = BoundInventory(rows, txn)
            finally:
                core.txn_abort(txn)
        self.closures.update(result.closures)
        return result

    def invoke_observed(self, role, *args):
        example = import_module(self.script.stem)
        path = self.directory / role
        before = self.inventory(path)
        trace = AdapterTrace()
        output, diagnostics = StringIO(), StringIO()
        argv = [str(self.script), "invoke", str(path), *(self.resolve(arg) for arg in args)]
        code = 0
        with (patch.object(sys, "argv", argv), redirect_stdout(output), redirect_stderr(diagnostics),
              patch.object(calls.Scope, "invoke", trace.invoke(calls.Scope.invoke)),
              patch.object(example, "_double_sum", trace.outer(example._double_sum)),
              patch.object(example, "_leaf_call", trace.leaf(example._leaf_call))):
            try:
                example.main()
            except SystemExit as error:
                if isinstance(error.code, str):
                    print(error.code, file=sys.stderr)
                    code = 1
                else:
                    code = error.code or 0
        after = self.inventory(path)
        return self.evidence("invoke_observed", (role, *args), before, after, commit=output.getvalue().strip(),
                             head=after.refs.get(args[2], ""), code=code, error=diagnostics.getvalue().strip(),
                             calls=trace.events)

    def history(self, _directory):
        return nullcontext(self)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("script", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    sys.path.insert(0, str(args.script.parent))
    with TemporaryDirectory(prefix="dml-implementation-bound-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        evidence = []
        for index, history in enumerate(histories):
            path = directory / f"history-{index}"
            replay = BoundHistory(path, args.script, args.scanner)
            row = replay_history(replay, path, history)
            evidence.append({**row, "closures": [replay.closures[dag] for dag in sorted(replay.closures)]})
        validation = evaluate(quint, args.rules, directory, evidence,
                              [args.histories, *(Path(__file__).with_name(f"ordinary_{name}.qnt")
                                                 for name in ("histories", "rules"))], attempt_defaults=EMPTY)
        check_verdicts(histories, evidence, validation)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"implementation-bound replay failed: {error}") from error
