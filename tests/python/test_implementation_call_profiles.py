"""Native exact final/return/request/reuse shapes; no forced predicates or new OS child.

Each group owns one actual HOST-generated native history, then writes independent
well-typed corrupt profile variants and checks their specific rejection boundaries.
"""

import daggerml as d
from daggerml import builtin as b
import pytest

from test_exchange_records import clone
from test_implementation_calls import initial, host, p, adapter


def test_native_terminal_delta_T_completion_return_and_call_ledgers(initial, host, tmp_path):
    path, commit = initial
    result = adapter.invoke(path, commit=commit, ref="outer", workspace=tmp_path / "HOST")
    good = p.inspect_completion(path, commit=result.commit)
    with d.Repository(path) as repo, repo.read() as tx:
        final = p.tree(tx, result.commit)
        before = tx.get_commit(result.commit).parents[0]
        aid = b.scalar(tx, tx.get_dag(good["attempt"]).root, "string")
        completion_name = "outer-completion-" + aid
        completion = final[completion_name]
        cf = tx.get_dag(completion).bindings
        ledger = b.link(tx, cf["calls"])
    cases = ("parents", "delta", "outcome-role", "completion-initial", "final-status", "final-occurrence", "final-completion", "tree",
             "ledger-count", "ledger-order", "premature-return", "return-value", "return-owner", "return-call", "return-getter")
    for fault in cases:
        with d.Repository(path) as repo, repo.write() as tx:
            entries, parents = dict(final), (before,)
            t, finished = good["attempt"], completion
            if fault == "parents":
                parents = (before, result.request.commit)
            elif fault == "delta":
                entries["additional-unexpected"] = result.request.closure["dag"]
            elif fault == "outcome-role":
                finished = clone(tx, completion, fields={"role": b.literal(tx, "unsupported-outcome")})
            elif fault == "completion-initial":
                finished = clone(tx, completion, fields={"plan": tx.put_subdag(result.request.closure["dag"])})
            elif fault.startswith("final-"):
                fields, root = {}, None
                if fault == "final-status":
                    fields["status"] = b.literal(tx, "working")
                elif fault == "final-occurrence":
                    root = b.literal(tx, "ia-" + "f" * 32)
                else:
                    fields["completion"] = tx.put_subdag(result.request.closure["dag"])
                t = clone(tx, t, fields=fields, root=root)
            elif fault == "tree":
                entries["inputs"] = result.request.closure["dag"]
            elif fault.startswith("ledger"):
                links = {"slot-00": good["calls"][0]} if fault == "ledger-count" else {"slot-00": good["calls"][1], "slot-01": good["calls"][0]}
                changed = b.record(tx, p.LEDGER_ROLE, links=links)
                finished = clone(tx, completion, fields={"calls": tx.put_subdag(changed)})
            elif fault == "premature-return":
                finished = clone(tx, completion, fields={"return": tx.put_subdag(good["leaf_result"])})
            else:
                changes = {"value": b.literal(tx, 85)} if fault == "return-value" else {
                    "request" if fault == "return-owner" else "call0" if fault == "return-call" else "getter0": tx.put_subdag(result.request.closure["dag"])}
                invalid = clone(tx, good["result"], fields=changes)
                finished = clone(tx, completion, fields={"return": tx.put_subdag(invalid)})
            if finished != completion and fault != "final-completion":
                t = clone(tx, t, fields={"completion": tx.put_subdag(finished)})
            entries["outer-attempt-" + aid], entries[completion_name] = t, finished
            changed = tx.put_commit(tx.put_tree(entries), parents=parents)
        with pytest.raises(ValueError):
            p.inspect_completion(path, commit=changed)
    assert len(host) == 2
    assert p.inspect_completion(path, commit=result.commit) == good


def test_native_own_request_plan_and_exact_two_commit_delta(initial):
    path, commit = initial
    q = p.record_request(path, commit=commit, ref="outer")
    with d.Repository(path) as repo, repo.read() as tx:
        qf = tx.get_dag(q.request).bindings
        decision = b.link(tx, qf["decision"])
        dc = tx.get_commit(q.commit).parents[0]
        basis = tx.get_commit(dc).parents[0]
        dc_entries, cq_entries = p.tree(tx, dc), p.tree(tx, q.commit)
    cases = ("role", "occurrence", "tree-Q", "tree-D", "Q-binding", "Q-intent", "D-binding", "D-value", "D-action", "plan-basis", "plan-control", "unrelated", "parents")
    for fault in cases:
        with d.Repository(path) as repo, repo.write() as tx:
            de, qe = dict(dc_entries), dict(cq_entries)
            changes, root = {}, None
            changed_decision, changed_plan = decision, q.plan
            if fault == "role":
                changes["role"] = b.literal(tx, "wrong")
            elif fault == "occurrence":
                root = b.literal(tx, "not-an-occurrence")
            elif fault in ("Q-binding", "Q-intent"):
                changes = {"binding": tx.put_subdag(q.closure["add"]["binding"])} if fault == "Q-binding" else {"intent": b.literal(tx, d.Datum.uri("urn:other:intent"))}
            elif fault.startswith("D-"):
                fields = {"binding": tx.put_subdag(q.closure["add"]["binding"])} if fault == "D-binding" else {"value": b.literal(tx, 42)} if fault == "D-value" else {"action": b.literal(tx, "reuse-selected")}
                changed_decision = clone(tx, decision, fields=fields)
            elif fault.startswith("plan-"):
                fields = {"basis": b.literal(tx, q.commit.bytes)} if fault == "plan-basis" else {"add-control": b.literal(tx, "not-control")}
                changed_plan = clone(tx, q.plan, fields=fields)
                changed_decision = clone(tx, decision, fields={"plan": tx.put_subdag(changed_plan)})
            if changed_decision != decision:
                changes["decision"] = tx.put_subdag(changed_decision)
                de["decision-" + q.request_id] = changed_decision
            if fault == "tree-D":
                de["decision-" + q.request_id] = q.closure["dag"]
            changed_dc = tx.put_commit(tx.put_tree(de), parents=(basis,))
            changed_q = clone(tx, q.request, fields=changes, root=root)
            qe["decision-" + q.request_id] = de["decision-" + q.request_id]
            qe["outer-request-" + q.request_id] = q.closure["dag"] if fault == "tree-Q" else changed_q
            if fault == "unrelated":
                qe["inputs"] = q.closure["dag"]
            changed_cq = tx.put_commit(tx.put_tree(qe), parents=(changed_dc, basis) if fault == "parents" else (changed_dc,))
        with pytest.raises((ValueError, KeyError)):
            p.inspect_request(path, commit=changed_cq, request=changed_q)


def test_native_outer_W_and_selection_exact_old_producer_root_refs(initial, host, tmp_path):
    path, commit = initial
    first = adapter.invoke(path, commit=commit, ref="outer", workspace=tmp_path / "HOST")
    selected = p.select_outer(path, commit=first.commit, completion=first.commit, ref="selected")
    q = p.record_request(path, commit=selected, closure_name="outer-B", control="require-selected", ref="reused")
    with d.Repository(path) as repo, repo.read() as tx:
        entries = p.tree(tx, q.reused)
        name = "outer-reuse-" + q.request_id
        w = entries[name]
        fields = tx.get_dag(w).bindings
        selection = entries[p.SLOT]
    for fault in ("request", "decision", "selection", "attempt", "result", "role", "root", "tree", "parent", "two-parents"):
        with d.Repository(path) as repo, repo.write() as tx:
            current, root, changes = dict(entries), None, {}
            if fault in ("request", "decision", "selection", "attempt", "result"):
                changes[fault] = tx.put_subdag(q.closure["dag"])
                if fault == "result":
                    root = changes[fault]
            elif fault == "role":
                changes["role"] = b.literal(tx, "wrong")
            elif fault == "root":
                root = fields["request"]
            elif fault == "tree":
                current["extra"] = w
            current[name] = clone(tx, w, fields=changes, root=root)
            parents = (selected,) if fault == "parent" else (q.commit, selected) if fault == "two-parents" else (q.commit,)
            bad = tx.put_commit(tx.put_tree(current), parents=parents)
        with pytest.raises((ValueError, KeyError)):
            p.inspect_reuse(path, commit=bad)
    # Selection is independently bound to ORIGINAL F/Q/T/R, not equal result or request B.
    for fault in ("completion", "request", "attempt", "result", "closure"):
        with d.Repository(path) as repo, repo.write() as tx:
            current = p.tree(tx, selected)
            changes = {"completion": b.literal(tx, selected.bytes)} if fault == "completion" else {fault: tx.put_subdag(q.closure["dag"])}
            current[p.SLOT] = clone(tx, selection, fields=changes, root=changes["result"] if fault == "result" else None)
            bad = tx.put_commit(tx.put_tree(current), parents=(selected,))
        with pytest.raises((ValueError, KeyError)):
            p.inspect_selection(path, commit=bad)
    assert len(host) == 2
