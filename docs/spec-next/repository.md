# Local repository and transactions

Status: implemented datum storage, repository schema 1. Not yet a commit/ref API.

## Authority boundary

This document owns local repository initialization, datum keys and reference
checks, transaction behavior and repository/transaction handle ownership in this
as-built specification. For datum encoding, IDs, value buffers and errors, see
[records.md](records.md). For documented scope, see [README.md](README.md).
Terms follow the shared [glossary](glossary.md).

Normative sections describe current code. An LMDB transaction commit is **not** a
DML history commit; history objects and refs have not been implemented.

## Repository contents and initialization

A repository is an LMDB environment using its main database, with:

- `meta/schema`: metadata record containing schema version 1.
- `objects/datums/<id>`: immutable datum records; `<id>` is 32 lowercase hex bytes.

Keys contain the stated bytes without a trailing NUL. Other object keyspaces and
mutable ref keys are not exposed by the current repository API.

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

`dml_txn_begin()` creates a read or write transaction. Datum operations occur inside
that transaction; no public operation stores a datum outside one.

- Write commit makes the transaction's changes visible together through LMDB.
- Abort discards its changes.
- A failed datum write poisons its write transaction. A subsequent commit MUST abort
  the entire batch, including earlier successful puts in that transaction.
- Committing a read transaction is rejected and consumes/aborts the handle.
- `dml_txn_commit()` consumes and nulls its handle on success or failure.
- `dml_txn_abort()` consumes/nulls its handle and is safe for a null handle.

A `map_full` result requires the caller to close and reopen with a larger map and
retry the complete transaction. It does not mean a partial batch should be adopted.

## Writes and reference validation

`dml_txn_put_datum()` requires a valid packed datum, derives its ID and checks direct
composite references against records visible in the transaction. Referenced children
must therefore already exist, or be inserted before their parent in the same batch.

References MUST resolve to valid datum records with matching IDs. Missing references,
wrong record types, excised records and detected ID mismatches are rejected.
The checks are not a general DAG reachability or cycle-validation facility.

Insertion uses no-overwrite semantics:

- Re-inserting identical bytes under the same ID succeeds without replacing them.
- Different bytes under an existing ID MUST produce an integrity error.
- The public API exposes no datum overwrite or deletion operation.

## Reads and integrity

`dml_txn_get_datum()` checks the stored envelope, record type and content ID, and
validates the requested datum's direct composite references. It returns a copied,
owned buffer rather than memory borrowed from LMDB. See
[records.md](records.md#c-api-ownership).

A missing record returns `not_found`. A datum with a mismatched content-addressed
key returns `integrity_error`.

There is limited recognition of a tombstone record found at a datum key: an
accepted tombstone shape is rejected as `invalid_payload` with detail
`record_type=tombstone;detail=excised`. This does not implement an excision request,
tombstone writer, deletion authority, GC, external cleanup or physical erasure.

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
encode and insert child datums
encode and insert a LIST referring to those children
commit storage transaction
close repository

reopen repository
begin read transaction
get LIST by its datum ID
abort/end read transaction
close repository
```

This is datum persistence, not yet creation of a DML tree, commit graph or ref.

## Implementation evidence

- [repo.c](../../src/repo.c): initialization, transactions and datum persistence.
- [Public repository API](../../include/dml/repo.h).
- [C repository tests](../../tests/c/test_repo.c): lifecycle and negative cases.
- [Native-driver repository tests](../../tests/python/test_repository_hypothesis.py):
  fresh-process reads, abort invisibility and failed-batch rollback.

These identify existing checks; this documentation pass did not rerun them.
