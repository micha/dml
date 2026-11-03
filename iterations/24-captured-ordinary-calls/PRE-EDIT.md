# Iteration 24 revised pre-edit gate

Status: **review proposal; coding/build/install/test/story HOLD**. Worker session
`01a19e29-2c18-766c-90ee-c5e084fd3ec0`, pane `%215`; coordinator `%197`.
BOTH shared builds/source remain exclusively worker-owned. This authorized design note
changes no DML source or accepted candidate mechanics. Read [HANDOFF](HANDOFF.md),
[DESIGN](DESIGN.md) and [EXAMPLE](EXAMPLE.md). Gates1/2/3/5/6/7 direction was reviewed as
satisfactory for a bounded draft; gate4 remains unresolved. No runtime experiment performed.

## 1. Explicit known-return projection proposal

This is a proposed refinement, NOT adopted behavior or arbitrary-root extraction:

1. Outside every recording write, validate public successful leaf S and its ORIGINAL
   Q/T/P/U/F through `reuse_selection.inspect`, complete transfer, exact captured closure
   and original call/decision association. Validate the strict builtin RETURN profile,
   returned node/value/ordered getter trace, exact Q/full inputs and source ledgers.
   A provisional publication, coherent response flag or equal scalar is insufficient.
2. A phase names THAT validated leaf R in its tree. In a short Recorder scope use public
   `Recorder.source(R, "value")` ONLY for this already validated normal-return profile.
   Retain the bridge as its own absent named tree entry. Its exact fields are the existing
   SOURCE role/value/source/name/node; source=R, name=`value`, node=the selected actual
   Literal NODE ID (BYTES16), value=that node's I64 datum. No equal literal substitute.
3. Downstream argument entry points to THIS bridge. Separate native call/source evidence
   links THIS bridge, actual add S/T/R and pending downstream Q. The session-returned
   logical node remains privately associated with exact selected leaf R and producer S/T;
   rebinding for argument construction explicitly records the bridge, not another origin.
   Validate this relationship on every handle consumption. No global datum-origin lookup.

The boundary is deliberate: builtin Inspector SOURCE checks retained source DAG, selected
named literal NODE ID and datum equality; it counts the source DAG but **does not recursively
certify the source return/trace/Q/producer**. That certification is independently mandatory
in step1 and in full outer selection/completion inspection. SOURCE alone is not success or
producer authority. Public Inspector/Recorder/runtime remain unchanged.

For double reuse the requested bridge links NEW add R3/S3/T3; W links OLD double T2/R2.
The ORIGINAL double input bridge links OLD add R1/S1/T1. Both complete chains, their exact
selected nodes and original public S histories must validate. Projecting cannot erase the
original chain from acceptance evidence or its aggregate accounting.

## 2. One union, not counters reset at scope boundaries

Proposed counting definition for reviewing gate4:

- `U` is the set of **distinct native DAG IDs** subjected to required builtin semantic
  validation for THIS outer execution and all ORIGINAL producer chains it consumes.
  Include literal/source/argument/entry/entry-ledger/operation/trace/return DAGs, selected
  source target DAGs, and captured builtin bindings checked by the interfaces.
- Union inputs, both outer getters, constructed maps, both call results and all selected
  ORIGINAL leaf traces/inputs/results across every short scope and validator. Sets are
  combined by native ID, never by equal datum/value. Independent successful positions
  remain counted even when their immutable operation content shares an ID.
- Closure/control/call/phase/Q/T/S/V/custom outer return/completion roles are strictly
  validated ordinary metadata, not builtin semantic profiles. They still belong to native
  ALL-parent typed closure; excluding them from `U` is a type boundary, not skipping their
  validation. Defaults/alternative captures are separately structurally checked; actual
  computational dependencies used on either chain belong to `U`.
- Native complete reachability/export/import retains every tree entry, DAG/node/datum and
  ALL parents, including old/unrelated history and composite children, under unchanged
  transfer limits100000 objects/4MiB per record/16MiB packed/32MiB bundle. A semantic projection
  cuts neither native graph edges nor transfer/history validation.
- Runtime authoring would maintain an explicit session set/prospective reservations and
  pass its union to completion validation; opening another Recorder does not reset it.
  Current per-Recorder/Inspector64 checks also remain unchanged. Static counts below are
  symbolic estimates for fixed profiles, NOT measured native receipts or hash proofs.

### Revised symbolic accounting

The count deliberately includes all original semantic certification, not just a projected
walk. Repeated `map_get` calls on the same map share ONE map-source argument-entry DAG;
key literals/key-entry DAGs also share when native content is identical.

| ORIGINAL direct-R chain | Added distinct DAGs | Running total |
| --- | ---: | ---: |
| Original a,b input: two literals, two entries, ledger, arguments | 6 | 6 |
| Two outer getters: key literals2/key entries2/map entry1/ledgers2/arguments2/operations2 | 11 | 17 |
| Exact map-get binding | 1 | 18 |
| Reconstructed add input: entries2/ledger1/arguments1 | 4 | 22 |
| Two add getters: map entry1/ledgers2/arguments2/operations2; existing key literals/entries reused | 7 | 29 |
| Add literal42/owned trace/normal return | 3 | 32 |
| Double input: entry1/ledger1/arguments1 | 3 | 35 |
| Double getter: key literal/entries2/ledger/arguments/operation | 6 | 41 |
| Double literal84/owned trace/normal return | 3 | 44 |
| Support list binding checked by unchanged normal leaf wrapper | 1 | 45 |

For swapped OQ3 the additional requested chain contributes input4 + outer getters7 +
reconstructed add input4 + add getters7 + new add trace/return2 + downstream argument3
= **27**. Literal13/29/42, key literal/entries and builtin bindings share; owning normal
return/trace association and all changed input/map-source records do not. Thus the direct
full evidence union is **44+27+1 =72**, already above64.

Correction to the first tmux plan: its new outer-getter increment8 should be7 because the
map-source entry is shared between those two getters. Its bare44+28=72 estimate omitted
list support; the corrected71 plus mandatory support1 is72. Preserve the original estimate;
it was not a native measurement. No extra builtin outer trace is proposed: custom outer
return links its two getter positions directly. Adding separate enclosing builtin traces
would add up to two DAGs across these two outer executions.

The projection creates distinct bridges for old add R1 and new add R3. Other profile counts
stay the same; the double argument ledger changes source link, not profile cardinality:

| Projected accounting | Distinct DAGs |
| --- | ---: |
| ORIGINAL full evidence (including original add chain and list binding) | 46 |
| Requested fresh prefix/add/new bridge/downstream map, including list binding | 37 |
| OLD double R projected semantic walk alone: bridge+source target2/input3/getter6/return3/map binding1 | 15 |
| Requested prefix union OLD projected double walk (shared map binding subtract1) | 51 |
| Additional ORIGINAL add certification outside the projection | 23 |
| **Complete projected evidence union** | **74** |

The23 adds all32 original add-chain DAGs minus its source R already counted1 and eight
shared DAGs (literal13/29/42, key literals a/b, their two key-entry DAGs, map binding).
Therefore **the recorded source projection DOES NOT solve full-union64**. Saying51 passes
while discarding those23 would be precisely the arbitrary scoped-counter interpretation
we must not choose. More source/capture variation can reduce dedup and needs its own
prospective count; these story counts are not general upper bounds.

## 3. Coordinator decision: clarification versus real redesign

Neither alternative below is selected:

**A. Explicit budget clarification.** Keep existing64 per semantic operand/Recorder,16arguments/
16positions and transfer caps. Explicitly revise the candidate's NEW aggregate acceptance
budget, e.g. maximum96 distinct semantic DAGs across current plus original evidence, while
also enforcing two ordinary positions/two outer getters/at most three maps and rejecting
prospective over-budget before launch. This is a visible NEW candidate budget change, NOT
claim that74 meets64, not raising installed constants and not an inherited waiver. Requires
coordinator scope decision; unknown source-specific reservation remains a prelaunch gate.

**B. Real source-sharing redesign (recommended for review if aggregate64 must remain).**
The outer fixed logical function performs its two actual getters to enforce a,b I64 contract,
then calls captured add with the **original exact argument-map NODE**, rather than rebuilding
that map from getter outputs. Add consumes that actual original source ledger. Its two child
getters still really execute, but share immutable operation DAG content with the outer getters
because binding/arguments/source are identical. The logical then constructs double's map from
its exact returned add node as before; no arithmetic moves into the host.

This explicitly changes pseudocode and map-construction count: original input + downstream
map = TWO maps per fresh invocation (rather than three), while fourteen actual getter positions,
six ordinary calls,10Q/8T/five direct leaves and both provenance chains remain. The outer getters
serve actual contract validation, not fabricated calls; acceptance must prove that purpose.
Direct ORIGINAL semantic chain becomes33 (+list1=34); swapped requested additions are input4 +
outer getters7 + add trace/return2 + downstream map3 =16. Full direct evidence union =
**33+16+1=50**; with two explicit source bridges =**52**. No omitted original certification.
Prefer direct exact-R downstream source if adopting B: the bridge is then unnecessary. These
are static estimates; exact graph/reservation checks remain mandatory before sole story.
This is a reviewed logical/profile redesign, NOT permission to implement it without approval.

## 4. Final outcome and same-occurrence attempt schemas

These NEW ordinary roles have separate authority from local F/S. Scalar fields are Literal
nodes; DAG links are SubDAG nodes. Commit IDs are exact BYTES16 metadata whose all-parent
retention is separately checked. No outer OS exit/cleanup is invented.

- Initial T is occurrence-rooted `ca-<32hex>`, exact `role`, `request` Q, `plan` DAG.
  It is immutable and never given final fields in place. Missing final outcome is UNKNOWN.
- Call ledger is role-rooted, exactly `role` plus consecutive slot00/slot01 links; at most2.
  A call record binds owning Q/initialT, exact slot/target C/argument/own leaf Q/control,
  and its immutable pending association. Success additionally links public successful S,
  exact producing T/R and (if reused) own W. Completed failed leaf uses a NEW failure
  witness, NOT successful S: independently saved expected/job/observation framing validates
  exact failed F/Q/T/outcome/cleanup through public observation inspection; F must be retained.
- Success completion DAG: role-rooted `example-outer-success-v1`, exact `role`, `request`,
  `initial-attempt`, `plan`, `calls`, `return`. Require two successful ordered calls, exactly
  two declared getters in return and validated final result ownership. Custom return is
  value-rooted with Q/initialT/inputs/exact returned double R/typed I64 value/call0/call1/
  getter0/getter1 links. No success merely from a flag or value84.
- Known leaf failure completion: role-rooted `example-outer-leaf-failure-v1`, exact `role`,
  `request`, `initial-attempt`, `plan`, `calls`, `failed-call`; failed-call is the last slot.
  No outer return. Slot0 failure forbids slot1; slot1 failure retains committed slot0 S/T/R.
  Actual leaf failure/cleanup disposition stays in the validated leaf witness.
- Known cooperative session failure completion: role-rooted `example-outer-session-failure-v1`,
  exact `role`, `request`, `initial-attempt`, `plan`, `calls`, `reason` STRING from fixed
  session-error categories, `detail` STRING bounded4096 UTF8 bytes. No outer return. Only
  deterministic interface/logical errors with all launched direct children known disposed
  qualify. Caught interface errors still poison success. Persistence/import/ref validation/
  unknown wait errors never get reclassified into this known-failure role.
- Final T: same occurrence root and unchanged role/request/plan field nodes, plus exact
  `initial-attempt` link, `status` STRING `done`, `completion` DAG. Completion links initial
  T, never final T. Return links initial T, never future final T/F. Therefore no self-ID cycle.
- Final history commit has parent `(previous phase,)`, preserves all entries except initial
  T's tree name replaced by final T, and adds only declared completion/terminal-phase names.
  Initial T remains retained via its original parent history and explicit final/completion
  links. Terminal phase binds owning initial T and completion, not its containing commit ID.
  The checked attempt-head moves atomically; response built before commit.
- Publication/import/custody/persistence uncertainty leaves the latest actual partial phases
  and initial T, with outcome UNKNOWN: no invented terminal failure/success or automatic retry.
  Precommit faults abort that batch; postcommit lost acknowledgment may leave full final T/F.
  Explicit ref/native inspection distinguishes publication from response; no fresh computation.

## 5. Outer reuse W: own request, OLD execution

NEW value/result-rooted `example-outer-reuse-v1` W has exactly `role`, `request` NEW Q,
`decision` THIS D, `selection` pinned outer S, `attempt` OLD final T, `result` OLD R.
Q's submission has EXACT parent THIS authored D commit and adds ONLY its canonical Q name;
D's basis supplies exact C/B/E/key/full MAP/control and selected S. Recompute selection eligibility
and validate OLD original completion/initial-to-final T/phase joins/both call associations and
leaf ORIGINAL public-S chains even on fresh/mismatch; malformed present selection is poison.
W's commit has EXACT parent `(own Q submission,)`, preserves its entire tree and adds ONLY
W under absent canonical satisfaction name; create-only explicit reuse ref. W creates no outer
T/phase/getter/inner Q/T or completion. Require exact NEW Q/D/S and OLD selected finalT/R equality,
not descriptions. W failure can leave legitimate own Q; postcommit acknowledgment loss can leave
complete W. Fresh outer/leaf work never changes selected slots automatically.

## 6. Review boundary

Please select gate4's explicit clarification or redesign (or request another design) before
coding/build/run. Failure/W schema spellings remain reviewable. Subsequent focused tests must
exercise union across scope/validator boundaries, exact source/selected-node association and
both producer chains, not just a51 projection walk. Installed readiness still precedes ONE story;
ONE final unchanged full-v, then freeze/release for SAME-history NONEXECUTING independent review.
GHA disabled/NOT RUN/not pass; native19 PAUSED/VP001 OPEN UNKNOWN/no standing waiver. No DML edit,
compiler/actors/build/install/test/story/commit/push or design publication is authorized by this note.
