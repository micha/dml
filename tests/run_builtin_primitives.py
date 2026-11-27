"""Replay requested built-in operations alongside single-call native steps."""

import argparse
from contextlib import ExitStack, contextmanager
from functools import partial
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from daggerml import builtin, core

from replay_core import DATUM_KINDS, CoreHistory
from run_histories import (
    absolute_path, add_quint_arguments, check_verdicts, evaluate, quint_command, read_histories, replay_history,
)
from trace_support import Replay, scan_inventory


DEFAULTS = dict(op="", args=[], status="ok", error="", value="", count=0, items=[],
                datumKind=0, datumPayload="", datum="", entries=[], sourceDag="", sourceNode="", name="",
                sourceUri="", binding="", func="", inputs="", returned="", trace=[], calls=[], events=[], unchanged=False)
INSPECTIONS = ("node", "binding", "arguments", "operation", "returned", "trace")
COMMANDS = (
    "native", "binding_put", "rec_new", "rec_enter", "rec_exit", "rec_source", "rec_literal",
    "rec_args", "rec_call", "rec_call_observed", "rec_ops", "rec_dag", "rec_trace", "rec_return",
    "ops_literal", "ops_map_get", "ops_list_get", "inspect", "inspect_offline", "checkpoint", "compare",
)


def value_fields(row, value):
    row.update(datumKind=value.kind, datumPayload=value.payload.hex())


def argument_entries(arguments):
    return [{"name": name.hex(), "id": source.dag.hex()} for name, source in arguments.entries]


def call_fields(op):
    return dict(func=op.func_uri.decode("ascii"), binding=op.binding.dag.hex(), sourceUri=op.binding.source_uri.decode("ascii"),
                inputs=op.arguments.dag.hex(), entries=argument_entries(op.arguments))


def description_fields(row, description):
    if isinstance(description, tuple):
        row["trace"] = [op.dag.hex() for op in description]
        return
    row["value"] = description.dag.hex()
    if isinstance(description, builtin.Binding):
        row["sourceUri"] = description.source_uri.decode("ascii")
        return
    value_fields(row, description.value)
    row["datum"] = description.datum.hex()
    if isinstance(description, builtin.LiteralSource):
        row.update(sourceDag=description.source_dag.hex(), sourceNode=description.source_node.hex(),
                   name=description.name.hex())
    elif isinstance(description, builtin.Arguments):
        row["entries"] = argument_entries(description)
    elif isinstance(description, builtin.Operation):
        row.update(call_fields(description))
    elif isinstance(description, builtin.Return):
        row.update(inputs=description.inputs.dag.hex(), returned=description.returned.dag.hex(),
                   trace=[op.dag.hex() for op in description.trace],
                   calls=[dict(dag=op.dag.hex(), **call_fields(op)) for op in description.trace])


class History:
    def __init__(self, scanner, directory):
        self.core = CoreHistory(core, None, directory, status_results=False)
        self.scanner = scanner
        self.recorders, self.scopes, self.nodes, self.ops, self.saved = {}, {}, {}, {}, {}

    def run(self, op, *args):
        row = {**DEFAULTS, "op": op, "args": list(args), "events": []}
        try:
            getattr(self, op)(row, *args)
        except core.Error as error:
            row.update(status=error.args[0], error=error.args[2])
        except (builtin.BuiltinError, TypeError, RuntimeError) as error:
            row.update(status=type(error).__name__, error=str(error))
        return row

    def native(self, row, op, *args):
        native = self.core.run(op, *args, include_error_detail=True)
        row.update(status=native["status"], error=native["detail"], value=native["value"],
                   count=native["count"], items=native["items"])

    def id(self, alias):
        return self.core.resolve("id", alias)

    def remember_id(self, row, alias, identifier):
        self.core.values["id"][alias] = identifier
        row["value"] = identifier.hex()

    def keep_node(self, row, alias, node):
        self.nodes[alias] = node
        value_fields(row, node.value)

    def typed(self, operand):
        if operand == "none":
            return None
        tag, value = operand.split(":", 1)
        if tag == "ids":
            return [self.id(alias) for alias in value.split(",")] if value else []
        if tag == "bool":
            return {"true": True, "false": False}[value]
        return {"int": int, "float": float, "text": str.encode, "hex": bytes.fromhex}[tag](value)

    def literal_value(self, kind, operand):
        value = self.typed(operand)
        if kind == "map":
            return list(zip(value[::2], value[1::2], strict=True))
        return value

    def binding_put(self, row, txn, uri, alias):
        self.remember_id(row, alias, builtin.put_binding(self.core.resolve("txn", txn), uri.encode("ascii")))

    def rec_new(self, row, txn, rec):
        self.recorders[rec] = builtin.Recorder(self.core.resolve("txn", txn))

    def rec_enter(self, row, rec):
        stack = self.scopes.get(rec, ExitStack())
        stack.enter_context(self.recorders[rec])
        self.scopes[rec] = stack

    def rec_exit(self, row, rec, message=None):
        with self.scopes.pop(rec):
            if message is not None:
                raise RuntimeError(message)

    def rec_literal(self, row, rec, kind, operand, alias):
        self.keep_node(row, alias, self.recorders[rec].literal(DATUM_KINDS[kind], self.literal_value(kind, operand)))

    def rec_source(self, row, rec, source, name, alias):
        self.keep_node(row, alias, self.recorders[rec].source(self.id(source), name.encode("utf-8")))

    def rec_args(self, row, rec, alias, *pairs):
        entries = [(self.typed(name), self.nodes[node]) for name, node in zip(pairs[::2], pairs[1::2], strict=True)]
        self.keep_node(row, alias, self.recorders[rec].arguments(entries))

    def rec_call(self, row, rec, func, binding, args, alias):
        result = self.recorders[rec].call(func.encode("ascii"), self.id(binding), self.nodes[args])
        self.keep_node(row, alias, result)

    def rec_call_observed(self, row, *args):
        # The two versions intentionally produce identical bytes. Observe entry,
        # not just the stored version label, while running the real handlers.
        def observe(name, handler, txn, operands):
            row["events"].append(name)
            return handler(txn, operands)

        with ExitStack() as stack:
            for name in ("_map_get_v1", "_map_get_v2"):
                stack.enter_context(patch.object(builtin, name, partial(observe, name, getattr(builtin, name))))
            self.rec_call(row, *args)

    def rec_ops(self, row, rec, map_binding, list_binding, alias):
        self.ops[alias] = self.recorders[rec].operations(map_binding=self.id(map_binding),
                                                         list_binding=self.id(list_binding))

    def rec_dag(self, row, rec, node, alias):
        self.remember_id(row, alias, self.recorders[rec].dag(self.nodes[node]))

    def rec_trace(self, row, rec, alias):
        self.remember_id(row, alias, self.recorders[rec].trace())

    def rec_return(self, row, rec, node, inputs, alias):
        self.keep_node(row, alias, self.recorders[rec].returned(self.nodes[node], inputs=self.nodes[inputs]))

    def ops_literal(self, row, ops, kind, operand, alias):
        self.keep_node(row, alias, self.ops[ops].literal(DATUM_KINDS[kind], self.literal_value(kind, operand)))

    def ops_map_get(self, row, ops, container, operand, alias):
        self.keep_node(row, alias, self.ops[ops].map_get(self.nodes[container], self.typed(operand)))

    def ops_list_get(self, row, ops, container, operand, alias):
        self.keep_node(row, alias, self.ops[ops].list_get(self.nodes[container], self.typed(operand)))

    def inspect(self, row, txn, method, dag):
        if method not in INSPECTIONS:
            raise ValueError(f"unknown Inspector operation {method}")
        inspector = builtin.Inspector(self.core.resolve("txn", txn))
        description_fields(row, getattr(inspector, method)(self.id(dag)))

    def inspect_offline(self, row, *args):
        def deny(name, *args, **kwargs):
            row["events"].append(name)
            raise RuntimeError(f"offline Inspector attempted {name}")

        with ExitStack() as stack:
            for obj, name in ((builtin.Recorder, "call"), (core, "txn_put_object"), (core, "txn_put_datum")):
                stack.enter_context(patch.object(obj, name, partial(deny, name)))
            self.inspect(row, *args)

    def inventory(self, repo):
        return scan_inventory(self.scanner, self.core.path(repo))

    def checkpoint(self, row, repo, alias):
        self.saved[alias] = self.inventory(repo)

    def compare(self, row, repo, alias):
        row["unchanged"] = self.inventory(repo) == self.saved[alias]


class Suite:
    def __init__(self, scanner):
        self.scanner = scanner

    @contextmanager
    def history(self, directory):
        history = History(self.scanner, directory)
        try:
            yield Replay({op: partial(history.run, op) for op in COMMANDS})
            if history.scopes or history.core.values["txn"] or history.core.values["repo"]:
                raise ValueError("end all recorder scopes and native handles before the history ends")
        finally:
            history.core.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    parser.add_argument("modules", type=absolute_path, nargs="*")
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-builtin-primitives-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        suite = Suite(args.scanner)
        observations = [{**replay_history(suite, directory / f"history-{i}", story), "scenario": i}
                        for i, story in enumerate(histories)]
        state = evaluate(quint, args.rules, directory, observations, [args.histories, *args.modules],
                         attempt_defaults=DEFAULTS)
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"builtin primitive replay failed: {error}") from error
