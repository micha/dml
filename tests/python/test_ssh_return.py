"""Fetched candidates retain unchanged authoritative exact-Q atomic receive boundary.

Transport here is a private in-process substitute; actual child/A storage are real.
"""

import json
from pathlib import Path

import daggerml as d
from daggerml import exchange as ex, ssh, transfer
import pytest

from test_binding_failures import core
from test_caller_requests import (
    caller_job,
    record,
    prepare_recorded,
    assert_file_unchanged,
)
from test_exchange import exchange_runtime, initialize, typed_oracle, assert_main
from test_exchange_process import track_new_puts, fresh_state, terminated_at_barrier
from test_exchange_progress import _fresh_absence
from test_records_hypothesis import run_driver
from test_ssh import transport, stage, local_workspace, worker_host_path


def fetched(caller_job, transport):
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    packet = ssh.fetch_ssh_exchange(
        handle, packet=handle.control.with_name("packet"), timeout_ms=10000
    )
    root = d.ObjectId.from_hex(
        json.loads((packet / "completion.json").read_bytes())["final_commit"]
    )
    return packet, root, local_workspace(handle) / "worker.dml"


@pytest.mark.parametrize("fault", ["ref", "raw-ref", "commit"])
def test_fetched_actual_new_a_puts_late_whole_batch_abort(
    caller_job, transport, core, fault
):
    path, workspace, spec, state, recorded = caller_job
    packet, root, worker = fetched(caller_job, transport)
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(worker, (root,))
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
            ex.receive_exchange(path, workspace=packet, expected=spec, ref="received")
    assert successful, "genuinely new actual-A successful put/readback required"
    assert_file_unchanged(path / "data.mdb", before)
    _fresh_absence(path, baseline, returned)
    with d.Repository(path) as repo, repo.read() as tx:
        if fault == "ref":
            assert tx.get_ref("received") == state[3]
        elif fault == "raw-ref":
            with pytest.raises(d.IntegrityError):
                tx.get_ref("received")
        else:
            with pytest.raises(d.NotFoundError):
                tx.get_ref("received")
    assert_main(path, state)


def test_fetched_real_map_full_new_a_puts_explicit_whole_receive_retry(
    tmp_path, transport, exchange_runtime
):
    path, workspace = tmp_path / "a", tmp_path / "prepared"
    source = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 early=t.put_literal(t.put_datum('new prefix'))
 large=t.put_literal(t.put_datum(b'x'*2097152))
 publish_result(t,c,t.put_dag(root=early,bindings={'large':large}))
"""
    state = initialize(path, source)
    recorded = record(path, state[0], "submission")
    spec = prepare_recorded(path, workspace, recorded)
    packet, root, worker = fetched((path, workspace, spec, state, recorded), transport)
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(worker, (root,))
    before = (path / "data.mdb").read_bytes()
    with track_new_puts(path, baseline) as successful:
        with pytest.raises(d.MapFullError):
            ex.receive_exchange(
                path, workspace=packet, expected=spec, ref="received", map_size=1048576
            )
    assert successful
    fresh_state(path, baseline, returned, False)
    # Restore comparable physical extent before exact raw-byte rollback assertion.
    with d.Repository(path):
        pass
    assert_file_unchanged(path / "data.mdb", before)
    check = ex.receive_exchange(
        path, workspace=packet, expected=spec, ref="received", map_size=8388608
    )
    assert check.commit == root
    fresh_state(path, baseline, returned, True)
    assert (
        len(transport[1]) == 3
    )  # Explicit receive retry never invokes SSH/another child.


@pytest.mark.parametrize("stage_name", ["receive-pre", "receive-post"])
def test_fetched_actual_storage_loss_before_after_commit(
    caller_job, transport, stage_name
):
    path, workspace, spec, state, recorded = caller_job
    packet, root, worker = fetched(caller_job, transport)
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(worker, (root,))
    terminated_at_barrier(path, packet, spec, stage_name)
    fresh_state(path, baseline, returned, stage_name == "receive-post")
    assert len(transport[1]) == 3
