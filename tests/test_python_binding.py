"""Exercise Python-specific handle consumption and lifetime behavior."""

from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from daggerml import core


class BindingTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "repo"

    def test_commit_failure_consumes_transaction_and_close_rejects_live_one(self):
        repo = core.repo_open(self.path, True)
        txn = core.txn_begin(repo, core.TXN_READ)
        with self.assertRaisesRegex(RuntimeError, "end the active transaction"):
            core.txn_begin(repo, core.TXN_WRITE)
        with self.assertRaises(core.Error) as close_error:
            core.repo_close(repo)
        self.assertEqual(close_error.exception.args[0], "invalid_state")
        with self.assertRaises(core.Error) as commit_error:
            core.txn_commit(txn)
        self.assertEqual(commit_error.exception.args[0], "invalid_state")
        with self.assertRaises(core.Error) as closed_error:
            core.txn_commit(txn)
        self.assertEqual(closed_error.exception.args[0], "invalid_argument")
        core.txn_abort(txn)  # idempotent on a consumed handle
        core.txn_abort(core.txn_begin(repo, core.TXN_WRITE))
        core.repo_close(repo)
        with self.assertRaises(core.Error):
            core.txn_begin(repo, core.TXN_READ)
        with self.assertRaises(core.Error):
            core.repo_close(repo)

    def test_view_keeps_packed_input_alive_and_checks_kind_and_bounds(self):
        dag = bytes(range(16))
        view, reference, count = core.object_decode(core.object_encode(core.REC_TREE, b"snapshot", dag))
        self.assertEqual((reference, count), (bytes(16), 1))
        self.assertEqual(core.object_view_entry(view, 0), (dag, b"snapshot"))
        with self.assertRaises(ValueError):
            core.object_view_entry(view, -1)
        with self.assertRaises(core.Error):
            core.object_view_entry(view, 1)
        with self.assertRaises(core.Error):
            core.object_view_parent(view, 0)
        with self.assertRaises(TypeError):
            core.object_view_entry(b"not a view", 0)

    def test_view_does_not_retain_a_bytes_subclass(self):
        discarded = []

        class TrackedBytes(bytes):
            def __del__(self):
                discarded.append(True)

        dag = bytes(range(16))
        record = TrackedBytes(core.object_encode(core.REC_TREE, b"snapshot", dag))
        view, _, _ = core.object_decode(record)
        record.view = view
        del record
        self.assertEqual(discarded, [True])
        self.assertEqual(core.object_view_entry(view, 0), (dag, b"snapshot"))

    def test_transaction_keeps_repository_alive_until_it_ends(self):
        txn = core.txn_begin(core.repo_open(self.path, True), core.TXN_WRITE)
        packed = core.datum_encode(core.DATUM_I64, 35)
        datum = core.txn_put_datum(txn, packed)
        core.txn_commit(txn)
        repo = core.repo_open(self.path, False)
        reader = core.txn_begin(repo, core.TXN_READ)
        self.assertEqual(core.txn_get_datum(reader, datum), packed)
        core.txn_abort(reader)
        core.repo_close(repo)

    def assert_absent(self, repo, datum):
        reader = core.txn_begin(repo, core.TXN_READ)
        try:
            with self.assertRaises(core.Error) as error:
                core.txn_get_datum(reader, datum)
            self.assertEqual(error.exception.args[0], "not_found")
        finally:
            core.txn_abort(reader)

    def test_dropping_transaction_on_owner_thread_rolls_back(self):
        repo = core.repo_open(self.path, True)
        txn = core.txn_begin(repo, core.TXN_WRITE)
        datum = core.txn_put_datum(txn, core.datum_encode(core.DATUM_I64, 35))
        del txn
        self.assert_absent(repo, datum)
        core.repo_close(repo)

    def test_foreign_actions_are_rejected_and_owner_reaps_dropped_transaction(self):
        repo = core.repo_open(self.path, True)
        transactions = [core.txn_begin(repo, core.TXN_WRITE)]
        datum = core.txn_put_datum(transactions[0], core.datum_encode(core.DATUM_I64, 35))
        outcomes = []

        def foreign_thread():
            txn = transactions.pop()
            for operation, handle in ((core.repo_close, repo), (core.txn_abort, txn), (core.txn_commit, txn)):
                try:
                    operation(handle)
                except RuntimeError as error:
                    outcomes.append(str(error))

        thread = Thread(target=foreign_thread)
        thread.start()
        thread.join()
        self.assertEqual(len(outcomes), 3)
        self.assertTrue(all("creating thread" in message for message in outcomes), outcomes)
        self.assert_absent(repo, datum)
        core.repo_close(repo)


if __name__ == "__main__":
    unittest.main()
