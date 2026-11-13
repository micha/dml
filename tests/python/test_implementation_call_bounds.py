"""NEW real reached64/next65 and propagated ORIGINAL ancestry8/9; no OS children.

Adversarial semantic profile data below is native typed metadata, NOT an executed
primitive/normal return or successful attempt. No fake public successful S is made.
"""

import json
import os
from pathlib import Path

import daggerml as d
from daggerml import builtin as b, transfer
import pytest

from test_captured_call_profiles import semantic_chain
from test_implementation_calls import initial, host, p, adapter, bridge, leaf


def boundary_inputs(tx, binding, *, returned=False, sourced=False, levels=7):
    full = semantic_chain(tx, binding, levels)  # Real typed native graph, not counters.
    if not returned:
        return full
    fields = tx.get_dag(full).bindings
    rows = tx.get_dag(b.link(tx, fields["entries"])).bindings
    sources = {}
    for n in ("arg-00", "arg-01"):
        row = tx.get_dag(b.link(tx, rows[n])).bindings
        sources[b.scalar(tx, row["key"], "string")] = b.link(tx, row["source"])
    q = p.event(tx, "local-request-v1", "q-" + "1" * 32, values={"intent": d.Datum.uri(leaf.ADD)},
                links={"binding": binding, "inputs": full})
    trace = b.record(tx, b.TRACE_ROLE, links={"request": q, "inputs": full})
    value = b.node_value(tx, tx.get_dag(sources["a"]).bindings["value"])[0]
    wrapped = b.record(tx, b.RETURN_ROLE, links={"returned": sources["a"], "trace": trace, "request": q, "inputs": full},
                       nodes={"value": tx.put_literal(value)}, root="value")
    other = sources["b"]
    if sourced:
        # Explicit actual literal selection; selected source DAG already in the semantic union.
        selected = tx.lookup_node(other, "value")
        other = b.record(tx, b.SOURCE_ROLE, values={"name": "value", "node": selected.bytes},
            links={"source": other}, nodes={"value": selected}, root="value")
    pairs, links = [], {}
    for i, (name, source) in enumerate((("a", wrapped), ("b", other))):
        key = tx.put_datum(name)
        datum = b.node_value(tx, tx.get_dag(source).bindings["value"])[0]
        pairs.append((key, datum))
        links["arg-%02d" % i] = b.record(tx, b.ENTRY_ROLE, nodes={"key": tx.put_literal(key)}, links={"source": source})
    ledger = b.record(tx, b.ENTRIES_ROLE, links=links)
    return b.record(tx, b.ARGUMENTS_ROLE, nodes={"value": b.literal(tx, d.Datum.map(pairs))}, links={"entries": ledger}, root="value")


def retain_proof(tmp_path, name, **data):
    output = Path(os.environ.get("DML_I25_PROOF_DIR", tmp_path))
    output.mkdir(exist_ok=True, parents=True)
    (output / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")


def test_NEW_native64_request_union_next65_UNUSED_requested_binding_BEFORE_Q(initial, tmp_path):
    path, base = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, base)
        entries["cap64"] = boundary_inputs(tx, entries["map-v1"], returned=True)
        entries["cap65"] = boundary_inputs(tx, entries["map-v1"], returned=True, sourced=True)
        commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
        tx.create_ref("bounds", commit)
    unions = {}
    with d.Repository(path) as repo, repo.read() as tx:
        for name in ("cap64", "cap65"):
            closure = p.inspect_closure(tx, commit, entries["outer-B" if name == "cap64" else "outer-A"])
            seen = set()
            p.arguments(tx, commit, entries[name], ("a", "b"), seen)
            semantic_only = frozenset(seen)
            # Requested B captures v2 on positive; input's native primitive graph uses v1.
            # Both requested getter/list bindings count EVEN though no new getter/dispatch ran.
            seen.update((closure["map_binding"], closure["add"]["list_binding"]))
            assert len(seen) == (64 if name == "cap64" else 65)
            unions[name] = frozenset(seen)
            assert len(semantic_only) == (62 if name == "cap64" else 64)
    q = p.record_request(path, commit=commit, closure_name="outer-B", inputs_name="cap64", ref="positive64")
    measured = set()
    p.inspect_request(path, commit=q.commit, request=q.request, seen=measured)
    assert frozenset(measured) == unions["cap64"]
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="union exceeds64"):
        p.record_request(path, commit=q.commit, inputs_name="cap65", ref="NEVER65")
    assert (path / "data.mdb").read_bytes() == before
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("NEVER65")
        assert not any(n.startswith("outer-attempt-") for n in p.tree(tx, q.commit))
    bundle = transfer.export_commit(path, commit=q.commit)
    (tmp_path / "actual-native64.bundle").write_bytes(bundle)
    retain_proof(tmp_path, "native64-next65", positive=sorted(str(x) for x in unions["cap64"]),
        rejected=sorted(str(x) for x in unions["cap65"]), unused_requested_list=str(closure["add"]["list_binding"]),
        positive_request=str(q.request), pinned=str(q.commit), OS_children=0,
        qualification="adversarial native semantic profiles/own metadata request, not executed return/success proof")


def test_NEW_real_union_reservation_preput_and_pre_LEAF_dispatch(initial, tmp_path, monkeypatch):
    path, base = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, base)
        entries["dense"] = boundary_inputs(tx, entries["map-v1"])
        commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
    q = p.record_request(path, commit=commit, inputs_name="dense", ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    assert len(session.seen) == 58  # Actual57 source DAGs + actual requested list B, not fake counters.
    def forbidden(*a, **k):
        pytest.fail("boundary must reject BEFORE ordinary child dispatch")
    monkeypatch.setattr(p.ex, "execute_exchange", forbidden)
    with pytest.raises(bridge.SessionError, match="expected poisoned boundary"):
        with session.context:
            session.start()
            # Real native getter preparation consumes source58+key1+arguments4=63.
            key = session.context.literal(d.Datum.string("a"))
            prepared = session.context.arguments({"map": session.input, "key": key})
            assert len(session.seen) == 63
            before = (path / "data.mdb").read_bytes()
            with pytest.raises(bridge.SessionError, match="reservation exceeds64"):
                session.context.invoke(session.context.bind(kind="builtin", intent=b.MAP_GET, target=q.closure["map_binding"]), prepared)
            assert (path / "data.mdb").read_bytes() == before
            assert not session.getters and not session.calls and session.context.poisoned
            # Exit propagates caught poison. No fake success or new Recorder continuation.
            raise bridge.SessionError("expected poisoned boundary")


def test_NEW_actual_pre_dispatch62_plus_required_return3_refuses65(initial, tmp_path, monkeypatch):
    path, base = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, base)
        entries["dense"] = boundary_inputs(tx, entries["map-v1"], levels=6)
        commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
    q = p.record_request(path, commit=commit, inputs_name="dense", ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    def forbidden(*a, **k):
        pytest.fail("actual pre-fresh-leaf reservation must reject BEFORE execute")
    monkeypatch.setattr(p.ex, "execute_exchange", forbidden)
    with pytest.raises(bridge.SessionError, match="reservation exceeds64"):
        with session.context:
            session.start()
            assert len(session.seen) == 51
            session.nodes.map_get(session.input, "a")
            session.nodes.map_get(session.input, "b")
            assert len(session.seen) == 62 and len(session.getters) == 2
            session.invoker.invoke(session.tokens[0], session.input)
    with d.Repository(path) as repo, repo.read() as tx:
        entries = p.tree(tx, session.current)
        assert len([n for n in entries if n.startswith("request-q-")]) == 1
        assert not any(n.startswith("attempt-a-") for n in entries)
        assert "status" not in tx.get_dag(session.initial).bindings
    assert not session.calls and not (session.workspace / "leaf-0").exists()
    retain_proof(tmp_path, "predispatch-next65", actual_ids=sorted(str(x) for x in session.seen),
        actual=62, required_fresh_return_additions=3, refused_reservation=65, OS_children=0,
        head=str(session.current), initial=str(session.initial), own_leaf_Q_retained=True)


def test_NEW_actual_ORIGINAL_retained_ancestry8_then9_BEFORE_Q(initial, host, tmp_path, monkeypatch):
    path, commit = initial
    depths = []
    check = p.authority_depth
    def measured(value):
        depths.append(value)
        return check(value)
    monkeypatch.setattr(p, "authority_depth", measured)
    results = []
    for number in range(1, 4):
        result = adapter.invoke(path, commit=commit, ref="outer-%d" % number, workspace=tmp_path / ("HOST-%d" % number))
        results.append(result)
        selected = p.select_outer(path, commit=result.commit, completion=result.commit,
                                  slot="choice-%d" % number, ref="choice-%d" % number)
        with d.Repository(path) as repo, repo.write() as tx:
            entries = p.tree(tx, selected)
            # TEST-PRIVATE explicit branch selection, not automatic adoption/public API expansion.
            entries[p.SLOT] = entries["choice-%d" % number]
            commit = tx.put_commit(tx.put_tree(entries), parents=(selected,))
            tx.create_ref("chosen-%d" % number, commit)
    assert len(host) == 6 and max(depths) == 8
    before = (path / "data.mdb").read_bytes()
    depths.clear()
    with pytest.raises(ValueError, match="chain too deep"):
        p.record_request(path, commit=commit, ref="NEVER-q4")
    assert max(depths) == 9 and len(host) == 6
    assert (path / "data.mdb").read_bytes() == before
    bundle = transfer.export_commit(path, commit=commit)
    (tmp_path / "actual-ORIGINAL8.bundle").write_bytes(bundle)
    retain_proof(tmp_path, "ORIGINAL8-next9", roots=[str(r.commit) for r in results], pinned=str(commit),
        successful_max=8, refused_next=9, depth_entry=0, HOST_publications=6, OS_children=0,
        qualification="actual retained native selected/producer ancestry with HOST publication; not OS custody or installed story")
