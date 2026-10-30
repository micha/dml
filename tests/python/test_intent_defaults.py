"""Small native Idef/D/own-Q/pinned reader review draft. NEVER starts Docker."""

import importlib.util
from pathlib import Path
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged, assert_recorded
from test_composed_execution import producer
from test_exchange import (
    ROOT,
    exchange_runtime,
    literal,
    nested,
    scalar,
    tree,
    typed_oracle,
)
from test_explicit_reuse import double
from test_reuse_selection import expected_file, select

spec = importlib.util.spec_from_file_location(
    "intent_defaults_example", ROOT / "examples/intent_defaults.py"
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


def define(double, **changes):
    arguments = dict(
        commit=double[2][2].commit,
        intent_name="double-intent",
        intent_uri="urn:example:double",
        default="reuse-by-default",
        ref="intent-default",
    )
    arguments.update(changes)
    return app.define(double[0][0], **arguments)


def request(path, commit, **changes):
    arguments = dict(
        commit=commit,
        intent_name="double-intent",
        binding_name="double-binding",
        inputs_name="double-inputs",
        selection_slot="selected-double",
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


def test_define_exact_minimal_native_shape_parent_ref_old_bytes_no_Q_T(
    double, monkeypatch
):
    path, base, _ = double[0]
    previous = double[2][2].commit
    old = typed_oracle(path, (previous, base))
    with monkeypatch.context() as guard:
        guard.setattr(
            subprocess,
            "Popen",
            lambda *a, **k: pytest.fail("policy authoring must not dispatch"),
        )
        got = define(double)
    assert app.inspect_definition(path, commit=got.commit, intent_name=got.name) == got
    with d.Repository(path) as repository, repository.read() as tx:
        assert tx.get_ref("main") == base
        assert tx.get_ref("intent-default") == got.commit
        assert tx.get_commit(got.commit).parents == (previous,)
        expected = tree(tx, previous)
        expected[got.name] = got.dag
        assert tree(tx, got.commit) == expected
        description = tx.get_dag(got.dag)
        assert set(description.bindings) == {"role", "intent", "default"}
        assert description.root == description.bindings["intent"]
        assert tx.get_datum(tx.get_node(description.root).datum) == d.Datum.uri(
            "urn:example:double"
        )
        assert scalar(tx, got.dag, "role") == "example-intent-default-v1"
        assert scalar(tx, got.dag, "default") == "reuse-by-default"
        assert all(tx.get_record(*key) == raw for key, raw in old.items())


@pytest.mark.parametrize(
    "mode,override,reason",
    [
        ("reuse-by-default", "default", "default-no-selection"),
        ("execute-by-default", "default", "default-execution"),
        ("reuse-by-default", "fresh", "override-fresh"),
    ],
)
def test_declared_fresh_records_only_D_own_Q_exact_spine_no_adoption(
    double, monkeypatch, mode, override, reason
):
    path = double[0][0]
    definition = define(double, default=mode)
    with monkeypatch.context() as guard:
        guard.setattr(
            subprocess, "Popen", lambda *a, **k: pytest.fail("pending Q not execution")
        )
        got = request(path, definition.commit, override=override)
        assert inspect(path, got) == got.decision
    assert got.decision.reason == reason and got.decision.action == "execute-fresh"
    assert got.reused is None and got.decision.selected is None
    assert got.recorded.request != double[2][2].request
    assert_recorded(path, got.recorded)
    with d.Repository(path) as repository, repository.read() as tx:
        assert tx.get_commit(got.decision.commit).parents == (definition.commit,)
        expected = tree(tx, definition.commit)
        expected[got.decision.name] = got.decision.dag
        assert tree(tx, got.decision.commit) == expected
        assert "selection" not in tx.get_dag(got.decision.dag).bindings
        assert nested(tx, got.decision.dag, "intent-definition") == definition.dag
        assert "selected-double" not in tree(tx, got.recorded.commit)
        assert {
            n for n in tree(tx, got.recorded.commit) if n.startswith("attempt-")
        } == {n for n in tree(tx, definition.commit) if n.startswith("attempt-")}


@pytest.mark.parametrize(
    "mode,override,reason",
    [
        ("reuse-by-default", "default", "default-selection"),
        ("execute-by-default", "reuse-selected", "override-selected-reuse"),
    ],
)
def test_default_hit_explicit_execute_default_override_pinned_S_own_Q_W(
    double, expected_file, monkeypatch, mode, override, reason
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit, default=mode)
    for source in (double[2][0], expected_file, double[2][4]):
        source.rename(source.with_name(source.name + ".unavailable"))
    with monkeypatch.context() as guard:
        guard.setattr(
            subprocess, "Popen", lambda *a, **k: pytest.fail("reuse never spawns")
        )
        got = request(
            path, definition.commit, override=override, reuse_ref="policy-reused"
        )
        assert inspect(path, got) == got.decision
    assert got.decision.reason == reason and got.decision.action == "reuse-selected"
    assert got.recorded.base == got.decision.commit
    assert got.recorded.request != chosen.request
    assert got.reused.attempt == chosen.attempt and got.reused.result == chosen.result
    with d.Repository(path) as repository, repository.read() as tx:
        assert nested(tx, got.decision.dag, "selection") == chosen.dag
        assert set(tx.get_dag(got.reused.dag).bindings) == {
            "role",
            "request",
            "attempt",
            "result",
        }
        assert nested(tx, chosen.attempt, "request") == chosen.request
    copied = path.parent / "policy-transferred"
    with d.Repository(copied, create=True):
        pass
    transfer.import_commit(
        copied, transfer.export_commit(path, commit=got.reused.commit)
    )
    before = (copied / "data.mdb").read_bytes()
    assert inspect(copied, got) == got.decision
    assert_file_unchanged(copied / "data.mdb", before)


def test_present_bad_selection_errors_not_absence_but_explicit_fresh_ignores_framing(
    double,
):
    path = double[0][0]
    definition = define(double)
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, definition.commit)
        entries["selected-double"] = double[2][2].result  # Native-valid, NOT S.
        bad = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="selection shape"):
        request(path, bad)
    assert_file_unchanged(path / "data.mdb", before)
    got = request(path, bad, override="fresh")
    assert (
        got.decision.reason == "override-fresh" and inspect(path, got) == got.decision
    )
    with d.Repository(path) as repository, repository.read() as tx:
        assert (
            tree(tx, got.recorded.commit)["selected-double"]
            == entries["selected-double"]
        )


@pytest.mark.parametrize("delta", ["empty", "unrelated"])
def test_missing_Q_cannot_select_fresh_Q_in_B_projection_as_submission_authority(
    double, delta
):
    path = double[0][0]
    definition = define(double)
    got = request(path, definition.commit)
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, got.decision.commit)
        if delta == "unrelated":
            entries["unrelated"] = double[2][2].result
        fake = tx.put_commit(tx.put_tree(entries), parents=(got.decision.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(TypeError, match="exact ObjectId"):
        app.inspect_request(
            path, commit=fake, request=None, decision_name=got.decision.name
        )
    assert_file_unchanged(path / "data.mdb", before)
    assert inspect(path, got) == got.decision


def test_update_true_sibling_defaults_old_decision_pinned_after_latest_ref_move(double):
    path = double[0][0]
    definition = define(double)
    original = request(path, definition.commit)
    changed = define(
        double,
        commit=definition.commit,
        update=True,
        default="execute-by-default",
        ref="execute-policy",
    )
    with d.Repository(path) as repository, repository.write() as tx:
        keep = tx.put_commit(
            tx.get_commit(definition.commit).tree, parents=(definition.commit,)
        )
        tx.update_ref("intent-default", changed.commit)
    assert (
        original.decision.reason == "default-no-selection"
        and inspect(path, original) == original.decision
    )
    assert (
        app.inspect_definition(path, commit=keep, intent_name="double-intent").dag
        == definition.dag
    )
    with d.Repository(path) as repository, repository.read() as tx:
        assert (
            tx.get_commit(keep).parents
            == tx.get_commit(changed.commit).parents
            == (definition.commit,)
        )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="stable URI"):
        define(
            double,
            commit=changed.commit,
            update=True,
            intent_uri="urn:example:other",
            ref="wrong-uri",
        )
    assert_file_unchanged(path / "data.mdb", before)
