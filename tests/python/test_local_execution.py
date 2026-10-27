"""Public local execution acceptance and private deterministic boundary fixtures."""
from dataclasses import replace
import importlib.machinery
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

import daggerml as dml
from daggerml import local
from hypothesis import given, strategies as st
import pytest

ROOT = Path(__file__).resolve().parents[2]
ADD = (ROOT / "examples/local_add.py").read_bytes()


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    # The runner has no source/bootstrap hooks. Stage this exact source and the
    # current real extension in a normal importable package for child processes.
    package = tmp_path / "current runtime" / "daggerml"
    package.mkdir(parents=True)
    for name in ("__init__.py", "local.py"):
        shutil.copyfile(ROOT / "python/daggerml/daggerml" / name, package / name)
    extension = Path(dml._core.__file__)
    assert any(str(extension).endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES)
    shutil.copyfile(extension, package / extension.name)
    monkeypatch.setenv("PYTHONPATH", str(package.parent))
    provenance = subprocess.run([sys.executable, "-c", "import daggerml, daggerml._core; print(daggerml.__file__); print(daggerml._core.__file__)"],
                               cwd=tmp_path, capture_output=True, text=True, timeout=20, check=True)
    assert all(str(package) in line for line in provenance.stdout.splitlines())
    return package.parent


@pytest.fixture
def state(tmp_path, runtime):
    path = tmp_path / "repository with spaces"
    with dml.Repository(path, create=True) as repo, repo.write() as tx:
        nodes = {name: tx.put_literal(tx.put_datum(value)) for name, value in (("left", 4), ("right", 7))}
        inputs = tx.put_dag(root=nodes["left"], bindings=nodes)
        binding = local.put_local_binding(tx, source=ADD, interpreter=sys.executable, timeout_ms=10000)
        initial = tx.put_commit(tx.put_tree({"keep": inputs}))
        tx.create_ref("main", initial)
    return path, inputs, binding, initial


def run(state, **kwargs):
    path, inputs, binding, _ = state
    return local.run_step(path, head_ref="main", intent_uri="urn:example:add-i64", binding=binding,
                          inputs=inputs, scratch_dir=path.parent, **kwargs)


def bind(state, source, timeout=10000, interpreter=None):
    path = state[0]
    with dml.Repository(path) as repo, repo.write() as tx:
        binding = local.put_local_binding(tx, source=source, interpreter=interpreter or sys.executable,
                                         timeout_ms=timeout)
    return path, state[1], binding, state[3]


def scalar(tx, dag, name):
    return tx.get_datum(tx.get_node(tx.lookup_node(dag, name)).datum).value


def subdag(tx, dag, name):
    return tx.get_node(tx.lookup_node(dag, name)).dag


def assert_initial(tx, context):
    dag = tx.get_dag(context.attempt)
    assert set(dag.bindings) == {"role", "request", "publication-ref", "scratch"}
    assert tx.get_datum(tx.get_node(dag.root).datum).value == context.attempt_id
    assert subdag(tx, context.request, "binding") == context.binding
    assert subdag(tx, context.request, "inputs") == context.inputs


def test_two_real_launches_retry_and_history(state):
    first, second = run(state), run(state)
    retried = local.retry_step(state[0], head_ref="main", request=first.context.request)
    assert first.request_id != second.request_id
    assert len({first.attempt_id, second.attempt_id, retried.attempt_id}) == 3
    assert first.request_id == retried.request_id
    assert first.result == second.result == retried.result
    assert first.outcome == "success" and first.cleanup == "ok"
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert scalar(tx, first.result, "result") == 11
        original = tx.get_record("dag", first.context.attempt)
        for result in (first, second, retried):
            assert_initial(tx, result.context)
            assert tx.get_commit(result.final_commit).parents == (result.context.pre_dispatch,
                                                                 tx.get_ref(result.context.publication_ref))
            tree = local._tree(tx, result.final_commit)
            assert tree["keep"] == state[1]
            assert tree["attempt-" + result.attempt_id] == result.final_attempt
            assert scalar(tx, result.final_attempt, "status") == "done"
            outcome = subdag(tx, result.final_attempt, "outcome")
            assert subdag(tx, outcome, "result") == result.result
            assert scalar(tx, subdag(tx, result.final_attempt, "cleanup"), "disposition") == "ok"
        assert tx.get_record("dag", first.context.attempt) == original
    assert not Path(first.context.scratch).exists()
    assert second.result is not None
    # Inspection in a fresh ordinary reader, independent of LocalRun's return values.
    reader = subprocess.run([sys.executable, "-c", "import daggerml as d; import sys;\nwith d.Repository(sys.argv[1]) as r, r.read() as t:\n print(t.get_ref('main'))",
                             str(state[0])], capture_output=True, text=True, timeout=20, check=True)
    assert reader.stdout.strip() == str(retried.final_commit)


@pytest.mark.parametrize("source,reason", [(b"raise RuntimeError('expected')", "child-exit"),
                                           (b"pass", "missing-publication"),
                                           (b"import time; time.sleep(60)", "timeout")])
def test_real_failures(state, source, reason):
    result = run(bind(state, source, timeout=200 if reason == "timeout" else 10000))
    assert result.outcome == "failure" and result.result is None
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        outcome = subdag(tx, result.final_attempt, "outcome")
        assert scalar(tx, outcome, "reason") == reason
        assert scalar(tx, result.final_attempt, "status") == "done"
        assert subdag(tx, outcome, "stderr")


def test_publication_then_nonzero_preserves_evidence(state):
    result = run(bind(state, ADD + b"\nraise RuntimeError('after publication')\n"))
    assert result.result is None and result.evidence is not None
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert scalar(tx, result.evidence, "result") == 11
        assert len(tx.get_commit(result.final_commit).parents) == 2
        assert subdag(tx, subdag(tx, result.final_attempt, "outcome"), "evidence") == result.evidence


def test_launch_and_cleanup_failure(state, monkeypatch):
    result = run(bind(state, b"pass", interpreter=str(state[0].parent / "absent python")))
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        outcome = subdag(tx, result.final_attempt, "outcome")
        assert scalar(tx, outcome, "reason") == "launch"
        assert "stdout" not in tx.get_dag(outcome).bindings
    original = local.shutil.rmtree
    def fail(path):
        raise PermissionError("owned scratch cleanup denied")
    monkeypatch.setattr(local.shutil, "rmtree", fail)
    result = run(state)
    assert result.outcome == "success" and result.cleanup == "failed" and result.result
    monkeypatch.setattr(local.shutil, "rmtree", original)
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        cleanup = subdag(tx, result.final_attempt, "cleanup")
        assert scalar(tx, cleanup, "scratch") == result.context.scratch
    original(result.context.scratch)


def test_bytes_diagnostics_and_cli_preview(state):
    result = run(bind(state, ADD + b"\nimport os; os.write(1,b'\\xff\\x1b' * 5000); os.write(2,b'\\xfe' * 5001)\n"))
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        outcome = subdag(tx, result.final_attempt, "outcome")
        for name, count in (("stdout", 10000), ("stderr", 5001)):
            diagnostic = subdag(tx, outcome, name)
            dag = tx.get_dag(diagnostic)
            assert len(tx.get_datum(tx.get_node(dag.root).datum).value) == 4096
            assert scalar(tx, diagnostic, "byte-count") == count
            assert scalar(tx, diagnostic, "truncated") is True
    cli = ROOT / "build/check/dml"
    cli = Path(os.environ.get("DML_BIN", cli))
    for args in (("snapshot", "--ref", "main"), ("walk", str(result.final_attempt), "--limit", "100"),
                 ("log", "--ref", "main")):
        output = subprocess.run([str(cli), "--repo", str(state[0]), *args], capture_output=True,
                                timeout=20, check=True)
        assert b"\x1b" not in output.stdout


def prepare(state, tmp_path):
    scratch = tempfile.mkdtemp(dir=tmp_path)
    return local._prepare(str(state[0]), "main", scratch, intent_uri="urn:test:add", binding=state[2], inputs=state[1])


def test_child_helpers_pinned_context_and_atomic_publication(state, tmp_path):
    context = prepare(state, tmp_path)
    try:
        assert local.child_context([str(state[0]), str(context.pre_dispatch), context.attempt_id,
                                    context.publication_ref]) == context
        with pytest.raises(local.ProtocolError):
            local.child_context([])
        with dml.Repository(state[0]) as repo:
            with repo.write() as tx:
                node = tx.put_literal(tx.put_datum(11))
                result = tx.put_dag(root=node)
                with pytest.raises(local.ProtocolError):
                    local.publish_result(tx, replace(context, inputs=context.binding), result)
                published = local.publish_result(tx, context, result)
                tx.abort()
            with repo.read() as tx:
                assert tx.get_ref(context.publication_ref) == context.pre_dispatch
                with pytest.raises(dml.NotFoundError):
                    tx.get_commit(published)
            with repo.write() as tx:
                node = tx.put_literal(tx.put_datum(11))
                result = tx.put_dag(root=node)
                published = local.publish_result(tx, context, result)
            with repo.write() as tx:
                with pytest.raises(local.ConflictError):
                    local.publish_result(tx, context, result)
            with repo.read() as tx:
                assert local._publication(tx, context, published) == result
    finally:
        shutil.rmtree(context.scratch)


def test_captured_source_not_moving_file_and_overflow(state, tmp_path, monkeypatch):
    file = tmp_path / "original.py"
    file.write_bytes(ADD)
    captured = bind(state, file.read_bytes())
    file.write_bytes(b"raise RuntimeError('changed')")
    assert run(captured).outcome == "success"
    with dml.Repository(state[0]) as repo, repo.write() as tx:
        left = tx.put_literal(tx.put_datum(2**63-1))
        right = tx.put_literal(tx.put_datum(1))
        inputs = tx.put_dag(root=left, bindings={"left": left, "right": right})
    assert run((state[0], inputs, state[2], state[3])).outcome == "failure"


@given(st.binary(min_size=1, max_size=200), st.integers(min_value=1, max_value=3600000))
def test_binding_roundtrip_and_identity(tmp_path_factory, source, timeout):
    # Function-scoped fixture independence is explicit: every example owns a repository.
    with tempfile.TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as scratch:
        with dml.Repository(Path(scratch) / "repo", create=True) as repo, repo.write() as tx:
            first = local.put_local_binding(tx, source=source, interpreter=sys.executable, timeout_ms=timeout)
            second = local.put_local_binding(tx, source=source, interpreter=sys.executable, timeout_ms=timeout)
            assert first == second
            assert local._binding(tx, first) == (source, sys.executable, timeout)


@pytest.mark.parametrize("source,interpreter,timeout,error", [
    ("not bytes", sys.executable, 1, TypeError), (b"x", Path(sys.executable), 1, TypeError),
    (b"x", sys.executable, True, TypeError), (b"", sys.executable, 1, ValueError),
    (b"x" * (1024*1024+1), sys.executable, 1, ValueError), (b"x", "python", 1, ValueError),
    (b"x", sys.executable + "\0", 1, ValueError), (b"x", sys.executable + "e\u0301", 1, ValueError),
    (b"x", sys.executable, 0, ValueError),
    (b"x", sys.executable, 3600001, ValueError)])
def test_binding_bounds(source, interpreter, timeout, error):
    with pytest.raises(error):
        local.put_local_binding(None, source=source, interpreter=interpreter, timeout_ms=timeout)


def test_example_in_current_process(tmp_path, runtime, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["local_execution.py", str(tmp_path / "example")])
    runpy.run_path(str(ROOT / "examples/local_execution.py"), run_name="__main__")
    # Execute the maintained child in-process too, measuring its helpers/source.
    with dml.Repository(tmp_path / "example") as repo, repo.read() as tx:
        head = tx.get_ref("main")
        tree = local._tree(tx, head)
        request = next(dag for name, dag in tree.items() if name.startswith("request-") and
                       scalar(tx, dag, "intent") == "urn:example:add-i64")
    scratch = tempfile.mkdtemp(dir=tmp_path)
    try:
        context = local._prepare(str(tmp_path / "example"), "main", scratch, request=request)
        monkeypatch.setattr(sys, "argv", ["entry.py", context.repository_path, str(context.pre_dispatch),
                                         context.attempt_id, context.publication_ref])
        runpy.run_path(str(ROOT / "examples/local_add.py"), run_name="__main__")
    finally:
        shutil.rmtree(scratch)
