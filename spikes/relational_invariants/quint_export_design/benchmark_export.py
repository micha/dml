"""Measure public Python export against the private C-row candidate on Linux."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
from statistics import median
import subprocess
import sys
from time import perf_counter_ns

import daggerml as dml
from daggerml import transfer

import native_export


CASES = {
    "shared": (128, 1024, 8192),
    "deep": (128, 1024, 8192),
    "wide-tree": (128, 1024, 4096, 16384),
    "wide-bindings": (128, 1024, 4096, 16384),
    "payload": (1, 4, 12),
}
EXPORTERS = {"python": transfer.export_commit, "native": native_export.export_commit_native}
MIB = 1024 * 1024


def build_fixture(path: Path, shape: str, size: int) -> tuple[dml.ObjectId, int]:
    """Build one closure; return the commit and its independently known row count."""
    with dml.Repository(path, create=True) as repo, repo.write() as tx:
        if shape == "deep":
            tree = tx.put_tree({})
            commit = tx.put_commit(tree)
            for _ in range(size - 1):
                commit = tx.put_commit(tree, parents=[commit])
            return commit, size + 1

        if shape == "payload":
            chunks = [tx.put_datum(bytes([index]) * MIB) for index in range(size)]
            node = tx.put_literal(tx.put_datum(dml.Datum.list(chunks)))
            dag = tx.put_dag(root=node)
            return tx.put_commit(tx.put_tree({"data": dag})), size + 5

        node = tx.put_literal(tx.put_datum("shared payload"))
        if shape == "wide-bindings":
            dag = tx.put_dag(root=node, bindings=((f"b{index:05}", node) for index in range(size)))
            return tx.put_commit(tx.put_tree({"dag": dag})), 5

        dag = tx.put_dag(root=node)
        if shape == "wide-tree":
            tree = tx.put_tree((f"t{index:05}", dag) for index in range(size))
            return tx.put_commit(tree), 5

        if shape != "shared":
            raise ValueError(f"Unknown fixture shape: {shape}")
        left_tree, right_tree = tx.put_tree({"left": dag}), tx.put_tree({"right": dag})
        commit = tx.put_commit(left_tree)
        # Each diamond has distinct parents that both point at the previous merge.
        for _ in range(size):
            left = tx.put_commit(left_tree, parents=[commit])
            right = tx.put_commit(right_tree, parents=[commit])
            commit = tx.put_commit(left_tree, parents=[left, right])
        return commit, 3 * size + 6


def check_bytes(path: Path, commit: dml.ObjectId, expected_rows: int) -> dict:
    baseline = transfer.export_commit(path, commit=commit)
    if baseline != native_export.export_commit_native(path, commit=commit):
        raise AssertionError(f"Bundle bytes differ: {path}")
    root, rows = transfer._parse(baseline)
    if root != commit or len(rows) != expected_rows:
        raise AssertionError(f"Unexpected bundle root or row count: {path}")
    return {"rows": len(rows), "packed_bytes": sum(len(record) for _, record in rows),
            "bundle_bytes": len(baseline), "sha256": sha256(baseline).hexdigest()}


def peak_rss_kib() -> int:
    # VmHWM is for this exec, unlike ru_maxrss which can carry a pre-exec high-water mark.
    with open("/proc/self/status", encoding="ascii") as status:
        for line in status:
            if line.startswith("VmHWM:"):
                _, value, unit = line.split()
                if unit == "kB":
                    return int(value)
                break
    raise RuntimeError("Linux /proc/self/status did not report VmHWM in KiB")


def time_export(export, path: Path, commit: dml.ObjectId) -> tuple[bytes, int, int]:
    start = perf_counter_ns()
    bundle = export(path, commit=commit)
    end = perf_counter_ns()
    return bundle, start, end


def diagnose_phases(exporter: str, path: Path, commit: dml.ObjectId) -> tuple[bytes, dict]:
    from unittest.mock import patch

    dumps = transfer.json.dumps
    read_rows = native_export.read_packed_rows
    stamps = {}

    def mark_json(*args, **kwargs):
        stamps["json_start"] = perf_counter_ns()
        return dumps(*args, **kwargs)

    def mark_rows(*args, **kwargs):
        rows = read_rows(*args, **kwargs)
        stamps["rows_end"] = perf_counter_ns()
        return rows

    with patch.object(transfer.json, "dumps", mark_json):
        if exporter == "native":
            with patch.object(native_export, "read_packed_rows", mark_rows):
                bundle, start, end = time_export(EXPORTERS[exporter], path, commit)
        else:
            bundle, start, end = time_export(EXPORTERS[exporter], path, commit)
    json_start = stamps["json_start"]
    phases = {"json_utf8_and_limit_ns": end - json_start}
    if exporter == "native":
        rows_end = stamps["rows_end"]
        phases.update(acquire_and_bind_ns=rows_end - start, base64_and_row_dicts_ns=json_start - rows_end)
    else:
        phases["walk_base64_and_row_dicts_ns"] = json_start - start
    return bundle, phases


def sample(args: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Run one export measurement in a fresh process")
    parser.add_argument("kind", choices=("timed", "phases"))
    parser.add_argument("exporter", choices=EXPORTERS)
    parser.add_argument("repo", type=Path)
    parser.add_argument("commit")
    args = parser.parse_args(args)
    commit = dml.ObjectId.from_hex(args.commit)
    if args.kind == "timed":
        bundle, start, end = time_export(EXPORTERS[args.exporter], args.repo, commit)
        result = {"peak_rss_kib": peak_rss_kib(), "elapsed_ns": end - start}
    else:
        bundle, result = diagnose_phases(args.exporter, args.repo, commit)
    result.update(bundle_bytes=len(bundle), sha256=sha256(bundle).hexdigest())
    print(json.dumps(result))


def run_sample(kind: str, exporter: str, path: Path, commit: dml.ObjectId, expected: dict) -> dict:
    child = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "_sample", kind, exporter, str(path), str(commit)],
        capture_output=True, text=True, timeout=120,
    )
    if child.returncode:
        raise RuntimeError(f"{kind} {exporter} {path.name}: exit {child.returncode}\n{child.stderr}")
    result = json.loads(child.stdout)
    if (result.pop("bundle_bytes"), result.pop("sha256")) != (expected["bundle_bytes"], expected["sha256"]):
        raise AssertionError(f"Worker bundle differs: {kind} {exporter} {path}")
    return result


def benchmark_case(out: Path, case: str, repeats: int) -> dict:
    shape, size = case.split(":")
    path = out / f"{shape}-{size}.dml"
    commit, expected_rows = build_fixture(path, shape, int(size))
    # Direct byte equality outside the measurements also warms the filesystem cache.
    expected = check_bytes(path, commit, expected_rows)
    samples = []
    for repeat in range(repeats):
        order = tuple(EXPORTERS) if repeat % 2 == 0 else tuple(reversed(EXPORTERS))
        for exporter in order:
            samples.append({"exporter": exporter, **run_sample("timed", exporter, path, commit, expected)})
    return {**expected, "root": str(commit), "samples": samples,
            "phases": {exporter: run_sample("phases", exporter, path, commit, expected) for exporter in EXPORTERS}}


def report_line(case: str, result: dict) -> str:
    times, peaks = [], []
    for exporter in EXPORTERS:
        runs = [sample for sample in result["samples"] if sample["exporter"] == exporter]
        times.append(median(sample["elapsed_ns"] for sample in runs) / 1e6)
        peaks.append(median(sample["peak_rss_kib"] for sample in runs) / 1024)
    return (f"{case:<20} {result['rows']:>6} {times[0]:>10.2f} {times[1]:>10.2f}"
            f" {times[0] / times[1]:>8.2f} {peaks[0]:>10.2f} {peaks[1]:>10.2f}")


def main() -> None:
    if sys.argv[1:2] == ["_sample"]:
        sample(sys.argv[2:])
        return
    cases = tuple(f"{shape}:{size}" for shape, sizes in CASES.items() for size in sizes)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory with existing parent")
    parser.add_argument("--case", action="append", choices=cases, help="Run only the selected case(s)")
    parser.add_argument("--repeats", type=int, default=5, help="Timed samples per exporter per case")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("This experiment uses Linux /proc for peak RSS")
    if not hasattr(dml._core, "_export_rows"):
        parser.error("Use the staged runtime built with -Dexperimental_export_walk=true")
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    if args.case and len(set(args.case)) != len(args.case):
        parser.error("--case must not be repeated for the same fixture")

    out = args.out.resolve()
    out.mkdir(mode=0o700)
    files = [__file__, native_export.__file__, transfer.__file__, dml.__file__, dml._core.__file__]
    report = {"platform": platform.platform(), "python": sys.version, "affinity": sorted(os.sched_getaffinity(0)),
              "files": {str(Path(file).resolve()): sha256(Path(file).read_bytes()).hexdigest() for file in files},
              "repeats": args.repeats, "cases": {}}
    print(f"{'case':<20} {'rows':>6} {'Python ms':>10} {'C path ms':>10}"
          f" {'speedup':>8} {'Python MiB':>10} {'C path MiB':>10}", flush=True)
    for case in args.case or cases:
        result = benchmark_case(out, case, args.repeats)
        report["cases"][case] = result
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(report_line(case, result), flush=True)


if __name__ == "__main__":
    main()
