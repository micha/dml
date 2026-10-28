"""Both selected return paths pin Cq/Q, including complete wrong-Q associations."""

from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

from test_caller_requests import (
    caller_job,
    caller_completed,
    record,
    prepare_recorded,
)
from test_exchange import (
    exchange_runtime,
    literal,
    tree,
    scalar,
    nested,
    typed_oracle,
    bundle_oracle,
    assert_main,
)
from test_exchange_records import clone, tamper, MODES
from test_exchange_progress import observation, observed_form, _fresh_absence
from test_exchange_process import track_new_puts
from test_binding_failures import core
import test_exchange_progress as progress


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
def test_caller_p_u_f_exact_bytes_refs_offline_no_registration(
    caller_completed, phase, monkeypatch
):
    path, workspace, spec, state, run = caller_completed
    original = typed_oracle(path, (spec.commit, state[3]))
    selected = observation(caller_completed, phase)
    assert selected.snapshot.request == spec.request
    expected = typed_oracle(workspace / "worker.dml", (selected.snapshot.commit,))
    assert bundle_oracle(selected.packet / "snapshot.bundle") == expected
    with d.Repository(path) as repo, repo.write() as tx:
        newer = tx.put_commit(tx.put_tree({"later": state[1]}), parents=(state[0],))
        tx.update_ref("main", newer)
    copied = path.parent / "only-packet"
    shutil.copytree(selected.packet, copied)
    (workspace / "worker.dml").rename(workspace / "worker.offline")
    with monkeypatch.context() as guard:
        for seam in ("run_request", "run_step", "retry_step"):
            guard.setattr(
                local,
                seam,
                lambda *a, **k: pytest.fail(
                    "inspection/reception must not register/dispatch"
                ),
            )
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("no execution"))
        got = ex.receive_observation(path, packet=copied, expected=spec, ref="received")
        assert (
            ex.receive_observation(path, packet=copied, expected=spec, ref="received")
            == got
        )
    assert observed_form(got) == selected.snapshot
    assert typed_oracle(path, (got.commit,)) == expected
    with d.Repository(path) as repo, repo.read() as tx:
        for key, raw in original.items():
            assert tx.get_record(*key) == raw
        assert tx.get_ref("submission") == spec.commit
        assert tx.get_ref("request-" + run.request_id) == spec.commit
        for ref in ("work", run.context.publication_ref):
            with pytest.raises(d.NotFoundError):
                tx.get_ref(ref)
    assert_main(path, state, newer)


@pytest.mark.parametrize("phase", ("sync", "initial", "publication", "completion"))
@pytest.mark.parametrize(
    "mode", ("foreign-cq", "association", "same-spelling", "missing-q")
)
def test_complete_matching_wrong_q_rejects_before_a(caller_completed, phase, mode):
    path, workspace, spec, state, run = caller_completed
    worker = workspace / "worker.dml"
    if mode == "foreign-cq":
        other_record = record(path, state[0], "submission-2")
        second = path.parent / "second"
        spec2 = prepare_recorded(path, second, other_record)
        run2 = ex.execute_exchange(second)
        # Independently validate as a genuine selected packet first.
        valid = ex.receive_exchange(
            path, workspace=second, expected=spec2, ref="valid-q2"
        )
        assert (
            valid.request == other_record.request != spec.request
            and valid.result == run.result
        )
        selected = observation(
            (path, second, spec2, state, run2),
            "completion" if phase == "sync" else phase,
            "other-packet",
        )
        pre, final, qid, aid = (
            run2.context.pre_dispatch,
            run2.final_commit,
            run2.request_id,
            run2.attempt_id,
        )
        source_worker = second / "worker.dml"
        root = final if phase == "sync" else selected.snapshot.commit
    else:
        with d.Repository(worker) as repo, repo.write() as tx:
            qid, aid = run.request_id, run.attempt_id
            if mode == "association":
                other = local.put_local_request(
                    tx,
                    request_id="q-" + "e" * 32,
                    intent_uri=spec.intent_uri,
                    binding=spec.binding,
                    inputs=spec.inputs,
                )
            else:
                other = clone(
                    tx,
                    spec.request,
                    fields={"intent": literal(tx, d.Datum.uri("urn:other"))},
                )
            pre_tree = tree(tx, run.context.pre_dispatch)
            initial = clone(
                tx, run.context.attempt, fields={"request": tx.put_subdag(other)}
            )
            pre_tree[run.context.publication_ref] = initial
            if mode == "same-spelling":
                pre_tree["request-" + qid] = other
            if mode == "missing-q":
                pre_tree.pop("request-" + qid)
            # Core discriminating case: EXPECTED Cq parent and exact expected Q
            # retained in tree; only T->Q association is wrong. Q2 is typed-complete
            # via T's sub-DAG edge, no missing dependencies/base rejection.
            pre = tx.put_commit(tx.put_tree(pre_tree), parents=(spec.commit,))
            if mode == "association":
                assert tree(tx, pre)["request-" + qid] == spec.request
                assert tx.get_commit(pre).parents == (spec.commit,)
                assert nested(tx, initial, "request") == other != spec.request
                assert (
                    nested(tx, other, "binding") == spec.binding
                    and nested(tx, other, "inputs") == spec.inputs
                )
                assert scalar(tx, other, "intent") == spec.intent_uri
            pdag = tree(tx, run.final_commit)["publication-" + aid]
            u_tree = dict(pre_tree, **{"publication-" + aid: pdag})
            publication = tx.put_commit(tx.put_tree(u_tree), parents=(pre,))
            final_attempt = clone(
                tx, run.final_attempt, fields={"request": tx.put_subdag(other)}
            )
            final_tree = dict(u_tree, **{run.context.publication_ref: final_attempt})
            final = tx.put_commit(tx.put_tree(final_tree), parents=(pre, publication))
        source_worker = worker
        root = (
            pre
            if phase == "initial"
            else publication if phase == "publication" else final
        )
    packet = path.parent / "wrong-packet"
    packet.mkdir()
    shutil.copyfile(workspace / "job.json", packet / "job.json")
    bundle = transfer.export_commit(source_worker, commit=root)
    # Independent fresh import confirms the candidate's full typed completeness.
    validation = path.parent / "typed-complete"
    with d.Repository(validation, create=True):
        pass
    imported = transfer.import_commit(validation, bundle)
    assert imported.commit == root
    assert typed_oracle(validation, (root,)) == typed_oracle(source_worker, (root,))
    if phase == "sync":
        (packet / "output.bundle").write_bytes(bundle)
        ex._write_document(
            packet / "completion.json",
            dict(
                format=ex.COMPLETION_FORMAT,
                token=spec.token,
                commit=str(spec.commit),
                final_commit=str(final),
                pre_dispatch=str(pre),
                request_id=qid,
                attempt_id=aid,
            ),
        )
    else:
        (packet / "snapshot.bundle").write_bytes(bundle)
        ex._write_document(
            packet / "observation.json",
            dict(
                format=ex.OBSERVATION_FORMAT,
                token=spec.token,
                commit=str(spec.commit),
                phase=phase,
                selected_commit=str(root),
                pre_dispatch=str(pre),
                request_id=qid,
                attempt_id=aid,
            ),
        )
    before = (path / "data.mdb").read_bytes()
    # Receipt token/base claims already rewritten to independent expected Q1.
    with pytest.raises((ex.ExchangeError, d.DmlError)) as error:
        if phase == "sync":
            ex.receive_exchange(path, workspace=packet, expected=spec, ref="wrong")
        else:
            ex.receive_observation(path, packet=packet, expected=spec, ref="wrong")
    if mode == "association":
        assert "initial attempt association" in str(error.value)
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("path_mode", ("sync", "async"))
def test_caller_mode_retains_all_final_outcome_history_checks(
    caller_completed, mode, path_mode
):
    if path_mode == "sync":
        path, workspace, spec, state, run = caller_completed
        tamper(workspace, run, mode)
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ex.ExchangeError):
            ex.receive_exchange(path, workspace=workspace, expected=spec, ref="bad")
        assert (path / "data.mdb").read_bytes() == before
    else:
        progress.test_completion_observation_keeps_all_existing_wrong_history_checks(
            caller_completed, mode
        )


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
@pytest.mark.parametrize("fault", ("ref", "malformed-ref", "commit"))
def test_caller_progress_late_actual_a_put_rollback(
    caller_completed, core, phase, fault
):
    # Baseline includes caller Q/Cq (unlike the original mode). Avoid counting
    # validation-store/preexisting Q rows as successful genuinely new A writes.
    path, workspace, spec, state, run = caller_completed
    selected = observation(caller_completed, phase)
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (selected.snapshot.commit,))
    if fault == "ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("received", state[3])
    elif fault == "malformed-ref":
        from test_records_hypothesis import run_driver

        run_driver("raw-write", str(path), "refs/heads/received", data=b"bad")
    before = (path / "data.mdb").read_bytes()
    with track_new_puts(
        path, baseline, core if fault == "commit" else None
    ) as successful:
        with pytest.raises((d.DmlError, transfer.RefConflictError)):
            ex.receive_observation(
                path, packet=selected.packet, expected=spec, ref="received"
            )
    assert successful
    assert (path / "data.mdb").read_bytes() == before
    _fresh_absence(path, baseline, returned)
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("submission") == spec.commit
        assert tx.get_ref("request-" + run.request_id) == spec.commit
    assert_main(path, state)


@pytest.mark.parametrize("mode", ("missing", "type", "id", "legacy", "extra"))
def test_required_nullable_request_job_handle_strict(caller_job, mode):
    path, workspace, spec, state, recorded = caller_job
    saved = path.parent / "handle"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(workspace, spec))
    assert ex.load_exchange_handle(saved).expected.request == recorded.request
    job = json.loads((workspace / "job.json").read_bytes())
    if mode == "missing":
        job.pop("request")
    elif mode == "type":
        job["request"] = 1
    elif mode == "id":
        job["request"] = "A" * 32
    elif mode == "legacy":
        job["format"] = "daggerml-local-exchange-job-v1"
    else:
        job["extra"] = True
    (workspace / "job.json").write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ex.ExchangeError):
        ex.execute_exchange(workspace)
    document = json.loads(saved.read_bytes())
    document["expected"] = job
    saved.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ex.ExchangeError):
        ex.load_exchange_handle(saved)
    assert not (workspace / "started").exists()
    with pytest.raises(TypeError):
        replace(spec, request="not-id")


@pytest.mark.parametrize(
    "mode",
    (
        "parents",
        "extra",
        "missing",
        "replaced",
        "preexisting",
        "intent",
        "binding",
        "inputs",
    ),
)
def test_pinned_submission_validation_before_workspace(caller_job, mode):
    path, workspace, spec, state, recorded = caller_job
    with d.Repository(path) as repo, repo.write() as tx:
        selected = tree(tx, spec.commit)
        basis = state[0]
        request = spec.request
        if mode == "extra":
            selected["extra"] = state[1]
        elif mode == "missing":
            selected.pop("request-" + recorded.request_id)
        elif mode == "replaced":
            selected["request-" + recorded.request_id] = state[2]
        elif mode == "preexisting":
            basis = spec.commit
        commit = tx.put_commit(
            tx.put_tree(selected), parents=() if mode == "parents" else (basis,)
        )
    target = path.parent / "bad-workspace"
    kwargs = dict(
        commit=commit,
        request=request,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri=spec.intent_uri,
        worker_ref="work",
        workspace=target,
    )
    if mode == "intent":
        kwargs["intent_uri"] = "urn:other"
    elif mode == "binding":
        kwargs["binding_name"] = "keep"
    elif mode == "inputs":
        kwargs["inputs_name"] = "keep"
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        ex.prepare_exchange(path, **kwargs)
    assert not target.exists() and (path / "data.mdb").read_bytes() == before


def test_caller_prior_q_t_history_coherent_pin_and_readers(
    caller_completed, monkeypatch
):
    path, workspace, spec, state, first = caller_completed
    returned = ex.receive_exchange(
        path, workspace=workspace, expected=spec, ref="prior"
    )
    recorded = record(path, returned.commit, "submission-2")
    second = path.parent / "second"
    spec2 = prepare_recorded(path, second, recorded)
    run2 = ex.execute_exchange(second)
    case = (path, second, spec2, state, run2)
    progress.test_coherent_read_transaction_and_pin_survive_ref_changes(
        case, monkeypatch
    )
    progress.test_progress_to_final_same_ref_conflicts_without_head_movement(case)
    import test_exchange_progress_process as processes

    with d.Repository(second / "worker.dml") as repo, repo.write() as tx:
        tx.update_ref("work", run2.final_commit)
        tx.update_ref(
            run2.context.publication_ref, tx.get_commit(run2.final_commit).parents[1]
        )
    processes.test_concurrent_read_only_observers_distinct_immutable_packets(case)
    with d.Repository(second / "worker.dml") as repo, repo.read() as tx:
        base = tree(tx, returned.commit)
        final = tree(tx, run2.final_commit)
        assert all(final[name] == oid for name, oid in base.items())
        assert tx.get_ref("request-" + run2.request_id) == spec2.commit


@pytest.mark.parametrize("phase", ("initial", "publication", "completion"))
def test_caller_validation_cleanup_before_any_a_write(
    caller_completed, monkeypatch, phase
):
    path, workspace, spec, state, run = caller_completed
    selected = observation(caller_completed, phase)
    before = (path / "data.mdb").read_bytes()
    allocated = []
    original = shutil.rmtree

    def denied(directory):
        allocated.append(directory)
        raise PermissionError("private receiver validation cleanup denial")

    importing = transfer.import_commit

    def only_validation(repository_path, *a, **k):
        assert Path(repository_path) != path
        return importing(repository_path, *a, **k)

    with monkeypatch.context() as guard:
        guard.setattr(ex.shutil, "rmtree", denied)
        guard.setattr(transfer, "import_commit", only_validation)
        with pytest.raises(PermissionError):
            ex.receive_observation(
                path, packet=selected.packet, expected=spec, ref="received"
            )
    assert len(allocated) == 1
    original(allocated[0])
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("fault", ("ref", "malformed-ref", "commit"))
def test_caller_sync_late_actual_a_put_rollback(caller_completed, core, fault):
    path, workspace, spec, state, run = caller_completed
    baseline = typed_oracle(path, (spec.commit, state[3]))
    returned = typed_oracle(workspace / "worker.dml", (run.final_commit,))
    if fault == "ref":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("received", state[3])
    elif fault == "malformed-ref":
        from test_records_hypothesis import run_driver

        run_driver("raw-write", str(path), "refs/heads/received", data=b"bad")
    before = (path / "data.mdb").read_bytes()
    with track_new_puts(
        path, baseline, core if fault == "commit" else None
    ) as successful:
        with pytest.raises((d.DmlError, transfer.RefConflictError)):
            ex.receive_exchange(
                path, workspace=workspace, expected=spec, ref="received"
            )
    assert successful
    assert (path / "data.mdb").read_bytes() == before
    _fresh_absence(path, baseline, returned)


@pytest.mark.parametrize("caller_mode", (False, True), ids=("fresh-q", "caller-q"))
def test_discovery_requires_fresh_attempt_even_with_valid_request(
    caller_completed, caller_mode
):
    path, workspace, spec, state, run = caller_completed
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        selected = tree(tx, run.context.pre_dispatch)
        selected.pop(run.context.publication_ref)
        wrong = tx.put_commit(tx.put_tree(selected), parents=(spec.commit,))
        tx.update_ref("work", wrong)
        if not caller_mode:
            spec = replace(spec, commit=state[0], request=None)
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        with pytest.raises(ex.ExchangeError, match="exactly one fresh"):
            ex._discover(tx, spec)
