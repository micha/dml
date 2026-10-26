# Retention, GC and excision model

Read `../WORKER.md`; you own only `feasibility/retention/`. Start immediately.

Build small executable deterministic Python experiments (standard library is
fine) for full commit-history reachability from every head across two research
repositories sharing one resource manager. Fake external resources are data, not
cloud objects. You may create/delete only synthetic files under ignored runtime.

Cover:
- all three resource classes, independently owned objects in externally owned
  containers, multiple datums/aliases for the same actual object;
- unmerged branch still roots history; dropping last head enables GC; retained
  historical provenance normally retains infrastructure;
- ordinary resource dependencies, including a retained artifact requiring an
  encryption key/storage; forbid deletion of prerequisite resources;
- resource-manager audit history is not itself a permanent retention root;
- asynchronous pending adoption when the research branch disappears, failed
  cleanup with later retries, inability to GC the sole cleanup identity first;
- unseen/unavailable research repository and concurrent changes to heads between
  GC planning, approval and deletion; demonstrate stale-plan deletion race and
  suggest reservation/fencing without pretending OpenTofu locking solves it;
- authorized resource excision with retained provenance vs sensitive content
  erasure, tombstones, shared consumers, dependency effects and cache availability;
- resource-manager state/mapping must survive regeneration of configuration.

Try to break naive algorithms. Include concrete counterexamples, executable safety
invariants and limits of those invariants. Prefer a small model over an elaborate
new schema. Evaluate how disposal recovery roots can be maintained without making
old research permanently rooted, and whether remote exports/refs introduce
ownership scopes beyond one repo's heads.

Deliver reproducible tests/scenario traces and report. Separate design questions
from bugs in your prototype. Explicitly identify where global coordination is
required and where eventual reconciliation is safe versus unsafe.
