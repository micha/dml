"""Replay atomic staging and observe exact persisted rows in a separate LMDB scan."""

from contextlib import contextmanager
from functools import partial
import re

from replay_gc import GROUPS
from replay_transfer import encode, import_attempt, seed, ZERO_ID
from trace_support import Replay, run_native, scan_inventory


def inventory_rows(scanner, repo):
    return [dict(key=key, packed=packed) for key, packed in scan_inventory(scanner, repo).items()]


def fields(stdout, pattern):
    match = re.fullmatch(pattern, stdout)
    if not match:
        raise ValueError(f"Unexpected native staged-import observation: {stdout!r}")
    return match.groups()


class Suite:
    initializers = ("init",)

    def __init__(self, runner, scanner, workspace):
        self.runner = runner
        self.scanner = scanner
        frames = seed(runner, scanner, workspace / "worker", "retention")
        selected = [frames[label] for group in ("base", "selected") for label in GROUPS[group]]
        result = [frames[label] for label in GROUPS["result"]]
        self.bundles = {}
        for target, closure in (("selected", selected), ("result", selected + result)):
            path = workspace / f"{target}.dmlb"
            path.write_bytes(encode(closure, frames[target].identifier))
            self.bundles[target, "valid"] = path
        path = workspace / "short.dmlb"
        path.write_bytes(self.bundles["result", "valid"].read_bytes()[:-1])
        self.bundles["result", "truncated"] = path
        self.selected = {"id": frames["selected"].identifier.hex(),
                         "rows": [row.row for row in selected]}
        self.result = {"id": frames["result"].identifier.hex(), "rows": [row.row for row in result]}

    @contextmanager
    def history(self, directory):
        repo = directory / "origin"
        kept = seed(self.runner, self.scanner, repo, "destination")
        fixture = dict(keep=dict(id=kept["keep"].identifier.hex(), rows=[row.row for row in kept.values()]),
                       selected=self.selected, result=self.result, initialRows=inventory_rows(self.scanner, repo))
        native = Origin(self.runner, repo, self.bundles, self.selected["id"])
        yield Replay({name: partial(self.observe, repo, getattr(native, name)) for name in (
            "import_result", "collect", "stage", "capture_main", "advance_main",
            "publish_returned", "read_ref", "release_returned",
        )}, fixture)

    def observe(self, repo, operation, *args):
        evidence = operation(*args)
        return dict(command=operation.__name__, target="", ref="", variant="", compared="", result="", packed="",
                    status="none", readStatus="none", update="none", completion="none", removed=123456789,
                    inventory=inventory_rows(self.scanner, repo)) | evidence


class Origin:
    def __init__(self, runner, repo, bundles, selected):
        self.runner = runner
        self.repo = repo
        self.bundles = bundles
        self.selected = selected
        self.captured = ZERO_ID
        self.returned = ZERO_ID

    def run(self, command, *args):
        return run_native(self.runner, command, self.repo, *args)

    def import_result(self):
        return self.import_bundle("result", "valid")

    def import_bundle(self, target, variant, *, ref=None):
        attempt = import_attempt(self.runner, self.repo, self.bundles[target, variant], "import", ref=ref)
        return {name: attempt[name] for name in ("status", "result", "completion")}

    def stage(self, target, ref, variant):
        if ref not in {"incoming", "returned", "bad/ref"}:
            raise ValueError(f"Invalid staged-import fixture ref: {ref!r}")
        attempt = self.import_bundle(target, variant, ref=ref)
        if ref == "returned":
            # Carry the actual returned output forward, even when the call failed.
            self.returned = attempt["result"]
        return dict(target=target, ref=ref, variant=variant) | attempt

    def collect(self):
        stdout = self.run("gc_transaction", "none", "none", "", "", "commit")
        status, edited, completion, removed = fields(stdout, r"([a-z_]+) ([a-z_]+) ([a-z_]+) ([0-9]+)\n")
        return dict(status=status, update=edited, completion=completion, removed=int(removed))

    def read_ref(self, ref):
        if ref not in {"main", "incoming", "returned"}:
            raise ValueError(f"Unknown ref: {ref!r}")
        stdout = self.run("read_ref", ref)
        status, result, read_status, packed = fields(
            stdout, r"([a-z_]+) ([0-9a-f]{32})\n([a-z_]+) ((?:[0-9a-f]{2})*)\n")
        return dict(ref=ref, status=status, result=result, readStatus=read_status, packed=packed)

    def capture_main(self):
        attempt = self.read_ref("main")
        self.captured = attempt["result"]
        return attempt

    def advance_main(self):
        stdout = self.run("update_ref", "main", self.selected)
        status, completion = fields(stdout, r"([a-z_]+)\n([a-z_]+)\n")
        return dict(status=status, completion=completion)

    def publish_returned(self):
        stdout = self.run("publish_expected", "main", self.captured, self.returned)
        status, actual, update, completion = fields(stdout, r"([a-z_]+) ([0-9a-f]{32})\n([a-z_]+) ([a-z_]+)\n")
        return dict(status=status, completion=completion, compared=self.captured,
                    target=self.returned, result=actual, update=update)

    def release_returned(self):
        stdout = self.run("release_expected", "returned", self.returned, "commit")
        status, completion = fields(stdout, r"([a-z_]+)\n([a-z_]+)\n")
        return dict(status=status, completion=completion, target=self.returned)
