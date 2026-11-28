"""Replay CLI routing with two test-only native argument-map table edits."""

import argparse
from contextlib import nullcontext
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from daggerml import core

from run_argument_maps import COMMIT_PREFIX, History
from run_histories import (
    absolute_path,
    add_quint_arguments,
    check_verdicts,
    evaluate,
    quint_command,
    read_histories,
    replay_history,
)
from recorded_call_fixtures import literal, put, transaction, view


EDIT_ROLE = b"argument-map-table-edit-v1"
EMPTY_EDIT = {"role": "", "operation": "", "key": "", "keyKind": -1, "operationKind": -1,
              "keyLiteral": False, "operationLiteral": False, "fields": 0}


def node_target(txn, node):
    packed = core.txn_get_object(txn, core.REC_NODE, node)
    _, target, _ = core.object_decode(packed)
    return target, packed == core.object_encode(core.REC_NODE, core.NODE_LITERAL, target)


def edit_evidence(repo, tree):
    with transaction(repo) as txn:
        entries, _, count = view(txn, core.REC_TREE, tree)
        if count != 1:
            raise ValueError("expected one native table-edit tree entry")
        dag, role = core.object_view_entry(entries, 0)
        _, root, fields = view(txn, core.REC_DAG, dag)
        key, key_literal = node_target(txn, root)
        operation = core.txn_lookup_node(txn, dag, b"operation")
        datum, operation_literal = node_target(txn, operation)
        key_kind = core.datum_decode(core.txn_get_datum(txn, key))[1] if key_literal else -1
        op, op_kind = core.datum_decode(core.txn_get_datum(txn, datum)) if operation_literal else (b"", -1)
    return {"role": role.decode("ascii"), "operation": op.decode("ascii") if op_kind == core.DATUM_STRING else "",
            "key": key.hex(), "keyKind": key_kind, "operationKind": op_kind,
            "keyLiteral": key_literal, "operationLiteral": operation_literal, "fields": fields}


class PoisonHistory(History):
    def __init__(self, directory, example, scanner):
        super().__init__(directory, example, scanner)
        self.operations["record_table_edit"] = self.record_table_edit

    def evidence(self, op, args, output, code, stderr, before, after):
        row = super().evidence(op, args, output, code, stderr, before, after)
        packed = after.get(COMMIT_PREFIX + row["commit"].encode("ascii").hex())
        parents, edit = [], EMPTY_EDIT
        if packed is not None:
            commit, tree, count = core.object_decode(bytes.fromhex(packed))
            parents = [core.object_view_parent(commit, i).hex() for i in range(count)]
            if op == "record_table_edit":
                edit = edit_evidence(self.directory / args[0], tree)
        return {**row, "nativeParents": parents, "edit": edit,
                "preserved": all(after.get(key) == value for key, value in before.items())}

    def record_table_edit(self, role, output, operation, basis, key, *attempts):
        repo = self.directory / role
        before = self.inventory(repo)
        key_id, *parents = map(bytes.fromhex, self.cli_args((key, basis, *attempts)))
        # Bypass only the example's table writer. Native storage still validates
        # object shape and dependencies; the example's CLI reads the committed history.
        with transaction(repo, core.TXN_WRITE) as txn:
            root = put(txn, core.REC_NODE, core.NODE_LITERAL, key_id)
            op = literal(txn, core.DATUM_STRING, operation.encode("ascii"))
            dag = put(txn, core.REC_DAG, root, b"operation", op)
            tree = put(txn, core.REC_TREE, EDIT_ROLE, dag)
            commit = put(txn, core.REC_COMMIT, tree, *parents)
            core.txn_ref_create(txn, output.encode("ascii"), commit)
            core.txn_commit(txn)
        return self.evidence("record_table_edit", (role, output, operation, basis, key, *attempts),
                             commit.hex(), 0, "", before, self.inventory(repo))


class PoisonProcesses:
    def __init__(self, example, scanner):
        self.example = example
        self.scanner = scanner

    def history(self, directory):
        return nullcontext(PoisonHistory(directory, self.example, self.scanner))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("example", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-argument-map-poison-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        processes = PoisonProcesses(args.example, args.scanner)
        evidence = [{**replay_history(processes, directory / f"history-{i}", history), "scenario": i}
                    for i, history in enumerate(histories)]
        state = evaluate(quint, args.rules, directory, evidence, [args.histories])
        check_verdicts(histories, evidence, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"argument-map poison replay failed: {error}") from error
