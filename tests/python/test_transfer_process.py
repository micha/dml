"""Real map-full, private storage faults and pre/postcommit process loss."""

import errno
import importlib.machinery
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import daggerml as dml
from daggerml import transfer as tr
import pytest

from test_binding_failures import core
from test_transfer import assert_absent, doc, initialize, rich

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def transfer_runtime(tmp_path, monkeypatch):
    package = tmp_path / "runtime" / "daggerml"
    package.mkdir(parents=True)
    for name in ("__init__.py", "local.py", "transfer.py"):
        shutil.copyfile(ROOT / "python/daggerml/daggerml" / name, package / name)
    extension = Path(dml._core.__file__)
    assert any(str(extension).endswith(s) for s in importlib.machinery.EXTENSION_SUFFIXES)
    shutil.copyfile(extension, package / extension.name)
    monkeypatch.setenv("PYTHONPATH", str(package.parent))
    return package.parent


def reader(path, rows, keep, present):
    # Fresh public reader is a process-loss oracle, not the interrupted return value.
    code = """
import json,sys,daggerml as d
path,rows,keep,present=sys.argv[1:]
rows=json.loads(rows); present=present=='yes'
with d.Repository(path) as r,r.read() as t:
 assert str(t.get_ref('keep'))==keep
 for row in rows:
  try: raw=t.get_record(row['kind'],d.ObjectId.from_hex(row['id']))
  except d.NotFoundError: assert not present
  else:
   import base64
   assert present and raw==base64.b64decode(row['record'])
 try: target=t.get_ref('received')
 except d.NotFoundError: assert not present
 else: assert present and str(target)==rows[-1]['id']
print('fresh-reader-ok')
"""
    import json

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(path),
            json.dumps(rows),
            str(keep),
            "yes" if present else "no",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fresh-reader-ok"


@pytest.mark.parametrize("stage", ["pre", "post"])
def test_process_loss_at_actual_commit(tmp_path, transfer_runtime, stage):
    root, _, _, _ = rich(tmp_path / "a")
    _, keep = initialize(tmp_path / "b")
    bundle = tr.export_commit(tmp_path / "a", commit=root)
    file, marker = tmp_path / "bundle.json", tmp_path / "barrier"
    file.write_bytes(bundle)
    process = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "tests/python/transfer_interruption_parent.py"),
            str(tmp_path / "b"),
            str(file),
            str(marker),
            stage,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 20
        while not marker.exists() and time.monotonic() < deadline and process.poll() is None:
            time.sleep(0.02)
        assert marker.exists(), "private importer barrier not reached"
        process.terminate()
        process.wait(timeout=10)
        assert process.returncode != 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    reader(tmp_path / "b", doc(bundle)["objects"], keep, stage == "post")
    assert tr.import_commit(tmp_path / "b", bundle, ref="received").commit == root
    reader(tmp_path / "b", doc(bundle)["objects"], keep, True)


def test_real_small_map_abort_and_explicit_whole_retry(tmp_path, transfer_runtime):
    source, dest = tmp_path / "a", tmp_path / "b"
    with dml.Repository(source, create=True) as repo, repo.write() as tx:
        early = tx.put_datum("new prefix before map-full")
        huge = tx.put_datum(b"x" * (2 * 1024 * 1024))
        nodes = [tx.put_literal(oid) for oid in (early, huge)]
        root = tx.put_commit(
            tx.put_tree({"large": tx.put_dag(root=nodes[0], bindings={"big": nodes[1]})})
        )
    _, keep = initialize(dest)
    bundle = tr.export_commit(source, commit=root)
    with pytest.raises(dml.MapFullError):
        tr.import_commit(dest, bundle, ref="received", map_size=1024 * 1024)
    # Avoid huge OS argument/environment values; saved smaller prefix is enough for abort.
    rows = doc(bundle)["objects"][:2]
    reader(dest, rows, keep, False)
    assert_absent(dest, ("datum", early), keep)
    assert tr.import_commit(dest, bundle, ref="received", map_size=8 * 1024 * 1024).commit == root
    with dml.Repository(dest) as repo, repo.read() as tx:
        assert tx.get_datum(huge).value == b"x" * (2 * 1024 * 1024)
        assert tx.get_ref("keep") == keep


@pytest.mark.parametrize("fault", ["write", "commit"])
def test_real_native_fault_consumption_aborts_batch(tmp_path, core, fault):
    root, _, _, _ = rich(tmp_path / "a")
    _, keep = initialize(tmp_path / "b")
    bundle = tr.export_commit(tmp_path / "a", commit=root)
    row = doc(bundle)["objects"][0]
    core.native_fault(13 if fault == "write" else 15, 3 if fault == "write" else 1, errno.EIO)
    try:
        with pytest.raises(dml.DmlError):
            tr.import_commit(tmp_path / "b", bundle, ref="received")
    finally:
        core.native_fault(0, 0, 0)
    assert_absent(tmp_path / "b", (row["kind"], dml.ObjectId.from_hex(row["id"])), keep)


def test_insert_binding_allocation_error_poison(tmp_path, core):
    root, records, _, _ = rich(tmp_path / "a")
    with dml.Repository(tmp_path / "b", create=True) as repo:
        tx = repo.write()
        early = tx.put_datum("allocation abort oracle")
        core.set_fault(2, 1)  # Native put succeeds; Python ID-return allocation fails.
        try:
            with pytest.raises(MemoryError):
                tx.put_record(*("datum", records[0][1]))
        finally:
            core.set_fault(0, 0)
        with pytest.raises(dml.InvalidStateError):
            tx.commit()
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(early)


def test_stored_byte_mismatch_is_late_abort(tmp_path, monkeypatch):
    root, _, _, _ = rich(tmp_path / "a")
    _, keep = initialize(tmp_path / "b")
    bundle = tr.export_commit(tmp_path / "a", commit=root)
    row = doc(bundle)["objects"][0]
    original = dml.Transaction.get_record

    def mismatched(self, kind, oid):
        raw = original(self, kind, oid)
        return raw + b"x" if kind == "commit" else raw

    monkeypatch.setattr(dml.Transaction, "get_record", mismatched)
    with pytest.raises(tr.TransferError, match="stored record bytes"):
        tr.import_commit(tmp_path / "b", bundle, ref="received")
    monkeypatch.setattr(dml.Transaction, "get_record", original)
    assert_absent(tmp_path / "b", (row["kind"], dml.ObjectId.from_hex(row["id"])), keep)
