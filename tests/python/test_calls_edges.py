"""Meaningful native structural shapes, constructor prevalidation and copied-state edges."""

from dataclasses import replace

import daggerml as d
from daggerml import builtin as b, calls as c
import pytest

from test_calls import metadata, leaf
from test_exchange_records import clone


@pytest.mark.parametrize("fault", ["adapter", "source-kind", "source-empty", "interpreter", "timeout", "environment", "role", "root", "extra"])
def test_native_inprocess_binding_structure_exact(metadata, fault):
    path, _, _, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        binding = b.record(tx, c.INPROCESS_ROLE, values={"adapter": d.Datum.uri("urn:example:inprocess"),
            "source": b"fixed source", "interpreter": None, "timeout-ms": None}, links={"environment": env})
        assert c.inspect_closure(tx, c.put_closure(tx, intent=leaf.ADD, binding=binding, environment=env)).environment == env
        changes, root = {}, None
        if fault == "adapter":
            changes["adapter"] = b.literal(tx, "not URI")
        elif fault.startswith("source"):
            changes["source"] = b.literal(tx, 1 if fault == "source-kind" else b"")
        elif fault in ("interpreter", "timeout"):
            changes["interpreter" if fault == "interpreter" else "timeout-ms"] = b.literal(tx, 1)
        elif fault == "environment":
            different = b.record(tx, c.ENVIRONMENT_ROLE, links={"child": b.record(tx, c.CAPTURE_ROLE,
                values={"kind": "builtin", "intent": d.Datum.uri(b.MAP_GET)},
                links={"target": b.put_binding(tx, source_uri="dml://source/builtin/map/get/v1")})})
            changes["environment"] = tx.put_subdag(different)
        elif fault == "role":
            changes["role"] = b.literal(tx, "unsupported")
        elif fault == "root":
            root = tx.get_dag(binding).bindings["source"]
        else:
            changes["extra"] = b.literal(tx, 1)
        invalid = clone(tx, binding, fields=changes, root=root)
        with pytest.raises((c.CallError, b.BuiltinError)):
            c.put_closure(tx, intent=leaf.ADD, binding=invalid, environment=env)


@pytest.mark.parametrize("fault", ["capture-kind", "capture-intent", "capture-type", "target-type", "too-many", "name", "late-invalid"])
def test_constructor_checks_ALL_captures_before_any_native_put(metadata, monkeypatch, fault):
    path, _, bindings, binding = metadata
    valid = c.Capture("builtin", b.MAP_GET, bindings["map"])
    with d.Repository(path) as repo, repo.write() as tx:
        cases = {
            "capture-kind": {"wrong": c.Capture("constant", leaf.ADD, binding)},
            "capture-intent": {"wrong": c.Capture("builtin", "URN:example:noncanonical", bindings["map"])},
            "capture-type": {"wrong": object()},
            "target-type": {"wrong": c.Capture("builtin", b.MAP_GET, str(bindings["map"]))},
            "too-many": [("x%d" % n, valid) for n in range(17)],
            "name": {"non ascii": valid},
            "late-invalid": [("first-valid", valid), ("later-invalid", object())],
        }
        recorded = []
        original = b.record
        def tracked(*a, **k):
            recorded.append(k)
            return original(*a, **k)
        monkeypatch.setattr(b, "record", tracked)
        with pytest.raises((c.CallError, TypeError)):
            c.put_environment(tx, cases[fault])
        assert recorded == []


@pytest.mark.parametrize("fault", ["kind", "intent", "name", "extra", "root", "depth-type"])
def test_structural_reader_rejects_native_malformed_capture(metadata, fault):
    path, _, bindings, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx, {"get": c.Capture("builtin", b.MAP_GET, bindings["map"])})
        row = b.link(tx, tx.get_dag(env).bindings["get"])
        if fault == "depth-type":
            with pytest.raises(c.CallError, match="depth"):
                c.inspect_environment(tx, env, depth=True)
            with pytest.raises(c.CallError, match="depth"):
                c.inspect_closure(tx, c.put_closure(tx, intent=leaf.ADD, binding=binding, environment=env), depth=9)
            return
        if fault == "kind":
            invalid_row = clone(tx, row, fields={"kind": b.literal(tx, "unsupported")})
        elif fault == "intent":
            child_env = c.put_environment(tx)
            child = c.put_closure(tx, intent=leaf.ADD, binding=binding, environment=child_env)
            invalid_row = b.record(tx, c.CAPTURE_ROLE, values={"kind": "ordinary", "intent": d.Datum.uri(leaf.DOUBLE)}, links={"target": child})
        elif fault == "extra":
            invalid_row = clone(tx, row, fields={"extra": b.literal(tx, 1)})
        elif fault == "root":
            invalid_row = clone(tx, row, root=tx.get_dag(row).bindings["kind"])
        else:
            invalid_row = row
        if fault == "name":
            # Native codec rejects this name BEFORE any structural reader can consume it.
            # This is native authoring assurance, not a fabricated reader-path pass.
            with pytest.raises(d.DmlError, match="name_profile"):
                b.record(tx, c.ENVIRONMENT_ROLE, links={"name with spaces": invalid_row})
            tx.abort()
            return
        invalid = b.record(tx, c.ENVIRONMENT_ROLE, links={"get": invalid_row})
        with pytest.raises((c.CallError, b.BuiltinError)):
            c.inspect_environment(tx, invalid)


@pytest.mark.parametrize("fault", ["non-description", "wrong-datum", "wrong-dag", "wrong-value", "wrong-type", "caught-read-state"])
def test_native_result_revalidation_and_caught_read_state_error_poison(metadata, monkeypatch, fault):
    path, base, bindings, _ = metadata
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(c.CallError):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as recorder:
                backend = leaf.RecorderBackend(recorder)
                with c.Context(backend) as context:
                    node = context.literal(42)
                    actual = context.describe(node)
                    if fault == "caught-read-state":
                        original_read = backend.read
                        active = [False]
                        def caught_read(dag):
                            if not active[0]:
                                active[0] = True
                                try:
                                    context.__enter__()
                                except c.CallError:
                                    pass
                                finally:
                                    active[0] = False
                            return original_read(dag)
                        monkeypatch.setattr(backend, "read", caught_read)
                        with pytest.raises(c.CallError, match="poison"):
                            context.describe(node)
                    else:
                        target = context.bind(kind="builtin", intent=b.MAP_GET, target=bindings["map"])
                        args = context.arguments({"map": context.arguments({"x": node}), "key": context.literal("x")})
                        source = context.describe(args)
                        wrong = {"non-description": node,
                            "wrong-datum": replace(actual, datum=source.datum),
                            "wrong-dag": replace(actual, dag=source.dag),
                            "wrong-value": replace(actual, value=d.Datum.i64(43)),
                            "wrong-type": replace(actual, dag="not an ObjectId")}[fault]
                        # TEST-PRIVATE verifier response replacement; independent native reread must reject.
                        monkeypatch.setattr(backend, "verify", lambda *a: wrong)
                        with pytest.raises(c.CallError, match="Description|description|differs"):
                            context.invoke(target, args)
                    assert context.poisoned
    assert (path / "data.mdb").read_bytes() == before


def test_scope_exit_requires_entered_unfinished_context():
    context = c.Context(object())
    with pytest.raises(c.CallError, match="entered"):
        context.__exit__(None, None, None)
    assert context.poisoned
    with c.Context(object()) as context:
        pass
    with pytest.raises(c.CallError, match="unfinished"):
        context.__exit__(None, None, None)
