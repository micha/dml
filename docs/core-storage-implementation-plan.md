# Core Storage Implementation Plan

Status: Core behavior implemented; coverage, failure injection, snapshot tests,
mutation instrumentation, and cross-platform CI verification remain incomplete.

Prepared: 2026-09-13.

Repository baseline: `21ddd5ab2dffc0f6619724f131cd8eb4617f005b` on `master`.

## 1. Purpose and authority boundary

Implement the first useful C-core milestone: canonical datum records that can be
validated, assigned stable object ids, and persisted transactionally in a local
repository. This is the foundation for the later DAG/commit/Python vertical slice.

This document owns implementation sequencing, proposed module boundaries, test
strategy, and milestone acceptance criteria. It is informative, not a second
on-disk specification. Proposed decisions below are not established format rules.

Technical sources of truth:

- [Object model](spec/object-model.md), Sections 4-10: encoding, identity,
  schemas, keyspace, repository semantics, and validation errors.
- [Python bindings](spec/python-bindings.md): eventual public Python behavior.
- [CLI](spec/cli.md): eventual user-facing commands.
- [Documentation guidelines](documentation-guidelines.md): documentation
  ownership and change process.
- [Agent guide](../AGENTS.md): coding, testing, and collaboration conventions.

Implementation authorization was granted on 2026-09-13. This plan remains an
informative checklist; format rules accepted during implementation are recorded
in the authoritative object model.

## 2. Starting point

Recheck these facts at implementation time; they describe the baseline above.

| Area | Existing implementation and consequence |
| --- | --- |
| Public core | `include/dml/dml.h` exposes only `dml_version()` and `DML_VERSION`. Add APIs without breaking either. |
| C sources | `src/dml.c` implements version reporting; `src/cli.c` handles only `--version` and `-V`. |
| Build | Root `meson.build` builds a C11 static `libdml`, the native CLI, and `test_version`; `dml_dep` already carries native dependencies. |
| Dependencies | `subprojects/xxhash.wrap` pins xxHash 0.8.3; `subprojects/lmdb.wrap` pins LMDB 0.9.35. Meson overlays are in `subprojects/packagefiles/`. |
| Python | `python/daggerml/meson.build` builds a separate placeholder extension without `libdml`. Existing scaffold tests mock its import. |
| Tests | `tests/c/test_version.c`, `tests/python/test_cli_hypothesis.py`, and `tests/python/test_python_scaffolds.py` cover scaffold behavior. |
| Validation | `scripts/check.sh` builds with coverage, runs Meson tests and pytest, and enforces 100% C line/function/branch and Python line coverage. |
| CI | `.github/workflows/ci.yml` tests Linux x86_64/aarch64, macOS x86_64/arm64, and Windows AMD64; a separate Linux job runs the strict check script. |
| Mutation checks | `.mull.yml` exists, but `scripts/check.sh -m` defaults to `test_version`. New code needs explicit mutation targets. |
| Architecture | `docs/architecture.md` is deliberately a placeholder. There is no implemented repository or record layer to extend. |

The worktree contained a pre-existing modification to `AGENTS.md` when this plan
was prepared. Read the current file and preserve that work. This planning session
did not run builds or tests; existing coverage artifacts are not a baseline pass
for the new milestone.

## 3. Milestone boundary

### 3.1 Deliverables

1. Explicit byte-oriented encoding/decoding helpers and stable validation errors.
2. Canonical encoding, structural validation, and decoding for all ten datum
   kinds in object-model Section 7.2.
3. Stable 16-byte object ids and lowercase hexadecimal conversion.
4. Metadata record support sufficient to initialize and check `meta/schema`.
5. Local repository open/create/close and explicit read/write transactions.
6. Immutable datum insertion, retrieval, duplicate handling, and direct
   composite-reference checks within a transaction.
7. A test-only native driver for Python property tests, focused low-level C
   tests, and coverage/memory/mutation evidence.
8. Concise documentation of the implemented C API, ownership, and one storage
   example.

The completion demonstration is: construct scalar and composite datums, store
them in one transaction, commit, close, reopen in a fresh process, and recover
the same canonical bytes and ids. An aborted batch leaves none of its new
objects visible.

### 3.2 Follow-on work

The next milestone after this one adds node/DAG/tree/commit codecs, graph-aware
validation, atomic refs, and a minimal local DAG commit/readback workflow. The
public Python bindings then link the real core and expose that workflow.

This milestone provides no general DAG builder, execution records or scheduler,
remote transfer, GC/excision writer, migration engine, or repository-facing CLI
commands. It recognizes tombstone reads as specified, without implementing
excision. It does not introduce a temporary public Python storage API.

The three execution questions in object-model Section 11 do not block datum
storage. Do not assign an ad hoc keyspace to `DML_REC_EXEC_REQUEST` here.

## 4. Phase 0: close format and API decisions

The draft specifies the major invariants but does not fully determine the bytes
of every value. Settle these details before recording golden ids or writing
persistent objects. Record accepted format choices in the authoritative object
model first; keep this plan as the implementation checklist.

### 4.1 Proposed format decisions

The recommendations in this table need reconciliation with the owner and the
current spec. They are concrete starting points, not claims about existing rules.

| Decision | Recommended resolution | Authority to clarify |
| --- | --- | --- |
| Record and repository versions | Begin with record-format version 1 and schema version 1, with separate constants from tool version `0.1.0`. Support exactly that window initially; reject other versions without migrating. | Object model Sections 4, 7.1, 10 |
| Reserved header flags | Writers emit zero; version-1 readers reject nonzero flags. Stored checksum is zero as already specified. | Sections 4, 10 |
| Packing beyond the header | Serialize fields consecutively with no C ABI padding. Do not extend the header's `#pragma pack` example into an assumption about native struct layout. | Sections 4, 5.1, 7 |
| Empty datum payload | Use `payload_ofs = 40` even for zero-length payloads; payload occupies the remainder of the record. | Sections 5.2, 7.2 |
| Scalar payloads | NULL: zero bytes. BOOL: one byte, 0 or 1. I64: eight-byte little-endian two's-complement representation. F64: eight-byte little-endian IEEE-754 binary64. BYTES: exact input bytes. | Sections 5.1, 7.2 |
| Canonical NaN | Use quiet-NaN bits `0x7ff8000000000000`. All NaN signs/payloads lower to that value; negative zero lowers to positive zero; preserve infinities. | Section 5.5 |
| Digest byte order | Treat ids as opaque byte arrays in xxHash's canonical 128-bit representation: high 64 bits then low 64 bits, each big-endian. This is distinct from little-endian numeric record fields. | Section 6 |
| Hash parameters | Use the default unseeded XXH3-128 variant; specify this explicitly alongside the algorithm name. | Section 6 |
| String normalization | Typed STRING construction accepts valid UTF-8 and normalizes NFC; stored-record validation rejects non-NFC bytes. Strings are length-delimited and may contain U+0000; names have separate constraints. | Sections 5.3, 7.2 |
| URI profile | Adopt an explicit syntax-based canonicalization profile and conformance vectors, described below. Reject reserved `dml:` schemes at all user-facing URI entry points. | Sections 5.3, 7.2; Python bindings Section 5 |
| Content-addressable types | For this milestone, expose datum hashing/storage only. Metadata remains at `meta/schema`; refs and tombstones do not gain content-addressed insertion APIs. | Sections 3.1, 6, 8 |

Recommended URI profile to resolve in Phase 0:

- Parse absolute RFC 3986 URIs; define whether relative references are rejected
  explicitly rather than accidentally accepting them in a generic parser.
- Use ASCII URI serialization. Raw non-ASCII text belongs to a future, separately
  specified IRI conversion boundary; percent-encoded UTF-8 remains representable.
- Lowercase the scheme and host; uppercase percent-escape hex digits; decode
  escapes for unreserved characters, preserving escaped reserved delimiters.
- Apply dot-segment removal to hierarchical paths. Explicitly define handling
  for rootless, scheme-specific paths such as URNs before implementing it.
- Preserve query ordering, fragments, significant empty components, and explicit
  ports. Avoid scheme-specific equivalences such as removing HTTP default ports
  unless the spec deliberately adopts them.
- Specify normalization order, including percent-encoded dot segments, with
  vectors. Include authorities, IPv6 literals, empty paths, rootless paths,
  queries, fragments, and malformed escapes.
- A URI datum encoder accepts canonical input only. A separate core normalization
  helper can support the future `Uri.from_string(raw)` API. Both reject a scheme
  equal to `dml` after case normalization; no public bypass boolean is needed in
  this milestone.

“RFC 3986 canonical form” alone does not settle every equivalence above. If these
decisions remain unresolved, report the milestone as blocked at Phase 0 rather
than substituting ASCII-only STRING support or an unspecified URI algorithm.

### 4.2 Text dependencies

The current dependencies do not provide complete NFC normalization or URI
parsing. Prefer established small C libraries over hand-written Unicode tables
or a new general-purpose URI parser:

- Evaluate utf8proc for UTF-8 validation and NFC normalization.
- Evaluate uriparser for RFC 3986 parsing and syntax normalization, with an
  explicit DML profile layered above it.
- Resolve current official documentation using the documentation workflow in
  the applicable agent instructions. Check exact APIs against the selected
  release, including allocation/free pairing and embedded-NUL handling.
- Before implementation, select exact releases and record source URLs, archive
  hashes, licenses, Unicode version, and supported platforms. Use the existing
  static Meson wrap/overlay pattern and expose dependencies through `dml_dep`.
- Verify Windows and both architecture families before depending on a library.
  Keep Python runtime dependencies at zero. Do not edit extracted subproject
  trees as the source of a patch.

These are dependency recommendations, not completed evaluations. If a candidate
cannot satisfy the profile or build matrix, document the replacement decision
before writing the normalization layer.

### 4.3 Repository and operational API decisions

Document these as C API behavior, adding authoritative repository semantics only
where they affect interoperability:

- Treat `path` as the LMDB environment directory itself; do not introduce an
  implicit `.dml` subdirectory or a named database per object type. Use the main
  database and the spec's textual key prefixes.
- `create=false` opens only an initialized repository. A missing path, empty
  directory, or missing schema fails without initializing a repository.
- `create=true` opens a valid repository or initializes a missing/empty directory
  whose parent exists. An existing nonempty directory with no valid schema is
  an error, not an invitation to overwrite an unrelated database.
- Initialize schema and optional creation metadata in one write transaction.
  Initialization failure may leave newly created filesystem artifacts; document
  retry behavior and never remove unrelated files during cleanup.
- Expose a byte-count map-size option with a documented finite default; 64 MiB
  is a proposed starting value for new environments. Define reopen behavior so
  an existing environment is not silently shrunk. Report map exhaustion with
  remediation; automatic resizing and retry are follow-on work.
- Use normal LMDB locking and durability. Do not enable relaxed-sync, unlocked,
  or writable-mapping modes as a default optimization.
- Make transactions explicit, with one thread using a transaction at a time and
  no nested write transactions initially. Document the pinned LMDB restrictions
  on concurrent transactions and environment handles.
- Require callers to share one repository handle per physical repository within
  a process. Do not open the same LMDB environment twice or introduce a hidden
  global handle registry. Separate processes may open the same repository.

Phase 0 exit: the accepted byte rules, URI vectors/dependency choices, open/create
semantics, ownership model, and operational errors are documented sufficiently
to write independent fixtures. Record any remaining unresolved choice explicitly.

## 5. Proposed implementation structure

Keep public interfaces narrow and byte layout private. The filenames below are
proposed additions, not files that exist at the baseline.

| File | Responsibility |
| --- | --- |
| `include/dml/dml.h` | Retain the version API and include the new public headers. |
| `include/dml/error.h` | Status enum and caller-owned error information. |
| `include/dml/record.h` | Object id, owned buffer, typed datum input/view, codec and id APIs. |
| `include/dml/repo.h` | Opaque repository/transaction handles, options, lifecycle, datum put/get. |
| `src/error.c` | Stable error-code names and allocation-free error formatting. |
| `src/encoding.c`, `src/encoding.h` | Checked length arithmetic and explicit little-endian byte access; private header. |
| `src/record.c` | Envelope validation and minimal schema metadata codec. |
| `src/datum.c` | Typed datum encoding, structural decoding, ordering and duplicate checks. |
| `src/text.c`, `src/uri.c` | Unicode and URI dependency boundaries; errors translated to core classes. |
| `src/object_id.c` | Hash-domain construction, digest byte conversion, id parsing/formatting. |
| `src/repo.c`, `src/repo_internal.h` | LMDB lifecycle, transactions, schema checks, key construction, persistence and reference resolution. |
| `tests/c/core_driver.c` | Non-installed command driver for Hypothesis tests against the real static core. |
| `tests/c/test_record.c` | Unaligned buffers, arithmetic edges, deterministic format corpus, allocation failures. |
| `tests/c/test_repo.c` | Transaction lifecycle, error cleanup, injected failures, snapshot/atomicity checks. |
| `tests/python/test_records_hypothesis.py` | Independent byte oracle and generated valid/invalid record properties. |
| `tests/python/test_repository_hypothesis.py` | Real filesystem persistence, rollback, duplicate and reference properties. |
| `tests/fixtures/records/` | Small reviewed golden vectors with provenance and readable expected fields. |
| `docs/core-storage.md` | Overview, usage example, C API ownership/lifecycle and operational errors; links to the wire spec. |

Add private headers only where another translation unit needs them. Follow the
existing `dml_` function prefix and snake_case API style, two-space C indentation,
K&R braces, explicit ownership, and small functions. Keep LMDB and normalization
library types out of installed headers.

### 5.1 API contract sketch

These names and signatures are an informative design sketch. Settle the exact
types before writing multiple callers.

```c
typedef struct dml_repo dml_repo;
typedef struct dml_txn dml_txn;

typedef struct {
  uint8_t bytes[16];
} dml_object_id;

typedef struct {
  uint8_t *data;
  size_t len;
} dml_buffer;

dml_status dml_datum_encode(const dml_datum_input *input,
                            dml_buffer *out, dml_error *error);
dml_status dml_record_validate(const uint8_t *data, size_t len,
                               dml_error *error);
dml_status dml_datum_decode(const uint8_t *data, size_t len,
                            dml_datum_view *out, dml_error *error);
dml_status dml_datum_id(const uint8_t *data, size_t len,
                        dml_object_id *out, dml_error *error);
dml_status dml_uri_canonicalize(const uint8_t *data, size_t len,
                                dml_buffer *out, dml_error *error);
void dml_buffer_free(dml_buffer *buffer);

dml_status dml_repo_open(const char *path, const dml_repo_options *options,
                         dml_repo **out, dml_error *error);
dml_status dml_repo_schema(dml_repo *repo, uint32_t *out, dml_error *error);
dml_status dml_txn_begin(dml_repo *repo, dml_txn_mode mode,
                         dml_txn **out, dml_error *error);
dml_status dml_txn_put_datum(dml_txn *txn, const uint8_t *data, size_t len,
                             dml_object_id *out, dml_error *error);
dml_status dml_txn_get_datum(dml_txn *txn, const dml_object_id *id,
                             dml_buffer *out, dml_error *error);
dml_status dml_txn_commit(dml_txn **txn, dml_error *error);
void dml_txn_abort(dml_txn **txn);
dml_status dml_repo_close(dml_repo **repo, dml_error *error);
```

Additional contracts:

- `dml_datum_input` is a tagged union with explicit lengths for byte/text spans,
  counts for id arrays, and key/value id pairs for maps. Constructors operate on
  typed values, not a loosely typed JSON representation.
- `dml_datum_view` borrows validated input bytes. It exposes lengths/kinds and
  safe accessors for composite members; it does not reinterpret an unaligned
  payload as a native integer or packed struct array.
- `dml_buffer` owns core-allocated memory. Output buffers/handles start empty;
  failures leave them empty. Free resets a buffer and is safe on an empty one.
- URI normalization returns length-delimited canonical URI bytes in such a
  buffer; a terminating C NUL is not part of the value. The datum encoder then
  applies its canonical-input-only contract to those bytes.
- Stored bytes are copied into an owned output buffer before the transaction
  ends. No pointer into an LMDB mapping escapes through the public API.
- All public functions validate pointer/length/count combinations. Zero-length
  inputs do not require dereferencing a null pointer. Specify valid output
  initialization and reuse in header comments.
- `dml_txn_commit` consumes and nulls its transaction handle on both success and
  failure. `dml_txn_abort` is safe for a null handle and consumes a live handle.
  Read transactions end with abort/close; attempting to commit one has an
  explicit, tested error contract.
- A failed mutating operation poisons its write transaction. Subsequent writes
  fail; attempting commit aborts the entire batch and consumes the handle.
  Expected lookup failures such as not-found do not poison a write transaction;
  fatal native transaction errors require abort.
- Repository close reports a busy/invalid-state error if transactions are still
  active, rather than freeing storage underneath them.
- Keep error construction allocation-free, including out-of-memory paths. A
  caller-owned error stores a stable high-level code, detail, and optional native
  error number. Avoid a mutable global last-error value.

### 5.2 Validation and error boundaries

Keep three checks distinguishable:

1. **Structural validation:** byte lengths, canonical representation, supported
   kinds, text rules. It is pure and does not open a repository.
2. **Identity validation:** compute the hash of canonical bytes and, when reading
   storage, compare it with the requested/key id.
3. **Reference validation:** resolve immediate composite children in the current
   transaction and verify datum type and stored-record integrity.

Use the validation classes from object-model Section 10: `invalid_header`,
`invalid_bounds`, `invalid_kind`, `invalid_payload`, and `invalid_utf8`. Preserve
Section 10.2's detail-to-class mapping for composite payload errors.

Propose separate operational statuses for invalid API arguments/state,
not-found, unsupported repository schema, allocation failure, map-full, and
storage/I/O failure. Document their names in the C API; they are additions to,
not replacements for, packed-record validation classes. Include native LMDB/OS
error information without exposing dependency types in the API.

Determine validation precedence with small fixtures: envelope before body,
bounds before content, canonical bytes before references. Well-formed tombstones
read from an object key get the exact Section 9.2 result:
`invalid_payload` with `record_type=tombstone;detail=excised`. Recognize this
before ordinary content-id verification, because excision retains the old key.

The generic record validator initially accepts META and DATUM only. Reject
unsupported record kinds explicitly. Recognizing a tombstone read failure does
not mean its schema or any other record schema is implemented for writing.

## 6. Codec implementation details

### 6.1 Envelope and integer access

After the Phase 0 packing decision, the expected fixed layout is:

| Record portion | Byte offsets / size |
| --- | --- |
| Header | magic at 0, version at 4, type at 6, total length at 8, flags at 12, checksum at 16; 20 bytes total |
| Datum prefix | kind at 20, payload length at 24, payload offset at 32; 40 bytes including header |
| Metadata | schema version at 20; 24 bytes including header |

This compact table is for implementing this milestone; maintain authoritative
layout definitions in object-model Sections 4 and 7.

- Read/write individual fields with byte operations or `memcpy` plus explicit
  endian conversion. Never hash or persist `sizeof(native_struct)` bytes.
- Validate the actual `size_t` input length before reading any header field.
  Reject records larger than the `u32` envelope limit before narrowing a value.
- Use subtraction-based bounds checks: first `offset <= total`, then
  `length <= total - offset`. Check multiplication and addition before allocating
  or evaluating `count * element_size`.
- Check canonical placement as well as bounds. For a datum, payload follows the
  fixed prefix directly, with no gaps, overlap, padding, or trailing bytes.
- Unknown versions/types, nonzero reserved fields, bad magic, and mismatched
  declared/actual lengths produce deterministic failures.
- Confirm host byte width and binary64 support at build time. Convert floating
  bits with `memcpy`; avoid undefined signed shifts, alignment assumptions, or
  signed overflow when encoding negative integers.

### 6.2 Datum values

- Encode NULL/BOOL/I64/F64 according to the accepted scalar layouts. The decoder
  rejects alternative BOOL values, negative-zero bits, and noncanonical NaNs.
- BYTES preserves every byte, including NUL. STRING validates UTF-8 and
  normalizes with length-aware NFC handling at construction time.
- URI handling uses the accepted profile; canonical storage validation compares
  with canonical output rather than silently rewriting bytes while reading.
- LIST preserves id order and duplicates. SET sorts a copy by id bytes and
  rejects duplicate ids. MAP sorts a copy by key-id bytes and rejects duplicate
  keys regardless of value. Do not mutate caller arrays.
- Encoders canonicalize typed inputs. Decoders reject unsorted/duplicate encoded
  SET/MAP inputs rather than repairing their identity.
- Empty composites include the little-endian count field; they are distinct
  from NULL and empty BYTES. Bound counts by `u32` and the record-size limit.
- Codec operations only handle ids for composite children. Missing-child and
  wrong-type errors belong to the repository-aware validation layer.

### 6.3 Object ids

- Validate canonical DATUM input before exposing its id through the public API.
- Construct the hash domain from the complete record with byte ranges `[0, 4)`,
  `[8, 12)`, and `[16, 20)` zeroed, following object-model Section 6.
- Preserve the version/type fields and the remainder of the payload. Do not
  modify the caller's buffer in place. A local masked header plus streaming hash
  is suitable; a checked temporary copy is also acceptable initially.
- Use the pinned library's canonical digest conversion after the Phase 0 byte
  order decision. Do not serialize the native `XXH128_hash_t` representation.
  Its implementation can be inspected in the pinned `xxhash.h` at
  `XXH128_canonicalFromHash`.
- Provide exact-length, checked id parse/format helpers. Storage keys always use
  32 lowercase hex characters; define whether external parsing accepts uppercase
  separately. The simplest initial parser accepts canonical lowercase only.
- Test masking through a private hash-domain helper. Public stored-record APIs
  still reject an invalid magic/length/checksum; masking is not a validation
  bypass.

## 7. Repository implementation details

### 7.1 Initialization and lifetime

1. Validate API options and establish whether the path is a repository that can
   be opened or a location eligible for initialization.
2. Create/open the LMDB environment and main database with checked return values.
   Apply map-size configuration according to the accepted open/reopen policy.
3. Validate existing `meta/schema`, or create its canonical META record inside
   the initialization transaction. Optional tool-version metadata is UTF-8 text,
   not a packed datum. Missing optional metadata is allowed.
4. Reject malformed/unsupported metadata without replacing it or performing an
   implicit migration. A concurrent initializer should recheck schema while
   holding the write transaction before creating metadata.
5. Publish the repository handle only after initialization/validation succeeds.
   On every failure, end any live transaction and release handles exactly once.

Use the pinned `lmdb.h` as the version-specific lifecycle reference. In
particular, commit consumes the native transaction handle even on failure, and
mapped values are transaction-scoped. Model these facts in failure tests.

### 7.2 Put datum

Within an active write transaction:

1. Check transaction state and structurally validate canonical DATUM bytes.
2. Resolve immediate LIST/SET/MAP references from `objects/datums/<id>` using the
   same transaction. Children inserted earlier in this batch are visible.
3. Check each resolved child's envelope/type/canonical bytes and id integrity.
   Report missing or non-datum child resolution as `invalid_kind` with
   `record_type=datum;detail=composite_ref_not_datum`, following Section 10.2.
   Preserve more specific corruption/excision failures for malformed children.
4. Compute the new id and form its exact type-prefixed, lowercase-hex key. Pass
   key length without a C terminator; do not store naked binary ids as keys.
5. Insert without overwrite. If the key already exists, validate the stored
   value and compare exact canonical bytes. Equal bytes mean idempotent success;
   different bytes mean an integrity/collision error and no overwrite.
6. An existing tombstone yields the excision error. Never resurrect it through
   ordinary put.
7. Return the id, but do not commit implicitly. Poison the transaction on a
   failed mutating operation so callers cannot accidentally commit an earlier
   partial batch.

Post-order insertion is the initial contract: children precede their composite
parents. Supporting forward references or incomplete imported object graphs
would require a separate validation/transaction design.

### 7.3 Get datum

Within an active read or write transaction:

1. Look up the exact datum key; an absent direct lookup is an operational
   not-found result.
2. Validate the envelope, recognize tombstone failure, require DATUM, validate
   canonical bytes, and compare recomputed id with the requested id.
3. Validate immediate composite references in the same snapshot, as on put.
4. Copy the record into an owned output buffer and return it. An error leaves the
   output empty; ending the transaction never invalidates a successful buffer.

This API returns packed bytes/a datum view, not a recursively materialized
Python collection. Immediate reference checking is not a claim of whole-graph
validation. Future recursive materialization needs its own visited-set and
resource-limit strategy and validates every traversed record.

Factor a private lookup that validates a child's own bytes/type/id without
following its children. Use that for immediate reference checking; recursively
calling the public get operation would accidentally add unbounded traversal of
corrupted or deeply nested data.

### 7.4 Atomicity and resource handling

- A batch of children and parents becomes visible together at commit. Abort or
  poisoned-transaction commit leaves every newly inserted batch object absent.
- Readers observe a consistent LMDB snapshot. A newly begun reader sees a
  completed writer's records; an already active reader keeps its old snapshot.
- Count active transactions per repository to prevent premature close. End
  transactions before releasing environment resources.
- Keep default thread/TLS behavior explicit. Use separate threads/processes for
  overlapping snapshot tests if the selected LMDB mode requires it; do not make
  an illegal same-thread test pass by weakening the production contract.
- Report map-full and I/O errors without automatic partial retries. A caller may
  reopen with a larger configured map size and retry the whole transaction.
- Support deterministic failure injection through small private, per-instance
  allocation/storage-call seams where real failures cannot be induced reliably.
  Production uses fixed real implementations. Avoid global fault counters,
  public test knobs, and a broad mock backend architecture.

## 8. Test strategy

### 8.1 Real-core bridge for Python properties

Build `test_core_driver` from `tests/c/core_driver.c` against the same `dml_dep`
used by the native CLI and C tests. It is test-only and is not installed. This
allows Python/Hypothesis to exercise the actual coverage-instrumented library
without first solving the separate wheel/static-linkage milestone.

Keep its command protocol small and documented in the test source:

- `encode <kind>`: accept a length-delimited typed value or id-array payload on
  stdin, call the typed encoder, return packed bytes on stdout.
- `validate`, `decode`, `id`: accept packed bytes; return deterministic status,
  decoded fields, or canonical hex id. Preserve error code/detail on stderr.
- `normalize-uri`: accept raw URI bytes and return the core helper's canonical
  bytes, so profile and idempotence tests exercise production normalization.
- `repo-init <path>`, `repo-put-batch <path> commit|abort`, and
  `repo-get <path> <id>`: exercise real repository APIs. Frame batch records with
  explicit lengths; do not encode arbitrary binary data as command arguments.

Use a different process for reopen assertions. Snapshot interleaving, injected
failures, and commit-consumption checks belong in focused C tests rather than a
large stateful driver protocol. The driver contains transport/adaptation only;
it does not implement production normalization, sorting, hashing, or persistence.

Locate the driver next to `DML_BIN`, including the `.exe` suffix used by Windows
CI, with a documented repository-root fallback for direct pytest runs. Fail
clearly if it is missing; never silently skip the new integration tests or use
the mocked Python extension.

### 8.2 Independent expected results

- Implement a small test-side byte encoder using Python `struct` and explicit
  constants from the accepted spec. Use Python's Unicode facilities as an
  independent NFC oracle, accounting for the pinned Unicode version.
- Store fixed record bytes, masked hash-input bytes, and expected ids in golden
  fixtures. Derive/check hashes with the pinned upstream xxHash implementation
  outside the production DML hash wrapper; record tool/version and generation
  procedure. Do not populate expected ids by calling the code under test.
- Include every datum kind and edge cases such as negative I64, infinity,
  canonical NaN, empty composites, non-ASCII NFC, and escaped URI delimiters.
- Share semantic fixtures with low-level C regression tests where practical.
  Round trips supplement exact byte checks; they cannot be the sole oracle.
- Keep generated values and collection sizes small for normal Hypothesis runs.
  Use targeted malformed records for huge claimed sizes instead of allocating
  gigabytes. Save minimized regressions for discovered failures.

### 8.3 Required test matrix

| Area | Assertions |
| --- | --- |
| Primitive encoding | Exact scalar widths/bytes; I64 minimum/maximum; both BOOL values; invalid BOOL bytes; empty and NUL-containing byte strings. |
| Floats | Multiple NaN signs/payloads encode identically; negative/positive zero encode identically; noncanonical stored forms fail; finite values and infinities round-trip. |
| Header | Truncation at each field boundary, bad magic, unsupported version/type, bad flags/checksum, length below minimum, excess/trailing data. |
| Bounds | Offset into header, out-of-range offset, overflow-shaped offset/length, gaps, payload-length mismatch, count overflow and count/body mismatch. |
| UTF-8/NFC | Invalid continuations, truncation, overlong forms, surrogate encodings and out-of-range code points; composed/decomposed equivalents; embedded NUL; combining sequences. |
| URI | Accepted profile vectors, normalization idempotence, canonical-input rejection, malformed escapes/authority, preserved reserved escapes and query ordering, mixed-case reserved `dml` scheme. |
| LIST | Order sensitivity, duplicate preservation, empty list, exact count encoding. |
| SET | Permutation-invariant encoding/id, duplicate rejection, strict byte ordering on stored input. |
| MAP | Permutation-invariant encoding/id, duplicate keys with equal or unequal values rejected, different keys with shared values accepted. |
| Hash/id | Reviewed golden ids; precise masked domain; input buffer unchanged; fixed digest byte order; strict hex length/characters; list/set kind separation. |
| Initialization | Missing path with create false; create/reopen; empty path policy; unrelated nonempty directory; malformed/missing/unsupported schema; optional metadata absent. |
| Persistence | Scalar/composite batch survives process exit; retrieved bytes equal input; duplicate insertion is idempotent; readonly transactions reject writes. |
| References | Same-transaction child visibility; missing child; wrong-type record under datum key; malformed/hash-mismatched child; list and both map positions checked. |
| Integrity | Invalid bytes cannot be inserted; raw test corruption is detected on get; different existing bytes are not overwritten; tombstone reads/puts report excision. |
| Transactions | Abort after successful puts; failure after earlier writes poisons batch; commit failure consumes handle; snapshot visibility; close with live transaction; repeated null abort/free. |
| Resource failures | Allocation failure at owned allocations; map exhaustion; environment/begin/put/commit failure cleanup; successful retry in a fresh transaction where applicable. |
| Platform | The same golden bytes/ids on every existing CI platform; unaligned input in C tests; paths with spaces and platform-specific executable suffix. |

Use real LMDB for successful integration scenarios. For corruption/tombstone
fixtures, use low-level test code that writes raw LMDB values; do not add a
public unsafe-write API. Simulated commit failures need to model that the native
handle has been consumed, so cleanup tests can catch double-abort/double-free.

Property-test candidates include `decode(encode(value))`, encode idempotence for
canonical values, set/map permutation invariance, list-order sensitivity, NFC
equivalence, and abort leaving the repository's visible datum set unchanged.
Malformed-byte fuzzing checks bounded, deterministic failure without crashes;
targeted single-defect fixtures establish exact error classes.

## 9. Implementation sequence and checkpoints

Complete each checkpoint with its focused tests before layering on the next.
These are logical review units, not instructions to create commits automatically.

### P0. Establish the contract and baseline

- Read current agent instructions, this plan, and the linked source documents.
- Inspect `git status` and preserve unrelated changes.
- Obtain implementation authorization, then run the existing standard validation
  once and record any pre-existing/tooling failure separately.
- Resolve Section 4 decisions and update the authoritative spec before code.
- Select/pin normalization dependencies and record their platform verification.
- Finalize the minimal C types, error taxonomy, ownership, and test-driver
  protocol. Add initial golden fixtures from the accepted format.

Exit: no implicit identity-defining decisions; baseline status recorded.

### P1. Add safe byte primitives, errors, and envelope validation

- Add public support types and private endian/checked-arithmetic helpers.
- Implement envelope and metadata validation/encoding.
- Extend root Meson source/header/test lists; introduce the smallest driver
  commands needed for record tests.
- Add malformed-header/bounds, unaligned-input, and resource-failure tests.

Exit: deterministic errors and exact metadata/header bytes on the build matrix.

### P2. Implement canonical datums and ids

- Implement scalar encoders/decoders, text/URI boundaries, composite ordering,
  and datum structural validation.
- Implement masked hashing and id conversion with reviewed golden fixtures.
- Add Hypothesis coverage across all ten kinds and targeted invalid payloads.
- Keep codec tests independent of repository state.

Exit: every datum kind has exact-byte, valid-input, and rejection coverage; ids
are stable across platforms and independent processes.

### P3. Add repository lifecycle and transaction primitives

- Implement open/create/schema/close and read/write transaction ownership.
- Test schema compatibility, path policy, initialization rollback and retry,
  readonly behavior, map limits, and handle cleanup.
- Add focused failure-injection seams only as needed for these tests.

Exit: initialized repositories reopen correctly; failures leave no live native
handles and never replace existing incompatible metadata.

### P4. Add immutable datum persistence and references

- Implement exact datum key construction, put/get, idempotency and integrity
  checks, tombstone rejection, and direct-child resolution.
- Implement poisoned write transactions and whole-batch rollback semantics.
- Add property-based roundtrip/abort tests and deterministic snapshot tests.

Exit: the Section 3 storage demonstration passes against real LMDB, including
fresh-process reopen and atomic failure paths.

### P5. Finish documentation and verification

- Write `docs/core-storage.md` with a short module overview, lifecycle/ownership
  contract, and compilable C example using the finalized API. Link to the object
  model rather than copying its schemas.
- Add a discoverability link from the README when the implementation exists.
  Update architecture status to describe actual implemented layers if warranted.
- Update `AGENTS.md` only for actual new tooling/conventions, preserving its
  existing worktree changes. Update command documentation if the check workflow
  or environment changes.
- Run the required checks in Section 10, inspect coverage gaps, and validate
  mutation effectiveness against new code rather than version-only scaffolds.
- Review the diff and report implemented behavior, test evidence, and any
  explicit unresolved issue. Do not describe later DAG/Python work as delivered.

Exit: all acceptance criteria in Section 11 are satisfied or clearly reported
as incomplete with evidence.

## 10. Verification workflow

Run commands from the repository root after implementation authorization. These
commands reflect the current repository workflow, not a newly installed toolchain.
Check tool availability first; `scripts/init.sh` is not evidence that tools are
installed and currently prints rather than executes its installation commands.

Required tooling: Meson, Ninja, a C compiler, Python plus
`requirements-dev.txt`, gcov/lcov/genhtml, Valgrind for memory checks, and a
compatible Mull/compiler setup for mutation testing.

During development, use the configured build for targeted tests:

```sh
meson compile -C build/check
meson test -C build/check --print-errorlogs
python3 -m pytest -q tests/python/test_records_hypothesis.py tests/python/test_repository_hypothesis.py
```

Run the standard end-to-end gate once the implementation is ready:

```sh
scripts/check.sh
```

Because this milestone touches allocation, mapped data, and transaction
lifetimes, run the memory-check variant as well:

```sh
scripts/check.sh -v
```

The `-v` option wraps Meson C tests only; it does not put pytest's driver
subprocesses under Valgrind. Ensure the C tests cover the critical allocation and
transaction lifetimes, or run specific saved driver cases under Valgrind too.

Mutation validation needs explicit new binaries, for example after those targets
exist:

```sh
MULL_TARGETS="build/check/test_record build/check/test_repo" scripts/check.sh -m
```

Verify that the compiler/instrumentation setup actually generates and executes
mutants in new `src/` code. A command that finds zero relevant mutants is not
mutation evidence. The current check script invokes the runner but does not
establish all compiler/plugin prerequisites or enforce a mutation-score threshold.
Record total/killed/surviving mutants, inspect survivors, and add meaningful
regressions for missed invariants. Explain equivalent mutants individually.

Additional verification notes:

- The root Meson build should build all new test targets by default so both
  `scripts/check.sh` and existing cross-platform CI discover them.
- Python-driven native execution needs to use the same instrumented library
  build whose counters lcov captures. Do not test a stale separately built wheel.
- The default local check enforces 100% C line/function/branch and Python line
  coverage. CI uses the report-only mode described in `README.md` (Build and
  Test). Inspect error branches and write meaningful failure tests instead of
  adding blanket exclusions. Discuss any necessary exclusion under the
  repository policy.
- Existing lcov exclusions remove dependencies, tests, and `build/check` paths.
  Confirm new production sources appear in the filtered report and none are
  accidentally excluded by source placement.
- Keep deterministic C corpus checks so Mull's no-argument test targets exercise
  substantive record/storage paths; the driver alone is not such a target.
- Run existing cross-platform CI jobs with the new code/dependencies. If a
  platform or tool cannot be exercised, report it as unverified rather than
  claiming a pass. Current architecture coverage is little-endian; golden bytes
  and explicit endian access do not substitute for an actual big-endian run.
- Coverage reports are under `build/coverage/html` and
  `build/coverage/python-html`; Meson logs are under `build/check/meson-logs`.
- Avoid redundant full runs after checks pass unless a change or unresolved
  concern warrants them. Do not use `-f` solely as a routine cleanup step.

## 11. Definition of done

- [x] Phase 0 format choices are accepted and documented in the authoritative
  spec, including scalar layouts, NaN bits, digest order, and URI profile.
- [ ] All ten datum kinds encode canonically, decode safely, and have independent
  golden vectors plus valid/invalid property coverage.
- [x] META initialization and version compatibility have explicit tested rules.
- [x] Repository put/get uses exact spec keys and preserves immutable bytes.
- [ ] Duplicate puts are idempotent; corruption/collision and tombstone cases
  fail without overwriting existing values.
- [ ] Composite children resolve with datum type and integrity checks in the
  same transaction; children inserted earlier in the batch are accepted.
- [x] Committed records survive fresh-process reopen with identical bytes/ids;
  abort and poisoned transactions expose no partial batch.
- [ ] Snapshot behavior and handle ownership are tested, including failures and
  allocation/map exhaustion. No mapping pointer escapes its transaction.
- [x] The existing version/CLI/package scaffold tests continue to pass.
- [ ] The standard check and memory checks pass; coverage is measured over new
  production sources; mutation results exercise the new implementation.
- [ ] Existing CI platform results are recorded, including normalization-library
  integration, or outstanding verification is explicitly identified.
- [x] Public API documentation includes an example and ownership/error contracts;
  new declarations are installed by Meson and no dependency types leak out.
- [ ] The final diff is scoped to the milestone and preserves pre-existing user
  changes. Implementation status and any deviations are accurately summarized.

## 12. Next-agent quick start

1. Read applicable agent instructions, then this plan and object-model Sections
   4-10. Verify baseline drift with Git before trusting the file map.
2. Confirm implementation approval; the approval attached to this document was
   for planning only.
3. Start at P0. The first coding task is safe byte primitives and envelope
   validation after the byte-level decisions are recorded, not a CLI command or
   a new Python facade.
4. Work through P1-P5 with tests alongside each layer and preserve the distinction
   between pure byte checks, identity checks, and repository reference checks.
5. Finish with evidence against Section 11 and hand off the subsequent
   node/DAG/tree/commit/ref and Python-linkage milestone separately.
