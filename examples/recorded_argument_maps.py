"""Record typed argument maps and reuse a selected attempt by value, not derivation."""

import argparse
import json
from pathlib import Path
import sys
from typing import NamedTuple
from uuid import uuid4

from daggerml import core

import recorded_calls as records


REQUEST = b"argument-map-request-v1"
RESULT = b"argument-map-result-v1"
ATTEMPT = b"argument-map-attempt-v1"
TABLE = b"argument-map-table-v1"
DELTA = b"argument-map-table-edit-v1"
DECISION = b"argument-map-decision-v1"
MAX_ARGUMENTS = 16
MAX_TABLE_ENTRIES = 16
MAX_REACHED_ATTEMPTS = 64
FRESH, TRY, REQUIRE = b"fresh", b"try-selected", b"require-selected"
PENDING, REUSE = b"pending", b"reuse"


class Literal(NamedTuple):
    kind: int
    value: int | bytes


class Returned(NamedTuple):
    ref: bytes
    attempt: bytes


class Datum(NamedTuple):
    kind: int
    payload: bytes


class Argument(NamedTuple):
    key: bytes
    key_id: bytes
    key_node: bytes
    datum: bytes
    source_node: bytes
    attempt: bytes | None


class Request(NamedTuple):
    commit: bytes
    implementation: bytes
    construction: bytes
    datum: bytes
    arguments: dict[bytes, Argument]


class Attempt(NamedTuple):
    commit: bytes
    identity: bytes
    request: Request
    result: bytes
    result_dag: bytes
    datum: bytes
    value: int
    gets: tuple[Argument, ...]


def _as_i64(datum):
    if datum.kind != core.DATUM_I64:
        raise ValueError("expected an I64 argument")
    return int.from_bytes(datum.payload, "little", signed=True)


def _add(args, get):
    return _as_i64(get(args, b"a")) + _as_i64(get(args, b"b"))


def _double(args, get):
    return 2 * _as_i64(get(args, b"x"))


def _double_v2(args, get):
    value = _as_i64(get(args, b"x"))
    return value + value


# Fixed callables and return/trace profiles, not a plugin or evaluator API.
IMPLEMENTATIONS = {
    b"add@1": (b"add", (b"a", b"b"), _add),
    b"double@1": (b"double", (b"x",), _double),
    b"double@2": (b"double", (b"x",), _double_v2),
}
INTENTS = (b"add", b"double")


def _implementation(name):
    if type(name) is not bytes or name not in IMPLEMENTATIONS:
        raise ValueError("unknown argument-map implementation")
    return IMPLEMENTATIONS[name]


def _binding(txn, dag, name):
    return core.txn_lookup_node(txn, dag, name)


def _dag(txn, root, **bindings):
    fields = [field for name, node in bindings.items() for field in (name.encode("ascii"), node)]
    return records._put_object(txn, core.REC_DAG, root, *fields)


def _subdag(txn, dag):
    return records._put_object(txn, core.REC_NODE, core.NODE_SUBDAG, dag)


def _literal_node(txn, identifier):
    return records._put_object(txn, core.REC_NODE, core.NODE_LITERAL, identifier)


def _string(txn, value):
    return records._put_literal(txn, core.DATUM_STRING, value)


def _datum(txn, identifier):
    payload, kind = core.datum_decode(core.txn_get_datum(txn, identifier))
    return Datum(kind, payload)


def _literal(txn, node):
    return records._target(txn, node, core.NODE_LITERAL)


def _string_value(txn, node):
    return records._read_literal(txn, node, core.DATUM_STRING)


def _shape(txn, dag, count):
    _, root, actual = records._object(txn, core.REC_DAG, dag)
    if count != actual:
        raise ValueError("argument-map DAG has the wrong binding count")
    return root


def _snapshot(txn, commit, entry):
    view, count, actual, dag = records._snapshot(txn, commit)
    if entry != actual:
        raise ValueError(f"expected a {entry.decode('ascii')} commit")
    return dag, tuple(core.object_view_parent(view, i) for i in range(count))


def _map_packed(arguments):
    return core.datum_encode(core.DATUM_MAP, [(arg.key_id, arg.datum) for arg in arguments.values()])


def _map_node(txn, arguments):
    return _literal_node(txn, core.txn_put_datum(txn, _map_packed(arguments)))


def _expected_pin(txn, ref, commit, label):
    if records._optional_ref(txn, ref) != commit:
        raise ValueError(f"{label} ref does not match the expected commit or absence")


def _commit_id(value):
    if not records.COMMIT_HEX.fullmatch(value):
        raise ValueError("expected a lowercase hexadecimal object ID")
    return bytes.fromhex(value.decode("ascii"))


class History:
    """Revalidate one invocation's bounded graph using only immutable records."""

    def __init__(self, txn):
        self.txn = txn
        self.attempts = {}

    def _check_map(self, root, arguments):
        datum = _literal(self.txn, root)
        if core.txn_get_datum(self.txn, datum) != _map_packed(arguments):
            raise ValueError("argument MAP does not match its construction")
        return datum

    def _argument(self, dag, count, origins):
        txn = self.txn
        key_node = _binding(txn, dag, b"key")
        key = _string_value(txn, key_node)
        source = _binding(txn, dag, b"source")
        attempt = None
        if count == 4:
            attempt = _commit_id(_string_value(txn, _binding(txn, dag, b"origin")))
            if attempt not in origins:
                raise ValueError("returned source must be an exact request parent")
            produced = self.attempt(attempt)
            if records._target(txn, source, core.NODE_SUBDAG) != produced.result_dag:
                raise ValueError("returned source does not match the selected attempt result")
            datum = produced.datum
        else:
            datum = _literal(txn, source)
            if _datum(txn, datum).kind not in (core.DATUM_I64, core.DATUM_STRING):
                raise ValueError("map literal source must be I64 or STRING")
        return Argument(key, _literal(txn, key_node), key_node, datum, source, attempt)

    def _construction(self, dag, origins):
        txn = self.txn
        inserts = []
        while True:
            _, root, count = records._object(txn, core.REC_DAG, dag)
            if count == 0:  # map_empty
                break
            if count not in (3, 4) or len(inserts) >= MAX_ARGUMENTS:
                raise ValueError("invalid or over-limit map_insert construction")
            prior = records._target(txn, _binding(txn, dag, b"prior"), core.NODE_SUBDAG)
            inserts.append((dag, root, count))
            dag = prior
        arguments = {}
        datum = self._check_map(root, arguments)
        for dag, root, count in reversed(inserts):
            arg = self._argument(dag, count, origins)
            if arg.key in arguments:
                raise ValueError("duplicate canonical argument key")
            arguments[arg.key] = arg
            datum = self._check_map(root, arguments)
        used = tuple(sorted({arg.attempt for arg in arguments.values() if arg.attempt is not None}))
        if used != origins:
            raise ValueError("request parents must be exactly the returned sources in ID order")
        return datum, arguments

    def request(self, commit):
        txn = self.txn
        dag, parents = _snapshot(txn, commit, REQUEST)
        if len(parents) > MAX_ARGUMENTS:
            raise ValueError("too many returned source parents")
        root = _shape(txn, dag, 3)
        implementation = _string_value(txn, _binding(txn, dag, b"implementation"))
        _implementation(implementation)
        records._check_uuid4(_string_value(txn, _binding(txn, dag, b"invocation")), "invocation ID")
        construction = records._target(txn, _binding(txn, dag, b"construction"), core.NODE_SUBDAG)
        datum, arguments = self._construction(construction, parents)
        if _literal(txn, root) != datum:
            raise ValueError("request argument MAP differs from its construction")
        return Request(commit, implementation, construction, datum, arguments)

    def attempt(self, commit):
        if commit in self.attempts:
            attempt = self.attempts[commit]
            if attempt is None:
                raise ValueError("cyclic returned source history")
            return attempt
        if len(self.attempts) >= MAX_REACHED_ATTEMPTS:
            raise ValueError("too many reached argument-map attempts")
        self.attempts[commit] = None
        attempt = self._read_attempt(commit)
        self.attempts[commit] = attempt
        return attempt

    def _read_attempt(self, commit):
        txn = self.txn
        dag, parents = _snapshot(txn, commit, ATTEMPT)
        if len(parents) != 2:
            raise ValueError("attempt requires a request and a successful result")
        request_commit, result = parents
        root = _shape(txn, dag, 1)
        if root != _binding(txn, dag, b"attempt"):
            raise ValueError("attempt identity must be the root")
        identity = _string_value(txn, root)
        records._check_uuid4(identity, "attempt ID")
        result_dag, result_parents = _snapshot(txn, result, RESULT)
        if result_parents != (request_commit,):
            raise ValueError("result does not belong to the producing request")
        request = self.request(request_commit)
        _, names, _ = _implementation(request.implementation)
        datum = _literal(txn, _shape(txn, result_dag, len(names)))
        value = _as_i64(_datum(txn, datum))
        gets = []
        for i, key in enumerate(names):
            get = records._target(txn, _binding(txn, result_dag, _step(i)), core.NODE_SUBDAG)
            arg = request.arguments.get(key)
            construction = records._target(txn, _binding(txn, get, b"construction"), core.NODE_SUBDAG)
            if (arg is None or construction != request.construction or _binding(txn, get, b"key") != arg.key_node
                    or _literal(txn, _shape(txn, get, 2)) != arg.datum):
                raise ValueError("map_get trace does not match the producing construction")
            _as_i64(_datum(txn, arg.datum))
            gets.append(arg)
        return Attempt(commit, identity, request, result, result_dag, datum, value, tuple(gets))


def _put_construction(txn, sources):
    arguments = {}
    root = _map_node(txn, arguments)
    dag = _dag(txn, root)
    history = History(txn)
    for key, source in sources:
        key_node = _string(txn, key)
        name = _string_value(txn, key_node)
        if name in arguments:
            raise ValueError("duplicate canonical argument key")
        origin = {}
        producing_attempt = None
        if isinstance(source, Returned):
            records._check_ref_name(source.ref, "returned source")
            records._check_commit_id(source.attempt, "returned attempt")
            _expected_pin(txn, source.ref, source.attempt, "returned source")
            attempt = history.attempt(source.attempt)
            node = _subdag(txn, attempt.result_dag)
            datum = attempt.datum
            producing_attempt = attempt.commit
            origin["origin"] = _string(txn, producing_attempt.hex().encode("ascii"))
        else:
            if not isinstance(source, Literal) or source.kind not in (core.DATUM_I64, core.DATUM_STRING):
                raise ValueError("expected an I64 or STRING literal or an exact returned attempt")
            if source.kind == core.DATUM_I64:
                records._check_i64(source.value, "argument-map literal")
            node = records._put_literal(txn, source.kind, source.value)
            datum = _literal(txn, node)
        arguments[name] = Argument(name, _literal(txn, key_node), key_node, datum, node, producing_attempt)
        root = _map_node(txn, arguments)
        dag = _dag(txn, root, prior=_subdag(txn, dag), key=key_node, source=node, **origin)
    # Reserve one slot for the attempt of this invocation, the next returned source.
    if len(history.attempts) >= MAX_REACHED_ATTEMPTS:
        raise ValueError("too many reached argument-map attempts for a new invocation")
    parents = sorted({arg.attempt for arg in arguments.values() if arg.attempt is not None})
    return root, dag, parents


def _step(i):
    return f"get-{i:02d}".encode("ascii")


def _execute(txn, request):
    # The callable gets copied datums and a getter bound to this map. Recording
    # authority stays here; this is cooperative separation, not a Python sandbox.
    args = _datum(txn, request.datum)
    values = {key: _datum(txn, arg.datum) for key, arg in request.arguments.items()}
    accessed = []

    def get(arguments, key):
        if arguments is not args:
            raise ValueError("map_get requires this invocation's argument map")
        payload, _ = core.datum_decode(core.datum_encode(core.DATUM_STRING, key))
        if payload not in values:
            raise ValueError("map_get argument key was not found")
        if len(accessed) >= MAX_ARGUMENTS:
            raise ValueError("map_get trace limit reached")
        accessed.append(payload)
        return values[payload]

    _, names, operation = _implementation(request.implementation)
    value = operation(args, get)
    if tuple(accessed) != names:
        raise ValueError("map_get accesses do not match the implementation profile")
    records._check_i64(value, "argument-map result")
    return value, tuple(request.arguments[key] for key in accessed)


def work(path, request_ref, request_commit, attempt_ref, attempt_id):
    """Execute one attempt of a pinned request and publish its occurrence and trace."""
    records._check_intent_refs(("request", request_ref), ("attempt", attempt_ref))
    records._check_commit_id(request_commit, "request commit")
    records._check_uuid4(attempt_id, "attempt ID")
    with records._write_transaction(path, create=False) as txn:
        _expected_pin(txn, request_ref, request_commit, "request")
        history = History(txn)
        request = history.request(request_commit)
        if len(history.attempts) >= MAX_REACHED_ATTEMPTS:
            raise ValueError("too many reached argument-map attempts for a new invocation")
        value, gets = _execute(txn, request)
        root = records._put_literal(txn, core.DATUM_I64, value)
        bindings = []
        for i, arg in enumerate(gets):
            access = _dag(txn, _literal_node(txn, arg.datum), key=arg.key_node,
                          construction=_subdag(txn, request.construction))
            bindings.extend((_step(i), _subdag(txn, access)))
        dag = records._put_object(txn, core.REC_DAG, root, *bindings)
        result = records._put_snapshot(txn, RESULT, dag, request_commit)
        identity = _string(txn, attempt_id)
        attempt_dag = _dag(txn, identity, attempt=identity)
        return records._publish(txn, attempt_ref, ATTEMPT, attempt_dag, request_commit, result)


def _apply_edit(entries, intent, key, operation, attempt):
    if operation == b"remove":
        if key not in entries or attempt is not None:
            raise ValueError("remove requires a selected key and no attempt")
        del entries[key]
        return
    if attempt is None or attempt.request.datum != key or _implementation(attempt.request.implementation)[0] != intent:
        raise ValueError("selected attempt does not match the table intent and argument MAP")
    if operation == b"insert":
        if key in entries or len(entries) >= MAX_TABLE_ENTRIES:
            raise ValueError("insert requires an absent key and room in the table")
    elif operation == b"adopt":
        old = entries.get(key)
        if old is None or (old.request.commit, old.identity) == (attempt.request.commit, attempt.identity):
            raise ValueError("adopt requires a different attempt for an existing key")
    else:
        raise ValueError("expected table operation insert, adopt, or remove")
    entries[key] = attempt


def _read_table(txn, commit):
    edits = []
    while True:
        _, _, entry, _ = records._snapshot(txn, commit)
        if entry != DELTA:
            break
        dag, parents = _snapshot(txn, commit, DELTA)
        if len(parents) not in (1, 2):
            raise ValueError("table edit needs a basis and an optional attempt")
        key = _literal(txn, _shape(txn, dag, 1))
        if _datum(txn, key).kind != core.DATUM_MAP:
            raise ValueError("table edit key must be a MAP datum")
        op = _string_value(txn, _binding(txn, dag, b"operation"))
        edits.append((key, op, parents[1] if len(parents) == 2 else None))
        commit = parents[0]
    dag, parents = _snapshot(txn, commit, TABLE)
    if parents:
        raise ValueError("argument-map table genesis cannot have parents")
    intent = records._read_single_string(txn, dag, b"intent", "argument-map table")
    if intent not in INTENTS:
        raise ValueError("unknown argument-map intent")
    entries = {}
    for key, op, selected in reversed(edits):
        attempt = None if selected is None else History(txn).attempt(selected)
        _apply_edit(entries, intent, key, op, attempt)
    return intent, entries


def define_table(path, table_ref, intent):
    if intent not in INTENTS:
        raise ValueError("unknown argument-map intent")
    records._check_intent_refs(("table", table_ref))
    with records._write_transaction(path, create=True) as txn:
        root = _string(txn, intent)
        return records._publish(txn, table_ref, TABLE, _dag(txn, root, intent=root))


def update_table(path, basis_ref, basis, output_ref, operation, *, selected=None, key=None):
    """Create an immutable one-key table version, retaining the exact basis."""
    refs = [("basis", basis_ref), ("output", output_ref)]
    if operation == b"remove":
        if selected is not None:
            raise ValueError("remove does not accept a selected attempt")
        records._check_commit_id(key, "argument MAP datum")
    elif operation in (b"insert", b"adopt"):
        if not isinstance(selected, Returned) or key is not None:
            raise ValueError("insert and adopt require a selected attempt, not an explicit key")
        records._check_commit_id(selected.attempt, "selected attempt")
        refs.append(("selected", selected.ref))
    else:
        raise ValueError("expected table operation insert, adopt, or remove")
    records._check_intent_refs(*refs)
    records._check_commit_id(basis, "table basis")
    with records._write_transaction(path, create=False) as txn:
        _expected_pin(txn, basis_ref, basis, "table basis")
        intent, entries = _read_table(txn, basis)
        attempt = None
        parents = (basis,)
        if selected is not None:
            _expected_pin(txn, selected.ref, selected.attempt, "selected attempt")
            attempt = History(txn).attempt(selected.attempt)
            key = attempt.request.datum
            parents += (selected.attempt,)
        _apply_edit(entries, intent, key, operation, attempt)
        dag = _dag(txn, _literal_node(txn, key), operation=_string(txn, operation))
        return records._publish(txn, output_ref, DELTA, dag, *parents)


def _route(txn, request, mode, table):
    if mode == FRESH:
        if table is not None:
            raise ValueError("fresh decision cannot retain a consulted table")
        return None
    if mode not in (TRY, REQUIRE):
        raise ValueError("unknown argument-map routing mode")
    hit = None
    if table is not None:
        intent, entries = _read_table(txn, table)
        if intent != _implementation(request.implementation)[0]:
            raise ValueError("argument-map table belongs to a different intent")
        hit = entries.get(request.datum)
    if hit is None and mode == REQUIRE:
        raise ValueError("no selected attempt for the argument MAP")
    return hit


def request(path, request_ref, decision_ref, implementation, invocation, sources, *, mode=FRESH,
            table_ref=None, table_commit=None):
    """Record the exact construction and either leave work pending or reuse an old result."""
    _implementation(implementation)
    records._check_uuid4(invocation, "invocation ID")
    if mode not in (FRESH, TRY, REQUIRE):
        raise ValueError("unknown argument-map routing mode")
    if not isinstance(sources, (list, tuple)) or len(sources) > MAX_ARGUMENTS:
        raise ValueError("expected up to sixteen named arguments")
    refs = [("request", request_ref), ("decision", decision_ref)]
    if mode != FRESH:
        refs.append(("table", table_ref))
        if table_commit is not None:
            records._check_commit_id(table_commit, "table commit")
    records._check_intent_refs(*refs)
    with records._write_transaction(path, create=True) as txn:
        if mode != FRESH:
            _expected_pin(txn, table_ref, table_commit, "table")
        else:
            table_commit = None
        root, construction, sources_parents = _put_construction(txn, sources)
        dag = _dag(txn, root, implementation=_string(txn, implementation), invocation=_string(txn, invocation),
                   construction=_subdag(txn, construction))
        commit = records._put_snapshot(txn, REQUEST, dag, *sources_parents)
        requested = History(txn).request(commit)
        hit = _route(txn, requested, mode, table_commit)
        parents = (commit,) if table_commit is None else (commit, table_commit)
        outcome = _string(txn, PENDING if hit is None else REUSE)
        receipt = _dag(txn, outcome, outcome=outcome, mode=_string(txn, mode))
        if hit is None:
            core.txn_ref_create(txn, request_ref, commit)
        else:
            _expected_pin(txn, request_ref, None, "request output")
            records._update_main(txn, hit.result, records._optional_ref(txn, records.MAIN))
            parents += (hit.commit,)
        return records._publish(txn, decision_ref, DECISION, receipt, *parents)


def _read_decision(txn, commit):
    dag, parents = _snapshot(txn, commit, DECISION)
    if not 1 <= len(parents) <= 3:
        raise ValueError("argument-map decision has the wrong parents")
    root = _shape(txn, dag, 2)
    if root != _binding(txn, dag, b"outcome"):
        raise ValueError("argument-map decision must root its outcome")
    outcome = _string_value(txn, root)
    mode = _string_value(txn, _binding(txn, dag, b"mode"))
    requested = History(txn).request(parents[0])
    table = parents[1] if len(parents) >= 2 else None
    hit = _route(txn, requested, mode, table)
    expected = (PENDING, ()) if hit is None else (REUSE, (hit.commit,))
    if (outcome, parents[2:]) != expected:
        raise ValueError("recorded decision does not match the pinned argument-map route")
    return requested, mode, outcome, table, hit


def _argument_report(arg):
    return {"key": arg.key.decode("utf-8"), "datum": arg.datum.hex(), "node": arg.source_node.hex(),
            "attempt": arg.attempt.hex() if arg.attempt is not None else ""}


def _request_report(requested):
    return {"request": requested.commit.hex(), "implementation": requested.implementation.decode("ascii"),
            "construction": requested.construction.hex(), "argument_map": requested.datum.hex(),
            "arguments": [_argument_report(arg) for _, arg in sorted(requested.arguments.items())]}


def _attempt_report(attempt):
    return {"attempt": attempt.commit.hex(), "attempt_id": attempt.identity.decode("ascii"),
            "result": attempt.result.hex(), "value": attempt.value, "producing": _request_report(attempt.request),
            "map_gets": [_argument_report(arg) for arg in attempt.gets]}


def inspect(path, ref):
    """Read a decision, request, or attempt. Historical refs are not consulted."""
    with records._repository(path, create=False) as repo, records._read_transaction(repo) as txn:
        commit = core.txn_ref_get(txn, ref)
        _, _, entry, _ = records._snapshot(txn, commit)
        report = {"commit": commit.hex()}
        if entry == DECISION:
            requested, mode, outcome, table, hit = _read_decision(txn, commit)
            report.update(requested=_request_report(requested), mode=mode.decode("ascii"),
                          outcome=outcome.decode("ascii"), table=table.hex() if table is not None else "")
            if hit is not None:
                report.update(_attempt_report(hit))
        elif entry == REQUEST:
            report["requested"] = _request_report(History(txn).request(commit))
        elif entry == ATTEMPT:
            report.update(_attempt_report(History(txn).attempt(commit)))
        elif entry in (TABLE, DELTA):
            intent, entries = _read_table(txn, commit)
            report.update(intent=intent.decode("ascii"),
                          entries={key.hex(): row.commit.hex() for key, row in entries.items()})
        else:
            raise ValueError("expected an argument-map decision, request, attempt, or table")
        return report


def _cli_argument(text):
    key, sep, descriptor = text.partition("=")
    kind, divider, value = descriptor.partition(":")
    if sep and divider:
        if kind == "i64":
            return key.encode(), Literal(core.DATUM_I64, int(value))
        if kind == "string":
            return key.encode(), Literal(core.DATUM_STRING, value.encode())
        if kind == "from" and ":" in value:
            ref, commit = value.split(":", 1)
            return key.encode(), Returned(ref.encode(), _commit_id(commit.encode()))
    raise ValueError("argument must be KEY=i64:N, KEY=string:TEXT, or KEY=from:REF:ATTEMPT")


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command, fields in (
        ("request", ("request_ref", "decision_ref", "implementation")),
        ("work", ("request_ref", "request_commit", "attempt_ref")),
        ("define-table", ("table_ref", "intent")),
        ("update-table", ("basis_ref", "basis", "output_ref", "operation")),
        ("inspect", ("ref",)),
    ):
        sub = commands.add_parser(command)
        sub.add_argument("repo", type=Path)
        for field in fields:
            sub.add_argument(field, type=str.encode)
        if command == "request":
            sub.add_argument("--arg", action="append", default=[])
            sub.add_argument("--invocation", type=str.encode)
            sub.add_argument("--mode", choices=(FRESH, TRY, REQUIRE), type=str.encode, default=FRESH)
            sub.add_argument("--table-ref", type=str.encode)
            sub.add_argument("--table-commit", type=str.encode)
        elif command == "work":
            sub.add_argument("--attempt-id", type=str.encode)
        elif command == "update-table":
            sub.add_argument("--selected", nargs=2, type=str.encode, metavar=("REF", "ATTEMPT"))
            sub.add_argument("--key", type=str.encode)
    return parser


def main():
    args = _parser().parse_args()
    path = args.repo
    try:
        if args.command == "inspect":
            print(json.dumps(inspect(path, args.ref), sort_keys=True))
            return 0
        if args.command == "request":
            commit = request(path, args.request_ref, args.decision_ref, args.implementation,
                             args.invocation or str(uuid4()).encode(), [_cli_argument(arg) for arg in args.arg],
                             mode=args.mode, table_ref=args.table_ref,
                             table_commit=None if args.table_commit is None else _commit_id(args.table_commit))
        elif args.command == "work":
            commit = work(path, args.request_ref, _commit_id(args.request_commit), args.attempt_ref,
                          args.attempt_id or str(uuid4()).encode())
        elif args.command == "define-table":
            commit = define_table(path, args.table_ref, args.intent)
        else:
            selected = None if args.selected is None else Returned(args.selected[0], _commit_id(args.selected[1]))
            commit = update_table(path, args.basis_ref, _commit_id(args.basis), args.output_ref, args.operation,
                                  selected=selected, key=None if args.key is None else _commit_id(args.key))
        print(commit.hex())
        return 0
    except (core.Error, ValueError, TypeError, OverflowError) as error:
        print(f"{args.command}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
