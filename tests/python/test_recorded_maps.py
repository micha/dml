"""Focused fixed-map/public provenance controls; no acceptance-story repetition."""

from dataclasses import replace
import importlib.util
from pathlib import Path
import subprocess
import sys

import daggerml as d
from daggerml import transfer
import pytest
from hypothesis import given, strategies as st

from test_exchange import ROOT, exchange_runtime, typed_oracle
from test_exchange_records import clone
from test_caller_requests import assert_file_unchanged

pytest_plugins = ("reuse_test_cleanup",)

paths = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "examples"))
    import argument_map_binding as binding
    import argument_map_funcs as funcs
    import datum_reuse as reuse
    import recorded_maps as app
    spec = importlib.util.spec_from_file_location("argument_map_story_test", ROOT / "tests/argument_maps/installed_story.py")
    story = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(story)
finally:
    sys.path[:] = paths


@pytest.fixture
def state(tmp_path):
    path = tmp_path / "maps"
    base, literals = story.initialize(path, sys.executable, ROOT / "examples")
    current = base
    sources = {}
    for n in ("x", "left", "right", "n42", "n13", "n29", "n30"):
        got = app.literal_source(path, commit=current, source_dag=literals, source_name=n, output_name="source-" + n, ref="source-" + n)
        current, sources[n] = got.commit, got.dag
    inputs = story.construct(path, current, prefix="first", pairs=((sources["x"], sources["n42"]),))
    return path, base, literals, sources, inputs


@pytest.fixture
def success(state, exchange_runtime, tmp_path):
    path, _, _, _, inputs = state
    table = reuse.define_table(path, commit=inputs.commit, table_name="double-table", intent_uri=story.DOUBLE, ref="empty-table")
    q = story.request(path, table.commit, number=1, func="double", input_name=inputs.name)
    selected, child = story.execute(path, tmp_path, q, 1)
    indexed = reuse.select_entry(path, commit=selected.commit, table_name="double-table", selection_slot=selected.slot, ref="indexed")
    return path, q, selected, indexed, child


def changed(path, base, name, dag):
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, base)
        entries[name] = dag
        return tx.put_commit(tx.put_tree(entries), parents=(base,))


def test_exact_native_map_semantics_immutable_no_Q_T_source_and_full_input(state, monkeypatch, tmp_path):
    path, base, literals, sources, inputs = state
    before = typed_oracle(path, (inputs.commit,))
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("metadata never dispatches"))
        got = app.inspect_input(path, commit=inputs.commit, dag=inputs.dag)
        source = app.inspect_source(path, commit=inputs.commit, dag=got.construction)
    assert source.datum == got.datum == inputs.datum
    with d.Repository(path) as repo, repo.read() as tx:
        assert got.value.kind == "map"
        fields = tx.get_dag(source.dag).bindings
        prior = app.link(tx, fields["prior"])
        assert app.node_value(tx, tx.get_dag(prior).bindings["result"])[1] == d.Datum.map(())
        assert tx.get_commit(inputs.commit).parents == (inputs.base,)
        assert app.tree(tx, inputs.commit) == {**app.tree(tx, inputs.base), inputs.name: inputs.dag}
        assert tx.get_ref(inputs.name) == inputs.commit
        assert all(tx.get_record(*key) == raw for key, raw in before.items())
        for dag in app.tree(tx, inputs.commit).values():
            assert app.scalar(tx, tx.get_dag(dag).bindings["role"], "string") not in ("local-request-v1", "local-attempt-v1") if "role" in tx.get_dag(dag).bindings else True
    replica = tmp_path / "replica"
    with d.Repository(replica, create=True):
        pass
    transfer.import_commit(replica, transfer.export_commit(path, commit=inputs.commit))
    assert app.inspect_input(replica, commit=inputs.commit, dag=inputs.dag) == got


def test_datum_only_facade_actual_recipe_this_input_errors_and_repetition(state):
    path, _, _, sources, inputs = state
    calls = []
    def logical(arguments, values):
        assert type(arguments) is d.Datum and arguments.kind == "map"
        assert [n for n in dir(values) if not n.startswith("_")] == ["map_get"]
        assert not hasattr(values, "__dict__")
        for field in ("repository_path", "inputs", "construction", "context", "request", "get_datum", "lookup_node"):
            assert not hasattr(values, field)
        with pytest.raises(ValueError, match="bound"):
            values.map_get(d.Datum.map(()), "x")
        with pytest.raises(TypeError):
            values.map_get(arguments, 1)
        with pytest.raises(KeyError):
            values.map_get(arguments, "missing")
        for _ in range(16):
            calls.append(values.map_get(arguments, "x"))
        with pytest.raises(ValueError, match="exceeds16"):
            values.map_get(arguments, "x")
        return calls[0]
    got, result, recipes = app.invoke(path, commit=inputs.commit, inputs=inputs.dag, func=logical)
    assert result == d.Datum.i64(42) and len(recipes) == 16 and len(set(recipes)) == 1
    assert got.construction == app.inspect_input(path, commit=inputs.commit, dag=inputs.dag).construction
    with pytest.raises(TypeError, match="explicit Datum"):
        app.invoke(path, commit=inputs.commit, inputs=inputs.dag, func=lambda a, v: 42)
    assert app.invoke(path, commit=inputs.commit, inputs=inputs.dag, func=funcs.double)[1] == d.Datum.i64(84)
    add = story.construct(path, inputs.commit, prefix="add", pairs=((sources["left"], sources["n13"]), (sources["right"], sources["n29"])))
    assert app.invoke(path, commit=add.commit, inputs=add.dag, func=funcs.add)[1] == d.Datum.i64(42)
    with pytest.raises(ValueError, match="I64"):
        funcs.double(d.Datum.map(()), app.DatumAccess(lambda a, k: d.Datum.string("bad")))
    with pytest.raises(ValueError, match="I64"):
        funcs.add(d.Datum.map(()), app.DatumAccess(lambda a, k: d.Datum.f64(1.0)))


@pytest.mark.parametrize("fault", ["node", "value", "name", "role", "root", "extra", "missing"])
def test_literal_source_forgery_rejects_without_target_publication(state, fault):
    path, _, literals, sources, inputs = state
    with d.Repository(path) as repo, repo.write() as tx:
        original = sources["n42"]
        changes = {}
        if fault == "node":
            changes["node"] = app.literal(tx, tx.lookup_node(literals, "n13").bytes)
        elif fault == "value":
            changes["result"] = app.literal(tx, 13)
        elif fault == "name":
            changes["name"] = app.literal(tx, "n13")
        elif fault == "role":
            changes["role"] = app.literal(tx, "unknown")
        elif fault == "extra":
            changes["extra"] = app.literal(tx, True)
        fields = {**tx.get_dag(original).bindings, **changes}
        if fault == "missing":
            fields.pop("node")
        root = app.literal(tx, "bad") if fault == "root" else fields["result"]
        bad = tx.put_dag(root=root, bindings=fields)
        entries = app.tree(tx, inputs.commit)
        entries["bad"] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(inputs.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        app.map_insert(path, commit=basis, prior=inputs.dag, key=sources["x"], value=bad, output_name="never", ref="never")
    # Inspect forged source itself: wrong input type must not mask this oracle.
    with pytest.raises((ValueError, KeyError)):
        app.inspect_source(path, commit=basis, dag=bad)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["opcode", "result", "prior-type", "key-type", "shape"])
def test_primitive_recomputation_not_claimed_results(state, fault):
    path, _, _, sources, inputs = state
    construction = app.inspect_input(path, commit=inputs.commit, dag=inputs.dag).construction
    with d.Repository(path) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(construction).bindings)
        if fault == "opcode":
            fields["opcode"] = app.literal(tx, "arbitrary-code")
        elif fault == "result":
            fields["result"] = app.literal(tx, d.Datum.map(()))
        elif fault == "prior-type":
            fields["prior"] = tx.put_subdag(sources["n42"])
        elif fault == "key-type":
            fields["key"] = tx.put_subdag(sources["n42"])
        else:
            fields["extra"] = app.literal(tx, "bad")
        bad = tx.put_dag(root=fields["result"], bindings=fields)
        entries = app.tree(tx, inputs.commit)
        entries["bad"] = bad
        basis = tx.put_commit(tx.put_tree(entries), parents=(inputs.commit,))
    with pytest.raises(ValueError):
        app.inspect_source(path, commit=basis, dag=bad)


def test_pinned_complete_closure_not_unrooted_arbitrary_ID(state):
    path, base, literals, sources, inputs = state
    with d.Repository(path) as repo, repo.write() as tx:
        unrooted = app.record(tx, app.OP_ROLE, {"opcode": "map_empty"}, root="result", nodes={"result": app.literal(tx, d.Datum.map(()))})
    with pytest.raises(ValueError, match="complete closure"):
        app.inspect_source(path, commit=base, dag=unrooted)
    with pytest.raises(ValueError, match="pinned in tree"):
        app.literal_source(path, commit=base, source_dag=unrooted, source_name="result", output_name="bad", ref="bad")
    # Existing source descriptor keeps its explicitly selected target through DAG
    # closure even after its old direct tree name is removed.
    with d.Repository(path) as repo, repo.write() as tx:
        entries = app.tree(tx, inputs.commit)
        entries.pop("literals")
        basis = tx.put_commit(tx.put_tree(entries), parents=(inputs.commit,))
    assert app.inspect_source(path, commit=basis, dag=sources["n42"]).value == d.Datum.i64(42)


def native_map_source(path, commit, pairs, label):
    with d.Repository(path) as repo, repo.write() as tx:
        literal = app.literal(tx, d.Datum.map(pairs))
        dag = tx.put_dag(root=literal, bindings={"value": literal})
        entries = app.tree(tx, commit)
        entries[label] = dag
        basis = tx.put_commit(tx.put_tree(entries), parents=(commit,))
    return app.literal_source(path, commit=basis, source_dag=dag, source_name="value", output_name=label + "-source", ref=label + "-source")


@pytest.mark.parametrize("fault", ["non-string", "over16"])
def test_literal_MAP_prior_input_same_profile_before_authoring_no_target_rows(state, fault):
    path, _, _, sources, inputs = state
    with d.Repository(path) as repo, repo.write() as tx:
        value = tx.put_datum(1)
        keys = [tx.put_datum(i if fault == "non-string" else "key%d" % i) for i in range(1 if fault == "non-string" else 17)]
    source = native_map_source(path, inputs.commit, [(key, value) for key in keys], "map")
    before = (path / "data.mdb").read_bytes()
    for operation in (
        lambda: app.put_inputs(path, commit=source.commit, construction=source.dag, output_name="never", ref="never"),
        lambda: app.map_insert(path, commit=source.commit, prior=source.dag, key=sources["x"], value=sources["n42"], output_name="never", ref="never"),
    ):
        with pytest.raises(ValueError):
            operation()
        assert_file_unchanged(path / "data.mdb", before)
        with d.Repository(path) as repo, repo.read() as tx:
            with pytest.raises(d.NotFoundError):
                tx.get_ref("never")


def test_NFC_duplicate_and_missing_immutable_error(state):
    path, _, _, sources, inputs = state
    with d.Repository(path) as repo, repo.write() as tx:
        fields = {"composed": app.literal(tx, "é"), "decomposed": app.literal(tx, "e\u0301")}
        dag = tx.put_dag(root=fields["composed"], bindings=fields)
        entries = app.tree(tx, inputs.commit)
        entries["unicode"] = dag
        basis = tx.put_commit(tx.put_tree(entries), parents=(inputs.commit,))
    first = app.literal_source(path, commit=basis, source_dag=dag, source_name="composed", output_name="u1", ref="u1")
    second = app.literal_source(path, commit=first.commit, source_dag=dag, source_name="decomposed", output_name="u2", ref="u2")
    built = story.construct(path, second.commit, prefix="unicode-map", pairs=((first.dag, sources["n42"]),))
    construction = app.inspect_input(path, commit=built.commit, dag=built.dag).construction
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="duplicate canonical"):
        app.map_insert(path, commit=built.commit, prior=construction, key=second.dag, value=sources["n42"], output_name="duplicate", ref="duplicate")
    assert_file_unchanged(path / "data.mdb", before)
    assert app.invoke(path, commit=built.commit, inputs=built.dag, func=lambda a, v: v.map_get(a, "e\u0301"))[1] == d.Datum.i64(42)


def test_prospective64_operation_and_input_boundary_no_uninspectable_publication(tmp_path):
    path = tmp_path / "bounded"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        base = tx.put_commit(tx.put_tree({}))
    current = app.map_empty(path, commit=base, output_name="empty", ref="empty")
    source = current.dag
    previous_value = None
    for i in range(13):
        with d.Repository(path) as repo, repo.write() as tx:
            fields = {"key": app.literal(tx, "k%d" % i), "value": app.literal(tx, i)}
            kd = tx.put_dag(root=fields["key"], bindings={"key": fields["key"]})
            vd = tx.put_dag(root=fields["value"], bindings={"value": fields["value"]})
            entries = app.tree(tx, current.commit)
            entries.update({"key%d" % i: kd, "value%d" % i: vd})
            basis = tx.put_commit(tx.put_tree(entries), parents=(current.commit,))
        key = app.literal_source(path, commit=basis, source_dag=kd, source_name="key", output_name="ks%d" % i, ref="ks%d" % i)
        value = app.literal_source(path, commit=key.commit, source_dag=vd, source_name="value", output_name="vs%d" % i, ref="vs%d" % i)
        if i == 12:
            # Prior61 + key descriptor/target2 + value descriptor/target2 exceeds64.
            before = (path / "data.mdb").read_bytes()
            with pytest.raises(ValueError, match="exceeds64"):
                app.map_insert(path, commit=value.commit, prior=source, key=key.dag, value=value.dag, output_name="never", ref="never")
            assert_file_unchanged(path / "data.mdb", before)
            # Reuse the old value: prior61 + key2 + new operation1 ==64.
            current = app.map_insert(path, commit=value.commit, prior=source, key=key.dag, value=previous_value, output_name="boundary64", ref="boundary64")
        else:
            current = app.map_insert(path, commit=value.commit, prior=source, key=key.dag, value=value.dag, output_name="insert%d" % i, ref="insert%d" % i)
        source, previous_value = current.dag, value.dag
    inspector = app.Inspector(path, current.commit)
    inspector.source(source)
    assert len(inspector.seen) == 64
    # Exact real64 reached graph, no monkeypatched cap: internal guards reject
    # one MORE input/access record before examining its recipe. Not an accepted I.
    with pytest.raises(ValueError, match="exceeds64"):
        inspector._enter("input", source)
    inspector.seen.remove(("input", source))
    with pytest.raises(ValueError, match="exceeds64"):
        inspector.access(source, app.Inputs(source, current.datum, inspector.values[source].value, source))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="prospective"):
        app.put_inputs(path, commit=current.commit, construction=source, output_name="input65", ref="input65")
    assert_file_unchanged(path / "data.mdb", before)
    # A hand-authored otherwise exact I65 is a meaningful negative reader control,
    # not author API permission or a successful invocation.
    with d.Repository(path) as repo, repo.write() as tx:
        forged = app.record(tx, app.INPUT_ROLE, links={"construction": source}, root="arguments", nodes={"arguments": tx.put_literal(current.datum)})
        entries = app.tree(tx, current.commit)
        entries["forged65"] = forged
        basis = tx.put_commit(tx.put_tree(entries), parents=(current.commit,))
    with pytest.raises(ValueError, match="exceeds64"):
        app.inspect_input(path, commit=basis, dag=forged)


@pytest.mark.parametrize("changes", [{"output_name": "bad/name"}, {"ref": None}, {"map_size": True}, {"map_size": 1}])
def test_author_profile_invalid_no_publication(state, changes):
    path, _, _, _, inputs = state
    args = dict(commit=inputs.commit, output_name="new", ref="new")
    args.update(changes)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.map_empty(path, **args)
    assert_file_unchanged(path / "data.mdb", before)


@given(st.integers(min_value=-1000, max_value=1000))
def test_native_typed_identity_pure_fixed_callable(number):
    assert funcs.double(d.Datum.map(()), app.DatumAccess(lambda a, k: d.Datum.i64(number))) == d.Datum.i64(number * 2)


def test_capture_explicit_sources_standalone_and_invalid():
    source = binding.capture("double")
    assert b"types.ModuleType" in source and b"argument_map_funcs.double" in source
    for module in binding.MODULES:
        assert repr((ROOT / "examples" / (module + ".py")).read_bytes()).encode() in source
    with pytest.raises(ValueError):
        binding.capture("arbitrary")


@pytest.mark.parametrize("kind", ["i64", "f64", "list", "set", "map"])
def test_typed_composite_identity_source_independent_facade_childIDs_native_closure(state, kind):
    path, _, _, sources, inputs = state
    with d.Repository(path) as repo, repo.write() as tx:
        a, b = tx.put_datum(1), tx.put_datum(2)
        datum = d.Datum.i64(1) if kind == "i64" else d.Datum.f64(1.0) if kind == "f64" else d.Datum.list((a, b)) if kind == "list" else d.Datum.set((b, a)) if kind == "set" else d.Datum.map(((a, b),))
        node = app.literal(tx, datum)
        first = tx.put_dag(root=node, bindings={"value": node})
        second = tx.put_dag(root=node, bindings={"value": node, "extra": app.literal(tx, "other source")})
        entries = app.tree(tx, inputs.commit)
        entries.update(first=first, second=second)
        base = tx.put_commit(tx.put_tree(entries), parents=(inputs.commit,))
    left = app.literal_source(path, commit=base, source_dag=first, source_name="value", output_name="left-value", ref="left-value")
    right = app.literal_source(path, commit=left.commit, source_dag=second, source_name="value", output_name="right-value", ref="right-value")
    one = story.construct(path, right.commit, prefix="one", pairs=((sources["x"], left.dag),))
    two = story.construct(path, one.commit, prefix="two", pairs=((sources["x"], right.dag),))
    assert one.datum == two.datum and one.dag != two.dag
    got, result, _ = app.invoke(path, commit=two.commit, inputs=two.dag, func=lambda a, v: v.map_get(a, "x"))
    with d.Repository(path) as repo, repo.read() as tx:
        assert result == tx.get_datum(left.datum)
        assert left.datum != tx.get_node(tx.lookup_node(inputs.dag, "arguments")).datum
    reverse = story.construct(path, two.commit, prefix="reversed", pairs=((sources["right"], right.dag), (sources["left"], left.dag)))
    normal = story.construct(path, reverse.commit, prefix="normal", pairs=((sources["left"], left.dag), (sources["right"], right.dag)))
    assert reverse.datum == normal.datum and reverse.dag != normal.dag
    assert normal.datum != one.datum
    if kind == "list":
        with d.Repository(path) as repo, repo.write() as tx:
            assert tx.put_datum(d.Datum.list((b, a))) != left.datum
    if kind in ("i64", "f64"):
        with d.Repository(path) as repo, repo.write() as tx:
            assert tx.put_datum(d.Datum.i64(1)) != tx.put_datum(d.Datum.f64(1.0))


def test_input_and_primitive_error_guards_native_shapes_bounded_and_cycle(state):
    path, _, _, sources, inputs = state
    inspector = app.Inspector(path, inputs.commit)
    key = inspector._enter("source", sources["n42"])
    with pytest.raises(ValueError, match="cyclic"):
        inspector._enter("source", sources["n42"])
    inspector.active.remove(key)
    assert inspector.input(inputs.dag) == inspector.input(inputs.dag)
    construction = inspector.input(inputs.dag).construction
    with pytest.raises(ValueError, match="absent"):
        app.map_empty(path, commit=inputs.commit, output_name=inputs.name, ref="other")
    with pytest.raises(ValueError, match="STRING key"):
        app.map_insert(path, commit=inputs.commit, prior=construction, key=sources["n42"], value=sources["n13"], output_name="bad", ref="bad")
    with d.Repository(path) as repo, repo.write() as tx:
        bad = clone(tx, inputs.dag, fields={"arguments": app.literal(tx, d.Datum.map(()))}, root=app.literal(tx, d.Datum.map(())))
        entries = app.tree(tx, inputs.commit)
        entries["bad-input"] = bad
        base = tx.put_commit(tx.put_tree(entries), parents=(inputs.commit,))
    with pytest.raises(ValueError, match="differs from construction"):
        app.inspect_input(path, commit=base, dag=bad)
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(ValueError, match="literal"):
            app.node_value(tx, tx.get_dag(inputs.dag).bindings["construction"])
        with pytest.raises(ValueError, match="sub-DAG"):
            app.link(tx, tx.get_dag(inputs.dag).bindings["arguments"])
        with pytest.raises(ValueError, match="scalar type"):
            app.scalar(tx, tx.get_dag(inputs.dag).bindings["arguments"], "string")
    with d.Repository(path) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(construction).bindings)
        fields["prior"] = tx.put_subdag(construction)
        duplicated = tx.put_dag(root=fields["result"], bindings=fields)
        entries = app.tree(tx, base)
        entries["duplicate-recipe"] = duplicated
        basis = tx.put_commit(tx.put_tree(entries), parents=(base,))
    with pytest.raises(ValueError, match="duplicate canonical"):
        app.inspect_source(path, commit=basis, dag=duplicated)


def test_sixteen_argument_limit_prior_immutable_before_insert(state):
    path, _, _, sources, inputs = state
    with d.Repository(path) as repo, repo.write() as tx:
        value = tx.put_datum(42)
        pairs = [(tx.put_datum("k%d" % i), value) for i in range(16)]
    source = native_map_source(path, inputs.commit, pairs, "full")
    valid = app.put_inputs(path, commit=source.commit, construction=source.dag, output_name="full-input", ref="full-input")
    assert len(app.inspect_input(path, commit=valid.commit, dag=valid.dag).value.value) == 16
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="exceeds16"):
        app.map_insert(path, commit=valid.commit, prior=source.dag, key=sources["x"], value=sources["n42"], output_name="over", ref="over")
    assert_file_unchanged(path / "data.mdb", before)


def bounded_construction(path, base):
    current = app.map_empty(path, commit=base, output_name="bounded-empty", ref="bounded-empty")
    for i in range(12):
        with d.Repository(path) as repo, repo.write() as tx:
            keynode, valnode = app.literal(tx, "k%d" % i), app.literal(tx, i)
            kd = tx.put_dag(root=keynode, bindings={"key": keynode})
            vd = tx.put_dag(root=valnode, bindings={"value": valnode})
            entries = app.tree(tx, current.commit)
            entries.update({"bounded-key%d" % i: kd, "bounded-value%d" % i: vd})
            basis = tx.put_commit(tx.put_tree(entries), parents=(current.commit,))
        key = app.literal_source(path, commit=basis, source_dag=kd, source_name="key", output_name="bounded-ks%d" % i, ref="bounded-ks%d" % i)
        value = app.literal_source(path, commit=key.commit, source_dag=vd, source_name="value", output_name="bounded-vs%d" % i, ref="bounded-vs%d" % i)
        current = app.map_insert(path, commit=value.commit, prior=current.dag, key=key.dag, value=value.dag, output_name="bounded-insert%d" % i, ref="bounded-insert%d" % i)
    return app.put_inputs(path, commit=current.commit, construction=current.dag, output_name="bounded-inputs", ref="bounded-inputs")


def test_successful_return64_new_returned_source65_rejects_BEFORE_publication(state, exchange_runtime, tmp_path):
    path, _, _, _, inputs = state
    full = bounded_construction(path, inputs.commit)
    with d.Repository(path) as repo, repo.write() as tx:
        # Companion trusted constant func: no getter, no acceptance-history jobs.
        source = binding.capture("double").replace(b"argument_map_funcs.double", b"(lambda a, v: recorded_maps.d.Datum.i64(42))")
        entries = app.tree(tx, full.commit)
        entries["constant-binding"] = app.local.put_local_binding(tx, source=source, interpreter=sys.executable, timeout_ms=10000)
        base = tx.put_commit(tx.put_tree(entries), parents=(full.commit,))
    q = reuse.record_request(path, commit=base, intent_uri="urn:example:fixture-constant42", binding_name="constant-binding", inputs_name=full.name, table_name="table", decision_name="constant-d", decision_ref="constant-d", submission_ref="constant-q")
    selected, child = story.execute(path, tmp_path, q, 9)
    inspector = app.Inspector(path, selected.commit)
    output = inspector.returned(selected.result, request=selected.request, inputs=selected.inputs)
    assert output.value == d.Datum.i64(42) and output.accesses == () and len(inspector.seen) == 64
    assert child["exit"] == 0 and child["reaped"]
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="prospective"):
        app.returned_source(path, commit=selected.commit, slot=selected.slot, output_name="returned65", ref="returned65")
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("returned65")
    # Same complete input62 + return/trace2 + one new getter recipe would be65:
    # fixed facade rejects before trusted wrapper opens its publication batch.
    with pytest.raises(ValueError, match="prospective"):
        app.invoke(path, commit=full.commit, inputs=full.dag, func=lambda a, v: v.map_get(a, "k0"))


def test_offline_blockers_real_nonexecuting_controls_before_module_load(exchange_runtime, tmp_path):
    import json
    reader = ROOT / "tests/argument_maps/offline_read.py"
    copied = tmp_path / "measured-reader.py"
    copied.write_bytes(reader.read_bytes())
    controls = subprocess.run([sys.executable, str(copied), "controls", str(tmp_path), str(tmp_path)], capture_output=True, text=True, timeout=15)
    assert controls.returncode == 0, controls.stderr
    assert json.loads(controls.stdout)["blockers"] == ["spawn", "http", "urllib-transport", "connect"]
    (tmp_path / "installed_story.py").write_text("import subprocess,sys\nsubprocess.Popen([sys.executable,'-c','raise SystemExit(99)'])\n")
    refused = subprocess.run([sys.executable, str(copied), "read", str(tmp_path), str(tmp_path)], capture_output=True, text=True, timeout=15)
    assert refused.returncode != 0 and "offline reader cannot spawn" in refused.stderr
