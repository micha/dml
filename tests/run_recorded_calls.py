"""Collect observations from the recorded-calls example for Quint."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import partial
from hashlib import sha256
import json
from os import cpu_count
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Lock
from time import monotonic

from daggerml import core

from replay_core import CoreHistory, OPERATIONS, operation_for
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


def json_fields(value):
    """Preserve JSON object field sets in a canonical depth-first order."""
    if isinstance(value, dict):
        keys = sorted(value)
        yield keys
        for key in keys:
            yield from json_fields(value[key])
    elif isinstance(value, list):
        for item in value:
            yield from json_fields(item)


def declaration_evidence(declaration):
    if declaration is None:
        return {"commit": "", "basis": "", "evidence": "", "predecessor": "", "successor": "", "reason": ""}
    return {"commit": id_evidence(declaration["commit"]), "basis": id_evidence(declaration["basis_commit"]),
            "evidence": id_evidence(declaration["evidence_commit"]), "predecessor": declaration["predecessor"],
            "successor": declaration["successor"], "reason": declaration["reason"]}


def advisory_evidence(view):
    return {"intent": id_evidence(view["intent_commit"]), "relation": view["relation"],
            "declaration": declaration_evidence(view["declaration"])}


def table_evidence(report):
    return {"intent": id_evidence(report["table_intent_commit"]),
            "implementation": report["table_implementation"],
            "previous": id_evidence(report["previous_table_commit"]) if report["previous_table_commit"] else "",
            "entries": [{"request": id_evidence(request), "selection": id_evidence(entry["selection_commit"]),
                         "result": id_evidence(entry["result_commit"]), "attempt": id_evidence(entry["attempt_commit"]),
                         "attemptId": entry["attempt_id"]} for request, entry in sorted(report["entries"].items())]}


def intent_table_evidence(report):
    previous = report.get("previous_table")
    return {"intent": id_evidence(report["intent_commit"]), "genesis": id_evidence(report["intent_genesis"]),
            "previous": id_evidence(previous) if previous else "",
            "entries": [{"producer": id_evidence(entry["producer_commit"]), "factor": entry["factor"],
                         "request": id_evidence(entry["producing_request_commit"]),
                         "implementation": entry["producing_implementation"],
                         "selection": id_evidence(entry["selection_commit"]), "result": id_evidence(entry["result_commit"]),
                         "attempt": id_evidence(entry["attempt_commit"]), "attemptId": entry["attempt_id"]}
                        for entry in report["entries"]]}


def evidence_text(text):
    # The Quint evidence writer cannot represent quotes, backslashes or non-ASCII text.
    return text if re.fullmatch(r"[\x20-\x21\x23-\x5b\x5d-\x7e]*", text) else "hex:" + text.encode("utf-8").hex()


def evidence(op, args, *, code, stderr, unchanged, bundle_present=False, bundle_unchanged=True, bundle_size=-1):
    command = op.replace("_", "-")
    missing_ref = re.fullmatch(
        rf"{re.escape(command)}: \('not_found', -?[0-9]+, 'ref was not found'\)", stderr.rstrip("\n"),
    ) is not None
    return {"op": op, "args": list(args), "code": code, "quiet": not stderr,
            "diagnosed": stderr.startswith(f"{command}: ") and "Traceback" not in stderr,
            "missingRef": missing_ref, "stderr": evidence_text(stderr.rstrip("\n")), "stdoutEmpty": False,
            "repoExisted": False, "repoExists": False,
            "nativeStatus": "", "nativeDetail": "", "nativeValue": "", "nativeCount": 0, "nativeItems": [],
            "commit": "", "calls": [], "reportFields": [], "stdoutHash": "", "historicalReportHash": "",
            "expectedCommit": "", "producerCommit": "", "removed": -1,
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
            "expectedIntent": "", "expectedEvidence": "", "definitionAdvisory": False,
            "expectedTable": "", "tableRef": "", "tableCommit": "",
            "reuseTable": {"intent": "", "implementation": "", "previous": "", "entries": []},
            "reuseScope": "", "producingRequest": "", "producingImplementation": "",
            "intentReuseTable": {"intent": "", "genesis": "", "previous": "", "entries": []},
            "supersession": declaration_evidence(None),
            "asKnownThen": {"intent": "", "relation": "", "declaration": declaration_evidence(None)},
            "knowledgeView": {"intent": "", "relation": "", "declaration": declaration_evidence(None)},
            "decision": {"id": "", "canonicalId": False, "policy": "", "intent": "", "defaultMode": "", "override": "",
                         "route": "", "reason": "", "plan": "", "planRef": "", "selectionRef": "", "selection": "",
                         "result": "", "implementationOverride": "", "implementationReason": ""},
            "unchanged": unchanged, "bundlePresent": bundle_present, "bundleUnchanged": bundle_unchanged,
            "bundleSize": bundle_size}


class ProcessHistory:
    def __init__(self, directory, example, fixture_lock):
        self.directory = directory
        self.repos = {role: directory / role for role in ("source", "worker", "replica")}
        self.example = example
        self.fixture_lock = fixture_lock
        self.native = CoreHistory(core, None, directory, status_results=False)
        self.file_checkpoints = {}
        self.sum_receipts = {}
        self.scale_receipts = {}
        self.plan_receipts = {}
        self.request_receipts = {}
        self.selection_receipts = {}
        self.attempt_receipts = {}
        self.policy_receipts = {}
        self.intent_receipts = {}
        self.table_receipts = {}
        self.decision_receipts = {}
        self.operations = {
            "record": self.record, "record_sum": self.record_sum, "record_scale": self.record_scale,
            "inspect": self.inspect, "export_sum": self.export_sum, "stage_input": self.stage_input,
            "release_input": self.release_input, "collect": self.collect,
            "unlink_bundle": self.unlink_bundle, "truncate_bundle": self.truncate_bundle,
            "write_bundle": self.write_bundle,
            "checkpoint_file": self.checkpoint_file, "compare_file": self.compare_file,
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
            "declare_scale_supersession": self.declare_scale_supersession,
            "define_scale_reuse_table": self.define_scale_reuse_table,
            "update_scale_reuse_table": self.update_scale_reuse_table,
            "request_table_scale": self.request_table_scale, "replicate_decision": self.replicate_decision,
            "define_scale_intent_reuse_table": self.define_scale_intent_reuse_table,
            "update_scale_intent_reuse_table": self.update_scale_intent_reuse_table,
            "request_intent_table_scale": self.request_intent_table_scale,
            **{op: partial(self.native_step, op) for op in (*OPERATIONS, "datum_encode", "object_encode")
               if op in ("repo_export_commit", "repo_import_commit_staged")
               or op not in OPERATIONS or not OPERATIONS[op].observes_failure
               if hasattr(core, op)},
        }

    def receipt_id(self, alias, receipts, role=None):
        if alias.startswith("native:"):
            return self.native.resolve("id", alias.removeprefix("native:")).hex()
        return receipts[alias if role is None else (role, alias)]

    def native_operand(self, arg):
        if arg.startswith("sum:"):
            return self.sum_receipts["source", arg.removeprefix("sum:")]
        if arg.startswith("scale:"):
            _, role, ref = arg.split(":")
            return self.scale_receipts[role, ref]
        if arg.startswith("plan:"):
            return self.plan_receipts[arg.removeprefix("plan:")]
        return arg

    def native_step(self, op, *args):
        # Explicit aliases pass immutable IDs across the CLI/native boundary.
        # Neither direction resolves a current pin to choose the expected ID.
        inputs = operation_for(op, args).inputs
        operands = [self.native_operand(arg) if i < len(inputs) and inputs[i] == "id" else arg
                    for i, arg in enumerate(args)]
        with self.fixture_lock:
            observed = self.native.run(op, *operands, include_error_detail=True)
        row = evidence(op, args, code=0, stderr="", unchanged=False)
        items = observed["items"]
        if op == "datum_decode" and observed["status"] == "ok" and observed["count"] == core.DATUM_STRING:
            items = [evidence_text(bytes.fromhex(observed["value"]).decode("utf-8"))]
        return {**row, "nativeStatus": observed["status"], "nativeDetail": evidence_text(observed["detail"]),
                "nativeValue": observed["value"], "nativeCount": observed["count"], "nativeItems": items}

    def invoke(self, op, args, *, operands=None, bundle=None):
        if self.native.values["repo"]:
            raise ValueError("close native repository handles before launching the CLI")
        role, *cli_args = args
        repo = self.repos[role]
        data = repo / "data.mdb"
        repo_existed = repo.exists()
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
            # Keep diagnostics together when distinct histories run concurrently.
            with self.fixture_lock:
                print(f"{self.directory.name}: {result.stderr}", file=sys.stderr, end="")
        row = evidence(op, args, code=result.returncode, stderr=result.stderr,
                       unchanged=before is not None and before == after,
                       bundle_present=bundle_after is not None, bundle_unchanged=bundle_before == bundle_after,
                       bundle_size=-1 if bundle_after is None else len(bundle_after))
        return {**row, "stdoutEmpty": not result.stdout, "repoExisted": repo_existed,
                "repoExists": repo.exists()}, result.stdout

    def write(self, op, args, **options):
        row, output = self.invoke(op, args, **options)
        return {**row, "commit": id_evidence(output.strip()) if row["code"] == 0 and output else ""}

    def record(self, *args):
        return self.write("record", args)

    def record_sum(self, role, pin, a, b):
        row = self.write("record_sum", (role, pin, a, b))
        if row["commit"]:
            self.sum_receipts[role, pin] = row["commit"]
        return row

    def select(self, op, role, pin, producer_receipt, *tail, bundle=None):
        commit = self.receipt_id(producer_receipt, self.sum_receipts, "source")
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
        commit = self.receipt_id(result_receipt, self.scale_receipts, role)
        bundle = self.directory / filename
        row = self.write("export_scale", (role, pin, result_receipt, filename),
                         operands=(pin, commit, bundle), bundle=bundle)
        return {**row, "expectedCommit": commit}

    def publish_scale(self, role, pin, result_receipt, producer_receipt, expected_factor, main_receipt):
        result = self.receipt_id(result_receipt, self.scale_receipts, "worker")
        producer = self.receipt_id(producer_receipt, self.sum_receipts, "source")
        main = "-" if main_receipt == "-" else self.receipt_id(main_receipt, self.scale_receipts, "worker")
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
        plan = self.receipt_id(plan_receipt, self.plan_receipts)
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
        request = self.receipt_id(request_receipt, self.request_receipts)
        row = self.write("work_scale", (role, pin, request_receipt, result_ref),
                         operands=(pin, request, result_ref))
        if row["commit"]:
            self.scale_receipts[role, result_ref] = row["commit"]
        return {**row, "expectedCommit": request}

    def work_scale_attempt(self, role, pin, request_receipt, attempt_ref, occurrence_id):
        request = self.receipt_id(request_receipt, self.request_receipts)
        args = (role, pin, request_receipt, attempt_ref, occurrence_id)
        row = self.write("work_scale_attempt", args, operands=("--", pin, request, attempt_ref, occurrence_id))
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
        plan = self.receipt_id(plan_receipt, self.plan_receipts)
        attempt = self.receipt_id(attempt_receipt, self.attempt_receipts)
        args = (role, plan_pin, plan_receipt, attempt_pin, attempt_receipt, selection_ref)
        if alias is not None:
            args += (alias,)
        row = self.write("select_scale_attempt", args, operands=(plan_pin, plan, attempt_pin, attempt, selection_ref))
        if row["commit"]:
            self.selection_receipts[alias if alias is not None else selection_ref] = row["commit"]
        return {**row, "expectedCommit": plan, "expectedAttempt": attempt}

    def adopt_scale_attempt(self, role, basis_ref, basis_receipt, attempt_ref, attempt_receipt, selection_ref):
        basis = self.receipt_id(basis_receipt, self.selection_receipts)
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
            expected = self.receipt_id(receipt, self.policy_receipts)
            operands.extend(("--basis-ref", basis_ref, "--basis-commit", expected))
        row = self.write("define_scale_policy", (role, policy_ref, default, *basis), operands=operands)
        if row["commit"]:
            self.policy_receipts[policy_ref] = row["commit"]
        return {**row, "expectedCommit": expected}

    def request_policy_scale(self, role, producer_ref, producer_receipt, policy_ref, policy_receipt,
                             plan_ref, decision_ref, factor, override, *selection):
        producer = self.sum_receipts["source", producer_receipt]
        policy = self.receipt_id(policy_receipt, self.policy_receipts)
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
                expected_selection = self.receipt_id(selection[1], self.selection_receipts)
                operands.extend(("--selection-commit", expected_selection))
        row = self.write("request_policy_scale", args, operands=operands)
        return {**row, "expectedCommit": producer, "expectedPolicy": policy, "expectedSelection": expected_selection}

    def define_scale_intent(self, role, intent_ref, implementation, *definition):
        expected = ""
        operands = [intent_ref, implementation]
        if len(definition) == 2:
            basis_ref, receipt = definition
            expected = self.receipt_id(receipt, self.intent_receipts)
            operands.extend(("--basis-ref", basis_ref, "--basis-commit", expected))
        else:
            reuse, v1_slot, v2_slot = definition
            operands.extend(("--reuse-default", reuse, "--v1-selection", v1_slot, "--v2-selection", v2_slot))
        row = self.write("define_scale_intent", (role, intent_ref, implementation, *definition), operands=operands)
        if row["commit"]:
            self.intent_receipts[intent_ref] = row["commit"]
        return {**row, "expectedCommit": expected}

    def declare_scale_supersession(self, role, basis_ref, basis_receipt, output_ref, predecessor, successor, reason,
                                   evidence_ref, evidence_receipt):
        basis = self.receipt_id(basis_receipt, self.intent_receipts)
        evidence_commit = self.receipt_id(evidence_receipt, self.sum_receipts, role)
        args = (role, basis_ref, basis_receipt, output_ref, predecessor, successor, reason, evidence_ref, evidence_receipt)
        operands = (basis_ref, basis, output_ref, predecessor, successor, reason, evidence_ref, evidence_commit)
        row = self.write("declare_scale_supersession", args, operands=operands)
        if row["commit"]:
            self.intent_receipts[output_ref] = row["commit"]
        return {**row, "expectedIntent": basis, "expectedEvidence": evidence_commit}

    def request_intent_scale(self, role, producer_ref, producer_receipt, intent_ref, intent_receipt,
                             plan_ref, decision_ref, factor, implementation, override, selection):
        producer = self.sum_receipts["source", producer_receipt]
        intent = self.receipt_id(intent_receipt, self.intent_receipts)
        args = (role, producer_ref, producer_receipt, intent_ref, intent_receipt, plan_ref, decision_ref,
                factor, implementation, override, selection)
        operands = [producer_ref, producer, intent_ref, intent, plan_ref, decision_ref, factor]
        if implementation != "default":
            operands.extend(("--implementation", implementation))
        if override != "default":
            operands.extend(("--override", override))
        expected_selection = "" if selection == "-" else self.receipt_id(selection, self.selection_receipts)
        if expected_selection:
            operands.extend(("--selection-commit", expected_selection))
        row = self.write("request_intent_scale", args, operands=operands)
        return {**row, "expectedCommit": producer, "expectedIntent": intent, "expectedSelection": expected_selection}

    def define_scale_reuse_table(self, role, intent_ref, intent_receipt, implementation, output):
        intent = self.intent_receipts[intent_receipt]
        args = (role, intent_ref, intent_receipt, implementation, output)
        row = self.write("define_scale_reuse_table", args, operands=(intent_ref, intent, implementation, output))
        if row["commit"]:
            self.table_receipts[output] = row["commit"]
        return {**row, "expectedIntent": intent}

    def update_scale_reuse_table(self, role, basis_ref, basis_receipt, selection_ref, selection_receipt, output, mode):
        basis = self.table_receipts[basis_receipt]
        selection = self.selection_receipts[selection_receipt]
        args = (role, basis_ref, basis_receipt, selection_ref, selection_receipt, output, mode)
        row = self.write("update_scale_reuse_table", args, operands=(basis_ref, basis, selection_ref, selection, output, mode))
        if row["commit"]:
            self.table_receipts[output] = row["commit"]
        return {**row, "expectedTable": basis, "expectedSelection": selection}

    def define_scale_intent_reuse_table(self, role, intent_ref, intent_receipt, output):
        intent = self.intent_receipts[intent_receipt]
        args = (role, intent_ref, intent_receipt, output)
        row = self.write("define_scale_intent_reuse_table", args, operands=(intent_ref, intent, output))
        if row["commit"]:
            self.table_receipts[output] = row["commit"]
        return {**row, "expectedIntent": intent}

    def update_scale_intent_reuse_table(self, role, basis_ref, basis_receipt, output, mode, *key):
        basis = self.table_receipts[basis_receipt]
        args = (role, basis_ref, basis_receipt, output, mode, *key)
        operands = [basis_ref, basis, output, mode]
        selection = producer = ""
        if mode == "remove":
            producer_receipt, factor = key
            producer = self.sum_receipts[role, producer_receipt]
            operands.extend(("--producer-commit", producer, "--factor", factor))
        else:
            selection_ref, selection_receipt = key
            selection = self.selection_receipts[selection_receipt]
            operands.extend(("--selection", selection_ref, "--selection-commit", selection))
        row = self.write("update_scale_intent_reuse_table", args, operands=operands)
        if row["commit"]:
            self.table_receipts[output] = row["commit"]
        return {**row, "expectedCommit": producer, "expectedTable": basis, "expectedSelection": selection}

    def request_table_scale(self, *args):
        return self.request_scale_from_table("request_table_scale", *args)

    def request_intent_table_scale(self, *args):
        return self.request_scale_from_table("request_intent_table_scale", *args)

    def request_scale_from_table(self, op, role, producer_ref, intent_ref, intent_receipt, plan_ref, decision_ref, factor,
                                 table_ref, table_receipt, implementation, override):
        producer = self.sum_receipts["source", producer_ref]
        intent = self.intent_receipts[intent_receipt]
        if table_receipt == "-":
            table = ""
        elif table_receipt.startswith("sum:"):
            table = self.sum_receipts[role, table_receipt.removeprefix("sum:")]
        else:
            table = self.table_receipts[table_receipt]
        args = (role, producer_ref, intent_ref, intent_receipt, plan_ref, decision_ref, factor, table_ref, table_receipt,
                implementation, override)
        operands = [producer_ref, producer, intent_ref, intent, plan_ref, decision_ref, factor, "--table", table_ref]
        if table:
            operands.extend(("--table-commit", table))
        if implementation != "default":
            operands.extend(("--implementation", implementation))
        if override != "default":
            operands.extend(("--override", override))
        row = self.write(op, args, operands=operands)
        if row["commit"]:
            self.decision_receipts[decision_ref] = row["commit"]
        return {**row, "expectedCommit": producer, "expectedIntent": intent, "expectedTable": table}

    def replicate_decision(self, role, decision_receipt, pin):
        # Fixture only: transfer the exact decision closure, without any of its ref names.
        commit = self.decision_receipts[decision_receipt]
        path = self.repos[role]
        data = path / "data.mdb"
        before = data.read_bytes()
        with self.fixture_lock:
            source = core.repo_open(path, False)
            try:
                bundle = core.repo_export_commit(source, bytes.fromhex(commit))
            finally:
                core.repo_close(source)
            replica = core.repo_open(self.repos["replica"], True)
            try:
                root = core.repo_import_commit_staged(replica, bundle, pin.encode("ascii"))
            finally:
                core.repo_close(replica)
        row = evidence("replicate_decision", (role, decision_receipt, pin), code=0, stderr="",
                       unchanged=before == data.read_bytes())
        return {**row, "commit": id_evidence(root.hex()), "expectedCommit": commit}

    def drop_ref(self, role, pin, kind, receipt):
        # Fixture only: simulate a separate ref owner without adding a CLI command.
        receipts = {"attempt": self.attempt_receipts, "selection": self.selection_receipts,
                    "policy": self.policy_receipts, "intent": self.intent_receipts, "table": self.table_receipts}
        expected = receipts[kind][receipt]
        path = self.repos[role]
        data = path / "data.mdb"
        before = data.read_bytes()
        with self.fixture_lock:
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
        plan = self.receipt_id(plan_receipt, self.plan_receipts)
        # Use the original worker receipt or a native ID, never re-resolve the pin.
        result = self.receipt_id(result_receipt, self.scale_receipts, "worker")
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
        plan = self.receipt_id(plan_receipt, self.plan_receipts)
        selection = self.receipt_id(selection_receipt, self.selection_receipts)
        args = (role, plan_pin, plan_receipt, selection_ref, selection_receipt, reuse_ref)
        row = self.write("publish_selected_scale", args,
                         operands=(plan_pin, plan, selection_ref, selection, reuse_ref))
        return {**row, "expectedCommit": plan, "expectedSelection": selection}

    def publish_requested_scale(self, role, pin, plan_receipt, returned, result_receipt, receipt_ref=None):
        plan = self.receipt_id(plan_receipt, self.plan_receipts)
        result = self.receipt_id(result_receipt, self.scale_receipts, "worker")
        args = (role, pin, plan_receipt, returned, result_receipt)
        operands = (pin, plan, returned, result)
        if receipt_ref is not None:
            args += (receipt_ref,)
            operands += ("--receipt-ref", receipt_ref)
        row = self.write("publish_requested_scale", args, operands=operands)
        return {**row, "expectedCommit": plan, "expectedResult": result}

    def unlink_bundle(self, filename):
        path = self.directory / filename
        path.unlink()
        return evidence("unlink_bundle", (filename,), code=0, stderr="", unchanged=False,
                        bundle_present=path.exists(), bundle_size=path.stat().st_size if path.is_file() else -1)

    def write_bundle(self, alias, filename):
        data = self.native.resolve("bundle", alias)
        path = self.directory / filename
        with path.open("xb") as file:
            file.write(data)
        written = path.read_bytes()
        return evidence("write_bundle", (alias, filename), code=0, stderr="", unchanged=written == data,
                        bundle_present=path.is_file(), bundle_size=len(written))

    def truncate_bundle(self, source, destination, count):
        src = self.directory / source
        dst = self.directory / destination
        before = src.read_bytes()
        suffix_length = int(count)
        if not 0 < suffix_length < len(before):
            raise ValueError("bundle suffix length must leave a nonempty prefix")
        with dst.open("xb") as file:
            file.write(before[:-suffix_length])
        copied = dst.read_bytes()
        # For a copied truncation, unchanged compares the retained prefix.
        return evidence("truncate_bundle", (source, destination, count), code=0, stderr="",
                        unchanged=copied == before[:len(copied)], bundle_present=dst.is_file(),
                        bundle_unchanged=src.read_bytes() == before, bundle_size=len(copied))

    def checkpoint_file(self, role, alias):
        data = self.repos[role] / "data.mdb"
        self.file_checkpoints[alias] = data.read_bytes()
        return {**evidence("checkpoint_file", (role, alias), code=0, stderr="", unchanged=False),
                "repoExists": data.is_file()}

    def compare_file(self, role, alias):
        data = self.repos[role] / "data.mdb"
        exists = data.is_file()
        unchanged = exists and data.read_bytes() == self.file_checkpoints[alias]
        return {**evidence("compare_file", (role, alias), code=0, stderr="", unchanged=unchanged), "repoExists": exists}

    def collect(self, role):
        row, output = self.invoke("collect", (role,))
        return {**row, "removed": int(output) if output else -1}

    def inspect(self, role, *args):
        knowledge = ""
        operands = args
        if len(args) == 2:
            ref, operand = args
            knowledge = (operand.removeprefix("literal:") if operand.startswith("literal:")
                         else self.receipt_id(operand, self.intent_receipts))
            operands = (ref, "--knowledge-commit", knowledge)
        row, output = self.invoke("inspect", (role, *args), operands=operands)
        row["expectedIntent"] = knowledge
        if output:
            row["stdoutHash"] = sha256(output.encode("utf-8")).hexdigest()
            report = json.loads(output)
            row["reportFields"] = list(json_fields(report))
            row["commit"] = id_evidence(report["commit"])
            row["tableRef"] = report.get("table_ref", "")
            if "table_commit" in report:
                row["tableCommit"] = id_evidence(report["table_commit"])
            row["reuseScope"] = report.get("reuse_scope", "")
            if "entries" in report:
                if row["reuseScope"] == "intent":
                    row["intentReuseTable"] = intent_table_evidence(report)
                else:
                    row["reuseTable"] = table_evidence(report)
            if "producing_request_commit" in report:
                row["producingRequest"] = id_evidence(report["producing_request_commit"])
            row["producingImplementation"] = report.get("producing_implementation", "")
            if "supersession" in report:
                row["definitionAdvisory"] = True
                row["supersession"] = declaration_evidence(report["supersession"])
            if "as_known_then" in report:
                historical = {key: value for key, value in report.items() if key != "knowledge_view"}
                row["historicalReportHash"] = sha256(json.dumps(historical, sort_keys=True).encode("utf-8")).hexdigest()
                row["asKnownThen"] = advisory_evidence(report["as_known_then"])
            if "knowledge_view" in report:
                row["knowledgeView"] = advisory_evidence(report["knowledge_view"])
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
        # Fixture calls use the in-process binding, unlike regular CLI steps.
        self.fixture_lock = Lock()

    @contextmanager
    def history(self, directory):
        history = ProcessHistory(directory, self.example, self.fixture_lock)
        try:
            yield history
            if history.native.values["repo"] or history.native.values["txn"]:
                raise ValueError("history must explicitly end native transactions and close repositories")
        finally:
            with self.fixture_lock:
                history.native.close()


def observe_histories(suite, directory, histories):
    def observe(index):
        return {**replay_history(suite, directory / f"history-{index}", histories[index]), "scenario": index}

    # Each history serially drives its own repositories and starts a subprocess
    # per CLI step. Start longer histories first, then restore the spec's order.
    order = sorted(range(len(histories)), key=lambda index: len(histories[index]), reverse=True)
    with ThreadPoolExecutor(max_workers=min(4, cpu_count() or 1)) as executor:
        return sorted(executor.map(observe, order), key=lambda observation: observation["scenario"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_quint_arguments(parser)
    for name in ("example", "histories", "rules"):
        parser.add_argument(name, type=absolute_path)
    parser.add_argument("modules", nargs="*", type=absolute_path, help="shared Quint modules")
    args = parser.parse_args()
    quint = quint_command(args)
    with TemporaryDirectory(prefix="dml-recorded-calls-") as tmp:
        directory = Path(tmp)
        started = monotonic()
        histories = read_histories(quint, args.histories, directory / "histories.itf.json", ["init"])
        loaded = monotonic()
        print(f"Loaded {len(histories)} recorded-call histories in {loaded - started:.2f}s", file=sys.stderr, flush=True)
        observations = observe_histories(Processes(args.example), directory, histories)
        replayed = monotonic()
        print(f"Collected recorded-call observations in {replayed - loaded:.2f}s", file=sys.stderr, flush=True)
        # Sparse columns keep the full evidence without repeating its wide type for each step.
        defaults = evidence("", (), code=0, stderr="", unchanged=False)
        state = evaluate(quint, args.rules, directory, observations, [args.histories, *args.modules],
                         attempt_defaults=defaults)
        print(f"Evaluated recorded-call observations in {monotonic() - replayed:.2f}s", file=sys.stderr, flush=True)
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"recorded-calls interpretation failed: {error}") from error
