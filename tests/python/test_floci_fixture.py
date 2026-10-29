"""Default-safe fixture ownership regressions; no Docker startup or daemon calls."""

import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "floci/fixture.py"
spec = importlib.util.spec_from_file_location("floci_fixture_support", PATH)
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def fixture():
    value = support.Fixture.__new__(support.Fixture)
    value.state = dict(
        owner="owner",
        service_id="service",
        name="service-name",
        clients=[],
        jobs=[],
        network="private",
        image="immutable",
    )
    value.save = lambda: None
    return value


@pytest.mark.parametrize(
    "status", ["SUBMITTED", "PENDING", "RUNNABLE", "STARTING", "RUNNING"]
)
def test_no_container_yet_does_not_authorize_stop_for_accepted_job(status):
    value = fixture()
    value.state["jobs"] = [dict(id="job", token="token")]
    value.batch = lambda *a: {
        "jobs": [
            dict(
                jobId="job",
                jobName="dml-token",
                status=status,
                retryStrategy={"attempts": 1},
                attempts=[],
            )
        ]
    }
    value.children = lambda: []
    value.clients_stopped = lambda: None
    value.docker = lambda *a, **k: pytest.fail(
        "no endpoint stop before job terminal proof"
    )
    with pytest.raises(AssertionError, match="owned writer"):
        value.stop()


def test_unknown_ack_is_blocker_without_automatic_listjobs_or_resubmit():
    value = fixture()
    value.job_intent("token", label="unknown-ack")
    assert value.state["jobs"] == [dict(id=None, token="token", label="unknown-ack")]
    value.batch = lambda *a: pytest.fail(
        "unknown ID cannot authorize API reconciliation/stop"
    )
    with pytest.raises(AssertionError, match="acknowledgement unknown"):
        value.jobs_terminal()


def test_create_response_loss_preserves_name_intent_before_docker_call():
    value = fixture()
    saves = []
    value.save = lambda: saves.append([dict(row) for row in value.state["clients"]])

    def lost(*args, **kwargs):
        assert args[0] == "create"
        assert saves[-1] == [
            dict(name="service-name-client-0", id=None, create_intent=True)
        ]
        raise TimeoutError("private create acknowledgement suppression")

    value.docker = lost
    with pytest.raises(TimeoutError):
        value.client("pass")
    assert value.state["clients"][0]["id"] is None
    with pytest.raises(AssertionError, match="create acknowledgement uncertain"):
        value.clients_stopped()


@pytest.mark.parametrize("census", [b"service\nclient\nunknown\n", b"service\n"])
def test_all_owner_census_rejects_untracked_or_missing_clients(census):
    value = fixture()
    value.state["clients"] = [dict(name="client-name", id="client")]
    value.inspect = lambda name: dict(
        Id="client",
        Name="/client-name",
        Config={"Labels": {"dml.owner": "owner"}},
        State={"Running": False},
    )
    value.docker = lambda *a: census
    with pytest.raises(AssertionError, match="untracked owned"):
        value.clients_stopped()


def test_terminal_exact_job_and_complete_stopped_client_census_pass():
    value = fixture()
    value.state["jobs"] = [dict(id="job", token="token")]
    value.batch = lambda *a: {
        "jobs": [
            dict(
                jobId="job",
                jobName="dml-token",
                status="SUCCEEDED",
                retryStrategy={"attempts": 1},
                attempts=[{}],
            )
        ]
    }
    value.jobs_terminal()
    assert value.state["jobs"][0]["terminal_proof"]["jobId"] == "job"
    value.state["clients"] = [dict(name="client-name", id="client")]
    value.inspect = lambda name: dict(
        Id="client",
        Name="/client-name",
        Config={"Labels": {"dml.owner": "owner"}},
        State={"Running": False},
    )
    value.docker = lambda *a: b"service\nclient\n"
    value.clients_stopped()


@pytest.mark.parametrize("fresh", [b"", b"original\n", b"new-child\n"])
def test_natural_list_inspect_disappearance_bounded_census_not_error_swallow(fresh):
    value = fixture()
    calls = []
    original_error = RuntimeError("private inspect race")

    def docker(*args):
        calls.append(args)
        if args[0] == "inspect":
            raise original_error
        assert args[0] == "ps"
        return b"original\n" if len(calls) == 1 else fresh

    value.docker = docker
    if fresh:
        with pytest.raises(RuntimeError) as error:
            value.children()
        assert error.value is original_error
    else:
        assert value.children() == []
    assert len(calls) == 3 and [call[0] for call in calls] == ["ps", "inspect", "ps"]


def test_non_disappearance_inspect_timeout_does_not_receive_extra_census():
    value = fixture()
    calls = []

    def docker(*args):
        calls.append(args)
        if args[0] == "ps":
            return b"original\n"
        raise TimeoutError("private unresolved Docker IO")

    value.docker = docker
    with pytest.raises(TimeoutError):
        value.children()
    assert len(calls) == 2


def test_background_client_wait_uncertainty_retains_registered_resource():
    value = fixture()
    calls = []

    def docker(*args, **kwargs):
        calls.append(args)
        if args[0] == "wait":
            raise TimeoutError("owned background reader wait uncertain")
        return b"client\n"

    value.docker = docker
    identifier = value.client("pass", background=True)
    assert identifier == "client" and value.state["clients"][0]["id"] == identifier
    with pytest.raises(TimeoutError):
        value.finish_client(identifier)
    assert value.state["clients"][0]["id"] == identifier
    assert not any(row[0] in ("stop", "kill", "rm") for row in calls)


@pytest.mark.parametrize("owner", ["owner", "foreign"])
def test_background_client_known_reap_checks_identity_before_copy(owner):
    value = fixture()
    value.state["clients"] = [dict(name="client", id="identifier")]
    calls = []
    value.docker = lambda *a, **k: calls.append(a) or b"{}"
    value.inspect = lambda *a: dict(
        Id="identifier",
        Config={"Labels": {"dml.owner": owner}},
        State={"Running": False, "ExitCode": 0},
    )
    if owner == "foreign":
        with pytest.raises(AssertionError):
            value.finish_client(
                "identifier", outputs=(("/tmp/packet", "owned-target"),)
            )
        assert not any(row[0] == "cp" for row in calls)
    else:
        assert (
            value.finish_client(
                "identifier", outputs=(("/tmp/packet", "owned-target"),)
            )
            == b"{}"
        )
        assert [row[0] for row in calls] == ["wait", "cp", "logs"]


def test_service_key_reader_does_not_repeat_old_ec2_first_field_regex_defect():
    rows = ["batch", "s3", "cloudwatchlogs", "iam", "ec2"] + [
        "service" + str(n) for n in range(123)
    ]
    app = "\n  services:\n" + "".join(
        "    "
        + name
        + ":\n      other: value\n      # retained comment\n      enabled: true\n"
        for name in rows
    )
    assert support.service_keys(app) == rows
