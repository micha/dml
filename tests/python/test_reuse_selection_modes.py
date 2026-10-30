"""Finite offline modes, full matching, capsule/scratch/response boundaries."""

from dataclasses import replace
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import uuid

import daggerml as d
from daggerml import exchange as ex, local, transfer
from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import (
    assert_file_unchanged,
    assert_recorded,
    track_typed_puts,
)
from test_composed_execution import producer, execute
from test_exchange import ROOT, exchange_runtime, literal, scalar, tree, typed_oracle
from test_explicit_reuse import double
from test_reuse_selection import app, expected_file, select
from test_reuse_selection_records import selection, reuse, adopt


@pytest.mark.parametrize(
    "dimension",
    [
        "intent",
        "source",
        "interpreter",
        "timeout",
        "factor",
        "factor-type",
        "endpoint",
        "bucket",
        "gate",
        "exit-code",
        "artifacts",
        "producer",
    ],
)
def test_full_valid_dimensions_including_equal42_producer_before_selection_Q_adoption(
    double, expected_file, selection, dimension
):
    path, base, first = double[0]
    alternate = execute(path, base, "another-add") if dimension == "producer" else None
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, selection.commit)
        if dimension in {"source", "interpreter", "timeout"}:
            binding = double[2][1].binding
            entries["double-binding"] = local.put_local_binding(
                tx,
                source=scalar(tx, binding, "source")
                + (b"\n# different source\n" if dimension == "source" else b""),
                interpreter=scalar(tx, binding, "interpreter")
                + (".different" if dimension == "interpreter" else ""),
                timeout_ms=scalar(tx, binding, "timeout-ms")
                + (1 if dimension == "timeout" else 0),
            )
        elif dimension != "intent":
            fields = dict(tx.get_dag(double[2][1].inputs).bindings)
            if dimension == "producer":
                assert alternate[2].result == first[2].result
                fields["producer"] = tx.put_subdag(
                    alternate[2].completion.final_attempt
                )
            else:
                key, value = {
                    "factor": ("factor", 3),
                    "factor-type": ("factor", True),
                    "endpoint": ("endpoint", "http://elsewhere:4566"),
                    "bucket": ("bucket", "different-bucket"),
                    "gate": ("gate", "another/key"),
                    "exit-code": ("exit-code", 23),
                    "artifacts": ("artifacts", b"changed"),
                }[dimension]
                fields[key] = literal(tx, value)
            entries["double-inputs"] = tx.put_dag(root=fields["value"], bindings=fields)
        changed = tx.put_commit(tx.put_tree(entries), parents=(selection.commit,))
    intent = "urn:example:other" if dimension == "intent" else "urn:example:double"
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="full inputs differ"):
        select(
            double,
            expected_file,
            commit=changed,
            slot="other-choice",
            ref="mismatch",
            intent_uri=intent,
        )
    with pytest.raises(ValueError, match="full inputs differ"):
        reuse(path, changed, intent_uri=intent)
    with pytest.raises(ValueError, match="full inputs differ"):
        adopt(path, changed, double[2], expected_file=expected_file, intent_uri=intent)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "fault",
    ["capture-cleanup", "validation-cleanup", "projection-cleanup", "projection-write"],
)
def test_owned_scratch_faults_before_authoring_and_separate_late_Q_W_cleanup(
    double, expected_file, selection, monkeypatch, fault
):
    path = double[0][0]
    original = shutil.rmtree
    writes = Path.write_bytes
    owned = []

    def denied(path, *a, **k):
        name = Path(path).name
        prefix = {
            "capture-cleanup": "dml-selection-capture-",
            "validation-cleanup": "dml-observation-validation-",
            "projection-cleanup": "dml-selection-projection-",
        }.get(fault)
        if prefix and name.startswith(prefix):
            owned.append(Path(path))
            raise PermissionError("private owned scratch disposal failure")
        return original(path, *a, **k)

    def denied_write(self, data):
        if self.parent.name.startswith("dml-selection-projection-"):
            raise PermissionError("private projection write failure")
        return writes(self, data)

    before = (path / "data.mdb").read_bytes()
    try:
        with monkeypatch.context() as guard:
            guard.setattr(shutil, "rmtree", denied)
            if fault == "projection-write":
                guard.setattr(Path, "write_bytes", denied_write)
            with pytest.raises(PermissionError):
                if fault == "capture-cleanup":
                    select(
                        double,
                        expected_file,
                        slot="another-choice",
                        ref="failed-choice",
                    )
                else:
                    reuse(path, selection.commit)
        if fault == "projection-cleanup":
            with d.Repository(path) as repository, repository.read() as tx:
                qcommit = tx.get_ref("reuse-submission")
                result = tx.get_ref("reused-double")
                assert tx.get_commit(qcommit).parents == (selection.commit,)
                assert tx.get_commit(result).parents == (qcommit,)
                assert "selected-double" in tree(tx, result)
                assert len([n for n in tree(tx, result) if n.startswith("reuse-")]) == 1
            with pytest.raises(ex.ExchangeError, match="submission ref"):
                reuse(path, selection.commit)
        else:
            assert_file_unchanged(path / "data.mdb", before)
    finally:
        for directory in owned:
            original(directory)


def test_inspection_projection_cleanup_failure_blocks_adoption_before_new_A_batch(
    double, selection, monkeypatch
):
    path = double[0][0]
    fresh = execute(
        path, selection.commit, "fresh-double", "double-binding", "double-inputs"
    )
    original = shutil.rmtree
    owned = []

    def denied(path, *a, **k):
        if Path(path).name.startswith("dml-selection-projection-"):
            owned.append(Path(path))
            raise PermissionError("private old proof cleanup failure")
        return original(path, *a, **k)

    before = (path / "data.mdb").read_bytes()
    try:
        with monkeypatch.context() as guard:
            guard.setattr(shutil, "rmtree", denied)
            with pytest.raises(PermissionError):
                adopt(path, fresh[2].commit, fresh)
        assert_file_unchanged(path / "data.mdb", before)
    finally:
        for directory in owned:
            original(directory)


@pytest.mark.parametrize("file", ["expected", "job.json", "observation.json"])
@pytest.mark.parametrize(
    "data",
    [b"{} {}", b'{"x":1,"x":2}', b"\xff", b"\xef\xbb\xbf{}", b"{}", b'{"x":NaN}'],
    ids=["trailing", "duplicate", "utf8", "bom", "fields", "constant"],
)
def test_raw_public_header_framing_rejection_before_select(
    double, expected_file, file, data
):
    source = expected_file if file == "expected" else double[2][0] / file
    source.write_bytes(data)
    before = (double[0][0] / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        select(double, expected_file)
    assert_file_unchanged(double[0][0] / "data.mdb", before)


def test_missing_unknown_forged_and_independent_expected_before_A(
    double, expected_file
):
    path = double[0][0]
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(FileNotFoundError):
        select(double, expected_file, packet=path.parent / "unknown")
    with pytest.raises(TypeError):
        select(double, expected_file, packet=replace(double[2][2], lifecycle="done"))
    alternate = execute(
        path, double[1].commit, "another-double", "double-binding", "double-inputs"
    )
    after_setup = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        select(double, expected_file, packet=alternate[0], commit=alternate[2].commit)
    assert_file_unchanged(path / "data.mdb", after_setup)


def test_original_transfer_record_and_bundle_bounds_without_profile_growth(
    double, expected_file, selection
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, selection.commit)
        entries["large"] = tx.put_dag(root=literal(tx, b"x" * (4 * 1024 * 1024 + 1)))
        oversized = tx.put_commit(tx.put_tree(entries), parents=(selection.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(transfer.TransferError, match="packed record"):
        reuse(path, oversized)
    assert_file_unchanged(path / "data.mdb", before)
    with (double[2][0] / "snapshot.bundle").open("wb") as stream:
        stream.write(b"x" * (transfer.MAX_BUNDLE_BYTES + 1))
    with pytest.raises(ValueError, match="owning profile"):
        select(double, expected_file)
    assert_file_unchanged(path / "data.mdb", before)


def test_fresh_Q_mode_not_independent_caller_expected(double):
    path = double[0][0]
    workspace = path.parent / "fresh-Q-mode"
    expected = ex.prepare_exchange(
        path,
        commit=double[1].commit,
        binding_name="double-binding",
        inputs_name="double-inputs",
        intent_uri="urn:example:double",
        worker_ref="work",
        workspace=workspace,
    )
    ex.execute_exchange(workspace)
    packet = path.parent / "fresh-Q-packet"
    ex.observe_exchange(ex.ExchangeHandle(workspace, expected), packet=packet)
    saved = path.parent / "expected-fresh-Q"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(workspace, expected))
    with pytest.raises(ValueError, match="independent caller Cq/Q"):
        select(double, saved, packet=packet)


def test_finite_all_modes_and_fresh_offline_entry(
    double, expected_file, capsys, monkeypatch
):
    path = double[0][0]
    common = [str(path), str(double[2][2].commit), "selected-double"]
    dimensions = ["double-binding", "double-inputs", "urn:example:double"]
    assert (
        app.main(
            [
                "select",
                *common,
                *dimensions,
                str(expected_file),
                str(double[2][0]),
                "selection-old",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    selected = d.ObjectId.from_hex(report["commit"])
    assert app.main(["inspect", str(path), str(selected), "selected-double"]) == 0
    assert json.loads(capsys.readouterr().out)["attempt"] == str(
        double[2][2].completion.final_attempt
    )
    assert (
        app.main(
            [
                "reuse-selected",
                str(path),
                str(selected),
                "selected-double",
                *dimensions,
                "reuse-submission",
                "reused-double",
            ]
        )
        == 0
    )
    reused = json.loads(capsys.readouterr().out)
    fresh = execute(
        path,
        d.ObjectId.from_hex(reused["commit"]),
        "fresh-double",
        "double-binding",
        "double-inputs",
    )
    saved = path.parent / "fresh-expected"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(fresh[4], fresh[1]))
    assert (
        app.main(
            [
                "adopt",
                str(path),
                str(fresh[2].commit),
                "selected-double",
                *dimensions,
                str(saved),
                str(fresh[0]),
                "adopt-fresh",
            ]
        )
        == 0
    )
    adopted = json.loads(capsys.readouterr().out)
    for source in (
        expected_file,
        double[2][0],
        double[2][4],
        saved,
        fresh[0],
        fresh[4],
    ):
        source.rename(source.with_name(source.name + ".unavailable"))
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples/reuse_selection.py"),
            "inspect",
            str(path),
            adopted["commit"],
            "selected-double",
        ],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert json.loads(result.stdout)["attempt"] == str(
        fresh[2].completion.final_attempt
    )
    monkeypatch.setattr(sys, "argv", ["reuse_selection.py"])
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(ROOT / "examples/reuse_selection.py"), run_name="__main__")
    assert error.value.code == 2


@pytest.mark.parametrize("name", ["", "bad/name", 1])
def test_explicit_name_profile_rejection(double, expected_file, name):
    with pytest.raises(ValueError, match="native profile"):
        select(double, expected_file, slot=name)


@settings(
    max_examples=4,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(st.text(alphabet="abcXYZ012", min_size=1, max_size=12))
def test_generated_containing_annotation_pinned_old_selection_not_global_latest(
    double, selection, annotation
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, selection.commit)
        entries["annotation"] = tx.put_dag(root=literal(tx, annotation))
        containing = tx.put_commit(
            tx.put_tree(entries), parents=(double[0][1], selection.commit)
        )
    label = uuid.uuid4().hex
    got = reuse(path, containing, submission_ref="s-" + label, ref="r-" + label)
    assert got.attempt == selection.attempt and got.recorded.base == containing
