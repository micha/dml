# Shared exercise repository / indexed contexts — results

Status: **COMPLETE, bounded slice ACCEPTED, STOPPED; isolated/uncommitted**. User explicitly
requested implementation after agreeing empty P0, publication-first parents and indexed context
DAGs. See [plan](SHARED-INDEX-PLAN.md), [corrections](SHARED-INDEX-CORRECTION.md) and
[readiness](SHARED-INDEX-READINESS.md). No main/Iteration25/shared-build/API/build/install/CI/
publication scope. Prior incremental prototype code/evidence remains unchanged/stopped.

## Implemented

NEW7 files under `../dml-relational-spike/spikes/relational_invariants/shared_index/`:
`__init__.py`, `exercise.py`, `project.py`, `check.py`, `run.py`, `test_shared.py`, `README.md`.

- ONE exercise repository per batch; no mutable exercise/publication refs.
- Parentless P0 contains empty index and immutable run declaration. Common fixture F is separate.
- Four fresh native builtin exercises, each two checkpoints branching from F; CN retains BOTH tips.
- PN parents exactly `(PN-1,CN)`. First-parent history follows publication, all-parent closure
  retains exercises/forks. Old index snapshots keep old descriptors unchanged.
- Each index entry links description DAG: label, distinct actual occurrence, target/root IDs,
  context and observations. CN/checkpoints also link THIS context and occurrence marker.
- Context/observations stored in native ordinary DAGs, including literal BYTES canonical JSON
  for structured parameters/captures/limits/expectations/returns/errors. Not external authoritative
  per-case sidecars/new native schema. Commit-ID LIST/BYTES interpreted explicitly as roots.
- Index/data-role projection from ONE generic extraction; no extra per-case repository reads.
- One shared derived DuckDB pool with per-case READ_ONLY/TEMP availability. Expected outcomes are
  outer assertions, never archived verdicts fed into invariant predicates. Bad graph stays case-local.

This is additive exerciser/normalizer/checker profile, NOT conversion of the completed incremental
controller's old four-E/five-P layout. No generic evaluator/controller promotion/full-suite migration.
Hybrid isolated destructive/storage fault foundations remain separate. Native diagram unchanged:
all new roles are ordinary DAG conventions, no new LMDB entities/layout/API.

## Actual validation

| Evidence | Actual result / qualification |
| --- | --- |
| Initial focus | **RAW1:23pass1fail,0.84s**,24 actual cases; manual static26 count corrected BEFORE run |
| Source preservation | Original7 archived exact; then revised checker/test pair archived before UNIT harness repair |
| First UNIT transport control | **RAW1:1fail,0.10s**; overescaped newly added fake regex, no E/SQL |
| Repaired UNIT | **1pass,0.07s,TRUEexit0**; no E/SQL |
| SAME retained four-case query gate | **TRUEexit0**, outcomes accept/accept/reject/accept; pool unchanged; ZERO E/native reads/normalization repeat |
| ONE standalone demo | **TRUEexit0**,4 cases/24 actual getter positions, ONE exercise repo; complete export/fresh validation import/no refs |
| ONE final complete isolated collection | **194PASS,108.33s,TRUEexit0**, actual XML;169 existing+25new cases, no assertion removal |
| SAME separate-expression review | **102checks0**, public native/receipt/XML reader, no catalog/checker facade or fresh E/SQL; same agent, not another worker |

Initial failure: warning-prefixed JSON stdout from unchanged SQL's deprecated lambda syntax.
Strict parser refused mixed diagnostics/data. Owning new transport fixed via COPY ordered query
rows to NDJSON file, with actual stdout/stderr/owner/exit retained separately; no warning suppression
or old predicate edits. UNIT repair only corrects regex/literal escape. Initial full CLI stdout/PID
not separately captured; traceback/known returncode0/source flow retained, not reconstructed-as-raw.
Warnings persist in corrected query logs. Raw failures remain failed despite final passes.

Final collection includes all old native/HOST/partial-map/concurrency qualifications unchanged;
NOT maintained full gate, installed/matrix/coverage100/Valgrind/codec/scientific/security proof.
No speedup/five-minute claim from1m48s isolated tests; no thresholds/deadlines/skips/exclusions changed.

## Demonstration facts

Cases: normal42, equal42 fresh, native-valid substituted43 negative, normal43. Final verdicts
**accept, accept, reject, accept**. Exactly24 actual getter returns; repeated equal computation
shares immutable native context/operation/trace content but distinct occurrences/CN targets.
Native wrong-result subject `e6d344b83d0ba7b29c0ad529c52e164e` is rejected only in its case.

Final publication `ae5c18d70a2ac9cc64b29dfa65533782`. Five publications P0–P4, first-parent chain
matches immutable external handles. Final-P4 export contains **275 typed objects /49,391 bytes**;
public import into separate OWN validation repository without ref retains every descriptor,
context/target/fork. Validation destination is not a second exercise repository. No DB/lock copies.

Generic extraction reads **275 unique typed objects** once; total per-case memberships **475**.
These are actual different scopes (publication/catalog overhead versus case closures), NOT an
old-validator read-count/equivalent-work speedup comparison. Case scopes derive from CN, not all
P4 ancestors. Older pinned P0/P1/P2 see0/1/2 cases despite future physically present objects.
Malformed context/role/root/limits/occurrence/parent order/lost prefix, cross-case availability,
missing-root error evidence and before-commit rollback controls preserve explicit rejection.

## Evidence, provenance and custody

Owned ignored `../dml-relational-spike/build/relational-spike/shared-index-v1/` contains focus/
transport failure and repaired logs/XML/exits, archived source, SAME queries/logs/results, demo
native/portable/projected/check artifacts, final194 XML/log/exit, audit.json and disposition.json.
Core/package is existing as-built base15555c0, captured executable/source/runtime descriptions,
not fresh installed/reproducible build or complete environment capture. Context includes declared
captures/limits; unknown arbitrary runtime effects/security isolation not promised.

Twelve new recorded REAL case-checker CLI PIDs (SAME4 +demo4 +final4) waited0 and absent. Two fake
UNIT owner files PID999991 explicitly excluded from actual actor inventory. Initial failed checker
and pool loaders/old suite child PIDs not individually retained; Popen.communicate/subprocess.run
waited-source flow and actual gate exits reviewed, not fabricated universal PID receipts. No
external fixtures/services/remote/cloud/image changes. Demo exercise/validation original directories
and owned test case trees renamed intact/identity-retired; portable bundle/data/native evidence
retained. Embedded handle/path strings now historical; no automatic resume from old paths.

## Remaining boundary

Schema/profile fixed to builtin map/get family; generic extractor remains reusable, new semantic
families need explicit context/check profiles. Committed publication handle external acknowledgement
is not filesystem/storage crash-atomic; no global namespace allocator/ref discovery. Same declared
namespace reused across separate stores can duplicate descriptive identities: caller responsibility,
not distributed/global occurrence uniqueness. Native projection is not an independent packed codec.
Data-field IDs are not native edges; parent retention is checked, not implicit BYTES traversal.

Coordinator accepts bounded requested implementation and **STOPS ALL** after final docs/source/link
checks. ALL spike code/docs remain UNCOMMITTED at tracked-clean15555c0; no commit/push/main integration
or promotion. Active Iteration25/source/BOTH shared builds untouched; development GHA disabled/notrun,
native19 PAUSED/private candidate retained/VP001 OPEN UNKNOWN/same owner/conditions/no waiver.
Further runs, case families, controller wiring, tooling/production/native work require new scope.
