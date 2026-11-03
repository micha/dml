"""Coherent LAST-phase native state-machine guards; original HOST fixture only."""

import daggerml as d
from daggerml import builtin as b
import pytest

from test_exchange_records import clone
from test_captured_call_profiles import case, frozen
from test_captured_call_history_guards import last_phase
from test_captured_calls import app


@pytest.mark.parametrize("fault,kind,message", [("delta", "get-a", "phase exact tree delta differs"), ("join-order", "leaf-join", "ordered leaf F join parents differ"), ("double-map", "leaf-prepare", "double must use THIS constructed map"), ("upstream", "leaf-prepare", "double THIS upstream S/T/R ledger differs"), ("pending-before-prep", "get-a", "leaf pending without preparation"), ("reuse-before-pending", "leaf-pending", "reuse phase outside pinned reuse call"), ("failed-after-S", "leaf-done", "failed DONE requires pending fresh F")])
def test_LAST_native_phase_semantic_transition_guard(case, fault, kind, message):
    path, got = case
    q, complete = got["q"], got["got"]
    aid = None
    with d.Repository(path) as repo, repo.write() as tx:
        aid = b.scalar(tx, tx.get_dag(complete["initial"]).root, "string")
        commit, name, phase, index = last_phase(tx, got["final"], kind)
        native = tx.get_commit(commit)
        entries = app.tree(tx, commit)
        fields = tx.get_dag(phase).bindings
        changes = {}
        if fault == "delta":
            entries["extra"] = q.closure["dag"]
        elif fault == "join-order":
            # Keep previous-first as the phase's actual declared navigation, but lose F edge.
            native = type(native)(native.tree, (native.parents[0], q.base))
        elif fault in ("double-map", "upstream"):
            assert b.scalar(tx, fields["slot"], "i64") == 1
            decision = b.link(tx, fields["decision"])
            if fault == "double-map":
                # D and phase agree on input; it is not THIS prior double-input map.
                changed = clone(tx, decision, fields={"inputs": tx.put_subdag(q.inputs.dag)})
                changes["inputs"] = tx.put_subdag(q.inputs.dag)
                entries[app.payload_names(aid, index, kind)["inputs"]] = q.inputs.dag
            else:
                changed = clone(tx, decision, fields={"upstream-slot": b.literal(tx, "wrong-upstream")})
            changes["decision"] = tx.put_subdag(changed)
            entries[app.payload_names(aid, index, kind)["decision"]] = changed
        elif fault == "failed-after-S":
            call = b.link(tx, fields["call"])
            cf = tx.get_dag(call).bindings
            changed = b.record(tx, app.CALL_ROLE, values={"status": "failure"}, links={"pending": b.link(tx, cf["pending"]), "witness": q.closure["dag"]})
            changes["call"] = tx.put_subdag(changed)
            entries[app.payload_names(aid, index, kind)["call"]] = changed
        else:
            # Preserve a valid native prefix, append the unsupported semantic transition.
            target_kind = "leaf-pending" if fault == "pending-before-prep" else "leaf-reused"
            if fault == "pending-before-prep":
                # Public Q is the required parent delta, but no preparation phase exists.
                pending_commit, _, pending_phase, _ = last_phase(tx, got["final"], "leaf-pending", 3)
                pending_fields = tx.get_dag(pending_phase).bindings
                call = b.link(tx, pending_fields["call"])
                leaf_q = b.link(tx, tx.get_dag(call).bindings["request"])
                qid = b.scalar(tx, tx.get_dag(leaf_q).root, "string")
                parent_entries = dict(entries, **{"request-" + qid: leaf_q})
                parent = tx.put_commit(tx.put_tree(parent_entries), parents=(commit,))
                entries = parent_entries
                links = {"call": call}
                values = {"submission": parent.bytes}
            else:
                # Legitimate W delta with own Q, but current preparation says fresh.
                call = b.link(tx, fields["call"])
                own_q = b.link(tx, tx.get_dag(call).bindings["request"])
                qid = b.scalar(tx, tx.get_dag(own_q).root, "string")
                w = b.record(tx, "example-explicit-reuse-v1", links={"request": own_q, "attempt": complete["initial"], "result": q.inputs.dag}, root="result")
                parent_entries = dict(entries, **{"reuse-" + qid: w})
                parent = tx.put_commit(tx.put_tree(parent_entries), parents=(commit,))
                entries = parent_entries
                links, values = {"reuse": w}, {"reuse-commit": parent.bytes}
            index += 1
            name = app.phase_name(aid, index)
            phase = b.record(tx, app.PHASE_ROLE, values={"kind": target_kind, "index": index, "previous": parent.bytes, **values}, links={"request": q.request, "initial-attempt": complete["initial"], **links})
            entries.update((app.payload_names(aid, index, target_kind)[n], value) for n, value in links.items())
            native = type(native)(native.tree, (parent,))
        entries[name] = clone(tx, phase, fields=changes)
        bad = tx.put_commit(tx.put_tree(entries), parents=native.parents)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        app.inspect_spine(path, bad, q.request, complete["initial"], aid, set())
    assert (path / "data.mdb").read_bytes() == before
