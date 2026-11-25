"""Invoke two captured ordinary leaves through a fixed synchronous call interface."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

from daggerml import builtin, core

import recorded_builtins as layout
import recorded_calls as records
from recorded_closures import FRESH, REQUIRE, TRY, _check_role, _pin_literal, _put_role


def _role(name):
    return b"ordinary-example-" + name + b"-v1"


DEFAULTS, ENV, CAPTURE = map(_role, (b"defaults", b"environment", b"capture"))
OUTER_Q, START, FINISHED, HIT = map(_role, (b"outer-request", b"start", b"finished", b"hit"))
ADD, ADD_Q, ADD_T = map(_role, (b"add", b"add-request", b"add-attempt"))
DOUBLE, DOUBLE_Q, DOUBLE_T, DOUBLE_HIT = map(_role, (b"double", b"double-request", b"double-attempt", b"double-hit"))
MAP_SOURCES = {1: layout.SOURCES[b"v1"], 2: layout.SOURCES[b"v2"]}
LIST_SOURCE = layout.SOURCES[b"list"]
MODES = (FRESH, TRY, REQUIRE)
MAX_HISTORY_RECORDS = 128
MAX_HISTORY_DEPTH = 32


@dataclass(frozen=True)
class Leaf:
    dag: bytes
    binding: builtin.Binding


@dataclass(frozen=True)
class Environment:
    dag: bytes
    binding: builtin.Binding
    list_binding: builtin.Binding
    add: Leaf
    double: Leaf


@dataclass(frozen=True)
class Capture:
    commit: bytes
    defaults: bytes
    environment: Environment


@dataclass(frozen=True)
class Selection:
    mode: bytes = FRESH
    ref: bytes | None = None
    expected: bytes | None = None


@dataclass(frozen=True)
class OuterRequest:
    commit: bytes
    capture: Capture
    args: builtin.Arguments
    invocation: bytes
    mode: bytes
    double_mode: bytes
    selected: Finish | None
    double_selected: LeafAttempt | None


@dataclass(frozen=True)
class Start:
    commit: bytes
    request: OuterRequest
    identity: bytes


@dataclass(frozen=True)
class LeafRequest:
    commit: bytes
    start: Start
    target: Leaf
    args: builtin.Arguments
    invocation: bytes
    upstream: LeafAttempt | None = None


@dataclass(frozen=True)
class LeafAttempt:
    commit: bytes
    request: LeafRequest
    identity: bytes
    result: builtin.Return
    trace: bytes | None = None  # The independent outer getter trace, owned by the add phase.


@dataclass(frozen=True)
class LeafDecision:
    commit: bytes
    requested: LeafRequest
    producing: LeafAttempt


@dataclass(frozen=True)
class Finish:
    commit: bytes
    double: LeafDecision

    @property
    def start(self):
        return self.double.requested.start


@dataclass(frozen=True)
class Hit:
    requested: OuterRequest
    producing: Finish


def _string(txn, value):
    return records._put_literal(txn, core.DATUM_STRING, value)


def _s(txn, dag, field):
    return layout._string(txn, layout._field(txn, dag, field))


def _snapshot(txn, commit):
    view, count, role, dag = records._snapshot(txn, commit)
    if count > 3:
        raise ValueError("ordinary call snapshot has too many parents")
    return role, dag, tuple(core.object_view_parent(view, i) for i in range(count))


def _put(txn, role, fields, *parents):
    return records._put_snapshot(txn, role, _put_role(txn, role, fields), *parents)


def _new_id():
    return str(uuid4()).encode("ascii")


def _args(args, names):
    if tuple(key for key, _ in args.entries) != names:
        raise ValueError("ordinary call has incorrect named arguments")
    return tuple(source.value.as_i64() for _, source in args.entries)


def _leaf_value(kind, values):
    value = values[0] + values[1] if kind == ADD else 2 * values[0]
    records._check_i64(value, "add result" if kind == ADD else "double result")
    return value


def _check_trace(trace, args, binding):
    if len(trace) != len(args.entries):
        raise ValueError("incorrect number of ordinary getter positions")
    for op, (key, _) in zip(trace, args.entries, strict=True):
        sources = dict(op.arguments.entries)
        if (op.func_uri != builtin.MAP_GET or op.binding != binding
                or sources[b"map"].dag != args.dag or type(sources[b"key"]) is not builtin.Description
                or sources[b"key"].value.payload != key):
            raise ValueError("ordinary getter uses the wrong binding, MAP or key")


def _check_union(txn, trace, *roots):
    """Count the union of independently validated builtin DAG profiles."""
    todo = [trace, *builtin.Inspector(txn).trace(trace), *roots]
    seen = set()
    while todo:
        node = todo.pop()
        dag = node if type(node) is bytes else node.dag
        if dag in seen:
            continue
        if len(seen) == builtin.MAX_RECORDS:
            raise ValueError("ordinary call exceeds the semantic DAG limit")
        seen.add(dag)
        if isinstance(node, builtin.Return):
            todo.extend((node.returned, node.inputs, layout._target(txn, dag, b"trace"), *node.trace))
        elif isinstance(node, builtin.Operation):
            todo.extend((node.binding, node.arguments))
        elif isinstance(node, builtin.Arguments):
            todo.extend(source for _, source in node.entries)
        elif isinstance(node, builtin.LiteralSource):
            todo.append(node.source_dag)


def _outer_matches(request):
    if request.selected is None:
        return False
    old = request.selected.start.request
    return (old.capture.environment.dag, old.args.datum) == (request.capture.environment.dag, request.args.datum)


def _double_matches(request):
    old = request.start.request.double_selected
    return (old is not None and old.request.target.dag == request.target.dag
            and old.request.args.datum == request.args.datum)


class Reader:
    """Bounded verifier of exact ordinary profiles; never invokes a callable."""

    def __init__(self, txn):
        self.txn = txn
        self.builtins = builtin.Inspector(txn)
        self._cache = {}
        self._active = set()

    def load(self, commit, *expected):
        if commit not in self._cache:
            if (commit in self._active or len(self._active) >= MAX_HISTORY_DEPTH
                    or len(self._cache) + len(self._active) >= MAX_HISTORY_RECORDS):
                raise ValueError("ordinary call history exceeds its proof bound")
            role, dag, parents = _snapshot(self.txn, commit)
            if role not in expected:
                raise ValueError("unexpected ordinary call history role")
            self._active.add(commit)
            try:
                handler = {
                    DEFAULTS: self._defaults, CAPTURE: self._capture, OUTER_Q: self._outer_request,
                    START: self._start, HIT: self._hit, ADD_Q: self._leaf_request, DOUBLE_Q: self._leaf_request,
                    ADD_T: self._leaf_attempt, DOUBLE_T: self._leaf_attempt, DOUBLE_HIT: self._double_hit,
                    FINISHED: self._finished,
                }[role]
                evidence = handler(commit, role, dag, parents)
                self._cache[commit] = (role, evidence)
            finally:
                self._active.remove(commit)
        role, evidence = self._cache[commit]
        if role not in expected:
            raise ValueError("unexpected ordinary call history role")
        return evidence

    def _shape(self, dag, role, count, parents, expected):
        _check_role(self.txn, dag, role, count)
        if len(parents) not in expected:
            raise ValueError("incorrect ordinary history parent count")

    def _leaf(self, dag, kind):
        _check_role(self.txn, dag, kind, 2)
        return Leaf(dag, self._map_binding(dag))

    def _map_binding(self, dag):
        binding = self.builtins.binding(layout._target(self.txn, dag, b"map-get"))
        if binding.source_uri not in MAP_SOURCES.values():
            raise ValueError("unsupported captured map getter")
        return binding

    def _defaults(self, _commit, _role, dag, parents):
        self._shape(dag, ENV, 5, parents, (0, 1))
        if parents and _snapshot(self.txn, parents[0])[0] != DEFAULTS:
            raise ValueError("defaults must descend from a defaults snapshot")
        listed = self.builtins.binding(layout._target(self.txn, dag, b"list-get"))
        if listed.source_uri != LIST_SOURCE:
            raise ValueError("unsupported captured list getter")
        add = self._leaf(layout._target(self.txn, dag, b"add"), ADD)
        double = self._leaf(layout._target(self.txn, dag, b"double"), DOUBLE)
        return Environment(dag, self._map_binding(dag), listed, add, double)

    def _capture(self, commit, role, dag, parents):
        self._shape(dag, role, 2, parents, (1,))
        env = self.load(parents[0], DEFAULTS)
        if layout._target(self.txn, dag, b"environment") != env.dag:
            raise ValueError("capture does not link the pinned defaults environment")
        return Capture(commit, parents[0], env)

    def _identity(self, dag, field):
        identity = _s(self.txn, dag, field)
        records._check_uuid4(identity, field.decode("ascii"))
        return identity

    def _outer_request(self, commit, role, dag, parents):
        txn = self.txn
        self._shape(dag, role, 7, parents, (1, 2, 3))
        capture = self.load(parents[0], CAPTURE)
        args = self.builtins.arguments(layout._target(txn, dag, b"inputs"))
        _args(args, (b"a", b"b"))
        if any(type(source) is not builtin.Description for _, source in args.entries):
            raise ValueError("outer input MAP requires the original I64 literal sources")
        modes = (_s(txn, dag, b"mode"), _s(txn, dag, b"double-mode"))
        pins = (_s(txn, dag, b"selected"), _s(txn, dag, b"double-selected"))
        if tuple(pin for pin in pins if pin) != tuple(parent.hex().encode("ascii") for parent in parents[1:]):
            raise ValueError("selection pins do not match the ordered request parents")
        selections = []
        for mode, pin, kind in zip(modes, pins, (FINISHED, DOUBLE_T), strict=True):
            if mode not in MODES or (mode == FRESH and pin):
                raise ValueError("incorrect ordinary selection controls")
            selections.append(self.load(bytes.fromhex(pin.decode("ascii")), kind) if pin else None)
        return OuterRequest(commit, capture, args, self._identity(dag, b"invocation"), *modes, *selections)

    def _start(self, commit, role, dag, parents):
        self._shape(dag, role, 2, parents, (1,))
        request = self.load(parents[0], OUTER_Q)
        if _outer_matches(request) or request.mode == REQUIRE:
            raise ValueError("outer request cannot start a fresh attempt")
        return Start(commit, request, self._identity(dag, b"attempt"))

    def _hit(self, _commit, role, dag, parents):
        self._shape(dag, role, 1, parents, (1,))
        request = self.load(parents[0], OUTER_Q)
        if not _outer_matches(request) or request.invocation == request.selected.start.request.invocation:
            raise ValueError("outer hit needs a matching attempt and a new request")
        return Hit(request, request.selected)

    def _leaf_request(self, commit, role, dag, parents):
        self._shape(dag, role, 4, parents, (1,))
        inputs = self.builtins.arguments(layout._target(self.txn, dag, b"inputs"))
        if role == ADD_Q:
            start = self.load(parents[0], START)
            upstream = None
            target = start.request.capture.environment.add
            if inputs.dag != start.request.args.dag:
                raise ValueError("add did not take the original outer argument node")
        else:
            upstream = self.load(parents[0], ADD_T)
            start = upstream.request.start
            target = start.request.capture.environment.double
            _args(inputs, (b"x",))
            if inputs.entries[0][1].dag != upstream.result.dag:
                raise ValueError("double did not take the exact add return node")
        if layout._target(self.txn, dag, b"target") != target.dag:
            raise ValueError("leaf request does not use its captured target")
        return LeafRequest(commit, start, target, inputs, self._identity(dag, b"invocation"), upstream)

    def _leaf_attempt(self, commit, role, dag, parents):
        txn = self.txn
        add = role == ADD_T
        self._shape(dag, role, 4 if add else 3, parents, (1,))
        request = self.load(parents[0], ADD_Q if add else DOUBLE_Q)
        output = self.builtins.returned(layout._target(txn, dag, b"result"))
        if not add and (_double_matches(request) or request.start.request.double_mode == REQUIRE):
            raise ValueError("double request cannot start a fresh attempt")
        if output.inputs.dag != request.args.dag:
            raise ValueError("leaf result does not belong to its producing request")
        _check_trace(output.trace, request.args, request.target.binding)
        values = _args(request.args, (b"a", b"b") if add else (b"x",))
        expected = _leaf_value(ADD if add else DOUBLE, values)
        if type(output.returned) is not builtin.Description or output.value.as_i64() != expected:
            raise ValueError("incorrect ordinary leaf return")
        outer = request.start.request
        env = outer.capture.environment
        trace = None
        if add:
            trace = layout._target(txn, dag, b"trace")
            _check_trace(self.builtins.trace(trace), outer.args, env.binding)
        _check_union(txn, trace if add else request.upstream.trace, output, env.list_binding)
        return LeafAttempt(commit, request, self._identity(dag, b"attempt"), output, trace)

    def _double_hit(self, commit, role, dag, parents):
        self._shape(dag, role, 1, parents, (2,))
        own = self.load(parents[0], DOUBLE_Q)
        producer = self.load(parents[1], DOUBLE_T)
        if (producer is not own.start.request.double_selected or not _double_matches(own)
                or own.invocation == producer.request.invocation):
            raise ValueError("double hit needs the pinned matching attempt and a new request")
        _check_union(self.txn, own.upstream.trace, own.args, producer.result,
                     own.start.request.capture.environment.list_binding)
        return LeafDecision(commit, own, producer)

    def double_decision(self, commit):
        phase = self.load(commit, DOUBLE_T, DOUBLE_HIT)
        return phase if isinstance(phase, LeafDecision) else LeafDecision(commit, phase.request, phase)

    def _finished(self, commit, role, dag, parents):
        txn = self.txn
        if len(parents) != 1 or layout._shape(txn, dag, 5) != layout._field(txn, dag, b"value"):
            raise ValueError("incorrect finished outer result shape")
        if _s(txn, dag, b"role") != role:
            raise ValueError("incorrect finished outer result role")
        double = self.double_decision(parents[0])
        returned = double.producing.result
        own = double.requested
        if (layout._target(txn, dag, b"returned") != returned.dag
                or layout._target(txn, dag, b"inputs") != own.start.request.args.dag
                or layout._target(txn, dag, b"trace") != own.upstream.trace
                or records._target(txn, layout._field(txn, dag, b"value"), core.NODE_LITERAL) != returned.datum):
            raise ValueError("outer return does not use the exact double result and outer trace")
        return Finish(commit, double)


def defaults(path, ref, version, *, expected=None):
    records._check_intent_refs(("defaults", ref))
    if type(version) is not int or version not in MAP_SOURCES:
        raise ValueError("getter version must be 1 or 2")
    with records._write_transaction(path, create=expected is None) as txn:
        layout._pin(txn, ref, expected, "defaults")
        if expected is not None:
            Reader(txn).load(expected, DEFAULTS)
        map_link = layout._link(txn, builtin.put_binding(txn, MAP_SOURCES[version]))
        env = _put_role(txn, ENV, {
            b"map-get": map_link,
            b"list-get": layout._link(txn, builtin.put_binding(txn, LIST_SOURCE)),
            b"add": layout._link(txn, _put_role(txn, ADD, {b"map-get": map_link})),
            b"double": layout._link(txn, _put_role(txn, DOUBLE, {b"map-get": map_link})),
        })
        if expected is None:
            return records._publish(txn, ref, DEFAULTS, env)
        commit = records._put_snapshot(txn, DEFAULTS, env, expected)
        core.txn_ref_update(txn, ref, commit)
        return commit


def capture(path, defaults_ref, defaults_commit, capture_ref):
    records._check_intent_refs(("defaults", defaults_ref), ("capture", capture_ref))
    with records._write_transaction(path, create=False) as txn:
        layout._pin(txn, defaults_ref, defaults_commit, "defaults")
        env = Reader(txn).load(defaults_commit, DEFAULTS)
        commit = _put(txn, CAPTURE, {b"environment": layout._link(txn, env.dag)}, defaults_commit)
        core.txn_ref_create(txn, capture_ref, commit)
        return commit


def _selection_refs(outer, double):
    refs = []
    for name, selection in (("outer selection", outer), ("double selection", double)):
        if selection.mode not in MODES:
            raise ValueError(f"invalid {name} mode")
        if selection.mode == FRESH:
            if selection.ref is not None or selection.expected is not None:
                raise ValueError(f"fresh mode does not accept a {name} pin")
        elif selection.ref is None:
            raise ValueError(f"{name} requires a ref and an exact commit or expected absence")
        else:
            refs.append((name, selection.ref))
    return refs


def _begin(path, capture_ref, capture_commit, output_ref, a, b, invocation, outer, double):
    with records._write_transaction(path, create=False) as txn:
        layout._pin(txn, capture_ref, capture_commit, "capture")
        layout._pin(txn, output_ref, None, "output")
        for control in (outer, double):
            if control.mode != FRESH:
                layout._pin(txn, control.ref, control.expected, "selection")
        if outer.mode == REQUIRE and outer.expected is None:
            raise ValueError("no selected outer attempt")
        with builtin.Recorder(txn) as recorder:
            args = recorder.arguments({b"a": recorder.literal(core.DATUM_I64, a),
                                       b"b": recorder.literal(core.DATUM_I64, b)})
            inputs = recorder.dag(args)
        parents = (capture_commit, *(s.expected for s in (outer, double) if s.expected is not None))
        q = _put(txn, OUTER_Q, {b"inputs": layout._link(txn, inputs), b"invocation": _string(txn, invocation),
                               b"mode": _string(txn, outer.mode), b"double-mode": _string(txn, double.mode),
                               b"selected": _pin_literal(txn, outer.expected),
                               b"double-selected": _pin_literal(txn, double.expected)}, *parents)
        reader = Reader(txn)
        request = reader.load(q, OUTER_Q)
        if _outer_matches(request):
            head = _put(txn, HIT, {}, q)
            reader.load(head, HIT)
            layout._main(txn, request.selected.commit)
        elif outer.mode == REQUIRE:
            raise ValueError("no selected outer attempt for the capture and argument MAP")
        else:
            head = _put(txn, START, {b"attempt": _string(txn, _new_id())}, q)
            reader.load(head, START)
        core.txn_ref_create(txn, output_ref, head)
        return head, request


def _leaf_call(kind, arguments, ops):
    keys = (b"a", b"b") if kind == ADD else (b"x",)
    values = tuple(ops.map_get(arguments, key).value.as_i64() for key in keys)
    return ops.literal(core.DATUM_I64, _leaf_value(kind, values))


def _double_sum(arguments, get, make_arguments, invoke, add, double):
    get(arguments, b"a").value.as_i64()
    get(arguments, b"b").value.as_i64()
    summed = invoke(add, arguments)
    return invoke(double, make_arguments({b"x": summed}))


@dataclass(eq=False, frozen=True)
class _Node:
    value: builtin.Datum


def _checked(method):
    def call(session, *args):
        if not session.active or session.poisoned:
            raise ValueError("ordinary call session is inactive or poisoned")
        try:
            return method(session, *args)
        except BaseException:
            session.poisoned = True
            raise
    return call


class _Session:
    """Bridge copied handles to short owned recorders; only two fixed call slots."""

    def __init__(self, path, ref, head, request, batch):
        self.path, self.ref, self.head = path, ref, head
        self.env, self.input_dag = request.capture.environment, request.args.dag
        self.arguments = _Node(request.args.value)
        self.add, self.double = object(), object()
        self.batch = batch
        self.txn = self.outer_scope = self.recorder = self.outer_input = self.outer_ops = None
        self.gets = 0
        self.summed = self.double_arguments = self.result = None
        self.add_result = self.double_inputs = None
        self.active, self.poisoned = True, False

    def _begin_batch(self):
        self.txn = self.batch.enter_context(records._write_transaction(self.path, create=False))
        layout._pin(self.txn, self.ref, self.head, "ordinary phase")
        return self.txn

    def _advance(self, head):
        core.txn_ref_update(self.txn, self.ref, head)
        self.batch.close()
        self.txn = None
        self.head = head

    @_checked
    def get(self, arguments, key):
        if arguments is not self.arguments or self.gets >= 2 or key != (b"a", b"b")[self.gets]:
            raise ValueError("outer getters require the original MAP and ordered keys a, b")
        if self.gets == 0:
            txn = self._begin_batch()
            self.outer_scope = self.batch.enter_context(ExitStack())
            self.recorder = self.outer_scope.enter_context(builtin.Recorder(txn))
            self.outer_input = self.recorder.load(self.input_dag)
            self.outer_ops = self._operations(self.recorder, self.env.binding)
        result = self.outer_ops.map_get(self.outer_input, key)
        self.gets += 1
        return _Node(result.value)

    def _operations(self, recorder, binding):
        return recorder.operations(map_binding=binding.dag, list_binding=self.env.list_binding.dag)

    def _request(self, role, dag, target):
        return _put(self.txn, role, {b"inputs": layout._link(self.txn, dag),
                                    b"target": layout._link(self.txn, target.dag),
                                    b"invocation": _string(self.txn, _new_id())}, self.head)

    def _leaf(self, kind, inputs, target):
        with builtin.Recorder(self.txn) as recorder:
            args = recorder.load(inputs)
            node = _leaf_call(kind, args, self._operations(recorder, target.binding))
            return recorder.dag(recorder.returned(node, inputs=args))

    def _attempt(self, role, own, output, *, trace=None):
        txn = self.txn
        fields = {b"attempt": _string(txn, _new_id()), b"result": layout._link(txn, output)}
        if trace is not None:
            fields[b"trace"] = layout._link(txn, trace)
        return _put(txn, role, fields, own)

    def _add(self):
        txn = self.txn
        trace = self.recorder.trace()
        self.outer_scope.close()
        own = self._request(ADD_Q, self.input_dag, self.env.add)
        self.add_result = self._leaf(ADD, self.input_dag, self.env.add)
        attempt = self._attempt(ADD_T, own, self.add_result, trace=trace)
        proof = Reader(txn).load(attempt, ADD_T)
        self._advance(attempt)
        self.outer_scope = self.recorder = self.outer_ops = self.outer_input = None
        self.summed = _Node(proof.result.value)
        return self.summed

    @_checked
    def make_arguments(self, entries):
        if (self.summed is None or self.double_arguments is not None or type(entries) is not dict
                or tuple(entries) != (b"x",) or entries[b"x"] is not self.summed):
            raise ValueError("double arguments require this session's exact add return")
        txn = self._begin_batch()
        with builtin.Recorder(txn) as recorder:
            node = recorder.arguments({b"x": recorder.load(self.add_result)})
            self.double_inputs = recorder.dag(node)
            self.double_arguments = _Node(node.value)
        return self.double_arguments

    def _double(self):
        txn = self.txn
        own = self._request(DOUBLE_Q, self.double_inputs, self.env.double)
        reader = Reader(txn)
        request = reader.load(own, DOUBLE_Q)
        if _double_matches(request):
            phase = _put(txn, DOUBLE_HIT, {}, own, request.start.request.double_selected.commit)
        elif request.start.request.double_mode == REQUIRE:
            raise ValueError("no selected double attempt for the captured leaf and argument MAP")
        else:
            output = self._leaf(DOUBLE, self.double_inputs, self.env.double)
            phase = self._attempt(DOUBLE_T, own, output)
        proof = reader.double_decision(phase)
        self._advance(phase)
        self.result = _Node(proof.producing.result.value)
        return self.result

    @_checked
    def invoke(self, target, arguments):
        if target is self.add and arguments is self.arguments and self.gets == 2 and self.summed is None:
            return self._add()
        if (target is self.double and self.double_arguments is not None
                and arguments is self.double_arguments and self.result is None):
            return self._double()
        raise ValueError("ordinary invocation requires the next captured target and an owned argument node")

    def finish(self, returned):
        if self.poisoned or self.result is None or returned is not self.result:
            raise ValueError("outer callable did not return its second call's result node")
        with records._write_transaction(self.path, create=False) as txn:
            layout._pin(txn, self.ref, self.head, "ordinary phase")
            reader = Reader(txn)
            double = reader.double_decision(self.head)
            own = double.requested
            output = double.producing.result
            value = records._put_object(txn, core.REC_NODE, core.NODE_LITERAL, output.datum)
            dag = layout._put_dag(txn, value, {
                b"role": _string(txn, FINISHED), b"value": value,
                b"inputs": layout._link(txn, own.start.request.args.dag),
                b"trace": layout._link(txn, own.upstream.trace), b"returned": layout._link(txn, output.dag),
            })
            finished = records._put_snapshot(txn, FINISHED, dag, self.head)
            reader.load(finished, FINISHED)
            core.txn_ref_update(txn, self.ref, finished)
            layout._main(txn, finished)
            return finished


def invoke(path, capture_ref, capture_commit, output_ref, a, b, *,
           outer=Selection(), double=Selection(), invocation=None):
    records._check_i64(a, "a")
    records._check_i64(b, "b")
    invocation = _new_id() if invocation is None else invocation
    records._check_uuid4(invocation, "invocation")
    records._check_intent_refs(("capture", capture_ref), ("output", output_ref), *_selection_refs(outer, double))
    head, request = _begin(path, capture_ref, capture_commit, output_ref, a, b, invocation, outer, double)
    if _outer_matches(request):
        return head
    with ExitStack() as batch:
        session = _Session(path, output_ref, head, request, batch)
        try:
            returned = _double_sum(session.arguments, session.get, session.make_arguments,
                                   session.invoke, session.add, session.double)
            return session.finish(returned)
        finally:
            session.active = False


def select_double(path, finished_ref, finished, output_ref):
    records._check_intent_refs(("finished", finished_ref), ("selection output", output_ref))
    with records._write_transaction(path, create=False) as txn:
        layout._pin(txn, finished_ref, finished, "finished")
        decision = Reader(txn).load(finished, FINISHED).double
        if decision.commit != decision.producing.commit:
            raise ValueError("select-double requires a fresh double attempt")
        core.txn_ref_create(txn, output_ref, decision.commit)
        return decision.commit


def _outer_report(request):
    capture = request.capture
    env = capture.environment
    return {"request": request.commit.hex(), "capture": capture.commit.hex(), "defaults": capture.defaults.hex(),
            "environment": env.dag.hex(), "inputs": request.args.dag.hex(), "argument_map": request.args.datum.hex(),
            "map_source": env.binding.source_uri.decode("ascii"), "mode": request.mode.decode("ascii"),
            "double_mode": request.double_mode.decode("ascii")}


def _leaf_report(decision):
    def request_report(request):
        upstream = request.upstream
        return {"request": request.commit.hex(), "target": request.target.dag.hex(), "inputs": request.args.dag.hex(),
                "argument_map": request.args.datum.hex(),
                "map_source": request.target.binding.source_uri.decode("ascii"),
                "upstream_attempt": upstream.commit.hex() if upstream else "",
                "upstream_return": upstream.result.dag.hex() if upstream else ""}

    producer = decision.producing
    return {"requested": request_report(decision.requested), "producing": request_report(producer.request),
            "attempt": producer.commit.hex(), "return_dag": producer.result.dag.hex(),
            "value": producer.result.value.as_i64(),
            "trace": [layout._operation_report(op) for op in producer.result.trace]}


def _add_report(add):
    return _leaf_report(LeafDecision(add.commit, add.request, add))


def _start_report(start):
    return {"requested": _outer_report(start.request), "attempt": start.commit.hex()}


def _finish_report(reader, finish):
    decision = finish.double
    add = decision.requested.upstream
    result = decision.producing.result
    return {**_start_report(finish.start), "producing": _outer_report(finish.start.request),
            "result": finish.commit.hex(), "add": _add_report(add), "double": _leaf_report(decision),
            "value": result.value.as_i64(), "return_dag": result.dag.hex(),
            "trace": [layout._operation_report(op) for op in reader.builtins.trace(add.trace)]}


def _report(reader, commit, role):
    if role == CAPTURE:
        capture = reader.load(commit, CAPTURE)
        env = capture.environment
        return {"status": "capture", "defaults": capture.defaults.hex(), "environment": env.dag.hex(),
                "map_source": env.binding.source_uri.decode("ascii"), "add": env.add.dag.hex(),
                "double": env.double.dag.hex()}
    if role == START:
        return {"status": "start", **_start_report(reader.load(commit, START))}
    if role == ADD_T:
        add = reader.load(commit, ADD_T)
        return {"status": "add", **_start_report(add.request.start), "add": _add_report(add)}
    if role in (DOUBLE_T, DOUBLE_HIT):
        double = reader.double_decision(commit)
        return {"status": "double", **_start_report(double.requested.start),
                "add": _add_report(double.requested.upstream), "double": _leaf_report(double)}
    if role == FINISHED:
        return {"status": "finished", **_finish_report(reader, reader.load(commit, FINISHED))}
    if role == HIT:
        hit = reader.load(commit, HIT)
        return {"status": "hit", **_finish_report(reader, hit.producing), "requested": _outer_report(hit.requested)}
    raise ValueError("inspect expects a capture, phase, or completed ordinary call")


def inspect(path, ref, *, expected=None):
    with records._repository(path, create=False) as repo, records._read_transaction(repo) as txn:
        commit = core.txn_ref_get(txn, ref) if expected is None else layout._pin(txn, ref, expected, "inspection")
        role, _, _ = _snapshot(txn, commit)
        return {"commit": commit.hex(), **_report(Reader(txn), commit, role)}


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    converters = dict.fromkeys(("defaults_commit", "capture_commit", "finished"), layout._commit_id)
    converters.update(version=int, a=int, b=int)
    for name, handler, fields in (
        ("defaults", defaults, ("ref", "version")),
        ("capture", capture, ("defaults_ref", "defaults_commit", "capture_ref")),
        ("invoke", invoke, ("capture_ref", "capture_commit", "output_ref", "a", "b")),
        ("select-double", select_double, ("finished_ref", "finished", "output_ref")),
        ("inspect", inspect, ("ref",)),
    ):
        command = commands.add_parser(name)
        command.set_defaults(handler=handler)
        command.add_argument("path", type=Path)
        for field in fields:
            command.add_argument(field, type=converters.get(field, str.encode))
        if name in ("defaults", "inspect"):
            command.add_argument("--expected", type=layout._commit_id)
        if name == "invoke":
            command.add_argument("--invocation", type=str.encode)
            for group, flag in (("outer", ""), ("double", "double-")):
                command.add_argument(f"--{flag}mode", dest=f"{group}_mode", choices=MODES,
                                     default=FRESH, type=str.encode)
                command.add_argument(f"--{flag}selected-ref", dest=f"{group}_ref", type=str.encode)
                command.add_argument(f"--{flag}selected", dest=f"{group}_selected", type=layout._commit_id)
    return parser


def main():
    args = vars(_parser().parse_args())
    name, handler = args.pop("command"), args.pop("handler")
    if name == "invoke":
        for control in ("outer", "double"):
            args[control] = Selection(*(args.pop(f"{control}_{field}") for field in ("mode", "ref", "selected")))
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
