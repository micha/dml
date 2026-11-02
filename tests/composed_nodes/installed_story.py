"""Explicit sole installed EIGHT-Q/SIX-local/TEN-getter acceptance; not a default fixture."""

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
import composed_node_calls as app
import composed_node_funcs as funcs
import explicit_reuse
import reuse_selection as selection


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def request(path, commit, intent, number, *, hit=False):
    func, _ = app.contract(intent)
    return app.record_request(path, commit=commit, intent=intent, binding_name=func + "-binding",
                              inputs_name="inputs-%d" % number, decision_name="decision-%d" % number,
                              decision_ref="decision-%d" % number, submission_ref="submission-%d" % number,
                              composition_name=None if intent == app.ADD else "composition-%d" % number,
                              control="fresh" if intent == app.ADD else "try-selected",
                              reuse_ref="satisfaction-%d" % number if hit else None)


def request_receipt(q, number):
    return dict(number=number, commit=str(q.recorded.commit), request=str(q.recorded.request),
                request_id=q.recorded.request_id, decision=q.decision.name, decision_commit=str(q.decision.commit),
                basis=str(q.decision.base), intent=q.decision.intent, inputs=str(q.recorded.inputs),
                datum=str(q.decision.inputs.datum), action=q.decision.action, reason=q.decision.reason,
                composition=None if q.decision.composition is None else str(q.decision.composition.dag),
                satisfaction=None if q.reused is None else str(q.reused.commit))


def execute(path, root, q, number, active):
    workspace = root / ("workspace-%d" % number)
    spec = ex.prepare_exchange(path, commit=q.recorded.commit, request=q.recorded.request,
                               binding_name=q.recorded.binding_name, inputs_name=q.recorded.inputs_name,
                               intent_uri=q.recorded.intent_uri, worker_ref="work", workspace=workspace)
    expected = root / ("expected-%d.json" % number)
    ex.save_exchange_handle(expected, ex.ExchangeHandle(workspace, spec))
    save(root / ("dispatch-%d.json" % number), dict(number=number, submission=str(q.recorded.commit),
         request=str(q.recorded.request), binding=str(spec.binding), inputs=str(spec.inputs),
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
        if Path(command[1]).read_bytes() != captured:
            raise RuntimeError("actual entry differs from captured source bytes")
        process = popen(*args, **kwargs)
        children.append(process)
        waited = process.wait
        process.wait_receipts = []
        def actual_wait(*wait_args, **wait_kwargs):
            try:
                result = waited(*wait_args, **wait_kwargs)
            except BaseException as error:
                process.wait_receipts.append(dict(returned=False, error=type(error).__name__))
                save(root / ("wait-%d.json" % number), process.wait_receipts)
                raise
            process.wait_receipts.append(dict(returned=True, exit=result))
            save(root / ("wait-%d.json" % number), process.wait_receipts)
            return result
        process.wait = actual_wait
        save(root / ("spawn-%d.json" % number), dict(number=number, request=str(context.request),
             submission=str(q.recorded.commit), pid=process.pid, args=command,
             pre_dispatch=str(context.pre_dispatch), attempt_id=context.attempt_id,
             publication_ref=context.publication_ref, entry_sha256=hashlib.sha256(captured).hexdigest()))
        return process
    subprocess.Popen = tracked
    try:
        active[0] = False  # ONLY bounded existing synchronous execution boundary.
        run = ex.execute_exchange(workspace)
    finally:
        active[0] = True  # BEFORE observation/import/S/semantic inspection.
        subprocess.Popen = popen
        save(root / ("child-%d.json" % number), dict(number=number, request=str(q.recorded.request),
             children=[dict(pid=c.pid, exit=c.poll(), reaped=c.returncode is not None,
                            actual_wait=c.wait_receipts) for c in children],
             outcome=None if run is None else run.outcome,
             completion=None if run is None else str(run.final_commit),
             result=None if run is None or run.result is None else str(run.result)))
    if (run is None or len(children) != 1 or children[0].poll() is None or
        children[0].returncode != 0 or run.outcome != "success" or
        children[0].wait_receipts != [dict(returned=True, exit=0)]):
        raise RuntimeError("failed/uncertain child custody: STOP/no relaunch")
    # The actual direct child is known wait-reaped BEFORE completion inspection/import.
    observation = ex.observe_exchange(ex.ExchangeHandle(workspace, spec), packet=root / ("packet-%d" % number))
    received = ex.receive_observation(path, packet=observation.packet, expected=spec, ref="completion-%d" % number)
    slot = "producer-add-%d" % number if q.decision.intent == app.ADD else app.SLOT if number == 2 else "fresh-double"
    selected = selection.select(path, commit=received.commit, slot=slot,
                                 binding_name=q.recorded.binding_name, inputs_name=q.recorded.inputs_name,
                                 intent_uri=q.recorded.intent_uri, packet=observation.packet,
                                 expected_file=expected, ref=slot)
    producer = app.inspect_producer(path, commit=selected.commit, slot=slot, intent=q.decision.intent)
    child = dict(number=number, pid=children[0].pid, exit=0, reaped=True,
                 request=str(q.recorded.request), request_id=q.recorded.request_id,
                 attempt=str(selected.attempt), attempt_id=selected.attempt_id, result=str(selected.result),
                 completion=str(selected.completion), pre_dispatch=str(run.context.pre_dispatch),
                 selection=str(selected.dag), selection_commit=str(selected.commit), slot=slot,
                 workspace=str(workspace), packet=str(observation.packet), expected=str(expected),
                 value=producer.returned.value.value)
    save(root / ("completed-%d.json" % number), child)
    return selected, child


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


def run(root):
    root = Path(root).resolve()
    root.mkdir()
    sources = root / "captured-source"
    sources.mkdir()
    operational = Path(__file__).resolve().parent
    if operational != root.parent / "launch-source":
        raise RuntimeError("launch ONLY the measured owned operational six-file copy outside checkout")
    hashes = {}
    for origin in [Path(__file__), Path(__file__).with_name("offline_read.py"),
                   *(EXAMPLES / (n + ".py") for n in ("composed_node_calls", "composed_node_funcs", "reuse_selection", "explicit_reuse"))]:
        target = sources / origin.name
        shutil.copyfile(origin, target)
        hashes[origin.name] = digest(target)
    modules = {n: dict(path=str(m.__file__), sha256=digest(m.__file__)) for n, m in
               (("daggerml", d), ("builtin", b), ("local", local), ("exchange", ex), ("transfer", transfer), ("native", d._core))}
    cli = Path(d.__file__).parent / "_bin" / "dml"
    modules["cli"] = dict(path=str(cli), sha256=digest(cli))
    for item in modules.values():
        if not Path(item["path"]).resolve().is_relative_to(Path(sys.prefix).resolve()):
            raise RuntimeError("actual isolated installed DML required, not checkout runtime")
    actual_helpers = {n: dict(path=str(Path(m.__file__).resolve()), sha256=digest(m.__file__)) for n, m in
                      (("composed_node_calls.py", app), ("composed_node_funcs.py", funcs),
                       ("reuse_selection.py", selection), ("explicit_reuse.py", explicit_reuse))}
    for n, item in actual_helpers.items():
        if Path(item["path"]) != operational / n or item["sha256"] != hashes[n]:
            raise RuntimeError("ACTUALLY imported helper path/bytes differ BEFORE launch")
    if digest(__file__) != hashes["installed_story.py"] or digest(operational / "offline_read.py") != hashes["offline_read.py"]:
        raise RuntimeError("ACTUAL controller/reader source differs BEFORE launch")
    save(root / "prelaunch-source.json", dict(sources=hashes, installed=modules, actual_helpers=actual_helpers,
         operational_source=str(operational), executing_controller=str(Path(__file__).resolve()),
         reader_source=str(operational / "offline_read.py"), interpreter=sys.executable,
         interpreter_sha256=digest(sys.executable), prefix=sys.prefix))
    active, controls = metadata_controls()
    save(root / "metadata-controls.json", controls)
    path = root / "caller.dml"
    commit = initial = app.initialize(path, sys.executable)
    requests, children, compositions = [], [], []
    for number, values in ((1, {"a": 13, "b": 29}), (3, {"a": 13, "b": 29}),
                           (5, {"a": 29, "b": 13}), (7, {"a": 13, "b": 30})):
        commit = app.prepare_add(path, commit=commit, values=values, inputs_name="inputs-%d" % number, ref="prepared-%d" % number)
        add = request(path, commit, app.ADD, number)
        add_row = request_receipt(add, number)
        save(root / ("request-%d.json" % number), add_row)
        requests.append(add_row)
        upstream, child = execute(path, root, add, number, active)
        children.append(child)
        next_number = number + 1
        composition = app.compose_double(path, commit=upstream.commit, producer_slot=upstream.slot,
                                         inputs_name="inputs-%d" % next_number,
                                         composition_name="composition-%d" % next_number, ref="composed-%d" % next_number)
        compositions.append(dict(number=next_number, commit=str(composition.commit), basis=str(composition.base),
                                 dag=str(composition.dag), inputs=str(composition.inputs.dag),
                                 selection=str(upstream.dag), attempt=str(upstream.attempt), result=str(upstream.result)))
        save(root / ("composition-%d.json" % next_number), compositions[-1])
        double = request(path, composition.commit, app.DOUBLE, next_number, hit=next_number in (4, 6))
        row = request_receipt(double, next_number)
        save(root / ("request-%d.json" % next_number), row)
        requests.append(row)
        if next_number in (4, 6):
            if double.reused is None:
                raise RuntimeError("equal full MAP must reuse OLD double without dispatch")
            commit = double.reused.commit
        else:
            if double.reused is not None or (next_number == 8 and double.decision.reason != "value-mismatch"):
                raise RuntimeError("fresh double must remain pending BEFORE explicit dispatch")
            downstream, child = execute(path, root, double, next_number, active)
            children.append(child)
            commit = downstream.commit
        save(root / "incremental.json", dict(requests=requests, children=children, compositions=compositions))
    results = {row["number"]: d.ObjectId.from_hex(row["result"]) for row in children}
    attempts = {row["number"]: d.ObjectId.from_hex(row["attempt"]) for row in children}
    satisfactions = {}
    for row in requests:
        if row["satisfaction"] is not None:
            with d.Repository(path) as repo, repo.read() as tx:
                decision = app.tree(tx, d.ObjectId.from_hex(row["satisfaction"]))
                w = decision["reuse-" + row["request_id"]]
                fields = b.shape(tx, w, ("role", "request", "attempt", "result"), app.W_ROLE, "result")
                results[row["number"]], attempts[row["number"]] = b.link(tx, fields["result"]), b.link(tx, fields["attempt"])
                satisfactions[row["number"]] = w
    with d.Repository(path) as repo, repo.write() as tx:
        # Ordinary summary retains ACTUAL requested chains and separate satisfactions.
        entries = app.tree(tx, commit)
        links = {"request-%d" % row["number"]: d.ObjectId.from_hex(row["request"]) for row in requests}
        links.update({"composition-%d" % row["number"]: d.ObjectId.from_hex(row["dag"]) for row in compositions})
        links.update({"selected-result-%d" % n: oid for n, oid in results.items()})
        links.update({"selected-attempt-%d" % n: oid for n, oid in attempts.items()})
        links.update({"satisfaction-%d" % n: oid for n, oid in satisfactions.items()})
        summary = b.record(tx, "example-composed-node-summary-v1", links=links)
        entries["summary"] = summary
        final = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref("final", final)
    receipt = dict(initial=str(initial), final=str(final), summary=str(summary), repository=str(path),
                   requests=requests, children=children, compositions=compositions, sources=hashes, installed=modules)
    save(root / "receipt.json", receipt)
    retired = []
    for child in children:
        try:
            os.kill(child["pid"], 0)  # Existence ONLY; no signal sent to a known owned PID.
        except ProcessLookupError as error:
            if error.errno != errno.ESRCH:
                raise
            retired.append(dict(pid=child["pid"], known_wait_exit=0, absent=True))
        else:
            raise RuntimeError("owned child PID still exists at retirement: STOP")
    save(root / "retirement.json", dict(children=retired, all_six_known_wait_reaped_absent=True))
    # ONLY owned originals AFTER all six children known wait-reaped AND absent.
    for child in children:
        for key in ("workspace", "packet", "expected"):
            original = Path(child[key])
            original.rename(original.with_name(original.name + ".unavailable"))
    sources.rename(root / "captured-source.unavailable")
    operational.rename(operational.with_name("launch-source.unavailable"))
    with d.Repository(root / "replica.dml", create=True):
        pass
    bundle = transfer.export_commit(path, commit=final)
    imported = transfer.import_commit(root / "replica.dml", bundle, ref="retained")
    save(root / "transfer.json", dict(final=str(imported.commit), rows=imported.object_count,
         bundle_sha256=hashlib.sha256(bundle).hexdigest(), stores={n: digest(root / n / "data.mdb") for n in ("caller.dml", "replica.dml")}))
    return receipt


def read(root):
    """SAME pinned history only; no arithmetic source execution or recording dispatcher."""
    root = Path(root)
    receipt = json.loads((root / "receipt.json").read_bytes())
    path = root / "replica.dml"
    final = d.ObjectId.from_hex(receipt["final"])
    bundle = json.loads(transfer.export_commit(path, commit=final))
    requests, attempts = set(), set()
    with d.Repository(path) as repo, repo.read() as tx:
        for row in bundle["objects"]:
            if row["kind"] == "dag":
                got = tx.get_dag(d.ObjectId.from_hex(row["id"]))
                if "role" not in got.bindings:
                    continue
                role = b.scalar(tx, got.bindings["role"], "string")
                if role == "local-request-v1":
                    requests.add(b.scalar(tx, got.root, "string"))
                elif role == "local-attempt-v1":
                    attempts.add(b.scalar(tx, got.root, "string"))
        if (len(requests), len(attempts)) != (8, 6):
            raise ValueError("native census must be EIGHT Q/SIX T")
        positions, outputs = 0, []
        for row in receipt["children"]:
            result = d.ObjectId.from_hex(row["result"])
            inspector = b.Inspector(tx, commit=final)
            returned = inspector.node(result)
            fields = tx.get_dag(result).bindings
            trace = inspector.trace(b.link(tx, fields["trace"]), request=b.link(tx, fields["request"]), inputs=b.link(tx, fields["inputs"]))
            if len(trace) != (2 if row["number"] in (1, 3, 5, 7) else 1):
                raise ValueError("getter positions differ")
            positions += len(trace)
            outputs.append(returned.value.value)
        if (positions, outputs) != (10, [42, 84, 42, 42, 43, 86]):
            raise ValueError("TEN child getters/results differ")
        keys = [app.inspect_arguments(tx, final, d.ObjectId.from_hex(row["inputs"]), row["intent"])[0].datum for row in receipt["requests"]]
        if not (keys[0] == keys[2] and len({keys[0], keys[4], keys[6]}) == 3
                and keys[1] == keys[3] == keys[5] and keys[7] != keys[1]):
            raise ValueError("canonical upstream distinct/downstream convergent keys differ")
    readings = [app.inspect_request(path, commit=d.ObjectId.from_hex(row["commit"]), request=d.ObjectId.from_hex(row["request"]),
                decision_name=row["decision"], satisfaction_commit=None if row["satisfaction"] is None else d.ObjectId.from_hex(row["satisfaction"])) for row in receipt["requests"]]
    for index in (3, 5):
        got = readings[index]
        if (got.action != "reuse-selected" or got.composition.producer.selected.attempt != d.ObjectId.from_hex(receipt["compositions"][index // 2]["attempt"])
            or got.selected.decision.composition.producer.selected.attempt != d.ObjectId.from_hex(receipt["children"][0]["attempt"])
            or got.selected.selected.attempt != d.ObjectId.from_hex(receipt["children"][1]["attempt"])):
            raise ValueError("requested producer versus OLD executed producer differs")
    selected = app.inspect_producer(path, commit=final, slot=app.SLOT, intent=app.DOUBLE)
    if selected.selected.request != d.ObjectId.from_hex(receipt["requests"][1]["request"]):
        raise ValueError("fresh86 must NOT auto-adopt")
    expected_links, actual_values = {}, []
    child_by_number = {row["number"]: row for row in receipt["children"]}
    for row, decision in zip(receipt["requests"], readings):
        n = row["number"]
        if (decision.commit != d.ObjectId.from_hex(row["decision_commit"]) or decision.base != d.ObjectId.from_hex(row["basis"])
            or decision.intent != row["intent"] or decision.inputs.dag != d.ObjectId.from_hex(row["inputs"])
            or str(decision.inputs.datum) != row["datum"] or (decision.action, decision.reason) != (row["action"], row["reason"])):
            raise ValueError("per-request ACTUAL decision/input/value/action identity differs")
        expected_links["request-%d" % n] = d.ObjectId.from_hex(row["request"])
        if decision.composition is not None:
            if decision.composition.dag != d.ObjectId.from_hex(row["composition"]):
                raise ValueError("per-request ACTUAL composition identity differs")
            expected_links["composition-%d" % n] = decision.composition.dag
        if n in child_by_number:
            child = child_by_number[n]
            producer = app.inspect_producer(path, commit=final, slot=child["slot"], intent=decision.intent)
            if (producer.selected.request != d.ObjectId.from_hex(row["request"])
                or producer.selected.attempt != d.ObjectId.from_hex(child["attempt"])
                or producer.selected.result != d.ObjectId.from_hex(child["result"])):
                raise ValueError("actual successful producing Q/T/R identity differs")
        else:
            producer = decision.selected
            with d.Repository(path) as repo, repo.read() as tx:
                w = app.tree(tx, d.ObjectId.from_hex(row["satisfaction"]))["reuse-" + row["request_id"]]
                expected_links["satisfaction-%d" % n] = w
        actual_values.append(producer.returned.value.value)
        expected_links["selected-result-%d" % n] = producer.selected.result
        expected_links["selected-attempt-%d" % n] = producer.selected.attempt
        with d.Repository(path) as repo, repo.read() as tx:
            q = tx.get_dag(d.ObjectId.from_hex(row["request"]))
            if (b.scalar(tx, q.root, "string") != row["request_id"]
                or b.scalar(tx, q.bindings["intent"], "uri") != decision.intent
                or b.link(tx, q.bindings["inputs"]) != decision.inputs.dag
                or b.link(tx, q.bindings["binding"]) != decision.binding):
                raise ValueError("per-request ACTUAL own Q dimensions differ")
    if actual_values != [42, 84, 42, 84, 42, 84, 43, 86]:
        raise ValueError("ACTUAL eight satisfactions differ")
    with d.Repository(path) as repo, repo.read() as tx:
        summary = d.ObjectId.from_hex(receipt["summary"])
        if app.tree(tx, final)["summary"] != summary:
            raise ValueError("actual summary tree link differs")
        fields = b.shape(tx, summary, ("role", *expected_links), "example-composed-node-summary-v1")
        if {n: b.link(tx, fields[n]) for n in expected_links} != expected_links:
            raise ValueError("actual summary exact requested/selected/W links differ")
    for row in receipt["children"]:
        app.inspect_producer(path, commit=final, slot=row["slot"], intent=app.ADD if row["number"] in (1, 3, 5, 7) else app.DOUBLE)
        custody = json.loads((root / ("child-%d.json" % row["number"])).read_bytes())
        if custody["children"] != [{"pid": row["pid"], "exit": 0, "reaped": True,
                                    "actual_wait": [{"returned": True, "exit": 0}]}]:
            raise ValueError("incremental child custody differs")
        for key in ("workspace", "packet", "expected"):
            original = Path(row[key])
            if original.exists() or not original.with_name(original.name + ".unavailable").exists():
                raise ValueError("owned original must be unavailable and retained")
    retirement = json.loads((root / "retirement.json").read_bytes())
    if (not retirement["all_six_known_wait_reaped_absent"] or retirement["children"] != [dict(pid=row["pid"], known_wait_exit=0, absent=True) for row in receipt["children"]]):
        raise ValueError("known wait/reaped/absent retirement differs")
    operational = root.parent / "launch-source"
    if operational.exists() or not operational.with_name("launch-source.unavailable").is_dir():
        raise ValueError("owned operational source copy must be unavailable and retained")
    return dict(requests=8, attempts=6, builtin_positions=10, results=actual_values,
                closure_objects=len(bundle["objects"]), requested_and_executed_chains_separate=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "metadata-controls"))
    parser.add_argument("root", nargs="?")
    args = parser.parse_args(argv)
    if args.mode == "run" and args.root is None:
        raise ValueError("explicit fresh owned story root required")
    result = run(args.root) if args.mode == "run" else metadata_controls()[1]
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
