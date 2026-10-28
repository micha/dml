# Iteration 8 coordination

## Authorization and assignment

The user declared Iteration 8 GO: the existing window-2 agent implements the approved
[design](DESIGN.md), [example](EXAMPLE.md) and [handoff](HANDOFF.md) in a new Pi session.
Coordinator monitors, independently reviews and provides feedback/fixes until satisfactory,
then directs focused worker commit/push and verifies final exact-SHA CI/fixes. This current
authorization supersedes the planning-only status, not the bounded scope/stop line.

No extra workers, release/tag/package publication, cloud/global tooling, automatic recovery,
detached service or later feature turn. No design checkpoint commit/push requested.

## Live preflight and ownership

- `/work` is mounted; both checkouts initially clean.
- Implementation baseline: `a8d646379a52878d087d28bc216b7baa4f9ef3db`.
- Design baseline: `31fe1087c838ebddad56f08be860de14bfa94d86`.
- Coordinator pane `%197`; existing window-2 Pi worker `%215`, sidebar `%216`.
- Coordinator sent `/new` to `%215` and verified `New session started` and empty context.
- Worker owns implementation/runtime/tests/as-built documentation and `RESULTS.md` here.
  Coordinator owns this file, `REVIEW.md` and design status reconciliation.
- Worker has exclusive **both `build/check` and `build/coverage`** through baseline and
  implementation. Complete fresh standard baseline before measured source edits.
  Source freeze and explicit release of both builds precede coordinator independent runs.
  No overlapping wipes/reconfiguration/source edits.
- Commit/push waits for explicit independent coordinator acceptance. Completion requires
  successful final exact-SHA CI, not merely local tests.

## Assignment

Read the approved handoff/design/example and all required instructions/contracts/prior
Iteration 7 evidence. Implement only explicit atomic A request recording, the public
local request builder/imported-Q first-attempt operation, pinned Cq/Q selection through
both return paths and the finite installed acceptance story. Preserve original execution
mode, exact request identity, separate cleanup, unknown outcomes, unchanged caller heads
and request refs, explicit received refs and application-owned process reaping.

Follow the handoff's meaningful rollback/new-put, real-process, strict wrong-Q, coherent
snapshot, all-parent typed-byte and installed provenance evidence. Record actual choices,
commands/exits/counts and limitations honestly. Send baseline/progress/blockers to `%197`;
freeze/release both builds for independent review. No extra agents or commit/push before
acceptance.

## Baseline and early review

Worker completed a fresh standard `scripts/check.sh -v` before measured edits, exit 0:
831 Python tests, seven C executables, Python 2013/2013 statements, retained native
1681/1681 lines, 132/132 functions, 1562/1562 outcomes. Binding memory has zero
unsuppressed errors/624 existing runtime suppressed contexts; 141 CLI Valgrind processes.
Session-local evidence: `/tmp/dml-iteration8-baseline.{log,exit}`.

Coordinator early source review found public local-owned seams and shared exact-Q
validation aligned with the plan; requested discriminating expected-Cq/T-to-wrong-matching-Q
cases in both return paths, imported retry rejection and successful-new-T/P late raw/dangling
reservation rollback. Worker reports these passing; substituted early raw-ref reads remain
explicitly qualified. Coordinator also requested reducing unrelated whole-file formatting;
worker restored unchanged local execution/finalization spelling. Required nullable `request`
and v2 job/handle framing are accepted engineering refinements, not compatibility machinery.
Independent installed probe is prepared separately; no shared-build use before freeze/release.
No acceptance or publication yet at that early checkpoint.

## Independent acceptance and publication gate

Worker froze 22 implementation files and explicitly released both builds after final stable
standard `-v`: 1081 Python/seven C, Python 2299/2299, unchanged native/memory gates.
Coordinator independently inspects source/evidence, verifies frozen/wheel/installed bytes,
runs a separate **302-check** installed workflow and fresh standard `-v`, exit 0 with the
same 1081/seven C and retained coverage/memory totals. [REVIEW.md](REVIEW.md) owns details
and qualifications. No outstanding within-scope finding remains.

Coordinator accepts this bounded slice, releases both builds back to worker and directs
focused inspection/staging/commit/normal push of only the reviewed 22 implementation files,
then exact-SHA automatic CI verification/fixes. CI source/test changes require focused
review and appropriate validation before another push. No extra workers, design commit/push,
force push/new remote, release/tag/package publication, cloud/global tooling or later turn.
Final publication/CI were pending at that gate.

## Initial CI and focused correction gate

Initial reviewed implementation is normally pushed as `509c2f0`. Exact-SHA run
[40621755388](https://github.com/micha/dml/actions/runs/40621755388) is cancelled on
Windows/other five jobs successful. Capped logs contain huge physical bytes-diff padding
without a test header. Dependency inspection plus bounded actual-Linux Windows-layout
emulation demonstrates the new small-map fixture comparing different physical extents
while complete logical rollback remains correct; exact Windows failedcase stays qualified.

Coordinator approves a bounded test-only correction, then reviews the one-file +72/-1
patch preserving exact-byte equality/raw/full typed/new-put oracles and adds feedback to
avoid redundant truncation of an already mapped Windows file. Worker stable postguard
standard passes 1085/seven C and unchanged gates; source freeze and both-build release
precede coordinator independent **254-test** postfix run, exit 0. [REVIEW.md](REVIEW.md)
owns evidence/limits. Coordinator accepts the correction, releases both builds and directs
only this test-file commit/normal push and new final exact-SHA CI verification. No runtime,
native, workflow, skip or gate change; no expanded scope. Final green CI was pending at
that correction gate.

## Final publication and stop

Worker normally pushed only accepted test correction as `865bb7933616133acf10d9b14ca0f5fe711c5850`.
Coordinator verifies one-file surface, clean implementation tree/index and matching remote
master. [Final exact-SHA CI 40624753242](https://github.com/micha/dml/actions/runs/40624753242)
passes **all six jobs**. Full final logs/job JSON, sole automatic exact-SHA push workflow list
and direct finite watch exit 0 verified; [REVIEW.md](REVIEW.md) owns counts/qualifications.
Initial cancelled Windows logs/diagnosis uncertainty and dependency-layout regression remain
explicit; no erased failed/cancelled history or claim of first-run green.

Worker directed to finalize only RESULTS and stop all implementation/build/staging/commit/
push/CI. This bounded turn is complete and stopped. No extra workers, design checkpoint
commit/push, release/tag/package publication, cloud/global tooling or later feature turn.
