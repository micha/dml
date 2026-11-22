"""Native fixture and operations for ref histories."""

from contextlib import contextmanager
import re
import subprocess

from trace_support import Replay, TIMEOUT, inventory_diff, scan_inventory


def read_line(process, pattern):
    line = process.stdout.readline()
    match = re.fullmatch(pattern + r"\n", line)
    if not match:
        raise ValueError(f"Unexpected replay response {line!r}; expected {pattern}")
    return match.groups()


class Suite:
    initializers = ("init", "changedInit")

    def __init__(self, runner, scanner, workspace):
        self.runner = runner
        self.scanner = scanner

    @contextmanager
    def history(self, directory):
        repo = directory / "repo"
        # Meson's test timeout bounds blocking reads from the interactive child.
        with subprocess.Popen([self.runner, repo], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              text=True, encoding="ascii") as process:
            try:
                target_a, target_b = read_line(process, r"READY ([0-9a-f]{32}) ([0-9a-f]{32})")
                if target_a == target_b:
                    raise ValueError("The runner must seed two distinct commit IDs")
                targets = {"A": target_a, "B": target_b}
                before = scan_inventory(self.scanner, repo)
                if (any(key.startswith(b"refs/heads/".hex()) for key in before)
                        or any(f"objects/commits/{target}".encode("ascii").hex() not in before
                               for target in targets.values())):
                    raise ValueError("Expected an unreferenced fixture with both announced commits")

                def create_ref(name, target):
                    nonlocal before
                    # Reject unrepresentable protocol requests, not failed API operations.
                    if not re.fullmatch(r"[!-~]+", name) or target not in targets:
                        raise ValueError(f"Invalid create_ref arguments: {name!r}, {target!r}")
                    process.stdin.write(f"{name} {target}\n")
                    process.stdin.flush()
                    created, committed = read_line(process, r"STEP ([a-z_]+) ([a-z_]+)")
                    after = scan_inventory(self.scanner, repo)
                    changes = inventory_diff(before, after)
                    before = after
                    return dict(refKey=f"refs/heads/{name}".encode("ascii").hex(),
                                targetId=targets[target], createStatus=created,
                                commitStatus=committed, changes=changes)

                yield Replay({"create_ref": create_ref})
                process.stdin.close()
                status = process.wait(timeout=TIMEOUT)
                if status != 0 or process.stdout.read():
                    raise ValueError(f"Replay did not finish cleanly (exit status {status})")
            finally:
                if process.poll() is None:
                    process.kill()
