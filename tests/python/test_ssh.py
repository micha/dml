"""Host helper coverage; substituted transport is not actual SSH fixture evidence."""

from dataclasses import replace
import io
import json
import os
from pathlib import Path
import runpy
import shlex
import struct
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, local, ssh, ssh_worker as worker, transfer
from hypothesis import given, settings, strategies as st
import pytest

from test_caller_requests import caller_job, prepare_recorded, record
from test_exchange import exchange_runtime, job, typed_oracle, bundle_oracle, scalar


def remote(tmp_path, **changes):
    values = dict(
        host="127.0.0.1",
        port=2222,
        user="dml",
        identity_file=tmp_path / "client key",
        known_hosts_file=tmp_path / "known hosts",
        python="/opt/dml/bin/python",
        workspace_root="/work/exchanges",
    )
    values.update(changes)
    return ssh.SSHRemote(**values)


def frame(action, bodies):
    output = io.BytesIO()
    ssh._write_frame(output, action, bodies)
    return output.getvalue()


def header(value, bodies=b""):
    value = value if isinstance(value, bytes) else json.dumps(value).encode()
    return struct.pack(">I", len(value)) + value + bodies


@pytest.fixture(autouse=True)
def worker_host_path(monkeypatch):
    # Private in-process helper emulation on a non-POSIX host. Public remote
    # endpoint validation stays POSIX; real acceptance runs in Linux container.
    if os.name == "nt":
        monkeypatch.setattr(worker, "_posix_path", lambda value: value)


def local_workspace(handle):
    return handle.control.parent / "remote" / handle.expected.token


@pytest.fixture
def transport(tmp_path, monkeypatch):
    endpoint = remote(tmp_path)
    (tmp_path / "remote").mkdir()
    launches = []
    actual = subprocess.Popen

    class Process:
        def __new__(cls, command, **kwargs):
            if command[0] != "ssh":
                return actual(command, **kwargs)
            return super().__new__(cls)

        def __init__(self, command, *, stdin, stdout, stderr, shell):
            assert shell is False
            assert all(hasattr(s, "fileno") for s in (stdin, stdout, stderr))
            launches.append(command)
            tokens = shlex.split(command[-1])
            assert tokens[1:3] == ["-m", "daggerml.ssh_worker"]
            try:
                local_path = tmp_path / "remote" / tokens[4].rsplit("/", 1)[-1]
                worker.serve(tokens[3], local_path, stdin, stdout)
                self.returncode = 0
            except Exception as error:
                stderr.write(type(error).__name__.encode())
                stderr.flush()
                self.returncode = 1

        def wait(self, timeout):
            assert timeout > 0
            return self.returncode

    monkeypatch.setattr(ssh.subprocess, "Popen", Process)
    return endpoint, launches


def stage(caller_job, transport):
    path, workspace, spec, state, recorded = caller_job
    endpoint, launches = transport
    control = path.parent / "control"
    return ssh.stage_ssh_exchange(
        endpoint, workspace=workspace, expected=spec, control=control, timeout_ms=10000
    )


def test_stage_execute_fetch_offline_exact_bytes(caller_job, transport, monkeypatch):
    path, workspace, spec, state, recorded = caller_job
    old = typed_oracle(path, (spec.commit, state[3]))
    handle = stage(caller_job, transport)
    remote_path = local_workspace(handle)
    assert set(p.name for p in remote_path.iterdir()) == {"job.json", "input.bundle"}
    assert ex.read_exchange_spec(remote_path) == spec
    assert (remote_path / "input.bundle").read_bytes() == (
        workspace / "input.bundle"
    ).read_bytes()
    path.rename(path.with_name("caller-offline"))
    workspace.rename(workspace.with_name("input-offline"))
    try:
        assert ssh.execute_ssh_exchange(handle, timeout_ms=10000) is None
    finally:
        path.with_name("caller-offline").rename(path)
    assert (handle.control / "dispatched").exists()
    with pytest.raises(ssh.SSHError, match="already dispatched"):
        ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    assert len(transport[1]) == 2
    packet = ssh.fetch_ssh_exchange(
        handle, packet=path.parent / "packet", timeout_ms=10000
    )
    assert len(transport[1]) == 3
    # Public receive alone validates computation. No network/registration on receipt.
    with monkeypatch.context() as guard:
        guard.setattr(
            ssh.subprocess, "Popen", lambda *a, **k: pytest.fail("no receive launch")
        )
        got = ex.receive_exchange(path, workspace=packet, expected=spec, ref="received")
        assert (
            ex.receive_exchange(path, workspace=packet, expected=spec, ref="received")
            == got
        )
    assert (
        got.request == spec.request and got.outcome == "success" and got.cleanup == "ok"
    )
    assert bundle_oracle(packet / "output.bundle") == typed_oracle(path, (got.commit,))
    assert typed_oracle(remote_path / "worker.dml", (got.commit,)) == typed_oracle(
        path, (got.commit,)
    )
    with d.Repository(path) as repo, repo.read() as tx:
        assert scalar(tx, got.result, "result") == 11
        assert tx.get_ref("submission") == spec.commit
        assert tx.get_ref("request-" + got.request_id) == spec.commit
        for key, data in old.items():
            assert tx.get_record(*key) == data
    # Remote one-shot guard independently rejects direct repeat, no new T.
    with pytest.raises(ex.ExchangeError):
        worker.serve("execute", remote_path, io.BytesIO(), io.BytesIO())


@pytest.mark.parametrize(
    "field,value",
    [
        ("host", "-oProxyCommand=bad"),
        ("host", "x@evil"),
        ("host", "a b"),
        ("host", "a;bad"),
        ("user", "-x"),
        ("user", "x@a"),
        ("user", "é"),
        ("port", 0),
        ("port", 65536),
        ("port", True),
        ("port", "22"),
        ("python", "relative"),
        ("python", "C:/python"),
        ("python", "//bin/python"),
        ("python", "/bin/../python"),
        ("python", "/bin//python"),
        ("python", "/bin/python/"),
        ("workspace_root", "/work/e\u0301"),
        ("workspace_root", "/work/\0x"),
        ("workspace_root", "/work/\nx"),
        ("workspace_root", "/work/\x85x"),
        ("workspace_root", ""),
        ("python", None),
        ("host", "\ud800"),
        ("identity_file", "key%h"),
        ("known_hosts_file", 'key"x'),
        ("known_hosts_file", "key${HOME}"),
        *([] if os.name == "nt" else [("identity_file", "key\\x")]),
    ],
    ids=lambda value: None,
)
def test_endpoint_rejects_unsafe_profiles(tmp_path, field, value):
    with pytest.raises((ssh.SSHError, TypeError, UnicodeError)):
        remote(tmp_path, **{field: value})


def test_argv_quotes_remote_tokens_and_isolates_configuration(caller_job, tmp_path):
    endpoint = remote(
        tmp_path,
        python="/opt/a 'quoted'; $(touch sentinel)/python",
        workspace_root="/work/a 'quoted'; $(touch sentinel)",
    )
    handle = ssh.SSHExchange(endpoint, caller_job[2], tmp_path / "control")
    argv = ssh._argv(handle, "execute", 1001)
    assert shlex.split(argv[-1]) == [
        endpoint.python,
        "-m",
        "daggerml.ssh_worker",
        "execute",
        handle.workspace,
    ]
    assert argv[:4] == ["ssh", "-F", "none", "-T"]
    for option in (
        "BatchMode=yes",
        "StrictHostKeyChecking=yes",
        "IdentityAgent=none",
        "IdentitiesOnly=yes",
        "GlobalKnownHostsFile=none",
        "ClearAllForwardings=yes",
        "ProxyCommand=none",
        "ProxyJump=none",
        "ConnectTimeout=2",
    ):
        assert option in argv
    assert endpoint.identity_file.as_posix() in argv
    assert 'UserKnownHostsFile="' + endpoint.known_hosts_file.as_posix() + '"' in argv
    with pytest.raises(TypeError):
        ssh.SSHExchange(None, caller_job[2], tmp_path)
    with pytest.raises(TypeError):
        ssh.SSHExchange(endpoint, None, tmp_path)
    with pytest.raises(ssh.SSHError):
        ssh.SSHExchange(endpoint, replace(caller_job[2], request=None), tmp_path)


@pytest.mark.parametrize("value", [True, "1", 0, -1, 3600001])
def test_timeout_invalid(value):
    with pytest.raises((TypeError, ssh.SSHError)):
        ssh._timeout(value)


@given(st.binary(max_size=1024), st.binary(max_size=1024))
@settings(max_examples=20)
def test_binary_frame_roundtrip(job, bundle):
    assert ssh._read_frame(io.BytesIO(frame("stage", (job, bundle))), "stage") == (
        job,
        bundle,
    )


@pytest.mark.parametrize(
    "document",
    [
        None,
        [],
        {},
        {"format": "other", "sizes": [0, 0]},
        {"format": ssh.FRAME_FORMAT.format("stage"), "sizes": [0, 0], "extra": 0},
        {"format": ssh.FRAME_FORMAT.format("stage"), "sizes": None},
        {"format": ssh.FRAME_FORMAT.format("stage"), "sizes": [0]},
        *[
            {"format": ssh.FRAME_FORMAT.format("stage"), "sizes": [v, 0]}
            for v in (True, -1, 8193, 2**128, "0", 1.5)
        ],
        b'{"format":"a","format":"b","sizes":[0,0]}',
        b'{"format":"a","sizes":[NaN,0]}',
        b"\xff",
        b"[]" * 2,
        b"[" * 1500 + b"]" * 1500,
    ],
    ids=[
        "null",
        "array",
        "missing",
        "format",
        "extra",
        "sizes-type",
        "sizes-count",
        "bool",
        "negative",
        "overflow",
        "huge",
        "str",
        "float",
        "duplicate",
        "constant",
        "utf8",
        "trailing",
        "deep",
    ],
)
def test_frame_bad_headers(document):
    with pytest.raises(ssh.SSHError):
        ssh._read_frame(io.BytesIO(header(document)), "stage")


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\0\0",
        struct.pack(">I", 0),
        struct.pack(">I", 8193),
        struct.pack(">I", 2) + b"{",
        frame("stage", (b"job", b"input"))[:-1],
        frame("ack", ()) + b"extra",
        b"banner\n" + frame("ack", ()),
    ],
)
def test_frame_truncated_extra_noise(data):
    with pytest.raises(ssh.SSHError):
        ssh._read_frame(
            io.BytesIO(data),
            "ack" if data.startswith(struct.pack(">I", 47)) else "stage",
        )


def test_header_exact_limit_and_original_bundle_limits(monkeypatch):
    descriptor = b"j" * 8192
    bundle = b"b" * transfer.MAX_BUNDLE_BYTES
    assert ssh._read_frame(
        io.BytesIO(frame("stage", (descriptor, bundle))), "stage"
    ) == (descriptor, bundle)
    padded = json.dumps(
        {"format": ssh.FRAME_FORMAT.format("stage"), "sizes": [0, 0]}
    ).encode()
    padded += b" " * (8192 - len(padded))
    assert ssh._read_frame(io.BytesIO(header(padded)), "stage") == (b"", b"")
    for bodies in (
        (descriptor + b"x", b""),
        (b"", bundle + b"x"),
        (b"",),
        (bytearray(), b""),
    ):
        with pytest.raises(ssh.SSHError):
            frame("stage", bodies)
    with pytest.raises(ssh.SSHError):
        ssh._limits("unknown")


def test_partial_reads_and_profile_file(tmp_path):
    class Chunks(io.BytesIO):
        def read(self, size=-1):
            return super().read(min(size, 2))

    assert ssh._read_frame(Chunks(frame("stage", (b"abc", b"12345"))), "stage") == (
        b"abc",
        b"12345",
    )
    path = tmp_path / "file"
    path.write_bytes(b"1234")
    assert ssh._read_file(path, 4) == b"1234"
    with pytest.raises(ssh.SSHError):
        ssh._read_file(path, 3)


def test_public_reader_original_mode_and_no_dispatch(job, monkeypatch):
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("reader never spawns")
    )
    assert ex.read_exchange_spec(job[1]) == job[2]
    assert ex.read_exchange_spec(job[1]).request is None


def test_stage_exact_selection_before_artifacts(caller_job, tmp_path):
    endpoint = remote(tmp_path)
    spec = replace(caller_job[2], token="f" * 32)
    control = tmp_path / "control"
    with pytest.raises(ssh.SSHError, match="differs"):
        ssh.stage_ssh_exchange(
            endpoint,
            workspace=caller_job[1],
            expected=spec,
            control=control,
            timeout_ms=1,
        )
    assert not control.exists()


def test_stage_remote_existing_or_partial_rejects(caller_job, transport):
    handle = stage(caller_job, transport)
    before = {p.name: p.read_bytes() for p in local_workspace(handle).iterdir()}
    with pytest.raises(ssh.SSHError, match="status 1"):
        ssh.stage_ssh_exchange(
            handle.remote,
            workspace=caller_job[1],
            expected=handle.expected,
            control=handle.control.with_name("another"),
            timeout_ms=1000,
        )
    assert before == {p.name: p.read_bytes() for p in local_workspace(handle).iterdir()}


def test_fetch_missing_receipt_does_not_execute(caller_job, transport):
    handle = stage(caller_job, transport)
    with pytest.raises(ssh.SSHError):
        ssh.fetch_ssh_exchange(
            handle, packet=handle.control.with_name("packet"), timeout_ms=1000
        )
    assert not (local_workspace(handle) / "started").exists()
    assert not handle.control.with_name("packet").exists()


@pytest.mark.parametrize(
    "operation", [ssh.execute_ssh_exchange, ssh.fetch_ssh_exchange]
)
def test_job_type_errors(operation):
    with pytest.raises(TypeError):
        operation(
            None,
            timeout_ms=1,
            **({"packet": "x"} if operation == ssh.fetch_ssh_exchange else {}),
        )


def test_spawn_failure_retains_guard_closes_streams(caller_job, tmp_path, monkeypatch):
    control = tmp_path / "control"
    control.mkdir()
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], control)
    streams = []

    def fail(command, **kwargs):
        streams.extend(kwargs[k] for k in ("stdin", "stdout", "stderr"))
        raise OSError("spawn")

    monkeypatch.setattr(ssh.subprocess, "Popen", fail)
    with pytest.raises(OSError):
        ssh.execute_ssh_exchange(handle, timeout_ms=1)
    assert (control / "dispatched").exists()
    assert all(s.closed for s in streams)
    with pytest.raises(ssh.SSHError, match="already dispatched"):
        ssh.execute_ssh_exchange(handle, timeout_ms=1)
    assert len(streams) == 3


@pytest.mark.parametrize("kill", [False, True])
def test_wait_failure_terminates_kills_reaps_local_only(
    caller_job, tmp_path, monkeypatch, kill
):
    control = tmp_path / "control"
    control.mkdir()
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], control)
    events, streams = [], []

    class Process:
        def __init__(self, command, **kwargs):
            streams.extend(kwargs[k] for k in ("stdin", "stdout", "stderr"))

        def wait(self, timeout):
            events.append("wait")
            if len(events) == 1 or (kill and "kill" not in events):
                raise subprocess.TimeoutExpired("ssh", timeout)
            return -9

        def poll(self):
            return None

        def terminate(self):
            events.append("terminate")

        def kill(self):
            events.append("kill")

    monkeypatch.setattr(ssh.subprocess, "Popen", Process)
    with pytest.raises(subprocess.TimeoutExpired):
        ssh.execute_ssh_exchange(handle, timeout_ms=1)
    assert events == (
        ["wait", "terminate", "wait", "kill", "wait"]
        if kill
        else ["wait", "terminate", "wait"]
    )
    assert all(s.closed for s in streams)

    class Exited:
        def poll(self):
            return 0

    ssh._shutdown(Exited())


def test_real_local_timeout_and_stderr_disk_not_pipe(caller_job, tmp_path, monkeypatch):
    control = tmp_path / "control"
    control.mkdir()
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], control)
    actual = ssh.subprocess.Popen
    processes = []

    def spawn(*args, **kwargs):
        p = actual(*args, **kwargs)
        processes.append(p)
        return p

    monkeypatch.setattr(ssh.subprocess, "Popen", spawn)
    monkeypatch.setattr(
        ssh,
        "_argv",
        lambda *a: [
            sys.executable,
            "-c",
            "import sys;sys.stderr.buffer.write(b'x'*1048576)",
        ],
    )
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    assert processes[-1].poll() == 0
    assert next(control.glob("execute.stderr.*")).stat().st_size == 1048576
    (control / "dispatched").unlink()  # Private local-only test, not production retry.
    monkeypatch.setattr(
        ssh, "_argv", lambda *a: [sys.executable, "-c", "import time;time.sleep(60)"]
    )
    with pytest.raises(subprocess.TimeoutExpired):
        ssh.execute_ssh_exchange(handle, timeout_ms=100)
    assert processes[-1].poll() is not None


def test_worker_fixed_actions_errors_and_main(
    caller_job, tmp_path, monkeypatch, capsys
):
    with pytest.raises(ssh.SSHError):
        worker.serve("arbitrary", tmp_path, io.BytesIO(), io.BytesIO())
    assert worker.main([]) == 2
    assert worker.main(["arbitrary", str(tmp_path)]) == 1

    class Stream:
        buffer = io.BytesIO()

    monkeypatch.setattr(sys, "stdin", Stream())
    monkeypatch.setattr(sys, "stdout", Stream())
    monkeypatch.setattr(worker, "serve", lambda *a: None)
    assert worker.main(["fetch", str(tmp_path)]) == 0
    with monkeypatch.context() as guard:
        guard.setattr(sys, "argv", ["ssh_worker"])
        with pytest.raises(SystemExit) as error:
            runpy.run_module("daggerml.ssh_worker", run_name="__main__")
        assert error.value.code == 2
