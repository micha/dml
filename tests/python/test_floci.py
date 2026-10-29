"""Host framing/composition tests. Private service substitution is NOT Batch evidence."""

from dataclasses import replace
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import daggerml as d
from daggerml import exchange as ex, floci as f, floci_http as h, floci_worker as worker
import pytest

from test_caller_requests import caller_job, caller_completed, assert_file_unchanged
from test_exchange import exchange_runtime, typed_oracle

JOB_ID = "12345678-1234-1234-1234-123456789abc"
ARN = "arn:aws:batch:us-east-1:000000000000:"


def remote(**changes):
    values = dict(
        endpoint="http://127.0.0.1:4566",
        bucket="dml-local",
        prefix="iteration11/scope",
        queue="local",
        job_definition="installed:1",
        image="sha256:" + "a" * 64,
        python="/opt/dml/bin/python",
    )
    values.update(changes)
    return f.FlociRemote(**values)


class Service:
    """Finite in-memory HTTP substitution; real native history remains authoritative."""

    def __init__(self, endpoint):
        self.remote = endpoint
        self.objects, self.calls = {}, []
        self.status = "RUNNING"
        self.response = None
        self.definition = dict(
            jobDefinitionName="installed",
            revision=1,
            status="ACTIVE",
            type="container",
            containerProperties=dict(
                image=endpoint.image,
                command=[endpoint.python, "-m", "daggerml.floci_worker"],
            ),
            retryStrategy={"attempts": 1},
        )
        self.body = None

    def request(
        self, remote, budget, method, path, data, service, bound, *, create=False
    ):
        budget.calls -= 1
        assert budget.calls >= 0
        self.calls.append((method, path, create))
        if service == "s3":
            if method == "GET":
                return (200, self.objects[path]) if path in self.objects else (404, b"")
            assert create
            if path in self.objects:
                return 412, b""
            self.objects[path] = data
            return 200, b""
        value = json.loads(data)
        if path.endswith("describejobdefinitions"):
            result = {"jobDefinitions": [self.definition]}
        elif path.endswith("submitjob"):
            self.body = value
            result = self.response or dict(
                jobId=JOB_ID, jobName=value["jobName"], jobArn=ARN + "job/" + JOB_ID
            )
        else:
            assert path.endswith("describejobs") and value == {"jobs": [JOB_ID]}
            result = {
                "jobs": [
                    dict(
                        jobId=JOB_ID,
                        jobName=self.body["jobName"],
                        jobDefinition=ARN + "job-definition/installed:1",
                        jobQueue=ARN + "job-queue/local",
                        status=self.status,
                        retryStrategy={"attempts": 1},
                        attempts=[],
                        container=dict(
                            image=remote.image,
                            command=self.body["containerOverrides"]["command"],
                        ),
                    )
                ]
            }
        return 200, h.encoded(result)


@pytest.fixture
def service(monkeypatch):
    result = Service(remote())
    monkeypatch.setattr(h, "request", result.request)
    return result


def stage(case, service):
    path, workspace, spec, *_ = case
    return f.stage_floci_exchange(
        service.remote,
        workspace=workspace,
        expected=spec,
        control=path.parent / "control",
        timeout_ms=10000,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("endpoint", "https://local:4566"),
        ("endpoint", "http://user@local:4566"),
        ("endpoint", "http://local:4566/"),
        ("endpoint", "http://LOCAL:4566"),
        ("endpoint", "http://local:04566"),
        ("endpoint", "http://local"),
        ("endpoint", "http://local:4566?x"),
        ("endpoint", "http://local:4566#x"),
        ("endpoint", "http://local:99999"),
        ("endpoint", "http://[bad:4566"),
        ("endpoint", "http://local\n:4566"),
        ("endpoint", None),
        ("bucket", "ab"),
        ("bucket", "a..b"),
        ("prefix", "a/../b"),
        ("prefix", "a//b"),
        ("prefix", "a/"),
        ("queue", "-option"),
        ("image", "tag:latest"),
        ("python", "C:/python"),
        ("python", "/opt//python"),
        ("job_definition", "installed"),
        ("prefix", "e\u0301"),
        ("endpoint", "http://\ud800:1"),
    ],
    ids=lambda value: None,
)
def test_operational_profiles_reject_unsafe_noncanonical_spelling(field, value):
    with pytest.raises((h.FlociError, TypeError, UnicodeError)):
        remote(**{field: value})


def test_stage_submit_guard_saved_and_service_status_not_outcome(
    caller_job, service, monkeypatch
):
    path, workspace, spec, state, _ = caller_job
    before = (path / "data.mdb").read_bytes()
    staged = stage(caller_job, service)
    assert len(service.calls) == 3 and all(
        call[0] == "PUT" and call[2] for call in service.calls
    )
    assert service.calls[-1][1].endswith("input/manifest.json") and service.body is None
    assert_file_unchanged(path / "data.mdb", before)
    acknowledged = f.submit_floci_exchange(staged, timeout_ms=10000)
    assert acknowledged.job_id == JOB_ID and (staged.control / "dispatched").exists()
    count = len(service.calls)
    with pytest.raises(h.FlociError, match="already dispatched"):
        f.submit_floci_exchange(staged, timeout_ms=10000)
    with pytest.raises(TypeError):
        f.submit_floci_exchange(acknowledged, timeout_ms=10000)
    assert len(service.calls) == count
    saved = path.parent / "saved"
    with monkeypatch.context() as guard:
        guard.setattr(h, "request", lambda *a, **k: pytest.fail("identity is inert"))
        f.save_floci_job(saved, acknowledged)
        assert f.load_floci_job(saved) == acknowledged
        with pytest.raises(FileExistsError):
            f.save_floci_job(saved, acknowledged)
    workspace.rename(workspace.with_name("input.offline"))
    for status in ("FAILED", "SUCCEEDED", "RUNNING"):
        service.status = status
        target = path.parent / ("packet-" + status)
        got = f.observe_floci_job(acknowledged, packet=target, timeout_ms=10000)
        assert (
            got.lifecycle == "working"
            and got.phase == "bootstrap"
            and got.packet is None
            and got.snapshot is None
        )
        assert not target.exists() and got.service_status == status
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "mode", ["extra", "name", "arn-type", "arn-foreign", "receipt", "allocation"]
)
def test_any_later_acknowledgement_failure_retains_valid_id_and_guard(
    caller_job, service, monkeypatch, mode
):
    staged = stage(caller_job, service)
    response = dict(
        jobId=JOB_ID,
        jobName="dml-" + staged.expected.token,
        jobArn=ARN + "job/" + JOB_ID,
    )
    if mode == "extra":
        response["extra"] = 1
    elif mode == "name":
        response["jobName"] = "wrong"
    elif mode == "arn-type":
        response["jobArn"] = True
    elif mode == "arn-foreign":
        response["jobArn"] = ARN + "job/" + JOB_ID[:-1] + "d"
    elif mode == "receipt":
        (staged.control / "submitted.json").write_bytes(b"preexisting")
    else:
        monkeypatch.setattr(
            f, "FlociJob", lambda *a: (_ for _ in ()).throw(MemoryError())
        )
    service.response = response
    with pytest.raises(h.FlociError) as error:
        f.submit_floci_exchange(staged, timeout_ms=10000)
    assert error.value.job_id == JOB_ID
    count = len(service.calls)
    with pytest.raises(h.FlociError):
        f.submit_floci_exchange(staged, timeout_ms=10000)
    assert len(service.calls) == count


def test_accepted_call_lost_ack_unknown_marker_no_repair(
    caller_job, service, monkeypatch
):
    staged = stage(caller_job, service)
    original = service.request

    def lost(*args, **kwargs):
        result = original(*args, **kwargs)
        if args[3].endswith("submitjob"):
            raise h.FlociError("private accepted response suppression")
        return result

    monkeypatch.setattr(h, "request", lost)
    with pytest.raises(h.FlociError) as error:
        f.submit_floci_exchange(staged, timeout_ms=10000)
    assert error.value.job_id is None and service.body is not None
    with pytest.raises(h.FlociError):
        f.submit_floci_exchange(staged, timeout_ms=10000)
    assert len([call for call in service.calls if call[1].endswith("submitjob")]) == 1


@pytest.mark.parametrize(
    "change",
    [
        dict(type="multinode"),
        dict(revision=True),
        dict(status="INACTIVE"),
        dict(retryStrategy={"attempts": True}),
        dict(retryStrategy={"attempts": 2}),
        dict(nodeProperties={}),
        dict(parameters={"hidden": "x"}),
        dict(timeout={"attemptDurationSeconds": 60}),
        dict(containerProperties={"image": "tag"}),
    ],
)
def test_exact_definition_preflight_failure_consumes_guard_no_submission(
    caller_job, service, change
):
    staged = stage(caller_job, service)
    service.definition.update(change)
    with pytest.raises(h.FlociError):
        f.submit_floci_exchange(staged, timeout_ms=10000)
    assert (staged.control / "dispatched").exists() and service.body is None


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
def test_public_packet_transport_complete_typed_history_atomic_offline_return(
    caller_completed, service, phase
):
    path, workspace, spec, state, run = caller_completed
    # Host emulates selected phases after real child reaping, not a live Batch job.
    staged = stage(caller_completed, service)
    job = f.submit_floci_exchange(staged, timeout_ms=10000)
    handle = ex.ExchangeHandle(workspace, spec)
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        if phase != "completion":
            tx.update_ref(spec.worker_ref, run.context.pre_dispatch)
            if phase == "initial":
                tx.update_ref(run.context.publication_ref, run.context.pre_dispatch)
    done = worker._publish(job, handle)
    assert done == (phase == "completion")
    original_objects = dict(service.objects)
    assert worker._publish(job, handle) == done
    assert service.objects == original_objects
    got = f.observe_floci_job(job, packet=path.parent / "packet", timeout_ms=10000)
    assert got.phase == phase and got.lifecycle == ("done" if done else "working")
    assert got.service_status == "RUNNING" and got.job_id == JOB_ID
    assert got.snapshot == ex.read_observation(got.packet, expected=spec)
    expected_bytes = typed_oracle(workspace / "worker.dml", (got.snapshot.commit,))
    workspace.rename(workspace.with_name("worker.offline"))
    service.objects.clear()
    received = ex.receive_observation(
        path, packet=got.packet, expected=spec, ref="received"
    )
    assert received.request == spec.request
    assert typed_oracle(path, (received.commit,)) == expected_bytes
    assert (
        ex.receive_observation(path, packet=got.packet, expected=spec, ref="received")
        == received
    )


@pytest.mark.parametrize(
    "mode",
    ["phase", "root", "job", "attempt-bool", "count-bool", "digest", "missing-file"],
)
def test_immutable_manifest_and_bytes_rejection_before_packet_or_a(
    caller_completed, service, mode
):
    path, workspace, spec, _, _ = caller_completed
    job = f.submit_floci_exchange(stage(caller_completed, service), timeout_ms=10000)
    worker._publish(job, ex.ExchangeHandle(workspace, spec))
    key = h.object_path(service.remote, spec.token, "phases/completion.json")
    value = json.loads(service.objects[key])
    if mode == "phase":
        value["phase"] = "initial"
    elif mode == "root":
        value["selected_commit"] = "b" * 32
    elif mode == "job":
        value["job_id"] = JOB_ID[:-1] + "d"
    elif mode == "attempt-bool":
        value["attempt"] = True
    elif mode == "count-bool":
        value["files"][0]["size"] = True
    elif mode == "digest":
        value["files"][0]["sha256"] = "b" * 64
    else:
        del service.objects[
            h.object_path(
                service.remote,
                spec.token,
                "snapshots/" + value["selected_commit"] + "/job.json",
            )
        ]
    service.objects[key] = h.encoded(value)
    before = (path / "data.mdb").read_bytes()
    target = path.parent / "invalid-packet"
    with pytest.raises(h.FlociError):
        f.observe_floci_job(job, packet=target, timeout_ms=10000)
    assert not target.exists()
    assert_file_unchanged(path / "data.mdb", before)
