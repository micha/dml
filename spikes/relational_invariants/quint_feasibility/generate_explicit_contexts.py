"""Lower explicit-ending context rules using the checked transaction expression subset."""

import argparse
from pathlib import Path
import subprocess

from generate_python import (
    Unsupported, closed_fields, compile_ir, literal, operands, require, scenario, string_set,
    type_name,
)
from generate_transactions import DRIVER, TransactionLowerer


LAYOUT = {
    "batch": "Attempt", "explicit": "Outcome", "exception": "str",
    "endedRef": "Ref", "endedMarker": "bool", "endRead": "Outcome", "endWrite": "Outcome",
    "endCommit": "Outcome", "endAbort": "Outcome", "exitCalls": "int",
}


class ExplicitContextLowerer(TransactionLowerer):
    def __init__(self, ir: dict) -> None:
        require(ir["stage"] == "compiling" and not ir["errors"], "expected checked compile output")
        modules = {module["name"]: module for module in ir["modules"]}
        require(len(ir["modules"]) == 2 and modules.keys() == {"transaction_rules", "explicit_context_rules"}
                and ir["main"] == "explicit_context_rules",
                "expected only explicit_context_rules and transaction_rules")
        context = modules["explicit_context_rules"]
        imports = [decl for decl in context["declarations"] if decl["kind"] == "import"]
        require(len(imports) == 1 and {key: value for key, value in imports[0].items() if key != "id"} == {
            "kind": "import", "defName": "*", "protoName": "transaction_rules",
            "fromSource": "./transaction_rules",
        }, "expected the single unqualified transaction_rules import")
        super().__init__({**ir, "main": "transaction_rules", "modules": [modules["transaction_rules"]]})
        declarations = [decl for decl in context["declarations"] if decl["kind"] != "import"]
        require(all("name" in decl for decl in declarations), "unsupported explicit context declaration")
        extra = {decl["name"]: decl for decl in declarations}
        require(len(extra) == len(declarations) and not (extra.keys() & self.declarations.keys()),
                "explicit context declarations must not shadow transaction declarations")
        reserved = {"ExplicitContext", "explicitContextScenario", "explicitContextRuleIds"}
        require(reserved <= extra.keys(), "missing explicit context declarations")
        record = extra["ExplicitContext"]
        require(record["kind"] == "typedef" and record["type"]["kind"] == "rec",
                "expected the ExplicitContext record")
        fields = closed_fields(record["type"]["fields"])
        # Integers are supported only as this recorded counter's field type;
        # arithmetic or integer function signatures are not newly supported.
        require({key: "int" if value["kind"] == "int" else type_name(value)
                 for key, value in fields.items()} == LAYOUT,
                "ExplicitContext layout does not match the explicit context adapter")
        self.declarations.update(extra)
        del self.signatures["verdict"]
        for symbol in sorted(extra.keys() - reserved):
            decl = extra[symbol]
            annotation = decl.get("typeAnnotation")
            require(decl.get("qualifier") == "puredef" and annotation is not None
                    and annotation["kind"] == "oper", f"expected explicitly typed pure def: {symbol}")
            args = tuple(type_name(arg) for arg in annotation["args"])
            result = type_name(annotation["res"])
            require(1 <= len(args) <= 2 and set(args) <= {"str", "bool", "ExplicitContext"}
                    and result in ("str", "bool"), f"unsupported explicit context signature: {symbol}")
            self.signatures[symbol] = ("puredef", args, result)
        require(self.signatures.get("explicitContextVerdict") == ("puredef", ("str", "ExplicitContext"), "str"),
                "explicitContextVerdict must take a rule ID and explicit context evidence")

    def python_name(self, symbol: str) -> str:
        return "verdict" if symbol == "explicitContextVerdict" else super().python_name(symbol)

    def emit(self) -> str:
        declaration = self.declarations["explicitContextScenario"]
        require(declaration.get("qualifier") == "pureval", "explicitContextScenario must be a pure val")
        args = operands(declaration["expr"], "Rec", 8)
        fields = {literal(key, "str"): value for key, value in zip(args[::2], args[1::2], strict=True)}
        require(fields.keys() == {"operations", "targets", "maxSteps", "finishes"},
                "unsupported explicit context scenario fields")
        finishes = string_set(fields["finishes"])
        require(finishes == ("abort_exception", "abort_normal", "commit_exception", "commit_normal"),
                "explicit context profile requires commit/abort with normal/exceptional exit")
        base_args = [arg for key, value in zip(args[::2], args[1::2], strict=True)
                     if key["value"] != "finishes" for arg in (key, value)]
        operations, targets, bound = scenario(
            {**declaration, "expr": {**declaration["expr"], "args": base_args}}, True,
        )
        require(bound <= 4, "explicit context scenario exceeds the spike history bound")
        registry = self.declarations["explicitContextRuleIds"]
        require(registry.get("qualifier") == "pureval", "explicitContextRuleIds must be a pure val")
        rule_ids = string_set(registry["expr"])
        require(1 <= len(rule_ids) <= 9 and all(rule.isascii() and rule.isidentifier() for rule in rule_ids),
                "explicitContextRuleIds must contain 1–9 ASCII identifiers")
        header = (
            "# Generated from explicit_context_rules.qnt and transaction_rules.qnt; do not edit.\n\n"
            "from collections import Counter\nfrom functools import reduce as _reduce\n\n"
            "from hypothesis import given, seed, settings, strategies as st\n\n"
            "from explicit_context_binding import "
            "exercise_explicit_context as exercise_transaction, validate_observation\n\n\n"
            f"TARGETS = {targets!r}\nOPERATIONS = {operations!r}\nMAX_STEPS = {bound}\n"
            f"FINISHES = {finishes!r}\nRULE_IDS = {rule_ids!r}\n"
        )
        definitions = "\n\n\n".join(self.definition(symbol) for symbol in self.signatures)
        return f"{header}\n\n{definitions}\n\n\n{DRIVER}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path)
    parser.add_argument("--source", default=Path(__file__).with_name("explicit_context_rules.qnt"), type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        code = ExplicitContextLowerer(compile_ir(args.quint.absolute(), args.source)).emit()
        compile(code, "<generated explicit context check>", "exec")
    except (Unsupported, subprocess.SubprocessError) as error:
        parser.exit(1, f"generation failed: {error}\n")
    args.out.write_text(code, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
