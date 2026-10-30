"""Actual-A new Idef/D bytes/late abort and authoring-only store-response loss."""

import errno
from pathlib import Path
import subprocess
import sys

import daggerml as d
from daggerml import transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_composed_execution import producer
from test_exchange import ROOT, exchange_runtime, tree, typed_oracle
from test_exchange_launch import wait_file
from test_exchange_progress import _fresh_absence
from test_explicit_reuse import double
from test_intent_defaults import app, define, request
from test_records_hypothesis import run_driver


def operation(double, mode):
    path = double[0][0]
    basis = double[2][2].commit
    if mode == "definition":

        def invoke(destination=path, **changes):
            return app.define(
                destination,
                commit=basis,
                intent_name="double-intent",
                intent_uri="urn:example:double",
                default="execute-by-default",
                ref="authored",
                **changes,
            )

    else:
        definition = define(double, default="execute-by-default")
        basis = definition.commit

        def invoke(destination=path, **changes):
            return request(
                destination, basis, decision_ref="authored", **changes
            ).decision

    with d.Repository(path) as repository, repository.write() as tx:
        # Deliberately unrooted old proof rows are ACTUAL A state, not part of C.
        node = tx.put_literal(tx.put_datum("unrooted-old-proof"))
        proof = tx.put_commit(tx.put_tree({"old-proof": tx.put_dag(root=node)}))
    return basis, invoke, proof


def prediction(path, basis, invoke, proof):
    predicted_path = path.parent / "prediction"
    with d.Repository(predicted_path, create=True):
        pass
    transfer.import_commit(predicted_path, transfer.export_commit(path, commit=basis))
    transfer.import_commit(predicted_path, transfer.export_commit(path, commit=proof))
    predicted = invoke(predicted_path)
    baseline = typed_oracle(path, (basis, proof))
    all_bytes = typed_oracle(predicted_path, (predicted.commit, proof))
    new = {key: raw for key, raw in all_bytes.items() if key not in baseline}
    # Independent ACTUAL native absence of EVERY new key, not export-only inference.
    with d.Repository(path) as repository, repository.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    assert {kind for kind, _ in new} == {"datum", "node", "dag", "tree", "commit"}
    assert sum(kind == "dag" for kind, _ in new) == 1
    return predicted, baseline, all_bytes, new


@pytest.mark.parametrize("mode", ["definition", "decision"])
@pytest.mark.parametrize(
    "fault",
    ["different-ref", "raw-ref", "allocation", "response", "commit", "map-full"],
)
def test_every_new_actual_A_row_readback_before_late_native_whole_batch_abort(
    double, core, monkeypatch, mode, fault
):
    path, old_base, _ = double[0]
    basis, invoke, proof = operation(double, mode)
    if fault == "different-ref":
        with d.Repository(path) as repository, repository.write() as tx:
            tx.create_ref("authored", old_base)
    elif fault == "raw-ref":
        run_driver("raw-write", str(path), "refs/heads/authored", data=b"raw-invalid")
    predicted, baseline, all_bytes, new = prediction(path, basis, invoke, proof)
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
        constructor = app.IntentDefinition if mode == "definition" else app.Decision

        def allocation(*a):
            if mode == "definition" and a[0] == basis:
                return constructor(*a)
            raise MemoryError("private precommit owning response allocation")

        monkeypatch.setattr(
            app, "IntentDefinition" if mode == "definition" else "Decision", allocation
        )
    try:
        with track_typed_puts(path, baseline) as puts:
            with pytest.raises((d.DmlError, MemoryError)):
                invoke(map_size=1048576 if fault == "map-full" else 0)
    finally:
        core.native_fault(0, 0, 0)
    assert puts == new  # EXACT genuinely-new actual-A bytes BEFORE each late failure.
    if fault == "map-full":
        with d.Repository(path):
            pass  # Comparable unchanged default map extent; no write, no shrink.
    assert_file_unchanged(path / "data.mdb", before)
    _fresh_absence(path, baseline, new)
    with d.Repository(path) as repository, repository.read() as tx:
        assert tx.get_ref("main") == old_base
        with pytest.raises(d.NotFoundError):
            tx.get_ref("policy-submission")
        if mode == "decision":
            assert tx.get_ref("intent-default") == basis


@pytest.mark.parametrize("mode", ["definition", "decision"])
@pytest.mark.parametrize("boundary", ["pre", "post"])
def test_actual_authoring_only_loss_predicts_every_byte_parent_name_ref(
    double, mode, boundary
):
    path = double[0][0]
    basis, invoke, proof = operation(double, mode)
    predicted, baseline, all_bytes, new = prediction(path, basis, invoke, proof)
    before = (path / "data.mdb").read_bytes()
    marker = path.parent / "store-barrier"
    with (path.parent / "authoring.stderr").open("wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/intent_interruption_parent.py"),
                str(ROOT / "examples/intent_defaults.py"),
                mode,
                str(path),
                str(basis),
                str(marker),
                boundary,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            wait_file(marker, process, timeout=15)
            process.terminate()  # ONLY authoring process, NO live computational child.
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    with d.Repository(path) as repository, repository.read() as tx:
        assert all(tx.get_record(*key) == raw for key, raw in baseline.items())
        with pytest.raises(d.NotFoundError):
            tx.get_ref("policy-submission")  # D survives alone; post barrier before Q.
        if boundary == "pre":
            with pytest.raises(d.NotFoundError):
                tx.get_ref("authored")
        else:
            assert tx.get_ref("authored") == predicted.commit
            assert tx.get_commit(predicted.commit).parents == (basis,)
            entries = tree(tx, basis)
            entries[predicted.name] = predicted.dag
            assert tree(tx, predicted.commit) == entries
    if boundary == "pre":
        assert_file_unchanged(path / "data.mdb", before)
        _fresh_absence(path, baseline, new)
    else:
        assert typed_oracle(path, (predicted.commit, proof)) == all_bytes
