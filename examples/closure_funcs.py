"""Fixed value-only Python closure; cooperative interface, not a sandbox."""

from daggerml import Datum


def scaled_sum(scale, ops):
    """Capture THIS recorder's scale handle/ops; invocation supplies only arguments."""
    if scale.value.kind != "i64":
        raise ValueError("captured scale must be I64")

    def invoke(arguments):
        a, b = ops.map_get(arguments, "a"), ops.map_get(arguments, "b")
        if a.value.kind != "i64" or b.value.kind != "i64":
            raise ValueError("a,b must be I64")
        total = Datum.i64(a.value.value + b.value.value)
        return ops.literal(Datum.i64(total.value * scale.value.value))

    return invoke
