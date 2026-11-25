"""Record and inspect local calls using ordinary DML objects.

Use `record REPO 7 5 3` to make both calls at once, or run
`record-sum REPO producer 7 5` and `record-scale REPO producer COMMIT result 3`
with the printed commit ID. Read either result with `inspect REPO [REF]`.
Use `export-sum` and `stage-input` to move a producer to another repository,
then `export-scale`, `stage-input`, and `publish-scale` to return the result.
Use `request-scale`, `export-request`, `work-scale`, and `publish-requested-scale`
when the source should preserve its expectations across invocations.
Use `stage-reused-scale` to stage an existing result, or `publish-reused-scale`
to publish it directly and retain a separate reuse record.
Use `work-scale-attempt` and `select-scale-attempt` to distinguish executions
of the same request without changing the result's identity. Use
`adopt-scale-attempt` to record a new version of a choice without moving it.
Use `define-scale-policy` and `request-policy-scale` to record why a request
uses an existing result or needs fresh work. Use `define-scale-intent` and
`request-intent-scale` to choose the implementation from a pinned definition
before applying that reuse policy. Use `declare-scale-supersession` to add
advisory evidence to a new intent version without promoting a default.
These layouts are not core record types or execution APIs.
"""

import argparse
from contextlib import contextmanager
import json
from operator import add, mul
from pathlib import Path
import re
from typing import NamedTuple
from uuid import uuid4

from daggerml import core


ENTRY = b"recorded-calls-v1"
SUM_ENTRY = b"recorded-sum-v1"
SCALE_ENTRY = b"recorded-scale-v1"
REQUEST_ENTRY = b"scale-request-v1"
PLAN_ENTRY = b"scale-plan-v1"
REQUESTED_SCALE_ENTRY = b"requested-scale-v1"
PUBLICATION_ENTRY = b"scale-publication-v1"
PUBLICATION_FIELDS = (b"plan_ref", b"plan_commit", b"staging_ref", b"result_commit")
REUSE_ENTRY = b"recorded-scale-reuse-v1"
SELECTION_ENTRY = b"scale-result-selection-v1"
ATTEMPT_ENTRY = b"scale-attempt-v1"
ATTEMPT_SELECTION_ENTRY = b"scale-attempt-selection-v1"
ADOPTION_ENTRY = b"scale-attempt-adoption-v1"
SELECTED_REUSE_ENTRY = b"recorded-selected-scale-reuse-v1"
POLICY_ENTRY = b"scale-intent-policy-v1"
DECISION_ENTRY = b"scale-request-decision-v1"
INTENT_ENTRY = b"scale-intent-definition-v1"
INTENT_DECISION_ENTRY = b"scale-intent-decision-v1"
INTENT_FIELDS = (b"default_implementation", b"policy_default", b"v1_selection_ref", b"v2_selection_ref")
SUPERSESSION_ENTRY = b"scale-implementation-supersession-v1"
SUPERSESSION_FIELDS = (b"predecessor", b"successor", b"reason")
REUSE_DEFAULT = b"reuse-by-default"
EXECUTE_DEFAULT = b"execute-by-default"
USE_DEFAULT = b"default"
FRESH = b"fresh"
REUSE_SELECTED = b"reuse-selected"
# The core's ASCII name profile, also used to validate historical ref-name literals.
REF_NAME = re.compile(rb"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
COMMIT_HEX = re.compile(rb"[0-9a-f]{32}")
UUID4 = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
SUM = b"example.sum@1"
SCALE_V1 = b"example.scale@1"
SCALE_V2 = b"example.scale@2"
MAIN = b"main"
MAX_BUNDLE_BYTES = 64 * 1024 * 1024  # The core's commit bundle limit.


class _ScaleRequest(NamedTuple):
    commit: bytes
    dag: bytes
    producer: bytes
    sum_dag: bytes
    implementation: bytes
    factor: int


class _ScaleAttempt(NamedTuple):
    commit: bytes
    request: _ScaleRequest
    result: bytes
    attempt_id: bytes


class _ScaleSelection(NamedTuple):
    request: _ScaleRequest
    result: bytes
    historical_ref: bytes
    attempt: _ScaleAttempt | None = None
    previous: bytes | None = None


class _ScaleIntent(NamedTuple):
    default_implementation: bytes
    policy_default: bytes
    v1_selection_ref: bytes
    v2_selection_ref: bytes


class _Supersession(NamedTuple):
    commit: bytes
    basis: bytes
    evidence: bytes
    predecessor: bytes
    successor: bytes
    reason: bytes


class _IntentVersion(NamedTuple):
    definition: _ScaleIntent
    previous: bytes | None
    genesis: bytes
    supersession: _Supersession | None


@contextmanager
def _repository(path, *, create):
    repo = core.repo_open(path, create)
    try:
        yield repo
    finally:
        core.repo_close(repo)


@contextmanager
def _read_transaction(repo):
    txn = core.txn_begin(repo, core.TXN_READ)
    try:
        yield txn
    finally:
        core.txn_abort(txn)


@contextmanager
def _write_transaction(path, *, create):
    with _repository(path, create=create) as repo:
        txn = core.txn_begin(repo, core.TXN_WRITE)
        try:
            yield txn
            core.txn_commit(txn)
        finally:
            core.txn_abort(txn)  # Safe after commit consumes the handle.


def _check_i64(value, label):
    if type(value) is not int or not -(1 << 63) <= value < (1 << 63):
        raise ValueError(f"{label} is not a signed 64-bit integer")


def _put_object(txn, kind, *fields):
    return core.txn_put_object(txn, kind, core.object_encode(kind, *fields))


def _put_literal(txn, kind, value):
    datum = core.txn_put_datum(txn, core.datum_encode(kind, value))
    return _put_object(txn, core.REC_NODE, core.NODE_LITERAL, datum)


def _object(txn, kind, identifier):
    return core.object_decode(core.txn_get_object(txn, kind, identifier))


def _target(txn, node, node_kind):
    packed = core.txn_get_object(txn, core.REC_NODE, node)
    _, target, _ = core.object_decode(packed)
    # The binding returns the target but not the node kind. Check the declared
    # edge, not just whether a typed object with that target ID exists.
    if packed != core.object_encode(core.REC_NODE, node_kind, target):
        raise ValueError("recorded source has the wrong node kind")
    return target


def _read_literal(txn, node, expected_kind):
    target = _target(txn, node, core.NODE_LITERAL)
    payload, kind = core.datum_decode(core.txn_get_datum(txn, target))
    if kind != expected_kind:
        raise ValueError("recorded literal has the wrong datum kind")
    return payload


def _read_i64(txn, node):
    return int.from_bytes(_read_literal(txn, node, core.DATUM_I64), "little", signed=True)


def _read_source(txn, node, *, from_call):
    if not from_call:
        return _read_i64(txn, node), None
    # Resolve the actual producer and its root. Never look up a producer by value.
    producer = _target(txn, node, core.NODE_SUBDAG)
    _, result, _ = _object(txn, core.REC_DAG, producer)
    return _read_i64(txn, result), producer


def _record_call(txn, implementation, operation, sources, *, call_input=None):
    arguments = [_read_source(txn, node, from_call=name == call_input)[0] for name, node in sources]
    value = operation(*arguments)
    _check_i64(value, f"{implementation.decode('ascii')} result")
    result = _put_literal(txn, core.DATUM_I64, value)
    version = _put_literal(txn, core.DATUM_STRING, implementation)
    bindings = [field for binding in sources for field in binding]
    return _put_object(txn, core.REC_DAG, result, b"implementation", version, *bindings)


def _record_sum(txn, a, b):
    left = _put_literal(txn, core.DATUM_I64, a)
    right = _put_literal(txn, core.DATUM_I64, b)
    return _record_call(txn, SUM, add, ((b"a", left), (b"b", right)))


def _check_scale_implementation(implementation):
    if type(implementation) is not bytes or implementation not in (SCALE_V1, SCALE_V2):
        raise ValueError(f"unsupported scale implementation {implementation!r}; use example.scale@1 or example.scale@2")


def _record_scale(txn, sum_call, factor, *, implementation=SCALE_V1):
    source = _put_object(txn, core.REC_NODE, core.NODE_SUBDAG, sum_call)
    multiplier = _put_literal(txn, core.DATUM_I64, factor)
    # The two supported versions deliberately share the same arithmetic.
    return _record_call(txn, implementation, mul, ((b"input", source), (b"factor", multiplier)), call_input=b"input")


def _put_snapshot(txn, entry, dag, *parents):
    tree = _put_object(txn, core.REC_TREE, entry, dag)
    return _put_object(txn, core.REC_COMMIT, tree, *parents)


def _publish(txn, ref, entry, dag, *parents):
    commit = _put_snapshot(txn, entry, dag, *parents)
    core.txn_ref_create(txn, ref, commit)
    return commit


def record(path, a, b, factor):
    """Create a fresh repository and return the recorded commit ID."""
    for name, value in (("a", a), ("b", b), ("factor", factor)):
        _check_i64(value, name)
    Path(path).mkdir()  # Do not reuse or modify an existing path.
    with _write_transaction(path, create=True) as txn:
        sum_call = _record_sum(txn, a, b)
        scale_call = _record_scale(txn, sum_call, factor)
        return _publish(txn, MAIN, ENTRY, scale_call)


def record_sum(path, pin, a, b):
    """Publish a sum under a new pin and return its commit ID."""
    _check_i64(a, "a")
    _check_i64(b, "b")
    with _write_transaction(path, create=True) as txn:
        return _publish(txn, pin, SUM_ENTRY, _record_sum(txn, a, b))


def _check_commit_id(commit, label="producer commit"):
    if type(commit) is not bytes or len(commit) != 16:
        raise ValueError(f"{label} must be a 16-byte ID")


def _check_ref_name(ref, label):
    if type(ref) is not bytes or not REF_NAME.fullmatch(ref):
        raise ValueError(f"{label} ref must be a valid ASCII ref name in bytes")


def _check_uuid4(value, label):
    if type(value) is not bytes or not UUID4.fullmatch(value):
        raise ValueError(f"{label} must be a canonical lowercase UUIDv4 in bytes")


def _selected_sum(txn, pin, expected):
    if core.txn_ref_get(txn, pin) != expected:
        raise ValueError("producer pin does not point to the expected commit")
    dag = _sum_dag(_snapshot(txn, expected))
    _inspect_call(txn, dag, SUM, (b"a", b"b"))  # Check shape, not arithmetic.
    return dag


def record_scale(path, producer_pin, producer_commit, result_ref, factor):
    """Scale the stored result of the exact pinned sum commit."""
    _check_i64(factor, "factor")
    _check_commit_id(producer_commit)
    with _write_transaction(path, create=False) as txn:
        sum_call = _selected_sum(txn, producer_pin, producer_commit)
        scale_call = _record_scale(txn, sum_call, factor)
        return _publish(txn, result_ref, SCALE_ENTRY, scale_call, producer_commit)


def _optional_ref(txn, ref):
    try:
        return core.txn_ref_get(txn, ref)
    except core.Error as error:
        status, _, detail = error.args
        # A dangling target can also produce not_found; it is not an absent ref.
        if (status, detail) != ("not_found", "ref was not found"):
            raise
        return None


def request_scale(path, producer_pin, producer_commit, plan_pin, factor, *, implementation=SCALE_V1):
    """Pin the versioned portable request and current main in a local plan."""
    _check_commit_id(producer_commit)
    _check_i64(factor, "factor")
    _check_scale_implementation(implementation)
    if type(plan_pin) is not bytes:
        raise ValueError("plan ref must be bytes")
    if plan_pin == MAIN:
        raise ValueError("plan ref must differ from main")
    with _write_transaction(path, create=False) as txn:
        _selected_sum(txn, producer_pin, producer_commit)
        expected_main = _optional_ref(txn, MAIN)
        plan = _put_scale_plan(txn, producer_commit, factor, implementation, expected_main)
        core.txn_ref_create(txn, plan_pin, plan)
    return plan


def _put_scale_plan(txn, producer, factor, implementation, expected_main):
    operation = _put_literal(txn, core.DATUM_STRING, implementation)
    multiplier = _put_literal(txn, core.DATUM_I64, factor)
    dag = _put_object(txn, core.REC_DAG, operation, b"implementation", operation, b"factor", multiplier)
    request = _put_snapshot(txn, REQUEST_ENTRY, dag, producer)
    if expected_main == request:
        raise ValueError("main already points to this request; stage requests under a separate ref")
    parents = (request,) if expected_main is None else (request, expected_main)
    return _put_snapshot(txn, PLAN_ENTRY, dag, *parents)


def _check_policy_default(policy_default):
    if type(policy_default) is not bytes or policy_default not in (REUSE_DEFAULT, EXECUTE_DEFAULT):
        raise ValueError("policy default must be reuse-by-default or execute-by-default")


def _check_policy_override(override):
    if type(override) is not bytes or override not in (USE_DEFAULT, FRESH, REUSE_SELECTED):
        raise ValueError("policy override must be default, fresh, or reuse-selected")


def define_scale_policy(path, policy_ref, policy_default, *, basis_ref=None, basis_commit=None):
    """Pin a default for the example's fixed scale intent, optionally versioning an old one."""
    _check_policy_default(policy_default)
    _check_ref_name(policy_ref, "policy")
    if (basis_ref is None) != (basis_commit is None):
        raise ValueError("policy basis requires both a ref and commit ID")
    if basis_ref is not None:
        _check_ref_name(basis_ref, "policy basis")
        _check_commit_id(basis_commit, "policy basis commit")
    if policy_ref == MAIN or basis_ref in (policy_ref, MAIN):
        raise ValueError("policy, basis, and main refs must be distinct")
    with _write_transaction(path, create=False) as txn:
        if basis_ref is not None:
            _selected_policy(txn, basis_ref, basis_commit)
        mode = _put_literal(txn, core.DATUM_STRING, policy_default)
        dag = _put_object(txn, core.REC_DAG, mode, b"default", mode)
        parents = () if basis_commit is None else (basis_commit,)
        return _publish(txn, policy_ref, POLICY_ENTRY, dag, *parents)


def _check_intent_refs(*refs):
    for label, ref in refs:
        _check_ref_name(ref, label)
    if len({MAIN, *(ref for _, ref in refs)}) != len(refs) + 1:
        raise ValueError("intent operation refs, selection slots, and main must be distinct")


def define_scale_intent(path, intent_ref, default_implementation, *, policy_default=None, v1_selection_ref=None,
                        v2_selection_ref=None, basis_ref=None, basis_commit=None):
    """Pin a scale definition, or version just the default implementation of an exact basis."""
    _check_scale_implementation(default_implementation)
    if (basis_ref is None) != (basis_commit is None):
        raise ValueError("intent basis requires both a ref and commit ID")
    refs = [("intent", intent_ref)]
    if basis_ref is None:
        _check_policy_default(policy_default)
        refs.extend((("v1 selection", v1_selection_ref), ("v2 selection", v2_selection_ref)))
    else:
        _check_commit_id(basis_commit, "intent basis commit")
        if any(value is not None for value in (policy_default, v1_selection_ref, v2_selection_ref)):
            raise ValueError("an intent version inherits its reuse default and selection slots from its basis")
        refs.append(("intent basis", basis_ref))
    _check_intent_refs(*refs)
    with _write_transaction(path, create=False) as txn:
        if basis_ref is not None:
            basis = _selected_intent(txn, basis_ref, basis_commit).definition
            _check_intent_refs(*refs, ("v1 selection", basis.v1_selection_ref), ("v2 selection", basis.v2_selection_ref))
            intent = basis._replace(default_implementation=default_implementation)
        else:
            intent = _ScaleIntent(default_implementation, policy_default, v1_selection_ref, v2_selection_ref)
        nodes = [_put_literal(txn, core.DATUM_STRING, value) for value in intent]
        bindings = [field for pair in zip(INTENT_FIELDS, nodes) for field in pair]
        dag = _put_object(txn, core.REC_DAG, nodes[0], *bindings)
        parents = () if basis_commit is None else (basis_commit,)
        return _publish(txn, intent_ref, INTENT_ENTRY, dag, *parents)


def _check_supersession(predecessor, successor, reason):
    _check_scale_implementation(predecessor)
    _check_scale_implementation(successor)
    if predecessor == successor:
        raise ValueError("supersession endpoints must be distinct implementations")
    if type(reason) is not bytes or reason not in (b"correctness-fix", b"operational-replacement"):
        raise ValueError("supersession reason must be correctness-fix or operational-replacement")


def _check_supersession_evidence(txn, basis, evidence):
    if basis == evidence:
        raise ValueError("supersession basis and evidence must be distinct commits")
    _, tree, _ = _object(txn, core.REC_COMMIT, evidence)
    _, _, entries = _object(txn, core.REC_TREE, tree)
    if entries == 0:
        raise ValueError("supersession evidence must have a nonempty tree")


def declare_scale_supersession(path, basis_ref, basis_commit, output_ref, predecessor, successor, reason,
                                evidence_ref, evidence_commit):
    """Create an advisory intent version without changing the definition or selection slots."""
    _check_commit_id(basis_commit, "intent basis commit")
    _check_commit_id(evidence_commit, "evidence commit")
    _check_supersession(predecessor, successor, reason)
    refs = (("intent basis", basis_ref), ("supersession output", output_ref), ("evidence", evidence_ref))
    _check_intent_refs(*refs)
    with _write_transaction(path, create=False) as txn:
        basis = _selected_intent(txn, basis_ref, basis_commit)
        intent = basis.definition
        _check_intent_refs(*refs, ("v1 selection", intent.v1_selection_ref), ("v2 selection", intent.v2_selection_ref))
        if basis.supersession is not None:
            raise ValueError("intent ancestry already has a supersession declaration")
        if core.txn_ref_get(txn, evidence_ref) != evidence_commit:
            raise ValueError("evidence ref does not point to the expected evidence commit")
        _check_supersession_evidence(txn, basis_commit, evidence_commit)
        nodes = [_put_literal(txn, core.DATUM_STRING, value) for value in (predecessor, successor, reason)]
        bindings = [field for pair in zip(SUPERSESSION_FIELDS, nodes) for field in pair]
        dag = _put_object(txn, core.REC_DAG, nodes[0], *bindings)
        return _publish(txn, output_ref, SUPERSESSION_ENTRY, dag, basis_commit, evidence_commit)


def _resolve_intent_implementation(intent, requested):
    if type(requested) is bytes and requested == USE_DEFAULT:
        return intent.default_implementation, b"default-implementation"
    _check_scale_implementation(requested)
    return requested, b"explicit-implementation"


def _intent_slot(intent, implementation):
    return intent.v1_selection_ref if implementation == SCALE_V1 else intent.v2_selection_ref


def _check_policy_request_refs(producer_pin, policy_ref, plan_pin, decision_ref, selection_ref, selection_commit):
    refs = [("producer", producer_pin), ("policy", policy_ref), ("plan", plan_pin), ("decision", decision_ref)]
    if selection_commit is not None:
        _check_commit_id(selection_commit, "selection commit")
        if selection_ref is None:
            raise ValueError("selection commit requires a selection ref")
    if selection_ref is not None:
        refs.append(("selection", selection_ref))
    for label, ref in refs:
        _check_ref_name(ref, label)
    if len({MAIN, *(ref for _, ref in refs)}) != len(refs) + 1:
        raise ValueError("producer, policy, plan, decision, selection, and main refs must be distinct")


def _resolve_policy_selection(txn, policy_default, override, selection_ref, selection_commit):
    if override == FRESH or (override == USE_DEFAULT and policy_default == EXECUTE_DEFAULT):
        return None
    if selection_ref is None:
        raise ValueError("reuse policy requires an explicit selection ref")
    if _optional_ref(txn, selection_ref) != selection_commit:
        raise ValueError("selection ref does not match the expected commit or absence")
    return selection_ref


def _policy_reason(policy_default, override, *, selected):
    if override == REUSE_SELECTED:
        if not selected:
            raise ValueError("explicit reuse requires a present selection")
        return b"override-selected-reuse"
    if override == FRESH or policy_default == EXECUTE_DEFAULT:
        if selected:
            raise ValueError("fresh execution cannot retain a selection")
        return b"override-fresh" if override == FRESH else b"default-execution"
    return b"default-selection" if selected else b"default-no-selection"


def _put_scale_decision(txn, decision_ref, entry, fields, *parents):
    fields = {b"decision_id": str(uuid4()).encode("ascii"), **fields}
    nodes = {name: _put_literal(txn, core.DATUM_STRING, value) for name, value in fields.items()}
    bindings = [field for pair in nodes.items() for field in pair]
    dag = _put_object(txn, core.REC_DAG, nodes[b"decision_id"], *bindings)
    return _publish(txn, decision_ref, entry, dag, *parents)


def _decide_scale(txn, producer, factor, implementation, plan_pin, decision_ref, *, entry, definition, policy_default,
                  override, selection_ref, selection_commit, fields):
    consulted = _resolve_policy_selection(txn, policy_default, override, selection_ref, selection_commit)
    reusing = consulted is not None and selection_commit is not None
    reason = _policy_reason(policy_default, override, selected=reusing)
    expected_main = _optional_ref(txn, MAIN)
    plan = _put_scale_plan(txn, producer, factor, implementation, expected_main)
    fields = {b"override": override, b"reason": reason, **fields}
    if consulted is not None:
        fields[b"selection_ref"] = consulted
    if reusing:
        if _optional_ref(txn, plan_pin) is not None:
            raise ValueError("plan output ref is already occupied")
        request, _ = _read_plan(txn, plan)
        selection = _read_scale_selection(txn, selection_commit, expected_request=request)
        _update_main(txn, selection.result, expected_main)
        return _put_scale_decision(txn, decision_ref, entry, fields, plan, definition, selection_commit)
    core.txn_ref_create(txn, plan_pin, plan)
    return _put_scale_decision(txn, decision_ref, entry, {**fields, b"plan_ref": plan_pin}, plan, definition)


def request_policy_scale(path, producer_pin, producer_commit, policy_ref, policy_commit, plan_pin, decision_ref,
                         factor, *, implementation=SCALE_V1, override=USE_DEFAULT, selection_ref=None,
                         selection_commit=None):
    """Prepare a fresh plan or publish exact reuse, atomically retaining a decision commit."""
    _check_commit_id(producer_commit)
    _check_commit_id(policy_commit, "policy commit")
    _check_i64(factor, "factor")
    _check_scale_implementation(implementation)
    _check_policy_override(override)
    _check_policy_request_refs(producer_pin, policy_ref, plan_pin, decision_ref, selection_ref, selection_commit)
    with _write_transaction(path, create=False) as txn:
        _selected_sum(txn, producer_pin, producer_commit)
        policy_default, _ = _selected_policy(txn, policy_ref, policy_commit)
        return _decide_scale(
            txn, producer_commit, factor, implementation, plan_pin, decision_ref,
            entry=DECISION_ENTRY, definition=policy_commit, policy_default=policy_default,
            override=override, selection_ref=selection_ref, selection_commit=selection_commit, fields={},
        )


def request_intent_scale(path, producer_pin, producer_commit, intent_ref, intent_commit, plan_pin, decision_ref,
                         factor, *, implementation=USE_DEFAULT, override=USE_DEFAULT, selection_commit=None):
    """Resolve the implementation from an exact intent version before deciding whether to reuse."""
    _check_commit_id(producer_commit)
    _check_commit_id(intent_commit, "intent commit")
    _check_i64(factor, "factor")
    _check_policy_override(override)
    if selection_commit is not None:
        _check_commit_id(selection_commit, "selection commit")
    refs = (("producer", producer_pin), ("intent", intent_ref), ("plan", plan_pin), ("decision", decision_ref))
    _check_intent_refs(*refs)
    with _write_transaction(path, create=False) as txn:
        _selected_sum(txn, producer_pin, producer_commit)
        intent = _selected_intent(txn, intent_ref, intent_commit).definition
        _check_intent_refs(*refs, ("v1 selection", intent.v1_selection_ref), ("v2 selection", intent.v2_selection_ref))
        chosen, reason = _resolve_intent_implementation(intent, implementation)
        fields = {b"implementation_override": implementation, b"implementation_reason": reason}
        return _decide_scale(
            txn, producer_commit, factor, chosen, plan_pin, decision_ref,
            entry=INTENT_DECISION_ENTRY, definition=intent_commit, policy_default=intent.policy_default,
            override=override, selection_ref=_intent_slot(intent, chosen), selection_commit=selection_commit,
            fields=fields,
        )


def _work_requested_scale(txn, incoming, request_commit):
    if core.txn_ref_get(txn, incoming) != request_commit:
        raise ValueError("incoming ref does not point to the expected request commit")
    request = _read_request(txn, request_commit)
    _inspect_call(txn, request.sum_dag, SUM, (b"a", b"b"))
    scale = _record_scale(txn, request.sum_dag, request.factor, implementation=request.implementation)
    return _put_snapshot(txn, REQUESTED_SCALE_ENTRY, scale, request_commit)


def work_scale(path, incoming, request_commit, result_ref):
    """Evaluate the exact staged request using its stored arguments."""
    _check_commit_id(request_commit, "request commit")
    with _write_transaction(path, create=False) as txn:
        result = _work_requested_scale(txn, incoming, request_commit)
        core.txn_ref_create(txn, result_ref, result)
    return result


def work_scale_attempt(path, incoming, request_commit, attempt_ref, attempt_id):
    """Evaluate a pinned request and retain this occurrence, not a separate result pin."""
    _check_commit_id(request_commit, "request commit")
    _check_uuid4(attempt_id, "attempt ID")
    _check_ref_name(incoming, "incoming")
    _check_ref_name(attempt_ref, "attempt")
    if len({incoming, attempt_ref, MAIN}) != 3:
        raise ValueError("incoming, attempt, and main refs must be distinct")
    with _write_transaction(path, create=False) as txn:
        result = _work_requested_scale(txn, incoming, request_commit)
        identity = _put_literal(txn, core.DATUM_STRING, attempt_id)
        dag = _put_object(txn, core.REC_DAG, identity, b"attempt_id", identity)
        return _publish(txn, attempt_ref, ATTEMPT_ENTRY, dag, request_commit, result)


def _write_bundle(bundle_path, bundle):
    with Path(bundle_path).open("xb") as output:
        output.write(bundle)


def _export_selected(path, pin, commit, bundle_path, select):
    with _repository(path, create=False) as repo:
        with _read_transaction(repo) as txn:
            select(txn, pin, commit)
        # Export by immutable ID in a new snapshot, never by re-resolving the pin.
        bundle = core.repo_export_commit(repo, commit)
    _write_bundle(bundle_path, bundle)
    return commit


def export_sum(path, pin, producer_commit, bundle_path):
    """Export the exact selected sum to a new bundle file."""
    _check_commit_id(producer_commit)
    return _export_selected(path, pin, producer_commit, bundle_path, _selected_sum)


def export_request(path, plan_pin, plan_commit, bundle_path):
    """Export only the request selected by the exact source-local plan."""
    _check_commit_id(plan_commit, "plan commit")
    with _repository(path, create=False) as repo:
        with _read_transaction(repo) as txn:
            request, _ = _selected_plan(txn, plan_pin, plan_commit)
            _inspect_call(txn, request.sum_dag, SUM, (b"a", b"b"))
        # The plan and its main expectation are not part of the portable closure.
        bundle = core.repo_export_commit(repo, request.commit)
    _write_bundle(bundle_path, bundle)
    return request.commit


def _checked_scale(txn, result):
    report = _inspect_snapshot(txn, result)
    producer = report.get("producer_commit")
    if producer is None or "request_commit" in report:
        raise ValueError("expected a split recorded-scale-v1 commit")
    _, scale = report["calls"]
    return bytes.fromhex(producer), scale["arguments"]["factor"]["value"]


def _selected_scale(txn, pin, expected):
    if core.txn_ref_get(txn, pin) != expected:
        raise ValueError("result pin does not point to the expected commit")
    report = _inspect_snapshot(txn, expected)
    if "producer_commit" not in report or len(report["calls"]) != 2:
        raise ValueError("expected a recorded-scale-v1 or requested-scale-v1 result commit")


def export_scale(path, pin, result_commit, bundle_path):
    """Export the exact selected scale with its producer to a new bundle file."""
    _check_commit_id(result_commit, "result commit")
    return _export_selected(path, pin, result_commit, bundle_path, _selected_scale)


def export_scale_attempt(path, pin, attempt_commit, bundle_path):
    """Export the exact selected attempt, its result, and its request closure."""
    _check_commit_id(attempt_commit, "attempt commit")
    _check_ref_name(pin, "attempt")
    return _export_selected(path, pin, attempt_commit, bundle_path, _selected_attempt)


def stage_input(path, pin, bundle_path):
    """Import a bundle under a new local pin and return its actual root ID."""
    with Path(bundle_path).open("rb") as source:
        bundle = source.read(MAX_BUNDLE_BYTES + 1)
    if len(bundle) > MAX_BUNDLE_BYTES:
        raise ValueError("commit bundle exceeds 64 MiB")
    with _repository(path, create=True) as repo:
        return core.repo_import_commit_staged(repo, bundle, pin)


def _check_reuse_selection(plan_pin, plan_commit, input_pin, input_commit, output, output_label,
                           *, input_label="result"):
    _check_commit_id(plan_commit, "plan commit")
    _check_commit_id(input_commit, f"{input_label} commit")
    for label, ref in (("plan", plan_pin), (input_label, input_pin), (output_label, output)):
        _check_ref_name(ref, label)
    if len({plan_pin, input_pin, output, MAIN}) != 4:
        raise ValueError(f"plan, {input_label}, {output_label}, and main refs must be distinct")


def _selected_reuse(txn, plan_pin, plan_commit, result_pin, result_commit):
    request, expected_main = _selected_plan(txn, plan_pin, plan_commit)
    if core.txn_ref_get(txn, result_pin) != result_commit:
        raise ValueError("result pin does not point to the expected commit")
    _inspect_snapshot(txn, result_commit, expected_request=request)
    return request, expected_main


def select_scale_result(path, plan_pin, plan_commit, result_pin, result_commit, selection_ref):
    """Record an exact reusable result without publishing or consuming either pin."""
    _check_reuse_selection(plan_pin, plan_commit, result_pin, result_commit, selection_ref, "selection")
    with _write_transaction(path, create=False) as txn:
        request, _ = _selected_reuse(txn, plan_pin, plan_commit, result_pin, result_commit)
        result_name = _put_literal(txn, core.DATUM_STRING, result_pin)
        dag = _put_object(txn, core.REC_DAG, result_name, b"result_ref", result_name)
        return _publish(txn, selection_ref, SELECTION_ENTRY, dag, request.commit, result_commit)


def select_scale_attempt(path, plan_pin, plan_commit, attempt_ref, attempt_commit, selection_ref):
    """Retain the exact attempt for the plan's request without publishing it."""
    _check_reuse_selection(plan_pin, plan_commit, attempt_ref, attempt_commit, selection_ref, "selection",
                           input_label="attempt")
    with _write_transaction(path, create=False) as txn:
        request, _ = _selected_plan(txn, plan_pin, plan_commit)
        _selected_attempt(txn, attempt_ref, attempt_commit, expected_request=request)
        name = _put_literal(txn, core.DATUM_STRING, attempt_ref)
        dag = _put_object(txn, core.REC_DAG, name, b"attempt_ref", name)
        return _publish(txn, selection_ref, ATTEMPT_SELECTION_ENTRY, dag, request.commit, attempt_commit)


def adopt_scale_attempt(path, basis_ref, basis_commit, attempt_ref, attempt_commit, selection_ref):
    """Create a new version of an attempt choice without changing its basis."""
    _check_commit_id(basis_commit, "basis selection commit")
    _check_commit_id(attempt_commit, "attempt commit")
    for label, ref in (("basis", basis_ref), ("attempt", attempt_ref), ("selection", selection_ref)):
        _check_ref_name(ref, label)
    if len({basis_ref, attempt_ref, selection_ref, MAIN}) != 4:
        raise ValueError("basis, attempt, selection, and main refs must be distinct")
    with _write_transaction(path, create=False) as txn:
        if core.txn_ref_get(txn, basis_ref) != basis_commit:
            raise ValueError("basis ref does not point to the expected selection commit")
        basis = _read_scale_selection(txn, basis_commit)
        if basis.attempt is None:
            raise ValueError("adoption basis must be an attempt selection")
        attempt = _selected_attempt(txn, attempt_ref, attempt_commit, expected_request=basis.request)
        if attempt.commit == basis.attempt.commit:
            raise ValueError("adoption must change the selected attempt commit")
        name = _put_literal(txn, core.DATUM_STRING, attempt_ref)
        dag = _put_object(txn, core.REC_DAG, name, b"attempt_ref", name)
        return _publish(txn, selection_ref, ADOPTION_ENTRY, dag, basis_commit, attempt_commit)


def stage_reused_scale(path, plan_pin, plan_commit, result_pin, result_commit, dest_pin):
    """Stage an exact local result for a plan without executing or publishing it."""
    _check_reuse_selection(plan_pin, plan_commit, result_pin, result_commit, dest_pin, "destination")
    with _write_transaction(path, create=False) as txn:
        _selected_reuse(txn, plan_pin, plan_commit, result_pin, result_commit)
        core.txn_ref_create(txn, dest_pin, result_commit)
    return result_commit


def _update_main(txn, result_commit, expected_main):
    if expected_main is None:
        core.txn_ref_create(txn, MAIN, result_commit)
    else:
        if core.txn_ref_get(txn, MAIN) != expected_main:
            raise ValueError("main does not point to the expected commit")
        core.txn_ref_update(txn, MAIN, result_commit)


def publish_scale(path, returned, result_commit, producer_commit, expected_factor, expected_main):
    """Publish a staged scale matching the requested producer and factor."""
    if type(returned) is not bytes:
        raise ValueError("staging ref must be bytes")
    if returned == MAIN:
        raise ValueError("staging ref must differ from main")
    _check_commit_id(result_commit, "result commit")
    _check_commit_id(producer_commit)
    _check_i64(expected_factor, "expected factor")
    if expected_main is not None:
        _check_commit_id(expected_main, "expected main commit")
    with _write_transaction(path, create=False) as txn:
        # Inspect the caller's immutable selection, never substitute the current pin target.
        producer, factor = _checked_scale(txn, result_commit)
        if producer != producer_commit:
            raise ValueError("result does not retain the expected producer commit")
        if factor != expected_factor:
            raise ValueError("recorded factor does not match the expected factor")
        _update_main(txn, result_commit, expected_main)
        # If the ref moved or disappeared, this failure also rolls back main.
        core.txn_ref_delete_expected(txn, returned, result_commit)
    return result_commit


def _record_publication(txn, receipt_ref, fields):
    nodes = {name: _put_literal(txn, core.DATUM_STRING, value) for name, value in fields.items()}
    bindings = [field for binding in nodes.items() for field in binding]
    dag = _put_object(txn, core.REC_DAG, nodes[b"result_commit"], *bindings)
    # Literal IDs, not parents: retaining a receipt does not pin the old history.
    _publish(txn, receipt_ref, PUBLICATION_ENTRY, dag)


def publish_requested_scale(path, plan_pin, plan_commit, returned, result_commit, *, receipt_ref=None):
    """Publish and consume both pins, or acknowledge a matching retained receipt."""
    _check_commit_id(plan_commit, "plan commit")
    _check_commit_id(result_commit, "result commit")
    if type(plan_pin) is not bytes or type(returned) is not bytes:
        raise ValueError("plan and staging refs must be bytes")
    if len({plan_pin, returned, MAIN}) != 3:
        raise ValueError("plan, staging, and main refs must be distinct")
    if receipt_ref is not None:
        for label, ref in (("plan", plan_pin), ("staging", returned), ("receipt", receipt_ref)):
            if type(ref) is not bytes or not REF_NAME.fullmatch(ref):
                raise ValueError(f"{label} ref must be a valid ASCII ref name in bytes")
        if receipt_ref in (plan_pin, returned, MAIN):
            raise ValueError("receipt, plan, staging, and main refs must be distinct")
        intent = {b"plan_ref": plan_pin, b"plan_commit": plan_commit.hex().encode("ascii"),
                  b"staging_ref": returned, b"result_commit": result_commit.hex().encode("ascii")}
    with _write_transaction(path, create=False) as txn:
        if receipt_ref is not None:
            receipt = _optional_ref(txn, receipt_ref)
            if receipt is not None:
                if _read_publication(txn, receipt) != intent:
                    raise ValueError("receipt does not match the requested publication")
                return result_commit
        request, expected_main = _selected_plan(txn, plan_pin, plan_commit)
        _inspect_snapshot(txn, result_commit, expected_request=request)
        if receipt_ref is not None:
            _record_publication(txn, receipt_ref, intent)
        _update_main(txn, result_commit, expected_main)
        core.txn_ref_delete_expected(txn, returned, result_commit)
        core.txn_ref_delete_expected(txn, plan_pin, plan_commit)
    return result_commit


def publish_reused_scale(path, plan_pin, plan_commit, result_pin, result_commit, reuse_ref):
    """Publish an exact local result and retain the plan and result as evidence of reuse."""
    _check_reuse_selection(plan_pin, plan_commit, result_pin, result_commit, reuse_ref, "reuse")
    with _write_transaction(path, create=False) as txn:
        _, expected_main = _selected_reuse(txn, plan_pin, plan_commit, result_pin, result_commit)
        _update_main(txn, result_commit, expected_main)
        core.txn_ref_delete_expected(txn, plan_pin, plan_commit)
        plan_name = _put_literal(txn, core.DATUM_STRING, plan_pin)
        result_name = _put_literal(txn, core.DATUM_STRING, result_pin)
        dag = _put_object(txn, core.REC_DAG, plan_name, b"plan_ref", plan_name, b"result_ref", result_name)
        _publish(txn, reuse_ref, REUSE_ENTRY, dag, plan_commit, result_commit)
    return result_commit


def publish_selected_scale(path, plan_pin, plan_commit, selection_ref, selection_commit, reuse_ref):
    """Use the exact retained selection and record how it was used, atomically."""
    _check_reuse_selection(plan_pin, plan_commit, selection_ref, selection_commit, reuse_ref, "reuse",
                           input_label="selection")
    with _write_transaction(path, create=False) as txn:
        request, expected_main = _selected_plan(txn, plan_pin, plan_commit)
        if core.txn_ref_get(txn, selection_ref) != selection_commit:
            raise ValueError("selection ref does not point to the expected selection commit")
        selection = _read_scale_selection(txn, selection_commit, expected_request=request)
        _update_main(txn, selection.result, expected_main)
        core.txn_ref_delete_expected(txn, plan_pin, plan_commit)
        plan_name = _put_literal(txn, core.DATUM_STRING, plan_pin)
        selection_name = _put_literal(txn, core.DATUM_STRING, selection_ref)
        dag = _put_object(txn, core.REC_DAG, plan_name, b"plan_ref", plan_name, b"selection_ref", selection_name)
        _publish(txn, reuse_ref, SELECTED_REUSE_ENTRY, dag, plan_commit, selection_commit)
    return selection.result


def abandon_scale_request(path, plan_pin, plan_commit):
    """Consume the exact local plan pin without publishing or canceling worker work."""
    _check_commit_id(plan_commit, "plan commit")
    if type(plan_pin) is not bytes or not REF_NAME.fullmatch(plan_pin):
        raise ValueError("plan ref must be a valid ASCII ref name in bytes")
    if plan_pin == MAIN:
        raise ValueError("plan ref must differ from main")
    with _write_transaction(path, create=False) as txn:
        _selected_plan(txn, plan_pin, plan_commit)
        core.txn_ref_delete_expected(txn, plan_pin, plan_commit)
    return plan_commit


def release_input(path, pin, producer_commit, result_ref):
    """Release the exact producer pin only if the selected result retains it."""
    _check_commit_id(producer_commit)
    with _write_transaction(path, create=False) as txn:
        result = core.txn_ref_get(txn, result_ref)
        producer, _ = _checked_scale(txn, result)
        if producer != producer_commit:
            raise ValueError("result does not retain the expected producer commit")
        core.txn_ref_delete_expected(txn, pin, producer_commit)
    return producer_commit


def collect(path):
    """Commit garbage collection and return the number of removed objects."""
    with _write_transaction(path, create=False) as txn:
        return core.txn_collect_garbage(txn)


def _inspect_call(txn, dag, implementation, names, *, call_input=None):
    _, result, count = _object(txn, core.REC_DAG, dag)
    if count != len(names) + 1:
        raise ValueError(f"wrong binding count for {implementation.decode('ascii')}")
    version = core.txn_lookup_node(txn, dag, b"implementation")
    if _read_literal(txn, version, core.DATUM_STRING) != implementation:
        raise ValueError(f"expected recorded implementation {implementation.decode('ascii')}")
    arguments = {}
    producer = None
    for name in names:
        node = core.txn_lookup_node(txn, dag, name)
        value, source = _read_source(txn, node, from_call=name == call_input)
        argument = {"node": node.hex(), "value": value}
        if source is not None:
            producer = source
            argument["call"] = producer.hex()
        arguments[name.decode("ascii")] = argument
    return {
        "dag": dag.hex(),
        "implementation": implementation.decode("ascii"),
        "result": {"node": result.hex(), "value": _read_i64(txn, result)},
        "arguments": arguments,
    }, producer


def _snapshot(txn, commit):
    commit_view, tree, parents = _object(txn, core.REC_COMMIT, commit)
    tree_view, _, entries = _object(txn, core.REC_TREE, tree)
    if entries != 1:
        raise ValueError("expected a single recorded-call tree entry")
    dag, entry = core.object_view_entry(tree_view, 0)
    return commit_view, parents, entry, dag


def _sum_dag(snapshot):
    _, parents, entry, dag = snapshot
    if parents != 0 or entry != SUM_ENTRY:
        raise ValueError("expected a parentless recorded-sum-v1 commit")
    return dag


def _read_request(txn, commit):
    view, parents, entry, dag = _snapshot(txn, commit)
    if entry != REQUEST_ENTRY or parents != 1:
        raise ValueError("expected a scale-request-v1 commit with one producer parent")
    _, root, count = _object(txn, core.REC_DAG, dag)
    version = core.txn_lookup_node(txn, dag, b"implementation")
    if count != 2 or root != version:
        raise ValueError("expected scale request with an implementation root and a factor")
    implementation = _read_literal(txn, version, core.DATUM_STRING)
    _check_scale_implementation(implementation)
    factor = _read_i64(txn, core.txn_lookup_node(txn, dag, b"factor"))
    producer = core.object_view_parent(view, 0)
    return _ScaleRequest(commit, dag, producer, _sum_dag(_snapshot(txn, producer)), implementation, factor)


def _read_plan(txn, commit):
    view, parents, entry, dag = _snapshot(txn, commit)
    if entry != PLAN_ENTRY or parents not in (1, 2):
        raise ValueError("expected a scale-plan-v1 commit with a request and optional main parent")
    request = _read_request(txn, core.object_view_parent(view, 0))
    if dag != request.dag:
        raise ValueError("plan DAG does not match the request DAG")
    return request, core.object_view_parent(view, 1) if parents == 2 else None


def _selected_plan(txn, pin, commit):
    if core.txn_ref_get(txn, pin) != commit:
        raise ValueError("plan ref does not point to the expected plan commit")
    return _read_plan(txn, commit)


def _inspect_request(txn, commit, entry):
    report = {"commit": commit.hex()}
    if entry == PLAN_ENTRY:
        request, main = _read_plan(txn, commit)
        report["expected_main"] = main.hex() if main is not None else None
    else:
        request = _read_request(txn, commit)
    summed, _ = _inspect_call(txn, request.sum_dag, SUM, (b"a", b"b"))
    return {**report, "request_commit": request.commit.hex(), "producer_commit": request.producer.hex(),
            "request_implementation": request.implementation.decode("ascii"),
            "request_factor": request.factor, "calls": [summed]}


def _read_publication(txn, commit):
    _, parents, entry, dag = _snapshot(txn, commit)
    if entry != PUBLICATION_ENTRY or parents != 0:
        raise ValueError("expected a parentless scale-publication-v1 receipt")
    _, root, count = _object(txn, core.REC_DAG, dag)
    if count != len(PUBLICATION_FIELDS) or root != core.txn_lookup_node(txn, dag, b"result_commit"):
        raise ValueError("publication receipt has the wrong DAG layout")
    fields = {name: _read_literal(txn, core.txn_lookup_node(txn, dag, name), core.DATUM_STRING)
              for name in PUBLICATION_FIELDS}
    plan, stage = fields[b"plan_ref"], fields[b"staging_ref"]
    if not (REF_NAME.fullmatch(plan) and REF_NAME.fullmatch(stage) and len({plan, stage, MAIN}) == 3
            and COMMIT_HEX.fullmatch(fields[b"plan_commit"]) and COMMIT_HEX.fullmatch(fields[b"result_commit"])):
        raise ValueError("publication receipt has invalid ref names or commit IDs")
    return fields


def _read_single_string(txn, dag, field, label):
    _, root, count = _object(txn, core.REC_DAG, dag)
    if count != 1 or root != core.txn_lookup_node(txn, dag, field):
        raise ValueError(f"{label} has the wrong DAG layout")
    return _read_literal(txn, root, core.DATUM_STRING)


def _read_scale_policy(txn, commit):
    policy = None
    while commit is not None:
        view, parents, entry, dag = _snapshot(txn, commit)
        if entry != POLICY_ENTRY or parents not in (0, 1):
            raise ValueError("expected a scale-intent-policy-v1 commit with an optional policy parent")
        mode = _read_single_string(txn, dag, b"default", "scale intent policy")
        _check_policy_default(mode)
        commit = core.object_view_parent(view, 0) if parents else None
        if policy is None:
            policy = mode, commit
    return policy


def _selected_policy(txn, ref, commit):
    if core.txn_ref_get(txn, ref) != commit:
        raise ValueError("policy ref does not point to the expected policy commit")
    return _read_scale_policy(txn, commit)


def _read_string_field(txn, dag, name):
    return _read_literal(txn, core.txn_lookup_node(txn, dag, name), core.DATUM_STRING)


def _read_intent_definition(txn, dag):
    _, root, count = _object(txn, core.REC_DAG, dag)
    if count != len(INTENT_FIELDS) or root != core.txn_lookup_node(txn, dag, INTENT_FIELDS[0]):
        raise ValueError("scale intent definition has the wrong DAG layout")
    intent = _ScaleIntent(*(_read_string_field(txn, dag, name) for name in INTENT_FIELDS))
    _check_scale_implementation(intent.default_implementation)
    _check_policy_default(intent.policy_default)
    _check_intent_refs(("v1 selection", intent.v1_selection_ref), ("v2 selection", intent.v2_selection_ref))
    return intent


def _read_supersession(txn, commit, view, parents, dag):
    if parents != 2:
        raise ValueError("supersession must have ordered intent basis and evidence parents")
    _, root, count = _object(txn, core.REC_DAG, dag)
    if count != len(SUPERSESSION_FIELDS) or root != core.txn_lookup_node(txn, dag, b"predecessor"):
        raise ValueError("supersession declaration has the wrong DAG layout")
    predecessor, successor, reason = (_read_string_field(txn, dag, name) for name in SUPERSESSION_FIELDS)
    _check_supersession(predecessor, successor, reason)
    basis, evidence = (core.object_view_parent(view, i) for i in range(2))
    _check_supersession_evidence(txn, basis, evidence)
    return _Supersession(commit, basis, evidence, predecessor, successor, reason)


def _read_scale_intent(txn, commit):
    head = commit
    previous = None
    definition = None
    supersession = None
    while True:
        view, parents, entry, dag = _snapshot(txn, commit)
        if entry == SUPERSESSION_ENTRY:
            if supersession is not None:
                raise ValueError("intent ancestry already has a supersession declaration")
            supersession = _read_supersession(txn, commit, view, parents, dag)
        elif entry == INTENT_ENTRY and parents in (0, 1):
            intent = _read_intent_definition(txn, dag)
            if definition is None:
                definition = intent
            elif intent != definition._replace(default_implementation=intent.default_implementation):
                raise ValueError("an intent version must preserve its reuse default and selection slots")
            if parents == 0:
                return _IntentVersion(definition, previous, commit, supersession)
        else:
            raise ValueError("expected a scale-intent-definition-v1 commit with an optional intent parent "
                             "or a scale supersession declaration")
        # Parent 1 on a declaration is opaque evidence, not part of the intent ancestry.
        parent = core.object_view_parent(view, 0)
        if commit == head:
            previous = parent
        commit = parent


def _selected_intent(txn, ref, commit):
    if core.txn_ref_get(txn, ref) != commit:
        raise ValueError("intent ref does not point to the expected intent commit")
    return _read_scale_intent(txn, commit)


def _supersession_report(declaration):
    if declaration is None:
        return None
    return {"commit": declaration.commit.hex(), "basis_commit": declaration.basis.hex(),
            "evidence_commit": declaration.evidence.hex(), "predecessor": declaration.predecessor.decode("ascii"),
            "successor": declaration.successor.decode("ascii"), "reason": declaration.reason.decode("ascii")}


def _supersession_view(intent_commit, implementation, declaration):
    relation = "none"
    if declaration is not None:
        relation = "predecessor" if implementation == declaration.predecessor else "successor"
    return {"intent_commit": intent_commit.hex(), "relation": relation, "declaration": _supersession_report(declaration)}


def _inspect_scale_decision(txn, commit, view, parents, entry, dag, *, knowledge_commit=None):
    label = "intent" if entry == INTENT_DECISION_ENTRY else "policy"
    if parents not in (2, 3):
        raise ValueError(f"{label} decision must have ordered plan, {label}, and optional selection parents")
    _, root, count = _object(txn, core.REC_DAG, dag)
    if root != core.txn_lookup_node(txn, dag, b"decision_id"):
        raise ValueError(f"{label} decision must have its decision ID as root")
    identity = _read_literal(txn, root, core.DATUM_STRING)
    _check_uuid4(identity, "decision ID")

    def read_field(name):
        return _read_string_field(txn, dag, name)

    plan, definition = (core.object_view_parent(view, i) for i in range(2))
    request, expected_main = _read_plan(txn, plan)
    if expected_main == request.commit:
        raise ValueError(f"{label} decision plan cannot expect its own request as main")
    intent = None
    field_count = 3
    if entry == INTENT_DECISION_ENTRY:
        historical = _read_scale_intent(txn, definition)
        intent = historical.definition
        policy_default = intent.policy_default
        requested = read_field(b"implementation_override")
        chosen, implementation_reason = _resolve_intent_implementation(intent, requested)
        if chosen != request.implementation or implementation_reason != read_field(b"implementation_reason"):
            raise ValueError("intent decision does not match the resolved implementation")
        details = {"intent_commit": definition.hex(), "request_implementation": chosen.decode("ascii"),
                   "implementation_override": requested.decode("ascii"),
                   "implementation_reason": implementation_reason.decode("ascii"),
                   "as_known_then": _supersession_view(definition, chosen, historical.supersession)}
        if knowledge_commit is not None:
            knowledge = historical if knowledge_commit == definition else _read_scale_intent(txn, knowledge_commit)
            if knowledge.genesis != historical.genesis:
                raise ValueError("knowledge commit belongs to a different intent lineage")
            details["knowledge_view"] = _supersession_view(knowledge_commit, chosen, knowledge.supersession)
        field_count += 2
    else:
        policy_default, _ = _read_scale_policy(txn, definition)
        details = {"policy_commit": definition.hex()}
    override = read_field(b"override")
    _check_policy_override(override)
    reusing = parents == 3
    reason = _policy_reason(policy_default, override, selected=reusing)
    consulted = reusing or reason == b"default-no-selection"
    if count != field_count + int(not reusing) + int(consulted) or read_field(b"reason") != reason:
        raise ValueError(f"{label} decision fields do not match the resolved policy")
    report = {"commit": commit.hex(), "decision_id": identity.decode("ascii"), **details,
              "policy_default": policy_default.decode("ascii"), "override": override.decode("ascii"),
              "reason": reason.decode("ascii"), "action": "reuse-selected" if reusing else "execute-fresh",
              "plan_commit": plan.hex(), "request_commit": request.commit.hex(),
              "expected_main": expected_main.hex() if expected_main is not None else None}
    names = {MAIN}
    if not reusing:
        plan_ref = read_field(b"plan_ref")
        if intent is not None:
            names.update((intent.v1_selection_ref, intent.v2_selection_ref))
        if not REF_NAME.fullmatch(plan_ref) or plan_ref in names:
            raise ValueError(f"{label} decision has invalid or aliased ref names")
        report["plan_ref"] = plan_ref.decode("ascii")
    if consulted:
        slot = read_field(b"selection_ref")
        if intent is not None:
            if slot != _intent_slot(intent, chosen):
                raise ValueError("intent decision does not name the resolved selection slot")
        elif not REF_NAME.fullmatch(slot) or slot == MAIN or (not reusing and slot == plan_ref):
            raise ValueError(f"{label} decision has invalid or aliased ref names")
        report["selection_ref"] = slot.decode("ascii")
    if reusing:
        selection_commit = core.object_view_parent(view, 2)
        selection = _read_scale_selection(txn, selection_commit, expected_request=request)
        report.update(selection_commit=selection_commit.hex(), result_commit=selection.result.hex())
        if selection.attempt is not None:
            report.update(_attempt_identity(selection.attempt))
    else:
        _inspect_call(txn, request.sum_dag, SUM, (b"a", b"b"))
    return report


def _read_scale_attempt(txn, commit, *, expected_request=None):
    view, parents, entry, dag = _snapshot(txn, commit)
    if entry != ATTEMPT_ENTRY or parents != 2:
        raise ValueError("expected a scale-attempt-v1 commit with ordered request and result parents")
    attempt_id = _read_single_string(txn, dag, b"attempt_id", "scale attempt")
    _check_uuid4(attempt_id, "attempt ID")
    request_id = core.object_view_parent(view, 0)
    if expected_request is not None and request_id != expected_request.commit:
        raise ValueError("attempt does not retain the expected request commit")
    request = _read_request(txn, request_id) if expected_request is None else expected_request
    result = core.object_view_parent(view, 1)
    _inspect_snapshot(txn, result, expected_request=request)
    return _ScaleAttempt(commit, request, result, attempt_id)


def _selected_attempt(txn, pin, commit, *, expected_request=None):
    if core.txn_ref_get(txn, pin) != commit:
        raise ValueError("attempt ref does not point to the expected attempt commit")
    return _read_scale_attempt(txn, commit, expected_request=expected_request)


def _read_scale_selection(txn, commit, *, expected_request=None):
    snapshot = _snapshot(txn, commit)
    if snapshot[2] == ADOPTION_ENTRY:
        return _read_scale_adoption(txn, snapshot, expected_request)
    return _read_initial_selection(txn, snapshot, expected_request)


def _read_initial_selection(txn, snapshot, expected_request):
    view, parents, entry, dag = snapshot
    if entry not in (SELECTION_ENTRY, ATTEMPT_SELECTION_ENTRY):
        raise ValueError("expected a scale result or attempt selection commit")
    kind = "attempt" if entry == ATTEMPT_SELECTION_ENTRY else "result"
    if parents != 2:
        raise ValueError(f"expected a {entry.decode('ascii')} commit with ordered request and {kind} parents")
    historical_ref = _read_single_string(txn, dag, f"{kind}_ref".encode("ascii"), f"{kind} selection")
    if not REF_NAME.fullmatch(historical_ref) or historical_ref == MAIN:
        raise ValueError(f"{kind} selection has an invalid {kind} ref name")
    request_id = core.object_view_parent(view, 0)
    if expected_request is not None and request_id != expected_request.commit:
        raise ValueError("selection does not retain the expected request commit")
    request = _read_request(txn, request_id) if expected_request is None else expected_request
    target = core.object_view_parent(view, 1)
    if entry == ATTEMPT_SELECTION_ENTRY:
        attempt = _read_scale_attempt(txn, target, expected_request=request)
        return _ScaleSelection(request, attempt.result, historical_ref, attempt)
    _inspect_snapshot(txn, target, expected_request=request)
    return _ScaleSelection(request, target, historical_ref)


def _read_scale_adoption(txn, snapshot, expected_request):
    # Follow parents iteratively so the validity of a chain does not depend on
    # Python's recursion limit. Validate every version, not just the current choice.
    head = None
    newer_attempt = None
    while snapshot[2] == ADOPTION_ENTRY:
        view, parents, _, dag = snapshot
        if parents != 2:
            raise ValueError("expected a scale-attempt-adoption-v1 commit with ordered selection and attempt parents")
        historical_ref = _read_single_string(txn, dag, b"attempt_ref", "attempt adoption")
        if not REF_NAME.fullmatch(historical_ref) or historical_ref == MAIN:
            raise ValueError("attempt adoption has an invalid attempt ref name")
        previous = core.object_view_parent(view, 0)
        attempt = _read_scale_attempt(txn, core.object_view_parent(view, 1), expected_request=expected_request)
        if attempt.commit == newer_attempt:
            raise ValueError("adoption must change the selected attempt commit")
        if head is None:
            head = _ScaleSelection(attempt.request, attempt.result, historical_ref, attempt, previous)
        expected_request = attempt.request
        newer_attempt = attempt.commit
        snapshot = _snapshot(txn, previous)

    if snapshot[2] != ATTEMPT_SELECTION_ENTRY:
        raise ValueError("adoption history must start with an attempt selection")
    initial = _read_initial_selection(txn, snapshot, expected_request)
    if initial.attempt.commit == newer_attempt:
        raise ValueError("adoption must change the selected attempt commit")
    return head


def _attempt_identity(attempt):
    return {"attempt_commit": attempt.commit.hex(), "attempt_id": attempt.attempt_id.decode("ascii")}


def _inspect_reuse_publication(txn, commit, view, parents, dag, *, selected):
    if parents != 2:
        ends = "selection" if selected else "result"
        raise ValueError(f"reuse record must have ordered plan and {ends} parents")
    _, root, count = _object(txn, core.REC_DAG, dag)
    if count != 2 or root != core.txn_lookup_node(txn, dag, b"plan_ref"):
        raise ValueError("reuse record has the wrong DAG layout")
    plan_pin = _read_literal(txn, root, core.DATUM_STRING)
    input_field = b"selection_ref" if selected else b"result_ref"
    input_pin = _read_literal(txn, core.txn_lookup_node(txn, dag, input_field), core.DATUM_STRING)
    if not (REF_NAME.fullmatch(plan_pin) and REF_NAME.fullmatch(input_pin) and len({plan_pin, input_pin, MAIN}) == 3):
        raise ValueError("reuse record has invalid ref names")
    plan = core.object_view_parent(view, 0)
    target = core.object_view_parent(view, 1)
    request, expected_main = _read_plan(txn, plan)
    refs = {input_field.decode("ascii"): input_pin.decode("ascii")}
    if selected:
        selection = _read_scale_selection(txn, target, expected_request=request)
        result = selection.result
        refs["selection_commit"] = target.hex()
        if selection.attempt is not None:
            refs.update(_attempt_identity(selection.attempt))
    else:
        result = target
        _inspect_snapshot(txn, result, expected_request=request)
    return {
        "commit": commit.hex(), "publication_mode": "reuse",
        "plan_ref": plan_pin.decode("ascii"), "plan_commit": plan.hex(),
        **refs, "result_commit": result.hex(),
        "request_commit": request.commit.hex(),
        "expected_main": expected_main.hex() if expected_main is not None else None,
    }


def _inspect_snapshot(txn, commit, *, expected_request=None, knowledge_commit=None):
    snapshot = _snapshot(txn, commit)
    view, parents, entry, terminal = snapshot
    if knowledge_commit is not None and entry != INTENT_DECISION_ENTRY:
        raise ValueError("a knowledge commit requires an intent decision")
    if expected_request is not None and entry != REQUESTED_SCALE_ENTRY:
        raise ValueError("expected a requested-scale-v1 result commit")
    if entry in (REQUEST_ENTRY, PLAN_ENTRY):
        return _inspect_request(txn, commit, entry)
    report = {"commit": commit.hex()}
    if entry == POLICY_ENTRY:
        mode, previous = _read_scale_policy(txn, commit)
        report["policy_default"] = mode.decode("ascii")
        if previous is not None:
            report["previous_policy_commit"] = previous.hex()
        return report
    if entry in (INTENT_ENTRY, SUPERSESSION_ENTRY):
        version = _read_scale_intent(txn, commit)
        fields = {name.decode("ascii"): value.decode("ascii") for name, value in zip(INTENT_FIELDS, version.definition)}
        return {**report, **fields, "previous_intent_commit": version.previous.hex() if version.previous else None,
                "supersession": _supersession_report(version.supersession)}
    if entry in (DECISION_ENTRY, INTENT_DECISION_ENTRY):
        return _inspect_scale_decision(txn, commit, view, parents, entry, terminal, knowledge_commit=knowledge_commit)
    if entry == PUBLICATION_ENTRY:
        fields = _read_publication(txn, commit)
        return {**report, **{name.decode("ascii"): value.decode("ascii") for name, value in fields.items()}}
    if entry == ATTEMPT_ENTRY:
        attempt = _read_scale_attempt(txn, commit)
        return {**report, "request_commit": attempt.request.commit.hex(),
                "request_implementation": attempt.request.implementation.decode("ascii"),
                "result_commit": attempt.result.hex(), "attempt_id": attempt.attempt_id.decode("ascii")}
    if entry in (SELECTION_ENTRY, ATTEMPT_SELECTION_ENTRY, ADOPTION_ENTRY):
        selection = _read_scale_selection(txn, commit)
        report.update(request_commit=selection.request.commit.hex(),
                      request_implementation=selection.request.implementation.decode("ascii"),
                      result_commit=selection.result.hex())
        if selection.attempt is None:
            return {**report, "result_ref": selection.historical_ref.decode("ascii")}
        if selection.previous is not None:
            report["previous_selection_commit"] = selection.previous.hex()
        return {**report, **_attempt_identity(selection.attempt),
                "attempt_ref": selection.historical_ref.decode("ascii")}
    if entry in (REUSE_ENTRY, SELECTED_REUSE_ENTRY):
        return _inspect_reuse_publication(txn, commit, view, parents, terminal, selected=entry == SELECTED_REUSE_ENTRY)
    if entry == SUM_ENTRY:
        dag = _sum_dag(snapshot)
        summed, _ = _inspect_call(txn, dag, SUM, (b"a", b"b"))
        return {**report, "calls": [summed]}
    if not ((entry == ENTRY and parents == 0) or (entry in (SCALE_ENTRY, REQUESTED_SCALE_ENTRY) and parents == 1)):
        raise ValueError("expected a recorded or requested scale commit with its required parents")
    request = None
    if entry == REQUESTED_SCALE_ENTRY:
        parent = core.object_view_parent(view, 0)
        if expected_request is not None and expected_request.commit != parent:
            raise ValueError("result does not retain the expected request commit")
        request = expected_request if expected_request is not None else _read_request(txn, parent)
    implementation = SCALE_V1 if request is None else request.implementation
    scale, producer = _inspect_call(txn, terminal, implementation, (b"input", b"factor"), call_input=b"input")
    if entry == SCALE_ENTRY:
        parent = core.object_view_parent(view, 0)
        if _sum_dag(_snapshot(txn, parent)) != producer:
            raise ValueError("scale input DAG does not match the producer parent")
        report["producer_commit"] = parent.hex()
    if request is not None:
        if producer != request.sum_dag:
            raise ValueError("scale input DAG does not match the request's producer")
        if scale["arguments"]["factor"]["value"] != request.factor:
            raise ValueError("recorded factor does not match the request factor")
        report["request_commit"] = request.commit.hex()
        report["producer_commit"] = request.producer.hex()
    summed, _ = _inspect_call(txn, producer, SUM, (b"a", b"b"))
    return {**report, "calls": [summed, scale]}


def inspect(path, ref=MAIN, *, knowledge_commit=None):
    """Read the committed example graph, optionally with a separate intent knowledge view."""
    if knowledge_commit is not None:
        _check_commit_id(knowledge_commit, "knowledge commit")
    with _repository(path, create=False) as repo, _read_transaction(repo) as txn:
        return _inspect_snapshot(txn, core.txn_ref_get(txn, ref), knowledge_commit=knowledge_commit)


def _parse_commit_id(text, label="producer commit"):
    try:
        identifier = bytes.fromhex(text)
    except ValueError:
        identifier = b""
    if len(text) != 32 or len(identifier) != 16:
        raise ValueError(f"{label} must be a 32-digit hexadecimal ID")
    return identifier


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    writer = commands.add_parser("record", help="record two calls in a new repository")
    writer.add_argument("repo", type=Path)
    for name in ("a", "b", "factor"):
        writer.add_argument(name, type=int)
    producer = commands.add_parser("record-sum", help="record a sum and create its pin")
    producer.add_argument("repo", type=Path)
    producer.add_argument("pin")
    producer.add_argument("a", type=int)
    producer.add_argument("b", type=int)
    consumer = commands.add_parser("record-scale", help="scale the stored result of a pinned sum")
    consumer.add_argument("repo", type=Path)
    consumer.add_argument("producer_pin")
    consumer.add_argument("producer_commit")
    consumer.add_argument("result_ref")
    consumer.add_argument("factor", type=int)
    exporter = commands.add_parser("export-sum", help="export the exact pinned sum to a new bundle")
    exporter.add_argument("repo", type=Path)
    exporter.add_argument("pin")
    exporter.add_argument("producer_commit")
    exporter.add_argument("bundle", type=Path)
    stage = commands.add_parser("stage-input", help="stage a bundle under a new local pin")
    stage.add_argument("repo", type=Path)
    stage.add_argument("pin")
    stage.add_argument("bundle", type=Path)
    scale_exporter = commands.add_parser("export-scale", help="export the exact pinned scale to a new bundle")
    scale_exporter.add_argument("repo", type=Path)
    scale_exporter.add_argument("result_ref")
    scale_exporter.add_argument("result_commit")
    scale_exporter.add_argument("bundle", type=Path)
    attempt_exporter = commands.add_parser("export-scale-attempt", help="export an exact pinned attempt and result")
    attempt_exporter.add_argument("repo", type=Path)
    attempt_exporter.add_argument("attempt_ref")
    attempt_exporter.add_argument("attempt_commit")
    attempt_exporter.add_argument("bundle", type=Path)
    publisher = commands.add_parser("publish-scale", help="publish the selected scale and release its staging ref")
    publisher.add_argument("repo", type=Path)
    publisher.add_argument("returned")
    publisher.add_argument("result_commit")
    publisher.add_argument("producer_commit")
    publisher.add_argument("expected_factor", type=int, help="signed 64-bit factor from the source request")
    publisher.add_argument("expected_main", help="required current main commit ID, or '-' if main must be absent")
    planner = commands.add_parser("request-scale", help="pin a scale request and the current main expectation")
    planner.add_argument("repo", type=Path)
    planner.add_argument("producer_pin")
    planner.add_argument("producer_commit")
    planner.add_argument("plan_pin")
    planner.add_argument("factor", type=int)
    planner.add_argument("--implementation", default=SCALE_V1.decode("ascii"),
                         help="exact scale implementation version (default: %(default)s)")
    policy = commands.add_parser("define-scale-policy", help="pin a version of the scale intent default")
    policy.add_argument("repo", type=Path)
    policy.add_argument("policy_ref")
    policy.add_argument("policy_default", choices=("reuse-by-default", "execute-by-default"))
    policy.add_argument("--basis-ref")
    policy.add_argument("--basis-commit")
    policy_request = commands.add_parser("request-policy-scale", help="prepare fresh work or publish exact reuse")
    policy_request.add_argument("repo", type=Path)
    for name in ("producer_pin", "producer_commit", "policy_ref", "policy_commit", "plan_pin", "decision_ref"):
        policy_request.add_argument(name)
    policy_request.add_argument("factor", type=int)
    policy_request.add_argument("--implementation", default=SCALE_V1.decode("ascii"))
    policy_request.add_argument("--override", choices=("default", "fresh", "reuse-selected"), default="default")
    policy_request.add_argument("--selection", help="explicit slot for a reuse path")
    policy_request.add_argument("--selection-commit", help="expected slot commit; omit to expect absence")
    intent = commands.add_parser("define-scale-intent", help="pin a version of the scale implementation default")
    intent.add_argument("repo", type=Path)
    intent.add_argument("intent_ref")
    intent.add_argument("default_implementation")
    intent.add_argument("--reuse-default", choices=("reuse-by-default", "execute-by-default"))
    intent.add_argument("--v1-selection", help="v1 selection slot for an initial definition")
    intent.add_argument("--v2-selection", help="v2 selection slot for an initial definition")
    intent.add_argument("--basis-ref")
    intent.add_argument("--basis-commit")
    supersession = commands.add_parser("declare-scale-supersession", help="add an advisory declaration to an intent")
    supersession.add_argument("repo", type=Path)
    for name in ("basis_ref", "basis_commit", "output_ref", "predecessor", "successor", "reason",
                 "evidence_ref", "evidence_commit"):
        supersession.add_argument(name)
    intent_request = commands.add_parser("request-intent-scale", help="resolve an implementation before reuse")
    intent_request.add_argument("repo", type=Path)
    for name in ("producer_pin", "producer_commit", "intent_ref", "intent_commit", "plan_pin", "decision_ref"):
        intent_request.add_argument(name)
    intent_request.add_argument("factor", type=int)
    intent_request.add_argument("--implementation", default="default", help="override the pinned default version")
    intent_request.add_argument("--override", choices=("default", "fresh", "reuse-selected"), default="default")
    intent_request.add_argument("--selection-commit", help="expected commit in the resolved slot, or omit for absence")
    request_exporter = commands.add_parser("export-request", help="export only the portable request from a plan")
    request_exporter.add_argument("repo", type=Path)
    request_exporter.add_argument("plan_pin")
    request_exporter.add_argument("plan_commit")
    request_exporter.add_argument("bundle", type=Path)
    worker = commands.add_parser("work-scale", help="record a scale from the exact staged request")
    worker.add_argument("repo", type=Path)
    worker.add_argument("incoming")
    worker.add_argument("request_commit")
    worker.add_argument("result_ref")
    attempt_worker = commands.add_parser("work-scale-attempt", help="run a staged request and record its occurrence")
    attempt_worker.add_argument("repo", type=Path)
    for name in ("incoming", "request_commit", "attempt_ref", "attempt_id"):
        attempt_worker.add_argument(name)
    reuse = commands.add_parser("stage-reused-scale", help="stage a pinned local result for the exact request")
    reuse.add_argument("repo", type=Path)
    for name in ("plan_pin", "plan_commit", "result_pin", "result_commit", "dest_pin"):
        reuse.add_argument(name)
    requested_publisher = commands.add_parser("publish-requested-scale", help="publish and consume a staged plan")
    requested_publisher.add_argument("repo", type=Path)
    requested_publisher.add_argument("plan_pin")
    requested_publisher.add_argument("plan_commit")
    requested_publisher.add_argument("returned")
    requested_publisher.add_argument("result_commit")
    requested_publisher.add_argument("--receipt-ref", help="keep a source-local receipt for safe retries")
    reuse_publisher = commands.add_parser("publish-reused-scale", help="publish a pinned result and record reuse")
    reuse_publisher.add_argument("repo", type=Path)
    for name in ("plan_pin", "plan_commit", "result_pin", "result_commit", "reuse_ref"):
        reuse_publisher.add_argument(name)
    chooser = commands.add_parser("select-scale-result", help="retain a pinned result without publishing it")
    chooser.add_argument("repo", type=Path)
    for name in ("plan_pin", "plan_commit", "result_pin", "result_commit", "selection_ref"):
        chooser.add_argument(name)
    attempt_chooser = commands.add_parser("select-scale-attempt", help="retain a pinned attempt without publishing")
    attempt_chooser.add_argument("repo", type=Path)
    for name in ("plan_pin", "plan_commit", "attempt_ref", "attempt_commit", "selection_ref"):
        attempt_chooser.add_argument(name)
    adopter = commands.add_parser("adopt-scale-attempt", help="record a new version of an attempt selection")
    adopter.add_argument("repo", type=Path)
    for name in ("basis_ref", "basis_commit", "attempt_ref", "attempt_commit", "selection_ref"):
        adopter.add_argument(name)
    selection_publisher = commands.add_parser("publish-selected-scale", help="publish from a selection and record reuse")
    selection_publisher.add_argument("repo", type=Path)
    for name in ("plan_pin", "plan_commit", "selection_ref", "selection_commit", "reuse_ref"):
        selection_publisher.add_argument(name)
    abandon = commands.add_parser("abandon-scale-request", help="release the exact local plan without publishing")
    abandon.add_argument("repo", type=Path)
    abandon.add_argument("plan_pin")
    abandon.add_argument("plan_commit")
    release = commands.add_parser("release-input", help="release a staged sum retained by a recorded result")
    release.add_argument("repo", type=Path)
    release.add_argument("pin")
    release.add_argument("producer_commit")
    release.add_argument("result_ref")
    collector = commands.add_parser("collect", help="collect unreachable objects")
    collector.add_argument("repo", type=Path)
    reader = commands.add_parser("inspect", help="read recorded calls from a ref (default: main)")
    reader.add_argument("repo", type=Path)
    reader.add_argument("ref", nargs="?", default="main")
    reader.add_argument("--knowledge-commit", help="add a separate view from this exact intent version")
    args = parser.parse_args()
    try:
        if args.command == "record":
            print(record(args.repo, args.a, args.b, args.factor).hex())
        elif args.command == "record-sum":
            print(record_sum(args.repo, args.pin.encode("ascii"), args.a, args.b).hex())
        elif args.command == "record-scale":
            commit = record_scale(args.repo, args.producer_pin.encode("ascii"), _parse_commit_id(args.producer_commit),
                                  args.result_ref.encode("ascii"), args.factor)
            print(commit.hex())
        elif args.command == "export-sum":
            print(export_sum(args.repo, args.pin.encode("ascii"), _parse_commit_id(args.producer_commit),
                             args.bundle).hex())
        elif args.command == "stage-input":
            print(stage_input(args.repo, args.pin.encode("ascii"), args.bundle).hex())
        elif args.command == "export-scale":
            result = _parse_commit_id(args.result_commit, "result commit")
            print(export_scale(args.repo, args.result_ref.encode("ascii"), result, args.bundle).hex())
        elif args.command == "export-scale-attempt":
            attempt = _parse_commit_id(args.attempt_commit, "attempt commit")
            print(export_scale_attempt(args.repo, args.attempt_ref.encode("ascii"), attempt, args.bundle).hex())
        elif args.command == "publish-scale":
            result = _parse_commit_id(args.result_commit, "result commit")
            producer = _parse_commit_id(args.producer_commit)
            expected_main = None if args.expected_main == "-" else _parse_commit_id(
                args.expected_main, "expected main commit",
            )
            print(publish_scale(args.repo, args.returned.encode("ascii"), result, producer,
                                args.expected_factor, expected_main).hex())
        elif args.command == "request-scale":
            print(request_scale(args.repo, args.producer_pin.encode("ascii"), _parse_commit_id(args.producer_commit),
                                args.plan_pin.encode("ascii"), args.factor,
                                implementation=args.implementation.encode("utf-8")).hex())
        elif args.command == "define-scale-policy":
            basis_ref = args.basis_ref.encode("ascii") if args.basis_ref is not None else None
            basis_commit = (_parse_commit_id(args.basis_commit, "policy basis commit")
                            if args.basis_commit is not None else None)
            print(define_scale_policy(args.repo, args.policy_ref.encode("ascii"), args.policy_default.encode("ascii"),
                                      basis_ref=basis_ref, basis_commit=basis_commit).hex())
        elif args.command == "request-policy-scale":
            selection_ref = args.selection.encode("ascii") if args.selection is not None else None
            selection_commit = (_parse_commit_id(args.selection_commit, "selection commit")
                                if args.selection_commit is not None else None)
            decision = request_policy_scale(
                args.repo, args.producer_pin.encode("ascii"), _parse_commit_id(args.producer_commit),
                args.policy_ref.encode("ascii"), _parse_commit_id(args.policy_commit, "policy commit"),
                args.plan_pin.encode("ascii"), args.decision_ref.encode("ascii"), args.factor,
                implementation=args.implementation.encode("utf-8"), override=args.override.encode("ascii"),
                selection_ref=selection_ref, selection_commit=selection_commit,
            )
            print(decision.hex())
        elif args.command == "define-scale-intent":
            basis_commit = (_parse_commit_id(args.basis_commit, "intent basis commit")
                            if args.basis_commit is not None else None)
            definition = define_scale_intent(
                args.repo, args.intent_ref.encode("ascii"), args.default_implementation.encode("utf-8"),
                policy_default=args.reuse_default.encode("ascii") if args.reuse_default is not None else None,
                v1_selection_ref=args.v1_selection.encode("ascii") if args.v1_selection is not None else None,
                v2_selection_ref=args.v2_selection.encode("ascii") if args.v2_selection is not None else None,
                basis_ref=args.basis_ref.encode("ascii") if args.basis_ref is not None else None,
                basis_commit=basis_commit,
            )
            print(definition.hex())
        elif args.command == "declare-scale-supersession":
            declaration = declare_scale_supersession(
                args.repo, args.basis_ref.encode("ascii"), _parse_commit_id(args.basis_commit, "intent basis commit"),
                args.output_ref.encode("ascii"), args.predecessor.encode("utf-8"), args.successor.encode("utf-8"),
                args.reason.encode("utf-8"), args.evidence_ref.encode("ascii"),
                _parse_commit_id(args.evidence_commit, "evidence commit"),
            )
            print(declaration.hex())
        elif args.command == "request-intent-scale":
            selection_commit = (_parse_commit_id(args.selection_commit, "selection commit")
                                if args.selection_commit is not None else None)
            decision = request_intent_scale(
                args.repo, args.producer_pin.encode("ascii"), _parse_commit_id(args.producer_commit),
                args.intent_ref.encode("ascii"), _parse_commit_id(args.intent_commit, "intent commit"),
                args.plan_pin.encode("ascii"), args.decision_ref.encode("ascii"), args.factor,
                implementation=args.implementation.encode("utf-8"), override=args.override.encode("ascii"),
                selection_commit=selection_commit,
            )
            print(decision.hex())
        elif args.command == "export-request":
            plan = _parse_commit_id(args.plan_commit, "plan commit")
            print(export_request(args.repo, args.plan_pin.encode("ascii"), plan, args.bundle).hex())
        elif args.command == "work-scale":
            request = _parse_commit_id(args.request_commit, "request commit")
            print(work_scale(args.repo, args.incoming.encode("ascii"), request, args.result_ref.encode("ascii")).hex())
        elif args.command == "work-scale-attempt":
            request = _parse_commit_id(args.request_commit, "request commit")
            attempt = work_scale_attempt(args.repo, args.incoming.encode("ascii"), request,
                                         args.attempt_ref.encode("ascii"), args.attempt_id.encode("utf-8"))
            print(attempt.hex())
        elif args.command == "stage-reused-scale":
            plan = _parse_commit_id(args.plan_commit, "plan commit")
            result = _parse_commit_id(args.result_commit, "result commit")
            print(stage_reused_scale(args.repo, args.plan_pin.encode("ascii"), plan, args.result_pin.encode("ascii"),
                                     result, args.dest_pin.encode("ascii")).hex())
        elif args.command == "publish-requested-scale":
            plan = _parse_commit_id(args.plan_commit, "plan commit")
            result = _parse_commit_id(args.result_commit, "result commit")
            receipt = args.receipt_ref.encode("ascii") if args.receipt_ref is not None else None
            print(publish_requested_scale(args.repo, args.plan_pin.encode("ascii"), plan,
                                          args.returned.encode("ascii"), result, receipt_ref=receipt).hex())
        elif args.command == "publish-reused-scale":
            plan = _parse_commit_id(args.plan_commit, "plan commit")
            result = _parse_commit_id(args.result_commit, "result commit")
            print(publish_reused_scale(args.repo, args.plan_pin.encode("ascii"), plan, args.result_pin.encode("ascii"),
                                       result, args.reuse_ref.encode("ascii")).hex())
        elif args.command == "select-scale-result":
            plan = _parse_commit_id(args.plan_commit, "plan commit")
            result = _parse_commit_id(args.result_commit, "result commit")
            print(select_scale_result(args.repo, args.plan_pin.encode("ascii"), plan, args.result_pin.encode("ascii"),
                                      result, args.selection_ref.encode("ascii")).hex())
        elif args.command == "select-scale-attempt":
            plan = _parse_commit_id(args.plan_commit, "plan commit")
            attempt = _parse_commit_id(args.attempt_commit, "attempt commit")
            print(select_scale_attempt(args.repo, args.plan_pin.encode("ascii"), plan, args.attempt_ref.encode("ascii"),
                                       attempt, args.selection_ref.encode("ascii")).hex())
        elif args.command == "adopt-scale-attempt":
            basis = _parse_commit_id(args.basis_commit, "basis selection commit")
            attempt = _parse_commit_id(args.attempt_commit, "attempt commit")
            print(adopt_scale_attempt(args.repo, args.basis_ref.encode("ascii"), basis,
                                      args.attempt_ref.encode("ascii"), attempt, args.selection_ref.encode("ascii")).hex())
        elif args.command == "publish-selected-scale":
            plan = _parse_commit_id(args.plan_commit, "plan commit")
            selection = _parse_commit_id(args.selection_commit, "selection commit")
            result = publish_selected_scale(args.repo, args.plan_pin.encode("ascii"), plan,
                                            args.selection_ref.encode("ascii"), selection, args.reuse_ref.encode("ascii"))
            print(result.hex())
        elif args.command == "abandon-scale-request":
            plan = _parse_commit_id(args.plan_commit, "plan commit")
            print(abandon_scale_request(args.repo, args.plan_pin.encode("ascii"), plan).hex())
        elif args.command == "release-input":
            print(release_input(args.repo, args.pin.encode("ascii"), _parse_commit_id(args.producer_commit),
                                args.result_ref.encode("ascii")).hex())
        elif args.command == "collect":
            print(collect(args.repo))
        else:
            knowledge = (_parse_commit_id(args.knowledge_commit, "knowledge commit")
                         if args.knowledge_commit is not None else None)
            print(json.dumps(inspect(args.repo, args.ref.encode("ascii"), knowledge_commit=knowledge)))
    except (core.Error, OSError, ValueError) as error:
        parser.exit(1, f"{args.command}: {error}\n")


if __name__ == "__main__":
    main()
