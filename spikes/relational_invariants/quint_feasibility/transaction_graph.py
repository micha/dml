"""Persist and reopen one transaction observation through native DML records."""

from collections.abc import Sequence
from pathlib import Path
import re

import daggerml as dml

from ref_binding import BINDINGS, Request
from transaction_binding import Batch, validate_observation


REF = "transaction-evidence"
SCHEMA = "quint-transaction-evidence-v1"
ROOT_FIELDS = {"schema", "initial", "requests", "finish", "requested_ids", "evidence"}
# Root map -> evidence map -> steps list -> step map -> tagged sum -> payload.
MAX_DATUM_DEPTH = 5


def _put_value(tx: dml.Transaction, value: object) -> dml.ObjectId:
    if value is None or type(value) in (bool, str):
        return tx.put_datum(value)
    if type(value) is tuple:
        return tx.put_datum(dml.Datum.list(_put_value(tx, item) for item in value))
    if type(value) is dict:
        return tx.put_datum(dml.Datum.map(
            (tx.put_datum(key), _put_value(tx, item)) for key, item in value.items()
        ))
    raise ValueError(f"Unsupported transaction evidence value: {type(value).__name__}")


def _get_value(tx: dml.Transaction, object_id: dml.ObjectId, depth: int = 0) -> object:
    if depth > MAX_DATUM_DEPTH:
        raise ValueError("Transaction evidence datum nesting exceeds the schema")
    datum = tx.get_datum(object_id)
    if datum.kind in ("null", "bool", "string"):
        return datum.value
    if datum.kind == "list":
        return tuple(_get_value(tx, item, depth + 1) for item in datum.value)
    if datum.kind == "map":
        result = {}
        for key, item in datum.value:
            name = tx.get_datum(key)
            if name.kind != "string":
                raise ValueError("Transaction evidence map keys must be strings")
            result[name.value] = _get_value(tx, item, depth + 1)
        return result
    raise ValueError(f"Unsupported transaction evidence datum kind: {datum.kind}")


def _is_object_id(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{32}", value) is not None


def _validate_batch(batch: Batch, initial: str | None, requests: Sequence[Request], finish: str) -> None:
    if batch.initial is not None and type(batch.initial) is not str:
        raise ValueError("Transaction initial target must be a string or null")
    if type(batch.requests) is not tuple or any(
        type(request) is not tuple or len(request) != 2
        or type(request[0]) is not str or request[0] not in BINDINGS or type(request[1]) is not str
        for request in batch.requests
    ):
        raise ValueError("Invalid transaction requests in evidence graph")
    if type(batch.finish) is not str or batch.finish not in ("commit", "abort"):
        raise ValueError("Invalid transaction finish in evidence graph")
    if type(batch.requested_ids) is not tuple or not all(map(_is_object_id, batch.requested_ids)):
        raise ValueError("Transaction requested IDs must be lowercase object IDs")

    evidence = validate_observation(initial, requests, finish, batch)
    snapshots = [evidence["before"], evidence["staged"], evidence["after"]]
    for step in evidence["steps"]:
        snapshots.extend((step["before"], step["after"]))
    if any(tag == "Target" and not _is_object_id(payload) for tag, payload in snapshots):
        raise ValueError("Transaction snapshot targets must be lowercase object IDs")


def save_batch(path: Path, batch: Batch) -> dml.ObjectId:
    """Create a new evidence repository and return its committed root ID."""
    _validate_batch(batch, batch.initial, batch.requests, batch.finish)
    record = {
        "schema": SCHEMA, "initial": batch.initial, "requests": batch.requests,
        "finish": batch.finish, "requested_ids": batch.requested_ids, "evidence": batch.evidence,
    }
    path.mkdir()
    with dml.Repository(path, create=True) as repo, repo.write() as tx:
        literal = tx.put_literal(_put_value(tx, record))
        dag = tx.put_dag(root=literal)
        root = tx.put_commit(tx.put_tree({"evidence": dag}))
        tx.create_ref(REF, root)
    return root


def _root_datum(tx: dml.Transaction, expected_root: dml.ObjectId) -> dml.ObjectId:
    root = tx.get_ref(REF)
    if root != expected_root:
        raise ValueError("Transaction evidence ref does not match the expected root")
    commit = tx.get_commit(root)
    tree = tx.get_tree(commit.tree)
    if commit.parents or set(tree) != {"evidence"}:
        raise ValueError("Expected one evidence DAG and a parentless commit")
    dag = tx.get_dag(tree["evidence"])
    node = tx.get_node(dag.root)
    if dag.bindings or not isinstance(node, dml.LiteralNode):
        raise ValueError("Expected an unbound evidence DAG with a literal root")
    return node.datum


def load_batch(
    path: Path, expected_root: dml.ObjectId, *, initial: str | None, requests: Sequence[Request], finish: str,
) -> Batch:
    """Read only the persisted graph, then validate it against the caller's recipe."""
    with dml.Repository(path) as repo, repo.read() as tx:
        record = _get_value(tx, _root_datum(tx, expected_root))
    if type(record) is not dict or record.keys() != ROOT_FIELDS or record["schema"] != SCHEMA:
        raise ValueError("Expected a complete transaction evidence graph with the supported schema")
    batch = Batch(record["initial"], record["requests"], record["finish"],
                  record["requested_ids"], record["evidence"])
    _validate_batch(batch, initial, requests, finish)
    return batch
