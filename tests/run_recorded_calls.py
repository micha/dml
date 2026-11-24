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
        self.directory = directory
        self.repos = {role: directory / role for role in ("source", "worker")}
        self.example = example
        self.sum_receipts = {}
        self.scale_receipts = {}
        self.plan_receipts = {}
        self.request_receipts = {}
        self.operations = {
            "record": self.record, "record_sum": self.record_sum, "record_scale": self.record_scale,
            "inspect": self.inspect, "export_sum": self.export_sum, "stage_input": self.stage_input,
            "release_input": self.release_input, "collect": self.collect,
            "export_scale": self.export_scale, "publish_scale": self.publish_scale,
            "request_scale": self.request_scale, "export_request": self.export_request,
            "work_scale": self.work_scale, "publish_requested_scale": self.publish_requested_scale,
            "abandon_scale_request": self.abandon_scale_request,
        }

    def invoke(self, op, args, *, operands=None, bundle=None):
        role, *cli_args = args
        repo = self.repos[role]
        data = repo / "data.mdb"
        before = data.read_bytes() if data.is_file() else None
        bundle_before = bundle.read_bytes() if bundle is not None and bundle.is_file() else None
        command = op.replace("_", "-")
        result = subprocess.run(
            [sys.executable, "-B", self.example, command, repo,
             *(cli_args if operands is None else operands)],
            cwd=self.directory, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        after = data.read_bytes() if data.is_file() else None
        bundle_after = bundle.read_bytes() if bundle is not None and bundle.is_file() else None
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        missing_ref = re.fullmatch(
            rf"{re.escape(command)}: \('not_found', -?[0-9]+, 'ref was not found'\)", result.stderr.rstrip("\n"),
        ) is not None
        return {"op": op, "args": list(args), "code": result.returncode, "quiet": not result.stderr,
                "diagnosed": result.stderr.startswith(f"{command}: ") and "Traceback" not in result.stderr,
                "missingRef": missing_ref,
                "commit": "", "calls": [], "expectedCommit": "", "producerCommit": "", "removed": -1,
                "expectedResult": "", "expectedMain": "", "requestCommit": "",
                "requestImplementation": "", "requestFactor": 0,
                "publication": {"planRef": "", "plan": "", "stagingRef": "", "result": ""},
                "unchanged": before is not None and before == after,
                "bundlePresent": bundle_after is not None, "bundleUnchanged": bundle_before == bundle_after}, result.stdout

    def write(self, op, args, **options):
        row, output = self.invoke(op, args, **options)
        return {**row, "commit": id_evidence(output.strip()) if output else ""}

    def record(self, *args):
        return self.write("record", args)

    def record_sum(self, role, pin, a, b):
        row = self.write("record_sum", (role, pin, a, b))
        if row["commit"]:
            self.sum_receipts[role, pin] = row["commit"]
        return row

    def select(self, op, role, pin, producer_receipt, *tail, bundle=None):
        # Only a record_sum receipt supplies the plan, never an import receipt.
        commit = self.sum_receipts["source", producer_receipt]
        operands = [pin, commit, *tail]
        if bundle is not None:
            operands[-1] = bundle
        row = self.write(op, (role, pin, producer_receipt, *tail), operands=operands, bundle=bundle)
        return {**row, "expectedCommit": commit}

    def record_scale(self, role, pin, producer_receipt, result_ref, factor):
        row = self.select("record_scale", role, pin, producer_receipt, result_ref, factor)
        if row["commit"]:
            self.scale_receipts[role, result_ref] = row["commit"]
        return row

    def export_sum(self, role, pin, producer_receipt, filename):
        return self.select("export_sum", role, pin, producer_receipt, filename, bundle=self.directory / filename)

    def stage_input(self, role, pin, filename):
        bundle = self.directory / filename
        return self.write("stage_input", (role, pin, filename), operands=(pin, bundle), bundle=bundle)

    def release_input(self, *args):
        return self.select("release_input", *args)

    def export_scale(self, role, pin, result_receipt, filename):
        commit = self.scale_receipts[role, result_receipt]
        bundle = self.directory / filename
        row = self.write("export_scale", (role, pin, result_receipt, filename),
                         operands=(pin, commit, bundle), bundle=bundle)
        return {**row, "expectedCommit": commit}

    def publish_scale(self, role, pin, result_receipt, producer_receipt, expected_factor, main_receipt):
        result = self.scale_receipts["worker", result_receipt]
        producer = self.sum_receipts["source", producer_receipt]
        main = "-" if main_receipt == "-" else self.scale_receipts["worker", main_receipt]
        row = self.write("publish_scale", (role, pin, result_receipt, producer_receipt, expected_factor, main_receipt),
                         operands=(pin, result, producer, expected_factor, main))
        return {**row, "expectedResult": result, "expectedCommit": producer, "expectedMain": main}

    def request_scale(self, role, pin, producer_receipt, plan, factor, receipt_alias=None):
        row = self.select("request_scale", role, pin, producer_receipt, plan, factor)
        if receipt_alias is not None:
            # The alias is only for replay; the CLI still writes the named pin.
            row["args"].append(receipt_alias)
        if row["commit"]:
            self.plan_receipts[plan if receipt_alias is None else receipt_alias] = row["commit"]
        return row

    def abandon_scale_request(self, role, pin, plan_receipt):
        plan = self.plan_receipts[plan_receipt]
        row = self.write("abandon_scale_request", (role, pin, plan_receipt), operands=(pin, plan))
        return {**row, "expectedCommit": plan}

    def export_request(self, role, pin, plan_receipt, filename):
        plan = self.plan_receipts[plan_receipt]
        bundle = self.directory / filename
        row = self.write("export_request", (role, pin, plan_receipt, filename),
                         operands=(pin, plan, bundle), bundle=bundle)
        if row["commit"]:
            self.request_receipts[plan_receipt] = row["commit"]
        return {**row, "expectedCommit": plan}

    def work_scale(self, role, pin, request_receipt, result_ref):
        request = self.request_receipts[request_receipt]
        row = self.write("work_scale", (role, pin, request_receipt, result_ref),
                         operands=(pin, request, result_ref))
        if row["commit"]:
            self.scale_receipts[role, result_ref] = row["commit"]
        return {**row, "expectedCommit": request}

    def publish_requested_scale(self, role, pin, plan_receipt, returned, result_receipt, receipt_ref=None):
        plan = self.plan_receipts[plan_receipt]
        result = self.scale_receipts["worker", result_receipt]
        args = (role, pin, plan_receipt, returned, result_receipt)
        operands = (pin, plan, returned, result)
        if receipt_ref is not None:
            args += (receipt_ref,)
            operands += ("--receipt-ref", receipt_ref)
        row = self.write("publish_requested_scale", args, operands=operands)
        return {**row, "expectedCommit": plan, "expectedResult": result}

    def collect(self, role):
        row, output = self.invoke("collect", (role,))
        return {**row, "removed": int(output) if output else -1}

    def inspect(self, *args):
        row, output = self.invoke("inspect", args)
        if output:
            report = json.loads(output)
            row["commit"] = id_evidence(report["commit"])
            if "calls" in report:
                row["calls"] = [call_evidence(call) for call in report["calls"]]
            if "plan_commit" in report:
                row["publication"] = {"planRef": report["plan_ref"], "plan": id_evidence(report["plan_commit"]),
                                      "stagingRef": report["staging_ref"], "result": id_evidence(report["result_commit"])}
            if "producer_commit" in report:
                row["producerCommit"] = id_evidence(report["producer_commit"])
            if "request_commit" in report:
                row["requestCommit"] = id_evidence(report["request_commit"])
            if "request_implementation" in report:
                row["requestImplementation"] = report["request_implementation"]
                row["requestFactor"] = report["request_factor"]
            if "expected_main" in report:
                main = report["expected_main"]
                row["expectedMain"] = "-" if main is None else id_evidence(main)
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
