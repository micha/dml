# Incremental testing — worked candidate

**Subsequent GO:** user “reviewed. GO” approves the bounded story plan, not as-built results or
activation before pre-edit/readiness acceptance. See [coordination](INCREMENTAL-COORDINATION.md)
and pending [pre-edit gate](INCREMENTAL-PRE-EDIT.md). Earlier pending-GO phrasing is historical.

Status: illustrative acceptance plan, NOT as-built evidence or implementation GO.
Read [design](INCREMENTAL-DESIGN.md) and [conditional handoff](INCREMENTAL-HANDOFF.md).

## Fixed scenario and pinned participants

One map/get scenario, TWO checkpoints, THREE builtin positions per checkpoint: source A
twice then source B, both sources carrying MAP `{"x":42}`, shipped getter versions alternating.
Use the existing exerciser's exact fork/root semantics; do not rewrite original assertions.
Stable scenario labels identify positions; actual controller request/attempt occurrences remain
run-specific. Candidate application does not gain ordinary application Q/T from this exercise.

The frozen trusted controller records into store TC. Candidate snapshots A/B are separate
owned directories using the same prepared native artifact, never the moving main checkout.
A matches the pinned base source. B differs by ONE declared comment-only edit to an owned
candidate `builtin.py` copy: intentionally equal behavior but a different whole-build identity.
This tests conservative invalidation, NOT correctness of a new candidate implementation.
P1/C1 are frozen initial projection/check code; P2/C2 each have a declared benign source-byte
change in an owned copy. Source edits and actual imported/executed identities are recorded;
changing a label/hash string without changing execution inputs is not the demonstration.
All pin receipts and stage boundaries require pre-edit review after future GO.

## Seven finite orchestration rounds

Each round asks for the E/P/C chain. The table describes successful-path activation, not
allowance to retry failed runs. Separate explicit adoption commands select only verified
successful results. “Reuse” always points to the producing OLD stage attempt.

| Round | Requested configuration/control | E | P | C |
| --- | --- | --- | --- | --- |
| 1 | A/P1/C1; no selections | Fresh | Fresh | Fresh |
| 2 | Same A/P1/C1; reuse selected | Reuse | Reuse | Reuse |
| 3 | A/P1/C2, checker bytes changed | Reuse | Reuse | Fresh |
| 4 | A/P2/C2, projection bytes changed | Reuse | Fresh | Fresh |
| 5 | B/P2/C2, candidate source bytes changed | Fresh | Fresh | Fresh |
| 6 | Same B/P2/C2; explicitly fresh ALL stages | Fresh | Fresh | Fresh |
| 7 | Separate wrong-result scenario/P2/C2 | Fresh | Fresh | Fresh, expected rejection |

After rounds1/3/4/5, explicit adoption selects the respective successful stage keys so the
next intended reuse has known authority. Round6 performs NO automatic adoption. Its fresh
E has the same E computational key as round5, but a distinct actual occurrence and evidence
manifest; P/C record THIS fresh producer. Verify round5's selection remains unchanged.
Then explicitly adopt round6 E on a sibling branch, leaving the earlier branch selecting
round5 E. P/C selections and unrelated entries stay unchanged. No extra stage execution is
needed for this selection/branch demonstration. Reusing a selection here must not infer
origin from equal native datum/content IDs.

Round7's owned scenario appends the existing native-valid wrong-result43 construction from
`test_spike.py`'s negative case to a normal two-checkpoint exercise. Its changed scenario
identity cannot match the positive selection. SQL must report `map_get_value` with the exact
bad-operation subject, not a vague nonzero exit. The driver records an unexpected-for-positive
result as failure and does NOT adopt it as cached success. The outer acceptance assertion
passes because it independently requires that specific rejection. No global expected-failure
allowlist, swallowed stage exit or removal of the original negative test.

Success-path totals: **21 controller stage requests, 4 E activations, 5 P activations,
6 C activations, 6 reused stage satisfactions**. There are15 fresh stage attempts, one of
which has a rejected C outcome. No generic request-count invariant is inferred for DML apps.
Bootstrap/focused controls are reported separately, not merged into these counts. Selection/
adoption commands are not extra computational stage requests under this candidate profile.
Failure before completion yields smaller actual counts and STOP, not invented missing events.

## What must be observed

- Real stage-entry/exit receipts identify loaded code/native bytes and owning process; no
  fabricated “fresh” counter increment with reused data. No detached service is needed.
- Round2 calls NONE of the three stage entry points. It still creates three NEW requests
  and artifact-admission checks, each linked to OLD attempts.
- Round3 retains E evidence and P fingerprints exactly; only C is freshly invoked.
- Round4 retains E exactly; P/C are new attempts under new keys.
- Round5 invokes E despite equal expected42 outputs. Full candidate identity, not expected
  output equality, drives the miss; P/C cannot silently reuse round4 under different E key.
- Round6 is fresh despite eligible selections, has new occurrences and fresh evidence,
  and does not move selectors until explicit adoption. Old branch choices stay inspectable.
- Round7 retains bad native history, fact projection and exact SQL counterexample, separate
  from earlier positive evidence. No positive selection is modified by a failed stage.

## Negative admission/control cases

Small owned control artifacts should also demonstrate: changed limits/environment namespace
miss or unsupported-context rejection; missing file and tampered file rejection; missing root
is an extraction error, not empty success; swapped same-value producer association rejected;
interrupted artifact-finalization/publication remains unselected; failed/unknown selection
cannot satisfy a new request; same-ID conflicting descriptors and stale publication basis
reject. A stable scenario label cannot collapse two fresh occurrences. Freeze their precise
source/data dependencies and finite fixture needs before activation; they are NOT permission
for additional normal E/P/C chains beyond the seven rounds.

## What this would and would not establish

It would establish the selected three-stage reuse/invalidation/provenance mechanics on one
local declared environment, with actual sensitivity controls. No cached pass self-granted by
candidate code, no false fresh-coverage claim and no automatic adoption are acceptance conditions.

It would NOT replace all44 paired cases/the full suite, prove hermeticity or independent native
codec correctness, provide fresh child/transport custody, meet a five-minute goal, promote a
controller build for general use or diagnose native19/VP-001. Timing is secondary; successful
activation counts and preserved authorities are the primary proof.
