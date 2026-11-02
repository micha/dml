"""Strict example roles/branches and public-success ORIGINAL-chain poisoning controls."""

from dataclasses import replace

import daggerml as d
from daggerml import builtin as b, exchange as ex, local
import pytest

from test_composed_node_calls import (app, initial, upstream, downstream, request, host_execute,
                                      select, reading, compose_next)
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged


@pytest.mark.parametrize("field,value", [("source", b"wrong"), ("adapter", d.Datum.uri("urn:wrong")),
                                          ("interpreter", "relative"), ("interpreter", "/a\0b"),
                                          ("timeout-ms", 0), ("timeout-ms", 3600001)])
def test_captured_binding_exact_fixed_contract_pre_Q(initial, field, value):
    path, base = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        entries["add-binding"] = clone(tx, entries["add-binding"], fields={field: b.literal(tx, value)})
        corrupt = tx.put_commit(tx.put_tree(entries), parents=(base,))
    prepared = app.prepare_add(path, commit=corrupt, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="input-1")
    with pytest.raises(ValueError):
        request(path, prepared, app.ADD, 1)


def test_wrong_builtin_binding_and_wrong_typed_arguments_pre_Q(initial):
    path, base = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        entries["map-get-v1"] = entries["list-get-v1"]
        wrong_binding = tx.put_commit(tx.put_tree(entries), parents=(base,))
        entries = app.tree(tx, base)
        with b.Recorder(tx, commit=base) as rec:
            args = rec.arguments({"a": rec.literal(True), "b": rec.literal(29)})
            entries["inputs-1"] = rec.dag(args)
        wrong_args = tx.put_commit(tx.put_tree(entries), parents=(base,))
    prepared = app.prepare_add(path, commit=wrong_binding, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="wrong")
    for commit in (prepared, wrong_args):
        with pytest.raises(ValueError):
            request(path, commit, app.ADD, 1)
    # Semantic arguments ARE strict; native datum/native literal IDs are not nodes.
    with pytest.raises(b.BuiltinError):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                rec.arguments({"x": d.Datum.i64(42)})


def test_composition_absent_names_and_depth_intent_guards(upstream):
    path, base, q1, s1 = upstream
    with pytest.raises(ValueError, match="names must differ"):
        app.compose_double(path, commit=s1.commit, producer_slot="producer-1", inputs_name="same", composition_name="same", ref="same")
    with pytest.raises(ValueError, match="both be absent"):
        app.compose_double(path, commit=s1.commit, producer_slot="producer-1", inputs_name="inputs-1", composition_name="newC", ref="newC")
    with pytest.raises(ValueError, match="exceeds"):
        app.inspect_producer(path, commit=s1.commit, slot="producer-1", intent=app.ADD, depth=5)
    with pytest.raises(ValueError, match="intent differs"):
        app.inspect_producer(path, commit=s1.commit, slot="producer-1", intent=app.DOUBLE)
    with pytest.raises(ValueError, match="absent"):
        app.prepare_add(path, commit=s1.commit, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="again")


def test_selected_ORIGINAL_C_chain_poison_even_value_mismatch(upstream, tmp_path, monkeypatch):
    path, base, q1, s1 = upstream
    c = app.compose_double(path, commit=s1.commit, producer_slot="producer-1", inputs_name="inputs-2", composition_name="composition-2", ref="composed-2")
    q2 = request(path, c.commit, app.DOUBLE, 2)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, c.commit)
        badC = clone(tx, c.dag, fields={"selection-slot": b.literal(tx, "nonexistent")})
        entries["composition-2"] = badC
        bad_basis = tx.put_commit(tx.put_tree(entries), parents=(c.base,))
        entries = app.tree(tx, q2.decision.commit)
        entries["composition-2"] = badC
        entries["decision-2"] = clone(tx, q2.decision.dag, fields={"composition": tx.put_subdag(badC)})
        badD = tx.put_commit(tx.put_tree(entries), parents=(bad_basis,))
    # Public Q/S validate execution history, not the example D/C semantic claims.
    recorded = ex.record_exchange_request(path, commit=badD, binding_name="double-binding", inputs_name="inputs-2", intent_uri=app.DOUBLE, ref="poison-Q")
    fake = replace(q2, recorded=recorded)
    run, expected, packet, received = host_execute(path, tmp_path, fake, 2, monkeypatch)
    s2 = select(path, fake, expected, packet, received, app.SLOT)
    prepared = app.prepare_add(path, commit=s2.commit, values={"a": 13, "b": 30}, inputs_name="inputs-3", ref="input-3")
    q3 = request(path, prepared, app.ADD, 3)
    run, expected, packet, received = host_execute(path, tmp_path, q3, 3, monkeypatch)
    s3 = select(path, q3, expected, packet, received, "producer-3")
    c4 = app.compose_double(path, commit=s3.commit, producer_slot="producer-3", inputs_name="inputs-4", composition_name="composition-4", ref="composed-4")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(KeyError, match="nonexistent"):
        request(path, c4.commit, app.DOUBLE, 4)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["zero-parent", "extra-tree", "decision-action"])
def test_public_success_wrong_ORIGINAL_add_decision_chain_reject(upstream, tmp_path, monkeypatch, fault):
    path, base, q1, s1 = upstream
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, q1.decision.commit)
        if fault == "extra-tree":
            entries["extra"] = q1.recorded.inputs
        if fault == "decision-action":
            entries[q1.decision.name] = clone(tx, q1.decision.dag, fields={"action": b.literal(tx, "reuse-selected")})
        badD = tx.put_commit(tx.put_tree(entries), parents=() if fault == "zero-parent" else (q1.decision.base,))
    recorded = ex.record_exchange_request(path, commit=badD, binding_name="add-binding", inputs_name="inputs-1", intent_uri=app.ADD, ref="poison-Q")
    fake = replace(q1, recorded=recorded)
    run, expected, packet, received = host_execute(path, tmp_path, fake, 7, monkeypatch)
    selected = select(path, fake, expected, packet, received, "poison-producer")
    with pytest.raises(ValueError):
        app.compose_double(path, commit=selected.commit, producer_slot="poison-producer", inputs_name="newinputs", composition_name="newC", ref="newC")


@pytest.mark.parametrize("fault", ["decision-parent", "decision-tree", "decision-claim", "submission-parent", "W-parent", "W-Q", "fresh-W"])
def test_strict_decision_submission_satisfaction_profile_reads(downstream, fault):
    path, base, q1, s1, c2, q2, s2 = downstream
    c4 = app.compose_double(path, commit=s2.commit, producer_slot="producer-1", inputs_name="inputs-4", composition_name="composition-4", ref="composed-4")
    q4 = request(path, c4.commit, app.DOUBLE, 4, hit=True)
    with d.Repository(path) as repo, repo.write() as tx:
        if fault.startswith("decision-"):
            entries = app.tree(tx, q4.decision.commit)
            if fault == "decision-tree":
                entries["extra"] = s1.result
            if fault == "decision-claim":
                entries[q4.decision.name] = clone(tx, q4.decision.dag, fields={"reason": b.literal(tx, "invented")})
            bad = tx.put_commit(tx.put_tree(entries), parents=() if fault == "decision-parent" else (q4.decision.base,))
        elif fault == "submission-parent":
            bad = tx.put_commit(tx.get_commit(q4.recorded.commit).tree)
        else:
            entries = app.tree(tx, q4.reused.commit)
            if fault == "W-Q":
                entries["reuse-" + q4.recorded.request_id] = clone(tx, q4.reused.dag, fields={"request": tx.put_subdag(q2.recorded.request)})
            bad = tx.put_commit(tx.put_tree(entries), parents=(c4.commit,) if fault == "W-parent" else (q4.recorded.commit,))
    with pytest.raises(ValueError):
        if fault.startswith("decision-"):
            app.inspect_decision(path, commit=bad, decision_name=q4.decision.name)
        elif fault == "submission-parent":
            app.inspect_request(path, commit=bad, request=q4.recorded.request, decision_name=q4.decision.name)
        elif fault == "fresh-W":
            app.inspect_request(path, commit=q2.recorded.commit, request=q2.recorded.request, decision_name=q2.decision.name, satisfaction_commit=bad)
        else:
            app.inspect_request(path, commit=q4.recorded.commit, request=q4.recorded.request, decision_name=q4.decision.name, satisfaction_commit=bad)
    with pytest.raises(ValueError, match="already present"):
        app._publish_reuse(path, replace(q4.recorded, commit=q4.reused.commit), s2, "again")


def test_required_selected_value_and_absence_reject(upstream, downstream):
    path, base, q1, s1 = upstream
    c = app.compose_double(path, commit=s1.commit, producer_slot="producer-1", inputs_name="newinputs", composition_name="newC", ref="newC")
    with pytest.raises(ValueError, match="no match"):
        app.record_request(path, commit=c.commit, intent=app.DOUBLE, binding_name="double-binding", inputs_name="newinputs",
                           composition_name="newC", decision_name="require", decision_ref="require-d", submission_ref="require-q", control="require-selected")
    path, base, q1, s1, c2, q2, s2 = downstream
    c = app.compose_double(path, commit=s2.commit, producer_slot="producer-1", inputs_name="inputs-4", composition_name="composition-4", ref="composed-4")
    assert reading(path, request(path, c.commit, app.DOUBLE, 4, hit=True, control="require-selected")).reason == "selected-value"


def test_coherent_normal_return_WRONG_ownQ_or_nonI64_reject_before_composition(initial, tmp_path, monkeypatch):
    path, base = initial
    prepared = app.prepare_add(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="input-1")
    other = app.record_request(path, commit=prepared, intent=app.ADD, binding_name="add-binding", inputs_name="inputs-1",
                               decision_name="other", decision_ref="other-d", submission_ref="other-q")
    q = request(path, other.recorded.commit, app.ADD, 1)
    publish = local.publish_result
    def coherent_WRONG_owner(tx, context, result):
        fields = tx.get_dag(result).bindings
        trace = clone(tx, b.link(tx, fields["trace"]), fields={"request": tx.put_subdag(other.recorded.request)})
        altered = clone(tx, result, fields={"request": tx.put_subdag(other.recorded.request), "trace": tx.put_subdag(trace)})
        return publish(tx, context, altered)
    monkeypatch.setattr(local, "publish_result", coherent_WRONG_owner)
    run, expected, packet, received = host_execute(path, tmp_path, q, 1, monkeypatch)
    s = select(path, q, expected, packet, received, "producer-1")
    with pytest.raises(ValueError, match="owner/value differs"):
        app.inspect_producer(path, commit=s.commit, slot="producer-1", intent=app.ADD)


def test_fresh_T_for_reuse_Q_is_NOT_selected_original_fresh_producer(downstream, tmp_path, monkeypatch):
    path, base, q1, s1, c2, q2, s2 = downstream
    c = app.compose_double(path, commit=s2.commit, producer_slot="producer-1", inputs_name="inputs-4", composition_name="composition-4", ref="composed-4")
    reused = request(path, c.commit, app.DOUBLE, 4, hit=True)
    # Test-private deliberate policy violation: public local mechanics permit fresh T for own Q.
    run, expected, packet, received = host_execute(path, tmp_path, reused, 4, monkeypatch)
    bad = select(path, reused, expected, packet, received, "policy-violation")
    with pytest.raises(ValueError, match="ORIGINAL fresh"):
        app.inspect_producer(path, commit=bad.commit, slot="policy-violation", intent=app.DOUBLE)


def test_public_prepare_response_dimension_substitution_guards(initial, monkeypatch):
    path, base = initial
    prepared = app.prepare_add(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="input-1")
    original = app._prepare
    def altered(*args, **kwargs):
        got = original(*args, **kwargs)
        return replace(got, inputs=got.binding)
    monkeypatch.setattr(app, "_prepare", altered)
    with pytest.raises(ValueError, match="public preparation dimensions"):
        request(path, prepared, app.ADD, 1)
    monkeypatch.setattr(app, "_prepare", original)
    q = request(path, prepared, app.ADD, 1)
    def altered_own_Q(*args, **kwargs):
        got = original(*args, **kwargs)
        return replace(got, inputs=got.binding) if len(args) == 6 else got
    monkeypatch.setattr(app, "_prepare", altered_own_Q)
    with pytest.raises(ValueError, match="own Q dimensions"):
        reading(path, q)
