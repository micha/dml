"""Explicit add/double composition, successful producer witnesses and ONE value selection.

Example-local public APIs only; no registry/evaluator or implicit dispatch. Native
argument/Q profiles are unchanged. Close all native handles before calling drivers.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile
import unicodedata

import daggerml as d
from daggerml import builtin as b, exchange as ex, local, transfer
import reuse_selection as selection

ADD = "urn:example:node-add"
DOUBLE = "urn:example:node-double"
COMPOSITION_ROLE = "example-node-composition-v1"
DECISION_ROLE = "example-composed-node-decision-v1"
W_ROLE = "example-explicit-reuse-v1"
SLOT = "selected-double"


def name(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None:
        raise ValueError("explicit name outside native profile")
    return value


def tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def contract(intent):
    if intent == ADD:
        return "add", ("a", "b")
    if intent == DOUBLE:
        return "double", ("x",)
    raise ValueError("only the two explicit add/double contracts are supported")


def capture(intent, map_binding, list_binding):
    func, _ = contract(intent)
    source = Path(__file__).with_name("composed_node_funcs.py").read_bytes()
    return ("import types\nfrom daggerml import builtin,local,ObjectId\n"
            "logical=types.ModuleType('composed_node_funcs')\n"
            "exec(compile(%r,'composed_node_funcs.py','exec'),logical.__dict__)\n"
            "builtin.publish_callable(local.child_context(),logical.%s,"
            "map_binding=ObjectId.from_hex(%r),list_binding=ObjectId.from_hex(%r))\n"
            % (source, func, str(map_binding), str(list_binding))).encode()


def inspect_binding(tx, dag, intent, entries):
    contract(intent)
    map_binding, list_binding = entries["map-get-v1"], entries["list-get-v1"]
    for oid, uri in ((map_binding, "dml://source/builtin/map/get/v1"),
                     (list_binding, "dml://source/builtin/list/get/v1")):
        if b.inspect_binding(tx, oid).source_uri != uri:
            raise ValueError("fixed builtin binding differs")
    fields = b.shape(tx, dag, ("role", "adapter", "source", "interpreter", "timeout-ms"),
                     "local-python-binding-v1")
    if (b.scalar(tx, fields["adapter"], "uri") != local.ADAPTER_URI
        or b.scalar(tx, fields["source"], "bytes") != capture(intent, map_binding, list_binding)):
        raise ValueError("captured callable binding differs")
    interpreter = b.scalar(tx, fields["interpreter"], "string")
    timeout = b.scalar(tx, fields["timeout-ms"], "i64")
    if (not os.path.isabs(interpreter) or "\0" in interpreter
        or unicodedata.normalize("NFC", interpreter) != interpreter or not 1 <= timeout <= 3600000):
        raise ValueError("callable interpreter/timeout differs")
    interpreter.encode("utf-8")


def inspect_arguments(tx, commit, inputs, intent):
    _, names = contract(intent)
    inspector = b.Inspector(tx, commit=commit)
    full = inspector.arguments(inputs)
    fields = b.shape(tx, inputs, ("role", "value", "entries"), b.ARGUMENTS_ROLE, "value")
    ledger = tx.get_dag(b.link(tx, fields["entries"]))
    sources = {}
    for n in sorted(set(ledger.bindings) - {"role"}):
        row = b.shape(tx, b.link(tx, ledger.bindings[n]), ("role", "key", "source"), b.ENTRY_ROLE)
        key = b.scalar(tx, row["key"], "string")
        sources[key] = inspector.node(b.link(tx, row["source"]))
    if set(sources) != set(names) or any(v.value.kind != "i64" for v in sources.values()):
        raise ValueError("exact named I64 argument contract differs")
    return full, sources


def initialize(path, interpreter):
    """Explicit fresh authoring only: no Q/T, primitive invocation or child."""
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        entries = {"map-get-v1": b.put_binding(tx, source_uri="dml://source/builtin/map/get/v1"),
                   "list-get-v1": b.put_binding(tx, source_uri="dml://source/builtin/list/get/v1")}
        for intent in (ADD, DOUBLE):
            func, _ = contract(intent)
            entries[func + "-binding"] = local.put_local_binding(
                tx, source=capture(intent, entries["map-get-v1"], entries["list-get-v1"]),
                interpreter=interpreter, timeout_ms=10000)
        commit = tx.put_commit(tx.put_tree(entries))
        tx.create_ref("main", commit)
    return commit


def prepare_add(path, *, commit, values, inputs_name, ref):
    """Bootstrap literal/map authoring, NOT computational builtin positions."""
    name(inputs_name)
    name(ref)
    items = list(values.items()) if hasattr(values, "items") else list(values)
    if len(items) != 2 or {key for key, value in items} != {"a", "b"}:
        raise ValueError("add needs exactly a,b")
    for key, value in items:
        d.Datum.i64(value)  # Exact type/range BEFORE write.
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


@dataclass(frozen=True)
class Producer:
    selected: selection.Selection
    inputs: b.Description
    returned: b.Description
    request_commit: d.ObjectId
    decision_name: str
    decision: object


def _prepare(path, commit, binding_name, inputs_name, intent, request=None):
    with tempfile.TemporaryDirectory(prefix="dml-composed-validation-") as scratch:
        return ex.prepare_exchange(path, commit=commit, binding_name=binding_name,
                                   inputs_name=inputs_name, intent_uri=intent, request=request,
                                   worker_ref="validation", workspace=Path(scratch) / "input")


def inspect_producer(path, *, commit, slot, intent, depth=0):
    """Public success plus structural value plus ORIGINAL producing decision/C chain."""
    if depth > 4:
        raise ValueError("producer decision chain exceeds fixed composition profile")
    selected = selection.inspect(path, commit=commit, slot=slot)
    if selected.intent_uri != intent:
        raise ValueError("selected producer intent differs")
    with d.Repository(path) as repo, repo.read() as tx:
        entries = tree(tx, commit)
        inspect_binding(tx, selected.binding, intent, entries)
        full, _ = inspect_arguments(tx, commit, selected.inputs, intent)
        returned = b.Inspector(tx, commit=commit).node(selected.result)
        fields = b.shape(tx, selected.result, ("role", "returned", "value", "trace", "request", "inputs"),
                         b.RETURN_ROLE, "value")
        if (returned.value.kind != "i64" or
            (b.link(tx, fields["request"]), b.link(tx, fields["inputs"])) != (selected.request, selected.inputs)):
            raise ValueError("selected explicit return owner/value differs")
        # Public S already validates F/P/Cq. Follow actual native parents, not description flags.
        pre = tx.get_commit(selected.completion).parents[0]
        cq = tx.get_commit(pre).parents[0]
        decision_commit = tx.get_commit(cq).parents[0]
        basis = tx.get_commit(decision_commit).parents
        if len(basis) != 1:
            raise ValueError("producing decision must have one parent")
        old, current = tree(tx, basis[0]), tree(tx, decision_commit)
        additions = set(current) - set(old)
        if len(additions) != 1:
            raise ValueError("producing decision must add exactly one name")
        decision_name = additions.pop()
    decision = inspect_request(path, commit=cq, request=selected.request,
                               decision_name=decision_name, depth=depth + 1)
    if (decision.intent != intent or decision.action != "execute-fresh"
        or decision.binding != selected.binding or decision.inputs != full):
        raise ValueError("producer must be ORIGINAL fresh declared request")
    return Producer(selected, full, returned, cq, decision_name, decision)


@dataclass(frozen=True)
class Composition:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    inputs_name: str
    inputs: b.Description
    producer: Producer


def compose_double(path, *, commit, producer_slot, inputs_name, composition_name, ref, map_size=0):
    for n in (producer_slot, inputs_name, composition_name, ref):
        name(n)
    if len({producer_slot, inputs_name, composition_name}) != 3:
        raise ValueError("composition names must differ")
    producer = inspect_producer(path, commit=commit, slot=producer_slot, intent=ADD)
    with d.Repository(path, map_size=map_size) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if inputs_name in entries or composition_name in entries:
            raise ValueError("inputs/composition names must both be absent")
        with b.Recorder(tx, commit=commit) as rec:
            result = rec.load(producer.selected.result)
            arguments = rec.arguments({"x": result})
            inputs = rec.dag(arguments)
            full = rec.inspector.arguments(inputs)
        dag = b.record(tx, COMPOSITION_ROLE, values={"key": "x", "selection-slot": producer_slot},
                       links={"arguments": inputs, "selection": producer.selected.dag,
                              "result": producer.selected.result})
        entries.update({inputs_name: inputs, composition_name: dag})
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = Composition(commit, authored, dag, composition_name, inputs_name, full, producer)
    return response


def inspect_composition(path, *, commit, inputs_name, composition_name, depth=0):
    for n in (inputs_name, composition_name):
        name(n)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("composition requires one actual parent")
        base = parents[0]
        old, entries = tree(tx, base), tree(tx, commit)
        if inputs_name == composition_name or inputs_name in old or composition_name in old:
            raise ValueError("composition adds two distinct absent names")
        inputs, dag = entries.pop(inputs_name), entries.pop(composition_name)
        if entries != old:
            raise ValueError("composition must add ONLY inputs/C")
        fields = b.shape(tx, dag, ("role", "arguments", "key", "selection-slot", "selection", "result"), COMPOSITION_ROLE)
        slot = b.scalar(tx, fields["selection-slot"], "string")
        name(slot)
        selected, result = b.link(tx, fields["selection"]), b.link(tx, fields["result"])
        if (b.scalar(tx, fields["key"], "string") != "x" or b.link(tx, fields["arguments"]) != inputs
            or old[slot] != selected):
            raise ValueError("composition actual-parent slot/arguments differ")
        full, sources = inspect_arguments(tx, commit, inputs, DOUBLE)
        if sources["x"].dag != result:
            raise ValueError("composition must use exact OUTER selected R source")
    producer = inspect_producer(path, commit=base, slot=slot, intent=ADD, depth=depth)
    if (selected, result, sources["x"].datum) != (producer.selected.dag, producer.selected.result, producer.returned.datum):
        raise ValueError("composition selected S/outerR/value differs")
    return Composition(base, commit, dag, composition_name, inputs_name, full, producer)


@dataclass(frozen=True)
class Decision:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    intent: str
    binding_name: str
    binding: d.ObjectId
    inputs_name: str
    inputs: b.Description
    composition: object
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


def _resolve(path, commit, intent, binding_name, inputs_name, composition_name, control, depth=0):
    contract(intent)
    for n in (binding_name, inputs_name):
        name(n)
    if control not in ("fresh", "try-selected", "require-selected"):
        raise ValueError("unsupported explicit control")
    if intent == ADD and (control != "fresh" or composition_name is not None):
        raise ValueError("add is explicitly fresh with no composition")
    if intent == DOUBLE and composition_name is None:
        raise ValueError("double requires actual composition witness")
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        entries = tree(tx, commit)
        binding = entries[binding_name]
        inspect_binding(tx, binding, intent, entries)
        full, sources = inspect_arguments(tx, commit, entries[inputs_name], intent)
        if intent == ADD:
            for source in sources.values():
                b.shape(tx, source.dag, ("role", "value"), b.LITERAL_ROLE, "value")
        present = SLOT in entries
    composition = None if intent == ADD else inspect_composition(
        path, commit=commit, inputs_name=inputs_name, composition_name=composition_name, depth=depth)
    spec = _prepare(path, commit, binding_name, inputs_name, intent)
    if (spec.binding, spec.inputs) != (binding, full.dag):
        raise ValueError("public preparation dimensions differ")
    selected = None
    if intent == DOUBLE and present:
        selected = inspect_producer(path, commit=commit, slot=SLOT, intent=DOUBLE, depth=depth)
    hit = selected is not None and selected.inputs.datum == full.datum
    if control == "fresh":
        action, reason = "execute-fresh", "explicit-fresh"
    elif hit:
        action, reason = "reuse-selected", "selected-value"
    elif control == "require-selected":
        raise ValueError("required selected value has no match")
    else:
        action, reason = "execute-fresh", "no-selection" if selected is None else "value-mismatch"
    return binding, full, composition, selected, action, reason


def _claims(intent, binding_name, inputs_name, composition_name, control, resolved):
    binding, full, composition, selected, action, reason = resolved
    values = {"intent": d.Datum.uri(intent), "binding-name": binding_name, "inputs-name": inputs_name,
              "control": control, "action": action, "reason": reason}
    links = {"binding": binding, "inputs": full.dag}
    if composition is not None:
        values["composition-name"] = composition_name
        links["composition"] = composition.dag
    if selected is not None:
        values["selection-slot"] = SLOT
        links["selection"] = selected.selected.dag
    return values, links


def _response(base, commit, dag, decision_name, intent, binding_name, inputs_name, control, resolved):
    binding, full, composition, selected, action, reason = resolved
    return Decision(base, commit, dag, decision_name, intent, binding_name, binding, inputs_name,
                    full, composition, control, action, reason, selected)


def inspect_decision(path, *, commit, decision_name, depth=0):
    name(decision_name)
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("decision requires one actual parent")
        base = parents[0]
        old, entries = tree(tx, base), tree(tx, commit)
        dag = entries.pop(decision_name)
        if decision_name in old or entries != old:
            raise ValueError("decision must add ONLY named D")
        fields = tx.get_dag(dag).bindings
        names = ["intent", "binding-name", "inputs-name", "control", "action", "reason"]
        names += [n for n in ("composition-name", "selection-slot") if n in fields]
        values = {n: b.scalar(tx, fields[n], "uri" if n == "intent" else "string") for n in names}
        links = {n: b.link(tx, fields[n]) for n in ("binding", "inputs")}
        links.update((n, b.link(tx, fields[n])) for n in ("composition", "selection") if n in fields)
        b.shape(tx, dag, ("role", "value", *names, *links), DECISION_ROLE, "inputs")
        datum, _ = b.node_value(tx, fields["value"])
    resolved = _resolve(path, base, values["intent"], values["binding-name"], values["inputs-name"],
                        values.get("composition-name"), values["control"], depth=depth)
    expected, expected_links = _claims(values["intent"], values["binding-name"], values["inputs-name"],
                                       values.get("composition-name"), values["control"], resolved)
    expected["intent"] = values["intent"]
    if values != expected or links != expected_links or datum != resolved[1].datum:
        raise ValueError("decision claims differ from actual basis")
    return _response(base, commit, dag, decision_name, values["intent"], values["binding-name"],
                     values["inputs-name"], values["control"], resolved)


def inspect_request(path, *, commit, request, decision_name, satisfaction_commit=None, depth=0):
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("submission requires one actual decision parent")
    decision = inspect_decision(path, commit=parents[0], decision_name=decision_name, depth=depth)
    spec = _prepare(path, commit, decision.binding_name, decision.inputs_name, decision.intent, request)
    if (spec.binding, spec.inputs) != (decision.binding, decision.inputs.dag):
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


def _publish_reuse(path, recorded, selected, ref):
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, recorded.commit)
        key = "reuse-" + recorded.request_id
        if key in entries:
            raise ValueError("satisfaction already present")
        dag = b.record(tx, W_ROLE, links={"request": recorded.request, "attempt": selected.attempt,
                                        "result": selected.result}, root="result")
        entries[key] = dag
        commit = tx.put_commit(tx.put_tree(entries), parents=(recorded.commit,))
        tx.create_ref(ref, commit)
        response = Satisfaction(commit, dag, selected.attempt, selected.result)
    return response


def record_request(path, *, commit, intent, binding_name, inputs_name, decision_name,
                   decision_ref, submission_ref, composition_name=None, control="fresh", reuse_ref=None):
    for n in (binding_name, inputs_name, decision_name, decision_ref, submission_ref):
        name(n)
    if composition_name is not None:
        name(composition_name)
    if reuse_ref is not None:
        name(reuse_ref)
    if (len({decision_ref, submission_ref, reuse_ref}) != 3
        or decision_name in (binding_name, inputs_name, composition_name, SLOT)
        or decision_name.startswith(("request-q-", "attempt-a-", "publication-a-", "reuse-q-"))):
        raise ValueError("publication names/refs must differ from existing dimensions/occurrences")
    resolved = _resolve(path, commit, intent, binding_name, inputs_name, composition_name, control)
    if (reuse_ref is not None) != (resolved[-2] == "reuse-selected"):
        raise ValueError("reuse ref required ONLY on selected hit")
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if decision_name in entries:
            raise ValueError("decision name must be absent")
        values, links = _claims(intent, binding_name, inputs_name, composition_name, control, resolved)
        dag = b.record(tx, DECISION_ROLE, values=values, links=links,
                       nodes={"value": tx.put_literal(resolved[1].datum)}, root="inputs")
        entries[decision_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(decision_ref, authored)
        decision = _response(commit, authored, dag, decision_name, intent, binding_name, inputs_name, control, resolved)
    recorded = ex.record_exchange_request(path, commit=authored, binding_name=binding_name,
                                           inputs_name=inputs_name, intent_uri=intent, ref=submission_ref)
    if (recorded.base, recorded.ref, recorded.intent_uri, recorded.binding_name, recorded.inputs_name,
        recorded.binding, recorded.inputs) != (authored, submission_ref, intent, binding_name, inputs_name,
                                              decision.binding, decision.inputs.dag):
        raise ValueError("own Q response differs from authored decision")
    with d.Repository(path) as repo, repo.read() as tx:
        if tx.get_commit(recorded.commit).parents != (authored,):
            raise ValueError("actual submission parent differs from THIS authored decision")
        if (tx.get_ref(decision_ref), tx.get_ref(submission_ref), tx.get_ref("request-" + recorded.request_id),
            b.scalar(tx, tx.get_dag(recorded.request).root, "string")) != (authored, recorded.commit, recorded.commit, recorded.request_id):
            raise ValueError("actual ownQ/decision-ref/submission-ref/reservation differs")
    inspect_request(path, commit=recorded.commit, request=recorded.request, decision_name=decision_name)
    reused = None if decision.action != "reuse-selected" else _publish_reuse(
        path, recorded, decision.selected.selected, reuse_ref)
    inspect_request(path, commit=recorded.commit, request=recorded.request, decision_name=decision_name,
                    satisfaction_commit=None if reused is None else reused.commit)
    return Request(decision, recorded, reused)
