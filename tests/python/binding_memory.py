"""Standalone Valgrind workload for supported binding ownership/failure paths.

The unsupported foreign-last-owner abandonment case intentionally leaks and is
covered separately in isolated subprocess tests, not in this leak-free workload.
"""

import gc
from pathlib import Path
import runpy
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT / "tests/conftest.py"))

import daggerml as dml
import importlib.util

BUILD = Path(dml._core.__file__).parent
spec = importlib.util.spec_from_file_location("_core_fault", next(p for p in BUILD.glob("_core_fault.*") if p.is_file()))
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
dml._core = core

# Runtime-only comparison: same imports, but no repository/binding workload.
import os
import sys
if os.environ.get("DML_MEMORY_BASELINE") == "1":
    raise SystemExit(0)

with tempfile.TemporaryDirectory() as scratch:
    path = Path(scratch) / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            child = tx.put_datum(42)
            second_child = tx.put_datum(43)
            node = tx.put_literal(child); dag = tx.put_dag(root=node)
            tree = tx.put_tree({"example": dag}); first = tx.put_commit(tree)
            commit = tx.put_commit(tree, parents=[first]); tx.create_ref("main", commit)
            values = [tx.put_datum(value) for value in [None, True, False, -(2**63), -42, 4.5, -3.25,
                      b"bytes", "text", dml.Datum.uri("https://example.org/"),
                      dml.Datum.list([]), dml.Datum.set([]), dml.Datum.map([]),
                      dml.Datum.list([child, second_child]), dml.Datum.set([child, second_child]),
                      dml.Datum.map([(child, child), (second_child, second_child)])]]
        for kind in [1, 2, 3]:
            for nth in range(1, 30):
                tx = repo.write()
                if kind == 3:
                    core.native_fault(1, nth, 0)
                else:
                    core.set_fault(kind, nth)
                try:
                    value = tx.put_datum(dml.Datum.map([(child, child), (second_child, second_child)]))
                    tx.put_tree({"example": dag})
                    tx.put_commit(tree, parents=[first])
                except (MemoryError, dml.DmlError):
                    pass
                finally:
                    core.set_fault(0, 0); core.native_fault(0, 0, 0)
                    tx.abort()
        with repo.read() as tx:
            for nth in range(1, 35):
                core.set_fault(2, nth)
                try:
                    descriptions = [tx.get_datum(value) for value in values]
                    tx.get_commit(commit); tx.get_tree(tree); tx.get_ref("main")
                except MemoryError:
                    pass
                finally:
                    core.set_fault(0, 0)
        tx = repo.write()
        tx.put_datum(99)
        box = [tx]; del tx
        thread = threading.Thread(target=box.clear); thread.start(); thread.join()
        repo.close()  # Legal owner-thread reclamation of the queued native txn.
    gc.collect()
print("binding memory workload passed")
