"""New definition/default-update/D actual-A late rollback and safe response loss."""

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
from test_implementation_selection import app, menu, define, request
from test_records_hypothesis import run_driver


def operation(menu, mode):
    double, basis = menu
    path = double[0][0]
    if mode == "definition":

        def invoke(destination=path, **changes):
            return app.define(
                destination,
                commit=basis,
                intent_name="double-intent",
                intent_uri="urn:example:double",
                default="execute-by-default",
                implementations=(
                    ("double-a", "double-a-binding", "selected-double-a"),
                    ("double-b", "double-b-binding", "selected-double-b"),
                ),
                default_implementation="double-a",
                ref="authored",
                **changes,
            )

    else:
        definition = define(menu, default="execute-by-default")
        basis = definition.commit
        if mode == "update":

            def invoke(destination=path, **changes):
                return app.update_default(
                    destination,
                    commit=basis,
                    intent_name="double-intent",
                    default_implementation="double-b",
                    ref="authored",
                    **changes,
                )

        else:

            def invoke(destination=path, **changes):
                return request(
                    destination, basis, decision_ref="authored", **changes
                ).decision

    with d.Repository(path) as repository, repository.write() as tx:
        node = tx.put_literal(tx.put_datum("unrooted-old-proof"))
        proof = tx.put_commit(tx.put_tree({"old-proof": tx.put_dag(root=node)}))
    return basis, invoke, proof


def prediction(path, basis, invoke, proof):
    destination = path.parent / "prediction"
    with d.Repository(destination, create=True):
        pass
    transfer.import_commit(destination, transfer.export_commit(path, commit=basis))
    transfer.import_commit(destination, transfer.export_commit(path, commit=proof))
    predicted = invoke(destination)
    baseline = typed_oracle(path, (basis, proof))
    all_bytes = typed_oracle(destination, (predicted.commit, proof))
    new = {key: raw for key, raw in all_bytes.items() if key not in baseline}
    with d.Repository(path) as repository, repository.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    assert {"dag", "tree", "commit"} <= {kind for kind, _ in new}
    assert all(raw == all_bytes[key] for key, raw in baseline.items())
    return predicted, baseline, all_bytes, new


@pytest.mark.parametrize("mode", ["definition", "update", "decision"])
@pytest.mark.parametrize(
    "fault",
    ["different-ref", "raw-ref", "allocation", "response", "commit", "map-full"],
)
def test_new_actual_A_put_bytes_before_late_whole_batch_abort(
    menu, core, monkeypatch, mode, fault
):
    path = menu[0][0][0]
    basis, invoke, proof = operation(menu, mode)
    if fault == "different-ref":
        with d.Repository(path) as repository, repository.write() as tx:
            tx.create_ref("authored", menu[0][0][1])
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
        constructor = app.Decision if mode == "decision" else app.IntentDefinition

        def allocation(*a, **k):
            # Definition readers/provisional checks precede the actual response.
            if mode != "decision" and (not a or a[0] == basis):
                return constructor(*a, **k)
            raise MemoryError("private precommit owned response")

        if mode == "update":
            replacing = app.replace

            def response_replace(obj, **values):
                if isinstance(obj, constructor) and "commit" in values:
                    raise MemoryError("private update response")
                return replacing(obj, **values)

            monkeypatch.setattr(app, "replace", response_replace)
        else:
            monkeypatch.setattr(
                app,
                "Decision" if mode == "decision" else "IntentDefinition",
                allocation,
            )
    try:
        with track_typed_puts(path, baseline) as puts:
            with pytest.raises((d.DmlError, MemoryError)):
                invoke(map_size=1048576 if fault == "map-full" else 0)
    finally:
        core.native_fault(0, 0, 0)
    assert puts == new
    if fault == "map-full":
        with d.Repository(path):
            pass
    assert_file_unchanged(path / "data.mdb", before)
    _fresh_absence(path, baseline, new)
    with d.Repository(path) as repository, repository.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("policy-submission")


@pytest.mark.parametrize("mode", ["definition", "update", "decision"])
@pytest.mark.parametrize("boundary", ["pre", "post"])
def test_new_authoring_only_loss_exact_absent_rows_or_complete_batch(
    menu, mode, boundary
):
    path = menu[0][0][0]
    basis, invoke, proof = operation(menu, mode)
    predicted, baseline, all_bytes, new = prediction(path, basis, invoke, proof)
    before = (path / "data.mdb").read_bytes()
    marker = path.parent / "store-barrier"
    with (path.parent / "authoring.stderr").open("wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/implementation_interruption_parent.py"),
                str(ROOT / "examples/implementation_selection.py"),
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
            process.terminate()  # Authoring only; no computational child exists.
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    with d.Repository(path) as repository, repository.read() as tx:
        assert all(tx.get_record(*key) == raw for key, raw in baseline.items())
        with pytest.raises(d.NotFoundError):
            tx.get_ref("policy-submission")
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
