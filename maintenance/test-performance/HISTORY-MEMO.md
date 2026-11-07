# History-validation memoization — second optimization stage

Status: locally implemented/validated, **uncommitted/unpublished**. The user said
“good work. proceed” after the [parallel coverage results](PARALLEL-COVERAGE.md)
and offer to target the remaining slow ancestry/history-validation case. Scope:
example-level validation/read reuse, unchanged original assertions/depth/provenance
checks; no low-level repository API/native code, native19, CI or publication work.
Five-minute full-suite target remains open; no fast/slow split introduced.

## Measured bottleneck

Parent HEAD remains local55a73e9; prior coverage tooling is also uncommitted.
Evidence root (relative to repository root):
`../dml/build/history-performance/20261105T173119Z/`.
Before this stage, accepted data/reports/source were copied under `before/`.
Profiling ONLY the original ancestry test passed:321753605 function calls,
4164 builtin Inspector/retained-history scans and7470894 native get_record calls.
Reachability cost204.9s of430.6s profiled wall time; transfer export1938calls/112.3s,
public S inspect377calls/88.7s, public prepare708calls/38.5s (nested times overlap).
Profiling overhead means these are not like-for-like benchmark timings.

## Implementation and authority preservation

Additional implementation paths: `examples/captured_calls.py`,
`tests/python/test_captured_call_read_memo.py`, and
`docs/captured-ordinary-calls.md`. Prior ten tooling paths remain; thirteen total.
The owning [example documentation](../../../dml/docs/captured-ordinary-calls.md)
records inspection-local behavior. Diagram/native/public repository code unchanged.

Within ONE synchronous, source-read-only inspection:

- Memoize successful complete snapshot export CHECKS, not large bundle payloads;
  public preparation/selection validation uses pinned source IDs and exact dimensions.
  API function identity and live transfer-limit values are part of the keys.
- Share the PUBLIC builtin Inspector only for the SAME actual transaction and
  commit. No constructor bypass, supplied retained flags, active/seen reset or
  cross-transaction semantic inspector reuse. A reentrant active walk gets a
  distinct normal Inspector. Semantic union/budgets remain enforced.
- An example-private readonly view shares copied immutable public getter results
  by resolved repository path, method identity and exact immutable arguments.
  Mutable refs are never cached. Every warm hit performs an uncached public ref
  lookup to check actual transaction owner/thread/ended state; its value is ignored,
  not source authority. Underlying abort/closed/wrong-thread errors still propagate.
- No writer/mutator is exposed by the view and no native handle stays active beyond
  its original short context. Copied values, not live reader ownership, span scopes.
  Entry count and byte-payload allowances bound caching, not acceptance: when full,
  ordinary public reads continue. Errors are not cached. Invalid key types delegate
  to original API validation. Changed getter implementations use different keys.
- Recursive proof keys retain exact depth and now include live semantic/authority/
  transfer bounds, so tightening a bound cannot consume an earlier permissive proof.
- New top-level inspection always starts fresh. No durable/global repository cache,
  alternative role codec, implicit graph access, source execution or computational
  reuse policy. Cooperative immutable source during the synchronous inspection is
  the same assumption as the original proof scope, not a sandbox guarantee.

Existing implementation/runtime helper APIs and original slow-test bodies are
unchanged. Example `outer_sources()` captures these revised profile bytes for NEW
closures; old versus new captured binding bytes must not be silently conflated.
No installed story was rerun or claimed to use these new bytes.

Ten new tests cover fresh-call/repository separation, immutable read reuse,
closed scope/native abort/wrong thread, uncached mutable refs, failed/invalid reads,
state-probe error propagation, changed native getters/limits, entry/payload caps,
inspector active/seen preservation/reentrancy, typed records/lookup, and changed
recursive semantic/authority bounds. No original test/timeout/exclusion changed.

## Validation chronology

| Evidence | Actual result |
| --- | --- |
| `profile/` |1pass, cProfile of original ancestry; before-code copy retained |
| `memo-v1/` |2 original tests pass, no Python coverage: ancestry156.29s/reuse95.30s; successful-check/inspector-sharing draft |
| `memo-v2/` |2 original tests pass, no Python coverage: ancestry86.36s/reuse61.36s after readonly copied-read view |
| `focused-v3/` |259 captured-call cases pass under SERIAL coverage, helper846/846 lines100; ancestry133.09s/reuse92.77s;574.80s total |
| `unit-v4/` |13 guard/proof tests pass after typed-payload cache allowance refinement |
| `unit-v5/` |14 guard/proof tests pass after recursive bound-key strengthening; final code copies retained |
| `full/` |ONE final adaptive standard -v gate, auto4: trueexit0,3417Pythonpass/two warnings, all remaining coverage/memory/native stages pass |

Intermediate source copies remain distinct: focused-v3 preceded two final
bounded-memory/key refinements; the final full gate exercises CURRENT sources.
No failed test run occurred in this stage. An informative pstats regex command
emitted a Python invalid-escape SyntaxWarning; not a test failure. No second full
or additional actor/native-investigation probes were launched.

## Final result and target

- Python coverage suite: **597.95s (9m58s)**.
- Full build/native/Python coverage/Valgrind/report gate: **713s (11m53s)**.
- Actual XML3417 cases, zero failures/errors/skips; four worker exits0.
- Python9194/9194 lines100; native1667lines/131functions/1550branches100.
  Binding memory and141 CLI Valgrind processes pass, thresholds unchanged.
- Actual three native lifecycle suite properties remain in controller XML.
  Native standard-session evidence is not original hosted attribution/VP-001 diagnosis.
- Sampled worker tree peaks170.2–246.6MiB; one sampling error, not a test failure.
  Existing1GiB admission allowance unchanged; sampling is not a maximum/OOM guarantee.
- Original two runpy and preexisting lcov dependency/unused-pattern warnings remain.
  Mull not requested. CI/no remote/platform assurance; dependencies/provisioning
  limitations in the previous report still apply.

Like-for-like adaptive COVERED full-run testcase totals:

| Original test | Before | After |
| --- | ---: | ---: |
| Selected ancestry/depth boundary |513.696s|222.017s (**3m42s**, about57% less) |
| Outer reuse/swapped-input provenance/default pinning |296.219s|152.928s (**2m33s**, about48% less) |

Whole-gate14m42s->11m53s saves2m49s, about19%. The lower wall-time gain shows that
other modules now account for much of the suite. **Five-minute target NOT met**;
optimizing only this example is insufficient. Next candidate is profiling shared
read/reachability/transfer validation across the remaining modules. Any low-level
repository API/native/lifetime change needs its own scope review BEFORE editing.
Fast/slow modes remain conditional fallback, not an approved test partition.

Source/index remain uncommitted at55a73e9. No commit/push requested for this stage;
no CI/workflow/service/image/cloud/release changes. Source/both builds/evidence
coordinator-owned; test activity stopped. Native19 PAUSED/private candidate retained,
VP-001 OPEN UNKNOWN/owner/conditions/no standing waiver remain.
