"""Malformed ordinary DAGs fail closed at the narrow local protocol boundary."""
from dataclasses import replace
from pathlib import Path
import shutil
import sys

import daggerml as dml
from daggerml import local
import pytest

from test_local_execution import ROOT, bind, prepare, run, runtime, state


@pytest.mark.parametrize("mode", ["ref", "missing-attempt", "root", "recorded-ref", "scratch", "request", "reservation"])
def test_context_rejects_pinned_mismatches(state, tmp_path, mode):
    context = prepare(state, tmp_path)
    try:
        with dml.Repository(state[0]) as repo, repo.write() as tx:
            tree = local._tree(tx, context.pre_dispatch)
            fields = {"role": "local-attempt-v1", "publication-ref": context.publication_ref,
                      "scratch": context.scratch}
            root = context.attempt_id
            if mode == "ref":
                with pytest.raises(local.ProtocolError, match="publication ref does not"):
                    local._context(tx, str(state[0]), context.pre_dispatch, context.attempt_id, "wrong")
                return
            if mode == "missing-attempt":
                tree.pop(context.publication_ref)
            elif mode == "root":
                root = "a-" + "0"*32
            elif mode == "recorded-ref":
                fields["publication-ref"] = "other"
            elif mode == "scratch":
                fields["scratch"] = "relative"
            elif mode == "request":
                tree.pop("request-" + context.request_id)
            else:
                tx.update_ref("request-" + context.request_id, state[3])
            if mode not in ("missing-attempt", "request", "reservation"):
                tree[context.publication_ref] = local._record(tx, root, fields, (("request", context.request),))
            pinned = tx.put_commit(tx.put_tree(tree), parents=(context.pre_dispatch,))
            with pytest.raises(local.ProtocolError):
                local._context(tx, str(state[0]), pinned, context.attempt_id, context.publication_ref)
    finally:
        shutil.rmtree(context.scratch)


def test_wrong_scalar_field_shapes_and_binding_root(state):
    with dml.Repository(state[0]) as repo, repo.write() as tx:
        nested = tx.put_subdag(state[1])
        with pytest.raises(local.ProtocolError, match="literal"):
            local._scalar(tx, nested, "string")
        number = local._literal(tx, 1)
        with pytest.raises(local.ProtocolError, match="string datum"):
            local._scalar(tx, number, "string")
        with pytest.raises(local.ProtocolError, match="fields"):
            local._fields(tx, state[1], ("role",), "local-request-v1")
        good = tx.get_dag(state[2])
        wrong_root = tx.put_dag(root=number, bindings=good.bindings)
        with pytest.raises(local.ProtocolError, match="binding root"):
            local._binding(tx, wrong_root)
        nodes = dict(good.bindings)
        nodes["adapter"] = local._literal(tx, dml.Datum.uri("urn:wrong"))
        wrong_adapter = tx.put_dag(root=good.root, bindings=nodes)
        with pytest.raises(local.ProtocolError, match="adapter"):
            local._binding(tx, wrong_adapter)


def test_retry_reservation_and_conflicting_head_request(state, tmp_path):
    context = prepare(state, tmp_path)
    try:
        with dml.Repository(state[0]) as repo, repo.write() as tx:
            tx.update_ref("request-" + context.request_id, state[3])
        with pytest.raises(local.LocalExecutionError, match="reservation mismatch"):
            local.retry_step(state[0], head_ref="main", request=context.request, scratch_dir=tmp_path)
        with dml.Repository(state[0]) as repo, repo.write() as tx:
            tx.update_ref("request-" + context.request_id, context.pre_dispatch)
            tree = local._tree(tx, context.pre_dispatch)
            tree["request-" + context.request_id] = state[1]
            commit = tx.put_commit(tx.put_tree(tree), parents=(context.pre_dispatch,))
            tx.update_ref("main", commit)
        with pytest.raises(local.LocalExecutionError, match="another request"):
            local.retry_step(state[0], head_ref="main", request=context.request, scratch_dir=tmp_path)
    finally:
        shutil.rmtree(context.scratch)


def test_existing_publication_entry_not_replaced(state, tmp_path):
    context = prepare(state, tmp_path)
    try:
        with dml.Repository(state[0]) as repo, repo.write() as tx:
            tree = local._tree(tx, context.pre_dispatch)
            tree["publication-" + context.attempt_id] = state[1]
            pinned = tx.put_commit(tx.put_tree(tree), parents=(context.pre_dispatch,))
            tx.update_ref(context.publication_ref, pinned)
            context = replace(context, pre_dispatch=pinned)
            with pytest.raises(local.ConflictError, match="entry already"):
                local.publish_result(tx, context, state[1])
    finally:
        shutil.rmtree(context.scratch)


def test_wait_error_reaps_and_final_context_mismatch(state, monkeypatch):
    events = []
    class Process:
        returncode = None
        def wait(self, timeout):
            events.append("wait")
            if len(events) == 1:
                raise RuntimeError("wait failed")
            self.returncode = -15
        def terminate(self): events.append("terminate")
        def poll(self): return self.returncode
    original_popen = local.subprocess.Popen
    monkeypatch.setattr(local.subprocess, "Popen", lambda *a, **k: Process())
    with pytest.raises(local.LocalExecutionError, match="wait failed"):
        run(state)
    assert events == ["wait", "terminate", "wait"]
    # A real, reaped process path is restored before the next dispatch.
    monkeypatch.setattr(local.subprocess, "Popen", original_popen)
    original = local._finalize
    def mismatched(context, *args):
        return original(replace(context, inputs=context.binding), *args)
    monkeypatch.setattr(local, "_finalize", mismatched)
    with pytest.raises(local.LocalExecutionError, match="completion context"):
        run(state)


@pytest.mark.parametrize("kind", ["string", "subdag"])
def test_child_add_validates_argument_types_in_process(state, tmp_path, monkeypatch, kind):
    with dml.Repository(state[0]) as repo, repo.write() as tx:
        node = tx.put_subdag(state[1]) if kind == "subdag" else local._literal(tx, "4")
        inputs = tx.put_dag(root=node, bindings={"left": node, "right": node})
    context = prepare((state[0], inputs, state[2], state[3]), tmp_path)
    try:
        monkeypatch.setattr(sys, "argv", ["entry.py", str(state[0]), str(context.pre_dispatch),
                                         context.attempt_id, context.publication_ref])
        import runpy
        with pytest.raises(ValueError, match="addition requires"):
            runpy.run_path(str(ROOT / "examples/local_add.py"), run_name="__main__")
    finally:
        shutil.rmtree(context.scratch)


def test_non_nfc_scratch_rejected_before_publication(state, tmp_path):
    parent = tmp_path / "e\u0301"
    parent.mkdir()
    with pytest.raises(local.LocalExecutionError, match="paths must be NFC") as error:
        local.run_step(state[0], head_ref="main", intent_uri="urn:x", binding=state[2],
                       inputs=state[1], scratch_dir=parent)
    assert error.value.occurrence is None
    assert not list(parent.iterdir())
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert tx.get_ref("main") == state[3]


def test_real_child_map_full_aborts_result_and_ref(state):
    source = b'''import daggerml as d
from daggerml.local import child_context, publish_result
c = child_context()
with d.Repository(c.repository_path, map_size=1048576) as r, r.write() as t:
    node = t.put_literal(t.put_datum(b'x' * 2097152))
    publish_result(t, c, t.put_dag(root=node))
'''
    result = run(bind(state, source))
    assert result.outcome == "failure"
    with dml.Repository(state[0]) as repo, repo.read() as tx:
        assert tx.get_ref(result.context.publication_ref) == result.context.pre_dispatch
        outcome = tx.get_node(tx.lookup_node(result.final_attempt, "outcome")).dag
        assert local._scalar(tx, tx.lookup_node(outcome, "reason"), "string") == "child-exit"
        stderr = tx.get_node(tx.lookup_node(outcome, "stderr")).dag
        data = tx.get_datum(tx.get_node(tx.get_dag(stderr).root).datum).value
        assert b"map_full" in data
