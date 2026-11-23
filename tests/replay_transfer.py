"""Native fixtures and operations for transfer histories."""

from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
import re
import struct

from trace_support import Replay, inventory_diff, run_native, scan_inventory


HEADER = struct.Struct("<4sI16sI")
FRAME = struct.Struct("<HHI16s")
KINDS = {2: "datums", 3: "nodes", 4: "dags", 5: "trees", 6: "commits"}
TAGS = {name: tag for tag, name in KINDS.items()}

# This intentionally describes the construction, not decoded edges from export.
# Insertion order also supplies one valid input order independently of C export.
EDGES = {
    "first": (), "second": (), "third": (), "fourth": (), "fifth": (),
    "list": ("first", "second"), "set": ("third", "fourth"), "map": ("list", "set"),
    "literal": ("map",), "inner": ("literal",), "nested": ("inner",), "bound": ("fifth",),
    "outer": ("nested", "bound"), "main_tree": ("outer", "inner"), "empty_tree": (),
    "ancestor": ("empty_tree",), "old_head": ("empty_tree", "ancestor"),
    "historical_literal": ("first",), "historical_dag": ("historical_literal",),
    "parent_tree": ("historical_dag",), "other_parent": ("parent_tree",),
    "root": ("main_tree", "other_parent", "old_head"),
}
LARGE_ORDER = ("small", "large", "list", "single_node", "single_dag", "single_tree", "root")
EXPORTS = {
    "export", "repeat", "reexport", "missing_root", "missing_edge", "busy_export", "dirty_export",
    "oversize_export",
}
TRANSFORMS = {
    "bad_magic", "bad_version", "reserved", "short_header", "short_frame", "short_record",
    "trailing", "wrong_kind", "embedded_kind", "wrong_id", "wrong_root", "wrong_root_type",
    "bad_packed", "duplicate", "extra", "thin", "forward", "oversize_count", "oversize_bundle",
}
IMPORTS = {
    "import", "alternative", "import_exported", "busy_import", "map_full", "corrupt_store",
    "oversize_record",
}


@dataclass(frozen=True)
class Frame:
    kind: int
    identifier: bytes
    packed: bytes

    @property
    def key(self):
        return f"objects/{KINDS[self.kind]}/{self.identifier.hex()}"

    @property
    def row(self):
        return dict(key=self.key.encode("ascii").hex(), packed=self.packed.hex())

    def encode(self):
        return FRAME.pack(self.kind, 0, len(self.packed), self.identifier) + self.packed


def seed(runner, scanner, repo, profile):
    if repo.exists():
        raise ValueError(f"Fixture directory already exists: {repo}")
    keys = {}
    for line in run_native(runner, "seed", repo, profile).splitlines():
        label, kind, identifier = line.split(" ")
        if label in keys or not re.fullmatch(r"[0-9a-f]{32}", identifier) or kind not in TAGS:
            raise ValueError(f"Invalid fixture row: {line!r}")
        keys[label] = (kind, identifier)
    inventory = scan_inventory(scanner, repo)
    frames = {
        label: Frame(TAGS[kind], bytes.fromhex(identifier),
                     bytes.fromhex(inventory[f"objects/{kind}/{identifier}".encode("ascii").hex()]))
        for label, (kind, identifier) in keys.items()
    }
    if len(set(frame.key for frame in frames.values())) != len(frames):
        raise ValueError(f"Fixture labels must have distinct typed keys: {repo}")
    return frames


def encode(frames, root):
    return HEADER.pack(b"DMLB", 1, root, len(frames)) + b"".join(frame.encode() for frame in frames)


def decode(bundle):
    magic, version, root, count = HEADER.unpack_from(bundle)
    if magic != b"DMLB" or version != 1 or not 0 < count <= 262144:
        raise ValueError("Export returned an invalid v1 envelope")
    rows = []
    offset = HEADER.size
    for _ in range(count):
        kind, reserved, length, identifier = FRAME.unpack_from(bundle, offset)
        offset += FRAME.size
        if reserved or kind not in KINDS or not 0 < length <= 16 * 1024 * 1024:
            raise ValueError("Export returned a malformed frame header")
        end = offset + length
        if end > len(bundle):
            raise ValueError("Export returned a short packed record")
        rows.append(Frame(kind, identifier, bundle[offset:end]).row)
        offset = end
    if offset != len(bundle):
        raise ValueError("Export returned trailing bytes")
    return root.hex(), rows


def variant(command, frames):
    root = frames["root"].identifier
    order = [frames[label] for label in EDGES]
    if command == "wrong_kind":
        order[0] = replace(order[0], kind=1)
    elif command == "embedded_kind":
        order[0] = replace(order[0], kind=3)
    elif command == "wrong_id":
        order[0] = replace(order[0], identifier=b"\xff" * 16)
    elif command == "wrong_root":
        root = b"\xff" * 16
    elif command == "wrong_root_type":
        order = [frames["first"]]
        root = frames["first"].identifier
    elif command == "bad_packed":
        order[-1] = replace(order[-1], packed=b"\x00" + order[-1].packed[1:])
    elif command in {"duplicate", "oversize_bundle"}:
        order.insert(1, order[0])
    elif command == "extra":
        order.insert(0, frames["unreachable"])
    elif command == "thin":
        del order[0]
    elif command == "forward":
        index = list(EDGES).index("list")
        order[0], order[index] = order[index], order[0]
    elif command == "alternative":
        order[0], order[1] = order[1], order[0]
    bundle = encode(order, root)
    if command == "bad_magic":
        return b"DMLX" + bundle[4:]
    if command == "bad_version":
        return bundle[:4] + struct.pack("<I", 2) + bundle[8:]
    if command == "reserved":
        return bundle[:HEADER.size + 2] + b"\x01\x00" + bundle[HEADER.size + 4:]
    if command == "short_header":
        return bundle[:HEADER.size - 1]
    if command == "short_frame":
        return bundle[:HEADER.size + FRAME.size - 1]
    if command == "short_record":
        return bundle[:-1]
    if command == "trailing":
        return bundle + b"\0"
    if command == "oversize_count":
        # Enough bytes for the declared count. Report its profile bound before
        # the duplicate encountered if parsing starts.
        return HEADER.pack(b"DMLB", 1, root, 262145) + order[0].encode() * 262145
    return bundle


def no_value():
    return dict(stage="", parent="", id="", kind=0, i64=0)


def export_attempt(runner, command, repo, root, path):
    mode = {"busy_export": "busy", "dirty_export": "dirty"}.get(command, "normal")
    path.unlink(missing_ok=True)
    stdout = run_native(runner, "export", repo, root, path, mode)
    match = re.fullmatch(r"([a-z_]+) (empty|buffer|unchanged|other)\n([a-z_]+)\n", stdout)
    if not match:
        raise ValueError(f"Unexpected C export response: {stdout!r}")
    status, shape, completion = match.groups()
    raw = path.read_bytes() if path.exists() else b""
    result, rows = decode(raw) if raw else ("", [])
    return dict(status=status, shape=shape, completion=completion, result=result,
                rows=rows, binary=raw.hex(), value=no_value())


def import_attempt(runner, repo, path, command):
    mode = {"busy_import": "busy", "map_full": "limited"}.get(command, "normal")
    stdout = run_native(runner, "import", repo, path, mode)
    match = re.fullmatch(r"([a-z_]+) ([0-9a-f]{32})\n([a-z_]+)\n", stdout)
    if not match:
        raise ValueError(f"Unexpected C import response: {stdout!r}")
    status, result, completion = match.groups()
    return dict(status=status, shape="", completion=completion, result=result,
                rows=[], binary="", value=no_value())


def fixture_model(frames, kept):
    def commit(frame):
        return dict(id=frame.identifier.hex(), packed=frame.packed.hex())

    return dict(
        root=commit(frames["root"]), initialHead=commit(kept["keep"]),
        datum=frames["fifth"].identifier.hex(),
        parent=dict(id=frames["other_parent"].identifier.hex(), datum=frames["first"].identifier.hex()),
        rows=[frames[label].row for label in EDGES],
        edges=[dict(parent=frames[label].row["key"], child=frames[child].row["key"])
               for label, children in EDGES.items() for child in children],
    )


def large_bundle(runner, scanner, directory, profile):
    repo = directory / profile
    frames = seed(runner, scanner, repo, profile)
    bundle = directory / f"{profile}.dmlb"
    root = frames["root"].identifier
    bundle.write_bytes(encode([frames[label] for label in LARGE_ORDER], root))
    return repo, root.hex(), bundle


class Suite:
    initializers = ("init",)

    def __init__(self, runner, scanner, workspace):
        self.runner = runner
        self.scanner = scanner
        self.large_bundles = {
            case: large_bundle(runner, scanner, workspace, profile)
            for case, profile in (("map_full", "large"), ("oversize_record", "oversize"))
        }

    @contextmanager
    def history(self, directory):
        source, destination = directory / "source", directory / "destination"
        frames = seed(self.runner, self.scanner, source, "source")
        kept = seed(self.runner, self.scanner, destination, "destination")
        if {frame.key for frame in frames.values()} & {frame.key for frame in kept.values()}:
            raise ValueError("Initial destination must not overlap source objects")
        fixture = TransferHistory(self.runner, self.scanner, source, destination, frames, kept,
                                  self.large_bundles)
        yield Replay({
            "export_commit": fixture.export_commit,
            "import_commit": fixture.import_commit,
            "stage_imported": partial(fixture.write_ref, "stage_imported", "create_ref", "incoming"),
            "publish_imported": partial(fixture.write_ref, "publish_imported", "update_ref", "main"),
            "read_main": partial(fixture.read_ref, "read_main", "main"),
            "read_staged": partial(fixture.read_ref, "read_staged", "incoming"),
            "read_value": fixture.read_value,
            "read_parent_value": fixture.read_parent_value,
            "read_staged_value": partial(fixture.read_snapshot, "read_staged_value", "incoming", False),
            "read_staged_parent_value": partial(fixture.read_snapshot, "read_staged_parent_value",
                                                "incoming", True),
        }, fixture_model(frames, kept))


@dataclass
class TransferHistory:
    runner: Path
    scanner: Path
    source: Path
    destination: Path
    frames: dict[str, Frame]
    kept: dict[str, Frame]
    large_bundles: dict[str, tuple[Path, str, Path]]
    imported: str = "00" * 16

    def export_commit(self, case):
        if case not in EXPORTS:
            raise ValueError(f"Unknown export case: {case!r}")
        directory = self.source.parent
        path = directory / ("exported.dmlb" if case == "export" else "attempt.dmlb")
        root = "00" * 16 if case == "missing_root" else self.frames["root"].identifier.hex()
        repo = self.destination if case == "reexport" else self.source
        if case == "missing_edge":
            run_native(self.runner, "delete", repo, self.frames["third"].key)
        if case == "oversize_export":
            repo, root, _ = self.large_bundles["oversize_record"]
        before = scan_inventory(self.scanner, repo)
        attempt = export_attempt(self.runner, case, repo, root, path)
        after = scan_inventory(self.scanner, repo)
        # Keep the oversized record out of the generated Quint source. Preserve
        # evidence of an unexpected change as a bounded, nonempty diff.
        if case == "oversize_export":
            changes = [] if before == after else [{"kind": "oversize_diff", "key": "",
                                                    "before": "", "after": ""}]
        else:
            changes = inventory_diff(before, after)
        return dict(command=case, changes=changes, **attempt)

    def import_commit(self, case):
        if case not in IMPORTS | TRANSFORMS:
            raise ValueError(f"Unknown import case: {case!r}")
        repo = self.destination
        if case == "corrupt_store":
            run_native(self.runner, "overwrite", repo, self.frames["root"].key, self.kept["keep"].key)
        path = self.bundle_for(case)
        before = scan_inventory(self.scanner, repo)
        attempt = import_attempt(self.runner, repo, path, case)
        if case == "import_exported":
            # Carry the actual output forward, even if import failed.
            self.imported = attempt["result"]
        changes = inventory_diff(before, scan_inventory(self.scanner, repo))
        return dict(command=case, changes=changes, **attempt)

    def write_ref(self, command, native_op, ref):
        repo = self.destination
        before = scan_inventory(self.scanner, repo)
        stdout = run_native(self.runner, native_op, repo, ref, self.imported)
        match = re.fullmatch(r"([a-z_]+)\n([a-z_]+)\n", stdout)
        if not match:
            raise ValueError(f"Unexpected C {command} response: {stdout!r}")
        status, completion = match.groups()
        changes = inventory_diff(before, scan_inventory(self.scanner, repo))
        return dict(command=command, status=status, completion=completion, shape="",
                    result=self.imported, binary="", rows=[], changes=changes, value=no_value())

    def read_ref(self, command, ref):
        repo = self.destination
        before = scan_inventory(self.scanner, repo)
        stdout = run_native(self.runner, "read_ref", repo, ref)
        match = re.fullmatch(r"([a-z_]+) ([0-9a-f]{32})\n([a-z_]+) ((?:[0-9a-f]{2})*)\n", stdout)
        if not match:
            raise ValueError(f"Unexpected C readback response: {stdout!r}")
        status, result, completion, packed = match.groups()
        changes = inventory_diff(before, scan_inventory(self.scanner, repo))
        return dict(command=command, status=status, completion=completion, shape="",
                    result=result, binary=packed, rows=[], changes=changes, value=no_value())

    def read_value(self, entry, binding):
        return self.read_snapshot("read_value", "main", False, entry, binding)

    def read_parent_value(self, index, entry, binding):
        return self.read_snapshot("read_parent_value", "main", True, index, entry, binding)

    def read_snapshot(self, command, ref, parent, *args):
        repo = self.destination
        before = scan_inventory(self.scanner, repo)
        native_op = "read_parent_value" if parent else "read_value"
        stdout = run_native(self.runner, native_op, repo, ref, *args)
        parent_field = r"(?P<parent>[0-9a-f]{32}) " if parent else ""
        match = re.fullmatch(r"(?P<status>[a-z_]+) (?P<stage>[a-z_]+) (?P<head>[0-9a-f]{32}) "
                             rf"{parent_field}(?P<datum>[0-9a-f]{{32}}) "
                             r"(?P<kind>[0-9]+) (?P<i64>-?[0-9]+)\n", stdout)
        if not match:
            raise ValueError(f"Unexpected C {command} response: {stdout!r}")
        observed = match.groupdict()
        changes = inventory_diff(before, scan_inventory(self.scanner, repo))
        return dict(command=command, status=observed["status"], completion="none", shape="",
                    result=observed["head"], binary="", rows=[], changes=changes,
                    value=dict(stage=observed["stage"], parent=observed.get("parent", ""),
                               id=observed["datum"], kind=int(observed["kind"]),
                               i64=int(observed["i64"])))

    def bundle_for(self, case):
        if case in self.large_bundles:
            return self.large_bundles[case][2]
        directory = self.destination.parent
        path = directory / "attempt.dmlb"
        exported = directory / "exported.dmlb"
        if case == "import_exported":
            if exported.exists():
                return exported
            path.write_bytes(b"")
        else:
            path.write_bytes(variant(case, self.frames))
        if case == "oversize_bundle":
            # Report the whole-input bound before parsing the duplicate frame.
            with path.open("r+b") as stream:
                stream.truncate(64 * 1024 * 1024 + 1)
        return path
