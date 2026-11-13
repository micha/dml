"""Explicit implementation captures and cooperative node-call integration.

Structural closure reading is NOT executable-source or producer-success proof.
Context belongs to trusted recording integration; logical code receives only its
bound Calls/Nodes. No backend registry, URI imports, native evaluator or sandbox.
"""

from dataclasses import dataclass
from functools import wraps
import math
import os
import re
import threading
import unicodedata

from . import Datum, LiteralNode, NotFoundError, ObjectId, SubDAGNode, canonicalize_uri
from . import builtin as b, transfer

ENVIRONMENT_ROLE = "implementation-environment-v1"
CAPTURE_ROLE = "implementation-capture-v1"
CLOSURE_ROLE = "implementation-closure-v1"
INPROCESS_ROLE = "implementation-inprocess-binding-v1"
MAX_CAPTURES = 16
MAX_STRUCTURE_DEPTH = 8


class CallError(ValueError):
    """Invalid cooperative invocation, closure or owned interface state."""


def same_value(first, second):
    """Compare copied canonical datums, including native canonical F64 NaN."""
    if type(first) is not Datum or type(second) is not Datum or first.kind != second.kind:
        return False
    if first.kind == "f64" and math.isnan(first.value) and math.isnan(second.value):
        return True
    return first == second


def _uri(value):
    if type(value) is not str or canonicalize_uri(value) != value:
        raise CallError("intent must be a canonical absolute URI")
    return value


def _name(value):
    if (type(value) is not str or value == "role"
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None):
        raise CallError("capture name outside native profile or reserved role")
    return value


@dataclass(frozen=True)
class Capture:
    kind: str
    intent: str
    target: ObjectId


@dataclass(frozen=True)
class Closure:
    dag: ObjectId
    intent: str
    binding: ObjectId
    environment: ObjectId
    captures: tuple


# Native DAG40 + sum(20 + ASCII field-name bytes), not new profile quotas.
_C_DAG_BYTES = 148
_CAPTURE_DAG_BYTES = 140
_BINDING_DAG_BYTES = 209
_ENVIRONMENT_DAG_BYTES = 64 + 148 * MAX_CAPTURES
_LOCAL_ROLE = "local-python-binding-v1"


class _StructuralReads:
    """ONE operation's charged typed native surface, including eager b.link reads.

    Raw public reads allocate/validate before Python checks; no pre-native size or
    RSS guarantee. Native DAG description/accessors are guarded BEFORE materialization.
    Mutable ref targets are never cached or used as structure authority.
    """

    def __init__(self, tx):
        self.tx = tx
        self.raw, self.values, self.dag_limits = {}, {}, {}
        self.packed = 0

    def state(self):
        try:
            self.tx.get_ref("calls-structural-state")
        except NotFoundError:
            pass

    def get_record(self, kind, oid):
        self.state()
        key = kind, oid
        if key not in self.raw:
            if len(self.raw) + 1 > transfer.MAX_OBJECTS:
                raise CallError("structural native membership exceeds transfer profile")
            raw = self.tx.get_record(kind, oid)
            if len(raw) > transfer.MAX_RECORD_BYTES or self.packed + len(raw) > transfer.MAX_PACKED_BYTES:
                raise CallError("structural native bytes exceed transfer profile")
            self.raw[key] = raw
            self.packed += len(raw)
        return self.raw[key]

    def guard_dag(self, dag, maximum):
        limit = min(self.dag_limits.get(dag, _ENVIRONMENT_DAG_BYTES), maximum)
        if len(self.get_record("dag", dag)) > limit:
            raise CallError("native DAG exceeds structural profile size")
        self.dag_limits[dag] = limit

    def get_dag(self, dag):
        self.guard_dag(dag, self.dag_limits.get(dag, _ENVIRONMENT_DAG_BYTES))
        key = "dag", dag
        if key not in self.values:
            self.values[key] = self.tx.get_dag(dag)
        return self.values[key]

    def get_node(self, node):
        if len(self.get_record("node", node)) != 40:
            raise CallError("structural native node size differs")  # pragma: no cover
        key = "node", node
        if key not in self.values:
            self.values[key] = self.tx.get_node(node)
        return self.values[key]

    def datum(self, datum, maximum=None):
        maximum = transfer.MAX_RECORD_BYTES if maximum is None else maximum
        if len(self.get_record("datum", datum)) > maximum:
            raise CallError("native datum exceeds structural field size")
        key = "datum", datum
        if key not in self.values:
            value = self.tx.get_datum(datum)
            if value.kind in ("map", "list", "set"):
                raise CallError("structural scalar field cannot contain composite references")
            self.values[key] = value
        return self.values[key]

    def get_datum(self, datum):
        return self.datum(datum)

    def reserve(self, records, packed, largest):
        self.state()
        if len(self.raw) + records > transfer.MAX_OBJECTS:
            raise CallError("prospective structural membership exceeds transfer profile")
        if largest > transfer.MAX_RECORD_BYTES or self.packed + packed > transfer.MAX_PACKED_BYTES:
            raise CallError("prospective structural bytes exceed transfer profile")


class _StructureWalk:
    """Operation-local native success proofs/height, never a caller-supplied cache.

    ALL named edges remain checked. A visited child charges actual depth+full height;
    each C independently compares native INPROCESS B.env with its own E.
    """

    def __init__(self, tx):
        self.read = _StructuralReads(tx)
        self.active, self.proofs, self.heights, self.bindings, self.rows = set(), {}, {}, {}, {}

    def depth(self, depth, height=0):
        if type(depth) is not int or not 0 <= depth <= MAX_STRUCTURE_DEPTH or depth + height > MAX_STRUCTURE_DEPTH:
            raise CallError("capture structure depth exceeds8")

    def scalar(self, node, kind, maximum=None):
        actual = self.read.get_node(node)
        if not isinstance(actual, LiteralNode):
            raise b.BuiltinError("expected literal value field")
        limit = {"null": 40, "i64": 48}.get(kind, transfer.MAX_RECORD_BYTES) if maximum is None else maximum
        value = self.read.datum(actual.datum, limit)
        if value.kind != kind:
            raise b.BuiltinError("wrong scalar kind: expected " + kind)
        return value.value

    def shape(self, dag, names, role, maximum):
        self.read.guard_dag(dag, maximum)
        got = self.read.get_dag(dag)
        if set(got.bindings) != set(names) or got.root != got.bindings.get("role"):
            raise b.BuiltinError("semantic profile fields/root differ")
        if self.scalar(got.bindings["role"], "string", 40 + len(role)) != role:
            raise b.BuiltinError("semantic profile role differs")
        return got.bindings

    def link(self, node, maximum):
        got = self.read.get_node(node)
        if not isinstance(got, SubDAGNode):
            raise b.BuiltinError("expected sub-DAG field")
        self.read.guard_dag(got.dag, maximum)  # BEFORE b.link's eager get_dag.
        return b.link(self.read, node)

    def binding(self, dag, kind, environment=None):
        self.read.guard_dag(dag, _BINDING_DAG_BYTES)
        if dag not in self.bindings:
            fields = self.read.get_dag(dag).bindings
            role = self.scalar(fields["role"], "string", 40 + max(map(len, (INPROCESS_ROLE, _LOCAL_ROLE, b.BINDING_ROLE))))
            common = ("role", "adapter", "source", "interpreter", "timeout-ms")
            if role == INPROCESS_ROLE:
                fields = self.shape(dag, (*common, "environment"), role, 209)
                self.scalar(fields["adapter"], "uri")  # Native validated canonical URI, not host input.
                for name in ("interpreter", "timeout-ms"):
                    self.scalar(fields[name], "null")
                native_env = self.link(fields["environment"], _ENVIRONMENT_DAG_BYTES)
                source = self.scalar(fields["source"], "bytes", 40 + 1048576)
                if not source:
                    raise CallError("captured source exceeds external binding profile")
                proof = role, native_env, None
            elif role == _LOCAL_ROLE:
                fields = self.shape(dag, common, role, 178)
                if self.scalar(fields["adapter"], "uri") != "urn:daggerml:local-python-v1":
                    raise CallError("unsupported external binding adapter")
                interpreter = self.scalar(fields["interpreter"], "string")
                interpreter.encode("utf-8")
                timeout = self.scalar(fields["timeout-ms"], "i64")
                if (not os.path.isabs(interpreter) or "\0" in interpreter
                    or unicodedata.normalize("NFC", interpreter) != interpreter or not 1 <= timeout <= 3600000):
                    raise CallError("invalid external interpreter or timeout")
                source = self.scalar(fields["source"], "bytes", 40 + 1048576)
                if not source:
                    raise CallError("captured source exceeds external binding profile")
                proof = role, None, None
            elif role == b.BINDING_ROLE:
                fields = self.shape(dag, common, role, 178)
                for name in ("adapter", "interpreter", "timeout-ms"):
                    self.scalar(fields[name], "null")
                proof = role, None, self.scalar(fields["source"], "uri")
            else:
                raise CallError("unsupported structural implementation binding")
            self.bindings[dag] = proof  # Only complete native B proof, NEVER valid-for-caller-E.
        role, native_env, source_uri = self.bindings[dag]
        if kind == "builtin":
            if role != b.BINDING_ROLE:
                raise CallError("builtin capture requires builtin binding")
        else:
            if role == b.BINDING_ROLE:
                raise CallError("ordinary closure requires executable implementation binding")
            if role == INPROCESS_ROLE and native_env != environment:
                raise CallError("binding and closure environments differ")
        return source_uri

    def capture(self, row):
        self.read.guard_dag(row, _CAPTURE_DAG_BYTES)
        if row not in self.rows:
            fields = self.shape(row, ("role", "kind", "intent", "target"), CAPTURE_ROLE, _CAPTURE_DAG_BYTES)
            kind = self.scalar(fields["kind"], "string", 48)
            intent = self.scalar(fields["intent"], "uri")  # Native datum identity memo, no recanonicalization.
            if kind not in ("builtin", "ordinary"):
                raise CallError("unsupported capture kind")
            target = self.link(fields["target"], _BINDING_DAG_BYTES if kind == "builtin" else _C_DAG_BYTES)
            self.rows[row] = Capture(kind, intent, target)
        return self.rows[row]

    def inspect_environment(self, dag, depth):
        self.depth(depth)
        self.read.guard_dag(dag, _ENVIRONMENT_DAG_BYTES)
        key = "environment", dag
        if key in self.active:
            raise CallError("cyclic capture structure")  # pragma: no cover
        if key in self.proofs:
            self.depth(depth, self.heights[key])
            return self.proofs[key]
        self.active.add(key)
        try:
            fields = self.read.get_dag(dag).bindings
            names = tuple(sorted(set(fields) - {"role"}))
            self.shape(dag, ("role", *names), ENVIRONMENT_ROLE, _ENVIRONMENT_DAG_BYTES)
            if len(names) > MAX_CAPTURES:
                raise CallError("environment exceeds16 named captures")
            captures, height = [], 0
            for name in names:
                _name(name)
                row = self.link(fields[name], _CAPTURE_DAG_BYTES)
                got = self.capture(row)
                if got.kind == "builtin":
                    self.binding(got.target, "builtin")
                else:
                    child = self.inspect_closure(got.target, depth + 1)
                    if child.intent != got.intent:
                        raise CallError("captured ordinary intent differs from closure")
                    height = max(height, 1 + self.heights[("closure", got.target)])
                captures.append((name, got))
            self.depth(depth, height)
            result = tuple(captures)
            self.proofs[key], self.heights[key] = result, height
            return result
        finally:
            self.active.remove(key)

    def inspect_closure(self, dag, depth):
        self.depth(depth)
        self.read.guard_dag(dag, _C_DAG_BYTES)
        key = "closure", dag
        if key in self.active:
            raise CallError("cyclic closure structure")  # pragma: no cover
        if key in self.proofs:
            result = self.proofs[key]
            self.binding(result.binding, "ordinary", result.environment)  # EVERY C association.
            self.depth(depth, self.heights[key])
            return result
        self.active.add(key)
        try:
            fields = self.shape(dag, ("role", "intent", "binding", "environment"), CLOSURE_ROLE, _C_DAG_BYTES)
            intent = self.scalar(fields["intent"], "uri")
            binding = self.link(fields["binding"], _BINDING_DAG_BYTES)
            environment = self.link(fields["environment"], _ENVIRONMENT_DAG_BYTES)
            self.binding(binding, "ordinary", environment)
            captures = self.inspect_environment(environment, depth)
            height = self.heights[("environment", environment)]
            result = Closure(dag, intent, binding, environment, captures)
            self.proofs[key], self.heights[key] = result, height
            return result
        finally:
            self.active.remove(key)


def inspect_environment(tx, dag, *, depth=0):
    """One bounded native structural walk; no execution/producer proof or reusable memo."""
    return _StructureWalk(tx).inspect_environment(dag, depth)


def inspect_closure(tx, dag, *, depth=0):
    """Structural C/B/E proof with full height and EACH C's native B/E association."""
    return _StructureWalk(tx).inspect_closure(dag, depth)


def put_environment(tx, captures=()):
    """Validate ALL existing captures/admit remaining budgets BEFORE metadata puts."""
    items = list(captures.items()) if hasattr(captures, "items") else list(captures)
    if len(items) > MAX_CAPTURES or len({name for name, _ in items}) != len(items):
        raise CallError("duplicate captures or more than16 captures")
    walk = _StructureWalk(tx)
    for name, capture in items:
        _name(name)
        if type(capture) is not Capture or type(capture.target) is not ObjectId:
            raise TypeError("capture requires Capture with ObjectId target")
        _uri(capture.intent)
        if capture.kind == "builtin":
            walk.binding(capture.target, "builtin")
        elif capture.kind == "ordinary":
            if walk.inspect_closure(capture.target, 1).intent != capture.intent:
                raise CallError("captured ordinary intent differs from closure")
        else:
            raise CallError("unsupported capture kind")
    # Conservative owning-layout upper bounds; no encoder/hash/dedup shortcut.
    rows = [420 + len(CAPTURE_ROLE) + len(got.kind) + len(got.intent) for _, got in items]
    env = 144 + len(ENVIRONMENT_ROLE) + 60 * len(items) + sum(len(name) for name, _ in items)
    largest = max([64 + 20 * len(items) + sum(len(name) for name, _ in items),
                   40 + len(ENVIRONMENT_ROLE), *[140 for _ in items],
                   *[40 + len(got.intent) for _, got in items]])
    walk.read.reserve(9 * len(items) + 3, sum(rows) + env, largest)
    links = {name: b.record(tx, CAPTURE_ROLE, values={"kind": got.kind, "intent": Datum.uri(got.intent)},
                           links={"target": got.target}) for name, got in items}
    return b.record(tx, ENVIRONMENT_ROLE, links=links)


def put_closure(tx, *, intent, binding, environment):
    """E-before-B-before-C with bounded ONE-operation proof/admission, no K."""
    _uri(intent)
    walk = _StructureWalk(tx)
    walk.inspect_environment(environment, 0)
    walk.binding(binding, "ordinary", environment)
    walk.read.reserve(7, 388 + len(CLOSURE_ROLE) + len(intent), max(148, 40 + len(intent)))
    return b.record(tx, CLOSURE_ROLE, values={"intent": Datum.uri(intent)},
                    links={"binding": binding, "environment": environment})


class Node:
    """Copied Datum only; construction alone conveys no Context ownership."""
    __slots__ = ("__value",)

    def __init__(self, value):
        self.__value = value

    @property
    def value(self):
        return self.__value


class Target:
    """Opaque exact-identity target; construction alone conveys no authority."""
    __slots__ = ()


@dataclass(frozen=True)
class Bound:
    kind: str
    intent: str
    target: ObjectId


class Calls:
    __slots__ = ("__invoke",)

    def __init__(self, invoke):
        self.__invoke = invoke

    def invoke(self, target, arguments):
        return self.__invoke(target, arguments)


class Nodes:
    __slots__ = ("__literal", "__arguments", "__map", "__list")

    def __init__(self, literal, arguments, map_get, list_get):
        self.__literal, self.__arguments, self.__map, self.__list = literal, arguments, map_get, list_get

    def literal(self, value):
        return self.__literal(value)

    def arguments(self, entries=()):
        return self.__arguments(entries)

    def map_get(self, node, key):
        return self.__map(node, key)

    def list_get(self, node, index):
        return self.__list(node, index)


def _guard(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        try:
            self._state()
            result = method(self, *args, **kwargs)
            self._state()  # Caught backend/read/state errors cannot return apparent success.
            return result
        except BaseException:
            # Copied poison state is safe even on a foreign thread. NO native
            # abort/close here: integration/Recorder cleanup stays owner-thread-only.
            self.poisoned = True
            raise
    return guarded


class Context:
    """Trusted explicitly bound integration, NOT supplied to logical code.

    Backend methods: bind(Bound), read(dag), literal(value), arguments(entries),
    perform(Bound, Description), verify(Bound, Description, receipt).
    Every read/verify derives native authority in the trusted integration. Verify
    MUST independently match THIS invocation/history, including requested and OLD
    producer chains; arbitrary callback values/flags/IDs are not success proofs.
    Context has no import-by-URI or mutable registry. Logical Calls cannot bind.
    All methods require an entered scope; rejected pre-entry/repeated/closed use
    poisons copied Context state. Node.value remains a readable copied Datum.
    """

    def __init__(self, backend):
        self.__backend = backend
        self.thread = threading.get_ident()
        self.ended = self.poisoned = self.entered = self.active = False
        self.__targets, self.__nodes = {}, {}
        self.calls = Calls(self.invoke)

    def _state(self, *, require_entered=True):
        if threading.get_ident() != self.thread:
            raise CallError("context used on wrong thread")
        if self.ended or self.poisoned:
            raise CallError("context ended or poisoned")
        if require_entered and not self.entered:
            raise CallError("context must be entered before use")

    def __enter__(self):
        try:
            self._state(require_entered=False)
            if self.entered:
                raise CallError("context already entered")
            self.entered = True
            return self
        except BaseException:
            self.poisoned = True
            raise

    def __exit__(self, kind, value, traceback):
        if threading.get_ident() != self.thread:
            self.poisoned = True
            raise CallError("context cleanup requires owning thread")
        if not self.entered or self.ended:
            self.poisoned = True
            raise CallError("context exit requires an entered unfinished scope")
        self.ended = True
        if kind is None and self.poisoned:
            raise CallError("caught callback/verifier/state error poisoned success")

    def _issue(self, actual):
        if type(actual) is not b.Description:
            raise CallError("integration must return native-derived Description")
        if type(actual.dag) is not ObjectId or type(actual.datum) is not ObjectId or type(actual.value) is not Datum:
            raise CallError("invalid native-derived description types")
        # Even an apparent Description is re-read, never a copied callback value.
        fresh = self.__backend.read(actual.dag)
        if (type(fresh) is not b.Description or fresh.dag != actual.dag
            or fresh.datum != actual.datum or not same_value(fresh.value, actual.value)):
            raise CallError("integration result differs from fresh native source")
        node = Node(fresh.value)
        self.__nodes[node] = fresh.dag, fresh.datum
        return node

    def _owned(self, node):
        if type(node) is not Node or node not in self.__nodes:
            raise CallError("foreign or fabricated context node")
        dag, datum = self.__nodes[node]
        actual = self.__backend.read(dag)
        if (type(actual) is not b.Description or actual.dag != dag or actual.datum != datum
            or not same_value(actual.value, node.value)):
            raise CallError("owned node/native value association differs")
        return actual

    @_guard
    def load(self, dag):
        """Trusted source loading; never part of bound logical Nodes."""
        return self._issue(self.__backend.read(dag))

    @_guard
    def describe(self, node):
        """Trusted recording bridge; logical interface exposes copied values only."""
        return self._owned(node)

    @_guard
    def bind(self, *, kind, intent, target):
        if kind not in ("builtin", "ordinary") or type(target) is not ObjectId:
            raise CallError("target requires explicit supported kind and ObjectId")
        bound = Bound(kind, _uri(intent), target)
        self.__backend.bind(bound)
        token = Target()
        self.__targets[token] = bound
        return token

    @_guard
    def literal(self, value):
        return self._issue(self.__backend.literal(value))

    @_guard
    def arguments(self, entries=()):
        items = list(entries.items()) if hasattr(entries, "items") else list(entries)
        if len(items) > b.MAX_ARGUMENTS:
            raise CallError("arguments exceed16")
        resolved = [(key, self._owned(node)) for key, node in items]
        return self._issue(self.__backend.arguments(resolved))

    @_guard
    def operations(self, *, map_target, list_target):
        for target, intent in ((map_target, b.MAP_GET), (list_target, b.LIST_GET)):
            bound = self.__targets.get(target)
            if bound is None or bound.kind != "builtin" or bound.intent != intent:
                raise CallError("getter convenience requires exact bound builtin target")
        def map_get(node, key):
            # Preparation/conversion errors poison just like dispatch errors.
            try:
                arguments = self.arguments({"map": node, "key": self.literal(Datum.string(key))})
                return self.invoke(map_target, arguments)
            except BaseException:
                self.poisoned = True
                raise
        def list_get(node, index):
            try:
                arguments = self.arguments({"list": node, "index": self.literal(Datum.i64(index))})
                return self.invoke(list_target, arguments)
            except BaseException:
                self.poisoned = True
                raise
        return Nodes(self.literal, self.arguments, map_get, list_get)

    @_guard
    def invoke(self, target, arguments):
        if type(target) is not Target or target not in self.__targets or self.active:
            raise CallError("foreign/fabricated target or context re-entry")
        actual = self._owned(arguments)
        if actual.value.kind != "map":
            raise CallError("func invocation requires argument-map node")
        bound = self.__targets[target]
        self.active = True
        try:
            receipt = self.__backend.perform(bound, actual)
            self._state()  # A caught nested error cannot be laundered by callback success.
            verified = self.__backend.verify(bound, actual, receipt)
            self._state()
            return self._issue(verified)
        finally:
            self.active = False
