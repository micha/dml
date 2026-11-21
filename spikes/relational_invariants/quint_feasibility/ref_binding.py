"""Native ref adapter shared by the direct and generated checks."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import daggerml as dml


REF = "spike"
BINDINGS = {"create_ref": dml.Transaction.create_ref, "update_ref": dml.Transaction.update_ref}
Request = tuple[str, str]


@dataclass(frozen=True)
class Attempt:
    before: dml.ObjectId | None
    requested: dml.ObjectId
    error_code: str | None  # None means the operation returned normally and committed.
    after: dml.ObjectId | None
    operation: str = "create_ref"


def read_ref(repo: dml.Repository) -> dml.ObjectId | None:
    with repo.read() as tx:
        try:
            return tx.get_ref(REF)
        except dml.NotFoundError as error:
            # get_ref also reports not_found for a broken target. Don't call that absence.
            if error.detail != "ref was not found":
                raise
            return None


def attempt_ref(repo: dml.Repository, operation: str, target: dml.ObjectId) -> Attempt:
    mutate = BINDINGS[operation]
    before = read_ref(repo)
    error_code = None
    with repo.write() as tx:
        try:
            mutate(tx, REF, target)
        except (dml.InvalidStateError, dml.NotFoundError) as error:
            # Capture the two modeled statuses; unrelated errors are not test verdicts.
            error_code = error.code
            tx.abort()
    return Attempt(before, target, error_code, read_ref(repo), operation)


def exercise_refs(targets: Sequence[str], requests: Sequence[Request]) -> tuple[Attempt, ...]:
    with TemporaryDirectory(prefix="quint-dml-") as tmp, dml.Repository(
        Path(tmp) / "repo", create=True
    ) as repo:
        with repo.write() as tx:
            commits = {}
            for index, label in enumerate(targets):
                datum = tx.put_datum(index)
                node = tx.put_literal(datum)
                dag = tx.put_dag(root=node)
                commits[label] = tx.put_commit(tx.put_tree({"value": dag}))
        return tuple(attempt_ref(repo, operation, commits[label]) for operation, label in requests)


def exercise_create_ref(targets: Sequence[str], requests: Sequence[str]) -> tuple[Attempt, ...]:
    return exercise_refs(targets, [("create_ref", label) for label in requests])


def ref_value(ref: dml.ObjectId | None) -> tuple[str, str | tuple[()]]:
    return ("Absent", ()) if ref is None else ("Target", ref.bytes.hex())


def observation(attempt: Attempt, *, mixed: bool = False) -> dict[str, str | tuple[str, str | tuple[()]]]:
    """Encode the Quint Attempt record, using tagged tuples for sum types."""
    success = "Succeeded" if mixed else "Created"
    evidence = {
        "before": ref_value(attempt.before),
        "requested": attempt.requested.bytes.hex(),
        "outcome": (success, ()) if attempt.error_code is None else ("Failed", attempt.error_code),
        "after": ref_value(attempt.after),
    }
    if mixed:
        evidence["operation"] = attempt.operation
    return evidence
