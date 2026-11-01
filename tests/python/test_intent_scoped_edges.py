"""New policy's two authorities, explicit removal and old-contract regression."""

from dataclasses import replace

import daggerml as d
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_intent_scoped_reuse import (
    app,
    indexed,
    menu,
    double,
    producer,
    execute,
    expected_file,
    state,
    empty,
    request,
    table_request,
    inspect_request,
)
from test_exchange import literal, nested, scalar, tree, typed_oracle, exchange_runtime
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged


def test_cross_binding_own_Q_and_historical_producer_old_APIs_unchanged(indexed):
    path, definition, _, selected, table = indexed
    old = typed_oracle(path, (table.commit,))
    got = table_request(indexed, implementation_override="double-b")
    assert got.decision.binding == got.recorded.binding != selected.binding
    assert got.decision.selected.binding == selected.binding
    assert got.reused.attempt == selected.attempt
    assert got.recorded.request != selected.request
    with d.Repository(path) as repo, repo.read() as tx:
        assert nested(tx, got.recorded.request, "binding") == got.decision.binding
        assert nested(tx, selected.request, "binding") == selected.binding
        assert nested(tx, selected.attempt, "request") == selected.request
        assert nested(tx, got.reused.dag, "request") == got.recorded.request
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
    assert inspect_request(path, got) == got.decision
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="binding"):
        app.selection.reuse_selected(
            path,
            commit=table.commit,
            slot=selected.slot,
            binding_name="double-b-binding",
            inputs_name="double-inputs",
            intent_uri=definition.intent_uri,
            submission_ref="old-q",
            ref="old-w",
        )
    assert_file_unchanged(path / "data.mdb", before)


def test_historical_producer_need_not_be_in_current_menu(indexed):
    path, definition, _, selected, table = indexed
    # Valid new fixed menu captures B and C, preserving historical A/S/Q/T authority.
    from daggerml import local

    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, table.commit)
        entries["binding-c"] = local.put_local_binding(
            tx,
            source=b"print('C')",
            interpreter=__import__("sys").executable,
            timeout_ms=10000,
        )
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    new = app.policy.define(
        path,
        commit=basis,
        intent_name="new-intent",
        intent_uri=definition.intent_uri,
        default="reuse-by-default",
        implementations=(
            ("b", "double-b-binding", "new-b-slot"),
            ("c", "binding-c", "new-c-slot"),
        ),
        default_implementation="b",
        ref="new-menu",
    )
    got = table_request(indexed, commit=new.commit, intent_name="new-intent")
    assert got.recorded.binding != selected.binding
    assert all(
        c.binding != selected.binding for c in got.decision.definition.implementations
    )
    assert inspect_request(path, got) == got.decision


@pytest.mark.parametrize(
    "fault", ["None", "binding", "inputs", "commit", "request-id", "inputs-name"]
)
def test_returned_ownQ_rejects_BEFORE_W_preserves_complete_Q(
    indexed, monkeypatch, fault
):
    original = app.ex.record_exchange_request

    def changed(*a, **k):
        got = original(*a, **k)
        field, value = {
            "None": ("request", None),
            "binding": ("binding", indexed[3].binding),
            "inputs": ("inputs", indexed[1].dag),
            "commit": ("commit", indexed[3].commit),
            "request-id": ("request_id", "q-" + "0" * 32),
            "inputs-name": ("inputs_name", "wrong"),
        }[fault]
        return replace(got, **{field: value})

    monkeypatch.setattr(app.ex, "record_exchange_request", changed)
    with pytest.raises((ValueError, TypeError, d.NotFoundError)):
        table_request(indexed, implementation_override="double-b")
    with d.Repository(indexed[0]) as repo, repo.read() as tx:
        assert tx.get_ref("submission")
        with pytest.raises(d.NotFoundError):
            tx.get_ref("satisfaction")


@pytest.mark.parametrize("fault", ["attempt", "result", "dag", "ref", "recorded"])
def test_returned_W_rejects_after_complete_W(indexed, monkeypatch, fault):
    original = app._publish_reuse

    def changed(*a, **k):
        got = original(*a, **k)
        return replace(
            got,
            **{
                fault: {
                    "attempt": indexed[1].dag,
                    "result": indexed[1].dag,
                    "dag": indexed[1].dag,
                    "ref": "wrong",
                    "recorded": replace(got.recorded, request=indexed[3].request),
                }[fault]
            },
        )

    monkeypatch.setattr(app, "_publish_reuse", changed)
    with pytest.raises(ValueError):
        table_request(indexed, implementation_override="double-b")
    with d.Repository(indexed[0]) as repo, repo.read() as tx:
        assert tx.get_commit(tx.get_ref("satisfaction")).parents == (
            tx.get_ref("submission"),
        )


def test_coherent_alternative_Di_Cq_rejected_at_ACTUAL_parent_BEFORE_W(
    indexed, monkeypatch
):
    path = indexed[0]
    # Same decision name/dimensions, but valid different override; no collision.
    alternate = table_request(
        indexed,
        implementation_override="double-b",
        override="fresh",
        reuse_ref=None,
        decision_ref="alternate-Di",
        submission_ref="alternate-Q",
    )
    original = app.ex.record_exchange_request
    returned = []

    def coherent_other_parent(*a, **k):
        claimed_base = k["commit"]
        k["commit"] = alternate.decision.commit
        got = original(*a, **k)
        returned.append(got)
        # Exact own Q, real submission/reservation refs, matching binding/full inputs.
        # Only returned base lies about the actual native parent.
        return replace(got, base=claimed_base)

    monkeypatch.setattr(app.ex, "record_exchange_request", coherent_other_parent)
    with pytest.raises(ValueError, match="actual submission parent differs"):
        table_request(indexed, implementation_override="double-b")
    actual = returned[0]
    # Public exact reader proves alternative is coherent, not malformed/oldQ/collision.
    assert (
        app.inspect_request(
            path, commit=actual.commit, request=actual.request, decision_name="decision"
        )
        == alternate.decision
    )
    with d.Repository(path) as repo, repo.read() as tx:
        assert (
            tx.get_ref("submission")
            == tx.get_ref("request-" + actual.request_id)
            == actual.commit
        )
        assert tx.get_commit(actual.commit).parents == (alternate.decision.commit,)
        authored = tx.get_ref("decision")
        assert authored != alternate.decision.commit
        assert tx.get_commit(authored).parents == (indexed[4].commit,)
        with pytest.raises(d.NotFoundError):
            tx.get_ref("satisfaction")


def test_remove_last_valid_empty_old_proof_no_retarget_no_ban(indexed):
    path, _, _, selected, table = indexed
    pinned = table_request(indexed, implementation_override="double-b")
    old = typed_oracle(path, (pinned.reused.commit,))
    removed = app.remove_entry(
        path,
        commit=pinned.reused.commit,
        table_name="table",
        inputs=selected.inputs,
        ref="removed",
    )
    assert removed.entries == ()
    assert app.inspect_table(path, commit=removed.commit, table_name="table") == removed
    with d.Repository(path) as repo, repo.read() as tx:
        previous, current = tree(tx, pinned.reused.commit), tree(tx, removed.commit)
        assert previous.pop("table") == table.dag
        current.pop("table")
        assert current == previous
        assert tx.get_commit(removed.commit).parents == (pinned.reused.commit,)
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        assert current[selected.slot] == selected.dag
    assert inspect_request(path, pinned) == pinned.decision
    before = (path / "data.mdb").read_bytes()
    for inputs in (selected.inputs, pinned.decision.definition.dag):
        with pytest.raises(ValueError, match="present"):
            app.remove_entry(
                path,
                commit=removed.commit,
                table_name="table",
                inputs=inputs,
                ref="bad",
            )
    with pytest.raises(TypeError):
        app.remove_entry(
            path, commit=removed.commit, table_name="table", inputs=None, ref="bad"
        )
    with pytest.raises(ValueError, match="matching table entry"):
        table_request(
            indexed,
            commit=removed.commit,
            override="reuse-selected",
            decision_name="missing",
            decision_ref="missing",
            submission_ref="missing-q",
        )
    assert_file_unchanged(path / "data.mdb", before)
    missed = table_request(
        indexed,
        commit=removed.commit,
        reuse_ref=None,
        decision_name="miss",
        decision_ref="miss",
        submission_ref="miss-q",
    )
    assert missed.reused is None and missed.decision.reason == "default-no-entry"
    # Explicit reselection of retained S is allowed, separate from requesting.
    restored = app.select_entry(
        path,
        commit=removed.commit,
        table_name="table",
        selection_slot=selected.slot,
        ref="restored",
    )
    assert restored.entries[0].selected.dag == selected.dag
    assert (
        app.inspect_table(
            path, commit=missed.recorded.commit, table_name="table"
        ).entries
        == ()
    )


@pytest.mark.parametrize("fault", ["old-table", "old-decision", "advisory"])
def test_old_roles_not_reinterpreted_advisory_does_not_filter(indexed, fault):
    path, definition, _, selected, table = indexed
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, table.commit)
        if fault == "old-table":
            fields = dict(tx.get_dag(table.dag).bindings)
            fields["role"] = literal(tx, "example-multi-input-table-v1")
            fields["binding"] = tx.put_subdag(selected.binding)
            entries["table"] = tx.put_dag(root=fields["binding"], bindings=fields)
        else:
            entries["deprecation"] = tx.put_dag(
                root=literal(tx, "advisory, not an eligibility gate")
            )
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    if fault == "old-table":
        with pytest.raises(ValueError):
            table_request(indexed, commit=basis)
        return
    got = table_request(indexed, commit=basis, implementation_override="double-b")
    assert got.reused.attempt == selected.attempt
    if fault == "old-decision":
        with pytest.raises(ValueError):
            app.policy.inspect_request(
                path,
                commit=got.recorded.commit,
                request=got.recorded.request,
                decision_name=got.decision.name,
            )


@pytest.mark.parametrize(
    "field", ["request", "attempt", "result", "completion", "validation"]
)
def test_partial_producer_authority_swaps_reject_without_forging_requested_binding(
    indexed, field
):
    path, definition, _, selected, table = indexed
    with d.Repository(path) as repo, repo.write() as tx:
        replacement = (
            literal(tx, definition.commit.bytes)
            if field == "completion"
            else tx.put_subdag(definition.dag)
        )
        forged = clone(
            tx,
            selected.dag,
            fields={field: replacement},
            root=replacement if field == "result" else None,
        )
        row = table.entries[0]
        rowdag = clone(
            tx,
            row.dag,
            fields={"selection": tx.put_subdag(forged)},
            root=tx.put_subdag(forged),
        )
        rows = nested(tx, table.dag, "entries")
        rows = clone(tx, rows, fields={row.key: tx.put_subdag(rowdag)})
        entries = tree(tx, table.commit)
        entries[selected.slot] = forged
        entries["table"] = clone(tx, table.dag, fields={"entries": tx.put_subdag(rows)})
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, TypeError)):
        table_request(indexed, commit=basis, implementation_override="double-b")
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("field", ["attempt", "result", "role"])
def test_W_partial_authority_rejects(indexed, field):
    path = indexed[0]
    got = table_request(indexed, implementation_override="double-b")
    with d.Repository(path) as repo, repo.write() as tx:
        changed = (
            literal(tx, "wrong") if field == "role" else tx.put_subdag(indexed[1].dag)
        )
        bad = clone(
            tx,
            got.reused.dag,
            fields={field: changed},
            root=changed if field == "result" else None,
        )
        entries = tree(tx, got.reused.commit)
        entries["reuse-" + got.recorded.request_id] = bad
        commit = tx.put_commit(tx.put_tree(entries), parents=(got.recorded.commit,))
    with pytest.raises(ValueError):
        inspect_request(path, got, satisfaction_commit=commit)


@pytest.mark.parametrize("field", ["table", "entry", "selection"])
def test_Di_consumed_links_recomputed(indexed, field):
    path = indexed[0]
    got = table_request(indexed, implementation_override="double-b")
    with d.Repository(path) as repo, repo.write() as tx:
        bad = clone(tx, got.decision.dag, fields={field: tx.put_subdag(indexed[1].dag)})
        entries = tree(tx, got.decision.commit)
        entries[got.decision.name] = bad
        commit = tx.put_commit(tx.put_tree(entries), parents=(got.decision.base,))
    with pytest.raises(ValueError, match="claims differ"):
        app.inspect_decision(path, commit=commit, decision_name=got.decision.name)


@pytest.mark.parametrize("present", [False, True])
def test_well_shaped_wrong_intent_is_not_absence(indexed, present):
    path, _, empty_table, _, table = indexed
    base = table if present else empty_table
    with d.Repository(path) as repo, repo.write() as tx:
        uri = literal(tx, d.Datum.uri("urn:wrong"))
        fields = dict(tx.get_dag(base.dag).bindings)
        fields["intent"] = uri
        entries = tree(tx, base.commit)
        entries["table"] = tx.put_dag(root=uri, bindings=fields)
        bad = tx.put_commit(tx.put_tree(entries), parents=(base.commit,))
    with pytest.raises(
        ValueError, match="PUBLIC successful selection" if present else "intent scope"
    ):
        table_request(
            indexed, commit=bad, reuse_ref="satisfaction" if present else None
        )
    with pytest.raises(ValueError):
        app.remove_entry(
            path, commit=bad, table_name="table", inputs=indexed[3].inputs, ref="bad"
        )


@pytest.mark.parametrize("field", ["binding", "inputs", "intent_uri"])
def test_public_exact_preparation_return_dimensions_checked(
    indexed, monkeypatch, field
):
    original = app.ex.prepare_exchange

    def changed(*a, **k):
        got = original(*a, **k)
        if k["request"] is not None:
            return replace(
                got, **{field: "urn:wrong" if field == "intent_uri" else indexed[1].dag}
            )
        return got

    monkeypatch.setattr(app.ex, "prepare_exchange", changed)
    with pytest.raises(ValueError, match="prepared Q differs"):
        table_request(indexed, implementation_override="double-b")
    with d.Repository(indexed[0]) as repo, repo.read() as tx:
        assert tx.get_ref("submission")
        with pytest.raises(d.NotFoundError):
            tx.get_ref("satisfaction")


def test_direct_author_rejects_existing_W_name(indexed):
    got = table_request(indexed)
    before = (indexed[0] / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="tree name already exists"):
        app._publish_reuse(
            indexed[0],
            replace(got.recorded, commit=got.reused.commit),
            indexed[3],
            "other",
            0,
        )
    assert_file_unchanged(indexed[0] / "data.mdb", before)


@pytest.mark.parametrize("fault", ["typed", "witness"])
def test_exact_full_inputs_not_equal_scalar(indexed, fault):
    path, _, _, selected, table = indexed
    with d.Repository(path) as repo, repo.write() as tx:
        original = tx.get_dag(selected.inputs)
        fields = dict(original.bindings)
        if fault == "typed":
            # Change a declared scalar's type, retaining other witnesses.
            fields["factor"] = literal(tx, 2.0)
        else:
            fields["producer"] = tx.put_subdag(indexed[1].dag)
        changed = tx.put_dag(root=original.root, bindings=fields)
        entries = tree(tx, table.commit)
        entries["altered"] = changed
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    with pytest.raises(ValueError, match="matching table entry"):
        table_request(
            indexed, commit=basis, inputs_name="altered", override="reuse-selected"
        )
