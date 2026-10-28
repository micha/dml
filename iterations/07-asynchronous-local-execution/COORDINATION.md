# Iteration 7 coordination

## Authorization and assignment

The user declared Iteration 7 GO and authorized the existing window-2 agent in a
new Pi session to implement the bounded design/example/handoff. Coordinator monitors,
independently reviews and provides feedback/fixes until satisfactory, then directs
worker commit/push and verifies exact-SHA CI/fixes. This supersedes preparation-only
permission statements, not the iteration's stop line. The separate saved handle/live
application process owner is the approved plan; no detached lifetime guarantee.

No extra workers, release/tag/package publication, cloud/global tooling, automatic
recovery or later feature turn. No design commit/push requested.

## Live preflight and ownership

- `/work` is mounted. Both checkouts initially clean.
- Implementation baseline: `a0aa05d56b9e70277a98bb03e26514ab6b6f1415`.
- Design baseline: `93ef0ce2d8698c38e88c46fa924ee98f2279db92`.
- Coordinator live pane: `%197`. Existing implementation worker: `dml-design:2`,
  Pi pane `%215` (sidebar `%216` is not the worker).
- Coordinator sent `/new` to `%215` and verified `New session started`, empty context.
- Worker owns implementation/runtime/tests/as-built documentation and `RESULTS.md`.
  Coordinator owns this file, `REVIEW.md`, and design status reconciliation.
- Worker has exclusive **both `build/check` and `build/coverage`** until explicit
  freeze/release. Finish a clean standard baseline before measured source edits.
  Coordinator does not configure/wipe/use those builds concurrently. Review runs
  follow explicit release and a source freeze; findings are returned to worker.
- Commit/push is authorized only after explicit coordinator acceptance. Final
  delivery requires successful final exact-SHA CI, not merely local green tests.

## Assignment

Read the approved [handoff](HANDOFF.md), [design](DESIGN.md) and [example](EXAMPLE.md),
all required live instructions/contracts and Iteration 6 evidence. Implement only the
bounded Python asynchronous start/observe/receive slice using public local/transfer
operations, fixed installed worker and additive readiness receipt. Preserve synchronous
behavior, unchanged caller heads, immutable validated P/U/F packets, one Q/T per job,
unknown outcomes, independent expected selection and explicit live process reaping.
Use finite private process barriers and fresh owned local scratch. Record actual versus
substituted faults, installed provenance, independent full typed-byte oracles, late
successful-new-put rollback, mutation/coverage/platform limitations honestly.

Send baseline and progress/blocker updates to `%197`, then freeze/release both builds
for independent review. No commit/push before acceptance; no additional agents.

## Baseline and early review

Worker reports fresh standard `scripts/check.sh -v` exit 0 before edits: seven C
executables, 609 Python tests, 1,639/1,639 Python statements and unchanged retained
C 1681/1681 lines, 132/132 functions, 1562/1562 outcomes. Binding memory has zero
unsuppressed errors (624 existing suppressed contexts); 141 CLI Valgrind processes.
Session-local worker evidence: `/tmp/dml-iteration7-baseline.{log,exit}`.

Coordinator early source inspection found additive public-API seams aligned; requested
explicit prior-Q/T-in-C, coherent read and post-selection pinned export regressions.
Further feedback distinguishes scaled-profile rejection from actual production-limit
post-completion overflow and requests genuine large-result overflow evidence, plus
attention to finite demonstration timing across slower platforms. No acceptance yet.

## Independent acceptance and publication gate

Worker addressed feedback with actual overflow/gates and concurrent-reader, valid token-
swap and receiver-scratch cleanup regressions, then explicitly froze source and released
both builds. Coordinator's separate installed workflow passes 208 checks; fresh independent
standard `-v` passes 831 Python/seven C, 2013/2013 Python statements and unchanged native/
memory gates. [REVIEW.md](REVIEW.md) owns inspection, evidence and qualifications.

Coordinator accepts this bounded slice, releases both builds to worker and directs focused
inspection/staging/commit/normal push of the reviewed 22 implementation files, then exact-
SHA automatic CI verification/fixes. No unrelated changes, extra workers, release/tag/package
publication, new remote/force push, cloud/global tooling or later turn. Final CI pending.

## Final publication and stop

Worker focused 22-file commit `a8d646379a52878d087d28bc216b7baa4f9ef3db` is normally
pushed; coordinator verifies committed surface, clean implementation tree/index and
matching remote master. [Exact-SHA CI](https://github.com/micha/dml/actions/runs/40602956772)
passes all six jobs on first run; no CI fix/rerun. Coordinator verifies complete logs/job
JSON, sole automatic push workflow list and finite watch exit 0. [REVIEW.md](REVIEW.md)
owns detailed counts/qualifications. Worker directed to finalize only RESULTS and stop
all runtime/build/staging/commit/push/CI work. No additional feature/release/publication
turn or design checkpoint commit/push authorized.
