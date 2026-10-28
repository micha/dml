"""Meaningful client/helper IO, packet, framing and local process failure boundaries."""

from dataclasses import replace
import builtins
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import daggerml as d
from daggerml import exchange as ex, local, ssh, ssh_worker as worker
import pytest

from test_ssh import frame, remote, stage, transport, local_workspace, worker_host_path
from test_caller_requests import caller_job, caller_completed
from test_exchange import exchange_runtime, typed_oracle
from test_exchange_process import track_new_puts
from test_caller_request_history import (
    test_complete_matching_wrong_q_rejects_before_a as wrong_history,
)


def test_complete_frame_extra_eof_is_not_outcome():
    with pytest.raises(ssh.SSHError, match="extra"):
        ssh._read_frame(io.BytesIO(frame("ack", ()) + b"x"), "ack")
    with pytest.raises(ssh.SSHError, match="extra"):
        ssh._read_frame(io.BytesIO(frame("stage", (b"job", b"input")) + b"x"), "stage")


def test_fetch_other_spec_rejects_before_packet(caller_job, transport):
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    path = local_workspace(handle) / "job.json"
    descriptor = json.loads(path.read_bytes())
    descriptor["token"] = "e" * 32
    path.write_text(json.dumps(descriptor))
    packet = handle.control.with_name("packet")
    with pytest.raises(ssh.SSHError, match="fetched job differs"):
        ssh.fetch_ssh_exchange(handle, packet=packet, timeout_ms=10000)
    assert not packet.exists()


@pytest.mark.parametrize("name", ["input.bundle", "job.json"])
def test_stage_file_failure_retains_partial_no_dispatch(
    caller_job, tmp_path, monkeypatch, name
):
    path = tmp_path / "partial"
    data = (caller_job[1] / "job.json").read_bytes(), (
        caller_job[1] / "input.bundle"
    ).read_bytes()
    original = builtins.open

    def fail(file, mode="r", *a, **k):
        if Path(file) == path / name and mode == "xb":
            raise OSError("owned IO failure")
        return original(file, mode, *a, **k)

    monkeypatch.setattr(builtins, "open", fail)
    with pytest.raises(OSError):
        worker.serve("stage", path, io.BytesIO(frame("stage", data)), io.BytesIO())
    assert path.is_dir() and not (path / "job.json").exists()
    assert not (path / "started").exists() and not (path / "worker.dml").exists()
    if name == "job.json":
        assert (path / "input.bundle").read_bytes() == data[1]


@pytest.mark.parametrize("name", ["output.bundle", "job.json", "completion.json"])
def test_fetch_write_failure_receipt_last_no_a(
    caller_job, transport, monkeypatch, name
):
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    before = (caller_job[0] / "data.mdb").read_bytes()
    packet = handle.control.with_name("partial")
    original = builtins.open

    def fail(file, mode="r", *a, **k):
        if Path(file) == packet / name and mode == "xb":
            raise OSError("owned packet IO failure")
        return original(file, mode, *a, **k)

    monkeypatch.setattr(builtins, "open", fail)
    with pytest.raises(OSError):
        ssh.fetch_ssh_exchange(handle, packet=packet, timeout_ms=10000)
    assert packet.is_dir() and not (packet / "completion.json").exists()
    assert (caller_job[0] / "data.mdb").read_bytes() == before
    assert (local_workspace(handle) / "completion.json").exists()


@pytest.mark.parametrize("index", [1, 2, 3])
def test_acquired_streams_close_on_setup_failure(
    caller_job, tmp_path, monkeypatch, index
):
    control = tmp_path / "control"
    control.mkdir()
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], control)
    original = tempfile.NamedTemporaryFile
    streams = []

    def fail(*a, **k):
        if len(streams) == index - 1:
            raise OSError("stream allocation")
        s = original(*a, **k)
        streams.append(s)
        return s

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", fail)
    with pytest.raises(OSError):
        ssh.execute_ssh_exchange(handle, timeout_ms=1)
    assert all(s.closed for s in streams)
    assert not (control / "dispatched").exists()


@pytest.mark.parametrize("status", [1, 255])
def test_client_exit_unknown_guard_no_receipt(
    caller_job, tmp_path, monkeypatch, status
):
    control = tmp_path / "control"
    control.mkdir()
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], control)
    monkeypatch.setattr(
        ssh,
        "_argv",
        lambda *a: [sys.executable, "-c", "raise SystemExit(" + str(status) + ")"],
    )
    with pytest.raises(ssh.SSHError, match="remote outcome unknown"):
        ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    assert (control / "dispatched").exists()
    assert not (control / "completion.json").exists()


def test_shutdown_failure_retains_owned_local_client(caller_job, tmp_path, monkeypatch):
    control = tmp_path / "control"
    control.mkdir()
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], control)
    streams = []
    events = []

    class Process:
        def __init__(self, command, **kwargs):
            streams.extend(kwargs[k] for k in ("stdin", "stdout", "stderr"))

        def poll(self):
            return None

        def wait(self, timeout):
            events.append("wait")
            raise subprocess.TimeoutExpired("private local process", timeout)

        def terminate(self):
            events.append("terminate")

        def kill(self):
            events.append("kill")

    monkeypatch.setattr(ssh.subprocess, "Popen", Process)
    with pytest.raises(ssh.SSHError, match="caller must reap") as error:
        ssh.execute_ssh_exchange(handle, timeout_ms=1)
    assert isinstance(error.value.process, Process)
    assert events == ["wait", "terminate", "wait", "kill", "wait"]
    assert all(s.closed for s in streams)
    assert (control / "dispatched").exists()


def test_execute_stdout_noise_rejected_after_local_reaping(
    caller_job, tmp_path, monkeypatch
):
    control = tmp_path / "control"
    control.mkdir()
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], control)
    monkeypatch.setattr(
        ssh, "_argv", lambda *a: [sys.executable, "-c", "print('startup noise')"]
    )
    with pytest.raises(ssh.SSHError, match="extra"):
        ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    assert (control / "dispatched").exists()


@pytest.mark.parametrize("mode", ["foreign-cq", "association"])
def test_ssh_candidate_keeps_exact_q_validator(caller_completed, mode):
    # Existing authoritative typed-complete wrong-Q oracle remains unchanged;
    # transport framing cannot weaken receive's selection/history checks.
    wrong_history(caller_completed, "sync", mode)


def test_fetch_never_executes_or_registers(caller_job, transport, monkeypatch):
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    before = typed_oracle(
        local_workspace(handle) / "worker.dml",
        (
            d.ObjectId.from_hex(
                json.loads((local_workspace(handle) / "completion.json").read_bytes())[
                    "final_commit"
                ]
            ),
        ),
    )

    def no(*a, **k):
        pytest.fail("fetch must never execute/register/finalize")

    for module, names in (
        (ex, ("execute_exchange",)),
        (local, ("run_request", "run_step", "retry_step")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, no)
    packet = ssh.fetch_ssh_exchange(
        handle, packet=handle.control.with_name("packet"), timeout_ms=10000
    )
    root = d.ObjectId.from_hex(
        json.loads((packet / "completion.json").read_bytes())["final_commit"]
    )
    assert typed_oracle(local_workspace(handle) / "worker.dml", (root,)) == before
