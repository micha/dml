"""Selected success/normal-return/own-Q authority and finite noncomputational negatives."""

from dataclasses import replace
from types import SimpleNamespace

import daggerml as d
from daggerml import builtin as b, exchange as ex, local, transfer
import pytest

from test_caller_requests import assert_file_unchanged
from test_exchange_records import clone
from test_composed_node_calls import (app, funcs, initial, upstream, downstream, request,
                                      compose_next, host_execute, select, reading)


@pytest.mark.parametrize("func,values", [(funcs.add, {"a": True, "b": 29}), (funcs.add, {"a": 13, "b": 29.0}),
                                         (funcs.double, {"x": True}), (funcs.double, {"x": 42.0}),
                                         (funcs.add, {"a": 2**63 - 1, "b": 1}),
                                         (funcs.double, {"x": 2**62})])
def test_logical_code_exact_I64_and_overflow_abort_native_write(initial, func, values):
    path, base = initial
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, OverflowError)):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                args = rec.arguments({key: rec.literal(value) for key, value in values.items()})
                bindings = app.tree(tx, base)
                ops = rec.operations(map_binding=bindings["map-get-v1"], list_binding=bindings["list-get-v1"])
                func(args, ops)
    assert_file_unchanged(path / "data.mdb", before)


def test_failed_completion_with_valid_provisional_return_is_NOT_success_authority(initial, tmp_path, monkeypatch):
    path, base = initial
    prepared = app.prepare_add(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="input-1")
    q = request(path, prepared, app.ADD, 1)
    publish = b.publish_callable
    def retain_publication(*args, **kwargs):
        committed = publish(*args, **kwargs)
        workspace = tmp_path / "workspace-1"
        handle = ex.ExchangeHandle(workspace, ex.read_exchange_spec(workspace))
        ex.observe_exchange(handle, packet=tmp_path / "publication")
        return committed
    monkeypatch.setattr(b, "publish_callable", retain_publication)
    run, expected, packet, received = host_execute(path, tmp_path, q, 1, monkeypatch, failed=True)
    assert run.outcome == "failure" and run.evidence is not None
    with d.Repository(path) as repo, repo.read() as tx:
        assert b.Inspector(tx, commit=received.commit).node(run.evidence).value == d.Datum.i64(42)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="successful recorded F"):
        select(path, q, expected, packet, received, "producer-1")
    assert_file_unchanged(path / "data.mdb", before)
    # Actual publication packet remains provisional even with valid R42.
    publication = tmp_path / "publication"
    with pytest.raises(ValueError, match="successful recorded F"):
        app.selection.select(path, commit=received.commit, slot="provisional", binding_name="add-binding",
                             inputs_name="inputs-1", intent_uri=app.ADD, packet=publication,
                             expected_file=expected, ref="provisional")


@pytest.mark.parametrize("fault", ["request", "inputs", "value", "returned", "trace-owner", "trace-value", "return-role"])
def test_forged_return_valid_native_public_success_not_structural_authority(initial, tmp_path, monkeypatch, fault):
    path, base = initial
    prepared = app.prepare_add(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="input-1")
    # Alternate legitimate Q serves as same-input WRONG owner, no extra computation.
    other = app.record_request(path, commit=prepared, intent=app.ADD, binding_name="add-binding", inputs_name="inputs-1",
                               decision_name="other", decision_ref="other-d", submission_ref="other-q")
    q = request(path, other.recorded.commit, app.ADD, 1)
    original = local.publish_result
    def poisoned(tx, context, result):
        fields = tx.get_dag(result).bindings
        changes = {}
        if fault in ("request", "inputs"):
            changes[fault] = tx.put_subdag(other.recorded.request if fault == "request" else app.tree(tx, base)["add-binding"])
        elif fault in ("value", "returned"):
            changes[fault] = b.literal(tx, 43) if fault == "value" else tx.put_subdag(context.inputs)
        elif fault == "return-role":
            changes["role"] = b.literal(tx, "wrong")
        else:
            trace = b.link(tx, fields["trace"])
            if fault == "trace-owner":
                altered = clone(tx, trace, fields={"request": tx.put_subdag(other.recorded.request)})
            else:
                operation = b.link(tx, tx.get_dag(trace).bindings["call-00"])
                altered_op = clone(tx, operation, fields={"value": b.literal(tx, 999)}, root=b.literal(tx, 999))
                altered = clone(tx, trace, fields={"call-00": tx.put_subdag(altered_op)})
            changes["trace"] = tx.put_subdag(altered)
        altered = clone(tx, result, fields=changes, root=changes.get("value"))
        return original(tx, context, altered)
    monkeypatch.setattr(local, "publish_result", poisoned)
    run, expected, packet, received = host_execute(path, tmp_path, q, 1, monkeypatch)
    s = select(path, q, expected, packet, received, "producer-1")
    assert app.selection.inspect(path, commit=s.commit, slot="producer-1").result == s.result
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        app.compose_double(path, commit=s.commit, producer_slot="producer-1", inputs_name="inputs-2",
                           composition_name="composition-2", ref="composed-2")
    assert_file_unchanged(path / "data.mdb", before)


def test_unretained_successful_F_selection_and_real_create_only_ref_conflict(upstream):
    path, base, q, selected = upstream
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        entries["producer-1"] = selected.dag
        unretained = tx.put_commit(tx.put_tree(entries), parents=(base,))
        tx.create_ref("already", base)
    with pytest.raises(ValueError, match="F not retained"):
        app.compose_double(path, commit=unretained, producer_slot="producer-1", inputs_name="new-inputs",
                           composition_name="new-C", ref="new")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(d.DmlError):
        app.compose_double(path, commit=selected.commit, producer_slot="producer-1", inputs_name="new-inputs",
                           composition_name="new-C", ref="already")
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("already") == base


@pytest.mark.parametrize("fault", ["response", "reservation", "submission-ref", "decision-ref", "extra-tree"])
def test_ownQ_response_actual_tree_refs_reservation_BEFORE_W(downstream, monkeypatch, fault):
    path, base, q1, s1, c2, q2, s2 = downstream
    c = app.compose_double(path, commit=s2.commit, producer_slot="producer-1", inputs_name="inputs-4",
                           composition_name="composition-4", ref="composed-4")
    original = ex.record_exchange_request
    def altered(*args, **kwargs):
        got = original(*args, **kwargs)
        if fault == "response":
            return replace(got, inputs=q1.recorded.inputs)
        with d.Repository(path) as repo, repo.write() as tx:
            if fault in ("reservation", "submission-ref", "decision-ref"):
                ref = "request-" + got.request_id if fault == "reservation" else got.ref if fault == "submission-ref" else "decision-4"
                tx.update_ref(ref, base)
            else:
                entries = app.tree(tx, got.commit)
                entries["extra"] = s1.result
                altered_commit = tx.put_commit(tx.put_tree(entries), parents=(got.base,))
                tx.update_ref(got.ref, altered_commit)
                tx.update_ref("request-" + got.request_id, altered_commit)
        return replace(got, commit=altered_commit) if fault == "extra-tree" else got
    monkeypatch.setattr(ex, "record_exchange_request", altered)
    monkeypatch.setattr(app, "_publish_reuse", lambda *a: pytest.fail("must reject BEFORE W"))
    with pytest.raises(ValueError):
        request(path, c.commit, app.DOUBLE, 4, hit=True)


@pytest.mark.parametrize("fault", ["no-C", "intent", "control", "add-C", "name", "ref", "unneeded-W", "required-miss", "existing-D", "occurrence-name"])
def test_declared_decision_request_errors_before_Q(initial, fault):
    path, base = initial
    prepared = app.prepare_add(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="input-1")
    args = dict(commit=prepared, intent=app.ADD, binding_name="add-binding", inputs_name="inputs-1",
                decision_name="decision", decision_ref="decision", submission_ref="submission")
    args.update({"intent": app.DOUBLE, "binding_name": "double-binding"} if fault == "no-C" else
                {"intent": "urn:unknown"} if fault == "intent" else {"control": "wrong"} if fault == "control" else
                {"composition_name": "C"} if fault == "add-C" else {"inputs_name": "bad/name"} if fault == "name" else
                {"submission_ref": "decision"} if fault == "ref" else {"reuse_ref": "unneeded"} if fault == "unneeded-W" else
                {"control": "require-selected"} if fault == "required-miss" else {"decision_name": "main"} if fault == "existing-D" else
                {"decision_name": "request-q-collision"})
    if fault == "existing-D":
        with d.Repository(path) as repo, repo.write() as tx:
            entries = app.tree(tx, prepared)
            entries["main"] = entries["inputs-1"]
            args["commit"] = tx.put_commit(tx.put_tree(entries), parents=(prepared,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.record_request(path, **args)
    assert_file_unchanged(path / "data.mdb", before)
