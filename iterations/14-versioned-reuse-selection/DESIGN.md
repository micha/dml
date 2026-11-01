# Iteration 14 candidate design: versioned reuse selection and explicit adoption

Status: **reviewed bounded plan; implementation/delegation/publication GO pending**.
The user subsequently stated “reviewed.” This records bounded plan review, not implemented
behavior or permission to restart worker/build/fixture/CI activity or commit/push. Exact engineering
spellings remain refinable; earlier preparation/review-pending wording below preserves provenance.

Status at preparation: **direction agreed; candidate details for review, no implementation/delegation GO**.
The user's “agreed” accepts the proposed bounded direction and preparation of the example/design/
handoff, not the exact representation below or permission to restart workers/builds/fixtures/CI.
Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md). Completed Iteration13 permissions are not
inherited; no design checkpoint commit/push requested. Exact engineering spellings remain refinable.

## 1. Agreed goal and stop line

Record a selected reusable successful attempt in immutable repository state. Later requests can
explicitly use that recorded selection. Fresh execution does NOT change the selection; explicit
**reuse adoption** records a fresh successful attempt as selected in a new snapshot. Two branches
can retain different choices for the same computation, without changing old selections or reuse
records. Neither selection nor adoption creates a computational request/attempt/job.

Keep Iteration13's exact **intent URI, binding DAG ID and complete input DAG ID** matching, including
producer witness. This is an initial matching tuple, not a new hash/mask/reuse-facet implementation.
Containing commits, request occurrences and transport metadata do not become matching dimensions.

No transparent reuse-by-default, history search/discovery, global cache index/registry, facets/masks,
cross-implementation equivalence, generic scheduler/evaluator/recovery/fallback, resources/GC/excision,
observer UI, native entity, cloud/second host/global tooling, release/package or later turn. Prefer
example-local public-API composition; no public reuse framework or native expansion presumed.

## 2. Planning evidence and existing authorities

Read-only inspection uses clean DML `b296fdb5acad4b8b1c7608aea3b1c5d0af6bd79c`:

- [Glossary](../../../dml/docs/spec-next/glossary.md#reuse-selection): reuse selection/adoption terms.
- [Iteration13 informative convention](../../../dml/docs/explicit-attempt-reuse.md) and
  [source](../../../dml/examples/explicit_reuse.py): exact packet authority, operation-owned new Q,
  separate Q/W writes and no new attempt/job. Existing W is an ordinary four-binding DAG.
- [Public inspector](../../../dml/docs/spec-next/asynchronous-execution.md#immutable-packets-and-independent-reception):
  `read_observation(packet, expected=...)` validates full history in disposable storage and returns
  owning fields; public save/load handle framing preserves independent expected Cq/Q.
- [Caller requests](../../../dml/docs/spec-next/caller-requests.md): owning Q publication/first registration.
- [Transfer](../../../dml/docs/spec-next/transfer.md): exact typed all-parent closure/profile/atomic import.
- [Python API](../../../dml/docs/spec-next/python-api.md): native handles/transactions/descriptions.
- [Floci](../../../dml/docs/spec-next/floci-execution.md): unchanged installed fresh-execution authority.

Concrete friction: the public inspector accepts packet files plus expected selection, not a bare
historical attempt ID. Merely recording T/R and later trusting those fields would bypass owning
outcome/Q/history validation. Merely recording old packet paths would leave selection dependent on
external files and encourage historical-path action. There is no currently public native historical-
attempt inspector or selection codec. Private exchange/local readers are NOT application APIs.

## 3. Recommended durable validation basis

Assistant recommendation, **not an agreed schema**: retain a small ordinary validation sub-DAG V
alongside a selection S. Capture the independently caller-owned expected HANDLE file through the
public loader, and the actual selected packet's `job.json`/`observation.json` as opaque bounded
BYTES. Each is limited by existing `exchange.MAX_DESCRIPTOR_BYTES` (8192). Do not persist another
full snapshot bundle: the selected native F history is already retained through commit parents.

Capture files into helper-owned disposable storage FIRST; validate those same owned copies through
public load/read operations. No re-read of mutable original headers after validation. Initial expected
comes from the caller's independently saved Cq/Q, never from incoming packet claims. Only actual
public validation supplies selected F/T/Q/R. Copying/IO is not filesystem atomicity or authentication.

Recommended S convention:

| Binding | Ordinary node |
| --- | --- |
| `role` | literal STRING `example-reuse-selection-v1` |
| `intent` | literal canonical URI, equal to validated requested intent |
| `binding` | sub-DAG reference to full selected binding |
| `inputs` | sub-DAG reference to full selected inputs |
| `request` | sub-DAG reference to ORIGINAL producing Q |
| `attempt` | sub-DAG reference to exact selected final T |
| `result` | sub-DAG reference to actual result R; also S root |
| `completion` | literal BYTES containing F's exact 16-byte ObjectId |
| `validation` | sub-DAG reference to V |

V has exact literal-BYTES bindings `expected`, `job`, `observation`, root `expected`. Its bytes are
existing public framing, not a second JSON/role/packed-record codec. Names/role/shape are example-local.
The completion datum is **metadata, not a native commit edge or retention root**: require F reachable
in the selected basis's ALL-parent history. The actual parent spine retains F and its complete closure.
The handle's serialized workspace remains inert data; load only its expected selection. Never observe,
start, follow/delete that workspace, or use receipt presence as proof of outcome.

A later reader takes caller-pinned C and the explicit named selection (recommended single slot
`selected-double`). Native typed reads obtain S/V and close handles. It exports exact F from A through
public transfer, materializes a new helper-owned packet using the captured bounded headers, loads the
captured expected with the public loader, then calls public `read_observation`. Require successful F,
exact S/F/T/Q/R/intent/binding/inputs agreement, exact ordinary shape/root/types, F in C's all-parent
history and complete bounded typed basis history. Public inspector validation handles/scratch close
before it returns. Initial selection/adoption can also dispose their materialized files before any
A write. Selected-reuse delegation may retain its newly owned packet through the existing Q/W
operation; disposing THAT projection afterward is a separate filesystem boundary and can fail after
Q/W publication. Do not mislabel it as pre-write validation scratch. Forged S flags/dataclasses/
literal84 never supply authority.

The pinned caller-selected repository state is now the source of the persisted expected choice;
reconstructed packet metadata is still checked against it and native history. This does not authenticate
who authored C or certify external truth. A fully coherent manually authored alternative valid selection
is a different recorded choice, not detectable fraud against an unstated user intention. Partial witness/
Q/metadata swaps and malformed/missing history reject. Supported writers remain cooperative/trusted.

This public-API composition intentionally costs export/temporary IO. It is a prototype recommendation,
not a promise of an efficient repository-native selector. If it reveals a genuine owning seam gap, present
concrete evidence/API alternatives for review; do not call private codecs or silently add a framework.

## 4. Initial selection publication

A deliberate `select` action takes pinned basis C, named binding/inputs/intent, explicit slot/ref,
old successful packet and independent expected file. Validate owned evidence, complete native history,
all-parent F retention and exact matching before any puts. Require the slot absent; no overwrite.

One A write preserves C's tree, adds only `selected-double -> S0`, creates Csel with `(C,)` parents
and a create-only explicit result ref. Prebuild the owned response before storage commit. There is
NO new Q/T/outcome/cleanup/job, and no existing head/submission/reservation/ref movement. Initial
selection of an already successful attempt does not count another empirical observation.

## 5. Explicit selected reuse and fresh control

`reuse-selected` takes pinned basis C plus explicit slot and requested binding/inputs/intent and
submission/return refs. It reads/revalidates S from THAT snapshot and checks the same three dimensions
before new Q. No historical packet directory, externally supplied attempt override, moving latest ref,
search or fallback is needed. Missing/invalid selection rejects; it does not choose fresh execution.

Prefer delegating to the existing Iteration13 authoring operation using the newly materialized owned
packet/expected, rather than another Q/W writer. Its existing ordinary W shape/role remains unchanged:
new Q, old selected T/result, separate transactions. Cqr's parent pins the exact selection-bearing C;
the known explicit slot in that immutable basis plus W's exact T/R establishes the recorded choice.
For this slice there is no extra third publication transaction/new W role/selection engine. Inspectors
can recover S from W's request-submission ancestry and known slot; do not claim W contains a direct S
edge. Actual writer-owned Q/W responses remain authority, not supplied descriptions.

A separately explicit fresh Q on a snapshot retaining S0/W imports them inertly into fresh B and
creates only Tfresh. Fresh F preserves S0 and W byte-identically, even if Rfresh equals Rold84.
Execution does not adopt Tfresh. Existing request/exchange/local/Floci protocols stay unchanged.

## 6. Explicit reuse adoption and two branches

`adopt` takes a pinned basis C retaining the existing slot S0 and the fresh successful F's owned
packet/independent expected file. Revalidate existing S0 from its persisted basis; validate the new
completion independently. Require identical intent/binding/full inputs, a distinct selected attempt,
and both supporting histories reachable through C's all-parent history. Same already-selected T is
rejected in this candidate application, not silently counted as fresh work. Cleanup-failed computational
success may remain eligible under the same explicit Iteration13 policy; never repair/reclassify it.

One A write preserves C's entire tree except replacing THAT slot's value with new ordinary S1/V1,
creates Cadopt with parents exactly `(C,)` and create-only explicit ref/prebuilt response. It creates
no Q/T/job and does not update old W, producing Q/T, existing heads or the prior selection object.
Changing the tree association in a new commit is not mutating S0. Adoption of mismatched computation
rejects, rather than redefining what the slot selects.

Use a sibling Ckeep with unchanged C tree and `(C,)` parent to demonstrate a true fork: explicit
`keep-old` ref selects S0; `adopt-fresh` selects S1. New requests explicitly using Ckeep versus Cadopt
reuse Told versus Tfresh. Equal result content does not erase their distinct selected occurrences.
Neither branch determines a repository-global winner or changes another branch's refs/history.

## 7. Failure, uncertainty and limits

Initial select/adopt are individually atomic S/V/tree/commit/ref batches. Invalid selection, P/U,
unknown/missing/unreturnable F, failed F with evidence84, corrupt/missing native closure, wrong-Q/
witness/metadata, or mismatched triple cannot publish selection/adoption or launch anything. Late
raw/different-ref, meaningful real map-full, allocation/response and consuming-commit failure abort
genuinely new selection rows together. Precommit authoring loss leaves no batch; postcommit missing
response can leave complete publication. Inspect explicit refs; no automatic repair/retry/resume.

Selected reuse inherits separate Q/W boundaries: Q may remain pending after W failure. Selection,
adoption, Q, W, packet materialization and service effects are NOT one transaction. Read/inspection/
transfer never creates an attempt or changes selection. Conflicts are not global exclusivity/exactly-once.

Metadata/profile or pre-authoring validation cleanup failure blocks successful publication. A later
projection-file cleanup/response failure may leave complete already-published Q/W; inspect its refs,
never duplicate Q or infer whole-operation rollback. No larger limits, hidden captured source hooks,
environment capture/auth/security/scientific-validity promises.
Native IDs are not cryptographic authentication; external resources may be unavailable or changed.
Exact normative owners remain existing contracts. S/V/W are ordinary DAGs, not new LMDB boxes.

## 8. Review and next gate

Candidate durable validation basis, fixed-slot reuse provenance, same-attempt rejection and helper/
fixture spellings need review; they are not additional user decisions or as-built behavior. Recommended
actual installed gate is still three jobs/nine phases: add, old double, explicit fresh double; selection,
selected reuse and adoption create NO fourth job. Prove service/old packet/expected/input/B OFFLINE
inspection/selection reuse, complete typed native bytes/ordered parents and branch-local choices.
See [acceptance story](EXAMPLE.md) and [conditional handoff](HANDOFF.md).

This planning turn edits only design notes. No DML/spec/diagram edit, worker assignment/restart,
build/test/fixture/image/provisioning/CI/experiment/commit/push. Next is candidate-plan review, then
separate bounded implementation/delegation/publication GO if requested.
