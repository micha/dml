"""NEW datum matching, ALL-row/public S/full-Q authority, separate W provenance."""

from dataclasses import replace
import subprocess

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

from test_recorded_maps import state, success, app as maps, binding, funcs, reuse, story, changed
from test_exchange import exchange_runtime, typed_oracle
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged

pytest_plugins = ("reuse_test_cleanup",)


def request(success, **changes):
    path, q, selected, table, child = success
    args = dict(commit=table.commit, intent_uri=story.DOUBLE, binding_name="double-binding", inputs_name=q.recorded.inputs_name, table_name="double-table", decision_name="new", decision_ref="new-decision", submission_ref="new-q", reuse_ref="new-w")
    args.update(changes)
    return reuse.record_request(path, **args)


def inspect(path, got, **changes):
    args = dict(commit=got.recorded.commit, request=got.recorded.request, decision_name=got.decision.name, satisfaction_commit=None if got.reused is None else got.reused.commit)
    args.update(changes)
    return reuse.inspect_request(path, **args)


def test_success_PUBLIC_return_actual_child_getters_and_new_ownQ_oldT_W_no_job(success, monkeypatch):
    path, q, selected, table, child = success
    output = maps.inspect_returned(path, commit=table.commit, slot=selected.slot)
    assert output.value == d.Datum.i64(84) and len(output.accesses) == 1
    assert output.request == q.recorded.request and child["exit"] == 0 and child["reaped"]
    before = typed_oracle(path, (table.commit,))
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("reuse/read never executes"))
        got = request(success)
        reading = inspect(path, got)
    assert reading.request == got.recorded.request != selected.request
    assert reading.returned == output and reading.executed == q.decision.inputs
    assert got.reused.attempt == selected.attempt and got.reused.result == selected.result
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_commit(got.decision.commit).parents == (table.commit,)
        assert tx.get_commit(got.recorded.commit).parents == (got.decision.commit,)
        assert tx.get_commit(got.reused.commit).parents == (got.recorded.commit,)
        assert all(tx.get_record(*key) == raw for key, raw in before.items())
    assert reuse.inspect_table(path, commit=table.commit, table_name="double-table") == table
    assert request(success, control="require-selected", decision_name="required", decision_ref="required-d", submission_ref="required-q", reuse_ref="required-w").decision.action == "reuse-selected"


def test_explicit_returned_source_native_equal_value_different_construction_real_datum_hit(success, state):
    path, q, selected, table, child = success
    output = maps.returned_source(path, commit=table.commit, slot=selected.slot, output_name="returned84", ref="returned84")
    # Fixture double returns84, so build literal84 explicitly for SAME-value control.
    with d.Repository(path) as repo, repo.write() as tx:
        node = maps.literal(tx, 84)
        dag = tx.put_dag(root=node, bindings={"v": node})
        entries = maps.tree(tx, output.commit)
        entries["literal84"] = dag
        basis = tx.put_commit(tx.put_tree(entries), parents=(output.commit,))
    literal = maps.literal_source(path, commit=basis, source_dag=dag, source_name="v", output_name="literal84-source", ref="literal84-source")
    a = story.construct(path, literal.commit, prefix="literal84-map", pairs=((state[3]["x"], literal.dag),))
    b = story.construct(path, a.commit, prefix="computed84-map", pairs=((state[3]["x"], output.dag),))
    ia, ib = (maps.inspect_input(path, commit=b.commit, dag=v.dag) for v in (a, b))
    assert ia.datum == ib.datum and ia.construction != ib.construction and ia.dag != ib.dag
    # Table is x42; correctly NOT a hit just because some source or R roots match84.
    got = request(success, commit=b.commit, inputs_name=b.name, reuse_ref=None)
    assert got.decision.reason == "no-entry" and inspect(path, got).executed is None
    assert maps.inspect_source(path, commit=b.commit, dag=output.dag).value == d.Datum.i64(84)


@pytest.mark.parametrize("control,table,reason", [("try-selected", False, "no-table"), ("try-selected", True, "no-entry"), ("fresh", True, "explicit-fresh")])
def test_empty_miss_and_fresh_no_T_public_shape_exact_basis(state, control, table, reason):
    path, _, _, _, inputs = state
    basis = inputs.commit
    if table:
        basis = reuse.define_table(path, commit=basis, table_name="table", intent_uri=story.DOUBLE, ref="table").commit
    got = reuse.record_request(path, commit=basis, intent_uri=story.DOUBLE, binding_name="double-binding", inputs_name=inputs.name, table_name="table", decision_name="decision", decision_ref="decision", submission_ref="submission", control=control)
    assert got.decision.reason == reason and got.reused is None
    assert inspect(path, got).requested == got.decision.inputs
    assert got.decision.table is not None if table and control != "fresh" else got.decision.table is None
    for wrong in (None, inputs.dag):
        with pytest.raises((TypeError, ValueError, KeyError)):
            inspect(path, got, request=wrong)
    with pytest.raises(ValueError, match="fresh"):
        inspect(path, got, satisfaction_commit=got.recorded.commit)


@pytest.mark.parametrize("fault", ["slot", "key", "arguments", "inputs", "selection", "role", "root", "extra", "cap", "duplicate-slot", "profile", "uri"])
def test_poisoned_NONmatching_row_rejected_no_fallback_or_target_publication(success, state, fault):
    path, q, selected, table, child = success
    with d.Repository(path) as repo, repo.write() as tx:
        row = table.entries[0]
        changes = {}
        if fault == "slot":
            changes["slot"] = maps.literal(tx, "absent")
        elif fault == "arguments":
            changes["arguments"] = maps.literal(tx, d.Datum.map(()))
        elif fault in ("inputs", "selection"):
            changes[fault] = tx.put_subdag(table.dag)
        elif fault == "role":
            changes["role"] = maps.literal(tx, "old-Mi")
        elif fault == "extra":
            changes["extra"] = maps.literal(tx, "extra")
        fields = {**tx.get_dag(row.dag).bindings, **changes}
        rowdag = tx.put_dag(root=maps.literal(tx, "wrong") if fault == "root" else fields["selection"], bindings=fields)
        entriesdag = maps.link(tx, tx.get_dag(table.dag).bindings["entries"])
        fields = dict(tx.get_dag(entriesdag).bindings)
        fields[row.key] = tx.put_subdag(rowdag)
        if fault == "key":
            fields["datum-wrong"] = fields.pop(row.key)
        if fault == "cap":
            fields.update({"extra%d" % i: tx.put_subdag(rowdag) for i in range(16)})
        if fault == "duplicate-slot":
            empty = tx.put_datum(d.Datum.map(()))
            other = clone(tx, rowdag, fields={"arguments": tx.put_literal(empty)})
            fields[reuse.datum_key(empty)] = tx.put_subdag(other)
        entriesdag = tx.put_dag(root=fields["role"], bindings=fields)
        changes = {"entries": tx.put_subdag(entriesdag)}
        if fault == "profile":
            changes["profile"] = maps.literal(tx, "old")
        if fault == "uri":
            changes["intent"] = maps.literal(tx, d.Datum.uri("urn:other"))
        entries = maps.tree(tx, table.commit)
        entries["double-table"] = clone(tx, table.dag, fields=changes, root=changes.get("intent"))
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    different = story.construct(path, basis, prefix="nonmatching", pairs=((state[3]["x"], state[3]["n13"]),))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        request(success, commit=different.commit, inputs_name=different.name, reuse_ref=None)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("field", reuse.SCALARS + reuse.LINKS + ("arguments", "role"))
def test_Dd_native_claims_recomputed_not_flags(success, field):
    path = success[0]
    got = request(success)
    with d.Repository(path) as repo, repo.write() as tx:
        change = tx.put_subdag(success[3].dag) if field in reuse.LINKS else maps.literal(tx, d.Datum.uri("urn:wrong") if field == "intent" else "wrong")
        bad = clone(tx, got.decision.dag, fields={field: change}, root=change if field == "inputs" else None)
        entries = maps.tree(tx, got.decision.commit)
        entries["new"] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(got.decision.base,))
    with pytest.raises((ValueError, KeyError)):
        reuse.inspect_decision(path, commit=basis, decision_name="new")


@pytest.mark.parametrize("fault", ["Q-parent", "W-parent", "W-ownQ", "W-T", "W-extra", "D-parent", "D-extra", "D-existing", "D-shape", "D-root"])
def test_pinned_spine_native_only_intended_deltas(success, fault):
    path = success[0]
    got = request(success)
    with d.Repository(path) as repo, repo.write() as tx:
        target = got.reused.commit if fault.startswith("W") else got.recorded.commit if fault.startswith("Q") else got.decision.commit
        entries = maps.tree(tx, target)
        if fault == "W-ownQ":
            entries["reuse-" + got.recorded.request_id] = clone(tx, got.reused.dag, fields={"request": tx.put_subdag(success[2].request)})
        elif fault == "W-T":
            entries["reuse-" + got.recorded.request_id] = clone(tx, got.reused.dag, fields={"attempt": tx.put_subdag(got.recorded.request)})
        elif fault.endswith("extra"):
            entries["extra"] = got.decision.dag
        elif fault in ("D-shape", "D-root"):
            entries["new"] = clone(tx, got.decision.dag, fields={"extra": maps.literal(tx, 1)} if fault == "D-shape" else {}, root=maps.literal(tx, 2) if fault == "D-root" else None)
        parents = tx.get_commit(target).parents
        if fault.endswith("parent"):
            parents = ()
        if fault == "D-existing":
            parents = (got.decision.commit,)
        bad = tx.put_commit(tx.put_tree(entries), parents=parents)
    with pytest.raises((ValueError, KeyError)):
        if fault.startswith("W"):
            inspect(path, got, satisfaction_commit=bad)
        elif fault.startswith("Q"):
            inspect(path, got, commit=bad)
        else:
            reuse.inspect_decision(path, commit=bad, decision_name="new")


def test_coherent_alternate_Dd_Cq_claimed_original_base_rejects_BEFORE_W(success, monkeypatch):
    path = success[0]
    original = ex.record_exchange_request
    alternative = request(success, control="fresh", decision_name="new", decision_ref="alternative-d", submission_ref="alternative-q", reuse_ref=None)
    assert inspect(path, alternative).decision.reason == "explicit-fresh"
    def substituted(*args, **kwargs):
        actual = original(*args, **kwargs)
        # Move only test-owned submission/reservation to a coherent alternate Cq,
        # preserving returned claims of the original newly authored Dd.
        with d.Repository(path) as repo, repo.write() as tx:
            tx.update_ref(actual.ref, alternative.recorded.commit)
        return replace(alternative.recorded, base=actual.base, ref=actual.ref)
    monkeypatch.setattr(ex, "record_exchange_request", substituted)
    with pytest.raises(ValueError, match="actual submission parent"):
        request(success)
    with d.Repository(path) as repo, repo.read() as tx:
        tx.get_ref("new-decision")
        with pytest.raises(d.NotFoundError):
            tx.get_ref("new-w")


@pytest.mark.parametrize("fault", ["base", "ref", "request-id", "request", "W-response"])
def test_late_own_descriptions_do_not_erase_complete_Q(success, monkeypatch, fault):
    path = success[0]
    original = ex.record_exchange_request
    def changed(*args, **kwargs):
        got = original(*args, **kwargs)
        if fault == "W-response":
            return got
        values = {"base": success[1].recorded.commit, "ref": "wrong", "request-id": "q-" + "0" * 32, "request": success[2].request}
        return replace(got, **{fault.replace("-", "_"): values[fault]})
    monkeypatch.setattr(ex, "record_exchange_request", changed)
    if fault == "W-response":
        original_w = reuse._publish_reuse
        def wrong(*a, **k):
            return replace(original_w(*a, **k), result=success[2].inputs)
        monkeypatch.setattr(reuse, "_publish_reuse", wrong)
    with pytest.raises((ValueError, KeyError)):
        request(success)
    with d.Repository(path) as repo, repo.read() as tx:
        tx.get_ref("new-q")
        if fault != "W-response":
            with pytest.raises(d.NotFoundError):
                tx.get_ref("new-w")


def test_one_key_removal_branches_and_explicit_reselection_no_discovery(success, monkeypatch):
    path, q, selected, table, child = success
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("metadata/read never dispatches"))
        removed = reuse.remove_entry(path, commit=table.commit, table_name=table.name, argument_datum=q.decision.inputs.datum, ref="removed")
        assert reuse.inspect_table(path, commit=removed.commit, table_name=table.name).entries == ()
        assert reuse.inspect_table(path, commit=table.commit, table_name=table.name) == table
        miss = request(success, commit=removed.commit, reuse_ref=None)
        assert miss.decision.reason == "no-entry"
        again = reuse.select_entry(path, commit=removed.commit, table_name=table.name, selection_slot=selected.slot, ref="again")
        assert again.entries[0].selected.attempt == selected.attempt
    with pytest.raises(ValueError, match="present"):
        reuse.remove_entry(path, commit=removed.commit, table_name=table.name, argument_datum=q.decision.inputs.datum, ref="absent")
    for operation in (reuse.select_entry, reuse.adopt_entry):
        with pytest.raises(ValueError):
            operation(path, commit=table.commit, table_name=table.name, selection_slot=selected.slot, ref="invalid")
    with pytest.raises(ValueError):
        reuse.adopt_entry(path, commit=removed.commit, table_name=table.name, selection_slot=selected.slot, ref="invalid")
    with pytest.raises(TypeError):
        reuse.datum_key(None)


@pytest.mark.parametrize("fault", ["node", "S", "R", "return-node", "role", "trace-Q", "trace-input", "get-map", "get-key", "get-result", "get-opcode", "trace-extra"])
def test_returned_profile_source_and_trace_strict_PUBLIC_S_actual_Q_authority(success, fault):
    path, q, selected, table, child = success
    original = maps.returned_source(path, commit=table.commit, slot=selected.slot, output_name="returned", ref="returned")
    with d.Repository(path) as repo, repo.write() as tx:
        if fault in ("node", "S", "R"):
            fields = {"node": maps.literal(tx, tx.get_dag(q.decision.inputs.dag).root.bytes)} if fault == "node" else {"selection" if fault == "S" else "returned": tx.put_subdag(q.decision.inputs.dag)}
            bad = clone(tx, original.dag, fields=fields)
        else:
            # Change application R without pretending modified R remains PUBLIC S.
            returned = tx.get_dag(selected.result)
            if fault == "return-node":
                bad_return = clone(tx, selected.result, fields={"return": tx.put_subdag(q.decision.inputs.dag)}, root=tx.put_subdag(q.decision.inputs.dag))
            elif fault == "role":
                bad_return = clone(tx, selected.result, fields={"role": maps.literal(tx, "arbitrary-root84")})
            else:
                trace = maps.link(tx, returned.bindings["trace"])
                fields = {}
                if fault == "trace-Q":
                    fields["request"] = tx.put_subdag(q.decision.inputs.dag)
                elif fault == "trace-input":
                    fields["inputs"] = tx.put_subdag(selected.result)
                elif fault == "trace-extra":
                    fields["extra"] = maps.literal(tx, 1)
                else:
                    getter = maps.link(tx, tx.get_dag(trace).bindings["access-00"])
                    changes = {"map": tx.put_subdag(q.decision.inputs.dag)} if fault == "get-map" else {"key": maps.literal(tx, "missing")} if fault == "get-key" else {"result": maps.literal(tx, 99)} if fault == "get-result" else {"opcode": maps.literal(tx, "map_insert")}
                    fields["access-00"] = tx.put_subdag(clone(tx, getter, fields=changes, root=changes.get("result")))
                trace = clone(tx, trace, fields=fields)
                bad_return = clone(tx, selected.result, fields={"trace": tx.put_subdag(trace)})
            bad = bad_return
        entries = maps.tree(tx, original.commit)
        entries["bad"] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(original.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        if fault in ("node", "S", "R"):
            maps.inspect_source(path, commit=basis, dag=bad)
        else:
            maps.Inspector(path, basis).returned(bad, request=q.recorded.request, inputs=q.recorded.inputs)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["uri", "control", "name", "ref", "reuse-ref", "map-size", "required"])
def test_invalid_controls_no_Dd_Q_metadata(state, fault):
    path, _, _, _, inputs = state
    args = dict(commit=inputs.commit, intent_uri=story.DOUBLE, binding_name="double-binding", inputs_name=inputs.name, table_name="table", decision_name="decision", decision_ref="decision", submission_ref="submission")
    args.update({"intent_uri": "URN:Example"} if fault == "uri" else {"control": "unknown"} if fault == "control" else {"decision_name": "request-q-collision"} if fault == "name" else {"decision_ref": "submission"} if fault == "ref" else {"reuse_ref": "unneeded"} if fault == "reuse-ref" else {"map_size": -1} if fault == "map-size" else {"control": "require-selected"})
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        reuse.record_request(path, **args)
    assert_file_unchanged(path / "data.mdb", before)


def test_empty_table_canonical_reader_and_existing_define_scope(state, monkeypatch):
    path, _, _, _, inputs = state
    got = reuse.define_table(path, commit=inputs.commit, table_name="table", intent_uri=story.DOUBLE, ref="table")
    with pytest.raises(ValueError, match="absent"):
        reuse.define_table(path, commit=got.commit, table_name="table", intent_uri=story.DOUBLE, ref="other")
    # Native packed URI already enforces canonicality; a separate reader-side
    # canonicalizer control proves empty rows do not bypass explicit scope check.
    original = d.canonicalize_uri
    monkeypatch.setattr(d, "canonicalize_uri", lambda uri: "urn:other")
    with pytest.raises(ValueError, match="canonical"):
        reuse.inspect_table(path, commit=got.commit, table_name="table")
    monkeypatch.setattr(d, "canonicalize_uri", original)


def test_same42_distinct_full_input_and_requested_binding_hit_retains_two_chains(success, state):
    path, q, selected, table, _ = success
    with d.Repository(path) as repo, repo.write() as tx:
        value = maps.literal(tx, 42)
        source_dag = tx.put_dag(root=value, bindings={"v": value, "method": maps.literal(tx, "different literal origin")})
        entries = maps.tree(tx, table.commit)
        entries["new-literal"] = source_dag
        entries["alternate-binding"] = maps.local.put_local_binding(tx, source=binding.capture("double") + b"\n# distinct captured implementation\n", interpreter=__import__("sys").executable, timeout_ms=10000)
        base = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    source = maps.literal_source(path, commit=base, source_dag=source_dag, source_name="v", output_name="new-source", ref="new-source")
    full = story.construct(path, source.commit, prefix="new-map", pairs=((state[3]["x"], source.dag),))
    got = request(success, commit=full.commit, binding_name="alternate-binding", inputs_name=full.name)
    reading = inspect(path, got)
    assert reading.requested.datum == reading.executed.datum
    assert reading.requested.dag != reading.executed.dag
    assert reading.requested.construction != reading.executed.construction
    assert got.recorded.binding != selected.binding
    assert got.reused.attempt == selected.attempt
    assert reading.returned.request == selected.request != reading.request


def test_actual_distinct_same_datum_adoption_other_key_true_sibling_branches(success, state, tmp_path):
    path, q, selected, table, child = success
    other = story.construct(path, table.commit, prefix="other", pairs=((state[3]["x"], state[3]["n13"]),))
    q2 = request(success, commit=other.commit, inputs_name=other.name, reuse_ref=None, decision_name="other-d", decision_ref="other-d", submission_ref="other-q")
    s2, _ = story.execute(path, tmp_path, q2, 2)
    two = reuse.select_entry(path, commit=s2.commit, table_name=table.name, selection_slot=s2.slot, ref="two")
    assert len(two.entries) == 2
    fresh = request(success, commit=two.commit, control="fresh", decision_name="fresh-d", decision_ref="fresh-d", submission_ref="fresh-q", reuse_ref=None)
    s3, _ = story.execute(path, tmp_path, fresh, 3)
    assert s3.attempt_id != selected.attempt_id
    # Both branches start from EXACT same s3.commit; keep and adopt differ only table.
    with d.Repository(path) as repo, repo.write() as tx:
        keep = tx.put_commit(tx.get_commit(s3.commit).tree, parents=(s3.commit,))
        tx.create_ref("keep", keep)
    adopted = reuse.adopt_entry(path, commit=s3.commit, table_name=table.name, selection_slot=s3.slot, ref="adopt")
    old = reuse.inspect_table(path, commit=keep, table_name=table.name)
    assert next(r for r in old.entries if r.inputs.datum == q.decision.inputs.datum).selected.attempt == selected.attempt
    assert next(r for r in adopted.entries if r.inputs.datum == q.decision.inputs.datum).selected.attempt == s3.attempt
    other_old = next(r for r in old.entries if r.inputs.datum != q.decision.inputs.datum)
    other_new = next(r for r in adopted.entries if r.inputs.datum != q.decision.inputs.datum)
    assert (other_old.dag, other_old.selected.dag) == (other_new.dag, other_new.selected.dag)
    removed = reuse.remove_entry(path, commit=adopted.commit, table_name=table.name, argument_datum=q.decision.inputs.datum, ref="remove-one")
    assert len(removed.entries) == 1 and removed.entries[0].dag == other_new.dag
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_commit(keep).parents == tx.get_commit(adopted.commit).parents == (s3.commit,)
        assert maps.tree(tx, removed.commit)[selected.slot] == selected.dag
    got = request(success, commit=adopted.commit, decision_name="new-adopted", decision_ref="new-adopted", submission_ref="new-adopted-q", reuse_ref="new-adopted-w")
    assert got.reused.attempt == s3.attempt


def test_table_remaining_reader_errors_and_native_closure_even_explicit_fresh(success, state, monkeypatch):
    path, q, selected, table, child = success
    with d.Repository(path) as repo, repo.write() as tx:
        entries = maps.tree(tx, table.commit)
        entries["wrong"] = table.dag
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    with pytest.raises(ValueError, match="names must differ"):
        request(success, binding_name="double-table")
    with pytest.raises(ValueError, match="must be absent"):
        request(success, decision_name="decision-1", decision_ref="d2", submission_ref="q2")
    # Native URI permits another canonical scope but selection policy rejects it.
    with pytest.raises(ValueError, match="scope"):
        reuse.select_entry(path, commit=reuse.define_table(path, commit=basis, table_name="wrong-scope", intent_uri="urn:other", ref="wrong-scope").commit, table_name="wrong-scope", selection_slot=selected.slot, ref="never")
    with d.Repository(path) as repo, repo.write() as tx:
        entries = maps.tree(tx, table.commit)
        entries["double-table"] = clone(tx, table.dag, fields={"entries": tx.put_subdag(selected.result)})
        bad = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    with pytest.raises((ValueError, KeyError)):
        reuse.inspect_table(path, commit=bad, table_name=table.name)
    # Explicit fresh ignores application table framing, but still public typed
    # full history validation (including side-parent composite descendants).
    assert request(success, commit=bad, control="fresh", reuse_ref=None).decision.table is None
    inspector = maps.Inspector(path, table.commit)
    output = inspector.returned(selected.result, request=selected.request, inputs=selected.inputs)
    assert inspector.returned(selected.result, request=selected.request, inputs=selected.inputs) is output
    real = reuse.maps.Inspector
    class WrongArgument(real):
        def input(self, dag):
            return replace(super().input(dag), datum=selected.result)
    with monkeypatch.context() as guard:
        guard.setattr(reuse.maps, "Inspector", WrongArgument)
        with pytest.raises(ValueError, match="argument datum"):
            reuse.inspect_table(path, commit=table.commit, table_name=table.name)


def test_own_public_prepared_response_dimensions_and_existing_W_guard(success, monkeypatch):
    path = success[0]
    got = request(success)
    original = reuse._prepare
    def substituted(*args, **kwargs):
        prepared = original(*args, **kwargs)
        if kwargs.get("request") is not None or len(args) > 6 and args[6] is not None:
            return replace(prepared, binding=success[2].inputs)
        return prepared
    with monkeypatch.context() as guard:
        guard.setattr(reuse, "_prepare", substituted)
        with pytest.raises(ValueError, match="actual full Q"):
            inspect(path, got)
    with pytest.raises(ValueError, match="already exists"):
        reuse._publish_reuse(path, replace(got.recorded, commit=got.reused.commit), got.decision.selected, "existing-w", 0)


@pytest.mark.parametrize("fault", ["Q-profile", "Q-occurrence", "trace-cap", "get-literal", "return-source-value"])
def test_remaining_strict_return_profile_native_controls(success, fault):
    path, q, selected, table, _ = success
    source = maps.returned_source(path, commit=table.commit, slot=selected.slot, output_name="returned", ref="returned")
    with d.Repository(path) as repo, repo.write() as tx:
        fields = tx.get_dag(selected.result).bindings
        trace = maps.link(tx, fields["trace"])
        expected_request = selected.request
        if fault in ("Q-profile", "Q-occurrence"):
            qfields = dict(tx.get_dag(selected.request).bindings)
            if fault == "Q-profile":
                qfields["inputs"] = tx.put_subdag(selected.result)
            qdag = tx.put_dag(root=maps.literal(tx, "invalid") if fault == "Q-occurrence" else tx.get_dag(selected.request).root, bindings=qfields)
            expected_request = qdag
            trace = clone(tx, trace, fields={"request": tx.put_subdag(qdag)})
        elif fault == "trace-cap":
            getter = tx.get_dag(trace).bindings["access-00"]
            trace = clone(tx, trace, fields={"access-%02d" % i: getter for i in range(17)})
        elif fault == "get-literal":
            getter = maps.link(tx, tx.get_dag(trace).bindings["access-00"])
            getdag = clone(tx, getter, fields={"key": maps.literal(tx, 1)})
            trace = clone(tx, trace, fields={"access-00": tx.put_subdag(getdag)})
        if fault == "return-source-value":
            bad = clone(tx, source.dag, fields={"result": maps.literal(tx, 99)}, root=maps.literal(tx, 99))
        else:
            bad = clone(tx, selected.result, fields={"trace": tx.put_subdag(trace)})
        entries = maps.tree(tx, source.commit)
        entries["bad"] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(source.commit,))
    with pytest.raises(ValueError):
        if fault == "return-source-value":
            maps.inspect_source(path, commit=basis, dag=bad)
        else:
            maps.Inspector(path, basis).returned(bad, request=expected_request, inputs=selected.inputs)
