"""Maintained endpoint example modes; no default Docker/SSH fixture startup."""

import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys

from daggerml import exchange as ex
import pytest

from test_caller_requests import caller_job, caller_completed
from test_exchange import ROOT, exchange_runtime
from test_exchange_progress import observation
from test_ssh import remote, transport, worker_host_path


@pytest.fixture
def example():
    path = ROOT / "examples/ssh_progress.py"
    spec = importlib.util.spec_from_file_location("ssh_progress_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def host_bindings(example, endpoint, monkeypatch):
    """Private in-process prepare model, not an installed POSIX remote runtime.

    Keep SSHRemote POSIX; translate only the example binding selected for this
    host substitute. Other explicit interpreter spellings retain their meaning.
    """
    original = example.put_local_binding

    def put_host_binding(tx, *, source, interpreter, timeout_ms):
        if interpreter == endpoint.python:
            interpreter = sys.executable
        return original(
            tx, source=source, interpreter=interpreter, timeout_ms=timeout_ms
        )

    monkeypatch.setattr(example, "put_local_binding", put_host_binding)


@pytest.mark.parametrize(
    "host_python",
    ["/usr/bin/python3", "D:/Python/python.exe"],
    ids=["posix-host", "windows-host"],
)
def test_private_prepare_binding_adapter_preserves_posix_endpoint(
    example, tmp_path, monkeypatch, host_python
):
    from dataclasses import replace
    from daggerml import ssh

    endpoint = remote(tmp_path)
    captured = []

    def put_binding(tx, **values):
        captured.append(values["interpreter"])
        return "private captured binding"

    monkeypatch.setattr(example, "put_local_binding", put_binding)
    monkeypatch.setattr(sys, "executable", host_python)
    host_bindings(example, endpoint, monkeypatch)
    assert (
        example.put_local_binding(
            None, source=b"x", interpreter=endpoint.python, timeout_ms=1
        )
        == "private captured binding"
    )
    assert captured == [host_python] and endpoint.python == "/opt/dml/bin/python"
    example.put_local_binding(
        None, source=b"x", interpreter="/explicit/other", timeout_ms=1
    )
    assert captured[-1] == "/explicit/other"
    if host_python.startswith("D:"):
        with pytest.raises(ssh.SSHError, match="absolute POSIX"):
            replace(endpoint, python=host_python)


def test_example_prepare_real_caller_q_prior_history(
    example, transport, tmp_path, caller_job, capsys, monkeypatch
):
    endpoint, _ = transport
    host_bindings(example, endpoint, monkeypatch)
    directory = tmp_path / "story"
    example.main(
        [
            "prepare",
            str(directory),
            endpoint.host,
            str(endpoint.port),
            endpoint.user,
            str(endpoint.identity_file),
            str(endpoint.known_hosts_file),
            endpoint.python,
            endpoint.workspace_root,
            "/work/declared-gate",
        ]
    )
    got = json.loads(capsys.readouterr().out)
    assert got["request"] != got["unstarted"]
    assert Path(got["saved"]).is_dir()
    with pytest.raises(FileExistsError):
        example.prepare(directory, endpoint, "/work/declared-gate")


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
def test_example_observe_receive_short_lived_modes(
    example, caller_completed, phase, tmp_path, monkeypatch, capsys
):
    selected = observation(caller_completed, phase)
    from daggerml import ssh

    job = ssh.SSHExchange(remote(tmp_path), caller_completed[2], tmp_path / "control")
    saved = tmp_path / "saved"
    ssh.save_ssh_exchange(saved, job)
    monkeypatch.setattr(example, "observe_ssh_exchange", lambda *a, **k: selected)
    example.main(["observe", str(saved), str(selected.packet)])
    assert json.loads(capsys.readouterr().out)["phase"] == phase
    example.main(
        [
            "receive",
            str(caller_completed[0]),
            str(saved),
            str(selected.packet),
            "received",
        ]
    )
    assert json.loads(capsys.readouterr().out)["ref"] == "received"
    monkeypatch.setattr(
        example,
        "observe_ssh_exchange",
        lambda *a, **k: ex.ExchangeObservation("working", "bootstrap", None, None),
    )
    example.main(["observe", str(saved), str(tmp_path / "bootstrap")])
    assert json.loads(capsys.readouterr().out)["commit"] is None


@pytest.mark.parametrize("uncertain", ["timeout", "oserror", "reaped"])
def test_example_owner_retained_on_uncertain_wait(
    example, caller_job, tmp_path, monkeypatch, uncertain, capsys
):
    from daggerml import ssh

    saved = tmp_path / "saved"
    ssh.save_ssh_exchange(
        saved, ssh.SSHExchange(remote(tmp_path), caller_job[2], tmp_path / "control")
    )
    calls = []

    class Owner:
        process = None

        def __init__(self):
            self.process = self

        def wait(self, timeout):
            calls.append(timeout)
            if len(calls) == 1:
                if uncertain == "timeout":
                    raise subprocess.TimeoutExpired("private owner", timeout)
                raise OSError("wait")
            return 0

        def poll(self):
            return 0 if uncertain == "reaped" else None

    monkeypatch.setattr(example, "start_ssh_exchange", lambda *a, **k: Owner())
    if uncertain == "reaped":
        with pytest.raises(OSError):
            example.own(saved)
    else:
        example.main(["own", str(saved)])
        output = capsys.readouterr()
        assert json.loads(output.out) == {"local_status": 0}
        assert "owner retained" in output.err and calls == [180, 180]


@pytest.mark.parametrize("args", [[], ["other"], ["prepare"], ["receive", "one"]])
def test_example_bad_modes(example, args):
    with pytest.raises(ValueError):
        example.main(args)


def test_example_main_guard_measured(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["ssh_progress.py"])
    with pytest.raises(ValueError):
        runpy.run_path(str(ROOT / "examples/ssh_progress.py"), run_name="__main__")
