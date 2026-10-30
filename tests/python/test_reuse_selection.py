"""First small ordinary S/V and durable PUBLIC reinspection draft; no Docker."""

import importlib.util
from pathlib import Path
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged
from test_composed_execution import producer, execute
from test_exchange import ROOT, exchange_runtime, nested, scalar, tree, typed_oracle
from test_explicit_reuse import double

spec = importlib.util.spec_from_file_location(
    "selection_example", ROOT / "examples/reuse_selection.py"
)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
paths = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    spec.loader.exec_module(app)
finally:
    sys.path[:] = paths


@pytest.fixture
def expected_file(double):
    second = double[2]
    path = double[0][0].parent / "independent-expected.json"
    ex.save_exchange_handle(path, ex.ExchangeHandle(second[4], second[1]))
    return path


def select(double, expected_file, **changes):
    arguments = dict(
        commit=double[2][2].commit,
        slot="selected-double",
        binding_name="double-binding",
        inputs_name="double-inputs",
        intent_uri="urn:example:double",
        packet=double[2][0],
        expected_file=expected_file,
        ref="selection-old",
    )
    arguments.update(changes)
    return app.select(double[0][0], **arguments)


def test_select_exact_ordinary_shape_preserved_bytes_no_q_t_job(
    double, expected_file, monkeypatch
):
    path, base, _ = double[0]
    old = typed_oracle(path, (double[2][2].commit, base))
    with monkeypatch.context() as guard:
        guard.setattr(
            subprocess, "Popen", lambda *a, **k: pytest.fail("selection never executes")
        )
        got = select(double, expected_file)
    with d.Repository(path) as repository, repository.read() as tx:
        assert tx.get_ref("main") == base
        assert tx.get_ref("selection-old") == got.commit
        assert tx.get_commit(got.commit).parents == (double[2][2].commit,)
        entries = tree(tx, double[2][2].commit)
        entries["selected-double"] = got.dag
        assert tree(tx, got.commit) == entries
        assert set(tx.get_dag(got.dag).bindings) == {
            "role",
            "intent",
            "binding",
            "inputs",
            "request",
            "attempt",
            "result",
            "completion",
            "validation",
        }
        assert tx.get_dag(got.dag).root == tx.lookup_node(got.dag, "result")
        assert scalar(tx, got.dag, "role") == "example-reuse-selection-v1"
        assert scalar(tx, got.dag, "completion") == double[2][2].commit.bytes
        assert nested(tx, got.dag, "request") == double[2][2].request
        assert nested(tx, got.dag, "attempt") == double[2][2].completion.final_attempt
        assert nested(tx, got.dag, "result") == double[2][2].result
        assert nested(tx, got.dag, "validation") == got.validation
        assert tx.get_dag(got.validation).root == tx.lookup_node(
            got.validation, "expected"
        )
        assert scalar(tx, got.validation, "expected") == expected_file.read_bytes()
        assert (
            scalar(tx, got.validation, "job")
            == (double[2][0] / "job.json").read_bytes()
        )
        assert (
            scalar(tx, got.validation, "observation")
            == (double[2][0] / "observation.json").read_bytes()
        )
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        select(double, expected_file, commit=got.commit, ref="another-selection")
    assert_file_unchanged(path / "data.mdb", before)


def test_durable_inspect_without_original_packet_expected_input_B(
    double, expected_file, monkeypatch
):
    path = double[0][0]
    got = select(double, expected_file)
    for source in (double[2][0], expected_file, double[2][4]):
        source.rename(source.with_name(source.name + ".unavailable"))
    before = (path / "data.mdb").read_bytes()
    with monkeypatch.context() as guard:
        guard.setattr(
            ex,
            "observe_exchange",
            lambda *a, **k: pytest.fail("historical handle inert"),
        )
        guard.setattr(
            ex, "start_exchange", lambda *a, **k: pytest.fail("historical handle inert")
        )
        assert app.inspect(path, commit=got.commit, slot=got.slot) == got
        assert app.inspect(path, commit=got.commit, slot=got.slot) == got
    copied = path.parent / "transferred"
    with d.Repository(copied, create=True):
        pass
    transfer.import_commit(copied, transfer.export_commit(path, commit=got.commit))
    assert app.inspect(copied, commit=got.commit, slot=got.slot) == got
    assert typed_oracle(copied, (got.commit,)) == typed_oracle(path, (got.commit,))
    assert_file_unchanged(path / "data.mdb", before)


def test_same_owned_headers_persist_not_mutable_original_reread(
    double, expected_file, monkeypatch
):
    original = app._materialize
    captured = expected_file.read_bytes()
    old_job = (double[2][0] / "job.json").read_bytes()
    old_observation = (double[2][0] / "observation.json").read_bytes()

    def materialize(*a):
        got = original(*a)
        expected_file.write_bytes(b"mutated after capture")
        (double[2][0] / "job.json").write_bytes(b"mutated after capture")
        (double[2][0] / "observation.json").write_bytes(b"mutated after capture")
        return got

    with monkeypatch.context() as guard:
        guard.setattr(app, "_materialize", materialize)
        got = select(double, expected_file)
    with d.Repository(double[0][0]) as repository, repository.read() as tx:
        assert scalar(tx, got.validation, "expected") == captured
        assert scalar(tx, got.validation, "job") == old_job
        assert scalar(tx, got.validation, "observation") == old_observation
    assert app.inspect(double[0][0], commit=got.commit, slot=got.slot) == got


@pytest.mark.parametrize("file", ["expected", "job.json", "observation.json"])
def test_descriptor_8192_exact_bounded_read_and_plus_one_rejection(
    double, expected_file, file
):
    source = expected_file if file == "expected" else double[2][0] / file
    data = source.read_bytes()
    source.write_bytes(data + b" " * (8192 - len(data)))
    assert len(app._bounded(source, 8192)) == 8192
    got = select(double, expected_file)
    assert app.inspect(double[0][0], commit=got.commit, slot=got.slot) == got
    source.write_bytes(source.read_bytes() + b" ")
    before = (double[0][0] / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="owning profile"):
        select(double, expected_file, ref="oversized")
    assert_file_unchanged(double[0][0] / "data.mdb", before)


def test_F_literal_metadata_is_not_parent_retention(double, expected_file):
    path, base, _ = double[0]
    with d.Repository(path) as repository, repository.write() as tx:
        disconnected = tx.put_commit(tx.get_commit(double[2][2].commit).tree)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="ALL-parent"):
        select(double, expected_file, commit=disconnected)
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repository, repository.write() as tx:
        nonfirst = tx.put_commit(
            tx.get_commit(double[2][2].commit).tree, parents=(base, double[2][2].commit)
        )
    got = select(double, expected_file, commit=nonfirst)
    assert app.inspect(path, commit=got.commit, slot=got.slot) == got
