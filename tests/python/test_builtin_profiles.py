"""Persisted profiles, native-source recomputation and REAL application bounds."""

import daggerml as d
from daggerml import builtin as b, transfer
import pytest

from test_builtin import state, construction, publish
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged


@pytest.fixture
def recorded(state):
    path, base, _, _, bindings, _ = state
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            sample = construction(rec, state)
            inputs = rec.arguments({"sample": sample})
            ops = rec.operations(map_binding=bindings["get1"], list_binding=bindings["index"])
            measured = ops.map_get(sample, "measurements")
            dag = rec.dag(measured)
            ledger = rec.trace()
            commit = publish(tx, base, ledger)
            full = rec.dag(inputs)
    return path, commit, dag, full, ledger


def forged(path, commit, dag, fields, *, root=None):
    with d.Repository(path) as repo, repo.write() as tx:
        changes = fields(tx) if callable(fields) else fields
        selected_root = root(tx) if callable(root) else root
        if selected_root is None and "value" in changes:
            selected_root = changes["value"]
        bad = clone(tx, dag, fields=changes, root=selected_root)
        entries = dict(tx.get_tree(tx.get_commit(commit).tree))
        entries["forged"] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(commit,))
    return basis, bad


@pytest.mark.parametrize("fault", ["source-name", "source-node", "source-value", "source-shape", "source-root", "operation-value", "operation-role", "operation-args", "operation-func", "argument-value", "argument-key", "entry-source", "entries-shape", "trace-shape", "trace-primitive"])
def test_strict_native_source_argument_operation_and_trace_recomputation(recorded, fault):
    path, commit, op, full, ledger = recorded
    with d.Repository(path) as repo, repo.read() as tx:
        arguments = b.link(tx, tx.get_dag(op).bindings["arguments"])
        rows = b.link(tx, tx.get_dag(arguments).bindings["entries"])
        first = b.link(tx, tx.get_dag(rows).bindings["arg-00"])
        # Find the original literal source in the operation graph.
        pending, seen, source = [full], set(), None
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            got = tx.get_dag(current)
            if b.scalar(tx, got.bindings["role"], "string") == b.SOURCE_ROLE:
                source = current
                break
            for node in got.bindings.values():
                obj = tx.get_node(node)
                if isinstance(obj, d.SubDAGNode):
                    pending.append(obj.dag)
        assert source is not None
    target = source if fault.startswith("source-") else op if fault.startswith("operation-") else arguments if fault == "argument-value" else first if fault in ("argument-key", "entry-source") else rows if fault == "entries-shape" else ledger
    root = None
    def changes(tx):
        if fault == "source-name":
            return {"name": b.literal(tx, "key")}
        if fault == "source-node":
            return {"node": b.literal(tx, bytes(16))}
        if fault in ("source-value", "operation-value", "argument-value"):
            return {"value": b.literal(tx, d.Datum.map(()))}
        if fault.endswith("shape"):
            return {"extra": b.literal(tx, 1)}
        if fault == "source-root":
            return {}
        if fault == "operation-role":
            return {"role": b.literal(tx, "not builtin")}
        if fault == "operation-args":
            return {"arguments": tx.put_subdag(full)}
        if fault == "operation-func":
            return {"func": b.literal(tx, d.Datum.uri(b.LIST_GET))}
        if fault == "argument-key":
            return {"key": b.literal(tx, 1)}
        if fault == "entry-source":
            return {"source": tx.put_subdag(op)}
        return {"call-00": tx.put_subdag(full)}
    if fault == "source-root":
        root = lambda tx: b.literal(tx, "wrong root")
    basis, bad = forged(path, commit, target, changes, root=root)
    with d.Repository(path) as repo, repo.read() as tx:
        inspector = b.Inspector(tx, commit=basis)
        if fault not in ("argument-key", "entry-source", "entries-shape"):
            with pytest.raises((b.BuiltinError, KeyError)):
                if fault.startswith("trace-"):
                    inspector.trace(bad)
                else:
                    inspector.node(bad)
        # Primitive fields wrong literal/SubDAG/type are also real native controls.
        with pytest.raises(b.BuiltinError, match="literal"):
            b.node_value(tx, tx.get_dag(op).bindings["arguments"])
        with pytest.raises(b.BuiltinError, match="sub-DAG"):
            b.link(tx, tx.get_dag(op).bindings["value"])
    if fault in ("argument-key", "entry-source", "entries-shape"):
        with d.Repository(path) as repo, repo.write() as tx:
            bad_rows = bad if fault == "entries-shape" else clone(tx, rows, fields={"arg-00": tx.put_subdag(bad)})
            bad_args = clone(tx, arguments, fields={"entries": tx.put_subdag(bad_rows)})
            entries = dict(tx.get_tree(tx.get_commit(basis).tree))
            entries["bad-arguments"] = bad_args
            final = tx.put_commit(tx.put_tree(entries), parents=(basis,))
        with d.Repository(path) as repo, repo.read() as tx:
            with pytest.raises(b.BuiltinError):
                b.Inspector(tx, commit=final).arguments(bad_args)


def test_exact_REAL64_reached_cap_and_prospective65_BEFORE_put(state, monkeypatch):
    path, base, _, _, bindings, _ = state
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            entries = dict(tx.get_tree(tx.get_commit(base).tree))
            for i in range(63):
                entries["literal-%02d" % i] = rec.dag(rec.literal(i))
            ledger = rec.trace()
            entries["trace"] = ledger
            assert len(rec.inspector.seen) == 64
            positive = tx.put_commit(tx.put_tree(entries), parents=(base,))
            tx.create_ref("real64", positive)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(b.BuiltinError, match="prospective"):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=positive) as rec:
                for dag in entries.values():
                    if dag not in bindings.values() and dag not in (state[2], state[3], state[5], ledger):
                        rec.load(dag)
                rec.inspector.trace(ledger)
                assert len(rec.inspector.seen) == 64
                original = tx.put_datum
                monkeypatch.setattr(d.Transaction, "put_datum", lambda *a: pytest.fail("prospective65 before first put"))
                rec.literal(999)
    assert_file_unchanged(path / "data.mdb", before)


def test_16positions_NOT_dedup_and_17_poison_NO_success(state):
    path, base, _, _, bindings, _ = state
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            args = rec.arguments()
            nodes = [rec.call(b.MAP_EMPTY, bindings["empty"], args) for _ in range(16)]
            assert len(set(rec.dag(node) for node in nodes)) == 1
            ledger = rec.trace()
            commit = publish(tx, base, ledger)
    with d.Repository(path) as repo, repo.read() as tx:
        assert len(b.Inspector(tx, commit=commit).trace(ledger)) == 16
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(b.BuiltinError, match="positions exceed16"):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=commit) as rec:
                args = rec.arguments()
                for _ in range(17):
                    rec.call(b.MAP_EMPTY, bindings["empty"], args)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["over16", "NFCduplicate", "nonstring", "missingargs", "keykind", "mapkind", "fullmap", "nonstring-map", "duplicate-insert", "v2-missing"])
def test_argument_MAP_limits_types_immutable_duplicates_common_preparation(state, fault):
    path, base, _, _, bindings, _ = state
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(b.BuiltinError):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                value = rec.literal(42)
                if fault == "over16":
                    rec.arguments({"k%d" % i: value for i in range(17)})
                elif fault == "NFCduplicate":
                    rec.arguments([("é", value), ("e\u0301", value)])
                elif fault == "nonstring":
                    rec.arguments({1: value})
                elif fault == "missingargs":
                    rec.call(b.MAP_GET, bindings["get1"], rec.arguments())
                elif fault == "duplicate-insert":
                    sample = construction(rec, state)
                    rec.call(b.MAP_INSERT, bindings["insert"], rec.arguments({"map": sample, "key": rec.literal("measurements"), "value": value}))
                elif fault == "v2-missing":
                    sample = construction(rec, state)
                    rec.call(b.MAP_GET, bindings["get2"], rec.arguments({"map": sample, "key": rec.literal("absent")}))
                else:
                    empty = rec.call(b.MAP_EMPTY, bindings["empty"], rec.arguments())
                    if fault == "fullmap":
                        pairs = [(tx.put_datum("key%d" % i), tx.put_datum(i)) for i in range(16)]
                        empty = rec.literal(d.Datum.map(pairs))
                    elif fault == "nonstring-map":
                        empty = rec.literal(d.Datum.map(((tx.put_datum(1), tx.put_datum(2)),)))
                    rec.call(b.MAP_INSERT, bindings["insert"], rec.arguments({"map": value if fault == "mapkind" else empty, "key": value if fault == "keykind" else rec.literal("new"), "value": value}))
    assert_file_unchanged(path / "data.mdb", before)


def test_unretained_foreign_invalid_source_handle_fields_and_inspector_bound_guards(state, recorded, monkeypatch):
    path, base, source, _, bindings, _ = state
    with d.Repository(path) as repo, repo.write() as tx:
        unrooted = b.record(tx, b.LITERAL_ROLE, nodes={"value": b.literal(tx, 999)}, root="value")
    with d.Repository(path) as repo, repo.read() as tx:
        inspector = b.Inspector(tx, commit=base)
        with pytest.raises(b.BuiltinError, match="not retained"):
            inspector.node(unrooted)
        with pytest.raises(b.BuiltinError, match="binding not retained"):
            inspector._binding(unrooted)
        inspector._enter(source)
        with pytest.raises(b.BuiltinError, match="cyclic"):
            inspector._enter(source)
    with pytest.raises(b.BuiltinError, match="named"):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                rec.source(unrooted, "value")
    with pytest.raises(b.BuiltinError, match="both"):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                rec.trace(request=source)
    with d.Repository(path) as repo, repo.read() as tx:
        monkeypatch.setattr(transfer, "MAX_OBJECTS", 1)
        with pytest.raises(b.BuiltinError, match="native closure"):
            b.Inspector(tx, commit=base)
