"""Lower a narrow context-completion profile, reusing checked transaction predicates."""

import argparse
from pathlib import Path
import subprocess

from generate_python import (
    Unsupported, closed_fields, compile_ir, literal, operands, require, scenario, string_set,
    type_name,
)
from generate_transactions import DRIVER, TransactionLowerer


class ContextLowerer(TransactionLowerer):
    def __init__(self, ir: dict) -> None:
        require(ir["stage"] == "compiling" and not ir["errors"], "expected checked compile output")
        modules = {module["name"]: module for module in ir["modules"]}
        require(len(ir["modules"]) == 2 and modules.keys() == {"transaction_rules", "context_rules"}
                and ir["main"] == "context_rules", "expected only context_rules and transaction_rules")
        context = modules["context_rules"]
        imports = [decl for decl in context["declarations"] if decl["kind"] == "import"]
        require(len(imports) == 1 and {key: value for key, value in imports[0].items() if key != "id"} == {
            "kind": "import", "defName": "*", "protoName": "transaction_rules",
            "fromSource": "./transaction_rules",
        }, "expected the single unqualified transaction_rules import")
        super().__init__({**ir, "main": "transaction_rules", "modules": [modules["transaction_rules"]]})
        declarations = [decl for decl in context["declarations"] if decl["kind"] != "import"]
        require(all("name" in decl for decl in declarations), "unsupported context declaration")
        extra = {decl["name"]: decl for decl in declarations}
        require(len(extra) == len(declarations) and not (extra.keys() & self.declarations.keys()),
                "context declarations must not shadow transaction declarations")
        reserved = {"Context", "contextScenario", "contextRuleIds"}
        require(reserved <= extra.keys(), "missing context declarations")
        context_type = extra["Context"]
        require(context_type["kind"] == "typedef" and context_type["type"]["kind"] == "rec",
                "expected the Context record")
        require({key: type_name(value) for key, value in
                 closed_fields(context_type["type"]["fields"]).items()} == {
                     "batch": "Attempt", "exception": "str",
                 }, "Context layout does not match the context adapter")
        self.declarations.update(extra)
        # The context entry point replaces, rather than translates, explicit endings.
        del self.signatures["verdict"]
        for symbol in sorted(extra.keys() - reserved):
            decl = extra[symbol]
            annotation = decl.get("typeAnnotation")
            require(decl.get("qualifier") == "puredef" and annotation is not None
                    and annotation["kind"] == "oper", f"expected explicitly typed pure def: {symbol}")
            args = tuple(type_name(arg) for arg in annotation["args"])
            result = type_name(annotation["res"])
            require(1 <= len(args) <= 2 and set(args) <= {"str", "bool", "Context"}
                    and result in ("str", "bool"), f"unsupported context signature: {symbol}")
            self.signatures[symbol] = ("puredef", args, result)
        require(self.signatures.get("contextVerdict") == ("puredef", ("str", "Context"), "str"),
                "contextVerdict must take a rule ID and context evidence")

    def python_name(self, symbol: str) -> str:
        return "verdict" if symbol == "contextVerdict" else super().python_name(symbol)

    def emit(self) -> str:
        declaration = self.declarations["contextScenario"]
        require(declaration.get("qualifier") == "pureval", "contextScenario must be a pure val")
        args = operands(declaration["expr"], "Rec", 8)
        fields = {literal(key, "str"): value for key, value in zip(args[::2], args[1::2], strict=True)}
        require(fields.keys() == {"operations", "targets", "maxSteps", "finishes"},
                "unsupported context scenario fields")
        finishes = string_set(fields["finishes"])
        require(finishes == ("exception", "normal"), "context profile requires normal and exceptional exit")
        base_args = [arg for key, value in zip(args[::2], args[1::2], strict=True)
                     if key["value"] != "finishes" for arg in (key, value)]
        operations, targets, bound = scenario(
            {**declaration, "expr": {**declaration["expr"], "args": base_args}}, True,
        )
        require(bound <= 4, "context scenario exceeds the spike history bound")
        registry = self.declarations["contextRuleIds"]
        require(registry.get("qualifier") == "pureval", "contextRuleIds must be a pure val")
        rule_ids = string_set(registry["expr"])
        require(1 <= len(rule_ids) <= 8 and all(rule.isascii() and rule.isidentifier() for rule in rule_ids),
                "contextRuleIds must contain 1–8 ASCII identifiers")
        header = (
            "# Generated from context_rules.qnt and transaction_rules.qnt; do not edit.\n\n"
            "from collections import Counter\nfrom functools import reduce as _reduce\n\n"
            "from hypothesis import given, seed, settings, strategies as st\n\n"
            "from context_binding import exercise_context as exercise_transaction, validate_observation\n\n\n"
            f"TARGETS = {targets!r}\nOPERATIONS = {operations!r}\nMAX_STEPS = {bound}\n"
            f"FINISHES = {finishes!r}\nRULE_IDS = {rule_ids!r}\n"
        )
        definitions = "\n\n\n".join(self.definition(symbol) for symbol in self.signatures)
        return f"{header}\n\n{definitions}\n\n\n{DRIVER}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path)
    parser.add_argument("--source", default=Path(__file__).with_name("context_rules.qnt"), type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        code = ContextLowerer(compile_ir(args.quint.absolute(), args.source)).emit()
        compile(code, "<generated context check>", "exec")
    except (Unsupported, subprocess.SubprocessError) as error:
        parser.exit(1, f"generation failed: {error}\n")
    args.out.write_text(code, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
