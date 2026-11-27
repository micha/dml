"""Live handle and recorder scope checks awaiting the scope replay port."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from daggerml import builtin, core


GET1 = b"dml://source/builtin/map/get/v1"
INDEX = b"dml://source/builtin/list/get/v1"
I64 = core.DATUM_I64


class BuiltinsTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = core.repo_open(Path(directory.name) / "repo", True)
        self.addCleanup(core.repo_close, self.repo)
        with self.transaction(core.TXN_WRITE) as tx:
            self.bindings = {name: builtin.put_binding(tx, name) for name in (GET1, INDEX)}

    @contextmanager
    def transaction(self, mode):
        tx = core.txn_begin(self.repo, mode)
        try:
            yield tx
            if mode == core.TXN_WRITE:
                core.txn_commit(tx)
        finally:
            core.txn_abort(tx)

    def operations(self, rec):
        return rec.operations(map_binding=self.bindings[GET1], list_binding=self.bindings[INDEX])

    def assert_absent(self, kind, get, identifier):
        with self.transaction(core.TXN_READ) as tx, self.assertRaises(core.Error) as missing:
            get(tx, *(() if kind is None else (kind,)), identifier)
        self.assertEqual(missing.exception.args[0], "not_found")

    def test_builtin_handles_are_opaque_and_value_outlives_scope(self):
        with self.transaction(core.TXN_WRITE) as tx, builtin.Recorder(tx) as rec:
            item = core.txn_put_datum(tx, core.datum_encode(I64, 42))
            source = rec.literal(core.DATUM_LIST, [item])
            answer = self.operations(rec).list_get(source, 0)
            with self.assertRaises(AttributeError):
                answer.value = source.value
            self.assertFalse(hasattr(answer, "dag"))
        self.assertEqual(answer.value.as_i64(), 42)
        with self.assertRaisesRegex(builtin.BuiltinError, "inactive"):
            rec.dag(answer)

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


if __name__ == "__main__":
    unittest.main()
