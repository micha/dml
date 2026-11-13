# Incremental testing prototype — results and STOP

Status: **bounded isolated prototype ACCEPTED and COMPLETE; STOPPED**. User reviewed/GO'd the
[design](INCREMENTAL-DESIGN.md)/[example](INCREMENTAL-EXAMPLE.md)/[handoff](INCREMENTAL-HANDOFF.md),
accepted [pre-edit](INCREMENTAL-PRE-EDIT.md), then approved the causal correction and delegated
bounded coordinator decisions by **“yes, you are in charge now”**. No publication/integration GO.
See [coordination](INCREMENTAL-COORDINATION.md) and [readiness](INCREMENTAL-READINESS.md).

## What exists now

Twelve NEW files in isolated `../dml-relational-spike/spikes/relational_invariants/incremental/`:
fixed sequential Python controller, strict dependency keys, immutable artifact manifests,
public low-level ordinary DAG request/attempt/outcome/satisfaction/selection/allocator conventions,
fixed E/P/C process wrappers, snapshot preparation,49 controls and owning README. No old helper/
role reinterpretation, native entity/API/C/storage/URI/async change, private role codec or generic
scheduler/evaluator/backend registry/cache discovery. No main/Iteration25/shared-build use.

Selected functions use real shipped map/get at two checkpoints, not HOST ordinary LOCAL jobs.
Trusted recorder is the pinned base Python/core snapshot; candidate A/B are explicit copies.
Candidate B and P2/C2 change actual owned source COMMENT bytes to demonstrate conservative
whole-build/code invalidation despite equal behavior. This is not a candidate semantic-fix test.

Persistent selectors/artifacts satisfy NEW requests with OLD actual stage attempts. Each request
opens native storage/read scopes; no in-memory success cache. Cross-process controller continuation
is supported structurally by persisted refs/artifacts but NOT separately activated as another
acceptance round/CLI resume. Caller supplies actual store namespace; cross-store/distributed global
occurrence uniqueness is not supplied. CONTROL fixtures repeat deterministic descriptive labels
across separate focused/final test collections; they are NOT fresh real E/P/C occurrence evidence.

## Actual evidence — do not merge these gates

| Gate | Actual result | Scope |
| --- | --- | --- |
| FIRST preparation v1 | **RAW TRUEexit1**, no pins.json/XML/native import | Path-component vs relative-string canonical order defect; [original failure](INCREMENTAL-PREPARATION-FAILURE.md) preserved |
| Draft preservation |12 byte-exact files + inventory archived BEFORE fix | `incremental-v1/failed-source/`; original partial snapshots/raw logs intact |
| Corrected preparation v2 | **TRUEexit0**,782 exact assets + pin receipt | Stdlib/Git copies/hash/read-only closure query, no compilation/stage/native import |
| ONE focused gate | **49PASS,0.79s,TRUEexit0**, actual XML | Pure keys/admission + tiny CONTROL native records/ONE portable42 seed, ZERO E/P/C/CLI/actor/network |
| Sole seven-round story | **TRUEexit0**,21 Q/15 actual T/6 reuse | Actual4E5P6C,15 foreground stage processes +23 sequential DuckDB CLI children |
| SAME independent-expression audit | **853checks,TRUEexit0** | Public native reader, no controller/stage validators/replay/SQL; same agent, not another independent worker |
| ONE CONTROL C sensitivity | Stage/CLI0; outer owning assertion **RAW TRUEexit1 EXPECTED** | Removed ONLY map_get_value rule; required counterexample vanishes, no adoption, ZERO E/P rerun |
| ONE final complete isolated collection | **169PASS,103.68s,TRUEexit0**, actual XML |120 original spike cases +49 new controls, assertions unchanged; NOT maintained full/coverage/platform gate |
| Final source/XML/process audit | Exact runtime/pins,169 actual XML/no failures/errors/skips;42 known actors waited/absent | Separate stdlib expression/receipts, ownership retirement; no fresh stage/SQL |

No warnings were reported in the two new pytest logs. Older reports' warnings/failures/HOST/
partial-assertion/single-trial qualifications stay historical and intact. Do not infer all-suite
speedup/five-minute success or complete old-validator equivalence from103.68s isolated collection.

## Actual reuse/invalidation behavior

| Round | Actual fresh E/P/C | Observed authority |
| --- | --- | --- |
|1 A/P1/C1 |1/1/1 | Explicitly adopted verified results |
|2 unchanged |0/0/0 | THREE NEW Q, exact OLD attempts/artifacts, no new T/actor |
|3 checker C2 byte change |0/0/1 | OLD E/P retained; fresh C |
|4 projection P2 byte change |0/1/1 | OLD E retained; fresh P/C |
|5 candidate B byte change |1/1/1 | Different E key even with exact SAME native roots42; downstream fresh |
|6 explicit fresh B |1/1/1 | Same E computational key, distinct actual E occurrence/artifact; no automatic selection move |
|7 real native wrong-result43 |1/1/1 | C terminal rejected, exact map_get_value subject, no positive selection |

Round6 E explicitly adopted ONLY on sibling `fresh-E-choice`; main retains round5 E and all other
selectors unchanged. Independent native history census:21 request events/30 initial+terminal
attempt descriptions describing15 actual occurrences/6 satisfaction events. Allocator next-run1/
next-event36; no branch reset. Every reuse satisfaction links THIS Q to exact OLD T/O; no attempt
owned by reused Q. All artifact file sets/digests and requested keys/transitive dependencies verified.
Equal datum/native-root content did not erase the actual producing stage occurrence.

Exact wrong operation subject `e6d344b83d0ba7b29c0ad529c52e164e`; original C rejects it. CONTROL
owning-rule-disabled C falsely accepts SAME negative P; outer required-counterexample assertion
fails with actual1 as intended. This deliberate false pass is rejected as assurance, NOT silently
called a normal passing C. CONTROL namespace/key differs and no selector adopted; retained native
controller history was publicly exported/imported, not database/lock copying or E/P rerun.

## Provenance and actual limitations

Frozen controller namespace:
`244c4b3d3110b2d022a794ff840a705e932a1bbc24d7f3025dbd5e48e2a5a447`.
Current six runtime bytes equal tested/frozen code. Assets are source/package/native/runtime pins,
not a fresh installed distribution or reproducible native build. Known historical build logs and
as-built core bytes qualified separately. Core's mutable RUNPATH prefix was NOT patched; minimal
pinned glibc/GCC environment and actual parent/core/library receipts used. CLI binary/environment
pinned, not post-exit child-library-map capture. Trusted integration, not security/full capture.

Conservative E key includes all tracked candidate source/build input bytes and native/runtime;
P includes selected E key+artifact+decoder/normalizer/context; C includes selected P key+artifact+
checker/rules/context. Candidate/normalizer/checker source changes cannot be skipped on expected
output equality. Fine-grained dependency slicing and property-case/seed caching remain OPEN.
Random sampled refresh explicitly DEFERRED/unimplemented. Coverage counters not gathered/reused
as fresh coverage. No maintained thresholds/assertions/exclusions/deadlines/budgets changed.

Public decoder/native foundation still shared; SQL rules intentionally partial. Scope covers the
selected map/get structural/value/source/position claims and controller reuse/publication, not
scientific truth, every native hash/name/URI/budget edge, all roles, LOCAL/SSH/Batch custody or
full-suite equivalence. Full isolated old paired cases remain HOST/partial-assertion, not real
child proof. Native19/VP-001 not diagnosed/fixed or waived; GHA remains disabled/NOT RUN/not pass.

Latent diagnostic limitation documented at readiness remains: an E/P activation error can report
missing payload FileNotFoundError after retaining terminal error/raw logs rather than final generic
RuntimeError. Stop/no adoption holds; actor error route NOT tested here. No speculative repair or
extra source preparation after successful concrete story. Selected artifacts are checked by digest/
owned-file convention, not tamper-proof against the owner. Cross-system crash durability is not
proved. These constraints block promotion as general production test tooling without another plan.

## Exact evidence and ownership disposition

Owned ignored directory `../dml-relational-spike/build/relational-spike/incremental-v2/`:
`prepare.*`, `focus.*`, `pins/`, `readiness.json`, `story.*`, `story/`, independently expressed
`audit_story.py`/`story-audit.*`, `sensitivity.py`/`sensitivity.*`, `sensitivity/`, `final.*`,
`retirement.json`, `final-audit.json`. Sensitivity shell envelope returned0 to continue inspection,
NOT an assertion pass: actual child RAW1 stored in sensitivity.exit/report, stderr empty and result
proves planned owning-rule failure. No swallowed unknown error represented as successful sensitivity.

Selected proof SHA256s:

- pins receipt `43864408af7133e197b5b7102530f978a7af41eec95aca8d660c16f8775643b6`;
- focused XML `77b055c75d4e3dce2809a15a86d4a48fbd7ae08d75383c3ef78d940a52a4c6db`;
- final XML `38a6af8733d6932efd5e0ce2f57abf0c982fa11bc48d2f9af55dee36b6680702`;
- story result `810b673efd2d359765d502c667ae105dcb817a74f5d42af1c3171d5cf1bfed0c`;
- SAME audit `3159211d3cec67a7ce5de5af1f0080b206191f13442c730cc2d889c2242ad7b9`.

42 explicitly inventoried stage/CLI children (38 story +4 sensitivity) have retained actual waited
exits and are absent. Original suite standalone checker child PID not separately inventoried;
its unchanged subprocess.run/check=True assertion passed, not a fabricated independent PID receipt.
Nine E/P native working directories identity-retired by rename with exact every-file hash equality;
focus/final OWN case trees renamed intact. Portable evidence/controller stores/closed analytical
artifacts retained; no database/lock copying/deletion or external fixtures/services. Working path
strings/old test paths remain historical after retirement, never automatic resume instructions.

## Acceptance and next boundary

Coordinator **ACCEPTS bounded isolated prototype**, with above qualifications, and explicitly
**STOPS ALL activity** after final documentation/source/link checks. Worktree base remains LOCAL
`15555c01e4db19a20b4de7049f776c4d995bd5e0`; ALL spike code/docs UNCOMMITTED, ignored evidence retained.
No commit/push, main integration, controller build promotion, maintained full gate/GHA/CI/dependency/
service/cloud/image/native19 work. Existing Iteration25 source/BOTH shared builds remain untouched
and separately worker-owned. New review/planning needed before any further run/reader/engineering;
completed GO/delegation not a standing restart or publication permission.

Possible later decisions (assistant suggestions, NOT selected): fresh-process continuation proof,
precise exercise dependency slicing, next existing test-family assertion map, controller pin/bootstrap
hardening and error-path diagnostic regression. No automatic second story/full or random auditing.
