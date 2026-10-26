"""Run: python3 -B feasibility/retention/test_model.py

Only synthetic files under runtime/ are written/deleted. JSONL traces contain
expected failures of deliberately naive algorithms, not failing test results.
"""
import itertools
import json
from pathlib import Path
import sys
import unittest

from model import Manager, Unsafe

BASE = Path(__file__).resolve().parent
TRACE = []


def event(scenario, **data):
    TRACE.append({"scenario": scenario, **data})


class Scenarios(unittest.TestCase):
    def setUp(self):
        self.m = Manager(BASE / "runtime" / self._testMethodName)

    def assertBlocked(self, fn, *args, **kwargs):
        with self.assertRaises(Unsafe) as cm:
            fn(*args, **kwargs)
        event(self._testMethodName, blocked=str(cm.exception))

    def test_01_history_all_heads_and_classes(self):
        m = self.m
        m.add("bucket", "external")
        m.add("compute", "provisioned")
        m.add("object", "adopted", deps={"bucket"}, container="bucket")
        m.alias("datum-one", "object")
        m.alias("datum-two", "object")
        m.publish("A", "a0", datums=["compute", "datum-one"])
        m.publish("A", "a1", parents=["a0"], datums=[])
        m.publish("A", "side", datums=["object"], head="unmerged")
        m.publish("B", "b0", datums=["datum-two"])
        self.assertEqual(m.plan().victims, frozenset())
        # Naive current-snapshot collector loses historical compute.
        current = {m.aliases[d] for r in m.repos.values() for c in r.heads.values()
                   for d in r.commits[c].datums}
        self.assertNotIn("compute", current)
        self.assertIn("compute", m.retained())
        m.move_head("A", "main", None)
        self.assertEqual(m.plan().victims, {"compute"})
        m.move_head("A", "unmerged", None)
        self.assertNotIn("object", m.plan().victims)  # B alias still owns object
        m.move_head("B", "main", None)
        p = m.plan()
        self.assertEqual(p.victims, {"compute", "object"})
        m.reserve(p)
        m.destroy_reserved()
        m.assert_safety()
        self.assertTrue((m.sandbox / "bucket.object").exists())
        event(self._testMethodName, historical_only="compute", aliases=2,
              deletion_order=[e["deleted"] for e in m.audit], external_container_survives=True)

    def test_02_dependency_closure_key_and_storage(self):
        m = self.m
        m.add("storage", "provisioned")
        m.add("key", "provisioned")
        m.add("artifact", "adopted", deps={"storage", "key"})
        m.publish("A", "a", datums=["artifact"])
        naive = set(m.resources) - m.history("A")
        self.assertEqual(naive, {"storage", "key"})
        self.assertEqual(m.plan().victims, set())
        m.move_head("A", "main", None)
        m.reserve(m.plan())
        m.destroy_reserved()
        self.assertEqual(m.audit[0], {"deleted": "artifact"})
        m.assert_safety()
        event(self._testMethodName, naive_would_delete=sorted(naive),
              safe_order=[x["deleted"] for x in m.audit])

    def test_03_audit_is_not_root(self):
        m = self.m
        m.add("old", "provisioned")
        m.publish("A", "a", datums=["old"])
        m.audit.append({"created": "old", "research_commit": "a"})
        m.move_head("A", "main", None)
        self.assertEqual(m.plan().victims, {"old"})
        m.reserve(m.plan())
        m.destroy_reserved()
        self.assertEqual(len(m.audit), 2)
        m.assert_safety()
        event(self._testMethodName, audit_entries=2, research_roots=0, collectible=True)

    def test_04_pending_adoption_drop_retry_cleanup_identity(self):
        m = self.m
        m.add("identity", "provisioned")
        m.add("result", "adopted", cleaner="identity", registered=False)
        m.start_adoption("result", "identity")  # durable before dropping research
        m.publish("A", "a", datums=["result"])
        m.move_head("A", "main", None)
        self.assertEqual(m.plan().victims, set())
        self.assertEqual(m.history("A"), set())
        m.reconcile("result", fail=True)
        self.assertIn("result", m.state.values())
        self.assertEqual(m.obligations["result"].failures, 1)
        m.assert_safety()
        m.reconcile("result", fail=True)
        self.assertEqual(m.obligations["result"].failures, 2)
        m.assert_safety()
        m.reconcile("result")
        self.assertFalse(m.obligations)
        self.assertEqual(m.plan().victims, {"identity"})
        m.reserve(m.plan())
        m.destroy_reserved()
        m.assert_safety()
        event(self._testMethodName, phases=["pending-adoption", "cleanup-failed",
              "cleanup-failed", "confirmed-absent", "identity-collected"], old_history_rooted=False)

    def test_05_naive_cleanup_identity_first_breaks_recovery(self):
        m = self.m
        m.add("identity", "provisioned")
        m.add("result", "adopted", registered=False)
        m.start_adoption("result", "identity")
        m._unlink("identity")  # bypass journal roots: deliberately unsafe
        self.assertBlocked(m.reconcile, "result")
        with self.assertRaisesRegex(AssertionError, "cleanup"):
            m.assert_safety()
        event(self._testMethodName, counterexample="unrooted research != no disposal obligation")

    def test_06_unavailable_or_unseen_repository(self):
        m = self.m
        m.add("shared", "provisioned")
        m.publish("B", "b", datums=["shared"])
        naive_a_only = set(m.resources) - m.history("A")
        self.assertEqual(naive_a_only, {"shared"})
        m.repos["B"].available = False
        self.assertBlocked(m.plan)
        m.repos["B"].available = True
        m.membership_complete = False
        self.assertBlocked(m.plan)
        m.membership_complete = True
        self.assertEqual(m.plan().victims, set())
        event(self._testMethodName, naive_a_only=sorted(naive_a_only),
              limitation="the model cannot discover a repository never registered")

    def test_07_stale_plan_and_check_delete_race(self):
        m = self.m
        m.add("object", "adopted")
        p = m.plan()
        self.assertEqual(p, m.plan())  # even immediate revalidation is insufficient
        m.publish("B", "b", datums=["object"])  # race after check/approval
        m.naive_destroy(p)
        with self.assertRaisesRegex(AssertionError, "deleted retained"):
            m.assert_safety()
        event(self._testMethodName, order=["plan", "approve/revalidate", "publish B", "delete"],
              lost_retained_resource="object")

    def test_08_fence_all_six_interleavings(self):
        outcomes = []
        for i, order in enumerate(itertools.permutations(["publish", "reserve", "destroy"])):
            m = Manager(self.m.sandbox / str(i))
            m.add("object", "adopted")
            p = m.plan()
            blocked = []
            for op in order:
                try:
                    if op == "publish":
                        m.publish("B", "b", datums=["object"])
                    elif op == "reserve":
                        m.reserve(p)
                    else:
                        m.destroy_reserved()
                except Unsafe as e:
                    blocked.append(f"{op}: {e}")
                m.assert_safety()
            outcomes.append({"order": order, "blocked": blocked, "deleted": sorted(m.deleted)})
        event(self._testMethodName, interleavings=outcomes, invariants_passed=6)

    def test_09_fence_covers_recovery_and_export_publishers(self):
        m = self.m
        m.add("identity", "provisioned")
        m.add("object", "adopted", cleaner="identity")
        m.reserve(m.plan())
        self.assertBlocked(m.start_adoption, "object", "identity")
        self.assertBlocked(m.add_export, "remote", {"object"})
        m.destroy_reserved()
        self.assertEqual([x["deleted"] for x in m.audit], ["object", "identity"])
        m.assert_safety()

    def test_10_retirement_shared_consumers_cache_and_provenance(self):
        m = self.m
        m.add("compute", "provisioned")
        m.add("artifact", "adopted")  # provenance edge, not runtime dependency on compute
        m.publish("A", "a", datums=["compute", "artifact"])
        m.publish("B", "b", datums=["compute"])
        before = m.repos["A"].commits["a"]
        self.assertBlocked(m.excise, {"compute"}, {"A"})
        m.excise({"compute"}, {"A", "B"})
        self.assertEqual(m.plan().victims, {"compute"})
        m.reserve(m.plan())
        m.destroy_reserved()
        self.assertEqual(before, m.repos["A"].commits["a"])
        self.assertFalse(m.available("compute"))
        self.assertTrue(m.available("artifact"))
        m.assert_safety()
        event(self._testMethodName, compute="tombstone", artifact_cache="available",
              closure_execution="unavailable", historical_commit="unchanged")

    def test_11_excision_key_requires_cascade_or_reencrypt(self):
        m = self.m
        m.add("key", "provisioned")
        m.add("storage", "provisioned")
        m.add("artifact", "adopted", deps={"key", "storage"})
        m.publish("A", "a", datums=["artifact"])
        m.publish("B", "b", datums=["artifact"])
        self.assertBlocked(m.excise, {"key"}, {"A", "B"})
        m.excise({"key", "artifact"}, {"A", "B"})
        self.assertFalse(m.available("artifact"))
        m.reserve(m.plan())
        m.destroy_reserved()
        m.assert_safety()
        event(self._testMethodName, key_only="rejected", cascade="approved explicitly",
              artifact_cache="unavailable", alternative="new verified re-encrypted artifact")

    def test_12_erasure_not_just_tombstone_or_new_commit(self):
        m = self.m
        m.add("sensitive", "adopted")
        m.publish("A", "a", datums=["sensitive"])
        m.publish("B", "b", datums=["sensitive"])
        m.copies["sensitive"] = {"A:old-datum": b"FAKE SECRET", "B:cache": b"FAKE SECRET"}
        m.uncontrolled_copies["offline-export"] = b"FAKE SECRET"
        m.excise({"sensitive"}, {"A", "B"}, erase=True)
        self.assertEqual(len(m.copies["sensitive"]), 2)  # tombstone alone didn't erase
        m.erase_controlled("sensitive")
        m.reserve(m.plan())
        m.destroy_reserved()
        m.assert_safety()
        self.assertTrue(m.uncontrolled_copies)  # intentionally outside guarantee
        event(self._testMethodName, tombstone=m.tombstones["sensitive"],
              controlled_copies_erased=2, uncontrolled_copy_survives=True,
              guarantee="controlled synthetic copies only, not global erasure")

    def test_13_external_excision_forbidden(self):
        m = self.m
        m.add("bucket", "external")
        m.add("object", "adopted", container="bucket", deps={"bucket"})
        m.publish("A", "a", datums=["object"])
        self.assertBlocked(m.excise, {"bucket"}, {"A"})
        m.excise({"object"}, {"A"})
        m.reserve(m.plan())
        m.destroy_reserved()
        m.assert_safety()
        self.assertTrue((m.sandbox / "bucket.object").exists())

    def test_14_config_regeneration_preserves_operational_mapping(self):
        m = self.m
        m.add("physical-object-17", "adopted")
        m.alias("stable-datum", "physical-object-17")
        m.publish("A", "a", datums=["stable-datum"])
        m.state = {"module.closure.result": "physical-object-17"}
        m.save_state()
        expected = dict(m.regenerate())
        m.config.clear()
        self.assertEqual(m.regenerate(), expected)
        # Negative control: configuration regeneration alone cannot restore state.
        m.state.clear()
        self.assertEqual(m.regenerate(), {})
        self.assertTrue((m.sandbox / "physical-object-17.object").exists())
        m.load_state()
        self.assertEqual(m.regenerate(), expected)
        m.assert_safety()
        event(self._testMethodName, stable_mapping=expected, config_only_recovery="insufficient",
              operational_state_reload="restored")

    def test_15_remote_export_extends_ownership_scope(self):
        m = self.m
        m.add("object", "adopted")
        m.publish("A", "a", datums=["object"])
        m.add_export("worker-result-ref", {"object"})
        m.move_head("A", "main", None)
        self.assertEqual(m.plan().victims, set())
        self.assertBlocked(m.excise, {"object"}, {"A", "B"})
        m.excise({"object"}, {"export:worker-result-ref"})
        m.reserve(m.plan())
        m.destroy_reserved()
        m.assert_safety()
        event(self._testMethodName, repo_heads=0, export_root=True,
              needed_authority="export:worker-result-ref")

    def test_17_missing_write_ahead_journal_loses_obligation(self):
        m = self.m
        m.add("identity", "provisioned")
        m.add("result", "adopted", registered=False)
        m.publish("A", "a", datums=["result"])
        m.move_head("A", "main", None)
        # Synthetic creation was observed by this omniscient model, but a
        # configuration/state-only reconciler knows neither ID nor obligation.
        discovered = set(m.state.values()) | m.recovery_roots() | m.retained()
        self.assertNotIn("result", discovered)
        self.assertTrue((m.sandbox / "result.object").exists())
        event(self._testMethodName, counterexample="creation before durable identity recording",
              result="undiscoverable to config/state-only reconciler",
              caveat="omniscient model still knows resource; real adapter may not")

    def test_18_adoption_transfers_to_retained_owner(self):
        m = self.m
        m.add("identity", "provisioned")
        m.add("result", "adopted", cleaner="identity", registered=False)
        m.start_adoption("result", "identity")
        m.publish("A", "a", datums=["result"])
        m.reconcile("result")
        self.assertFalse(m.obligations)
        self.assertEqual(m.plan().victims, set())
        m.assert_safety()
        m.move_head("A", "main", None)
        m.reserve(m.plan())
        m.destroy_reserved()
        m.assert_safety()
        self.assertEqual([x["deleted"] for x in m.audit], ["result", "identity"])
        event(self._testMethodName, adoption="transferred to research retention",
              later_disposal_order=[x["deleted"] for x in m.audit])

    def test_19_namespace_mutations_fenced(self):
        m = self.m
        m.add("object", "adopted")
        m.reserve(m.plan())
        self.assertBlocked(m.alias, "late", "object")
        self.assertBlocked(m.add, "new", "provisioned")
        self.assertBlocked(m.excise, {"object"}, set())
        m.destroy_reserved()
        m.assert_safety()

    def test_20_bounded_dependency_graph_and_two_repo_census(self):
        nodes = ["key", "storage", "artifact"]
        edges = [("storage", "key"), ("artifact", "key"), ("artifact", "storage")]
        cases = 0
        for graph_mask, a_mask, b_mask in itertools.product(range(8), repeat=3):
            m = Manager(self.m.sandbox / str(cases))
            deps = {n: set() for n in nodes}
            for bit, (dependent, prerequisite) in enumerate(edges):
                if graph_mask & (1 << bit):
                    deps[dependent].add(prerequisite)
            for n in nodes:
                m.add(n, "adopted" if n == "artifact" else "provisioned", deps=deps[n])
            roots = set()
            for repo, mask in [("A", a_mask), ("B", b_mask)]:
                chosen = [n for bit, n in enumerate(nodes) if mask & (1 << bit)]
                roots.update(chosen)
                m.publish(repo, "c", datums=chosen)
            # Independent fixed-point oracle, not Manager.closure.
            expected = set(roots)
            while True:
                expanded = expected | set().union(*(deps[n] for n in expected))
                if expanded == expected:
                    break
                expected = expanded
            self.assertEqual(m.retained(), expected)
            self.assertEqual(m.plan().victims, set(nodes) - expected)
            m.reserve(m.plan())
            m.destroy_reserved()
            m.assert_safety()
            cases += 1
        self.assertEqual(cases, 512)
        event(self._testMethodName, graphs=8, root_subsets_per_repo=8,
              cases=cases, oracle="independent fixed-point", invariants="passed")

    def test_16_dependency_cycle_fails_closed(self):
        m = self.m
        m.add("x", "provisioned", deps={"y"})
        m.add("y", "provisioned", deps={"x"})
        m.reserve(m.plan())
        self.assertBlocked(m.destroy_reserved)
        self.assertFalse(m.deleted)
        m.assert_safety()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Scenarios)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (BASE / "runtime").mkdir(exist_ok=True)
    (BASE / "runtime" / "traces.jsonl").write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in TRACE))
    sys.exit(not result.wasSuccessful())
