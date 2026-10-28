"""Finite real Q-recording/worker/receiver barriers, never sacrifice a live child."""

import base64
import json
import shutil
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

from test_caller_requests import (
    caller_job,
    caller_completed,
    record,
    prepare_recorded,
    assert_recorded,
)
from test_exchange import (
    ROOT,
    exchange_runtime,
    initialize,
    tree,
    scalar,
    typed_oracle,
    assert_main,
)
from test_exchange_launch import wait_file, barrier_source, fresh_observe
from test_exchange_progress import observation, _fresh_absence
from test_exchange_progress_process import stopped
from test_exchange_process import fresh_state, track_new_puts


@pytest.mark.parametrize("stage", ("pre", "post"))
def test_actual_recording_commit_response_loss_new_q_cq(
    tmp_path, exchange_runtime, stage
):
    path = tmp_path / "a"
    state = initialize(path)
    baseline = typed_oracle(path, (state[0], state[3]))
    marker = tmp_path / "barrier"
    with open(tmp_path / "errors", "wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/request_interruption_parent.py"),
                str(path),
                str(state[0]),
                str(marker),
                stage,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            wait_file(marker, process, timeout=10)
            process.terminate()  # recording-only process: no computational child
            process.wait(timeout=5)
            assert process.returncode != 0
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    puts = {
        (kind, d.ObjectId.from_hex(oid)): base64.b64decode(raw)
        for kind, oid, raw in json.loads(marker.read_bytes())
    }
    new = {key: raw for key, raw in puts.items() if key not in baseline}
    assert any(kind == "dag" for kind, oid in new) and any(
        kind == "commit" for kind, oid in new
    )
    if stage == "pre":
        _fresh_absence(path, baseline, new)
        with d.Repository(path) as repo, repo.read() as tx:
            with pytest.raises(d.NotFoundError):
                tx.get_ref("recorded")
    else:
        # Fresh independent all-type reader, not the interrupted function response.
        manifest = tmp_path / "expected"
        manifest.write_text(
            json.dumps(
                [
                    [k, str(i), base64.b64encode(b).decode()]
                    for (k, i), b in baseline.items()
                ]
                + [
                    [k, str(i), base64.b64encode(b).decode()]
                    for (k, i), b in new.items()
                ]
            ),
            encoding="utf-8",
        )
        code = """import sys,json,base64,daggerml as d
with d.Repository(sys.argv[1]) as r,r.read() as t:
 for k,i,b in json.load(open(sys.argv[2],encoding='utf-8')):assert t.get_record(k,d.ObjectId.from_hex(i))==base64.b64decode(b)
 c=t.get_ref('recorded'); tree=t.get_tree(t.get_commit(c).tree)
 names=[n for n in tree if n.startswith('request-q-')];assert len(names)==1
 assert t.get_ref(names[0])==c
 assert not any(n.startswith('attempt-') for n in tree)
"""
        subprocess.run(
            [sys.executable, "-c", code, str(path), str(manifest)],
            check=True,
            timeout=20,
        )
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ex.ExchangeError, match="already exists"):
            record(path, state[0], "recorded")
        assert (path / "data.mdb").read_bytes() == before
    assert_main(path, state)


@pytest.mark.parametrize(
    "stage", ("launch-marker", "initial", "publication", "completion")
)
def test_caller_safe_worker_loss_unknown_or_done(caller_job, stage):
    path, workspace, spec, state, recorded = caller_job
    before = (path / "data.mdb").read_bytes()
    stopped(caller_job, stage)
    h = ex.ExchangeHandle(workspace, spec)
    selected = ex.observe_exchange(h, packet=path.parent / "packet")
    assert selected.phase == ("bootstrap" if stage == "launch-marker" else stage)
    assert selected.lifecycle == ("done" if stage == "completion" else "working")
    assert not (workspace / "completion.json").exists()
    assert (path / "data.mdb").read_bytes() == before
    assert_recorded(path, recorded)
    if stage != "launch-marker":
        assert selected.snapshot.request == recorded.request
        assert (
            ex.observe_exchange(h, packet=path.parent / "repeat").snapshot
            == selected.snapshot
        )
        got = ex.receive_observation(
            path, packet=selected.packet, expected=spec, ref="received"
        )
        assert got.request == recorded.request
        if stage == "initial":
            with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
                scratch = scalar(tx, got.initial_attempt, "scratch")
            shutil.rmtree(scratch)  # proven pre-spawn/reaped worker, owned fixture only
        elif stage == "publication":
            assert got.completion is None and got.result is not None
        else:
            assert got.completion.outcome == "success"
    with pytest.raises(ex.ExchangeError):
        ex.start_exchange(h)
    assert_recorded(path, recorded)


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
@pytest.mark.parametrize("stage", ("receive-pre", "receive-post"))
def test_caller_actual_return_commit_loss_full_state(caller_completed, phase, stage):
    path, workspace, spec, state, run = caller_completed
    selected = observation(caller_completed, phase)
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (selected.snapshot.commit,))
    assert sum(key not in baseline for key in returned) > 3
    stopped(caller_completed, stage, selected.packet)
    fresh_state(path, baseline, returned, stage == "receive-post")
    got = ex.receive_observation(
        path, packet=selected.packet, expected=spec, ref="received"
    )
    assert (
        ex.receive_observation(
            path, packet=selected.packet, expected=spec, ref="received"
        )
        == got
    )
    fresh_state(path, baseline, returned, True)
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("submission") == spec.commit
        assert tx.get_ref("request-" + run.request_id) == spec.commit
    assert_main(path, state)


@pytest.mark.parametrize("nonzero", (False, True), ids=("zero", "nonzero-after-u"))
def test_real_finite_owner_fresh_clients_exact_caller_q(
    tmp_path, exchange_runtime, nonzero
):
    path, workspace = tmp_path / "a", tmp_path / "work"
    state = initialize(path, barrier_source(tmp_path, nonzero))
    recorded = record(path, state[0])
    spec = prepare_recorded(path, workspace, recorded)
    saved = tmp_path / "saved"
    h = ex.ExchangeHandle(workspace, spec)
    ex.save_exchange_handle(saved, h)
    offline = tmp_path / "a.offline"
    path.rename(offline)
    launch = ex.start_exchange(h)
    try:
        wait_file(tmp_path / "initial-ready", launch.process)
        p = fresh_observe(saved, tmp_path / "p")
        assert p["phase"] == "initial" and p["request"] == recorded.request_id
        assert launch.process.poll() is None
        (tmp_path / "initial-release").touch()
        wait_file(tmp_path / "publication-ready", launch.process)
        u = fresh_observe(saved, tmp_path / "u")
        assert u["phase"] == "publication" and u["lifecycle"] == "working"
        assert u["request"] == p["request"] and u["attempt"] == p["attempt"]
        assert launch.process.poll() is None
        (tmp_path / "publication-release").touch()
        assert launch.wait(timeout=15) == 0
        (workspace / "completion.json").unlink()
        f = fresh_observe(saved, tmp_path / "f")
        assert f["phase"] == "completion" and f["lifecycle"] == "done"
    finally:
        (tmp_path / "initial-release").touch()
        (tmp_path / "publication-release").touch()
        launch.wait(timeout=20)
        offline.rename(path)
    (workspace / "worker.dml").rename(workspace / "worker.offline")
    for phase in ("p", "u", "f"):
        got = ex.receive_observation(
            path, packet=tmp_path / phase, expected=spec, ref=phase
        )
        assert got.request == recorded.request
        assert got.attempt_id == p["attempt"]
        if phase == "f":
            assert got.completion.outcome == ("failure" if nonzero else "success")
            assert (got.completion.evidence is not None) == nonzero
    assert_recorded(path, recorded)
    assert_main(path, state)


@pytest.mark.parametrize("mode", ("outer-spawn", "child-spawn", "cleanup"))
def test_outer_unknown_vs_child_launch_recorded_failure(caller_job, monkeypatch, mode):
    path, workspace, spec, state, recorded = caller_job
    h = ex.ExchangeHandle(workspace, spec)
    if mode == "outer-spawn":
        with monkeypatch.context() as guard:
            guard.setattr(
                subprocess,
                "Popen",
                lambda *a, **k: (_ for _ in ()).throw(
                    OSError("private outer spawn denied")
                ),
            )
            with pytest.raises(OSError):
                ex.start_exchange(h)
        assert (
            ex.observe_exchange(h, packet=path.parent / "packet").phase == "bootstrap"
        )
        assert not (workspace / "worker.dml").exists()
        with pytest.raises(ex.ExchangeError):
            ex.start_exchange(h)
    else:
        with monkeypatch.context() as guard:
            if mode == "child-spawn":
                guard.setattr(
                    local.subprocess,
                    "Popen",
                    lambda *a, **k: (_ for _ in ()).throw(
                        OSError("private child spawn denied")
                    ),
                )
            else:
                guard.setattr(
                    local,
                    "_cleanup",
                    lambda scratch: ("failed", "private cleanup denied"),
                )
            run = ex.execute_exchange(workspace)
        got = ex.receive_exchange(
            path, workspace=workspace, expected=spec, ref="received"
        )
        assert got.request == recorded.request
        if mode == "child-spawn":
            assert (
                got.outcome == "failure"
                and got.reason == "launch"
                and got.exit_code is None
            )
        else:
            assert got.outcome == "success" and got.cleanup == "failed" and got.result
            shutil.rmtree(run.context.scratch)
    assert_recorded(path, recorded)


@pytest.mark.parametrize("sync", (False, True), ids=("async", "sync"))
def test_caller_real_new_a_map_full_and_explicit_transfer_retry(
    tmp_path, exchange_runtime, sync
):
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
    recorded = record(path, state[0])
    spec = prepare_recorded(path, workspace, recorded)
    run = ex.execute_exchange(workspace)
    selected = observation((path, workspace, spec, state, run), "completion")
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (run.final_commit,))

    def receiving(size):
        if sync:
            return ex.receive_exchange(
                path, workspace=workspace, expected=spec, ref="received", map_size=size
            )
        return ex.receive_observation(
            path, packet=selected.packet, expected=spec, ref="received", map_size=size
        )

    with track_new_puts(path, baseline) as successful:
        with pytest.raises(d.MapFullError):
            receiving(1048576)
    assert successful
    fresh_state(path, baseline, returned, False)
    assert receiving(8388608).commit == run.final_commit
    fresh_state(path, baseline, returned, True)
    assert_recorded(path, recorded)


def test_caller_real_post_f_record_profile_overflow(tmp_path, exchange_runtime):
    source = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 n=t.put_literal(t.put_datum(b'x'*(4*1024*1024+1)))
 publish_result(t,c,t.put_dag(root=n))
"""
    path, workspace = tmp_path / "a", tmp_path / "work"
    state = initialize(path, source)
    recorded = record(path, state[0])
    spec = prepare_recorded(path, workspace, recorded)
    with pytest.raises(transfer.TransferError, match="packed record exceeds"):
        ex.execute_exchange(workspace)
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        final = tx.get_ref("work")
        attempt = tree(tx, final)[
            next(n for n in tree(tx, final) if n.startswith("attempt-"))
        ]
        assert scalar(tx, attempt, "status") == "done"
        assert (
            scalar(tx, tx.get_node(tx.lookup_node(attempt, "outcome")).dag, "role")
            == "local-success-v1"
        )
    before = (workspace / "worker.dml/data.mdb").read_bytes()
    with pytest.raises(transfer.TransferError, match="packed record exceeds"):
        ex.observe_exchange(
            ex.ExchangeHandle(workspace, spec), packet=tmp_path / "packet"
        )
    assert (workspace / "worker.dml/data.mdb").read_bytes() == before
    assert not (tmp_path / "packet").exists()
    assert_recorded(path, recorded)


@pytest.mark.parametrize("stage", ("receive-pre", "receive-post"))
def test_caller_sync_actual_a_storage_response_loss(caller_completed, stage):
    from test_exchange_process import terminated_at_barrier

    path, workspace, spec, state, run = caller_completed
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (run.final_commit,))
    terminated_at_barrier(path, workspace, spec, stage)
    fresh_state(path, baseline, returned, stage == "receive-post")
    got = ex.receive_exchange(path, workspace=workspace, expected=spec, ref="received")
    assert (
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="received")
        == got
    )
    fresh_state(path, baseline, returned, True)
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("submission") == spec.commit
        assert tx.get_ref("request-" + run.request_id) == spec.commit
