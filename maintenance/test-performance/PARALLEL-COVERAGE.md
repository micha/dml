# Resource-aware parallel coverage — local implementation and validation

Later optimization: [inspection-local history/read memoization](HISTORY-MEMO.md).
This report owns the earlier14m42s baseline; current final gate is11m53s with the
additional example-only changes, not a rewritten outcome for the earlier run.

Status: **implemented and locally validated, uncommitted/unpublished** at parent
`55a73e9fa4895cce39a081070ebff906a3b67f19`. The user requested continuing test
optimization toward a five-minute full-suite target, then agreed to parallel
coverage with workers selected from available CPU and memory and said “proceed”.
This separate bounded tooling work does not reopen Iteration24 or native19.
No coding worker/extra agent, CI launch, workflow edit, push or release occurred.

## As built

- `DML_TEST_WORKERS=auto scripts/check.sh -v` uses pytest-cov/xdist, preserving
  the original source scope, EXACT existing omission list and coverage.py
  report/XML/HTML thresholds. Default remains serial (`0`); explicit numeric
  worker counts are diagnostic overrides. No fast/slow test modes introduced.
- `scripts/test_resources.py` reads host memory/process eligibility and visible
  Linux cgroup v1/v2 parent CPU/memory constraints. Admission is the minimum of
  known host physical cores (logical fallback), affinity/quota and remaining
  memory after reserve. Unknown detection selects one worker with a diagnostic;
  known insufficient memory/invalid allowances fail clearly.
- Initial conservative allowance:1024MiB per worker +1024MiB reserve, adjustable
  via positive integer `DML_TEST_WORKER_MB`/`DML_TEST_RESERVE_MB`. This is NOT an
  enforced memory limit or OOM guarantee. Windows job quotas are not detected.
- Root `conftest.py` loads `tests/parallel_validation.py` early enough for the
  controller's auto-count hook. Native Python package bootstrap is unchanged.
  Shared history fixture CONSUMING modules are grouped, including the previously
  missed adapter-response module. No per-test assertion or deadline changed.
- Worker process-tree RSS is sampled once per second. Shared pages can be counted
  more than once; transient peaks can be missed. Exit/errors/memory/resource
  decisions and actual native suite properties are retained in worker reports.
- `record_testsuite_property` forwards through the original pytest fixture, then
  transfers worker values to the controller's JUnit logger. This bridges upstream
  xdist's missing suite properties; no reconstructed/fake native evidence.
- Native worker counters are isolated with GCOV_PREFIX/STRIP and merged with
  initial C-test counters by matching GCC `gcov-tool`. Relocation variables are
  cleared ONLY for the merge subprocess. Raw numeric counter union is tested;
  no invented coverage hits, threshold reduction or new exclusion.
- pytest-cov7 does not silently instrument application subprocesses; no coverage
  subprocess patch enabled. The existing coverage measurement scope is retained.

The implementation [Build and Test](../../../dml/README.md#optional-resource-aware-parallel-coverage)
owns commands/limits. The [validation policy](../../../dml/docs/validation-policy.md)
remains authoritative. No LMDB entity/relationship/layout change, so the as-built
entity diagram is unchanged. Native/library execution code is unchanged.

## Dependencies and portability boundary

Declared development dependencies now include pytest-cov>=7 and psutil>=5.9;
current profile requires development Python>=3.9, not a change to the installed
library's Python requirement. External Nix tools add the matching packages;
lockfile unchanged, original/final flake bytes retained. Tested versions:
pytest-cov7.1.0, psutil7.2.2, xdist3.8.0, coverage7.14.1, GCC/gcov-tool15.3.0.
Normal package-cache preparation was authorized; no global profile/service/config
change. External tools directory is not Git-versioned.

This is LOCAL Linux/GCC validation, not all-platform/CI certification. Workflow
provisioning is untouched: in particular existing Windows MSYS2 provisioning must
supply the new declared dependencies for the added support tests/profile; native
counter merging requires a matching GNU toolchain. Hosted Windows/macOS integration
is not demonstrated. Development GHA remains disabled by decision; no enable/run
or budget/runner/release-control changes were made.

## Retained evidence and failures

Evidence root (relative to repository root):
`../dml/build/parallel-coverage/20261105T150920Z/`.
Previous accepted coverage database/reports/counters and tool flake/lock were
preserved in `before/` before code/build activity.

| Evidence | Actual outcome |
| --- | --- |
| `focused-v1/` |61pass, sizing policy120/120 lines measured100%; earlier draft |
| `focused-v2/`, `focused-v3/` |Each RAW3fail/64pass: worker suite-property bridge failed. Hooks under tests/conftest loaded too late for controller; hook-result replacement also did not replace the cached fixture. Original XML/reports preserved; nested stdout was not saved in those early probes. |
| `focused-v4/` |67pass after early plugin/bootstrap and proper fixture override; policy120/120 |
| `focused-v5/` |73pass: additional actual owning-function/coverage-failure and hook-cap tests; source copies/diff retained |
| `full/` |RAW trueexit1: native7 pass; Python3402pass/5fail/two warnings in790.75s, actual8 workers. Remaining standard report/memory/native-merge stages NOT reached. |
| `diagnostics/clean/`, `diagnostics/prefixed/` |SAME retained raw counter profiles copied into isolated controls: gcov-tool clean-env exit0, inherited GCOV relocation exit4/GCC ICE. No compiler/native actors invoked. |
| `focused-v6/` |Corrected73pass; final sizing122/122 lines100%; explicit inherited-GCOV regression and physical-core policy checks |
| `deadline-targeted/` |160 existing exchange/progress cases pass under worker coverage at automatic4, unchanged deadlines;13.91s. Targeted result was NOT claimed as full-load assurance. |
| `full-corrected/` |ONE bounded corrected full gate: trueexit0, native7 pass, Python3407pass/two warnings, complete report/Valgrind/native100 stages. Final source copies/diff/log/XML/start/end/exit retained. |

Initial full five failures:

1. Two old property tests exceeded unchanged Hypothesis200ms deadlines:
   `test_generated_repeat_receive_refs_are_nonexecuting` (256.98ms) and
   `test_generated_progress_identity_repeat_and_pin` (223.79ms).
2. Three new merging tests failed with gcov-tool exit4/GCC internal error under
   inherited worker GCOV relocation. The retained SAME-profile controls establish
   this tool environment mechanism; not a native DML/LMDB mechanism.

The initial CPU hook counted8 logical CPUs despite4 physical cores, overriding
xdist's usual physical-core preference. Admission now caps at physical cores when
known. The deadlines were NOT raised/disabled; both tests subsequently pass in the
160-case targeted run and corrected full workload at4. Their original exact timing
contributions (coverage/SMT contention/other load) are not separately profiled;
this does not diagnose VP-001 or earlier hosted async failures.

Initial failed combined Python data was preserved in `failed-data/`; an informative
read-only report at THAT frozen source showed9129/9129 lines100. This was not a
passed full gate or final-source report. Final policy source changed120->122
statements; final complete report is9131/9131. Do not combine/relabel source versions.
Nix temporary test directories from full invocations are not durable evidence;
primary logs/XML/suite properties, worker metrics and archived main counter/data
files remain. The first snapshot attempt omitted mkdir for one native-counter
copy target and failed; corrected custody copy completed, source/data unchanged.

The second full was deliberately bounded after a proven counter fix, CPU-policy
correction,73 focused passes and160 targeted passes, to test complete workload and
previously unreached stages. It was not retry-until-green or another automatic
baseline; no third full was launched.

## Final outcome and performance

Corrected full gate: **14m42s total**, Python phase **755.97s (12m36s)**.
Actual XML3407 cases, zero failures/errors/skips; all4 worker exits0. Native suite
properties `native_lifecycle_compile`, `native_lifecycle_baseline`, and
`native_lifecycle_interleaved` are present in actual controller XML.
Python9131/9131 statements100; native1667lines/131functions/1550branches100;
binding memory +141 CLI Valgrind processes pass, unchanged suppression policy.
Two original runpy warnings and preexisting lcov dependency/unused-pattern warnings
remain. Mull not requested; no installed computational story/fixture/image run.

The prior serial coverage full gate took40m48s; this is about2.8x faster end-to-end.
That comparison includes extra support tests and is not a pure fixed-workload CPU
scaling benchmark. Automatic4 worker sampled tree peaks:238.2/114.2/126.3/243.8MiB,
zero probe errors. One-GiB allowance is over4x the largest observed sampled peak;
it remains a conservative initial profile, not a proof of maximum memory usage.
The initial8-worker run had one sampling error and peak356.7MiB; preserved separately.

**Five-minute target NOT met.** Longest final coverage testcase totals:

- Retained selected ancestry/depth boundary:513.696s (**8m34s**).
- Outer reuse/swapped inner provenance/default pinning:296.219s (**4m56s**).
- Adapter response reuse guard:70.823s including setup.
- Reuse-history guard:63.294s including setup.

More workers cannot split the single8m34s case. Further meaningful optimization
must reduce validation/history work, not simply increase parallelism. Fast/slow
modes remain the user's conditional fallback, NOT an implemented/selected split.

## Stop and ownership

Ten implementation paths changed/added; source/index remain uncommitted at55a73e9.
External Nix flake change is unversioned and evidence-retained. No commit/push
requested for this stage. Both native builds/coverage data and source remain
coordinator-owned; no live test owners or additional coding workers intended.
No automatic further suite/profile/fixture/CI retry. Remaining optimization direction
needs a bounded next plan; native19 remains PAUSED/private candidate retained,
VP-001 OPEN UNKNOWN with existing owner/conditions and no standing waiver.
