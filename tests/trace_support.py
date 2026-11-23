"""Shared dispatch and independent LMDB observations for trace replay."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import re
import subprocess


TIMEOUT = 20


@dataclass(frozen=True)
class Replay:
    """A live fixture and its registered operation handlers for one history."""

    operations: Mapping[str, Callable[..., dict]]


def run_native(*args):
    result = subprocess.run(args, capture_output=True, text=True, encoding="ascii", timeout=TIMEOUT)
    if result.returncode != 0:
        raise ValueError(f"{args[0]} {args[1]} exited {result.returncode}: {result.stderr}")
    return result.stdout


def scan_inventory(scanner, repo):
    inventory = {}
    for line in run_native(scanner, repo).splitlines(keepends=True):
        match = re.fullmatch(r"([0-9a-f]+) ([0-9a-f]*)\n", line)
        if not match or any(len(group) % 2 for group in match.groups()) or match[1] in inventory:
            raise ValueError(f"Invalid LMDB inventory entry in {repo}")
        inventory[match[1]] = match[2]
    if b"meta/schema".hex() not in inventory:
        raise ValueError(f"Inventory is missing the schema in {repo}")
    return inventory


def inventory_diff(before, after):
    changes = []
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        if old != new:
            kind = "added" if old is None else "removed" if new is None else "modified"
            changes.append(dict(kind=kind, key=key, before=old or "", after=new or ""))
    return changes
