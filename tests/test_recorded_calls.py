"""Test the recorded-calls example across process and repository boundaries."""

from contextlib import contextmanager
import json
from pathlib import Path
import runpy
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


def put_requested_result(txn, request, producer_dag, factor, output, *, implementation=b"example.scale@1"):
    version = literal(txn, core.DATUM_STRING, implementation)
    source = put(txn, core.REC_NODE, core.NODE_SUBDAG, producer_dag)
    multiplier = literal(txn, core.DATUM_I64, factor)
    root = literal(txn, core.DATUM_I64, output)
    dag = put(txn, core.REC_DAG, root, b"implementation", version, b"input", source, b"factor", multiplier)
    tree = put(txn, core.REC_TREE, b"requested-scale-v1", dag)
    return put(txn, core.REC_COMMIT, tree, request)


class RecordedCallsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.example = runpy.run_path(EXAMPLE)

    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.repo = self.workspace / "repo"

    def run_example(self, command, *operands, repo=None):
        return subprocess.run(
            [sys.executable, "-B", EXAMPLE, command, self.repo if repo is None else repo, *map(str, operands)],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def expect_success(self, command, *operands, repo=None):
        result = self.run_example(command, *operands, repo=repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def expect_failure(self, command, *operands, repo=None):
        result = self.run_example(command, *operands, repo=repo)
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

    def snapshot(self, txn, ref, entry):
        commit = core.txn_ref_get(txn, ref)
        commit_view, tree, parents = view(txn, core.REC_COMMIT, commit)
        tree_view, _, entries = view(txn, core.REC_TREE, tree)
        self.assertEqual(entries, 1)
        dag, name = core.object_view_entry(tree_view, 0)
        self.assertEqual(name, entry)
        return commit, dag, tuple(core.object_view_parent(commit_view, index) for index in range(parents))

    def assert_missing_ref(self, txn, name):
        with self.assertRaises(core.Error) as error:
            core.txn_ref_get(txn, name)
        self.assertEqual(error.exception.args[0], "not_found")

    def test_compose_each_pinned_sum_even_when_both_share_a_result_node(self):
        expected = self.expect_success("record-sum", "producer", 7, 5).strip()
        decoy = self.expect_success("record-sum", "decoy", 9, 3).strip()
        consumer = self.expect_success("record-scale", "producer", expected, "main", 3).strip()
        alternate = self.expect_success("record-scale", "decoy", decoy, "alternate", 3).strip()
        with transaction(self.repo) as txn:
            first, first_dag, parents = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            self.assertEqual(parents, ())
            second, second_dag, parents = self.snapshot(txn, b"decoy", b"recorded-sum-v1")
            self.assertEqual(parents, ())
            self.assertEqual((first.hex(), second.hex()), (expected, decoy))
            self.assertNotEqual(first, second)
            self.assertNotEqual(first_dag, second_dag)
            _, first_root, _ = view(txn, core.REC_DAG, first_dag)
            _, second_root, _ = view(txn, core.REC_DAG, second_dag)
            self.assertEqual(first_root, second_root)
            self.assertEqual(self.literal_value(txn, first_root, core.DATUM_I64), 12)
            for ref, printed, parent, producer in (
                (b"main", consumer, first, first_dag), (b"alternate", alternate, second, second_dag),
            ):
                commit, scale, parents = self.snapshot(txn, ref, b"recorded-scale-v1")
                self.assertEqual(commit.hex(), printed)
                self.assertEqual(parents, (parent,))
                source = core.txn_lookup_node(txn, scale, b"input")
                self.assertEqual(self.node_target(txn, source, core.NODE_SUBDAG), producer)
        self.assertNotEqual(consumer, alternate)

        sum_report = json.loads(self.expect_success("inspect", "producer"))
        self.assertEqual(sum_report["commit"], expected)
        self.assertEqual([call["dag"] for call in sum_report["calls"]], [first_dag.hex()])

        # Neither changing the input ref to an equal-valued decoy nor releasing both
        # pins changes the already committed parent and sub-DAG edge.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"producer", second)
            core.txn_commit(txn)
        moved = json.loads(self.expect_success("inspect"))
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_delete_expected(txn, b"producer", second)
            core.txn_ref_delete_expected(txn, b"decoy", second)
            core.txn_commit(txn)
        data_path = self.repo / "data.mdb"
        before = data_path.read_bytes()
        main = json.loads(self.expect_success("inspect"))
        other = json.loads(self.expect_success("inspect", "alternate"))
        self.assertEqual(data_path.read_bytes(), before)
        self.assertEqual(main, moved)
        for report, commit, parent, dag, a, b in (
            (main, consumer, expected, first_dag, 7, 5), (other, alternate, decoy, second_dag, 9, 3),
        ):
            self.assertEqual(report["commit"], commit)
            self.assertEqual(report["producer_commit"], parent)
            summed, scaled = report["calls"]
            self.assertEqual(summed["dag"], dag.hex())
            self.assertEqual(summed["arguments"]["a"]["value"], a)
            self.assertEqual(summed["arguments"]["b"]["value"], b)
            self.assertEqual(scaled["arguments"]["input"]["call"], dag.hex())
            self.assertEqual(scaled["arguments"]["input"]["value"], 12)
            self.assertEqual(scaled["result"]["value"], 36)

    def test_scale_rejects_stale_or_missing_pin_even_if_requested_commit_exists(self):
        expected = self.expect_success("record-sum", "producer", 7, 5).strip()
        decoy = self.expect_success("record-sum", "decoy", 9, 3).strip()
        data_path = self.repo / "data.mdb"
        before = data_path.read_bytes()
        for pin, reason in (("decoy", "expected commit"), ("missing", "not_found")):
            with self.subTest(pin=pin):
                self.assertIn(reason, self.expect_failure("record-scale", pin, expected, "main", 3))
                self.assertEqual(data_path.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"producer").hex(), expected)
            self.assertEqual(core.txn_ref_get(txn, b"decoy").hex(), decoy)
            self.assert_missing_ref(txn, b"main")

    def test_rejected_writes_keep_existing_refs_and_discard_new_values(self):
        expected = self.expect_success("record-sum", "producer", 7, 5).strip()
        consumer = self.expect_success("record-scale", "producer", expected, "main", 3).strip()
        data_path = self.repo / "data.mdb"
        cases = (
            ("record-sum", ("producer", 43, 77), 43, "invalid_state"),
            ("record-scale", ("producer", expected, "producer", 41), 41, "invalid_state"),
            ("record-scale", ("producer", expected, "main", 17), 17, "invalid_state"),
            ("record-scale", ("producer", expected, "overflow", 1 << 62), 1 << 62, "example.scale@1 result"),
        )
        for command, arguments, candidate_value, reason in cases:
            with self.subTest(command=command, arguments=arguments):
                # Derive the ID without permanently storing the candidate datum.
                with transaction(self.repo, core.TXN_WRITE) as txn:
                    datum = core.txn_put_datum(txn, core.datum_encode(core.DATUM_I64, candidate_value))
                before = data_path.read_bytes()
                self.assertIn(reason, self.expect_failure(command, *arguments))
                self.assertEqual(data_path.read_bytes(), before)
                with transaction(self.repo) as txn:
                    self.assertEqual(core.txn_ref_get(txn, b"producer").hex(), expected)
                    self.assertEqual(core.txn_ref_get(txn, b"main").hex(), consumer)
                    self.assert_missing_ref(txn, b"overflow")
                    with self.assertRaises(core.Error) as error:
                        core.txn_get_datum(txn, datum)
                    self.assertEqual(error.exception.args[0], "not_found")

    def publish_sum_fixture(self, implementation=b"example.sum@1"):
        with transaction(self.repo, core.TXN_WRITE, create=True) as txn:
            implementation_node = literal(txn, core.DATUM_STRING, implementation)
            a = literal(txn, core.DATUM_I64, 2)
            b = literal(txn, core.DATUM_I64, 3)
            root = literal(txn, core.DATUM_I64, -17)
            producer = put(txn, core.REC_DAG, root, b"implementation", implementation_node, b"a", a, b"b", b)
            tree = put(txn, core.REC_TREE, b"recorded-sum-v1", producer)
            commit = put(txn, core.REC_COMMIT, tree)
            core.txn_ref_create(txn, b"producer", commit)
            core.txn_commit(txn)
            return commit, producer, root

    def test_scale_uses_the_stored_sum_result_without_reexecuting_sum(self):
        commit, producer, root = self.publish_sum_fixture()
        self.expect_success("record-scale", "producer", commit.hex(), "main", 6)
        with transaction(self.repo) as txn:
            _, scale, _ = self.snapshot(txn, b"main", b"recorded-scale-v1")
            _, scale_root, _ = view(txn, core.REC_DAG, scale)
            self.assertEqual(self.literal_value(txn, scale_root, core.DATUM_I64), -102)  # Not (2 + 3) * 6.
        report = json.loads(self.expect_success("inspect"))
        self.assertEqual(report["producer_commit"], commit.hex())
        summed, scaled = report["calls"]
        self.assertEqual(summed["result"], {"node": root.hex(), "value": -17})
        self.assertEqual(scaled["arguments"]["input"]["call"], producer.hex())
        self.assertEqual(scaled["arguments"]["input"]["value"], -17)
        self.assertEqual(scaled["result"]["value"], -102)

    def test_handoff_scales_stored_value_and_keeps_exact_lineage_after_collection(self):
        expected, producer, stored_root = self.publish_sum_fixture()
        decoy = self.expect_success("record-sum", "decoy", 6, -23).strip()  # Same stored result: -17.
        origin = self.repo / "data.mdb"
        origin_before = origin.read_bytes()
        worker = self.workspace / "worker"
        selected_bundle = self.workspace / "selected.dmlb"
        decoy_bundle = self.workspace / "decoy.dmlb"
        for pin, commit, bundle, dest_pin in (
            ("producer", expected.hex(), selected_bundle, "incoming"),
            ("decoy", decoy, decoy_bundle, "discard"),
        ):
            self.assertEqual(self.expect_success("export-sum", pin, commit, bundle).strip(), commit)
            self.assertEqual(self.expect_success("stage-input", dest_pin, bundle, repo=worker).strip(), commit)
            bundle.unlink()  # No bundle is available to any later worker invocation.

        result = self.expect_success("record-scale", "incoming", expected.hex(), "main", 6, repo=worker).strip()
        self.assertEqual(self.expect_success("release-input", "incoming", expected.hex(), "main", repo=worker).strip(),
                         expected.hex())
        with transaction(worker, core.TXN_WRITE) as txn:
            self.assert_missing_ref(txn, b"incoming")
            core.txn_ref_delete_expected(txn, b"discard", bytes.fromhex(decoy))
            core.txn_commit(txn)
        with transaction(worker) as txn:
            view(txn, core.REC_COMMIT, bytes.fromhex(decoy))  # Ref release alone did not collect it.
        self.assertGreater(int(self.expect_success("collect", repo=worker)), 0)

        with transaction(worker) as txn:
            with self.assertRaises(core.Error) as collected:
                core.txn_get_object(txn, core.REC_COMMIT, bytes.fromhex(decoy))
            self.assertEqual(collected.exception.args[0], "not_found")
            self.assert_missing_ref(txn, b"producer")  # Bundles did not copy origin refs.
            self.assert_missing_ref(txn, b"incoming")
            commit, scale, parents = self.snapshot(txn, b"main", b"recorded-scale-v1")
            self.assertEqual((commit.hex(), parents), (result, (expected,)))
            _, sum_tree, _ = view(txn, core.REC_COMMIT, expected)
            sum_view, _, _ = view(txn, core.REC_TREE, sum_tree)
            self.assertEqual(core.object_view_entry(sum_view, 0), (producer, b"recorded-sum-v1"))
            self.assertEqual(view(txn, core.REC_DAG, producer)[1], stored_root)
            input_node = core.txn_lookup_node(txn, scale, b"input")
            self.assertEqual(self.node_target(txn, input_node, core.NODE_SUBDAG), producer)
            result_node = view(txn, core.REC_DAG, scale)[1]
            self.assertEqual(self.literal_value(txn, result_node, core.DATUM_I64), -102)  # Not (2 + 3) * 6.

        data = worker / "data.mdb"
        before = data.read_bytes()
        report = json.loads(self.expect_success("inspect", repo=worker))
        self.assertEqual(report["commit"], result)
        self.assertEqual(report["producer_commit"], expected.hex())
        summed, scaled = report["calls"]
        self.assertEqual(summed["result"], {"node": stored_root.hex(), "value": -17})
        self.assertEqual(scaled["arguments"]["input"], {"node": input_node.hex(), "value": -17, "call": producer.hex()})
        self.assertEqual(scaled["result"], {"node": result_node.hex(), "value": -102})
        self.assertEqual(data.read_bytes(), before)
        self.assertEqual(origin.read_bytes(), origin_before)

    def test_handoff_rejects_decoy_identity_and_unverified_release_without_changes(self):
        expected = self.expect_success("record-sum", "producer", 7, 5).strip()
        decoy = self.expect_success("record-sum", "decoy", 9, 3).strip()
        expected_id, decoy_id = bytes.fromhex(expected), bytes.fromhex(decoy)
        self.assertNotEqual(expected_id, decoy_id)
        worker = self.workspace / "worker"
        data = worker / "data.mdb"
        selected_bundle = self.workspace / "selected.dmlb"
        decoy_bundle = self.workspace / "decoy.dmlb"

        self.assertIn("expected commit", self.expect_failure("export-sum", "decoy", expected, selected_bundle))
        self.assertFalse(selected_bundle.exists())
        self.expect_success("export-sum", "producer", expected, selected_bundle)
        self.expect_success("export-sum", "decoy", decoy, decoy_bundle)
        selected_bytes = selected_bundle.read_bytes()
        self.expect_failure("export-sum", "decoy", decoy, selected_bundle)
        self.assertEqual(selected_bundle.read_bytes(), selected_bytes)
        self.assertEqual(self.expect_success("stage-input", "incoming", decoy_bundle, repo=worker).strip(), decoy)

        def worker_rejects(reason, command, *operands):
            before = data.read_bytes()
            self.assertIn(reason, self.expect_failure(command, *operands, repo=worker))
            self.assertEqual(data.read_bytes(), before)

        worker_rejects("invalid_state", "stage-input", "incoming", decoy_bundle)
        worker_rejects("invalid_state", "stage-input", "incoming", selected_bundle)
        worker_rejects("expected commit", "record-scale", "incoming", expected, "main", 3)
        self.expect_success("record-scale", "incoming", decoy, "other", 3, repo=worker)
        with transaction(worker, core.TXN_WRITE) as txn:
            self.assert_missing_ref(txn, b"main")
            core.txn_ref_delete_expected(txn, b"incoming", decoy_id)
            core.txn_commit(txn)
        self.expect_success("stage-input", "incoming", selected_bundle, repo=worker)
        worker_rejects("not_found", "release-input", "incoming", expected, "main")
        worker_rejects("does not retain the expected producer commit", "release-input", "incoming", expected, "other")
        self.expect_success("record-scale", "incoming", expected, "main", 3, repo=worker)

        with transaction(worker, core.TXN_WRITE) as txn:
            other = core.txn_ref_get(txn, b"other")
            _, wrong_tree, _ = view(txn, core.REC_COMMIT, other)
            # The expected sole parent is present, but the input DAG in this tree belongs to the decoy.
            forged = put(txn, core.REC_COMMIT, wrong_tree, expected_id)
            core.txn_ref_create(txn, b"forged", forged)
            core.txn_commit(txn)
        worker_rejects("does not match the producer parent", "release-input", "incoming", expected, "forged")

        with transaction(worker, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"incoming", decoy_id)
            core.txn_commit(txn)
        worker_rejects("invalid_state", "release-input", "incoming", expected, "main")
        with transaction(worker) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"incoming"), decoy_id)

    def test_truncated_bundle_never_publishes_a_pin_or_partial_closure(self):
        expected, producer, _ = self.publish_sum_fixture()
        worker = self.workspace / "worker"
        bundle = self.workspace / "selected.dmlb"
        truncated = self.workspace / "truncated.dmlb"
        self.expect_success("export-sum", "producer", expected.hex(), bundle)
        truncated.write_bytes(bundle.read_bytes()[:-1])

        self.assertIn("invalid_bounds", self.expect_failure("stage-input", "incoming", truncated, repo=worker))
        # The first attempt may initialize the repository, but not commit the import.
        with transaction(worker, create=True) as txn:
            self.assert_missing_ref(txn, b"incoming")
            with self.assertRaises(core.Error) as absent:
                core.txn_get_object(txn, core.REC_DAG, producer)
            self.assertEqual(absent.exception.args[0], "not_found")

        data = worker / "data.mdb"
        before = data.read_bytes()
        self.assertIn("invalid_bounds", self.expect_failure("stage-input", "incoming", truncated, repo=worker))
        self.assertEqual(data.read_bytes(), before)
        self.assertEqual(self.expect_success("stage-input", "incoming", bundle, repo=worker).strip(), expected.hex())

    def test_return_publishes_stored_output_and_retains_both_links_without_source_pin(self):
        producer, sum_dag, _ = self.publish_sum_fixture()
        decoy = bytes.fromhex(self.expect_success("record-sum", "decoy", 6, -23).strip())
        worker = self.workspace / "worker"
        outbound = self.workspace / "sum.dmlb"
        inbound = self.workspace / "scale.dmlb"
        self.expect_success("export-sum", "producer", producer.hex(), outbound)
        self.expect_success("stage-input", "incoming", outbound, repo=worker)
        with transaction(worker, core.TXN_WRITE) as txn:
            source = put(txn, core.REC_NODE, core.NODE_SUBDAG, sum_dag)
            factor = literal(txn, core.DATUM_I64, 6)
            version = literal(txn, core.DATUM_STRING, b"example.scale@1")
            root = literal(txn, core.DATUM_I64, -98)  # Neither (2 + 3) * 6 nor -17 * 6.
            dag = put(txn, core.REC_DAG, root, b"implementation", version, b"input", source, b"factor", factor)
            tree = put(txn, core.REC_TREE, b"recorded-scale-v1", dag)
            result = put(txn, core.REC_COMMIT, tree, producer)
            core.txn_ref_create(txn, b"result", result)
            core.txn_commit(txn)
        worker_report = self.expect_success("inspect", "result", repo=worker)
        worker_data = worker / "data.mdb"
        worker_before = worker_data.read_bytes()
        self.assertEqual(self.expect_success("export-scale", "result", result.hex(), inbound, repo=worker).strip(),
                         result.hex())
        self.assertEqual(self.expect_success("stage-input", "returned", inbound).strip(), result.hex())
        self.assertEqual(self.expect_success("inspect", "returned"), worker_report)
        outbound.unlink()
        inbound.unlink()  # Publication uses only objects that have already been staged.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_delete_expected(txn, b"producer", producer)
            core.txn_ref_delete_expected(txn, b"decoy", decoy)
            core.txn_commit(txn)

        data = self.repo / "data.mdb"
        before = data.read_bytes()
        self.assertIn("recorded factor does not match the expected factor",
                      self.expect_failure("publish-scale", "returned", result.hex(), producer.hex(), 5, "-"))
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assert_missing_ref(txn, b"main")
            self.assertEqual(core.txn_ref_get(txn, b"returned"), result)

        report = self.expect_success("publish-scale", "returned", result.hex(), producer.hex(), 6, "-")
        self.assertEqual(report.strip(), result.hex())
        self.assertGreater(int(self.expect_success("collect")), 0)
        with transaction(self.repo) as txn:
            for ref in (b"producer", b"decoy", b"returned", b"incoming", b"result"):
                self.assert_missing_ref(txn, ref)
            with self.assertRaises(core.Error) as collected:
                core.txn_get_object(txn, core.REC_COMMIT, decoy)
            self.assertEqual(collected.exception.args[0], "not_found")
            self.assertEqual(self.snapshot(txn, b"main", b"recorded-scale-v1"), (result, dag, (producer,)))
            _, producer_tree, _ = view(txn, core.REC_COMMIT, producer)
            tree_view, _, _ = view(txn, core.REC_TREE, producer_tree)
            self.assertEqual(core.object_view_entry(tree_view, 0), (sum_dag, b"recorded-sum-v1"))
            input_node = core.txn_lookup_node(txn, dag, b"input")
            self.assertEqual(self.node_target(txn, input_node, core.NODE_SUBDAG), sum_dag)
            self.assertEqual(self.literal_value(txn, view(txn, core.REC_DAG, dag)[1], core.DATUM_I64), -98)
        self.assertEqual(self.expect_success("inspect"), worker_report)
        self.assertEqual(worker_data.read_bytes(), worker_before)

    def test_failed_staging_guard_rolls_back_both_create_and_update_of_main(self):
        producer = self.expect_success("record-sum", "producer", 7, 5).strip()
        result = self.expect_success("record-scale", "producer", producer, "result", 3).strip()
        other = self.expect_success("record-scale", "producer", producer, "other", 4).strip()
        producer_id, result_id, other_id = (bytes.fromhex(commit) for commit in (producer, result, other))
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_create(txn, b"returned", result_id)
            core.txn_commit(txn)
        self.assertEqual(json.loads(self.expect_success("inspect", "returned"))["commit"], result)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"returned", other_id)
            core.txn_commit(txn)
        data = self.repo / "data.mdb"

        def reject(reason, pin, expected_main):
            before = data.read_bytes()
            self.assertIn(reason, self.expect_failure("publish-scale", pin, result, producer, 3, expected_main))
            self.assertEqual(data.read_bytes(), before)

        reject("ref target differs", "returned", "-")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            self.assert_missing_ref(txn, b"main")
            core.txn_ref_create(txn, b"main", producer_id)
            core.txn_commit(txn)
        reject("ref target differs", "returned", producer)
        reject("must differ from main", "main", producer)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"main"), producer_id)
            self.assertEqual(core.txn_ref_get(txn, b"returned"), other_id)
            core.txn_ref_delete_expected(txn, b"returned", other_id)
            core.txn_commit(txn)
        reject("not_found", "returned", producer)
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"main"), producer_id)
            self.assert_missing_ref(txn, b"returned")

    def test_durable_plan_updates_existing_main_without_exporting_it(self):
        producer = self.expect_success("record-sum", "producer", 7, 5).strip()
        previous = self.expect_success("record-sum", "main", 12, 0).strip()
        producer_id, previous_id = bytes.fromhex(producer), bytes.fromhex(previous)
        plan = self.expect_success("request-scale", "producer", producer, "plan", -3).strip()
        pending = json.loads(self.expect_success("inspect", "plan"))
        self.assertEqual(pending["expected_main"], previous)
        self.assertEqual(pending["producer_commit"], producer)
        self.assertEqual(pending["request_factor"], -3)
        self.assertEqual(pending["request_implementation"], "example.scale@1")

        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            core.txn_ref_delete_expected(txn, b"producer", producer_id)
            core.txn_ref_update(txn, b"main", producer_id)
            core.txn_commit(txn)
        self.expect_success("collect")  # The plan, not either ref, pins the original state.
        worker = self.workspace / "worker"
        outbound = self.workspace / "request.dmlb"
        inbound = self.workspace / "result.dmlb"
        request = self.expect_success("export-request", "plan", plan, outbound).strip()
        self.assertEqual(request, pending["request_commit"])
        request_id = bytes.fromhex(request)
        self.assertEqual(self.expect_success("stage-input", "incoming", outbound, repo=worker).strip(), request)
        with transaction(worker) as txn:
            self.assert_missing_ref(txn, b"main")
            for private_id in (bytes.fromhex(plan), previous_id):
                with self.assertRaises(core.Error) as absent:
                    core.txn_get_object(txn, core.REC_COMMIT, private_id)
                self.assertEqual(absent.exception.args[0], "not_found")
        result = self.expect_success("work-scale", "incoming", request, "result", repo=worker).strip()
        self.expect_success("export-scale", "result", result, inbound, repo=worker)
        self.assertEqual(self.expect_success("stage-input", "returned", inbound).strip(), result)
        worker_report = self.expect_success("inspect", "result", repo=worker)
        outbound.unlink()
        inbound.unlink()

        before = (self.repo / "data.mdb").read_bytes()
        self.assertIn("main does not point to the expected commit",
                      self.expect_failure("publish-requested-scale", "plan", plan, "returned", result))
        self.assertEqual((self.repo / "data.mdb").read_bytes(), before)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", previous_id)
            core.txn_commit(txn)
        self.assertEqual(self.expect_success("publish-requested-scale", "plan", plan, "returned", result).strip(),
                         result)
        self.assertGreater(int(self.expect_success("collect")), 0)
        with transaction(self.repo) as txn:
            result_id, scale, parents = self.snapshot(txn, b"main", b"requested-scale-v1")
            self.assertEqual((result_id.hex(), parents), (result, (request_id,)))
            request_view, _, count = view(txn, core.REC_COMMIT, request_id)
            self.assertEqual(count, 1)
            self.assertEqual(core.object_view_parent(request_view, 0), producer_id)
            self.assertEqual(self.node_target(txn, core.txn_lookup_node(txn, scale, b"input"), core.NODE_SUBDAG),
                             sum_dag)
            for ref in (b"plan", b"returned", b"producer"):
                self.assert_missing_ref(txn, ref)
            for private_id in (bytes.fromhex(plan), previous_id):
                with self.assertRaises(core.Error) as swept:
                    core.txn_get_object(txn, core.REC_COMMIT, private_id)
                self.assertEqual(swept.exception.args[0], "not_found")
        self.assertEqual(self.expect_success("inspect"), worker_report)

    def test_durable_publication_checks_factor_and_physical_link_on_exact_request(self):
        producer = self.expect_success("record-sum", "producer", 7, -7).strip()
        self.expect_success("record-sum", "decoy", 8, -8)
        plan = self.expect_success("request-scale", "producer", producer, "plan", 3).strip()
        request = bytes.fromhex(json.loads(self.expect_success("inspect", "plan"))["request_commit"])
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, decoy_dag, _ = self.snapshot(txn, b"decoy", b"recorded-sum-v1")
            self.assertNotEqual(sum_dag, decoy_dag)
            self.assertEqual(view(txn, core.REC_DAG, sum_dag)[1], view(txn, core.REC_DAG, decoy_dag)[1])
            version = literal(txn, core.DATUM_STRING, b"example.scale@1")
            candidates = {}
            for pin, factor, source_dag, output in (
                (b"wrong-factor", -2, sum_dag, 0), (b"wrong-input", 3, decoy_dag, 0),
                (b"returned", 3, sum_dag, -98),  # Publication checks records, not arithmetic.
            ):
                source = put(txn, core.REC_NODE, core.NODE_SUBDAG, source_dag)
                multiplier = literal(txn, core.DATUM_I64, factor)
                root = literal(txn, core.DATUM_I64, output)
                dag = put(txn, core.REC_DAG, root, b"implementation", version, b"input", source,
                          b"factor", multiplier)
                tree = put(txn, core.REC_TREE, b"requested-scale-v1", dag)
                candidates[pin] = put(txn, core.REC_COMMIT, tree, request)
                core.txn_ref_create(txn, pin, candidates[pin])
            core.txn_commit(txn)

        before = (self.repo / "data.mdb").read_bytes()
        for pin, reason in ((b"wrong-factor", "recorded factor does not match"),
                            (b"wrong-input", "scale input DAG does not match")):
            with self.subTest(pin=pin):
                self.assertIn(reason, self.expect_failure("publish-requested-scale", "plan", plan, pin.decode(),
                                                          candidates[pin].hex()))
                self.assertEqual((self.repo / "data.mdb").read_bytes(), before)
        result = candidates[b"returned"].hex()
        self.assertIn("distinct", self.expect_failure("publish-requested-scale", "plan", plan, "plan", result))
        self.assertIn("recorded-scale-v1", self.expect_failure("publish-scale", "returned", result, producer, 3, "-"))
        self.assertEqual((self.repo / "data.mdb").read_bytes(), before)
        self.assertEqual(self.expect_success("publish-requested-scale", "plan", plan, "returned", result).strip(),
                         result)
        report = json.loads(self.expect_success("inspect"))
        self.assertEqual(report["calls"][1]["result"]["value"], -98)

    def test_result_with_exact_request_parent_but_wrong_implementation_is_rejected(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        previous = self.example["record_sum"](self.repo, b"main", 12, 0)
        plan = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3,
                                             implementation=b"example.scale@2")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, _, (request, _) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            bad_result = put_requested_result(txn, request, sum_dag, 3, 36)
            core.txn_ref_create(txn, b"candidate", bad_result)
            core.txn_commit(txn)

        bundle = self.workspace / "candidate.dmlb"
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for args in (
            ("inspect", "candidate"),
            ("export-scale", "candidate", bad_result.hex(), bundle),
            ("publish-requested-scale", "plan", plan.hex(), "candidate", bad_result.hex(), "--receipt-ref", "ack"),
            ("stage-reused-scale", "plan", plan.hex(), "candidate", bad_result.hex(), "returned"),
            ("publish-reused-scale", "plan", plan.hex(), "candidate", bad_result.hex(), "proof"),
        ):
            with self.subTest(command=args[0]):
                self.assertIn("expected recorded implementation example.scale@2", self.expect_failure(*args))
                self.assertEqual(data.read_bytes(), before)
        self.assertFalse(bundle.exists())
        with transaction(self.repo) as txn:
            for ref, commit in ((b"main", previous), (b"plan", plan), (b"candidate", bad_result)):
                self.assertEqual(core.txn_ref_get(txn, ref), commit)
            for ref in (b"ack", b"returned", b"proof"):
                self.assert_missing_ref(txn, ref)

    def test_reuse_commands_reject_malformed_plan_and_inconsistent_results(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        self.example["record_sum"](self.repo, b"decoy", 9, 3)
        plan = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3)
        self.example["request_scale"](self.repo, b"producer", producer, b"other-plan", 4)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, _, (request,) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            _, other_dag, (other_request,) = self.snapshot(txn, b"other-plan", b"scale-plan-v1")
            _, producer_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, decoy_dag, _ = self.snapshot(txn, b"decoy", b"recorded-sum-v1")
            self.assertNotEqual(producer_dag, decoy_dag)
            self.assertEqual(view(txn, core.REC_DAG, producer_dag)[1], view(txn, core.REC_DAG, decoy_dag)[1])

            bad_plan_tree = put(txn, core.REC_TREE, b"scale-plan-v1", other_dag)
            bad_plan = put(txn, core.REC_COMMIT, bad_plan_tree, request)
            core.txn_ref_create(txn, b"bad-plan", bad_plan)
            good = put_requested_result(txn, request, producer_dag, 3, 36)
            _, good_tree, _ = view(txn, core.REC_COMMIT, good)
            candidates = {
                b"bad-shape": put(txn, core.REC_COMMIT, good_tree),  # Missing request parent.
                b"wrong-factor": put_requested_result(txn, request, producer_dag, 4, 36),
                b"wrong-producer": put_requested_result(txn, request, decoy_dag, 3, 36),
                # Exact expected DAG and factor, but the parent has a different request ID.
                b"wrong-request": put(txn, core.REC_COMMIT, good_tree, other_request),
                b"good": good,
            }
            for pin, commit in candidates.items():
                core.txn_ref_create(txn, pin, commit)
            core.txn_commit(txn)

        data = self.repo / "data.mdb"
        before = data.read_bytes()
        cases = (
            (b"bad-plan", bad_plan, b"good", "plan DAG does not match"),
            (b"plan", plan, b"bad-shape", "required parents"),
            (b"plan", plan, b"wrong-factor", "recorded factor does not match"),
            (b"plan", plan, b"wrong-producer", "scale input DAG does not match"),
            (b"plan", plan, b"wrong-request", "result does not retain the expected request commit"),
        )
        for command in ("stage_reused_scale", "publish_reused_scale"):
            reuse = self.example[command]
            for plan_pin, plan_commit, result_pin, reason in cases:
                with self.subTest(command=command, plan=plan_pin, result=result_pin):
                    with self.assertRaisesRegex(ValueError, reason):
                        reuse(self.repo, plan_pin, plan_commit, result_pin, candidates[result_pin], b"dest")
                    self.assertEqual(data.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "result does not retain the expected request commit"):
            self.example["publish_requested_scale"](self.repo, b"plan", plan, b"wrong-request",
                                                    candidates[b"wrong-request"])
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assert_missing_ref(txn, b"dest")
            self.assert_missing_ref(txn, b"main")

    def test_stage_reused_scale_preserves_stored_evidence_and_publication_state(self):
        producer = self.example["record_sum"](self.repo, b"producer", (1 << 63) - 1, 0)
        first_plan = self.example["request_scale"](self.repo, b"producer", producer, b"first-plan", 3)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, _, (request,) = self.snapshot(txn, b"first-plan", b"scale-plan-v1")
            # Real execution would overflow; reuse should retain the literal output unchanged.
            result = put_requested_result(txn, request, sum_dag, 3, -98)
            for pin in (b"history", b"returned"):
                core.txn_ref_create(txn, pin, result)
            core.txn_commit(txn)
        self.example["publish_requested_scale"](
            self.repo, b"first-plan", first_plan, b"returned", result, receipt_ref=b"ack")
        previous = self.example["record_sum"](self.repo, b"unrelated", 2, 0)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", previous)
            receipt = core.txn_ref_get(txn, b"ack")
            core.txn_commit(txn)
        plan = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3)
        self.assertNotEqual(plan, first_plan)
        history = self.example["inspect"](self.repo, b"history")
        self.assertEqual(history["request_commit"], request.hex())
        self.assertEqual(history["calls"][1]["result"]["value"], -98)
        destination = "1" + "a" * 124 + "._-"

        staged = self.expect_success("stage-reused-scale", "plan", plan.hex(), "history", result.hex(), destination)
        self.assertEqual(staged.strip(), result.hex())
        with transaction(self.repo) as txn:
            for pin, expected in ((b"plan", plan), (b"main", previous), (b"ack", receipt),
                                  (b"history", result), (destination.encode("ascii"), result)):
                self.assertEqual(core.txn_ref_get(txn, pin), expected)
        self.assertEqual(json.loads(self.expect_success("inspect", destination)), history)

        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_delete_expected(txn, b"history", result)
            core.txn_commit(txn)
        self.expect_success("collect")
        published = self.expect_success("publish-requested-scale", "plan", plan.hex(), destination, result.hex())
        self.assertEqual(published.strip(), result.hex())
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"main"), result)
            self.assertEqual(core.txn_ref_get(txn, b"ack"), receipt)
            for pin in (b"history", b"plan", destination.encode("ascii")):
                self.assert_missing_ref(txn, pin)
        self.assertEqual(json.loads(self.expect_success("inspect")), history)

    def test_reuse_commands_validate_ids_and_all_ref_slots_before_opening_repository(self):
        class BytesSubclass(bytes):
            pass

        class UnopenablePath:
            def __fspath__(self):
                raise AssertionError("invalid selections must be rejected before opening the repository")

        identifier = bytes(16)
        selection = (b"plan", identifier, b"history", identifier, b"dest")
        invalid_refs = ("ref", bytearray(b"ref"), BytesSubclass(b"ref"), b"", b"-ref", b"ref/name",
                        b"r\xc3\xa9f", b"ref\n", b"x" * 129)
        aliases = ((b"main", b"history", b"dest"), (b"plan", b"main", b"dest"),
                   (b"plan", b"history", b"main"), (b"plan", b"plan", b"dest"),
                   (b"plan", b"history", b"history"), (b"plan", b"history", b"plan"))
        for command, output_ref in (("stage_reused_scale", "destination"), ("publish_reused_scale", "reuse")):
            reuse = self.example[command]
            for index, label in ((0, "plan"), (2, "result"), (4, output_ref)):
                for invalid in invalid_refs:
                    args = list(selection)
                    args[index] = invalid
                    with self.subTest(command=command, ref=label, invalid=invalid):
                        with self.assertRaisesRegex(ValueError, f"{label} ref.*ASCII.*bytes"):
                            reuse(UnopenablePath(), *args)
            for plan, result, dest in aliases:
                with self.subTest(command=command, plan=plan, result=result, dest=dest):
                    with self.assertRaisesRegex(ValueError, "distinct"):
                        reuse(UnopenablePath(), plan, identifier, result, identifier, dest)
            for index, label in ((1, "plan"), (3, "result")):
                for invalid in (identifier.hex(), bytearray(identifier), BytesSubclass(identifier), b"x" * 15, b"x" * 17):
                    args = list(selection)
                    args[index] = invalid
                    with self.subTest(command=command, commit=label, invalid=invalid):
                        with self.assertRaisesRegex(ValueError, f"{label} commit.*16-byte ID"):
                            reuse(UnopenablePath(), *args)

    def test_publish_reused_scale_retains_historical_edges_without_reexecuting(self):
        producer = self.example["record_sum"](self.repo, b"producer", (1 << 63) - 1, 0)
        previous = self.example["record_sum"](self.repo, b"main", 2, 0)
        plan_pin = b"1" + b"a" * 124 + b"._-"
        plan = self.example["request_scale"](self.repo, b"producer", producer, plan_pin, 3)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, _, (request, captured) = self.snapshot(txn, plan_pin, b"scale-plan-v1")
            self.assertEqual(captured, previous)
            # Execution would overflow. Both results match structurally, but only
            # the explicitly selected result belongs in main and the reuse record.
            result = put_requested_result(txn, request, sum_dag, 3, -98)
            alternate = put_requested_result(txn, request, sum_dag, 3, 99)
            core.txn_ref_create(txn, b"history", result)
            core.txn_ref_create(txn, b"staged", alternate)
            core.txn_commit(txn)
        stored = self.example["inspect"](self.repo, b"history")
        self.assertEqual(stored["calls"][1]["result"]["value"], -98)
        publish = self.example["publish_reused_scale"]
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "result pin does not point to the expected commit"):
            publish(self.repo, plan_pin, plan, b"history", alternate, b"reuse")
        self.assertEqual(data.read_bytes(), before)

        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", producer)
            core.txn_commit(txn)
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "main does not point to the expected commit"):
            publish(self.repo, plan_pin, plan, b"history", result, b"reuse")
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", previous)
            core.txn_commit(txn)
        self.assertEqual(publish(self.repo, plan_pin, plan, b"history", result, b"reuse"), result)

        with transaction(self.repo) as txn:
            record, dag, parents = self.snapshot(txn, b"reuse", b"recorded-scale-reuse-v1")
            self.assertEqual(parents, (plan, result))
            _, root, bindings = view(txn, core.REC_DAG, dag)
            self.assertEqual(bindings, 2)
            self.assertEqual(root, core.txn_lookup_node(txn, dag, b"plan_ref"))
            self.assertEqual(self.literal_value(txn, root, core.DATUM_STRING), plan_pin.decode("ascii"))
            result_node = core.txn_lookup_node(txn, dag, b"result_ref")
            self.assertEqual(self.literal_value(txn, result_node, core.DATUM_STRING), "history")
            self.assert_missing_ref(txn, plan_pin)
            for ref, expected in ((b"main", result), (b"history", result), (b"staged", alternate)):
                self.assertEqual(core.txn_ref_get(txn, ref), expected)
        report = {"commit": record.hex(), "publication_mode": "reuse", "plan_ref": plan_pin.decode("ascii"),
                  "plan_commit": plan.hex(), "result_ref": "history", "result_commit": result.hex(),
                  "request_commit": request.hex(), "expected_main": previous.hex()}
        self.assertEqual(self.example["inspect"](self.repo), stored)
        self.assertEqual(self.example["inspect"](self.repo, b"reuse"), report)

        replacement = self.example["record_sum"](self.repo, b"replacement", 6, 0)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            # Historical names can now refer to unrelated objects. No ref but
            # reuse reaches either parent, or the plan's captured old main.
            for ref in (b"main", b"history"):
                core.txn_ref_update(txn, ref, replacement)
            core.txn_ref_create(txn, plan_pin, replacement)
            core.txn_ref_delete_expected(txn, b"staged", alternate)
            core.txn_ref_delete_expected(txn, b"producer", producer)
            core.txn_commit(txn)
        self.assertGreater(self.example["collect"](self.repo), 0)
        self.assertEqual(self.example["inspect"](self.repo, b"reuse"), report)
        with transaction(self.repo) as txn:
            for commit in (plan, result, previous, request, producer):
                view(txn, core.REC_COMMIT, commit)
            with self.assertRaises(core.Error) as swept:
                view(txn, core.REC_COMMIT, alternate)
            self.assertEqual(swept.exception.args[0], "not_found")

    def test_publish_reused_scale_rejects_occupied_ref_even_with_exact_intent(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        plan = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, _, (request,) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            result = put_requested_result(txn, request, sum_dag, 3, 36)
            core.txn_ref_create(txn, b"history", result)
            core.txn_ref_create(txn, b"reuse", producer)
            core.txn_commit(txn)
        publish = self.example["publish_reused_scale"]
        selection = (self.repo, b"plan", plan, b"history", result, b"reuse")
        data = self.repo / "data.mdb"

        def reject_occupied(target):
            before = data.read_bytes()
            with self.assertRaisesRegex(core.Error, "ref already exists"):
                publish(*selection)
            self.assertEqual(data.read_bytes(), before)
            with transaction(self.repo) as txn:
                self.assert_missing_ref(txn, b"main")
                for pin, expected in ((b"plan", plan), (b"history", result), (b"reuse", target)):
                    self.assertEqual(core.txn_ref_get(txn, pin), expected)

        reject_occupied(producer)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_delete_expected(txn, b"reuse", producer)
            core.txn_commit(txn)
        self.assertEqual(publish(*selection), result)
        self.assertIsNone(self.example["inspect"](self.repo, b"reuse")["expected_main"])
        with transaction(self.repo, core.TXN_WRITE) as txn:
            record = core.txn_ref_get(txn, b"reuse")
            self.assert_missing_ref(txn, b"plan")
            self.assertEqual(core.txn_ref_get(txn, b"history"), result)
            # Restore both guards so only occupancy of the identical record
            # can cause the next request to fail; it is not a retry key.
            core.txn_ref_delete_expected(txn, b"main", result)
            core.txn_ref_create(txn, b"plan", plan)
            core.txn_commit(txn)
        reject_occupied(record)

    def test_inspect_rejects_malformed_reuse_record_and_inconsistent_result(self):
        producer, _, plan, result = self.prepare_receipted_scale()
        self.example["request_scale"](self.repo, b"producer", producer, b"other-plan", 4)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, _, (wrong_request, _) = self.snapshot(txn, b"other-plan", b"scale-plan-v1")
            other_result = put_requested_result(txn, wrong_request, sum_dag, 4, 48)
            plan_node = literal(txn, core.DATUM_STRING, b"plan")
            result_node = literal(txn, core.DATUM_STRING, b"returned")
            main_node = literal(txn, core.DATUM_STRING, b"main")
            invalid_node = literal(txn, core.DATUM_STRING, b"invalid/name")
            number_node = literal(txn, core.DATUM_I64, 7)
            fields = (b"plan_ref", plan_node, b"result_ref", result_node)
            good = put(txn, core.REC_DAG, plan_node, *fields)
            cases = {
                b"reversed-parents": (good, (result, plan)),
                b"missing-parent": (good, (plan,)),
                b"wrong-request": (good, (plan, other_result)),
                b"wrong-dag-root": (put(txn, core.REC_DAG, result_node, *fields), (plan, result)),
                b"extra-binding": (put(txn, core.REC_DAG, plan_node, *fields, b"extra", number_node), (plan, result)),
            }
            for name, value in ((b"invalid-name", invalid_node), (b"main-alias", main_node),
                                (b"plan-alias", plan_node), (b"wrong-type", number_node)):
                dag = put(txn, core.REC_DAG, plan_node, b"plan_ref", plan_node, b"result_ref", value)
                cases[name] = (dag, (plan, result))
            for name, (dag, parents) in cases.items():
                tree = put(txn, core.REC_TREE, b"recorded-scale-reuse-v1", dag)
                core.txn_ref_create(txn, name, put(txn, core.REC_COMMIT, tree, *parents))
            core.txn_commit(txn)
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for name in cases:
            with self.subTest(record=name):
                with self.assertRaises(ValueError):
                    self.example["inspect"](self.repo, name)
                self.assertEqual(data.read_bytes(), before)

    def test_retained_selection_transfers_without_the_origin_plan_and_publishes_without_result_pin(self):
        producer, previous, plan, result = self.prepare_receipted_scale()
        with transaction(self.repo, core.TXN_WRITE) as txn:
            # Make main stale before recording the choice, and leave the old tip reachable only by the plan.
            core.txn_ref_update(txn, b"main", producer)
            _, _, (request, _) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            core.txn_commit(txn)
        choose = self.example["select_scale_result"]
        selection = choose(self.repo, b"plan", plan, b"returned", result, b"selection")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            actual, dag, parents = self.snapshot(txn, b"selection", b"scale-result-selection-v1")
            self.assertEqual((actual, parents), (selection, (request, result)))
            _, root, count = view(txn, core.REC_DAG, dag)
            self.assertEqual(count, 1)
            self.assertEqual(root, core.txn_lookup_node(txn, dag, b"result_ref"))
            self.assertEqual(self.literal_value(txn, root, core.DATUM_STRING), "returned")
            self.assertEqual(core.txn_ref_get(txn, b"main"), producer)
            core.txn_ref_delete_expected(txn, b"plan", plan)
            core.txn_ref_delete_expected(txn, b"returned", result)
            core.txn_ref_delete_expected(txn, b"producer", producer)
            core.txn_ref_delete_expected(txn, b"main", producer)
            core.txn_commit(txn)
        self.assertGreater(self.example["collect"](self.repo), 0)
        with transaction(self.repo) as txn:
            for swept in (plan, previous):
                with self.assertRaises(core.Error) as error:
                    view(txn, core.REC_COMMIT, swept)
                self.assertEqual(error.exception.args[0], "not_found")
        bundle = self.workspace / "selection.dmlb"
        repo = core.repo_open(self.repo, False)
        try:
            bundle.write_bytes(core.repo_export_commit(repo, selection))
        finally:
            core.repo_close(repo)
        destination = self.workspace / "destination"
        self.assertEqual(self.example["stage_input"](destination, b"imported", bundle), selection)
        inspect = self.example["inspect"]
        self.assertEqual(inspect(destination, b"imported"), {
            "commit": selection.hex(), "request_commit": request.hex(), "request_implementation": "example.scale@1",
            "result_commit": result.hex(), "result_ref": "returned",
        })
        with transaction(destination, core.TXN_WRITE) as txn:
            core.txn_ref_create(txn, b"producer", producer)
            core.txn_commit(txn)
        new_plan = self.example["request_scale"](destination, b"producer", producer, b"new-plan", 3)
        self.assertNotEqual(new_plan, plan)
        publish = self.example["publish_selected_scale"]
        args = (destination, b"new-plan", new_plan, b"imported", selection, b"returned")
        self.assertEqual(publish(*args), result)
        with transaction(destination, core.TXN_WRITE) as txn:
            proof, _, parents = self.snapshot(txn, b"returned", b"recorded-selected-scale-reuse-v1")
            self.assertEqual(parents, (new_plan, selection))
            self.assert_missing_ref(txn, b"new-plan")
            core.txn_ref_delete_expected(txn, b"main", result)
            core.txn_ref_create(txn, b"new-plan", new_plan)
            core.txn_commit(txn)
        data = destination / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            publish(*args)  # The exact reuse record is occupied, not a receipt.
        self.assertEqual(data.read_bytes(), before)
        with transaction(destination, core.TXN_WRITE) as txn:
            core.txn_ref_delete_expected(txn, b"new-plan", new_plan)
            core.txn_ref_delete_expected(txn, b"imported", selection)
            core.txn_ref_delete_expected(txn, b"producer", producer)
            core.txn_commit(txn)
        self.example["collect"](destination)
        self.assertEqual(inspect(destination, b"returned"), {
            "commit": proof.hex(), "publication_mode": "reuse", "plan_ref": "new-plan",
            "plan_commit": new_plan.hex(), "selection_ref": "imported", "selection_commit": selection.hex(),
            "result_commit": result.hex(), "request_commit": request.hex(), "expected_main": None,
        })

    def test_selection_reader_and_publication_revalidate_raw_selection_parents_and_layout(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        version = b"example.scale@2"
        plan = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3, implementation=version)
        self.example["request_scale"](self.repo, b"producer", producer, b"other-plan", 4, implementation=version)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, _, (request,) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            _, _, (other_request,) = self.snapshot(txn, b"other-plan", b"scale-plan-v1")
            result = put_requested_result(txn, request, sum_dag, 3, 36, implementation=version)
            wrong_version = put_requested_result(txn, request, sum_dag, 3, 36)
            wrong_parent = put_requested_result(txn, other_request, sum_dag, 3, 36, implementation=version)
            name = literal(txn, core.DATUM_STRING, b"history")
            main = literal(txn, core.DATUM_STRING, b"main")
            number = literal(txn, core.DATUM_I64, 7)
            field = (b"result_ref", name)
            good_dag = put(txn, core.REC_DAG, name, *field)
            cases = (
                (b"bad-version", good_dag, (request, wrong_version), "expected recorded implementation"),
                (b"bad-request", good_dag, (request, wrong_parent), "result does not retain the expected request commit"),
                (b"reversed", good_dag, (result, request), "expected a scale-request-v1|selection does not retain"),
                (b"missing-parent", good_dag, (request,), "ordered request and result parents"),
                (b"bad-root", put(txn, core.REC_DAG, number, *field), (request, result), "wrong DAG layout"),
                (b"bad-name", put(txn, core.REC_DAG, main, b"result_ref", main), (request, result), "invalid result ref"),
                (b"bad-type", put(txn, core.REC_DAG, number, b"result_ref", number),
                 (request, result), "wrong datum kind"),
            )
            invalid = []
            for ref, dag, parents, error in cases:
                tree = put(txn, core.REC_TREE, b"scale-result-selection-v1", dag)
                selection = put(txn, core.REC_COMMIT, tree, *parents)
                core.txn_ref_create(txn, ref, selection)
                invalid.append((ref, selection, error))
            core.txn_ref_create(txn, b"history", wrong_version)
            core.txn_commit(txn)
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "expected recorded implementation example.scale@2"):
            self.example["select_scale_result"](self.repo, b"plan", plan, b"history", wrong_version, b"choice")
        self.assertEqual(data.read_bytes(), before)
        for ref, selection, error in invalid:
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(ValueError, error):
                    self.example["inspect"](self.repo, ref)
                with self.assertRaisesRegex(ValueError, error):
                    self.example["publish_selected_scale"](self.repo, b"plan", plan, ref, selection, b"reuse")
                self.assertEqual(data.read_bytes(), before)

    def test_request_or_worker_failure_does_not_leave_partial_state(self):
        producer = self.expect_success("record-sum", "producer", 2, 0).strip()
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for pin, factor, reason in (
            ("main", 3, "plan ref must differ from main"),
            ("plan", 1 << 63, "signed 64-bit"),
        ):
            with self.subTest(pin=pin):
                self.assertIn(reason, self.expect_failure("request-scale", "producer", producer, pin, factor))
                self.assertEqual(data.read_bytes(), before)
        plan = self.expect_success("request-scale", "producer", producer, "plan", 1 << 62).strip()
        before = data.read_bytes()
        self.expect_failure("request-scale", "producer", producer, "plan", 3)
        self.assertEqual(data.read_bytes(), before)
        worker = self.workspace / "worker"
        bundle = self.workspace / "request.dmlb"
        request = self.expect_success("export-request", "plan", plan, bundle).strip()
        self.expect_failure("export-request", "producer", plan, self.workspace / "wrong.dmlb")
        self.assertFalse((self.workspace / "wrong.dmlb").exists())
        self.expect_success("stage-input", "main", bundle)
        before = data.read_bytes()
        self.assertIn("main already points to this request",
                      self.expect_failure("request-scale", "producer", producer, "second-plan", 1 << 62))
        self.assertEqual(data.read_bytes(), before)
        self.expect_success("stage-input", "incoming", bundle, repo=worker)
        worker_data = worker / "data.mdb"
        before = worker_data.read_bytes()
        self.assertIn("example.scale@1 result", self.expect_failure("work-scale", "incoming", request, "result",
                                                                    repo=worker))
        self.assertEqual(worker_data.read_bytes(), before)
        with transaction(worker) as txn:
            self.assert_missing_ref(txn, b"result")
            self.assertEqual(core.txn_ref_get(txn, b"incoming").hex(), request)

    def test_worker_rejects_an_imported_request_for_an_unsupported_implementation(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        # Build a structurally valid portable record that local planning would reject.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            version = literal(txn, core.DATUM_STRING, b"example.scale@3")
            factor = literal(txn, core.DATUM_I64, 3)
            dag = put(txn, core.REC_DAG, version, b"implementation", version, b"factor", factor)
            tree = put(txn, core.REC_TREE, b"scale-request-v1", dag)
            request = put(txn, core.REC_COMMIT, tree, producer)
            core.txn_ref_create(txn, b"portable", request)
            core.txn_commit(txn)
        bundle = self.workspace / "future-request.dmlb"
        repo = core.repo_open(self.repo, False)
        try:
            bundle.write_bytes(core.repo_export_commit(repo, request))
        finally:
            core.repo_close(repo)

        worker = self.workspace / "worker"
        self.assertEqual(self.expect_success("stage-input", "incoming", bundle, repo=worker).strip(), request.hex())
        data = worker / "data.mdb"
        before = data.read_bytes()
        self.assertIn("unsupported scale implementation",
                      self.expect_failure("work-scale", "incoming", request.hex(), "result", repo=worker))
        self.assertEqual(data.read_bytes(), before)
        with transaction(worker) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"incoming"), request)
            self.assert_missing_ref(txn, b"result")

    def prepare_receipted_scale(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        previous = self.example["record_sum"](self.repo, b"main", 12, 0)
        plan = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3)
        worker = self.workspace / "worker"
        outbound = self.workspace / "request.dmlb"
        inbound = self.workspace / "result.dmlb"
        request = self.example["export_request"](self.repo, b"plan", plan, outbound)
        self.example["stage_input"](worker, b"incoming", outbound)
        result = self.example["work_scale"](worker, b"incoming", request, b"result")
        self.example["export_scale"](worker, b"result", result, inbound)
        self.example["stage_input"](self.repo, b"returned", inbound)
        return producer, previous, plan, result

    def test_abandon_releases_only_selected_pin_when_main_has_moved_and_result_is_staged(self):
        producer, previous, plan, result = self.prepare_receipted_scale()
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", producer)
            core.txn_ref_create(txn, b"other-plan", plan)
            core.txn_commit(txn)

        worker_data = self.workspace / "worker" / "data.mdb"
        worker_before = worker_data.read_bytes()
        abandon = ("abandon-scale-request", "plan", plan.hex())
        self.assertEqual(self.expect_success(*abandon).strip(), plan.hex())
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        self.assertIn("not_found", self.expect_failure(*abandon))
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assert_missing_ref(txn, b"plan")
            for name, commit in ((b"other-plan", plan), (b"main", producer),
                                 (b"producer", producer), (b"returned", result)):
                self.assertEqual(core.txn_ref_get(txn, name), commit)

        # Even with a ready result and the captured main restored, the missing
        # pin prevents publication. An alias of the same plan cannot substitute.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", previous)
            core.txn_commit(txn)
        before = data.read_bytes()
        self.assertIn("not_found", self.expect_failure("publish-requested-scale", "plan", plan.hex(),
                                                      "returned", result.hex(), "--receipt-ref", "ack"))
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assert_missing_ref(txn, b"ack")
            self.assertEqual(core.txn_ref_get(txn, b"main"), previous)

        # Once the independent roots are gone, no abandonment record keeps
        # the private plan or captured main alive; staging still owns its result.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", producer)
            core.txn_ref_delete_expected(txn, b"other-plan", plan)
            core.txn_commit(txn)
        self.assertGreater(self.example["collect"](self.repo), 0)
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"returned"), result)
            for commit in (plan, previous):
                with self.assertRaises(core.Error) as collected:
                    view(txn, core.REC_COMMIT, commit)
                self.assertEqual(collected.exception.args[0], "not_found")
        self.assertEqual(worker_data.read_bytes(), worker_before)

    def test_abandon_leaves_collection_explicit_without_a_main_or_staged_result(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        pin = b"1" + b"a" * 124 + b"._-"
        plan = self.example["request_scale"](self.repo, b"producer", producer, pin, 3)
        request = bytes.fromhex(self.example["inspect"](self.repo, pin)["request_commit"])
        self.assertEqual(self.example["abandon_scale_request"](self.repo, pin, plan), plan)
        with transaction(self.repo) as txn:
            self.assert_missing_ref(txn, pin)
            self.assert_missing_ref(txn, b"main")
            self.assertEqual(core.txn_ref_get(txn, b"producer"), producer)
            for commit in (plan, request):
                view(txn, core.REC_COMMIT, commit)
        self.assertGreater(self.example["collect"](self.repo), 0)
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"producer"), producer)
            for commit in (plan, request):
                with self.assertRaises(core.Error) as collected:
                    view(txn, core.REC_COMMIT, commit)
                self.assertEqual(collected.exception.args[0], "not_found")

    def test_abandon_rejects_replaced_pin_main_and_malformed_plan_without_writes(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        original = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3)
        replacement = self.example["request_scale"](self.repo, b"producer", producer, b"other-plan", 4)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"plan", replacement)
            core.txn_ref_create(txn, b"main", original)
            _, original_tree, _ = view(txn, core.REC_COMMIT, original)
            replacement_view, _, _ = view(txn, core.REC_COMMIT, replacement)
            # Correct tag and parent count, but the request's DAG differs from the plan's.
            malformed = put(txn, core.REC_COMMIT, original_tree, core.object_view_parent(replacement_view, 0))
            core.txn_ref_create(txn, b"malformed", malformed)
            core.txn_commit(txn)

        data = self.repo / "data.mdb"
        before = data.read_bytes()
        abandon = self.example["abandon_scale_request"]
        for pin, commit, reason in (
            (b"plan", original, "expected plan commit"),
            (b"main", original, "plan ref must differ from main"),
            (b"producer", producer, "expected a scale-plan-v1 commit"),
            (b"malformed", malformed, "plan DAG does not match"),
        ):
            with self.subTest(pin=pin):
                with self.assertRaisesRegex(ValueError, reason):
                    abandon(self.repo, pin, commit)
                self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            for pin, commit in ((b"plan", replacement), (b"main", original),
                                (b"producer", producer), (b"malformed", malformed)):
                self.assertEqual(core.txn_ref_get(txn, pin), commit)

    def test_abandon_validates_selection_before_opening_repository(self):
        class BytesSubclass(bytes):
            pass

        class UnopenablePath:
            def __fspath__(self):
                raise AssertionError("invalid selections must be rejected before opening the repository")

        abandon = self.example["abandon_scale_request"]
        identifier = bytes(16)
        invalid_pins = ("plan", bytearray(b"plan"), BytesSubclass(b"plan"), b"", b"-plan", b"plan/name",
                        b"pl\xc3\xa1n", b"plan\n", b"p" * 129, b"main")
        for pin in invalid_pins:
            with self.subTest(pin=pin), self.assertRaisesRegex(ValueError, "plan ref.*(bytes|main)"):
                abandon(UnopenablePath(), pin, identifier)
        for commit in (identifier.hex(), bytearray(identifier), BytesSubclass(identifier), b"x" * 15, b"x" * 17):
            with self.subTest(commit=commit), self.assertRaisesRegex(ValueError, "plan commit.*16-byte ID"):
                abandon(UnopenablePath(), b"plan", commit)

    def test_receipt_retries_without_changes_after_ref_reuse_and_collection(self):
        producer_id, previous_id, plan_id, result_id = self.prepare_receipted_scale()
        plan, result = plan_id.hex(), result_id.hex()
        publish = ("publish-requested-scale", "plan", plan, "returned", result, "--receipt-ref", "ack")
        self.assertEqual(self.expect_success(*publish).strip(), result)
        fields = {"plan_ref": "plan", "plan_commit": plan, "staging_ref": "returned", "result_commit": result}
        with transaction(self.repo) as txn:
            receipt, dag, parents = self.snapshot(txn, b"ack", b"scale-publication-v1")
            self.assertEqual(parents, ())
            _, root, bindings = view(txn, core.REC_DAG, dag)
            self.assertEqual(bindings, len(fields))
            self.assertEqual(root, core.txn_lookup_node(txn, dag, b"result_commit"))
            for name, value in fields.items():
                node = core.txn_lookup_node(txn, dag, name.encode("ascii"))
                self.assertEqual(self.literal_value(txn, node, core.DATUM_STRING), value)
            self.assertEqual(core.txn_ref_get(txn, b"main"), result_id)
            self.assert_missing_ref(txn, b"plan")
            self.assert_missing_ref(txn, b"returned")
        report = {"commit": receipt.hex(), **fields}
        data = self.repo / "data.mdb"

        def assert_retry_unchanged():
            before = data.read_bytes()
            retry = self.example["publish_requested_scale"]
            self.assertEqual(retry(self.repo, b"plan", plan_id, b"returned", result_id, receipt_ref=b"ack"),
                             result_id)
            self.assertEqual(data.read_bytes(), before)
            self.assertEqual(self.example["inspect"](self.repo, b"ack"), report)
            self.assertEqual(data.read_bytes(), before)

        assert_retry_unchanged()
        # All first-publication guards now pass again, but the old attempt may not republish.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", previous_id)
            core.txn_ref_create(txn, b"plan", plan_id)
            core.txn_ref_create(txn, b"returned", result_id)
            core.txn_commit(txn)
        assert_retry_unchanged()
        # Unrelated new targets use the old names. The receipt retains no old history.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            for ref in (b"main", b"plan", b"returned"):
                core.txn_ref_update(txn, ref, producer_id)
            core.txn_commit(txn)
        self.assertGreater(self.example["collect"](self.repo), 0)
        with transaction(self.repo) as txn:
            for commit in (previous_id, plan_id, result_id):
                with self.assertRaises(core.Error) as swept:
                    core.txn_get_object(txn, core.REC_COMMIT, commit)
                self.assertEqual(swept.exception.args[0], "not_found")

        # Keep a fresh-process retry and JSON inspection after the referenced commits are gone.
        before = data.read_bytes()
        self.assertEqual(self.expect_success(*publish).strip(), result)
        self.assertEqual(data.read_bytes(), before)
        self.assertEqual(json.loads(self.expect_success("inspect", "ack")), report)
        self.assertEqual(data.read_bytes(), before)

    def test_receipt_key_rejects_each_changed_field_even_when_new_publication_is_ready(self):
        producer_id, previous_id, plan_id, result_id = self.prepare_receipted_scale()

        def publish(plan_ref, proposed_plan, staging_ref, proposed_result, receipt=b"ack"):
            return self.example["publish_requested_scale"](
                self.repo, plan_ref, proposed_plan, staging_ref, proposed_result, receipt_ref=receipt)

        self.assertEqual(publish(b"plan", plan_id, b"returned", result_id), result_id)
        data = self.repo / "data.mdb"

        def reject(*selection):
            before = data.read_bytes()
            with self.assertRaisesRegex(ValueError, "receipt does not match"):
                publish(*selection)
            self.assertEqual(data.read_bytes(), before)

        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", previous_id)
            for ref, commit in ((b"plan", plan_id), (b"other-plan", plan_id),
                                (b"returned", result_id), (b"other-returned", result_id)):
                core.txn_ref_create(txn, ref, commit)
            core.txn_commit(txn)
        reject(b"other-plan", plan_id, b"returned", result_id)
        reject(b"plan", plan_id, b"other-returned", result_id)

        with transaction(self.repo, core.TXN_WRITE) as txn:
            # Both results satisfy the original request; only their stored output differs.
            commit_view, tree, _ = view(txn, core.REC_COMMIT, result_id)
            request = core.object_view_parent(commit_view, 0)
            tree_view, _, _ = view(txn, core.REC_TREE, tree)
            dag, entry = core.object_view_entry(tree_view, 0)
            arguments = (b"implementation", b"input", b"factor")
            bindings = [field for name in arguments for field in (name, core.txn_lookup_node(txn, dag, name))]
            new_dag = put(txn, core.REC_DAG, literal(txn, core.DATUM_I64, 99), *bindings)
            new_tree = put(txn, core.REC_TREE, entry, new_dag)
            other_result = put(txn, core.REC_COMMIT, new_tree, request)
            core.txn_ref_update(txn, b"returned", other_result)
            core.txn_commit(txn)
        reject(b"plan", plan_id, b"returned", other_result)

        with transaction(self.repo, core.TXN_WRITE) as txn:
            # Recapture a different main, but keep the producer and factor (hence request) exact.
            core.txn_ref_update(txn, b"main", producer_id)
            core.txn_ref_delete_expected(txn, b"plan", plan_id)
            core.txn_ref_update(txn, b"returned", result_id)
            core.txn_commit(txn)
        other_plan = self.example["request_scale"](self.repo, b"producer", producer_id, b"plan", 3)
        self.assertNotEqual(other_plan, plan_id)
        reject(b"plan", other_plan, b"returned", result_id)
        # This plan and result are ready under a fresh key, including a maximum-length name.
        fresh = b"1" + b"a" * 124 + b"._-"
        selection = (b"plan", other_plan, b"returned", result_id, fresh)
        self.assertEqual(publish(*selection), result_id)
        after = data.read_bytes()
        self.assertEqual(publish(*selection), result_id)
        self.assertEqual(data.read_bytes(), after)
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"other-plan"), plan_id)
            self.assertEqual(core.txn_ref_get(txn, b"other-returned"), result_id)

    def test_receipt_aliases_and_occupied_key_reject_without_writes(self):
        producer, _, plan, result = self.prepare_receipted_scale()
        data = self.repo / "data.mdb"

        def publish(receipt):
            return self.example["publish_requested_scale"](
                self.repo, b"plan", plan, b"returned", result, receipt_ref=receipt)

        before = data.read_bytes()
        for alias in (b"main", b"plan", b"returned"):
            with self.subTest(alias=alias):
                with self.assertRaisesRegex(ValueError, "distinct"):
                    publish(alias)
                self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_create(txn, b"not-receipt", producer)
            nodes = {name: literal(txn, core.DATUM_STRING, value) for name, value in (
                (b"plan_ref", b"plan"), (b"plan_commit", plan.hex().encode("ascii")),
                (b"staging_ref", b"returned"), (b"result_commit", result.hex().encode("ascii")),
            )}
            # Exact matching fields, but the wrong binding is the root.
            operands = [field for binding in nodes.items() for field in binding]
            dag = put(txn, core.REC_DAG, nodes[b"plan_commit"], *operands)
            tree = put(txn, core.REC_TREE, b"scale-publication-v1", dag)
            core.txn_ref_create(txn, b"bad-receipt", put(txn, core.REC_COMMIT, tree))
            core.txn_commit(txn)
        before = data.read_bytes()
        for occupied, reason in ((b"not-receipt", "expected a parentless"),
                                 (b"bad-receipt", "wrong DAG layout")):
            with self.subTest(occupied=occupied):
                with self.assertRaisesRegex(ValueError, reason):
                    publish(occupied)
                self.assertEqual(data.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "wrong DAG layout"):
            self.example["inspect"](self.repo, b"bad-receipt")
        self.assertEqual(data.read_bytes(), before)

    def test_failed_receipted_publication_does_not_reserve_key_or_infer_success_from_main(self):
        producer, previous, plan, result = self.prepare_receipted_scale()
        data = self.repo / "data.mdb"

        def publish():
            return self.example["publish_requested_scale"](
                self.repo, b"plan", plan, b"returned", result, receipt_ref=b"ack")

        def reject(error, reason):
            before = data.read_bytes()
            with self.assertRaisesRegex(error, reason):
                publish()
            self.assertEqual(data.read_bytes(), before)
            with transaction(self.repo) as txn:
                self.assert_missing_ref(txn, b"ack")

        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"returned", producer)
            core.txn_commit(txn)
        reject(core.Error, "ref target differs")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"returned", result)
            core.txn_ref_update(txn, b"main", result)
            core.txn_commit(txn)
        reject(ValueError, "main does not point to the expected commit")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_update(txn, b"main", previous)
            core.txn_commit(txn)
        self.assertEqual(publish(), result)

    def test_receipted_publication_validates_ref_names_before_opening_repository(self):
        class BytesSubclass(bytes):
            pass

        class UnopenablePath:
            def __fspath__(self):
                raise AssertionError("invalid ref names must be rejected before opening the repository")

        publish = self.example["publish_requested_scale"]
        identifier = bytes(16)
        invalid_types = ("ref", bytearray(b"ref"), BytesSubclass(b"ref"))
        invalid_names = (b"", b"-ref", b".ref", b"_ref", b"ref/name", b"r\xc3\xa9f", b"ref\n", b"x" * 129)
        for index, label in enumerate(("plan", "staging", "receipt")):
            for invalid in (*invalid_types, *invalid_names):
                names = [b"plan", b"returned", b"ack"]
                names[index] = invalid
                diagnostic = f"{label} ref.*valid ASCII ref name" if type(invalid) is bytes else "ref.*bytes"
                with self.subTest(ref=label, invalid=repr(invalid)), self.assertRaisesRegex(ValueError, diagnostic):
                    plan, stage, receipt = names
                    publish(UnopenablePath(), plan, identifier, stage, identifier, receipt_ref=receipt)

    def test_publish_validates_arguments_before_opening_the_repository(self):
        class BytesSubclass(bytes):
            pass

        class IntSubclass(int):
            pass

        publish = runpy.run_path(EXAMPLE)["publish_scale"]
        identifier = bytes(16)
        for arguments, diagnostic in (
            ((BytesSubclass(b"main"), identifier, identifier, 3, None), "staging ref must be bytes"),
            ((b"returned", BytesSubclass(identifier), identifier, 3, None), "result commit must be a 16-byte ID"),
            ((b"returned", identifier, BytesSubclass(identifier), 3, None), "producer commit must be a 16-byte ID"),
            ((b"returned", identifier, identifier, 3, BytesSubclass(identifier)),
             "expected main commit must be a 16-byte ID"),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(ValueError, diagnostic):
                publish(self.repo, *arguments)
        for factor in (True, IntSubclass(3), "3", -(1 << 63) - 1, 1 << 63):
            with self.subTest(factor=factor), self.assertRaisesRegex(ValueError, "expected factor.*signed 64-bit"):
                publish(self.repo, b"returned", identifier, identifier, factor, None)
        self.assertFalse(self.repo.exists())

    def test_scale_rejects_unknown_sum_version_even_with_matching_pin_and_tree_entry(self):
        commit, _, _ = self.publish_sum_fixture(b"example.sum@2")
        data_path = self.repo / "data.mdb"
        before = data_path.read_bytes()
        diagnostic = self.expect_failure("record-scale", "producer", commit.hex(), "main", 3)
        self.assertIn("expected recorded implementation example.sum@1", diagnostic)
        self.assertEqual(data_path.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"producer"), commit)
            self.assert_missing_ref(txn, b"main")

    def test_inspect_rejects_mismatched_parent_even_when_the_sum_roots_match(self):
        expected = self.expect_success("record-sum", "producer", 7, 5).strip()
        decoy = self.expect_success("record-sum", "decoy", 9, 3).strip()
        self.expect_success("record-scale", "producer", expected, "main", 3)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            consumer = core.txn_ref_get(txn, b"main")
            _, tree, _ = view(txn, core.REC_COMMIT, consumer)
            _, first_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, second_dag, _ = self.snapshot(txn, b"decoy", b"recorded-sum-v1")
            self.assertNotEqual(first_dag, second_dag)
            self.assertEqual(view(txn, core.REC_DAG, first_dag)[1], view(txn, core.REC_DAG, second_dag)[1])
            forged = put(txn, core.REC_COMMIT, tree, bytes.fromhex(decoy))
            core.txn_ref_create(txn, b"mismatch", forged)
            core.txn_commit(txn)

        data_path = self.repo / "data.mdb"
        before = data_path.read_bytes()
        bundle = self.workspace / "mismatch.dmlb"
        for command, args in (
            ("inspect", ("mismatch",)),
            ("export-scale", ("mismatch", forged.hex(), bundle)),
            ("publish-scale", ("mismatch", forged.hex(), decoy, 3, consumer.hex())),
        ):
            with self.subTest(command=command):
                self.assertIn("does not match the producer parent", self.expect_failure(command, *args))
                self.assertEqual(data_path.read_bytes(), before)
                self.assertFalse(bundle.exists())

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
