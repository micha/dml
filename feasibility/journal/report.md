# Journal follow-up: immutable snapshots and write-ahead creation

## Authority boundary and verdict

This report describes **journal-v2**, an experimental local SQLite candidate, not
an approved DML schema, LMDB integration or production lifecycle service. The
[contract](contract.md) owns the executable interface. The initial findings remain
unchanged in [report-v1.md](report-v1.md), [summary-v1.json](summary-v1.json) and
[evidence-v1.json](evidence-v1.json); initial source and contract copies are also
retained. First-wave models/reports and the DML implementation were not modified.
The original `done.json` is not proof of this follow-up; delivery uses a separate
`followup-done.json`.

**The targeted corrections work within the cooperative local boundary.** All 35
combined tests pass: 20 baseline tests, including the revised creation-crash case,
and 15 focused follow-up tests. Management state now has immutable transactional
snapshots, and a file created before its physical receipt has a durable identity,
alias and cleanup obligation rather than the invisible orphan seen in v1.

**The strongest remaining counterexample is pre-receipt physical ambiguity.** After
creation crashes, replace the unreceipted file with different-inode but identical
bytes. Reconciliation accepts that new inode because no original inode receipt
committed. A moved copy of the old file remains. This is an executed limitation of
content/capability-based recovery, not an exactly-once or hostile-filesystem claim.
Changed bytes and unsafe file types are instead quarantined without deletion.

## Commands, versions and evidence

From `/work/repos/micha/dml-design`:

```sh
python3 -B feasibility/journal/test_journal.py
python3 -B feasibility/journal/test_followup.py
# Captured final combined run:
python3 -B feasibility/journal/test_followup.py > feasibility/journal/runtime/tests-followup-final.log 2>&1
```

Versions remain **Python 3.13.15**, **SQLite 3.51.2**, Linux **6.18.55**, x86_64,
glibc **2.42**. Source is [journal.py](journal.py),
[test_journal.py](test_journal.py) and [test_followup.py](test_followup.py).
The standalone v2 baseline passed 20 tests in 4.099 seconds. The first combined run
passed 34 tests; after adding effect-boundary revalidation and its delayed-dispatch
race, the final [log](runtime/tests-followup-final.log) records **35 tests, zero
failures/errors, 6.722 seconds**. [evidence.json](evidence.json) records source
hashes, all follow-up runs, exact observations and snapshot-size measurements.

Runs use newly allocated ignored sandboxes and never auto-prune existing resources.
Baseline and follow-up allocation each have an eight-run cap; tests refuse an
unscoped import-driven entry point. There were no installs, cloud APIs, Docker
connections, credential reads, commits or remote changes. The documentation skill
was read, but native Context7 tools were unavailable and its installation-based CLI
route is prohibited by the worker contract. No quota result is asserted. Primary
[SQLite trigger](https://www.sqlite.org/lang_createtrigger.html) and
[conflict-resolution](https://www.sqlite.org/lang_conflict.html) documentation was
fetched with bounded timeouts. In particular, `REPLACE` fires deletion guards only
with recursive triggers enabled; the candidate enables that setting and tests it.
Transaction and fsync sources from the initial delivery remain recorded.

## Immutable history versus operational projections

Every successful logical projection change appends a **whole-projection snapshot
in the same transaction**. The snapshot includes metadata/revision, resource claims
and receipts, aliases, member availability, immutable commits, actual heads,
dependencies, cleanup obligations, tickets and creation observations. Canonical
JSON is hashed with SHA-256; each envelope includes a sequence, parent hash and
event label. Identical/no-op operations append nothing. Ticket intent updates append
history without advancing the retention revision that would invalidate the ticket.

Mutable rows are now coordination indexes, not the sole management record. A test
publishes an operational head, removes it, reserves disposal, records intent and
acknowledges absence. It then completes another ticket, changes membership and
reopens. Earlier head state and all three ticket states—`reserved`, `intent`,
`acknowledged`—remain inspectable by their original snapshot hashes. Adoption,
withdrawal and outcome changes likewise appear as new projections, not rewritten
snapshot content.

`history()`, `history_at(hash)` and `validate_history()` validate linkage and return
detached data. Changing a returned dictionary cannot mutate stored history. Normal
history update, delete and `INSERT OR REPLACE` attempts fail through SQL guards.
Tests reject altered content hashes, a rehashed but wrong parent, and missing
sequence entries. Reopen detects a deliberately malformed appended row. This does
**not** authenticate the database against a privileged writer capable of dropping
guards and rewriting an entire chain or replacing its file; there is no external
signed anchor.

Transactionality is executed, not merely inferred. An injected snapshot-persistence
failure rolls back both the projection and appended history. More strongly, a real
process exits after physical receipt **and its snapshot** are inserted but before
COMMIT: reopen sees neither, while the earlier dispatch intent remains intact.
The original destruction/acknowledgement crash tests continue to pass.

## Creation intent and reconciliation

Creation is now three stages:

1. `creation_intent(alias, content, cleanup)` commits a minted identity, unique path,
   expected digest/size, immutable alias claim and unresolved cleanup obligation.
   No filesystem effect has occurred. The resource's device/inode is still null.
2. `realize_creation(identity, content)` validates explicitly supplied bytes, commits
   dispatch intent, then exclusively creates and fsyncs only the minted sandbox
   path. Existing paths are never truncated. It rechecks admission at the external
   effect boundary.
3. `reconcile_creation(identity)` observes the path without creating or deleting it.
   Matching regular single-link content publishes the physical receipt and pending
   adoption obligation. Absence records `absent` with prior effect unknown. Changed
   bytes, partial content, symlink, hardlink, directory or FIFO produce sticky
   `quarantined` status. FIFO observation is nonblocking.

Pending creation already protects aliases, identity and cleaner independently of
research heads. It cannot be adopted, used operationally, excised or reserved as a
destructive victim before receipt. `create_file()` retains its original call shape
and successful identity return, wrapping these stages. An unresolved convenience
call can fail after committing intent: failure is not permission to forget it.

An absent intent is explicitly replayable with matching bytes, but observation
alone does not silently retry creation. Quarantined files and cleanup prerequisites
remain intact across reopen; there is intentionally no automatic repair, deletion
or cancellation API. This sacrifices availability rather than guessing ownership.
Once receipt exists, the original immutable inode/content checks govern disposal.

A further deterministic process race exercises delayed creation. Dispatcher A pauses
after committed dispatch intent; reconciler B realizes that identity and completes
its disposal. A resumes only after acknowledgement. The effect-boundary recheck
returns historical completion without recreating the disposed path. Without that
recheck, a stale creation dispatcher would be dangerous. Current operational
readiness still requires resource/lifecycle admission, not just a past `received`
creation result.

## Real exits and quarantined unknown outcomes

The final suite performs **12 abrupt OS exits**, without orderly SQLite close or
Python exception unwinding: six destruction exits, one revised baseline creation
exit and five focused creation exits. Ordering uses pipe barriers, never timing
sleeps; waits and joins are bounded.

| Boundary or attack | Observation after reopen | Outcome |
|---|---|---|
| Committed creation intent, before file effect | No file; known identity and pinned cleaner | Records unknown absence; explicit replay succeeds |
| File fsync, before receipt | Matching file; pending durable creation | Reconciliation publishes receipt without rewriting bytes |
| Receipt and snapshot inserted, before COMMIT | File present; both updates rolled back | Earlier intent survives; reconciliation succeeds |
| Crash then changed bytes | Null receipt; mutation observed | Durable quarantine; file untouched; cleaner pinned |
| Crash then identical-byte replacement | Different inode, expected digest | Replacement accepted; original identity before receipt unknowable |
| Delayed dispatcher after another process disposes | Completed creation and disposal already recorded | No recreation after resume |
| Reservation/effect/acknowledgement and partial batch exits | Same observations as baseline | All six destruction recoveries pass |

Four additional unsafe-path cases are quarantined and preserved. Rejected admissions
and repeated recovery of a finished ticket append no false successful change.
Full-history root extraction, two-publisher/deleter schedules, unavailable member,
stale plan/ticket, ownership and withdrawn-publication tests remain passing.

## Evidence boundaries, tradeoffs and next experiment

**Executed:** transactional snapshot preservation/validation, actual OS exit/reopen,
creation intent before file effects, positive reconciliation, quarantine, delayed
creation admission, and prior local destructive fences. **Asserted/simulated:**
complete membership/dependency census, member availability, provider adoption and
cleanup programs; `adopted()` remains trusted caller testimony. Snapshot chains
approximate versioned DML data but do not integrate native request/attempt/evidence
DAGs. **Documentation-backed:** trigger/transaction/fsync API semantics, not tested
power-loss durability. **Conjecture:** a real DML/backend implementation can preserve
these boundaries at useful scale.

Prioritized remaining work, not approved decisions:

- **P0: Receipt ambiguity and trusted creation authority.** Unique capability paths
  plus expected content are sufficient only for cooperating sandbox writers.
  Provider operation IDs, a trusted creation service or a durable early inode
  checkpoint could narrow uncertainty; each adds identity/handoff complexity and
  still cannot make external effects globally atomic. Another reasonable policy
  quarantines every present-but-unreceipted file, sacrificing positive recovery.
- **P0: Real backend gate/receipt binding.** Tickets retain their existing interface,
  now versioned `journal-v2`; saved-plan bytes, configuration/backend receipts and
  physical identity mapping remain independent gate obligations. V1 databases are
  explicitly refused, not silently upgraded with invented history.
- **P1: Scale and retention semantics.** In the outcome-history test, 20 snapshots
  store **39,661 JSON bytes**, versus **3,071 bytes** for the final snapshot alone.
  Full snapshots and whole-chain validation grow poorly. An append-only fact DAG
  with transactional materialized indexes could reduce duplication but needs
  explicit event schemas, replay validation and migration. Management snapshots
  deliberately do not become research retention roots; otherwise audit retention
  would prevent all GC.
- **P1: Availability and erasure.** Coarse tickets block unrelated creation and
  reconciliation; quarantine pins prerequisites indefinitely. Resource-scoped
  fences/explicit remediation could improve availability with more conflict and
  authority rules. Immutable snapshots retain metadata/digests; no sensitive-data,
  backup, secure-page or legal-erasure guarantee follows.

Next, independently rerun this v2 candidate and integrate a fresh-owned sandbox
with the saved-plan gate and import-capable artifact provider. Use immutable receipt
observations and the existing `reserve -> verify -> begin_effect -> effect -> ack`
sequence; do not infer physical absence from apply success or historical creation
completion. Native DML, cloud and privileged-writer hardening remain separate work.
