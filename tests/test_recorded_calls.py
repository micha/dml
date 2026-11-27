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


if __name__ == "__main__":
    unittest.main()
