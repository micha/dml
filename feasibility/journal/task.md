# Durable candidate journal and root-export prototype

Read `../WORKER.md` and `../ITERATION.md`; own only `feasibility/journal/`.
Start now. This is candidate-design iteration, not a finalized schema. Read the
first-wave integration/review findings, especially identity overwrite, new
operational dependencies after excision, incomplete root exports, stale deletion
plans and loss of sole disposal identity.

Build a small real persistent Python/SQLite prototype (stdlib only). SQLite is a
local transactional test substrate, not a DML storage proposal. Publish a concise
`contract.md` or JSON interface contract early so the gate worker can understand
how to integrate later. Prefer a few clear functions over a large framework.

Desired candidate capabilities:
1. Canonical physical resource identity separate from names/aliases; immutable
   lifecycle ownership registration. Reject external->managed reclassification,
   duplicate physical identities and conflicting alias rebinding. Record replace
   as a new identity. No arbitrary file deletion; disposable paths must be newly
   created validated sandbox files and deletion should check recorded identity.
2. Durable known-repository membership, immutable commits and actual heads;
   full-history root extraction comes from these stored graphs, not hand-exported
   independent test roots. Atomic head CAS and publication checks against disposed
   or withdrawn operational dependencies. Distinguish historical provenance from
   new operational acquisition and explain the chosen policy.
3. Pending adoption/disposal obligations survive removal of last research head;
   cleanup prerequisites persist until successful absence acknowledgement. Never
   erase only cleanup identity before effects are resolved.
4. Destruction reservation/admission fences against cooperating new references,
   dependency additions and membership changes. Make authoritative revision/ticket
   checks available to a backend-neutral deployment gate. Persist in-flight intent
   before effect; after crash recognize actual absence and idempotently finish.
5. Explicit excision can retain historical associations but disallow newly created
   operational dependencies unless explicit cancellation/replacement policy.

Run actual multiprocess tests with two publishers and a deleter, barrier-controlled
races (deterministic, no sleep-based timing), process termination at reservation,
external effect/unlink and acknowledgement boundaries, reopen/recovery, unavailable
repository member and stale plan ticket cases. At least one crash must be a real
OS process exit/kill, not an injected exception. Demonstrate original identity and
withdrawn-publication counterexamples are rejected by candidate admissions.

Provide Python source/tests and commands. Explain trust boundary: cooperative
publishers only, complete registered membership/dependencies assumed, external
mutation still possible. Fences can sacrifice availability; no exactly-once or
legal erasure claim. Document where chronology/evidence DAGs are approximated,
which behavior is policy and alternatives that remain reasonable.

Finish normal report/summary/done. Include current contract version and a short
example of create reservation -> verify ticket -> effect -> record outcome. No
modifications to first-wave models or reports.
