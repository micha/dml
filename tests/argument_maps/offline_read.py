"""Installed SAME-history nonexecuting reader; blockers active BEFORE helper load."""

import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys

TRANSPORT = ("http", "urllib", "requests", "httpx", "aiohttp", "boto3", "botocore", "docker", "daggerml.floci", "daggerml.ssh")


def blocked(name):
    if name in ("urllib", "urllib.parse"):
        return False  # Exact stdlib pure URI parsing, not transport.
    return any(name == prefix or name.startswith(prefix + ".") for prefix in TRANSPORT)


class NoTransport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname):
            raise RuntimeError("offline reader cannot import transport")


def no_spawn(event, args):
    if event in ("subprocess.Popen", "os.posix_spawn", "os.fork", "os.forkpty", "os.exec", "os.system", "socket.connect", "socket.bind", "socket.getaddrinfo"):
        raise RuntimeError("offline reader cannot spawn or connect")


def activate():
    if any(blocked(n) for n in sys.modules):
        raise RuntimeError("transport loaded before blockers")
    sys.meta_path.insert(0, NoTransport())
    sys.addaudithook(no_spawn)


def controls():
    import subprocess
    import socket
    rejected = []
    for label, action in (
        ("spawn", lambda: subprocess.Popen([sys.executable, "-c", "raise SystemExit(99)"])),
        ("http", lambda: __import__("http.client")),
        ("urllib-transport", lambda: __import__("urllib.request")),
        ("connect", lambda: socket.create_connection(("127.0.0.1", 1))),
    ):
        try:
            action()
        except RuntimeError:
            rejected.append(label)
        else:
            raise AssertionError("blocker did not reject " + label)
    return rejected


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] not in ("controls", "read"):
        raise ValueError("expected controls|read, story root, captured helper directory")
    mode, root, directory = args
    activate()
    if mode == "controls":
        result = dict(blockers=controls(), nonexecuting=True)
    else:
        directory = Path(directory)
        sys.path.insert(0, str(directory))
        spec = importlib.util.spec_from_file_location("same_recorded_map_story", directory / "installed_story.py")
        story = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(story)
        result = story.read(root)
        if any(blocked(n) for n in sys.modules):
            raise AssertionError("transport appeared during read")
        result["nonexecuting"] = True
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
