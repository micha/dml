"""Lower the transaction feasibility rules from checked Quint 0.33.1 IR."""

import argparse
from pathlib import Path
import subprocess

from generate_python import (
    Lowerer, Unsupported, closed_fields, compile_ir, literal, name, operands, require,
    scenario, string_set, type_name,
)


LAYOUTS = {
    "Ref": ("sum", {"Absent": "unit", "Target": "str", "Unreadable": "str"}),
    "Outcome": ("sum", {"Succeeded": "unit", "Failed": "str"}),
    "Step": ("rec", {"operation": "str", "requested": "str", "before": "Ref", "after": "Ref",
                     "outcome": "Outcome", "poisoned": "bool"}),
    "Attempt": ("rec", {"before": "Ref", "staged": "Ref", "after": "Ref", "steps": "List[Step]",
                        "finish": "str", "outcome": "Outcome", "markerBefore": "bool",
                        "markerStaged": "bool", "markerAfter": "bool"}),
}


def transaction_type(node: dict) -> str:
    if node["kind"] == "list":
        return f"List[{transaction_type(node['elem'])}]"
    return type_name(node)


class TransactionLowerer(Lowerer):
    def __init__(self, ir: dict) -> None:
        require(ir["stage"] == "compiling" and not ir["errors"], "expected checked compile output")
        modules = ir["modules"]
        self.module = ir["main"]
        require(len(modules) == 1 and self.module == modules[0]["name"] == "transaction_rules",
                "expected the transaction_rules module without imports")
        declarations = modules[0]["declarations"]
        require(all("name" in decl for decl in declarations), "imports are unsupported in rules")
        self.declarations = {decl["name"]: decl for decl in declarations}
        self.table = ir["table"]
        self.success = "Succeeded"
        for type_id, (kind, layout) in LAYOUTS.items():
            decl = self.declarations.get(type_id)
            require(decl is not None and decl["kind"] == "typedef" and decl["type"]["kind"] == kind,
                    f"unsupported {type_id} type")
            fields = closed_fields(decl["type"]["fields"])
            require({key: transaction_type(value) for key, value in fields.items()} == layout,
                    f"{type_id} layout does not match the transaction adapter")
        self.signatures = {
            "Absent": ("val", (), "Ref"), "Succeeded": ("val", (), "Outcome"),
            "Target": ("def", ("str",), "Ref"), "Unreadable": ("def", ("str",), "Ref"),
            "Failed": ("def", ("str",), "Outcome"),
        }
        reserved = LAYOUTS.keys() | self.signatures.keys() | {"scenario", "ruleIds"}
        require(reserved <= self.declarations.keys(), "missing transaction declarations")
        for symbol in sorted(self.declarations.keys() - reserved):
            decl = self.declarations[symbol]
            annotation = decl.get("typeAnnotation")
            require(decl.get("qualifier") == "puredef" and annotation is not None
                    and annotation["kind"] == "oper", f"expected explicitly typed pure def: {symbol}")
            args = tuple(type_name(arg) for arg in annotation["args"])
            result = type_name(annotation["res"])
            require(1 <= len(args) <= 2 and set(args) <= {"str", "bool", "Attempt", "Step"}
                    and result in ("str", "bool"), f"unsupported signature for {symbol}")
            self.signatures[symbol] = ("puredef", args, result)
        require(self.signatures.get("verdict") == ("puredef", ("str", "Attempt"), "str"),
                "transaction verdict must take a rule ID and a transaction attempt")

    def python_name(self, symbol: str) -> str:
        return name("" if symbol == "verdict" else "_q_", symbol)

    def expression(self, node: dict, params: tuple[dict, ...]) -> str:
        kind = node["kind"]
        if kind == "int":
            return repr(int(node["value"]))
        if kind == "name":
            for index, param in enumerate(params):
                if self.resolves_to(node, param):
                    return ("value", "value1")[index] if index < 2 else f"_local{index}"
        if kind == "let":
            binding = node["opdef"]
            require(binding.get("kind") == "def" and binding.get("qualifier") in ("val", "pureval")
                    and binding["expr"]["kind"] != "lambda", "only local values are supported")
            scope = params if len(params) >= 2 else (*params, {"id": -1})
            symbol = f"_local{len(scope)}"
            value = self.expression(binding["expr"], params)
            body = self.expression(node["expr"], (*scope, binding))
            return f"((lambda {symbol}: {body})({value}))"
        if kind == "lambda":
            local = tuple(node["params"])
            require(len(local) == 2 and len(params) >= 1, "only binary fold lambdas are supported")
            # Top-level definitions use value/value1; reserve both slots for nested
            # lambda names even when the containing pure def has just one parameter.
            scope = params if len(params) >= 2 else (*params, {"id": -1})
            symbols = ", ".join(f"_local{index}" for index in range(len(scope), len(scope) + len(local)))
            return f"(lambda {symbols}: {self.expression(node['expr'], (*scope, *local))})"
        if kind == "app":
            op, args = node["opcode"], node["args"]
            if op == "Rec":
                require(len(args) >= 2 and len(args) % 2 == 0, "expected nonempty record literal")
                keys = [literal(key, "str") for key in args[::2]]
                require(len(set(keys)) == len(keys), "duplicate record fields are unsupported")
                fields = [f"{key!r}: {self.expression(value, params)}"
                          for key, value in zip(keys, args[1::2], strict=True)]
                return "{" + ", ".join(fields) + "}"
            if op in ("foldl", "length", "or"):
                values = [self.expression(arg, params) for arg in args]
                if op == "foldl" and len(args) == 3:
                    require(args[2]["kind"] == "lambda", "foldl requires an explicit binary lambda")
                    return f"_reduce({values[2]}, {values[0]}, {values[1]})"
                if op == "length" and len(args) == 1:
                    return f"len({values[0]})"
                if op == "or" and len(args) >= 2:
                    return f"({' or '.join(values)})"
                raise Unsupported(f"unsupported transaction operation {op!r}/{len(args)}")
        return super().expression(node, params)

    def emit(self) -> str:
        decl = self.declarations["scenario"]
        require(decl.get("qualifier") == "pureval", "scenario must be a pure val")
        args = operands(decl["expr"], "Rec", 8)
        fields = {literal(key, "str"): value for key, value in zip(args[::2], args[1::2], strict=True)}
        require(fields.keys() == {"operations", "targets", "maxSteps", "finishes"},
                "unsupported transaction scenario fields")
        finishes = string_set(fields["finishes"])
        require(finishes == ("abort", "commit"), "the transaction profile requires abort and commit")
        base_args = [arg for key, value in zip(args[::2], args[1::2], strict=True)
                     if key["value"] != "finishes" for arg in (key, value)]
        operations, targets, bound = scenario({**decl, "expr": {**decl["expr"], "args": base_args}}, True)
        require(bound <= 4, "transaction scenario exceeds the spike history bound")
        registry = self.declarations["ruleIds"]
        require(registry.get("qualifier") == "pureval", "ruleIds must be a pure val")
        rule_ids = string_set(registry["expr"])
        require(1 <= len(rule_ids) <= 8 and all(rule.isascii() and rule.isidentifier() for rule in rule_ids),
                "ruleIds must contain 1–8 ASCII identifiers")
        header = (
            "# Generated from transaction_rules.qnt; do not edit.\n\n"
            "from collections import Counter\nfrom functools import reduce as _reduce\n\n"
            "from hypothesis import given, seed, settings, strategies as st\n\n"
            "from transaction_binding import exercise_transaction, validate_observation\n\n\n"
            f"TARGETS = {targets!r}\nOPERATIONS = {operations!r}\nMAX_STEPS = {bound}\n"
            f"FINISHES = {finishes!r}\nRULE_IDS = {rule_ids!r}\n"
        )
        definitions = "\n\n\n".join(self.definition(symbol) for symbol in self.signatures)
        return f"{header}\n\n{definitions}\n\n\n{DRIVER}"


DRIVER = '''REQUESTS = st.tuples(st.sampled_from(OPERATIONS), st.sampled_from(TARGETS))
HISTORIES = st.tuples(st.sampled_from((None, *TARGETS)),
                      st.lists(REQUESTS, max_size=MAX_STEPS), st.sampled_from(FINISHES))


class RuleViolation(AssertionError):
    def __init__(self, rule, initial, requests, finish, evidence):
        self.rule, self.initial, self.requests, self.finish = rule, initial, tuple(requests), finish
        super().__init__(f"{rule}: initial={initial!r}, requests={self.requests!r}, "
                         f"finish={finish!r}, evidence={evidence!r}")


def execute(initial, requests, finish):
    return exercise_transaction(TARGETS, initial, requests, finish)


def verdicts(evidence):
    return {rule: verdict(rule, evidence) for rule in RULE_IDS}


def check(initial, requests, finish, batch):
    evidence = validate_observation(initial, requests, finish, batch)
    counts = Counter()
    for rule, result in verdicts(evidence).items():
        if result == "violation":
            raise RuleViolation(rule, initial, requests, finish, evidence)
        if result not in ("pass", "unexercised"):
            raise ValueError(f"Unknown verdict from {rule}: {result!r}")
        counts[rule, result] += 1
    return counts


def require_witnesses(counts):
    missing = [rule for rule in RULE_IDS if counts[rule, "pass"] == 0]
    if missing:
        raise AssertionError(f"Rules with no matching exercise in the suite: {', '.join(missing)}")


def run_property(*, sample_seed, max_examples, corrupt=None, history_strategy=None):
    histories, counts = 0, Counter()

    @seed(sample_seed)
    @settings(max_examples=max_examples, database=None, deadline=None)
    @given(HISTORIES if history_strategy is None else history_strategy)
    def property_check(trace):
        nonlocal histories
        initial, requests, finish = trace
        batch = execute(initial, requests, finish)
        try:
            counts.update(check(initial, requests, finish, batch))
        except RuleViolation as error:
            if corrupt is not None:
                raise RuntimeError(f"Real observations failed during the shrink control: {error}") from error
            raise
        if corrupt is not None:
            check(initial, requests, finish, corrupt(trace, batch))
        histories += 1

    property_check()
    require_witnesses(counts)
    return histories, counts
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path)
    parser.add_argument("--source", default=Path(__file__).with_name("transaction_rules.qnt"), type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        code = TransactionLowerer(compile_ir(args.quint.absolute(), args.source)).emit()
        compile(code, "<generated transaction check>", "exec")
    except (Unsupported, subprocess.SubprocessError) as error:
        parser.exit(1, f"generation failed: {error}\n")
    args.out.write_text(code, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
