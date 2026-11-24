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
- Export and unpinned import do not change refs. A bundle includes no refs and
  is external data, not a stored LMDB record. It does not capture resources
  addressed by URIs.
- The repository handle MUST have no active transactions for export or either
  form of import. Export takes an empty `dml_buffer`; on success the caller owns
  it and frees it with `dml_buffer_free()`. Import borrows its input bytes for the
  duration of the call and writes the returned root ID only after committing
  successfully.

### Atomic staging

`dml_repo_import_commit_staged()` MUST apply the same bundle validation and
object insertion rules as unpinned import and create a local [ref](repository.md#refs)
to the bundle root in the same write transaction. The caller supplies a short
ref name such as `incoming`. An existing ref MUST be rejected even if it already
points to the bundle root. Failure leaves the repository and root ID output
unchanged. No other ref is created or moved, and the bundle format is unchanged.

A staging ref is an ordinary [retention root](repository.md#retention-roots), not
an approval of the commit. With atomic staging, [garbage collection](repository.md#explicit-garbage-collection)
cannot run between the insertion and creation of the ref. The ref retains the
bundle closure while it targets the root. Unpinned import followed by a separate
ref creation has no such guarantee.

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
| Null required argument, nonempty export output, or invalid staging ref name | `invalid_argument` |
| Active repository transaction or existing staging ref | `invalid_state` |
| Wrong bundle magic/version or nonzero frame reserved field | `invalid_header` |
| Truncation, invalid framing length/count, size limit, or trailing bytes | `invalid_bounds` |
| Unsupported frame type or mismatch with its packed type | `invalid_kind` |
| Incorrect frame ID or final commit ID differing from the header | `integrity_error` |
| Duplicate, absent, misordered, or unrelated frame; final frame is not a commit | `invalid_payload` |
| Missing stored object during export | `not_found` |

Packed-record and repository failures otherwise preserve their underlying status
(for example `map_full` on import). Apart from the order of checks specified
above, applications MUST NOT rely on precedence when multiple checks would fail.
A failed export with a valid empty output leaves it empty.

## Informative example

With two open repository handles and no active transactions:

```c
dml_buffer bundle = {0};
dml_object_id imported;
const dml_bytes incoming = {(const uint8_t *)"incoming", sizeof("incoming") - 1};
dml_status status = dml_repo_export_commit(source, &root, &bundle, &error);
if (status == DML_OK) {
  status = dml_repo_import_commit_staged(dest, (dml_bytes){bundle.data, bundle.len},
                                         incoming, &imported, &error);
}
dml_buffer_free(&bundle);
/* On success, imported equals root and incoming retains it. */
```

Stage an import under `incoming` to inspect it without changing `main`. After
reopening, resolve `incoming` in a read transaction, then read the commit and
follow its ordered parent IDs. If the candidate is accepted, publish the commit
ID that was actually inspected in a separate write transaction. The
[standalone C example](../../examples/transfer_history.c) demonstrates this flow.

### Record a result without publishing to `main`

The standalone example's `--lineage` mode passes the staged input value to a
caller-supplied C function. The caller keeps the commit ID it inspected rather
than resolving `incoming` again. It writes a result commit with that input as its
sole parent and creates `result-pin` in the same write transaction. A duplicate
pin rejects the transaction, including any new result objects. `main` and
`incoming` are untouched.

The result tree has one entry, `lineage-v1`. Its DAG has an `output` I64 literal
(which is also the root) and an `implementation` STRING literal holding the
caller's versioned implementation identifier. The caller knows the input datum
path within the parent snapshot. After reopening, it reads the recorded result,
identity and parent through `result-pin`; no computation is rerun. This is an
application convention using ordinary commits, datums and refs. DML does not
execute the function, attest that it ran, or store its code.

### Return and publish the recorded result

The example's `--round-trip` mode exports the result commit selected by the
worker's `result-pin` and atomically stages it under `returned` in the source
repository. The bundle includes the lineage objects and the complete input
history, even where the source already has those objects. The pin stays local to
the worker. The source inspects the staged commit by ID, checking its sole
parent, input, output, and implementation identifier without executing the
computation.

The source then reads `main` in a write transaction and moves it to the inspected
result ID only if `main` still points to the expected tip. A stale expectation
aborts publication and leaves `returned` in place for further inspection or
explicit release. This is a caller-side conditional update, not a merge. After
successful publication, the example releases `returned` only if it still points
to the inspected result. It reopens the source and checks the same lineage
through `main`. Returning and publishing the result do not change the worker's
refs.

The example then releases the worker's `incoming` in a separate write transaction,
only if it still points to the input it inspected. After reopening, `incoming`
is absent and `result-pin` still yields the result and its original input via the
result's parent link. See [retention roots](repository.md#retention-roots).

### Resume a handoff across processes

The [provenance handoff example](../../examples/provenance_handoff.c) separates the
requester, worker and publisher into invocations. Each bundle is an ordinary
commit bundle; refs stay local. The lineage is **result → request → input snapshot**,
where each arrow is a sole parent link.

- **Request.** The requester selects the source's current `main` as the input
  snapshot. The request's tree has one entry, `request-v1`. Its DAG has three
  STRING literal bindings: `input-entry` and `input-binding` select an I64
  literal in the input snapshot, and `operation` (also the DAG root) names a
  versioned operation. The requester stores the request commit and creates
  `request-pin` in one write transaction before exporting it. Selecting a
  different operation or input path changes the request ID even when the input
  snapshot is unchanged. This is an example convention, not a new core record
  type or execution API.
- **Work.** The worker stages the request bundle under `incoming`. It reads the
  operation and selector from that exact request and dispatches only
  `example.add-one@1` or `example.subtract-one@1`. It commits the `lineage-v1`
  result and `result-pin` together, then exports the result. The result's claimed
  implementation ID is the selected operation ID.
- **Publish.** The publisher stages the result under `returned` and compares
  its parent with the source's independently pinned request. It checks the
  input selector, result shape, datum kinds and claimed implementation ID; it
  does not recompute the output or verify its correctness or origin. In one
  write transaction it checks that `main` still points to the request's input
  snapshot, publishes the inspected result, and deletes `returned` and
  `request-pin` only at their inspected targets. A mismatched request, stale
  tip, or failed guarded deletion leaves publication unapplied and the staged
  result available for inspection unless another caller has moved or removed it.

The worker can release `incoming` in a separate command. In one write
transaction it inspects `result-pin` and releases `incoming` only if it points
at the result's exact request parent. `result-pin` still retains the result,
request and input snapshot through collection. See
[running and resuming the example](../../README.md#three-process-provenance-handoff)
for supported checkpoints and file-handling limits.

#### Inspect a committed checkpoint

`inspect source SOURCE` and `inspect worker WORKER` report the selected role's
refs and checkpoint in a single read transaction. When the request can be
read, the report includes its ID, input snapshot ID, operation, and selector.
Inspection does not run a computation, use bundle files, or write repository
objects or refs.

- **Source:** `request-pin` marks a pinned request; `returned` marks a staged
  result. For a staged result, inspection checks the same request, result, and
  input-tip conditions as publication. A blocker is reported on stderr and
  causes a nonzero exit. A ready report applies only to the read snapshot;
  `publish` still checks `main` and the staging refs in its write transaction.
  `inactive` means neither handoff ref resolved. It does not say whether an
  earlier handoff was published.
- **Worker:** `incoming` marks a staged request; `result-pin` marks a recorded
  result. The report follows the pinned result's parent even after `incoming`
  is released. If a resolved `incoming` points elsewhere, inspection reports
  why it cannot be released and exits nonzero. It does not predict whether
  execution, export, or publication can succeed.

A ref reported as `not found` could be absent or have an unresolvable target.
This example opens the repository normally; inspection is not a filesystem
read-only mode, an integrity scan, or evidence of execution correctness.

See [transfer.h](../../include/dml/transfer.h) and [transfer.c](../../src/transfer.c).
