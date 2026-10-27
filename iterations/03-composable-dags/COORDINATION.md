# Iteration 3 implementation coordination

Status: implementation, independent review, authorized commit/push and final
exact-SHA CI verification are complete. Published `9b8fb71` passes all six jobs;
see [RESULTS.md](RESULTS.md) and [REVIEW.md](REVIEW.md). Work is stopped. The assignment
below preserves the completed coordination, not a directive to restart.

## Authorization

The user's instruction:

> have the `pi` agent in window 2 implement. you monitor the agent's work and review
> it. provide feedback as necessary until all issues are resolved. when all is
> satisfactory have the agent commit and push. ensure that the CI workflows complete
> successfully -- have the agent fix any issues.

This supersedes the planning documents' implementation-pending status for this
bounded turn. Read [HANDOFF.md](HANDOFF.md), [DESIGN.md](DESIGN.md) and
[EXAMPLE.md](EXAMPLE.md) completely and follow their scope/stop line. Follow machine
and both repositories' instructions. This is not release/package publication,
extra-worker, cloud experiment or later-feature authorization.

## Worker assignment

Use the existing Pi agent in `dml-design:2`, pane `%215`; no new agent/session is
needed because inspection found its conversation empty. Work in the existing
`/work/repos/micha/dml` checkout (initially clean at `e253249`). Read its agent guide
and all handoff prerequisites before code changes.

1. Implement the approved bounded turn, selecting only provisional engineering
   details left open by the plan. Keep one C foundation and one native CLI.
2. Maintain `RESULTS.md` here with baseline, selected choices, changed files,
   actual commands/results and honest limitations. Do not overwrite unrelated edits.
3. Run standard default validation, meaningful fault/memory checks, bounded mutation
   diagnostics and a local installed smoke workflow. Preserve thresholds/exclusion
   policy. Use only bounded project-local build/install scratch and available tools;
   ask for any missing tooling permission rather than system/global changes.
4. Report progress/blockers and the reviewed-change surface. When implementation
   and your checks are complete, explicitly report readiness for coordinator review.
5. Respond to coordinator review/probes and fix issues with regressions. Do not
   commit or push until the coordinator explicitly accepts the implementation.
6. After that acceptance, inspect/stage only this turn's changes, make focused
   implementation commit(s), normally push the existing branch/remote, verify the
   remote SHA and monitor all automatically triggered CI runs for the exact SHA.
   Fix failures within scope, rerun affected local/default checks, commit/push fixes,
   and verify final exact-SHA CI success. Do not force push, create a remote, tag,
   trigger releases or publish packages. Escalate unrelated or unavailable-workflow
   blockers instead of hiding them or weakening CI.

## Shared resources and ownership

- Worker owns runtime/test/as-built implementation files and this iteration's
  `RESULTS.md`. Coordinator owns `REVIEW.md`, design README/discussion/AGENTS and
  authorization-status reconciliation. Do not edit these coordinator-owned files
  concurrently; send proposed updates or questions instead.
- Worker has exclusive `../dml/build/check` until it explicitly pauses/releases it
  for independent coordinator validation. Standard checks wipe/reconfigure it.
- Coordinator will inspect changes while work proceeds, use independent scratch
  when possible, and request a runtime/build pause for final review/probes/checks.
- No additional delegates. Communicate through this existing worker's tmux input;
  status can be monitored from its transcript and delivery notes.
- Design notes remain local/uncommitted unless separately directed. Commit/push
  authorization here concerns the bounded implementation checkout changes.

Stop once reviewed implementation and final exact-SHA CI are satisfactory. Preserve
failed-run history, tested/excluded populations, mutation survivors and platform/
installed/finalizer limitations rather than converting partial evidence into claims.
