"""Immutable implementation closures and a synchronous, owned node-call scope."""

from collections.abc import Callable, Collection, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from threading import current_thread

from . import builtin, core


CLOSURE_ROLE = b"implementation-call-closure-v1"
MAX_CAPTURES = 16
_METADATA = (b"role", b"intent", b"implementation")


class CallError(ValueError):
    """Invalid closure, call target, node, or scope."""


@dataclass(frozen=True, slots=True)
class Closure:
    dag: bytes
    intent: bytes
    implementation: bytes
    captures: tuple[tuple[bytes, bytes], ...]


def _capture_names(names: Collection[bytes]) -> tuple[bytes, ...]:
    if len(names) > MAX_CAPTURES:
        raise CallError("implementation capture limit exceeded")
    if any(type(name) is not bytes or name in _METADATA for name in names):
        raise CallError("closure capture names must be bytes and may not shadow metadata")
    if len(names) != len(set(names)):
        raise CallError("duplicate implementation capture name")
    return tuple(sorted(names))


def put_closure(txn, *, intent: bytes, implementation: bytes, captures: Mapping[bytes, bytes]) -> bytes:
    """Record two URI identifiers and exact named dependency DAG links."""
    if type(intent) is not bytes or type(implementation) is not bytes:
        raise CallError("closure intent and implementation require URI bytes")
    links = tuple((name, captures[name]) for name in _capture_names(captures))
    fields = ((b"intent", builtin._put_literal(txn, core.DATUM_URI, intent)),
              (b"implementation", builtin._put_literal(txn, core.DATUM_URI, implementation)))
    return builtin._record(txn, CLOSURE_ROLE, fields=fields, links=links)


def inspect_closure(txn, dag: bytes, *, names: Collection[bytes]) -> Closure:
    """Check the closure against the adapter's exact capture slots, not executable behavior."""
    names = _capture_names(names)
    header = builtin._header(txn, dag)
    fields = builtin._shape(txn, dag, header, (*_METADATA, *names), root=b"role")
    if builtin._scalar(txn, fields[b"role"], core.DATUM_STRING) != CLOSURE_ROLE:
        raise CallError("unexpected implementation closure role")
    intent = builtin._scalar(txn, fields[b"intent"], core.DATUM_URI)
    implementation = builtin._scalar(txn, fields[b"implementation"], core.DATUM_URI)
    captures = tuple((name, builtin._link(txn, fields[name])) for name in names)
    return Closure(dag, intent, implementation, captures)


@dataclass(eq=False, frozen=True, slots=True)
class Node:
    """A copied value; native provenance associations are owned by trusted adapters."""

    value: builtin.Datum


class Target:
    """An opaque, scoped token for one trusted binding."""

    __slots__ = ()


class Scope:
    """One synchronous call scope. Only pass its invoke method to logical code.

    Trusted adapters own native associations and publication. This interface is
    cooperative, not a sandbox or a validator of ordinary execution evidence.
    """

    def __init__(self):
        self._owner = None
        self._active = self._failed = False
        self._nodes = set()
        self._targets = {}

    def __enter__(self):
        if self._owner is not None:
            raise CallError("call scope cannot be reentered")
        self._owner = current_thread()
        self._active = True
        return self

    def __exit__(self, kind, value, traceback):
        if self._owner is not current_thread():
            raise CallError("call scope belongs to another thread")
        self._active = False
        self._targets.clear()
        self._nodes.clear()
        if kind is None and self._failed:
            raise CallError("caught error poisoned call scope")

    def _check(self):
        if self._owner is not current_thread() or not self._active or self._failed:
            raise CallError("call scope is foreign, inactive or poisoned")

    def copy(self, value: builtin.Datum) -> Node:
        self._check()
        if type(value) is not builtin.Datum or type(value.kind) is not int or type(value.payload) is not bytes:
            raise CallError("call scope requires a copied datum")
        node = Node(value)
        self._nodes.add(node)
        return node

    @contextmanager
    def bind(self, adapter: Callable[[Node], Node]) -> Iterator[Target]:
        self._check()
        target = Target()
        self._targets[target] = adapter
        try:
            yield target
        finally:
            self._targets.pop(target, None)

    @contextmanager
    def bind_builtin(self, recorder: builtin.Recorder, func: bytes, binding: bytes,
                     arguments: builtin.ValueNode) -> Iterator[tuple[Target, Node]]:
        """Bind a fixed builtin to one exact prepared argument node in its recorder."""
        owned = self.copy(arguments.value)

        def dispatch(node):
            if node is not owned:
                raise CallError("builtin call requires its exact prepared argument node")
            return self.copy(recorder.call(func, binding, arguments).value)

        with self.bind(dispatch) as target:
            yield target, owned

    def invoke(self, target: Target, arguments: Node) -> Node:
        """Invoke a scoped target on an owned argument MAP and return an owned node."""
        self._check()
        try:
            if type(target) is not Target or target not in self._targets:
                raise CallError("foreign or unbound call target")
            if type(arguments) is not Node or arguments not in self._nodes or arguments.value.kind != core.DATUM_MAP:
                raise CallError("invocation requires an owned argument MAP node")
            result = self._targets[target](arguments)
            # An adapter may catch a nested call error. Do not accept its result.
            self._check()
            if type(result) is not Node or result not in self._nodes:
                raise CallError("invocation returned a foreign node")
            return result
        except BaseException:
            self._failed = True
            raise
