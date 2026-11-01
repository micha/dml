# Iteration 17 worked example: preserve a predecessor after a correctness fix

Status: **candidate acceptance story, NOT executed; direction agreed, implementation GO pending**.
[DESIGN](DESIGN.md) distinguishes agreed direction from assistant-origin mechanics.
[HANDOFF](HANDOFF.md) owns conditional assignment/validation/publication boundaries.

## 1. New test fixture, not a defect claim about Iteration16

Predeclare two genuinely different captured local Python bindings for `urn:example:double`:

```text
A: intentionally buggy; max(0, 2 * n)
B: corrected for this example; 2 * n
input I: literal I64 n = -3
initial default: A
reuse default: reuse-by-default
selected-A / selected-B: ABSENT
known supersession slot: ABSENT
```

Both consume actual I and publish an ordinary result sub-DAG. No canned output, binding
replacement behind a ref, implementation installation or borrowed Batch image is needed.
This is a NEW fixture: Iteration16's recorded A remains the correct multiplication code it
actually captured. No producer is required for this literal-input case; existing producer-
witness matching remains unchanged when such a witness is supplied.

## 2. Execute A and retain the surprising result

A normal request on the initial definition records own Q_A and explicitly runs A through
existing installed local caller-request/exchange operations:

```text
Cdef -> Cdec_A -> Cq_A -> P/U/F_A
A(-3) -> R0
```

Actual completed native history records T_A, success, result0 and separate cleanup. Success
means the computation completed/published, NOT that0 is the correct answer. Capture/receive
its public completed packet after local execution has reaped the child, then explicitly
select S_A through existing S/V successful-history authority. No automatic selection.

The common snapshot C_A retains the definition/menu/full BA/BB/I/Q_A/T_A/R0/S_A. B's slot
and the supersession slot remain absent. Two actual binding IDs remain distinct.

## 3. Record evidence and a correctness supersession; promotion is separate

Author an ordinary evidence DAG E_fix. The example independently checks its selected S_A/
actual full BA/I/T_A/R0 through public authority and typed native reads. Record the researcher-
asserted expected I64 value-6 and explanation of the negative-input counterexample. Linking
this evidence does not make DML certify the expected mathematics or every affected input.

Then record ordinary L_fix:

```text
captured intent definition / predecessor A choice / successor B choice
reason: correctness-fix
evidence: E_fix
basis: exact pre-declaration commit, retained in all-parent history
```

Candidate commits add only E and then only L at explicit absent names, each with its own
exact parent/create-only ref/batch. No Q/T/dispatch/default/selection changes.

At C_L, **A is STILL the default**. The advisory does not force execution, suppress S_A or
rewrite the successful T_A outcome. Explicit promotion via the existing default-only helper
creates C_B: same menu/bindings/reuse default/I/S_A/L_fix/other entries, only default B changes.
Evidence publication, L publication and promotion are separate boundaries; a lost response
can leave any earlier complete publication without the later one, not implicit repair.

## 4. Fresh B uses B, not A's result

A normal request on C_B resolves actual BB before reuse policy. B's slot is genuinely absent:

```text
D_B: default B / default-implementation / execute-fresh / default-no-selection
new Q_B -> explicit local execution -> T_B -> Rminus6
```

Actual B computes-6 from the SAME full I. It creates the SECOND and final fresh attempt of
normal acceptance. A's S_A/R0 cannot satisfy B. Fresh B success does not create S_B, change
L, adopt anything or erase A's old proof. Receive only under explicit refs.

All declaration/evidence/old definition/code/Q/T/W bytes and ordered parent relationships
stay unchanged. No registry, cross-implementation equivalence or invalidation rule appears.

## 5. Explicit A reuse on the corrected branch

With all computational workers reaped and original packet/input/B paths unavailable, explicitly
select A on the new branch using the unchanged implementation/reuse helper:

```text
implementation override: A
implementation reason: explicit-implementation
reuse decision: default-selection
new Q_A_again / W -> OLD T_A / R0
```

No third attempt is created. W retains its original four fields and links NEW Q to OLD
selected T/result; T_A still references Q_A. This deliberately reproduces the recorded
predecessor result; deprecation does not quietly substitute B or invalidate the old outcome.

The proposed reader reports as-known-then L_fix from THIS request's actual D.base, identifies
the selected binding as the deprecated predecessor, and preserves the separately recorded
implementation/reuse reasons. This is advisory state available in that pinned basis, not
proof the caller consulted/understood it; the unchanged request helper does not interpret L.
There is no new mandatory acknowledgement flag or ban.

## 6. Old branch and explicit later-knowledge view

Create a true keep-A sibling from C_A before evidence/declaration, preserving its tree:

```text
                           C_A (S_A, default A; no L)
                          /                         
Ckeep-A (same tree)                           C_E -> C_L -> C_B (default B)
        |                                                        |
new own Q_old / W -> T_A,R0                      new Q_B/T_B and explicit A reuse
```

Normal request on the old branch creates the FOURTH normal Q and reuses T_A/R0, not new T.
Pinned inspection distinguishes:

| View of Q_old | Meaning |
| --- | --- |
| As known then, actual D.base | Default A; no declaration in the explicit known slot at that snapshot |
| Explicit knowledge=C_B or its descendant | A is predecessor in L_fix; correctness-fix/evidence shown as separate knowledge |

The knowledge commit is explicit, not latest ref resolution. It can be on a sibling history;
its role is a selected knowledge context, not proof of a universal chronological clock.
Never edit old Q/D or report that the old request originally knew L_fix. Moving latest/default
refs cannot retarget either pinned context. Querying B identifies it as the declared successor,
not as deprecated simply because L contains a deprecation statement about A.

Transfer the needed pinned request/knowledge roots to a fresh repository and repeat both
views with no original packet/B/executable-source action. Reads add no Q/T/ref or job.

## 7. Operational-replacement sibling control

On a separate sibling from the common captured menu/history, record ordinary E_op explanation
and L_op with SAME A/B endpoints but `reason = operational-replacement`. Keep default/choices
unchanged unless explicitly promoted. No Q/T/execution required for this metadata control.

This says the declared replacement motivation is operational; it neither asserts that old
results are incorrect nor certifies they are correct. It is not a performance measurement,
actual infrastructure migration or contradiction of the retained counterexample. Readers
show the explicitly chosen branch's reason without collapsing the two declarations into a
global status. General reason revision, multiple declarations and successor chains are deferred.

## 8. Acceptance counts and limits

Recommended normal workflow: **FOUR distinct requests / TWO real local attempts**:
A fresh, B fresh, A override reuse on the corrected branch, A default reuse on the old branch.
L/evidence/default changes, operational sibling and fresh transfer readers create no attempt.
All fresh local work must finish/reap before offline-only policy/read phases. No Batch/SSH/
Docker/service/image/third-attempt requirement or retired fixture restart.

Focused negatives cover strict reason/endpoints/basis ancestry/evidence closure, same-binding
or unknown successor, capture drift, actual D.base versus current ref, wrong Q, missing versus
malformed L, wrong-scope explicit knowledge, predecessor versus successor classification,
rollback/loss of the NEW authoring batch and unchanged old proof. These tests do not prove
scientific validity, defect impact across history, authentication or universal reproducibility.

VP-001 remains OPEN/UNKNOWN; Iteration16's final pass is not its diagnosis. This example is
NOT as-built behavior. Implementation/delegation/publication GO remains separate.
