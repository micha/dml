# Frozen fixture setup experiment

Status: locally implemented and checked, **uncommitted / not pushed**. Five-minute
full-suite goal **NOT met**. The user said “go ahead and give it a try” after the
offer to reduce redundant test setup before expanding runtime/API scope.

## Scope and preserved assurance

Nine additional implementation paths atop the previous thirteen at local DML
HEAD55a73e9: six existing test modules (`test_recorded_maps`, `test_datum_reuse`,
`test_recorded_map_atomicity`, `test_exchange`, `test_captured_call_profiles`,
`test_captured_call_reuse_guards`) and three new modules (`worker_history_seed`,
`test_worker_history_seed`, `test_history_seed_isolation`). Twenty-two paths total.

- Captured-call frozen/history seeds are reused within a pytest worker/session.
  Imported fixtures have distinct FixtureDefs even at session scope; a config-owned
  stash shares the successfully completed builder result across those definitions.
  Failures are not cached; configs/builders have distinct keys. No persistent cache.
- Recorded-map metadata and one REAL successful/reaped producer seed per worker are
  exported as pinned public transfer bundles. Each case retains its OWN new repository
  and explicit refs, restored via public import/create_ref. No native database/lock
  file copying, low-level API/native/lifetime change or workspace resume.
- Successful-producer setup now uses retained real evidence, not a newly launched
  equivalent child for every metadata/read negative. Dedicated fresh execution tests
  and computation inside existing test bodies remain unchanged. Saved child PID/exit/
  reaping refers to the actual seed producer, NOT a new per-test launch.
- Runtime package copying factored into a callable test helper; existing function-scoped
  runtime/environment fixture remains. Source metadata dictionaries handed to case
  fixtures are copied. Case writes do not change seed bundles or another case's refs.
- Four new tests cover store/ref/public-authority isolation, exact export/native identity,
  actual producer evidence, config/builder separation and failure-not-cached behavior.
  All existing test-function ASTs equal HEAD (assertions and decorators included).

No assertion removal, semantic/depth/transfer budget change, test/runtime deadline,
coverage scope/exclusion/100 threshold change, fast/slow split, runtime optimization,
workflow/CI/default-parallel change, install, commit or push.

## Evidence and raw failures

Root: `../dml/build/fixture-performance/20261106T032148Z/`.

1. `focused-v1`: RAW exit1, 34pass/93setupERROR in8.79s. New seed fixtures were not
   imported into consuming modules; original bytes/log/XML retained.
2. Corrected explicit dependency imports, `focused-v2`: exit0,127pass in33.66s,
   no Python coverage, original assertions unchanged.
3. `shared-focused`: exit0,110pass/auto4 in45.07s, no Python coverage. Setup timings
   revealed session scope alone still duplicates builders across imported FixtureDefs;
   this weaker version is NOT claimed to share once per worker.
4. Config-stash correction and four guards, `shared-corrected`: exit0,239pass/auto4
   in54.30s, no Python coverage; source copies/XML/worker reports retained. All six
   existing modules' test-function ASTs verified exact HEAD equality.
5. ONE ordinary resource-aware parallel gate, `full`: TRUEexit0,597s overall
   (**9m57s**);3421Pythonpass/two original runpy warnings in582.87s (**9m43s**).
   Native7/memory gates pass; Python9194/9194 and native1667lines/131functions/
   1550branches100. Valgrind NOT enabled: command intentionally omitted `-v` to
   match the user's ordinary command profile. Existing lcov warnings retained.

Full command:

```sh
nix develop /work/repos/micha/dml-build-tools --offline --command \
  env DML_TEST_WORKERS=auto DML_TEST_REPORT_DIR="$out/worker-reports" \
  bash scripts/check.sh
```

Logs/actual exit/start/end/data/source copies/coverage reports/worker RSS reports
retained. Full run did NOT request pytest JUnit/durations; PythonJUnit ABSENT and
no new full per-module timing breakdown available. A subsequent read-only attempt
expected a nonexistent XML and failed StopIteration; not reconstructed as actual.
Earlier focused XML exists; full Python/native completion and coverage rely on actual
standard-command logs/reports, not an invented full XML. First shared-focused report
used default worker-report destination; corrected/full use dedicated destinations.

## What the experiment established

The full Python phase is only about2.5% faster than our preceding597.95s covered
phase; prior overall713s included optional `-v` checks and is NOT a like-for-like
ordinary-gate speedup. The user's8m35.832s ordinary parallel timing (no success/
coverage logs supplied) is faster than this run. Machine/run variability and missing
new per-case durations mean **no convincing whole-suite improvement is established**.
Focused setup sharing passes; no five-minute success or hosted-platform guarantee.
Do not repeat the whole suite automatically to obtain a preferred timing.

Next candidate: bounded sampling/profiling of remaining shared reachability/transfer
reads, or review whether this fixture complexity is worth keeping. Low-level
repository/native API edits need separate scope review. Fast/slow modes remain a
conditional fallback, not selected. Work stopped after this finite experiment;
source/both builds/evidence coordinator-owned. GHA disabled/native19 PAUSED/private
candidate retained/VP-001 OPEN UNKNOWN/owner/conditions remain, no old diagnosis/waiver.
