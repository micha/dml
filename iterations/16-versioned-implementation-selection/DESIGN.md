# Iteration 16 candidate design: versioned implementation selection

## Delivery and stop

This bounded turn is **COMPLETE AND STOPPED** through published `e0089323`, all six
final-SHA CI jobs successful. See [RESULTS](RESULTS.md), [REVIEW](REVIEW.md) and the
[implemented example convention](../../../dml/docs/versioned-implementation-selection.md).
The plan/authorization below is historical, not permission to restart or begin a later turn.

## GO authorization

The user's subsequent **Iteration 16 GO** approves this bounded design/example/handoff
for implementation by the existing window-2 agent in a NEW Pi session, coordinator review
and feedback, then accepted worker commit/normal push/CI fixes. See
[COORDINATION](COORDINATION.md). This supersedes pending-review/GO wording below for
this turn, not scope or as-built status; exact engineering spellings remain refinable.

The original preparation status and rationale below preserve planning provenance.

Status: **direction agreed; candidate mechanics for review, implementation GO pending**.
The user agreed to the proposed next slice and offered example/handoff preparation.
That authorizes planning, not exact schema/API approval, delegation, experiments or
publication. Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md).

## 1. Agreed direction and stop line

One intent has two captured implementation bindings available side by side. Record a
versioned default choice; callers can explicitly select another. Resolve and record
that choice BEFORE applying the existing reuse/fresh policy and recording the operation's
own Q. Retain which definition/override explains the selected actual binding.

Different snapshots/branches retain different defaults without rewriting implementations,
old definitions/requests/attempts/results/reuse choices. Same result84 does not authorize
cross-implementation reuse. Each binding keeps an explicit known selection slot; selection
and adoption remain deliberate, not automatic after fresh success.

This is one named intent/two known bindings/fixed worked-example inputs, not a URI registry,
installation/resource manager, full closure model, cache discovery/index/facets/masks,
interchangeability/deprecation framework, scheduler/native entity/cloud/UI or later feature.
Python still explicitly drives execution. No change to async/LMDB/transfer/Floci roles assumed.

## 2. Existing authorities and source-inspected friction

Planning inspects clean published DML `4a05334058a77e78c8ad9c512726123fc347e352`:

- [Intent defaults](../../../dml/docs/intent-reuse-defaults.md) and
  [helper](../../../dml/examples/intent_defaults.py): currently caller supplies binding/input/
  selection names; minimal Idef has EXACT role/intent/default fields. D captures actual
  selection/reasons, then existing own-Q or Q/W delegation. This code does not resolve
  an implementation default. Its document's old acceptance-pending header is stale versus
  completed [Iteration15 delivery](../15-intent-reuse-defaults/RESULTS.md), not a new gate.
- [Versioned selection](../../../dml/docs/versioned-reuse-selection.md) and
  [helper](../../../dml/examples/reuse_selection.py): ordinary S/V/public revalidation, exact
  URI/binding/full-input identity, no search or implicit adoption.
- [Caller requests](../../../dml/docs/spec-next/caller-requests.md) and
  [public preparation](../../../dml/docs/spec-next/repository-execution.md#preparation-and-retained-workspace):
  consume selected TREE names, exact Q roles and one-parent/preserved-tree-plus-only-Q.
- [Transfer](../../../dml/docs/spec-next/transfer.md) and
  [owning packet inspector](../../../dml/docs/spec-next/asynchronous-execution.md#immutable-packets-and-independent-reception)
  own full native history/typed closure and selected successful completion authority.
- [Glossary](../../../dml/docs/spec-next/glossary.md) distinguishes intent, implementation,
  provisional closure and actual request/attempt occurrence.

Appending implementation fields to old Idef would violate its owning reader's exact shape.
Recommend a NEW example-local intent-definition/decision convention, composing existing
PUBLIC preparation/request/S-V/Q-W operations. Do not call private local `_binding`/`_request`
readers or treat a caller-supplied response/verdict as authority. Exact helper/file names are
refinable; no public framework or C primitive gap established by read-only inspection.

## 3. Recommended ordinary records (assistant candidates)

Use an explicit tree entry, illustratively `double-intent`, for ordinary Idef16:

| Binding | Candidate value |
| --- | --- |
| role | literal STRING identifying the new example convention |
| intent | canonical URI, also Idef root |
| reuse-default | literal reuse-by-default or execute-by-default |
| implementations | sub-DAG menu with two named choice references |
| default-implementation | literal label naming one menu member |

Menu labels `double-a`/`double-b` are names, NOT stable implementation identities or reuse
keys. Each ordinary choice captures its binding sub-DAG ID, explicit binding tree name and
known selection-slot name. Recommend choice root = binding reference, strict exact fields/
node/datum types and a fixed menu root marker. Two distinct binding IDs and distinct slots
make the demonstration genuine; do not manufacture two implementations merely by relabeling
identical code. Exact role strings/schema spellings remain candidates, not native entities.

Initial definition captures the binding IDs resolved from the caller's pinned tree. Later
request resolution requires the selected declared tree name STILL match that captured ID;
reject drift rather than silently follow a new binding/current ref. Definition update in
this slice changes ONLY the default label, preserves URI/reuse default/menu/options/other
entries/selections, exact `(C,)` parent/create-only explicit ref/prebuilt response/one batch.
No Q/T/job or installation occurs. General adding/removing/deprecating implementations is
deferred, as is availability discovery or a guarantee that a recorded interpreter can run.

The new ordinary D captures exact Idef16 and selected choice/binding/full inputs, selected
label, requested implementation override (default versus explicit label), selection reason
(default-implementation versus explicit-implementation), resolved tree/slot names, and the
SEPARATE reuse override/action/reason. Link S ONLY when reusing. Recommend root = definition
reference, absent caller-chosen decision name, Cdec preserves C/adds ONLY D/parent `(C,)`.
No policy fields added to normative Q/T/W; W retains its original four fields/own Q/old T/R.

These are application recommendations, not approval of exact APIs or a new intent schema.
Old Iteration15 conventions/record bytes retain their own meanings; no migration/general
backward-compatibility machinery or silent reinterpretation is required.

## 4. Resolve two independent choices

1. Pin C/intent entry; validate ordinary definition/menu/choice metadata and names.
2. Default implementation selects Idef16's declared label; explicit label selects ONLY that
   known member. Unknown/missing/wrong-type label is an error, never fallback/installation.
3. Verify selected binding tree entry matches captured ID. Validate consumed binding/full
   inputs/full native all-parent history through PUBLIC temporary prepare(request=None),
   never execute that projection. Close handles/scratch BEFORE actual-A decision authoring.
4. Apply the existing reuse table to the SELECTED member's explicit slot. Only missing entry
   is absence. Present incompatible/unreadable/failed selection on a reuse path errors
   before D/Q; no switch to another implementation or fresh fallback.
5. Publish D, then existing own-Q builder or selected-reuse Q/W delegation. Compare actual
   returned selection with validated D. Helper records, NEVER dispatches.
6. Explicit application drives existing prepare/stage/submit/observe/receive for its actual
   pending fresh Q. Actual fresh execution creates T, not merely asking for another binding.

Implementation override and reuse override are independent. Explicit A does not mean fresh A;
A can reuse its selected A attempt. Explicit fresh A means new A attempt without adoption.
Execute-default B can still explicitly reuse selected B. No A result satisfies B merely
because URI/inputs/result match. A forged B-slot holding valid A S errors, not a miss.

Each known slot holds ONE selected successful attempt for this exact full-input tuple, not a
multi-input cache. Changing inputs with a present incompatible S still errors on reuse; fresh
can use another valid tuple without repairing/adopting S. Declared fresh/default-execute ignores
unused S application framing, not native closure. Unselected member's S is not consulted; menu/
choice structural integrity and complete reached native history remain required. Consumed local
binding semantics belong to public preparation, not a second application role decoder.

Matching remains actual `(intent URI, selected full binding DAG, full input DAG)` including
producer witness. Menu/default/other-option changes are recorded control context, not new masks
or a blanket rule that future intent dependencies never contribute to computation. This slice
does not claim general intent/closure dependency identity semantics.

## 5. Inspection, boundaries and evidence

Pinned readers recompute implementation and reuse choices from actual Cdec parent/definition/
overrides/known slots, not latest refs. Require exact non-None ObjectId Q and use public
prepare(request=Q, commit=Cq) for normative submission/Q authority. Check optional original
four-field W against exact new Q/selected old final T/R. Native transfer alone retains all
choice/code/definition/decision/history; readers need no original packet/B/service/source run.

Idef16/default update and D authoring individually atomic; D/Q/W/files/service remain separate.
Failures can leave definition/decision, pending Q or complete satisfaction after lost response/
late cleanup. Never repair/duplicate Q/adopt/fallback/relaunch on error. Meaningful new-A late
rollback and response-loss controls must use genuinely absent predicted keys, not preexisting
proof records or disposable validation-store writes. Existing owning Q/W loss gates stay relevant.

Recommend THREE real local Batch jobs/NINE P/U/F: producer42, A84, B84. Offline definition change/
explicit selection/A-override reuse/B-default reuse/true sibling readers add no job. Ordinary
selection slots separate actual binding histories; public revalidation/typed bytes/parent and
occurrence checks—not scalar84 or service counters alone—support the claim. See EXAMPLE.

## 6. Validation policy and VP-001 planning revisit

Use the published [proportionate validation policy](../../../dml/docs/validation-policy.md):
focused changed invariants/negative controls and concrete installed workflow primary, one worker
final full-v/unchanged criteria, independent risk-based focused/acceptance checks, actual final-SHA
CI/JUnit evidence and explicit triage—not duplicate full suites/all-source inventories/fixtures.

[VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md) is revisited at this planning
checkpoint: root cause/attribution still UNKNOWN; its approval applies ONLY maintenance4a053340,
not Iteration16. Proposed slice changes authoring/choice conventions, not async observation/
LMDB handle lifetime; no runtime investigation or standing waiver inherited. If implementation
needs those changes, pause and separately scope the investigation before acceptance. Any new CI
failure requires fresh evidence/decision. Current baseline CI is red with the recorded exception,
not described as fully green. No new probes/runs started during planning.

Next: review candidate design/example/handoff, then separate implementation/delegation/publication
GO. DML/spec/diagram/runtime/build/fixture/image/CI/worker remain unchanged/stopped. No checkpoint
commit/push requested; completed maintenance/Iteration15 authorizations are not inherited.
