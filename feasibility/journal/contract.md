# Candidate journal interface — v2

## Authority boundary

This document describes only [journal.py](journal.py), not an approved DML policy or
specification. SQLite is a local transactional substrate. The initial contract is
preserved in [contract-v1.md](contract-v1.md). Version v2 refuses v1 databases rather
than fabricating their missing historical observations; no migration is implemented.

## Construction and compatibility

Import `Journal`, `Rejected`, `CONTRACT_VERSION` (`journal-v2`), and `validate_chain`.
Construct `Journal(db_path, sandbox_path, runtime_root=None)` with a fresh empty
sandbox for a new journal. Paths are restricted to a feasibility workstream's ignored
`runtime/`; integration can explicitly select its own runtime root. Each process
opens its own connection, and callers respect their assigned write scope. No API
accepts arbitrary deletion paths. Use `close()` when finished.

Existing `create_file`, `resource`, membership/commit/head methods and gate ticket
methods retain their call shapes. Pending creations now have immutable resource
claims with null device/inode; operational acquisition, adoption, excision and
reservation require a physical receipt. Only the version string changes for tickets.

## Creation intent, effect and observation

- `creation_intent(alias, content=b"synthetic", cleanup=None)` durably registers a
  unique identity/path/digest, expected size, immutable alias and pending obligation
  **before** external file creation. It returns the identity, without creating a file.
  Content bytes are not stored; only synthetic digests/size are recorded.
- `realize_creation(identity, content)` checks supplied bytes against the intent,
  durably marks dispatch intent, then creates/fsyncs exclusively if the path is
  absent. Existing paths are never truncated. Admission is rechecked at the effect
  boundary so a delayed dispatcher cannot recreate an identity already receipted
  and disposed by another cooperating reconciler. It calls reconciliation and
  returns the creation status dict. A terminal `received` result can describe past
  creation; consult `resource()`/operational admission for current readiness.
  Repeated realization cannot repair a quarantined outcome.
- `reconcile_creation(identity)` does not create or delete files. A matching regular
  single-link file at the unique intended path yields an immutable device/inode
  receipt and changes the obligation to adoption. Absence yields durable `absent`
  observation with prior effect unknown. Different bytes, partial writes, symlinks,
  hardlinks or unreadable/type-unsafe paths yield sticky `quarantined` status.
- `creation(identity)` returns target, size, status and canonical JSON observation.
- `create_file(alias, content=b"synthetic", cleanup=None)` remains the convenience
  intent -> realization -> receipt path, returning identity on success. Unresolved
  outcomes remain registered and raise `Rejected`, not invisible orphan cleanup.

A pending/quarantined creation protects aliases, identity and cleanup prerequisites
independently of heads. An absent creation can be explicitly replayed with matching
bytes. Quarantine has no cancellation/repair API. An identical-byte foreign
replacement before the first inode receipt cannot be distinguished: recovery trusts
the unique sandbox capability and cooperative writers, not digest equality as proof
of uninterrupted physical identity. After receipt, identity mutation is rejected.

## Append-only snapshots

Successful projection changes append a whole-projection content-addressed snapshot
in the **same SQLite transaction**. This includes resources, aliases, membership,
commits, actual heads, dependencies, obligations, tickets, creation observations and
revision metadata. Each snapshot has sequence, parent hash, event label and a
canonical JSON SHA-256 hash. Identical projection/no-op operations append nothing.

- `history()` validates the complete chain and its latest projection, returning
  detached snapshot envelopes in sequence order.
- `history_at(hash)` returns an inspectable historical snapshot, not a live row view.
- `validate_history()` returns count and tip hash after validation.
- `validate_chain(entries)` validates detached envelopes' sequence/parent/hash linkage.

History has no update/delete API. SQL triggers reject update/delete/replacement of
existing snapshots on the candidate connection (recursive triggers enabled).
Reopen and every managed transaction validate chain linkage and latest projection
consistency. Mutable tables are coordination indexes/projections, not the only
research/management record. Direct privileged DB changes, dropped guards, whole-chain
rewriting or replacing database files are outside this cooperative trust boundary.
There is no external signed anchor, replica protocol or secure history erasure.

## Existing retention and gate interface

- `register_external(identity, physical, alias)` records immutable external ownership;
  duplicate identities/physical keys and alias rebinding fail. `alias(name, identity)`
  only adds an unused alias. Managed replacement is another fresh creation.
- `member(repo, available=True)` records durable membership/availability; members
  cannot be unregistered. Unknown/unavailable members block destructive admission.
- `commit(repo, key, parents=(), provenance=(), operational=())` stores immutable
  local commit DAGs. `head(repo, name, expected, new)` atomically CASes actual heads;
  `None` removes a head. `export()` derives full-history associations from all heads.
- `dependency(source, target)` adds operational dependencies. `excise(identity)`
  withdraws new operational acquisition but preserves historical associations.
- `adopted(identity)` records a trusted caller adoption assertion, not executed import;
  cleanup stays unresolved/pinned until target absence acknowledgement. `obligations()`
  exposes durable prerequisites even without research heads.
- `snapshot()` returns version/revision/roots. `reserve(victims, expected_revision,
  plan_digest)` checks membership, retention, withdrawal, ownership and dependencies,
  persists one global fence and disposal responsibilities, and returns a ticket.
- `verify(ticket)` checks authoritative version/id/revision/victims/plan digest and
  active status. `begin_effect(ticket)` durably records in-flight intent before effect.
- `effect(ticket)` checks recorded file identity/content and unlinks only candidate
  files; already absent files are accepted. `ack(ticket)` observes actual absence,
  records disposed resources/resolved obligations/finished ticket and releases fence.
  `recover(ticket)` repeats begin/effect/ack idempotently after process exit.

Informative gate example:

```python
s = journal.snapshot()
t = journal.reserve([resource_id], s["revision"], "sha256:actual-saved-plan")
journal.verify(t)        # independently bind plan/backend/config receipts
journal.begin_effect(t)  # durable intent before external mutation
journal.effect(t)        # or a cooperative backend deleting these exact files
journal.ack(t)           # actual absence, not merely apply exit status
old_outcomes = journal.history()
```

## Candidate policies and limitations

All admission and creation reconciliation writes are blocked during one active
destruction ticket, even unrelated work. Ticket intent does not advance retention
revision, but does append immutable history. There is no expiry/cancellation;
stuck tickets sacrifice availability. New operational references fail at commit
creation and on newly reachable commits per head. Existing ancestors remain
historical; provenance-only associations may mention withdrawn/disposed identities.

Plan digests are opaque equality fields: the gate independently checks actual plan
bytes, configuration revision, backend lineage/serial and physical identity mapping.
All publishers/deployments must cooperate; membership/dependency completeness is
assumed. External check/unlink races remain possible. Whole snapshots and complete
chain validation are deliberately unscalable. This is not native DML/LMDB, exactly-
once execution, universal provider adoption, power-loss testing or legal erasure.
