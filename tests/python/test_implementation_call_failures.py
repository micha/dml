"""Publicly framed HOST failures/UNKNOWN and coherent native associations. ZERO OS children."""

from dataclasses import replace
import errno
import json

import daggerml as d
from daggerml import builtin as b, calls as c, local
import pytest

from test_exchange_records import clone
from test_implementation_calls import initial, host, p, adapter, bridge


def fresh(path, commit, tmp_path, number):
    return adapter.invoke(path, commit=commit, ref="outer-%d" % number, workspace=tmp_path / ("HOST-%d" % number))


@pytest.mark.parametrize("slot", [0, 1])
def test_FIRST_SECOND_public_HOST_failedF_stops_next_and_prior_success_survives(initial, host, tmp_path, monkeypatch, slot):
    path, commit = initial
    launches, owned = [], []
    execute, create = local._execute, adapter.Session
    def remember(*a, **k):
        session = create(*a, **k)
        owned.append(session)
        return session
    def failure(context, source, interpreter, timeout):
        observed = execute(context, source, interpreter, timeout)
        launches.append(context)
        if len(launches) - 1 == slot:
            return local._Observation(7, "child-exit", "HOST nonzero AFTER native publication", observed.stdout, observed.stderr)
        return observed
    monkeypatch.setattr(adapter, "Session", remember)
    monkeypatch.setattr(local, "_execute", failure)
    q = p.record_request(path, commit=commit, ref="outer")
    final = adapter.execute(path, q, workspace=tmp_path / "session")
    got = p.inspect_completion(path, commit=final)
    assert got["outcome"] == "failure" and got["result"] is None
    assert len(launches) == slot + 1 and len(got["calls"]) == slot + 1
    with pytest.raises(ValueError, match="success"):
        p.select_outer(path, commit=final, completion=final, ref="NEVER-select")
    if slot == 1:
        with d.Repository(path) as repo, repo.read() as tx:
            fields = tx.get_dag(got["calls"][0]).bindings
            actual_slot = b.scalar(tx, fields["selection-slot"], "string")
        selected, result = p.inspect_leaf_success(path, commit=final, slot=actual_slot)
        assert result.value == d.Datum.i64(42) and selected.request != q.request
    assert owned[0].failed_call == got["calls"][-1]
    with d.Repository(path) as repo, repo.read() as tx:
        failed = tx.get_dag(got["calls"][-1]).bindings
        pending = tx.get_dag(b.link(tx, failed["pending"])).bindings
        witness = b.link(tx, failed["witness"])
        own_q = b.link(tx, pending["request"])
    received = p.inspect_failed_witness(path, final, witness, own_q)
    assert received.completion.outcome == "failure" and received.completion.reason == "child-exit"
    assert received.completion.exit_code == 7 and received.completion.evidence is not None


@pytest.mark.parametrize("fault", ["wait", "import", "validation", "ack"])
def test_public_boundary_UNKNOWN_no_fake_done_retry_OR_outer_completion(initial, host, tmp_path, monkeypatch, fault):
    path, commit = initial
    q = p.record_request(path, commit=commit, ref="outer")
    owned = []
    create = adapter.Session
    def remember(*a, **k):
        session = create(*a, **k)
        owned.append(session)
        return session
    monkeypatch.setattr(adapter, "Session", remember)
    original_success = p.inspect_leaf_success
    if fault == "wait":
        def unknown(*a):
            raise OSError("HOST unknown direct-child disposition")
        monkeypatch.setattr(local, "_execute", unknown)
    elif fault == "import":
        def refusal(*a, **k):
            raise d.IntegrityError("integrity_error", 1, "HOST public import refusal")
        monkeypatch.setattr(p.ex, "receive_exchange", refusal)
    elif fault == "validation":
        def refusal(*a, **k):
            raise ValueError("HOST public producer validation refusal")
        monkeypatch.setattr(p, "inspect_leaf_success", refusal)
    else:
        commit_tx = d.Transaction.commit
        def lost(tx):
            try:
                entries = p.tree(tx, tx.get_ref("work"))
                target = any(n.startswith("publication-a-") for n in entries)
            except d.NotFoundError:
                target = False
            commit_tx(tx)
            if target:
                raise RuntimeError("HOST postcommit completed-worker ack loss")
        monkeypatch.setattr(d.Transaction, "commit", lost)
    with pytest.raises((RuntimeError, OSError, local.LocalExecutionError, d.DmlError)):
        adapter.execute(path, q, workspace=tmp_path / "session")
    assert len(owned) == 1
    session = owned[0]
    with d.Repository(path) as repo, repo.read() as tx:
        head = tx.get_ref("outer-head-" + session.aid)
        assert p.tree(tx, head)["outer-attempt-" + session.aid] == session.initial
        assert "status" not in tx.get_dag(session.initial).bindings
        for current in p.history(tx, head):
            assert "outer-completion-" + session.aid not in p.tree(tx, current)
        slots = [n for n in p.tree(tx, head) if n.startswith("leaf-witness-")]
    assert len(host) <= 1
    if fault == "validation":
        assert len(slots) == 1  # Durable successful first S survives later verification uncertainty.
        monkeypatch.setattr(p, "inspect_leaf_success", original_success)
        selected, result = p.inspect_leaf_success(path, commit=head, slot=slots[0])
        assert result.value == d.Datum.i64(42)
    if fault == "ack":
        with d.Repository(tmp_path / "session/leaf-0/worker.dml") as repo, repo.read() as tx:
            final = tx.get_ref("work")
            attempts = [v for n, v in p.tree(tx, final).items() if n.startswith("attempt-a-")]
            assert len(attempts) == 1 and b.scalar(tx, tx.get_dag(attempts[0]).bindings["status"], "string") == "done"
        assert not (tmp_path / "session/leaf-0/completion.json").exists()


def test_repeat_getter_is_known_interface_failure_not_native_UNKNOWN(initial, tmp_path):
    path, commit = initial
    q = p.record_request(path, commit=commit, ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    with pytest.raises(c.CallError, match="poison"):
        with session.context:
            session.start()
            session.nodes.map_get(session.input, "a")
            session.nodes.map_get(session.input, "b")
            with pytest.raises(bridge.SessionError, match="getter key"):
                session.nodes.map_get(session.input, "a")
            assert session.poisoned and not session.unknown
    # Check outside the outer exception envelope too: a wrong TypeError cannot satisfy this.
    assert session.poisoned and not session.unknown
    final = session.fail(bridge.SessionError("unsupported repeated getter"))
    assert p.inspect_completion(path, commit=final)["outcome"] == "failure"


def test_caught_facade_error_then_finish_is_conservative_UNKNOWN_no_success(initial, tmp_path):
    path, commit = initial
    q = p.record_request(path, commit=commit, ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    with pytest.raises(RuntimeError, match="UNKNOWN"):
        with session.context:
            session.start()
            with pytest.raises(c.CallError, match="fabricated"):
                session.context.describe(c.Node(d.Datum.i64(42)))
            with pytest.raises(c.CallError, match="poison"):
                session.finish(session.input)
            assert session.unknown and session.poisoned
            session.fail(c.CallError("caught facade error attempted completion"))
    with d.Repository(path) as repo, repo.read() as tx:
        head = tx.get_ref("outer-head-" + session.aid)
        assert p.tree(tx, head)["outer-attempt-" + session.aid] == session.initial
        assert "status" not in tx.get_dag(session.initial).bindings
        assert not any("outer-completion-" + session.aid in p.tree(tx, parent) for parent in p.history(tx, head))


def test_direct_PRE_backend_facade_error_is_unclassified_UNKNOWN_no_terminal(initial, tmp_path):
    path, commit = initial
    q = p.record_request(path, commit=commit, ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    with pytest.raises(c.CallError, match="fabricated") as error:
        with session.context:
            session.start()
            session.context.describe(c.Node(d.Datum.i64(42)))
    assert not session.unknown  # No backend guard classified it yet.
    with pytest.raises(RuntimeError, match="UNKNOWN"):
        session.fail(error.value)
    assert session.unknown and session.poisoned
    with d.Repository(path) as repo, repo.read() as tx:
        head = tx.get_ref("outer-head-" + session.aid)
        assert "status" not in tx.get_dag(session.initial).bindings
        assert "outer-completion-" + session.aid not in p.tree(tx, head)


def test_native_verifier_receipt_association_is_UNKNOWN_not_cooperative_error(initial, tmp_path, monkeypatch):
    path, commit = initial
    q = p.record_request(path, commit=commit, ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    original = session.perform
    def wrong_receipt(*a, **k):
        return tuple(list(original(*a, **k)))  # Equal fields, WRONG THIS-call receipt object.
    monkeypatch.setattr(session, "perform", wrong_receipt)
    with pytest.raises(RuntimeError, match="expected verifier uncertainty"):
        with session.context:
            session.start()
            with pytest.raises(ValueError) as error:
                session.nodes.map_get(session.input, "a")
            assert type(error.value) is ValueError  # SessionError subclass is NOT native uncertainty.
            assert session.unknown and session.poisoned
            raise RuntimeError("expected verifier uncertainty")
    with d.Repository(path) as repo, repo.read() as tx:
        head = tx.get_ref("outer-head-" + session.aid)
        assert "status" not in tx.get_dag(session.initial).bindings
        assert "outer-completion-" + session.aid not in p.tree(tx, head)
    with pytest.raises(RuntimeError, match="UNKNOWN"):
        session.fail(c.CallError("receipt mismatch"))


def test_coherent_OTHER_native_submission_parent_even_lying_response_reject_before_dispatch(initial, tmp_path, monkeypatch):
    path, commit = initial
    original = p.ex.record_exchange_request
    def alternate(path, **kwargs):
        with d.Repository(path) as repo, repo.write() as tx:
            other = tx.put_commit(tx.put_tree(p.tree(tx, kwargs["commit"])), parents=(kwargs["commit"],))
        recorded = original(path, **dict(kwargs, commit=other))
        return replace(recorded, base=kwargs["commit"])
    def forbidden(*a, **k):
        pytest.fail("coherent other submission must reject BEFORE dispatch")
    monkeypatch.setattr(p.ex, "record_exchange_request", alternate)
    monkeypatch.setattr(p.ex, "execute_exchange", forbidden)
    q = p.record_request(path, commit=commit, ref="outer")
    with pytest.raises(RuntimeError, match="UNKNOWN"):
        adapter.execute(path, q, workspace=tmp_path / "session")


@pytest.mark.parametrize("fault", ["pending-control", "leafD-extra", "double-input", "parent-order", "duplicate-getter", "valid-OLD-S-graft"])
def test_native_coherent_wrong_inner_source_phase_producer_BEFORE_later_dispatch(initial, host, tmp_path, monkeypatch, fault):
    path, commit = initial
    first = fresh(path, commit, tmp_path, 1)
    got = p.inspect_completion(path, commit=first.commit)
    with d.Repository(path) as repo, repo.read() as tx:
        old_add = tx.get_dag(got["calls"][0]).bindings
        old_slot = b.scalar(tx, old_add["selection-slot"], "string")
        old_double = tx.get_dag(got["calls"][1]).bindings
        old_pending = tx.get_dag(b.link(tx, old_double["pending"])).bindings
        old_input = b.link(tx, old_pending["inputs"])
    old_selected, _ = p.inspect_leaf_success(path, commit=first.commit, slot=old_slot)
    phase, changed = bridge.Session._phase, []
    def alter(self, kind, **kwargs):
        if not changed:
            if fault in ("pending-control", "leafD-extra") and kind == ("leaf-pending" if fault == "pending-control" else "leaf-prepare"):
                author = kwargs["author"]
                def poisoned(tx, commit):
                    result = author(tx, commit)
                    key = "call" if fault == "pending-control" else "decision"
                    fields = {"control": b.literal(tx, "reuse-selected")} if fault == "pending-control" else {"extra": b.literal(tx, 1)}
                    result[key] = clone(tx, result[key], fields=fields)
                    return result
                kwargs = dict(kwargs, author=poisoned)
                changed.append(kind)
            elif fault == "double-input" and kind == "double-input":
                kwargs = dict(kwargs, author=lambda *a: {"inputs": old_input})
                changed.append(kind)
            elif fault == "parent-order" and kind == "leaf-join":
                put = d.Transaction.put_commit
                def reversed_parents(tx, tree, *, parents=()):
                    return put(tx, tree, parents=tuple(reversed(parents)) if len(parents) == 2 else parents)
                monkeypatch.setattr(d.Transaction, "put_commit", reversed_parents)
                changed.append(kind)
            elif fault == "duplicate-getter" and kind == "get-b":
                kind = "get-a"
                changed.append(kind)
        return phase(self, kind, **kwargs)
    monkeypatch.setattr(bridge.Session, "_phase", alter)
    if fault == "valid-OLD-S-graft":
        def graft(path, **kwargs):
            with d.Repository(path) as repo, repo.write() as tx:
                entries = p.tree(tx, kwargs["commit"])
                entries[kwargs["slot"]] = old_selected.dag
                authored = tx.put_commit(tx.put_tree(entries), parents=(kwargs["commit"],))
                tx.create_ref(kwargs["ref"], authored)
            changed.append("valid-OLD-S")
            return replace(old_selected, commit=authored, slot=kwargs["slot"])
        monkeypatch.setattr(p.selection, "select", graft)
    q = p.record_request(path, commit=first.commit, ref="outer-2")
    with pytest.raises((RuntimeError, ValueError, KeyError)):
        adapter.execute(path, q, workspace=tmp_path / "HOST-2")
    assert changed and len(host) <= 3  # Original2 plus at most THIS add; no later double.


@pytest.mark.parametrize("fault", ["outer-D-action", "outer-Q-binding", "prepare-basis", "getter-prefix"])
def test_public_valid_ORIGINAL_S_but_poisoned_outer_prefix_rejects_fresh_mismatch(initial, host, tmp_path, monkeypatch, fault):
    from captured_call_rewrite import rewrite
    path, commit = initial
    first = fresh(path, commit, tmp_path, 1)
    got = p.inspect_completion(path, commit=first.commit)
    pinned = p.pin_leaf(path, commit=first.commit, call=got["calls"][1], slot=p.DOUBLE_SLOT, ref="pinned")
    changed = []
    def corrupt(read, write, old, fields, root):
        original = read.get_dag(old).bindings
        role = b.scalar(read, original["role"], "string") if "role" in original else None
        if fault == "outer-D-action" and role == p.D_ROLE:
            fields["action"] = b.literal(write, "reuse-selected")
        elif fault == "outer-Q-binding" and role == p.Q_ROLE:
            fields["binding"] = write.put_subdag(first.request.closure["add"]["binding"])
        elif fault == "prepare-basis" and role == p.LEAF_D_ROLE:
            fields["basis"] = b.literal(write, first.request.base.bytes)
        elif fault == "getter-prefix" and role == p.PHASE_ROLE and b.scalar(read, original["kind"], "string") == "get-b":
            fields["kind"] = b.literal(write, "get-a")
        else:
            return fields, root
        changed.append(old)
        return fields, root
    destination = tmp_path / "coherent-poison.dml"
    poisoned, mapping = rewrite(path, destination, pinned, corrupt)
    assert changed
    selected = p.selection.inspect(destination, commit=poisoned, slot=p.DOUBLE_SLOT)
    assert selected.result == got["leaf_result"]  # PUBLIC local S/F remains valid, NEW prefix must reject.
    mismatched = p.prepare_arguments(destination, commit=poisoned, values={"a": 13, "b": 30}, inputs_name="changed", ref="changed")
    before = (destination / "data.mdb").read_bytes()
    for control, inputs_name in (("fresh", "inputs"), ("try-selected", "changed")):
        with pytest.raises(ValueError):
            p.record_request(destination, commit=mismatched, control=control, inputs_name=inputs_name, ref="NEVER")
        assert (destination / "data.mdb").read_bytes() == before
