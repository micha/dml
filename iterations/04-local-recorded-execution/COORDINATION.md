# Iteration 4 implementation coordination

Status: implementation, independent review, authorized publication and final
exact-SHA CI are complete. Published through `d498a6c`; all six final CI jobs pass.
See [RESULTS.md](RESULTS.md) and [REVIEW.md](REVIEW.md). Worker is stopped. The
assignment below preserves completed coordination, not permission to restart.

## Authorization

The user instructed:

> iteration 4 is GO. have the agent in window 2 do the implementation in a new session. monitor the agent's work and review, providing feedback to the agent as necessary. when all is satisfactory have the agent commit and push. then monitor the CI workflow and have the agent fix issues as needed.

This supersedes the planning documents' pending-authorization statements for this
bounded turn. Follow [HANDOFF.md](HANDOFF.md), [DESIGN.md](DESIGN.md) and
[EXAMPLE.md](EXAMPLE.md), selecting provisional engineering details and recording
actual choices. Material scope/model changes still need user review. No later
feature, extra worker, cloud experiment, release/tag or package publication.

## Assignment and shared resources

- Existing worker: `dml-design:2`, Pi pane `%215`. Coordinator sent `/new` and
  verified the new empty session before assigning this turn. No new tmux window
  or additional agent.
- Implementation checkout: `/work/repos/micha/dml`, initially clean at
  `9b8fb7176e31186621dd5a4c26adadec4d76bc1e`.
- Worker owns runtime/tests/as-built documentation and [RESULTS.md](RESULTS.md).
  Coordinator owns REVIEW, this coordination note and design status reconciliation.
- Worker has exclusive `../dml/build/check` until explicitly paused/released for
  independent coordinator checks. Coordinator may read diffs concurrently and
  use independent scratch; do not race standard checks that wipe the build.
- Read machine and both repository instructions plus all handoff prerequisites.
  Preserve unrelated work and keep tests/process/install scratch bounded/local.
- Report progress, selected choices, deviations, blockers and readiness for review.
  Meaningful failure tests, default validation with unchanged thresholds, current
  installed parent/child/console workflow and honest assurance limits are required.
- Do not commit/push until explicit coordinator acceptance. Respond to findings
  with fixes/regressions and release the build for independent final checks.
- After acceptance, inspect/stage only the reviewed implementation slice, make
  focused commits, normally push existing branch/remote, verify remote SHA and
  monitor automatically triggered exact-SHA CI. Fix within-scope failures without
  weakening tests/thresholds, push fixes and verify final CI success. No force push,
  remote creation, manual release trigger or package publication.

Design notes remain local/uncommitted unless separately requested. Stop when the
bounded implementation, independent review and final exact-SHA CI are satisfactory.
