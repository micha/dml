# Iteration 8 candidate design: caller-recorded requests

Status: the user approved this bounded design, worked example and conditional handoff
and requested a local design checkpoint. This is an **approved plan, not implemented
behavior or implementation/delegation/publication GO**. No experiments, worker restart/
assignment, implementation commit/push or CI authorized. Iteration 7's completed GO is
not inherited. Illustrative spellings remain refinable; this is not an as-built contract.

## 1. Ownership, agreements and learning goal

This document owns candidate request-recording, dispatch and history-validation mechanics.
[EXAMPLE.md](EXAMPLE.md) owns acceptance; [HANDOFF.md](HANDOFF.md) owns future work order.
[Discussion](../../discussion.md#iteration-8-agreed-direction-caller-recorded-requests)
owns agreements and the [glossary](../../../dml/docs/spec-next/glossary.md) owns vocabulary.
Current [local](../../../dml/docs/spec-next/local-execution.md),
[exchange](../../../dml/docs/spec-next/repository-execution.md),
[asynchronous](../../../dml/docs/spec-next/asynchronous-execution.md) and
[transfer](../../../dml/docs/spec-next/transfer.md) contracts own implemented behavior.

Agreed direction:

- A explicitly records request Q before launch, without hidden start-time writes or
  automatic movement of its existing heads.
- Transfer pinned history to fresh local B; B creates T for the **same Q**, not a new Q.
- Reuse asynchronous P/U/F observation and validated explicit-ref reception.
- Preserve an unstarted request when launch fails/never occurs; do not invent an outcome.
- Fresh clients observe without relaunching; distinct submissions have distinct Q/T even
  if bindings, inputs and result content match. Reject history for another matching Q.
- Same machine; no automatic retry/recovery, global exactly-once, network/cloud,
  scheduling, reuse/facets, resources or observer feature.

Learning goal: make the caller's request durable independently of worker launch, with
continuous request identity across repository boundaries before adding network transport.
Exact mechanics below originated as assistant recommendations and are now accepted as
this bounded plan. Illustrative APIs/format spellings remain engineering refinements, not
already implemented contracts. Earlier candidate-review phrasing preserves provenance.

## 2. Inspected baseline and why a new public seam is needed

Planning inspected clean implementation
`a8d646379a52878d087d28bc216b7baa4f9ef3db`. Design retains intentionally uncommitted
Iteration 7 delivery/status and Iteration 8 direction notes. No implementation/spec edits,
tests/builds/prototypes, worker activity or publication occurred during preparation.
[Iteration 7 RESULTS](../07-asynchronous-local-execution/RESULTS.md) and
[REVIEW](../07-asynchronous-local-execution/REVIEW.md) are prior evidence, not a fresh baseline.

Current source seams:

- `local.run_step` records Q and T together in B; there is no public request-only builder.
- `local.retry_step` accepts an existing request only through its **local reservation ref**.
  Import does not copy refs, so calling retry on imported Q alone fails. Treating the first
  attempt as a retry, synthesizing refs in exchange to bypass validation, or calling private
  `_prepare`/`_record` would obscure ownership rather than solve it.
- Local child context and finalization require exact Q in P and a matching reservation
  snapshot. Existing publication/finalization mechanics can remain after preparation changes.
- Exchange `_initial` currently requires fresh Q/T additions to its base; `_discover`
  derives both from new tree names. Caller-origin mode must instead pin existing Q and
  derive only fresh T. Both synchronous and asynchronous returned-history paths use these
  checks and must be extended together without weakening the original mode.
- Transfer, native transactions/refs and the fixed installed worker already provide the
  required transport/storage/process seams. No native operation or alternate codec needed.

## 3. Recommended stages and illustrative API

Use a narrow public local request builder and explicit first-attempt operation, composed
by exchange. Exact names/signatures are illustrative:

```text
local.put_local_request(tx, *, request_id, intent_uri, binding, inputs) -> ObjectId
local.run_request(repository_path, *, head_ref, request_commit, request,
                  scratch_dir=None) -> LocalRun

exchange.record_exchange_request(A, *, commit=C, binding_name, inputs_name,
                                 intent_uri, ref=submission_ref, map_size=0)
    -> RecordedRequest
exchange.prepare_exchange(A, *, commit=Cq, binding_name, inputs_name, intent_uri,
                          worker_ref, workspace, request=Q) -> ExchangeSpec
```

`prepare_exchange`'s proposed optional `request=None` preserves the existing fresh-Q-in-B
calling mode; request-present mode pins caller Q. Existing start/execute/observe/receive and
handle helpers remain the entry points. Do not add a generic mode registry or new executor.

`RecordedRequest` is a frozen owned description of base C, submission Cq/ref, Q ID and
occurrence, selected names/IDs and intent. It holds no live handle/process or transport token.
Transport token/workspace belongs to later preparation, not request identity. A suggested
`ExchangeSpec.request: Optional[ObjectId]` pins Q content, including its occurrence; derive
qid/name from validated Q instead of trusting another mutable selector. Equivalent bounded
spellings can be refined in implementation and recorded in RESULTS.

The local builder validates exact occurrence profile, canonical consumed role/types and
binding/inputs using local-owned readers, then constructs the existing ordinary Q shape.
It does not generate refs, commit a transaction, claim unique occurrence, allocate scratch
or launch. Its caller owns atomic storage publication/collision handling. Existing `run_step`
may reuse this local-owned builder without changing its role bytes or behavior. The
recording helper's proposed `map_size` follows existing repository options for its A
transaction; it is not a computation/result quota or permission for automatic map growth.

## 4. Explicit atomic request recording in A

Recommended exchange helper behavior:

1. Validate arguments; read **explicit immutable C** within the helper's write transaction.
   Resolve selected binding/inputs by C's tree names and validate consumed local values.
   A's moving main is not selected or changed.
2. Require caller-chosen submission ref absent. Generate a fresh `q-` UUID occurrence,
   with a small bounded collision retry like current local preparation. Reject existing
   matching request-ref/tree names, including malformed/dangling ref keys; never repair.
3. Build Q with the existing `local-request-v1` root/fields via public local builder.
   Cq has exactly parent `(C,)` and C's exact tree plus `request-<qid> -> Q`.
4. Atomically store Q/Cq and create **both** the explicit submission ref and an A-local
   `request-<qid>` reservation ref pointing to Cq. No T, scratch, publication or outcome.
   Prebuild the owned description before successful storage commit.

The reservation is a local collision/association convention, not a transmitted capability.
The explicit submission ref is create-only, not a head that the helper updates. If names
coincide/conflict, fail the whole batch. Other refs/old records remain byte-identical.
Ordinary raw object construction cannot establish global uniqueness across copied histories.

This helper **does write A**, deliberately and separately from preparation/start. Request
recording and workspace preparation are not one transaction. Prepare/export/file failure
leaves already-recorded Q retained under its refs. Loss before recording commit leaves no
batch; loss after commit before response can leave Q/Cq/ref despite no returned description.
Do not automatically rerun recording after response loss. Inspect explicit ref; repeat
recording with that existing ref rejects before a new committed Q. No idempotency service.

## 5. Pinned submission validation and B-local first-attempt registration

Caller-origin preparation validates Cq as a submission, not any snapshot containing Q:

- Cq has exactly one parent C; its tree equals C's tree plus exactly Q's canonical name.
- Q/name/occurrence/role/types are exact, that name was absent in C, and selected named
  binding/inputs and intent agree with Q. Selected bindings remain unchanged from C.
- Pinned expected Cq/Q IDs, not matching argument values alone, select this request.
- A-local reservation refs are not needed for read-only preparation/validation of copied
  Cq. Their absence does not authorize dispatch and does not require recreating them.

Prepare performs no A writes, exports full Cq history and writes the existing exclusive
workspace/bounded job last. Propose adding Q selection to the strict descriptor/handle
profile; reject unknown/missing/wrong-type fields. Formats may advance consistently
without pre-1.0 migration/old-file compatibility machinery. Existing API modes/tests stay
usable with freshly generated files. Exact labels remain implementation choices.

Execute imports Cq into fresh B under worker ref, validates root/Cq/Q/selection, closes
handles and publishes readiness as today. It calls **public `run_request`**, never private
local functions or exchange-created reservation shortcuts.

`run_request` recommends one atomic pre-dispatch transaction:

1. Require worker head exactly `request_commit == Cq` and validate exact submission/Q.
2. Require B-local Q reservation absent; different, same-target, malformed or dangling
   existing reservation rejects. This is first registration, not a retry/repair API.
3. Generate only fresh T, with existing bounded attempt-name/ref collision checks.
4. Preserve Cq's entire tree including **exact Q ID**; add only `attempt-<aid> -> T`.
   P has parent `(Cq,)`. Atomically move worker head to P, create Q reservation at Cq
   and attempt publication ref at P. Close transactions/handles before execution.

No computational launch before that transaction commits. This candidate operation is
specifically first registration of an **unregistered imported submission**, not a universal
first-attempt helper for every locally reserved Q. A's already-reserved request does not
qualify; executing it in A is not this acceptance slice. Builder/role reads retain the
existing direct-validation contract; complete transfer validation supplies transitive
closure checks, not scientific or full-environment assurance. A failure aborts new T/refs/head;
Q remains imported in B and recorded in A. P can survive loss before actual child dispatch:
T exists but outcome remains unknown. Existing child context works because Cq's reservation
snapshot contains exact Q; publication/reaping/cleanup/finalization remain the existing path.
`run_step`/`retry_step` keep their original behavior and tests. An explicitly requested local
retry remains its existing API, not something the exchange worker invokes automatically.

Importing Cq/Q **alone** neither creates B reservation nor executes. Dispatch authority here
is a trusted caller's explicit one-shot workspace plus explicit `run_request` invocation,
not a cryptographic permission encoded in Q/ref. Reject second first-attempt registration
in that B. Fresh repositories/workspaces can copy Q and explicitly request more attempts;
this prototype makes no global claim that the same Q cannot ever execute twice. Such
replay/recovery policy is outside this slice; no automatic relaunch or marker clearing.

## 6. Observation and receive: same Q, fresh T

Retain Iteration 7 live-owner/readiness/coherent-read/pinned-export/isolated-validation
mechanics. Bootstrap creates no packet or T. Caller already knows Q from RecordedRequest
and expected Cq/Q; unchanged bootstrap response with no selected attempt snapshot does
**not** mean the request is absent. No new request-only packet phase/lifecycle is needed.

In caller-origin mode discovery derives Q from expected/validated submission, **not fresh
request-name differences**. Relative to Cq, require exactly one fresh T and no new/replaced
Q; prior unrelated Q/T/publication entries in C are preserved. Read head/publication refs
in the same transaction, close and export selected immutable ID as today.

| Snapshot | Caller-origin validation delta | Lifecycle |
| --- | --- | --- |
| P | Parents `(Cq,)`; exact Cq tree plus only fresh initial T; T references exact caller Q; no final fields | `working` |
| U | Parents `(P,)`; exact P tree plus matching T publication/result | `working` |
| F | Exact P/optional U and ordered `(P,)` or `(P,U)`; final T preserves initial fields; recorded computation/separate cleanup | `done` after successful retrieval |

Shared role checks still validate Q's actual intent/binding/inputs/root. Both synchronous
completion receive and asynchronous P/U/F receive compare independent expected **Cq/Q**.
A different Q2 with identical values must reject even if packet token/base assertions are
edited to expected. Q occurrence equality without exact Q-content/selected-snapshot equality
is insufficient. Don't relax the original fresh-Q-in-B checks into a universal prefix scan.

Only explicit received refs are created; A's submission and request reservation refs remain
at Cq. They are not moved to P/F or adopted into main. B refs do not transfer; any A-local
Q reservation already present was deliberately created during recording, not copied back.
Full packet suffices with B offline and independent expected; historical source/paths stay
inert. Duplicate validation IO/profile costs remain. No general schema/merge/latest-sync.

## 7. Failures and review choices

- No launch/failed outer-worker spawn before P: A has Q; no fabricated T or outcome.
- Child spawn failure **after** committed P: recorded failure/cleanup F for T is valid done
  once retrieved. This differs from an outer launch error that never created T.
- P/U loss without F remains unknown, possibly forever. Client exits don't relaunch.
- F without receipt can be retrieved; profile/IO error is not a done response or failed Q.
- Wrong Cq/Q, changed worker head, reservation conflict, malformed fields, late storage/
  ref/map-full/commit and response-loss boundaries need full-state/no-dispatch oracles.

Review particularly: explicit two-ref A publication; public builder/first-attempt seam;
strict submission Cq rather than arbitrary historical Q; B-local registration only during
explicit pre-dispatch; pinned Q in expected/descriptor; unchanged bootstrap meaning and
process ownership; no global replay guarantee. These are candidate refinements.

Stop after this vertical slice and independent acceptance. No native/old-spec changes,
request lifecycle/cancellation registry, automatic retry/recovery, scheduler/daemon,
network/cloud, distributed authorization/locking, reuse/facets, resources/GC/excision,
observer/UI, CLI mutation, version bump/migration or later feature. Material scope change
requires a reproducer/proposal and separate approval.
