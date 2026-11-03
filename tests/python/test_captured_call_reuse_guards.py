"""Finite current-source reuse bridge authority; not four-row/deep/installed story.

One original HOST outer supplies two successful LOCAL publications; one new HOST add
supplies distinct actual R. Second ordinary position reuses OLD double with NO child.
This measures currently missing bridge/W paths and supplies coherent last snapshots.
"""

from pathlib import Path
import sys

import daggerml as d
from daggerml import builtin as b, local, transfer
import pytest

from test_exchange_records import clone
from test_captured_calls import app, bridge, leaf, fresh, pin_double
from test_captured_call_history_guards import last_phase


@pytest.fixture(scope="module")
def reuse_history(tmp_path_factory):
    root = tmp_path_factory.mktemp("captured-reuse-guards")
    path = root / "caller"
    base = app.initialize(path, sys.executable)
    base = app.prepare_arguments(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
    base = app.prepare_arguments(path, commit=base, values={"a": 29, "b": 13}, inputs_name="swapped", ref="swapped")
    published = []
    def host(context, source, interpreter, timeout):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(local, "child_context", lambda *a, **k: context)
            exec(compile(source, "HOST captured reuse entry", "exec"), {})
        published.append(context)
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(local, "_execute", host)
        q1, final, got = fresh(path, base, root, 1)
        pinned = pin_double(path, final, got["calls"][1])
        q = app.record_request(path, commit=pinned, inputs_name="swapped", double_control="require-selected", ref="newQ")
        session = bridge.Session(path, q, root / "partial")
        session.nodes.map_get(session.input, "a")
        session.nodes.map_get(session.input, "b")
        new_add = session.invoker.invoke(session.tokens[0], session.input)
        arguments = session.nodes.arguments({"x": new_add})
        before = len(published)
        result = session.invoker.invoke(session.tokens[1], arguments)
        assert len(published) == before == 3 and result.value == d.Datum.i64(84)
        spine = app.inspect_spine(path, session.current, q.request, session.initial, session.aid, session.seen)
        assert len(spine["calls"]) == 2 and len(session.seen) == 50
        selected, _ = app.inspect_leaf_success(path, commit=session.current, slot=app.DOUBLE_SLOT)
        with d.Repository(path) as repo, repo.read() as tx:
            old = tx.get_dag(got["calls"][1]).bindings
            current = tx.get_dag(session.calls[1]).bindings
            assert tuple(b.link(tx, current[n]) for n in ("attempt", "result")) == tuple(b.link(tx, old[n]) for n in ("attempt", "result"))
            own_q = b.link(tx, tx.get_dag(b.link(tx, current["pending"])).bindings["request"])
            assert own_q != b.link(tx, tx.get_dag(b.link(tx, old["pending"])).bindings["request"])
            app.inspect_leaf_reuse(tx, session.current, own_q, selected)
        session.ended = True  # Known HOST population; retained PARTIAL outer, no OS/native handles live.
    return dict(bundle=transfer.export_commit(path, commit=session.current), q=q, commit=session.current,
                initial=session.initial, aid=session.aid, selected=selected, own_q=own_q, HOST_publications=3)


@pytest.fixture
def reused_case(tmp_path, reuse_history):
    path = tmp_path / "retained-reuse"
    with d.Repository(path, create=True):
        pass
    transfer.import_commit(path, reuse_history["bundle"], ref="history")
    return path, reuse_history


def test_current_reuse_positive_ownQ_OLD_T_R_and_no_new_double_publication(reused_case):
    path, got = reused_case
    assert got["HOST_publications"] == 3
    result = app.inspect_spine(path, got["commit"], got["q"].request, got["initial"], got["aid"], set())
    assert len(result["calls"]) == 2


@pytest.mark.parametrize("fault,message", [("publication", "reuse phase publication differs"), ("W-tree", "reuse phase W tree differs"), ("T", "NEW Q/OLD selected T/R differs"), ("done-slot", "pinned S and prior W")])
def test_coherent_LAST_reuse_phase_or_done_native_guard(reused_case, fault, message):
    path, got = reused_case
    with d.Repository(path) as repo, repo.write() as tx:
        kind = "leaf-done" if fault == "done-slot" else "leaf-reused"
        commit, phase_name, phase, index = last_phase(tx, got["commit"], kind)
        original = tx.get_commit(commit)
        entries = app.tree(tx, commit)
        fields = tx.get_dag(phase).bindings
        changes = {}
        if fault == "publication":
            changes["reuse-commit"] = b.literal(tx, got["q"].commit.bytes)
        elif fault == "done-slot":
            call = b.link(tx, fields["call"])
            changed = clone(tx, call, fields={"selection-slot": b.literal(tx, "wrong-slot")})
            changes["call"] = tx.put_subdag(changed)
            entries[app.payload_names(got["aid"], index, kind)["call"]] = changed
        else:
            old_w = b.link(tx, fields["reuse"])
            changed = clone(tx, old_w, fields={"attempt": tx.put_subdag(got["initial"])})
            changes["reuse"] = tx.put_subdag(changed)
            entries[app.payload_names(got["aid"], index, kind)["reuse"]] = changed
            if fault == "T":
                # Valid own-W delta and phase agree, but OLD producing T is wrong.
                parent = app.tree(tx, original.parents[0])
                wn = "reuse-" + b.scalar(tx, tx.get_dag(got["own_q"]).root, "string")
                parent[wn] = changed
                new_parent = tx.put_commit(tx.put_tree(parent), parents=tx.get_commit(original.parents[0]).parents)
                entries[wn] = changed
                original = type(original)(original.tree, (new_parent,))
                changes["previous"] = changes["reuse-commit"] = b.literal(tx, new_parent.bytes)
        entries[phase_name] = clone(tx, phase, fields=changes)
        bad = tx.put_commit(tx.put_tree(entries), parents=original.parents)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        app.inspect_spine(path, bad, got["q"].request, got["initial"], got["aid"], set())
    assert (path / "data.mdb").read_bytes() == before


def test_standalone_leaf_W_exact_ownQ_OLD_T_R_guard(reused_case):
    path, got = reused_case
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, got["commit"])
        wn = "reuse-" + b.scalar(tx, tx.get_dag(got["own_q"]).root, "string")
        entries[wn] = clone(tx, entries[wn], fields={"attempt": tx.put_subdag(got["initial"])})
        bad = tx.put_commit(tx.put_tree(entries), parents=(got["commit"],))
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(ValueError, match="leaf ownQ/OLD T/R W"):
            app.inspect_leaf_reuse(tx, bad, got["own_q"], got["selected"])
