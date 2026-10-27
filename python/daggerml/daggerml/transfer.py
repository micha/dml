"""Bounded pinned-commit exchange, using only the public repository API.

Objects and every parent are copied verbatim; refs and external resources are not.
Callers must close other handles for the physical repository before these helpers.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from typing import Optional

from . import LiteralNode, NotFoundError, ObjectId, Repository, Transaction

__all__ = ["export_commit", "import_commit", "ImportResult", "TransferError", "RefConflictError"]

FORMAT = "daggerml-commit-bundle-v1"
MAX_BUNDLE_BYTES = 32 * 1024 * 1024
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_PACKED_BYTES = 16 * 1024 * 1024
MAX_OBJECTS = 100000
KINDS = ("datum", "node", "dag", "tree", "commit")


class TransferError(ValueError):
    """Bundle framing, identity, order or completeness failure (no payload detail)."""


class RefConflictError(TransferError):
    """The explicit destination ref already points to a different commit."""


@dataclass(frozen=True)
class ImportResult:
    commit: ObjectId
    object_count: int
    ref: Optional[str]


def _edges(tx: Transaction, kind: str, object_id: ObjectId):
    """One typed edge definition shared by export and import."""
    if kind == "datum":
        datum = tx.get_datum(object_id)
        if datum.kind in ("list", "set"):
            return tuple(("datum", child) for child in datum.value)
        if datum.kind == "map":
            return tuple(("datum", child) for pair in datum.value for child in pair)
        return ()
    if kind == "node":
        node = tx.get_node(object_id)
        return (("datum", node.datum),) if isinstance(node, LiteralNode) else (("dag", node.dag),)
    if kind == "dag":
        dag = tx.get_dag(object_id)
        return tuple(("node", child) for child in (dag.root, *dag.bindings.values()))
    if kind == "tree":
        return tuple(("dag", dag) for _, dag in tx.get_tree(object_id).entries)
    commit = tx.get_commit(object_id)
    return (("tree", commit.tree),) + tuple(("commit", parent) for parent in commit.parents)


def _record_size(record: bytes, total: int) -> int:
    if len(record) > MAX_RECORD_BYTES:
        raise TransferError("packed record exceeds profile limit")
    total += len(record)
    if total > MAX_PACKED_BYTES:
        raise TransferError("total packed bytes exceed profile limit")
    return total


def export_commit(repository_path, *, commit: ObjectId) -> bytes:
    """Export all and only one immutable commit's complete typed object closure."""
    if not isinstance(commit, ObjectId):
        raise TypeError("commit requires ObjectId")
    rows, active, completed = [], set(), set()
    total = 0
    # Frames keep native-validated owned bytes until their dependencies finish.
    stack = [(("commit", commit), None)]
    with Repository(repository_path) as repo, repo.read() as tx:
        while stack:
            key, record = stack.pop()
            if record is not None:
                active.remove(key)
                completed.add(key)
                rows.append(
                    {
                        "kind": key[0],
                        "id": str(key[1]),
                        "record": base64.b64encode(record).decode("ascii"),
                    }
                )
                continue
            if key in active:
                raise TransferError("cycle in reached object graph")
            if key in completed:
                continue
            if len(active) + len(completed) >= MAX_OBJECTS:
                raise TransferError("object count exceeds profile limit")
            record = tx.get_record(*key)
            total = _record_size(record, total)
            children = _edges(tx, *key)
            active.add(key)
            stack.append((key, record))
            stack.extend((child, None) for child in reversed(children))
    bundle = json.dumps(
        {"format": FORMAT, "root": str(commit), "objects": rows},
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(bundle) > MAX_BUNDLE_BYTES:
        raise TransferError("encoded bundle exceeds profile limit")
    return bundle


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TransferError("duplicate JSON key")
        result[key] = value
    return result


def _constant(_):
    raise TransferError("nonstandard JSON constant")


def _parse_id(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{32}", value) is None:
        raise TransferError("expected lowercase 32-hex ID")
    return ObjectId.from_hex(value)


def _parse(bundle):
    if type(bundle) is not bytes:
        raise TypeError("bundle requires exact bytes")
    if len(bundle) > MAX_BUNDLE_BYTES:
        raise TransferError("encoded bundle exceeds profile limit")
    try:
        document = json.loads(
            bundle.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
        )
    except (ValueError, RecursionError):
        # Suppress parser text/cause: it may contain caller payload or enormous integers.
        raise TransferError("invalid UTF-8/JSON bundle") from None
    if type(document) is not dict or set(document) != {"format", "root", "objects"}:
        raise TransferError("expected exact bundle fields")
    if document["format"] != FORMAT:
        raise TransferError("unsupported bundle format")
    root = _parse_id(document["root"])
    objects = document["objects"]
    if type(objects) is not list or not 1 <= len(objects) <= MAX_OBJECTS:
        raise TransferError("invalid object count")
    rows, seen, total = [], set(), 0
    for row in objects:
        if type(row) is not dict or set(row) != {"kind", "id", "record"}:
            raise TransferError("expected exact row fields")
        kind = row["kind"]
        if type(kind) is not str or kind not in KINDS:
            raise TransferError("unknown immutable kind")
        key = kind, _parse_id(row["id"])
        if key in seen:
            raise TransferError("duplicate typed object")
        encoded = row["record"]
        if type(encoded) is not str or len(encoded) > 4 * ((MAX_RECORD_BYTES + 2) // 3):
            raise TransferError("invalid encoded record size/type")
        try:
            record = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise TransferError("invalid base64 record") from None
        # Re-encoding checks excess padding and unused bits on supported Python >=3.8.
        if base64.b64encode(record).decode("ascii") != encoded:
            raise TransferError("noncanonical base64 record")
        total = _record_size(record, total)
        seen.add(key)
        rows.append((key, record))
    if rows[-1][0] != ("commit", root):
        raise TransferError("root commit must be final row")
    return root, rows


def import_commit(
    repository_path, bundle: bytes, *, ref: Optional[str] = None, map_size: int = 0
) -> ImportResult:
    """Validate a self-contained bundle and publish it in one owned write batch.

    A response lost after commit does not imply rollback. Reimport is idempotent;
    an explicit ref is created or accepted at the same target, never moved.
    """
    if ref is not None:
        if type(ref) is not str:
            raise TypeError("ref requires str or None")
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", ref) is None:
            raise TransferError("invalid destination ref name")
    root, rows = _parse(bundle)
    result = ImportResult(root, len(rows), ref)
    with Repository(repository_path, map_size=map_size) as repo, repo.write() as tx:
        adjacency = {}
        for key, record in rows:
            if tx.put_record(key[0], record) != key[1]:
                raise TransferError("computed record ID differs from row ID")
            if tx.get_record(*key) != record:
                raise TransferError("stored record bytes differ from bundle")
            children = _edges(tx, *key)
            if any(child not in adjacency for child in children):
                raise TransferError("dependency requires an earlier typed bundle row")
            adjacency[key] = children
        reached, pending = set(), [("commit", root)]
        while pending:
            key = pending.pop()
            if key not in reached:
                reached.add(key)
                pending.extend(adjacency[key])
        if len(reached) != len(adjacency):
            raise TransferError("bundle contains objects outside root closure")
        if ref is not None:
            try:
                existing = tx.get_ref(ref)
            except NotFoundError:
                # A dangling existing ref can also read not_found; create never overwrites.
                tx.create_ref(ref, root)
            else:
                if existing != root:
                    raise RefConflictError("destination ref points to a different commit")
    return result
