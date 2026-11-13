"""Approved finite six native metadata families; exact malformed fields and rejection stages."""

import daggerml as d
from daggerml import builtin as b, calls as c
import pytest

from test_calls import metadata, leaf
from test_exchange_records import clone


def test_native_scalar_wrong_kind_is_not_copy_coercion(metadata):
    path, _, _, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        node = b.literal(tx, 42)
        with pytest.raises(b.BuiltinError, match="wrong scalar kind: expected string"):
            c._StructureWalk(tx).scalar(node, "string")


def test_actual_native_C_fields_root_and_role_reject_within_valid_size_bound(metadata):
    path, _, _, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        good = c.put_closure(tx, intent=leaf.ADD, binding=binding, environment=env)
        for fault in ("fields", "root", "role"):
            fields = dict(tx.get_dag(good).bindings)
            root = fields["role"]
            if fault == "fields":
                del fields["binding"]
            elif fault == "root":
                root = fields["intent"]
            else:
                fields["role"] = root = b.literal(tx, "unsupported")
            bad = tx.put_dag(root=root, bindings=fields)
            assert len(tx.get_record("dag", bad)) <= 148
            with pytest.raises(b.BuiltinError, match="profile role differs" if fault == "role" else "profile fields/root differ"):
                c.inspect_closure(tx, bad)


def test_native_LOCAL_adapter_interpreter_timeout_and_empty_source(metadata):
    path, _, _, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        for fault, value, message in (("adapter", d.Datum.uri("urn:other:adapter"), "unsupported external binding adapter"),
            ("interpreter", "relative", "invalid external interpreter or timeout"),
            ("timeout-ms", 0, "invalid external interpreter or timeout"),
            ("source", b"", "captured source exceeds external binding profile")):
            bad = clone(tx, binding, fields={fault: b.literal(tx, value)})
            with pytest.raises(c.CallError, match=message):
                c._StructureWalk(tx).binding(bad, "ordinary", None)


def test_native_INPROCESS_NULL_config_empty_source_and_each_environment(metadata):
    path, _, bindings, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        other = c.put_environment(tx, {"get": c.Capture("builtin", b.MAP_GET, bindings["map"])})
        binding = b.record(tx, c.INPROCESS_ROLE, values={"adapter": d.Datum.uri("urn:example:inprocess"),
            "source": b"fixed", "interpreter": None, "timeout-ms": None}, links={"environment": env})
        for name in ("interpreter", "timeout-ms"):
            bad = clone(tx, binding, fields={name: b.literal(tx, d.Datum.bytes(b""))})
            with pytest.raises(b.BuiltinError, match="wrong scalar kind: expected null"):
                c._StructureWalk(tx).binding(bad, "ordinary", env)
        bad = clone(tx, binding, fields={"source": b.literal(tx, b"")})
        with pytest.raises(c.CallError, match="captured source exceeds"):
            c._StructureWalk(tx).binding(bad, "ordinary", env)
        walk = c._StructureWalk(tx)
        walk.binding(binding, "ordinary", env)
        with pytest.raises(c.CallError, match="binding and closure environments differ"):
            walk.binding(binding, "ordinary", other)


def test_native_capture_unknown_kind_and_child_intent_mismatch(metadata):
    path, _, _, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        empty = c.put_environment(tx)
        child = c.put_closure(tx, intent=leaf.ADD, binding=binding, environment=empty)
        row = b.record(tx, c.CAPTURE_ROLE, values={"kind": "unknown", "intent": d.Datum.uri(leaf.ADD)}, links={"target": child})
        assert len(tx.get_record("dag", row)) == 140
        with pytest.raises(c.CallError, match="unsupported capture kind"):
            c._StructureWalk(tx).capture(row)
        row = b.record(tx, c.CAPTURE_ROLE, values={"kind": "ordinary", "intent": d.Datum.uri(leaf.DOUBLE)}, links={"target": child})
        env = b.record(tx, c.ENVIRONMENT_ROLE, links={"child": row})
        with pytest.raises(c.CallError, match="captured ordinary intent differs from closure"):
            c.inspect_environment(tx, env)


def test_native_fixed_shallow_role_scalar_kind_and_capture_intent(metadata):
    path, _, bindings, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        role = b.literal(tx, "wrong")
        bad = tx.put_dag(root=role, bindings={"role": role})
        with pytest.raises(ValueError, match="fixed shallow role differs"):
            leaf.shallow_shape(tx, bad, c.ENVIRONMENT_ROLE, ("role",), 2432)
        with pytest.raises(ValueError, match="native shallow scalar kind differs"):
            leaf.shallow_scalar(tx, b.literal(tx, 42), "string", 100)
        row = b.record(tx, c.CAPTURE_ROLE, values={"kind": "builtin", "intent": d.Datum.uri("urn:short")}, links={"target": bindings["map"]})
        env = b.record(tx, c.ENVIRONMENT_ROLE, links={"get": row})
        with pytest.raises(ValueError, match="fixed shallow capture kind/intent differs"):
            leaf.shallow_environment(tx, env, {"get": ("builtin", b.MAP_GET)})
