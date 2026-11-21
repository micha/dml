"""Observe explicit endings inside real write contexts, without predicting verdicts."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import daggerml as dml

from context_binding import ContextBodyError
from ref_binding import BINDINGS, REF, Request
from transaction_binding import (
    MARKER, Batch, marker_present, read_ref, validate_observation as validate_batch, validate_sum,
)


FINISHES = ("commit_normal", "commit_exception", "abort_normal", "abort_exception")


@dataclass(frozen=True)
class ExplicitContextBatch:
    initial: str | None
    requests: tuple[Request, ...]
    finish: str
    requested_ids: tuple[str, ...]
    evidence: dict


def observe_operation(call: Callable[[], object]) -> tuple:
    """Record supported native statuses; unrelated errors retain their identity."""
    try:
        call()
    except (dml.InvalidStateError, dml.NotFoundError) as error:
        return ("Failed", error.code)
    return ("Succeeded", ())


def exercise_explicit_context(
    targets: Sequence[str], initial: str | None, requests: Sequence[Request], finish: str,
) -> ExplicitContextBatch:
    if finish not in FINISHES:
        raise ValueError(f"Unsupported explicit context ending: {finish!r}")
    if initial is not None and initial not in targets:
        raise ValueError(f"Unknown initial target: {initial!r}")
    if any(operation not in BINDINGS or label not in targets for operation, label in requests):
        raise ValueError("Unknown operation or target in explicit context requests")
    ending, completion = finish.split("_")
    with TemporaryDirectory(prefix="quint-explicit-context-") as tmp, dml.Repository(
        Path(tmp) / "repo", create=True
    ) as repo:
        with repo.write() as tx:
            commits = {}
            for index, label in enumerate(targets):
                datum = tx.put_datum(index)
                node = tx.put_literal(datum)
                dag = tx.put_dag(root=node)
                commits[label] = tx.put_commit(tx.put_tree({"value": dag}))
            if initial is not None:
                tx.create_ref(REF, commits[initial])
        with repo.write() as tx:
            marker = tx.put_datum(MARKER)
            tx.abort()
        with repo.read() as reader:
            before = read_ref(reader)
            marker_before = marker_present(reader, marker)
        steps = []
        poisoned = False
        body_error = ContextBodyError("explicit context body sentinel")
        raised_body_error = False
        body_completed = False
        exception = "none"
        outcome = ("Succeeded", ())
        tx = repo.write()
        phase = "body"
        exit_calls = 0
        commit, abort = tx.commit, tx.abort

        def observed_commit():
            nonlocal exit_calls
            if phase == "exit":
                exit_calls += 1
            return commit()

        def observed_abort():
            nonlocal exit_calls
            if phase == "exit":
                exit_calls += 1
            return abort()

        # These instance-local transparent wrappers count public completion calls;
        # reader completion, body probes and fallback cleanup are not exit calls.
        tx.commit, tx.abort = observed_commit, observed_abort
        try:
            try:
                with tx:
                    actual_marker = tx.put_datum(MARKER)
                    if actual_marker != marker:
                        raise RuntimeError("Native marker ID changed between identical insertions")
                    marker_staged = marker_present(tx, marker)
                    for operation, label in requests:
                        step_before = read_ref(tx, allow_unreadable=poisoned)
                        step_outcome = observe_operation(lambda: BINDINGS[operation](tx, REF, commits[label]))
                        step_after = read_ref(tx, allow_unreadable=poisoned or step_outcome[0] == "Failed")
                        steps.append({"operation": operation, "requested": commits[label].bytes.hex(),
                                      "before": step_before, "after": step_after,
                                      "outcome": step_outcome, "poisoned": poisoned})
                        poisoned = poisoned or step_outcome[0] == "Failed"
                    staged = read_ref(tx, allow_unreadable=poisoned)
                    explicit = observe_operation(getattr(tx, ending))
                    # Observe consumption/publication before __exit__ or any probe
                    # can repair a non-consuming explicit ending.
                    with repo.read() as reader:
                        ended_ref = read_ref(reader)
                        ended_marker = marker_present(reader, marker)
                    end_read = observe_operation(lambda: tx.get_ref(REF))
                    end_write = observe_operation(lambda: tx.put_datum(MARKER))
                    end_commit = observe_operation(tx.commit)
                    end_abort = observe_operation(tx.abort)
                    body_completed = True
                    phase = "exit"
                    if completion == "exception":
                        raised_body_error = True
                        raise body_error
            except ContextBodyError as error:
                if not raised_body_error:
                    raise
                exception = "original" if error is body_error else "replaced"
                outcome = ("Failed", "body_exception" if error is body_error else "replaced_exception")
            except dml.InvalidStateError as error:
                if not body_completed:
                    raise
                # An incorrect exit may try to complete an ended handle, including
                # masking the original body exception. That is observable failure.
                outcome = ("Failed", error.code)
            else:
                if raised_body_error:
                    exception = "suppressed"
            with repo.read() as reader:
                after = read_ref(reader)
                marker_after = marker_present(reader, marker)
        finally:
            phase = "cleanup"
            tx.abort()
        evidence = {
            "batch": {"before": before, "staged": staged, "after": after, "steps": tuple(steps),
                      "finish": finish, "outcome": outcome, "markerBefore": marker_before,
                      "markerStaged": marker_staged, "markerAfter": marker_after},
            "explicit": explicit, "exception": exception,
            "endedRef": ended_ref, "endedMarker": ended_marker,
            "endRead": end_read, "endWrite": end_write, "endCommit": end_commit, "endAbort": end_abort,
            "exitCalls": exit_calls,
        }
        return ExplicitContextBatch(initial, tuple(requests), finish,
                                    tuple(commits[label].bytes.hex() for _, label in requests), evidence)


def validate_observation(
    initial: str | None, requests: Sequence[Request], finish: str, batch: ExplicitContextBatch,
) -> dict:
    """Reject incomplete, malformed or misassociated evidence before rule matching."""
    if finish not in FINISHES:
        raise ValueError(f"Unsupported explicit context ending: {finish!r}")
    if (initial, tuple(requests), finish) != (batch.initial, batch.requests, batch.finish):
        raise ValueError("Explicit context evidence belongs to another exercise")
    evidence = batch.evidence
    fields = {"batch", "explicit", "exception", "endedRef", "endedMarker", "endRead", "endWrite",
              "endCommit", "endAbort", "exitCalls"}
    if type(evidence) is not dict or evidence.keys() != fields:
        raise ValueError("Expected complete explicit context evidence")
    if (type(evidence["exception"]) is not str
            or evidence["exception"] not in ("none", "original", "replaced", "suppressed")):
        raise ValueError("Invalid explicit context exception evidence")
    for field in ("explicit", "endRead", "endWrite", "endCommit", "endAbort"):
        validate_sum(evidence[field], {"Succeeded": tuple, "Failed": str})
    validate_sum(evidence["endedRef"], {"Absent": tuple, "Target": str, "Unreadable": str})
    if type(evidence["endedMarker"]) is not bool:
        raise ValueError("Ended marker evidence must be boolean")
    if type(evidence["exitCalls"]) is not int or evidence["exitCalls"] < 0:
        raise ValueError("Exit call count must be a nonnegative integer")
    validate_batch(initial, requests, finish, Batch(initial, tuple(requests), finish,
                                                  batch.requested_ids, evidence["batch"]))
    return evidence
