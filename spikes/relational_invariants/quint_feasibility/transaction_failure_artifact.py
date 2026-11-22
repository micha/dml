"""Save the exact transaction batch reported after Hypothesis finishes shrinking."""

from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

import daggerml as dml
from hypothesis import given, seed, settings
from hypothesis.strategies import SearchStrategy

import generated_transactions as generated
from ref_binding import Request
from transaction_binding import Batch
from transaction_graph import load_batch, save_batch


History = tuple[str | None, Sequence[Request], str]
VerdictCounts = Counter[tuple[str, str]]


class _ObservedFailure(AssertionError):
    def __init__(self, batch: Batch, error: generated.RuleViolation) -> None:
        self.batch = batch
        self.rule = error.rule
        super().__init__(str(error))


class SavedFailure(AssertionError):
    """A reported violation whose batch is now stored under a pinned root."""

    def __init__(self, path: Path, root: dml.ObjectId, failure: _ObservedFailure) -> None:
        self.batch = failure.batch
        self.rule = failure.rule
        self.root = root
        super().__init__(f"{self.rule}: saved transaction failure to {path} at {root}")


def _check_observed(trace: History, batch: Batch, *, control_baseline: bool = False) -> VerdictCounts:
    try:
        return generated.check(*trace, batch)
    except generated.RuleViolation as error:
        if control_baseline:
            raise RuntimeError(f"Real observations failed before control injection: {error}") from error
        raise _ObservedFailure(batch, error) from error


def run_property(
    path: Path, *, sample_seed: int, max_examples: int,
    corrupt: Callable[[Batch], Batch] | None = None,
    history_strategy: SearchStrategy[History] | None = None,
) -> tuple[int, VerdictCounts]:
    """Check freshly executed examples; save only a single reported invariant failure."""
    histories, counts = 0, Counter()

    @seed(sample_seed)
    @settings(max_examples=max_examples, database=None, deadline=None)
    @given(generated.HISTORIES if history_strategy is None else history_strategy)
    def check_case(trace: History) -> None:
        nonlocal histories
        batch = generated.execute(*trace)
        counts.update(_check_observed(trace, batch, control_baseline=corrupt is not None))
        if corrupt is not None:
            _check_observed(trace, corrupt(batch))
        histories += 1

    try:
        check_case()
    except _ObservedFailure as failure:
        # This is the reported failure, not a last-seen batch or a recipe to rerun.
        root = save_batch(path, failure.batch)
        raise SavedFailure(path, root, failure) from failure

    generated.require_witnesses(counts)
    return histories, counts


def replay_failure(
    path: Path, root: dml.ObjectId, *, initial: str | None, requests: Sequence[Request], finish: str,
) -> tuple[Batch, generated.RuleViolation]:
    """Recheck pinned observations with the current checker, without executing their recipe."""
    batch = load_batch(path, root, initial=initial, requests=requests, finish=finish)
    try:
        generated.check(initial, requests, finish, batch)
    except generated.RuleViolation as error:
        return batch, error
    raise ValueError("Pinned transaction evidence does not reproduce an invariant violation")
