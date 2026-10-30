"""Meaningful response/projection/submission failures and policy publication edges."""

from dataclasses import replace
from pathlib import Path
import runpy
import shutil
import sys

import daggerml as d
from daggerml import exchange as ex
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged
from test_composed_execution import producer
from test_exchange import ROOT, exchange_runtime, literal, tree
from test_explicit_reuse import double
from test_intent_defaults import app, define, request, inspect
from test_reuse_selection import expected_file, select


@pytest.mark.parametrize(
    "change,error",
    [
        ({"update": 1}, TypeError),
        ({"intent_uri": None}, ValueError),
        ({"intent_uri": "HTTP://Example.com"}, ValueError),
        ({"commit_existing": True}, ValueError),
        ({"update": True}, ValueError),
    ],
)
def test_definition_explicit_update_mode_canonical_URI_absence_state(
    double, change, error
):
    change = dict(change)
    path = double[0][0]
    if change.pop("commit_existing", False):
        change["commit"] = define(double).commit
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(error):
        define(double, **change)
    assert_file_unchanged(path / "data.mdb", before)


def test_existing_decision_entry_not_replaced_or_unrelated_pending_marker(double):
    path = double[0][0]
    definition = define(double)
    got = request(path, definition.commit)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="decision tree name already exists"):
        request(
            path,
            got.recorded.commit,
            decision_ref="another",
            submission_ref="another-submission",
        )
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "fault", ["zero-parent", "two-parents", "extra", "preexisting-name"]
)
def test_D_reader_exact_one_basis_parent_add_only_absent_named_D(double, fault):
    path = double[0][0]
    definition = define(double)
    got = request(path, definition.commit)
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, got.decision.commit)
        parents = (
            ()
            if fault == "zero-parent"
            else (
                (definition.commit, double[0][1])
                if fault == "two-parents"
                else (
                    (got.decision.commit,)
                    if fault == "preexisting-name"
                    else (definition.commit,)
                )
            )
        )
        if fault == "extra":
            entries["extra"] = double[2][2].result
        fake = tx.put_commit(tx.put_tree(entries), parents=parents)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.inspect_decision(path, commit=fake, decision_name=got.decision.name)
    assert_file_unchanged(path / "data.mdb", before)


def test_declared_fresh_cannot_claim_reuse_satisfaction(double):
    path = double[0][0]
    definition = define(double)
    got = request(path, definition.commit)
    with pytest.raises(ValueError, match="fresh decision cannot"):
        app.inspect_request(
            path,
            commit=got.recorded.commit,
            request=got.recorded.request,
            decision_name=got.decision.name,
            satisfaction_commit=got.recorded.commit,
        )


@pytest.mark.parametrize("fault", ["Q-response", "reuse-response"])
def test_actual_owning_response_mismatch_does_not_undo_committed_D_Q_W(
    double, expected_file, monkeypatch, fault
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit)
    if fault == "Q-response":
        owning = ex.record_exchange_request

        def changed(*a, **k):
            got = owning(*a, **k)
            return replace(got, inputs=double[0][2][1].inputs)

        monkeypatch.setattr(ex, "record_exchange_request", changed)
        with pytest.raises(ValueError, match="owning Q differs"):
            request(path, definition.commit, override="fresh")
    else:
        owning = app.selection.reuse_selected

        def changed(*a, **k):
            got = owning(*a, **k)
            return replace(got, attempt=chosen.request)

        monkeypatch.setattr(app.selection, "reuse_selected", changed)
        with pytest.raises(ValueError, match="owning reused selection differs"):
            request(path, definition.commit, reuse_ref="reused")
    with d.Repository(path) as repository, repository.read() as tx:
        cq = tx.get_ref("policy-submission")
        cdec = tx.get_ref("decision-one")
        entries = tree(tx, cq)
        qnames = set(entries) - set(tree(tx, cdec))
        q = entries[qnames.pop()]
        w = tx.get_ref("reused") if fault == "reuse-response" else None
    # Reader uses ACTUAL native history, not substituted response fields.
    assert app.inspect_request(
        path, commit=cq, request=q, decision_name="decision-one", satisfaction_commit=w
    ).reason == ("override-fresh" if fault == "Q-response" else "default-selection")


def test_late_reuse_projection_cleanup_can_leave_complete_D_Q_W(
    double, expected_file, monkeypatch
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit)
    removal, owned = shutil.rmtree, []
    # First selection.inspect projection closes BEFORE D; second projection lives
    # through Q/W delegation. Fail ONLY that late owned projection's disposal.
    count = []

    def denied(directory, *a, **k):
        if Path(directory).name.startswith("dml-selection-projection-"):
            count.append(True)
            if len(count) == 2:
                owned.append(Path(directory))
                raise PermissionError("private late delegation cleanup")
        return removal(directory, *a, **k)

    try:
        with monkeypatch.context() as guard:
            guard.setattr(shutil, "rmtree", denied)
            with pytest.raises(PermissionError):
                request(path, definition.commit, reuse_ref="reused")
        with d.Repository(path) as repository, repository.read() as tx:
            cq, w = tx.get_ref("policy-submission"), tx.get_ref("reused")
            cdec = tx.get_ref("decision-one")
            entries = tree(tx, cq)
            names = set(entries) - set(tree(tx, cdec))
            q = entries[names.pop()]
        assert (
            app.inspect_request(
                path,
                commit=cq,
                request=q,
                decision_name="decision-one",
                satisfaction_commit=w,
            ).reason
            == "default-selection"
        )
    finally:
        for directory in owned:
            removal(directory)


def test_actual_script_entry_runs_finite_native_inspect_mode(
    double, monkeypatch, capsys
):
    path = double[0][0]
    definition = define(double)
    monkeypatch.setitem(sys.modules, "reuse_selection", app.selection)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "intent_defaults.py",
            "inspect-definition",
            str(path),
            str(definition.commit),
            "double-intent",
        ],
    )
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(ROOT / "examples/intent_defaults.py"), run_name="__main__")
    assert error.value.code == 0
    assert "reuse-by-default" in capsys.readouterr().out
