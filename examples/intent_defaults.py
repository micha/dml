"""Example-local intent defaults/overrides; records and reads, NEVER dispatches.

Ordinary Idef/D, unchanged PUBLIC preparation/Q/S-V/Q-W authority. Close other
native handles first. D/Q/W/files/service are separate publication boundaries.
"""

import argparse
from dataclasses import dataclass
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


@dataclass(frozen=True)
class IntentDefinition:
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    intent_uri: str
    default: str


@dataclass(frozen=True)
class Decision:
    base: d.ObjectId
    commit: d.ObjectId
    dag: d.ObjectId
    name: str
    definition: IntentDefinition
    binding: d.ObjectId
    inputs: d.ObjectId
    binding_name: str
    inputs_name: str
    selection_slot: str
    override: str
    action: str
    reason: str
    selected: object


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


def _decision_name(value, names):
    _name(value)
    if value in names or value.startswith(
        ("request-q-", "attempt-a-", "publication-a-", "reuse-q-")
    ):
        raise ValueError("decision name collides with selected or occurrence names")


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
        raise ValueError("policy field must be literal")
    datum = tx.get_datum(value.datum)
    if datum.kind != kind:
        raise ValueError("policy scalar type differs")
    return datum.value


def _link(tx, node):
    value = tx.get_node(node)
    if not isinstance(value, d.SubDAGNode):
        raise ValueError("policy field must be sub-DAG")
    tx.get_dag(value.dag)
    return value.dag


def _definition(tx, commit, name):
    dag = _tree(tx, commit)[name]
    description = tx.get_dag(dag)
    fields = description.bindings
    if (
        set(fields) != {"role", "intent", "default"}
        or description.root != fields["intent"]
    ):
        raise ValueError("intent definition shape/root differs")
    if _scalar(tx, fields["role"], "string") != "example-intent-default-v1":
        raise ValueError("intent definition role differs")
    uri = _scalar(tx, fields["intent"], "uri")
    mode = _enum(_scalar(tx, fields["default"], "string"), MODES, "intent default")
    return IntentDefinition(commit, dag, name, uri, mode)


def inspect_definition(repository_path, *, commit, intent_name):
    _name(intent_name)
    with d.Repository(repository_path) as repository, repository.read() as tx:
        response = _definition(tx, commit, intent_name)
    transfer.export_commit(repository_path, commit=commit)
    return response


def define(
    repository_path,
    *,
    commit,
    intent_name,
    intent_uri,
    default,
    ref,
    update=False,
    map_size=0,
):
    """One Idef/tree/commit/create-only ref batch, response BEFORE storage commit."""
    _name(intent_name)
    _name(ref)
    _enum(default, MODES, "intent default")
    _map(map_size)
    if type(update) is not bool:
        raise TypeError("update requires bool")
    if type(intent_uri) is not str or d.canonicalize_uri(intent_uri) != intent_uri:
        raise ValueError("intent URI must be canonical")
    transfer.export_commit(repository_path, commit=commit)
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        entries = _tree(tx, commit)
        if (intent_name in entries) != update:
            raise ValueError(
                "intent slot must be absent for define, present for update"
            )
        if update and _definition(tx, commit, intent_name).intent_uri != intent_uri:
            raise ValueError("intent update cannot change stable URI")
        fields = {
            name: tx.put_literal(tx.put_datum(value))
            for name, value in {
                "role": "example-intent-default-v1",
                "intent": d.Datum.uri(intent_uri),
                "default": default,
            }.items()
        }
        dag = tx.put_dag(root=fields["intent"], bindings=fields)
        entries[intent_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = IntentDefinition(authored, dag, intent_name, intent_uri, default)
    return response


def _prepare(
    repository_path, commit, binding_name, inputs_name, intent_uri, request=None
):
    # PUBLIC consumed binding/input/ALL-history and optional normative submission/Q
    # authority. Workspace/token are disposable transport, NEVER execution state.
    with tempfile.TemporaryDirectory(prefix="dml-policy-validation-") as scratch:
        response = ex.prepare_exchange(
            repository_path,
            commit=commit,
            request=request,
            binding_name=binding_name,
            inputs_name=inputs_name,
            intent_uri=intent_uri,
            worker_ref="policy-validation",
            workspace=Path(scratch) / "input",
        )
    return response


def _resolve(
    repository_path, commit, intent_name, binding_name, inputs_name, slot, override
):
    _enum(override, OVERRIDES, "request override")
    for name in (intent_name, binding_name, inputs_name, slot):
        _name(name)
    if len({intent_name, binding_name, inputs_name, slot}) != 4:
        raise ValueError("policy tree names must be distinct")
    with d.Repository(repository_path) as repository, repository.read() as tx:
        definition = _definition(tx, commit, intent_name)
        present = slot in _tree(tx, commit)  # ONLY entry absence is a miss.
    spec = _prepare(
        repository_path, commit, binding_name, inputs_name, definition.intent_uri
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
        # No catch-to-execute. Unused S framing is deliberately not inspected above.
        selected = selection.inspect(repository_path, commit=commit, slot=slot)
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
    return definition, spec, selected, action, reason


def record_policy_request(
    repository_path,
    *,
    commit,
    intent_name,
    binding_name,
    inputs_name,
    selection_slot,
    decision_name,
    override="default",
    decision_ref,
    submission_ref,
    reuse_ref=None,
    map_size=0,
):
    """Validate/dispose first; separate D, own Q, optional existing W. No launch."""
    _name(decision_name)
    for ref in (decision_ref, submission_ref):
        _name(ref)
    _map(map_size)
    if reuse_ref is not None:
        _name(reuse_ref)
    if len({decision_ref, submission_ref, reuse_ref}) != 3:
        raise ValueError("publication refs must differ")
    _decision_name(
        decision_name, {intent_name, binding_name, inputs_name, selection_slot}
    )
    definition, spec, selected, action, reason = _resolve(
        repository_path,
        commit,
        intent_name,
        binding_name,
        inputs_name,
        selection_slot,
        override,
    )
    if (reuse_ref is not None) != (selected is not None):
        raise ValueError("reuse ref required ONLY for selected reuse")
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        entries = _tree(tx, commit)
        if decision_name in entries:
            raise ValueError("decision tree name already exists")
        fields = {
            name: tx.put_literal(tx.put_datum(value))
            for name, value in {
                "role": "example-request-policy-decision-v1",
                "intent-name": intent_name,
                "binding-name": binding_name,
                "inputs-name": inputs_name,
                "selection-slot": selection_slot,
                "override": override,
                "action": action,
                "reason": reason,
            }.items()
        }
        fields.update(
            {
                name: tx.put_subdag(value)
                for name, value in {
                    "intent-definition": definition.dag,
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
            spec.binding,
            spec.inputs,
            binding_name,
            inputs_name,
            selection_slot,
            override,
            action,
            reason,
            selected,
        )
    if selected is None:
        recorded = ex.record_exchange_request(
            repository_path,
            commit=authored,
            binding_name=binding_name,
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
            slot=selection_slot,
            binding_name=binding_name,
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
    return PolicyRequest(decision, recorded, reused)


def inspect_decision(repository_path, *, commit, decision_name):
    """Recompute from exact Cdec parent, NEVER latest policy/selection ref."""
    _name(decision_name)
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
        required = {
            "role",
            "intent-definition",
            "binding",
            "inputs",
            "intent-name",
            "binding-name",
            "inputs-name",
            "selection-slot",
            "override",
            "action",
            "reason",
        }
        if (
            set(fields) not in (required, required | {"selection"})
            or description.root != fields["intent-definition"]
        ):
            raise ValueError("decision shape/root differs")
        if (
            _scalar(tx, fields["role"], "string")
            != "example-request-policy-decision-v1"
        ):
            raise ValueError("decision role differs")
        values = {
            name: _scalar(tx, fields[name], "string")
            for name in (
                "intent-name",
                "binding-name",
                "inputs-name",
                "selection-slot",
                "override",
                "action",
                "reason",
            )
        }
        links = {
            name: _link(tx, fields[name])
            for name in ("intent-definition", "binding", "inputs")
        }
        choice = _link(tx, fields["selection"]) if "selection" in fields else None
    _decision_name(
        decision_name,
        {
            values[n]
            for n in ("intent-name", "binding-name", "inputs-name", "selection-slot")
        },
    )
    definition, spec, selected, action, reason = _resolve(
        repository_path,
        base,
        values["intent-name"],
        values["binding-name"],
        values["inputs-name"],
        values["selection-slot"],
        values["override"],
    )
    if (
        links["intent-definition"],
        links["binding"],
        links["inputs"],
        choice,
        values["action"],
        values["reason"],
    ) != (
        definition.dag,
        spec.binding,
        spec.inputs,
        None if selected is None else selected.dag,
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
        spec.binding,
        spec.inputs,
        values["binding-name"],
        values["inputs-name"],
        values["selection-slot"],
        values["override"],
        action,
        reason,
        selected,
    )


def inspect_request(
    repository_path, *, commit, request, decision_name, satisfaction_commit=None
):
    """PUBLIC exact Q validation; optionally check unchanged four-field W spine."""
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
            qname = added.pop()  # PUBLIC preparation already validates exactly one Q.
            entries = _tree(tx, satisfaction_commit)
            dag = entries.pop("reuse-" + qname[len("request-") :], None)
            if (
                dag is None
                or tx.get_commit(satisfaction_commit).parents != (commit,)
                or entries != basis
            ):
                raise ValueError("satisfaction must add ONLY W on exact Q submission")
            description = tx.get_dag(dag)
            fields = description.bindings
            if (
                set(fields) != {"role", "request", "attempt", "result"}
                or description.root != fields["result"]
            ):
                raise ValueError("reuse association shape/root differs")
            if _scalar(
                tx, fields["role"], "string"
            ) != "example-explicit-reuse-v1" or tuple(
                _link(tx, fields[n]) for n in ("request", "attempt", "result")
            ) != (
                request,
                decision.selected.attempt,
                decision.selected.result,
            ):
                raise ValueError("reuse association differs from decision/own Q")
        transfer.export_commit(repository_path, commit=satisfaction_commit)
    return decision


def _decision_report(got):
    return dict(
        decision_commit=str(got.commit),
        decision=str(got.dag),
        decision_name=got.name,
        base=str(got.base),
        definition=str(got.definition.dag),
        default=got.definition.default,
        intent=got.definition.intent_uri,
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
    """One finite offline action. Fresh dispatch stays in a SEPARATE application."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in (
        "define",
        "inspect-definition",
        "request",
        "inspect-decision",
        "inspect-request",
    ):
        command = commands.add_parser(mode)
        command.add_argument("repository")
        command.add_argument("commit", type=d.ObjectId.from_hex)
        if mode in ("define", "inspect-definition", "request"):
            command.add_argument("intent_name")
        if mode == "define":
            for name in ("intent_uri", "default", "ref"):
                command.add_argument(name)
            command.add_argument("--update", action="store_true")
        elif mode == "request":
            for name in (
                "binding_name",
                "inputs_name",
                "selection_slot",
                "decision_name",
                "override",
                "decision_ref",
                "submission_ref",
            ):
                command.add_argument(name)
            command.add_argument("--reuse-ref")
        elif mode in ("inspect-decision", "inspect-request"):
            if mode == "inspect-request":
                # REQUIRED exact Q: never silently select fresh-Q-in-B mode.
                command.add_argument("request", type=d.ObjectId.from_hex)
                command.add_argument("--satisfaction-commit", type=d.ObjectId.from_hex)
            command.add_argument("decision_name")
    arguments = vars(parser.parse_args(argv))
    mode, repository = arguments.pop("mode"), arguments.pop("repository")
    if mode in ("define", "inspect-definition"):
        got = (define if mode == "define" else inspect_definition)(
            repository, **arguments
        )
        report = dict(
            commit=str(got.commit),
            definition=str(got.dag),
            name=got.name,
            intent=got.intent_uri,
            default=got.default,
        )
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
