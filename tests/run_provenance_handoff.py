"""Process integration; executable paths may point to consumers of an installed libdml."""

import subprocess
import sys
import tempfile
from pathlib import Path


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

    def observe(self, repository, ref, expected_parent):
        fields = self.probe("result", repository, ref).split()
        require(len(fields) == 8, fields)
        require(fields[1] == expected_parent, (fields, expected_parent))
        require(fields[5:] == ["43", "44", "example.add-one@1"], fields)
        return fields

    def same_result(self, repository, ref, expected):
        actual = self.observe(repository, ref, expected[1])
        require(actual == expected, (actual, expected))

    def direct(self):
        # Normal case: exactly three workflow invocations, exchanging only the bundles.
        self.call("request", self.source, self.request)
        self.call("work", self.worker, self.result, self.request)
        self.call("publish", self.source, self.result)
        result = self.observe(self.worker, "result-pin", self.input)
        self.same_result(self.source, "main", result)
        self.refs(self.source, main=result[0], request_pin="missing", returned="missing")
        self.refs(self.worker, main="missing", incoming=self.input, result_pin=result[0])

    def restart_and_collect(self):
        self.call("request", self.source, self.request)
        self.refs(self.source, main=self.input, request_pin=self.input, returned="missing")
        self.collect_orphan(self.source)

        self.probe("stage-input", self.worker, self.request)  # Stop immediately after committed import.
        self.request.unlink()
        self.refs(self.worker, incoming=self.input, result_pin="missing", main="missing")
        self.collect_orphan(self.worker)
        self.result.write_bytes(b"do not overwrite")
        self.call("work", self.worker, self.result, rejected=self.result.name)
        require(self.result.read_bytes() == b"do not overwrite", self.result)
        result = self.observe(self.worker, "result-pin", self.input)
        self.collect_orphan(self.worker)
        retry = self.path / "retry.dml"
        self.call("work", self.worker, retry)
        self.refs(self.worker, main="missing", incoming=self.input, result_pin=result[0])

        self.call("stage-result", self.source, retry)
        retry.unlink()
        self.refs(self.source, main=self.input, request_pin=self.input, returned=result[0])
        self.collect_orphan(self.source)
        self.same_result(self.source, "returned", result)
        self.call("publish", self.source)
        self.refs(self.source, main=result[0], request_pin="missing", returned="missing")
        self.collect_orphan(self.source)
        self.same_result(self.source, "main", result)

        self.probe("retarget", self.worker, "incoming", self.ancestor)
        self.call("release-input", self.worker, rejected="release inspected staging ref")
        self.refs(self.worker, main="missing", incoming=self.ancestor, result_pin=result[0])
        self.same_result(self.worker, "result-pin", result)
        self.probe("retarget", self.worker, "incoming", self.input)
        self.call("release-input", self.worker)
        self.refs(self.worker, main="missing", incoming="missing", result_pin=result[0])
        self.collect_orphan(self.worker)
        self.same_result(self.worker, "result-pin", result)

    def wrong_parent(self):
        alternate_source = self.path / "alternate"
        alternate_request = self.path / "alternate.dml"
        wrong_worker = self.path / "wrong-worker"
        wrong_bundle = self.path / "wrong.dml"
        other, _ = self.probe("seed", alternate_source, "alternate").splitlines()
        require(other != self.input, other)
        self.call("request", self.source, self.request)
        self.call("work", self.worker, self.result, self.request)
        correct = self.observe(self.worker, "result-pin", self.input)
        self.call("request", alternate_source, alternate_request)
        self.call("work", wrong_worker, wrong_bundle, alternate_request)
        wrong = self.observe(wrong_worker, "result-pin", other)
        require(correct[0] != wrong[0], (correct, wrong))
        # Same input and output datums and implementation, different parent.
        require(correct[2:] == wrong[2:], (correct, wrong))
        self.call("publish", self.source, wrong_bundle, rejected="result parent does not match")
        self.refs(self.source, main=self.input, request_pin=self.input, returned=wrong[0])
        self.collect_orphan(self.source)
        self.same_result(self.source, "returned", wrong)

    def stale_tip(self):
        occupied = self.path / "occupied.dml"
        occupied.write_bytes(b"already here")
        self.call("request", self.source, occupied, rejected=occupied.name)
        require(occupied.read_bytes() == b"already here", occupied)
        competitor = self.probe("compete", self.source)
        require(competitor != self.input, competitor)
        self.refs(self.source, main=competitor, request_pin=self.input, returned="missing")
        # The original input is a sibling of main and is still pinned, even after GC.
        self.collect_orphan(self.source)
        self.call("request", self.source, self.request)
        self.call("work", self.worker, self.result, self.request)
        result = self.observe(self.worker, "result-pin", self.input)
        self.call("stage-result", self.source, self.result)
        self.call("publish", self.source, rejected="main no longer points to the original request")
        self.refs(self.source, main=competitor, request_pin=self.input, returned=result[0])
        self.collect_orphan(self.source)
        self.same_result(self.source, "returned", result)


def main():
    example, fixture = (Path(arg).resolve() for arg in sys.argv[1:])
    with tempfile.TemporaryDirectory(prefix="dml-handoff-") as temp:
        for case in ("direct", "restart_and_collect", "wrong_parent", "stale_tip"):
            handoff = Handoff(Path(temp) / case, example, fixture)
            getattr(handoff, case)()
            print(f"{case}: passed")


if __name__ == "__main__":
    main()
