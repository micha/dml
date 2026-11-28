"""Check exact I64 inputs in the captured ordinary example."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from trace_support import scan_inventory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import recorded_ordinary_calls as example


class OrdinaryCallsTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name) / "repo"
        self.defaults = example.defaults(self.repo, b"defaults", 1)
        self.capture = example.capture(self.repo, b"defaults", self.defaults, b"closure")

    def inventory(self):
        return scan_inventory(SCANNER, self.repo)

    def test_non_i64_values_rejected_before_recording(self):
        before = self.inventory()
        for value in (True, 1.5, 1 << 63, -(1 << 63) - 1):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "signed 64-bit integer"):
                example.invoke(self.repo, b"closure", self.capture, b"call", value, 29)
        self.assertEqual(self.inventory(), before)


if __name__ == "__main__":
    SCANNER = Path(sys.argv.pop(1)).resolve()
    unittest.main()
