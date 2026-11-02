"""Logical datum-only callables for the fixed recorded-map example."""

import daggerml as d


def add(arguments, values):
    left = values.map_get(arguments, "left")
    right = values.map_get(arguments, "right")
    if left.kind != "i64" or right.kind != "i64":
        raise ValueError("add requires I64 arguments")
    return d.Datum.i64(left.value + right.value)


def double(arguments, values):
    value = values.map_get(arguments, "x")
    if value.kind != "i64":
        raise ValueError("double requires I64 argument")
    return d.Datum.i64(value.value * 2)
