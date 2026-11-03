"""Strict native final-T/W/profile negatives over ONE frozen HOST-produced history."""

from pathlib import Path
import sys

import daggerml as d
from daggerml import builtin as b, local, transfer
import pytest

from test_exchange_records import clone
from test_captured_calls import app, adapter, bridge, leaf, fresh, pin_double


@pytest.fixture(scope="module")
def frozen(tmp_path_factory):
    root = tmp_path_factory.mktemp("captured-profiles")
    path = root / "caller"
    commit = app.initialize(path, sys.executable)
    commit = app.prepare_arguments(path, commit=commit, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
    publications = []
    def host_entry(context, source, interpreter, timeout):
        # Evaluate actual captured entry in HOST; native protocol/storage real, NO OS wait proof.
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(local, "child_context", lambda *a, **k: context)
            exec(compile(source, "HOST captured leaf entry", "exec"), {})
        publications.append(context)
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(local, "_execute", host_entry)
        q, final, got = fresh(path, commit, root, 1)
    assert len(publications) == 2
    selected = app.select_outer(path, commit=final, completion=final, ref="selected")
    selected = pin_double(path, selected, got["calls"][1])
    reused = app.record_request(path, commit=selected, control="require-selected", ref="reused")
    assert reused.reused is not None
    return dict(bundle=transfer.export_commit(path, commit=reused.reused), q=q, final=final, got=got, reused=reused)


@pytest.fixture
def case(tmp_path, frozen):
    path = tmp_path / "case"
    with d.Repository(path, create=True):
        pass
    transfer.import_commit(path, frozen["bundle"], ref="case")
    return path, frozen


@pytest.mark.parametrize("fault", ["role", "root", "extra", "status", "initial", "request", "plan", "completion", "occurrence", "parent", "tree"])
def test_same_occurrence_final_T_exact_links_parent_replacement(case, fault):
    path, frozen = case
    final, got = frozen["final"], frozen["got"]
    with d.Repository(path) as repo, repo.write() as tx:
        old = app.tree(tx, final)
        final_t = got["attempt"]
        fields = tx.get_dag(final_t).bindings
        changes, root = {}, None
        if fault == "role":
            changes["role"] = b.literal(tx, "wrong")
        elif fault == "root":
            root = fields["status"]
        elif fault == "extra":
            changes["extra"] = b.literal(tx, 1)
        elif fault == "status":
            changes["status"] = b.literal(tx, "working")
        elif fault in ("initial", "request", "plan", "completion"):
            changes["initial-attempt" if fault == "initial" else fault] = tx.put_subdag(frozen["q"].closure["dag"])
        elif fault == "occurrence":
            root = b.literal(tx, "ca-" + "f" * 32)
        changed = clone(tx, final_t, fields=changes, root=root)
        attempt_name = next(n for n, v in old.items() if v == final_t)
        old[attempt_name] = changed
        if fault == "tree":
            old["inputs"] = frozen["q"].closure["dag"]
        parents = tx.get_commit(final).parents
        if fault == "parent":
            parents = (frozen["q"].commit, parents[0])
        bad = tx.put_commit(tx.put_tree(old), parents=parents)
    with pytest.raises(ValueError):
        app.inspect_completion(path, commit=bad)


@pytest.mark.parametrize("fault", ["role", "root", "extra", "request", "decision", "selection", "attempt", "result", "parent", "tree"])
def test_outer_W_own_Q_THIS_D_OLD_T_R_strict_native_delta(case, fault):
    path, frozen = case
    commit = frozen["reused"].reused
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, commit)
        wn = "outer-reuse-" + frozen["reused"].request_id
        dag = entries[wn]
        fields = tx.get_dag(dag).bindings
        changes, root = {}, None
        if fault == "role":
            changes["role"] = b.literal(tx, "wrong")
        elif fault == "root":
            root = fields["request"]
        elif fault == "extra":
            changes["extra"] = b.literal(tx, 1)
        elif fault in ("request", "decision", "selection", "attempt", "result"):
            changes[fault] = tx.put_subdag(frozen["q"].closure["dag"])
            if fault == "result":
                root = changes[fault]
        entries[wn] = clone(tx, dag, fields=changes, root=root)
        if fault == "tree":
            entries["extra"] = dag
        parents = tx.get_commit(commit).parents
        if fault == "parent":
            parents = (frozen["q"].commit,)
        bad = tx.put_commit(tx.put_tree(entries), parents=parents)
    with pytest.raises((ValueError, KeyError)):
        app.inspect_reuse(path, commit=bad)


def test_changed_valid_capture_identity_cannot_reuse_even_equal_intent_full_MAP(case):
    path, frozen = case
    base = frozen["reused"].base
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        env = b.record(tx, app.E_ROLE, links={"add": entries["add-B"], "double": entries["double-B"], "map-get": entries["map-v1"]})
        binding = b.record(tx, app.B_ROLE, values={"adapter": d.Datum.uri(app.ADAPTER), "source": app.binding_source(env),
            "interpreter": None, "timeout-ms": None}, links={"environment": env})
        key = b.record(tx, leaf.K_ROLE, links={"binding": binding, "environment": env})
        entries["other-outer"] = b.record(tx, app.C_ROLE, values={"intent": d.Datum.uri(app.INTENT)},
            links={"binding": binding, "environment": env, "key": key})
        authored = tx.put_commit(tx.put_tree(entries), parents=(base,))
    with d.Repository(path) as repo, repo.read() as tx:
        other = app.inspect_closure(tx, authored, entries["other-outer"])
        assert other["key"] != frozen["q"].closure["key"]
    with pytest.raises(ValueError, match="does not match"):
        app.record_request(path, commit=authored, closure_name="other-outer", control="require-selected", ref="must-not-reuse")


def semantic_chain(tx, binding, levels):
    """Adversarial native semantic profiles, NOT claimed executed builtin positions."""
    current = b.record(tx, b.LITERAL_ROLE, nodes={"value": b.literal(tx, d.Datum.i64(42))}, root="value")
    key = b.record(tx, b.LITERAL_ROLE, nodes={"value": b.literal(tx, "x")}, root="value")
    def arguments(entries):
        rows, pairs = {}, []
        for i, (name, source) in enumerate(sorted(entries.items())):
            fields = tx.get_dag(source).bindings
            datum = b.node_value(tx, fields["value"])[0]
            key_id = tx.put_datum(name)
            pairs.append((key_id, datum))
            rows["arg-%02d" % i] = b.record(tx, b.ENTRY_ROLE, nodes={"key": tx.put_literal(key_id)}, links={"source": source})
        ledger = b.record(tx, b.ENTRIES_ROLE, links=rows)
        return b.record(tx, b.ARGUMENTS_ROLE, nodes={"value": b.literal(tx, d.Datum.map(pairs))}, links={"entries": ledger}, root="value")
    for _ in range(levels):
        container = arguments({"x": current})
        operands = arguments({"map": container, "key": key})
        current = b.record(tx, b.OPERATION_ROLE, values={"func": d.Datum.uri(b.MAP_GET)},
            links={"binding": binding, "arguments": operands}, nodes={"value": b.literal(tx, d.Datum.i64(42))}, root="value")
    # Deliberately share the original literal42 DAG; this makes level8 EXACT64,
    # with sharing proved by native content IDs, not an omitted source relationship.
    other = b.record(tx, b.LITERAL_ROLE, nodes={"value": b.literal(tx, d.Datum.i64(42))}, root="value")
    return arguments({"a": current, "b": other})


@pytest.mark.parametrize("levels,expected", [(7, 57), (8, 64)])
def test_ACTUAL_native_union_and_prospective_64_boundary_BEFORE_child(tmp_path, levels, expected, monkeypatch):
    path = tmp_path / "caller"
    base = app.initialize(path, sys.executable)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        entries["inputs"] = semantic_chain(tx, entries["map-v1"], levels)
        commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
    with d.Repository(path) as repo, repo.read() as tx:
        seen = set()
        app.arguments(tx, commit, entries["inputs"], ("a", "b"), seen)
        assert len(seen) == expected
    q = app.record_request(path, commit=commit, ref="outer")
    monkeypatch.setattr(app.ex, "execute_exchange", lambda *a, **k: pytest.fail("budget BEFORE child"))
    if levels == 8:
        # Exact64 source graph plus required list support exceeds aggregate budget before T.
        with pytest.raises(ValueError, match="union exceeds64"):
            bridge.Session(path, q, tmp_path / "session")
    else:
        session = bridge.Session(path, q, tmp_path / "session")
        session.map_get(session.input, "a")
        assert len(session.seen) == 64
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(bridge.SessionError, match="reservation exceeds64"):
            session.map_get(session.input, "b")
        assert (path / "data.mdb").read_bytes() == before
        assert len(session.getters) == 1 and session.poisoned


def test_moved_defaults_cannot_retarget_prepared_call_BEFORE_dispatch(case, tmp_path, monkeypatch):
    path, frozen = case
    moved = app.promote_defaults(path, commit=frozen["reused"].reused, ref="defaults")
    q = app.record_request(path, commit=moved, ref="fresh-after-defaults")
    publications = []
    def host_entry(context, source, interpreter, timeout):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(local, "child_context", lambda *a, **k: context)
            exec(compile(source, "HOST captured leaf entry", "exec"), {})
        publications.append(context)
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    monkeypatch.setattr(local, "_execute", host_entry)
    session = bridge.Session(path, q, tmp_path / "partial")
    session.map_get(session.input, "a")
    session.map_get(session.input, "b")
    result = session.invoke(session.tokens[0], session.input)
    assert len(publications) == 1
    assert publications[0].binding == q.closure["add"]["binding"]
    assert result.value == d.Datum.i64(42)
    session.ended = True  # Deliberately retained partial outer; HOST only, no live child/handle.

