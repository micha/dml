"""Representative NEW metadata/child-publication atomicity; author-only loss.

No old runtime fault matrix replay. Each predicted new record is checked for
native absence BEFORE and AFTER abort, not inferred solely from exported roots.
"""

from pathlib import Path
from types import SimpleNamespace
import errno
import subprocess
import sys

import daggerml as d
from daggerml import transfer
import pytest

from test_recorded_maps import state, success, app as maps, reuse, funcs, story
from test_exchange import ROOT, exchange_runtime, typed_oracle
from test_binding_failures import core
from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_exchange_launch import wait_file

pytest_plugins = ("reuse_test_cleanup",)


def operation(state, mode):
    path, _, _, sources, inputs = state
    basis = inputs.commit
    construction = maps.inspect_input(path, commit=basis, dag=inputs.dag).construction
    if mode == "input":
        prepared = maps.map_insert(path, commit=basis, prior=construction, key=sources["left"], value=sources["n13"], output_name="prepared", ref="prepared")
        basis, construction = prepared.commit, prepared.dag
    def invoke(destination=path, **changes):
        args = dict(commit=basis, ref="authored", map_size=0)
        args.update(changes)
        if mode == "primitive":
            return maps.map_insert(destination, prior=construction, key=sources["left"], value=sources["n13"], output_name="authored", **args)
        if mode == "input":
            return maps.put_inputs(destination, construction=construction, output_name="authored", **args)
        if mode == "table":
            return reuse.define_table(destination, table_name="table", intent_uri=story.DOUBLE, **args)
        return reuse.record_request(destination, commit=args["commit"], intent_uri=story.DOUBLE, binding_name="double-binding", inputs_name=inputs.name, table_name="table", decision_name="decision", decision_ref=args["ref"], submission_ref="submission", map_size=args["map_size"])
    return basis, invoke


def predict(path, basis, invoke, tmp_path):
    old = typed_oracle(path, (basis,))
    prediction = tmp_path / "prediction"
    with d.Repository(prediction, create=True):
        pass
    transfer.import_commit(prediction, transfer.export_commit(path, commit=basis))
    got = invoke(prediction)
    # Decision failure happens before Q; predict its actual native Dd batch only.
    commit = got.decision.commit if isinstance(got, reuse.Request) else got.commit
    new = {key: raw for key, raw in typed_oracle(prediction, (commit,)).items() if key not in old}
    assert new and {"dag", "tree", "commit"} <= {kind for kind, _ in new}
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
    return got, old, new


@pytest.mark.parametrize("mode", ["primitive", "input", "table", "decision"])
@pytest.mark.parametrize("fault", ["late-ref", "response", "commit"])
def test_actual_NEW_native_metadata_batch_absent_on_abort(state, mode, fault, core, monkeypatch, tmp_path):
    path = state[0]
    basis, invoke = operation(state, mode)
    got, old, new = predict(path, basis, invoke, tmp_path)
    before = (path / "data.mdb").read_bytes()
    creating = d.Transaction.create_ref
    def late(self, name, target):
        if name == "authored":
            if fault == "late-ref":
                raise MemoryError("late explicit ref failure")
            if fault == "commit":
                core.native_fault(15, 1, errno.EIO)
        return creating(self, name, target)
    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        module, field = (maps, "Authored") if mode in ("primitive", "input") else (reuse, "Table") if mode == "table" else (reuse, "Decision")
        monkeypatch.setattr(module, field, lambda *a, **k: (_ for _ in ()).throw(MemoryError("precommit response allocation")))
    try:
        with track_typed_puts(path, old) as puts:
            with pytest.raises((MemoryError, d.DmlError)):
                invoke()
    finally:
        core.native_fault(0, 0, 0)
    assert puts == new
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)
        with pytest.raises(d.NotFoundError):
            tx.get_ref("authored")
        if mode == "decision":
            with pytest.raises(d.NotFoundError):
                tx.get_ref("submission")


def pending_hit(success, monkeypatch):
    from test_datum_reuse import request
    saved = {}
    original = reuse._publish_reuse
    def stop(path, recorded, selected, ref, size):
        saved.update(recorded=recorded, selected=selected)
        raise RuntimeError("private STOP after full Dd/Q before W")
    with monkeypatch.context() as guard:
        guard.setattr(reuse, "_publish_reuse", stop)
        with pytest.raises(RuntimeError, match="private STOP"):
            request(success)
    return saved["recorded"], saved["selected"], original


@pytest.mark.parametrize("fault", ["late-ref", "response", "map-full"])
def test_new_W_abort_keeps_exact_complete_Dd_Q_no_T(success, monkeypatch, tmp_path, fault):
    path = success[0]
    recorded, selected, publish = pending_hit(success, monkeypatch)
    def invoke(destination=path, **changes):
        return publish(destination, recorded, selected, "authored", changes.get("map_size", 0))
    got, old, new = predict(path, recorded.commit, invoke, tmp_path)
    before = (path / "data.mdb").read_bytes()
    original = d.Transaction.create_ref
    def late(self, name, commit):
        if name == "authored":
            if fault == "late-ref":
                raise MemoryError("late W ref")
            if fault == "map-full":
                self.put_datum(b"x" * (2 * 1024 * 1024))
        return original(self, name, commit)
    monkeypatch.setattr(d.Transaction, "create_ref", late)
    if fault == "response":
        monkeypatch.setattr(reuse, "Satisfaction", lambda *a: (_ for _ in ()).throw(MemoryError("W response allocation")))
    with track_typed_puts(path, old) as puts:
        with pytest.raises((d.MapFullError, MemoryError)):
            invoke(map_size=1048576 if fault == "map-full" else 0)
    assert puts == new
    if fault == "map-full":
        with d.Repository(path):
            pass
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("new-q") == recorded.commit
        assert tx.get_commit(recorded.commit).parents == (recorded.base,)
        for key in new:
            with pytest.raises(d.NotFoundError):
                tx.get_record(*key)


def test_actual_getter_trace_return_child_publication_single_batch_and_failure_abort(success, monkeypatch):
    path = success[0]
    from test_datum_reuse import request
    got = request(success, control="fresh", reuse_ref=None)
    context = SimpleNamespace(repository_path=path, pre_dispatch=got.recorded.commit, inputs=got.recorded.inputs, request=got.recorded.request)
    captured = {}
    def publication(tx, context, result):
        captured["result"] = result
        entries = maps.tree(tx, context.pre_dispatch)
        entries["host-profile"] = result
        commit = tx.put_commit(tx.put_tree(entries), parents=(context.pre_dispatch,))
        tx.create_ref("host-profile", commit)
        return commit
    with monkeypatch.context() as guard:
        guard.setattr(maps.local, "publish_result", publication)
        commit = maps.publish_callable(context, funcs.double)
    output = maps.Inspector(path, commit).returned(captured["result"], request=context.request, inputs=context.inputs)
    assert output.value == d.Datum.i64(84) and len(output.accesses) == 1
    # This is a host publication seam control, NOT another actual successful T/F.
    second = request(success, control="fresh", decision_name="host2", decision_ref="host2-d", submission_ref="host2-q", reuse_ref=None)
    context2 = SimpleNamespace(repository_path=path, pre_dispatch=second.recorded.commit, inputs=second.recorded.inputs, request=second.recorded.request)
    before = (path / "data.mdb").read_bytes()
    def failure(tx, context, result):
        captured["failed-result"] = result
        tx.get_dag(result)  # Actual authored complete R exists before late failure.
        raise MemoryError("late child publication seam failure")
    with monkeypatch.context() as guard:
        guard.setattr(maps.local, "publish_result", failure)
        with pytest.raises(MemoryError, match="late child"):
            maps.publish_callable(context2, funcs.double)
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_dag(captured["failed-result"])


@pytest.mark.parametrize("boundary", ["pre", "post"])
def test_authoring_only_loss_exact_predicted_native_publication(state, exchange_runtime, tmp_path, boundary):
    path = state[0]
    basis, invoke = operation(state, "primitive")
    predicted, old, new = predict(path, basis, invoke, tmp_path)
    marker = tmp_path / "marker"
    source = ROOT / "tests/argument_maps/metadata_loss.py"
    retained = tmp_path / "measured-metadata-loss.py"
    retained.write_bytes(source.read_bytes())
    import hashlib
    (tmp_path / "controller.sha256").write_text(hashlib.sha256(retained.read_bytes()).hexdigest() + "\n")
    errors = (tmp_path / "actor.stderr").open("wb")
    process = subprocess.Popen([sys.executable, str(retained), str(ROOT / "examples"), str(path), str(basis), str(marker), boundary], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errors)
    try:
        wait_file(marker, process, timeout=15)
        process.terminate()
        process.wait(timeout=5)
        errors.flush()
        assert process.returncode is not None and (tmp_path / "actor.stderr").read_bytes() == b""
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        errors.close()
    with d.Repository(path) as repo, repo.read() as tx:
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        if boundary == "pre":
            with pytest.raises(d.NotFoundError):
                tx.get_ref("authored")
            for key in new:
                with pytest.raises(d.NotFoundError):
                    tx.get_record(*key)
        else:
            assert tx.get_ref("authored") == predicted.commit
            assert tx.get_commit(predicted.commit).parents == (basis,)
            assert all(tx.get_record(*key) == raw for key, raw in new.items())
