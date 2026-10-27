import gc
import os
from pathlib import Path
import subprocess
import sys
import threading

import daggerml as dml
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_foreign_last_owner_reference_safe_abandonment(tmp_path):
    # Unsupported owner-thread lifetime is tested in a disposable process: a
    # legal native cleanup thread no longer exists. ResourceWarning is explicit,
    # and the child deliberately abandons native resources rather than aborting
    # the transaction from the foreign thread. This is NOT a leak-free case.
    setup = f"import runpy; runpy.run_path({str(ROOT / 'tests/conftest.py')!r})\n"
    body = f"""
import daggerml as dml, gc, threading, warnings
warnings.simplefilter('always', ResourceWarning)
repo = dml.Repository({str(tmp_path / 'repo')!r}, create=True)
tx = repo.write()
tx.put_datum(42)
box = [tx, repo]
del tx, repo
def drop():
    box.clear()
    gc.collect()
thread = threading.Thread(target=drop)
thread.start(); thread.join()
print('safe abandonment')
"""
    result = subprocess.run([sys.executable, "-c", setup + body], capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.strip() == "safe abandonment"
    assert "native resources abandoned" in result.stderr
    assert "Exception ignored" not in result.stderr
    assert "SystemError" not in result.stderr
    assert "unraisable" not in result.stderr


@pytest.mark.parametrize("warning_error", [False, True])
def test_foreign_abandonment_warning_as_error_is_unraisable(tmp_path, warning_error):
    setup = f"import runpy; runpy.run_path({str(ROOT / 'tests/conftest.py')!r})\n"
    body = f"""
import daggerml as dml, gc, threading, warnings, sys
warnings.simplefilter({'error' if warning_error else 'ignore'!r}, ResourceWarning)
errors = []
sys.unraisablehook = lambda error: errors.append(str(error.exc_value))
repo = dml.Repository({str(tmp_path / 'repo')!r}, create=True)
tx = repo.write()
box = [tx, repo]
del tx, repo
thread = threading.Thread(target=box.clear)
thread.start(); thread.join()
assert len(errors) == {int(warning_error)}
"""
    result = subprocess.run([sys.executable, "-c", setup + body], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_native_pending_reclaimed_by_owner_capsule_destructor(tmp_path):
    core = dml._core
    repo = core.repo_open(str(tmp_path / "repo"), True, 0)
    tx = core.txn_begin(repo, True)
    box = [tx]
    del tx
    thread = threading.Thread(target=box.clear); thread.start(); thread.join()
    del repo  # Reap on creating thread even without a public close() invocation.
    gc.collect()
    with dml.Repository(tmp_path / "repo") as owner:
        with owner.write() as tx:
            tx.put_datum(42)


def test_native_ref_and_handle_errors(tmp_path):
    core = dml._core
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        with repo.write() as tx:
            tree = tx.put_tree({}); commit = tx.put_commit(tree)
            tx.create_ref("main", commit)
        for op in [lambda tx: tx.create_ref("main", commit), lambda tx: tx.update_ref("missing", commit)]:
            tx = repo.write()
            with pytest.raises(dml.DmlError):
                op(tx)
            tx.abort()
        with repo.read() as tx:
            with pytest.raises(TypeError):
                core.ref_op(tx._handle, 1, "main", 1)
        for function, args in [(core.put_record, (None, 2, b"bad")),
                               (core.ref_op, (None, 0, "main", None))]:
            with pytest.raises(ValueError):
                function(*args)
    for kind, value in [(10, (1,)), (10, ((b"\0"*16, b"short"),))]:
        with pytest.raises((TypeError, ValueError)):
            core.encode_datum(kind, value)
    with pytest.raises(TypeError):
        core.encode_object(5, (1,), None)
