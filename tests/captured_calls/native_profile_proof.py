"""Opt-in CURRENT-source retained native proof; THREE HOST publications, ZERO OS children.

Not the installed10Q8T story: initial outer completion then swapped partial prefix ending
BEFORE double Q/invoke. Exact graph sets/dedup/reservations retained for readiness review.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples"))

import daggerml as d
from daggerml import builtin as b, local, transfer
import captured_calls as p
import captured_call_adapter as adapter
import captured_call_session as bridge


def proof(root):
    root = Path(root).resolve()
    root.mkdir()
    path = root / "caller.dml"
    source_files = ("captured_calls.py", "captured_call_session.py", "captured_call_adapter.py", "captured_call_funcs.py", "captured_call_leaf.py")
    sources = {n: hashlib.sha256((ROOT / "examples" / n).read_bytes()).hexdigest() for n in source_files}
    for name in source_files:
        (root / name).write_bytes((ROOT / "examples" / name).read_bytes())
    launches, reservations, depths = [], [], []
    original_execute, original_context = local._execute, local.child_context
    original_reserve, original_depth = bridge.Session._reserve, p.authority_depth
    def host(context, source, interpreter, timeout):
        local.child_context = lambda *a, **k: context
        try:
            exec(compile(source, "HOST captured entry", "exec"), {})
        finally:
            local.child_context = original_context
        launches.append(dict(request=str(context.request), attempt=context.attempt_id, pre=str(context.pre_dispatch), source_sha256=hashlib.sha256(source).hexdigest()))
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    def reserve(self, count):
        reservations.append(dict(attempt=self.aid, prior=len(self.seen), count=count, bound=len(self.seen) + count))
        return original_reserve(self, count)
    def depth(value):
        depths.append(value)
        return original_depth(value)
    local._execute, bridge.Session._reserve, p.authority_depth = host, reserve, depth
    try:
        base = p.initialize(path, sys.executable)
        base = p.prepare_arguments(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
        base = p.prepare_arguments(path, commit=base, values={"a": 29, "b": 13}, inputs_name="swapped", ref="swapped")
        q1 = p.record_request(path, commit=base, ref="q1")
        final = adapter.execute(path, q1, workspace=root / "initial-HOST")
        got = p.inspect_completion(path, commit=final)
        assert len(got["semantic_ids"]) == 34
        selected = p.select_outer(path, commit=final, completion=final, ref="selected-outer")
        with d.Repository(path) as repo, repo.read() as tx:
            second = tx.get_dag(got["calls"][1]).bindings
            double_s = b.link(tx, second["selection"])
        with d.Repository(path) as repo, repo.write() as tx:
            entries = p.tree(tx, selected)
            entries[p.DOUBLE_SLOT] = double_s
            selected = tx.put_commit(tx.put_tree(entries), parents=(selected,))
            tx.create_ref("selected-double", selected)
        q3 = p.record_request(path, commit=selected, inputs_name="swapped", control="try-selected", double_control="require-selected", ref="q3")
        session = bridge.Session(path, q3, root / "partial-HOST")
        first = session.nodes.map_get(session.input, "a")
        second = session.nodes.map_get(session.input, "b")
        assert first.value == d.Datum.i64(29) and second.value == d.Datum.i64(13)
        add = session.invoker.invoke(session.tokens[0], session.input)
        full = session.nodes.arguments({"x": add})
        current = session.current
        actual = p.inspect_spine(path, current, q3.request, session.initial, session.aid, session.seen)
        assert len(session.seen) == 50 and len(actual["calls"]) == 1 and len(launches) == 3
        with d.Repository(path) as repo, repo.read() as tx:
            old_add = tx.get_dag(got["calls"][0]).bindings
            old_r = b.link(tx, old_add["result"])
            old_rf = tx.get_dag(old_r).bindings
            old_q = b.link(tx, old_rf["request"])
            old_trace = b.Inspector(tx, commit=current).trace(b.link(tx, old_rf["trace"]), request=old_q, inputs=q1.inputs.dag)
            assert tuple(v.dag for v in old_trace) == got["getters"]
            new_call = tx.get_dag(session.calls[0]).bindings
            new_r = b.link(tx, new_call["result"])
            new_rf = tx.get_dag(new_r).bindings
            new_q = b.link(tx, new_rf["request"])
            new_trace = b.Inspector(tx, commit=current).trace(b.link(tx, new_rf["trace"]), request=new_q, inputs=q3.inputs.dag)
            assert tuple(v.dag for v in new_trace) == tuple(session.getters)
            description, source = p.arguments(tx, current, session.handles[full][0], ("x",), set())
            assert source["x"].dag == new_r != old_r
            old_double, _ = p.arguments(tx, current, b.link(tx, tx.get_dag(double_s).bindings["inputs"]), ("x",), set())
            assert description.datum == old_double.datum
        bundle = transfer.export_commit(path, commit=current)
        (root / "history.bundle").write_bytes(bundle)
        session.ended = True
        result = dict(source=sources, HOST_only=True, OS_computational_children=0, HOST_publications=3,
            original_final=str(final), partial_head=str(current), initial=str(session.initial), outer_request=str(q3.request),
            original_semantic_ids=sorted(str(v) for v in got["semantic_ids"]),
            aggregate_semantic_ids=sorted(str(v) for v in session.seen), reservations=reservations,
            maximum_measured_prefix_depth=max(depths), same_source_outer_and_add_getter_IDs=True,
            old_outer_getters=[str(v) for v in got["getters"]], old_leaf_getters=[str(v.dag) for v in old_trace],
            new_outer_getters=[str(v) for v in session.getters], new_leaf_getters=[str(v.dag) for v in new_trace],
            old_add_R=str(old_r), new_add_R=str(new_r), double_MAP_datum=str(description.datum),
            double_input=str(description.dag), direct_source=str(source["x"].dag),
            bound64=True, authority8=True, no_double_Q_or_second_ordinary_position=True,
            fixed_story_depth_mapping="Same authority edges as measured v7 max5; additional persisted reread starts existing prefix at0, adds no edge or semantic nodes",
            known_limitation="partial proof does not run final q4/before-return; v7 exact-source qualification remains, mapping is explicit not a new current full-story measurement")
        assert all(r["bound"] <= 64 for r in reservations)
        (root / "proof.json").write_text(json.dumps(result, indent=2) + "\n")
        assert sources == {n: hashlib.sha256((ROOT / "examples" / n).read_bytes()).hexdigest() for n in source_files}
        return result
    finally:
        local._execute, local.child_context = original_execute, original_context
        bridge.Session._reserve, p.authority_depth = original_reserve, original_depth


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not args.run:
        raise ValueError("explicit --run required; no default computation")
    print(json.dumps(proof(args.output), indent=2))


if __name__ == "__main__":
    main()
