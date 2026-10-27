"""Pinned selection, real work, exact typed oracles and pre-write packet rejection."""

from dataclasses import replace
import base64
import importlib.machinery
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import daggerml as d
from daggerml import exchange as ex, local, transfer
from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

ROOT = Path(__file__).resolve().parents[2]
ADD = (ROOT / "examples/local_add.py").read_bytes()


@pytest.fixture
def exchange_runtime(tmp_path, monkeypatch):
    package = tmp_path / "runtime" / "daggerml"
    package.mkdir(parents=True)
    for name in ("__init__.py", "local.py", "transfer.py", "exchange.py"):
        shutil.copyfile(ROOT / "python/daggerml/daggerml" / name, package / name)
    extension = Path(d._core.__file__)
    assert any(
        str(extension).endswith(s) for s in importlib.machinery.EXTENSION_SUFFIXES
    )
    shutil.copyfile(extension, package / extension.name)
    monkeypatch.setenv("PYTHONPATH", str(package.parent))
    return package.parent


def literal(tx, value):
    return tx.put_literal(tx.put_datum(value))


def initialize(path, source=ADD, extra=None):
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        left, right = literal(tx, 4), literal(tx, 7)
        inputs = tx.put_dag(root=left, bindings={"left": left, "right": right})
        binding = local.put_local_binding(
            tx, source=source, interpreter=sys.executable, timeout_ms=10000
        )
        tree = {
            "binding": binding,
            "inputs": inputs,
            "keep": tx.put_dag(root=literal(tx, "retained")),
        }
        if extra is not None:
            tree["large"] = tx.put_dag(root=literal(tx, extra))
        commit = tx.put_commit(tx.put_tree(tree))
        other = tx.put_commit(
            tx.put_tree({"sentinel": tx.put_dag(root=literal(tx, "branch-only"))})
        )
        tx.create_ref("main", commit)
        tx.create_ref("sentinel", other)
    return commit, binding, inputs, other


def prepare(path, workspace, commit):
    return ex.prepare_exchange(
        path,
        commit=commit,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add-i64",
        worker_ref="work",
        workspace=workspace,
    )


@pytest.fixture
def job(tmp_path, exchange_runtime):
    path, workspace = tmp_path / "a", tmp_path / "workspace"
    state = initialize(path)
    spec = prepare(path, workspace, state[0])
    return path, workspace, spec, state


@pytest.fixture
def completed(job):
    path, workspace, spec, state = job
    run = ex.execute_exchange(workspace)
    return path, workspace, spec, state, run


def typed_oracle(path, roots):
    """Independent breadth-first enumeration via public descriptions, not transfer edges."""
    result, pending = {}, [("commit", root) for root in roots]
    with d.Repository(path) as repo, repo.read() as tx:
        while pending:
            kind, oid = pending.pop(0)
            if (kind, oid) in result:
                continue
            result[kind, oid] = tx.get_record(kind, oid)
            if kind == "commit":
                c = tx.get_commit(oid)
                pending += [("tree", c.tree)] + [("commit", p) for p in c.parents]
            elif kind == "tree":
                pending += [("dag", v) for v in tx.get_tree(oid).values()]
            elif kind == "dag":
                dag = tx.get_dag(oid)
                pending += [("node", dag.root)] + [
                    ("node", n) for n in dag.bindings.values()
                ]
            elif kind == "node":
                n = tx.get_node(oid)
                pending += (
                    [("datum", n.datum)]
                    if isinstance(n, d.LiteralNode)
                    else [("dag", n.dag)]
                )
            else:
                datum = tx.get_datum(oid)
                if datum.kind in ("list", "set"):
                    pending += [("datum", n) for n in datum.value]
                elif datum.kind == "map":
                    pending += [("datum", n) for pair in datum.value for n in pair]
    return result


def bundle_oracle(file):
    return {
        (row["kind"], d.ObjectId.from_hex(row["id"])): base64.b64decode(row["record"])
        for row in json.loads(file.read_bytes())["objects"]
    }


def scalar(tx, dag, name):
    return tx.get_datum(tx.get_node(tx.lookup_node(dag, name)).datum).value


def nested(tx, dag, name):
    return tx.get_node(tx.lookup_node(dag, name)).dag


def tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def packet(workspace, run):
    """Caller copy, no B/input required by receive."""
    copy = workspace.with_name(workspace.name + "-packet")
    copy.mkdir()
    for name in ("job.json", "output.bundle", "completion.json"):
        shutil.copyfile(workspace / name, copy / name)
    return copy


def assert_main(path, state, main=None):
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("main") == (state[0] if main is None else main)
        assert tx.get_ref("sentinel") == state[3]


def test_two_fresh_workspaces_pin_offline_packet_exact_bytes(job, monkeypatch):
    path, workspace, spec, state = job
    original = typed_oracle(path, (state[0], state[3]))
    assert bundle_oracle(workspace / "input.bundle") == typed_oracle(path, (state[0],))
    offline = path.with_name("a-offline")
    path.rename(offline)
    try:
        first = ex.execute_exchange(workspace)
    finally:
        offline.rename(path)
    # Independent caller head movement, not an exchange action.
    with d.Repository(path) as repo, repo.write() as tx:
        newer = tx.put_commit(
            tx.put_tree({"later": tx.put_dag(root=literal(tx, 99))}),
            parents=(state[0],),
        )
        tx.update_ref("main", newer)
    workspace2 = workspace.with_name("second")
    spec2 = prepare(path, workspace2, state[0])
    second = ex.execute_exchange(workspace2)
    assert (
        spec.token != spec2.token
        and spec.binding == spec2.binding
        and spec.inputs == spec2.inputs
    )
    assert (
        first.request_id != second.request_id and first.attempt_id != second.attempt_id
    )
    assert first.result == second.result
    expected_bytes = typed_oracle(workspace / "worker.dml", (first.final_commit,))
    assert bundle_oracle(workspace / "output.bundle") == expected_bytes
    return_packet = packet(workspace, first)
    (workspace / "worker.dml").rename(workspace / "worker.offline")
    # Historical paths remain inert. Test-owned sentinels are not cleanup authority.
    scratch = Path(first.context.scratch)
    scratch.mkdir()
    sentinel = scratch / "retained"
    sentinel.write_bytes(b"not deletion authority")
    try:

        def no_process(*args, **kwargs):
            pytest.fail("receive/inspection must not execute")

        with monkeypatch.context() as guard:
            guard.setattr(subprocess, "Popen", no_process)
            received = ex.receive_exchange(
                path, workspace=return_packet, expected=spec, ref="trial-1"
            )
            assert (
                ex.receive_exchange(
                    path, workspace=return_packet, expected=spec, ref="trial-1"
                )
                == received
            )
            received2 = ex.receive_exchange(
                path, workspace=workspace2, expected=spec2, ref="trial-2"
            )
        assert received.result == received2.result == first.result
        assert (
            received.request == first.context.request
            and received.initial_attempt == first.context.attempt
        )
        assert (
            received.outcome == "success"
            and received.cleanup == "ok"
            and received.exit_code == 0
        )
        assert typed_oracle(path, (first.final_commit,)) == expected_bytes
        with d.Repository(path) as repo, repo.read() as tx:
            for key, raw in original.items():
                assert tx.get_record(*key) == raw
            assert tx.get_ref("trial-1") == first.final_commit
            assert tx.get_commit(first.final_commit).parents == (
                first.context.pre_dispatch,
                tx.get_commit(first.final_commit).parents[1],
            )
            assert scalar(tx, received.result, "result") == 11
            assert "status" not in tx.get_dag(received.initial_attempt).bindings
            for ref in (
                "work",
                "request-" + first.request_id,
                first.context.publication_ref,
            ):
                with pytest.raises(d.NotFoundError):
                    tx.get_ref(ref)
        assert sentinel.read_bytes() == b"not deletion authority"
        assert_main(path, state, newer)
        with pytest.raises(ex.ExchangeError):
            ex.execute_exchange(workspace)
    finally:
        shutil.rmtree(scratch)


@pytest.mark.parametrize(
    "source,reason,evidence",
    [
        (b"raise RuntimeError('expected')", "child-exit", False),
        (b"pass", "missing-publication", False),
        (ADD + b"\nraise RuntimeError('after')", "child-exit", True),
    ],
    ids=("nonzero", "no-publication", "evidence"),
)
def test_recorded_failure_is_returnable(
    tmp_path, exchange_runtime, source, reason, evidence
):
    path, workspace = tmp_path / "a", tmp_path / "work"
    state = initialize(path, source)
    spec = prepare(path, workspace, state[0])
    run = ex.execute_exchange(workspace)
    received = ex.receive_exchange(
        path, workspace=workspace, expected=spec, ref="failure"
    )
    assert run.outcome == received.outcome == "failure"
    assert received.result is None and received.reason == reason and received.detail
    assert (received.evidence is not None) == evidence
    assert_main(path, state)


def test_cleanup_failure_preserves_success(job, monkeypatch):
    path, workspace, spec, state = job
    original = shutil.rmtree

    def denied(path, *args, **kwargs):
        raise PermissionError("local scratch denied")

    with monkeypatch.context() as guard:
        guard.setattr(local.shutil, "rmtree", denied)
        run = ex.execute_exchange(workspace)
    try:
        received = ex.receive_exchange(
            path, workspace=workspace, expected=spec, ref="cleanup"
        )
        assert (
            received.outcome == "success"
            and received.cleanup == "failed"
            and received.result
        )
    finally:
        original(run.context.scratch)


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("commit", "main", TypeError),
        ("binding_name", 1, TypeError),
        ("binding_name", "missing", ex.ExchangeError),
        ("inputs_name", "missing", ex.ExchangeError),
        ("worker_ref", "bad/name", ex.ExchangeError),
        ("intent_uri", 1, TypeError),
        ("intent_uri", "HTTP://Example.com", ex.ExchangeError),
        ("intent_uri", "relative", d.DmlError),
        ("workspace", "", ex.ExchangeError),
    ],
    ids=(
        "commit-type",
        "name-type",
        "binding-missing",
        "inputs-missing",
        "ref-profile",
        "uri-type",
        "uri-canonical",
        "uri-relative",
        "empty-path",
    ),
)
def test_prepare_boundaries(job, field, value, error):
    path, workspace, spec, state = job
    kwargs = dict(
        commit=state[0],
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:x",
        worker_ref="work",
        workspace=workspace.with_name("new"),
    )
    kwargs[field] = value
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(error):
        ex.prepare_exchange(path, **kwargs)
    assert (path / "data.mdb").read_bytes() == before


def test_existing_workspace_and_selection_types(job):
    path, workspace, spec, state = job
    with pytest.raises(FileExistsError):
        prepare(path, workspace, state[0])
    with pytest.raises(TypeError):
        replace(spec, inputs="hex")
    with pytest.raises(ex.ExchangeError):
        replace(spec, token="A" * 32)
    with pytest.raises(ex.ExchangeError):
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="bad/name")
    with pytest.raises(TypeError):
        ex.receive_exchange(path, workspace=workspace, expected=None, ref="trial")
    for value in (True, -1, 1, sys.maxsize + 1):
        with pytest.raises((TypeError, ex.ExchangeError)):
            ex.execute_exchange(workspace, map_size=value)
    assert not (workspace / "started").exists()


def change_json(path, **updates):
    document = json.loads(path.read_bytes())
    document.update(updates)
    path.write_text(json.dumps(document), encoding="utf-8")


@pytest.mark.parametrize(
    "mode",
    (
        "worker",
        "output",
        "completion",
        "started",
        "missing-input",
        "input-limit",
        "input-root",
        "selection",
    ),
)
def test_one_shot_bootstrap_failures(job, mode, monkeypatch):
    path, workspace, spec, state = job
    if mode in ("worker", "output", "completion", "started"):
        name = {
            "worker": "worker.dml",
            "output": "output.bundle",
            "completion": "completion.json",
            "started": "started",
        }[mode]
        (workspace / name).touch()
    elif mode == "missing-input":
        (workspace / "input.bundle").unlink()
    elif mode == "input-limit":
        monkeypatch.setattr(transfer, "MAX_BUNDLE_BYTES", 1)
    elif mode == "input-root":
        (workspace / "input.bundle").write_bytes(
            transfer.export_commit(path, commit=state[3])
        )
    else:
        change_json(workspace / "job.json", inputs=str(state[1]))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ex.ExchangeError, FileNotFoundError)):
        ex.execute_exchange(workspace)
    assert (path / "data.mdb").read_bytes() == before
    if mode not in ("worker", "output", "completion"):
        assert (workspace / "started").exists()
        with pytest.raises(ex.ExchangeError):
            ex.execute_exchange(workspace)


@pytest.mark.parametrize("file", ("job.json", "completion.json"))
@pytest.mark.parametrize(
    "data",
    (
        b"{}",
        b"[]",
        b'{"format":1}',
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{} {}",
        b"[" * 2000,
        b"x" * 8193,
    ),
    ids=(
        "empty",
        "array",
        "wrong-fields",
        "duplicate",
        "nan",
        "infinity",
        "utf8",
        "bom",
        "trailing",
        "deep",
        "oversize",
    ),
)
def test_strict_bounded_descriptor_rejection(completed, file, data):
    path, workspace, spec, state, run = completed
    (workspace / file).write_bytes(data)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="trial")
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize(
    "file,field,value",
    [
        ("job.json", "format", "wrong"),
        ("job.json", "commit", "A" * 32),
        ("job.json", "binding_name", "bad/name"),
        ("job.json", "token", "0" * 32),
        ("completion.json", "format", "wrong"),
        ("completion.json", "token", "0" * 32),
        ("completion.json", "commit", "0" * 32),
        ("completion.json", "final_commit", "0" * 32),
        ("completion.json", "pre_dispatch", "0" * 32),
        ("completion.json", "request_id", "wrong"),
        ("completion.json", "attempt_id", "wrong"),
    ],
    ids=(
        "job-format",
        "job-id",
        "job-name",
        "job-token",
        "receipt-format",
        "receipt-token",
        "receipt-base",
        "receipt-root",
        "receipt-pre",
        "receipt-request",
        "receipt-attempt",
    ),
)
def test_packet_fields_rejected_before_a(completed, file, field, value):
    path, workspace, spec, state, run = completed
    change_json(workspace / file, **{field: value})
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ex.ExchangeError, d.NotFoundError)):
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="trial")
    assert (path / "data.mdb").read_bytes() == before


def test_swapped_complete_identical_job_packet(job):
    path, workspace, spec, state = job
    second = workspace.with_name("second")
    spec2 = prepare(path, second, state[0])
    ex.execute_exchange(second)
    for name in ("output.bundle", "completion.json"):
        shutil.copyfile(second / name, workspace / name)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError, match="token"):
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="trial")
    assert (path / "data.mdb").read_bytes() == before
    assert spec2.token != spec.token


@given(st.text(alphabet="abcXYZ012._-", min_size=1, max_size=140))
def test_name_profile_property(name):
    valid = len(name) <= 128 and name[0] not in "._-"
    if valid:
        assert ex._name(name) == name
    else:
        with pytest.raises(ex.ExchangeError):
            ex._name(name)


@given(
    st.integers(min_value=-10000, max_value=10000),
    st.integers(min_value=-10000, max_value=10000),
)
def test_selection_identity_pin_property(tmp_path_factory, left, right):
    with tempfile.TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as directory:
        path = Path(directory) / "a"
        state = initialize(path)
        with d.Repository(path) as repo, repo.write() as tx:
            nodes = {"left": literal(tx, left), "right": literal(tx, right)}
            inputs = tx.put_dag(root=nodes["left"], bindings=nodes)
            selected = tree(tx, state[0])
            selected["inputs"] = inputs
            commit = tx.put_commit(tx.put_tree(selected), parents=(state[0],))
            tx.update_ref("main", state[3])
        spec = prepare(path, Path(directory) / "workspace", commit)
        assert spec.inputs == inputs and spec.commit == commit
        assert bundle_oracle(
            Path(directory) / "workspace/input.bundle"
        ) == typed_oracle(path, (commit,))


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    name=st.text(alphabet="abcXYZ012", min_size=1, max_size=25),
    repetitions=st.integers(1, 4),
)
def test_generated_repeat_receive_refs_are_nonexecuting(
    completed, name, repetitions, monkeypatch
):
    # Shared fixture is intentional: generated refs target the same immutable F;
    # reimport is the property, not fresh execution per Hypothesis example.
    path, workspace, spec, state, run = completed
    worker_bytes = (workspace / "worker.dml/data.mdb").read_bytes()
    with monkeypatch.context() as guard:
        guard.setattr(
            subprocess, "Popen", lambda *args, **kwargs: pytest.fail("no reexecution")
        )
        received = ex.receive_exchange(
            path, workspace=workspace, expected=spec, ref="r-" + name
        )
        for _ in range(repetitions):
            assert (
                ex.receive_exchange(
                    path, workspace=workspace, expected=spec, ref="r-" + name
                )
                == received
            )
    assert received.commit == run.final_commit and received.attempt_id == run.attempt_id
    assert (workspace / "worker.dml/data.mdb").read_bytes() == worker_bytes
    assert_main(path, state)
