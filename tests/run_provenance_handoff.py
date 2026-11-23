"""Collect process and filesystem evidence for the Quint handoff workflow spec."""

import argparse
from contextlib import nullcontext
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from run_histories import check_verdicts, evaluate, read_histories, replay_history


def file_bytes(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


class ProcessHistory:
    def __init__(self, directory, example, fixture):
        self.directory = directory
        self.example = example
        self.fixture = fixture
        self.saved = {}
        self.operations = {
            "handoff": lambda *args: self.invoke(example, "handoff", args, args),
            "fixture": self.probe,
            "write_file": self.write_file,
            "remove_file": self.remove_file,
            "read_file": self.read_file,
        }

    def path(self, token):
        if not token.startswith("@") or Path(token[1:]).name != token[1:] or token[1:] in ("", ".", ".."):
            raise ValueError(f"expected a workspace path token, got {token!r}")
        return self.directory / token[1:]

    @staticmethod
    def evidence(op, args, code=0, stdout=None, stderr=None, storage="unobserved", existed=False):
        return {"op": op, "args": list(args), "code": code, "stdout": stdout or [],
                "stderr": stderr or [], "storage": storage, "existed": existed}

    def probe(self, *request):
        # Named fixture output slots let later fixture calls pass exact IDs.
        # The handoff executable receives no IDs through this bridge.
        separator = request.index("--capture")
        actual, captures = request[:separator], request[separator + 1:]
        if "$" in actual:
            index = actual.index("$")
            actual = (*actual[:index], self.saved[actual[index + 1]], *actual[index + 2:])
        evidence = self.invoke(self.fixture, "fixture", request, actual)
        for name, value in zip(captures, (value for row in evidence["stdout"] for value in row)):
            if name:
                self.saved[name] = value
        return evidence

    def invoke(self, executable, op, request, args):
        paths = {arg: self.path(arg) for arg in args if arg.startswith("@")}
        inspect = op == "handoff" and args[0] == "inspect"
        repo = paths[args[2]] if inspect else None
        before = (repo.exists(), file_bytes(repo / "data.mdb")) if inspect else None
        result = subprocess.run([executable, *(paths.get(arg, arg) for arg in args)],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        after = (repo.exists(), file_bytes(repo / "data.mdb")) if inspect else None
        error = result.stderr
        # Normalize workspace paths (e.g. from perror), not the diagnostic text.
        for token, path in sorted(paths.items(), key=lambda item: len(str(item[1])), reverse=True):
            error = error.replace(str(path), token)
        # Keep every report line, including duplicates and malformed lines.
        stdout = [line.split(": ", 1) if inspect else line.split() for line in result.stdout.splitlines()]
        stderr = []
        for line in error.splitlines():
            pieces = line.split(": ", 1)
            detail = re.fullmatch(r"\S+ \((.*)\)", pieces[-1]) if len(pieces) == 2 else None
            stderr.append([*pieces, detail[1]] if detail else pieces)
        storage = "unobserved" if not inspect else "unchanged" if before == after else "changed"
        return self.evidence(op, request, result.returncode, stdout, stderr, storage, bool(before and before[0]))

    def write_file(self, path, text):
        self.path(path).write_bytes(text.encode("ascii"))
        return self.evidence("write_file", [path, text])

    def remove_file(self, path):
        self.path(path).unlink()
        return self.evidence("remove_file", [path])

    def read_file(self, path):
        data = file_bytes(self.path(path))
        value = ["missing"] if data is None else ["present", data.hex()]
        return self.evidence("read_file", [path], stdout=[value])


class Processes:
    def __init__(self, example, fixture):
        self.example = example
        self.fixture = fixture

    def history(self, directory):
        return nullcontext(ProcessHistory(directory, self.example, self.fixture))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("quint", "example", "fixture", "histories", "rules"):
        parser.add_argument(name, type=lambda path: Path(path).absolute())
    args = parser.parse_args()
    with TemporaryDirectory(prefix="dml-handoff-") as tmp:
        directory = Path(tmp)
        histories = read_histories(args.quint, args.histories, directory / "histories.itf.json", ["init"])
        suite = Processes(args.example, args.fixture)
        observations = [
            {**replay_history(suite, directory / f"history-{index}", requests), "scenario": index}
            for index, requests in enumerate(histories)
        ]
        state = evaluate(args.quint, args.rules, directory, observations, [args.histories])
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"handoff interpretation failed: {error}") from error
