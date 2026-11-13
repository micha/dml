# Iteration 25 worked candidate: same intent, different captures

Status: **bounded story plan reviewed; NOT executed evidence or implementation GO**.
See [review checkpoint](../../discussion.md#iteration25-plan-review).
Read [DESIGN](DESIGN.md) and [HANDOFF](HANDOFF.md). API spellings, profiles and counts are recommendations.

## 1. Metadata preparation, no invocations

Create A/B implementations of fixed add(a,b), double(x) and sum_then_double(a,b) intents.
A leaves capture map-get-v1/list-get-v1; B leaves capture map-get-v2/list-get-v1. Outer A captures add-A,
double-A/getter-v1; outer B captures add-B/double-B/getter-v2. Exact B/E/source bytes differ. There are
no intent captures or computational capture keys. Set convenience defaults to A.

Prepare input-map nodes for `{a:13,b:29}`. Later author a NEW equal-value input node from different actual
literal source nodes for row2: e.g. select named literal13/29 from a separately retained source DAG through
public recorded source access. Do not fabricate a producer attempt for those literals. Native MAP value
must be exactly equal while input DAG/source relationships differ. Also prepare `{a:13,b:30}` for row5.
All construction uses recorded argument/source ledgers; bootstrap/promotion/adoption create ZERO Q/T/
getter invocations. Existing `Recorder.source` selects an explicit literal, not arbitrary-root extraction.

Reuse key is intent + full MAP value. `{a:13,b:29}` and `{a:29,b:13}` would differ, despite equal sum42;
commutative normalization is not part of this slice. That distinction is a focused test, not another job.

## 2. Five outer requests

One finite application owns the synchronous outer adapter and SIX direct LOCAL leaf children.
A single `invoke(target, argument_node)` facade is used for outer/leaf calls and all builtin getters;
recorded argument-building is eager preparation, not extra primitive execution.

| Outer row | Requested closure/input/control | Add | Double | Outer result |
| --- | --- | --- | --- | --- |
| OQ1 | A /13,29 /fresh outer + fresh inner | IQ1 fresh A ->42 /IT1 | IQ2 fresh A ->84 /IT2 | OT1 fresh A ->84 |
| OQ2 | B /equal MAP, different actual sources /require selected outer | no inner Q | no inner Q | OLD OT1/R1 ->84; no outer T |
| OQ3 | B /13,29 /fresh outer + fresh inner | IQ3 fresh B ->42 /IT3 | IQ4 fresh B ->84 /IT4 | OT3 fresh B ->84 |
| OQ4 | B /13,29 /fresh outer + require selected inner | IQ5 own B Q ->OLD A IT1/Radd1 | IQ6 own B Q ->OLD A IT2/Rdouble1 | OT4 fresh B composition ->84; no leaf T |
| OQ5 | old A /13,30 /try selected outer + try selected inner | IQ7 mismatch/fresh A ->43 /IT7 | IQ8 mismatch/fresh A ->86 /IT8 | OT5 fresh A ->86 |

Labels are explanatory, not actual UUIDs/content IDs. Outer T uses a distinct in-process profile;
leaf T uses unchanged LOCAL execution. Row2 requests B but is satisfied by A. It does NOT claim B ran.

After OQ1 explicitly select its successful outer attempt, add attempt and double attempt in THREE known
intent-specific slots. Selection publication is metadata, not a request/attempt. OQ3 bypasses eligible
selections and actually runs B, but does not adopt any result. Every slot stays at row1 throughout.

Before OQ4, promote convenience add/double defaults to B. Keep already-created outer A and B byte-identical.
OQ4 invokes B but its own B leaf requests reuse selected OLD A attempts, extending cross-implementation
reuse to the inner boundary as well as OQ2's outer boundary. OQ5 explicitly invokes old A and actually
dispatches A leaves after promotion, proving pinning at execution as well as request time. Combining the
last proposal's default-pinning and different-input demonstrations in OQ5 avoids a separate compatibility
job. The miss row intentionally uses A, not B.

For every fresh outer invocation, two outer I64 getters precede ordinary dispatch; add receives ORIGINAL
exact outer input node. Double's map source is THIS invocation's validated add result node. On OQ4 that
node comes from OLD selected add, but this invocation has its own add request/satisfaction.

OQ4 and OQ1 double maps have equal `{x:42}` values, but the new request/outer association is distinct.
A copied node or equal value must not erase the selected producer witness. OQ5 add MAP differs from
selected13,29 and double MAP x43 differs from selectedx42: both misses are legitimate, no auto-adoption.

## 3. Proposed counts

```text
outer requests:             5     in-process outer attempts: 4
leaf requests:              8     synchronous LOCAL attempts:6
total requests:            13     total attempts:            10
fresh computational children:6    outer/descendant workers:   0
ordinary inner call positions:8   primitive getter positions:17
```

Getter positions:

- Outer: FOUR fresh invocations * TWO =8.
- Fresh add: THREE * TWO =6.
- Fresh double: THREE * ONE =3.
- Total17; row2 has ZERO and inner hits in row4 have ZERO leaf getters.

The seventeen positions span separate owning ledgers, not one trace exceeding its16-position limit.
Native operation content may deduplicate without merging positions. No list-get, map-empty/map-insert,
support/compatibility invocation or extra Q/T. Initial calls of outer targets and builtin calls use the
same facade; primitive calls retain their existing no-Q/T representation. Ordinary argument maps are
one original and one downstream per fresh outer call; builtin getter preparation adds its own maps.

Actual counts and complete semantic union must be checked from native history. Old Iteration24 counts
and34/50 budgets are not receipts for these new profiles. Readiness needs actual prospective unions and
pre-dispatch reservations within64,16/16/transfer/depth8 limits; if not feasible, STOP for redesign.

## 4. Provenance assertions

Row2 must retain BOTH:

```text
NEW OQ2 -> requested B -> B captures -> NEW actual input/source ledger
NEW satisfaction -> selected OLD OT1/R1
    -> ORIGINAL OQ1/A/A captures/original inputs
    -> ORIGINAL add IQ1/IT1 and double IQ2/IT2
```

B source/getter versions must never be relabelled as the execution behind R1. OLD A history remains
retained through real graph/parent links, not just serialized ID strings. Full value equality is checked
from both argument profiles; malformed present selections are errors, not misses.

Row4 demonstrates NEW B outer attempt with NEW B inner Qs but OLD successful A leaf attempts. Each own
Q/requested target/full inputs is recorded before satisfaction. Reader validates ORIGINAL producing outer
prefixes independently; current outer success must not be required to validate its first successful leaf.

Row3 validates actual B implementation/captures/getter-v2 traces, independent of the declared equivalence.
Row5 validates actual A captures/getter-v1 after defaults move, value86 and selected slots unchanged.
Readers validate recorded source/value/provenance and fixed builtin semantics, not execute captured
Python arithmetic as a substitute for original execution evidence.

## 5. Acceptance readiness and stopped inspection

After future GO only, perform focused interface/capture/authority tests and bounded fresh isolated current
DML install using available pinned tools/caches. Review exact captured module/helper/logical/controller/
reader bytes, installed identities, capability boundaries, native phase/union plan and event-envelope
negative control BEFORE the sole installed story. Controller event category must not collide with payload
fields, preserving Iteration24's learned failure. No metadata-only pass claimed as runtime acceptance.

Run the table ONCE in a sanitized installed environment, no checkout runtime imports. Record actual
request/attempt/action/capture/source/ref/phase identities and each of SIX PIDs/waits/reaped-absence
receipts incrementally. Outer-hit boundaries block dispatch; only declared fresh leaf boundaries launch.
Failure or uncertain custody stops; no automatic second story or retry-until-green.

After known disposition retire ONLY owned operational paths; preserve inert full pinned history/source/
logs/data hashes. Fresh installed blocked readers inspect SAME caller and transferred copy nonexecutingly:
no logical source execution, recording, dispatch/transport, target writes or new refs. Public validator
scratch is separately permitted and scoped. Verify no-job counts, exact requested/OLD chains, immutable
stores, slots/default pinning and all-parent retention. Correct reader oracles on SAME data rather than
repeat computation. Coordinator independent review uses SAME stopped evidence, not another job fixture.

This remains local evidence, not platform all-green, native19/VP-001 diagnosis, a security sandbox or
scientific certification. GHA remains disabled; implementation/validation/publication GO is separate.
