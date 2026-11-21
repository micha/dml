"""Measure direct Quint agreement and test the generated property without Quint or Node."""

import argparse
from collections import Counter
from dataclasses import replace
from itertools import batched, product
from pathlib import Path
from shutil import which

import generated_ref as generated


def compare_with_quint(quint: Path, source: Path | None, changed_profile: bool) -> None:
    from exercise_ref import RULES_FILE, evaluate
    from ref_binding import Attempt, observation

    source = source or RULES_FILE
    targets = generated.TARGETS
    histories = [history for n in range(generated.MAX_STEPS + 1) for history in product(targets, repeat=n)]
    attempts = tuple(attempt for history in histories for attempt in generated.execute(history))
    commit_ids = tuple(generated.execute([target])[0].requested for target in targets)
    refs = (None, *commit_ids)
    matrix = tuple(Attempt(*fields) for fields in product(refs, commit_ids, (None, "invalid_state", "not_found"), refs))
    cases = attempts + matrix
    # Bound each generated Quint input, retaining the direct evaluator's original timeout.
    direct = [result for batch in batched(cases, 32) for result in evaluate(quint, batch, source)]
    python = [generated.verdict(observation(attempt)) for attempt in cases]
    for attempt, expected, actual in zip(cases, direct, python, strict=True):
        if expected != actual:
            raise AssertionError(f"Quint={expected}, Python={actual} on {attempt!r}")
    actual_counts = Counter(python[:len(attempts)])
    matrix_counts = Counter(python[len(attempts):])
    if changed_profile:
        # This control changes the accepted status and the generator's alphabet/bound.
        assert targets == ("x", "z") and generated.MAX_STEPS == 3
        assert actual_counts == {"unexercised": 14, "violation": 20}
        assert matrix_counts == {"unexercised": 18, "pass": 4, "violation": 32}
    else:
        assert len(histories) == 121 and actual_counts == {"unexercised": 120, "pass": 306}
        assert len(matrix) == 144 and matrix_counts == {"unexercised": 36, "pass": 9, "violation": 99}
    print(f"agreement: {len(histories)} real histories, {len(attempts)} actual attempts {dict(actual_counts)}, "
          f"{len(matrix)} synthetic observations {dict(matrix_counts)}")


def check_offline() -> None:
    for tool in ("quint", "node", "npm"):
        if which(tool) is not None:
            raise RuntimeError(f"{tool} is on PATH; run from the offline staging directory with an empty tool PATH")
    try:
        generated.check([generated.TARGETS[0]], ())
    except ValueError as error:
        assert "one DML observation per requested action" in str(error), error
    else:
        raise AssertionError("the generated checker accepted missing evidence")

    histories, counts = generated.run_property(sample_seed=4120, max_examples=32)
    assert histories > 0 and counts["pass"] > 0 and counts["unexercised"] > 0
    print(f"offline: {histories} generated histories, {dict(counts)}", flush=True)

    first_failure = None

    def corrupt(requests: list[str], actual: tuple) -> tuple:
        nonlocal first_failure
        changed = tuple(
            replace(attempt, after=attempt.requested)
            if attempt.before is not None and attempt.before != attempt.requested else attempt
            for attempt in actual
        )
        if first_failure is None and changed != actual:
            first_failure = tuple(requests)
        return changed

    try:
        generated.run_property(sample_seed=4120, max_examples=32, corrupt=corrupt)
    except generated.RuleViolation as error:
        assert first_failure is not None and len(first_failure) > 2, first_failure
        assert len(error.requests) == 2 and error.requests[0] != error.requests[1], error.requests
        print(f"offline shrink: {first_failure} -> {error.requests}\n  {error}", flush=True)
    else:
        raise AssertionError("the generated checker did not detect the fabricated overwrite")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("offline")
    differential = modes.add_parser("differential")
    differential.add_argument("--quint", required=True, type=Path)
    differential.add_argument("--source", type=Path)
    differential.add_argument("--changed-profile", action="store_true")
    args = parser.parse_args()
    if args.mode == "offline":
        check_offline()
    else:
        compare_with_quint(args.quint.absolute(), args.source, args.changed_profile)


if __name__ == "__main__":
    main()
