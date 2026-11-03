# Iteration 20 conditional handoff: result-based input reuse

Status: **DEFERRED historical candidate; NOT an active handoff; do not execute this plan**.
Replacement: [recorded argument maps handoff](../20-recorded-argument-maps/HANDOFF.md), candidate
for review; separate implementation GO still required.
See [Iteration20 redirection](../../discussion.md#iteration20-redirection-value-arguments-and-separate-provenance).
New callable-boundary mechanics require a replacement plan/review and separate implementation GO.
The original conditional handoff below is preserved as historical candidate material only.

Original status: **prepared candidate for review; implementation/delegation/publication GO pending**.
The user agreed the direction and requested preparation only. Read [DESIGN](DESIGN.md) and
[EXAMPLE](EXAMPLE.md) before review. Exact engineering spellings/counts remain refinable.
This handoff starts no worker, source edit, build, story, investigation, commit or push.

## Goal and recommended bounded mechanics

For a consumer declaring producer occurrence irrelevant to its result, a new full input with
another valid upstream attempt but the SAME full result sub-DAG may reuse an old downstream
attempt. Preserve new own Q/full actual inputs/upstream witness and original downstream
Q/T/full executed inputs/upstream witness separately. New request on either path; no new T
on reuse; reuse is not another empirical downstream trial.

Recommend two versioned modes, `exact-inputs` and `result-inputs`, for ONE fixed witnessed-input
profile. NEW ordinary P/Mp/Dp/projection roles, public upstream/downstream immutable S inspection,
full actual caller Q and ordinary W composition. Exact mode keys full inputs; result mode removes
ONLY producer from a strictly validated projection retaining exact result DAG and typed factor.
No scalar-only equality, unvalidated witness, arbitrary field deletion or general mask language.

Table scoped by intent+exact P; bounded sixteen entries/all-entry revalidation. Rows retain original
full inputs and both historical downstream/upstream S slots/links. Decision retains requested
upstream S/full input, exact policy and consumed historical authority. New pinned reader independently
recomputes both chains and identities. Explicit table selection/adoption/removal stays versioned;
policy change does not automatically migrate/reinterpret old tables or requests.

Keep old Mi/Di/readers/exact-binding APIs and Floci composition convention unchanged. Use NEW
example-local public-API composition, not private role codec or globally relaxed Q validation.
Report a genuine public seam gap before expanding scope. Ordinary DAG roles add no native entity.

## Required reading and preflight AFTER future GO

Read machine index/mounted administration guidance, design AGENTS/README/discussion resume/glossary,
ALL20 documents, implementation AGENTS and documentation guidelines, linked public authorities
in DESIGN, and owning [validation policy](../../../dml/docs/validation-policy.md).
Read [GHA disable decision](../19-intent-scoped-reuse/GHA-DISABLED.md), Iteration19
[review](../19-intent-scoped-reuse/REVIEW.md), and
[VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md).

Reinspect actual HEAD/index/source ownership/relevant installed provenance; don't treat historical
clean receipts as live proof. Planning baseline is published47131da with development GHA disabled,
feature19 accepted/publisheda71e89f, native investigation PAUSED/private incomplete unexecuted
candidate retained. No deleting, completing or executing that private native harness.

If future GO delegates: ONLY existing window2 worker in a verified NEW Pi session; coordinator owns
review/coordination/design status, worker authorized source/tests/informative docs/owned local story/
results. Explicitly transfer BOTH shared builds/source from coordinator ownership before edits/runs.
Worker then owns both until changed-surface/HEAD freeze and explicit release. No concurrent builds,
whole-source inventory ritual, extra agent or inherited restart permission. Missing downloads/
installations need scoped approval; no global tooling/service/image/retired fixture restart.

## Pre-edit validation map

Record changed invariants and assurance before implementation; exact commands chosen from current
owning build documentation, not invented examples or historical rituals:

1. Strict P/profile/mode/shape/role/type/root; full inputs remain distinct when only upstream T
   changes. Deterministic projection discards ONLY that field, retains full R/typed factor, and
   is invariant to native canonical binding order. All other relevant variations distinguish
   identity. Unknown profiles/fields reject. No target mutation during inspection/key derivation.
2. Public successful upstream S owns BOTH input R/T and retained F. Historical row's downstream
   S owns original full inputs; historical upstream S matches those inputs. Requested upstream
   S separately matches actual new inputs. Failure/unknown/mixed R/T/slot substitution rejects.
3. Table intent/P/key/row/cap/uniqueness/all-entry validation, policy separation, explicit one-key
   adoption/removal, distinct occurrence replacement, unchanged other rows/S/history/branches.
   Wrong P or old Mi is error, absent key default miss, explicit reuse miss before Dp/Q.
4. Dp exact actual basis/P/requested binding/full inputs/upstream S/action/reason and historical
   consumed row/S recomputation. Own returned public Q/Cq/ref/tree exact before W; W actual
   ownQ/oldT/R/one-parent/only-W delta. Old T/Q/upstream provenance must NEVER be rewritten.
   Pinned readers must not replace actual policy with latest slot/ref or latest upstream attempt.
5. Full reached native all-parent/composite closure, including fresh paths. Historical paths inert;
   fresh transferred readers need no spawning/transport/original files. Result-mode full result
   DAG equality, not I64-root equality; projected inputs cannot be substituted on actual Q.
6. Representative changed projection/table/decision/W rollback/loss boundaries: real absent
   predicted rows, late collision/allocation/map-full where meaningful, preallocated response,
   complete-publication-with-lost-response. Prior completed batches persist on later failure.
   Rely on unchanged S/Q/native faults; no wholesale repetition of their old matrices.

Useful mutations: leave witness accidentally in projection; drop factor/result structure; omit
upstream-success association; substitute projection on Q; use latest policy; overwrite historical
witness with new witness; skip nonmatching row validation; accept another W request/attempt.
Mutation should fail its predicted invariant, not collection/import/collision. Retain controller/
mutant source versions and hashes BEFORE execution; missing tooling is not install permission.

Preserve tests/memory/coverage thresholds/skips/runtime timeouts/budgets. Precise no-value exclusions
need rationale and tested-versus-excluded accounting. Difficult meaningful failure paths need tests.
No retry-until-green, swallowed errors or weaker assertions to bypass failures.

## Concrete acceptance and proportionate local validation

EXAMPLE proposes SEVEN Q/SIX real synchronous LOCAL attempts over main/exact sibling roots:
producer42; double84; fresh producer42; result-policy newQ/old-double reuse; exact-policy sibling
fresh double84; main fresh producer43; result-policy miss/fresh double86. Metadata/S/transfer/read
add no support Q/T. Exact sibling fresh execution distinguishes policies empirically. No extra
attempt for table population/reader/oracle correction; focused test fixtures counted separately.

Use current installed DML with captured trusted local producer/consumer source bytes. Prefer the
existing public synchronous local workflow; no async story, phase holds, old Batch/SSH/Docker
fixture or timing/LMDB investigation. Standalone children import installed public runtime only.
Observe/receive/publicly validate exact completed history, then known safe child reaping. Count
native distinct Q/T over retained roots, not host dispatch counts. Keep logs/controller sources/
source provenance/original failed oracles before correction. Transfer retained roots and run fresh
installed nonexecuting policy/readers with spawn and transport blocked.

Owning validation policy: focused changed-behavior checks plus concrete story primary; ONE unchanged
final standard `scripts/check.sh -v` on final relevant source after future GO. Independent coordinator
review/checks risk-based, preferably NONEXECUTING on SAME retained evidence; no automatic second
full suite or duplicate story. Any repeat needs a stated assurance benefit, reviewed scope and
preserved original outcome. Full-gate recurrence of related native/async failure requires fresh
triage/scope, not reopening the paused investigation or invoking VP-001 as standing waiver.

Development GHA is disabled by explicit user decision. DO NOT enable/run it or reserve a fix-CI
round. Historical CI failures/cancellations and UNKNOWN attribution remain raw; disabled workflow
is not a pass or native fix. No workflow/budget/runner/release-control/repository-setting changes.
Missing platform evidence must be described, not claimed as verified by local Linux success.

## Documentation, independent acceptance, publication and STOP

Add informative owner documentation for new helper/policy/profile/reader with existing normative
links. Explain local witness terminology against glossary request/attempt/result concepts; any
shared glossary clarification happens only within future authorized implementation and must not
pretend a generic facet/mask subsystem was implemented. Preserve old frozen evidence and contracts.

Review [as-built visualization guidance](../../../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance)
and LMDB diagram against actual storage/relationship claims. New ordinary P/Mp/Dp DAGs do not
justify new LMDB entity boxes or proposal-state technical claims. No UX namespace reorganization.

Freeze changed list/diff/HEAD/relevant hashes and explicitly release BOTH builds/source for independent
review. Record actual focused/full/installed exits, original failures, source identity, independent
versus reviewed evidence and limits. New attributable failures block; UNKNOWN failures require
explicit evidence/risk/follow-up disposition under owning policy, never hidden greenwashing.

ONLY after independent acceptance and authorized focused publication: worker focused staged/secret
review, commit/normal existing remote push, verify exact source+remote SHA. No development GHA
launch. RESULTS/REVIEW should state GHA intentionally disabled/not run and preserve unresolved
native investigation/VP-001, not claim all-six-green. Safe owned child/evidence disposition and
explicit STOP ALL finish this turn. No package/release/cloud/global tooling/native runtime fix/
resource/scheduler/framework/generic cache/later turn/design checkpoint commit/push authorization.

Review this candidate plan, then request separate GO. Preparation alone authorizes none of those
implementation/delegation/build/story/publication actions.
