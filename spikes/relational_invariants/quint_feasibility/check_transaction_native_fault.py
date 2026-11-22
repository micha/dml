"""Shrink and replay a fault in the native abort of a poisoned write."""

import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
from shutil import which
import subprocess
import sys
from unittest.mock import patch

import daggerml as dml
from daggerml import _core

import generated_transactions as generated
from transaction_binding import Batch
import transaction_failure_artifact as artifact


SEED = 4120
MAX_EXAMPLES = 120
RULE = "commitPoisoned"
# A poisoned native abort can affect both endings. Exercise all commit histories
# and keep empty explicit aborts as witnesses without introducing a second failure.
HISTORIES = generated.HISTORIES.filter(lambda trace: trace[2] == "commit" or not trace[1])


def run_clean(path: Path) -> dict:
    examples, counts = artifact.run_property(path, sample_seed=SEED, max_examples=MAX_EXAMPLES,
                                             history_strategy=HISTORIES)
    assert examples == MAX_EXAMPLES and not path.exists(), (examples, path)
    passes = {rule: counts[rule, "pass"] for rule in generated.RULE_IDS}
    assert all(passes.values()), counts
    return {"examples": examples, "passes": passes}


def run_fault(path: Path) -> dict:
    check_live = generated.check
    checks = 0
    violations: list[tuple[Batch, generated.RuleViolation]] = []

    def observe_check(initial, requests, finish, batch):
        nonlocal checks
        checks += 1
        assert not path.exists(), "Wrote an evidence graph during checking or shrinking"
        try:
            return check_live(initial, requests, finish, batch)
        except generated.RuleViolation as error:
            assert error.rule == RULE, error
            violations.append((batch, error))
            raise

    try:
        with patch.object(generated, "check", observe_check):
            # No observation override: execute and check the batch returned by the adapter.
            artifact.run_property(path, sample_seed=SEED, max_examples=MAX_EXAMPLES,
                                  history_strategy=HISTORIES)
    except artifact.SavedFailure as saved:
        assert saved.rule == RULE and path.is_dir(), saved
        assert len(violations) > 1 and saved.__cause__ is not None, violations
        assert any(batch is saved.batch and error is saved.__cause__.__cause__
                   for batch, error in violations), "Saved failure does not carry the checked native batch"
        first = violations[0][0]
        assert len(saved.batch.requests) < len(first.requests), (first, saved.batch)
        return {"checks": checks, "violations": len(violations), "first": asdict(first),
                "final": asdict(saved.batch), "root": str(saved.root), "rule": saved.rule}
    raise AssertionError("The disposable native fault did not produce a saved violation")


def replay_clean(path: Path, pin: dict) -> dict:
    initial, requests, finish = pin["initial"], tuple(map(tuple, pin["requests"])), pin["finish"]
    with (patch.object(generated, "execute", side_effect=AssertionError("Replay executed the recipe")),
          patch.object(dml.Repository, "write", side_effect=AssertionError("Replay opened a writer"))):
        batch, error = artifact.replay_failure(path, dml.ObjectId.from_hex(pin["root"]),
                                               initial=initial, requests=requests, finish=finish)
    verdicts = generated.verdicts(batch.evidence)
    failures = {rule for rule, verdict in verdicts.items() if verdict == "violation"}
    assert error.rule == RULE and failures == {RULE}, verdicts

    # Separately rerun the recipe on the clean build; this is not part of replay.
    pristine = generated.execute(initial, requests, finish)
    generated.check(initial, requests, finish, pristine)
    assert batch.evidence["outcome"] == ("Failed", "invalid_state"), batch
    assert batch.evidence["markerAfter"] is True and pristine.evidence["markerAfter"] is False
    # The fault publishes any ref change already observed in the successful prefix.
    successful_refs = [step["after"] for step in batch.evidence["steps"] if step["outcome"][0] == "Succeeded"]
    assert batch.evidence["after"] == (successful_refs[-1] if successful_refs else pristine.evidence["after"])
    assert replace(batch, evidence={**batch.evidence, "markerAfter": False,
                                    "after": pristine.evidence["after"]}) == pristine
    return {"batch": asdict(batch), "rule": error.rule, "verdicts": verdicts,
            "pristine_evidence": pristine.evidence}


def run_child(phase: str, package_root: Path, path: Path, *, pin: dict | None = None) -> dict:
    args = [sys.executable, "-B", str(Path(__file__).resolve()), str(package_root),
            "--out", str(path), "--phase", phase]
    if pin is not None:
        args.extend(["--pin", json.dumps(pin)])
    result = subprocess.run(args, capture_output=True, text=True, timeout=60,
                            env={"PATH": os.environ["PATH"], "PYTHONPATH": str(package_root), "PYTHONHASHSEED": "0"})
    if result.returncode != 0:
        raise RuntimeError(f"{phase} failed ({result.returncode}):\n{result.stdout}{result.stderr}")
    return json.loads(result.stdout)


def run_all(clean_root: Path, fault_root: Path, path: Path) -> dict:
    assert clean_root != fault_root, "Clean and faulted builds must be staged separately"
    clean = run_child("clean", clean_root, path)
    fault = run_child("fault", fault_root, path)
    final = fault["final"]
    pin = {key: final[key] for key in ("initial", "requests", "finish")}
    replay = run_child("replay", clean_root, path, pin={**pin, "root": fault["root"]})
    assert replay["rule"] == fault["rule"] and replay["batch"] == final, replay
    return {"clean": clean, "fault": fault, "replay": replay}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clean_root", type=lambda path: Path(path).resolve())
    parser.add_argument("fault_root", nargs="?", type=lambda path: Path(path).resolve())
    parser.add_argument("--out", type=Path, required=True, help="New evidence repository path")
    parser.add_argument("--phase", choices=("clean", "fault", "replay"), help=argparse.SUPPRESS)
    parser.add_argument("--pin", type=json.loads, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run without optimizations to keep the checks enabled")
    if any(which(tool) is not None for tool in ("quint", "node", "npm")):
        parser.error("Run offline with no Quint, Node or npm on PATH")
    package = args.clean_root / "daggerml"
    if Path(dml.__file__).resolve().parent != package or Path(_core.__file__).resolve().parent != package:
        parser.error(f"Python and native DML must come from {package}")
    path = args.out.absolute()
    if args.phase != "replay" and (path.exists() or path.is_symlink() or not path.parent.is_dir()):
        parser.error("Expected a new evidence repository path with an existing parent directory")
    if args.phase is None and args.fault_root is not None and args.pin is None:
        result = run_all(args.clean_root, args.fault_root, path)
    elif args.fault_root is None and args.phase == "clean" and args.pin is None:
        result = run_clean(path)
    elif args.fault_root is None and args.phase == "fault" and args.pin is None:
        result = run_fault(path)
    elif args.fault_root is None and args.phase == "replay" and args.pin is not None:
        result = replay_clean(path, args.pin)
    else:
        parser.error("Supply both package roots for the offline experiment")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
