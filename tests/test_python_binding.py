"""Exercise Python-specific argument, error and lifetime behavior."""

from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from daggerml import core


class BindingTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "repo"

    def test_core_error_identifies_status_native_code_and_detail(self):
        with self.assertRaises(core.Error) as raised:
            core.repo_open(self.path, False)
        status, code, detail = raised.exception.args
        self.assertEqual(status, "not_found")
        self.assertIsInstance(code, int)
        self.assertIn("path does not exist", detail)
        self.assertFalse(self.path.exists())

    def test_repository_argument_errors_do_not_create_a_repository(self):
        cases = ((TypeError, (self.path, 1)), (ValueError, (b"bad\x00path", True)),
                 (OverflowError, (self.path, True, -1)), (TypeError, (self.path, True, 1.5)))
        for error, args in cases:
            with self.subTest(args=args), self.assertRaises(error):
                core.repo_open(*args)
        with self.assertRaises(core.Error) as raised:
            core.repo_open(self.path, True, 1024)
        self.assertEqual(raised.exception.args[0], "invalid_argument")
        self.assertFalse(self.path.exists())
        core.repo_close(core.repo_open(self.path, True, 1024 * 1024))

    def test_commit_failure_consumes_transaction_and_close_rejects_live_one(self):
        repo = core.repo_open(self.path, True)
        txn = core.txn_begin(repo, core.TXN_READ)
        with self.assertRaisesRegex(RuntimeError, "end the active transaction"):
            core.txn_begin(repo, core.TXN_WRITE)
        with self.assertRaises(core.Error) as close_error:
            core.repo_close(repo)
        self.assertEqual(close_error.exception.args[0], "invalid_state")
        with self.assertRaises(core.Error) as commit_error:
            core.txn_commit(txn)
        self.assertEqual(commit_error.exception.args[0], "invalid_state")
        with self.assertRaises(core.Error) as closed_error:
            core.txn_commit(txn)
        self.assertEqual(closed_error.exception.args[0], "invalid_argument")
        core.txn_abort(txn)  # idempotent on a consumed handle
        core.txn_abort(core.txn_begin(repo, core.TXN_WRITE))
        core.repo_close(repo)
        with self.assertRaises(core.Error):
            core.txn_begin(repo, core.TXN_READ)
        with self.assertRaises(core.Error):
            core.repo_close(repo)

    def test_bad_python_arguments_do_not_poison_a_native_write(self):
        repo = core.repo_open(self.path, True)
        txn = core.txn_begin(repo, core.TXN_WRITE)
        data = core.datum_encode(core.DATUM_STRING, b"kept")
        datum = core.txn_put_datum(txn, data)
        with self.assertRaises(TypeError):
            core.txn_put_datum(txn, bytearray(data))
        with self.assertRaises(TypeError):
            core.txn_ref_create(repo, b"main", datum)
        with self.assertRaisesRegex(ValueError, "16 bytes"):
            core.txn_ref_create(txn, b"main", datum[:-1])
        core.txn_commit(txn)
        reader = core.txn_begin(repo, core.TXN_READ)
        output = core.txn_get_datum(reader, datum)
        core.txn_abort(reader)
        core.repo_close(repo)
        self.assertEqual(output, data)
        self.assertEqual(core.datum_decode(output), (b"kept", core.DATUM_STRING))

    def test_map_encoding_is_canonical_and_rejects_duplicate_keys(self):
        low, high = bytes(16), b"\xff" * 16
        self.assertEqual(core.datum_decode(core.datum_encode(core.DATUM_MAP, ())),
                         (bytes(4), core.DATUM_MAP))
        packed = core.datum_encode(core.DATUM_MAP, [(high, low), (low, high)])
        self.assertEqual(core.datum_decode(packed), (b"\x02\x00\x00\x00" + low + high + high + low, core.DATUM_MAP))
        self.assertEqual(packed, core.datum_encode(core.DATUM_MAP, ((low, high), (high, low))))
        with self.assertRaises(core.Error) as duplicate:
            core.datum_encode(core.DATUM_MAP, [(low, high), (low, low)])
        self.assertEqual(duplicate.exception.args[0], "invalid_payload")
        self.assertIn("map_keys_not_strictly_sorted", duplicate.exception.args[2])

    def test_map_encoding_rejects_invalid_entry_shapes_and_ids(self):
        identifier = bytes(16)
        cases = (
            (TypeError, iter(())),
            (TypeError, {identifier: identifier}),
            (TypeError, ([identifier, identifier],)),
            (TypeError, ((identifier,),)),
            (TypeError, ((identifier, identifier, identifier),)),
            (TypeError, ((bytearray(identifier), identifier),)),
            (ValueError, ((identifier[:-1], identifier),)),
            (ValueError, ((identifier, identifier), (identifier, identifier + b"!"))),
        )
        for error, entries in cases:
            with self.subTest(entries=entries), self.assertRaises(error):
                core.datum_encode(core.DATUM_MAP, entries)

    def test_null_and_uri_use_native_canonical_encoding(self):
        self.assertEqual(core.datum_decode(core.datum_encode(core.DATUM_NULL, None)), (b"", core.DATUM_NULL))
        with self.assertRaises(TypeError):
            core.datum_encode(core.DATUM_NULL, b"")
        with self.assertRaises(TypeError):
            core.datum_encode(core.DATUM_URI, "dml://source/builtin/map/get/v1")
        canonical = b"dml://source/builtin/map/get/v1"
        encoded = core.datum_encode(core.DATUM_URI, canonical)
        self.assertEqual(core.datum_decode(encoded), (canonical, core.DATUM_URI))
        for invalid in (b"relative", b"dml:\x00", b"dml:x\xff", b"dml:%zz", b"DML://SOURCE/builtin/map/get/%761"):
            with self.subTest(uri=invalid), self.assertRaises(core.Error) as rejected:
                core.datum_encode(core.DATUM_URI, invalid)
            self.assertEqual(rejected.exception.args[0], "invalid_payload")

    def test_datum_members_preserve_list_order_and_native_map_keys(self):
        low, high = bytes(16), b"\xff" * 16
        for members in ([high, low, high], (high, low, high)):
            packed = core.datum_encode(core.DATUM_LIST, members)
            self.assertEqual(core.datum_members(packed), (high, low, high))
        for kind in (core.DATUM_LIST, core.DATUM_MAP):
            self.assertEqual(core.datum_members(core.datum_encode(kind, ())), ())
        packed = core.datum_encode(core.DATUM_MAP, ((high, low), (low, high)))
        self.assertEqual(core.datum_members(packed), ((low, high), (high, low)))
        with self.assertRaises(core.Error):
            core.datum_members(packed[:-1])
        with self.assertRaises(TypeError):
            core.datum_members(bytearray(packed))
        with self.assertRaisesRegex(ValueError, "require a LIST or MAP"):
            core.datum_members(core.datum_encode(core.DATUM_NULL, None))

    def test_list_encoding_rejects_non_sequences_and_bad_ids(self):
        for items in (iter(()), {bytes(16)}, bytes(16), (bytearray(16),)):
            with self.subTest(items=items), self.assertRaises(TypeError):
                core.datum_encode(core.DATUM_LIST, items)
        with self.assertRaisesRegex(ValueError, "16 bytes"):
            core.datum_encode(core.DATUM_LIST, (bytes(16), bytes(17)))

    def test_map_write_rejects_a_node_id_and_rolls_back(self):
        repo = core.repo_open(self.path, True)
        self.addCleanup(core.repo_close, repo)
        txn = core.txn_begin(repo, core.TXN_WRITE)
        self.addCleanup(core.txn_abort, txn)
        key = core.txn_put_datum(txn, core.datum_encode(core.DATUM_STRING, b"key"))
        node = core.txn_put_object(txn, core.REC_NODE, core.object_encode(core.REC_NODE, key))
        packed = core.datum_encode(core.DATUM_MAP, ((key, node),))
        with self.assertRaises(core.Error) as invalid:
            core.txn_put_datum(txn, packed)
        self.assertEqual(invalid.exception.args[0], "invalid_kind")
        self.assertIn("composite_ref_not_datum", invalid.exception.args[2])
        with self.assertRaises(core.Error) as poisoned:
            core.txn_commit(txn)
        self.assertEqual(poisoned.exception.args[0], "invalid_state")
        self.assert_absent(repo, key)

    def test_staged_bundle_retains_nested_map_and_normalized_key(self):
        source = core.repo_open(self.path, True)
        self.addCleanup(core.repo_close, source)
        writer = core.txn_begin(source, core.TXN_WRITE)
        self.addCleanup(core.txn_abort, writer)

        def put_object(kind, *operands):
            return core.txn_put_object(writer, kind, core.object_encode(kind, *operands))

        key = core.txn_put_datum(writer, core.datum_encode(core.DATUM_STRING, "café".encode()))
        equivalent = core.txn_put_datum(writer, core.datum_encode(core.DATUM_STRING, "cafe\u0301".encode()))
        self.assertEqual(equivalent, key)
        value = core.txn_put_datum(writer, core.datum_encode(core.DATUM_I64, 42))
        with self.assertRaises(core.Error) as duplicate:
            core.datum_encode(core.DATUM_MAP, ((key, value), (equivalent, value)))
        self.assertEqual(duplicate.exception.args[0], "invalid_payload")
        uri = core.txn_put_datum(writer, core.datum_encode(core.DATUM_URI, b"dml://source/future/v99"))
        null = core.txn_put_datum(writer, core.datum_encode(core.DATUM_NULL, None))
        listing = core.txn_put_datum(writer, core.datum_encode(core.DATUM_LIST, (value, null, uri)))
        inner_record = core.datum_encode(core.DATUM_MAP, ((key, listing),))
        inner = core.txn_put_datum(writer, inner_record)
        outer_record = core.datum_encode(core.DATUM_MAP, ((key, inner),))
        outer = core.txn_put_datum(writer, outer_record)
        literal = put_object(core.REC_NODE, core.NODE_LITERAL, outer)
        dag = put_object(core.REC_DAG, literal, b"arguments", literal)
        tree = put_object(core.REC_TREE, b"snapshot", dag)
        commit = put_object(core.REC_COMMIT, tree)
        core.txn_ref_create(writer, b"main", commit)
        core.txn_commit(writer)

        bundle = core.repo_export_commit(source, commit)
        replica = core.repo_open(self.path.with_name("replica"), True)
        self.addCleanup(core.repo_close, replica)
        self.assertEqual(core.repo_import_commit_staged(replica, bundle, b"staged"), commit)
        reader = core.txn_begin(replica, core.TXN_READ)
        self.addCleanup(core.txn_abort, reader)
        self.assertEqual(core.txn_ref_get(reader, b"staged"), commit)
        self.assertEqual(core.txn_lookup_node(reader, dag, b"arguments"), literal)
        self.assertEqual(core.txn_get_datum(reader, outer), outer_record)
        self.assertEqual(core.txn_get_datum(reader, inner), inner_record)
        self.assertEqual(core.datum_members(core.txn_get_datum(reader, listing)), (value, null, uri))
        self.assertEqual(core.datum_decode(core.txn_get_datum(reader, uri)), (b"dml://source/future/v99", core.DATUM_URI))
        self.assertEqual(core.datum_decode(core.txn_get_datum(reader, null)), (b"", core.DATUM_NULL))
        self.assertEqual(core.datum_decode(core.txn_get_datum(reader, key)), ("café".encode(), core.DATUM_STRING))
        self.assertEqual(core.datum_decode(core.txn_get_datum(reader, value)), (b"*" + bytes(7), core.DATUM_I64))

    def test_bundle_binding_owns_results_and_maps_native_errors(self):
        repo = core.repo_open(self.path, True)
        self.addCleanup(core.repo_close, repo)
        txn = core.txn_begin(repo, core.TXN_WRITE)
        tree = core.txn_put_object(txn, core.REC_TREE, core.object_encode(core.REC_TREE))
        root = core.txn_put_object(txn, core.REC_COMMIT, core.object_encode(core.REC_COMMIT, tree))
        core.txn_commit(txn)

        with self.assertRaisesRegex(ValueError, "16 bytes"):
            core.repo_export_commit(repo, root.hex().encode("ascii"))
        with self.assertRaises(TypeError):
            core.repo_import_commit_staged(repo, bytearray(), b"incoming")
        bundle = core.repo_export_commit(repo, root)
        self.assertIs(type(bundle), bytes)
        reader = core.txn_begin(repo, core.TXN_READ)
        for operation, args in (
            (core.repo_export_commit, (repo, root)),
            (core.repo_import_commit_staged, (repo, bundle, b"incoming")),
            (core.txn_collect_garbage, (reader,)),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(core.Error) as rejected:
                    operation(*args)
                self.assertEqual(rejected.exception.args[0], "invalid_state")
                self.assertTrue(rejected.exception.args[2])
        core.txn_abort(reader)
        with self.assertRaises(core.Error) as malformed:
            core.repo_import_commit_staged(repo, b"", b"incoming")
        self.assertEqual(malformed.exception.args[0], "invalid_bounds")
        imported = core.repo_import_commit_staged(repo, bundle, b"incoming")
        self.assertIs(type(imported), bytes)
        self.assertEqual(imported, root)
        with self.assertRaises(core.Error) as occupied:
            core.repo_import_commit_staged(repo, bundle, b"incoming")
        self.assertEqual(occupied.exception.args[0], "invalid_state")

        txn = core.txn_begin(repo, core.TXN_WRITE)
        core.txn_ref_delete_expected(txn, b"incoming", imported)
        self.assertEqual(core.txn_collect_garbage(txn), 2)
        core.txn_abort(txn)
        self.assertEqual(core.repo_export_commit(repo, imported), bundle)

    def test_view_keeps_packed_input_alive_and_checks_kind_and_bounds(self):
        dag = bytes(range(16))
        view, reference, count = core.object_decode(core.object_encode(core.REC_TREE, b"snapshot", dag))
        self.assertEqual((reference, count), (bytes(16), 1))
        self.assertEqual(core.object_view_entry(view, 0), (dag, b"snapshot"))
        with self.assertRaises(ValueError):
            core.object_view_entry(view, -1)
        with self.assertRaises(core.Error):
            core.object_view_entry(view, 1)
        with self.assertRaises(core.Error):
            core.object_view_parent(view, 0)
        with self.assertRaises(TypeError):
            core.object_view_entry(b"not a view", 0)

    def test_view_does_not_retain_a_bytes_subclass(self):
        discarded = []

        class TrackedBytes(bytes):
            def __del__(self):
                discarded.append(True)

        dag = bytes(range(16))
        record = TrackedBytes(core.object_encode(core.REC_TREE, b"snapshot", dag))
        view, _, _ = core.object_decode(record)
        record.view = view
        del record
        self.assertEqual(discarded, [True])
        self.assertEqual(core.object_view_entry(view, 0), (dag, b"snapshot"))

    def test_transaction_keeps_repository_alive_until_it_ends(self):
        txn = core.txn_begin(core.repo_open(self.path, True), core.TXN_WRITE)
        packed = core.datum_encode(core.DATUM_I64, 35)
        datum = core.txn_put_datum(txn, packed)
        core.txn_commit(txn)
        repo = core.repo_open(self.path, False)
        reader = core.txn_begin(repo, core.TXN_READ)
        self.assertEqual(core.txn_get_datum(reader, datum), packed)
        core.txn_abort(reader)
        core.repo_close(repo)

    def assert_absent(self, repo, datum):
        reader = core.txn_begin(repo, core.TXN_READ)
        try:
            with self.assertRaises(core.Error) as error:
                core.txn_get_datum(reader, datum)
            self.assertEqual(error.exception.args[0], "not_found")
        finally:
            core.txn_abort(reader)

    def test_dropping_transaction_on_owner_thread_rolls_back(self):
        repo = core.repo_open(self.path, True)
        txn = core.txn_begin(repo, core.TXN_WRITE)
        datum = core.txn_put_datum(txn, core.datum_encode(core.DATUM_I64, 35))
        del txn
        self.assert_absent(repo, datum)
        core.repo_close(repo)

    def test_foreign_actions_are_rejected_and_owner_reaps_dropped_transaction(self):
        repo = core.repo_open(self.path, True)
        transactions = [core.txn_begin(repo, core.TXN_WRITE)]
        datum = core.txn_put_datum(transactions[0], core.datum_encode(core.DATUM_I64, 35))
        outcomes = []

        def foreign_thread():
            txn = transactions.pop()
            for operation, handle in ((core.repo_close, repo), (core.txn_abort, txn), (core.txn_commit, txn)):
                try:
                    operation(handle)
                except RuntimeError as error:
                    outcomes.append(str(error))

        thread = Thread(target=foreign_thread)
        thread.start()
        thread.join()
        self.assertEqual(len(outcomes), 3)
        self.assertTrue(all("creating thread" in message for message in outcomes), outcomes)
        self.assert_absent(repo, datum)
        core.repo_close(repo)


if __name__ == "__main__":
    unittest.main()
