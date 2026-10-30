"""Genuinely NEW actual-A S/V rollback and safe authoring-only commit loss."""

import errno
from pathlib import Path
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_composed_execution import producer, execute
from test_exchange import ROOT, exchange_runtime, tree, typed_oracle
from test_exchange_launch import wait_file
from test_exchange_progress import _fresh_absence
from test_explicit_reuse import double
from test_records_hypothesis import run_driver
from test_reuse_selection import app, expected_file, select
from test_reuse_selection_records import selection, adopt


def operation(double, expected_file, selection, mode):
    path = double[0][0]
    if mode == "select":
        basis = double[2][2].commit

        def invoke(destination=path, **changes):
            return app.select(
                destination,
                commit=basis,
                slot="selected-new",
                binding_name="double-binding",
                inputs_name="double-inputs",
                intent_uri="urn:example:double",
                packet=double[2][0],
                expected_file=expected_file,
                ref="authored",
                **changes,
            )

        return basis, invoke, double[2][0], expected_file
    fresh = execute(
        path, selection.commit, "fresh-double", "double-binding", "double-inputs"
    )
    saved = path.parent / "fresh-authoring-expected"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(fresh[4], fresh[1]))
    basis = fresh[2].commit

    def invoke(destination=path, **changes):
        return app.adopt(
            destination,
            commit=basis,
            slot="selected-double",
            binding_name="double-binding",
            inputs_name="double-inputs",
            intent_uri="urn:example:double",
            packet=fresh[0],
            expected_file=saved,
            ref="authored",
            **changes,
        )

    return basis, invoke, fresh[0], saved


@pytest.mark.parametrize("mode", ["select", "adopt"])
@pytest.mark.parametrize(
    "fault",
    ["different-ref", "raw-ref", "allocation", "response", "commit", "map-full"],
)
def test_new_actual_A_S_V_batch_readback_then_complete_native_raw_physical_abort(
    double, expected_file, core, monkeypatch, mode, fault
):
    path, base, _ = double[0]
    selection = select(double, expected_file) if mode == "adopt" else None
    basis, invoke, _, __ = operation(double, expected_file, selection, mode)
    if fault == "different-ref":
        with d.Repository(path) as repository, repository.write() as tx:
            tx.create_ref("authored", base)
    elif fault == "raw-ref":
        run_driver("raw-write", str(path), "refs/heads/authored", data=b"raw-invalid")
    baseline = typed_oracle(path, (basis, base))
    prediction = path.parent / "prediction"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(prediction, transfer.export_commit(path, commit=basis))
    predicted = invoke(prediction)
    predicted_new = {
        key: raw
        for key, raw in typed_oracle(prediction, (predicted.commit,)).items()
        if key not in baseline
    }
    # Independent real native absence BEFORE actual authoring, not export-only
    # absence. Initial select has NO precreated S/V; adoption retains all old proof
    # through fresh F. No identical unrooted proof can qualify as a new row.
    with d.Repository(path) as repository, repository.read() as tx:
        for key in predicted_new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
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
        # Adoption's old inspect also allocates Selection; fault ONLY new response.
        real = app.Selection

        def response(*a):
            if a[0] == basis:
                return real(*a)
            raise MemoryError("private precommit response allocation")

        monkeypatch.setattr(app, "Selection", response)
    try:
        with track_typed_puts(path, baseline) as puts:
            with pytest.raises((d.DmlError, MemoryError)):
                invoke(map_size=1048576 if fault == "map-full" else 0)
    finally:
        core.native_fault(0, 0, 0)
    assert puts == predicted_new  # EVERY genuinely new actual-A packed byte/readback.
    # Not validation-store/preexisting proof puts: exact actual repository filter.
    assert {"datum", "node", "dag", "tree", "commit"} <= {kind for kind, _ in puts}
    assert sum(kind == "dag" for kind, _ in puts) == 2  # genuinely new S AND V
    assert sum(kind == "tree" for kind, _ in puts) == 1
    assert sum(kind == "commit" for kind, _ in puts) == 1
    if fault == "map-full":
        with d.Repository(path):
            pass  # Restore comparable default physical layout on Windows, no writes.
    assert_file_unchanged(path / "data.mdb", before)
    _fresh_absence(path, baseline, puts)
    with d.Repository(path) as repository, repository.read() as tx:
        if selection is not None:
            assert tx.get_ref("selection-old") == selection.commit
            assert tree(tx, basis)["selected-double"] == selection.dag
        assert tx.get_ref("main") == base


@pytest.mark.parametrize("mode", ["select", "adopt"])
@pytest.mark.parametrize("boundary", ["pre", "post"])
def test_actual_authoring_only_store_commit_loss_predicts_every_new_row_parent_slot_ref(
    double, expected_file, mode, boundary
):
    path = double[0][0]
    selection = select(double, expected_file) if mode == "adopt" else None
    basis, invoke, packet, saved = operation(double, expected_file, selection, mode)
    original = typed_oracle(path, (basis,))
    prediction = path.parent / "prediction"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(prediction, transfer.export_commit(path, commit=basis))
    predicted = invoke(prediction)
    all_bytes = typed_oracle(prediction, (predicted.commit,))
    new = {key: raw for key, raw in all_bytes.items() if key not in original}
    assert sum(kind == "dag" for kind, _ in new) == 2
    with d.Repository(path) as repository, repository.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    before = (path / "data.mdb").read_bytes()
    marker = path.parent / "store-barrier"
    with (path.parent / "authoring.stderr").open("wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/selection_interruption_parent.py"),
                str(ROOT / "examples/reuse_selection.py"),
                mode,
                str(path),
                str(basis),
                str(packet),
                str(saved),
                str(marker),
                boundary,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            wait_file(marker, process, timeout=15)
            process.terminate()  # Authoring ONLY. No live computational child/job.
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    with d.Repository(path) as repository, repository.read() as tx:
        assert all(tx.get_record(*key) == raw for key, raw in original.items())
        if selection is not None:
            assert tx.get_ref("selection-old") == selection.commit
        if boundary == "pre":
            with pytest.raises(d.NotFoundError):
                tx.get_ref("authored")
        else:
            assert tx.get_ref("authored") == predicted.commit
            assert tx.get_commit(predicted.commit).parents == (basis,)
            entries = tree(tx, basis)
            entries[predicted.slot] = predicted.dag
            assert tree(tx, predicted.commit) == entries
    if boundary == "pre":
        assert_file_unchanged(path / "data.mdb", before)
        _fresh_absence(path, original, new)
    else:
        assert typed_oracle(path, (predicted.commit,)) == all_bytes
