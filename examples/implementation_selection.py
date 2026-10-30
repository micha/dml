"""Example-local captured implementation menu, then independent reuse policy.

Ordinary DAGs; PUBLIC preparation/Q/S-V/Q-W only. Records/reads, NEVER dispatches.
Close other native handles first. Definition/D/Q/W/files/service are separate.
"""

import argparse
from dataclasses import dataclass, replace
import json
from pathlib import Path
import re
import sys
import tempfile

import daggerml as d
from daggerml import exchange as ex, transfer
import reuse_selection as selection

MODES = ("reuse-by-default", "execute-by-default")
OVERRIDES = ("default", "fresh", "reuse-selected")
DEFINITION_ROLE = "example-implementation-definition-v1"
MENU_ROLE = "example-implementation-menu-v1"
CHOICE_ROLE = "example-implementation-choice-v1"
DECISION_ROLE = "example-implementation-decision-v1"


@dataclass(frozen=True)
class Implementation:
    label: str
    dag: d.ObjectId
    binding: d.ObjectId
    binding_name: str
    selection_slot: str


@dataclass(frozen=True)
class IntentDefinition:
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    intent_uri: str
    default: str
    menu: d.ObjectId
    implementations: tuple
    default_implementation: str


@dataclass(frozen=True)
class Decision:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    definition: IntentDefinition
    implementation: Implementation
    implementation_override: str
    implementation_reason: str
    binding: d.ObjectId
    inputs: d.ObjectId
    inputs_name: str
    override: str
    action: str
    reason: str
    selected: object

    @property
    def binding_name(self):
        return self.implementation.binding_name

    @property
    def selection_slot(self):
        return self.implementation.selection_slot


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


def _enum(value, allowed, label):
    if type(value) is not str or value not in allowed:
        raise ValueError("unknown " + label)
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
    value = tx.get_node(node)
    if not isinstance(value, d.LiteralNode):
        raise ValueError("implementation field must be literal")
    datum = tx.get_datum(value.datum)
    if datum.kind != kind:
        raise ValueError("implementation scalar type differs")
    return datum.value


def _link(tx, node):
    value = tx.get_node(node)
    if not isinstance(value, d.SubDAGNode):
        raise ValueError("implementation field must be sub-DAG")
    tx.get_dag(value.dag)
    return value.dag


def _shape(tx, dag, names, root, role):
    description = tx.get_dag(dag)
    fields = description.bindings
    if set(fields) != set(names) or description.root != fields[root]:
        raise ValueError("implementation record shape/root differs")
    if _scalar(tx, fields["role"], "string") != role:
        raise ValueError("implementation record role differs")
    return fields


def _distinct(definition, inputs_name=None, decision_name=None):
    names = [definition.name]
    names += [choice.binding_name for choice in definition.implementations]
    names += [choice.selection_slot for choice in definition.implementations]
    if inputs_name is not None:
        names.append(inputs_name)
    if decision_name is not None:
        names.append(decision_name)
        if decision_name.startswith(
            ("request-q-", "attempt-a-", "publication-a-", "reuse-q-")
        ):
            raise ValueError("decision name collides with occurrence names")
    for name in names:
        _name(name)
    if len(set(names)) != len(names):
        raise ValueError("implementation tree names/slots must be distinct")
    if len({choice.binding for choice in definition.implementations}) != 2:
        raise ValueError("implementations require distinct captured binding IDs")


def _definition(tx, commit, name):
    entries = _tree(tx, commit)
    dag = entries[name]
    fields = _shape(
        tx,
        dag,
        (
            "role",
            "intent",
            "reuse-default",
            "implementations",
            "default-implementation",
        ),
        "intent",
        DEFINITION_ROLE,
    )
    uri = _scalar(tx, fields["intent"], "uri")
    default = _enum(
        _scalar(tx, fields["reuse-default"], "string"), MODES, "reuse default"
    )
    menu = _link(tx, fields["implementations"])
    description = tx.get_dag(menu)
    options = description.bindings
    if (
        len(options) != 3
        or "role" not in options
        or description.root != options["role"]
    ):
        raise ValueError("implementation menu shape/root differs")
    if _scalar(tx, options["role"], "string") != MENU_ROLE:
        raise ValueError("implementation menu role differs")
    implementations = []
    for label in sorted(set(options) - {"role"}):
        _name(label)
        if label == "default":
            raise ValueError("implementation label default is reserved")
        choice = _link(tx, options[label])
        values = _shape(
            tx,
            choice,
            ("role", "binding", "binding-name", "selection-slot"),
            "binding",
            CHOICE_ROLE,
        )
        implementations.append(
            Implementation(
                label,
                choice,
                _link(tx, values["binding"]),
                _scalar(tx, values["binding-name"], "string"),
                _scalar(tx, values["selection-slot"], "string"),
            )
        )
    selected = _enum(
        _scalar(tx, fields["default-implementation"], "string"),
        tuple(choice.label for choice in implementations),
        "default implementation",
    )
    response = IntentDefinition(
        commit, dag, name, uri, default, menu, tuple(implementations), selected
    )
    _distinct(response)
    # ALL declared cross-links are structural capture, not decoding unconsumed code.
    if any(
        entries[choice.binding_name] != choice.binding for choice in implementations
    ):
        raise ValueError("captured binding tree entry drift")
    return response


def inspect_definition(repository_path, *, commit, intent_name):
    _name(intent_name)
    with d.Repository(repository_path) as repository, repository.read() as tx:
        response = _definition(tx, commit, intent_name)
    transfer.export_commit(repository_path, commit=commit)
    return response


def _literals(tx, values):
    return {name: tx.put_literal(tx.put_datum(value)) for name, value in values.items()}


def _put_definition(tx, uri, default, menu, label):
    fields = _literals(
        tx,
        {
            "role": DEFINITION_ROLE,
            "intent": d.Datum.uri(uri),
            "reuse-default": default,
            "default-implementation": label,
        },
    )
    fields["implementations"] = tx.put_subdag(menu)
    return tx.put_dag(root=fields["intent"], bindings=fields)


def define(
    repository_path,
    *,
    commit,
    intent_name,
    intent_uri,
    default,
    implementations,
    default_implementation,
    ref,
    map_size=0,
):
    """Two explicit (label,binding tree name,selection slot) triples; no install/Q."""
    _name(intent_name)
    _name(ref)
    _enum(default, MODES, "reuse default")
    _map(map_size)
    if type(intent_uri) is not str or d.canonicalize_uri(intent_uri) != intent_uri:
        raise ValueError("intent URI must be canonical")
    if (
        type(implementations) is not tuple
        or len(implementations) != 2
        or any(type(row) is not tuple or len(row) != 3 for row in implementations)
    ):
        raise ValueError("two explicit implementation triples required")
    labels = tuple(row[0] for row in implementations)
    for row in implementations:
        for name in row:
            _name(name)
    if len(set(labels)) != 2 or set(labels) & {"role", "default"}:
        raise ValueError("implementation labels distinct and not reserved")
    _enum(default_implementation, labels, "default implementation")
    transfer.export_commit(repository_path, commit=commit)
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        entries = _tree(tx, commit)
        if intent_name in entries:
            raise ValueError("intent slot must be absent for define")
        choices = tuple(
            Implementation(
                label, entries[binding_name], entries[binding_name], binding_name, slot
            )
            for label, binding_name, slot in sorted(implementations)
        )
        provisional = IntentDefinition(
            commit,
            commit,
            intent_name,
            intent_uri,
            default,
            commit,
            choices,
            default_implementation,
        )
        _distinct(provisional)
        if any(choice.selection_slot in entries for choice in choices):
            raise ValueError("initial selection slots must be absent")
        captured = []
        menu_fields = _literals(tx, {"role": MENU_ROLE})
        for choice in choices:
            fields = _literals(
                tx,
                {
                    "role": CHOICE_ROLE,
                    "binding-name": choice.binding_name,
                    "selection-slot": choice.selection_slot,
                },
            )
            fields["binding"] = tx.put_subdag(choice.binding)
            dag = tx.put_dag(root=fields["binding"], bindings=fields)
            captured.append(replace(choice, dag=dag))
            menu_fields[choice.label] = tx.put_subdag(dag)
        menu = tx.put_dag(root=menu_fields["role"], bindings=menu_fields)
        dag = _put_definition(tx, intent_uri, default, menu, default_implementation)
        entries[intent_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = IntentDefinition(
            authored,
            dag,
            intent_name,
            intent_uri,
            default,
            menu,
            tuple(captured),
            default_implementation,
        )
    return response


def update_default(
    repository_path, *, commit, intent_name, default_implementation, ref, map_size=0
):
    """Replace ONLY default label; same URI/reuse policy/menu/choices/other entries."""
    _name(intent_name)
    _name(ref)
    _map(map_size)
    transfer.export_commit(repository_path, commit=commit)
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        definition = _definition(tx, commit, intent_name)
        _enum(
            default_implementation,
            tuple(c.label for c in definition.implementations),
            "default implementation",
        )
        dag = _put_definition(
            tx,
            definition.intent_uri,
            definition.default,
            definition.menu,
            default_implementation,
        )
        entries = _tree(tx, commit)
        entries[intent_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = replace(
            definition,
            commit=authored,
            dag=dag,
            default_implementation=default_implementation,
        )
    return response


def _prepare(
    repository_path, commit, binding_name, inputs_name, intent_uri, request=None
):
    # PUBLIC consumed binding/input/ALL-history/Q authority; NEVER execute projection.
    with tempfile.TemporaryDirectory(
        prefix="dml-implementation-validation-"
    ) as scratch:
        response = ex.prepare_exchange(
            repository_path,
            commit=commit,
            request=request,
            binding_name=binding_name,
            inputs_name=inputs_name,
            intent_uri=intent_uri,
            worker_ref="implementation-validation",
            workspace=Path(scratch) / "input",
        )
    return response


def _resolve(
    repository_path, commit, intent_name, inputs_name, implementation_override, override
):
    _enum(override, OVERRIDES, "reuse override")
    _name(intent_name)
    with d.Repository(repository_path) as repository, repository.read() as tx:
        definition = _definition(tx, commit, intent_name)
        _distinct(definition, inputs_name)
        labels = tuple(c.label for c in definition.implementations)
        _enum(implementation_override, ("default", *labels), "implementation override")
        label = (
            definition.default_implementation
            if implementation_override == "default"
            else implementation_override
        )
        implementation = next(c for c in definition.implementations if c.label == label)
        present = implementation.selection_slot in _tree(tx, commit)
    implementation_reason = (
        "default-implementation"
        if implementation_override == "default"
        else "explicit-implementation"
    )
    spec = _prepare(
        repository_path,
        commit,
        implementation.binding_name,
        inputs_name,
        definition.intent_uri,
    )
    selected = None
    if override == "fresh":
        action, reason = "execute-fresh", "override-fresh"
    elif override == "default" and definition.default == "execute-by-default":
        action, reason = "execute-fresh", "default-execution"
    elif not present:
        if override == "reuse-selected":
            raise ValueError("explicit selected reuse requires selection entry")
        action, reason = "execute-fresh", "default-no-selection"
    else:
        selected = selection.inspect(
            repository_path, commit=commit, slot=implementation.selection_slot
        )
        if (selected.intent_uri, selected.binding, selected.inputs) != (
            spec.intent_uri,
            spec.binding,
            spec.inputs,
        ):
            raise ValueError("selection intent/binding/full inputs differ")
        action = "reuse-selected"
        reason = (
            "default-selection" if override == "default" else "override-selected-reuse"
        )
    return (
        definition,
        implementation,
        implementation_reason,
        spec,
        selected,
        action,
        reason,
    )


def record_policy_request(
    repository_path,
    *,
    commit,
    intent_name,
    inputs_name,
    decision_name,
    implementation_override="default",
    override="default",
    decision_ref,
    submission_ref,
    reuse_ref=None,
    map_size=0,
):
    """Resolve implementation FIRST; independent reuse policy THEN D/own Q/optional W."""
    _name(decision_name)
    for ref in (decision_ref, submission_ref):
        _name(ref)
    _map(map_size)
    if reuse_ref is not None:
        _name(reuse_ref)
    if len({decision_ref, submission_ref, reuse_ref}) != 3:
        raise ValueError("publication refs must differ")
    (
        definition,
        implementation,
        implementation_reason,
        spec,
        selected,
        action,
        reason,
    ) = _resolve(
        repository_path,
        commit,
        intent_name,
        inputs_name,
        implementation_override,
        override,
    )
    _distinct(definition, inputs_name, decision_name)
    if (reuse_ref is not None) != (selected is not None):
        raise ValueError("reuse ref required ONLY for selected reuse")
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        entries = _tree(tx, commit)
        if decision_name in entries:
            raise ValueError("decision tree name already exists")
        fields = _literals(
            tx,
            {
                "role": DECISION_ROLE,
                "intent-name": intent_name,
                "binding-name": implementation.binding_name,
                "inputs-name": inputs_name,
                "selection-slot": implementation.selection_slot,
                "implementation": implementation.label,
                "implementation-override": implementation_override,
                "implementation-reason": implementation_reason,
                "override": override,
                "action": action,
                "reason": reason,
            },
        )
        fields.update(
            {
                name: tx.put_subdag(value)
                for name, value in {
                    "intent-definition": definition.dag,
                    "implementation-choice": implementation.dag,
                    "binding": spec.binding,
                    "inputs": spec.inputs,
                }.items()
            }
        )
        if selected is not None:
            fields["selection"] = tx.put_subdag(selected.dag)
        dag = tx.put_dag(root=fields["intent-definition"], bindings=fields)
        entries[decision_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(decision_ref, authored)
        decision = Decision(
            commit,
            authored,
            dag,
            decision_name,
            definition,
            implementation,
            implementation_override,
            implementation_reason,
            spec.binding,
            spec.inputs,
            inputs_name,
            override,
            action,
            reason,
            selected,
        )
    if selected is None:
        recorded = ex.record_exchange_request(
            repository_path,
            commit=authored,
            binding_name=implementation.binding_name,
            inputs_name=inputs_name,
            intent_uri=definition.intent_uri,
            ref=submission_ref,
            map_size=map_size,
        )
        reused = None
    else:
        reused = selection.reuse_selected(
            repository_path,
            commit=authored,
            slot=implementation.selection_slot,
            binding_name=implementation.binding_name,
            inputs_name=inputs_name,
            intent_uri=definition.intent_uri,
            submission_ref=submission_ref,
            ref=reuse_ref,
            map_size=map_size,
        )
        recorded = reused.recorded
        if (reused.attempt, reused.result) != (selected.attempt, selected.result):
            raise ValueError("actual owning reused selection differs from decision")
    if (recorded.base, recorded.intent_uri, recorded.binding, recorded.inputs) != (
        authored,
        definition.intent_uri,
        spec.binding,
        spec.inputs,
    ):
        raise ValueError("actual owning Q differs from validated decision")
    # Returned IDs/flags are not submission or satisfaction authority. Revalidate
    # actual pinned Q and optional W through PUBLIC preparation/our pinned reader.
    inspect_request(
        repository_path,
        commit=recorded.commit,
        request=recorded.request,
        decision_name=decision_name,
        satisfaction_commit=None if reused is None else reused.commit,
    )
    with d.Repository(repository_path) as repository, repository.read() as tx:
        if (
            recorded.ref != submission_ref
            or recorded.binding_name != implementation.binding_name
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
    """Recompute both choices from ACTUAL one parent, never latest refs/flags."""
    _name(decision_name)
    scalar_names = (
        "intent-name",
        "binding-name",
        "inputs-name",
        "selection-slot",
        "implementation",
        "implementation-override",
        "implementation-reason",
        "override",
        "action",
        "reason",
    )
    link_names = ("intent-definition", "implementation-choice", "binding", "inputs")
    with d.Repository(repository_path) as repository, repository.read() as tx:
        parents = tx.get_commit(commit).parents
        if len(parents) != 1:
            raise ValueError("decision commit requires exact one parent")
        base = parents[0]
        entries, old = _tree(tx, commit), _tree(tx, base)
        dag = entries.pop(decision_name)
        if decision_name in old or entries != old:
            raise ValueError("decision commit must add ONLY named D")
        description = tx.get_dag(dag)
        fields = description.bindings
        required = {"role", *scalar_names, *link_names}
        if (
            set(fields) not in (required, required | {"selection"})
            or description.root != fields["intent-definition"]
        ):
            raise ValueError("decision shape/root differs")
        if _scalar(tx, fields["role"], "string") != DECISION_ROLE:
            raise ValueError("decision role differs")
        values = {name: _scalar(tx, fields[name], "string") for name in scalar_names}
        links = {name: _link(tx, fields[name]) for name in link_names}
        choice = _link(tx, fields["selection"]) if "selection" in fields else None
    (
        definition,
        implementation,
        implementation_reason,
        spec,
        selected,
        action,
        reason,
    ) = _resolve(
        repository_path,
        base,
        values["intent-name"],
        values["inputs-name"],
        values["implementation-override"],
        values["override"],
    )
    _distinct(definition, values["inputs-name"], decision_name)
    if (
        tuple(links[n] for n in link_names),
        choice,
        values["binding-name"],
        values["selection-slot"],
        values["implementation"],
        values["implementation-reason"],
        values["action"],
        values["reason"],
    ) != (
        (definition.dag, implementation.dag, spec.binding, spec.inputs),
        None if selected is None else selected.dag,
        implementation.binding_name,
        implementation.selection_slot,
        implementation.label,
        implementation_reason,
        action,
        reason,
    ):
        raise ValueError("decision claims differ from pinned parent authority")
    transfer.export_commit(repository_path, commit=commit)
    return Decision(
        base,
        commit,
        dag,
        decision_name,
        definition,
        implementation,
        values["implementation-override"],
        implementation_reason,
        spec.binding,
        spec.inputs,
        values["inputs-name"],
        values["override"],
        action,
        reason,
        selected,
    )


def inspect_request(
    repository_path, *, commit, request, decision_name, satisfaction_commit=None
):
    """PUBLIC exact non-None Q authority; optional original four-field W spine."""
    if type(request) is not d.ObjectId:
        raise TypeError("submitted request requires exact ObjectId, never None")
    with d.Repository(repository_path) as repository, repository.read() as tx:
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
        with d.Repository(repository_path) as repository, repository.read() as tx:
            basis = _tree(tx, commit)
            added = set(basis) - set(_tree(tx, cdec))
            qname = added.pop()  # PUBLIC preparation checks exactly one Q.
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


def _definition_report(got):
    return dict(
        commit=str(got.commit),
        definition=str(got.dag),
        name=got.name,
        intent=got.intent_uri,
        default=got.default,
        menu=str(got.menu),
        default_implementation=got.default_implementation,
        implementations=[
            dict(
                label=c.label,
                choice=str(c.dag),
                binding=str(c.binding),
                binding_name=c.binding_name,
                selection_slot=c.selection_slot,
            )
            for c in got.implementations
        ],
    )


def _decision_report(got):
    return dict(
        decision_commit=str(got.commit),
        decision=str(got.dag),
        decision_name=got.name,
        base=str(got.base),
        definition=str(got.definition.dag),
        default=got.definition.default,
        default_implementation=got.definition.default_implementation,
        intent=got.definition.intent_uri,
        implementation=got.implementation.label,
        implementation_choice=str(got.implementation.dag),
        implementation_override=got.implementation_override,
        implementation_reason=got.implementation_reason,
        binding_name=got.binding_name,
        inputs_name=got.inputs_name,
        selection_slot=got.selection_slot,
        override=got.override,
        action=got.action,
        reason=got.reason,
        binding=str(got.binding),
        inputs=str(got.inputs),
        selection=None if got.selected is None else str(got.selected.dag),
        attempt=None if got.selected is None else str(got.selected.attempt),
        result=None if got.selected is None else str(got.selected.result),
    )


def main(argv=None):
    """One finite offline action. Dispatch stays in a SEPARATE explicit application."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in (
        "define",
        "update-default",
        "inspect-definition",
        "request",
        "inspect-decision",
        "inspect-request",
    ):
        command = commands.add_parser(mode)
        command.add_argument("repository")
        command.add_argument("commit", type=d.ObjectId.from_hex)
        if mode in ("define", "update-default", "inspect-definition", "request"):
            command.add_argument("intent_name")
        if mode == "define":
            for name in ("intent_uri", "default", "default_implementation", "ref"):
                command.add_argument(name)
            command.add_argument(
                "--implementation", nargs=3, action="append", required=True
            )
        elif mode == "update-default":
            command.add_argument("default_implementation")
            command.add_argument("ref")
        elif mode == "request":
            for name in (
                "inputs_name",
                "decision_name",
                "implementation_override",
                "override",
                "decision_ref",
                "submission_ref",
            ):
                command.add_argument(name)
            command.add_argument("--reuse-ref")
        elif mode in ("inspect-decision", "inspect-request"):
            if mode == "inspect-request":
                command.add_argument("request", type=d.ObjectId.from_hex)
                command.add_argument("--satisfaction-commit", type=d.ObjectId.from_hex)
            command.add_argument("decision_name")
    arguments = vars(parser.parse_args(argv))
    mode, repository = arguments.pop("mode"), arguments.pop("repository")
    if mode == "define":
        arguments["implementations"] = tuple(
            tuple(row) for row in arguments.pop("implementation")
        )
    if mode in ("define", "update-default", "inspect-definition"):
        got = {
            "define": define,
            "update-default": update_default,
            "inspect-definition": inspect_definition,
        }[mode](repository, **arguments)
        report = _definition_report(got)
    elif mode == "request":
        got = record_policy_request(repository, **arguments)
        report = _decision_report(got.decision)
        report.update(
            request_commit=str(got.recorded.commit),
            request=str(got.recorded.request),
            request_id=got.recorded.request_id,
            commit=str(
                got.recorded.commit if got.reused is None else got.reused.commit
            ),
            association=None if got.reused is None else str(got.reused.dag),
        )
    else:
        got = (inspect_decision if mode == "inspect-decision" else inspect_request)(
            repository, **arguments
        )
        report = _decision_report(got)
    print(json.dumps(dict(mode=mode, **report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
