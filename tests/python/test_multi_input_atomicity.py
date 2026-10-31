"""NEW table authoring predicted actual-A rows, rollback and safe author-only loss."""

import errno
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_exchange import ROOT, exchange_runtime, tree, typed_oracle, literal
from test_exchange_launch import wait_file
from test_exchange_progress import _fresh_absence
from test_records_hypothesis import run_driver
from test_multi_input_reuse import (
    app,
    indexed,
    menu,
    double,
    producer,
    execute,
    expected_file,
)


@pytest.fixture
def author_state(indexed, request, menu, expected_file):
    path, definition, table, chosen, inserted = indexed
    if request.param == "insert":
        # Existing fixture already inserted the old row (unrooted bytes count too).
        # Capture a NEW absent S slot so actual-A predicted table rows are new.
        with d.Repository(path) as repo, repo.write() as tx:
            basis = tx.put_commit(
                tx.get_commit(chosen.commit).tree,
                parents=(chosen.commit, inserted.commit),
            )
        chosen = app.selection.select(
            path,
            commit=basis,
            slot="insertion-new",
            binding_name="double-a-binding",
            inputs_name="double-inputs",
            intent_uri=definition.intent_uri,
            packet=menu[0][2][0],
            expected_file=expected_file,
            ref="insertion-capture",
        )
        return path, chosen.commit, chosen.slot, "insert"
    packet, expected, received, _, workspace = execute(
        path,
        inserted.commit,
        "fresh",
        binding="double-a-binding",
        inputs="double-inputs",
    )
    expected_path = path.parent / "fresh-expected.json"
    ex.save_exchange_handle(expected_path, ex.ExchangeHandle(workspace, expected))
    fresh = app.selection.select(
        path,
        commit=received.commit,
        slot="immutable-fresh",
        binding_name="double-a-binding",
        inputs_name="double-inputs",
        intent_uri=definition.intent_uri,
        packet=packet,
        expected_file=expected_path,
        ref="fresh-capture",
    )
    return path, fresh.commit, fresh.slot, "adopt"


def author(state, **changes):
    path, basis, slot, mode = state
    args = dict(commit=basis, table_name="table", selection_slot=slot, ref="authored")
    args.update(changes)
    return (app.select_entry if mode == "insert" else app.adopt_entry)(path, **args)


def prediction(state):
    path, basis, slot, mode = state
    with d.Repository(path) as repo, repo.write() as tx:
        proof = tx.put_commit(
            tx.put_tree({"unrooted": tx.put_dag(root=literal(tx, "old proof"))})
        )
    copied = path.parent / "prediction"
    with d.Repository(copied, create=True):
        pass
    for root in (basis, proof):
        transfer.import_commit(copied, transfer.export_commit(path, commit=root))
    predicted = author((copied, basis, slot, mode))
    old = typed_oracle(path, (basis, proof))
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
    "author_state,fault",
    [
        ("insert", "different-ref"),
        ("adopt", "raw-ref"),
        ("insert", "allocation"),
        ("adopt", "response"),
        ("insert", "commit"),
        ("adopt", "map-full"),
    ],
    indirect=["author_state"],
)
def test_table_new_actual_A_puts_then_late_atomic_rollback(
    author_state, exchange_runtime, core, monkeypatch, fault
):
    path, basis, _, _ = author_state
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
        response_type = app.Table

        def fail(*a, **k):
            if a[0] != basis:
                raise MemoryError("precommit table response")
            return response_type(*a, **k)

        monkeypatch.setattr(app, "Table", fail)
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


@pytest.mark.parametrize(
    "author_state,boundary",
    [("insert", "pre"), ("adopt", "post")],
    indirect=["author_state"],
)
def test_author_only_loss_no_computational_child_absent_or_complete(
    author_state, exchange_runtime, boundary
):
    path, basis, slot, mode = author_state
    predicted, old, complete, new, proof = prediction(author_state)
    before = (path / "data.mdb").read_bytes()
    marker = path.parent / "barrier"
    with (path.parent / "author.stderr").open("wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/multi_input_interruption_parent.py"),
                str(path),
                str(basis),
                slot,
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
            entries = tree(tx, basis)
            entries["table"] = predicted.dag
            assert tree(tx, predicted.commit) == entries
    if boundary == "pre":
        assert_file_unchanged(path / "data.mdb", before)
        _fresh_absence(path, old, new)
    else:
        assert typed_oracle(path, (predicted.commit, proof)) == complete
