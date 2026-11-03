"""Coherent native association negatives; host process/response faults labelled separately."""

from dataclasses import replace

import daggerml as d
from daggerml import builtin as b, local
import pytest

from test_exchange_records import clone
from test_captured_calls import app, adapter, bridge, fresh, host, initial, pin_double


@pytest.mark.parametrize("field", ["role", "intent", "key", "environment", "binding", "root", "extra"])
def test_outer_capture_poison_BEFORE_request_even_fresh(initial, field):
    path, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, commit)
        original = entries["outer"]
        changes = {"role": b.literal(tx, "wrong")} if field == "role" else {"intent": b.literal(tx, d.Datum.uri("urn:wrong"))} if field == "intent" else {"extra": b.literal(tx, 1)} if field == "extra" else {field: tx.put_subdag(entries["add-B"])} if field != "root" else {}
        entries["outer"] = clone(tx, original, fields=changes, root=tx.get_dag(original).bindings["binding"] if field == "root" else None)
        corrupt = tx.put_commit(tx.put_tree(entries), parents=(commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.record_request(path, commit=corrupt, ref="bad")
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("fault", ["foreign", "value", "order", "repeat", "arguments", "token", "reserved"])
def test_session_scope_caught_poison_blocks_success(initial, tmp_path, fault):
    path, commit = initial
    q = app.record_request(path, commit=commit, ref="outer")
    session = bridge.Session(path, q, tmp_path / "session")
    if fault == "foreign":
        action = lambda: session.map_get(bridge.Node(session.input.value), "a")
    elif fault == "value":
        session.input._Node__value = d.Datum.i64(42)
        action = lambda: session.map_get(session.input, "a")
    elif fault == "order":
        action = lambda: session.map_get(session.input, "b")
    elif fault == "repeat":
        session.map_get(session.input, "a")
        action = lambda: session.map_get(session.input, "a")
    elif fault == "arguments":
        action = lambda: session.arguments({"x": session.input})
    elif fault == "token":
        session.map_get(session.input, "a")
        session.map_get(session.input, "b")
        action = lambda: session.invoke(object(), session.input)
    else:
        session.seen.update(d.ObjectId(bytes([i]) * 16) for i in range(53))
        action = lambda: session.map_get(session.input, "a")
    with pytest.raises(bridge.SessionError):
        action()
    assert session.poisoned
    with pytest.raises(bridge.SessionError, match="poison"):
        session.finish(session.input)
    failed = session.fail(bridge.SessionError("caught"))
    assert app.inspect_completion(path, commit=failed)["outcome"] == "failure"


@pytest.mark.parametrize("slot", [0, 1])
def test_recorded_inner_failure_stops_next_preserves_prior_success(initial, tmp_path, host, monkeypatch, slot):
    path, commit = initial
    real_host = local._execute
    launches = []
    def failing(context, source, interpreter, timeout):
        result = real_host(context, source, interpreter, timeout)
        launches.append(context)
        if len(launches) - 1 == slot:
            return local._Observation(7, "child-exit", "HOST substitute nonzero after publication", result.stdout, result.stderr)
        return result
    monkeypatch.setattr(local, "_execute", failing)
    q, final, got = fresh(path, commit, tmp_path, 1)
    assert got["outcome"] == "failure" and got["result"] is None
    assert len(launches) == slot + 1 and len(got["calls"]) == slot + 1
    with pytest.raises(ValueError, match="success"):
        app.select_outer(path, commit=final, completion=final, ref="must-not-select")
    if slot == 1:
        with d.Repository(path) as repo, repo.read() as tx:
            first = tx.get_dag(got["calls"][0]).bindings
            slot_name = b.scalar(tx, first["selection-slot"], "string")
        selected, result = app.inspect_leaf_success(path, commit=final, slot=slot_name)
        assert result.value == d.Datum.i64(42)


@pytest.mark.parametrize("fault", ["wait", "import", "validation", "ack"])
def test_uncertainty_no_outer_done_retry_or_synthetic_failure(initial, tmp_path, host, monkeypatch, fault):
    path, commit = initial
    q = app.record_request(path, commit=commit, ref="outer")
    owned = []
    real_session = adapter.Session
    def remember(*args, **kwargs):
        session = real_session(*args, **kwargs)
        owned.append(session)
        return session
    monkeypatch.setattr(adapter, "Session", remember)
    if fault == "wait":
        # HOST substitute for unestablished direct-child disposition, not native process evidence.
        monkeypatch.setattr(local, "_execute", lambda *a: (_ for _ in ()).throw(OSError("unknown wait")))
    elif fault == "import":
        monkeypatch.setattr(app.ex, "receive_exchange", lambda *a, **k: (_ for _ in ()).throw(d.IntegrityError("integrity_error", 1, "HOST import refusal")))
    elif fault == "validation":
        monkeypatch.setattr(app, "inspect_leaf_success", lambda *a, **k: (_ for _ in ()).throw(ValueError("HOST validation refusal")))
    else:
        original = d.Transaction.commit
        def lost(tx):
            try:
                tree = app.tree(tx, tx.get_ref("work"))
                target = any(n.startswith("publication-a-") for n in tree)
            except d.NotFoundError:
                target = False
            original(tx)
            if target:
                raise RuntimeError("HOST postcommit ack loss")
        monkeypatch.setattr(d.Transaction, "commit", lost)
    with pytest.raises((RuntimeError, OSError, local.LocalExecutionError, d.DmlError)):
        adapter.execute(path, q, workspace=tmp_path / "session")
    assert len(owned) == 1
    session = owned[0]
    with d.Repository(path) as repo, repo.read() as tx:
        cq = tx.get_ref("outer")
        assert cq == q.commit
        actual_head = tx.get_ref("outer-head-" + session.aid)
        current = app.tree(tx, actual_head)
        assert current["outer-attempt-" + session.aid] == session.initial
        assert "status" not in tx.get_dag(session.initial).bindings
        # Unlike the ORIGINAL weaker immutable-Q oracle, inspect ALL actual owned-head ancestry.
        for native_commit in app.history(tx, actual_head):
            native = app.tree(tx, native_commit)
            assert "outer-completion-" + session.aid not in native
            for dag in native.values():
                fields = tx.get_dag(dag).bindings
                if "role" in fields and b.scalar(tx, fields["role"], "string") in (app.SUCCESS_ROLE, app.FAILURE_ROLE, app.ERROR_ROLE):
                    assert b.link(tx, fields["initial-attempt"]) != session.initial
    if fault == "ack":
        # Durable LOCAL F is visible despite missing acknowledgment; A/outer remains UNKNOWN.
        worker = tmp_path / "session" / "leaf-0" / "worker.dml"
        with d.Repository(worker) as repo, repo.read() as tx:
            final = tx.get_ref("work")
            attempts = [v for n, v in app.tree(tx, final).items() if n.startswith("attempt-a-")]
            assert len(attempts) == 1
            assert b.scalar(tx, tx.get_dag(attempts[0]).bindings["status"], "string") == "done"
        assert not (tmp_path / "session" / "leaf-0" / "completion.json").exists()
    assert len(host) <= 1


def test_public_response_same_dimensions_wrong_NATIVE_preparation_parent_reject_before_dispatch(initial, tmp_path, monkeypatch):
    path, commit = initial
    q = app.record_request(path, commit=commit, ref="outer")
    original = app.ex.record_exchange_request
    def alternate(path, **kwargs):
        with d.Repository(path) as repo, repo.write() as tx:
            # Coherent unchanged snapshot, but NOT THIS authored preparation parent.
            alt = tx.put_commit(tx.put_tree(app.tree(tx, kwargs["commit"])), parents=(kwargs["commit"],))
        actual = original(path, **dict(kwargs, commit=alt))
        return replace(actual, base=kwargs["commit"])
    monkeypatch.setattr(app.ex, "record_exchange_request", alternate)
    monkeypatch.setattr(app.ex, "execute_exchange", lambda *a, **k: pytest.fail("wrong native parent BEFORE dispatch"))
    with pytest.raises(RuntimeError, match="UNKNOWN"):
        adapter.execute(path, q, workspace=tmp_path / "session")


@pytest.mark.parametrize("fault", ["F-graft", "pending-control", "leafD-extra", "double-input", "parent-order", "duplicate-getter"])
def test_native_coherent_wrong_phase_association_rejected_before_later_dispatch(initial, tmp_path, host, monkeypatch, fault):
    path, commit = initial
    q1, f1, g1 = fresh(path, commit, tmp_path, 1)
    original = bridge.Session._phase
    changed = [False]
    def alter(self, kind, **kwargs):
        if not changed[0]:
            if fault == "F-graft" and kind == "leaf-join":
                with d.Repository(path) as repo, repo.read() as tx:
                    first = tx.get_dag(g1["calls"][0]).bindings
                    slot = b.scalar(tx, first["selection-slot"], "string")
                selected, _ = app.inspect_leaf_success(path, commit=f1, slot=slot)
                kwargs = dict(kwargs, second=selected.completion, values={"completion": selected.completion.bytes})
                changed[0] = True
            elif fault in ("pending-control", "leafD-extra") and kind == ("leaf-pending" if fault == "pending-control" else "leaf-prepare"):
                author = kwargs["author"]
                def poisoned(tx, commit):
                    result = author(tx, commit)
                    key = "call" if fault == "pending-control" else "decision"
                    fields = {"control": b.literal(tx, "reuse-selected")} if fault == "pending-control" else {"extra": b.literal(tx, 1)}
                    result[key] = clone(tx, result[key], fields=fields)
                    return result
                kwargs = dict(kwargs, author=poisoned)
                changed[0] = True
            elif fault == "double-input" and kind == "double-input":
                # Reuse valid FIRST execution's downstream map with equal42 but wrong actual R.
                with d.Repository(path) as repo, repo.read() as tx:
                    cf = tx.get_dag(g1["calls"][1]).bindings
                    pf = tx.get_dag(b.link(tx, cf["pending"])).bindings
                    old_input = b.link(tx, pf["inputs"])
                kwargs = dict(kwargs, author=lambda *a: {"inputs": old_input})
                changed[0] = True
            elif fault == "duplicate-getter" and kind == "get-b":
                kind = "get-a"
                changed[0] = True
            elif fault == "parent-order" and kind == "leaf-join":
                put_commit = d.Transaction.put_commit
                def swapped(tx, tree, *, parents=()):
                    return put_commit(tx, tree, parents=tuple(reversed(parents)) if len(parents) == 2 else parents)
                monkeypatch.setattr(d.Transaction, "put_commit", swapped)
                changed[0] = True
        return original(self, kind, **kwargs)
    monkeypatch.setattr(bridge.Session, "_phase", alter)
    q2 = app.record_request(path, commit=f1, ref="outer-2")
    with pytest.raises((RuntimeError, ValueError, KeyError)):
        adapter.execute(path, q2, workspace=tmp_path / "execution-2")
    assert changed[0]
    assert len(host) <= 3  # At most first new add; no later double after corrupted source/history.


def test_valid_S_same_value_OTHER_F_graft_still_not_THIS_fresh_producer(initial, tmp_path, host, monkeypatch):
    path, commit = initial
    q1, f1, g1 = fresh(path, commit, tmp_path, 1)
    with d.Repository(path) as repo, repo.read() as tx:
        first = tx.get_dag(g1["calls"][0]).bindings
        old_slot = b.scalar(tx, first["selection-slot"], "string")
    old, _ = app.inspect_leaf_success(path, commit=f1, slot=old_slot)
    original = app.selection.select
    changed = []
    def graft(path, **kwargs):
        actual = original(path, **kwargs)
        if not changed:
            with d.Repository(path) as repo, repo.write() as tx:
                entries = app.tree(tx, actual.commit)
                entries[kwargs["slot"]] = old.dag
                coherent = tx.put_commit(tx.put_tree(entries), parents=(kwargs["commit"],))
                tx.update_ref(kwargs["ref"], coherent)
            changed.append(coherent)
            # Fully valid public S/history+equal42, but different ORIGINAL Q/F.
            assert app.selection.inspect(path, commit=coherent, slot=kwargs["slot"]).dag == old.dag
            return replace(old, commit=coherent, slot=kwargs["slot"])
        return actual
    monkeypatch.setattr(app.selection, "select", graft)
    q2 = app.record_request(path, commit=f1, ref="outer-2")
    with pytest.raises(RuntimeError, match="UNKNOWN"):
        adapter.execute(path, q2, workspace=tmp_path / "execution-2")
    assert changed and len(host) == 3


def test_original_recursion_depth_not_reset_by_completion_spine(initial, tmp_path, host):
    path, commit = initial
    _, final, _ = fresh(path, commit, tmp_path, 1)
    with pytest.raises(ValueError, match="chain too deep"):
        app.inspect_completion(path, commit=final, depth=9)


@pytest.mark.parametrize("fault", ["outer-D-action", "outer-Q-binding", "prepare-basis", "getter-prefix"])
@pytest.mark.parametrize("control,inputs_name", [("fresh", "inputs"), ("try-selected", "swapped")])
def test_selected_leaf_ORIGINAL_outer_poison_even_fresh_or_value_mismatch(initial, tmp_path, host, fault, control, inputs_name):
    from captured_call_rewrite import rewrite
    path, commit = initial
    q, final, got = fresh(path, commit, tmp_path, 1)
    pinned = pin_double(path, final, got["calls"][1])
    changed = []
    def corrupt(read, write, old, fields, root):
        original = read.get_dag(old).bindings
        role = b.scalar(read, original["role"], "string") if "role" in original else None
        if fault == "outer-D-action" and role == app.D_ROLE:
            fields["action"] = b.literal(write, "reuse-selected")
        elif fault == "outer-Q-binding" and role == app.Q_ROLE:
            fields["binding"] = write.put_subdag(q.closure["add"]["binding"])
        elif fault == "prepare-basis" and role == app.LEAF_D_ROLE:
            fields["basis"] = b.literal(write, q.base.bytes)
        elif fault == "getter-prefix" and role == app.PHASE_ROLE and b.scalar(read, original["kind"], "string") == "get-b":
            fields["kind"] = b.literal(write, "get-a")
        else:
            return fields, root
        changed.append(old)
        return fields, root
    poisoned_path = tmp_path / "coherent-poison"
    bad, mapping = rewrite(path, poisoned_path, pinned, corrupt)
    assert changed
    # Positive control: the OLD public S/Q/T/F framing is fully valid in this rewritten history.
    selected = app.selection.inspect(poisoned_path, commit=bad, slot=app.DOUBLE_SLOT)
    assert selected.result == got["leaf_result"]
    before = (poisoned_path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.record_request(poisoned_path, commit=bad, control=control, inputs_name=inputs_name, ref="must-not-record")
    assert (poisoned_path / "data.mdb").read_bytes() == before


def test_ACTUAL_retained_selected_ancestry_reaches8_next_edge9_rejected_BEFORE_Q(initial, tmp_path, host, monkeypatch):
    path, commit = initial
    depths = []
    original = app.authority_depth
    def measured(depth):
        depths.append(depth)
        return original(depth)
    monkeypatch.setattr(app, "authority_depth", measured)
    for number in range(1, 4):
        _, final, got = fresh(path, commit, tmp_path, number)
        selected = app.select_outer(path, commit=final, completion=final, slot="choice-%d" % number, ref="choice-%d" % number)
        with d.Repository(path) as repo, repo.write() as tx:
            entries = app.tree(tx, selected)
            entries[app.SLOT] = entries["choice-%d" % number]
            commit = tx.put_commit(tx.put_tree(entries), parents=(selected,))
            tx.create_ref("selected-%d" % number, commit)
    assert len(host) == 6 and max(depths) == 8
    # Actual OLD choices/producing requests form the ancestry; entry depth stays zero.
    before = (path / "data.mdb").read_bytes()
    depths.clear()
    with pytest.raises(ValueError, match="chain too deep"):
        app.record_request(path, commit=commit, ref="must-not-create-q4")
    assert max(depths) == 9 and len(host) == 6
    assert (path / "data.mdb").read_bytes() == before
