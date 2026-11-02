"""Fixed internal versioned funcs and bounded ordinary value-node recording.

Native SubDAG nodes carry these semantic profiles; no native evaluator/opcode is
introduced. ValueNode exposes copied values only. Trusted Python is not sandboxed.
"""

from dataclasses import dataclass
from functools import wraps
import math
import re
import unicodedata

from . import Datum, LiteralNode, ObjectId, SubDAGNode

BINDING_ROLE = "builtin-binding-v1"
LITERAL_ROLE = "builtin-literal-v1"
SOURCE_ROLE = "builtin-literal-source-v1"
ARGUMENTS_ROLE = "builtin-arguments-v1"
ENTRIES_ROLE = "builtin-argument-entries-v1"
ENTRY_ROLE = "builtin-argument-entry-v1"
OPERATION_ROLE = "builtin-operation-v1"
TRACE_ROLE = "builtin-trace-v1"
RETURN_ROLE = "builtin-return-v1"
MAP_EMPTY = "dml://builtin/map/empty"
MAP_INSERT = "dml://builtin/map/insert"
MAP_GET = "dml://builtin/map/get"
LIST_GET = "dml://builtin/list/get"
MAX_ARGUMENTS = 16
MAX_POSITIONS = 16
MAX_RECORDS = 64


class BuiltinError(ValueError):
    """Unsupported binding or invalid semantic node/recording scope."""


def literal(tx, value):
    return tx.put_literal(tx.put_datum(value))


def _same_value(first, second):
    """Canonical copied datum equality; native F64 NaNs have ONE canonical value."""
    if type(first) is not Datum or type(second) is not Datum or first.kind != second.kind:
        return False
    if first.kind == "f64" and math.isnan(first.value) and math.isnan(second.value):
        return True
    return first == second


def node_value(tx, node):
    got = tx.get_node(node)
    if not isinstance(got, LiteralNode):
        raise BuiltinError("expected literal value field")
    return got.datum, tx.get_datum(got.datum)


def scalar(tx, node, kind):
    _, value = node_value(tx, node)
    if value.kind != kind:
        raise BuiltinError("wrong scalar kind: expected " + kind)
    return value.value


def link(tx, node):
    got = tx.get_node(node)
    if not isinstance(got, SubDAGNode):
        raise BuiltinError("expected sub-DAG field")
    tx.get_dag(got.dag)
    return got.dag


def record(tx, role, *, values=(), links=(), nodes=(), root="role"):
    fields = {"role": literal(tx, role)}
    fields.update((n, literal(tx, v)) for n, v in dict(values).items())
    fields.update((n, tx.put_subdag(v)) for n, v in dict(links).items())
    fields.update(dict(nodes))
    return tx.put_dag(root=fields[root], bindings=fields)


def shape(tx, dag, names, role, root="role"):
    got = tx.get_dag(dag)
    if set(got.bindings) != set(names) or got.root != got.bindings[root]:
        raise BuiltinError("semantic profile fields/root differ")
    if scalar(tx, got.bindings["role"], "string") != role:
        raise BuiltinError("semantic profile role differs")
    return got.bindings


@dataclass(frozen=True)
class Binding:
    dag: ObjectId
    source_uri: str


def inspect_binding(tx, dag):
    """Structural inspection allows unsupported URI versions, never executes them."""
    fields = shape(tx, dag, ("role", "adapter", "source", "interpreter", "timeout-ms"), BINDING_ROLE)
    for n in ("adapter", "interpreter", "timeout-ms"):
        scalar(tx, fields[n], "null")
    return Binding(dag, scalar(tx, fields["source"], "uri"))


def put_binding(tx, *, source_uri):
    """Record a strict internal descriptor; supported pairing is checked at invocation."""
    return record(tx, BINDING_ROLE, values={"adapter": None, "source": Datum.uri(source_uri),
                                         "interpreter": None, "timeout-ms": None})


def _map(tx, got):
    if got.value.kind != "map" or len(got.value.value) > MAX_ARGUMENTS:
        raise BuiltinError("bounded MAP required (at most16 entries)")
    for key, value in got.value.value:
        if tx.get_datum(key).kind != "string":
            raise BuiltinError("MAP keys must be STRING")
        tx.get_datum(value)
    return got.value.value


def _key(got):
    if got.value.kind != "string":
        raise BuiltinError("key must be STRING")
    return got.datum


def _map_empty(tx, args):
    return Datum.map(())


def _map_insert(tx, args):
    pairs = dict(_map(tx, args["map"]))
    key = _key(args["key"])
    if key in pairs:
        raise BuiltinError("duplicate canonical key")
    if len(pairs) >= MAX_ARGUMENTS:
        raise BuiltinError("insert exceeds16 entries")
    pairs[key] = args["value"].datum
    return Datum.map(pairs.items())


def _map_get_v1(tx, args):
    key = _key(args["key"])
    pairs = _map(tx, args["map"])
    for stored, value in pairs:
        if stored == key:
            return tx.get_datum(value)
    raise BuiltinError("missing map key")


def _map_get_v2(tx, args):
    key = _key(args["key"])
    pairs = dict(_map(tx, args["map"]))
    if key not in pairs:
        raise BuiltinError("missing map key")
    return tx.get_datum(pairs[key])


def _list_get(tx, args):
    container, index = args["list"], args["index"].value
    if container.value.kind != "list" or index.kind != "i64":
        raise BuiltinError("list/get requires LIST and I64 index")
    if not 0 <= index.value < len(container.value.value):
        raise BuiltinError("list index out of range")
    return tx.get_datum(container.value.value[index.value])


def _handler(func_uri, source_uri):
    # Exact fixed routing; no registry, URI imports/fetches, fallback or latest.
    if (func_uri, source_uri) == (MAP_EMPTY, "dml://source/builtin/map/empty/v1"):
        return (), _map_empty
    if (func_uri, source_uri) == (MAP_INSERT, "dml://source/builtin/map/insert/v1"):
        return ("map", "key", "value"), _map_insert
    if (func_uri, source_uri) == (MAP_GET, "dml://source/builtin/map/get/v1"):
        return ("map", "key"), _map_get_v1
    if (func_uri, source_uri) == (MAP_GET, "dml://source/builtin/map/get/v2"):
        return ("map", "key"), _map_get_v2
    if (func_uri, source_uri) == (LIST_GET, "dml://source/builtin/list/get/v1"):
        return ("list", "index"), _list_get
    raise BuiltinError("unsupported builtin func/source pairing")


@dataclass(frozen=True)
class Description:
    dag: ObjectId
    datum: ObjectId
    value: Datum


def _retained(tx, commit):
    """Native DAG reachability through ALL parents; no supplied membership flags."""
    from . import transfer
    pending, seen, dags = [("commit", commit)], set(), set()
    packed_bytes = 0
    while pending:
        kind, oid = pending.pop()
        if (kind, oid) in seen:
            continue
        seen.add((kind, oid))
        raw = tx.get_record(kind, oid)
        packed_bytes += len(raw)
        if (len(seen) > transfer.MAX_OBJECTS or len(raw) > transfer.MAX_RECORD_BYTES
            or packed_bytes > transfer.MAX_PACKED_BYTES):
            raise BuiltinError("native closure exceeds transfer profile")
        if kind == "commit":
            got = tx.get_commit(oid)
            pending.extend(("commit", p) for p in got.parents)
            pending.append(("tree", got.tree))
        elif kind == "tree":
            pending.extend(("dag", v) for v in tx.get_tree(oid).values())
        elif kind == "dag":
            dags.add(oid)
            got = tx.get_dag(oid)
            pending.extend(("node", v) for v in (got.root, *got.bindings.values()))
        elif kind == "node":
            got = tx.get_node(oid)
            if isinstance(got, SubDAGNode):
                pending.append(("dag", got.dag))
            else:
                pending.append(("datum", got.datum))
        else:
            got = tx.get_datum(oid)
            if got.kind in ("list", "set"):
                pending.extend(("datum", child) for child in got.value)
            elif got.kind == "map":
                pending.extend(("datum", child) for pair in got.value for child in pair)
    return dags


class Inspector:
    """Read-only fixed semantic recomputation, no recording dispatcher/source execution.

    Reached cap counts distinct native DAG IDs of semantic profiles, bindings,
    entry ledgers, trace ledgers and selected literal source DAGs. Shared content
    counts once; trace positions are independently bounded and never deduplicated.
    """

    def __init__(self, tx, *, commit):
        self.tx = tx
        self.retained = _retained(tx, commit)
        self.seen, self.active = set(), set()

    def reserve(self, count):
        if len(self.seen) + count > MAX_RECORDS:
            raise BuiltinError("prospective reached profile exceeds64")

    def _enter(self, dag):
        if dag not in self.retained:
            raise BuiltinError("node DAG not retained by pinned native history")
        if dag in self.active:
            raise BuiltinError("cyclic semantic profile")
        self.seen.add(dag)
        self.reserve(0)
        self.active.add(dag)

    def _binding(self, dag):
        if dag not in self.retained:
            raise BuiltinError("binding not retained")
        self.seen.add(dag)
        self.reserve(0)
        return inspect_binding(self.tx, dag)

    def arguments(self, dag):
        got, entries = self._arguments(dag)
        return got

    def _arguments(self, dag):
        tx = self.tx
        self._enter(dag)
        try:
            fields = shape(tx, dag, ("role", "value", "entries"), ARGUMENTS_ROLE, "value")
            datum, value = node_value(tx, fields["value"])
            description = Description(dag, datum, value)
            pairs = dict(_map(tx, description))
            rows = link(tx, fields["entries"])
            self._enter(rows)
            try:
                ledger = tx.get_dag(rows)
                positions = tuple("arg-%02d" % i for i in range(len(ledger.bindings) - 1))
                shape(tx, rows, ("role", *positions), ENTRIES_ROLE)
                if len(positions) > MAX_ARGUMENTS:
                    raise BuiltinError("arguments exceed16")
                result = {}
                actual = {}
                for n in positions:
                    entry = link(tx, ledger.bindings[n])
                    self._enter(entry)
                    try:
                        row = shape(tx, entry, ("role", "key", "source"), ENTRY_ROLE)
                        key, key_value = node_value(tx, row["key"])
                        if key_value.kind != "string" or key in actual:
                            raise BuiltinError("duplicate/non-STRING argument key")
                        source = self.node(link(tx, row["source"]))
                        actual[key] = source.datum
                        result[key_value.value] = source
                    finally:
                        self.active.remove(entry)
                if pairs != actual:
                    raise BuiltinError("argument value differs from actual source nodes")
                return description, result
            finally:
                self.active.remove(rows)
        finally:
            self.active.remove(dag)

    def trace(self, dag, *, request=None, inputs=None):
        tx = self.tx
        self._enter(dag)
        try:
            got = tx.get_dag(dag)
            fixed = ("role",) if request is None else ("role", "request", "inputs")
            positions = tuple("call-%02d" % i for i in range(len(got.bindings) - len(fixed)))
            fields = shape(tx, dag, (*fixed, *positions), TRACE_ROLE)
            if len(positions) > MAX_POSITIONS:
                raise BuiltinError("trace positions exceed16")
            if request is not None:
                if (link(tx, fields["request"]), link(tx, fields["inputs"])) != (request, inputs):
                    raise BuiltinError("trace owning Q/full inputs differ")
                q = tx.get_dag(request)
                if (set(q.bindings) != {"role", "intent", "binding", "inputs"}
                    or scalar(tx, q.bindings["role"], "string") != "local-request-v1"
                    or re.fullmatch(r"q-[0-9a-f]{32}", scalar(tx, q.root, "string")) is None
                    or link(tx, q.bindings["inputs"]) != inputs):
                    raise BuiltinError("actual Q/input profile differs")
                self.arguments(inputs)
            result = []
            for n in positions:
                operation = link(tx, fields[n])
                role = scalar(tx, tx.get_dag(operation).bindings["role"], "string")
                if role != OPERATION_ROLE:
                    raise BuiltinError("trace requires primitive operation nodes")
                result.append(self.node(operation))
            return tuple(result)
        finally:
            self.active.remove(dag)

    def node(self, dag):
        tx = self.tx
        role = scalar(tx, tx.get_dag(dag).bindings["role"], "string")
        if role == ARGUMENTS_ROLE:
            return self.arguments(dag)
        self._enter(dag)
        try:
            if role in (LITERAL_ROLE, SOURCE_ROLE):
                names = ("role", "value") if role == LITERAL_ROLE else ("role", "value", "source", "name", "node")
                fields = shape(tx, dag, names, role, "value")
                datum, value = node_value(tx, fields["value"])
                if role == SOURCE_ROLE:
                    target = link(tx, fields["source"])
                    self.seen.add(target)
                    self.reserve(0)
                    selected = tx.lookup_node(target, scalar(tx, fields["name"], "string"))
                    if (selected.bytes != scalar(tx, fields["node"], "bytes")
                        or node_value(tx, selected)[0] != datum):
                        raise BuiltinError("literal source node/value association differs")
            elif role == OPERATION_ROLE:
                fields = shape(tx, dag, ("role", "func", "binding", "arguments", "value"), role, "value")
                binding = self._binding(link(tx, fields["binding"]))
                names, handler = _handler(scalar(tx, fields["func"], "uri"), binding.source_uri)
                _, args = self._arguments(link(tx, fields["arguments"]))
                if set(args) != set(names):
                    raise BuiltinError("builtin exact argument names differ")
                datum, value = node_value(tx, fields["value"])
                # Native canonical value is compared without authoring a datum.
                expected = handler(tx, args)
                if expected.kind == "map":
                    expected = Datum.map(sorted(expected.value, key=lambda p: p[0].bytes))
                if not _same_value(value, expected):
                    raise BuiltinError("operation value differs from fixed semantics")
            elif role == RETURN_ROLE:
                fields = shape(tx, dag, ("role", "returned", "value", "trace", "request", "inputs"), role, "value")
                returned = self.node(link(tx, fields["returned"]))
                datum, value = node_value(tx, fields["value"])
                if datum != returned.datum:
                    raise BuiltinError("explicit returned node/value differ")
                self.trace(link(tx, fields["trace"]), request=link(tx, fields["request"]), inputs=link(tx, fields["inputs"]))
            else:
                raise BuiltinError("unsupported semantic node role")
            return Description(dag, datum, value)
        finally:
            self.active.remove(dag)


class ValueNode:
    """Copied computational value only; no public record/source/context navigation."""
    __slots__ = ("__value",)

    def __init__(self, value):
        self.__value = value

    @property
    def value(self):
        return self.__value


def _author(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        if self.ended or self.failed:
            raise BuiltinError("recording scope ended or poisoned")
        try:
            return method(self, *args, **kwargs)
        except BaseException:
            self.failed = True
            raise
    return guarded


class NodeOperations:
    """Bound datum-oriented callable interface, not trusted recorder/repository authority."""
    __slots__ = ("__literal", "__map_get", "__list_get")

    def __init__(self, literal_fn, map_fn, list_fn):
        self.__literal, self.__map_get, self.__list_get = literal_fn, map_fn, list_fn

    def literal(self, value):
        return self.__literal(value)

    def map_get(self, container, key):
        return self.__map_get(container, key)

    def list_get(self, container, index):
        return self.__list_get(container, index)


class Recorder:
    """Trusted wrapper-owned write scope; MUST use as context inside tx context.

    Caught authoring errors poison completion; context exit aborts the WHOLE supplied
    storage transaction. No pointers escape through ValueNode. Sources are re-read
    from strict native profiles each time a handle is consumed. Inspector cap plus
    conservative prospective additions precede each put (dedup can use less).
    """

    def __init__(self, tx, *, commit):
        self.tx, self.commit = tx, commit
        self.inspector = Inspector(tx, commit=commit)
        self.handles, self.positions = {}, []
        self.ended = self.failed = self.entered = False

    def __enter__(self):
        if self.ended or self.failed or self.entered:
            raise BuiltinError("recording scope ended, poisoned or already entered")
        self.entered = True
        return self

    def __exit__(self, kind, value, traceback):
        self.ended = True
        if kind is not None or self.failed:
            self.tx.abort()
            if kind is None:
                raise BuiltinError("caught error poisoned whole recording scope")

    def _owned(self, node):
        if type(node) is not ValueNode or node not in self.handles:
            raise BuiltinError("foreign or fabricated value node")
        actual = self.inspector.node(self.handles[node])
        if not _same_value(actual.value, node.value):
            raise BuiltinError("owned handle/native value association differs")
        return actual

    def _handle(self, dag):
        self.inspector.retained.add(dag)
        actual = self.inspector.node(dag)
        node = ValueNode(actual.value)
        self.handles[node] = dag
        return node

    def _new(self, dag):
        self.inspector.retained.add(dag)
        self.inspector.seen.add(dag)
        return dag

    @_author
    def load(self, dag):
        self.inspector.node(dag)
        return self._handle(dag)

    @_author
    def source(self, source_dag, name):
        entries = self.tx.get_tree(self.tx.get_commit(self.commit).tree)
        if source_dag not in entries.values():
            raise BuiltinError("source DAG must be named in pinned tree")
        selected = self.tx.lookup_node(source_dag, name)
        datum, _ = node_value(self.tx, selected)
        self.inspector.seen.add(source_dag)
        self.inspector.reserve(1)
        dag = record(self.tx, SOURCE_ROLE, values={"name": name, "node": selected.bytes},
                     links={"source": source_dag}, nodes={"value": self.tx.put_literal(datum)}, root="value")
        return self._handle(dag)

    @_author
    def literal(self, value):
        self.inspector.reserve(1)
        return self._handle(record(self.tx, LITERAL_ROLE, nodes={"value": literal(self.tx, value)}, root="value"))

    @_author
    def arguments(self, entries=()):
        items = list(entries.items()) if hasattr(entries, "items") else list(entries)
        if len(items) > MAX_ARGUMENTS:
            raise BuiltinError("arguments exceed16")
        canonical, values = [], {}
        for key, source in items:
            if type(key) is not str:
                raise BuiltinError("argument keys must be STRING")
            key = unicodedata.normalize("NFC", key)
            if key in values:
                raise BuiltinError("duplicate canonical argument key")
            actual = self._owned(source)
            values[key] = actual.datum
            canonical.append((key, actual.dag))
        self.inspector.reserve(2 + len(items))
        rows, pairs = {}, []
        for i, (key, source) in enumerate(sorted(canonical)):
            key_id = self.tx.put_datum(key)
            pairs.append((key_id, values[key]))
            rows["arg-%02d" % i] = self._new(record(self.tx, ENTRY_ROLE, nodes={"key": self.tx.put_literal(key_id)}, links={"source": source}))
        ledger = self._new(record(self.tx, ENTRIES_ROLE, links=rows))
        dag = record(self.tx, ARGUMENTS_ROLE, nodes={"value": literal(self.tx, Datum.map(pairs))}, links={"entries": ledger}, root="value")
        return self._handle(dag)

    @_author
    def call(self, func_uri, binding, arguments):
        actual = self._owned(arguments)
        _, args = self.inspector._arguments(actual.dag)
        bound = self.inspector._binding(binding)
        names, handler = _handler(func_uri, bound.source_uri)
        if set(args) != set(names):
            raise BuiltinError("builtin exact argument names differ")
        if len(self.positions) >= MAX_POSITIONS:
            raise BuiltinError("successful builtin positions exceed16")
        # Reserve one future enclosing trace ledger too; returned scope reserves R separately.
        self.inspector.reserve(2)
        value = handler(self.tx, args)
        dag = record(self.tx, OPERATION_ROLE, values={"func": Datum.uri(func_uri)},
                     links={"binding": binding, "arguments": actual.dag}, nodes={"value": literal(self.tx, value)}, root="value")
        node = self._handle(dag)
        self.positions.append(dag)
        return node

    @_author
    def dag(self, node):
        """Trusted authoring boundary; never supplied to logical callable."""
        return self._owned(node).dag

    @_author
    def _map_get(self, binding, container, key):
        self._owned(container)
        key_node = self.literal(Datum.string(key))
        return self.call(MAP_GET, binding, self.arguments({"map": container, "key": key_node}))

    @_author
    def _list_get(self, binding, container, index):
        self._owned(container)
        index_node = self.literal(Datum.i64(index))
        return self.call(LIST_GET, binding, self.arguments({"list": container, "index": index_node}))

    @_author
    def operations(self, *, map_binding, list_binding):
        # Validate exact choices now, even if a logical function makes no accesses.
        _handler(MAP_GET, self.inspector._binding(map_binding).source_uri)
        _handler(LIST_GET, self.inspector._binding(list_binding).source_uri)
        return NodeOperations(self.literal, lambda container, key: self._map_get(map_binding, container, key),
                              lambda container, index: self._list_get(list_binding, container, index))

    @_author
    def trace(self, *, request=None, inputs=None):
        if (request is None) != (inputs is None):
            raise BuiltinError("trace requires both request and inputs")
        self.inspector.reserve(1)
        links = {"call-%02d" % i: dag for i, dag in enumerate(self.positions)}
        if request is not None:
            links.update(request=request, inputs=inputs)
        dag = self._new(record(self.tx, TRACE_ROLE, links=links))
        self.inspector.trace(dag, request=request, inputs=inputs)
        return dag

    @_author
    def returned(self, node, *, request, inputs):
        actual = self._owned(node)
        self.inspector.arguments(inputs)
        self.inspector.reserve(2)
        trace = self.trace(request=request, inputs=inputs)
        dag = record(self.tx, RETURN_ROLE, links={"returned": actual.dag, "trace": trace, "request": request, "inputs": inputs},
                     nodes={"value": self.tx.put_literal(actual.datum)}, root="value")
        return self._handle(dag)


def publish_callable(context, func, *, map_binding, list_binding):
    """Common node call for one normal local wrapper, ONE child publication batch."""
    from . import Repository, local, transfer
    transfer.export_commit(context.repository_path, commit=context.pre_dispatch)
    with Repository(context.repository_path) as repo, repo.write() as tx:
        with Recorder(tx, commit=context.pre_dispatch) as recorder:
            arguments = recorder.load(context.inputs)
            recorder.inspector.arguments(context.inputs)
            ops = recorder.operations(map_binding=map_binding, list_binding=list_binding)
            result = func(arguments, ops)
            returned = recorder.returned(result, request=context.request, inputs=context.inputs)
            return local.publish_result(tx, context, recorder.dag(returned))
