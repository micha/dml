"""Native-backed checks for fixed built-ins and their recording boundary."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from daggerml import builtin, core


EMPTY = b"dml://source/builtin/map/empty/v1"
INSERT = b"dml://source/builtin/map/insert/v1"
GET1 = b"dml://source/builtin/map/get/v1"
GET2 = b"dml://source/builtin/map/get/v2"
INDEX = b"dml://source/builtin/list/get/v1"
UNKNOWN = b"dml://source/builtin/map/get/v99"
I64, STRING, LIST, MAP = core.DATUM_I64, core.DATUM_STRING, core.DATUM_LIST, core.DATUM_MAP


def stored(tx, kind, *fields):
    return core.txn_put_object(tx, kind, core.object_encode(kind, *fields))


def datum(tx, kind, value):
    return core.txn_put_datum(tx, core.datum_encode(kind, value))


def literal(tx, kind, value):
    return stored(tx, core.REC_NODE, core.NODE_LITERAL, datum(tx, kind, value))


def link(tx, dag):
    return stored(tx, core.REC_NODE, core.NODE_SUBDAG, dag)


def profile(tx, role, root, **fields):
    fields["role"] = literal(tx, STRING, role)
    names = (part for name, node in fields.items() for part in (name.encode("ascii"), node))
    return stored(tx, core.REC_DAG, fields[root], *names)


class BuiltinsTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = core.repo_open(Path(directory.name) / "repo", True)
        self.addCleanup(core.repo_close, self.repo)
        with self.transaction(core.TXN_WRITE) as tx:
            self.bindings = {name: builtin.put_binding(tx, name) for name in (EMPTY, INSERT, GET1, GET2, INDEX)}

    @contextmanager
    def transaction(self, mode):
        tx = core.txn_begin(self.repo, mode)
        try:
            yield tx
            if mode == core.TXN_WRITE:
                core.txn_commit(tx)
        finally:
            core.txn_abort(tx)

    def call(self, rec, func, source, entries=()):
        return rec.call(func, self.bindings[source], rec.arguments(entries))

    def operations(self, rec):
        return rec.operations(map_binding=self.bindings[GET1], list_binding=self.bindings[INDEX])

    def assert_absent(self, kind, get, identifier):
        with self.transaction(core.TXN_READ) as tx, self.assertRaises(core.Error) as missing:
            get(tx, *(() if kind is None else (kind,)), identifier)
        self.assertEqual(missing.exception.args[0], "not_found")

    def test_five_exact_handlers_carry_nodes_and_original_input(self):
        with self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            list_id = datum(tx, I64, 42)
            list_node = literal(tx, LIST, [list_id])
            # Distinct source DAGs deliberately contain the exact same native literal node.
            left = stored(tx, core.REC_DAG, list_node, b"item", list_node, b"left", list_node)
            right = stored(tx, core.REC_DAG, list_node, b"item", list_node, b"right", list_node)
            source_a, source_b = (rec.source(dag, b"item") for dag in (left, right))
            source_ids = rec.dag(source_a), rec.dag(source_b)
            self.assertNotEqual(*source_ids)
            self.assertEqual(source_a.value, source_b.value)
            empty = self.call(rec, builtin.MAP_EMPTY, EMPTY)
            key = rec.literal(STRING, b"items")
            maps = [self.call(rec, builtin.MAP_INSERT, INSERT, {b"map": empty, b"key": key, b"value": source})
                    for source in (source_a, source_b)]
            map_ids = tuple(map(rec.dag, maps))
            self.assertEqual(maps[0].value, maps[1].value)
            self.assertEqual(empty.value, builtin.Datum(MAP, core.datum_decode(core.datum_encode(MAP, ()))[0]))
            args = rec.arguments({b"map": maps[1], b"key": key})
            args_id = rec.dag(args)
            with patch.object(builtin, "_map_get_v1", wraps=builtin._map_get_v1) as v1, \
                 patch.object(builtin, "_map_get_v2", wraps=builtin._map_get_v2) as v2:
                got1 = rec.call(builtin.MAP_GET, self.bindings[GET1], args)
                v1.assert_called_once()
                v2.assert_not_called()
                got2 = rec.call(builtin.MAP_GET, self.bindings[GET2], args)
                v1.assert_called_once()
                v2.assert_called_once()
            answer = self.operations(rec).list_get(got2, 0)
            self.assertEqual(answer.value.as_i64(), 42)
            self.assertEqual(got1.value, got2.value)
            result = rec.dag(rec.returned(answer, inputs=args))
            with self.assertRaises(AttributeError):
                got1.value = got2.value
            self.assertFalse(hasattr(got2, "dag"))
        self.assertEqual(answer.value.as_i64(), 42)
        with self.assertRaisesRegex(builtin.BuiltinError, "inactive"):
            rec.dag(answer)
        with self.transaction(core.TXN_READ) as tx:
            read = builtin.Inspector(tx)
            with patch.object(builtin.Recorder, "call", side_effect=AssertionError("offline dispatch")), \
                 patch.object(core, "txn_put_object", side_effect=AssertionError("offline authoring")), \
                 patch.object(core, "txn_put_datum", side_effect=AssertionError("offline authoring")):
                final = read.returned(result)
            self.assertEqual(final.value.as_i64(), 42)
            self.assertEqual(final.inputs.dag, args_id)
            empty_op, insert_a, insert_b, get1, get2, index = final.trace
            self.assertEqual([op.binding.source_uri for op in final.trace], [EMPTY, INSERT, INSERT, GET1, GET2, INDEX])
            self.assertNotEqual(get1.dag, get2.dag)
            self.assertEqual((get1.arguments.dag, get2.arguments.dag), (args_id, args_id))
            self.assertEqual(dict(get2.arguments.entries)[b"map"].dag, map_ids[1])
            self.assertEqual(dict(index.arguments.entries)[b"list"].dag, get2.dag)
            self.assertEqual(final.returned.dag, index.dag)
            self.assertEqual(dict(insert_a.arguments.entries)[b"value"].dag, source_ids[0])
            self.assertEqual(dict(insert_b.arguments.entries)[b"value"].dag, source_ids[1])
            self.assertEqual(read.node(source_ids[1]).source_dag, right)
            self.assertEqual(empty_op.arguments.entries, ())

    def test_unknown_source_is_inspectable_but_cannot_execute(self):
        with self.transaction(core.TXN_WRITE) as tx:
            unknown = builtin.put_binding(tx, UNKNOWN)
        with self.transaction(core.TXN_READ) as tx:
            self.assertEqual(builtin.inspect_binding(tx, unknown).source_uri, UNKNOWN)
        for binding in (unknown, self.bindings[INDEX]):
            with self.subTest(binding=binding), self.assertRaisesRegex(builtin.BuiltinError, "pairing"), \
                 self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
                rec.call(builtin.MAP_GET, binding, rec.arguments())

    def test_rejects_malformed_binding_fields_and_root(self):
        with self.transaction(core.TXN_WRITE) as tx:
            absent = literal(tx, core.DATUM_NULL, None)
            uri = literal(tx, core.DATUM_URI, GET1)
            text = literal(tx, STRING, GET1)
            valid = {"adapter": absent, "source": uri, "interpreter": absent, "timeout-ms": absent}
            bad = [profile(tx, builtin.BINDING_ROLE, "source", **valid)]
            replacements = {"adapter": uri, "interpreter": text, "timeout-ms": text, "source": text}
            for field, replacement in replacements.items():
                bad.append(profile(tx, builtin.BINDING_ROLE, "role", **(valid | {field: replacement})))
            bad.append(profile(tx, b"other", "role", **valid))
            bad.append(profile(tx, builtin.BINDING_ROLE, "role", **(valid | {"extra": text})))
        with self.transaction(core.TXN_READ) as tx:
            for dag in bad:
                with self.subTest(dag=dag), self.assertRaises(builtin.BuiltinError):
                    builtin.inspect_binding(tx, dag)

    def test_nonmatching_argument_shape_and_bad_map_or_index_fail(self):
        def too_many_names(rec):
            return self.call(rec, builtin.MAP_EMPTY, EMPTY, {b"extra": rec.literal(I64, 0)})

        def missing_key(rec):
            return self.operations(rec).map_get(rec.literal(MAP, ()), b"absent")

        def missing_v2_key(rec):
            return self.call(rec, builtin.MAP_GET, GET2,
                             {b"map": rec.literal(MAP, ()), b"key": rec.literal(STRING, b"absent")})

        def non_map(rec):
            return self.operations(rec).map_get(rec.literal(I64, 0), b"absent")

        def non_string_key(rec):
            return self.call(rec, builtin.MAP_GET, GET2, {b"map": rec.literal(MAP, ()), b"key": rec.literal(I64, 0)})

        cases = ((too_many_names, "names"), (missing_key, "missing MAP"), (missing_v2_key, "missing MAP"),
                 (non_map, "MAP container"), (non_string_key, "STRING"))
        for operation, message in cases:
            with self.subTest(operation=operation), self.assertRaisesRegex(builtin.BuiltinError, message), \
                 self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
                operation(rec)
        for index in (-1, 1, True, 0.0):
            with self.subTest(index=index), self.assertRaises(builtin.BuiltinError), \
                 self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
                self.operations(rec).list_get(rec.literal(LIST, [datum(tx, I64, 5)]), index)

    def test_insert_and_arguments_reject_nfc_duplicate_keys(self):
        decomposed, composed = "cafe\u0301".encode(), "café".encode()
        with self.assertRaisesRegex(builtin.BuiltinError, "duplicate canonical argument key"), \
             self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            source = rec.literal(I64, 0)
            rec.arguments([(decomposed, source), (composed, source)])
        with self.assertRaisesRegex(builtin.BuiltinError, "duplicate canonical key"), \
             self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            value = rec.literal(I64, 9)
            base = rec.literal(MAP, [(datum(tx, STRING, composed), datum(tx, I64, 3))])
            self.call(rec, builtin.MAP_INSERT, INSERT, {b"map": base, b"key": rec.literal(STRING, decomposed),
                                                        b"value": value})

    def test_caught_conversion_aborts_previously_staged_native_rows_and_ref(self):
        with self.assertRaisesRegex(builtin.BuiltinError, "caught error poisoned"), \
             self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            empty = self.call(rec, builtin.MAP_EMPTY, EMPTY)
            operation = rec.dag(empty)
            args = builtin.Inspector(tx).operation(operation).arguments.dag
            tree = stored(tx, core.REC_TREE, b"primitive", operation)
            publication = stored(tx, core.REC_COMMIT, tree)
            core.txn_ref_create(tx, b"partial", publication)
            with self.assertRaises(TypeError):
                self.operations(rec).map_get(empty, None)
            with self.assertRaisesRegex(builtin.BuiltinError, "poisoned"):
                rec.trace()
        self.assert_absent(core.REC_DAG, core.txn_get_object, operation)
        self.assert_absent(core.REC_DAG, core.txn_get_object, args)
        self.assert_absent(core.REC_COMMIT, core.txn_get_object, publication)
        self.assert_absent(None, core.txn_ref_get, b"partial")

    def test_outer_publication_failure_rolls_back_new_argument_trace_and_return(self):
        with self.assertRaisesRegex(RuntimeError, "deliberate late failure"), self.transaction(core.TXN_WRITE) as tx, \
             builtin.Recorder(tx) as rec:
            value = rec.literal(LIST, [datum(tx, I64, 743)])
            args = rec.arguments({b"items": value})
            ops = self.operations(rec)
            found = ops.list_get(ops.map_get(args, b"items"), 0)
            operation, result = rec.dag(found), rec.dag(rec.returned(found, inputs=args))
            wrap = builtin.Inspector(tx).returned(result)
            map_get, list_get = wrap.trace
            native_trace = core.txn_lookup_node(tx, result, b"trace")
            _, trace_dag, _ = core.object_decode(core.txn_get_object(tx, core.REC_NODE, native_trace))
            raise RuntimeError("deliberate late failure")
        for dag in (map_get.arguments.dag, list_get.arguments.dag, wrap.inputs.dag, map_get.dag,
                    operation, trace_dag, result):
            self.assert_absent(core.REC_DAG, core.txn_get_object, dag)

    def test_foreign_handles_and_fabricated_equal_values_are_not_sources(self):
        with self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            old = rec.literal(I64, 17)
            old_id = rec.dag(old)
        for fake in (old, builtin.ValueNode(old.value)):
            with self.subTest(fake=fake), self.assertRaisesRegex(builtin.BuiltinError, "foreign or fabricated"), \
                 self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
                rec.arguments({b"value": fake})
        with self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            loaded = rec.load(old_id)
            self.assertIsNot(loaded, old)
            self.assertEqual(loaded.value, old.value)
            self.assertEqual(rec.dag(loaded), old_id)

    def test_recorder_requires_active_scope_and_reentry_aborts(self):
        with self.assertRaisesRegex(builtin.BuiltinError, "caught error poisoned"), \
             self.transaction(core.TXN_WRITE) as tx:
            rec = builtin.Recorder(tx)
            with self.assertRaisesRegex(builtin.BuiltinError, "inactive"):
                rec.literal(I64, 29)
            with rec:
                staged = rec.dag(rec.literal(I64, 29))
                with self.assertRaisesRegex(builtin.BuiltinError, "reentered"), rec:
                    self.fail("same recorder reentered")
        self.assert_absent(core.REC_DAG, core.txn_get_object, staged)
        with self.assertRaisesRegex(builtin.BuiltinError, "reentered"), rec:
            self.fail("ended recorder reused")

    def test_logical_literal_cannot_inject_native_collection_members(self):
        with self.transaction(core.TXN_WRITE) as tx:
            known = datum(tx, I64, 321)
        with self.assertRaisesRegex(builtin.BuiltinError, "caught error poisoned"), \
             self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            ops = self.operations(rec)
            value = ops.literal(I64, 42)
            partial = rec.dag(value)
            with self.assertRaisesRegex(builtin.BuiltinError, "not native IDs"):
                ops.literal(LIST, [known])
        self.assert_absent(core.REC_DAG, core.txn_get_object, partial)

    def test_native_canonical_nan_value_round_trips_through_node_operations(self):
        # Format-v1 packed canonical F64 NaN, not a Python float round trip.
        packed = bytes.fromhex("444d4c310100020030000000000000000000000004000000"
                               "08000000000000002800000000000000000000000000f87f")
        with self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            item = core.txn_put_datum(tx, packed)
            source = rec.literal(LIST, [item])
            arg = rec.arguments({b"items": source})
            ops = self.operations(rec)
            returned = ops.list_get(ops.map_get(arg, b"items"), 0)
            result = rec.dag(rec.returned(returned, inputs=arg))
        with self.transaction(core.TXN_READ) as tx:
            read = builtin.Inspector(tx).returned(result)
            self.assertEqual(read.datum, item)
            self.assertEqual(read.value, returned.value)

    def test_limits_distinguish_distinct_native_records_from_call_positions(self):
        with self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            args = rec.arguments()
            for _ in range(16):
                result = rec.call(builtin.MAP_EMPTY, self.bindings[EMPTY], args)
            trace_dag = rec.trace()
            dag = rec.dag(result)
        with self.transaction(core.TXN_READ) as tx:
            trace = builtin.Inspector(tx).trace(trace_dag)
            self.assertEqual(tuple(op.dag for op in trace), (dag,) * 16)
        with self.assertRaisesRegex(builtin.BuiltinError, "position limit"), self.transaction(core.TXN_WRITE) as tx, \
             builtin.Recorder(tx) as rec:
            args = rec.arguments()
            for _ in range(17):
                rec.call(builtin.MAP_EMPTY, self.bindings[EMPTY], args)
        with self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            node = rec.literal(I64, 0)
            args = rec.arguments({str(i).encode(): node for i in range(16)})
            self.assertEqual(len(builtin.Inspector(tx).arguments(rec.dag(args)).entries), 16)
        with self.assertRaisesRegex(builtin.BuiltinError, "argument limit"), self.transaction(core.TXN_WRITE) as tx, \
             builtin.Recorder(tx) as rec:
            node = rec.literal(I64, 0)
            rec.arguments({str(i).encode(): node for i in range(17)})
        with self.assertRaisesRegex(builtin.BuiltinError, "profile limit"), self.transaction(core.TXN_WRITE) as tx, \
             builtin.Recorder(tx) as rec:
            for i in range(64):
                last = rec.literal(I64, i + 1000)
            last_dag = rec.dag(last)
            self.assertEqual(rec.dag(rec.literal(I64, 1063)), last_dag)
            rec.literal(I64, 1064)
        self.assert_absent(core.REC_DAG, core.txn_get_object, last_dag)

    def test_inspector_rejects_persisted_false_value_and_wrong_source(self):
        with self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            named = literal(tx, I64, 44)
            different = literal(tx, I64, 45)
            source = stored(tx, core.REC_DAG, named, b"item", named)
            source_lie = profile(tx, builtin.SOURCE_ROLE, "value", name=literal(tx, STRING, b"item"),
                                 value=different, source=link(tx, source))
            key = literal(tx, STRING, b"item")
            arguments_lie = profile(tx, builtin.ARGUMENTS_ROLE, "value", value=literal(tx, MAP, ()),
                                    **{"key-00": key, "source-00": link(tx, rec.dag(rec.literal(I64, 45)))})
            args = rec.dag(rec.arguments())
            operation_lie = profile(tx, builtin.OPERATION_ROLE, "value", value=different,
                                    func=literal(tx, core.DATUM_URI, builtin.MAP_EMPTY),
                                    binding=link(tx, self.bindings[EMPTY]), arguments=link(tx, args))
            claimed = rec.dag(rec.literal(I64, 44))
            return_lie = profile(tx, builtin.RETURN_ROLE, "value", value=different, returned=link(tx, claimed),
                                 inputs=link(tx, args), trace=link(tx, rec.trace()))
        with self.transaction(core.TXN_READ) as tx:
            inspector = builtin.Inspector(tx)
            cases = ((source_lie, "source node differs"), (arguments_lie, "differs from actual source"),
                     (operation_lie, "fixed semantics"), (return_lie, "differs from returned node"))
            for invalid, message in cases:
                with self.subTest(invalid=invalid), self.assertRaisesRegex(builtin.BuiltinError, message):
                    inspector.node(invalid)


if __name__ == "__main__":
    unittest.main()
