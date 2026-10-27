# Iteration 1 delivery notes

Status: reviewed follow-up and URI correction published as `6ee9329`; its exact-SHA
GitHub CI run passed all six jobs. The passing local default gate remains separate
validation evidence. Design notes stay local and uncommitted. Initial delivery/CI
and local review measurements below remain historical; see the
[follow-up publication checkpoint](#follow-up-publication-checkpoint) for the
current source state, push result and Actions outcomes.

## Preflight

The user instructed implementation to begin. `/work` is mounted. Implementation
HEAD is `b428b0195e8f76ef902d13d0da4ac3da7e3d284e`, initially clean. Design HEAD is
`043c851f1eadac958d3596bf2c7c3e5a126ecf23`; existing changes to `AGENTS.md`,
`README.md`, `discussion.md` and untracked `iterations/` are preserved.
The initial instruction to begin did not authorize commits or pushes. The user
subsequently requested an implementation commit, GitHub push and Actions monitoring;
see the publication checkpoint below.

Inspected all handoff-required source/header/test files and documentation. Existing
ignored `build/check` contains build outputs, no `test-repository-data` directory.
The existing validation shell is `../dml-build-tools`; no tooling was installed.

Baseline command (implementation checkout):

```sh
nix develop ../dml-build-tools --no-write-lock-file -c bash scripts/check.sh
```

Exit 1: all 4 C executables and 22 Python tests pass; Python coverage is 100%
(31 statements). C coverage gate fails: 601/743 lines (80.9%), 53/54 functions
(98.1%), 407/640 branches (63.6%). The filtered report includes a Nix-store GCC
intrinsics header. Neither exclusions nor thresholds were changed. Baseline log:
`/tmp/dml-iteration1-baseline.log` (session-local diagnostic, not durable evidence).

## Implementation sketch — assistant-selected representation

These choices were written before coding and adopted by the implementation. They
are assistant implementation choices within the authorized turn, not prior design
agreements. Actual contracts are in the
[as-built specification](../../../dml/docs/spec-next/README.md).

- Reuse the 20-byte envelope and existing hash domain. Node: u32 literal kind 1,
  datum ID. DAG: root node ID. Tree: u32 entry count, then u32 name byte length,
  name bytes, DAG ID per entry. Commit: tree ID, u32 parent count, parent IDs.
- Counts/lengths are little-endian u32; records are at most UINT32_MAX bytes.
  No persisted C structs, offsets, execution fields or spare future dimensions.
- Names use an intentionally narrow profile: 1–128 ASCII bytes; first byte is
  alphanumeric, remaining bytes alphanumeric, underscore, hyphen or dot.
  Tree entries sort lexicographically by name bytes; duplicate names reject.
  Empty trees are supported. Names are data, never filesystem paths.
- Commit parents preserve supplied order; duplicates reject. Zero/multiple
  parents are supported without merge semantics.
- Small common object input/borrowed-view codec API for node/DAG/tree/commit,
  with type-discriminated fields and entry/parent accessors. A broader immutable
  ID API supports datum plus these four types; datum ID remains datum-only.
- New transactional put/get APIs take an explicit expected object type and
  reject mismatches. Existing datum API remains unchanged. Type-qualified keys
  use `objects/nodes/`, `objects/dags/`, `objects/trees/`, `objects/commits/`.
- Direct references check stored encoding, expected type and key/content identity,
  not recursive transitive validity. Objects must exist before their referencing
  objects, including earlier writes in the same storage transaction.
- Ref names use the same narrow profile, stored under `refs/heads/<name>` with a
  raw 16-byte commit ID. Explicit create and update, no implicit upsert. Duplicate
  create returns invalid_state; update/lookup of an absent ref returns not_found.
  Ref reads/writes check the target commit and its direct references.
- Get buffers are copied/owned; decoded views borrow input; output buffers must
  be empty. Failed writes poison the transaction. Existing thread-affinity and
  external-synchronization requirements remain unchanged.

## Delivered source state

The user subsequently authorized committing and pushing the implementation.
Implementation is committed as `0bcfe920291358296587d0a27782d95cc28f9b98`
(`Implement minimum viable snapshots, history and refs`) and pushed to
`micha/dml` branch `master`. The push also published the existing as-built spec
and glossary commits `be4111d` and `b428b01`. Remote `master` was verified at the
new commit. Only an untracked generated `subprojects/.wraplock` remains outside
the commit; it was not staged. A trailing blank line in a new test file was
removed after staged whitespace validation caught it.

Design HEAD remains `043c851`, with pre-existing handoff changes and these notes
uncommitted. This checkout has no remote; no remote was created and no design
changes were pushed. No changes to old `docs/spec/`, versions, public Python
packages or production CLI behavior. The shared glossary's meanings already fit
these objects and did not need amendment.

Implementation changes (paths relative to `../dml`):

- New `include/dml/object.h`, `src/object.c`: narrow names and the four codecs/views.
- `include/dml/dml.h`, `include/dml/repo.h`: expose object and transactional ref APIs.
- `src/record.c`, `src/record_internal.h`: shared envelope writer and record validation.
- `src/object_id.c`: shared hashing; `dml_datum_id()` remains datum-only.
- `src/repo.c`: common typed immutable storage and direct-reference checks; ref
  create/get/update; existing datum lifecycle/rollback contracts preserved.
- `meson.build`: library/header wiring, C object test and native history driver.
- New `tests/c/test_object.c`, `tests/c/history_driver.c`; extended
  `tests/c/core_driver.c` with test-only codecs/storage/corruption commands.
- New `tests/python/test_objects_hypothesis.py`, `tests/python/test_history.py`.
- New `docs/spec-next/objects.md`; updated spec `README.md`, `records.md`,
  `repository.md`, including the Mermaid document-reference map.

Design changes in this turn: this report; README delivery link; discussion status,
outcome and resume point; historical-status annotation at the top of the handoff.
The pre-existing design `AGENTS.md` edit was not amended. Generated build/coverage
outputs were refreshed by standard validation; the empty Meson `.wraplock` created
by these runs was removed after validation, not added to source control.

## Validation and outcome

This section preserves the initial delivery's historical measurements. It is not
superseded evidence of a rerun; new measurements are recorded separately in the
[review follow-up](#review-follow-up).

All commands below run from `../dml`, in the existing development shell unless
otherwise stated. No dependencies were installed and no environment files changed.

| Check | Exit | Actual outcome |
| --- | --- | --- |
| Baseline `nix develop ../dml-build-tools --no-write-lock-file -c bash scripts/check.sh` | 1 | 4 C executables, 22 Python tests pass; baseline coverage gate fails (above) |
| Codec checkpoint: same shell, `meson compile -C build/check && meson test -C build/check --print-errorlogs` | 0 | 5 C executables pass |
| Workflow checkpoint: same shell, `meson compile -C build/check && python3 -m pytest -q` | 0 | Initial 71 Python tests pass |
| Final `nix develop ../dml-build-tools --no-write-lock-file -c bash scripts/check.sh -v` | 1 | Build succeeds; 5 C executables pass under Valgrind; 81 Python tests pass; coverage gate fails |
| Separate history-driver Valgrind harness, nine invocations (below) | 0 | All invocations report 0 errors and 0 allocated bytes at exit |
| `git diff --check` in both checkouts | 0 | No whitespace errors |
| Local Markdown link/heading checker | 0 | 127 local links/anchors checked across 10 documents |

Final standard-check measurements (not adjusted after the additional memory runs):

| Coverage domain | Lines | Functions | Branches |
| --- | --- | --- | --- |
| Filtered C report, including the existing Nix-store intrinsics entry | 881/999 (88.2%) | 78/78 (100%) | 672/902 (74.5%) |
| New `src/object.c` | 157/162 (96.9%) | 10/10 (100%) | 155/168 (92.3%) |
| Shared `src/repo.c` | 304/354 (85.9%) | 29/29 (100%) | 226/308 (73.4%) |
| Python production sources | 31/31 (100%) | — | — |

The unchanged standard gate requires 100% C line/function/branch coverage. Both
baseline gaps and new unexercised paths remain, including allocation failures and
large-size boundaries. **Review correction:** the retained Nix intrinsics entry
has `LF=10`, `LH=8`, so it contributes **2 uncovered lines**, not the 10 originally
claimed here. The historical overall percentages above are unchanged; excluding
this header would not make the gate pass. No thresholds/exclusions changed;
no informational `-c` result is being substituted for a passing gate. The final
build emits the existing Nix `_FORTIFY_SOURCE`/unoptimized-debug warnings; the new
signedness warning seen during development was corrected.

Valgrind flags were `--error-exitcode=101 --leak-check=full --show-leak-kinds=all
--track-origins=yes`. In addition to the five registered C executables, an inline
Python harness created its own temporary directory and ran the history driver:
`negative`, `map-full`, initial/later/branch `snapshot`, ref and historical-ID
`inspect`, aborted `snapshot`, and poisoned `snapshot`. Each process exited 0,
reported zero errors and zero bytes allocated at exit. Only its own scratch was
removed. These runs do not claim exhaustive allocation-failure testing.
Mutation testing, sanitizer builds and concurrent-writer stress were not run.
Windows and other platform builds were subsequently exercised by GitHub Actions
as recorded below.

Session-local diagnostics: `/tmp/dml-iteration1-baseline.log`,
`/tmp/dml-iteration1-codec.log`, `/tmp/dml-iteration1-tests.log`,
`/tmp/dml-iteration1-final.log`, `/tmp/dml-iteration1-memory.log`.
Ignored standard artifacts: `../dml/build/coverage/html/`,
`../dml/build/coverage/python-html/`, and
`../dml/build/check/meson-logs/testlog-valgrind.txt`. Raw Meson JSON logs include
process environment data and were not copied into this design repository.
These paths are diagnostic locations, not durable evidence dependencies; the
commands and checked-in test sources reproduce the tests.

### Acceptance accounting

- **Demonstrated:** initial 42 snapshot and ref in one storage transaction;
  subsequent 43 snapshot with parent C1 and ref update; fresh-process inspection
  resolves 43 then follows the parent to 42. C2/C3 share parent C1. All immutable
  objects' bytes and IDs remain unchanged after ref movement.
- **Demonstrated:** canonical encoding against independent Python byte oracles;
  deterministic IDs and identity changes; tree sorting/duplicates; zero/one/multiple
  ordered parents and duplicate-parent rejection; empty-tree codec.
- **Demonstrated:** truncation at every byte in representative records, malformed
  counts/lengths, unsupported node kinds, noncanonical names and reserved headers.
  Existing datum golden vectors remain unchanged and pass.
- **Demonstrated:** identical reinsertion; missing/wrong-type references at datum,
  root, tree-entry, tree and parent positions; stored corrupt header/type/ID checks;
  missing refs, duplicate create, absent update, invalid names, no-op/backward update,
  invalid targets and malformed ref width.
- **Demonstrated:** abort and poisoned-commit rollback hide all five new object
  types and preserve the previous ref, including when failure occurs after the ref
  was already updated. Map-full rollback and full-batch retry after larger-map
  reopen also pass.
- **Demonstrated:** same-transaction references and ref targets, owned buffer cleanup,
  consumed handles, close with active transaction rejection and read-only ref writes.
  Direct validation's non-transitive boundary is explicitly tested and documented.
- **Outstanding:** default coverage gate; not all low-level failure paths are tested.
  No broader safety or production-readiness claim follows from these finite checks.

## Choices, deviations and limits

The implementation adopts the sketch above without adding deferred subsystems.
Rather than four repeated public put/get/codec families, it uses explicit
type-discriminated APIs. Stored and expected types are still checked; no plugin
registry or extensible schema framework was introduced.

Names deliberately use the narrow ASCII profile rather than Unicode normalization.
Parent duplicate validation is quadratic; repeated indexed tree-entry access scans
preceding entries and makes whole-tree reference checking quadratic. This minimal
implementation is tested with small histories, not benchmarked for large trees or
parent lists. No computational execution semantics follow from literal DAG storage.

Direct checks do not recursively prove the full stored graph valid. Ref updates
validate the new target and existing ref width, not the previous target's integrity;
a correctly sized dangling ref can be repaired explicitly. Standard LMDB atomicity
and the existing external-synchronization/thread-affinity requirements are retained,
not expanded into ancestry, compare-and-swap or remote coordination guarantees.

Wrong-type IDs absent from the expected typed keyspace report `not_found`; wrong
record types injected under an expected key report `invalid_kind`. This differs
from the existing composite-datum missing-reference error (`invalid_kind`) and is
explicit in the spec. Existing immutable-key corruption is never overwritten;
malformed existing bytes may return the codec/type error rather than a blanket
integrity error. Metadata schema and envelope format numbers remain 1 under the
agreed ephemeral pre-1.0 policy; no migration machinery was added.

## Publication and GitHub Actions checkpoint

Following the user's explicit request, committed the 18 implementation/code/test/spec
files and ran `git push origin master` (exit 0). No force push, tags, releases,
manual deployment or workflow changes were made.

[CI run 40444854493](https://github.com/micha/dml/actions/runs/40444854493)
ran for the exact committed SHA and completed successfully. Monitoring command:

```sh
gh run watch 40444854493 -R micha/dml --compact --exit-status --interval 15
```

Exit 0. Final run status and remote `master` SHA were checked again through
`gh run view`, `gh run list --commit` and `git ls-remote`. CI was the only workflow
triggered for this SHA; the release workflow is tag/manual-only and was not run.

| Job | Outcome | Test results from completed job logs |
| --- | --- | --- |
| Linux x86_64 | Success | 5 C executables, 81 Python tests |
| Linux aarch64 | Success | 5 C executables, 81 Python tests |
| macOS x86_64 | Success | 5 C executables, 81 Python tests |
| macOS arm64 | Success | 5 C executables, 81 Python tests |
| Windows AMD64 | Success | 5 C executables, 81 Python tests |
| Strict Linux check.sh | Success | 5 C executables, 81 Python tests; coverage reports generated |

Despite its name, `Strict Linux check.sh` invokes `scripts/check.sh -c`; its logs
explicitly say coverage thresholds are disabled. A green GitHub run does **not**
resolve or waive the failing local default percentage gate above. Session-local
CI diagnostics are `/tmp/dml-iteration1-actions-watch.log` and
`/tmp/dml-iteration1-actions.log`; raw logs were not committed.

## Review follow-up

### Scope, source state and policy correction

The user reviewed the first turn and authorized bounded testing/documentation
hardening, not a new feature iteration. The review found no functional correctness
defect in the new object/ref implementation; direct-reference checking, ASCII
names, supplied parent order and the small
quadratic operations remain accepted choices, not requests for expansion.

The user subsequently clarified that **100% coverage is a means, not an end**:
precise no-value exclusions are permitted without asking for each one. Difficulty
alone is not a rationale. Preserve the threshold on remaining code, document each
location/reason and distinguish exclusions from tests. This supersedes the earlier
blanket prohibition. The policy is now recorded in implementation/design AGENTS
and reconciled in the handoff's test guidance. The historical percentages above
have not been changed. The GCC-header claim was visibly corrected: LF=10, LH=8
means **2**, not 10, uncovered lines.

Implementation HEAD remains `0bcfe920291358296587d0a27782d95cc28f9b98` on `master`;
no new commits, pushes or GitHub workflow runs were made. Design HEAD remains
`043c851` on `main`, with the existing uncommitted handoff/design changes preserved.
The pre-existing generated `subprojects/.wraplock` remains untracked and untouched.
No delegates, global installs or OS configuration changes were used.

During validation, unrelated concurrent LSP work appeared: `.gitignore`,
`scripts/setup-lsp.sh`, `tests/python/test_setup_lsp.py`, and a C-editor section
in the implementation README. Those changes were not edited or adopted as this
follow-up's deliverables. The final standard run sees their 3 tests in addition
to this follow-up's 83 Python tests; the combined current tree reports 86 tests.
The shared README contains both owners' separate changes. No cleanup or Git
operation discarded those changes.

### Delivered changes

- `docs/architecture.md` now describes the implemented datum/object/ref module
  boundaries and points to `docs/spec-next/README.md` rather than presenting DAG/
  commit codecs as future functionality or the old draft as implemented behavior.
- The implementation README links the as-built spec, glossary and coverage scope;
  the old spec is explicitly draft context. `docs/spec/` remains unchanged.
- New `tests/c/test_boundaries.c` covers arithmetic, malformed records, counts,
  lengths, invalid arguments, canonical text/numbers/URIs and accessor bounds.
- New `tests/c/test_faults.c`, `fault_control.h`, `fault_injection.h` and
  `fault_injection.c` exercise codec/identity allocations, URI and LMDB error
  cleanup, empty failure outputs, schema/path edges, composite references,
  collision rejection and poisoned object/ref rollback. The hash collision is
  deliberately simulated, not a discovered XXH3 collision.
- `meson.build` builds a private fault-test core from the same source list with
  dependency-call substitutions. The installed library has no fault state or
  test API. Seven C executables are registered, versus five in the first turn.
- `tests/python/test_history.py` adds two test-only malformed legacy tombstone
  fixtures; no public corruption/excision operation was added.
- `src/object.c`, `object_id.c`, `record.c`, `repo.c`, `uri.c` have precise coverage
  markers/comments and small condition-layout changes, not changed wire formats
  or public behavior. Checks remain compiled and present.
- `scripts/check.sh` newly removes only the exact compiler-header family
  `*/lib/gcc/*/include/emmintrin.h`. Thresholds remain unchanged at 100%.
- [Coverage catalog](../../../dml/tests/coverage-exclusions.md) records every exact
  statement/region and its invariant or no-value rationale. Implementation AGENTS
  links this owning document; the design guide and handoff preserve the policy.

### Actual commands and outcomes

Commands run from `../dml`. The existing `../dml-build-tools` environment was used
with `--quiet --log-format raw --no-write-lock-file`; no environment/package change
was required.

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

**Final exit 0:** build succeeds; all **7 C executables** pass under Valgrind;
**86 Python tests** pass in the combined current tree (83 in this follow-up's
suite plus 3 unrelated LSP tests). Production Python coverage remains 31/31, 100%.
All seven C processes report **0 errors and 0 bytes allocated at exit** with
`--error-exitcode=101 --leak-check=full --show-leak-kinds=all --track-origins=yes`.
The default C percentage gate passes; no `-c` result substitutes for it.

A marker-free diagnostic of the same final counters was also captured:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash -c 'lcov --capture --no-markers --ignore-errors unused \
    --directory build/check \
    --exclude "/usr/*" --exclude "*/subprojects/*" \
    --exclude "*/tests/*" --exclude "*/build/check/*" \
    --output-file build/coverage/lcov.review-unexcluded.filtered.info \
    --rc branch_coverage=1'
```

**Exit 0.** These are the pre-existing non-DML source filters, applied early so
unretained dependency data cannot fail the marker-free diagnostic. This command
keeps the GCC header and ignores all new source markers. `unused` handling is for
filters absent on this host, not a suppression of branches or consistency checks
in DML source. It emits an LMDB dependency-only gcov consistency warning and two
unused-pattern warnings; those do not affect the retained DML data.

| Population | Lines | Functions | Branches |
| --- | --- | --- | --- |
| Historical initial-delivery filtered report | 881/999 (88.2%) | 78/78 (100%) | 672/902 (74.5%) |
| Final marker-free diagnostic, retaining GCC header | 999/1006 (99.3%) | 78/78 (100%) | 881/902 (97.7%) |
| Final default-gate population after authorized exclusions | 990/990 (100%) | 78/78 (100%) | 835/835 (100%) |

The new marker-free line denominator differs from the historical one because
conditions were formatted onto separate lines; it is not a rewrite of the earlier
measurements. Exclusions remove **16 measured lines** and **67 branch outcomes**,
with **zero excluded functions**. Of those removed populations, gcov had recorded
hits for 9 lines and 46 outcomes. They are excluded from the denominator, not
credited as passing tests. The remaining 7 lines and 21 outcomes lack recorded
hits. Line-wide branch markers necessarily remove some already-tested reachable
outcomes together with their impossible edge; their test assertions remain.

Exact excluded-source accounting from the two final tracefiles:

| Source | Removed lines | Removed branch outcomes | Rationale authority |
| --- | --- | --- | --- |
| GCC `emmintrin.h` | 10 (8 recorded hits) | 0 | Dependency-only intrinsic implementations |
| `src/object.c` | 3: tree-size error return, sorted-array overflow error return, second-switch default | 15 | Validated types, supported 64-bit size bounds and no-value multi-GiB repetition |
| `src/object_id.c` | 0 | 4 | Validated type range |
| `src/record.c` | 0 | 22 | Exhaustive switches and impossible add-4 overflow after aligned multiplication |
| `src/repo.c` | 0 | 4 | External mkdir timing race and already-validated allocation-free decoder |
| `src/uri.c` | 3: non-hex return and malformed-escape cleanup/error return | 22 | Original grammar validation and nonnegative dependency size output |

The [catalog](../../../dml/tests/coverage-exclusions.md#exact-exclusions) provides
precise function/statement locations, inline marker scope, preserved tests and
re-evaluation requirements. None of the meaningful allocation-failure handlers,
transaction rollback paths or supported API argument checks were excluded.

Intermediate checks are not hidden:

- Before the final test additions/exclusions, a default `-v` run exited 1 with
  7 C executables and 81 Python tests passing, but only 961/999 lines and 804/902
  branches. A later pre-exclusion run improved to 99.0% lines and 96.9% branches,
  still exit 1. Functions were 100% throughout these follow-up runs.
- An exclusion-narrowing checkpoint exited 1 at 841/843 branches (99.8%); the
  two impossible type-range edges were attributed to the first line by GCC.
  Their branch groups were explicitly documented and marked rather than changing
  the runtime guards or accepting 99.8% as success.
- Another `-v` run was interrupted by the concurrent LSP check's Meson wipe:
  a test-owned directory disappeared, so `test_faults` failed its `fopen` assertion
  (6/7 C executables passed; Valgrind still reported no leaks/errors). Its subsequent
  diagnostic failed on missing `.gcno` data. The active concurrent run was observed,
  left untouched and allowed to finish; the final isolated standard run above
  rebuilt and passed. That interrupted run is not passing evidence.
- Initial unrestricted marker-free capture failed consistency checks in dependency
  data; a capture with the usual filters then exited 1 solely on unused filter
  patterns. The successful diagnostic above uses the same scope and narrowly
  handles those unused patterns. No DML consistency check was disabled.

Logs are session-local diagnostics, not committed evidence dependencies:
`/tmp/dml-review-tests.log`, `/tmp/dml-review-tests2.log`,
`/tmp/dml-review-initial-check.log`, `/tmp/dml-review-pre-exclusions.log`,
`/tmp/dml-review-markers-check.log`, `/tmp/dml-review-interrupted-check.log`,
`/tmp/dml-review-final-check.log`, `/tmp/dml-review-unexcluded-final.log`.
Standard ignored artifacts contain the final filtered trace and Valgrind test log;
`build/coverage/lcov.review-unexcluded.filtered.info` is the additional diagnostic.
Raw Meson environment-bearing JSON logs were not copied into design notes.

The final documentation/source checks also pass: `git diff --check` in both
checkouts, a local Markdown checker covering **162 links/anchors in 15 documents**,
and whitespace checks on the new files. `git diff --stat -- docs/spec` is empty.
`nm build/check/libdml.a` contains no `dml_test_` symbols, confirming that the
installed-library archive does not contain the fault hooks.

### Limits and stop point

No new repository functionality, transitive validation, name expansion, merge,
execution or optimization was added. Checks still run; coverage does not prove
scientific validity, capture completeness or general concurrency safety. The
exclusions and arithmetic reasoning target the currently supported 64-bit matrix.
The new follow-up was validated locally on Linux, not through a new Windows/macOS
CI run; the earlier published CI evidence applies to commit `0bcfe92`, not these
uncommitted changes. Mutation testing and sanitizer builds were not run.

This follow-up is left uncommitted for user review. The user should review both the
meaningful failure tests and the explicitly unmeasured regions; the percentage
alone is not the acceptance argument.

## Final URI diagnostic correction

The user accepted the follow-up review and authorized only this remaining
correction. A pre-existing diagnostic bug in `src/uri.c` discarded the return code
from `uriToStringCharsRequiredA()` and reported the preceding normalization
success. The new size-failure fixture had codified that bug by expecting
`error.native_code == URI_SUCCESS`. This section supersedes that expectation,
not the original object/ref review or the historical measurements above.

Changes relative to the preceding uncommitted follow-up are limited to:

- `src/uri.c`: assign the size-calculation result to `status` within the existing
  short-circuited failure condition. Normalization failure still skips sizing;
  failed sizing reports its actual native code through the existing error path.
  Cleanup, empty failure output, normal serialization and error classification
  are preserved.
- `tests/c/test_faults.c`: inject `URI_ERROR_OUTPUT_TOO_LARGE` for the size routine
  and require `error.native_code == injected_code`. Other fault cases remain
  unchanged. The pinned `UriRecompose.c` calls the allocation-free size engine;
  its overflow return `URI_ERROR_TOSTRING_TOO_LONG` aliases the supported
  `URI_ERROR_OUTPUT_TOO_LARGE` in `UriBase.h`.
- These delivery notes and the discussion resume point.

No additional exclusions, threshold changes, APIs or feature work were introduced.
The prior justified coverage markers and compiler-header filter are unchanged.
Existing LSP changes, the generated `.wraplock`, and earlier design notes were
preserved. Implementation HEAD remains `0bcfe920291358296587d0a27782d95cc28f9b98`;
design HEAD remains `043c851f1eadac958d3596bf2c7c3e5a126ecf23`. All new correction
changes remain uncommitted; there were no pushes, delegates or global/OS changes.

### Regression and final validation

From the implementation checkout, after changing the fixture but before fixing
the production code:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash -c 'meson compile -C build/check && \
    meson test -C build/check test_faults --print-errorlogs'
```

**Exit 1**, as expected: the fault test fails its
`error.native_code == injected_code` assertion (line 133). The existing bug is
therefore demonstrated by the corrected fixture, rather than hidden by it.
Session-local log: `/tmp/dml-uri-size-regression.log`.

After the one-line production fix, with no other `check.sh` process active:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

**Exit 0:** all 7 C executables pass under Valgrind; all 86 Python tests in the
combined current tree pass (83 in the bounded repository suite plus 3 unrelated
LSP tests). All seven C processes report 0 errors and 0 bytes allocated at exit
using the standard `-v` flags. Python production coverage remains 31/31, 100%.
Retained C coverage is unchanged: **990/990 lines, 78/78 functions, 835/835 branch
outcomes**, all 100%. This is a fresh default-gate result, not informational `-c`
validation. The regression path is tested, not excluded.

The marker-free diagnostic in the preceding follow-up section is historical to
that run; it was not freshly recaptured for this correction. Final standard
artifacts were refreshed by the command above. The previous filtered trace was
copied to `/tmp/dml-uri-review-prior-lcov.info` before rerunning; the final log is
`/tmp/dml-uri-size-final-check.log`. No raw environment-bearing Meson JSON was
copied into design notes. No new remote/platform, sanitizer or mutation runs were
performed. `git diff --check` passes in both checkouts; the local Markdown checker
passes 165 links/anchors across 15 documents. The Git indexes remain empty. The
correction is stopped for user review.

## Follow-up publication checkpoint

The user explicitly authorized a focused implementation commit, normal push and
Actions monitoring after accepting the reviews. The complete 1,424-line staged
diff was read before committing; staged whitespace and scope checks passed.
Only the reviewed 17 implementation/testing/documentation files were committed.
README was staged with a cached patch containing only its as-built/coverage
orientation hunk, leaving the unrelated editor section in the working tree.

Implementation commit:
`6ee93293ea10d7950c1cdc894b18dda695c55baf`
(`Harden repository tests and fix URI size error propagation`).
`git push origin master` exited **0**. Existing remote/branch state was fetched
and verified before publication; remote `refs/heads/master` was then verified at
the exact new SHA. No remote was created, force push used, tag/release made or
account/environment setting changed.

[CI run 40452494677](https://github.com/micha/dml/actions/runs/40452494677) was
identified by that exact SHA, monitored to terminal **success**, and checked again
through `gh run view` and `gh run list --commit`. CI was the only workflow run for
this SHA; the release workflow was not triggered. Monitoring command:

```sh
gh run watch 40452494677 -R micha/dml --compact --exit-status --interval 15
```

Exit **0**. Completed logs report these per-job measurements for the published
source population, not the prior commit's CI:

| Job | Outcome | C executables | Python tests |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40452494677/job/122018210845) | Success | 7 pass, 0 fail | 83 pass |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40452494677/job/122018210817) | Success | 7 pass, 0 fail | 83 pass |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40452494677/job/122018210784) | Success | 7 pass, 0 fail | 83 pass |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40452494677/job/122018210832) | Success | 7 pass, 0 fail | 83 pass |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40452494677/job/122018210765) | Success | 7 pass, 0 fail | 83 pass |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40452494677/job/122018210670) | Success | 7 pass, 0 fail | 83 pass |

The Linux validation job reports retained 990/990 lines, 78/78 functions and
835/835 branches (100%), but explicitly runs `scripts/check.sh -c` with percentage
thresholds disabled. Its success is informational and does **not** replace the
already-recorded passing local default `scripts/check.sh -v` gate. The local
combined-tree run had 86 Python tests: the published 83 plus 3 excluded, unrelated
LSP tests. Local Valgrind evidence covers all seven C executables; CI was not a
new Valgrind run. Publication did not change the reviewed source code or exclusions.

Remaining implementation working-tree changes are deliberately unstaged:

- `.gitignore`: unrelated editor database ignore entries.
- `README.md`: only the 16-line C Editor Setup section.
- Untracked `scripts/setup-lsp.sh` and `tests/python/test_setup_lsp.py`: unrelated
  LSP work, not published.
- Untracked generated `subprojects/.wraplock`: preserved, not published.

Build/coverage outputs and raw diagnostic logs are ignored and were not staged.
No staged changes remain. The design checkout stays at `043c851` with its
pre-existing guide/README/discussion/handoff edits and delivery notes uncommitted;
it still has no remote, and no design commit or push was made. These historical
local-phase references to uncommitted implementation changes are superseded by
this explicit publication checkpoint, not silently rewritten as earlier approval.

Session-local Actions diagnostics are `/tmp/dml-hardening-publication-watch.log`
and `/tmp/dml-hardening-publication-actions.log`; raw environment-bearing logs
were not committed. No failing job required investigation or fixes. No delegates,
feature expansion or subsequent iteration began. Publication and monitoring are
complete; stop for user/coordinator review.

## Suggested next turn — not started

The initially suggested coverage-hardening turn, final URI diagnostic correction
and authorized publication checkpoint are recorded above. Stop here; selection of
any new functionality turn remains user-led. No execution, remotes,
resource work or later observer stage has started.
