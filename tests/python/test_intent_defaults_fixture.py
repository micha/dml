"""Default-safe controller/import-spawn/census/native oracles. NEVER starts Docker."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_composed_execution import producer
from test_exchange import ROOT, exchange_runtime
from test_explicit_reuse import double
from test_intent_defaults import app, define, request


def controller():
    names = (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_integration",
        "composed_app",
        "reuse_integration",
        "selection_integration",
    )
    previous = {name: sys.modules.get(name) for name in names}
    paths = list(sys.path)
    for name in names:
        sys.modules.pop(name, None)
    try:
        sys.path.insert(0, str(ROOT / "tests/floci"))
        spec = importlib.util.spec_from_file_location(
            "intent_controller", ROOT / "tests/floci/intent_integration.py"
        )
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result
    finally:
        sys.path[:] = paths
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def test_controller_import_aliases_scoped_no_fixture_start():
    old, paths = dict(sys.modules), list(sys.path)
    controller()
    for name in (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_integration",
        "composed_app",
        "reuse_integration",
        "selection_integration",
    ):
        assert sys.modules.get(name) is old.get(name)
    assert sys.path == paths


@pytest.mark.parametrize(
    "family",
    [
        "http",
        "http.client",
        "http.server",
        "urllib.request",
        "urllib.error",
        "urllib.response",
        "urllib.robotparser",
        "requests",
        "httpx",
        "aiohttp",
        "boto3",
        "botocore",
        "docker",
        "docker.api",
        "daggerml.floci",
        "daggerml.floci_http",
        "daggerml.floci_worker",
    ],
)
def test_actual_fresh_policy_process_HTTP_Floci_Docker_import_families_blocked(
    tmp_path, family
):
    controller_app = controller()
    source = tmp_path / "blocked-client.py"
    source.write_text(
        "import sys,types\np=types.ModuleType('daggerml');p.__path__=[];sys.modules['daggerml']=p\ntry:__import__(sys.argv[1])\nexcept AssertionError as error:assert 'cannot import service' in str(error)\nelse:raise AssertionError('service import not blocked')\n"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", controller_app.OFFLINE, str(source), family],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize(
    "operation",
    ["subprocess", "system", "posix-spawn-audit", "fork-audit", "exec-audit"],
)
def test_actual_fresh_policy_process_spawn_is_actively_blocked(tmp_path, operation):
    controller_app = controller()
    source = tmp_path / "blocked-spawn.py"
    source.write_text(
        "import os,subprocess,sys\ntry:\n "
        + {
            "subprocess": "subprocess.run([sys.executable,'-c','raise AssertionError(\"must not run\")'])",
            "system": "os.system('exit 37')",
            "posix-spawn-audit": "sys.audit('os.posix_spawn',sys.executable,[],{})",
            "fork-audit": "sys.audit('os.fork')",
            "exec-audit": "sys.audit('os.exec',sys.executable,[],{})",
        }[operation]
        + "\nexcept AssertionError as error:assert 'cannot spawn' in str(error)\nelse:raise AssertionError('spawn not blocked')\n"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", controller_app.OFFLINE, str(source)],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_controller_native_D_Q_oracle_reader_readonly_and_population(
    double, monkeypatch
):
    controller_app = controller()
    path = double[0][0]
    definition = define(double)
    got = request(path, definition.commit)
    report = app._decision_report(got.decision)
    report.update(
        request_commit=str(got.recorded.commit),
        request=str(got.recorded.request),
        request_id=got.recorded.request_id,
        commit=str(got.recorded.commit),
        association=None,
    )
    assert (
        controller_app.verify_policy(
            path, definition.commit, report, "default-no-selection"
        )
        == got.recorded.commit
    )
    controller_app.verify_definition(
        path, definition.commit, definition.dag, "reuse-by-default"
    )
    with pytest.raises(AssertionError):
        controller_app.verify_definition(
            path, definition.commit, definition.dag, "execute-by-default"
        )
    population = controller_app.native_population(path, [got.recorded.commit])
    assert len(population["requests"]) == 3 and len(population["attempts"]) == 2
    assert all(len(versions) == 2 for versions in population["attempts"].values())

    def read(*a):
        return dict(report)

    monkeypatch.setattr(controller_app, "invoke", read)
    assert (
        controller_app.read_policy("copied-example", [], path, report)["reason"]
        == "default-no-selection"
    )


def test_controller_pending_fresh_prepare_is_SEPARATE_from_policy_process(double):
    controller_app = controller()
    path = double[0][0]
    got = request(path, define(double).commit)
    report = dict(
        request_commit=str(got.recorded.commit),
        request=str(got.recorded.request),
        intent=got.recorded.intent_uri,
    )
    expected = controller_app.prepare_policy(
        path, path.parent, "separate-adapter", report
    )
    assert (
        expected.request == got.recorded.request
        and expected.commit == got.recorded.commit
    )
    assert not (path.parent / "separate-adapter-input/worker.dml").exists()


@pytest.mark.parametrize("bootstrap", ["preloaded-parser", "stdlib-path-abc-model"])
def test_stdlib_only_parser_bootstrap_is_not_transport_authority(tmp_path, bootstrap):
    controller_app = controller()
    source = tmp_path / "parser-client.py"
    source.write_text(
        "import sys,urllib.parse\nassert 'urllib' in sys.modules and 'urllib.parse' in sys.modules\nassert urllib.parse.quote_from_bytes(b'a b') == 'a%20b'\n"
    )
    prelude = "import urllib.parse\n"
    if bootstrap == "stdlib-path-abc-model":
        # Actual fresh subprocess dependency model: importing either bootstrap
        # helper pulls the REAL pure stdlib parser, as pinned3.12 pathlib does.
        prelude = """import builtins
original_import=builtins.__import__
def bootstrap(name,*a,**k):
 if name in ('importlib.abc','pathlib'):original_import('urllib.parse')
 return original_import(name,*a,**k)
builtins.__import__=bootstrap
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", prelude + controller_app.OFFLINE, str(source)],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize("family", ["urllib.request", "http.client"])
def test_preloaded_transport_family_is_error_not_deleted_or_ignored(tmp_path, family):
    controller_app = controller()
    source = tmp_path / "must-not-run.py"
    marker = tmp_path / "unexpected-client-start"
    source.write_text(
        "from pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n"
    )
    prelude = "import " + family + "\n"
    result = subprocess.run(
        [sys.executable, "-B", "-c", prelude + controller_app.OFFLINE, str(source)],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode != 0 and "AssertionError" in result.stderr.decode()
    assert not marker.exists()
