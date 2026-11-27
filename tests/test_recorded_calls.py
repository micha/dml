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
ATTEMPT_A = b"a0000000-0000-4000-8000-000000000001"
ATTEMPT_B = b"b0000000-0000-4000-8000-000000000002"


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

    def test_attempt_edges_keep_one_of_two_executions_of_the_same_result(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        plan = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, _, (request,) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            core.txn_ref_create(txn, b"incoming", request)
            core.txn_commit(txn)

        work = self.example["work_scale_attempt"]
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            work(self.repo, b"incoming", request, b"producer", ATTEMPT_A)
        self.assertEqual(data.read_bytes(), before)
        result = self.example["work_scale"](self.repo, b"incoming", request, b"legacy-result")
        first = work(self.repo, b"incoming", request, b"first", ATTEMPT_A)
        second = work(self.repo, b"incoming", request, b"second", ATTEMPT_B)
        duplicate = work(self.repo, b"incoming", request, b"duplicate", ATTEMPT_A)
        self.assertNotEqual(first, second)
        self.assertEqual(first, duplicate)
        select = self.example["select_scale_attempt"]
        selection = select(self.repo, b"plan", plan, b"first", first, b"chosen")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            for pin, attempt, label in ((b"first", first, ATTEMPT_A), (b"second", second, ATTEMPT_B)):
                actual, dag, parents = self.snapshot(txn, pin, b"scale-attempt-v1")
                self.assertEqual((actual, parents), (attempt, (request, result)))
                _, root, count = view(txn, core.REC_DAG, dag)
                self.assertEqual((count, root), (1, core.txn_lookup_node(txn, dag, b"attempt_id")))
                self.assertEqual(self.literal_value(txn, root, core.DATUM_STRING), label.decode("ascii"))
            actual, dag, parents = self.snapshot(txn, b"chosen", b"scale-attempt-selection-v1")
            self.assertEqual((actual, parents), (selection, (request, first)))
            _, root, count = view(txn, core.REC_DAG, dag)
            self.assertEqual((count, root), (1, core.txn_lookup_node(txn, dag, b"attempt_ref")))
            self.assertEqual(self.literal_value(txn, root, core.DATUM_STRING), "first")
            self.assertEqual(core.txn_ref_get(txn, b"plan"), plan)
            self.assert_missing_ref(txn, b"main")
            for pin, expected in ((b"first", first), (b"second", second), (b"duplicate", duplicate),
                                  (b"legacy-result", result), (b"incoming", request)):
                core.txn_ref_delete_expected(txn, pin, expected)
            core.txn_commit(txn)

        self.assertGreater(self.example["collect"](self.repo), 0)
        with transaction(self.repo) as txn:
            with self.assertRaisesRegex(core.Error, "not_found"):
                view(txn, core.REC_COMMIT, second)
            for commit in (first, request, result):
                core.txn_get_object(txn, core.REC_COMMIT, commit)
        publish = self.example["publish_selected_scale"]
        self.assertEqual(publish(self.repo, b"plan", plan, b"chosen", selection, b"reuse"), result)
        self.assertEqual(self.example["collect"](self.repo), 0)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            reuse, _, parents = self.snapshot(txn, b"reuse", b"recorded-selected-scale-reuse-v1")
            self.assertEqual(parents, (plan, selection))
            self.assertEqual(core.txn_ref_get(txn, b"main"), result)
            self.assert_missing_ref(txn, b"plan")
            core.txn_ref_delete_expected(txn, b"main", result)
            core.txn_ref_delete_expected(txn, b"chosen", selection)
            core.txn_ref_delete_expected(txn, b"producer", producer)
            core.txn_commit(txn)
        self.example["collect"](self.repo)
        self.assertEqual(self.example["inspect"](self.repo, b"reuse"), {
            "commit": reuse.hex(), "publication_mode": "reuse", "plan_ref": "plan", "plan_commit": plan.hex(),
            "selection_ref": "chosen", "selection_commit": selection.hex(), "request_commit": request.hex(),
            "result_commit": result.hex(), "attempt_commit": first.hex(), "attempt_id": ATTEMPT_A.decode("ascii"),
            "expected_main": None,
        })

    def test_attempt_selection_rechecks_nested_request_version_and_shapes(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        planner = self.example["request_scale"]
        version = b"example.scale@2"
        plan = planner(self.repo, b"producer", producer, b"plan", 3, implementation=version)
        planner(self.repo, b"producer", producer, b"other-plan", 4, implementation=version)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, sum_dag, _ = self.snapshot(txn, b"producer", b"recorded-sum-v1")
            _, _, (request,) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            _, _, (other_request,) = self.snapshot(txn, b"other-plan", b"scale-plan-v1")
            result = put_requested_result(txn, request, sum_dag, 3, 36, implementation=version)
            wrong_version = put_requested_result(txn, request, sum_dag, 3, 36)
            other_result = put_requested_result(txn, other_request, sum_dag, 4, 36, implementation=version)

            def tree_for(entry, field, value):
                node = literal(txn, core.DATUM_STRING, value)
                dag = put(txn, core.REC_DAG, node, field, node)
                return put(txn, core.REC_TREE, entry, dag)

            attempt_tree = tree_for(b"scale-attempt-v1", b"attempt_id", ATTEMPT_A)
            malformed_tree = tree_for(b"scale-attempt-v1", b"attempt_id", ATTEMPT_A.upper())
            selection_tree = tree_for(b"scale-attempt-selection-v1", b"attempt_ref", b"historical")
            invalid = []
            for name, tree, parents, reason in (
                (b"wrong-version", attempt_tree, (request, wrong_version), "expected recorded implementation"),
                (b"wrong-result", attempt_tree, (request, other_result), "result does not retain the expected request"),
                (b"wrong-request", attempt_tree, (other_request, other_result),
                 "attempt does not retain the expected request"),
                (b"wrong-count", attempt_tree, (request,), "ordered request and result parents"),
                (b"wrong-id", malformed_tree, (request, result), "canonical lowercase UUIDv4"),
            ):
                attempt = put(txn, core.REC_COMMIT, tree, *parents)
                selection = put(txn, core.REC_COMMIT, selection_tree, request, attempt)
                selection_ref = b"select-" + name
                core.txn_ref_create(txn, name, attempt)
                core.txn_ref_create(txn, selection_ref, selection)
                invalid.append((name, attempt, selection_ref, selection, reason))
            good = put(txn, core.REC_COMMIT, attempt_tree, request, result)
            malformed = tree_for(b"scale-attempt-selection-v1", b"attempt_ref", b"main")
            for pin, tree, parents, reason in (
                (b"bad-history", malformed, (request, good), "invalid attempt ref"),
                (b"not-attempt", selection_tree, (request, result), "expected a scale-attempt-v1"),
            ):
                selection = put(txn, core.REC_COMMIT, tree, *parents)
                core.txn_ref_create(txn, pin, selection)
                invalid.append((None, None, pin, selection, reason))
            core.txn_commit(txn)

        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for attempt_ref, attempt, selection_ref, selection, reason in invalid:
            with self.subTest(ref=selection_ref):
                if attempt_ref is not None:
                    with self.assertRaisesRegex(ValueError, reason):
                        self.example["select_scale_attempt"](self.repo, b"plan", plan, attempt_ref, attempt, b"new")
                with self.assertRaisesRegex(ValueError, reason):
                    self.example["inspect"](self.repo, selection_ref)
                with self.assertRaisesRegex(ValueError, reason):
                    self.example["publish_selected_scale"](self.repo, b"plan", plan, selection_ref, selection, b"reuse")
                self.assertEqual(data.read_bytes(), before)

    def prepare_adoption(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        plan = self.example["request_scale"](self.repo, b"producer", producer, b"plan", 3)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, _, (request,) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            core.txn_ref_create(txn, b"incoming", request)
            core.txn_commit(txn)
        work = self.example["work_scale_attempt"]
        first = work(self.repo, b"incoming", request, b"first", ATTEMPT_A)
        initial = self.example["select_scale_attempt"](self.repo, b"plan", plan, b"first", first, b"chosen")
        second = work(self.repo, b"incoming", request, b"second", ATTEMPT_B)
        return producer, plan, request, first, second, initial

    def test_adoption_without_plan_retains_ordered_history_and_rolls_back_on_occupied_output(self):
        producer, plan, request, first, second, initial = self.prepare_adoption()
        self.example["abandon_scale_request"](self.repo, b"plan", plan)
        adopt = self.example["adopt_scale_attempt"]
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            adopt(self.repo, b"chosen", initial, b"second", second, b"producer")
        self.assertEqual(data.read_bytes(), before)

        newer = adopt(self.repo, b"chosen", initial, b"second", second, b"changed")
        before = data.read_bytes()
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            adopt(self.repo, b"chosen", initial, b"second", second, b"changed")
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            actual, dag, parents = self.snapshot(txn, b"changed", b"scale-attempt-adoption-v1")
            self.assertEqual((actual, parents), (newer, (initial, second)))
            _, root, count = view(txn, core.REC_DAG, dag)
            self.assertEqual((count, root), (1, core.txn_lookup_node(txn, dag, b"attempt_ref")))
            self.assertEqual(self.literal_value(txn, root, core.DATUM_STRING), "second")
            self.assertEqual(core.txn_ref_get(txn, b"producer"), producer)
            self.assert_missing_ref(txn, b"plan")
            self.assert_missing_ref(txn, b"main")
            for ref, expected in ((b"first", first), (b"second", second), (b"chosen", initial),
                                  (b"incoming", request)):
                core.txn_ref_delete_expected(txn, ref, expected)
            core.txn_commit(txn)
        self.assertGreater(self.example["collect"](self.repo), 0)
        with transaction(self.repo) as txn:
            for commit in (initial, first, second):
                view(txn, core.REC_COMMIT, commit)
        report = self.example["inspect"](self.repo, b"changed")
        self.assertEqual(report["previous_selection_commit"], initial.hex())
        self.assertEqual(report["attempt_commit"], second.hex())

    def test_adoption_and_reuse_validate_the_whole_typed_version_chain(self):
        producer, plan, request, first, second, initial = self.prepare_adoption()
        # Alternate implementation deliberately computes the same scalar value.
        self.example["request_scale"](self.repo, b"producer", producer, b"other-plan", 3,
                                      implementation=b"example.scale@2")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, _, (other_request,) = self.snapshot(txn, b"other-plan", b"scale-plan-v1")
            core.txn_ref_create(txn, b"other-request", other_request)
            core.txn_commit(txn)
        other = self.example["work_scale_attempt"](self.repo, b"other-request", other_request, b"other", ATTEMPT_B)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            def named_tree(entry, field, value):
                node = literal(txn, core.DATUM_STRING, value)
                return put(txn, core.REC_TREE, entry, put(txn, core.REC_DAG, node, field, node))

            tree = named_tree(b"scale-attempt-adoption-v1", b"attempt_ref", b"historical")
            bad_tree = named_tree(b"scale-attempt-adoption-v1", b"attempt_ref", b"main")
            _, _, (_, result) = self.snapshot(txn, b"first", b"scale-attempt-v1")
            legacy_tree = named_tree(b"scale-result-selection-v1", b"result_ref", b"result")
            legacy = put(txn, core.REC_COMMIT, legacy_tree, request, result)
            core.txn_ref_create(txn, b"legacy", legacy)
            duplicate = put(txn, core.REC_COMMIT, tree, initial, first)
            wrong_request = put(txn, core.REC_COMMIT, tree, initial, other)
            bad_name = put(txn, core.REC_COMMIT, bad_tree, initial, second)
            invalid = []
            for ref, parents, reason in (
                (b"single-parent", (initial,), "ordered selection and attempt parents"),
                (b"swapped-parents", (second, initial), "expected a scale-attempt-v1"),
                (b"legacy-root", (legacy, second), "history must start with an attempt selection"),
                (b"duplicate-middle", (duplicate, second), "must change the selected attempt commit"),
                (b"other-middle", (wrong_request, second), "attempt does not retain the expected request"),
                (b"bad-name-middle", (bad_name, first), "invalid attempt ref name"),
            ):
                commit = put(txn, core.REC_COMMIT, tree, *parents)
                core.txn_ref_create(txn, ref, commit)
                invalid.append((ref, commit, reason))
            core.txn_commit(txn)

        data = self.repo / "data.mdb"
        before = data.read_bytes()
        adopt = self.example["adopt_scale_attempt"]
        for basis_ref, basis, attempt_ref, attempt, reason in (
            (b"legacy", legacy, b"second", second, "basis must be an attempt selection"),
            (b"chosen", initial, b"other", other, "attempt does not retain the expected request"),
        ):
            with self.assertRaisesRegex(ValueError, reason):
                adopt(self.repo, basis_ref, basis, attempt_ref, attempt, b"next")
            self.assertEqual(data.read_bytes(), before)
        for ref, commit, reason in invalid:
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(ValueError, reason):
                    adopt(self.repo, ref, commit, b"second", second, b"next")
                with self.assertRaisesRegex(ValueError, reason):
                    self.example["inspect"](self.repo, ref)
                with self.assertRaisesRegex(ValueError, reason):
                    self.example["publish_selected_scale"](self.repo, b"plan", plan, ref, commit, b"reuse")
                self.assertEqual(data.read_bytes(), before)

    def test_adoption_inspects_a_chain_longer_than_default_python_recursion_limit(self):
        _, _, _, first, second, initial = self.prepare_adoption()
        with transaction(self.repo, core.TXN_WRITE) as txn:
            name = literal(txn, core.DATUM_STRING, b"historical")
            dag = put(txn, core.REC_DAG, name, b"attempt_ref", name)
            tree = put(txn, core.REC_TREE, b"scale-attempt-adoption-v1", dag)
            tip = initial
            for i in range(1025):
                previous = tip
                tip = put(txn, core.REC_COMMIT, tree, previous, second if i % 2 == 0 else first)
            core.txn_ref_create(txn, b"tip", tip)
            core.txn_commit(txn)
        report = self.example["inspect"](self.repo, b"tip")
        self.assertEqual(report["commit"], tip.hex())
        self.assertEqual(report["previous_selection_commit"], previous.hex())
        self.assertEqual(report["attempt_commit"], second.hex())

    def test_adoption_validates_all_argument_slots_before_opening_repository(self):
        commit = b"\x00" * 16
        adopt = self.example["adopt_scale_attempt"]
        for basis, old, incoming, attempt, output, reason in (
            (b"chosen", b"short", b"incoming", commit, b"next", "basis selection commit"),
            (b"chosen", commit, b"incoming", b"short", b"next", "attempt commit"),
            (b"-", commit, b"incoming", commit, b"next", "basis ref"),
            (b"chosen", commit, "incoming", commit, b"next", "attempt ref"),
            (b"chosen", commit, b"incoming", commit, b"-", "selection ref"),
            (b"chosen", commit, b"chosen", commit, b"next", "distinct"),
            (b"chosen", commit, b"incoming", commit, b"chosen", "distinct"),
            (b"chosen", commit, b"incoming", commit, b"incoming", "distinct"),
            (b"main", commit, b"incoming", commit, b"next", "distinct"),
            (b"chosen", commit, b"main", commit, b"next", "distinct"),
            (b"chosen", commit, b"incoming", commit, b"main", "distinct"),
        ):
            with self.subTest(basis=basis, incoming=incoming, output=output, reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    adopt(self.repo, basis, old, incoming, attempt, output)
                self.assertFalse(self.repo.exists())

    def test_policy_legacy_reuse_rolls_back_late_and_keeps_distinct_decisions_for_equal_intent(self):
        producer, old_plan, request, _, _, _ = self.prepare_adoption()
        define = self.example["define_scale_policy"]
        policy = define(self.repo, b"policy", b"reuse-by-default")
        result = self.example["work_scale"](self.repo, b"incoming", request, b"result")
        chosen = self.example["select_scale_result"](self.repo, b"plan", old_plan, b"result", result, b"legacy")
        prior_main = self.example["record_scale"](self.repo, b"producer", producer, b"main", 4)
        self.assertNotEqual(prior_main, result)

        def decide(ref, *, factor=3):
            return self.example["request_policy_scale"](
                self.repo, b"producer", producer, b"policy", policy, b"would-plan", ref, factor,
                selection_ref=b"legacy", selection_commit=chosen,
            )

        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "selection does not retain the expected request"):
            decide(b"wrong-request", factor=4)
        self.assertEqual(data.read_bytes(), before)
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            decide(b"result")
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"main"), prior_main)
            self.assertEqual(core.txn_ref_get(txn, b"plan"), old_plan)
            self.assert_missing_ref(txn, b"would-plan")
            self.assert_missing_ref(txn, b"wrong-request")

        decision = decide(b"first-decision")
        report = self.example["inspect"](self.repo, b"first-decision")
        self.assertEqual(report["expected_main"], prior_main.hex())
        self.assertEqual((report["selection_commit"], report["result_commit"]), (chosen.hex(), result.hex()))
        self.assertNotIn("attempt_id", report)
        with transaction(self.repo) as txn:
            stored, dag, parents = self.snapshot(txn, b"first-decision", b"scale-request-decision-v1")
            plan = bytes.fromhex(report["plan_commit"])
            self.assertEqual((stored, parents), (decision, (plan, policy, chosen)))
            self.assertEqual(core.txn_ref_get(txn, b"main"), result)
            self.assertEqual(core.txn_ref_get(txn, b"plan"), old_plan)
            self.assert_missing_ref(txn, b"would-plan")
            plan_view, _, parent_count = view(txn, core.REC_COMMIT, plan)
            self.assertEqual(parent_count, 2)
            self.assertEqual(core.object_view_parent(plan_view, 0), request)
            self.assertEqual(core.object_view_parent(plan_view, 1), prior_main)
            _, root, count = view(txn, core.REC_DAG, dag)
            self.assertEqual((count, root), (4, core.txn_lookup_node(txn, dag, b"decision_id")))
            self.assertEqual(self.literal_value(txn, root, core.DATUM_STRING), report["decision_id"])

        # Both later decisions have the same immutable parents and intent data.
        self.assertNotEqual(decide(b"again"), decide(b"repeat"))
        again = self.example["inspect"](self.repo, b"again")
        repeat = self.example["inspect"](self.repo, b"repeat")
        self.assertNotEqual(again.pop("commit"), repeat.pop("commit"))
        self.assertNotEqual(again.pop("decision_id"), repeat.pop("decision_id"))
        self.assertEqual(again, repeat)
        self.assertEqual((again["selection_commit"], again["result_commit"]), (chosen.hex(), result.hex()))

    def test_policy_and_decision_readers_revalidate_typed_parents_and_fields(self):
        producer, plan, _, _, _, selection = self.prepare_adoption()
        define = self.example["define_scale_policy"]
        policy = define(self.repo, b"policy", b"reuse-by-default")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            def record(ref, entry, fields, root, *parents):
                nodes = {key: literal(txn, core.DATUM_STRING, value) for key, value in fields.items()}
                bindings = [value for pair in nodes.items() for value in pair]
                dag = put(txn, core.REC_DAG, nodes[root], *bindings)
                tree = put(txn, core.REC_TREE, entry, dag)
                commit = put(txn, core.REC_COMMIT, tree, *parents)
                core.txn_ref_create(txn, ref, commit)
                return commit

            policy_entry = b"scale-intent-policy-v1"
            malformed = record(b"bad-policy", policy_entry, {b"default": b"reuse-by-default"}, b"default", producer)
            invalid = ((b"bad-policy", "optional policy parent"), (b"unknown-policy", "policy default must be"))
            record(b"unknown-policy", policy_entry, {b"default": b"typo"}, b"default")
            fields = {b"decision_id": ATTEMPT_A, b"override": b"default", b"reason": b"default-selection",
                      b"selection_ref": b"chosen"}
            cases = (
                (b"swapped", fields, b"decision_id", (policy, plan, selection), "expected a scale-plan-v1"),
                (b"bad-ancestor", fields, b"decision_id", (plan, malformed, selection), "optional policy parent"),
                (b"not-selection", fields, b"decision_id", (plan, policy, producer), "expected a scale result or attempt"),
                (b"wrong-root", fields, b"reason", (plan, policy, selection), "decision ID as root"),
                (b"wrong-id", {**fields, b"decision_id": b"not-a-uuid"}, b"decision_id",
                 (plan, policy, selection), "canonical lowercase UUIDv4"),
                (b"wrong-override", {**fields, b"override": b"fresh"}, b"decision_id",
                 (plan, policy, selection), "fresh execution cannot retain a selection"),
                (b"wrong-reason", {**fields, b"reason": b"default-no-selection"}, b"decision_id",
                 (plan, policy, selection), "fields do not match"),
                (b"extra-field", {**fields, b"plan_ref": b"not-created"}, b"decision_id",
                 (plan, policy, selection), "fields do not match"),
                (b"aliased-refs", {**fields, b"plan_ref": b"fresh", b"reason": b"default-no-selection",
                                   b"selection_ref": b"fresh"}, b"decision_id",
                 (plan, policy), "invalid or aliased ref names"),
            )
            commits = {ref: record(ref, b"scale-request-decision-v1", fields, root, *parents)
                       for ref, fields, root, parents, _ in cases}
            core.txn_commit(txn)

        before = (self.repo / "data.mdb").read_bytes()
        inspect = self.example["inspect"]
        for ref, reason in (*invalid, *((ref, reason) for ref, _, _, _, reason in cases)):
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, reason):
                inspect(self.repo, ref)
        with self.assertRaisesRegex(ValueError, "optional policy parent"):
            define(self.repo, b"next", b"execute-by-default", basis_ref=b"bad-policy", basis_commit=malformed)
        with self.assertRaisesRegex(ValueError, "optional policy parent"):
            self.example["request_policy_scale"](self.repo, b"producer", producer, b"bad-policy", malformed,
                                                 b"would-plan", b"decision", 3, override=b"fresh")

        def decide(override):
            return self.example["request_policy_scale"](
                self.repo, b"producer", producer, b"policy", policy, b"would-plan", b"decision", 3,
                override=override, selection_ref=b"swapped", selection_commit=commits[b"swapped"],
            )

        with self.assertRaisesRegex(ValueError, "expected a scale result or attempt selection"):
            decide(b"default")
        self.assertEqual((self.repo / "data.mdb").read_bytes(), before)
        decision = decide(b"fresh")
        report = inspect(self.repo, b"decision")
        self.assertEqual((report["commit"], report["reason"]), (decision.hex(), "override-fresh"))
        self.assertNotIn("selection_ref", report)
        self.assertNotIn("selection_commit", report)

    def test_intent_readers_revalidate_definition_lineage_and_implementation_decision(self):
        producer, _, _, _, _, chosen = self.prepare_adoption()
        define = self.example["define_scale_intent"]
        decide = self.example["request_intent_scale"]
        inspect = self.example["inspect"]
        v1, v2 = b"example.scale@1", b"example.scale@2"
        basis = define(self.repo, b"basis", v1, policy_default=b"reuse-by-default",
                       v1_selection_ref=b"chosen", v2_selection_ref=b"chosen-b")
        right = define(self.repo, b"right", v2, basis_ref=b"basis", basis_commit=basis)
        decision = decide(self.repo, b"producer", producer, b"right", right, b"plan-b", b"miss", 3)
        report = inspect(self.repo, b"miss")
        self.assertEqual((report["request_implementation"], report["selection_ref"]), (v2.decode(), "chosen-b"))
        self.assertNotIn("selection_commit", report)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            plan, _, (request,) = self.snapshot(txn, b"plan-b", b"scale-plan-v1")
            stored, _, parents = self.snapshot(txn, b"miss", b"scale-intent-decision-v1")
            self.assertEqual((stored, parents, report["request_commit"]), (decision, (plan, right), request.hex()))
            _, _, parents = self.snapshot(txn, b"right", b"scale-intent-definition-v1")
            self.assertEqual(parents, (basis,))

            def record(ref, entry, fields, root, *parents):
                nodes = {key: literal(txn, core.DATUM_STRING, value) for key, value in fields.items()}
                bindings = [value for pair in nodes.items() for value in pair]
                dag = put(txn, core.REC_DAG, nodes[root], *bindings)
                tree = put(txn, core.REC_TREE, entry, dag)
                commit = put(txn, core.REC_COMMIT, tree, *parents)
                core.txn_ref_create(txn, ref, commit)
                return commit

            definitions = {b"default_implementation": v2, b"policy_default": b"reuse-by-default",
                           b"v1_selection_ref": b"chosen", b"v2_selection_ref": b"chosen-b"}
            definition_entry = b"scale-intent-definition-v1"
            invalid = []
            for ref, fields, parent, error in (
                (b"changed-policy", {b"policy_default": b"execute-by-default"}, basis, "preserve its reuse default"),
                (b"changed-slot", {b"v1_selection_ref": b"another"}, basis, "preserve its reuse default"),
                (b"aliased-slots", {b"v1_selection_ref": b"chosen-b"}, basis, "must be distinct"),
                (b"unknown-version", {b"default_implementation": b"typo"}, basis, "unsupported scale implementation"),
                (b"wrong-ancestor", {}, producer, "optional intent parent"),
            ):
                commit = record(ref, definition_entry, {**definitions, **fields}, b"default_implementation", parent)
                invalid.append((ref, commit, error))

            fields = {b"decision_id": ATTEMPT_A, b"override": b"default", b"reason": b"default-no-selection",
                      b"implementation_override": b"default", b"implementation_reason": b"default-implementation",
                      b"plan_ref": b"plan-b", b"selection_ref": b"chosen-b"}
            reuse_fields = {key: value for key, value in fields.items() if key != b"plan_ref"}
            for ref, forged, parents, error in (
                (b"wrong-definition", {**fields, b"selection_ref": b"chosen"},
                 (plan, basis), "resolved implementation"),
                (b"wrong-override", {**fields, b"selection_ref": b"chosen", b"implementation_override": v1,
                                     b"implementation_reason": b"explicit-implementation"},
                 (plan, right), "resolved implementation"),
                (b"wrong-reason", {**fields, b"implementation_override": v2}, (plan, right), "resolved implementation"),
                (b"wrong-slot", {**fields, b"selection_ref": b"chosen"}, (plan, right), "resolved selection slot"),
                (b"aliased-plan", {**fields, b"plan_ref": b"chosen"}, (plan, right), "invalid or aliased ref names"),
                (b"foreign-selection", {**reuse_fields, b"reason": b"default-selection"},
                 (plan, right, chosen), "selection does not retain the expected request"),
            ):
                commit = record(ref, b"scale-intent-decision-v1", forged, b"decision_id", *parents)
                invalid.append((ref, commit, error))
            core.txn_commit(txn)

        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for ref, _, error in invalid:
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, error):
                inspect(self.repo, ref)
        bad_ref, bad_commit, error = next(row for row in invalid if row[0] == b"wrong-ancestor")
        with self.assertRaisesRegex(ValueError, error):
            define(self.repo, b"child", v1, basis_ref=bad_ref, basis_commit=bad_commit)
        with self.assertRaisesRegex(ValueError, error):
            decide(self.repo, b"producer", producer, bad_ref, bad_commit, b"unused-plan", b"unused", 3, override=b"fresh")
        self.assertEqual(data.read_bytes(), before)

    def test_intent_fresh_routes_ignore_slot_and_an_explicit_reuse_overrides_execute_default(self):
        producer, _, request, first, _, chosen = self.prepare_adoption()
        define = self.example["define_scale_intent"]
        decide = self.example["request_intent_scale"]
        inspect = self.example["inspect"]
        v1, v2 = b"example.scale@1", b"example.scale@2"
        intent = define(self.repo, b"intent", v2, policy_default=b"execute-by-default",
                        v1_selection_ref=b"chosen", v2_selection_ref=b"not-selection")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_create(txn, b"not-selection", producer)
            core.txn_commit(txn)

        def ask(plan_ref, decision_ref, factor=3, **options):
            return decide(self.repo, b"producer", producer, b"intent", intent, plan_ref, decision_ref, factor, **options)

        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "expected a scale result or attempt selection"):
            ask(b"unused", b"bad", override=b"reuse-selected", selection_commit=producer)
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            ask(b"rolled-back", b"plan", factor=4, override=b"fresh", selection_commit=chosen)
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assert_missing_ref(txn, b"rolled-back")
            self.assert_missing_ref(txn, b"main")

        for plan_ref, decision_ref, override, reason in (
            (b"default-plan", b"default-decision", b"default", "default-execution"),
            (b"fresh-plan", b"fresh-decision", b"fresh", "override-fresh"),
        ):
            ask(plan_ref, decision_ref, override=override, selection_commit=chosen)
            report = inspect(self.repo, decision_ref)
            self.assertEqual((report["request_implementation"], report["reason"]), (v2.decode(), reason))
            self.assertNotIn("selection_ref", report)
            self.assertNotIn("selection_commit", report)

        ask(b"unused", b"reused", implementation=v1, override=b"reuse-selected", selection_commit=chosen)
        report = inspect(self.repo, b"reused")
        self.assertEqual((report["request_commit"], report["attempt_commit"]), (request.hex(), first.hex()))
        self.assertEqual((report["implementation_reason"], report["reason"]),
                         ("explicit-implementation", "override-selected-reuse"))
        with transaction(self.repo) as txn:
            self.assertEqual(core.txn_ref_get(txn, b"main").hex(), report["result_commit"])
            self.assertEqual(core.txn_ref_get(txn, b"not-selection"), producer)
            self.assert_missing_ref(txn, b"unused")

    def test_supersession_requires_exact_distinct_pins_and_rolls_back_occupied_output(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        define = self.example["define_scale_intent"]
        declare = self.example["declare_scale_supersession"]
        v1, v2 = b"example.scale@1", b"example.scale@2"
        basis = define(self.repo, b"basis", v2, policy_default=b"reuse-by-default",
                       v1_selection_ref=b"slot-v1", v2_selection_ref=b"slot-v2")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            empty_tree = put(txn, core.REC_TREE)
            empty = put(txn, core.REC_COMMIT, empty_tree)
            core.txn_ref_create(txn, b"empty", empty)
            core.txn_ref_create(txn, b"same-basis", basis)
            core.txn_commit(txn)
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        reason = b"correctness-fix"
        for expected, output, successor, tag, evidence_ref, evidence, error in (
            (producer, b"unused", v2, reason, b"producer", producer, "expected intent commit"),
            (basis, b"unused", v2, reason, b"producer", basis, "expected evidence commit"),
            (basis, b"unused", v2, reason, b"empty", empty, "nonempty tree"),
            (basis, b"unused", v2, reason, b"same-basis", basis, "distinct commits"),
            (basis, b"unused", v2, reason, b"slot-v2", producer, "must be distinct"),
            (basis, b"slot-v1", v2, reason, b"producer", producer, "must be distinct"),
            (basis, b"main", v2, reason, b"producer", producer, "must be distinct"),
            (basis, b"unused", v1, reason, b"producer", producer, "distinct implementations"),
            (basis, b"unused", b"example.scale@3", reason, b"producer", producer, "unsupported scale implementation"),
            (basis, b"unused", v2, b"typo", b"producer", producer, "supersession reason"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                declare(self.repo, b"basis", expected, output, v1, successor, tag, evidence_ref, evidence)
            self.assertEqual(data.read_bytes(), before)
        # Use a different occupied output so the writer reaches ref creation after building new objects.
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            declare(self.repo, b"basis", basis, b"empty", v1, v2, reason, b"producer", producer)
        self.assertEqual(data.read_bytes(), before)
        declared = declare(self.repo, b"basis", basis, b"noted", v1, v2, reason, b"producer", producer)
        inspect = self.example["inspect"]
        report = inspect(self.repo, b"noted")
        self.assertEqual((report["default_implementation"], report["previous_intent_commit"]), (v2.decode(), basis.hex()))
        self.assertEqual(report["supersession"]["commit"], declared.hex())
        self.assertIsNone(inspect(self.repo, b"basis")["supersession"])
        before = data.read_bytes()
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            declare(self.repo, b"basis", basis, b"noted", v1, v2, reason, b"producer", producer)
        with self.assertRaisesRegex(ValueError, "already has a supersession declaration"):
            declare(self.repo, b"noted", declared, b"unused", v2, v1, reason, b"producer", producer)
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            actual, _, parents = self.snapshot(txn, b"noted", b"scale-implementation-supersession-v1")
            self.assertEqual((actual, parents), (declared, (basis, producer)))
            self.assertEqual(core.txn_ref_get(txn, b"basis"), basis)
            self.assertEqual(core.txn_ref_get(txn, b"producer"), producer)
            for ref in (b"main", b"unused", b"slot-v1", b"slot-v2"):
                self.assert_missing_ref(txn, ref)

    def test_supersession_rejects_forged_ancestry_and_unrelated_knowledge(self):
        evidence = self.example["record_sum"](self.repo, b"producer", 7, 5)
        define = self.example["define_scale_intent"]
        inspect = self.example["inspect"]
        choose = self.example["request_intent_scale"]
        v1, v2 = b"example.scale@1", b"example.scale@2"
        initial = dict(policy_default=b"execute-by-default", v1_selection_ref=b"slot-v1", v2_selection_ref=b"slot-v2")
        basis = define(self.repo, b"basis", v1, **initial)
        unrelated = define(self.repo, b"unrelated", v2, **initial)
        choose(self.repo, b"producer", evidence, b"basis", basis, b"pending", b"decision", 3)
        valid = self.example["declare_scale_supersession"](
            self.repo, b"basis", basis, b"noted", v1, v2, b"operational-replacement", b"producer", evidence,
        )
        promoted = define(self.repo, b"promoted", v2, basis_ref=b"noted", basis_commit=valid)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, dag, _ = self.snapshot(txn, b"noted", b"scale-implementation-supersession-v1")
            predecessor = core.txn_lookup_node(txn, dag, b"predecessor")
            successor = core.txn_lookup_node(txn, dag, b"successor")
            reason = core.txn_lookup_node(txn, dag, b"reason")
            bogus = literal(txn, core.DATUM_STRING, b"looks-valid")
            wrong_kind = literal(txn, core.DATUM_I64, 7)

            def declaration(root, successor_node, reason_node):
                return put(txn, core.REC_DAG, root, b"predecessor", predecessor, b"successor", successor_node,
                           b"reason", reason_node)

            invalid = []
            for ref, fields, parents, error in (
                (b"bad-root", declaration(successor, successor, reason), (basis, evidence), "wrong DAG layout"),
                (b"bad-type", declaration(predecessor, successor, wrong_kind), (basis, evidence), "wrong datum kind"),
                (b"bad-reason", declaration(predecessor, successor, bogus), (basis, evidence), "supersession reason"),
                (b"self-endpoint", declaration(predecessor, predecessor, reason), (basis, evidence),
                 "distinct implementations"),
                (b"no-evidence", dag, (basis,), "ordered intent basis and evidence"),
                (b"swapped", dag, (evidence, basis), "optional intent parent"),
                (b"stacked", dag, (promoted, evidence), "already has a supersession declaration"),
            ):
                tree = put(txn, core.REC_TREE, b"scale-implementation-supersession-v1", fields)
                record = put(txn, core.REC_COMMIT, tree, *parents)
                core.txn_ref_create(txn, ref, record)
                invalid.append((ref, record, error))
            core.txn_commit(txn)
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for ref, record, error in invalid:
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(ValueError, error):
                    inspect(self.repo, ref)
                with self.assertRaisesRegex(ValueError, error):
                    inspect(self.repo, b"decision", knowledge_commit=record)
        # Same reuse mode and slots, but a different initial snapshot.
        with self.assertRaisesRegex(ValueError, "different intent lineage"):
            inspect(self.repo, b"decision", knowledge_commit=unrelated)
        with self.assertRaisesRegex(core.Error, "not_found"):
            inspect(self.repo, b"decision", knowledge_commit=b"\0" * 16)
        with self.assertRaisesRegex(ValueError, "knowledge commit must be a 16-byte ID"):
            inspect(self.repo, b"decision", knowledge_commit=b"invalid")
        with self.assertRaisesRegex(ValueError, "knowledge commit requires an intent decision"):
            inspect(self.repo, b"pending", knowledge_commit=valid)
        self.assertEqual(data.read_bytes(), before)

    def test_supersession_views_use_transferred_pins_and_keep_historical_absence(self):
        record_sum = self.example["record_sum"]
        define = self.example["define_scale_intent"]
        choose = self.example["request_intent_scale"]
        producer = record_sum(self.repo, b"producer", 7, 5)
        evidence = record_sum(self.repo, b"evidence", -3, 0)
        v1, v2 = b"example.scale@1", b"example.scale@2"
        basis = define(self.repo, b"basis", v1, policy_default=b"execute-by-default",
                       v1_selection_ref=b"slot-v1", v2_selection_ref=b"slot-v2")
        old = choose(self.repo, b"producer", producer, b"basis", basis, b"old-plan", b"old", 3)
        declaration = self.expect_success("declare-scale-supersession", "basis", basis.hex(), "noted",
                                          v1.decode(), v2.decode(), "operational-replacement",
                                          "evidence", evidence.hex()).strip()
        noted = bytes.fromhex(declaration)
        promotion = define(self.repo, b"promoted", v2, basis_ref=b"noted", basis_commit=noted)
        new = choose(self.repo, b"producer", producer, b"promoted", promotion, b"new-plan", b"new", 3)
        # A conflicting sibling can use a declaration as opaque evidence; it is not a second intent parent.
        sibling = self.example["declare_scale_supersession"](
            self.repo, b"basis", basis, b"sibling", v2, v1, b"correctness-fix", b"noted", noted,
        )
        # The replica has neither live intent ref, either plan ref, nor an evidence pin.
        destination = self.workspace / "replica"
        source = core.repo_open(self.repo, False)
        try:
            replica = core.repo_open(destination, True)
            try:
                for ref, commit in ((b"old", old), (b"new", new), (b"peer-knowledge", sibling)):
                    bundle = core.repo_export_commit(source, commit)
                    self.assertEqual(core.repo_import_commit_staged(replica, bundle, ref), commit)
            finally:
                core.repo_close(replica)
        finally:
            core.repo_close(source)
        self.example["collect"](destination)
        with transaction(destination) as txn:
            for ref in (b"main", b"evidence", b"basis", b"noted", b"promoted", b"old-plan", b"new-plan"):
                self.assert_missing_ref(txn, ref)
            view(txn, core.REC_COMMIT, evidence)
        expected = {"commit": declaration, "basis_commit": basis.hex(), "evidence_commit": evidence.hex(),
                    "predecessor": v1.decode(), "successor": v2.decode(), "reason": "operational-replacement"}
        prior = json.loads(self.expect_success("inspect", "old", repo=destination))
        together = json.loads(self.expect_success("inspect", "old", "--knowledge-commit", promotion.hex(),
                                                  repo=destination))
        self.assertEqual(prior["as_known_then"], {"intent_commit": basis.hex(), "relation": "none", "declaration": None})
        self.assertEqual(together.pop("knowledge_view"),
                         {"intent_commit": promotion.hex(), "relation": "predecessor", "declaration": expected})
        self.assertEqual(together, prior)
        newer = json.loads(self.expect_success("inspect", "new", "--knowledge-commit", basis.hex(), repo=destination))
        self.assertEqual(newer["as_known_then"],
                         {"intent_commit": promotion.hex(), "relation": "successor", "declaration": expected})
        self.assertEqual(newer["knowledge_view"], {"intent_commit": basis.hex(), "relation": "none", "declaration": None})
        sibling_read = self.example["inspect"](destination, b"new", knowledge_commit=sibling)
        self.assertEqual(sibling_read.pop("knowledge_view"),
                         {"intent_commit": sibling.hex(), "relation": "predecessor", "declaration": {
                             "commit": sibling.hex(), "basis_commit": basis.hex(), "evidence_commit": declaration,
                             "predecessor": v2.decode(), "successor": v1.decode(), "reason": "correctness-fix",
                         }})
        self.assertEqual(sibling_read, self.example["inspect"](destination, b"new"))

    def test_attempt_work_rejects_invalid_identity_stale_ref_and_overflow_atomically(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        self.example["request_scale"](self.repo, b"producer", producer, b"plan", 1 << 62)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            _, _, (request,) = self.snapshot(txn, b"plan", b"scale-plan-v1")
            core.txn_ref_create(txn, b"incoming", request)
            core.txn_commit(txn)
        work = self.example["work_scale_attempt"]
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for incoming, commit, output, identity, reason in (
            (b"incoming", request, b"attempt", ATTEMPT_A.upper(), "canonical lowercase UUIDv4"),
            (b"incoming", request, b"attempt", ATTEMPT_A.replace(b"-8000-", b"-7000-"), "UUIDv4"),
            (b"incoming", request, b"attempt", ATTEMPT_A.decode("ascii"), "UUIDv4"),
            (b"incoming", request, b"incoming", ATTEMPT_A, "distinct"),
            (b"incoming", request, b"main", ATTEMPT_A, "distinct"),
            (b"incoming", request, b"-invalid", ATTEMPT_A, "valid ASCII ref name"),
            (b"incoming", b"short", b"attempt", ATTEMPT_A, "16-byte ID"),
            (b"incoming", producer, b"attempt", ATTEMPT_A, "expected request commit"),
            (b"incoming", request, b"attempt", ATTEMPT_A, "signed 64-bit integer"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    work(self.repo, incoming, commit, output, identity)
                self.assertEqual(data.read_bytes(), before)

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

    def make_scale_reuse_table(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        intent = self.example["define_scale_intent"](
            self.repo, b"intent", b"example.scale@1", policy_default=b"reuse-by-default",
            v1_selection_ref=b"legacy-v1", v2_selection_ref=b"legacy-v2",
        )
        table = self.example["define_scale_reuse_table"](self.repo, b"intent", intent, b"example.scale@1", b"empty")
        return producer, intent, table

    def make_table_selection(self, producer, factor, *, suffix, implementation=b"example.scale@1"):
        plan_ref, request_ref, attempt_ref, selection_ref = (
            f"{name}-{suffix}".encode("ascii") for name in ("plan", "request", "attempt", "selection")
        )
        plan = self.example["request_scale"](
            self.repo, b"producer", producer, plan_ref, factor, implementation=implementation,
        )
        with transaction(self.repo, core.TXN_WRITE) as txn:
            plan_view, _, _ = view(txn, core.REC_COMMIT, plan)
            request = core.object_view_parent(plan_view, 0)
            core.txn_ref_create(txn, request_ref, request)
            core.txn_commit(txn)
        attempt_id = f"00000000-0000-4000-8000-{suffix:012d}".encode("ascii")
        attempt = self.example["work_scale_attempt"](self.repo, request_ref, request, attempt_ref, attempt_id)
        selection = self.example["select_scale_attempt"](self.repo, plan_ref, plan, attempt_ref, attempt, selection_ref)
        return request, (selection_ref, selection)

    @staticmethod
    def put_table_delta(txn, basis, selection, operation, key):
        root = literal(txn, core.DATUM_STRING, operation)
        request = literal(txn, core.DATUM_STRING, key.hex().encode("ascii"))
        dag = put(txn, core.REC_DAG, root, b"operation", root, b"request_commit", request)
        tree = put(txn, core.REC_TREE, b"scale-reuse-table-update-v1", dag)
        return put(txn, core.REC_COMMIT, tree, basis, selection)

    def test_reuse_table_capacity_rejects_insertion_without_eviction_but_permits_adoption(self):
        producer, _, empty = self.make_scale_reuse_table()
        basis_ref, basis = b"empty", empty
        update = self.example["update_scale_reuse_table"]
        keys = []
        for factor in range(-8, 8):
            key, selection = self.make_table_selection(producer, factor, suffix=factor + 9)
            keys.append(key.hex())
            output = f"table-{factor}".encode("ascii")
            basis_ref, basis = output, update(self.repo, basis_ref, basis, *selection, output, b"insert")
        full = self.example["inspect"](self.repo, basis_ref)
        self.assertEqual(set(full["entries"]), set(keys))
        overflow_key, overflow = self.make_table_selection(producer, 8, suffix=17)
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "more than 16 requests"):
            update(self.repo, basis_ref, basis, *overflow, b"too-many", b"insert")
        self.assertEqual(data.read_bytes(), before)
        # A structurally valid committed delta cannot bypass the reader's cap.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            forged = self.put_table_delta(txn, basis, overflow[1], b"insert", overflow_key)
            core.txn_ref_create(txn, b"forged-overflow", forged)
            core.txn_commit(txn)
        with self.assertRaisesRegex(ValueError, "more than 16 requests"):
            self.example["inspect"](self.repo, b"forged-overflow")
        _, replacement = self.make_table_selection(producer, -8, suffix=18)
        update(self.repo, basis_ref, basis, *replacement, b"adopted", b"adopt")
        current = self.example["inspect"](self.repo, b"adopted")
        old_rows, new_rows = full["entries"], current["entries"]
        self.assertEqual({key for key in old_rows if old_rows[key] != new_rows[key]}, {keys[0]})
        self.assertEqual(new_rows[keys[0]]["selection_commit"], replacement[1].hex())
        self.assertEqual(self.example["inspect"](self.repo, basis_ref), full)

    def test_reuse_table_rejects_result_only_and_cross_version_selections(self):
        producer, _, empty = self.make_scale_reuse_table()
        key, _ = self.make_table_selection(producer, 2, suffix=1)
        old_plan = bytes.fromhex(self.example["inspect"](self.repo, b"plan-1")["commit"])
        result = self.example["work_scale"](self.repo, b"request-1", key, b"result")
        selected_result = self.example["select_scale_result"](
            self.repo, b"plan-1", old_plan, b"result", result, b"selected-result",
        )
        _, selected_v2 = self.make_table_selection(producer, 2, suffix=2, implementation=b"example.scale@2")
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for selection, diagnostic in (((b"selected-result", selected_result), "requires an attempt selection"),
                                      (selected_v2, "implementation does not match")):
            with self.subTest(selection=selection[0]), self.assertRaisesRegex(ValueError, diagnostic):
                self.example["update_scale_reuse_table"](self.repo, b"empty", empty, *selection, b"bad", b"insert")
            self.assertEqual(data.read_bytes(), before)

    def test_reuse_table_rejects_buried_nonmatching_delta_even_on_a_hit(self):
        producer, intent, empty = self.make_scale_reuse_table()
        first, selected_first = self.make_table_selection(producer, 2, suffix=1)
        _, selected_second = self.make_table_selection(producer, 3, suffix=2)
        _, replacement = self.make_table_selection(producer, 2, suffix=3)
        one = self.example["update_scale_reuse_table"](self.repo, b"empty", empty, *selected_first, b"one", b"insert")
        with transaction(self.repo, core.TXN_WRITE) as txn:
            # Claim a key unrelated to the actual selection on a row this request won't look up.
            forged = self.put_table_delta(txn, one, selected_second[1], b"insert", bytes(16))
            buried = self.put_table_delta(txn, forged, replacement[1], b"adopt", first)
            core.txn_ref_create(txn, b"buried", buried)
            core.txn_commit(txn)
        request = self.example["request_table_scale"]
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "key does not match the selection request commit"):
            self.example["inspect"](self.repo, b"buried")
        arguments = (self.repo, b"producer", producer, b"intent", intent, b"fresh", b"decision", 2)
        with self.assertRaisesRegex(ValueError, "key does not match the selection request commit"):
            request(*arguments, table_ref=b"buried", table_commit=buried)
        self.assertEqual(data.read_bytes(), before)
        request(*arguments, table_ref=b"buried", table_commit=buried, override=b"fresh")
        decision = self.example["inspect"](self.repo, b"decision")
        self.assertEqual(decision["request_commit"], first.hex())
        self.assertEqual(decision["reason"], "override-fresh")
        self.assertTrue({"table_ref", "table_commit", "selection_commit"}.isdisjoint(decision))

    def test_reuse_table_scope_uses_intent_genesis_not_latest_intent_or_equal_fields(self):
        producer, intent, empty = self.make_scale_reuse_table()
        _, selected = self.make_table_selection(producer, 2, suffix=1)
        table = self.example["update_scale_reuse_table"](self.repo, b"empty", empty, *selected, b"one", b"insert")
        define = self.example["define_scale_intent"]
        other = define(self.repo, b"other", b"example.scale@2", policy_default=b"reuse-by-default",
                       v1_selection_ref=b"legacy-v1", v2_selection_ref=b"legacy-v2")
        # Returning to v1 now produces the same definition fields as the table's intent, but in another lineage.
        same_fields = define(self.repo, b"same-fields", b"example.scale@1", basis_ref=b"other", basis_commit=other)
        promoted = define(self.repo, b"promoted", b"example.scale@2", basis_ref=b"intent", basis_commit=intent)
        request = self.example["request_table_scale"]
        pins = {"table_ref": b"one", "table_commit": table}
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for ref, commit in ((b"same-fields", same_fields), (b"promoted", promoted)):
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, "selected implementation"):
                request(self.repo, b"producer", producer, ref, commit, b"unused", b"decision", 2, **pins)
            self.assertEqual(data.read_bytes(), before)
        request(self.repo, b"producer", producer, b"promoted", promoted, b"unused", b"decision", 2,
                implementation=b"example.scale@1", **pins)
        self.assertEqual(self.example["inspect"](self.repo, b"decision")["selection_commit"], selected[1].hex())

    def test_execute_default_bypasses_table_but_explicit_reuse_requires_exact_hit(self):
        producer, _, _ = self.make_scale_reuse_table()
        intent = self.example["define_scale_intent"](
            self.repo, b"execute", b"example.scale@1", policy_default=b"execute-by-default",
            v1_selection_ref=b"legacy-v1", v2_selection_ref=b"legacy-v2",
        )
        empty = self.example["define_scale_reuse_table"](self.repo, b"execute", intent, b"example.scale@1", b"ex-table")
        request = self.example["request_table_scale"]
        inputs = (self.repo, b"producer", producer, b"execute", intent)
        request(*inputs, b"fresh", b"default-execute", 2, table_ref=b"ex-table", table_commit=producer)
        decision = self.example["inspect"](self.repo, b"default-execute")
        self.assertEqual(decision["reason"], "default-execution")
        self.assertTrue({"table_ref", "table_commit", "selection_commit"}.isdisjoint(decision))
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "explicit reuse requires"):
            request(*inputs, b"unused", b"reuse", 2, table_ref=b"ex-table", table_commit=empty,
                    override=b"reuse-selected")
        self.assertEqual(data.read_bytes(), before)
        _, selected = self.make_table_selection(producer, 2, suffix=1)
        table = self.example["update_scale_reuse_table"](self.repo, b"ex-table", empty, *selected, b"hit", b"insert")
        request(*inputs, b"unused", b"reuse", 2, table_ref=b"hit", table_commit=table, override=b"reuse-selected")
        decision = self.example["inspect"](self.repo, b"reuse")
        self.assertEqual(decision["reason"], "override-selected-reuse")
        self.assertEqual(decision["selection_commit"], selected[1].hex())

    def test_reuse_table_decision_inspection_recomputes_hit_and_miss_from_its_table_parent(self):
        producer, intent, empty = self.make_scale_reuse_table()
        _, selection = self.make_table_selection(producer, 3, suffix=1)
        table = self.example["update_scale_reuse_table"](self.repo, b"empty", empty, *selection, b"one", b"insert")
        self.example["request_table_scale"](
            self.repo, b"producer", producer, b"intent", intent, b"unused", b"decision", 3,
            table_ref=b"one", table_commit=table,
        )
        with transaction(self.repo, core.TXN_WRITE) as txn:
            decision = core.txn_ref_get(txn, b"decision")
            snapshot, tree, count = view(txn, core.REC_COMMIT, decision)
            self.assertEqual(count, 3)
            plan, definition, actual = (core.object_view_parent(snapshot, i) for i in range(3))
            self.assertEqual((definition, actual), (intent, table))
            forged = put(txn, core.REC_COMMIT, tree, plan, intent, empty)
            core.txn_ref_create(txn, b"forged-decision", forged)
            core.txn_commit(txn)
        with self.assertRaisesRegex(ValueError, "fields do not match the resolved policy"):
            self.example["inspect"](self.repo, b"forged-decision")
        self.assertEqual(self.example["inspect"](self.repo, b"decision")["reason"], "default-table-hit")

    def make_intent_reuse_table(self):
        producer, intent, legacy = self.make_scale_reuse_table()
        empty = self.example["define_scale_intent_reuse_table"](self.repo, b"intent", intent, b"intent-empty")
        return producer, intent, legacy, empty

    def change_intent_table(self, basis_ref, basis_commit, output_ref, operation, *, selection=None, **key):
        pins = {} if selection is None else dict(zip(("selection_ref", "selection_commit"), selection))
        return self.example["update_scale_intent_reuse_table"](
            self.repo, basis_ref, basis_commit, output_ref, operation, **pins, **key,
        )

    @staticmethod
    def put_intent_table_delta(txn, basis, operation, producer, factor, *selection_parents, factor_kind=core.DATUM_I64):
        root = literal(txn, core.DATUM_STRING, operation)
        source = literal(txn, core.DATUM_STRING, producer.hex().encode("ascii"))
        multiplier = literal(txn, factor_kind, factor)
        dag = put(txn, core.REC_DAG, root, b"operation", root, b"producer_commit", source, b"factor", multiplier)
        tree = put(txn, core.REC_TREE, b"scale-intent-reuse-table-update-v1", dag)
        return put(txn, core.REC_COMMIT, tree, basis, *selection_parents)

    def test_intent_reuse_table_rejects_removed_malformed_history_and_wrong_parent_shapes(self):
        producer, intent, legacy, empty = self.make_intent_reuse_table()
        _, first = self.make_table_selection(producer, -3, suffix=1)
        _, other = self.make_table_selection(producer, 3, suffix=2, implementation=b"example.scale@2")
        one = self.change_intent_table(b"intent-empty", empty, b"one", b"insert", selection=first)
        with transaction(self.repo, core.TXN_WRITE) as txn:
            # A later removal cannot hide a key that did not match the producing request.
            wrong_key = self.put_intent_table_delta(txn, one, b"insert", producer, -4, other[1])
            extra_parent = self.put_intent_table_delta(txn, one, b"remove", producer, -3, first[1])
            missing_parent = self.put_intent_table_delta(txn, one, b"insert", producer, 3)
            wrong_type = self.put_intent_table_delta(txn, one, b"remove", producer, b"-3", factor_kind=core.DATUM_STRING)
            buried = self.put_intent_table_delta(txn, wrong_key, b"remove", producer, -4)
            wrong_role = self.put_intent_table_delta(txn, legacy, b"insert", producer, -3, first[1])
            for ref, commit in ((b"buried", buried), (b"extra-parent", extra_parent),
                                (b"missing-parent", missing_parent), (b"wrong-type", wrong_type),
                                (b"wrong-role", wrong_role)):
                core.txn_ref_create(txn, ref, commit)
            core.txn_commit(txn)
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        for ref, commit, diagnostic in (
            (b"buried", buried, "key does not match the selection inputs"),
            (b"extra-parent", extra_parent, "requires its basis and a selection"),
            (b"missing-parent", missing_parent, "requires its basis and a selection"),
            (b"wrong-type", wrong_type, "wrong datum kind"),
            (b"wrong-role", wrong_role, "expected an intent reuse table"),
        ):
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(ValueError, diagnostic):
                    self.example["inspect"](self.repo, ref)
                with self.assertRaisesRegex(ValueError, diagnostic):
                    self.example["request_intent_table_scale"](
                        self.repo, b"producer", producer, b"intent", intent, b"new-plan", b"new-decision", -3,
                        table_ref=ref, table_commit=commit, implementation=b"example.scale@2",
                    )
                self.assertEqual(data.read_bytes(), before)

    def test_intent_reuse_table_removal_frees_a_key_without_forgetting_old_selections(self):
        producer, _, _, empty = self.make_intent_reuse_table()
        basis, ref = empty, b"intent-empty"
        for factor in range(-8, 8):
            implementation = b"example.scale@1" if factor % 2 else b"example.scale@2"
            _, selection = self.make_table_selection(producer, factor, suffix=factor + 9, implementation=implementation)
            output = f"intent-table-{factor}".encode("ascii")
            basis, ref = self.change_intent_table(ref, basis, output, b"insert", selection=selection), output
        _, extra = self.make_table_selection(producer, 8, suffix=17)
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "more than 16 requests"):
            self.change_intent_table(ref, basis, b"full", b"insert", selection=extra)
        self.assertEqual(data.read_bytes(), before)

        inspect = self.example["inspect"]
        original = inspect(self.repo, ref)
        removed = self.change_intent_table(ref, basis, b"removed", b"remove", producer_commit=producer, factor=-8)
        remaining = [row for row in original["entries"] if row["factor"] != -8]
        self.assertEqual(len(remaining), 15)
        self.assertEqual(inspect(self.repo, b"removed")["entries"], remaining)
        self.change_intent_table(b"removed", removed, b"refilled", b"insert", selection=extra)
        refilled = inspect(self.repo, b"refilled")["entries"]
        self.assertEqual(refilled[:-1], remaining)
        self.assertEqual((refilled[-1]["factor"], refilled[-1]["selection_commit"]), (8, extra[1].hex()))
        self.assertEqual(inspect(self.repo, ref), original)

    def test_intent_reuse_rejects_same_attempt_and_result_only_selection(self):
        producer, _, _, empty = self.make_intent_reuse_table()
        request, first = self.make_table_selection(producer, 3, suffix=1)
        one = self.change_intent_table(b"intent-empty", empty, b"one", b"insert", selection=first)
        inspect = self.example["inspect"]
        plan = bytes.fromhex(inspect(self.repo, b"plan-1")["commit"])
        attempt = bytes.fromhex(inspect(self.repo, b"attempt-1")["commit"])
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_create(txn, b"aliased-attempt", attempt)
            core.txn_commit(txn)
        alias = self.example["select_scale_attempt"](
            self.repo, b"plan-1", plan, b"aliased-attempt", attempt, b"alias-selection",
        )
        self.assertNotEqual(first[1], alias)
        result = self.example["work_scale"](self.repo, b"request-1", request, b"result")
        result_only = self.example["select_scale_result"](
            self.repo, b"plan-1", plan, b"result", result, b"result-only",
        )
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "must change the selected attempt"):
            self.change_intent_table(b"one", one, b"no-change", b"adopt", selection=(b"alias-selection", alias))
        with self.assertRaisesRegex(ValueError, "requires an attempt selection"):
            self.change_intent_table(b"intent-empty", empty, b"bad", b"insert", selection=(b"result-only", result_only))
        self.assertEqual(data.read_bytes(), before)

    def test_intent_reuse_retains_the_requested_plan_and_original_producing_request(self):
        producer, intent, _, empty = self.make_intent_reuse_table()
        producing_request, selection = self.make_table_selection(producer, -3, suffix=1)
        table = self.change_intent_table(b"intent-empty", empty, b"one", b"insert", selection=selection)
        inspect = self.example["inspect"]
        old_plan = bytes.fromhex(inspect(self.repo, b"plan-1")["commit"])
        v2_plan = self.example["request_scale"](
            self.repo, b"producer", producer, b"reference-v2-plan", -3, implementation=b"example.scale@2",
        )
        requested = inspect(self.repo, b"reference-v2-plan")["request_commit"]
        decision = self.example["request_intent_table_scale"](
            self.repo, b"producer", producer, b"intent", intent, b"unused", b"decision", -3,
            table_ref=b"one", table_commit=table, implementation=b"example.scale@2",
        )
        report = inspect(self.repo, b"decision")
        self.assertEqual((report["request_commit"], report["request_implementation"]), (requested, "example.scale@2"))
        self.assertEqual((report["producing_request_commit"], report["producing_implementation"]),
                         (producing_request.hex(), "example.scale@1"))
        self.assertNotEqual(requested, producing_request.hex())
        with transaction(self.repo, core.TXN_WRITE) as txn:
            decision_view, tree, count = view(txn, core.REC_COMMIT, decision)
            self.assertEqual(count, 3)
            self.assertEqual(tuple(core.object_view_parent(decision_view, i) for i in range(count)),
                             (v2_plan, intent, table))
            result = core.txn_ref_get(txn, b"main")
            result_view, _, count = view(txn, core.REC_COMMIT, result)
            self.assertEqual(count, 1)
            self.assertEqual(core.object_view_parent(result_view, 0), producing_request)
            self.assert_missing_ref(txn, b"unused")
            forged_plan = put(txn, core.REC_COMMIT, tree, old_plan, intent, table)
            forged_table = put(txn, core.REC_COMMIT, tree, v2_plan, intent, empty)
            core.txn_ref_create(txn, b"forged-plan", forged_plan)
            core.txn_ref_create(txn, b"forged-table", forged_table)
            core.txn_commit(txn)
        with self.assertRaisesRegex(ValueError, "does not match the resolved implementation"):
            inspect(self.repo, b"forged-plan")
        with self.assertRaisesRegex(ValueError, "fields do not match the resolved policy"):
            inspect(self.repo, b"forged-table")

    def test_intent_reuse_rejects_occupied_outputs_without_publishing_the_producing_result(self):
        producer, intent, _, empty = self.make_intent_reuse_table()
        _, selection = self.make_table_selection(producer, 3, suffix=1)
        one = self.change_intent_table(b"intent-empty", empty, b"one", b"insert", selection=selection)
        self.example["record_scale"](self.repo, b"producer", producer, b"main", 4)
        data = self.repo / "data.mdb"
        # Use another alias for the table pin, so the decision collides after the main write, not during ref validation.
        with transaction(self.repo, core.TXN_WRITE) as txn:
            core.txn_ref_create(txn, b"one-live", one)
            core.txn_commit(txn)
        before = data.read_bytes()
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            self.example["request_intent_table_scale"](
                self.repo, b"producer", producer, b"intent", intent, b"unused", b"one", 3,
                table_ref=b"one-live", table_commit=one, implementation=b"example.scale@2",
            )
        self.assertEqual(data.read_bytes(), before)
        with self.assertRaisesRegex(core.Error, "ref already exists"):
            self.change_intent_table(b"one-live", one, b"one", b"remove", producer_commit=producer, factor=3)
        self.assertEqual(data.read_bytes(), before)
        with transaction(self.repo) as txn:
            self.assert_missing_ref(txn, b"unused")


if __name__ == "__main__":
    unittest.main()
