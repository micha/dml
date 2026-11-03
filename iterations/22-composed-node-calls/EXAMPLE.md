# Iteration 22 worked example: different upstream keys, equal downstream values

Status: **candidate for review; NOT executed; separate implementation GO required**.
Read [DESIGN](DESIGN.md) and [HANDOFF](HANDOFF.md). Names, ordinary roles, helper spelling and exact
counts are recommendations, not as-built changes. The standard node and return-loading support
already exists; this story exercises its successful-producer/request/reuse composition.

## 1. Setup and ordinary funcs

One caller repository A, six fresh same-machine synchronous-local workspaces/B stores, and an
isolated current-source DML install after future GO. No external service/image/SSH/Batch fixture.
Use immutable captured add/double source bindings, explicitly pinned shipped map-get-v1/list-get-v1.
No choice/default promotion, dynamic URI registration, latest implementation lookup or builtin upgrade.

Illustrative logical code using the CURRENT node interface, not a new API contract:

```python
from daggerml import Datum


def add(arguments, ops):
    a = ops.map_get(arguments, "a")
    b = ops.map_get(arguments, "b")
    if a.value.kind != "i64" or b.value.kind != "i64":
        raise ValueError("add requires I64 arguments")
    return ops.literal(Datum.i64(a.value.value + b.value.value))


def double(arguments, ops):
    x = ops.map_get(arguments, "x")
    if x.value.kind != "i64":
        raise ValueError("double requires an I64 argument")
    return ops.literal(Datum.i64(x.value.value * 2))
```

Captured wrappers call installed `builtin.publish_callable`. Each fresh ordinary call returns its
explicit normal result-sub-DAG node with value, returned link, actual builtin trace and own Q/inputs.
Python performs arithmetic, not a new internal arithmetic handler. Add's exact names are `a,b`,
double's `x`. Native I64 bounds apply. The child has no checkout-only helper dependency.

Caller preparation uses `Recorder.literal` plus `Recorder.arguments` for add. This bootstrap
preparation records source links and MAP value; it is not a map/empty or map/insert invocation.
All metadata/selection/argument construction phases create ZERO Q/T and ZERO builtin call positions.

## 2. Q1 add(13,29), Q2 double42

Prepare I1 from explicit literal nodes `{a:13,b:29}`. Record decision then own Q1. Separate explicit
local dispatch creates T1, executes two map-get positions and returns R1 with I64 value42. Wait/reap
the direct child BEFORE completion inspection/receive. Import exact history under an explicit ref,
then capture public successful producer S1 in a new immutable slot `producer-add-1`.

Before composition, publicly validate S1 and inspect R1's explicit return/Q/full-input association.
Close validation handles before write. Sketch of existing recorder operations inside the new
composition helper:

```python
with builtin.Recorder(tx, commit=pinned_basis) as recorder:
    source = recorder.load(validated_selection.result)
    arguments = recorder.arguments({"x": source})
    inputs_dag = recorder.dag(arguments)
    # Helper also records C linking inputs_dag to the captured S1 and R1.
```

This loads R1 itself, not an arbitrary root or copied42; no add execution happens during loading.
Publish I2 plus C2, preserving exact S1/T1/R1 provenance outside the MAP datum. Record own Q2 for
double `{x:42}`. No selected-double yet: Q2 is pending fresh until separate explicit dispatch.
T2 executes one map-get and returns R2/value84. Publicly capture S2 into `selected-double`.
Selection is explicit and creates no Q/T; later fresh work never automatically replaces S2.

Requested AND executed Q2 chain:

```text
Q2 -> I2 -> R1 -> Q1 inputs {a:13,b:29}
C2 -> S1 -> producing add T1/R1
T2 -> producing Q2 -> R2/value84
```

## 3. Q3 fresh add(13,29), Q4 reused double42

Prepare I3 using the SAME literal/key mapping as I1. Canonical add argument MAP IDs match; full
input DAGs may deduplicate too. Force fresh Q3/T3 despite that equality. Two getter positions,
new result R3/value42 and public producer S3 under `producer-add-3`. Distinct Q/T occurrences are
required; there is no second independent observation merely from recording another key or S.

Compose I4/C4 from the actual selected S3/R3, not the convenient older R1. I4 and I2 have equal
MAP datum `{x:42}`; requested source graphs differ. Record own Q4 and W4 choosing OLD double
T2/R2 through validated S2. No new double attempt, callable execution, getter trace or completion.

Reader shows BOTH chains, never relabels R2:

```text
requested Q4 -> I4 -> R3; C4 -> S3/T3
satisfied Q4 -> W4 -> OLD T2/R2 -> original Q2/I2; original C2 -> S1/T1
```

R3's returned profile includes Q3, so its outer R differs from R1 here. This is not a universal
rule that every fresh attempt changes result content: multiple attempts of one Q can share R.
The separately captured S/T witness, not inferred node inequality, identifies the selected attempt.

## 4. Q5 add(29,13), Q6 reused double42

Prepare I5 `{a:29,b:13}`. Assert canonical MAP identity DIFFERENT from I1/I3. The effective add key
is different: names associate with different values, even though addition is commutative. Do not
swap values back, sort operands, infer equivalence or reuse Q1's result. Explicit fresh Q5/T4 really
executes two getter positions and returns R5/value42; capture S5 at `producer-add-5`.

Compose I6/C6 from S5/R5. Its downstream MAP `{x:42}` equals I2/I4 despite the DIFFERENT upstream
computation key. Record new Q6/W6 selecting the SAME old double T2/R2. No new downstream attempt or
getter. Preserve requested swapped-add provenance and original nonswapped executed-double provenance.

This is the user's extra case: convergence of different computations to one downstream value key,
not merely convergence of two occurrences of the same computation.

## 5. Q7 add(13,30), Q8 fresh double43

I7 `{a:13,b:30}` has a third add argument-map key. Q7/T5 executes two getters, returns R7/value43;
capture S7 at `producer-add-7`. Compose I8/C8 from S7/R7: MAP `{x:43}` differs from `{x:42}`.

Publicly validate the present selected-double S2 even though its value will not match. This is a
VALID value miss, not malformed-selection fallback. Record Q8 as pending fresh BEFORE dispatch;
no T yet. Separate explicit T6 executes one getter and returns R8/value86. Inspect/capture successful
S8 under a distinct evidence slot if needed, without replacing `selected-double` S2.

Original Q2/T2/R2, Q4/W4, Q6/W6 and S2 remain unchanged. Q8's fresh result is not automatically adopted.
An ordinary final summary links all four requested producer chains and each selected downstream
satisfaction, explicitly distinguishing requested sources from the historical executed source.

## 6. Exact proposed census and identity assertions

| Request | Func and argument-map value | New attempt | Satisfaction |
| --- | --- | --- | --- |
| Q1 | add `{a:13,b:29}` | T1 |42|
| Q2 | double `{x:42}` from Q1/T1 | T2 |84|
| Q3 | add `{a:13,b:29}`, explicit fresh | T3 |42|
| Q4 | double `{x:42}` from Q3/T3 | none | OLD T2/R2/84 |
| Q5 | add `{a:29,b:13}` | T4 |42|
| Q6 | double `{x:42}` from Q5/T4 | none | OLD T2/R2/84 |
| Q7 | add `{a:13,b:30}` | T5 |43|
| Q8 | double `{x:43}` from Q7/T5 | T6 |86|

EIGHT requests/SIX synchronous LOCAL attempts, no support occurrences. TEN successful builtin
positions: four add traces × two map-get, two double traces × one map-get. No getter trace for
Q4/Q6, no list-get/construction/compatibility calls. Inspector semantic recomputation is nonrecording
validation, not additional invocation positions. Native record dedup does not dedup Q/T or positions.

Effective reuse keys (no new native cache table/index is required):

```text
add key(Q1) == add key(Q3)
add key(Q5) != add key(Q1); add key(Q7) differs from both
double key(Q2) == double key(Q4) == double key(Q6)
double key(Q8) != double key(Q2)
```

Companion pure/native checks establish that inserting identical map entries in reverse ORDER still
matches, while swapping their associated VALUES differs. Full-map equality is typed/canonical, not
Python scalar coercion or an ad hoc arithmetic-equivalence rule. Add and double intent URIs are
always distinct, even if some argument values or results happen to coincide.

## 7. Same-history nonexecuting review and companion negatives

Retain measured controller/captured sources/helpers/installed module/native/CLI identities BEFORE
launch. Save each Q, intended dispatch, actual child PID/wait/outcome and native IDs incrementally;
stop on uncertain custody or failure, not speculative relaunch. Metadata phases block spawn/transport;
only six explicit local dispatch boundaries allow their expected direct children.

After all six children are known reaped, make only owned originals unavailable and transfer SAME
pinned full all-parent typed/composite history to a fresh repository. Blocker-FIRST fresh installed
readers inspect history without new calls, native records/refs, arithmetic jobs or original packet
paths. Verify exact8Q6T/10positions, C-to-S-to-R/input chains, own-Q/W actual parents/tree/reservations,
unchanged selected-double and old records, original versus requested sources, source/captured byte
provenance and unchanged caller/replica data bytes. Complete authority uses public S and structural
return inspection together; neither copied values nor valid native records alone suffice.

Focused companions, separate from acceptance occurrences: reject same-value WRONG S/R source
substitution, provisional/failure/unretained producer, forged return owner/value/trace, missing C or
coherent alternate C/decision, poisoned selected-double EVEN on mismatch, unexpected names/types and
bare Datum/native-node-ID in place of owned semantic handle. Test meaningful input+C publication
rollback and pending-Q/W failure boundaries without an extra computational story. Existing builtin
and exchange suites supply unchanged mechanisms; no repeated full fault matrix is requested.

Candidate story is NOT executed. It proves explicit node-call composition/value reuse if accepted
and implemented, not generic evaluation, arithmetic certification, full capture/security, new
builtin-version compatibility, cross-adapter execution or fresh platform assurance. GHA disabled/
NOT RUN; native19 PAUSED/private candidate incomplete-unexecuted; VP-001 OPEN UNKNOWN unchanged.
