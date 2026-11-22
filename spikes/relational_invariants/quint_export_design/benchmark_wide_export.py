"""Compare wide tree/DAG scaling across two staged Linux release runtimes."""

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


HERE = Path(__file__).resolve().parent
CASES = tuple(
    f"{shape}:{size}"
    for shape in ("wide-tree", "wide-bindings")
    for size in (1024, 4096, 8192, 16384)
)
OPERATIONS = ("get-packed", "put-packed", "decode", "lookup-last", "python-export", "native-export")


def digest_files(*files: Path) -> dict[str, str]:
    return {str(file): sha256(file.read_bytes()).hexdigest() for file in files}


def runtime() -> dict:
    import daggerml as dml
    from daggerml import transfer

    stage = Path(os.environ["PYTHONPATH"]) / "daggerml"
    modules = {"wrapper": dml, "transfer": transfer, "core": dml._core}
    files = {name: Path(module.__file__).resolve() for name, module in modules.items()}
    if any(file.parent != stage for file in files.values()):
        raise RuntimeError(f"Expected staged modules under {stage}, got {files}")
    if not hasattr(dml._core, "_export_rows"):
        raise RuntimeError("Use a release runtime built with -Dexperimental_export_walk=true")
    return {name: {"path": str(file), "sha256": sha256(file.read_bytes()).hexdigest()}
            for name, file in files.items()}


def prepare(directory: Path, case: str) -> dict:
    """One immutable read fixture and one dependency-only fixture for aborted puts."""
    import daggerml as dml
    from daggerml import transfer

    from benchmark_export import build_fixture

    shape, size = case.split(":")
    path = directory / "read.dml"
    commit, expected_rows = build_fixture(path, shape, int(size))
    bundle = transfer.export_commit(path, commit=commit)
    root, rows = transfer._parse(bundle)
    if root != commit or len(rows) != expected_rows or tuple(key[0] for key, _ in rows) != transfer.KINDS:
        raise AssertionError(f"Unexpected root or row order for {case}")

    # Prefix ends before the wide record; each measured put is a fresh insert.
    index = 3 if shape == "wide-tree" else 2
    (kind, oid), packed = rows[index]
    with dml.Repository(directory / "write.dml", create=True) as repo, repo.write() as tx:
        for (dependency_kind, expected), record in rows[:index]:
            if tx.put_record(dependency_kind, record) != expected:
                raise AssertionError(f"Unexpected dependency ID for {case}")

    (directory / "bundle.json").write_bytes(bundle)
    (directory / "wide.record").write_bytes(packed)
    return {"size": int(size), "kind": kind, "root": str(commit), "record_id": str(oid),
            "target_id": str(rows[index - 1][0][1]), "rows": len(rows), "record_bytes": len(packed),
            "bundle_bytes": len(bundle), "bundle_sha256": sha256(bundle).hexdigest()}


def timed(call, *args, **kwargs) -> tuple[object, int]:
    start = perf_counter_ns()
    result = call(*args, **kwargs)
    return result, perf_counter_ns() - start


def sample(directory: Path, operation: str) -> dict:
    import daggerml as dml

    from benchmark_export import EXPORTERS

    fixture = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    kind = fixture["kind"]
    width = fixture["size"]
    oid = dml.ObjectId.from_hex(fixture["record_id"])
    target = dml.ObjectId.from_hex(fixture["target_id"])
    path = directory / "read.dml"
    if operation.endswith("-export"):
        commit = dml.ObjectId.from_hex(fixture["root"])
        exporter = EXPORTERS[operation.split("-", 1)[0]]
        result, elapsed = timed(exporter, path, commit=commit)
        expected = (directory / "bundle.json").read_bytes()
    elif operation == "decode":
        packed = (directory / "wide.record").read_bytes()
        result, elapsed = timed(dml._call, dml._core.decode_object, packed)
        prefix, reference = ("t", bytes(16)) if kind == "tree" else ("b", target.bytes)
        expected = reference, tuple((f"{prefix}{index:05}", target.bytes) for index in range(width))
    elif operation == "put-packed":
        packed = (directory / "wide.record").read_bytes()
        with dml.Repository(directory / "write.dml") as repo, repo.write() as tx:
            result, elapsed = timed(tx.put_record, kind, packed)
            tx.abort()
        expected = oid
    else:
        with dml.Repository(path) as repo, repo.read() as tx:
            if operation == "get-packed":
                result, elapsed = timed(tx.get_record, kind, oid)
                expected = (directory / "wide.record").read_bytes()
            elif operation == "lookup-last" and kind == "dag":
                result, elapsed = timed(tx.lookup_node, oid, f"b{width - 1:05}")
                expected = target
            else:
                raise ValueError(f"Unknown operation for {kind}: {operation}")
    if result != expected:
        raise AssertionError(f"Result differs for {directory.name}: {operation}")
    return {"elapsed_ns": elapsed}


def run_worker(stage: Path, *args: str) -> dict:
    child = subprocess.run(
        [sys.executable, "-B", __file__, "_worker", *args],
        env={**os.environ, "PYTHONPATH": str(stage)}, capture_output=True, text=True, timeout=120,
    )
    if child.returncode:
        raise RuntimeError(f"{stage}: {' '.join(args)}: exit {child.returncode}\n{child.stderr}")
    return json.loads(child.stdout)


def worker(args: list[str]) -> None:
    command, *arguments = args
    if command == "runtime":
        result = runtime()
    elif command == "prepare":
        result = prepare(Path(arguments[0]), arguments[1])
    elif command == "sample":
        result = sample(Path(arguments[0]), arguments[1])
    else:
        raise ValueError(f"Unknown worker command: {command}")
    print(json.dumps(result))


def benchmark_case(directory: Path, case: str, stages: dict[str, Path], repeats: int) -> dict:
    directory.mkdir()
    fixture = run_worker(stages["baseline"], "prepare", str(directory), case)
    (directory / "fixture.json").write_text(json.dumps(fixture) + "\n", encoding="utf-8")
    measurements = {}
    for operation in OPERATIONS:
        if operation == "lookup-last" and fixture["kind"] != "dag":
            continue
        # Warm each operation for both builds before alternating their timed order.
        for stage in stages.values():
            run_worker(stage, "sample", str(directory), operation)
        samples = []
        for repeat in range(repeats):
            order = stages if repeat % 2 == 0 else reversed(stages)
            for label in order:
                result = run_worker(stages[label], "sample", str(directory), operation)
                samples.append({"runtime": label, **result})
        timings = {label: median(run["elapsed_ns"] for run in samples if run["runtime"] == label) / 1e6
                   for label in stages}
        measurements[operation] = {"median_ms": timings, "samples": samples}
        baseline = timings["baseline"]
        candidate = timings.get("candidate")
        comparison = f" {candidate:10.3f} {baseline / candidate:8.2f}" if candidate is not None else ""
        print(f"{case:<20} {operation:<14} {baseline:10.3f}{comparison}", flush=True)
    return {**fixture, "operations": measurements}


def main() -> None:
    if sys.argv[1:2] == ["_worker"]:
        worker(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-python", type=Path, required=True, help="Staged baseline Python import path")
    parser.add_argument("--candidate-python", type=Path, help="Staged candidate import path; omit for baseline only")
    parser.add_argument("--out", type=Path, required=True, help="New output directory with existing parent")
    parser.add_argument("--case", action="append", choices=CASES, help="Run only selected case(s)")
    parser.add_argument("--repeats", type=int, default=6, help="Timed samples per runtime per operation")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("The benchmark is a Linux warm-cache comparison")
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    if args.case and len(set(args.case)) != len(args.case):
        parser.error("--case must not be repeated for the same fixture")

    stages = {"baseline": args.baseline_python.resolve()}
    if args.candidate_python is not None:
        stages["candidate"] = args.candidate_python.resolve()
        if stages["candidate"] == stages["baseline"]:
            parser.error("Stage baseline and candidate in distinct directories")
    runtimes = {label: run_worker(stage, "runtime") for label, stage in stages.items()}
    if "candidate" in runtimes:
        baseline, candidate = runtimes["baseline"], runtimes["candidate"]
        if baseline["core"]["sha256"] == candidate["core"]["sha256"]:
            parser.error("Stage different baseline and candidate core binaries")
        for name in ("wrapper", "transfer"):
            if baseline[name]["sha256"] != candidate[name]["sha256"]:
                parser.error(f"Keep the Python {name} bytes identical across runtimes")
    inputs = (Path(__file__).resolve(), HERE / "benchmark_export.py", HERE / "native_export.py")
    report = {"platform": platform.platform(), "python": sys.version, "affinity": sorted(os.sched_getaffinity(0)),
              "files": digest_files(*inputs), "runtimes": runtimes, "repeats": args.repeats, "cases": {}}
    out = args.out.resolve()
    out.mkdir(mode=0o700)
    comparison = f" {'after ms':>10} {'speedup':>8}" if "candidate" in stages else ""
    print(f"{'case':<20} {'operation':<14} {'before ms':>10}{comparison}", flush=True)
    for case in args.case or CASES:
        directory = out / case.replace(":", "-")
        report["cases"][case] = benchmark_case(directory, case, stages, args.repeats)
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
