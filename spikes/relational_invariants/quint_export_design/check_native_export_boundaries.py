"""Check limits, storage errors, and allocation cleanup for the opt-in C export hook."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import daggerml as dml
from daggerml import _core_fault, transfer

from check_export_baseline import build_fixture
from check_native_export import Limits, export_rows, read_rows
from export_fault_sweep import compare_faults


def capture_error(expected_type, function):
    try:
        function()
    except expected_type as error:
        return error
    raise AssertionError(f"Expected {expected_type.__name__}")


def compare_limits(repo, commit, expected):
    exact = Limits(len(expected), max(len(record) for _, record in expected),
                   sum(len(record) for _, record in expected))
    fields = {"MAX_OBJECTS": exact.objects, "MAX_RECORD_BYTES": exact.record,
              "MAX_PACKED_BYTES": exact.packed}
    baseline = transfer.export_commit(repo, commit=commit)
    with patch.multiple(transfer, **fields):
        assert export_rows(repo, commit) == expected
        assert transfer.export_commit(repo, commit=commit) == baseline

    checks = (("MAX_OBJECTS", replace(exact, objects=exact.objects - 1), "object count"),
              ("MAX_RECORD_BYTES", replace(exact, record=exact.record - 1), "packed record"),
              ("MAX_PACKED_BYTES", replace(exact, packed=exact.packed - 1), "total packed bytes"))
    for constant, short, diagnostic in checks:
        with patch.multiple(transfer, **(fields | {constant: fields[constant] - 1})):
            py = capture_error(transfer.TransferError, lambda: transfer.export_commit(repo, commit=commit))
            c = capture_error(transfer.TransferError, lambda: export_rows(repo, commit, short))
            assert type(c) is type(py) and str(c) == str(py) and diagnostic in str(c)
    with dml.Repository(repo) as source, source.read() as tx:
        for limits in (replace(exact, objects=0), replace(exact, record=0), replace(exact, packed=0)):
            capture_error(transfer.TransferError, lambda: read_rows(tx, commit, limits))
            assert read_rows(tx, commit, exact) == expected
        for args, error_type in (((tx._handle, commit.bytes, -1, 0, 0), ValueError),
                                 ((tx._handle, b"short", 1, 1, 1), ValueError),
                                 ((None, commit.bytes, 1, 1, 1), ValueError)):
            capture_error(error_type, lambda: dml._core._export_rows(*args))
        tx.abort()
        capture_error(dml.InvalidStateError, lambda: dml._call(dml._core._export_rows,
                      tx._handle, commit.bytes, exact.objects, exact.record, exact.packed))


def compare_storage_errors(repo, driver):
    def verify(commit, expected_code=None):
        baseline = capture_error(dml.DmlError, lambda: transfer.export_commit(repo, commit=commit))
        alternate = capture_error(dml.DmlError, lambda: export_rows(repo, commit))
        assert type(alternate) is type(baseline) and alternate.args == baseline.args
        assert (alternate.code, alternate.native_code, alternate.detail) == (
            baseline.code, baseline.native_code, baseline.detail)
        if expected_code is not None:
            assert alternate.code == expected_code
        return alternate.code

    fixture = build_fixture(repo)
    outcomes = {"absent_commit": verify(dml.ObjectId(bytes(16)), "not_found")}
    # Break an edge encountered only after the merge tree and left history complete.
    commit = dml.ObjectId.from_hex(fixture.keys["left-first"][1])
    key = f"objects/datums/{fixture.keys['map-key'][1]}"
    subprocess.run([driver, "raw-delete", repo, key], check=True, timeout=10)
    outcomes["missing_reached_child"] = verify(commit, "invalid_kind")
    subprocess.run([driver, "raw-write", repo, key], input=b"malformed datum", check=True, timeout=10)
    outcomes["corrupt_reached_child"] = verify(commit)
    assert outcomes["corrupt_reached_child"] != "not_found"
    return outcomes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-driver", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New working directory with existing parent")
    args = parser.parse_args()
    if not __debug__ or not all(hasattr(core, "_export_rows") for core in (dml._core, _core_fault)):
        parser.error("Use assertions and both staged extensions built with -Dexperimental_export_walk=true")
    args.out.mkdir(mode=0o700)
    repo = args.out / "limits.dml"
    fixture = build_fixture(repo)
    commit = dml.ObjectId.from_hex(fixture.keys["left-first"][1])
    expected = tuple((key, fixture.records[key]) for key in fixture.orders["left-first"])
    compare_limits(repo, commit, expected)
    # Separate pristine repository for error setup (then edit it with the existing raw-store driver).
    error_repo = args.out / "errors.dml"
    summary = {"limit_boundaries": "pass", **compare_faults(repo),
               **compare_storage_errors(error_repo, args.core_driver.resolve())}
    result = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (args.out / "summary.json").write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
