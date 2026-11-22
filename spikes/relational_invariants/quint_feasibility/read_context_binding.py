"""Observe a Python read context and the repository before and after it."""

from collections.abc import Callable, Sequence
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import daggerml as dml


REF = "read-context-anchor"
PROBE_REF = "read-context-probe"
OPERATIONS = {"commit", "create_ref", "missing_read"}
EXIT_MODES = {"normal", "exception"}


class BodyException(Exception):
    pass


def observe(call: Callable[[], object]) -> str:
    try:
        result = call()
    except dml.InvalidStateError as error:
        return error.code
    except dml.NotFoundError as error:
        if error.detail != "ref was not found":
            raise
        return error.code
    return str(result) if isinstance(result, dml.ObjectId) else "ok"


def exercise(requests: Sequence[str], exit_mode: str) -> dict:
    if not requests or any(request not in OPERATIONS for request in requests) or exit_mode not in EXIT_MODES:
        raise ValueError("Expected supported read-context actions and exit mode")
    with TemporaryDirectory(prefix="quint-read-context-") as tmp, dml.Repository(
        Path(tmp) / "repo", create=True
    ) as repo:
        with repo.write() as writer:
            node = writer.put_literal(writer.put_datum(42))
            tree = writer.put_tree({"value": writer.put_dag(root=node)})
            target = writer.put_commit(tree)
            writer.create_ref(REF, target)
        with repo.read() as reader:
            before = str(reader.get_ref(REF))

        sentinel = BodyException("read context body")
        exit_outcome = "ok"
        steps = []
        tx = repo.read()
        calls = {"commit": tx.commit, "create_ref": lambda: tx.create_ref(PROBE_REF, target),
                 "missing_read": lambda: tx.get_ref(PROBE_REF)}
        try:
            with tx:
                for request in requests:
                    result = observe(calls[request])
                    read_after = observe(lambda: tx.get_ref(REF))
                    # A lookup's successful return is represented by its status here, not its data.
                    steps.append({"operation": request, "outcome": "ok" if is_target(result) else result,
                                  "readAfter": read_after})
                if exit_mode == "exception":
                    raise sentinel
        except BodyException as error:
            if error is not sentinel:
                raise
            exit_outcome = "same_exception"

        ended_read = observe(lambda: tx.get_ref(REF))
        # Do not call tx.abort() first; it could mask missing cleanup on context exit.
        try:
            reader = repo.read()
        except dml.InvalidStateError as error:
            if error.detail != "repository already has an active transaction":
                raise
            after = probe_ref = error.code
        else:
            with reader:
                after = observe(lambda: reader.get_ref(REF))
                probe = observe(lambda: reader.get_ref(PROBE_REF))
                probe_ref = "ok" if is_target(probe) else probe
        return {"before": before, "steps": tuple(steps), "exitMode": exit_mode, "exitOutcome": exit_outcome,
                "endedRead": ended_read, "after": after, "probeRef": probe_ref}


def is_target(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{32}", value) is not None


def is_reading(value: object) -> bool:
    return is_target(value) or (type(value) is str and value in ("not_found", "invalid_state"))


def validate_observation(requests: Sequence[str], exit_mode: str, attempt: dict) -> None:
    fields = {"before", "steps", "exitMode", "exitOutcome", "endedRead", "after", "probeRef"}
    if type(attempt) is not dict or attempt.keys() != fields or not is_target(attempt["before"]):
        raise ValueError("Expected complete read-context evidence with a known starting ref")
    if (exit_mode not in EXIT_MODES or attempt["exitMode"] != exit_mode or type(attempt["steps"]) is not tuple
            or not requests or len(attempt["steps"]) != len(requests)):
        raise ValueError("Read-context evidence does not match its recipe")
    if (not all(is_reading(attempt[key]) for key in ("endedRead", "after"))
            or attempt["exitOutcome"] not in ("ok", "same_exception")
            or attempt["probeRef"] not in ("ok", "not_found", "invalid_state")):
        raise ValueError("Invalid read-context completion evidence")
    for request, step in zip(requests, attempt["steps"], strict=True):
        if (type(step) is not dict or step.keys() != {"operation", "outcome", "readAfter"}
                or request not in OPERATIONS or step["operation"] != request
                or step["outcome"] not in ("ok", "not_found", "invalid_state") or not is_reading(step["readAfter"])):
            raise ValueError("Incomplete or mismatched read-context step evidence")
