# Versioned reuse selection and explicit adoption

Status: informative, implemented **example-local** convention over existing public APIs.

## Authority boundary

This page owns [reuse_selection.py](../examples/reuse_selection.py), not a public selection
framework, default cache, native entity or new adapter role. [Explicit reuse](explicit-attempt-reuse.md)
owns its existing ordinary Q/W association; [caller requests](spec-next/caller-requests.md)
owns Q publication. [Asynchronous exchange](spec-next/asynchronous-execution.md#immutable-packets-and-independent-reception)
owns strict public packet/expected/history inspection, [transfer](spec-next/transfer.md) owns complete
typed all-parent closure/profile and [Python API](spec-next/python-api.md) owns native storage/lifetime.
Fresh execution uses unchanged [Floci](spec-next/floci-execution.md) or local adapter operations.

## A recorded choice, not another trial

The [composed example](composed-recorded-steps.md) executes add13+29 → result sub-DAG42,
then double consumes that actual result and exact producer attempt witness → result sub-DAG84.
The selection example deliberately records which successful double attempt to reuse. Selection
and adoption create **no computational request, attempt, outcome, cleanup or external job**.
They do not count another empirical observation or authenticate who made the choice.

Initial matching is exact **intent URI, full binding DAG ID, full input DAG ID**. This includes
source/interpreter/timeout and producer witness/factor/types/all declared input values. Equal42/84
never substitutes an occurrence. Containing commit, transport token and request occurrence are
not matching dimensions. No mask/facet/default/search/index or cross-implementation rule is added.

## Durable ordinary S/V

An explicitly named tree slot (illustratively `selected-double`) holds ordinary selection S:

| Binding | Node |
| --- | --- |
| `role` | literal STRING `example-reuse-selection-v1` |
| `intent` | literal canonical URI |
| `binding`, `inputs` | sub-DAG references to full computational dimensions |
| `request` | sub-DAG reference to ORIGINAL producing Q |
| `attempt` | sub-DAG reference to exact selected final T |
| `result` | sub-DAG reference to actual R; also S root |
| `completion` | literal BYTES, exact16-byte F ID |
| `validation` | sub-DAG reference to V |

V has exactly literal BYTES `expected`, `job`, `observation`; root is `expected`. These are opaque
existing public HANDLE/job/observation framing, **each at most8192 bytes**, not another JSON-role
codec or duplicate full-history bundle. `expected` comes from an independently caller-owned saved
Cq/Q selection, never an incoming receipt. Capture uses read(limit+1), then validates the SAME
owned immutable copies and persists them without original-file rereads. Bundle capture keeps the
owning32MiB limit. IO is not a filesystem/multi-file transaction or hostile-writer capture guarantee.

The literal F ID is **metadata, not a native commit edge or retention root**. F must be reachable
through the pinned basis's ALL-parent history. Complete public export validates every reached typed
native record and composite-only child under unchanged transfer limits. Ordinary parent links retain
that history; S/V are not new LMDB boxes or keys.

A pinned reader checks exact native S/V field sets, root, node/datum types and metadata bounds;
closes native handles; exports retained exact F; writes a fresh owned packet using stored headers;
loads expected through the public loader and calls public packet inspection. EVERY S computational/
Q/T/R/F claim is compared against those owned public fields. Supplied descriptions/flags never
supply authoring authority. The serialized historical workspace remains inert: never observe/start/
stat/delete it, run historical source or signal a process. Native record reads still allocate under
existing public read semantics before application-level header-length checks;8192 is not a native
read-size/RSS bound. No new native bounded-read primitive is claimed.

Trusted pinned repository state supplies the persisted expected choice. A fully coherent valid
alternative is a different deliberate recorded selection, not detectable fraud against unstated
intentions. Partial witness/Q/F/header swaps, malformed framing/history, P/U, failed F evidence84,
unknown/missing/unreturnable F and damaged closure reject. Computational success with **recorded
failed cleanup** remains eligible under explicit historical policy, never repaired/reclassified.

## Explicit operations and distinct boundaries

- `select`: pinned C/explicit absent slot, full matching/retention/public validation BEFORE puts.
  One atomic A storage transaction preserves C's tree/adds only S, creates Csel with `(C,)` parents
  and create-only explicit ref. Response is allocated before commit. Capture/validation scratch
  is disposed before opening the authoring write.
- `inspect`: pinned C/explicit slot, repository-only revalidation. Creates no DML records/refs/Q/T.
  Export/materialization costs temporary IO; ORIGINAL packet/expected/input/B/service are unnecessary.
- `reuse-selected`: resolves THAT S and matches requested dimensions BEFORE Q; delegates to the
  unchanged existing Q/W operation using its newly owned packet/expected. New Qr/Cqr parent pins
  selection-bearing C and known slot; W links exact old T/R. There is **no direct W-to-S edge** or
  extra third publication transaction. Q and W remain separate, and W failure can leave pending Q.
- Explicit fresh execution separately records Qfresh/stages/submits/observes/receives. It imports S0/
  V0/W0 inertly and creates only Tfresh. Equal result does **not** adopt or change S0/earlier W.
- `adopt`: revalidates old S0 from persisted basis AND independently captured new successful F.
  Requires same dimensions, a distinct **attempt occurrence** from owning public
  `ReceivedObservation.attempt_id`, and both supporting histories retained. Exact final-T content
  remains the selected witness; another valid final description of the same occurrence is NOT
  fresh work, even with a different T/F ID. Owned Selection responses expose validated `attempt_id`
  without adding a native S/V field. One atomic
  A batch preserves tree except THAT slot→new S1/V1, creates Cadopt with `(C,)` parents/create-only ref.
  The already-selected occurrence rejects as no-op policy. No Q/T/job or old-object/ref rewrite.

A sibling Ckeep with C's unchanged tree and `(C,)` parent preserves S0; Cadopt preserves S1. Explicit
requests on the two branches reuse different selected attempts despite equalR84. Neither branch is
a repository-global winner; ref movement/annotations do not retarget immutable pinned choices.

Late ref/allocation/real map-full/consuming-commit failure aborts each S/V publication batch. Pre-store
commit authoring loss leaves no batch; postcommit lost response can leave complete publication.
Inspect explicit refs; conflicts do not authorize repair/automatic new Q/adoption/fresh work. Q/W,
files and service effects are **not one transaction**. Reuse projection files live through delegation;
their cleanup can fail AFTER Q/W publication, leaving complete Q/W without a successful response.
Do not infer whole-operation rollback or duplicate Q. Inspector/capture cleanup failure BEFORE
select/adopt blocks publication. No distributed exactly-once/idempotent whole-driver promise.

## Finite offline modes

Copy both example files together when running outside the checkout; they import installed DML and
stdlib, not Floci/HTTP/Docker. Initial packet/independent expected is needed only for capture:

```sh
python examples/reuse_selection.py select A.dml <C> selected-double \
  double-binding double-inputs urn:example:double independent-expected.json old-F selection-old
python examples/reuse_selection.py inspect A.dml <Csel> selected-double
python examples/reuse_selection.py reuse-selected A.dml <Csel> selected-double \
  double-binding double-inputs urn:example:double reuse-submission reused-double
# Separately use existing request/stage/submit/observe/receive for explicit fresh execution.
python examples/reuse_selection.py adopt A.dml <fresh-F> selected-double \
  double-binding double-inputs urn:example:double fresh-expected.json fresh-F-packet adopt-fresh
```

Each call is one finite explicit action, not an evaluator, polling driver or provisioning tool.
Ordinary inspection uses `dml ... snapshot`, `walk <S>` and `log --commit <C>`; bounded CLI output is
not exhaustive integrity evidence. Branch authoring and application sequencing remain caller policy.

## Evidence and limits

[Native selection](../tests/python/test_reuse_selection.py),
[shape/capsule/branch gates](../tests/python/test_reuse_selection_records.py),
[actual-new-row atomicity/authoring-only loss](../tests/python/test_reuse_selection_atomicity.py),
[finite modes/matching/scratch faults](../tests/python/test_reuse_selection_modes.py) and
[default-safe controller](../tests/python/test_reuse_selection_fixture.py) start no Docker.
The separately mandatory [actual installed three-job/nine-phase gate](../tests/floci/README.md#versioned-selection-and-adoption-gate)
distinguishes real S3/Batch/available gated B native bytes from offline selection/reuse/adoption/
branch readers and external all-status/persisted job census. Normal final B remains ephemeral.

Unchanged root-source coverage/memory gates retain the example. Host statements are not every branch,
installed-child/platform/process-memory/security/full-environment/scientific-validity assurance.
Content IDs are not authentication. Existing unsigned-local Floci/socket/job-security/cleanup/profile/
ephemeral-B limits persist. Exact commands, provenance, original failures, tested versus substituted
faults, mutation/Windows UNKNOWN qualifications and independent review belong to
[Iteration14 RESULTS](../../dml-design/iterations/14-versioned-reuse-selection/RESULTS.md) and
[REVIEW](../../dml-design/iterations/14-versioned-reuse-selection/REVIEW.md).
