# Advisory implementation supersession

Status: informative, implemented **example-local** convention over public APIs.

## Authority boundary

This page owns [implementation_supersession.py](../examples/implementation_supersession.py),
not a native entity, lifecycle registry, installation framework or public policy API.
[Implementation selection](versioned-implementation-selection.md) owns unchanged Idef/menu/
choice/D and exact Q inspection. [Versioned reuse selection](versioned-reuse-selection.md)
owns S/V successful-history authority; [explicit reuse](explicit-attempt-reuse.md) owns W.
[Caller requests](spec-next/caller-requests.md) owns Q/Cq; [exchange](spec-next/repository-execution.md)
owns explicit local dispatch/return; [public observation](spec-next/asynchronous-execution.md#immutable-packets-and-independent-reception)
owns packet validation. [Transfer](spec-next/transfer.md) owns complete typed ALL-parent
closure; [Python API](spec-next/python-api.md) owns handle/storage lifetime.

## One fixed advisory relationship

One intent's already captured two-member menu can declare B supersedes A. Structured
`correctness-fix` versus `operational-replacement` records motivation and links ordinary
evidence. A reason/evidence link is a recorded assessment, **not authentication, scientific
certification or automatic impact calculation**. Operational replacement neither asserts
old results incorrect nor certifies them correct. A completed computation can succeed while
producing a scientifically surprising result.

The explicitly known tree slot holds ordinary L, with exactly:

| Field | Node/value |
| --- | --- |
| role | literal STRING `example-implementation-supersession-v1` |
| basis | literal BYTES containing exact pre-declaration commit ID |
| intent-name | literal STRING definition tree name |
| intent-definition | captured definition sub-DAG |
| predecessor-label / successor-label | literal STRING menu labels |
| predecessor / successor | captured choice sub-DAGs; predecessor is L root |
| reason | literal STRING `correctness-fix` or `operational-replacement` |
| evidence | supporting ordinary sub-DAG |

Both endpoints must be distinct members of the same public-validated definition/menu.
Strict names/shape/root/node/datum types, reason enumeration, basis ancestry, captured
choices and current definition/tree cross-links reject malformed or drifting metadata.
Labels are scoped names, not implementation identities. Current intent URI and captured
menu/choices must match; default-only promotion remains compatible. This is not a successor
chain, general menu evolution or installation operation.

Basis bytes are **data, not a native commit edge**. Inspection requires the exact stored
basis in the query commit's ALL-parent ancestry, then calls public definition inspection
at that basis. Complete native transfer closure is checked even on genuinely absent-L
paths, including other parents/composite-only descendants. Serialized verdicts/latest refs/
original paths cannot replace public authority. Evidence framing validates native closure,
not evidence relevance or truth; a coherent different assessment is another claim, not
fraud detected against an unstated author intention.

## Separate publication, promotion, work and adoption

`record_supersession` requires explicit immutable C, absent L slot, distinct definition/
binding/selection/evidence tree names, known labels/reason and create-only ref. It resolves
evidence at C, closes all public inspection/native handles, then atomically adds only L,
preserves every other tree entry, creates a new commit with exact `(C,)` parent and explicit
ref. Its owned response is allocated before storage commit. It creates no Q/T/job, changes
no default/selection, and does not interpret prior results as failures.

Only a separate call to the existing `update_default` promotes B. L publication does not
silently promote, suppress A's selection, adopt a result or force fresh work. Old exact
Idef/menu/choice/D/Q/T/W shapes remain unchanged. Existing request resolution does not
interpret L: advisory inspection is separate. Explicit A remains selectable and eligible
for its own matching successful attempt; A never satisfies B by sharing intent/input/result.
Fresh B success does not install S_B. Full matching/producer-witness semantics are unchanged.

L/evidence/promotion/Q/W/files/external work are separate boundaries. Late ref/allocation/
real map-full/consuming commit failure rolls back the individual L batch; pre-store loss
leaves no batch, postcommit lost response may leave complete publication. Existing explicit
refs/history must be inspected; no automatic repair/retry/promotion/relaunch follows errors.
Tests terminate only authoring-only processes, never an uncertain live computational child.
No physical power-loss, whole-driver atomicity or distributed exactly-once claim follows.

## Two separately labelled knowledge views

`inspect_request_context` composes public exact non-None Q/Cq inspection and optional original
four-field W validation. Its `decision` retains original implementation/reuse reasons.

- `as_known_then`: known-slot metadata at **actual D.base**, not Cq, latest/default ref or
  a caller-supplied historical flag. The view names this exact immutable context.
- `explicit_knowledge`: optional caller-selected immutable `knowledge_commit`, separately
  named and classified against the request's actual full binding. Compatibility is required
  even if that snapshot genuinely lacks L. It may be a descendant or sibling; no global
  chronological ordering is inferred.

Views report `no-recorded-declaration`, `predecessor` or `successor`. Absence means only no L
in that slot at that snapshot, **not implementation health**. Present malformed/incompatible
L errors, never becomes absence. The declared successor is not deprecated simply because
L describes its predecessor. Available advisory state is not proof the caller consulted or
understood it; no new acknowledgement/ban/consultation record is claimed. Inspection neither
rewrites historical D/Q/T/W nor persists a merged historical truth or dispatches anything.
Transferred pinned roots suffice without original packets/B/input/source execution.

## Public example-local composition

Copy this helper and `implementation_selection.py`, `reuse_selection.py`, `explicit_reuse.py`
together; import installed DML rather than a checkout runtime:

```python
import implementation_supersession as advisory

L = advisory.record_supersession(
    "A.dml", commit=C, intent_name="intent", slot="supersession",
    predecessor_label="a", successor_label="b", reason="correctness-fix",
    evidence_name="evidence-fix", ref="declared",
)
# A is still default. Explicit separate promotion uses existing helper.
B = advisory.policy.update_default(
    "A.dml", commit=L.commit, intent_name="intent",
    default_implementation="b", ref="promoted",
)
view = advisory.inspect_request_context(
    "A.dml", commit=Cq_old, request=Q_old, decision_name="decision-old",
    slot="supersession", satisfaction_commit=Cr_old, knowledge_commit=B.commit,
)
```

Close other physical-repository handles before invoking helpers. No new CLI policy framework
is added; ordinary native CLI inspection remains available.

## Evidence and limits

[Strict metadata/context tests](../tests/python/test_implementation_supersession.py),
[new authoring rollback/loss](../tests/python/test_implementation_supersession_atomicity.py),
[controller oracles/blockers](../tests/python/test_implementation_supersession_fixture.py)
start no computational/service fixture. The explicit
[installed story](../tests/supersession/story.py) uses NEW intentionally buggy A(-3)->0 and
corrected B(-3)->-6, not a defect claim about Iteration16 A:

```sh
env -u PYTHONPATH /path/to/installed/python -B tests/supersession/story.py run /fresh/parent/story
```

Exactly four normal Q/two real local attempts: fresh A, fresh B, explicit A reuse on promoted
branch and A reuse on true keep-A sibling. Evidence/L/promotion/operational sibling add none.
Synchronous execute reaps actual direct computational children before completed public
observation/receive. After S/V capture and both attempts, original packet/expected/workspace/B
paths become unavailable; copied offline clients actively block transport imports and spawn.
Fresh transferred readers distinguish actual old knowledge from explicitly selected fix or
operational branches. These controls are trusted finite local evidence, not sandboxing,
full environmental capture, every platform/process-memory assurance or scientific validity.

The helper stays in unchanged ROOT-source coverage with no new exclusions/threshold changes.
Ordinary L adds no native keys/boxes or storage relationship changes; as-built diagram reviewed
without a technical edit. Actual exits/counts/provenance, original failed probes/controller
correction, installed acceptance and publication/CI limits belong to
[Iteration17 RESULTS](../../dml-design/iterations/17-implementation-supersession/RESULTS.md).
[Coordinator REVIEW](../../dml-design/iterations/17-implementation-supersession/REVIEW.md)
owns independent acceptance, not this page. VP-001 remains OPEN/UNKNOWN, not diagnosed by
this story or inherited as a standing failure waiver.
