# Local repository and transactions

Status: implemented immutable-object storage and transactional refs, repository schema 1.

## Authority boundary

This document owns local repository initialization, persisted object/ref keys,
direct reference checks, transaction behavior and repository/transaction handle
ownership in this as-built specification. For encoding, IDs, value buffers and
errors, see [records.md](records.md). For snapshot/history fields and the shared
name profile, see [objects.md](objects.md). For documented scope, see [README.md](README.md).
Terms follow the shared [glossary](glossary.md).

Normative sections describe current code. Committing a **storage transaction** is
not creating a DML history **commit**.

## Repository contents and initialization

A repository is an LMDB environment using its main database, with:

- `meta/schema`: metadata record containing schema version 1.
- `objects/datums/<id>`: immutable datum records.
- `objects/nodes/<id>`, `objects/dags/<id>`, `objects/trees/<id>` and
  `objects/commits/<id>`: the corresponding immutable records.
- `refs/heads/<name>`: mutable raw 16-byte commit target IDs.

`<id>` is 32 lowercase hex bytes. Keys contain the stated bytes without a trailing
NUL. Ref values are not record envelopes and do not have content identities.

`dml_repo_open()` accepts a path and optional creation/map-size options.

- Without creation, opening MUST require an initialized supported repository.
- With creation, a missing or empty directory may be initialized. The caller must
  supply an existing parent directory; initialization is not recursive.
- The implementation MUST reject an unrelated nonempty directory, malformed schema,
  unsupported schema, or nonempty database with no schema. It MUST NOT replace them.
- Schema initialization uses one write transaction. An empty LMDB database left by
  interrupted initialization remains eligible for creation.
- Errors may leave newly created filesystem artifacts; initialization is not an
  atomic filesystem-directory operation.

The default map size is 64 MiB. A nonzero configured size below 1 MiB is rejected.
The API exposes no automatic map-growth operation.

## Transactions

`dml_txn_begin()` creates a read or write transaction. Object and ref operations
occur inside that transaction; no public operation stores them outside one.

- Write commit makes the transaction's changes visible together through LMDB.
- Abort discards its changes.
- A failed object or ref write poisons its write transaction. A subsequent commit
  MUST abort the entire batch, including earlier successful puts and ref changes.
- Committing a read transaction is rejected and consumes/aborts the handle.
- `dml_txn_commit()` consumes and nulls its handle on success or failure.
- `dml_txn_abort()` consumes/nulls its handle and is safe for a null handle.

A `map_full` result requires the caller to close and reopen with a larger map and
retry the complete transaction. It does not mean a partial batch should be adopted.

## Writes and reference validation

`dml_txn_put_datum()` requires a valid packed datum. `dml_txn_put_object()` requires
an explicit expected type (node/DAG/tree/commit) matching the packed record. Both
derive the object's ID and check its direct references against records visible
in the storage transaction. Referenced objects must already exist or be inserted
earlier in the same batch.

References MUST resolve to valid records of the expected type with matching
key/content IDs. Direct relationships are:

| Object | Direct referenced types |
| --- | --- |
| Composite datum | Datum elements, keys and values |
| Literal node | Datum |
| DAG | Root node |
| Tree | Entry DAGs |
| Commit | Tree and each parent commit |

Missing new-object references return `not_found`; the existing composite-datum
API reports `invalid_kind` for missing children. An ID belonging to another type
normally does not exist in the expected typed keyspace and returns the same
missing-reference error. A record of the wrong type found under an expected key
returns `invalid_kind`.

These are **direct**, not transitive checks: referenced records' encoding and ID
are checked, but their own references are not recursively resolved. Construction
order provides a simple discipline, not a general graph-cycle proof or validation
of an externally corrupted store.

Insertion uses no-overwrite semantics:

- Re-inserting identical bytes under the same ID succeeds without replacing them.
- An existing value MUST never be replaced. A different valid encoding under the
  claimed ID produces an integrity error; malformed encoding or a wrong stored
  type produces the corresponding validation error.
- The public API exposes no immutable-object overwrite or deletion operation.

## Reads and integrity

`dml_txn_get_datum()` and `dml_txn_get_object()` check the stored envelope, expected
record type, content ID and requested object's direct references using the same
rules as writes. They return copied, owned buffers rather than memory borrowed from
LMDB. See [records.md](records.md#c-api-ownership).

A missing object returns `not_found`. An object with a mismatched content-addressed
key returns `integrity_error`. Invalid encoding returns the relevant codec error.

There is limited recognition of a tombstone record found at an immutable-object key: an
accepted tombstone shape is rejected as `invalid_payload` with detail
`record_type=tombstone;detail=excised`. This does not implement an excision request,
tombstone writer, deletion authority, GC, external cleanup or physical erasure.

## Refs

Ref names MUST satisfy the [ASCII name profile](objects.md#names-and-tree-ordering).
The caller supplies a short name such as `main`; storage adds `refs/heads/`.
Names are case-sensitive repository data, not filesystem paths.

- `dml_txn_ref_create()` MUST reject an existing ref with `invalid_state`, even if
  the supplied target is identical. It never overwrites.
- `dml_txn_ref_update()` MUST require an existing ref. Missing refs return
  `not_found`; an existing value whose width is not 16 bytes returns
  `integrity_error`. An update replaces the target, not an immutable object.
- Create/update MUST check that the supplied target is a valid commit with matching
  ID and valid direct tree/parent references. Targets inserted earlier in the same
  storage transaction are permitted. Target validation precedes the existence check.
- `dml_txn_ref_get()` copies the target ID, validates its commit and direct references,
  and returns `not_found` for an absent ref or absent target. Wrong-width ref values
  return `integrity_error`.
- Updating validates the new target, not the previous target's existence/integrity;
  a correctly sized dangling ref can therefore be explicitly repaired.

A storage transaction can publish an entire snapshot and its ref target atomically.
Moving a ref does not change historical object bytes or IDs. Update does not impose
ancestry/fast-forward policy or compare-and-swap semantics.

## Handle ownership and concurrency

Public declarations are in [repo.h](../../include/dml/repo.h).

- Repository and transaction output slots MUST initially be null.
- A transaction MUST be used and ended by its creating thread.
- Calls sharing one repository handle and its transactions require external
  synchronization; callers MUST NOT assume thread-safe concurrent use.
- Callers should share one repository handle for a physical repository within a
  process. Separate processes can open the same repository using LMDB locking.
- `dml_repo_close()` MUST reject a repository with active transactions. A successful
  close consumes and nulls its handle.

These local transaction guarantees do not establish remote publication atomicity,
compare-and-swap ref updates or exactly-once external execution.

## Informative example: current capability

```text
open/create local repository
begin write transaction
encode/insert datum 42, literal node, rooted DAG, tree entry example
encode/insert initial commit C1 referencing that tree
create ref main -> C1
commit storage transaction
begin another write transaction
encode/insert analogous 43 snapshot and commit C2 with parent C1
update ref main -> C2
commit storage transaction
close repository

in a fresh process, reopen repository and begin a read transaction
resolve main; read C2's tree/DAG/node/datum to obtain 43
follow C2's parent C1; read its snapshot to obtain 42
abort/end read transaction
close repository
```

See [history_driver.c](../../tests/c/history_driver.c) for a native example of
construction and inspection through this API.

## Implementation evidence

- [repo.c](../../src/repo.c): initialization, transactions, object and ref persistence.
- [Public repository API](../../include/dml/repo.h).
- [C repository tests](../../tests/c/test_repo.c): lifecycle and negative cases.
- [Native-driver repository tests](../../tests/python/test_repository_hypothesis.py):
  fresh-process reads, abort invisibility and failed-batch rollback.
- [History tests](../../tests/python/test_history.py): fresh-process inspection,
  branching, ordered multiple parents, immutable content, ref edges, corruption,
  and atomic object/ref rollback even after attempted poisoned commit.

Actual validation runs and outstanding gates are recorded in the
[Iteration 1 delivery notes](../../../dml-design/iterations/01-minimum-viable-repository/RESULTS.md).
