"""Observe CLI inspection of an argument-map request with a substituted native root."""

import argparse
from contextlib import nullcontext
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from daggerml import core

from run_argument_maps import REF_PREFIX, History
from run_histories import (
    absolute_path,
    add_quint_arguments,
    check_verdicts,
    evaluate,
    quint_command,
    read_histories,
    replay_history,
)
from recorded_call_fixtures import put, transaction, view


REQUEST_FIELDS = (b"construction", b"implementation", b"invocation")
EMPTY_MAP = {"node": "", "datum": "", "literal": False, "kind": -1, "members": []}
EMPTY_REQUEST = {"dag": "", "role": "", "parents": [], "entries": 0, "fields": 0, "bindings": [],
                 "root": EMPTY_MAP, "construction": "", "constructionMap": EMPTY_MAP}


def snapshot(txn, commit):
    record, tree, count = view(txn, core.REC_COMMIT, commit)
    entries, _, size = view(txn, core.REC_TREE, tree)
    dag, role = core.object_view_entry(entries, 0)
    return dag, role, [core.object_view_parent(record, i) for i in range(count)], size


def node_target(txn, node, kind):
    packed = core.txn_get_object(txn, core.REC_NODE, node)
    _, target, _ = core.object_decode(packed)
    return target if packed == core.object_encode(core.REC_NODE, kind, target) else None


def map_evidence(txn, root):
    datum = node_target(txn, root, core.NODE_LITERAL)
    if datum is None:
        return {**EMPTY_MAP, "node": root.hex()}
    packed = core.txn_get_datum(txn, datum)
    _, kind = core.datum_decode(packed)
    members = []
    if kind == core.DATUM_MAP:
        for key, value in core.datum_members(packed):
            key_data, key_kind = core.datum_decode(core.txn_get_datum(txn, key))
            value_data, value_kind = core.datum_decode(core.txn_get_datum(txn, value))
            number = int.from_bytes(value_data, "little", signed=True) if value_kind == core.DATUM_I64 else 0
            members.append({"keyHex": key_data.hex(), "keyKind": key_kind, "valueKind": value_kind, "value": number})
    return {"node": root.hex(), "datum": datum.hex(), "literal": True, "kind": kind, "members": members}


def request_evidence(repo, commit):
    with transaction(repo) as txn:
        dag, role, parents, size = snapshot(txn, commit)
        _, root, fields = view(txn, core.REC_DAG, dag)
        bindings = [core.txn_lookup_node(txn, dag, name) for name in REQUEST_FIELDS]
        construction = node_target(txn, bindings[0], core.NODE_SUBDAG)
        construction_map = EMPTY_MAP
        if construction is not None:
            _, constructed_root, _ = view(txn, core.REC_DAG, construction)
            construction_map = map_evidence(txn, constructed_root)
        return {"dag": dag.hex(), "role": role.decode("ascii"), "parents": [x.hex() for x in parents],
                "entries": size, "fields": fields, "bindings": [x.hex() for x in bindings],
                "root": map_evidence(txn, root), "construction": construction.hex() if construction else "",
                "constructionMap": construction_map}


class RequestIntegrityHistory(History):
    def __init__(self, directory, example, scanner):
        super().__init__(directory, example, scanner)
        self.operations["record_request_root"] = self.record_request_root

    def evidence(self, op, args, output, code, stderr, before, after):
        row = super().evidence(op, args, output, code, stderr, before, after)
        # Read the target chosen by the committed ref, not the CLI receipt.
        target = after.get(REF_PREFIX + args[1].encode("ascii").hex())
        native = (request_evidence(self.directory / args[0], bytes.fromhex(target))
                  if target and op in ("inspect", "record_request_root") else EMPTY_REQUEST)
        return {**{key: row[key] for key in ("op", "args", "code", "error", "commit", "unchanged", "refs",
                                            "request", "input", "construction", "implementation", "reportDigest")},
                "stdout": bool(output), "native": native, "additions": len(after.keys() - before.keys()),
                "preserved": all(after.get(key) == value for key, value in before.items())}

    def record_request_root(self, role, output, basis, donor):
        repo = self.directory / role
        before = self.inventory(repo)
        original, substitute = map(bytes.fromhex, self.cli_args((basis, donor)))
        # Change only the request root. All writes use normal native encoding,
        # object validation and transaction publication.
        with transaction(repo, core.TXN_WRITE) as txn:
            dag, entry, parents, _ = snapshot(txn, original)
            donor_dag, _, _, _ = snapshot(txn, substitute)
            _, root, _ = view(txn, core.REC_DAG, donor_dag)
            bindings = [item for name in REQUEST_FIELDS for item in (name, core.txn_lookup_node(txn, dag, name))]
            request = put(txn, core.REC_DAG, root, *bindings)
            tree = put(txn, core.REC_TREE, entry, request)
            commit = put(txn, core.REC_COMMIT, tree, *parents)
            core.txn_ref_create(txn, output.encode("ascii"), commit)
            core.txn_commit(txn)
        return self.evidence("record_request_root", (role, output, basis, donor), commit.hex(), 0, "", before,
                             self.inventory(repo))


class RequestIntegrityProcesses:
    def __init__(self, example, scanner):
        self.example = example
        self.scanner = scanner

    def history(self, directory):
        return nullcontext(RequestIntegrityHistory(directory, self.example, self.scanner))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("example", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-argument-map-request-integrity-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        processes = RequestIntegrityProcesses(args.example, args.scanner)
        evidence = [replay_history(processes, directory / f"history-{i}", history)
                    for i, history in enumerate(histories)]
        state = evaluate(quint, args.rules, directory, evidence, [args.histories])
        check_verdicts(histories, evidence, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"argument-map request integrity replay failed: {error}") from error
