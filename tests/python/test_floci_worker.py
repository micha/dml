"""Private owner/publisher failures, not installed fault hooks or Batch evidence."""

from types import SimpleNamespace

from daggerml import exchange as ex, floci as f, floci_http as h, floci_worker as worker
import pytest

from test_caller_requests import caller_job
from test_exchange import exchange_runtime
from test_floci import remote, JOB_ID, service


@pytest.mark.parametrize("failure", ["publish", "poll", "none"])
@pytest.mark.parametrize("final_failure", [False, True])
def test_unconditional_final_readonly_attempt_after_known_reap_preserves_errors(
    caller_job, monkeypatch, failure, final_failure
):
    _, workspace, expected, *_ = caller_job
    handle = ex.ExchangeHandle(workspace, expected)
    primary = OSError("private initial failure")
    final = OSError("private final failure")
    process = SimpleNamespace(returncode=None)
    events = []

    def poll():
        events.append("poll")
        if failure == "poll":
            raise primary
        return None if events.count("poll") == 1 else 0

    def wait(timeout):
        events.append("reap")
        process.returncode = 0
        return 0

    process.poll = poll
    launch = SimpleNamespace(process=process, wait=wait)
    monkeypatch.setattr(worker, "_inputs", lambda *a: handle)
    monkeypatch.setattr(worker.exchange, "start_exchange", lambda *a: launch)
    monkeypatch.setattr(worker.time, "sleep", lambda *a: None)

    def publish(*a):
        events.append("publish")
        if process.returncode is None and failure == "publish":
            raise primary
        if process.returncode is not None and final_failure:
            raise final
        return True

    monkeypatch.setattr(worker, "_publish", publish)
    if failure == "none" and not final_failure:
        worker.run(
            remote(), expected.token, str(expected.commit), job_id=JOB_ID, attempt="1"
        )
    else:
        with pytest.raises(worker.FlociWorkerError) as error:
            worker.run(
                remote(),
                expected.token,
                str(expected.commit),
                job_id=JOB_ID,
                attempt="1",
            )
        assert error.value.launch is launch
        assert error.value.primary_error is (None if failure == "none" else primary)
        assert error.value.final_error is (final if final_failure else None)
        assert error.value.__cause__ is (primary if failure != "none" else final)
    assert events[-2:] == ["reap", "publish"]


def test_uncertain_wait_retains_same_owner_no_signal_bounded_diagnostic(
    monkeypatch, capsys
):
    process = SimpleNamespace(returncode=None)
    errors = [OSError(), KeyboardInterrupt(), TimeoutError()]
    calls = []

    def wait(timeout):
        calls.append(timeout)
        if errors:
            raise errors.pop()
        process.returncode = 0
        return 0

    owner = SimpleNamespace(process=process, wait=wait)
    monkeypatch.setattr(worker.time, "sleep", lambda *a: None)
    assert worker._reap(owner) is None
    assert calls == [1, 1, 1, 1]
    assert capsys.readouterr().err == "Floci worker wait disposition pending\n"


@pytest.mark.parametrize(
    "failure", ["write", "flush", "sleep-oserror", "sleep-interrupt"]
)
def test_diagnostic_and_sleep_errors_cannot_escape_uncertain_owned_wait(
    monkeypatch, failure
):
    process = SimpleNamespace(returncode=None)
    acquired_error = (
        OSError("private secondary IO failure")
        if failure != "sleep-interrupt"
        else KeyboardInterrupt()
    )
    waits, writes, flushes, sleeps = [], [], [], []

    def wait(timeout):
        waits.append(timeout)
        if len(waits) < 3:
            assert process.returncode is None
            raise TimeoutError()
        process.returncode = 0
        return 0

    class Stderr:
        def write(self, data):
            writes.append(data)
            if failure == "write":
                raise acquired_error

        def flush(self):
            flushes.append(True)
            if failure == "flush":
                raise acquired_error

    def sleep(seconds):
        sleeps.append(seconds)
        if failure.startswith("sleep-"):
            raise acquired_error

    owner = SimpleNamespace(process=process, wait=wait)
    with monkeypatch.context() as guarded:
        guarded.setattr(worker.sys, "stderr", Stderr())
        guarded.setattr(worker.time, "sleep", sleep)
        result = worker._reap(owner)
    assert result is acquired_error and waits == [1, 1, 1] and process.returncode == 0
    assert len(writes) <= 2 and len(flushes) <= 1 and sleeps == [0.2, 0.2]


def test_known_reap_permanent_close_error_not_retried_or_logged(monkeypatch, capsys):
    process = SimpleNamespace(returncode=None)
    close_error = OSError("permanent stream-close failure")
    calls = []

    def wait(timeout):
        calls.append(timeout)
        process.returncode = 0
        raise close_error

    launch = SimpleNamespace(process=process, wait=wait)
    assert worker._reap(launch) is close_error
    assert calls == [1] and capsys.readouterr().err == ""
    monkeypatch.setattr(worker, "_publish", lambda *a: True)
    assert worker._finish(None, None, launch) == (close_error, None)


def test_missing_final_packet_is_error_not_done_after_known_reap(monkeypatch):
    owner = SimpleNamespace(
        process=SimpleNamespace(returncode=1), wait=lambda timeout: 1
    )
    monkeypatch.setattr(worker, "_publish", lambda *a: False)
    reap_error, final_error = worker._finish(None, None, owner)
    assert reap_error is None and isinstance(final_error, h.FlociError)


def test_inputs_download_exact_closed_bytes_before_any_start(
    caller_job, service, monkeypatch, tmp_path
):
    from test_floci import stage

    _, original, expected, *_ = caller_job
    staged = stage(caller_job, service)
    handle = worker._inputs(staged.remote, expected.token, str(expected.commit))
    try:
        assert ex.read_exchange_spec(handle.workspace) == expected
        assert (handle.workspace / "input.bundle").read_bytes() == (
            original / "input.bundle"
        ).read_bytes()
        assert not (handle.workspace / "worker.dml").exists()
    finally:
        # This private test proves no start happened; remove only allocated fixture workspace.
        import shutil

        shutil.rmtree(handle.workspace)


@pytest.mark.parametrize("attempt", [None, 1, "2", "01"])
def test_service_retry_rejects_before_input_or_dispatch(monkeypatch, attempt):
    monkeypatch.setattr(
        worker, "_inputs", lambda *a: pytest.fail("no download/dispatch")
    )
    with pytest.raises(h.FlociError):
        worker.run(remote(), "a" * 32, "b" * 32, job_id=JOB_ID, attempt=attempt)


def test_entrypoint_finite_fixed_config_errors(monkeypatch, capsys):
    assert worker.main([]) == 2
    assert worker.main(["{}", "a" * 32, "b" * 32]) == 1
    monkeypatch.setenv("AWS_BATCH_JOB_ID", JOB_ID)
    monkeypatch.setenv("AWS_BATCH_JOB_ATTEMPT", "1")
    captured = []
    monkeypatch.setattr(worker, "run", lambda *a, **k: captured.append((a, k)))
    assert (
        worker.main(
            [h.encoded(f._remote_document(remote())).decode(), "a" * 32, "b" * 32]
        )
        == 0
    )
    assert captured[0][1] == dict(job_id=JOB_ID, attempt="1")
    assert "Floci worker failed" in capsys.readouterr().err
