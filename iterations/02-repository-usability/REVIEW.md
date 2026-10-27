# Iteration 2 coordinator review

Status: independent implementation review and final standard validation complete;
no outstanding functional blocker for the bounded iteration. Final documentation
reconciliation is recorded below. This is acceptance of the prototype's documented
scope, not production-readiness or untested-platform certification.

## Authorization and delegation

The user approved the usability proposal and explicitly requested implementation
by the existing agent in window 2, in a new Pi session, with coordinator monitoring,
independent review, feedback and fixes until satisfactory. No commit, push, package
publication, additional workers or later feature turn was authorized.

The coordinator reused `dml-design:2` (agent pane `%215`), issued `/new`, and verified
that Pi reported a new session. No tmux session was created. The implementation
session is named `dml-iteration2-implementation`; session ID is
`01a17bee-6bb6-72d3-bb83-c3e1cecf057b`. The complete handoff prompt was delivered
and the agent began reading machine/project instructions and iteration documents.

At delegation the implementation checkout was clean at `06bf66e`. Existing design
changes were preserved. The coordinator updated planning authorization statements;
implementation source remains owned by the window-2 agent. Review findings will
be sent back rather than fixed concurrently by the coordinator.

## Independent review plan

- Inspect the actual diff, not only the agent's summary or test counts.
- Check native linkage, value/type boundaries, copied ownership, context/handle
  lifecycle, fail-closed writes and thread restrictions.
- Check CLI selectors, traversal/deduplication/limits, previews, locale/JSON/terminal
  escaping, error streams and inspection-only state behavior.
- Check core reuse, package self-containment, installed artifact provenance and
  the single native CLI forwarding seam.
- Exercise adversarial API/CLI cases in coordinator-owned scratch, after agreeing
  a validation pause so shared build wipes cannot race.
- Review standard-gate populations, exclusions, memory/failure/mutation accounting,
  as-built contracts and claimed platform evidence.
- Send material findings to the agent, verify regressions/fixes, rerun final checks
  as appropriate, and report completion only after acceptance is supported.

## Early review feedback

These findings were sent while implementation continued; fixes and final evidence
remain pending, so this is not a defect claim about a completed delivery.

1. **Factory bypass:** exported `Transaction(owner, write)` initially bypassed
   repository thread/single-active checks and active registration. Requested
   factory-only creation or equivalent enforced policy and regression coverage.
2. **Explicit lifecycle endings:** repository context exit initially rejected an
   already explicitly closed repository; transaction abort checked a closed owner
   before honoring ended/idempotent state. Requested coherent repeated cleanup
   and preservation of original exceptions.
3. **Finalizer thread safety:** native capsule destructors initially ended handles
   without creating-thread checks. Requested safe handling of last-reference
   destruction on another thread, not only method-level rejection tests.
4. **Human presentation:** the initial non-JSON CLI added a title to compact one-line
   JSON. Requested usable human metadata/rows/layout, while retaining JSON contract.
5. **Terminal controls:** requested escaping Unicode C1 controls in human previews,
   in addition to ASCII C0/DEL, with regression inputs such as U+0085/U+009B.
6. **Wheel targeting:** an initial wheel was tagged cp313-abi3 despite declared
   Python >=3.8 support. Requested explicit ABI-tag configuration review and honest
   separation of declared compatibility from actual platform/runtime evidence.

The agent reported the baseline passing default check with 7 C executables under
Valgrind and 86 Python tests. This is agent-reported baseline evidence, not a
coordinator rerun or Iteration 2 completion result.

The coordinator approved bounded dependency bootstrap only within newly created
project-local packaging scratch for the already-authorized local installation
validation. No global/system or shared tooling changes were approved.

## Independent coordinator checks

After the agent explicitly confirmed a shared-build/runtime-code pause, the
coordinator ran a separate script against the real freshly built extension at
`../dml/build/check/_core.abi3.so`, with only coordinator-owned temporary repositories.
Command from `../dml`:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c python3 /tmp/dml-iteration2-coordinator-probes.py
```

Exit **0**, **30 independent assertions**. The script starts a separate producing
process, then checks CLI/Python inspection of both historical snapshots, a hex-shaped
ref versus explicit commit selector, fork/shared-ancestor all-parent traversal at
limits 1/2/3/4/5/100, 112-entry default/exact truncation, an 80-code-point non-BMP
preview boundary, escaped controls/full JSON values, extreme I64/nonfinite F64,
unchanged encoded bytes, caught-conversion-error rollback including prior ref movement,
nonpoisoning failed reads, creating-thread rejection, factory-only transactions,
and idempotent cleanup after explicit closure. Diagnostics:
`/tmp/dml-iteration2-coordinator-probes.log`. Script/log are session-local, not
committed evidence dependencies; maintained regressions remain in implementation tests.

The coordinator also created an independent `/tmp/dml-i2-review-install.*` venv,
installed both agent-built wheels with `--no-index --no-deps`, ran the public history
example outside the checkout and inspected `main` through its installed `dml`.
Exit **0**; snapshot root datum is 43, and module/extension paths point into that
venv's `site-packages`, not source/build paths. Diagnostic:
`/tmp/dml-i2-review-install.log`. This is local Linux/Python 3.13 install evidence,
not portability or earlier-runtime evidence. Wheel contents were inspected: the
real extension, native executable, package sources/types and metadata; no private
fault extension, static library or C headers are packaged.

The shared-build pause was released after these probes. No core codec/storage
source or public C header diff was found. A temporary documentation EOF whitespace
issue was sent back for correction before final validation.

## Mutation review feedback

Initial agent reports had CLI 11/38 survivors (71%) and binding 1/13 survivors (92%).
These are not green mutation gates. The reported CLI operators exceeded the intended
configuration; the coordinator flagged the unexported `MULL_CONFIG` assignment and
requested actual-scope accounting or an exported-config rerun. The coordinator also
requested stronger tests for output-failure detail and spurious unraisable output
on normal ResourceWarning abandonment, plus meaningful allocation-fault targets
where practical. Equivalent formatting/allocation choices and astronomical-size
boundaries should be distinguished from useful missing assertions.

## Final follow-up and independent standard validation

The agent fixed the factory/lifecycle/presentation/control-escaping issues, added
native deferred owner-thread cleanup with an explicit unsupported abandonment
boundary, and fixed a real warning-as-error destructor crash exposed by the
adversarial lifetime tests. Passing the dying capsule to `PyErr_WriteUnraisable`
could re-enter its destructor; using a non-dying context fixes that regression.
The release selector was restored to its existing interpreter matrix rather than
making unverified oldest-runtime changes.

Mutation review also exposed useful assurance gaps: >1024-byte JSON output growth,
False/empty collection/tree inputs, and exact numeric decode values in the private
fault fixture. The agent added success/value regressions and large-output native
Valgrind runs; the final CLI memory workload now covers 60 processes. These are
additional tests, not new runtime capabilities or exclusions.

After a second explicitly acknowledged final shared-build/runtime pause, the
coordinator independently ran, from `../dml`:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

**Exit 0**, diagnostic `/tmp/dml-iteration2-coordinator-final-check.log`:

- All **7 C executables** pass under Valgrind.
- **249 Python tests** pass; production Python coverage **399/399 statements**.
- Retained C coverage **1555/1555 lines**, **125/125 functions**,
  **1409/1409 branch outcomes**, all 100% under the unchanged default gate.
- The real binding ownership/failure workload passes, with **0 unsuppressed memory
  errors**. Precisely matched CPython runtime leak suppressions remain visible;
  the process is not claimed allocation-free.
- **60 native CLI Valgrind processes** pass, including allocation-failure sweeps
  and large full-output growth boundaries, with zero errors and no bytes at exit.

This is a coordinator rerun, not substituted agent/CI/informational evidence.
No shared-build race occurred. Both checkout whitespace checks pass afterward.
The implementation core codec/storage sources and public C headers remain unchanged.

## Final assessment

**Satisfactory within Iteration 2's authorized scope.** The Python API and
inspection-only CLI share the real C foundation; fresh-process history, immutable
bytes, atomic rollback, lifecycle boundaries, installed artifacts and final standard
checks have independent evidence. No outstanding functional blocker remains from
the coordinator's review. The agent was instructed to stop implementation and
complete delivery notes; no commit/push/publication or later feature work occurred.

Qualifications retained, not waived or hidden:

- Local Linux/Python 3.13 evidence only; no new Windows/macOS/earlier-runtime or
  GitHub Actions run. Local wheel tags and declarations are not runtime coverage.
- Mutation diagnostics have survivors and are not green mutation gates. Remaining
  equivalent/parser/reallocation choices, impractical bounds and unexercised
  diagnostic/memory mutants need accurate classification in delivery notes; no
  universal test-effectiveness claim follows from 100% retained coverage.
- Native cleanup is supported on the creating thread. Foreign-thread last-owner
  abandonment deliberately warns/leaves resources until process exit; it is
  unsupported misuse, not leak-free finalization evidence.
- Dirty-tree source-archive staging proves a bounded self-contained source-to-wheel
  route, not that normal VCS sdist creation captured uncommitted edits.
- No large-history benchmarks, OS-read-only repository open, new concurrency policy,
  execution, remotes or resource lifecycle work is claimed.

Final delivery notes were read completely and reconciled with the implementation,
independent results, source state and documented limits. README/discussion now
record completion and a user-review resume point; design/handoff are marked as
completed planning context rather than instructions to restart. Worker handoff
explicitly states work is stopped. The coordinator ended the Pi process after
completion to prevent delayed original prompt paragraphs from reopening work;
only read-only preflight occurred during that brief replay. No new tmux session
was created, and the saved implementation Pi session remains resumable.

Final whitespace/local-link/source-status checks pass. Implementation HEAD remains
`06bf66e`; both Git indexes are empty; old `docs/spec/` has no diff. All turn changes
remain uncommitted for user review.

## Authorized publication follow-up

The user subsequently authorized commit/push and exact-SHA Actions verification.
The reviewed implementation was published as `ee0327f`; five Unix jobs passed,
but Windows exposed a test-extension selector that picked a linker import library.
Coordinator fix `d9a554c` added a suffix-aware shared selector and five regressions.
Windows then ran the suite and exposed three locale-decoding fixture failures and
two POSIX fake-compiler fixture failures. Coordinator fix `e253249` made UTF-8
protocol decoding explicit and supplied a native CMD compiler fixture on Windows,
with a forced-ASCII fallback regression. No production API/core/CLI change, disabled
test, lowered threshold, new suppression or new platform skip was needed.

Fresh final local `scripts/check.sh -v` exits 0: 7 C executables, 255 Python tests,
Python 399/399, retained C 1555/1555 lines, 125/125 functions, 1409/1409 outcomes,
zero unsuppressed binding errors and 60 passing CLI Valgrind processes.
[Final CI run 40467554833](https://github.com/micha/dml/actions/runs/40467554833)
for exact SHA `e253249eca70ad588d918d321a54a1413447b8a0` passes all six jobs.
Remote master matches that SHA; implementation working tree/index are clean.
[Publication notes](RESULTS.md#publication-checkpoint) preserve both failed runs,
fixes, per-platform test/skipped populations and memory/packaging qualifications.

The previous no-CI/uncommitted limits above describe the original review phase.
Functional CI coverage now spans the existing platform matrix; installed wheel,
release and earlier-runtime coverage are not inferred from that run. Informational
`-c` CI and local default `-v` remain separate evidence. Design notes remain local
and uncommitted; no tags, releases, package publication or further feature turn.
