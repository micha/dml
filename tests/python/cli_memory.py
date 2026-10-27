"""Valgrind native inspection commands and their injected allocation boundaries."""

import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT / "tests/conftest.py"))
import daggerml as dml

BUILD = Path(dml._core.__file__).parent
DRIVER = BUILD / ("test_cli_fault_driver.exe" if os.name == "nt" else "test_cli_fault_driver")
count = 0
with tempfile.TemporaryDirectory() as scratch:
    path = Path(scratch) / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            value = tx.put_datum('a"\\\n\u0085' + "é"*90)
            node = tx.put_literal(value)
            dag = tx.put_dag(root=node, bindings={"a": node, "b": node})
            subdag = tx.put_subdag(dag)
            nested = tx.put_dag(root=subdag, bindings={"trial": subdag, "value": node})
            nested_commit = tx.put_commit(tx.put_tree({"nested": nested}))
            tree = tx.put_tree({"example": dag}); first = tx.put_commit(tree)
            second = tx.put_commit(tree, parents=[first]); tx.create_ref("main", second)
            large_values = ["payloadé\n" * 400, bytes(range(256)) * 16]
            large_ids = [tx.put_datum(item) for item in large_values]
    for args in [["ref", "get", "main"], ["show", "datum", str(value)],
                 ["snapshot", "--ref", "main"], ["log", "--ref", "main"],
                 ["walk", str(nested)], ["lookup", str(nested), "trial"],
                 ["show", "dag", str(nested)], ["show", "node", str(subdag)],
                 ["snapshot", "--commit", str(nested_commit)]]:
        for nth in range(1, 500):
            result = subprocess.run([
                "valgrind", "--error-exitcode=101", "--leak-check=full", "--show-leak-kinds=all", "--track-origins=yes",
                str(DRIVER), "1", str(nth), "--json", "--repo", str(path), *args,
            ], capture_output=True)
            count += 1
            assert result.returncode in (0, 1), result.stderr.decode(errors="replace")
            assert b"ERROR SUMMARY: 0 errors" in result.stderr
            assert b"in use at exit: 0 bytes" in result.stderr
            if result.returncode == 0:
                break
        else:
            raise AssertionError("allocation sweep never succeeded")
    # Two large real outputs, not thousands of fault-sweep subprocesses. This
    # checks growth/NUL boundaries after the initial 1024-byte output allocation.
    native = BUILD / ("dml.exe" if os.name == "nt" else "dml")
    for identity, expected in zip(large_ids, large_values):
        result = subprocess.run([
            "valgrind", "--error-exitcode=101", "--leak-check=full", "--show-leak-kinds=all", "--track-origins=yes",
            str(native), "--json", "--repo", str(path), "show", "datum", str(identity),
        ], capture_output=True)
        count += 1
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        assert b"ERROR SUMMARY: 0 errors" in result.stderr
        assert b"in use at exit: 0 bytes" in result.stderr
        description = json.loads(result.stdout)["datum"]
        assert description["value"] == (expected.hex() if type(expected) is bytes else expected)
        assert len(result.stdout) > 4096
print(f"native CLI memory workload passed: {count} Valgrind processes")
