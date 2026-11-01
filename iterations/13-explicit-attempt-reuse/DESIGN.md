# Iteration 13 candidate design: explicit historical-attempt reuse

Status: **reviewed bounded plan; implementation/delegation/publication GO pending**.
The user subsequently stated “reviewed.” This records plan review, not implemented behavior,
worker assignment, fixture/build/CI operations or commit/push permission. Exact engineering
spellings remain refinable; earlier candidate wording preserves preparation provenance.

Status at preparation: **direction agreed; candidate details for review, no implementation/delegation GO**.
The user agreed to the proposal to record a new request while explicitly reusing an earlier
successful attempt, with strict intent/binding/full-input matching. This authorizes planning,
not implementation, fixtures/builds, worker restart, commit/push or CI. Exact engineering
spellings and the recommendations below remain refinable. Read [EXAMPLE](EXAMPLE.md) and
[HANDOFF](HANDOFF.md). Completed Iteration12 GO is not inherited.

## 1. Goal and boundaries

Distinguish three things in ordinary history:

- A new request asking for the same computation.
- Explicit satisfaction using a particular successful historical attempt and its result.
- A separately requested fresh attempt, even when its result content is identical.

Caller choice is explicit. No automatic cache lookup/discovery, reuse-by-default policy,
identity masks/facets, adoption/default selection, cross-implementation equivalence, registry,
scheduler/recovery, resources or cloud feature. No new native entity or executable node.
Existing request/attempt roles and P/U/F execution protocol should remain unchanged.

This first matching rule compares **intent URI, binding DAG ID and complete input DAG ID**.
It does not compare request occurrence, transport token, containing commit or current head.
Another containing snapshot can ask the same computation. Different recorded interpreter,
source, timeout or input witness contributes through the binding/input IDs and rejects reuse
under this rule, even when a broader future facet might intentionally ignore that dimension.
This is a bounded rule, not the final identity-facet or scientific equivalence policy.

## 2. Planning evidence and existing authorities

Read-only inspection uses clean DML `66311fcc1a2c652b5e2526c5de78a3cf781e67d6` and:

- [Caller requests](../../../dml/docs/spec-next/caller-requests.md): explicit atomic Q/Cq/two refs.
- [Public asynchronous inspector](../../../dml/docs/spec-next/asynchronous-execution.md):
  complete packet/exact independently expected selection before returned owned fields.
- [Local roles](../../../dml/docs/spec-next/local-execution.md): original request/attempt association.
- [Transfer](../../../dml/docs/spec-next/transfer.md): complete typed all-parent closure.
- [Python API](../../../dml/docs/spec-next/python-api.md): native transaction/handle boundaries.
- [Floci](../../../dml/docs/spec-next/floci-execution.md): unchanged execution and service-status limits.
- [Composition example](../../../dml/docs/composed-recorded-steps.md): exact producer witness/I2.

Existing `record_exchange_request` returns owned fields from its actual new Q publication.
`read_observation` supplies owned historical request/attempt/result fields after validation.
There is no currently public general reuse record or pending-request satisfaction inspector.
Private `local._request/_submission` and exchange role readers are NOT application APIs.
Prefer an example-local operation that creates its own new request through the public helper;
that avoids accepting forgeable incoming RecordedRequest flags or adding a public framework.
A genuine need for an independently callable pending-Q reuse stage/public validator needs
concrete evidence and review, not private codec access or duplicate local-role validation.

## 3. Recommended authoring sequence

A finite host operation takes explicit basis C, tree names/intent, historical immutable packet
and **independently supplied old expected Cq/Q**, plus create-only submission/return refs.
It creates no prepared workspace, transport token, B, attempt, service call or execution owner.

1. Publicly validate the historical packet against old expected. Require F/completion/done/
   computational success with actual result. Require the selected history already in A.
   Never use bare manually supplied ReceivedObservation/RecordedRequest as validation authority.
2. Read immutable basis C's selected binding/input IDs through public typed native reads.
   Compare selected intent/binding/inputs with the validated historical computation. Require
   historical F reachable in C's all-parent commit history for this bounded application.
   Preserve exact selected final attempt/result from that SAME validated completion.
3. Close handles. Deliberately call existing `record_exchange_request` for fresh Qr/Cqr under
   explicit submission/request refs. Its actual owned return supplies new Q fields; verify
   the three matching dimensions again. No arbitrary preexisting Q description is accepted.
4. In a SEPARATE A write transaction on pinned Cqr, preserve its tree and add only an ordinary
   reuse DAG W. Create Cr with parents exactly `(Cqr,)` and an absent explicit reuse-result ref.
   Prebuild owned response before storage commit. Submission/reservation/other heads stay fixed.
5. Return the selected result only after W/Cr/ref commits. Report **reuse**, not a new attempt,
   new empirical observation or a fresh execution completion.

Prevalidation mismatch rejects BEFORE recording Qr. Later reuse-publication/map/ref/allocation
failure can leave already-recorded Qr without satisfaction. That is inspectable pending knowledge,
not rollback of Qr or permission to create another Q/attempt/submit automatically. No transaction
spans Qr publication and W publication; postcommit missing response can leave complete W/Cr/ref.
This version deliberately does not promise resuming an arbitrary previously recorded pending Q.

## 4. Ordinary reuse association

Recommended example-local W convention (not a core kind or mandatory universal schema):

| Binding | Node |
| --- | --- |
| `role` | literal STRING `example-explicit-reuse-v1` |
| `request` | sub-DAG reference to NEW Qr |
| `attempt` | sub-DAG reference to selected OLD final attempt T2f |
| `result` | sub-DAG reference to actual OLD R2; also W root |

Suggested tree entry `reuse-<new-request-occurrence>`, explicit ref `reused-double`.
T2f continues to link to its ORIGINAL Q2. Do not reparent/rewrite T2f to Qr, create an initial
attempt for Qr, synthesize another local-success outcome or disguise W as a P/U/F packet.
Navigation Qr/W/T2f/Q2/I2 preserves what was newly asked versus what was actually executed.
A repeated explicit reuse choice gets a new request, not another trial; create-only authoring
under an existing submission/ref rejects. This is not a globally exclusive request-resolution
registry preventing a user from explicitly attempting a copied Q elsewhere.

## 5. Eligibility and policy

Only a publicly validated successful final attempt qualifies. P/U, absent/unknown/bootstrap,
failed F with evidence84, malformed history and unreturnable F reject. Service success/time/
logs/content-equal84 never imply eligibility. No automatic fallback to fresh execution on rejection.
For this application, recommend permitting recorded computational success with failed cleanup,
preserving that disposition, as Iteration12 does. This is explicit application policy, not
cleanup repair or a core rule; fixture resource operations still require known writer disposition.

Matching full I2 includes `value -> R1`, `producer -> T1f`, factor and declared fixture inputs.
Another producer T1bf yielding equal42 changes I2, so this initial rule rejects double reuse.
Different intent/binding/factor/type/gate/artifact bytes also reject. An intentionally different
valid old attempt with the SAME three dimensions can be explicitly selected; equal R2 does
not erase which attempt was chosen. Nothing here certifies complete capture or scientific validity.

## 6. Fresh-execution control and inspection

After W exists, separately record Qfresh through the existing request helper on an explicit
snapshot retaining W and old history. Prepare/execute/observe/receive via unchanged Floci APIs.
Fresh B creates only Tfresh for Qfresh; imported W/Qr/T2f are inert copied history. Require the
same complete binding/input IDs, distinct Q/T/job and potentially identical R2/root84. Do not
adopt Tfresh as a default or rewrite W; W remains linked to the deliberately chosen T2f.

An actual bounded installed acceptance can use one add job, one original double job, offline
reuse with NO job, then one deliberate fresh double job: three real jobs/nine P/U/F, not four.
The fixture can stop/archive after the original jobs, prove offline reuse, then explicitly resume
only the proven-stopped service for the fresh control. This is fixture policy, NOT application
workflow recovery/live-job restart. Exact modes/controller recipe remain engineering choices.

Python/CLI inspect W's new Qr versus old T2f/original Q2 and result84, then Qfresh/Tfresh/result84.
Full native bytes/all ordered parents/attempt population are stronger oracles than scalar output,
transport hashes, service counts or bounded CLI presentation alone.

## 7. Next gate

Review the candidate example/design/handoff. Separate bounded implementation/delegation and
publication GO is required. No DML/spec/diagram edits, worker/fixture/image/build/CI/provisioning/
experiment restart or design checkpoint commit/push occurred in this planning turn.
