"""Fixed capture/key/own-Q tests. HOST publication is NOT actual installed custody."""

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
    import closure_calls as app
    import closure_funcs as funcs
    import closure_runtime as rt
finally:
    sys.path[:] = _saved


def entries(path, commit):
    with d.Repository(path) as repo, repo.read() as tx:
        return app.tree(tx, commit)


def create(path, base, label="A", version="v1", scale="A", **kwargs):
    selected = entries(path, base)
    return app.create_closure(path, commit=base, map_dependency=selected["map-" + version],
        list_dependency=selected["list-v1"], scale=selected["scale-" + scale],
        binding_name="binding-" + label, closure_name="closure-" + label,
        interpreter=sys.executable, ref="created-" + label, **kwargs)


def request(path, commit, number, label="A", control="fresh", hit=False):
    return app.record_request(path, commit=commit, closure_name="closure-" + label,
        binding_name="binding-" + label, inputs_name="inputs", decision_name="decision-%d" % number,
        decision_ref="decision-%d" % number, submission_ref="submission-%d" % number,
        control=control, reuse_ref="reuse-%d" % number if hit else None)


def reading(path, q):
    return app.inspect_request(path, commit=q.recorded.commit, request=q.recorded.request,
        decision_name=q.decision.name, satisfaction_commit=None if q.reused is None else q.reused.commit)


@pytest.fixture
def initial(tmp_path):
    path = tmp_path / "caller"
    base = app.initialize(path)
    made = create(path, base)
    commit = app.prepare_arguments(path, commit=made.commit, values={"a": 13, "b": 29}, inputs_name="inputs", ref="prepared")
    return path, base, made, commit


def host_execute(path, root, q, number, monkeypatch):
    def publication(context, source, interpreter, timeout):
        rt.publish(context, q.decision.closure.environment.dag, *app.sources(), funcs.scaled_sum)
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    monkeypatch.setattr(local, "_execute", publication)
    workspace = root / ("workspace-%d" % number)
    spec = ex.prepare_exchange(path, commit=q.recorded.commit, request=q.recorded.request,
        binding_name=q.recorded.binding_name, inputs_name=q.recorded.inputs_name,
        intent_uri=app.INTENT, worker_ref="work", workspace=workspace)
    run = ex.execute_exchange(workspace)
    expected = root / ("expected-%d.json" % number)
    handle = ex.ExchangeHandle(workspace, spec)
    ex.save_exchange_handle(expected, handle)
    observed = ex.observe_exchange(handle, packet=root / ("packet-%d" % number))
    received = ex.receive_observation(path, packet=observed.packet, expected=spec, ref="completion-%d" % number)
    selected = app.selection.select(path, commit=received.commit, slot=app.SLOT if number == 1 else "witness-%d" % number,
        binding_name=q.recorded.binding_name, inputs_name=q.recorded.inputs_name, intent_uri=app.INTENT,
        packet=observed.packet, expected_file=expected, ref="selected-%d" % number)
    assert run.outcome == "success"
    return selected


@pytest.fixture
def successful(initial, tmp_path, monkeypatch):
    path, base, made, commit = initial
    q = request(path, commit, 1)
    selected = host_execute(path, tmp_path, q, 1, monkeypatch)
    return path, base, made, q, selected


def test_graph_retention_source_exact_K_equivalence_and_default_pin(initial):
    path, base, first, commit = initial
    selected = entries(path, commit)
    moved = app.promote_defaults(path, commit=commit, map_dependency=selected["map-v2"], scale=selected["scale-C"], ref="defaults")
    second = create(path, moved, "B", "v2", "B")
    third = create(path, second.commit, "C", "v2", "C")
    with d.Repository(path) as repo, repo.read() as tx:
        ca = app.inspect_closure(tx, third.commit, first.dag)
        cb = app.inspect_closure(tx, third.commit, second.dag)
        cc = app.inspect_closure(tx, third.commit, third.dag)
        assert ca.key == cb.key != cc.key
        assert ca.environment.scale.value == cb.environment.scale.value == d.Datum.i64(2)
        assert ca.environment.scale.dag != cb.environment.scale.dag
        assert ca.environment.map_binding != cb.environment.map_binding
        assert len({ca.dag, cb.dag, cc.dag}) == 3
        assert tx.get_commit(first.commit).parents == (base,)
        assert {n: v for n, v in app.tree(tx, first.commit).items() if n not in ("binding-A", "closure-A")} == app.tree(tx, base)
        raw = tx.get_record("dag", first.dag)
        assert raw == tx.get_record("dag", ca.dag)
        assert b.scalar(tx, tx.get_dag(ca.binding).bindings["source"], "bytes") == rt.capture(ca.environment.dag, *app.sources())
        assert app.tree(tx, moved)["default-scale"] == selected["scale-C"]
        assert ca.environment.scale.dag == selected["scale-A"]


def test_own_Q_reuse_new_capture_OLD_execution_and_fresh_control(successful, tmp_path, monkeypatch):
    path, base, first, q1, s1 = successful
    selected = entries(path, s1.commit)
    moved = app.promote_defaults(path, commit=s1.commit, map_dependency=selected["map-v2"], scale=selected["scale-C"], ref="defaults")
    q2 = request(path, moved, 2, control="require-selected", hit=True)
    assert reading(path, q2).closure.dag == first.dag
    second = create(path, q2.reused.commit, "B", "v2", "B")
    monkeypatch.setattr(local, "_execute", lambda *a: pytest.fail("reuse cannot dispatch"))
    q4 = request(path, second.commit, 4, "B", "require-selected", True)
    got = reading(path, q4)
    assert got.closure.dag == second.dag and got.selected.closure.dag == first.dag
    assert got.closure.environment.map_binding != got.selected.closure.environment.map_binding
    assert got.closure.environment.scale.dag != got.selected.closure.environment.scale.dag
    assert got.closure.key == got.selected.closure.key
    assert q4.reused.attempt == s1.attempt and q4.reused.result == s1.result
    assert len({q1.recorded.request, q2.recorded.request, q4.recorded.request}) == 3
    q5 = request(path, q4.reused.commit, 5, "B")
    fresh = host_execute(path, tmp_path, q5, 5, monkeypatch)
    producer = app.inspect_producer(path, commit=fresh.commit, slot="witness-5")
    assert producer.returned.value == d.Datum.i64(84)
    assert producer.closure.dag == second.dag and producer.selected.attempt != s1.attempt
    assert app.selection.inspect(path, commit=fresh.commit, slot=app.SLOT).dag == s1.dag


def test_changed_scale_miss_full_MAP_same_poison_not_fallback(successful, tmp_path, monkeypatch):
    path, base, first, q1, s1 = successful
    changed = create(path, s1.commit, "C", "v2", "C")
    q6 = request(path, changed.commit, 6, "C", "try-selected")
    got = reading(path, q6)
    assert got.inputs.datum == q1.decision.inputs.datum
    assert got.closure.key != got.selected.closure.key
    assert got.reason == "capture-value-mismatch" and q6.reused is None
    fresh = host_execute(path, tmp_path, q6, 6, monkeypatch)
    assert app.inspect_producer(path, commit=fresh.commit, slot="witness-6").returned.value == d.Datum.i64(126)
    assert app.selection.inspect(path, commit=fresh.commit, slot=app.SLOT).dag == s1.dag


@pytest.mark.parametrize("values", [{"a": 13}, {"a": 13, "b": 29, "scale": 3}, {"a": True, "b": 29}, {"a": 13.0, "b": 29}, [("a", 13), ("a", 29)], {"a": 2**63, "b": 29}])
def test_argument_contract_before_write(initial, values):
    path, base, made, commit = initial
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, TypeError, OverflowError)):
        app.prepare_arguments(path, commit=commit, values=values, inputs_name="other", ref="other")
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["key-scale", "key-func", "key-root", "key-extra", "closure-role", "closure-intent", "closure-root", "closure-extra", "environment-extra", "environment-root", "dependency-func", "dependency-version", "source-bytes", "same-value-E"])
def test_strict_profile_and_exact_same_value_E_source_association(initial, fault):
    path, base, first, commit = initial
    second = create(path, commit, "B", "v1", "B")
    with d.Repository(path) as repo, repo.write() as tx:
        original = app.inspect_closure(tx, second.commit, first.dag)
        fields = tx.get_dag(first.dag).bindings
        changes, root = {}, None
        if fault.startswith("key-"):
            key_changes = {"scale": b.literal(tx, 3)} if fault == "key-scale" else {"map-get": b.literal(tx, d.Datum.uri(b.LIST_GET))} if fault == "key-func" else {"extra": b.literal(tx, 1)} if fault == "key-extra" else {}
            key = clone(tx, first.key, fields=key_changes, root=tx.get_dag(first.key).bindings["scale"] if fault == "key-root" else None)
            changes["capture-key"] = tx.put_subdag(key)
        elif fault.startswith("closure-"):
            changes = {"role": b.literal(tx, "unsupported")} if fault == "closure-role" else {"intent": b.literal(tx, d.Datum.uri("urn:example:other"))} if fault == "closure-intent" else {"extra": b.literal(tx, 1)} if fault == "closure-extra" else {}
            root = fields["binding"] if fault == "closure-root" else None
        elif fault.startswith("environment-"):
            env = clone(tx, first.environment, fields={"extra": b.literal(tx, 1)} if fault == "environment-extra" else {}, root=tx.get_dag(first.environment).bindings["scale"] if fault == "environment-root" else None)
            changes["environment"] = tx.put_subdag(env)
        elif fault.startswith("dependency-"):
            dep = original.environment.map_dependency
            dep_changes = {"func": b.literal(tx, d.Datum.uri(b.LIST_GET))} if fault == "dependency-func" else {"binding": tx.put_subdag(b.put_binding(tx, source_uri="dml://source/builtin/map/get/v999"))}
            dep = clone(tx, dep, fields=dep_changes)
            env = clone(tx, first.environment, fields={"map-get": tx.put_subdag(dep)})
            changes["environment"] = tx.put_subdag(env)
        elif fault == "source-bytes":
            normal = clone(tx, first.binding, fields={"source": b.literal(tx, b"wrong")})
            changes["binding"] = tx.put_subdag(normal)
        else:
            # Coherent equal K/source value, but B embeds E-A while C links E-B.
            changes["environment"] = tx.put_subdag(second.environment)
        bad = clone(tx, first.dag, fields=changes, root=root)
        entries = app.tree(tx, second.commit)
        entries["closure-A"] = bad
        corrupt = tx.put_commit(tx.put_tree(entries), parents=(second.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        request(path, corrupt, 2)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("field", ["intent", "result", "inputs", "completion"])
def test_poisoned_S_errors_even_scale_mismatch(successful, field):
    path, base, first, q, selected = successful
    changed = create(path, selected.commit, "C", "v2", "C")
    with d.Repository(path) as repo, repo.write() as tx:
        fields = {field: b.literal(tx, b"wrong") if field == "completion" else b.literal(tx, d.Datum.uri("urn:wrong")) if field == "intent" else tx.put_subdag(first.dag)}
        entries = app.tree(tx, changed.commit)
        entries[app.SLOT] = clone(tx, selected.dag, fields=fields, root=fields[field] if field == "result" else None)
        bad = tx.put_commit(tx.put_tree(entries), parents=(changed.commit,))
    with pytest.raises(ValueError):
        request(path, bad, 6, "C", "try-selected")


def test_actual_coherent_SAME_name_alternate_native_parent_reject_before_W(successful, monkeypatch):
    path, base, first, q, selected = successful
    alternate = app.record_request(path, commit=selected.commit, closure_name="closure-A", binding_name="binding-A", inputs_name="inputs",
        decision_name="decision-2", decision_ref="alt-d", submission_ref="alt-q", control="fresh")
    original = ex.record_exchange_request
    def swap(*args, **kwargs):
        actual = original(*args, **kwargs)
        with d.Repository(path) as repo, repo.write() as tx:
            tx.update_ref(actual.ref, alternate.recorded.commit)
        return replace(alternate.recorded, base=actual.base, ref=actual.ref)
    monkeypatch.setattr(ex, "record_exchange_request", swap)
    monkeypatch.setattr(app, "publish_reuse", lambda *a: pytest.fail("wrong native parent BEFORE W"))
    with pytest.raises(ValueError, match="actual submission parent"):
        request(path, selected.commit, 2, control="require-selected", hit=True)


@pytest.mark.parametrize("a,bvalue,scale", [(2**63-1, 1, 0), (2**62, 0, 3), (-2**63, -1, 1)])
def test_intermediate_AND_final_I64_overflow(a, bvalue, scale, initial):
    path, base, made, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        with pytest.raises(OverflowError), b.Recorder(tx, commit=commit) as rec:
            c = app.inspect_closure(tx, commit, made.dag)
            ops = rec.operations(map_binding=c.environment.map_binding, list_binding=c.environment.list_binding)
            arguments = rec.arguments({"a": rec.literal(d.Datum.i64(a)), "b": rec.literal(d.Datum.i64(bvalue))})
            funcs.scaled_sum(rec.literal(d.Datum.i64(scale)), ops)(arguments)


def test_child_wrong_expected_environment_reject_BEFORE_any_write(initial, tmp_path, monkeypatch):
    path, base, first, commit = initial
    q = request(path, commit, 1)
    def publication(context, source, interpreter, timeout):
        original = d.Repository.write
        monkeypatch.setattr(d.Repository, "write", lambda *a: pytest.fail("invalid child cannot open write"))
        try:
            with pytest.raises(ValueError, match="child exact"):
                rt.publish(context, first.key, *app.sources(), funcs.scaled_sum)
        finally:
            monkeypatch.setattr(d.Repository, "write", original)
        raise RuntimeError("expected child refusal")
    monkeypatch.setattr(local, "_execute", publication)
    workspace = tmp_path / "wrong-child"
    ex.prepare_exchange(path, commit=q.recorded.commit, request=q.recorded.request,
        binding_name="binding-A", inputs_name="inputs", intent_uri=app.INTENT, worker_ref="work", workspace=workspace)
    with pytest.raises(local.LocalExecutionError):
        ex.execute_exchange(workspace)


@pytest.mark.parametrize("fault", ["capture", "trace"])
def test_public_success_WITH_poisoned_ORIGINAL_capture_or_trace_even_on_mismatch(initial, tmp_path, monkeypatch, fault):
    """Genuine public S accepts success/history; new capture contract independently rejects.

    HOST writer deliberately bypasses trusted wrapper to simulate poisoned producer records.
    No real process or claim that runtime produced this malformed history.
    """
    path, base, first, commit = initial
    second = create(path, commit, "B", "v2", "B")
    q = request(path, second.commit, 1)
    if fault == "capture":
        with d.Repository(path) as repo, repo.write() as tx:
            chosen = app.tree(tx, q.decision.commit)
            chosen[q.decision.name] = clone(tx, q.decision.dag, fields={"closure": tx.put_subdag(second.dag)})
            poisoned = tx.put_commit(tx.put_tree(chosen), parents=(second.commit,))
        recorded = ex.record_exchange_request(path, commit=poisoned, binding_name="binding-A", inputs_name="inputs", intent_uri=app.INTENT, ref="poisoned-Q")
        q = replace(q, recorded=recorded)
    def publication(context, source, interpreter, timeout):
        with d.Repository(context.repository_path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=context.pre_dispatch) as rec:
                scale = rec.load(q.decision.closure.environment.scale.dag)
                args = rec.load(context.inputs)
                chosen = app.tree(tx, context.pre_dispatch)
                captured = q.decision.closure.environment.map_binding
                wrong = b.link(tx, tx.get_dag(chosen["map-v2"]).bindings["binding"])
                ops = rec.operations(map_binding=wrong if fault == "trace" else captured,
                                     list_binding=q.decision.closure.environment.list_binding)
                result = funcs.scaled_sum(scale, ops)(args)
                returned = rec.returned(result, request=context.request, inputs=context.inputs)
                local.publish_result(tx, context, rec.dag(returned))
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    monkeypatch.setattr(local, "_execute", publication)
    workspace = tmp_path / "poisoned-original"
    spec = ex.prepare_exchange(path, commit=q.recorded.commit, request=q.recorded.request,
        binding_name="binding-A", inputs_name="inputs", intent_uri=app.INTENT, worker_ref="work", workspace=workspace)
    run = ex.execute_exchange(workspace)
    assert run.outcome == "success"
    handle = ex.ExchangeHandle(workspace, spec)
    expected = tmp_path / "poisoned-expected.json"
    ex.save_exchange_handle(expected, handle)
    observed = ex.observe_exchange(handle, packet=tmp_path / "poisoned-packet")
    received = ex.receive_observation(path, packet=observed.packet, expected=spec, ref="poisoned-completion")
    selected = app.selection.select(path, commit=received.commit, slot=app.SLOT,
        binding_name="binding-A", inputs_name="inputs", intent_uri=app.INTENT,
        packet=observed.packet, expected_file=expected, ref="poisoned-selected")
    assert app.selection.inspect(path, commit=selected.commit, slot=app.SLOT).result == run.result
    changed = create(path, selected.commit, "C", "v2", "C")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="decision actual basis|ORIGINAL getter"):
        request(path, changed.commit, 6, "C", "try-selected")
    assert_file_unchanged(path / "data.mdb", before)
