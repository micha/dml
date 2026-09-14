import json
import os
import pathlib
import struct
import subprocess

from hypothesis import given
from hypothesis import strategies as st


def core_driver() -> pathlib.Path:
  configured = os.environ.get("DML_CORE_DRIVER")
  if configured:
    return pathlib.Path(configured)
  dml = pathlib.Path(os.environ.get("DML_BIN", "build/check/dml"))
  suffix = ".exe" if os.name == "nt" else ""
  driver = dml.with_name(f"test_core_driver{suffix}")
  if not driver.is_file():
    raise RuntimeError(f"native core test driver is missing: {driver}")
  return driver


def run_driver(*args: str, data: bytes = b"", check: bool = True) -> subprocess.CompletedProcess[bytes]:
  return subprocess.run(
    [core_driver(), *args],
    input=data,
    check=check,
    capture_output=True,
  )


def record(kind: int, payload: bytes) -> bytes:
  total = 40 + len(payload)
  return struct.pack("<IHHIIIIQQ", 0x314C4D44, 1, 2, total, 0, 0, kind,
                     len(payload), 40) + payload


@given(st.booleans())
def test_bool_encoding_matches_independent_oracle(value: bool) -> None:
  actual = run_driver("encode", "2", data=bytes([value])).stdout
  assert actual == record(2, bytes([value]))


@given(st.integers(min_value=-(2**63), max_value=2**63 - 1))
def test_i64_encoding_matches_independent_oracle(value: int) -> None:
  payload = struct.pack("<q", value)
  assert run_driver("encode", "3", data=payload).stdout == record(3, payload)


@given(st.binary(max_size=256))
def test_bytes_encoding_matches_independent_oracle(value: bytes) -> None:
  assert run_driver("encode", "5", data=value).stdout == record(5, value)


@given(st.lists(st.binary(min_size=16, max_size=16), max_size=12))
def test_list_encoding_preserves_ids(values: list[bytes]) -> None:
  payload = struct.pack("<I", len(values)) + b"".join(values)
  assert run_driver("encode", "8", data=b"".join(values)).stdout == record(8, payload)


@given(st.lists(st.binary(min_size=16, max_size=16), max_size=12, unique=True))
def test_set_encoding_sorts_unique_ids(values: list[bytes]) -> None:
  payload = struct.pack("<I", len(values)) + b"".join(sorted(values))
  assert run_driver("encode", "9", data=b"".join(values)).stdout == record(9, payload)


def test_float_and_text_canonicalization() -> None:
  negative_zero = run_driver("encode", "4", data=struct.pack("<d", -0.0)).stdout
  assert negative_zero == record(4, b"\0" * 8)
  nan = run_driver("encode", "4", data=struct.pack("<Q", 0xFFF0000000000001)).stdout
  assert nan == record(4, struct.pack("<Q", 0x7FF8000000000000))
  assert run_driver("encode", "6", data="e\N{COMBINING ACUTE ACCENT}".encode()).stdout == record(
    6, "é".encode()
  )


def test_uri_profile_and_malformed_record_rejection() -> None:
  assert run_driver("normalize-uri", data=b"HTTP://Example.COM/a/../b/%7e?q=%2f").stdout == (
    b"http://example.com/b/~?q=%2F"
  )
  assert run_driver("normalize-uri", data=b"urn:a/%7e/../b").stdout == b"urn:a/~/../b"
  malformed = record(1, b"")[:-1]
  result = run_driver("validate", data=malformed, check=False)
  assert result.returncode != 0
  assert b"invalid_header" in result.stderr


def test_reviewed_golden_records_and_ids() -> None:
  fixture_path = pathlib.Path(__file__).parents[1] / "fixtures" / "records" / "datums.json"
  vectors = json.loads(fixture_path.read_text(encoding="ascii"))["vectors"]
  for record_hex, expected_id in vectors.values():
    packed = bytes.fromhex(record_hex)
    assert run_driver("validate", data=packed).returncode == 0
    assert run_driver("id", data=packed).stdout.strip().decode() == expected_id
