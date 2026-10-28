"""Maintained application measured through a private in-process transport substitute."""

from dataclasses import replace
import importlib.util
from pathlib import Path
import runpy
import sys

import daggerml as d
from daggerml import local, ssh
import pytest

from test_ssh import remote, transport, worker_host_path
from test_exchange import exchange_runtime

ROOT = Path(__file__).resolve().parents[2]


def application():
    spec = importlib.util.spec_from_file_location(
        "ssh_example", ROOT / "examples/ssh_execution.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def host_application(monkeypatch, endpoint):
    """Private host transport model, not an installed POSIX remote runtime.

    Keep the public helper endpoint POSIX. Only the example's declared child
    binding is translated to the actual host interpreter for this substitute.
    """
    app = application()
    original = app.put_local_binding

    def put_host_binding(tx, *, source, interpreter, timeout_ms):
        if interpreter == endpoint.python:
            interpreter = sys.executable
        return original(
            tx, source=source, interpreter=interpreter, timeout_ms=timeout_ms
        )

    monkeypatch.setattr(app, "put_local_binding", put_host_binding)
    return app


@pytest.mark.parametrize(
    "host_python",
    ["/usr/bin/python3", "D:/Python/python.exe"],
    ids=["posix-host", "windows-host"],
)
def test_private_host_binding_adapter_preserves_posix_endpoint(
    tmp_path, monkeypatch, host_python
):
    endpoint = remote(tmp_path)
    captured = []

    def put_binding(tx, **values):
        captured.append(values["interpreter"])
        return "private captured binding"

    monkeypatch.setattr(local, "put_local_binding", put_binding)
    monkeypatch.setattr(sys, "executable", host_python)
    app = host_application(monkeypatch, endpoint)
    assert (
        app.put_local_binding(
            None, source=b"x", interpreter=endpoint.python, timeout_ms=1
        )
        == "private captured binding"
    )
    assert captured == [host_python]
    assert endpoint.python == "/opt/dml/bin/python"
    app.put_local_binding(
        None, source=b"x", interpreter="/explicit/other", timeout_ms=1
    )
    assert captured[-1] == "/explicit/other"
    if host_python.startswith("D:"):
        # The pre-fix harness retargeted the public endpoint and failed here,
        # before any story could run. Keep production rejection unchanged.
        with pytest.raises(ssh.SSHError, match="absolute POSIX"):
            replace(endpoint, python=host_python)


def test_example_two_matching_failure_and_main(
    tmp_path, transport, exchange_runtime, capsys, monkeypatch
):
    endpoint = transport[0]
    app = host_application(monkeypatch, endpoint)
    args = [
        str(tmp_path / "story"),
        endpoint.host,
        str(endpoint.port),
        endpoint.user,
        str(endpoint.identity_file),
        str(endpoint.known_hosts_file),
        endpoint.python,
        endpoint.workspace_root,
    ]
    app.main(args)
    import json

    got = json.loads(capsys.readouterr().out)
    assert len(got["runs"]) == 3
    assert got["runs"][0]["result"] == got["runs"][1]["result"]
    assert got["runs"][2]["outcome"] == "failure"
    assert got["runs"][2]["cleanup"] == "ok"
    assert len(transport[1]) == 9
    with pytest.raises(ValueError):
        app.main([])
    monkeypatch.setattr(sys, "argv", ["ssh_execution"])
    with pytest.raises(ValueError):
        runpy.run_path(str(ROOT / "examples/ssh_execution.py"), run_name="__main__")


def test_example_restores_caller_on_transport_loss(
    tmp_path, transport, exchange_runtime, monkeypatch
):
    app = host_application(monkeypatch, transport[0])

    def fail(*a, **k):
        raise OSError("transport loss")

    monkeypatch.setattr(app, "execute_ssh_exchange", fail)
    story = tmp_path / "story"
    with pytest.raises(OSError):
        app.produce(story, transport[0])
    with d.Repository(story / "caller.dml") as repo, repo.read() as tx:
        tx.get_ref("submission-1")
    assert not (story / "caller.offline").exists()
