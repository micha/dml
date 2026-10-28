"""Maintained application measured through a private in-process transport substitute."""

from dataclasses import replace
import importlib.util
from pathlib import Path
import runpy
import sys

import daggerml as d
import pytest

from test_ssh import transport, worker_host_path
from test_exchange import exchange_runtime

ROOT = Path(__file__).resolve().parents[2]


def application():
    spec = importlib.util.spec_from_file_location(
        "ssh_example", ROOT / "examples/ssh_execution.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_two_matching_failure_and_main(
    tmp_path, transport, exchange_runtime, capsys, monkeypatch
):
    endpoint = replace(transport[0], python=sys.executable)
    app = application()
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
    app = application()

    def fail(*a, **k):
        raise OSError("transport loss")

    monkeypatch.setattr(app, "execute_ssh_exchange", fail)
    story = tmp_path / "story"
    with pytest.raises(OSError):
        app.produce(story, replace(transport[0], python=sys.executable))
    with d.Repository(story / "caller.dml") as repo, repo.read() as tx:
        tx.get_ref("submission-1")
    assert not (story / "caller.offline").exists()
