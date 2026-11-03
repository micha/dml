"""Native selection retention/return metadata and short guarded prefix boundaries."""

import daggerml as d
from daggerml import builtin as b
import pytest

from test_exchange_records import clone
from test_captured_call_profiles import case, frozen
from test_captured_call_history_guards import last_phase
from test_captured_calls import app


@pytest.mark.parametrize("fault,message", [("unretained", "F not retained by ALL-parent history"), ("attempt", "selection ORIGINAL completion differs")])
def test_native_outer_selection_retention_and_ORIGINAL_exact_claim(case, fault, message):
    path, got = case
    with d.Repository(path) as repo, repo.write() as tx:
        base = got["reused"].base
        entries = app.tree(tx, base)
        old_s = entries[app.SLOT]
        if fault == "unretained":
            # All linked ordinary S fields can be retained without retaining F as parent.
            entries = app.tree(tx, got["q"].base)
            entries[app.SLOT] = old_s
            bad = tx.put_commit(tx.put_tree(entries), parents=(got["q"].base,))
        else:
            entries[app.SLOT] = clone(tx, old_s, fields={"attempt": tx.put_subdag(got["got"]["initial"])})
            bad = tx.put_commit(tx.put_tree(entries), parents=(base,))
    with pytest.raises(ValueError, match=message):
        app.inspect_selection(path, commit=bad)


def test_native_outer_return_owner_exact_guard_AFTER_coherent_return_phase(case):
    path, got = case
    q, complete = got["q"], got["got"]
    with d.Repository(path) as repo, repo.write() as tx:
        current, phase_name, phase, index = last_phase(tx, got["final"], "returned")
        aid = b.scalar(tx, tx.get_dag(complete["initial"]).root, "string")
        old_r = b.link(tx, tx.get_dag(phase).bindings["return"])
        new_r = clone(tx, old_r, fields={"request": tx.put_subdag(q.closure["dag"])})
        entries = app.tree(tx, current)
        entries[phase_name] = clone(tx, phase, fields={"return": tx.put_subdag(new_r)})
        entries[app.payload_names(aid, index, "returned")["return"]] = new_r
        parent = tx.put_commit(tx.put_tree(entries), parents=tx.get_commit(current).parents)
        final = app.tree(tx, got["final"])
        final.update(entries)
        name, an = "outer-completion-" + aid, "outer-attempt-" + aid
        changed = clone(tx, final[name], fields={"return": tx.put_subdag(new_r)})
        final[name] = changed
        final[an] = clone(tx, got["got"]["attempt"], fields={"completion": tx.put_subdag(changed)})
        bad = tx.put_commit(tx.put_tree(final), parents=(parent,))
    with pytest.raises(ValueError, match="outer return exact leaf R/owner/ledger differs"):
        app.inspect_completion(path, commit=bad)


def test_native_INITIAL_T_plan_must_equal_actual_fresh_Q_before_prefix(case):
    path, got = case
    with d.Repository(path) as repo, repo.write() as tx:
        q = got["q"]
        initial = clone(tx, got["got"]["initial"], fields={"plan": tx.put_subdag(q.closure["dag"])})
        aid = b.scalar(tx, tx.get_dag(initial).root, "string")
        entries = app.tree(tx, q.commit)
        entries["outer-attempt-" + aid] = initial
        bad = tx.put_commit(tx.put_tree(entries), parents=(q.commit,))
    with pytest.raises(ValueError, match="ORIGINAL fresh outer Q/initial T/plan authority"):
        app.inspect_spine(path, bad, q.request, initial, aid, set())


def test_native_phase_after_recorded_return_is_rejected(case):
    path, got = case
    q, complete = got["q"], got["got"]
    with d.Repository(path) as repo, repo.write() as tx:
        parent, _, _, index = last_phase(tx, got["final"], "returned")
        aid = b.scalar(tx, tx.get_dag(complete["initial"]).root, "string")
        entries = app.tree(tx, parent)
        node = complete["getters"][0]
        index += 1
        phase = b.record(tx, app.PHASE_ROLE, values={"kind": "get-a", "index": index, "previous": parent.bytes}, links={"request": q.request, "initial-attempt": complete["initial"], "node": node})
        entries[app.phase_name(aid, index)] = phase
        entries[app.payload_names(aid, index, "get-a")["node"]] = node
        bad = tx.put_commit(tx.put_tree(entries), parents=(parent,))
    with pytest.raises(ValueError, match="phase follows terminal result/failure"):
        app.inspect_spine(path, bad, q.request, complete["initial"], aid, set())
