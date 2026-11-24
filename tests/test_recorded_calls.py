"""Test the recorded-calls example across process and repository boundaries."""

from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from daggerml import core


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "recorded_calls.py"


@contextmanager
def transaction(path, mode=core.TXN_READ, *, create=False):
    repo = core.repo_open(path, create)
    try:
        txn = core.txn_begin(repo, mode)
        try:
            yield txn
        finally:
            core.txn_abort(txn)
    finally:
        core.repo_close(repo)


def put(txn, kind, *operands):
    return core.txn_put_object(txn, kind, core.object_encode(kind, *operands))


def literal(txn, kind, value):
    datum = core.txn_put_datum(txn, core.datum_encode(kind, value))
    return put(txn, core.REC_NODE, core.NODE_LITERAL, datum)


def view(txn, kind, object_id):
    return core.object_decode(core.txn_get_object(txn, kind, object_id))


class RecordedCallsTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.repo = self.workspace / "repo"

    def run_example(self, command, *operands):
        return subprocess.run(
            [sys.executable, "-B", EXAMPLE, command, self.repo, *map(str, operands)],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def expect_success(self, command, *operands):
        result = self.run_example(command, *operands)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def expect_failure(self, command, *operands):
        result = self.run_example(command, *operands)
        self.assertEqual(result.returncode, 1, (result.stdout, result.stderr))
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip())
        self.assertNotIn("Traceback", result.stderr)
        return result.stderr

    def node_target(self, txn, node, kind):
        packed = core.txn_get_object(txn, core.REC_NODE, node)
        _, target, _ = core.object_decode(packed)
        self.assertEqual(packed, core.object_encode(core.REC_NODE, kind, target))
        return target

    def literal_value(self, txn, node, kind):
        datum = self.node_target(txn, node, core.NODE_LITERAL)
        payload, actual_kind = core.datum_decode(core.txn_get_datum(txn, datum))
        self.assertEqual(actual_kind, kind)
        if kind == core.DATUM_I64:
            return int.from_bytes(payload, "little", signed=True)
        return payload.decode("utf-8")

    def number(self, txn, node, expected):
        self.assertEqual(self.literal_value(txn, node, core.DATUM_I64), expected)
        return {"node": node.hex(), "value": expected}

    def test_fresh_process_reports_committed_argument_nodes_and_producer(self):
        output = self.expect_success("record", -23, 16, -3)
        with transaction(self.repo) as txn:
            commit = core.txn_ref_get(txn, b"main")
            self.assertEqual(output.strip(), commit.hex())
            _, tree, parents = view(txn, core.REC_COMMIT, commit)
            self.assertEqual(parents, 0)
            tree_view, _, entries = view(txn, core.REC_TREE, tree)
            self.assertEqual(entries, 1)
            scale, name = core.object_view_entry(tree_view, 0)
            self.assertEqual(name, b"recorded-calls-v1")

            _, scale_root, scale_bindings = view(txn, core.REC_DAG, scale)
            self.assertEqual(scale_bindings, 3)
            source = core.txn_lookup_node(txn, scale, b"input")
            producer = self.node_target(txn, source, core.NODE_SUBDAG)
            _, sum_root, sum_bindings = view(txn, core.REC_DAG, producer)
            self.assertEqual(sum_bindings, 3)

            sum_impl = core.txn_lookup_node(txn, producer, b"implementation")
            scale_impl = core.txn_lookup_node(txn, scale, b"implementation")
            self.assertEqual(self.literal_value(txn, sum_impl, core.DATUM_STRING), "example.sum@1")
            self.assertEqual(self.literal_value(txn, scale_impl, core.DATUM_STRING), "example.scale@1")
            a = core.txn_lookup_node(txn, producer, b"a")
            b = core.txn_lookup_node(txn, producer, b"b")
            factor = core.txn_lookup_node(txn, scale, b"factor")
            expected = {
                "commit": commit.hex(),
                "calls": [
                    {
                        "dag": producer.hex(),
                        "implementation": "example.sum@1",
                        "result": self.number(txn, sum_root, -7),
                        "arguments": {"a": self.number(txn, a, -23), "b": self.number(txn, b, 16)},
                    },
                    {
                        "dag": scale.hex(),
                        "implementation": "example.scale@1",
                        "result": self.number(txn, scale_root, 21),
                        "arguments": {
                            "input": {"node": source.hex(), "call": producer.hex(), "value": -7},
                            "factor": self.number(txn, factor, -3),
                        },
                    },
                ],
            }

        self.assertEqual(json.loads(self.expect_success("inspect")), expected)

    def publish_fixture(self, *, linked_input):
        with transaction(self.repo, core.TXN_WRITE, create=True) as txn:
            sum_impl = literal(txn, core.DATUM_STRING, b"example.sum@1")
            scale_impl = literal(txn, core.DATUM_STRING, b"example.scale@1")
            a = literal(txn, core.DATUM_I64, 2)
            b = literal(txn, core.DATUM_I64, 3)
            sum_root = literal(txn, core.DATUM_I64, -17)
            producer = put(txn, core.REC_DAG, sum_root, b"implementation", sum_impl, b"a", a, b"b", b)
            # Another legitimate shape has the exact same root. The edge, not the value or
            # even the result node ID, identifies which invocation supplied the argument.
            decoy = put(txn, core.REC_DAG, sum_root, b"implementation", sum_impl, b"a", b, b"b", a)
            self.assertNotEqual(decoy, producer)
            source = put(txn, core.REC_NODE, core.NODE_SUBDAG, producer) if linked_input else sum_root
            factor = literal(txn, core.DATUM_I64, 6)
            scale_root = literal(txn, core.DATUM_I64, -98)
            scale = put(
                txn, core.REC_DAG, scale_root, b"implementation", scale_impl, b"input", source, b"factor", factor,
            )
            tree = put(txn, core.REC_TREE, b"recorded-calls-v1", scale)
            commit = put(txn, core.REC_COMMIT, tree)
            core.txn_ref_create(txn, b"main", commit)
            core.txn_commit(txn)
            return producer.hex()

    def test_inspect_reports_stored_evidence_without_recomputing_outputs(self):
        selected_call = self.publish_fixture(linked_input=True)
        data_path = self.repo / "data.mdb"
        before = data_path.read_bytes()
        producer, consumer = json.loads(self.expect_success("inspect"))["calls"]
        self.assertEqual(producer["dag"], selected_call)
        self.assertEqual(producer["result"]["value"], -17)  # Not 2 + 3.
        argument = consumer["arguments"]["input"]
        self.assertEqual(argument["call"], selected_call)
        self.assertEqual(argument["value"], -17)
        self.assertEqual(consumer["result"]["value"], -98)  # Not -17 * 6.
        self.assertEqual(data_path.read_bytes(), before)

    def test_inspect_rejects_equal_value_without_producer_edge(self):
        self.publish_fixture(linked_input=False)
        data_path = self.repo / "data.mdb"
        before = data_path.read_bytes()
        diagnostic = self.expect_failure("inspect")
        self.assertIn("wrong node kind", diagnostic)
        self.assertEqual(data_path.read_bytes(), before)

    def test_out_of_range_argument_does_not_create_repository(self):
        diagnostic = self.expect_failure("record", 1 << 63, 0, 1)
        self.assertIn("a is not a signed 64-bit integer", diagnostic)
        self.assertFalse(self.repo.exists())

    def test_overflow_does_not_publish_or_retain_partial_values(self):
        max_i64 = (1 << 63) - 1
        cases = {
            "sum": ((max_i64, 1, 1), max_i64),
            "scale": ((-max_i64, -1, -1), -(1 << 63)),
        }
        for operation, (inputs, partial_value) in cases.items():
            with self.subTest(operation=operation):
                self.repo = self.workspace / operation
                diagnostic = self.expect_failure("record", *inputs)
                self.assertIn(f"example.{operation}@1 result", diagnostic)
                # Get the would-be ID without adding the object to committed state.
                with transaction(self.repo, core.TXN_WRITE) as txn:
                    packed = core.datum_encode(core.DATUM_I64, partial_value)
                    datum = core.txn_put_datum(txn, packed)
                with transaction(self.repo) as txn:
                    with self.assertRaises(core.Error) as ref_error:
                        core.txn_ref_get(txn, b"main")
                    self.assertEqual(ref_error.exception.args[0], "not_found")
                    with self.assertRaises(core.Error) as datum_error:
                        core.txn_get_datum(txn, datum)
                    self.assertEqual(datum_error.exception.args[0], "not_found")

    def test_second_record_cannot_replace_published_snapshot(self):
        commit = self.expect_success("record", 2, 3, 6).strip()
        data_path = self.repo / "data.mdb"
        before = data_path.read_bytes()
        self.expect_failure("record", 13, 17, 41)
        self.assertEqual(data_path.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"main").hex(), commit)


if __name__ == "__main__":
    unittest.main()
