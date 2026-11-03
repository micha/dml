"""Targeted native prefix/profile guards over ONE frozen original HOST history.

Each corruption is the LAST snapshot under inspection: no inconsistent descendant
hashes hide a guard behind a generic tree-delta failure. No four-row/deep replay.
"""

import daggerml as d
from daggerml import builtin as b
import pytest

from test_exchange_records import clone
from test_captured_call_profiles import case, frozen
from test_captured_calls import app, bridge


def last_phase(tx, final, kind, slot=None):
    pending = [final]
    seen = set()
    while pending:
        commit = pending.pop()
        if commit in seen:
            continue
        seen.add(commit)
        native = tx.get_commit(commit)
        if native.parents:
            old, current = app.tree(tx, native.parents[0]), app.tree(tx, commit)
            for name in set(current) - set(old):
                if name.startswith("phase-ca-"):
                    fields = tx.get_dag(current[name]).bindings
                    if b.scalar(tx, fields["kind"], "string") == kind:
                        index = b.scalar(tx, fields["index"], "i64")
                        if slot is None or index == slot:
                            return commit, name, current[name], index
        pending.extend(native.parents)
    raise AssertionError("actual original phase missing: " + kind)


CASES = [
    ("unknown-kind", "get-a", "unknown phase"),
    ("previous", "get-a", "ordinal/owner/previous"),
    ("payload", "get-a", "payload association"),
    ("nonconsecutive", "get-b", "positions not consecutive"),
    ("get-b-first", "get-a", "getter order"),
    ("getter-key", "get-a", "order/I64"),
    ("getter-binding", "get-a", "source/binding"),
    ("premature-map", "get-a", "before actual successful add"),
    ("literal-map", "double-input", "exact returned add R"),
    ("prepare-before-getters", "get-a", "before getter checks"),
    ("D-key", "leaf-prepare", "exact B/E/key"),
    ("D-name", "leaf-prepare", "basis/named dimensions"),
    ("D-owner", "leaf-prepare", "owner/capture/input"),
    ("forward", "leaf-prepare", "SAME original"),
    ("D-action", "leaf-prepare", "actual pinned plan"),
    ("pending-owner", "leaf-pending", "exact owner/target/input"),
    ("pending-submission", "leaf-pending", "submission differs"),
    ("join-before-pending", "leaf-prepare", "outside pending fresh"),
    ("selected-before-join", "leaf-pending", "before exact fresh join"),
    ("S-commit", "leaf-selected", "THIS joined F"),
    ("selection-publication", "leaf-selected", "selected phase publication"),
    ("selection-tree", "leaf-selected", "S tree differs"),
    ("done-before-pending", "get-a", "without pending completion"),
    ("return-before-calls", "get-a", "before both successful"),
    ("status", "leaf-done", "final status"),
    ("done-pending", "leaf-done", "pending association"),
    ("done-S", "leaf-done", "prior S phase"),
    ("done-attempt", "leaf-done", "ORIGINAL S/T/R"),
]


@pytest.mark.parametrize("fault,kind,message", CASES)
def test_actual_last_native_prefix_guard(case, fault, kind, message):
    path, original = case
    q, got = original["q"], original["got"]
    with d.Repository(path) as repo, repo.write() as tx:
        commit, phase_name, phase_dag, index = last_phase(tx, original["final"], kind, 2 if kind == "leaf-prepare" else 3 if kind == "leaf-pending" else 5 if kind == "leaf-selected" else 6 if kind == "leaf-done" else None)
        native = tx.get_commit(commit)
        entries = app.tree(tx, commit)
        fields = tx.get_dag(phase_dag).bindings
        aid = b.scalar(tx, tx.get_dag(got["initial"]).root, "string")
        changes = {}
        replacement_kind = None
        link_updates = {}
        if fault == "unknown-kind":
            changes["kind"] = b.literal(tx, "unsupported")
        elif fault == "previous":
            changes["previous"] = b.literal(tx, q.base.bytes)
        elif fault == "payload":
            entries[app.payload_names(aid, index, kind)["node"]] = q.inputs.dag
        elif fault == "nonconsecutive":
            changes["index"] = b.literal(tx, 7)
            del entries[phase_name]
            phase_name = app.phase_name(aid, 7)
            old_payload = app.payload_names(aid, index, kind)["node"]
            entries[app.payload_names(aid, 7, kind)["node"]] = entries.pop(old_payload)
        elif fault == "get-b-first":
            replacement_kind = "get-b"
        elif fault == "getter-key":
            with b.Recorder(tx, commit=native.parents[0]) as rec:
                args = rec.arguments({"map": rec.load(q.inputs.dag), "key": rec.literal(d.Datum.string("b"))})
                link_updates["node"] = rec.dag(rec.call(b.MAP_GET, q.closure["map_binding"], args))
        elif fault == "getter-binding":
            with b.Recorder(tx, commit=native.parents[0]) as rec:
                args = rec.arguments({"map": rec.load(q.inputs.dag), "key": rec.literal(d.Datum.string("a"))})
                link_updates["node"] = rec.dag(rec.call(b.MAP_GET, app.tree(tx, commit)["map-v2"], args))
        elif fault == "literal-map":
            with b.Recorder(tx, commit=native.parents[0]) as rec:
                link_updates["inputs"] = rec.dag(rec.arguments({"x": rec.literal(d.Datum.i64(42))}))
        elif fault.startswith("D-"):
            decision = b.link(tx, fields["decision"])
            name = {"D-key": "key", "D-name": "inputs-name", "D-owner": "outer-request", "D-action": "control"}[fault]
            node = b.literal(tx, "wrong") if fault in ("D-name", "D-action") else tx.put_subdag(q.closure["dag"])
            link_updates["decision"] = clone(tx, decision, fields={name: node})
        elif fault == "forward":
            link_updates["binding"] = q.closure["double"]["binding"]
        elif fault == "pending-owner":
            link_updates["call"] = clone(tx, b.link(tx, fields["call"]), fields={"slot": b.literal(tx, 1)})
        elif fault == "pending-submission":
            changes["submission"] = b.literal(tx, q.commit.bytes)
        elif fault == "S-commit":
            link_updates["selection"] = clone(tx, b.link(tx, fields["selection"]), fields={"completion": b.literal(tx, q.base.bytes)})
        elif fault == "selection-publication":
            changes["selection-commit"] = b.literal(tx, q.base.bytes)
        elif fault == "selection-tree":
            # Actual S phase/body agree, but original parent tree's slot does NOT.
            previous = app.tree(tx, native.parents[0])
            slot = b.scalar(tx, fields["selection-slot"], "string")
            previous[slot] = q.closure["dag"]
            parent = tx.put_commit(tx.put_tree(previous), parents=tx.get_commit(native.parents[0]).parents)
            entries[slot] = q.closure["dag"]
            native = type(native)(native.tree, (parent,))
            changes["previous"] = b.literal(tx, parent.bytes)
            changes["selection-commit"] = b.literal(tx, parent.bytes)
        elif fault in ("done-pending", "done-S", "done-attempt", "status"):
            name = {"status": "status", "done-pending": "pending", "done-S": "selection", "done-attempt": "attempt"}[fault]
            node = b.literal(tx, "unsupported") if name == "status" else tx.put_subdag(q.closure["dag"])
            link_updates["call"] = clone(tx, b.link(tx, fields["call"]), fields={name: node})
        else:
            replacement_kind = {"premature-map": "double-input", "prepare-before-getters": "leaf-prepare",
                "join-before-pending": "leaf-join", "selected-before-join": "leaf-selected",
                "done-before-pending": "leaf-done", "return-before-calls": "returned"}[fault]
        if replacement_kind:
            for name in app.payload_names(aid, index, kind).values():
                del entries[name]
            common = {n: fields[n] for n in ("role", "request", "initial-attempt", "index", "previous")}
            common["kind"] = b.literal(tx, replacement_kind)
            for name in app.PHASE_LINKS[replacement_kind]:
                common[name] = tx.put_subdag(q.inputs.dag)
                entries[app.payload_names(aid, index, replacement_kind)[name]] = q.inputs.dag
            for name in app.PHASE_VALUES[replacement_kind]:
                common[name] = b.literal(tx, 0 if name == "slot" else "slot" if name == "selection-slot" else native.parents[0].bytes)
            if replacement_kind == "leaf-join":
                common["completion"] = b.literal(tx, q.base.bytes)
                native = type(native)(native.tree, (native.parents[0], q.base))
            if fault == "selected-before-join":
                # Keep the original valid pending prefix; insert an S delta WITHOUT F join.
                entries = app.tree(tx, commit)
                published = dict(entries, slot=q.inputs.dag)
                parent = tx.put_commit(tx.put_tree(published), parents=(commit,))
                entries = published
                index += 1
                phase_name = app.phase_name(aid, index)
                common["index"] = b.literal(tx, index)
                common["previous"] = b.literal(tx, parent.bytes)
                common["selection-commit"] = b.literal(tx, parent.bytes)
                entries[app.payload_names(aid, index, replacement_kind)["selection"]] = q.inputs.dag
                native = type(native)(native.tree, (parent,))
            phase = tx.put_dag(root=tx.get_dag(phase_dag).root, bindings=common)
        else:
            if fault == "S-commit":
                # Parent S delta and actual phase payload agree; only S's F is wrong.
                previous = app.tree(tx, native.parents[0])
                slot = b.scalar(tx, fields["selection-slot"], "string")
                previous[slot] = link_updates["selection"]
                parent = tx.put_commit(tx.put_tree(previous), parents=tx.get_commit(native.parents[0]).parents)
                entries[slot] = link_updates["selection"]
                native = type(native)(native.tree, (parent,))
                changes["previous"] = b.literal(tx, parent.bytes)
                changes["selection-commit"] = b.literal(tx, parent.bytes)
            for name, dag in link_updates.items():
                changes[name] = tx.put_subdag(dag)
                entries[app.payload_names(aid, 7 if fault == "nonconsecutive" else index, kind)[name]] = dag
            phase = clone(tx, phase_dag, fields=changes)
        entries[phase_name] = phase
        bad = tx.put_commit(tx.put_tree(entries), parents=native.parents)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        app.inspect_spine(path, bad, q.request, got["initial"], aid, set())
    assert (path / "data.mdb").read_bytes() == before
