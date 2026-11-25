"""Focused tests of the dispatch boundary; repository rules use the real C API."""

from contextlib import contextmanager
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, call, patch

from replay_core import CoreHistory, bundle_items
from run_histories import check_verdicts, quint_evidence, replay_history
from trace_support import Replay


class ApiError(RuntimeError):
    pass


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

    @patch("replay_core.scan_inventory", return_value={})
    def test_core_dispatch_does_not_end_transaction_on_write_failure(self, scan):
        core = Mock(Error=ApiError)
        repo, txn = object(), object()
        core.repo_open.return_value = repo
        core.txn_begin.return_value = txn
        core.txn_ref_create.side_effect = ApiError("invalid_state", 0, "ref already exists")
        core.txn_commit.side_effect = ApiError("invalid_state", 0, "transaction poisoned")
        target = bytes(range(16))
        history = CoreHistory(core, "scanner", Path("repo"))
        history.values["id"]["A"] = target
        history.run("repo_open", "repo", "create")
        history.run("txn_begin", "repo", "write", "writer")

        self.assertEqual(history.run("txn_ref_create", "writer", "main", "A"), {
            "op": "txn_ref_create", "args": ["writer", "main", "A"], "status": "invalid_state",
            "value": "", "count": 0, "items": [], "changes": [], "otherChanges": [],
        })
        self.assertIs(history.values["txn"]["writer"], txn)
        self.assertEqual(history.run("txn_commit", "writer")["status"], "invalid_state")
        self.assertFalse(history.values["txn"])
        history.run("repo_close", "repo")
        self.assertEqual(core.mock_calls, [
            call.repo_open(str(Path("repo") / "repo"), True), call.txn_begin(repo, 2),
            call.txn_ref_create(txn, b"main", target), call.txn_commit(txn), call.repo_close(repo),
        ])
        self.assertEqual(scan.call_count, len(core.mock_calls))

    def test_binding_errors_are_not_api_statuses(self):
        core = Mock(Error=ApiError)
        core.repo_open.side_effect = RuntimeError("invalid_state", 0, "unexpected binding failure")
        history = CoreHistory(core, "scanner", Path("repo"))
        with self.assertRaisesRegex(RuntimeError, "unexpected binding failure"):
            history.run("repo_open", "repo", "create")

    def test_export_observer_checks_wire_envelope_and_frame_bounds(self):
        root = bytes(range(16))
        header = struct.pack("<4sI16sI", b"DMLB", 1, root, 1)
        frame = struct.pack("<HHI16s", 6, 0, 1, root) + b"x"
        self.assertEqual(bundle_items(header + frame), [root.hex(), "6", root.hex(), "78"])
        for data, message in ((header[:-1], "length"), (header + frame[:10], "frame header"),
                              (header + frame[:-1], "frame"), (header + frame + b"x", "trailing")):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                bundle_items(data)

    def test_quint_evidence_batches_attempts_without_reordering_histories(self):
        observations = [
            {"attempts": [{"value": i} for i in range(17)], "scenario": 4},
            {"attempts": [{"value": 21}], "scenario": 7},
        ]
        first_batch = ", ".join(f"{{ value: {i} }}" for i in range(16))
        self.assertEqual(quint_evidence(observations).splitlines(), [
            f"  pure val evidenceBatch0_0 = List({first_batch})",
            "  pure val evidenceBatch0_16 = List({ value: 16 })",
            "  pure val evidenceHistory0: Observation = { scenario: 4, attempts: "
            "List(evidenceBatch0_0, evidenceBatch0_16).foldl(List(), (out, batch) => out.concat(batch)) }",
            "  pure val evidenceBatch1_0 = List({ value: 21 })",
            "  pure val evidenceHistory1: Observation = { scenario: 7, attempts: evidenceBatch1_0 }",
            "  pure val evidence: List[Observation] = List(evidenceHistory0, evidenceHistory1)",
        ])

    def test_quint_evidence_shares_defaults_without_changing_live_values(self):
        defaults = {"value": 0, "details": {"ok": False}}
        observations = [{"attempts": [defaults, {"value": 1, "details": {"ok": True}},
                                      {"value": 0, "details": {"ok": 0}}]}]
        lines = quint_evidence(observations, attempt_defaults=defaults).splitlines()
        self.assertEqual(lines[:2], [
            "  pure val evidenceDefaults = { value: 0, details: { ok: false } }",
            "  pure val evidenceBatch0_0 = List(evidenceDefaults, { ...evidenceDefaults, value: 1, details: { ok: true } },"
            " { ...evidenceDefaults, details: { ok: 0 } })",
        ])
        for different in ({"value": 0}, {**defaults, "other": 0}):
            with self.subTest(different=different), self.assertRaisesRegex(ValueError, "fields do not match"):
                quint_evidence([{"attempts": [different]}], attempt_defaults=defaults)

    def test_missing_step_verdict_fails(self):
        histories = [[{"op": "read_value", "args": []}]]
        evidence = [{"attempts": [{"value": "a"}]}]
        state = {"controls": True, "coverage": True, "verdicts": [[]], "accepting": [[]]}
        with self.assertRaises(ValueError):
            check_verdicts(histories, evidence, state)


if __name__ == "__main__":
    unittest.main()
