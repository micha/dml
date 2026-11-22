"""Lower checked Quint read-context rules to a Python property."""

import argparse
from pathlib import Path
import subprocess

from generate_python import Unsupported, closed_fields, compile_ir, literal, operands, require, string_set, type_name
from generate_transactions import TransactionLowerer, transaction_type


# Only these operations and endings have concrete bindings.
OPERATIONS = {"commit", "create_ref", "missing_read"}
EXIT_MODES = {"normal", "exception"}
LAYOUTS = {
    "Step": {"operation": "str", "outcome": "str", "readAfter": "str"},
    "Attempt": {"before": "str", "steps": "List[Step]", "exitMode": "str", "exitOutcome": "str",
                "endedRead": "str", "after": "str", "probeRef": "str"},
}


class ReadContextLowerer(TransactionLowerer):
    def __init__(self, ir: dict) -> None:
        require(ir["stage"] == "compiling" and not ir["errors"], "expected checked compile output")
        self.module = ir["main"]
        modules = ir["modules"]
        require(len(modules) == 1 and modules[0]["name"] == self.module == "read_context_rules",
                "expected only read_context_rules without imports")
        declarations = modules[0]["declarations"]
        require(all("name" in decl for decl in declarations), "unsupported read-context import")
        self.declarations = {decl["name"]: decl for decl in declarations}
        self.table = ir["table"]
        self.success = None
        reserved = LAYOUTS.keys() | {"scenario", "ruleIds"}
        require(reserved <= self.declarations.keys(), "missing required read-context declarations")
        for type_id, layout in LAYOUTS.items():
            decl = self.declarations[type_id]
            require(decl["kind"] == "typedef" and decl["type"]["kind"] == "rec", f"expected record {type_id}")
            fields = closed_fields(decl["type"]["fields"])
            require({key: transaction_type(value) for key, value in fields.items()} == layout,
                    f"{type_id} layout does not match the read-context adapter")
        self.signatures = {}
        for symbol in sorted(self.declarations.keys() - reserved):
            decl = self.declarations[symbol]
            annotation = decl.get("typeAnnotation")
            require(decl.get("qualifier") == "puredef" and annotation is not None
                    and annotation["kind"] == "oper", f"expected explicitly typed pure def: {symbol}")
            args = tuple(type_name(arg) for arg in annotation["args"])
            result = type_name(annotation["res"])
            require(1 <= len(args) <= 2 and set(args) <= {"str", "bool", "Attempt", "Step"}
                    and result in ("bool", "str"), f"unsupported signature for {symbol}")
            self.signatures[symbol] = ("puredef", args, result)
        require(self.signatures.get("verdict") == ("puredef", ("str", "Attempt"), "str"),
                "expected a verdict definition taking a rule ID and an attempt")

    def validate_registry(self, ids: tuple[str, ...]) -> None:
        verdict = self.declarations["verdict"]["expr"]
        require(verdict["kind"] == "lambda", "verdict must dispatch its rule ID")
        parameter = verdict["params"][0]
        branch = verdict["expr"]
        dispatched = set()
        while branch["kind"] == "app" and branch["opcode"] == "ite":
            condition, _, branch = operands(branch, "ite", 3)
            key, value = operands(condition, "eq", 2)
            require(key["kind"] == "name" and self.resolves_to(key, parameter),
                    "verdict must branch on its rule ID")
            rule = literal(value, "str")
            require(rule not in dispatched, f"duplicate verdict for {rule}")
            dispatched.add(rule)
        require(literal(branch, "str") == "unknown rule", "verdict must reject unknown rules")
        require(dispatched == set(ids), "read-context rule registry and verdict dispatch do not agree")

    def emit(self) -> str:
        decl = self.declarations["scenario"]
        require(decl.get("qualifier") == "pureval", "scenario must be a pure val")
        args = operands(decl["expr"], "Rec", 6)
        fields = {literal(key, "str"): value for key, value in zip(args[::2], args[1::2], strict=True)}
        require(fields.keys() == {"operations", "exits", "maxSteps"}, "unsupported read-context scenario fields")
        operations = string_set(fields["operations"])
        exits = string_set(fields["exits"])
        bound = literal(fields["maxSteps"], "int")
        require(operations and set(operations) <= OPERATIONS and exits and set(exits) <= EXIT_MODES,
                "scenario has an unsupported read-context operation or ending")
        require(1 <= bound <= 4, "scenario exceeds the read-context profile bounds")
        registry = self.declarations["ruleIds"]
        require(registry.get("qualifier") == "pureval", "ruleIds must be a pure val")
        ids = string_set(registry["expr"])
        require(len(ids) == len(operands(registry["expr"], "Set")) and 1 <= len(ids) <= 8
                and all(rule.isascii() and rule.isidentifier() for rule in ids), "unsupported read-context registry")
        self.validate_registry(ids)
        header = (
            "# Generated from read_context_rules.qnt; do not edit.\n\n"
            "from collections import Counter\nfrom functools import reduce as _reduce\n\n"
            "from hypothesis import given, seed, settings, strategies as st\n\n"
            "from read_context_binding import exercise as execute, validate_observation\n\n\n"
            f"OPERATIONS = {operations!r}\nEXIT_MODES = {exits!r}\nMAX_STEPS = {bound}\nRULE_IDS = {ids!r}\n"
        )
        definitions = "\n\n\n".join(self.definition(symbol) for symbol in self.signatures)
        return f"{header}\n\n{definitions}\n\n\n{DRIVER}"


DRIVER = '''HISTORIES = st.tuples(st.lists(st.sampled_from(OPERATIONS), min_size=1, max_size=MAX_STEPS),
                      st.sampled_from(EXIT_MODES))


class RuleViolation(AssertionError):
    def __init__(self, rule, requests, exit_mode, attempt):
        self.rule, self.requests, self.exit_mode = rule, tuple(requests), exit_mode
        self.attempt = attempt
        super().__init__(f"{rule}: {self.requests!r}, {exit_mode}: {attempt!r}")


def verdicts(attempt):
    return {rule: verdict(rule, attempt) for rule in RULE_IDS}


def check(requests, exit_mode, attempt):
    validate_observation(requests, exit_mode, attempt)
    counts = Counter()
    for rule, result in verdicts(attempt).items():
        if result == "violation":
            raise RuleViolation(rule, requests, exit_mode, attempt)
        if result not in ("pass", "unexercised"):
            raise ValueError(f"Unknown verdict from {rule}: {result!r}")
        counts[rule, result] += 1
    return counts


def require_witnesses(counts):
    missing = [rule for rule in RULE_IDS if not counts[rule, "pass"]]
    if missing:
        raise AssertionError(f"Rules with no matching read context: {', '.join(missing)}")


def run_property(*, sample_seed, max_examples, history_strategy=HISTORIES):
    counts = Counter()
    histories = 0

    @seed(sample_seed)
    @settings(max_examples=max_examples, database=None, deadline=None)
    @given(history_strategy)
    def check_case(trace):
        nonlocal histories
        requests, exit_mode = trace
        counts.update(check(requests, exit_mode, execute(requests, exit_mode)))
        histories += 1

    check_case()
    require_witnesses(counts)
    return histories, counts
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path)
    parser.add_argument("--source", default=Path(__file__).with_name("read_context_rules.qnt"), type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        code = ReadContextLowerer(compile_ir(args.quint.absolute(), args.source)).emit()
        compile(code, str(args.out), "exec")
    except (Unsupported, subprocess.SubprocessError) as error:
        parser.exit(1, f"generation failed: {error}\n")
    args.out.write_text(code, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
