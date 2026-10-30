"""Policy matrix/full dimensions, source/closure/scratch controls and finite modes."""

import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_composed_execution import producer, execute
from test_exchange import ROOT, exchange_runtime, literal, scalar, tree, typed_oracle
from test_exchange_records import clone
from test_explicit_reuse import double
from test_intent_defaults import app, define, request, inspect
from test_records_hypothesis import run_driver
from test_reuse_selection import expected_file, select


@pytest.mark.parametrize("mode", app.MODES)
@pytest.mark.parametrize("override", app.OVERRIDES)
def test_complete_no_selection_matrix_explicit_missing_never_fallback(
    double, mode, override
):
    path = double[0][0]
    definition = define(double, default=mode)
    before = (path / "data.mdb").read_bytes()
    if override == "reuse-selected":
        with pytest.raises(ValueError, match="requires selection entry"):
            request(
                path, definition.commit, override=override, reuse_ref="not-fallback"
            )
        assert_file_unchanged(path / "data.mdb", before)
    else:
        got = request(path, definition.commit, override=override)
        assert got.decision.reason == (
            "override-fresh"
            if override == "fresh"
            else (
                "default-no-selection"
                if mode == "reuse-by-default"
                else "default-execution"
            )
        )
        assert inspect(path, got) == got.decision


@pytest.mark.parametrize("mode", app.MODES)
@pytest.mark.parametrize("override", app.OVERRIDES)
def test_complete_valid_selection_matrix_double_override_and_no_adoption(
    double, expected_file, mode, override
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit, default=mode)
    reuse = (
        override == "reuse-selected"
        or override == "default"
        and mode == "reuse-by-default"
    )
    got = request(
        path,
        definition.commit,
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
            else "default-selection" if reuse else "default-execution"
        )
    )
    assert inspect(path, got) == got.decision
    with d.Repository(path) as repository, repository.read() as tx:
        assert tree(tx, got.recorded.commit)["selected-double"] == chosen.dag


@pytest.mark.parametrize(
    "dimension",
    [
        "intent",
        "source",
        "interpreter",
        "timeout",
        "factor",
        "factor-type",
        "endpoint",
        "bucket",
        "gate",
        "exit-code",
        "artifacts",
        "producer",
    ],
)
def test_full_valid_dimension_mismatch_rejects_before_D_Q_but_explicit_fresh_valid(
    double, expected_file, dimension
):
    path, base, first = double[0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit)
    alternate = (
        execute(path, base, "other-producer") if dimension == "producer" else None
    )
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, definition.commit)
        if dimension in ("source", "interpreter", "timeout"):
            binding = double[2][1].binding
            entries["double-binding"] = local.put_local_binding(
                tx,
                source=scalar(tx, binding, "source")
                + (b"\n# changed\n" if dimension == "source" else b""),
                interpreter=scalar(tx, binding, "interpreter")
                + (".changed" if dimension == "interpreter" else ""),
                timeout_ms=scalar(tx, binding, "timeout-ms")
                + (1 if dimension == "timeout" else 0),
            )
        elif dimension == "intent":
            node = literal(tx, d.Datum.uri("urn:example:different"))
            entries[definition.name] = clone(
                tx, definition.dag, fields={"intent": node}, root=node
            )
        else:
            fields = dict(tx.get_dag(double[2][1].inputs).bindings)
            if dimension == "producer":
                assert alternate[2].result == first[2].result
                fields["producer"] = tx.put_subdag(
                    alternate[2].completion.final_attempt
                )
            else:
                name, value = {
                    "factor": ("factor", 3),
                    "factor-type": ("factor", True),
                    "endpoint": ("endpoint", "http://other:4566"),
                    "bucket": ("bucket", "other-bucket"),
                    "gate": ("gate", "different/key"),
                    "exit-code": ("exit-code", 23),
                    "artifacts": ("artifacts", b"changed"),
                }[dimension]
                fields[name] = literal(tx, value)
            entries["double-inputs"] = tx.put_dag(root=fields["value"], bindings=fields)
        changed = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    before = (path / "data.mdb").read_bytes()
    with track_typed_puts(path, typed_oracle(path, (changed,))) as puts:
        with pytest.raises(ValueError, match="full inputs differ"):
            request(path, changed, reuse_ref="mismatch")
    assert not puts
    assert_file_unchanged(path / "data.mdb", before)
    fresh = request(path, changed, override="fresh")
    assert fresh.decision.reason == "override-fresh" and fresh.reused is None
    assert inspect(path, fresh) == fresh.decision


@pytest.mark.parametrize(
    "field,value",
    [
        ("intent_name", "missing"),
        ("override", "unknown"),
        ("override", None),
        ("binding_name", "double-inputs"),
        ("selection_slot", "double-intent"),
        ("decision_name", "double-intent"),
        ("decision_name", "request-q-reserved"),
        ("intent_name", "bad/name"),
        ("decision_ref", "bad/name"),
        ("submission_ref", "decision-one"),
        ("map_size", True),
        ("map_size", 1),
        ("reuse_ref", "unused"),
    ],
)
def test_strict_safe_distinct_names_unknown_missing_enum_refs_profile_before_any_D_Q(
    double, field, value
):
    path = double[0][0]
    definition = define(double)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        request(path, definition.commit, **{field: value})
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("damage", ["missing", "corrupt", "oversized"])
@pytest.mark.parametrize("override", ["default", "fresh"])
def test_unused_selection_bypass_NEVER_bypasses_native_all_parent_composite_closure(
    double, damage, override
):
    path = double[0][0]
    definition = define(double, default="execute-by-default")
    with d.Repository(path) as repository, repository.write() as tx:
        leaf = tx.put_datum(
            b"x" * (4 * 1024 * 1024 + 1) if damage == "oversized" else b"composite-only"
        )
        raw = tx.get_record("datum", leaf)
        collection = tx.put_datum(d.Datum.list([leaf]))
        entries = tree(tx, definition.commit)
        entries["selected-double"] = tx.put_dag(root=tx.put_literal(collection))
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
        request(path, basis, override=override)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["write", "cleanup"])
def test_public_policy_validation_files_and_cleanup_fail_before_D_Q(
    double, monkeypatch, fault
):
    path = double[0][0]
    definition = define(double)
    before = (path / "data.mdb").read_bytes()
    removal, owned = shutil.rmtree, []
    write = ex.os.replace

    def denied_remove(directory, *a, **k):
        if Path(directory).name.startswith("dml-policy-validation-"):
            owned.append(Path(directory))
            raise PermissionError("private policy scratch cleanup")
        return removal(directory, *a, **k)

    def denied_write(source, target):
        if Path(target).parent.parent.name.startswith("dml-policy-validation-"):
            raise PermissionError("private public preparation file publication")
        return write(source, target)

    try:
        with monkeypatch.context() as guard:
            guard.setattr(
                shutil, "rmtree", denied_remove if fault == "cleanup" else removal
            )
            if fault == "write":
                guard.setattr(ex.os, "replace", denied_write)
            with pytest.raises(PermissionError):
                request(path, definition.commit)
        assert_file_unchanged(path / "data.mdb", before)
    finally:
        for directory in owned:
            removal(directory)


def test_D_Q_W_separate_failures_no_whole_operation_rollback_repair(
    double, expected_file, monkeypatch
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit)
    original = ex.record_exchange_request
    with monkeypatch.context() as guard:
        guard.setattr(
            ex,
            "record_exchange_request",
            lambda *a, **k: (_ for _ in ()).throw(MemoryError("private Q failure")),
        )
        with pytest.raises(MemoryError):
            request(path, definition.commit, reuse_ref="reused")
    with d.Repository(path) as repository, repository.read() as tx:
        decision = tx.get_ref("decision-one")
        with pytest.raises(d.NotFoundError):
            tx.get_ref("policy-submission")
    assert (
        app.inspect_decision(path, commit=decision, decision_name="decision-one").reason
        == "default-selection"
    )
    with d.Repository(path) as repository, repository.write() as tx:
        tx.create_ref("conflict-W", definition.commit)
    with pytest.raises(d.InvalidStateError):
        request(
            path,
            definition.commit,
            decision_name="decision-two",
            decision_ref="decision-two",
            submission_ref="submission-two",
            reuse_ref="conflict-W",
        )
    with d.Repository(path) as repository, repository.read() as tx:
        cq = tx.get_ref("submission-two")
        qentries = tree(tx, cq)
        qnames = set(qentries) - set(tree(tx, tx.get_commit(cq).parents[0]))
        q = qentries[qnames.pop()]
    assert (
        app.inspect_request(
            path, commit=cq, request=q, decision_name="decision-two"
        ).action
        == "reuse-selected"
    )
    with pytest.raises(d.InvalidStateError):
        request(
            path, definition.commit, reuse_ref="reused"
        )  # D-ref conflict, never duplicate Q.


def test_all_finite_offline_modes_and_required_exact_Q_argument(
    double, expected_file, capsys, monkeypatch
):
    path = double[0][0]
    base = str(double[2][2].commit)
    assert (
        app.main(
            [
                "define",
                str(path),
                base,
                "double-intent",
                "urn:example:double",
                "reuse-by-default",
                "intent-default",
            ]
        )
        == 0
    )
    defined = json.loads(capsys.readouterr().out)
    assert (
        app.main(["inspect-definition", str(path), defined["commit"], "double-intent"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["definition"] == defined["definition"]
    assert (
        app.main(
            [
                "request",
                str(path),
                defined["commit"],
                "double-intent",
                "double-binding",
                "double-inputs",
                "selected-double",
                "decision-one",
                "default",
                "decision-one",
                "policy-submission",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["action"] == "execute-fresh" and report["association"] is None
    assert (
        app.main(
            ["inspect-decision", str(path), report["decision_commit"], "decision-one"]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["reason"] == "default-no-selection"
    assert (
        app.main(
            [
                "inspect-request",
                str(path),
                report["request_commit"],
                report["request"],
                "decision-one",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["definition"] == defined["definition"]
    with pytest.raises(SystemExit) as error:
        app.main(["inspect-request", str(path), report["request_commit"]])
    assert error.value.code == 2
    with pytest.raises(TypeError):
        app.inspect_request(
            path,
            commit=d.ObjectId.from_hex(report["request_commit"]),
            request="not ObjectId",
            decision_name="decision-one",
        )
    monkeypatch.setitem(sys.modules, "reuse_selection", app.selection)
    monkeypatch.setattr(sys, "argv", ["intent_defaults.py"])
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(ROOT / "examples/intent_defaults.py"), run_name="__main__")
    assert error.value.code == 2
