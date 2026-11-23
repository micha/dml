"""Replay individual DML core operations through the private Python binding."""

from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from importlib.util import module_from_spec, spec_from_file_location
import re
import struct

from trace_support import Replay, inventory_diff, scan_inventory


RECORD_TYPES = {"node": 3, "dag": 4, "tree": 5, "commit": 6}
DATUM_KINDS = {"i64": 3, "string": 6}
NODE_KINDS = {"literal": 1, "subdag": 2}
TXN_MODES = {"read": 1, "write": 2}
BUNDLE_HEADER = struct.Struct("<4sI16sI")
FRAME = struct.Struct("<HHI16s")


@dataclass(frozen=True)
class Operation:
    inputs: tuple[str, ...]
    output: str = ""
    ends: str = ""
    observes_failure: bool = False


OPERATIONS = {
    "repo_open": Operation(("path", "create"), "repo"),
    "repo_close": Operation(("repo",), ends="repo"),
    "txn_begin": Operation(("repo", "mode"), "txn"),
    "txn_commit": Operation(("txn",), ends="txn"),
    "txn_abort": Operation(("txn",), ends="txn"),
    "txn_put_datum": Operation(("txn", "packed"), "id"),
    "txn_get_datum": Operation(("txn", "id"), "packed"),
    "txn_put_object": Operation(("txn", "type", "packed"), "id"),
    "txn_get_object": Operation(("txn", "type", "id"), "packed"),
    "txn_ref_create": Operation(("txn", "name", "id")),
    "txn_ref_update": Operation(("txn", "name", "id")),
    "txn_ref_delete_expected": Operation(("txn", "name", "id")),
    "txn_ref_get": Operation(("txn", "name"), "id"),
    "txn_lookup_node": Operation(("txn", "id", "name"), "id"),
    "object_decode": Operation(("packed",), "view"),
    "object_view_parent": Operation(("view", "int"), "id"),
    "object_view_entry": Operation(("view", "int"), "entry"),
    "datum_decode": Operation(("packed",), "datum"),
    "repo_export_commit": Operation(("repo", "id"), "bundle", observes_failure=True),
    "repo_import_commit": Operation(("repo", "bundle"), "id", observes_failure=True),
    "repo_import_commit_staged": Operation(("repo", "bundle", "name"), "id", observes_failure=True),
    "txn_collect_garbage": Operation(("txn",), "count", observes_failure=True),
    "txn_check_integrity": Operation(("txn",), "integrity"),
}

def object_operands(args):
    if len(args) >= 2:
        kind, arity = args[0], len(args) - 2
        if kind == "node" and arity in (1, 2):
            return ("type", "id") if arity == 1 else ("type", "node_kind", "id")
        if kind == "dag" and arity % 2 == 1:
            return ("type", "id") + ("name", "id") * (arity // 2)
        if kind == "tree" and arity % 2 == 0:
            return ("type",) + ("name", "id") * (arity // 2)
        if kind == "commit" and arity >= 1:
            return ("type",) + ("id",) * arity
    raise ValueError("unsupported object encoder arguments")


def operation_for(op, args):
    if op == "object_encode":
        return Operation(object_operands(args), "packed")
    if op == "datum_encode":
        if not args or args[0] not in DATUM_KINDS:
            raise ValueError("unsupported datum encoder kind")
        return Operation(("datum_kind", "int" if args[0] == "i64" else "text"), "packed")
    return OPERATIONS[op]


def bundle_items(data):
    """Observe envelope and ordered frames independently of DML."""
    if not BUNDLE_HEADER.size <= len(data) <= 64 * 1024**2:
        raise ValueError("invalid exported bundle length")
    magic, version, root, count = BUNDLE_HEADER.unpack_from(data)
    if magic != b"DMLB" or version != 1 or not 0 < count <= 262144:
        raise ValueError("invalid exported bundle header")
    items = [root.hex()]
    offset = BUNDLE_HEADER.size
    for _ in range(count):
        if len(data) - offset < FRAME.size:
            raise ValueError("short exported bundle frame header")
        tag, reserved, length, identifier = FRAME.unpack_from(data, offset)
        offset += FRAME.size
        end = offset + length
        if tag not in range(2, 7) or reserved or not 0 < length <= 16 * 1024**2 or end > len(data):
            raise ValueError("invalid exported bundle frame")
        items.extend((str(tag), identifier.hex(), data[offset:end].hex()))
        offset = end
    if offset != len(data):
        raise ValueError("unexpected trailing bytes in exported bundle")
    return items


class CoreHistory:
    def __init__(self, core, scanner, directory):
        self.core = core
        self.scanner = scanner
        self.directory = directory
        self.values = {kind: {} for kind in ("repo", "txn", "packed", "id", "view", "bundle")}
        self.txn_repos = {}
        self.before = {}

    def path(self, alias):
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", alias):
            raise ValueError(f"invalid repository alias {alias!r}")
        return self.directory / alias

    def resolve(self, kind, arg):
        if kind in ("packed", "id", "bundle") and arg.startswith("hex:"):
            return bytes.fromhex(arg[4:])
        if kind == "bundle" and "~" in arg:
            alias, drop = arg.split("~")
            count = int(drop)
            if count < 1:
                raise ValueError("bundle suffix length must be positive")
            return self.values[kind][alias][:-count]
        if kind in self.values:
            if arg not in self.values[kind] and kind in ("packed", "id", "bundle") and re.fullmatch(r"(?:[0-9a-f]{2})+", arg):
                return bytes.fromhex(arg)
            return self.values[kind][arg]
        if kind == "path":
            return str(self.path(arg))
        if kind == "create":
            return {"create": True, "existing": False}[arg]
        if kind == "mode":
            return TXN_MODES[arg]
        if kind == "type":
            return RECORD_TYPES[arg]
        if kind == "datum_kind":
            return DATUM_KINDS[arg]
        if kind == "node_kind":
            return NODE_KINDS[arg]
        if kind in ("name", "text"):
            return arg.encode("utf-8")
        if kind == "int":
            return int(arg)
        raise ValueError(f"unsupported argument kind {kind}")

    def observe_output(self, output, alias, status, result):
        value, count, items = "", 0, []
        if output in ("packed", "id", "bundle"):
            value = result.hex()
            if output == "bundle" and status == "ok":
                items = bundle_items(result)
        elif output == "view":
            result, reference, count = result
            value = reference.hex()
            self.values["id"][alias] = reference
        elif output == "entry":
            result, name = result
            value, items = result.hex(), [name.hex()]
            output = "id"
        elif output == "datum":
            payload, count = result
            value = payload.hex()
        elif output == "count":
            count = result
        elif output == "integrity":
            report, unreachable = result
            items = [str(number) for number in report]
            for tag, identifier in sorted(unreachable):
                items.extend((str(tag), identifier.hex()))
        if status == "ok" and output in self.values:
            self.values[output][alias] = result
        return value, count, items

    def run(self, op, *args):
        spec = operation_for(op, args)
        has_alias = spec.output in ("txn", "packed", "id", "view", "bundle", "entry")
        if len(args) != len(spec.inputs) + has_alias:
            raise ValueError(f"wrong argument count for {op}")
        out = args[-1] if has_alias else ""
        primary = ""
        if spec.inputs[0] in ("repo", "path"):
            primary = args[0]
        elif spec.inputs[0] == "txn":
            primary = self.txn_repos[args[0]]
        if spec.output == "repo":
            out = primary
            if out in self.values["repo"]:
                raise ValueError("close the repository before reopening it")
        if spec.output == "txn" and (out in self.txn_repos or primary in self.txn_repos.values()):
            raise ValueError("end the active transaction before starting another for this repository")

        native_args = [self.resolve(kind, arg) for kind, arg in zip(spec.inputs, args)]

        status, value, count, items = "ok", "", 0, []
        try:
            result = getattr(self.core, op)(*native_args)
        except RuntimeError as error:
            if (len(error.args) != 3 or not isinstance(error.args[0], str)
                    or not isinstance(error.args[1], int) or not isinstance(error.args[2], str)):
                raise
            status = error.args[0]
        else:
            if spec.observes_failure:
                status, result = result
            value, count, items = self.observe_output(spec.output, out, status, result)
            if op == "repo_open":
                self.before.setdefault(primary, {})
            elif op == "txn_begin":
                self.txn_repos[out] = primary
        if spec.ends and (spec.ends == "txn" or status == "ok"):
            del self.values[spec.ends][args[0]]
            if spec.ends == "txn":
                del self.txn_repos[args[0]]

        changes, other_changes = [], []
        for repo, before in self.before.items():
            after = scan_inventory(self.scanner, self.path(repo))
            (changes if repo == primary else other_changes).extend(inventory_diff(before, after))
            self.before[repo] = after
        return dict(op=op, args=list(args), status=status, value=value, count=count, items=items,
                    changes=changes, otherChanges=other_changes)

    def close(self):
        # Safety net for invalid histories, not a modeled transition.
        self.values["txn"].clear()
        self.values["repo"].clear()


class Suite:
    def __init__(self, binding, scanner):
        spec = spec_from_file_location("_dml_core", binding)
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load the DML Python binding at {binding}")
        self.core = module_from_spec(spec)
        spec.loader.exec_module(self.core)
        self.scanner = scanner

    @contextmanager
    def history(self, directory):
        history = CoreHistory(self.core, self.scanner, directory)
        try:
            yield Replay({op: partial(history.run, op) for op in (*OPERATIONS, "object_encode", "datum_encode")})
            if history.values["repo"] or history.values["txn"]:
                raise ValueError("history must explicitly end transactions and close the repository")
        finally:
            history.close()
