# Development validation policy

## Authority boundary

This document owns development validation selection, acceptance and CI failure triage
for the design spiral. [Build and Test](../README.md#build-and-test) owns commands;
[AGENTS — Testing](../AGENTS.md#testing) and the
[exclusion catalog](../tests/coverage-exclusions.md) own coverage criteria/rationales.
Technical contracts remain in [spec-next](spec-next/README.md). This policy does not
relax release controls, repository settings or historical delivery requirements.

## Choose evidence before running

Record a short change-validation map in the turn's results:

- Changed behavior/invariants → focused positive and relevant negative checks.
- Concrete acceptance workflow, when needed → what real execution/transport it proves.
  Mocks do not replace actual execution/transport when those mechanisms change.
- Unchanged areas → existing evidence relied on, and why another run adds assurance.

Focused behavioral checks and concrete acceptance are primary; CI supplies complementary
fresh-source portability/regression evidence, not scientific correctness or complete
external-environment capture. Documentation/CI-only work needs real reporting/configuration
checks, not unrelated computational jobs or retired fixtures.

When executable runtime/build/test tooling changes, the worker runs the unchanged full
standard gate once on final relevant sources (`scripts/check.sh -v` in the project tools
environment). Preserve tests, coverage/memory thresholds, skips/exclusions and budgets.
A fresh full pre-edit baseline is optional: select it when it can distinguish a meaningful
problem, not simply to repeat a recent exact published pass.

The coordinator independently reviews the changed surface and validates according to risk;
a second complete suite or installed fixture is not automatic. Recheck affected behavior
after substantive fixes. Documentation/exception wording alone does not invalidate unchanged
runtime/installed evidence. A repeat full gate or fixture needs a stated assurance benefit.

## Shared ownership and review

One worker owns shared builds (`build/check`, `build/coverage`) until explicit release.
Freeze HEAD, the changed-file list/diff and relevant source identity before independent
validation; do not edit or wipe builds concurrently. Use Git identity and targeted hashes
where provenance matters, not mandatory whole-repository inventories or duplicate log downloads.
Acceptance precedes focused commit/normal push. Report commands, actual exits, limitations,
original failures and safe owned-process/fixture disposition; stop when the bounded question
is answered. None of this authorizes a new fixture, service, dependency or later feature.

## CI reports are evidence, not verdicts

[CI](../.github/workflows/ci.yml) retains five full-test platforms plus Linux `check.sh -c`.
Each job requests pytest JUnit XML at `build/test-results/pytest.xml`, uploaded with the
existing artifact action on success/failure: `<matrix name>-pytest-results` or
`strict-linux-pytest-results`. Strict Linux uses step-local `PYTEST_ADDOPTS`; `check.sh`
and pytest configuration remain unchanged. Coverage reports in CI-c are informational;
build/test/report-generation nonzero exits still fail. Uploads do not mask test exits.

The upload selects only that XML file, not temp stores, environment dumps, credentials,
Docker state or research artifacts. Default JUnit captured-stream logging is not enabled;
failure tracebacks can contain test data, so keep diagnostic inputs nonsensitive.
Missing files produce an upload warning, not a claim that tests ran or passed. Early failure,
cancellation or a hard timeout may prevent report creation/upload. A present XML can contain
failures, collection errors, skips or zero tests; it does not establish completion/success.

After publication, inspect the **actual final SHA**, run/attempt and every job conclusion.
Compare XML testcase/failure/error/skip counts with primary job logs/results. Distinguish
collection/usage/no-test errors, environmental provisioning failure and cancellation from
test failures. Missing or inconsistent evidence requires investigation; no automatic pass.
See official [pytest JUnit](https://docs.pytest.org/en/stable/how-to/output.html#creating-junitxml-format-files),
[exit codes](https://docs.pytest.org/en/stable/reference/exit-codes.html) and
[Actions artifacts](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

## Failure triage and explicit exceptions

New attributable failures block acceptance: diagnose with primary logs/XML/diagnostics,
fix and add regressions. An unchanged test/source alone does **not** establish inheritance;
it can expose a regression in changed code or dependencies. Bound the investigation before
speculative edits. No continue-on-error, blanket xfail/skip, failure allowlist, automatic
retry or swallowed exit may turn failure into green.

An evidenced inherited failure can receive an **explicit acceptance exception** from the
coordinator, with named follow-up. Unknown attribution remains blocking unless the coordinator
explicitly justifies bounded risk acceptance under delegated authority. Do not label an
unknown cause diagnosed/pre-existing. Record the following in the turn's review/results:

- Actual failing SHA, run URL/ID, attempt, job/platform, test node ID and failure signature;
  primary failed logs/report reference (or precisely what evidence is missing).
- Prior evidence of the same failure, affected source/dependency comparison and attribution
  reasoning; a repeat on another SHA is not automatically the same failure.
- Why primary changed-behavior/acceptance evidence remains credible, unresolved knowledge,
  affected scope and residual risk. No blanket Windows/unchanged-test/timeout exception.
- Named follow-up owner and investigation task/reference, with a concrete revisit condition.
- Coordinator decision/approval and its scope: **accepted with exception**, not green/fixed.

This is a record checklist, not an automatic exception validator or a standing exemption.
Raw CI stays failed when it failed. Preserve failed runs even after a later pass; that pass
does not diagnose the earlier cause. Reruns require a specific diagnostic question, bounded
count and recorded original/attempt outcomes, never retry-until-green. A follow-up must
revisit the exception when its stated condition occurs. Changes beyond the authorized
maintenance/feature boundary require separate approval.

## Final report

Give the focused validation map/results, relevant full/concrete acceptance results, exact
published SHA/remote identity and actual CI outcome/artifact findings. Say **all green** only
when the actual jobs pass; otherwise name the approved exception record and unresolved
failure. Distinguish independently executed checks from reviewed worker evidence, tested
from excluded code, host coverage from installed-child/platform assurance, and fixed from
UNKNOWN causes. Retain prior evidence rather than rewriting historical failures.
