"""Execute transaction batches and capture observations, without predicting verdicts."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import daggerml as dml

from ref_binding import BINDINGS, REF, Request, ref_value


MARKER = "quint-transaction-marker"


@dataclass(frozen=True)
class Batch:
    initial: str | None
    requests: tuple[Request, ...]
    finish: str
    requested_ids: tuple[str, ...]
    evidence: dict


def read_ref(tx: dml.Transaction, *, allow_unreadable: bool = False) -> tuple:
    try:
        return ref_value(tx.get_ref(REF))
    except dml.NotFoundError as error:
        if error.detail != "ref was not found":
            raise
        return ("Absent", ())
    except dml.InvalidStateError as error:
        if not allow_unreadable or error.detail != "transaction ended or failed":
            raise
        return ("Unreadable", error.code)


def marker_present(tx: dml.Transaction, marker: dml.ObjectId) -> bool:
    try:
        tx.get_datum(marker)
    except dml.NotFoundError:
        # This marker is a scalar string with no direct references to go missing.
        return False
    return True


def exercise_transaction(
    targets: Sequence[str], initial: str | None, requests: Sequence[Request], finish: str,
) -> Batch:
    if finish not in ("commit", "abort"):
        raise ValueError(f"Unsupported transaction ending: {finish!r}")
    if initial is not None and initial not in targets:
        raise ValueError(f"Unknown initial target: {initial!r}")
    if any(operation not in BINDINGS or label not in targets for operation, label in requests):
        raise ValueError("Unknown operation or target in transaction requests")
    with TemporaryDirectory(prefix="quint-txn-") as tmp, dml.Repository(
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
        # Obtain the native marker ID without publishing it. The separate read below
        # establishes genuine absence, rather than assuming deduplication did not occur.
        with repo.write() as tx:
            marker = tx.put_datum(MARKER)
            tx.abort()
        with repo.read() as tx:
            before = read_ref(tx)
            marker_before = marker_present(tx, marker)
        steps = []
        poisoned = False  # Bookkeeping from observed errors, not a shadow ref state.
        tx = repo.write()
        try:
            actual_marker = tx.put_datum(MARKER)
            if actual_marker != marker:
                raise RuntimeError("Native marker ID changed between identical insertions")
            marker_staged = marker_present(tx, marker)
            for operation, label in requests:
                step_before = read_ref(tx, allow_unreadable=poisoned)
                outcome = ("Succeeded", ())
                try:
                    BINDINGS[operation](tx, REF, commits[label])
                except (dml.InvalidStateError, dml.NotFoundError) as error:
                    outcome = ("Failed", error.code)
                step_after = read_ref(tx, allow_unreadable=poisoned or outcome[0] == "Failed")
                steps.append({"operation": operation, "requested": commits[label].bytes.hex(),
                              "before": step_before, "after": step_after,
                              "outcome": outcome, "poisoned": poisoned})
                poisoned = poisoned or outcome[0] == "Failed"
            staged = read_ref(tx, allow_unreadable=poisoned)
            outcome = ("Succeeded", ())
            try:
                # Do not abort automatically on a caught mutation error: attempting
                # commit on the same poisoned transaction is the behavior under test.
                getattr(tx, finish)()
            except dml.InvalidStateError as error:
                outcome = ("Failed", error.code)
            # Observe before fallback cleanup: an ending that leaves the write
            # transaction active must fail here, not borrow rollback from finally.
            with repo.read() as reader:
                after = read_ref(reader)
                marker_after = marker_present(reader, marker)
        finally:
            tx.abort()
        evidence = {"before": before, "staged": staged, "after": after, "steps": tuple(steps),
                    "finish": finish, "outcome": outcome, "markerBefore": marker_before,
                    "markerStaged": marker_staged, "markerAfter": marker_after}
        requested_ids = tuple(commits[label].bytes.hex() for _, label in requests)
        return Batch(initial, tuple(requests), finish, requested_ids, evidence)


def validate_observation(
    initial: str | None, requests: Sequence[Request], finish: str, batch: Batch,
) -> dict:
    """Reject incomplete/misassociated evidence before evaluating any predicates."""
    if (initial, tuple(requests), finish) != (batch.initial, batch.requests, batch.finish):
        raise ValueError("Transaction evidence belongs to another exercise")
    attempt = batch.evidence
    fields = {"before", "staged", "after", "steps", "finish", "outcome", "markerBefore",
              "markerStaged", "markerAfter"}
    step_fields = {"operation", "requested", "before", "after", "outcome", "poisoned"}
    if type(attempt) is not dict or attempt.keys() != fields:
        raise ValueError("Expected complete transaction evidence")
    if (attempt["finish"] != finish or type(attempt["steps"]) is not tuple
            or len(attempt["steps"]) != len(requests) or len(batch.requested_ids) != len(requests)):
        raise ValueError("Transaction ending or action count does not match the request")
    for field in ("before", "staged", "after"):
        validate_sum(attempt[field], {"Absent": tuple, "Target": str, "Unreadable": str})
    validate_sum(attempt["outcome"], {"Succeeded": tuple, "Failed": str})
    if any(type(attempt[field]) is not bool for field in ("markerBefore", "markerStaged", "markerAfter")):
        raise ValueError("Marker evidence must be boolean")
    for (operation, _), requested, step in zip(requests, batch.requested_ids, attempt["steps"], strict=True):
        if (type(step) is not dict or step.keys() != step_fields or step["operation"] != operation
                or step["requested"] != requested):
            raise ValueError("Incomplete or mismatched transaction step evidence")
        for field in ("before", "after"):
            validate_sum(step[field], {"Absent": tuple, "Target": str, "Unreadable": str})
        validate_sum(step["outcome"], {"Succeeded": tuple, "Failed": str})
        if type(step["poisoned"]) is not bool:
            raise ValueError("Poisoning evidence must be boolean")
    return attempt


def validate_sum(value, variants: dict[str, type]) -> None:
    if type(value) is not tuple or len(value) != 2 or type(value[0]) is not str:
        raise ValueError("Invalid tagged-sum evidence")
    tag, payload = value
    expected = variants.get(tag)
    if expected is None or type(payload) is not expected or (expected is tuple and payload != ()):
        raise ValueError("Invalid tagged-sum evidence")
