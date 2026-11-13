"""NEW native histories with explicitly HOST-substituted publication, ZERO OS children."""

import json
import os
from pathlib import Path
import sys

import daggerml as d
from daggerml import builtin as b, calls as c, local
import pytest

ROOT = Path(__file__).resolve().parents[2]
_saved = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    import implementation_calls as p
    import implementation_call_adapter as adapter
    import implementation_call_leaf as leaf
    import implementation_call_funcs as logical
    import implementation_call_session as bridge
    import implementation_leaf_funcs as funcs
finally:
    sys.path[:] = _saved


@pytest.fixture
def initial(tmp_path):
    path = tmp_path / "caller.dml"
    commit = p.initialize(path, sys.executable)
    commit = p.prepare_arguments(path, commit=commit, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
    return path, commit


@pytest.fixture
def host(monkeypatch):
    publications = []
    def publication(context, source, interpreter, timeout):
        with d.Repository(context.repository_path) as repo, repo.read() as tx:
            intent = b.scalar(tx, tx.get_dag(context.request).bindings["intent"], "uri")
            candidates = []
            for dag in b.Inspector(tx, commit=context.pre_dispatch).retained:
                fields = tx.get_dag(dag).bindings
                if "role" in fields and b.scalar(tx, fields["role"], "string") == c.CLOSURE_ROLE:
                    got = c.inspect_closure(tx, dag)
                    if got.binding == context.binding:
                        candidates.append(got)
            assert len(candidates) == 1
            closure = candidates[0]
            assert closure.intent == intent
            assert source == leaf.capture(closure.environment, intent, *leaf.sources())
        leaf.publish(context, closure.environment, intent, *leaf.sources(), funcs.add if intent == leaf.ADD else funcs.double)
        publications.append(context)
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    def forbid(*args, **kwargs):
        pytest.fail("HOST metadata test must never launch an OS child")
    monkeypatch.setattr(local, "_execute", publication)
    monkeypatch.setattr(local.subprocess, "Popen", forbid)
    return publications


def test_metadata_structural_profiles_PIN_defaults_and_old_contracts_unchanged(initial):
    path, commit = initial
    with d.Repository(path) as repo, repo.read() as tx:
        entries = p.tree(tx, commit)
        a, other = (p.inspect_closure(tx, commit, entries["outer-" + label]) for label in ("A", "B"))
        assert a["intent"] == other["intent"] == p.INTENT
        assert a["binding"] != other["binding"] and a["environment"] != other["environment"]
        assert not any("key" in tx.get_dag(entries[n]).bindings for n in ("outer-A", "outer-B", "add-A", "add-B"))
        assert a["add"]["dag"] == entries["default-add"]
        with pytest.raises(ValueError):
            b.inspect_binding(tx, a["binding"])
    moved = p.promote_defaults(path, commit=commit, ref="defaults-B")
    with d.Repository(path) as repo, repo.read() as tx:
        updated = p.tree(tx, moved)
        assert updated["outer-A"] == entries["outer-A"] and updated["outer-B"] == entries["outer-B"]
        assert {n for n in updated if updated[n] != entries[n]} == {"default-add", "default-double"}
        assert p.inspect_closure(tx, moved, updated["outer-A"])["add"]["dag"] == entries["add-A"]


def test_actual_outer_entry_nested_leaf_and_ALL_getters_use_common_Context_invoke(initial, host, tmp_path, monkeypatch):
    path, commit = initial
    calls = []
    original = c.Context.invoke
    def measured(self, target, arguments):
        # Count facade entries; Recorder inspection semantic recomputation isn't dispatch.
        calls.append(arguments.value)
        return original(self, target, arguments)
    monkeypatch.setattr(c.Context, "invoke", measured)
    result = adapter.invoke(path, commit=commit, ref="outer-1", workspace=tmp_path / "HOST-1")
    assert result.node.value == d.Datum.i64(84)
    assert len(host) == 2 and len(calls) == 8  # outer1 + ordinary2 + outerget2 + leafget3
    got = p.inspect_completion(path, commit=result.commit)
    assert got["request"] == result.request.request and got["closure"] == result.request.closure
    with d.Repository(path) as repo, repo.read() as tx:
        first, second = (tx.get_dag(call).bindings for call in got["calls"])
        pending0 = tx.get_dag(b.link(tx, first["pending"])).bindings
        pending1 = tx.get_dag(b.link(tx, second["pending"])).bindings
        assert b.link(tx, pending0["inputs"]) == result.request.inputs.dag
        _, sources = p.arguments(tx, result.commit, b.link(tx, pending1["inputs"]), ("x",), set())
        assert sources["x"].dag == b.link(tx, first["result"])
        add_return = tx.get_dag(b.link(tx, first["result"])).bindings
        trace = b.Inspector(tx, commit=result.commit).trace(b.link(tx, add_return["trace"]),
            request=b.link(tx, pending0["request"]), inputs=result.request.inputs.dag)
        assert tuple(v.dag for v in trace) == got["getters"]
    assert got["semantic_ids"] == result.semantic_ids
    assert len(result.semantic_ids) <= 64  # This source's measured graph, not general feasibility.


def test_five_native_row_shapes_requested_AND_OLD_union_no_binding_key_HOST_only(initial, host, tmp_path, monkeypatch):
    path, commit = initial
    commit = p.prepare_source_arguments(path, commit=commit, values={"a": 13, "b": 29}, inputs_name="new-sources", ref="new-sources")
    commit = p.prepare_arguments(path, commit=commit, values={"a": 13, "b": 30}, inputs_name="changed", ref="changed")
    reservations, depths, invoke_entries = [], [], []
    reserve, depth, invoke = bridge.Session._reserve, p.authority_depth, c.Context.invoke
    def measured_reserve(self, count):
        reservations.append(dict(request=str(self.q.request), previous=sorted(str(x) for x in self.seen),
            additional=count, bound=len(self.seen) + count))
        return reserve(self, count)
    def measured_depth(value):
        depths.append(value)
        return depth(value)
    def measured_invoke(self, target, args):
        invoke_entries.append(args.value)
        return invoke(self, target, args)
    monkeypatch.setattr(bridge.Session, "_reserve", measured_reserve)
    monkeypatch.setattr(p, "authority_depth", measured_depth)
    monkeypatch.setattr(c.Context, "invoke", measured_invoke)
    results, known = [], None
    for number, label, inputs, outer, inner in ((1, "A", "inputs", "fresh", "fresh"),
        (2, "B", "new-sources", "require-selected", "fresh"), (3, "B", "inputs", "fresh", "fresh"),
        (4, "B", "inputs", "fresh", "require-selected"), (5, "A", "changed", "try-selected", "try-selected")):
        if number == 4:
            commit = p.promote_defaults(path, commit=commit, ref="defaults-B")
        before = len(host), len(invoke_entries)
        result = adapter.invoke(path, commit=commit, closure_name="outer-" + label, inputs_name=inputs,
            control=outer, add_control=inner, double_control=inner, ref="outer-%d" % number,
            workspace=tmp_path / ("HOST-%d" % number))
        results.append(result)
        commit = result.commit
        assert result.node.value == d.Datum.i64(86 if number == 5 else 84)
        assert len(host) - before[0] == (0 if number in (2, 4) else 2)
        assert len(invoke_entries) - before[1] == (1 if number == 2 else 5 if number == 4 else 8)
        assert len(result.semantic_ids) <= b.MAX_RECORDS
        with d.Repository(path) as repo, repo.read() as tx:
            entries = p.tree(tx, commit)
            # Requested captured bindings count even when no getter/adaptor ran.
            closure = p.inspect_closure(tx, commit, entries["outer-" + label])
            assert {closure["map_binding"], closure["add"]["list_binding"]} <= result.semantic_ids
        if number == 1:
            got = p.inspect_completion(path, commit=commit)
            commit = p.select_outer(path, commit=commit, completion=commit, ref="selected-outer")
            for call, slot, ref in zip(got["calls"], (p.ADD_SLOT, p.DOUBLE_SLOT), ("selected-add", "selected-double")):
                commit = p.pin_leaf(path, commit=commit, call=call, slot=slot, ref=ref)
            with d.Repository(path) as repo, repo.read() as tx:
                entries = p.tree(tx, commit)
                known = {slot: entries[slot] for slot in (p.SLOT, p.ADD_SLOT, p.DOUBLE_SLOT)}
        else:
            with d.Repository(path) as repo, repo.read() as tx:
                assert {slot: p.tree(tx, commit)[slot] for slot in known} == known
    assert len(host) == 6 and len(invoke_entries) == 30
    assert all(r["bound"] <= 64 for r in reservations) and max(depths) <= 8
    with d.Repository(path) as repo, repo.read() as tx:
        first = results[0].request.inputs
        new = results[1].request.inputs
        assert first.datum == new.datum and first.dag != new.dag
        assert results[0].request.closure["binding"] != results[1].request.closure["binding"]
        assert p.tree(tx, commit)["default-add"] == p.tree(tx, commit)["add-B"]
    # Read/reuse authority checks finish outside any live native transaction.
    selected = p.inspect_reuse(path, commit=results[1].commit)
    assert selected.request == results[1].request.request
    assert selected.selected["closure"] == results[0].request.closure
    original = p.inspect_completion(path, commit=results[0].commit)
    actual = p.inspect_completion(path, commit=results[3].commit)
    with d.Repository(path) as repo, repo.read() as tx:
        for old, new in zip(original["calls"], actual["calls"]):
            of, nf = tx.get_dag(old).bindings, tx.get_dag(new).bindings
            assert b.link(tx, of["attempt"]) == b.link(tx, nf["attempt"])
            assert b.link(tx, of["result"]) == b.link(tx, nf["result"])
            op = tx.get_dag(b.link(tx, of["pending"])).bindings
            np = tx.get_dag(b.link(tx, nf["pending"])).bindings
            assert b.link(tx, op["request"]) != b.link(tx, np["request"])
            assert b.link(tx, op["closure"]) != b.link(tx, np["closure"])
    proof = dict(HOST_only=True, OS_children=0, HOST_publications=6, Context_invoke_entries=30,
        rows=[dict(request=str(r.request.request), completion=str(r.commit),
            requested_closure=str(r.request.closure["dag"]), input=str(r.request.inputs.dag),
            semantic_ids=sorted(str(x) for x in r.semantic_ids)) for r in results],
        reservations=reservations, maximum_measured_depth=max(depths), structural_depth_limit=c.MAX_STRUCTURE_DEPTH,
        ORIGINAL_depth_limit=p.MAX_AUTHORITY_DEPTH, semantic_limit=b.MAX_RECORDS,
        qualification="native HOST graph/reservation evidence, NOT installed story/custody/feasibility for changed bytes")
    output = Path(os.environ.get("DML_I25_PROOF_DIR", tmp_path))
    output.mkdir(exist_ok=True, parents=True)
    (output / "native-row-proof.json").write_text(json.dumps(proof, indent=2) + "\n")


@pytest.mark.parametrize("fault", ["old-valid-completion", "old-same-context-handle", "datum", "id", "flags"])
def test_native_valid_but_WRONG_original_result_association_rejects_NEW_outer_Q(initial, host, tmp_path, monkeypatch, fault):
    path, commit = initial
    old = adapter.invoke(path, commit=commit, ref="original", workspace=tmp_path / "HOST-original")
    backend = adapter.EntryBackend(path, old.commit, "outer-B", "inputs",
        dict(control="fresh", add_control="fresh", double_control="fresh"), "new-request", tmp_path / "NEVER-dispatch", None)
    old_return = p.inspect_completion(path, commit=old.commit)
    original_read = backend.read
    def allow_valid_old_node_for_test(dag):
        if dag != old_return["result"]:
            return original_read(dag)
        validated = p.inspect_completion(path, commit=old.commit)
        with d.Repository(path) as repo, repo.read() as tx:
            return b.Description(dag, validated["datum"], tx.get_datum(validated["datum"]))
    monkeypatch.setattr(backend, "read", allow_valid_old_node_for_test)
    with pytest.raises(c.CallError):
        with c.Context(backend) as context:
            target = context.bind(kind="ordinary", intent=p.INTENT, target=backend.closure["dag"])
            arguments = context.load(backend.inputs)
            # TEST-PRIVATE read grant; real native successful old node, not a fabricated value.
            old_handle = context.load(old_return["result"])
            def false_response(bound, actual):
                # Actual new native own Q is valid, but old successful completion belongs to OLD Q/A.
                backend.request = p.record_request(path, commit=backend.current, closure_name="outer-B", ref="new-request")
                backend.current = old.commit
                backend.last = (backend.request.request, backend.current)
                if fault == "old-valid-completion":
                    return backend.last  # Fresh native proof must reject even this coherent response shape.
                return {"old-same-context-handle": old_handle, "datum": old.node.value,
                        "id": old.commit, "flags": {"success": True, "result": 84}}[fault]
            monkeypatch.setattr(backend, "perform", false_response)
            with pytest.raises(c.CallError, match="THIS|callback"):
                context.invoke(target, arguments)
            assert context.poisoned
    assert len(host) == 2 and not (tmp_path / "NEVER-dispatch").exists()
    assert p.inspect_completion(path, commit=old.commit)["request"] == old.request.request
    assert p.inspect_request(path, commit=backend.request.commit, request=backend.request.request).closure["binding"] != old.request.closure["binding"]


@pytest.mark.parametrize("slot", [p.SLOT, p.ADD_SLOT, p.DOUBLE_SLOT])
@pytest.mark.parametrize("control", ["fresh", "try-selected", "require-selected"])
def test_ALL_present_poison_rejects_before_NEW_Q_even_fresh_mismatch(initial, slot, control):
    path, commit = initial
    commit = p.prepare_arguments(path, commit=commit, values={"a": 13, "b": 30}, inputs_name="mismatch", ref="mismatch")
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, commit)
        entries[slot] = b.record(tx, "malformed-selected-authority", values={"value": 84})
        poisoned = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref("poison", poisoned)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        p.record_request(path, commit=poisoned, inputs_name="mismatch", control=control, ref="NEVER-Q")
    assert (path / "data.mdb").read_bytes() == before
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("NEVER-Q")


def test_actual_pinned_A_leaf_dispatch_AFTER_defaults_B(initial, host, tmp_path):
    path, commit = initial
    moved = p.promote_defaults(path, commit=commit, ref="default-B")
    result = adapter.invoke(path, commit=moved, closure_name="outer-A", ref="pinned-A", workspace=tmp_path / "HOST-pinned")
    assert len(host) == 2 and result.node.value == d.Datum.i64(84)
    with d.Repository(path) as repo, repo.read() as tx:
        entries = p.tree(tx, result.commit)
        assert entries["default-add"] == entries["add-B"]
        a = p.inspect_closure(tx, result.commit, entries["outer-A"])
        assert result.request.closure == a
        assert [context.binding for context in host] == [a["add"]["binding"], a["double"]["binding"]]


def test_targeted_cross_B_outer_and_inner_hits_PIN_OLD_A_no_automatic_adoption(initial, host, tmp_path):
    path, commit = initial
    first = adapter.invoke(path, commit=commit, ref="outer-1", workspace=tmp_path / "HOST-1")
    got = p.inspect_completion(path, commit=first.commit)
    commit = p.select_outer(path, commit=first.commit, completion=first.commit, ref="selected-outer")
    for call, slot, ref in zip(got["calls"], (p.ADD_SLOT, p.DOUBLE_SLOT), ("selected-add", "selected-double")):
        commit = p.pin_leaf(path, commit=commit, call=call, slot=slot, ref=ref)
    commit = p.prepare_source_arguments(path, commit=commit, values={"a": 13, "b": 29}, inputs_name="new-sources", ref="new-sources")
    hit = adapter.invoke(path, commit=commit, closure_name="outer-B", inputs_name="new-sources", control="require-selected",
        ref="outer-hit", workspace=tmp_path / "NEVER-outer-adapter")
    assert hit.request.reused is not None and hit.node.value == d.Datum.i64(84)
    assert len(host) == 2 and not (tmp_path / "NEVER-outer-adapter").exists()
    assert p.inspect_reuse(path, commit=hit.commit).selected["attempt"] == got["attempt"]
    # Separately fresh outer B with pinned OLD A inner reuse: ZERO further leaf execution.
    inner = adapter.invoke(path, commit=hit.commit, closure_name="outer-B", add_control="require-selected", double_control="require-selected",
        ref="outer-inner-hit", workspace=tmp_path / "HOST-inner-hit")
    assert inner.node.value == d.Datum.i64(84) and len(host) == 2
    current = p.inspect_completion(path, commit=inner.commit)
    with d.Repository(path) as repo, repo.read() as tx:
        entries = p.tree(tx, inner.commit)
        assert entries[p.SLOT] == hit.request.selected["dag"]
        for original, actual, name in zip(got["calls"], current["calls"], ("add", "double")):
            old, new = tx.get_dag(original).bindings, tx.get_dag(actual).bindings
            assert tuple(b.link(tx, old[n]) for n in ("selection", "attempt", "result")) == tuple(b.link(tx, new[n]) for n in ("selection", "attempt", "result"))
            pending = tx.get_dag(b.link(tx, new["pending"])).bindings
            assert b.link(tx, pending["closure"]) == current["closure"][name]["dag"]
            assert b.link(tx, pending["request"]) != b.link(tx, tx.get_dag(b.link(tx, old["pending"])).bindings["request"])
        assert {entries[p.ADD_SLOT], entries[p.DOUBLE_SLOT]} == {b.link(tx, tx.get_dag(call).bindings["selection"]) for call in got["calls"]}


def test_swapped_named_arguments_differ_full_MAP_and_required_miss_creates_no_Q(initial):
    path, commit = initial
    swapped = p.prepare_arguments(path, commit=commit, values={"a": 29, "b": 13}, inputs_name="swapped", ref="swapped")
    with d.Repository(path) as repo, repo.read() as tx:
        entries = p.tree(tx, swapped)
        original, left = p.arguments(tx, swapped, entries["inputs"], ("a", "b"), set())
        changed, right = p.arguments(tx, swapped, entries["swapped"], ("a", "b"), set())
        assert original.datum != changed.datum and original.dag != changed.dag
        assert left["a"].datum == right["b"].datum and left["b"].datum == right["a"].datum
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="required"):
        p.record_request(path, commit=swapped, control="require-selected", ref="NEVER")
    assert (path / "data.mdb").read_bytes() == before



