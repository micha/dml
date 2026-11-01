# Proportionate validation for the design spiral

Current delivery: **COMPLETE AND STOPPED at published `4a053340`, accepted WITH
[exception VP-001](EXCEPTION-VP-001.md)**. Raw CI41098299553 attempt1 FAILED/five
successful jobs/one Macarm oldasync failure UNKNOWN; follow-up OPEN. See
[RESULTS](RESULTS.md), [REVIEW](REVIEW.md) and [COORDINATION](COORDINATION.md).
Initial authorization/plan below preserves chronology, not worker/runtime/CI restart
permission. No new feature or automatic follow-up investigation authorized.

Status: **authorized bounded maintenance turn**. The user agreed to make focused
behavioral checks and concrete acceptance primary, keep CI for portability/regression,
and explicitly handle inherited failures. They authorized planning, fresh-session
implementation by the existing window-2 agent, coordinator review, then worker
commit/normal push/CI fixes. Coordinator may revise this plan using judgment based on
CI evidence; revisions must be recorded, not silently change what a failure means.
This is maintenance, not Iteration16 or a new DML capability.

## Evidence and problem

DML starts clean at published `664a87085961b5e24d2b709e057e4a28fe724088`.
Iteration15's final six-job CI passed. Its first run found a real Python3.12
**test-controller** portability bug; an unchanged Windows caller-story also failed,
then passed on a different SHA without a demonstrated cause/fix. See
[Iteration15 review](../../iterations/15-intent-reuse-defaults/REVIEW.md).

Existing CI runs the full five-platform test matrix plus Linux `check.sh -c`.
`check.sh -v` retains local full coverage and memory checks; CI-c reports coverage
without percentage enforcement. CI is useful complementary evidence, not proof of
scientific correctness/full environment capture or a replacement for real acceptance.
Repeated worker/coordinator full runs, redundant source/log inventories and rerunning
unchanged fixtures after docs/harness edits have become disproportionate.

## Selected bounded implementation

1. Add one concise owning `../dml/docs/validation-policy.md` for development acceptance,
   validation selection, CI triage, explicit exception records and final reporting.
   Link it from implementation AGENTS/README; align design AGENTS for future handoffs.
   Historical iteration contracts/results remain history, not rewritten failures.
2. Keep all current CI platforms/full tests, runner/dependency settings, coverage/memory
   thresholds, skips/exclusions and existing outer/runtime budgets. Do NOT make jobs
   green with continue-on-error, blanket xfail/skip, automatic retries or swallowed exits.
   Do NOT change branch protections/release workflows/account settings.
3. Add small, practical CI failure evidence: pytest JUnit XML for each matrix job and
   upload on success/failure (existing upload-artifact action version), with stable
   platform-specific artifact names. Include strict-Linux results using existing pytest
   configuration/environment if feasible WITHOUT expanding check.sh into a framework.
   Preserve actual pytest/build/report exit codes. Do not upload whole temp repositories,
   environment/credentials, Docker state or research artifacts. Missing report after an
   early crash/cancellation is absence/unknown, never passing tests.
4. Add focused default-safe tests for the changed workflow/reporting contract. Exercise
   real pytest passing/failing/collection-error reports and original nonzero status,
   not only search for strings in YAML. Keep dependency-free tests where feasible;
   do not introduce a generic CI classifier/quarantine service or policy engine.

Exact file/helper spellings are refinable. Prefer workflow flags and pytest's existing
JUnit support over new execution wrappers. If evidence shows another approach provides
substantially more value, propose it with costs/limits for coordinator review.

## Development acceptance policy to implement

### Primary, chosen before execution

Record a short change-validation map: changed behavior/invariants, focused tests,
concrete acceptance workflow (if needed), unchanged areas and why extra runs add value.
Use relevant negative tests; mocks do not replace actual transport/execution when those
are changed. Documentation/CI-only turns require actual workflow/reporting checks,
not resurrecting unrelated SSH/Floci jobs or computational images.

Run the unchanged complete standard gate once on the worker's final relevant sources
when executable validation/runtime/build/test tooling changes. Preserve existing local
coverage/memory criteria; proportionate means reducing duplicate executions, not their
thresholds. A fresh pre-edit full baseline is optional when a recent exact published
pass and focused baseline suffice; run it if it would distinguish a meaningful problem.
Coordinator independently reviews changes and runs focused tests/acceptance appropriate
to risk. A second full suite is NOT automatically required. Revalidate affected behavior
following substantive fixes; a documentation/exception wording change alone does not
invalidate unchanged runtime/installed evidence or demand a new full/fixture run.

### CI as complementary portability/regression evidence

After accepted focused commit/normal push, inspect the actual final SHA's complete CI
outcome. Newly introduced/attributable failures block and require fixes/regressions.
Unknown/new failures cannot be dismissed merely because the test file is unchanged.
An unchanged test may expose a regression in changed code or environment. Diagnose
within a bounded effort, using primary logs/JUnit/diagnostics before speculative edits.

An **explicit acceptance exception** can be made for an evidenced inherited failure,
with coordinator approval and a named follow-up investigation. Record exact SHA/run/
job/test/failure signature, prior evidence of the same failure, affected source/dependency
comparison, why primary change evidence remains credible, missing knowledge/risk,
owner/revisit condition and the actual acceptance decision. No blanket exception for
Windows, any unchanged test, timeouts, missing logs or 'probably flaky'. Repeat on a
new SHA is not automatically the same failure. Unknown attribution remains blocking
unless coordinator explicitly justifies and records a bounded risk acceptance under
this user's delegated judgment; never call it a diagnosed pre-existing cause.

Raw CI stays failed when it failed. Say **accepted with exception**, not all-green/fixed.
A later green run does not erase the failed run or diagnose its cause. Reruns require a
specific diagnostic question, bounded count and recorded original/attempt outcomes;
never run until green. Environmental/provisioning failures are distinct from test failure.
No permanent quarantine/skip/failure allowlist in this turn.

### Economical review and evidence

Worker owns shared builds until source freeze/explicit release. Freeze the changed
surface and HEAD; coordinator checks that surface and unchanged areas relevant to
claims. No mandatory every-file hash inventory, multiple identical CI ZIP downloads or
multi-layer source censuses merely because prior turns did them. Keep one primary CI
outcome/reference and useful failure evidence; Git/source identity and targeted hashes
where provenance actually matters. Preserve failures, uncertainty, secrets boundaries
and safe owned-process/fixture disposition. Stop when the bounded question is answered.

## Validation and publication for THIS turn

- Focused pre-edit/before-after report/status/workflow checks. No baseline full/real
  Batch job is required just to repeat Iteration15 evidence.
- Worker one final `scripts/check.sh -v` in existing project tools environment;
  meaningful before-fail/after-pass controls where feasible. Static docs/workflow checks.
- Coordinator independent focused reporting/status/workflow tests and source review,
  NOT a mandatory second full/installed Batch run. No fixture/image/server startup.
- Focused worker commit/normal push after acceptance; inspect all final-SHA jobs and
  actual report artifacts. Prefer all green; apply the explicit triage/exception policy
  rather than imposing unconditional all-six-green. New reporting defects must be fixed.
- On CI evidence, coordinator may refine reporting/selection/triage within maintenance
  scope. Record each revision and its justification; no need to ask user for every
  bounded adjustment. Runtime changes, global services/tool installs, cloud, releases,
  extra agents or a later feature turn are outside scope and need separate approval.
- Concise worker RESULTS and coordinator REVIEW/COORDINATION, actual final outcome
  (green or explicit exception), source/remote/ownership/disposition check, STOP.
  No design checkpoint commit/push requested.

## Evidence-based final disposition: VP-001

Actual published4a053340 CI41098299553 attempt1 completed with five successes and
one macOS arm64 failure in unchanged asynchronous-story execution. New15 reporting
checks pass on every platform; all six XML artifacts correctly retain outcomes and
match primary counts/digests, including the real failed job. Source/dependency/source-
ordering review does not establish root cause or attribution; do not call this a
proven inherited defect or same Windows cause. No speculative runtime fix/retry.

Coordinator applies the user-delegated UNKNOWN-attribution bounded risk-acceptance
clause: **maintenance accepted with [exception VP-001](EXCEPTION-VP-001.md)**, raw
CI stays FAILED. ExactSHA/job/test only, named coordinator follow-up/revisit before
related changes or recurrence/next planning checkpoint; not a standing waiver.
This is the recorded evidence-driven application of the plan, not altered thresholds,
masked CI, automatic retry or new runtime scope. The reporting/triage question is
answered; broader async/native-open investigation remains an OPEN follow-up requiring
separate authorized scope. No additional implementation/CI run is needed just for green.

