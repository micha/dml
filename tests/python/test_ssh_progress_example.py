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


def test_example_prepare_real_caller_q_prior_history(
    example, transport, tmp_path, caller_job, capsys
):
    endpoint, _ = transport
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
