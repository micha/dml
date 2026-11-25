"""Pin internal builtin versions and reuse a selected ordinary result by MAP value."""

import argparse
import json
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4

from daggerml import builtin, core

import recorded_calls as records


CHOICE = b"builtin-example-choice-v1"
REQUEST = b"builtin-example-request-v1"
RESULT = b"builtin-example-result-v1"
ATTEMPT = b"builtin-example-attempt-v1"
DECISION = b"builtin-example-decision-v1"
COMPAT = b"builtin-example-compat-v1"
SOURCES = {
    b"v1": b"dml://source/builtin/map/get/v1",
    b"v2": b"dml://source/builtin/map/get/v2",
    b"list": b"dml://source/builtin/list/get/v1",
}
VERSIONS = (b"v1", b"v2")
FRESH, TRY, REQUIRE = b"fresh", b"try-selected", b"require-selected"
PENDING, REUSE = b"pending", b"reuse"


class Attempt(NamedTuple):
    request: bytes
    result: bytes
    binding: builtin.Binding
    args: builtin.Arguments
    returned: builtin.Return
    value: int


def _put_dag(txn, root, fields):
    bindings = [part for item in fields.items() for part in item]
    return records._put_object(txn, core.REC_DAG, root, *bindings)


def _link(txn, dag):
    return records._put_object(txn, core.REC_NODE, core.NODE_SUBDAG, dag)


def _field(txn, dag, name):
    return core.txn_lookup_node(txn, dag, name)


def _target(txn, dag, name):
    return records._target(txn, _field(txn, dag, name), core.NODE_SUBDAG)


def _string(txn, node):
    return records._read_literal(txn, node, core.DATUM_STRING)


def _shape(txn, dag, expected):
    _, root, count = records._object(txn, core.REC_DAG, dag)
    if count != expected:
        raise ValueError("wrong builtin example DAG shape")
    return root


def _snapshot(txn, commit, entry):
    view, count, actual, dag = records._snapshot(txn, commit)
    if actual != entry or count > 2:
        raise ValueError(f"expected a {entry.decode('ascii')} commit")
    return dag, tuple(core.object_view_parent(view, i) for i in range(count))


def _pin(txn, ref, expected, label):
    records._check_ref_name(ref, label)
    if expected is not None:
        records._check_commit_id(expected, label)
    if records._optional_ref(txn, ref) != expected:
        raise ValueError(f"{label} ref does not match the expected commit or absence")
    return expected


def _main(txn, result):
    records._update_main(txn, result, records._optional_ref(txn, records.MAIN))


def _read_choice_fields(txn, inspect, dag):
    default = _string(txn, _shape(txn, dag, len(SOURCES)))
    bindings = {key: inspect.binding(_target(txn, dag, key)) for key in SOURCES}
    if any(binding.source_uri != SOURCES[key] for key, binding in bindings.items()):
        raise ValueError("choice does not retain its exact versioned bindings")
    return default, bindings


def _read_choice(txn, inspect, commit):
    dag, parents = _snapshot(txn, commit, CHOICE)
    default, bindings = _read_choice_fields(txn, inspect, dag)
    if default == b"v1" and not parents:
        return default, bindings
    if default == b"v2" and len(parents) == 1:
        basis, previous = _snapshot(txn, parents[0], CHOICE)
        if not previous and _read_choice_fields(txn, inspect, basis) == (b"v1", bindings):
            return default, bindings
    raise ValueError("choice must begin on v1 and may promote only once without changing bindings")


def _publish_choice(txn, ref, default, binds, *parents):
    root = records._put_literal(txn, core.DATUM_STRING, default)
    dag = _put_dag(txn, root, {key: _link(txn, bind) for key, bind in binds.items()})
    return records._publish(txn, ref, CHOICE, dag, *parents)


def define_choice(path, ref):
    records._check_intent_refs(("choice", ref))
    with records._write_transaction(path, create=True) as txn:
        return _publish_choice(txn, ref, b"v1", {key: builtin.put_binding(txn, uri) for key, uri in SOURCES.items()})


def promote(path, basis_ref, basis, ref):
    records._check_intent_refs(("basis choice", basis_ref), ("promoted choice", ref))
    with records._write_transaction(path, create=False) as txn:
        _pin(txn, basis_ref, basis, "basis choice")
        default, bindings = _read_choice(txn, builtin.Inspector(txn), basis)
        if default != b"v1":
            raise ValueError("only a v1 choice can be promoted")
        return _publish_choice(txn, ref, b"v2", {key: binding.dag for key, binding in bindings.items()}, basis)


def _resolve(default, bindings, override):
    label = default if override == b"" else override
    if label not in VERSIONS:
        raise ValueError("unsupported map/get version")
    return bindings[label]


def _prepare_input(txn, recorder, value, source):
    value_id = core.txn_put_datum(txn, core.datum_encode(core.DATUM_I64, value))
    if source == b"literal":
        items = recorder.literal(core.DATUM_LIST, (value_id,))
    elif source == b"named":
        native = records._put_literal(txn, core.DATUM_LIST, (value_id,))
        source_dag = _put_dag(txn, native, {b"items": native})
        items = recorder.source(source_dag, b"items")
    else:
        raise ValueError("expected literal or named list source")
    return recorder.arguments(((b"items", items),))


def _read_request(txn, inspect, commit):
    dag, parents = _snapshot(txn, commit, REQUEST)
    if len(parents) != 1:
        raise ValueError("request must retain its choice")
    default, bindings = _read_choice(txn, inspect, parents[0])
    invocation = _string(txn, _shape(txn, dag, 3))
    records._check_uuid4(invocation, "builtin invocation ID")
    override = _string(txn, _field(txn, dag, b"override"))
    binding = _resolve(default, bindings, override)
    args = inspect.arguments(_target(txn, dag, b"inputs"))
    if _target(txn, dag, b"map-get") != binding.dag:
        raise ValueError("request does not pin the resolved map/get binding")
    if len(args.entries) != 1 or args.entries[0][0] != b"items" or args.entries[0][1].value.kind != core.DATUM_LIST:
        raise ValueError("first requires one LIST argument named items")
    return binding, bindings[b"list"], args


def _checked_return(returned, map_binding, list_binding, args):
    if returned.inputs.dag != args.dag or len(returned.trace) != 2:
        raise ValueError("return does not own the request arguments and two getter positions")
    first, second = returned.trace
    pinned = ((builtin.MAP_GET, map_binding), (builtin.LIST_GET, list_binding))
    if tuple((operation.func_uri, operation.binding) for operation in returned.trace) != pinned:
        raise ValueError("return has the wrong pinned getter bindings")
    first_args, second_args = dict(first.arguments.entries), dict(second.arguments.entries)
    if (first_args[b"map"].dag != args.dag or first_args[b"key"].value.payload != b"items"
            or second_args[b"list"].dag != first.dag or second_args[b"index"].value.as_i64() != 0
            or returned.returned.dag != second.dag):
        raise ValueError("getter trace does not match the exact consumed source nodes")
    return returned.value.as_i64()


def _read_attempt(txn, inspect, attempt):
    dag, parents = _snapshot(txn, attempt, ATTEMPT)
    records._check_uuid4(_string(txn, _shape(txn, dag, 0)), "builtin attempt ID")
    if len(parents) != 2:
        raise ValueError("attempt must link its request and result")
    request, result = parents
    returned, owner = _snapshot(txn, result, RESULT)
    if owner != (request,):
        raise ValueError("result does not belong to the producing request")
    binding, list_binding, args = _read_request(txn, inspect, request)
    output = inspect.returned(returned)
    value = _checked_return(output, binding, list_binding, args)
    return Attempt(request, result, binding, args, output, value)


def request(path, choice_ref, choice, pending_ref, decision_ref, value, invocation, *,
            source=b"literal", override=b"", mode=FRESH, selected_ref=None, selected=None):
    records._check_i64(value, "list item")
    records._check_uuid4(invocation, "builtin invocation ID")
    if mode not in (FRESH, TRY, REQUIRE):
        raise ValueError("unknown builtin reuse mode")
    refs = [("choice", choice_ref), ("pending request", pending_ref), ("decision", decision_ref)]
    if mode != FRESH:
        if selected_ref is None:
            raise ValueError("reuse requires a selection ref and an exact commit or expected absence")
        refs.append(("selection", selected_ref))
    records._check_intent_refs(*refs)
    with records._write_transaction(path, create=False) as txn:
        inspect = builtin.Inspector(txn)
        _pin(txn, choice_ref, choice, "choice")
        default, bindings = _read_choice(txn, inspect, choice)
        binding = _resolve(default, bindings, override)
        producer = None
        if mode != FRESH and _pin(txn, selected_ref, selected, "selection") is not None:
            producer = _read_attempt(txn, inspect, selected)
        with builtin.Recorder(txn) as recorder:
            input_dag = recorder.dag(_prepare_input(txn, recorder, value, source))
        args = inspect.arguments(input_dag)
        hit = producer is not None and producer.args.datum == args.datum
        if mode == REQUIRE and not hit:
            raise ValueError("no selected attempt for the argument MAP")
        identity = records._put_literal(txn, core.DATUM_STRING, invocation)
        dag = _put_dag(txn, identity, {
            b"inputs": _link(txn, input_dag), b"map-get": _link(txn, binding.dag),
            b"override": records._put_literal(txn, core.DATUM_STRING, override),
        })
        own = records._put_snapshot(txn, REQUEST, dag, choice)
        if hit:
            _pin(txn, pending_ref, None, "pending request")
            _main(txn, producer.result)
        else:
            core.txn_ref_create(txn, pending_ref, own)
        root = records._put_literal(txn, core.DATUM_STRING, mode)
        route = records._put_literal(txn, core.DATUM_STRING, REUSE if hit else PENDING)
        decision = _put_dag(txn, root, {b"outcome": route})
        parents = (own, selected) if producer is not None else (own,)
        return records._publish(txn, decision_ref, DECISION, decision, *parents)


def _first(arguments, ops):
    return ops.list_get(ops.map_get(arguments, b"items"), 0)


def work(path, pending_ref, pending, attempt_ref, attempt_id):
    records._check_intent_refs(("pending request", pending_ref), ("attempt output", attempt_ref))
    records._check_uuid4(attempt_id, "builtin attempt ID")
    with records._write_transaction(path, create=False) as txn:
        _pin(txn, pending_ref, pending, "request")
        binding, list_binding, args = _read_request(txn, builtin.Inspector(txn), pending)
        with builtin.Recorder(txn) as recorder:
            inputs = recorder.load(args.dag)
            ops = recorder.operations(map_binding=binding.dag, list_binding=list_binding.dag)
            output = _first(inputs, ops)
            output.value.as_i64()
            returned = recorder.dag(recorder.returned(output, inputs=inputs))
        result = records._put_snapshot(txn, RESULT, returned, pending)
        identity = records._put_literal(txn, core.DATUM_STRING, attempt_id)
        attempt = _put_dag(txn, identity, {})
        _main(txn, result)
        return records._publish(txn, attempt_ref, ATTEMPT, attempt, pending, result)


def _compat_inputs(recorder, txn):
    empty_binding = builtin.put_binding(txn, b"dml://source/builtin/map/empty/v1")
    insert_binding = builtin.put_binding(txn, b"dml://source/builtin/map/insert/v1")
    empty = recorder.call(builtin.MAP_EMPTY, empty_binding, recorder.arguments(()))
    key = recorder.literal(core.DATUM_STRING, b"items")
    value = recorder.literal(core.DATUM_I64, 42)
    inserted = recorder.call(builtin.MAP_INSERT, insert_binding, recorder.arguments(
        ((b"map", empty), (b"key", key), (b"value", value))))
    return recorder.arguments(((b"map", inserted), (b"key", key)))


def compatibility(path, choice_ref, choice, output_ref):
    records._check_intent_refs(("choice", choice_ref), ("compatibility output", output_ref))
    with records._write_transaction(path, create=False) as txn:
        _pin(txn, choice_ref, choice, "choice")
        default, bindings = _read_choice(txn, builtin.Inspector(txn), choice)
        if default != b"v2":
            raise ValueError("compatibility controls require the promoted choice")
        with builtin.Recorder(txn) as recorder:
            args = _compat_inputs(recorder, txn)
            calls = {v: _link(txn, recorder.dag(recorder.call(builtin.MAP_GET, bindings[v].dag, args)))
                     for v in VERSIONS}
        root = records._put_literal(txn, core.DATUM_STRING, b"map/get compatibility")
        return records._publish(txn, output_ref, COMPAT, _put_dag(txn, root, calls), choice)


def _request_report(commit, binding, args):
    return {"request": commit.hex(), "binding": binding.source_uri.decode("ascii"),
            "inputs": args.dag.hex(), "argument_map": args.datum.hex(), "source": args.entries[0][1].dag.hex()}


def _operation_report(operation):
    return {"operation": operation.dag.hex(), "func": operation.func_uri.decode("ascii"),
            "binding": operation.binding.source_uri.decode("ascii"), "inputs": operation.arguments.dag.hex(),
            "datum": operation.datum.hex(),
            "sources": {key.decode("ascii"): arg.dag.hex() for key, arg in operation.arguments.entries}}


def _attempt_report(commit, attempt):
    return {"attempt": commit.hex(), "result": attempt.result.hex(), "value": attempt.value,
            "producing": _request_report(attempt.request, attempt.binding, attempt.args),
            "returned": attempt.returned.returned.dag.hex(),
            "trace": [_operation_report(op) for op in attempt.returned.trace]}


def _decision_report(txn, inspector, commit):
    dag, parents = _snapshot(txn, commit, DECISION)
    root = _shape(txn, dag, 1)
    mode, outcome = _string(txn, root), _string(txn, _field(txn, dag, b"outcome"))
    if (mode not in (FRESH, TRY, REQUIRE) or not parents or (mode == FRESH and len(parents) != 1)):
        raise ValueError("invalid builtin decision ancestry or mode")
    request = parents[0]
    binding, _, args = _read_request(txn, inspector, request)
    selected = parents[1] if len(parents) == 2 else None
    historical = _read_attempt(txn, inspector, selected) if selected is not None else None
    hit = historical is not None and historical.args.datum == args.datum
    if outcome != (REUSE if hit else PENDING) or (mode == REQUIRE and not hit):
        raise ValueError("builtin decision does not match its recorded selection")
    report = {"outcome": outcome.decode("ascii"), "requested": _request_report(request, binding, args),
              "selection": selected.hex() if selected is not None else ""}
    if hit:
        report.update(_attempt_report(selected, historical))
    return report


def _compat_report(txn, inspector, commit):
    dag, parents = _snapshot(txn, commit, COMPAT)
    if (len(parents) != 1 or _string(txn, _shape(txn, dag, len(VERSIONS))) != b"map/get compatibility"):
        raise ValueError("invalid compatibility record")
    default, bindings = _read_choice(txn, inspector, parents[0])
    v1, v2 = (inspector.operation(_target(txn, dag, label)) for label in VERSIONS)
    if (default != b"v2" or v1.func_uri != builtin.MAP_GET or v2.func_uri != builtin.MAP_GET
            or (v1.binding, v2.binding) != (bindings[b"v1"], bindings[b"v2"])
            or v1.arguments.dag != v2.arguments.dag or v1.datum != v2.datum):
        raise ValueError("compatibility calls do not retain the same arguments and exact versions")
    inserted = inspector.operation(dict(v1.arguments.entries)[b"map"].dag)
    if inserted.func_uri != builtin.MAP_INSERT:
        raise ValueError("compatibility map must come from map/insert")
    empty = inspector.operation(dict(inserted.arguments.entries)[b"map"].dag)
    if empty.func_uri != builtin.MAP_EMPTY:
        raise ValueError("compatibility insertion must start from map/empty")
    return {"value": v1.value.as_i64(), "trace": [_operation_report(op) for op in (empty, inserted, v1, v2)]}


def inspect(path, ref):
    with records._repository(path, create=False) as repo, records._read_transaction(repo) as txn:
        commit = core.txn_ref_get(txn, ref)
        _, _, entry, _ = records._snapshot(txn, commit)
        inspector = builtin.Inspector(txn)
        if entry == DECISION:
            report = _decision_report(txn, inspector, commit)
        elif entry == ATTEMPT:
            report = _attempt_report(commit, _read_attempt(txn, inspector, commit))
        elif entry == COMPAT:
            report = _compat_report(txn, inspector, commit)
        else:
            raise ValueError("inspect expects a builtin decision, attempt or compatibility ref")
        return {"commit": commit.hex(), **report}


def _commit_id(value):
    if len(value) != 32 or value.lower() != value:
        raise argparse.ArgumentTypeError("expected a 32-digit lowercase commit ID")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected a hexadecimal commit ID") from error
    if len(decoded) != 16:
        raise argparse.ArgumentTypeError("expected a 32-digit hexadecimal commit ID")
    return decoded


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name, handler, fields in (
        ("define-choice", define_choice, ("ref",)),
        ("promote", promote, ("basis_ref", "basis", "ref")),
        ("compatibility", compatibility, ("choice_ref", "choice", "output_ref")),
        ("request", request, ("choice_ref", "choice", "pending_ref", "decision_ref", "value")),
        ("work", work, ("pending_ref", "pending", "attempt_ref")),
        ("inspect", inspect, ("ref",)),
    ):
        sub = subcommands.add_parser(name)
        sub.set_defaults(handler=handler)
        sub.add_argument("path", type=Path)
        for field in fields:
            converters = {"choice": _commit_id, "basis": _commit_id, "pending": _commit_id, "value": int}
            sub.add_argument(field, type=converters.get(field, str.encode))
        if name == "request":
            sub.add_argument("--source", type=str.encode, choices=(b"literal", b"named"), default=b"literal")
            sub.add_argument("--version", dest="override", type=str.encode, default=b"")
            sub.add_argument("--mode", type=str.encode, choices=(FRESH, TRY, REQUIRE), default=FRESH)
            sub.add_argument("--selected-ref", type=str.encode)
            sub.add_argument("--selected", type=_commit_id)
            sub.add_argument("--invocation", type=str.encode)
        elif name == "work":
            sub.add_argument("--attempt-id", type=str.encode)
    return parser


def main():
    args = vars(_parser().parse_args())
    name, handler = args.pop("command"), args.pop("handler")
    for field in ("invocation", "attempt_id"):
        if field in args and args[field] is None:
            args[field] = str(uuid4()).encode("ascii")
    try:
        result = handler(**args)
    except core.Error as error:
        status, _, detail = error.args
        raise SystemExit(f"{name}: {status}: {detail}") from error
    except ValueError as error:
        raise SystemExit(f"{name}: {error}") from error
    print(json.dumps(result, sort_keys=True) if isinstance(result, dict) else result.hex())


if __name__ == "__main__":
    main()
