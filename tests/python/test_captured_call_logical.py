"""Actual fixed logical source consumes getter results before supplied ordinary interface."""

from types import SimpleNamespace

import daggerml as d
import pytest

from test_captured_calls import bridge, logical


def test_fixed_logical_FORWARDS_original_node_then_exact_returned_add_node():
    original, summed, doubled, downstream = object(), object(), object(), object()
    add, double = object(), object()
    events = []
    def get(node, key):
        assert node is original
        events.append(("get", key))
        return bridge.Node(d.Datum.i64(13 if key == "a" else 29))
    def arguments(entries):
        assert entries == {"x": summed}
        events.append(("arguments", summed))
        return downstream
    def invoke(target, node):
        if target is add:
            assert node is original
            events.append(("invoke-add", node))
            return summed
        assert target is double and node is downstream
        events.append(("invoke-double", node))
        return doubled
    func = logical.double_sum(add, double, SimpleNamespace(map_get=get, arguments=arguments), SimpleNamespace(invoke=invoke))
    assert func(original) is doubled
    assert events == [("get", "a"), ("get", "b"), ("invoke-add", original), ("arguments", summed), ("invoke-double", downstream)]


@pytest.mark.parametrize("key,value", [("a", d.Datum.bool(True)), ("b", d.Datum.f64(29.0)), ("a", d.Datum.string("13"))])
def test_getter_result_I64_guard_precedes_ANY_ordinary_call(key, value):
    original = object()
    def get(node, name):
        assert node is original
        return bridge.Node(value if name == key else d.Datum.i64(1))
    def forbidden(*args):
        pytest.fail("invalid actual getter result MUST stop before ordinary invoke/arguments")
    func = logical.double_sum(object(), object(), SimpleNamespace(map_get=get, arguments=forbidden), SimpleNamespace(invoke=forbidden))
    with pytest.raises(ValueError, match="I64"):
        func(original)
