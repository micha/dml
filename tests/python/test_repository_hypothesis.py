import pathlib
import struct
import subprocess

from hypothesis import HealthCheck
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from test_records_hypothesis import run_driver


@settings(
  max_examples=12,
  deadline=None,
  suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(st.integers(min_value=-(2**63), max_value=2**63 - 1))
def test_committed_datum_survives_fresh_process(tmp_path: pathlib.Path, value: int) -> None:
  repo = tmp_path / "repo"
  run_driver("repo-init", str(repo))
  encoded = run_driver("encode", "3", data=struct.pack("<q", value)).stdout
  framed = struct.pack("<I", len(encoded)) + encoded
  put = run_driver("repo-put-batch", str(repo), "commit", data=framed)
  object_id = put.stdout.strip().decode()
  assert len(object_id) == 32
  assert run_driver("repo-get", str(repo), object_id).stdout == encoded


def test_aborted_batch_is_not_visible(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  run_driver("repo-init", str(repo))
  encoded = run_driver("encode", "5", data=b"aborted").stdout
  object_id = run_driver("id", data=encoded).stdout.strip().decode()
  framed = struct.pack("<I", len(encoded)) + encoded
  run_driver("repo-put-batch", str(repo), "abort", data=framed)
  result = run_driver("repo-get", str(repo), object_id, check=False)
  assert result.returncode != 0
  assert b"not_found" in result.stderr


def test_batch_failure_rolls_back_earlier_put(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  run_driver("repo-init", str(repo))
  first = run_driver("encode", "5", data=b"first").stdout
  missing_id = b"\x55" * 16
  invalid_parent = run_driver("encode", "8", data=missing_id).stdout
  framed = struct.pack("<I", len(first)) + first + struct.pack("<I", len(invalid_parent)) + invalid_parent
  result = run_driver("repo-put-batch", str(repo), "commit", data=framed, check=False)
  assert result.returncode != 0
  first_id = run_driver("id", data=first).stdout.strip().decode()
  assert run_driver("repo-get", str(repo), first_id, check=False).returncode != 0
