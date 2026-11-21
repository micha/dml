"""Measure exact transaction evidence repeats and direct versus native graph verification."""

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
import platform
from shutil import which
from statistics import median
import subprocess
import sys
from tempfile import TemporaryDirectory, gettempdir
from time import perf_counter_ns

import daggerml as dml
import generated_transactions as generated

from ref_binding import Request
from transaction_binding import Batch
from transaction_graph import load_batch, save_batch


@dataclass(frozen=True)
class Recipe:
    requests: tuple[Request, ...]
    finish: str
    ending_rule: str


INITIAL = "a"
UPDATE_A = ("update_ref", "a")
UPDATE_B = ("update_ref", "b")
RECIPES = {
    "clean": Recipe((UPDATE_A, UPDATE_B), "commit", "commitClean"),
    "near-clean": Recipe((UPDATE_B, UPDATE_B), "commit", "commitClean"),
    "poisoned": Recipe((UPDATE_B, ("create_ref", "a")), "commit", "commitPoisoned"),
    "abort": Recipe((UPDATE_A, UPDATE_B), "abort", "explicitAbort"),
}
ENDINGS = {"commitClean", "commitPoisoned", "explicitAbort"}


def expect_verdicts(recipe: Recipe, counts: Counter) -> dict[str, str]:
    expected = {rule: "pass" if rule not in ENDINGS or rule == recipe.ending_rule else "unexercised"
                for rule in ("commitClean", "commitPoisoned", "explicitAbort",
                             "continuity", "freshMarker", "stepEffects")}
    assert counts == Counter(expected.items()), counts
    return expected


def reopen(path: Path, root: dml.ObjectId, recipe: Recipe) -> Batch:
    return load_batch(path, root, initial=INITIAL, requests=recipe.requests, finish=recipe.finish)


def timed_direct(recipe: Recipe) -> tuple[Batch, Counter, dict[str, int]]:
    start = perf_counter_ns()
    batch = generated.execute(INITIAL, recipe.requests, recipe.finish)
    captured = perf_counter_ns()
    counts = generated.check(INITIAL, recipe.requests, recipe.finish, batch)
    end = perf_counter_ns()
    return batch, counts, {
        "direct_execute": captured - start,
        "direct_check": end - captured,
        "direct_total": end - start,
    }


def timed_graph(path: Path, recipe: Recipe) -> tuple[Batch, Batch, dml.ObjectId, Counter, dict[str, int]]:
    start = perf_counter_ns()
    live = generated.execute(INITIAL, recipe.requests, recipe.finish)
    captured = perf_counter_ns()
    root = save_batch(path, live)
    saved = perf_counter_ns()
    batch = reopen(path, root, recipe)
    loaded = perf_counter_ns()
    counts = generated.check(INITIAL, recipe.requests, recipe.finish, batch)
    end = perf_counter_ns()
    return live, batch, root, counts, {
        "graph_execute": captured - start,
        "graph_save": saved - captured,
        "graph_load": loaded - saved,
        "graph_check": end - loaded,
        "graph_replay": end - saved,
        "graph_post_capture": end - captured,
        "graph_total": end - start,
    }


def receipt(batch: Batch, root: dml.ObjectId, verdicts: dict[str, str]) -> dict:
    # Transport for measurement receipts only; stored evidence remains native datums.
    return {"root": str(root), "batch": asdict(batch), "verdicts": verdicts}


def collect(directory: Path, index: int, samples: int, warmup: int) -> dict:
    measurements = {name: [] for name in RECIPES}
    repeats = {}
    names = list(RECIPES)
    for iteration in range(-warmup, samples):
        offset = (iteration + index) % len(names)
        for name in names[offset:] + names[:offset]:
            recipe = RECIPES[name]
            context = (index, iteration, name)
            # Manage and clean the graph's enclosing directory outside both timers.
            # Keep the first measured graph per recipe for an independent reader.
            with TemporaryDirectory(dir=directory) as scratch:
                path = (directory if iteration == 0 else Path(scratch)) / name
                if (iteration + index + names.index(name)) % 2 == 0:
                    direct, direct_counts, direct_times = timed_direct(recipe)
                    live, reopened, root, graph_counts, graph_times = timed_graph(path, recipe)
                else:
                    live, reopened, root, graph_counts, graph_times = timed_graph(path, recipe)
                    direct, direct_counts, direct_times = timed_direct(recipe)
            assert direct == live == reopened, (context, direct, live, reopened)
            assert direct_counts == graph_counts, (context, direct_counts, graph_counts)
            observed = receipt(reopened, root, expect_verdicts(recipe, graph_counts))
            assert repeats.setdefault(name, observed) == observed, (context, repeats[name], observed)
            if iteration >= 0:
                measurements[name].append({**direct_times, **graph_times})
    return {"repeats": repeats, "measurements_ns": measurements}


def expect_rejected(message: str, path: Path, root: dml.ObjectId, recipe: Recipe) -> None:
    try:
        reopen(path, root, recipe)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Expected graph reopen to reject: {message}")


def read_controls(directory: Path, roots: dict[str, dml.ObjectId]) -> dict:
    repeats = {}
    batches = {}
    for name, recipe in RECIPES.items():
        batch = reopen(directory / name, roots[name], recipe)
        counts = generated.check(INITIAL, recipe.requests, recipe.finish, batch)
        repeats[name] = receipt(batch, roots[name], expect_verdicts(recipe, counts))
        batches[name] = batch

    assert len(set(roots.values())) == len(RECIPES), roots
    clean, neighbor = batches["clean"], batches["near-clean"]
    assert clean.requests != neighbor.requests and clean.evidence["steps"] != neighbor.evidence["steps"]
    assert {key: value for key, value in clean.evidence.items() if key != "steps"} == {
        key: value for key, value in neighbor.evidence.items() if key != "steps"
    }
    assert repeats["clean"]["verdicts"] == repeats["near-clean"]["verdicts"]
    expect_rejected("another exercise", directory / "clean", roots["clean"], RECIPES["near-clean"])

    # Same recipe, same shape and real failure outcome; change only marker publication.
    poisoned = batches["poisoned"]
    assert poisoned.evidence["markerAfter"] is False
    wrong = replace(poisoned, evidence={**poisoned.evidence, "markerAfter": True})
    path = directory / "wrong-publication"
    wrong_root = save_batch(path, wrong)
    assert wrong_root not in roots.values(), wrong_root
    recipe = RECIPES["poisoned"]
    expect_rejected("ref does not match the expected root", path, roots["poisoned"], recipe)
    changed = reopen(path, wrong_root, recipe)
    assert changed == wrong
    assert generated.verdicts(changed.evidence) == {
        **repeats["poisoned"]["verdicts"], "commitPoisoned": "violation",
    }
    try:
        generated.check(INITIAL, recipe.requests, recipe.finish, changed)
    except generated.RuleViolation as error:
        assert error.rule == "commitPoisoned", error
    else:
        raise AssertionError("Changed publication escaped full graph verification")
    return {"repeats": repeats, "wrong_root": str(wrong_root)}


def run_child(hash_seed: int, *args: str) -> dict:
    env = {**os.environ, "PYTHONHASHSEED": str(hash_seed)}
    command = [sys.executable, "-B", str(Path(__file__).resolve()), *args]
    result = subprocess.run(command, text=True, capture_output=True, env=env, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"{command} failed ({result.returncode}):\n{result.stdout}{result.stderr}")
    return json.loads(result.stdout)


def measure(processes: int, samples: int, warmup: int) -> dict:
    workers = []
    with TemporaryDirectory(prefix="quint-txn-measure-") as tmp:
        directory = Path(tmp)
        for index in range(processes):
            worker = directory / str(index)
            worker.mkdir()
            result = run_child(index + 1, "--worker", str(worker), str(index),
                               "--samples", str(samples), "--warmup", str(warmup))
            workers.append(result)
        baseline = workers[0]["repeats"]
        assert all(worker["repeats"] == baseline for worker in workers), "Independent executions differed"
        reader = run_child(processes + 1, "--reader", str(directory / "0"),
                           *(baseline[name]["root"] for name in RECIPES))
        assert reader["repeats"] == baseline, "Fresh reader did not recover the independently captured batch"
    return {"processes": processes, "samples_per_recipe_per_process": samples, "warmup": warmup,
            "python": sys.version, "platform": platform.platform(), "tmp_parent": gettempdir(),
            "repeats": baseline, "wrong_root": reader["wrong_root"],
            "workers_ns": [worker["measurements_ns"] for worker in workers]}


def report(result: dict) -> None:
    processes, samples, warmup = result["processes"], result["samples_per_recipe_per_process"], result["warmup"]
    print(f"{processes} fresh workers; {samples} measured pairs and {warmup} warmup pairs per recipe per worker.")
    print("All paired batches, same-recipe roots and six verdicts agree, including a separate reader process.")
    for name in RECIPES:
        print(f"  {name}: {result['repeats'][name]['root']}")
    print(f"Changed marker publication: {result['wrong_root']} violates commitPoisoned; "
          "wrong root and wrong recipe also rejected.")
    print("Median [min, max] microseconds; replay is an in-process reopen immediately after save.")
    print(f"{'stage':<20}" + "".join(f"{name:>27}" for name in RECIPES))
    workers = result["workers_ns"]
    for stage in workers[0]["clean"][0]:
        row = f"{stage:<20}"
        for name in RECIPES:
            values = [pair[stage] / 1000 for worker in workers for pair in worker[name]]
            row += f"{f'{median(values):.1f} [{min(values):.1f}, {max(values):.1f}]':>27}"
        print(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processes", type=int, default=4)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--json", type=Path, help="Save raw nanosecond measurements and exact evidence receipts")
    internal = parser.add_mutually_exclusive_group()
    internal.add_argument("--worker", nargs=2, help=argparse.SUPPRESS)
    internal.add_argument("--reader", nargs=1 + len(RECIPES), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run without Python optimizations to keep the evidence checks enabled")
    if any(which(tool) is not None for tool in ("quint", "node", "npm")):
        parser.error("Run from the offline stage with no Quint, Node or npm on PATH")
    if args.processes < 2 or args.samples < 1 or args.warmup < 0:
        parser.error("Need at least two processes, one sample per recipe, and nonnegative warmup")
    if args.worker is not None:
        path, index = args.worker
        print(json.dumps(collect(Path(path), int(index), args.samples, args.warmup)))
    elif args.reader is not None:
        path, *pins = args.reader
        roots = dict(zip(RECIPES, map(dml.ObjectId.from_hex, pins), strict=True))
        print(json.dumps(read_controls(Path(path), roots)))
    else:
        result = measure(args.processes, args.samples, args.warmup)
        if args.json is not None:
            args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        report(result)


if __name__ == "__main__":
    main()
