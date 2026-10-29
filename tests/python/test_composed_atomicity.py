"""Meaningfully new actual-A authoring puts before late failure; no Docker."""

import errno
from pathlib import Path

import daggerml as d
import pytest

from test_binding_failures import core
from test_caller_requests import track_typed_puts, assert_file_unchanged
from test_composed_execution import producer, basis, summary, execute, example
from test_exchange import exchange_runtime, typed_oracle
from test_exchange_progress import _fresh_absence
from test_records_hypothesis import run_driver


def authoring(producer, operation):
    path, base, first = producer
    if operation == "basis":
        return lambda **k: basis(producer, **k), "double-basis", (first[2].commit,)
    authored = basis(producer)
    second = execute(path, authored.commit, "double", "double-binding", "double-inputs")
    return (
        lambda **k: summary(producer, second, **k),
        "experiment-result",
        (second[2].commit,),
    )


@pytest.mark.parametrize("operation", ["basis", "summary"])
@pytest.mark.parametrize(
    "fault", ["different-ref", "raw-ref", "commit", "map-full", "response"]
)
def test_late_authoring_new_native_puts_whole_batch_rollback(
    producer, operation, fault, core, monkeypatch
):
    path, base, first = producer
    call, ref, roots = authoring(producer, operation)
    if fault == "different-ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref(ref, base)
    elif fault == "raw-ref":
        run_driver("raw-write", str(path), "refs/heads/" + ref, data=b"bad")
    baseline = typed_oracle(path, roots)
    before = (path / "data.mdb").read_bytes()
    original = d.Transaction.create_ref

    def late(self, name, target):
        if name == ref:
            if fault == "map-full":
                self.put_datum(b"x" * (2 * 1024 * 1024))
            elif fault == "commit":
                core.native_fault(15, 1, errno.EIO)
        return original(self, name, target)

    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        monkeypatch.setattr(
            example,
            "Authored",
            lambda *a: (_ for _ in ()).throw(
                MemoryError("private precommit response allocation")
            ),
        )
    try:
        with track_typed_puts(path, baseline) as new:
            with pytest.raises((d.DmlError, MemoryError)):
                call(map_size=1048576 if fault == "map-full" else 0)
    finally:
        core.native_fault(0, 0, 0)
    assert any(k == "dag" for k, oid in new) and any(k == "commit" for k, oid in new)
    assert len(new) >= 3, "successful genuinely NEW actual A rows/readback required"
    if fault == "map-full":
        with d.Repository(path):
            pass  # Comparable default physical map on Windows.
    assert_file_unchanged(path / "data.mdb", before)
    _fresh_absence(path, baseline, new)


@pytest.mark.parametrize("operation", ["basis", "summary"])
@pytest.mark.parametrize("boundary", ["pre", "post"])
def test_authoring_only_actual_store_commit_interruption(producer, operation, boundary):
    import subprocess
    import sys
    from daggerml import exchange as ex, transfer
    from test_composed_execution import REMOTE
    from test_exchange import ROOT
    from test_exchange_launch import wait_file

    path, base, first = producer
    second = None
    if operation == "summary":
        authored = basis(producer)
        second = execute(
            path, authored.commit, "double", "double-binding", "double-inputs"
        )
    first_saved = path.parent / "first-expected"
    ex.save_exchange_handle(first_saved, ex.ExchangeHandle(first[4], first[1]))
    second_saved = path.parent / "second-expected"
    if second:
        ex.save_exchange_handle(second_saved, ex.ExchangeHandle(second[4], second[1]))
    selected_root = first[2].commit if operation == "basis" else second[2].commit
    baseline = typed_oracle(path, (selected_root,))
    prediction = path.parent / "prediction-A"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(
        prediction, transfer.export_commit(path, commit=selected_root)
    )
    if operation == "basis":
        predicted = example.consumer_basis(
            prediction,
            producer_packet=first[0],
            producer_expected=first[1],
            remote=REMOTE,
            gate="gates/double",
        )
    else:
        predicted = example.experiment_summary(
            prediction,
            producer_packet=first[0],
            producer_expected=first[1],
            consumer_packet=second[0],
            consumer_expected=second[1],
        )
    expected_bytes = typed_oracle(prediction, (predicted.commit,))
    genuinely_new = {
        key: raw for key, raw in expected_bytes.items() if key not in baseline
    }
    assert len(genuinely_new) >= 3
    marker = path.parent / "authoring-barrier"
    before = (path / "data.mdb").read_bytes()
    with open(path.parent / "authoring-stderr", "wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/composed_interruption_parent.py"),
                str(ROOT / "examples/composed_execution.py"),
                str(path),
                str(first[0]),
                str(first_saved),
                str(second[0]) if second else "unused",
                str(second_saved),
                str(marker),
                boundary,
                operation,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            wait_file(marker, process, timeout=10)
            process.terminate()
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    ref = "double-basis" if operation == "basis" else "experiment-result"
    if boundary == "pre":
        assert_file_unchanged(path / "data.mdb", before)
        _fresh_absence(path, baseline, genuinely_new)
        with d.Repository(path) as repo, repo.read() as tx:
            with pytest.raises(d.NotFoundError):
                tx.get_ref(ref)
    else:
        # Fresh complete native closure, not only a ref/status assertion.
        with d.Repository(path) as repo, repo.read() as tx:
            target = tx.get_ref(ref)
            expected_parent = (
                first[2].commit if operation == "basis" else second[2].commit
            )
            assert tx.get_commit(target).parents == (expected_parent,)
            entries = tx.get_tree(tx.get_commit(target).tree)
            assert (
                "double-inputs" if operation == "basis" else "experiment"
            ) in entries
        assert target == predicted.commit
        assert typed_oracle(path, (target,)) == expected_bytes
        with pytest.raises(d.InvalidStateError):
            basis(producer) if operation == "basis" else summary(producer, second)
