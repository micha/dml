"""Compose recorded add and double calls, with explicit downstream result reuse."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

from daggerml import builtin, core

import recorded_builtins as layout
import recorded_calls as records
from recorded_calls import _put_literal as _literal


CONFIG = b"composition-example-config-v1"
REQUEST = b"composition-example-request-v1"
RESULT = b"composition-example-result-v1"
ATTEMPT = b"composition-example-attempt-v1"
COMPOSITION = b"composition-example-composition-v1"
DECISION = b"composition-example-decision-v1"
ADD = b"urn:example:node-add"
DOUBLE = b"urn:example:node-double"
FRESH, TRY, REQUIRE = b"fresh", b"try-selected", b"require-selected"
PENDING, REUSE = b"pending", b"reuse"
MAP_SOURCE = b"dml://source/builtin/map/get/v1"
LIST_SOURCE = b"dml://source/builtin/list/get/v1"


@dataclass(frozen=True)
class Request:
    commit: bytes
    func: bytes
    args: builtin.Arguments
    map_binding: builtin.Binding
    list_binding: builtin.Binding
    composition: Composition | None = None


@dataclass(frozen=True)
class Attempt:
    commit: bytes
    request: Request
    result: bytes
    output: builtin.Return


@dataclass(frozen=True)
class Composition:
    commit: bytes
    inputs: builtin.Arguments
    producer: Attempt


def _read_config(txn, inspector, commit):
    dag, parents = layout._snapshot(txn, commit, CONFIG)
    root = layout._shape(txn, dag, 3)
    if parents or root != layout._field(txn, dag, b"role") or layout._string(txn, root) != CONFIG:
        raise ValueError("invalid composition configuration")
    map_binding = inspector.binding(layout._target(txn, dag, b"map-get"))
    list_binding = inspector.binding(layout._target(txn, dag, b"list-get"))
    if (map_binding.source_uri, list_binding.source_uri) != (MAP_SOURCE, LIST_SOURCE):
        raise ValueError("configuration must pin the exact supported getter versions")
    return map_binding, list_binding


def define(path, config_ref):
    records._check_intent_refs(("configuration", config_ref))
    with records._write_transaction(path, create=True) as txn:
        root = _literal(txn, core.DATUM_STRING, CONFIG)
        dag = layout._put_dag(txn, root, {
            b"role": root,
            b"map-get": layout._link(txn, builtin.put_binding(txn, MAP_SOURCE)),
            b"list-get": layout._link(txn, builtin.put_binding(txn, LIST_SOURCE)),
        })
        return records._publish(txn, config_ref, CONFIG, dag)


def _check_arguments(args, func):
    names = (b"a", b"b") if func == ADD else (b"x",)
    if tuple(name for name, _ in args.entries) != names:
        raise ValueError("request does not have the exact named arguments for its func")
    for _, arg in args.entries:
        arg.value.as_i64()
        if func == ADD and type(arg) is not builtin.Description:
            raise ValueError("add arguments must be direct recorded literals")


def _read_request(txn, inspector, commit, expected_func=None):
    dag, parents = layout._snapshot(txn, commit, REQUEST)
    root = layout._shape(txn, dag, 3)
    func = records._read_literal(txn, root, core.DATUM_URI)
    if expected_func is not None and func != expected_func:
        raise ValueError("attempt has the wrong ordinary func")
    if len(parents) != 1 or root != layout._field(txn, dag, b"func") or func not in (ADD, DOUBLE):
        raise ValueError("invalid ordinary request shape or func")
    invocation = layout._string(txn, layout._field(txn, dag, b"invocation"))
    records._check_uuid4(invocation, "composition invocation ID")
    inputs = layout._target(txn, dag, b"inputs")
    if func == ADD:
        map_binding, list_binding = _read_config(txn, inspector, parents[0])
        args = inspector.arguments(inputs)
        _check_arguments(args, ADD)
        return Request(commit, func, args, map_binding, list_binding)
    composition = _read_composition(txn, inspector, parents[0])
    if inputs != composition.inputs.dag:
        raise ValueError("double request inputs do not match its composition")
    upstream = composition.producer.request
    return Request(commit, func, composition.inputs, upstream.map_binding, upstream.list_binding, composition)


def _validate_return(request, output):
    args = request.args
    if output.inputs.dag != args.dag or len(output.trace) != len(args.entries):
        raise ValueError("return does not own the exact request inputs and getter positions")
    for operation, (name, _) in zip(output.trace, args.entries, strict=True):
        sources = dict(operation.arguments.entries)
        if (operation.func_uri != builtin.MAP_GET or operation.binding != request.map_binding
                or sources[b"map"].dag != args.dag or type(sources[b"key"]) is not builtin.Description
                or sources[b"key"].value.payload != name):
            raise ValueError("getter trace does not match the exact request inputs and keys")
    values = tuple(arg.value.as_i64() for _, arg in args.entries)
    expected = values[0] + values[1] if request.func == ADD else 2 * values[0]
    if type(output.returned) is not builtin.Description or output.value.as_i64() != expected:
        raise ValueError("ordinary return is not the expected I64 literal")


def _read_attempt(txn, inspector, commit, expected_func=None):
    dag, parents = layout._snapshot(txn, commit, ATTEMPT)
    attempt_id = layout._string(txn, layout._shape(txn, dag, 0))
    records._check_uuid4(attempt_id, "composition attempt ID")
    if len(parents) != 2:
        raise ValueError("attempt must retain its own request and result")
    request = _read_request(txn, inspector, parents[0], expected_func)
    result = parents[1]
    returned, owner = layout._snapshot(txn, result, RESULT)
    if owner != (request.commit,):
        raise ValueError("result does not belong to the producing request")
    output = inspector.returned(returned)
    _validate_return(request, output)
    return Attempt(commit, request, result, output)


def _put_composition(txn, inputs_dag, producer_commit):
    root = _literal(txn, core.DATUM_STRING, producer_commit.hex().encode("ascii"))
    return layout._put_dag(txn, root, {b"producer": root, b"inputs": layout._link(txn, inputs_dag)})


def _read_composition(txn, inspector, commit):
    dag, parents = layout._snapshot(txn, commit, COMPOSITION)
    root = layout._shape(txn, dag, 2)
    if (len(parents) != 1 or root != layout._field(txn, dag, b"producer")
            or layout._string(txn, root) != parents[0].hex().encode("ascii")):
        raise ValueError("composition producer does not match its pinned attempt")
    producer = _read_attempt(txn, inspector, parents[0], ADD)
    inputs = inspector.arguments(layout._target(txn, dag, b"inputs"))
    _check_arguments(inputs, DOUBLE)
    if inputs.entries[0][1].dag != producer.output.dag:
        raise ValueError("composition input does not use the exact producer return DAG")
    return Composition(commit, inputs, producer)


def compose(path, upstream_ref, upstream, composition_ref):
    records._check_intent_refs(("upstream", upstream_ref), ("composition", composition_ref))
    with records._write_transaction(path, create=False) as txn:
        layout._pin(txn, upstream_ref, upstream, "upstream")
        producer = _read_attempt(txn, builtin.Inspector(txn), upstream, ADD)
        with builtin.Recorder(txn) as recorder:
            inputs = recorder.arguments({b"x": recorder.load(producer.output.dag)})
            dag = _put_composition(txn, recorder.dag(inputs), producer.commit)
        return records._publish(txn, composition_ref, COMPOSITION, dag, producer.commit)


def _put_request(txn, func, inputs, basis, invocation):
    root = _literal(txn, core.DATUM_URI, func)
    dag = layout._put_dag(txn, root, {
        b"func": root,
        b"inputs": layout._link(txn, inputs),
        b"invocation": _literal(txn, core.DATUM_STRING, invocation),
    })
    return records._put_snapshot(txn, REQUEST, dag, basis)


def request_add(path, config_ref, config, pending_ref, a, b, invocation):
    records._check_intent_refs(("configuration", config_ref), ("pending request", pending_ref))
    records._check_i64(a, "a")
    records._check_i64(b, "b")
    records._check_uuid4(invocation, "composition invocation ID")
    with records._write_transaction(path, create=False) as txn:
        layout._pin(txn, config_ref, config, "configuration")
        _read_config(txn, builtin.Inspector(txn), config)
        with builtin.Recorder(txn) as recorder:
            inputs = recorder.arguments({b"a": recorder.literal(core.DATUM_I64, a),
                                         b"b": recorder.literal(core.DATUM_I64, b)})
            request = _put_request(txn, ADD, recorder.dag(inputs), config, invocation)
        core.txn_ref_create(txn, pending_ref, request)
        return request


def _matches(composition, historical):
    # Both sides have already been checked against the fixed DOUBLE intent.
    return historical is not None and historical.request.args.datum == composition.inputs.datum


def request_double(path, composition_ref, composition, pending_ref, decision_ref, invocation, *,
                   mode=FRESH, selected_ref=None, selected=None):
    records._check_uuid4(invocation, "composition invocation ID")
    refs = [("composition", composition_ref), ("pending request", pending_ref), ("decision", decision_ref)]
    if mode not in (FRESH, TRY, REQUIRE):
        raise ValueError("unknown composition reuse mode")
    if mode != FRESH:
        if selected_ref is None:
            raise ValueError("reuse requires a selection ref and an exact commit or expected absence")
        refs.append(("selection", selected_ref))
    records._check_intent_refs(*refs)
    with records._write_transaction(path, create=False) as txn:
        inspector = builtin.Inspector(txn)
        layout._pin(txn, composition_ref, composition, "composition")
        source = _read_composition(txn, inspector, composition)
        historical = None
        if mode != FRESH and layout._pin(txn, selected_ref, selected, "selection") is not None:
            historical = _read_attempt(txn, inspector, selected, DOUBLE)
        hit = _matches(source, historical)
        if mode == REQUIRE and not hit:
            raise ValueError("no selected double attempt for the argument MAP")
        own = _put_request(txn, DOUBLE, source.inputs.dag, composition, invocation)
        if hit:
            if own == historical.request.commit:
                raise ValueError("reuse needs a new invocation ID, not the producing request")
            layout._pin(txn, pending_ref, None, "pending request")
            layout._main(txn, historical.result)
        else:
            core.txn_ref_create(txn, pending_ref, own)
        root = _literal(txn, core.DATUM_STRING, mode)
        dag = layout._put_dag(txn, root, {b"outcome": _literal(txn, core.DATUM_STRING, REUSE if hit else PENDING)})
        parents = (own,) if historical is None else (own, historical.commit)
        return records._publish(txn, decision_ref, DECISION, dag, *parents)


def _add(arguments, ops):
    a = ops.map_get(arguments, b"a").value.as_i64()
    b = ops.map_get(arguments, b"b").value.as_i64()
    return ops.literal(core.DATUM_I64, a + b)


def _double(arguments, ops):
    x = ops.map_get(arguments, b"x").value.as_i64()
    return ops.literal(core.DATUM_I64, x * 2)


def work(path, pending_ref, pending, attempt_ref, attempt_id):
    records._check_intent_refs(("pending request", pending_ref), ("attempt output", attempt_ref))
    records._check_uuid4(attempt_id, "composition attempt ID")
    with records._write_transaction(path, create=False) as txn:
        layout._pin(txn, pending_ref, pending, "request")
        request = _read_request(txn, builtin.Inspector(txn), pending)
        logical = _add if request.func == ADD else _double
        with builtin.Recorder(txn) as recorder:
            args = recorder.load(request.args.dag)
            ops = recorder.operations(map_binding=request.map_binding.dag, list_binding=request.list_binding.dag)
            returned = recorder.dag(recorder.returned(logical(args, ops), inputs=args))
        result = records._put_snapshot(txn, RESULT, returned, pending)
        identity = _literal(txn, core.DATUM_STRING, attempt_id)
        dag = layout._put_dag(txn, identity, {})
        layout._main(txn, result)
        return records._publish(txn, attempt_ref, ATTEMPT, dag, pending, result)


def _arguments_report(args):
    return {"inputs": args.dag.hex(), "argument_map": args.datum.hex(),
            "sources": {key.decode("ascii"): arg.dag.hex() for key, arg in args.entries}}


def _upstream_report(producer):
    return {"attempt": producer.commit.hex(), "request": producer.request.commit.hex(),
            "result": producer.result.hex(), "return_dag": producer.output.dag.hex(),
            "argument_map": producer.request.args.datum.hex()}


def _request_report(request):
    report = {"request": request.commit.hex(), "func": request.func.decode("ascii"),
              **_arguments_report(request.args)}
    composition = request.composition
    if composition is not None:
        report.update(composition=composition.commit.hex(), upstream=_upstream_report(composition.producer))
    return report


def _attempt_report(attempt):
    return {"attempt": attempt.commit.hex(), "result": attempt.result.hex(),
            "producing": _request_report(attempt.request), "return_dag": attempt.output.dag.hex(),
            "value": attempt.output.value.as_i64(),
            "trace": [layout._operation_report(operation) for operation in attempt.output.trace]}


def _decision_report(txn, inspector, commit):
    dag, parents = layout._snapshot(txn, commit, DECISION)
    mode = layout._string(txn, layout._shape(txn, dag, 1))
    outcome = layout._string(txn, layout._field(txn, dag, b"outcome"))
    if mode not in (FRESH, TRY, REQUIRE) or not parents or (mode == FRESH and len(parents) != 1):
        raise ValueError("invalid composition decision ancestry or mode")
    own = _read_request(txn, inspector, parents[0], DOUBLE)
    historical = _read_attempt(txn, inspector, parents[1], DOUBLE) if len(parents) == 2 else None
    hit = _matches(own.composition, historical)
    if outcome != (REUSE if hit else PENDING) or (mode == REQUIRE and not hit):
        raise ValueError("composition decision does not match its recorded selection")
    if hit and own.commit == historical.request.commit:
        raise ValueError("reuse needs a new invocation ID, not the producing request")
    report = {"requested": _request_report(own), "outcome": outcome.decode("ascii"),
              "selection": "" if historical is None else historical.commit.hex()}
    if hit:
        report.update(_attempt_report(historical))
    return report


def inspect(path, ref, expected=None):
    with records._repository(path, create=False) as repo, records._read_transaction(repo) as txn:
        commit = core.txn_ref_get(txn, ref) if expected is None else layout._pin(txn, ref, expected, "inspection")
        _, _, entry, _ = records._snapshot(txn, commit)
        inspector = builtin.Inspector(txn)
        if entry == DECISION:
            report = _decision_report(txn, inspector, commit)
        elif entry == ATTEMPT:
            report = _attempt_report(_read_attempt(txn, inspector, commit))
        elif entry == COMPOSITION:
            composition = _read_composition(txn, inspector, commit)
            report = {**_arguments_report(composition.inputs), "upstream": _upstream_report(composition.producer)}
        else:
            raise ValueError("inspect expects a composition, decision or attempt ref")
        return {"commit": commit.hex(), **report}


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    converters = dict.fromkeys(("config", "upstream", "composition", "pending"), layout._commit_id)
    converters.update(a=int, b=int)
    for name, handler, fields in (
        ("define", define, ("config_ref",)),
        ("request-add", request_add, ("config_ref", "config", "pending_ref", "a", "b")),
        ("work", work, ("pending_ref", "pending", "attempt_ref")),
        ("compose", compose, ("upstream_ref", "upstream", "composition_ref")),
        ("request-double", request_double, ("composition_ref", "composition", "pending_ref", "decision_ref")),
        ("inspect", inspect, ("ref",)),
    ):
        command = commands.add_parser(name)
        command.set_defaults(handler=handler)
        command.add_argument("path", type=Path)
        for field in fields:
            command.add_argument(field, type=converters.get(field, str.encode))
        if name in ("request-add", "request-double"):
            command.add_argument("--invocation", type=str.encode)
        if name == "request-double":
            command.add_argument("--mode", choices=(FRESH, TRY, REQUIRE), default=FRESH, type=str.encode)
            command.add_argument("--selected-ref", type=str.encode)
            command.add_argument("--selected", type=layout._commit_id)
        elif name == "work":
            command.add_argument("--attempt-id", type=str.encode)
        elif name == "inspect":
            command.add_argument("--expected", type=layout._commit_id)
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
    except (ValueError, OverflowError) as error:
        raise SystemExit(f"{name}: {error}") from error
    print(json.dumps(result, sort_keys=True) if isinstance(result, dict) else result.hex())


if __name__ == "__main__":
    main()
