# Iteration 9 independent coordinator review

Status: **bounded implementation, independent review and final publication/CI complete**
through `29ed39b`; all six exact-SHA CI jobs succeed. Work is complete and stopped.
The existing window-2 worker implements; coordinator independently reviews and validates.
[RESULTS.md](RESULTS.md) owns worker evidence/choices; [COORDINATION.md](COORDINATION.md)
owns assignment/build/fixture gates. No later feature turn/release/package publication.

## Reviewed surface and contract

Reviewed the frozen 22-file surface, public exchange reader/install inventory, SSH client/
fixed helper, maintained example, four host test files, private fixture/loss/integration
support and owning/navigation/coverage docs. All 22 SHA256s match
`../dml/build/iteration9-bare/source-freeze.json` before and after independent validation.
Existing local diagram commit `f7113d7` is preserved unchanged and explicitly accounted
for as an ancestor of eventual normal push, not Iteration 9 runtime work.

- Runtime composition uses public exchange/local/transfer authorities, no Docker dependency,
  private cross-layer DML calls or duplicate native/job/role codec. Strict public job reader
  preserves original local fresh-Q/caller-Q modes; new SSH path requires pinned caller Q.
- Endpoint/config profiles, independent expected, owned bytes, POSIX remote quoting, fixed
  command/actions, strict host-key/public-key/no inherited proxy/config/forwarding settings
  and binary exact-length/EOF framing align with implemented docs.
- Stage creates files only; pre-Popen local guard survives uncertainty, remote one-shot guard
  stays independent. Fetch is nonexecuting transport candidate; authoritative exact-Q/history/
  outcome/cleanup validation precedes atomic explicit-ref A import. No caller head/ref adoption.
- File-backed stream/wait ownership avoids blocking pipe writes/unread stderr. Failed local
  shutdown retains actual acquired Popen for caller reaping; it is not a remote PID/recovery
  guarantee. Spawn/filesystem/log disk and remote process lifetime remain qualified.
- Diagram review: no new native key/entity/body/hash/relationship or changed displayed boundary;
  external SSH/control/fixture files do not belong as native entities. Diagram unchanged; its
  four focused checks remain in the fresh passing suite. No old-spec/native/local/transfer/
  CLI/workflow/schema/version change.

## Feedback and fixes during implementation

Coordinator required exact-Q typed-complete association rejection, actual host-key/auth/
quoting/guard/production-profile evidence, endpoint-offline installed receive, independent
all-typed/every-byte/every-parent oracles and genuine actual-A-new-put rollback distinctions.
Reviewed meaningful error paths rather than accepting statement percentages alone.

Early fixture review identified private barrier cleanup only on expected paths; worker
changed it to finally-release/disposition checks on catchable failure paths and blocker/
retention rather than stopping unknown live writers. Coordinator also required actual remote
repeat guard independent of local guard. Worker strengthened those cases and documented them.
Local shutdown-retained-owner refinement is accepted and tested/documented.

Bridge connectivity prerequisite failed without host firewall/service changes. User explicitly
approved loopback-only host networking. Offline copied cached bare Nix runtime fixture is within
scope, with no pulls/bootstrap/global changes/mounts. Coordinator permitted stopped owned
fixture replacement after archive when audit found unnecessary development-Python dependencies.
Final 36-path/~240MiB image is distinct from prior 46-path tools-env fixture; no erased failure
history or network-namespace/second-host isolation claim.

## Fresh independent standard validation

Coordinator exclusively owned both shared builds after explicit worker freeze/release:

```sh
cd ../dml
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration9-coordinator-standard.{log,exit}`: **exit 0**, **1,189 Python tests**
(160.44 seconds), **seven C executables**, Python **2637/2637 statements**, retained native
**1681/1681 lines, 132/132 functions, 1562/1562 outcomes**. Binding memory passes with zero
unsuppressed errors/existing 624 runtime contexts; **141 native CLI Valgrind processes** pass.
No source omission/exclusion/suppression/threshold weakening was added. Intentional runpy
RuntimeWarning is present, not a skipped or failing gate. Host statements are not all Python
branches or installed SSH/container/child instrumentation. Existing native exclusions,
CPython suppressions and unsupported foreign-last-owner finalization remain qualified.

Independent `git diff --check` passes; 179 changed implementation Markdown file/anchor targets
pass. Source/install inventory has no credentials/test/image/private hooks packaged. Native
and runtime files remain focused; no unrelated work is staged by coordinator.

## Separate independent installed workflow

Coordinator created a separate offline installed venv from final reviewed wheels using
existing bare Python and packaging pip, no build/bootstrap/download. Application probe
`/tmp/dml-iteration9-independent.py` runs with PYTHONPATH unset from `/tmp` against that
installed runtime, not checkout imports. Evidence:
`/tmp/dml-iteration9-coordinator-{install,probe2}.log` and `probe2.exit`.

**177 explicit independent checks, exit 0**, plus embedded child assertions, using new
workspaces/custom captured source computing **19+23=42**, not worker's maintained addition:

- Independently verified stopped fixture identity, empty mounts, approved host networking,
  installed source bytes and no checkout package path. Restarted only the retained endpoint.
- Stage-only exact files/no B; A and prepared input artifacts offline during actual fixed
  installed SSH execution; child asserts configured `/opt/dml/bin/python` and installed
  package/native provenance. Repeated local dispatch rejects; no automatic relaunch.
- Two matching Qs create distinct Q/T and equal result; independent nonzero-after-publication
  failure retains evidence, missing declared child interpreter records launch failure.
- Copied B only after owned writers were absent. Independent breadth-first typed traversal
  compares every record byte/all parent commits, including composite-only descendants, with
  incoming bundle rows and eventual A. Checks exact imported Q reservation, Cq/P association
  and only one new T relative to Cq.
- Stopped endpoint only after no entry/helper/private writer remained; B retained. Offline
  installed receive and explicit idempotent repeat preserve independently advanced main,
  sentinel and submission/request refs and old bytes. Wrong matching-Q token/base-rewritten
  packet rejects before any A physical bytes change.

First probe completed its normal workflows but failed its own too-narrow expected exception
class at the final foreign-Cq packet rejection: existing authoritative receive correctly
raised native NotFoundError rather than ExchangeError. Corrected only the private oracle to
accept documented DmlError and reran the entire workflow in fresh workspaces, yielding 177
checks. This was not a production fix or claimed association-specific wrong-Q test. The
worker/default typed-complete expected-Cq/T-to-wrong-Q case separately exercises that stronger
association rejection. Initial `/tmp/dml-iteration9-coordinator-probe.log` remains evidence.

Coordinator additionally copied the stopped container's installed package and independently
compared **all 11 wheel package artifacts**, including extension/native executable, against
remote and separate host installation **every byte**. All match. All 22 frozen source hashes
still match. The same endpoint remains stopped, empty mounts, with B/evidence retained until
explicit fixture release/retirement.

## Worker evidence and assurance qualifications

Inspected worker normal/private gate support and RESULTS; final installed gate **271 checks**
includes actual strict unknown/changed-key/auth SSH255, quoted helper/root without injected
side effects, remote repeat start counter, genuine unchanged 4MiB+1 post-F export overflow,
unknown P/U and closed-file response/fetch loss, endpoint-offline fresh receivers and stronger
otherwise typed-complete wrong-Q association rejection. This is worker evidence, not a claim
coordinator independently reran every fault/quoting/profile gate.

Default fresh coordinator suite independently reruns fetched candidates with actual new-A
successful puts/readback before late ref/raw-ref/substituted consuming-commit errors, real
small-map failure and actual pre/post-A-commit process loss. Transport is private in-process
substitution there; actual A storage/child effects are real. Comparable-map/compact exact-byte
oracles preserve physical/logical whole-batch rollback; no oversized diagnostics/boundary
reduction. Native consuming-commit EIO is not real disk/power failure.

Private remote commands pause before spawn or after actual child reaping; they are not normal
installed helper branch coverage or arbitrary hard-owner-loss/process-tree assurance. No live
computational child sacrifice. Nine worker selected negative oracles each produce intended
test failure; unavailable Python mutation tools remain a gap, not a mutation score. Installed
process coverage/memory, other Python/OS/SSH/libc/actual second-host portability, sandbox/
security audit, full environment capture/scientific truth, global replay/exactly-once,
remote supervision/power-loss and hard resource quotas are not established. Informational
CI `-c` will not replace local standard `-v` or actual installed fixture evidence.

## Acceptance/publication gate

No outstanding within-scope finding remains. Coordinator accepts this bounded frozen slice,
returns both builds to worker and directs focused inspection/staging/commit/normal push of
only reviewed 22 files, explicitly including the existing unchanged `f7113d7` ancestor.
Final acceptance of publication still requires exact-SHA automatic CI success. CI fixes must
remain focused/reviewed/appropriately validated; no new remote/force push/tag/release/package
publication/additional worker or later feature turn.
## Initial publication and reviewed Windows test correction

Reviewed initial 22-file slice is normally committed/pushed as
`f63ac75fa03f78ce74c4ce8e3ff041a937a792a9`, preserving/accounting for prior diagram ancestor.
Coordinator verifies commit surface/clean tree/remote SHA. Initial exact-SHA automatic
[CI 40699187591](https://github.com/micha/dml/actions/runs/40699187591) completes **failure**:
five jobs succeed, Windows fails three tests. Coordinator finite watch exits1; completed
JSON and original sanitized/full logs remain retained. No first-run-green claim.

Two new SSH example test-harness failures are confirmed in actual Windows traceback:
retargeting public POSIX `remote.python` to Windows `sys.executable` correctly rejects before
story execution. Accepted one-test-file correction keeps the endpoint POSIX and maps only
the private in-process example binding seam to actual host interpreter. POSIX/Windows spelling
regressions preserve another explicit interpreter and production Windows-as-POSIX rejection.
No runtime/example/fixture/native/gate/skip/workflow change, nor new installed-runtime claim.

Worker stable postfix standard passes **1191 Python/seven C**, Python2637/2637 and unchanged
native/memory/141CLI gates. After explicit freeze/release, coordinator independently runs
SSH plus caller-example **104 tests**, exit0 (7.99 seconds), verifies all22 combined original/
fix hashes and whitespace. `/tmp/dml-iteration9-coordinator-postfix.{log,exit}`. No outstanding
fix finding; coordinator accepts one-file +63/-5 correction, returns both builds and directs
focused test-only commit/normal push and new final exact-SHA CI verification.

Third initial failure is unchanged prior caller example: handle2 requests publication but
observes completion. Actual timestamps indicate early (~0.84s whole-test) failure, not evidence
of 15-second gate expiry. Child reason/artifacts are absent, so cause is **unknown**. Five worker
Linux repetitions plus independent postfix caller cases pass; this is not Windows reproduction,
a deadline/flakiness diagnosis or proof of old runtime correctness. No prior code is altered.

## Final publication, CI and retirement

Accepted one-file correction is normally committed/pushed as
**`29ed39be6c1c18e6d57f782dd073acd37939c71c`**. Coordinator independently verifies its one-file
surface, clean implementation tree/index and matching remote master. Publication consists
of initial reviewed22-file `f63ac75` plus one-file test correction `29ed39b`, and unchanged
preexisting authorized diagram/maintenance ancestor `f7113d7`; no amended history/force push.

[Final exact-SHA CI 40701925587](https://github.com/micha/dml/actions/runs/40701925587)
completes **success in all six jobs**. Direct finite coordinator `gh run watch --exit-status`
exits0; completed exact-SHA job JSON, full logs and sole automatic push workflow list verified.
No manual/release workflow. Seven C tests pass everywhere. Linux/strict1191 Python;
macOS1187/four existing skips; Windows1185/five existing skips, with one POSIX literal-backslash
credential parameter not applicable to native Windows path-separator semantics. No production
profile relaxation/disabled meaningful Windows test. Strict informational CI reports2637/2637;
its `-c` remains distinct from fresh local `-v` and installed SSH evidence.

Actual final Windows verbose log explicitly passes prior caller story and both formerly
failing SSH example cases. This verifies current CI, **not a recovered diagnosis/fix of the
initial unchanged caller failure**; its early child reason stays unknown. Initial failed CI
and two confirmed harness defects remain visible, not first-run success.

Final evidence: `/tmp/dml-iteration9-coordinator-final-{ci.json,ci.log,ci.err,ci-summary.log,
runs.json,watch.log,watch.exit,log.exit}`; initial CI JSON/watch/full worker logs and independent
standard/probe/postfix evidence retained separately. No secret values in committed material.

After independent probe, coordinator released final fixture for explicit retirement. Worker
archived final stopped `/work`/B under `../dml/build/iteration9-bare/retained-work` with
`retirement-provenance.json`, verified labelled stopped disposition and removed only that
owned container/private credentials plus exact earlier worker-owned private-key artifacts.
Coordinator verifies no labelled owned container or32769 listener remains. Image/nonsensitive
packets/source/wheel/provenance evidence remains ignored/caller-owned; no global prune.
Retirement is separate from recorded computational scratch cleanup.

Worker directed to finalize RESULTS only and stop all runtime/build/staging/commit/push/CI.
This turn is complete and stopped. No extra workers, design checkpoint commit/push, later
feature, cloud/global tooling, new remote, release/tag/package publication or further CI.
