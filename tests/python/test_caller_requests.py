"""Public Q-only recording/first registration, exact identities and whole-batch faults."""

from contextlib import contextmanager, ExitStack
import errno
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import uuid

import daggerml as d
from daggerml import exchange as ex, local, transfer
from hypothesis import given, settings, strategies as st
import pytest

from test_binding_failures import core
from test_exchange import (
    ROOT,
    exchange_runtime,
    initialize,
    literal,
    tree,
    scalar,
    nested,
    typed_oracle,
    assert_main,
)
from test_exchange_records import clone
from test_exchange_progress import _fresh_absence
from test_records_hypothesis import run_driver


def record(path, commit, ref="submission", **kwargs):
    return ex.record_exchange_request(
        path,
        commit=commit,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add-i64",
        ref=ref,
        **kwargs,
    )


def prepare_recorded(path, workspace, recorded):
    return ex.prepare_exchange(
        path,
        commit=recorded.commit,
        request=recorded.request,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri=recorded.intent_uri,
        worker_ref="work",
        workspace=workspace,
    )


@pytest.fixture
def caller_job(tmp_path, exchange_runtime):
    path, workspace = tmp_path / "a", tmp_path / "work"
    state = initialize(path)
    recorded = record(path, state[0])
    spec = prepare_recorded(path, workspace, recorded)
    return path, workspace, spec, state, recorded


@pytest.fixture
def caller_completed(caller_job):
    path, workspace, spec, state, recorded = caller_job
    run = ex.execute_exchange(workspace)
    assert (
        run.context.request == recorded.request
        and run.request_id == recorded.request_id
    )
    return path, workspace, spec, state, run


def assert_recorded(path, recorded):
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref(recorded.ref) == recorded.commit
        assert tx.get_ref("request-" + recorded.request_id) == recorded.commit
        assert tx.get_commit(recorded.commit).parents == (recorded.base,)
        expected = tree(tx, recorded.base)
        expected["request-" + recorded.request_id] = recorded.request
        assert tree(tx, recorded.commit) == expected
        assert scalar(tx, recorded.request, "intent") == recorded.intent_uri
        assert nested(tx, recorded.request, "binding") == recorded.binding
        assert nested(tx, recorded.request, "inputs") == recorded.inputs
        assert (
            tx.get_datum(tx.get_node(tx.get_dag(recorded.request).root).datum).value
            == recorded.request_id
        )


def test_q_before_launch_copy_without_refs_or_dispatch(caller_job, monkeypatch):
    path, workspace, spec, state, recorded = caller_job
    assert_recorded(path, recorded)
    assert_main(path, state)
    assert not (workspace / "worker.dml").exists()
    assert not list(path.parent.glob("dml-local-*"))
    assert spec.request == recorded.request and spec.commit == recorded.commit
    assert ex.observe_exchange(
        ex.ExchangeHandle(workspace, spec), packet=path.parent / "packet"
    ) == ex.ExchangeObservation("working", "bootstrap", None, None)
    copied = path.parent / "copied"
    with d.Repository(copied, create=True):
        pass
    bundle = transfer.export_commit(path, commit=recorded.commit)
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("pure import/prepare must not spawn"),
    )
    transfer.import_commit(copied, bundle, ref="work")
    assert typed_oracle(copied, (recorded.commit,)) == typed_oracle(
        path, (recorded.commit,)
    )
    with d.Repository(copied) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("request-" + recorded.request_id)
        assert not any(n.startswith("attempt-") for n in tree(tx, recorded.commit))
    with pytest.raises(local.LocalExecutionError) as error:
        local.retry_step(
            copied, head_ref="work", request=recorded.request, scratch_dir=path.parent
        )
    assert isinstance(error.value.__cause__, d.NotFoundError)
    assert error.value.occurrence is None
    prepare_recorded(copied, path.parent / "copied-workspace", recorded)
    native = Path(__import__("os").environ.get("DML_BIN", ROOT / "build/check/dml"))
    # Ordinary CLI is inspection only; restore actual process seam for this reader.
    monkeypatch.undo()
    got = subprocess.run(
        [str(native), "--json", "--repo", str(path), "snapshot", "--ref", recorded.ref],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert json.loads(got.stdout)["parents"] == [str(recorded.base)]


def test_public_builder_no_refs_commit_scratch_or_unique_claim(
    tmp_path, exchange_runtime
):
    path = tmp_path / "a"
    state = initialize(path)
    baseline = typed_oracle(path, (state[0], state[3]))
    qid = "q-" + "1" * 32
    with d.Repository(path) as repo:
        with repo.write() as tx:
            q = local.put_local_request(
                tx,
                request_id=qid,
                intent_uri="urn:example:add-i64",
                binding=state[1],
                inputs=state[2],
            )
            assert (
                local.put_local_request(
                    tx,
                    request_id=qid,
                    intent_uri="urn:example:add-i64",
                    binding=state[1],
                    inputs=state[2],
                )
                == q
            )
            assert set(tx.get_dag(q).bindings) == {
                "role",
                "intent",
                "binding",
                "inputs",
            }
            with pytest.raises(d.NotFoundError):
                tx.get_ref("request-" + qid)
            tx.abort()
        with repo.read() as tx:
            with pytest.raises(d.NotFoundError):
                tx.get_dag(q)
            for key, raw in baseline.items():
                assert tx.get_record(*key) == raw
    assert not list(tmp_path.glob("dml-local-*"))


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("request_id", None, local.ProtocolError),
        ("request_id", "q-" + "A" * 32, local.ProtocolError),
        ("request_id", "a-" + "0" * 32, local.ProtocolError),
        ("intent_uri", 1, TypeError),
        ("intent_uri", "relative", d.DmlError),
        ("intent_uri", "HTTP://Example.com", d.DmlError),
        ("binding", None, TypeError),
        ("inputs", None, TypeError),
    ],
    ids=(
        "qid-type",
        "qid-upper",
        "qid-role",
        "intent-type",
        "intent-relative",
        "intent-canonical",
        "binding-type",
        "inputs-type",
    ),
)
def test_builder_boundaries(caller_job, field, value, error):
    path, workspace, spec, state, recorded = caller_job
    kwargs = dict(
        request_id="q-" + "2" * 32,
        intent_uri=recorded.intent_uri,
        binding=spec.binding,
        inputs=spec.inputs,
    )
    kwargs[field] = value
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(error), d.Repository(path) as repo, repo.write() as tx:
        local.put_local_request(tx, **kwargs)
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("commit", None, TypeError),
        ("binding_name", 1, TypeError),
        ("inputs_name", "missing", ex.ExchangeError),
        ("binding_name", "missing", ex.ExchangeError),
        ("ref", "bad/name", ex.ExchangeError),
        ("intent_uri", "HTTP://Example.com", ex.ExchangeError),
        ("map_size", True, TypeError),
        ("map_size", 1, ex.ExchangeError),
        ("map_size", -1, ex.ExchangeError),
    ],
    ids=(
        "commit-type",
        "name-type",
        "missing-inputs",
        "missing-binding",
        "ref-profile",
        "intent-canonical",
        "map-type",
        "map-small",
        "map-negative",
    ),
)
def test_record_boundaries_before_batch(caller_job, field, value, error):
    path, workspace, spec, state, recorded = caller_job
    kwargs = dict(
        commit=state[0],
        binding_name="binding",
        inputs_name="inputs",
        intent_uri=recorded.intent_uri,
        ref="new",
    )
    kwargs[field] = value
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(error):
        ex.record_exchange_request(path, **kwargs)
    assert (path / "data.mdb").read_bytes() == before


def assert_file_unchanged(file, before):
    """Exact whole-file equality with bounded diagnostics, never hash-only equality."""
    actual = file.read_bytes()
    unchanged = actual == before
    assert unchanged, (
        "whole file differs: lengths "
        + str(len(before))
        + "/"
        + str(len(actual))
        + "; SHA256 "
        + hashlib.sha256(before).hexdigest()
        + "/"
        + hashlib.sha256(actual).hexdigest()
    )


@contextmanager
def track_typed_puts(path, baseline):
    """Successful genuinely new puts/readback in this actual repository only."""
    successful = {}
    opening = d.Repository.__init__

    def opened(self, repository_path, **kwargs):
        opening(self, repository_path, **kwargs)
        self._test_selected_path = Path(repository_path).resolve() == path.resolve()

    with patch.object(d.Repository, "__init__", opened):
        with ExitStack() as stack:
            for method, kind in (
                ("put_datum", "datum"),
                ("put_literal", "node"),
                ("put_subdag", "node"),
                ("put_dag", "dag"),
                ("put_tree", "tree"),
                ("put_commit", "commit"),
            ):
                original = getattr(d.Transaction, method)

                def put(self, *a, _original=original, _kind=kind, **k):
                    oid = _original(self, *a, **k)
                    if self._owner._test_selected_path and (_kind, oid) not in baseline:
                        raw = self.get_record(_kind, oid)
                        successful[_kind, oid] = raw
                    return oid

                stack.enter_context(patch.object(d.Transaction, method, put))
            yield successful


@pytest.mark.parametrize(
    "fault",
    (
        "second-ref",
        "dangling-submission",
        "dangling-qref",
        "raw-qref",
        "commit",
        "map-full",
    ),
)
def test_record_late_q_cq_puts_whole_abort(caller_job, core, monkeypatch, fault):
    path, workspace, spec, state, recorded = caller_job
    qid = "q-" + "3" * 32
    monkeypatch.setattr(ex.uuid, "uuid4", lambda: uuid.UUID(hex="3" * 32))
    if fault.startswith("dangling"):
        name = "new" if fault == "dangling-submission" else "request-" + qid
        run_driver("raw-write", str(path), "refs/heads/" + name, data=bytes(16))
    # Raw qref normally rejects on the early read. To exercise native create late,
    # insert raw corruption from a private fixture within the same transaction isn't
    # public; instead hide only its early read and preserve actual create semantics.
    if fault == "raw-qref":
        run_driver("raw-write", str(path), "refs/heads/request-" + qid, data=b"bad")
        original_get = d.Transaction.get_ref

        def unread(self, name):
            if name == "request-" + qid:
                raise d.NotFoundError(
                    "not_found", detail="private early-read substitution"
                )
            return original_get(self, name)

        monkeypatch.setattr(d.Transaction, "get_ref", unread)
    baseline = typed_oracle(path, (state[0], state[3], recorded.commit))
    before = (path / "data.mdb").read_bytes()
    creating = d.Transaction.create_ref

    def late(self, name, target):
        if name == "request-" + qid:
            if fault == "second-ref":
                raise d.DmlError("io_error", detail="private late second-ref denial")
            if fault == "map-full":
                self.put_datum(
                    b"x" * (2 * 1024 * 1024)
                )  # real native map-full after Q/Cq
        return creating(self, name, target)

    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "commit":
        core.native_fault(15, 1, errno.EIO)
    try:
        with track_typed_puts(path, baseline) as new:
            with pytest.raises(d.DmlError):
                record(
                    path,
                    state[0],
                    "new",
                    map_size=1048576 if fault == "map-full" else 0,
                )
    finally:
        core.native_fault(0, 0, 0)
    assert sum(kind == "dag" for kind, oid in new) >= 1
    assert (
        sum(kind == "commit" for kind, oid in new) == 1
    ), "actual successful new Cq put required"
    # LMDB's Windows open sets physical file extent to the configured map size.
    # Compare the SAME default-map layout on both sides of the failed small-map
    # transaction. This opens/closes only, with no research-state writes. Fresh
    # all-object/absent-batch and raw-corruption oracles below remain unchanged.
    if fault == "map-full":
        with d.Repository(path):
            pass
    assert_file_unchanged(path / "data.mdb", before)
    _fresh_absence(path, baseline, new)
    assert_recorded(path, recorded)
    assert_main(path, state)


@pytest.mark.parametrize("mode", ("existing", "same-target", "raw", "alias"))
def test_record_conflicts_do_not_repair(caller_job, monkeypatch, mode):
    path, workspace, spec, state, recorded = caller_job
    ref = "new"
    if mode in ("existing", "same-target"):
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref(ref, state[3] if mode == "existing" else state[0])
    elif mode == "raw":
        run_driver("raw-write", str(path), "refs/heads/new", data=b"bad")
    else:
        monkeypatch.setattr(ex.uuid, "uuid4", lambda: uuid.UUID(hex="4" * 32))
        ref = "request-q-" + "4" * 32
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ex.ExchangeError, d.DmlError)):
        record(path, state[0], ref)
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("collision", ("ref", "tree"))
def test_record_collision_retry_and_exhaustion(caller_job, monkeypatch, collision):
    path, workspace, spec, state, recorded = caller_job
    payload = "5" * 32
    name = "request-q-" + payload
    base = state[0]
    with d.Repository(path) as repo, repo.write() as tx:
        if collision == "ref":
            tx.create_ref(name, state[0])
        else:
            selected = tree(tx, base)
            selected[name] = state[1]
            base = tx.put_commit(tx.put_tree(selected), parents=(base,))
    original = uuid.uuid4
    ids = iter((uuid.UUID(hex=payload), original()))
    monkeypatch.setattr(ex.uuid, "uuid4", lambda: next(ids))
    got = record(path, base, "retry")
    assert got.request_id != "q-" + payload
    assert_recorded(path, got)
    monkeypatch.setattr(ex.uuid, "uuid4", lambda: uuid.UUID(hex=payload))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError, match="collision limit"):
        record(path, base, "exhausted")
    assert (path / "data.mdb").read_bytes() == before


@settings(max_examples=15, deadline=None)
@given(
    st.text(alphabet="abcXYZ012", min_size=1, max_size=24),
    st.binary(min_size=16, max_size=16),
)
def test_generated_record_preserves_bytes_and_duplicate_ref(
    tmp_path_factory, name, payload
):
    with tempfile.TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as directory:
        path = Path(directory) / "a"
        state = initialize(path)
        before = typed_oracle(path, (state[0], state[3]))
        with patch.object(ex.uuid, "uuid4", lambda: uuid.UUID(bytes=payload)):
            got = record(path, state[0], "s-" + name)
            assert_recorded(path, got)
            assert got.request_id == "q-" + payload.hex()
            all_bytes = typed_oracle(path, (got.commit, state[3]))
            assert all(all_bytes[key] == raw for key, raw in before.items())
            with pytest.raises(ex.ExchangeError):
                record(path, state[0], "s-" + name)
        assert_main(path, state)


def imported(caller_job):
    path, workspace, spec, state, recorded = caller_job
    worker = path.parent / "imported"
    with d.Repository(worker, create=True):
        pass
    transfer.import_commit(
        worker, (workspace / "input.bundle").read_bytes(), ref="work"
    )
    return worker


@pytest.mark.parametrize(
    "mode",
    (
        "head",
        "non-submission",
        "missing-q",
        "wrong-q",
        "basis-binding",
        "qid",
        "role",
        "intent-type",
        "binding-type",
        "inputs-type",
    ),
)
def test_first_registration_rejects_wrong_basis_q_without_spawn(
    caller_job, monkeypatch, mode
):
    path, workspace, spec, state, recorded = caller_job
    worker = imported(caller_job)
    selected, request = spec.commit, spec.request
    with d.Repository(worker) as repo, repo.write() as tx:
        if mode == "head":
            tx.update_ref("work", state[0])
        elif mode == "non-submission":
            selected = tx.put_commit(
                tx.get_commit(spec.commit).tree, parents=(state[0], spec.commit)
            )
        elif mode == "missing-q":
            selected = state[0]
        elif mode == "basis-binding":
            selected = tx.put_commit(
                tx.put_tree({"request-" + recorded.request_id: request}),
                parents=(tx.put_commit(tx.put_tree({})),),
            )
        else:
            fields, root = {}, None
            if mode in ("wrong-q", "qid"):
                root = literal(tx, "q-" + "9" * 32 if mode == "wrong-q" else "bad")
            elif mode == "role":
                fields["role"] = literal(tx, "wrong")
            elif mode == "intent-type":
                fields["intent"] = tx.put_subdag(spec.inputs)
            else:
                fields[mode[:-5]] = literal(tx, "wrong")
            request = clone(tx, request, fields=fields, root=root)
            selected_tree = tree(tx, spec.commit)
            selected_tree["request-" + recorded.request_id] = request
            selected = tx.put_commit(tx.put_tree(selected_tree), parents=(state[0],))
        if mode != "head":
            tx.update_ref("work", selected)
    before = (worker / "data.mdb").read_bytes()
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("no precommit spawn")
    )
    with pytest.raises(local.LocalExecutionError) as error:
        local.run_request(
            worker,
            head_ref="work",
            request_commit=selected,
            request=request,
            scratch_dir=path.parent,
        )
    assert error.value.occurrence is None
    assert (worker / "data.mdb").read_bytes() == before
    assert_recorded(path, recorded)


@pytest.mark.parametrize(
    "fault", ("same", "different", "dangling", "raw", "late-ref", "commit", "map-full")
)
def test_registration_reservation_and_late_new_t_p_rollback(
    caller_job, core, monkeypatch, fault
):
    path, workspace, spec, state, recorded = caller_job
    worker = imported(caller_job)
    qref = "request-" + recorded.request_id
    if fault in ("same", "different"):
        with d.Repository(worker) as repo, repo.write() as tx:
            tx.create_ref(
                qref,
                spec.commit if fault == "same" else state[0],
            )
    elif fault in ("dangling", "raw"):
        run_driver(
            "raw-write",
            str(worker),
            "refs/heads/" + qref,
            data=bytes(16) if fault == "dangling" else b"bad",
        )
    if fault == "raw":
        original = d.Transaction.get_ref

        def hidden(self, name):
            if name == qref:
                raise d.NotFoundError(
                    "not_found", detail="private early-read substitution"
                )
            return original(self, name)

        monkeypatch.setattr(d.Transaction, "get_ref", hidden)
    baseline = typed_oracle(worker, (spec.commit,))
    before = (worker / "data.mdb").read_bytes()
    creating = d.Transaction.create_ref

    def late(self, name, target):
        if name == qref:
            if fault == "late-ref":
                raise d.DmlError("io_error", detail="private late registration denial")
            if fault == "map-full":
                self.put_datum(
                    b"x" * (65 * 1024 * 1024)
                )  # unchanged default map, real native failure
        return creating(self, name, target)

    monkeypatch.setattr(d.Transaction, "create_ref", late)
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("no spawn after failed atomic registration"),
    )
    if fault == "commit":
        core.native_fault(15, 1, errno.EIO)
    try:
        with track_typed_puts(worker, baseline) as new:
            with pytest.raises(local.LocalExecutionError) as error:
                local.run_request(
                    worker,
                    head_ref="work",
                    request_commit=spec.commit,
                    request=spec.request,
                    scratch_dir=path.parent,
                )
    finally:
        core.native_fault(0, 0, 0)
    assert error.value.occurrence is None
    if fault not in ("same", "different"):
        assert any(kind == "dag" for kind, oid in new) and any(
            kind == "commit" for kind, oid in new
        ), "genuine T/P successful puts required"
    assert (worker / "data.mdb").read_bytes() == before
    # No computational subprocess; restore seam for fresh independent typed reader.
    runtime_path = __import__("os").environ["PYTHONPATH"]
    monkeypatch.undo()
    monkeypatch.setenv("PYTHONPATH", runtime_path)
    _fresh_absence(worker, baseline, new)
    with d.Repository(worker) as repo, repo.read() as tx:
        assert tx.get_ref("work") == spec.commit
    assert_recorded(path, recorded)


def test_first_registration_exact_q_only_new_t_then_reject_again(caller_job):
    path, workspace, spec, state, recorded = caller_job
    worker = imported(caller_job)
    original = typed_oracle(worker, (spec.commit,))
    run = local.run_request(
        worker,
        head_ref="work",
        request_commit=spec.commit,
        request=spec.request,
        scratch_dir=path.parent,
    )
    assert (
        run.context.request == recorded.request
        and run.request_id == recorded.request_id
    )
    with d.Repository(worker) as repo, repo.read() as tx:
        expected = tree(tx, spec.commit)
        expected[run.context.publication_ref] = run.context.attempt
        assert tree(tx, run.context.pre_dispatch) == expected
        assert tx.get_commit(run.context.pre_dispatch).parents == (spec.commit,)
        assert tx.get_ref("request-" + recorded.request_id) == spec.commit
        for key, raw in original.items():
            assert tx.get_record(*key) == raw
    with pytest.raises(local.LocalExecutionError):
        local.run_request(
            worker, head_ref="work", request_commit=spec.commit, request=spec.request
        )
    # Even resetting the head cannot erase the local first-registration guard.
    with d.Repository(worker) as repo, repo.write() as tx:
        tx.update_ref("work", spec.commit)
    with pytest.raises(local.LocalExecutionError, match="already registered"):
        local.run_request(
            worker, head_ref="work", request_commit=spec.commit, request=spec.request
        )
    assert_recorded(path, recorded)


def test_first_attempt_collision_retry_exhaustion_and_types(caller_job, monkeypatch):
    worker = imported(caller_job)
    spec = caller_job[2]
    for field in ("request", "request_commit"):
        kwargs = dict(head_ref="work", request=spec.request, request_commit=spec.commit)
        kwargs[field] = None
        with pytest.raises(TypeError):
            local.run_request(worker, **kwargs)
    aid = "a-" + "6" * 32
    with d.Repository(worker) as repo, repo.write() as tx:
        tx.create_ref("attempt-" + aid, spec.commit)
    original = local._new_id
    monkeypatch.setattr(local, "_new_id", lambda p: aid)
    before = (worker / "data.mdb").read_bytes()
    with pytest.raises(local.LocalExecutionError, match="collision limit"):
        local.run_request(
            worker, head_ref="work", request_commit=spec.commit, request=spec.request
        )
    assert (worker / "data.mdb").read_bytes() == before
    calls = []

    def once(prefix):
        calls.append(prefix)
        assert prefix == "a", "first attempt must never generate Q"
        return aid if len(calls) == 1 else original(prefix)

    monkeypatch.setattr(local, "_new_id", once)
    run = local.run_request(
        worker, head_ref="work", request_commit=spec.commit, request=spec.request
    )
    assert len(calls) == 2 and run.context.request == spec.request


@pytest.mark.parametrize("fault", ("input", "job", "export"))
def test_prepare_failure_leaves_recorded_q(caller_job, monkeypatch, fault):
    import builtins

    path, workspace, spec, state, recorded = caller_job
    opening = builtins.open

    def denied(file, *a, **k):
        if Path(file).name == "input.bundle":
            raise PermissionError("private input-file denial")
        return opening(file, *a, **k)

    if fault == "input":
        monkeypatch.setattr(builtins, "open", denied)
    elif fault == "job":
        monkeypatch.setattr(
            ex.os,
            "replace",
            lambda *a: (_ for _ in ()).throw(PermissionError("private job denial")),
        )
    else:
        monkeypatch.setattr(transfer, "MAX_PACKED_BYTES", 1)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((OSError, transfer.TransferError)):
        prepare_recorded(path, path.parent / "failed-prepare", recorded)
    assert (path / "data.mdb").read_bytes() == before
    assert_recorded(path, recorded)


@pytest.mark.parametrize(
    "mode",
    ("root", "role", "source", "adapter", "interpreter", "timeout", "subdag", "fields"),
)
@pytest.mark.parametrize("operation", ("builder", "record"))
def test_consumed_binding_profile_before_q_publication(caller_job, mode, operation):
    path, workspace, spec, state, recorded = caller_job
    with d.Repository(path) as repo, repo.write() as tx:
        fields, root, remove = {}, None, ()
        if mode == "root":
            root = literal(tx, "wrong")
        elif mode == "fields":
            remove = ("source",)
        elif mode == "subdag":
            fields["source"] = tx.put_subdag(spec.inputs)
        else:
            values = {
                "role": "wrong",
                "source": b"",
                "adapter": d.Datum.uri("urn:wrong"),
                "interpreter": "relative",
                "timeout": 0,
            }
            fields["timeout-ms" if mode == "timeout" else mode] = literal(
                tx, values[mode]
            )
        binding = clone(tx, spec.binding, fields=fields, root=root, remove=remove)
        selected = tree(tx, state[0])
        selected["binding"] = binding
        commit = tx.put_commit(tx.put_tree(selected), parents=(state[0],))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((local.ProtocolError, ex.ExchangeError, ValueError)):
        if operation == "record":
            record(path, commit, "malformed")
        else:
            with d.Repository(path) as repo, repo.write() as tx:
                local.put_local_request(
                    tx,
                    request_id="q-" + "d" * 32,
                    intent_uri=spec.intent_uri,
                    binding=binding,
                    inputs=spec.inputs,
                )
    assert (path / "data.mdb").read_bytes() == before


def test_record_response_prebuilt_before_commit(caller_job, monkeypatch):
    path, workspace, spec, state, recorded = caller_job
    baseline = typed_oracle(path, (spec.commit, state[3]))
    before = (path / "data.mdb").read_bytes()
    monkeypatch.setattr(
        ex,
        "RecordedRequest",
        lambda *a: (_ for _ in ()).throw(
            MemoryError("private owned-description allocation")
        ),
    )
    with track_typed_puts(path, baseline) as new:
        with pytest.raises(MemoryError):
            record(path, state[0], "allocation")
    assert any(k == "commit" for k, oid in new)
    assert (path / "data.mdb").read_bytes() == before
    _fresh_absence(path, baseline, new)


@pytest.mark.parametrize(
    "mode", ("raw-reservation", "attempt-tree", "publication-tree")
)
def test_first_registration_early_raw_or_tree_collision(caller_job, monkeypatch, mode):
    path, workspace, spec, state, recorded = caller_job
    aid = "a-" + "b" * 32
    if mode != "raw-reservation":
        with d.Repository(path) as repo, repo.write() as tx:
            selected = tree(tx, state[0])
            selected[
                ("attempt-" if mode == "attempt-tree" else "publication-") + aid
            ] = state[2]
            base = tx.put_commit(tx.put_tree(selected), parents=(state[0],))
        recorded = record(path, base, "collision-submission")
        workspace = path.parent / "collision-workspace"
        spec = prepare_recorded(path, workspace, recorded)
        caller_job = (path, workspace, spec, state, recorded)
    worker = imported(caller_job)
    if mode == "raw-reservation":
        run_driver(
            "raw-write",
            str(worker),
            "refs/heads/request-" + recorded.request_id,
            data=b"bad",
        )
    monkeypatch.setattr(local, "_new_id", lambda prefix: aid)
    before = (worker / "data.mdb").read_bytes()
    baseline = typed_oracle(worker, (spec.commit,))
    with monkeypatch.context() as guard:
        guard.setattr(
            subprocess,
            "Popen",
            lambda *a, **k: pytest.fail("early rejection must not spawn"),
        )
        with track_typed_puts(worker, baseline) as new:
            with pytest.raises(local.LocalExecutionError) as error:
                local.run_request(
                    worker,
                    head_ref="work",
                    request_commit=spec.commit,
                    request=spec.request,
                )
    assert not new and error.value.occurrence is None
    if mode == "raw-reservation":
        assert isinstance(error.value.__cause__, d.IntegrityError)
    else:
        assert "collision limit" in str(error.value)
    assert (worker / "data.mdb").read_bytes() == before
    assert_recorded(path, recorded)


@pytest.mark.parametrize("difference", ("same", "raw-byte", "extent"))
def test_exact_file_comparison_has_compact_failure(difference, tmp_path):
    file = tmp_path / "raw-bytes"
    before = b"x" * (2 * 1024 * 1024)
    actual = (
        before
        if difference == "same"
        else (before[:-1] + b"y" if difference == "raw-byte" else before + b"\0")
    )
    file.write_bytes(actual)
    if difference == "same":
        assert_file_unchanged(file, before)
    else:
        with pytest.raises(AssertionError, match="whole file differs") as error:
            assert_file_unchanged(file, before)
        assert len(str(error.value)) < 512
        assert "x" * 100 not in str(error.value)


def test_record_map_full_same_layout_after_windows_extent_change(
    caller_job, core, monkeypatch
):
    path = caller_job[0]
    original = d.Repository.__init__
    extents = []

    def windows_extent(self, repository_path, **kwargs):
        original(self, repository_path, **kwargs)
        if Path(repository_path).resolve() == path.resolve():
            size = kwargs.get("map_size", 0) or 64 * 1024 * 1024
            # Vendored mdb_env_map/_WIN32 uses SetEndOfFile at open. Model only
            # that file-layout effect over real Linux/native transactions; native
            # map sizes match, committed data fits the 1 MiB pressure map.
            # Actual Windows already set this extent while opening the native
            # mapping; never redundantly truncate its live mapped section.
            if (path / "data.mdb").stat().st_size != size:
                with open(path / "data.mdb", "r+b") as stream:
                    stream.truncate(size)
            extents.append(size)

    monkeypatch.setattr(d.Repository, "__init__", windows_extent)
    test_record_late_q_cq_puts_whole_abort(caller_job, core, monkeypatch, "map-full")
    assert 1048576 in extents
    small = extents.index(1048576)
    assert 64 * 1024 * 1024 in extents[small + 1 :]
