"""Native metadata/facade guards; no ordinary child launch or installed acceptance story."""

from pathlib import Path
import sys
import threading

import daggerml as d
from daggerml import builtin as b, calls as c, local
import pytest

ROOT = Path(__file__).resolve().parents[2]
_saved = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    import implementation_call_leaf as leaf
finally:
    sys.path[:] = _saved


@pytest.fixture
def metadata(tmp_path):
    path = tmp_path / "calls.dml"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        bindings = {"map": b.put_binding(tx, source_uri="dml://source/builtin/map/get/v1"),
                    "list": b.put_binding(tx, source_uri="dml://source/builtin/list/get/v1")}
        external = local.put_local_binding(tx, source=b"pass\n", interpreter=sys.executable, timeout_ms=1000)
        base = tx.put_commit(tx.put_tree({**bindings, "external": external}))
        tx.create_ref("main", base)
    return path, base, bindings, external


def test_actual_common_builtin_facade_conveniences_and_node_copy(metadata, monkeypatch):
    path, base, bindings, _ = metadata
    invoked = []
    original = c.Context.invoke
    def measured(self, target, arguments):
        invoked.append(target)
        return original(self, target, arguments)
    monkeypatch.setattr(c.Context, "invoke", measured)
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            with c.Context(leaf.RecorderBackend(rec)) as context:
                map_target = context.bind(kind="builtin", intent=b.MAP_GET, target=bindings["map"])
                list_target = context.bind(kind="builtin", intent=b.LIST_GET, target=bindings["list"])
                operations = context.operations(map_target=map_target, list_target=list_target)
                args = operations.arguments({"x": operations.literal(42)})
                got = operations.map_get(args, "x")
                assert got.value == d.Datum.i64(42)
                values = d.Datum.list((tx.put_datum(13), tx.put_datum(29)))
                selected = operations.list_get(operations.literal(values), 1)
                assert selected.value == d.Datum.i64(29)
                assert invoked == [map_target, list_target]
                assert len(rec.positions) == 2
                assert not hasattr(got, "__dict__") and not hasattr(operations, "load")
                assert not hasattr(context.calls, "bind")
                assert context.describe(got).dag == rec.positions[0]
    assert got.value == d.Datum.i64(42)  # Copied read remains available after closure.
    with pytest.raises(c.CallError, match="ended"):
        context.describe(got)


@pytest.mark.parametrize("fault", ["pre-enter", "re-enter", "foreign-node", "fabricated-node", "foreign-target", "fabricated-target",
    "non-map", "callback", "verifier", "old-result", "caught-reentry", "wrong-thread", "wrong-thread-exit", "bad-key", "bad-index"])
def test_caught_scope_callback_verifier_and_state_errors_poison_whole_writer(metadata, monkeypatch, fault):
    path, base, bindings, _ = metadata
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((c.CallError, b.BuiltinError)):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                backend = leaf.RecorderBackend(rec)
                context = c.Context(backend)
                if fault == "pre-enter":
                    with pytest.raises(c.CallError, match="entered"):
                        context.literal(1)
                    with context:
                        pass
                with context:
                    target = context.bind(kind="builtin", intent=b.MAP_GET, target=bindings["map"])
                    index = context.bind(kind="builtin", intent=b.LIST_GET, target=bindings["list"])
                    ops = context.operations(map_target=target, list_target=index)
                    args = context.arguments({"x": context.literal(42)})
                    native_args = context.arguments({"map": args, "key": context.literal("x")})
                    if fault == "foreign-node":
                        with c.Context(leaf.RecorderBackend(rec)) as other:
                            foreign = other.literal(42)
                    if fault == "foreign-target":
                        with c.Context(leaf.RecorderBackend(rec)) as other:
                            foreign = other.bind(kind="builtin", intent=b.MAP_GET, target=bindings["map"])
                    if fault == "callback":
                        def fail(*a):
                            raise ValueError("causal callback failure")
                        monkeypatch.setattr(backend, "perform", fail)
                    if fault == "verifier":
                        def fail(*a):
                            raise ValueError("causal verifier failure")
                        monkeypatch.setattr(backend, "verify", fail)
                    if fault == "old-result":
                        old = context.invoke(target, native_args)
                        old_description = context.describe(old)
                        old_perform = backend.perform
                        def wrong_result(*a):
                            old_perform(*a)  # Actual new call position; response still wrong association.
                            return old_description
                        monkeypatch.setattr(backend, "perform", wrong_result)
                    if fault == "caught-reentry":
                        old_perform = backend.perform
                        def catch_state(*a):
                            try:
                                context.invoke(target, native_args)
                            except c.CallError:
                                pass
                            return old_perform(*a)
                        monkeypatch.setattr(backend, "perform", catch_state)
                    actions = {
                        "re-enter": context.__enter__,
                        "foreign-node": lambda: context.describe(foreign),
                        "fabricated-node": lambda: context.describe(c.Node(d.Datum.i64(42))),
                        "foreign-target": lambda: context.invoke(foreign, native_args),
                        "fabricated-target": lambda: context.invoke(c.Target(), native_args),
                        "non-map": lambda: context.invoke(target, context.literal(42)),
                        "bad-key": lambda: ops.map_get(args, 1),
                        "bad-index": lambda: ops.list_get(args, True),
                    }
                    if fault in ("wrong-thread", "wrong-thread-exit"):
                        failures = []
                        def worker():
                            try:
                                context.__exit__(None, None, None) if fault.endswith("exit") else context.describe(args)
                            except c.CallError as error:
                                failures.append(str(error))
                        thread = threading.Thread(target=worker)
                        thread.start()
                        thread.join()
                        assert len(failures) == 1 and "thread" in failures[0]
                        # Recorder transaction still alive on owner; no foreign native cleanup.
                        assert tx.get_commit(base).tree is not None
                    else:
                        with pytest.raises((c.CallError, ValueError, TypeError)):
                            actions.get(fault, lambda: context.invoke(target, native_args))()
                    assert context.poisoned
                    with pytest.raises(c.CallError, match="poison"):
                        context.literal(1)
    assert (path / "data.mdb").read_bytes() == before


def test_native_constructor_reader_depth8_boundary_and_new_ordinary_edge_charge(metadata):
    path, base, _, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        environment = c.put_environment(tx)
        closure = c.put_closure(tx, intent=leaf.ADD, binding=binding, environment=environment)
        for level in range(8):
            environment = c.put_environment(tx, {"child": c.Capture("ordinary", leaf.ADD, closure)})
            closure = c.put_closure(tx, intent=leaf.ADD, binding=binding, environment=environment)
        assert c.inspect_closure(tx, closure).dag == closure
        retained = tx.put_commit(tx.put_tree({"depth8": closure}), parents=(base,))
        tx.create_ref("depth8", retained)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(c.CallError, match="depth"):
        with d.Repository(path) as repo, repo.write() as tx:
            c.put_environment(tx, {"child": c.Capture("ordinary", leaf.ADD, closure)})
    assert (path / "data.mdb").read_bytes() == before
    # Native storage accepts the complete well-typed DAG, but the structural reader rejects9.
    with d.Repository(path) as repo, repo.write() as tx:
        row = b.record(tx, c.CAPTURE_ROLE, values={"kind": "ordinary", "intent": d.Datum.uri(leaf.ADD)}, links={"target": closure})
        over = b.record(tx, c.ENVIRONMENT_ROLE, links={"child": row})
        assert tx.get_dag(over).root is not None
        with pytest.raises(c.CallError, match="depth"):
            c.inspect_environment(tx, over)
        tx.abort()


def test_structural_capture_unknown_version_not_executable_and_no_intent_environment_or_K(metadata):
    path, _, bindings, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        unknown = b.put_binding(tx, source_uri="dml://source/builtin/map/get/v99")
        environment = c.put_environment(tx, {"map-get": c.Capture("builtin", b.MAP_GET, unknown)})
        closure = c.put_closure(tx, intent=leaf.ADD, binding=binding, environment=environment)
        got = c.inspect_closure(tx, closure)
        assert dict(got.captures)["map-get"].target == unknown
        assert set(tx.get_dag(closure).bindings) == {"role", "intent", "binding", "environment"}
        assert got.binding == binding and not hasattr(got, "key")
        with pytest.raises(ValueError, match="shallow capture fields/root"):
            leaf.environment(tx, environment)
        complete_unknown = c.put_environment(tx, {"map-get": c.Capture("builtin", b.MAP_GET, unknown),
            "list-get": c.Capture("builtin", b.LIST_GET, bindings["list"])})
        with pytest.raises(ValueError, match="unsupported captured getter"):
            leaf.environment(tx, complete_unknown)
        with pytest.raises(c.CallError):
            c.put_environment(tx, [("x", c.Capture("builtin", b.MAP_GET, bindings["map"]))] * 2)
        with pytest.raises(c.CallError):
            c.put_environment(tx, {"role": c.Capture("builtin", b.MAP_GET, bindings["map"])})
        with pytest.raises(c.CallError):
            c.put_environment(tx, {"constant": c.Capture("constant", leaf.ADD, binding)})
        with pytest.raises(c.CallError):
            c.put_environment(tx, {"wrong": c.Capture("ordinary", leaf.DOUBLE, closure)})
        with pytest.raises(c.CallError):
            c.put_closure(tx, intent="URN:example:noncanonical", binding=binding, environment=environment)


def test_canonical_copied_NaN_and_typed_finite_equality():
    assert c.same_value(d.Datum.f64(float("nan")), d.Datum.f64(float("nan")))
    assert not c.same_value(d.Datum.f64(42.0), d.Datum.i64(42))
    assert not c.same_value(d.Datum.f64(42.0), d.Datum.f64(43.0))
    assert not c.same_value(42, d.Datum.i64(42))
