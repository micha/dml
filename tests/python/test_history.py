import pathlib
import struct
import subprocess
import tempfile

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from test_objects_hypothesis import encode, tree_payload
from test_records_hypothesis import core_driver, run_driver


def history(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
  driver = core_driver().with_name(core_driver().name.replace("test_core_driver", "test_history_driver"))
  return subprocess.run([driver, *args], capture_output=True, check=check)


def snapshot(repo: pathlib.Path, value: int, parent: str = "none", ref: str = "main", mode: str = "create") -> list[str]:
  return history("snapshot", str(repo), str(value), parent, ref, mode).stdout.decode().splitlines()


def inspect(repo: pathlib.Path, target: str, mode: str = "ref") -> tuple[str, list[str], int]:
  lines = history("inspect", str(repo), mode, target).stdout.decode().splitlines()
  count = int(lines[1])
  return lines[0], lines[2:2 + count], int(lines[2 + count])


def get(repo: pathlib.Path, kind: int, object_id: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
  if kind == 2:
    return run_driver("repo-get", str(repo), object_id, check=check)
  return run_driver("object-get", str(repo), str(kind), object_id, check=check)


def test_acceptance_workflow_branching_and_immutable_bytes(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  frozen = [get(repo, kind, object_id).stdout for kind, object_id in zip(range(2, 7), first)]
  second = snapshot(repo, 43, first[-1], mode="update")
  assert inspect(repo, "main") == (second[-1], [first[-1]], 43)
  assert inspect(repo, first[-1], "id") == (first[-1], [], 42)
  second_bytes = [get(repo, kind, object_id).stdout for kind, object_id in zip(range(2, 7), second)]
  third = snapshot(repo, 44, first[-1], ref="branch")
  assert inspect(repo, "branch") == (third[-1], [first[-1]], 44)
  assert inspect(repo, "main") == (second[-1], [first[-1]], 43)
  assert first[-1] != second[-1] != third[-1]
  for objects, records in [(first, frozen), (second, second_bytes)]:
    for kind, object_id, packed in zip(range(2, 7), objects, records):
      assert get(repo, kind, object_id).stdout == packed
      assert run_driver("object-id", data=packed).stdout.strip().decode() == object_id


@settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.integers(min_value=-(2**63), max_value=2**63 - 1))
def test_snapshot_roundtrip_across_fresh_processes(tmp_path: pathlib.Path, value: int) -> None:
  # Each example uses its own initialized repository, never overwrites development data.
  repo = pathlib.Path(tempfile.mkdtemp(dir=tmp_path)) / "repo"
  objects = snapshot(repo, value)
  assert inspect(repo, "main") == (objects[-1], [], value)


@pytest.mark.parametrize("mode", ["abort", "poison"])
def test_object_inserts_and_ref_update_roll_back_together(tmp_path: pathlib.Path, mode: str) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  discarded = snapshot(repo, 43, first[-1], mode=mode)
  assert inspect(repo, "main") == (first[-1], [], 42)
  for kind, object_id in zip(range(2, 7), discarded):
    result = get(repo, kind, object_id, check=False)
    assert result.returncode == 1 and b"not_found" in result.stderr


def test_map_full_poisoning_and_full_batch_retry(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "map-full"
  history("map-full", str(repo))
  assert inspect(repo, "main")[2] == 43


def test_native_missing_wrong_type_lifecycle_and_ref_edges(tmp_path: pathlib.Path) -> None:
  history("negative", str(tmp_path / "negative"))


PREFIXES = {2: "datums", 3: "nodes", 4: "dags", 5: "trees", 6: "commits"}


def overwrite(repo: pathlib.Path, key: str, packed: bytes) -> None:
  run_driver("raw-write", str(repo), key, data=packed)


@pytest.mark.parametrize("kind", range(3, 7))
@pytest.mark.parametrize("corruption", ["bad_header", "wrong_type", "wrong_id"])
def test_reads_detect_corrupt_object_key_values(tmp_path: pathlib.Path, kind: int, corruption: str) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  second = snapshot(repo, 43, first[-1], mode="update")
  key = f"objects/{PREFIXES[kind]}/{first[kind - 2]}"
  original = get(repo, kind, first[kind - 2]).stdout
  if corruption == "bad_header":
    replacement = b"bad"
    expected = b"invalid_header"
  elif corruption == "wrong_type":
    replacement = get(repo, 2, first[0]).stdout
    expected = b"invalid_kind"
  else:
    replacement = get(repo, kind, second[kind - 2]).stdout
    expected = b"integrity_error"
  overwrite(repo, key, replacement)
  result = get(repo, kind, first[kind - 2], check=False)
  assert result.returncode == 1 and expected in result.stderr
  # A write cannot repair an immutable key by replacing its corrupted value.
  result = history("snapshot", str(repo), "42", "none", "another", "create", check=False)
  assert result.returncode == 1
  assert get(repo, kind, first[kind - 2], check=False).returncode == 1
  overwrite(repo, key, original)  # Test-only restoration to inspect rollback.
  assert inspect(repo, "main") == (second[-1], [first[-1]], 43)


@pytest.mark.parametrize("kind,child_kind", [(3, 2), (4, 3), (5, 4), (6, 5)])
def test_reads_and_writes_check_direct_referenced_object_types(tmp_path: pathlib.Path, kind: int, child_kind: int) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  key = f"objects/{PREFIXES[child_kind]}/{first[child_kind - 2]}"
  parent_record = get(repo, kind, first[kind - 2]).stdout
  # Put a valid object of another kind under the claimed typed key.
  wrong_kind = 3 if child_kind == 2 else 2
  overwrite(repo, key, get(repo, wrong_kind, first[wrong_kind - 2]).stdout)
  result = get(repo, kind, first[kind - 2], check=False)
  assert result.returncode == 1 and b"invalid_kind" in result.stderr
  result = put(repo, kind, parent_record, check=False)
  assert result.returncode == 1 and b"invalid_kind" in result.stderr


@pytest.mark.parametrize("replacement,expected", [(b"short", b"integrity_error"), (b"\xff" * 16, b"not_found")])
def test_ref_reads_reject_corruption_and_missing_targets(tmp_path: pathlib.Path, replacement: bytes, expected: bytes) -> None:
  repo = tmp_path / "repo"
  snapshot(repo, 42)
  overwrite(repo, "refs/heads/main", replacement)
  result = history("inspect", str(repo), "ref", "main", check=False)
  assert result.returncode == 1 and expected in result.stderr
  if replacement == b"short":
    result = history("snapshot", str(repo), "43", "none", "main", "update", check=False)
    assert result.returncode == 1 and b"integrity_error" in result.stderr


def test_ref_reads_check_target_type_and_identity(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  second = snapshot(repo, 43, first[-1], mode="update")
  key = f"objects/commits/{second[-1]}"
  overwrite(repo, key, get(repo, 2, first[0]).stdout)
  result = history("inspect", str(repo), "ref", "main", check=False)
  assert result.returncode == 1 and b"invalid_kind" in result.stderr
  overwrite(repo, key, get(repo, 6, first[-1]).stdout)
  result = history("inspect", str(repo), "ref", "main", check=False)
  assert result.returncode == 1 and b"integrity_error" in result.stderr


def test_backward_and_noop_ref_updates_preserve_snapshots(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  second = snapshot(repo, 43, first[-1], mode="update")
  frozen = get(repo, 6, second[-1]).stdout
  assert snapshot(repo, 42, mode="update") == first
  assert snapshot(repo, 42, mode="update") == first
  assert inspect(repo, "main") == (first[-1], [], 42)
  assert get(repo, 6, second[-1]).stdout == frozen


def test_ref_target_commit_checks_direct_tree_and_parents(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  second = snapshot(repo, 43, first[-1], mode="update")
  key = f"objects/commits/{first[-1]}"
  overwrite(repo, key, get(repo, 2, first[0]).stdout)
  result = history("inspect", str(repo), "ref", "main", check=False)
  assert result.returncode == 1 and b"invalid_kind" in result.stderr
  assert get(repo, 6, second[-1], check=False).returncode == 1


def test_direct_checks_do_not_claim_transitive_validation(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  overwrite(repo, f"objects/datums/{first[0]}", b"bad")
  # Commit's direct tree is intact; traversal reaches and rejects the bad datum.
  assert get(repo, 6, first[-1]).returncode == 0
  assert get(repo, 3, first[1], check=False).returncode == 1
  assert history("inspect", str(repo), "ref", "main", check=False).returncode == 1


def put(repo: pathlib.Path, kind: int, packed: bytes, check: bool = True) -> subprocess.CompletedProcess[bytes]:
  return run_driver("object-put", str(repo), str(kind), data=packed, check=check)


def test_multiple_parents_persist_in_supplied_order_without_merge(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  second = snapshot(repo, 43, first[-1], mode="update")
  third = snapshot(repo, 44, first[-1], ref="branch")
  tree = bytes.fromhex(second[3])
  parents = bytes.fromhex(third[-1]) + bytes.fromhex(second[-1])
  packed = encode(6, tree + struct.pack("<I", 2) + parents)
  commit_id = put(repo, 6, packed).stdout.strip().decode()
  assert get(repo, 6, commit_id).stdout == packed
  assert put(repo, 6, packed).stdout.strip().decode() == commit_id
  assert inspect(repo, commit_id, "id") == (commit_id, [third[-1], second[-1]], 43)
  reverse = encode(6, tree + struct.pack("<I", 2) + bytes.fromhex(second[-1]) + bytes.fromhex(third[-1]))
  assert put(repo, 6, reverse).stdout.strip().decode() != commit_id


@pytest.mark.parametrize("position", ["datum", "root", "entry", "tree", "parent"])
def test_missing_direct_references_reject_on_put_and_read(tmp_path: pathlib.Path, position: str) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  missing = b"\xff" * 16
  if position == "datum":
    kind, payload = 3, struct.pack("<I", 1) + missing
  elif position == "root":
    kind, payload = 4, missing
  elif position == "entry":
    kind, payload = 5, tree_payload([("example", missing)])
  elif position == "tree":
    kind, payload = 6, missing + struct.pack("<I", 0)
  else:
    kind, payload = 6, bytes.fromhex(first[3]) + struct.pack("<I", 1) + missing
  packed = encode(kind, payload)
  result = put(repo, kind, packed, check=False)
  assert result.returncode == 1 and b"not_found" in result.stderr
  object_id = run_driver("object-id", data=packed).stdout.strip().decode()
  assert get(repo, kind, object_id, check=False).returncode == 1
  overwrite(repo, f"objects/{PREFIXES[kind]}/{object_id}", packed)
  result = get(repo, kind, object_id, check=False)
  assert result.returncode == 1 and b"not_found" in result.stderr
  assert inspect(repo, "main") == (first[-1], [], 42)


def test_store_requires_explicit_matching_type(tmp_path: pathlib.Path) -> None:
  repo = tmp_path / "repo"
  first = snapshot(repo, 42)
  dag = get(repo, 4, first[2]).stdout
  result = put(repo, 3, dag, check=False)
  assert result.returncode == 1 and b"invalid_kind" in result.stderr
  assert inspect(repo, "main") == (first[-1], [], 42)
