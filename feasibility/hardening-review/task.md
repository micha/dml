# Candidate hardening integration and independent challenge

Read `../WORKER.md`, `../ITERATION.md`, `../CANDIDATES.md`. Own only
`feasibility/hardening-review/`. Start reviewing journal/gate/artifact sources now,
then wait in bounded intervals (up to 15 minutes total) for their reports/markers
before final assessment. Existing first-wave counterexamples must stay intact.

Review candidate policies and try to break them. Independently rerun their tests
in fresh owned sandboxes without editing their source. If scripts have unsafe fixed
paths, use verified copied sources with disclosed relocation/adaptation, or report
that limit. Never operate on live cloud/system/production resources.

Try an actual integrated local handoff if feasible:
- The durable journal records actual commits/heads and a newly created file artifact.
- The real OpenTofu artifact provider adopts that same file without changing bytes.
- Root extraction protects it; shared consumer/drop-head/excision decisions produce
  a durable ticket.
- The backend-neutral gate applies an authorized actual provider destruction plan;
  journal completion observes absence rather than trusting apply exit alone.
- Crash/restart or mismatched physical identity leads to safe recovery/rejection.
This would be actual synthetic file/provider integration, not proof of native DML,
AWS semantics, hostile-filesystem security or a distributed protocol.

Focus independent tests on:
1. Saved plan/config/root freshness at effect boundary and bypass limitations.
2. Canonical identity/owner changes, newly reacquired old heads after withdrawal,
   provenance-only references versus new operational acquisitions.
3. True full-history extraction, member census, durable cleanup prerequisites.
4. Actual multiprocess kill/reopen and ticket state after effect but before receipt.
5. Provider import/no-op/update/read/delete behavior on content/identity mismatch,
   symlink/escape, absent files and potential read/stat/unlink races.
6. Event history versus mutable projection: the user requires versioned research
   state. Does the candidate retain durable observations immutably, or only mutate
   SQLite rows? This may require a design correction even if safety tests pass.
7. State receipt sensitivity, root exposure, all-resource plan parsing limits,
   and module composition. Prototypes must not declare universal HCL safety.

Do not force incompatible worker interfaces into a falsely complete result.
Document adapters, interface friction and unresolved assumptions. If integration
requires a worker fix, write a specific recommendation and provide a minimal
reproducer; the coordinator can resume the worker after first delivery.

Deliver `report.md`, `summary.json`, safe executable checks/integration if possible,
and done marker. Compare at least two reasonable policy alternatives (coarse vs
per-resource fence, provenance/operational distinction, provider versus direct
artifact adapter) without declaring choices approved. Verdict should say what now
works, what remains flawed, and which approach to review in the morning.
