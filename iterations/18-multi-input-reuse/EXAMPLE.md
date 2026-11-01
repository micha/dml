# Iteration 18 worked example: keep two input selections, adopt only one

Status: **candidate acceptance story, NOT executed; planning authorized, GO pending**.
Read [DESIGN](DESIGN.md) for agreed direction versus candidate mechanics and
[HANDOFF](HANDOFF.md) for conditional implementation/validation/publication boundaries.

## 1. Setup: exact full identities, not a global cache

Capture local implementation A for `urn:example:double`: actual typed I64 `n`, result `2*n`.
The public two-member implementation menu may also capture distinct B for nonexecuting
scope negatives; A remains default throughout, B is NOT executed in normal acceptance.
Do not claim this experiment diagnoses any earlier implementation defect.

```text
reuse default: reuse-by-default
full input DAG I2: root/binding n = I64 2
full input DAG I3: root/binding n = I64 3
new explicitly known table: M_empty scoped to intent URI + full BA
old single-selection slots: absent; not reinterpreted as tables
```

Both input DAGs persist under distinct explicit tree names. Ordinary empty-table publication
is separate from definition publication. No Q/T or implementation installation happens here.
Full matching includes captured source/interpreter/timeout/full inputs. This standalone literal
example omits a producer job; producer-witness identity remains unchanged when supplied.

## 2. Fill the first entry

New table-aware request Q2 selects A/I2. Empty matching-key lookup yields fresh work under
reuse-by-default; record the new table-decision Dm, then own Q2. Explicit existing local
prepare/execute/completed observe/receive records T2old and result DAG R4:

```text
Q2 -> actual A(2) -> T2old / R4
```

Observe/receive successful completed history AFTER synchronous computational-child reaping.
Explicitly capture S2old/V2old with existing public `select` at NEW `selected-2-old` slot.
Then separately insert table entry I2->S2old, creating M_one. S capture/table publication add
no Q/T; late table error can leave a complete captured S that has not been indexed.

## 3. Fill the second without displacing the first

New Q3 selects same BA but full I3. M_one is valid but has no matching key: fresh, not reuse
of R4 and not an error merely because another tuple exists. Actual A(3) records T3/R6.
Explicit public S3/V3 capture at NEW `selected-3`; separately insert I3->S3:

```text
M_two:
  (intent, BA, I2) -> S2old / T2old / R4
  (intent, BA, I3) -> S3    / T3    / R6
```

Prove the I2 row and old selection bytes/ref remain unchanged. No table-wide replacement
of selected history, automatic adoption, eviction or result-based key appears.

## 4. Reuse both input tuples

After actual reaping/S capture, make original packets/expected/workspace/input/B paths for
the first two attempts unavailable. Fresh copied installed policy processes actively block
transport imports and process spawning. Two normal table-aware requests:

```text
new Q2again / W2again -> OLD T2old / R4
new Q3again / W3again -> OLD T3    / R6
```

No third attempt yet. Each W keeps original role/request/attempt/result shape, links its own
new Q to exact historical T/R, and each old T still references its own producing Q. Request
reader recomputes actual Dm parent, implementation/reuse reasons and exact matched entry/S;
latest refs/serialized decision flags cannot substitute authority. Both table entries remain.

## 5. Fresh control is not adoption

Explicit `fresh` for BA/I2 creates FIFTH normal Q and THIRD/last computational attempt:

```text
Q2fresh -> actual A(2) -> T2new / R4
```

T2new has a distinct validated attempt occurrence even though R4 content deduplicates with
the old result. M_two is unchanged; default/other row/S2old/S3 are unchanged. Fresh execution
ignores unused table APPLICATION framing but still validates all reached native history.

Capture successful F2new through PUBLIC `select` into NEW `selected-2-fresh` S2new/V2new slot.
Do NOT overwrite old indexed `selected-2-old`: before adoption, the table remains coherent
and points to S2old while S2new exists unindexed. Reap the third child/capture before making
its original completed files/paths unavailable. No further computational work is needed.

## 6. Explicit one-key adoption and true old-choice sibling

From common C_capture containing M_two and BOTH old/new I2 selections, publish two branches:

```text
                        C_capture (M_two; S2old, S2new, S3)
                         /                               
Ckeep (same tree; I2->S2old)                 Cadopt (ONLY M changes; I2->S2new)
```

Explicit `adopt_entry` validates the old and new S, exact URI/BA/I2 and distinct owning
attempt occurrence. Cadopt replaces only the I2 row; I3->S3 and every non-table tree entry
remain byte-identical. Ckeep preserves M_two with exact same common parent; it is a true
sibling, not simply an old ref alias. Adoption adds no Q/T and changes no default.

Sixth Q on Cadopt reuses T2new/R4. Seventh Q on Ckeep reuses T2old/R4. Equal R4 does not merge
these selections or trials. I3 still selects T3/R6 on both branches; READ the unchanged row
without needing another request. Old Q/T/W/S/V/Dm/table/code/input records and fixed refs stay
unchanged. Moving latest refs cannot retarget either pinned choice.

## 7. Transferred offline readers and focused negatives

Transfer complete pinned request/satisfaction/adoption/keep roots into a fresh repository.
Fresh installed readers, with transport/spawn blockers and no original execution paths, verify
both table entries, exact request bases/own Q/W, old/new I2 choice, I3 preservation and full
ordered-parent/typed/composite closure. Reads add no Q/T/ref or job.

Default-safe tests—not extra acceptance executions—cover:

- Correct nonmatching key is a miss; malformed/present table or S is an error, not fallback.
  Absent table/key default-fresh versus explicit reuse-selected requiring a hit.
- Wrong URI/full binding/table, changed input types/full DAG/producer witness, wrong S slot/
  link, duplicate/wrong rendered key, extra fields/types/roots and candidate finite cap.
  Valid A table cannot satisfy B; no second implementation dispatch needed for this control.
- Explicit fresh/default-execute versus table application framing; missing/corrupt reached
  native history ALWAYS errors even when table is absent/unused.
- Adoption of same attempt occurrence rejects; genuinely fresh equal-result attempt succeeds;
  unrelated row and old proof preserved. Separate capture/table failure boundaries retained.
- Actual Dm parent/exact non-None own Q/old-Q substitution/W and changed returned descriptions;
  new authoring batch rollback/loss with predicted absent actual-A rows. No old fault-matrix replay.

## 8. Normal counts and limits

**SEVEN distinct Q / THREE real local T occurrences**:
initial2, initial3, reuse2, reuse3, fresh2, adopted-branch reuse2, keep-branch reuse2.
Selection/table/branch/adoption/transfer/read operations add none. Enumerate any support
occurrences separately; do not hide them in normal counts. No Batch/SSH/Docker/service/image/
producer/fourth-attempt requirement. Three direct computational children must be explicitly
owned, completed and reaped; no unsafe termination or outcome inferred solely from process exit.

This proposes useful bounded exact-tuple lookup, not cache discovery across history, masks/
facets/equivalence, scientific certification, resource management or a generic evaluator.
VP-001 remains OPEN/UNKNOWN/no standing waiver; prior green is not its diagnosis. No acceptance
story has run and implementation/delegation/publication permission remains separate.
