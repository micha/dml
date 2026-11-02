"""Two cooperative value-only node funcs; Python arithmetic is explicit, not a builtin."""

from daggerml import Datum


def add(arguments, ops):
    a = ops.map_get(arguments, "a")
    b = ops.map_get(arguments, "b")
    if a.value.kind != "i64" or b.value.kind != "i64":
        raise ValueError("add requires exact I64 operands")
    return ops.literal(Datum.i64(a.value.value + b.value.value))


def double(arguments, ops):
    x = ops.map_get(arguments, "x")
    if x.value.kind != "i64":
        raise ValueError("double requires an exact I64 operand")
    return ops.literal(Datum.i64(x.value.value * 2))
