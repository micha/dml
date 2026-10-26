"""Run baseline plus focused immutable-history and creation-intent experiments."""
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import unittest

import test_journal as baseline
from journal import CONTRACT_VERSION, Journal, Rejected, encode, validate_chain
from test_journal import JournalTests, receive, finish


def delayed_creator(db, sandbox, pipe, identity):
    j = Journal(db, sandbox)
    tx = j.tx

    @contextmanager
    def controlled_tx(write=True, event="projection-change"):
        if event == "creation-external-effect":
            pipe.send("dispatch-committed-before-effect")
            assert pipe.recv() == "resume"
        with tx(write=write, event=event):
            yield

    j.tx = controlled_tx
    pipe.send(j.realize_creation(identity, b"synthetic"))
    j.close()


def creation_crash(db, sandbox, pipe, cleanup, phase):
    j = Journal(db, sandbox)
    identity = j.creation_intent("pending", b"followup synthetic", cleanup)
    pipe.send(identity)

    def die():
        pipe.send({"boundary": phase})
        assert pipe.recv() == "exit"
        os._exit(75)

    if phase == "intent":
        die()
    if phase == "file-fsync":
        sync = j.fsync_directory

        def synced():
            sync()
            die()

        j.fsync_directory = synced
    if phase == "receipt-before-commit":
        append = j._append_history

        def appended(projection, event):
            append(projection, event)
            if event == "creation-observation":
                die()  # Receipt AND history inserted, but neither committed.

        j._append_history = appended
    j.realize_creation(identity, b"followup synthetic")
    raise AssertionError("unrecognized crash boundary")


class FollowupTests(JournalTests):
    def observation(self, value):
        (self.root / "followup-observation.json").write_text(json.dumps(value, indent=2) + "\n")

    def pending_crash(self, phase):
        cleaner = self.j.create_file("cleaner")
        p, c = self.spawn(creation_crash, cleaner, phase)
        identity = receive(c)
        self.assertEqual(receive(c), {"boundary": phase})
        c.send("exit")
        finish(p, expected=75)
        self.reopen()
        self.assertIsNone(self.j.resource(identity)["dev"])
        self.assertIn(cleaner, self.j.export()["retained"])
        self.assertEqual(next(o for o in self.j.obligations() if o["target"] == identity)["kind"], "creation")
        with self.assertRaises(Rejected):
            self.j.create_file("pending")
        with self.assertRaises(Rejected):
            self.j.register_external(identity, "other", "other")
        with self.assertRaises(Rejected):
            self.reservation([identity])
        with self.assertRaises(Rejected):
            self.reservation([cleaner])
        with self.assertRaises(Rejected):
            self.j.commit("A", "pending-operational", operational=[identity])
        return identity, cleaner, p.exitcode

    def test_followup_creation_intent_exit_absence_and_explicit_replay(self):
        f, cleaner, code = self.pending_crash("intent")
        self.assertFalse(Path(self.j.resource(f)["path"]).exists())
        result = self.j.reconcile_creation(f)
        self.assertEqual(result["status"], "absent")
        absent_history = self.j.history()[-1]
        with self.assertRaisesRegex(Rejected, "digest mismatch"):
            self.j.realize_creation(f, b"wrong")
        self.j.realize_creation(f, b"followup synthetic")
        self.assertEqual(self.j.creation(f)["status"], "received")
        self.assertEqual(self.j.history_at(absent_history["hash"]), absent_history)
        self.j.recover(self.reservation([f]))
        self.j.recover(self.reservation([cleaner]))
        self.observation({"phase": "creation-intent", "exitcode": code,
                          "absent_was_unknown": True, "replayed_explicitly": True,
                          "invisible_orphans": 0, "recovered": True})

    def test_followup_creation_fsync_exit_matching_receipt_recovery(self):
        f, cleaner, code = self.pending_crash("file-fsync")
        st = Path(self.j.resource(f)["path"]).stat()
        self.assertEqual(self.j.reconcile_creation(f)["status"], "received")
        self.assertEqual(self.j.resource(f)["ino"], st.st_ino)
        self.reopen()
        self.assertEqual(self.j.creation(f)["status"], "received")
        self.j.recover(self.reservation([f]))
        self.j.recover(self.reservation([cleaner]))
        self.observation({"phase": "creation-file-fsync", "exitcode": code,
                          "matching_receipt": True, "invisible_orphans": 0, "recovered": True})

    def test_followup_receipt_and_history_crash_roll_back_together(self):
        f, cleaner, code = self.pending_crash("receipt-before-commit")
        self.assertEqual(self.j.creation(f)["status"], "creating")
        previous = self.j.history()[-1]
        self.assertEqual(previous["event"], "creation-dispatch-intent")
        self.assertFalse(any(r["target"] == f and r["status"] == "received"
                             for e in self.j.history() for r in e["projection"]["creations"]))
        self.j.reconcile_creation(f)
        self.assertEqual(self.j.history_at(previous["hash"]), previous)
        self.j.recover(self.reservation([f]))
        self.j.recover(self.reservation([cleaner]))
        self.observation({"phase": "creation-receipt-before-commit", "exitcode": code,
                          "receipt_and_history_rolled_back": True, "recovered": True})

    def test_followup_mutation_after_creation_crash_is_quarantined(self):
        f, cleaner, code = self.pending_crash("file-fsync")
        path = Path(self.j.resource(f)["path"])
        path.write_bytes(b"partial or externally mutated")
        result = self.j.reconcile_creation(f)
        self.assertEqual(result["status"], "quarantined")
        snapshot = self.j.history()[-1]
        self.reopen()
        self.assertEqual(self.j.creation(f)["status"], "quarantined")
        with self.assertRaisesRegex(Rejected, "quarantined"):
            self.j.realize_creation(f, b"followup synthetic")
        self.assertEqual(self.j.history_at(snapshot["hash"]), snapshot)
        self.assertEqual(path.read_bytes(), b"partial or externally mutated")
        self.assertIn(cleaner, self.j.export()["retained"])
        self.observation({"phase": "creation-mutated-after-crash", "exitcode": code,
                          "quarantined": True, "file_preserved": True, "cleanup_pinned": True,
                          "recovered": False})

    def test_followup_unsafe_creation_paths_preserved_and_quarantined(self):
        target = self.j.create_file("link-source", b"link-source")
        original = Path(self.j.resource(target)["path"])
        for kind in ("symlink", "hardlink", "directory", "fifo"):
            with self.subTest(kind=kind):
                f = self.j.creation_intent(kind)
                path = Path(self.j.resource(f)["path"])
                if kind == "symlink":
                    path.symlink_to(original)
                elif kind == "hardlink":
                    os.link(original, path)
                elif kind == "directory":
                    path.mkdir()
                else:
                    os.mkfifo(path, 0o600)
                self.assertEqual(self.j.reconcile_creation(f)["status"], "quarantined")
                self.assertTrue(os.path.lexists(path))
                self.assertIsNone(self.j.resource(f)["dev"])
        self.assertEqual(original.read_bytes(), b"link-source")

    def test_followup_before_receipt_same_bytes_replacement_is_indistinguishable(self):
        f, cleaner, code = self.pending_crash("file-fsync")
        path = Path(self.j.resource(f)["path"])
        prior_inode = path.stat().st_ino
        moved = path.with_name(path.name + "-old-unreceipted")
        path.rename(moved)
        path.write_bytes(b"followup synthetic")
        self.assertNotEqual(path.stat().st_ino, prior_inode)
        self.assertEqual(self.j.reconcile_creation(f)["status"], "received")
        self.assertNotEqual(self.j.resource(f)["ino"], prior_inode)
        self.assertTrue(moved.exists())
        self.observation({"phase": "identical-bytes-pre-receipt-replacement", "exitcode": code,
                          "replacement_accepted": True, "prior_inode_unknowable_from_intent": True,
                          "old_file_preserved": True, "limitation": "cooperative capability ownership assumed"})

    def test_followup_delayed_creation_cannot_recreate_after_disposal(self):
        f = self.j.creation_intent("delayed")
        p, c = self.spawn(delayed_creator, f)
        self.assertEqual(receive(c), "dispatch-committed-before-effect")
        self.j.realize_creation(f, b"synthetic")
        self.j.recover(self.reservation([f]))
        path = Path(self.j.resource(f)["path"])
        self.assertFalse(path.exists())
        c.send("resume")
        self.assertEqual(receive(c)["status"], "received")  # historical completion, not readiness
        finish(p)
        self.reopen()
        self.assertFalse(path.exists())
        self.assertEqual(self.j.resource(f)["disposed"], 1)
        self.observation({"kind": "delayed-creation-vs-disposal",
                          "barrier_controlled": True, "recreated_disposed_identity": False})

    def test_followup_pending_creation_blocked_by_destruction_fence(self):
        f = self.j.create_file("victim")
        pending = self.j.creation_intent("pending")
        ticket = self.reservation([f])
        for fn in (lambda: self.j.realize_creation(pending, b"synthetic"),
                   lambda: self.j.reconcile_creation(pending)):
            with self.assertRaisesRegex(Rejected, "fence"):
                fn()
        self.assertFalse(Path(self.j.resource(pending)["path"]).exists())
        self.j.recover(ticket)
        self.j.realize_creation(pending, b"synthetic")
        self.assertEqual(self.j.creation(pending)["status"], "received")

    def test_followup_prior_state_and_ticket_outcomes_inspectable(self):
        f = self.j.create_file("first")
        self.j.commit("A", "old", operational=[f])
        self.j.head("A", "main", None, "old")
        retained = self.j.history()[-1]
        self.j.adopted(f)
        self.j.head("A", "main", "old", None)
        ticket = self.reservation([f])
        reserved = self.j.history()[-1]
        self.j.begin_effect(ticket)
        intent = self.j.history()[-1]
        self.j.effect(ticket)
        self.j.ack(ticket)
        finished = self.j.history()[-1]
        g = self.j.create_file("second")
        self.j.recover(self.reservation([g]))
        self.j.member("B", available=False)
        self.reopen()
        for original in (retained, reserved, intent, finished):
            self.assertEqual(self.j.history_at(original["hash"]), original)
        self.assertEqual(retained["projection"]["heads"], [{"repo": "A", "name": "main", "tip": "old"}])
        outcomes = [e["projection"]["tickets"][0]["status"] for e in (reserved, intent, finished)]
        self.assertEqual(outcomes, ["reserved", "intent", "acknowledged"])
        self.assertEqual(self.j.resource(f)["disposed"], 1)
        self.assertGreater(self.j.validate_history()["count"], finished["sequence"])
        self.observation({"kind": "immutable-history", "prior_head_preserved": True,
                          "prior_ticket_states": outcomes, "snapshots": self.j.validate_history()["count"]})

    def test_followup_history_cannot_update_delete_or_replace(self):
        entry = self.j.history()[0]
        row = self.j.db.execute("SELECT * FROM history WHERE sequence=1").fetchone()
        self.assertEqual(self.j.db.execute("PRAGMA recursive_triggers").fetchone()[0], 1)
        sqls = [("UPDATE history SET body='changed' WHERE sequence=1", ()),
                ("DELETE FROM history WHERE sequence=1", ()),
                ("INSERT OR REPLACE INTO history VALUES (?,?,?,?)", tuple(row))]
        for sql, args in sqls:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                with self.j.tx():
                    self.j.db.execute(sql, args)
        self.reopen()
        self.assertEqual(self.j.history_at(entry["hash"]), entry)
        detached = self.j.history_at(entry["hash"])
        detached["projection"]["members"].append({"repo": "invented", "available": 1})
        self.assertEqual(self.j.history_at(entry["hash"]), entry)

    def test_followup_history_hash_parent_and_sequence_validation(self):
        entries = self.j.history()
        self.assertEqual(validate_chain(entries), entries[-1]["hash"])
        wrong = copy.deepcopy(entries)
        wrong[0]["event"] = "altered"
        with self.assertRaisesRegex(Rejected, "hash"):
            validate_chain(wrong)
        wrong = copy.deepcopy(entries)
        wrong[-1]["parent"] = None
        body = {k: v for k, v in wrong[-1].items() if k != "hash"}
        wrong[-1]["hash"] = hashlib.sha256(encode(body).encode()).hexdigest()
        with self.assertRaisesRegex(Rejected, "parent"):
            validate_chain(wrong)
        with self.assertRaisesRegex(Rejected, "sequence"):
            validate_chain(entries[1:])

    def test_followup_snapshot_failure_rolls_back_successful_projection_change(self):
        before = self.j.history()
        append = self.j._append_history

        def fail_after_append(projection, event):
            append(projection, event)
            raise Rejected("snapshot persistence failure")

        self.j._append_history = fail_after_append
        with self.assertRaisesRegex(Rejected, "snapshot persistence"):
            self.j.member("not-committed")
        self.j._append_history = append
        self.reopen()
        self.assertEqual(self.j.history(), before)
        self.assertNotIn("not-committed", self.j.export()["members"])

    def test_followup_rejections_and_idempotent_recovery_append_no_false_changes(self):
        f = self.j.create_file("victim")
        before = self.j.history()
        with self.assertRaises(Rejected):
            self.j.create_file("victim")
        self.assertEqual(self.j.history(), before)
        t = self.reservation([f])
        self.j.recover(t)
        after = self.j.history()
        self.j.recover(t)
        self.assertEqual(self.j.history(), after)

    def test_followup_reopen_rejects_naive_invalid_appended_history(self):
        entries = self.j.history()
        last = entries[-1]
        malformed = {k: v for k, v in last.items() if k != "hash"}
        malformed["sequence"] += 1
        malformed["parent"] = last["hash"]
        # Deliberate privileged append in this test's own DB, not an API operation.
        # Reopen detects naive tampering, but cannot authenticate a whole-chain rewrite.
        with sqlite3.connect(self.db) as raw:
            raw.execute("INSERT INTO history VALUES (?,?,?,?)",
                        (malformed["sequence"], "bad-hash", last["hash"], encode(malformed)))
        with self.assertRaisesRegex(Rejected, "hash"):
            self.reopen()

    def test_followup_legacy_database_not_silently_migrated(self):
        db = self.root / "legacy.sqlite"
        sandbox = self.root / "legacy-files"
        sandbox.mkdir()
        with sqlite3.connect(db) as raw:
            raw.execute("CREATE TABLE meta (key TEXT PRIMARY KEY,value TEXT)")
            raw.execute("INSERT INTO meta VALUES ('version','journal-v1')")
        with self.assertRaisesRegex(Rejected, "no implicit"):
            Journal(db, sandbox)
        with sqlite3.connect(db) as raw:
            self.assertIsNone(raw.execute("SELECT 1 FROM sqlite_master WHERE name='history'").fetchone())


if __name__ == "__main__":
    runtime = Path(__file__).parent / "runtime"
    runtime.mkdir(exist_ok=True)
    if len(list(runtime.glob("followup-run-*"))) >= 8:
        raise SystemExit("Eight follow-up runs retained; inspect/archive before another run")
    run = Path(tempfile.mkdtemp(prefix="followup-run-", dir=runtime)).resolve()
    baseline.RUN = run
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(JournalTests)
    names = sorted(n for n in dir(FollowupTests) if n.startswith("test_followup_"))
    suite.addTests(FollowupTests(n) for n in names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    evidence = {"version": CONTRACT_VERSION, "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version, "platform": platform.platform(), "run": str(run),
                "tests": result.testsRun, "baseline_tests": 20, "focused_tests": len(names),
                "failures": len(result.failures), "errors": len(result.errors), "success": result.wasSuccessful(),
                "baseline_crashes": [json.loads(p.read_text()) for p in sorted(run.glob("*/crash-observation.json"))],
                "followup_observations": [json.loads(p.read_text()) for p in sorted(run.glob("*/followup-observation.json"))]}
    (run / "results.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    sys.exit(not result.wasSuccessful())
