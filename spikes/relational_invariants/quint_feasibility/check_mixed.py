"""Check the generated mixed-ref profile against Quint and run it without Quint."""

import argparse
from collections import Counter
from dataclasses import replace
from itertools import batched, chain, product
from pathlib import Path
from shutil import which

import generated_mixed as generated

from ref_binding import Attempt, Request


RULES = Path(__file__).with_name("mixed_ref_rules.qnt")


def compare_with_quint(quint: Path) -> None:
    from exercise_ref import evaluate

    alphabet = tuple(product(generated.OPERATIONS, generated.TARGETS))
    histories = [history for size in range(generated.MAX_STEPS + 1) for history in product(alphabet, repeat=size)]
    attempts = tuple(chain.from_iterable(generated.execute(history) for history in histories))
    commits = tuple(generated.execute([("create_ref", target)])[0].requested for target in generated.TARGETS)
    assert len(set(commits)) == len(generated.TARGETS), "abstract targets did not map to distinct commits"
    refs = (None, *commits)
    matrix = tuple(
        Attempt(before, requested, code, after, operation)
        for operation, before, requested, code, after in
        product(generated.OPERATIONS, refs, commits, (None, "invalid_state", "not_found"), refs)
    )

    def compare(cases: tuple[Attempt, ...]) -> dict[str, Counter[str]]:
        counts: dict[str, Counter[str]] = {rule: Counter() for rule in generated.RULE_IDS}
        for batch in batched(cases, 32):
            direct = evaluate(quint, batch, RULES, rule_ids=generated.RULE_IDS)
            python = ((attempt, rule, result) for attempt in batch
                      for rule, result in generated.verdicts(attempt).items())
            for expected, (attempt, rule, actual) in zip(direct, python, strict=True):
                if actual != expected:
                    raise AssertionError(f"{rule}: Quint={expected}, Python={actual} on {attempt!r}")
                counts[rule][actual] += 1
        return counts

    actual_counts = compare(attempts)
    synthetic_counts = compare(matrix)
    assert len(histories) == 85 and len(attempts) == 228 and len(matrix) == 108
    assert actual_counts == {
        "duplicateCreate": {"pass": 44, "unexercised": 184},
        "updateExisting": {"pass": 44, "unexercised": 184},
        "updateMissing": {"pass": 70, "unexercised": 158},
    }
    assert synthetic_counts == {
        "duplicateCreate": {"pass": 4, "unexercised": 72, "violation": 32},
        "updateExisting": {"pass": 4, "unexercised": 72, "violation": 32},
        "updateMissing": {"pass": 2, "unexercised": 90, "violation": 16},
    }
    print(f"agreement: {len(histories)} histories, {len(attempts)} actual and {len(matrix)} synthetic attempts, "
          f"{(len(attempts) + len(matrix)) * len(generated.RULE_IDS)} identical verdicts")
    for rule in generated.RULE_IDS:
        print(f"  {rule}: actual={dict(actual_counts[rule])}, synthetic={dict(synthetic_counts[rule])}")


def check_without_quint() -> None:
    if any(which(tool) is not None for tool in ("quint", "node", "npm")):
        raise RuntimeError("Use the offline staging directory with an empty tool PATH")
    requests = [("create_ref", "a"), ("create_ref", "b")]
    actual = generated.execute(requests)
    try:
        generated.check(requests, actual[:1])
    except ValueError as error:
        assert "one DML observation per requested action" in str(error), error
    else:
        raise AssertionError("the generated checker accepted incomplete evidence")
    try:
        generated.check(requests, (replace(actual[0], operation="update_ref"), actual[1]))
    except ValueError as error:
        assert "Observation operation mismatch at step 0" in str(error), error
    else:
        raise AssertionError("the generated checker accepted mismatched action evidence")
    try:
        generated.require_witnesses(generated.check(requests, actual))
    except AssertionError as error:
        assert str(error) == "Rules with no matching exercise in the suite: updateExisting, updateMissing", error
        print(f"offline non-vacuity control: {error}")
    else:
        raise AssertionError("one matched rule concealed two unexercised rules")

    histories, counts = generated.run_property(sample_seed=4120, max_examples=40)
    assert histories > 0 and all(counts[rule, "pass"] for rule in generated.RULE_IDS)
    matches = {rule: counts[rule, "pass"] for rule in generated.RULE_IDS}
    print(f"offline: {histories} generated histories; matching passes={matches}", flush=True)

    first_failure: tuple[Request, ...] | None = None

    def corrupt(trace: list[Request], attempts: tuple[Attempt, ...]) -> tuple[Attempt, ...]:
        nonlocal first_failure
        corrupted = tuple(
            replace(attempt, error_code="invalid_state", after=attempt.before)
            if attempt.operation == "update_ref" and attempt.before is not None and attempt.before != attempt.requested
            else attempt
            for attempt in attempts
        )
        if first_failure is None and corrupted != attempts:
            first_failure = tuple(trace)
        return corrupted

    try:
        generated.run_property(sample_seed=4120, max_examples=40, corrupt=corrupt)
    except generated.RuleViolation as error:
        assert error.rule == "updateExisting", error
        assert first_failure is not None and len(first_failure) > 2, first_failure
        assert [operation for operation, _ in error.requests] == ["create_ref", "update_ref"], error
        assert error.requests[0][1] != error.requests[1][1], error
        print(f"offline shrink: {first_failure} -> {error.requests}\n  {error}", flush=True)
    else:
        raise AssertionError("the generated property did not detect the fabricated failed update")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_subparsers(dest="mode", required=True)
    mode.add_parser("offline")
    differential = mode.add_parser("differential")
    differential.add_argument("--quint", required=True, type=Path)
    args = parser.parse_args()
    if args.mode == "offline":
        check_without_quint()
    else:
        compare_with_quint(args.quint.absolute())


if __name__ == "__main__":
    main()
