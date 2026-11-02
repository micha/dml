"""Logical node-to-node sum-pair; no implicit graph/provenance interface."""

import daggerml as d


def sum_pair(arguments, ops):
    sample = ops.map_get(arguments, "sample")
    measurements = ops.map_get(sample, "measurements")
    left = ops.list_get(measurements, 0)
    right = ops.list_get(measurements, 1)
    if left.value.kind != "i64" or right.value.kind != "i64":
        raise ValueError("sum_pair requires I64 measurements")
    return ops.literal(d.Datum.i64(left.value.value + right.value.value))
