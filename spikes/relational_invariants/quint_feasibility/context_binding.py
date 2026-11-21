"""Observe actual Python write-context completion, without predicting verdicts."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import daggerml as dml

from ref_binding import BINDINGS, REF, Request
from transaction_binding import (
    MARKER, Batch, marker_present, read_ref, validate_observation as validate_batch,
)


class ContextBodyError(Exception):
    """A fresh exception instance raised deliberately inside the tested context."""


@dataclass(frozen=True)
class ContextBatch:
    initial: str | None
    requests: tuple[Request, ...]
    finish: str
    requested_ids: tuple[str, ...]
    evidence: dict


def exercise_context(
    targets: Sequence[str], initial: str | None, requests: Sequence[Request], finish: str,
) -> ContextBatch:
    if finish not in ("normal", "exception"):
        raise ValueError(f"Unsupported context ending: {finish!r}")
    if initial is not None and initial not in targets:
        raise ValueError(f"Unknown initial target: {initial!r}")
    if any(operation not in BINDINGS or label not in targets for operation, label in requests):
        raise ValueError("Unknown operation or target in context requests")
    with TemporaryDirectory(prefix="quint-context-") as tmp, dml.Repository(
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
        body_error = ContextBodyError("context body sentinel")
        raised_body_error = False
        body_completed = False
        exception = "none"
        outcome = ("Succeeded", ())
        tx = repo.write()
        try:
            try:
                # Exercise Python's real context protocol, not a direct __exit__ call.
                with tx:
                    actual_marker = tx.put_datum(MARKER)
                    if actual_marker != marker:
                        raise RuntimeError("Native marker ID changed between identical insertions")
                    marker_staged = marker_present(tx, marker)
                    for operation, label in requests:
                        step_before = read_ref(tx, allow_unreadable=poisoned)
                        step_outcome = ("Succeeded", ())
                        try:
                            BINDINGS[operation](tx, REF, commits[label])
                        except (dml.InvalidStateError, dml.NotFoundError) as error:
                            step_outcome = ("Failed", error.code)
                        step_after = read_ref(tx, allow_unreadable=poisoned or step_outcome[0] == "Failed")
                        steps.append({"operation": operation, "requested": commits[label].bytes.hex(),
                                      "before": step_before, "after": step_after,
                                      "outcome": step_outcome, "poisoned": poisoned})
                        poisoned = poisoned or step_outcome[0] == "Failed"
                    staged = read_ref(tx, allow_unreadable=poisoned)
                    body_completed = True
                    if finish == "exception":
                        raised_body_error = True
                        raise body_error
            except ContextBodyError as error:
                if not raised_body_error:
                    raise
                exception = "original" if error is body_error else "replaced"
                outcome = ("Failed", "body_exception" if error is body_error else "replaced_exception")
            except dml.InvalidStateError as error:
                if finish != "normal" or not body_completed:
                    raise
                outcome = ("Failed", error.code)
            else:
                if raised_body_error:
                    exception = "suppressed"
            # A still-active context must fail this fresh read before cleanup can
            # supply rollback. Unexpected body/exit errors are never legitimate rejections.
            with repo.read() as reader:
                after = read_ref(reader)
                marker_after = marker_present(reader, marker)
        finally:
            tx.abort()
        evidence = {
            "batch": {"before": before, "staged": staged, "after": after, "steps": tuple(steps),
                      "finish": finish, "outcome": outcome, "markerBefore": marker_before,
                      "markerStaged": marker_staged, "markerAfter": marker_after},
            "exception": exception,
        }
        return ContextBatch(initial, tuple(requests), finish,
                            tuple(commits[label].bytes.hex() for _, label in requests), evidence)


def validate_observation(
    initial: str | None, requests: Sequence[Request], finish: str, batch: ContextBatch,
) -> dict:
    """Keep complete evidence and input association mandatory before matching rules."""
    if (initial, tuple(requests), finish) != (batch.initial, batch.requests, batch.finish):
        raise ValueError("Context evidence belongs to another exercise")
    evidence = batch.evidence
    if type(evidence) is not dict or evidence.keys() != {"batch", "exception"}:
        raise ValueError("Expected complete context evidence")
    if (type(evidence["exception"]) is not str
            or evidence["exception"] not in ("none", "original", "replaced", "suppressed")):
        raise ValueError("Invalid context exception evidence")
    validate_batch(initial, requests, finish, Batch(initial, tuple(requests), finish,
                                                  batch.requested_ids, evidence["batch"]))
    return evidence
