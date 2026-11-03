# Iteration 20 worked example: same result, different producer

Status: **DEFERRED historical candidate; NOT executed; not active Iteration20 acceptance**.
Replacement: [recorded argument-map story](../20-recorded-argument-maps/EXAMPLE.md), NOT executed.
See [redirection](../../discussion.md#iteration20-redirection-value-arguments-and-separate-provenance).
Original candidate follows unchanged; no implementation/run permission.

Original status: **candidate, NOT executed**. Direction/preparation authorized; exact mechanics and
counts require plan review, then separate implementation GO. Read [DESIGN](DESIGN.md) and
[HANDOFF](HANDOFF.md). All IDs below are symbolic; no command here authorizes a run.

## Setup and notation

One ordinary repository A, fresh explicit synchronous-local execution workspaces, captured
trusted producer/consumer source bytes and current installed DML after future GO. Python
chooses every action; there is no evaluator or scheduler. Producer computes an explicitly
supplied I64 (42 or43); consumer reads result I64 and factor2, not producer identity.
Producer witness is provenance, not a computational dependency for THIS consumer's result.

Keep both implementation choices required by existing bounded intent-definition conventions
if those public helpers are composed. The story requests one explicit local binding per intent;
unused menu entries require no execution. No implementation-selection capability expansion.

- `U1/U2/U3`: distinct upstream final attempt DAGs/occurrences.
- `R42/R43`: FULL upstream result sub-DAGs with literal I64 root42/43.
- `I1/I2/I3`: full new-profile consumer input DAGs with value/producer/factor/role.
- `J42/J43`: result-mode projected DAGs retaining role/value/factor, not producer.
- `D1/D2/D3`: downstream attempt occurrences, not decision role Dp.
- Every successful attempt is explicitly observed/received and child-reaped. Public S capture
  supplies successful Q/T/R/F authority; exit code alone is not a successful history proof.

Initialize `Presult` and `Pexact`, separate empty tables for the same downstream intent,
explicit immutable slots and create-only refs. Policy/table/source authoring creates no Q/T.
No Floci endpoint/gate fields are smuggled into the new profile or excluded silently.

## Finite sequence

| Phase | Explicit action | New Q | New T | Recorded result |
| --- | --- | ---: | ---: | --- |
| 1 | Fresh producer(42) | Q1 | U1 | R42 |
| 2 | Fresh double(I1), with producer U1 | Q2 | D1 | R84 |
| 3 | Fresh producer(42) again | Q3 | U2 | SAME R42 |
| 4 | Result-policy request double(I2) | Q4 | none | selected D1/R84 |
| 5 | Exact-policy sibling request double(I2), default miss then explicit dispatch | Q5 | D2 | R84 |
| 6 | Main result-policy branch: fresh producer(43) | Q6 | U3 | R43 |
| 7 | Result-policy request double(I3), default miss then explicit dispatch | Q7 | D3 | R86 |

After phase1 capture upstream S_U1. Build I1 by validated association:

```text
I1: value=R42, producer=U1, factor=I64(2), fixed role; root=value
```

After phase2 capture downstream S_D1 and explicitly insert it into BOTH tables with its
original input I1 and upstream authority S_U1. There is no new downstream attempt for selection.

After phase3 capture S_U2 and build I2:

```text
I2: value=R42, producer=U2, factor=I64(2), fixed role; root=value
I1 != I2                         # full record identity
project(Presult, I1) = J42
project(Presult, I2) = J42        # result-based reuse identity
U1 occurrence != U2 occurrence  # no deduplication of attempts
```

Fork TRUE sibling branches from this same pre-Q4 basis. Each snapshot contains the two policies
and tables; point an explicit active policy name at result/exact P in its respective branch.
Request selects the corresponding explicitly named table. Neither branch edits the other's
refs/defaults/table or migrates its keys. Policy update is an ordinary new snapshot, not mutable
interpretation of previously recorded requests.

Phase4 creates its Dp then PUBLIC Q4 with I2 and requested binding. A separate W4 links Q4 to
OLD D1/R84. The selected downstream attempt's original Q2 still contains I1/U1. No DML completion
packet is fabricated for Q4. Record/read a summary exposing:

```text
requested: Q4 -> I2 -> U2/R42
satisfied by: W4 -> D1 -> Q2 -> I1 -> U1/R42
result: R84
```

This says Q4 reused the result of a computation performed using I1. It does NOT say D1 ran with
U2, or that phase4 is another empirical downstream trial. On the exact sibling, phase5 has no
I2 key although I1 is selected. Record pending Q5, then explicitly execute D2. Preserve old I1
selection; no automatic adoption. This proves exact semantics, not merely a mocked miss flag.

Return to the result branch for phases6/7. Capture S_U3, build I3 with R43/U3/factor2. J43 differs
from J42, so record pending Q7 and explicitly execute D3->R86. Table still selects D1 at J42;
J43 stays absent unless separately adopted. No automatic adoption is part of this story.

## Native and nonexecuting assertions

Across the union of retained main/exact refs: exactly SEVEN distinct request occurrences and
SIX distinct attempt occurrences, with Q4 satisfied by reuse only. Count native identities and
parent reachability, not host dispatch counters. Exact sibling's Q5/D2 need not be ancestors of
main; retain both explicit roots. No extra support Q/T in this acceptance history.

Check independently:

- U1/U2 distinct IDs and occurrences; exact same R42 ID; I1/I2 distinct; J42 exact equality.
- Q4 retains FULL I2, not J42; Q2/D1 retain I1 and U1, W4 exact ownQ4/oldD1/R84.
- Captured policy IDs, tables, actual ordered parent spines and exact tree deltas; old basis,
  selections and sibling refs unchanged. Pexact still matches only full input IDs.
- I3/J43 differ; Q7/D3 result86; both fresh misses leave selections unchanged.
- Each input's value/producer comes from the SAME public validated upstream S; each historical
  row's downstream S owns its original full input and its own validated upstream S.
- Pinned readers operate after original workspaces/packets/source paths are unavailable; only
  safe explicitly owned paths become unavailable after children are known reaped. Retained
  S validation/history supplies authority, not live service/path access.

Transfer both retained roots to a fresh local repository through existing public pinned transfer.
Fresh installed nonexecuting readers verify both provenance chains/policies and result84/86 with
spawning/transport actively blocked. This is local repository evidence, not cross-adapter/cloud
or crash-durability assurance. Use the SAME retained story for coordinator readers; no duplicate
computational story by default.

## Focused companion negatives (separate from story occurrence counts)

Test malformed input role/extra fields, wrong type/factor, swapped U1/R43, failed or unknown
upstream, and dangling/changed selection slots. Equal scalar42 in a DIFFERENT full result DAG
must miss in result mode. Argument type/structure/factor changes cannot share identity.

Test wrong policy/table linkage, old Mi passed as Mp, changed policy-slot after pinned decision,
poisoned nonmatching row, projected Q inputs, W linking another Q/T/R, historical witness overwritten
by requested witness, malformed full native closure even on fresh path. Explicit reuse miss rejects
before a new decision/Q; default miss is pending until separate dispatch.

Representative metadata-only select/adopt/remove checks preserve other rows and old choices;
use existing validated story attempts for adoption controls where possible. No additional real
attempt just to populate a table, test a reader or correct an oracle. Keep original failed probes
and source versions before correction; corrected reads should first consume SAME evidence.

## Stop and qualifications

Proposed local evidence answers this bounded identity/provenance question, not generic arbitrary
facets or scientific correctness. Preserve all local gate failures/UNKNOWN causes; existing native
investigation remains paused and VP-001 is not resolved by a successful story. GHA stays disabled.
No worker restart/build/fixture/source/publication occurs before separately approved GO.
