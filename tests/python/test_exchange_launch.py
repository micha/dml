"""Retained one-shot launch, saved identity and finite application-owned real workers."""

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time

import daggerml as d
from daggerml import exchange as ex
from daggerml import exchange_worker
import pytest

from test_exchange import (
    job,
    exchange_runtime,
    initialize,
    prepare,
    typed_oracle,
    assert_main,
)
from test_exchange_progress import handle, observed_form


def wait_file(file, process, timeout=5):
    deadline = time.monotonic() + timeout
    while not file.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert file.exists(), "private finite child barrier not reached"


def barrier_source(directory, nonzero=False):
    # Source itself is test-owned captured trusted code. No installed fault hook.
    return (
        """import time,sys
from pathlib import Path
import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
base=Path(%r)
def barrier(name):
 (base/(name+'-ready')).write_text('ready')
 end=time.monotonic()+8
 while not (base/(name+'-release')).exists():
  if time.monotonic()>end: raise TimeoutError('private child watchdog')
  time.sleep(.01)
barrier('initial')
with d.Repository(c.repository_path) as r,r.write() as t:
 left=t.get_datum(t.get_node(t.lookup_node(c.inputs,'left')).datum).value
 right=t.get_datum(t.get_node(t.lookup_node(c.inputs,'right')).datum).value
 n=t.put_literal(t.put_datum(left+right))
 publish_result(t,c,t.put_dag(root=n,bindings={'result':n}))
barrier('publication')
sys.exit(%d)
"""
        % (str(directory), 7 if nonzero else 0)
    ).encode()


def fresh_observe(saved, packet):
    code = """import sys,json
from daggerml.exchange import load_exchange_handle,observe_exchange
h=load_exchange_handle(sys.argv[1]); o=observe_exchange(h,packet=sys.argv[2]); s=o.snapshot
print(json.dumps({'phase':o.phase,'lifecycle':o.lifecycle,'request':s.request_id,'attempt':s.attempt_id,'commit':str(s.commit)}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(saved), str(packet)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    "nonzero", (False, True), ids=("zero", "nonzero-after-publication")
)
def test_fixed_worker_returns_while_child_held_fresh_clients_same_occurrence(
    tmp_path, exchange_runtime, nonzero
):
    path, workspace = tmp_path / "a", tmp_path / "work"
    state = initialize(path, barrier_source(tmp_path, nonzero))
    spec = prepare(path, workspace, state[0])
    saved = tmp_path / "saved.json"
    h = handle(workspace, spec)
    ex.save_exchange_handle(saved, h)
    assert ex.load_exchange_handle(saved) == h
    path.rename(tmp_path / "a-offline")
    launch = ex.start_exchange(h)
    try:
        wait_file(tmp_path / "initial-ready", launch.process)
        assert launch.process.poll() is None
        with pytest.raises(subprocess.TimeoutExpired):
            launch.wait(timeout=0.01)
        assert not launch._stdout.closed and not launch._stderr.closed
        p = fresh_observe(saved, tmp_path / "p")  # fresh client exits normally
        assert p["phase"] == "initial" and p["lifecycle"] == "working"
        before = (workspace / "worker.dml/data.mdb").read_bytes()
        with pytest.raises(ex.ExchangeError):
            ex.start_exchange(ex.load_exchange_handle(saved))
        assert (workspace / "worker.dml/data.mdb").read_bytes() == before
        (tmp_path / "initial-release").touch()
        wait_file(tmp_path / "publication-ready", launch.process)
        u = fresh_observe(saved, tmp_path / "u")
        assert u["phase"] == "publication" and u["lifecycle"] == "working"
        assert launch.process.poll() is None
        assert p["request"] == u["request"] and p["attempt"] == u["attempt"]
        (tmp_path / "publication-release").touch()
        assert (
            launch.wait(timeout=15) == 0
        )  # computational failure is normal worker completion
        assert launch._stdout.closed and launch._stderr.closed
        f = fresh_observe(saved, tmp_path / "f")
        assert f["phase"] == "completion" and f["lifecycle"] == "done"
        assert f["request"] == u["request"] and f["attempt"] == u["attempt"]
    finally:
        # Never kill worker with live child. Cooperative release + child watchdog,
        # then direct worker wait/reap. Failing watchdog is not cleanup assurance.
        (tmp_path / "initial-release").touch()
        (tmp_path / "publication-release").touch()
        launch.wait(timeout=20)
        (tmp_path / "a-offline").rename(path)
    (workspace / "worker.dml").rename(workspace / "worker.offline")
    for phase in ("p", "u", "f"):
        got = ex.receive_observation(
            path, packet=tmp_path / phase, expected=spec, ref=phase
        )
        assert got.request_id == f["request"] and got.attempt_id == f["attempt"]
        if phase == "f":
            assert got.completion.outcome == ("failure" if nonzero else "success")
            assert got.completion.cleanup == "ok"
            assert (got.completion.evidence is not None) == nonzero
            assert (got.completion.result is not None) != nonzero
        else:
            assert got.completion is None
    assert_main(path, state)


@pytest.mark.parametrize(
    "artifact",
    (
        "launched",
        "started",
        "worker.dml",
        "worker-ready.json",
        "output.bundle",
        "completion.json",
        "worker.stdout",
        "worker.stderr",
    ),
)
def test_start_preexisting_artifact_never_spawns(job, monkeypatch, artifact):
    path, workspace, spec, state = job
    (workspace / artifact).touch()
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("must not spawn")
    )
    with pytest.raises(ex.ExchangeError):
        ex.start_exchange(handle(workspace, spec))
    assert_main(path, state)


@pytest.mark.parametrize("fault", ("stdout", "stderr", "spawn", "owner"))
def test_catchable_launch_setup_fault_retains_marker_and_closes_streams(
    job, monkeypatch, fault
):
    import builtins

    path, workspace, spec, state = job
    opening, streams = builtins.open, []

    def opened(file, *args, **kwargs):
        if Path(file).name == "worker." + fault:
            raise PermissionError("private log-open denial")
        stream = opening(file, *args, **kwargs)
        if Path(file).name in ("worker.stdout", "worker.stderr"):
            streams.append(stream)
        return stream

    monkeypatch.setattr(builtins, "open", opened)
    if fault == "spawn":
        monkeypatch.setattr(
            subprocess,
            "Popen",
            lambda *a, **k: (_ for _ in ()).throw(OSError("private spawn denied")),
        )
    elif fault == "owner":
        monkeypatch.setattr(
            ex,
            "WorkerLaunch",
            lambda *a, **k: (_ for _ in ()).throw(
                MemoryError("private owner allocation")
            ),
        )
    else:
        monkeypatch.setattr(
            subprocess, "Popen", lambda *a, **k: pytest.fail("must not spawn")
        )
    with pytest.raises((OSError, MemoryError)):
        ex.start_exchange(handle(workspace, spec))
    assert (workspace / "launched").exists() and not (workspace / "started").exists()
    assert all(stream.closed for stream in streams)
    with pytest.raises(ex.ExchangeError):
        ex.start_exchange(handle(workspace, spec))


def test_actual_spawn_ack_loss_preserves_known_owner(job):
    path, workspace, spec, state = job
    owner = []

    def application():
        owner.append(ex.start_exchange(handle(workspace, spec)))
        raise OSError("application response lost after actual spawn")

    with pytest.raises(OSError):
        application()
    try:
        with pytest.raises(ex.ExchangeError):
            ex.start_exchange(handle(workspace, spec))
        assert owner[0].wait(timeout=15) == 0
        assert (
            ex.observe_exchange(
                handle(workspace, spec), packet=workspace.parent / "packet"
            ).lifecycle
            == "done"
        )
    finally:
        owner[0].wait(timeout=20)


@pytest.mark.parametrize(
    "data",
    (
        b"{}",
        b"[]",
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{} {}",
        b"[" * 2000,
        b"x" * 8193,
    ),
    ids=(
        "fields",
        "array",
        "duplicate",
        "nan",
        "utf8",
        "bom",
        "trailing",
        "deep",
        "oversize",
    ),
)
def test_saved_handle_strict_framing_no_dispatch(job, data, monkeypatch):
    path, workspace, spec, state = job
    saved = workspace.parent / "handle.json"
    saved.write_bytes(data)
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("load never starts")
    )
    with pytest.raises(ex.ExchangeError):
        ex.load_exchange_handle(saved)


def test_handle_types_nested_exact_fields_bounds_and_no_workspace_action(job):
    path, workspace, spec, state = job
    with pytest.raises(TypeError):
        ex.ExchangeHandle(workspace, None)
    for operation in (
        lambda: ex.start_exchange(None),
        lambda: ex.observe_exchange(None, packet="x"),
        lambda: ex.save_exchange_handle(workspace / "saved", None),
    ):
        with pytest.raises(TypeError):
            operation()
    saved = workspace.parent / "saved"
    ex.save_exchange_handle(saved, handle(workspace, spec))
    with pytest.raises(FileExistsError):
        ex.save_exchange_handle(saved, handle(workspace, spec))
    document = json.loads(saved.read_bytes())
    for changes in (
        {"workspace": 1},
        {"expected": []},
        {"expected": dict(document["expected"], format="bad")},
        {"expected": dict(document["expected"], extra=True)},
    ):
        saved.write_text(json.dumps(dict(document, **changes)))
        with pytest.raises(ex.ExchangeError):
            ex.load_exchange_handle(saved)
    huge = ex.ExchangeHandle("/" + "x" * 8192, spec)
    with pytest.raises(ex.ExchangeError):
        ex.save_exchange_handle(workspace.parent / "large", huge)
    # Loading only current identity doesn't stat or act on serialized paths.
    ex.save_exchange_handle(
        workspace.parent / "absent", handle(workspace.parent / "missing", spec)
    )
    assert (
        ex.load_exchange_handle(workspace.parent / "absent").workspace.name == "missing"
    )
    with pytest.raises(ex.ExchangeError):
        ex.start_exchange(handle(workspace, replace(spec, token="0" * 32)))


def test_fixed_worker_main_measured(job, monkeypatch):
    path, workspace, spec, state = job
    called = []
    monkeypatch.setattr(
        exchange_worker, "execute_exchange", lambda value: called.append(value)
    )
    exchange_worker.main([str(workspace)])
    assert called == [str(workspace)]
    for args in ([], ["one", "two"]):
        with pytest.raises(SystemExit):
            exchange_worker.main(args)
    monkeypatch.setattr(sys, "argv", ["worker", str(workspace)])
    exchange_worker.main()
