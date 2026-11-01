# Iteration 10 independent coordinator review

Status: **bounded implementation, independent review and final publication/CI complete**
through `099d156`; all six final exact-SHA jobs succeed. Work is complete and stopped.
Two earlier unchanged Windows story failure causes remain unknown; final pass is not their
fix/diagnosis. [RESULTS.md](RESULTS.md) owns worker choices/evidence; [COORDINATION.md](COORDINATION.md)
owns assignment/build/fixture gates. No later feature turn or release/package publication.

## Reviewed surface and contract

Reviewed the frozen **24-file** implementation surface: three runtime modules, endpoint
example, five new host test files, fixture/support/gates, owning/navigation documents and
coverage catalog. Every SHA256 in `../dml/build/iteration10-owned/source-freeze.json` remains
unchanged before/after independent validation. Existing local diagram/test commit `a94e6f5`
is preserved/accounted for as an unchanged ancestor of eventual normal push.

- Public exchange read-only inspector shares strict packet parsing and owned-bundle history
  validation with receive; returned refs/nested completion refs are None. Validation scratch
  closes/cleans before success or A publication. No private cross-layer role/native/job codec.
- Saved SSH configuration composes public exchange handle serialization, with strict bounded
  operational metadata; save/load never connect/read B/dispatch/serialize live process state.
- Start invokes the same fixed foreground execute once with shared pre-Popen dispatch guard.
  Separate application-owned SSHLaunch returns without authentication/readiness/computation wait.
  Timeout/uncertain wait retains process/streams, never automatically kills this connection.
  Known local disposition closes streams even on output/status/seek/read/close errors; repeated
  wait preserves the cached result/error. Status remains transport-only.
- Fixed nonexecuting observe composes public coherent exchange selection/pinned export; exact
  bootstrap/progress framing carries evidence, not trusted done/success claims. Remote scratch
  disposal precedes reply; host independent expected/history validation and scratch disposal
  precede final immutable packet allocation/receipt-last publication. Observation-client loss
  ownership stays distinct from execution connection and uncertain remote descendants.
- Exact Cq/Q/T/P/U/F, original synchronous/local paths, unchanged caller heads/request refs,
  unknown versus failure, provisional U and separate cleanup survive. Existing authoritative
  receive atomically imports under explicit create-or-same-target refs; no implicit adoption.
- Diagram/native review: no changed LMDB entities/key families/packed fields/hash inputs or
  displayed boundaries. Saved SSH/owner/transport/fixture files remain external application
  state, not new native entities. Diagram remains unchanged; six focused checks are in the
  passing suite. No real-browser audit, native primitive/schema/version/old-spec/workflow change.

## Monitoring feedback and fixes

Early runtime review required explicit postreap seek/read/stack-close/repeated-wait errors,
uncertain wait owner retention, setup/owner/spawn allocation and mixed dispatch guards. Worker
added meaningful regressions without exclusions/gate weakening.

Coordinator found an actual fixture error-path ownership gap: normal finally waited only for
apparently live clients and could skip A restoration/writer checks when waiting raised;
concurrent observation readers could be dropped after another client's failure. Worker fixed
unconditional owner disposal, nested independent gate-release/A-restore/writer checks, original
error preservation and explicit retained owners on uncertainty, plus all acquired reader
ownership. Private regressions and rerun actual gate pass. This was fixture assurance work,
not a production outcome/lifetime fix or success-only cleanup claim.

Accepted documented example refinement: normal trusted gates/binding are finite, while uncertain
owner reaping retains the application through bounded repeated waits for external investigation.
That blocker retention can be indefinite; it is not a detached service or guaranteed deadline.

## Fresh independent standard validation

After explicit source freeze and release of **both** shared builds, coordinator ran:

```sh
cd ../dml
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration10-coordinator-standard.{log,exit}`: **exit0**, **1357 Python tests**
(188.34s), **seven C executables**, Python **2828/2828 statements**, native retained
**1681/1681 lines,132/132 functions,1562/1562 outcomes**. Binding memory workload passes
zero unsuppressed errors/existing624 runtime contexts; **141 CLI Valgrind processes** pass.
No new coverage exclusions/source omissions/suppressions/weaker thresholds. Intentional
existing runpy warning is not a skipped/failing gate. Host statement coverage is not every
Python branch or installed SSH/helper/child instrumentation. Existing native exclusions,
CPython suppressions and unsupported foreign-last-owner finalization remain qualified.

Independent whitespace and **244 local Markdown file/anchor targets** pass; all24 source
hashes remain unchanged. Packaging contains runtime/core/CLI/types, not tests/private hooks/
credentials. No coordinator implementation edits or staging.

## Separate independent installed workflow

Coordinator created a **separate offline installed venv**, using existing bare Python and
packaging pip with `--no-index --no-deps` reviewed wheels; no build/bootstrap/download.
`/tmp/dml-iteration10-independent.py` runs from `/tmp` with PYTHONPATH unset, no project-test
imports. Evidence: `/tmp/dml-iteration10-coordinator-{install,probe}.log`, `probe.exit`, and
`/tmp/dml-iteration10-independent-story/summary.json`. **178 independent checks, exit0**, plus
embedded computational-child assertions. No workflow assertion failure or production fix.

Custom captured source computes **13+29=42**, using explicitly declared remote gates controlled
out of band, not worker's maintained addition source. Three normal actual fixed SSH streams:

- Fresh bootstrap clients allocate no packet; exact caller Q is staged before dispatch.
  A/input artifacts are offline during launch/progress, saved control identity remains usable.
  Mixed dispatch repeats reject; execution timeout retains live owner/streams.
- Fresh short-lived installed clients retrieve P/U/F. Same exact Q/T/initial fields, only new T
  relative to Cq, exact P/U/F ordered parents and working/done boundaries are checked. Failure
  exits23 after U, retaining publication as evidence with separate cleanup. Two matching jobs
  have distinct Q/T and equal result42.
- Independent breadth-first public traversal compares **every typed object/packed byte/all
  parents**, including composite-only children, across remote B, bundle-validation store and A.
  No transfer-private traversal or CLI-prefix oracle. Recorded F is retrievable without original
  synchronous output/receipt; old selected packets remain independent evidence.
- Owners explicitly reap; endpoint stops only after independent writer-absence checks. Fresh
  installed packet-only receive/idempotent repeats work offline, preserve advanced main/sentinel/
  never-started/submission/request refs and all prior reachable bytes, and do not copy B refs.
  P-ref-to-F conflicts without physical A mutation; independently validated second matching-Q
  packets with rewritten transport claims reject at inspector/receive without A writes.

Independent artifact audit compares **all13 wheel package files** (eleven core package plus
CLI package files), including extension/native executable, against separate coordinator host,
fixture host and stopped container installation **every byte**. All match. The stopped fixture
has empty mounts and approved host-network profile, with no32769 listener; B/keys/evidence
remain retained for explicit retirement after archive. This is same-machine filesystem/runtime/
SSH separation, not network-namespace or second-host isolation.

## Worker evidence and assurance limits

Inspected worker actual gate/support/RESULTS. Worker final installed progress **393 checks**
and separate synchronous regression **271 checks** include actual auth/unknown/changed keys,
otherwise typed-complete expected-Cq/wrong-T-to-matching-Q P/U/F, original production4MiB+1
post-F overflow/no done packet, remote one-shot guard, fresh clients/concurrent readers and
full typed-byte/offline-reception oracles. Coordinator did not independently rerun every
fault/profile/private barrier: those remain distinguished worker evidence.

Independent full suite reruns observed-packet late rollback after successful **genuinely new
actual-A puts/readback**, raw/different refs/substituted consuming-commit errors, existing real
small-map and pre/post-A-storage-commit loss tests. Host transport substitution is not actual
installed SSH evidence; scratch/preexisting Q writes are not miscounted as new A writes.
Comparable-map/full logical and physical-byte rollback oracles remain enabled. Simulated
commit EIO is not physical disk/power-loss proof.

Private remote readiness/pre-spawn/after-actual-reap/post-F/interrupted-observation barriers
are explicitly substituted commands, not installed fault hooks/normal helper branch coverage
or arbitrary hard-owner-loss survival. No live computational child sacrifice. Eleven selected
worker negative probes produce intended test failures; unavailable Python mutation tools remain
a gap, not a framework mutation score. Installed-process coverage/memory, other Python/OS/SSH/
libc/physical-host portability, sandbox/security/full capture/scientific truth/global exactly-once,
detached supervision/power-loss and hard disk/RSS/deadline guarantees are not established.
Informational CI `-c` does not replace local `-v` or mandatory actual installed evidence.

## Precommit audit correction pending

Worker's complete staged-diff audit found progress gate's changed-host fixture writes literal
backslash-n rather than a newline. Parsing that retained file with ssh-keygen fails255; therefore
its async changed-key255 was **malformed/unknown-host evidence**, not genuine changed-key proof.
The separate synchronous271 gate has a correct newline and genuine changed-key evidence.
No production behavior or other progression evidence changes. No commit/push yet.

Coordinator pauses publication, approves focused support/test newline/parser/fingerprint regression
and fresh protected owned credentials with unchanged reviewed cached image/runtime (old fixture
already archived/retired). Require actual async changed-key verification, updated qualifications,
appropriate stable checks and explicit revised freeze/release before independent postfix acceptance.
Earlier acceptance describes the then-reviewed surface, not permission to push the known flaw.

Worker final two-file correction writes deterministic UTF-8/LF bytes, parses/fingerprints both
public and known-host files before SSH, compares against actual host public fingerprint and
requires dedicated `REMOTE HOST IDENTIFICATION HAS CHANGED`/offending-key diagnostics. A
Windows text-conversion model fails before binary-write fix and passes after; no runtime change.
Worker final stable `-v` passes **1361 Python/seven C**, unchanged2828/2828/native/memory gates;
full actual installed progress gate rerun passes **396 checks** with genuine changed-key proof.
Original393 gate qualification remains visible; synchronous271 genuine proof stays distinct.

After revised freeze/release, coordinator independently reviews exact124-line two-file delta,
runs **168 progress/launch/example/fixture tests**, exit0 (25.10s), and verifies all24 revised
hashes stable with **only those two files changed**. `/tmp/dml-iteration10-coordinator-postfix.{log,
exit}`. Independently parses retained corrected changed-host/public files with ssh-keygen,
confirming matching valid public fingerprints; checks final dedicated-diagnostic log and
stopped/empty-mount/no-listener fixture. This is independent parser/postfix validation plus
reviewed worker actual SSH evidence, not a second full installed workflow rerun.

No outstanding finding remains. Coordinator accepts the focused correction, returns both
builds/fixture and reauthorizes focused24-file normal commit/push/exact-SHA CI. Runtime remains
identical to independent full standard/178-check installed evidence above. Archive/retire only
stopped owned fixture; preserve chronological failure evidence. No commit/push yet claimed.

## Initial publication and Windows CI finding

Reviewed24-file slice normally committed/pushed as
**`fdba76e9820f6bf03a6902c46d3eed603ea84568`**, +2825/-74, preserving unchanged user-authorized
`a94e6f5` ancestor. Coordinator verifies surface, clean tree/index and matching remote master.
Owned fixtures/private keys archived/retired by worker after stopped-writer checks; image and
nonsensitive evidence retained. No force/new remote/release/manual workflow.

[Initial exact-SHA CI40785659063](https://github.com/micha/dml/actions/runs/40785659063)
finishes **five jobs successful/Windows failed**; independent finite watch exits1, completed
JSON/full logs retained at `/tmp/dml-iteration10-coordinator-{ci.json,ci.log,ci.err,watch.log,
watch.exit,runs.json}`. Actual Windows traceback identifies **one new test-harness failure**:
progress example's private in-process prepare test supplies `/opt/dml/bin/python` to host
local binding validation; native Windows isabs correctly rejects the POSIX interpreter.
Windows1354 tests pass/five existing skips. No old caller-story failure in this run.

Coordinator requests focused test-only host-binding adapter/regressions while keeping the
public SSH endpoint POSIX and production/local profiles unchanged; no skip/threshold weakening,
speculative runtime change or CI fix publication before review. Same-machine Linux installed
SSH evidence above is not a Windows caller-to-POSIX portability claim. Final exact-SHA all-job
success remains outstanding.

## Reviewed CI correction

Worker proposes one-test-file **+57/-1** host-binding adapter: only the private in-process
example binding matching the POSIX endpoint is translated to host sys.executable; endpoint
remains POSIX, other explicit interpreter preserved. Two semantic POSIX/Windows-spelling
regressions also retain public Windows-as-POSIX rejection. No runtime/example/fixture/local/
package/workflow/skip/profile/threshold change or new installed/Windows remote capability claim.

Worker fresh stable `-v` passes **1363 Python/seven C**, unchanged2828/2828/native/memory gates;
170 focused tests pass. After explicit freeze/release, coordinator reviews exact one-file diff,
independently passes **33 progress/fixture/old SSH/caller example tests**, exit0 (4.51s), verifies
all24 CI-fix hashes stable/only that one file changed and whitespace. Evidence:
`/tmp/dml-iteration10-coordinator-ci-postfix.{log,exit}`. No outstanding finding: coordinator
accepts test-only correction, returns both builds and directs focused normal fix commit/push
and new exact-SHA automatic CI. Initial failure/cause remains visible, not first-run success.

## Second publication and unchanged old-story failure

Accepted one-test-file correction normally committed/pushed as
**`6f063d94a9bf724b314f89597a78a86ad2824b9e`**. Coordinator verifies one-file surface/clean
checkout/index/matching remote. [Exact-SHA CI40787706542](https://github.com/micha/dml/actions/runs/40787706542)
attempt1 finishes **five jobs successful/Windows failed**; independent watch exits1. The new
progress prepare/adapter cases explicitly pass. Sole failure is **unchanged prior asynchronous
example**: trial3 coherent discovery completes, then pinned export's reopen of worker.dml yields
native storage_error/ENOENT2. Windows1356 pass/five skips; initial corrected failure is absent.
Full JSON/logs/watch retained under `/tmp/dml-iteration10-coordinator-final-*` (attempt1).

Neither trace nor artifacts establish why this open failed: no selected phase/worker/child/B
artifacts available. It is not diagnosed as gate expiry, a new SSH regression or a native fix.
Read-only source/process/cleanup review plus Linux repetitions cannot reproduce native Windows.
Coordinator authorizes **one failed-job-only same-SHA CI rerun**, retaining attempt1 evidence and
UNKNOWN cause, not speculative runtime/test changes, retry inside tests, gate increase or a new
feature. Final successful CI remains outstanding; later pass must not be called a diagnosis/fix
of this prior failure or first-run green. Recurrence would require scoped diagnostic proposal.

## Authorized diagnostic rerun and next bounded diagnostic scope

One failed-job-only rerun of CI40787706542 at **unchanged exact6f063d9**, attempt2, finishes
five successes/Windows failure; independent watch exits1. Full attempt2 JSON/logs/watch/runs
retained at `/tmp/dml-iteration10-coordinator-rerun-*`. Old async ENOENT case and new prepare
adapter pass. **Different unchanged caller-story** now fails `launch.wait(timeout=15)==0` after
P/U/F retrieval; no worker returncode/logs explain why. Windows1356 pass/five skips. No second
rerun submitted or source changes by this diagnostic verification. Neither failure is diagnosed
by another passing case. Linux five old-async repetitions pass, not Windows reproduction.

Read-only native review notes LMDB Windows named-lock OpenMutexA can also yield error2; thus
ENOENT from mdb_env_open is not proof the B directory disappeared. This is a plausible error
source, not captured diagnosis. Original two old-story causes remain UNKNOWN.

Coordinator authorizes narrow **test-only failure diagnostics/regressions**, preserving/rethrowing
original failure with bounded owned worker/path/phase/outcome evidence, no execution/retry/ref
repair/timeout/gate increase or sensitive/unbounded payload output. Review/freeze/validation before
diagnostic publication; no production/example/local/native change or speculative fix. Final
successful exact-SHA CI remains outstanding.

## Reviewed test-only failure diagnostics

Reviewed three test files: shared harness wraps main once (caller harness already reuses it),
new diagnostic helper attaches at most8192 escaped bytes then bare-reraises original failure,
and nine regressions. Only fixed synthetic owned workspaces/files, bounded512-byte worker log
tails, phase/selected receipt and owner poll status are collected. Public small B outcome/cleanup
inspection occurs only with known local owner disposition. No environment/raw MDB dumps/serialized
scratch traversal/dispatch/import/ref write/repair/wait/signal/retry/gate change. Capture/native/
allocation errors cannot mask original. Diagnostic read is evidence, not structural authority or
another attempt. It may expose recurring failure; it is not a runtime fix/established diagnosis.

Coordinator caught synthetic compile co_filenames resolving to phantom root coverage sources.
Worker's first standard1372-test pass ended **exit1 at coverage**, not a full green gate.
Synthetic regression filenames changed only to absolute owned pytest temp paths outside source
profile, not aliases to maintained examples or new coverage omissions. Final worker stable `-v`
passes **1372/seven C**, unchanged2828/2828/native/memory gates. After freeze/release coordinator
independently passes **44 diagnostic/old-async/caller/progress/fixture tests**, exit0 (5.45s),
verifies all27 aggregate frozen hashes and **all prior24/runtime/examples unchanged**/whitespace.
`/tmp/dml-iteration10-coordinator-diagnostics-postfix.{log,exit}`. No outstanding finding: accept
focused test-only diagnostic commit/normal push and new exact-SHA CI; return both builds. No
further same-SHA rerun authorized by this acceptance; original unknown failures stay recorded.

## Final publication, CI, retirement and stop

Reviewed test-only diagnostic enrichment normally committed/pushed as
**`099d156fb49f81a7da0683898189a85c1172988c`**, three files/+511/-1. Coordinator verifies
surface, clean implementation tree/index/matching remote master and all27 aggregate accepted
hashes. Runtime remains unchanged from independent full standard/installed178-check evidence;
publication consists of initial24-file `fdba76e`, one-test correction `6f063d9`, diagnostic
three-test-file `099d156`, preserving unchanged user-authorized diagram ancestor `a94e6f5`.

[Final exact-SHA CI40791372333](https://github.com/micha/dml/actions/runs/40791372333)
completes **success in all six jobs**, attempt1. Coordinator direct finite watch exits0,
completed exact-SHA jobs JSON/full logs/sole automatic push run verified; no final manual
rerun/release. Seven C tests pass everywhere; Linux/strict1372 Python, macOS1368/four existing
skips, Windows1366/five existing skips (one POSIX literal-backslash credential parameter remains
inapplicable to native Windows separator semantics). CI strict informational `-c` reports
2828/2828, distinct from worker final local `-v`1372 and coordinator independent full/postfix/
installed evidence. No skip/profile/gate relaxation.

Final Windows verbose log explicitly passes old async story, old caller story and fixed new
progress prepare case. This verifies current CI, **not a diagnosis/fix of earlier old-story
ENOENT or post-P/U/F worker-status causes**. Those remain UNKNOWN; no failure occurred to
exercise new diagnostic notes in final run. Original failed runs/one authorized same-SHA
failed-job rerun, confirmed new harness fix, precommit malformed-key and phantom-source
regression defect remain recorded, not first-publication-green claims.

Final evidence `/tmp/dml-iteration10-coordinator-diagnostic-{ci.json,ci.log,ci.err,log.exit,
watch.log,watch.exit,runs.json}`. At this checkpoint implementation is clean and remote master
matches099d156. Worker archived original/fresh stopped owned `/work`/B histories/provenance,
then retired only labelled stopped container/private keys; coordinator verifies no owned
iteration10 container/32769 listener. Image/nonsensitive source/closure/wheel/packet/B evidence
retained, no global prune. Retirement is separate from recorded computational cleanup.

Worker directed to finalize RESULTS only and stop all runtime/build/test/staging/commit/push/
CI/rerun/fixture activity. Bounded Iteration10 is complete and stopped for user review. No
additional worker/design checkpoint commit/push/new remote/force push/release/tag/package
publication/cloud/global tooling/detached supervision or later feature turn.

## Acceptance and publication gate

No outstanding within-scope finding remains. Coordinator accepts the bounded frozen slice,
returns both builds and stopped fixture to worker, and directs focused inspected24-file
commit/normal push, accounting for unchanged existing `a94e6f5` ancestor. Publication completion
requires successful final exact-SHA automatic CI; focused CI corrections need review/appropriate
validation. Archive required B/evidence and retire only stopped labelled owned fixture/private
keys; retain image/nonsensitive evidence, no global prune. No additional workers/new remote/
force push/tag/release/package publication/cloud/global tooling or later feature turn.
