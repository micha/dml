"""Execute GC histories and observe persisted rows through the raw LMDB scanner."""

from contextlib import contextmanager
from functools import partial
import re

from replay_transfer import encode, import_attempt, seed
from trace_support import Replay, inventory_diff, run_native, scan_inventory

# Rows in construction order, not a closure learned from the collector or checker.
GROUPS = {
    "base": ("base_datum", "base_node", "base_dag", "base_tree", "base"),
    "selected": ("selected_datum", "selected_node", "selected_dag", "selected_tree", "selected"),
    "result": ("output_datum", "output_node", "implementation_datum", "implementation_node",
               "result_dag", "result_tree", "result"),
}


class Suite:
    initializers = ("init",)

    def __init__(self, runner, scanner, workspace):
        self.runner = runner
        self.scanner = scanner
        self.frames = seed(runner, scanner, workspace / "retention", "retention")
        frames = [self.frames[label] for group in GROUPS.values() for label in group]
        self.bundle = workspace / "retention.dmlb"
        self.bundle.write_bytes(encode(frames, self.frames["result"].identifier))
        self.fixture = {
            target: dict(id=self.frames[target].identifier.hex(),
                         rows=[self.frames[label].row for label in labels])
            for target, labels in GROUPS.items()
        }
        self.fixture["damage"] = self.frames["implementation_datum"].row

    @contextmanager
    def history(self, directory):
        repo = directory / "destination"
        seed(self.runner, self.scanner, repo, "empty")
        yield Replay({"import_result": partial(self.observe, repo, self.import_result),
                      "transact": partial(self.observe, repo, self.transact),
                      "damage": partial(self.observe, repo, self.damage)}, self.fixture)

    def observe(self, repo, operation, *args):
        before = scan_inventory(self.scanner, repo)
        attempt = operation(repo, *args)
        after = scan_inventory(self.scanner, repo)
        return dict(command=operation.__name__, order="", edit="", ref="", target="", finish="",
                    status="none", refStatus="none", completion="none", removed=123456789, result="",
                    changes=inventory_diff(before, after)) | attempt

    def import_result(self, repo):
        attempt = import_attempt(self.runner, repo, self.bundle, "import")
        return {name: attempt[name] for name in ("status", "completion", "result")}

    def transact(self, repo, order, edit, ref, target, finish):
        if order == "none" and (edit, ref, target) == ("none", "", ""):
            identifier = ""
        elif (order in {"before", "after", "only"} and edit in {"create", "update", "delete"}
              and ref in {"main", "incoming", "result-pin"} and target in GROUPS):
            identifier = self.frames[target].identifier.hex()
        else:
            raise ValueError(f"Invalid GC ref edit: {(order, edit, ref, target)!r}")
        if finish not in {"commit", "abort"}:
            raise ValueError(f"Invalid GC transaction completion: {finish!r}")
        stdout = run_native(self.runner, "gc_transaction", repo, order, edit, ref, identifier, finish)
        match = re.fullmatch(r"([a-z_]+) ([a-z_]+) ([a-z_]+) ([0-9]+)\n", stdout)
        if not match:
            raise ValueError(f"Unexpected C GC response: {stdout!r}")
        status, edited, completion, removed = match.groups()
        return dict(order=order, edit=edit, ref=ref, target=target, finish=finish,
                    status=status, refStatus=edited, completion=completion, removed=int(removed))

    def damage(self, repo):
        # Delete an implementation datum from the detached result graph. The
        # selected commit still exists and can be staged before collection.
        run_native(self.runner, "delete", repo, self.frames["implementation_datum"].key)
        return {}
