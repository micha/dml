"""Record a scaled-sum closure, separating captured dependencies from inputs."""

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


DEFAULTS = b"closure-example-defaults-v1"
CLOSURE = b"closure-example-closure-v1"
ENVIRONMENT = b"closure-example-environment-v1"
CAPTURE_KEY = b"closure-example-capture-key-v1"
REQUEST = b"closure-example-request-v1"
DECISION = b"closure-example-decision-v1"
ATTEMPT = b"closure-example-attempt-v1"
RESULT = b"closure-example-result-v1"
FUNC = b"urn:example:captured-scaled-sum"
IMPLEMENTATION = b"scaled-sum-python-v1"
FRESH, TRY, REQUIRE = b"fresh", b"try-selected", b"require-selected"
PENDING, REUSE = b"pending", b"reuse"
MAP_SOURCES = {1: layout.SOURCES[b"v1"], 2: layout.SOURCES[b"v2"]}
LIST_SOURCE = layout.SOURCES[b"list"]


@dataclass(frozen=True)
class Environment:
    dag: bytes
    map_binding: builtin.Binding
    list_binding: builtin.Binding
    scale: builtin.LiteralSource
    origin: bytes


@dataclass(frozen=True)
class Closure:
    commit: bytes
    dag: bytes
    defaults: bytes
    environment: Environment
    key: bytes


@dataclass(frozen=True)
class Request:
    commit: bytes
    closure: Closure
    args: builtin.Arguments


@dataclass(frozen=True)
class Attempt:
    commit: bytes
    request: Request
    result: bytes
    output: builtin.Return


def _put_role(txn, role, fields):
    root = _literal(txn, core.DATUM_STRING, role)
    return layout._put_dag(txn, root, {b"role": root, **fields})


def _check_role(txn, dag, role, count):
    root = layout._shape(txn, dag, count)
    if root != layout._field(txn, dag, b"role") or layout._string(txn, root) != role:
        raise ValueError(f"expected a {role.decode('ascii')} DAG")


def _pin_literal(txn, commit):
    return _literal(txn, core.DATUM_STRING, b"" if commit is None else commit.hex().encode("ascii"))


def _check_pin(txn, dag, field, commit):
    expected = b"" if commit is None else commit.hex().encode("ascii")
    if layout._string(txn, layout._field(txn, dag, field)) != expected:
        raise ValueError(f"{field.decode('ascii')} pin does not match the actual parent")


def _read_defaults(txn, inspector, commit):
    dag, parents = layout._snapshot(txn, commit, DEFAULTS)
    if len(parents) > 1:
        raise ValueError("defaults must have at most one predecessor")
    _check_role(txn, dag, ENVIRONMENT, 4)
    map_binding = inspector.binding(layout._target(txn, dag, b"map-get"))
    list_binding = inspector.binding(layout._target(txn, dag, b"list-get"))
    if map_binding.source_uri not in MAP_SOURCES.values() or list_binding.source_uri != LIST_SOURCE:
        raise ValueError("unsupported captured getter binding")
    scale = inspector.node(layout._target(txn, dag, b"scale"))
    scale.value.as_i64()
    if type(scale) is not builtin.LiteralSource or scale.name != b"value":
        raise ValueError("expected a named scale source")
    if layout._shape(txn, scale.source_dag, 2) != scale.source_node:
        raise ValueError("wrong root in scale source")
    origin = layout._string(txn, layout._field(txn, scale.source_dag, b"origin"))
    return Environment(dag, map_binding, list_binding, scale, origin)


def defaults(path, ref, map_version, scale, origin, *, expected=None):
    records._check_intent_refs(("defaults", ref))
    records._check_i64(scale, "captured scale")
    if type(map_version) is not int or map_version not in MAP_SOURCES:
        raise ValueError("map getter version must be 1 or 2")
    with records._write_transaction(path, create=expected is None) as txn:
        layout._pin(txn, ref, expected, "defaults")
        if expected is not None:
            _read_defaults(txn, builtin.Inspector(txn), expected)
        value = _literal(txn, core.DATUM_I64, scale)
        source = layout._put_dag(txn, value, {
            b"value": value, b"origin": _literal(txn, core.DATUM_STRING, origin),
        })
        with builtin.Recorder(txn) as recorder:
            scale_dag = recorder.dag(recorder.source(source, b"value"))
        env = _put_role(txn, ENVIRONMENT, {
            b"map-get": layout._link(txn, builtin.put_binding(txn, MAP_SOURCES[map_version])),
            b"list-get": layout._link(txn, builtin.put_binding(txn, LIST_SOURCE)),
            b"scale": layout._link(txn, scale_dag),
        })
        if expected is None:
            return records._publish(txn, ref, DEFAULTS, env)
        commit = records._put_snapshot(txn, DEFAULTS, env, expected)
        core.txn_ref_update(txn, ref, commit)
        return commit


def _put_key(txn, env):
    return _put_role(txn, CAPTURE_KEY, {
        b"map-get": _literal(txn, core.DATUM_URI, builtin.MAP_GET),
        b"list-get": _literal(txn, core.DATUM_URI, builtin.LIST_GET),
        b"scale": records._put_object(txn, core.REC_NODE, core.NODE_LITERAL, env.scale.datum),
    })


def _check_key(txn, key, env):
    _check_role(txn, key, CAPTURE_KEY, 4)
    for name, func in ((b"map-get", builtin.MAP_GET), (b"list-get", builtin.LIST_GET)):
        if records._read_literal(txn, layout._field(txn, key, name), core.DATUM_URI) != func:
            raise ValueError("capture key does not match the builtin funcs")
    if records._target(txn, layout._field(txn, key, b"scale"), core.NODE_LITERAL) != env.scale.datum:
        raise ValueError("capture key does not match the typed scale datum")


def capture(path, defaults_ref, defaults_commit, closure_ref):
    records._check_intent_refs(("defaults", defaults_ref), ("closure", closure_ref))
    with records._write_transaction(path, create=False) as txn:
        layout._pin(txn, defaults_ref, defaults_commit, "defaults")
        env = _read_defaults(txn, builtin.Inspector(txn), defaults_commit)
        dag = _put_role(txn, CLOSURE, {
            b"func": _literal(txn, core.DATUM_URI, FUNC),
            b"implementation": _literal(txn, core.DATUM_STRING, IMPLEMENTATION),
            b"environment": layout._link(txn, env.dag),
            b"capture-key": layout._link(txn, _put_key(txn, env)),
        })
        return records._publish(txn, closure_ref, CLOSURE, dag, defaults_commit)


def _read_closure(txn, inspector, commit):
    dag, parents = layout._snapshot(txn, commit, CLOSURE)
    _check_role(txn, dag, CLOSURE, 5)
    if len(parents) != 1:
        raise ValueError("closure must retain its pinned defaults")
    func = records._read_literal(txn, layout._field(txn, dag, b"func"), core.DATUM_URI)
    implementation = layout._string(txn, layout._field(txn, dag, b"implementation"))
    if (func, implementation) != (FUNC, IMPLEMENTATION):
        raise ValueError("unsupported closure func or implementation")
    env = _read_defaults(txn, inspector, parents[0])
    if layout._target(txn, dag, b"environment") != env.dag:
        raise ValueError("closure environment does not match its pinned defaults")
    key = layout._target(txn, dag, b"capture-key")
    _check_key(txn, key, env)
    return Closure(commit, dag, parents[0], env, key)


def _input_values(args):
    if tuple(name for name, _ in args.entries) != (b"a", b"b"):
        raise ValueError("scaled sum requires exactly the I64 arguments a and b")
    return tuple(source.value.as_i64() for _, source in args.entries)


def _put_request(txn, closure, inputs, invocation):
    root = _literal(txn, core.DATUM_URI, FUNC)
    dag = layout._put_dag(txn, root, {
        b"func": root, b"invocation": _literal(txn, core.DATUM_STRING, invocation),
        b"closure": _pin_literal(txn, closure), b"inputs": layout._link(txn, inputs),
    })
    return records._put_snapshot(txn, REQUEST, dag, closure)


def _read_request(txn, inspector, commit):
    dag, parents = layout._snapshot(txn, commit, REQUEST)
    root = layout._shape(txn, dag, 4)
    if (len(parents) != 1 or root != layout._field(txn, dag, b"func")
            or records._read_literal(txn, root, core.DATUM_URI) != FUNC):
        raise ValueError("request must retain a closure for the fixed scaled sum func")
    _check_pin(txn, dag, b"closure", parents[0])
    records._check_uuid4(layout._string(txn, layout._field(txn, dag, b"invocation")), "closure invocation ID")
    closure = _read_closure(txn, inspector, parents[0])
    args = inspector.arguments(layout._target(txn, dag, b"inputs"))
    _input_values(args)
    return Request(commit, closure, args)


def _scaled_value(a, b, scale):
    total = a + b
    records._check_i64(total, "scaled sum subtotal")
    product = total * scale
    records._check_i64(product, "scaled sum product")
    return product


def _check_return(own, output):
    env = own.closure.environment
    args = own.args
    if output.inputs.dag != args.dag or len(output.trace) != 2:
        raise ValueError("return must own the exact invocation and two getters")
    for operation, (name, _) in zip(output.trace, args.entries, strict=True):
        sources = dict(operation.arguments.entries)
        if (operation.func_uri != builtin.MAP_GET or operation.binding != env.map_binding
                or sources[b"map"].dag != args.dag or type(sources[b"key"]) is not builtin.Description
                or sources[b"key"].value.payload != name):
            raise ValueError("getter trace does not match the captured binding, inputs and keys")
    a, b = _input_values(args)
    expected = _scaled_value(a, b, env.scale.value.as_i64())
    if type(output.returned) is not builtin.Description or output.value.as_i64() != expected:
        raise ValueError("return is not the expected I64 scaled sum literal")


def _read_attempt(txn, inspector, commit):
    dag, parents = layout._snapshot(txn, commit, ATTEMPT)
    records._check_uuid4(layout._string(txn, layout._shape(txn, dag, 0)), "closure attempt ID")
    if len(parents) != 2:
        raise ValueError("attempt must retain its own request and result")
    own = _read_request(txn, inspector, parents[0])
    result = parents[1]
    returned, owner = layout._snapshot(txn, result, RESULT)
    if owner != (own.commit,):
        raise ValueError("result does not belong to the producing request")
    output = inspector.returned(returned)
    _check_return(own, output)
    return Attempt(commit, own, result, output)


def _matches(closure, args, producer):
    # The readers already enforce the fixed func and implementation for both requests.
    if producer is None:
        return False
    past = producer.request
    return closure.key == past.closure.key and args.datum == past.args.datum


def _publish_decision(txn, ref, own, mode, producer, hit):
    selected = None if producer is None else producer.commit
    root = _literal(txn, core.DATUM_STRING, mode)
    dag = layout._put_dag(txn, root, {
        b"outcome": _literal(txn, core.DATUM_STRING, REUSE if hit else PENDING),
        b"request": _pin_literal(txn, own), b"selection": _pin_literal(txn, selected),
    })
    parents = (own,) if selected is None else (own, selected)
    return records._publish(txn, ref, DECISION, dag, *parents)


def request(path, closure_ref, closure_commit, pending_ref, decision_ref, a, b, invocation, *,
            mode=FRESH, selected_ref=None, selected=None):
    records._check_i64(a, "a")
    records._check_i64(b, "b")
    records._check_uuid4(invocation, "closure invocation ID")
    refs = [("closure", closure_ref), ("pending request", pending_ref), ("decision", decision_ref)]
    if mode not in (FRESH, TRY, REQUIRE):
        raise ValueError("unknown closure reuse mode")
    if mode != FRESH:
        if selected_ref is None:
            raise ValueError("reuse requires a selection ref and an exact commit or expected absence")
        refs.append(("selection", selected_ref))
    records._check_intent_refs(*refs)
    with records._write_transaction(path, create=False) as txn:
        inspector = builtin.Inspector(txn)
        layout._pin(txn, closure_ref, closure_commit, "closure")
        closure = _read_closure(txn, inspector, closure_commit)
        producer = None
        if mode != FRESH and layout._pin(txn, selected_ref, selected, "selection") is not None:
            producer = _read_attempt(txn, inspector, selected)
        with builtin.Recorder(txn) as recorder:
            inputs = recorder.arguments({b"a": recorder.literal(core.DATUM_I64, a),
                                         b"b": recorder.literal(core.DATUM_I64, b)})
            input_dag = recorder.dag(inputs)
        hit = _matches(closure, inspector.arguments(input_dag), producer)
        if mode == REQUIRE and not hit:
            raise ValueError("no selected attempt for the capture key and argument MAP")
        own = _put_request(txn, closure.commit, input_dag, invocation)
        if hit:
            if own == producer.request.commit:
                raise ValueError("reuse needs a new invocation ID, not the producing request")
            layout._pin(txn, pending_ref, None, "pending request")
            layout._main(txn, producer.result)
        else:
            core.txn_ref_create(txn, pending_ref, own)
        return _publish_decision(txn, decision_ref, own, mode, producer, hit)


def _bind_scaled_sum(scale, ops):
    def scaled_sum(arguments):
        a = ops.map_get(arguments, b"a").value.as_i64()
        b = ops.map_get(arguments, b"b").value.as_i64()
        return ops.literal(core.DATUM_I64, _scaled_value(a, b, scale.value.as_i64()))

    return scaled_sum


def work(path, pending_ref, pending, attempt_ref, attempt_id):
    records._check_intent_refs(("pending request", pending_ref), ("attempt output", attempt_ref))
    records._check_uuid4(attempt_id, "closure attempt ID")
    with records._write_transaction(path, create=False) as txn:
        layout._pin(txn, pending_ref, pending, "request")
        own = _read_request(txn, builtin.Inspector(txn), pending)
        env = own.closure.environment
        with builtin.Recorder(txn) as recorder:
            args = recorder.load(own.args.dag)
            scale = recorder.load(env.scale.dag)
            ops = recorder.operations(map_binding=env.map_binding.dag, list_binding=env.list_binding.dag)
            scaled_sum = _bind_scaled_sum(scale, ops)
            returned = recorder.dag(recorder.returned(scaled_sum(args), inputs=args))
        result = records._put_snapshot(txn, RESULT, returned, pending)
        identity = _literal(txn, core.DATUM_STRING, attempt_id)
        dag = layout._put_dag(txn, identity, {})
        layout._main(txn, result)
        return records._publish(txn, attempt_ref, ATTEMPT, dag, pending, result)


def _closure_report(closure):
    env = closure.environment
    return {
        "closure": closure.commit.hex(), "descriptor": closure.dag.hex(), "defaults": closure.defaults.hex(),
        "environment": env.dag.hex(), "capture_key": closure.key.hex(),
        "func": FUNC.decode("ascii"), "implementation": IMPLEMENTATION.decode("ascii"),
        "map_binding": env.map_binding.dag.hex(), "map_source": env.map_binding.source_uri.decode("ascii"),
        "list_binding": env.list_binding.dag.hex(), "list_source": env.list_binding.source_uri.decode("ascii"),
        "scale": env.scale.value.as_i64(), "scale_source": env.scale.dag.hex(), "scale_origin": env.origin.decode(),
    }


def _request_report(own):
    return {
        "request": own.commit.hex(), "func": FUNC.decode("ascii"), "inputs": own.args.dag.hex(),
        "argument_map": own.args.datum.hex(),
        "sources": {key.decode("ascii"): arg.dag.hex() for key, arg in own.args.entries},
        "capture": _closure_report(own.closure),
    }


def _attempt_report(producer):
    return {"attempt": producer.commit.hex(), "result": producer.result.hex(),
            "producing": _request_report(producer.request), "return_dag": producer.output.dag.hex(),
            "value": producer.output.value.as_i64(),
            "trace": [layout._operation_report(operation) for operation in producer.output.trace]}


def _decision_report(txn, inspector, commit):
    dag, parents = layout._snapshot(txn, commit, DECISION)
    mode = layout._string(txn, layout._shape(txn, dag, 3))
    outcome = layout._string(txn, layout._field(txn, dag, b"outcome"))
    if mode not in (FRESH, TRY, REQUIRE) or not parents or (mode == FRESH and len(parents) != 1):
        raise ValueError("invalid closure decision ancestry or mode")
    selected = parents[1] if len(parents) == 2 else None
    _check_pin(txn, dag, b"request", parents[0])
    _check_pin(txn, dag, b"selection", selected)
    own = _read_request(txn, inspector, parents[0])
    producer = _read_attempt(txn, inspector, selected) if selected is not None else None
    hit = _matches(own.closure, own.args, producer)
    if outcome != (REUSE if hit else PENDING) or (mode == REQUIRE and not hit):
        raise ValueError("closure decision does not match its recorded selection")
    if hit and own.commit == producer.request.commit:
        raise ValueError("reuse needs a new invocation ID, not the producing request")
    report = {"requested": _request_report(own), "mode": mode.decode("ascii"),
              "outcome": outcome.decode("ascii"), "selection": "" if selected is None else selected.hex()}
    if hit:
        report.update(_attempt_report(producer))
    return report


def inspect(path, ref, expected=None):
    with records._repository(path, create=False) as repo, records._read_transaction(repo) as txn:
        commit = core.txn_ref_get(txn, ref) if expected is None else layout._pin(txn, ref, expected, "inspection")
        _, _, entry, _ = records._snapshot(txn, commit)
        inspector = builtin.Inspector(txn)
        if entry == CLOSURE:
            report = _closure_report(_read_closure(txn, inspector, commit))
        elif entry == DECISION:
            report = _decision_report(txn, inspector, commit)
        elif entry == ATTEMPT:
            report = _attempt_report(_read_attempt(txn, inspector, commit))
        else:
            raise ValueError("inspect expects a closure, decision or attempt ref")
        return {"commit": commit.hex(), **report}


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    converters = dict.fromkeys(("defaults_commit", "closure_commit", "pending"), layout._commit_id)
    converters.update(a=int, b=int, scale=int, map_version=int)
    for name, handler, fields in (
        ("defaults", defaults, ("ref", "map_version", "scale", "origin")),
        ("capture", capture, ("defaults_ref", "defaults_commit", "closure_ref")),
        ("request", request, ("closure_ref", "closure_commit", "pending_ref", "decision_ref", "a", "b")),
        ("work", work, ("pending_ref", "pending", "attempt_ref")),
        ("inspect", inspect, ("ref",)),
    ):
        command = commands.add_parser(name)
        command.set_defaults(handler=handler)
        command.add_argument("path", type=Path)
        for field in fields:
            command.add_argument(field, type=converters.get(field, str.encode))
        if name == "request":
            command.add_argument("--invocation", type=str.encode)
            command.add_argument("--mode", choices=(FRESH, TRY, REQUIRE), default=FRESH, type=str.encode)
            command.add_argument("--selected-ref", type=str.encode)
            command.add_argument("--selected", type=layout._commit_id)
        elif name == "work":
            command.add_argument("--attempt-id", type=str.encode)
        elif name in ("defaults", "inspect"):
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
