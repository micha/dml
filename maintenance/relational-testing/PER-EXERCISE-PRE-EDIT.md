# Per-exercise reuse — concrete pre-edit review

**READ-ONLY PLAN COMPLETE; awaiting gate acceptance before source edits/builds/tests/activation.**
User “implementation is GO” approves the [design](PER-EXERCISE-DESIGN.md),
[example](PER-EXERCISE-EXAMPLE.md), [handoff](PER-EXERCISE-HANDOFF.md), retaining this mandatory
review and later readiness. Current assistant owns ONLY additive isolated spike work, not another
agent/main/Iteration25/shared builds. [Coordination](PER-EXERCISE-COORDINATION.md).
Exact engineering below is proposed concretization for this gate, not as-built source or proof.

## 1. Preservation, actual pins and new source scope

Actual current observations, without native import or database reads:

- Worktree `../dml-relational-spike`, HEAD15555c01e4db19a20b4de7049f776c4d995bd5e0, tracked diff empty;
  `spikes/` untracked. `per_exercise/` and `build/relational-spike/per-exercise-v1/` both ABSENT.
-372 tracked file manifest (Git path/mode/order, actual size/hash, sorted-key compact ASCII JSON)
  SHA256 `6dfe866aa2fd13938a938260542240d8a55694e83103484c5adfff5d48583c3b`, agreeing prior baseline.
-59 prior spike `.py`/`.sql` files, lexicographic relative POSIX paths/size/hash/sorted-key compact
  JSON inventory digest `b738c8ffb2fb36b95ed76cd2b8f507b227d510d9395828cfcdf15f300e9798cd`.
  This records current source bytes, not complete historic execution/evidence provenance.
- `_core.abi3.so`:885112 bytes,
  `5fd0ce05a9bb48bb7bdcf2b7de212427f54522c37301e12e4ec7fc7f14fda134`.
  `_core_fault.abi3.so`:894192 bytes,
  `b3f8821144bf64cda49c9ecfaba282e6f88dcdf4517087fab046fa925520febd`.
  New generated exercise uses ordinary core only; fault binary remains only the old direct-test
  dependency, no new fault activation, no candidate recorder/core substitution.

Selected current owning source hashes:

| Source | SHA256 |
| --- | --- |
| incremental/records.py | d5e2a115531a26d2b80c18fb3851288bafe74325bc7c0c5a108cce4507e98d35 |
| incremental/identity.py | 8ab7950ce6e953c08552e376e3fdf2fe95c85bf058818b75e3fbcdcbaca690d4 |
| incremental/artifacts.py | de3e34e5582e3a47d0fd8b4a640555c42dd617f83cc24c246351c723d5998002 |
| shared_index/exercise.py | 3f87330e2ec59e8a828d8c8d8934695bd22ab209d90fc1aa1415fefef5dd7572 |
| shared_index/project.py | 7c3128082f9c994f34e1aa903d65dd9d23dd7c119d65a98ef415029b2e81c70e |
| shared_index/check.py | f32df7ae2682a903867ac857d51696b4fe2c8cbfc8c37780c95dff6dbec88f09 |
| normalizer.py | 61df051366e292777e5ece416b59015583c72cfe5243f177783831ffe53e7f02 |
| schema.py | 2e50597486ab7ee9ef3e92461017ca364cf86dd5ed79e4d7f7b7a6ab6c96d418 |
| checks.sql | bbf58e51f33710321176bcad80e40880c51beb038a5eb0dc228f4aaaf223f219 |
| engine.py | 36ee67871706a19c7cbc05292f1b0807bbc558848ee3a73aca0a770bed273318 |

After acceptance, preserve exact full prior executable inventory in NEW evidence before adding
files. New12 proposed files ONLY: `__init__.py`, `pins.py`, `profiles.py`, `evidence.py`, `capsules.py`,
`batch.py`, `stages.py`, `driver.py`, `project.py`, `predicate.py`, `test_per_exercise.py`, `README.md`.
Names refinable only within these responsibilities. No old source/body/SQL rewrite. Existing
identity/artifacts/Store reused unchanged; no promotion of speculative machinery to maintained DML.

Snapshot destination NEW `per-exercise-v1/pins/`: frozen legacy recorder package/code/native,
A/B whole tracked candidate copies (actual B builtin comment change), pinned shared_index/extractor/
schema/engine/SQL helpers, NEW trusted eight-module controller/wrapper code, isolated P1/P2 project
payload and C1/C2 predicate/SQL payload. Actual P2/C2 source comment variants loaded from the declared
paths, not only different revision hashes. Transitive code included. Replaceable payload variants
excluded from the controller namespace and from unrelated E inputs.

Use the same existing absolute Python/DuckDB/library pins as `incremental.driver`, with static
byte checks during preparation. Cached test pytest/Hypothesis environment and existing isolated
DuckDB1.5.2 binding only for focused/final tests, no installation. No controller trust promotion.

Static `readelf -d` confirms core's only NEEDED libc and RUNPATH starts mutable
`/work/repos/micha/dml-design/outputs/out/lib` before immutable glibc/GCC paths. Never patch/rebuild
ELF here. Absolute Python `-I -B`, explicit package/source paths, minimal environment with pinned
LD_LIBRARY_PATH/glibc/GCC, owned HOME/TMPDIR/hash seed/locale, no ambient PYTHONPATH/preload/audit.
Actual core/Python/module/loaded-library receipts revalidated on successful actor admission.
Qualified pinned as-built artifact + old build logs, NOT signed source-to-binary/reproducibility/
hermetic/security proof. Unknown loaded-library/path/source mismatch stops.

## 2. Exact envelopes and variant independence

Keep existing `FORMAT`, required dependency fields and domain-separated E/P/C keys. Canonical input
fields reject missing/extra keys, floats, duplicate JSON keys, bool-as-I64 and unsupported types.

E context exactly `{profile: per-exercise-v1, scenario: stableID, value: I64, fault: bool}` with
scenario limited to positive-a/negative-b/positive-c. Whole candidate manifest hash in candidate;
exercise manifest hashes fixed helper/harness/evidence contract; wrapper/runtime as before.
No run/Q/T/batch/path/other-case-value in this context. Those operational facts are recorded in
native Q/T and new grouping records, not omitted from provenance.

P context adds exactly the selected ONE E publication root and same requested case profile.
`upstream_key` and `upstream_artifact` come from admitted E terminal authority, not caller strings;
normalizer composite includes project/capsule/schema/materializer/decoder dependencies. Native
source/schema/SQL imports are pinned. P1/P2 different executed payload bytes partition only P/C.

C context contains same case profile and exact selected P case boundary, roots and authority
summary. Full P key/artifact digest + checker/transitive SQL/predicate/source-scope/assertion
contract/DuckDB runtime define it. Case membership validated from actual CN closure and its capsule.
No pooled DB digest/current grouping/counter/foreign case in C key. C1/C2 different executed bytes
partition C only. Common trusted-wrapper edits conservatively invalidate all affected keys.

Parent recomputes expected envelope; validates upstream terminal/request/status/artifact/key/roots/
case context. Known selector lookup requires full envelope equality. Found-invalid errors, not
miss/retry. Legacy Store supplies actual reserved run/event occurrences and basis protection.

## 3. Shared stores, one-case fixture and portable custody

Three native stores under NEW owned story root: controller.dml; evidence.dml; decoder.dml.
ONE serialized owner; separate actor opens only its declared store, copied IDs cross short scopes.
E actor never touches controller store; C opens NO native store. No old retired repository access,
LMDB file/lock copying, reset, detached worker or LOCAL adapter.

Fresh E constructs a fixture from exactly one requested value (`fixture(tx,[spec])`), so unrelated
parameters never bind its fixture. Uses fixed `make_case` to record v1/v2 checkpoints with3calls
apiece, actual returned values checked; deliberate wrong value only in its declared fault case.
Original helper roles retained. Wrap actual context/observations/producer run in one-case P0/P1
with parents(P0,CN). The actual E attempt occurrence prefixes `/exercise-1` in its old producer
profile; stable label matches requested scenario. Do not use NEW batch occurrence as producer.

Close handles before public export of THIS P1, persist portable bundle+root/context/producer/source
receipts outside working native store. E artifact status success means exercise/evidence completed,
including deliberately malformed semantic result—not cached SQL acceptance. Bundle/root hashes and
producer fields validated against E request/T at admission.

Fresh P imports THIS bundle publicly into shared decoder, checks returned P1 ID, closes import
handles, runs `extract` exactly once rooted at P1 and existing single-case `catalog` validation.
Other decoder objects do not grant availability. Create canonical case capsule from selected
producer descriptor/run/CN/context/membership/roots + ordered typed JSONL. No DuckDB process at P.
Reuse P has no native import/extraction. Retain exact OLD capsule on reuse.

Transfer32MiB/record4MiB/packed16MiB/100000bundleobjects, extracted10000unique objects, builtin64/
16arguments/16positions and artifact32MiB+1MiBlogs unchanged. Shapes are bounded small fixtures,
not a proof of actual final bytes/object union yet: focused controls and readiness must measure
control fixture/guard calculations; actual story hard-admits every case/union and stops on overflow.
Native source/binary/entity/diagram/URI/lifetime/API unchanged.

## 4. New index and controller grouping conventions

NEW ordinary STRING-role-rooted DAG profiles, separate from every old same-run index:

| Role | Proposed fields besides role |
| --- | --- |
| per-exercise-batch-run-v1 | occurrence STRING, requested BYTES(canonical three specs), profile STRING |
| per-exercise-batch-index-v1 | case-001/002/003 SUBDAG entry links, introduced incrementally |
| per-exercise-batch-entry-v1 | requested BYTES, request BYTES(QID), terminal BYTES(TID), outcome BYTES(OID), E-key STRING, E-artifact STRING(hash), fresh BOOL, producer-description SUBDAG, producer-run SUBDAG, target BYTES(CNID), producer-publication BYTES(P1ID) |
| per-exercise-controller-batch-v1 | occurrence STRING, cases SUBDAG(grouping ledger), evidence-publication BYTES, evidence-artifact BYTES(manifest), materialization BYTES(identity/manifest), state STRING(complete) |
| per-exercise-controller-case-v1 | requested BYTES, E/P/C-Q SUBDAG, E/P/C-T SUBDAG, E/P/C-O SUBDAG, fresh BYTES(three flags) |

Native evidence generation gets its own empty parentless P0, then PN parents=(PN-1,selected CN).
Entry SubDAG links retain original producer context/observations/run; old description values stay
unchanged. CN retains both branch checkpoint tips and declared fixture. P1's full old publisher
history stays in its selected E bundle; BYTES P1 field not itself a native edge or retention guarantee.
Controller Q/T/O BYTE IDs similarly require external controller authority; evidence-only export
cannot be claimed standalone controller provenance. Missing controller evidence fails closed.

Controller batch role links real9Q/9selectedT/9O in its OWN store, captures bundle/pool references;
write `latest-batch` while preserving `latest-event` and every selection. Read expected main basis
and check/update SAME storage transaction. No self-ID cycle: batch ID not stored inside itself,
producer descriptions precede final batch commits; external immutable file manifest finalized first.
Cross-store/file publication not globally atomic; incomplete grouped work is not a passed batch.

Grouping gets its own reserved event occurrence (no fake Q/T). Seven grouping reservations therefore
add7 allocator events beyond63Q+33freshT; expected103 event reservations if no extra controls/reserves.
Actual initial+terminal attempt DAGs still share33 occurrences. Continuation reserves a second run.

New catalog verifies strict field/native types; full requested parameter/profile ↔ selected E
producer context/key/artifact; old occurrence markers match OLD descriptor, not current batch;
case roots/membership inside THIS CN; cumulative entries and ordered PN parents; correspondence
with exact native controller Q/T/O/satisfaction. No acceptance based on encoded IDs alone.

## 5. Capsule admission, canonical merge and pooled assembly

A capsule owns exact tables from SCHEMA, canonical JSONL ordering/strict row types/keys, complete
source object closure and case profile; parse duplicate JSON keys strictly. Admit immutable artifact
manifest/full file set/size/hash and exact request/producer/upstream dependencies via legacy validators.

For materialization, derive typed object identities from all three selected capsules, require all
same-key rows agree exactly, no omitted/missing typed targets. `KEYS` in schema supplies compound row
identity; duplicate same-key conflicting content errors, exact duplicate sharing allowed. Case roots
not merged globally: pooled roots table EMPTY; each query generates its exact three checkpoint roots/
positions independently. Union typed objects≤10000, exact case capsule membership rederived rather
than accepted from a summary. A physically present foreign object cannot satisfy a missing edge
in a case capsule; admission validates each capsule independently before the union.

Materialization key = domain-separated canonical ordered scenario/P-key/P-artifact list + schema/
materializer/runtime. Pool directory is owned direct-child content-addressed generation, finalized
manifest contains code/dependency/rows/file hashes/loader actual PID/command/exit. Known same inputs
rehash/revalidate all files; found-invalid error, no rebuild fallback. New inputs invoke ONLY pinned
DuckDB loader once, retaining SQL/diagnostics and true exit; persist closed read-only pool. Cap32MiB
for materialization data and bounded logs as for stage artifacts; no use of cached verdict as input.

This assembly happens once before C requests and even when all C will reuse; admission required
for selected group. R2/R4 reuse verified closed pool; R1/R3/R5/R6/R7 build it. Pool-build metadata
recorded in controller grouping, not a fourth generic E/P/C attempt or uncounted stage work.

## 6. Exact query confinement and assertion boundaries

Static source review of `shared_index.check.case_sql` + ALL `checks.sql` views:

- TEMP `available(kind,oid)` from case CN closure; object/edge/base table views filtered by typed
  source/owner membership. Edges preserve target IDs so missing records remain visible.
- TEMP roots regenerated from THIS context. Immutable pooled roots are not queried as case roots.
- Every derived semantic view uses these scoped base views or fixed VALUES constants; contextual
  faults consult scoped profiles/field_data and explicit case source/binding authority.
- Query uses scoped violations/contextual_faults only, READ_ONLY DB/no attachments/global scans,
  no prior expectation/verdict rows in SQL. No unscoped pool objects counting/joins.

C uses unchanged scoped query builder via declared payload; exact generated SQL/source admission
rejects unknown replacement query code rather than declaring arbitrary SQL confined. The proposed
C2 variant is an actual comment-byte change, not arbitrary extension of query dependencies.
Confinement controls must check generated ALL-table view coverage plus behavior in real small
CONTROL fixtures: foreign-case rows/order cannot change the verdict; OWN relevant changes can.

C records independent structured violations first. Outside SQL, positive requires zero violations;
negative requires ONLY owning map_get_value at exactly its bad-operation subject. Do not reuse
old `assert_expected` alone as exhaustive negative agreement: it checks owning subjects but does
not reject unrelated extra violations. New predicate wrapper enforces that stricter check without
changing old tests/SQL. SQL/tool/profile/admission errors are error outcomes, never semantic rejection.
C success0 means correct per-case agreement; C reuse records NEWQ→OLDT/O, zero SQL.

## 7. Finite validation, owners and explicit gates

After pre-edit acceptance ONLY:

1. Add proposed NEW12 files; static AST/whitespace/EOF checks; preserve baseline59 source inventory.
   ONE stdlib/Git-only snapshot preparation, actual byte/source/runtime receipts. Preparation failure
   retains partial/unsealed evidence, STOP for reviewed causal correction—no automatic retry.
2. Freeze focused control mapping/list/count BEFORE ONE new-file focus. Pure keys/types/foreign
   authority/merge/conflicts/pool tamper/state tests; small CONTROL native/schema/confinement fixture
   and owning-rule sensitivity as explicitly listed in the focus plan. No acceptance chain warm-up.
   Use declared cached tools/binding, no download/build. Meaningful failed control stops for causal
   plan; no repeat-until-green. Actual control/native/query processes separately inventoried.
3. Readiness source/package/pin/static query/fixture bounds/selector review before ONE story. Runtime
   story output MUST be absent. Actual available resources/loaded dependencies/caps checked, no native
   retired evidence replay/second full or baseline story. Qualified same-agent independent expressions.
4. ONE7round story63Q33T8E11P14C30reuse, freshE48positions;5poolload+14caseCLI;33stages+1continuation
   =53 known story actors. ONE controller-process continuation actually reserves new run and9NEWQ,
   imports no native E/P and invokes no stages/query/pool loaders. Current generation grouping still
   writes metadata. Adoption R1/R3/R4 only gives15slots, late outputs unselected; sibling E replacement
   preserves15/unrelated entries. Request/attempt before actor; parent waits stages/new controller,
   materializer waits loaders, C waits pinned one-case CLI. No deadline/timeout/skip/cap weakening.
5. SAME retained independent-expression audit from low-level public native reads, exact source/
   manifests/group indices/Q-T-O/satisfaction/old-new producer fields/counts/caps/PID exits/branch
   choices. Nonexecuting (no E/P/C/pool query), actual cached proof is historical assurance only.
6. ONE complete isolated collection on final substantive sources: previous229 + exactnew controls,
   actual XML/rawlogs/true exit; no maintained full-v/shared build/coverage/Valgrind/installed/CI.
   Preserve every old test/assertion. Source-fixing failures require bounded fresh gate decision,
   not silently running another story/full. Native19/VP001 untouched.
7. Preserve exact reports/source/proof hashes; retire OWN new original working/case trees only after
   known children waited/reaped/absent and custody certain. No database/lock copy/delete/global cleanup.
   Finish local design results and STOP; no commit/push/controller production promotion.

## Review request

Accept or revise this seven-item pre-edit plan, especially NEW index cross-store provenance,
case-isolated fixture/key identity, ALL-view query confinement, stricter negative agreement and
materialization admission without whole-pool dependency in C keys. This is the mandatory review
before implementation. No new source/snapshot/store/import/test/native/SQL stage activation has
occurred; GO is active but remains subject to gate acceptance. No additional user decision on
random sampling/per-rule slicing/native delta reads/full-suite adoption has been inferred.
