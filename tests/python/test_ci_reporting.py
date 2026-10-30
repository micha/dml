"""Execute owning pytest commands/report options in isolated, real tiny suites."""

import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from test_check_script import required_bash


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def workflow_step(name):
    source = WORKFLOW.read_text()
    steps = re.split(r"(?m)^      - name: ", source)[1:]
    matches = [step for step in steps if step.splitlines()[0] == name]
    assert len(matches) == 1, name
    return matches[0]


def scalar(step, key):
    matches = re.findall(r"(?m)^        " + re.escape(key) + r": (.+)$", step)
    assert len(matches) == 1, (key, step)
    return matches[0]


def isolated_environment():
    # Nested pytest must not overwrite an outer CI report/coverage data or load
    # unrelated plugins. No environment values are persisted in the report.
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PYTEST_", "COVERAGE_")) and key != "PYTHONPATH"
    }
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return environment


def test_workflow_reports_are_narrow_always_uploaded_without_masking_status():
    for step_name, artifact_name in (
        ("Upload Python test results", "${{ matrix.name }}-pytest-results"),
        ("Upload strict Python test results", "strict-linux-pytest-results"),
    ):
        step = workflow_step(step_name)
        assert scalar(step, "if") == "always()"
        assert scalar(step, "uses") == "actions/upload-artifact@v7"
        assert f"          name: {artifact_name}\n" in step
        assert "          path: build/test-results/pytest.xml\n" in step
        assert "          if-no-files-found: warn\n" in step
        assert "include-hidden-files" not in step
    unix = scalar(workflow_step("Run Python tests (unix)"), "run")
    windows = scalar(workflow_step("Run Python tests (Windows)"), "run")
    assert shlex.split(unix) == [
        "python",
        "-m",
        "pytest",
        "-q",
        "--junitxml=build/test-results/pytest.xml",
    ]
    assert shlex.split(windows) == [
        "python",
        "-u",
        "-m",
        "pytest",
        "-vv",
        "-o",
        "faulthandler_timeout=60",
        "--junitxml=build/test-results/pytest.xml",
    ]
    strict = workflow_step("Run strict validation")
    assert scalar(strict, "run") == "scripts/check.sh -c"
    assert (
        "          PYTEST_ADDOPTS: --junitxml=build/test-results/pytest.xml\n" in strict
    )
    # No wrapper, ignored test exit, global pytest override, retry or quarantine.
    source = WORKFLOW.read_text()
    assert "continue-on-error" not in source
    assert source.count("PYTEST_ADDOPTS:") == 1
    for name in (
        "Run Python tests (unix)",
        "Run Python tests (Windows)",
        "Run strict validation",
    ):
        assert "||" not in scalar(workflow_step(name), "run")


@pytest.mark.parametrize(
    "route", ["unix", "Windows", "strict-no-source", "strict-source"]
)
@pytest.mark.parametrize(
    "case,code,failures,errors",
    [("pass", 0, 0, 0), ("fail", 1, 1, 0), ("collection", 2, 0, 1)],
)
def test_real_pytest_reports_and_original_status(
    tmp_path, monkeypatch, route, case, code, failures, errors
):
    tests = tmp_path / "tests"
    tests.mkdir()
    content = {
        "pass": "def test_probe(): assert 17 + 25 == 42\n",
        "fail": "def test_probe(): assert 17 + 25 == 99\n",
        "collection": "raise RuntimeError('owned collection failure')\n",
    }[case]
    (tests / "test_probe.py").write_text(content)
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    parent_report = tmp_path / "parent-report.xml"
    parent_coverage = tmp_path / "parent-coverage"
    for path in (parent_report, parent_coverage):
        path.write_bytes(b"owned outer evidence")
    monkeypatch.setenv(
        "PYTEST_ADDOPTS",
        f"--junitxml={shlex.quote(str(parent_report))} -k never_matches_parent",
    )
    monkeypatch.setenv("PYTEST_PLUGINS", "owned_nonexistent_parent_plugin")
    monkeypatch.setenv("COVERAGE_FILE", str(parent_coverage))
    environment = isolated_environment()
    if route.startswith("strict"):
        if route == "strict-source":
            (tmp_path / "source.py").write_text("VALUE = 42\n")
        source = (ROOT / "scripts/check.sh").read_text()
        start = source.index("run_python_tests_and_coverage_if_present() {")
        stop = source.index("\nrun_mull() {", start)
        strict = workflow_step("Run strict validation")
        options = re.findall(r"(?m)^          PYTEST_ADDOPTS: (.+)$", strict)
        assert len(options) == 1
        environment["PYTEST_ADDOPTS"] = options[0]
        # Run CURRENT owning function with real pytest/coverage; only resolve
        # python3 to the current toolchain interpreter (also on native Windows).
        command = [
            required_bash(),
            "-c",
            'set -euo pipefail\npython3() { "$OWNED_PYTHON" "$@"; }\n'
            + source[start:stop]
            + '\nrun_python_tests_and_coverage_if_present "$1" "$1/coverage" 0\n',
            "owning-report",
            tmp_path.as_posix(),
        ]
        environment["OWNED_PYTHON"] = Path(sys.executable).as_posix()
    else:
        command = [sys.executable] + shlex.split(
            scalar(workflow_step(f"Run Python tests ({route})"), "run")
        )[1:]
    result = subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=30,
    )
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    assert result.returncode == code, output
    for path in (parent_report, parent_coverage):
        assert path.read_bytes() == b"owned outer evidence"
    report = tmp_path / "build/test-results/pytest.xml"
    assert report.is_file(), output
    suites = ET.parse(report).getroot().findall("testsuite")
    assert len(suites) == 1
    suite = suites[0]
    assert int(suite.attrib["tests"]) == 1
    assert int(suite.attrib["failures"]) == failures
    assert int(suite.attrib["errors"]) == errors
    assert int(suite.attrib["skipped"]) == 0
    assert len(suite.findall("testcase")) == 1
    if case == "fail":
        assert suite.find("testcase/failure") is not None
    elif case == "collection":
        error = suite.find("testcase/error")
        assert error is not None and "owned collection failure" in error.text
    if route == "strict-source" and code != 0:
        assert "Reporting Python source coverage" not in output
        assert not (tmp_path / "coverage/python-coverage.xml").exists()


@pytest.mark.parametrize("early", ["usage", "no-tests"])
def test_early_pytest_nonzero_and_report_absence_is_not_success(tmp_path, early):
    command = [sys.executable] + shlex.split(
        scalar(workflow_step("Run Python tests (unix)"), "run")
    )[1:]
    if early == "usage":
        command.append("--owned-invalid-option")
    result = subprocess.run(
        command,
        cwd=tmp_path,
        env=isolated_environment(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == (4 if early == "usage" else 5), result.stderr.decode(
        "utf-8", errors="replace"
    )
    report = tmp_path / "build/test-results/pytest.xml"
    if early == "usage":
        assert not report.exists()
    else:
        suite = ET.parse(report).getroot().find("testsuite")
        assert suite is not None and int(suite.attrib["tests"]) == 0
        assert suite.findall("testcase") == []  # Present XML is not a passing suite.
