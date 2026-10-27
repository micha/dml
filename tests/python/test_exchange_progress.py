"""Independent immutable P/U/F validation, coherent discovery and late A rollback."""

from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess

import daggerml as d
from daggerml import exchange as ex, local, transfer
from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

from test_binding_failures import core
from test_exchange import (
    job,
    completed,
    exchange_runtime,
    initialize,
    prepare,
    literal,
    tree,
    scalar,
    typed_oracle,
    bundle_oracle,
    assert_main,
    change_json,
)
from test_exchange_process import track_new_puts, fresh_state
from test_exchange_records import clone, tamper, MODES


def handle(workspace, spec):
    return ex.ExchangeHandle(workspace, spec)


def observation(completed, phase="completion", name="packet"):
    path, workspace, spec, state, run = completed
    worker = workspace / "worker.dml"
    with d.Repository(worker) as repo, repo.write() as tx:
        if phase != "completion":
            tx.update_ref("work", run.context.pre_dispatch)
            if phase == "initial":
                tx.update_ref(run.context.publication_ref, run.context.pre_dispatch)
    packet = workspace.parent / name
    return ex.observe_exchange(handle(workspace, spec), packet=packet)


def observed_form(received):
    completion = received.completion
    return replace(
        received,
        ref=None,
        completion=(None if completion is None else replace(completion, ref=None)),
    )


def receive(completed, packet, ref="received"):
    path, workspace, spec, state, run = completed
    return ex.receive_observation(path, packet=packet, expected=spec, ref=ref)


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
def test_exact_selected_progress_offline_receive_and_no_execution(
    completed, phase, monkeypatch
):
    path, workspace, spec, state, run = completed
    original = typed_oracle(path, (state[0], state[3]))
    selected = observation(completed, phase)
    snapshot = selected.snapshot
    assert (
        snapshot.request_id == run.request_id and snapshot.attempt_id == run.attempt_id
    )
    assert snapshot.lifecycle == ("done" if phase == "completion" else "working")
    assert (snapshot.completion is not None) == (phase == "completion")
    assert (snapshot.result is not None) == (phase != "initial")
    expected = typed_oracle(workspace / "worker.dml", (snapshot.commit,))
    assert bundle_oracle(selected.packet / "snapshot.bundle") == expected
    with d.Repository(path) as repo, repo.write() as tx:
        newer = tx.put_commit(tx.put_tree({"later": state[1]}), parents=(state[0],))
        tx.update_ref("main", newer)
    copied = workspace.parent / "only-packet"
    shutil.copytree(selected.packet, copied)
    (workspace / "worker.dml").rename(workspace / "worker.offline")
    for name in ("input.bundle", "output.bundle", "completion.json"):
        (workspace / name).unlink()
    with monkeypatch.context() as guard:
        guard.setattr(
            subprocess, "Popen", lambda *a, **k: pytest.fail("must not execute")
        )
        got = receive(completed, copied)
        assert receive(completed, copied) == got
    assert observed_form(got) == snapshot
    assert typed_oracle(path, (snapshot.commit,)) == expected
    with d.Repository(path) as repo, repo.read() as tx:
        for key, raw in original.items():
            assert tx.get_record(*key) == raw
        for ref in ("work", "request-" + run.request_id, run.context.publication_ref):
            with pytest.raises(d.NotFoundError):
                tx.get_ref(ref)
    assert_main(path, state, newer)


def test_bootstrap_no_fake_occurrence_or_packet(job, monkeypatch):
    path, workspace, spec, state = job
    packet = workspace.parent / "packet"
    got = ex.observe_exchange(handle(workspace, spec), packet=packet)
    assert got == ex.ExchangeObservation("working", "bootstrap", None, None)
    assert not packet.exists()

    def before_dispatch(*args, **kwargs):
        raise RuntimeError("stop before recording")

    monkeypatch.setattr(local, "run_step", before_dispatch)
    with pytest.raises(RuntimeError):
        ex.execute_exchange(workspace)
    assert ex.observe_exchange(handle(workspace, spec), packet=packet) == got
    assert not packet.exists()


@pytest.mark.parametrize(
    "mode", ("malformed", "token", "base", "missing-b", "wrong-head", "bad-ref")
)
def test_ready_invalid_storage_is_error_not_bootstrap(completed, mode):
    path, workspace, spec, state, run = completed
    if mode == "malformed":
        (workspace / "worker-ready.json").write_bytes(b"{")
    elif mode in ("token", "base"):
        change_json(
            workspace / "worker-ready.json",
            **{("token" if mode == "token" else "commit"): "0" * 32},
        )
    elif mode == "missing-b":
        (workspace / "worker.dml").rename(workspace / "worker.offline")
    else:
        with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
            if mode == "wrong-head":
                tx.update_ref("work", tx.put_commit(tx.put_tree({})))
            else:
                tx.update_ref("work", run.context.pre_dispatch)
                tx.update_ref(run.context.publication_ref, spec.commit)
    with pytest.raises((ex.ExchangeError, d.DmlError)):
        ex.observe_exchange(handle(workspace, spec), packet=workspace.parent / "packet")


def test_readiness_io_failure_prevents_dispatch_and_retains_one_shot(job, monkeypatch):
    path, workspace, spec, state = job
    replacing = ex.os.replace

    def denied(source, target):
        if Path(target).name == "worker-ready.json":
            raise PermissionError("readiness denied")
        return replacing(source, target)

    monkeypatch.setattr(ex.os, "replace", denied)
    monkeypatch.setattr(local, "run_step", lambda *a, **k: pytest.fail("no dispatch"))
    with pytest.raises(PermissionError):
        ex.execute_exchange(workspace)
    assert (workspace / "started").exists() and (workspace / "worker.dml").exists()
    assert not (workspace / "worker-ready.json").exists()
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        assert tx.get_ref("work") == spec.commit
    assert (
        ex.observe_exchange(
            handle(workspace, spec), packet=workspace.parent / "packet"
        ).phase
        == "bootstrap"
    )
    with pytest.raises(ex.ExchangeError):
        ex.execute_exchange(workspace)


def test_preexisting_readiness_rejects_sync_before_started(job):
    path, workspace, spec, state = job
    (workspace / "worker-ready.json").touch()
    with pytest.raises(ex.ExchangeError):
        ex.execute_exchange(workspace)
    assert not (workspace / "started").exists()


def test_prior_requests_attempts_publications_in_c_are_preserved(completed):
    path, workspace, spec, state, first = completed
    # A second job starts from a real previous final C, not fake prefix entries.
    prior = ex.receive_exchange(path, workspace=workspace, expected=spec, ref="prior")
    second = workspace.parent / "second"
    spec2 = prepare(path, second, prior.commit)
    run2 = ex.execute_exchange(second)
    case = (path, second, spec2, state, run2)
    for phase in ("completion", "publication", "initial"):
        selected = observation(case, phase, "packet-" + phase)
        got = receive(case, selected.packet, "prior-" + phase)
        assert got.request_id == run2.request_id != first.request_id
        assert got.attempt_id == run2.attempt_id != first.attempt_id
        with d.Repository(path) as repo, repo.read() as tx:
            actual = tree(tx, got.commit)
            for name in (
                "request-" + first.request_id,
                "attempt-" + first.attempt_id,
                "publication-" + first.attempt_id,
            ):
                assert actual[name] == tree(tx, prior.commit)[name]


def test_coherent_read_transaction_and_pin_survive_ref_changes(completed, monkeypatch):
    path, workspace, spec, state, run = completed
    worker = workspace / "worker.dml"
    with d.Repository(worker) as repo, repo.write() as tx:
        tx.update_ref("work", run.context.pre_dispatch)
        tx.update_ref(run.context.publication_ref, run.context.pre_dispatch)
    publication_parent = _publication_parent(worker, run)
    original = d.Transaction.get_ref
    changed = []

    def read_ref(self, name):
        target = original(self, name)
        if name == "work" and not changed:
            changed.append(True)
            # Separate process changes BOTH refs after first read. The observation's
            # second ref read MUST still see the old P in its same LMDB snapshot.
            subprocess.run(
                [
                    __import__("sys").executable,
                    "-c",
                    """import sys,daggerml as d
with d.Repository(sys.argv[1]) as r,r.write() as t:
 t.update_ref('work',d.ObjectId.from_hex(sys.argv[2]))
 t.update_ref(sys.argv[3],d.ObjectId.from_hex(sys.argv[4]))
""",
                    str(worker),
                    str(run.final_commit),
                    run.context.publication_ref,
                    str(publication_parent),
                ],
                check=True,
                timeout=20,
            )
        return target

    original_export = transfer.export_commit
    exported = []

    def exporting(repository_path, *, commit):
        assert changed and commit == run.context.pre_dispatch
        exported.append(commit)
        return original_export(repository_path, commit=commit)

    with monkeypatch.context() as guard:
        guard.setattr(d.Transaction, "get_ref", read_ref)
        guard.setattr(transfer, "export_commit", exporting)
        got = ex.observe_exchange(
            handle(workspace, spec), packet=workspace.parent / "pin"
        )
    assert got.phase == "initial" and exported == [run.context.pre_dispatch]
    assert bundle_oracle(got.packet / "snapshot.bundle") == typed_oracle(
        worker, (run.context.pre_dispatch,)
    )
    assert (
        ex.observe_exchange(
            handle(workspace, spec), packet=workspace.parent / "later"
        ).phase
        == "completion"
    )


def _publication_parent(worker, run):
    with d.Repository(worker) as repo, repo.read() as tx:
        return tx.get_commit(run.final_commit).parents[1]


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
@pytest.mark.parametrize("fault", ("ref", "malformed-ref", "commit"))
def test_progress_late_new_put_full_rollback(completed, core, phase, fault):
    path, workspace, spec, state, run = completed
    selected = observation(completed, phase)
    baseline = typed_oracle(path, (state[0], state[3]))
    returned = typed_oracle(workspace / "worker.dml", (selected.snapshot.commit,))
    if fault == "ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("received", state[3])
    elif fault == "malformed-ref":
        from test_records_hypothesis import run_driver

        run_driver("raw-write", str(path), "refs/heads/received", data=b"\0")
    before = (path / "data.mdb").read_bytes()
    with track_new_puts(
        path, baseline, core if fault == "commit" else None
    ) as successful:
        with pytest.raises((transfer.RefConflictError, d.DmlError)):
            receive(completed, selected.packet)
    assert successful
    assert (path / "data.mdb").read_bytes() == before
    # Fresh full immutable-state reader; conflicting refs checked separately.
    if fault == "commit":
        fresh_state(path, baseline, returned, False)
    else:
        _fresh_absence(path, baseline, returned)
    assert_main(path, state)


def _fresh_absence(path, baseline, returned):
    # Reuse existing fresh oracle with a distinct absent ref, while preserve raw
    # conflicts byte-for-byte. No deletion/repair of the malformed ref for the test.
    import base64

    manifest = path.parent / "absence.json"
    manifest.write_text(
        json.dumps(
            {
                "baseline": [
                    [k, str(i), base64.b64encode(b).decode()]
                    for (k, i), b in baseline.items()
                ],
                "new": [[k, str(i)] for k, i in returned if (k, i) not in baseline],
            }
        )
    )
    subprocess.run(
        [
            __import__("sys").executable,
            "-c",
            """import sys,json,base64,daggerml as d
m=json.load(open(sys.argv[2]))
with d.Repository(sys.argv[1]) as r,r.read() as t:
 for k,i,b in m['baseline']: assert t.get_record(k,d.ObjectId.from_hex(i))==base64.b64decode(b)
 for k,i in m['new']:
  try:t.get_record(k,d.ObjectId.from_hex(i))
  except d.NotFoundError:pass
  else:raise AssertionError('new batch visible')
""",
            str(path),
            str(manifest),
        ],
        check=True,
        timeout=20,
    )


def test_progress_to_final_same_ref_conflicts_without_head_movement(completed):
    path, workspace, spec, state, run = completed
    final = observation(completed, "completion", "final")
    initial = observation(completed, "initial", "initial")
    receive(completed, initial.packet)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(transfer.RefConflictError):
        receive(completed, final.packet)
    assert (path / "data.mdb").read_bytes() == before
    receive(completed, final.packet, "final")
    assert_main(path, state)


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
@pytest.mark.parametrize(
    "field,value",
    [
        ("phase", "bootstrap"),
        ("phase", 1),
        ("selected_commit", "0" * 32),
        ("pre_dispatch", "0" * 32),
        ("token", "0" * 32),
        ("commit", "0" * 32),
        ("request_id", "wrong"),
        ("attempt_id", "wrong"),
    ],
    ids=(
        "phase-name",
        "phase-type",
        "root",
        "pre",
        "token",
        "base",
        "request",
        "attempt",
    ),
)
def test_progress_descriptor_wrong_identity_before_a(completed, phase, field, value):
    selected = observation(completed, phase)
    change_json(selected.packet / "observation.json", **{field: value})
    path = completed[0]
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ex.ExchangeError, d.DmlError)):
        receive(completed, selected.packet)
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("mode", MODES)
def test_completion_observation_keeps_all_existing_wrong_history_checks(
    completed, mode
):
    path, workspace, spec, state, run = completed
    tamper(workspace, run, mode)
    receipt = json.loads((workspace / "completion.json").read_bytes())
    packet = workspace.parent / "packet"
    packet.mkdir()
    shutil.copyfile(workspace / "job.json", packet / "job.json")
    shutil.copyfile(workspace / "output.bundle", packet / "snapshot.bundle")
    ex._write_document(
        packet / "observation.json",
        {
            "format": ex.OBSERVATION_FORMAT,
            "token": spec.token,
            "commit": str(spec.commit),
            "phase": "completion",
            "selected_commit": receipt["final_commit"],
            "pre_dispatch": receipt["pre_dispatch"],
            "request_id": receipt["request_id"],
            "attempt_id": receipt["attempt_id"],
        },
    )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        receive(completed, packet)
    assert (path / "data.mdb").read_bytes() == before


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    phase=st.sampled_from(("initial", "publication", "completion")),
    name=st.text(alphabet="abcXYZ012", min_size=1, max_size=20),
)
def test_generated_progress_identity_repeat_and_pin(completed, phase, name):
    path, workspace, spec, state, run = completed
    # Reset actual refs to original immutable history for each generated case.
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        tx.update_ref("work", run.final_commit)
        tx.update_ref(
            run.context.publication_ref, tx.get_commit(run.final_commit).parents[1]
        )
    packet_name = "generated-" + phase + "-" + name
    packet = workspace.parent / packet_name
    if packet.exists():
        shutil.rmtree(packet)  # test-owned completed packet only, no writers
    selected = observation(completed, phase, packet_name)
    first = receive(completed, selected.packet, "r-" + phase + "-" + name)
    assert receive(completed, selected.packet, first.ref) == first
    assert observed_form(first) == selected.snapshot
    assert first.request_id == run.request_id and first.attempt_id == run.attempt_id
    assert_main(path, state)
