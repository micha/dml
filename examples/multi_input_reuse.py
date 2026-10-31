"""Example-local bounded multi-input selection; PUBLIC composition, never dispatch.

M/entries/Dm are ordinary DAGs, not native entities. Old choice.selection-slot
and old D remain unchanged. Close native handles before calling these operations.
"""

from dataclasses import dataclass, replace
from pathlib import Path
import re
import sys
import tempfile

import daggerml as d
from daggerml import exchange as ex, transfer
import implementation_selection as policy
import reuse_selection as selection

TABLE_ROLE = "example-multi-input-table-v1"
ENTRIES_ROLE = "example-multi-input-entries-v1"
ENTRY_ROLE = "example-multi-input-entry-v1"
DECISION_ROLE = "example-multi-input-decision-v1"
MAX_ENTRIES = 16


@dataclass(frozen=True)
class Entry:
    key: str
    dag: d.ObjectId
    inputs: d.ObjectId
    selected: selection.Selection


@dataclass(frozen=True)
class Table:
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    intent_uri: str
    binding: d.ObjectId
    entries: tuple


@dataclass(frozen=True)
class Decision:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    definition: policy.IntentDefinition
    implementation: policy.Implementation
    inputs: d.ObjectId
    inputs_name: str
    table_name: str
    implementation_override: str
    implementation_reason: str
    override: str
    action: str
    reason: str
    table: object
    entry: object

    @property
    def selected(self):
        return None if self.entry is None else self.entry.selected

    @property
    def binding(self):
        return self.implementation.binding

    @property
    def binding_name(self):
        return self.implementation.binding_name


@dataclass(frozen=True)
class PolicyRequest:
    decision: Decision
    recorded: ex.RecordedRequest
    reused: object


def _name(value):
    if (
        type(value) is not str
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None
    ):
        raise ValueError("explicit name outside native profile")
    return value


def _map(value):
    if (
        type(value) is not int
        or value < 0
        or value > sys.maxsize
        or 0 < value < 1048576
    ):
        raise ValueError("map_size outside unchanged profile")


def _tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def _scalar(tx, node, kind):
    got = tx.get_node(node)
    if not isinstance(got, d.LiteralNode):
        raise ValueError("table field must be literal")
    datum = tx.get_datum(got.datum)
    if datum.kind != kind:
        raise ValueError("table scalar type differs")
    return datum.value


def _link(tx, node):
    got = tx.get_node(node)
    if not isinstance(got, d.SubDAGNode):
        raise ValueError("table field must be sub-DAG")
    tx.get_dag(got.dag)
    return got.dag


def _shape(tx, dag, names, root, role):
    got = tx.get_dag(dag)
    fields = got.bindings
    if set(fields) != set(names) or got.root != fields[root]:
        raise ValueError("table record shape/root differs")
    if _scalar(tx, fields["role"], "string") != role:
        raise ValueError("table record role differs")
    return fields


def _literals(tx, values):
    return {name: tx.put_literal(tx.put_datum(value)) for name, value in values.items()}


def input_key(inputs):
    if type(inputs) is not d.ObjectId:
        raise TypeError("full input ObjectId required")
    return "input-" + str(inputs)


def _distinct(*names):
    for name in names:
        _name(name)
    if len(set(names)) != len(names):
        raise ValueError("table/selection/binding/input/decision names must differ")


def inspect_table(repository_path, *, commit, table_name):
    """Strict ALL-entry public successful-S validation, including nonmatching rows."""
    _name(table_name)
    with d.Repository(repository_path) as repo, repo.read() as tx:
        tree = _tree(tx, commit)
        dag = tree[table_name]
        fields = _shape(
            tx, dag, ("role", "intent", "binding", "entries"), "binding", TABLE_ROLE
        )
        uri = _scalar(tx, fields["intent"], "uri")
        binding = _link(tx, fields["binding"])
        entries = tx.get_dag(_link(tx, fields["entries"]))
        rows = entries.bindings
        if (
            "role" not in rows
            or entries.root != rows["role"]
            or len(rows) > MAX_ENTRIES + 1
        ):
            raise ValueError("bounded entries shape/root/cap differs")
        if _scalar(tx, rows["role"], "string") != ENTRIES_ROLE:
            raise ValueError("entries role differs")
        captured = []
        for key in sorted(set(rows) - {"role"}):
            entry = _link(tx, rows[key])
            values = _shape(
                tx,
                entry,
                ("role", "inputs", "selection", "selection-slot"),
                "selection",
                ENTRY_ROLE,
            )
            inputs, selected = (_link(tx, values[n]) for n in ("inputs", "selection"))
            slot = _scalar(tx, values["selection-slot"], "string")
            _distinct(table_name, slot)
            if key != input_key(inputs) or tree[slot] != selected:
                raise ValueError("entry key/current selection slot differs")
            captured.append((key, entry, inputs, selected, slot))
        if len({row[4] for row in captured}) != len(captured):
            raise ValueError("entry selection slots must be unique")
    transfer.export_commit(repository_path, commit=commit)
    validated = []
    for key, entry, inputs, selected, slot in captured:
        got = selection.inspect(repository_path, commit=commit, slot=slot)
        if (got.dag, got.intent_uri, got.binding, got.inputs) != (
            selected,
            uri,
            binding,
            inputs,
        ):
            raise ValueError("entry differs from PUBLIC successful selection")
        validated.append(Entry(key, entry, inputs, got))
    return Table(commit, dag, table_name, uri, binding, tuple(validated))


def _publish(repository_path, *, commit, table_name, uri, binding, rows, ref, map_size):
    # All projections closed before authoring. Build response BEFORE batch commit.
    with d.Repository(repository_path, map_size=map_size) as repo, repo.write() as tx:
        entries = _tree(tx, commit)
        fields = _literals(tx, {"role": ENTRIES_ROLE})
        authored_rows = []
        for row in rows:
            values = _literals(
                tx, {"role": ENTRY_ROLE, "selection-slot": row.selected.slot}
            )
            values.update(
                inputs=tx.put_subdag(row.inputs),
                selection=tx.put_subdag(row.selected.dag),
            )
            dag = tx.put_dag(root=values["selection"], bindings=values)
            fields[row.key] = tx.put_subdag(dag)
            authored_rows.append(replace(row, dag=dag))
        row_dag = tx.put_dag(root=fields["role"], bindings=fields)
        fields = _literals(tx, {"role": TABLE_ROLE, "intent": d.Datum.uri(uri)})
        fields.update(binding=tx.put_subdag(binding), entries=tx.put_subdag(row_dag))
        dag = tx.put_dag(root=fields["binding"], bindings=fields)
        entries[table_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = Table(
            authored,
            dag,
            table_name,
            uri,
            binding,
            tuple(
                replace(row, selected=replace(row.selected, commit=authored))
                for row in authored_rows
            ),
        )
    return response


def define_table(
    repository_path, *, commit, table_name, intent_uri, binding_name, ref, map_size=0
):
    _distinct(table_name, binding_name)
    _name(ref)
    _map(map_size)
    if type(intent_uri) is not str or d.canonicalize_uri(intent_uri) != intent_uri:
        raise ValueError("intent URI must be canonical")
    transfer.export_commit(repository_path, commit=commit)
    with d.Repository(repository_path) as repo, repo.read() as tx:
        entries = _tree(tx, commit)
        if table_name in entries:
            raise ValueError("table slot must be absent for define")
        binding = entries[binding_name]
    return _publish(
        repository_path,
        commit=commit,
        table_name=table_name,
        uri=intent_uri,
        binding=binding,
        rows=(),
        ref=ref,
        map_size=map_size,
    )


def _update(
    repository_path, *, commit, table_name, selection_slot, ref, adopting, map_size
):
    _distinct(table_name, selection_slot)
    _name(ref)
    _map(map_size)
    previous = inspect_table(repository_path, commit=commit, table_name=table_name)
    chosen = selection.inspect(repository_path, commit=commit, slot=selection_slot)
    if (previous.intent_uri, previous.binding) != (chosen.intent_uri, chosen.binding):
        raise ValueError("table scope differs from selection")
    key = input_key(chosen.inputs)
    old = next((row for row in previous.entries if row.key == key), None)
    if adopting:
        if old is None:
            raise ValueError("adoption requires matching old entry")
        if old.selected.attempt_id == chosen.attempt_id:
            raise ValueError("adoption requires distinct attempt occurrence")
    elif old is not None or len(previous.entries) >= MAX_ENTRIES:
        raise ValueError("insertion requires absent key and available capacity")
    rows = tuple(row for row in previous.entries if row.key != key) + (
        Entry(key, chosen.dag, chosen.inputs, chosen),
    )
    return _publish(
        repository_path,
        commit=commit,
        table_name=table_name,
        uri=previous.intent_uri,
        binding=previous.binding,
        rows=tuple(sorted(rows, key=lambda r: r.key)),
        ref=ref,
        map_size=map_size,
    )


def select_entry(
    repository_path, *, commit, table_name, selection_slot, ref, map_size=0
):
    """Insert ONE absent exact-input key; no S capture, Q, T or dispatch."""
    return _update(
        repository_path,
        commit=commit,
        table_name=table_name,
        selection_slot=selection_slot,
        ref=ref,
        adopting=False,
        map_size=map_size,
    )


def adopt_entry(
    repository_path, *, commit, table_name, selection_slot, ref, map_size=0
):
    """Replace ONE row with a distinct successful occurrence in a NEW S slot."""
    return _update(
        repository_path,
        commit=commit,
        table_name=table_name,
        selection_slot=selection_slot,
        ref=ref,
        adopting=True,
        map_size=map_size,
    )


def _prepare(path, commit, binding_name, inputs_name, intent_uri, request=None):
    with tempfile.TemporaryDirectory(prefix="dml-table-validation-") as scratch:
        got = ex.prepare_exchange(
            path,
            commit=commit,
            request=request,
            binding_name=binding_name,
            inputs_name=inputs_name,
            intent_uri=intent_uri,
            worker_ref="table-validation",
            workspace=Path(scratch) / "input",
        )
    return got


def _resolve(
    path,
    commit,
    intent_name,
    inputs_name,
    table_name,
    implementation_override,
    override,
    decision_name,
):
    definition = policy.inspect_definition(path, commit=commit, intent_name=intent_name)
    labels = tuple(c.label for c in definition.implementations)
    if type(implementation_override) is not str or implementation_override not in (
        "default",
        *labels,
    ):
        raise ValueError("unknown implementation override")
    if type(override) is not str or override not in policy.OVERRIDES:
        raise ValueError("unknown reuse override")
    _distinct(
        intent_name,
        inputs_name,
        table_name,
        decision_name,
        *(c.binding_name for c in definition.implementations),
        *(c.selection_slot for c in definition.implementations),
    )
    if decision_name.startswith(
        ("request-q-", "attempt-a-", "publication-a-", "reuse-q-")
    ):
        raise ValueError("decision name collides with occurrence names")
    label = (
        definition.default_implementation
        if implementation_override == "default"
        else implementation_override
    )
    choice = next(c for c in definition.implementations if c.label == label)
    spec = _prepare(
        path, commit, choice.binding_name, inputs_name, definition.intent_uri
    )
    table = entry = None
    if override == "fresh":
        action, reason = "execute-fresh", "override-fresh"
    elif override == "default" and definition.default == "execute-by-default":
        action, reason = "execute-fresh", "default-execution"
    else:
        with d.Repository(path) as repo, repo.read() as tx:
            present = table_name in _tree(tx, commit)
        if present:
            table = inspect_table(path, commit=commit, table_name=table_name)
            if (table.intent_uri, table.binding) != (
                definition.intent_uri,
                choice.binding,
            ):
                raise ValueError("table intent/full binding scope differs")
            for row in table.entries:
                _distinct(
                    intent_name,
                    inputs_name,
                    table_name,
                    decision_name,
                    row.selected.slot,
                    *(c.binding_name for c in definition.implementations),
                    *(c.selection_slot for c in definition.implementations),
                )
            entry = next(
                (row for row in table.entries if row.inputs == spec.inputs), None
            )
        if entry is None:
            if override == "reuse-selected":
                raise ValueError(
                    "explicit selected reuse requires matching table entry"
                )
            action, reason = "execute-fresh", (
                "default-no-table" if table is None else "default-no-entry"
            )
        else:
            action, reason = "reuse-selected", (
                "default-entry" if override == "default" else "override-selected-reuse"
            )
    return definition, choice, spec, table, entry, action, reason


def _decision_fields(tx, definition, choice, spec, table, entry, values):
    fields = _literals(tx, {"role": DECISION_ROLE, **values})
    links = {
        "intent-definition": definition.dag,
        "implementation-choice": choice.dag,
        "binding": spec.binding,
        "inputs": spec.inputs,
    }
    if table is not None:
        links["table"] = table.dag
    if entry is not None:
        links.update(entry=entry.dag, selection=entry.selected.dag)
    fields.update({name: tx.put_subdag(dag) for name, dag in links.items()})
    return fields


SCALARS = (
    "intent-name",
    "binding-name",
    "inputs-name",
    "table-name",
    "implementation",
    "implementation-override",
    "implementation-reason",
    "override",
    "action",
    "reason",
)
LINKS = ("intent-definition", "implementation-choice", "binding", "inputs")


def _claims(
    definition,
    choice,
    inputs_name,
    table_name,
    implementation_override,
    override,
    action,
    reason,
):
    return dict(
        zip(
            SCALARS,
            (
                definition.name,
                choice.binding_name,
                inputs_name,
                table_name,
                choice.label,
                implementation_override,
                (
                    "default-implementation"
                    if implementation_override == "default"
                    else "explicit-implementation"
                ),
                override,
                action,
                reason,
            ),
        )
    )


def _response(
    base,
    commit,
    dag,
    name,
    resolved,
    inputs_name,
    table_name,
    implementation_override,
    override,
):
    definition, choice, spec, table, entry, action, reason = resolved
    return Decision(
        base,
        commit,
        dag,
        name,
        definition,
        choice,
        spec.inputs,
        inputs_name,
        table_name,
        implementation_override,
        (
            "default-implementation"
            if implementation_override == "default"
            else "explicit-implementation"
        ),
        override,
        action,
        reason,
        table,
        entry,
    )


def record_policy_request(
    repository_path,
    *,
    commit,
    intent_name,
    inputs_name,
    table_name,
    decision_name,
    implementation_override="default",
    override="default",
    decision_ref,
    submission_ref,
    reuse_ref=None,
    map_size=0,
):
    for name in (decision_name, decision_ref, submission_ref):
        _name(name)
    _map(map_size)
    if reuse_ref is not None:
        _name(reuse_ref)
    if len({decision_ref, submission_ref, reuse_ref}) != 3:
        raise ValueError("publication refs must differ")
    resolved = _resolve(
        repository_path,
        commit,
        intent_name,
        inputs_name,
        table_name,
        implementation_override,
        override,
        decision_name,
    )
    definition, choice, spec, table, entry, action, reason = resolved
    if (reuse_ref is not None) != (entry is not None):
        raise ValueError("reuse ref required ONLY for selected reuse")
    with d.Repository(repository_path, map_size=map_size) as repo, repo.write() as tx:
        entries = _tree(tx, commit)
        if decision_name in entries:
            raise ValueError("decision tree name already exists")
        fields = _decision_fields(
            tx,
            definition,
            choice,
            spec,
            table,
            entry,
            _claims(
                definition,
                choice,
                inputs_name,
                table_name,
                implementation_override,
                override,
                action,
                reason,
            ),
        )
        dag = tx.put_dag(root=fields["intent-definition"], bindings=fields)
        entries[decision_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(decision_ref, authored)
        decision = _response(
            commit,
            authored,
            dag,
            decision_name,
            resolved,
            inputs_name,
            table_name,
            implementation_override,
            override,
        )
    reused = None
    if entry is None:
        recorded = ex.record_exchange_request(
            repository_path,
            commit=authored,
            binding_name=choice.binding_name,
            inputs_name=inputs_name,
            intent_uri=definition.intent_uri,
            ref=submission_ref,
            map_size=map_size,
        )
    else:
        reused = selection.reuse_selected(
            repository_path,
            commit=authored,
            slot=entry.selected.slot,
            binding_name=choice.binding_name,
            inputs_name=inputs_name,
            intent_uri=definition.intent_uri,
            submission_ref=submission_ref,
            ref=reuse_ref,
            map_size=map_size,
        )
        recorded = reused.recorded
        if (reused.attempt, reused.result) != (
            entry.selected.attempt,
            entry.selected.result,
        ):
            raise ValueError("actual owning reused selection differs from decision")
    if (recorded.base, recorded.intent_uri, recorded.binding, recorded.inputs) != (
        authored,
        definition.intent_uri,
        spec.binding,
        spec.inputs,
    ):
        raise ValueError("actual owning Q differs from validated decision")
    inspect_request(
        repository_path,
        commit=recorded.commit,
        request=recorded.request,
        decision_name=decision_name,
        satisfaction_commit=None if reused is None else reused.commit,
    )
    with d.Repository(repository_path) as repo, repo.read() as tx:
        if (
            recorded.ref != submission_ref
            or recorded.binding_name != choice.binding_name
            or recorded.inputs_name != inputs_name
            or tx.get_ref(submission_ref) != recorded.commit
            or tx.get_ref("request-" + recorded.request_id) != recorded.commit
            or _tree(tx, recorded.commit).get("request-" + recorded.request_id)
            != recorded.request
        ):
            raise ValueError("actual owning submission differs from response")
        if reused is not None and (
            tx.get_ref(reuse_ref) != reused.commit
            or _tree(tx, reused.commit).get("reuse-" + recorded.request_id)
            != reused.dag
        ):
            raise ValueError("actual owning satisfaction differs from response")
    return PolicyRequest(decision, recorded, reused)


def inspect_decision(repository_path, *, commit, decision_name):
    _name(decision_name)
    with d.Repository(repository_path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("decision commit requires exact one parent")
        base = parents[0]
        entries, old = _tree(tx, commit), _tree(tx, base)
        dag = entries.pop(decision_name)
        if decision_name in old or entries != old:
            raise ValueError("decision commit must add ONLY named Dm")
        got = tx.get_dag(dag)
        fields = got.bindings
        required = {"role", *SCALARS, *LINKS}
        if (
            set(fields)
            not in (
                required,
                required | {"table"},
                required | {"table", "entry", "selection"},
            )
            or got.root != fields["intent-definition"]
        ):
            raise ValueError("decision shape/root differs")
        if _scalar(tx, fields["role"], "string") != DECISION_ROLE:
            raise ValueError("decision role differs")
        values = {name: _scalar(tx, fields[name], "string") for name in SCALARS}
        links = {
            name: _link(tx, fields[name]) for name in set(fields) - {"role", *SCALARS}
        }
    resolved = _resolve(
        repository_path,
        base,
        values["intent-name"],
        values["inputs-name"],
        values["table-name"],
        values["implementation-override"],
        values["override"],
        decision_name,
    )
    definition, choice, spec, table, entry, action, reason = resolved
    expected = dict(zip(LINKS, (definition.dag, choice.dag, spec.binding, spec.inputs)))
    if table is not None:
        expected["table"] = table.dag
    if entry is not None:
        expected.update(entry=entry.dag, selection=entry.selected.dag)
    if links != expected or values != _claims(
        definition,
        choice,
        values["inputs-name"],
        values["table-name"],
        values["implementation-override"],
        values["override"],
        action,
        reason,
    ):
        raise ValueError("decision claims differ from pinned parent authority")
    transfer.export_commit(repository_path, commit=commit)
    return _response(
        base,
        commit,
        dag,
        decision_name,
        resolved,
        values["inputs-name"],
        values["table-name"],
        values["implementation-override"],
        values["override"],
    )


def inspect_request(
    repository_path, *, commit, request, decision_name, satisfaction_commit=None
):
    if type(request) is not d.ObjectId:
        raise TypeError("submitted request requires exact ObjectId, never None")
    with d.Repository(repository_path) as repo, repo.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("submission requires exact one decision parent")
        cdec = parents[0]
    decision = inspect_decision(
        repository_path, commit=cdec, decision_name=decision_name
    )
    _prepare(
        repository_path,
        commit,
        decision.binding_name,
        decision.inputs_name,
        decision.definition.intent_uri,
        request=request,
    )
    if satisfaction_commit is not None:
        if decision.selected is None:
            raise ValueError("fresh decision cannot claim reuse W")
        with d.Repository(repository_path) as repo, repo.read() as tx:
            basis = _tree(tx, commit)
            qname = (set(basis) - set(_tree(tx, cdec))).pop()
            entries = _tree(tx, satisfaction_commit)
            dag = entries.pop("reuse-" + qname[len("request-") :], None)
            if (
                dag is None
                or tx.get_commit(satisfaction_commit).parents != (commit,)
                or entries != basis
            ):
                raise ValueError("satisfaction must add ONLY W on exact Q submission")
            fields = _shape(
                tx,
                dag,
                ("role", "request", "attempt", "result"),
                "result",
                "example-explicit-reuse-v1",
            )
            if tuple(
                _link(tx, fields[n]) for n in ("request", "attempt", "result")
            ) != (request, decision.selected.attempt, decision.selected.result):
                raise ValueError("reuse association differs from decision/own Q")
        transfer.export_commit(repository_path, commit=satisfaction_commit)
    return decision
