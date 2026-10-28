"""Progress transport preserves owning exact-Q/history and actual A atomicity."""

from pathlib import Path
import json
import shutil

import daggerml as d
from daggerml import exchange as ex, ssh, ssh_worker as worker, transfer
import pytest

from test_binding_failures import core
from test_caller_requests import caller_job, caller_completed, assert_file_unchanged
from test_caller_request_history import (
    test_complete_matching_wrong_q_rejects_before_a as wrong_q,
)
from test_exchange import exchange_runtime, typed_oracle
from test_exchange_progress import observation, _fresh_absence
from test_exchange_records import MODES, tamper
from test_exchange_process import track_new_puts
from test_records_hypothesis import run_driver
from test_ssh import transport, stage, local_workspace, worker_host_path, remote


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
@pytest.mark.parametrize(
    "mode", ["foreign-cq", "association", "same-spelling", "missing-q"]
)
def test_public_inspector_wrong_complete_q_and_transport_no_packet(
    caller_completed, phase, mode, monkeypatch
):
    wrong_q(caller_completed, phase, mode)
    path, workspace, spec, _, _ = caller_completed
    packet = path.parent / "wrong-packet"
    with pytest.raises((ex.ExchangeError, d.DmlError)) as error:
        ex.read_observation(packet, expected=spec)
    if mode == "association":
        assert "initial attempt association" in str(error.value)
    job = ssh.SSHExchange(remote(path.parent), spec, path.parent / "control")
    bodies = tuple(
        (packet / name).read_bytes()
        for name in ("job.json", "observation.json", "snapshot.bundle")
    )
    monkeypatch.setattr(ssh, "_invoke", lambda *a: ("observation", bodies))
    before = (path / "data.mdb").read_bytes()
    target = path.parent / "host-packet"
    with pytest.raises((ex.ExchangeError, d.DmlError)):
        ssh.observe_ssh_exchange(job, packet=target, timeout_ms=1)
    assert not target.exists()
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("mode", MODES)
def test_readonly_inspector_retains_final_role_history_rejection(
    caller_completed, mode
):
    path, workspace, spec, _, run = caller_completed
    tamper(workspace, run, mode)
    receipt = json.loads((workspace / "completion.json").read_bytes())
    packet = path.parent / "packet"
    packet.mkdir()
    shutil.copyfile(workspace / "job.json", packet / "job.json")
    (packet / "snapshot.bundle").write_bytes((workspace / "output.bundle").read_bytes())
    receipt["format"] = ex.OBSERVATION_FORMAT
    receipt["phase"] = "completion"
    receipt["selected_commit"] = receipt.pop("final_commit")
    (packet / "observation.json").write_text(json.dumps(receipt))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        ex.read_observation(packet, expected=spec)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
@pytest.mark.parametrize("fault", ["ref", "raw-ref", "commit"])
def test_ssh_observed_packet_actual_new_a_puts_late_rollback(
    caller_job, transport, core, phase, fault
):
    path, _, spec, state, _ = caller_job
    job = stage(caller_job, transport)
    ssh.execute_ssh_exchange(job, timeout_ms=10000)
    worker_path = local_workspace(job) / "worker.dml"
    with d.Repository(worker_path) as repo, repo.write() as tx:
        final = tx.get_ref("work")
        pre, publication = tx.get_commit(final).parents
        aid = next(
            name
            for name in tx.get_tree(tx.get_commit(pre).tree)
            if name.startswith("attempt-")
        )
        if phase != "completion":
            tx.update_ref("work", pre)
            if phase == "initial":
                tx.update_ref(aid, pre)
    got = ssh.observe_ssh_exchange(job, packet=path.parent / "packet", timeout_ms=10000)
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(worker_path, (got.snapshot.commit,))
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
                path, packet=got.packet, expected=spec, ref="received"
            )
    assert successful, "genuinely new actual A puts/readback required"
    _fresh_absence(path, baseline, returned)
    assert_file_unchanged(path / "data.mdb", before)


def observed_case(caller_job, transport, monkeypatch, phase):
    path, _, spec, state, _ = caller_job
    handle = stage(caller_job, transport)
    captured = []
    execute = ex.execute_exchange

    def run(*args, **kwargs):
        result = execute(*args, **kwargs)
        captured.append(result)
        return result

    with monkeypatch.context() as guard:
        guard.setattr(ex, "execute_exchange", run)
        ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    run = captured[0]
    workspace = local_workspace(handle)
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        if phase != "completion":
            tx.update_ref("work", run.context.pre_dispatch)
            if phase == "initial":
                tx.update_ref(run.context.publication_ref, run.context.pre_dispatch)
    selected = ssh.observe_ssh_exchange(
        handle, packet=path.parent / "packet", timeout_ms=10000
    )
    return selected, (path, workspace, spec, state, run)


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
@pytest.mark.parametrize("boundary", ["receive-pre", "receive-post"])
def test_ssh_observed_actual_a_storage_loss(
    caller_job, transport, monkeypatch, phase, boundary
):
    from test_exchange_process import fresh_state
    from test_exchange_progress_process import stopped

    selected, case = observed_case(caller_job, transport, monkeypatch, phase)
    path, workspace, spec, state, run = case
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (selected.snapshot.commit,))
    stopped(case, boundary, selected.packet)
    fresh_state(path, baseline, returned, boundary == "receive-post")
    # Only complete packet + independent expected; receive retry never invokes SSH.
    with monkeypatch.context() as guard:
        guard.setattr(
            ssh, "_invoke", lambda *a, **k: pytest.fail("no computational retry")
        )
        got = ex.receive_observation(
            path, packet=selected.packet, expected=spec, ref="received"
        )
        assert got.commit == selected.snapshot.commit
    fresh_state(path, baseline, returned, True)


def test_ssh_observed_real_map_full_after_actual_new_puts(
    tmp_path, transport, exchange_runtime, monkeypatch
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
    spec = prepare_recorded(path, workspace, recorded)
    selected, case = observed_case(
        (path, workspace, spec, state, recorded), transport, monkeypatch, "completion"
    )
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(case[1] / "worker.dml", (selected.snapshot.commit,))
    before = (path / "data.mdb").read_bytes()
    with track_new_puts(path, baseline) as successful:
        with pytest.raises(d.MapFullError):
            ex.receive_observation(
                path,
                packet=selected.packet,
                expected=spec,
                ref="received",
                map_size=1048576,
            )
    assert successful
    fresh_state(path, baseline, returned, False)
    with d.Repository(path):
        pass  # comparable original physical map extent, no research-state writes
    assert_file_unchanged(path / "data.mdb", before)
    assert (
        ex.receive_observation(
            path,
            packet=selected.packet,
            expected=spec,
            ref="received",
            map_size=8388608,
        ).commit
        == selected.snapshot.commit
    )
    fresh_state(path, baseline, returned, True)
    assert len(transport[1]) == 3
