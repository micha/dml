"""Blocker-FIRST fresh installed SAME-history reader; no source exec/record/dispatch."""

import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

TRANSPORT = ("http", "urllib", "requests", "httpx", "aiohttp", "boto3", "botocore", "docker", "daggerml.floci", "daggerml.ssh")


def blocked(name):
    if name in ("urllib", "urllib.parse"):
        return False
    return any(name == prefix or name.startswith(prefix + ".") for prefix in TRANSPORT)


class NoTransport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname):
            raise RuntimeError("reader forbids transport imports")


def audit(event, args):
    if event in ("subprocess.Popen", "os.posix_spawn", "os.fork", "os.forkpty", "os.exec", "os.system", "socket.connect", "socket.bind", "socket.getaddrinfo"):
        raise RuntimeError("reader forbids spawn/connect")


def activate():
    if any(blocked(n) for n in sys.modules):
        raise RuntimeError("transport loaded before blockers")
    sys.meta_path.insert(0, NoTransport())
    sys.addaudithook(audit)


def controls():
    import socket
    import subprocess
    result = []
    for label, action in (("spawn", lambda: subprocess.Popen([sys.executable, "-c", "raise SystemExit(99)"])),
        ("http", lambda: __import__("http.client")), ("urllib-transport", lambda: __import__("urllib.request")),
        ("connect", lambda: socket.create_connection(("127.0.0.1", 1)))):
        try:
            action()
        except RuntimeError:
            result.append(label)
        else:
            raise AssertionError("reader blocker missed " + label)
    return dict(blockers=result, blocker_first=True, nonexecuting=True)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guards(story, targets):
    opened = {}
    initialize, write = story.d.Repository.__init__, story.d.Repository.write
    def track(owner, path, **options):
        initialize(owner, path, **options)
        opened[id(owner)] = Path(path).resolve()
    def forbid_target_write(owner):
        if opened[id(owner)] in targets:
            raise RuntimeError("reader forbids target write transactions")
        return write(owner)
    def forbidden(*args, **kwargs):
        raise RuntimeError("reader forbids recording/dispatch/logical execution")
    story.d.Repository.__init__, story.d.Repository.write = track, forbid_target_write
    for module, names in ((story.b, ("record", "publish_callable")),
        (story.local, ("run_step", "run_request", "retry_step", "publish_result", "child_context")),
        (story.ex, ("execute_exchange", "start_exchange", "record_exchange_request")),
        (story.p, ("initialize", "record_request", "select_outer", "promote_defaults", "prepare_arguments"))):
        for name in names:
            setattr(module, name, forbidden)
    story.adapter.execute = story.logical.double_sum = story.leaf.publish = forbidden
    story.funcs.add = story.funcs.double = forbidden
    story.bridge.Session.__init__ = forbidden
    story.b.Recorder.__init__ = forbidden
    return forbidden


def author_controls(directory):
    directory = Path(directory).resolve()
    sys.path.insert(0, str(directory))
    spec = importlib.util.spec_from_file_location("controlled_captured_story", directory / "installed_story.py")
    story = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(story)
    story.identities()
    story.helper_identities(directory)
    result = []
    with tempfile.TemporaryDirectory(prefix="dml-captured-reader-controls-") as scratch:
        target = Path(scratch) / "sentinel.dml"
        with story.d.Repository(target, create=True):
            pass  # Metadata-only empty self-owned sentinel, zero Q/T.
        before = digest(target / "data.mdb")
        guards(story, {target})
        with story.d.Repository(target) as repo:
            probes = (("target-write", repo.write), ("record", lambda: story.b.record(None, "forbidden")),
                ("dispatch", lambda: story.adapter.execute(None, None)),
                ("logical", lambda: story.logical.double_sum(None, None, None, None)),
                ("recorder", lambda: story.b.Recorder(None, commit=None)))
            for label, action in probes:
                try:
                    action()
                except RuntimeError:
                    result.append(label)
                else:
                    raise AssertionError("reader author blocker missed " + label)
        if digest(target / "data.mdb") != before:
            raise AssertionError("reader controls changed sentinel data")
    return result


def read(root, directory):
    root, directory = Path(root).resolve(), Path(directory).resolve()
    stores = [root / n / "data.mdb" for n in ("caller.dml", "replica.dml")]
    before = {str(p): digest(p) for p in stores}
    receipt = json.loads((root / "receipt.json").read_bytes())
    original = json.loads((root / "prelaunch-source.json").read_bytes())
    operational = root.parent / "launch-source"
    retired = operational.with_name("launch-source.unavailable")
    if (operational.exists() or original["operational_source"] != str(operational)
        or original["controller"] != str(operational / "installed_story.py")
        or receipt["sources"] != original["sources"] or receipt["installed"] != original["installed"]):
        raise ValueError("prelaunch/original/current source custody differs")
    if digest(sys.executable) != receipt["interpreter_sha256"] or sys.executable != receipt["interpreter"]:
        raise ValueError("actual reader interpreter differs")
    for filename, expected in receipt["sources"].items():
        if digest(directory / filename) != expected or digest(retired / filename) != expected:
            raise ValueError("captured/current/retired source identity differs BEFORE imports")
    if digest(__file__) != receipt["sources"]["offline_read.py"]:
        raise ValueError("actually executing reader identity differs")
    sys.path.insert(0, str(directory))
    spec = importlib.util.spec_from_file_location("same_captured_call_story", directory / "installed_story.py")
    story = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(story)
    helpers = story.helper_identities(directory)
    for filename, actual in helpers.items():
        if actual["sha256"] != receipt["sources"][filename] or original["helpers"][filename] != dict(
            path=str(operational / filename), sha256=actual["sha256"]):
            raise ValueError("ACTUALLY imported helper path/hash differs")
    if story.identities() != receipt["installed"]:
        raise ValueError("ACTUALLY installed runtime/native/CLI differs")
    targets = {root / "caller.dml", root / "replica.dml"}
    guards(story, targets)
    result = story.read(root)
    if any(blocked(n) for n in sys.modules):
        raise AssertionError("transport loaded while reading")
    custody = json.loads((root / "custody.json").read_bytes())
    if (custody["direct"] != 5 or len(custody["children"]) != 5
        or any(row["waits"] != [dict(returned=True, exit=0)] or row.get("absent") is not True for row in custody["children"])):
        raise ValueError("actual known reaping/absent direct-child receipts differ")
    if digest(root / "full-history.bundle") != receipt["bundle_sha256"]:
        raise ValueError("SAME immutable complete packet differs")
    after = {str(p): digest(p) for p in stores}
    if before != after:
        raise AssertionError("reader mutated target native stores")
    return dict(results=result, before=before, after=after, nonexecuting=True, actual_source_runtime_custody_verified=True)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] not in ("controls", "read"):
        raise ValueError("expected controls|read ROOT SOURCE_DIRECTORY")
    activate()  # BEFORE DML/helper import.
    if args[0] == "controls":
        result = controls()
        result["author_blockers"] = author_controls(args[2])
    else:
        result = read(args[1], args[2])
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
