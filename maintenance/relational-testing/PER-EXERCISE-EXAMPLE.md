# Per-exercise reuse — worked acceptance candidate

**Final:** sole actual63Q33T8E11P14C30reuse story completed; [results](PER-EXERCISE-RESULTS.md)
record actual gates/qualifications/STOP. Example below historical intended counts, no repeat authority.

**Subsequent GO:** bounded implementation approved, required [pre-edit review](PER-EXERCISE-PRE-EDIT.md)
acceptance pending before coding/preparation/activation. [Coordination](PER-EXERCISE-COORDINATION.md)
owns current gates. Counts below remain intended, not executed evidence; story awaits later readiness.

**PREPARED FOR REVIEW, not executed/implementation GO.** [Design](PER-EXERCISE-DESIGN.md),
[conditional handoff](PER-EXERCISE-HANDOFF.md). Names/counts below are intended checks, not actual
receipts. New generated three-case map/get profile; no additional maintained-test conversion claim.

## Inputs and identities

| Stable scenario | Initial inputs | Expected independent semantic verdict |
| --- | --- | --- |
| positive-a | value42, faultFalse | accept |
| negative-b | value42, faultTrue | reject: map_get_value at its actual bad-operation |
| positive-c | value43, faultFalse | accept |

The input-change configuration changes ONLY negative-b value42→44. Same candidate/harness/runtime,
same stable scenario IDs; positive-a/c keep exactly the same E envelopes. A malformed/tool failure
is not the intended negative verdict. Each fresh E makes SIX actual builtin positions (two
checkpoint recordings, three map/get calls apiece), separate producer occurrence/roots.

A/B differ by actual candidate builtin source comment bytes, P1/P2 by actual normalizer payload
bytes, C1/C2 by actual checker payload bytes. Same behavior is not a waiver for changed code.
Fixed materializer/controller manifests do not change in the story. The checker variant is an
entire query program dependency, so all three C cases depend on that edit; per-rule SQL slicing
is deferred, not falsely claimed to rerun only one invariant in that case.

## Seven finite rounds

Every round requests E/P/C for each of three cases: NINE new requests, even when all stages reuse.

| Round | Inputs/build/projector/checker | Fresh E/P/C | Reused stages | Pool load CLI |
| --- | --- | --- | --- | --- |
|1 | initial / A / P1 / C1 | 3/3/3 | 0 | 1 |
|2 | SAME, genuine NEW controller process | 0/0/0 | 9 | 0 |
|3 | ONLY negative-b value44 / A / P1 / C1 | 1/1/1 | 6 | 1 |
|4 | same changed inputs / A / P1 / C2 | 0/0/3 | 6 | 0 |
|5 | same changed inputs / A / P2 / C2 | 0/3/3 | 3 | 1 |
|6 | same changed inputs / B / P1 / C2 | 3/3/3 | 0 | 1 |
|7 | A / P1 / C2, explicit fresh ONLY negative-b | 1/1/1 | 6 | 1 |

**63 new stage requests;33 fresh attempts =8E+11P+14C;30 reuse satisfactions.**
Fresh E8×6=48 builtin positions. Fresh C14 execute14 scoped case-query CLIs; five distinct pool
assemblies execute5 loader CLIs. Intended actors:33 stage processes +19 SQL CLI children +ONE
continuation controller process=53 known owned actors. Pool loads belong to trusted assembly,
not P stage attempts; P returns case capsules and activates no DuckDB CLI. Batch/index assembly
is recorded separately, not fabricated as a new exercise attempt. Pure/focused and final isolated
test invocations are separately counted; these story totals exclude them.

R2 actually reopens the saved controller in a different Python process, reserves a NEW run,
creates9NEW Q→OLD T/O satisfactions and reuses the exact old native producers/fact capsules/
verdicts/verified closed pool. Zero E/P/C/query/pool loader activation. NEW grouping/index records
may still be written: “no stage work” does not mean “no repository IO or hashing”.

R3 proves selective work: positive-a/c E/P/C producer IDs/artifact digests are unchanged; only
negative-b gets NEW E/P/C attempts and actual value44 evidence. New generation/index retains
OLD descriptors unchanged for positive-a/c. The shared fixture cannot capture other case values.

R4 uses OLD E/P for all cases and the existing materialization, but executes all C because their
query dependency changed. R5 reprojects/checks all without E. R6 demonstrates conservative whole-
build invalidation even though A/B's changed source bytes need not change computational values.

R7 returns to the previously selected A/P1/C2 configuration. Positive-a/c reuse all three stages.
negative-b's fresh E has the SAME E key as R3 but a distinct producing occurrence/publication;
P/C see its new upstream artifact/roots and execute anew. Fresh E/P/C does not silently adopt.

## Explicit selection and the existing16-slot limit

- R1 explicitly verify/adopt9 successful attempts (3E/3P/3C).
- R3 explicitly adopt3 new negative-b-key attempts; retain initial keys. Total12 slots.
- R4 explicitly adopt3 C2 attempts. Total15 slots.
- R5/R6/R7 fresh outputs remain UNSELECTED. Do NOT adopt their additional keys and exceed16.
- After R7, fork at the current snapshot and explicitly adopt ONLY its negative-b E on the sibling.
  This replaces an existing slot: both branches still have15 selectors. Main continues choosing
  R3's E; sibling chooses R7's E. All other entries/OLD history remain unchanged.

No eviction/selection deletion/cap increase/history discovery/automatic fallback is hidden here.
The generated three-case instance is deliberately sized to fit existing engine limits.

## Required observations, not timing proxies

Record exact request/satisfaction/attempt/outcome/selection links, each E producer's native P0/P1/
CN/checkpoints/context/observations, requested versus produced context in every batch index, artifact
file sets/hashes, all selected per-case keys/roots, materialization input identity/hash and actual
source/import/runtime/command/PID/true-exit receipts. Show that every OLD descriptor and case context
remains unmodified and every reused stage owns no new attempt or CLI. Query result files contain
structured rows; diagnostics remain separate. SQL must not see previously recorded verdicts.

Read-only SAME independent-expression audit should derive the matrix/counts from actual native
controller histories, not trust result-summary counters. Compare all7 grouping records with their
native indices/artifacts; verify current specs match selected producer contexts; traverse all CN
parents and case memberships. Exact continuation9NEWQ must belong to the new actual reserved run,
not a vacuous filtered clause. Check main/sibling selector equality except the intended one slot.

Confinement/admission regressions must establish that unrelated pooled rows cannot affect a case
and that changed OWN scoped rows/sources/roots/positions or the owning rule can affect its verdict.
Preserve a wrong expected result as an outer assertion failure, not a cached success. Structural/
manifest errors fail before case checking rather than count as the expected negative.

This is a finite acceptance candidate, not a speedup/full-suite/platform/coverage assurance claim.
One story only after review/GO/readiness; errors preserve raw evidence and STOP for scoped causal
review, not automatic second story or retries until the target counts happen to match.
