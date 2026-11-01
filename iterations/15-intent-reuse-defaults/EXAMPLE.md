# Iteration 15 worked example: a default chooses reuse or fresh work

Current delivery: **implemented, independently accepted, published and STOPPED through
`664a870`**, all six final exact-SHA CI41090059076 jobs successful. Actual worker and
separate independent four-job/twelve-phase gates pass; see [RESULTS](RESULTS.md),
[REVIEW](REVIEW.md) and [COORDINATION](COORDINATION.md). The acceptance story/status
below preserves planning chronology, not a claim of pending GO or permission to restart.
Actual example mechanics are [documented separately](../../../dml/docs/intent-reuse-defaults.md).

Status: **bounded acceptance story approved; NOT executed, implementation GO pending**.
The user approved the example/design/handoff as the bounded plan, not implemented behavior or
worker/build/fixture/CI permission. Exact engineering spellings remain refinable. Earlier
preparation wording below preserves provenance.

Status at preparation: **candidate acceptance story; direction agreed, NOT executed or implementation GO**.
[DESIGN](DESIGN.md) distinguishes agreed behavior from recommended Idef/D/transaction mechanics;
[HANDOFF](HANDOFF.md) owns conditional work/review/stop gates. Exact spellings remain refinable.
DML stays clean published8393a82; worker/builds/fixtures/CI remain stopped. No checkpoint requested.

## 1. Define one intent default and obtain the producer

Predeclare the existing trusted add/double bindings. Record minimal ordinary intent definition
`Idef0` under illustrative tree entry `double-intent`:

```text
intent URI = urn:example:double
intent default = reuse-by-default
selected-double is ABSENT
```

Idef0 is versioned data, not a core purity classification or automatic implementation selection.
Callers still supply known binding/input/selection names. Its publication creates no Q/T/job.
Execute the existing add step normally:

```text
13,29 -> Qadd / Tadd -> Radd(root42)
```

Receive its exact successful recorded F, then existing public composition creates full double
inputs `I2`: actual Radd sub-DAG, exact selected final producer Tadd witness, factor2 and all
other declared fields. Idef0 survives unchanged in these snapshots. Policy is being explored
only for double; add is the dependency-producing setup, not another policy registry entry.

## 2. Default reuse with genuine absence deliberately executes

An ordinary policy request pins this snapshot/known intent and selection slot, override=default.
The slot really does not exist; no decoder/IO error is treated as absence.

Recommended decision description Dmiss records:

```text
Idef0 / exact binding / full I2
requested override: default
resolved action: execute-fresh
reason: default-no-selection
no selected attempt used
```

Cdec-miss preserves the basis tree/adds only Dmiss, parent exactly `(basis,)`. Existing public Q
recording then creates Qold/Cqold with exactly `(Cdec-miss,)` parent/adds only Qold. Neither D nor
Q proves dispatch. Only the explicit application driver stages/submits the second actual Batch job:

```text
Qold / Told -> Rold(root84)
```

Fresh observers retrieve real P/U/F; full exact-Q history is received under explicit refs.
Successful F0 still has **NO selection slot**. Default absence permitted work, not adoption.

After terminal-job/ALLclient/empty namespace proof, stop/archive service. Deliberately use the
existing select operation to publish S0/V0 choosing Told/Rold. No third job/Q/T is created.
Remove availability of original packet/independent expected/input/B paths after owned capture;
new readers need only persisted framing/native all-parent support, not those old paths.

## 3. A matching default request now reuses

With service OFFLINE, a fresh installed copied policy example reads pinned Idef0/S0 and exact
binding/I2. No attempt ID is supplied by the caller:

```text
Dreuse: override default, action reuse-selected, reason default-selection, selection S0
new Qr0 / ordinary W0 -> Told-final / Rold84
```

Recommended separate spine is `(C -> Cdec -> Cqr -> Cr)`. D refers directly to Idef0/S0; W0 keeps
its original four-binding shape. Q submission ancestry/known decision entry/exact W Q/T/R links
explain the default choice. No direct W-to-D/S edge is claimed. Old producing Qold/Told stay linked;
new Qr0 is a request, not another execution. Exact native attempt population/external job set stay
unchanged at two Batch jobs. Reinspection/transfer creates no Q/T/decision/job.

## 4. Explicit fresh override, still no automatic adoption

On a snapshot retaining Idef0/S0/W0, request override=fresh:

```text
Dfresh: Idef0 still reuse-by-default, override fresh, action execute-fresh,
        reason override-fresh, no selected attempt used
new Qfresh / Tfresh -> Rfresh(root84)
```

The helper records D and its own Q; the explicitly chosen existing adapter driver launches the
THIRD real job. Fixture resume/reset of SAME declared finite keys follows only proven-stopped
terminal/client/namespace state, not runtime recovery. B imports Idef/D/S0/V0/W0 inertly;
P/U/F/A preserve EVERY old packed byte/ordered parent. Tfresh occurrence is genuinely distinct;
Rf may equal Rold. S0 still selects Told and W0 still refers to Told. Definition is not changed.

After terminal/ALLclient/empty namespace, stop/archive again. Explicit existing occurrence-based
adoption creates S1/V1 selecting Tfresh in a NEW snapshot; no Q/T/job or old-object rewrite.
Original fresh packet/expected files become unavailable after capture. Another ordinary default
request now reuses S1/Tfresh/R84 with a new Q/W and no fourth job at this point.

## 5. Two branch-local defaults

From a pinned snapshot retaining S1 and Idef0, create true siblings:

```text
                         Cbranch (Idef0 reuse, S1 selects Tfresh)
                           /                         \
Ckeep: unchanged tree, parent Cbranch     Cexecute: replace only intent slot with Idef1
        Idef0 / S1                                 same URI, execute-by-default / S1
                                                   parent exactly Cbranch
```

Policy change creates no Q/T/job, modifies no selection or old definition, and advances no other
head. Both branches retain the same full computational dimensions; Idef's control-only version
change does not change their matching tuple.

- Ordinary request on Ckeep: D captures Idef0/default-selection, reuses Tfresh, new Q/W only.
- Ordinary request on Cexecute: D captures Idef1/default-execution. The explicit driver launches
  the FOURTH actual double job, producing Texecute/R84. S1 remains Tfresh, not Texecute.
- Explicit selected-reuse override on the execute-default branch: D captures Idef1 plus override-
  selected-reuse; new Q/W uses S1/Tfresh, not the most recently executed Texecute. No fifth job.

After final terminal/client/namespace proof, stop/archive. Fresh installed readers/transferred
repositories inspect definition versions, reasons, requests, old selected/fresh occurrences and
equal results with no live service/original evidence. Branch refs/main/old submissions remain
unchanged. There is no repository-global default winner or invisible latest selection.

## 6. Counts and uncertainty

Recommended normal gate has precisely **FOUR actual Batch jobs/TWELVE P/U/F phases**:
add; absence-driven old double; explicit-fresh double; execute-default double.
All policy-definition publications, D records, select/adopt, default hits and explicit-selected
hits add no external job or computational attempt. If existing support retains a genuine host-prior
attempt, enumerate it separately; four Batch jobs is not a claim of only four global empirical
occurrences. Compare complete native request/attempt versions, not just controller counters.

D publication, Q, W, preparation files, service submission and reception are separate boundaries.
Q failure can leave D without Q; W failure can leave D plus pending Q; late projection cleanup/
response loss can leave complete D/Q/W. Lost response never authorizes duplicate Q/fresh fallback/
selection change or automatic repair. A returned execute-fresh Q is still pending until explicit
adapter work records T/outcome. Missing final outcome stays unknown, not failed.

## 7. Required controls

- Missing/malformed intent definition, unknown default/override, wrong root/role/type/extra fields
  reject before D/Q. Policy update cannot silently change URI or overwrite another tree entry.
- Default reuse's present malformed/mismatched S rejects BEFORE any D/Q/dispatch; never catch its
  exceptions as "no selection". Explicit-selected missing S rejects rather than executing fresh.
- Approved bounded-plan distinction: declared fresh/default-execute need not inspect unused S application
  metadata; native reached history must still be intact. Their reason is explicit execution, NOT
  fallback after a reuse error; S is not repaired/adopted.
- Full source/interpreter/timeout/factor/type/producer-witness differences remain reuse mismatches.
  Equal42/84 never substitutes occurrence. Policy-only version/annotations/ref movement do not
  retarget a pinned choice; definition can change without changing full binding/I2.
- Typed-complete tampered D action/reason/override/Idef/name/S links reject through example native
  context plus owning public preparation/S/V validation. Supplied verdict flags are not authority;
  a fully coherent different declaration is another recorded choice, not detectable fraud.
- New Idef/D late-fault batches require genuinely NEW actual-A readbacks/native absence, full
  rollback/real map-full/consuming commit/response allocation and safe authoring-only pre/post-
  store-commit loss. Existing Q/W/storage-response/projection boundaries stay separate.
- Default hits/definition changes/adoption/readers remain endpoint-OFFLINE. Broad HTTP/Floci/Docker
  import and process-spawn blockers operate in THAT policy/reader process; dispatch lives outside
  it. Normal final B remains ephemeral; no private hold/fifth job/fault-matrix repetition presumed.
- All-status external census plus fresh persisted before/after two/three/four-job archives, full
  typed bytes/every ordered parent/attempt population and exact owned stopped resources corroborate
  behavior. Batching source validation files or reading metadata is not an external job.

Next: separate bounded implementation/delegation/publication GO if requested. The Idef/D/public-
validation/decision-parent/unused-S mechanics are the approved bounded plan, not as-built behavior.
This story has NOT been executed; no worker/source/build/fixture/image/provisioning/CI/commit/push
permission follows from plan approval.
