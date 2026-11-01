# Validation-policy maintenance results

Status: **COMPLETE AND STOPPED; accepted with [exception VP-001](EXCEPTION-VP-001.md)**
through published `4a05334058a77e78c8ad9c512726123fc347e352`.
Raw exact-SHA CI41098299553 attempt1 remains **FAILED: five successful jobs, one Macarm
failure**. All six reports pass the reporting audit; coordinator explicitly accepts
bounded UNKNOWN-attribution risk. NOT all green/fixed/diagnosed inherited. No rerun,
fixture/image/service startup, installations or design publication.

## Preflight and selection

Fresh session `01a18dc6-1793-766c-90ee-c5caa22aad10`, existing pane `%215`, Pi PID491011
(parent4017062); coordinator `%197`. Machine index read first, `/work` mounted, admin
placement/design instructions/README/discussion resume/glossary/complete maintenance plan,
handoff and coordination/implementation instructions and owning workflow/check/config/tests/
coverage guidance/Iteration15 final results and review read. DML tree/index clean at
published `664a87085961b5e24d2b709e057e4a28fe724088`, master/origin master match; no active
check/pytest/build found. Accumulated design notes preserved; coordinator owns designstatus.

Change-validation map:

| Changed surface | Primary evidence | Unchanged evidence/boundary |
| --- | --- | --- |
| Development selection/triage policy and AGENTS/README pointers | Owning-doc review/local links/exception-risk checklist | Historical reports not rewritten; no standing exceptions |
| CI JUnit flag and step-local strict environment/upload | Current official docs; real current workflow commands and owning check function in tiny isolated suites | Platforms/full arguments/action versions/budgets/dependencies/exits unchanged |
| Default-safe reporting regressions | Real pytest pass0/fail1/collection2/usage4/no-tests5 and XML content/absence | No generic classifier/wrapper/dependency; no fixture or runtime changes |

No fresh full baseline: exact published Iteration15 final pass supplies existing evidence;
focused before/after checks distinguish the reporting change. One final worker unchanged
full-v on stable relevant sources remains required; coordinator independent validation will
be focused/risk-based, not automatic duplicate full/installed fixture work.

## First concise draft and focused checks

DML changed surface: `.github/workflows/ci.yml`, `AGENTS.md`, `README.md`, new
`docs/validation-policy.md`, new `tests/python/test_ci_reporting.py`. `check.sh`/pytest
configuration/native/runtime/diagram/release controls untouched. Matrix appends only
`--junitxml=build/test-results/pytest.xml`; strict step uses existing `PYTEST_ADDOPTS`.
New per-platform/strict always-upload steps select only the XML file, with missing-file
warning, no captured stdout/env dump or whole temp stores.

Current official documentation queried: `/websites/pytest_en_stable` (JUnit support,
collection errors, exit codes), `/websites/github_en_actions` (always uploads),
`/actions/upload-artifact` (current v7/path/name/missing-file/default hidden-file behavior).
Sources include pytest stable docs, docs.github.com Python workflow example and
[upload-artifact README](https://github.com/actions/upload-artifact/blob/main/README.md).
Actual installed toolchain pytest/coverage are exercised, not inferred from documentation.

Evidence under `../dml/build/validation-policy/`:

- `before-reporting.{log,exit}` **exit1/one intended assertion failure**: new contract test
  rejects original workflow's missing upload step;14 deselected. Not a collection/tool error.
- `first-focused.{log,exit}` **exit0/23 passed/6.76s**, new reporting suite plus existing
  check-script/MSYS/LF/existing outer-budget tests. Twelve real child cases execute CURRENT
  matrix Unix/Windows commands or owning strict check function (both source/no-source
  branches), verify pass0/fail1/collection2 and actual testcase/failure/error counts.
  Early usage4 produces no XML; no-tests5 produces zero-test XML, not successful tests.
  Nested probes clear only their inherited pytest/coverage/PYTHONPATH settings and use
  owned temp cwd/config/report path, avoiding global parent JUnit/coverage overwrites.
  Strict test/collection failures stop before later coverage report generation.
- `focused-isolation.{log,exit}` **exit0/23 passed/6.84s**, with actual outer XML
  `focused-parent.xml`. Each of twelve real probes seeds conflicting parent JUnit/filter/
  missing-plugin/coverage-file settings and sentinel files, then verifies both sentinels
  unchanged and correct child result/XML. Black subsequently formats the test only.
- Static local Markdown checks: three DML documents/39 file+anchor targets pass; whitespace
  passes. No actionlint executable is installed; no provisioning or hosted syntax claim.

Installed project toolchain is pytest9.0.3/coverage7.14.1. Direct stable-doc HTTP lookup
returned403, not a successful retrieval; official pytest GitHub source via Actions-authorized
GitHub read succeeds. `official-pytest-addopts.rst` records environment/CLI precedence:
configuration addopts, then PYTEST_ADDOPTS, then command-line arguments (last wins).
`official-pytest-usage.rst` is retained. A probe-only excerpt slicing mistake initially
created an empty file and was corrected; no implementation/config/status consequence.

These are host reporting/config/status checks, not actual hosted artifact uploads,
Windows execution or final all-platform CI proof. Final published-SHA XML counts must be
compared with primary job result/log populations. XML presence alone is not completion/pass.

Policy exceptions are procedural only: actual SHA/run/attempt/job/node/signature/primary raw
failure, inheritance/attribution/source-dependency reasoning, credible primary evidence/risk,
named follow-up/revisit condition and coordinator scoped decision are required. No actual
exception approved or claimed. UNKNOWN causes from Iteration15 Windows ENOENT and older
failures remain UNKNOWN; a later pass is not their diagnosis/fix.

First draft sent to coordinator for read-only feedback before final full-v. Coordinator
accepts concise policy/exact five-file draft for the final gate, not publication. Black
check/whitespace/three-document39-target links pass. Exactly five source hashes and HEAD
captured in `stable-five.json`, not a whole-source inventory. Supervisor881721 starts the
ONE unchanged final command with all five sources stable:

```sh
cd /work/repos/micha/dml
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`standard-final.{log,exit}` completes **exit0/2082 Python tests/two existing warnings/
470.48s**, **4301/4301 ROOT-source statements**, **seven C executables under Valgrind**,
unchanged retained native1681/1681 lines,132/132 functions,1562/1562 branch outcomes all100%.
Binding0 unsuppressed errors/existing624 suppressed runtime contexts; **141 native CLI
Valgrind processes** pass. Existing dependency/compiler/lcov warnings retained. No new
exclusion/source omission/threshold/suppression/skip/runtime/outer-budget change. This is
worker host/native evidence, not actual hosted uploads or new installed-child assurance.

AFTER the sole final gate, exact five files/HEAD664a870 stable against `stable-five.json`,
index empty; complete `changed-five.diff` and `release-check.json` retained. No entire
repository hash/source census. Only docs/AGENTS/README/workflow/default-safe test changed;
native/runtime/packaging/diagram/release controls untouched. No fixture needed/restarted.

Worker **FREEZES all five maintained changes/HEAD and build/test use**, and **EXPLICITLY
RELEASES BOTH build/check AND build/coverage** to coordinator for independent focused
reporting/status/current-command/doc review. Worker RESULTS-only while frozen; no tests,
source edits, staging/commit/push until explicit acceptance/ownership return. Share one set
of six small final-SHA XML artifacts for independent count review rather than duplicate
large log ZIP inventories. No design checkpoint/publication, fixtures/services or extra agents.

## Independent acceptance and normal publication

Coordinator verifies exact frozen5/HEAD/index/hashes and independently executes focused
reporting/check-script suite **exit0/23 passed/6.70s**, actual independent XML23 tests/
0failures/0errors/0skips. Own eight-doc48-target link/whitespace review and after-check
five-file stability pass. No outstanding finding or exception; this is independently
executed evidence, not worker replay. Coordinator accepts exact5 and explicitly returns
BOTH builds/source for focused normal publication/actual final-SHA CI/report audit.

Worker stages only five accepted DML files; reads complete staged diff, checks exact
staged+source five hashes/empty unrelated surface/whitespace/scoped secret patterns.
Focused **`4a05334058a77e78c8ad9c512726123fc347e352`**, parent664a870, **five files/+338/-3**,
commit and normal existing master/origin push **exit0**. Tree/index clean; remote master
matches. No amend/force/new remote/tag/release/package/design publication.

Immediate first exact-SHA runlist is empty (queue delay), not failed CI. Sole automatic
push [CI41098299553](https://github.com/micha/dml/actions/runs/41098299553), attempt1,
then starts. `final-runs.json` and finite1500-second `final-watch.{log,exit}` retain
actual SHA/run/observation. No manual rerun or final success/exception claim. After
completion, one shared set of six small XML ZIPs and primary result counts will be audited;
no duplicate full suite/fixture/large-log archive ritual. Original before-failure and
Iteration15/older UNKNOWN causes remain preserved.

## Actual final CI and artifact audit

Sole automatic exact4a053340 [CI41098299553](https://github.com/micha/dml/actions/runs/41098299553),
**attempt1/completed FAILURE**; one finitewatch **exit1**. Five jobs succeed; macOS arm64
fails its actual Python test step, NOT report upload. No workflow rerun/source correction.
`final-ci.json`, `final-artifacts.json`, one shared six small XML ZIP+XML set under
`xml-artifacts/`, direct per-job primary logs and `xml-audit.json` retain evidence.
All six ZIPs validCRC/exactly `pytest.xml`, no captured-stream XML elements. Actual
counts reconcile with primary summaries and every testcase/failure/error/skip element:

| Job | XML tests | Passed | Failed | Errors | Existing skips | New reporting tests |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Linux x86_64 | 2082 | 2082 | 0 | 0 | 0 | 15 pass |
| Linux aarch64 | 2082 | 2082 | 0 | 0 | 0 | 15 pass |
| Strict Linux check.sh | 2082 | 2082 | 0 | 0 | 0 | 15 pass |
| macOS x86_64 | 2082 | 2078 | 0 | 0 | 4 | 15 pass |
| macOS arm64 | 2082 | 2077 | 1 | 0 | 4 | 15 pass |
| Windows AMD64 | 2081 | 2076 | 0 | 0 | 5 | 15 pass |

Every job passes seven C executables. Windows retains the pre-existing platform-specific
parameter difference. No new skip/exclusion/runtime/outer-budget/platform/dependency or
release change. Strict CI-c remains informational coverage, not worker full-v/memory.
Single downloads only; Macarm failure log was independently retrieved concurrently by
worker/coordinator before steering arrived, acknowledged duplication with no later repeat.
No large whole-run ZIP/duplicate watches/new experiments or speculative tests/fixes.

## Macarm failure triage / approved exception VP-001

Actual job **124209695675**, test
`tests/python/test_asynchronous_example.py::test_maintained_async_story_host_client_helpers_full_bytes_cli`,
XML artifact **12996819484**. Signature: `DmlError storage_error/native2: opening LMDB
environment: No such file or directory`, opening `workspace-1/worker.dml` during
**publication observation** in `observe_exchange`, not test timeout or artifact failure.
Primary raw `macos-arm64.log` and coordinator `macarm-failure-primary.log` retain full
stack; XML contains its failure. Later owned diagnostics show worker.dml/bundle/completion
present, successful done outcome/cleanup and rc0/reaped worker; later state does not
explain the earlier ENOENT. No new reporting failure; all15 cases pass on allsix jobs.

Bounded read-only attribution:

- Exact five-file commit leaves old test/observer/example/native/diagnostic/dependency
  declarations unchanged. This alone does NOT establish inheritance/non-regression.
- Failed case is first XML testcase; new reporting probes are indices340–354 and had
  not run. Global JUnit/timing/ephemeral-host effects remain possible, not diagnosed.
- Readiness is published AFTER B create/import/selection. Initial/publication use the
  same B path; no demonstrated deletion occurs in these paths. Local cleanup targets
  separate `dml-local-*` scratch. Native env-open flags0 returns errno2, not a clock guard.
- Retained Iteration15 final Macarm primary installation summary matches pytest9.2.0,
  coverage7.17.0, Hypothesis6.170.14, Meson1.12.1/Ninja1.13.2 and other listed pip packages;
  earlier Macarm2063pass4skip. This is package comparison, not full environment capture.
- Prior Iteration15 Windows ENOENT occurred with childrc1/no final output; this Macarm
  observer failure has later successfulF/rc0. No demonstrated identical prior Macarm
  signature/cause or proven equivalence to Windows. Both underlying causes remain UNKNOWN.

Coordinator independently audits final SHA/run/attempt/job metadata, shared six ZIP CRCs/
exactfile/report counts against primary logs, artifact metadata sourceSHA/server SHA256
against downloaded bytes, new15 cases/C7 each and accepted5 COMMITTED/source/remote stability.
Coordinator **APPROVES [VP-001](EXCEPTION-VP-001.md)** under delegated judgment: explicit
UNKNOWN-attribution risk acceptance for only this SHA/run/attempt/job/test/signature.
Reporting/policy evidence is credible, including real failed-job XML uploaded with
unmasked test exit; residual runtime/JUnit-timing/ephemeral-host risk stays unresolved.
Full cross-platform regression assurance is incomplete. This is not a demonstrated
inherited defect or a diagnosis/fix of this Macarm or previous Windows failure.

Named follow-up owner: **coordinator in pane%197**, accountable for carrying OPEN VP-001
into the next planning/review checkpoint and proposing separately authorized investigation;
no implementation investigator assigned. Revisit before the next async observation/execution,
LMDB open/handle lifetime or story-test change; upon signature recurrence or credible
reporting/environment-causation evidence; and at the next design/maintenance planning
checkpoint. No standing waiver/automatic future acceptance/experiment authorization.
A fresh failure needs fresh attribution and decision. Raw CI remains FAILED; delivery is
**accepted with exception**, never all-green/fixed.

After CI, `final-source.json` verifies exact publishedSHA/parent664a870/exact5 accepted
source+COMMITTED hashes/clean tree+index/matching remote master. Owned full-check/watch
supervisors absent (ps exits1 when no selected processes), no remaining owned check/watcher.
No new fixtures/services were started; retired resources/images untouched. Proportionate
execution: no full baseline, ONE final worker full-v, independent23 focused tests instead
of another full suite, targeted five-file identity rather than whole-source inventories,
shared six small reports rather than duplicate whole-run ZIPs, zero CI reruns and zero
fixture/image/service experiments. Real negative hosted upload evidence is retained.

Coordinator directs RESULTS-only finalization, now complete. Worker explicitly **STOPS
ALL source/runtime/build/test/staging/commit/push/CI polling/rerun/fixture/image/job activity**
after this finalization/completion acknowledgment. No further tools, native investigation,
new commit solely for green, fixture restart, extra worker/global tooling/release/package/
design checkpoint or later feature. Coordinator owns final REVIEW/COORDINATION/designstatus.
