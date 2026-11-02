"""Blocker-FIRST fresh installed SAME-history reader; no arithmetic/source dispatch."""

import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys

TRANSPORT = ("http", "urllib", "requests", "httpx", "aiohttp", "boto3", "botocore", "docker", "daggerml.floci", "daggerml.ssh")


def blocked(name):
    if name in ("urllib", "urllib.parse"):
        return False  # Exact pure stdlib parser, NOT urllib.request transport.
    return any(name == p or name.startswith(p + ".") for p in TRANSPORT)


class NoTransport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname):
            raise RuntimeError("offline reader cannot import transport")


def audit(event, args):
    if event in ("subprocess.Popen", "os.posix_spawn", "os.fork", "os.forkpty", "os.exec", "os.system", "socket.connect", "socket.bind", "socket.getaddrinfo"):
        raise RuntimeError("offline reader cannot spawn or connect")


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
            raise AssertionError("blocker did not reject " + label)
    return dict(blockers=result, nonexecuting=True)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(root, directory):
    root, directory = Path(root).resolve(), Path(directory).resolve()
    stores = [root / n / "data.mdb" for n in ("caller.dml", "replica.dml")]
    before = {str(p): digest(p) for p in stores}
    receipt = json.loads((root / "receipt.json").read_bytes())
    prelaunch = json.loads((root / "prelaunch-source.json").read_bytes())
    if receipt["sources"] != prelaunch["sources"] or receipt["installed"] != prelaunch["installed"]:
        raise ValueError("incremental prelaunch/receipt provenance differs")
    if digest(sys.executable) != prelaunch["interpreter_sha256"] or sys.executable != prelaunch["interpreter"]:
        raise ValueError("actual interpreter differs")
    operational = root.parent / "launch-source"
    retired = operational.with_name("launch-source.unavailable")
    if (prelaunch["operational_source"] != str(operational) or operational.exists()
        or prelaunch["executing_controller"] != str(operational / "installed_story.py")
        or prelaunch["reader_source"] != str(operational / "offline_read.py")):
        raise ValueError("actual launch operational/controller/reader identity differs")
    for name, item in prelaunch["actual_helpers"].items():
        if item != dict(path=str(operational / name), sha256=receipt["sources"][name]) or digest(retired / name) != item["sha256"]:
            raise ValueError("ACTUALLY imported helper custody/hash differs")
    for name, expected in receipt["sources"].items():
        if digest(directory / name) != expected or digest(retired / name) != expected:
            raise ValueError("captured controller/helper/reader bytes differ BEFORE load")
    if digest(__file__) != receipt["sources"]["offline_read.py"]:
        raise ValueError("ACTUALLY executing reader differs")
    sys.path.insert(0, str(directory))
    spec = importlib.util.spec_from_file_location("same_closure_story", directory / "installed_story.py")
    story = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(story)
    for filename, module in (("installed_story.py", story), ("closure_calls.py", story.app),
        ("closure_runtime.py", story.rt), ("closure_funcs.py", story.funcs),
        ("reuse_selection.py", story.selection), ("explicit_reuse.py", story.explicit_reuse)):
        actual = Path(module.__file__).resolve()
        if actual != directory / filename or digest(actual) != receipt["sources"][filename]:
            raise ValueError("ACTUALLY imported helper path/hash differs")
    modules = {"daggerml": story.d, "builtin": story.b, "local": story.local,
               "exchange": story.ex, "transfer": story.transfer, "native": story.d._core}
    for name, module in modules.items():
        expected = receipt["installed"][name]
        actual = Path(module.__file__).resolve()
        if (not actual.is_relative_to(Path(sys.prefix).resolve())
            or actual != Path(expected["path"]).resolve() or digest(actual) != expected["sha256"]):
            raise ValueError("actual isolated installed runtime/native differs")
    cli = Path(story.d.__file__).parent / "_bin" / "dml"
    if str(cli) != receipt["installed"]["cli"]["path"] or digest(cli) != receipt["installed"]["cli"]["sha256"]:
        raise ValueError("actual installed native CLI differs")
    targets = {root / "caller.dml", root / "replica.dml"}
    opened = {}
    initialize, write = story.d.Repository.__init__, story.d.Repository.write
    def tracked_init(owner, path, **kwargs):
        initialize(owner, path, **kwargs)
        opened[id(owner)] = Path(path).resolve()
    def no_target_write(owner):
        if opened[id(owner)] in targets:
            raise RuntimeError("NONEXECUTING reader forbids target write transactions")
        return write(owner)
    def no_record(*args, **kwargs):
        raise RuntimeError("NONEXECUTING reader forbids recording/dispatch")
    story.d.Repository.__init__, story.d.Repository.write = tracked_init, no_target_write
    for module, names in ((story.b, ("record", "publish_callable")),
        (story.local, ("run_step", "run_request", "retry_step", "publish_result")),
        (story.ex, ("execute_exchange", "start_exchange", "record_exchange_request"))):
        for name in names:
            setattr(module, name, no_record)
    story.funcs.scaled_sum = story.rt.publish = no_record
    for name in ("call", "literal", "arguments", "returned"):
        setattr(story.b.Recorder, name, no_record)
    result = story.read(root)
    if any(blocked(n) for n in sys.modules):
        raise AssertionError("transport loaded during read")
    after = {str(p): digest(p) for p in stores}
    if before != after:
        raise AssertionError("immutable caller/replica bytes changed")
    result.update(nonexecuting=True, stores_before=before, stores_after=after, prelaunch_and_actual_runtime_verified=True)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] not in ("controls", "read"):
        raise ValueError("expected controls|read, story root, captured helper directory")
    activate()  # BEFORE every DML/helper import.
    print(json.dumps(controls() if args[0] == "controls" else read(args[1], args[2]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
