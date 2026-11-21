"""Run one Quint conformance rule against fresh, real DML ref histories."""

import argparse
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

import daggerml as dml
from hypothesis import given, seed, settings, strategies as st

from ref_binding import Attempt, exercise_create_ref


TARGETS = ("a", "b", "c")
RULE = "create_ref: existing ref rejects and preserves its target"
RULES_FILE = Path(__file__).with_name("ref_rules.qnt")
HISTORIES = st.lists(st.integers(0, len(TARGETS) - 1), max_size=4)


def exercise(requests: list[int]) -> tuple[Attempt, ...]:
    return exercise_create_ref(TARGETS, tuple(TARGETS[index] for index in requests))


def ref_literal(ref: dml.ObjectId | None) -> str:
    return "Absent" if ref is None else f'Target("{ref.bytes.hex()}")'


def attempt_literal(attempt: Attempt, *, mixed: bool = False) -> str:
    if attempt.error_code is None:
        outcome = "Succeeded" if mixed else "Created"
    else:
        if re.fullmatch(r"[a-z_]+", attempt.error_code) is None:
            raise ValueError(f"Unrecognized DML status token: {attempt.error_code!r}")
        outcome = f'Failed("{attempt.error_code}")'
    prefix = ""
    if mixed:
        if re.fullmatch(r"[a-z_]+", attempt.operation) is None:
            raise ValueError(f"Invalid operation identifier: {attempt.operation!r}")
        prefix = f'operation: "{attempt.operation}", '
    return (
        f'{{ {prefix}before: {ref_literal(attempt.before)}, requested: "{attempt.requested.bytes.hex()}", '
        f'outcome: {outcome}, after: {ref_literal(attempt.after)} }}'
    )


def evaluate(
    quint: Path, attempts: tuple[Attempt, ...], rules: Path = RULES_FILE, *, rule_ids: tuple[str, ...] = (),
) -> list[str]:
    """Return verdicts in attempt order, then in supplied rule order for the mixed profile."""
    mixed = bool(rule_ids)
    rules_module = "mixed_ref_rules" if mixed else "ref_rules"
    literals = ",\n    ".join(attempt_literal(attempt, mixed=mixed) for attempt in attempts)
    if mixed:
        if any(re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9]*", rule) is None for rule in rule_ids):
            raise ValueError(f"Invalid rule identifiers: {rule_ids!r}")
        ids = ", ".join(f'"{rule}"' for rule in rule_ids)
        init = (
            f"  pure val orderedRules = List({ids})\n"
            "  action init = all {\n"
            f"    ruleIds == Set({ids}),\n"
            "    verdicts' = attempts.foldl(List(), (items, a) =>\n"
            "      orderedRules.foldl(items, (results, rule) => results.append(verdict(rule, a)))),\n"
            "  }\n"
        )
    else:
        init = "  action init = verdicts' = attempts.foldl(List(), (items, a) => items.append(verdict(a)))\n"
    with TemporaryDirectory(prefix="quint-eval-") as tmp:
        directory = Path(tmp)
        shutil.copyfile(rules, directory / f"{rules_module}.qnt")
        module = directory / "observations.qnt"
        report = directory / "verdicts.json"
        module.write_text(
            'module observations {\n'
            f'  import {rules_module}.* from "./{rules_module}"\n'
            f'  pure val attempts: List[Attempt] = List({literals})\n'
            '  var verdicts: List[str]\n'
            f'{init}'
            "  action step = verdicts' = verdicts\n"
            '}\n',
            encoding="utf-8",
        )
        completed = subprocess.run(
            [quint, "run", module, "--backend=typescript", "--max-samples=1", "--max-steps=0",
             "--seed=1", "--verbosity=0", f"--out-itf={report}"],
            capture_output=True, text=True, timeout=10,
        )
        if completed.returncode != 0 or not report.is_file():
            raise RuntimeError(f"Quint produced no usable verdict (exit {completed.returncode}):\n"
                               f"{completed.stdout}{completed.stderr}")
        trace = json.loads(report.read_text(encoding="utf-8"))
    if trace["#meta"]["status"] != "ok" or trace["vars"] != ["verdicts"] or len(trace["states"]) != 1:
        raise ValueError("Expected one successful Quint ITF state with a verdicts variable")
    verdicts = trace["states"][0]["verdicts"]
    if not isinstance(verdicts, list) or len(verdicts) != len(attempts) * max(1, len(rule_ids)) or any(
        item not in ("unexercised", "pass", "violation") for item in verdicts
    ):
        raise ValueError(f"Expected one known Quint verdict per attempt and rule, got {verdicts!r}")
    return verdicts


class RefViolation(AssertionError):
    def __init__(self, requests: list[int], index: int, attempt: Attempt):
        self.requests = tuple(requests)
        super().__init__(f"{RULE}; requests={self.requests}, step={index}: {attempt_literal(attempt)}")


def require_conformance(requests: list[int], attempts: tuple[Attempt, ...], verdicts: list[str]) -> None:
    for index, (attempt, verdict) in enumerate(zip(attempts, verdicts, strict=True)):
        if verdict == "violation":
            raise RefViolation(requests, index, attempt)


def check_real_histories(quint: Path) -> None:
    requests = [0, 0, 1]
    attempts = exercise(requests)
    repeat_different = attempts[2]
    wrong_outcome = replace(repeat_different, error_code=None)
    changed_target = replace(repeat_different, after=repeat_different.requested)
    verdicts = evaluate(quint, attempts + (wrong_outcome, changed_target))
    if verdicts != ["unexercised", "pass", "pass", "violation", "violation"]:
        raise AssertionError(f"Expected fresh, same-target, different-target, and negative controls: {verdicts}")
    print(f"directed: fresh, same target, different target, wrong outcome, changed target -> {verdicts}",
          flush=True)

    counts: Counter[str] = Counter()
    histories = 0

    @settings(max_examples=24, derandomize=True, database=None, deadline=None)
    @given(HISTORIES)
    def exercise_and_check(requests: list[int]) -> None:
        nonlocal histories
        attempts = exercise(requests)
        verdicts = evaluate(quint, attempts)
        require_conformance(requests, attempts, verdicts)
        counts.update(verdicts)
        histories += 1

    exercise_and_check()
    if not counts["pass"] or not counts["unexercised"]:
        raise AssertionError(f"Generated histories did not exercise both outcomes: {dict(counts)}")
    print(f"generated: histories={histories}, {dict(counts)}", flush=True)


def check_shrinking(quint: Path) -> None:
    first_failure = None

    @seed(4120)
    @settings(max_examples=20, database=None, deadline=None)
    @given(HISTORIES)
    def check_corrupted_observations(requests: list[int]) -> None:
        nonlocal first_failure
        actual = exercise(requests)
        # Fabricate only the observed post-state of a repeat with a different target.
        # DML still executes every real create_ref call in every generated/shrunk history.
        corrupted = tuple(
            replace(a, after=a.requested) if a.before is not None and a.before != a.requested else a
            for a in actual
        )
        verdicts = evaluate(quint, actual + corrupted)
        try:
            require_conformance(requests, actual, verdicts[:len(actual)])
        except RefViolation as error:
            raise RuntimeError(f"Real observations failed during the shrink control: {error}") from error
        try:
            require_conformance(requests, corrupted, verdicts[len(actual):])
        except RefViolation as error:
            if first_failure is None:
                first_failure = error.requests
            raise  # Hypothesis sees and shrinks the failure within the property invocation.

    try:
        check_corrupted_observations()
    except RefViolation as counterexample:
        requests = counterexample.requests
        if first_failure == requests or len(requests) != 2 or requests[0] == requests[1]:
            raise AssertionError(f"Expected shrink to two different targets: {first_failure} -> {requests}")
        print(f"shrink control: {first_failure} -> {requests}\n  {counterexample}", flush=True)
    else:
        raise AssertionError("Quint did not detect the fabricated overwrite")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path, help="path to the Quint 0.33.1 executable")
    args = parser.parse_args()
    quint = args.quint.absolute()
    version = subprocess.run([quint, "--version"], check=True, capture_output=True, text=True, timeout=10)
    if version.stdout.strip() != "0.33.1":
        parser.error(f"expected Quint 0.33.1, got {version.stdout.strip()!r}")
    check_real_histories(quint)
    check_shrinking(quint)


if __name__ == "__main__":
    main()
