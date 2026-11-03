"""Pure coverage data/source reporting: exact scaffold exclusions, retained100 gate."""

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import coverage
import pytest

ROOT = Path(__file__).resolve().parents[2]
LABELS = ("HOST captured leaf entry", "HOST captured reuse entry", "isolated old event append")


def patterns(root):
    source = (ROOT / "scripts/check.sh").read_text()
    value = re.search(r'local omit_patterns="([^"\n]+)"', source).group(1)
    return value.replace("$root", str(root))


def report(root, data, mode="report", output=None):
    command = [sys.executable, "-m", "coverage", mode, "--omit", patterns(root), "--fail-under=100"]
    if output is not None:
        command += ["-o" if mode == "xml" else "-d", str(output)]
    return subprocess.run(command, cwd=ROOT, env=dict(os.environ, COVERAGE_FILE=str(data)),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_exact_three_missing_scaffolds_omitted_all_reporters_keep_real_code(tmp_path):
    root = tmp_path / "source-root"
    root.mkdir()
    maintained = root / "kept.py"
    maintained.write_text("value = 1\n")
    data = root / ".coverage"
    cov = coverage.CoverageData(basename=str(data))
    cov.add_lines({str(maintained): {1}, **{str(root / label): set(range(1, 11)) if i < 2 else {1} for i, label in enumerate(LABELS)}})
    cov.write()
    before = hashlib.sha256(data.read_bytes()).hexdigest()
    assert all(not (root / label).exists() for label in LABELS)
    for mode, output in (("report", None), ("xml", tmp_path / "report.xml"), ("html", tmp_path / "html")):
        result = report(root, data, mode, output)
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert "No source for code" not in result.stdout + result.stderr
    xml = (tmp_path / "report.xml").read_text()
    assert "kept.py" in xml and all(label not in xml for label in LABELS)
    assert hashlib.sha256(data.read_bytes()).hexdigest() == before


def test_actual_maintained_source_uncovered_STILL_fails_100(tmp_path):
    maintained = ROOT / "examples/captured_call_session.py"
    assert maintained.exists()
    data = tmp_path / ".coverage"
    cov = coverage.CoverageData(basename=str(data))
    cov.add_lines({str(maintained): {3}, **{str(ROOT / label): {1} for label in LABELS}})
    cov.write()
    before = hashlib.sha256(data.read_bytes()).hexdigest()
    result = report(ROOT, data)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "captured_call_session.py" in result.stdout and "100" in result.stdout
    assert "No source for code" not in result.stdout + result.stderr
    assert hashlib.sha256(data.read_bytes()).hexdigest() == before


def test_owning_omit_list_is_exact_and_consistent_no_guard_module_omission():
    source = (ROOT / "scripts/check.sh").read_text()
    got = patterns(ROOT).split(",")
    assert got == [str(ROOT / "tests/*"), str(ROOT / "subprojects/*"), str(ROOT / "build/*"), *[str(ROOT / label) for label in LABELS]]
    assert not any("examples" in value or "python" in value for value in got)
    assert 'coverage report --omit "$omit_patterns" --fail-under="$coverage_threshold"' in source
    assert 'coverage xml --omit "$omit_patterns" --fail-under="$coverage_threshold"' in source
    assert 'coverage html --omit "$omit_patterns" --fail-under="$coverage_threshold"' in source
    assert "local coverage_threshold=100" in source
