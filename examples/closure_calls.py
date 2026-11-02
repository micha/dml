"""Fixed example-local immutable captures and ONE-S capture-aware own-Q/W bridge.

Public APIs only. No nested ordinary calls, generic evaluator or inherited key change.
"""

from dataclasses import dataclass
from pathlib import Path
import tempfile

import daggerml as d
from daggerml import builtin as b, exchange as ex, local, transfer
import closure_runtime as rt
import reuse_selection as selection

INTENT, SLOT = rt.INTENT, rt.SLOT
name, tree, inspect_arguments = rt.name, rt.tree, rt.inspect_arguments
W_ROLE = "example-explicit-reuse-v1"


def sources():
    return tuple(Path(__file__).with_name(n).read_bytes() for n in ("closure_runtime.py", "closure_funcs.py"))


def inspect_closure(tx, commit, dag):
    return rt.inspect_closure(tx, commit, dag, *sources())


def initialize(path):
    """Prepare retained constants/getters at explicit bootstrap boundaries; no calls/Q/T."""
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        entries = {}
        for label, uri, func in (("map-v1", "map/get/v1", b.MAP_GET), ("map-v2", "map/get/v2", b.MAP_GET), ("list-v1", "list/get/v1", b.LIST_GET)):
            binding = b.put_binding(tx, source_uri="dml://source/builtin/" + uri)
            entries[label] = b.record(tx, rt.F_ROLE, values={"func": d.Datum.uri(func)}, links={"binding": binding})
        for label, value in (("origin-A", 2), ("origin-B", 2), ("origin-C", 3)):
            fields = {"origin": b.literal(tx, label), "value": b.literal(tx, d.Datum.i64(value))}
            entries[label] = tx.put_dag(root=fields["value"], bindings=fields)
        base = tx.put_commit(tx.put_tree(entries))
        tx.create_ref("bootstrap", base)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, base)
        with b.Recorder(tx, commit=base) as rec:
            for label in ("A", "B", "C"):
                entries["scale-" + label] = rec.dag(rec.source(entries["origin-" + label], "value"))
        entries.update({"default-map": entries["map-v1"], "default-scale": entries["scale-A"]})
        commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
        tx.create_ref("main", commit)
    return commit


@dataclass(frozen=True)
class Created:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    binding: d.ObjectId
    environment: d.ObjectId
    key: d.ObjectId


def create_closure(path, *, commit, map_dependency, list_dependency, scale, binding_name,
                   closure_name, interpreter, ref, timeout_ms=10000, map_size=0):
    for n in (binding_name, closure_name, ref):
        name(n)
    if binding_name == closure_name:
        raise ValueError("closure/binding names must differ")
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        inspector = b.Inspector(tx, commit=commit)
        rt.inspect_dependency(tx, inspector, map_dependency, b.MAP_GET)
        rt.inspect_dependency(tx, inspector, list_dependency, b.LIST_GET)
        value = rt.inspect_scale(tx, inspector, scale)
    runtime_source, logical_source = sources()
    with d.Repository(path, map_size=map_size) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if binding_name in entries or closure_name in entries:
            raise ValueError("both closure publication names must be absent")
        environment = b.record(tx, rt.E_ROLE, links={"map-get": map_dependency, "list-get": list_dependency, "scale": scale})
        key = b.record(tx, rt.K_ROLE, values={"map-get": d.Datum.uri(b.MAP_GET), "list-get": d.Datum.uri(b.LIST_GET)},
                       nodes={"scale": tx.put_literal(value.datum)})
        binding = local.put_local_binding(tx, source=rt.capture(environment, runtime_source, logical_source),
                                          interpreter=interpreter, timeout_ms=timeout_ms)
        closure = b.record(tx, rt.C_ROLE, values={"intent": d.Datum.uri(INTENT)},
                           links={"binding": binding, "environment": environment, "capture-key": key})
        entries.update({binding_name: binding, closure_name: closure})
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = Created(commit, authored, closure, binding, environment, key)
    return response


def promote_defaults(path, *, commit, map_dependency, scale, ref):
    name(ref)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        inspector = b.Inspector(tx, commit=commit)
        rt.inspect_dependency(tx, inspector, map_dependency, b.MAP_GET)
        rt.inspect_scale(tx, inspector, scale)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if not {"default-map", "default-scale"} <= set(entries):
            raise ValueError("default entries must already exist")
        entries.update({"default-map": map_dependency, "default-scale": scale})
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
    return authored


def prepare_arguments(path, *, commit, values, inputs_name, ref):
    name(inputs_name)
    name(ref)
    items = list(values.items()) if hasattr(values, "items") else list(values)
    if len(items) != 2 or {key for key, value in items} != {"a", "b"}:
        raise ValueError("invocation requires EXACT a,b")
    for key, value in items:
        d.Datum.i64(value)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if inputs_name in entries:
            raise ValueError("inputs name must be absent")
        with b.Recorder(tx, commit=commit) as rec:
            full = rec.arguments([(key, rec.literal(d.Datum.i64(value))) for key, value in items])
            inputs = rec.dag(full)
        entries[inputs_name] = inputs
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
    return authored


def prepare(path, commit, binding_name, inputs_name, request=None):
    with tempfile.TemporaryDirectory(prefix="dml-closure-validation-") as scratch:
        return ex.prepare_exchange(path, commit=commit, binding_name=binding_name,
            inputs_name=inputs_name, intent_uri=INTENT, request=request,
            worker_ref="validation", workspace=Path(scratch) / "input")


@dataclass(frozen=True)
class Producer:
    selected: selection.Selection
    closure: rt.Closure
    inputs: b.Description
    returned: b.Description
    decision: object


def inspect_producer(path, *, commit, slot, depth=0):
    if depth > 8:
        raise ValueError("original decision selection chain exceeds fixed bound")
    selected = selection.inspect(path, commit=commit, slot=slot)
    if selected.intent_uri != INTENT:
        raise ValueError("selected intent differs")
    with d.Repository(path) as repo, repo.read() as tx:
        pre = tx.get_commit(selected.completion).parents[0]
        cq = tx.get_commit(pre).parents[0]
        dc = tx.get_commit(cq).parents[0]
        parents = tx.get_commit(dc).parents
        if len(parents) != 1:
            raise ValueError("producer decision must have one basis")
        additions = set(tree(tx, dc)) - set(tree(tx, parents[0]))
        if len(additions) != 1:
            raise ValueError("producer decision must add one name")
        decision_name = additions.pop()
    decision = inspect_request(path, commit=cq, request=selected.request, decision_name=decision_name, depth=depth + 1)
    if (decision.action != "execute-fresh" or decision.closure.binding != selected.binding
        or decision.inputs.dag != selected.inputs):
        raise ValueError("selected ORIGINAL fresh capture/inputs differs")
    with d.Repository(path) as repo, repo.read() as tx:
        inspector = b.Inspector(tx, commit=commit)
        returned = inspector.node(selected.result)
        fields = b.shape(tx, selected.result, ("role", "returned", "value", "trace", "request", "inputs"), b.RETURN_ROLE, "value")
        if (returned.value.kind != "i64" or (b.link(tx, fields["request"]), b.link(tx, fields["inputs"])) != (selected.request, selected.inputs)):
            raise ValueError("selected return ORIGINAL Q/full input differs")
        trace = inspector.trace(b.link(tx, fields["trace"]), request=selected.request, inputs=selected.inputs)
        if len(trace) != 2:
            raise ValueError("selected trace requires EXACT two getter positions")
        for operation, expected_key in zip(trace, ("a", "b")):
            op = b.shape(tx, operation.dag, ("role", "func", "binding", "arguments", "value"), b.OPERATION_ROLE, "value")
            args_id = b.link(tx, op["arguments"])
            args = tx.get_dag(args_id).bindings
            ledger = tx.get_dag(b.link(tx, args["entries"]))
            sources_by_key = {}
            for n in ("arg-00", "arg-01"):
                row = b.shape(tx, b.link(tx, ledger.bindings[n]), ("role", "key", "source"), b.ENTRY_ROLE)
                sources_by_key[b.scalar(tx, row["key"], "string")] = b.link(tx, row["source"])
            if (b.scalar(tx, op["func"], "uri") != b.MAP_GET
                or b.link(tx, op["binding"]) != decision.closure.environment.map_binding
                or set(sources_by_key) != {"map", "key"} or sources_by_key["map"] != selected.inputs
                or inspector.node(sources_by_key["key"]).value != d.Datum.string(expected_key)):
                raise ValueError("selected ORIGINAL getter binding/source/order differs")
        # Literal result records no arithmetic provenance; inspection never reruns arithmetic.
        b.shape(tx, b.link(tx, fields["returned"]), ("role", "value"), b.LITERAL_ROLE, "value")
    return Producer(selected, decision.closure, decision.inputs, returned, decision)


@dataclass(frozen=True)
class Decision:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    closure_name: str
    binding_name: str
    inputs_name: str
    closure: rt.Closure
    inputs: b.Description
    control: str
    action: str
    reason: str
    selected: object


@dataclass(frozen=True)
class Satisfaction:
    commit: d.ObjectId
    dag: d.ObjectId
    attempt: d.ObjectId
    result: d.ObjectId


@dataclass(frozen=True)
class Request:
    decision: Decision
    recorded: ex.RecordedRequest
    reused: object


def resolve(path, commit, closure_name, binding_name, inputs_name, control, depth=0):
    for n in (closure_name, binding_name, inputs_name):
        name(n)
    if control not in ("fresh", "try-selected", "require-selected"):
        raise ValueError("unsupported explicit control")
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        entries = tree(tx, commit)
        closure = inspect_closure(tx, commit, entries[closure_name])
        full = inspect_arguments(tx, commit, entries[inputs_name])
        if entries[binding_name] != closure.binding:
            raise ValueError("requested named binding differs from capture")
        present = SLOT in entries
    spec = prepare(path, commit, binding_name, inputs_name)
    if (spec.binding, spec.inputs) != (closure.binding, full.dag):
        raise ValueError("public preparation dimensions differ")
    # Validate ORIGINAL producer even for explicit fresh or a computational mismatch.
    selected = inspect_producer(path, commit=commit, slot=SLOT, depth=depth) if present else None
    hit = selected is not None and (selected.closure.key, selected.inputs.datum) == (closure.key, full.datum)
    if control == "fresh":
        action, reason = "execute-fresh", "explicit-fresh"
    elif hit:
        action, reason = "reuse-selected", "selected-capture-value"
    elif control == "require-selected":
        raise ValueError("required selection has no capture/value match")
    else:
        action, reason = "execute-fresh", "no-selection" if selected is None else "capture-value-mismatch"
    return closure, full, selected, action, reason


def claims(closure_name, binding_name, inputs_name, control, resolved):
    closure, full, selected, action, reason = resolved
    values = {"intent": d.Datum.uri(INTENT), "closure-name": closure_name, "binding-name": binding_name,
              "inputs-name": inputs_name, "control": control, "action": action, "reason": reason}
    links = {"closure": closure.dag, "binding": closure.binding, "environment": closure.environment.dag,
             "capture-key": closure.key, "inputs": full.dag}
    if selected is not None:
        links["selection"] = selected.selected.dag
    return values, links


def response(base, commit, dag, decision_name, closure_name, binding_name, inputs_name, control, resolved):
    closure, full, selected, action, reason = resolved
    return Decision(base, commit, dag, decision_name, closure_name, binding_name, inputs_name,
                    closure, full, control, action, reason, selected)


def inspect_decision(path, *, commit, decision_name, depth=0):
    with d.Repository(path) as repo, repo.read() as tx:
        base, dag, values, closure, full = rt.decision_fields(tx, commit, decision_name, *sources())
    resolved = resolve(path, base, values["closure-name"], values["binding-name"], values["inputs-name"], values["control"], depth)
    if resolved[:2] != (closure, full) or resolved[-2:] != (values["action"], values["reason"]):
        raise ValueError("decision claims differ from actual capture-aware resolution")
    return response(base, commit, dag, decision_name, values["closure-name"], values["binding-name"], values["inputs-name"], values["control"], resolved)


def inspect_request(path, *, commit, request, decision_name, satisfaction_commit=None, depth=0):
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("submission requires one actual decision parent")
    decision = inspect_decision(path, commit=parents[0], decision_name=decision_name, depth=depth)
    spec = prepare(path, commit, decision.binding_name, decision.inputs_name, request)
    if (spec.binding, spec.inputs) != (decision.closure.binding, decision.inputs.dag):
        raise ValueError("own Q dimensions differ")
    if satisfaction_commit is not None:
        if decision.action != "reuse-selected":
            raise ValueError("fresh decision cannot claim W")
        with d.Repository(path) as repo, repo.read() as tx:
            entries = tree(tx, satisfaction_commit)
            qid = b.scalar(tx, tx.get_dag(request).root, "string")
            dag = entries.pop("reuse-" + qid)
            if tx.get_commit(satisfaction_commit).parents != (commit,) or entries != tree(tx, commit):
                raise ValueError("W must add ONLY satisfaction to own Q")
            fields = b.shape(tx, dag, ("role", "request", "attempt", "result"), W_ROLE, "result")
            old = decision.selected.selected
            if tuple(b.link(tx, fields[n]) for n in ("request", "attempt", "result")) != (request, old.attempt, old.result):
                raise ValueError("W ownQ/OLD producingT/R differs")
        transfer.export_commit(path, commit=satisfaction_commit)
    return decision


def publish_reuse(path, recorded, selected, ref):
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, recorded.commit)
        key = "reuse-" + recorded.request_id
        if key in entries:
            raise ValueError("satisfaction already present")
        dag = b.record(tx, W_ROLE, links={"request": recorded.request, "attempt": selected.attempt, "result": selected.result}, root="result")
        entries[key] = dag
        commit = tx.put_commit(tx.put_tree(entries), parents=(recorded.commit,))
        tx.create_ref(ref, commit)
        got = Satisfaction(commit, dag, selected.attempt, selected.result)
    return got


def record_request(path, *, commit, closure_name, binding_name, inputs_name, decision_name,
                   decision_ref, submission_ref, control="fresh", reuse_ref=None):
    for n in (closure_name, binding_name, inputs_name, decision_name, decision_ref, submission_ref):
        name(n)
    if reuse_ref is not None:
        name(reuse_ref)
    if (len({decision_ref, submission_ref, reuse_ref}) != 3
        or len({closure_name, binding_name, inputs_name, decision_name, SLOT}) != 5
        or decision_name.startswith(("request-q-", "attempt-a-", "publication-a-", "reuse-q-"))):
        raise ValueError("publication names/refs must differ")
    resolved = resolve(path, commit, closure_name, binding_name, inputs_name, control)
    if (reuse_ref is not None) != (resolved[-2] == "reuse-selected"):
        raise ValueError("reuse ref required ONLY on selected hit")
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if decision_name in entries:
            raise ValueError("decision name must be absent")
        values, links = claims(closure_name, binding_name, inputs_name, control, resolved)
        dag = b.record(tx, rt.D_ROLE, values=values, links=links,
                       nodes={"value": tx.put_literal(resolved[1].datum)}, root="inputs")
        entries[decision_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(decision_ref, authored)
        decision = response(commit, authored, dag, decision_name, closure_name, binding_name, inputs_name, control, resolved)
    recorded = ex.record_exchange_request(path, commit=authored, binding_name=binding_name,
                                          inputs_name=inputs_name, intent_uri=INTENT, ref=submission_ref)
    if (recorded.base, recorded.ref, recorded.intent_uri, recorded.binding_name, recorded.inputs_name,
        recorded.binding, recorded.inputs) != (authored, submission_ref, INTENT, binding_name, inputs_name,
                                              decision.closure.binding, decision.inputs.dag):
        raise ValueError("own Q response differs from authored decision")
    with d.Repository(path) as repo, repo.read() as tx:
        if tx.get_commit(recorded.commit).parents != (authored,):
            raise ValueError("actual submission parent differs from THIS authored decision")
        if (tx.get_ref(decision_ref), tx.get_ref(submission_ref), tx.get_ref("request-" + recorded.request_id),
            b.scalar(tx, tx.get_dag(recorded.request).root, "string")) != (authored, recorded.commit, recorded.commit, recorded.request_id):
            raise ValueError("actual ownQ/decision-ref/submission-ref/reservation differs")
    inspect_request(path, commit=recorded.commit, request=recorded.request, decision_name=decision_name)
    reused = None if decision.action != "reuse-selected" else publish_reuse(path, recorded, decision.selected.selected, reuse_ref)
    inspect_request(path, commit=recorded.commit, request=recorded.request, decision_name=decision_name,
                    satisfaction_commit=None if reused is None else reused.commit)
    return Request(decision, recorded, reused)
