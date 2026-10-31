"""Strict ordinary advisory L and actual-D.base versus explicit knowledge, no jobs."""

import importlib.util
from pathlib import Path
import subprocess
import sys

import daggerml as d
from daggerml import local, transfer
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
from test_records_hypothesis import run_driver
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged

paths = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    import implementation_supersession as app
finally:
    sys.path[:] = paths


@pytest.fixture
def state(tmp_path):
    path = tmp_path / "A"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        entries = {
            label: local.put_local_binding(
                tx, source=source, interpreter=sys.executable, timeout_ms=10000
            )
            for label, source in (
                ("binding-a", b"print('A')"),
                ("binding-b", b"print('B')"),
            )
        }
        entries["inputs"] = tx.put_dag(root=literal(tx, -3))
        entries["evidence"] = tx.put_dag(root=literal(tx, "research assertion"))
        basis = tx.put_commit(tx.put_tree(entries))
        tx.create_ref("main", basis)
    definition = app.policy.define(
        path,
        commit=basis,
        intent_name="intent",
        intent_uri="urn:example:double",
        default="reuse-by-default",
        implementations=(
            ("a", "binding-a", "selected-a"),
            ("b", "binding-b", "selected-b"),
        ),
        default_implementation="a",
        ref="definition",
    )
    return path, definition


def author(state, **changes):
    path, definition = state
    args = dict(
        commit=definition.commit,
        intent_name="intent",
        slot="supersession",
        predecessor_label="a",
        successor_label="b",
        reason="correctness-fix",
        evidence_name="evidence",
        ref="declared",
    )
    args.update(changes)
    return app.record_supersession(path, **args)


def inspect(state, commit):
    return app.inspect_supersession(
        state[0], commit=commit, intent_name="intent", slot="supersession"
    )


def request(state, commit, **changes):
    args = dict(
        commit=commit,
        intent_name="intent",
        inputs_name="inputs",
        decision_name="decision",
        decision_ref="decision",
        submission_ref="submission",
    )
    args.update(changes)
    return app.policy.record_policy_request(state[0], **args)


def context(state, got, **changes):
    args = dict(
        commit=got.recorded.commit,
        request=got.recorded.request,
        decision_name=got.decision.name,
        slot="supersession",
    )
    args.update(changes)
    return app.inspect_request_context(state[0], **args)


def test_advisory_only_then_separate_promotion_all_parent_basis_transfer(
    state, tmp_path, monkeypatch
):
    path, definition = state
    old = typed_oracle(path, (definition.commit,))
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("no dispatch"))
        assert inspect(state, definition.commit) is None
        declared = author(state)
        assert inspect(state, declared.commit) == declared
        promoted = app.policy.update_default(
            path,
            commit=declared.commit,
            intent_name="intent",
            default_implementation="b",
            ref="promoted",
        )
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, definition.commit)
        entries[declared.slot] = declared.dag
        assert tree(tx, declared.commit) == entries
        assert tx.get_commit(declared.commit).parents == (definition.commit,)
        assert scalar(tx, declared.dag, "basis") == definition.commit.bytes
        assert (
            nested(tx, declared.dag, "predecessor") == definition.implementations[0].dag
        )
        assert nested(tx, declared.dag, "evidence") == entries["evidence"]
        assert tx.get_dag(declared.dag).root == tx.lookup_node(
            declared.dag, "predecessor"
        )
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        # Basis may be reachable ONLY through second parent, not first-parent log.
        unrelated = tx.put_commit(
            tx.put_tree({"unrelated": tx.put_dag(root=literal(tx, 42))})
        )
        merged = tx.put_commit(
            tx.get_commit(promoted.commit).tree, parents=(unrelated, promoted.commit)
        )
        tx.update_ref("main", merged)
    assert (
        app.policy.inspect_definition(
            path, commit=declared.commit, intent_name="intent"
        ).default_implementation
        == "a"
    )
    assert inspect(state, merged).dag == declared.dag
    replica = tmp_path / "replica"
    with d.Repository(replica, create=True):
        pass
    transfer.import_commit(replica, transfer.export_commit(path, commit=merged))
    before = (replica / "data.mdb").read_bytes()
    assert inspect((replica, definition), merged).basis == definition.commit
    assert_file_unchanged(replica / "data.mdb", before)


@pytest.mark.parametrize("reason", app.REASONS)
def test_actual_D_base_not_submission_latest_or_explicit_sibling_knowledge(
    state, reason
):
    path, definition = state
    old = request(state, definition.commit)
    declared = author(state, reason=reason)
    got = context(state, old, knowledge_commit=declared.commit)
    assert got.decision == old.decision
    assert got.as_known_then.commit == old.decision.base == definition.commit
    assert got.as_known_then.relation == "no-recorded-declaration"
    assert got.explicit_knowledge.commit == declared.commit
    assert got.explicit_knowledge.relation == "predecessor"
    assert got.explicit_knowledge.declaration.reason == reason
    promoted = app.policy.update_default(
        path,
        commit=declared.commit,
        intent_name="intent",
        default_implementation="b",
        ref="promoted",
    )
    later = request(
        state,
        promoted.commit,
        decision_name="decision-b",
        decision_ref="decision-b",
        submission_ref="submission-b",
    )
    read = context(state, later)
    assert read.as_known_then.commit == promoted.commit
    assert (
        read.as_known_then.relation == "successor" and read.explicit_knowledge is None
    )
    assert read.as_known_then.declaration.definition.default_implementation == "a"
    # Move latest to another branch; pinned contexts remain identical.
    with d.Repository(path) as repo, repo.write() as tx:
        tx.update_ref("main", later.recorded.commit)
    assert context(state, old, knowledge_commit=declared.commit) == got
    for q in (None, later.recorded.request):
        before = (path / "data.mdb").read_bytes()
        with pytest.raises((TypeError, ValueError)):
            context(state, old, request=q)
        assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("field", app.FIELDS)
@pytest.mark.parametrize("fault", ["missing", "wrong-type", "wrong-node"])
def test_present_malformed_L_never_absence(state, field, fault):
    path, definition = state
    declared = author(state)
    with d.Repository(path) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(declared.dag).bindings)
        root = tx.get_dag(declared.dag).root
        if fault == "missing":
            fields.pop(field)
        else:
            fields[field] = (
                (
                    literal(tx, b"not-a-subdag")
                    if field
                    in ("intent-definition", "predecessor", "successor", "evidence")
                    else tx.put_subdag(tree(tx, definition.commit)["evidence"])
                )
                if fault == "wrong-node"
                else literal(tx, True)
            )
            if tx.lookup_node(declared.dag, field) == root:
                root = fields[field]
        altered = tx.put_dag(root=root, bindings=fields)
        entries = tree(tx, declared.commit)
        entries[declared.slot] = altered
        forged = tx.put_commit(tx.put_tree(entries), parents=(declared.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((TypeError, ValueError)):
        inspect(state, forged)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "fault",
    [
        "role",
        "reason",
        "same",
        "unknown",
        "basis-length",
        "unretained",
        "definition",
        "predecessor",
        "successor",
        "intent",
        "root",
        "extra",
        "current-menu",
        "current-uri",
        "tree-drift",
    ],
)
def test_typed_complete_L_false_claims_endpoint_capture_scope_ancestry(state, fault):
    path, definition = state
    declared = author(state)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, declared.commit)
        fields, root = {}, None
        if fault in ("role", "reason"):
            fields[fault] = literal(tx, "unknown")
        elif fault in ("same", "unknown"):
            fields["successor-label"] = literal(
                tx, "a" if fault == "same" else "unknown"
            )
        elif fault == "basis-length":
            fields["basis"] = literal(tx, b"short")
        elif fault == "unretained":
            unrelated = tx.put_commit(tx.get_commit(definition.commit).tree)
            fields["basis"] = literal(tx, unrelated.bytes)
        elif fault in ("definition", "predecessor", "successor"):
            fields["intent-definition" if fault == "definition" else fault] = (
                tx.put_subdag(entries["evidence"])
            )
            if fault == "predecessor":
                root = fields[fault]
        elif fault == "intent":
            fields["intent-name"] = literal(tx, "other")
        elif fault == "root":
            root = literal(tx, "wrong")
        elif fault == "extra":
            fields["extra"] = literal(tx, "wrong")
        elif fault in ("current-menu", "current-uri"):
            edits = (
                {"intent": literal(tx, d.Datum.uri("urn:other"))}
                if fault == "current-uri"
                else {"implementations": tx.put_subdag(entries["evidence"])}
            )
            entries["intent"] = clone(
                tx, definition.dag, fields=edits, root=edits.get("intent")
            )
        else:
            entries["binding-a"] = entries["binding-b"]
        entries[declared.slot] = clone(tx, declared.dag, fields=fields, root=root)
        forged = tx.put_commit(tx.put_tree(entries), parents=(declared.commit,))
    with pytest.raises((TypeError, ValueError)):
        inspect(state, forged)


@pytest.mark.parametrize(
    "changes",
    [
        {"reason": "unknown"},
        {"reason": None},
        {"predecessor_label": "unknown"},
        {"successor_label": "a"},
        {"successor_label": "bad/name"},
        {"ref": "bad/name"},
        {"slot": "binding-a"},
        {"slot": "evidence"},
        {"evidence_name": "absent"},
        {"slot": None},
        {"map_size": True},
        {"map_size": 1},
        {"map_size": -1},
        {"map_size": sys.maxsize + 1},
    ],
)
def test_authoring_invalid_parameters_no_puts(state, changes):
    before = (state[0] / "data.mdb").read_bytes()
    with pytest.raises((TypeError, ValueError, KeyError)):
        author(state, **changes)
    assert_file_unchanged(state[0] / "data.mdb", before)


def test_slot_already_present_and_wrong_scope_even_absent_K(state):
    path, definition = state
    declared = author(state)
    with pytest.raises(ValueError, match="absent"):
        author(state, commit=declared.commit, ref="other")
    old = request(state, definition.commit)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, definition.commit)
        node = literal(tx, d.Datum.uri("urn:other"))
        entries["intent"] = clone(
            tx, definition.dag, fields={"intent": node}, root=node
        )
        incompatible = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    with pytest.raises(ValueError, match="drift"):
        context(state, old, knowledge_commit=incompatible)
    with pytest.raises(TypeError):
        context(state, old, knowledge_commit="latest")


@pytest.mark.parametrize("present", [False, True])
@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_complete_all_parent_composite_closure_even_absent_L(
    state, exchange_runtime, present, damage
):
    path, definition = state
    with d.Repository(path) as repo, repo.write() as tx:
        leaf = tx.put_datum(b"composite-only")
        raw = tx.get_record("datum", leaf)
        composite = tx.put_datum(d.Datum.list([tx.put_datum(d.Datum.list([leaf]))]))
        side = tx.put_commit(
            tx.put_tree({"composite": tx.put_dag(root=tx.put_literal(composite))})
        )
        basis = tx.put_commit(
            tx.get_commit(definition.commit).tree, parents=(definition.commit, side)
        )
    selected = author(state, commit=basis).commit if present else basis
    if damage == "missing":
        run_driver("raw-delete", str(path), "objects/datums/" + str(leaf))
    else:
        run_driver(
            "raw-write", str(path), "objects/datums/" + str(leaf), data=raw[:-1] + b"X"
        )
    before = (path / "data.mdb").read_bytes()
    for invoke in (
        lambda: inspect(state, selected),
        lambda: author(state, commit=selected, slot="another", ref="another"),
    ):
        with pytest.raises(d.DmlError):
            invoke()
    assert_file_unchanged(path / "data.mdb", before)


def test_valid_alternative_menu_capture_drift_with_and_without_L(state):
    path, definition = state
    declared = author(state)
    old = request(state, definition.commit)
    for basis in (definition.commit, declared.commit):
        with d.Repository(path) as repo, repo.write() as tx:
            entries = tree(tx, basis)
            new_binding = local.put_local_binding(
                tx,
                source=b"print('alternative')",
                interpreter=sys.executable,
                timeout_ms=10000,
            )
            entries["binding-a"] = new_binding
            choice = clone(
                tx,
                definition.implementations[0].dag,
                fields={"binding": tx.put_subdag(new_binding)},
                root=tx.put_subdag(new_binding),
            )
            menu = clone(tx, definition.menu, fields={"a": tx.put_subdag(choice)})
            entries["intent"] = clone(
                tx, definition.dag, fields={"implementations": tx.put_subdag(menu)}
            )
            changed = tx.put_commit(tx.put_tree(entries), parents=(basis,))
        app.policy.inspect_definition(
            path, commit=changed, intent_name="intent"
        )  # VALID, not malformed setup.
        with pytest.raises(ValueError, match="drift"):
            context(state, old, knowledge_commit=changed)
