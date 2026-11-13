"""IC-003 finite real native METADATA work/height/size/binding/owner/admission checks.

No original exponential baseline, benchmark, ordinary invocation or OS child.
"""

from collections import Counter
import json
from pathlib import Path
import sys
import threading

import daggerml as d
from daggerml import builtin as b, calls as c, local, transfer
import pytest

from test_calls import metadata, leaf, ROOT

INTENT = "urn:example:structural-shared?" + "a" * 4096


def shared(tx, binding, depth):
    env = c.put_environment(tx)
    current = c.put_closure(tx, intent=INTENT, binding=binding, environment=env)
    levels = [(current, env)]
    for _ in range(depth):
        env = c.put_environment(tx, {"name%02d" % i: c.Capture("ordinary", INTENT, current) for i in range(16)})
        current = c.put_closure(tx, intent=INTENT, binding=binding, environment=env)
        levels.append((current, env))
    return current, levels


def test_real_shared16_depth8_named_positions_bounded_expansions_URI_once_and_constructor_walk(metadata, tmp_path, monkeypatch):
    path, base, _, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        root, levels = shared(tx, binding, 8)
        pinned = tx.put_commit(tx.put_tree({"shared": root}), parents=(base,))
        tx.create_ref("shared", pinned)
        uri = tx.put_datum(d.Datum.uri(INTENT))
    counts, uris = Counter(), Counter()
    shape, datum = c._StructureWalk.shape, d.Transaction.get_datum
    def measured_shape(self, dag, names, role, maximum):
        counts[role] += 1
        return shape(self, dag, names, role, maximum)
    def measured_datum(tx, oid):
        if oid == uri:
            uris[oid] += 1
        return datum(tx, oid)
    def no_host_uri(*a):
        pytest.fail("stored native URI must not be recanonicalized as host input")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(c._StructureWalk, "shape", measured_shape)
        patch.setattr(d.Transaction, "get_datum", measured_datum)
        patch.setattr(c, "canonicalize_uri", no_host_uri)
        with d.Repository(path) as repo, repo.read() as tx:
            got = c.inspect_closure(tx, root)
            assert len(got.captures) == 16 and tuple(name for name, _ in got.captures) == tuple("name%02d" % i for i in range(16))
            assert len({capture.target for _, capture in got.captures}) == 1
    assert counts[c.CLOSURE_ROLE] == counts[c.ENVIRONMENT_ROLE] == 9
    assert counts[c.CAPTURE_ROLE] == 8 and counts["local-python-binding-v1"] == 1
    assert uris[uri] == 1  # SAME long native URI across distinct C/capture records, decoded once.
    # Current constructors themselves share ONE walk across the sixteen same-child captures.
    counts.clear()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(c._StructureWalk, "shape", measured_shape)
        with d.Repository(path) as repo, repo.write() as tx:
            child = levels[7][0]
            made = c.put_environment(tx, {"name%02d" % i: c.Capture("ordinary", INTENT, child) for i in range(16)})
            assert made == levels[8][1]
    assert counts[c.CLOSURE_ROLE] == counts[c.ENVIRONMENT_ROLE] == 8
    (tmp_path / "work-proof.json").write_text(json.dumps(dict(depth=8, names=16,
        reader_full_C_expansions=9, reader_full_E_expansions=9, native_shared_URI_decodes=1,
        constructor_full_C_expansions=8, OS_children=0, no_exponential_baseline=True), indent=2) + "\n")
    (tmp_path / "shared-depth8.bundle").write_bytes(transfer.export_commit(path, commit=pinned))


def test_shallow_first_diamond_cached_child_full_height_refuses_deep9_and_constructor(metadata):
    path, _, _, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        top, levels = shared(tx, binding, 8)
        captures = {"a-shallow": c.Capture("ordinary", INTENT, levels[7][0]),
                    "b-deep": c.Capture("ordinary", INTENT, top)}
        rows = {name: b.record(tx, c.CAPTURE_ROLE, values={"kind": got.kind, "intent": d.Datum.uri(got.intent)},
                               links={"target": got.target}) for name, got in captures.items()}
        malformed = b.record(tx, c.ENVIRONMENT_ROLE, links=rows)
        with pytest.raises(c.CallError, match="depth"):
            c.inspect_environment(tx, malformed)
        inserted = []
        original = b.record
        def tracked(*a, **k):
            inserted.append(k)
            return original(*a, **k)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(b, "record", tracked)
            with pytest.raises(c.CallError, match="depth"):
                c.put_environment(tx, captures)
        assert inserted == []  # New ordinary edge charged even after same child shallow success.


def test_shared_INPROCESS_B_native_environment_rechecked_for_SECOND_C(metadata):
    path, _, bindings, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        first_env = c.put_environment(tx)
        other_env = c.put_environment(tx, {"get": c.Capture("builtin", b.MAP_GET, bindings["map"])})
        binding = b.record(tx, c.INPROCESS_ROLE, values={"adapter": d.Datum.uri("urn:example:inprocess"),
            "source": b"supported structural source", "interpreter": None, "timeout-ms": None}, links={"environment": first_env})
        first = c.put_closure(tx, intent=INTENT, binding=binding, environment=first_env)
        # Native typed profile valid; SECOND C has wrong E under SAME already-proven B.
        second = b.record(tx, c.CLOSURE_ROLE, values={"intent": d.Datum.uri(INTENT)}, links={"binding": binding, "environment": other_env})
        rows = {name: b.record(tx, c.CAPTURE_ROLE, values={"kind": "ordinary", "intent": d.Datum.uri(INTENT)},
            links={"target": target}) for name, target in (("a-first", first), ("b-second", second))}
        env = b.record(tx, c.ENVIRONMENT_ROLE, links=rows)
        with pytest.raises(c.CallError, match="environments differ"):
            c.inspect_environment(tx, env)


def test_oversized_native_DAG_reject_BEFORE_get_dag_including_eager_link_and_warm(metadata, monkeypatch):
    path, _, _, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        node = b.literal(tx, c.ENVIRONMENT_ROLE)
        oversized = tx.put_dag(root=node, bindings={"name%04d" % i: node for i in range(1000)})
        link = tx.put_subdag(oversized)
        get_dag = d.Transaction.get_dag
        attempts = []
        def forbidden_decode(tx, oid):
            if oid == oversized:
                attempts.append(oid)
                pytest.fail("oversized application DAG cannot be decoded before raw guard")
            return get_dag(tx, oid)
        monkeypatch.setattr(d.Transaction, "get_dag", forbidden_decode)
        with pytest.raises(c.CallError, match="profile size"):
            c.inspect_environment(tx, oversized)
        view = c._StructuralReads(tx)
        for _ in range(2):
            with pytest.raises(c.CallError, match="profile size"):
                b.link(view, link)  # Its eager get_dag MUST pass through the raw-size guard.
        assert attempts == []


def test_structural_native_owner_thread_ended_composite_and_no_failed_proof(metadata):
    path, _, bindings, _ = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        work = c._StructureWalk(tx)
        assert work.inspect_environment(env, 0) == ()
        failures = []
        def wrong_thread():
            try:
                work.inspect_environment(env, 0)
            except d.InvalidStateError:
                failures.append(True)
        thread = threading.Thread(target=wrong_thread)
        thread.start()
        thread.join()
        assert failures == [True]
        composite = tx.put_datum(d.Datum.list((tx.put_datum(42),)))
        with pytest.raises(c.CallError, match="composite"):
            work.read.get_datum(composite)
        assert ("datum", composite) not in work.read.values
        tx.abort()
        with pytest.raises(d.InvalidStateError):
            work.inspect_environment(env, 0)


@pytest.mark.parametrize("budget", ["objects", "bytes"])
def test_remaining_constructor_admission_native_measured_PREFIX_before_ANY_put(metadata, monkeypatch, budget):
    path, _, bindings, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        items = {"get": c.Capture("builtin", b.MAP_GET, bindings["map"])}
        measured = c._StructureWalk(tx)
        measured.binding(bindings["map"], "builtin")
        rows = 420 + len(c.CAPTURE_ROLE) + len("builtin") + len(b.MAP_GET)
        env = 144 + len(c.ENVIRONMENT_ROLE) + 60 + len("get")
        before = []
        record = b.record
        def tracked(*a, **k):
            before.append(True)
            return record(*a, **k)
        monkeypatch.setattr(b, "record", tracked)
        # TEST-PRIVATE owning limit narrowed to this REAL native prefix + prospective
        # required records/bytes minus1. No fake seen counters or production cap change.
        if budget == "objects":
            monkeypatch.setattr(transfer, "MAX_OBJECTS", len(measured.read.raw) + 12 - 1)
        else:
            monkeypatch.setattr(transfer, "MAX_PACKED_BYTES", measured.read.packed + rows + env - 1)
        with pytest.raises(c.CallError, match="prospective structural"):
            c.put_environment(tx, items)
        assert before == []


def test_remaining_C_constructor_admission_rejects_before_any_public_put(metadata, monkeypatch):
    path, _, _, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        env = c.put_environment(tx)
        measured = c._StructureWalk(tx)
        measured.inspect_environment(env, 0)
        measured.binding(binding, "ordinary", env)
        monkeypatch.setattr(transfer, "MAX_OBJECTS", len(measured.read.raw) + 7 - 1)
        def forbidden(*a, **k):
            pytest.fail("remaining C admission must reject BEFORE any public metadata put")
        monkeypatch.setattr(b, "record", forbidden)
        with pytest.raises(c.CallError, match="prospective structural membership"):
            c.put_closure(tx, intent=INTENT, binding=binding, environment=env)


def test_fixed_adapter_unsupported16_set_rejects_BEFORE_generic_expansion(metadata, monkeypatch):
    path, _, _, binding = metadata
    with d.Repository(path) as repo, repo.write() as tx:
        root, levels = shared(tx, binding, 8)
        def forbidden(*a, **k):
            pytest.fail("unsupported fixed capture set must reject before structural recursion")
        monkeypatch.setattr(c, "inspect_environment", forbidden)
        with pytest.raises(ValueError, match="shallow"):
            leaf.environment(tx, levels[8][1])
