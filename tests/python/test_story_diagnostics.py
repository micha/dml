"""Bounded TEST-ONLY old-story evidence preserves primary failure and boundaries."""

import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import daggerml as d
from daggerml import exchange as ex, transfer
import pytest

import story_diagnostics as diagnostic
from test_caller_requests import caller_job, caller_completed
from test_exchange import exchange_runtime, typed_oracle


class OwnerProcess:
    def __init__(self, code):
        self.code = code
        self.polls = 0

    def poll(self):
        self.polls += 1
        return self.code

    def wait(self, *args, **kwargs):
        pytest.fail("diagnostic must not wait/reap/retry")

    def terminate(self):
        pytest.fail("diagnostic must not signal")

    kill = terminate


def failing_story(script, values, original):
    namespace = dict(values, ORIGINAL=original)
    exec(
        compile(
            """def produce(args):
 workspace=WORKSPACE
 phase=PHASE
 launch=LAUNCH
 spec=SPEC
 snapshots=SNAPSHOTS
 raise ORIGINAL
""",
            str((Path(values["WORKSPACE"]).parent / script).resolve()),
            "exec",
        ),
        namespace,
    )
    return namespace["produce"]


def note(error):
    text = error.__notes__[-1]
    assert len(text.encode("utf-8")) <= diagnostic.MAX_NOTE_BYTES
    assert "\x00" not in text and "\x1b" not in text
    return json.loads(text.removeprefix("owned-story-diagnostic: "))


@pytest.mark.parametrize("script", ["asynchronous_execution.py", "caller_requests.py"])
def test_both_harnesses_preserve_original_bounded_logs_typed_final_no_execution(
    caller_completed, monkeypatch, script
):
    path, source, spec, state, run = caller_completed
    story = path.parent / "story"
    workspace = story / "workspace-3"
    workspace.mkdir(parents=True)
    shutil.copytree(source / "worker.dml", workspace / "worker.dml")
    (workspace / "worker.stdout").write_bytes(b"\x00" * 1048576)
    (workspace / "worker.stderr").write_bytes(
        b"ignored prefix" * 1048576 + b"synthetic worker native error 2\n"
    )
    baseline = typed_oracle(workspace / "worker.dml", (run.final_commit,))
    original = AssertionError("synthetic outer worker failure")
    process = OwnerProcess(1)
    snapshot = dict(
        phase="completion",
        commit=str(run.final_commit),
        request_id=run.request_id,
        attempt_id=run.attempt_id,
    )
    function = failing_story(
        script,
        dict(
            WORKSPACE=workspace,
            PHASE="completion",
            LAUNCH=SimpleNamespace(process=process),
            SPEC=spec,
            SNAPSHOTS=[snapshot],
        ),
        original,
    )

    def deny(*args, **kwargs):
        pytest.fail("diagnostic must not dispatch/import/repair/write")

    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", deny)
        guard.setattr(ex, "start_exchange", deny)
        guard.setattr(ex, "execute_exchange", deny)
        guard.setattr(transfer, "import_commit", deny)
        for name in (
            "put_record",
            "put_datum",
            "put_tree",
            "put_commit",
            "create_ref",
            "update_ref",
        ):
            guard.setattr(d.Transaction, name, deny)
        with pytest.raises(AssertionError) as caught:
            diagnostic.run_story(function, story)
    assert (
        caught.value is original and str(original) == "synthetic outer worker failure"
    )
    report = note(original)
    assert report["phase"] == "completion" and report["workspace"] == "workspace-3"
    assert str(story) not in original.__notes__[-1]
    assert report["selected"]["commit"] == str(run.final_commit)
    assert report["owner"] == dict(state="reaped", returncode=1)
    assert report["files"]["worker.dml"] and report["files"]["worker.stderr"]
    assert report["logs"]["worker.stdout"]["size"] == 1048576
    assert report["logs"]["worker.stderr"]["tail"].endswith(
        "synthetic worker native error 2\n"
    )
    assert report["logs"]["worker.stderr"]["truncated"]
    assert report["final"]["outcome"]["role"] == "local-success-v1"
    assert report["final"]["cleanup"]["disposition"] == "ok"
    assert process.polls == 1
    assert typed_oracle(workspace / "worker.dml", (run.final_commit,)) == baseline


@pytest.mark.parametrize("code", [None, 0], ids=["live", "reaped-read-error"])
def test_live_owner_skips_store_and_native_read_failure_does_not_replace_original(
    tmp_path, monkeypatch, code
):
    story = tmp_path / "story"
    workspace = story / "workspace-1"
    workspace.mkdir(parents=True)
    process = OwnerProcess(code)
    original = ValueError("original observer error")
    values = dict(
        WORKSPACE=workspace,
        PHASE="initial",
        LAUNCH=SimpleNamespace(process=process),
        SPEC=object(),
        SNAPSHOTS=[],
    )
    called = []

    def unreadable(*args):
        called.append(True)
        raise d.DmlError("storage_error", 2, "synthetic native open failure")

    monkeypatch.setattr(diagnostic, "typed_final", unreadable)
    with pytest.raises(ValueError) as caught:
        diagnostic.run_story(
            failing_story("asynchronous_execution.py", values, original), story
        )
    assert caught.value is original
    report = note(original)
    if code is None:
        assert (
            called == [] and report["final"]["state"] == "skipped-live-or-unknown-owner"
        )
    else:
        assert called == [True]
        assert report["final"]["inspection_error"] == dict(
            type="DmlError", code="storage_error", native_code=2
        )
    assert process.polls == 1


@pytest.mark.parametrize("fault", ["allocation", "outside", "budget"])
def test_collector_failure_unowned_paths_and_budget_preserve_original(
    tmp_path, monkeypatch, fault
):
    story = tmp_path / "story"
    story.mkdir()
    workspace = (tmp_path / "unowned") if fault == "outside" else story / "workspace-1"
    workspace.mkdir()
    original = RuntimeError("original story error")
    function = failing_story(
        "caller_requests.py",
        dict(
            WORKSPACE=workspace,
            PHASE="publication",
            LAUNCH=None,
            SPEC=None,
            SNAPSHOTS=[],
        ),
        original,
    )
    if fault == "allocation":

        def denied(*args, **kwargs):
            raise MemoryError("private diagnostic allocation")

        monkeypatch.setattr(diagnostic, "collect", denied)
    elif fault == "budget":
        (workspace / "worker.stderr").write_bytes(b"x" * 1048576)
        monkeypatch.setattr(diagnostic, "MAX_NOTE_BYTES", 128)
    else:
        monkeypatch.setattr(
            diagnostic, "tail", lambda *a: pytest.fail("outside log access")
        )
    with pytest.raises(RuntimeError) as caught:
        diagnostic.run_story(function, story)
    assert caught.value is original and str(original) == "original story error"
    if fault == "outside":
        assert note(original)["workspace"] == "outside-owned-story"
    elif fault == "budget":
        assert note(original) == {"capture_error": "profile-overflow"}


def test_success_invokes_once_no_diagnostics(monkeypatch, tmp_path):
    calls = []
    marker = object()
    monkeypatch.setattr(
        diagnostic,
        "note_failure",
        lambda *a: pytest.fail("no successful-run diagnostic"),
    )

    def success(args):
        calls.append(args)
        return marker

    assert diagnostic.run_story(success, tmp_path) is marker
    assert calls == [[str(tmp_path)]]


def test_original_selected_receipt_phase_survives_later_final_read(tmp_path):
    story = tmp_path / "story"
    workspace = story / "workspace-3"
    workspace.mkdir(parents=True)
    original = d.DmlError("storage_error", 2, "synthetic observer open error")
    process = OwnerProcess(0)
    selected = d.ObjectId.from_hex("1" * 32)
    namespace = dict(
        WORKSPACE=workspace,
        LAUNCH=SimpleNamespace(process=process),
        ORIGINAL=original,
        SELECTED=selected,
    )
    exec(
        compile(
            """def observe_exchange():
 receipt={'phase':'initial','selected_commit':SELECTED,'request_id':'q-'+'2'*32,'attempt_id':'a-'+'3'*32}
 raise ORIGINAL
""",
            str((story / "exchange.py").resolve()),
            "exec",
        ),
        namespace,
    )
    exec(
        compile(
            """def produce(args):
 workspace=WORKSPACE
 phase='initial'
 launch=LAUNCH
 spec=None
 snapshots=[]
 observe_exchange()
""",
            str((story / "asynchronous_execution.py").resolve()),
            "exec",
        ),
        namespace,
    )
    with pytest.raises(d.DmlError) as caught:
        diagnostic.run_story(namespace["produce"], story)
    assert caught.value is original
    report = note(original)
    assert report["selected"]["phase"] == "initial"
    assert report["selected"]["commit"] == str(selected)
    assert report["original"] == dict(
        type="DmlError", code="storage_error", native_code=2
    )
    assert process.polls == 1
