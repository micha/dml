import struct

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from test_records_hypothesis import run_driver


ids = st.binary(min_size=16, max_size=16)
names = st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=1, max_size=16)


def envelope(kind: int, payload: bytes) -> bytes:
  return struct.pack("<IHHIII", 0x314C4D44, 1, kind, 20 + len(payload), 0, 0) + payload


def encode(kind: int, payload: bytes) -> bytes:
  return run_driver("encode-object", str(kind), data=payload).stdout


def object_id(packed: bytes) -> bytes:
  return run_driver("object-id", data=packed).stdout.strip()


def tree_payload(entries: list[tuple[str, bytes]]) -> bytes:
  return struct.pack("<I", len(entries)) + b"".join(
    struct.pack("<I", len(name)) + name.encode("ascii") + dag for name, dag in entries
  )


@given(ids)
def test_node_dag_oracles_and_type_domain(reference: bytes) -> None:
  node = encode(3, struct.pack("<I", 1) + reference)
  dag = encode(4, reference)
  assert node == envelope(3, struct.pack("<I", 1) + reference)
  assert dag == envelope(4, reference)
  assert object_id(node) != object_id(dag)
  assert object_id(node) == object_id(node)
  changed = bytes([reference[0] ^ 1]) + reference[1:]
  assert object_id(node) != object_id(encode(3, struct.pack("<I", 1) + changed))
  assert object_id(dag) != object_id(encode(4, changed))
  assert run_driver("id", data=node, check=False).returncode != 0


@given(st.lists(st.tuples(names, ids), unique_by=lambda entry: entry[0], max_size=12))
def test_tree_sorting_matches_independent_oracle(entries: list[tuple[str, bytes]]) -> None:
  packed = encode(5, tree_payload(entries))
  assert packed == envelope(5, tree_payload(sorted(entries)))
  assert packed == encode(5, tree_payload(list(reversed(entries))))
  assert run_driver("validate", data=packed).returncode == 0
  if entries:
    changed = entries + [(entries[0][0], b"\x55" * 16)]
    result = run_driver("encode-object", "5", data=tree_payload(changed), check=False)
    assert result.returncode != 0 and b"invalid_payload" in result.stderr


@given(tree=ids, parents=st.lists(ids, unique=True, max_size=8))
def test_parent_order_and_count_oracle(tree: bytes, parents: list[bytes]) -> None:
  payload = tree + struct.pack("<I", len(parents)) + b"".join(parents)
  packed = encode(6, payload)
  assert packed == envelope(6, payload)
  assert run_driver("validate", data=packed).returncode == 0
  if len(parents) > 1:
    reversed_record = encode(6, tree + struct.pack("<I", len(parents)) + b"".join(reversed(parents)))
    assert object_id(packed) != object_id(reversed_record)
  if parents:
    duplicate = tree + struct.pack("<I", 2) + parents[0] * 2
    result = run_driver("encode-object", "6", data=duplicate, check=False)
    assert result.returncode != 0 and b"duplicate_parent" in result.stderr


@pytest.mark.parametrize("name", [b"", b"a/b", b".a", b"_a", b"a b", b"a\0b", b"\xff", "é".encode(), b"a" * 129])
def test_narrow_tree_name_profile_rejects_ambiguous_names(name: bytes) -> None:
  payload = struct.pack("<II", 1, len(name)) + name + b"\0" * 16
  result = run_driver("encode-object", "5", data=payload, check=False)
  assert result.returncode != 0


@settings(max_examples=40)
@given(kind=st.integers(min_value=3, max_value=6), payload=st.binary(max_size=100))
def test_malformed_enveloped_payloads_fail_without_crashing(kind: int, payload: bytes) -> None:
  # Random bodies may accidentally encode valid objects; success must hash cleanly.
  packed = envelope(kind, payload)
  result = run_driver("validate", data=packed, check=False)
  assert result.returncode in (0, 1)
  if result.returncode == 0:
    assert len(object_id(packed)) == 32


@pytest.mark.parametrize("kind,payload", [
  (3, struct.pack("<I", 2) + b"\0" * 16),
  (4, b"\0" * 17),
  (5, struct.pack("<I", 0) + b"extra"),
  (5, struct.pack("<II", 1, 0xFFFFFFFF) + b"a" + b"\0" * 16),
  (5, struct.pack("<I", 0xFFFFFFFF)),
  (6, b"\0" * 16 + struct.pack("<I", 0xFFFFFFFF)),
  (6, b"\0" * 16 + struct.pack("<I", 0) + b"extra"),
])
def test_invalid_kind_counts_lengths_and_trailing_bytes(kind: int, payload: bytes) -> None:
  assert run_driver("validate", data=envelope(kind, payload), check=False).returncode == 1


@pytest.mark.parametrize("kind,payload", [
  (3, struct.pack("<I", 1) + b"\0" * 16), (4, b"\0" * 16),
  (5, tree_payload([("example", b"\0" * 16)])),
  (6, b"\0" * 16 + struct.pack("<I", 1) + b"\x01" * 16),
])
def test_every_truncation_and_reserved_envelope_fields(kind: int, payload: bytes) -> None:
  packed = envelope(kind, payload)
  for offset in range(len(packed)):
    assert run_driver("validate", data=packed[:offset], check=False).returncode == 1
  for offset in [0, 4, 12, 16]:
    corrupt = bytearray(packed)
    corrupt[offset] ^= 2
    assert run_driver("validate", data=bytes(corrupt), check=False).returncode == 1
  # A ref-tagged record is neither supported record validation nor immutable identity.
  assert run_driver("object-id", data=envelope(7, b"\0" * 16), check=False).returncode == 1
