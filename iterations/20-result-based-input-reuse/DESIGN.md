# Iteration 20 candidate design: result-based input reuse

Status: **DEFERRED historical candidate; not the active Iteration20 plan or implementation handoff**.
Replacement: [recorded argument maps](../20-recorded-argument-maps/DESIGN.md) (candidate for review,
separate implementation GO required).
The user redirected Iteration20 to [value arguments and separate provenance](../../discussion.md#iteration20-redirection-value-arguments-and-separate-provenance).
The original preparation below is retained, not approved/as-built behavior or implementation GO.

Original status: **direction agreed; preparation authorized; candidate for review; implementation GO pending**.
The user accepted the producer-reference distinction and asked to prepare the iteration.
Exact schemas, API names and story counts below are assistant recommendations, not as-built
behavior or additional user decisions. Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md).
Development GHA stays disabled; the Iteration19 native investigation stays PAUSED.

## 1. Goal and agreed direction

A fresh upstream attempt producing the SAME result sub-DAG can permit downstream reuse
without being mistaken for the original upstream attempt. Preserve the complete downstream
input DAG and actual upstream provenance, while making the reuse matching policy explicit
and versioned. Old snapshots/requests keep their original meaning.

Document-local **producer witness** means the input's recorded reference to the selected
upstream final attempt. It is not a new native entity or proof of scientific correctness.
A result may have identical content across distinct attempts; neither content deduplication
nor downstream reuse supplies another independent downstream empirical observation.

Two proposed policies:

- `exact-inputs`: downstream intent plus complete input DAG identity, including producer witness.
- `result-inputs`: downstream intent plus a fixed projection retaining the exact result sub-DAG
  and other declared computational arguments, but excluding ONLY the producer witness.

Both continue Iteration19 intent-scoped matching: requested versus historical producing
implementation bindings remain distinct provenance, not automatic reuse partitions.
Result-based matching is a user declaration that this consumer does not depend on the excluded
producer occurrence. Consumers that inspect producer identity/methodology need exact matching
or an appropriately different intent. DML does not certify that the declaration is true.

## 2. Read-only source findings and public authorities

- [Composed steps](../../../dml/docs/composed-recorded-steps.md) and
  [helper](../../../dml/examples/composed_execution.py) link `value` to R and `producer` to
  final T. Changing T changes the full input DAG ID even when R stays identical. Existing
  helper also declares Floci endpoint/bucket/gate/exit-code/artifacts; it is NOT a generic
  witness-erasing input projector and must not silently drop those fields.
- [Intent-scoped helper](../../../dml/examples/intent_scoped_reuse.py) validates public S
  selections but keys Mi rows by exact input ID. Its resolver and pinned reader compare exact
  inputs. Removing one equality check does not implement this iteration's projection policy.
- [Selection](../../../dml/docs/versioned-reuse-selection.md) and
  [helper](../../../dml/examples/reuse_selection.py) provide PUBLIC `select`/`inspect` for
  original successful Q/T/R/F and producer occurrence. Reuse that authority, not `_projection`,
  private packet-role decoding, forgeable response flags or relabelled historical expected Q.
- [Caller requests](../../../dml/docs/spec-next/caller-requests.md),
  [exchange preparation](../../../dml/docs/spec-next/repository-execution.md),
  [local execution](../../../dml/docs/spec-next/local-execution.md),
  [transfer](../../../dml/docs/spec-next/transfer.md) and
  [Python API](../../../dml/docs/spec-next/python-api.md) continue to own exact Q, execution,
  full native closure, storage and lifetimes. Q ALWAYS records full actual inputs, not projection.

Recommend a NEW example-local helper and reader. Old Mi/Di/exact-binding helpers, their roles,
readers and composition contracts stay unchanged. Any genuinely missing public seam must be
reported before scope expansion; native/API/framework changes are not presumed necessary.

## 3. Fixed witnessed-input profile and deterministic projection (candidate)

Use a NEW minimal synchronous-local consumer input convention, not the old Floci input schema:

| Field | Candidate value |
| --- | --- |
| role | literal STRING identifying this fixed input profile |
| value | sub-DAG link to the selected upstream result R; also input root |
| producer | sub-DAG link to the SAME selected upstream final attempt T |
| factor | literal I64; two in the worked story |

Strictly validate fields/root/node types. Public upstream S inspection supplies exact R/T/F
and success authority; require `value == S.result` and `producer == S.attempt`, with retained
upstream history. A syntactically valid T link alone is not success or association authority.
The upstream S is a separate explicit immutable tree slot supplied to authoring and captured
by the decision/row; it need not become another computational input field.

The result projection is an ordinary DAG with NEW projection role, root=`value`, and exactly
`role/value/factor`. Preserve the FULL result DAG ID, not its scalar root; retain factor type
and value. Do not flatten nested result structure, normalize types, ignore arbitrary fields,
recursively strip every producer-looking binding or hash opaque full input IDs.

`exact-inputs` uses full input ID directly. `result-inputs` uses the projected DAG ID. Both
require the same strict input profile and public witness validation before matching. A malformed
input/failed upstream/incorrect witness is an error, never a miss or a reason to execute fresh.
Unknown/extra fields reject rather than silently disappear. The only excluded input dimension
is `producer`; implementation exclusion is the already established intent-scoped boundary.

Use native object construction to obtain a deterministic projection ID. Nonexecuting inspection
must be read-only with respect to the target repository: use an isolated disposed scratch store
if needed to recompute IDs; no target puts, permanent scratch refs or retained handles. Bindings'
canonical order must follow native encoding, not Python iteration order or a new ad hoc hash.

## 4. Versioned policy, table and selections (candidate)

Recommend ordinary NEW policy P, table Mp and decision Dp roles; illustrative labels only.
P contains fixed profile/version and mode `exact-inputs` or `result-inputs`, no arbitrary mask.
It is explicitly named in the snapshot tree. Updating the policy slot creates a new snapshot;
requests capture the exact P ID from their actual decision basis. No policy override/default
framework or automatic policy inference is added. Reuse-versus-fresh controls remain separate
from identity mode and may compose the existing public intent/default inspection conventions.

Mp scope is canonical downstream intent URI plus exact P ID. Zero to sixteen unique entries:
key rendered from the chosen input identity, with original full input ID, downstream immutable
S slot/link, and original input's upstream immutable S slot/link. The row retains full original
provenance even when keyed by a projection. Publicly inspect BOTH S selections and check:

1. downstream S's intent/full inputs match row;
2. original full inputs match their upstream S's exact R/T;
3. recomputed policy identity matches key;
4. slots at the pinned commit still link the captured S IDs; all history is retained.

Validate ALL entries, including nonmatching ones. Requested upstream S/full inputs are independently
validated; key equality never substitutes for those checks. Wrong policy/table role/intent is an
error, not an empty table. Existing Mi or old input profiles cannot masquerade as Mp.

Two full inputs differing only in producer witness collide deliberately under result mode.
Insertion requires absent key. Replacing the selected downstream attempt requires explicit
one-key adoption of a different successful attempt occurrence, with fresh immutable S capture;
equal result bytes do not make two attempts one occurrence. No automatic overwrite/adoption.
Removal deletes only the selected key in a new snapshot, preserving other rows, S slots/history
and old branches, as in Iteration19. A policy change does not rekey/migrate old tables: explicitly
construct a separate table and revalidate selections under its policy. Both modes can coexist.

## 5. Request, satisfaction and pinned reader (candidate)

Resolve the requested binding and full actual inputs, exact policy and requested upstream S.
For selected reuse, validate the table and selected historical downstream S/upstream S, compare
intent plus the policy-derived identities, and record both full input IDs/provenance chains.
Fresh/default miss remains a pending new Q until explicit adapter dispatch; explicit reuse miss
errors before Dp/Q. No automatic history discovery, fallback, upstream execution or adoption.

Publish Dp capturing P, actual full inputs, requested upstream S/slot, requested binding, mode,
identity, action/reason and consumed table/row/historical S links where applicable. Its actual
parent pins the decision basis. Then separately PUBLIC-record own Q using full requested inputs
and validate exact returned Q/Cq/ref/tree before the separate ordinary four-field W transaction.
W links own new Q to selected OLD downstream T/R. Original downstream T retains its original Q
and original upstream witness; never forge a completion of the new Q or relabel the old T.

Pinned reader recomputes the policy, identities, both witness associations and exact decision/
submission/satisfaction parents/deltas from native history and public S/Q authorities. It exposes
requested full inputs/upstream producer separately from historical executed inputs/upstream
producer. This distinction is mandatory: a reused downstream attempt did NOT execute with the
new upstream witness. A summary must link new request/W and historical downstream T explicitly,
not claim a newly executed chain or reuse the old fresh-only summary helper unchanged.

Publication remains separate policy/table/capture/adoption/decision/Q/W/dispatch boundaries.
Close validation/scratch handles before target writes. Use single-batch mutations, exact parent,
create-only explicit refs and preallocated responses. W abort can leave Q pending; lost response
can leave complete publication. No whole-driver rollback, retry or exactly-once effects claim.

## 6. Scope and assurance

[EXAMPLE](EXAMPLE.md) proposes SEVEN Q/SIX synchronous LOCAL attempts across retained main/exact
sibling refs, including same-R/different-T downstream reuse, exact-policy miss with real fresh
execution, and different-R miss yielding86. No extra computational support occurrences in this
acceptance history. Fresh readers/transfer/metadata are nonexecuting. No Batch/SSH/Docker/service.

Focus negatives on swapped/failed upstream witness, result DAG versus scalar equality, factor/
types/extra fields, policy or slot substitution, poisoned nonmatching rows, own-Q versus old-Q,
projected rather than full Q inputs, and false downstream execution provenance. Representative
NEW projection/table/decision-W rollback/loss tests supplement existing native/S/Q evidence.
No generic masks/facets/native IDs/cache discovery/index/scheduler/resources/restrictions/UX
namespace cleanup, lifecycle-reader unification or runtime/LMDB repair.

Follow [validation policy](../../../dml/docs/validation-policy.md), with development GHA launch
requirements superseded by the [user's disable decision](../19-intent-scoped-reuse/GHA-DISABLED.md).
One unchanged final worker full gate after future GO, focused local acceptance and risk-based
independent review; no duplicate full/story ritual. Native investigation and VP-001 remain
PAUSED/OPEN UNKNOWN respectively; this planning does not diagnose them or grant a waiver.
No implementation/build/story/CI/publication starts from this candidate.
