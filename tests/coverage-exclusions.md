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
`LCOV_EXCL_BR_LINE` for an unmeasured branch group. No functions are excluded.
The latter is **line-wide**: when a condition or switch has an impossible edge,
lcov also removes its already-tested reachable edges from the percentage's
denominator. The assertions for reachable behavior remain. This tooling
limitation must not be described as every original branch having been exercised.
Re-evaluate each exclusion if its stated invariant or supported platform changes.

Locations below are stable function/statement identifiers; the inline markers
pin the precise lines in the current source.

| Source and marked statement/region | Why further execution provides no useful assurance | Retained assurance |
| --- | --- | --- |
| `src/object.c`, `dml_object_decode()` type-range condition | Successful record validation admits only META through COMMIT. The upper-range rejection edge cannot occur. | Datum rejection, accepted object views and malformed records are tested. |
| `src/object.c`, tree per-entry total-size guard and its error return | On 64-bit hosts, each prior iteration bounds `len` to u32 and the next increment to at most 148, so `size_t` addition cannot overflow. Reaching the u32 total-size rejection requires a multi-GiB tree and tens of millions of repeated entries; that repeats independently tested checked addition and the common u32 record-size contract, rather than exercising different ownership or storage behavior. | Public oversized-count rejection, checked arithmetic, name bounds, codec counts, canonical ordering and both tree allocation failures are tested. No large-tree performance claim is made. |
| `src/object.c`, tree sorted-array multiplication guard and its error return | A u32-bounded entry count times the entry structure size cannot overflow 64-bit `size_t`. Synthetic helper lies would only violate this invariant. | Multiplication overflow is tested directly; allocation failure and cleanup are tested at both tree allocations. |
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
