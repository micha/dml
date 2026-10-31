"""NEW L actual-A predicted absence, old proof, late rollback and safe author loss."""

import errno
import subprocess
import sys

import daggerml as d
from daggerml import transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_exchange import ROOT, exchange_runtime, literal, tree, typed_oracle
from test_exchange_launch import wait_file
from test_exchange_progress import _fresh_absence
from test_records_hypothesis import run_driver
from test_implementation_supersession import app, state, author


def prediction(state):
    path, definition = state
    with d.Repository(path) as repo, repo.write() as tx:
        proof = tx.put_commit(
            tx.put_tree({"unrooted": tx.put_dag(root=literal(tx, "old proof"))})
        )
    copied = path.parent / "prediction"
    with d.Repository(copied, create=True):
        pass
    for root in (definition.commit, proof):
        transfer.import_commit(copied, transfer.export_commit(path, commit=root))
    predicted = author((copied, definition))
    old = typed_oracle(path, (definition.commit, proof))
    complete = typed_oracle(copied, (predicted.commit, proof))
    new = {key: raw for key, raw in complete.items() if key not in old}
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    assert {"dag", "tree", "commit"} <= {kind for kind, _ in new}
    assert all(complete[key] == raw for key, raw in old.items())
    return predicted, old, complete, new, proof


@pytest.mark.parametrize(
    "fault",
    ["different-ref", "raw-ref", "allocation", "response", "commit", "map-full"],
)
def test_new_L_actual_A_new_puts_then_late_batch_rollback(
    state, exchange_runtime, core, monkeypatch, fault
):
    path, definition = state
    if fault == "different-ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("declared", definition.commit)
    elif fault == "raw-ref":
        run_driver("raw-write", str(path), "refs/heads/declared", data=b"invalid")
    predicted, old, complete, new, proof = prediction(state)
    before = (path / "data.mdb").read_bytes()
    creating = d.Transaction.create_ref

    def late(self, name, target):
        if name == "declared":
            if fault == "allocation":
                core.native_fault(1, 1, 0)
            elif fault == "commit":
                core.native_fault(15, 1, errno.EIO)
            elif fault == "map-full":
                self.put_datum(b"x" * (2 * 1024 * 1024))
        return creating(self, name, target)

    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":

        def fail(*a, **k):
            raise MemoryError("precommit L response")

        monkeypatch.setattr(app, "Supersession", fail)
    try:
        with track_typed_puts(path, old) as puts:
            with pytest.raises((d.DmlError, MemoryError)):
                author(state, map_size=1048576 if fault == "map-full" else 0)
    finally:
        core.native_fault(0, 0, 0)
    assert puts == new
    if fault == "map-full":
        with d.Repository(path):
            pass
    assert_file_unchanged(path / "data.mdb", before)
    _fresh_absence(path, old, new)


@pytest.mark.parametrize("boundary", ["pre", "post"])
def test_authoring_only_loss_no_child_absent_or_complete_new_L(
    state, exchange_runtime, boundary
):
    path, definition = state
    predicted, old, complete, new, proof = prediction(state)
    before = (path / "data.mdb").read_bytes()
    marker = path.parent / "store-barrier"
    with (path.parent / "authoring.stderr").open("wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/supersession_interruption_parent.py"),
                str(path),
                str(definition.commit),
                str(marker),
                boundary,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            wait_file(marker, process, timeout=15)
            process.terminate()  # ONLY authoring, no computational child exists.
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    with d.Repository(path) as repo, repo.read() as tx:
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        if boundary == "pre":
            with pytest.raises(d.NotFoundError):
                tx.get_ref("declared")
        else:
            assert tx.get_ref("declared") == predicted.commit
            assert tx.get_commit(predicted.commit).parents == (definition.commit,)
            entries = tree(tx, definition.commit)
            entries[predicted.slot] = predicted.dag
            assert tree(tx, predicted.commit) == entries
    if boundary == "pre":
        assert_file_unchanged(path / "data.mdb", before)
        _fresh_absence(path, old, new)
    else:
        assert typed_oracle(path, (predicted.commit, proof)) == complete
