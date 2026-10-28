# Iteration 9 coordination

## Authorization and assignment

The user declared Iteration 9 GO: the existing window-2 agent implements the bounded
[design](DESIGN.md), [example](EXAMPLE.md) and [handoff](HANDOFF.md) in a new Pi session.
Coordinator monitors, independently reviews and provides feedback/fixes until satisfactory,
then directs focused worker commit/push and verifies final exact-SHA CI/fixes. This supersedes
planning-only status, not the bounded scope/stop line.

No extra workers, cloud/second-host or remote-Docker experiments, global tooling/services,
release/tag/package publication, automatic recovery or later feature turn. Missing fixture
prerequisites requiring downloads/installations still require a scoped decision. No design
checkpoint commit/push requested.

## Live preflight and ownership

- `/work` is mounted; implementation tree/index initially clean.
- Implementation baseline: `f7113d7acb3a0fe35eed6cb0013d3074533aef51`; published Iteration 8
  endpoint `865bb79`. Existing user-authorized local diagram/maintenance commit `f7113d7`
  is explicitly accounted for as an ancestor of the authorized normal Iteration 9 push,
  not new runtime work; do not amend/drop it.
- Design baseline: `74a7bcd5c7bf33b6d247b4e51f51cd19e37516e1`, with preserved uncommitted
  Iteration 9 planning/status files.
- Coordinator `%197`; existing window-2 Pi worker `%215`, sidebar `%216`.
- Coordinator sent `/new` to `%215`, verified `New session started`/empty context and
  submitted the bounded assignment. Worker began instruction/preflight reading.
- Worker owns runtime/tests/as-built documentation/fixture/example and `RESULTS.md` here.
  Coordinator owns this file, `REVIEW.md` and design status reconciliation.
- Worker has exclusive **both `build/check` and `build/coverage`** through fresh baseline
  and implementation. Independent coordinator runs wait for source freeze and explicit
  release of both builds. No overlapping source edits/wipes/reconfiguration.
- Commit/push waits for explicit independent coordinator acceptance. Completion requires
  successful final exact-SHA CI, plus mandatory actual installed local SSH/container
  evidence; mocks, skipped integration or CI alone do not satisfy acceptance.

## Preflight and approved fixture refinement

Worker reports fresh pre-edit standard `-v` exit 0: 1,089 Python/seven C, Python 2299/2299,
unchanged native/memory gates. This is worker baseline evidence, not coordinator rerun.
An offline scratch image uses 37 cached Nix runtime closure paths (248 MiB) plus current
wheel/venv, avoiding downloads/global installation/retagging. Coordinator permits this
bounded fixture engineering choice; installed loader/native/runtime provenance must be proved.

Container loopback sshd banner works, but host published-port/direct bridge access fails.
No host firewall/service change was made. The worker proposed host networking instead;
**the user explicitly approved** loopback-only host networking through a questionnaire.
Use one owned `--network host` container with sshd `ListenAddress 127.0.0.1` and a dedicated
free high port, no shared mounts. This refines the planned bridge/published-port profile:
filesystem/runtime separation remains, network-namespace isolation is not demonstrated.
Verify actual binding/exposure and record limitation; retire only stopped owned failed
fixtures. This does not authorize broader networking/provisioning or host changes.

## Assignment boundaries

Implement caller-Q-only synchronous SSH stage/execute/fetch using a fixed installed helper,
public exchange spec reader and existing local/transfer/exact-Q atomic A receive. Docker is
local fixture control only, never a runtime backend/shared exchange mount. Preserve exact
Cq/Q, distinct T, unchanged caller heads/request refs, separate cleanup, unknown outcomes,
retained B and nonexecuting fetch/receive. Require strict endpoint/host-key/framing/remote
quoting, pre-spawn local dispatch guard and existing remote one-shot guard.

Read all handoff instructions/contracts/prior evidence; inspect local socket/context/cache/
ABI before fixture operations; use existing tools/caches. Report blockers rather than pulling
or installing missing prerequisites. Follow meaningful exact-Q/all-typed-byte/all-parent,
actual-A-new-put rollback/map-full, installed provenance and finite safe process-loss evidence.
No installed fault hooks or live-child sacrifice; report substituted versus real checks and
local-client versus remote-process reaping honestly. Review as-built diagram/no-native-change
rationale. Preserve thresholds/memory checks and compact IDs/diagnostics.

After stable standard `-v`, actual installed SSH/container gate and static/package/doc checks,
freeze and release both builds for independent coordinator review before publication.

## Independent acceptance and publication gate

Worker froze all 22 files and released both builds after stable `-v` exit0: 1,189 Python/
seven C, Python2637/2637 and unchanged native/memory/141CLI gates; final actual bare installed
fixture gate271 and nine selected negative probes pass. Coordinator reviewed source/contracts/
fixture/meaningful failure tests, independently ran fresh standard with the same counts and
separate offline-installed custom actual SSH **177-check** workflow. All11 wheel/remote/host
package artifacts match every byte; all22 frozen hashes remain unchanged. [REVIEW.md](REVIEW.md)
owns evidence, initial private-oracle exception correction and qualifications.

No outstanding within-scope finding remains: coordinator accepts the bounded slice and returns
both builds, directs focused reviewed22-file worker commit/normal push (preserving/accounting
for existing `f7113d7` ancestor), then final exact-SHA automatic CI/fixes. No publication yet
claimed at this gate. Final fixture is stopped/writer-free after independent probe; worker
may archive required B/evidence and retire only the labelled stopped owned container/private
keys, keeping nonsensitive evidence/image, no global deletion. CI fixes require focused review.
## Final reviewed CI correction, publication and stop

Initial reviewed22-file implementation is normally committed/pushed as `f63ac75`, including
unchanged prior `f7113d7` ancestor. Initial exact-SHA CI40699187591 finishes five jobs green/
Windows three failures. Actual trace confirms two new SSH example host-model POSIX-vs-Windows
interpreter errors. Third unchanged caller-story early completion reason remains unknown.
Coordinator approves/reviews one-test-file private host-binding adapter and POSIX/Windows
regressions, keeping production/example/fixture/old caller source unchanged. Worker stable
`-v` passes1191/seven C/unchanged gates; explicit freeze/release precedes coordinator independent
104-test postfix pass and hash verification. Coordinator accepts focused one-file correction,
returns builds and directs normal commit/push/new exact-SHA CI. [REVIEW.md](REVIEW.md) owns details.

Focused correction is normally pushed as **`29ed39be6c1c18e6d57f782dd073acd37939c71c`**.
Coordinator verifies one-file surface, clean tree/index/matching remote and sole automatic
[final exact-SHA CI40701925587](https://github.com/micha/dml/actions/runs/40701925587):
**all six jobs successful**, direct finite watch exit0/full logs/job JSON. Windows explicitly
passes old caller story and both fixed SSH cases; prior old failure cause remains unknown.
No manual workflow, further fix, gate/skip weakening, runtime/profile relaxation or release.

Fixture retirement authorized after independent stopped-writer probe: worker archives final
B/provenance, removes only labelled stopped owned container/private keys; coordinator verifies
no owned container/32769 listener. Image/nonsensitive evidence retained, no global prune.
Worker directed to finalize RESULTS only and stop all runtime/build/staging/commit/push/CI.
Implementation, review and publication/CI are complete and stopped. No design checkpoint
commit/push, additional worker, cloud/global tooling, release/package publication or later turn.
