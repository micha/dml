"""Meaningful complete-valid matching, packet authority and failure gates."""

from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged
from test_composed_execution import producer, basis, execute, DOUBLE
from test_exchange import exchange_runtime, literal, nested, scalar, tree, typed_oracle
from test_exchange_records import clone
from test_explicit_reuse import app, double, reuse
from test_records_hypothesis import run_driver


@pytest.mark.parametrize(
    "dimension",
    [
        "source",
        "interpreter",
        "timeout",
        "factor",
        "factor-type",
        "endpoint",
        "gate",
        "artifacts",
        "producer",
    ],
)
def test_full_binding_input_changes_even_equal_scalar_result_reject_before_q(
    double, dimension
):
    path, base, first = double[0]
    second = double[2]
    alternate = (
        execute(path, base, "alternate-producer") if dimension == "producer" else None
    )
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, second[2].commit)
        if dimension in ("source", "interpreter", "timeout"):
            binding = tx.get_dag(second[1].binding)
            source = scalar(tx, second[1].binding, "source")
            interpreter = scalar(tx, second[1].binding, "interpreter")
            timeout = scalar(tx, second[1].binding, "timeout-ms")
            entries["double-binding"] = local.put_local_binding(
                tx,
                source=(
                    source + b"\n# declared alternative\n"
                    if dimension == "source"
                    else source
                ),
                interpreter=(
                    interpreter + ".unavailable"
                    if dimension == "interpreter"
                    else interpreter
                ),
                timeout_ms=timeout + 1 if dimension == "timeout" else timeout,
            )
        else:
            fields = dict(tx.get_dag(second[1].inputs).bindings)
            if dimension == "producer":
                assert alternate[2].result == first[2].result
                fields["producer"] = tx.put_subdag(
                    alternate[2].completion.final_attempt
                )
            else:
                key, value = {
                    "factor": ("factor", 3),
                    "factor-type": ("factor", True),
                    "endpoint": ("endpoint", "http://elsewhere:4566"),
                    "gate": ("gate", "another/declared-gate"),
                    "artifacts": ("artifacts", b"another-declaration"),
                }[dimension]
                fields[key] = literal(tx, value)
            entries["double-inputs"] = tx.put_dag(root=fields["value"], bindings=fields)
        changed = tx.put_commit(tx.put_tree(entries), parents=(second[2].commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="full inputs differ"):
        reuse(double, commit=changed)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("phase", ["initial", "publication"])
def test_p_u_cannot_create_reuse_q_w(double, phase):
    path = double[0][0]
    progress = execute(
        path, double[1].commit, phase, "double-binding", "double-inputs", phase=phase
    )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="successful recorded completion"):
        reuse(double, historical_packet=progress[0], historical_expected=progress[1])
    assert_file_unchanged(path / "data.mdb", before)


def test_failed_f_evidence_84_cannot_authorize_new_request(double):
    path = double[0][0]
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, double[1].commit)
        entries["double-binding"] = local.put_local_binding(
            tx,
            source=DOUBLE + b"\nimport sys;sys.exit(23)\n",
            interpreter=sys.executable,
            timeout_ms=10000,
        )
        base = tx.put_commit(tx.put_tree(entries), parents=(double[1].commit,))
    failed = execute(path, base, "failure", "double-binding", "double-inputs")
    assert (
        failed[2].completion.outcome == "failure"
        and failed[2].completion.evidence == double[2][2].result
    )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="successful recorded completion"):
        reuse(
            double,
            commit=failed[2].commit,
            historical_packet=failed[0],
            historical_expected=failed[1],
        )
    assert_file_unchanged(path / "data.mdb", before)


def test_missing_unknown_bootstrap_and_forged_dataclass_no_authority(double):
    path = double[0][0]
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(FileNotFoundError):
        reuse(double, historical_packet=path.parent / "unknown-bootstrap")
    with pytest.raises(TypeError):
        reuse(double, historical_packet=replace(double[2][2], lifecycle="done"))
    assert_file_unchanged(path / "data.mdb", before)


def test_another_matching_success_is_explicitly_selectable_not_silent_witness_swap(
    double,
):
    path = double[0][0]
    second = double[2]
    alternate = execute(
        path, double[1].commit, "alternate-double", "double-binding", "double-inputs"
    )
    assert alternate[2].result == second[2].result
    assert alternate[2].completion.final_attempt != second[2].completion.final_attempt
    chosen = reuse(
        double,
        commit=alternate[2].commit,
        historical_packet=alternate[0],
        historical_expected=alternate[1],
    )
    assert chosen.attempt == alternate[2].completion.final_attempt
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        reuse(double, historical_packet=alternate[0])
    assert_file_unchanged(path / "data.mdb", before)


def test_success_cleanup_failure_policy_preserves_original_disposition(
    double, monkeypatch
):
    path = double[0][0]
    original = shutil.rmtree

    def denied(path, *a, **k):
        if Path(path).name.startswith("dml-local-"):
            raise PermissionError("private known cleanup failure")
        return original(path, *a, **k)

    with monkeypatch.context() as guard:
        guard.setattr(shutil, "rmtree", denied)
        selected = execute(
            path, double[1].commit, "cleanup-double", "double-binding", "double-inputs"
        )
    try:
        assert (
            selected[2].completion.cleanup == "failed"
            and selected[2].completion.outcome == "success"
        )
        old = typed_oracle(path, (selected[2].commit,))
        got = reuse(
            double,
            commit=selected[2].commit,
            historical_packet=selected[0],
            historical_expected=selected[1],
        )
        assert got.attempt == selected[2].completion.final_attempt
        with d.Repository(path) as repo, repo.read() as tx:
            assert all(tx.get_record(*key) == raw for key, raw in old.items())
    finally:
        original(selected[3].context.scratch)


def test_complete_wrong_t_to_matching_q_packet_rejected_by_public_authority(double):
    path = double[0][0]
    second = double[2]
    run, worker = second[3], second[4] / "worker.dml"
    with d.Repository(worker) as repo, repo.write() as tx:
        other = local.put_local_request(
            tx,
            request_id="q-" + "e" * 32,
            intent_uri=second[1].intent_uri,
            binding=second[1].binding,
            inputs=second[1].inputs,
        )
        initial = clone(
            tx, run.context.attempt, fields={"request": tx.put_subdag(other)}
        )
        entries = tree(tx, run.context.pre_dispatch)
        entries[run.context.publication_ref] = initial
        pre = tx.put_commit(tx.put_tree(entries), parents=(second[1].commit,))
        assert entries["request-" + run.request_id] == second[1].request
        entries["publication-" + run.attempt_id] = tree(tx, run.final_commit)[
            "publication-" + run.attempt_id
        ]
        publication = tx.put_commit(tx.put_tree(entries), parents=(pre,))
        entries[run.context.publication_ref] = clone(
            tx, run.final_attempt, fields={"request": tx.put_subdag(other)}
        )
        final = tx.put_commit(tx.put_tree(entries), parents=(pre, publication))
    packet = path.parent / "wrong-association"
    shutil.copytree(second[0], packet)
    (packet / "snapshot.bundle").write_bytes(
        transfer.export_commit(worker, commit=final)
    )
    validation = path.parent / "complete-wrong-validation"
    with d.Repository(validation, create=True):
        pass
    transfer.import_commit(validation, (packet / "snapshot.bundle").read_bytes())
    assert typed_oracle(validation, (final,)) == typed_oracle(worker, (final,))
    receipt = json.loads((packet / "observation.json").read_bytes())
    receipt.update(selected_commit=str(final), pre_dispatch=str(pre))
    (packet / "observation.json").write_text(json.dumps(receipt), encoding="utf-8")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError, match="initial attempt association"):
        reuse(double, historical_packet=packet)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_native_damaged_composite_only_descendant_rejects_before_q(double, damage):
    path = double[0][0]
    with d.Repository(path) as repo, repo.write() as tx:
        absent = tx.put_datum("composite-only-deep-child")
        inner = tx.put_datum(d.Datum.list([absent]))
        outer = tx.put_datum(d.Datum.list([inner]))
        entries = tree(tx, double[2][2].commit)
        entries["composite"] = tx.put_dag(root=tx.put_literal(outer))
        base = tx.put_commit(tx.put_tree(entries), parents=(double[2][2].commit,))
        child_bytes = tx.get_record("datum", absent)
    if damage == "missing":
        run_driver("raw-delete", str(path), "objects/datums/" + str(absent))
    else:
        # Complete valid STRING record under the WRONG claimed content ID; native
        # integrity check must reject this deep, composite-only reached leaf.
        run_driver(
            "raw-write",
            str(path),
            "objects/datums/" + str(absent),
            data=child_bytes[:-1] + b"X",
        )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(d.DmlError):
        reuse(double, commit=base)
    assert_file_unchanged(path / "data.mdb", before)


def test_unreturnable_genuine_f_original_packed_profile_does_not_create_q(double):
    path = double[0][0]
    # A real new successful computation publishes >4MiB datum; unchanged runner
    # records F, then export rejects. No valid F packet exists to reuse.
    source = DOUBLE.replace(
        b"bindings={'result':n}",
        b"bindings={'result':n,'large':t.put_literal(t.put_datum(b'x'*(4*1024*1024+1)))}",
    )
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, double[1].commit)
        entries["double-binding"] = local.put_local_binding(
            tx, source=source, interpreter=sys.executable, timeout_ms=10000
        )
        base = tx.put_commit(tx.put_tree(entries), parents=(double[1].commit,))
    recorded = ex.record_exchange_request(
        path,
        commit=base,
        binding_name="double-binding",
        inputs_name="double-inputs",
        intent_uri="urn:example:double",
        ref="overflow-submission",
    )
    workspace = path.parent / "overflow-input"
    expected = ex.prepare_exchange(
        path,
        commit=recorded.commit,
        request=recorded.request,
        binding_name="double-binding",
        inputs_name="double-inputs",
        intent_uri=recorded.intent_uri,
        worker_ref="work",
        workspace=workspace,
    )
    with pytest.raises(transfer.TransferError, match="packed record"):
        ex.execute_exchange(workspace)
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        final = tx.get_ref("work")
        attempts = [
            v
            for n, v in tree(tx, final).items()
            if n.startswith("attempt-") and n not in tree(tx, expected.commit)
        ]
        assert len(attempts) == 1 and scalar(tx, attempts[0], "status") == "done"
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(FileNotFoundError):
        reuse(
            double,
            historical_packet=workspace / "no-successful-F-packet",
            historical_expected=expected,
        )
    assert_file_unchanged(path / "data.mdb", before)
