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


class RecordedCallsTest(unittest.TestCase):
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

        report = self.expect_success("publish-scale", "returned", result.hex(), producer.hex(), "-")
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
            self.assertIn(reason, self.expect_failure("publish-scale", pin, result, producer, expected_main))
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

    def test_publish_checks_plain_byte_arguments_before_opening_the_repository(self):
        class BytesSubclass(bytes):
            pass

        publish = runpy.run_path(EXAMPLE)["publish_scale"]
        identifier = bytes(16)
        for arguments, diagnostic in (
            ((BytesSubclass(b"main"), identifier, identifier, None), "staging ref must be bytes"),
            ((b"returned", BytesSubclass(identifier), identifier, None), "result commit must be a 16-byte ID"),
            ((b"returned", identifier, BytesSubclass(identifier), None), "producer commit must be a 16-byte ID"),
            ((b"returned", identifier, identifier, BytesSubclass(identifier)), "expected main commit must be a 16-byte ID"),
        ):
            with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(ValueError, diagnostic):
                publish(self.repo, *arguments)
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
            ("publish-scale", ("mismatch", forged.hex(), decoy, consumer.hex())),
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
