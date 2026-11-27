"""Collect live CLI and independent native observations for closure replay."""

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from daggerml import core

from replay_core import WORKFLOW_NATIVE_DEFAULTS, WorkflowNative
from run_builtins import READ_ONLY
from run_composition import (
    IDENTITY,
    OBJECT_PREFIX,
    RECEIPT,
    Inventory as CompositionInventory,
    parents,
    put,
    record_view,
    replace_parents,
    repository,
)
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


ROLE_PREFIX = "closure-example-"
ROLES = ("defaults", "closure", "request", "decision", "attempt", "result")
NO_ENV = {"environment": "", "mapBinding": "", "mapSource": "", "listBinding": "", "listSource": "",
          "scaleSource": "", "scaleOrigin": "", "scale": 0}
NO_CAPTURE = {**NO_ENV, "closure": "", "descriptor": "", "defaults": "", "captureKey": "", "func": "",
              "implementation": ""}
NO_Q = {"request": "", "func": "", "inputs": "", "map": "", "sources": [], "capture": NO_CAPTURE}
CAPTURE_NAMES = {
    "captureKey": "capture_key", "mapBinding": "map_binding", "mapSource": "map_source",
    "listBinding": "list_binding", "listSource": "list_source", "scaleSource": "scale_source",
    "scaleOrigin": "scale_origin",
}
CAPTURE_FIELDS = (b"role", b"func", b"implementation", b"environment", b"capture-key")
ENV_FIELDS = (b"role", b"map-get", b"list-get", b"scale")
Q_FIELDS = (b"func", b"invocation", b"closure", b"inputs")
D_FIELDS = (b"outcome", b"request", b"selection")


def text(value):
    return value.decode("ascii")


def source_edges(sources):
    return [{"name": name, "dag": dag} for name, dag in sorted(sources.items())]


def q_report(report):
    if not report:
        return NO_Q
    capture = {name: report["capture"][CAPTURE_NAMES.get(name, name)] for name in NO_CAPTURE}
    return {"request": report["request"], "func": report["func"], "inputs": report["inputs"],
            "map": report["argument_map"], "sources": source_edges(report["sources"]), "capture": capture}


class Inventory(CompositionInventory):
    """Decode native records without using the example or its inspector."""

    def node(self, txn, dag, name):
        return core.txn_lookup_node(txn, dag, name)

    def link(self, txn, dag, name):
        return self.node_target(self.node(txn, dag, name), core.NODE_SUBDAG)

    def scalar(self, txn, dag, name, kind):
        return self.literal(self.node(txn, dag, name), kind)

    def string(self, txn, dag, name):
        return text(self.scalar(txn, dag, name, core.DATUM_STRING))

    def uri(self, txn, dag, name):
        return text(self.scalar(txn, dag, name, core.DATUM_URI))

    def binding_source(self, txn, binding):
        return self.uri(txn, binding, b"source")

    def read_env(self, txn, env):
        map_binding = self.link(txn, env, b"map-get")
        list_binding = self.link(txn, env, b"list-get")
        scale = self.link(txn, env, b"scale")
        origin = self.link(txn, scale, b"source")
        return {"environment": env.hex(), "mapBinding": map_binding.hex(),
                "mapSource": self.binding_source(txn, map_binding), "listBinding": list_binding.hex(),
                "listSource": self.binding_source(txn, list_binding), "scaleSource": scale.hex(),
                "scaleOrigin": self.string(txn, origin, b"origin"),
                "scale": self.i64(txn, scale, b"value")}

    def argument_id(self, txn, dag):
        return self.node_target(self.node(txn, dag, b"value"), core.NODE_LITERAL)

    def edges(self, txn, dag):
        _, _, size = core.object_decode(self.packed(b"dags", dag))
        return source_edges({self.string(txn, dag, f"key-{i:02d}".encode()):
                             self.link(txn, dag, f"source-{i:02d}".encode()).hex()
                             for i in range((size - 2) // 2)})

    def get_value(self, datum, expected):
        value, kind = core.datum_decode(self.packed(b"datums", datum))
        if kind != expected:
            raise ValueError(f"expected argument datum kind {expected}, found {kind}")
        return int.from_bytes(value, "little", signed=True) if kind == core.DATUM_I64 else value

    def i64(self, txn, dag, name):
        node = self.node(txn, dag, name)
        return self.get_value(self.node_target(node, core.NODE_LITERAL), core.DATUM_I64)

    def read_map(self, txn, dag):
        datum = self.argument_id(txn, dag)
        if core.datum_decode(self.packed(b"datums", datum))[1] != core.DATUM_MAP:
            raise ValueError("expected native argument MAP")
        pairs = sorted((text(self.get_value(key, core.DATUM_STRING)), self.get_value(value, core.DATUM_I64))
                       for key, value in core.datum_members(self.packed(b"datums", datum)))
        return {"inputs": dag.hex(), "map": datum.hex(), "sources": self.edges(txn, dag),
                "args": [{"name": name, "value": value} for name, value in pairs]}

    def trace(self, txn, dag):
        _, _, size = core.object_decode(self.packed(b"dags", dag))
        calls = []
        bindings = []
        keys = []
        values = []
        for index in range(size - 1):
            op = self.link(txn, dag, f"call-{index:02d}".encode())
            binding = self.link(txn, op, b"binding")
            inputs = self.link(txn, op, b"arguments")
            sources = self.edges(txn, inputs)
            calls.append({"operation": op.hex(), "func": self.uri(txn, op, b"func"),
                          "binding": self.binding_source(txn, binding), "inputs": inputs.hex(),
                          "datum": self.argument_id(txn, op).hex(), "sources": sources})
            bindings.append(binding.hex())
            key = next(edge["dag"] for edge in sources if edge["name"] == "key")
            keys.append(text(self.root_literal(key, core.DATUM_STRING)))
            values.append(self.i64(txn, op, b"value"))
        return calls, bindings, keys, values

    def read_commit(self, identifier, txn):
        raw = bytes.fromhex(identifier)
        dag, name = contents(txn, raw)
        role = text(name)
        ps = [parent.hex() for parent in parents(txn, raw)]
        row = {"id": identifier, "role": role, "dag": dag.hex(), "parents": ps, "capture": NO_CAPTURE,
               "pin": "", "selected": "", "mode": "", "outcome": "", "inputs": "", "map": "", "func": "",
               "sources": [], "args": [], "trace": [], "traceBindings": [], "traceKeys": [], "traceValues": [],
               "value": 0, "keyScale": 0, "keyFuncs": []}
        if role == role_name("defaults"):
            row["capture"] = {**NO_CAPTURE, **self.read_env(txn, dag), "defaults": identifier}
        elif role == role_name("closure"):
            key = self.link(txn, dag, b"capture-key")
            row.update(capture={**self.read_env(txn, self.link(txn, dag, b"environment")),
                                "closure": identifier, "descriptor": dag.hex(), "defaults": ps[0],
                                "captureKey": key.hex(), "func": self.uri(txn, dag, b"func"),
                                "implementation": self.string(txn, dag, b"implementation")},
                       keyScale=self.i64(txn, key, b"scale"),
                       keyFuncs=[self.uri(txn, key, builtin) for builtin in (b"map-get", b"list-get")])
        elif role == role_name("request"):
            row.update(self.read_map(txn, self.link(txn, dag, b"inputs")),
                       pin=self.string(txn, dag, b"closure"), func=self.uri(txn, dag, b"func"))
        elif role == role_name("decision"):
            row.update(mode=text(self.root_literal(dag.hex(), core.DATUM_STRING)),
                       outcome=self.string(txn, dag, b"outcome"), pin=self.string(txn, dag, b"request"),
                       selected=self.string(txn, dag, b"selection"))
        elif role == role_name("result"):
            trace, bindings, keys, values = self.trace(txn, self.link(txn, dag, b"trace"))
            row.update(inputs=self.link(txn, dag, b"inputs").hex(), trace=trace, traceBindings=bindings,
                       traceKeys=keys, traceValues=values, value=self.i64(txn, dag, b"value"))
        return row

    def counts(self):
        return [sum(record["role"] == role_name(role) for record in self.commits.values()) for role in ROLES]


def role_name(role):
    return f"{ROLE_PREFIX}{role}-v1"


def contents(txn, commit):
    _, tree, _ = record_view(txn, core.REC_COMMIT, commit)
    view, _, count = record_view(txn, core.REC_TREE, tree)
    if count != 1:
        raise ValueError("expected single-entry closure example snapshot")
    return core.object_view_entry(view, 0)


def snapshot(txn, original, dag, *ps):
    _, name = contents(txn, original)
    return put(txn, core.REC_COMMIT, put(txn, core.REC_TREE, name, dag), *ps)


def replacement_dag(txn, dag, names, field, node):
    _, root, count = record_view(txn, core.REC_DAG, dag)
    if count != len(names):
        raise ValueError("unexpected fixture DAG binding count")
    entries = [(name, node if name == field else core.txn_lookup_node(txn, dag, name)) for name in names]
    return put(txn, core.REC_DAG, root, *(item for pair in entries for item in pair))


def target(txn, dag, field):
    node = core.txn_lookup_node(txn, dag, field)
    _, identifier, _ = record_view(txn, core.REC_NODE, node)
    return identifier


def literal(txn, kind, value):
    datum = core.txn_put_datum(txn, core.datum_encode(kind, value))
    return put(txn, core.REC_NODE, core.NODE_LITERAL, datum)


def link(txn, dag):
    return put(txn, core.REC_NODE, core.NODE_SUBDAG, dag)


def repin(txn, commit, names, field, value, *ps):
    dag, _ = contents(txn, commit)
    replacement = literal(txn, core.DATUM_STRING, value.hex().encode("ascii"))
    return snapshot(txn, commit, replacement_dag(txn, dag, names, field, replacement), *ps)


def graft_selection(txn, attempt, alternate):
    q, r = parents(txn, attempt)
    (closure,) = parents(txn, q)
    (wrong_defaults,) = parents(txn, alternate)
    wrong_closure = replace_parents(txn, closure, wrong_defaults)
    wrong_q = repin(txn, q, Q_FIELDS, b"closure", wrong_closure, wrong_closure)
    wrong_r = replace_parents(txn, r, wrong_q)
    return replace_parents(txn, attempt, wrong_q, wrong_r)


def graft_decision(txn, kind, decision):
    q, selected = parents(txn, decision)
    (requested,) = parents(txn, q)
    if kind == "original":
        poison = graft_selection(txn, selected, requested)
        return repin(txn, decision, D_FIELDS, b"selection", poison, q, poison)
    (producing_q, _) = parents(txn, selected)
    (producing,) = parents(txn, producing_q)
    (defaults,) = parents(txn, requested)
    descriptor, _ = contents(txn, requested)
    old_descriptor, _ = contents(txn, producing)
    if kind == "key":
        key = target(txn, descriptor, b"capture-key")
        wrong = replacement_dag(txn, key, ENV_FIELDS, b"scale", literal(txn, core.DATUM_I64, 3))
        field = b"capture-key"
    else:
        field = b"environment"
        env = target(txn, descriptor, field)
        old_env = target(txn, old_descriptor, field)
        replaced = {"source": b"scale", "binding": b"map-get"}[kind]
        wrong = replacement_dag(txn, env, ENV_FIELDS, replaced,
                                core.txn_lookup_node(txn, old_env, replaced))
    bad_descriptor = replacement_dag(txn, descriptor, CAPTURE_FIELDS, field, link(txn, wrong))
    wrong_closure = snapshot(txn, requested, bad_descriptor, defaults)
    wrong_q = repin(txn, q, Q_FIELDS, b"closure", wrong_closure, wrong_closure)
    return repin(txn, decision, D_FIELDS, b"request", wrong_q, wrong_q, selected)


class History:
    def __init__(self, directory, script, scanner):
        self.directory = directory
        self.script = script
        self.scanner = scanner
        self.receipts = {}
        self.native = WorkflowNative(core, directory)
        self.operations = {op: self.command(op) for op in ("defaults", "capture", "request", "work", "inspect")}
        self.operations.update(graft=self.graft, replicate=self.replicate, retire=self.retire, native=self.native_step)

    def native_step(self, op, *args):
        row = self.evidence("", (), Inventory({}), Inventory({}))
        return {**row, **self.native.run(op, *args)}

    def inventory(self, path):
        self.native.require_closed()
        if not (path / "data.mdb").is_file():
            return Inventory({})
        rows = scan_inventory(self.scanner, path)
        with repository(path) as repo:
            txn = core.txn_begin(repo, core.TXN_READ)
            try:
                return Inventory(rows, txn)
            finally:
                core.txn_abort(txn)

    @staticmethod
    def evidence(op, args, before, after, *, commit="", report=None, code=0, error="", transfer=False):
        if commit and not IDENTITY.fullmatch(commit):
            raise ValueError(f"expected a commit ID, got {commit!r}")
        report = report or {}
        refs = [{"name": name, "before": before.refs.get(name, ""), "after": after.refs.get(name, "")}
                for name in sorted(before.refs.keys() | after.refs.keys())
                if before.refs.get(name, "") != after.refs.get(name, "")]
        return {"op": op, "args": list(args), "commit": commit, "code": code, "error": error,
                "unchanged": before.rows == after.rows, "main": after.refs.get("main", ""),
                "preserved": all(after.rows.get(key) == value for key, value in before.rows.items()
                                 if key.startswith(OBJECT_PREFIX)),
                "refs": refs, "transfer": transfer, "counts": after.counts(),
                "selectedRef": after.refs.get("t1", ""),
                "created": [after.commits[key] for key in sorted(after.commits.keys() - before.commits.keys())],
                "profiles": after.added_builtin_profiles(before),
                "requested": q_report(report.get("requested")), "producing": q_report(report.get("producing")),
                "mode": report.get("mode", ""), "outcome": report.get("outcome", ""),
                "selection": report.get("selection", ""), "attempt": report.get("attempt", ""),
                "result": report.get("result", ""), "outer": report.get("return_dag", ""),
                "value": report.get("value", 0),
                "trace": [{**call, "sources": source_edges(call["sources"])} for call in report.get("trace", [])],
                **WORKFLOW_NATIVE_DEFAULTS}

    def command(self, op):
        def invoke(role, *args):
            path = self.directory / role
            before = self.inventory(path)
            argv = [self.native.cli_operand(RECEIPT.sub(lambda match: self.receipts[match[1]], arg)) for arg in args]
            wrapper = ["-c", READ_ONLY] if op == "inspect" else []
            process = subprocess.run([sys.executable, "-B", *wrapper, self.script, op, path, *argv],
                                     cwd=self.directory, capture_output=True, text=True, encoding="utf-8", timeout=30)
            output = process.stdout.strip()
            report = json.loads(output) if op == "inspect" and output else None
            after = self.inventory(path)
            if role == "source":
                self.receipts.update(after.refs)
                if op == "defaults" and "defaults" in after.refs:
                    self.receipts.setdefault("initial-defaults", after.refs["defaults"])
            return self.evidence(op, (role, *args), before, after, commit=report["commit"] if report else output,
                                 report=report, code=process.returncode, error=process.stderr.strip())
        return invoke

    def graft(self, role, kind, ref, alternate, output):
        path = self.directory / role
        before = self.inventory(path)
        with repository(path) as repo:
            txn = core.txn_begin(repo, core.TXN_WRITE)
            try:
                original = bytes.fromhex(before.refs[ref])
                if kind == "selection":
                    commit = graft_selection(txn, original, bytes.fromhex(before.refs[alternate]))
                else:
                    commit = graft_decision(txn, kind, original)
                core.txn_ref_create(txn, output.encode("ascii"), commit)
                core.txn_commit(txn)
            finally:
                core.txn_abort(txn)
        self.receipts[output] = commit.hex()
        return self.evidence("graft", (role, kind, ref, alternate, output), before, self.inventory(path),
                             commit=commit.hex())

    def replicate(self, role, ref, pin):
        path = self.directory / role
        before = self.inventory(path)
        source_path = self.directory / "source"
        with repository(source_path) as source:
            bundle = core.repo_export_commit(source, bytes.fromhex(self.receipts[ref]))
        with repository(path, create=True) as target_repo:
            commit = core.repo_import_commit_staged(target_repo, bundle, pin.encode("ascii"))
            exact = core.repo_export_commit(target_repo, commit) == bundle
        source = self.inventory(source_path)
        after = self.inventory(path)
        exact = exact and all(source.rows.get(key) == value for key, value in after.rows.items()
                              if key.startswith(OBJECT_PREFIX))
        self.receipts[pin] = commit.hex()
        return self.evidence("replicate", (role, ref, pin), before, after, commit=commit.hex(), transfer=exact)

    def retire(self, role):
        original = self.directory / role
        before = self.inventory(original)
        retired = original.rename(self.directory / "retired")
        return self.evidence("retire", (role,), before, self.inventory(retired), transfer=not original.exists())


class Processes:
    def __init__(self, script, scanner):
        self.script = script
        self.scanner = scanner

    @contextmanager
    def history(self, directory):
        history = History(directory, self.script, self.scanner)
        with history.native:
            yield history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("script", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-closures-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        suite = Processes(args.script, args.scanner)
        observations = [replay_history(suite, directory / f"history-{i}", story)
                        for i, story in enumerate(histories)]
        defaults = History.evidence("", (), Inventory({}), Inventory({}))
        imports = [args.histories, *(args.histories.with_name(name) for name in (
            "workflow_native_fixture.qnt", "recorded_calls_fixtures.qnt"))]
        state = evaluate(quint, args.rules, directory, observations, imports, attempt_defaults=defaults)
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"closure replay failed: {error}") from error
