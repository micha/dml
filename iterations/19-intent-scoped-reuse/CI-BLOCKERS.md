# Iteration 19 CI blockers: fresh UNKNOWN-attribution failures

Status: **publication exists; CI disposition BLOCKED pending scoped decision**.
This is NOT an approved acceptance exception, diagnosed inherited failure or permission to
investigate related runtime/story behavior. Coordinator%197 owns follow-up and user scope request.

## Exact observations

Published SHA `a71e89f80f319a4abc4f3d1b57ab1ad8ffe559ed`, parent3b2b370, exact accepted TWELVE.
Automatic push [CI41269736666](https://github.com/micha/dml/actions/runs/41269736666), attempt1,
raw **FAILURE: four successful jobs, two failed jobs**. No rerun/dispatch/source fix.

Both failing jobs report ONLY
`tests/python/test_asynchronous_example.py::test_maintained_async_story_host_client_helpers_full_bytes_cli`:

- [Windows AMD64/job124739865241](https://github.com/micha/dml/actions/runs/41269736666/job/124739865241):
  completion poll `handle-2.json` expires at existing15s demonstration deadline. Diagnostic
  workspace2/native publication selected, owner rc1/reaped, completion.json/output.bundle absent;
  worker.dml exists at later diagnostic inspection. Truncated worker.stderr ends in
  `LocalExecutionError: storage_error: opening LMDB environment: No such file or directory`
  through local.py `_run` line568. XML2656/2650pass/1failure/0error/5existing skips;
  primary423.98s, not outer-job timeout.
- [macOS x86_64/job124739865282](https://github.com/micha/dml/actions/runs/41269736666/job/124739865282):
  same test/completion15s deadline, diagnostic workspace3/native publication selected, owner
  rc1/reaped, completion/output absent, later worker.dml exists, truncated stderr ends in same
  LocalExecutionError LMDB-open ENOENT. XML2657/2652pass/1failure/0error/4existing skips;
  primary829.28s, within existing20min outer cap, not outer-job timeout.

Different workspaces/platforms/occurrences are NOT proven same root cause, nor proven identical
to maintenance VP-001's Macarm observer-open failure. Later path existence does not explain
earlier ENOENT. Deadline exhaustion is an observed symptom, not justification for increasing
it or hiding native errors. Failed owner reaping does not certify computational-child disposition
at the failed step; uploaded tail lacks complete worker traceback/filesystem/native-open timeline.

## Independently verified shared evidence

`../dml/build/iteration19/final-ci-evidence/` retains SINGLE six small ZIP/XML, actual run/jobs/
artifacts metadata and useful direct per-job primary logs. Windows primary was downloaded once
successfully by coordinator and reused, not downloaded again. Independent ZIP CRC/exact one
pytest.xml/server SHA256/sourceSHA/run/artifact identity/full XML counts versus primary/C7 verified.
Receipt `build/iteration19/coordinator-ci-audit-pending.json`. All **164 NEW policy/authority/fault/
controller tests PLUS4 cleanup registration tests PASS on EVERY platform**, no new skips.
Other jobs: StrictLinux/Linuxx86/Linuxarm2657pass; Macarm2653pass+4existing skips. Raw failures stay.

Coordinator's initial Windows `gh api` GET rejected terminal escapes; initial assistant message
incorrectly asserted exit0 before checking. Corrected documented `--allow-escape-sequences` GET
actually exits0 and supplies complete retained primary. Original tool error/message and correction
are retained, not a runtime failure/extra CI attempt or two successful downloads.

## Attribution and assurance boundary

Affected async example/test/local/exchange/native/fixture/story-diagnostic/workflow/dependency
sources are unchanged versus parent, except cleanup population adds four exact module names;
old async module is not newly eligible. Independent affected-source Git diff inspected. New
example-local Mi/Di helper does not change runtime behavior. Failure appears in first old test
before new cases execute. Collection/import/global/environment/timing effects remain possible:
unchanged source alone does NOT establish inheritance or absence of regression.

Parent Iteration18 exact3b2b370/CI41182904065 actually passed both affected platforms, not evidence
of a diagnosed identical pre-existing cause. Windows primary actual pytest platform and pacman
Packages64 show Python3.14.9(parent) ->3.14.10(current), same observed pytest9.2.0/coverage7.17.0/
Hypothesis6.170.14 etc. Difference is NOT causation. Mac observed installed package lines match;
complete runner/environment/filesystem equivalence is not established. Worker first attribution
filename-suffix failure preserved; later Windows selector wrongly compared first Packages4 while
claiming Packages64, reporting false equality. Coordinator independently read actual64+platform
lines, requested original source/report/log preservation and corrected same-byte analysis. No
runtime experiment, silent evidence overwrite or inferred package-version fix authorized.

Primary Iteration19 assurance remains independent48 focused/1384 installed NONEXECUTING,
reviewed worker209/solefull2657/unweakened gates/actual6Q4T26phase/IS-001 resolved. This supports
bounded new composition, not healthy cross-platform asynchronous runtime assurance. Both fresh
failures/root causes/attribution remain **UNKNOWN**. VP-001 stays OPEN UNKNOWN/no standing waiver.

## Decision boundary and proposed next scope

No exception is currently approved; no all-green/complete delivery claim. Worker must pause
source/build/CI/story/computation/investigation after bounded evidence recording. User decision:

1. Authorize a separately bounded investigation by the existing agent (no extra worker), starting
   with a precise plan for filesystem/native-open/worker/cleanup timeline and preserved diagnostics.
   Finite relevant probes/diagnostic CI changes require explicit assurance questions/counts; causal
   fix/regression reviewed before commit/push. No timeout/skip/threshold/budget/runner relaxation,
   retry-until-green, new feature/cloud/global tooling or repeated Iteration19 acceptance story.
2. Accept Iteration19 with explicitly recorded UNKNOWN-attribution risk exceptions for THESE two
   SHA/run/job/test observations and stop. Raw CI remains FAILED; coordinator-owned named follow-up
   revisits before related async/LMDB/story/release-assurance changes or recurrence, not a standing
   waiver. This must be described as accepted WITH exceptions, never green/fixed/inherited.

Completed GO/older VP-001 does not authorize related async/LMDB investigation by inheritance.
Coordinator surfaces this fresh decision rather than expanding runtime scope or applying an
automatic old-test exemption. Final disposition/STOP remains pending.
