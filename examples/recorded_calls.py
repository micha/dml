"""Record and inspect local calls using ordinary DML objects.

Use `record REPO 7 5 3` to make both calls at once, or run
`record-sum REPO producer 7 5` and `record-scale REPO producer COMMIT result 3`
with the printed commit ID. Read either result with `inspect REPO [REF]`.
This example's call layouts are not core record types or execution APIs.
"""

import argparse
from contextlib import contextmanager
import json
from operator import add, mul
from pathlib import Path

from daggerml import core


ENTRY = b"recorded-calls-v1"
SUM_ENTRY = b"recorded-sum-v1"
SCALE_ENTRY = b"recorded-scale-v1"
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


@contextmanager
def _write_transaction(path, *, create):
    with _repository(path, create=create) as repo:
        txn = core.txn_begin(repo, core.TXN_WRITE)
        try:
            yield txn
            core.txn_commit(txn)
        finally:
            core.txn_abort(txn)  # Safe after commit consumes the handle.


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


def _record_sum(txn, a, b):
    left = _put_literal(txn, core.DATUM_I64, a)
    right = _put_literal(txn, core.DATUM_I64, b)
    return _record_call(txn, SUM, add, ((b"a", left), (b"b", right)))


def _record_scale(txn, sum_call, factor):
    source = _put_object(txn, core.REC_NODE, core.NODE_SUBDAG, sum_call)
    multiplier = _put_literal(txn, core.DATUM_I64, factor)
    return _record_call(txn, SCALE, mul, ((b"input", source), (b"factor", multiplier)), call_input=b"input")


def _publish(txn, ref, entry, dag, *parents):
    tree = _put_object(txn, core.REC_TREE, entry, dag)
    commit = _put_object(txn, core.REC_COMMIT, tree, *parents)
    core.txn_ref_create(txn, ref, commit)
    return commit


def record(path, a, b, factor):
    """Create a fresh repository and return the recorded commit ID."""
    for name, value in (("a", a), ("b", b), ("factor", factor)):
        _check_i64(value, name)
    Path(path).mkdir()  # Do not reuse or modify an existing path.
    with _write_transaction(path, create=True) as txn:
        sum_call = _record_sum(txn, a, b)
        scale_call = _record_scale(txn, sum_call, factor)
        return _publish(txn, MAIN, ENTRY, scale_call)


def record_sum(path, pin, a, b):
    """Publish a sum under a new pin and return its commit ID."""
    _check_i64(a, "a")
    _check_i64(b, "b")
    with _write_transaction(path, create=True) as txn:
        return _publish(txn, pin, SUM_ENTRY, _record_sum(txn, a, b))


def record_scale(path, producer_pin, producer_commit, result_ref, factor):
    """Scale the stored result of the exact pinned sum commit."""
    _check_i64(factor, "factor")
    if not isinstance(producer_commit, bytes) or len(producer_commit) != 16:
        raise ValueError("producer commit must be a 16-byte ID")
    with _write_transaction(path, create=False) as txn:
        selected = core.txn_ref_get(txn, producer_pin)
        if selected != producer_commit:
            raise ValueError("producer pin does not point to the expected commit")
        sum_call = _sum_dag(_snapshot(txn, selected))
        _inspect_call(txn, sum_call, SUM, (b"a", b"b"))  # Check shape, not arithmetic.
        scale_call = _record_scale(txn, sum_call, factor)
        return _publish(txn, result_ref, SCALE_ENTRY, scale_call, selected)


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


def _snapshot(txn, commit):
    commit_view, tree, parents = _object(txn, core.REC_COMMIT, commit)
    tree_view, _, entries = _object(txn, core.REC_TREE, tree)
    if entries != 1:
        raise ValueError("expected a single recorded-call tree entry")
    dag, entry = core.object_view_entry(tree_view, 0)
    return commit_view, parents, entry, dag


def _sum_dag(snapshot):
    _, parents, entry, dag = snapshot
    if parents != 0 or entry != SUM_ENTRY:
        raise ValueError("expected a parentless recorded-sum-v1 commit")
    return dag


def _inspect_snapshot(txn, commit):
    snapshot = _snapshot(txn, commit)
    view, parents, entry, terminal = snapshot
    report = {"commit": commit.hex()}
    if entry == SUM_ENTRY:
        dag = _sum_dag(snapshot)
        summed, _ = _inspect_call(txn, dag, SUM, (b"a", b"b"))
        return {**report, "calls": [summed]}
    if not ((entry == ENTRY and parents == 0) or (entry == SCALE_ENTRY and parents == 1)):
        raise ValueError("expected a recorded-calls-v1 or recorded-scale-v1 commit with its required parents")
    scale, producer = _inspect_call(txn, terminal, SCALE, (b"input", b"factor"), call_input=b"input")
    if entry == SCALE_ENTRY:
        parent = core.object_view_parent(view, 0)
        if _sum_dag(_snapshot(txn, parent)) != producer:
            raise ValueError("scale input DAG does not match the producer parent")
        report["producer_commit"] = parent.hex()
    summed, _ = _inspect_call(txn, producer, SUM, (b"a", b"b"))
    return {**report, "calls": [summed, scale]}


def inspect(path, ref=MAIN):
    """Read the committed example graph without executing or verifying arithmetic."""
    with _repository(path, create=False) as repo:
        txn = core.txn_begin(repo, core.TXN_READ)
        try:
            return _inspect_snapshot(txn, core.txn_ref_get(txn, ref))
        finally:
            core.txn_abort(txn)


def _parse_commit_id(text):
    try:
        identifier = bytes.fromhex(text)
    except ValueError:
        identifier = b""
    if len(text) != 32 or len(identifier) != 16:
        raise ValueError("producer commit must be a 32-digit hexadecimal ID")
    return identifier


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    writer = commands.add_parser("record", help="record two calls in a new repository")
    writer.add_argument("repo", type=Path)
    for name in ("a", "b", "factor"):
        writer.add_argument(name, type=int)
    producer = commands.add_parser("record-sum", help="record a sum and create its pin")
    producer.add_argument("repo", type=Path)
    producer.add_argument("pin")
    producer.add_argument("a", type=int)
    producer.add_argument("b", type=int)
    consumer = commands.add_parser("record-scale", help="scale the stored result of a pinned sum")
    consumer.add_argument("repo", type=Path)
    consumer.add_argument("producer_pin")
    consumer.add_argument("producer_commit")
    consumer.add_argument("result_ref")
    consumer.add_argument("factor", type=int)
    reader = commands.add_parser("inspect", help="read recorded calls from a ref (default: main)")
    reader.add_argument("repo", type=Path)
    reader.add_argument("ref", nargs="?", default="main")
    args = parser.parse_args()
    try:
        if args.command == "record":
            print(record(args.repo, args.a, args.b, args.factor).hex())
        elif args.command == "record-sum":
            print(record_sum(args.repo, args.pin.encode("ascii"), args.a, args.b).hex())
        elif args.command == "record-scale":
            commit = record_scale(args.repo, args.producer_pin.encode("ascii"), _parse_commit_id(args.producer_commit),
                                  args.result_ref.encode("ascii"), args.factor)
            print(commit.hex())
        else:
            print(json.dumps(inspect(args.repo, args.ref.encode("ascii"))))
    except (core.Error, OSError, ValueError) as error:
        parser.exit(1, f"{args.command}: {error}\n")


if __name__ == "__main__":
    main()
