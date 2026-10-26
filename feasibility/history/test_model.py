import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from model import (Adapter, Conflict, FakeService, IDs, Repo, Store, attempt,
                   binding, canonical, choose, event, install, observations,
                   outcome, request)


RUNTIME = Path(__file__).parent / "runtime"


class HistoryTests(unittest.TestCase):
    def setUp(self):
        RUNTIME.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=RUNTIME)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "objects")
        self.repo = Repo(self.store, self.root / "heads.json")
        self.ids = IDs("writer-A")
        self.impl = self.store.put("artifact", {"uri": "file:///synthetic/sum.py",
                                               "version": "sha256:code-v1"})
        self.adapt = self.store.put("artifact", {"version": "adapter-v1"})
        hcl = self.store.put("hcl", 'resource "synthetic_worker" "sum" {}\n')
        self.description = self.store.put("installation-description",
                                         {"execution_config": {"size": "small"}},
                                         {"implementation": self.impl,
                                          "adapter": self.adapt, "hcl": hcl})
        self.installation, self.closure = install(
            self.store, self.ids, self.description,
            {"uri": "file:///synthetic/worker", "version": "worker-v1"},
            {"creation_time": 1, "ip": "192.0.2.1"})
        self.inputs = self.store.put("datum", [4, 7])
        self.bound = binding(self.store, "intent:sum", self.closure, self.inputs)
        self.result = self.store.put("datum", 11)

    def new_attempt(self, req=None):
        req = req or request(self.store, self.ids, self.bound)
        att = attempt(self.store, self.ids, req)
        created = event(self.store, self.ids, att, "registered")
        self.repo.append("main", [created])
        return req, att

    def success(self, att, branch="main", cleanup="success"):
        done = event(self.store, self.ids, att, "done",
                     {"status": "done", "computation": "success", "cleanup": cleanup},
                     {"result": self.result})
        self.repo.append(branch, [done])
        return done

    def select(self, att, branch="main"):
        adoption = event(self.store, self.ids, att, "adopted",
                         {"selection_key": self.bound})
        self.repo.append(branch, [adoption], {self.bound: att})

    def service(self):
        return FakeService(self.root / "service.json")

    def test_content_dedup_but_distinct_occurrences(self):
        q1, a1 = self.new_attempt()
        q2, a2 = self.new_attempt()
        d1, d2 = self.success(a1), self.success(a2)
        self.assertNotEqual(q1, q2)
        self.assertNotEqual(a1, a2)
        self.assertEqual(self.store.get(q1)["refs"], self.store.get(q2)["refs"])
        self.assertEqual(self.store.get(d1)["refs"]["result"],
                         self.store.get(d2)["refs"]["result"])
        self.assertEqual(self.store.put("datum", 11), self.result)

    def test_naive_content_identity_loses_two_trials(self):
        naive1 = self.store.put("execution", refs={"binding": self.bound,
                                                   "result": self.result})
        naive2 = self.store.put("execution", refs={"binding": self.bound,
                                                   "result": self.result})
        self.assertEqual(len({naive1, naive2}), 1)
        _, a1 = self.new_attempt()
        _, a2 = self.new_attempt()
        self.assertEqual(len({a1, a2}), 2)

    def test_allocator_collision_is_not_fixed_by_hashing(self):
        q1 = request(self.store, IDs("same-issuer"), self.bound)
        q2 = request(self.store, IDs("same-issuer"), self.bound)
        self.assertEqual(q1, q2)  # deliberate falsification of undurable allocator
        q3 = request(self.store, IDs("different-issuer"), self.bound)
        self.assertNotEqual(q1, q3)

    def test_reuse_is_not_independent_trial_and_default_off_override(self):
        _, original = self.new_attempt()
        self.success(original)
        self.select(original)
        before = self.repo.heads["main"]
        self.assertIsNone(choose(self.repo, before, self.bound, False))
        self.assertEqual(choose(self.repo, before, self.bound, False,
                                explicit=original), original)
        self.assertEqual(choose(self.repo, before, self.bound, True), original)
        q2 = request(self.store, self.ids, self.bound)
        hit = event(self.store, self.ids, q2, "reuse", refs={"actual_attempt": original,
                                                           "result": self.result})
        self.repo.append("main", [hit])
        reachable = self.store.walk(self.repo.heads["main"])
        self.assertEqual(sum(self.store.get(x)["kind"] == "attempt" for x in reachable), 1)
        _, fresh = self.new_attempt()
        self.success(fresh)
        self.assertNotEqual(fresh, original)
        self.assertEqual(sum(self.store.get(x)["kind"] == "attempt"
                             for x in self.store.walk(self.repo.heads["main"])), 2)

    def test_versioned_intent_policy_and_recorded_request_override(self):
        _, att = self.new_attempt()
        self.success(att)
        self.select(att)
        off = self.store.put("intent-definition", {"uri": "intent:sum", "reuse_default": False})
        on = self.store.put("intent-definition", {"uri": "intent:sum", "reuse_default": True})
        q1 = request(self.store, self.ids, self.bound, policy=off,
                     override={"explicit_attempt": att})
        # Actual execution is a graph edge on the reuse observation, not a string.
        hit = event(self.store, self.ids, q1, "reuse", refs={"actual_attempt": att,
                                                          "result": self.result})
        self.repo.append("main", [hit])
        historical = self.repo.heads["main"]
        q2 = request(self.store, self.ids, self.bound, policy=on)
        current = self.repo.append("main", [event(self.store, self.ids, q2, "requested")])
        self.assertNotEqual(off, on)
        self.assertIn(off, self.store.walk(historical))
        self.assertNotIn(on, self.store.walk(historical))
        self.assertIn(on, self.store.walk(current))
        self.assertEqual(self.store.get(q1)["refs"]["binding"],
                         self.store.get(q2)["refs"]["binding"])
        self.assertIsNone(choose(self.repo, historical, self.bound,
                                 self.store.get(off)["value"]["reuse_default"]))
        self.assertEqual(choose(self.repo, current, self.bound,
                                 self.store.get(on)["value"]["reuse_default"]), att)

    def test_discrepant_fresh_result_is_visible_without_automatic_adoption(self):
        _, original = self.new_attempt()
        self.success(original)
        self.select(original)
        _, fresh = self.new_attempt()
        different = self.store.put("datum", 12)
        done = event(self.store, self.ids, fresh, "done",
                     {"status": "done", "computation": "success", "cleanup": "success"},
                     {"result": different})
        self.repo.append("main", [done])
        self.assertNotEqual(different, self.result)
        self.assertEqual(choose(self.repo, self.repo.heads["main"], self.bound, True), original)
        self.assertEqual(outcome(self.repo, self.repo.heads["main"], fresh), "success")
        self.assertIn(different, self.store.walk(self.repo.heads["main"]))

    def test_fresh_is_not_adoption_and_branch_isolation(self):
        _, a1 = self.new_attempt()
        self.success(a1)
        self.select(a1)
        historical = self.repo.heads["main"]
        self.repo.fork("other")
        self.assertIsNone(choose(self.repo, historical, self.bound, True, fresh=True))
        _, a2 = self.new_attempt()
        self.success(a2)
        self.assertEqual(choose(self.repo, self.repo.heads["main"], self.bound, True), a1)
        self.select(a2)
        self.assertEqual(choose(self.repo, self.repo.heads["main"], self.bound, True), a2)
        self.assertEqual(choose(self.repo, self.repo.heads["other"], self.bound, True), a1)
        self.assertEqual(choose(self.repo, historical, self.bound, True), a1)

    def test_reuse_rejects_unknown_failed_and_wrong_binding(self):
        _, att = self.new_attempt()
        with self.assertRaises(ValueError):
            choose(self.repo, self.repo.heads["main"], self.bound, False, explicit=att)
        self.success(att)
        other = binding(self.store, "intent:sum", self.closure,
                        self.store.put("datum", [3, 8]))
        with self.assertRaises(ValueError):
            choose(self.repo, self.repo.heads["main"], other, False, explicit=att)
        _, failed = self.new_attempt()
        ev = event(self.store, self.ids, failed, "done",
                   {"status": "done", "computation": "failure", "cleanup": "success"})
        self.repo.append("main", [ev])
        with self.assertRaises(ValueError):
            choose(self.repo, self.repo.heads["main"], self.bound, False, explicit=failed)

    def test_installations_same_closure_despite_incidental_outputs(self):
        second, closure = install(self.store, self.ids, self.description,
                                  {"uri": "file:///synthetic/worker", "version": "worker-v1"},
                                  {"creation_time": 2, "ip": "192.0.2.2"})
        self.assertNotEqual(second, self.installation)
        self.assertEqual(closure, self.closure)
        self.assertNotEqual(self.store.get(second)["refs"]["resolved"],
                            self.store.get(self.installation)["refs"]["resolved"])
        third, changed = install(self.store, self.ids, self.description,
                                 {"uri": "file:///synthetic/worker", "version": "worker-v2"}, {})
        self.assertNotEqual(changed, self.closure)
        self.assertNotEqual(third, second)
        self.assertIn(self.description, self.store.walk(self.installation))

    def test_naive_incidental_outputs_invalidate_equal_binding(self):
        resolved1 = self.store.get(self.installation)["refs"]["resolved"]
        second, fixed = install(self.store, self.ids, self.description,
                               {"uri": "file:///synthetic/worker", "version": "worker-v1"},
                               {"creation_time": 999})
        resolved2 = self.store.get(second)["refs"]["resolved"]
        naive1 = self.store.put("naive-closure", refs={"resolved": resolved1})
        naive2 = self.store.put("naive-closure", refs={"resolved": resolved2})
        self.assertNotEqual(naive1, naive2)
        self.assertEqual(fixed, self.closure)
        # Excluding a real execution endpoint is unsafe if it influences behavior.
        _, endpoint_changes = install(self.store, self.ids, self.description,
                                       {"uri": "file:///synthetic/other-worker",
                                        "version": "worker-v1"}, {})
        self.assertNotEqual(endpoint_changes, fixed)

    def test_mutable_name_cannot_identify_artifact_version(self):
        stable = "https://example.invalid/worker/latest"
        naive1 = self.store.put("artifact", {"uri": stable})
        naive2 = self.store.put("artifact", {"uri": stable})
        external_bytes = [b"return 11", b"return 999"]
        self.assertNotEqual(external_bytes[0], external_bytes[1])
        self.assertEqual(naive1, naive2)
        fixed = [self.store.put("artifact", {"uri": stable,
                  "sha256": hashlib.sha256(raw).hexdigest()}) for raw in external_bytes]
        self.assertNotEqual(*fixed)  # no network dereference/integrity guarantee

    def test_one_request_multiple_attempts_unknown_then_success(self):
        q, a1 = self.new_attempt()
        self.assertEqual(outcome(self.repo, self.repo.heads["main"], a1), "unknown")
        _, a2 = self.new_attempt(q)
        self.success(a2)
        self.assertEqual(self.store.get(a1)["refs"]["request"], q)
        self.assertEqual(self.store.get(a2)["refs"]["request"], q)
        self.assertEqual(outcome(self.repo, self.repo.heads["main"], a1), "unknown")
        self.assertEqual(outcome(self.repo, self.repo.heads["main"], a2), "success")

    def test_crash_resume_from_disk_and_idempotent_submission(self):
        _, att = self.new_attempt()
        service = self.service()
        adapter = Adapter(self.repo, self.ids, service)
        with self.assertRaises(RuntimeError):
            adapter.tick("main", att, crash_after_submit=True)
        self.assertEqual(len(service.jobs), 1)
        self.assertEqual(outcome(self.repo, self.repo.heads["main"], att), "unknown")
        # Discard model objects; recover CAS and mutable head from disk.
        repo2 = Repo(Store(self.root / "objects"), self.root / "heads.json")
        service2 = self.service()
        restarted = Adapter(repo2, IDs("restart-B"), service2)
        self.assertEqual(restarted.tick("main", att), "working")
        self.assertEqual(restarted.tick("main", att), "working")
        self.assertEqual(restarted.tick("main", att), "done")
        self.assertEqual(len(service2.jobs), 1)
        self.assertEqual(next(iter(service2.jobs.values()))["executions"], 1)
        self.assertEqual(outcome(repo2, repo2.heads["main"], att), "success")

    def test_bounded_calls_incremental_results_cleanup_failure_remediation(self):
        _, att = self.new_attempt()
        service = self.service()
        adapter = Adapter(self.repo, self.ids, service)
        history = []
        for expected in ["working", "working", "done"]:
            before = service.calls
            status = adapter.tick("main", att, cleanup_succeeds=False)
            self.assertEqual(status, expected)
            self.assertLessEqual(service.calls - before, 1)
            history.append(self.repo.heads["main"])
        phases = [observations(self.repo, h, att) for h in history]
        self.assertEqual([len(p) for p in phases], [2, 3, 4])
        self.assertTrue(any("partial" in n["refs"] for n in phases[1].values()))
        final = next(n for n in phases[2].values() if n["value"]["name"] == "done")
        self.assertEqual(final["value"]["data"]["cleanup"], "failed")
        self.assertEqual(final["refs"]["result"], self.result)
        self.assertEqual(outcome(self.repo, history[-1], att), "success")
        remediation = event(self.store, self.ids, att, "cleanup-remediated",
                            {"cleanup": "success", "job": final["value"]["data"]["job"]})
        self.repo.append("main", [remediation])
        self.assertNotIn(remediation, self.repo.state(history[-1])[0])
        self.assertEqual(outcome(self.repo, self.repo.heads["main"], att), "success")
        self.assertEqual(adapter.tick("main", att), "done")
        self.assertEqual(service.calls, 2)  # no resubmission on remediation

    def test_recorded_computation_failure_is_done_not_unknown(self):
        _, att = self.new_attempt()
        adapter = Adapter(self.repo, self.ids, self.service())
        self.assertEqual(adapter.tick("main", att), "working")
        self.assertEqual(adapter.tick("main", att), "working")
        self.assertEqual(adapter.tick("main", att, fail=True), "done")
        self.assertEqual(outcome(self.repo, self.repo.heads["main"], att), "failure")
        terminal = next(n for n in observations(self.repo, self.repo.heads["main"], att).values()
                        if n["value"]["name"] == "done")
        self.assertNotIn("result", terminal["refs"])
        self.assertEqual(terminal["value"]["data"]["failure"], "executor error")

    def test_progress_acyclic_and_records_immutable(self):
        _, att = self.new_attempt()
        adapter = Adapter(self.repo, self.ids, self.service())
        adapter.tick("main", att)
        old = self.repo.heads["main"]
        adapter.tick("main", att)
        new = self.repo.heads["main"]
        self.assertNotEqual(old, new)
        self.assertEqual(len(observations(self.repo, old, att)), 2)
        self.assertEqual(len(observations(self.repo, new, att)), 3)
        copy = self.store.get(att)
        copy["value"]["occurrence"] = "tampered"
        self.assertNotEqual(self.store.get(att)["value"]["occurrence"], "tampered")
        with self.assertRaises((KeyError, FileNotFoundError)):
            self.store.put("cycle", refs={"self": "not-yet-existing"})
        for cid in self.store.walk(new):
            self.assertNotIn(cid, self.store.get(cid)["refs"].values())

    def test_commit_merge_correlations_and_selection_conflict(self):
        _, a1 = self.new_attempt()
        _, a2 = self.new_attempt()
        self.success(a1)
        self.success(a2)
        base = self.repo.heads["main"]
        el = event(self.store, self.ids, a1, "adopted", {"orchestration": "run:L"})
        er = event(self.store, self.ids, a2, "adopted", {"orchestration": "run:R"})
        left = self.repo.propose(base, [el], {self.bound: a1}, git="synthetic-git:L")
        right = self.repo.propose(base, [er], {self.bound: a2}, git="synthetic-git:R")
        with self.assertRaises(Conflict):
            self.repo.merge(base, left, right)
        merged = self.repo.merge(base, left, right, {self.bound: a2}, git="synthetic-git:M")
        self.assertTrue({el, er}.issubset(self.repo.state(merged)[0]))
        self.assertEqual(self.repo.state(merged)[1][self.bound], a2)
        self.assertEqual(self.store.get(left)["value"]["git"], "synthetic-git:L")
        self.assertEqual(self.store.get(merged)["refs"]["parent:1"], right)
        self.assertTrue({left, right, base}.issubset(self.repo.ancestors(merged)))

    def test_simultaneous_lifecycle_updates_cas_merge_no_observation_loss(self):
        _, att = self.new_attempt()
        base = self.repo.heads["main"]
        e1 = event(self.store, self.ids, att, "working", {"status": "working", "phase": "submitted"})
        e2 = event(self.store, IDs("writer-B"), att, "working",
                   {"status": "working", "phase": "retrieved"})
        left = self.repo.propose(base, [e1])
        right = self.repo.propose(base, [e2])
        self.repo.publish("main", base, left)
        with self.assertRaises(Conflict):
            self.repo.publish("main", base, right)
        merged = self.repo.merge(base, left, right)
        self.repo.publish("main", left, merged)
        self.assertTrue({e1, e2}.issubset(observations(self.repo, merged, att)))
        with self.assertRaises(Conflict):
            Adapter(self.repo, self.ids, self.service()).tick("main", att)
        naive = {"status": "submitted"}
        naive["status"] = "retrieved"
        self.assertEqual(len(naive), 1)  # naive last-writer overwrites one observation

    def test_conflicting_done_observations_preserved_not_certified(self):
        _, att = self.new_attempt()
        self.success(att)
        failure = event(self.store, IDs("writer-B"), att, "done",
                        {"status": "done", "computation": "failure", "cleanup": "success"})
        self.repo.append("main", [failure])
        self.assertEqual(outcome(self.repo, self.repo.heads["main"], att), "conflicting")
        with self.assertRaises(ValueError):
            choose(self.repo, self.repo.heads["main"], self.bound, False, explicit=att)
        self.assertEqual(sum(n["value"]["name"] == "done" for n in
                             observations(self.repo, self.repo.heads["main"], att).values()), 2)

    def test_compute_excision_can_retain_selected_result_but_not_fresh_execution(self):
        _, att = self.new_attempt()
        self.success(att)
        self.select(att)
        resource = self.store.get(self.closure)["refs"]["resource"]
        excision = event(self.store, self.ids, resource, "resource-retired",
                         {"authorized": True, "physical_deletion": "confirmed"})
        self.repo.append("main", [excision])
        head = self.repo.heads["main"]
        self.assertEqual(choose(self.repo, head, self.bound, True), att)
        self.assertIn(self.result, self.store.walk(head))
        available = not any(n["value"]["name"] == "resource-retired" for n in
                            observations(self.repo, head, resource).values())
        self.assertFalse(available)  # freshness now requires reinstall/rebind
        self.assertIn(resource, self.store.walk(head))  # NOT sensitive-content erasure

    def test_hidden_internal_retries_not_counted_by_attempt_id(self):
        _, att = self.new_attempt()
        external_executions = ["provider-job-1", "provider-job-2"]
        hidden = event(self.store, self.ids, att, "done",
                       {"status": "done", "computation": "success", "cleanup": "success"},
                       {"result": self.result})
        self.repo.append("main", [hidden])
        self.assertEqual(len(external_executions), 2)
        self.assertEqual(sum(self.store.get(x)["kind"] == "attempt"
                             for x in self.store.walk(self.repo.heads["main"])), 1)
        # Candidate fix only works if the adapter reports each actual execution.
        executions = [self.store.put("external-execution", {"occurrence": name},
                                     {"attempt": att}) for name in external_executions]
        reported = event(self.store, self.ids, att, "external-accounting",
                         refs={f"execution:{i}": x for i, x in enumerate(executions)})
        self.repo.append("main", [reported])
        self.assertEqual(sum(self.store.get(x)["kind"] == "external-execution"
                             for x in self.store.walk(self.repo.heads["main"])), 2)

    def test_missing_result_and_contradictory_reuse_flags_rejected(self):
        _, att = self.new_attempt()
        incomplete = event(self.store, self.ids, att, "done",
                           {"status": "done", "computation": "success", "cleanup": "success"})
        self.repo.append("main", [incomplete])
        with self.assertRaises(ValueError):
            choose(self.repo, self.repo.heads["main"], self.bound, False, explicit=att)
        with self.assertRaises(ValueError):
            choose(self.repo, self.repo.heads["main"], self.bound, False,
                   explicit=att, fresh=True)

    def test_scenario_fixture_is_reproducible(self):
        from run_scenarios import scenarios
        expected = json.loads((Path(__file__).parent / "scenario-results.json").read_text())
        self.assertEqual(scenarios(), expected)

    def test_disk_corruption_detected(self):
        path = self.root / "objects" / (self.result + ".json")
        path.write_bytes(canonical({"altered": True}))
        fresh_store = Store(self.root / "objects")
        with self.assertRaises(ValueError):
            fresh_store.get(self.result)


if __name__ == "__main__":
    unittest.main()
