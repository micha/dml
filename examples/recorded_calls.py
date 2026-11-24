"""Record and inspect two local calls using ordinary DML objects.

Run `python examples/recorded_calls.py record REPO 7 5 3` with an installed
`daggerml.core`, then `python examples/recorded_calls.py inspect REPO`.
This example's call layout is not a core record type or execution API.
"""

import argparse
from contextlib import contextmanager
import json
from operator import add, mul
from pathlib import Path

from daggerml import core


ENTRY = b"recorded-calls-v1"
SUM = b"example.sum@1"
SCALE = b"example.scale@1"
MAIN = b"main"


@contextmanager
def _repository(path, *, create):
    repo = core.repo_open(path, create)
    try:
        yield repo
    finally:
        core.repo_close(repo)


def _check_i64(value, label):
    if type(value) is not int or not -(1 << 63) <= value < (1 << 63):
        raise ValueError(f"{label} is not a signed 64-bit integer")


def _put_object(txn, kind, *fields):
    return core.txn_put_object(txn, kind, core.object_encode(kind, *fields))


def _put_literal(txn, kind, value):
    datum = core.txn_put_datum(txn, core.datum_encode(kind, value))
    return _put_object(txn, core.REC_NODE, core.NODE_LITERAL, datum)


def _object(txn, kind, identifier):
    return core.object_decode(core.txn_get_object(txn, kind, identifier))


def _target(txn, node, node_kind):
    packed = core.txn_get_object(txn, core.REC_NODE, node)
    _, target, _ = core.object_decode(packed)
    # The binding returns the target but not the node kind. Check the declared
    # edge, not just whether a typed object with that target ID exists.
    if packed != core.object_encode(core.REC_NODE, node_kind, target):
        raise ValueError("recorded source has the wrong node kind")
    return target


def _read_literal(txn, node, expected_kind):
    target = _target(txn, node, core.NODE_LITERAL)
    payload, kind = core.datum_decode(core.txn_get_datum(txn, target))
    if kind != expected_kind:
        raise ValueError("recorded literal has the wrong datum kind")
    return payload


def _read_i64(txn, node):
    return int.from_bytes(_read_literal(txn, node, core.DATUM_I64), "little", signed=True)


def _read_source(txn, node, *, from_call):
    if not from_call:
        return _read_i64(txn, node), None
    # Resolve the actual producer and its root. Never look up a producer by value.
    producer = _target(txn, node, core.NODE_SUBDAG)
    _, result, _ = _object(txn, core.REC_DAG, producer)
    return _read_i64(txn, result), producer


def _record_call(txn, implementation, operation, sources, *, call_input=None):
    arguments = [_read_source(txn, node, from_call=name == call_input)[0] for name, node in sources]
    value = operation(*arguments)
    _check_i64(value, f"{implementation.decode('ascii')} result")
    result = _put_literal(txn, core.DATUM_I64, value)
    version = _put_literal(txn, core.DATUM_STRING, implementation)
    bindings = [field for binding in sources for field in binding]
    return _put_object(txn, core.REC_DAG, result, b"implementation", version, *bindings)


def record(path, a, b, factor):
    """Create a fresh repository and return the recorded commit ID."""
    for name, value in (("a", a), ("b", b), ("factor", factor)):
        _check_i64(value, name)
    Path(path).mkdir()  # Do not reuse or modify an existing path.
    with _repository(path, create=True) as repo:
        txn = core.txn_begin(repo, core.TXN_WRITE)
        try:
            left, right, multiplier = (_put_literal(txn, core.DATUM_I64, value) for value in (a, b, factor))
            sum_call = _record_call(txn, SUM, add, ((b"a", left), (b"b", right)))
            source = _put_object(txn, core.REC_NODE, core.NODE_SUBDAG, sum_call)
            scale_call = _record_call(txn, SCALE, mul, ((b"input", source), (b"factor", multiplier)),
                                      call_input=b"input")
            tree = _put_object(txn, core.REC_TREE, ENTRY, scale_call)
            commit = _put_object(txn, core.REC_COMMIT, tree)
            core.txn_ref_create(txn, MAIN, commit)
            core.txn_commit(txn)
            return commit
        finally:
            # Abort on Python or native write failure; safe after commit consumes the handle.
            core.txn_abort(txn)


def _inspect_call(txn, dag, implementation, names, *, call_input=None):
    _, result, count = _object(txn, core.REC_DAG, dag)
    if count != len(names) + 1:
        raise ValueError(f"wrong binding count for {implementation.decode('ascii')}")
    version = core.txn_lookup_node(txn, dag, b"implementation")
    if _read_literal(txn, version, core.DATUM_STRING) != implementation:
        raise ValueError(f"expected recorded implementation {implementation.decode('ascii')}")
    arguments = {}
    producer = None
    for name in names:
        node = core.txn_lookup_node(txn, dag, name)
        value, source = _read_source(txn, node, from_call=name == call_input)
        argument = {"node": node.hex(), "value": value}
        if source is not None:
            producer = source
            argument["call"] = producer.hex()
        arguments[name.decode("ascii")] = argument
    return {
        "dag": dag.hex(),
        "implementation": implementation.decode("ascii"),
        "result": {"node": result.hex(), "value": _read_i64(txn, result)},
        "arguments": arguments,
    }, producer


def inspect(path):
    """Read the committed example graph without executing or verifying arithmetic."""
    with _repository(path, create=False) as repo:
        txn = core.txn_begin(repo, core.TXN_READ)
        try:
            commit = core.txn_ref_get(txn, MAIN)
            _, tree, parents = _object(txn, core.REC_COMMIT, commit)
            view, _, entries = _object(txn, core.REC_TREE, tree)
            if parents or entries != 1:
                raise ValueError("expected one entry in a parentless recorded-calls commit")
            terminal, name = core.object_view_entry(view, 0)
            if name != ENTRY:
                raise ValueError("expected recorded-calls-v1 tree entry")
            scale, producer = _inspect_call(txn, terminal, SCALE, (b"input", b"factor"), call_input=b"input")
            summed, _ = _inspect_call(txn, producer, SUM, (b"a", b"b"))
            return {"commit": commit.hex(), "calls": [summed, scale]}
        finally:
            core.txn_abort(txn)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    writer = commands.add_parser("record", help="record two calls in a new repository")
    writer.add_argument("repo", type=Path)
    for name in ("a", "b", "factor"):
        writer.add_argument(name, type=int)
    reader = commands.add_parser("inspect", help="read the recorded calls from main")
    reader.add_argument("repo", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "record":
            print(record(args.repo, args.a, args.b, args.factor).hex())
        else:
            print(json.dumps(inspect(args.repo)))
    except (core.Error, OSError, ValueError) as error:
        parser.exit(1, f"{args.command}: {error}\n")


if __name__ == "__main__":
    main()
