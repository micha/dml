import json
import os
from pathlib import Path
import subprocess

import daggerml as dml
import pytest

from test_python_api import snapshot

ROOT = Path(__file__).resolve().parents[2]
BUILD = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml")).resolve().parent
DRIVER = BUILD / ("test_cli_fault_driver.exe" if os.name == "nt" else "test_cli_fault_driver")


@pytest.fixture
def history_fixture(tmp_path):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            first = snapshot(tx, 'a"\\\n\u0085' + "é"*90)
            second = snapshot(tx, dml.Datum.uri("https://example.org/"), [first["commit"]])
            nested_node = tx.put_subdag(first["dag"])
            second["nested_node"] = nested_node
            second["nested"] = tx.put_dag(root=nested_node, bindings={"a": nested_node, "b": first["node"]})
            second["nested_commit"] = tx.put_commit(tx.put_tree({"nested": second["nested"]}))
            tx.create_ref("main", second["commit"])
    return path, first, second


@pytest.mark.parametrize("command", ["log", "snapshot", "snapshot-uri", "show", "show-uri", "ref", "walk", "lookup", "show-dag", "show-subdag", "snapshot-subdag"])
def test_cli_allocation_failure_sweep(history_fixture, command):
    path, first, second = history_fixture
    args = {"log": ["log", "--ref", "main"], "snapshot": ["snapshot", "--commit", str(first["commit"])],
            "show": ["show", "datum", str(first["datum"])], "ref": ["ref", "get", "main"],
            "show-uri": ["show", "datum", str(second["datum"])],
            "snapshot-subdag": ["snapshot", "--commit", str(second["nested_commit"])],
            "walk": ["walk", str(second["nested"])], "lookup": ["lookup", str(second["nested"]), "a"],
            "show-dag": ["show", "dag", str(second["nested"])],
            "show-subdag": ["show", "node", str(second["nested_node"])],
            "snapshot-uri": ["snapshot", "--commit", str(second["commit"])]}[command]
    failed = 0
    for nth in range(1, 2000):
        result = subprocess.run([str(DRIVER), "1", str(nth), "--json", "--repo", str(path), *args], capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            assert json.loads(result.stdout)["command"]
            break
        failed += 1
        assert result.returncode == 1 and result.stdout == "", result.stderr
        assert json.loads(result.stderr)["error"]["code"] == "out_of_memory"
    else:
        pytest.fail("allocation sweep did not reach an uninjected successful run")
    assert failed > 3


@pytest.mark.parametrize("args", [["--version"], ["--help"], ["--json", "--repo", "REPO", "log", "--ref", "main"],
                                  ["--json", "--repo", "REPO", "walk", "NESTED"],
                                  ["--repo", "REPO", "lookup", "NESTED", "a"],
                                  ["--repo", "REPO", "show", "datum", "DATUM"]])
def test_cli_output_failure_sweep(history_fixture, args):
    path, first, second = history_fixture
    args = [str(path) if arg == "REPO" else str(first["datum"]) if arg == "DATUM" else str(second["nested"]) if arg == "NESTED" else arg for arg in args]
    failures = 0
    for nth in range(1, 1500):
        result = subprocess.run([str(DRIVER), "2", str(nth), *args], capture_output=True)
        if result.returncode == 0:
            break
        assert result.returncode == 1
        failures += 1
    else:
        pytest.fail("output sweep did not reach an uninjected successful run")
    assert failures >= 2


def test_diagnostic_allocation_failure_and_cycle_detection(history_fixture):
    from test_history import overwrite
    from test_objects_hypothesis import encode
    import struct
    path, first, second = history_fixture
    fallback = False
    for nth in range(1, 50):
        result = subprocess.run([str(DRIVER), "1", str(nth), "--json", "--repo", str(path), "ref", "get", "unknown"], capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 1 and result.stdout == ""
        error = json.loads(result.stderr)["error"]
        fallback |= error["detail"] == "diagnostic allocation failed"
    assert fallback
    # Simulated constant hash permits a content-addressed cycle in a private
    # test fixture. This is not a discovered real XXH3 collision.
    zero = "0"*32
    overwrite(path, "objects/trees/" + zero, encode(5, struct.pack("<I", 0)))
    overwrite(path, "objects/commits/" + zero,
              encode(6, bytes(16) + struct.pack("<I", 1) + bytes(16)))
    result = subprocess.run([str(DRIVER), "3", "0", "--json", "--repo", str(path), "log", "--commit", zero], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"]["code"] == "integrity_error"
    assert "cycle" in result.stderr
    overwrite(path, "objects/dags/" + zero, encode(4, bytes(16) + struct.pack("<I", 0)))
    overwrite(path, "objects/nodes/" + zero, encode(3, struct.pack("<I", 2) + bytes(16)))
    for limit in [2, 3, 100]:
        result = subprocess.run([str(DRIVER), "3", "0", "--json", "--repo", str(path), "walk", zero,
                                 "--limit", str(limit)], capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 1 and result.stdout == ""
        assert "cycle in traversed DAG" in json.loads(result.stderr)["error"]["detail"]
    # A bounded prefix ending before the active edge is encountered isn't a cycle proof.
    result = subprocess.run([str(DRIVER), "3", "0", "--json", "--repo", str(path), "walk", zero,
                             "--limit", "1"], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0 and json.loads(result.stdout)["truncated"]
    result = subprocess.run([str(DRIVER), "4", "0", "--help"], capture_output=True)
    assert result.returncode == 0 and result.stdout == b""
