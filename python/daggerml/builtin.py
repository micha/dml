"""Fixed versioned built-ins recorded as ordinary native DAGs.

ValueNode is a cooperative interface for trusted Python, not a sandbox. Only
trusted wrappers receive the recorder and publish its native records.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import wraps

from . import core


MAP_EMPTY = b"dml://builtin/map/empty"
MAP_INSERT = b"dml://builtin/map/insert"
MAP_GET = b"dml://builtin/map/get"
LIST_GET = b"dml://builtin/list/get"

BINDING_ROLE = b"builtin-binding-v1"
LITERAL_ROLE = b"builtin-literal-v1"
SOURCE_ROLE = b"builtin-literal-source-v1"
ARGUMENTS_ROLE = b"builtin-arguments-v1"
OPERATION_ROLE = b"builtin-operation-v1"
TRACE_ROLE = b"builtin-trace-v1"
RETURN_ROLE = b"builtin-return-v1"

MAX_ARGUMENTS = 16
MAX_POSITIONS = 16
MAX_RECORDS = 64
MAX_MAP_ENTRIES = 16


class BuiltinError(ValueError):
    """Invalid profile, unsupported built-in call or unusable recording scope."""


@dataclass(frozen=True, slots=True)
class Datum:
    kind: int
    payload: bytes

    def as_i64(self) -> int:
        if self.kind != core.DATUM_I64:
            raise BuiltinError("expected an I64 value")
        return int.from_bytes(self.payload, "little", signed=True)


@dataclass(frozen=True, slots=True)
class Binding:
    dag: bytes
    source_uri: bytes


@dataclass(frozen=True, slots=True)
class Description:
    dag: bytes
    datum: bytes
    value: Datum


@dataclass(frozen=True, slots=True)
class LiteralSource(Description):
    source_dag: bytes
    name: bytes
    source_node: bytes


@dataclass(frozen=True, slots=True)
class Arguments(Description):
    entries: tuple[tuple[bytes, Description], ...]


@dataclass(frozen=True, slots=True)
class Operation(Description):
    func_uri: bytes
    binding: Binding
    arguments: Arguments


@dataclass(frozen=True, slots=True)
class Return(Description):
    returned: Description
    trace: tuple[Operation, ...]
    inputs: Arguments


class ValueNode:
    """A copied value; the recorder separately owns its exact native association."""

    __slots__ = ("__value",)

    def __init__(self, value):
        self.__value = value

    @property
    def value(self) -> Datum:
        return self.__value


def _put_object(tx, kind, *fields):
    return core.txn_put_object(tx, kind, core.object_encode(kind, *fields))


def _literal(tx, datum):
    return _put_object(tx, core.REC_NODE, core.NODE_LITERAL, datum)


def _put_literal(tx, kind, value):
    return _literal(tx, core.txn_put_datum(tx, core.datum_encode(kind, value)))


def _record(tx, role, *, fields=(), links=(), root=b"role"):
    nodes = {b"role": _put_literal(tx, core.DATUM_STRING, role), **dict(fields)}
    nodes.update((name, _put_object(tx, core.REC_NODE, core.NODE_SUBDAG, dag)) for name, dag in links)
    return _put_object(tx, core.REC_DAG, nodes[root], *(item for pair in nodes.items() for item in pair))


def _node_target(tx, node, kind):
    packed = core.txn_get_object(tx, core.REC_NODE, node)
    _, target, _ = core.object_decode(packed)
    if packed != core.object_encode(core.REC_NODE, kind, target):
        raise BuiltinError("unexpected native node kind in builtin profile")
    return target


def _link(tx, node):
    return _node_target(tx, node, core.NODE_SUBDAG)


def _datum(packed):
    payload, kind = core.datum_decode(packed)
    return Datum(kind, payload)


def _read_value(tx, node):
    datum = _node_target(tx, node, core.NODE_LITERAL)
    return datum, _datum(core.txn_get_datum(tx, datum))


def _scalar(tx, node, kind):
    _, actual = _read_value(tx, node)
    if actual.kind != kind:
        raise BuiltinError("wrong datum kind in builtin profile")
    return actual.payload


def _lookup(tx, dag, name):
    try:
        return core.txn_lookup_node(tx, dag, name)
    except core.Error as error:
        if (error.args[0], error.args[2]) != ("not_found", "node name was not found in this DAG"):
            raise
        raise BuiltinError(f"missing builtin profile field {name!r}") from error


def _header(tx, dag):
    _, root, count = core.object_decode(core.txn_get_object(tx, core.REC_DAG, dag))
    return root, count


def _shape(tx, dag, header, names, *, root=b"value"):
    node, count = header
    if count != len(names):
        raise BuiltinError("builtin profile has wrong binding count")
    fields = {name: _lookup(tx, dag, name) for name in names}
    if fields[root] != node:
        raise BuiltinError("builtin profile has wrong root")
    return fields


def put_binding(tx, source_uri: bytes) -> bytes:
    """Store a structural internal binding, even for an unknown source URI."""
    source = _put_literal(tx, core.DATUM_URI, source_uri)
    absent = _put_literal(tx, core.DATUM_NULL, None)
    return _record(tx, BINDING_ROLE, fields=((b"adapter", absent), (b"source", source),
                                             (b"interpreter", absent), (b"timeout-ms", absent)))


def inspect_binding(tx, dag: bytes) -> Binding:
    """Read a strict binding without implying executable version support."""
    names = (b"role", b"adapter", b"source", b"interpreter", b"timeout-ms")
    fields = _shape(tx, dag, _header(tx, dag), names, root=b"role")
    if _scalar(tx, fields[b"role"], core.DATUM_STRING) != BINDING_ROLE:
        raise BuiltinError("not a builtin binding role")
    for name in (b"adapter", b"interpreter", b"timeout-ms"):
        _scalar(tx, fields[name], core.DATUM_NULL)
    return Binding(dag, _scalar(tx, fields[b"source"], core.DATUM_URI))


def _map_members(tx, container):
    if container.value.kind != core.DATUM_MAP:
        raise BuiltinError("expected a MAP container")
    pairs = core.datum_members(core.txn_get_datum(tx, container.datum))
    if len(pairs) > MAX_MAP_ENTRIES:
        raise BuiltinError("builtin MAP entry limit exceeded")
    if any(_datum(core.txn_get_datum(tx, key)).kind != core.DATUM_STRING for key, _ in pairs):
        raise BuiltinError("builtin MAP requires STRING keys")
    return pairs


def _key(node):
    if node.value.kind != core.DATUM_STRING:
        raise BuiltinError("builtin key must be STRING")
    return node.datum


def _map_empty(tx, args):
    return core.datum_encode(core.DATUM_MAP, ())


def _map_insert(tx, args):
    pairs = dict(_map_members(tx, args[b"map"]))
    key = _key(args[b"key"])
    if key in pairs:
        raise BuiltinError("duplicate canonical key")
    if len(pairs) >= MAX_MAP_ENTRIES:
        raise BuiltinError("builtin MAP entry limit exceeded")
    pairs[key] = args[b"value"].datum
    return core.datum_encode(core.DATUM_MAP, tuple(pairs.items()))


def _map_get_v1(tx, args):
    key = _key(args[b"key"])
    for stored, value in _map_members(tx, args[b"map"]):
        if stored == key:
            return core.txn_get_datum(tx, value)
    raise BuiltinError("missing MAP key")


def _map_get_v2(tx, args):
    key = _key(args[b"key"])
    value = dict(_map_members(tx, args[b"map"])).get(key)
    if value is None:
        raise BuiltinError("missing MAP key")
    return core.txn_get_datum(tx, value)


def _list_get(tx, args):
    container = args[b"list"]
    if container.value.kind != core.DATUM_LIST:
        raise BuiltinError("expected a LIST container")
    index = args[b"index"].value.as_i64()
    members = core.datum_members(core.txn_get_datum(tx, container.datum))
    if not 0 <= index < len(members):
        raise BuiltinError("LIST index out of range")
    return core.txn_get_datum(tx, members[index])


def _handler(func, source):
    if (func, source) == (MAP_EMPTY, b"dml://source/builtin/map/empty/v1"):
        return (), _map_empty
    if (func, source) == (MAP_INSERT, b"dml://source/builtin/map/insert/v1"):
        return (b"key", b"map", b"value"), _map_insert
    if (func, source) == (MAP_GET, b"dml://source/builtin/map/get/v1"):
        return (b"key", b"map"), _map_get_v1
    if (func, source) == (MAP_GET, b"dml://source/builtin/map/get/v2"):
        return (b"key", b"map"), _map_get_v2
    if (func, source) == (LIST_GET, b"dml://source/builtin/list/get/v1"):
        return (b"index", b"list"), _list_get
    raise BuiltinError("unsupported builtin func/source pairing")


def _apply(tx, func, binding, arguments):
    names, handler = _handler(func, binding.source_uri)
    args = dict(arguments.entries)
    if tuple(args) != names:
        raise BuiltinError("builtin exact argument names differ")
    return handler(tx, args)


def _name(prefix, position):
    return prefix + f"-{position:02d}".encode("ascii")


def _expect(value, kind):
    if not isinstance(value, kind):
        raise BuiltinError(f"expected a builtin {kind.__name__} profile")
    return value


def _charge(seen, dag):
    if dag not in seen:
        if len(seen) >= MAX_RECORDS:
            raise BuiltinError("builtin reached profile limit exceeded")
        seen.add(dag)
    return dag


class _Inspection:
    def __init__(self, tx, seen):
        self.tx = tx
        self.seen = seen
        self.nodes = {}
        self.bindings = {}

    def binding(self, dag):
        if dag not in self.bindings:
            self.bindings[dag] = inspect_binding(self.tx, _charge(self.seen, dag))
        return self.bindings[dag]

    def arguments(self, dag):
        return _expect(self.node(dag), Arguments)

    def operation(self, dag):
        return _expect(self.node(dag), Operation)

    def trace(self, dag):
        tx = self.tx
        header = _header(tx, _charge(self.seen, dag))
        count = header[1] - 1
        if not 0 <= count <= MAX_POSITIONS:
            raise BuiltinError("invalid builtin trace position count")
        names = tuple(_name(b"call", i) for i in range(count))
        fields = _shape(tx, dag, header, (b"role", *names), root=b"role")
        if _scalar(tx, fields[b"role"], core.DATUM_STRING) != TRACE_ROLE:
            raise BuiltinError("not a builtin trace role")
        return tuple(self.operation(_link(tx, fields[name])) for name in names)

    def _arguments(self, dag, header):
        tx = self.tx
        count, leftover = divmod(header[1] - 2, 2)
        if leftover or not 0 <= count <= MAX_ARGUMENTS:
            raise BuiltinError("invalid builtin argument count")
        names = tuple((_name(b"key", i), _name(b"source", i)) for i in range(count))
        fields = _shape(tx, dag, header, (b"role", b"value", *(part for pair in names for part in pair)))
        datum, value = _read_value(tx, fields[b"value"])
        pairs = []
        entries = []
        for key_field, source_field in names:
            key, copied = _read_value(tx, fields[key_field])
            if copied.kind != core.DATUM_STRING or (entries and entries[-1][0] >= copied.payload):
                raise BuiltinError("builtin argument keys must be distinct canonical STRINGs in order")
            source = self.node(_link(tx, fields[source_field]))
            pairs.append((key, source.datum))
            entries.append((copied.payload, source))
        if core.txn_get_datum(tx, datum) != core.datum_encode(core.DATUM_MAP, pairs):
            raise BuiltinError("argument MAP differs from actual source values")
        return Arguments(dag, datum, value, tuple(entries))

    def _literal_source(self, dag, header):
        tx = self.tx
        fields = _shape(tx, dag, header, (b"role", b"value", b"source", b"name"))
        source = _charge(self.seen, _link(tx, fields[b"source"]))
        name = _scalar(tx, fields[b"name"], core.DATUM_STRING)
        if _lookup(tx, source, name) != fields[b"value"]:
            raise BuiltinError("literal source node differs from named native binding")
        datum, value = _read_value(tx, fields[b"value"])
        return LiteralSource(dag, datum, value, source, name, fields[b"value"])

    def _operation(self, dag, header):
        tx = self.tx
        fields = _shape(tx, dag, header, (b"role", b"value", b"func", b"binding", b"arguments"))
        func = _scalar(tx, fields[b"func"], core.DATUM_URI)
        binding = self.binding(_link(tx, fields[b"binding"]))
        args = self.arguments(_link(tx, fields[b"arguments"]))
        datum, value = _read_value(tx, fields[b"value"])
        if core.txn_get_datum(tx, datum) != _apply(tx, func, binding, args):
            raise BuiltinError("builtin operation value differs from fixed semantics")
        return Operation(dag, datum, value, func, binding, args)

    def _returned(self, dag, header):
        tx = self.tx
        fields = _shape(tx, dag, header, (b"role", b"value", b"returned", b"trace", b"inputs"))
        datum, value = _read_value(tx, fields[b"value"])
        returned = self.node(_link(tx, fields[b"returned"]))
        if datum != returned.datum:
            raise BuiltinError("builtin return value differs from returned node")
        trace = self.trace(_link(tx, fields[b"trace"]))
        inputs = self.arguments(_link(tx, fields[b"inputs"]))
        return Return(dag, datum, value, returned, trace, inputs)

    def _read_node(self, dag):
        tx = self.tx
        header = _header(tx, dag)
        role = _scalar(tx, _lookup(tx, dag, b"role"), core.DATUM_STRING)
        if role == LITERAL_ROLE:
            fields = _shape(tx, dag, header, (b"role", b"value"))
            return Description(dag, *_read_value(tx, fields[b"value"]))
        if role == SOURCE_ROLE:
            return self._literal_source(dag, header)
        if role == ARGUMENTS_ROLE:
            return self._arguments(dag, header)
        if role == OPERATION_ROLE:
            return self._operation(dag, header)
        if role == RETURN_ROLE:
            return self._returned(dag, header)
        raise BuiltinError("unsupported builtin node role")

    def node(self, dag):
        if dag not in self.nodes:
            _charge(self.seen, dag)
            self.nodes[dag] = None
            self.nodes[dag] = self._read_node(dag)
        if self.nodes[dag] is None:
            raise BuiltinError("cyclic builtin node profile")
        return self.nodes[dag]


class Inspector:
    """Recompute fixed semantics without recording calls or executing user code."""

    def __init__(self, tx):
        self._tx = tx

    def node(self, dag: bytes) -> Description:
        return _Inspection(self._tx, set()).node(dag)

    def binding(self, dag: bytes) -> Binding:
        return inspect_binding(self._tx, dag)

    def arguments(self, dag: bytes) -> Arguments:
        return _expect(self.node(dag), Arguments)

    def operation(self, dag: bytes) -> Operation:
        return _expect(self.node(dag), Operation)

    def returned(self, dag: bytes) -> Return:
        return _expect(self.node(dag), Return)

    def trace(self, dag: bytes) -> tuple[Operation, ...]:
        return _Inspection(self._tx, set()).trace(dag)


def _author(action):
    @wraps(action)
    def checked(self, *args, **kwargs):
        if not self._active or self._failed:
            raise BuiltinError("builtin recording scope is inactive or poisoned")
        try:
            return action(self, *args, **kwargs)
        except BaseException:
            self._failed = True
            raise

    return checked


class NodeOperations:
    """The restricted operation interface passed to a logical callable."""

    __slots__ = ("__literal", "__map_get", "__list_get")

    def __init__(self, literal, map_get, list_get):
        self.__literal = literal
        self.__map_get = map_get
        self.__list_get = list_get

    def literal(self, kind: int, value: int | bytes) -> ValueNode:
        return self.__literal(kind, value)

    def map_get(self, container: ValueNode, key: bytes) -> ValueNode:
        return self.__map_get(container, key)

    def list_get(self, container: ValueNode, index: int) -> ValueNode:
        return self.__list_get(container, index)


class Recorder:
    """Single-use scope in a trusted wrapper's write transaction.

    Commit only after successful scope exit. An escaping error or a caught
    recording error aborts the entire supplied transaction. Distinct reached
    semantic DAGs (including bindings, trace and named source DAGs) are counted
    by native ID; identical operation IDs still occupy separate trace positions.
    """

    def __init__(self, tx):
        self._tx = tx
        self._seen = set()
        self._handles = {}
        self._positions = []
        self._active = self._entered = self._failed = False

    def __enter__(self):
        if self._entered:
            if self._active:
                self._failed = True
            raise BuiltinError("builtin recording scope cannot be reentered")
        self._active = self._entered = True
        return self

    def __exit__(self, kind, value, traceback):
        tx, self._tx = self._tx, None
        self._active = False
        self._handles.clear()
        if kind is not None or self._failed:
            core.txn_abort(tx)
            if kind is None:
                raise BuiltinError("caught error poisoned builtin recording scope")

    def _owned(self, node, reader):
        if type(node) is not ValueNode or node not in self._handles:
            raise BuiltinError("foreign or fabricated builtin value node")
        actual = reader.node(self._handles[node])
        if actual.value != node.value:
            raise BuiltinError("owned node value differs from native profile")
        return actual

    def _reader(self):
        return _Inspection(self._tx, self._seen)

    def _handle(self, dag, value):
        node = ValueNode(value)
        self._handles[node] = _charge(self._seen, dag)
        return node

    @_author
    def load(self, dag: bytes) -> ValueNode:
        """Reload an exact recorded node as a new handle in this scope."""
        actual = self._reader().node(dag)
        return self._handle(dag, actual.value)

    @_author
    def source(self, source_dag: bytes, name: bytes) -> ValueNode:
        """Select a named native literal in an explicit immutable source DAG."""
        tx = self._tx
        selected = _lookup(tx, _charge(self._seen, source_dag), name)
        _, value = _read_value(tx, selected)
        field = _put_literal(tx, core.DATUM_STRING, name)
        dag = _record(tx, SOURCE_ROLE, fields=((b"name", field), (b"value", selected)),
                      links=((b"source", source_dag),), root=b"value")
        return self._handle(dag, value)

    @_author
    def literal(self, kind: int, value) -> ValueNode:
        if kind == core.DATUM_I64 and type(value) is not int:
            raise BuiltinError("I64 literal requires an integer, not coercion")
        packed = core.datum_encode(kind, value)
        txn = self._tx
        node = _literal(txn, core.txn_put_datum(txn, packed))
        dag = _record(txn, LITERAL_ROLE, fields=((b"value", node),), root=b"value")
        return self._handle(dag, _datum(packed))

    def _argument_entries(self, entries):
        tx = self._tx
        reader = self._reader()
        found = {}
        for i, (key, source) in enumerate(entries.items() if isinstance(entries, Mapping) else entries):
            if i >= MAX_ARGUMENTS:
                raise BuiltinError("builtin argument limit exceeded")
            if type(key) is not bytes:
                raise BuiltinError("builtin argument key must be STRING bytes")
            packed = core.datum_encode(core.DATUM_STRING, key)
            canonical = _datum(packed).payload
            if canonical in found:
                raise BuiltinError("duplicate canonical argument key")
            found[canonical] = (core.txn_put_datum(tx, packed), self._owned(source, reader))
        return tuple(found[key] for key in sorted(found))

    @_author
    def arguments(self, entries=()) -> ValueNode:
        tx = self._tx
        entries = self._argument_entries(entries)
        packed = core.datum_encode(core.DATUM_MAP, tuple((key, source.datum) for key, source in entries))
        fields = [(b"value", _literal(tx, core.txn_put_datum(tx, packed)))]
        links = []
        for i, (key, source) in enumerate(entries):
            fields.append((_name(b"key", i), _literal(tx, key)))
            links.append((_name(b"source", i), source.dag))
        dag = _record(tx, ARGUMENTS_ROLE, fields=fields, links=links, root=b"value")
        return self._handle(dag, _datum(packed))

    @_author
    def call(self, func_uri: bytes, binding: bytes, arguments: ValueNode) -> ValueNode:
        if type(func_uri) is not bytes:
            raise BuiltinError("builtin func must be exact URI bytes")
        if len(self._positions) >= MAX_POSITIONS:
            raise BuiltinError("builtin call position limit exceeded")
        tx = self._tx
        reader = self._reader()
        args = _expect(self._owned(arguments, reader), Arguments)
        bound = reader.binding(binding)
        packed = _apply(tx, func_uri, bound, args)
        func = _put_literal(tx, core.DATUM_URI, func_uri)
        value = _literal(tx, core.txn_put_datum(tx, packed))
        dag = _record(tx, OPERATION_ROLE, fields=((b"func", func), (b"value", value)),
                      links=((b"binding", binding), (b"arguments", args.dag)), root=b"value")
        node = self._handle(dag, _datum(packed))
        self._positions.append(dag)
        return node

    @_author
    def dag(self, node: ValueNode) -> bytes:
        """Obtain the exact associated native DAG for trusted publication."""
        return self._owned(node, self._reader()).dag

    @_author
    def _map_get(self, binding, container, key):
        args = self.arguments({b"map": container, b"key": self.literal(core.DATUM_STRING, key)})
        return self.call(MAP_GET, binding, args)

    @_author
    def _list_get(self, binding, container, index):
        args = self.arguments({b"list": container, b"index": self.literal(core.DATUM_I64, index)})
        return self.call(LIST_GET, binding, args)

    @_author
    def _scalar_literal(self, kind, value):
        if type(kind) is not int or kind not in (core.DATUM_I64, core.DATUM_STRING):
            raise BuiltinError("logical literal requires I64 or STRING, not native IDs")
        return self.literal(kind, value)

    @_author
    def operations(self, *, map_binding: bytes, list_binding: bytes) -> NodeOperations:
        reader = self._reader()
        _handler(MAP_GET, reader.binding(map_binding).source_uri)
        _handler(LIST_GET, reader.binding(list_binding).source_uri)
        return NodeOperations(self._scalar_literal, lambda container, key: self._map_get(map_binding, container, key),
                              lambda container, index: self._list_get(list_binding, container, index))

    @_author
    def trace(self) -> bytes:
        links = tuple((_name(b"call", i), dag) for i, dag in enumerate(self._positions))
        return _charge(self._seen, _record(self._tx, TRACE_ROLE, links=links))

    @_author
    def returned(self, node: ValueNode, *, inputs: ValueNode) -> ValueNode:
        reader = self._reader()
        actual = self._owned(node, reader)
        args = _expect(self._owned(inputs, reader), Arguments)
        trace = self.trace()
        value = _literal(self._tx, actual.datum)
        dag = _record(self._tx, RETURN_ROLE, fields=((b"value", value),), root=b"value",
                      links=((b"returned", actual.dag), (b"trace", trace), (b"inputs", args.dag)))
        return self._handle(dag, actual.value)
