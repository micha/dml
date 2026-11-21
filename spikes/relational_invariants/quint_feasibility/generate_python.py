"""Compile the ref feasibility profiles from Quint 0.33.1 IR to Python."""

import argparse
from collections.abc import Set
import json
import keyword
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


TYPE_LAYOUTS = {
    "Ref": ("sum", {"Absent": "unit", "Target": "str"}),
    "Outcome": ("sum", {"Created": "unit", "Failed": "str"}),
    "Attempt": ("rec", {"before": "Ref", "requested": "str", "outcome": "Outcome", "after": "Ref"}),
}
# Allowed exports and their arity; None denotes a value rather than a function.
DEFINITIONS = {
    "Absent": ("val", None, "Ref"),
    "Created": ("val", None, "Outcome"),
    "Target": ("def", "str", "Ref"),
    "Failed": ("def", "str", "Outcome"),
    "whenRefExists": ("puredef", "Attempt", "bool"),
    "expectRejectedAndPreserved": ("puredef", "Attempt", "bool"),
    "verdict": ("puredef", "Attempt", "str"),
}


class Unsupported(ValueError):
    """The type-checked program uses something outside this backend's profile."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Unsupported(message)


def closed_fields(row: dict) -> dict:
    if row["kind"] == "empty":
        return {}
    require(row["kind"] == "row" and row["other"]["kind"] == "empty", "expected a closed row")
    return {field["fieldName"]: field["fieldType"] for field in row["fields"]}


def type_name(node: dict) -> str:
    kind = node["kind"]
    if kind == "const":
        return node["name"]
    if kind == "tup" and not closed_fields(node["fields"]):
        return "unit"
    require(kind in ("str", "bool"), f"unsupported type {kind!r}")
    return kind


def operands(node: dict, opcode: str, arity: int | None = None) -> list[dict]:
    require(node["kind"] == "app" and node["opcode"] == opcode, f"expected literal {opcode}")
    args = node["args"]
    require(arity is None or len(args) == arity, f"unexpected arity for {opcode}")
    return args


def literal(node: dict, kind: str) -> str | int:
    require(node["kind"] == kind, f"expected {kind} literal, got {node['kind']!r}")
    return node["value"]


def string_set(expr: dict) -> tuple[str, ...]:
    return tuple(sorted({literal(arg, "str") for arg in operands(expr, "Set")}))


def scenario(declaration: dict, mixed: bool) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    require(declaration["kind"] == "def" and declaration["qualifier"] == "pureval",
            "scenario must be a pure val")
    args = operands(declaration["expr"], "Rec", 6)
    fields = {literal(key, "str"): value for key, value in zip(args[::2], args[1::2], strict=True)}
    operation_field = "operations" if mixed else "operation"
    require(fields.keys() == {operation_field, "targets", "maxSteps"}, "unsupported scenario fields")
    operations = string_set(fields[operation_field]) if mixed else (literal(fields[operation_field], "str"),)
    allowed = {"create_ref", "update_ref"} if mixed else {"create_ref"}
    require(bool(operations) and set(operations) <= allowed, f"unsupported DML operation set: {operations!r}")
    targets = string_set(fields["targets"])
    max_steps = literal(fields["maxSteps"], "int")
    require(1 <= len(targets) <= 8 and 0 <= max_steps <= 8, "scenario exceeds the spike profile bounds")
    return operations, targets, max_steps


def name(prefix: str, identifier: str) -> str:
    require(identifier.isascii() and identifier.isidentifier() and not keyword.iskeyword(identifier),
            f"unsupported identifier {identifier!r}")
    return prefix + identifier


class Lowerer:
    def __init__(self, ir: dict) -> None:
        require(ir["stage"] == "compiling" and not ir["errors"], "expected checked compile output")
        modules = ir["modules"]
        self.module = ir["main"]
        require(len(modules) == 1 and modules[0]["name"] == self.module
                and self.module in ("ref_rules", "mixed_ref_rules"), "unsupported Quint module")
        self.mixed = self.module == "mixed_ref_rules"
        declarations = modules[0]["declarations"]
        require(all("name" in decl for decl in declarations), "imports are not supported in the rules module")
        self.declarations = {decl["name"]: decl for decl in declarations}
        self.table = ir["table"]
        layouts = dict(TYPE_LAYOUTS)
        if self.mixed:
            layouts["Outcome"] = ("sum", {"Succeeded": "unit", "Failed": "str"})
            layouts["Attempt"] = ("rec", {"operation": "str", **layouts["Attempt"][1]})
        self.success = "Succeeded" if self.mixed else "Created"
        self.signatures = self.definition_signatures(layouts.keys())
        for type_id, (kind, layout) in layouts.items():
            decl = self.declarations.get(type_id)
            require(decl is not None and decl["kind"] == "typedef" and decl["type"]["kind"] == kind,
                    f"unsupported {type_id} type")
            fields = closed_fields(decl["type"]["fields"])
            require({key: type_name(value) for key, value in fields.items()} == layout,
                    f"{type_id} layout does not match the DML adapter")

    def definition_signatures(self, type_ids: Set[str]) -> dict:
        if not self.mixed:
            require(self.declarations.keys() == type_ids | DEFINITIONS.keys() | {"scenario"},
                    "unsupported declarations in ref_rules")
            return {key: (qualifier, (arg,) if arg is not None else (), result)
                    for key, (qualifier, arg, result) in DEFINITIONS.items()}
        constructors = {"Absent": ("val", (), "Ref"), "Succeeded": ("val", (), "Outcome"),
                        "Target": ("def", ("str",), "Ref"), "Failed": ("def", ("str",), "Outcome")}
        signatures = dict(constructors)
        reserved = type_ids | constructors.keys() | {"scenario", "ruleIds"}
        require(reserved <= self.declarations.keys(), "missing declarations in mixed_ref_rules")
        for symbol in sorted(self.declarations.keys() - reserved):
            decl = self.declarations[symbol]
            annotation = decl.get("typeAnnotation")
            require(decl.get("qualifier") == "puredef" and annotation is not None and annotation["kind"] == "oper",
                    f"expected explicitly typed pure def: {symbol}")
            args = tuple(type_name(arg) for arg in annotation["args"])
            result = type_name(annotation["res"])
            require(1 <= len(args) <= 2 and set(args) <= {"str", "bool", "Attempt"}
                    and result in ("str", "bool"), f"unsupported signature for {symbol}")
            signatures[symbol] = ("puredef", args, result)
        require(signatures.get("verdict") == ("puredef", ("str", "Attempt"), "str"),
                "mixed verdict must take a rule ID and an attempt")
        return signatures

    def python_name(self, symbol: str) -> str:
        return name("_q_" if self.mixed and symbol != "verdict" else "", symbol)

    def resolves_to(self, node: dict, symbol: dict | None) -> bool:
        resolved = self.table.get(str(node["id"]))
        return symbol is not None and resolved is not None and resolved["id"] == symbol["id"]

    def expression(self, node: dict, params: tuple[dict, ...]) -> str:
        kind = node["kind"]
        if kind in ("str", "bool"):
            return repr(node["value"])
        if kind == "name":
            for index, param in enumerate(params):
                if self.resolves_to(node, param):
                    return "value" if index == 0 else "value1"
            symbol = node["name"]
            if symbol in ("Absent", self.success) and self.resolves_to(node, self.declarations[symbol]):
                return self.python_name(symbol)
            raise Unsupported(f"unsupported name {symbol!r}")
        require(kind == "app", f"unsupported expression kind {kind!r}")
        op, args = node["opcode"], node["args"]
        values = [self.expression(arg, params) for arg in args]
        if op == "Tup" and not args:
            return "()"
        if op == "variant" and len(args) == 2 and args[0]["kind"] == "str":
            return f"({values[0]}, {values[1]})"
        if op == "field" and len(args) == 2 and args[1]["kind"] == "str":
            return f"({values[0]})[{values[1]}]"
        if op in ("eq", "neq") and len(args) == 2:
            symbol = "==" if op == "eq" else "!="
            return f"({values[0]} {symbol} {values[1]})"
        if op == "and" and len(args) >= 2:
            return f"({' and '.join(values)})"
        if op == "not" and len(args) == 1:
            return f"(not {values[0]})"
        if op == "ite" and len(args) == 3:
            return f"({values[1]} if {values[0]} else {values[2]})"
        if op in self.signatures and args and len(args) == len(self.signatures[op][1]):
            require(self.resolves_to(node, self.declarations[op]), f"unresolved call to {op}")
            return f"{self.python_name(op)}({', '.join(values)})"
        raise Unsupported(f"unsupported operation {op!r}/{len(args)}")

    def definition(self, name: str) -> str:
        declaration = self.declarations[name]
        qualifier, arg_types, result_type = self.signatures[name]
        require(declaration["kind"] == "def" and declaration["qualifier"] == qualifier,
                f"unexpected qualifier for {name}")
        annotation, expr = declaration.get("typeAnnotation"), declaration["expr"]
        require(annotation is not None, f"expected an explicit type for {name}")
        symbol = self.python_name(name)
        if not arg_types:
            require(type_name(annotation) == result_type, f"unexpected type for {name}")
            return f"{symbol} = {self.expression(expr, ())}"
        require(annotation["kind"] == "oper" and tuple(type_name(arg) for arg in annotation["args"]) == arg_types
                and type_name(annotation["res"]) == result_type, f"unexpected signature for {name}")
        require(expr["kind"] == "lambda" and len(expr["params"]) == len(arg_types), f"unexpected lambda for {name}")
        parameters = ", ".join(("value", "value1")[:len(arg_types)])
        return f"def {symbol}({parameters}):\n    return {self.expression(expr['expr'], tuple(expr['params']))}"

    def emit(self) -> str:
        operations, targets, bound = scenario(self.declarations["scenario"], self.mixed)
        header = (
            f"# Generated from {self.module}.qnt by generate_python.py; do not edit.\n\n"
            "from collections import Counter\n\n"
            "from hypothesis import given, seed, settings, strategies as st\n\n"
        )
        binding = "exercise_refs" if self.mixed else f"exercise_{operations[0]}"
        header += f"from ref_binding import {binding} as exercise, observation\n\n\n"
        header += f"TARGETS = {targets!r}\nMAX_STEPS = {bound}\n"
        if self.mixed:
            registry = self.declarations["ruleIds"]
            require(registry.get("qualifier") == "pureval", "ruleIds must be a pure val")
            rule_ids = string_set(registry["expr"])
            require(1 <= len(rule_ids) <= 8 and all(rule.isascii() and rule.isidentifier() for rule in rule_ids),
                    "ruleIds must contain 1–8 ASCII identifiers")
            header += f"OPERATIONS = {operations!r}\nRULE_IDS = {rule_ids!r}\n"
        definitions = "\n\n\n".join(self.definition(name) for name in self.signatures)
        driver = MIXED_DRIVER if self.mixed else DRIVER
        return f"{header}\n\n{definitions}\n\n\n{driver}"


DRIVER = '''HISTORIES = st.lists(st.sampled_from(TARGETS), max_size=MAX_STEPS)


class RuleViolation(AssertionError):
    def __init__(self, requests, index, evidence):
        self.requests = tuple(requests)
        super().__init__(f"ref_rules.verdict: requests={self.requests!r}, step={index}, {evidence!r}")


def execute(requests):
    return exercise(TARGETS, requests)


def check(requests, attempts):
    if len(requests) != len(attempts):
        raise ValueError("Expected one DML observation per requested action")
    counts = Counter()
    for index, attempt in enumerate(attempts):
        evidence = observation(attempt)
        result = verdict(evidence)
        if result == "violation":
            raise RuleViolation(requests, index, evidence)
        if result not in ("pass", "unexercised"):
            raise ValueError(f"Unknown verdict: {result!r}")
        counts[result] += 1
    return counts
'''


MIXED_DRIVER = '''REQUESTS = st.tuples(st.sampled_from(OPERATIONS), st.sampled_from(TARGETS))
HISTORIES = st.lists(REQUESTS, max_size=MAX_STEPS)


class RuleViolation(AssertionError):
    def __init__(self, rule, requests, index, evidence):
        self.rule = rule
        self.requests = tuple(requests)
        super().__init__(f"{rule}: requests={self.requests!r}, step={index}, {evidence!r}")


def execute(requests):
    return exercise(TARGETS, requests)


def verdicts(attempt):
    evidence = observation(attempt, mixed=True)
    return {rule: verdict(rule, evidence) for rule in RULE_IDS}


def check(requests, attempts):
    if len(requests) != len(attempts):
        raise ValueError("Expected one DML observation per requested action")
    counts = Counter()
    for index, ((operation, _), attempt) in enumerate(zip(requests, attempts, strict=True)):
        if operation != attempt.operation:
            raise ValueError(f"Observation operation mismatch at step {index}")
        for rule, result in verdicts(attempt).items():
            if result == "violation":
                raise RuleViolation(rule, requests, index, observation(attempt, mixed=True))
            if result not in ("pass", "unexercised"):
                raise ValueError(f"Unknown verdict from {rule}: {result!r}")
            counts[rule, result] += 1
    return counts


def require_witnesses(counts):
    missing = [rule for rule in RULE_IDS if counts[rule, "pass"] == 0]
    if missing:
        raise AssertionError(f"Rules with no matching exercise in the suite: {', '.join(missing)}")
'''


PROPERTY_DRIVER = '''

def run_property(*, sample_seed, max_examples, corrupt=None):
    histories, counts = 0, Counter()

    @seed(sample_seed)
    @settings(max_examples=max_examples, database=None, deadline=None)
    @given(HISTORIES)
    def property_check(requests):
        nonlocal histories
        actual = execute(requests)
        try:
            counts.update(check(requests, actual))
        except RuleViolation as error:
            if corrupt is not None:
                raise RuntimeError(f"Real observations failed during the shrink control: {error}") from error
            raise
        if corrupt is not None:
            check(requests, corrupt(requests, actual))
        histories += 1

    property_check()
'''
DRIVER += PROPERTY_DRIVER + '''    if counts["pass"] == 0:
        raise AssertionError("ref_rules.verdict: no matching exercise in the suite")
    return histories, counts
'''
MIXED_DRIVER += PROPERTY_DRIVER + '''    require_witnesses(counts)
    return histories, counts
'''


def compile_ir(quint: Path, source: Path) -> dict:
    version = subprocess.run([quint, "--version"], check=True, capture_output=True, text=True, timeout=10)
    require(version.stdout.strip() == "0.33.1", f"expected Quint 0.33.1, got {version.stdout.strip()!r}")
    with TemporaryDirectory(prefix="quint-compile-") as tmp:
        report = Path(tmp) / "compiled.json"
        completed = subprocess.run(
            [quint, "compile", source, "--target=json", "--flatten=false", "--out", report],
            capture_output=True, text=True, timeout=15,
        )
        if completed.returncode != 0 or not report.is_file():
            detail = completed.stdout
            if report.is_file():
                detail = json.dumps(json.loads(report.read_text(encoding="utf-8"))["errors"])
            raise Unsupported(f"Quint compile failed (exit {completed.returncode}): {completed.stderr}{detail}")
        return json.loads(report.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path)
    parser.add_argument("--source", default=Path(__file__).with_name("ref_rules.qnt"), type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        code = Lowerer(compile_ir(args.quint.absolute(), args.source)).emit()
        compile(code, "<generated ref check>", "exec")
    except (Unsupported, subprocess.SubprocessError) as error:
        parser.exit(1, f"generation failed: {error}\n")
    args.out.write_text(code, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
