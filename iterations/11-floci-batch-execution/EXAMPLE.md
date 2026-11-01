# Iteration 11 worked example: one DML computation inside a Floci Batch job

Status: **BOUNDED STORY DELIVERED/INDEPENDENTLY ACCEPTED/PUBLISHED AND STOPPED through `640cabb`**.
All six final exact-SHA CI jobs succeed. [RESULTS.md](RESULTS.md)/[REVIEW.md](REVIEW.md) distinguish
actual normal installed story/private probes/independent checks and retained qualifications;
this worked plan is not the owning as-built API. No restart/later turn authorized.

Status at assignment: **Iteration 11 GO; this acceptance story is assigned, not yet demonstrated**.
Coordinator independent acceptance precedes focused worker commit/push/exact-SHA CI; see
[COORDINATION.md](COORDINATION.md). Earlier pending-GO statements preserve plan provenance.

Status at plan approval: **approved acceptance plan; not executed, implementation GO pending**.
The user accepted DESIGN/EXAMPLE/HANDOFF. Earlier candidate phrasing preserves planning origin;
exact engineering spellings remain refinable, not as-built behavior.
[DESIGN.md](DESIGN.md) owns proposed mechanics; [HANDOFF.md](HANDOFF.md) owns evidence/work gates.
[Feasibility](../../feasibility/floci/REPORT.md) tested real Node jobs and PRIOR packet replay
separately. This story must demonstrate actual newly produced DML history inside Batch.
API/image/schema spellings remain engineering recommendations for review.

## 1. Explicit local service and trusted installed job

After separate GO only, use cached pinned Floci2.3.0 in a new owned private internal bridge:
no host networking/published ports, exact Batch/S3/CloudWatchLogs/IAM services and actual no9169
IMDS listener checked before submission. Local Docker socket authority is explicitly trusted,
not a sandbox. No project/A/source/exchange/credential mounts or cloud endpoints. Fixture owner
creates queue/revisioned definition/bucket; the runtime adapter provisions none of them.

Build an offline job image containing **current installed DML**, explicit `/opt/dml/bin/python`
and exact native/worker/module bytes. This is new bounded image work, not permission to reuse
an old source wheel by name. Candidate DML memory512MiB; child CPU/PID limits remain unenforced
by Floci. Finite trusted processes and image/native/closure provenance must be verified.

The caller can create A on the host and copy closed staged files/saved identity to private-bridge
clients. Fresh installed client processes use explicit local HTTP endpoints; no source imports/
PYTHONPATH/shared A or live application/SSH connection is required during execution. The fixture
controller may use Docker cp/exec solely for owned evidence/gate control, never as runtime history
transport. Objects and progress actually travel via S3.

## 2. Record what was requested before submission

Fresh A has C/main, sentinel, genuine unrelated prior Q/T/publication history and composite-only
children. Keep all old reachable bytes. Trusted captured source declares:

- left13/right29, image interpreter and public local child/publication contract;
- explicit local S3 endpoint/bucket/test gate keys as ordinary named inputs;
- finite out-of-band gate waits before computation and after result publication;
- no Docker import, inherited real credentials/cloud endpoint or hidden test/runtime hook.

Source asserts installed image/interpreter/native provenance, constructs a result sub-DAG rooted
in42 and named result, and publishes it through existing public local APIs. A second source/job
publishes the same result then exits23; publication must remain evidence, not silent success.

A deliberately calls `record_exchange_request` under `submission-1`: Q/Cq with exactly `(C,)`
parents and only Q added. Fresh Python/CLI inspection confirms no T/outcome, submission/Q refs at
Cq. Record a separate never-started Q. Prepare with exact Cq/Q; snapshot main/sentinel/request
refs and all old typed packed objects before upload.

## 3. Stage bytes, submit once, exit the submitting client

Illustrative caller sequence:

```text
expected = prepare_exchange(A, commit=Cq, request=Q, ..., workspace=inputs)
staged = stage_floci_exchange(remote, workspace=inputs, expected=expected,
                             control=new_control, timeout_ms=budget)
job = submit_floci_exchange(staged, timeout_ms=budget)
save_floci_job(new_saved_directory, job)
```

Stage uploads exact closed input bundle/job and publishes input manifest last, without executing.
Independent S3/API/fixture inspection sees no Batch job/T from stage. Saving/loading identity does
not connect/dispatch. Existing/partial destinations reject; stage failures leave Q recorded.

Move A and original prepared inputs offline. Submission creates its local dispatch marker before
SubmitJob, force attempts1, receives actual external job ID and exits its client while the real
Batch job remains gated. A second submission for that control rejects before another API call.
No WorkerLaunch/SSHLaunch or live submitting owner crosses the client boundary.

The installed job-side adapter downloads/validates input, owns one public fixed local worker,
and B registers that **same Q** then creates only T. External Batch ID/attempt1 remain operational
saved/manifest association, not a new DML occurrence or renamed local role. Fresh clients never
register Q, recreate T or repeat submission merely because no packet is available.

## 4. Observe actual P and U from fresh clients

A fresh installed observer loads only saved independent identity:

```text
observation = observe_floci_job(load_floci_job(saved), packet=new_packet,
                               timeout_ms=transport_budget)
```

Each call is bounded, one selection/retrieval, no internal wait for completion. Before first
publication it may report working/bootstrap/no packet; service status alone asserts no outcome.

Retrieve **P/initial** while the child is gated before arithmetic:

- working; exact Q and one new T relative to Cq; P parents `(Cq,)`;
- no final fields/computation/cleanup; P is not proof of external dispatch;
- S3 immutable phase manifest links acknowledged Batch job/attempt1 and selected P;
- packet files/hash/length and public selected-history validation succeed without A writes.

Repeat observations from clients that exit. Check same Batch job ID/single owned job child,
no additional Q/T/ref/object mutations due to observation. Independent public all-typed/every-
packed-byte/all-parent oracles compare selected actual B and fetched packet validation store.

Fixture controller releases only initial gate through declared S3 gate object. Retrieve
**U/publication** while child remains at the second gate:

- working, provisional result42, exact same Q/T/initial field nodes;
- U parents `(P,)`; local attempt has no final status/outcome;
- P packet and S3 immutable objects remain byte-identical.

Concurrent observers allocate distinct local packets. Publication of F between manifest selection
and file retrieval cannot retarget pinned U; no monotonic-newest order is claimed. Fast ungated
jobs may skip observable P/U but final complete history still preserves them.

## 5. Final recorded history is not Batch terminal status

Release publication gate. Job-side DML runner reaps the computational child, attempts local
scratch cleanup and records **F**. Adapter publishes complete immutable F packet, phase manifest
last. Fresh client reports done only after public exact-Q/full-history validation:

- same Q/T; final T preserves initial field nodes, ordered parents `(P,U)`;
- successful computation42 and separate cleanup disposition, not a service boolean;
- old P/U packets stay working; no A return ref yet.

For nonzero23 AFTER U, F records computational failure with result42 as evidence and cleanup
separately. The outer adapter job can complete successfully after publishing this recorded failure:
Batch SUCCEEDED is not the DML computational outcome. Conversely safe after-reap/post-F outer
response loss/nonzero job exit can coexist with already available valid F/done.

Use a **separately labelled private fixture wrapper/barrier after actual reaping** where needed
to inspect/copy final job-local B before Floci automatically removes its job container. Never
install fault hooks or keep a live computational child merely for a loss experiment. Actual
normal installed-helper evidence remains distinct from private lifetime/evidence barriers.

## 6. Service unavailable, existing explicit-ref receive

After proof all owned writers stopped, archive required B/packets/service evidence and stop the
endpoint. Restore A and advance main independently. Fresh installed receiver uses downloaded
packet plus independently saved selection only:

```text
receive_observation(A, packet=P, expected=job.expected, ref="trial-1-initial")
receive_observation(A, packet=U, expected=job.expected, ref="trial-1-publication")
receive_observation(A, packet=F, expected=job.expected, ref="trial-1-completion")
```

All typed objects/every packed byte/all parent history agree with original B/packet store;
prior research/main/sentinel/submission/Q refs and bytes stay unchanged. B operational refs do
not copy. Explicit same-target repeat is nonexecuting; F under existing P ref conflicts/aborts
new batch, not implicit advancement. No service/input/image/source/historical path is consulted.

Run two matching submissions against the same C/binding/inputs after prior child reaping and
gate reset: distinct Q/T and external job IDs, equal result content. The never-started Q remains
without an attempt. Keep first-run packets exact throughout the second/failure jobs.

## 7. Ambiguity, corruption and real boundaries

Required negative evidence, real where possible and explicitly labelled otherwise:

- Before SubmitJob transport failure: Q/stage/marker retained, no automatic submit. Accepted job
  with lost acknowledgement: independently prove exactly one job/attempt, caller reports unknown
  and refuses repeat; no hidden ListJobs repair. Use finite private client response suppression,
  release gates/reap actual job afterward, never kill its live child for convenience.
- A create-only object conflict or upload failure before phase manifest yields no successful new
  publication. After remote manifest commit but lost response, fresh observe can retrieve already
  stored immutable history; no reexecution. Existing objects never overwrite silently.
- Manifest/profile/count/hash/phase/job/attempt/root mismatch, missing file despite manifest,
  duplicate/deep/UTF8/oversized data, wrong-Q swaps and typed-complete expected-Cq/T-to-another-
  matching-Q association reject before host packet success/A writes. Do not rely only on absent Cq.
- Service FAILED/SUCCEEDED with no valid F remains unknown/working, not fabricated completion.
  Genuine original transfer-profile overflow after B F supplies no successful done packet.
- Validation scratch/packet/object IO errors; new actual-A puts before late ref/raw-ref/map-full/
  consuming-commit failures; real pre/post-A-storage-commit interruption distinguish absent batch
  from complete import despite missing response. Receive retry is never another computation.
- Original Windows old-story unknown failures/diagnostic notes remain visible; do not alter old
  runtime/examples just to hide recurrence without a reproducible within-scope finding.

## 8. Evidence, retirement and stop

Prove exact current installed modules/native/image/closure/file bytes, no shared mounts/source
path, exact four services/no9169/internal network/no host exposure before any computational submit.
Mandatory actual combined DML gate cannot be replaced by Node feasibility, mocks or CI. Host
coverage is not installed job instrumentation/AWS parity/physical host/restart/authentication proof.

All catchable errors preserve acquired owners, release owned finite gates and independently prove
job/client disposition before stop/restart/retirement. Floci terminal status alone is insufficient.
Retain fixture/evidence as blocker if unknown; exact identity-checked owned removal only, no prune
or arbitrary PID/historical scratch signalling. Uploaded history/artifact retention is separate
from local computational cleanup. Stop after the authorized slice; planning grants no operations.
