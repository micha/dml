# Iteration 15 candidate design: intent-level reuse defaults and request overrides

Current delivery: **implemented, independently accepted, published and STOPPED through
`664a870`**, all six final exact-SHA CI41090059076 jobs successful. See
[RESULTS](RESULTS.md), [REVIEW](REVIEW.md) and [COORDINATION](COORDINATION.md).
The plan/approval/pending-GO statements below preserve chronology, not restart permission;
actual behavior belongs to the [implemented example convention](../../../dml/docs/intent-reuse-defaults.md).
No later turn/design publication authorized.

Status: **bounded design/example/handoff approved; implementation/delegation/publication GO pending**.
The user stated “approved.” This accepts the assistant-origin Idef/D/public-validation/decision-
parent/unused-S mechanics as the bounded plan, not implemented behavior or a native/public schema.
Exact engineering spellings remain refinable. Separate GO is still required; no worker/source/
build/fixture/CI operations or commit/push are authorized. Earlier preparation wording below
preserves provenance, not current plan status.

Status at preparation: **direction agreed; candidate mechanics for review, implementation/delegation/publication GO pending**.
The user agreed to the proposed bounded direction and offered example/design/handoff preparation.
This does not approve the exact ordinary Idef/D representation, validation projection, naming or
transaction choices below, or authorize implementation. Read [EXAMPLE](EXAMPLE.md) and
[HANDOFF](HANDOFF.md). Iteration14 is complete/stopped through8393a82; its GO is not inherited.
No design checkpoint commit/push requested. Exact engineering spellings remain refinable.

## 1. Agreed direction and stop line

- Version an intent definition's `reuse-by-default` or `execute-by-default` behavior.
- A request can use the default or explicitly request fresh execution/selected reuse.
- Both paths create a distinct new computational request Q. Reuse creates no new T/job;
  actual fresh execution alone creates a new attempt. Reuse is not another empirical observation.
- Preserve which policy version/override explains the decision in inspectable ordinary history.
- Execution and adoption stay separate. Even first execution on an absent selection does not
  automatically install a selection. Existing explicit select/adopt remain deliberate operations.
- Default reuse with **no recorded selection** chooses fresh execution without adoption.
  A present but invalid or mismatched choice is an error, never a silent fresh fallback.
- Two branches can retain different intent defaults without rewriting old definitions, choices,
  requests, attempts or results.

One intent and one explicitly known selection slot; callers still select the binding/full inputs.
Matching remains exact **intent URI/full binding DAG/full input DAG**, including producer witness.
No purity classification, URI discovery/registry, cache search/index, reuse facets/masks,
cross-implementation equivalence, automatic adoption/retry/recovery/fallback/cancellation,
generic evaluator/scheduler, resources/GC/UI, native entity, cloud/global tooling/release/package
or later feature. Prefer example-local PUBLIC API composition, not a public policy framework.

## 2. Read-only planning evidence and existing authorities

Planning inspects clean published DML `8393a82a14df0e5ac7e9af21e4466d9829f9808d`:

- [Glossary intent](../../../dml/docs/spec-next/glossary.md#intent),
  [request](../../../dml/docs/spec-next/glossary.md#request),
  [reuse selection](../../../dml/docs/spec-next/glossary.md#reuse-selection) and
  [adoption](../../../dml/docs/spec-next/glossary.md#adoption).
- [Versioned selection example](../../../dml/docs/versioned-reuse-selection.md) and
  [source](../../../dml/examples/reuse_selection.py): persisted S/V public revalidation,
  exact selected occurrence/final-T witness, branch choices and existing Q/W delegation.
- [Explicit reuse](../../../dml/docs/explicit-attempt-reuse.md) and
  [source](../../../dml/examples/explicit_reuse.py): own new Q, separate ordinary W, no dispatch.
- [Caller requests](../../../dml/docs/spec-next/caller-requests.md): Q has an exact existing
  role, Cq has exactly one parent and adds only Q, two A refs are published atomically.
- [Preparation](../../../dml/docs/spec-next/repository-execution.md#preparation-and-retained-workspace):
  public `prepare_exchange` validates consumed binding/inputs/full native closure without writing
  A/creating Q/T/dispatch; caller-Q mode additionally owns exact submission/Q validation.
- [Owning packet inspector](../../../dml/docs/spec-next/asynchronous-execution.md#immutable-packets-and-independent-reception),
  [transfer](../../../dml/docs/spec-next/transfer.md), [Python API](../../../dml/docs/spec-next/python-api.md)
  and [Floci](../../../dml/docs/spec-next/floci-execution.md) remain normative owners.

Concrete friction: adding policy fields directly to Q would change the consumed local role;
putting D beside Q in the same submission would violate the public "adds only Q" boundary.
There is also no public bare-binding/request-role reader to call from application code.
Recommend a **separate decision-bearing parent snapshot** and temporary public preparation for
owning source/Q validation instead of private `_request`/`_binding` codecs or protocol expansion.
These are source-inspected composition recommendations, NOT experimentally demonstrated here.

## 3. Behavior matrix

`default` below means no request override. Selection eligibility always uses the owning persisted
S/V/public inspector; an external response flag or same scalar84 is not authority.

| Override | Intent default | Selection consulted | Decision |
| --- | --- | --- | --- |
| default | reuse-by-default | absent explicit slot | execute-fresh; reason default-no-selection |
| default | reuse-by-default | valid and exact match | reuse-selected; reason default-selection |
| default | reuse-by-default | present, invalid/mismatched | error before D/Q; no execution |
| default | execute-by-default | not used | execute-fresh; reason default-execution |
| fresh | either valid default | not used | execute-fresh; reason override-fresh |
| reuse-selected | either valid default | valid and exact match required | reuse-selected; reason override-selected-reuse |
| reuse-selected | either valid default | absent/invalid/mismatched | error before D/Q; no execution |

Unknown override/default, missing or malformed intent definition always errors; it is not an
implicit execute default. **Absence means the selection tree entry does not exist**, not any
exception raised while decoding/revalidating a present entry. No broad KeyError/IO/validation
catch may turn an unusable choice into a miss.

Assistant-origin clarification accepted in the bounded plan: explicit fresh and execute-by-default do not
use S, so do not require its application-level framing/matching to be valid. They neither repair
nor replace it. Full reached **native** history must still be complete/profile-valid. This is a
deliberately declared execution choice, not fallback after failed reuse validation. It also lets
fresh execution use another valid binding/input triple without pretending the old S matches it.
On a reuse path, a present incompatible S remains an error; this bounded known-slot model is not
an automatically searched multi-key cache.

## 4. Recommended ordinary records (assistant-origin plan, not as-built schema)

### Idef: a minimal versioned intent default

Illustrative tree entry `double-intent` refers to an ordinary DAG with exactly:

| Binding | Node |
| --- | --- |
| role | literal STRING `example-intent-default-v1` |
| intent | literal canonical URI; also Idef root |
| default | literal STRING `reuse-by-default` or `execute-by-default` |

This is a minimal example-local intent definition, not a native intent kind, implementation
registry or full closure/install description. Binding/input names are separately caller-supplied.
Changing default produces a NEW Idef/tree/commit preserving the URI and all other tree entries;
parents exactly `(C,)`, create-only explicit ref, prebuilt response. Initial definition requires an
absent slot; updating an existing definition cannot silently change its stable intent URI.
No Q/T/job or selection change occurs. Generic raw authors remain cooperative/trusted.

Idef only records URI/control behavior in this slice; its version ID is NOT added to the initial
computational matching tuple. Changing default alone should not cache-bust matching work.
Do not generalize this to future intent definitions carrying computational dependencies: their
identity contribution is a later design question, not an implemented mask/facet rule.

### D: an ordinary request-policy decision description

Recommended bindings: literal STRING role `example-request-policy-decision-v1`;
sub-DAG references `intent-definition`, `binding`, `inputs`; literal STRING `intent-name`,
`binding-name`, `inputs-name`, `selection-slot`, `override`, `action`, `reason`.
Root is the `intent-definition` reference node. `override` is exactly default/fresh/reuse-selected;
action and reason follow the table. Add sub-DAG `selection -> S` **only when actually reusing**.
Fresh decisions intentionally use no selected attempt; an absent selection field is not unknown T.

D captures the exact definition version, computational dimensions, explicit names/override and
resolved reason. It is not Q, T, adapter status, proof of dispatch or another empirical trial.
Otherwise identical D content may deduplicate while Q occurrences remain distinct.

Recommend an explicit caller-chosen absent `decision_name` per action, added to C's tree, not an
unversioned global "pending" slot. Cdec preserves C's entire tree/adds ONLY D, parent `(C,)`,
create-only decision ref/prebuilt response. Naming/generation remains refinable; no new native
occurrence reservation or automatic replacement of unrelated entries is needed.

## 5. Recommended request ordering and public authority

A small candidate `examples/intent_defaults.py` imports installed DML/public exchange/transfer and
existing example-local selection/reuse helpers explicitly. It records, but does NOT launch.

1. Read pinned C/known intent entry, binding/input names, selection slot and override. Require exact
   Idef root/fields/node/datum types/canonical URI/enum and safe distinct tree-name usage.
2. Validate consumed source binding/inputs and COMPLETE native basis through PUBLIC preparation in
   a new helper-owned temporary child workspace, `request=None`. It creates only transport files/
   token, no A records/Q/T/B/external job. Dispose scratch BEFORE D authoring. Never start/execute/
   observe this validation workspace or preserve its token as a computation identity.
3. Resolve the table. If reusing, invoke existing PUBLIC-backed persisted-selection inspection,
   compare exact URI/binding/full inputs and capture exact S/final T/R/owning occurrence. All
   native/validation handles and pre-authoring scratch close before any actual-A puts.
4. Atomically publish D/Cdec/explicit decision ref as above. This is SEPARATE from recording Q.
5. On execute-fresh, existing `record_exchange_request` creates the operation's own Q/Cq/two refs
   on Cdec. Return an owned pending request; no job/attempt/start is hidden in the helper.
6. On reuse-selected, existing `reuse_selected(Cdec, known slot, ...)` revalidates/delegates its
   own Q and separate W. Compare actual returned Q dimensions and selected T/R with D. Do not
   accept caller-supplied RecordedRequest/decision/result flags as authoring authority.
7. ONLY the explicit application driver chooses existing prepare/stage/submit/observe/receive for
   an owning execute-fresh response. Reuse invokes no execution adapter. Serialized D is inert
   research state, not universal permission to dispatch/recover a request in arbitrary repositories.

Resulting spines (no extra fields on normative Q/T/W):

```text
C -> Cdec(D) -> Cq(Q) -> Cr(W)          # reuse; W still has only its original four bindings
C -> Cdec(D) -> Cq(Q) -> P/U/F in B     # explicit driver stages/executes fresh
```

D has a direct S reference on reuse; **W does not gain a direct D/S edge**. Q's exact submission
parent Cdec/known decision entry and W's original Q/T/R association expose the reason/choice.
No public whole-driver request-resolution/exclusivity/exactly-once claim is added.

## 6. Inspection, uncertainty and limits

Recommended example-local reader checks Cdec's exact one-parent/preserved-tree-plus-D delta,
Idef/D native shapes/types and EVERY action/reason/override/definition/name/selection claim against
that pinned parent, not a moved ref or current latest default. Recompute reuse decisions through
existing S/V public inspection. A submitted Q is validated through PUBLIC `prepare_exchange`
against Cq/Q in owned disposable files; public preparation owns exact local Q roles/submission,
not an application JSON/local-role codec. A satisfied W keeps its existing shape and links actual
new Q to D's publicly validated selected T/R. Generic history/transfer alone is not policy validation.
No original packet/expected/B/service/historical interpreter/source execution is required.

This reader costs temporary IO and public export; no efficient repository-native resolver is
promised. If the composition exposes a real seam gap, present exact authority/signature/friction
alternatives for review before adding a public reader/framework or calling private codecs.

Idef publication and D publication are individually atomic. D/Q/W/files/service are NOT one
transaction. A failed Q can leave D/Cdec; failed W can leave D and pending Q; late reuse projection
cleanup/response loss can leave complete D/Q/W. Fresh stage/submit/retrieval failures retain their
existing uncertainty. No error triggers automatic new Q, fresh fallback, adoption, ref repair or
retry. D without Q is only a decision basis, not a requested or attempted computation.

Supported creating-thread/single-wrapper lifetime, 8192-byte public framing, unchanged complete
transfer row/record/bundle profiles, capture/trust/authentication/cleanup/ephemeral-B limitations
persist. Native IDs are not authentication; these defaults do not certify purity/scientific truth.

## 7. Evidence and next gate

Recommend four actual local Batch jobs/twelve phases: add42; default-reuse absence deliberately
executes old double84; explicit fresh override double84; execute-default branch double84.
Selection/default hits/adoption/policy changes/explicit-selected override create no extra job.
Offline readers record why requests chose their path; native typed bytes/all ordered parents/
request-attempt populations and all-status/persisted service census corroborate counts.
See [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md).

Require native mismatch/malformed/miss-vs-error/unused-selection controls, original request/witness
preservation, meaningful genuinely-new Idef/D rows before late rollback/real map-full/response and
actual authoring-only pre/post-store-commit loss; existing Q/W authority stays separate. No source
omission/threshold/skip/profile weakening. Existing CI Macx86 outer20/other matrix10/strict budget
and all runtime timeouts stay unchanged; older Windows causes/initial Mac slowdown remain UNKNOWN.

Idef/D fields/root/names, public temporary preparation, separate decision basis, unused-S
execution rule and four-job controller are assistant-origin choices accepted as the bounded plan,
not as-built behavior; exact engineering spellings remain refinable. No new experiment/code/
spec/diagram edit, worker/build/fixture/image/CI restart, provisioning or commit/push occurred.
Next is separate implementation/delegation/publication GO, if requested.
