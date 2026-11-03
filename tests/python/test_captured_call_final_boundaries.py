"""Remaining delegate boundaries; HOST substitutions explicitly not native corruption."""

from dataclasses import replace
from types import SimpleNamespace
import inspect

import daggerml as d
from daggerml import builtin as b, local
import pytest

from test_captured_call_profiles import case, frozen
from test_captured_calls import app, adapter, bridge, leaf, initial
from test_captured_call_history_guards import last_phase


def test_ORIGINAL_double_native_positive_then_HOST_upstream_response_mismatch(case, monkeypatch):
    path, got = case
    with d.Repository(path) as repo, repo.read() as tx:
        fields = tx.get_dag(got["got"]["calls"][1]).bindings
        slot = b.scalar(tx, fields["selection-slot"], "string")
    selected, _ = app.inspect_leaf_success(path, commit=got["final"], slot=slot)
    with d.Repository(path) as repo, repo.read() as tx:
        pre = tx.get_commit(selected.completion).parents[0]
        cq = tx.get_commit(pre).parents[0]
        dc = tx.get_commit(cq).parents[0]
        prior = app.tree(tx, tx.get_commit(dc).parents[0])
        decision = next(v for n, v in app.tree(tx, dc).items() if n not in prior and "role" in tx.get_dag(v).bindings and b.scalar(tx, tx.get_dag(v).bindings["role"], "string") == app.LEAF_D_ROLE)
        df = tx.get_dag(decision).bindings
        basis, upstream_slot = app.oid(tx, df["basis"]), b.scalar(tx, df["upstream-slot"], "string")
    original = app.inspect_leaf_success
    def wrong(*args, **kwargs):
        actual, result = original(*args, **kwargs)
        if kwargs["commit"] == basis and kwargs["slot"] == upstream_slot and inspect.currentframe().f_back.f_code.co_name == "inspect_leaf_success":
            actual = replace(actual, result=got["q"].closure["dag"])
        return actual, result
    monkeypatch.setattr(app, "inspect_leaf_success", wrong)
    with pytest.raises(ValueError, match="ORIGINAL requested source/producer differs"):
        app.inspect_leaf_success(path, commit=got["final"], slot=slot)


@pytest.mark.parametrize("fault,message", [("observation", "public completion/observation differs"), ("selection", "actual S must follow THIS joined phase")])
def test_HOST_exchange_return_and_selection_response_exact_boundary(case, tmp_path, monkeypatch, fault, message):
    path, got = case
    with d.Repository(path) as repo, repo.read() as tx:
        cf = tx.get_dag(got["got"]["calls"][0]).bindings
        pending = b.link(tx, cf["pending"])
        pf = tx.get_dag(pending).bindings
        request = b.link(tx, pf["request"])
        slot_name = b.scalar(tx, cf["selection-slot"], "string")
    selected, _ = app.inspect_leaf_success(path, commit=got["final"], slot=slot_name)
    with d.Repository(path) as repo, repo.read() as tx:
        pre = tx.get_commit(selected.completion).parents[0]
        cq = tx.get_commit(pre).parents[0]
        qid = b.scalar(tx, tx.get_dag(request).root, "string")
        aid = b.scalar(tx, tx.get_dag(got["got"]["initial"]).root, "string")
        dimensions = app.payload_names(aid, 2, "leaf-prepare")
        selected_phase, _, _, _ = last_phase(tx, got["final"], "leaf-selected", 5)
        s_commit = tx.get_commit(selected_phase).parents[0]
        joined = tx.get_commit(s_commit).parents[0]
    if fault == "selection":
        with d.Repository(path) as repo, repo.write() as tx:
            tx.create_ref("leaf-selected-" + aid + "-0", got["q"].base)
    # Real independently public-validated submission descriptors. External calls below are HOST.
    spec = app.public_prepare(path, cq, dimensions["binding"], dimensions["inputs"], selected.intent_uri, request)
    workspace = tmp_path / "HOST-delegate"
    workspace.mkdir()
    recorded = SimpleNamespace(commit=cq, request=request, binding_name=dimensions["binding"],
        inputs_name=dimensions["inputs"], intent_uri=selected.intent_uri)
    context = SimpleNamespace(request=request, pre_dispatch=pre, attempt=d.ObjectId(bytes=b"t" * 16),
        binding=selected.binding, inputs=selected.inputs)
    run = SimpleNamespace(outcome="success", cleanup="ok", final_commit=selected.completion, attempt_id="a-HOST", context=context)
    session = bridge.Session.__new__(bridge.Session)
    session.path, session.workspace, session.aid = path, workspace, aid
    session.current = joined if fault == "selection" else got["final"]
    session.receipt = lambda *a: None
    session.seen = set()
    monkeypatch.setattr(app.ex, "prepare_exchange", lambda *a, **k: spec)
    monkeypatch.setattr(app.ex, "save_exchange_handle", lambda *a: None)
    monkeypatch.setattr(app.ex, "execute_exchange", lambda *a: run)
    monkeypatch.setattr(app.ex, "observe_exchange", lambda *a, **k: SimpleNamespace(snapshot=SimpleNamespace(commit=got["q"].base if fault == "observation" else selected.completion)))
    monkeypatch.setattr(app.ex, "receive_exchange", lambda *a, **k: SimpleNamespace(commit=selected.completion, outcome="success"))
    monkeypatch.setattr(session, "_phase", lambda *a, **k: None)
    if fault == "selection":
        monkeypatch.setattr(app.selection, "select", lambda *a, **k: replace(selected, commit=s_commit))
    else:
        monkeypatch.setattr(app.selection, "select", lambda *a, **k: pytest.fail("wrong observed F BEFORE S"))
    with pytest.raises((ValueError, KeyError), match=message):
        session._execute(recorded, pending, 0)


def test_recorded_failure_native_positive_then_HOST_wrong_PUBLIC_F_response(initial, tmp_path, monkeypatch):
    path, base = initial
    # ONE finite HOST runner refusal, zero logical source execution/publication/OS children.
    monkeypatch.setattr(local, "_execute", lambda *a: local._Observation(7, "child-exit", "HOST refusal", (b"", 0), (b"", 0)))
    q = app.record_request(path, commit=base, ref="q")
    final = adapter.execute(path, q, workspace=tmp_path / "failure")
    got = app.inspect_completion(path, commit=final)
    assert got["outcome"] == "failure" and len(got["calls"]) == 1
    original = app.inspect_failed_witness
    def wrong(*a, **k):
        actual = original(*a, **k)
        return replace(actual, commit=base)  # HOST descriptor corruption AFTER public failure proof.
    monkeypatch.setattr(app, "inspect_failed_witness", wrong)
    with pytest.raises(ValueError, match="failed call witness must certify THIS joined F"):
        app.inspect_completion(path, commit=final)
