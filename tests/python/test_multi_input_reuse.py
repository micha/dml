"""Strict ordinary table/new decision tests, public authority and no dispatch."""

from dataclasses import replace
import sys
import subprocess

import daggerml as d
from daggerml import transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_exchange import (
    ROOT,
    exchange_runtime,
    literal,
    nested,
    scalar,
    tree,
    typed_oracle,
)
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged
from test_records_hypothesis import run_driver
from test_implementation_supersession import state
from test_implementation_selection import menu, define
from test_explicit_reuse import double
from test_composed_execution import producer, execute
from test_reuse_selection import expected_file

paths = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    import multi_input_reuse as app
finally:
    sys.path[:] = paths


def empty(state, **changes):
    path, definition = state
    args = dict(
        commit=definition.commit,
        table_name="table",
        intent_uri=definition.intent_uri,
        binding_name="binding-a",
        ref="table",
    )
    args.update(changes)
    return app.define_table(path, **args)


def request(state, commit, **changes):
    args = dict(
        commit=commit,
        intent_name="intent",
        inputs_name="inputs",
        table_name="table",
        decision_name="decision",
        decision_ref="decision",
        submission_ref="submission",
    )
    args.update(changes)
    return app.record_policy_request(state[0], **args)


def inspect_request(path, got, **changes):
    args = dict(
        commit=got.recorded.commit,
        request=got.recorded.request,
        decision_name=got.decision.name,
        satisfaction_commit=None if got.reused is None else got.reused.commit,
    )
    args.update(changes)
    return app.inspect_request(path, **args)


@pytest.fixture
def indexed(menu, expected_file):
    path = menu[0][0][0]
    definition = define(menu)
    table = app.define_table(
        path,
        commit=definition.commit,
        table_name="table",
        intent_uri=definition.intent_uri,
        binding_name="double-a-binding",
        ref="table",
    )
    chosen = app.selection.select(
        path,
        commit=table.commit,
        slot="immutable-old",
        binding_name="double-a-binding",
        inputs_name="double-inputs",
        intent_uri=definition.intent_uri,
        packet=menu[0][2][0],
        expected_file=expected_file,
        ref="captured",
    )
    inserted = app.select_entry(
        path,
        commit=chosen.commit,
        table_name="table",
        selection_slot=chosen.slot,
        ref="inserted",
    )
    return path, definition, table, chosen, inserted


def table_request(indexed, **changes):
    path, definition, _, chosen, table = indexed
    args = dict(
        commit=table.commit,
        intent_name=definition.name,
        inputs_name="double-inputs",
        table_name="table",
        decision_name="decision",
        decision_ref="decision",
        submission_ref="submission",
        reuse_ref="satisfaction",
    )
    args.update(changes)
    return app.record_policy_request(path, **args)


def test_empty_public_authoring_transfer_exact_parent_only_table_no_dispatch(
    state, tmp_path, monkeypatch
):
    path, definition = state
    old = typed_oracle(path, (definition.commit,))
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("no dispatch"))
        got = empty(state)
        assert app.inspect_table(path, commit=got.commit, table_name="table") == got
    with d.Repository(path) as repo, repo.read() as tx:
        entries = tree(tx, definition.commit)
        entries["table"] = got.dag
        assert tree(tx, got.commit) == entries
        assert tx.get_commit(got.commit).parents == (definition.commit,)
        assert tx.get_ref("table") == got.commit
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
    replica = tmp_path / "replica"
    with d.Repository(replica, create=True):
        pass
    transfer.import_commit(replica, transfer.export_commit(path, commit=got.commit))
    assert app.inspect_table(replica, commit=got.commit, table_name="table") == got


@pytest.mark.parametrize(
    "present,override,reason",
    [
        (False, "default", "default-no-table"),
        (True, "default", "default-no-entry"),
        (True, "fresh", "override-fresh"),
    ],
)
def test_default_miss_and_explicit_fresh_new_Dm_own_Q_no_T(
    state, present, override, reason
):
    basis = empty(state).commit if present else state[1].commit
    got = request(state, basis, override=override)
    assert got.decision.reason == reason and got.reused is None
    assert got.decision.base == basis
    assert inspect_request(state[0], got) == got.decision
    assert (got.decision.table is not None) == (present and override != "fresh")
    with d.Repository(state[0]) as repo, repo.read() as tx:
        assert tx.get_commit(got.decision.commit).parents == (basis,)
        assert nested(tx, got.recorded.request, "inputs") == got.decision.inputs
        assert scalar(tx, got.decision.dag, "role") == app.DECISION_ROLE
    for q in (None, state[1].dag):
        with pytest.raises((TypeError, ValueError)):
            inspect_request(state[0], got, request=q)
    with pytest.raises(ValueError, match="fresh"):
        inspect_request(state[0], got, satisfaction_commit=got.recorded.commit)
    # Old exact-D reader rejects this NEW role, not silently generalized.
    with pytest.raises(ValueError):
        app.policy.inspect_request(
            state[0],
            commit=got.recorded.commit,
            request=got.recorded.request,
            decision_name="decision",
        )


@pytest.mark.parametrize("present", [False, True])
def test_explicit_reuse_requires_hit_without_any_publication(state, present):
    basis = empty(state).commit if present else state[1].commit
    before = (state[0] / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="matching table entry"):
        request(state, basis, override="reuse-selected", reuse_ref="satisfaction")
    assert_file_unchanged(state[0] / "data.mdb", before)


@pytest.mark.parametrize(
    "changes",
    [
        {"table_name": None},
        {"table_name": "binding-a"},
        {"ref": "bad/name"},
        {"map_size": True},
        {"map_size": 1},
        {"map_size": -1},
        {"map_size": sys.maxsize + 1},
        {"intent_uri": "not a uri"},
        {"intent_uri": None},
    ],
)
def test_define_invalid_no_publication(state, changes):
    before = (state[0] / "data.mdb").read_bytes()
    with pytest.raises((TypeError, ValueError, d.DmlError)):
        empty(state, **changes)
    assert_file_unchanged(state[0] / "data.mdb", before)


def test_existing_empty_no_overwrite(state):
    got = empty(state)
    with pytest.raises(ValueError, match="absent"):
        empty(state, commit=got.commit, ref="other")
    with pytest.raises(TypeError):
        app.input_key(None)


@pytest.mark.parametrize(
    "changes",
    [
        {"implementation_override": "unknown"},
        {"implementation_override": None},
        {"override": "unknown"},
        {"override": None},
        {"table_name": "inputs"},
        {"decision_name": "request-q-collision"},
        {"decision_name": "bad/name"},
        {"decision_ref": "submission"},
        {"reuse_ref": "bad/name"},
        {"reuse_ref": "satisfaction"},
    ],
)
def test_request_invalid_no_Dm_Q(state, changes):
    before = (state[0] / "data.mdb").read_bytes()
    with pytest.raises((TypeError, ValueError)):
        request(state, state[1].commit, **changes)
    assert_file_unchanged(state[0] / "data.mdb", before)


@pytest.mark.parametrize(
    "level,names",
    [("table", ("role", "intent", "binding", "entries")), ("entries", ("role",))],
)
@pytest.mark.parametrize("fault", ["missing", "type", "node", "root", "extra", "role"])
def test_strict_empty_shape_never_fallback(state, level, names, fault):
    path = state[0]
    got = empty(state)
    with d.Repository(path) as repo, repo.write() as tx:
        dag = got.dag if level == "table" else nested(tx, got.dag, "entries")
        fields = dict(tx.get_dag(dag).bindings)
        root = tx.get_dag(dag).root
        field = names[0] if fault in ("role", "extra", "root") else names[-1]
        if fault == "missing":
            fields.pop(field)
        elif fault == "extra":
            fields["extra"] = literal(tx, "wrong")
        elif fault == "root":
            root = literal(tx, "wrong")
        else:
            fields[field] = (
                tx.put_subdag(state[1].dag)
                if fault == "node"
                else literal(tx, True if fault == "type" else "wrong")
            )
            if tx.lookup_node(dag, field) == root:
                root = fields[field]
        changed = tx.put_dag(root=root, bindings=fields)
        table = (
            changed
            if level == "table"
            else clone(tx, got.dag, fields={"entries": tx.put_subdag(changed)})
        )
        entries = tree(tx, got.commit)
        entries["table"] = table
        basis = tx.put_commit(tx.put_tree(entries), parents=(got.commit,))
    with pytest.raises((TypeError, ValueError)):
        request(state, basis)
    # Explicit fresh doesn't consume application framing, but native closure exists.
    assert request(state, basis, override="fresh").decision.table is None


@pytest.mark.parametrize("override", ["default", "reuse-selected"])
def test_selected_reuse_exact_own_Q_original_W_and_pinned_after_ref_move(
    indexed, override
):
    path, definition, _, chosen, table = indexed
    old = typed_oracle(path, (table.commit,))
    got = table_request(indexed, override=override)
    assert got.decision.entry.inputs == chosen.inputs
    assert got.reused.attempt == chosen.attempt and got.reused.result == chosen.result
    assert got.recorded.request != chosen.request
    assert got.decision.reason == (
        "default-entry" if override == "default" else "override-selected-reuse"
    )
    assert inspect_request(path, got) == got.decision
    with d.Repository(path) as repo, repo.write() as tx:
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        assert set(tx.get_dag(got.reused.dag).bindings) == {
            "role",
            "request",
            "attempt",
            "result",
        }
        assert nested(tx, got.reused.dag, "request") == got.recorded.request
        tx.update_ref("inserted", got.recorded.commit)
    assert inspect_request(path, got) == got.decision
    with pytest.raises(ValueError):
        inspect_request(path, got, request=chosen.request)


@pytest.mark.parametrize(
    "fault",
    [
        "key",
        "slot",
        "selection",
        "inputs",
        "role",
        "root",
        "extra",
        "missing",
        "literal-selection",
        "wrong-slot-type",
        "cap",
        "duplicate-slot",
    ],
)
def test_all_entry_validation_nonmatching_invalid_rejects(indexed, fault):
    path, definition, _, chosen, table = indexed
    with d.Repository(path) as repo, repo.write() as tx:
        row = table.entries[0]
        changes, root = {}, None
        if fault == "slot":
            changes["selection-slot"] = literal(tx, "absent")
        elif fault == "selection":
            changes["selection"] = tx.put_subdag(definition.dag)
            root = changes["selection"]
        elif fault == "inputs":
            changes["inputs"] = tx.put_subdag(definition.dag)
        elif fault == "role":
            changes["role"] = literal(tx, "wrong")
        elif fault == "root":
            root = literal(tx, "wrong")
        elif fault == "extra":
            changes["extra"] = literal(tx, "wrong")
        elif fault == "literal-selection":
            changes["selection"] = literal(tx, "wrong")
            root = changes["selection"]
        elif fault == "wrong-slot-type":
            changes["selection-slot"] = literal(tx, True)
        row_dag = clone(tx, row.dag, fields=changes, root=root)
        if fault == "missing":
            fields = dict(tx.get_dag(row.dag).bindings)
            fields.pop("inputs")
            row_dag = tx.put_dag(root=tx.get_dag(row.dag).root, bindings=fields)
        rows_dag = nested(tx, table.dag, "entries")
        fields = dict(tx.get_dag(rows_dag).bindings)
        fields[row.key] = tx.put_subdag(row_dag)
        if fault == "key":
            fields["input-wrong"] = fields.pop(row.key)
        if fault == "cap":
            fields.update(
                {"extra-" + str(i): tx.put_subdag(row_dag) for i in range(16)}
            )
        if fault == "duplicate-slot":
            # A second full-input key aliases same S: either slot uniqueness or
            # full public selection identity must reject, never result equality.
            second = definition.dag
            fields[app.input_key(second)] = tx.put_subdag(
                clone(tx, row.dag, fields={"inputs": tx.put_subdag(second)})
            )
        rows_dag = tx.put_dag(root=fields["role"], bindings=fields)
        entries = tree(tx, table.commit)
        entries["table"] = clone(
            tx, table.dag, fields={"entries": tx.put_subdag(rows_dag)}
        )
        n = literal(tx, 3)
        entries["other-inputs"] = tx.put_dag(root=n, bindings={"n": n})
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, TypeError, KeyError)):
        table_request(indexed, commit=basis, inputs_name="other-inputs", reuse_ref=None)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["binding", "uri", "S-inputs", "S-binding", "S-role"])
def test_scope_and_public_S_authority_not_flags(indexed, fault):
    path, definition, _, chosen, table = indexed
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, table.commit)
        if fault in ("binding", "uri"):
            changes = (
                {"binding": tx.put_subdag(entries["double-b-binding"])}
                if fault == "binding"
                else {"intent": literal(tx, d.Datum.uri("urn:other"))}
            )
            entries["table"] = clone(
                tx, table.dag, fields=changes, root=changes.get("binding")
            )
        else:
            changes = {
                fault[2:]: (
                    literal(tx, "wrong")
                    if fault == "S-role"
                    else tx.put_subdag(definition.dag)
                )
            }
            bad = clone(tx, chosen.dag, fields=changes)
            entries[chosen.slot] = bad
            row = table.entries[0]
            rowdag = clone(
                tx,
                row.dag,
                fields={"selection": tx.put_subdag(bad)},
                root=tx.put_subdag(bad),
            )
            rows = nested(tx, table.dag, "entries")
            rows = clone(tx, rows, fields={row.key: tx.put_subdag(rowdag)})
            entries["table"] = clone(
                tx, table.dag, fields={"entries": tx.put_subdag(rows)}
            )
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    with pytest.raises((ValueError, TypeError)):
        table_request(indexed, commit=basis)


def test_valid_nonmatching_key_is_miss_full_inputs_type_witness_not_scalar(indexed):
    path, _, _, _, table = indexed
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, table.commit)
        # Same visible value but distinct full input DAG (producer witness retained).
        fields = dict(tx.get_dag(entries["double-inputs"]).bindings)
        fields["witness"] = literal(tx, "distinct witness")
        entries["other-inputs"] = tx.put_dag(
            root=tx.get_dag(entries["double-inputs"]).root, bindings=fields
        )
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    got = table_request(
        indexed, commit=basis, inputs_name="other-inputs", reuse_ref=None
    )
    assert (
        got.decision.reason == "default-no-entry"
        and got.decision.table.dag == table.dag
    )
    assert got.decision.entry is None
    assert inspect_request(path, got) == got.decision
    with pytest.raises(ValueError, match="scope"):
        table_request(indexed, implementation_override="double-b")
    fresh = table_request(
        indexed,
        implementation_override="double-b",
        override="fresh",
        reuse_ref=None,
        decision_name="decision-b",
        decision_ref="decision-b",
        submission_ref="submission-b",
    )
    assert fresh.decision.table is None


def test_insertion_existing_same_attempt_adoption_and_scope_reject(indexed):
    path, _, _, chosen, table = indexed
    for func in (app.select_entry, app.adopt_entry):
        with pytest.raises(ValueError):
            func(
                path,
                commit=table.commit,
                table_name="table",
                selection_slot=chosen.slot,
                ref="other",
            )
    with pytest.raises(ValueError, match="matching old"):
        app.adopt_entry(
            path,
            commit=chosen.commit,
            table_name="table",
            selection_slot=chosen.slot,
            ref="other",
        )
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, chosen.commit)
        entries["table"] = clone(
            tx, indexed[2].dag, fields={"intent": literal(tx, d.Datum.uri("urn:other"))}
        )
        basis = tx.put_commit(tx.put_tree(entries), parents=(chosen.commit,))
    with pytest.raises(ValueError, match="scope"):
        app.select_entry(
            path,
            commit=basis,
            table_name="table",
            selection_slot=chosen.slot,
            ref="other",
        )


@pytest.mark.parametrize("field", app.SCALARS + app.LINKS + ("role",))
def test_new_Dm_claims_recomputed_actual_parent_not_response(state, field):
    got = request(state, empty(state).commit)
    with d.Repository(state[0]) as repo, repo.write() as tx:
        change = (
            tx.put_subdag(state[1].dag) if field in app.LINKS else literal(tx, "wrong")
        )
        if field == "intent-definition":
            change = tx.put_subdag(got.decision.inputs)
        dag = clone(
            tx,
            got.decision.dag,
            fields={field: change},
            root=change if field == "intent-definition" else None,
        )
        entries = tree(tx, got.decision.commit)
        entries["decision"] = dag
        bad = tx.put_commit(tx.put_tree(entries), parents=(got.decision.base,))
    with pytest.raises((ValueError, KeyError, TypeError)):
        app.inspect_decision(state[0], commit=bad, decision_name="decision")


@pytest.mark.parametrize(
    "fault",
    [
        "parents",
        "extra-tree",
        "existing-Dm",
        "shape",
        "root",
        "Q-parents",
        "W-parents",
        "W-own-Q",
    ],
)
def test_actual_decision_submission_satisfaction_spines(indexed, fault):
    path = indexed[0]
    got = table_request(indexed)
    with d.Repository(path) as repo, repo.write() as tx:
        cdec = got.decision.commit
        entries = tree(tx, cdec)
        if fault == "parents":
            cdec = tx.put_commit(tx.put_tree(entries))
        elif fault == "extra-tree":
            entries["extra"] = got.decision.dag
            cdec = tx.put_commit(tx.put_tree(entries), parents=(got.decision.base,))
        elif fault == "existing-Dm":
            cdec = tx.put_commit(tx.put_tree(entries), parents=(got.decision.commit,))
        elif fault in ("shape", "root"):
            dag = clone(
                tx,
                got.decision.dag,
                fields={"extra": literal(tx, "bad")} if fault == "shape" else {},
                root=literal(tx, "bad") if fault == "root" else None,
            )
            entries["decision"] = dag
            cdec = tx.put_commit(tx.put_tree(entries), parents=(got.decision.base,))
        elif fault == "Q-parents":
            bad = tx.put_commit(tx.get_commit(got.recorded.commit).tree)
        elif fault == "W-parents":
            bad = tx.put_commit(
                tx.get_commit(got.reused.commit).tree, parents=(got.decision.commit,)
            )
        else:
            fields = {"request": tx.put_subdag(indexed[3].request)}
            entries = tree(tx, got.reused.commit)
            entries["reuse-" + got.recorded.request_id] = clone(
                tx, got.reused.dag, fields=fields
            )
            bad = tx.put_commit(tx.put_tree(entries), parents=(got.recorded.commit,))
    with pytest.raises((ValueError, KeyError)):
        if fault.startswith("W-"):
            inspect_request(path, got, satisfaction_commit=bad)
        elif fault == "Q-parents":
            inspect_request(path, got, commit=bad)
        else:
            app.inspect_decision(path, commit=cdec, decision_name="decision")


@pytest.mark.parametrize(
    "fault", ["base", "request", "ref", "binding-name", "satisfaction-dag", "attempt"]
)
def test_late_returned_descriptions_reject_preserve_already_published_batches(
    indexed, monkeypatch, fault
):
    path = indexed[0]
    original = app.selection.reuse_selected

    def changed(*a, **k):
        got = original(*a, **k)
        if fault == "attempt":
            return replace(got, attempt=indexed[1].dag)
        if fault == "satisfaction-dag":
            return replace(got, dag=indexed[1].dag)
        value = {
            "base": indexed[1].commit,
            "request": indexed[3].request,
            "ref": "wrong",
            "binding-name": "wrong",
        }[fault]
        return replace(
            got, recorded=replace(got.recorded, **{fault.replace("-", "_"): value})
        )

    monkeypatch.setattr(app.selection, "reuse_selected", changed)
    with pytest.raises((ValueError, KeyError)):
        table_request(indexed)
    with d.Repository(path) as repo, repo.read() as tx:
        q = tx.get_ref("submission")
        w = tx.get_ref("satisfaction")
        assert tx.get_commit(w).parents == (q,)
        assert tx.get_ref("decision") == tx.get_commit(q).parents[0]


@pytest.mark.parametrize("override", ["fresh", "default"])
def test_default_execute_ignores_application_not_native_closure(state, override):
    path, definition = state
    if override == "default":
        with d.Repository(path) as repo, repo.write() as tx:
            entries = tree(tx, definition.commit)
            entries["intent"] = clone(
                tx,
                definition.dag,
                fields={"reuse-default": literal(tx, "execute-by-default")},
            )
            basis = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    else:
        basis = definition.commit
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, basis)
        entries["table"] = tx.put_dag(root=literal(tx, "unused"))
        basis = tx.put_commit(tx.put_tree(entries), parents=(basis,))
    got = request(state, basis, override=override)
    assert got.decision.table is None and inspect_request(path, got) == got.decision


@pytest.mark.parametrize("present", [False, True])
@pytest.mark.parametrize("override", ["default", "fresh"])
def test_complete_composite_all_parent_native_closure_always_required(
    state, exchange_runtime, present, override
):
    path, definition = state
    basis = empty(state).commit if present else definition.commit
    with d.Repository(path) as repo, repo.write() as tx:
        leaf = tx.put_datum(b"composite-only")
        nested_value = tx.put_datum(d.Datum.list([leaf]))
        side = tx.put_commit(
            tx.put_tree({"side": tx.put_dag(root=tx.put_literal(nested_value))})
        )
        basis = tx.put_commit(tx.get_commit(basis).tree, parents=(basis, side))
    run_driver("raw-delete", str(path), "objects/datums/" + str(leaf))
    with pytest.raises(d.DmlError):
        request(state, basis, override=override)
