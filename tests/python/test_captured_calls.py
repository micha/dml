"""NEW outer convention. HOST leaf publication substitutes are NOT installed custody."""

from pathlib import Path
import sys

import daggerml as d
from daggerml import builtin as b, local, transfer
import pytest

ROOT = Path(__file__).resolve().parents[2]
_saved = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    import captured_calls as app
    import captured_call_adapter as adapter
    import captured_call_leaf as leaf
    import captured_call_funcs as logical
    import captured_call_session as bridge
    import composed_node_funcs as funcs
finally:
    sys.path[:] = _saved


@pytest.fixture
def initial(tmp_path):
    path = tmp_path / "caller"
    base = app.initialize(path, sys.executable)
    prepared = app.prepare_arguments(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs", ref="prepared")
    swapped = app.prepare_arguments(path, commit=prepared, values={"a": 29, "b": 13}, inputs_name="swapped", ref="swapped")
    return path, swapped


@pytest.fixture
def host(monkeypatch):
    """Actual native writes/protocol; explicit HOST substitute for OS launch/wait."""
    calls = []
    def publication(context, source, interpreter, timeout):
        with d.Repository(context.repository_path) as repo, repo.read() as tx:
            q = tx.get_dag(context.request)
            intent = b.scalar(tx, q.bindings["intent"], "uri")
            env = None
            for dag in b.Inspector(tx, commit=context.pre_dispatch).retained:
                fields = tx.get_dag(dag).bindings
                if "role" in fields and b.scalar(tx, fields["role"], "string") == leaf.C_ROLE:
                    if b.link(tx, fields["binding"]) == context.binding:
                        env = b.link(tx, fields["environment"])
            assert env is not None
        func = funcs.add if intent == leaf.ADD else funcs.double
        leaf.publish(context, env, intent, *leaf.sources(), func)
        calls.append(context)
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    monkeypatch.setattr(local, "_execute", publication)
    return calls


def fresh(path, commit, root, number, **controls):
    q = app.record_request(path, commit=commit, ref="outer-%d" % number, **controls)
    final = adapter.execute(path, q, workspace=root / ("execution-%d" % number))
    return q, final, app.inspect_completion(path, commit=final)


def pin_double(path, commit, call):
    with d.Repository(path) as repo, repo.read() as tx:
        fields = tx.get_dag(call).bindings
        slot = b.scalar(tx, fields["selection-slot"], "string")
    selected, _ = app.inspect_leaf_success(path, commit=commit, slot=slot)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, commit)
        entries[app.DOUBLE_SLOT] = selected.dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref("pin-double", authored)
    return authored


def test_initial_metadata_exact_B_E_key_defaults_and_old_consumers(initial, tmp_path):
    path, commit = initial
    with d.Repository(path) as repo, repo.read() as tx:
        entries = app.tree(tx, commit)
        outer = app.inspect_closure(tx, commit, entries["outer"])
        assert outer["add"]["dag"] == entries["add-A"]
        assert outer["double"]["dag"] == entries["double-A"]
        assert outer["key"] != outer["add"]["key"]
        assert b.scalar(tx, tx.get_dag(outer["binding"]).bindings["source"], "bytes") == app.binding_source(outer["environment"])
        with pytest.raises(ValueError):
            b.inspect_binding(tx, outer["binding"])
    with pytest.raises(ValueError):
        app.public_prepare(path, commit, "outer", "inputs", app.INTENT)
    moved = app.promote_defaults(path, commit=commit, ref="defaults")
    with d.Repository(path) as repo, repo.read() as tx:
        new = app.tree(tx, moved)
        assert new["default-add"] == entries["add-B"]
        assert new["outer"] == entries["outer"]
        assert set(n for n in new if new[n] != entries[n]) == {"default-add", "default-double"}


def test_actual_logical_calls_direct_sources_shared_content_but_distinct_positions(initial, tmp_path, host):
    path, commit = initial
    q, final, got = fresh(path, commit, tmp_path, 1)
    assert got["outcome"] == "success" and got["datum"] is not None
    assert len(host) == 2 and len(got["getters"]) == len(got["calls"]) == 2
    assert len(got["semantic_ids"]) == 34
    with d.Repository(path) as repo, repo.read() as tx:
        first = tx.get_dag(got["calls"][0]).bindings
        pending = tx.get_dag(b.link(tx, first["pending"])).bindings
        add_q = b.link(tx, pending["request"])
        assert b.link(tx, tx.get_dag(add_q).bindings["inputs"]) == q.inputs.dag
        add_r = b.link(tx, first["result"])
        result = b.Inspector(tx, commit=final).node(got["leaf_result"])
        assert result.value == d.Datum.i64(84)
        add_fields = tx.get_dag(add_r).bindings
        trace = b.Inspector(tx, commit=final).trace(b.link(tx, add_fields["trace"]), request=add_q, inputs=q.inputs.dag)
        assert tuple(v.dag for v in trace) == got["getters"]
        # Shared operation DAGs DO NOT collapse separate ordered ledgers/positions.
        assert len(trace) + len(got["getters"]) == 4
        second = tx.get_dag(got["calls"][1]).bindings
        double_pending = tx.get_dag(b.link(tx, second["pending"])).bindings
        full, sources = app.arguments(tx, final, b.link(tx, double_pending["inputs"]), ("x",), set())
        assert sources["x"].dag == add_r
        assert tx.get_commit(final).parents != (q.commit,)


def test_outer_hit_no_invocation_swapped_inner_ownQ_OLD_chain_and_fresh_default_pin(initial, tmp_path, host, monkeypatch):
    depths, before_return = [], []
    check_depth = app.authority_depth
    finish = bridge.Session.finish
    active = [False]
    def measured_depth(depth):
        depths.append(depth)
        if active[0]:
            before_return.append(depth)
        return check_depth(depth)
    def measured_finish(self, *a, **k):
        active[0] = True
        try:
            return finish(self, *a, **k)
        finally:
            active[0] = False
    monkeypatch.setattr(app, "authority_depth", measured_depth)
    monkeypatch.setattr(bridge.Session, "finish", measured_finish)
    path, commit = initial
    q1, f1, g1 = fresh(path, commit, tmp_path, 1)
    selected = app.select_outer(path, commit=f1, completion=f1, ref="selected-outer")
    pinned = pin_double(path, selected, g1["calls"][1])
    moved = app.promote_defaults(path, commit=pinned, ref="defaults")
    q2 = app.record_request(path, commit=moved, control="require-selected", double_control="require-selected", ref="outer-2")
    assert q2.reused is not None and len(host) == 2
    assert app.inspect_reuse(path, commit=q2.reused).selected["attempt"] == g1["attempt"]
    with pytest.raises(ValueError, match="hit"):
        adapter.execute(path, q2, workspace=tmp_path / "must-not-create")
    assert not (tmp_path / "must-not-create").exists()
    q3, f3, g3 = fresh(path, q2.reused, tmp_path, 3, inputs_name="swapped", control="try-selected", double_control="require-selected")
    assert len(host) == 3 and len(g3["semantic_ids"]) == 50
    with d.Repository(path) as repo, repo.read() as tx:
        old = tx.get_dag(g1["calls"][1]).bindings
        new = tx.get_dag(g3["calls"][1]).bindings
        assert b.link(tx, old["attempt"]) == b.link(tx, new["attempt"])
        assert b.link(tx, old["result"]) == b.link(tx, new["result"])
        pn = tx.get_dag(b.link(tx, new["pending"])).bindings
        po = tx.get_dag(b.link(tx, old["pending"])).bindings
        assert b.link(tx, pn["request"]) != b.link(tx, po["request"])
        ni, ns = app.arguments(tx, f3, b.link(tx, pn["inputs"]), ("x",), set())
        oi, os = app.arguments(tx, f3, b.link(tx, po["inputs"]), ("x",), set())
        assert ni.datum == oi.datum and ns["x"].dag != os["x"].dag
        assert ns["x"].dag == b.link(tx, tx.get_dag(g3["calls"][0]).bindings["result"])
    q4, f4, g4 = fresh(path, f3, tmp_path, 4)
    assert len(host) == 5
    assert g4["closure"] == g1["closure"]
    assert app.inspect_selection(path, commit=f4)["attempt"] == g1["attempt"]
    assert len(g1["getters"]) + len(g3["getters"]) + len(g4["getters"]) + 3 * 2 + 2 == 14
    assert len({q1.request, q2.request, q3.request, q4.request}) == 4
    assert max(depths) == max(before_return) == 5
    depths.clear()
    app.inspect_completion(path, commit=f4)
    assert max(depths) == 5  # SAME native final reader path, not merely selected basis before dispatch.


def test_session_handles_order_guard_and_caught_poison(initial, tmp_path):
    path, commit = initial
    q = app.record_request(path, commit=commit, ref="outer-1")
    session = bridge.Session(path, q, tmp_path / "session")
    with pytest.raises(bridge.SessionError, match="guard"):
        session.invoke(session.tokens[0], session.input)
    with pytest.raises(bridge.SessionError, match="poison"):
        session.map_get(session.input, "a")
    failure = session.fail(bridge.SessionError("caught"))
    assert app.inspect_completion(path, commit=failure)["outcome"] == "failure"
    with pytest.raises(bridge.SessionError, match="ended"):
        session.arguments({})


@pytest.mark.parametrize("values", [{"a": True, "b": 1}, {"a": 1}, {"a": 1.0, "b": 2}, {"a": 2**63, "b": 0}])
def test_invalid_input_prewrite(initial, values):
    path, commit = initial
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, TypeError, OverflowError)):
        app.prepare_arguments(path, commit=commit, values=values, inputs_name="bad", ref="bad")
    assert (path / "data.mdb").read_bytes() == before
