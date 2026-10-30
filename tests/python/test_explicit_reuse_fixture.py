"""Default-safe census/finite controller helper checks; NEVER starts Docker."""

import importlib.util
import json
import os
import sys
from types import SimpleNamespace

import pytest

from test_exchange import ROOT


def controller():
    names = (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_integration",
        "composed_app",
        "installed_reuse_app",
    )
    modules = {name: sys.modules.get(name) for name in names}
    paths = list(sys.path)
    for name in names:
        sys.modules.pop(name, None)
    try:
        sys.path.insert(0, str(ROOT / "tests/floci"))
        spec = importlib.util.spec_from_file_location(
            "reuse_controller", ROOT / "tests/floci/reuse_integration.py"
        )
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result
    finally:
        sys.path[:] = paths
        for name, previous in modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def test_census_reads_independent_actual_service_store_not_controller_count(tmp_path):
    rows = {
        "owner/job-a": dict(
            jobId="job-a",
            status="SUCCEEDED",
            retryStrategy={"attempts": 1},
            attempts=[{}],
        )
    }
    path = tmp_path / "batch-jobs.json"
    path.write_text(json.dumps(rows))
    app = controller()
    assert app.service_census(tmp_path, ["job-a"]) == path.read_bytes()
    with pytest.raises(AssertionError):
        app.service_census(tmp_path, ["other-job"])
    rows["owner/job-b"] = dict(
        jobId="job-b", status="RUNNING", retryStrategy={"attempts": 1}, attempts=[{}]
    )
    path.write_text(json.dumps(rows))
    with pytest.raises(AssertionError):
        app.service_census(tmp_path, ["job-a", "job-b"])
    rows["owner/job-b"].update(status="FAILED", retryStrategy={"attempts": 2})
    path.write_text(json.dumps(rows))
    with pytest.raises(AssertionError):
        app.service_census(tmp_path, ["job-a", "job-b"])


def test_controller_import_scopes_all_script_aliases():
    before = dict(sys.modules)
    paths = list(sys.path)
    controller()
    for name in (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_integration",
        "composed_app",
        "installed_reuse_app",
    ):
        assert sys.modules.get(name) is before.get(name)
    assert sys.path == paths


def test_fresh_client_has_bounded_no_pythonpath_invocation_and_retained_error(
    monkeypatch,
):
    app = controller()
    calls = []
    monkeypatch.setenv("PYTHONPATH", "must-not-leak-checkout")

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=b'{"fresh":true}', stderr=b"")

    monkeypatch.setattr(app.subprocess, "run", run)
    evidence = []
    assert app.run_fresh(["explicit-installed-python", "-B"], evidence) == {
        "fresh": True
    }
    assert calls[0][1]["timeout"] == 30
    assert (
        "PYTHONPATH" not in calls[0][1]["env"]
        and os.environ["PYTHONPATH"] == "must-not-leak-checkout"
    )
    monkeypatch.setattr(
        app.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=23, stdout=b"", stderr=b"owned original failure"
        ),
    )
    with pytest.raises(AssertionError, match="error retained"):
        app.run_fresh(["explicit-installed-python"], evidence)
    assert (
        evidence[-1]["exit"] == 23
        and evidence[-1]["stderr"] == "owned original failure"
    )


def test_each_command_error_is_persisted_before_later_failure(tmp_path, monkeypatch):
    app = controller()
    log = tmp_path / "commands.json"
    evidence = app.CommandEvidence(log)
    monkeypatch.setattr(
        app.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=23, stdout=b"", stderr=b"original client failure"
        ),
    )
    with pytest.raises(AssertionError):
        app.run_fresh(["installed-client"], evidence)
    assert json.loads(log.read_bytes())[-1]["exit"] == 23

    def unknown(*a, **k):
        raise app.subprocess.TimeoutExpired("installed-client", 30)

    monkeypatch.setattr(app.subprocess, "run", unknown)
    with pytest.raises(app.subprocess.TimeoutExpired):
        app.run_fresh(["installed-client"], evidence)
    row = json.loads(log.read_bytes())[-1]
    assert row["exit"] is None and row["disposition"] == "unknown"
