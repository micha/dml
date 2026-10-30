"""Owning check.sh pytest-presence function, actual paths/pipes, no builds."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from test_exchange import ROOT


SHIM = b"""#!/usr/bin/env bash
if [ "$1" = "-" ]; then printf '0\\n'; exit 0; fi
if [ "$*" = '-m pytest --version' ]; then exit 0; fi
if [ "$*" = '-m pytest -q' ]; then echo OWNING_PYTEST_INVOKED; exit 0; fi
echo 'unexpected Python seam' >&2; exit 1
"""


def required_bash(*, platform=None, executable=None):
    """Select dev-toolchain Bash explicitly, never Windows' bare WSL launcher."""
    platform = os.name if platform is None else platform
    executable = sys.executable if executable is None else executable
    if platform == "nt":
        candidate = Path(executable).resolve().parents[2] / "usr/bin/bash.exe"
        if not candidate.is_file():
            raise RuntimeError("presence tests require MSYS Bash beside UCRT Python")
        return str(candidate)
    located = shutil.which("bash")
    if located is None:
        raise RuntimeError("presence tests require Bash on PATH")
    return str(Path(located).resolve())


def write_shim(path):
    # Exact ASCII/LF bytes on every native platform; text newline=None would
    # translate LF to CRLF on Windows before Bash could run the observer.
    path.write_bytes(SHIM)
    path.chmod(0o755)


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
    write_shim(python)
    assert python.read_bytes() == SHIM and b"\r" not in SHIM
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
            required_bash(),
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


def test_only_macOS_x86_outer_CI_budget_is_twenty_minutes():
    # Read the owning workflow scalar, without adding a YAML dependency or
    # changing any test/runtime timeout. GitHub evaluates this simple selector.
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    matrix_job, strict_job = workflow.split("\n  strict-linux-check:", 1)
    timeout = re.findall(r"(?m)^    timeout-minutes: (.+)$", matrix_job)
    assert len(timeout) == 1
    choice = re.fullmatch(
        r"\$\{\{ matrix\.name == '([^']+)' && ([0-9]+) \|\| ([0-9]+) \}\}", timeout[0]
    )
    assert choice is not None, "expected bounded single-platform CI selector"
    selected, raised, ordinary = choice.groups()
    names = re.findall(r"(?m)^          - name: (.+)$", matrix_job)
    assert set(names) == {
        "Linux x86_64",
        "Linux aarch64",
        "macOS x86_64",
        "macOS arm64",
        "Windows AMD64",
    }
    assert selected == "macOS x86_64"
    for name in names:
        budget = int(raised) if name == selected else int(ordinary)
        assert budget == (20 if name == "macOS x86_64" else 10)
    assert "timeout-minutes:" not in strict_job  # existing separate budget unchanged


def test_native_windows_requires_MSYS_Bash_not_PATH_WSL(tmp_path, monkeypatch):
    root = tmp_path / "MSYS"
    python = root / "ucrt64/bin/python.exe"
    bash = root / "usr/bin/bash.exe"
    python.parent.mkdir(parents=True)
    bash.parent.mkdir(parents=True)
    python.touch()
    bash.touch()

    def no_PATH_lookup(*a):
        pytest.fail("native Windows must not discover the PATH/WSL bash stub")

    monkeypatch.setattr(shutil, "which", no_PATH_lookup)
    assert required_bash(platform="nt", executable=python) == str(bash.resolve())
    bash.unlink()
    with pytest.raises(RuntimeError, match="MSYS Bash"):
        required_bash(platform="nt", executable=python)


def test_unix_absolute_Bash_and_missing_is_error_not_skip(tmp_path, monkeypatch):
    bash = tmp_path / "bash"
    bash.touch()
    monkeypatch.setattr(shutil, "which", lambda name: str(bash))
    assert required_bash(platform="posix") == str(bash.resolve())
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="Bash on PATH"):
        required_bash(platform="posix")


def test_exact_ASCII_LF_shim_avoids_native_CRLF_text_model(tmp_path, monkeypatch):
    original = Path.write_text

    def windows_text(self, data, *a, **k):
        if self.name == "python3":
            return self.write_bytes(data.replace("\n", "\r\n").encode("ascii"))
        return original(self, data, *a, **k)

    monkeypatch.setattr(Path, "write_text", windows_text)
    path = tmp_path / "python3"
    write_shim(path)
    raw = path.read_bytes()
    assert raw == SHIM and b"\r" not in raw
    assert raw.startswith(b"#!/usr/bin/env bash\n") and raw.endswith(b"\n")
    raw.decode("ascii")
    result = subprocess.run(
        [required_bash(), path.as_posix(), "-m", "pytest", "--version"],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode()
