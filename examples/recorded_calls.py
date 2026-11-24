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
of the same request without changing the result's identity.
These layouts are not core record types or execution APIs.
"""

import argparse
from contextlib import contextmanager
import json
from operator import add, mul
from pathlib import Path
import re
from typing import NamedTuple

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
SELECTED_REUSE_ENTRY = b"recorded-selected-scale-reuse-v1"
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


def _check_attempt_id(attempt_id):
    if type(attempt_id) is not bytes or not UUID4.fullmatch(attempt_id):
        raise ValueError("attempt ID must be a canonical lowercase UUIDv4 in bytes")


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
        operation = _put_literal(txn, core.DATUM_STRING, implementation)
        multiplier = _put_literal(txn, core.DATUM_I64, factor)
        dag = _put_object(txn, core.REC_DAG, operation, b"implementation", operation, b"factor", multiplier)
        tree = _put_object(txn, core.REC_TREE, REQUEST_ENTRY, dag)
        request = _put_object(txn, core.REC_COMMIT, tree, producer_commit)
        if expected_main == request:
            raise ValueError("main already points to this request; stage requests under a separate ref")
        parents = (request,) if expected_main is None else (request, expected_main)
        return _publish(txn, plan_pin, PLAN_ENTRY, dag, *parents)


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
    _check_attempt_id(attempt_id)
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


def _read_scale_attempt(txn, commit, *, expected_request=None):
    view, parents, entry, dag = _snapshot(txn, commit)
    if entry != ATTEMPT_ENTRY or parents != 2:
        raise ValueError("expected a scale-attempt-v1 commit with ordered request and result parents")
    attempt_id = _read_single_string(txn, dag, b"attempt_id", "scale attempt")
    _check_attempt_id(attempt_id)
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
    view, parents, entry, dag = _snapshot(txn, commit)
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


def _inspect_snapshot(txn, commit, *, expected_request=None):
    snapshot = _snapshot(txn, commit)
    view, parents, entry, terminal = snapshot
    if expected_request is not None and entry != REQUESTED_SCALE_ENTRY:
        raise ValueError("expected a requested-scale-v1 result commit")
    if entry in (REQUEST_ENTRY, PLAN_ENTRY):
        return _inspect_request(txn, commit, entry)
    report = {"commit": commit.hex()}
    if entry == PUBLICATION_ENTRY:
        fields = _read_publication(txn, commit)
        return {**report, **{name.decode("ascii"): value.decode("ascii") for name, value in fields.items()}}
    if entry == ATTEMPT_ENTRY:
        attempt = _read_scale_attempt(txn, commit)
        return {**report, "request_commit": attempt.request.commit.hex(),
                "request_implementation": attempt.request.implementation.decode("ascii"),
                "result_commit": attempt.result.hex(), "attempt_id": attempt.attempt_id.decode("ascii")}
    if entry in (SELECTION_ENTRY, ATTEMPT_SELECTION_ENTRY):
        selection = _read_scale_selection(txn, commit)
        report.update(request_commit=selection.request.commit.hex(),
                      request_implementation=selection.request.implementation.decode("ascii"),
                      result_commit=selection.result.hex())
        if selection.attempt is None:
            return {**report, "result_ref": selection.historical_ref.decode("ascii")}
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


def inspect(path, ref=MAIN):
    """Read the committed example graph without executing or verifying arithmetic."""
    with _repository(path, create=False) as repo, _read_transaction(repo) as txn:
        return _inspect_snapshot(txn, core.txn_ref_get(txn, ref))


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
            print(json.dumps(inspect(args.repo, args.ref.encode("ascii"))))
    except (core.Error, OSError, ValueError) as error:
        parser.exit(1, f"{args.command}: {error}\n")


if __name__ == "__main__":
    main()
