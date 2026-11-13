# Per-exercise prototype — corrected focus / readiness review

**Subsequent bounded completion:** user approved this and future gates; PE-002/003 fixed/6targeted
pass, delegated readiness accepted/sole story0/SAME4272 audit0. Raw final284failed test-import bridge
corrected narrowly; causal final286pass. [Results](PER-EXERCISE-RESULTS.md) COMPLETE/STOPPED,
[coordination](PER-EXERCISE-COORDINATION.md) owns actual decisions. Historical blockers below retained.

Status: **Corrected focused gate PASSES; readiness NOT ACCEPTED, two new guard gaps block story.**
[Coordination](PER-EXERCISE-COORDINATION.md), original [failure](PER-EXERCISE-FOCUS-FAILURE.md),
[design](PER-EXERCISE-DESIGN.md). User approved ONLY two-file boundary fix, one pure regression,
one corrected snapshot and one corrected focused invocation. All performed within that scope.
No acceptance stage/story/final collection/current native reader/query replay from readiness review.

## Approved correction and actual evidence

Changed executable paths ONLY project.py/test_per_exercise.py. Explicit `canonical_rows(raw)`
converts native extractor mapping with `ordered(dict(raw))`; strict existing serialized capsule
validator/row field/type/uniqueness/cap checks remain unchanged. ONE pure test covers conversion,
defaultdict serialization rejection and unknown extra table rejection. Original48 function/class
ASTs equal archived failed source, additional function exactly one. Prior59 executable files exact.

ONE NEW per-exercise-v2/pins preparation TRUEexit0. ONE corrected focus **49PASS1.62s/TRUEexit0**,
actual49 XML/no errors/failures/skips. Existing failed48/33pass15errors0.67s/exit1/source12/pins/
partial native originals untouched under v1; not overwritten or relabeled passing.

Important correction to the proposed wording “new namespace”: actual trusted controller/code8/
common wrapper/E fingerprints stayed IDENTICAL. This is a replaceable P payload fix, so P1/P2
actual code/manifest identities changed and downstream P/C keys change, but C payload/code and
controller namespace do not. That is the approved dependency-independence design, not accidental
source equivalence or a new namespace/fresh platform guarantee. v2 is a NEW snapshot LOCATION.

Corrected CONTROL fixture:3direct helpers/18builtin positions,3export/public imports/projections,
ONE pooled loader +3 scoped SQL queries (positive,owningnegative,disabledowningrule). No E/P/C
controller processes/requests/attempts/selections/adoption/continuation/acceptance. Four real CLI
owner receipts waited0 and PIDs absent, verified from retained files (wrapperPID not separately
retained). No fake owner/custody receipt. Deliberate disabled-rule outer AssertionError caught by
its negative test, not a product failure transformed into a cached stage success.

Actual case typed counts151/157/151; union272≤10000. Portable bundle sizes25457/26414/25457bytes;
canonical capsules77555/80462/77555bytes. Small CONTROL data fits, NOT a measurement of the future
seven-generation history/33stage workload. Story still hard-admits every actual bound.

Retained evidence `../dml-relational-spike/build/relational-spike/per-exercise-v2/`: source.json,
correction-audit.json (two paths/originalAST/old archive), actual pins, prepare/focus rawlogs/XML/
trueexits, native/portable CONTROL sources/projections/pool/queries/diagnostics/owners,
focus-audit.json (stdlib SAME files/XML only). Source12 currently exact, old59/source/archive verified.
No second corrected preparation/focus or story. Main/shared builds/GHA/native19/VP001 unchanged.

## Static changed-surface review — blocking gaps

### PE-002: reported foreign outcome not cross-checked

`batch.authority` reads the actual selected terminal and its outcome, validates current request/
producing input/key/spec/artifact/status/satisfaction. But its final checks do NOT compare
`result['outcome']` with `str(attempt['outcome'])`. Both evidence entry and native controller
case grouping subsequently use the supplied result outcome. Normal `Controller.result()` supplies
the right ID, but that producer convention is not an admission guard against a forged cross-link.

Consequently a malformed result can retain a valid T/request/artifact while naming another outcome
in the grouped evidence. The claimed externalQ/T/O cross-check must not rely on that unchecked
member. This is a source-established new admission omission; NOT an actual observed corrupted
batch, native storage/old runtime failure or historical diagnosis. Existing focus has no owning
forged-outcome regression, and old Store tests do not cover this new grouping adapter.

### PE-003: native batch datum kinds discarded

The nested `batch.inspect.fields` checks field names/role/root, then reads literal `.value` only.
Entry comparison uses dictionary equality against wanted Python values. It does not preserve/
validate native datum kinds. In particular Python boolTrue and integer1 compare equal, so a native
I64 `fresh=1` can compare equal to expected BOOLTrue. Literal IDs and SubDAG links likewise require
explicit profile kinds, not just post-conversion value comparisons.

New strict native profile validation promised by pre-edit is therefore incomplete. Fixed writer
currently emits the intended types, but typed-invalid evidence must fail admission. Static issue,
not an actually run native mutant/batch; no such probe claimed. Existing49 controls concern old
producer/capsule profiles and key/SQL semantics, not this NEW batch field decoder.

## Proposed next bounded guard correction — approval required

ONLY TWO NEW owning executable paths: batch.py/test_per_exercise.py.

1. Add explicit result outcome ID versus selected actual attempt outcome comparison before native
   evidence/grouping publication; no old role/Store/schema changes or weaker outcome checks.
2. Factor native batch field reader into a strict owning function with explicit profile field
   kinds, literal STRING role/root, literal BOOLfresh/STRINGkeys/BYTESforeign IDs/context,
   native SubDAG producer/group links. Preserve existing exact names and compare wanted values;
   wrong native kind rejects BEFORE that comparison.
3. Add SIX focused controls: valid/forged reported outcome (pure isolated role-admission control,
   not security proof); valid native field profile; I64-for-BOOL rejection; STRING-for-BYTES rejection;
   literal-for-SubDAG rejection. Existing49 test bodies unchanged, isolated collection becomes55new
   controls/284total if no later additions.

Preserve exact corrected-v2 source/proof before edits. ONE fresh corrected snapshot (trusted batch
code changes, therefore actual controller namespace changes) +ONE TARGETED six-case invocation
NEW owned outputs/XML/trueexit. Field-kind tests use one small CONTROL metadata-only native store,
no builtin calls/application attempts/portablecase/extractor/pool/SQL/stage-controller activation.
No whole49 repeat/accepted story/dummy warm-up or hidden retry. After pass, SAME source/fixture/
foreign guard and readiness review before deciding ONE seven-round acceptance. Further failure or
uncertainty STOP for named causal scope. This is not automatic authorization for this correction.

Current pause is the readiness blocker decision. No time/cap/threshold/skip/native/API/old helper
change, dependency/install/build/CI/GHA/main/shared-build takeover/extraagent/commit/push or controller
production promotion. Completed two-file approved correction does not authorize automatic next
engineering/activation; original failed evidence/qualifications/VP001 OPEN UNKNOWN retained.
