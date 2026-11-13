# Incremental prototype — failed snapshot preparation / bounded correction request

Status: **STOPPED before focus/readiness**. User accepted pre-edit plan by “accepted. proceed.”;
new isolated draft implemented. FIRST snapshot preparation RAW TRUEexit1; no automatic retry.
No focused test/native import/controller store/E-P-C/SQL/complete collection/build/install/commit/push.

## Actual raw evidence

Owned worktree `build/relational-spike/incremental-v1/`:
`prepare.stdout` EMPTY, `prepare.stderr` actual traceback, `prepare.exit` actual1;
partial `pins/` contains copied source/package/native artifacts, NOT a completed pin receipt.
`pins/pins.json` ABSENT; focused log/XML and story directory ABSENT. No XML reconstruction/pass.
Raw stderr SHA256 `f8f95535c857873b6be6da5b9b18ab14e12df003605026154a79143bb040d0e6`.
Existing source/evidence/native bytes remain intact, Git tracked diff empty at15555c0.

Failure: `driver.prepare` → candidate fingerprints → `identity.manifest_digest` raises
`ValueError('manifest order differs')`. Source copying/closure query happened before failure;
final pin receipt/read-only sealing did NOT. Treat snapshots as incomplete, not installed or trusted.
No candidate code/native extension or DuckDB activated. Stdlib hashing, Git and read-only Nix
closure query only. Original failed snapshot source includes ALL six runtime Python source copies,
including the defective builder and driver, before any proposed correction. Twelve current new
spike files remain uncommitted; no original source changed.

## SAME stopped-data causal observation

Read-only filesystem ordering comparison on copied `candidate-A` (373files) reproduces the first
misordering at index26 without invoking any prototype code or recreating preparation:

- `sorted(Path.rglob(...))` compares Path COMPONENTS: `docs/spec/cli.md`,
  `docs/spec/execution.md`, `docs/spec/maintainability.md` precede `docs/spec-next/...`.
- Validator expects full relative STRING order: `docs/spec-next/AGENTS.md`,
  `docs/spec-next/README.md`, `docs/spec-next/asynchronous-execution.md` precede `docs/spec/...`.

The hyphen sorts before slash in strings; component `spec` sorts before component `spec-next`.
This is a NEW prototype canonical file-manifest defect. It is NOT a native/DML/runtime/API bug,
Nix provisioning failure, historical native19 attribution or VP-001 diagnosis. Canonical ordering
is meaningful key/authority assurance; do NOT remove the validator or accept unsorted manifests.

## Narrow proposed correction — approval pending

Only TWO owning new files, BEFORE fresh preparation:

1. `incremental/identity.py`: builder sorts traversal with explicit relative-posix-string key,
   matching the EXISTING strict validator. Preserve all symlink/type/digest/file-set guards.
2. `incremental/test_identity.py`: ONE precise directory-prefix regression with `spec/` and
   `spec-next/`, asserting exact relative string order and successful strict manifest admission.
   Deliberately reverting the builder must fail this case; no weakened comparison/threshold.

Before edits, preserve exact ALL12 new draft source bytes + digests in a NEW owned failure-source
archive, while leaving existing failed snapshots/logs intact. Corrected controller namespace/source
pin will differ; do not claim failed source has been validated by later current tests.

Proposed finite continuation: ONE fresh corrected stdlib/Git-only snapshot preparation in NEW
`build/relational-spike/incremental-v2/`, then the previously UNCONSUMED ONE focused invocation,
now **49** anticipated cases (48 original +1 precise regression) on frozen corrected sources.
No native pre-run, exploratory repeat, actor/SQL/map/get/full suite or additional preparation
if this fails. Correction touches no package/core/storage/API/old tests/runtime deadlines.
Process blockers/CONTROL fixture namespace stay. Preserve actual commands/exits/XML/uncertainty.
Success still stops at explicit STATIC/metadata readiness review; no automatic seven-round story.

This is a named causal correction and new-source preparation request, not retry-until-green or
reuse of a failed pin directory. Original failure remains RAWfailed even if correction passes.
Main Iteration25/source/shared builds remain untouched; GHA disabled/native19 PAUSED/private
candidate retained/VP001 OPEN UNKNOWN/owner/conditions/no standing waiver unchanged.

## Current decision

Accept the TWO-file manifest-order correction + source preservation + ONE corrected preparation/
49-case focus continuation, or revise scope. No further executable/test edit/preparation/activation
has been performed after failure; documentation/status updates only. No hidden completion, renewed reader or publication permission.
