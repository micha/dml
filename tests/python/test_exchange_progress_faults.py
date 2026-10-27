"""Strict packets, typed-valid wrong P/U history and observation publication faults."""

import json
from pathlib import Path
import runpy
import shutil
import sys

import daggerml as d
from daggerml import exchange as ex, transfer
from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

from test_exchange import (
    job,
    completed,
    exchange_runtime,
    change_json,
    tree,
    scalar,
    initialize,
    prepare,
    literal,
    ROOT,
)
from test_exchange_progress import handle, observation, receive
from test_exchange_records import tamper


@pytest.mark.parametrize("phase", ("initial", "publication"))
@pytest.mark.parametrize(
    "mode",
    (
        "pre-parent",
        "pre-extra",
        "pre-missing-request",
        "pre-missing-attempt",
        "request-intent",
        "request-binding",
        "request-inputs",
        "request-root",
        "request-role",
        "request-extra-field",
        "initial-request",
        "initial-ref",
        "initial-scratch",
        "initial-root",
    ),
)
def test_typed_valid_wrong_initial_basis_no_a_writes(completed, phase, mode):
    path, workspace, spec, state, run = completed
    tamper(workspace, run, mode)
    receipt = json.loads((workspace / "completion.json").read_bytes())
    pre = d.ObjectId.from_hex(receipt["pre_dispatch"])
    final = d.ObjectId.from_hex(receipt["final_commit"])
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        selected = pre if phase == "initial" else tx.get_commit(final).parents[1]
    packet = workspace.parent / "wrong"
    packet.mkdir()
    shutil.copyfile(workspace / "job.json", packet / "job.json")
    (packet / "snapshot.bundle").write_bytes(
        transfer.export_commit(workspace / "worker.dml", commit=selected)
    )
    ex._write_document(
        packet / "observation.json",
        {
            "format": ex.OBSERVATION_FORMAT,
            "token": spec.token,
            "commit": str(spec.commit),
            "phase": phase,
            "selected_commit": str(selected),
            "pre_dispatch": str(pre),
            "request_id": run.request_id,
            "attempt_id": run.attempt_id,
        },
    )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ex.ExchangeError, d.DmlError)):
        receive(completed, packet)
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize(
    "mode",
    (
        "publication-parent",
        "publication-unrelated",
        "publication-missing",
        "publication-occurrence",
    ),
)
def test_wrong_publication_is_not_completion_or_success(completed, mode):
    path, workspace, spec, state, run = completed
    tamper(workspace, run, mode)
    receipt = json.loads((workspace / "completion.json").read_bytes())
    pre = d.ObjectId.from_hex(receipt["pre_dispatch"])
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        final = d.ObjectId.from_hex(receipt["final_commit"])
        tx.update_ref("work", pre)
        tx.update_ref(run.context.publication_ref, tx.get_commit(final).parents[1])
    with pytest.raises(ex.ExchangeError):
        ex.observe_exchange(handle(workspace, spec), packet=workspace.parent / "packet")


@pytest.mark.parametrize("file", ("job.json", "observation.json", "worker-ready.json"))
@pytest.mark.parametrize(
    "data",
    (
        b"{}",
        b"[]",
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{} {}",
        b"[" * 2000,
        b"x" * 8193,
    ),
    ids=(
        "fields",
        "array",
        "duplicate",
        "nan",
        "infinity",
        "utf8",
        "bom",
        "trailing",
        "deep",
        "oversize",
    ),
)
def test_progress_strict_consumed_descriptors(completed, file, data):
    path, workspace, spec, state, run = completed
    selected = observation(completed)
    target = workspace if file == "worker-ready.json" else selected.packet
    (target / file).write_bytes(data)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        if file == "worker-ready.json":
            ex.observe_exchange(
                handle(workspace, spec), packet=workspace.parent / "new"
            )
        else:
            receive(completed, selected.packet)
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize(
    "fault", ("export", "bundle", "job", "receipt", "validation", "cleanup")
)
def test_post_final_retrieval_error_never_returns_done_retains_b(
    completed, monkeypatch, fault
):
    import builtins

    path, workspace, spec, state, run = completed
    packet = workspace.parent / "packet"
    before = (workspace / "worker.dml/data.mdb").read_bytes()
    remaining = []
    if fault == "export":
        # Actual owning profile rejection (scaled total), not fake success.
        monkeypatch.setattr(transfer, "MAX_PACKED_BYTES", 1)
    elif fault == "bundle":
        opening = builtins.open

        def denied(file, *a, **k):
            if Path(file).name == "snapshot.bundle":
                raise PermissionError("bundle denied")
            return opening(file, *a, **k)

        monkeypatch.setattr(builtins, "open", denied)
    elif fault in ("job", "receipt"):
        replacing = ex.os.replace

        def denied(source, target):
            if Path(target).name == (
                "job.json" if fault == "job" else "observation.json"
            ):
                raise PermissionError("descriptor denied")
            return replacing(source, target)

        monkeypatch.setattr(ex.os, "replace", denied)
    elif fault == "validation":
        importing = transfer.import_commit

        def denied(repository, *a, **k):
            if Path(repository).name == "validation.dml":
                raise OSError("validation denied")
            return importing(repository, *a, **k)

        monkeypatch.setattr(transfer, "import_commit", denied)
    else:
        removing = shutil.rmtree

        def denied(directory, *a, **k):
            remaining.append(directory)
            raise PermissionError("scratch cleanup denied")

        monkeypatch.setattr(ex.shutil, "rmtree", denied)
    try:
        with pytest.raises((OSError, transfer.TransferError)):
            ex.observe_exchange(handle(workspace, spec), packet=packet)
    finally:
        if fault == "cleanup":
            for directory in remaining:
                removing(directory)
    assert (workspace / "worker.dml/data.mdb").read_bytes() == before
    assert not (packet / "observation.json").exists()
    assert packet.exists() == (fault in ("bundle", "job", "receipt"))


def test_receiver_validation_cleanup_failure_prevents_any_a_put(completed, monkeypatch):
    path, workspace, spec, state, run = completed
    selected = observation(completed)
    before = (path / "data.mdb").read_bytes()
    remaining = []
    removing = shutil.rmtree
    importing = transfer.import_commit

    def imported(repository, *args, **kwargs):
        assert Path(repository) != path, "cleanup failure must precede A import"
        return importing(repository, *args, **kwargs)

    def denied(directory, *args, **kwargs):
        remaining.append(directory)
        raise PermissionError("receiver scratch cleanup denied")

    with monkeypatch.context() as guard:
        guard.setattr(transfer, "import_commit", imported)
        guard.setattr(ex.shutil, "rmtree", denied)
        with pytest.raises(PermissionError):
            receive(completed, selected.packet)
    assert len(remaining) == 1 and Path(remaining[0]).exists()
    removing(remaining[0])
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
def test_valid_swapped_same_selection_other_token_progress_packet(completed, phase):
    path, workspace, spec, state, run = completed
    selected = observation(completed, phase, "original")
    second = workspace.parent / "second"
    spec2 = prepare(path, second, spec.commit)
    run2 = ex.execute_exchange(second)
    other = observation((path, second, spec2, state, run2), phase, "other")
    assert (
        spec.token != spec2.token
        and spec.binding == spec2.binding
        and spec.inputs == spec2.inputs
    )
    # Structurally valid P/U/F from the matching independent job, not fabricated
    # malformed ID/token. Keep first job, swap second receipt + entire bundle.
    for name in ("observation.json", "snapshot.bundle"):
        shutil.copyfile(other.packet / name, selected.packet / name)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError, match="token/base"):
        receive(completed, selected.packet)
    assert (path / "data.mdb").read_bytes() == before


def test_missing_partial_or_existing_packets(completed):
    selected = observation(completed)
    with pytest.raises(FileExistsError):
        ex.observe_exchange(handle(completed[1], completed[2]), packet=selected.packet)
    (selected.packet / "snapshot.bundle").write_bytes(b"{")
    with pytest.raises(transfer.TransferError):
        receive(completed, selected.packet)
    (selected.packet / "observation.json").unlink()
    with pytest.raises(FileNotFoundError):
        receive(completed, selected.packet)
    with pytest.raises(TypeError):
        ex.receive_observation(
            completed[0], packet=selected.packet, expected=None, ref="received"
        )
    with pytest.raises(ex.ExchangeError):
        ex.receive_observation(
            completed[0], packet=selected.packet, expected=completed[2], ref="bad/name"
        )


def test_packet_job_mismatch_root_phase_swap_before_a(completed):
    path, workspace, spec, state, run = completed
    final = observation(completed, "completion", "final")
    initial = observation(completed, "initial", "initial")
    original = (path / "data.mdb").read_bytes()
    (initial.packet / "snapshot.bundle").write_bytes(
        (final.packet / "snapshot.bundle").read_bytes()
    )
    with pytest.raises(ex.ExchangeError, match="root mismatch"):
        receive(completed, initial.packet)
    change_json(final.packet / "job.json", token="0" * 32)
    with pytest.raises(ex.ExchangeError, match="expected"):
        receive(completed, final.packet)
    assert (path / "data.mdb").read_bytes() == original


def test_final_head_parentless_and_wrong_initial_selected_root(completed):
    path, workspace, spec, state, run = completed
    selected = observation(completed, "publication")
    change_json(selected.packet / "observation.json", phase="initial")
    with pytest.raises(ex.ExchangeError, match="initial root"):
        receive(completed, selected.packet)
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        parentless = tx.put_commit(tx.get_commit(run.final_commit).tree)
        tx.update_ref("work", parentless)
    with pytest.raises(ex.ExchangeError, match="no pre-dispatch parent"):
        ex.observe_exchange(
            handle(workspace, spec), packet=workspace.parent / "missing-parent"
        )


def test_true_production_record_overflow_after_recorded_f_reaped(
    tmp_path, exchange_runtime
):
    source = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 n=t.put_literal(t.put_datum(b'x'*(4*1024*1024+1)))
 publish_result(t,c,t.put_dag(root=n))
"""
    path, workspace = tmp_path / "a", tmp_path / "work"
    state = initialize(path, source)
    spec = prepare(path, workspace, state[0])
    assert transfer.MAX_RECORD_BYTES == 4 * 1024 * 1024
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(transfer.TransferError, match="packed record exceeds"):
        ex.execute_exchange(workspace)
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        final = tx.get_ref("work")
        attempt = next(
            v for k, v in tree(tx, final).items() if k.startswith("attempt-")
        )
        assert scalar(tx, attempt, "status") == "done"
        outcome = tx.get_node(tx.lookup_node(attempt, "outcome")).dag
        cleanup = tx.get_node(tx.lookup_node(attempt, "cleanup")).dag
        assert scalar(tx, outcome, "role") == "local-success-v1"
        assert scalar(tx, cleanup, "disposition") == "ok"
        result = tx.get_node(tx.lookup_node(outcome, "result")).dag
        datum = tx.get_node(tx.get_dag(result).root).datum
        assert len(tx.get_record("datum", datum)) > transfer.MAX_RECORD_BYTES
    # Runner's synchronous return path recorded F only after actual child wait/reap
    # and cleanup. Observe independently sees F but cannot retrieve a valid packet.
    frozen_b = (workspace / "worker.dml/data.mdb").read_bytes()
    with pytest.raises(transfer.TransferError, match="packed record exceeds"):
        ex.observe_exchange(handle(workspace, spec), packet=tmp_path / "packet")
    assert not (tmp_path / "packet").exists()
    assert not (workspace / "completion.json").exists()
    assert (workspace / "worker.dml/data.mdb").read_bytes() == frozen_b
    assert (path / "data.mdb").read_bytes() == before
    with pytest.raises(ex.ExchangeError):
        ex.start_exchange(handle(workspace, spec))
    with pytest.raises(ex.ExchangeError):
        ex.execute_exchange(workspace)


def test_worker_module_main_guard_measured(job, monkeypatch):
    import daggerml.exchange as exchange

    called = []
    monkeypatch.setattr(
        exchange, "execute_exchange", lambda value: called.append(value)
    )
    monkeypatch.setattr(sys, "argv", ["worker", str(job[1])])
    monkeypatch.delitem(sys.modules, "daggerml.exchange_worker", raising=False)
    runpy.run_module("daggerml.exchange_worker", run_name="__main__")
    assert called == [str(job[1])]


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    phase=st.sampled_from(("initial", "publication")),
    value=st.integers(-10000, 10000),
    name=st.text(alphabet="abc012XYZ", min_size=1, max_size=20),
)
def test_generated_typed_wrong_progress_tree(completed, phase, value, name):
    path, workspace, spec, state, run = completed
    worker = workspace / "worker.dml"
    with d.Repository(worker) as repo, repo.write() as tx:
        pre_tree = tree(tx, run.context.pre_dispatch)
        pre_tree["extra-" + name] = tx.put_dag(root=literal(tx, value))
        wrong_pre = tx.put_commit(tx.put_tree(pre_tree), parents=(spec.commit,))
        tx.update_ref("work", wrong_pre)
        tx.update_ref(run.context.publication_ref, wrong_pre)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        ex.observe_exchange(handle(workspace, spec), packet=workspace.parent / "never")
    assert (path / "data.mdb").read_bytes() == before
