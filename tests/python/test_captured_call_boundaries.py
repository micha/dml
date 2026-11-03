"""Meaningful cheap native profile/configuration boundaries, no OS computations."""

from dataclasses import replace
from types import SimpleNamespace

import daggerml as d
from daggerml import builtin as b, local
import pytest

from test_exchange_records import clone
from test_captured_calls import app, adapter, bridge, initial, leaf


@pytest.mark.parametrize("name", [None, "", "x/y", "a" * 129, "é"])
def test_native_name_profile(name):
    with pytest.raises(ValueError):
        app.name(name)


@pytest.mark.parametrize("depth", [-1, True, "0", 9])
def test_shared_authority_depth_type_boundary(depth):
    with pytest.raises(ValueError):
        app.authority_depth(depth)


@pytest.mark.parametrize("fault", ["intent", "map-version", "key", "source", "adapter", "interpreter", "timeout"])
def test_leaf_exact_capture_config_native_negatives(initial, fault):
    path, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, commit)
        original = entries["add-A"]
        fields = tx.get_dag(original).bindings
        changes = {}
        if fault == "intent":
            changes["intent"] = b.literal(tx, d.Datum.uri("urn:unsupported"))
        elif fault == "map-version":
            env = b.link(tx, fields["environment"])
            bad_binding = b.put_binding(tx, source_uri="dml://source/builtin/map/get/v99")
            changes["environment"] = tx.put_subdag(clone(tx, env, fields={"map-get": tx.put_subdag(bad_binding)}))
        elif fault == "key":
            key = b.link(tx, fields["key"])
            changes["key"] = tx.put_subdag(clone(tx, key, fields={"binding": tx.put_subdag(entries["add-B"])}))
        else:
            binding = b.link(tx, fields["binding"])
            value = b"wrong" if fault == "source" else d.Datum.uri("urn:wrong") if fault == "adapter" else "relative-python" if fault == "interpreter" else 0
            updated = clone(tx, binding, fields={"timeout-ms" if fault == "timeout" else fault: b.literal(tx, value)})
            changes["binding"] = tx.put_subdag(updated)
            changes["key"] = tx.put_subdag(clone(tx, b.link(tx, fields["key"]), fields={"binding": tx.put_subdag(updated)}))
        bad = clone(tx, original, fields=changes)
        with pytest.raises(ValueError):
            leaf.inspect(tx, bad, *leaf.sources())


@pytest.mark.parametrize("fault", ["outer-map", "outer-source", "outer-key", "not-retained"])
def test_outer_exact_supported_profile(initial, fault):
    path, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, commit)
        outer = entries["outer"]
        fields = tx.get_dag(outer).bindings
        changes = {}
        if fault == "outer-map":
            env = b.link(tx, fields["environment"])
            changes["environment"] = tx.put_subdag(clone(tx, env, fields={"map-get": tx.put_subdag(entries["map-v2"])}))
        elif fault == "outer-source":
            changes["binding"] = tx.put_subdag(clone(tx, b.link(tx, fields["binding"]), fields={"source": b.literal(tx, b"wrong")}))
        elif fault == "outer-key":
            changes["key"] = tx.put_subdag(clone(tx, b.link(tx, fields["key"]), fields={"environment": tx.put_subdag(entries["add-A"])}))
        else:
            changes["intent"] = b.literal(tx, d.Datum.uri("urn:unretained"))
        bad = clone(tx, outer, fields=changes)
        bad_entries = dict(entries, outer=bad)
        staged = tx.put_commit(tx.put_tree(bad_entries), parents=(commit,))
        with pytest.raises(ValueError):
            app.inspect_closure(tx, commit if fault == "not-retained" else staged, bad)


@pytest.mark.parametrize("control,double", [("bad", "fresh"), ("fresh", "bad"), ("require-selected", "fresh")])
def test_invalid_control_and_absent_required_selection_prewrite(initial, control, double):
    path, commit = initial
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.record_request(path, commit=commit, control=control, double_control=double, ref="invalid")
    assert (path / "data.mdb").read_bytes() == before


def test_no_duplicate_input_authoring_and_public_delta_checks(initial):
    path, commit = initial
    with pytest.raises(ValueError, match="already exists"):
        app.prepare_arguments(path, commit=commit, values={"a": 1, "b": 2}, inputs_name="inputs", ref="duplicate")
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, commit)
        extra = dict(entries, extra=entries["outer"])
        no_parent = tx.put_commit(tx.put_tree(extra))
        wrong_delta = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        changed = dict(extra, inputs=entries["outer"])
        wrong_preserved = tx.put_commit(tx.put_tree(changed), parents=(commit,))
        for candidate, message in ((no_parent, "single-parent"), (wrong_delta, "absent-name"), (wrong_preserved, "unrelated")):
            with pytest.raises(ValueError, match=message):
                app.single_delta(tx, candidate, ("extra",))


@pytest.mark.parametrize("fault", ["foreign-argument", "third-getter", "non-dict", "not-fresh", "premature", "head-moved", "phase-shape", "phase-name", "reservation"])
def test_cooperative_facade_and_native_head_boundary(initial, tmp_path, fault):
    path, commit = initial
    q = app.record_request(path, commit=commit, ref="q")
    if fault == "not-fresh":
        with pytest.raises(ValueError, match="hit"):
            adapter.execute(path, replace(q, action="reuse-selected"), workspace=tmp_path / "absent")
        return
    if fault == "reservation":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.update_ref("outer-request-" + q.request_id, q.base)
        with pytest.raises(ValueError, match="reservation"):
            bridge.Session(path, q, tmp_path / "absent")
        return
    session = bridge.Session(path, q, tmp_path / "session")
    if fault == "foreign-argument":
        session.map_get(session.input, "a")
        session.map_get(session.input, "b")
        action = lambda: session.invoke(session.tokens[0], bridge.Node(session.input.value))
    elif fault == "third-getter":
        session.map_get(session.input, "a")
        session.map_get(session.input, "b")
        action = lambda: session.map_get(session.input, "a")
    elif fault == "non-dict":
        action = lambda: session.arguments(None)
    elif fault == "premature":
        action = lambda: session.finish(session.input)
    elif fault == "head-moved":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.update_ref("outer-head-" + session.aid, q.commit)
        action = lambda: session.map_get(session.input, "a")
    elif fault == "phase-shape":
        action = lambda: session._phase("get-a", links={})
    else:
        with d.Repository(path) as repo, repo.write() as tx:
            entries = app.tree(tx, session.current)
            entries[app.phase_name(session.aid, 0)] = q.closure["dag"]
            injected = tx.put_commit(tx.put_tree(entries), parents=(session.current,))
            tx.update_ref("outer-head-" + session.aid, injected)
        session.current = injected
        action = lambda: session._phase("get-a", links={"node": q.inputs.dag})
    with pytest.raises((ValueError, bridge.SessionError)):
        action()
