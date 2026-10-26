# Candidate journal interface — v1

## Authority boundary

This document describes only the executable candidate in [journal.py](journal.py).
It is not a DML specification or an approved policy. SQLite is a local transactional
substrate; all publishers and deployment gates are assumed cooperative.

## Interface

Import `Journal`, `Rejected`, and `CONTRACT_VERSION` from `journal.py`.
Construct `Journal(db_path, sandbox_path, runtime_root=None)`; each process opens
its own connection. The sandbox is an already allocated fresh empty directory
under this workstream's ignored `runtime/`. The optional runtime root lets later
integration allocate its own sandbox in another feasibility workstream's ignored
`runtime/`, without writing this worker's directory. Callers must respect their
own assigned write scope. No method accepts an arbitrary deletion path.

- `create_file(alias, content=b"synthetic", cleanup=None)` creates a fresh exclusive
  UUID-named file, registers immutable managed identity, and persists a pending
  adoption obligation. Returns identity. `register_external(identity, physical,
  alias)` records immutable external ownership; duplicate identities/physical keys
  and alias rebinding are rejected. `alias(name, identity)` only adds aliases.
  Replacement is another `create_file`, not reclassification or path reuse.
- `member(repo, available=True)` registers/updates availability, never unregisters
  membership. Unknown or unavailable members block destructive admission.
- `commit(repo, key, parents=(), provenance=(), operational=())` stores immutable
  repository-local DAG records. `head(repo, name, expected, new)` atomically CASes
  an actual head (`None` removes it). `export()` derives full-history associations
  from all stored heads; it includes member availability and revision.
- `dependency(source, target)` records a new operational resource dependency.
  `excise(identity)` withdraws operational acquisition without changing old records.
  There is intentionally no cancellation API: replacement gets a fresh identity.
- `adopted(identity)` changes pending adoption to ongoing management/disposal
  responsibility; it does not release cleanup prerequisites. `obligations()`
  exposes durable cleanup identities/prerequisites. An unresolved target can still
  be disposed; reservation converts its obligation to disposal, keeping prerequisites.
- `snapshot()` returns `version`, `revision`, and `roots` for plan binding.
- `reserve(victims, expected_revision, plan_digest)` checks membership, full-history
  retention (unless explicitly withdrawn), dependencies, ownership and identity;
  persists one global reservation and disposal obligations. Returns a ticket dict
  with `version`, `id`, `revision`, `victims`, `plan_digest` and `status`.
- `verify(ticket)` checks exact authoritative ticket fields, active status,
  membership and revision; returns authoritative ticket. `begin_effect(ticket)`
  verifies and durably marks intent before a deployment effect.
- `effect(ticket)` checks intent and recorded sandbox identity and unlinks only
  recorded files; already absent files are accepted. `ack(ticket)` verifies actual
  absence, marks resources disposed, resolves obligations and finishes the ticket.
  `recover(ticket)` calls begin/effect/ack idempotently, including after process death.

`Rejected` is an admission failure; no successful rejection should mutate state.
SQL connections are owned by callers; use `close()` when finished.

## Gate example (informative)

```python
s = journal.snapshot()
ticket = journal.reserve([resource_id], s["revision"], plan_digest="sha256:...")
journal.verify(ticket)       # gate checks digest/victims against its saved plan
journal.begin_effect(ticket) # durable in-flight intent BEFORE external mutation
journal.effect(ticket)       # or cooperative backend effect, not arbitrary paths
journal.ack(ticket)          # absence observation, not merely apply exit status
```

The gate must independently bind actual plan bytes, victim identities, backend
lineage/serial and configuration revision. This prototype treats `plan_digest` as
an opaque equality field: it does not parse OpenTofu or establish backend receipts.
A non-file backend needs its own identity-scoped effect and absence observer;
`ack()` here observes only the candidate sandbox files. `adopted()` is a trusted
caller assertion, not an executed provider import or validated adoption receipt.
Do not use a successful verification to justify an uncooperative deployment bypass.

## Candidate policies and limits

All admission writes (heads, new commits, dependencies, membership, identity and
excision) are blocked while one ticket is active, even unrelated writes. This
coarse durable fence sacrifices availability and survives crashes without lease
expiry. Outcomes are the only writes permitted under the fence. Revision advances
on admissions/reservation/acknowledgement, not on intent status changes.

Provenance can mention withdrawn/disposed identities. New explicit operational
references are rejected at commit creation; head publication rechecks operational
references in commits newly reachable relative to that head's previous history.
Already retained ancestors remain historical after withdrawal. Reacquiring an old
unrooted operational commit is rejected. Excision does not erase associations.

Every unresolved obligation independently pins its cleanup prerequisite until
successful target absence acknowledgement, including after adoption. Resource
operational dependencies block target destruction until sources are disposed.
Managed registration is restricted to freshly created candidate files. Physical
identity uses a minted token plus recorded device/inode/content digest. External
mutation between stat/check/unlink remains outside the cooperative guarantee;
this is not a hostile-filesystem defense, exactly-once execution or legal erasure.
Creation is not write-ahead protected: a process exit after file creation but before
registration can leave an unregistered sandbox orphan. The test suite demonstrates
and retains this orphan; there is no automatic orphan deletion or ownership inference.
