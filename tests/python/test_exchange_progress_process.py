"""Safe actual-worker loss and actual-A pre/postcommit knowledge boundaries."""

from pathlib import Path
import shutil
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

from test_exchange import (
    ROOT,
    job,
    completed,
    exchange_runtime,
    initialize,
    prepare,
    typed_oracle,
    scalar,
    tree,
    assert_main,
)
from test_exchange_launch import wait_file
from test_exchange_progress import handle, observation, receive
from test_exchange_process import fresh_state, track_new_puts


def stopped(job, stage, packet="unused"):
    path, workspace, spec, state = job[:4]
    saved, marker = workspace.parent / "handle.json", workspace.parent / "barrier"
    ex.save_exchange_handle(saved, handle(workspace, spec))
    with open(workspace.parent / "private-errors", "wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/progress_interruption_parent.py"),
                str(saved),
                str(marker),
                stage,
                str(path),
                str(packet),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            wait_file(marker, process, timeout=10)
            # Barrier is either before child spawn or after real child wait/reap;
            # receive process has no computational child. Safe known ownership only.
            process.terminate()
            process.wait(timeout=5)
            assert process.returncode != 0
        finally:
            if process.poll() is None:
                # A failed barrier is NOT a successful process-cleanup test. The
                # private child finishes within its existing bounded timeout first.
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


@pytest.mark.parametrize(
    "stage", ("launch-marker", "initial", "publication", "completion")
)
def test_safe_loss_unknown_vs_retrieved_done_no_relaunch(job, stage):
    path, workspace, spec, state = job
    before = (path / "data.mdb").read_bytes()
    stopped(job, stage)
    h = handle(workspace, spec)
    got = ex.observe_exchange(h, packet=workspace.parent / "packet")
    expected_phase = "bootstrap" if stage == "launch-marker" else stage
    assert got.phase == expected_phase
    assert got.lifecycle == ("done" if stage == "completion" else "working")
    assert not (workspace / "completion.json").exists()
    assert (path / "data.mdb").read_bytes() == before
    if stage != "launch-marker":
        assert (
            ex.observe_exchange(h, packet=workspace.parent / "repeat").snapshot
            == got.snapshot
        )
        returned = ex.receive_observation(
            path, packet=got.packet, expected=spec, ref="received"
        )
        assert (
            returned.request_id == got.snapshot.request_id
            and returned.attempt_id == got.snapshot.attempt_id
        )
        if stage == "initial":
            # Only test-owned scratch; private barrier PROVES no spawn happened,
            # and the stopped worker is reaped before cleanup follows recorded path.
            with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
                scratch = scalar(tx, returned.initial_attempt, "scratch")
            shutil.rmtree(scratch)
        if stage == "publication":
            assert returned.completion is None and returned.result is not None
        if stage == "completion":
            assert returned.completion.outcome == "success"
    with pytest.raises(ex.ExchangeError):
        ex.start_exchange(h)
    if stage != "launch-marker":
        with pytest.raises(ex.ExchangeError):
            ex.execute_exchange(workspace)
    assert_main(path, state)


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
@pytest.mark.parametrize("stage", ("receive-pre", "receive-post"))
def test_actual_progress_commit_response_loss_full_fresh_oracle(
    completed, phase, stage
):
    path, workspace, spec, state, run = completed
    selected = observation(completed, phase)
    baseline = typed_oracle(path, (state[0], state[3]))
    returned = typed_oracle(workspace / "worker.dml", (selected.snapshot.commit,))
    assert sum(key not in baseline for key in returned) > 3
    stopped(completed, stage, selected.packet)
    fresh_state(path, baseline, returned, stage == "receive-post")
    assert_main(path, state)
    first = receive(completed, selected.packet)
    assert receive(completed, selected.packet) == first
    fresh_state(path, baseline, returned, True)


def test_concurrent_read_only_observers_distinct_immutable_packets(completed):
    path, workspace, spec, state, run = completed
    saved = workspace.parent / "concurrent-handle"
    ex.save_exchange_handle(saved, handle(workspace, spec))
    release = workspace.parent / "concurrent-release"
    before = (workspace / "worker.dml/data.mdb").read_bytes()
    code = """import sys,time
from pathlib import Path
from daggerml import exchange as ex
saved,packet,ready,release=sys.argv[1:]
original=ex._discover
def together(tx,spec):
 result=original(tx,spec)
 Path(ready).touch()
 deadline=time.monotonic()+10
 while not Path(release).exists():
  if time.monotonic()>deadline:raise TimeoutError('private concurrent reader watchdog')
  time.sleep(.01)
 return result
ex._discover=together
ex.observe_exchange(ex.load_exchange_handle(saved),packet=packet)
"""
    processes, streams, packets = [], [], []
    try:
        for index in range(2):
            packet = workspace.parent / ("concurrent-" + str(index))
            packets.append(packet)
            stream = open(workspace.parent / ("concurrent-errors-" + str(index)), "wb")
            streams.append(stream)
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        code,
                        str(saved),
                        str(packet),
                        str(workspace.parent / ("concurrent-ready-" + str(index))),
                        str(release),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=stream,
                )
            )
        # Both processes hold genuine B read transactions at the private barrier.
        for index, process in enumerate(processes):
            wait_file(workspace.parent / ("concurrent-ready-" + str(index)), process)
        release.touch()
        for process in processes:
            assert process.wait(timeout=15) == 0
    finally:
        release.touch()
        for process in processes:
            if process.poll() is None:
                process.terminate()  # reader only: no computational child
                process.wait(timeout=5)
        for stream in streams:
            stream.close()
    assert (workspace / "worker.dml/data.mdb").read_bytes() == before
    for name in ("job.json", "observation.json", "snapshot.bundle"):
        assert (packets[0] / name).read_bytes() == (packets[1] / name).read_bytes()
    assert receive(completed, packets[0], "first").commit == run.final_commit
    assert receive(completed, packets[1], "second").commit == run.final_commit
    assert_main(path, state)


def test_progress_real_new_put_map_full_whole_retry(tmp_path, exchange_runtime):
    source = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 n=t.put_literal(t.put_datum('new prefix'))
 big=t.put_literal(t.put_datum(b'x'*2097152))
 publish_result(t,c,t.put_dag(root=n,bindings={'big':big}))
"""
    path, workspace = tmp_path / "a", tmp_path / "work"
    state = initialize(path, source)
    spec = prepare(path, workspace, state[0])
    run = ex.execute_exchange(workspace)
    completed = (path, workspace, spec, state, run)
    selected = observation(completed, "publication")
    baseline = typed_oracle(path, (state[0], state[3]))
    returned = typed_oracle(workspace / "worker.dml", (selected.snapshot.commit,))
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
    got = ex.receive_observation(
        path, packet=selected.packet, expected=spec, ref="received", map_size=8388608
    )
    assert got.commit == selected.snapshot.commit and got.lifecycle == "working"
    fresh_state(path, baseline, returned, True)
