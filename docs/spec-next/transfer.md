# Commit transfer

## Authority boundary

This document owns the binary commit bundle and its C import/export contract.
[Records and datums](records.md) owns packed records and content IDs;
[repository and transactions](repository.md) owns local persistence and refs.

## Repository behavior

A **commit bundle** is a self-contained encoding of one DML commit and its
transitive object dependencies. Starting at that commit, follow every typed,
direct [object reference](repository.md#writes-and-reference-validation), including
all parent commits. The bundle MUST contain exactly the resulting typed objects,
one frame per (type, ID) pair. Dependencies MUST appear before any frame that
refers to them. The final frame MUST be the commit named in the bundle header.

- `dml_repo_export_commit()` reads one repository snapshot. It MUST preserve the
  stored packed bytes and object IDs. Export of unchanged objects under the same
  root is deterministic; a particular order among independent frames is not a
  wire requirement. Missing or invalid dependencies cause export to fail.
- `dml_repo_import_commit()` validates the framing, packed records, IDs, order,
  and exact root closure before writing. It MUST reject omitted objects even if
  the destination has them. It MUST use one write transaction and leave the
  destination unchanged on failure. Existing byte-identical objects are reused;
  conflicting stored values are not replaced. Importing the same bundle again
  succeeds when the stored data still agrees with it.
- Neither operation creates, moves, or transfers refs. A bundle is external
  data, not a stored LMDB record. It does not capture resources addressed by URIs.
- The repository handle MUST have no active transactions for either call.
  Export takes an empty `dml_buffer`; on success the caller owns it and frees it
  with `dml_buffer_free()`. Import borrows its input bytes for the duration of the
  call and writes the returned root ID only after committing successfully.

## Binary format version 1

All integer fields are unsigned little-endian. IDs are the 16 raw bytes of the
content ID, not hex text. Sizes include exactly the bytes described below; no
padding or trailing data is permitted.

| Header offset | Bytes | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `DMLB` |
| 4 | 4 | Version `1` |
| 8 | 16 | Root commit ID |
| 24 | 4 | Frame count |

The 28-byte header is followed by exactly that many frames:

| Frame offset | Bytes | Field |
| ---: | ---: | --- |
| 0 | 2 | Record type tag: `2` datum, `3` node, `4` DAG, `5` tree, `6` commit |
| 2 | 2 | Reserved, MUST be zero |
| 4 | 4 | Byte length of the packed record |
| 8 | 16 | Object ID |
| 24 | As declared | Complete packed record, including its record envelope |

Both directions enforce a maximum of 64 MiB for the whole bundle, 16 MiB per
packed record, and 262,144 frames. The frame count MUST be nonzero. Import checks
the whole-buffer size and declared frame count before parsing frames. No earlier
JSON/base64 transfer format is accepted. The limits bound encoded data, not
peak memory or processing time. Content IDs are not cryptographic proofs of
origin or authenticity.

## Failures

| Condition | Status |
| --- | --- |
| Null required argument or nonempty export output | `invalid_argument` |
| Active repository transaction | `invalid_state` |
| Wrong bundle magic/version or nonzero frame reserved field | `invalid_header` |
| Truncation, invalid framing length/count, size limit, or trailing bytes | `invalid_bounds` |
| Unsupported frame type or mismatch with its packed type | `invalid_kind` |
| Incorrect frame ID or final commit ID differing from the header | `integrity_error` |
| Duplicate, absent, misordered, or unrelated frame; final frame is not a commit | `invalid_payload` |
| Missing stored object during export | `not_found` |

Packed-record and repository failures otherwise preserve their underlying status
(for example `map_full` on import). Apart from the order of checks specified
above, applications MUST NOT rely on precedence when multiple checks would fail.
A failed export with a valid empty output leaves it empty. A failed import does
not change the root ID output.

## Informative example

With two open repository handles and no active transactions:

```c
dml_buffer bundle = {0};
dml_object_id imported;
dml_status status = dml_repo_export_commit(source, &root, &bundle, &error);
if (status == DML_OK) {
  status = dml_repo_import_commit(dest, (dml_bytes){bundle.data, bundle.len},
                                  &imported, &error);
}
dml_buffer_free(&bundle);
/* On success, imported equals root. The caller may publish a ref separately. */
```

See [transfer.h](../../include/dml/transfer.h) and [transfer.c](../../src/transfer.c).
