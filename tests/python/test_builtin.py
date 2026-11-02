"""Fixed shipped builtin node semantics/routing/ownership/prospective poison gates."""

from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import daggerml as d
from daggerml import builtin as b, exchange as ex, local, transfer
import pytest
from hypothesis import given, strategies as st

from test_exchange import ROOT, typed_oracle
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged


@pytest.fixture
def state(tmp_path):
    path = tmp_path / "builtin"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        left, right = tx.put_datum(13), tx.put_datum(29)
        values = tx.put_datum(d.Datum.list((left, right)))
        nodes = {"list": tx.put_literal(values), "same-list": tx.put_literal(values), "key": b.literal(tx, "measurements")}
        source = tx.put_dag(root=nodes["list"], bindings=nodes)
        second = tx.put_dag(root=nodes["list"], bindings={**nodes, "method": b.literal(tx, "different source")})
        bindings = {n: b.put_binding(tx, source_uri="dml://source/builtin/" + suffix) for n, suffix in
                    (("empty", "map/empty/v1"), ("insert", "map/insert/v1"), ("get1", "map/get/v1"), ("get2", "map/get/v2"), ("index", "list/get/v1"))}
        external = local.put_local_binding(tx, source=b"raise SystemExit(0)", interpreter=sys.executable, timeout_ms=10000)
        base = tx.put_commit(tx.put_tree({**bindings, "source": source, "second": second, "external": external}))
        tx.create_ref("main", base)
    return path, base, source, second, bindings, external


def publish(tx, base, dag, name="scope"):
    entries = dict(tx.get_tree(tx.get_commit(base).tree))
    entries[name] = dag
    commit = tx.put_commit(tx.put_tree(entries), parents=(base,))
    tx.create_ref(name, commit)
    return commit


def construction(rec, state):
    source = rec.source(state[2], "list")
    empty = rec.call(b.MAP_EMPTY, state[4]["empty"], rec.arguments())
    result = rec.call(b.MAP_INSERT, state[4]["insert"], rec.arguments({"map": empty, "key": rec.literal("measurements"), "value": source}))
    return result


def test_actual_common_calls_nested_values_sources_URI_roundtrip_transfer_CLI(state, tmp_path, monkeypatch):
    path, base, source, second, bindings, _ = state
    before = typed_oracle(path, (base,))
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            sample = construction(rec, state)
            args = rec.arguments({"sample": sample})
            ops = rec.operations(map_binding=bindings["get1"], list_binding=bindings["index"])
            got = ops.map_get(args, "sample")
            measurements = ops.map_get(got, "measurements")
            left = ops.list_get(measurements, 0)
            right = ops.list_get(measurements, 1)
            assert left.value == d.Datum.i64(13) and right.value == d.Datum.i64(29)
            assert [n for n in dir(left) if not n.startswith("_")] == ["value"]
            assert [n for n in dir(ops) if not n.startswith("_")] == ["list_get", "literal", "map_get"]
            assert not hasattr(left, "__dict__")
            ledger = rec.trace()
            commit = publish(tx, base, ledger)
            sample_dag, args_dag = rec.dag(sample), rec.dag(args)
    assert left.value == d.Datum.i64(13)
    with pytest.raises(b.BuiltinError, match="ended"):
        ops.map_get(args, "sample")
    with d.Repository(path) as repo, repo.read() as tx:
        inspector = b.Inspector(tx, commit=commit)
        assert len(inspector.trace(ledger)) == 6
        assert inspector.arguments(args_dag).value.kind == "map"
        assert all(tx.get_record(*key) == raw for key, raw in before.items())
        assert b.inspect_binding(tx, bindings["get1"]).source_uri.endswith("v1")
        assert b.Inspector(tx, commit=commit).node(sample_dag).value == sample.value
    replica = tmp_path / "replica"
    with d.Repository(replica, create=True):
        pass
    transfer.import_commit(replica, transfer.export_commit(path, commit=commit), ref="retained")
    assert transfer.export_commit(replica, commit=commit) == transfer.export_commit(path, commit=commit)
    cli = subprocess.run([str(ROOT / "build/check/dml"), "--json", "--repo", str(replica), "walk", str(bindings["get1"])], capture_output=True, text=True)
    assert cli.returncode == 0 and "dml://source/builtin/map/get/v1" in cli.stdout


def test_real_v1_v2_exact_entrypoint_sentinels_and_NO_latest(state, monkeypatch):
    path, base, _, _, bindings, _ = state
    calls = []
    old, new = b._map_get_v1, b._map_get_v2
    def v1(tx, args):
        calls.append("v1")
        return old(tx, args)
    def v2(tx, args):
        calls.append("v2")
        return new(tx, args)
    monkeypatch.setattr(b, "_map_get_v1", v1)
    monkeypatch.setattr(b, "_map_get_v2", v2)
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            sample = construction(rec, state)
            args = rec.arguments({"map": sample, "key": rec.literal("measurements")})
            one = rec.call(b.MAP_GET, bindings["get1"], args)
            # Revalidation calls inspector fixed semantics too; assert target-specific delta.
            assert "v1" in calls and "v2" not in calls
            mark = len(calls)
            two = rec.call(b.MAP_GET, bindings["get2"], args)
            assert "v2" in calls[mark:]
            assert one.value == two.value
            assert rec.dag(one) != rec.dag(two)
            publish(tx, base, rec.trace())
    assert b._handler(b.MAP_GET, "dml://source/builtin/map/get/v1")[1] is v1
    assert b._handler(b.MAP_GET, "dml://source/builtin/map/get/v2")[1] is v2
    for func, source in ((b.MAP_GET, "dml://source/builtin/map/get/v99"), (b.MAP_EMPTY, "dml://source/builtin/map/get/v1"), ("dml://builtin/unknown", "dml://source/builtin/map/get/v1")):
        with pytest.raises(b.BuiltinError, match="unsupported"):
            b._handler(func, source)


@pytest.mark.parametrize("fault", ["role", "root", "extra", "missing", "adapter", "interpreter", "timeout-ms", "source-string", "source-bytes", "source-null", "unknown", "wrong-pair"])
def test_binding_strict_and_unsupported_before_handler_no_success(state, fault, monkeypatch):
    path, base, _, _, bindings, _ = state
    with d.Repository(path) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(bindings["empty"]).bindings)
        if fault == "missing":
            fields.pop("source")
        elif fault == "extra":
            fields["extra"] = b.literal(tx, 1)
        elif fault == "role":
            fields["role"] = b.literal(tx, "local-python-binding-v1")
        elif fault in ("adapter", "interpreter", "timeout-ms"):
            fields[fault] = b.literal(tx, "not NULL")
        elif fault.startswith("source-"):
            fields["source"] = b.literal(tx, "dml://source/builtin/map/empty/v1" if fault.endswith("string") else b"bytes" if fault.endswith("bytes") else None)
        elif fault in ("unknown", "wrong-pair"):
            fields["source"] = b.literal(tx, d.Datum.uri("dml://source/builtin/map/empty/v99" if fault == "unknown" else "dml://source/builtin/map/get/v1"))
        bad = tx.put_dag(root=b.literal(tx, "bad") if fault == "root" else fields["role"], bindings=fields)
        entries = dict(tx.get_tree(tx.get_commit(base).tree))
        entries["bad"] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(base,))
    before = (path / "data.mdb").read_bytes()
    monkeypatch.setattr(b, "_map_empty", lambda *a: pytest.fail("invalid binding must not invoke handler"))
    with pytest.raises(b.BuiltinError):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=basis) as rec:
                rec.call(b.MAP_EMPTY, bad, rec.arguments())
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["key-int", "key-bool", "index-bool", "index-float", "index-string", "index-overflow", "negative", "too-large", "missing", "wrong-map", "wrong-list", "foreign", "fabricated"])
def test_caught_convenience_error_poison_WHOLE_scope_prior_actual_primitive_ABSENT(state, fault):
    path, base, _, _, bindings, _ = state
    before = (path / "data.mdb").read_bytes()
    staged = []
    with pytest.raises(b.BuiltinError, match="poisoned"):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=base) as rec:
                # New operation not already in pinned store; actual durable absence oracle.
                sample = construction(rec, state)
                staged.append(rec.dag(sample))
                ops = rec.operations(map_binding=bindings["get1"], list_binding=bindings["index"])
                values = rec.source(state[2], "list")
                try:
                    if fault.startswith("key-"):
                        ops.map_get(sample, 1 if fault == "key-int" else True)
                    elif fault.startswith("index-"):
                        ops.list_get(values, {"index-bool": True, "index-float": 0.0, "index-string": "0", "index-overflow": 2**63}[fault])
                    elif fault in ("negative", "too-large"):
                        ops.list_get(values, -1 if fault == "negative" else 2)
                    elif fault == "missing":
                        ops.map_get(sample, "absent")
                    elif fault == "wrong-map":
                        ops.map_get(values, "measurements")
                    elif fault == "wrong-list":
                        ops.list_get(sample, 0)
                    elif fault == "foreign":
                        with b.Recorder(tx, commit=base) as other:
                            foreign = other.source(state[2], "list")
                        ops.list_get(foreign, 0)
                    else:
                        ops.map_get(b.ValueNode(sample.value), "measurements")
                except (b.BuiltinError, TypeError, OverflowError):
                    pass
                else:
                    pytest.fail("predicted convenience failure did not occur")
                assert rec.failed
                with pytest.raises(b.BuiltinError, match="poisoned"):
                    rec.literal(42)
                with pytest.raises(b.BuiltinError, match="poisoned"):
                    rec.trace()
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        for dag in staged:
            with pytest.raises(d.NotFoundError):
                tx.get_dag(dag)


def test_context_reentry_ended_reload_and_value_native_laundering(state):
    path, base, _, _, bindings, _ = state
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            with pytest.raises(b.BuiltinError, match="already entered"):
                rec.__enter__()
            node = construction(rec, state)
            dag = rec.dag(node)
            commit = publish(tx, base, rec.trace())
    with pytest.raises(b.BuiltinError):
        rec.__enter__()
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=commit) as next_rec:
            copy = next_rec.load(dag)
            assert copy.value == node.value and copy is not node
            next_rec.trace()
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(b.BuiltinError, match="association"):
        with d.Repository(path) as repo, repo.write() as tx:
            with b.Recorder(tx, commit=commit) as rec:
                copy = rec.load(dag)
                copy._ValueNode__value = d.Datum.i64(999)  # Trusted introspection, MUST NOT launder value.
                rec.arguments({"x": copy})
    assert_file_unchanged(path / "data.mdb", before)


def test_equal_nested_collections_THIS_source_not_global_origin(state):
    path, base, _, _, bindings, _ = state
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            a = rec.source(state[2], "list")
            c = rec.source(state[3], "list")
            assert a.value == c.value and rec.dag(a) != rec.dag(c)
            args = rec.arguments({"left": a, "right": c})
            ops = rec.operations(map_binding=bindings["get1"], list_binding=bindings["index"])
            left = ops.map_get(args, "left")
            right = ops.map_get(args, "right")
            assert left.value == right.value and rec.dag(left) != rec.dag(right)
            l = ops.list_get(left, 0)
            r = ops.list_get(right, 0)
            ld, rd = rec.dag(l), rec.dag(r)
            commit = publish(tx, base, rec.trace())
    with d.Repository(path) as repo, repo.read() as tx:
        for dag, expected in ((ld, left), (rd, right)):
            fields = tx.get_dag(dag).bindings
            operands = tx.get_dag(b.link(tx, fields["arguments"])).bindings
            rows = tx.get_dag(b.link(tx, operands["entries"]))
            sources = {b.scalar(tx, tx.get_dag(b.link(tx, row)).bindings["key"], "string"):
                       b.link(tx, tx.get_dag(b.link(tx, row)).bindings["source"]) for n, row in rows.bindings.items() if n != "role"}
            assert sources["list"] == rec.handles[expected]
        assert b.Inspector(tx, commit=commit).node(ld).value == d.Datum.i64(13)


@pytest.mark.parametrize("uri", ["dml://builtin/map/get", "dml:unknown", "DML:x"])
def test_reserved_external_all_authoring_and_persisted_retry_paths_NO_dispatch(state, uri, monkeypatch, tmp_path):
    path, base, source, _, _, external = state
    before = (path / "data.mdb").read_bytes()
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("reserved intent cannot dispatch"))
    with d.Repository(path) as repo, repo.write() as tx:
        with pytest.raises(local.ProtocolError, match="reserved"):
            local.put_local_request(tx, request_id="q-" + "1" * 32, intent_uri=uri, binding=external, inputs=source)
    with pytest.raises(local.ProtocolError):
        local.run_step(path, head_ref="main", intent_uri=uri, binding=external, inputs=source)
    with pytest.raises((ex.ExchangeError, d.DmlError)):
        ex.record_exchange_request(path, commit=base, binding_name="external", inputs_name="source", intent_uri=uri, ref="never")
    with pytest.raises((ex.ExchangeError, d.DmlError)):
        ex.prepare_exchange(path, commit=base, binding_name="external", inputs_name="source", intent_uri=uri, worker_ref="work", workspace=tmp_path / "never")
    assert_file_unchanged(path / "data.mdb", before)
    # Raw trusted write is not authentication, but supported retry/read must still reject.
    with d.Repository(path) as repo, repo.write() as tx:
        request = local._record(tx, "q-" + "1" * 32, {"role": "local-request-v1", "intent": d.Datum.uri(d.canonicalize_uri(uri))}, (("binding", external), ("inputs", source)))
        with pytest.raises(local.ProtocolError, match="reserved"):
            local._request(tx, request)
        entries = dict(tx.get_tree(tx.get_commit(base).tree))
        entries["request-q-" + "1" * 32] = request
        submission = tx.put_commit(tx.put_tree(entries), parents=(base,))
        tx.update_ref("main", submission)
        tx.create_ref("request-q-" + "1" * 32, submission)
    with pytest.raises(local.LocalExecutionError) as caught:
        local.retry_step(path, head_ref="main", request=request)
    assert isinstance(caught.value.__cause__, local.ProtocolError)
    with pytest.raises(local.LocalExecutionError) as first:
        local.run_request(path, head_ref="main", request_commit=submission, request=request)
    assert isinstance(first.value.__cause__, local.ProtocolError)


@given(st.sampled_from(["dml", "DML", "DmL"]), st.integers(min_value=1, max_value=99))
def test_native_URI_canonical_reference_profile(scheme, version):
    actual = d.canonicalize_uri(scheme + "://SOURCE/builtin/map/get/v" + str(version))
    assert actual == "dml://source/builtin/map/get/v" + str(version)


def test_blocker_FIRST_reader_real_controls_and_poisoned_helper_load(tmp_path):
    import hashlib
    import json
    reader = ROOT / "tests/builtins/offline_read.py"
    controls = subprocess.run([sys.executable, "-I", str(reader), "controls", str(tmp_path), str(tmp_path)], capture_output=True, text=True, timeout=15)
    assert controls.returncode == 0, controls.stderr
    assert json.loads(controls.stdout)["blockers"] == ["spawn", "http", "urllib-transport", "connect"]
    for name in ("caller.dml", "replica.dml"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "data.mdb").write_bytes(b"inert blocker control; not an LMDB store")
    probe = tmp_path / "installed_story.py"
    probe.write_text("import subprocess,sys\nsubprocess.Popen([sys.executable,'-c','raise SystemExit(99)'])\n")
    (tmp_path / "receipt.json").write_text(json.dumps({"sources": {probe.name: hashlib.sha256(probe.read_bytes()).hexdigest()}, "installed": {}}))
    refused = subprocess.run([sys.executable, "-I", str(reader), "read", str(tmp_path), str(tmp_path)], capture_output=True, text=True, timeout=15)
    assert refused.returncode != 0 and "offline reader cannot spawn" in refused.stderr


def test_canonical_F64_NaN_value_node_arguments_and_nested_getters_not_host_equality(state):
    import math
    path, base, source, second, bindings, external = state
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=base) as rec:
            nan = rec.literal(d.Datum.f64(float("nan")))
            args = rec.arguments({"nan": nan})
            ops = rec.operations(map_binding=bindings["get2"], list_binding=bindings["index"])
            mapped = ops.map_get(args, "nan")
            datum = b.node_value(tx, tx.get_dag(rec.dag(nan)).bindings["value"])[0]
            values = rec.literal(d.Datum.list((datum,)))
            indexed = ops.list_get(values, 0)
            for node in (nan, mapped, indexed):
                assert node.value.kind == "f64" and math.isnan(node.value.value)
                rec.dag(node)  # Native revalidation, not merely inspection of copied flags.
            negative_zero = rec.literal(d.Datum.f64(-0.0))
            assert negative_zero.value == d.Datum.f64(0.0)
            commit = publish(tx, base, rec.trace())
    with d.Repository(path) as repo, repo.read() as tx:
        trace = tx.get_tree(tx.get_commit(commit).tree)["scope"]
        actual = b.Inspector(tx, commit=commit).trace(trace)
        assert len(actual) == 2 and all(math.isnan(got.value.value) for got in actual)


@pytest.mark.parametrize("left,right,expected", [
    (d.Datum.f64(float("nan")), d.Datum.f64(float("nan")), True),
    (d.Datum.f64(float("nan")), d.Datum.f64(1.0), False),
    (d.Datum.f64(1.0), d.Datum.f64(float("nan")), False),
    (d.Datum.i64(1), d.Datum.f64(1.0), False),
    (d.Datum.bool(True), d.Datum.i64(1), False),
    (d.Datum.f64(1.0), d.Datum.f64(2.0), False),
    (d.Datum.f64(float("inf")), d.Datum.f64(float("inf")), True),
    (d.Datum.f64(float("inf")), d.Datum.f64(-float("inf")), False),
    (d.Datum.f64(-0.0), d.Datum.f64(0.0), True),
    (d.Datum.null(), d.Datum.null(), True),
    (d.Datum.string("x"), None, False),
    (None, d.Datum.string("x"), False),
    (d.Datum.list((d.ObjectId(bytes(16)),)), d.Datum.list((d.ObjectId(b"x" * 16),)), False),
    (d.Datum.map(((d.ObjectId(bytes(16)), d.ObjectId(b"x" * 16)),)),
     d.Datum.map(((d.ObjectId(bytes(16)), d.ObjectId(b"x" * 16)),)), True),
])
def test_pure_typed_canonical_value_equivalence_NO_write_or_kind_coercion(left, right, expected):
    assert b._same_value(left, right) is expected
