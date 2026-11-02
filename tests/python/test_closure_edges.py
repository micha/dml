"""Finite meaningful native profile/spine negatives plus explicitly substituted responses."""

from dataclasses import replace
from types import SimpleNamespace

import daggerml as d
from daggerml import builtin as b, exchange as ex
import pytest

from test_closure_calls import app, rt, funcs, create, entries, initial, successful, request, reading
from test_exchange_records import clone


def test_names_existing_publications_controls_and_refs(initial):
    path, base, made, commit = initial
    with pytest.raises(ValueError):
        app.name("bad/name")
    selected = entries(path, commit)
    args = dict(commit=commit, map_dependency=selected["map-v1"], list_dependency=selected["list-v1"], scale=selected["scale-A"],
                binding_name="binding-A", closure_name="closure-A", interpreter=made.binding, ref="new")
    with pytest.raises(ValueError, match="must be absent"):
        app.create_closure(path, **args)
    args["closure_name"] = args["binding_name"]
    with pytest.raises(ValueError, match="names must differ"):
        app.create_closure(path, **args)
    with pytest.raises(ValueError, match="must be absent"):
        app.prepare_arguments(path, commit=commit, values={"a": 1, "b": 2}, inputs_name="inputs", ref="other")
    with pytest.raises(ValueError, match="unsupported explicit"):
        request(path, commit, 1, control="automatic")
    with pytest.raises(ValueError, match="required selection"):
        request(path, commit, 1, control="require-selected")
    with pytest.raises(ValueError, match="reuse ref required"):
        request(path, commit, 1, hit=True)
    kwargs = dict(commit=commit, closure_name="closure-A", binding_name="binding-A", inputs_name="inputs", decision_name="decision",
                  decision_ref="same", submission_ref="same")
    with pytest.raises(ValueError, match="names/refs"):
        app.record_request(path, **kwargs)
    q = request(path, commit, 1)
    with pytest.raises(ValueError, match="must be absent"):
        request(path, q.recorded.commit, 1)
    with pytest.raises(ValueError, match="fresh decision cannot"):
        app.inspect_request(path, commit=q.recorded.commit, request=q.recorded.request, decision_name=q.decision.name, satisfaction_commit=q.recorded.commit)


@pytest.mark.parametrize("value", [True, 2.0, None])
def test_retained_wrong_scale_type_reject_before_creation(initial, value):
    path, base, made, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=commit) as rec:
            scale = rec.dag(rec.literal(value))
        tree = app.tree(tx, commit)
        tree["bad-scale"] = scale
        basis = tx.put_commit(tx.put_tree(tree), parents=(commit,))
    chosen = entries(path, basis)
    with pytest.raises(ValueError, match="scale requires"):
        app.create_closure(path, commit=basis, map_dependency=chosen["map-v1"], list_dependency=chosen["list-v1"], scale=scale,
            binding_name="new-B", closure_name="new-C", interpreter="/bin/python", ref="new")


def test_unretained_descriptors_and_removed_defaults(initial):
    path, base, made, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        chosen = app.tree(tx, commit)
        orphan = b.record(tx, rt.F_ROLE, values={"func": d.Datum.uri(b.MAP_GET), "extra": 1}, links={"binding": b.link(tx, tx.get_dag(chosen["map-v1"]).bindings["binding"])})
        inspector = b.Inspector(tx, commit=commit)
        with pytest.raises(ValueError, match="dependency not retained"):
            rt.inspect_dependency(tx, inspector, orphan, b.MAP_GET)
        binding = b.link(tx, tx.get_dag(chosen["map-v1"]).bindings["binding"])
        inspector.retained.remove(binding)  # HOST guard control; real reachability follows F edge.
        with pytest.raises(ValueError, match="binding not retained"):
            rt.inspect_dependency(tx, inspector, chosen["map-v1"], b.MAP_GET)
        with pytest.raises(ValueError, match="environment not retained"):
            rt.inspect_environment(tx, base, made.environment)
        with pytest.raises(ValueError, match="closure not retained"):
            app.inspect_closure(tx, base, made.dag)
        del chosen["default-map"]
        no_defaults = tx.put_commit(tx.put_tree(chosen), parents=(commit,))
    chosen = entries(path, no_defaults)
    with pytest.raises(ValueError, match="default entries"):
        app.promote_defaults(path, commit=no_defaults, map_dependency=chosen["map-v1"], scale=chosen["scale-A"], ref="new")


@pytest.mark.parametrize("field,value", [("interpreter", "relative"), ("timeout-ms", 0), ("adapter", d.Datum.uri("urn:wrong"))])
def test_local_binding_consumed_fields_exact(initial, field, value):
    path, base, made, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        binding = clone(tx, made.binding, fields={field: b.literal(tx, value)})
        closure = clone(tx, made.dag, fields={"binding": tx.put_subdag(binding)})
        chosen = app.tree(tx, commit)
        chosen.update({"closure-A": closure, "binding-A": binding})
        bad = tx.put_commit(tx.put_tree(chosen), parents=(commit,))
    with d.Repository(path) as repo, repo.read() as tx, pytest.raises(ValueError):
        app.inspect_closure(tx, bad, closure)


def test_semantic_argument_extra_and_wrong_named_B(initial):
    path, base, made, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        chosen = app.tree(tx, commit)
        with b.Recorder(tx, commit=commit) as rec:
            wrong = rec.dag(rec.arguments({"a": rec.literal(1), "b": rec.literal(2), "scale": rec.literal(3)}))
        chosen["inputs"] = wrong
        bad = tx.put_commit(tx.put_tree(chosen), parents=(commit,))
    with pytest.raises(ValueError, match="EXACT a,b"):
        request(path, bad, 1)
    with d.Repository(path) as repo, repo.write() as tx:
        chosen = app.tree(tx, commit)
        chosen["binding-A"] = made.dag
        bad = tx.put_commit(tx.put_tree(chosen), parents=(commit,))
    with pytest.raises(ValueError, match="named binding differs"):
        request(path, bad, 1)


@pytest.mark.parametrize("fault", ["two-parent", "extra-tree", "claim", "resolution"])
def test_actual_D_profile_basis_delta_claims(initial, monkeypatch, fault):
    path, base, made, commit = initial
    q = request(path, commit, 1)
    with d.Repository(path) as repo, repo.write() as tx:
        chosen = app.tree(tx, q.decision.commit)
        if fault == "extra-tree":
            chosen["extra"] = made.dag
        if fault in ("claim", "resolution"):
            chosen[q.decision.name] = clone(tx, q.decision.dag, fields={"action": b.literal(tx, "bogus")} if fault == "claim" else {"control": b.literal(tx, "try-selected"), "reason": b.literal(tx, "capture-value-mismatch")})
        bad = tx.put_commit(tx.put_tree(chosen), parents=(commit, base) if fault == "two-parent" else (commit,))
    with pytest.raises(ValueError):
        app.inspect_decision(path, commit=bad, decision_name=q.decision.name)


@pytest.mark.parametrize("fault", ["response", "reservation", "prepare", "ownQprepare", "zero-parent"])
def test_native_ownQ_vs_response_flags(initial, monkeypatch, fault):
    path, base, made, commit = initial
    original = ex.record_exchange_request
    prepare = app.prepare
    if fault in ("response", "reservation"):
        def changed(*args, **kwargs):
            got = original(*args, **kwargs)
            if fault == "response":
                return replace(got, binding=made.dag)
            with d.Repository(path) as repo, repo.write() as tx:
                tx.update_ref("request-" + got.request_id, base)
            return got
        monkeypatch.setattr(ex, "record_exchange_request", changed)
    else:
        def changed_prepare(*args, **kwargs):
            got = prepare(*args, **kwargs)
            own = len(args) > 4 and args[4] is not None
            return replace(got, binding=made.dag) if fault == "prepare" or own else got
        if fault != "zero-parent":
            monkeypatch.setattr(app, "prepare", changed_prepare)
    if fault == "zero-parent":
        with d.Repository(path) as repo, repo.write() as tx:
            zero = tx.put_commit(tx.get_commit(base).tree)
        with pytest.raises(ValueError, match="submission requires"):
            app.inspect_request(path, commit=zero, request=made.dag, decision_name="decision")
    else:
        with pytest.raises(ValueError):
            request(path, commit, 1)


@pytest.mark.parametrize("fault", ["parent", "attempt", "duplicate"])
def test_W_actual_tree_parent_and_old_T(successful, monkeypatch, fault):
    path, base, made, q1, selected = successful
    q = request(path, selected.commit, 2, control="require-selected", hit=True)
    with d.Repository(path) as repo, repo.write() as tx:
        chosen = app.tree(tx, q.reused.commit)
        key = "reuse-" + q.recorded.request_id
        if fault == "attempt":
            chosen[key] = clone(tx, q.reused.dag, fields={"attempt": tx.put_subdag(made.dag)})
        bad = tx.put_commit(tx.put_tree(chosen), parents=(selected.commit,) if fault == "parent" else (q.recorded.commit,))
    if fault == "duplicate":
        with pytest.raises(ValueError, match="already present"):
            app.publish_reuse(path, replace(q.recorded, commit=bad), selected, "other-W")
    else:
        with pytest.raises(ValueError):
            app.inspect_request(path, commit=q.recorded.commit, request=q.recorded.request, decision_name=q.decision.name, satisfaction_commit=bad)


@pytest.mark.parametrize("fault", ["depth", "intent", "decision", "return-owner", "trace-count", "trace-binding", "basis", "delta"])
def test_ORIGINAL_producer_guards_on_public_response_substitutions(successful, monkeypatch, fault):
    path, base, made, q, selected = successful
    if fault == "depth":
        with pytest.raises(ValueError, match="chain exceeds"):
            app.inspect_producer(path, commit=selected.commit, slot=app.SLOT, depth=9)
        return
    inspected = app.selection.inspect
    if fault == "intent":
        monkeypatch.setattr(app.selection, "inspect", lambda *a, **k: replace(inspected(*a, **k), intent_uri="urn:wrong"))
    elif fault == "decision":
        original = app.inspect_request
        monkeypatch.setattr(app, "inspect_request", lambda *a, **k: replace(original(*a, **k), action="reuse-selected"))
    elif fault in ("return-owner", "trace-count", "trace-binding"):
        with d.Repository(path) as repo, repo.write() as tx:
            fields = tx.get_dag(selected.result).bindings
            if fault == "return-owner":
                with b.Recorder(tx, commit=selected.commit) as rec:
                    returned = rec.dag(rec.literal(True))
                result = clone(tx, selected.result, fields={"returned": tx.put_subdag(returned), "value": tx.get_dag(returned).bindings["value"]})
            else:
                trace_id = b.link(tx, fields["trace"])
                trace = tx.get_dag(trace_id).bindings
                trace = dict(trace)
                if fault == "trace-count":
                    del trace["call-01"]
                else:
                    old = b.link(tx, trace["call-00"])
                    op = tx.get_dag(old).bindings
                    other = b.link(tx, tx.get_dag(entries_from_tx(tx, selected.commit)["map-v2"]).bindings["binding"])
                    changed = clone(tx, old, fields={"binding": tx.put_subdag(other)})
                    trace["call-00"] = tx.put_subdag(changed)
                trace_id = tx.put_dag(root=trace["role"], bindings=trace)
                result = clone(tx, selected.result, fields={"trace": tx.put_subdag(trace_id)})
            chosen = app.tree(tx, selected.commit)
            chosen["bad-return"] = result
            retained = tx.put_commit(tx.put_tree(chosen), parents=(selected.commit,))
        monkeypatch.setattr(app.selection, "inspect", lambda *a, **k: replace(selected, result=result))
        selected = replace(selected, commit=retained)
    else:
        # Public-S substituted response points to synthetic spine; no claim public S accepted it.
        with d.Repository(path) as repo, repo.write() as tx:
            chosen = app.tree(tx, q.decision.commit)
            if fault == "delta":
                chosen["extra"] = made.dag
            dc = tx.put_commit(tx.put_tree(chosen), parents=() if fault == "basis" else (commit_from_q(q),))
            cq = tx.put_commit(tx.get_commit(q.recorded.commit).tree, parents=(dc,))
            pre = tx.put_commit(tx.get_commit(selected.completion).tree, parents=(cq,))
            final = tx.put_commit(tx.get_commit(selected.completion).tree, parents=(pre,))
        monkeypatch.setattr(app.selection, "inspect", lambda *a, **k: replace(selected, completion=final))
    with pytest.raises(ValueError):
        app.inspect_producer(path, commit=selected.commit, slot=app.SLOT)


def entries_from_tx(tx, commit):
    return app.tree(tx, commit)


def commit_from_q(q):
    return q.decision.base


def test_logical_types_without_graph_authority():
    ops = SimpleNamespace(map_get=lambda arguments, key: SimpleNamespace(value=d.Datum.bool(True)))
    with pytest.raises(ValueError, match="scale must"):
        funcs.scaled_sum(SimpleNamespace(value=d.Datum.f64(2.0)), ops)
    with pytest.raises(ValueError, match="a,b must"):
        funcs.scaled_sum(SimpleNamespace(value=d.Datum.i64(2)), ops)(object())


@pytest.mark.parametrize("fault", ["pre", "cq", "dc", "delta", "control", "spec"])
def test_child_native_spines_and_coherent_control_before_write(initial, monkeypatch, fault):
    path, base, made, commit = initial
    q = request(path, commit, 1)
    with d.Repository(path) as repo, repo.write() as tx:
        dc = q.decision.commit
        if fault in ("dc", "delta", "control"):
            chosen = app.tree(tx, dc)
            if fault == "delta":
                chosen["extra"] = made.dag
            if fault == "control":
                # Allowed individual strings, forbidden control/action pairing.
                chosen[q.decision.name] = clone(tx, q.decision.dag, fields={"control": b.literal(tx, "require-selected")})
            dc = tx.put_commit(tx.put_tree(chosen), parents=() if fault == "dc" else (commit,))
        submission_tree = app.tree(tx, dc)
        submission_tree["request-" + q.recorded.request_id] = q.recorded.request
        cq = tx.put_commit(tx.put_tree(submission_tree), parents=() if fault == "cq" else (dc,))
        pre = tx.put_commit(tx.get_commit(cq).tree, parents=() if fault == "pre" else (cq,))
    context = SimpleNamespace(repository_path=path, pre_dispatch=pre, request=q.recorded.request,
                              binding=made.binding, inputs=q.recorded.inputs)
    if fault == "spec":
        original = ex.prepare_exchange
        monkeypatch.setattr(ex, "prepare_exchange", lambda *a, **k: replace(original(*a, **k), binding=made.dag))
    monkeypatch.setattr(d.Repository, "write", lambda *a: pytest.fail("child rejected BEFORE publication write"))
    with pytest.raises(ValueError):
        rt.publish(context, made.environment, *app.sources(), funcs.scaled_sum)


def test_ORIGINAL_return_guard_copied_scalar_not_success_claim(successful, monkeypatch):
    path, base, made, q, selected = successful
    original = b.Inspector.node
    def changed(self, dag):
        got = original(self, dag)
        return replace(got, value=d.Datum.bool(True)) if dag == selected.result else got
    monkeypatch.setattr(b.Inspector, "node", changed)
    with pytest.raises(ValueError, match="selected return ORIGINAL"):
        app.inspect_producer(path, commit=selected.commit, slot=app.SLOT)


def test_unretained_scale_and_FULL_argument_wrong_actual_source(initial):
    path, base, made, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        orphan = b.record(tx, b.LITERAL_ROLE, values={"value": 7}, root="value")
        with pytest.raises(ValueError, match="not retained"):
            rt.inspect_scale(tx, b.Inspector(tx, commit=commit), orphan)
        chosen = app.tree(tx, commit)
        full = tx.get_dag(chosen["inputs"]).bindings
        ledger_id = b.link(tx, full["entries"])
        ledger = tx.get_dag(ledger_id).bindings
        a_row = b.link(tx, ledger["arg-00"])
        b_row = b.link(tx, ledger["arg-01"])
        wrong_source = tx.get_dag(b_row).bindings["source"]
        altered = clone(tx, a_row, fields={"source": wrong_source})
        ledger_id = clone(tx, ledger_id, fields={"arg-00": tx.put_subdag(altered)})
        chosen["inputs"] = clone(tx, chosen["inputs"], fields={"entries": tx.put_subdag(ledger_id)})
        corrupt = tx.put_commit(tx.put_tree(chosen), parents=(commit,))
    with pytest.raises(ValueError, match="actual source"):
        request(path, corrupt, 1)
