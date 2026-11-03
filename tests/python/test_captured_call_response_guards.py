"""Native source/Q and explicitly HOST response-boundary guards; zero OS actors."""

from types import SimpleNamespace
from dataclasses import replace

import daggerml as d
from daggerml import builtin as b
import pytest

from test_captured_calls import app, bridge, leaf, initial


@pytest.mark.parametrize("fault,message", [("source", "child captured binding/environment"), ("Q", "child Q exact computational association")])
def test_actual_native_child_source_Q_refusal_BEFORE_any_callable_record(initial, monkeypatch, fault, message):
    path, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, commit)
        target = leaf.inspect(tx, entries["add-A"], *leaf.sources())
        binding = target["binding"]
        if fault == "source":
            binding = app.local.put_local_binding(tx, source=b"wrong captured entry", interpreter=__import__("sys").executable, timeout_ms=10000)
        q = b.record(tx, "local-python-request-v1", values={"intent": d.Datum.uri(leaf.DOUBLE if fault == "Q" else leaf.ADD)}, links={"binding": binding, "inputs": entries["inputs"]})
        entries.update(binding=binding, request=q)
        native = tx.put_commit(tx.put_tree(entries), parents=(commit,))
    context = SimpleNamespace(repository_path=path, pre_dispatch=native, binding=binding, request=q, inputs=entries["inputs"])
    monkeypatch.setattr(b, "publish_callable", lambda *a, **k: pytest.fail("native source/Q guard BEFORE recording"))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        leaf.publish(context, target["environment"], leaf.ADD, *leaf.sources(), lambda *a: pytest.fail("no logical call"))
    assert (path / "data.mdb").read_bytes() == before


def test_Host_native_spine_response_mismatch_before_ANY_leaf_Q(initial, tmp_path, monkeypatch):
    path, base = initial
    q = app.record_request(path, commit=base, ref="q")
    session = bridge.Session(path, q, tmp_path / "session")
    session.map_get(session.input, "a")
    session.map_get(session.input, "b")
    original = app.inspect_spine
    def mismatch(*a, **k):
        result = original(*a, **k)
        return dict(result, getters=())
    monkeypatch.setattr(app, "inspect_spine", mismatch)
    monkeypatch.setattr(app.ex, "record_exchange_request", lambda *a, **k: pytest.fail("guard before leafQ"))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="actual getter/call guard differs before dispatch"):
        session.invoke(session.tokens[0], session.input)
    assert session.unknown and session.poisoned
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("fault,message", [("owner", "failed leaf witness owner/retention"), ("framing", "failure framing exceeds public profile"), ("public", "failed witness PUBLIC completion differs")])
def test_native_failed_witness_owner_framing_and_PUBLIC_response_boundary(initial, tmp_path, monkeypatch, fault, message):
    path, base = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        q = entries["outer"]  # Ordinary native link identity; this helper only checks exact owner.
        header = b"x" * (app.ex.MAX_DESCRIPTOR_BYTES + 1) if fault == "framing" else b"{}"
        witness = b.record(tx, app.PREFIX + "failure-witness-v1", values={"completion": base.bytes, "expected": header, "job": b"{}", "observation": b"{}"}, links={"request": q})
        entries["witness"] = witness
        commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
    if fault == "owner":
        with d.Repository(path) as repo, repo.read() as tx:
            with pytest.raises(ValueError, match=message):
                app.inspect_failure(tx, commit, witness, entries["inputs"])
    else:
        if fault == "public":
            # HOST public-loader response substitutes only; native witness owner/history is real.
            monkeypatch.setattr(app.ex, "load_exchange_handle", lambda *a: SimpleNamespace(expected=object()))
            monkeypatch.setattr(app.ex, "read_observation", lambda *a, **k: SimpleNamespace(phase="request"))
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match=message):
            app.inspect_failed_witness(path, commit, witness, q)
        assert (path / "data.mdb").read_bytes() == before


def test_typed_native_history_transfer_bound_retained_guard(initial, monkeypatch):
    path, base = initial
    # Scaled private limit exercises the actual native ALL-parent traversal guard;
    # does not claim real-million-object stress or production profile reduction.
    monkeypatch.setattr(app.transfer, "MAX_OBJECTS", 1)
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(ValueError, match="history exceeds transfer profile"):
            app.history(tx, base)
