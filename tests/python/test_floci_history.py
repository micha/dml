"""Actual native history/new-A-put oracles behind privately substituted object IO."""

from pathlib import Path

import daggerml as d
from daggerml import (
    exchange as ex,
    floci as f,
    floci_http as h,
    floci_worker as worker,
    transfer,
)
import pytest

from test_binding_failures import core
from test_caller_requests import caller_completed, caller_job, assert_file_unchanged
from test_caller_request_history import (
    test_complete_matching_wrong_q_rejects_before_a as wrong_q,
)
from test_exchange import exchange_runtime, typed_oracle
from test_exchange_progress import _fresh_absence
from test_exchange_process import track_new_puts
from test_records_hypothesis import run_driver
from test_floci import service, stage


def selected(case, service, phase):
    path, workspace, expected, _, run = case
    job = f.submit_floci_exchange(stage(case, service), timeout_ms=10000)
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        if phase != "completion":
            tx.update_ref(expected.worker_ref, run.context.pre_dispatch)
            if phase == "initial":
                tx.update_ref(run.context.publication_ref, run.context.pre_dispatch)
    worker._publish(job, ex.ExchangeHandle(workspace, expected))
    return job, f.observe_floci_job(
        job, packet=path.parent / "packet", timeout_ms=10000
    )


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
@pytest.mark.parametrize("fault", ["ref", "raw-ref", "commit"])
def test_returned_packet_genuinely_new_actual_a_puts_before_late_rollback(
    caller_completed, service, core, phase, fault
):
    path, workspace, expected, state, _ = caller_completed
    _, got = selected(caller_completed, service, phase)
    baseline = typed_oracle(path, (expected.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (got.snapshot.commit,))
    if fault == "ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("received", state[3])
    elif fault == "raw-ref":
        run_driver("raw-write", str(path), "refs/heads/received", data=b"bad")
    before = (path / "data.mdb").read_bytes()
    with track_new_puts(
        path, baseline, core if fault == "commit" else None
    ) as successful:
        with pytest.raises((d.DmlError, transfer.RefConflictError)):
            ex.receive_observation(
                path, packet=got.packet, expected=expected, ref="received"
            )
    assert (
        successful
    ), "successful genuinely new actual-A puts/readback, not scratch/Q rows"
    _fresh_absence(path, baseline, returned)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
@pytest.mark.parametrize(
    "mode", ["foreign-cq", "association", "same-spelling", "missing-q"]
)
def test_typed_complete_wrong_matching_q_rejects_before_success_or_a(
    caller_completed, service, phase, mode
):
    wrong_q(caller_completed, phase, mode)
    path, workspace, expected, _, _ = caller_completed
    packet = path.parent / "wrong-packet"
    job = f.submit_floci_exchange(stage(caller_completed, service), timeout_ms=10000)
    files = tuple((name, (packet / name).read_bytes()) for name in h.PACKET_FILES)
    import json
    from types import SimpleNamespace

    receipt = json.loads((packet / "observation.json").read_bytes())
    snapshot = SimpleNamespace(commit=d.ObjectId.from_hex(receipt["selected_commit"]))
    for name, data in files:
        service.objects[
            h.object_path(
                job.remote,
                expected.token,
                "snapshots/" + str(snapshot.commit) + "/" + name,
            )
        ] = data
    service.objects[
        h.object_path(job.remote, expected.token, "phases/" + phase + ".json")
    ] = f._phase_manifest(job, phase, snapshot, files)
    before = (path / "data.mdb").read_bytes()
    target = path.parent / "wrong-observed"
    with pytest.raises((ex.ExchangeError, d.DmlError)) as error:
        f.observe_floci_job(job, packet=target, timeout_ms=10000)
    if mode == "association":
        assert "initial attempt association" in str(error.value)
    assert not target.exists()
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
@pytest.mark.parametrize("boundary", ["receive-pre", "receive-post"])
def test_retrieved_packets_actual_storage_commit_loss(
    caller_completed, service, phase, boundary
):
    from test_exchange_progress_process import stopped
    from test_exchange_process import fresh_state

    path, workspace, expected, state, _ = caller_completed
    _, got = selected(caller_completed, service, phase)
    baseline = typed_oracle(path, (expected.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (got.snapshot.commit,))
    stopped(caller_completed, boundary, got.packet)
    fresh_state(path, baseline, returned, boundary == "receive-post")
    imported = ex.receive_observation(
        path, packet=got.packet, expected=expected, ref="received"
    )
    assert imported.commit == got.snapshot.commit
    fresh_state(path, baseline, returned, True)


def test_returned_real_small_map_failure_after_actual_new_a_puts(
    tmp_path, service, exchange_runtime
):
    from test_caller_requests import record, prepare_recorded
    from test_exchange import initialize
    from test_exchange_process import fresh_state

    source = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 early=t.put_literal(t.put_datum('genuinely new prefix'))
 large=t.put_literal(t.put_datum(b'x'*2097152))
 publish_result(t,c,t.put_dag(root=early,bindings={'large':large}))
"""
    path, workspace = tmp_path / "a", tmp_path / "input"
    state = initialize(path, source)
    recorded = record(path, state[0])
    expected = prepare_recorded(path, workspace, recorded)
    run = ex.execute_exchange(workspace)
    _, got = selected((path, workspace, expected, state, run), service, "completion")
    baseline = typed_oracle(path, (expected.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (got.snapshot.commit,))
    before = (path / "data.mdb").read_bytes()
    with track_new_puts(path, baseline) as successful:
        with pytest.raises(d.MapFullError):
            ex.receive_observation(
                path,
                packet=got.packet,
                expected=expected,
                ref="received",
                map_size=1048576,
            )
    assert successful
    fresh_state(path, baseline, returned, False)
    with d.Repository(path):
        pass  # Restore comparable physical map extent, not research state.
    assert_file_unchanged(path / "data.mdb", before)
    assert (
        ex.receive_observation(
            path, packet=got.packet, expected=expected, ref="received", map_size=8388608
        ).commit
        == got.snapshot.commit
    )
    fresh_state(path, baseline, returned, True)


def test_f_arrival_after_selected_u_manifest_cannot_retarget_owned_bytes(
    caller_completed, service, monkeypatch
):
    path, workspace, expected, _, run = caller_completed
    job = f.submit_floci_exchange(stage(caller_completed, service), timeout_ms=10000)
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        tx.update_ref(expected.worker_ref, run.context.pre_dispatch)
    handle = ex.ExchangeHandle(workspace, expected)
    worker._publish(job, handle)
    u = d.ObjectId.from_hex(
        __import__("json").loads(
            service.objects[
                h.object_path(job.remote, expected.token, "phases/publication.json")
            ]
        )["selected_commit"]
    )
    old_u = typed_oracle(workspace / "worker.dml", (u,))
    original = h.get_object
    advanced = []

    def get(*args):
        if args[3] == "snapshots/" + str(u) + "/job.json" and not advanced:
            with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
                tx.update_ref(expected.worker_ref, run.final_commit)
            worker._publish(job, handle)
            advanced.append(True)
        return original(*args)

    monkeypatch.setattr(h, "get_object", get)
    got = f.observe_floci_job(job, packet=path.parent / "selected-u", timeout_ms=10000)
    assert advanced and got.phase == "publication" and got.snapshot.commit == u
    validation = path.parent / "u-validation"
    with d.Repository(validation, create=True):
        pass
    transfer.import_commit(validation, (got.packet / "snapshot.bundle").read_bytes())
    assert typed_oracle(validation, (u,)) == old_u
    newer = f.observe_floci_job(job, packet=path.parent / "new-f", timeout_ms=10000)
    assert newer.phase == "completion" and newer.snapshot.commit == run.final_commit
    assert ex.read_observation(got.packet, expected=expected).lifecycle == "working"
