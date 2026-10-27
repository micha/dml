"""Meaningful role, conflict, storage and deterministic interruption regressions."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import daggerml as dml
from daggerml import local
import pytest

from test_local_execution import ADD, ROOT, assert_initial, bind, prepare, run, runtime, scalar, state, subdag


@pytest.mark.parametrize("phase", ["prepared", "published"])
def test_parent_loss_unknown_and_explicit_retry(state, tmp_path, phase):
    barrier = tmp_path / "barrier.json"
    parent = subprocess.Popen([sys.executable, str(ROOT / "tests/python/local_interruption_parent.py"),
                               str(state[0]), str(state[2]), str(state[1]), phase, str(barrier)],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    context = None
    try:
        deadline = time.monotonic() + 20
        while not barrier.exists():
            assert parent.poll() is None, "parent exited before barrier"
            assert time.monotonic() < deadline, "finite barrier deadline expired"
            time.sleep(0.01)
        # File may be visible before all bytes have been written. The private fixture
        # uses atomic rename below; this read is not a scheduling-dependent oracle.
        fields = json.loads(barrier.read_text(encoding="utf-8"))
        for name in ("pre_dispatch", "request", "attempt", "binding", "inputs"):
            fields[name] = dml.ObjectId.from_hex(fields[name])
        context = local.LocalContext(**fields)
        parent.terminate()
        parent.communicate(timeout=10)
        with dml.Repository(state[0]) as repo, repo.read() as tx:
            assert tx.get_ref("main") == context.pre_dispatch
            assert_initial(tx, context)
            saved = tx.get_record("dag", context.attempt)
            publication = tx.get_ref(context.publication_ref)
            if phase == "prepared":
                assert publication == context.pre_dispatch
                assert not (Path(context.scratch) / "entry.py").exists()
            else:
                assert publication != context.pre_dispatch
                assert scalar(tx, local._publication(tx, context, publication), "result") == 11
        # Fresh-process low-level inspection neither infers failure nor finalizes.
        probe = subprocess.run([sys.executable, "-c", "import daggerml as d, sys;\nwith d.Repository(sys.argv[1]) as r, r.read() as t:\n print(','.join(t.get_dag(d.ObjectId.from_hex(sys.argv[2])).bindings))",
                                str(state[0]), str(context.attempt)], capture_output=True, text=True,
                               timeout=20, check=True)
        assert "status" not in probe.stdout and "outcome" not in probe.stdout
        retried = local.retry_step(state[0], head_ref="main", request=context.request)
        assert retried.request_id == context.request_id and retried.attempt_id != context.attempt_id
        assert retried.context.binding == context.binding and retried.context.inputs == context.inputs
        with dml.Repository(state[0]) as repo, repo.read() as tx:
            assert tx.get_record("dag", context.attempt) == saved
            assert local._tree(tx, retried.final_commit)["attempt-" + context.attempt_id] == context.attempt
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.communicate(timeout=10)
        if context is not None and Path(context.scratch).exists():
            shutil.rmtree(context.scratch)
        # Only fixture-owned directories in this test's temporary root.
        for scratch in tmp_path.glob("dml-local-*"):
            shutil.rmtree(scratch)


def test_preparation_write_and_commit_failure_never_launch(state, monkeypatch):
    original_create = dml.Transaction.create_ref
    original_commit = dml.Transaction.commit
    for failure in ("create", "commit"):
        launched = []
        monkeypatch.setattr(local, "_execute", lambda *a: launched.append(a))
        if failure == "create":
            def fail_create(tx, name, commit):
                if name.startswith("attempt-"):
                    raise dml.DmlError("allocation_failed", detail="injected ref creation")
                return original_create(tx, name, commit)
            monkeypatch.setattr(dml.Transaction, "create_ref", fail_create)
        else:
            monkeypatch.setattr(dml.Transaction, "create_ref", original_create)
            def fail_commit(tx):
                tx.abort()
                raise dml.DmlError("io_error", detail="injected storage commit")
            monkeypatch.setattr(dml.Transaction, "commit", fail_commit)
        with pytest.raises(local.LocalExecutionError) as error:
            run(state)
        assert error.value.occurrence is None and not launched
        monkeypatch.setattr(dml.Transaction, "commit", original_commit)
        with dml.Repository(state[0]) as repo, repo.read() as tx:
            assert tx.get_ref("main") == state[3]
            assert local._tree(tx, state[3]) == {"keep": state[1]}
        assert not list(state[0].parent.glob("dml-local-*"))


def test_collision_retry_and_limit(state, monkeypatch):
    q, a = "q-" + "1"*32, "a-" + "1"*32
    with dml.Repository(state[0]) as repo, repo.write() as tx:
        tx.create_ref("request-" + q, state[3])
        tx.create_ref("attempt-" + a, state[3])
    original = local._new_id
    calls = []
    def collide_once(prefix):
        calls.append(prefix)
        return (q if prefix == "q" else a) if len(calls) <= 2 else original(prefix)
    monkeypatch.setattr(local, "_new_id", collide_once)
    assert run(state).outcome == "success"
    monkeypatch.setattr(local, "_new_id", lambda prefix: q if prefix == "q" else a)
    with pytest.raises(local.LocalExecutionError, match="collision limit") as error:
        run(state)
    assert error.value.occurrence is None
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert tx.get_ref("request-" + q) == state[3]
        assert tx.get_ref("attempt-" + a) == state[3]


def test_completion_abort_and_head_conflict_preserve_child(state, monkeypatch):
    original = local._finalize
    for mode in ("storage", "head"):
        def fail(context, head, observation, cleanup):
            with dml.Repository(state[0]) as repo, repo.write() as tx:
                if mode == "head":
                    tx.update_ref("main", state[3])
            if mode == "storage":
                original_commit = dml.Transaction.commit
                def abort_commit(tx):
                    tx.abort()
                    raise dml.MapFullError("map_full", detail="completion injected")
                monkeypatch.setattr(dml.Transaction, "commit", abort_commit)
                try:
                    return original(context, head, observation, cleanup)
                finally:
                    monkeypatch.setattr(dml.Transaction, "commit", original_commit)
            return original(context, head, observation, cleanup)
        monkeypatch.setattr(local, "_finalize", fail)
        with pytest.raises(local.LocalExecutionError) as error:
            run(state)
        context = error.value.occurrence
        assert context is not None
        with dml.Repository(state[0]) as repo, repo.read() as tx:
            assert_initial(tx, context)
            assert tx.get_ref("main") == (context.pre_dispatch if mode == "storage" else state[3])
            target = tx.get_ref(context.publication_ref)
            assert target != context.pre_dispatch
            assert scalar(tx, local._publication(tx, context, target), "result") == 11


def test_child_write_abort_is_not_publication(state):
    source = ADD.replace(b"    publish_result(tx, context, result)",
                         b"    publish_result(tx, context, result)\n    tx.abort()")
    result = run(bind(state, source))
    assert result.outcome == "failure"
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert tx.get_ref(result.context.publication_ref) == result.context.pre_dispatch
        assert scalar(tx, subdag(tx, result.final_attempt, "outcome"), "reason") == "missing-publication"


@pytest.mark.parametrize("mode", ["attempt", "role", "type", "parents", "tree", "bare"])
def test_invalid_publication_rejected(state, monkeypatch, mode):
    original = local._execute
    def malicious(context, *args):
        observed = original(context, *args)
        with dml.Repository(state[0]) as repo, repo.write() as tx:
            target = tx.get_ref(context.publication_ref)
            tree = local._tree(tx, context.pre_dispatch)
            if mode == "bare":
                tx.update_ref(context.publication_ref, context.pre_dispatch)
                return observed
            result = local._publication(tx, context, target)
            role = "wrong-role" if mode == "role" else "local-publication-v1"
            root = "a-" + "0"*32 if mode == "attempt" else context.attempt_id
            if mode == "type":
                publication = local._record(tx, root, {"role": role, "result": 11})
            else:
                publication = local._record(tx, root, {"role": role}, (("result", result),))
            tree["publication-" + context.attempt_id] = publication
            if mode == "tree":
                tree.pop("keep")
            commit = tx.put_commit(tx.put_tree(tree), parents=() if mode == "parents" else (context.pre_dispatch,))
            tx.update_ref(context.publication_ref, commit)
        return observed
    monkeypatch.setattr(local, "_execute", malicious)
    result = run(state)
    assert result.outcome == "failure" and result.result is None and result.evidence is None
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert scalar(tx, subdag(tx, result.final_attempt, "outcome"), "reason") == ("missing-publication" if mode == "bare" else "invalid-publication")
        assert tx.get_commit(result.final_commit).parents == (result.context.pre_dispatch,)
        assert local._tree(tx, result.final_commit)["keep"] == state[1]


def test_shutdown_escalation_and_unreaped_is_unknown(state, monkeypatch):
    events = []
    class Process:
        returncode = None
        def terminate(self): events.append("terminate")
        def kill(self): events.append("kill")
        def wait(self, timeout):
            events.append("wait")
            if events.count("wait") == 1:
                raise subprocess.TimeoutExpired("fixture", timeout)
            self.returncode = -9
        def poll(self): return self.returncode
    process = Process()
    local._shutdown(process)
    assert events == ["terminate", "wait", "kill", "wait"]
    class Unreaped(Process):
        def wait(self, timeout): raise subprocess.TimeoutExpired("fixture", timeout)
    monkeypatch.setattr(local.subprocess, "Popen", lambda *a, **k: Unreaped())
    with pytest.raises(local.LocalExecutionError) as error:
        run(state)
    context = error.value.occurrence
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert tx.get_ref("main") == context.pre_dispatch
        assert_initial(tx, context)


def test_setup_io_failure_records_launch_and_postlaunch_io_is_unknown(state, monkeypatch):
    original = Path.write_bytes
    monkeypatch.setattr(Path, "write_bytes", lambda *a: (_ for _ in ()).throw(OSError("scratch write failed")))
    result = run(state)
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert scalar(tx, subdag(tx, result.final_attempt, "outcome"), "reason") == "launch"
    monkeypatch.setattr(Path, "write_bytes", original)
    monkeypatch.setattr(local, "_diagnostic", lambda *a: (_ for _ in ()).throw(OSError("diagnostic read failed")))
    with pytest.raises(local.LocalExecutionError) as error:
        run(state)
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert_initial(tx, error.value.occurrence)


def test_exception_cleanup_preserves_inspectable_ids_and_interrupt(state, monkeypatch):
    original_cleanup = local._cleanup
    def broken(*a): raise RuntimeError("private dispatch failure")
    monkeypatch.setattr(local, "_execute", broken)
    monkeypatch.setattr(local, "_cleanup", lambda *a: ("failed", "private cleanup failed"))
    with pytest.raises(local.LocalExecutionError, match="cleanup failed") as error:
        run(state)
    context = error.value.occurrence
    original_cleanup(context.scratch)
    monkeypatch.setattr(local, "_cleanup", original_cleanup)
    def interrupt(*a): raise KeyboardInterrupt()
    monkeypatch.setattr(local, "_execute", interrupt)
    with pytest.raises(KeyboardInterrupt):
        run(state)
    assert not list(state[0].parent.glob("dml-local-*"))


def test_argument_boundaries():
    for path in ("", "x\0", b"\xff"):
        with pytest.raises((ValueError, UnicodeError)):
            local._path(path)
    with pytest.raises(TypeError):
        local.run_step("absent", head_ref="main", intent_uri=1, binding=None, inputs=None)
    with pytest.raises(TypeError):
        local.run_step("absent", head_ref="main", intent_uri="urn:x", binding=None, inputs=None)
    with pytest.raises(TypeError):
        local.retry_step("absent", head_ref="main", request=None)
    for value in ("q-" + "a"*32, "a-" + "A"*32, None):
        with pytest.raises(local.ProtocolError):
            local._occurrence(value, "a")
