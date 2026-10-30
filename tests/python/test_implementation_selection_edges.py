"""New helper matrix, response authority, closure and finite offline mode controls."""

from dataclasses import replace
import json
from pathlib import Path
import runpy
import shutil
import sys

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged, track_typed_puts
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
from test_implementation_selection import app, menu, define, request, inspect
from test_records_hypothesis import run_driver
from test_reuse_selection import expected_file


@pytest.fixture
def selected(menu, expected_file):
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
        ref="selected-a",
    )
    return definition, chosen


@pytest.mark.parametrize("default", app.MODES)
@pytest.mark.parametrize("override", app.OVERRIDES)
@pytest.mark.parametrize("label", ["default", "double-a", "double-b"])
def test_complete_independent_choice_reuse_table_with_selection(
    menu, selected, default, override, label
):
    path = menu[0][0][0]
    definition, chosen = selected
    basis = chosen.commit
    if default != definition.default:
        with d.Repository(path) as repository, repository.write() as tx:
            entries = tree(tx, basis)
            entries[definition.name] = clone(
                tx, definition.dag, fields={"reuse-default": literal(tx, default)}
            )
            basis = tx.put_commit(tx.put_tree(entries), parents=(basis,))
    use_a = label != "double-b"
    reuse = use_a and (
        override == "reuse-selected"
        or override == "default"
        and default == "reuse-by-default"
    )
    if override == "reuse-selected" and not use_a:
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match="requires selection"):
            request(
                path,
                basis,
                implementation_override=label,
                override=override,
                reuse_ref="reused",
            )
        assert_file_unchanged(path / "data.mdb", before)
        return
    got = request(
        path,
        basis,
        implementation_override=label,
        override=override,
        reuse_ref="reused" if reuse else None,
    )
    assert (got.reused is not None) == reuse
    assert got.decision.reason == (
        "override-selected-reuse"
        if override == "reuse-selected"
        else (
            "override-fresh"
            if override == "fresh"
            else (
                "default-execution"
                if default == "execute-by-default"
                else "default-selection" if use_a else "default-no-selection"
            )
        )
    )
    assert inspect(path, got) == got.decision
    with d.Repository(path) as repository, repository.read() as tx:
        assert tree(tx, got.recorded.commit)["selected-double-a"] == chosen.dag
        assert "selected-double-b" not in tree(tx, got.recorded.commit)


@pytest.mark.parametrize(
    "path_kind,fault",
    [
        (path_kind, fault)
        for path_kind in ("fresh", "reuse")
        for fault in (
            "old-Q",
            "None-Q",
            "commit",
            "request-id",
            "ref",
            "binding-name",
            "inputs-name",
            "dimensions",
            "attempt",
            "W-commit",
            "W-dag",
        )
        if path_kind == "reuse" or fault not in ("attempt", "W-commit", "W-dag")
    ],
)
def test_actual_returned_response_not_self_authority_late_error_retains_readable_publication(
    menu, selected, monkeypatch, path_kind, fault
):
    path = menu[0][0][0]
    definition, chosen = selected
    owning = (
        ex.record_exchange_request
        if path_kind == "fresh"
        else app.selection.reuse_selected
    )
    actual = []

    def changed(*a, **k):
        got = owning(*a, **k)
        actual.append(got)
        recorded = got if path_kind == "fresh" else got.recorded
        changes = {
            "old-Q": dict(request=chosen.request),
            "None-Q": dict(request=None),
            "commit": dict(commit=definition.commit),
            "request-id": dict(request_id="q-" + "0" * 32),
            "ref": dict(ref="wrong"),
            "binding-name": dict(binding_name="double-b-binding"),
            "inputs-name": dict(inputs_name="wrong"),
            "dimensions": dict(inputs=chosen.result),
        }
        if fault in changes:
            recorded = replace(recorded, **changes[fault])
            return recorded if path_kind == "fresh" else replace(got, recorded=recorded)
        return replace(
            got,
            **{
                "attempt": dict(attempt=chosen.request),
                "W-commit": dict(commit=recorded.commit),
                "W-dag": dict(dag=chosen.dag),
            }[fault],
        )

    with monkeypatch.context() as guard:
        guard.setattr(
            ex if path_kind == "fresh" else app.selection,
            "record_exchange_request" if path_kind == "fresh" else "reuse_selected",
            changed,
        )
        with pytest.raises((ValueError, KeyError, TypeError, d.DmlError)):
            request(
                path,
                chosen.commit,
                override="fresh" if path_kind == "fresh" else "default",
                reuse_ref=None if path_kind == "fresh" else "reused",
            )
    assert len(actual) == 1
    recorded = actual[0] if path_kind == "fresh" else actual[0].recorded
    decision = app.inspect_request(
        path,
        commit=recorded.commit,
        request=recorded.request,
        decision_name="decision-one",
        satisfaction_commit=None if path_kind == "fresh" else actual[0].commit,
    )
    assert decision.reason == (
        "override-fresh" if path_kind == "fresh" else "default-selection"
    )
    with d.Repository(path) as repository, repository.read() as tx:
        assert tx.get_ref("policy-submission") == recorded.commit
        if path_kind == "reuse":
            assert tx.get_ref("reused") == actual[0].commit


@pytest.mark.parametrize("damage", ["missing", "corrupt", "oversized"])
def test_declared_fresh_ignores_unused_S_framing_NOT_all_parent_composite_native_closure(
    menu, damage
):
    path = menu[0][0][0]
    definition = define(menu)
    with d.Repository(path) as repository, repository.write() as tx:
        leaf = tx.put_datum(
            b"x" * (4 * 1024 * 1024 + 1) if damage == "oversized" else b"composite-only"
        )
        raw = tx.get_record("datum", leaf)
        datum = tx.put_datum(d.Datum.list([leaf]))
        entries = tree(tx, definition.commit)
        entries["selected-double-a"] = tx.put_dag(root=tx.put_literal(datum))
        nonfirst = tx.put_commit(tx.put_tree(entries))
        basis = tx.put_commit(
            tx.get_commit(definition.commit).tree, parents=(definition.commit, nonfirst)
        )
    if damage == "missing":
        run_driver("raw-delete", str(path), "objects/datums/" + str(leaf))
    elif damage == "corrupt":
        run_driver(
            "raw-write", str(path), "objects/datums/" + str(leaf), data=raw[:-1] + b"X"
        )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((d.DmlError, transfer.TransferError)):
        request(path, basis, override="fresh")
    assert_file_unchanged(path / "data.mdb", before)


def test_unused_native_valid_bad_selection_and_other_valid_inputs_fresh_no_repair(
    menu, selected
):
    path = menu[0][0][0]
    definition, chosen = selected
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, chosen.commit)
        entries["selected-double-a"] = chosen.result
        inputs = clone(tx, chosen.inputs, fields={"factor": literal(tx, 3)})
        entries["double-inputs"] = inputs
        basis = tx.put_commit(tx.put_tree(entries), parents=(chosen.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        request(path, basis, reuse_ref="bad")
    assert_file_unchanged(path / "data.mdb", before)
    fresh = request(path, basis, override="fresh")
    assert fresh.decision.inputs == inputs and inspect(path, fresh) == fresh.decision
    with d.Repository(path) as repository, repository.read() as tx:
        assert tree(tx, fresh.recorded.commit)["selected-double-a"] == chosen.result


@pytest.mark.parametrize("dimension", ["factor", "factor-type", "producer", "intent"])
def test_full_input_producer_witness_URI_selection_mismatch_no_D_Q(
    menu, selected, dimension
):
    path = menu[0][0][0]
    definition, chosen = selected
    alternate = (
        execute(path, menu[0][0][1], "other-producer")
        if dimension == "producer"
        else None
    )
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, chosen.commit)
        if dimension == "intent":
            node = literal(tx, d.Datum.uri("urn:example:other"))
            entries[definition.name] = clone(
                tx, definition.dag, fields={"intent": node}, root=node
            )
        else:
            fields = (
                {"producer": tx.put_subdag(alternate[2].completion.final_attempt)}
                if dimension == "producer"
                else {"factor": literal(tx, True if dimension == "factor-type" else 3)}
            )
            entries["double-inputs"] = clone(tx, chosen.inputs, fields=fields)
        basis = tx.put_commit(tx.put_tree(entries), parents=(chosen.commit,))
    before = (path / "data.mdb").read_bytes()
    with track_typed_puts(path, typed_oracle(path, (basis,))) as puts:
        with pytest.raises(ValueError, match="full inputs differ"):
            request(path, basis, reuse_ref="mismatch")
    assert not puts
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "change",
    [
        dict(intent_uri=None),
        dict(intent_uri="HTTP://Example.com"),
        dict(default="unknown"),
        dict(map_size=True),
        dict(map_size=1),
        dict(intent_name="bad/name"),
        dict(implementations=[]),
        dict(implementations=(("a", "double-a-binding"), ("b", "double-b-binding"))),
        dict(
            implementations=(
                ("default", "double-a-binding", "sa"),
                ("b", "double-b-binding", "sb"),
            )
        ),
        dict(
            implementations=(
                ("a", "double-a-binding", "sa"),
                ("a", "double-b-binding", "sb"),
            )
        ),
        dict(
            implementations=(
                ("a", "double-a-binding", "sa"),
                ("b", "double-a-binding", "sb"),
            )
        ),
        dict(default_implementation="unknown"),
    ],
)
def test_definition_invalid_api_inputs_no_batch(menu, change):
    path = menu[0][0][0]
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, TypeError)):
        define(menu, **change)
    assert_file_unchanged(path / "data.mdb", before)


def test_definition_existing_initial_slot_existing_selection_not_replaced(
    menu, selected
):
    path = menu[0][0][0]
    definition, chosen = selected
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="absent for define"):
        define(menu, commit=definition.commit)
    with pytest.raises(ValueError, match="selection slots must be absent"):
        define(menu, commit=chosen.commit, intent_name="other-intent", ref="other")
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["zero-parent", "two-parent", "extra", "preexisting"])
def test_reader_decision_one_parent_only_absent_D(menu, fault):
    path = menu[0][0][0]
    definition = define(menu)
    got = request(path, definition.commit)
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, got.decision.commit)
        if fault == "extra":
            entries["extra"] = menu[0][2][2].result
        parents = (
            ()
            if fault == "zero-parent"
            else (
                (definition.commit, menu[1])
                if fault == "two-parent"
                else (
                    (got.decision.commit,)
                    if fault == "preexisting"
                    else (definition.commit,)
                )
            )
        )
        forged = tx.put_commit(tx.put_tree(entries), parents=parents)
    with pytest.raises(ValueError):
        app.inspect_decision(path, commit=forged, decision_name=got.decision.name)


def test_decision_existing_name_submission_bad_parent_fresh_W_and_invalid_update(menu):
    path = menu[0][0][0]
    definition = define(menu)
    got = request(path, definition.commit)
    with pytest.raises(ValueError, match="already exists"):
        request(
            path, got.recorded.commit, decision_ref="other", submission_ref="other-q"
        )
    with pytest.raises(ValueError, match="fresh decision"):
        app.inspect_request(
            path,
            commit=got.recorded.commit,
            request=got.recorded.request,
            decision_name=got.decision.name,
            satisfaction_commit=got.recorded.commit,
        )
    with d.Repository(path) as repository, repository.write() as tx:
        forged = tx.put_commit(
            tx.get_commit(got.recorded.commit).tree,
            parents=(definition.commit, got.decision.commit),
        )
    with pytest.raises(ValueError, match="exact one decision parent"):
        app.inspect_request(
            path,
            commit=forged,
            request=got.recorded.request,
            decision_name=got.decision.name,
        )
    with pytest.raises(ValueError, match="default implementation"):
        app.update_default(
            path,
            commit=definition.commit,
            intent_name=definition.name,
            default_implementation="unknown",
            ref="bad",
        )


@pytest.mark.parametrize(
    "fault", ["own-Q", "attempt", "result", "role", "root", "extra", "parent", "tree"]
)
def test_original_four_field_W_against_actual_own_Q_selected_T_R(menu, selected, fault):
    path = menu[0][0][0]
    definition, chosen = selected
    got = request(path, chosen.commit, reuse_ref="reused")
    with d.Repository(path) as repository, repository.write() as tx:
        node = literal(tx, "wrong")
        fields = (
            {"request": tx.put_subdag(chosen.request)}
            if fault == "own-Q"
            else (
                {fault: tx.put_subdag(chosen.request)}
                if fault in ("attempt", "result")
                else {fault: node} if fault in ("role", "extra") else {}
            )
        )
        dag = clone(
            tx, got.reused.dag, fields=fields, root=node if fault == "root" else None
        )
        entries = tree(tx, got.recorded.commit)
        entries["reuse-" + got.recorded.request_id] = dag
        if fault == "tree":
            entries["extra"] = chosen.result
        forged = tx.put_commit(
            tx.put_tree(entries),
            parents=(chosen.commit if fault == "parent" else got.recorded.commit,),
        )
    with pytest.raises(ValueError):
        app.inspect_request(
            path,
            commit=got.recorded.commit,
            request=got.recorded.request,
            decision_name=got.decision.name,
            satisfaction_commit=forged,
        )


@pytest.mark.parametrize("fault", ["file", "cleanup"])
def test_consumed_public_projection_IO_cleanup_closes_before_D_Q(
    menu, monkeypatch, fault
):
    path = menu[0][0][0]
    definition = define(menu)
    before = (path / "data.mdb").read_bytes()
    removal, owned, replacing = shutil.rmtree, [], ex.os.replace

    def denied_remove(directory, *a, **k):
        if Path(directory).name.startswith("dml-implementation-validation-"):
            owned.append(Path(directory))
            raise PermissionError("private validation disposal")
        return removal(directory, *a, **k)

    def denied_file(source, target):
        if Path(target).parent.parent.name.startswith("dml-implementation-validation-"):
            raise PermissionError("private preparation publication")
        return replacing(source, target)

    try:
        with monkeypatch.context() as guard:
            guard.setattr(
                shutil, "rmtree", denied_remove if fault == "cleanup" else removal
            )
            if fault == "file":
                guard.setattr(ex.os, "replace", denied_file)
            with pytest.raises(PermissionError):
                request(path, definition.commit)
        assert_file_unchanged(path / "data.mdb", before)
    finally:
        for directory in owned:
            removal(directory)


def test_finite_all_modes_required_Q_and_actual_script_entry(
    menu, selected, capsys, monkeypatch
):
    path = menu[0][0][0]
    definition, chosen = selected
    base = menu[1]
    args = [
        "define",
        str(path),
        str(base),
        "other-intent",
        "urn:example:double",
        "reuse-by-default",
        "double-a",
        "cli-defined",
        "--implementation",
        "double-a",
        "double-a-binding",
        "other-sa",
        "--implementation",
        "double-b",
        "double-b-binding",
        "other-sb",
    ]
    assert app.main(args) == 0
    defined = json.loads(capsys.readouterr().out)
    assert (
        app.main(
            [
                "update-default",
                str(path),
                defined["commit"],
                "other-intent",
                "double-b",
                "cli-updated",
            ]
        )
        == 0
    )
    updated = json.loads(capsys.readouterr().out)
    assert (
        app.main(["inspect-definition", str(path), updated["commit"], "other-intent"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["default_implementation"] == "double-b"
    assert (
        app.main(
            [
                "request",
                str(path),
                str(chosen.commit),
                "double-intent",
                "double-inputs",
                "decision-cli",
                "double-a",
                "default",
                "decision-cli",
                "submission-cli",
                "--reuse-ref",
                "reused-cli",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert (
        app.main(
            ["inspect-decision", str(path), report["decision_commit"], "decision-cli"]
        )
        == 0
    )
    assert (
        json.loads(capsys.readouterr().out)["implementation_reason"]
        == "explicit-implementation"
    )
    assert (
        app.main(
            [
                "inspect-request",
                str(path),
                report["request_commit"],
                report["request"],
                "decision-cli",
                "--satisfaction-commit",
                report["commit"],
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["attempt"] == str(chosen.attempt)
    assert (
        app.main(
            [
                "request",
                str(path),
                updated["commit"],
                "other-intent",
                "double-inputs",
                "decision-fresh",
                "default",
                "fresh",
                "decision-fresh",
                "submission-fresh",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["association"] is None
    with pytest.raises(SystemExit) as error:
        app.main(["inspect-request", str(path), report["request_commit"]])
    assert error.value.code == 2
    monkeypatch.setitem(sys.modules, "reuse_selection", app.selection)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "implementation_selection.py",
            "inspect-definition",
            str(path),
            updated["commit"],
            "other-intent",
        ],
    )
    with pytest.raises(SystemExit) as error:
        runpy.run_path(
            str(ROOT / "examples/implementation_selection.py"), run_name="__main__"
        )
    assert error.value.code == 0
