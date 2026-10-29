"""Meaningful malformed transport/packet/IO boundaries; substitutions are private."""

from dataclasses import replace
import json
from pathlib import Path
import runpy

from daggerml import (
    exchange as ex,
    floci as f,
    floci_http as h,
    floci_worker as worker,
    transfer,
)
import pytest

from test_caller_requests import caller_job, caller_completed
from test_exchange import exchange_runtime
from test_floci import JOB_ID, remote, service, stage
from test_floci_http import raw, wire


def test_argument_identity_and_staging_mismatch(caller_job, service, tmp_path):
    _, workspace, expected, *_ = caller_job
    with pytest.raises(TypeError):
        f.StagedFlociExchange(None, expected, tmp_path)
    with pytest.raises(TypeError):
        f.StagedFlociExchange(remote(), None, tmp_path)
    with pytest.raises(h.FlociError):
        f.StagedFlociExchange(remote(), replace(expected, request=None), tmp_path)
    with pytest.raises(TypeError):
        f.save_floci_job(tmp_path / "saved", None)
    with pytest.raises(TypeError):
        f.observe_floci_job(None, packet=tmp_path, timeout_ms=1)
    with pytest.raises(h.FlociError):
        f.stage_floci_exchange(
            remote(),
            workspace=workspace,
            expected=replace(expected, token="a" * 32),
            control=tmp_path / "control",
            timeout_ms=100,
        )
    assert not (tmp_path / "control").exists()
    staged = stage(caller_job, service)
    with pytest.raises(h.FlociError, match="local staged identity"):
        f.submit_floci_exchange(
            replace(staged, remote=remote(queue="different")), timeout_ms=100
        )
    assert not (staged.control / "dispatched").exists()


@pytest.mark.parametrize("mode", ["base", "request"])
def test_input_manifest_independent_selection(caller_job, service, mode):
    staged = stage(caller_job, service)
    value = json.loads((staged.control / "staged.json").read_bytes())
    value["commit" if mode == "base" else "request"] = "a" * 32
    (staged.control / "staged.json").write_bytes(h.encoded(value))
    with pytest.raises(h.FlociError):
        f.submit_floci_exchange(staged, timeout_ms=100)
    assert not (staged.control / "dispatched").exists()


@pytest.mark.parametrize(
    "response", [{}, {"jobDefinitions": []}, {"jobDefinitions": [None]}]
)
def test_missing_invalid_exact_definition(caller_job, service, monkeypatch, response):
    staged = stage(caller_job, service)
    monkeypatch.setattr(h, "batch", lambda *a: response)
    with pytest.raises(h.FlociError):
        f.submit_floci_exchange(staged, timeout_ms=100)
    assert (staged.control / "dispatched").exists()


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"jobs": []},
        {"jobs": [None]},
        {"jobs": [dict(jobDefinition="installed:1", jobQueue="local")]},
    ],
)
def test_diagnostic_bad_shape_does_not_supply_outcome(
    caller_job, service, monkeypatch, response
):
    job = f.submit_floci_exchange(stage(caller_job, service), timeout_ms=100)
    monkeypatch.setattr(h, "batch", lambda *a: response)
    with pytest.raises(h.FlociError):
        f.observe_floci_job(job, packet=job.control.with_name("bad"), timeout_ms=100)


@pytest.mark.parametrize(
    "field,value",
    [
        ("jobDefinition", "different:1"),
        ("jobQueue", "different"),
        ("retryStrategy", {"attempts": 2}),
        ("attempts", [{}, {}]),
        ("status", "UNKNOWN"),
    ],
)
def test_diagnostic_association_and_service_attempts(
    caller_job, service, monkeypatch, field, value
):
    job = f.submit_floci_exchange(stage(caller_job, service), timeout_ms=100)
    original = h.batch

    def changed(*args):
        result = original(*args)
        result["jobs"][0][field] = value
        return result

    monkeypatch.setattr(h, "batch", changed)
    with pytest.raises(h.FlociError):
        f.observe_floci_job(job, packet=job.control.with_name("bad"), timeout_ms=100)


def test_acknowledged_uuid_is_not_arn(caller_job, service):
    staged = stage(caller_job, service)
    service.response = dict(
        jobId=JOB_ID, jobName="dml-" + staged.expected.token, jobArn=JOB_ID
    )
    with pytest.raises(h.FlociError) as error:
        f.submit_floci_exchange(staged, timeout_ms=100)
    assert error.value.job_id == JOB_ID


@pytest.mark.parametrize(
    "rows", [None, [], [dict(name="unexpected", size=1, sha256="a" * 64)]]
)
def test_manifest_file_sets_exact_order(rows):
    with pytest.raises(h.FlociError):
        h.validate_rows(rows, ("job.json",))
    with pytest.raises(h.FlociError):
        h.fields({}, ("token",), "unsupported")


def test_valid_selected_bytes_do_not_authorize_wrong_phase_manifest(
    caller_completed, service
):
    path, workspace, expected, _, _ = caller_completed
    job = f.submit_floci_exchange(stage(caller_completed, service), timeout_ms=100)
    assert worker._publish(job, ex.ExchangeHandle(workspace, expected))
    old_key = h.object_path(job.remote, expected.token, "phases/completion.json")
    manifest = json.loads(service.objects.pop(old_key))
    manifest["phase"] = "initial"
    service.objects[
        h.object_path(job.remote, expected.token, "phases/initial.json")
    ] = h.encoded(manifest)
    with pytest.raises(h.FlociError, match="authoritative history"):
        f.observe_floci_job(job, packet=path.parent / "bad", timeout_ms=100)
    assert not (path.parent / "bad").exists()


def test_installed_worker_no_input_or_wrong_download_selection(
    caller_job, service, monkeypatch
):
    _, workspace, expected, *_ = caller_job
    with pytest.raises(h.FlociError, match="unavailable"):
        worker._inputs(remote(), expected.token, str(expected.commit))
    stage(caller_job, service)
    monkeypatch.setattr(h, "owned_spec", lambda *a: replace(expected, token="a" * 32))
    with pytest.raises(h.FlociError, match="staged selection"):
        worker._inputs(remote(), expected.token, str(expected.commit))


def test_job_bootstrap_no_packet_publication(caller_job):
    _, workspace, expected, *_ = caller_job
    handle = ex.ExchangeHandle(workspace, expected)
    assert worker._closed_packet(handle) is None
    assert (
        worker._publish(f.FlociJob(remote(), expected, workspace, JOB_ID), handle)
        is False
    )


def test_worker_module_entry_no_test_hooks(monkeypatch):
    monkeypatch.setattr("sys.argv", ["daggerml.floci_worker"])
    with pytest.raises(SystemExit) as error:
        runpy.run_module("daggerml.floci_worker", run_name="__main__")
    assert error.value.code == 2


def test_real_wire_conditional_header_and_extra_over_owned_body_bound():
    with wire([(0, raw(b"", declared=0))]) as (endpoint, captured):
        value = remote(endpoint=endpoint.endpoint)
        h.put_object(value, h.Budget(1000, 1), "a" * 32, "input/job.json", b"{}")
    assert "If-None-Match: *\r\n" in captured[0][0]
    with wire([(0, raw(b"abcd", declared=2))]) as (endpoint, _):
        with pytest.raises(h.FlociError, match="profile"):
            h.request(endpoint, h.Budget(1000, 1), "POST", "/", b"", "batch", 2)
    with wire([(0, b"HTTP/1.1 200 OK\r\nPartial")]) as (endpoint, _):
        with pytest.raises(h.FlociError):
            h.request(endpoint, h.Budget(1000, 1), "POST", "/", b"", "batch", 2)


@pytest.mark.parametrize(
    "size",
    [transfer.MAX_BUNDLE_BYTES, transfer.MAX_BUNDLE_BYTES + 1],
    ids=["original32MiB", "original32MiB-plus-one"],
)
def test_original_transfer_response_bound_not_only_scaled_descriptor(size):
    body = b"x" * size
    with wire([(0, raw(body, declared=size))]) as (endpoint, _):
        if size > transfer.MAX_BUNDLE_BYTES:
            with pytest.raises(h.FlociError, match="profile"):
                h.request(
                    endpoint,
                    h.Budget(10000, 1),
                    "POST",
                    "/",
                    b"",
                    "s3",
                    transfer.MAX_BUNDLE_BYTES,
                )
        else:
            assert (
                h.request(
                    endpoint,
                    h.Budget(10000, 1),
                    "POST",
                    "/",
                    b"",
                    "s3",
                    transfer.MAX_BUNDLE_BYTES,
                )[1]
                == body
            )
