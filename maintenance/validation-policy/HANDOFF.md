# Validation-policy maintenance handoff

Current delivery: **COMPLETE AND STOPPED at published `4a053340`, accepted WITH
[exception VP-001](EXCEPTION-VP-001.md)**. Raw finalCI failed/fivegreens/one Macarm
oldasync failure UNKNOWN, follow-up OPEN. Worker explicit STOP ALL; see
[RESULTS](RESULTS.md), [REVIEW](REVIEW.md) and [COORDINATION](COORDINATION.md).
This completed handoff is historical, not permission to restart workers/source/build/
fixture/CI or investigate runtime without separate authorization.

Status: **GO authorized**, not a pending-plan-review request. Read [PLAN](PLAN.md)
and [COORDINATION](COORDINATION.md). User delegates evidence-based plan refinement
to coordinator. No new runtime feature/Iteration16, extra agent, cloud/global tooling,
release/package publication or design checkpoint commit/push.

## Preflight and ownership

Read `/home/ssm-user/AGENTS.md` FIRST; mounted /work/admin placement, design and
implementation instructions/documentation guidelines/README/discussion resume/glossary.
Read complete PLAN, this HANDOFF, relevant Iteration15 final review/results, owning
workflow/check.sh/pytest config/coverage and check-script regressions. Use current official
GitHub Actions/pytest docs for API/config details; inspect installed versions/source.

Verify NEW Pi session in existing window2 `%215`, coordinator `%197`; acknowledge session
UUID, clean DML HEAD `664a87085961b5e24d2b709e057e4a28fe724088` and shared-build/process
state. Preserve accumulated design notes. Worker owns implementation guidance/docs/
workflow/tests and maintenance RESULTS. Coordinator owns PLAN revisions/REVIEW/
COORDINATION/design status. Neither rewrites completed historical evidence.

Worker exclusively owns BOTH build/check and build/coverage until changed-surface
freeze/explicit release. No concurrent edits/build wipes. Use focused baseline from
existing published pass, NOT ritual unchanged full baseline. One final worker full-v;
independent focused coordinator validation after release. No every248-file inventory,
second complete suite, installed-image rebuild or retired Floci/SSH fixture restart
without a concrete need. This turn authorizes none of those fixtures/services.

## First draft and tests

Prepare concise owning docs/validation-policy.md, AGENTS/README pointers, minimal CI
pytest report/upload changes, focused default-safe regressions. Send draft/selection
rationale to coordinator before broad work. No CI pass masking/retry/skip/quarantine/
threshold/runtime/outer-budget changes assumed. Keep all five platforms/full tests+
strict Linux; preserve existing failure exits. XML artifacts are diagnostics, not
acceptance classifications. Cover real pytest pass/fail/collection error and report
absence, per-platform paths/always upload/current versions, unchanged budgets/test args.
No new module/framework/private runtime codec or dependency assumed.

Explicit exception procedure must preserve failed raw CI, require primary evidence/
attribution review and named follow-up, scope to actual SHA/run/job/test signature,
record risk/approval/revisit condition and distinguish unresolved from fixed. It must
not let 'unchanged test' alone excuse a regression. Coordinator judgment may revise the
bounded plan based on observed CI; ask before code that exceeds maintenance scope.

## Gates and publication

1. Focused actual tests/source/doc checks, before/after when useful; no secret capture.
2. Worker final unchanged standard command once on stable executable sources:
   `nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file -c bash scripts/check.sh -v`.
3. Changed-file list/HEAD/diff freeze and explicit BOTH-build release; coordinator
   independent focused review/status/report/artifact probes. No automatic full rerun.
4. After explicit independent acceptance: focused staged diff/secret check/commit/
   normal push existing master/origin. No force/rewrite/new remote/tag/release.
5. Exact published-SHA CI outcomes and useful primary report artifacts. Fix new
   attributable failures. Preserve inherited/unknown failures and apply explicit
   approved exception process when justified; do NOT demand reruns until all green.
   Finite CI observation budget should cover existing longest outer20min job.
6. Revalidate only affected paths after corrections; full suite/fixture repeats need
   an explicit assurance benefit. Review substantive correction before next commit.
7. Final actual outcome/source/remote, concise worker RESULTS, coordinator REVIEW,
   and STOP ALL activity. No future feature permission inherited.
