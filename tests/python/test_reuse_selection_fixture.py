"""Default-safe finite controller/census/alias tests. NEVER start Docker."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_composed_execution import producer
from test_exchange import ROOT, exchange_runtime
from test_explicit_reuse import double
from test_reuse_selection import expected_file, select


def controller():
    aliases = (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_integration",
        "composed_app",
        "reuse_integration",
    )
    old = {name: sys.modules.get(name) for name in aliases}
    paths = list(sys.path)
    for name in aliases:
        sys.modules.pop(name, None)
    try:
        sys.path.insert(0, str(ROOT / "tests/floci"))
        spec = importlib.util.spec_from_file_location(
            "selection_controller", ROOT / "tests/floci/selection_integration.py"
        )
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result
    finally:
        sys.path[:] = paths
        for name, previous in old.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def test_controller_import_aliases_are_scoped_no_fixture_start():
    old = dict(sys.modules)
    paths = list(sys.path)
    controller()
    for name in (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_integration",
        "composed_app",
        "reuse_integration",
    ):
        assert sys.modules.get(name) is old.get(name)
    assert sys.path == paths


@pytest.mark.parametrize("mode", ["complete", "extra", "pagination"])
def test_all_seven_external_status_census_not_default_running_only(mode):
    app = controller()
    calls = []

    def batch(action, body):
        calls.append((action, body))
        result = {
            "jobSummaryList": (
                [{"jobId": "one"}] if body["jobStatus"] == "SUCCEEDED" else []
            )
        }
        if mode == "extra" and body["jobStatus"] == "RUNNING":
            result["jobSummaryList"].append({"jobId": "unknown-writer"})
        if mode == "pagination":
            result["nextToken"] = "more"
        return result

    fixture = SimpleNamespace(batch=batch)
    if mode == "complete":
        assert app.external_census(fixture, ["one"]) == ["one"]
        assert {body["jobStatus"] for _, body in calls} == {
            "SUBMITTED",
            "PENDING",
            "RUNNABLE",
            "STARTING",
            "RUNNING",
            "SUCCEEDED",
            "FAILED",
        }
        assert all(
            action == "ListJobs" and body["maxResults"] == 100 for action, body in calls
        )
    else:
        with pytest.raises(AssertionError):
            app.external_census(fixture, ["one"])


def test_fresh_controller_explicit_copied_sibling_and_blocked_service_import(
    monkeypatch,
):
    app = controller()
    calls = []

    def run(command, evidence):
        calls.append(command)
        return {"fresh": True}

    monkeypatch.setattr(app, "run_fresh", run)
    assert app.invoke(
        Path("/owned/copied/reuse_selection.py"), [], "inspect", "/owned/A", "0" * 32
    ) == {"fresh": True}
    assert app.OFFLINE_SELECTION in calls[0]
    assert (
        "NoService" in app.OFFLINE_SELECTION
        and "sys.path.insert" in app.OFFLINE_SELECTION
    )
    assert calls[0][-1] == "selected-double"


@pytest.mark.parametrize(
    "name",
    [
        "http",
        "http.client",
        "http.server",
        "docker",
        "docker.api",
        "daggerml.floci",
        "daggerml.floci_http",
        "daggerml.floci_worker",
    ],
)
def test_actual_fresh_subprocess_service_family_attempt_is_blocked(name):
    app = controller()
    code = (
        app.OFFLINE_POLICY
        + """
import types
p=types.ModuleType('daggerml');p.__path__=[];sys.modules['daggerml']=p
try: __import__(sys.argv[2])
except AssertionError as error: assert 'cannot import service' in str(error)
else: raise AssertionError('actual attempted import was NOT blocked')
"""
    )
    # Stub only the unavailable parent package so its children reach the finder;
    # this probe tests actual fresh attempted imports, not installed computation.
    result = subprocess.run(
        [sys.executable, "-c", code, "/owned/copied/selection.py", name],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_independent_headers_bound_and_inspect_only_complete_bytes(
    double, expected_file, monkeypatch
):
    app = controller()
    path = double[0][0]
    headers = app.capture_headers(expected_file, double[2][0])
    assert headers[0] == expected_file.read_bytes()
    expected_file.write_bytes(b"x" * 8193)
    with pytest.raises(AssertionError):
        app.capture_headers(expected_file, double[2][0])
    monkeypatch.setattr(app, "invoke", lambda *a: {"inspection": True})
    assert app.inspect_client("owned-source", [], path, double[2][2].commit) == {
        "inspection": True
    }


def test_controller_real_native_choice_and_exact_reuse_checks(double, expected_file):
    from test_reuse_selection_records import reuse

    app = controller()
    got = select(double, expected_file)
    report = {
        "commit": str(got.commit),
        "selection": str(got.dag),
        "validation": str(got.validation),
    }
    assert app.verify_choice(
        double[0][0],
        report,
        double[2][1],
        double[2][2],
        app.capture_headers(expected_file, double[2][0]),
    ) == (
        got.commit,
        got.dag,
        got.validation,
    )
    reused = reuse(double[0][0], got.commit)
    report = {
        "commit": str(reused.commit),
        "association": str(reused.dag),
        "request_commit": str(reused.recorded.commit),
        "request": str(reused.recorded.request),
        "request_id": reused.recorded.request_id,
    }
    assert app.verify_reuse(double[0][0], got.commit, report, double[2][2]) == (
        reused.commit,
        reused.dag,
    )
