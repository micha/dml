# Iteration 14 worked example: record a choice, execute fresh, adopt explicitly

Status: **reviewed bounded acceptance story; not executed, implementation GO pending**.
The user's “reviewed” checkpoint is separate from implementation/delegation/publication permission.
Exact engineering spellings remain refinable; earlier candidate wording preserves preparation provenance.

Status at preparation: **candidate acceptance story; direction agreed, not executed or implementation GO**.
[DESIGN](DESIGN.md) owns candidate mechanics; [HANDOFF](HANDOFF.md) owns conditional work/review
and stop gates. Exact names/validation-basis shape/helper placement need review. Planning leaves
DML clean at published `b296fdb`; existing worker/builds/fixtures stay stopped.

## 1. Original genuinely executed chain

Using current installed public composition/execution, obtain:

```text
13,29 -> Qadd / Tadd -> Radd(root42)
Radd, exact producer Tadd-final, factor2 -> Qold / Told -> Rold(root84)
```

Receive old successful F0 into A, preserving full native Q/T/P/U/F and composite-only history,
independent caller Cqold/Qold and old packet. Existing sentinel/orchestration refs stay fixed.
After exact terminal-job/ALLclient/namespace proof, stop/archive the finite service. At this point
there are two new Batch jobs, not an adopted/default reusable choice.

## 2. Explicitly record the original choice

On pinned F0, explicitly create ordinary S0 in the `selected-double` tree slot:

```text
S0 (root/result -> Rold84)
├── intent, binding, full inputs I2
├── request -> Qold (original producing request)
├── attempt -> Told-final (chosen successful occurrence)
├── result -> actual Rold
├── completion: exact F0 ID (ordinary metadata)
└── validation -> V0 (bounded public expected/job/observation framing bytes)
```

Recommended publication: Csel0 has parent `(F0,)`, preserves F0's entire tree and adds only S0;
create-only explicit `selection-old` ref points Csel0. No new Q/T/job/result/outcome is created.
S0 does not count another empirical trial. Its supporting F0 is retained by native commit history,
NOT by pretending the completion-ID datum is a native retention edge.

Make ORIGINAL old packet/expected/input/B directories unavailable after capture. With service still
stopped, a fresh installed reader can validate S0 using only pinned repository state: export retained
F0, materialize the captured bounded headers and call the owning public inspector. It does not follow
S0's inert serialized workspace or submit work. Capsule contents are checked, not trusted flags.

## 3. Explicitly reuse the recorded choice

Ask for matching computation through `reuse-selected(Csel0, selected-double, ...)`:

```text
new Qr0 / W0 -> Told-final / Rold84
```

Caller supplies the explicit snapshot/slot/requested dimensions, not another attempt ID or old
external packet path. W0 retains the existing Iteration13 ordinary four-binding association. Its
new Q submission parent pins Csel0's selection-bearing tree; native ancestry plus the known slot
and W0's exact T/R expose the choice. No direct W-to-S edge is claimed in this candidate.

No new attempt/B/job/source invocation. S0 stays byte-identical. Missing/invalid/mismatched selection
rejects; there is no automatic fresh fallback. Q and W remain separate transactions; later W or
projection-file cleanup/response failure can leave pending Q or complete W, not whole-operation
rollback. Reinspection/import creates no request, attempt or selection.

## 4. Deliberately execute fresh, but keep the choice

Separately record Qfresh on a pinned snapshot retaining S0/W0 and identical intent/binding/full I2.
Only explicit stage/submit launches the third real Batch job. Fresh B imports S0/V0/W0/history inertly,
creates only Tfresh and returns F1/Rfresh(root84). Fresh clients observe real P/U/F.

Require Qfresh distinct from Qold/Qr0, Tfresh distinct from Told, and potentially Rfresh==Rold.
S0 still selects Told; W0 still points at Told. Successful fresh execution **does not adopt itself**.
The fixture may resume its previously proven-stopped endpoint/reset the SAME declared finite keys
only after known disposition. That is test policy, not runtime workflow recovery/live-job restart.
After the fresh job is terminal/clients stopped/namespace empty, stop/archive the endpoint again.

## 5. Explicitly adopt and fork

Offline, revalidate S0 and fresh F1 against its independently captured Cqfresh/Qfresh. Explicit
reuse adoption creates ordinary S1/V1 selecting Tfresh/Rfresh for the SAME three dimensions.
Cadopt preserves F1's tree except retargeting `selected-double` from S0 to S1; parents exactly `(F1,)`.
Create-only explicit `adopt-fresh` ref points Cadopt. Nothing mutates S0/Told/Qold/W0 or existing refs.
Adoption creates NO new Q/T/job and is not another fresh execution.

For a true branch comparison, create sibling Ckeep with F1's unchanged tree and `(F1,)` parent:

```text
             F1 (contains S0/W0 plus fresh Q/T/result)
             /                                      
Ckeep: selected-double -> S0        Cadopt: selected-double -> S1
        chosen Told/R84                     chosen Tfresh/R84
```

Explicit `keep-old` and `adopt-fresh` refs retain these snapshots. Fresh installed selected-reuse
clients create new Q/W on each branch, selecting Told versus Tfresh with equal result84. They need
no ORIGINAL packet/expected files, live service, historical interpreter or B. Both branch choices
and every earlier record remain intact. No fourth computational job or repository-global winner.

## 6. Required controls and inspectable boundaries

- Full valid intent/source/interpreter/timeout/factor/type/declared-input/producer-witness changes
  reject; equal42/84 does not relax matching. Different containing commits/annotations are allowed.
- P/U, unknown/missing/unreturnable F, failed F with evidence84 and malformed/wrong-Q history cannot
  select/adopt/reuse. Computational success with failed cleanup follows explicit historical policy.
- Swap S's attempt/result/producing-Q/F or one V header to another otherwise-valid matching attempt:
  public validation/native cross-links reject before Q/selection puts. Completely valid alternate
  selection is an explicit recorded choice, not impersonation of a different pinned snapshot.
- F must be reachable through ALL parents, including nonfirst paths; arbitrary stored F/metadata
  is not retention. Missing/corrupt composite-only history rejects. Metadata bounds stay unchanged.
- Selection/adoption batches are atomic under late new-put/readback/ref/commit/allocation/real map-full
  failures and actual authoring-only pre/post-store-commit loss. Existing Q/W authority is separate.
- A valid older pinned snapshot still selects its own recorded choice; a basis lacking required
  selection/supporting history rejects. Ref conflicts, repeated authoring and scratch cleanup/
  response loss never authorize implicit ref advance, adoption, Q duplication, fresh work or repair.
- Full typed native bytes/every ordered parent/attempt population and independent external job census
  are stronger proof than scalar84, mock counters or bounded CLI. Normal ephemeral final B remains
  explicitly qualified; no new private hold is presumed.

## 7. Deliverable and next gate

A small maintained example-local select/read/reuse-selected/adopt workflow, focused default-safe
native/capsule/rollback/loss/branch tests, actual installed three-job/nine-phase chain and informative
documentation through unchanged owners. Initial S/Csel, adoption S/Cadopt and Q/W/storage/files/
service are separate boundaries; no generic framework/new native entity/private role codec.

Candidate details require review, then separate bounded implementation/delegation/publication GO.
This example has NOT been executed; no worker/build/fixture/image/CI/source restart or commit/push.
