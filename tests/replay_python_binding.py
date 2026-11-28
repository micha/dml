"""Typed operands and Python-level observations for the public core binding."""

import re

from replay_core import CoreHistory, NO_RESULT, Operation, Suite


class BindingHistory(CoreHistory):
    @staticmethod
    def operation(op, args):
        if op == "datum_encode" and len(args) >= 4 and args[1] == "py":
            return Operation(("datum_kind",) + ("python",) * (len(args) - 2), "packed")
        if op == "repo_open" and len(args) == 3:
            return Operation(("path", "create", "int"), "repo")
        if op == "datum_members":
            return Operation(("packed",), "members")
        return CoreHistory.operation(op, args)

    def primary_repo(self, kind, arg):
        if kind == "txn" and arg.startswith("py:repo:"):
            return arg.removeprefix("py:repo:")
        if kind == "path":
            return arg.removesuffix("~nul")
        return super().primary_repo(kind, arg)

    def operands(self, op, spec, args):
        if spec.inputs[-1] == "python":
            return [self.resolve("datum_kind", args[0]), self.typed_value(args[2:-1])]
        return super().operands(op, spec, args)

    def resolve(self, kind, arg):
        if arg.startswith("py:"):
            return self.typed_value([arg[3:]])
        if kind == "path":
            if arg.endswith("~nul"):
                return bytes(self.path(arg[:-4])) + b"\0suffix"
            return self.path(arg)
        return super().resolve(kind, arg)

    def typed_value(self, operands):
        """Decode a prefix expression, e.g. ["tuple:2", "int:1", "bytes:ff"]."""
        tokens = iter(operands)

        def read():
            token = next(tokens)
            tag, _, text = token.partition(":")
            if tag in ("list", "tuple", "iter", "set", "dict"):
                size = int(text)
                if size < 0:
                    raise ValueError("negative Python container size")
                if tag == "dict":
                    return {read(): read() for _ in range(size)}
                items = [read() for _ in range(size)]
                return {"list": list, "tuple": tuple, "iter": iter, "set": set}[tag](items)
            if tag == "repo":
                return self.resolve(tag, text)
            if tag in ("short_id", "text_id", "mutable_packed", "short_packed"):
                if tag == "short_id":
                    return self.resolve("id", text)[:-1]
                if tag == "text_id":
                    return self.resolve("id", text).hex().encode("ascii")
                packed = self.resolve("packed", text)
                return bytearray(packed) if tag == "mutable_packed" else packed[:-1]
            if tag == "bytes":
                return bytes.fromhex(text)
            if tag == "bytearray":
                return bytearray.fromhex(text)
            if tag == "str":
                return bytes.fromhex(text).decode("utf-8")
            if tag in ("int", "float"):
                return {"int": int, "float": float}[tag](text)
            raise ValueError(f"unknown Python operand {token!r}")

        try:
            value = read()
        except StopIteration as error:
            raise ValueError("incomplete Python operand") from error
        if next(tokens, None) is not None:
            raise ValueError("trailing Python operand tokens")
        return value

    def invoke(self, op, spec, operands):
        call = getattr(self.core, op)
        facts = dict(errorClass="", errorTypes=[], nativeCode=0, resultTypes=[])
        try:
            result = call(*operands)
        except (self.core.Error, TypeError, ValueError, OverflowError) as error:
            facts["errorClass"] = type(error).__name__
            facts["errorTypes"] = [type(arg).__name__ for arg in error.args]
            status, detail = "python_error", str(error)
            if type(error) is self.core.Error and facts["errorTypes"] == ["str", "int", "str"]:
                status, facts["nativeCode"], detail = error.args
            if not re.fullmatch(r"[\x20-\x21\x23-\x5b\x5d-\x7e]*", detail):
                detail = "hex:" + detail.encode("utf-8").hex()
            return status, detail, NO_RESULT, facts
        facts["resultTypes"] = result_types(result)
        return "ok", "", result, facts

    def observe_output(self, output, alias, status, result):
        if output == "members":
            members = [item.hex() for member in result for item in
                       (member if isinstance(member, tuple) else (member,))]
            return "", len(result), members
        return super().observe_output(output, alias, status, result)

    def run(self, op, *args):
        row = super().run(op, *args, include_error_detail=True)
        return {**row, "paths": sorted(path.name for path in self.directory.iterdir())}


def result_types(value):
    if type(value) is tuple:
        return [f"tuple:{len(value)}", *(kind for item in value for kind in result_types(item))]
    return [type(value).__name__]


class BindingSuite(Suite):
    history_type = BindingHistory
    operations = (*Suite.operations, "datum_members")

    def __init__(self, binding, scanner):
        if binding != "daggerml.core":
            raise ValueError("Python boundary replay requires the public binding")
        super().__init__(binding, scanner)
