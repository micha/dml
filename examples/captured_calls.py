"""NEW bounded ordinary outer-call profiles; public storage/leaf APIs, no native changes.

The in-process adapter is NOT a local-python Q/T/F producer. All completion/selection
inspection is nonexecuting. Separate short writes retain exact native source/history.
"""

from dataclasses import dataclass
from pathlib import Path
import re
import tempfile
import uuid

import daggerml as d
from daggerml import builtin as b, exchange as ex, local, transfer
import captured_call_leaf as leaf
import reuse_selection as selection

INTENT = "urn:example:captured-double-sum"
ADAPTER = "urn:example:in-process-double-sum-v1"
PREFIX = "example-outer-"
B_ROLE, E_ROLE, C_ROLE = (PREFIX + n + "-v1" for n in ("binding", "environment", "closure"))
D_ROLE, PLAN_ROLE, Q_ROLE, T_ROLE = (PREFIX + n + "-v1" for n in ("decision", "plan", "request", "attempt"))
PHASE_ROLE, CALL_ROLE, LEAF_D_ROLE = (PREFIX + n + "-v1" for n in ("phase", "call", "leaf-decision"))
RETURN_ROLE, LEDGER_ROLE, S_ROLE, W_ROLE = (PREFIX + n + "-v1" for n in ("return", "calls", "selection", "reuse"))
SUCCESS_ROLE, FAILURE_ROLE, ERROR_ROLE = (PREFIX + n + "-v1" for n in ("success", "leaf-failure", "session-failure"))
SLOT, DOUBLE_SLOT = "selected-double-sum", "selected-inner-double"
CONTROLS = ("fresh", "try-selected", "require-selected")
# Increment ONLY when crossing a selected ORIGINAL outer/leaf producer authority.
# Its own request/spine/prerequisite functions preserve depth; helper frames add nothing.
MAX_AUTHORITY_DEPTH = 8


def authority_depth(depth):
    if type(depth) is not int or not 0 <= depth <= MAX_AUTHORITY_DEPTH:
        raise ValueError("ORIGINAL authority chain too deep or invalid depth")


def name(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None:
        raise ValueError("explicit name outside native profile")
    return value


def tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def oid(tx, node):
    return d.ObjectId(b.scalar(tx, node, "bytes"))


def occurrence(tx, dag, role, prefix, names):
    got = tx.get_dag(dag)
    if set(got.bindings) != set(names) | {"role"} or b.scalar(tx, got.bindings["role"], "string") != role:
        raise ValueError("occurrence fields/role differ")
    value = b.scalar(tx, got.root, "string")
    if re.fullmatch(prefix + r"[0-9a-f]{32}", value) is None:
        raise ValueError("occurrence root differs")
    return got.bindings, value


def event(tx, role, identifier, *, values=(), links=()):
    fields = {"role": b.literal(tx, role)}
    fields.update((n, b.literal(tx, v)) for n, v in dict(values).items())
    fields.update((n, tx.put_subdag(v)) for n, v in dict(links).items())
    return tx.put_dag(root=b.literal(tx, identifier), bindings=fields)


def outer_sources():
    here = Path(__file__).parent
    return tuple(here.joinpath(n).read_bytes() for n in
                 ("captured_call_funcs.py", "captured_call_session.py", "captured_call_adapter.py", "captured_calls.py"))


def binding_source(env):
    # Exact captured code data, no source contains future B/K/C/F identifiers.
    return repr((str(env), outer_sources())).encode("utf-8")


def budget(seen):
    if len(seen) > b.MAX_RECORDS:
        raise ValueError("aggregate ORIGINAL/requested semantic union exceeds64")


def arguments(tx, commit, dag, names, seen):
    inspector = b.Inspector(tx, commit=commit)
    full = inspector.arguments(dag)
    fields = b.shape(tx, dag, ("role", "value", "entries"), b.ARGUMENTS_ROLE, "value")
    rows = tx.get_dag(b.link(tx, fields["entries"]))
    sources = {}
    for key in sorted(set(rows.bindings) - {"role"}):
        row = b.shape(tx, b.link(tx, rows.bindings[key]), ("role", "key", "source"), b.ENTRY_ROLE)
        sources[b.scalar(tx, row["key"], "string")] = inspector.node(b.link(tx, row["source"]))
    if set(sources) != set(names) or any(v.value.kind != "i64" for v in sources.values()):
        raise ValueError("exact I64 argument contract differs")
    seen.update(inspector.seen)
    budget(seen)
    return full, sources


def inspect_closure(tx, commit, dag):
    retained = b.Inspector(tx, commit=commit).retained
    fields = b.shape(tx, dag, ("role", "intent", "binding", "environment", "key"), C_ROLE)
    if dag not in retained or b.scalar(tx, fields["intent"], "uri") != INTENT:
        raise ValueError("outer captured intent/retention differs")
    binding, env, key = (b.link(tx, fields[n]) for n in ("binding", "environment", "key"))
    ef = b.shape(tx, env, ("role", "add", "double", "map-get"), E_ROLE)
    add, double = (leaf.inspect(tx, b.link(tx, ef[n]), *leaf.sources()) for n in ("add", "double"))
    map_binding = b.link(tx, ef["map-get"])
    if (add["intent"], double["intent"], b.inspect_binding(tx, map_binding).source_uri) != (
        leaf.ADD, leaf.DOUBLE, "dml://source/builtin/map/get/v1"):
        raise ValueError("fixed outer captures differ")
    normal = b.shape(tx, binding, ("role", "adapter", "source", "interpreter", "timeout-ms", "environment"), B_ROLE)
    keys = b.shape(tx, key, ("role", "binding", "environment"), leaf.K_ROLE)
    if (b.scalar(tx, normal["adapter"], "uri") != ADAPTER
        or b.scalar(tx, normal["source"], "bytes") != binding_source(env)
        or b.link(tx, normal["environment"]) != env
        or tuple(b.link(tx, keys[n]) for n in ("binding", "environment")) != (binding, env)):
        raise ValueError("outer exact captured binding/identity differs")
    for n in ("interpreter", "timeout-ms"):
        b.scalar(tx, normal[n], "null")
    # Complete typed retention includes source bytes and ALL linked captures, not embedded IDs alone.
    if not {binding, env, key, add["dag"], double["dag"], map_binding} <= retained:
        raise ValueError("captured dependency not retained")  # pragma: no cover
    return dict(dag=dag, binding=binding, environment=env, key=key, add=add, double=double, map_binding=map_binding)


def initialize(path, interpreter):
    """Metadata ONLY: four captured leaf choices and immutable old outer closure."""
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        entries = {"map-v1": b.put_binding(tx, source_uri="dml://source/builtin/map/get/v1"),
                   "map-v2": b.put_binding(tx, source_uri="dml://source/builtin/map/get/v2"),
                   "list-v1": b.put_binding(tx, source_uri="dml://source/builtin/list/get/v1")}
        for label, getter in (("A", "map-v1"), ("B", "map-v2")):
            for intent in (leaf.ADD, leaf.DOUBLE):
                func, _ = leaf.contract(intent)
                env = b.record(tx, leaf.E_ROLE, links={"map-get": entries[getter], "list-get": entries["list-v1"]})
                binding = local.put_local_binding(tx, source=leaf.capture(env, intent, *leaf.sources()),
                                                  interpreter=interpreter, timeout_ms=10000)
                key = b.record(tx, leaf.K_ROLE, links={"binding": binding, "environment": env})
                closure = b.record(tx, leaf.C_ROLE, values={"intent": d.Datum.uri(intent)},
                                   links={"binding": binding, "environment": env, "key": key})
                entries[func + "-" + label] = closure
        env = b.record(tx, E_ROLE, links={"add": entries["add-A"], "double": entries["double-A"], "map-get": entries["map-v1"]})
        binding = b.record(tx, B_ROLE, values={"adapter": d.Datum.uri(ADAPTER), "source": binding_source(env),
            "interpreter": None, "timeout-ms": None}, links={"environment": env})
        key = b.record(tx, leaf.K_ROLE, links={"binding": binding, "environment": env})
        entries["outer"] = b.record(tx, C_ROLE, values={"intent": d.Datum.uri(INTENT)},
            links={"binding": binding, "environment": env, "key": key})
        entries.update({"default-add": entries["add-A"], "default-double": entries["double-A"]})
        commit = tx.put_commit(tx.put_tree(entries))
        tx.create_ref("main", commit)
    return commit


def prepare_arguments(path, *, commit, values, inputs_name, ref):
    name(inputs_name)
    name(ref)
    if set(values) != {"a", "b"} or len(values) != 2:
        raise ValueError("outer input requires exact a,b")
    for value in values.values():
        d.Datum.i64(value)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if inputs_name in entries:
            raise ValueError("input name already exists")
        with b.Recorder(tx, commit=commit) as rec:
            full = rec.arguments({n: rec.literal(d.Datum.i64(v)) for n, v in values.items()})
            entries[inputs_name] = rec.dag(full)
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
    return authored


def promote_defaults(path, *, commit, ref):
    name(ref)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        for func in ("add", "double"):
            leaf.inspect(tx, entries[func + "-B"], *leaf.sources())
            entries["default-" + func] = entries[func + "-B"]
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
    return authored


def single_delta(tx, commit, added, replaced=()):
    parents = tx.get_commit(commit).parents
    if len(parents) != 1:
        raise ValueError("single-parent metadata delta differs")
    old, current = tree(tx, parents[0]), tree(tx, commit)
    if set(current) != set(old) | set(added) or set(added) & set(old):
        raise ValueError("absent-name metadata delta differs")
    if any(current[n] != v for n, v in old.items() if n not in replaced):
        raise ValueError("unrelated tree entry changed")
    return parents[0]


def public_prepare(path, commit, binding_name, inputs_name, intent, request=None):
    with tempfile.TemporaryDirectory(prefix="dml-captured-call-validation-") as root:
        return ex.prepare_exchange(path, commit=commit, binding_name=binding_name, inputs_name=inputs_name,
            intent_uri=intent, request=request, worker_ref="validation", workspace=Path(root) / "input")


def validate_recorded(path, recorded, base, binding_name, inputs_name, target, inputs, ref):
    """Validate THIS authored preparation and operational native reservations BEFORE dispatch."""
    spec = public_prepare(path, recorded.commit, binding_name, inputs_name, target["intent"], recorded.request)
    with d.Repository(path) as repo, repo.read() as tx:
        q = tx.get_dag(recorded.request)
        qid = b.scalar(tx, q.root, "string")
        if (tx.get_commit(recorded.commit).parents != (base,)
            or (tx.get_ref(ref), tx.get_ref("request-" + qid)) != (recorded.commit, recorded.commit)
            or (spec.binding, spec.inputs) != (target["binding"], inputs)
            or (recorded.base, recorded.ref, recorded.request_id, recorded.binding_name, recorded.inputs_name,
                recorded.binding, recorded.inputs, recorded.intent_uri) !=
               (base, ref, qid, binding_name, inputs_name, target["binding"], inputs, target["intent"])):
            raise ValueError("actual leaf submission THIS preparation/ref/reservation/dimensions differs")
    return spec


def inspect_leaf_success(path, *, commit, slot, seen=None, depth=0):
    """Public S plus ORIGINAL captured decision, exact trace and upstream producer."""
    authority_depth(depth)
    seen = set() if seen is None else seen
    selected = selection.inspect(path, commit=commit, slot=slot)
    with d.Repository(path) as repo, repo.read() as tx:
        pre = tx.get_commit(selected.completion).parents[0]
        cq = tx.get_commit(pre).parents[0]
        dc = tx.get_commit(cq).parents[0]
        entries = tree(tx, dc)
        q = tx.get_dag(selected.request)
        old = tree(tx, tx.get_commit(dc).parents[0])
        # The decision was authored with leaf dimensions and an owning preparation phase.
        decisions = [(n, v) for n, v in entries.items() if n not in old and
                     "role" in tx.get_dag(v).bindings and
                     b.scalar(tx, tx.get_dag(v).bindings["role"], "string") == LEAF_D_ROLE]
        if len(decisions) != 1:
            raise ValueError("ORIGINAL leaf decision absent/ambiguous")
        decision_name, decision = decisions[0]
        fields = tx.get_dag(decision).bindings
        optional = ("upstream-slot", "upstream") if selected.intent_uri == leaf.DOUBLE else ()
        b.shape(tx, decision, ("role", "outer-request", "outer-attempt", "slot", "closure", "binding", "environment", "key", "inputs", "control",
                               "binding-name", "inputs-name", "basis", *optional), LEAF_D_ROLE)
        target = leaf.inspect(tx, b.link(tx, fields["closure"]), *leaf.sources())
        if tuple(b.link(tx, fields[n]) for n in ("binding", "environment", "key")) != tuple(target[n] for n in ("binding", "environment", "key")):
            raise ValueError("ORIGINAL exact leaf B/E/key differs")
        if oid(tx, fields["basis"]) != tx.get_commit(dc).parents[0]:
            raise ValueError("ORIGINAL leaf decision basis differs")
        if (target["binding"], target["intent"], b.link(tx, fields["inputs"]), b.scalar(tx, fields["control"], "string")) != (
            selected.binding, selected.intent_uri, selected.inputs, "fresh"):
            raise ValueError("ORIGINAL leaf capture/input/fresh association differs")
        owner = b.link(tx, fields["outer-request"])
        initial = b.link(tx, fields["outer-attempt"])
        qfields, _ = occurrence(tx, owner, Q_ROLE, "cq-", ("intent", "binding", "inputs", "closure", "decision"))
        tfields, owner_aid = occurrence(tx, initial, T_ROLE, "ca-", ("request", "plan"))
        outer = inspect_closure(tx, dc, b.link(tx, qfields["closure"]))
        slot_number = 0 if selected.intent_uri == leaf.ADD else 1
        if (b.link(tx, tfields["request"]) != owner or b.scalar(tx, fields["slot"], "i64") != slot_number
            or target != outer["add" if slot_number == 0 else "double"]):
            raise ValueError("ORIGINAL captured target/outer T/slot differs")
        full, sources = arguments(tx, commit, selected.inputs, leaf.contract(selected.intent_uri)[1], seen)
        if slot_number == 0 and selected.inputs != b.link(tx, qfields["inputs"]):
            raise ValueError("add Q must consume ORIGINAL exact outer input DAG")
        inspector = b.Inspector(tx, commit=commit)
        result = inspector.node(selected.result)
        returned = b.shape(tx, selected.result, ("role", "returned", "value", "trace", "request", "inputs"), b.RETURN_ROLE, "value")
        if (b.link(tx, returned["request"]), b.link(tx, returned["inputs"]), result.value.kind) != (
            selected.request, selected.inputs, "i64"):
            raise ValueError("ORIGINAL returned owner/value differs")
        b.shape(tx, b.link(tx, returned["returned"]), ("role", "value"), b.LITERAL_ROLE, "value")
        trace = inspector.trace(b.link(tx, returned["trace"]), request=selected.request, inputs=selected.inputs)
        expected_keys = leaf.contract(selected.intent_uri)[1]
        if len(trace) != len(expected_keys):
            raise ValueError("ORIGINAL getter positions differ")
        for got, key in zip(trace, expected_keys):
            inspect_getter(tx, commit, got.dag, selected.inputs, key, target["map_binding"], seen)
        seen.update(inspector.seen)
        seen.add(target["list_binding"])
        basis = oid(tx, fields["basis"])
        # The actual preparation snapshot adds ONLY strict phase+decision+dimension payloads.
        phases = [(n, v) for n, v in entries.items() if n not in old and
                  "role" in tx.get_dag(v).bindings and
                  b.scalar(tx, tx.get_dag(v).bindings["role"], "string") == PHASE_ROLE]
        if len(phases) != 1:
            raise ValueError("ORIGINAL leaf preparation phase absent/ambiguous")
        phase_name_actual, phase_dag = phases[0]
        phase = b.shape(tx, phase_dag, ("role", "request", "initial-attempt", "kind", "index", "previous",
            "slot", "decision", "binding", "inputs"), PHASE_ROLE)
        phase_index = b.scalar(tx, phase["index"], "i64")
        payloads = payload_names(owner_aid, phase_index, "leaf-prepare")
        if (phase_name_actual != phase_name(owner_aid, phase_index) or b.scalar(tx, phase["kind"], "string") != "leaf-prepare"
            or oid(tx, phase["previous"]) != basis or b.scalar(tx, phase["slot"], "i64") != slot_number
            or tuple(b.link(tx, phase[n]) for n in ("request", "initial-attempt", "decision", "binding", "inputs")) !=
                (owner, initial, decision, target["binding"], selected.inputs)
            or set(entries) - set(old) != set(payloads.values()) | {phase_name_actual}
            or any(entries[n] != v for n, v in old.items())
            or any(entries[payloads[n]] != b.link(tx, phase[n]) for n in ("decision", "binding", "inputs"))):
            raise ValueError("ORIGINAL leaf preparation exact native association/delta differs")
        upstream_slot = b.scalar(tx, fields["upstream-slot"], "string") if optional else None
        upstream_dag = b.link(tx, fields["upstream"]) if optional else None
        bn, inn = (b.scalar(tx, fields[n], "string") for n in ("binding-name", "inputs-name"))
        if (bn, inn, decision_name) != (payloads["binding"], payloads["inputs"], payloads["decision"]):
            raise ValueError("ORIGINAL leaf preparation named dimensions differ")
    prefix = inspect_spine(path, basis, owner, initial, owner_aid, seen, depth=depth)
    if (len(prefix["getters"]) != 2 or len(prefix["calls"]) != slot_number
        or prefix["failed"] is not None or prefix["returned"] is not None
        or (slot_number == 1 and prefix["double_inputs"] != selected.inputs)):
        raise ValueError("ORIGINAL leaf requires exact outer getter/call/input prefix")
    if slot_number == 1:
        with d.Repository(path) as repo, repo.read() as tx:
            first = tx.get_dag(prefix["calls"][0]).bindings
            if (b.link(tx, first["selection"]), b.scalar(tx, first["selection-slot"], "string")) != (upstream_dag, upstream_slot):
                raise ValueError("ORIGINAL double THIS actual prior add association differs")
    spec = public_prepare(path, cq, bn, inn, selected.intent_uri, selected.request)
    if (spec.binding, spec.inputs) != (target["binding"], full.dag):
        raise ValueError("actual public leaf submission differs")
    if upstream_slot is not None:
        upstream, _ = inspect_leaf_success(path, commit=basis, slot=upstream_slot, seen=seen, depth=depth + 1)
        if (upstream.dag, upstream.result) != (upstream_dag, sources["x"].dag) or upstream.intent_uri != leaf.ADD:
            raise ValueError("ORIGINAL requested source/producer differs")
    budget(seen)
    return selected, result


def inspect_getter(tx, commit, dag, inputs, key, binding, seen):
    inspector = b.Inspector(tx, commit=commit)
    got = inspector.node(dag)
    fields = b.shape(tx, dag, ("role", "func", "binding", "arguments", "value"), b.OPERATION_ROLE, "value")
    args = tx.get_dag(b.link(tx, fields["arguments"]))
    rows = tx.get_dag(b.link(tx, args.bindings["entries"]))
    sources = {}
    for n in ("arg-00", "arg-01"):
        row = b.shape(tx, b.link(tx, rows.bindings[n]), ("role", "key", "source"), b.ENTRY_ROLE)
        sources[b.scalar(tx, row["key"], "string")] = b.link(tx, row["source"])
    if (b.scalar(tx, fields["func"], "uri"), b.link(tx, fields["binding"]), sources.get("map")) != (b.MAP_GET, binding, inputs):
        raise ValueError("getter exact source/binding differs")
    if inspector.node(sources["key"]).value != d.Datum.string(key) or got.value.kind != "i64":
        raise ValueError("getter order/I64 contract differs")
    seen.update(inspector.seen)
    budget(seen)
    return got


@dataclass(frozen=True)
class Request:
    base: d.ObjectId
    decision_commit: d.ObjectId
    commit: d.ObjectId
    request: d.ObjectId
    request_id: str
    closure: dict
    inputs: b.Description
    plan: d.ObjectId
    action: str
    selected: object
    reused: object = None


def resolve(path, commit, closure_name, inputs_name, control, double_control, seen, depth=0):
    authority_depth(depth)
    if control not in CONTROLS or double_control not in CONTROLS:
        raise ValueError("unsupported explicit reuse control")
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        entries = tree(tx, commit)
        closure = inspect_closure(tx, commit, entries[name(closure_name)])
        full, _ = arguments(tx, commit, entries[name(inputs_name)], ("a", "b"), seen)
        outer_present, double_present = SLOT in entries, DOUBLE_SLOT in entries
    # Every present selection validated even for explicit fresh or computational mismatch.
    selected = inspect_selection(path, commit=commit, slot=SLOT, seen=seen, depth=depth + 1) if outer_present else None
    inner = inspect_leaf_success(path, commit=commit, slot=DOUBLE_SLOT, seen=seen, depth=depth + 1)[0] if double_present else None
    hit = selected is not None and (selected["closure"]["key"], selected["inputs_datum"]) == (closure["key"], full.datum)
    action = "execute-fresh" if control == "fresh" or not hit else "reuse-selected"
    if control == "require-selected" and not hit:
        raise ValueError("required outer selection does not match")
    return closure, full, selected, inner, action


def record_request(path, *, commit, closure_name="outer", inputs_name="inputs", control="fresh", double_control="fresh", ref):
    name(ref)
    seen = set()
    closure, full, selected, inner, action = resolve(path, commit, closure_name, inputs_name, control, double_control, seen)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        plan_links = {} if inner is None else {"double-selection": inner.dag}
        plan = b.record(tx, PLAN_ROLE, values={"basis": commit.bytes, "add-control": "fresh", "double-control": double_control}, links=plan_links)
        links = {"closure": closure["dag"], "binding": closure["binding"], "environment": closure["environment"],
                 "key": closure["key"], "inputs": full.dag, "plan": plan}
        if selected is not None:
            links["selection"] = selected["dag"]
        qid = "cq-" + uuid.uuid4().hex
        decision = b.record(tx, D_ROLE, values={"intent": d.Datum.uri(INTENT), "closure-name": closure_name,
            "inputs-name": inputs_name, "control": control, "action": action}, links=links,
            nodes={"value": tx.put_literal(full.datum)}, root="inputs")
        dn = "decision-" + qid
        if dn in entries:
            raise ValueError("outer occurrence collision")
        entries[dn] = decision
        dc = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref + "-decision", dc)
        q = event(tx, Q_ROLE, qid, values={"intent": d.Datum.uri(INTENT)},
            links={"binding": closure["binding"], "inputs": full.dag, "closure": closure["dag"], "decision": decision})
        entries["outer-request-" + qid] = q
        cq = tx.put_commit(tx.put_tree(entries), parents=(dc,))
        tx.create_ref(ref, cq)
        tx.create_ref("outer-request-" + qid, cq)
        response = Request(commit, dc, cq, q, qid, closure, full, plan, action, selected)
    with d.Repository(path) as repo, repo.read() as tx:
        if (tx.get_ref(ref), tx.get_ref(ref + "-decision"), tx.get_ref("outer-request-" + qid)) != (cq, dc, cq):
            raise ValueError("actual outer Q/decision/reservation refs differ")
    inspect_request(path, commit=cq, request=q, seen=seen)
    if action == "reuse-selected":
        with d.Repository(path) as repo, repo.write() as tx:
            entries = tree(tx, cq)
            fields = {"request": q, "decision": decision, "selection": selected["dag"],
                      "attempt": selected["attempt"], "result": selected["result"]}
            entries["outer-reuse-" + qid] = b.record(tx, W_ROLE, links=fields, root="result")
            reused = tx.put_commit(tx.put_tree(entries), parents=(cq,))
            tx.create_ref(ref + "-reuse", reused)
        inspect_reuse(path, commit=reused, seen=seen)
        response = Request(commit, dc, cq, q, qid, closure, full, plan, action, selected, reused)
    return response


def inspect_request(path, *, commit, request, seen=None, depth=0):
    authority_depth(depth)
    seen = set() if seen is None else seen
    with d.Repository(path) as repo, repo.read() as tx:
        q, qid = occurrence(tx, request, Q_ROLE, "cq-", ("intent", "binding", "inputs", "closure", "decision"))
        dc = single_delta(tx, commit, ("outer-request-" + qid,))
        if tree(tx, commit)["outer-request-" + qid] != request:
            raise ValueError("own Q native tree differs")
        base = single_delta(tx, dc, ("decision-" + qid,))
        decision = b.link(tx, q["decision"])
        if tree(tx, dc)["decision-" + qid] != decision:
            raise ValueError("own Q THIS decision differs")
        fields = tx.get_dag(decision).bindings
        optional = ("selection",) if SLOT in tree(tx, base) else ()
        b.shape(tx, decision, ("role", "intent", "closure-name", "inputs-name", "control", "action", "closure", "binding",
            "environment", "key", "inputs", "plan", "value", *optional), D_ROLE, "inputs")
        cn, inn, control, action = (b.scalar(tx, fields[n], "string") for n in ("closure-name", "inputs-name", "control", "action"))
        plan = b.link(tx, fields["plan"])
        pf = tx.get_dag(plan).bindings
        po = ("double-selection",) if DOUBLE_SLOT in tree(tx, base) else ()
        b.shape(tx, plan, ("role", "basis", "add-control", "double-control", *po), PLAN_ROLE)
        dc_control = b.scalar(tx, pf["double-control"], "string")
        if oid(tx, pf["basis"]) != base or b.scalar(tx, pf["add-control"], "string") != "fresh":
            raise ValueError("pinned call control basis differs")
        claimed = {n: b.link(tx, fields[n]) for n in ("closure", "binding", "environment", "key", "inputs")}
        if (b.scalar(tx, q["intent"], "uri") != INTENT or b.scalar(tx, fields["intent"], "uri") != INTENT
            or tuple(b.link(tx, q[n]) for n in ("binding", "inputs", "closure")) != tuple(claimed[n] for n in ("binding", "inputs", "closure"))):
            raise ValueError("outer Q/D computational association differs")
        value = b.node_value(tx, fields["value"])[0]
        selected_id = b.link(tx, fields["selection"]) if optional else None
        inner_id = b.link(tx, pf["double-selection"]) if po else None
    closure, full, selected, inner, actual = resolve(path, base, cn, inn, control, dc_control, seen, depth)
    if (claimed != {"closure": closure["dag"], "binding": closure["binding"], "environment": closure["environment"],
        "key": closure["key"], "inputs": full.dag} or value != full.datum or action != actual
        or selected_id != (None if selected is None else selected["dag"])
        or inner_id != (None if inner is None else inner.dag)):
        raise ValueError("outer decision claims differ from actual pinned basis")
    return Request(base, dc, commit, request, qid, closure, full, plan, action, selected)


def inspect_reuse(path, *, commit, seen=None):
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("outer W requires one Q parent")
        cq = parents[0]
        added = set(tree(tx, commit)) - set(tree(tx, cq))
        if len(added) != 1:
            raise ValueError("outer W must add ONLY satisfaction")
        wn = added.pop()
        single_delta(tx, commit, (wn,))
        fields = b.shape(tx, tree(tx, commit)[wn], ("role", "request", "decision", "selection", "attempt", "result"), W_ROLE, "result")
        links = {n: b.link(tx, fields[n]) for n in ("request", "decision", "selection", "attempt", "result")}
    q = inspect_request(path, commit=cq, request=links["request"], seen=seen)
    with d.Repository(path) as repo, repo.read() as tx:
        decision = b.link(tx, tx.get_dag(q.request).bindings["decision"])
    if (q.action != "reuse-selected" or wn != "outer-reuse-" + q.request_id
        or links != {"request": q.request, "decision": decision, "selection": q.selected["dag"],
                     "attempt": q.selected["attempt"], "result": q.selected["result"]}):
        raise ValueError("outer W ownQ/THIS D/OLD attempt/result differs")
    return q


def select_outer(path, *, commit, completion, slot=SLOT, ref):
    name(slot)
    name(ref)
    got = inspect_completion(path, commit=completion)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if slot in entries or completion not in history(tx, commit):
            raise ValueError("outer selection requires absent slot/retained completion")
        if got["outcome"] != "success":
            raise ValueError("outer selection requires success")
        links = {"closure": got["closure"]["dag"], "request": got["request"], "attempt": got["attempt"], "result": got["result"]}
        dag = b.record(tx, S_ROLE, values={"completion": completion.bytes}, links=links, root="result")
        entries[slot] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
    return authored


def history(tx, commit):
    pending, seen = [commit], set()
    while pending:
        current = pending.pop()
        if current not in seen:
            seen.add(current)
            pending.extend(tx.get_commit(current).parents)
            if len(seen) > transfer.MAX_OBJECTS:
                raise ValueError("history exceeds transfer profile")
    return seen


def inspect_selection(path, *, commit, slot=SLOT, seen=None, depth=0):
    authority_depth(depth)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        dag = tree(tx, commit)[name(slot)]
        fields = b.shape(tx, dag, ("role", "completion", "closure", "request", "attempt", "result"), S_ROLE, "result")
        completion = oid(tx, fields["completion"])
        links = {n: b.link(tx, fields[n]) for n in ("closure", "request", "attempt", "result")}
        if completion not in history(tx, commit):
            raise ValueError("outer F not retained by ALL-parent history")
    got = inspect_completion(path, commit=completion, seen=seen, depth=depth)
    if got["outcome"] != "success" or links != {"closure": got["closure"]["dag"], "request": got["request"],
                                                    "attempt": got["attempt"], "result": got["result"]}:
        raise ValueError("outer selection ORIGINAL completion differs")
    return dict(got, dag=dag, completion=completion)


# Fixed phase payloads: fields/root and exact additions are recomputed, not user-supplied delta claims.
PHASE_LINKS = {"get-a": ("node",), "get-b": ("node",), "double-input": ("inputs",),
               "leaf-prepare": ("decision", "binding", "inputs"), "leaf-pending": ("call",),
               "leaf-join": (), "leaf-reused": ("reuse",), "leaf-selected": ("selection",), "leaf-done": ("call",),
               "returned": ("return",)}
PHASE_VALUES = {"get-a": (), "get-b": (), "double-input": (), "leaf-prepare": ("slot",),
                "leaf-pending": ("submission",), "leaf-join": ("completion",),
                "leaf-reused": ("reuse-commit",), "leaf-selected": ("selection-commit", "selection-slot"), "leaf-done": (), "returned": ()}


def phase_name(aid, index):
    return "phase-" + aid + "-%02d" % index


def payload_names(aid, index, kind):
    return {key: "payload-" + aid + "-%02d-" % index + key for key in PHASE_LINKS[kind]}


def inspect_completion(path, *, commit, seen=None, depth=0):
    """Strict NEW authority over native phases; never executes logical arithmetic."""
    authority_depth(depth)
    seen = set() if seen is None else seen
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("outer completion requires one previous phase")
        before = parents[0]
        old, final = tree(tx, before), tree(tx, commit)
        additions = set(final) - set(old)
        if len(additions) != 1:
            raise ValueError("terminal delta must add ONLY completion")
        completion_name = additions.pop()
        completion = final[completion_name]
        role = b.scalar(tx, tx.get_dag(completion).bindings["role"], "string")
        extras = ("return",) if role == SUCCESS_ROLE else ("failed-call",) if role == FAILURE_ROLE else ("reason", "detail") if role == ERROR_ROLE else None
        if extras is None:
            raise ValueError("unsupported outer outcome role")
        fields = b.shape(tx, completion, ("role", "request", "initial-attempt", "plan", "calls", *extras), role)
        request, initial, plan, calls_id = (b.link(tx, fields[n]) for n in ("request", "initial-attempt", "plan", "calls"))
        tf, aid = occurrence(tx, initial, T_ROLE, "ca-", ("request", "plan"))
        attempt_name = "outer-attempt-" + aid
        if old[attempt_name] != initial or b.link(tx, tf["request"]) != request or b.link(tx, tf["plan"]) != plan:
            raise ValueError("completion owning immutable initial T differs")
        final_attempt = final[attempt_name]
        ff, final_aid = occurrence(tx, final_attempt, T_ROLE, "ca-", ("request", "plan", "initial-attempt", "status", "completion"))
        if (final_aid != aid or any(ff[n] != tf[n] for n in ("role", "request", "plan"))
            or b.link(tx, ff["initial-attempt"]) != initial or b.scalar(tx, ff["status"], "string") != "done"
            or b.link(tx, ff["completion"]) != completion or completion_name != "outer-completion-" + aid):
            raise ValueError("same-occurrence final T/initial/completion differs")
        expected_tree = dict(old)
        expected_tree[attempt_name] = final_attempt
        expected_tree[completion_name] = completion
        if final != expected_tree:
            raise ValueError("completion changed unrelated tree state")
        ledger = tx.get_dag(calls_id)
        call_names = tuple("slot-%02d" % i for i in range(len(ledger.bindings) - 1))
        b.shape(tx, calls_id, ("role", *call_names), LEDGER_ROLE)
        if len(call_names) > 2 or (role == SUCCESS_ROLE and len(call_names) != 2):
            raise ValueError("terminal ordered call positions differ")
        call_ids = tuple(b.link(tx, ledger.bindings[n]) for n in call_names)
        returned_id = b.link(tx, fields["return"]) if role == SUCCESS_ROLE else None
        failed_id = b.link(tx, fields["failed-call"]) if role == FAILURE_ROLE else None
        if role == ERROR_ROLE:
            if (b.scalar(tx, fields["reason"], "string") != "session-error"
                or len(b.scalar(tx, fields["detail"], "string").encode("utf-8")) > 4096):
                raise ValueError("session failure detail differs")
    spine = inspect_spine(path, before, request, initial, aid, seen, depth=depth)
    q = inspect_request(path, commit=spine["submission"], request=request, seen=seen, depth=depth)
    if q.action != "execute-fresh" or q.plan != plan:
        raise ValueError("fresh completion decision/plan differs")
    if tuple(spine["calls"]) != call_ids or failed_id != spine["failed"]:
        raise ValueError("terminal actual call associations differ")
    result, datum = None, None
    if returned_id is not None:
        if spine["returned"] != returned_id or spine["failed"] is not None or len(spine["getters"]) != 2:
            raise ValueError("premature/fake outer return")
        with d.Repository(path) as repo, repo.read() as tx:
            rf = b.shape(tx, returned_id, ("role", "request", "initial-attempt", "inputs", "returned", "value", "call0", "call1", "getter0", "getter1"), RETURN_ROLE, "value")
            last = tx.get_dag(call_ids[-1]).bindings
            result = b.link(tx, last["result"])
            inspector = b.Inspector(tx, commit=commit)
            actual = inspector.node(result)
            datum, value = b.node_value(tx, rf["value"])
            if (tuple(b.link(tx, rf[n]) for n in ("request", "initial-attempt", "inputs", "returned", "call0", "call1", "getter0", "getter1")) !=
                (request, initial, q.inputs.dag, result, *call_ids, *spine["getters"]) or datum != actual.datum or value.kind != "i64"):
                raise ValueError("outer return exact leaf R/owner/ledger differs")
            seen.update(inspector.seen)
    budget(seen)
    return dict(request=request, attempt=final_attempt, initial=initial, result=returned_id,
                leaf_result=result, datum=datum, inputs_datum=q.inputs.datum, closure=q.closure, outcome="success" if role == SUCCESS_ROLE else "failure",
                getters=tuple(spine["getters"]), calls=call_ids, semantic_ids=frozenset(seen))


def inspect_spine(path, commit, request, initial, aid, seen, depth=0):
    """Walk actual native step deltas backwards, then validate ordered semantic transitions."""
    authority_depth(depth)
    steps = []
    with d.Repository(path) as repo, repo.read() as tx:
        cursor = commit
        while True:
            parents = tx.get_commit(cursor).parents
            if len(steps) > 24 or not parents:
                raise ValueError("bounded outer phase spine missing initial")
            previous = parents[0]
            old, current = tree(tx, previous), tree(tx, cursor)
            if current.get("outer-attempt-" + aid) == initial and "outer-attempt-" + aid not in old:
                if parents != (previous,) or set(current) - set(old) != {"outer-attempt-" + aid} or any(current[n] != v for n, v in old.items()):
                    raise ValueError("initial T exact delta differs")
                submission = previous
                break
            phase_names = [n for n in set(current) - set(old) if n.startswith("phase-" + aid + "-")]
            if len(phase_names) != 1:
                raise ValueError("phase must add one canonical phase name")
            phase = current[phase_names[0]]
            fields = tx.get_dag(phase).bindings
            kind = b.scalar(tx, fields["kind"], "string")
            if kind not in PHASE_LINKS:
                raise ValueError("unknown phase kind")
            b.shape(tx, phase, ("role", "request", "initial-attempt", "kind", "index", "previous", *PHASE_LINKS[kind], *PHASE_VALUES[kind]), PHASE_ROLE)
            index = b.scalar(tx, fields["index"], "i64")
            if (phase_names[0] != phase_name(aid, index) or oid(tx, fields["previous"]) != previous
                or (b.link(tx, fields["request"]), b.link(tx, fields["initial-attempt"])) != (request, initial)):
                raise ValueError("phase ordinal/owner/previous differs")
            payloads = payload_names(aid, index, kind)
            if set(current) - set(old) != set(payloads.values()) | {phase_names[0]} or any(current[n] != v for n, v in old.items()):
                raise ValueError("phase exact tree delta differs")
            links = {n: b.link(tx, fields[n]) for n in PHASE_LINKS[kind]}
            if any(current[payloads[n]] != target for n, target in links.items()):
                raise ValueError("phase actual payload association differs")
            values = {n: b.scalar(tx, fields[n], "i64" if n == "slot" else "string" if n == "selection-slot" else "bytes") for n in PHASE_VALUES[kind]}
            expected_parents = (previous, d.ObjectId(values["completion"])) if kind == "leaf-join" else (previous,)
            if parents != expected_parents:
                raise ValueError("ordered leaf F join parents differ")
            steps.append((cursor, kind, links, values, index))
            cursor = previous
            # Public Q and S each have their own unchanged exact single-parent delta.
            if kind == "leaf-pending":
                if d.ObjectId(values["submission"]) != previous:
                    raise ValueError("pending call submission differs")
                qf = tx.get_dag(b.link(tx, tx.get_dag(links["call"]).bindings["request"])).root
                qid = b.scalar(tx, qf, "string")
                cursor = single_delta(tx, previous, ("request-" + qid,))
            elif kind == "leaf-reused":
                if d.ObjectId(values["reuse-commit"]) != previous:
                    raise ValueError("reuse phase publication differs")
                wf = tx.get_dag(links["reuse"]).bindings
                leaf_q = b.link(tx, wf["request"])
                qid = b.scalar(tx, tx.get_dag(leaf_q).root, "string")
                cursor = single_delta(tx, previous, ("reuse-" + qid,))
                if tree(tx, previous)["reuse-" + qid] != links["reuse"]:
                    raise ValueError("reuse phase W tree differs")
            elif kind == "leaf-selected":
                if d.ObjectId(values["selection-commit"]) != previous:
                    raise ValueError("selected phase publication differs")
                cursor = single_delta(tx, previous, (values["selection-slot"],))
                if tree(tx, previous)[values["selection-slot"]] != links["selection"]:
                    raise ValueError("selected phase S tree differs")
        if any(row[4] != i for i, row in enumerate(reversed(steps))):
            raise ValueError("phase positions not consecutive")
    q = inspect_request(path, commit=submission, request=request, seen=seen, depth=depth)
    with d.Repository(path) as repo, repo.read() as tx:
        initial_fields, initial_aid = occurrence(tx, initial, T_ROLE, "ca-", ("request", "plan"))
        if (q.action != "execute-fresh" or initial_aid != aid
            or b.link(tx, initial_fields["request"]) != q.request or b.link(tx, initial_fields["plan"]) != q.plan):
            raise ValueError("ORIGINAL fresh outer Q/initial T/plan authority differs")
    getters, calls, pending, prep, failed, returned = [], [], None, None, None, None
    joined = reused = selected_phase = None
    double_inputs = None
    double_selected = inspect_leaf_success(path, commit=q.base, slot=DOUBLE_SLOT, seen=seen, depth=depth + 1)[0] if _has_slot(path, q.base, DOUBLE_SLOT) else None
    for current, kind, links, values, index in reversed(steps):
        if failed is not None or returned is not None:
            raise ValueError("phase follows terminal result/failure")
        with d.Repository(path) as repo, repo.read() as tx:
            if kind in ("get-a", "get-b"):
                if len(getters) >= 2 or kind != ("get-a", "get-b")[len(getters)] or calls or prep is not None:
                    raise ValueError("outer getter order/dispatch guard differs")
                inspect_getter(tx, current, links["node"], q.inputs.dag, "a" if kind == "get-a" else "b", q.closure["map_binding"], seen)
                getters.append(links["node"])
            elif kind == "double-input":
                if len(calls) != 1 or pending is not None:
                    raise ValueError("double input before actual successful add")
                _, sources = arguments(tx, current, links["inputs"], ("x",), seen)
                result = b.link(tx, tx.get_dag(calls[0]).bindings["result"])
                if sources["x"].dag != result or double_inputs is not None:
                    raise ValueError("double arguments must use exact returned add R")
                double_inputs = links["inputs"]
            elif kind == "leaf-prepare":
                if len(getters) != 2 or prep is not None or len(calls) > 1 or values["slot"] != len(calls):
                    raise ValueError("call before getter checks/ordered slot differs")
                fields = tx.get_dag(links["decision"]).bindings
                target = q.closure["add" if values["slot"] == 0 else "double"]
                optional = ("upstream-slot", "upstream") if values["slot"] == 1 else ()
                b.shape(tx, links["decision"], ("role", "outer-request", "outer-attempt", "slot", "closure", "binding", "environment", "key", "inputs", "control",
                    "binding-name", "inputs-name", "basis", *optional), LEAF_D_ROLE)
                if tuple(b.link(tx, fields[n]) for n in ("binding", "environment", "key")) != tuple(target[n] for n in ("binding", "environment", "key")):
                    raise ValueError("leaf decision exact B/E/key differs")
                previous = tx.get_commit(current).parents[0]
                payloads = payload_names(aid, index, "leaf-prepare")
                if (oid(tx, fields["basis"]) != previous or b.scalar(tx, fields["binding-name"], "string") != payloads["binding"]
                    or b.scalar(tx, fields["inputs-name"], "string") != payloads["inputs"]):
                    raise ValueError("leaf decision exact basis/named dimensions differ")
                if (b.link(tx, fields["outer-request"]), b.link(tx, fields["outer-attempt"]), b.link(tx, fields["closure"]),
                    b.link(tx, fields["inputs"]), b.scalar(tx, fields["slot"], "i64")) != (request, initial, target["dag"], links["inputs"], values["slot"]):
                    raise ValueError("prepared leaf decision owner/capture/input differs")
                if links["binding"] != target["binding"] or (values["slot"] == 0 and links["inputs"] != q.inputs.dag):
                    raise ValueError("add must forward SAME original input DAG")
                expected_control = "fresh"
                if values["slot"] == 1:
                    if links["inputs"] != double_inputs:
                        raise ValueError("double must use THIS constructed map")
                    first = tx.get_dag(calls[0]).bindings
                    first_slot = b.scalar(tx, first["selection-slot"], "string")
                    if (b.scalar(tx, fields["upstream-slot"], "string"), b.link(tx, fields["upstream"])) != (first_slot, b.link(tx, first["selection"])):
                        raise ValueError("double THIS upstream S/T/R ledger differs")
                    pf = tx.get_dag(q.plan).bindings
                    control = b.scalar(tx, pf["double-control"], "string")
                    requested, _ = arguments(tx, current, links["inputs"], ("x",), seen)
                    if double_selected is not None:
                        old_selected, _ = arguments(tx, current, double_selected.inputs, ("x",), seen)
                        hit = double_selected.binding == target["binding"] and old_selected.datum == requested.datum
                    else:
                        hit = False
                    if control == "require-selected" and not hit:
                        raise ValueError("required pinned double selection mismatch")
                    if control != "fresh" and hit:
                        expected_control = "reuse-selected"
                if b.scalar(tx, fields["control"], "string") != expected_control:
                    raise ValueError("leaf action differs from actual pinned plan")
                prep = (links, values["slot"], expected_control)
            elif kind == "leaf-pending":
                if prep is None or pending is not None:
                    raise ValueError("leaf pending without preparation")
                cf = b.shape(tx, links["call"], ("role", "outer-request", "outer-attempt", "slot", "closure", "inputs", "request", "control"), CALL_ROLE)
                target = q.closure["add" if prep[1] == 0 else "double"]
                if (b.link(tx, cf["outer-request"]), b.link(tx, cf["outer-attempt"]), b.scalar(tx, cf["slot"], "i64"),
                    b.link(tx, cf["closure"]), b.link(tx, cf["inputs"])) != (request, initial, prep[1], target["dag"], prep[0]["inputs"]):
                    raise ValueError("pending call exact owner/target/input differs")
                if b.scalar(tx, cf["control"], "string") != prep[2]:
                    raise ValueError("pending action differs from THIS prepared plan")
                pending = links["call"]
            elif kind == "leaf-join":
                if pending is None or prep[2] != "fresh" or joined is not None or reused is not None:
                    raise ValueError("fresh F join outside pending fresh call")
                joined = d.ObjectId(values["completion"])
            elif kind == "leaf-reused":
                if pending is None or prep[2] != "reuse-selected" or joined is not None or reused is not None:
                    raise ValueError("reuse phase outside pinned reuse call")
                wf = b.shape(tx, links["reuse"], ("role", "request", "attempt", "result"), "example-explicit-reuse-v1", "result")
                if tuple(b.link(tx, wf[n]) for n in ("request", "attempt", "result")) != (
                    b.link(tx, tx.get_dag(pending).bindings["request"]), double_selected.attempt, double_selected.result):
                    raise ValueError("reuse phase NEW Q/OLD selected T/R differs")
                reused = links["reuse"]
            elif kind == "leaf-selected":
                if pending is None or joined is None or reused is not None or selected_phase is not None:
                    raise ValueError("public S before exact fresh join or duplicated")
                sf = tx.get_dag(links["selection"]).bindings
                if oid(tx, sf["completion"]) != joined:
                    raise ValueError("public S must certify THIS joined F")
                selected_phase = (links["selection"], values["selection-slot"])
            elif kind == "leaf-done":
                if pending is None or (joined is None and reused is None):
                    raise ValueError("leaf completion without pending completion authority")
            elif kind == "returned":
                if len(calls) != 2 or pending is not None:
                    raise ValueError("outer return before both successful calls")
                returned = links["return"]
        if kind == "leaf-pending":
            with d.Repository(path) as repo, repo.read() as tx:
                pf = tx.get_dag(pending).bindings
                own_q = b.link(tx, pf["request"])
                bn = payload_names(aid, index - 1, "leaf-prepare")["binding"]
                inn = payload_names(aid, index - 1, "leaf-prepare")["inputs"]
            spec = public_prepare(path, d.ObjectId(values["submission"]), bn, inn,
                                  q.closure["add" if prep[1] == 0 else "double"]["intent"], own_q)
            if (spec.binding, spec.inputs) != (prep[0]["binding"], prep[0]["inputs"]):
                raise ValueError("pending public Q exact dimensions differ")
        if kind == "leaf-done":
            failed_witness = None
            with d.Repository(path) as repo, repo.read() as tx:
                fields = tx.get_dag(links["call"]).bindings
                status = b.scalar(tx, fields["status"], "string")
                extras = ("selection", "selection-slot", "attempt", "result") if status == "success" else ("witness",) if status == "failure" else None
                if extras is None:
                    raise ValueError("leaf final status differs")
                b.shape(tx, links["call"], ("role", "pending", "status", *extras), CALL_ROLE)
                if b.link(tx, fields["pending"]) != pending:
                    raise ValueError("leaf final pending association differs")
                pf = tx.get_dag(pending).bindings
                own_q = b.link(tx, pf["request"])
                if status == "success":
                    slot = b.scalar(tx, fields["selection-slot"], "string")
                    claimed = tuple(b.link(tx, fields[n]) for n in ("selection", "attempt", "result"))
                    if prep[2] == "fresh" and selected_phase != (claimed[0], slot):
                        raise ValueError("fresh DONE requires THIS exact prior S phase")
                    if prep[2] == "reuse-selected" and (selected_phase is not None or reused is None or slot != DOUBLE_SLOT):
                        raise ValueError("reuse DONE requires pinned S and prior W only")
                else:
                    if prep[2] != "fresh" or joined is None or selected_phase is not None:
                        raise ValueError("failed DONE requires pending fresh F, not success S")
                    failed = links["call"]
                    failed_witness = b.link(tx, fields["witness"])
                    inspect_failure(tx, current, failed_witness, own_q)
            if failed_witness is not None:
                actual_failure = inspect_failed_witness(path, current, failed_witness, own_q)
                if actual_failure.commit != joined:
                    raise ValueError("failed call witness must certify THIS joined F")
            if status == "success":
                selected, _ = inspect_leaf_success(path, commit=current, slot=slot, seen=seen, depth=depth + 1)
                if selected.request != own_q and (reused is None or selected.dag != double_selected.dag):
                    raise ValueError("reused call must consume exact pinned selection")
                if selected.request == own_q and (joined != selected.completion or prep[2] != "fresh"):
                    raise ValueError("fresh call ORIGINAL Q/joined F differs")
                if claimed != (selected.dag, selected.attempt, selected.result):
                    raise ValueError("call success public ORIGINAL S/T/R differs")
                with d.Repository(path) as repo, repo.read() as tx:
                    selected_target = leaf.inspect(tx, b.link(tx, tx.get_dag(pending).bindings["closure"]), *leaf.sources())
                    selected_inputs = b.link(tx, tx.get_dag(pending).bindings["inputs"])
                    requested, _ = arguments(tx, current, selected_inputs, leaf.contract(selected_target["intent"])[1], seen)
                    selected_full, _ = arguments(tx, current, selected.inputs, leaf.contract(selected.intent_uri)[1], seen)
                    if selected.binding != selected_target["binding"] or selected_full.datum != requested.datum:
                        raise ValueError("call reuse exact captured binding/full MAP differs")
                    # A fresh call's public Q equals producing Q; reuse own Q remains separate.
                    if selected.request != own_q:
                        inspect_leaf_reuse(tx, current, own_q, selected)
                calls.append(links["call"])
            else:
                calls.append(links["call"])
            pending = prep = joined = reused = selected_phase = None
    budget(seen)
    return dict(submission=submission, getters=getters, calls=calls, failed=failed, returned=returned, double_inputs=double_inputs)


def _has_slot(path, commit, slot):
    with d.Repository(path) as repo, repo.read() as tx:
        return slot in tree(tx, commit)


def inspect_leaf_reuse(tx, commit, request, selected):
    qid = b.scalar(tx, tx.get_dag(request).root, "string")
    dag = tree(tx, commit)["reuse-" + qid]
    fields = b.shape(tx, dag, ("role", "request", "attempt", "result"), "example-explicit-reuse-v1", "result")
    if tuple(b.link(tx, fields[n]) for n in ("request", "attempt", "result")) != (request, selected.attempt, selected.result):
        raise ValueError("leaf ownQ/OLD T/R W differs")


def inspect_failure(tx, commit, witness, request):
    fields = b.shape(tx, witness, ("role", "completion", "request", "expected", "job", "observation"), PREFIX + "failure-witness-v1")
    completion = oid(tx, fields["completion"])
    if b.link(tx, fields["request"]) != request or completion not in history(tx, commit):
        raise ValueError("failed leaf witness owner/retention differs")
    # Inspection uses public packet validation AFTER target read handles close (caller responsibility).
    return completion, tuple(b.scalar(tx, fields[n], "bytes") for n in ("expected", "job", "observation"))


def inspect_failed_witness(path, commit, witness, request):
    with d.Repository(path) as repo, repo.read() as tx:
        completion, headers = inspect_failure(tx, commit, witness, request)
    if any(len(raw) > ex.MAX_DESCRIPTOR_BYTES for raw in headers):
        raise ValueError("failure framing exceeds public profile")
    bundle = transfer.export_commit(path, commit=completion)
    with tempfile.TemporaryDirectory(prefix="dml-captured-failure-validation-") as root:
        root = Path(root)
        for n, raw in zip(("expected.json", "job.json", "observation.json"), headers):
            root.joinpath(n).write_bytes(raw)
        root.joinpath("snapshot.bundle").write_bytes(bundle)
        expected = ex.load_exchange_handle(root / "expected.json").expected
        got = ex.read_observation(root, expected=expected)
    if (got.phase != "completion" or got.commit != completion or got.request != request
        or got.completion.outcome != "failure"):
        raise ValueError("failed witness PUBLIC completion differs")
    return got

