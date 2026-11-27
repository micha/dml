"""Observe CLI inspection of recorded returned arguments and their native source links."""

import argparse
from contextlib import nullcontext
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from daggerml import core

from run_argument_map_request_integrity import node_target, snapshot
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
from test_recorded_calls import put, transaction, view


EMPTY_DAG = {"dag": "", "root": "", "fields": 0}
EMPTY_SNAPSHOT = {**EMPTY_DAG, "role": "", "parents": [], "entries": 0}
EMPTY_RESULT = {"attempt": EMPTY_SNAPSHOT, "result": EMPTY_SNAPSHOT, "datum": "", "kind": -1, "value": 0}
EMPTY_REQUEST = {"request": EMPTY_SNAPSHOT, "construction": EMPTY_DAG, "constructionNode": "",
                 "implementationNode": "", "invocationNode": "", "priorNode": "", "keyNode": "", "keyHex": "",
                 "originNode": "", "origin": "", "sourceNode": "", "sourceDag": "", "input": "", "kind": -1,
                 "members": []}


def hex_id(identifier):
    return identifier.hex() if identifier is not None else ""


def dag_shape(txn, dag):
    _, root, fields = view(txn, core.REC_DAG, dag)
    return {"dag": dag.hex(), "root": root.hex(), "fields": fields}


def snapshot_shape(txn, commit):
    dag, role, parents, entries = snapshot(txn, commit)
    return {**dag_shape(txn, dag), "role": role.decode("ascii"), "parents": [p.hex() for p in parents],
            "entries": entries}


def literal_data(txn, node):
    datum = node_target(txn, node, core.NODE_LITERAL)
    return core.datum_decode(core.txn_get_datum(txn, datum)) if datum is not None else (b"", -1)


def result_evidence(txn, attempt):
    occurrence = snapshot_shape(txn, attempt)
    result = snapshot_shape(txn, bytes.fromhex(occurrence["parents"][1]))
    root = bytes.fromhex(result["root"])
    payload, kind = literal_data(txn, root)
    return {"attempt": occurrence, "result": result, "datum": hex_id(node_target(txn, root, core.NODE_LITERAL)),
            "kind": kind, "value": int.from_bytes(payload, "little", signed=True) if kind == core.DATUM_I64 else 0}


def request_evidence(txn, commit):
    request = snapshot_shape(txn, commit)
    dag = bytes.fromhex(request["dag"])
    construction_node = core.txn_lookup_node(txn, dag, b"construction")
    construction = node_target(txn, construction_node, core.NODE_SUBDAG)
    prior, key, origin, source = (core.txn_lookup_node(txn, construction, name)
                                  for name in (b"prior", b"key", b"origin", b"source"))
    key_data, key_kind = literal_data(txn, key)
    origin_data, origin_kind = literal_data(txn, origin)
    datum = node_target(txn, bytes.fromhex(request["root"]), core.NODE_LITERAL)
    packed = core.txn_get_datum(txn, datum)
    _, kind = core.datum_decode(packed)
    members = []
    if kind == core.DATUM_MAP:
        for member_key, value in core.datum_members(packed):
            payload, member_kind = core.datum_decode(core.txn_get_datum(txn, member_key))
            members.append({"keyHex": payload.hex(), "kind": member_kind, "datum": value.hex()})
    return {"request": request, "construction": dag_shape(txn, construction),
            "constructionNode": construction_node.hex(),
            "implementationNode": core.txn_lookup_node(txn, dag, b"implementation").hex(),
            "invocationNode": core.txn_lookup_node(txn, dag, b"invocation").hex(),
            "priorNode": prior.hex(), "keyNode": key.hex(), "keyHex": key_data.hex() if key_kind == core.DATUM_STRING else "",
            "originNode": origin.hex(), "origin": origin_data.decode("ascii") if origin_kind == core.DATUM_STRING else "",
            "sourceNode": source.hex(), "sourceDag": hex_id(node_target(txn, source, core.NODE_SUBDAG)),
            "input": datum.hex(), "kind": kind, "members": members}


def bindings(txn, dag, names):
    return [item for name in names for item in (name, core.txn_lookup_node(txn, dag, name))]


class ReturnedSourceHistory(History):
    def __init__(self, directory, example, scanner):
        super().__init__(directory, example, scanner)
        self.operations["record_returned_source"] = self.record_returned_source

    def evidence(self, op, args, output, code, stderr, before, after):
        row = super().evidence(op, args, output, code, stderr, before, after)
        request, result = EMPTY_REQUEST, EMPTY_RESULT
        target = after.get(REF_PREFIX + args[1].encode("ascii").hex())
        # Observe the committed ref even when inspection produces no report.
        if target and op in ("inspect", "record_returned_source"):
            commit = bytes.fromhex(target)
            with transaction(self.directory / args[0]) as txn:
                _, role, _, _ = snapshot(txn, commit)
                if role == b"argument-map-attempt-v1":
                    result = result_evidence(txn, commit)
                elif role == b"argument-map-request-v1":
                    request = request_evidence(txn, commit)
        return {**{key: row[key] for key in ("op", "args", "code", "commit", "unchanged", "refs", "attempt", "result",
                                            "producingRequest", "producingImplementation", "producingInput", "value",
                                            "request", "input", "implementation", "construction", "sources", "keyHex",
                                            "reportDigest")},
                "diagnostics": stderr.splitlines(), "stdout": bool(output), "nativeRequest": request,
                "nativeResult": result, "additions": len(after.keys() - before.keys()),
                "preserved": all(after.get(key) == value for key, value in before.items())}

    def record_returned_source(self, role, output, basis, donor):
        repo = self.directory / role
        before = self.inventory(repo)
        original, attempt = map(bytes.fromhex, self.cli_args((basis, donor)))
        # Use normal core object encoding/publication in the disposable fixture repo.
        with transaction(repo, core.TXN_WRITE) as txn:
            dag, entry, parents, _ = snapshot(txn, original)
            _, _, (_, result), _ = snapshot(txn, attempt)
            result_dag, _, _, _ = snapshot(txn, result)
            construction_node = core.txn_lookup_node(txn, dag, b"construction")
            construction = node_target(txn, construction_node, core.NODE_SUBDAG)
            _, map_root, _ = view(txn, core.REC_DAG, construction)
            _, request_root, _ = view(txn, core.REC_DAG, dag)
            source = put(txn, core.REC_NODE, core.NODE_SUBDAG, result_dag)
            new_construction = put(txn, core.REC_DAG, map_root, b"source", source,
                                   *bindings(txn, construction, (b"prior", b"key", b"origin")))
            link = put(txn, core.REC_NODE, core.NODE_SUBDAG, new_construction)
            new_request = put(txn, core.REC_DAG, request_root, b"construction", link,
                              *bindings(txn, dag, (b"implementation", b"invocation")))
            tree = put(txn, core.REC_TREE, entry, new_request)
            commit = put(txn, core.REC_COMMIT, tree, *parents)
            core.txn_ref_create(txn, output.encode("ascii"), commit)
            core.txn_commit(txn)
        return self.evidence("record_returned_source", (role, output, basis, donor), commit.hex(), 0, "", before,
                             self.inventory(repo))


class Processes:
    def __init__(self, example, scanner):
        self.example = example
        self.scanner = scanner

    def history(self, directory):
        return nullcontext(ReturnedSourceHistory(directory, self.example, self.scanner))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("example", "scanner", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-argument-map-returned-source-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        processes = Processes(args.example, args.scanner)
        evidence = [replay_history(processes, directory / f"history-{i}", history)
                    for i, history in enumerate(histories)]
        state = evaluate(quint, args.rules, directory, evidence, [args.histories])
        check_verdicts(histories, evidence, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"argument-map returned-source replay failed: {error}") from error
