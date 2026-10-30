"""Focused captured menu/default, separate reuse choice and pinned own-Q authority."""

import importlib.util
from pathlib import Path
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import (
    assert_file_unchanged,
    assert_recorded,
    track_typed_puts,
)
from test_composed_execution import producer, execute
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
from test_explicit_reuse import double
from test_reuse_selection import expected_file, select

spec = importlib.util.spec_from_file_location(
    "implementation_example", ROOT / "examples/implementation_selection.py"
)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
paths = list(sys.path)
aliases = {
    name: sys.modules.get(name) for name in ("reuse_selection", "explicit_reuse")
}
try:
    sys.path.insert(0, str(ROOT / "examples"))
    spec.loader.exec_module(app)
finally:
    sys.path[:] = paths
    for name, old in aliases.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


@pytest.fixture
def menu(double):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, double[2][2].commit)
        entries["double-a-binding"] = entries.pop("double-binding")
        entries["double-b-binding"] = local.put_local_binding(
            tx,
            source=scalar(tx, entries["double-a-binding"], "source")
            + b"\n# Distinct captured implementation B\n",
            interpreter=sys.executable,
            timeout_ms=10000,
        )
        basis = tx.put_commit(tx.put_tree(entries), parents=(double[2][2].commit,))
    return double, basis


def define(menu, **changes):
    double, basis = menu
    arguments = dict(
        commit=basis,
        intent_name="double-intent",
        intent_uri="urn:example:double",
        default="reuse-by-default",
        implementations=(
            ("double-a", "double-a-binding", "selected-double-a"),
            ("double-b", "double-b-binding", "selected-double-b"),
        ),
        default_implementation="double-a",
        ref="intent-default",
    )
    arguments.update(changes)
    return app.define(double[0][0], **arguments)


def request(path, commit, **changes):
    arguments = dict(
        commit=commit,
        intent_name="double-intent",
        inputs_name="double-inputs",
        decision_name="decision-one",
        decision_ref="decision-one",
        submission_ref="policy-submission",
    )
    arguments.update(changes)
    return app.record_policy_request(path, **arguments)


def inspect(path, got):
    return app.inspect_request(
        path,
        commit=got.recorded.commit,
        request=got.recorded.request,
        decision_name=got.decision.name,
        satisfaction_commit=None if got.reused is None else got.reused.commit,
    )


def selected_a(menu, expected_file):
    double, basis = menu
    path = double[0][0]
    return app.selection.select(
        path,
        commit=basis,
        slot="selected-double-a",
        binding_name="double-a-binding",
        inputs_name="double-inputs",
        intent_uri="urn:example:double",
        packet=double[2][0],
        expected_file=expected_file,
        ref="selection-a",
    )


def test_definition_update_exact_capture_only_default_siblings_old_bytes(
    menu, monkeypatch
):
    double, basis = menu
    path = double[0][0]
    old = typed_oracle(path, (basis, double[0][1]))
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("no dispatch"))
        got = define(menu)
        assert (
            app.inspect_definition(path, commit=got.commit, intent_name=got.name) == got
        )
        changed = app.update_default(
            path,
            commit=got.commit,
            intent_name=got.name,
            default_implementation="double-b",
            ref="default-b",
        )
    assert got.implementations == changed.implementations and got.menu == changed.menu
    assert got.intent_uri == changed.intent_uri and got.default == changed.default
    with d.Repository(path) as repository, repository.write() as tx:
        keep = tx.put_commit(tx.get_commit(got.commit).tree, parents=(got.commit,))
        tx.update_ref("intent-default", changed.commit)
    with d.Repository(path) as repository, repository.read() as tx:
        assert (
            tx.get_commit(keep).parents
            == tx.get_commit(changed.commit).parents
            == (got.commit,)
        )
        assert tx.get_commit(got.commit).parents == (basis,)
        entries = tree(tx, basis)
        entries[got.name] = got.dag
        assert tree(tx, got.commit) == entries
        entries[got.name] = changed.dag
        assert tree(tx, changed.commit) == entries
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        assert set(tx.get_dag(got.dag).bindings) == {
            "role",
            "intent",
            "reuse-default",
            "implementations",
            "default-implementation",
        }
        assert tx.get_dag(got.dag).root == tx.lookup_node(got.dag, "intent")
        assert tx.get_dag(got.menu).root == tx.lookup_node(got.menu, "role")
        assert len({c.binding for c in got.implementations}) == 2
        for c in got.implementations:
            assert tx.get_dag(c.dag).root == tx.lookup_node(c.dag, "binding")
            assert nested(tx, c.dag, "binding") == entries[c.binding_name] == c.binding
    assert (
        app.inspect_definition(path, commit=keep, intent_name=got.name).dag == got.dag
    )


@pytest.mark.parametrize(
    "default,label,override,reason",
    [
        ("reuse-by-default", "default", "default", "default-no-selection"),
        ("reuse-by-default", "double-b", "default", "default-no-selection"),
        ("reuse-by-default", "double-a", "fresh", "override-fresh"),
        ("execute-by-default", "double-b", "default", "default-execution"),
    ],
)
def test_independent_implementation_then_reuse_pending_own_Q_no_T_adoption(
    menu, monkeypatch, default, label, override, reason
):
    path = menu[0][0][0]
    definition = define(menu, default=default)
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("no dispatch"))
        got = request(
            path, definition.commit, implementation_override=label, override=override
        )
        assert inspect(path, got) == got.decision
    chosen = "double-a" if label == "default" else label
    assert got.decision.implementation.label == chosen
    assert got.decision.implementation_reason == (
        "default-implementation" if label == "default" else "explicit-implementation"
    )
    assert got.decision.reason == reason and got.reused is None
    assert_recorded(path, got.recorded)
    with d.Repository(path) as repository, repository.read() as tx:
        assert tx.get_commit(got.decision.commit).parents == (definition.commit,)
        entries = tree(tx, definition.commit)
        entries[got.decision.name] = got.decision.dag
        assert tree(tx, got.decision.commit) == entries
        assert (
            nested(tx, got.decision.dag, "implementation-choice")
            == got.decision.implementation.dag
        )
        assert nested(tx, got.recorded.request, "binding") == got.decision.binding
        assert all(
            slot not in tree(tx, got.recorded.commit)
            for slot in ("selected-double-a", "selected-double-b")
        )


def test_own_unselected_A_valid_S_not_consulted_B_absence_fresh_cross_binding_forgery_rejects(
    menu, expected_file, monkeypatch
):
    double, basis = menu
    path = double[0][0]
    definition = define(menu)
    chosen = app.selection.select(
        path,
        commit=definition.commit,
        slot="selected-double-a",
        binding_name="double-a-binding",
        inputs_name="double-inputs",
        intent_uri="urn:example:double",
        packet=double[2][0],
        expected_file=expected_file,
        ref="selection-a",
    )
    changed = app.update_default(
        path,
        commit=chosen.commit,
        intent_name="double-intent",
        default_implementation="double-b",
        ref="default-b",
    )
    inspecting = app.selection.inspect
    with monkeypatch.context() as guard:
        guard.setattr(
            app.selection,
            "inspect",
            lambda *a, **k: pytest.fail("unselected A S not consulted"),
        )
        pending = request(path, changed.commit)
        assert (
            pending.decision.reason == "default-no-selection"
            and inspect(path, pending) == pending.decision
        )
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, changed.commit)
        entries["selected-double-b"] = chosen.dag
        forged = tx.put_commit(tx.put_tree(entries), parents=(changed.commit,))
    before = (path / "data.mdb").read_bytes()
    with track_typed_puts(path, typed_oracle(path, (forged,))) as puts:
        with pytest.raises(ValueError, match="full inputs differ"):
            request(
                path,
                forged,
                decision_name="decision-forged",
                decision_ref="decision-forged",
                submission_ref="forged-q",
                reuse_ref="no-cross-binding",
            )
    assert not puts
    assert_file_unchanged(path / "data.mdb", before)
    hit = request(
        path,
        changed.commit,
        implementation_override="double-a",
        decision_name="decision-hit",
        decision_ref="decision-hit",
        submission_ref="hit-q",
        reuse_ref="hit-w",
    )
    assert (
        hit.decision.implementation_reason == "explicit-implementation"
        and hit.decision.reason == "default-selection"
    )
    assert (
        hit.reused.attempt == chosen.attempt and hit.recorded.request != chosen.request
    )
    assert inspect(path, hit) == hit.decision
    with d.Repository(path) as repository, repository.read() as tx:
        assert nested(tx, hit.reused.dag, "request") == hit.recorded.request
        assert nested(tx, chosen.attempt, "request") == chosen.request
    copied = path.parent / "implementation-transferred"
    with d.Repository(copied, create=True):
        pass
    transfer.import_commit(
        copied, transfer.export_commit(path, commit=hit.reused.commit)
    )
    for source in (double[2][0], expected_file, double[2][4]):
        source.rename(source.with_name(source.name + ".unavailable"))
    before = (copied / "data.mdb").read_bytes()
    assert inspect(copied, hit) == hit.decision
    assert_file_unchanged(copied / "data.mdb", before)


@pytest.mark.parametrize(
    "fault",
    [
        "unknown",
        "none",
        "inputs-alias",
        "decision-alias",
        "occurrence-name",
        "ref-alias",
        "reuse-ref",
        "missing-reuse",
    ],
)
def test_invalid_request_names_overrides_refs_no_D_Q(menu, fault):
    path = menu[0][0][0]
    definition = define(menu)
    changes = {
        "unknown": dict(implementation_override="unknown"),
        "none": dict(implementation_override=None),
        "inputs-alias": dict(inputs_name="selected-double-b"),
        "decision-alias": dict(decision_name="double-a-binding"),
        "occurrence-name": dict(decision_name="request-q-" + "a" * 32),
        "ref-alias": dict(submission_ref="decision-one"),
        "reuse-ref": dict(reuse_ref="unneeded"),
        "missing-reuse": dict(override="reuse-selected"),
    }[fault]
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        request(path, definition.commit, **changes)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "level,field",
    [
        ("definition", "role"),
        ("definition", "intent"),
        ("definition", "reuse-default"),
        ("definition", "implementations"),
        ("definition", "default-implementation"),
        ("menu", "role"),
        ("menu", "double-a"),
        ("menu", "double-b"),
        ("choice", "role"),
        ("choice", "binding"),
        ("choice", "binding-name"),
        ("choice", "selection-slot"),
    ],
)
@pytest.mark.parametrize("fault", ["missing", "wrong-type", "subdag"])
def test_strict_new_definition_menu_choice_all_fields_before_D_Q(
    menu, level, field, fault
):
    path = menu[0][0][0]
    definition = define(menu)
    with d.Repository(path) as repository, repository.write() as tx:
        original = (
            definition.dag
            if level == "definition"
            else (
                definition.menu
                if level == "menu"
                else definition.implementations[0].dag
            )
        )
        fields = dict(tx.get_dag(original).bindings)
        root = tx.get_dag(original).root
        if fault == "missing":
            fields.pop(field)
        else:
            fields[field] = (
                tx.put_subdag(menu[0][2][2].result)
                if fault == "subdag"
                else literal(tx, True)
            )
            if tx.lookup_node(original, field) == root:
                root = fields[field]
        forged = tx.put_dag(root=root, bindings=fields)
        if level == "choice":
            forged = clone(
                tx, definition.menu, fields={"double-a": tx.put_subdag(forged)}
            )
        if level != "definition":
            forged = clone(
                tx, definition.dag, fields={"implementations": tx.put_subdag(forged)}
            )
        entries = tree(tx, definition.commit)
        entries[definition.name] = forged
        basis = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        request(path, basis)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "fault",
    [
        "binding-drift",
        "alias-slot",
        "same-binding",
        "unknown-default",
        "menu-role",
        "reserved-label",
        "root",
        "extra",
    ],
)
def test_typed_complete_crosslinks_menu_default_strict_not_fallback(menu, fault):
    path = menu[0][0][0]
    definition = define(menu)
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, definition.commit)
        dag = definition.dag
        a, b = definition.implementations
        if fault == "binding-drift":
            entries[a.binding_name] = b.binding
        elif fault in ("alias-slot", "same-binding"):
            values = (
                {"selection-slot": literal(tx, a.selection_slot)}
                if fault == "alias-slot"
                else {"binding": tx.put_subdag(a.binding)}
            )
            altered = clone(tx, b.dag, fields=values, root=values.get("binding"))
            menu_id = clone(
                tx, definition.menu, fields={b.label: tx.put_subdag(altered)}
            )
            dag = clone(tx, dag, fields={"implementations": tx.put_subdag(menu_id)})
        elif fault == "unknown-default":
            dag = clone(
                tx, dag, fields={"default-implementation": literal(tx, "unknown")}
            )
        elif fault in ("menu-role", "reserved-label"):
            fields = dict(tx.get_dag(definition.menu).bindings)
            if fault == "menu-role":
                fields["role"] = literal(tx, "unknown")
            else:
                fields["default"] = fields.pop(a.label)
            menu_id = tx.put_dag(root=fields["role"], bindings=fields)
            dag = clone(tx, dag, fields={"implementations": tx.put_subdag(menu_id)})
        else:
            node = literal(tx, "wrong")
            dag = clone(
                tx,
                dag,
                fields={"extra": node} if fault == "extra" else {},
                root=node if fault == "root" else None,
            )
        entries[definition.name] = dag
        basis = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    transfer.export_commit(path, commit=basis)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        request(path, basis)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "field",
    [
        "role",
        "intent-definition",
        "implementation-choice",
        "binding",
        "inputs",
        "intent-name",
        "binding-name",
        "inputs-name",
        "selection-slot",
        "implementation",
        "implementation-override",
        "implementation-reason",
        "override",
        "action",
        "reason",
        "root",
        "extra",
    ],
)
def test_D_partial_forged_claims_recomputed_actual_parent(menu, field):
    path = menu[0][0][0]
    definition = define(menu)
    got = request(path, definition.commit)
    with d.Repository(path) as repository, repository.write() as tx:
        node = (
            tx.put_subdag(menu[0][2][2].result)
            if field
            in ("intent-definition", "implementation-choice", "binding", "inputs")
            else literal(tx, "unknown")
        )
        forged = clone(
            tx,
            got.decision.dag,
            fields={} if field == "root" else {field: node},
            root=node if field in ("root", "intent-definition") else None,
        )
        entries = tree(tx, definition.commit)
        entries[got.decision.name] = forged
        cdec = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        app.inspect_decision(path, commit=cdec, decision_name=got.decision.name)
    assert_file_unchanged(path / "data.mdb", before)


def test_reader_exact_non_None_own_Q_old_Q_not_authority_and_pinned_after_ref_move(
    menu,
):
    path = menu[0][0][0]
    definition = define(menu)
    got = request(path, definition.commit)
    app.update_default(
        path,
        commit=got.recorded.commit,
        intent_name=definition.name,
        default_implementation="double-b",
        ref="latest",
    )
    before = (path / "data.mdb").read_bytes()
    for q in (None, menu[0][2][2].request):
        with pytest.raises((TypeError, ValueError)):
            app.inspect_request(
                path,
                commit=got.recorded.commit,
                request=q,
                decision_name=got.decision.name,
            )
    assert_file_unchanged(path / "data.mdb", before)
    assert inspect(path, got) == got.decision
