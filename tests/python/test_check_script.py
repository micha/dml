"""Owning check.sh pytest-presence function, actual paths/pipes, no builds."""

import os
from pathlib import Path
import subprocess

import pytest

from test_exchange import ROOT


@pytest.mark.parametrize("mode", ["prefix", "suffix", "no-files", "absent"])
def test_production_presence_function_drains_many_paths_and_preserves_no_files(
    tmp_path, mode
):
    root = tmp_path / "owned-function-root"
    root.mkdir()
    if mode != "absent":
        tests = root / "tests"
        tests.mkdir()
        # A nonmatching file/directory does not qualify as a Python test.
        (tests / "ordinary.py").write_text("not a collected test")
        (tests / "test_directory.py").mkdir()
        if mode in ("prefix", "suffix"):
            for number in range(600):
                name = "x" * 96 + str(number)
                name = "test_" + name + ".py" if mode == "prefix" else name + "_test.py"
                (tests / name).write_bytes(b"")
            # Actual output exceeds common pipe capacities, not a copied pipeline
            # or forced false exit. Both matching patterns use real find paths.
            assert sum(len(str(p).encode()) + 1 for p in tests.iterdir()) > 65536
    shims = tmp_path / "shims"
    shims.mkdir()
    python = shims / "python3"
    python.write_text(
        """#!/usr/bin/env bash
if [ "$1" = "-" ]; then printf '0\\n'; exit 0; fi
if [ "$*" = '-m pytest --version' ]; then exit 0; fi
if [ "$*" = '-m pytest -q' ]; then echo OWNING_PYTEST_INVOKED; exit 0; fi
echo 'unexpected Python seam' >&2; exit 1
"""
    )
    python.chmod(0o755)
    source = (ROOT / "scripts/check.sh").read_text()
    start = source.index("run_python_tests_and_coverage_if_present() {")
    stop = source.index("\nrun_mull() {", start)
    function = source[start:stop]  # Execute CURRENT owning production function.
    environment = os.environ.copy()
    # MSYS Bash imports native Windows PATH; convert only this owned shim path,
    # without assuming that a drive-colon spelling is a Bash PATH component.
    prelude = 'set -euo pipefail\nshim="$2"\nif command -v cygpath >/dev/null 2>&1; then shim="$(cygpath -u "$shim")"; fi\nexport PATH="$shim:$PATH"\n'
    result = subprocess.run(
        [
            "bash",
            "-c",
            prelude
            + function
            + '\nrun_python_tests_and_coverage_if_present "$1" "$1/coverage" 1\n',
            "owning-check",
            root.as_posix(),
            shims.as_posix(),
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        env=environment,
        timeout=30,
    )
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    assert result.returncode == 0, output
    if mode in ("prefix", "suffix"):
        assert "OWNING_PYTEST_INVOKED" in output, output
        assert "skipping pytest" not in output
    else:
        assert "OWNING_PYTEST_INVOKED" not in output
        assert (
            "No tests/ directory" if mode == "absent" else "No pytest files"
        ) in output
