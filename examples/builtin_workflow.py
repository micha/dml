"""Bounded example-local map/get choice and ONE-S node-input own-Q/W bridge.

No generic registry/table/cache policy. Public S validates success separately from
installed builtin semantic inspection. All validation handles close before writes.
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

INTENT = "urn:example:node-sum-pair"
CHOICE_ROLE = "example-builtin-choice-v1"
DECISION_ROLE = "example-node-reuse-decision-v1"
W_ROLE = "example-explicit-reuse-v1"
SLOT = "selected-sum-pair"


def tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def name(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None:
        raise ValueError("explicit name outside native profile")
    return value


def capture(map_binding, list_binding, *, logical_source=None):
    source = (Path(__file__).with_name("builtin_funcs.py").read_bytes()
              if logical_source is None else logical_source)
    return ("import types\nfrom daggerml import builtin,local,ObjectId\n"
            "logical=types.ModuleType('builtin_funcs')\n"
            "exec(compile(%r,'builtin_funcs.py','exec'),logical.__dict__)\n"
            "MAP_BINDING=%r\nLIST_BINDING=%r\n"
            "builtin.publish_callable(local.child_context(),logical.sum_pair,"
            "map_binding=ObjectId.from_hex(MAP_BINDING),"
            "list_binding=ObjectId.from_hex(LIST_BINDING))\n"
            % (source, str(map_binding), str(list_binding))).encode()


@dataclass(frozen=True)
class Choice:
    dag: d.ObjectId
    default: str
    map_v1: d.ObjectId
    map_v2: d.ObjectId
    normal_v1: d.ObjectId
    normal_v2: d.ObjectId
    list_v1: d.ObjectId
    logical_source: bytes

    def selected(self, label):
        if label not in ("v1", "v2"):
            raise ValueError("unsupported implementation label")
        return ((self.map_v1, self.normal_v1) if label == "v1"
                else (self.map_v2, self.normal_v2))


def put_choice(tx, *, map_v1, map_v2, normal_v1, normal_v2, list_v1, logical_source, default="v1"):
    if default not in ("v1", "v2"):
        raise ValueError("unsupported implementation label")
    return b.record(tx, CHOICE_ROLE, values={"func": d.Datum.uri(b.MAP_GET), "default": default, "logical-source": logical_source},
                    links={"map-v1": map_v1, "map-v2": map_v2, "normal-v1": normal_v1, "normal-v2": normal_v2, "list-v1": list_v1})


def inspect_choice(tx, dag):
    fields = b.shape(tx, dag, ("role", "func", "default", "logical-source", "map-v1", "map-v2", "normal-v1", "normal-v2", "list-v1"), CHOICE_ROLE)
    if b.scalar(tx, fields["func"], "uri") != b.MAP_GET:
        raise ValueError("choice func differs")
    label = b.scalar(tx, fields["default"], "string")
    ids = [b.link(tx, fields[n]) for n in ("map-v1", "map-v2", "normal-v1", "normal-v2", "list-v1")]
    source = b.scalar(tx, fields["logical-source"], "bytes")
    got = Choice(dag, label, *ids, source)
    got.selected(label)
    for version, map_id, normal_id in (("v1", got.map_v1, got.normal_v1), ("v2", got.map_v2, got.normal_v2)):
        if b.inspect_binding(tx, map_id).source_uri != "dml://source/builtin/map/get/" + version:
            raise ValueError("choice exact map binding differs")
        normal = tx.get_dag(normal_id)
        if (set(normal.bindings) != {"role", "adapter", "source", "interpreter", "timeout-ms"}
            or normal.root != normal.bindings["role"]
            or b.scalar(tx, normal.bindings["role"], "string") != "local-python-binding-v1"
            or b.scalar(tx, normal.bindings["adapter"], "uri") != local.ADAPTER_URI
            or b.scalar(tx, normal.bindings["source"], "bytes") != capture(map_id, got.list_v1, logical_source=source)):
            raise ValueError("captured normal binding wiring differs")
        interpreter = b.scalar(tx, normal.bindings["interpreter"], "string")
        timeout = b.scalar(tx, normal.bindings["timeout-ms"], "i64")
        if (not interpreter or not os.path.isabs(interpreter) or "\0" in interpreter
            or unicodedata.normalize("NFC", interpreter) != interpreter or not 1 <= timeout <= 3600000):
            raise ValueError("captured normal binding execution fields differ")
        interpreter.encode("utf-8")
    if b.inspect_binding(tx, got.list_v1).source_uri != "dml://source/builtin/list/get/v1":
        raise ValueError("choice list binding differs")
    return got


def promote(path, *, commit, choice_name, default, ref):
    name(choice_name)
    name(ref)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        old = inspect_choice(tx, entries[choice_name])
        old.selected(default)
        dag = put_choice(tx, map_v1=old.map_v1, map_v2=old.map_v2, normal_v1=old.normal_v1,
                         normal_v2=old.normal_v2, list_v1=old.list_v1, logical_source=old.logical_source, default=default)
        entries[choice_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
    return authored


def inspect_node(path, *, commit, dag):
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        return b.Inspector(tx, commit=commit).node(dag)


def _prepare(path, commit, binding_name, inputs_name, request=None):
    with tempfile.TemporaryDirectory(prefix="dml-node-validation-") as scratch:
        return ex.prepare_exchange(path, commit=commit, binding_name=binding_name,
                                   inputs_name=inputs_name, intent_uri=INTENT, request=request,
                                   worker_ref="validation", workspace=Path(scratch) / "input")


@dataclass(frozen=True)
class Decision:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    choice: Choice
    label: str
    override: str
    binding_name: str
    inputs_name: str
    inputs: b.Description
    control: str
    action: str
    reason: str
    selected: object
    executed: object
    returned: object


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


def _resolve(path, commit, choice_name, override, inputs_name, control):
    for n in (choice_name, inputs_name):
        name(n)
    if override not in ("default", "v1", "v2") or control not in ("try-selected", "fresh", "require-selected"):
        raise ValueError("invalid choice override/reuse control")
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        entries = tree(tx, commit)
        choice = inspect_choice(tx, entries[choice_name])
        label = choice.default if override == "default" else override
        _, normal = choice.selected(label)
        binding_name = "sum-" + label
        if entries[binding_name] != normal:
            raise ValueError("named normal binding differs from choice")
        full = b.Inspector(tx, commit=commit).arguments(entries[inputs_name])
        present = SLOT in entries
    spec = _prepare(path, commit, binding_name, inputs_name)
    if spec.inputs != full.dag or spec.binding != normal:
        raise ValueError("public preparation dimensions differ")
    selected = executed = returned = None
    if present:
        selected = selection.inspect(path, commit=commit, slot=SLOT)
        if selected.intent_uri != INTENT:
            raise ValueError("selected sum-pair intent differs")
        with d.Repository(path) as repo, repo.read() as tx:
            inspector = b.Inspector(tx, commit=commit)
            executed = inspector.arguments(selected.inputs)
            returned = inspector.node(selected.result)
            fields = tx.get_dag(selected.result).bindings
            if (b.link(tx, fields["request"]), b.link(tx, fields["inputs"])) != (selected.request, selected.inputs):
                raise ValueError("selected returned profile original Q/input differs")
    hit = executed is not None and executed.datum == full.datum
    if control == "fresh":
        action, reason = "execute-fresh", "explicit-fresh"
    elif hit:
        action, reason = "reuse-selected", "selected-value"
    elif control == "require-selected":
        raise ValueError("required selected value has no match")
    else:
        action, reason = "execute-fresh", "no-selection" if selected is None else "value-mismatch"
    return choice, label, binding_name, full, selected, executed, returned, action, reason


def _claims(choice_name, override, inputs_name, control, resolved):
    choice, label, binding_name, full, selected, executed, returned, action, reason = resolved
    values = {"intent": d.Datum.uri(INTENT), "choice-name": choice_name, "override": override,
              "label": label, "binding-name": binding_name, "inputs-name": inputs_name,
              "control": control, "action": action, "reason": reason}
    links = {"choice": choice.dag, "binding": choice.selected(label)[1], "inputs": full.dag}
    if selected is not None:
        links["selection"] = selected.dag
    return values, links


def _response(base, commit, dag, decision_name, override, inputs_name, control, resolved):
    choice, label, binding_name, full, selected, executed, returned, action, reason = resolved
    return Decision(base, commit, dag, decision_name, choice, label, override, binding_name,
                    inputs_name, full, control, action, reason, selected, executed, returned)


def inspect_decision(path, *, commit, decision_name):
    name(decision_name)
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("decision requires exact one parent")
        base = parents[0]
        entries, old = tree(tx, commit), tree(tx, base)
        dag = entries.pop(decision_name)
        if decision_name in old or entries != old:
            raise ValueError("decision must add ONLY named Dn")
        fields = tx.get_dag(dag).bindings
        names = ("intent", "choice-name", "override", "label", "binding-name", "inputs-name", "control", "action", "reason")
        values = {n: b.scalar(tx, fields[n], "uri" if n == "intent" else "string") for n in names}
        links = {n: b.link(tx, fields[n]) for n in ("choice", "binding", "inputs")}
        if "selection" in fields:
            links["selection"] = b.link(tx, fields["selection"])
        b.shape(tx, dag, ("role", "value", *names, *links), DECISION_ROLE, "inputs")
        datum, _ = b.node_value(tx, fields["value"])
    resolved = _resolve(path, base, values["choice-name"], values["override"], values["inputs-name"], values["control"])
    expected, expected_links = _claims(values["choice-name"], values["override"], values["inputs-name"], values["control"], resolved)
    expected["intent"] = INTENT
    if values != expected or links != expected_links or datum != resolved[3].datum:
        raise ValueError("decision claims differ from actual basis")
    return _response(base, commit, dag, decision_name, values["override"], values["inputs-name"], values["control"], resolved)


def inspect_request(path, *, commit, request, decision_name, satisfaction_commit=None):
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("submission requires one decision parent")
    decision = inspect_decision(path, commit=parents[0], decision_name=decision_name)
    spec = _prepare(path, commit, decision.binding_name, decision.inputs_name, request)
    if (spec.binding, spec.inputs) != (decision.choice.selected(decision.label)[1], decision.inputs.dag):
        raise ValueError("own Q dimensions differ")
    if satisfaction_commit is not None:
        if decision.action != "reuse-selected":
            raise ValueError("fresh decision cannot claim W")
        with d.Repository(path) as repo, repo.read() as tx:
            entries = tree(tx, satisfaction_commit)
            qid = b.scalar(tx, tx.get_dag(request).root, "string")
            w = entries.pop("reuse-" + qid)
            if tx.get_commit(satisfaction_commit).parents != (commit,) or entries != tree(tx, commit):
                raise ValueError("W must add ONLY satisfaction on own Q")
            fields = b.shape(tx, w, ("role", "request", "attempt", "result"), W_ROLE, "result")
            if tuple(b.link(tx, fields[n]) for n in ("request", "attempt", "result")) != (request, decision.selected.attempt, decision.selected.result):
                raise ValueError("W ownQ/oldT/result differ")
        transfer.export_commit(path, commit=satisfaction_commit)
    return decision


def _publish_reuse(path, recorded, selected, ref):
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, recorded.commit)
        key = "reuse-" + recorded.request_id
        if key in entries:
            raise ValueError("satisfaction already present")
        dag = b.record(tx, W_ROLE, links={"request": recorded.request, "attempt": selected.attempt, "result": selected.result}, root="result")
        entries[key] = dag
        commit = tx.put_commit(tx.put_tree(entries), parents=(recorded.commit,))
        tx.create_ref(ref, commit)
        response = Satisfaction(commit, dag, selected.attempt, selected.result)
    return response


def record_request(path, *, commit, choice_name, inputs_name, decision_name,
                   decision_ref, submission_ref, override="default", control="try-selected", reuse_ref=None):
    names = (choice_name, inputs_name, decision_name, decision_ref, submission_ref)
    for n in names:
        name(n)
    if reuse_ref is not None:
        name(reuse_ref)
    if len({decision_ref, submission_ref, reuse_ref}) != 3 or len({choice_name, inputs_name, decision_name, SLOT}) != 4:
        raise ValueError("publication refs/metadata names must differ")
    if decision_name.startswith(("request-q-", "attempt-a-", "publication-a-", "reuse-q-")):
        raise ValueError("decision name collides with occurrence names")
    resolved = _resolve(path, commit, choice_name, override, inputs_name, control)
    if (reuse_ref is not None) != (resolved[-2] == "reuse-selected"):
        raise ValueError("reuse ref required ONLY on selected hit")
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if decision_name in entries:
            raise ValueError("decision name must be absent")
        values, links = _claims(choice_name, override, inputs_name, control, resolved)
        dag = b.record(tx, DECISION_ROLE, values=values, links=links,
                       nodes={"value": tx.put_literal(resolved[3].datum)}, root="inputs")
        entries[decision_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(decision_ref, authored)
        decision = _response(commit, authored, dag, decision_name, override, inputs_name, control, resolved)
    recorded = ex.record_exchange_request(path, commit=authored, binding_name=decision.binding_name,
                                           inputs_name=inputs_name, intent_uri=INTENT, ref=submission_ref)
    if (recorded.base, recorded.binding, recorded.inputs, recorded.intent_uri, recorded.ref,
        recorded.binding_name, recorded.inputs_name) != (authored, decision.choice.selected(decision.label)[1],
                                                        decision.inputs.dag, INTENT, submission_ref,
                                                        decision.binding_name, inputs_name):
        raise ValueError("own Q response differs from authored Dn")
    with d.Repository(path) as repo, repo.read() as tx:
        if tx.get_commit(recorded.commit).parents != (authored,):
            raise ValueError("actual submission parent differs from authored Dn")
        if (tx.get_ref(submission_ref), tx.get_ref("request-" + recorded.request_id),
            b.scalar(tx, tx.get_dag(recorded.request).root, "string")) != (recorded.commit, recorded.commit, recorded.request_id):
            raise ValueError("actual ownQ/ref/reservation differs")
    inspect_request(path, commit=recorded.commit, request=recorded.request, decision_name=decision_name)
    reused = None if decision.action != "reuse-selected" else _publish_reuse(path, recorded, decision.selected, reuse_ref)
    inspect_request(path, commit=recorded.commit, request=recorded.request, decision_name=decision_name,
                    satisfaction_commit=None if reused is None else reused.commit)
    return Request(decision, recorded, reused)
