# Iteration 3 coordinator review

Status: implementation review, authorized commit/push and independent final
exact-SHA CI verification are complete. The bounded turn is accepted and stopped.
Worker checks and limitations are owned by [RESULTS.md](RESULTS.md). This report
owns independent coordinator inspection/probes, feedback and acceptance.

## Scope and source state

The user approved the plan and authorized the existing window-2 Pi worker to
implement, with coordinator review/fixes, then commit/push after acceptance and
CI verification/fixes. See [COORDINATION.md](COORDINATION.md).

Review inspected uncommitted implementation over `e253249`, including codec/input/
view changes, direct-reference validation/scoped lookup, linked Python conversion
and descriptions, native CLI traversal/root handling, tests/example, coverage
reassessment and as-built documentation. No execution/reuse/remote/resource/observer
feature, old-spec change, migration, version bump or packaging redesign was found.

The worker explicitly paused runtime/test edits and released `build/check` before
independent probes/default validation. No additional agent was launched. Coordinator
made no implementation edits; findings were sent to the worker for fixes.

## Feedback and resolution

1. Shared named-object diagnostics initially labeled new DAG failures as trees.
   Worker added type-specific diagnostics and malformed/name/allocation assertions,
   and reassessed the shared existing exclusion invariants.
2. A public Hypothesis test assumed generated names could never equal `root` or
   `absent`. Worker added an explicit example, a guaranteed-missing name and a
   conditional missing-root assertion. The deterministic non-reserved-root case
   remains. This was a potential test/CI flake, not a production defect.
3. Untracked `test-fault-data-*` directories appeared during mutation diagnostics.
   Before staging, worker confirmed their PID names against its mutation profile
   files, checked that only its test-owned data was present, and removed those
   scratch directories. None were committed. This was publication hygiene, not a
   reason to change production behavior or ignore tests.

No outstanding functional defect was found after the first two corrections.

## Independent probes

Session-local `/tmp/dml-iteration3-coordinator-probe.py` directly loads current
Python sources against the real `build/check` extension and calls the native CLI.
Executed in the existing tools shell, exit 0: **49 independent checks pass**.
Log: `/tmp/dml-iteration3-coordinator-probe.log`.

Checks include canonical binding order and an independent packed DAG byte oracle,
caller-container copying/read-only descriptions, explicit single-scope lookup,
root aliases, nonliteral roots, shared node/DAG expansion, exact and over-limit
prefixes, escaped/truncated non-BMP previews, saved historical bytes, child commit
publication, lookup not poisoning writes, and native/conversion/duplicate mutation
failure rolling back both prior values and ref movement. These finite checks are
not a global integrity, computational-causality or production-safety proof.

## Independent standard validation

From `../dml`:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Fresh coordinator run exits **0**. Log:
`/tmp/dml-iteration3-coordinator-check.log`.

- **7 C executables** under Valgrind and **316 Python tests** pass.
- Python **469/469 statements**, retained C **1681/1681 lines**,
  **132/132 functions**, **1562/1562 outcomes** (100%). Thresholds unchanged.
- Expanded binding workload has zero unsuppressed memory errors/leaks, with narrow
  existing CPython runtime suppressions. Unsupported foreign-last-owner abandonment
  remains excluded from supported leak-free lifetime claims.
- **141 native CLI Valgrind processes** pass.

Existing precise exclusions are reassessed, not silently called tested behavior.
Worker marker-free population, mutation survivor reports and platform/runtime-only
comparison limitations remain qualified in RESULTS; no coordinator mutation rerun
or new sanitizer guarantee is claimed. CI informational `-c` is not this default
percentage/memory gate.

## Independent installed workflow

Created a separate fresh `/tmp/dml-iteration3-review-install.*` venv and installed
worker-built current wheels offline with `--no-index --no-deps`, using the existing
Iteration 2 packaging-tools interpreter. Ran from `/tmp` with PYTHONPATH unset.
An installed extension/console workflow and separate reader verify scoped lookup,
I64 max value, saved record bytes, nested snapshot root and exact four-record walk
without truncation. Paths assert venv `site-packages`. Exit 0.

Log: `/tmp/dml-iteration3-coordinator-install.log`. Initial invocation mistakenly
used the intentionally pip-less installed interpreter as an installer and failed
`No module named pip`; retry uses the correct existing packaging-tools interpreter.
This tooling-selection failure is preserved, not a product defect or new bootstrap.
No global/system package installation occurred.

This is local CPython 3.13/Linux x86_64 wheel evidence, not earlier-runtime, other
platform, manylinux, new sdist or release verification.

## Documentation and acceptance

Both whitespace checks and independent changed-Markdown local target/anchor checks
pass. API/CLI/core contracts distinguish containment from computational causality,
required root from named bindings, node versus DAG targets, direct versus transitive
validation and presentation limits versus memory/read bounds. The changed DAG shape
is explicitly incompatible without pre-1.0 migrations.

The implementation is satisfactory for the approved bounded turn. The worker was
released to perform authorized focused commit/push and exact-SHA CI monitoring.
Final verification follows. Design notes remain local/uncommitted.

## Independent publication and final CI verification

The worker inspected/staged only the reviewed 31-file slice and committed/pushed
[`9b8fb7176e31186621dd5a4c26adadec4d76bc1e`](https://github.com/micha/dml/commit/9b8fb7176e31186621dd5a4c26adadec4d76bc1e)
(`Add composable DAGs and scoped named-node lookup`). Coordinator independently
inspected the committed file list/stat, verified local HEAD and remote
`refs/heads/master` match, and confirmed the implementation worktree/index is clean.
No CI follow-up fix was needed: the first published run passed.

[CI run 40474598485](https://github.com/micha/dml/actions/runs/40474598485) completes
**success** for that exact SHA. Coordinator `gh run watch --exit-status` exits 0;
final run JSON, exact head SHA, all six completed jobs, full completed logs and the
run list for that SHA were independently checked. That run is the only automatic
workflow for the SHA. Release Python is tag/manual-only and was not triggered.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598300) | Success | 7 | 316 passed |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598283) | Success | 7 | 316 passed |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598202) | Success | 7 | 312 passed, 4 skipped |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598408) | Success | 7 | 312 passed, 4 skipped |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598472) | Success | 7 | 311 passed, 5 skipped |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40474598485/job/122089598048) | Success | 7 | 316 passed |

Four existing skips concern absent `/dev/full`; Windows also skips the existing
Unix closed-pipe test. Portable private output-failure tests remain enabled. No
new skips or weaker thresholds were introduced. The runner's macOS arm64 capacity
annotation is informational; the job completed successfully.

CI is functional platform/build evidence, not installed wheel or release proof.
Its strict-Linux job remains informational `-c`, distinct from local default `-v`
coverage/memory acceptance. Mutation survivors, precise exclusions, runtime memory
suppressions, direct-validation/presentation-bound limits and unsupported finalizer
abandonment remain qualified; CI success does not remove them.

Session-local diagnostics: `/tmp/dml-iteration3-coordinator-actions-watch.log`,
`/tmp/dml-iteration3-coordinator-ci.{json,log}`. No remote creation, force push,
release/tag, package publication, system change, additional worker or later feature
turn occurred. Final implementation/CI acceptance is complete; worker was instructed
to finalize RESULTS and stop.
