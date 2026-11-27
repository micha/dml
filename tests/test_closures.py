"""Check typed capture boundaries and transactional failures in recorded closures."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from trace_support import scan_inventory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import recorded_closures as example


INVOCATION = b"90000000-0000-4000-8000-000000000001"
ATTEMPT = b"90000000-0000-4000-8000-000000000002"
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

    def test_inspection_does_not_bind_or_run_the_logical_callable(self):
        request = self.request()
        producer = example.work(self.path, b"pending", request, b"done", ATTEMPT)
        before = self.inventory()
        with patch.object(example, "_bind_scaled_sum", side_effect=AssertionError("inspection tried to bind work")):
            self.assertEqual(example.inspect(self.path, b"done", expected=producer)["value"], 84)
        self.assertEqual(self.inventory(), before)


if __name__ == "__main__":
    SCANNER = Path(sys.argv.pop(1)).resolve()
    unittest.main()
