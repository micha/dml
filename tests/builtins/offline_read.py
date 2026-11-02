"""Blocker-FIRST fresh installed SAME-history reader; no original operational paths."""

import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys

TRANSPORT = ("http", "urllib", "requests", "httpx", "aiohttp", "boto3", "botocore", "docker", "daggerml.floci", "daggerml.ssh")


def blocked(name):
    if name in ("urllib", "urllib.parse"):
        return False  # Exact pure stdlib parsing only, not urllib.request transport.
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
                          ("http", lambda: __import__("http.client")),
                          ("urllib-transport", lambda: __import__("urllib.request")),
                          ("connect", lambda: socket.create_connection(("127.0.0.1", 1)))):
        try:
            action()
        except RuntimeError:
            result.append(label)
        else:
            raise AssertionError("blocker did not reject " + label)
    return dict(blockers=result, nonexecuting=True)


def final_artifacts(manifest_path):
    """Explicit two-runtime provenance; NEVER discard old receipt/hash authority."""
    final = json.loads(Path(manifest_path).read_bytes())
    original = json.loads(Path(final["original_manifest"]).read_bytes())
    if (final["allowed_changed_python"] != ["builtin.py"]
        or set(final["artifacts"]) != set(original["artifacts"])
        or Path(final["prefix"]).resolve() != Path(sys.prefix).resolve()):
        raise ValueError("final manifest inventory/prefix/change scope differs")
    for name, old in original["artifacts"].items():
        actual_old = Path(old["installed"]).resolve()
        if not str(actual_old).startswith(final["original_prefix"] + "/") or hashlib.sha256(actual_old.read_bytes()).hexdigest() != old["sha256"]:
            raise ValueError("ORIGINAL installed artifact hash differs")
        current = final["artifacts"][name]
        actual_final = Path(current["installed"]).resolve()
        if not str(actual_final).startswith(final["prefix"] + "/") or hashlib.sha256(actual_final.read_bytes()).hexdigest() != current["sha256"]:
            raise ValueError("FINAL installed artifact hash differs")
        if name != "builtin.py" and current["sha256"] != old["sha256"]:
            raise ValueError("non-builtin runtime/native/CLI changed")
    return final


def read(root, directory, *, final_manifest=None):
    # No DML/helper import precedes activate() in main.
    root, directory = Path(root), Path(directory)
    stores = [root / name / "data.mdb" for name in ("caller.dml", "replica.dml")]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in stores}
    receipt = json.loads((root / "receipt.json").read_bytes())
    for name, expected in receipt["sources"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError("captured controller/helper bytes differ before load")
    sys.path.insert(0, str(directory))
    spec = importlib.util.spec_from_file_location("same_builtin_story", directory / "installed_story.py")
    story = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(story)
    imported_helpers = {"installed_story.py": story,
                        "builtin_workflow.py": sys.modules["builtin_workflow"],
                        "reuse_selection.py": sys.modules["reuse_selection"],
                        "explicit_reuse.py": sys.modules["explicit_reuse"]}
    for filename, module in imported_helpers.items():
        actual = Path(module.__file__).resolve()
        if actual != (directory / filename).resolve() or hashlib.sha256(actual.read_bytes()).hexdigest() != receipt["sources"][filename]:
            raise ValueError("actually imported helper path/bytes differ")
    modules = {"daggerml": story.d, "builtin": story.b, "local": story.local,
               "exchange": story.ex, "transfer": story.transfer, "native": story.d._core}
    final = None if final_manifest is None else final_artifacts(final_manifest)
    for name, module in modules.items():
        got = receipt["installed"][name]
        actual = Path(module.__file__).resolve()
        # Original receipt checks are retained EVEN when current builtin intentionally differs.
        original_file = Path(got["path"]).resolve()
        if hashlib.sha256(original_file.read_bytes()).hexdigest() != got["sha256"]:
            raise ValueError("ORIGINAL receipt runtime/native hash differs")
        current = got if final is None else final["artifacts"][module.__file__.split("/")[-1] if name != "native" else "native"]
        if (not str(actual).startswith(str(Path(sys.prefix).resolve()) + "/")
            or actual != Path(current.get("installed", current.get("path"))).resolve()
            or hashlib.sha256(actual.read_bytes()).hexdigest() != current["sha256"]):
            raise ValueError("installed source/native provenance differs")
    cli = Path(story.d.__file__).parent / "_bin" / "dml"
    old_cli = receipt["installed"]["cli"]
    if hashlib.sha256(Path(old_cli["path"]).read_bytes()).hexdigest() != old_cli["sha256"]:
        raise ValueError("ORIGINAL receipt CLI provenance differs")
    if hashlib.sha256(cli.read_bytes()).hexdigest() != old_cli["sha256"]:
        raise ValueError("installed native CLI provenance differs")
    result = story.read(root)
    if any(blocked(n) for n in sys.modules):
        raise AssertionError("transport loaded during read")
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in stores}
    if before != after:
        raise AssertionError("immutable caller/replica data bytes changed")
    result.update(nonexecuting=True, stores_before=before, stores_after=after,
                  original_runtime_verified=True, final_manifest=None if final is None else str(final_manifest))
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if (len(args) not in (3, 5) or args[0] not in ("controls", "read")
        or len(args) == 5 and (args[0] != "read" or args[3] != "--final-manifest")):
        raise ValueError("expected controls|read, story root, helpers, optional --final-manifest path")
    activate()
    result = controls() if args[0] == "controls" else read(args[1], args[2], final_manifest=None if len(args) == 3 else args[4])
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
