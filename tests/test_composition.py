"""Check forged provenance against the native repository."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from daggerml import builtin, core

from trace_support import scan_inventory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import recorded_composition as example


INVOCATION = b"90000000-0000-4000-8000-000000000001"
ATTEMPT = b"90000000-0000-4000-8000-000000000002"


class CompositionTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "repo"
        self.config = example.define(self.path, b"config")

    def inventory(self):
        return scan_inventory(SCANNER, self.path)

    def add(self, a, b):
        return example.request_add(self.path, b"config", self.config, b"add", a, b, INVOCATION)

    def test_same_value_named_getter_key_is_not_the_recorded_literal_path(self):
        request = self.add(13, 29)
        ex = example
        with ex.records._write_transaction(self.path, create=False) as txn:
            inspector = builtin.Inspector(txn)
            owner = ex._read_request(txn, inspector, request)
            key = ex.records._put_literal(txn, core.DATUM_STRING, b"a")
            named = ex.layout._put_dag(txn, key, {b"key": key})
            with builtin.Recorder(txn) as rec:
                inputs = rec.load(owner.args.dag)
                a_args = rec.arguments({b"map": inputs, b"key": rec.source(named, b"key")})
                a = rec.call(builtin.MAP_GET, owner.map_binding.dag, a_args)
                b_args = rec.arguments({b"map": inputs, b"key": rec.literal(core.DATUM_STRING, b"b")})
                b = rec.call(builtin.MAP_GET, owner.map_binding.dag, b_args)
                value = rec.literal(core.DATUM_I64, a.value.as_i64() + b.value.as_i64())
                returned = rec.dag(rec.returned(value, inputs=inputs))
            self.assertEqual(inspector.returned(returned).value.as_i64(), 42)
            result = ex.records._put_snapshot(txn, ex.RESULT, returned, request)
            identity = ex.records._put_literal(txn, core.DATUM_STRING, ATTEMPT)
            forged = ex.records._publish(txn, b"forged", ex.ATTEMPT, ex.layout._put_dag(txn, identity, {}),
                                         request, result)
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "getter trace does not match the exact request inputs and keys"):
            ex.compose(self.path, b"forged", forged, b"from-forged")
        self.assertEqual(self.inventory(), before)

    def double_request(self, a, b):
        add_request = self.add(a, b)
        producer = example.work(self.path, b"add", add_request, b"add-done", ATTEMPT)
        composition = example.compose(self.path, b"add-done", producer, b"from-add")
        decision = example.request_double(self.path, b"from-add", composition, b"double", b"decision", INVOCATION)
        report = example.inspect(self.path, b"decision", expected=decision)
        return composition, bytes.fromhex(report["requested"]["request"])

    def test_reuse_cannot_masquerade_as_a_new_request_with_the_same_id(self):
        composition, request = self.double_request(13, 29)
        producer = example.work(self.path, b"double", request, b"double-done", ATTEMPT)
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "reuse needs a new invocation ID"):
            example.request_double(self.path, b"from-add", composition, b"unused", b"reuse", INVOCATION,
                                   mode=example.REQUIRE, selected_ref=b"double-done", selected=producer)
        self.assertEqual(self.inventory(), before)

        ex = example
        with ex.records._write_transaction(self.path, create=False) as txn:
            literal = ex.records._put_literal
            mode = literal(txn, core.DATUM_STRING, ex.REQUIRE)
            dag = ex.layout._put_dag(txn, mode, {b"outcome": literal(txn, core.DATUM_STRING, ex.REUSE)})
            forged = ex.records._publish(txn, b"forged", ex.DECISION, dag, request, producer)
        with self.assertRaisesRegex(ValueError, "reuse needs a new invocation ID"):
            ex.inspect(self.path, b"forged", expected=forged)


if __name__ == "__main__":
    SCANNER = Path(sys.argv.pop(1)).resolve()
    unittest.main()
