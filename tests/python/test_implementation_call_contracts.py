"""Fixed logical type/range contracts and supported capture/source wiring; not OS evidence."""

from types import SimpleNamespace

import daggerml as d
from daggerml import builtin as b, calls as c
import pytest

from test_exchange_records import clone
from test_implementation_calls import initial, p, adapter, bridge, leaf, funcs, logical
from test_calls import metadata


def test_fixed_logical_TYPE_guards_before_ordinary_or_arithmetic():
    outer = logical
    def forbidden(*a, **k):
        pytest.fail("wrong type must reject before invoke/literal/arithmetic")
    for value in (d.Datum.bool(True), d.Datum.f64(42.0)):
        ops = SimpleNamespace(map_get=lambda *a: c.Node(value), arguments=forbidden, literal=forbidden)
        with pytest.raises(ValueError, match="I64"):
            outer.double_sum(object(), object(), ops, SimpleNamespace(invoke=forbidden))(object())
        with pytest.raises(ValueError, match="I64"):
            funcs.add(object(), ops)
        with pytest.raises(ValueError, match="I64"):
            funcs.double(object(), ops)
    ops = SimpleNamespace(map_get=lambda *a: c.Node(d.Datum.i64(2**63 - 1)), literal=forbidden)
    with pytest.raises(OverflowError):
        funcs.add(object(), ops)
    with pytest.raises(OverflowError):
        funcs.double(object(), ops)


def test_native_fixed_leaf_capture_kind_version_and_exact_source(initial):
    path, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, commit)
        got = leaf.inspect(tx, entries["add-A"], *leaf.sources())
        with pytest.raises(ValueError, match="unsupported fixed"):
            leaf.contract("urn:unknown")
        with pytest.raises(ValueError, match="source"):
            leaf.inspect(tx, entries["add-A"], leaf.sources()[0] + b"\n# wrong bytes", leaf.sources()[1])
        # Explicit native environment variants, not supplied membership flags.
        for fault in ("intent", "version"):
            target = entries["map-v1"] if fault == "intent" else b.put_binding(tx, source_uri="dml://source/builtin/map/get/v99")
            environment = c.put_environment(tx, {"map-get": c.Capture("builtin", b.LIST_GET if fault == "intent" else b.MAP_GET, target),
                "list-get": c.Capture("builtin", b.LIST_GET, entries["list-v1"])})
            with pytest.raises(ValueError):
                leaf.environment(tx, environment)


def test_leaf_Recorder_backend_has_NO_ordinary_dispatch_and_exact_native_position(metadata):
    path, base, bindings, binding = metadata
    with pytest.raises(c.CallError):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                backend = leaf.RecorderBackend(rec)
                ordinary = c.Bound("ordinary", leaf.ADD, binding)
                with pytest.raises(c.CallError, match="ordinary"):
                    backend.bind(ordinary)
                with pytest.raises(c.CallError, match="ordinary"):
                    backend.perform(ordinary, None)
                with pytest.raises(c.CallError, match="unsupported"):
                    backend.bind(c.Bound("builtin", b.MAP_EMPTY, bindings["map"]))
                with c.Context(backend) as ctx:
                    target = ctx.bind(kind="builtin", intent=b.MAP_GET, target=bindings["map"])
                    args = ctx.arguments({"map": ctx.arguments({"x": ctx.literal(42)}), "key": ctx.literal("x")})
                    actual = ctx.describe(args)
                    ctx.invoke(target, args)
                    receipt = backend.last
                    # Genuine extra native primitive through trusted Recorder authority makes
                    # backend's earlier occurrence receipt stale, even if content deduplicates.
                    rec.call(b.MAP_GET, bindings["map"], rec.load(actual.dag))
                    with pytest.raises(c.CallError, match="position"):
                        backend.verify(c.Bound("builtin", b.MAP_GET, bindings["map"]), actual, receipt)
                    receipt = backend.perform(c.Bound("builtin", b.MAP_GET, bindings["map"]), actual)
                    with pytest.raises(c.CallError, match="target/arguments"):
                        backend.verify(c.Bound("builtin", b.LIST_GET, bindings["map"]), actual, receipt)
                    raise c.CallError("expected contract error abort")


def test_entry_trusted_capabilities_cannot_bind_or_load_arbitrary_results(initial, tmp_path):
    path, commit = initial
    backend = adapter.EntryBackend(path, commit, "outer-A", "inputs", dict(control="fresh", add_control="fresh", double_control="fresh"),
        "outer", tmp_path / "NEVER", None)
    with pytest.raises(c.CallError, match="only THIS"):
        backend.bind(c.Bound("ordinary", p.INTENT, backend.closure["add"]["dag"]))
    with pytest.raises(c.CallError, match="arbitrary"):
        backend.read(backend.closure["dag"])
    with pytest.raises(c.CallError, match="fabricate"):
        backend.literal(42)
    with pytest.raises(c.CallError, match="prepared"):
        backend.arguments([])
    with pytest.raises(c.CallError, match="target/input"):
        backend.perform(c.Bound("ordinary", p.INTENT, backend.closure["add"]["dag"]), b.Description(backend.inputs, d.ObjectId(bytes(16)), d.Datum.map(())))
    assert not (tmp_path / "NEVER").exists()
