"""Native phase/owning-payload negatives over one actual HOST prefix/history per test group."""

import daggerml as d
from daggerml import builtin as b
import pytest

from test_exchange_records import clone
from test_implementation_calls import initial, host, p, adapter


def test_native_PHASE_spine_order_parent_owner_payload_and_terminal_guards(initial, host, tmp_path):
    path, base = initial
    result = adapter.invoke(path, commit=base, ref="outer", workspace=tmp_path / "HOST")
    got = p.inspect_completion(path, commit=result.commit)
    with d.Repository(path) as repo, repo.read() as tx:
        aid = b.scalar(tx, tx.get_dag(got["initial"]).root, "string")
        before = tx.get_commit(result.commit).parents[0]
        available = []
        for current in p.history(tx, before):
            parents = tx.get_commit(current).parents
            if not parents:
                continue
            previous = parents[0]
            old, now = p.tree(tx, previous), p.tree(tx, current)
            names = [n for n in set(now) - set(old) if n.startswith("phase-" + aid + "-")]
            if len(names) == 1:
                phase = now[names[0]]
                fields = tx.get_dag(phase).bindings
                available.append((b.scalar(tx, fields["kind"], "string"), current, names[0], phase))
        steps = {kind: (commit, name, phase) for kind, commit, name, phase in available}
    # Each well-typed malformed immutable commit is checked from its ACTUAL native tree/parents.
    variants = (("get-a", "unknown-kind"), ("get-a", "previous"), ("get-a", "owner"), ("get-a", "payload"),
        ("get-a", "delta"), ("get-a", "ordinal"), ("leaf-join", "parents"),
        ("leaf-pending", "submission"), ("leaf-selected", "selection-commit"),
        ("get-key-a", "literal"), ("get-arguments-a", "inputs"), ("get-a", "arguments"),
        ("double-input", "duplicate-map"), ("returned", "terminal-follow"), ("leaf-done", "status"))
    for kind, fault in variants:
        current, name, phase = steps[kind]
        with d.Repository(path) as repo, repo.write() as tx:
            tree, fields = p.tree(tx, current), tx.get_dag(phase).bindings
            changes, parents = {}, tx.get_commit(current).parents
            if fault == "unknown-kind":
                changes["kind"] = b.literal(tx, "unsupported-phase")
            elif fault == "previous":
                changes["previous"] = b.literal(tx, result.request.commit.bytes)
            elif fault == "owner":
                changes["request"] = tx.put_subdag(result.request.closure["dag"])
            elif fault == "payload":
                index = b.scalar(tx, fields["index"], "i64")
                tree[p.payload_names(aid, index, kind)["node"]] = got["getters"][1]
            elif fault == "delta":
                tree["unrelated"] = result.request.closure["dag"]
            elif fault == "ordinal":
                changes["index"] = b.literal(tx, 90)
            elif fault == "parents":
                parents = tuple(reversed(parents))
            elif fault in ("submission", "selection-commit"):
                changes[fault] = b.literal(tx, result.request.commit.bytes)
            elif fault in ("literal", "inputs", "arguments", "status"):
                index = b.scalar(tx, fields["index"], "i64")
                payload = "node" if fault in ("literal", "arguments") else "inputs" if fault == "inputs" else "call"
                target = b.link(tx, fields[payload])
                if fault == "literal":
                    invalid = clone(tx, target, fields={"value": b.literal(tx, "b")})
                elif fault == "inputs":
                    # Valid original argument MAP is NOT getter's prepared map/key argument node.
                    invalid = result.request.inputs.dag
                elif fault == "arguments":
                    # Another real, semantically valid operation cannot substitute for THIS
                    # prepared getter arguments/position even under the same captured binding.
                    invalid = got["getters"][1]
                else:
                    invalid = clone(tx, target, fields={"status": b.literal(tx, "unknown")})
                changes[payload] = tx.put_subdag(invalid)
                tree[p.payload_names(aid, index, kind)[payload]] = invalid
            elif fault == "duplicate-map":
                # Replaying a valid double-input after the already constructed map is illegal.
                index = b.scalar(tx, fields["index"], "i64") + 1
                changes.update(index=b.literal(tx, index), previous=b.literal(tx, current.bytes))
                new_name = p.phase_name(aid, index)
                new_phase = clone(tx, phase, fields=changes)
                tree[new_name] = new_phase
                tree[p.payload_names(aid, index, kind)["inputs"]] = b.link(tx, fields["inputs"])
                changed = tx.put_commit(tx.put_tree(tree), parents=(current,))
            else:
                # Native phase after terminal return, consecutive index/correct previous/delta.
                index = b.scalar(tx, fields["index"], "i64") + 1
                extra = b.record(tx, p.PHASE_ROLE, values={"kind": "get-key-a", "index": index, "previous": current.bytes},
                    links={"request": result.request.request, "initial-attempt": got["initial"], "node": got["getters"][0]})
                tree[p.phase_name(aid, index)] = extra
                tree[p.payload_names(aid, index, "get-key-a")["node"]] = got["getters"][0]
                changed = tx.put_commit(tx.put_tree(tree), parents=(current,))
            if fault not in ("duplicate-map", "terminal-follow"):
                tree[name] = clone(tx, phase, fields=changes)
                changed = tx.put_commit(tx.put_tree(tree), parents=parents)
        with pytest.raises((ValueError, KeyError)):
            p.inspect_spine(path, changed, result.request.request, got["initial"], aid, set())
    assert len(host) == 2
