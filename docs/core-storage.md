# Core Storage

Status: Implemented for record format 1 and repository schema 1.

## Overview

The native C core encodes and validates canonical datum records, derives stable
16-byte object ids, and stores immutable datums in LMDB transactions. The wire
format, hashing domain, keyspace, and validation classes are defined by
`docs/spec/object-model.md` Sections 4-10.

The implementation supports all ten datum kinds. Composite records contain
datum object ids rather than nested records. Insert children before their LIST,
SET, or MAP parent in the same write transaction.

## Dependencies

- xxHash 0.8.3 provides unseeded XXH3-128 object ids.
- LMDB 0.9.35 provides local transactional storage.
- utf8proc 2.11.3 provides UTF-8 validation and NFC using Unicode 17.0.0. It is
  distributed under the MIT and Unicode Data licenses.
- uriparser 1.0.2 provides RFC 3986 parsing and syntax normalization. It is
  distributed under the BSD-3-Clause license.

All dependencies are pinned as static Meson wrap fallbacks and have
length-aware boundaries in the core. Their types do not appear in installed DML
headers.

## Ownership

- `dml_datum_encode()`, `dml_uri_canonicalize()`, and
  `dml_txn_get_datum()` return core-owned `dml_buffer` allocations. Release
  them with `dml_buffer_free()`. The function is safe on an empty buffer.
- `dml_datum_decode()` returns a borrowed view. Keep the packed input alive and
  unchanged while using the view or its accessors.
- `dml_txn_commit()` consumes and nulls a write transaction on success and
  failure. `dml_txn_abort()` consumes a transaction and is null-safe.
- A failed write operation poisons its transaction. A later commit aborts the
  complete batch.
- `dml_repo_close()` reports `invalid_state` while a transaction is active.
  Share one repository handle for a physical repository within a process.
- Calls on a shared repository and its transactions require external
  synchronization. A transaction is thread-affine and must be used and ended
  by its creating thread. Separate processes may open the repository normally.

Every function accepts an optional caller-owned `dml_error`. Its status,
native code, and fixed-size detail storage require no error-path allocation.
The `map_full` status means the caller must close, reopen with a larger
`map_size`, and retry the complete transaction.

## Example

```c
#include <stdint.h>
#include <stdio.h>

#include <dml/dml.h>

int main(void) {
  dml_repo_options options = {true, DML_REPO_DEFAULT_MAP_SIZE};
  dml_datum_input input = {.kind = DML_DATUM_I64, .value.i64 = 42};
  dml_buffer record = {0};
  dml_object_id id;
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_error error;

  if (dml_datum_encode(&input, &record, &error) != DML_OK ||
      dml_repo_open("example.dml", &options, &repo, &error) != DML_OK ||
      dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) != DML_OK ||
      dml_txn_put_datum(txn, record.data, record.len, &id, &error) != DML_OK ||
      dml_txn_commit(&txn, &error) != DML_OK) {
    fprintf(stderr, "%s: %s\n", dml_status_name(error.code), error.detail);
    dml_txn_abort(&txn);
    if (repo != NULL) dml_repo_close(&repo, NULL);
    dml_buffer_free(&record);
    return 1;
  }

  dml_buffer_free(&record);
  return dml_repo_close(&repo, &error) == DML_OK ? 0 : 1;
}
```

Opening with `create=false` requires an initialized repository. Opening with
`create=true` initializes a missing or empty directory whose parent exists but
does not replace an unrelated nonempty directory or incompatible schema.
Initialization can leave newly created filesystem artifacts after an error;
retrying creation is safe after the underlying error is corrected.
