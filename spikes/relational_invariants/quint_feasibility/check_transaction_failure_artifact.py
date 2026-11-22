"""Check live shrinking, one final native evidence write, and offline failure replay."""

import argparse
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
from shutil import which
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import daggerml as dml
import generated_transactions as generated

from ref_binding import Request
from transaction_binding import Batch
import transaction_failure_artifact as artifact
from transaction_graph import save_batch


SAMPLE_SEED = 4120
MAX_EXAMPLES = 120
EXPECTED_VIOLATION = "commitPoisoned"
EXPECTED_VERDICTS = {"commitClean": "unexercised", "commitPoisoned": "violation",
                     "continuity": "pass", "explicitAbort": "unexercised",
                     "freshMarker": "pass", "stepEffects": "pass"}


def marker_leak(batch: Batch) -> Batch:
    evidence = batch.evidence
    if batch.finish != "commit" or evidence["outcome"] != ("Failed", "invalid_state"):
        return batch
    # Keep an actual successful ref movement before the subsequent poison.
    if not any(step["outcome"] == ("Succeeded", ()) and step["after"] != evidence["before"]
               for step in evidence["steps"]):
        return batch
    assert evidence["markerAfter"] is False and evidence["markerStaged"] is True, evidence
    return replace(batch, evidence={**evidence, "markerAfter": True})


@dataclass
class Attempt:
    live: Batch
    live_checked: bool = False
    candidate: Batch | None = None
    candidate_checked: bool = False


class PropertyProbe:
    """Observe the real runner's boundaries without replacing Hypothesis or DML."""

    def __init__(self, path: Path, *, inject: bool) -> None:
        self.path = path
        self.inject = inject
        self.execute_live = generated.execute
        self.check_live = generated.check
        self.seed = artifact.seed
        self.attempts: list[Attempt] = []
        self.counts = Counter()
        self.violations: list[tuple[Batch, generated.RuleViolation]] = []
        self.writes: list[tuple[Batch, dml.ObjectId]] = []
        self.reported_error: BaseException | None = None
        self.property_running = False
        self.property_finished = False

    def wrap_seed(self, sample_seed):
        # The outermost decorator wraps the final callable after @settings/@given.
        # Catch what Hypothesis actually reports, not the last checker invocation.
        def decorate(test):
            run_test = self.seed(sample_seed)(test)

            def run():
                assert not self.property_running and not self.property_finished
                self.property_running = True
                try:
                    run_test()
                except BaseException as error:
                    self.reported_error = error
                    raise
                finally:
                    self.property_running = False
                    self.property_finished = True
                    assert not self.path.exists(), self.path

            return run

        return decorate

    def execute(self, initial, requests, finish) -> Batch:
        assert self.property_running, "Transaction was executed outside the property"
        assert not self.path.exists(), self.path
        batch = self.execute_live(initial, requests, finish)
        self.attempts.append(Attempt(batch))
        return batch

    def check(self, initial, requests, finish, batch):
        assert self.property_running and not self.path.exists(), self.path
        attempt = self.attempts[-1]
        if not attempt.live_checked:
            assert batch is attempt.live
            counts = self.check_live(initial, requests, finish, batch)
            self.counts.update(counts)
            attempt.live_checked = True
            return counts
        assert self.inject and not attempt.candidate_checked and batch is attempt.candidate
        attempt.candidate_checked = True
        try:
            return self.check_live(initial, requests, finish, batch)
        except generated.RuleViolation as error:
            self.violations.append((batch, error))
            raise

    def corrupt(self, batch: Batch) -> Batch:
        assert self.property_running and not self.path.exists(), self.path
        attempt = self.attempts[-1]
        assert batch is attempt.live and attempt.live_checked and attempt.candidate is None
        attempt.candidate = marker_leak(batch)
        return attempt.candidate

    def save(self, path: Path, batch: Batch) -> dml.ObjectId:
        assert self.inject and self.property_finished and not self.property_running, "Unexpected evidence save"
        assert path == self.path and not path.exists() and not self.writes, path
        assert self.reported_error is not None
        assert any(batch is checked and self.reported_error.__cause__ is error
                   for checked, error in self.violations), "Did not save the reported, checked Batch object"
        root = save_batch(path, batch)
        self.writes.append((batch, root))
        return root

    def run(self) -> tuple[int, Counter]:
        with (patch.object(artifact, "seed", self.wrap_seed), patch.object(artifact, "save_batch", self.save),
              patch.object(generated, "execute", self.execute), patch.object(generated, "check", self.check)):
            return artifact.run_property(self.path, sample_seed=SAMPLE_SEED, max_examples=MAX_EXAMPLES,
                                         corrupt=self.corrupt if self.inject else None)

    def check_attempts(self) -> None:
        assert self.property_finished and self.attempts
        assert all(attempt.live_checked and attempt.candidate_checked == self.inject for attempt in self.attempts)


def passing_property(path: Path) -> None:
    probe = PropertyProbe(path, inject=False)
    histories, counts = probe.run()
    probe.check_attempts()
    assert histories == len(probe.attempts) == MAX_EXAMPLES, histories
    assert counts == probe.counts and all(counts[rule, "pass"] > 0 for rule in generated.RULE_IDS), counts
    assert not probe.writes and not path.exists(), path
    print(f"Passing property: {histories} live batches checked, six matching rules, no evidence writes.")


def failing_property(path: Path) -> tuple[Batch, dml.ObjectId]:
    probe = PropertyProbe(path, inject=True)
    try:
        probe.run()
    except artifact.SavedFailure as saved:
        probe.check_attempts()
        assert saved.rule == EXPECTED_VIOLATION and saved.__cause__ is probe.reported_error, saved
        assert len(probe.writes) == 1 and probe.writes[0][0] is saved.batch and probe.writes[0][1] == saved.root
        first, _ = probe.violations[0]
        final = saved.batch
        assert len(first.requests) == 3 and len(final.requests) == 2, (first, final)
        assert len(probe.violations) > 1
        live = next(attempt.live for attempt in probe.attempts if attempt.candidate is final)
        assert live.evidence["markerAfter"] is False
        assert final == replace(live, evidence={**live.evidence, "markerAfter": True})
        assert generated.verdicts(final.evidence) == EXPECTED_VERDICTS
        print(f"Marker control: {len(probe.attempts)} live checks, {len(probe.violations)} violating candidates, "
              f"{first.requests} shrank to {final.requests}.")
        print(f"Saved exactly the reported batch, once after shrinking: {saved.root}")
        return final, saved.root
    raise AssertionError("Hypothesis did not report the marker publication violation")


def expect_invalid(message: str, check: Callable[[], object]) -> None:
    try:
        check()
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Expected rejection: {message}")


def reopen(path: Path, root: dml.ObjectId, initial: str | None, requests: tuple[Request, ...], finish: str) -> dict:
    # Fail if replay attempts live execution or opens a native write transaction.
    with (patch.object(generated, "execute", side_effect=AssertionError("Replay executed the transaction")),
          patch.object(dml.Repository, "write", side_effect=AssertionError("Replay opened a writer"))):
        batch, error = artifact.replay_failure(path, root, initial=initial, requests=requests, finish=finish)
        assert isinstance(error, generated.RuleViolation)
        assert (error.initial, error.requests, error.finish) == (initial, requests, finish), error
        wrong_pin = str(root)[:-1] + ("1" if str(root).endswith("0") else "0")
        expect_invalid("does not match the expected root", lambda: artifact.replay_failure(
            path, dml.ObjectId.from_hex(wrong_pin), initial=initial, requests=requests, finish=finish))
        wrong_finish = "abort" if finish == "commit" else "commit"
        expect_invalid("belongs to another exercise", lambda: artifact.replay_failure(
            path, root, initial=initial, requests=requests, finish=wrong_finish))
    return {"batch": asdict(batch), "rule": error.rule, "verdicts": generated.verdicts(batch.evidence)}


def fresh_process(path: Path, root: dml.ObjectId, batch: Batch, empty_bin: Path) -> None:
    # Only the independently supplied pin and recipe cross into the child. The
    # returned JSON is a comparison receipt, not the persisted evidence format.
    env = {"PATH": str(empty_bin), "PYTHONHASHSEED": "799"}
    if "PYTHONPATH" in os.environ:
        env["PYTHONPATH"] = os.environ["PYTHONPATH"]
    recipe = json.dumps((batch.initial, batch.requests, batch.finish))
    child = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--reopen", str(path), str(root), recipe],
        capture_output=True, text=True, env=env, timeout=30,
    )
    if child.returncode != 0:
        raise RuntimeError(f"Fresh replay failed ({child.returncode}):\n{child.stdout}{child.stderr}")
    expected = {"batch": asdict(batch), "rule": EXPECTED_VIOLATION, "verdicts": EXPECTED_VERDICTS}
    assert json.loads(child.stdout) == json.loads(json.dumps(expected)), child.stdout
    print("Fresh offline replay: exact batch and commitPoisoned violation; no live execution or writer; "
          "wrong pin and recipe rejected.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--out", type=Path, help="Keep the failure graph at this new repository path")
    mode.add_argument("--reopen", nargs=3, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run without Python optimizations to keep the evidence checks enabled")
    if any(which(tool) is not None for tool in ("quint", "node", "npm")):
        parser.error("Run from the offline stage with no Quint, Node or npm on PATH")
    if args.reopen is not None:
        path, pin, recipe = args.reopen
        initial, requests, finish = json.loads(recipe)
        print(json.dumps(reopen(Path(path), dml.ObjectId.from_hex(pin), initial,
                                tuple(map(tuple, requests)), finish)))
        return
    with TemporaryDirectory(prefix="quint-transaction-failure-") as tmp:
        directory = Path(tmp)
        path = args.out.absolute() if args.out is not None else directory / "evidence"
        if path.exists() or path.is_symlink() or not path.parent.is_dir():
            parser.error("Expected a new evidence repository path with an existing parent directory")
        passing_property(path)
        batch, root = failing_property(path)
        empty_bin = directory / "empty-bin"
        empty_bin.mkdir()
        fresh_process(path, root, batch, empty_bin)


if __name__ == "__main__":
    main()
