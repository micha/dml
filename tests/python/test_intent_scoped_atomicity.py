"""Representative NEW removal/direct-W actual-A rollback and author-only loss."""

from dataclasses import replace
import errno
import subprocess
import sys

import daggerml as d
from daggerml import transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_exchange import ROOT, exchange_runtime, tree, typed_oracle, literal
from test_exchange_launch import wait_file
from test_exchange_progress import _fresh_absence
from test_records_hypothesis import run_driver
from test_intent_scoped_reuse import (
    app,
    indexed,
    menu,
    double,
    producer,
    execute,
    expected_file,
    table_request,
)


@pytest.fixture
def author_state(indexed, request):
    path, _, _, selected, table = indexed
    if request.param == "remove":
        # Preserve a later non-table entry so the removed tree is genuinely NEW,
        # not the already-retained pre-insertion capture tree.
        with d.Repository(path) as repo, repo.write() as tx:
            entries = tree(tx, table.commit)
            entries["later-note"] = tx.put_dag(root=literal(tx, "preserve me"))
            basis = tx.put_commit(tx.put_tree(entries), parents=(table.commit,))
        return path, basis, selected, None, "remove"
    pending = table_request(
        indexed, implementation_override="double-b", override="fresh", reuse_ref=None
    )
    return path, pending.recorded.commit, selected, pending.recorded, "W"


def author(state, **changes):
    path, basis, selected, recorded, mode = state
    if mode == "remove":
        return app.remove_entry(
            path,
            commit=basis,
            table_name="table",
            inputs=selected.inputs,
            ref="authored",
            **changes,
        )
    return app._publish_reuse(
        path, recorded, selected, "authored", changes.get("map_size", 0)
    )


def prediction(state):
    path, basis, selected, recorded, mode = state
    with d.Repository(path) as repo, repo.write() as tx:
        proof = tx.put_commit(
            tx.put_tree(
                {"unrooted": tx.put_dag(root=literal(tx, "old unrooted proof"))}
            )
        )
    copied = path.parent / "prediction"
    with d.Repository(copied, create=True):
        pass
    for root in (basis, proof):
        transfer.import_commit(copied, transfer.export_commit(path, commit=root))
    predicted = author((copied, basis, selected, recorded, mode))
    old = typed_oracle(path, (basis, proof))
    complete = typed_oracle(copied, (predicted.commit, proof))
    new = {key: raw for key, raw in complete.items() if key not in old}
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    # Last-row removal legitimately deduplicates the retained original empty Mi.
    assert {"tree", "commit"} <= {kind for kind, _ in new}
    if mode == "W":
        assert "dag" in {kind for kind, _ in new}
    assert all(complete[key] == raw for key, raw in old.items())
    return predicted, old, complete, new, proof


@pytest.mark.parametrize("author_state", ["remove", "W"], indirect=True)
@pytest.mark.parametrize(
    "fault",
    ["different-ref", "raw-ref", "allocation", "response", "commit", "map-full"],
)
def test_new_batches_late_atomic_rollback(
    author_state, exchange_runtime, core, monkeypatch, fault
):
    path, basis, _, recorded, mode = author_state
    if fault == "different-ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("authored", basis)
    elif fault == "raw-ref":
        run_driver("raw-write", str(path), "refs/heads/authored", data=b"invalid")
    predicted, old, complete, new, proof = prediction(author_state)
    before = (path / "data.mdb").read_bytes()
    creating = d.Transaction.create_ref

    def late(self, name, target):
        if name == "authored":
            if fault == "allocation":
                core.native_fault(1, 1, 0)
            elif fault == "commit":
                core.native_fault(15, 1, errno.EIO)
            elif fault == "map-full":
                self.put_datum(b"x" * (2 * 1024 * 1024))
        return creating(self, name, target)

    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        response_type = app.Table if mode == "remove" else app.Reused

        def fail(*a, **k):
            if mode == "W" or a[0] != basis:
                raise MemoryError("precommit owned response")
            return response_type(*a, **k)

        monkeypatch.setattr(app, "Table" if mode == "remove" else "Reused", fail)
    try:
        with track_typed_puts(path, old) as puts:
            with pytest.raises((d.DmlError, MemoryError)):
                author(author_state, map_size=1048576 if fault == "map-full" else 0)
    finally:
        core.native_fault(0, 0, 0)
    assert puts == new
    if fault == "map-full":
        with d.Repository(path):
            pass
    assert_file_unchanged(path / "data.mdb", before)
    _fresh_absence(path, old, new)
    if recorded is not None:
        with d.Repository(path) as repo, repo.read() as tx:
            assert tx.get_ref(recorded.ref) == recorded.commit


@pytest.mark.parametrize("author_state", ["remove", "W"], indirect=True)
@pytest.mark.parametrize("boundary", ["pre", "post"])
def test_author_only_loss_absent_or_complete(author_state, exchange_runtime, boundary):
    path, basis, selected, recorded, mode = author_state
    predicted, old, complete, new, proof = prediction(author_state)
    before = (path / "data.mdb").read_bytes()
    marker = path.parent / "barrier"
    with (path.parent / "author.stderr").open("wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/intent_scoped_interruption_parent.py"),
                str(path),
                str(basis),
                selected.slot,
                mode,
                str(marker),
                boundary,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            wait_file(marker, process, timeout=15)
            process.terminate()
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    with d.Repository(path) as repo, repo.read() as tx:
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        if boundary == "pre":
            with pytest.raises(d.NotFoundError):
                tx.get_ref("authored")
        else:
            assert tx.get_ref("authored") == predicted.commit
            assert tx.get_commit(predicted.commit).parents == (basis,)
    if boundary == "pre":
        assert_file_unchanged(path / "data.mdb", before)
        _fresh_absence(path, old, new)
    else:
        assert typed_oracle(path, (predicted.commit, proof)) == complete
