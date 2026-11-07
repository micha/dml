"""Real tiny xdist/coverage runs and raw native counter merging; no DML jobs."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from test_check_script import required_bash
from test_ci_reporting import isolated_environment

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("mode", ["pass", "test-fail", "coverage-gap"])
@pytest.mark.parametrize("route", ["pytest", "owning-function"])
def test_real_worker_coverage_grouping_properties_and_failure_status(tmp_path, mode, route):
    tests = tmp_path / "tests"
    tests.mkdir()
    # Execute owning hooks, changing ONLY the bootstrap repository path so these
    # tiny suites can use the existing extension. No DML computation is invoked.
    (tmp_path / "conftest.py").write_text((ROOT / "conftest.py").read_text())
    plugin = (ROOT / "tests/parallel_validation.py").read_text()
    assert plugin.count('ROOT = Path(__file__).resolve().parents[1]') == 1
    (tests / "parallel_validation.py").write_text(plugin.replace(
        'ROOT = Path(__file__).resolve().parents[1]', f'ROOT = Path({str(ROOT)!r})'))
    original = (ROOT / "tests/conftest.py").read_text()
    assert original.count('ROOT = Path(__file__).resolve().parents[1]') == 1
    source = original.replace('ROOT = Path(__file__).resolve().parents[1]', f'ROOT = Path({str(ROOT)!r})')
    source += '\nimport pytest\n@pytest.fixture(scope="module")\ndef frozen(request, record_testsuite_property):\n    worker = request.config.workerinput["workerid"]\n    record_testsuite_property("tiny_worker", worker)\n    return worker\n'
    (tests / "conftest.py").write_text(source)
    maintained = 'def left():\n    return 13\n\ndef right():\n    return 29\n'
    if mode == "coverage-gap":
        maintained += '\ndef uncovered():\n    return 99\n'
    (tmp_path / "calc.py").write_text(maintained)
    for name, value in (("left", 13), ("right", 29)):
        expected = 99 if mode == "test-fail" and name == "left" else value
        (tests / ("test_" + name + ".py")).write_text(
            f'import calc\n\ndef test_first(frozen):\n    assert calc.{name}() == {expected}\n'
            f'\ndef test_second(frozen):\n    assert calc.{name}() == {value}\n')
    (tmp_path / ".coveragerc").write_text('[run]\nsource = .\nomit = tests/*\n')
    env = isolated_environment()
    env.update(COVERAGE_FILE=str(tmp_path / ".coverage"), DML_TEST_REPORT_DIR=str(tmp_path / "reports"),
               DML_TEST_GCOV_DIR=str(tmp_path / "native-workers"),
               GCOV_PREFIX=str(tmp_path / "inherited-worker-prefix"), GCOV_PREFIX_STRIP="6")
    if route == "owning-function":
        script = (ROOT / "scripts/check.sh").read_text()
        start = script.index("run_python_tests_and_coverage_if_present() {")
        functions = script[start:script.index("\nrun_mull() {", start)]
        env.update(DML_TEST_WORKERS="2", PYTEST_PLUGINS="xdist.plugin,pytest_cov.plugin",
                   PYTEST_ADDOPTS="--junitxml=pytest.xml", OWNED_PYTHON=Path(sys.executable).as_posix())
        command = [required_bash(), "-c", 'set -euo pipefail\npython3() { "$OWNED_PYTHON" "$@"; }\n'
            'require_cmd() { command -v "$1" >/dev/null; }\n' + functions +
            '\nrun_python_tests_and_coverage_if_present "$1" "$1/build/coverage" 1\n',
            "owned-parallel", tmp_path.as_posix()]
    else:
        command = [sys.executable, "-m", "pytest", "-q", "-p", "xdist.plugin", "-p", "pytest_cov.plugin",
            "-n", "auto", "--maxprocesses=2", "--dist=loadgroup", "--max-worker-restart=0", "--cov=.",
            "--cov-config=.coveragerc", "--cov-report=", "--cov-fail-under=0", "--junitxml=pytest.xml"]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    (tmp_path / "pytest.stdout").write_text(result.stdout)
    (tmp_path / "pytest.stderr").write_text(result.stderr)
    (tmp_path / "pytest.exit").write_text(str(result.returncode) + "\n")
    expected_exit = 1 if mode == "test-fail" else 2 if mode == "coverage-gap" and route == "owning-function" else 0
    assert result.returncode == expected_exit, (result.stdout, result.stderr)
    xml = ET.parse(tmp_path / "pytest.xml").getroot()
    cases = list(xml.iter("testcase"))
    assert len(cases) == 4 and sum(c.find("failure") is not None for c in cases) == (1 if mode == "test-fail" else 0)
    properties = xml.findall('.//testsuite/properties/property')
    assert sorted(p.get("value") for p in properties if p.get("name") == "tiny_worker") == ["gw0", "gw1"]
    assert all("@test_" in c.get("name") for c in cases), "consuming-module grouping absent"
    plan = json.loads((tmp_path / "reports/resources.json").read_text())
    assert plan["selected_workers"] == 2
    for worker in ("gw0", "gw1"):
        report = json.loads((tmp_path / ("reports/" + worker + ".json")).read_text())
        assert not report["crashed"] and report["memory"]["samples"] > 0
        assert report["memory"]["peak_sampled_tree_rss"] > 0
        assert report["suite_properties"] == [["tiny_worker", worker]]
    coverage = subprocess.run([sys.executable, "-m", "coverage", "report", "--fail-under=100"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert coverage.returncode == (2 if mode == "coverage-gap" else 0), (coverage.stdout, coverage.stderr)
    assert "calc.py" in coverage.stdout


def owning_merge_function():
    source = (ROOT / "scripts/check.sh").read_text()
    start = source.index("merge_parallel_native_coverage() {")
    return source[start:source.index("\nrun_mull() {", start)]


def merge(root, *, tool=None):
    env = isolated_environment()
    if tool is not None:
        env["PATH"] = str(tool) + os.pathsep + env["PATH"]
    env["OWNED_PYTHON"] = Path(sys.executable).as_posix()
    return subprocess.run([required_bash(), "-c",
        'set -euo pipefail\npython3() { "$OWNED_PYTHON" "$@"; }\nrequire_cmd() { command -v "$1" >/dev/null; }\n'
        + owning_merge_function() + '\nmerge_parallel_native_coverage "$1" "$1/build/coverage"\n',
        "owned-merge", root.as_posix()], env=env, capture_output=True, text=True, timeout=30)


def test_no_parallel_native_directory_does_not_require_merge_tool(tmp_path):
    assert merge(tmp_path).returncode == 0


def test_real_gcov_merge_preserves_initial_and_all_worker_hits(tmp_path, monkeypatch):
    # Reproduce the outer xdist worker's environment even in a serial test run.
    monkeypatch.setenv("GCOV_PREFIX", str(tmp_path / "inherited-worker-prefix"))
    monkeypatch.setenv("GCOV_PREFIX_STRIP", "6")
    build = tmp_path / "build/check"
    build.mkdir(parents=True)
    source = build / "branch.c"
    source.write_text('int left(void) {\n return 13;\n}\nint right(void) {\n return 29;\n}\n'
                      'int main(int argc, char **argv) {\n int v = argc > 1 ? left() : right();\n return v > 99;\n}\n')
    binary = build / ("probe.exe" if os.name == "nt" else "probe")
    intro = json.loads((Path(os.environ.get("DML_BIN", ROOT / "build/check/dml")).parent /
                        "meson-info/intro-compilers.json").read_text())
    compiled = subprocess.run([*intro["host"]["c"]["exelist"], "--coverage", "-O0", str(source), "-o", str(binary)],
                              capture_output=True, text=True, timeout=30)
    assert compiled.returncode == 0, (compiled.stdout, compiled.stderr)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GCOV_")}
    assert subprocess.run([str(binary)], env=env, timeout=15).returncode == 0
    workers = tmp_path / "build/coverage/native-workers"
    for worker in ("gw0", "gw1"):
        destination = workers / worker
        destination.mkdir(parents=True)
        assert subprocess.run([str(binary), "left"], env=dict(env, GCOV_PREFIX=str(destination),
            GCOV_PREFIX_STRIP=str(len(build.parts) - 1)), timeout=15).returncode == 0
        assert list(destination.glob("*.gcda"))
    # Empty owned directory is not a worker. Exercise the directory-only guard.
    (workers / "not-a-worker").write_text("not a counter directory")
    result = merge(tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    notes = next(build.glob("*.gcno"))
    report = subprocess.run(["gcov", "-b", "-c", "-o", str(notes), str(source)],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert report.returncode == 0, (report.stdout, report.stderr)
    lines = (tmp_path / "branch.c.gcov").read_text()
    assert re.search(r"\s*2:\s*2:.*return 13", lines), lines
    assert re.search(r"\s*1:\s*5:.*return 29", lines), lines
    assert re.search(r"\s*3:\s*9:.*return v", lines), lines


def test_merge_failure_keeps_original_raw_counters_and_nonzero_exit(tmp_path):
    build = tmp_path / "build/check"
    build.mkdir(parents=True)
    before = b"owned raw counter witness"
    (build / "probe.gcda").write_bytes(before)
    (tmp_path / "build/coverage/native-workers/gw0").mkdir(parents=True)
    tools = tmp_path / "tools"
    tools.mkdir()
    script = tools / "gcov-tool"
    script.write_bytes(b"#!/usr/bin/env bash\nexit 3\n")
    script.chmod(0o755)
    result = merge(tmp_path, tool=tools)
    assert result.returncode == 3, (result.stdout, result.stderr)
    assert (build / "probe.gcda").read_bytes() == before
