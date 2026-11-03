# Captured ordinary calls

Status: **example-local implementation; corrected installed story and SAME blocked readers pass**.
Original+resumed validation evidence is complete; independent acceptance/publication remain pending.
The original full-v failed at generated HOST reporting labels; the exact approved reporting
exclusions and resumed unchanged requested stages are documented in
[completion evidence](../../dml-design/iterations/24-captured-ordinary-calls/REPORTING-COMPLETION.md).
This is combined evidence, not a retroactively passing original invocation.

## Authority boundary

This page owns the NEW [profiles](../examples/captured_calls.py),
[short-scope session](../examples/captured_call_session.py),
[in-process adapter](../examples/captured_call_adapter.py),
[logical double_sum](../examples/captured_call_funcs.py) and
[captured LOCAL leaves](../examples/captured_call_leaf.py).
[Internal builtins](internal-builtins.md) owns semantic node recording/inspection and its
unchanged16arguments/16positions/64reached bounds. [Python storage](spec-next/python-api.md),
[caller Q](spec-next/caller-requests.md), [LOCAL](spec-next/local-execution.md),
[exchange](spec-next/repository-execution.md), [successful leaf S](versioned-reuse-selection.md)
and [transfer](spec-next/transfer.md) keep their existing contracts. These ordinary conventions
are not installed dispatcher APIs, native entities/opcodes/record codecs or a general evaluator.

## Actual composition and explicit execution responsibilities

The fixed logical factory receives opaque captured add/double tokens and bound interfaces:

```text
invoke(original argument-map NODE):
    a = nodes.map_get(original, "a")
    b = nodes.map_get(original, "b")
    require both actual getter results are I64
    summed = calls.invoke(captured_add, original)
    return calls.invoke(captured_double, nodes.arguments({x: summed}))
```

The original node is forwarded intentionally. Add's recorded getters and the outer getters
can share immutable operation DAG IDs because their binding and exact input/source are identical.
They still occupy TWO positions in each separate owning ledger; native content deduplication does
not deduplicate events. Input plus double's argument map gives TWO maps per fresh composition,
with three retained as an upper bound. No redundant reconstructed add map or Recorder.source
projection is used. Double's entry source is the exact validated normal add R, not literal42.

The logical code really invokes its supplied ordinary call interface. The call interface records
requests/resolves independently pinned controls and produces node handles. The adapter evaluates
ONLY the fixed supported captured logical source in the finite application process. Fresh leaves
use public synchronous exchange/LOCAL in independent repositories; their computational children
are direct children of that SAME application. There is no outer subprocess, asynchronous owner,
RPC server, descendant worker, URI fetch, recursive ordinary evaluator or arbitrary-code timeout.

Execution, call recording and recording integration are responsibility distinctions, not mandatory
separate services/entities. Cooperative trusted Python is **not a security sandbox, purity proof,
complete environment capture or scientific/arithmetic certification**. Finite calls are not a
portable wall-clock limit on in-process Python. Leaf Python explicitly checks I64 arithmetic.

## Immutable captures and conservative identities

Role-rooted leaf E captures exact map-get/list-get bindings. Leaf B retains exact wrapper/logical
bytes, E ID, interpreter and timeout under unchanged local-python-binding-v1. Leaf C retains intent,
B/E/K; K is exactly the B/E pair. Outer E captures add C/double C/map-get-v1. Outer B is DISTINCT:
role `example-outer-binding-v1`, adapter URI `urn:example:in-process-double-sum-v1`, exact captured
logical/session/adapter/profile source BYTES, interpreter NULL, timeout-ms NULL, E link. Outer C
retains intent `urn:example:captured-double-sum`, B/E/K. K links B/E AFTER they exist, before C.
No source contains future C/F IDs; graph links, not embedded ID strings alone, retain dependencies.

NEW outer/leaf matching is exact intent + verified B/E identity K + FULL computational argument MAP
value. Existing examples' keys are unchanged. Arbitrary same-intent closure equivalence is not
inferred. Source/interpreter/captured getter choice partitions this conservative identity.
Containing commits, convenience default names and controls do not retarget captured C.

Bootstrap/default promotion makes no Q/T/getter invocation. Promotion changes only two existing
convenience tree entries. Present known outer/double selections are validated even on explicit
fresh or value mismatch; poison is an error, not a miss. Fresh work never auto-adopts.

## NEW request/attempt/phase authority

All scalars use native Literal nodes; DAG links use existing SubDAG carriers. These roles are
ordinary example conventions, never fed into old LOCAL Q/T/F or successful-S validators.

- D roots at inputs. It captures exact C/B/E/K/input MAP value, control/action, selection if present,
  and a separate plan. Plan fixes actual basis BYTES16, add=fresh, double control and present S.
- Q is occurrence-rooted `cq-<32hex>` with exact role/intent/B/inputs/C/D fields. D and Q are separate
  native commits authored in one storage batch; each exact single-parent/tree delta is checked.
  Explicit decision/submission/request-reservation refs are create-only. Metadata loss is not retry.
- Initial T is immutable, occurrence-rooted `ca-<32hex>` with Q/plan. Its commit adds ONLY T to Q.
  Checked attempt-head updates coordinate short batches; no writer/handle spans ordinary dispatch,
  validation scratch/import or waiting.
- Consecutive immutable phase DAGs bind Q/initialT/kind/index/actual previous commit and fixed
  kind-specific payloads. Get-a/get-b must precede prepare; one double-input follows successful add.
  Preparation binds exact target C/B/E/K, argument DAG, own outer Q/T, slot, basis/control and names.
- Public LOCAL Q is separately recorded. BEFORE dispatch/reuse, native THIS preparation parent,
  Q dimensions/tree/submission/reservation refs and complete persisted prefix are checked. Returned
  descriptions/flags never authorize dispatch. Slot1 requires THIS double-input and add S/T/R.
- A fresh F is publicly received under an explicit ref, then integrated by a NEW phase commit with
  ordered parents `(previous outer phase, exact leaf F)`. Preserve the whole previous outer tree;
  do not copy an arbitrary leaf head tree. Public S follows THAT join; DONE must consume THAT own
  Q/F/S. Reuse instead records own public Q/W, consumes pinned OLD S/T/R, and makes no fresh F/T.
- Custom outer return roots at an I64 value and links exact returned double R, Q/initialT/full input,
  both ordered calls and outer getter positions. It is not builtin-return-v1 with a fake local Q.
- Completion links initial T, plan, ordered calls and return, or a strict known-failure profile.
  Final T preserves occurrence/role/Q/plan field nodes, adds initialT/done/completion. Completion
  links INITIAL T, not future final T/F. Final commit replaces only T and adds completion, preserving
  unrelated entries with exactly one previous-phase parent. No self-ID/F cycle.

## Successful ORIGINAL authority and outer reuse

Standalone leaf inspection composes public S/Q/T/P/U/F validation with exact captured leaf/normal
return/getter/source checks AND the ORIGINAL actual outer D/Q/plan/initialT and prerequisite prefix.
Add's prefix ends at get-b; double's ends at THIS double-input and certifies only completed slot0.
It does not require outer success: a successful first leaf survives a later failure. ORIGINAL
preparation phase/payload/tree/basis/public Cq parent and captured target are checked independently.

`MAX_AUTHORITY_DEPTH=8` counts crossed ORIGINAL selection/producer authority edges. Its own
request/spine/prerequisite helper frames preserve the same depth. Every recursive public entry
uses the SAME hard guard; no resets or skipped ORIGINAL checks. This NEW unpublished-helper bound
was refined from4 after a real HOST validation failure; existing runtime/semantic/transfer limits
were not changed. The fixed story's HOST before-return/final reader paths measured max5; actual
retained ancestry reaches8 and next edge9 rejects before Q. Installed evidence remains pending.

Outer S has exact role/completion BYTES16/C/Q/finalT/R, rooted at R. The F ID is metadata, not a
native retention edge: F must be in ALL-parent history. Reader validates original completion,
initial-to-final T and both ordered call associations. Explicit select authors ONLY absent S after F.
Outer W roots at OLD R and binds own NEW Q/THIS D/pinned S/OLD finalT/R. W commit adds only W to own
Q with exactly that single parent. Outer hit creates no outer T/phase/getter/inner Q or invocation.

Swapped add(29,13) differs in full MAP from add(13,29), although both produce42. Downstream MAP x42
matches with SAME double capture. NEW double Q/input/source/add S/T/R stays distinct from OLD double
T/R and its ORIGINAL Q/input/add S/T/R. Both chains remain retained and independently validated.

## Bounds, failure and uncertainty

One aggregate semantic-ID set spans short scopes and all consumed ORIGINAL chains. It includes
builtin literal/source/argument/entry/ledger/operation/trace/return DAGs and validated builtin
bindings; metadata C/D/Q/T/S/phase roles still have full typed/native/ALL-parent transfer authority.
Opening another Recorder never resets the aggregate. Conservative future additions are reserved
BEFORE semantic puts or fresh child dispatch. Existing per-Recorder bounds are also enforced.

HOST native profiles measured34 for the original complete chain and50 for the swapped requested/
OLD union, including support binding. Native adversarial profiles prove actual64 membership and
pre-put/fresh-dispatch reservation rejection; fake-counter tests remain separately qualified.
These are source-specific evidence, not general quotas or installed receipts. Fixed session counts:
two outer getters, two ordinary calls, two maps (three upper bound); native transfer caps unchanged.

First recorded leaf failure stops slot1; later failure retains earlier successful work. A failed
leaf has public failed-F framing/witness, not a fabricated successful S. Known cooperative session
failure records bounded detail only when direct-child disposition is known. Caught interface errors
permanently poison success. Native/persistence/import/public-validation/uncertain-wait errors retain
partial phases and outcome UNKNOWN, not invented success/failure or automatic retry. Precommit faults
abort that batch; postcommit acknowledgment loss may leave a visible complete publication.
Outer has no synthetic OS exit/cleanup record. LOCAL computational outcome/cleanup stay distinct.

## Evidence and delivery boundaries

[Focused tests](../tests/python/test_captured_calls.py),
[coherent edges](../tests/python/test_captured_call_edges.py),
[native atomicity](../tests/python/test_captured_call_atomicity.py),
[strict final profiles/bounds](../tests/python/test_captured_call_profiles.py) and
[logical checks](../tests/python/test_captured_call_logical.py) distinguish HOST substitutions from
native row/ref rollback. [Finite mutants](../tests/captured_calls/mutations.py) use measured private
copies/plugins, not shipped hooks or an exhaustive score. [Installed controller/reader](../tests/captured_calls/README.md)
is opt-in. The first activation failed before any leaf launch because the controller's event
category collided with phase payload `kind`; its durable1Q/1initialT/1get-a and raw incomplete log
remain retained. The reviewed controller-only `event` envelope correction passed a real metadata
phase regression, then a separately authorized FRESH story completed10Q/8T/five LOCAL/6ordinary/
14getter with allfive wait0/native barrier/reaped-absence receipts. NEW owned originals were
retired only after known reaping; blocked fresh SAME-history caller/replica readers passed without
writes/recording/arithmetic/dispatch, checking native provenance/counts/34+50 unions. This is worker
installed evidence, not independent test execution/platform or implementation acceptance.

[Diagram](lmdb-entity-diagram.html) review: ordinary roles/joins use existing native DAG/node/tree/
commit/ref relationships, no new entity/key/hash/layout/namespace implementation. No diagram change
is needed for these example roles. GHA disabled/NOT RUN/not pass; native19 PAUSED/VP001 OPEN UNKNOWN.
Commands/source qualifications/failures/independent acceptance belong to
[Iteration24 results](../../dml-design/iterations/24-captured-ordinary-calls/RESULTS.md), not inferred
from this draft or an unexecuted platform workflow.

Current focused closure includes coherent LAST-native-snapshot and publicly valid ORIGINAL
history controls, separately labelled HOST delegate/Inspector response substitutions, and
TEST-PRIVATE copied-session-state reconstruction. Informative cumulative helper line coverage
is1144/1144 after the [single approved exclusion](../tests/coverage-exclusions.md#iteration-24-captured-ordinary-call-exclusion);
this is not an unchanged full gate, every Python branch or instrumented installed-child coverage.
The excluded post-retention raise is not a passing test. Its comment-only marker preserves the
AST including locations but changes captured outer source BYTES/B identity: older native proof
and v7 measurements retain their old hashes plus static unchanged-behavior/count/depth mapping,
not an exact current-source or newly executed installed claim. The later corrected installed
story separately measured34/50 under current captured bytes and passed bounded validators; it
does not retroactively change the older measured source IDs or claim a newly instrumented max5.
