# Iteration 1 handoff: minimum viable repository

Status at preparation: ready for implementation handoff; implementation had not
started. **Current delivery:** see [RESULTS.md](RESULTS.md) for the implemented
workflow, historical gate failure and subsequent bounded hardening/exclusion-policy
follow-up. The remainder preserves the implementation handoff and its scope.

The user has explicitly authorized code changes in `/work/repos/micha/dml` for
this iteration.

## 1. Authorization and purpose

The user requested this handoff after agreeing on a smaller first design-spiral
iteration, then explicitly authorized code changes in `/work/repos/micha/dml`.
Implement the bounded scope below in that checkout when instructed to begin.
No additional location/code-authorization decision is needed for this iteration.

The new as-built documentation directory `docs/spec-next/` is also authorized.
Neither authorization permits expanding this iteration into execution, remotes or
other deferred subsystems.

The goal is:

> Create immutable repository snapshots, connect them into a commit graph, and
> point mutable refs at commits, using the existing datum and LMDB foundation.

This is a shallow first turn, not a complete repository subsystem. The user
rejected an initial plan involving intents, closures and execution as too ambitious.
Do not reintroduce those features to make the prototype appear more complete.

## 2. Read before starting

Follow the machine-wide instruction index and verify `/work` is mounted. Then read:

1. [Design repository agent guide](../../AGENTS.md).
2. [Discussion resume point](../../discussion.md#resume-point) and
   [development policy](../../discussion.md#design-spiral-and-pre-10-compatibility-policy).
3. [Implementation repository agent guide](../../../dml/AGENTS.md).
4. [Shared documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   completely, before documentation changes.
5. [New spec README](../../../dml/docs/spec-next/README.md),
   [spec agent guide](../../../dml/docs/spec-next/AGENTS.md),
   [glossary](../../../dml/docs/spec-next/glossary.md),
   [records](../../../dml/docs/spec-next/records.md) and
   [repository storage](../../../dml/docs/spec-next/repository.md).
6. The implementation files listed in Section 7 and the standard
   [validation script](../../../dml/scripts/check.sh).

The old draft `docs/spec/` may be consulted for context. Its larger layouts and
execution/pinning semantics are not automatically requirements of this iteration.
Keep that suite unchanged unless separately authorized.

## 3. Development rules

### User-agreed direction

- Prefer minimal implementations and frequent iterations. Breadth and depth can
  alternate according to what teaches us something useful.
- All DML development repositories/state are ephemeral until `v1.0.0`.
- Do not increment versions or introduce migrations/compatibility layers merely
  because this iteration changes the development format.
- Immutable objects remain immutable inside a repository. Ephemeral state is not
  permission to overwrite historical objects or delete unrelated data/resources.
- The as-built spec documents implemented functionality, not a future roadmap.
  Its documented functionality defines its scope; no missing-feature inventory.
- Maintained documentation uses the glossary consistently. Design discussion does
  so on a best-effort basis. Provisional glossary entries do not approve schemas.

### Scope control

- Use only newly created local test repositories. No cloud/service operations.
- No remotes, pushes, global package installation, OS changes or resource cleanup.
- Inspect Git status first and preserve unrelated changes. Do not reset/clean a
  checkout to match the handoff baseline.
- No public Python binding or CLI project is required. A small native test driver
  suffices; Python can orchestrate native tests without being a public binding.
- Any new representation below is an **assistant implementation recommendation**,
  not a previously selected wire format. Keep it small, document the actual result,
  and surface consequential deviations rather than inventing broader requirements.

## 4. Baseline and what is reusable

At handoff preparation, the latest local commits are:

| Checkout | Commit | Meaning |
| --- | --- | --- |
| `dml` | `b428b01` | Shared glossary and new-spec vocabulary guidance |
| `dml-design` | `043c851` | Links and discussion vocabulary policy, before this handoff |

Reinspect status and HEAD; these are provenance, not a request to check out old state.

The implementation already supplies:

- Datum encode/decode/validation for ten kinds.
- Canonical record envelopes, text/URI helpers and 16-byte content IDs.
- LMDB initialization, transactions and immutable datum put/get.
- Failed-write transaction poisoning and atomic rollback.
- Public C ownership/error conventions and tests.

It does not currently supply node/DAG/tree/commit codecs or a ref API. Type constants
in `record.h` are not implementations. Python/CLI/example adapter code is scaffold.

Keep existing datum APIs and tests working where practical. No old-repository
migration promise is needed, but unnecessary breakage of useful APIs is not a goal.

## 5. In-scope entities and operations

| Entity | Minimum content | Required behavior |
| --- | --- | --- |
| Datum | Existing record | Reuse encoding, hashing and storage |
| Node | Literal datum reference | Encode, validate, identify, store, read |
| DAG | Root node reference | Encode, validate, identify, store, read |
| Tree | Named DAG entries | Encode, validate, identify, store, read |
| Commit | Tree reference and parent commit references | Encode, validate, identify, store, read |
| Ref | Repository-scoped name and target commit | Create/read/update atomically in a storage transaction |

A tree can support an empty entry collection if that is the simplest consistent
codec; tests for this iteration use at least one entry. A DAG needs a root; optional
named-node bindings are unnecessary. Tree-entry names are **not** named-node bindings.

Commits should permit zero parents for initial history and a parent list for later
history. Supporting a parent list is not implementing merge. The demonstrated
workflow needs zero/one parent and two children sharing a parent. If the codec
supports multiple parents, test and document its ordering/duplicate policy too.

Only the full recorded content identity is needed for immutable objects. There are
no masks or computational reuse identities in this implementation turn. Refs are
mutable pointers, not content-addressed immutable objects.

### Required operations

- Open/create a local repository using existing behavior.
- Put/get the in-scope immutable objects in a storage transaction.
- Create a named ref to an existing commit; read it; explicitly update its target.
- Follow a commit's parents and read its tree, DAG, root node and datum.
- Close/reopen and perform the same inspection in a fresh process.

A convenience commit-graph traversal API is not required. A driver can retrieve
parents and traverse them itself. Ref listing/deletion and branch-management commands
are unnecessary for the success case.

## 6. Concrete acceptance workflow

The test driver constructs this state:

```text
main -> C2 -> C1
        |     |
        T2    T1
        |     |
      example example       (tree-entry names)
        |     |
        D2    D1
        |     |
        N2    N1
        |     |
       43    42              (I64 datums)
```

Arrow meanings: ref target, commit parent, or object reference. They are not
execution steps.

1. Create a fresh repository in test-owned scratch.
2. In one write transaction, store datum `42`, literal node N1, DAG D1, tree T1
   with entry `example`, commit C1 with no parents, and ref `main -> C1`.
3. Commit the **storage transaction**.
4. In another write transaction, store the analogous `43` snapshot and C2 with
   parent C1, and update `main -> C2`.
5. Commit that transaction, close the repository, and end the process.
6. A fresh process resolves `main`, reads C2's snapshot and obtains `43`.
7. It follows C2's parent and reads C1's snapshot to obtain `42`.
8. Re-read C1 and C2 by ID after moving the ref; their bytes/IDs are unchanged.

For branching history, independently create C3 with parent C1, using the same small
object model. A second ref can expose C3 if useful. No merge/rebase/checkout operation
is needed to demonstrate that C2 and C3 share a parent.

## 7. Suggested implementation approach

### Existing files to inspect

| Area | Files |
| --- | --- |
| Public types and datum codec | [record.h](../../../dml/include/dml/record.h), [record.c](../../../dml/src/record.c) |
| Envelope and binary helpers | [record_internal.h](../../../dml/src/record_internal.h), [encoding.h](../../../dml/src/encoding.h), [encoding.c](../../../dml/src/encoding.c) |
| Identity | [object_id.c](../../../dml/src/object_id.c) |
| Storage/ownership | [repo.h](../../../dml/include/dml/repo.h), [repo.c](../../../dml/src/repo.c) |
| Public errors | [error.h](../../../dml/include/dml/error.h) |
| Build wiring | [meson.build](../../../dml/meson.build) |
| Native tests/driver | [test_record.c](../../../dml/tests/c/test_record.c), [test_repo.c](../../../dml/tests/c/test_repo.c), [core_driver.c](../../../dml/tests/c/core_driver.c) |
| Property/integration tests | [record tests](../../../dml/tests/python/test_records_hypothesis.py), [repository tests](../../../dml/tests/python/test_repository_hypothesis.py) |

### Recommended structure

Extend the native C foundation rather than build a second storage backend or a
parallel Python-only repository. Use minimal packed record codecs for the new
entities. Reuse the current envelope, length/overflow helpers, ID type and error
conventions. Do not persist native C structs/pointers or allocate space for unused
future features just to match the old draft.

Before coding the codecs, write a short implementation sketch in the delivery notes
covering these choices, then implement the smallest coherent version:

- Fields needed for each object, count/length representation and canonical ordering.
- Supported literal-node form and how unsupported node kinds are rejected.
- Tree name encoding, duplicate-name policy and ordering.
- Parent-list ordering/duplicates; prefer preserving supplied parent order to avoid
  silently choosing first-parent semantics through ID sorting.
- Ref-name validation and key namespace. Reusing `refs/heads/<name>` is a reasonable
  starting convention, not a requirement to implement all old ref categories.
- Public put/get and ref-operation API names and ownership/error behavior.

For names, reuse existing normalization/validation machinery where appropriate;
if the first implementation supports only a narrower name profile, state and test
that exact profile. Do not quietly accept ambiguous duplicate normalized names or
use names as filesystem paths.

### Immutable-object storage

A small internal common helper may eliminate repeated key/hash/lookup logic, while
public operations retain type checks. Avoid a broad plugin registry or generic
schema framework.

For every new immutable object:

- Derive ID from its canonical encoded content, including type/version domain.
- Store under a type-qualified key with no-overwrite semantics.
- Accept reinsertion only for identical content under that ID.
- Validate direct referenced objects' presence and expected type before insertion.
- Allow references to objects inserted earlier in the same transaction.
- On reads, validate encoding and key/content-ID agreement; apply the documented
  direct-reference checks consistently rather than claiming transitive validation.

Keep `dml_datum_id()` restricted to datums. Factor its underlying hashing machinery
or add a broader immutable-object ID operation without accidentally accepting refs
as content-addressed objects. Retain existing datum golden vectors if their encoding
is unchanged; do not rewrite expected vectors merely to hide a regression.

Requiring parents/children to exist before their referencing object provides a
simple construction discipline for this turn. No general graph-cycle solver or
arbitrary forward-reference publication is needed. It does not prove correctness
of externally corrupted stores.

### Ref updates and transactions

Ref storage is mutable and uses the same LMDB transaction as object insertion.
A single commit can make a complete snapshot and its ref target visible together.

- A ref target must resolve to a valid commit in the transaction.
- Distinguish create from update, or document explicit upsert semantics. Never let
  callers accidentally treat an immutable-object put as a ref overwrite operation.
- Failed writes must preserve the existing poisoned-transaction/rollback contract.
- Do not require fast-forward checks, ancestry policy, compare-and-swap, leases or
  concurrent branch-edit protocols in this turn.
- Preserve existing thread-affinity and external-synchronization requirements.
  Atomic LMDB writes are not an authorization or remote-concurrency protocol.

## 8. Work sequence

Each step is a small checkpoint, not a requirement for separate commits.

1. **Preflight:** confirm authorization, read instructions, inspect status/build
   setup, identify any environment blockers, and run the relevant existing baseline
   tests in test-owned scratch once authorized. Record actual outcomes.
2. **Codec slice:** add the minimal node/DAG/tree/commit encoders, decoders/views,
   validators and immutable-object hashing, with focused round-trip/negative tests.
3. **Storage slice:** add their transactional put/get and typed-reference checks,
   preserving datum behavior and rollback/integrity guarantees.
4. **Ref slice:** add the small transaction-scoped named-pointer operations.
5. **Workflow slice:** extend a native test driver and fresh-process integration
   tests to exercise Section 6. Keep the production CLI/Python packages unchanged
   unless a tiny necessary adjustment is explicitly justified.
6. **As-built docs:** document the implemented contracts and update the spec's
   document map and glossary mappings as needed. Do not publish planned behavior
   as current functionality.
7. **Review/validation:** run required checks, compare against acceptance criteria,
   report shortcuts and limitations, and stop rather than growing iteration 2.

No hard estimate of time, lines or agents is required. If a step expands into a
large subsystem, reduce the candidate implementation and bring the scope question
back to the user.

## 9. Test checklist

Use existing C tests for low-level boundaries and Python/native-driver tests for
workflow/property checks. Coverage targets remain those of the repository; the
prototype policy does not silently waive them. **Subsequent user policy:** coverage
is a means, not an end. Narrowly justified no-value exclusions are authorized;
record precise lines/branches/regions and reasoning, distinguish exclusions from
tests, and preserve the threshold on remaining code. Difficulty alone is not a
rationale. See [testing guidance](../../../dml/AGENTS.md#testing) and
[review follow-up notes](RESULTS.md#review-follow-up).

### Codec and identity

- [ ] Round trip all new entity types, including initial/later commit parents.
- [ ] Same canonical content produces the same ID.
- [ ] Changed datum/root/tree/parent content changes the corresponding object's ID.
- [ ] Ref movement does not change any immutable object's ID or bytes.
- [ ] Name ordering/normalization and duplicate rules match the actual codec.
- [ ] Truncation, bad counts/offsets/lengths and unsupported kinds fail cleanly.
- [ ] Existing datum vectors and tests remain valid unless an intentional change is
      explicitly justified without a migration promise.

### Storage, history and refs

- [ ] Section 6 succeeds across fresh processes.
- [ ] Reinserting identical immutable objects succeeds.
- [ ] Missing and wrong-type datum/node/DAG/tree/parent/ref-target references reject.
- [ ] Corrupt content under a claimed object key is detected by reads.
- [ ] Branching commit graph is inspectable without merge/rebase.
- [ ] Unknown ref lookup and create/update edge cases have documented errors.
- [ ] Refs can target commits inserted earlier in the same storage transaction.
- [ ] Aborting object inserts plus a ref update preserves the prior head and leaves
      new objects invisible.
- [ ] A failing write after earlier successful inserts prevents the entire batch
      and ref update from becoming visible, even if the caller then tries commit.
- [ ] Existing ownership/lifecycle behavior still holds: consumed handles, buffer
      cleanup, close with active transaction, and read-only write rejection.

A raw corruption fixture can use test-only LMDB access as existing tests do; do not
add production overwrite/delete methods just to inject invalid state. Each test must
clean only scratch it owns.

### Standard validation

From the implementation checkout, use `scripts/check.sh` as instructed by its agent
guide. The default validates tests and enforces coverage thresholds. `-c` is the
existing informational-coverage mode, useful for diagnosis, but is not evidence of
passing the default percentage gates. Apply the subsequently authorized no-value
exclusion policy above; do not lower thresholds, hide meaningful behavior or claim
100% merely because a `-c` run passed.

If dependencies/tooling prevent a required check, report that precisely and request
any needed environment authorization. Do not install globally, invent unjustified
exclusions or turn a skipped stage into success. Valgrind/mutation runs are optional unless requested;
report them only if actually run.

Do not use `scripts/check.sh -f` without understanding its removal of build outputs.
Even without `-f`, the script reconfigures `build/check` using Meson `--wipe` and writes
coverage reports. Inspect relevant ignored outputs before running it. A standalone
`test_repo` binary also uses a relative `test-repository-data` path; run tests in a
controlled test working directory, not a directory containing unrelated data there.

## 10. As-built documentation delivery

Maintain the shared [documentation guidelines](../../../dml/docs/documentation-guidelines.md)
and [spec agent instructions](../../../dml/docs/spec-next/AGENTS.md).

Suggested ownership after implementation:

- `records.md`: common envelope/hash rules and datum encoding; avoid duplicating
  identity rules in each new object description.
- A small new object-model document: implemented node/DAG/tree/commit fields,
  canonicalization and typed-reference structure. Name it for its actual scope.
- `repository.md`: persisted keys, transaction put/get, ref behavior and ownership.
- `glossary.md`: shared meanings; technical documents own concrete behavior.
- `README.md`: orientation, concept ownership and Mermaid document-reference map.

The file split is a recommendation. If the new descriptions are shorter and clearer
in an existing owning document, use that rather than creating empty subsystem pages.
Update authoritative text alongside implemented behavior using the shared change
process. No old-spec rewrites, missing-feature inventories or normative future APIs.

Use **commit** for DML history and **storage transaction** for LMDB batches. A tree
entry name is not named-node lookup. A supported parent list is not a merge operation.

## 11. Deliverables and completion report

Deliver:

1. Minimal implementation in the explicitly authorized checkout/location.
2. Reproducible tests/driver demonstrating the success case and negative cases.
3. Updated as-built docs, glossary where necessary, and document/reference diagram.
4. A short report in this design repository, suggested `RESULTS.md` alongside this
   handoff, covering:
   - actual commits/source state and files changed;
   - representation choices and any deviations from this plan;
   - commands, exit statuses, test units and coverage actually measured;
   - working capability, deliberate shortcuts and unresolved findings;
   - one suggested next turn, without starting it.
5. A current discussion resume point summarizing the outcome.

Completion means the workflow works from newly created state through fresh-process
inspection, immutable/ref boundaries are enforced, required tests are accounted for,
and docs describe the code that exists. An unrun check or unresolved defect remains
visible in the report; a completion label must not hide it.

Do not auto-commit or push from this handoff. Follow the user's explicit commit
instructions, preserve unrelated work and use small focused commits when requested.
If delegating later, keep shared core files under one integration owner and agree
bounded ownership before dispatch; this plan is not a request to spawn workers.

## 12. Stop line

This iteration ends with a minimum viable repository. Do not proceed to execution,
intents, closures, named-node lookup, reuse/masks, remotes, merge/rebase, GC/excision,
resource managers, public binding redesign or observer implementation.

The code-change authorization is established; this handoff preparation did not
start implementation. After implementing this iteration, stop for user review and
selection of the next spiral turn.
