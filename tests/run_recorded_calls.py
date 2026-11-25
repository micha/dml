"""Collect observations from the recorded-calls example for Quint."""

import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from daggerml import core

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


def evidence(op, args, *, code, stderr, unchanged, bundle_present=False, bundle_unchanged=True):
    command = op.replace("_", "-")
    missing_ref = re.fullmatch(
        rf"{re.escape(command)}: \('not_found', -?[0-9]+, 'ref was not found'\)", stderr.rstrip("\n"),
    ) is not None
    return {"op": op, "args": list(args), "code": code, "quiet": not stderr,
            "diagnosed": stderr.startswith(f"{command}: ") and "Traceback" not in stderr,
            "missingRef": missing_ref,
            "commit": "", "calls": [], "expectedCommit": "", "producerCommit": "", "removed": -1,
            "expectedResult": "", "expectedSelection": "", "expectedAttempt": "", "expectedMain": "",
            "previousSelection": "", "requestCommit": "", "requestImplementation": "", "requestFactor": 0,
            "publication": {"planRef": "", "plan": "", "stagingRef": "", "result": ""},
            "reusePublication": {"mode": "", "planRef": "", "plan": "", "resultRef": "", "result": ""},
            "selection": {"resultRef": "", "result": ""},
            "selectedPublication": {"mode": "", "planRef": "", "plan": "", "selectionRef": "",
                                    "selection": "", "result": ""},
            "occurrence": {"id": "", "commit": "", "result": "", "historicalRef": ""},
            "policy": {"defaultMode": "", "previous": ""}, "expectedPolicy": "",
            "intent": {"implementation": "", "defaultMode": "", "v1Selection": "", "v2Selection": "", "previous": ""},
            "expectedIntent": "",
            "decision": {"id": "", "canonicalId": False, "policy": "", "intent": "", "defaultMode": "", "override": "",
                         "route": "", "reason": "", "plan": "", "planRef": "", "selectionRef": "", "selection": "",
                         "result": "", "implementationOverride": "", "implementationReason": ""},
            "unchanged": unchanged, "bundlePresent": bundle_present, "bundleUnchanged": bundle_unchanged}


class ProcessHistory:
    def __init__(self, directory, example):
        self.directory = directory
        self.repos = {role: directory / role for role in ("source", "worker")}
        self.example = example
        self.sum_receipts = {}
        self.scale_receipts = {}
        self.plan_receipts = {}
        self.request_receipts = {}
        self.selection_receipts = {}
        self.attempt_receipts = {}
        self.policy_receipts = {}
        self.intent_receipts = {}
        self.operations = {
            "record": self.record, "record_sum": self.record_sum, "record_scale": self.record_scale,
            "inspect": self.inspect, "export_sum": self.export_sum, "stage_input": self.stage_input,
            "release_input": self.release_input, "collect": self.collect,
            "export_scale": self.export_scale, "publish_scale": self.publish_scale,
            "request_scale": self.request_scale, "export_request": self.export_request,
            "work_scale": self.work_scale, "publish_requested_scale": self.publish_requested_scale,
            "abandon_scale_request": self.abandon_scale_request, "stage_reused_scale": self.stage_reused_scale,
            "publish_reused_scale": self.publish_reused_scale, "select_scale_result": self.select_scale_result,
            "publish_selected_scale": self.publish_selected_scale, "work_scale_attempt": self.work_scale_attempt,
            "export_scale_attempt": self.export_scale_attempt, "select_scale_attempt": self.select_scale_attempt,
            "adopt_scale_attempt": self.adopt_scale_attempt, "drop_ref": self.drop_ref,
            "define_scale_policy": self.define_scale_policy, "request_policy_scale": self.request_policy_scale,
            "define_scale_intent": self.define_scale_intent, "request_intent_scale": self.request_intent_scale,
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
        row = evidence(op, args, code=result.returncode, stderr=result.stderr,
                       unchanged=before is not None and before == after,
                       bundle_present=bundle_after is not None, bundle_unchanged=bundle_before == bundle_after)
        return row, result.stdout

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

    def request_scale(self, role, pin, producer_receipt, plan, factor, *tail):
        # A lone extra operand aliases the receipt only in replay. Pass the
        # two-token implementation option through to the actual CLI instead.
        alias, options = (tail[0], ()) if len(tail) == 1 else (plan, tail)
        row = self.select("request_scale", role, pin, producer_receipt, plan, factor, *options)
        if len(tail) == 1:
            row["args"].append(alias)
        if row["commit"]:
            self.plan_receipts[alias] = row["commit"]
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

    def work_scale_attempt(self, role, pin, request_receipt, attempt_ref, occurrence_id):
        request = self.request_receipts[request_receipt]
        args = (role, pin, request_receipt, attempt_ref, occurrence_id)
        row = self.write("work_scale_attempt", args, operands=(pin, request, attempt_ref, occurrence_id))
        if row["commit"]:
            self.attempt_receipts[attempt_ref] = row["commit"]
        return {**row, "expectedCommit": request}

    def export_scale_attempt(self, role, pin, attempt_receipt, filename):
        commit = self.attempt_receipts[attempt_receipt]
        bundle = self.directory / filename
        row = self.write("export_scale_attempt", (role, pin, attempt_receipt, filename),
                         operands=(pin, commit, bundle), bundle=bundle)
        return {**row, "expectedCommit": commit}

    def select_scale_attempt(self, role, plan_pin, plan_receipt, attempt_pin, attempt_receipt, selection_ref, alias=None):
        plan = self.plan_receipts[plan_receipt]
        attempt = self.attempt_receipts[attempt_receipt]
        args = (role, plan_pin, plan_receipt, attempt_pin, attempt_receipt, selection_ref)
        if alias is not None:
            args += (alias,)
        row = self.write("select_scale_attempt", args, operands=(plan_pin, plan, attempt_pin, attempt, selection_ref))
        if row["commit"]:
            self.selection_receipts[alias if alias is not None else selection_ref] = row["commit"]
        return {**row, "expectedCommit": plan, "expectedAttempt": attempt}

    def adopt_scale_attempt(self, role, basis_ref, basis_receipt, attempt_ref, attempt_receipt, selection_ref):
        basis = self.selection_receipts[basis_receipt]
        attempt = self.attempt_receipts[attempt_receipt]
        args = (role, basis_ref, basis_receipt, attempt_ref, attempt_receipt, selection_ref)
        row = self.write("adopt_scale_attempt", args, operands=(basis_ref, basis, attempt_ref, attempt, selection_ref))
        if row["commit"]:
            self.selection_receipts[selection_ref] = row["commit"]
        return {**row, "expectedCommit": basis, "expectedAttempt": attempt}

    def define_scale_policy(self, role, policy_ref, default, *basis):
        expected = ""
        operands = [policy_ref, default]
        if basis:
            basis_ref, receipt = basis
            expected = self.policy_receipts[receipt]
            operands.extend(("--basis-ref", basis_ref, "--basis-commit", expected))
        row = self.write("define_scale_policy", (role, policy_ref, default, *basis), operands=operands)
        if row["commit"]:
            self.policy_receipts[policy_ref] = row["commit"]
        return {**row, "expectedCommit": expected}

    def request_policy_scale(self, role, producer_ref, producer_receipt, policy_ref, policy_receipt,
                             plan_ref, decision_ref, factor, override, *selection):
        producer = self.sum_receipts["source", producer_receipt]
        policy = self.policy_receipts[policy_receipt]
        args = (role, producer_ref, producer_receipt, policy_ref, policy_receipt, plan_ref, decision_ref,
                factor, override, *selection)
        operands = [producer_ref, producer, policy_ref, policy, plan_ref, decision_ref, factor,
                    "--implementation", "example.scale@2"]
        if override != "default":
            operands.extend(("--override", override))
        expected_selection = ""
        if selection:
            operands.extend(("--selection", selection[0]))
            if len(selection) == 2:
                expected_selection = self.selection_receipts[selection[1]]
                operands.extend(("--selection-commit", expected_selection))
        row = self.write("request_policy_scale", args, operands=operands)
        return {**row, "expectedCommit": producer, "expectedPolicy": policy, "expectedSelection": expected_selection}

    def define_scale_intent(self, role, intent_ref, implementation, *definition):
        expected = ""
        operands = [intent_ref, implementation]
        if len(definition) == 2:
            basis_ref, receipt = definition
            expected = self.intent_receipts[receipt]
            operands.extend(("--basis-ref", basis_ref, "--basis-commit", expected))
        else:
            reuse, v1_slot, v2_slot = definition
            operands.extend(("--reuse-default", reuse, "--v1-selection", v1_slot, "--v2-selection", v2_slot))
        row = self.write("define_scale_intent", (role, intent_ref, implementation, *definition), operands=operands)
        if row["commit"]:
            self.intent_receipts[intent_ref] = row["commit"]
        return {**row, "expectedCommit": expected}

    def request_intent_scale(self, role, producer_ref, producer_receipt, intent_ref, intent_receipt,
                             plan_ref, decision_ref, factor, implementation, override, selection):
        producer = self.sum_receipts["source", producer_receipt]
        intent = self.intent_receipts[intent_receipt]
        args = (role, producer_ref, producer_receipt, intent_ref, intent_receipt, plan_ref, decision_ref,
                factor, implementation, override, selection)
        operands = [producer_ref, producer, intent_ref, intent, plan_ref, decision_ref, factor]
        if implementation != "default":
            operands.extend(("--implementation", implementation))
        if override != "default":
            operands.extend(("--override", override))
        expected_selection = "" if selection == "-" else self.selection_receipts[selection]
        if expected_selection:
            operands.extend(("--selection-commit", expected_selection))
        row = self.write("request_intent_scale", args, operands=operands)
        return {**row, "expectedCommit": producer, "expectedIntent": intent, "expectedSelection": expected_selection}

    def drop_ref(self, role, pin, kind, receipt):
        # Fixture only: simulate a separate ref owner without adding a CLI command.
        receipts = {"attempt": self.attempt_receipts, "selection": self.selection_receipts,
                    "policy": self.policy_receipts, "intent": self.intent_receipts}
        expected = receipts[kind][receipt]
        path = self.repos[role]
        data = path / "data.mdb"
        before = data.read_bytes()
        repo = core.repo_open(path, False)
        try:
            txn = core.txn_begin(repo, core.TXN_WRITE)
            try:
                core.txn_ref_delete_expected(txn, pin.encode("ascii"), bytes.fromhex(expected))
                core.txn_commit(txn)
            finally:
                core.txn_abort(txn)
        finally:
            core.repo_close(repo)
        row = evidence("drop_ref", (role, pin, kind, receipt), code=0, stderr="",
                       unchanged=before == data.read_bytes())
        return {**row, "expectedCommit": expected}

    def select_reuse(self, op, role, plan_pin, plan_receipt, result_pin, result_receipt, output):
        plan = self.plan_receipts[plan_receipt]
        # The original worker result, never the local staging receipt.
        result = self.scale_receipts["worker", result_receipt]
        row = self.write(op, (role, plan_pin, plan_receipt, result_pin, result_receipt, output),
                         operands=(plan_pin, plan, result_pin, result, output))
        return {**row, "expectedCommit": plan, "expectedResult": result}

    def stage_reused_scale(self, *args):
        return self.select_reuse("stage_reused_scale", *args)

    def publish_reused_scale(self, *args):
        return self.select_reuse("publish_reused_scale", *args)

    def select_scale_result(self, role, plan_pin, plan_receipt, result_pin, result_receipt, selection_ref):
        row = self.select_reuse("select_scale_result", role, plan_pin, plan_receipt, result_pin, result_receipt,
                                selection_ref)
        if row["commit"]:
            self.selection_receipts[selection_ref] = row["commit"]
        return row

    def publish_selected_scale(self, role, plan_pin, plan_receipt, selection_ref, selection_receipt, reuse_ref):
        plan = self.plan_receipts[plan_receipt]
        selection = self.selection_receipts[selection_receipt]
        args = (role, plan_pin, plan_receipt, selection_ref, selection_receipt, reuse_ref)
        row = self.write("publish_selected_scale", args,
                         operands=(plan_pin, plan, selection_ref, selection, reuse_ref))
        return {**row, "expectedCommit": plan, "expectedSelection": selection}

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
            if "decision_id" in report:
                decision_id = report["decision_id"]
                canonical_id = re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                                            decision_id) is not None
                row["decision"] = {
                    "id": decision_id, "canonicalId": canonical_id,
                    "policy": id_evidence(report["policy_commit"]) if "policy_commit" in report else "",
                    "intent": id_evidence(report["intent_commit"]) if "intent_commit" in report else "",
                    "defaultMode": report["policy_default"], "override": report["override"],
                    "route": report["action"], "reason": report["reason"], "plan": id_evidence(report["plan_commit"]),
                    "planRef": report.get("plan_ref", ""), "selectionRef": report.get("selection_ref", ""),
                    "selection": id_evidence(report["selection_commit"]) if "selection_commit" in report else "",
                    "result": id_evidence(report["result_commit"]) if "result_commit" in report else "",
                    "implementationOverride": report.get("implementation_override", ""),
                    "implementationReason": report.get("implementation_reason", ""),
                }
                if "plan_ref" in report:
                    self.plan_receipts[report["plan_ref"]] = row["decision"]["plan"]
            elif "default_implementation" in report:
                previous = report["previous_intent_commit"]
                row["intent"] = {"implementation": report["default_implementation"],
                                 "defaultMode": report["policy_default"], "v1Selection": report["v1_selection_ref"],
                                 "v2Selection": report["v2_selection_ref"],
                                 "previous": "" if previous is None else id_evidence(previous)}
            elif "policy_default" in report:
                row["policy"] = {"defaultMode": report["policy_default"], "previous":
                                 id_evidence(report["previous_policy_commit"]) if "previous_policy_commit" in report else ""}
            elif "selection_commit" in report:
                row["selectedPublication"] = {
                    "mode": report["publication_mode"], "planRef": report["plan_ref"],
                    "plan": id_evidence(report["plan_commit"]), "selectionRef": report["selection_ref"],
                    "selection": id_evidence(report["selection_commit"]), "result": id_evidence(report["result_commit"]),
                }
            elif "publication_mode" in report:
                row["reusePublication"] = {
                    "mode": report["publication_mode"], "planRef": report["plan_ref"],
                    "plan": id_evidence(report["plan_commit"]), "resultRef": report["result_ref"],
                    "result": id_evidence(report["result_commit"]),
                }
            elif "plan_commit" in report:
                row["publication"] = {"planRef": report["plan_ref"], "plan": id_evidence(report["plan_commit"]),
                                      "stagingRef": report["staging_ref"], "result": id_evidence(report["result_commit"])}
            elif "result_ref" in report:
                row["selection"] = {"resultRef": report["result_ref"], "result": id_evidence(report["result_commit"])}
            if "attempt_id" in report:
                row["occurrence"] = {
                    "id": report["attempt_id"], "commit": id_evidence(report.get("attempt_commit", report["commit"])),
                    "result": id_evidence(report["result_commit"]), "historicalRef": report.get("attempt_ref", ""),
                }
            if "previous_selection_commit" in report:
                row["previousSelection"] = id_evidence(report["previous_selection_commit"])
            if "producer_commit" in report:
                row["producerCommit"] = id_evidence(report["producer_commit"])
            if "request_commit" in report:
                row["requestCommit"] = id_evidence(report["request_commit"])
            if "request_implementation" in report:
                row["requestImplementation"] = report["request_implementation"]
            if "request_factor" in report:
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
