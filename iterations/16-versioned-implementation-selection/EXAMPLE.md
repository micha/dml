# Iteration 16 worked example: choose A or B, then decide reuse

## Delivery and stop

This bounded turn is **COMPLETE AND STOPPED** through published `e0089323`, all six
final-SHA CI jobs successful. Actual three-job/nine-phase evidence and original limitations
are in [RESULTS](RESULTS.md); independent acceptance is in [REVIEW](REVIEW.md).
The candidate story/authorization below preserves planning provenance, not restart permission.

## GO authorization

The user's subsequent **Iteration 16 GO** approves this bounded acceptance story/design/
handoff for implementation in a fresh existing window-2 session, coordinator review,
then accepted worker commit/normal push/CI fixes. See [COORDINATION](COORDINATION.md).
Pending-review/GO wording below is historical; the story is not yet executed or as-built.

The original preparation status below preserves planning provenance.

Status: **candidate acceptance story, NOT executed; direction agreed, implementation GO pending**.
[DESIGN](DESIGN.md) separates user-agreed direction from candidate schema/helper choices.
[HANDOFF](HANDOFF.md) owns conditional assignment/validation/publication boundaries.

## 1. Declare two captured bindings for one intent

Construct two genuinely different captured Python implementation bindings, both for the
small admitted demo of doubling an I64 producer result with declared factor2:

```text
intent URI: urn:example:double
implementation label double-a -> captured BA / tree double-a-binding / selected-double-a
a different label double-b     -> captured BB / tree double-b-binding / selected-double-b
BA != BB
reuse default: reuse-by-default
default implementation: double-a
SA and SB selection entries: ABSENT
```

For example A uses multiplication; B uses addition after checking the demo factor2 contract.
Both read the actual result sub-DAG/input context and publish an ordinary result sub-DAG;
neither is canned84. Exact source/role/API spellings are candidates, not selected schema.
Labels are scoped names, not URI discovery or identity substitutes. The bindings already
contain captured entry bytes/interpreter/timeout; defining choices installs no resources.

Record ordinary definition I_A in a snapshot, preserving other entries. Python explicitly
runs the existing producer once:

```text
13 + 29 -> Qadd / Tadd -> R42
I2 = actual R42 sub-DAG + exact selected final producer attempt witness + factor2
```

Both implementations use this SAME full I2. Producer provisional/failure/unknown evidence
cannot authorize the consumer; existing public composition owns that boundary.

## 2. Default A, no recorded A selection: fresh execution

A normal request pins the definition and input names but supplies NO binding tree name or
selection-slot name—the declared choice owns those resolved names.

```text
D_A captures I_A
implementation override: default
selected implementation: double-a / BA
implementation reason: default-implementation
reuse override: default
reuse decision: execute-fresh / default-no-selection (SA absent)
```

Recommended spine is existing separate D parent, then own Q:

```text
C -> Cdec(D_A) -> Cq(Q_A) -> P/U/F for T_A -> R84
```

Only the explicit application driver dispatches the SECOND actual Batch job. Actual Q_A
contains BA/full I2; F success still does NOT create SA. After terminal-job/ALLclient/empty
namespace proof, stop/archive the endpoint and explicitly select SA using existing S/V/public
successful-history authority. Definition/selection publications create no Q/T/job.

## 3. Change default to B; do not reuse A as B

With the endpoint OFFLINE, publish I_B in a NEW snapshot:

```text
same intent URI / reuse default / captured menu BA,BB / selection-slot declarations
new default implementation: double-b
SA still selects T_A / R84; SB remains ABSENT
```

A normal request on this version resolves BB and SB:

```text
D_B: I_B / default-implementation double-b / BB / SAME I2
reuse decision: execute-fresh / default-no-selection (SB absent)
new own Q_B
```

SA exists but is NOT the selected implementation's slot. Its result84 cannot satisfy Q_B.
If SB were PRESENT but held A's valid S, that would error before D/Q—not execute fresh or
fall back to A. Genuine absence is different from an incompatible declared choice.

After known-stopped-only fixture resume/reset of the SAME declared finite keys, explicitly
launch the THIRD actual Batch job. Actual B code computes from R42/full I2, returning84:

```text
Q_B / T_B -> R84       # BA != BB, T_A != T_B; result content may be identical
```

B imports old definition/SA/producing history inertly. BA/BB/I_A/SA/old Q/T bytes and parent
relationships remain unchanged. New successful F_B still does NOT automatically install SB.
Stop/archive after exact terminal/client/namespace proof; explicitly select SB offline.
Original selected packets/expected/input/B become unavailable after owned capture, not read
by subsequent policy operations. Native persisted S/V/all-parent history remains authority.

## 4. Default B reuse, explicit A reuse

On the snapshot containing I_B, SA and SB, with endpoint OFFLINE:

| Request | Implementation decision | Reuse decision | Actual selected attempt |
| --- | --- | --- | --- |
| normal/default | I_B default chooses BB | valid SB/default-selection | T_B |
| explicit double-a | override chooses BA despite I_B default | valid SA/default-selection | T_A |

Both record DISTINCT new Q and ordinary W, no new T/job. Old T_A still references its original
Q_A, old T_B its Q_B. W retains original role/request/attempt/result fields; D records exact
I_B/choice/implementation override and separate reuse decision. There is no inferred common
cache entry merely because both R84 IDs match, and 'explicit implementation' does not mean fresh.
A separate explicit fresh override would request a new attempt without adopting; native tests
can cover its pending-Q/no-implicit-dispatch semantics without adding a fourth acceptance job.

## 5. True sibling defaults

From a common snapshot retaining BOTH selections and I_B:

```text
                         Ccommon (I_B, SA, SB)
                          /                 \
Ckeep-B (same tree)                          Cdefault-A (replace only intent definition)
parent exactly Ccommon                      parent exactly Ccommon
I_B / SA / SB                               I_A-equivalent / same SA / same SB
```

Restoring A's identical definition content may deduplicate its Idef record; this is still a
new snapshot/default change, not mutation or another empirical observation. Both binding IDs
and both S/V choices remain fixed. Offline normal requests on A and B siblings create new Q/W
using T_A and T_B respectively. Moving a latest/default ref cannot retarget historical D/Q.
Fresh transferred readers revalidate each branch's definition/reasons/own Q/selected T/R
without original packet/B/endpoint/source execution. Copying history creates no request/job.

## 6. Counts, negative controls and limits

Normal acceptance: **THREE actual Batch jobs/NINE real P/U/F**—producer, A, B. Initial/default
publications, explicit select, default/override reuse, sibling changes and readers create no
extra computational job. Enumerate real native Q/T occurrences/versions and all external states,
including any genuine host-prior used by support, separately from the three Batch jobs.

Primary controls: unknown override/default label/missing or malformed definition/choice, captured
binding-tree drift, wrong/aliased slot and forged choice/default/reuse claims reject; full B/input/
producer-witness mismatch never becomes cross-implementation reuse. Changing menu/default context
alone cannot retarget selected computation. Explicit fresh/default-execute ignores unused S
application framing but not full native closure. Inspecting Q requires exact non-None Q authority.

Definition/default-update/D individually atomic; D/Q/W/files/service separate. Late errors or
lost acknowledgments can leave decision/pending Q/complete W; no duplicate/fallback/adoption/repair.
Actual owning Q and selected successful historical attempt—not response flags or scalar84—own
association. One real demonstration plus focused negative tests is not proof of every platform/
process/branch/cleanup/environment/scientific property.

[VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md) remains OPEN/UNKNOWN and is
revisited in planning; no fresh experiment occurred or standing CI waiver extends to this turn.
Implementation/fixture/delegation/publication GO is separate. This story is NOT as-built behavior.
