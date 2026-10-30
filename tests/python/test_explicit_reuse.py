"""Public native explicit selection/new-Q/old-T tests; no Docker startup."""

import importlib.util
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex
import pytest

from test_caller_requests import assert_file_unchanged, assert_recorded
from test_composed_execution import producer, basis, execute
from test_exchange import (
    ROOT,
    exchange_runtime,
    literal,
    nested,
    scalar,
    tree,
    typed_oracle,
)

spec = importlib.util.spec_from_file_location(
    "reuse_example", ROOT / "examples/explicit_reuse.py"
)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)


@pytest.fixture
def double(producer):
    authored = basis(producer)
    second = execute(
        producer[0], authored.commit, "double", "double-binding", "double-inputs"
    )
    return producer, authored, second


def reuse(double, **changes):
    producer, authored, second = double
    arguments = dict(
        commit=second[2].commit,
        binding_name="double-binding",
        inputs_name="double-inputs",
        intent_uri="urn:example:double",
        historical_packet=second[0],
        historical_expected=second[1],
        submission_ref="reuse-submission",
        ref="reused-double",
    )
    arguments.update(changes)
    return app.reuse_attempt(producer[0], **arguments)


def test_new_q_old_exact_t_result_no_execution_and_separate_tree_spine(
    double, monkeypatch
):
    producer, authored, second = double
    path, base, first = producer
    old = typed_oracle(path, (second[2].commit, base))
    with monkeypatch.context() as guard:
        guard.setattr(
            subprocess, "Popen", lambda *a, **k: pytest.fail("reuse never executes")
        )
        got = reuse(double)
    assert_recorded(path, got.recorded)
    assert got.recorded.request != second[2].request
    assert (
        got.attempt == second[2].completion.final_attempt
        and got.result == second[2].result
    )
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("main") == base
        assert tx.get_commit(got.commit).parents == (got.recorded.commit,)
        expected = tree(tx, got.recorded.commit)
        expected["reuse-" + got.recorded.request_id] = got.dag
        assert tree(tx, got.commit) == expected
        assert nested(tx, got.dag, "request") == got.recorded.request
        assert nested(tx, got.dag, "attempt") == got.attempt
        assert nested(tx, got.attempt, "request") == second[2].request
        assert nested(tx, got.dag, "result") == got.result
        assert scalar(tx, got.dag, "role") == "example-explicit-reuse-v1"
        dag = tx.get_dag(got.dag)
        assert set(dag.bindings) == {"role", "request", "attempt", "result"}
        assert dag.root == dag.bindings["result"]
        assert {n for n in expected if n.startswith("attempt-")} == {
            n for n in tree(tx, second[2].commit) if n.startswith("attempt-")
        }
        for key, raw in old.items():
            assert tx.get_record(*key) == raw
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError, match="submission ref"):
        reuse(double)
    assert_file_unchanged(path / "data.mdb", before)


def test_nonfirst_parent_reachability_containing_commit_not_matching_dimension(double):
    path, base, _ = double[0]
    second = double[2]
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, second[2].commit)
        entries["annotation"] = tx.put_dag(
            root=literal(tx, "another containing snapshot")
        )
        containing = tx.put_commit(
            tx.put_tree(entries), parents=(base, second[2].commit)
        )
    got = reuse(double, commit=containing)
    assert (
        got.recorded.base == containing
        and got.attempt == second[2].completion.final_attempt
    )


def test_explicit_fresh_control_imports_w_and_only_new_t_keeps_old_selection(double):
    path = double[0][0]
    old = double[2]
    chosen = reuse(double)
    retained = typed_oracle(path, (chosen.commit,))
    fresh = execute(
        path, chosen.commit, "fresh-double", "double-binding", "double-inputs"
    )
    assert fresh[1].binding == old[1].binding and fresh[1].inputs == old[1].inputs
    assert len({fresh[2].request, chosen.recorded.request, old[2].request}) == 3
    assert fresh[2].attempt_id != old[2].attempt_id
    assert fresh[2].result == old[2].result == chosen.result
    with d.Repository(fresh[4] / "worker.dml") as repo, repo.read() as tx:
        expected = tree(tx, fresh[1].commit)
        expected[fresh[3].context.publication_ref] = fresh[2].initial_attempt
        assert tree(tx, fresh[2].pre_dispatch) == expected
        assert tx.get_commit(fresh[2].pre_dispatch).parents == (fresh[1].commit,)
        assert nested(tx, chosen.dag, "attempt") == chosen.attempt
        assert nested(tx, chosen.attempt, "request") == old[2].request
        assert all(tx.get_record(*key) == raw for key, raw in retained.items())
        assert tx.get_ref("request-" + fresh[2].request_id) == fresh[1].commit
        with pytest.raises(d.NotFoundError):
            tx.get_ref("request-" + chosen.recorded.request_id)
    with d.Repository(path) as repo, repo.read() as tx:
        assert nested(tx, chosen.dag, "attempt") != fresh[2].completion.final_attempt
        assert tx.get_ref(chosen.ref) == chosen.commit


@pytest.mark.parametrize("dimension", ["intent", "binding", "inputs"])
def test_complete_valid_dimension_mismatch_before_any_new_q(double, dimension):
    path = double[0][0]
    second = double[2]
    changes = {}
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, second[2].commit)
        if dimension == "binding":
            entries["double-binding"] = entries["add-binding"]
        elif dimension == "inputs":
            entries["double-inputs"] = entries["add-inputs"]
        changed = tx.put_commit(tx.put_tree(entries), parents=(second[2].commit,))
    if dimension == "intent":
        changes["intent_uri"] = "urn:example:other-purpose"
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="full inputs differ"):
        reuse(double, commit=changed, **changes)
    assert_file_unchanged(path / "data.mdb", before)


def test_valid_packet_without_basis_ancestry_rejects_before_q(double):
    path = double[0][0]
    second = double[2]
    with d.Repository(path) as repo, repo.write() as tx:
        unrelated = tx.put_commit(tx.get_commit(second[2].commit).tree)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="all-parent"):
        reuse(double, commit=unrelated)
    assert_file_unchanged(path / "data.mdb", before)
