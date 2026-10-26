# Targeted journal follow-up: immutable evidence and creation intent

The user authorized evolving the design and trying fixes. Resume your existing
journal session. Own only your original journal directory. Preserve the initial
report/summary as historical artifacts if you revise their findings; do not alter
first-wave models. Read `../CANDIDATES.md` and current hardening-review task.

Your first delivery correctly exposes two important limitations that we should now
try to fix, rather than merely record:
1. Research/management observations need immutable versioned history, not just
   mutated SQLite coordination rows. Add an append-only content-addressed event or
   snapshot history in the same transactions as successful journal changes. Mutable
   row tables may remain operational projections. Demonstrate the prior state and
   prior ticket outcomes remain inspectable after later changes and reopen. Prevent
   normal API mutation/deletion of history, validate parent/hash linkage, and explain
   that direct privileged DB tampering remains out of scope. A whole-projection
   snapshot per change is acceptable as a deliberately unscalable experiment.
2. Creation must persist a durable intent BEFORE creating the synthetic external
   file. Record a unique intended identity/path/digest/cleanup prerequisite, then
   perform creation, then publish the actual physical receipt. Kill the process
   after intent, after file fsync and before receipt; restart should find a durable
   obligation rather than an invisible orphan. Do not auto-delete ambiguous/mutated
   files. Pending creation must protect cleanup prerequisites and alias/identity
   claims. Preserve API compatibility with gate's use of resource/create_file and
   tickets; add a concise reconciliation API if necessary.

Add focused actual crash/reopen/history tests and rerun the existing suite. Report
both positive recovery and quarantined unknown outcomes. This remains a toy local
journal, not DML/LMDB integration, a new production schema, universal erasure or
exactly-once execution.

Update contract/report/summary with the new evidence and tradeoffs (append-only
history versus materialized coordination indexes, full-snapshot cost, stuck ticket
availability). Publish `followup-done.json` atomically AFTER the revised report.
Do not reuse your original done marker as proof of this new work. Return and exit.
