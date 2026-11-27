"""Test the recorded-calls example across process and repository boundaries."""

from contextlib import contextmanager
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
import unittest

from daggerml import core


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "recorded_calls.py"
ATTEMPT_A = b"a0000000-0000-4000-8000-000000000001"


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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.example = runpy.run_path(EXAMPLE)

    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.repo = self.workspace / "repo"

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

    def test_supersession_rejects_short_raw_knowledge_id(self):
        producer = self.example["record_sum"](self.repo, b"producer", 7, 5)
        basis = self.example["define_scale_intent"](self.repo, b"basis", b"example.scale@1",
                                                   policy_default=b"execute-by-default",
                                                   v1_selection_ref=b"slot-v1", v2_selection_ref=b"slot-v2")
        self.example["request_intent_scale"](self.repo, b"producer", producer, b"basis", basis, b"pending", b"decision", 3)
        data = self.repo / "data.mdb"
        before = data.read_bytes()
        with self.assertRaisesRegex(ValueError, "knowledge commit must be a 16-byte ID"):
            self.example["inspect"](self.repo, b"decision", knowledge_commit=b"invalid")
        self.assertEqual(data.read_bytes(), before)

    def test_attempt_work_rejects_string_identity_and_short_raw_id(self):
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
            (b"incoming", request, b"attempt", ATTEMPT_A.decode("ascii"), "UUIDv4"),
            (b"incoming", b"short", b"attempt", ATTEMPT_A, "16-byte ID"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    work(self.repo, incoming, commit, output, identity)
                self.assertEqual(data.read_bytes(), before)

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
