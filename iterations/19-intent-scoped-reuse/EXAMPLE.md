# Iteration 19 worked example: share across bindings, remove one choice

Status: **candidate acceptance story, NOT executed; planning authorized, GO pending**.
Read [DESIGN](DESIGN.md) and [HANDOFF](HANDOFF.md). Counts/mechanics are assistant candidates
for bounded review, not as-built results or additional user decisions.

## 1. Setup

Intent `urn:example:double` declares interchangeable result semantics for its implementations.
Capture two distinct actual local bindings: A uses `2*n`, B uses `n+n`. Both consume typed I64 n,
produce identically shaped result sub-DAGs and retain actual captured source/interpreter/timeout.
A is default throughout; requests explicitly select B where noted. No default change is needed.

```text
I2: full input DAG, n=I64 2
I3: full input DAG, n=I64 3
Mi_empty: explicitly named intent-scoped table, no binding field
reuse default: reuse-by-default
```

Same-intent membership is a user declaration, not scientific proof. No adapter availability/
installation promise is made. Both implementations are local in this bounded test; no actual
Docker-to-Batch transport validation is claimed. New role/table/decision readers do not silently
reinterpret old binding-scoped M/Dm. User and bookkeeping DAGs continue sharing one tree.

## 2. Two independent input entries

Request1 selects A/I2; valid empty table misses. Record Di and own Q1_A2, then explicitly
prepare/execute/completed observe/receive: T_A2/R4, success/cleanup authority after child reaping.
Capture S_A2 through unchanged public selection at NEW `selected-a2` slot using ACTUAL A binding.
Separately insert I2->S_A2 into Mi.

Request2 selects A/I3; valid table misses I3. Execute T_A3/R6, capture S_A3 at NEW slot and insert
I3->S_A3 without displacing I2. At this point:

```text
Mi_two, scope = intent only:
  I2 -> S_A2 / producing binding A / T_A2 / R4
  I3 -> S_A3 / producing binding A / T_A3 / R6
```

Capture/table authoring adds no Q/T. Reap both children/capture before renaming original packet/
expected/workspace/input/B paths unavailable. Later policies revalidate producer S from native
history, not those paths. Original bytes/logs/source copies stay inert evidence.

## 3. Request B, reuse A

Request3 explicitly selects B/I2 under reuse default. Fresh copied installed nonexecuting client
with transport/spawn blockers validates same URI/full I2, despite producer binding A != requested B:

```text
new Q3_B2: binding B, inputs I2
new W3: request Q3_B2 -> OLD T_A2 / R4
OLD T_A2 -> original Q1_A2: binding A, inputs I2
```

No B attempt/adapter invocation/job/completion or cleanup is invented. Di names B as requested
choice and links the actual S_A2; producer binding remains A. Exact public own-Q validation and
independent successful S authority agree. Table/default/S bytes do not change. Old same-binding
reuse APIs still reject this cross-binding pairing; only NEW policy composes this association.

## 4. Fresh B and explicit cross-binding adoption

Request4 explicitly selects B/I2 with `fresh`. Actual synchronous B returns R4 through a distinct
T_B2 occurrence. Fresh success leaves Mi_two unchanged. Capture S_B2 at NEW `selected-b2` slot
using ACTUAL B binding; do not overwrite indexed `selected-a2`. New S exists unindexed.

From common C_capture retaining Mi_two/S_A2/S_A3/S_B2, publish:

```text
Ckeep:  same table/tree, parent C_capture
Cadopt: ONLY table changes I2 -> S_B2, parent C_capture
```

Publicly validate SAME intent/I2 and distinct owning attempt; binding difference is permitted.
I3 row/old S slots/non-table entries stay byte-identical. Same R4 content does not merge attempts.
Reap/capture third computational child, then make its original paths unavailable.

Request5 explicitly selects A/I2 on Cadopt and reuses B's result:

```text
new Q5_A2: binding A
new W5 -> OLD T_B2 / R4 (producing Q4_B2/binding B)
```

No new A attempt. Offline readers inspect Ckeep still choosing A2, Cadopt choosing B2, both
retaining I3->A3. No extra request needed merely to read the old sibling's choice.

## 5. Remove only I2, then actually execute the miss

From Request5's satisfaction basis, explicitly remove exact I2 key in a new Mi snapshot:

```text
Mi_removed:
  I3 -> S_A3 / T_A3 / R6
# I2 absent; old S_A2/S_B2 and all Q/T/R/proof/history remain.
```

Removal adds no Q/T, changes no default/other row/selection slots and does not propagate across
branches. Old fixed refs/trees still preserve selections A2 and B2. No prohibition on R4 is stored.
Malformed tables are not repaired by removal; no global cache search or S deletion occurs.

Request6 explicitly selects B/I2 with `default`. Strict valid table has no I2: `default-no-entry`,
own pending Q6_B2, NO selected S/W. Explicit adapter execution records fourth/last real attempt
T_B2_after_remove/R4. Prove the new attempt ID differs even though R4 content is equal; table still
contains ONLY I3. No automatic selection/adoption/reinsertion or hidden reuse of retained T_A2/T_B2.
Reap fourth child before completed observation/receive; preserve evidence under unavailable names
once all required inspections are complete. No extra S capture needed for this last attempt.

Explicit reuse-selected on missing I2 is tested to reject BEFORE Di/Q, not a seventh request.
Explicit reselection of a retained old successful S is permitted by the agreed policy; test on an
isolated/new branch without another computation, proving removal is not a persistent content ban.
Do not silently reinsert during normal requesting or label it a recovery mechanism.

## 6. Transferred readers and focused controls

Transfer complete pinned Q/satisfaction/keep/adopt/removal/final roots to a fresh repository.
Copied installed readers with active transport/spawn blockers need no original packet/expected/
workspace/input/B/service/source execution. Check full typed/all-parent/composite closure, exact
own-Q/requested binding versus S/producing binding, W/Q/T/R links, ordered parents, old bytes/refs,
two-input history/one remaining row/no automatic adoption and actual native census.

Focused tests, not extra installed computations:

- Different canonical intent or full inputs/type/producer witness rejects selected reuse;
  binding difference ALONE permits it under NEW policy, never under old exact-binding helpers.
- Malformed/invalid nonmatching row/slot/S/producer Q/F/T/R rejects, no fallback; fresh ignores
  unused table application framing but still validates complete reached native closure.
- Requested binding/Q must never be overwritten by producer binding/Q; returned old-Q/NoneQ/
  forged Cq/W/ref/base/reasons reject, preserving earlier published batches when appropriate.
- Same attempt occurrence adoption rejects; A->B adoption and same-result distinct attempts work.
- Removal requires exact present key, preserves all other rows/old S/history; absent-key/wrong
  URI/invalid table failures cause no partial publication. Empty table after last-key removal works.
- Unrelated valid advisory supersession/deprecation metadata does not filter successful results,
  choose binding/default, delete entries or create a new knowledge-view feature. Older supersession
  context reader owns old D, not this new decision. No result restriction is interpreted.
- Direct-W/table-removal late authoring rollback/loss with predicted genuinely absent actual-A
  rows; no unsafe computational termination/whole-workflow rollback/physical-power-loss claim.

## 7. Counts and limitations

**SIX distinct normal requests / FOUR real synchronous LOCAL attempt occurrences:**

| Request | Requested binding/input | Outcome |
| --- | --- | --- |
| 1 | A/I2 | fresh A2 ->4 |
| 2 | A/I3 | fresh A3 ->6 |
| 3 | B/I2 | reuse A2 ->4; no attempt |
| 4 | B/I2, explicit fresh | fresh B2 ->4 |
| 5 | A/I2 | reuse adopted B2 ->4; no attempt |
| 6 | B/I2, after removal | default miss, fresh B2 ->4; no adoption |

Zero support occurrences IN acceptance history. Metadata/branch/transfer/reads add none. Fourth
attempt has specific assurance value: proves removal-driven fresh work, while second input's
actual attempt proves unrelated-row preservation. Not the superseded four-Q/two-attempt draft.
No fifth attempt/producer/Batch/SSH/Docker/image/service/default promotion or duplicate story.

This proves bounded intent-level declared equivalence/provenance/versioned removal composition,
not scientific correctness/full environment/efficient global indexing or actual cross-adapter
execution. Preserve original controller identity BEFORE runs and original failed probes; prefer
corrected NONEXECUTING oracles on SAME retained history over duplicate computations. VP-001 stays
OPEN UNKNOWN/no standing waiver; no story has run and implementation/publication GO is separate.
