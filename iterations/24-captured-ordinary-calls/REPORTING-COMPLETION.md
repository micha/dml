# Iteration24 reporting correction and resumed validation completion

Status: **requested original+resumed stage evidence complete; independent acceptance/publication pending**.
Original `scripts/check.sh -v` stays RAW FAILED exit1, not retroactively a passing invocation.

## Immutable originals and exact reporting issue

`../dml/build/iteration24/reporting-investigation/original/` preserves182 exact artifacts:
original repo `.coverage`, relevant31 source bytes/pre=current hashes, raw full command/start/end/
stdout/stderr/exit, native Valgrind XML/log and gcda/gcno/gcov/counter/build inventories. Public
CoverageData7.14.1 READ-ONLY inventory0 found56 measured files/empty-only contexts and EXACTLY:

- `$root/HOST captured leaf entry`: test-generated ten-line bootstrap.
- `$root/HOST captured reuse entry`: test-generated ten-line bootstrap.
- `$root/isolated old event append`: isolated one-line historical test expression.

Original/archive coverage DB bytes unchanged. `inventory.json`, `origins.json` and preservation
manifest own exact measured lines/source paths/hashes/version/compile origins. No fake source
attribution or coverage-data filtering/rewrite. User explicitly approved necessary exact scaffold
exclusions for expedited reporting; coordinator reviewed and approved these THREE labels ONLY.

Owning script changes: append exactly these root-qualified labels to existing omit_patterns;
pass that SAME list explicitly to XML/HTML as report/collection. No wildcard examples/package
omission, ignore-errors, threshold reduction, runtime/helper/binding/testbehavior/deletion.
[Catalog](../../../dml/tests/coverage-exclusions.md#iteration-24-generated-host-reporting-labels)
owns no-value rationale and retained maintained-code assurance. Excluded statements are not passing
coverage. Actual canonical wrapper/logical/other example/package/meaningful guards remain measured.

Pure reporter regressions3PASS1.02s/XML/exit0: absent scaffold labels report/XMLHTML successfully,
actual maintained uncovered captured_call_session.py STILL rejects at100 with exit2; exact owning
pattern list/consistency and dataimmutability checked. No DMLjob/source arithmetic/3354 replay.

## Raw original stage accounting and evidence correction

Original full: native7PASS under initial native Valgrind; pytest stdout3354PASS/2warnings/2843.80s;
coverage report fails NoSource/trueexit1. Python pytest JUnit is **ABSENT**, not invented/reconstructed.
The earlier message asserting retained PythonJUnit was unsupported and is explicitly corrected.
Preserved PythoncoverageXML timestamp2026-11-02T18:26:59Z predates this full and is stale, not its
report. Native testlog-valgrind.junit.xml is actual2026-11-03T03:30:29Z evidence. BindingValgrind/
CLI/PythonXMLHTML/lcovthreshold stages were unreached in RAW original. Mull -m was NOT requested,
not a failed or skipped requested mutation gate. Communication3345 was a typo; primary count3354.

## ONCE resumed/combined stages, no second full replay

`reporting-investigation/resumed/` owns source/script-diff/derived commands/counter-before/true
command/start/end/stdout/stderr/exit0, frozenDB COPY and report artifacts. SAME DML_BIN compiled
build/check; no mesonwipe/build/reset/coverageerase/pytest/installedfixture/reader repeat. Remaining
binding/CLI/lcov/remove/genhtml/native-threshold commands derived exactly from owning script, with
only approved Python source-label exclusions. Original snapshots/counters/source provenance retained.

- Python8962 retained statements/0missing/100%; XML+HTML generated from frozen full data COPY.
  These are coverage reports, NOT Python pytest JUnit. Every maintained example/package retained.
- Binding Valgrind0errors; definite/indirect/possible loss0. Existing documented CPython runtime
  suppressions/reachable blocks retained; not a whole-process/no-runtime-allocation claim.
- Native CLI allocation cleanup141 Valgrind processes pass, unchanged workload/limits.
- Native lcov/genhtml/threshold:11sourcefiles,1667/1667lines,131/131functions,1550/1550branches100%.
  Standard dependency removals/markers unchanged. LMDB inconsistent-block and unused-pattern WARNINGS
  preserved, not silenced/new ignore policy or native/runtime diagnosis.

This is truthful **resumed/combined completion evidence**, not originalcheck.shpass/platformCI or
independently executed validation. No further tests/full/story needed before risk-based independent
focused/SAME NONEXECUTING review. Corrected installed10Q8T5LOCAL14getter/SAME reader and first RAW
activation1Q1T1getter zero-leaf failure remain separate; captured helper/source identities unchanged.
GHAoff/NOTRUN/releaseuntouched/native19PAUSED/VP001OPENUNKNOWN/no older diagnosis/standing waiver.
