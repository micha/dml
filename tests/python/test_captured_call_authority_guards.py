"""Finite ORIGINAL public-positive typed rewrites and LAST native terminal guards.

One original frozen HOST history (two publications/zero OS) supports the batch;
no four-row/deep/installed population. Exact guard errors are the oracles.
"""

from dataclasses import replace

import daggerml as d
from daggerml import builtin as b
import pytest

from captured_call_rewrite import rewrite
from test_exchange_records import clone
from test_captured_call_profiles import case, frozen
from test_captured_calls import app, bridge, leaf, initial


@pytest.mark.parametrize("fault,message", [("decision-role", "decision absent/ambiguous"), ("decision-key", "exact leaf B/E/key"), ("fresh-control", "capture/input/fresh association"), ("slot", "captured target/outer T/slot"), ("phase-role", "preparation phase absent/ambiguous"), ("phase-slot", "preparation exact native association/delta"), ("outer-input", "add Q must consume ORIGINAL exact outer input"), ("dimension-name", "preparation named dimensions"), ("double-upstream", "double THIS actual prior add association")])
def test_ORIGINAL_leaf_public_S_valid_but_exact_outer_authority_rejects(case, tmp_path, fault, message):
    path, got = case
    with d.Repository(path) as repo, repo.read() as tx:
        first = tx.get_dag(got["got"]["calls"][1 if fault == "double-upstream" else 0]).bindings
        slot = b.scalar(tx, first["selection-slot"], "string")
        wrong_input = got["q"].closure["dag"]  # Retained actual DAG, deliberately not owning outer input.
    changed = []
    def corrupt(read, write, old, fields, root):
        original = read.get_dag(old).bindings
        if "role" not in original:
            return fields, root
        role = b.scalar(read, original["role"], "string")
        if role == app.LEAF_D_ROLE and b.scalar(read, original["slot"], "i64") == 1 and fault == "double-upstream":
            fields["upstream"] = write.put_subdag(got["q"].closure["dag"])
        elif role == app.Q_ROLE and fault == "outer-input":
            fields["inputs"] = write.put_subdag(wrong_input)
        elif role == app.LEAF_D_ROLE and b.scalar(read, original["slot"], "i64") == 0 and fault == "dimension-name":
            fields["inputs-name"] = b.literal(write, "wrong-dimension")
        elif role == app.LEAF_D_ROLE and b.scalar(read, original["slot"], "i64") == 0 and fault in ("decision-role", "decision-key", "fresh-control", "slot"):
            name = {"decision-role": "role", "decision-key": "key", "fresh-control": "control", "slot": "slot"}[fault]
            fields[name] = write.put_subdag(got["q"].closure["key"]) if name == "key" else b.literal(write, 1 if name == "slot" else "wrong")
        elif role == app.PHASE_ROLE and b.scalar(read, original["kind"], "string") == "leaf-prepare" and b.scalar(read, original["slot"], "i64") == 0 and fault in ("phase-role", "phase-slot"):
            fields["role" if fault == "phase-role" else "slot"] = b.literal(write, "wrong" if fault == "phase-role" else 1)
        else:
            return fields, root
        changed.append(old)
        return fields, root
    destination = tmp_path / "original-poison"
    bad, _ = rewrite(path, destination, got["final"], corrupt)
    assert changed
    # Unchanged public S/Q/T/F authority stays valid in the coherent native copy.
    positive = app.selection.inspect(destination, commit=bad, slot=slot)
    assert positive.intent_uri == (leaf.DOUBLE if fault == "double-upstream" else leaf.ADD)
    before = (destination / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        app.inspect_leaf_success(destination, commit=bad, slot=slot)
    assert (destination / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("fault,message", [("extra", "terminal delta must add ONLY"), ("role", "unsupported outer outcome role"), ("owner", "owning immutable initial T"), ("calls", "ordered call positions"), ("ledger", "actual call associations"), ("return", "premature/fake outer return")])
def test_LAST_native_completion_shape_owner_ledger_return_exact_guard(case, fault, message):
    path, got = case
    with d.Repository(path) as repo, repo.write() as tx:
        final = got["final"]
        entries = app.tree(tx, final)
        aid = b.scalar(tx, tx.get_dag(got["got"]["initial"]).root, "string")
        name = "outer-completion-" + aid
        completion = entries[name]
        fields = tx.get_dag(completion).bindings
        changes = {}
        if fault == "extra":
            entries["extra"] = got["q"].closure["dag"]
        elif fault == "role":
            changes["role"] = b.literal(tx, "unsupported")
        elif fault == "owner":
            changes["plan"] = tx.put_subdag(got["q"].closure["dag"])
        elif fault in ("calls", "ledger"):
            links = {"slot-00": got["got"]["calls"][0]} if fault == "calls" else {"slot-00": got["got"]["calls"][1], "slot-01": got["got"]["calls"][0]}
            changes["calls"] = tx.put_subdag(b.record(tx, app.LEDGER_ROLE, links=links))
        else:
            changes["return"] = tx.put_subdag(got["q"].closure["dag"])
        new_completion = clone(tx, completion, fields=changes)
        entries[name] = new_completion
        attempt_name = "outer-attempt-" + aid
        entries[attempt_name] = clone(tx, entries[attempt_name], fields={"completion": tx.put_subdag(new_completion)})
        bad = tx.put_commit(tx.put_tree(entries), parents=tx.get_commit(final).parents)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        app.inspect_completion(path, commit=bad)
    assert (path / "data.mdb").read_bytes() == before


def test_native_session_failure_detail_exact_profile(initial, tmp_path):
    path, base = initial
    q = app.record_request(path, commit=base, ref="q")
    session = bridge.Session(path, q, tmp_path / "metadata-session")
    final = session.fail(bridge.SessionError("known cooperative failure"))
    assert app.inspect_completion(path, commit=final)["outcome"] == "failure"
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, final)
        name = "outer-completion-" + session.aid
        bad_completion = clone(tx, entries[name], fields={"detail": b.literal(tx, "x" * 4097)})
        entries[name] = bad_completion
        an = "outer-attempt-" + session.aid
        entries[an] = clone(tx, entries[an], fields={"completion": tx.put_subdag(bad_completion)})
        bad = tx.put_commit(tx.put_tree(entries), parents=tx.get_commit(final).parents)
    with pytest.raises(ValueError, match="session failure detail differs"):
        app.inspect_completion(path, commit=bad)


@pytest.mark.parametrize("fault,message", [("missing-initial", "bounded outer phase spine missing initial"), ("initial-delta", "initial T exact delta differs")])
def test_native_initial_spine_root_and_delta_guard(initial, tmp_path, fault, message):
    path, base = initial
    q = app.record_request(path, commit=base, ref="q")
    session = bridge.Session(path, q, tmp_path / "metadata-session")
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, session.current)
        if fault == "missing-initial":
            bad = tx.put_commit(tx.put_tree(app.tree(tx, base)))
        else:
            entries["extra"] = q.closure["dag"]
            bad = tx.put_commit(tx.put_tree(entries), parents=(q.commit,))
    with pytest.raises(ValueError, match=message):
        app.inspect_spine(path, bad, q.request, session.initial, session.aid, set())


def test_native_outer_W_requires_exact_single_parent(initial):
    path, base = initial
    with d.Repository(path) as repo, repo.write() as tx:
        commit = tx.put_commit(tx.put_tree(app.tree(tx, base)))
    with pytest.raises(ValueError, match="outer W requires one Q parent"):
        app.inspect_reuse(path, commit=commit)


def test_duplicate_outer_selection_slot_is_not_authorization_to_replace(case):
    path, got = case
    with pytest.raises(ValueError, match="absent slot/retained completion"):
        app.select_outer(path, commit=got["reused"].base, completion=got["final"], ref="duplicate")
