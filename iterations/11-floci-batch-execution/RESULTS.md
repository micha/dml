# Iteration 11 implementation results

Status: **COMPLETE AND STOPPED through published `640cabb05dd9426323069e816621dcbc0c829ae0`**;
all six final exact-SHA CI jobs succeed. Initial Windows old-reader cause remains UNKNOWN;
final pass/diagnostics are NOT its diagnosis or established fix. User Iteration11 GO and active
[COORDINATION.md](COORDINATION.md) supersede historical pending-GO plan headers.
Worker `%215` owns runtime/tests/as-built/example/fixture and this report; coordinator
`%197` owns independent review/coordination/design status. Independent initial/postfix acceptance,
separate focused publication and final exact-SHA verification are complete. Worker now stops
all runtime/build/test/fixture/staging/commit/push/CI activity. No design commit/push or later turn.

## Preflight and fresh unchanged baseline

Machine index/admin guidance/placement, design instructions/README/complete discussion/
glossary, approved DESIGN/EXAMPLE/HANDOFF/active COORDINATION, implementation instructions/
documentation guidelines/all current as-built public contracts, packaging/coverage catalog,
Iteration10 RESULTS/REVIEW/COORDINATION, feasibility index/iteration/final audit and complete
Floci REPORT/REVIEW/HANDOFF/probe/replay read. Current maintained exchange/SSH/worker/native
headers/storage claims/tests inspected; pinned released Batch definition/submit/runner and
S3 conditional-write source inspected. No historical task protocols executed.

`/work` mounted; `TMUX_PANE=%215` verified (default tmux current-window query points to
coordinator, not worker identity). DML tree/index clean at
`099d156fb49f81a7da0683898189a85c1172988c`; design HEAD
`28cbff2bf46819fb9b1048ccd351050957c521b4` with accumulated notes preserved.
No measured source edits preceded completed unchanged baseline:

```sh
cd /work/repos/micha/dml
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Evidence `../dml/build/iteration11/baseline.{log,exit}`, **exit0**: **1372 Python tests**
(187.97s), **seven C executables**, Python **2828/2828 statements**, retained native
**1681/1681 lines,132/132 functions,1562/1562 outcomes**. Binding workload zero unsuppressed
errors/existing624 runtime contexts; **141 native CLI Valgrind processes**. Existing runpy
warning retained. No omission/exclusion/profile/threshold/suppression changes.

Explicit `unix:///var/run/docker.sock` daemon is michas-robots/linux/x86_64, `/work/docker`,
socketGID131. Cached Floci image digest
`sha256:09b72c45f333019adecb302e79c6b746e290135f528016c8514618bc7ab02344`
exists; OCI version2.3.0/revision`ee15f502bfc017861b67b076b82e1ccd032c7129` match pinned
retained primary source. No old study fixtures remain. Existing unrelated three service
containers untouched. Packaging Python/build/meson-python and bare cached Python3.13.15
available; bare Python closure query finds22 store paths. Current DML wheel/image/combined
gate still pending: an old installed artifact is not current-source evidence.

Context7 `/floci-io/floci/2.3.0` Batch endpoints/attempts and S3 guidance corroborated against
pinned source; conditional-write source is not runtime proof. `/python/cpython` HTTPResponse
framing/connection ownership documentation informs strict bounded transport. No cloud/proxy/
credential discovery/SDK installation, pull/download/global service change or fixture startup
performed at this baseline checkpoint. Missing prerequisites still require scoped approval.
Prior unchanged Windows story causes remain **UNKNOWN**; baseline pass is not their diagnosis.

## Implemented surface and host assurance

Added `floci.py`, internal same-family `floci_http.py`, fixed installed `floci_worker.py`,
Meson inventory, finite example/child, default-safe tests, explicit fixtures and owning
as-built/navigation documents. Public exchange spec/handle/start/observe/inspector and
unchanged receive/local/transfer remain authoritative; no private cross-layer role/native/
job codec, native entity, CLI/old-spec/workflow/version change or SDK/Docker runtime dependency.

Direct unsigned HTTP has strict8192 status/header/descriptor counts, raw Connection:close EOF
beyond Content-Length, duplicate/framing/encoding/UTF8/JSON rejection, finite total time/call
accounting and closed acquired connections/streams. Original32MiB bundle/4MiB record limits
remain. Stage is create-only/manifest-last and nonexecuting; submit persists guard BEFORE API,
preflights exact revision/image/fixed command and forces attempts1. Valid acknowledged UUID
survives later ack/ARN/receipt/allocation errors; missing ack never clears guard/resubmits.
Saved identity composes public expected codec, metadata last, no endpoint/input/control/B/A/PID
consultation. One fixed F/U/P observation pins immutable files, validates/cleans scratch before
new packet; status is diagnostic, not outcome. Job program retains public WorkerLaunch, reaps
on all catchable poll/publisher errors, then attempts final read-only publication without repair.
Uncertain wait/diagnostic/write/flush/sleep errors retain same owner with at most one diagnostic;
known postreap close error does not retry forever. Primary/reap/final diagnostics remain separate.

Initial HTTP draft failed11 tests (three real missing HeaderReader.flush cleanup, eight private
mock setup defects); `http-first.log` retained and fixed before installed gates. Focused108 then
167/all568 runtime statements passed. Coordinator found diagnostic/sleep escaping uncertain
reap; protected fix **30** focused tests passes (earlier terse27 count was wrong). Expanded171/
all576 runtime statements passes. Earlier --source=file-path invocation failed measurement/no
data despite119 tests; module-scoped correction retained, no omission or passing-gate claim.
New native map-full/storage-loss/examples **47 tests** pass. Background fixture refinements
add three meaningful cases, **18 fixture tests** pass. No exclusion/threshold/profile/suppression
change or reduced original boundary. Host statements are not every branch/installed child.

Typed-complete retained-Cq/Q but T-to-other-matching-Q P/U/F rejects at association, not only
absent base. Successful genuinely NEW actual-A puts/readback precede late different/raw refs,
real1MiB-map/2MiB-result failure and private consuming-commit EIO. Complete typed/raw/compact
comparable-map physical oracles prove whole rollback. Actual receiver pre/post-storage-commit
barriers for all phases distinguish absent batch vs complete ref/history despite lost response;
receive retry never computes. Final role/evidence/diagnostic/cleanup authority stays exchange-owned.

## Actual current installed DML-in-Batch

Commands in implementation/tools shell, without downloads:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash tests/floci/build.sh "$PWD/build/iteration11-image2" \
  "$PWD/build/iteration2-packaging/bin/python" /run/current-system/sw/bin/python3
python3 -B tests/floci/fixture.py start build/iteration11-image2 \
  --application ../dml-design/feasibility/floci/runtime/sources/release/src/main/resources/application.yml
env -u PYTHONPATH build/iteration11-image2/context/rootfs/opt/dml/bin/python -B \
  tests/floci/integration.py build/iteration11-image2 build/iteration11-image2/story-normal2
env -u PYTHONPATH build/iteration11-image2/context/rootfs/opt/dml/bin/python -B \
  tests/floci/retained_integration.py build/iteration11-image2 build/iteration11-image2/story-private3
env -u PYTHONPATH build/iteration11-image2/context/rootfs/opt/dml/bin/python -B \
  tests/floci/loss_integration.py build/iteration11-image2 build/iteration11-image2/story-loss1
env -u PYTHONPATH build/iteration11-image2/context/rootfs/opt/dml/bin/python -B \
  tests/floci/bootstrap_integration.py build/iteration11-image2 build/iteration11-image2/story-bootstrap1
```

Current build/start/normal2/private3/loss1/bootstrap1 **exit0**, separate evidence under
`../dml/build/iteration11/*.{log,exit}` and each story summary. Normal immutable image
**`sha256:64b55708793fd7c6af80db671d19eedd42c587fb58a214823877147dad603ee5`**;
installed host Python `../dml/build/iteration11-image2/context/rootfs/opt/dml/bin/python`.
Bare Python3.13.15/22 cached store paths/current dirty-source wheel route. All **16 package/
core/CLI/module artifacts** match byte-for-byte across wheel/host/image/actual computational
child (`artifacts.json`, `wheels.sha256`); maintained Python source bytes match installed Python
modules. Native extension/CLI binary equality is artifact equality, NOT native C source bytes
equal to binaries or independent native build reproducibility. No checkout/PYTHONPATH/shared
runtime/exchange/A mounts or
packaged tests/controller/private hooks. cp313-abi3/current prefix is not earlier-Python/other-
platform/general relocation/reproducible-vendor-binary proof. Raw evidence remains ignored.

Before EVERY computational submit: pinned Floci digest/revision, user1001/GID131/socket+private-
volume-only mounts/cap-drop/no-new-privileges/service512MiB/1CPU/pids256, internal bridge/no ports,
robust ALL128 keys/effective EXACT Batch/S3/CloudWatchLogs/IAM and actual no9169 binding proved.
Actual conditional PUT:* create, collision412 and exact original GET bytes pass. Job512MiB/
user1000/no mounts/no ports/no privilege inspected. **CPU/PID ceilings absent and service CapDrop/
SecurityOpt NOT inherited**. Actual child Uid/Gid1000, CapInh/Prm/Eff0, CapBnd`00000000a80425fb`,
NoNewPrivs0/Seccomp2 recorded. Trusted finite workload, not adversarial confinement; trusted
service socket remains daemon-root-equivalent. No host-network/global-firewall workaround.

### Normal installed worker, separate from private wrappers

**Three real jobs/nine newly produced P/U/F packets**: submitter exits/stopped before initial
S3 gate release; A/input offline; fresh installed observers same job/T, no recomputation. Actual
P/U gated B public BFS every typed packed byte/every parent/composite-only descendants equals
packet rows/validation/A. Exact Q/Cq/only new T/initial fields/ordered history preserved. Two
matching same-C requests have distinct Q/T/job IDs/equal42; never-started Q stays without T.
Nonzero23 AFTER U is recorded failure/evidence with separate cleanup while normal outer job
SUCCEEDED. Endpoint-offline receive preserves independently advanced main/sentinel/submission/
request refs/old bytes, no B refs, nonexecuting repeats. Child asserts all16 installed bytes and
consumes/checks declared endpoint via exact fixed-fixture assertion; actual /proc security recorded.

Initial image1/normal1 also passes, but predates protected secondary-reap fix and endpoint/
security enrichment. Retained, not called current: image
`sha256:a99d6d691256523a555722576347a1c8d0e9ad4e5625b47f639e3e255bd89b7b`, core wheel
`fa009ad54a79e8b144dd721f026fbfbea0fc8fc5f316a36dfdf4ffc701229bf6`, CLI
`f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`.

### Private after-reap evidence and preserved failures

`private3`: explicit fixture-only ENTRYPOINT/image OUTSIDE installed package invokes unchanged
worker then finite hold only AFTER return/known reap. Three cases have copied final actual B
**133/139/135 typed rows**. Complete byte/parent equality across B/packet-validation/A applies
ONLY to held successful F and genuine locked-scratch cleanup-failed F. Overflow has the actual
B oracle/done-field checks and retained P, NOT returned F/validation/A equality. Its **4MiB+1
BYTES payload** yields a larger packed datum record including the40-byte envelope/prefix,
exceeding the unchanged4MiB packed-record profile. Worker0/0/1, outer natural
75/FAILED/attempt1. Valid F is done while RUNNING and after outerFAILED; overflow B genuinely
records F but no done packet, old P stays working. Exact private B copy is NOT normal runtime
archive/durability. Unuploaded B can disappear with Floci automatic container removal.

`private1` **exit1**: whole-workspace cp fails intentionally locked cleanup scratch/data permission,
not runtime. Original log/partial archive/completed final-held B retained; no permission edits.
Correction copies only exact worker.dml into fresh destination after actual reap. `private2`
**exit1**: ps->inspect races natural child removal. Original log/completed B copies retained;
one bounded fresh census accepts only proven disappearance; persistent/new IDs/IO uncertainty
reject, not retry-until-pass. Source/default-safe census regressions pass. New explicit Q/story/
pinned revisions repeat known safely stopped cases, never unknown submission. Both original
fixtures safely exact-terminal/census/namespace checked stopped/archived; no live-child sacrifice.

### Actual S3/job loss, immutable pin and bootstrap

`loss1` **exit0/two actual jobs** plus staged-body-without-manifest:

- Real input bodies commit; private post-response suppression prevents input manifest/successful
  stage, no computational submit, Q/control retained.
- Exactly ONE real accepted SubmitJob; private after-HTTP acknowledgement suppression leaves
  caller no ID/retained guard, repeat rejected before API. Explicit OUT-OF-BAND token/initial
  manifest/single resource-ID container/DescribeJobs correlation identifies that exact job,
  then gates release/natural reap. No ListJobs/runtime repair/resubmit; not physical packet loss.
- Actual S3 snapshot body privately cut after32 bytes: strict installed transport rejects/no
  successful packet. Fresh client retrieves same gated U without another T. Background reader
  holds selected U manifest while real F arrives; ALL owned packet bytes remain U, no retarget.
- Private job-side response suppression after actual P-manifest commit: fresh observer retrieves
  immutable P, publisher retains/reaps and final read-only attempt publishes genuine F. Actual
  final B/validation full byte equality, valid F before outerFAILED75. Not installed fault API.

`bootstrap1` **exit0**: real stage, exact owned input-body deletion BEFORE submit/launch; actual
installed job refuses missing pinned bytes. ServiceFAILED/attempt1 remains **working/bootstrap/
no packet**, no child-start marker. No invented T/computational outcome. Old P/U remain working/
provisional/unknown even after later F. Original local safe pre-spawn/after-reap loss authority
also remains in default tests, not a new detached Floci/host-crash guarantee.

ALL background readers explicitly waited/inspected; wait uncertainty retains registered ID.
Create name/intent precedes Docker create; unknown job IDs block stop. Every endpoint stop requires
exact known terminal token/ID/single attempt, ALL owner-client census/stopped IDs AND namespace
absence. Fresh service data/log snapshots on every stop. Current image2 fixture **stopped and
retained** for independent review; original image1 stopped evidence remains retained. No premature
retirement/prune/arbitrary historical scratch deletion/unknown-writer signalling or child kill.

## Standard/static/mutation/diagram checkpoint

Stable `standard1` **exit0**: **1572 Python** (209.91s), seven C, **3536/3536 Python**
(new runtime576/examples132), unchanged native1681/132/1562, binding zero errors/existing624 runtime
contexts and **141 CLI Valgrind processes**. Two intentional worker runpy warnings. Three background
regressions then added. Final stable `standard-final.{log,exit}` **exit0**:
**1575 Python tests** (204.80s), seven C, **3536/3536 Python**, unchanged retained
native1681/132/1562 all100%, zero binding errors/existing624 runtime contexts,
**141 CLI Valgrind processes**, two intentional worker runpy warnings. All sources/tests
stable throughout final run, no coverage omissions/exclusions/threshold changes.

Black19 files/shell syntax/whitespace pass; **16 Markdown documents/281 local file+anchor targets**
pass. All16 current maintained/wheel/host artifacts/runtime-only inventory match. LMDB diagram
byte-identical to baseline: native/key/model/role review finds no new persisted entity/body/hash/
relationship/boundary or native transport boxes. Full suite includes focused diagram checks,
not a new browser audit. No native/old-spec/workflow/version or source-gate change.

mutmut/cosmic-ray commands/modules absent, no bootstrap. Seven ignored in-memory selected negative
probes modify NO maintained/installed file: each pytest **exit1/one intended failure**, not setup/
collection/internal errors, aggregateexit0: resubmit, status-to-done, conditional overwrite,
CL-hidden extra wire bytes, exact T-to-Q bypass, unsafe endpoint, packet-before-validation.
Evidence `build/iteration11/oracles/`. Not a framework mutation score/complete Python branch,
installed process-memory/security/host-loss assurance. Original C exclusions/CPython suppressions/
unsupported finalizer limits and **UNKNOWN old Windows causes** unchanged.

## ALL-source freeze and explicit release for independent review

Final standard/static/package/actual-installed gates pass as qualified above. Index empty;
HEAD remains clean baseline commit099d156 plus exactly33 uncommitted reviewed-turn files,
not committed/pushed. Entire maintained implementation inventory is frozen:

- `../dml/build/iteration11-image2/all-source-freeze.json`: **204 ALL maintained source files**,
  SHA256 `71d8720a6546dc63441c094c27fd7c7cd968a896df582e72a77b704f43da6fe3`;
  includes baseline files plus33 changed files, sizes/SHAs/HEAD/current installed paths.
- `source-freeze.json`:33-file changed-slice inventory,
  SHA256 `04cb6e1fd3ab5893451d98a5e3152dda697d574f5196759219bdfcb017351aba`.
- `artifacts.json`:16 package artifact inventory,
  SHA256 `497c7fad612746d9dc2a6c86b7e2709c36c4edc09683f9ff0822b6edd8b80f11`.
- Current installed host Python:
  `/work/repos/micha/dml/build/iteration11-image2/context/rootfs/opt/dml/bin/python`;
  normal image `sha256:64b55708793fd7c6af80db671d19eedd42c587fb58a214823877147dad603ee5`.
  Image/wheels/closure/current-package/normal/private/loss/bootstrap evidence retained there.

All204 hashes rechecked stable after final gates. Native/core/local/transfer/exchange/CLI/
old-spec/workflow/version/LMDB diagram remain unchanged. Design/coordinator notes are preserved;
this report is worker-owned and not an implementation commit.

Worker now **FREEZES ALL implementation files AND all shared build/fixture use** and
**EXPLICITLY RELEASES BOTH build/check AND build/coverage to coordinator** for independent
full-v/custom current installed probe. No worker edits/builds/fixture operations until ownership
returned. Report-only reconciliation may continue. Current image2 fixture exact service
`8df5cdb8fe5ae7753075c614e4732abc0977e1200e9e5111f1b1bc7ae2412da7` is STOPPED, known10 jobs
terminal/attempt1, all189 tracked clients/census stopped, namespace empty. All original/current
snapshots/B/provenance retained; new fresh coordinator fixture allowed within active GO, no
retirement of unknown writers. Original image1 also STOPPED with known5 terminal jobs/all84
clients/empty namespace; its original failed/partial evidence remains distinct and retained.

## Independent acceptance, focused publication and exact-SHA failure

Coordinator independently passes fresh full-v **1575/seven C/3536/unchanged native/binding/141CLI**
and separately authored fresh current-installed **380-check** normal17+25=42 story,16 artifact
assertions, exact Q/prior+composite history, all typed packed/all-parent P/U B/packet/A oracles,
offline same-target/ref-conflict/wrong-phase rejection. ALL204/33 hashes/file set,281 local
links/runtime-only artifacts/unchanged native diagram independently verified. REVIEW owns that
independent evidence, not a worker rerun. Coordinator fixture was exact-stopped/archived and
identity-retired (one job/15 clients); worker never operated it.

After explicit acceptance, worker verifies ALL204/33 accepted bytes, clean starting index/
existing master/origin/no sensitive markers, stages ONLY33 files and reads the COMPLETE6341-line
staged diff (`build/iteration11/reviewed-staged.diff`), whitespace passes. Focused commit
**`9ed2270aa595235856da436e283887023f067033`**,33 files/+6053/-2, normally pushed with **exit0**.
Implementation tree/index clean and remote master exact9ed2270 at publication checkpoint.
No ignored fixtures/artifacts/design/old-spec/native/workflow/version/remote/tag/release work.

Sole automatic exact-SHA push CI [40909150388](https://github.com/micha/dml/actions/runs/40909150388),
attempt1, completes **FAILURE: five jobs successful/Windows failed**; finite900s watch exits1.
Completed JSON and FULL primary failed/all-job logs retained under `build/iteration11/initial-*`.
Windows **1568 passed/five existing skips/two warnings/one failure**,213.94s: UNCHANGED
`test_caller_prior_q_t_history_coherent_pin_and_readers` delegates to old concurrent-observer
helper; both genuine B read barriers are reached, then a reader wait returns1. Its stderr
file contents are NOT exposed in the primary traceback. **Cause UNKNOWN**; not a runtime/gate/
new Floci defect or diagnosis of older Windows failures. All new Floci cases pass in that run.
No blind rerun, native/runtime/old test/gate relaxation or speculative fix.

## Authorized exact stopped-resource retirement

Original/current worker fixtures were already exact terminal/census/namespace checked stopped.
Post-acceptance latest service objects/logs freshly archived to each image root
`service-data-retirement`, with complete `retirement.json` stopped identity/job/client/network/
volume evidence. Existing B/packet/current/partial/private1/private2 failure archives preserved.

Sequential archive/removal command hit tool120s timeout after original image1 completed and
current image2 partial removal. No computation was targeted; no live retirement Docker CLI/
process remained. Partial state/log/archives retained. Resume independently inspects the exact
remaining117 owned stopped current IDs, records72 already-absent previously owned IDs and bulk
normal-rm those117 only; exact labelled empty network/private volume identity checked then
removed, **exit0** (`retirement-resume.log`, `retirement-resume-commands.json`). Original84 clients/
service and current189 clients/service plus respective network/volume now retired; no iteration11
labelled container/network/volume remains. Images/all nonsensitive evidence retained. No force/
prune/prefix deletion/arbitrary historical scratch disposal/coordinator fixture operation.

## Postpublication test-only finite-peer-EOF follow-up

Coordinator source review finds a genuine NEW TEST-helper ownership defect: wire().serve() used
empty recv results without EOF checks for BOTH partial request-header/body loops, permitting
infinite immediate empty reads after peer close despite socket timeout. This finding is NOT the
initial Windows old-reader failure's cause or a runtime defect. Initial SHA/failed CI remain.

Authorized narrow change ONLY `tests/python/test_floci_http.py`: each loop returns on empty EOF
through finally-owned socket/listener close; two real loopback peers send partial header/body
then close, and explicitly join/assert the exact owned fake-service thread is stopped. No
runtime/example/profile/timeout/budget/coverage/old-test change. Focused **205 tests exit0/15.08s**;
Black/whitespace pass. ALL prior204 source hashes except this ONE test file match, including all
16 runtime/image artifact bytes. No new installed gate necessary or claimed.

EOF-only stable `wire-eof-standard` **exit0**:1577 Python/seven C/3536 Python/unchanged native/
binding624/141CLI. Only AFTER it completed, coordinator authorized DISTINCT TEST-only old-reader
failure diagnostics: `test_exchange_progress_process.py` only import+@after_cleanup, new
`concurrent_reader_diagnostics.py` and eight regressions in `test_concurrent_reader_diagnostics.py`.
Original owning function BODY/cleanup/signals/deadlines/assertions unchanged. Decorator captures
failure only AFTER existing finally cleanup, runs once and bare-reraises original same object/
type/args/traceback. Fixed exact-owned concurrent-errors-0/1 tails (512 bytes each), cached
returncodes and ready/release existence only; escaped note bounded8192, resolved outside/symlink
paths reject. NO process methods/poll/wait/signals, environment/native/record dumps, retry/repair.
Diagnostic IO/allocation/note failures cannot mask original. Synthetic compile filenames are
absolute OWNED tmp paths, not phantom maintained-source coverage entries.

Focused aggregate **225 tests exit0/34.88s**; fresh stable `reader-diagnostics-standard` **exit0**:
**1585 Python** (207.92s), seven C,3536/3536 Python, unchanged native1681/132/1562 all100%,
binding zero errors/existing624 contexts and141CLI. Black/whitespace pass. Exactly FOUR test
files differ from accepted publication (EOF1 separate from diagnostics3); all16 runtime/image
artifact bytes and all other original204 files unchanged. No new installed gate needed/claimed.

ALL **206 maintained sources** frozen at `build/iteration11/followup-source-freeze.json`,
SHA256 `83bf724c84ba30093568f252cf11dce0d8ee95204ef5a20c15d14cec9bcf4056`.
Separate proposed diffs `wire-eof-proposed.diff` and `reader-diagnostics-proposed.diff` retained.
Worker FREEZES all source/build use and explicitly RELEASES BOTH build/check AND build/coverage
for independent aggregate follow-up review. No follow-up staging/commit/push before acceptance;
EOF and diagnostic changes must remain distinct commits. Initial9ed CI failure persists in
history, no same-SHA rerun. Diagnostics may expose a future old-reader cause; **NOT an established
fix or diagnosis**. Final all-six exact-SHA CI success still required; old Windows causes UNKNOWN.
## Follow-up independent acceptance and separate focused publication

Coordinator independently reviews exact EOF1/diagnostic3 deltas, passes **225 tests/35.30s**,
checks ALL206/four delta hashes/exact file set stable and reads worker final1585 full-v exit0.
Native/runtime/image16 bytes unchanged; all owned fixture resources independently absent.
No outstanding finding; both builds/source returned and separate focused test commits/one
normal aggregate push explicitly authorized. This is postfix acceptance, not a diagnosis
of initial Windows reader rc1 or earlier UNKNOWN causes.

Worker verifies every accepted206 source hash, clean9ed baseline index/master/existing origin
and stages ONLY EOF test file, then ONLY three diagnostic files, checking staged bytes against
freeze and full staged diffs/whitespace. EOF commit **`4bb0bfa`**,one file/+32/-3; diagnostic
commit **`640cabb05dd9426323069e816621dcbc0c829ae0`**,three files/+288. NORMAL PUSH ONCE
**exit0** after both. Runtime/examples/fixtures/wheels/profiles/old test body unchanged;
no ignored build/data/design/native/workflow changes staged. Tree/index clean and remote
master exact640cabb. Initial9ed plus two test-only followups are preserved, no amend/rerun.

Initial exact-SHA lookup briefly returned no run, then confirms sole automatic push
[CI40913866835](https://github.com/micha/dml/actions/runs/40913866835),attempt1, exact640cabb.
## Final exact-SHA success and stop

[Final automatic CI40913866835](https://github.com/micha/dml/actions/runs/40913866835),attempt1,
completes **SUCCESS for exact `640cabb05dd9426323069e816621dcbc0c829ae0`**, all SIX jobs.
Finite900s direct watch **exit0**, completed exact-SHA JSON/full all-job logs/logexit0 and sole
push workflow list verified; no manual/same-SHA rerun or release workflow. Final aggregate's
first attempt passes, **NOT a first-publication-green claim for the turn**. Initial9ed failed
CI/EOF finding/old-reader UNKNOWN traceback and all original private failures remain recorded.

| Final job | C executables | Python results |
| --- | --- | --- |
| Strict Linux | 7 | 1585 passed,2 warnings;167.27s |
| Linux aarch64 | 7 | 1585 passed,2 warnings;129.62s |
| Linux x86_64 | 7 | 1585 passed,2 warnings;134.71s |
| macOS arm64 | 7 | 1581 passed,4 existing skips,2 warnings;121.85s |
| macOS x86_64 | 7 | 1581 passed,4 existing skips,2 warnings;493.02s |
| Windows AMD64 | 7 | 1579 passed,5 existing skips,2 warnings;228.88s |

Existing device/pipe/POSIX credential-parameter skips retain original platform scope; no
meaningful failed case skipped, deadline/gate/profile reduced, workflow changed or runtime
retry added. CI strict uses informational **-c**, not worker/coordinator local **-v**/memory
or mandatory actual installed Batch evidence. Host3536/3536 statements are not every Python
branch/installed process memory instrumentation. Native/exclusion/finalizer/auth/capture/
security/ephemeral-B/physical-host/platform/restart/deadline/mutation limitations remain.

Final Windows verbose log explicitly PASSES old caller-prior/concurrent-reader case and old
async/caller stories. This verifies current behavior, **NOT why earlier reader returned1**
or old story causes; those stay UNKNOWN. Diagnostic notes were not exercised by an actual
failure in the final run. The EOF helper fix is a separately confirmed test ownership defect,
not inferred cause of initial Windows failure. All16 runtime/native/CLI image artifacts remain
unchanged across test-only followups; no new installed-runtime capability implied by CI.

Final evidence: `build/iteration11/final-ci.json`, `final-ci-full.{log,err,exit}`,
`final-runs.json`, `followup-watch.{log,exit}`. Initial complete/failed logs, staged/proposed
EOF and diagnostic diffs, all source/artefact inventories, actual normal/private/loss/bootstrap/
coordinator archives and exact retirement records remain separate retained evidence.

At final checkpoint, implementation **tree/index CLEAN**, existing remote master exact640cabb,
ALL206 accepted aggregate source hashes stable. Publication is33-file9ed2270, one-test EOF
4bb0bfa, then three-test diagnostic640cabb, **36 unique turn files**, no published amendment,
design commit/new remote/force/tag/release/package publication. Coordinator independent initial
full-v/custom380 plus postfix225 remain attributed independent evidence, not worker reruns.

All original/current/coordinator owned fixture containers/networks/volumes are archived and
identity-checked retired after exact stopped job/client/namespace proofs. Images/all nonsensitive
B/packets/objects/source/closure/wheel/failed+final evidence retained, no prune or historical
scratch disposal. Service-owned retirement stays separate from recorded computational cleanup.

**COMPLETE AND STOPPED.** RESULTS finalized. No further source/runtime/build/test/staging/
commit/push/CI polling/rerun/fixture operations/design checkpoint/additional worker/global/cloud
change/release/package publication/later feature turn. Coordinator owns final REVIEW/
COORDINATION/design reconciliation; final success never erases initial uncertainties.