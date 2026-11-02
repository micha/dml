"""Explicit ONE installed THREE-Q/TWO synchronous LOCAL/16 builtin-position story.

The read helper is used by blocker-FIRST offline_read.py on SAME retained history.
Runtime must be actually installed; helpers
are explicit example sources, not checkout runtime PYTHONPATH or installed modules.
"""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
if not EXAMPLES.is_dir():
    EXAMPLES = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLES))

import daggerml as d
from daggerml import builtin as b, exchange as ex, local, transfer
import builtin_workflow as app
import reuse_selection as selection


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def initialize(path, interpreter, *, sources=EXAMPLES):
    logical = (Path(sources) / "builtin_funcs.py").read_bytes()
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        bindings = {n: b.put_binding(tx, source_uri="dml://source/builtin/" + suffix) for n, suffix in
                    (("empty-v1", "map/empty/v1"), ("insert-v1", "map/insert/v1"), ("get-v1", "map/get/v1"), ("get-v2", "map/get/v2"), ("index-v1", "list/get/v1"))}
        normal = {"sum-" + v: local.put_local_binding(tx, source=app.capture(bindings["get-" + v], bindings["index-v1"], logical_source=logical), interpreter=interpreter, timeout_ms=10000) for v in ("v1", "v2")}
        choice = app.put_choice(tx, map_v1=bindings["get-v1"], map_v2=bindings["get-v2"], normal_v1=normal["sum-v1"], normal_v2=normal["sum-v2"], list_v1=bindings["index-v1"], logical_source=logical)
        lists = {}
        left, right, changed = (tx.put_datum(v) for v in (13, 29, 30))
        for label, values in (("A", (left, right)), ("B", (left, right)), ("C", (left, changed))):
            node = b.literal(tx, d.Datum.list(values))
            lists[label] = tx.put_dag(root=node, bindings={"measurements": node, "origin": b.literal(tx, label)})
        entries = {**bindings, **normal, "get-choice": choice, **{"source-" + n: dag for n, dag in lists.items()}}
        commit = tx.put_commit(tx.put_tree(entries))
        tx.create_ref("main", commit)
    return commit, bindings, lists


def construct(path, commit, bindings, source, label):
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=commit) as rec:
            values = rec.source(source, "measurements")
            empty = rec.call(b.MAP_EMPTY, bindings["empty-v1"], rec.arguments())
            sample = rec.call(b.MAP_INSERT, bindings["insert-v1"], rec.arguments({"map": empty, "key": rec.literal("measurements"), "value": values}))
            inputs = rec.arguments({"sample": sample})
            ledger = rec.trace()
            entries = app.tree(tx, commit)
            entries[label + "-inputs"] = rec.dag(inputs)
            entries[label + "-construction"] = ledger
            authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
            tx.create_ref(label + "-construction", authored)
            response = dict(commit=str(authored), inputs=str(rec.dag(inputs)), datum=str(rec.inspector.arguments(rec.dag(inputs)).datum), ledger=str(ledger), source=str(source), label=label)
    return response


def request(path, commit, label, number, *, hit=False, override="default", control="try-selected"):
    return app.record_request(path, commit=commit, choice_name="get-choice", inputs_name=label + "-inputs",
                              decision_name="decision-%d" % number, decision_ref="decision-%d" % number,
                              submission_ref="submission-%d" % number, override=override, control=control,
                              reuse_ref="satisfaction-%d" % number if hit else None)


def request_receipt(got):
    return dict(commit=str(got.recorded.commit), request=str(got.recorded.request), request_id=got.recorded.request_id,
                decision=got.decision.name, decision_commit=str(got.decision.commit), basis=str(got.decision.base),
                inputs=str(got.decision.inputs.dag), datum=str(got.decision.inputs.datum), label=got.decision.label,
                satisfaction=None if got.reused is None else str(got.reused.commit))


def execute(path, root, got, number, *, audit_active=None):
    workspace = root / ("workspace-%d" % number)
    spec = ex.prepare_exchange(path, commit=got.recorded.commit, request=got.recorded.request,
                               binding_name=got.recorded.binding_name, inputs_name=got.recorded.inputs_name,
                               intent_uri=app.INTENT, worker_ref="work", workspace=workspace)
    expected = root / ("expected-%d.json" % number)
    ex.save_exchange_handle(expected, ex.ExchangeHandle(workspace, spec))
    children, run = [], None
    original = subprocess.Popen
    def tracked(*args, **kwargs):
        command = args[0]
        if children or len(command) != 6 or command[0] != sys.executable or command[-4] != str(workspace / "worker.dml"):
            raise RuntimeError("only exact expected direct local child is allowed")
        context = local.child_context(command[-4:])
        if ((context.request, context.binding, context.inputs) != (got.recorded.request, spec.binding, spec.inputs)
            or command[1] != str(Path(context.scratch) / "entry.py")):
            raise RuntimeError("actual native child request/binding/input/entry differs")
        with d.Repository(context.repository_path) as repo, repo.read() as tx:
            captured = b.scalar(tx, tx.get_dag(context.binding).bindings["source"], "bytes")
        if Path(command[1]).read_bytes() != captured:
            raise RuntimeError("actual child entry differs from captured native source")
        process = original(*args, **kwargs)
        children.append(process)
        save(root / ("spawn-%d.json" % number), dict(request=str(got.recorded.request),
              submission=str(got.recorded.commit), pid=process.pid, args=args[0], entry_sha256=hashlib.sha256(captured).hexdigest(),
              pre_dispatch=args[0][-3], attempt_id=args[0][-2], publication_ref=args[0][-1]))
        return process
    subprocess.Popen = tracked
    try:
        if audit_active is not None:
            audit_active[0] = False
        run = ex.execute_exchange(workspace)
    finally:
        if audit_active is not None:
            audit_active[0] = True
        subprocess.Popen = original
        save(root / ("child-%d.json" % number), dict(request=str(got.recorded.request),
             children=[dict(pid=c.pid, exit=c.poll(), reaped=c.returncode is not None) for c in children],
             outcome=None if run is None else run.outcome, completion=None if run is None else str(run.final_commit),
             result=None if run is None or run.result is None else str(run.result)))
    if len(children) != 1 or children[0].poll() is None or run.outcome != "success" or children[0].returncode != 0:
        raise RuntimeError("uncertain/unsuccessful child custody: STOP, no relaunch")
    # Actual child known reaped BEFORE observe/receive/public S.
    observation = ex.observe_exchange(ex.ExchangeHandle(workspace, spec), packet=root / ("packet-%d" % number))
    received = ex.receive_observation(path, packet=observation.packet, expected=spec, ref="completion-%d" % number)
    slot = app.SLOT if number == 1 else "fresh-sum-pair"
    selected = selection.select(path, commit=received.commit, slot=slot, binding_name=got.recorded.binding_name,
                                 inputs_name=got.recorded.inputs_name, intent_uri=app.INTENT, packet=observation.packet,
                                 expected_file=expected, ref=slot)
    with d.Repository(path) as repo, repo.read() as tx:
        output = b.Inspector(tx, commit=selected.commit).node(selected.result)
        native = dict(completion_parents=[str(p) for p in tx.get_commit(run.final_commit).parents],
                      completion_tree={n: str(v) for n, v in app.tree(tx, run.final_commit).items()},
                      reservation=str(tx.get_ref("request-" + got.recorded.request_id)))
    child = dict(number=number, pid=children[0].pid, exit=0, reaped=True, attempt_id=run.attempt_id,
                 attempt=str(run.final_attempt), request=str(run.context.request), result=str(run.result),
                 completion=str(run.final_commit), pre_dispatch=str(run.context.pre_dispatch),
                 workspace=str(workspace), packet=str(observation.packet), expected=str(expected),
                 selection=str(selected.dag), selection_commit=str(selected.commit), slot=slot, value=output.value.value, native=native)
    save(root / ("completed-%d.json" % number), child)
    return selected, child


def compatibility(path, commit, bindings, inputs):
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=commit) as rec:
            old_input = rec.load(inputs)
            args = rec.arguments({"map": old_input, "key": rec.literal("sample")})
            old = rec.call(b.MAP_GET, bindings["get-v1"], args)
            new = rec.call(b.MAP_GET, bindings["get-v2"], args)
            if old.value != new.value:
                raise ValueError("retained versions disagree")
            ledger = rec.trace()
            entries = app.tree(tx, commit)
            entries["compatibility"] = ledger
            final = tx.put_commit(tx.put_tree(entries), parents=(commit,))
            tx.create_ref("final", final)
            return final, ledger


def run(root):
    root = Path(root).resolve()
    root.mkdir()
    sources = root / "captured-source"
    sources.mkdir()
    hashes = {}
    for origin in [__file__, *(EXAMPLES / (n + ".py") for n in ("builtin_workflow", "builtin_funcs", "reuse_selection", "explicit_reuse"))]:
        origin = Path(origin)
        target = sources / origin.name
        shutil.copyfile(origin, target)
        hashes[origin.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    modules = {n: dict(path=str(m.__file__), sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()) for n, m in
               (("daggerml", d), ("builtin", b), ("local", local), ("exchange", ex), ("transfer", transfer), ("native", d._core))}
    for item in modules.values():
        if not str(Path(item["path"]).resolve()).startswith(str(Path(sys.prefix).resolve()) + "/"):
            raise RuntimeError("story requires isolated installed runtime, not checkout/PYTHONPATH")
    cli = Path(d.__file__).parent / "_bin" / "dml"
    modules["cli"] = dict(path=str(cli), sha256=hashlib.sha256(cli.read_bytes()).hexdigest())
    save(root / "prelaunch-source.json", dict(source=hashes, installed=modules, interpreter=sys.executable))
    active = [True]
    def audit(event, args):
        if active[0] and event in ("subprocess.Popen", "os.posix_spawn", "os.fork", "os.forkpty", "os.exec", "os.system", "socket.connect", "socket.bind", "socket.getaddrinfo"):
            raise RuntimeError("builtin/metadata phase cannot spawn or transport")
    sys.addaudithook(audit)
    path = root / "caller.dml"
    initial, bindings, literals = initialize(path, sys.executable, sources=sources)
    a = construct(path, initial, bindings, literals["A"], "A")
    save(root / "construction-A.json", a)
    q1 = request(path, d.ObjectId.from_hex(a["commit"]), "A", 1)
    save(root / "request-1.json", request_receipt(q1))
    s1, child1 = execute(path, root, q1, 1, audit_active=active)
    promoted = app.promote(path, commit=s1.commit, choice_name="get-choice", default="v2", ref="promoted")
    bb = construct(path, promoted, bindings, literals["B"], "B")
    save(root / "construction-B.json", bb)
    q2 = request(path, d.ObjectId.from_hex(bb["commit"]), "B", 2, hit=True)
    save(root / "request-2.json", request_receipt(q2))
    c = construct(path, q2.reused.commit, bindings, literals["C"], "C")
    save(root / "construction-C.json", c)
    q3 = request(path, d.ObjectId.from_hex(c["commit"]), "C", 3)
    save(root / "request-3.json", request_receipt(q3))
    if q3.decision.reason != "value-mismatch" or q3.reused is not None:
        raise RuntimeError("changed input must remain pending fresh BEFORE dispatch")
    s3, child3 = execute(path, root, q3, 3, audit_active=active)
    final, ledger = compatibility(path, s3.commit, bindings, q1.recorded.inputs)
    receipt = dict(initial=str(initial), final=str(final), repository=str(path), requests=[request_receipt(q) for q in (q1, q2, q3)],
                   children=[child1, child3], constructions=[a, bb, c], promoted=str(promoted), compatibility=str(ledger),
                   sources=hashes, installed=modules)
    save(root / "receipt.json", receipt)
    for child in receipt["children"]:
        for key in ("workspace", "packet", "expected"):
            original = Path(child[key])
            original.rename(original.with_name(original.name + ".unavailable"))
    sources.rename(root / "captured-source.unavailable")
    with d.Repository(root / "replica.dml", create=True):
        pass
    transfer.import_commit(root / "replica.dml", transfer.export_commit(path, commit=final), ref="retained")
    return receipt


def read(root):
    root = Path(root)
    receipt = json.loads((root / "receipt.json").read_bytes())
    path = root / "replica.dml"
    final = d.ObjectId.from_hex(receipt["final"])
    bundle = json.loads(transfer.export_commit(path, commit=final))
    requests, attempts = set(), set()
    with d.Repository(path) as repo, repo.read() as tx:
        for row in bundle["objects"]:
            if row["kind"] != "dag":
                continue
            got = tx.get_dag(d.ObjectId.from_hex(row["id"]))
            if "role" not in got.bindings:
                continue
            role = b.scalar(tx, got.bindings["role"], "string")
            if role == "local-request-v1":
                requests.add(b.scalar(tx, got.root, "string"))
            elif role == "local-attempt-v1":
                attempts.add(b.scalar(tx, got.root, "string"))
        if (len(requests), len(attempts)) != (3, 2):
            raise ValueError("native story census must be THREE Q/TWO T")
        construction_positions = sum(len(b.Inspector(tx, commit=final).trace(d.ObjectId.from_hex(row["ledger"]))) for row in receipt["constructions"])
        nested, values = 0, []
        for row in receipt["children"]:
            inspector = b.Inspector(tx, commit=final)
            output = inspector.node(d.ObjectId.from_hex(row["result"]))
            values.append(output.value.value)
            fields = tx.get_dag(output.dag).bindings
            nested += len(inspector.trace(b.link(tx, fields["trace"]), request=b.link(tx, fields["request"]), inputs=b.link(tx, fields["inputs"])))
        compat = b.Inspector(tx, commit=final).trace(d.ObjectId.from_hex(receipt["compatibility"]))
        if (construction_positions, nested, len(compat), values) != (6, 8, 2, [42, 43]) or compat[0].datum != compat[1].datum:
            raise ValueError("actual position/result/version compatibility differs")
        choice = app.inspect_choice(tx, app.tree(tx, final)["get-choice"])
        if choice.default != "v2":
            raise ValueError("default promotion missing")
    readings = [app.inspect_request(path, commit=d.ObjectId.from_hex(row["commit"]), request=d.ObjectId.from_hex(row["request"]), decision_name=row["decision"], satisfaction_commit=None if row["satisfaction"] is None else d.ObjectId.from_hex(row["satisfaction"])) for row in receipt["requests"]]
    if (readings[0].inputs.datum != readings[1].inputs.datum or readings[0].inputs.dag == readings[1].inputs.dag
        or readings[0].inputs.datum == readings[2].inputs.datum or readings[1].executed != readings[0].inputs
        or readings[1].returned.value != d.Datum.i64(42) or readings[1].label != "v2" or readings[0].label != "v1"):
        raise ValueError("requested/executed full-value-source/version provenance differs")
    selected = selection.inspect(path, commit=final, slot=app.SLOT)
    if selected.request != d.ObjectId.from_hex(receipt["requests"][0]["request"]):
        raise ValueError("fresh work automatically adopted")
    return dict(requests=3, attempts=2, builtin_positions=16, construction=6, nested=8, compatibility=2, results=[42, 42, 43], closure_objects=len(bundle["objects"]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run",))
    parser.add_argument("root")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
