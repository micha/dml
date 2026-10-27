"""Valid complete bundles with wrong selected role/history must not touch A."""

import json
from pathlib import Path

import daggerml as d
from daggerml import exchange as ex, transfer
from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

from test_exchange import (
    completed,
    job,
    exchange_runtime,
    literal,
    nested,
    tree,
    initialize,
    prepare,
    change_json,
    assert_main,
)


def clone(tx, oid, *, fields=None, remove=(), root=None):
    dag = tx.get_dag(oid)
    bindings = dict(dag.bindings)
    for key in remove:
        bindings.pop(key, None)
    bindings.update(fields or {})
    return tx.put_dag(root=dag.root if root is None else root, bindings=bindings)


MODES = (
    "pre-parent",
    "pre-extra",
    "pre-missing-request",
    "pre-missing-attempt",
    "request-intent",
    "request-binding",
    "request-inputs",
    "request-root",
    "request-role",
    "request-missing-field",
    "request-extra-field",
    "request-scalar-subdag",
    "request-subdag-scalar",
    "initial-request",
    "initial-ref",
    "initial-scratch",
    "initial-root",
    "final-missing",
    "final-request",
    "final-status",
    "final-root",
    "final-role",
    "final-extra",
    "final-parent-order",
    "final-parent-count",
    "final-unrelated",
    "final-no-publication",
    "publication-parent",
    "publication-unrelated",
    "publication-missing",
    "publication-occurrence",
    "publication-result",
    "outcome-role",
    "outcome-root",
    "outcome-exit",
    "outcome-result",
    "failure-reason",
    "failure-detail",
    "failure-exit",
    "failure-evidence",
    "failure-launch-evidence",
    "cleanup-disposition",
    "cleanup-detail",
    "cleanup-extra-scratch",
    "cleanup-missing-scratch",
    "cleanup-wrong-scratch",
    "diagnostic-fields",
    "diagnostic-count",
    "diagnostic-truncated",
    "diagnostic-data",
    "diagnostic-type",
)


def tamper(workspace, run, mode):
    worker = workspace / "worker.dml"
    with d.Repository(worker) as repo, repo.write() as tx:
        pre_tree = tree(tx, run.context.pre_dispatch)
        final_tree = tree(tx, run.final_commit)
        original_parents = tx.get_commit(run.final_commit).parents
        qname, aname, pname = (
            "request-" + run.request_id,
            "attempt-" + run.attempt_id,
            "publication-" + run.attempt_id,
        )
        q, initial, final = run.context.request, run.context.attempt, run.final_attempt
        wrong = literal(tx, "wrong")
        different_result = tx.put_dag(root=literal(tx, 900))
        if mode.startswith("request-"):
            fields, remove, root = {}, (), None
            if mode in ("request-binding", "request-inputs"):
                fields[mode[8:]] = tx.put_subdag(different_result)
            elif mode == "request-intent":
                fields["intent"] = literal(tx, d.Datum.uri("urn:wrong"))
            elif mode == "request-root":
                root = wrong
            elif mode == "request-role":
                fields["role"] = wrong
            elif mode == "request-missing-field":
                remove = ("intent",)
            elif mode == "request-extra-field":
                fields["extra"] = wrong
            elif mode == "request-scalar-subdag":
                fields["intent"] = tx.put_subdag(different_result)
            else:
                fields["binding"] = wrong
            q = clone(tx, q, fields=fields, remove=remove, root=root)
        initial_fields = {"request": tx.put_subdag(q)}
        initial_root = None
        if mode == "initial-request":
            initial_fields["request"] = tx.put_subdag(different_result)
        if mode == "initial-ref":
            initial_fields["publication-ref"] = wrong
        if mode == "initial-scratch":
            initial_fields["scratch"] = literal(tx, "relative")
        if mode == "initial-root":
            initial_root = wrong
        initial = clone(tx, initial, fields=initial_fields, root=initial_root)
        pre_tree[qname], pre_tree[aname] = q, initial
        if mode == "pre-extra":
            pre_tree["extra"] = different_result
        if mode == "pre-missing-request":
            pre_tree.pop(qname)
        if mode == "pre-missing-attempt":
            pre_tree.pop(aname)
        base = tx.get_commit(run.context.pre_dispatch).parents[0]
        pre = tx.put_commit(
            tx.put_tree(pre_tree),
            parents=(
                (base, run.context.pre_dispatch) if mode == "pre-parent" else (base,)
            ),
        )
        common = {
            key: tx.get_dag(initial).bindings[key]
            for key in ("role", "request", "publication-ref", "scratch")
        }
        final = clone(tx, final, fields=common)
        fields, remove, root = {}, (), None
        if mode == "final-request":
            fields["request"] = tx.put_subdag(different_result)
        if mode == "final-status":
            fields["status"] = wrong
        if mode == "final-root":
            root = wrong
        if mode == "final-role":
            fields["role"] = wrong
        if mode == "final-extra":
            fields["extra"] = wrong
        outcome = nested(tx, final, "outcome")
        cleanup = nested(tx, final, "cleanup")
        if mode.startswith("outcome-"):
            outcome_fields, outcome_root = {}, None
            if mode == "outcome-role":
                outcome_fields["role"] = wrong
            if mode == "outcome-root":
                outcome_root = wrong
            if mode == "outcome-exit":
                outcome_fields["exit-code"] = literal(tx, 1)
            if mode == "outcome-result":
                outcome_fields["result"] = tx.put_subdag(different_result)
            outcome = clone(tx, outcome, fields=outcome_fields, root=outcome_root)
        if mode.startswith("failure-"):
            role = literal(tx, "local-failure-v1")
            failure_fields = {
                "role": role,
                "exit-code": literal(tx, 1),
                "reason": literal(tx, "child-exit"),
                "detail": literal(tx, "recorded failure"),
                "evidence": tx.put_subdag(run.result),
            }
            if mode == "failure-reason":
                failure_fields["reason"] = wrong
            if mode == "failure-detail":
                failure_fields["detail"] = literal(tx, "x" * 4097)
            if mode == "failure-exit":
                failure_fields["exit-code"] = literal(tx, 0)
            if mode == "failure-evidence":
                failure_fields["evidence"] = tx.put_subdag(different_result)
            if mode == "failure-launch-evidence":
                failure_fields["reason"] = literal(tx, "launch")
                failure_fields["exit-code"] = literal(tx, None)
            outcome = tx.put_dag(root=role, bindings=failure_fields)
        if mode.startswith("cleanup-"):
            cleanup_fields = {}
            if mode == "cleanup-disposition":
                cleanup_fields["disposition"] = wrong
            if mode == "cleanup-detail":
                cleanup_fields["detail"] = literal(tx, "x" * 4097)
            if mode == "cleanup-extra-scratch":
                cleanup_fields["scratch"] = literal(tx, run.context.scratch)
            if mode in ("cleanup-missing-scratch", "cleanup-wrong-scratch"):
                cleanup_fields["disposition"] = literal(tx, "failed")
            if mode == "cleanup-wrong-scratch":
                cleanup_fields["scratch"] = literal(tx, "/not-owned")
            cleanup = clone(tx, cleanup, fields=cleanup_fields)
        if mode.startswith("diagnostic-"):
            diagnostic = nested(tx, outcome, "stdout")
            diag_fields, diag_root = {}, None
            if mode == "diagnostic-fields":
                diag_fields["extra"] = wrong
            if mode == "diagnostic-count":
                diag_fields["byte-count"] = literal(tx, -1)
            if mode == "diagnostic-truncated":
                diag_fields["truncated"] = literal(tx, True)
            if mode == "diagnostic-data":
                diag_root = literal(tx, b"x" * 4097)
            if mode == "diagnostic-type":
                diag_fields["byte-count"] = wrong
            diagnostic = clone(tx, diagnostic, fields=diag_fields, root=diag_root)
            outcome = clone(tx, outcome, fields={"stdout": tx.put_subdag(diagnostic)})
        fields.update(outcome=tx.put_subdag(outcome), cleanup=tx.put_subdag(cleanup))
        final = clone(tx, final, fields=fields, remove=remove, root=root)
        publication = final_tree[pname]
        if mode == "publication-occurrence":
            publication = clone(tx, publication, root=wrong)
        if mode == "publication-result":
            publication = clone(
                tx, publication, fields={"result": tx.put_subdag(different_result)}
            )
        publication_tree = dict(pre_tree)
        publication_tree[pname] = publication
        if mode == "publication-missing":
            publication_tree.pop(pname)
        if mode == "publication-unrelated":
            publication_tree["keep"] = different_result
        publication_commit = tx.put_commit(
            tx.put_tree(publication_tree),
            parents=() if mode == "publication-parent" else (pre,),
        )
        final_tree = dict(pre_tree)
        final_tree[aname] = final
        final_tree[pname] = publication
        if mode == "final-missing":
            final_tree.pop(aname)
        if mode == "final-unrelated":
            final_tree["keep"] = different_result
        parents = (pre, publication_commit)
        if mode == "final-parent-order":
            parents = (publication_commit, pre)
        if mode == "final-parent-count":
            parents = (pre, publication_commit, run.final_commit)
        if mode == "final-no-publication":
            parents = (pre,)
            final_tree.pop(pname)
        final_commit = tx.put_commit(tx.put_tree(final_tree), parents=parents)
    (workspace / "output.bundle").write_bytes(
        transfer.export_commit(worker, commit=final_commit)
    )
    change_json(
        workspace / "completion.json",
        final_commit=str(final_commit),
        pre_dispatch=str(pre),
    )


@pytest.mark.parametrize("mode", MODES)
def test_wrong_typed_roles_and_history_reject_entire_packet(completed, mode):
    path, workspace, spec, state, run = completed
    tamper(workspace, run, mode)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="bad")
    # Byte-identical entire immutable store: no return objects, not merely no bad ref.
    assert (path / "data.mdb").read_bytes() == before
    assert_main(path, state)


def test_valid_wrong_selection_completion_not_just_malformed_json(job):
    path, workspace, spec, state = job
    other = workspace.with_name("other")
    other_spec = ex.prepare_exchange(
        path,
        commit=spec.commit,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:other-intent",
        worker_ref="work",
        workspace=other,
    )
    ex.execute_exchange(other)
    (workspace / "output.bundle").write_bytes((other / "output.bundle").read_bytes())
    receipt = json.loads((other / "completion.json").read_bytes())
    receipt["token"] = spec.token
    (workspace / "completion.json").write_text(json.dumps(receipt), encoding="utf-8")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError, match="request selection"):
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="bad")
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize(
    "field,value",
    (
        ("adapter", d.Datum.uri("urn:wrong")),
        ("source", b""),
        ("timeout-ms", 0),
        ("interpreter", "relative"),
    ),
)
def test_malformed_binding_selected_before_workspace(job, field, value):
    path, workspace, spec, state = job
    with d.Repository(path) as repo, repo.write() as tx:
        selected = tree(tx, spec.commit)
        selected["binding"] = clone(
            tx, spec.binding, fields={field: literal(tx, value)}
        )
        commit = tx.put_commit(tx.put_tree(selected), parents=(spec.commit,))
    target = workspace.with_name("bad-binding")
    with pytest.raises(ex.ExchangeError):
        prepare(path, target, commit)
    assert not target.exists()


def test_actual_recorded_failure_cannot_be_relabelled_success(
    tmp_path, exchange_runtime
):
    path, workspace = tmp_path / "a", tmp_path / "worker"
    state = initialize(path, b"raise RuntimeError('genuine recorded failure')")
    spec = prepare(path, workspace, state[0])
    run = ex.execute_exchange(workspace)
    assert run.outcome == "failure" and run.result is None
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        result = tx.put_dag(root=literal(tx, 11))
        role = literal(tx, "local-success-v1")
        false_success = tx.put_dag(
            root=role,
            bindings={
                "role": role,
                "exit-code": literal(tx, 0),
                "result": tx.put_subdag(result),
            },
        )
        false_attempt = clone(
            tx, run.final_attempt, fields={"outcome": tx.put_subdag(false_success)}
        )
        selected = tree(tx, run.final_commit)
        selected["attempt-" + run.attempt_id] = false_attempt
        fabricated = tx.put_commit(
            tx.put_tree(selected), parents=tx.get_commit(run.final_commit).parents
        )
    (workspace / "output.bundle").write_bytes(
        transfer.export_commit(workspace / "worker.dml", commit=fabricated)
    )
    change_json(workspace / "completion.json", final_commit=str(fabricated))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError, match="success does not match"):
        ex.receive_exchange(
            path, workspace=workspace, expected=spec, ref="false-success"
        )
    assert (path / "data.mdb").read_bytes() == before
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        assert tx.get_ref("work") == run.final_commit  # Real failure remains recorded.


@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    st.text(alphabet="abcXYZ012", min_size=1, max_size=30), st.integers(-100000, 100000)
)
def test_generated_extra_history_rejected_before_a(completed, name, value):
    # Each example starts from the same immutable original F, never a previous
    # modified snapshot. A must stay byte-identical across all examples.
    path, workspace, spec, state, run = completed
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        selected = tree(tx, run.final_commit)
        selected["extra-" + name] = tx.put_dag(root=literal(tx, value))
        modified = tx.put_commit(
            tx.put_tree(selected), parents=tx.get_commit(run.final_commit).parents
        )
    (workspace / "output.bundle").write_bytes(
        transfer.export_commit(workspace / "worker.dml", commit=modified)
    )
    change_json(workspace / "completion.json", final_commit=str(modified))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError, match="completion tree"):
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="bad")
    assert (path / "data.mdb").read_bytes() == before
