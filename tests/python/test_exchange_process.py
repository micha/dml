"""Real B/A map-full, persistence/file faults and bounded process-loss oracles."""

from contextlib import contextmanager
from dataclasses import asdict
import errno
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

from test_binding_failures import core
from test_exchange import (
    ROOT,
    ADD,
    job,
    completed,
    exchange_runtime,
    initialize,
    prepare,
    typed_oracle,
    bundle_oracle,
    literal,
    scalar,
    tree,
    assert_main,
)
from test_records_hypothesis import run_driver


def expected_file(directory, spec):
    file = directory / "caller-expected.json"
    values = asdict(spec)
    for key in ("commit", "binding", "inputs"):
        values[key] = str(getattr(spec, key))
    file.write_text(json.dumps(values), encoding="utf-8")
    return file


def terminated_at_barrier(path, workspace, spec, stage):
    expected = expected_file(workspace.parent, spec)
    marker = workspace.parent / (stage + "-barrier")
    stderr = workspace.parent / (stage + "-stderr")
    with open(stderr, "wb") as errors:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "tests/python/exchange_interruption_parent.py"),
                str(path),
                str(workspace),
                str(expected),
                str(marker),
                stage,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            deadline = time.monotonic() + 20
            while (
                not marker.exists()
                and process.poll() is None
                and time.monotonic() < deadline
            ):
                time.sleep(0.02)
            assert marker.exists(), stderr.read_text(encoding="utf-8", errors="replace")
            process.terminate()
            process.wait(timeout=10)
            assert process.returncode != 0
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


def fresh_state(path, baseline, returned, present):
    # Independent oracle file, finite reader, all exact typed bytes/ref checks.
    import base64

    manifest = path.parent / "fresh-oracle.json"
    manifest.write_text(
        json.dumps(
            {
                "baseline": [
                    [k, str(oid), base64.b64encode(raw).decode()]
                    for (k, oid), raw in baseline.items()
                ],
                "returned": [
                    [k, str(oid), base64.b64encode(raw).decode()]
                    for (k, oid), raw in returned.items()
                ],
            }
        ),
        encoding="utf-8",
    )
    code = """import base64,json,sys,daggerml as d
path,file,present=sys.argv[1:]; present=present=='yes'
data=json.load(open(file,encoding='utf-8'))
with d.Repository(path) as r,r.read() as t:
 for kind,oid,raw in data['baseline']:
  assert t.get_record(kind,d.ObjectId.from_hex(oid))==base64.b64decode(raw)
 baseline={(k,oid) for k,oid,raw in data['baseline']}
 for kind,oid,raw in data['returned']:
  try: actual=t.get_record(kind,d.ObjectId.from_hex(oid))
  except d.NotFoundError: assert not present and (kind,oid) not in baseline
  else: assert (present or (kind,oid) in baseline) and actual==base64.b64decode(raw)
 try: target=t.get_ref('received')
 except d.NotFoundError: assert not present
 else: assert present and str(target)==data['returned'][0][1]
print('fresh-state-ok')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(path),
            str(manifest),
            "yes" if present else "no",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fresh-state-ok"


@pytest.mark.parametrize("stage", ("unknown", "worker-done", "caller"))
def test_worker_and_caller_loss_knowledge_boundaries(job, stage):
    path, workspace, spec, state = job
    before = (path / "data.mdb").read_bytes()
    terminated_at_barrier(path, workspace, spec, stage)
    assert (path / "data.mdb").read_bytes() == before
    assert_main(path, state)
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        head = tx.get_ref("work")
        selected = tree(tx, head)
        attempt = next(
            dag for name, dag in selected.items() if name.startswith("attempt-")
        )
        if stage == "unknown":
            assert "status" not in tx.get_dag(attempt).bindings
            scratch = scalar(tx, attempt, "scratch")
        else:
            assert scalar(tx, attempt, "status") == "done"
    assert (workspace / "completion.json").exists() == (stage == "caller")
    with pytest.raises(ex.ExchangeError):
        ex.execute_exchange(workspace)
    if stage == "caller":
        received = ex.receive_exchange(
            path, workspace=workspace, expected=spec, ref="received"
        )
        assert received.outcome == "success"
    elif stage == "unknown":
        # Private barrier guarantees no child was spawned; terminated worker reaped.
        shutil.rmtree(scratch)


@pytest.mark.parametrize("stage", ("receive-pre", "receive-post"))
def test_loss_around_actual_a_storage_commit(completed, stage):
    path, workspace, spec, state, run = completed
    baseline = typed_oracle(path, (state[0], state[3]))
    returned = typed_oracle(workspace / "worker.dml", (run.final_commit,))
    assert sum(key not in baseline for key in returned) > 3
    terminated_at_barrier(path, workspace, spec, stage)
    fresh_state(path, baseline, returned, stage == "receive-post")
    assert_main(path, state)
    first = ex.receive_exchange(
        path, workspace=workspace, expected=spec, ref="received"
    )
    assert (
        ex.receive_exchange(path, workspace=workspace, expected=spec, ref="received")
        == first
    )
    fresh_state(path, baseline, returned, True)


@pytest.mark.parametrize(
    "stage",
    (
        "prepare-input",
        "prepare-job",
        "worker-output",
        "worker-receipt",
        "validation-cleanup",
    ),
)
def test_meaningful_file_failures_retain_workspaces(job, stage, monkeypatch):
    path, workspace, spec, state = job
    before = (path / "data.mdb").read_bytes()
    if stage.startswith("prepare"):
        workspace = workspace.with_name("file-failure")
        if stage == "prepare-input":
            original = ex._write_document
            # Fail actual exclusive input file open, not descriptor parser.
            import builtins

            opening = builtins.open

            def fail(file, *args, **kwargs):
                if Path(file).name == "input.bundle":
                    raise PermissionError("input denied")
                return opening(file, *args, **kwargs)

            monkeypatch.setattr(builtins, "open", fail)
        else:
            monkeypatch.setattr(
                ex.os,
                "replace",
                lambda *args: (_ for _ in ()).throw(PermissionError("job denied")),
            )
        with pytest.raises(PermissionError):
            prepare(path, workspace, state[0])
        assert workspace.exists() and not (workspace / "job.json").exists()
    elif stage.startswith("worker"):
        if stage == "worker-output":
            import builtins

            opening = builtins.open

            def fail(file, *args, **kwargs):
                if Path(file).name == "output.bundle":
                    raise PermissionError("output denied")
                return opening(file, *args, **kwargs)

            monkeypatch.setattr(builtins, "open", fail)
        else:
            monkeypatch.setattr(
                ex.os,
                "replace",
                lambda *args: (_ for _ in ()).throw(PermissionError("receipt denied")),
            )
        with pytest.raises(PermissionError):
            ex.execute_exchange(workspace)
        assert not (workspace / "completion.json").exists()
        with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
            attempt = next(
                v
                for k, v in tree(tx, tx.get_ref("work")).items()
                if k.startswith("attempt-")
            )
            assert scalar(tx, attempt, "status") == "done"
    else:
        ex.execute_exchange(workspace)
        original = shutil.rmtree
        remaining = []

        def denied(path, *args, **kwargs):
            remaining.append(path)
            raise PermissionError("validation cleanup denied")

        with monkeypatch.context() as guard:
            guard.setattr(ex.shutil, "rmtree", denied)
            with pytest.raises(PermissionError):
                ex.receive_exchange(
                    path, workspace=workspace, expected=spec, ref="received"
                )
        assert len(remaining) == 1 and Path(remaining[0]).exists()
        original(remaining[0])
    assert (path / "data.mdb").read_bytes() == before
    assert workspace.exists()


def test_real_b_import_map_full_before_dispatch(
    tmp_path, exchange_runtime, monkeypatch
):
    path, workspace = tmp_path / "a", tmp_path / "work"
    state = initialize(path, extra=b"x" * 2097152)
    spec = prepare(path, workspace, state[0])
    monkeypatch.setattr(
        local,
        "run_step",
        lambda *args, **kwargs: pytest.fail("no dispatch after failed import"),
    )
    with pytest.raises(d.MapFullError):
        ex.execute_exchange(workspace, map_size=1048576)
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("work")
    with pytest.raises(ex.ExchangeError):
        ex.execute_exchange(workspace)
    assert_main(path, state)


def test_post_computation_actual_profile_overflow(job, monkeypatch):
    path, workspace, spec, state = job
    source = (
        ADD
        + b"""\nwith Repository(context.repository_path) as repo, repo.write() as tx:
    pass
"""
    )
    # Scale owning transfer packed-total limit to input size. Full completion adds
    # genuinely new records and exceeds it; this is not a 16 MiB stress claim.
    baseline = sum(len(raw) for raw in typed_oracle(path, (state[0],)).values())
    monkeypatch.setattr(transfer, "MAX_PACKED_BYTES", baseline)
    with pytest.raises(transfer.TransferError, match="total packed"):
        ex.execute_exchange(workspace)
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        attempt = next(
            v
            for k, v in tree(tx, tx.get_ref("work")).items()
            if k.startswith("attempt-")
        )
        assert scalar(tx, attempt, "status") == "done"
    assert not (workspace / "completion.json").exists()
    assert_main(path, state)


@contextmanager
def track_new_puts(path, baseline, commit_fault=None):
    """Private successful actual-A puts, excluding isolated validation import."""
    from unittest.mock import patch

    original_import, original_put = transfer.import_commit, d.Transaction.put_record
    active, successful = False, []

    def importing(repository_path, *args, **kwargs):
        nonlocal active
        active = Path(repository_path) == path
        if active and commit_fault is not None:
            commit_fault.native_fault(15, 1, errno.EIO)
        try:
            return original_import(repository_path, *args, **kwargs)
        finally:
            active = False
            if commit_fault is not None:
                commit_fault.native_fault(0, 0, 0)

    def putting(self, kind, record):
        oid = original_put(self, kind, record)
        if active and (kind, oid) not in baseline:
            assert self.get_record(kind, oid) == record
            successful.append((kind, oid))
        return oid

    with patch.object(transfer, "import_commit", importing), patch.object(
        d.Transaction, "put_record", putting
    ):
        yield successful


@pytest.mark.parametrize("fault", ("ref", "malformed-ref", "commit"))
def test_late_a_fault_rolls_back_genuinely_new_records(completed, core, fault):
    path, workspace, spec, state, run = completed
    baseline = typed_oracle(path, (state[0], state[3]))
    returned = typed_oracle(workspace / "worker.dml", (run.final_commit,))
    if fault == "ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("trial", state[3])
    elif fault == "malformed-ref":
        run_driver("raw-write", str(path), "refs/heads/trial", data=b"\0")
    # Whole file equality includes raw different-target/malformed ref values.
    raw_before = (path / "data.mdb").read_bytes()
    with track_new_puts(
        path, baseline, core if fault == "commit" else None
    ) as successful:
        with pytest.raises((transfer.RefConflictError, d.DmlError)):
            ex.receive_exchange(path, workspace=workspace, expected=spec, ref="trial")
    assert successful, "late fault must follow a successful genuinely new actual-A put"
    assert (path / "data.mdb").read_bytes() == raw_before
    if fault == "ref":
        with d.Repository(path) as repo, repo.read() as tx:
            assert tx.get_ref("trial") == state[3]
    if fault == "malformed-ref":
        with d.Repository(path) as repo, repo.read() as tx:
            with pytest.raises(d.IntegrityError):
                tx.get_ref("trial")
    fresh_state(path, baseline, returned, False)
    assert_main(path, state)
    assert (workspace / "worker.dml").exists()


def test_real_late_a_map_full_whole_import_retry(tmp_path, exchange_runtime):
    path, workspace = tmp_path / "a", tmp_path / "work"
    # Base is small. A truly new >1 MiB output exists only in B.
    source = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 early=t.put_literal(t.put_datum('new output prefix'))
 big=t.put_literal(t.put_datum(b'x'*2097152))
 publish_result(t,c,t.put_dag(root=early,bindings={'big':big}))
"""
    state = initialize(path, source)
    spec = prepare(path, workspace, state[0])
    run = ex.execute_exchange(workspace)
    baseline = typed_oracle(path, (state[0], state[3]))
    returned = typed_oracle(workspace / "worker.dml", (run.final_commit,))
    with track_new_puts(path, baseline) as successful:
        with pytest.raises(d.MapFullError):
            ex.receive_exchange(
                path,
                workspace=workspace,
                expected=spec,
                ref="received",
                map_size=1048576,
            )
    assert (
        successful
    ), "real map-full must follow a successful genuinely new actual-A put"
    fresh_state(path, baseline, returned, False)
    assert_main(path, state)
    result = ex.receive_exchange(
        path, workspace=workspace, expected=spec, ref="received", map_size=8388608
    )
    assert result.commit == run.final_commit
    fresh_state(path, baseline, returned, True)


def test_preparation_reached_unrelated_parent_corruption(job):
    path, workspace, spec, state = job
    # A branch-only sentinel becomes an actual parent: selection itself remains good.
    with d.Repository(path) as repo, repo.write() as tx:
        selected = tx.put_commit(tx.get_commit(state[0]).tree, parents=(state[3],))
    run_driver("raw-delete", str(path), "objects/commits/" + str(state[3]))
    with pytest.raises(d.NotFoundError):
        prepare(path, workspace.with_name("corrupt"), selected)
    assert not workspace.with_name("corrupt").exists()


def test_actual_post_computation_record_profile_overflow(tmp_path, exchange_runtime):
    path, workspace = tmp_path / "a", tmp_path / "work"
    source = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 n=t.put_literal(t.put_datum(b'x'*(4*1024*1024+1)))
 publish_result(t,c,t.put_dag(root=n))
"""
    state = initialize(path, source)
    spec = prepare(path, workspace, state[0])
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(transfer.TransferError, match="packed record exceeds"):
        ex.execute_exchange(workspace)
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        attempt = next(
            v
            for k, v in tree(tx, tx.get_ref("work")).items()
            if k.startswith("attempt-")
        )
        assert scalar(tx, attempt, "status") == "done"
        outcome = tx.get_node(tx.lookup_node(attempt, "outcome")).dag
        assert scalar(tx, outcome, "role") == "local-success-v1"
    assert not (workspace / "completion.json").exists()
    assert (path / "data.mdb").read_bytes() == before
    with pytest.raises(ex.ExchangeError):
        ex.execute_exchange(workspace)


def test_descriptor_generation_bound_and_worker_ref_conflict(job, monkeypatch):
    path, workspace, spec, state = job
    with pytest.raises(ex.ExchangeError):
        ex._write_document(workspace / "large.json", {"large": "x" * 8192})
    original = transfer.import_commit

    def moved(repository_path, *args, **kwargs):
        result = original(repository_path, *args, **kwargs)
        with d.Repository(repository_path) as repo, repo.write() as tx:
            other = tx.put_commit(tx.put_tree({}))
            tx.update_ref("work", other)
        return result

    monkeypatch.setattr(transfer, "import_commit", moved)
    with pytest.raises(ex.ExchangeError, match="worker ref"):
        ex.execute_exchange(workspace)
