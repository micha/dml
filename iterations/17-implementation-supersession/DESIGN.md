# Iteration 17 candidate design: implementation supersession

Status: **direction agreed; candidate mechanics for review, implementation GO pending**.
The user agreed to the offered next slice and example/design/handoff preparation. This is
not approval of exact record/API details, implementation, delegation or publication.
Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md). Current DML is clean published
`e0089323cac3bc29b4301b4d3e7340d345d20d7a`; Iteration16 is complete and stopped.

## 1. Agreed direction

One intent has two captured implementation bindings. Record that B supersedes A, with a
structured distinction between a **correctness fix** and an **operational replacement**,
and link supporting ordinary evidence DAGs. Explicitly make B the default in a new snapshot.
Preserve A, its selected attempts/results and old branch defaults; A remains explicitly
selectable. Distinguish what a historical request knew at its pinned snapshot from separately
selected later knowledge about that implementation.

Deprecation is initially advisory, not automatic invalidation, deletion, cross-implementation
reuse or forced execution. A discrepancy, a supersession declaration, default promotion,
fresh execution and reuse adoption remain different operations. A reason describes a
recorded assessment, not DML certification of scientific validity or defect impact.

The worked example uses NEW intentionally buggy A and corrected B test bindings. It does
**not** claim that Iteration16's actual multiplication implementation has a defect.

## 2. Existing authorities and inspected seams

Read-only planning inspects published e0089323:

- [Implementation selection](../../../dml/docs/versioned-implementation-selection.md) and
  [helper](../../../dml/examples/implementation_selection.py): exact ordinary Idef/menu/choice/D
  shapes; public `inspect_definition`, `update_default`, `record_policy_request` and
  `inspect_request`. `update_default` changes only the default label and preserves all other
  tree entries. D's actual parent pins the whole decision basis, not just the definition.
- [Versioned selection](../../../dml/docs/versioned-reuse-selection.md): explicit S/V captures
  and revalidates selected successful history; exact URI/full binding/full inputs remain.
- [Caller requests](../../../dml/docs/spec-next/caller-requests.md): own Q and exact submission;
  [repository execution](../../../dml/docs/spec-next/repository-execution.md): local explicit
  prepare/execute/return; [packet authority](../../../dml/docs/spec-next/asynchronous-execution.md#public-surface-and-descriptions):
  public `ExchangeHandle`, `observe_exchange`, `read_observation`, `receive_observation`.
- [Transfer](../../../dml/docs/spec-next/transfer.md) owns complete typed all-parent history;
  [glossary](../../../dml/docs/spec-next/glossary.md) owns vocabulary. **Implementation
  supersession** here is a document-local declared relationship, not adapter working/done.

Appending lifecycle fields to existing exact Idef/choice/D would silently change their
contract. Recommend a separate ordinary declaration at an explicitly known tree entry,
with a new example-local helper/reader. Existing request/default/reuse operations remain
unchanged. No private `_definition`/local-role decoder or public framework gap is established.

## 3. Recommended declaration mechanics (assistant candidates)

Use one explicitly known slot, illustratively `double-supersession`, holding ordinary L:

| Field | Candidate node/value |
| --- | --- |
| role | literal STRING for the new example convention |
| basis | literal BYTES containing the pinned pre-declaration DML commit ID |
| intent-name | literal STRING naming the definition in that basis |
| intent-definition | sub-DAG of that captured definition |
| predecessor-label / successor-label | literal STRING labels from its two-member menu |
| predecessor / successor | captured choice sub-DAGs, not moving tree/ref lookups |
| reason | literal STRING `correctness-fix` or `operational-replacement` |
| evidence | sub-DAG of supporting recorded evidence |

Recommend root = predecessor choice. Captured choices retain full binding IDs/code/tree/slot
names. Labels aid inspection; they are not stable implementation identities. Both endpoints
must be distinct members of the SAME public-validated captured definition/menu. Same-binding,
self-successor, unknown member/reason, wrong types/roots and capture drift reject.

Candidate `record_supersession` pins C, calls PUBLIC definition inspection, resolves the
explicit evidence tree entry, validates complete native closure, then closes all read/
projection handles BEFORE one L/tree/new commit/create-only ref batch. Require absent L slot,
noncolliding explicit names and exact parent `(C,)`; preserve every other entry. Prebuild
response before storage commit. No Q/T/workspace/job/default change/selection change.

The basis ID is data, not a native commit edge. A reader must verify its presence in the
query commit's ALL-parent ancestry before PUBLIC definition inspection at that exact basis;
never trust a path, latest ref or serialized definition/choice verdict. Compare captured
DAGs/labels with that public result. Current applicable definition must have the same intent
URI and captured menu/choices; default movement alone does not make the relation drift.
This is one fixed declaration/menu, not installation/menu evolution or successor-chain lookup.

An evidence link asserts support; the metadata reader does NOT certify its relevance or
truth. Example-local code separately checks the demonstrated counterexample's actual
selected S/T/result/typed input and researcher-asserted expected value through public native
reads and successful-history authority. A fully coherent alternative assessment is another
recorded claim, not authenticated against an unstated author intention.

Exact roles/filenames/schema/response spellings are refinable. These recommendations are
for review, not implemented behavior or additional user decisions.

## 4. Advisory status, explicit promotion and reuse

Publish L first. A remains the default at C_L: merely recording a declaration does not
silently promote B, adopt a result, disable A's slot or rewrite any outcome. Then explicitly
call existing `update_default(C_L, default_implementation=B)` to create C_B. It preserves
L/menu/bindings/reuse default/selections and changes ONLY Idef's default label.

L and promotion are SEPARATE transactions. Lost response/late error can leave L without
promotion; there is no whole-operation rollback, automatic completion/retry or hidden ref
movement. The declaration's old captured Idef remains retained after new Idef content appears.

Requests use the unchanged implementation/reuse helper. Normal requests on C_B resolve B,
then B's slot; A's selected result never satisfies B. Explicit A remains eligible for its
OWN selected successful attempt, or separately requested fresh work, under existing exact
matching. "Deprecated" does not reclassify an old computationally successful outcome as
execution failure or mean every predecessor result is incorrect. Operational replacement
neither declares old results incorrect nor certifies them correct.

No new acknowledgement/ban/invalidation/purity/equivalence policy is assumed. An explicit
label does not by itself mean fresh execution. No new T is created by reuse or inspection.

## 5. Two clearly labelled inspection views

Recommend a read-only `inspect_request_context` composing existing PUBLIC `inspect_request`
with the explicit known lifecycle slot. Require exact non-None Q/Cq and optional actual W;
recompute the actual D parent and use **D.base** for as-known-then metadata.

- **As known then:** look up the known L slot in the request's actual decision basis.
  Genuine absence means "no declaration in this slot at this snapshot", NOT "implementation
  certified healthy". Present malformed/incompatible L errors, never becomes absence.
- **Explicit knowledge view:** optionally supply an immutable `knowledge_commit`. Read THAT
  snapshot's declaration and report its relation to the request's actual full binding.
  Label this separately; do not alter historical D/Q/T/W or substitute the current default.

Do not automatically use latest refs, search all records or infer a total chronological
ordering between branches. Here **as known then** means declaration state AVAILABLE in the
pinned request basis, not proof a person/agent consulted or understood it. The unchanged
request helper does not interpret L; this new reader supplies the advisory view. No hidden
consultation/acknowledgement record or claim of changed default-resolution authority.
A supplied knowledge snapshot may be a later descendant or a
sibling; the response names both contexts, not an invented global as-of time. The two
captures must refer to the same intent/captured menu for this bounded example. Report the
request binding as predecessor, declared successor, or no recorded declaration in the known
slot; successor status is not deprecation of B. Invalid supplied scope/IDs/types fail.

Ordinary native parent/tree history already retains L in later request bases. Recommend no
new policy fields in exact D/Q/T/W and no new persisted merged "historical truth" record.
Readers need only transferred pinned roots, not original packet/B/source execution. Complete
native closure remains required on absence/fresh paths as well as selected reuse.

## 6. Concrete learning and proportionate validation

Recommend a small **current-installed local, TWO-attempt** demonstration, not another Batch
fixture: intentionally buggy A(-3) -> 0; corrected B(-3) -> -6. Use existing caller Q,
local execute, public completed observation/explicit-ref receive and S/V authority. Observe
completed history AFTER actual local child reaping; no new asynchronous lifecycle mechanism,
phase-hold experiment or unsafe process termination. Exact engineering orchestration remains
refinable; report a public seam gap rather than expand protocol/native scope.

Four normal request occurrences: fresh A, fresh B, explicit A reuse on the new branch and
A reuse on the old branch; only TWO fresh attempts. Declaration/evidence/default publication,
operational-reason sibling and readers add none. No producer job is needed for this standalone
literal-input example; no changed producer-witness matching rule follows from that simplification.

Primary controls: declared reason/endpoint/evidence identity and strict metadata; advisory
publication versus explicit promotion; predecessor versus successor context; actual D.base
versus latest/explicit knowledge; old bytes/branches/full-input matching; unknown/malformed
entries; wrong old Q; one new authoring batch's meaningful late rollback/loss with genuinely
absent predicted rows and known old-proof preservation. Do not replay unchanged Q/W/transport
fault matrices. See [HANDOFF](HANDOFF.md) for conditional execution/review/CI boundaries.

Follow [validation policy](../../../dml/docs/validation-policy.md): focused changed invariants
and small actual installed workflow primary, one worker final standard gate, risk-based
independent checks, actual final-SHA CI/report triage. No prebaseline/second full/whole-source
inventory/duplicate fixture or automatic all-six-green gate. Derive exits/counts/receipts
from real commands and reports, never presumed success; preserve original failures and
reconstruction qualifications. No new exclusions or threshold/budget changes assumed.

## 7. Deferred work and planning stop

No generic registry/deprecation database/impact scanner/ban/default policy, successor chain,
new menu installation/resources, cache discovery/index/facets/masks/cross-implementation reuse,
scheduler/native entity/remote service/UI/release feature. No production integration or
specification/diagram change by design agreement alone.

[VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md) revisited at this planning
checkpoint: remains OPEN/UNKNOWN. Iteration16's actual Mac15 pass did not diagnose the old
Mac14 ENOENT. Proposed slice changes advisory authoring/readers, not async observation/LMDB
handle lifetime/affected old story tests. Pause and separately scope investigation if those
changes become necessary or a signature recurs. No standing waiver or investigation GO.

Next: review this design/example/handoff, then separate implementation/delegation/publication
GO. No worker/source/spec/diagram/build/fixture/image/CI/experiment/provisioning/commit/push
started. Existing implementation stays clean e0089323; no design checkpoint requested.
