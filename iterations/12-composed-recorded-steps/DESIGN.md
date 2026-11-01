# Iteration 12 candidate design: composed recorded steps

Status: **reviewed bounded plan; implementation/delegation/publication GO pending**.
The user subsequently stated “reviewed.” This records the review checkpoint for these documents,
not implemented behavior, worker assignment, fixture/build/CI or commit/push permission. Exact
engineering spellings remain refinable; earlier candidate/review-pending statements preserve origin.

Status at preparation: **agreed direction; candidate details for review, no implementation/delegation GO**.
The user agreed to compose two recorded steps and requested the example/handoff. This authorizes
planning here, not DML edits, worker restart, fixtures/builds/CI, commit/push or another feature.
[EXAMPLE.md](EXAMPLE.md) owns the acceptance story; [HANDOFF.md](HANDOFF.md) owns work/evidence gates.
Exact names and helper placement below are assistant recommendations, not an as-built contract.

## 1. Goal and scope

Connect two actual installed Python/DML computations through the existing local Floci adapter:

```text
13,29 -> add -> result sub-DAG R1 rooted in42
R1,2  -> double -> result sub-DAG R2 rooted in84
```

Python controls sequencing. DML records caller requests, distinct attempts, selected producer
provenance, inputs, results and full history. There is no new native add/multiply/call primitive,
generic executable DAG, dependency scheduler or service-managed Batch dependency job.

The slice is primarily an authoring/composition example over existing public APIs. Prefer small
example-local helpers for consumer-basis and summary publication. No new public composition
module is selected in advance. A demonstrably useful narrow shared helper can be proposed during
an authorized turn; a missing owning seam needs evidence/review, not private role-codec access or
a framework added by default.

No cache/reuse/facets, intent/closure registry, automatic retry/recovery/workflow resumption,
parallel/fan-out scheduling, resource management/GC/excision, cloud/AWS SDK/authentication,
observer/UI, native entities, versions/migrations, release/package publication or later turn.

## 2. Existing authorities and planning baseline

- [Python API](../../../dml/docs/spec-next/python-api.md): typed owned descriptions, sub-DAG
  nodes, explicit storage transactions and creating-thread/single-wrapper ownership.
- [Caller requests](../../../dml/docs/spec-next/caller-requests.md): atomic Q/Cq/two refs,
  imported-Q first attempt and exact caller selection.
- [Asynchronous exchange](../../../dml/docs/spec-next/asynchronous-execution.md): public
  selected-history inspector, immutable P/U/F and authoritative explicit-ref reception.
- [Floci](../../../dml/docs/spec-next/floci-execution.md): fixed local HTTP, one-shot dispatch,
  saved external job, manifest-last immutable S3 and job-side process ownership.
- [Transfer](../../../dml/docs/spec-next/transfer.md): complete all-parent typed byte closure,
  original profile and atomic create-or-same-target receive.
- [CLI](../../../dml/docs/spec-next/cli.md): bounded nonexecuting inspection.

Read-only planning inspected clean DML `640cabb05dd9426323069e816621dcbc0c829ae0`, public request
construction, ReceivedObservation/ReceivedRun fields, ordinary DAG/tree/commit operations and
installed example source. No missing C operation is presently indicated. Iteration11 is
[complete/stopped](../11-floci-batch-execution/REVIEW.md); its permissions are not inherited.
The design checkout retains uncommitted prior delivery/planning notes. No implementation or
experiment is claimed by this design.

## 3. Explicit selected-producer input

Use an ordinary named input DAG I2, recommended bindings:

| Name | Node | Meaning |
| --- | --- | --- |
| `value` | Sub-DAG reference to R1 | Actual recorded result supplied to double, not a reconstructed literal42 |
| `producer` | Sub-DAG reference to final attempt DAG T1f | Exact selected producing occurrence/version |
| `factor` | Literal I64 2 | Ordinary consumer argument |
| `endpoint`, `bucket`, `gate` | Literal configured strings | Declared finite local S3 gate inputs |
| `artifacts` if used by fixture | Literal BYTES | Declared installed-runtime assertion data, not complete dependency capture |
| `exit-code` if used by example | Literal I64 | Explicit trusted example failure policy |

Recommend I2 root be the same `value` node. These are **example-local conventions**, not reserved
names, a new node kind or a generic provenance/input schema. Producer is an immutable DAG ID,
not a mutable latest ref, external job ID, serialized Popen or historical scratch capability.

R1 can be content-identical across two producer attempts. T1f preserves which one was selected:
with every other node fixed, changing only `producer` changes I2's full-record ID even when both
value nodes reference the same R1. No reuse identity/mask is inferred from that difference.

The producer selection comes from public validation against independent first-step expected
Cq/Q, and from the SAME received completion description, not incoming consumer claims or bare
manually constructed flags. Require selected F1 already present in A. The input builder checks
its recorded references against the selected description and A's native typed reads. It need
not decode another copy of local role conventions; public inspection supplies those fields.

The double implementation follows `value -> R1 -> root literal I64`, reads `factor`, computes
in Python and publishes R2 through public local APIs. It does not reconstruct R1 from42, execute
T1f, or follow T1f's historical interpreter/scratch/publication-ref strings. `producer` records
an explicit selection witness; it is not automatically interpreted by the native core. The
example/inspector can follow T1f's request/outcome using public DAG descriptions. Recorded links
and captured trusted code do not independently prove scientific causality or complete capture.

## 4. Eligibility is example policy, not a new adapter lifecycle

For this example, build the consumer basis/request only after:

1. First packet is fully validated against independent expected1 and atomically received in A.
2. It is F/completion with `lifecycle == done` and recorded computational `outcome == success`.
3. R1 meets the declared consumer contract: a literal I64 result root, not BOOL/STRING42.

P/U publication42 is ineligible. Done failure with evidence42 is also ineligible. Bootstrap,
unknown/unreturnable F or invalid packet does not become success from service status or time.
No new Q2, T2 or successful summary is invented on these paths.

Computational success and cleanup disposition stay separate. Recommend allowing a valid
successful F with **recorded cleanup failure** to be selected, retaining that disposition in
history; this example policy is not mandatory for other applications. Fixture next-job launch
still requires known owned-writer disposition. Uncertain cleanup/owner is not a permission to
signal historical paths or retire resources. Normal installed story uses cleanup-ok; the policy
edge can be tested with precise host/private evidence without another large fixture matrix.

A failed producer remains a valid recorded failure; a nonnumeric successful result remains a
valid producer success but is unsuitable for this consumer. Neither is reclassified as a
transport error or followed by an automatically fabricated failed consumer attempt.

## 5. Caller basis, request and history publication

Predeclare `add-binding`, `add-inputs` and `double-binding` in basis C0. A contains genuine prior
Q/T/publication history/composite-only children and an independently rooted sentinel as before.

First caller records Q1/Cq1 on C0 and receives F1 under an explicit `add-completion` ref. Then:

- One public A write transaction reads **pinned F1**, preserves its entire tree, adds only I2
  under new `double-inputs`, creates C2 with exactly `(F1,)` parents and creates absent caller
  ref `double-basis`. Prebuild owned response before committing; native abort/ref rules apply.
- Handles close. Existing `record_exchange_request` deliberately records Q2/Cq2 on C2 under
  `submission-double` plus its existing reservation ref. This separate transaction is not
  concealed as atomic with C2/input publication, files or external dispatch.
- `prepare_exchange(request=Q2, commit=Cq2)` and unchanged Floci stages launch one fresh B2.
  B2 imports full selected history, registers only Q2 and creates only T2. Prior T1 is history,
  never an execution instruction. Its source operational refs are not transferred/recreated.
- Receive F2 under explicit `double-completion`, without moving A's existing main/sentinel/
  producer/submission/reservation refs.

Proposed commit spine, arrows mean parent references, not computational data flow:

```text
Cq1 -> C0; P1 -> Cq1; U1 -> P1; F1 -> (P1,U1)
C2 -> F1; Cq2 -> C2; P2 -> Cq2; U2 -> P2; F2 -> (P2,U2)
S -> F2
```

Existing heads stay unchanged except deliberate ordinary application head movement in tests.
Following returned F1 when creating C2 is an explicit new history branch, not automatic adoption,
head synchronization, combining two returned branches or a general merge algorithm.

Ref/name collisions reject before replacing an existing tree entry/head. Same-target packet
receive stays idempotent, but rerunning consumer-basis/request generation is **not** claimed
idempotent: create-only refs reject, and postcommit missing responses require explicit inspection.
No automatic fresh Q2/dispatch/summary to repair uncertainty.

## 6. Successful experiment summary

After validated received successful F2, publish an ordinary DAG E in a new A commit S:

- Root: sub-DAG node referencing R2.
- Named `add`: sub-DAG node referencing selected T1f.
- Named `double`: sub-DAG node referencing T2f.
- Named `result`: the same node as root.

Preserve F2's tree, add only new `experiment` entry, parents exactly `(F2,)`, create absent
`experiment-result` ref atomically with the DAG/tree/commit. No execution/finalization occurs.

Before success summary, verify through public validated selections/native input reads that Q2's
selected I2 has exact R1/T1f/factor2 and that both computations succeeded. An alternate producer
with equal42 is not silently swapped into summary. Summary is a navigational grouping of recorded
selections/results, not a new global experiment status/type, certification or executable plan.

Failed consumer F2 retains its outcome, evidence84 if published and cleanup history; no successful
84 summary is emitted. The final consumer closure already retains selected producer history.
Summary and input references make navigation easier; they do not replace that all-parent history.

## 7. Operational profile and minimal evidence

Reuse the implemented local unsigned Floci profile; no new transport/protocol/profile widening.
After separate GO only, use fresh owned internal network/no ports/exact four services/no9169,
explicit trusted local socket/private volume/current installed byte provenance and attempts1.
All prior containers/volumes were retired; a cached image is not a live fixture.

Keep the computational jobs sequential for this bounded fixture: accept F1 from recorded history,
then independently prove its outer job/container disposition before next submit. That additional
fixture resource policy does NOT redefine DML done as service terminal. Fresh client invocation
is still bounded, with Python/application polling outside the adapter. Consumer source remains
standalone captured entry bytes; no imports of uninstalled example helpers/checkout/PYTHONPATH,
Docker or installed fault hooks. Shared authoring helpers are host-side unless deliberately
installed and included in renewed image provenance.

Mandatory new evidence: actual two-step composition, equal-result selected-producer distinction,
provisional/failed/unknown producer blocks, failed consumer retention, complete bytes/parents and
source/offline inspection, meaningful new A-write rollback/loss for basis/summary, unchanged heads/
old bytes, no recomputation on observation/import. Reuse existing Iteration11 regression authority
and fixed ownership/framing tests rather than copying/rerunning every old fault fixture as a new
claim. Preserve unresolved old Windows causes and bounded reader diagnostics.

## 8. Open engineering choices and next gate

Refinable: example/helper filenames, precise application-local field/ref names, finite driver
modes versus a bounded controller, and whether demonstrated friction warrants a shared Python
helper. No need is assumed for a native operation, another role validator, or a public generic
workflow API. Any genuine missing seam/material scope change needs evidence and a decision.

Next: review this candidate example/design/handoff, then **separate bounded implementation/
delegation GO**. Commit/push/CI authorization also needs to be explicit for the future turn.
No source/as-built/diagram edit, agent assignment, image/fixture/build/test/CI or commit/push was
performed by preparing this plan.
