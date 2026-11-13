"""Native structural/capability/laundering guards with exact Context error scopes."""

import daggerml as d
from daggerml import builtin as b, calls as c
import pytest

from test_calls import metadata, leaf


def test_fresh_Context_rebind_retained_node_and_bound_public_Calls_invoke(metadata):
    path, base, bindings, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as recorder:
            with c.Context(leaf.RecorderBackend(recorder)) as context:
                old = context.literal(42)
                dag = context.describe(old).dag
            entries = dict(tx.get_tree(tx.get_commit(base).tree))
            entries["actual-source"] = dag
            retained = tx.put_commit(tx.put_tree(entries), parents=(base,))
    assert old.value == d.Datum.i64(42)
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=retained) as recorder:
            with c.Context(leaf.RecorderBackend(recorder)) as context:
                source = context.load(dag)
                assert source is not old and source.value == old.value
                full = context.arguments({"x": source})
                target = context.bind(kind="builtin", intent=b.MAP_GET, target=bindings["map"])
                result = context.calls.invoke(target, context.arguments({"map": full, "key": context.literal("x")}))
                assert result.value == d.Datum.i64(42)
                assert len(recorder.positions) == 1


def test_external_structural_adapter_interpreter_limits_and_native_capture17(metadata):
    path, _, bindings, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        for adapter, interpreter, timeout, message in (("urn:other:adapter", "/python", 1, "adapter"),
            ("urn:daggerml:local-python-v1", "relative-python", 1, "interpreter"),
            ("urn:daggerml:local-python-v1", "/python", 0, "timeout")):
            bad = b.record(tx, "local-python-binding-v1", values={"adapter": d.Datum.uri(adapter), "source": b"pass",
                "interpreter": interpreter, "timeout-ms": timeout})
            with pytest.raises(c.CallError, match=message):
                c.put_closure(tx, intent=leaf.ADD, binding=bad, environment=env)
        row = b.record(tx, c.CAPTURE_ROLE, values={"kind": "builtin", "intent": d.Datum.uri(b.MAP_GET)}, links={"target": bindings["map"]})
        env17 = b.record(tx, c.ENVIRONMENT_ROLE, links={"get%02d" % i: row for i in range(17)})
        with pytest.raises(c.CallError, match="exceeds16"):
            c.inspect_environment(tx, env17)


@pytest.mark.parametrize("fault", ["bind-kind", "argument17", "operations-target", "laundered-value"])
def test_capability_and_argument_bounds_laundering_abort_native_writer(metadata, fault):
    path, base, bindings, _ = metadata
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(c.CallError, match="poison"):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                with c.Context(leaf.RecorderBackend(rec)) as context:
                    node = context.literal(42)
                    map_target = context.bind(kind="builtin", intent=b.MAP_GET, target=bindings["map"])
                    index = context.bind(kind="builtin", intent=b.LIST_GET, target=bindings["list"])
                    if fault == "laundered-value":
                        node._Node__value = d.Datum.i64(43)  # TEST-PRIVATE copied handle corruption, native42 remains.
                    actions = {"bind-kind": lambda: context.bind(kind="arbitrary", intent=leaf.ADD, target=bindings["map"]),
                        "argument17": lambda: context.arguments({"a%d" % i: node for i in range(17)}),
                        "operations-target": lambda: context.operations(map_target=c.Target(), list_target=index),
                        "laundered-value": lambda: context.describe(node)}
                    with pytest.raises(c.CallError):
                        actions[fault]()
    assert (path / "data.mdb").read_bytes() == before
