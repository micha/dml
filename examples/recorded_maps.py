"""Fixed recorded-map prototype; ordinary DAG conventions, NOT core operations.

Inspection recomputes only three fixed recipes. Logical callables get copied
Datum + bound map_get only; trusted wrapper authority is not a Python sandbox.
"""

from dataclasses import dataclass
import json
import re
import sys
import unicodedata

import daggerml as d
from daggerml import local, transfer
import reuse_selection as selection

PROFILE = "example-recorded-maps-v1"
LITERAL_ROLE = PROFILE + "-literal-source"
RETURNED_ROLE = PROFILE + "-returned-source"
OP_ROLE = PROFILE + "-operation"
INPUT_ROLE = PROFILE + "-input"
RETURN_ROLE = PROFILE + "-return"
TRACE_ROLE = PROFILE + "-trace"
MAX_ARGUMENTS = 16
MAX_ACCESSES = 16
MAX_RECORDS = 64


@dataclass(frozen=True)
class Value:
    dag: d.ObjectId
    datum: d.ObjectId
    value: d.Datum


@dataclass(frozen=True)
class Authored:
    base: d.ObjectId
    commit: d.ObjectId
    name: str
    dag: d.ObjectId
    datum: d.ObjectId


@dataclass(frozen=True)
class Inputs:
    dag: d.ObjectId
    datum: d.ObjectId
    value: d.Datum
    construction: d.ObjectId


@dataclass(frozen=True)
class Returned:
    dag: d.ObjectId
    node: d.ObjectId
    datum: d.ObjectId
    value: d.Datum
    request: d.ObjectId
    inputs: Inputs
    accesses: tuple


def name(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None:
        raise ValueError("explicit name outside native profile")
    return value


def map_size(value):
    if type(value) is not int or value < 0 or value > sys.maxsize or 0 < value < 1048576:
        raise ValueError("map_size outside unchanged profile")


def tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def literal(tx, value):
    return tx.put_literal(tx.put_datum(value))


def scalar(tx, node, kind):
    datum, value = node_value(tx, node)
    if value.kind != kind:
        raise ValueError("record scalar type differs")
    return value.value


def node_value(tx, node):
    got = tx.get_node(node)
    if not isinstance(got, d.LiteralNode):
        raise ValueError("record field must be literal")
    return got.datum, tx.get_datum(got.datum)


def link(tx, node):
    got = tx.get_node(node)
    if not isinstance(got, d.SubDAGNode):
        raise ValueError("record field must be sub-DAG")
    tx.get_dag(got.dag)
    return got.dag


def shape(tx, dag, names, root, role):
    got = tx.get_dag(dag)
    if set(got.bindings) != set(names) or got.root != got.bindings[root]:
        raise ValueError("record shape/root differs")
    if scalar(tx, got.bindings["role"], "string") != role:
        raise ValueError("record role differs")
    return got.bindings


def record(tx, role, values=(), links=(), root="role", nodes=()):
    fields = {"role": literal(tx, role)}
    fields.update({n: literal(tx, v) for n, v in dict(values).items()})
    fields.update({n: tx.put_subdag(v) for n, v in dict(links).items()})
    fields.update(dict(nodes))
    return tx.put_dag(root=fields[root], bindings=fields)


def map_pairs(value, tx):
    if value.kind != "map" or len(value.value) > MAX_ARGUMENTS:
        raise ValueError("bounded STRING argument MAP required")
    for key, item in value.value:
        if tx.get_datum(key).kind != "string":
            raise ValueError("argument map keys must be STRING")
        tx.get_datum(item)
    return dict(value.value)


class Inspector:
    """One bounded reached-profile inspection; no live handle during PUBLIC S calls."""

    def __init__(self, path, commit):
        self.path, self.commit = path, commit
        bundle = json.loads(transfer.export_commit(path, commit=commit))
        self.retained = {d.ObjectId.from_hex(row["id"]) for row in bundle["objects"] if row["kind"] == "dag"}
        self.values, self.inputs, self.returns, self.selections = {}, {}, {}, {}
        self.active, self.seen = set(), set()

    def reserve(self, count):
        if len(self.seen) + count > MAX_RECORDS:
            raise ValueError("prospective recorded-map reached profile exceeds64")

    def _enter(self, kind, oid):
        if oid not in self.retained:
            raise ValueError("source/profile DAG must be in pinned basis complete closure")
        key = kind, oid
        if key in self.active:
            raise ValueError("cyclic recorded-map profile")
        self.seen.add(key)
        if len(self.seen) > MAX_RECORDS or len(self.active) >= MAX_RECORDS:
            raise ValueError("recorded-map reached profile exceeds64")
        self.active.add(key)
        return key

    def selected(self, slot):
        if slot not in self.selections:
            self.selections[slot] = selection.inspect(self.path, commit=self.commit, slot=slot)
        return self.selections[slot]

    def source(self, dag):
        if dag in self.values:
            return self.values[dag]
        key = self._enter("source", dag)
        try:
            with d.Repository(self.path) as repo, repo.read() as tx:
                role = scalar(tx, tx.get_dag(dag).bindings["role"], "string")
                if role == LITERAL_ROLE:
                    fields = shape(tx, dag, ("role", "source", "name", "node", "result"), "result", role)
                    target = link(tx, fields["source"])
                    # _enter requires this descriptor in native-complete basis:
                    # its sub-DAG target is therefore in that same closure.
                    self.seen.add(("literal-dag", target))
                    self.reserve(0)
                    selected_name = scalar(tx, fields["name"], "string")
                    node = d.ObjectId(scalar(tx, fields["node"], "bytes"))
                    if tx.lookup_node(target, selected_name) != node:
                        raise ValueError("literal source named node differs")
                    actual, value = node_value(tx, node)
                    if node_value(tx, fields["result"])[0] != actual:
                        raise ValueError("literal source value association differs")
                    result = Value(dag, actual, value)
                elif role == RETURNED_ROLE:
                    fields = shape(tx, dag, ("role", "slot", "selection", "returned", "node", "result"), "result", role)
                    slot = scalar(tx, fields["slot"], "string")
                    selected, returned = (link(tx, fields[n]) for n in ("selection", "returned"))
                    node = d.ObjectId(scalar(tx, fields["node"], "bytes"))
                    claimed, value = node_value(tx, fields["result"])
                    result = None
                elif role == OP_ROLE:
                    opcode = scalar(tx, tx.get_dag(dag).bindings["opcode"], "string")
                    required = ("role", "opcode", "result")
                    if opcode == "map_insert":
                        required += ("prior", "key", "value")
                    elif opcode != "map_empty":
                        raise ValueError("construction accepts only empty/insert")
                    fields = shape(tx, dag, required, "result", role)
                    actual, value = node_value(tx, fields["result"])
                    pairs = map_pairs(value, tx)
                    operands = tuple(link(tx, fields[n]) for n in ("prior", "key", "value")) if opcode == "map_insert" else ()
                    result = None
                else:
                    raise ValueError("unknown recorded-map source role")
            # Every tx closed before recursion/public successful history projection.
            if role == RETURNED_ROLE:
                got = self.selected(slot)
                if (got.dag, got.result) != (selected, returned):
                    raise ValueError("returned source PUBLIC S/result differs")
                output = self.returned(returned, request=got.request, inputs=got.inputs)
                if (output.node, output.datum) != (node, claimed):
                    raise ValueError("returned source selected node/value differs")
                result = Value(dag, claimed, value)
            elif role == OP_ROLE:
                expected = {}
                if operands:
                    prior, key_source, value_source = (self.source(operand) for operand in operands)
                    if prior.value.kind != "map" or key_source.value.kind != "string":
                        raise ValueError("insert requires MAP prior and STRING key")
                    expected = dict(prior.value.value)
                    if key_source.datum in expected:
                        raise ValueError("duplicate canonical argument key")
                    expected[key_source.datum] = value_source.datum
                if pairs != expected:
                    raise ValueError("primitive result differs from recomputed operands")
                result = Value(dag, actual, value)
            self.values[dag] = result
            return result
        finally:
            self.active.remove(key)

    def input(self, dag):
        if dag in self.inputs:
            return self.inputs[dag]
        key = self._enter("input", dag)
        try:
            with d.Repository(self.path) as repo, repo.read() as tx:
                fields = shape(tx, dag, ("role", "arguments", "construction"), "arguments", INPUT_ROLE)
                datum, value = node_value(tx, fields["arguments"])
                map_pairs(value, tx)
                construction = link(tx, fields["construction"])
            got = self.source(construction)
            if got.datum != datum:
                raise ValueError("input argument datum differs from construction")
            result = Inputs(dag, datum, value, construction)
            self.inputs[dag] = result
            return result
        finally:
            self.active.remove(key)

    def access(self, dag, inputs):
        self.seen.add(("access", dag))
        if len(self.seen) > MAX_RECORDS:
            raise ValueError("recorded-map reached profile exceeds64")
        with d.Repository(self.path) as repo, repo.read() as tx:
            fields = shape(tx, dag, ("role", "opcode", "map", "key", "result"), "result", OP_ROLE)
            if scalar(tx, fields["opcode"], "string") != "map_get" or link(tx, fields["map"]) != inputs.construction:
                raise ValueError("getter must use THIS invocation construction")
            key, key_value = node_value(tx, fields["key"])
            actual, value = node_value(tx, fields["result"])
        if key_value.kind != "string" or dict(inputs.value.value).get(key) != actual:
            raise ValueError("getter key/result differs from actual argument map")
        return Value(dag, actual, value)

    def returned(self, dag, *, request, inputs):
        cache_key = dag, request, inputs
        if cache_key in self.returns:
            return self.returns[cache_key]
        key = self._enter("return", dag)
        try:
            with d.Repository(self.path) as repo, repo.read() as tx:
                fields = shape(tx, dag, ("role", "return", "trace"), "return", RETURN_ROLE)
                datum, value = node_value(tx, fields["return"])
                node = fields["return"]
                trace_dag = link(tx, fields["trace"])
                self.seen.add(("trace", trace_dag))
                self.reserve(0)
                trace = tx.get_dag(trace_dag)
                names = set(trace.bindings)
                count = len(names) - 3
                positions = tuple("access-%02d" % i for i in range(count))
                if not 0 <= count <= MAX_ACCESSES or names != {"role", "request", "inputs", *positions} or trace.root != trace.bindings["role"]:
                    raise ValueError("bounded ordered getter trace shape differs")
                if scalar(tx, trace.root, "string") != TRACE_ROLE or link(tx, trace.bindings["request"]) != request or link(tx, trace.bindings["inputs"]) != inputs:
                    raise ValueError("return trace owning Q/full input differs")
                q = tx.get_dag(request)
                if set(q.bindings) != {"role", "intent", "binding", "inputs"} or scalar(tx, q.bindings["role"], "string") != "local-request-v1" or link(tx, q.bindings["inputs"]) != inputs:
                    raise ValueError("return trace actual full Q differs")
                if re.fullmatch(r"q-[0-9a-f]{32}", scalar(tx, q.root, "string")) is None:
                    raise ValueError("return trace request occurrence differs")
                access_dags = tuple(link(tx, trace.bindings[n]) for n in positions)
            actual_input = self.input(inputs)
            accesses = tuple(self.access(got, actual_input) for got in access_dags)
            result = Returned(dag, node, datum, value, request, actual_input, accesses)
            self.returns[cache_key] = result
            return result
        finally:
            self.active.remove(key)


def inspect_source(path, *, commit, dag):
    transfer.export_commit(path, commit=commit)
    return Inspector(path, commit).source(dag)


def inspect_input(path, *, commit, dag):
    transfer.export_commit(path, commit=commit)
    return Inspector(path, commit).input(dag)


def inspect_returned(path, *, commit, slot):
    inspector = Inspector(path, commit)
    got = inspector.selected(slot)
    return inspector.returned(got.result, request=got.request, inputs=got.inputs)


def _publish(path, commit, output_name, ref, size, author):
    name(output_name)
    name(ref)
    map_size(size)
    with d.Repository(path, map_size=size) as repo, repo.write() as tx:
        entries = tree(tx, commit)
        if output_name in entries:
            raise ValueError("new metadata name must be absent")
        dag, datum = author(tx)
        entries[output_name] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = Authored(commit, authored, output_name, dag, datum)
    return response


def literal_source(path, *, commit, source_dag, source_name, output_name, ref, map_size=0):
    name(source_name)
    transfer.export_commit(path, commit=commit)
    with d.Repository(path) as repo, repo.read() as tx:
        if source_dag not in tree(tx, commit).values():
            raise ValueError("literal source DAG must be explicitly pinned in tree")
        node = tx.lookup_node(source_dag, source_name)
        datum, _ = node_value(tx, node)
    def author(tx):
        dag = record(tx, LITERAL_ROLE, {"name": source_name, "node": node.bytes}, {"source": source_dag}, "result", {"result": tx.put_literal(datum)})
        return dag, datum
    return _publish(path, commit, output_name, ref, map_size, author)


def returned_source(path, *, commit, slot, output_name, ref, map_size=0):
    inspector = Inspector(path, commit)
    selected = inspector.selected(slot)
    output = inspector.returned(selected.result, request=selected.request, inputs=selected.inputs)
    inspector.reserve(1)
    def author(tx):
        dag = record(tx, RETURNED_ROLE, {"slot": slot, "node": output.node.bytes}, {"selection": selected.dag, "returned": output.dag}, "result", {"result": tx.put_literal(output.datum)})
        return dag, output.datum
    return _publish(path, commit, output_name, ref, map_size, author)


def map_empty(path, *, commit, output_name, ref, map_size=0):
    transfer.export_commit(path, commit=commit)
    def author(tx):
        datum = tx.put_datum(d.Datum.map(()))
        return record(tx, OP_ROLE, {"opcode": "map_empty"}, root="result", nodes={"result": tx.put_literal(datum)}), datum
    return _publish(path, commit, output_name, ref, map_size, author)


def map_insert(path, *, commit, prior, key, value, output_name, ref, map_size=0):
    transfer.export_commit(path, commit=commit)
    inspector = Inspector(path, commit)
    previous, key_source, value_source = (inspector.source(got) for got in (prior, key, value))
    if previous.value.kind != "map" or key_source.value.kind != "string":
        raise ValueError("insert requires MAP prior and STRING key")
    with d.Repository(path) as repo, repo.read() as tx:
        pairs = map_pairs(previous.value, tx)
    inspector.reserve(1)
    if key_source.datum in pairs:
        raise ValueError("duplicate canonical argument key")
    if len(pairs) >= MAX_ARGUMENTS:
        raise ValueError("argument map exceeds16")
    pairs[key_source.datum] = value_source.datum
    def author(tx):
        datum = tx.put_datum(d.Datum.map(pairs.items()))
        dag = record(tx, OP_ROLE, {"opcode": "map_insert"}, {"prior": prior, "key": key, "value": value}, "result", {"result": tx.put_literal(datum)})
        return dag, datum
    return _publish(path, commit, output_name, ref, map_size, author)


def put_inputs(path, *, commit, construction, output_name, ref, map_size=0):
    inspector = Inspector(path, commit)
    value = inspector.source(construction)
    with d.Repository(path) as repo, repo.read() as tx:
        map_pairs(value.value, tx)
    inspector.reserve(1)
    def author(tx):
        dag = record(tx, INPUT_ROLE, links={"construction": construction}, root="arguments", nodes={"arguments": tx.put_literal(value.datum)})
        return dag, value.datum
    return _publish(path, commit, output_name, ref, map_size, author)


class DatumAccess:
    """Only documented callable method is map_get; private callback is trusted."""
    __slots__ = ("__get",)

    def __init__(self, get):
        self.__get = get

    def map_get(self, arguments, key):
        return self.__get(arguments, key)


def invoke(path, *, commit, inputs, func):
    """Validate/copy BEFORE calling func; no live repository supplied to it.

    Return actual access recipes for the trusted wrapper's single publication batch.
    Func accepts only bound argument MAP, not arbitrary datum navigation.
    """
    inspector = Inspector(path, commit)
    got = inspector.input(inputs)
    with d.Repository(path) as repo, repo.read() as tx:
        copied = {tx.get_datum(key).value: (key, item, tx.get_datum(item)) for key, item in got.value.value}
    recipes = []
    def get(arguments, key):
        if type(arguments) is not d.Datum or arguments != got.value:
            raise ValueError("getter accepts only bound argument MAP")
        if type(key) is not str:
            raise TypeError("getter key must be STRING")
        key = unicodedata.normalize("NFC", key)
        if key not in copied:
            raise KeyError("missing argument key")
        if len(recipes) >= MAX_ACCESSES:
            raise ValueError("getter trace exceeds16")
        key_id, item, value = copied[key]
        recipes.append((key_id, item))
        return value
    result = func(got.value, DatumAccess(get))
    if type(result) is not d.Datum:
        raise TypeError("logical callable must return explicit Datum")
    inspector.reserve(2 + len(set(recipes)))  # return + trace + distinct getter recipes
    return got, result, tuple(recipes)


def publish_callable(context, func):
    """Trusted standalone wrapper; all trace/R/publication in ONE child batch."""
    inputs, value, recipes = invoke(context.repository_path, commit=context.pre_dispatch, inputs=context.inputs, func=func)
    with d.Repository(context.repository_path) as repo, repo.write() as tx:
        accesses = {}
        for i, (key, item) in enumerate(recipes):
            dag = record(tx, OP_ROLE, {"opcode": "map_get"}, {"map": inputs.construction}, "result", {"key": tx.put_literal(key), "result": tx.put_literal(item)})
            accesses["access-%02d" % i] = dag
        trace = record(tx, TRACE_ROLE, links={"request": context.request, "inputs": inputs.dag, **accesses})
        returned = record(tx, RETURN_ROLE, links={"trace": trace}, root="return", nodes={"return": literal(tx, value)})
        return local.publish_result(tx, context, returned)
