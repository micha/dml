"""Default-safe controller oracles/blockers; one small local table composition test."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_exchange import ROOT, exchange_runtime, literal, tree
from test_multi_input_reuse import (
    app,
    state,
    empty,
    request,
    indexed,
    table_request,
    menu,
    expected_file,
    double,
    producer,
)

spec = importlib.util.spec_from_file_location(
    "multi_input_story", ROOT / "tests/multi_input/story.py"
)
story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story)


def test_three_local_completions_multiple_entries_one_key_adoption_true_siblings(
    tmp_path, exchange_runtime
):
    root = tmp_path / "story"
    root.mkdir()
    state = story.init(root, app)
    path = Path(state["path"])
    for label, n, basis in (
        ("two", 2, state["empty"]),
        ("three", 3, None),
        ("fresh", 2, None),
    ):
        basis = basis or state["last"]
        story.request(
            path,
            app,
            state,
            label,
            basis,
            n,
            fresh=label == "fresh",
            expected_reason=(
                "override-fresh" if label == "fresh" else "default-no-entry"
            ),
        )
        story.execute(root, path, state, label)
        chosen = story.capture(path, app, state, label, state["runs"][label]["commit"])
        if label != "fresh":
            got = app.select_entry(
                path,
                commit=chosen.commit,
                table_name="table",
                selection_slot=chosen.slot,
                ref="indexed-" + label,
            )
            assert app.inspect_table(path, commit=got.commit, table_name="table") == got
            state["last"] = str(got.commit)
            if label == "three":
                state["table-two"] = str(got.dag)
        else:
            state["common"] = str(chosen.commit)
    adopted = app.adopt_entry(
        path,
        commit=chosen.commit,
        table_name="table",
        selection_slot="selected-fresh",
        ref="adopted",
    )
    state["adopted"] = str(adopted.commit)
    with d.Repository(path) as repo, repo.write() as tx:
        keep = tx.put_commit(
            tx.get_commit(chosen.commit).tree, parents=(chosen.commit,)
        )
        tx.create_ref("keep", keep)
    state["keep"] = str(keep)
    assert story.verify_branches(path, app, state)["only_I2_adopted"]
    with d.Repository(path) as repo, repo.read() as tx:
        assert tree(tx, chosen.commit)["table"] == d.ObjectId.from_hex(
            state["table-two"]
        )
    # Once current tree S cross-link is overwritten, ALL-entry inspection rejects.
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, chosen.commit)
        entries["selected-two"] = entries["selected-fresh"]
        broken = tx.put_commit(tx.put_tree(entries), parents=(chosen.commit,))
    with pytest.raises(ValueError, match="slot"):
        app.inspect_table(path, commit=broken, table_name="table")
    for label in ("two", "three", "fresh"):
        assert (
            state["runs"][label]["child_reaped"]
            and state["runs"][label]["child_exit"] == 0
        )


def test_capacity_insertion_does_not_evict_valid_existing_row(indexed, monkeypatch):
    path, _, _, chosen, table = indexed
    with monkeypatch.context() as guard:
        # Precise boundary unit control over the finite count, no production cap change.
        guard.setattr(app, "MAX_ENTRIES", 0)
        with pytest.raises(ValueError, match="capacity"):
            app.select_entry(
                path,
                commit=chosen.commit,
                table_name="table",
                selection_slot=chosen.slot,
                ref="other",
            )
    assert app.MAX_ENTRIES == 16


def test_same_occurrence_different_public_T_F_descriptions_still_not_fresh(
    indexed, monkeypatch
):
    path, _, _, chosen, table = indexed
    from dataclasses import replace

    original = app.selection.inspect

    def inspect(*a, **k):
        got = original(*a, **k)
        if k["slot"] == "alternate":
            # Unit adversary: returned description changes, occurrence doesn't.
            return replace(got, attempt=indexed[1].dag, completion=indexed[1].commit)
        return got

    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, table.commit)
        entries["alternate"] = chosen.dag
        basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
    monkeypatch.setattr(app.selection, "inspect", inspect)
    with pytest.raises(ValueError, match="distinct attempt occurrence"):
        app.adopt_entry(
            path,
            commit=basis,
            table_name="table",
            selection_slot="alternate",
            ref="other",
        )


def test_returned_binding_and_existing_decision_slot_authority(state):
    path, definition = state
    got = request(state, definition.commit)
    assert got.decision.binding == got.recorded.binding
    with pytest.raises(ValueError, match="already exists"):
        request(
            state, got.recorded.commit, decision_ref="other", submission_ref="other-q"
        )


@pytest.mark.parametrize(
    "name",
    ["http", "http.client", "urllib.request", "boto3", "docker", "daggerml.floci"],
)
def test_actual_fresh_offline_transport_attempt_blocked(name):
    code = story.OFFLINE.replace(
        "runpy.run_path(sys.argv[0],run_name='__main__')",
        """import types
p=types.ModuleType('daggerml');p.__path__=[];sys.modules['daggerml']=p
try:__import__(sys.argv[0])
except AssertionError as e:assert 'cannot import transport' in str(e)
else:raise AssertionError('not blocked')""",
    )
    got = subprocess.run(
        [sys.executable, "-c", code, name], capture_output=True, timeout=15
    )
    assert got.returncode == 0, got.stderr.decode()


@pytest.mark.parametrize("action", ["subprocess.Popen", "os.system", "os.fork"])
def test_actual_fresh_offline_process_spawn_attempt_blocked(action):
    code = story.OFFLINE.replace(
        "runpy.run_path(sys.argv[0],run_name='__main__')",
        """import os,subprocess
try:
 if sys.argv[0]=='subprocess.Popen':subprocess.Popen([sys.executable,'-c','pass'])
 elif sys.argv[0]=='os.system':os.system('true')
 else:
  if not hasattr(os,'fork'):
   sys.audit('os.fork')
  else:os.fork()
except AssertionError as e:assert 'cannot spawn' in str(e)
else:raise AssertionError('not blocked')""",
    )
    got = subprocess.run(
        [sys.executable, "-c", code, action], capture_output=True, timeout=15
    )
    assert got.returncode == 0, got.stderr.decode()


@pytest.mark.parametrize(
    "fault",
    ["base", "decision-commit", "table", "entry", "selection", "override", "reason"],
)
def test_controller_same_relation_wrong_pinned_context_rejects(
    state, monkeypatch, fault
):
    path, definition = state
    got = request(state, empty(state).commit)
    item = dict(
        commit=str(got.recorded.commit),
        request=str(got.recorded.request),
        decision=got.decision.name,
        base=str(got.decision.base),
        decision_commit=str(got.decision.commit),
        binding=str(got.decision.binding),
        inputs=str(got.decision.inputs),
        override="default",
        reason="default-no-entry",
        table=str(got.decision.table.dag),
        entry=None,
        selection=None,
        satisfaction=None,
    )
    native = {"requests": {"one": item}}
    assert story.read(path, app, native, "one")["read_only"]
    item[{"decision-commit": "decision_commit"}.get(fault, fault)] = (
        str(definition.commit)
        if fault in ("base", "decision-commit", "table", "entry", "selection")
        else "wrong"
    )
    with pytest.raises(AssertionError):
        story.read(path, app, native, "one")
