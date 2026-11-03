# Iteration 23 worked candidate: fixed capture, changing defaults

Status: **illustrative plan for review; NOT an executed example or implementation GO**.
Read [DESIGN](DESIGN.md) for candidate representation/identity and [HANDOFF](HANDOFF.md) for limits.
Exact names/API/records below remain refinable. No outer/inner ordinary-request evaluator is assumed.

## 1. Computational contract

One ordinary intent, illustratively `urn:example:captured-scaled-sum`, computes:

```text
scaled_sum({a:13,b:29}) = (13 + 29) * captured_scale
```

Invocation arguments are EXACT `a,b` with I64 values. Captured scale is exact I64; bool/float/coercion
and intermediate/final signed-I64 overflow reject. The logical callable uses TWO recorded map-get
calls, reads the captured scale value and returns an owned I64 literal node. Arithmetic is ordinary
Python, not a new builtin operation or separately recorded add/double requests.

All invocations below use FULL MAP `{a:13,b:29}`. Its argument sources may be newly authored but the
value is identical. Scale is NOT an invocation argument. Supplying `scale` in that MAP rejects.
Capturing scale does not imply executing a producer to calculate it.

## 2. Bootstrap values and explicit closures

Prepare supported map-get-v1, map-get-v2 and list-get-v1 bindings; no dispatch yet. Prepare named
constant source DAGs with value2 at origin-A, value2 at origin-B, and value3. Distinct origin descriptors
are retained provenance, not different computational values. Their semantic literal-source nodes
can differ despite equal2; the underlying native literal/datum may deduplicate.

Create closure C-A explicitly from:

```text
map-get  = exact map-get-v1 binding
list-get = exact list-get-v1 binding (support dependency; not invoked)
scale    = semantic source node for origin-A/value2
```

Its immutable environment E-A is linked by C-A. Executable B-A captures E-A ID and exact logical/helper
bytes. Its capture key K2 has scale2 and the two builtin func URIs, not origin-A/v1/default names.
Author a convenience default state pointing to map-get-v1 and the scale2 source. Closure construction
is atomic bootstrap authoring; it creates zero Q/T/getter positions.

## 3. Six requests, four actual fresh attempts

| Q | Requested closure | Control and selected state | Expected satisfaction | New T | Getter positions |
| --- | --- | --- | --- | --- | --- |
| Q1 | C-A: v1, origin-A scale2 | fresh; no selected result | fresh84 | T1 | 2, both v1 |
| Q2 | SAME C-A after default change | require-selected S1 | OLD84 from T1/R1 | none | 0 |
| Q3 | SAME C-A after default change | explicit fresh, S1 retained | fresh84 | T3 | 2, both v1 |
| Q4 | NEW C-B: v2, origin-B scale2 | require-selected S1, equal K2 | OLD84 from T1/R1 | none | 0 |
| Q5 | C-B: v2, origin-B scale2 | explicit fresh, S1 retained | fresh84 | T5 | 2, both v2 |
| Q6 | NEW C-C: v2, scale3 | try-selected S1, K3 differs | pending miss, then fresh126 | T6 | 2, both v2 |

For Q1 explicitly record own Q, dispatch exactly once through unchanged synchronous local exchange,
wait/reap the direct child, validate completion/import, and explicitly select successful S1 under
`selected-scaled-sum`. Selection is a separate action; closure creation and completion do not adopt.

Before Q2 publish a new default state: map-get-v2 and scale3. Preserve C-A/E-A/B-A/K2 and old history.
Q2 uses the pinned existing C-A, not the moving defaults. It creates own Q2/W2, no attempt/trace.
Q3 then proves actual execution still uses captured v1/scale2 despite those changed defaults.

Create C-B explicitly from v2, list-get-v1 and origin-B/value2. Full environment/closure/source/binding
identity differs from C-A, but recomputed capture K2 and invocation MAP match. Q4 records its NEW
requested capture, then W4 selects OLD T1/R1. It does not claim that T1 used v2 or origin-B.
Q5's fresh control independently demonstrates actual captured-v2 execution; its successful result
leaves S1 unchanged.

Create C-C explicitly from the new defaults v2/scale3. Its K3 differs while intent/invocation MAP stay
identical. Q6 must NOT reuse S1's84. Record own pending Q6 with valid-mismatch reason, then dispatch
one fresh attempt yielding126. No automatic adoption; `selected-scaled-sum` still selects T1/R1/K2.

Total: **SIX distinct Q / FOUR synchronous LOCAL attempts / EIGHT successful child map-get positions**.
Zero list-get/construction/compatibility positions, support Q/T, nested workers or separately recorded
inner ordinary attempts. Getter trace positions are not unique content-record counts. Inspector's
fixed nonrecording semantic recomputation is not another invocation or empirical execution.

Explicit immutable successful S evidence for fresh completions may be retained in separate known
witness slots for offline validation. Only S1 is consumed as this example's reusable choice; those
other witnesses neither update `selected-scaled-sum` nor trigger any job/discovery. Record actual
request/attempt/native IDs, never predict IDs from conceptual Q/T labels.

## 4. Identity and provenance observations

Candidate computation key is `(intent URI, capture K, full invocation MAP datum)`:

```text
C-A / C-B : source-distinct scale2 + equivalent getter purpose -> K2
C-C       : scale3                                        -> K3

Q1/Q2/Q3/Q4/Q5 key = (scaled-sum, K2, {a:13,b:29})
Q6 key             = (scaled-sum, K3, {a:13,b:29})
```

This NEW key is proposed for review. It deliberately prevents a captured constant from disappearing
from reuse identity. Getter exact versions and scale derivation stay provenance, not K in this fixed
equivalent-handler profile. Do not normalize arbitrary implementations or recursively captured funcs.
Do not change Iteration20–22 keys/helpers to apply this convention retroactively.

Pinned reader view of Q4 distinguishes:

```text
NEW requested Q4 -> exact B-B/I4; decision -> C-B/E-B/origin-B/v2/K2
NEW W4           -> OLD T1/R1 -> original Q1/decision/C-A/E-A/origin-A/v1/K2
```

Capture does not pin the selected historical attempt: Q3/Q5 fresh controls execute with their captured
funcs while leaving S1 untouched. Moving defaults cannot change an existing closure; changing the
explicit captured scale can change computational meaning and therefore eligibility.

## 5. Evidence and negative controls after separate GO

Focused tests, not extra acceptance jobs, cover malformed/unknown getter pair, wrong/unretained scale,
constant BOOL/F64, duplicate/extra profile fields, ignored scale in K, wrong equal-valued source
association, child default reread, coherent wrong decision/closure, unsupported closure version,
poisoned S even on mismatch, and own-Q/W validation. I64/overflow and old-versus-requested chain checks
are meaningful; no runtime catch-and-retry or failure masking.

New closure B/C publication and decision/Q/W are separate transactions. Test atomic new-row failure
with previously ABSENT predicted IDs, actual late-ref/map-full/commit faults, unrelated old-byte
preservation and acknowledgment-loss classification where useful. Do not claim whole filesystem/
job/history rollback, automatic repair or exactly-once execution.

After all four owned children are known direct-wait reaped, retire only owned operational paths and
preserve inert evidence. Transfer the SAME complete pinned history to a fresh replica. Blocker-FIRST
installed NONEXECUTING readers inspect native/Q/public successful S/C/E/K/actual B source/getter traces/
W/summary/immutable bytes; no logical arithmetic or source execution, new Q/T/records/refs or second
story. Separate metadata controls reject spawn/transport before jobs; only FOUR explicit dispatches
are allowed in the sole installed story. A failure/uncertain custody stops for scoped review, not relaunch.

A summary is an ordinary DAG linking six own requests, four successful attempt/result witnesses,
three closures and two W satisfactions, not a seventh request or new native entity. Record actual
counts/known ownership and capture provenance BEFORE asserting expected values. Independent risk-based
review reads SAME stopped evidence, distinct from reviewed worker computation/full evidence.

This example is not current behavior or full platform assurance. Development GHA remains disabled/
NOT RUN/not pass; native19 PAUSED/private candidate incomplete-unexecuted retained/VP-001 OPEN UNKNOWN.
No story/source/build/worker/CI/investigation/commit/push permission follows preparation.
