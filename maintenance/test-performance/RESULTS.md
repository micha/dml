# Slow-test performance — bounded local work

Subsequent separately authorized work: [resource-aware parallel coverage](PARALLEL-COVERAGE.md)
is locally validated/uncommitted. The records below own the earlier committed optimization
and no-coverage trial; they do not describe the newer coverage profile or current source diff.

Status: locally committed and validated; **not pushed**.
DML commit: `55a73e9fa4895cce39a081070ebff906a3b67f19`
(parent `59b38303fe2f4c89d6fce3b01933f7260eb28320`), exact three paths:
`examples/captured_calls.py`, `tests/python/test_captured_call_inspection_proofs.py`,
`requirements-dev.txt`. User explicitly requested a commit after reviewing the
successful parallel trial. Validated helper/regression/dependency bytes and exact
staged scope were verified before commit; implementation source/index clean afterward.
No push or CI launch was requested or performed.
The user requested per-test timing, then chose optimizing the two slowest tests
before parallelization and said “proceed”. The initial optimization below was
followed by separately approved pytest-xdist preparation and ONE four-worker
trial; see [parallel trial](#parallel-trial). No CI enable/run or push was performed.
The later explicitly requested local commits are recorded above. This is separate
from the paused Iteration19 native investigation; it does not diagnose VP-001.

## Baseline and measured cause

Implementation parent: `59b38303fe2f4c89d6fce3b01933f7260eb28320`.
One serial Python-only timing run, using existing native binaries without
coverage.py: **3357 passed, two warnings, 1933.89 seconds**.
Evidence: `../dml/build/test-timings/20261104T000706Z/` (relative to repository root).
All testcase totals are in `timings.csv`; setup/call/teardown in `pytest.log`;
module aggregates in `summary.json`; actual results in `timings.xml`.

The two largest testcase totals were 519.92s (retained selected ancestry/depth
boundary) and 216.54s (outer reuse/swapped-input inner reuse/default pinning).
They account for about38% of aggregate testcase time. Captured-call tests:
246 cases, 1134.654s, about59%. Setup across the suite was approximately684s;
body time1243s (rounded textual phase durations).

A separate cProfile run of ONLY these two tests passed. Evidence:
`../dml/build/test-performance/20261104T202628Z-baseline/`.
It recorded 1087080681 function calls, 20164 builtin Inspector constructions/
retained-history scans and 28485351 native get_record calls. The recursive
request/spine/selection/leaf-completion validators repeatedly validate the same
pinned histories. Profiled wall/test timings are inflated by instrumentation and
are **not** the speedup baseline. This identifies repeated work in the
example-level validation/recording integration, not a native storage diagnosis.

## Change and preserved invariants

Only implementation helper `examples/captured_calls.py` changed; new regression
file `tests/python/test_captured_call_inspection_proofs.py`. The two original slow
tests and all their assertions remain unchanged. No native/runtime entity/layout,
old helper API, diagram, test deadline, threshold, exclusion or workflow changed.

The five recursive inspection entrypoints share successful proofs within ONE
synchronous inspection call using an example-private ContextVar. Keys include
validator identity, resolved repository path, ALL supplied pinned identities and
exact authority depth. No cross-call/global/history-discovery cache. Source
repository inspection is read-only; temporary public packet-validation stores
remain unchanged. Failed checks are not cached and the root context resets even
on error. Every hit contributes the proof's complete reached semantic IDs and
rechecks the caller's aggregate64 budget. Completion/selection responses expose
the caller's full union without mutating cached results. Reached IDs propagate
on failure as before. No depth reset, skipped authority edge, fake success,
external execution substitution or removed negative assertion was introduced.

Four new tests cover successful reuse and fresh-call revalidation; repository/
commit/depth isolation and rejection beyond8; aggregate budget checking on cache
hits; failed-check noncaching/reached-ID preservation/context cleanup.

## Validation and timings

| Evidence | Result |
| --- | --- |
| `../dml/build/test-performance/20261104T204656Z-optimized/` | Two original tests PASS,406.89s total; testcase260.162s/145.963s. Earlier draft before final union-response/failure propagation refinements. |
| `../dml/build/test-performance/20261104T205451Z-focused/` | Final250 captured-call tests PASS,797.57s; slow testcase264.515s/148.454s. No coverage instrumentation. Final source diff retained; this run did not record start/end timestamps. |
| `../dml/build/test-performance/20261104T210836Z-full/` | ONE final standard `scripts/check.sh -v`, with only pytest timing/XML reporting flags: trueexit0;3361 Python tests PASS/two warnings,2324.42s; seven native tests pass; binding memory and141 native CLI Valgrind processes pass; Python9005/9005 lines and native1667lines/131functions/1550branches100%. Source copies/diff/start/end/log/XML/exit retained. |

Like-for-like no-coverage timings: ancestry519.92->264.515s (about49% less),
reuse216.54->148.454s (about31% less), combined736.46->412.969s (about44% less,
roughly5m23 saved). Different runs/machine load can affect these measurements;
no whole-suite optimized no-coverage replay was performed, so there is no measured
new whole-suite timing at that setting. Full coverage-enabled timings are separate:
ancestry403.226s/reuse226.739s. Native binaries remain debug/gcov-instrumented even
in the no-coverage.py runs; these are not release-build performance measurements.

The full gate took approximately40m48s including rebuild/Valgrind/reporting.
It is a true successful standard gate, unlike Iteration24's historical original
coverage-report failure; that older failure remains historical, not rewritten.
Mull was not requested. Two runpy warnings for Floci/SSH module execution remain;
lcov emitted dependency/unused-pattern warnings. Thresholds/exclusions unchanged.
No installed story or additional native-investigation probes were run.

## Limitations and stop line

This is a meaningful first optimization, not a claim that DML performance is
solved. The ancestry test still takes over4 minutes without Python coverage;
repeated reachability/serialization and work across independent inspections
remain plausible next profiling targets. No durable cache or cache invalidation
API is proposed. Next-stage approval and evidence are recorded below. Development GHA remains
disabled; no platform/all-green claim.

At the initial optimization stop, only the helper and new regression path were
modified/untracked. Native validation build/coverage outputs were refreshed by
the authorized standard gate. No source publication or design checkpoint commit
was made.

## Parallel trial

The user subsequently said “proceed” to the explicit offer to add pytest-xdist
and run a bounded four-worker trial. Added `pytest-xdist>=3.6` to DML's
`requirements-dev.txt` and `p.pytest-xdist` to the existing external
`/work/repos/micha/dml-build-tools/flake.nix`. The latter is not a Git repository;
its exact original/final files are retained with the evidence. Lockfile bytes
unchanged; no system configuration/service/global profile change. Offline
preparation failed because dependencies were not cached (raw logs retained),
then normal Nix package-cache preparation succeeded: pytest9.0.3,
pytest-xdist3.8.0, execnet2.1.2. Only tooling derivations built, not DML.

ONE serial-free four-worker Python suite invocation:
`pytest -n 4 --dist=loadgroup --max-worker-restart=0`, without coverage.py,
using the existing native binaries. Timing/XML flags remain enabled; no changed
runtime deadline/threshold/assertion, automatic retry or worker restart.

Evidence: `../dml/build/test-parallel/20261105T025720Z-four-workers/`.
Actual exit0; **3361 passed, two original runpy warnings,538.48s (8m58s)**;
XML3361/zero failures/errors/skips, empty stderr. All four workers independently
collected3361 cases. Per-worker journals account for266+1071+519+1505 test bodies
and about531–534s work per worker. Three shared-fixture modules were each assigned
to exactly ONE worker: captured profiles (gw0), captured reuse guards (gw2), and
native lifecycle (gw1, avoiding duplicated private compilation/session setup).
No live pytest/execnet/trial descendants found after completion.

The trial-only plugin `dml_parallel_trial.py` lives IN the evidence directory,
loaded with `PYTHONPATH=<evidence> -p dml_parallel_trial`. It adds grouping marks
BEFORE xdist handles collection, writes phase journals and directs native gcov
counters into worker-specific evidence paths. It does not change the maintained
conftest, tests, scheduler implementation or runtime. `command`, timestamps,
`stdout`, `pytest.xml`, `timings.csv`, `summary.json`, collection reports and
worker phase journals make the run auditable. No new default parallel mode or
parallel full-gate/coverage integration was selected.

Important qualification: xdist's `record_testsuite_property` does not propagate
native lifecycle suite properties into the controller's JUnit report: actual
parallel XML has ZERO suite properties. Per-test results and worker-local fixture
files exist, but this timing trial is NOT a replacement for the accepted serial
standard gate's diagnostic/coverage evidence.

The previous accepted Python coverage database, native counters and reports
were copied before any parallel work. Post-trial identities confirm exact helper/
regression/binaries/Python coverage/lcov report and shared native-counter bytes.
A subsequent default-SERIAL smoke with xdist installed passed the four proof
regressions in0.75s; its startup wrote shared native counters. Those raw smoke
counters were archived, then the original accepted counters restored and their
complete digest manifest verified exact. No `.coverage` erase, report overwrite,
DML rebuild or full-suite replay was performed in this parallel stage.

The earlier ORIGINAL unoptimized serial suite took32m14s; the optimized parallel
trial takes8m58s, about3.6x faster end-to-end. That comparison includes BOTH
optimization and parallelization, not an isolated3.6x parallel speedup. No full
optimized serial/no-coverage replay exists. Individual heavy tests slowed under
contention: ancestry322.701s and reuse180.954s versus optimized serial focused
264.515s/148.454s. Parallel scheduling still greatly reduced wall time.

The external tools flake change remains outside Git; exact original/final bytes
are retained with the trial evidence. This results note is committed separately
in the design repository. No push, CI run, system change, paused-investigation
restart or next feature turn. Local work is stopped pending further user direction.
