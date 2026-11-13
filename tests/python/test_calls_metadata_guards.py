"""Approved finite native METADATA guards1-6+8; no height repeat/fake raw/node-size filler."""

import daggerml as d
from daggerml import builtin as b, calls as c, transfer
import pytest

from test_calls import metadata, leaf


@pytest.mark.parametrize("budget", ["objects", "packed", "record"])
def test_actual_raw_native_prefix_next_read_scaled_limit(metadata, monkeypatch, budget):
    path, _, _, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        first = tx.put_datum(42)
        second = tx.put_datum("x" * 200)
        view = c._StructuralReads(tx)
        before = view.get_record("datum", first)
        actual = tx.get_record("datum", second)
        read_calls = []
        read = d.Transaction.get_record
        def measured(owner, kind, oid):
            read_calls.append((kind, oid))
            return read(owner, kind, oid)
        monkeypatch.setattr(d.Transaction, "get_record", measured)
        # TEST-PRIVATE scaled owning limit, REAL prefix/next native bytes; not production stress.
        if budget == "objects":
            monkeypatch.setattr(transfer, "MAX_OBJECTS", len(view.raw))
        elif budget == "packed":
            monkeypatch.setattr(transfer, "MAX_PACKED_BYTES", len(before) + len(actual) - 1)
        else:
            monkeypatch.setattr(transfer, "MAX_RECORD_BYTES", len(actual) - 1)
        with pytest.raises(c.CallError, match="structural native"):
            view.get_record("datum", second)
        assert ("datum", second) not in view.raw
        assert read_calls == ([] if budget == "objects" else [("datum", second)])
        assert view.packed == len(before)


def test_source_BYTES_over_existing_1MiB_rejects_BEFORE_datum_decode(metadata, monkeypatch):
    path, _, _, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        source = tx.put_datum(b"x" * (1048576 + 1))
        binding = b.record(tx, "local-python-binding-v1", values={"adapter": d.Datum.uri("urn:daggerml:local-python-v1"),
            "interpreter": "/python", "timeout-ms": 1}, nodes={"source": tx.put_literal(source)})
        get = d.Transaction.get_datum
        def forbid_source(owner, oid):
            if oid == source:
                pytest.fail("source profile byte guard must reject BEFORE copied datum decode")
            return get(owner, oid)
        monkeypatch.setattr(d.Transaction, "get_datum", forbid_source)
        work = c._StructureWalk(tx)
        with pytest.raises(c.CallError, match="datum exceeds structural field size"):
            work.binding(binding, "ordinary", None)
        assert binding not in work.bindings


def test_native_capture_kind_over8_rejects_BEFORE_kind_datum_decode(metadata, monkeypatch):
    path, _, bindings, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        kind = tx.put_datum("ordinaryX")
        row = b.record(tx, c.CAPTURE_ROLE, values={"intent": d.Datum.uri(leaf.ADD)},
            nodes={"kind": tx.put_literal(kind)}, links={"target": bindings["map"]})
        get = d.Transaction.get_datum
        def forbid_kind(owner, oid):
            if oid == kind:
                pytest.fail("capture kind valid8 byte bound must reject BEFORE native datum decode")
            return get(owner, oid)
        monkeypatch.setattr(d.Transaction, "get_datum", forbid_kind)
        work = c._StructureWalk(tx)
        with pytest.raises(c.CallError, match="field size"):
            work.capture(row)
        assert row not in work.rows


@pytest.mark.parametrize("direction", ["scalar-is-subdag", "link-is-literal"])
def test_actual_native_Literal_SubDAG_field_kind_mismatch(metadata, direction):
    path, _, _, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        literal, subdag = b.literal(tx, "not a link"), tx.put_subdag(env)
        work = c._StructureWalk(tx)
        with pytest.raises(b.BuiltinError, match="literal" if direction.startswith("scalar") else "sub-DAG"):
            if direction.startswith("scalar"):
                work.scalar(subdag, "string")
            else:
                work.link(literal, 2432)


def test_builtin_LOCAL_kind_mismatch_rejects_even_after_binding_native_proof(metadata):
    path, _, bindings, local_binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        work = c._StructureWalk(tx)
        work.binding(local_binding, "ordinary", env)
        assert local_binding in work.bindings
        with pytest.raises(c.CallError, match="builtin capture requires builtin"):
            work.binding(local_binding, "builtin")
        work.binding(bindings["map"], "builtin")
        with pytest.raises(c.CallError, match="ordinary closure requires executable"):
            work.binding(bindings["map"], "ordinary", env)
        wrong = b.record(tx, c.CLOSURE_ROLE, values={"intent": d.Datum.uri(leaf.ADD)},
            links={"binding": bindings["map"], "environment": env})
        with pytest.raises(c.CallError, match="ordinary closure"):
            c.inspect_closure(tx, wrong)


@pytest.mark.parametrize("direction", ["scalar-is-subdag", "link-is-literal", "scalar-oversize", "link-oversize"])
def test_fixed_shallow_real_kind_or_size_reject_before_eager_decode(metadata, monkeypatch, direction):
    path, _, _, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        literal, subdag = b.literal(tx, "value"), tx.put_subdag(env)
        if direction == "scalar-is-subdag":
            with pytest.raises(ValueError, match="requires literal"):
                leaf.shallow_scalar(tx, subdag, "string", 100)
        elif direction == "link-is-literal":
            with pytest.raises(ValueError, match="requires SubDAG"):
                leaf.shallow_link(tx, literal, 2432)
        elif direction == "scalar-oversize":
            datum = tx.put_datum("x" * 80)
            node = tx.put_literal(datum)
            get = d.Transaction.get_datum
            def forbid(owner, oid):
                if oid == datum:
                    pytest.fail("fixed scalar raw bound must precede native description")
                return get(owner, oid)
            monkeypatch.setattr(d.Transaction, "get_datum", forbid)
            with pytest.raises(ValueError, match="scalar exceeds profile"):
                leaf.shallow_scalar(tx, node, "string", 40 + len(c.CLOSURE_ROLE))
        else:
            # Smaller-than-E but larger-than-C native DAG: correct expected profile-specific bound.
            node = b.literal(tx, "role")
            other = tx.put_dag(root=node, bindings={"name%d" % i: node for i in range(8)})
            link = tx.put_subdag(other)
            get = d.Transaction.get_dag
            def forbid(owner, oid):
                if oid == other:
                    pytest.fail("expected-C raw limit must precede eager b.link native get_dag")
                return get(owner, oid)
            monkeypatch.setattr(d.Transaction, "get_dag", forbid)
            with pytest.raises(ValueError, match="target exceeds profile"):
                leaf.shallow_link(tx, link, 148)
