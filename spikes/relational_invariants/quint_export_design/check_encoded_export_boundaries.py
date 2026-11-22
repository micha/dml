"""Compare full export bytes and profile error precedence against the Python exporter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import daggerml as dml
from daggerml import transfer

from check_export_baseline import build_fixture, expected_bundle
from native_export import export_commit_native

_EXPORTERS = (transfer.export_commit, export_commit_native)


def check_error(repo, commit, expected_type: type[Exception], expected_message: str) -> None:
    for export in _EXPORTERS:
        try:
            export(repo, commit=commit)
        except expected_type as error:
            assert type(error) is expected_type, (export.__name__, type(error))
            message = error.code if isinstance(error, dml.DmlError) else str(error)
            assert message == expected_message, (export.__name__, message, expected_message)
        else:
            raise AssertionError(f"{export.__name__} accepted input expected to fail: {expected_message}")


def check_boundaries(repo: Path) -> dict[str, int]:
    fixture = build_fixture(repo)
    sizes = {}
    for label, order in fixture.orders.items():
        root = fixture.keys[label]
        commit = dml.ObjectId.from_hex(root[1])
        expected = expected_bundle(root, order, fixture.records)
        packed_sizes = [len(fixture.records[key]) for key in order]
        exact = dict(
            MAX_BUNDLE_BYTES=len(expected),
            MAX_OBJECTS=len(order),
            MAX_RECORD_BYTES=max(packed_sizes),
            MAX_PACKED_BYTES=sum(packed_sizes),
        )
        with patch.multiple(transfer, **exact):
            for export in _EXPORTERS:
                assert export(repo, commit=commit) == expected, (export.__name__, label)
            for limit in (len(expected) - 1, 0):
                with patch.object(transfer, "MAX_BUNDLE_BYTES", limit):
                    check_error(repo, commit, transfer.TransferError, "encoded bundle exceeds profile limit")
            # Size rejection must not poison subsequent exports from the same repository.
            for export in _EXPORTERS:
                assert export(repo, commit=commit) == expected, (export.__name__, label)
        sizes[label] = len(expected)

    # Discovery starts at the root, not the first emitted row. The tree is reached
    # before the larger list. Make aggregate overflow at the tree win over that later record.
    commit = dml.ObjectId.from_hex(fixture.keys["left-first"][1])
    root_size = len(fixture.records[fixture.keys["left-first"]])
    tree_size = len(fixture.records[fixture.keys["top-tree"]])
    list_size = len(fixture.records[fixture.keys["list"]])
    assert tree_size <= root_size < list_size
    with patch.multiple(transfer, MAX_BUNDLE_BYTES=0, MAX_RECORD_BYTES=root_size,
                        MAX_PACKED_BYTES=root_size + tree_size - 1):
        check_error(repo, commit, transfer.TransferError, "total packed bytes exceed profile limit")

    # Hold both budgets just below the list's required size; per-record wins on that row.
    before_list = ("left-first", "top-tree", "main-dag", "main-node")
    before_list_bytes = sum(len(fixture.records[fixture.keys[label]]) for label in before_list)
    with patch.multiple(transfer, MAX_BUNDLE_BYTES=0, MAX_RECORD_BYTES=list_size - 1,
                        MAX_PACKED_BYTES=before_list_bytes + list_size - 1):
        check_error(repo, commit, transfer.TransferError, "packed record exceeds profile limit")
        with patch.object(transfer, "MAX_OBJECTS", len(before_list)):
            check_error(repo, commit, transfer.TransferError, "object count exceeds profile limit")

    # The encoded limit is applied after traversal, including native storage lookup.
    with patch.object(transfer, "MAX_BUNDLE_BYTES", 0):
        check_error(repo, dml.ObjectId(bytes(16)), dml.NotFoundError, "not_found")
    check_error(None, "not an ObjectId", TypeError, "commit requires ObjectId")
    return sizes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New working directory with existing parent")
    args = parser.parse_args()
    if not __debug__ or not hasattr(dml._core, "_export_rows"):
        parser.error("Use assertions and the staged extension built with -Dexperimental_export_walk=true")
    args.out.mkdir(mode=0o700)
    sizes = check_boundaries(args.out / "encoded.dml")
    result = json.dumps({"encoded_bytes": sizes, "limit_boundaries": "pass", "precedence": "pass"},
                        indent=2, sort_keys=True) + "\n"
    (args.out / "summary.json").write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
