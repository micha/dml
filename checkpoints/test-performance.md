# Checkpoint: test performance and parallel execution

The user requested “let's make a checkpoint here” after local commits and review
of the next two slow tests. This records completed work and a possible resume
point, **not permission for another optimization, test run or push**.

## Current state

- DML is clean at local commit `55a73e9fa4895cce39a081070ebff906a3b67f19`,
  parent `59b38303fe2f4c89d6fce3b01933f7260eb28320`. It has **not been pushed**.
- The initial detailed [performance results](../maintenance/test-performance/RESULTS.md)
  were committed in this design repository as `99cd523`.
- The external `/work/repos/micha/dml-build-tools/flake.nix` includes pytest-xdist,
  with unchanged lockfile. That directory is not Git-versioned; original/final
  bytes are retained with the trial evidence.
- Iteration24's published delivery and [learning review](24-lessons.md) remain
  historical. This separate user-authorized performance work did not reopen its
  installed story, add a new feature iteration or resume the native investigation.

## What was measured and changed

The original serial Python suite passed3357 tests in **32m14s**, without Python
coverage instrumentation. Its two slowest tests spent **8m40s** and **3m37s**
constructing and validating small captured-call histories.

Profiling identified repeated example-level authority validation:20164 builtin
reachability scans and28.5 million native record reads across those two tests.
This was evidence of redundant validation work, not proof of a native storage
bottleneck or diagnosis of the paused LMDB/lifetime issue.

The committed helper reuses successful pinned-history proofs within ONE
synchronous inspection call. Repository/identity/depth separation, semantic
budget checks, failure propagation and fresh independent validation remain.
The original tests/assertions are unchanged; four new regressions protect the
optimization. No native layout/entity, deadline, threshold or exclusion changed.

| Evidence | Actual outcome |
| --- | --- |
| Final serial focused tests, no Python coverage | 250 pass; slow tests **4m25s / 2m28s**, about44% less combined time |
| Standard full `scripts/check.sh -v` | True exit0;3361 Python tests, seven native tests, memory checks and unchanged100% coverage gates pass |
| ONE four-worker Python trial, no Python coverage | **3361 pass in8m58s**, two original warnings, no failures/errors/skips/retries |

The32m14s->8m58s comparison is about3.6x end-to-end improvement from BOTH
optimization and parallel execution, not an isolated parallel speedup. No full
optimized serial/no-coverage replay was performed. Native binaries still have
debug/gcov instrumentation; these are not release-build benchmarks.

## Parallel execution is optional and still a trial

pytest-xdist is now a declared development dependency and available in the Nix
tools. The trial used four workers, loadgroup scheduling, no worker restart and
an evidence-local plugin for grouping, phase timings and isolated native counters.
It grouped captured profiles, captured reuse guards and native lifecycle tests
by module to avoid repeated expensive setup. Ordinary testing remains serial;
no maintained default parallel runner or parallel coverage gate was introduced.

The successful trial does NOT replace the serial standard gate: xdist omitted
native suite-level properties from JUnit XML. Worker-local test/fixture evidence
remains, and accepted Python/native coverage data was preserved. The later serial
smoke's counter writes were archived and the original accepted native counters
restored exactly. Full provenance and raw preparation failure are in the results.

## Suggested resume point: expensive fixture consumers

Excluding the two previously optimized tests, the next two by TOTAL duration in
the parallel trial are in `tests/python/test_captured_call_adapter_responses.py`:

| Test | Total | Setup | Body |
| --- | ---: | ---: | ---: |
| `test_native_reuse_positive_then_HOST_pinned_witness_response_guard` | 42.7s | 33.4s | 9.3s |
| `test_Host_pinned_selected_response_guard_BEFORE_own_double_Q[pinned-pinned double selection changed]` | 41.7s | 33.4s | 8.2s |

This consuming module imports the expensive module-scoped reuse-history fixture
but was not grouped in the trial. Its setup therefore ran on multiple workers.
Grouping this module is the assistant's suggested next experiment, **not an
approved change or demonstrated improvement**. Rankings include setup and depend
on worker scheduling; they are not rankings of body cost alone. Further DML
profiling, maintained parallel-tool integration and fixture grouping remain
separate possible directions requiring user selection.

## Stop line

This checkpoint authorizes local design documentation and commit only. No push,
new test/build/install/profile/story/worker/CI run or next optimization begins.
Development GHA remains disabled; release controls unchanged. Native19 remains
PAUSED with its private candidate retained; VP-001 OPEN/UNKNOWN and existing
owner/revisit conditions remain. No earlier failure diagnosis, standing waiver,
all-platform-green or parallel-coverage assurance is claimed.
