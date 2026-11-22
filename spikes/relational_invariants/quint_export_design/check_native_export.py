"""Compare the opt-in C walker with Python export and the unchanged Quint rules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import daggerml as dml
from daggerml import transfer

from check_export_baseline import Observation, RULE_NAMES, build_fixture, check_quint, expected_bundle


@dataclass(frozen=True)
class Limits:
    objects: int
    record: int
    packed: int


KINDS_BY_TYPE = {value: kind for kind, value in dml._TYPES.items()}


def read_rows(tx: dml.Transaction, commit: dml.ObjectId, limits: Limits | None = None):
    tx._check()
    if limits is None:
        limits = Limits(transfer.MAX_OBJECTS, transfer.MAX_RECORD_BYTES, transfer.MAX_PACKED_BYTES)
    result = dml._call(dml._core._export_rows, tx._handle, dml._id(commit),
                       limits.objects, limits.record, limits.packed)
    if isinstance(result, str):
        raise transfer.TransferError(result)
    return tuple(((KINDS_BY_TYPE[kind], oid.hex()), record) for kind, oid, record in result)


def export_rows(repo: Path, commit: dml.ObjectId, limits: Limits | None = None):
    with dml.Repository(repo) as source, source.read() as tx:
        return read_rows(tx, commit, limits)


def check_exports(quint: Path, out: Path, *, first_parent_control: bool) -> dict:
    repo = out / "source.dml"
    fixture = build_fixture(repo)
    cases, summary = [], {}
    for label, wanted in fixture.orders.items():
        root = fixture.keys[label]
        commit = dml.ObjectId.from_hex(root[1])
        baseline = transfer.export_commit(repo, commit=commit)
        expected = expected_bundle(root, wanted, fixture.records)
        assert baseline == expected, f"Python baseline changed: {label}"

        native_rows = export_rows(repo, commit)
        keys = tuple(key for key, _ in native_rows)
        assert all(record == fixture.records[key] for key, record in native_rows), label
        actual = expected_bundle(root, keys, dict(native_rows))
        if first_parent_control:
            second = "right" if label == "left-first" else "left"
            assert fixture.keys[second] not in keys, f"Control did not omit {second}"
            assert actual != baseline and keys[-1] == root, label
        else:
            assert native_rows == tuple((key, fixture.records[key]) for key in wanted), label
            assert actual == baseline, f"Native bundle differs: {label}"

        verdicts = (True, False, False) if first_parent_control else (True, True, True)
        cases.append(Observation(root, wanted, keys, verdicts))
        (out / f"{label}-native.json").write_bytes(actual)
        (out / f"{label}-python.json").write_bytes(baseline)
        summary[label] = {"rows": len(keys), "native_sha256": sha256(actual).hexdigest(),
                          "python_sha256": sha256(baseline).hexdigest(),
                          "missing": sorted(set(wanted) - set(keys))}
    for label, verdict in zip(summary, check_quint(quint, out, fixture.edges, cases), strict=True):
        summary[label]["verdicts"] = dict(zip(RULE_NAMES, verdict, strict=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New working directory with existing parent")
    parser.add_argument("--first-parent-control", action="store_true",
                        help="Require the negative verdicts from a disposable first-parent C build")
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run without optimizations to keep the checks enabled")
    if not hasattr(dml._core, "_export_rows"):
        parser.error("Use the staged runtime built with -Dexperimental_export_walk=true")
    quint = args.quint.absolute()
    version = subprocess.run([quint, "--version"], capture_output=True, text=True, check=True, timeout=10)
    if version.stdout.strip() != "0.33.1":
        parser.error(f"Expected Quint 0.33.1, got {version.stdout.strip()!r}")
    args.out.mkdir(mode=0o700)
    summary = check_exports(quint, args.out.resolve(), first_parent_control=args.first_parent_control)
    result = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (args.out / "summary.json").write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
