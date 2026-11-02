"""Example-local ONE-S/Q/W/choice controls; host publication substitution, NOT story."""

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import daggerml as d
from daggerml import builtin as b, exchange as ex, local
import pytest

from test_exchange import ROOT
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged

saved = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    import builtin_workflow as app
    import builtin_funcs as funcs
    spec = importlib.util.spec_from_file_location("builtin_story_test", ROOT / "tests/builtins/installed_story.py")
    story = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(story)
finally:
    sys.path[:] = saved


@pytest.fixture
def state(tmp_path):
    path = tmp_path / "workflow"
    base, bindings, lists = story.initialize(path, sys.executable)
    a = story.construct(path, base, bindings, lists["A"], "A")
    return path, base, bindings, lists, a


workflow_state = state


@pytest.fixture
def success(workflow_state, tmp_path, monkeypatch):
    path, base, bindings, lists, a = workflow_state
    q = story.request(path, d.ObjectId.from_hex(a["commit"]), "A", 1)
    def host_publication(context, source, interpreter, timeout):
        # Test-private host seam; NOT actual child custody/installed acceptance.
        b.publish_callable(context, funcs.sum_pair, map_binding=bindings["get-v1"], list_binding=bindings["index-v1"])
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    monkeypatch.setattr(local, "_execute", host_publication)
    workspace = tmp_path / "host-publication"
    expected = ex.prepare_exchange(path, commit=q.recorded.commit, request=q.recorded.request,
                                    binding_name="sum-v1", inputs_name="A-inputs", intent_uri=app.INTENT,
                                    worker_ref="work", workspace=workspace)
    ex.execute_exchange(workspace)
    saved = tmp_path / "expected.json"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(workspace, expected))
    observation = ex.observe_exchange(ex.ExchangeHandle(workspace, expected), packet=tmp_path / "packet")
    received = ex.receive_observation(path, packet=observation.packet, expected=expected, ref="received")
    selected = app.selection.select(path, commit=received.commit, slot=app.SLOT,
                                     binding_name="sum-v1", inputs_name="A-inputs", intent_uri=app.INTENT,
                                     packet=observation.packet, expected_file=saved, ref=app.SLOT)
    return (*workflow_state, q, selected)


def request(success, **changes):
    path, base, bindings, lists, a, q, selected = success
    args = dict(commit=selected.commit, choice_name="get-choice", inputs_name="A-inputs", decision_name="new",
                decision_ref="new-d", submission_ref="new-q", reuse_ref="new-w")
    args.update(changes)
    return app.record_request(path, **args)


def reading(path, got):
    return app.inspect_request(path, commit=got.recorded.commit, request=got.recorded.request,
                               decision_name=got.decision.name, satisfaction_commit=None if got.reused is None else got.reused.commit)


def test_source_distinct_full_MAP_value_hit_requested_v2_old_v1_no_dispatch_no_auto_adoption(success, monkeypatch):
    path, base, bindings, lists, a, q, selected = success
    promoted = app.promote(path, commit=selected.commit, choice_name="get-choice", default="v2", ref="promoted")
    bb = story.construct(path, promoted, bindings, lists["B"], "B")
    monkeypatch.setattr(local, "_execute", lambda *a: pytest.fail("hit/metadata cannot dispatch"))
    hit = request(success, commit=d.ObjectId.from_hex(bb["commit"]), inputs_name="B-inputs")
    got = reading(path, hit)
    assert got.inputs.datum == got.executed.datum and got.inputs.dag != got.executed.dag
    assert got.label == "v2" and got.returned.value == d.Datum.i64(42)
    assert hit.reused.attempt == selected.attempt and hit.reused.result == selected.result
    assert hit.recorded.request != selected.request and hit.recorded.binding != selected.binding
    required = request(success, commit=hit.reused.commit, inputs_name="B-inputs", control="require-selected",
                       decision_name="required", decision_ref="required-d", submission_ref="required-q", reuse_ref="required-w")
    assert required.reused.attempt == selected.attempt
    c = story.construct(path, required.reused.commit, bindings, lists["C"], "C")
    miss = request(success, commit=d.ObjectId.from_hex(c["commit"]), inputs_name="C-inputs", reuse_ref=None,
                   decision_name="miss", decision_ref="miss-d", submission_ref="miss-q")
    assert reading(path, miss).reason == "value-mismatch" and miss.reused is None
    assert app.selection.inspect(path, commit=miss.recorded.commit, slot=app.SLOT).attempt == selected.attempt
    with d.Repository(path) as repo, repo.read() as tx:
        assert app.inspect_choice(tx, app.tree(tx, selected.commit)["get-choice"]).default == "v1"
        assert app.inspect_choice(tx, app.tree(tx, promoted)["get-choice"]).default == "v2"
        assert tx.get_commit(promoted).parents == (selected.commit,)
        changed = app.tree(tx, promoted)
        changed["get-choice"] = app.tree(tx, selected.commit)["get-choice"]
        assert changed == app.tree(tx, selected.commit)
        fields = tx.get_dag(got.returned.dag).bindings
        trace = b.link(tx, fields["trace"])
        ops = b.Inspector(tx, commit=hit.reused.commit).trace(trace, request=selected.request, inputs=selected.inputs)
        assert len(ops) == 4


@pytest.mark.parametrize("field,value", [("interpreter", d.Datum.i64(1)), ("interpreter", d.Datum.string("")),
                                          ("interpreter", d.Datum.string("relative")), ("interpreter", d.Datum.string("/a\0b")),
                                          ("timeout-ms", d.Datum.bool(True)), ("timeout-ms", d.Datum.i64(0)),
                                          ("timeout-ms", d.Datum.i64(3600001)), ("source", d.Datum.bytes(b"wrong"))])
def test_malformed_UNSELECTED_normal_binding_choice_error_before_Q(state, field, value):
    path, base, bindings, lists, a = state
    basis = d.ObjectId.from_hex(a["commit"])
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, basis)
        choice = app.inspect_choice(tx, entries["get-choice"])
        bad_normal = clone(tx, choice.normal_v2, fields={field: b.literal(tx, value)})
        entries["sum-v2"] = bad_normal
        entries["get-choice"] = clone(tx, choice.dag, fields={"normal-v2": tx.put_subdag(bad_normal)})
        corrupt = tx.put_commit(tx.put_tree(entries), parents=(basis,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.record_request(path, commit=corrupt, choice_name="get-choice", inputs_name="A-inputs", decision_name="new", decision_ref="new-d", submission_ref="new-q")
    assert_file_unchanged(path / "data.mdb", before)


def test_SAME_name_alternate_Dn_Cq_coherent_response_fakebase_BEFORE_W(success, monkeypatch):
    path = success[0]
    alternative = request(success, control="fresh", reuse_ref=None, decision_name="new", decision_ref="alt-d", submission_ref="alt-q")
    original = ex.record_exchange_request
    def alternate(*args, **kwargs):
        actual = original(*args, **kwargs)
        with d.Repository(path) as repo, repo.write() as tx:
            tx.update_ref(actual.ref, alternative.recorded.commit)
        return replace(alternative.recorded, base=actual.base, ref=actual.ref)
    monkeypatch.setattr(ex, "record_exchange_request", alternate)
    monkeypatch.setattr(app, "_publish_reuse", lambda *a: pytest.fail("alternate actual parent must reject BEFORE W"))
    with pytest.raises(ValueError, match="actual submission parent"):
        request(success)
    with d.Repository(path) as repo, repo.read() as tx:
        tx.get_ref("new-d")
        tx.get_ref("new-q")
        with pytest.raises(d.NotFoundError):
            tx.get_ref("new-w")


@pytest.mark.parametrize("fault", ["intent", "inputs", "result", "completion", "role"])
def test_corrupt_S_even_VALUE_mismatch_ERROR_not_miss(success, fault):
    path, base, bindings, lists, a, q, selected = success
    with d.Repository(path) as repo, repo.write() as tx:
        changes = {fault: tx.put_subdag(selected.result if fault == "inputs" else q.recorded.inputs)} if fault in ("inputs", "result") else {fault: b.literal(tx, d.Datum.uri("urn:wrong") if fault == "intent" else b"bad" if fault == "completion" else "wrong")}
        bad = clone(tx, selected.dag, fields=changes, root=changes.get("result"))
        entries = app.tree(tx, selected.commit)
        entries[app.SLOT] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(selected.commit,))
    c = story.construct(path, basis, bindings, lists["C"], "C")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        request(success, commit=d.ObjectId.from_hex(c["commit"]), inputs_name="C-inputs", reuse_ref=None)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["choice-default", "choice-func", "choice-map", "choice-list", "choice-name", "input-name", "override", "control", "required", "ref", "decision-name", "unneeded-w", "existing"])
def test_invalid_choice_request_profiles_prewrite_NO_Q(state, fault):
    path, base, bindings, lists, a = state
    basis = d.ObjectId.from_hex(a["commit"])
    if fault.startswith("choice-") and fault != "choice-name":
        with d.Repository(path) as repo, repo.write() as tx:
            entries = app.tree(tx, basis)
            choice = entries["get-choice"]
            changes = {"default": b.literal(tx, "v99")} if fault == "choice-default" else {"func": b.literal(tx, d.Datum.uri(b.MAP_EMPTY))} if fault == "choice-func" else {"map-v1" if fault == "choice-map" else "list-v1": tx.put_subdag(bindings["get-v2"])}
            entries["get-choice"] = clone(tx, choice, fields=changes)
            basis = tx.put_commit(tx.put_tree(entries), parents=(basis,))
    args = dict(commit=basis, choice_name="get-choice", inputs_name="A-inputs", decision_name="decision", decision_ref="decision-d", submission_ref="decision-q")
    args.update({"choice_name": "bad/name"} if fault == "choice-name" else {"inputs_name": "bad/name"} if fault == "input-name" else {"override": "v99"} if fault == "override" else {"control": "unknown"} if fault == "control" else {"control": "require-selected"} if fault == "required" else {"decision_ref": "decision-q"} if fault == "ref" else {"decision_name": "request-q-collision"} if fault == "decision-name" else {"reuse_ref": "unneeded"} if fault == "unneeded-w" else {"decision_name": "A-inputs"} if fault == "existing" else {})
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.record_request(path, **args)
    assert_file_unchanged(path / "data.mdb", before)


def test_request_decision_NATIVE_claims_parent_tree_W_owner(success):
    path = success[0]
    got = request(success)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, got.decision.commit)
        fields = tx.get_dag(got.decision.dag).bindings
        # Keep exact root/shape while changing logical decision; recomputation must reject.
        bad = clone(tx, got.decision.dag, fields={"reason": b.literal(tx, "invented")})
        entries[got.decision.name] = bad
        corrupt = tx.put_commit(tx.put_tree(entries), parents=(got.decision.base,))
    with pytest.raises(ValueError, match="claims differ"):
        app.inspect_decision(path, commit=corrupt, decision_name=got.decision.name)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, got.reused.commit)
        entries["reuse-" + got.recorded.request_id] = clone(tx, got.reused.dag, fields={"request": tx.put_subdag(success[-1].request)})
        bad_w = tx.put_commit(tx.put_tree(entries), parents=(got.recorded.commit,))
    with pytest.raises(ValueError, match="ownQ"):
        app.inspect_request(path, commit=got.recorded.commit, request=got.recorded.request,
                             decision_name=got.decision.name, satisfaction_commit=bad_w)
    with pytest.raises(ValueError, match="already present"):
        app._publish_reuse(path, replace(got.recorded, commit=got.reused.commit), got.decision.selected, "again")
