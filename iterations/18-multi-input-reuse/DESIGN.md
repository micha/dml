# Iteration 18 candidate design: multi-input reuse selection

Status: **direction agreed; candidate mechanics for review, implementation GO pending**.
The user accepted the proposed exact intent URI/full binding/full input matching after
clarification, then requested preparation for handoff. This authorizes planning, not exact
schema/API approval, delegation, experiments or publication. Read [EXAMPLE](EXAMPLE.md)
and [HANDOFF](HANDOFF.md). Current DML is clean published
`9f182be635207e03c8cb1cc4f58973632dfe97c9`; Iteration17 is accepted, complete and stopped.

## 1. Agreed capability and identity

Retain selected successful attempts for several input tuples without one displacing another.
A request either reuses the selected attempt for its exact dimensions or records fresh work
under the existing reuse default/explicit override. Fresh work does not automatically adopt.
Explicit adoption changes only the matching table entry in a new snapshot; old branches
retain old choices. Reuse always records a new Q, never another T or empirical trial.

Matching remains exact **canonical intent URI, full binding DAG ID, full input DAG ID**.
Source/interpreter/timeout and all captured inputs/producer witnesses contribute as before.
Intent alone describes purpose, not interchangeable implementations: buggy A(-3)->0 and
corrected B(-3)->-6 must not collide. The user confirmed keeping the original full-matching
proposal. A table scoped to URI/binding can avoid repeating those values in each physical
entry; the EFFECTIVE identity still includes all three. No opaque containing-commit/Q ID
is added to the key, and no mask, facet or cross-binding equivalence is introduced.

## 2. Read-only inspected authorities and public seams

- [Implementation selection](../../../dml/docs/versioned-implementation-selection.md) and
  [helper](../../../dml/examples/implementation_selection.py) own public strict definition/
  captured menu/default resolution. The existing choice's `selection-slot` means one S,
  not a table. Its exact old D/request reader must NOT silently acquire new meanings.
- [Versioned reuse selection](../../../dml/docs/versioned-reuse-selection.md) and
  [helper](../../../dml/examples/reuse_selection.py) expose PUBLIC `select`, `inspect`,
  `reuse_selected`, `adopt`. S/V retains successful F/owning Q/T/R validation framing,
  revalidated from repository history without original files. `reuse_selected` operates
  on an S in a TREE SLOT at the actual request basis; there is no public inspect-by-S-ID.
- [Explicit reuse](../../../dml/docs/explicit-attempt-reuse.md) owns original four-field W;
  [caller requests](../../../dml/docs/spec-next/caller-requests.md) owns exact own-Q/Cq;
  [preparation](../../../dml/docs/spec-next/repository-execution.md#preparation-and-retained-workspace)
  owns consumed binding/full inputs/exact Q. Existing local completion/receive and
  [transfer](../../../dml/docs/spec-next/transfer.md) own successful complete native history.
- [Glossary](../../../dml/docs/spec-next/glossary.md) owns vocabulary and
  [validation policy](../../../dml/docs/validation-policy.md) owns evidence selection/CI triage.

Recommend NEW example-local ordinary table/decision conventions composed from these public
seams. No private `_projection`, `_definition`, local role decoder or public framework needed
is established. Exact names/representation remain refinable; report a concrete seam gap
before expanding native/runtime scope.

## 3. Recommended ordinary table (assistant candidate)

One explicitly supplied known tree name, illustratively `double-a-reuse`, holds table M:

| Field | Candidate node/value |
| --- | --- |
| role | literal STRING for this new example convention |
| intent | canonical URI |
| binding | captured full binding sub-DAG; M root |
| entries | sub-DAG of the finite entry map |

The entries DAG has a literal role root and zero to SIXTEEN named entry links. Candidate
names are `input-<full input DAG ID hex>`: lossless rendering of an existing ID, NOT a new
reuse hash/facet or caller-defined approximate key. Each entry has exact ordinary fields:
`role`, captured `inputs`, captured `selection` S, literal STRING `selection-slot`; root=S.
Labels must agree with captured full inputs; duplicates/extra fields/wrong roots/types reject.
The sixteen-entry cap is a candidate finite example profile, not a user-selected general
cache limit. Over-cap publication rejects without eviction; no LRU, deletion or registry.

Every selected S stays in its OWN explicitly named tree slot. Table inspection validates
all bounded entries through PUBLIC `reuse_selection.inspect` at the query commit, compares
actual S DAG ID and URI/binding/inputs, and requires current tree-slot/S cross-links. Distinct
keys cannot alias a mismatching S. This deliberately uses the existing inspect-by-slot seam
rather than pretending S IDs alone are success authority. Slot names are lookup framing,
not computation identity. Table/selection/binding/input/decision names must not collide.

A present table is strict recorded selection state, not a hint: when consumed, any malformed
entry or invalid S rejects, including a nonmatching entry. This bounded ALL-entry public
validation is intentionally simpler than lazy indexing. An explicit fresh/default-execute
request does not consume table application framing, but still validates complete reached
native/all-parent/composite closure. Absence of the TABLE ENTRY or a matching KEY on the
reuse-default path permits fresh work; an unreadable/malformed present table never becomes
absence. A valid table for another binding/intent is incompatible, NOT a miss. Inputs missing
from the requested tree are an error, not an empty key. No other table/history is searched.

## 4. Publication, capture and explicit adoption

Recommend separate explicit operations, each with its own create-only ref:

1. `define_table`: optionally create absent EMPTY M for captured URI/binding. No Q/T.
2. Existing public `select`: capture a validated successful F into a NEW absent S slot.
3. `select_entry`: inspect M and that S, require absent exact key, then add only the new row
   to M at its known tree slot in one batch; other keys/tree entries unchanged.
4. `adopt_entry`: inspect the old matching row AND proposed new S, require same full tuple
   and distinct validated attempt occurrence, then replace only that row in a new M snapshot.

For adoption, capture fresh F with existing `select` into a NEW S slot rather than overwriting
an indexed old S slot through `adopt`. This keeps the current table coherent while the new
selection exists but is NOT yet adopted. Old S/V slots remain unchanged and reachable;
only M's mapping changes explicitly. This is candidate public composition, not new native
adoption semantics or permission to duplicate an execution.

Each M authoring batch closes inspection/projection handles BEFORE writes, prebuilds response,
preserves every non-table tree entry and uses exact `(C,)` parent. Definition/capture/table
selection/adoption/D/Q/W/execution are SEPARATE transactions. S capture failure publishes no
table change; table-update failure may leave a complete unindexed new S. Fresh success leaves
M unchanged. Lost response can leave a complete publication: inspect explicit refs, never
repair/relaunch/adopt/evict automatically. Old binding/source/input/S/V/Q/T/R bytes and refs
stay intact. Native history, not literal metadata IDs, supplies retention.

## 5. Request composition and pinned inspection (assistant candidate)

Recommend a new helper with explicit `intent_name`, implementation override, input tree name,
TABLE name and reuse override. PUBLIC definition inspection selects the actual captured binding
FIRST. When consumed, the supplied table must match that URI/binding; wrong A table for
selected B errors, never cross-reuses. An absent B table can permit fresh work. Existing Idef/menu/choice/defaults remain
unchanged; their old S slots are NOT reinterpreted as table slots. Only the explicitly supplied
new table controls this new helper, not the old helper's single-slot selection or a search.

Normal `default` with reuse-by-default resolves exact row; absence yields fresh. Explicit
`reuse-selected` requires that row. Explicit `fresh` or default execute-by-default ignores
unused table application framing. Capture chosen binding/full I through public preparation
without execution. No default change, table update or S adoption occurs while requesting.

Record a NEW ordinary decision role Dm, not appended fields in exact old D. Candidate captures:
strict validated Idef/selected choice/full binding/full inputs; explicit names/table name;
implementation and independent reuse overrides/reasons/action; table/entry/S links ONLY when
actually consumed, including a table-with-no-match if one was inspected. Actual native parent
pins all basis state. A new pinned reader recomputes from that parent, never latest refs or
response flags, and uses public exact non-None Q preparation plus strict original four-field W
association validation. Old `inspect_request`/supersession context readers own old D, not Dm;
general reader unification/lifecycle integration is NOT silently claimed by this slice.

Reuse delegates PUBLIC `reuse_selected` at Dm's actual commit and the matched S tree slot,
retaining normal own Q then separate W; fresh delegates public Q authoring then explicit adapter
action. Compare returned Q/Cq/W to actual submitted native/ref/decision history, including own-Q
substitution negatives; already-published batches survive a late response rejection. No attempt
on lookup/selection/adoption/inspection. The table/decision stores no copied bundle or new
success verdict; S/V/public packet authority remains owner. Full transfer closure is required
on hit, miss and fresh paths even when table framing is ignored.

## 6. Concrete learning and proportionate evidence

[EXAMPLE](EXAMPLE.md) proposes one actual selected binding, input DAGs I2/I3 and three LOCAL
attempts: double2->4, double3->6, explicit fresh double2->4. Two table entries coexist; repeated
requests reuse each; explicit adoption changes ONLY I2's selected attempt; true sibling keeps
old I2. Normal acceptance SEVEN Q/THREE T, including post-adoption and old-branch reuse;
metadata/default/transfer readers add none. No producer job or Batch/SSH/Docker/image needed.
A second captured binding can exist in the menu for nonexecuting cross-binding negatives.

Primary controls: exact table scope/key/S-slot/typed input and producer-witness matching,
multiple retained entries/miss versus malformed/wrong-scope/duplicate/cap, independent fresh/
reuse/default decisions, distinct attempt adoption (equalR4 does not merge attempts), old bytes/
branches/only-one-row update, exact own Q/parent/W, full closure and transferred offline reads.
Meaningful NEW table authoring late rollback/response/commit/map-full and safe pre/post author-only
loss use genuinely absent predicted actual-A rows; rely on unchanged S/Q/W/exchange fault suites.
No automatic second full/duplicate workflow or all-source census. Actual outcomes/counts/receipts
come from completed commands/XML, original failures and uncertainty preserved.

## 7. Deferred scope and stop

No generic/global cache, history discovery, table eviction/removal/merge, producer matching
change, masks/facets/equivalence/cross-implementation reuse, new menu installation/registry,
resource/scheduler/observer/cloud/native entity or universal reader framework. Example-local
lookup within one explicitly selected bounded table is the intended new capability, not a
claim of scalable index efficiency or scientific certification.

VP-001 revisited for this planning checkpoint: remains OPEN/UNKNOWN; Iteration17 green is not
old-runtime diagnosis or a standing waiver. No async observer/LMDB handle lifetime/affected
old story change is presumed. Related change or recurrence needs fresh scope/triage, not
speculative fixes. Planning authorizes no investigation/build/story/CI restart.

Next: review these candidate details, then separate implementation/delegation/publication GO.
DML/spec/diagram stay unchanged; no worker/experiment/provisioning/commit/push started or design
checkpoint requested. Completed Iteration17 GO is not inherited.
