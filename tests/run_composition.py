"""Collect live CLI and independent native evidence for composed node calls."""

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from daggerml import core

from replay_core import WORKFLOW_NATIVE_DEFAULTS, WorkflowNative
from run_builtins import READ_ONLY
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


RECEIPT = re.compile(r"@([a-z][a-z0-9-]*)")
IDENTITY = re.compile(r"[0-9a-f]{32}")
REF_PREFIX = b"refs/heads/".hex()
COMMIT_PREFIX = b"objects/commits/".hex()
DAG_PREFIX = b"objects/dags/".hex()
OBJECT_PREFIX = b"objects/".hex()


class Inventory:
    def __init__(self, rows, txn=None):
        self.rows = rows
        self.commits = {}
        self.profiles = {}
        for key in rows:
            if key.startswith(COMMIT_PREFIX):
                commit = bytes.fromhex(key[len(COMMIT_PREFIX):]).decode("ascii")
                self.commits[commit] = self.read_commit(commit, txn)
            elif key.startswith(DAG_PREFIX):
                dag = bytes.fromhex(bytes.fromhex(key[len(DAG_PREFIX):]).decode("ascii"))
                try:
                    node = core.txn_lookup_node(txn, dag, b"role")
                except core.Error as error:
                    if error.args[0] != "not_found":
                        raise
                else:
                    role = self.literal(node, core.DATUM_STRING)
                    if role.startswith(b"builtin-"):
                        self.profiles[key] = role.decode("ascii")
        self.refs = {bytes.fromhex(key[len(REF_PREFIX):]).decode("ascii"): value
                     for key, value in rows.items() if key.startswith(REF_PREFIX)}

    def packed(self, kind, identifier):
        key = (b"objects/" + kind + b"/" + identifier.hex().encode("ascii")).hex()
        return bytes.fromhex(self.rows[key])

    def read_commit(self, identifier, txn):
        view, tree, count = core.object_decode(self.packed(b"commits", bytes.fromhex(identifier)))
        parents = [core.object_view_parent(view, i).hex() for i in range(count)]
        view, _, count = core.object_decode(self.packed(b"trees", tree))
        if count != 1:
            raise ValueError("expected one example role in the native commit tree")
        dag, name = core.object_view_entry(view, 0)
        producer = ""
        inputs = ""
        if name == b"composition-example-composition-v1":
            _, root, count = core.object_decode(self.packed(b"dags", dag))
            if count != 2 or core.txn_lookup_node(txn, dag, b"producer") != root:
                raise ValueError("expected exact composition DAG shape")
            producer = self.literal(root, core.DATUM_STRING).decode("ascii")
        if name in (b"composition-example-composition-v1", b"composition-example-request-v1"):
            inputs = self.node_target(core.txn_lookup_node(txn, dag, b"inputs"), core.NODE_SUBDAG).hex()
        return {"id": identifier, "role": name.decode("ascii"), "dag": dag.hex(),
                "parents": parents, "pin": producer, "inputs": inputs}

    def node_target(self, node, kind):
        packed = self.packed(b"nodes", node)
        _, target, _ = core.object_decode(packed)
        if packed != core.object_encode(core.REC_NODE, kind, target):
            raise ValueError("unexpected recorded node kind")
        return target

    def literal(self, node, kind):
        datum = self.node_target(node, core.NODE_LITERAL)
        payload, actual = core.datum_decode(self.packed(b"datums", datum))
        if actual != kind:
            raise ValueError("unexpected literal datum kind")
        return payload

    def root_literal(self, dag, kind):
        _, root, _ = core.object_decode(self.packed(b"dags", bytes.fromhex(dag)))
        return self.literal(root, kind)

    def counts(self):
        return [sum(record["role"] == f"composition-example-{role}-v1" for record in self.commits.values())
                for role in ("request", "attempt", "result", "composition", "decision")]

    def added_builtin_profiles(self, before):
        return sorted(role for key, role in self.profiles.items() if key not in before.rows)


def upstream(raw):
    return {field: raw.get(label, "") for field, label in (
        ("attempt", "attempt"), ("request", "request"), ("result", "result"),
        ("outer", "return_dag"), ("map", "argument_map"))}


def sources(raw):
    return [{"name": name, "dag": dag} for name, dag in sorted(raw.get("sources", {}).items())]


def request(raw):
    return {"func": raw.get("func", ""), "request": raw.get("request", ""), "inputs": raw.get("inputs", ""),
            "map": raw.get("argument_map", ""), "sources": sources(raw),
            "composition": raw.get("composition", ""), "upstream": upstream(raw.get("upstream", {}))}


def report_fields(raw, inventory):
    trace = [{"operation": call["operation"], "func": call["func"], "binding": call["binding"],
              "inputs": call["inputs"], "datum": call["datum"], "sources": sources(call),
              "key": inventory.root_literal(call["sources"]["key"], core.DATUM_STRING).decode("ascii")}
             for call in raw.get("trace", [])]
    return {"requested": request(raw.get("requested", {})), "producing": request(raw.get("producing", {})),
            "trace": trace, "outcome": raw.get("outcome", ""),
            "selection": raw.get("selection", ""), "attempt": raw.get("attempt", ""),
            "result": raw.get("result", ""), "outer": raw.get("return_dag", ""), "value": raw.get("value", 0)}


@contextmanager
def repository(path, *, create=False):
    repo = core.repo_open(path, create)
    try:
        yield repo
    finally:
        core.repo_close(repo)


def record_view(txn, kind, identifier):
    return core.object_decode(core.txn_get_object(txn, kind, identifier))


def parents(txn, commit):
    view, _, count = record_view(txn, core.REC_COMMIT, commit)
    return tuple(core.object_view_parent(view, i) for i in range(count))


def put(txn, kind, *fields):
    return core.txn_put_object(txn, kind, core.object_encode(kind, *fields))


def replace_parents(txn, commit, *replacements):
    _, tree, _ = record_view(txn, core.REC_COMMIT, commit)
    return put(txn, core.REC_COMMIT, tree, *replacements)


def graft_selection(txn, selection, alternate):
    q, r = parents(txn, selection)
    (c,) = parents(txn, q)
    wrong_c = replace_parents(txn, c, alternate)
    wrong_q = replace_parents(txn, q, wrong_c)
    wrong_r = replace_parents(txn, r, wrong_q)
    return replace_parents(txn, selection, wrong_q, wrong_r)


def graft_reuse_request(txn, decision):
    _, selected = parents(txn, decision)
    producing_request, _ = parents(txn, selected)
    return replace_parents(txn, decision, producing_request, selected)


def graft_history(txn, decision):
    own, historical = parents(txn, decision)
    (current,) = parents(txn, own)
    (producer,) = parents(txn, current)
    wrong_t = graft_selection(txn, historical, producer)
    return replace_parents(txn, decision, own, wrong_t)


def graft_parent(txn, decision):
    own, historical = parents(txn, decision)
    old_q, _ = parents(txn, historical)
    (original,) = parents(txn, old_q)
    (alternate,) = parents(txn, original)
    (current,) = parents(txn, own)
    return replace_parents(txn, current, alternate)


def graft_input(txn, decision):
    own, historical = parents(txn, decision)
    old_q, _ = parents(txn, historical)
    (original,) = parents(txn, old_q)
    (current,) = parents(txn, own)
    (actual,) = parents(txn, current)

    def contents(commit):
        _, tree, _ = record_view(txn, core.REC_COMMIT, commit)
        view, _, _ = record_view(txn, core.REC_TREE, tree)
        return core.object_view_entry(view, 0)

    original_dag, _ = contents(original)
    current_dag, role = contents(current)
    old_input = core.txn_lookup_node(txn, original_dag, b"inputs")
    producer = core.txn_lookup_node(txn, current_dag, b"producer")
    dag = put(txn, core.REC_DAG, producer, b"producer", producer, b"inputs", old_input)
    return put(txn, core.REC_COMMIT, put(txn, core.REC_TREE, role, dag), actual)


class History:
    def __init__(self, directory, script, scanner):
        self.directory = directory
        self.script = script
        self.scanner = scanner
        self.receipts = {}
        self.native = WorkflowNative(core, directory)
        self.operations = {op: self.command(op) for op in (
            "define", "request_add", "work", "compose", "request_double", "inspect")}
        self.operations.update(replicate=self.replicate, retire=self.retire, native=self.native_step)
        for fixture in (graft_selection, graft_parent, graft_input, graft_history, graft_reuse_request):
            self.operations[fixture.__name__] = self.fixture(fixture)

    def native_step(self, op, *args):
        row = self.evidence("", (), Inventory({}), Inventory({}))
        return {**row, **self.native.run(op, *args)}

    def inventory(self, repo):
        self.native.require_closed()
        if not (repo / "data.mdb").is_file():
            return Inventory({})
        rows = scan_inventory(self.scanner, repo)
        with repository(repo) as handle:
            txn = core.txn_begin(handle, core.TXN_READ)
            try:
                return Inventory(rows, txn)
            finally:
                core.txn_abort(txn)

    def evidence(self, op, args, before, after, *, commit="", report=None, error="", code=0, transfer=False):
        if commit and not IDENTITY.fullmatch(commit):
            raise ValueError(f"expected a commit ID, got {commit!r}")
        for name, target in after.refs.items():
            self.receipts.setdefault(name, target)
        added = sorted(after.commits.keys() - before.commits.keys())
        changed = sorted(before.refs.keys() | after.refs.keys())
        refs = [{"name": name, "before": before.refs.get(name, ""), "after": after.refs.get(name, "")}
                for name in changed if before.refs.get(name, "") != after.refs.get(name, "")]
        preserved = all(after.rows.get(key) == value for key, value in before.rows.items()
                        if key.startswith(OBJECT_PREFIX))
        return {"op": op, "args": list(args), "commit": commit, "code": code, "error": error,
                "unchanged": before.rows == after.rows, "preserved": preserved, "transfer": transfer,
                "refs": refs, "main": after.refs.get("main", ""), "counts": after.counts(),
                "profiles": after.added_builtin_profiles(before),
                "created": [after.commits[identifier] for identifier in added],
                **report_fields(report or {}, after), **WORKFLOW_NATIVE_DEFAULTS}

    def command(self, op):
        def invoke(role, *args):
            repo = self.directory / role
            before = self.inventory(repo)
            argv = [self.native.cli_operand(RECEIPT.sub(lambda match: self.receipts[match[1]], arg)) for arg in args]
            wrapper = ["-c", READ_ONLY] if op == "inspect" else []
            process = subprocess.run([sys.executable, "-B", *wrapper, self.script,
                                      op.replace("_", "-"), repo, *argv], cwd=self.directory,
                                     capture_output=True, text=True, encoding="utf-8", timeout=30)
            output = process.stdout.strip()
            report = json.loads(output) if op == "inspect" and output else None
            return self.evidence(op, (role, *args), before, self.inventory(repo),
                                 commit=report["commit"] if report is not None else output, report=report,
                                 error=process.stderr.strip(), code=process.returncode)
        return invoke

    def fixture(self, forge):
        def invoke(role, *args):
            path = self.directory / role
            before = self.inventory(path)
            *refs, output = args
            with repository(path) as repo:
                txn = core.txn_begin(repo, core.TXN_WRITE)
                try:
                    commits = [core.txn_ref_get(txn, ref.encode("ascii")) for ref in refs]
                    commit = forge(txn, *commits)
                    core.txn_ref_create(txn, output.encode("ascii"), commit)
                    core.txn_commit(txn)
                finally:
                    core.txn_abort(txn)
            return self.evidence(forge.__name__, (role, *args), before, self.inventory(path), commit=commit.hex())
        return invoke

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
        return self.evidence("replicate", (role, receipt, pin), before, after, commit=commit.hex(), transfer=exact)

    def retire(self, role):
        original = self.directory / role
        before = self.inventory(original)
        retired = original.rename(self.directory / "retired")
        after = self.inventory(retired)
        return self.evidence("retire", (role,), before, after, transfer=not original.exists())


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
    with TemporaryDirectory(prefix="dml-composition-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        suite = Processes(args.script, args.scanner)
        observations = [replay_history(suite, directory / f"history-{i}", story)
                        for i, story in enumerate(histories)]
        defaults = History(directory, args.script, args.scanner).evidence("", (), Inventory({}), Inventory({}))
        imports = [args.histories, *(args.histories.with_name(name) for name in (
            "workflow_native_fixture.qnt", "recorded_calls_fixtures.qnt"))]
        state = evaluate(quint, args.rules, directory, observations, imports, attempt_defaults=defaults)
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"composition replay failed: {error}") from error
