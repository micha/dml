"""Example-local advisory supersession, preserving exact older policy records.

PUBLIC definition/request inspection and native all-parent transfer authority only.
Reads never dispatch; L publication and default promotion are separate batches.
Close other native handles before calling. Evidence records a claim, not certification.
"""

from dataclasses import dataclass
import re
import sys

import daggerml as d
import implementation_selection as policy

ROLE = "example-implementation-supersession-v1"
REASONS = ("correctness-fix", "operational-replacement")
FIELDS = (
    "role",
    "basis",
    "intent-name",
    "intent-definition",
    "predecessor-label",
    "successor-label",
    "predecessor",
    "successor",
    "reason",
    "evidence",
)


@dataclass(frozen=True)
class Supersession:
    commit: d.ObjectId
    dag: d.ObjectId
    slot: str
    basis: d.ObjectId
    definition: policy.IntentDefinition
    predecessor: policy.Implementation
    successor: policy.Implementation
    reason: str
    evidence: d.ObjectId


@dataclass(frozen=True)
class KnowledgeView:
    commit: d.ObjectId
    relation: str
    declaration: object


@dataclass(frozen=True)
class RequestContext:
    decision: policy.Decision
    as_known_then: KnowledgeView
    explicit_knowledge: object


def _name(value):
    if (
        type(value) is not str
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None
    ):
        raise ValueError("explicit name outside native profile")
    return value


def _tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def _scalar(tx, node, kind):
    value = tx.get_node(node)
    if not isinstance(value, d.LiteralNode):
        raise ValueError("supersession field must be literal")
    datum = tx.get_datum(value.datum)
    if datum.kind != kind:
        raise ValueError("supersession scalar type differs")
    return datum.value


def _link(tx, node):
    value = tx.get_node(node)
    if not isinstance(value, d.SubDAGNode):
        raise ValueError("supersession field must be sub-DAG")
    tx.get_dag(value.dag)
    return value.dag


def _compatible(captured, current):
    if (
        captured.name,
        captured.intent_uri,
        captured.menu,
        captured.implementations,
    ) != (current.name, current.intent_uri, current.menu, current.implementations):
        raise ValueError("supersession intent/captured menu drift")


def _endpoints(definition, predecessor_label, successor_label):
    for label in (predecessor_label, successor_label):
        _name(label)
    members = {c.label: c for c in definition.implementations}
    if predecessor_label not in members or successor_label not in members:
        raise ValueError("supersession endpoint outside captured menu")
    predecessor, successor = members[predecessor_label], members[successor_label]
    if predecessor.binding == successor.binding:
        raise ValueError("supersession endpoints require distinct bindings")
    return predecessor, successor


def _reason(value):
    if type(value) is not str or value not in REASONS:
        raise ValueError("unknown supersession reason")
    return value


def _names(definition, slot, evidence_name=None):
    names = [definition.name, slot]
    names += [c.binding_name for c in definition.implementations]
    names += [c.selection_slot for c in definition.implementations]
    if evidence_name is not None:
        names.append(evidence_name)
    for name in names:
        _name(name)
    if len(set(names)) != len(names):
        raise ValueError("supersession tree names must be distinct")


def record_supersession(
    repository_path,
    *,
    commit,
    intent_name,
    slot,
    predecessor_label,
    successor_label,
    reason,
    evidence_name,
    ref,
    map_size=0,
):
    """Add ONLY absent L on (C,), create-only ref, response allocated precommit.

    No Q/T/job/default/selection change. Validation handles close BEFORE authoring.
    """
    _name(ref)
    if (
        type(map_size) is not int
        or map_size < 0
        or map_size > sys.maxsize
        or 0 < map_size < 1048576
    ):
        raise ValueError("map_size outside unchanged profile")
    _reason(reason)
    definition = policy.inspect_definition(
        repository_path, commit=commit, intent_name=intent_name
    )
    _names(definition, slot, evidence_name)
    predecessor, successor = _endpoints(definition, predecessor_label, successor_label)
    with d.Repository(repository_path) as repository, repository.read() as tx:
        entries = _tree(tx, commit)
        if slot in entries:
            raise ValueError("supersession slot must be absent")
        evidence = entries[evidence_name]
        tx.get_dag(evidence)
    # PUBLIC definition inspection already exports complete native closure at C.
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        fields = {
            name: tx.put_literal(tx.put_datum(value))
            for name, value in {
                "role": ROLE,
                "basis": commit.bytes,
                "intent-name": intent_name,
                "predecessor-label": predecessor_label,
                "successor-label": successor_label,
                "reason": reason,
            }.items()
        }
        fields.update(
            {
                name: tx.put_subdag(value)
                for name, value in {
                    "intent-definition": definition.dag,
                    "predecessor": predecessor.dag,
                    "successor": successor.dag,
                    "evidence": evidence,
                }.items()
            }
        )
        dag = tx.put_dag(root=fields["predecessor"], bindings=fields)
        entries[slot] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = Supersession(
            authored,
            dag,
            slot,
            commit,
            definition,
            predecessor,
            successor,
            reason,
            evidence,
        )
    return response


def inspect_supersession(repository_path, *, commit, intent_name, slot):
    """Pinned fixed-menu declaration or genuine slot absence; malformed NEVER misses.

    Basis BYTES are not native edges: require ALL-parent retention, then PUBLIC
    definition inspection at that exact basis. Default movement alone is compatible.
    """
    current = policy.inspect_definition(
        repository_path, commit=commit, intent_name=intent_name
    )
    _names(current, slot)
    with d.Repository(repository_path) as repository, repository.read() as tx:
        entries = _tree(tx, commit)
        if slot not in entries:
            return None
        dag = entries[slot]
        description = tx.get_dag(dag)
        fields = description.bindings
        if set(fields) != set(FIELDS) or description.root != fields["predecessor"]:
            raise ValueError("supersession shape/root differs")
        if _scalar(tx, fields["role"], "string") != ROLE:
            raise ValueError("supersession role differs")
        basis = d.ObjectId(_scalar(tx, fields["basis"], "bytes"))
        if _scalar(tx, fields["intent-name"], "string") != intent_name:
            raise ValueError("supersession intent name differs")
        labels = tuple(
            _scalar(tx, fields[n], "string")
            for n in ("predecessor-label", "successor-label")
        )
        reason = _reason(_scalar(tx, fields["reason"], "string"))
        links = tuple(
            _link(tx, fields[n])
            for n in ("intent-definition", "predecessor", "successor", "evidence")
        )
        pending, seen = [commit], set()
        while pending:
            selected = pending.pop()
            if selected not in seen:
                seen.add(selected)
                pending.extend(tx.get_commit(selected).parents)
        if basis not in seen:
            raise ValueError("supersession basis not retained in ALL-parent history")
    captured = policy.inspect_definition(
        repository_path, commit=basis, intent_name=intent_name
    )
    _compatible(captured, current)
    predecessor, successor = _endpoints(captured, *labels)
    if links[:3] != (captured.dag, predecessor.dag, successor.dag):
        raise ValueError("supersession captured endpoint/definition drift")
    return Supersession(
        commit, dag, slot, basis, captured, predecessor, successor, reason, links[3]
    )


def _view(repository_path, commit, decision, slot):
    declaration = inspect_supersession(
        repository_path, commit=commit, intent_name=decision.definition.name, slot=slot
    )
    # Compatible scope is required even when the selected slot is genuinely absent.
    current = policy.inspect_definition(
        repository_path, commit=commit, intent_name=decision.definition.name
    )
    _compatible(decision.definition, current)
    relation = "no-recorded-declaration"
    if declaration is not None:
        relation = (
            "predecessor"
            if decision.binding == declaration.predecessor.binding
            else "successor"
        )
    return KnowledgeView(commit, relation, declaration)


def inspect_request_context(
    repository_path,
    *,
    commit,
    request,
    decision_name,
    slot,
    satisfaction_commit=None,
    knowledge_commit=None,
):
    """Exact own-Q/W authority; actual D.base versus separately explicit immutable K.

    Available advisory state is not proof of consultation, health or global time.
    Never reads latest refs, dispatches, rewrites old records or certifies evidence.
    """
    decision = policy.inspect_request(
        repository_path,
        commit=commit,
        request=request,
        decision_name=decision_name,
        satisfaction_commit=satisfaction_commit,
    )
    historical = _view(repository_path, decision.base, decision, slot)
    explicit = (
        None
        if knowledge_commit is None
        else _view(repository_path, knowledge_commit, decision, slot)
    )
    return RequestContext(decision, historical, explicit)
