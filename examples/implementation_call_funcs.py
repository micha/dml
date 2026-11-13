"""ONE fixed node-to-node composition; value checks precede either ordinary call."""


def double_sum(add, double, nodes, calls):
    def invoke(arguments):
        a = nodes.map_get(arguments, "a")
        b = nodes.map_get(arguments, "b")
        if a.value.kind != "i64" or b.value.kind != "i64":
            raise ValueError("double_sum requires exact a,b I64")
        # The original node is intentionally forwarded, not rebuilt from getter values.
        summed = calls.invoke(add, arguments)
        return calls.invoke(double, nodes.arguments({"x": summed}))
    return invoke
