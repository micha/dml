"""New actual W native writes/rollback and separate retained-Q uncertainty."""

import errno
from pathlib import Path
import subprocess
import sys
import uuid

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

from test_binding_failures import core
from test_caller_requests import (
    assert_file_unchanged,
    assert_recorded,
    track_typed_puts,
)
from test_composed_execution import producer
from test_exchange import ROOT, exchange_runtime, tree, typed_oracle
from test_exchange_launch import wait_file
from test_exchange_progress import _fresh_absence
from test_explicit_reuse import app, double, reuse
from test_records_hypothesis import run_driver


@pytest.mark.parametrize(
    "fault",
    ["different-ref", "raw-ref", "commit", "allocation", "map-full", "response"],
)
def test_genuinely_new_w_puts_readback_rollback_but_committed_q_retained(
    double, core, monkeypatch, fault
):
    path, base, _ = double[0]
    if fault == "different-ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("reused-double", base)
    elif fault == "raw-ref":
        run_driver("raw-write", str(path), "refs/heads/reused-double", data=b"bad")
    old = typed_oracle(path, (double[2][2].commit, base))
    snapshot = {}
    recording = ex.record_exchange_request

    def actual_record(*a, **k):
        got = recording(*a, **k)
        # Closed actual Q publication is the boundary oracle, not a fabricated Q.
        snapshot["recorded"] = got
        with d.Repository(path):
            pass  # Comparable default physical layout before W pressure on Windows.
        snapshot["baseline"] = typed_oracle(path, (got.commit, base))
        snapshot["bytes"] = (path / "data.mdb").read_bytes()
        return got

    monkeypatch.setattr(ex, "record_exchange_request", actual_record)
    creating = d.Transaction.create_ref

    def late(self, name, target):
        if name == "reused-double":
            if fault == "map-full":
                self.put_datum(b"x" * (2 * 1024 * 1024))
            elif fault == "commit":
                core.native_fault(15, 1, errno.EIO)
            elif fault == "allocation":
                core.native_fault(1, 1, 0)
        return creating(self, name, target)

    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        monkeypatch.setattr(
            app,
            "Reused",
            lambda *a: (_ for _ in ()).throw(
                MemoryError("private response allocation")
            ),
        )
    try:
        with track_typed_puts(path, old) as successful:
            with pytest.raises((d.DmlError, MemoryError)):
                reuse(double, map_size=1048576 if fault == "map-full" else 0)
    finally:
        core.native_fault(0, 0, 0)
    new_w = {
        key: raw for key, raw in successful.items() if key not in snapshot["baseline"]
    }
    assert len(new_w) >= 3
    assert {"dag", "tree", "commit"} <= {key[0] for key in new_w}
    if fault == "map-full":
        with d.Repository(path):
            pass
    assert_file_unchanged(path / "data.mdb", snapshot["bytes"])
    _fresh_absence(path, snapshot["baseline"], new_w)
    assert_recorded(path, snapshot["recorded"])
    # A failed W is not permission to create another Q or hidden fallback.
    with pytest.raises(ex.ExchangeError, match="submission ref"):
        reuse(double)


@pytest.mark.parametrize("boundary", ["pre", "post"])
def test_actual_w_store_commit_loss_predicted_every_byte_parent_ref_q_survives(
    double, monkeypatch, boundary
):
    path = double[0][0]
    second = double[2]
    payload = "c" * 32
    expected_file = path.parent / "historical-expected"
    ex.save_exchange_handle(expected_file, ex.ExchangeHandle(second[4], second[1]))
    original = typed_oracle(path, (second[2].commit,))
    prediction = path.parent / "prediction"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(
        prediction, transfer.export_commit(path, commit=second[2].commit)
    )
    with monkeypatch.context() as guard:
        guard.setattr(ex.uuid, "uuid4", lambda: uuid.UUID(hex=payload))
        predicted = app.reuse_attempt(
            prediction,
            commit=second[2].commit,
            binding_name="double-binding",
            inputs_name="double-inputs",
            intent_uri="urn:example:double",
            historical_packet=second[0],
            historical_expected=second[1],
            submission_ref="reuse-submission",
            ref="reused-double",
        )
    q_bytes = typed_oracle(prediction, (predicted.recorded.commit,))
    all_bytes = typed_oracle(prediction, (predicted.commit,))
    new_w = {key: raw for key, raw in all_bytes.items() if key not in q_bytes}
    assert {"dag", "tree", "commit"} <= {key[0] for key in new_w}
    marker = path.parent / "W-barrier"
    errors_path = path.parent / "reuse-errors"
    with errors_path.open("wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/reuse_interruption_parent.py"),
                str(ROOT / "examples/explicit_reuse.py"),
                str(path),
                str(second[2].commit),
                str(second[0]),
                str(expected_file),
                payload,
                str(marker),
                boundary,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            wait_file(marker, process, timeout=10)
            process.terminate()  # Authoring-only process; no computational child.
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    assert (
        d.ObjectId.from_hex(Path(str(marker) + ".q").read_text())
        == predicted.recorded.commit
    )
    assert_recorded(path, predicted.recorded)
    with d.Repository(path) as repo, repo.read() as tx:
        assert all(tx.get_record(*key) == raw for key, raw in original.items())
        if boundary == "pre":
            with pytest.raises(d.NotFoundError):
                tx.get_ref("reused-double")
        else:
            assert tx.get_ref("reused-double") == predicted.commit
            assert tx.get_commit(predicted.commit).parents == (
                predicted.recorded.commit,
            )
            expected_tree = tree(tx, predicted.recorded.commit)
            expected_tree["reuse-" + predicted.recorded.request_id] = predicted.dag
            assert tree(tx, predicted.commit) == expected_tree
    if boundary == "pre":
        assert_file_unchanged(
            path / "data.mdb", Path(str(marker) + ".q-bytes").read_bytes()
        )
        _fresh_absence(path, q_bytes, new_w)
    else:
        assert typed_oracle(path, (predicted.commit,)) == all_bytes
    with pytest.raises(ex.ExchangeError, match="submission ref"):
        reuse(double)
