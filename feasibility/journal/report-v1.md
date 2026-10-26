# Durable candidate journal: executed admissions and crash recovery

## Authority boundary and verdict

This report owns the journal experiment only. [The interface](contract.md) is
**journal-v1**, a candidate, not a DML specification or approved policy. SQLite is
a local transactional substrate; the DML implementation and first-wave reports
were not changed.

**Qualified success for cooperative local destructive admission; no-go for a
complete creation/adoption journal or unrestricted deployment.** Twenty tests pass
against real SQLite databases and newly created files. Two publisher processes and
a deleter demonstrate both race outcomes. Seven subprocesses actually terminate
using `os._exit`, including inside transactions. Destruction recovers after partial
effects and lost acknowledgements, while original ownership-overwrite and
post-withdrawal operational-publication examples are rejected.

The strongest surviving counterexample is **creation before registration**: exiting
after file creation/fsync but before the database insert leaves one unregistered
orphan. The test passes by exposing that limitation, not by hiding or repairing it.
External file mutation also leaves a deliberately unreleased fence. These results
are not production, distributed, exactly-once, cloud-adoption or erasure guarantees.

## Reproduction and evidence

From `/work/repos/micha/dml-design`:

```sh
python3 -B feasibility/journal/test_journal.py
# Captured delivery run:
python3 -B feasibility/journal/test_journal.py > feasibility/journal/runtime/tests-delivery-scoped.log 2>&1
```

Versions: **Python 3.13.15**, **SQLite 3.51.2**, Linux **6.18.55**, x86_64,
glibc **2.42**. No packages or tools were installed. Source is
[journal.py](journal.py) and [test_journal.py](test_journal.py); exact source hashes,
documentation hashes and run history are in [evidence.json](evidence.json).
The final [raw test log](runtime/tests-delivery-scoped.log) reports **20 tests, zero
failures/errors**, in 2.953 seconds. The authoritative observed duration is in that
log; timing is not a correctness condition.

Each run allocates new directories, retains all state and synthetic fixtures, and
never prunes existing files. The runner caps retained runs at eight. Five runs were
performed: 16 passing tests initially; a 19-test expansion with one diagnostic-text
assertion failure; 19 passing after fixing that assertion; then two passing 20-test
runs, the last after adding a safe-entrypoint guard. The failed [log](runtime/tests-final.log) remains: rejection correctly said
`full-history retained`, while the test incorrectly expected `cleanup prerequisite`.
No unsafe admission succeeded in that failure.

The required documentation skill was read. Native Context7 tools were unavailable
in this session; its CLI route would require installing a documentation CLI,
forbidden by the worker contract. No quota result is claimed. Instead, downloaded
primary [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html),
[Python sqlite3 documentation](https://docs.python.org/3.13/library/sqlite3.html) and
[Python os documentation](https://docs.python.org/3.13/library/os.html) verified
`BEGIN IMMEDIATE`, explicit transaction control, and file fsync semantics. Downloads
were bounded with timeouts and retained only under ignored runtime paths.

## What the candidate does

### Immutable identity and actual rooted history

Managed registration creates a UUID-named file exclusively in an initially empty,
validated sandbox. Immutable lifecycle identity, physical path key, owner,
device/inode and content digest are recorded independently of aliases. Alias
rebinding, duplicate physical keys, duplicate identity registration and external
victim disposal are rejected. A database trigger also rejects ownership mutation.
Replacement creates a distinct file/identity; this does not implement provider
import or identify equivalent arbitrary external URIs.

Commit parent links and resource associations are immutable records in the database.
Heads are actual stored CAS references. Export traverses **all heads and complete
parent ancestry**, rather than accepting a separately hand-authored root list.
The test retains a resource through an empty child snapshot, a second head and a
second repository; destruction becomes admissible only after every retaining head
is removed. Membership is durable and cannot be silently unregistered. An unavailable
member blocks destruction after reopen, even though this centralized experiment
still possesses its stored graph.

New explicit operational references are checked at commit creation and again when
commits become newly reachable through a head. Withdrawal therefore invalidates a
queued operational publication made before excision. Newly created dependencies
on withdrawn resources also fail. Existing ancestors remain provenance, and a new
provenance-only tombstone reference can publish after disposal. Reacquiring an old
unrooted operational commit is rejected. This deliberately conservative per-head
policy also rejects copying operational history to another head after withdrawal,
even if some other head already retains it; a repository-wide acquisition policy
is a reasonable alternative.

### Durable responsibilities and coarse fencing

Pending adoption and disposal responsibilities live outside research-head retention.
Removing the last head does not erase the target identity or cleanup prerequisite.
An adoption assertion changes the obligation to ongoing management, **not** resolved
cleanup: prerequisites remain pinned until successful target absence acknowledgement.
Reservation converts pending/managed obligations to disposal while keeping the
original cleaner. Live operational dependents require source disposal first;
batches containing both dependency endpoints are conservatively rejected.

One durable global reservation freezes all admission writes: membership, heads,
commits, identity registrations, excision and dependency additions. Even unrelated
publication is blocked. The reservation binds exact victim identities, journal
revision and caller-supplied plan digest. A changed revision, altered ticket field
or completed ticket fails gate verification. Intent is persisted before effect;
absence acknowledgement resolves responsibilities and releases the fence.

This trades throughput and availability for a clear local serialization boundary.
There is no lease expiry, forced cancellation or automatic takeover that could
silently admit references while an old effect is executing. A crashed cooperating
worker can reopen and recover the same ticket. A stuck or identity-mismatched ticket
needs explicit investigation; this prototype supplies no unsafe override.

## Executed races and crashes

All ordering uses pipe handshakes with bounded waits, never sleep-based timing.
In the reservation-first schedule, two publishers and one deleter are separate OS
processes. Both publishers' head, commit, dependency and membership writes fail
under the persisted fence. In the publication-first schedule, both heads publish,
the deleter's old revision is rejected, and a fresh plan is rejected as retained.
A separate simultaneous two-process head CAS admits exactly one publisher.

| Real exit boundary | Reopen observation | Recovery |
|---|---|---|
| Reservation, before intent | File present; ticket/cleanup durable | Begins effect, unlinks, acknowledges |
| Intent, before effect | File present; intent durable | Same ticket completes |
| Unlink/fsync inside effect transaction | File absent; acknowledgement absent | Accepts actual absence and finishes |
| Acknowledgement updates, before COMMIT | File absent; database updates rolled back | Responsibilities stay pinned, then resolve |
| Acknowledgement COMMIT, before response | File absent; disposed already durable | Repeated recovery is idempotent |
| First unlink of a two-victim batch | Exactly one absent; both outcomes unresolved | Deletes remaining file, then resolves both |
| Creation/fsync before registration | One file, no resource/obligation record | **Not recovered: orphan retained** |

Six destruction subprocesses exit with code 73; the creation counterexample exits
with code 74. These are real OS exits without Python exception unwinding or orderly
database close. Final per-boundary observations are included in
[evidence.json](evidence.json). Tests also show that modified bytes or a replacement
inode at the recorded path are not deleted. The unresolved ticket remains fenced.

## Claim boundaries and prioritized gaps

- **Executed:** SQLite durability across process exit/reopen; actual head-derived
  roots; cooperative CAS/fences; filesystem identity/content checks; unlink/absence
  recovery; cleanup identity retention; rejected stale/withdrawn admissions.
- **Simulated/asserted:** repository availability flags, complete membership,
  complete declared dependencies, adoption success (`adopted()` is caller testimony),
  and the semantic role of cleanup resources. No cleanup executable or provider
  import is run. Commit strings/association sets approximate ordinary DML DAGs;
  there is no request/attempt chronology or immutable observation/evidence DAG.
- **Documentation-backed:** transaction/fsync API behavior, not remote-storage or
  power-loss guarantees. **Conjecture:** translating this protocol to LMDB and a
  real backend can preserve the same boundaries.

**P0: Creation write-ahead handoff.** The executed orphan requires a durable creation
intent, minted identity and sandbox capability before creation; recovery must then
reconcile presence without claiming external creation happened exactly once. This
adds uncertain/pending states and ownership-validation work.

**P0: Real gate/backend binding.** Plan digest is an opaque equality field, not a
parsed saved plan. A deployment gate must independently validate actual plan bytes,
configuration revision, backend lineage/serial and physical victim receipts, and
all deployments must cooperate. External mutations and direct SQLite writes are
outside the trust boundary. Registration/dependency census completeness remains
assumed; string equality is not universal URI canonicalization.

**P1: Availability and richer history.** Resource-scoped reservations could allow
unrelated work but require cross-resource/membership conflict tracking. Immutable
receipt/remediation DAGs could improve auditability; tombstone minimization and
secure erasure need separate design. SQLite pages, backups, logs and retained files
are not wiped, and no legal-compliance claim is made.

## Next experiment and gate example

Integrate this contract with a cooperative saved-plan gate and an import-capable
synthetic provider, using an integration-owned fresh runtime root. Add durable
creation intent and receipt identity checks before considering native DML or cloud
work. The minimal candidate sequence is:

```python
s = journal.snapshot()
t = journal.reserve([resource_id], s["revision"], "sha256:actual-plan-digest")
journal.verify(t)          # compare actual plan/backend bindings independently
journal.begin_effect(t)    # durable intent before mutation
journal.effect(t)          # real recorded sandbox unlink in this prototype
journal.ack(t)             # actual absence, not merely successful apply
```

The [contract](contract.md) is the integration source of truth. None of these policy
choices is an approved DML decision.
