"""Check typed capture boundaries and transactional failures in recorded closures."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from daggerml import builtin, core

from trace_support import scan_inventory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import recorded_closures as example


INVOCATION = b"90000000-0000-4000-8000-000000000001"
ATTEMPT = b"90000000-0000-4000-8000-000000000002"
SECOND_INVOCATION = b"90000000-0000-4000-8000-000000000003"
MAX_I64 = (1 << 63) - 1


class ClosureTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "repo"
        self.defaults = example.defaults(self.path, b"defaults", 1, 2, b"origin-a")
        self.closure = example.capture(self.path, b"defaults", self.defaults, b"closure")

    def inventory(self):
        return scan_inventory(SCANNER, self.path)

    def request(self, a=13, b=29, *, pending=b"pending", decision=b"decision"):
        commit = example.request(self.path, b"closure", self.closure, pending, decision, a, b, INVOCATION)
        return bytes.fromhex(example.inspect(self.path, decision, expected=commit)["requested"]["request"])

    def test_scale_and_invocation_values_are_exact_i64(self):
        before = self.inventory()
        for value in (True, 2.0, MAX_I64 + 1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "captured scale is not a signed 64-bit integer"):
                    example.defaults(self.path, b"new-defaults", 1, value, b"invalid")
                with self.assertRaisesRegex(ValueError, "a is not a signed 64-bit integer"):
                    self.request(a=value)
        self.assertEqual(self.inventory(), before)

    def test_recorded_scale_cannot_appear_as_an_invocation_override(self):
        ex = example
        with ex.records._write_transaction(self.path, create=False) as txn:
            with builtin.Recorder(txn) as rec:
                values = {name: rec.literal(core.DATUM_I64, value)
                          for name, value in ((b"a", 13), (b"b", 29), (b"scale", 3))}
                inputs = rec.dag(rec.arguments(values))
            request = ex._put_request(txn, self.closure, inputs, INVOCATION)
            core.txn_ref_create(txn, b"pending", request)
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "requires exactly the I64 arguments a and b"):
            ex.work(self.path, b"pending", request, b"done", ATTEMPT)
        self.assertEqual(self.inventory(), before)

    def test_inspection_does_not_bind_or_run_the_logical_callable(self):
        request = self.request()
        producer = example.work(self.path, b"pending", request, b"done", ATTEMPT)
        before = self.inventory()
        with patch.object(example, "_bind_scaled_sum", side_effect=AssertionError("inspection tried to bind work")):
            self.assertEqual(example.inspect(self.path, b"done", expected=producer)["value"], 84)
        self.assertEqual(self.inventory(), before)

    def test_equivalent_getter_version_in_original_trace_is_poison_even_on_scale_miss(self):
        ex = example
        producing_q = self.request()
        promoted = ex.defaults(self.path, b"defaults", 2, 3, b"origin-c", expected=self.defaults)
        alternate = ex.capture(self.path, b"defaults", promoted, b"alternate")
        with ex.records._write_transaction(self.path, create=False) as txn:
            inspector = builtin.Inspector(txn)
            own = ex._read_request(txn, inspector, producing_q)
            newer = ex._read_defaults(txn, inspector, promoted)
            with builtin.Recorder(txn) as rec:
                args = rec.load(own.args.dag)
                ops = rec.operations(map_binding=newer.map_binding.dag, list_binding=newer.list_binding.dag)
                a = ops.map_get(args, b"a").value.as_i64()
                b = ops.map_get(args, b"b").value.as_i64()
                out = rec.literal(core.DATUM_I64, (a + b) * 2)
                returned = rec.dag(rec.returned(out, inputs=args))
            self.assertEqual(inspector.returned(returned).value.as_i64(), 84)
            result = ex.records._put_snapshot(txn, ex.RESULT, returned, producing_q)
            identity = ex.records._put_literal(txn, core.DATUM_STRING, ATTEMPT)
            selected = ex.records._publish(txn, b"poison", ex.ATTEMPT, ex.layout._put_dag(txn, identity, {}),
                                           producing_q, result)
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "getter trace does not match the captured binding"):
            ex.request(self.path, b"alternate", alternate, b"unused", b"decision-miss", 13, 29, SECOND_INVOCATION,
                       mode=ex.TRY, selected_ref=b"poison", selected=selected)
        self.assertEqual(self.inventory(), before)


if __name__ == "__main__":
    SCANNER = Path(sys.argv.pop(1)).resolve()
    unittest.main()
