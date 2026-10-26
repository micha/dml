# Retention, GC and excision feasibility

## Authority boundary and verdict

This is an informative experiment report, not an approved DML specification. The
conceptual baseline is the [design discussion](../../discussion.md); the assigned
scope is [task.md](task.md). No implementation-repository files were changed.

**Verdict:** full-history retention across two repositories is tractable in a
small model, but asynchronous deletion is unsafe without a complete ownership
census, durable disposal identities, dependency closure, and coordination with
resource-reference publication. Regenerable configuration is not regenerable
operational state. Tombstones alone neither erase content nor protect shared
consumers.

The strongest executed counterexamples are:

- A current-snapshot scan would collect `compute` although an ancestor commit
  still retains it.
- A plan checked immediately before approval deletes `object` after repository B
  publishes a reference between that check and deletion.
- Collecting the only cleanup identity strands a pending adopted result.
- Removing a key breaks a retained artifact even when both repositories authorize
  the key's retirement; dependency impact needs a separate disposition.

## Reproduction and evidence

Run from `/work/repos/micha/dml-design` using **Python 3.13.15**, standard library
only. There are no downloads, provider calls, cloud objects, or models involved.

```sh
mkdir -p feasibility/retention/runtime
python3 -B feasibility/retention/test_model.py \
  > feasibility/retention/runtime/test-output.txt 2>&1
sha256sum feasibility/retention/runtime/traces.jsonl \
  > feasibility/retention/runtime/trace-sha256.txt
python3 -B feasibility/retention/test_model.py \
  > feasibility/retention/runtime/test-output-repeat.txt 2>&1
sha256sum --check feasibility/retention/runtime/trace-sha256.txt
```

Observed: **20 tests passed**, including all six permutations of publication,
reservation, and destruction, plus **512 bounded graph/root combinations**. The
second run took 0.121 seconds; timing is incidental. Trace checksum verification
returned `OK`; the deterministic trace SHA-256 was
`7c37e3e70b1b467206060b5400728717d78ed6594e59bb1c602412e777bb43dd`.

Source: [model.py](model.py), [test_model.py](test_model.py). Detailed generated
records: [scenario traces](runtime/traces.jsonl), [test output](runtime/test-output.txt).
Runtime artifacts are ignored and recreated by the commands above. Fake resources
are synthetic `.object` files beneath this workstream's `runtime/`; erasure copies
are synthetic bytes in model memory.

### Claim-to-evidence map

All numbered tests below are **executed simulations**, not demonstrations against
DML, OpenTofu, a distributed database, or real encryption.

| Claim | Executed evidence |
| --- | --- |
| Every head and its ancestors matter; aliases aggregate by actual identity | 01 |
| Ordinary dependencies and cleanup identities affect retention/order | 02, 09, 18; 512 independent fixed-point comparisons in 20 |
| Resource-manager audit is not a research root | 03 |
| Pending adoption survives branch removal; two failures remain retryable | 04; naive identity loss in 05 |
| Missing repository knowledge makes destructive planning unsafe | 06 |
| Revalidation alone has a check/delete race; cooperative fencing prevents tested races | 07–09, 19 |
| Retirement and content erasure have different effects | 10–13 |
| State/address mapping survives configuration regeneration, not state loss | 14 |
| Remote export references extend retention/authorization scope | 15 |
| Cycles fail closed; pre-journal creation can escape reconciliation discovery | 16–17 |

**Documentation-derived context:** full-history roots, the three ownership
classes, optional GC, and excision come from the discussion, not new decisions.
**Conjecture:** a durable distributed reservation protocol and secure erasure
implementation could enforce stronger guarantees. Neither was built here.

## What the model established

### Roots, ownership, and dependencies

Both repositories share one manager. Commits are immutable records; heads are
mutable. History traversal follows every parent from every head. A provisioned
closure resource remains retained by an ancestor even when the newest snapshot
contains no resource datums. An unmerged head independently retains its history.
Dropping A's heads still cannot collect an adopted object referenced through B's
second datum alias. Dropping the final head makes managed resources collectible.
The external bucket survives deletion of its independently owned object.

Retention then closes over prerequisites: an encrypted artifact retains its key
and storage even without direct datums naming them. Destruction orders dependent
before prerequisite. The graph sweep checks eight acyclic three-resource graphs
against all eight root subsets in each repository, using a separate fixed-point
oracle. A two-resource cycle is rejected, not silently linearized. Audit records
remain present after disposal without rooting the discarded research.

### Disposal recovery without permanent research roots

A minimal recovery obligation stores target identity, cleanup identity, phase,
and failure count. It roots neither the abandoned commit nor its ancestors.
Targets under such obligations are excluded from ordinary GC and disposed by the
reconciler instead. This distinction avoids accidentally retaining the target
forever merely because cleanup needs its identity.

In test 04, adoption is pending when the last research head disappears. The
reconciler registers the object, records two simulated cleanup failures, and
finally confirms deletion. Only then does it discharge the obligation and allow
collection of the cleanup identity. In test 18, retained research instead takes
over retention after adoption; later GC still deletes result before identity.

This needs a durable handoff before research GC can drop the only identifying
record. Test 17 illustrates the creation-before-journal gap: the omniscient model
knows the object, but a reconciler scanning only state, rooted history, and
obligations does not. A real adapter could have an undiscoverable leak. A safe
journal cannot manufacture an unknown external identifier after a crash.

### Plans and publication

Test 07 deletes a retained object despite a just-revalidated plan. Approval is
not a transaction with publication. The corrected simulation reserves a victim
set at the validated revision. Head updates, exports, and pending-adoption
registration reject references to fenced victims; alias/resource namespace
changes and excision are blocked during the reservation. After destruction,
publication of an ordinary live reference to that deleted identity is rejected.

The fence is a cooperative in-memory mechanism. It is not a crash-safe protocol.
An OpenTofu operational-state lock, whatever its backend behavior, would not by
itself enlist these separate repository publishers. No OpenTofu locking behavior
was tested or assumed.

### Excision, cache availability, and erasure

Retiring `compute` requires both current consumers' approval and leaves historical
commits unchanged. Its references resolve through a tombstone; execution using
it becomes unavailable. An independently usable cached artifact remains
available because provenance association is not modeled as a runtime dependency.
A key is different: removing it alone is rejected while its retained artifact
still needs it. Explicitly retiring both makes the artifact cache unavailable.
Creating and verifying a newly encrypted artifact is a possible alternative,
not an executed migration or an approved design.

Content erasure additionally clears two controlled synthetic copies. Publishing
a tombstone alone leaves both copies intact. An uncontrolled offline copy
survives deliberately: the report claims no global erasure. Tombstones contain
only synthetic ID and status. Real identifiers, hashes, reasons, old DAG literals,
logs, replicas, and backups might themselves disclose sensitive information and
need a larger erasure inventory.

### Operational mapping and remote references

Test 14 preserves `module.closure.result -> physical-object-17` while throwing away
and regenerating configuration. Clearing state leaves the actual object present
but loses that operational mapping; explicitly reloading saved state restores it.
The prototype materializes a mapping view, not HCL: it uses operational addresses
and does not prove reconstruction of configuration from DML alone. Provider
private state, schema versions, and import/replacement behavior remain untested.

An explicit export/ref retains an object after all local heads disappear. Its
owner also participates in excision authorization. This exposes a scope beyond
one repository's heads; an unmanaged copy cannot be discovered by this model.

## Coordination, gaps, and next experiment

**Global coordination is needed** for membership changes, retention-affecting
publication versus deletion, shared-consumer excision, and transfer of the sole
cleanup identity. Unknown or unavailable associated repositories block planning.
A completeness flag is only an assumption, not a discovery mechanism.

**Eventual reconciliation is safe in this model** for configuration generation,
adoption registration, observations, and cleanup retries while durable obligations
and prerequisites remain protected. **It is unsafe** to destroy resources from
stale exported root summaries, discard recovery records on failure, or allow new
references during an unfenced destruction window. Delayed destruction wastes
resources; premature destruction loses retained research availability.

Prioritized possible fixes and tradeoffs, not decisions:

1. **Durable reservation/fencing:** bind approval to root/membership revisions;
   enlist all reference publishers, persist deletion-in-flight status, and prevent
   expired leases from reopening publication while an old deleter can still act.
   This adds global coordination and sacrifices availability during partitions.
2. **Recovery handoff:** retain minimal resource identities and cleanup capability
   before discarding research. Discharge only after confirmed absence or transfer
   to another durable owner. Unknown outcomes can require indefinite quarantine,
   but need not retain the old research DAG.
3. **Complete identity/dependency inventory:** canonicalize actual objects across
   aliases and repositories; separate containment, provenance, operational and
   cleanup dependencies. Wrong edges either leak infrastructure or break caches.
4. **Excision policy and copy inventory:** decide who can override shared consumers,
   what dependency cascades are permitted, and what can honestly be certified as
   erased. This cannot be inferred from graph reachability alone.

The invariants check retained prerequisites, recovery capability, external
ownership, tombstone fields, and controlled-copy erasure. They cannot detect
missing dependency declarations, unregistered repositories, uncontrolled copies,
or an executor bypassing the APIs. Direct dictionary mutation is fixture access,
not a production protocol. Revisions/fences and the journal are not persisted;
provider failures and crashes during ordinary GC are not modeled. The initial
syntax error was corrected before the passing runs; intentionally unsafe
comparators are test fixtures, not unresolved prototype bugs.

**Next experiment:** use two local publisher processes and a file-backed durable
journal, kill the deleter between reservation and unlink, then attempt publication
and restart recovery. Exercise lost responses and partial deletion while checking
that no publisher can re-root a deletion-in-flight object and that cleanup
identities survive. This would test the largest unproven step without cloud access.
