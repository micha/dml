# Iteration 22 conditional handoff: composed ordinary node calls

Status: **prepared for review; NOT implementation/delegation/publication GO**.
The user's “proceed” authorized preparing these documents after clarification, not a worker/source/
build/test/story/publication restart. Read ALL THREE [DESIGN](DESIGN.md), [EXAMPLE](EXAMPLE.md) and
this handoff. Exact engineering spellings remain refinable. Review first, then separate GO.

## 1. Bounded goal and recommended implementation surface

Compose actual separately recorded add and double funcs using the installed standard argument-map
NODE -> result NODE interface. Use the EXISTING normal-return loader, not a new scalar-extraction
primitive. Match double reuse by intent/full argument-MAP datum while preserving selected upstream
producer attempts separately from historical double execution provenance.

Recommend:

- NEW example-local logical add/double source and small public-API composition/request/reuse/reader
  helpers. One captured local binding per func; exact fixed names/types, pinned shipped getters,
  explicit Python sequencing. No generic dispatcher/registry/evaluator/scheduler.
- Public successful upstream S + installed return inspection BEFORE caller write, then existing
  `Recorder.load(S.result)`/`arguments({x: result})`. One atomic input+C publication preserves outer
  result source and selected S/T witness outside MAP values and unchanged strict arguments profile.
- NEW ordinary C/decision/summary conventions. A common helper can accept two explicit func contracts;
  no rewriting old sum-pair Dn/choice/SLOT or older datum reuse helpers. No library imports examples.
- One explicitly selected-double S, own public Q on every path, public ordinary W linking new Q to
  old T/R for TWO value hits. Present invalid S is error even on mismatch; pending miss followed by
  separate explicit fresh dispatch; no auto-adoption or hidden retries/history discovery.
- Pinned same-history reader validates actual composition/decision/Q/W and both requested/historical
  producer chains. It never rewrites old double's inputs/trace or counts reuse as fresh execution.

Candidate implementation paths: NEW files under `examples/` for logical sources and helper,
`tests/python/` for focused contract/identity/association/atomicity tests, explicit installed
controller/reader under a new `tests/` directory, and an informative owning `docs/` example document.
Use descriptive repository conventions; exact filenames are not approved. Current installed
builtin/local/exchange/transfer/native APIs appear sufficient and should preferably remain unchanged.
If a missing public seam is demonstrated, explain and seek coordinator review before that change;
private codecs/projection, new native entity/layout/opcode, mutable registry or runtime repair are
not assumed necessary. Do not add native arithmetic funcs or a second value codec.

## 2. Reading and preflight ONLY after review and GO

Machine instruction index/admin/mounted-work guidance first. Read design AGENTS/README/discussion
resume/glossary/ALL22 documents, implementation AGENTS and
[documentation guidelines](../../../dml/docs/documentation-guidelines.md). Consult these authorities:

- [Internal builtins](../../../dml/docs/internal-builtins.md),
  [builtin.py](../../../dml/python/daggerml/daggerml/builtin.py) (arguments/load/returned/Inspector/
  publish_callable), [Python API](../../../dml/docs/spec-next/python-api.md),
  [objects](../../../dml/docs/spec-next/objects.md).
- [Successful S](../../../dml/docs/versioned-reuse-selection.md),
  [reuse_selection.py](../../../dml/examples/reuse_selection.py) PUBLIC select/inspect,
  [current sum-pair bridge](../../../dml/examples/builtin_workflow.py). Old exact-binding
  reuse_selected delegation is not a valid shortcut for new value-matching/different full inputs.
- [Caller Q](../../../dml/docs/spec-next/caller-requests.md),
  [local](../../../dml/docs/spec-next/local-execution.md),
  [exchange](../../../dml/docs/spec-next/repository-execution.md),
  [transfer](../../../dml/docs/spec-next/transfer.md),
  [prior installed evidence method](../../../dml/tests/builtins/README.md).
- [Iteration21 review](../21-internal-builtins/REVIEW.md)/
  [results](../21-internal-builtins/RESULTS.md): original versus final comparator provenance remains
  qualified. Its completed installed story is not evidence of this NEW composition workflow.
- [Owning validation policy](../../../dml/docs/validation-policy.md),
  [GHA disabled decision](../19-intent-scoped-reuse/GHA-DISABLED.md),
  [VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md).

Preparation verified DML clean at `a523b0bfc8c4cc9f96a36b7b62138d9645b3eab3`, no implementation
changes/build/test/run. Design contains preserved accumulated uncommitted earlier notes; do not
stage or rewrite them as part of implementation. Reinspect actual HEAD/index/changed-surface source
and relevant tools AFTER GO, not an automatic full baseline or whole-repo inventory.

Only if separately delegated: existing window2 worker in a verified NEW Pi session. Coordinator
explicitly transfers BOTH `build/check`, `build/coverage` and source to worker until targeted changed-
surface/HEAD freeze and release. Worker owns implementation/tests/docs/owned story/RESULTS;
coordinator REVIEW/coordination/status. No additional worker/model/global configuration change.

## 3. Pre-edit change-validation map and meaningful invariants

Record a concise map before edits. Focus on NEW composition behavior, not repeated inherited rituals.

### Node/value and contract identity

- `put_datum` datum ID versus native literal node ID versus semantic ValueNode/DAG distinction.
  New arguments support existing returned nodes through load; bare datum/native storage description,
  fabricated/foreign/ended handle is not equivalent. Reload changes temporary handle only.
- Add exact `a,b`/double exact `x`, typed I64/no bool/float/coercion, canonical map entry-order
  independence and value-swap difference. Compare full MAP datum, not full source identity, inner
  scalar alone, arithmetic commutativity or native Q/result IDs.
- Every successful add/double getter routes through the installed bound URI call interface with
  own standard argument node. No hand-authored trace or unrecorded accessor path. No new primitive
  Q/T or arithmetic operation schema. Copied Datum contains child IDs, not implicit provenance.
- Existing16argument/16position/64reached-semantic-DAG caps retained; loaded producer includes
  original argument/trace closure. Explicit chain fits without silently raising bounds. Native
  complete all-parent/composite transfer closure has its own bounds. Prospective checks before puts.

### Producer authority and composition witness

- Public S proves exact successful recorded Q/T/R/F; return inspector proves explicit returned/value/
  trace/Q/input profile. Require BOTH before using a computed source; structural valid R/provisional
  publication alone cannot supply historical success. No arbitrary-root extraction.
- Exact selected upstream slot/S/result matches C's actual basis and I.x source; C links S and outer
  R, not equal-valued unrelated R/inner literal/forged dataclass fields. Same-value WRONG producer
  should fail even when downstream reuse key would match. Capture T via S; Q/R alone does not identify
  every possible attempt. Durable witness remains coherent after convenience-ref/slot movement.
- Native input+C/tree/commit/ref publication is atomic and changes only intended entries. Public
  validation scratch/handles close BEFORE write; no nested same-store public S/export while write
  is live. Recorder errors poison completion under existing semantics. No native pointers escape.
- C is separate ordinary provenance outside MAP datum and unchanged arguments/Q role. Reader reports
  Q inputs PLUS its captured decision/C basis, not false claim that the argument-map value contains T.

### Decisions, own Q/W and reader

- Actual requested binding/func/inputs/C and one known downstream S validated; selected original
  double decision/C/upstream-S chain checked. Malformed/nonmatching entry still errors, no fallback.
- New decision one-parent/intended tree delta, actual Cq parent equals THIS decision, own non-None Q/
  exact binding-input-intent/ref/reservation/tree. Coherent alternate SAME-name C/decision and forged
  response claims fail BEFORE W, not accepted by a later permissive reread.
- Reuse W adds only satisfaction for new Q with old T/R; old T owns original producing Q. Two hits
  create no attempt/getter/completion. New upstream source never mutates historical double inputs.
- Valid absence/value miss leaves pending Q before explicit dispatch. Fresh86 leaves selected84
  unchanged; no implicit adoption. Explicit upstream fresh repeat is distinct Q/T despite same key.
- Pinned readers preserve both new requested source chain and old executed source chain, complete
  anonymous/composite/all-parent native bytes and exact ordered parents. Reads execute no captured
  arithmetic code or recording dispatcher and write no DML records/refs.

Representative NEW fault gates: late create-ref conflict, real map-full or consuming-commit fault in
input+C publication after genuinely ABSENT new rows were inserted; source/S/return validation errors
before publication; own-Q alternate-parent rejection before W; W late failure retaining legitimate
pending Q. One author-only pre/post-store acknowledgement-loss boundary if useful. Predict actual
new node/DAG/tree/commit IDs before checking absence; equal-content dedup must not make rollback
oracles vacuous. Native write, decision, Q, W, scratch files and local child remain separate boundaries.
Do not rerun all unchanged selection/exchange fault matrices or add acceptance failure jobs.

Useful finite private mutations: swap I.x's outer result for same-value wrong producer; mismatch
C.slot/S/result with otherwise coherent native objects; strip C/trace owner validation; match full
input identity instead of MAP value; normalize swapped operands; claim current producer as old
executed producer; trust returned Q parent instead of actual parent. Preserve measured private source
BEFORE run; verify predicted failure rather than import/name/ref collision. No shipped hooks,
threshold/skip/exclusion/runtime deadline change. Narrow no-value exclusions need exact rationale;
difficult meaningful failures still need tests.

## 4. One installed story and same-history review

After GO use a fresh bounded isolated local installation from actual current source and cached
project tools. Example helpers remain explicitly captured/copied local helpers, not claimed shipped
DML APIs. Parent/child use installed DML without checkout runtime PYTHONPATH; unset PYTHONPATH and
PYTHONHOME and record actual native/module/CLI/interpreter/helper/captured source identities before
launch. Do not mutate old installed prefixes, private19 candidate or retained evidence. Missing
installations/downloads require a separate scoped decision; no global tooling/image/service changes.

Run ONE [EXAMPLE](EXAMPLE.md) story: EIGHT Q/SIX synchronous LOCAL attempts, FOUR adds/TWO doubles,
TEN successful child map-get positions. Results42/84, fresh42/reuse84, swapped42/reuse84, changed43/86.
ZERO support Q/T, no extra getter/construction/compatibility jobs. Ordinary map preparation is
bootstrap, not builtin invocation. Count trace positions separately from deduplicated content IDs.

Use existing synchronous exchange execute then completion observation/import AFTER direct child
wait/reaping, not an additional async supervisor or live-progress fixture. Metadata phases block
spawn/transport; allow only SIX expected direct children at explicit dispatch boundaries. Retain
incremental request/PID/wait/outcome/native IDs before later assertions. Failure/uncertain custody
means STOP and scoped triage, never relaunch/timeout bump/retry-until-green. No extra computation
solely to make a reader pass or replace missing original evidence.

After all six children are known reaped, make only owned original source/workspace/packet/expected
paths unavailable, keep inert evidence, transfer SAME pinned complete history. Fresh blocker-FIRST
readers load installed runtime/captured helpers, public S/Q authority and semantic inspector to check
8Q6T/10positions/keys/all requested-versus-executed chains/immutable bytes. Exact stdlib URI parsing
may be allowed; transport/spawn remain blocked with actual negative controls. Coordinator independently
reads SAME stopped evidence; no second story or installed compute. Correct nonexecuting reader errors
on SAME history first, retaining original source/hash/errors and source-version qualifications.

## 5. Final validation, documentation, review and conditional publication

Follow owning validation policy: focused behavior and installed concrete acceptance primary; ONE
final unchanged worker full `scripts/check.sh -v` on final relevant sources after future GO. No
automatic pre-edit full baseline/second full/story/whole-source census; repetitions require reviewed
assurance benefit. Freeze exact changed paths/HEAD/diff/relevant sources before releasing BOTH builds
for risk-based coordinator validation/SAME-history nonexecuting review. Preserve raw failures and
uncertainty; a pass on changed source is not proof the original version passed.

Add an informative owning composition example document; reference installed builtin/return/local/Q/S
contracts instead of duplicating or claiming new native semantics. Review actual
[diagram claims](../../../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance):
ordinary C/decision/summary roles are not new LMDB entities. Change diagram/glossary/spec only if
necessary within a later authorized implementation, never to depict this candidate as as-built.
Old sum-pair and datum helper contracts remain unchanged. No proposed native graph layout.

Development GHA remains disabled/NOT RUN, not pass or fresh platform all-green. No workflow enable/
run/budget/runner/release-control/repository-setting edits. Native19 PAUSED/private candidate
incomplete-unexecuted retained; no compile/actor/native repair/probe. VP-001 OPEN UNKNOWN with existing
owner/revisit conditions/no standing waiver; this turn presumes unchanged synchronous execution.
Any related recurrence or required async/LMDB/open/lifetime change needs fresh scoped triage before
acceptance. Historical raw failures/cancellations/possible-lost memory/source qualifications remain.

ONLY following separate GO/publication permission and independent acceptance: exact staged-path/
secret/whitespace audit including new files, focused worker commit/NORMAL existing remote push, exact
accepted-current-committed/parent/clean source-index/live remote identity and read-only workflow-state
verification. No force/tag/release/package/design checkpoint publication. Final RESULTS distinguishes
worker/focused/full/installed/independent evidence, faults/exclusions/source qualifications and known
owned custody; explicit STOP ALL/BOTH source-builds returned. No later turn or investigation restart.

This conditional handoff starts NOTHING. Candidate review precedes separate implementation GO;
completed21 and paused19 permissions are not inherited.
