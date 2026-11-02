"""Finite FIVE-Q/FOUR synchronous LOCAL-attempt recorded-map acceptance story.

Run only explicitly with installed DML. `read` inspects SAME retained history;
no computation, transport, original source/workspace or operational ref required.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

# Application helpers are explicit source, not installed runtime modules.
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
if EXAMPLES.is_dir():
    sys.path.insert(0, str(EXAMPLES))

import daggerml as d
from daggerml import exchange as ex, local, transfer
import argument_map_binding as binding
import datum_reuse as reuse
import recorded_maps as maps
import reuse_selection as selection

DOUBLE = "urn:example:datum-double"
ADD = "urn:example:datum-add"


def initialize(path, interpreter, sources):
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        fields = {n: maps.literal(tx, v) for n, v in {"x": "x", "left": "left", "right": "right", "n42": 42, "n13": 13, "n29": 29, "n30": 30}.items()}
        literals = tx.put_dag(root=fields["n42"], bindings=fields)
        entries = {"literals": literals}
        for func in ("add", "double"):
            entries[func + "-binding"] = local.put_local_binding(tx, source=binding.capture(func, directory=sources), interpreter=interpreter, timeout_ms=10000)
        commit = tx.put_commit(tx.put_tree(entries))
        tx.create_ref("main", commit)
    return commit, literals


def construct(path, commit, *, prefix, pairs):
    empty = maps.map_empty(path, commit=commit, output_name=prefix + "-empty", ref=prefix + "-empty")
    current, source = empty.commit, empty.dag
    for i, (key, value) in enumerate(pairs):
        name = prefix + "-insert-%d" % i
        got = maps.map_insert(path, commit=current, prior=source, key=key, value=value, output_name=name, ref=name)
        current, source = got.commit, got.dag
    got = maps.put_inputs(path, commit=current, construction=source, output_name=prefix + "-inputs", ref=prefix + "-inputs")
    return got


def request(path, commit, *, number, func, input_name, hit=False):
    return reuse.record_request(path, commit=commit, intent_uri=DOUBLE if func == "double" else ADD, binding_name=func + "-binding", inputs_name=input_name, table_name="double-table" if func == "double" else "add-table", decision_name="decision-%d" % number, decision_ref="decision-%d" % number, submission_ref="submission-%d" % number, reuse_ref="satisfaction-%d" % number if hit else None)


def execute(path, root, got, number):
    workspace = root / ("workspace-%d" % number)
    spec = ex.prepare_exchange(path, commit=got.recorded.commit, request=got.recorded.request, binding_name=got.recorded.binding_name, inputs_name=got.recorded.inputs_name, intent_uri=got.recorded.intent_uri, worker_ref="work", workspace=workspace)
    saved = root / ("expected-%d.json" % number)
    ex.save_exchange_handle(saved, ex.ExchangeHandle(workspace, spec))
    # Synchronous execute returns only after the unchanged local adapter reaps its
    # direct computational child. Retain direct PID/wait observations explicitly.
    children = []
    run = None
    original = subprocess.Popen
    def tracked(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child
    subprocess.Popen = tracked
    try:
        run = ex.execute_exchange(workspace)
    finally:
        subprocess.Popen = original
        custody = dict(number=number, request=str(got.recorded.request), submission=str(got.recorded.commit), children=[dict(pid=c.pid, exit=c.poll(), reaped=c.returncode is not None) for c in children], outcome=None if run is None else run.outcome, completion=None if run is None else str(run.final_commit), result=None if run is None or run.result is None else str(run.result))
        (root / ("child-%d.json" % number)).write_text(json.dumps(custody, indent=2) + "\n")
    if any(child.poll() is None for child in children):
        raise RuntimeError("uncertain child custody: STOP, no relaunch")
    if len(children) != 1 or run.outcome != "success" or children[0].returncode != 0:
        raise RuntimeError("story computation did not complete successfully: STOP")
    observation = ex.observe_exchange(ex.ExchangeHandle(workspace, spec), packet=root / ("packet-%d" % number))
    received = ex.receive_observation(path, packet=observation.packet, expected=spec, ref="completion-%d" % number)
    selected = selection.select(path, commit=received.commit, slot="success-%d" % number, binding_name=got.recorded.binding_name, inputs_name=got.recorded.inputs_name, intent_uri=got.recorded.intent_uri, packet=observation.packet, expected_file=saved, ref="success-%d" % number)
    with d.Repository(path) as repo, repo.read() as tx:
        native = dict(selection_parents=[str(v) for v in tx.get_commit(selected.commit).parents], completion_parents=[str(v) for v in tx.get_commit(run.final_commit).parents], completion_tree=str(tx.get_commit(run.final_commit).tree), completion_entries={n: str(v) for n, v in maps.tree(tx, run.final_commit).items()}, reservation=str(tx.get_ref("request-" + got.recorded.request_id)), completion_ref=str(tx.get_ref("completion-%d" % number)))
    (root / ("completed-%d.json" % number)).write_text(json.dumps(dict(request=str(selected.request), attempt=str(selected.attempt), result=str(selected.result), selection=str(selected.dag), selection_commit=str(selected.commit), pre_dispatch=str(run.context.pre_dispatch), native=native, pid=children[0].pid, exit=children[0].returncode, reaped=True), indent=2) + "\n")
    return selected, dict(number=number, workspace=str(workspace), packet=str(observation.packet), expected=str(saved), pid=children[0].pid, exit=children[0].returncode, reaped=True, completion=str(run.final_commit), pre_dispatch=str(run.context.pre_dispatch), attempt_id=run.attempt_id, attempt=str(run.final_attempt), request=str(run.context.request), result=str(run.result))


def _request_receipt(got):
    return dict(commit=str(got.recorded.commit), request=str(got.recorded.request), request_id=got.recorded.request_id, decision=got.decision.name, decision_commit=str(got.decision.commit), basis=str(got.decision.base), inputs=str(got.decision.inputs.dag), datum=str(got.decision.inputs.datum), construction=str(got.decision.inputs.construction), satisfaction=None if got.reused is None else str(got.reused.commit))


def _save_request(root, number, got):
    (root / ("request-%d.json" % number)).write_text(json.dumps(_request_receipt(got), indent=2) + "\n")


def run(root, *, interpreter=None):
    root = Path(root).resolve()
    root.mkdir()
    source_dir = root / "captured-source"
    source_dir.mkdir()
    origin = EXAMPLES
    source_names = (*binding.MODULES, "datum_reuse", "argument_map_binding")
    hashes = {}
    for module in source_names:
        source = origin / (module + ".py")
        target = source_dir / source.name
        shutil.copyfile(source, target)
        hashes[source.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    controller = source_dir / "installed_story.py"
    shutil.copyfile(__file__, controller)
    hashes[controller.name] = hashlib.sha256(controller.read_bytes()).hexdigest()
    (root / "prelaunch-source.json").write_text(json.dumps(hashes, indent=2) + "\n")
    path = root / "caller.dml"
    commit, literal_dag = initialize(path, sys.executable if interpreter is None else interpreter, source_dir)
    initial = commit
    sources = {}
    for n in ("x", "left", "right", "n42", "n13", "n29", "n30"):
        got = maps.literal_source(path, commit=commit, source_dag=literal_dag, source_name=n, output_name="source-" + n, ref="source-" + n)
        commit, sources[n] = got.commit, got.dag
    table = reuse.define_table(path, commit=commit, table_name="double-table", intent_uri=DOUBLE, ref="empty-table")
    first = construct(path, table.commit, prefix="literal42", pairs=((sources["x"], sources["n42"]),))
    q1 = request(path, first.commit, number=1, func="double", input_name=first.name)
    _save_request(root, 1, q1)
    s1, child1 = execute(path, root, q1, 1)
    selected_table = reuse.select_entry(path, commit=s1.commit, table_name="double-table", selection_slot=s1.slot, ref="selected-table")
    add42 = construct(path, selected_table.commit, prefix="add42", pairs=((sources["left"], sources["n13"]), (sources["right"], sources["n29"])))
    q2 = request(path, add42.commit, number=2, func="add", input_name=add42.name)
    _save_request(root, 2, q2)
    s2, child2 = execute(path, root, q2, 2)
    value42 = maps.returned_source(path, commit=s2.commit, slot=s2.slot, output_name="computed42-source", ref="computed42-source")
    computed42 = construct(path, value42.commit, prefix="computed42", pairs=((sources["x"], value42.dag),))
    q3 = request(path, computed42.commit, number=3, func="double", input_name=computed42.name, hit=True)
    _save_request(root, 3, q3)
    add43 = construct(path, q3.reused.commit, prefix="add43", pairs=((sources["left"], sources["n13"]), (sources["right"], sources["n30"])))
    q4 = request(path, add43.commit, number=4, func="add", input_name=add43.name)
    _save_request(root, 4, q4)
    s4, child4 = execute(path, root, q4, 4)
    value43 = maps.returned_source(path, commit=s4.commit, slot=s4.slot, output_name="computed43-source", ref="computed43-source")
    computed43 = construct(path, value43.commit, prefix="computed43", pairs=((sources["x"], value43.dag),))
    q5 = request(path, computed43.commit, number=5, func="double", input_name=computed43.name)
    _save_request(root, 5, q5)
    if q5.decision.reason != "no-entry" or q5.reused is not None:
        raise RuntimeError("changed argument datum must remain pending fresh before dispatch")
    s5, child5 = execute(path, root, q5, 5)
    # An ordinary summary links satisfaction, not a fake fresh completion for Q3.
    with d.Repository(path) as repo, repo.write() as tx:
        links = {"request-%d" % i: q.recorded.request for i, q in enumerate((q1, q2, q3, q4, q5), 1)}
        links.update(satisfaction=q3.reused.dag, **{"historical-result": s1.result, "final-result": s5.result})
        summary = maps.record(tx, "example-recorded-map-story-v1", links=links, root="final-result")
        entries = maps.tree(tx, s5.commit)
        entries["summary"] = summary
        final = tx.put_commit(tx.put_tree(entries), parents=(s5.commit,))
        tx.create_ref("final", final)
    receipt = dict(initial=str(initial), final=str(final), repository=str(path), sources=hashes, requests=[_request_receipt(q) for q in (q1, q2, q3, q4, q5)], children=[child1, child2, child4, child5], selected_table=str(selected_table.dag))
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    # Only owned originals, AFTER actual direct-child reaping; bytes retained inert.
    for child in receipt["children"]:
        for key in ("workspace", "packet", "expected"):
            original_path = Path(child[key])
            original_path.rename(original_path.with_name(original_path.name + ".unavailable"))
    source_dir.rename(root / "captured-source.unavailable")
    replica = root / "replica.dml"
    with d.Repository(replica, create=True):
        pass
    transfer.import_commit(replica, transfer.export_commit(path, commit=final), ref="retained")
    return receipt


def read(root, *, repository=None):
    root = Path(root)
    receipt = json.loads((root / "receipt.json").read_bytes())
    path = root / "replica.dml" if repository is None else Path(repository)
    final = d.ObjectId.from_hex(receipt["final"])
    bundle = json.loads(transfer.export_commit(path, commit=final))
    requests, attempts = set(), set()
    with d.Repository(path) as repo, repo.read() as tx:
        for row in bundle["objects"]:
            if row["kind"] != "dag":
                continue
            dag = tx.get_dag(d.ObjectId.from_hex(row["id"]))
            if "role" not in dag.bindings:
                continue
            role = maps.scalar(tx, dag.bindings["role"], "string")
            if role == "local-request-v1":
                requests.add(maps.scalar(tx, dag.root, "string"))
            elif role == "local-attempt-v1":
                attempts.add(maps.scalar(tx, dag.root, "string"))
    if len(requests) != 5 or len(attempts) != 4:
        raise ValueError("native acceptance census must be FIVE Q/FOUR T")
    readings = []
    for row in receipt["requests"]:
        got = reuse.inspect_request(path, commit=d.ObjectId.from_hex(row["commit"]), request=d.ObjectId.from_hex(row["request"]), decision_name=row["decision"], satisfaction_commit=None if row["satisfaction"] is None else d.ObjectId.from_hex(row["satisfaction"]))
        readings.append(got)
    table = reuse.inspect_table(path, commit=final, table_name="double-table")
    outputs = tuple(maps.inspect_returned(path, commit=final, slot="success-%d" % n) for n in (1, 2, 4, 5))
    if tuple(got.value.value for got in outputs) != (84, 42, 43, 86) or sum(len(got.accesses) for got in outputs) != 6:
        raise ValueError("returned values/actual successful getter positions differ")
    literal_input, computed_input = readings[0].requested, readings[2].requested
    if literal_input.datum != computed_input.datum or literal_input.construction == computed_input.construction or literal_input.dag == computed_input.dag:
        raise ValueError("equal MAP datums must retain distinct construction/full I")
    if readings[2].executed != literal_input or readings[2].returned.request != readings[0].request:
        raise ValueError("requested versus historical executed provenance differs")
    if len(table.entries) != 1 or table.entries[0].inputs != literal_input or datum_key_for(readings[4].requested) in {r.key for r in table.entries}:
        raise ValueError("fresh work must not automatically adopt")
    return dict(requests=len(requests), attempts=len(attempts), getter_positions=6, results=[got.value.value for got in outputs], requested_construction=str(computed_input.construction), executed_construction=str(literal_input.construction), closure_objects=len(bundle["objects"]))


def datum_key_for(inputs):
    return reuse.datum_key(inputs.datum)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "read"))
    parser.add_argument("root")
    args = parser.parse_args(argv)
    result = run(args.root) if args.mode == "run" else read(args.root)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
