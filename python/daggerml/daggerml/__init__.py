"""Low-level, transaction-scoped interfaces to the native DML repository."""

from __future__ import annotations

import functools
import os
import threading
import weakref
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Iterator, Mapping as MappingType, Tuple, Union

from . import _core

__all__ = [
    "version", "ObjectId", "Datum", "LiteralNode", "SubDAGNode", "DAG", "Tree", "Commit",
    "Repository", "Transaction", "canonicalize_uri", "DmlError", "NotFoundError",
    "InvalidStateError", "IntegrityError", "MapFullError",
]


class DmlError(Exception):
    """Native status, dependency code and diagnostic detail."""

    def __init__(self, code: str, native_code: int = 0, detail: str = "") -> None:
        self.code = code
        self.native_code = native_code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class NotFoundError(DmlError):
    pass


class InvalidStateError(DmlError):
    pass


class IntegrityError(DmlError):
    pass


class MapFullError(DmlError):
    pass


def _call(function, *args):
    try:
        return function(*args)
    except RuntimeError as error:
        if len(error.args) == 3:
            code, native_code, detail = error.args
            cls = {"not_found": NotFoundError, "invalid_state": InvalidStateError,
                   "integrity_error": IntegrityError, "map_full": MapFullError}.get(code, DmlError)
            raise cls(code, native_code, detail) from error
        raise InvalidStateError("invalid_state", detail=str(error)) from error


def version() -> str:
    return _core.dml_version()


@dataclass(frozen=True)
class ObjectId:
    bytes: bytes

    def __post_init__(self) -> None:
        if type(self.bytes) is not bytes:
            raise TypeError("ObjectId requires bytes")
        if len(self.bytes) != 16:
            raise ValueError("ObjectId requires exactly 16 bytes")

    @classmethod
    def from_hex(cls, text: str) -> ObjectId:
        if not isinstance(text, str):
            raise TypeError("hex ID requires str")
        return cls(_call(_core.parse_id, text))

    def __str__(self) -> str:
        return self.bytes.hex()


def _id(value: ObjectId) -> bytes:
    if not isinstance(value, ObjectId):
        raise TypeError("expected ObjectId, not an implicit ID or value")
    return value.bytes


_KINDS = ("null", "bool", "i64", "f64", "bytes", "string", "uri", "list", "set", "map")
_TYPES = {"datum": 2, "node": 3, "dag": 4, "tree": 5, "commit": 6}
_FACTORY_TOKEN = object()


@dataclass(frozen=True)
class Datum:
    kind: str
    value: object = None

    def __post_init__(self) -> None:
        kind, value = self.kind, self.value
        if kind not in _KINDS:
            raise ValueError("unknown datum kind")
        expected = {"null": type(None), "bool": bool, "i64": int, "f64": float,
                    "bytes": bytes, "string": str, "uri": str}
        if kind in expected:
            if type(value) is not expected[kind]:
                raise TypeError(f"{kind} requires {expected[kind].__name__}")
            if kind == "i64" and not -(2**63) <= value < 2**63:
                raise OverflowError("i64 out of signed 64-bit range")
        elif kind in ("list", "set"):
            value = tuple(value)
            for item in value:
                _id(item)
        else:
            value = tuple(tuple(pair) for pair in value)
            for pair in value:
                if len(pair) != 2:
                    raise ValueError("map entries require two IDs")
                _id(pair[0])
                _id(pair[1])
        object.__setattr__(self, "value", value)

    @classmethod
    def null(cls) -> Datum:
        return cls("null")

    @classmethod
    def bool(cls, value: bool) -> Datum:
        return cls("bool", value)

    @classmethod
    def i64(cls, value: int) -> Datum:
        return cls("i64", value)

    @classmethod
    def f64(cls, value: float) -> Datum:
        return cls("f64", value)

    @classmethod
    def bytes(cls, value: bytes) -> Datum:
        return cls("bytes", value)

    @classmethod
    def string(cls, value: str) -> Datum:
        return cls("string", value)

    @classmethod
    def uri(cls, value: str) -> Datum:
        return cls("uri", value)

    @classmethod
    def list(cls, items: Iterable[ObjectId]) -> Datum:
        return cls("list", items)

    @classmethod
    def set(cls, items: Iterable[ObjectId]) -> Datum:
        return cls("set", items)

    @classmethod
    def map(cls, pairs: Iterable[Tuple[ObjectId, ObjectId]]) -> Datum:
        return cls("map", pairs)


def _datum(value) -> Datum:
    if isinstance(value, Datum):
        return value
    kind = {type(None): "null", bool: "bool", int: "i64", float: "f64", bytes: "bytes", str: "string"}.get(type(value))
    if kind is None:
        raise TypeError("put_datum accepts Datum or an exact scalar type; collections require IDs")
    return Datum(kind, value)


def canonicalize_uri(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("URI requires str")
    return _call(_core.canonicalize_uri, text)


@dataclass(frozen=True)
class LiteralNode:
    datum: ObjectId

    def __post_init__(self) -> None:
        _id(self.datum)


@dataclass(frozen=True)
class SubDAGNode:
    dag: ObjectId

    def __post_init__(self) -> None:
        _id(self.dag)


@dataclass(frozen=True)
class DAG:
    root: ObjectId
    bindings: MappingType[str, ObjectId] = ()

    def __post_init__(self) -> None:
        _id(self.root)
        pairs = self.bindings.items() if isinstance(self.bindings, Mapping) else self.bindings
        copied = {}
        for name, node in pairs:
            if not isinstance(name, str):
                raise TypeError("binding name requires str")
            _id(node)
            if name in copied:
                raise ValueError("duplicate binding name")
            copied[name] = node
        object.__setattr__(self, "bindings", MappingProxyType(copied))


@dataclass(frozen=True)
class Tree(Mapping):
    entries: Tuple[Tuple[str, ObjectId], ...]

    def __post_init__(self) -> None:
        entries = tuple(tuple(pair) for pair in self.entries)
        for name, dag in entries:
            if not isinstance(name, str):
                raise TypeError("tree name requires str")
            _id(dag)
        object.__setattr__(self, "entries", entries)

    def __iter__(self) -> Iterator[str]:
        return (name for name, _ in self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, name: str) -> ObjectId:
        for key, dag in self.entries:
            if key == name:
                return dag
        raise KeyError(name)


@dataclass(frozen=True)
class Commit:
    tree: ObjectId
    parents: Tuple[ObjectId, ...] = ()

    def __post_init__(self) -> None:
        _id(self.tree)
        parents = tuple(self.parents)
        for parent in parents:
            _id(parent)
        object.__setattr__(self, "parents", parents)


def _mutation(function):
    @functools.wraps(function)
    def guarded(self, *args, **kwargs):
        self._check(write=True)
        try:
            return function(self, *args, **kwargs)
        except BaseException:
            self._failed = True
            raise
    return guarded


class Repository:
    """One creating-thread, single-active-transaction native repository owner."""

    def __init__(self, path: Union[str, bytes, os.PathLike], *, create: bool = False, map_size: int = 0) -> None:
        path = os.fsdecode(os.fspath(path))
        if "\0" in path:
            raise ValueError("repository path contains NUL")
        if type(create) is not bool or type(map_size) is not int:
            raise TypeError("create requires bool and map_size requires int")
        self._thread = threading.get_ident()
        self._handle = _call(_core.repo_open, path, create, map_size)
        self._active = None
        self._closed = False
        self._entered = False

    def _check(self) -> None:
        if threading.get_ident() != self._thread:
            raise InvalidStateError("invalid_state", detail="repository belongs to another thread")
        if self._closed:
            raise InvalidStateError("invalid_state", detail="repository is closed")

    @property
    def schema(self) -> int:
        self._check()
        return _call(_core.repo_schema, self._handle)

    def _transaction(self, write: bool) -> Transaction:
        self._check()
        active = self._active() if self._active else None
        if active is not None and not active._ended:
            raise InvalidStateError("invalid_state", detail="repository already has an active transaction")
        tx = Transaction(self, write, _token=_FACTORY_TOKEN)
        self._active = weakref.ref(tx)
        return tx

    def read(self) -> Transaction:
        return self._transaction(False)

    def write(self) -> Transaction:
        return self._transaction(True)

    def close(self) -> None:
        if threading.get_ident() != self._thread:
            raise InvalidStateError("invalid_state", detail="repository belongs to another thread")
        if not self._closed:
            _call(_core.repo_close, self._handle)
            self._closed = True

    def __enter__(self) -> Repository:
        self._check()
        if self._entered:
            raise InvalidStateError("invalid_state", detail="repository context already entered")
        self._entered = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if threading.get_ident() != self._thread:
            raise InvalidStateError("invalid_state", detail="repository belongs to another thread")
        if self._closed:
            return
        active = self._active() if self._active else None
        if active is not None:
            active.abort()
        self.close()


class Transaction:
    """Explicit native storage transaction; context commits only successful writes."""

    def __init__(self, owner: Repository, write: bool, *, _token=None) -> None:
        if _token is not _FACTORY_TOKEN:
            raise TypeError("use Repository.read() or Repository.write() to create transactions")
        owner._check()
        self._owner = owner
        self._handle = _call(_core.txn_begin, owner._handle, write)
        self._write = write
        self._ended = False
        self._entered = False
        self._failed = False

    def _check(self, *, write: bool = False) -> None:
        self._owner._check()
        if self._ended or self._failed:
            raise InvalidStateError("invalid_state", detail="transaction ended or failed")
        if write and not self._write:
            raise InvalidStateError("invalid_state", detail="read transaction cannot write")

    def __enter__(self) -> Transaction:
        self._check()
        if self._entered:
            raise InvalidStateError("invalid_state", detail="transaction context already entered")
        self._entered = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._ended:
            return
        if exc_type is not None or not self._write:
            self.abort()
        else:
            self.commit()

    def abort(self) -> None:
        if threading.get_ident() != self._owner._thread:
            raise InvalidStateError("invalid_state", detail="transaction belongs to another thread")
        if not self._ended:
            self._owner._check()
            _call(_core.txn_end, self._handle, False)
            self._ended = True

    def commit(self) -> None:
        self._owner._check()
        if self._failed:
            self.abort()
            raise InvalidStateError("invalid_state", detail="failed mutation; entire transaction aborted")
        self._check(write=True)
        try:
            _call(_core.txn_end, self._handle, True)
        finally:
            self._ended = True

    def get_record(self, kind: str, object_id: ObjectId) -> bytes:
        self._check()
        if kind not in _TYPES:
            raise ValueError("expected datum/node/dag/tree/commit")
        return _call(_core.get_record, self._handle, _TYPES[kind], _id(object_id))

    def get_datum(self, object_id: ObjectId) -> Datum:
        kind, value = _call(_core.decode_datum, self.get_record("datum", object_id))
        if kind in (8, 9):
            value = tuple(ObjectId(item) for item in value)
        elif kind == 10:
            value = tuple((ObjectId(key), ObjectId(item)) for key, item in value)
        return Datum(_KINDS[kind - 1], value)

    def _get_object(self, kind: str, object_id: ObjectId):
        return _call(_core.decode_object, self.get_record(kind, object_id))

    def get_node(self, object_id: ObjectId) -> Union[LiteralNode, SubDAGNode]:
        reference, kind = self._get_object("node", object_id)
        return (LiteralNode if kind == 1 else SubDAGNode)(ObjectId(reference))

    def get_dag(self, object_id: ObjectId) -> DAG:
        reference, entries = self._get_object("dag", object_id)
        return DAG(ObjectId(reference), tuple((name, ObjectId(node)) for name, node in entries))

    def lookup_node(self, dag: ObjectId, name: str) -> ObjectId:
        self._check()
        if not isinstance(name, str):
            raise TypeError("node name requires str")
        return ObjectId(_call(_core.lookup_node, self._handle, _id(dag), name))

    def get_tree(self, object_id: ObjectId) -> Tree:
        _, entries = self._get_object("tree", object_id)
        return Tree(tuple((name, ObjectId(dag)) for name, dag in entries))

    def get_commit(self, object_id: ObjectId) -> Commit:
        tree, parents = self._get_object("commit", object_id)
        return Commit(ObjectId(tree), tuple(ObjectId(parent) for parent in parents))

    def get_ref(self, name: str) -> ObjectId:
        self._check()
        if not isinstance(name, str):
            raise TypeError("ref name requires str")
        return ObjectId(_call(_core.ref_op, self._handle, 0, name, None))

    @_mutation
    def put_datum(self, value: Union[Datum, None, bool, int, float, bytes, str]) -> ObjectId:
        datum = _datum(value)
        value = datum.value
        if datum.kind in ("list", "set"):
            value = tuple(_id(item) for item in value)
        elif datum.kind == "map":
            value = tuple((_id(key), _id(item)) for key, item in value)
        record = _call(_core.encode_datum, _KINDS.index(datum.kind) + 1, value)
        return ObjectId(_call(_core.put_record, self._handle, 2, record))

    def _put_object(self, kind: str, value, parents=None) -> ObjectId:
        type_code = _TYPES[kind]
        record = _call(_core.encode_object, type_code, value, parents)
        return ObjectId(_call(_core.put_record, self._handle, type_code, record))

    @_mutation
    def put_literal(self, datum: ObjectId) -> ObjectId:
        return self._put_object("node", _id(datum), 1)

    @_mutation
    def put_subdag(self, dag: ObjectId) -> ObjectId:
        return self._put_object("node", _id(dag), 2)

    @_mutation
    def put_dag(self, *, root: ObjectId, bindings=()) -> ObjectId:
        pairs = bindings.items() if isinstance(bindings, Mapping) else bindings
        converted = []
        for name, node in pairs:
            if not isinstance(name, str):
                raise TypeError("binding name requires str")
            converted.append((name.encode("utf-8"), _id(node)))
        return self._put_object("dag", _id(root), tuple(converted))

    @_mutation
    def put_tree(self, entries: Union[MappingType[str, ObjectId], Iterable[Tuple[str, ObjectId]]]) -> ObjectId:
        pairs = entries.items() if isinstance(entries, Mapping) else entries
        converted = []
        for name, dag in pairs:
            if not isinstance(name, str):
                raise TypeError("tree name requires str")
            converted.append((name.encode("utf-8"), _id(dag)))
        return self._put_object("tree", tuple(converted))

    @_mutation
    def put_commit(self, tree: ObjectId, *, parents: Iterable[ObjectId] = ()) -> ObjectId:
        return self._put_object("commit", _id(tree), tuple(_id(parent) for parent in parents))

    @_mutation
    def create_ref(self, name: str, commit: ObjectId) -> None:
        if not isinstance(name, str):
            raise TypeError("ref name requires str")
        _call(_core.ref_op, self._handle, 1, name, _id(commit))

    @_mutation
    def update_ref(self, name: str, commit: ObjectId) -> None:
        if not isinstance(name, str):
            raise TypeError("ref name requires str")
        _call(_core.ref_op, self._handle, 2, name, _id(commit))
