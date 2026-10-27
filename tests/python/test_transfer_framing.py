"""Strict framing/profile and malformed packed native records, with short IDs."""

import base64
import json
import struct

import daggerml as dml
from daggerml import transfer as tr
import pytest

from test_transfer import assert_absent, doc, initialize, pack, rich


@pytest.mark.parametrize(
    "mode",
    [
        "utf8",
        "empty",
        "truncate",
        "trailing",
        "duplicate-key",
        "nan",
        "deep",
        "huge-int",
        "top-type",
        "top-extra",
        "format",
        "root-type",
        "root-uppercase",
        "objects-type",
        "objects-empty",
        "row-type",
        "row-extra",
        "kind-type",
        "kind",
        "id",
        "record-type",
        "alphabet",
        "whitespace",
        "padding",
        "pad-bits",
        "nonascii",
        "duplicate",
        "root-not-last",
        "root-datum",
    ],
    ids=str,
)
def test_strict_framing_before_destination_write(tmp_path, monkeypatch, mode):
    root, _, _, _ = rich(tmp_path / "a")
    document = doc(tr.export_commit(tmp_path / "a", commit=root))
    row = document["objects"][0]
    raw = None
    if mode == "utf8":
        raw = b"\xff"
    elif mode == "empty":
        raw = b""
    elif mode == "truncate":
        raw = pack(document)[:-1]
    elif mode == "trailing":
        raw = pack(document) + b"{}"
    elif mode == "duplicate-key":
        raw = b'{"format":"x","format":"y"}'
    elif mode == "nan":
        raw = b'{"objects":NaN}'
    elif mode == "deep":
        raw = b"[" * 2000 + b"0" + b"]" * 2000
    elif mode == "huge-int":
        raw = b"9" * 10000
    elif mode == "top-type":
        document = []
    elif mode == "top-extra":
        document["extra"] = 0
    elif mode == "format":
        document["format"] = "other"
    elif mode == "root-type":
        document["root"] = 0
    elif mode == "root-uppercase":
        document["root"] = str(root).upper()
    elif mode == "objects-type":
        document["objects"] = {}
    elif mode == "objects-empty":
        document["objects"] = []
    elif mode == "row-type":
        document["objects"][0] = []
    elif mode == "row-extra":
        row["extra"] = 0
    elif mode == "kind-type":
        row["kind"] = []
    elif mode == "kind":
        row["kind"] = "ref"
    elif mode == "id":
        row["id"] = "0" * 31
    elif mode == "record-type":
        row["record"] = 0
    elif mode == "alphabet":
        row["record"] = "????"
    elif mode == "whitespace":
        row["record"] += "\n"
    elif mode == "padding":
        row["record"] += "="
    elif mode == "pad-bits":
        row["record"] = "Zh=="
    elif mode == "nonascii":
        row["record"] = "\u00ff"
    elif mode == "duplicate":
        document["objects"].insert(1, dict(row))
    elif mode == "root-not-last":
        document["objects"].reverse()
    elif mode == "root-datum":
        document["root"] = row["id"]

    def must_not_open(*args, **kwargs):
        pytest.fail("framing failure must precede repository opening")

    monkeypatch.setattr(tr, "Repository", must_not_open)
    with pytest.raises(tr.TransferError) as error:
        tr.import_commit(tmp_path / "not-created", raw if raw is not None else pack(document))
    assert len(str(error.value)) < 100


@pytest.mark.parametrize(
    "mode", ["bundle", "record-encoded", "record-decoded", "total", "count"], ids=str
)
def test_limit_rejections_both_directions(tmp_path, monkeypatch, mode):
    root, records, _, _ = rich(tmp_path / "a")
    bundle = tr.export_commit(tmp_path / "a", commit=root)
    if mode == "bundle":
        monkeypatch.setattr(tr, "MAX_BUNDLE_BYTES", len(bundle) - 1)
    elif mode == "record-encoded":
        monkeypatch.setattr(tr, "MAX_RECORD_BYTES", 1)
    elif mode == "record-decoded":
        # 40-byte datum base64 length also permits 42 decoded bytes. Bound after decode.
        document = doc(bundle)
        document["objects"][0]["record"] = base64.b64encode(b"x" * 42).decode()
        bundle = pack(document)
        monkeypatch.setattr(tr, "MAX_RECORD_BYTES", 40)
    elif mode == "total":
        monkeypatch.setattr(tr, "MAX_PACKED_BYTES", sum(len(r) for _, r in records) - 1)
    elif mode == "count":
        monkeypatch.setattr(tr, "MAX_OBJECTS", len(records) - 1)
    with pytest.raises(tr.TransferError):
        tr.import_commit(tmp_path / "not-created", bundle)
    with pytest.raises(tr.TransferError):
        tr.export_commit(tmp_path / "a", commit=root)


def test_actual_encoded_limit_before_open(tmp_path, monkeypatch, request):
    assert len(request.node.nodeid) < 160

    def must_not_open(*args, **kwargs):
        pytest.fail("oversized framing must fail before destination open")

    monkeypatch.setattr(tr, "Repository", must_not_open)
    with pytest.raises(tr.TransferError, match="encoded bundle"):
        tr.import_commit(tmp_path / "not-created", b" " * (tr.MAX_BUNDLE_BYTES + 1))


def test_actual_record_limit_export_and_import(tmp_path):
    path = tmp_path / "a"
    with dml.Repository(path, create=True) as repo, repo.write() as tx:
        datum = tx.put_datum(b"x" * tr.MAX_RECORD_BYTES)
        record = tx.get_record("datum", datum)
        root = tx.put_commit(tx.put_tree({"large": tx.put_dag(root=tx.put_literal(datum))}))
    with pytest.raises(tr.TransferError, match="packed record"):
        tr.export_commit(path, commit=root)
    document = {
        "format": tr.FORMAT,
        "root": str(root),
        "objects": [
            {"kind": "datum", "id": str(datum), "record": base64.b64encode(record).decode()}
        ],
    }
    with pytest.raises(tr.TransferError, match="encoded record"):
        tr.import_commit(tmp_path / "not-created", pack(document))


def test_limits_exact_boundary_and_whitespace_order(tmp_path, monkeypatch):
    root, records, _, _ = rich(tmp_path / "a")
    bundle = tr.export_commit(tmp_path / "a", commit=root)
    monkeypatch.setattr(tr, "MAX_BUNDLE_BYTES", len(bundle))
    monkeypatch.setattr(tr, "MAX_RECORD_BYTES", max(len(r) for _, r in records))
    monkeypatch.setattr(tr, "MAX_PACKED_BYTES", sum(len(r) for _, r in records))
    monkeypatch.setattr(tr, "MAX_OBJECTS", len(records))
    initialize(tmp_path / "b")
    assert tr.export_commit(tmp_path / "a", commit=root) == bundle
    assert tr.import_commit(tmp_path / "b", bundle).commit == root
    monkeypatch.setattr(tr, "MAX_BUNDLE_BYTES", len(bundle) * 2)
    document = doc(bundle)
    # Independent leaf rows may be permuted; writer remains canonical/deterministic.
    rows = document["objects"]
    a, b = [row for row in rows if row["kind"] == "datum"][:2]
    document["objects"] = [b, a] + [row for row in rows if row is not a and row is not b]
    assert tr.import_commit(tmp_path / "b", json.dumps(document, indent=1).encode()).commit == root


@pytest.mark.parametrize(
    "mode",
    [
        "magic",
        "version",
        "type",
        "length",
        "flags",
        "checksum",
        "negative-zero",
        "nan",
        "nfc",
        "set-order",
        "map-order",
        "name-order",
        "uri",
    ],
    ids=str,
)
def test_native_malformed_packed_records_abort_earlier_puts(tmp_path, mode):
    root, records, _, _ = rich(tmp_path / "a")
    initialize(tmp_path / "b")
    record = bytearray(records[0][1])
    if mode in ("negative-zero", "nan"):
        record = bytearray(
            next(
                r
                for (k, _), r in records
                if k == "datum" and struct.unpack_from("<I", r, 20)[0] == 4
            )
        )
        struct.pack_into(
            "<Q", record, 40, 0x8000000000000000 if mode == "negative-zero" else 0x7FF0000000000001
        )
    elif mode == "nfc":
        # A valid envelope and lengths containing decomposed rather than NFC text.
        record = bytearray(records[9][1][:40] + "e\u0301".encode())
        struct.pack_into("<I", record, 8, len(record))
        struct.pack_into("<Q", record, 24, 3)
    elif mode in ("set-order", "map-order"):
        tag, width = (9, 16) if mode == "set-order" else (10, 32)
        record = bytearray(
            next(
                r
                for (k, _), r in records
                if k == "datum" and struct.unpack_from("<I", r, 20)[0] == tag
            )
        )
        record[44 : 44 + width], record[44 + width : 44 + 2 * width] = (
            record[44 + width : 44 + 2 * width],
            record[44 : 44 + width],
        )
    elif mode == "name-order":
        record = bytearray(next(r for (k, _), r in records if k == "tree" and len(r) > 24))
        # Canonical first tree name all -> zll, now after shared.
        record[28] = ord("z")
    elif mode == "uri":
        record = bytearray(records[10][1])
        record[40:43] = b"URN"
    else:
        offset, fmt, value = {
            "magic": (0, "<I", 0),
            "version": (4, "<H", 2),
            "type": (6, "<H", 3),
            "length": (8, "<I", len(record) + 1),
            "flags": (12, "<I", 1),
            "checksum": (16, "<I", 1),
        }[mode]
        struct.pack_into(fmt, record, offset, value)
    with dml.Repository(tmp_path / "b") as repo:
        tx = repo.write()
        earlier = tx.put_datum("earlier malformed oracle")
        with pytest.raises(dml.DmlError):
            tx.put_record("tree" if mode == "name-order" else "datum", bytes(record))
        with pytest.raises(dml.InvalidStateError):
            tx.commit()
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(earlier)


@pytest.mark.parametrize("argument", ["bundle", "commit", "ref-type", "ref-name"], ids=str)
def test_argument_validation(argument):
    with pytest.raises((TypeError, tr.TransferError)):
        if argument == "commit":
            tr.export_commit("unused", commit="0" * 32)
        elif argument == "bundle":
            tr.import_commit("unused", bytearray())
        elif argument == "ref-type":
            tr.import_commit("unused", b"", ref=4)
        else:
            tr.import_commit("unused", b"", ref="bad/name")
