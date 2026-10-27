# Pinned commit transfer

Status: implemented by explicitly imported `daggerml.transfer`.

## Authority boundary

This document owns the transfer API, bundle framing/profile, complete typed object
closure checks, optional ref policy and publication boundaries. [Python API](python-api.md)
owns packed insertion, values and lifetime; [repository](repository.md) owns native
storage validation/atomicity, [records](records.md) owns encoding/identity, and
[objects](objects.md) owns graph fields. [Local execution](local-execution.md) owns
ordinary request/attempt conventions; [CLI](cli.md) owns existing inspection.
Normative sections describe implemented behavior. Terms follow the [glossary](glossary.md).

**Object closure** here is document-local: all typed immutable objects reachable
from a selected commit. It does not mean a computational/environment closure.

## Public API

```python
from daggerml.transfer import (
    export_commit, import_commit, ImportResult, TransferError, RefConflictError,
)

export_commit(repository_path, *, commit: ObjectId) -> bytes
import_commit(repository_path, bundle: bytes, *, ref=None, map_size=0) -> ImportResult
```

Both helpers require an initialized repository and close their own handles before
returning owned data. Paths and `map_size` follow [Repository](python-api.md#repository-and-transactions).
Callers MUST close other handles for the physical repository before invoking them;
the single-wrapper/creating-thread policy is not extended by a global registry.
Export requires an explicit `ObjectId`, never a ref name or implicit head. Import
requires exact immutable `bytes`. `ref` is `None` or an exact string satisfying the
existing [name profile](objects.md#names-and-canonical-ordering).

Frozen `ImportResult` owns `commit: ObjectId`, `object_count: int`, and `ref: Optional[str]`.
Count means validated bundle rows, not newly inserted keys or computational attempts.
Import creates no replacement DML commit. Without a ref it stores objects and returns
the root ID, without inferring a navigation/retention policy.

`TransferError` (a `ValueError`) reports framing/profile, identity, order, cycle or
closure failures with fixed messages, not payload excerpts. `RefConflictError`
specializes it for a readable different-target ref. Native storage/encoding errors
retain [low-level exceptions](python-api.md#errors); Python API type errors remain
`TypeError`. Malformed/deep JSON is rejected without a write batch. Allocation and
IO failures propagate; no automatic growth, repair or partial adoption occurs.

## Complete typed reachability

Export MUST follow these edges in order, deduplicating by `(kind, ObjectId)`:

| Object | Edges |
| --- | --- |
| Commit | Tree, every parent commit in stored order |
| Tree | Every entry DAG in canonical name order |
| DAG | Root node, every binding node in canonical name order |
| Literal node | Datum |
| Sub-DAG-reference node | Target DAG |
| LIST / SET datum | Every datum element in stored order |
| MAP datum | Key then value for every pair in stored order |
| Other datum | None |

A single source read transaction pins all reads. Iterative depth-first traversal
tracks active/completed objects and emits on exit, rejecting cycles while allowing
sharing. Packed records and typed descriptions come from validated public reads;
there is no Python packed codec or alternate hash. All parent history, anonymous
roots, nested/shared DAGs and composite children are included. Missing/corrupt reached
records or profile overflow fail export, never produce a partial successful bundle.
Mutable head movement cannot change export of the same immutable ID.

Metadata, mutable refs, unreachable/other-branch-only data and external resources
are not included. URI/STRING/BYTES contents are data, not graph edges or instructions.
Recorded source is never executed, and historical paths are never followed/deleted.

## Bundle format and supported profile

The owned UTF-8 JSON envelope has exactly these fields (example is abbreviated):

```json
{"format":"daggerml-commit-bundle-v1","root":"<32 lowercase hex>","objects":[{"kind":"datum","id":"<32 lowercase hex>","record":"<base64 packed bytes>"}]}
```

- Top-level fields MUST be exactly `format`, `root`, `objects`; row fields exactly
  `kind`, `id`, `record`. Duplicate JSON keys, missing/unknown fields and wrong
  types are rejected. Format MUST equal `daggerml-commit-bundle-v1`.
- IDs MUST be lowercase 32-hex strings. Kinds MUST be `datum`, `node`, `dag`, `tree`
  or `commit`. Row IDs are assertions checked against native computed identity.
- `record` MUST be standard canonical base64: strict alphabet/padding, no whitespace,
  unused pad bits or excess padding. Decoding is validated then re-encoded for
  equality, using APIs supported by declared Python >=3.8.
- JSON MUST be one valid UTF-8 document, with no trailing document, BOM or nonstandard
  NaN/Infinity constants. Bounded JSON whitespace is accepted.
- Rows MUST contain each typed object once, with dependencies strictly earlier.
  Root MUST be a commit and the final row. All and only its object closure MUST be
  present, even if an omitted dependency already exists in the destination.
- Valid alternative topological orders are accepted. Export uses stable key order
  `format,root,objects` and `kind,id,record`, ASCII escaping and compact separators,
  without a trailing newline or path/time/ref/random metadata. Re-export of the
  same root produces identical bytes, including from another repository.

The module's profile constants are the owning implementation values:

| Limit | Value |
| --- | --- |
| Encoded bundle (`MAX_BUNDLE_BYTES`) | 32 MiB |
| Packed record (`MAX_RECORD_BYTES`) | 4 MiB |
| Sum of packed records (`MAX_PACKED_BYTES`) | 16 MiB |
| Rows (`MAX_OBJECTS`) | 100,000 |

These are transfer-profile bounds, not repository size restrictions or an exact
RSS/time guarantee. The byte API cannot prevent allocation of its caller argument.
JSON parsing allocates before row checks; encoded record size is checked before
base64 decoding and decoded totals incrementally. Export's native validated read
may allocate a large source record before its size check; owned descriptions,
traversal frames, base64 and JSON also allocate. Long read snapshots can retain
LMDB pages. No streaming/native read-size primitive is supplied.

The wrapper label is distinct from native record/schema versions. Unsupported
packed encodings fail native validation; pre-1.0 compatibility/migrations are not
promised. XXH3-128 IDs are content identity, **not authentication** or cryptographic
adversarial-integrity proof.

## Atomic import and optional ref

Import parses framing/profile/duplicates/root placement before opening B. One
helper-owned write storage transaction then:

1. Inserts **every** row with public `put_record`, including existing keys. Checks
   computed ID and exact stored bytes. Native validation/no-overwrite remains
   authoritative for encoding, direct references and existing corruption.
2. Reads each typed description and requires every direct dependency to appear
   in an earlier **bundle row**, not merely in B. This rejects thin/forward/cyclic
   input even when destination objects exist.
3. Traverses accumulated adjacency from the root and rejects unreachable extras.
4. With explicit `ref`, reads it under the same write lock. Missing ref is created;
   a readable same-target ref is preserved; a different target conflicts. Malformed,
   dangling or corrupt targets fail, never repair or overwrite. A dangling ref can
   read `not_found`, but the subsequent create rejects its existing key.
5. Commits only after all checks succeed, then closes and returns the prebuilt
   owned `ImportResult`.

Late row/closure/ref failure, map-full or failed storage commit MUST abort earlier
new objects/ref writes together, leaving unrelated existing state unchanged. The
helper owns the transaction; catching a transfer validation exception cannot expose
a caller-owned partial batch. Initialization/file artifacts are outside this boundary.
Caller-managed map-full recovery closes/reopens with a larger map and retries the
entire bundle; import never grows automatically.

Loss **before commit** leaves old state. During/after commit, complete publication
may exist despite a missing response. Postcommit acknowledgement loss is not rollback
or evidence of failed import. Inspect/reimport explicitly; identical complete bundles
and same-target refs are idempotent, not resumable transfer or a new execution.

## Transferred execution history and trust

Request/attempt occurrences, source bytes, initial unknown states, final outcomes,
cleanup reports and ordered publication parents transfer unchanged. Source request
reservation/attempt publication **refs** do not transfer; stored ref-name strings
remain historical data. Import does not install runnable/recovery state, retry an
unknown attempt, infer a head or act on historical scratch/resources.

Full all-parent history may include sensitive code/logs/data. Copying policy and
destination authority belong to callers; there is no filtering, erasure, external
resource copying, sandbox or complete hostile-input/security audit. Resource URIs
can be unavailable or changed. Recorded cleanup is a historical report, not cleanup
performed at B. Transfer does not certify complete capture or scientific validity.

## Informative example and evidence

With an installed runtime, from outside the checkout:

```sh
python /path/to/examples/pinned_transfer.py /fresh/parent/story
dml --json --repo /fresh/parent/story/destination.dml snapshot --ref received
dml --json --repo /fresh/parent/story/destination.dml log --ref received
```

The [runnable story](../../examples/pinned_transfer.py) executes two real additions
using the existing [trusted child](../../examples/local_add.py), moves the source
head, exports the pinned completion, then imports/inspects through fresh processes.
Ordinary caller-owned file writes are not atomic filesystem publication; partial
files are invalid input, not a partial successful repository import.

Evidence: [module](../../python/daggerml/daggerml/transfer.py),
[packed insertion/closure tests](../../tests/python/test_transfer.py),
[framing/native malformed-record tests](../../tests/python/test_transfer_framing.py),
[process/map-full/fault tests](../../tests/python/test_transfer_process.py) and
[real-attempt example tests](../../tests/python/test_transfer_example.py).
Actual runs, installed provenance, measured versus uninstrumented processes,
negative-oracle scope and platform limits are in
[Iteration 5 results](../../../dml-design/iterations/05-pinned-snapshot-transfer/RESULTS.md).
