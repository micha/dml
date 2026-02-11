import os
import subprocess
import unittest

try:
  from hypothesis import given
  from hypothesis import strategies as st
except ModuleNotFoundError as exc:
  raise unittest.SkipTest("hypothesis is not installed") from exc


def dml_bin() -> str:
  return os.environ.get("DML_BIN", "build/check/dml")


def test_version_flag_reports_library_version() -> None:
  result = subprocess.run(
    [dml_bin(), "--version"],
    check=False,
    text=True,
    capture_output=True,
  )

  assert result.returncode == 0
  assert result.stdout.strip() == "0.1.0"
  assert result.stderr == ""


def test_short_version_flag_reports_library_version() -> None:
  result = subprocess.run(
    [dml_bin(), "-V"],
    check=False,
    text=True,
    capture_output=True,
  )

  assert result.returncode == 0
  assert result.stdout.strip() == "0.1.0"
  assert result.stderr == ""


def test_no_arguments_rejected() -> None:
  result = subprocess.run(
    [dml_bin()],
    check=False,
    text=True,
    capture_output=True,
  )

  assert result.returncode == 2
  assert result.stdout == ""
  assert "usage:" in result.stderr


def test_version_with_extra_argument_rejected() -> None:
  result = subprocess.run(
    [dml_bin(), "--version", "extra"],
    check=False,
    text=True,
    capture_output=True,
  )

  assert result.returncode == 2
  assert result.stdout == ""
  assert "usage:" in result.stderr


@given(
  st.text(min_size=1, max_size=16)
  .filter(lambda s: "\x00" not in s)
  .filter(lambda s: s not in {"--version", "-V"})
)
def test_unknown_argument_rejected(arg: str) -> None:
  result = subprocess.run(
    [dml_bin(), arg],
    check=False,
    text=True,
    capture_output=True,
  )

  assert result.returncode == 2
  assert result.stdout == ""
  assert "usage:" in result.stderr
