"""Process integration; executable paths may point to consumers of an installed libdml."""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple


ADD_ONE = "example.add-one@1"
SUBTRACT_ONE = "example.subtract-one@1"
UNKNOWN = "example.unknown@1"
WRONG_PARENT = "result parent does not match the original request"


class Request(NamedTuple):
    commit: str
    input_commit: str
    input_datum: str
    input_value: str
    operation: str
    entry: str
    binding: str


class Result(NamedTuple):
    commit: str
    request: str
    input_commit: str
    input_datum: str
    output_datum: str
    implementation_datum: str
    input_value: str
    output_value: str
    implementation: str


def require(condition, evidence):
    if not condition:
        raise AssertionError(evidence)


def run(executable, *args, rejected=None):
    command = [executable, *map(str, args)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    expected_code = 0 if rejected is None else 1
    require(result.returncode == expected_code, (command, result))
    if rejected is not None:
        require(rejected in result.stderr, (command, result))
    return result.stdout.strip()


class Handoff:
    def __init__(self, path, example, fixture):
        self.path = path
        path.mkdir()
        self.example = example
        self.fixture = fixture
        self.source = path / "source"
        self.worker = path / "worker"
        self.request = path / "request.dml"
        self.result = path / "result.dml"
        self.input, self.ancestor = self.probe("seed", self.source, "original").splitlines()

    def call(self, *args, **kwargs):
        return run(self.example, *args, **kwargs)

    def probe(self, *args):
        return run(self.fixture, *args)

    def refs(self, repository, **expected):
        for key, value in expected.items():
            ref = key.replace("_", "-")
            actual = self.probe("ref", repository, ref)
            require(actual == value, (repository, ref, actual, value))

    def collect_orphan(self, repository):
        orphan = self.probe("orphan", repository)
        require(self.probe("datum", repository, orphan) == "present", (repository, orphan))
        removed = self.probe("collect", repository)
        require(removed == "1", (repository, removed))
        require(self.probe("datum", repository, orphan) == "missing", (repository, orphan))

    def read_request(self, repository, ref, snapshot, operation, entry, binding, value):
        actual = Request(*self.probe("request", repository, ref).split())
        require(actual.input_commit == snapshot and actual.commit != snapshot, (actual, snapshot))
        expected = (str(value), operation, entry, binding)
        require(actual[3:] == expected, (actual, expected))
        return actual

    def new_request(self, source, path, snapshot, operation=ADD_ONE,
                    entry="snapshot", binding="value", value=43):
        self.call("request", source, path, operation, entry, binding)
        return self.read_request(source, "request-pin", snapshot, operation, entry, binding, value)

    def observe(self, repository, ref, request, output, implementation=None):
        actual = Result(*self.probe("result", repository, ref).split())
        expected = (request.commit, request.input_commit, request.input_datum)
        require(actual[1:4] == expected, (actual, expected))
        expected = (request.input_value, str(output), implementation or request.operation)
        require(actual[6:] == expected, (actual, expected))
        return actual

    def same_result(self, repository, ref, expected):
        actual = Result(*self.probe("result", repository, ref).split())
        require(actual == expected, (actual, expected))

    def direct(self):
        # Exactly three workflow invocations, selecting a nonroot binding in a different tree entry.
        request = self.new_request(self.source, self.request, self.input,
                                   entry="alternate-snapshot", binding="alternate-value", value=343)
        self.call("work", self.worker, self.result, self.request)
        self.call("publish", self.source, self.result)
        result = self.observe(self.worker, "result-pin", request, 344)
        self.same_result(self.source, "main", result)
        self.refs(self.source, main=result.commit, request_pin="missing", returned="missing")
        self.refs(self.worker, main="missing", incoming=request.commit, result_pin=result.commit)

    def distinct_operations(self):
        replica = self.path / "replica"
        subtract_request = self.path / "subtract-request.dml"
        subtract_result = self.path / "subtract-result.dml"
        subtract_worker = self.path / "subtract-worker"
        tip, ancestor = self.probe("seed", replica, "original").splitlines()
        require((tip, ancestor) == (self.input, self.ancestor), (tip, ancestor))
        add = self.new_request(self.source, self.request, self.input)
        subtract = self.new_request(replica, subtract_request, self.input, SUBTRACT_ONE)
        require(add.commit != subtract.commit and add.input_datum == subtract.input_datum, (add, subtract))

        self.call("work", self.worker, self.result, self.request)
        self.observe(self.worker, "result-pin", add, 44)
        self.call("work", subtract_worker, subtract_result, subtract_request)
        result = self.observe(subtract_worker, "result-pin", subtract, 42)
        self.call("publish", replica, subtract_result)
        self.same_result(replica, "main", result)
        self.refs(replica, main=result.commit, request_pin="missing", returned="missing")

        # The same input snapshot and selector do not authorize a different request.
        self.call("publish", self.source, subtract_result, rejected=WRONG_PARENT)
        self.refs(self.source, main=self.input, request_pin=add.commit, returned=result.commit)
        self.same_result(self.source, "returned", result)

    def restart_and_collect(self):
        request = self.new_request(self.source, self.request, self.input)
        self.refs(self.source, main=self.input, request_pin=request.commit, returned="missing")
        self.collect_orphan(self.source)

        self.probe("stage-input", self.worker, self.request)  # Stop immediately after committed import.
        self.request.unlink()
        self.refs(self.worker, incoming=request.commit, result_pin="missing", main="missing")
        self.collect_orphan(self.worker)
        self.result.write_bytes(b"do not overwrite")
        self.call("work", self.worker, self.result, rejected=self.result.name)
        require(self.result.read_bytes() == b"do not overwrite", self.result)
        result = self.observe(self.worker, "result-pin", request, 44)
        self.collect_orphan(self.worker)
        retry = self.path / "retry.dml"
        self.call("work", self.worker, retry)
        self.refs(self.worker, main="missing", incoming=request.commit, result_pin=result.commit)

        self.call("stage-result", self.source, retry)
        retry.unlink()
        self.refs(self.source, main=self.input, request_pin=request.commit, returned=result.commit)
        self.collect_orphan(self.source)
        self.same_result(self.source, "returned", result)
        self.call("publish", self.source)
        self.refs(self.source, main=result.commit, request_pin="missing", returned="missing")
        self.collect_orphan(self.source)
        self.same_result(self.source, "main", result)

        self.probe("retarget", self.worker, "incoming", request.input_commit)
        self.call("release-input", self.worker, rejected="release inspected staging ref")
        self.refs(self.worker, main="missing", incoming=request.input_commit, result_pin=result.commit)
        self.same_result(self.worker, "result-pin", result)
        self.probe("retarget", self.worker, "incoming", request.commit)
        self.call("release-input", self.worker)
        self.refs(self.worker, main="missing", incoming="missing", result_pin=result.commit)
        self.collect_orphan(self.worker)
        self.same_result(self.worker, "result-pin", result)

    def wrong_parent(self):
        alternate_source = self.path / "alternate"
        alternate_request = self.path / "alternate.dml"
        wrong_worker = self.path / "wrong-worker"
        wrong_bundle = self.path / "wrong.dml"
        other, _ = self.probe("seed", alternate_source, "alternate").splitlines()
        require(other != self.input, other)
        original = self.new_request(self.source, self.request, self.input)
        self.call("work", self.worker, self.result, self.request)
        correct = self.observe(self.worker, "result-pin", original, 44)
        alternate = self.new_request(alternate_source, alternate_request, other)
        self.call("work", wrong_worker, wrong_bundle, alternate_request)
        wrong = self.observe(wrong_worker, "result-pin", alternate, 44)
        require(correct.commit != wrong.commit and correct.request != wrong.request, (correct, wrong))
        # Same input and output datums and implementation, different request parents.
        require(correct[3:] == wrong[3:], (correct, wrong))
        self.call("publish", self.source, wrong_bundle, rejected=WRONG_PARENT)
        self.refs(self.source, main=self.input, request_pin=original.commit, returned=wrong.commit)
        self.collect_orphan(self.source)
        self.same_result(self.source, "returned", wrong)

    def wrong_implementation(self):
        request = self.new_request(self.source, self.request, self.input)
        self.probe("stage-input", self.worker, self.request)
        forged = self.probe("forge-result", self.worker, self.result)
        result = self.observe(self.worker, "fixture-result", request, 44, SUBTRACT_ONE)
        require(result.commit == forged, (result, forged))
        self.call("publish", self.source, self.result,
                  rejected="result implementation does not match the requested operation")
        self.refs(self.source, main=self.input, request_pin=request.commit, returned=result.commit)
        self.same_result(self.source, "returned", result)

    def unsupported_operation(self):
        self.call("request", self.source, self.request, rejected="recover request pin")
        require(not self.request.exists(), self.request)
        self.refs(self.source, main=self.input, request_pin="missing", returned="missing")
        self.call("request", self.source, self.request, UNKNOWN, "snapshot", "value",
                  rejected="unsupported request operation")
        require(not self.request.exists(), self.request)
        self.refs(self.source, main=self.input, request_pin="missing", returned="missing")

        # Independently produce a valid request using an operation the worker does not implement.
        forged = self.probe("forge-request", self.source, self.request)
        request = self.read_request(self.source, "fixture-request", self.input, UNKNOWN, "snapshot", "value", 43)
        require(request.commit == forged, (request, forged))
        self.call("work", self.worker, self.result, self.request, rejected="unsupported request operation")
        require(not self.result.exists(), self.result)
        self.refs(self.worker, main="missing", incoming=request.commit, result_pin="missing")

    def stale_tip(self):
        occupied = self.path / "occupied.dml"
        occupied.write_bytes(b"already here")
        self.call("request", self.source, occupied, ADD_ONE, "snapshot", "value", rejected=occupied.name)
        require(occupied.read_bytes() == b"already here", occupied)
        request = self.read_request(self.source, "request-pin", self.input, ADD_ONE, "snapshot", "value", 43)
        competitor = self.probe("compete", self.source)
        require(competitor != self.input, competitor)
        self.refs(self.source, main=competitor, request_pin=request.commit, returned="missing")
        # A fresh explicit request may not overwrite the pin or silently re-export it.
        self.call("request", self.source, self.request, SUBTRACT_ONE, "snapshot", "value",
                  rejected="request-pin already exists")
        require(not self.request.exists(), self.request)
        self.refs(self.source, main=competitor, request_pin=request.commit, returned="missing")
        # The original input is a sibling of main and is still reachable through the request after GC.
        self.collect_orphan(self.source)
        self.call("request", self.source, self.request)
        self.call("work", self.worker, self.result, self.request)
        result = self.observe(self.worker, "result-pin", request, 44)
        self.call("stage-result", self.source, self.result)
        self.call("publish", self.source, rejected="main no longer points to the original input snapshot")
        self.refs(self.source, main=competitor, request_pin=request.commit, returned=result.commit)
        self.collect_orphan(self.source)
        self.same_result(self.source, "returned", result)


def main():
    example, fixture = (Path(arg).resolve() for arg in sys.argv[1:])
    with tempfile.TemporaryDirectory(prefix="dml-handoff-") as temp:
        for case in ("direct", "distinct_operations", "restart_and_collect", "wrong_parent",
                     "wrong_implementation", "unsupported_operation", "stale_tip"):
            handoff = Handoff(Path(temp) / case, example, fixture)
            getattr(handoff, case)()
            print(f"{case}: passed")


if __name__ == "__main__":
    main()
