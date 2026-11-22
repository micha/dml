"""Spike-only full exporter using the opt-in C walker and Python bundle framing."""

from __future__ import annotations

import base64
import json

import daggerml as dml
from daggerml import transfer

_KINDS_BY_TYPE = {code: kind for kind, code in dml._TYPES.items()}


def read_packed_rows(repository_path, commit: dml.ObjectId) -> tuple[tuple[int, bytes, bytes], ...]:
    """Acquire owned postorder rows in one read transaction, translating profile failures."""
    if not isinstance(commit, dml.ObjectId):
        raise TypeError("commit requires ObjectId")
    with dml.Repository(repository_path) as repo, repo.read() as tx:
        rows = dml._call(
            dml._core._export_rows,
            tx._handle,
            dml._id(commit),
            transfer.MAX_OBJECTS,
            transfer.MAX_RECORD_BYTES,
            transfer.MAX_PACKED_BYTES,
        )
        if isinstance(rows, str):
            raise transfer.TransferError(rows)
        return rows


def export_commit_native(repository_path, *, commit: dml.ObjectId) -> bytes:
    """Export one pinned commit with the public exporter's canonical Python framing."""
    rows = [
        {
            "kind": _KINDS_BY_TYPE[kind],
            "id": oid.hex(),
            "record": base64.b64encode(record).decode("ascii"),
        }
        for kind, oid, record in read_packed_rows(repository_path, commit)
    ]
    bundle = json.dumps(
        {"format": transfer.FORMAT, "root": str(commit), "objects": rows},
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(bundle) > transfer.MAX_BUNDLE_BYTES:
        raise transfer.TransferError("encoded bundle exceeds profile limit")
    return bundle
