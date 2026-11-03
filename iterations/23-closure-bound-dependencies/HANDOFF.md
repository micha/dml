# Iteration 23 conditional handoff: closure-bound dependencies

Status: **prepared for review; NOT implementation/delegation/publication GO**.
The user's “proceed” authorized preparation ONLY. Read ALL THREE [DESIGN](DESIGN.md),
[EXAMPLE](EXAMPLE.md) and this handoff. Exact engineering spellings remain refinable.
Candidate review, then separate GO/delegation/publication permission; this document starts nothing.

## 1. Bounded capability and explicit scope change

Record and consume a closure's immutable captured dependencies, both callable and noncallable,
separately from invocation arguments. Recommend ONE fixed ordinary local scaled-sum func, capturing
supported internal getter bindings and an I64 scale source. Default promotion does not change an
existing capture; equivalent captured values can reuse while changed scale partitions eligibility.

The initial assistant outer-double_sum/inner-add-double request proposal is DEFERRED. Current
fixed builtin dispatch does not invoke arbitrary ordinary funcs; local/exchange publication enforces
fixed tree/parent deltas and direct-child ownership. This candidate intentionally has no separately
recorded inner ordinary requests or nested workers. Its computation `(a+b)*captured_scale` is explicit
Python in ONE local attempt. General captured dependencies remain the conceptual direction; the
prototype supports only the fixed literal-source and internal-builtin capture types.

Recommend NEW example-local helper/logical/captured-wrapper files, focused `tests/python/` checks,
explicit installed controller/reader in a NEW `tests/` directory, and informative owning `docs/`
example/navigation. No production library imports examples; captured child code does not resolve
checkout-only modules. Prefer unchanged installed builtin/local/exchange/transfer/native code.
A demonstrated missing public seam needs coordinator review BEFORE expansion.

Candidate roles C/E/F/K/D/summary are ordinary DAG conventions. Q/binding/argument/trace/return/S/W
contracts remain unchanged. No private codec, native entity/layout/opcode, general evaluator,
recursive closure interpreter, dispatcher/registry/cache discovery/table, resource provisioning,
async/open/lifetime repair, automatic default/reuse adoption or release feature.

## 2. Authorities and preflight ONLY after review and GO

Read machine index/admin/mounted-work guidance; design AGENTS/README/discussion resume/glossary;
ALL23 documents; implementation AGENTS and [documentation guidance](../../../dml/docs/documentation-guidelines.md).
Relevant authority/source links:

- [Internal builtins](../../../dml/docs/internal-builtins.md),
  [builtin.py](../../../dml/python/daggerml/daggerml/builtin.py): Recorder.source/load/arguments/
  operations/call/returned, Inspector, publish_callable's existing one-normal-callable scope.
- [Python storage](../../../dml/docs/spec-next/python-api.md),
  [objects](../../../dml/docs/spec-next/objects.md),
  [repository](../../../dml/docs/spec-next/repository.md): ordinary native authoring and storage batches.
- [Caller Q](../../../dml/docs/spec-next/caller-requests.md),
  [local execution](../../../dml/docs/spec-next/local-execution.md),
  [exchange](../../../dml/docs/spec-next/repository-execution.md),
  [exchange.py](../../../dml/python/daggerml/daggerml/exchange.py): exact submission/publication/F shapes,
  direct-child wait/reaping and historical ownership, not nested-process support.
- [Public successful S](../../../dml/docs/versioned-reuse-selection.md),
  [reuse_selection.py](../../../dml/examples/reuse_selection.py) select/inspect,
  [transfer](../../../dml/docs/spec-next/transfer.md): retained complete typed Q/T/R/F authority.
- [Current composed calls](../../../dml/docs/composed-node-calls.md),
  [composed_node_calls.py](../../../dml/examples/composed_node_calls.py),
  [Iteration22 results](../22-composed-node-calls/RESULTS.md)/[review](../22-composed-node-calls/REVIEW.md):
  existing value+source distinction/own-Q checks/methodology, not proof of NEW closure behavior.
- [Owning validation policy](../../../dml/docs/validation-policy.md),
  [GHA disabled decision](../19-intent-scoped-reuse/GHA-DISABLED.md),
  [VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md).

Preparation verified implementation clean `a57125cdf735310f2330226ce6272b3a67e53f62`; no builds,
installs/tests/story/readers or runtime edits. Accumulated uncommitted design notes stay unrelated to
implementation staging. Reinspect actual HEAD/index/relevant changed source/tools after GO; no full
baseline, automatic whole-repository inventory, downloads/global environment change or old fixture restart.

Only if separately delegated: existing window2 worker in verified NEW Pi session. Coordinator
explicitly transfers BOTH `build/check`/`build/coverage` and source until targeted changed-surface/
HEAD freeze/release. Worker owns implementation/tests/docs/owned evidence/RESULTS; coordinator
review/coordination/design status. No additional worker/model/global configuration change.

## 3. Pre-edit change-validation map

Record concise chosen invariants/evidence before edits. Resolve exact capture/child association
plumbing read-only before coding. Keep profile/identity details distinguishable from user decisions.

### Closure construction and dependency association

- Fixed strict F/E/K/C profiles: exact root/field sets/types/supported getter pair and retained
  semantic I64 constant. Native datum ID/storage node description is not a semantic handle.
- C retains E/K/B by actual graph links; E retains exact F/constant source. Source wrapper embeds E
  ID, NEVER C's own future hash. No self-ID cycle or sole string-ID retention.
- Reconstruct fixed captured B bytes from exact E/logical/helper bytes; consuming another coherent
  same-value E or a moving default is not equivalent provenance. Reject unknown versions/unretained
  descriptors/corrupted link/value/role/root; no silent fallback to latest.
- Atomic creation adds ONLY two absent B/C names in one-parent snapshot/create-only ref. Constants/
  getter descriptors are prepared earlier; no Q/T/job/primitive invocation during closure creation.
  Publication context is not a unique closure-occurrence object; equal immutable content deduplicates.
- Default promotion changes only intended convenience entries in a new snapshot. Existing capture
  stays byte-identical and executable by explicit selection; no mutation of captured E/source.
- No nested same-store public projection while a write lives. Public validation scratch/handles
  close before authoring; no native pointers escape or cross-thread inspection reuse.

### Invocation, constant value and source access

- Invocation MAP exact `a,b` I64. Captured scale remains outside it; `scale` override/extra fields
  reject, BOOL/F64/coercion/overflow reject. Source-distinct equal MAPs remain canonical-value equal.
- Wrapper consumes exact pinned D/C/E/B, not current default names. Validate decision/request native
  spines BEFORE publication write; bind constant node/getter ops in THIS recorder. Python lexical
  factory parameters are not extra graph arguments or implicit provenance access.
- Logical function receives argument node/value-oriented ops and captured value node, NOT repository,
  graph navigation or context. Preserve cooperative trust limits; no sandbox/full capture promise.
- Two actual child map-get positions use exact captured map-get-v1/v2; list-get binding is validated
  support capture but not invoked. Standard preparation/literal constant load adds no getter position.
- Existing16arguments/16positions/64semantic DAG and native transfer caps unchanged. Count reached
  closure of source nodes/argument ledgers/operations/result BEFORE puts; do not raise limits.
  New descriptor reader has fixed small fields, no arbitrary unbounded traversal/recursive captures.
- Publish existing normal returned/trace/Q/full-I in unchanged ONE child transaction via public
  Recorder/local helpers. No fields appended to strict builtin/Q/binding roles or altered F joins.
  C/E/D capture provenance is separate; old literal result does not trace arithmetic it never recorded.

### Computational identity, own Q/W and old execution

- Recompute K from E: typed scale datum and captured builtin FUNC URIs, not user token/source origin/
  exact implementation version/default/ref/commit. Key is NEW `(intent,K,full invocation MAP)`.
- Distinct equal2 source nodes and equivalent map-get-v1/v2 retain distinct capture provenance but
  equal K. Scale2 versus3 differs even when intent and invocation MAP equal. No arbitrary normal
  implementation or recursive closure equivalence is assumed. Old example keys stay unchanged.
- Strict D captures requested C/E/K/B/I and known selected S, including valid mismatch/fresh control.
  One-parent intended D delta; actual Cq parent equals THIS D, exact Q/tree/ref/reservation/dimensions.
  Reject coherent wrong same-name closure/decision and forged response flags BEFORE W.
- Public S success AND ORIGINAL D/C/E/K/return/Q/input/getter trace validation; malformed selected
  entry errors even on mismatch. Same scalar alone is not reuse authority. Preserve selected T through S.
- Reuse owns NEW Q/W but creates no T/getter/completion. NEW requested C-B/v2/origin-B is not rewritten
  into OLD executed C-A/v1/origin-A. Fresh controls and changed-capture miss leave S1 unchanged.
- Miss records pending Q before separate explicit dispatch. W late failure can leave legitimate Q;
  closure/decision/Q/W/files/child are separate boundaries, not an operation-wide rollback.

### Meaningful finite faults and mutations

Test genuinely new absent rows for closure B/C publication through actual late-ref and native
map-full/consuming-commit faults, with predicted IDs and unrelated immutable-byte preservation.
Deduplicated old E/K/constant records do not prove rollback. One author-only pre/postcommit lost-ack
control if useful, preserving absent versus complete publication without automatic re-recording.
Reuse existing evidence for unchanged Q/exchange fault matrices; do not duplicate every inherited test.

Useful measured private mutations: reread current getter/scale defaults; ignore scale in K; include
source identity in K; use stale/original C as requested capture; trust D/response claims instead of
native parent/binding; skip ORIGINAL capture validation on value mismatch. Predict actual assertion/
rejection before running; retain original failed/weak probes and measured prelaunch identities.
No shipped fault hooks, exhaustive mutation claim, weakened threshold/skip/budget/deadline or hidden
retry. Narrow no-value exclusions need exact location/rationale; meaningful difficult failures need tests.

## 4. Sole installed acceptance and SAME-history review after GO

Fresh bounded isolated local current-source install with cached project tools, no downloads.
Example helpers remain captured/copied local files, not claimed installed library APIs. Record actual
parent/child installed/native/CLI/interpreter/helper/wrapper/logical/controller identities before
launch; unset PYTHONPATH/PYTHONHOME and exclude checkout runtime imports. Do not alter old prefixes/
private19 candidate/evidence. Missing packages/installations/downloads require separately scoped approval.

Run ONE [EXAMPLE](EXAMPLE.md): **SIX Q/FOUR synchronous LOCAL attempts/EIGHT child map-get positions**:
fresh84; old closure reuse84 after default change; old closure fresh84/v1; equivalent new closure
reuse84; new closure fresh84/v2; changed scale miss then fresh126/v2. Zero list/construction/support/
compatibility calls, inner ordinary requests or descendants. Default/capture/known S changes are explicit
metadata batches. Additional fresh-completion S slots are evidence only, not selected-result adoption.

Metadata phases block actual spawn/transport; allow only FOUR explicit direct-child dispatch
boundaries. Reuse/closure creation execute no child. Record incremental Q/T/C/E/K/spawn/PID/wait/
publication/outcome/cleanup receipts BEFORE later assertions. Existing synchronous execute, known
direct-child wait/reap, THEN completion observation/import; no async supervision fixture. Failure or
uncertain custody STOPs for bounded triage, not relaunch/deadline bump or replacing original evidence.

After all four owned children are known reaped, retire ONLY owned operational originals, retain inert
bytes and transfer SAME complete pinned history. Blocker-FIRST actual negative controls before fresh
installed NONEXECUTING readers: no recording/dispatch/logical arithmetic/source exec/target writes/
new refs/transport, public validation scratch allowed. Inspect actual six Q/four T/eight ordered
positions, exact capture/current-versus-OLD execution, native/public S/own-Q/W/summary/source hashes/
ordered F parents and immutable data bytes. Correct reader errors on SAME evidence first, preserve
failed sources/oracles and provenance qualifications. Independent review does not rerun computation.

## 5. Validation, documentation and conditional delivery

Focused changed behavior/concrete acceptance primary; ONE final unchanged worker `scripts/check.sh -v`
on final relevant sources under [validation policy](../../../dml/docs/validation-policy.md).
No automatic baseline/second full/installed story/whole-source inventory rituals. Targeted source/
HEAD/changed-path/diff/evidence freeze and explicit BOTH-build release before independent risk-based
focused/SAME-history NONEXECUTING review. Preserve raw failures/source changes/unknowns; new-source
pass does not prove original-source pass or historical cause attribution.

Add informative owning closure example documentation with links to builtin/Q/S/local/transfer
authorities; do not turn candidate roles into native specs. Review actual
[diagram guidance](../../../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance):
ordinary DAG descriptors with SubDAG references normally add no native entities/layout/keys. Update
only actual affected displayed claims after authorized implementation; never show proposed native
closure storage. Glossary's existing provisional closure/dependency meanings suffice; exact API
identifiers remain document-local, not a new global schema authority.

Development GHA disabled/NOT RUN/not pass; no enable/run/workflow/budget/runner/settings/release-control
change or fresh platform all-green. Native19 PAUSED/private candidate incomplete-unexecuted retained.
VP-001 planning revisit OPEN UNKNOWN/same coordinator owner/conditions, NOT a standing waiver or
native diagnosis. Related async/LMDB/open/lifetime need/recurrence requires fresh scope/triage; do not
silently use this handoff as investigation permission. Historical raw failures/cancellations/possible-
lost memory/source qualifications remain.

ONLY after separate GO/publication authorization and independent acceptance: focused staged-path/
secret/whitespace audit including new files, exact worker commit/NORMAL existing remote push, accepted-
current-committed/parent/clean source-index/live remote verification and read-only workflow-state GET.
No force/tag/release/package/design checkpoint publication. RESULTS distinguishes focused/full/
installed/independent evidence, faults/exclusions/source qualifications/known custody; explicit STOP
ALL/BOTH builds/source/evidence returned. No later feature or investigation restart.

This conditional handoff authorizes nothing to execute. Candidate review precedes separate GO.
Completed22 and paused19 permissions are not inherited.
