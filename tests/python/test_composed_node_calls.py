"""NEW example contracts/associations; HOST publication seam, not installed custody."""

from dataclasses import replace
from pathlib import Path
import sys

import daggerml as d
from daggerml import builtin as b, exchange as ex, local
import pytest

from test_caller_requests import assert_file_unchanged
from test_exchange import ROOT
from test_exchange_records import clone

_saved = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    import composed_node_calls as app
    import composed_node_funcs as funcs
finally:
    sys.path[:] = _saved


def request(path, commit, intent, number, *, hit=False, control=None):
    func, _ = app.contract(intent)
    return app.record_request(path, commit=commit, intent=intent, binding_name=func + "-binding",
                              inputs_name="inputs-%d" % number, decision_name="decision-%d" % number,
                              decision_ref="decision-%d" % number, submission_ref="submission-%d" % number,
                              composition_name=None if intent == app.ADD else "composition-%d" % number,
                              control=control or ("fresh" if intent == app.ADD else "try-selected"),
                              reuse_ref="satisfaction-%d" % number if hit else None)


def host_execute(path, root, q, number, monkeypatch, *, failed=False):
    def publication(context, source, interpreter, timeout):
        with d.Repository(path) as repo, repo.read() as tx:
            entries = app.tree(tx, q.recorded.commit)
        b.publish_callable(context, funcs.add if q.decision.intent == app.ADD else funcs.double,
                           map_binding=entries["map-get-v1"], list_binding=entries["list-get-v1"])
        return local._Observation(1 if failed else 0, "child-exit" if failed else None,
                                  "test host failure" if failed else "", (b"", 0), (b"", 0))
    monkeypatch.setattr(local, "_execute", publication)
    workspace = root / ("workspace-%d" % number)
    spec = ex.prepare_exchange(path, commit=q.recorded.commit, request=q.recorded.request,
                               binding_name=q.recorded.binding_name, inputs_name=q.recorded.inputs_name,
                               intent_uri=q.recorded.intent_uri, worker_ref="work", workspace=workspace)
    run = ex.execute_exchange(workspace)
    expected = root / ("expected-%d.json" % number)
    handle = ex.ExchangeHandle(workspace, spec)
    ex.save_exchange_handle(expected, handle)
    observed = ex.observe_exchange(handle, packet=root / ("packet-%d" % number))
    received = ex.receive_observation(path, packet=observed.packet, expected=spec, ref="completion-%d" % number)
    return run, expected, observed.packet, received


def select(path, q, expected, packet, received, slot):
    return app.selection.select(path, commit=received.commit, slot=slot,
                                 binding_name=q.recorded.binding_name, inputs_name=q.recorded.inputs_name,
                                 intent_uri=q.recorded.intent_uri, packet=packet, expected_file=expected, ref=slot)


@pytest.fixture
def initial(tmp_path):
    path = tmp_path / "caller"
    return path, app.initialize(path, sys.executable)


@pytest.fixture
def upstream(initial, tmp_path, monkeypatch):
    path, base = initial
    prepared = app.prepare_add(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs-1", ref="input-1")
    q = request(path, prepared, app.ADD, 1)
    run, expected, packet, received = host_execute(path, tmp_path, q, 1, monkeypatch)
    s = select(path, q, expected, packet, received, "producer-1")
    return path, base, q, s


@pytest.fixture
def downstream(upstream, tmp_path, monkeypatch):
    path, base, q1, s1 = upstream
    c = app.compose_double(path, commit=s1.commit, producer_slot="producer-1", inputs_name="inputs-2",
                           composition_name="composition-2", ref="composed-2")
    q2 = request(path, c.commit, app.DOUBLE, 2)
    run, expected, packet, received = host_execute(path, tmp_path, q2, 2, monkeypatch)
    s2 = select(path, q2, expected, packet, received, app.SLOT)
    return path, base, q1, s1, c, q2, s2


def compose_next(state, tmp_path, monkeypatch, *, values=None):
    path, base, q1, s1, c2, q2, s2 = state
    prepared = app.prepare_add(path, commit=s2.commit, values=values or {"a": 13, "b": 29},
                               inputs_name="inputs-3", ref="prepared-3")
    q3 = request(path, prepared, app.ADD, 3)
    run, expected, packet, received = host_execute(path, tmp_path, q3, 3, monkeypatch)
    s3 = select(path, q3, expected, packet, received, "producer-3")
    c4 = app.compose_double(path, commit=s3.commit, producer_slot="producer-3", inputs_name="inputs-4",
                            composition_name="composition-4", ref="composed-4")
    return q3, s3, c4


def reading(path, got):
    return app.inspect_request(path, commit=got.recorded.commit, request=got.recorded.request,
                               decision_name=got.decision.name,
                               satisfaction_commit=None if got.reused is None else got.reused.commit)


def test_node_loading_preserves_OUTER_result_AND_exact_selected_attempt(upstream):
    path, base, q1, s1 = upstream
    c = app.compose_double(path, commit=s1.commit, producer_slot="producer-1", inputs_name="inputs-2",
                           composition_name="composition-2", ref="composed-2")
    got = app.inspect_composition(path, commit=c.commit, inputs_name="inputs-2", composition_name="composition-2")
    assert got == c
    assert got.producer.selected.attempt == s1.attempt
    with d.Repository(path) as repo, repo.read() as tx:
        full, sources = app.inspect_arguments(tx, c.commit, c.inputs.dag, app.DOUBLE)
        assert sources["x"].dag == s1.result and sources["x"].value == d.Datum.i64(42)
        assert set(tx.get_dag(c.inputs.dag).bindings) == {"role", "value", "entries"}
        # The MAP contains DATUM IDs; selected attempt authority is NOT in the value.
        assert list(dict(full.value.value).values()) == [got.producer.returned.datum]
        assert tx.get_datum(got.producer.returned.datum) == d.Datum.i64(42)
        assert set(tx.get_dag(c.dag).bindings) == {"role", "arguments", "key", "selection-slot", "selection", "result"}
        assert tx.get_commit(c.commit).parents == (s1.commit,)
        before = app.tree(tx, s1.commit)
        after = app.tree(tx, c.commit)
        assert {n: v for n, v in after.items() if n not in ("inputs-2", "composition-2")} == before
        assert b.link(tx, tx.get_dag(c.dag).bindings["selection"]) == s1.dag


@pytest.mark.parametrize("values", [{"a": 13, "b": 29}, {"a": 29, "b": 13}])
def test_full_MAP_value_hit_NEW_requested_chain_OLD_executed_chain_no_job(downstream, tmp_path, monkeypatch, values):
    path, base, q1, s1, c2, q2, s2 = downstream
    q3, s3, c4 = compose_next(downstream, tmp_path, monkeypatch, values=values)
    monkeypatch.setattr(local, "_execute", lambda *a: pytest.fail("metadata/reuse cannot dispatch"))
    q4 = request(path, c4.commit, app.DOUBLE, 4, hit=True)
    decision = reading(path, q4)
    assert q3.recorded.request != q1.recorded.request and s3.attempt_id != s1.attempt_id
    assert decision.inputs.datum == decision.selected.inputs.datum
    assert decision.inputs.dag != decision.selected.inputs.dag
    assert decision.composition.producer.selected == c4.producer.selected
    assert decision.composition.producer.selected.attempt == s3.attempt
    assert decision.selected.decision.composition.producer.selected.attempt == s1.attempt
    assert q4.reused.attempt == s2.attempt and q4.reused.result == s2.result
    assert decision.selected.returned.value == d.Datum.i64(84)
    assert q4.recorded.request != q2.recorded.request
    assert (q3.decision.inputs.datum == q1.decision.inputs.datum) == (values == {"a": 13, "b": 29})
    with d.Repository(path) as repo, repo.read() as tx:
        assert app.tree(tx, q4.reused.commit)[app.SLOT] == s2.dag
        fields = tx.get_dag(s2.result).bindings
        assert b.link(tx, fields["request"]) == q2.recorded.request
        assert len(b.Inspector(tx, commit=q4.reused.commit).trace(
            b.link(tx, fields["trace"]), request=q2.recorded.request, inputs=q2.recorded.inputs)) == 1
        entries = app.tree(tx, q4.recorded.commit)
        assert not any(n.startswith("attempt-") and n not in app.tree(tx, c4.commit) for n in entries)


def test_value_miss_pending_own_Q_and_no_auto_adoption(downstream, tmp_path, monkeypatch):
    path = downstream[0]
    q3, s3, c4 = compose_next(downstream, tmp_path, monkeypatch, values={"a": 13, "b": 30})
    q4 = request(path, c4.commit, app.DOUBLE, 4)
    got = reading(path, q4)
    assert got.reason == "value-mismatch" and q4.reused is None
    assert got.inputs.datum != got.selected.inputs.datum
    assert got.selected.returned.value == d.Datum.i64(84)
    run, expected, packet, received = host_execute(path, tmp_path, q4, 4, monkeypatch)
    fresh = select(path, q4, expected, packet, received, "fresh-double")
    assert app.inspect_producer(path, commit=fresh.commit, slot="fresh-double", intent=app.DOUBLE).returned.value == d.Datum.i64(86)
    assert app.selection.inspect(path, commit=fresh.commit, slot=app.SLOT).dag == downstream[-1].dag


def test_map_insertion_order_equal_values_swapped_values_differ(initial):
    path, base = initial
    ids = []
    for number, items in enumerate(([('a', 13), ('b', 29)], [('b', 29), ('a', 13)], [('a', 29), ('b', 13)])):
        commit = app.prepare_add(path, commit=base, values=items, inputs_name="input", ref="prepared-%d" % number)
        with d.Repository(path) as repo, repo.read() as tx:
            full, _ = app.inspect_arguments(tx, commit, app.tree(tx, commit)["input"], app.ADD)
            ids.append((full.dag, full.datum))
    assert ids[0] == ids[1] and ids[0][1] != ids[2][1]


@pytest.mark.parametrize("values", [{"a": True, "b": 29}, {"a": 13.0, "b": 29}, {"a": 13},
                                     {"a": 13, "b": 29, "z": 0}, [("a", 13), ("a", 29)],
                                     {"a": 2**63, "b": 29}])
def test_prepare_exact_names_types_before_write(initial, values):
    path, base = initial
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((TypeError, ValueError, OverflowError)):
        app.prepare_add(path, commit=base, values=values, inputs_name="inputs", ref="inputs")
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["slot", "S", "R", "key", "arguments", "extra-field", "root", "inner-literal", "extra-tree", "old-name", "two-parent"])
def test_composition_actual_parent_slot_S_outerR_same_value_wrong_source_reject(downstream, tmp_path, monkeypatch, fault):
    path, base, q1, s1, c2, q2, s2 = downstream
    q3, s3, c4 = compose_next(downstream, tmp_path, monkeypatch)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, c4.commit)
        changes = {}
        if fault == "slot":
            changes["selection-slot"] = b.literal(tx, "producer-1")
        elif fault == "S":
            changes["selection"] = tx.put_subdag(s1.dag)
        elif fault == "R":
            changes["result"] = tx.put_subdag(s1.result)
        elif fault == "key":
            changes["key"] = b.literal(tx, "y")
        elif fault == "arguments":
            changes["arguments"] = tx.put_subdag(c2.inputs.dag)
        elif fault == "extra-field":
            changes["unexpected"] = b.literal(tx, 1)
        elif fault == "inner-literal":
            outer = tx.get_dag(s3.result).bindings
            inner = b.link(tx, outer["returned"])
            with b.Recorder(tx, commit=c4.base) as rec:
                inputs = rec.arguments({"x": rec.load(inner)})
                entries["inputs-4"] = rec.dag(inputs)
            changes.update(arguments=tx.put_subdag(entries["inputs-4"]), result=tx.put_subdag(inner))
        if changes or fault == "root":
            entries["composition-4"] = clone(tx, c4.dag, fields=changes,
                                               root=tx.get_dag(c4.dag).bindings["result"] if fault == "root" else None)
        if fault == "extra-tree":
            entries["extra"] = s1.result
        parents = (c4.base, base) if fault == "two-parent" else (c4.commit,) if fault == "old-name" else (c4.base,)
        corrupt = tx.put_commit(tx.put_tree(entries), parents=parents)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        request(path, corrupt, app.DOUBLE, 4, hit=True)
    assert_file_unchanged(path / "data.mdb", before)


def test_coherent_equal_value_alternate_C_parent_S_not_actual_selected_R(downstream, tmp_path, monkeypatch):
    path, base, q1, s1, c2, q2, s2 = downstream
    q3, s3, c4 = compose_next(downstream, tmp_path, monkeypatch)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, c4.commit)
        # Completely coherent old R/old I, but claiming THIS new producer S3.
        entries["inputs-4"] = c2.inputs.dag
        entries["composition-4"] = clone(tx, c4.dag, fields={"arguments": tx.put_subdag(c2.inputs.dag),
                                                            "result": tx.put_subdag(s1.result)})
        corrupt = tx.put_commit(tx.put_tree(entries), parents=(c4.base,))
    with pytest.raises(ValueError, match="selected S/outerR"):
        request(path, corrupt, app.DOUBLE, 4, hit=True)


def test_actual_SAME_name_alternate_decision_parent_response_reject_BEFORE_W(downstream, monkeypatch):
    path, base, q1, s1, c2, q2, s2 = downstream
    # New composition from same upstream at a later basis, then coherent alternate fresh Q.
    c = app.compose_double(path, commit=s2.commit, producer_slot="producer-1", inputs_name="inputs-4",
                           composition_name="composition-4", ref="composed-4")
    alternate = app.record_request(path, commit=c.commit, intent=app.DOUBLE, binding_name="double-binding",
                                   inputs_name="inputs-4", composition_name="composition-4", decision_name="decision-4",
                                   control="fresh", decision_ref="alternate-d", submission_ref="alternate-q")
    original = ex.record_exchange_request
    def replace_response(*args, **kwargs):
        actual = original(*args, **kwargs)
        with d.Repository(path) as repo, repo.write() as tx:
            tx.update_ref(actual.ref, alternate.recorded.commit)
        return replace(alternate.recorded, base=actual.base, ref=actual.ref)
    monkeypatch.setattr(ex, "record_exchange_request", replace_response)
    monkeypatch.setattr(app, "_publish_reuse", lambda *a: pytest.fail("wrong actual parent must reject BEFORE W"))
    with pytest.raises(ValueError, match="actual submission parent"):
        request(path, c.commit, app.DOUBLE, 4, hit=True)
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("satisfaction-4")


@pytest.mark.parametrize("field", ["intent", "result", "inputs", "completion"])
def test_poisoned_selected_even_mismatch_error_not_miss(downstream, tmp_path, monkeypatch, field):
    path = downstream[0]
    q3, s3, c4 = compose_next(downstream, tmp_path, monkeypatch, values={"a": 13, "b": 30})
    selected = downstream[-1]
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, c4.base)
        changed = tx.put_subdag(s3.result) if field in ("result", "inputs") else b.literal(
            tx, d.Datum.uri(app.ADD) if field == "intent" else b"bad")
        entries[app.SLOT] = clone(tx, selected.dag, fields={field: changed}, root=changed if field == "result" else None)
        basis = tx.put_commit(tx.put_tree(entries), parents=(c4.base,))
    composed = app.compose_double(path, commit=basis, producer_slot="producer-3", inputs_name="other-inputs",
                                  composition_name="other-C", ref="other-C")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.record_request(path, commit=composed.commit, intent=app.DOUBLE, binding_name="double-binding",
                           inputs_name="other-inputs", composition_name="other-C", decision_name="miss",
                           decision_ref="miss-d", submission_ref="miss-q", control="try-selected")
    assert_file_unchanged(path / "data.mdb", before)


def test_two_attempts_ONE_Q_equal_outerR_still_capture_THIS_selected_T(upstream, tmp_path, monkeypatch):
    path, base, q1, first = upstream
    # HOST publication only: explicitly imported same Q, another B registration/attempt.
    run, expected, packet, received = host_execute(path, tmp_path, q1, 9, monkeypatch)
    with d.Repository(path) as repo, repo.write() as tx:
        joined = tx.put_commit(tx.get_commit(first.commit).tree, parents=(first.commit, received.commit))
    second = app.selection.select(path, commit=joined, slot="producer-second", binding_name="add-binding",
                                 inputs_name="inputs-1", intent_uri=app.ADD, packet=packet, expected_file=expected, ref="producer-second")
    assert first.request == second.request and first.result == second.result
    assert first.attempt != second.attempt and first.attempt_id != second.attempt_id
    c = app.compose_double(path, commit=second.commit, producer_slot="producer-second", inputs_name="input-second",
                           composition_name="C-second", ref="C-second")
    actual = app.inspect_composition(path, commit=c.commit, inputs_name="input-second", composition_name="C-second")
    assert actual.producer.selected.attempt == second.attempt
    assert actual.producer.selected.result == first.result
    with d.Repository(path) as repo, repo.read() as tx:
        assert b.link(tx, tx.get_dag(actual.dag).bindings["selection"]) == second.dag
