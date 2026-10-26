"""Actual persistent, multiprocess tests. No sleeps or pre-existing file deletion."""
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import unittest

from journal import CONTRACT_VERSION, Journal, Rejected

CTX = mp.get_context("spawn")
RUN = None


def receive(pipe):
    if not pipe.poll(15):
        raise AssertionError("bounded process handshake timed out")
    return pipe.recv()


def finish(process, expected=0):
    process.join(15)
    if process.is_alive():
        process.kill()
        process.join(5)
        raise AssertionError("process did not exit")
    if process.exitcode != expected:
        raise AssertionError(f"exit {process.exitcode}, expected {expected}")


def publisher(db, sandbox, pipe, repo, key, name="main", extra=None):
    j = Journal(db, sandbox)
    pipe.send("ready")
    assert pipe.recv() == "go"
    attempts = [("head", lambda: j.head(repo, name, None, key))]
    if extra:
        source, target = extra
        attempts += [("commit", lambda: j.commit(repo, "late", provenance=[target])),
                     ("dependency", lambda: j.dependency(source, target)),
                     ("membership", lambda: j.member("new-member"))]
    outcomes = {}
    for label, fn in attempts:
        try:
            fn()
            outcomes[label] = "accepted"
        except Rejected as e:
            outcomes[label] = str(e)
    pipe.send(outcomes)
    j.close()


def deleter(db, sandbox, pipe, victims, revision):
    j = Journal(db, sandbox)
    pipe.send("ready")
    assert pipe.recv() == "go"
    try:
        ticket = j.reserve(victims, revision, "sha256:race-plan")
        pipe.send({"ticket": ticket})
        assert pipe.recv() == "finish"
        j.recover(ticket)
    except Rejected as e:
        pipe.send({"rejected": str(e)})
    j.close()


def crash_deleter(db, sandbox, pipe, victim, revision, phase):
    j = Journal(db, sandbox)
    victims = victim if isinstance(victim, list) else [victim]
    ticket = j.reserve(victims, revision, "sha256:crash-plan")
    pipe.send(ticket)

    def die():
        pipe.send({"boundary": phase})
        assert pipe.recv() == "exit"
        os._exit(73)  # Real process exit; no exception unwinding/SQLite close.

    if phase == "reservation":
        die()
    j.begin_effect(ticket)
    if phase == "intent":
        die()
    if phase == "unlink":
        sync = j.fsync_directory

        def after_unlink():
            sync()
            die()  # Inside effect's SQLite transaction, after real unlink/fsync.

        j.fsync_directory = after_unlink
    j.effect(ticket)
    if phase == "ack-before-commit":
        bump = j.bump

        def before_commit():
            result = bump()
            die()  # Updates made, but no SQL COMMIT yet.
            return result

        j.bump = before_commit
    j.ack(ticket)
    if phase == "ack-after-commit":
        die()  # Durable acknowledgement but no response to coordinator.
    raise AssertionError("unknown crash boundary")


def crash_creator(db, sandbox, pipe):
    j = Journal(db, sandbox)
    sync = j.fsync_directory

    def after_creation():
        sync()
        pipe.send("created-before-receipt")
        assert pipe.recv() == "exit"
        os._exit(74)

    j.fsync_directory = after_creation
    j.create_file("orphan")


class JournalTests(unittest.TestCase):
    def setUp(self):
        if RUN is None:
            raise RuntimeError("Use the script entry point to allocate a scoped runtime run")
        self.root = Path(tempfile.mkdtemp(prefix=self._testMethodName + "-", dir=RUN))
        self.sandbox = self.root / "files"
        self.sandbox.mkdir()
        self.db = self.root / "journal.sqlite"
        self.j = Journal(self.db, self.sandbox)
        self.j.member("A")
        self.j.member("B")

    def tearDown(self):
        self.j.close()

    def reopen(self):
        self.j.close()
        self.j = Journal(self.db, self.sandbox)

    def spawn(self, fn, *args):
        parent, child = CTX.Pipe()
        p = CTX.Process(target=fn, args=(str(self.db), str(self.sandbox), child, *args))
        p.start()
        child.close()
        return p, parent

    def reservation(self, victims):
        return self.j.reserve(victims, self.j.snapshot()["revision"], "sha256:test-plan")

    def test_new_journal_refuses_nonempty_or_out_of_scope_sandbox(self):
        f = self.j.create_file("owned")
        with self.assertRaisesRegex(Rejected, "fresh empty"):
            Journal(self.root / "new.sqlite", self.sandbox)
        self.assertFalse((self.root / "new.sqlite").exists())
        with self.assertRaisesRegex(Rejected, "runtime root"):
            Journal(self.db, self.sandbox, runtime_root=self.root)
        with self.assertRaisesRegex(Rejected, "selected runtime"):
            Journal(self.db, Path("/"))
        self.assertTrue(Path(self.j.resource(f)["path"]).exists())

    def test_original_identity_overwrite_rejected(self):
        self.j.register_external("bucket", "external:bucket/version1", "bucket-name")
        with self.assertRaises(Rejected):
            self.j.register_external("bucket", "other", "other-name")
        with self.assertRaises(Rejected):
            self.j.create_file("bucket-name")
        self.assertEqual(list(self.sandbox.iterdir()), [])
        with self.assertRaises(Rejected):
            self.j.register_external("duplicate", "external:bucket/version1", "duplicate")
        f = self.j.create_file("file-name")
        with self.assertRaises(Rejected):
            self.j.alias("bucket-name", f)
        with self.assertRaises(Rejected):
            self.j.register_external("different", self.j.resource(f)["physical"], "different")
        with self.assertRaises(sqlite3.IntegrityError):
            with self.j.tx():
                self.j.db.execute("UPDATE resources SET owner='managed' WHERE id='bucket'")
        with self.assertRaises(Rejected):
            self.reservation(["bucket"])
        replacement = self.j.create_file("replacement")
        self.assertNotEqual(f, replacement)
        self.assertEqual(self.j.resource("bucket")["owner"], "external")

    def test_actual_full_history_roots_multiple_heads_and_members(self):
        f = self.j.create_file("artifact")
        self.j.commit("A", "c1", provenance=[f])
        self.j.commit("A", "c2", parents=["c1"])
        self.j.head("A", "main", None, "c2")
        self.j.head("A", "alias", None, "c1")
        self.j.commit("B", "b1", provenance=[f])
        self.j.head("B", "main", None, "b1")
        self.reopen()
        export = self.j.export()
        self.assertEqual(export["commits"], {"A": ["c1", "c2"], "B": ["b1"]})
        self.assertEqual(export["associations"], [f])
        with self.assertRaises(Rejected):
            self.j.commit("A", "c1")
        with self.assertRaises(Rejected):
            self.reservation([f])
        self.j.head("A", "main", "c2", None)
        self.j.head("A", "alias", "c1", None)
        with self.assertRaises(Rejected):
            self.reservation([f])
        self.j.head("B", "main", "b1", None)
        self.assertEqual(self.j.export()["associations"], [])
        self.j.recover(self.reservation([f]))

    def test_withdrawn_new_operational_publication_rejected(self):
        f = self.j.create_file("compute")
        other = self.j.create_file("result")
        self.j.commit("A", "old", operational=[f])
        self.j.commit("B", "queued", operational=[f])
        self.j.head("A", "main", None, "old")
        self.j.excise(f)
        with self.assertRaises(Rejected):
            self.j.dependency(other, f)
        with self.assertRaises(Rejected):
            self.j.commit("A", "bad", operational=[f])
        with self.assertRaises(Rejected):
            self.j.head("B", "main", None, "queued")
        self.j.commit("A", "history", parents=["old"], provenance=[f])
        self.j.head("A", "main", "old", "history")
        self.j.recover(self.reservation([f]))
        self.assertIn(f, self.j.export()["associations"])
        self.j.commit("B", "tombstone", provenance=[f])
        self.j.head("B", "main", None, "tombstone")
        with self.assertRaises(Rejected):
            self.j.commit("B", "bad-after", operational=[f])
        self.j.head("A", "main", "history", None)
        with self.assertRaises(Rejected):
            self.j.head("A", "main", None, "old")

    def test_pending_cleanup_survives_last_head_removal(self):
        cleaner = self.j.create_file("cleaner")
        self.j.adopted(cleaner)
        f = self.j.create_file("pending-artifact", cleanup=cleaner)
        self.j.commit("A", "attempt", provenance=[f])
        self.j.head("A", "main", None, "attempt")
        self.j.head("A", "main", "attempt", None)
        self.reopen()
        self.assertIn(cleaner, self.j.export()["retained"])
        self.assertEqual(self.j.resource(f)["disposed"], 0)
        with self.assertRaises(Rejected):
            self.reservation([cleaner])
        with self.assertRaises(Rejected):
            self.j.excise(cleaner)
        ticket = self.reservation([f])
        self.assertEqual(next(o for o in self.j.obligations() if o["target"] == f)["cleanup"], cleaner)
        with self.assertRaises(Rejected):
            self.j.ack(ticket)
        self.j.begin_effect(ticket)
        with self.assertRaises(Rejected):
            self.j.ack(ticket)
        self.j.effect(ticket)
        self.reopen()
        self.assertIn(cleaner, self.j.export()["retained"])
        self.j.ack(ticket)
        self.assertNotIn(cleaner, self.j.export()["retained"])
        self.j.recover(self.reservation([cleaner]))
        self.assertTrue(all(o["resolved"] for o in self.j.obligations()))
        self.assertEqual(self.j.resource(f)["id"], f)  # sole identity never erased

    def test_adoption_does_not_release_eventual_cleanup_identity(self):
        cleaner = self.j.create_file("cleaner")
        artifact = self.j.create_file("artifact", cleanup=cleaner)
        self.j.adopted(artifact)
        self.reopen()
        obligation = next(o for o in self.j.obligations() if o["target"] == artifact)
        self.assertEqual(obligation["kind"], "managed")
        self.assertEqual(obligation["resolved"], 0)
        with self.assertRaisesRegex(Rejected, "retained"):
            self.reservation([cleaner])
        self.j.recover(self.reservation([artifact]))
        self.j.recover(self.reservation([cleaner]))

    def test_live_dependency_requires_source_disposal_first(self):
        target = self.j.create_file("target")
        source = self.j.create_file("source")
        self.j.dependency(source, target)
        with self.assertRaises(Rejected):
            self.reservation([target])
        with self.assertRaises(Rejected):
            self.j.excise(target)
        self.j.recover(self.reservation([source]))
        self.j.recover(self.reservation([target]))

    def test_unavailable_member_and_stale_plan(self):
        f = self.j.create_file("artifact")
        old = self.j.snapshot()
        self.j.member("B", available=False)
        with self.assertRaisesRegex(Rejected, "unavailable"):
            self.reservation([f])
        self.reopen()
        self.assertFalse(self.j.export()["members"]["B"])
        self.j.member("B", available=True)
        with self.assertRaisesRegex(Rejected, "stale"):
            self.j.reserve([f], old["revision"], "old-plan")
        ticket = self.reservation([f])
        for field, replacement in [("revision", 0), ("plan_digest", "changed-plan"), ("victims", [])]:
            bad = dict(ticket, **{field: replacement})
            with self.assertRaisesRegex(Rejected, "binding"):
                self.j.verify(bad)
        with self.assertRaisesRegex(Rejected, "intent"):
            self.j.effect(ticket)
        self.j.recover(ticket)
        with self.assertRaisesRegex(Rejected, "finished"):
            self.j.verify(ticket)
        self.j.recover(ticket)  # lost acknowledgement response is idempotent

    def test_recorded_identity_blocks_external_file_mutation(self):
        f = self.j.create_file("artifact", b"original")
        ticket = self.reservation([f])
        path = Path(self.j.resource(f)["path"])
        path.write_bytes(b"mutated")  # only this test's newly minted sandbox file
        self.j.begin_effect(ticket)
        with self.assertRaisesRegex(Rejected, "content identity"):
            self.j.effect(ticket)
        self.assertEqual(path.read_bytes(), b"mutated")
        with self.assertRaises(Rejected):
            self.j.ack(ticket)
        self.reopen()
        with self.assertRaisesRegex(Rejected, "fence"):
            self.j.member("C")

    def test_replacement_at_recorded_path_not_deleted(self):
        f = self.j.create_file("artifact")
        ticket = self.reservation([f])
        path = Path(self.j.resource(f)["path"])
        moved = path.with_name(path.name + "-retained-old-inode")
        path.rename(moved)  # keeps old inode alive; prevents accidental inode reuse
        path.write_bytes(b"synthetic")
        self.j.begin_effect(ticket)
        with self.assertRaisesRegex(Rejected, "physical file identity"):
            self.j.effect(ticket)
        self.assertTrue(path.exists())
        self.assertTrue(moved.exists())

    def test_two_publishers_and_deleter_reservation_wins(self):
        f = self.j.create_file("victim")
        other = self.j.create_file("source")
        self.j.commit("A", "a", provenance=[f])
        self.j.commit("B", "b", provenance=[f])
        revision = self.j.snapshot()["revision"]
        p1, c1 = self.spawn(publisher, "A", "a", "main", (other, f))
        p2, c2 = self.spawn(publisher, "B", "b", "main", (other, f))
        d, dc = self.spawn(deleter, [f], revision)
        for c in (c1, c2, dc):
            self.assertEqual(receive(c), "ready")
        dc.send("go")
        ticket = receive(dc)["ticket"]
        self.j.verify(ticket)
        c1.send("go")
        c2.send("go")
        for c in (c1, c2):
            results = receive(c)
            self.assertEqual(set(results), {"head", "commit", "dependency", "membership"})
            self.assertTrue(all("fence" in v for v in results.values()))
        dc.send("finish")
        for p in (p1, p2, d):
            finish(p)
        self.reopen()
        self.assertEqual(self.j.resource(f)["disposed"], 1)
        self.assertEqual(self.j.export()["heads"], {})

    def test_two_publishers_and_deleter_publication_wins(self):
        f = self.j.create_file("victim")
        self.j.commit("A", "a", provenance=[f])
        self.j.commit("B", "b", provenance=[f])
        revision = self.j.snapshot()["revision"]
        p1, c1 = self.spawn(publisher, "A", "a")
        p2, c2 = self.spawn(publisher, "B", "b")
        d, dc = self.spawn(deleter, [f], revision)
        for c in (c1, c2, dc):
            self.assertEqual(receive(c), "ready")
        c1.send("go")
        self.assertEqual(receive(c1)["head"], "accepted")
        c2.send("go")
        self.assertEqual(receive(c2)["head"], "accepted")
        dc.send("go")
        self.assertIn("stale", receive(dc)["rejected"])
        for p in (p1, p2, d):
            finish(p)
        with self.assertRaisesRegex(Rejected, "retained"):
            self.reservation([f])
        self.assertTrue(Path(self.j.resource(f)["path"]).exists())

    def test_atomic_head_cas_two_processes(self):
        self.j.commit("A", "a")
        self.j.commit("A", "b")
        p1, c1 = self.spawn(publisher, "A", "a")
        p2, c2 = self.spawn(publisher, "A", "b")
        for c in (c1, c2):
            self.assertEqual(receive(c), "ready")
        for c in (c1, c2):
            c.send("go")
        results = [receive(c)["head"] for c in (c1, c2)]
        self.assertEqual(results.count("accepted"), 1)
        self.assertEqual(results.count("head CAS conflict"), 1)
        for p in (p1, p2):
            finish(p)
        self.reopen()
        self.assertIn(self.j.export()["heads"]["A"]["main"], ("a", "b"))

    def crash_case(self, phase):
        cleaner = self.j.create_file("cleaner")
        self.j.adopted(cleaner)
        f = self.j.create_file("victim", cleanup=cleaner)
        p, c = self.spawn(crash_deleter, f, self.j.snapshot()["revision"], phase)
        ticket = receive(c)
        self.assertEqual(receive(c), {"boundary": phase})
        c.send("exit")
        finish(p, expected=73)
        self.reopen()
        absent = phase in ("unlink", "ack-before-commit", "ack-after-commit")
        self.assertEqual(not Path(self.j.resource(f)["path"]).exists(), absent)
        acknowledged = phase == "ack-after-commit"
        self.assertEqual(self.j.resource(f)["disposed"], int(acknowledged))
        if not acknowledged:
            self.assertIn(cleaner, self.j.export()["retained"])
            with self.assertRaisesRegex(Rejected, "fence"):
                self.j.commit("B", "late", provenance=[f])
        self.j.recover(ticket)
        self.j.recover(ticket)
        self.assertEqual(self.j.resource(f)["disposed"], 1)
        self.assertNotIn(cleaner, self.j.export()["retained"])
        self.j.commit("B", "after", provenance=[f])
        self.j.head("B", "main", None, "after")
        self.assertIn(f, self.j.export()["associations"])
        self.j.recover(self.reservation([cleaner]))
        (self.root / "crash-observation.json").write_text(json.dumps({
            "phase": phase, "exitcode": p.exitcode, "absent_on_reopen": absent,
            "acknowledged_on_reopen": acknowledged, "recovered": True}, indent=2) + "\n")

    def test_partial_batch_effect_crash_recovers_remaining_victim(self):
        cleaner = self.j.create_file("cleaner")
        victims = [self.j.create_file("first", cleanup=cleaner),
                   self.j.create_file("second", cleanup=cleaner)]
        p, c = self.spawn(crash_deleter, victims, self.j.snapshot()["revision"], "unlink")
        ticket = receive(c)
        self.assertEqual(receive(c), {"boundary": "unlink"})
        c.send("exit")
        finish(p, expected=73)
        self.reopen()
        absent = [not Path(self.j.resource(v)["path"]).exists() for v in victims]
        self.assertEqual(sum(absent), 1)
        self.assertEqual(sum(self.j.resource(v)["disposed"] for v in victims), 0)
        self.assertIn(cleaner, self.j.export()["retained"])
        self.j.recover(ticket)
        self.assertTrue(all(not Path(self.j.resource(v)["path"]).exists() for v in victims))
        self.assertNotIn(cleaner, self.j.export()["retained"])
        self.j.recover(self.reservation([cleaner]))
        (self.root / "crash-observation.json").write_text(json.dumps({
            "phase": "partial-batch-unlink", "exitcode": p.exitcode,
            "absent_count_on_reopen": sum(absent), "recovered": True}, indent=2) + "\n")

    def test_creation_crash_keeps_registered_intent_until_receipt(self):
        p, c = self.spawn(crash_creator)
        self.assertEqual(receive(c), "created-before-receipt")
        c.send("exit")
        finish(p, expected=74)
        self.reopen()
        self.assertEqual(len(list(self.sandbox.iterdir())), 1)
        obligations = self.j.obligations()
        self.assertEqual(len(obligations), 1)
        f = obligations[0]["target"]
        self.assertEqual(obligations[0]["kind"], "creation")
        self.assertIsNone(self.j.resource(f)["dev"])
        self.assertEqual(self.j.creation(f)["status"], "creating")
        self.assertEqual(self.j.reconcile_creation(f)["status"], "received")
        self.assertIsNotNone(self.j.resource(f)["dev"])
        (self.root / "crash-observation.json").write_text(json.dumps({
            "phase": "creation-before-receipt", "exitcode": p.exitcode,
            "unregistered_orphan_count": 0, "recovered": True}, indent=2) + "\n")

    def test_crash_reservation(self):
        self.crash_case("reservation")

    def test_crash_intent(self):
        self.crash_case("intent")

    def test_crash_inside_effect_after_unlink(self):
        self.crash_case("unlink")

    def test_crash_ack_transaction_before_commit(self):
        self.crash_case("ack-before-commit")

    def test_crash_after_ack_commit_before_response(self):
        self.crash_case("ack-after-commit")


if __name__ == "__main__":
    runtime = Path(__file__).parent / "runtime"
    runtime.mkdir(exist_ok=True)
    runs = list(runtime.glob("run-*"))
    if len(runs) >= 8:
        raise SystemExit("Eight runs retained; inspect/archive before another run. No auto-pruning.")
    RUN = Path(tempfile.mkdtemp(prefix="run-", dir=runtime)).resolve()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(JournalTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    evidence = {"version": CONTRACT_VERSION, "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version, "platform": platform.platform(),
                "run": str(RUN), "tests": result.testsRun,
                "failures": len(result.failures), "errors": len(result.errors),
                "success": result.wasSuccessful(),
                "crashes": [json.loads(p.read_text()) for p in sorted(RUN.glob("*/crash-observation.json"))]}
    (RUN / "results.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    sys.exit(not result.wasSuccessful())
