"""Finite offline entry/default-safe authority/owned-response edge coverage."""

from dataclasses import replace
import json
from pathlib import Path
import runpy
import subprocess
import sys
import uuid

import daggerml as d
from daggerml import exchange as ex
from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged, assert_recorded
from test_composed_execution import producer
from test_exchange import ROOT, exchange_runtime, literal, tree, typed_oracle
from test_explicit_reuse import app, double, reuse


def test_finite_fresh_offline_entry_and_reinspection_creates_nothing(
    double, monkeypatch, capsys
):
    path = double[0][0]
    second = double[2]
    saved = path.parent / "independent-expected"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(second[4], second[1]))
    arguments = [
        str(path),
        str(second[2].commit),
        "double-binding",
        "double-inputs",
        "urn:example:double",
        str(saved),
        str(second[0]),
        "reuse-submission",
        "reused-double",
    ]
    # Input/B unavailable; historical interpreter/source are inert data.
    second[4].rename(second[4].with_name("second-input-and-B-offline"))
    assert app.main(arguments) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "reuse" and report["attempt"] == str(
        second[2].completion.final_attempt
    )
    before = (path / "data.mdb").read_bytes()
    for _ in range(2):
        assert (
            ex.read_observation(second[0], expected=second[1]).result
            == second[2].result
        )
        assert (
            ex.receive_observation(
                path, packet=second[0], expected=second[1], ref="received-double"
            ).result
            == second[2].result
        )
    assert_file_unchanged(path / "data.mdb", before)
    # Fresh process uses only staged public runtime; no Floci/HTTP/Docker import.
    code = (
        "import runpy,sys;sys.argv="
        + repr(
            [
                str(ROOT / "examples/explicit_reuse.py"),
                *arguments[:-2],
                "another-submission",
                "another-reuse",
            ]
        )
        + ";runpy.run_path(sys.argv[0],run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, timeout=15
    )
    assert result.returncode == 0, result.stderr.decode()
    fresh = json.loads(result.stdout)
    assert (
        fresh["attempt"] == report["attempt"] and fresh["request"] != report["request"]
    )


def test_offline_module_has_no_transport_runtime_import(double):
    code = "import importlib.util,sys;s=importlib.util.spec_from_file_location('offline_reuse',sys.argv[1]);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);assert not {'http.client','daggerml.floci','daggerml.floci_http','docker'} & set(sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", code, str(ROOT / "examples/explicit_reuse.py")],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_module_entry_requires_explicit_finite_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["explicit_reuse.py"])
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(ROOT / "examples/explicit_reuse.py"), run_name="__main__")
    assert error.value.code == 2


def test_fresh_q_mode_valid_packet_not_independent_caller_q(double):
    path = double[0][0]
    workspace = path.parent / "fresh-q-mode"
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
    packet = path.parent / "fresh-q-packet"
    ex.observe_exchange(ex.ExchangeHandle(workspace, expected), packet=packet)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="pinned historical Cq/Q"):
        reuse(double, historical_packet=packet, historical_expected=expected)
    assert_file_unchanged(path / "data.mdb", before)


def test_actual_request_response_selection_recheck_failure_retains_q_not_w(
    double, monkeypatch
):
    path = double[0][0]
    recording = ex.record_exchange_request
    actual = []

    def changed(*a, **k):
        got = recording(*a, **k)
        actual.append(got)
        return replace(got, intent_uri="urn:private:changed-response")

    monkeypatch.setattr(ex, "record_exchange_request", changed)
    with pytest.raises(ValueError, match="actual newly recorded"):
        reuse(double)
    assert_recorded(path, actual[0])
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("reused-double")


def test_reuse_name_collision_after_actual_q_retains_pending_submission(
    double, monkeypatch
):
    path = double[0][0]
    payload = "b" * 32
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, double[2][2].commit)
        entries["reuse-q-" + payload] = double[2][2].result
        base = tx.put_commit(tx.put_tree(entries), parents=(double[2][2].commit,))
    monkeypatch.setattr(ex.uuid, "uuid4", lambda: uuid.UUID(hex=payload))
    with pytest.raises(ValueError, match="reuse tree name"):
        reuse(double, commit=base)
    with d.Repository(path) as repo, repo.read() as tx:
        qcommit = tx.get_ref("reuse-submission")
        assert tx.get_commit(qcommit).parents == (base,)
        assert tx.get_ref("request-q-" + payload) == qcommit
        with pytest.raises(d.NotFoundError):
            tx.get_ref("reused-double")


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(st.text(alphabet="abcXYZ012", min_size=1, max_size=16))
def test_generated_containing_annotations_match_without_new_attempt(double, annotation):
    path = double[0][0]
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, double[2][2].commit)
        entries["annotation"] = tx.put_dag(root=literal(tx, annotation))
        base = tx.put_commit(tx.put_tree(entries), parents=(double[2][2].commit,))
    # Fresh explicit refs per generated request, never idempotent occurrence creation.
    label = uuid.uuid4().hex
    got = reuse(double, commit=base, submission_ref="s-" + label, ref="r-" + label)
    assert (
        got.recorded.binding == double[2][1].binding
        and got.recorded.inputs == double[2][1].inputs
    )
    assert got.attempt == double[2][2].completion.final_attempt
