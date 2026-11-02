"""Example-local func/MAP-datum reuse; NEW Md/Dd, own full Q and old T/R.

No dispatch, discovery, automatic adoption, reinterpretation of old helper roles,
private runtime codec, or native entity. All validation handles close before writes.
"""

from dataclasses import dataclass, replace
from pathlib import Path
import tempfile

import daggerml as d
from daggerml import exchange as ex, transfer
import recorded_maps as maps
import reuse_selection as selection

TABLE_ROLE = "example-datum-reuse-table-v1"
ENTRIES_ROLE = "example-datum-reuse-entries-v1"
ENTRY_ROLE = "example-datum-reuse-entry-v1"
DECISION_ROLE = "example-datum-reuse-decision-v1"
W_ROLE = "example-explicit-reuse-v1"
MAX_ENTRIES = 16
CONTROLS = ("try-selected", "fresh", "require-selected")
SCALARS = ("intent", "binding-name", "inputs-name", "table-name", "control", "action", "reason")
LINKS = ("binding", "inputs", "construction")


@dataclass(frozen=True)
class Entry:
    key: str
    dag: d.ObjectId
    inputs: maps.Inputs
    selected: selection.Selection
    returned: maps.Returned


@dataclass(frozen=True)
class Table:
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    intent_uri: str
    entries: tuple


@dataclass(frozen=True)
class Decision:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    intent_uri: str
    binding: d.ObjectId
    binding_name: str
    inputs: maps.Inputs
    inputs_name: str
    table_name: str
    control: str
    action: str
    reason: str
    table: object
    entry: object

    @property
    def selected(self):
        return None if self.entry is None else self.entry.selected


@dataclass(frozen=True)
class Satisfaction:
    commit: d.ObjectId
    dag: d.ObjectId
    ref: str
    attempt: d.ObjectId
    result: d.ObjectId


@dataclass(frozen=True)
class Request:
    decision: Decision
    recorded: ex.RecordedRequest
    reused: object


@dataclass(frozen=True)
class Inspection:
    decision: Decision
    request: d.ObjectId
    requested: maps.Inputs
    executed: object
    returned: object


def datum_key(datum):
    if type(datum) is not d.ObjectId:
        raise TypeError("argument-map datum requires ObjectId")
    return "datum-" + str(datum)


def _uri(uri):
    if type(uri) is not str or d.canonicalize_uri(uri) != uri:
        raise ValueError("intent URI must be canonical")


def _distinct(*names):
    for name in names:
        maps.name(name)
    if len(set(names)) != len(names):
        raise ValueError("metadata/binding/input/selection names must differ")


def inspect_table(path, *, commit, table_name):
    maps.name(table_name)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        tree = maps.tree(tx, commit)
        dag = tree[table_name]
        fields = maps.shape(tx, dag, ("role", "intent", "profile", "entries"), "intent", TABLE_ROLE)
        uri = maps.scalar(tx, fields["intent"], "uri")
        _uri(uri)
        if maps.scalar(tx, fields["profile"], "string") != maps.PROFILE:
            raise ValueError("table input profile differs")
        rows = tx.get_dag(maps.link(tx, fields["entries"]))
        if "role" not in rows.bindings or rows.root != rows.bindings["role"] or len(rows.bindings) > MAX_ENTRIES + 1 or maps.scalar(tx, rows.root, "string") != ENTRIES_ROLE:
            raise ValueError("bounded table entries shape/root/role differs")
        captured = []
        for key in sorted(set(rows.bindings) - {"role"}):
            row = maps.link(tx, rows.bindings[key])
            fields = maps.shape(tx, row, ("role", "arguments", "inputs", "selection", "slot"), "selection", ENTRY_ROLE)
            argument, _ = maps.node_value(tx, fields["arguments"])
            inputs, selected = (maps.link(tx, fields[n]) for n in ("inputs", "selection"))
            slot = maps.scalar(tx, fields["slot"], "string")
            _distinct(table_name, slot)
            if key != datum_key(argument) or tree[slot] != selected:
                raise ValueError("table key/pinned immutable selection slot differs")
            captured.append((key, row, argument, inputs, selected, slot))
        if len({row[-1] for row in captured}) != len(captured):
            raise ValueError("table selection slots must be unique")
    entries = []
    # Independent bounded traversal for each row: ALL rows, not just matching one.
    for key, row, argument, inputs, selected, slot in captured:
        inspector = maps.Inspector(path, commit)
        got = inspector.selected(slot)
        if (got.dag, got.intent_uri, got.inputs) != (selected, uri, inputs):
            raise ValueError("table row differs from PUBLIC successful S/full Q")
        full = inspector.input(inputs)
        returned = inspector.returned(got.result, request=got.request, inputs=got.inputs)
        if full.datum != argument:
            raise ValueError("table argument datum differs from original full input")
        entries.append(Entry(key, row, full, got, returned))
    return Table(commit, dag, table_name, uri, tuple(entries))


def _publish_table(path, commit, table_name, uri, rows, ref, map_size):
    with d.Repository(path, map_size=map_size) as repo, repo.write() as tx:
        tree = maps.tree(tx, commit)
        nodes = {"role": maps.literal(tx, ENTRIES_ROLE)}
        authored_rows = []
        for row in rows:
            dag = maps.record(tx, ENTRY_ROLE, {"slot": row.selected.slot}, {"inputs": row.inputs.dag, "selection": row.selected.dag}, "selection", {"arguments": tx.put_literal(row.inputs.datum)})
            nodes[row.key] = tx.put_subdag(dag)
            authored_rows.append(replace(row, dag=dag))
        entries = tx.put_dag(root=nodes["role"], bindings=nodes)
        dag = maps.record(tx, TABLE_ROLE, {"intent": d.Datum.uri(uri), "profile": maps.PROFILE}, {"entries": entries}, "intent")
        tree[table_name] = dag
        authored = tx.put_commit(tx.put_tree(tree), parents=(commit,))
        tx.create_ref(ref, authored)
        response = Table(authored, dag, table_name, uri, tuple(replace(row, selected=replace(row.selected, commit=authored)) for row in authored_rows))
    return response


def define_table(path, *, commit, table_name, intent_uri, ref, map_size=0):
    maps.name(table_name)
    maps.name(ref)
    maps.map_size(map_size)
    _uri(intent_uri)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        if table_name in maps.tree(tx, commit):
            raise ValueError("new table name must be absent")
    return _publish_table(path, commit, table_name, intent_uri, (), ref, map_size)


def _update(path, commit, table_name, slot, ref, size, adopting):
    _distinct(table_name, slot)
    maps.name(ref)
    maps.map_size(size)
    previous = inspect_table(path, commit=commit, table_name=table_name)
    inspector = maps.Inspector(path, commit)
    selected = inspector.selected(slot)
    if selected.intent_uri != previous.intent_uri:
        raise ValueError("table intent scope differs from selection")
    full = inspector.input(selected.inputs)
    output = inspector.returned(selected.result, request=selected.request, inputs=selected.inputs)
    key = datum_key(full.datum)
    old = next((r for r in previous.entries if r.key == key), None)
    if adopting:
        if old is None or old.selected.attempt_id == selected.attempt_id:
            raise ValueError("adoption requires matching row and distinct successful attempt")
    elif old is not None or len(previous.entries) >= MAX_ENTRIES:
        raise ValueError("insertion requires absent key and available capacity")
    rows = tuple(r for r in previous.entries if r.key != key) + (Entry(key, selected.dag, full, selected, output),)
    return _publish_table(path, commit, table_name, previous.intent_uri, tuple(sorted(rows, key=lambda r: r.key)), ref, size)


def select_entry(path, *, commit, table_name, selection_slot, ref, map_size=0):
    return _update(path, commit, table_name, selection_slot, ref, map_size, False)


def adopt_entry(path, *, commit, table_name, selection_slot, ref, map_size=0):
    return _update(path, commit, table_name, selection_slot, ref, map_size, True)


def remove_entry(path, *, commit, table_name, argument_datum, ref, map_size=0):
    maps.name(ref)
    maps.map_size(map_size)
    key = datum_key(argument_datum)
    previous = inspect_table(path, commit=commit, table_name=table_name)
    if not any(row.key == key for row in previous.entries):
        raise ValueError("removal requires present argument datum key")
    return _publish_table(path, commit, table_name, previous.intent_uri, tuple(r for r in previous.entries if r.key != key), ref, map_size)


def _prepare(path, commit, binding_name, inputs_name, uri, request=None):
    with tempfile.TemporaryDirectory(prefix="dml-datum-validation-") as scratch:
        got = ex.prepare_exchange(path, commit=commit, binding_name=binding_name, inputs_name=inputs_name, intent_uri=uri, request=request, worker_ref="validation", workspace=Path(scratch) / "input")
    return got


def _resolve(path, commit, uri, binding_name, inputs_name, table_name, control, decision_name):
    _uri(uri)
    _distinct(binding_name, inputs_name, table_name, decision_name)
    if decision_name.startswith(("request-q-", "attempt-a-", "publication-a-", "reuse-q-")):
        raise ValueError("decision name collides with occurrence names")
    if type(control) is not str or control not in CONTROLS:
        raise ValueError("unknown datum reuse control")
    spec = _prepare(path, commit, binding_name, inputs_name, uri)
    full = maps.inspect_input(path, commit=commit, dag=spec.inputs)
    table = entry = None
    if control == "fresh":
        action, reason = "execute-fresh", "explicit-fresh"
    else:
        with d.Repository(path) as repo, repo.read() as tx:
            present = table_name in maps.tree(tx, commit)
        if present:
            table = inspect_table(path, commit=commit, table_name=table_name)
            if table.intent_uri != uri:
                raise ValueError("table intent scope differs")
            for row in table.entries:
                _distinct(binding_name, inputs_name, table_name, decision_name, row.selected.slot)
            entry = next((r for r in table.entries if r.key == datum_key(full.datum)), None)
        if entry is None:
            if control == "require-selected":
                raise ValueError("required selected reuse has no matching datum entry")
            action, reason = "execute-fresh", "no-table" if table is None else "no-entry"
        else:
            action, reason = "reuse-selected", "selected-datum"
    return spec, full, table, entry, action, reason


def _claims(uri, binding_name, inputs_name, table_name, control, action, reason):
    return dict(zip(SCALARS, (d.Datum.uri(uri), binding_name, inputs_name, table_name, control, action, reason)))


def _links(spec, full, table, entry):
    links = dict(zip(LINKS, (spec.binding, spec.inputs, full.construction)))
    if table is not None:
        links["table"] = table.dag
    if entry is not None:
        links.update(entry=entry.dag, selection=entry.selected.dag)
    return links


def _response(base, commit, dag, decision_name, uri, binding_name, inputs_name, table_name, control, resolved):
    spec, full, table, entry, action, reason = resolved
    return Decision(base, commit, dag, decision_name, uri, spec.binding, binding_name, full, inputs_name, table_name, control, action, reason, table, entry)


def inspect_decision(path, *, commit, decision_name):
    maps.name(decision_name)
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("decision requires exact one basis parent")
        base = parents[0]
        entries, old = maps.tree(tx, commit), maps.tree(tx, base)
        dag = entries.pop(decision_name)
        if decision_name in old or entries != old:
            raise ValueError("decision must add ONLY named Dd")
        got = tx.get_dag(dag)
        fields = got.bindings
        required = {"role", "arguments", *SCALARS, *LINKS}
        if set(fields) not in (required, required | {"table"}, required | {"table", "entry", "selection"}) or got.root != fields["inputs"]:
            raise ValueError("decision shape/root differs")
        if maps.scalar(tx, fields["role"], "string") != DECISION_ROLE:
            raise ValueError("decision role differs")
        values = {n: maps.scalar(tx, fields[n], "uri" if n == "intent" else "string") for n in SCALARS}
        argument, _ = maps.node_value(tx, fields["arguments"])
        links = {n: maps.link(tx, fields[n]) for n in set(fields) - {"role", "arguments", *SCALARS}}
    resolved = _resolve(path, base, values["intent"], values["binding-name"], values["inputs-name"], values["table-name"], values["control"], decision_name)
    spec, full, table, entry, action, reason = resolved
    expected_values = _claims(values["intent"], values["binding-name"], values["inputs-name"], values["table-name"], values["control"], action, reason)
    expected_values["intent"] = values["intent"]
    if argument != full.datum or links != _links(spec, full, table, entry) or values != expected_values:
        raise ValueError("decision claims differ from actual pinned basis")
    transfer.export_commit(path, commit=commit)
    return _response(base, commit, dag, decision_name, values["intent"], values["binding-name"], values["inputs-name"], values["table-name"], values["control"], resolved)


def inspect_request(path, *, commit, request, decision_name, satisfaction_commit=None):
    if type(request) is not d.ObjectId:
        raise TypeError("own full submitted Q requires exact ObjectId")
    with d.Repository(path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("submission requires exact one decision parent")
    decision = inspect_decision(path, commit=parents[0], decision_name=decision_name)
    spec = _prepare(path, commit, decision.binding_name, decision.inputs_name, decision.intent_uri, request=request)
    if (spec.binding, spec.inputs, spec.intent_uri) != (decision.binding, decision.inputs.dag, decision.intent_uri):
        raise ValueError("actual full Q differs from decision")
    if satisfaction_commit is not None:
        if decision.selected is None:
            raise ValueError("fresh decision cannot claim reuse satisfaction")
        with d.Repository(path) as repo, repo.read() as tx:
            basis = maps.tree(tx, commit)
            qid = maps.scalar(tx, tx.get_dag(request).root, "string")
            entries = maps.tree(tx, satisfaction_commit)
            dag = entries.pop("reuse-" + qid, None)
            if dag is None or tx.get_commit(satisfaction_commit).parents != (commit,) or entries != basis:
                raise ValueError("satisfaction must add ONLY W on exact own Q")
            fields = maps.shape(tx, dag, ("role", "request", "attempt", "result"), "result", W_ROLE)
            if tuple(maps.link(tx, fields[n]) for n in ("request", "attempt", "result")) != (request, decision.selected.attempt, decision.selected.result):
                raise ValueError("W own Q/historical T/R differs")
        transfer.export_commit(path, commit=satisfaction_commit)
    return Inspection(decision, request, decision.inputs, None if decision.entry is None else decision.entry.inputs, None if decision.entry is None else decision.entry.returned)


def _validate_recorded(path, recorded, decision, submission_ref):
    if (recorded.base, recorded.intent_uri, recorded.binding, recorded.inputs, recorded.binding_name, recorded.inputs_name, recorded.ref) != (decision.commit, decision.intent_uri, decision.binding, decision.inputs.dag, decision.binding_name, decision.inputs_name, submission_ref):
        raise ValueError("returned own Q description differs from authored decision")
    with d.Repository(path) as repo, repo.read() as tx:
        if tx.get_commit(recorded.commit).parents != (decision.commit,):
            raise ValueError("actual submission parent differs from authored decision")
        if maps.scalar(tx, tx.get_dag(recorded.request).root, "string") != recorded.request_id or tx.get_ref(submission_ref) != recorded.commit or tx.get_ref("request-" + recorded.request_id) != recorded.commit:
            raise ValueError("actual submission/reservation differs from response")
    inspect_request(path, commit=recorded.commit, request=recorded.request, decision_name=decision.name)


def _publish_reuse(path, recorded, selected, ref, size):
    with d.Repository(path, map_size=size) as repo, repo.write() as tx:
        entries = maps.tree(tx, recorded.commit)
        name = "reuse-" + recorded.request_id
        if name in entries:
            raise ValueError("reuse name already exists")
        dag = maps.record(tx, W_ROLE, links={"request": recorded.request, "attempt": selected.attempt, "result": selected.result}, root="result")
        entries[name] = dag
        commit = tx.put_commit(tx.put_tree(entries), parents=(recorded.commit,))
        tx.create_ref(ref, commit)
        response = Satisfaction(commit, dag, ref, selected.attempt, selected.result)
    return response


def record_request(path, *, commit, intent_uri, binding_name, inputs_name, table_name, decision_name, decision_ref, submission_ref, control="try-selected", reuse_ref=None, map_size=0):
    for n in (decision_ref, submission_ref):
        maps.name(n)
    maps.map_size(map_size)
    if reuse_ref is not None:
        maps.name(reuse_ref)
    if len({decision_ref, submission_ref, reuse_ref}) != 3:
        raise ValueError("publication refs must differ")
    resolved = _resolve(path, commit, intent_uri, binding_name, inputs_name, table_name, control, decision_name)
    spec, full, table, entry, action, reason = resolved
    if (reuse_ref is not None) != (entry is not None):
        raise ValueError("reuse ref required ONLY for selected hit")
    with d.Repository(path, map_size=map_size) as repo, repo.write() as tx:
        entries = maps.tree(tx, commit)
        if decision_name in entries:
            raise ValueError("new decision name must be absent")
        dag = maps.record(tx, DECISION_ROLE, _claims(intent_uri, binding_name, inputs_name, table_name, control, action, reason), _links(spec, full, table, entry), "inputs", {"arguments": tx.put_literal(full.datum)})
        entries[decision_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(decision_ref, authored)
        decision = _response(commit, authored, dag, decision_name, intent_uri, binding_name, inputs_name, table_name, control, resolved)
    recorded = ex.record_exchange_request(path, commit=authored, binding_name=binding_name, inputs_name=inputs_name, intent_uri=intent_uri, ref=submission_ref, map_size=map_size)
    _validate_recorded(path, recorded, decision, submission_ref)
    reused = None if entry is None else _publish_reuse(path, recorded, entry.selected, reuse_ref, map_size)
    inspect_request(path, commit=recorded.commit, request=recorded.request, decision_name=decision_name, satisfaction_commit=None if reused is None else reused.commit)
    if reused is not None:
        with d.Repository(path) as repo, repo.read() as tx:
            if tx.get_ref(reuse_ref) != reused.commit or maps.tree(tx, reused.commit).get("reuse-" + recorded.request_id) != reused.dag or (reused.attempt, reused.result, reused.ref) != (entry.selected.attempt, entry.selected.result, reuse_ref):
                raise ValueError("actual owning satisfaction differs from response")
    return Request(decision, recorded, reused)
