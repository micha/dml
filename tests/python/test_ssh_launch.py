"""Live foreground client ownership, distinct from saved observation identity."""

import io
from pathlib import Path
import subprocess
import sys
import tempfile

from daggerml import ssh
import pytest

from test_caller_requests import caller_job
from test_exchange import exchange_runtime
from test_ssh import remote


def job(caller_job):
    path = caller_job[0].parent
    control = path / "control"
    control.mkdir()
    return ssh.SSHExchange(remote(path), caller_job[2], control)


def test_start_returns_before_any_wait_and_mixed_guard(caller_job, monkeypatch):
    handle = job(caller_job)
    processes, streams = [], []

    class Process:
        returncode = None

        def __init__(self, command, **kwargs):
            assert command[-1].split()[-2] == "execute"
            assert (handle.control / "dispatched").exists()
            assert kwargs["stdin"] == subprocess.DEVNULL and kwargs["shell"] is False
            streams.extend(kwargs[k] for k in ("stdout", "stderr"))
            processes.append(self)

        def wait(self, timeout):
            raise AssertionError("start must never wait")

    monkeypatch.setattr(ssh.subprocess, "Popen", Process)
    launch = ssh.start_ssh_exchange(handle, connect_timeout_ms=1001)
    assert launch.process is processes[0] and launch.job == handle
    assert all(not s.closed for s in streams)
    for operation, kwargs in (
        (ssh.start_ssh_exchange, {"connect_timeout_ms": 1}),
        (ssh.execute_ssh_exchange, {"timeout_ms": 1}),
    ):
        with pytest.raises(ssh.SSHError, match="already dispatched"):
            operation(handle, **kwargs)
    assert len(processes) == 1
    launch._stack.close()  # Private process double has no computational child.


@pytest.mark.parametrize(
    "error",
    [subprocess.TimeoutExpired("ssh", 0.01), OSError("uncertain wait")],
    ids=["timeout", "wait-error"],
)
def test_wait_uncertainty_retains_connection_then_reaps(caller_job, monkeypatch, error):
    handle = job(caller_job)
    events, streams = [], []

    class Process:
        returncode = None

        def __init__(self, command, **kwargs):
            streams.extend(kwargs[k] for k in ("stdout", "stderr"))

        def wait(self, timeout):
            events.append("wait")
            if len(events) == 1:
                raise error
            self.returncode = 0
            return 0

        def terminate(self):
            pytest.fail("execution timeout never terminates")

        def kill(self):
            pytest.fail("execution timeout never kills")

    monkeypatch.setattr(ssh.subprocess, "Popen", Process)
    launch = ssh.start_ssh_exchange(handle, connect_timeout_ms=1000)
    with pytest.raises(type(error)):
        launch.wait(timeout=0.01)
    assert all(not s.closed for s in streams) and not launch._finished
    assert launch.wait(timeout=1) == 0
    assert all(s.closed for s in streams)
    assert launch.wait(timeout=1) == 0 and events == ["wait", "wait"]


@pytest.mark.parametrize("fault", ["stdout", "stderr", "owner", "spawn"])
def test_start_setup_failures_close_acquired_no_lost_process(
    caller_job, monkeypatch, fault
):
    handle = job(caller_job)
    original = tempfile.NamedTemporaryFile
    streams, spawned = [], []

    def allocate(*args, **kwargs):
        if kwargs["prefix"] == "execute." + fault + ".":
            raise OSError("stream allocation")
        stream = original(*args, **kwargs)
        streams.append(stream)
        return stream

    def spawn(*args, **kwargs):
        spawned.append(True)
        raise OSError("spawn")

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", allocate)
    monkeypatch.setattr(subprocess, "Popen", spawn)
    if fault == "owner":
        monkeypatch.setattr(
            ssh, "SSHLaunch", lambda *a: (_ for _ in ()).throw(MemoryError("owner"))
        )
    with pytest.raises((OSError, MemoryError)):
        ssh.start_ssh_exchange(handle, connect_timeout_ms=1)
    assert all(s.closed for s in streams)
    assert bool(spawned) == (fault == "spawn")
    assert (handle.control / "dispatched").exists() == (fault == "spawn")
    with pytest.raises(TypeError):
        ssh.start_ssh_exchange(None, connect_timeout_ms=1)


@pytest.mark.parametrize(
    "source,status",
    [("raise SystemExit(255)", 255), ("print('noise')", 0)],
    ids=["status", "startup-noise"],
)
def test_wait_postreap_failure_disposes_streams_retains_guard(
    caller_job, monkeypatch, source, status
):
    handle = job(caller_job)
    monkeypatch.setattr(ssh, "_argv", lambda *a: [sys.executable, "-c", source])
    launch = ssh.start_ssh_exchange(handle, connect_timeout_ms=1000)
    with pytest.raises(ssh.SSHError) as error:
        launch.wait(timeout=10)
    assert launch.process.poll() == status
    assert launch._stdout.closed
    assert (handle.control / "dispatched").exists()
    with pytest.raises(ssh.SSHError) as repeated:
        launch.wait(timeout=1)
    assert repeated.value is error.value


def test_actual_local_nonwaiting_owner_cooperative_wait_timeout(
    caller_job, tmp_path, monkeypatch
):
    handle = job(caller_job)
    ready, release = tmp_path / "ready", tmp_path / "release"
    code = """import sys,time
from pathlib import Path
ready,release=map(Path,sys.argv[1:])
ready.touch()
deadline=time.monotonic()+10
while not release.exists():
 if time.monotonic()>deadline: raise RuntimeError('private watchdog')
 time.sleep(.01)
sys.stderr.buffer.write(b'x'*1048576)
"""
    monkeypatch.setattr(
        ssh, "_argv", lambda *a: [sys.executable, "-c", code, str(ready), str(release)]
    )
    launch = ssh.start_ssh_exchange(handle, connect_timeout_ms=1000)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            launch.wait(timeout=0.05)
        assert launch.process.poll() is None and not launch._stdout.closed
    finally:
        release.touch()
        assert launch.wait(timeout=15) == 0
    assert ready.exists() and launch._stdout.closed
    assert next(handle.control.glob("execute.stderr.*")).stat().st_size == 1048576
    with pytest.raises(ssh.SSHError):
        ssh.execute_ssh_exchange(handle, timeout_ms=1)


def test_synchronous_dispatch_blocks_async_start(caller_job, monkeypatch):
    handle = job(caller_job)
    monkeypatch.setattr(ssh, "_argv", lambda *a: [sys.executable, "-c", "pass"])
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("no repeat spawn")
    )
    with pytest.raises(ssh.SSHError):
        ssh.start_ssh_exchange(handle, connect_timeout_ms=1)


@pytest.mark.parametrize("fault", ["seek", "read", "close"])
def test_known_reap_seek_read_close_errors_dispose_and_repeat(
    caller_job, monkeypatch, fault
):
    handle = job(caller_job)
    monkeypatch.setattr(ssh, "_argv", lambda *a: [sys.executable, "-c", "pass"])
    launch = ssh.start_ssh_exchange(handle, connect_timeout_ms=1000)
    streams = list(launch._stack._exit_callbacks)  # real acquired file resources
    original_stdout = launch._stdout
    closing = launch._stack.close

    class Output:
        def seek(self, *args):
            if fault == "seek":
                raise OSError("postreap seek")
            return original_stdout.seek(*args)

        def read(self, *args):
            if fault == "read":
                raise OSError("postreap read")
            return original_stdout.read(*args)

    launch._stdout = Output()

    def close():
        closing()  # dispose real acquired streams, then substitute close error
        raise OSError("postreap stack close")

    if fault == "close":
        monkeypatch.setattr(launch._stack, "close", close)
    with pytest.raises(OSError) as error:
        launch.wait(timeout=10)
    assert launch.process.poll() == 0 and original_stdout.closed
    assert not launch._stack._exit_callbacks and streams
    with pytest.raises(OSError) as repeated:
        launch.wait(timeout=1)
    assert repeated.value is error.value
