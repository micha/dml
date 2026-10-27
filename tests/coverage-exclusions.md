# Coverage scope and no-value exclusions

## Authority boundary

This document owns the rationale for the specific coverage exclusions used by
[scripts/check.sh](../scripts/check.sh). The user-approved policy is in
[AGENTS.md — Testing](../AGENTS.md#testing). Technical behavior remains owned by
[the as-built specification](../docs/spec-next/README.md).

Coverage is a means of improving assurance, not an end. Add meaningful tests for
boundary/error handling, allocation failure and rollback. Difficulty alone does
not justify excluding a path. The default gate still requires 100% of the
**retained** line/function/branch population; exclusions are not passing tests.

## Meaningful failure tests

- [test_boundaries.c](c/test_boundaries.c) tests checked arithmetic, malformed
  records, counts and lengths, noncanonical text/URIs, unsupported types and
  invalid API arguments without constructing invalid memory spans for reads.
- [test_faults.c](c/test_faults.c) tests allocation failure throughout the codecs,
  identity and repository lifecycle; dependency errors during URI processing and
  LMDB operations; failed reads leaving empty buffers; poisoned-transaction
  rollback; malformed/missing schema; permissions and unrelated directories;
  composite-datum references; and simulated hash-collision rejection.
- The private fault core compiles the same source files with
  [fault_injection.h](c/fault_injection.h) force-included. Its one-shot substitutions
  return allocation failures or dependency error codes. The commit substitution
  consumes the native LMDB handle on failure, as the real API does. Hash-collision
  fixtures use a constant test hash; they are not discovered XXH3 collisions.
- The installed library has no fault hooks or mutable test state. These tests
  still use real codecs and LMDB transactions except for the selected dependency
  call. Scratch is newly created, process-specific and cleaned only when owned.
  The permission tests run on non-root Unix users; they are not Windows permission
  guarantees. The arithmetic boundaries and allocation-size rationale below are
  for the currently supported 64-bit test matrix.

## Exact exclusions

Source comments carry `LCOV_EXCL_LINE` for an unmeasured line and
`LCOV_EXCL_BR_LINE` for an unmeasured branch group. No DML production functions
are excluded; the CPython dependency-header exclusion below removes only dependency
functions. The latter is **line-wide**: when a condition or switch has an impossible edge,
lcov also removes its already-tested reachable edges from the percentage's
denominator. The assertions for reachable behavior remain. This tooling
limitation must not be described as every original branch having been exercised.
Re-evaluate each exclusion if its stated invariant or supported platform changes.

Locations below are stable function/statement identifiers; the inline markers
pin the precise lines in the current source.

| Source and marked statement/region | Why further execution provides no useful assurance | Retained assurance |
| --- | --- | --- |
| `src/object.c`, `dml_object_decode()` type-range condition | Successful record validation admits only META through COMMIT. The upper-range rejection edge cannot occur. | Datum rejection, accepted object views and malformed records are tested. |
| `src/object.c`, shared DAG/tree per-entry total-size guard and its error return | On 64-bit hosts, each prior iteration bounds `len` to u32 and the next increment to at most 148, so `size_t` addition cannot overflow. Reaching the u32 total-size rejection requires a multi-GiB named object and tens of millions of repeated entries; that repeats independently tested checked addition and the common u32 record-size contract, rather than exercising different ownership or storage behavior. | Public oversized-count rejection, checked arithmetic, name bounds, codec counts, canonical ordering and both DAG/tree allocation failures are tested. No large-tree performance claim is made. |
| `src/object.c`, shared DAG/tree sorted-array multiplication guard and its error return | A u32-bounded entry count times the entry structure size cannot overflow 64-bit `size_t`. Synthetic helper lies would only violate this invariant. | Multiplication overflow is tested directly; allocation failure and cleanup are tested at both named-object allocations. |
| `src/object.c`, encoder's second type switch and its default | The first switch has accepted exactly NODE/DAG/TREE/COMMIT; this second switch covers all four. Its fallback is unreachable with unchanged caller-owned input. | All four encoding bodies, identity, malformed types and both switch-entry argument guards are tested. |
| `src/object_id.c`, immutable type-range condition | Successful record validation permits only META..COMMIT. A type above COMMIT cannot reach this condition. | META rejection, datum-only identity restrictions, all immutable types, bad encoding and hash allocation failure are tested. |
| `src/record.c`, both encoder kind switches | The earlier range guard admits exactly the ten cases covered by both switches; the compiler's implicit defaults cannot occur. | All ten kinds, independent encoding oracles, malformed kinds and failed encoding allocations remain tested. |
| `src/record.c`, the LIST/SET and MAP `dml_size_add(payload_len, 4, ...)` conditions | After successful multiplication by 16 or 32, the largest possible product leaves at least 15 or 31 bytes below SIZE_MAX. Adding 4 cannot overflow. These expressions have been placed on separate lines from the meaningful multiply/count guards. | Multiply overflow, oversized counts and total-record overflow/bounds are tested without exclusions on those guards. |
| `src/repo.c`, creation's `mkdir`/EEXIST condition | EEXIST after stat reported absence requires an external creator in that gap. A fabricated timing race would not prove filesystem-directory atomicity or add repository-transaction assurance. | Normal creation, missing-parent failure, unrelated paths and initialization failure cleanup are tested. The spec explicitly does not promise atomic filesystem initialization. |
| `src/repo.c`, direct-object-reference decoder status guard | Private callers already checked the same unchanged bytes' encoding, expected type and content ID. The supported object decoder performs no allocations, so it cannot newly fail there. | Independent decoder rejection and actual direct-reference failures, corruption and allocation errors remain tested. Composite datum decoding can allocate and is not excluded. |
| `src/uri.c`, `hex_value()` branch groups and final non-hex return | This static helper is called only after the original URI grammar parser accepted each percent escape. Only the three supported hexadecimal ranges can reach it. Some lower/upper short-circuit edges and the non-hex return are therefore impossible. | Digits, uppercase/lowercase hexadecimal conversions and percent normalization are exercised; invalid original syntax is rejected in tests. |
| `src/uri.c`, `normalize_escapes()` malformed-escape condition and cleanup/error return | The original grammar has already rejected truncated or non-hex escapes. Violating that premise would require changing the input concurrently or a parser defect, neither of which a fabricated successful parse would validate. | Malformed original syntax, both parser stages' failures and cleanup, ordinary escape conversion and allocation failure are tested. |
| `src/uri.c`, missing-or-empty scheme condition | A parsed non-null RFC scheme is nonempty. Only the empty-but-non-null edge is impossible. | Missing, reserved, mixed-case and valid schemes remain tested. |
| `src/uri.c`, `chars_required < 0` condition | Successful string-size calculation supplies a nonnegative character count. An invented success with a negative count would violate the dependency's output contract. | Normal size/serialization and dependency-error cleanup at both calls are tested. |
| `scripts/check.sh`, removal pattern `*/lib/gcc/*/include/emmintrin.h` | This exact compiler header contributes dependency-only SIMD inline implementations emitted through xxHash, not DML source behavior. Testing two unused intrinsic implementations would add no assurance about DML's hash domain or repository. | Datum golden IDs, immutable-object domains and identity changes are tested. Only this header is newly removed, not all Nix-store or system sources. |

The historical retained header entry had LF=10, LH=8 (two uncovered lines). Its
removal excludes all ten dependency-header lines, including eight previously hit
lines. See [delivery notes](../../dml-design/iterations/01-minimum-viable-repository/RESULTS.md#review-follow-up)
for actual marker-free and gated counts, excluded populations, commands and memory
check results. No excluded path is evidence of a passing test.

## Iteration 2 binding and CLI exclusions

The old exclusions above are unchanged. Added precise locations:

| Location | No-value rationale | Retained assurance |
| --- | --- | --- |
| `python/daggerml/src/_core_module.c`, `repo_schema()` status guard | The live-handle helper and non-null local output already establish this allocation-free native query's complete preconditions. It cannot newly fail. | Closed/wrong-thread/invalid native handles and successful schema reads are tested. |
| Same source, `txn_begin()`'s `Py_INCREF(owner)` and `decode_datum()`'s `Py_INCREF(Py_None)`/NULL case label | CPython generates immortal/refcount branches, not alternate DML ownership paths. A live capsule owner is mortal and None is immortal on this Python build. The NULL case label marker accounts for GCC attributing the inline branch to that label. | Owner retention, successful/failing capsule construction, explicit cleanup, queued foreign-thread cleanup and isolated unsupported abandonment tests remain measured. |
| `src/cli.c`, `traverse()` traversal-array size guard and error-return line | Overflow requires exabytes of already-allocated traversal state on the supported 64-bit matrix. Repeating giant graphs adds no distinct cleanup/storage assurance. | Real initial/reallocation failures, both traversal arrays, late failures, shared ancestors/DAGs, deep iterative nesting, exact limits and simulated-hash commit/DAG cycle fixtures are tested. |
| `src/cli.c`, positive limit parser's `*end` guard | Every input byte was already checked as a decimal digit, so successful `strtoumax` consumes the whole string. A fabricated partial parse would violate the dependency's contract. | Empty/non-digit/negative/zero/overflow limits and valid limits are tested. |
| `src/cli.c`, parser's `parsed > SIZE_MAX` guard | uintmax_t and size_t are both 64-bit on the supported matrix. This guard currently contributes no measured branch; retain it and re-evaluate on another width. | Decimal overflow is exercised through errno/ERANGE; no smaller target-width support is inferred. |
| `src/cli.c`, final `close_status` guard | The sole read transaction was just consumed by abort. The handle is live and idle, or null after open failure; repository close cannot newly fail. | All open/traversal/read failures clean up, and native close-with-active rejection remains tested independently. |
| `scripts/check.sh`, `*/include/python*/object.h` filter | CPython limited-API inline type/refcount helpers are dependency implementation, not DML behavior. | Binding buffers, handles, return values and reference-stealing/allocation errors have real tests and memory workloads. No DML source file is removed. |

In particular, datum decoding is **not excluded** as allocation-free: URI/text
validation can allocate again. URI allocation sweeps exercise decode failure
following an already-successful typed read. No binding/CLI allocation-failure,
rollback, parser, output-write or unsafe-finalization handler is excluded.

At the passing default checkpoint, marker-free versus retained measurements:

| Population | Lines | Functions | Branch outcomes |
| --- | --- | --- | --- |
| Marker-free, retaining GCC/CPython headers | 1584/1592 | 129/129 | 1483/1524 |
| Default gate | 1555/1555 | 125/125 | 1409/1409 |

All exclusions combined remove **37 lines** (29 had hits), **115 outcomes** (74
had hits), and **4 dependency functions** (all hit). No DML function is excluded.
Iteration 2 additions remove 21 lines (20 hit), 48 outcomes (28 hit), and those 4
functions; the prior population removes 16 lines/67 outcomes as previously
cataloged. New per-source removals are:

- CPython `object.h`: 20 lines, 32 outcomes, 4 functions (`Py_XDECREF`, `_Py_NewRef`,
  `PyType_HasFeature`, `Py_TYPE`); 20 lines/19 outcomes/4 functions had hits.
- Binding: 0 lines, 6 outcomes; 3 outcomes had hits.
- CLI: 1 line, 10 outcomes; 0 lines/6 outcomes had hits.

These are denominator removals, not claimed passing tests. Full commands,
intermediate failures and source state are in
[Iteration 2 results](../../dml-design/iterations/02-repository-usability/RESULTS.md).

## Iteration 3 exclusion reassessment

The shared DAG/tree size exclusions retain the same 64-bit invariant: validated
names add at most 148 bytes to a u32-bounded length; both base sizes (24/40) and
minimum-entry count guards bound the sorted array. DAG inputs use separately typed
public bindings; a private sorted tree-entry buffer copies each name/target rather
than alias-casting input arrays. Both allocation failures and cleanup are exercised
for DAGs as well as trees. The marked guards are not excluded entire functions.

The renamed typed `traverse()` retains the same astronomical-size growth guards
for both commit history and DAG/node traversal. Encoded counts are u32-bounded;
adding the DAG root cannot overflow size_t on the supported 64-bit matrix.
Actual allocation failures, shared/active cases, cycles and output failures remain
retained tests. The direct-reference decoder exclusion still applies: DAG-binding
and node-kind decoding are allocation-free after the same unchanged bytes were
validated. No new exclusion is needed merely for lookup/conversion/traversal.

Historical Iteration 2 population counts below remain that iteration's evidence,
not current counts. Iteration 3 measurements are in its
[results](../../dml-design/iterations/03-composable-dags/RESULTS.md).

## Iteration 4 Python execution population

`daggerml.local` and both local examples remain in the unchanged root-source Python
coverage gate. No new exclusion, source omission, threshold change or suppression
is introduced. Host-side calls exercise every local-layer statement, including
child context/publication helpers and meaningful malformed-role, spawn, shutdown,
IO, cleanup, collision and storage/conflict failures. The maintained child example
also runs directly under host coverage, including its type-rejection branches.

Real subprocess acceptance stages the maintained sources with the current linked
extension; it is not a second codec or production bootstrap. Staged and installed
subprocesses are **not coverage-instrumented** by the host coverage invocation.
Direct helper coverage must not be described as coverage of every actual installed
child invocation or every Python branch. Deterministic parent-loss barriers and
fault substitutions are private fixtures, not installed runtime controls.

Existing C tests and binding/CLI Valgrind workloads remain enabled. No native source
changes occur in this slice, and Mull does not supply mutation assurance for the
new Python layer. Real subprocess tests are functional/process-disposition evidence,
not new process-level Valgrind or sandbox assurance. Actual checks and bounded
negative-oracle probes belong to
[Iteration 4 results](../../dml-design/iterations/04-local-recorded-execution/RESULTS.md).

## Iteration 5 Python transfer population

The public packed insertion wrapper, explicit `daggerml.transfer` module and
transfer example remain in the unchanged Python source gate. No new exclusion,
source omission, suppression or threshold change. Host-side tests measure transfer
framing, traversal, full-bundle checks and owning transaction boundaries, including
real stored missing/corrupt keys, real small-map abort and private native write/
consuming-commit faults. Test-only `raw-delete` extends the existing driver fixture;
it is not shipped or an immutable deletion API.

Private process barriers surround the actual storage commit: termination after
three puts but before commit versus after successful commit before acknowledgement.
Fresh readers distinguish no batch from complete publication. These staged and
installed processes are not host-coverage-instrumented; direct helper/example
coverage is separate from real process-loss/installed functional evidence.

The existing binding Valgrind workload additionally reinserts exact records for
all datum kinds, literal/sub-DAG nodes, rooted/named DAGs, trees and commits, and
sweeps packed insertion allocation failures. Native production code is unchanged;
existing exact exclusions still apply. These bounded workloads do not supply a
new process-memory, hostile-input or Python mutation-framework guarantee. Actual
retained populations, memory results, negative-oracle probes and platform/runtime
limits belong to [Iteration 5 results](../../dml-design/iterations/05-pinned-snapshot-transfer/RESULTS.md).

## Iteration 6 Python exchange population

The explicit `daggerml.exchange` layer and repository execution example stay in the
unchanged root-source Python coverage gate. No new exclusion, source omission,
threshold reduction or memory suppression. Host-side tests measure bounded descriptor
IO, selected-role/history inspection and meaningful bootstrap, file, cleanup and
publication failures. Native production and existing local/transfer layers are unchanged.

Private barriers distinguish persisted unknown B before child spawn, done B after
actual child reaping, separate worker completion/reaping before caller pause and
actual A precommit/postcommit loss. Successful new actual-A puts are tracked before
real map-full and substituted consuming-commit failure; fresh readers check whole
logical rollback. Exact whole `data.mdb` equality additionally preserves raw different/
malformed-ref bytes. Generated history/repeat-receive properties and a genuine recorded
failure relabelled as success strengthen selection/classification oracles.

Staged/installed worker/child/receiver processes are not host-coverage-instrumented.
Safe private barriers/direct-worker disposition are not general process-tree cleanup,
power-loss or security assurance. Existing binding/native CLI memory workloads remain,
not new installed-process memory checks. Actual counts, installed/runtime provenance,
negative-oracle probes and limitations belong to
[Iteration 6 results](../../dml-design/iterations/06-local-repository-execution/RESULTS.md).

## Iteration 7 asynchronous exchange population

The additive exchange helpers, fixed installed worker module and maintained asynchronous
application/slow child remain measured in the unchanged source gate. No new exclusions,
source omissions, reduced inputs, weaker thresholds or memory suppressions. Host-helper
statement coverage is not every Python branch or installed worker/child invocation.

Private cooperative child barriers expose real P/U before exit; application owners retain/
reap workers. Worker-loss barriers are before computational spawn or after proven actual
child reaping. Coherent-read tests move both refs from a separate process mid-read, then
export the pinned immutable selection. Independent typed-byte oracles, prior history in C,
strict framing and typed-valid wrong histories protect progress association/unknown state.
Genuinely new actual-A successful puts/readback precede real map-full, different/malformed
refs and private substituted consuming-commit failures. Fresh readers compare all baseline/
new immutable records; whole-file equality preserves raw ref corruption. Actual pre/post-A
commit process barriers distinguish no batch from complete import despite response loss.

A scaled packed-total rejection is not production-limit stress. Separate actual >4 MiB
result recording lets the unchanged runner reap/record F, then execute/observe export fails
at the unchanged real per-record limit; no false done packet or retry occurs. Maintained
example gates are caller-owned normal captured-source inputs, not installed fault hooks.
Failed watchdog/barrier cleanup is not general process-tree/power-loss assurance. Existing
binding/141 native CLI memory workloads remain separate from installed process-memory and
Python mutation evidence. Commands, provenance, faults and remaining qualifications belong
to [Iteration 7 results](../../dml-design/iterations/07-asynchronous-local-execution/RESULTS.md).

## Memory-check accounting

`check.sh -v` now additionally exercises the actual binding under Valgrind through
[its standalone workload](python/binding_memory.py), and a native CLI allocation
sweep through [its workload](python/cli_memory.py). It uses `PYTHONMALLOC=malloc`
and `--trace-children=yes` to follow Nix's Python exec wrapper into CPython.
A wrapper-only run without exec tracing is not Python memory evidence.

[The suppression file](valgrind-cpython.supp) matches definite-leak reports with
specific CPython cached/interned Unicode call chains: unmarshalling, module/type
initialization, parser identifiers and import-name processing. It contains no
DML buffer/handle allocator or direct binding Unicode-return chain. Neither
invalid-access nor uninitialized-value errors are suppressed. Re-evaluate these
patterns for a new Python build; they are not a blanket CPython/source suppression.

`DML_MEMORY_BASELINE=1` runs the same import setup with no repository workload.
The runtime-only and full-workload checks had identical exit heap populations;
both reported zero unsuppressed memory errors/leaks. Exact suppressed and reachable
counts depend on the current source/runtime and are recorded per run in results.
This is not a claim that the Python process has no retained runtime allocations.

Unsupported foreign-thread last-owner abandonment deliberately leaves native
resources unreclaimed and is tested only in disposable subprocesses. It is **not**
part of leak-free supported-finalization evidence. The documented ResourceWarning
and warnings-as-errors/unraisable behavior are tested rather than excluded.
