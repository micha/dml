# VP-001: macOS arm64 asynchronous-story failure

Status: **APPROVED bounded UNKNOWN-attribution risk acceptance for THIS maintenance
SHA/run/job/test only** by coordinator%197 under the user's delegated judgment,2026-10-30.
Final six-report artifact/source review is complete. This is NOT a diagnosed inherited
cause, a standing waiver, a test quarantine or permission to alter runtime/skip/retry policy.

## Exact observation and evidence

- SHA: `4a05334058a77e78c8ad9c512726123fc347e352`.
- [CI41098299553](https://github.com/micha/dml/actions/runs/41098299553), push, attempt1.
- Failed job: [macOS arm64 /124209695675](https://github.com/micha/dml/actions/runs/41098299553/job/124209695675).
- Test: `tests/python/test_asynchronous_example.py::test_maintained_async_story_host_client_helpers_full_bytes_cli`.
- Failure: `DmlError`, `storage_error`, native2/ENOENT opening
  `story/workspace-1/worker.dml` in `observe_exchange` during publication observation.
- Primary pytest: **1failed/2077passed/4existing skips/2warnings/328.12s**.
- Uploaded [pytest artifact12996819484](https://github.com/micha/dml/actions/runs/41098299553/artifacts/12996819484):
  XML2082tests/1failure/0errors/4skips; all15 new reporting cases pass. Raw failed status
  and traceback preserved, upload succeeds despite failed test step.
- Shared local evidence: `../dml/build/validation-policy/macarm-failure-primary.log`
  (coordinator raw API exit0) and `xml-artifacts/macos-arm64.{zip,xml}` (worker retrieved,
  one pytest.xml/valid CRC). Worker duplicate failed-job fetch preceded steering and is
  retained, not another CI attempt. No workflow rerun occurred.

Later owned diagnostics show worker.dml exists, complete successful F/output bundle,
cleanup ok and worker rc0/reaped. Those are LATER observations, not an explanation of
why the earlier open returned ENOENT. No filesystem/lock-file/system-call timeline
identifies the root cause. Do not infer a readiness race simply from ENOENT: current
source publishes readiness AFTER B creation/import. No deliberate B rename occurs
before completion in the inspected example.

## Attribution and missing knowledge

Exact changed surface is five guidance/workflow/report-test files; asynchronous example,
its test, exchange/local/native/Python binding, shared helpers/configuration and dependency
**declarations** are unchanged versus parent664a870. Prior retained Macarm CI41090059076
passed2063+4existing skips; observed pytest9.2.0/coverage7.17.0/Hypothesis6.170.14/
Meson1.12.1/Ninja1.13.2/pluggy1.7.0 and other listed installed package versions match.
This failed testcase is first in the report; new report-child probes appear later and
had not executed yet. Added global JUnit logging/runner scheduling/environment could
still affect timing. Unchanged source alone is NOT proof of non-regression.

No identical prior macOS arm64 failure is established. Earlier Windows ENOENT reports
concern different paths/stacks/later child disposition; do not call them the same cause.
Root cause and attribution remain **UNKNOWN**, not 'proven pre-existing' or fixed.

## Why bounded maintenance acceptance is considered

The scope changes validation guidance and diagnostic reporting, NOT runtime behavior.
Worker single full-v2082/4301/sevenC/unweakenedmemory and independently executed focused
23 reporting/status checks pass. Hosted Macarm proves the new upload preserves the real
failure without masking it; all15 new tests pass. Other five CI jobs pass. The current
question is whether the maintained reporting/acceptance process works, not a new claim
of healthy macOS asynchronous execution. Fixing an unproven runtime race by retries,
timeout increases or speculative core edits would expand this turn and weaken evidence.

Residual risk: a real macOS/runtime or report-induced timing problem remains unresolved;
CI is RED and full cross-platform regression assurance is incomplete. Acceptance must
say **accepted with exception**, never all-green/test fixed. The record applies ONLY
this SHA/run/attempt/job/test signature; unrelated/new failures are not exempted.

## Named follow-up and revisit conditions

Follow-up owner: **coordinator in dml-design pane%197**, accountable for carrying VP-001
into the next planning/review checkpoint and proposing a separately authorized bounded
investigation. Implementation investigator is NOT assigned; no extra agent/runtime or
fixture restart follows from this record.

Investigation goal: establish a precise filesystem/native-open/worker/readiness timeline,
including possible data/lock-path failure, independently compare platform/runtime and
JUnit-on/off behavior with controlled finite runs, and produce a reproducing regression
before a claimed fix. Distinguish API transport errors, transient absence and true corrupt
history; preserve the original failure and avoid catch-ENOENT-as-bootstrap masking.

Revisit REQUIRED before accepting the next change to async observation/execution,
LMDB open/handle lifetime or these story tests; upon recurrence of this signature on
macOS or credible evidence linking it to reporting/environment changes; and at the next
design/maintenance planning checkpoint. A fresh occurrence needs its own attribution/
acceptance decision—this is NOT a standing exemption. No arbitrary number of reruns until
success. Investigation beyond this maintenance scope requires separate authorization.

## Coordinator decision

Coordinator%197 **accepts this bounded validation-policy/reporting maintenance delivery
WITH EXCEPTION VP-001** at exact4a053340/CI41098299553/attempt1/job124209695675/test above.
Raw CI remains **FAILURE: five successful jobs, one failed macOS arm64 job**. No rerun,
code fix, skip or green/fixed claim. This explicitly accepts UNKNOWN attribution and the
stated residual risk; it does not certify healthy asynchronous execution on macOS.

Independent final verification: exact six job outcomes/SHA/attempt; shared six ZIPs each
one pytest.xml/valid CRC; all artifact metadata sourceSHA and server SHA256 digests
match downloaded bytes. Every report's testcase/failure/error/skip counts matches its
primary job summary; seven C executables pass each, all15 new reporting cases pass each.
Only this old-story failure occurs. Exact accepted5 committed/source hashes, parent664a870,
clean tree/index and matching remote are unchanged AFTERCI. No source/runtime change or
new evidence demonstrates causation. Positive reporting evidence includes preservation
of a REAL failed-job report, not just passing mock reports.

Follow-up VP-001 remains OPEN with coordinator owner/revisit conditions above. This
exception is part of the actual maintenance acceptance record; future failures need
fresh attribution/review, and any demonstrated link to reporting must reopen it. Worker
may finalize RESULTS-only and STOP. No further runtime investigation/fixture/CI activity
is authorized by this approval.

## Iteration 16 planning checkpoint revisit

Coordinator revisited this record when the user agreed to planning versioned implementation
selection for one intent. Root cause/attribution remain UNKNOWN; no new experiment or prior-
failure equivalence evidence. The proposed slice changes example-local definition/choice/
decision authoring and uses existing execution, not async observation/LMDB handle lifetime/
affected story mechanics. Investigation remains OPEN, not started or automatically deferred
past a related source change. Conditional handoff must pause/separately scope it if such changes
become necessary. THIS maintenance exception does NOT extend to Iteration16; any future CI
failure needs fresh attribution and explicit risk/acceptance decision. No new worker/build/
fixture/CI/source/publication permission is granted by this planning revisit.

## Iteration 17 planning checkpoint revisit

The user agreed to planning advisory implementation supersession after reviewing completed
Iteration16. Coordinator revisited VP-001: original root cause/attribution remain UNKNOWN;
Iteration16's actual macOS15/arm64 pass is not diagnosis of the earlier macOS14 ENOENT.
Proposed work adds ordinary declarations and pinned/separate-context readers, using unchanged
public local completion/selection authority. No async observer/LMDB handle lifetime/affected
old-story source change is presumed. Follow-up remains OPEN with its owner/revisit conditions;
pause and separately scope investigation if related changes become necessary or the signature
recurs. Maintenance's exception does not extend to Iteration17. No new probes, worker/build/
fixture/CI restart, investigation or publication is authorized by this planning revisit.

## Iteration 18 planning checkpoint revisit

The user confirmed versioned multi-input reuse with exact URI/full binding/full input matching
and requested handoff preparation after accepting completed Iteration17. Coordinator revisited
VP-001: original root cause/attribution remain UNKNOWN; Iteration17 actual six-platform pass
is not diagnosis of the earlier ENOENT. Proposed work changes example-local table/decision/
selection composition, not async observation/LMDB handle lifetime/affected old-story sources.
Follow-up remains OPEN with the same owner/revisit conditions; pause and separately scope any
related changes or recurrence. No standing Iteration18 failure waiver, investigation or worker/
source/build/story/CI/experiment/publication permission follows this planning revisit.

## Iteration19 planning checkpoint revisit

After reviewing completed18, the user agreed intent-scoped cross-implementation reuse and
simplified selected-entry removal (persistent result restrictions deferred), then requested
candidate preparation. Coordinator revisited VP-001: original cause/attribution remains UNKNOWN;
Iteration18's actual six-platform pass is not diagnosis of earlier ENOENT. Candidate work is
example-local table/decision/own-Q/ordinary W composition over unchanged public producer-history
and synchronous local execution, not async observation/LMDB handle lifetime/affected old-story
source changes. Follow-up remains OPEN with existing owner/revisit conditions; related changes
or recurrence require fresh scoped investigation/triage. No standing Iteration19 waiver or
investigation/worker/build/story/CI/source/publication authorization follows this planning revisit.

