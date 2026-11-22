"""Focused tests of the dispatch boundary; repository rules use the real C API."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from run_histories import check_verdicts, replay_history
from trace_support import Replay


class Fixture:
    def __init__(self):
        self.closed = False

    @contextmanager
    def history(self, directory):
        values = []

        def append_value(value):
            values.append(value)
            return {"length": len(values)}

        def read_value():
            return {"value": values[-1]}

        try:
            yield Replay({"append_value": append_value, "read_value": read_value})
        finally:
            self.closed = True


class TraceInterpreterTest(unittest.TestCase):
    def test_dispatches_new_operations_in_order(self):
        fixture = Fixture()
        with TemporaryDirectory() as tmp:
            observed = replay_history(fixture, Path(tmp) / "history-1", [
                {"op": "append_value", "args": ["a"]},
                {"op": "append_value", "args": ["b"]},
                {"op": "read_value", "args": []},
            ])
        self.assertEqual(observed, {"attempts": [{"length": 1}, {"length": 2}, {"value": "b"}]})
        self.assertTrue(fixture.closed)

    def test_bad_requests_report_step_and_close_fixture(self):
        for request, diagnostic in (({"op": "unknown", "args": []}, "unknown operation"),
                                    ({"op": "append_value", "args": []}, "missing 1 required")):
            with self.subTest(request=request), TemporaryDirectory() as tmp:
                fixture = Fixture()
                with self.assertRaisesRegex(ValueError, f"history-1, step 1.*{diagnostic}"):
                    replay_history(fixture, Path(tmp) / "history-1", [request])
                self.assertTrue(fixture.closed)

    def test_missing_step_verdict_fails(self):
        histories = [[{"op": "read_value", "args": []}]]
        evidence = [{"attempts": [{"value": "a"}]}]
        state = {"controls": True, "coverage": True, "verdicts": [[]], "accepting": [[]]}
        with self.assertRaises(ValueError):
            check_verdicts(histories, evidence, state)


if __name__ == "__main__":
    unittest.main()
