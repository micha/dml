# Iteration 21 conditional handoff: internal versioned built-ins

Status: **bounded handoff reviewed; NOT implementation/delegation/publication GO**.
The user subsequently stated “reviewed”; this records bounded plan review only, not as-built
behavior or permission to start. Exact engineering spellings remain refinable. Earlier preparation:
The user authorized preparation, not source edits/worker restart/build/install/run/publication.
Read ALL THREE [DESIGN](DESIGN.md), [EXAMPLE](EXAMPLE.md) and this handoff before review. User-agreed
calling/binding direction and assistant-origin engineering mechanics are distinguished in DESIGN.
Exact spellings and acceptance counts remain refinable. Review first, then separate GO.

## 1. Bounded goal and recommended engineering surface

Implement actual installed internal built-in funcs, not just example aliases:

- Common DML call contract: argument-map NODE in, result NODE out. Argument preparation retains
  source relationships separately from MAP datum pairs; no bare-Datum shortcut or provenance API.
- Fixed URI funcs map/empty, map/insert, map/get, list/get, with NULL adapter/interpreter/timeout and
  exact versioned source URI. Real map/get-v1 and v2 shipped together, distinct handlers/entrypoints,
  same semantics; pinned old binding still executes after explicit choice-v2 promotion.
- New additive installed module, illustratively `daggerml.builtin`, using public native repository/
  canonical datums and strict ordinary DAG profiles. Python fixed handlers are the first candidate;
  not an external plugin/process/download/source evaluator or new native opcode schema.
- Native URI prerequisite: current src/uri.c rejects ALL dml: URIs. Permit storing/referencing them
  through the existing canonical pipeline; preserve all other URI grammar/canonical/allocation/error
  rules and native encoding/hash/schema. Reserve executable definitions via exact closed dispatch,
  not by prohibiting reference datums. Unknown valid URIs can persist; unsupported execution rejects.
  Add ONLY the corresponding reserved-intent guard to local/exchange external request validation,
  so a Python binding cannot newly claim a dml: builtin intent. Reject BEFORE Q/dispatch; preserve
  old binding fields and all process/attempt/publication/observation behavior.
- Value-oriented recorder-owned semantic node handles, standard argument preparation, actual nested
  map/list result nodes and normal result-sub-DAG node with explicit returned-value/trace authority.
- Small example-local choice/request/reuse/pinned reader bridge using public S and exact Q/W. ONE
  named selection is enough for this story; do not duplicate generic tables/lifecycle/cache policies.
  Old20/earlier profiles and local/exchange/transfer semantics remain unchanged.

Candidate implementation paths: new `python/daggerml/daggerml/builtin.py` (a small owning support file
is acceptable if justified), additive Meson runtime installation, src/uri.c's one reserved-scheme
rule/unused helper and owning C/Python URI tests; narrow local.py/exchange.py external dml:-intent
reservation guards and tests; NEW example funcs/wrapper/choice/reuse helper,
focused tests/explicit installed controller/offline reader, owning as-built builtin docs and URI
rule update. Follow existing source locations/conventions; these are not an approved exact pathset.
No public mutable registry/framework, legacy helper rewrite, core handle/LMDB/open/async repair,
vendored change, native new node kinds/ABI, generic evaluator/scheduler/resource/cache feature.

## 2. Reading and preflight AFTER review and GO

Machine index FIRST/mounted admin instructions; design AGENTS/README/discussion current/resume/
shared glossary/ALL21 documents; implementation AGENTS and
[documentation guidelines](../../../dml/docs/documentation-guidelines.md).
Read DESIGN's source/authority links and current actual tests, particularly:

- [URI implementation](../../../dml/src/uri.c), [C record tests](../../../dml/tests/c/test_record.c),
  [URI failure tests](../../../dml/tests/c/test_faults.c),
  [record property tests](../../../dml/tests/python/test_records_hypothesis.py),
  [public Python tests](../../../dml/tests/python/test_python_api.py).
- [Objects](../../../dml/docs/spec-next/objects.md),
  [records](../../../dml/docs/spec-next/records.md),
  [Python API](../../../dml/docs/spec-next/python-api.md),
  [local](../../../dml/docs/spec-next/local-execution.md),
  [caller requests](../../../dml/docs/spec-next/caller-requests.md),
  [exchange](../../../dml/docs/spec-next/repository-execution.md),
  [transfer](../../../dml/docs/spec-next/transfer.md),
  [successful S](../../../dml/docs/versioned-reuse-selection.md).
- [Iteration20 owner](../../../dml/docs/recorded-argument-maps.md),
  [review](../20-recorded-argument-maps/REVIEW.md),
  [new-profile controls](../../../dml/tests/python/test_recorded_maps.py),
  [own-Q controls](../../../dml/tests/python/test_datum_reuse.py),
  [atomicity](../../../dml/tests/python/test_recorded_map_atomicity.py).
- [Owning validation policy](../../../dml/docs/validation-policy.md),
  [development GHA disable decision](../19-intent-scoped-reuse/GHA-DISABLED.md),
  [VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md).

Preparation verifies DML HEAD `7e9bf133d5d175a492fb1e9d651e91a476358604`, clean. No builtins/new URI
behavior exists yet; prior installed20 checks do not prove the proposed surface. Reinspect live
source/index/HEAD/relevant artifact provenance AFTER GO, not an automatic full baseline/inventory.
Preserve private19 native candidate/harness/evidence, incomplete and UNEXECUTED; investigation remains
PAUSED. Do not finish/delete/compile/run it. GHA remains disabled, VP-001 OPEN UNKNOWN/no waiver.

ONLY if separately delegated by GO: existing window2 agent in verified NEW Pi session; explicitly
hand BOTH shared builds/source to worker. Worker owns implementation/tests/docs/owned story/RESULTS;
coordinator owns REVIEW/coordination/design status. Worker exclusively owns build/check and coverage
until changed-surface+HEAD freeze/explicit release; no concurrent edits/wipes or extra workers.

## 3. Concise pre-edit invariant -> validation map

Record this before edits; select assurance by changed behavior, not inherited ritual matrices.

### URI and binding gate

- Canonical dml: refs survive native put/read/packed validation/transfer/CLI; uppercase scheme/host
  normalization, escapes and canonical-input rejection follow existing rules. Arbitrary canonical
  unknown refs are data, not execution authority. Keep relative/non-ASCII/NUL/invalid syntax/packed
  noncanonical errors and meaningful allocation/parser/normalization failure paths.
- Exact role/root/field sets/types/NULL fields/source namespace/version/func pairing validate.
  Source BYTES, STRING masquerading as URI, NULL source, omitted/extra fields, wrong adapter/interpreter/
  timeout and local-Python role reject. An external Python request under dml: rejects before Q or
  dispatch, while references in unrelated value graphs still roundtrip. No URI fetch, import-by-URI,
  fallback or mutation of registry.
- Distinct v1/v2 routing needs meaningful controls even when output values agree. Test-private
  per-version sentinel/interception controls can prove target entrypoint selection; a mutant routing
  v1 to v2 must fail routing assurance, not merely pass equal-value assertions. No test hook ships.
  Unsupported version rejects without invoking any known handler or writing successful operation.

### Standard node arguments, actual sources and values

- Every builtin (including empty/insert) gets a recorded argument-map node; convenience calls route
  through the SAME URI invoker. Argument bootstrap is explicit and nonrecursive. No unrecorded
  host-path shortcut or automatic dependency/evaluator execution.
- Argument map datum is rederived from exact source nodes, not caller scalar flags. Native MAP pairs
  contain datum IDs only; source DAG/name/node association and all composite children are retained.
  Equal-valued node handles from different sources/key paths preserve THIS source, including repeated
  equal collections in one invocation; global datum-origin lookup is a meaningful negative/mutation.
- Foreign-recorder, fabricated/stale handles and result provenance laundering reject; authoring
  through ended handles rejects, while copied value inspection after closure need not. Validation
  relies on native records and invocation ownership, not dataclass equivalence or a boolean token
  alone. Logical callable lacks public graph/path/context/ref/arbitrary-ID APIs; qualify trusted
  Python introspection authority, not security isolation.
- Duplicate NFC map keys, wrong map/key/list/index types, missing key, I64 index bounds, BOOL/F64
  coercions, prior immutability and canonical insertion order. Nested collection getters return owned
  NODEs with copied Datum values; normal callable returns NODE, not bare Datum.
- Reached/argument/position limits include prospective additions before writes. Native complete
  all-parent/composite closure is separate. Avoid arbitrary sub-DAG root extraction and unrooted-ID
  authority; read/author only exact supported profiles.

### Result/publication/inspection and bridge

- Actual ordered builtin trace, owning Q/full input and returned node/value in normal result sub-DAG;
  no fake scalar projection or copied caller-supplied trace. Builtin semantic operation profile distinct
  from a normal result sub-DAG despite native storage carriers. Validate handler semantics through
  fixed non-recording inspector recomputation, not historical source execution or new call recording.
- Child-local sources/argument nodes/operations/trace/R and old publish_result are one publication
  batch; late failure aborts, no false success. Native handles stay creating-thread owned; no nested
  same-store wrapper/public S projection under a live write; no pointers escape via public node handle.
- NEW Dn/own public Q/ordinary W exact actual parents/tree/ref/reservation/dimensions; coherent alternate
  SAME-name decision/Cq response must reject BEFORE W. Prior complete Dn/Q can remain after W failure.
- Public immutable S required for historical success; one consumed slot validated even on value
  mismatch. New requested source/binding/choice versus historical executed source/binding/trace;
  no new T/getter trace/completion on hit, no automatic adoption/history search. Old APIs unchanged.

Representative NEW batch faults: prospective invalid argument/binding no-target publication; late-ref,
response allocation/consuming commit/real map-full on meaningful new operation+argument publication
or child trace/R/publication; one metadata author-only pre/post response-loss boundary if useful.
Predict genuinely ABSENT native nodes/DAG/tree/commit BEFORE/AFTER; content dedup must not make an
absence oracle vacuous. Keep whole scope/storage/files/Q/W/child distinct. Do not repeat all old S/Q/
exchange fault matrices; existing evidence supplies unchanged contracts. A caught error must not
permit a partially recorded successful scope; document poisoning/abort semantics.

Useful limited mutations: bypass exact version routing; reinterpret NULL as missing/default latest;
hide a source-node/value mismatch; read nested equal value from wrong source; bypass common argument
preparation; forge result-node datum/trace owner; match full source record instead of MAP value;
trust returned Q base instead of actual parent. Measure controller/copy/mutant source BEFORE runs;
failure must hit predicted invariant, not wrong name/import/ref collision. Preserve originals/unknowns.
No thresholds/skips/runtime deadlines/budgets changes. Narrow no-value exclusions need exact rationale;
difficult meaningful failure paths still need tests.

## 4. Build/install and one concrete installed story

Executable native URI + installed module changes require a fresh bounded local build/install AFTER
GO. Use existing cached tools/dependencies and a fresh isolated prefix/venv; do not mutate the old
retained installed20 environment/image rootfs. No global install/image rebuild/service/download.
Missing prerequisites need separately scoped approval. Check actual owning module/package inventory,
linked library/native CLI source provenance and installed bytes; no checkout runtime PYTHONPATH or
source-only helper pretending to be shipped dispatch. Preserve actual filenames for host coverage.

Run ONE [EXAMPLE](EXAMPLE.md) story: THREE Q/TWO synchronous LOCAL attempts, results42/reuse42/43,
eight actual nested getter positions, six caller empty/insert positions and two real post-promotion
old/new compatibility calls;16 successful builtin invocation positions, zero support Q/T. Internal
phases block spawn/transport; only the TWO explicit normal local attempts launch/reap direct children.
Do not add a compatibility local job, extra failed acceptance attempt or computation for a reader.
Native unique record counts may deduplicate; compare positions and owning scopes, not invented IDs.

Controller/captured wrapper/support/native module/library/install manifests retained BEFORE launch.
Save Q and child PID/wait/outcome/native publication IDs incrementally before later metadata.
Direct child known reaped BEFORE observation/receive; stop on uncertain ownership/writers, never
speculatively relaunch. Make only owned original paths unavailable AFTER safe disposition. Transfer
SAME pinned final all-parent/composite history; fresh current-installed readers activate real spawn/
transport blockers BEFORE runtime/helpers load. Exact stdlib URI parsing is not transport; keep
separate real blocker controls. Coordinator independently reads SAME evidence, no duplicate story.
Reader failure -> corrected nonexecuting read on SAME history first, original source/hash/error kept.

This proves shipped fixed dispatch/version retention/node composition and value reuse inside ONE
new installation, not a previous builtin release, old20 reader support, security/purity/fullcapture/
scientific correctness/performance/nativefix/platform all-green. No runtime lifecycle investigation.

## 5. Final gate, independent review and documentation

Owning validation policy applies: focused behavior/concrete installed workflow primary; ONE final
unchanged worker `scripts/check.sh -v` on final relevant sources, no automatic full pre-edit baseline
or second full/story. Repetition requires reviewed assurance benefit. Shared builds/source freeze,
exact changed pathset/HEAD/diff/relevant module/native/source identities and explicit BOTH release
before risk-based coordinator checks/SAME stopped-history installed inspection. No whole-repo census
ritual or false pass from unfinished commands. Raw errors/uncertainty preserved; new attributable
failures block, related old async/LMDB recurrence needs fresh scope, VP-001 is not a standing waiver.

After GO, add owning as-built runtime documentation for fixed builtins/node profiles/NULL binding/
standard invocation/result contract/version limits; update native URI authority and package module
inventory. Old external-request authorities gain ONLY the explicit reserved-intent restriction;
other local/exchange/transfer contracts and old example docs remain accurate.
Glossary clarification can distinguish semantic value-oriented node interface from native storage
nodes without changing Datum to mean Node or falsely claiming a generic evaluator.
Review [diagram guidance](../../../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance)
against actual native storage/URI/boundary claims. Ordinary operation DAG carriers are not new LMDB
entities; no diagrams of proposed native opcodes. Focused diagram checks if edited, no rendering
claim without relevant verification. No DML/glossary/spec/diagram changes during preparation.

Development GHA stays disabled. No enable/launch/rerun, workflow/runner/budget/release-control or
repository-setting edit. Report intentionally NOT RUN, not green; local evidence not fresh platform
assurance. Preserve prior failed/cancelled rawCI/UNKNOWN/65possiblylost/VP-001/private19 PAUSE.

## 6. Conditional publication and STOP

ONLY after independent acceptance and separately authorized publication: exact staged path/secret/
whitespace audit INCLUDING new/untracked files, focused worker commit/normal existing remote push,
verify exact current+committed accepted hashes/parent/clean source-index/live remote SHA. No force
push, design checkpoint publication or package/release publication. Read-only workflow state verify
as relevant; development GHA NOT RUN. Results/review distinguish actual exits/worker/independent/
installed/host/substituted evidence, exclusions, source changes and safe owned custody. Finalize
RESULTS and explicit STOP ALL; no further feature/native investigation/runtime restart follows.

This preparation starts NOTHING. No worker/build/install/native validation/story/CI/experiment/
provisioning/commit/push until reviewed plan and separate GO; no inherited completed20/paused19 scope.
