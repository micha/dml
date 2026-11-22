"""Native fixture and operations for ref histories."""

from contextlib import contextmanager
import re
import struct

from trace_support import Replay, inventory_diff, run_native, scan_inventory


ID = r"[0-9a-f]{32}"
STATUS = r"[a-z_]+"


def response(pattern, stdout):
    match = re.fullmatch(pattern + r"\n", stdout)
    if not match:
        raise ValueError(f"Unexpected replay response {stdout!r}; expected {pattern}")
    return match.groups()


def ref_key(name):
    return f"refs/heads/{name}".encode("ascii").hex()


def snapshot_rows(dag, parent, tree, tip):
    """Describe the requested v1 objects without reading bytes from the store."""
    def row(kind, identifier, tag, body):
        header = struct.pack("<4sHHIII", b"DML1", 1, tag, 20 + len(body), 0, 0)
        return dict(key=f"objects/{kind}/{identifier}".encode("ascii").hex(),
                    packed=(header + body).hex())

    entry = b"snapshot"
    tree_body = struct.pack("<II", 1, len(entry)) + entry + bytes.fromhex(dag)
    commit_body = bytes.fromhex(tree) + struct.pack("<I", 1) + bytes.fromhex(parent)
    return [row("trees", tree, 5, tree_body), row("commits", tip, 6, commit_body)]


def read_ref(runner, repo, name):
    *statuses, tip, tree, parents = response(
        rf"READ ({STATUS}) ({STATUS}) ({STATUS}) ({ID}) ({ID})((?: {ID})*)",
        run_native(runner, "read", repo, name),
    )
    return dict(tip=tip, tree=tree, parents=parents.split(), statuses=statuses)


class Suite:
    initializers = ("init", "changedInit")

    def __init__(self, runner, scanner, workspace):
        self.runner = runner
        self.scanner = scanner

    @contextmanager
    def history(self, directory):
        repo = directory / "repo"
        a, b, empty_tree, dag = response(rf"READY ({ID}) ({ID}) ({ID}) ({ID})",
                                         run_native(self.runner, "seed", repo))
        targets = {"A": a, "B": b}
        before = scan_inventory(self.scanner, repo)
        keys = [f"objects/commits/{a}", f"objects/commits/{b}",
                f"objects/trees/{empty_tree}", f"objects/dags/{dag}"]
        if (a == b or any(key.startswith(ref_key("")) for key in before)
                or any(key.encode("ascii").hex() not in before for key in keys)):
            raise ValueError("Expected an unreferenced fixture with the announced objects")

        def observe():
            nonlocal before
            after = scan_inventory(self.scanner, repo)
            changes = inventory_diff(before, after)
            before = after
            return changes

        def create_ref(name, target):
            statuses = list(response(rf"CREATE ({STATUS}) ({STATUS})",
                                     run_native(self.runner, "create", repo, name, targets[target])))
            return dict(op="create", key=ref_key(name), tip=targets[target], tree="", parent="",
                        extraKey="", finish="commit", rows=[], statuses=statuses, changes=observe(),
                        readback=dict(tip="", tree="", parents=[], statuses=[]))

        def publish_snapshot(name, parent, finish, extra_name):
            *statuses, tree, tip = response(
                rf"PUBLISH ({STATUS}) ({STATUS}) ({STATUS}) ({STATUS}) ({STATUS}) ({ID}) ({ID})",
                run_native(self.runner, "publish", repo, name, targets[parent], dag, finish, extra_name),
            )
            changes = observe()
            # Open from a fresh process after the write transaction and raw inventory scan.
            readback = read_ref(self.runner, repo, name)
            return dict(op="publish", key=ref_key(name), tip=tip, tree=tree, parent=targets[parent],
                        extraKey=ref_key(extra_name) if extra_name else "", finish=finish,
                        rows=snapshot_rows(dag, targets[parent], tree, tip),
                        statuses=statuses, changes=changes, readback=readback)

        yield Replay({"create_ref": create_ref, "publish_snapshot": publish_snapshot},
                     fixture=dict(a=a, emptyTree=empty_tree))
