"""Opt-in sole SIX-Q/FOUR-local/EIGHT-getter installed capture story; never default-run."""

import argparse
import errno
import hashlib
import json
import os
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
import closure_calls as app
import closure_funcs as funcs
import closure_runtime as rt
import explicit_reuse
import reuse_selection as selection


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metadata_controls():
    active = [True]
    def audit(event, args):
        if active[0] and event in ("subprocess.Popen", "os.posix_spawn", "os.fork", "os.forkpty", "os.exec", "os.system", "socket.connect", "socket.bind", "socket.getaddrinfo"):
            raise RuntimeError("metadata phase cannot spawn or transport")
    sys.addaudithook(audit)
    import socket
    import urllib.request
    rejected = []
    for label, action in (("spawn", lambda: subprocess.Popen([sys.executable, "-c", "raise SystemExit(99)"])),
        ("connect", lambda: socket.create_connection(("127.0.0.1", 1))),
        ("urllib-transport", lambda: urllib.request.urlopen("http://127.0.0.1:1", timeout=1))):
        try:
            action()
        except RuntimeError:
            rejected.append(label)
        else:
            raise RuntimeError("metadata blocker did not reject " + label)
    return active, dict(blockers=rejected, before_any_Q_T=True)


def create(path, commit, label, version, scale):
    with d.Repository(path) as repo, repo.read() as tx:
        entries = app.tree(tx, commit)
    return app.create_closure(path, commit=commit, map_dependency=entries["map-" + version],
        list_dependency=entries["list-v1"], scale=entries["scale-" + scale], binding_name="binding-" + label,
        closure_name="closure-" + label, interpreter=sys.executable, ref="created-" + label)


def request(path, commit, number, label, control, hit):
    return app.record_request(path, commit=commit, closure_name="closure-" + label,
        binding_name="binding-" + label, inputs_name="inputs", decision_name="decision-%d" % number,
        decision_ref="decision-%d" % number, submission_ref="submission-%d" % number, control=control,
        reuse_ref="satisfaction-%d" % number if hit else None)


def request_receipt(q, number):
    c = q.decision.closure
    return dict(number=number, commit=str(q.recorded.commit), request=str(q.recorded.request),
        request_id=q.recorded.request_id, decision=q.decision.name, decision_commit=str(q.decision.commit),
        basis=str(q.decision.base), binding=str(c.binding), closure=str(c.dag), environment=str(c.environment.dag),
        scale=str(c.environment.scale.dag), key=str(c.key), map_binding=str(c.environment.map_binding),
        inputs=str(q.recorded.inputs), datum=str(q.decision.inputs.datum), action=q.decision.action,
        reason=q.decision.reason, satisfaction=None if q.reused is None else str(q.reused.commit))


def execute(path, root, q, number, active):
    workspace = root / ("workspace-%d" % number)
    spec = ex.prepare_exchange(path, commit=q.recorded.commit, request=q.recorded.request,
        binding_name=q.recorded.binding_name, inputs_name=q.recorded.inputs_name,
        intent_uri=app.INTENT, worker_ref="work", workspace=workspace)
    expected = root / ("expected-%d.json" % number)
    ex.save_exchange_handle(expected, ex.ExchangeHandle(workspace, spec))
    save(root / ("dispatch-%d.json" % number), dict(number=number, request=str(q.recorded.request),
        submission=str(q.recorded.commit), binding=str(spec.binding), inputs=str(spec.inputs),
        expected_sha256=digest(expected), interpreter=sys.executable, workspace=str(workspace)))
    children, run = [], None
    popen = subprocess.Popen
    def tracked(*args, **kwargs):
        command = args[0]
        if (children or len(command) != 6 or command[0] != sys.executable
            or command[-4] != str(workspace / "worker.dml") or kwargs.get("shell", False)):
            raise RuntimeError("only ONE exact expected direct local child is allowed")
        context = local.child_context(command[-4:])
        if ((context.request, context.binding, context.inputs) != (q.recorded.request, spec.binding, spec.inputs)
            or command[1] != str(Path(context.scratch) / "entry.py")):
            raise RuntimeError("actual native child Q/binding/input/entry differs")
        with d.Repository(context.repository_path) as repo, repo.read() as tx:
            captured = b.scalar(tx, tx.get_dag(context.binding).bindings["source"], "bytes")
            closure = app.inspect_closure(tx, context.pre_dispatch, q.decision.closure.dag)
        if closure != q.decision.closure or Path(command[1]).read_bytes() != captured:
            raise RuntimeError("actual pinned capture/entry source differs")
        process = popen(*args, **kwargs)
        children.append(process)
        waited = process.wait
        process.wait_receipts = []
        def actual_wait(*a, **k):
            try:
                result = waited(*a, **k)
            except BaseException as error:
                process.wait_receipts.append(dict(returned=False, error=type(error).__name__))
                save(root / ("wait-%d.json" % number), process.wait_receipts)
                raise
            process.wait_receipts.append(dict(returned=True, exit=result))
            save(root / ("wait-%d.json" % number), process.wait_receipts)
            return result
        process.wait = actual_wait
        save(root / ("spawn-%d.json" % number), dict(number=number, request=str(context.request),
            submission=str(q.recorded.commit), pid=process.pid, args=command, pre_dispatch=str(context.pre_dispatch),
            attempt_id=context.attempt_id, publication_ref=context.publication_ref,
            entry_sha256=hashlib.sha256(captured).hexdigest()))
        return process
    subprocess.Popen = tracked
    try:
        active[0] = False
        run = ex.execute_exchange(workspace)
    finally:
        active[0] = True  # BEFORE completion observation/import/S/inspection.
        subprocess.Popen = popen
        save(root / ("child-%d.json" % number), dict(number=number, request=str(q.recorded.request),
            children=[dict(pid=c.pid, exit=c.poll(), reaped=c.returncode is not None, actual_wait=c.wait_receipts) for c in children],
            outcome=None if run is None else run.outcome, completion=None if run is None else str(run.final_commit),
            result=None if run is None or run.result is None else str(run.result)))
    if (run is None or len(children) != 1 or children[0].poll() is None or children[0].returncode != 0
        or run.outcome != "success" or children[0].wait_receipts != [dict(returned=True, exit=0)]):
        raise RuntimeError("failed/uncertain custody: STOP/no relaunch")
    observed = ex.observe_exchange(ex.ExchangeHandle(workspace, spec), packet=root / ("packet-%d" % number))
    received = ex.receive_observation(path, packet=observed.packet, expected=spec, ref="completion-%d" % number)
    slot = app.SLOT if number == 1 else "witness-%d" % number
    selected = selection.select(path, commit=received.commit, slot=slot, binding_name=q.recorded.binding_name,
        inputs_name=q.recorded.inputs_name, intent_uri=app.INTENT, packet=observed.packet, expected_file=expected, ref=slot)
    # Custody receipt already persisted BEFORE value/profile assertion.
    producer = app.inspect_producer(path, commit=selected.commit, slot=slot)
    row = dict(number=number, pid=children[0].pid, exit=0, reaped=True, request=str(q.recorded.request),
        request_id=q.recorded.request_id, attempt=str(selected.attempt), attempt_id=selected.attempt_id,
        result=str(selected.result), completion=str(selected.completion), pre_dispatch=str(run.context.pre_dispatch),
        selection=str(selected.dag), selection_commit=str(selected.commit), slot=slot, workspace=str(workspace),
        packet=str(observed.packet), expected=str(expected), value=producer.returned.value.value)
    save(root / ("completed-%d.json" % number), row)
    return selected, row


def run(root):
    root = Path(root).resolve()
    root.mkdir()
    operational = Path(__file__).resolve().parent
    if operational != root.parent / "launch-source":
        raise RuntimeError("launch ONLY measured owned operational seven-file copy")
    captured = root / "captured-source"
    captured.mkdir()
    source_names = ("installed_story.py", "offline_read.py", "closure_calls.py", "closure_runtime.py", "closure_funcs.py", "reuse_selection.py", "explicit_reuse.py")
    hashes = {}
    for n in source_names:
        shutil.copyfile(operational / n, captured / n)
        hashes[n] = digest(captured / n)
    modules = {n: dict(path=str(m.__file__), sha256=digest(m.__file__)) for n, m in
        (("daggerml", d), ("builtin", b), ("local", local), ("exchange", ex), ("transfer", transfer), ("native", d._core))}
    cli = Path(d.__file__).parent / "_bin" / "dml"
    modules["cli"] = dict(path=str(cli), sha256=digest(cli))
    for item in modules.values():
        if not Path(item["path"]).resolve().is_relative_to(Path(sys.prefix).resolve()):
            raise RuntimeError("actual isolated installed DML required")
    helpers = {n: dict(path=str(Path(m.__file__).resolve()), sha256=digest(m.__file__)) for n, m in
        (("closure_calls.py", app), ("closure_runtime.py", rt), ("closure_funcs.py", funcs),
         ("reuse_selection.py", selection), ("explicit_reuse.py", explicit_reuse))}
    for n, item in helpers.items():
        if Path(item["path"]) != operational / n or item["sha256"] != hashes[n]:
            raise RuntimeError("ACTUALLY imported helper path/bytes differ BEFORE launch")
    if digest(__file__) != hashes["installed_story.py"] or digest(operational / "offline_read.py") != hashes["offline_read.py"]:
        raise RuntimeError("actual controller/reader bytes differ")
    save(root / "prelaunch-source.json", dict(sources=hashes, installed=modules, actual_helpers=helpers,
        operational_source=str(operational), executing_controller=str(Path(__file__).resolve()),
        reader_source=str(operational / "offline_read.py"), interpreter=sys.executable,
        interpreter_sha256=digest(sys.executable), prefix=sys.prefix))
    active, controls = metadata_controls()
    save(root / "metadata-controls.json", controls)
    path = root / "caller.dml"
    initial = commit = app.initialize(path)
    ca = create(path, commit, "A", "v1", "A")
    commit = app.prepare_arguments(path, commit=ca.commit, values={"a": 13, "b": 29}, inputs_name="inputs", ref="prepared")
    closures, requests, children = [ca], [], []
    for number, label, control, hit in ((1, "A", "fresh", False), (2, "A", "require-selected", True),
        (3, "A", "fresh", False), (4, "B", "require-selected", True), (5, "B", "fresh", False), (6, "C", "try-selected", False)):
        if number == 2:
            with d.Repository(path) as repo, repo.read() as tx:
                entries = app.tree(tx, commit)
            commit = app.promote_defaults(path, commit=commit, map_dependency=entries["map-v2"], scale=entries["scale-C"], ref="defaults")
        if number in (4, 6):
            made = create(path, commit, label, "v2", "B" if number == 4 else "C")
            closures.append(made)
            commit = made.commit
        q = request(path, commit, number, label, control, hit)
        row = request_receipt(q, number)
        save(root / ("request-%d.json" % number), row)
        requests.append(row)
        if hit:
            commit = q.reused.commit
        else:
            if q.reused is not None or (number == 6 and q.decision.reason != "capture-value-mismatch"):
                raise RuntimeError("fresh/miss must remain pending BEFORE explicit dispatch")
            selected, child = execute(path, root, q, number, active)
            children.append(child)
            commit = selected.commit
        save(root / "incremental.json", dict(requests=requests, children=children))
    child_by_number = {row["number"]: row for row in children}
    links = {"closure-%d" % i: c.dag for i, c in enumerate(closures)}
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, commit)
        for row in requests:
            n = row["number"]
            links["request-%d" % n] = d.ObjectId.from_hex(row["request"])
            producer = child_by_number[n] if n in child_by_number else children[0]
            links["selected-result-%d" % n] = d.ObjectId.from_hex(producer["result"])
            links["selected-attempt-%d" % n] = d.ObjectId.from_hex(producer["attempt"])
            if row["satisfaction"] is not None:
                links["satisfaction-%d" % n] = app.tree(tx, d.ObjectId.from_hex(row["satisfaction"]))["reuse-" + row["request_id"]]
        summary = b.record(tx, "example-closure-summary-v1", links=links)
        entries["summary"] = summary
        final = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref("final", final)
    receipt = dict(initial=str(initial), final=str(final), summary=str(summary), repository=str(path),
        requests=requests, children=children, closures=[dict(commit=str(c.commit), basis=str(c.base), dag=str(c.dag),
        binding=str(c.binding), environment=str(c.environment), key=str(c.key)) for c in closures], sources=hashes, installed=modules)
    save(root / "receipt.json", receipt)
    retired = []
    for child in children:
        try:
            os.kill(child["pid"], 0)
        except ProcessLookupError as error:
            if error.errno != errno.ESRCH:
                raise
            retired.append(dict(pid=child["pid"], known_wait_exit=0, absent=True))
        else:
            raise RuntimeError("owned PID exists at retirement: STOP")
    save(root / "retirement.json", dict(children=retired, all_four_known_wait_reaped_absent=True))
    for child in children:
        for key in ("workspace", "packet", "expected"):
            original = Path(child[key])
            original.rename(original.with_name(original.name + ".unavailable"))
    captured.rename(root / "captured-source.unavailable")
    operational.rename(operational.with_name("launch-source.unavailable"))
    with d.Repository(root / "replica.dml", create=True):
        pass
    bundle = transfer.export_commit(path, commit=final)
    imported = transfer.import_commit(root / "replica.dml", bundle, ref="retained")
    save(root / "transfer.json", dict(final=str(imported.commit), rows=imported.object_count,
        bundle_sha256=hashlib.sha256(bundle).hexdigest(), stores={n: digest(root / n / "data.mdb") for n in ("caller.dml", "replica.dml")}))
    return receipt


def read(root):
    """SAME retained history, fixed semantics only; never execute arithmetic sources."""
    root = Path(root)
    receipt = json.loads((root / "receipt.json").read_bytes())
    path, final = root / "replica.dml", d.ObjectId.from_hex(receipt["final"])
    bundle = json.loads(transfer.export_commit(path, commit=final))
    requests, attempts, positions = set(), set(), 0
    with d.Repository(path) as repo, repo.read() as tx:
        for row in bundle["objects"]:
            if row["kind"] != "dag":
                continue
            dag = tx.get_dag(d.ObjectId.from_hex(row["id"]))
            if "role" not in dag.bindings:
                continue
            role = b.scalar(tx, dag.bindings["role"], "string")
            if role == "local-request-v1":
                requests.add(b.scalar(tx, dag.root, "string"))
            elif role == "local-attempt-v1":
                attempts.add(b.scalar(tx, dag.root, "string"))
        if (len(requests), len(attempts)) != (6, 4):
            raise ValueError("native census must be SIX Q/FOUR T")
        for row in receipt["children"]:
            fields = tx.get_dag(d.ObjectId.from_hex(row["result"])).bindings
            trace = b.Inspector(tx, commit=final).trace(b.link(tx, fields["trace"]), request=b.link(tx, fields["request"]), inputs=b.link(tx, fields["inputs"]))
            if len(trace) != 2:
                raise ValueError("each child requires TWO map getter positions")
            positions += len(trace)
    readings = [app.inspect_request(path, commit=d.ObjectId.from_hex(row["commit"]), request=d.ObjectId.from_hex(row["request"]),
        decision_name=row["decision"], satisfaction_commit=None if row["satisfaction"] is None else d.ObjectId.from_hex(row["satisfaction"])) for row in receipt["requests"]]
    expected_links, outputs = {}, []
    child_by_number = {row["number"]: row for row in receipt["children"]}
    for row, decision in zip(receipt["requests"], readings):
        n, c = row["number"], decision.closure
        actual = dict(binding=str(c.binding), closure=str(c.dag), environment=str(c.environment.dag), scale=str(c.environment.scale.dag),
            key=str(c.key), map_binding=str(c.environment.map_binding), inputs=str(decision.inputs.dag), datum=str(decision.inputs.datum),
            action=decision.action, reason=decision.reason, decision_commit=str(decision.commit), basis=str(decision.base))
        if any(row[key] != value for key, value in actual.items()):
            raise ValueError("per-request actual native decision/capture/value differs")
        expected_links["request-%d" % n] = d.ObjectId.from_hex(row["request"])
        producer = app.inspect_producer(path, commit=final, slot=child_by_number[n]["slot"]) if n in child_by_number else decision.selected
        outputs.append(producer.returned.value.value)
        expected_links["selected-result-%d" % n] = producer.selected.result
        expected_links["selected-attempt-%d" % n] = producer.selected.attempt
        with d.Repository(path) as repo, repo.read() as tx:
            q = tx.get_dag(d.ObjectId.from_hex(row["request"]))
            if (b.scalar(tx, q.root, "string"), b.scalar(tx, q.bindings["intent"], "uri"), b.link(tx, q.bindings["binding"]), b.link(tx, q.bindings["inputs"])) != (row["request_id"], app.INTENT, c.binding, decision.inputs.dag):
                raise ValueError("per-request actual own Q differs")
            if row["satisfaction"] is not None:
                expected_links["satisfaction-%d" % n] = app.tree(tx, d.ObjectId.from_hex(row["satisfaction"]))["reuse-" + row["request_id"]]
        if n in child_by_number:
            child = child_by_number[n]
            if (producer.selected.request, producer.selected.attempt, producer.selected.result) != tuple(d.ObjectId.from_hex(child[k]) for k in ("request", "attempt", "result")):
                raise ValueError("actual successful producing Q/T/R differs")
    with d.Repository(path) as repo, repo.read() as tx:
        closures = [app.inspect_closure(tx, final, d.ObjectId.from_hex(row["dag"])) for row in receipt["closures"]]
        for i, (row, c) in enumerate(zip(receipt["closures"], closures)):
            authored = d.ObjectId.from_hex(row["commit"])
            basis = d.ObjectId.from_hex(row["basis"])
            before, after = app.tree(tx, basis), app.tree(tx, authored)
            new = set(after) - set(before)
            if (tx.get_commit(authored).parents != (basis,) or len(new) != 2
                or {n: v for n, v in after.items() if n not in new} != before or set(after[n] for n in new) != {c.binding, c.dag}
                or (str(c.binding), str(c.environment.dag), str(c.key)) != (row["binding"], row["environment"], row["key"])):
                raise ValueError("actual two-name closure publication differs")
            expected_links["closure-%d" % i] = c.dag
        ca, cb, cc = closures
        if not (ca.key == cb.key != cc.key and ca.environment.scale.datum == cb.environment.scale.datum
            and ca.environment.scale.dag != cb.environment.scale.dag and ca.environment.map_binding != cb.environment.map_binding
            and len({r.inputs.datum for r in readings}) == 1):
            raise ValueError("source-distinct equivalent capture/change-scale key differs")
        if [r.closure.dag for r in readings] != [ca.dag, ca.dag, ca.dag, cb.dag, cb.dag, cc.dag]:
            raise ValueError("requested pinned capture choices differ")
        if [readings[i].selected.closure.dag for i in (1, 3)] != [ca.dag, ca.dag]:
            raise ValueError("OLD executed capture differs")
        promoted = readings[1].base
        promotion_parents = tx.get_commit(promoted).parents
        if len(promotion_parents) != 1:
            raise ValueError("default promotion requires one actual parent")
        before, after = app.tree(tx, promotion_parents[0]), app.tree(tx, promoted)
        if (set(before) != set(after)
            or {n for n in before if before[n] != after[n]} != {"default-map", "default-scale"}
            or (before["default-map"], before["default-scale"]) != (ca.environment.map_dependency, ca.environment.scale.dag)
            or (after["default-map"], after["default-scale"]) != (cb.environment.map_dependency, cc.environment.scale.dag)
            or before["closure-A"] != after["closure-A"] or before["binding-A"] != after["binding-A"]
            or after["closure-A"] != ca.dag or after["binding-A"] != ca.binding
            or (app.tree(tx, final)["default-map"], app.tree(tx, final)["default-scale"]) != (cb.environment.map_dependency, cc.environment.scale.dag)):
            raise ValueError("actual v2/scale3 default promotion versus pinned A differs")
        summary = d.ObjectId.from_hex(receipt["summary"])
        fields = b.shape(tx, summary, ("role", *expected_links), "example-closure-summary-v1")
        if app.tree(tx, final)["summary"] != summary or {n: b.link(tx, fields[n]) for n in expected_links} != expected_links:
            raise ValueError("actual summary exact links differ")
    if positions != 8 or outputs != [84, 84, 84, 84, 84, 126]:
        raise ValueError("EIGHT getter/six satisfaction census differs")
    selected = app.inspect_producer(path, commit=final, slot=app.SLOT)
    if selected.selected.request != d.ObjectId.from_hex(receipt["requests"][0]["request"]):
        raise ValueError("fresh work must NOT auto-adopt")
    for row in receipt["children"]:
        custody = json.loads((root / ("child-%d.json" % row["number"])).read_bytes())
        if custody["children"] != [dict(pid=row["pid"], exit=0, reaped=True, actual_wait=[dict(returned=True, exit=0)])]:
            raise ValueError("incremental direct-child wait/reap custody differs")
        for key in ("workspace", "packet", "expected"):
            original = Path(row[key])
            if original.exists() or not original.with_name(original.name + ".unavailable").exists():
                raise ValueError("owned originals must be unavailable/retained")
    retirement = json.loads((root / "retirement.json").read_bytes())
    if not retirement["all_four_known_wait_reaped_absent"] or retirement["children"] != [dict(pid=r["pid"], known_wait_exit=0, absent=True) for r in receipt["children"]]:
        raise ValueError("known wait/reaped/absent retirement differs")
    return dict(requests=6, attempts=4, builtin_positions=8, results=outputs, closure_objects=len(bundle["objects"]), requested_and_OLD_executed_capture_separate=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "metadata-controls"))
    parser.add_argument("root", nargs="?")
    args = parser.parse_args(argv)
    if args.mode == "run" and args.root is None:
        raise ValueError("explicit fresh owned root required")
    print(json.dumps(run(args.root) if args.mode == "run" else metadata_controls()[1], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
