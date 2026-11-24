"""Collect observations from the recorded-calls example for Quint."""

import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from run_histories import (
    absolute_path,
    add_quint_arguments,
    check_verdicts,
    evaluate,
    quint_command,
    read_histories,
    replay_history,
)


def id_evidence(value):
    if not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValueError(f"expected a lowercase hexadecimal object ID, got {value!r}")
    return value


def call_evidence(call):
    return {
        "dag": id_evidence(call["dag"]),
        "implementation": call["implementation"],
        "resultNode": id_evidence(call["result"]["node"]),
        "resultValue": call["result"]["value"],
        "arguments": [
            {"name": name, "node": id_evidence(arg["node"]), "value": arg["value"],
             "producer": id_evidence(arg["call"]) if "call" in arg else ""}
            for name, arg in sorted(call["arguments"].items())
        ],
    }


class ProcessHistory:
    def __init__(self, directory, example):
        self.repo = directory / "calls"
        self.example = example
        self.receipts = {}
        self.operations = {"record": self.record, "record_sum": self.record_sum,
                           "record_scale": self.record_scale, "inspect": self.inspect}

    def invoke(self, op, args, *, operands=None):
        data = self.repo / "data.mdb"
        before = data.read_bytes() if data.is_file() else None
        result = subprocess.run(
            [sys.executable, "-B", self.example, op.replace("_", "-"), self.repo,
             *(args if operands is None else operands)],
            cwd=self.repo.parent, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        after = data.read_bytes() if data.is_file() else None
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        return {"op": op, "args": list(args), "code": result.returncode, "quiet": not result.stderr,
                "commit": "", "calls": [], "expectedCommit": "", "producerCommit": "",
                "unchanged": before is not None and before == after}, result.stdout

    def write(self, op, args, *, operands=None):
        row, output = self.invoke(op, args, operands=operands)
        return {**row, "commit": id_evidence(output.strip()) if output else ""}

    def record(self, *args):
        return self.write("record", args)

    def record_sum(self, pin, a, b):
        row = self.write("record_sum", (pin, a, b))
        self.receipts[pin] = row["commit"]
        return row

    def record_scale(self, pin, producer_receipt, result, factor):
        commit = self.receipts[producer_receipt]
        row = self.write("record_scale", (pin, producer_receipt, result, factor),
                         operands=(pin, commit, result, factor))
        return {**row, "expectedCommit": commit}

    def inspect(self, *args):
        row, output = self.invoke("inspect", args)
        if output:
            report = json.loads(output)
            row["commit"] = id_evidence(report["commit"])
            row["calls"] = [call_evidence(call) for call in report["calls"]]
            if "producer_commit" in report:
                row["producerCommit"] = id_evidence(report["producer_commit"])
        return row


class Processes:
    def __init__(self, example):
        self.example = example

    def history(self, directory):
        return nullcontext(ProcessHistory(directory, self.example))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("example", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-recorded-calls-") as tmp:
        directory = Path(tmp)
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        suite = Processes(args.example)
        observations = [
            {**replay_history(suite, directory / f"history-{index}", requests), "scenario": index}
            for index, requests in enumerate(histories)
        ]
        state = evaluate(quint, args.rules, directory, observations, [args.histories])
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"recorded-calls interpretation failed: {error}") from error
