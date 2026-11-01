# Iteration 11 candidate design: recorded execution through Floci Batch

Status: **IMPLEMENTED, INDEPENDENTLY ACCEPTED, PUBLISHED AND STOPPED through `640cabb`**.
All six final exact-SHA CI jobs succeed; see [REVIEW.md](REVIEW.md), [RESULTS.md](RESULTS.md)
and [COORDINATION.md](COORDINATION.md). The [as-built contract](../../../dml/docs/spec-next/floci-execution.md)
owns actual engineering behavior. Earlier candidate/GO statements below preserve plan provenance,
not permission to restart or begin another turn.

Status at assignment: **Iteration 11 GO and assigned in a fresh session**; coordinator monitoring/independent
review/fixes precede focused worker commit/push and exact-SHA CI. See
[COORDINATION.md](COORDINATION.md). Historical pending-GO statements below are superseded for
this bounded turn; the plan is not an as-built claim.

Status at plan approval: **approved bounded plan; implementation/delegation/publication GO pending**.
The user accepted DESIGN/EXAMPLE/HANDOFF after clarifying the low-level Python orchestration,
recorded intent/binding/inputs and validated-history (not Batch status) completion boundary.
Engineering choices below are now the accepted plan, not implemented behavior; exact spellings
remain refinable. Earlier candidate language preserves planning provenance.
[EXAMPLE.md](EXAMPLE.md) owns the acceptance story; [HANDOFF.md](HANDOFF.md) owns work/evidence
gates. No worker/fixture/build/CI restart or commit/push authorized by plan approval.

## 1. Goal and boundaries

Run **installed DML inside one real Floci Batch job**, publish recorded progress through S3,
and let fresh bounded adapter invocations retrieve that history after the submission client
exits. A records exact request Q/Cq first; B creates only its attempt T; receive preserves
existing A heads/request refs under explicit caller-chosen return refs.

The execution adapter owns submission, observation, retrieval and its declared disposition.
Floci supplies the external job mechanism. Do not introduce a separate DML supervisor subsystem.
A job-side adapter program may own existing local worker processes **inside that Batch job**;
this is ordinary job implementation, not a detached service or scheduler.

Recommended first slice:

- One trusted installed Python/DML job image; single-container job, **service attempts = 1**.
- Explicit local Floci endpoint; precreated bucket/queue/revisioned job definition.
- Immutable full-history input/progress objects, small manifest-last publication.
- Saved external job/independent selection identity, no live caller process to serialize/retain.
- Reuse public exchange/local/transfer authority, not another role/native/job codec.
- Demonstrate real combined execution, fresh clients, failure/evidence, selection/atomic return
  and safe acknowledgement/publication gaps. Service terminal status is never DML outcome.

No AWS/cloud host, SigV4/IAM/VPC/capacity parity, automatic retry/recovery/cancellation, array/
multinode/dependency scheduling, cache/reuse/facets, resource/GC/excision/UI, native primitive,
version/migration, release/package publication or later feature turn. No live-job restart promise.

## 2. What the study proves — and does not

[Floci REPORT](../../feasibility/floci/REPORT.md)/[REVIEW](../../feasibility/floci/REVIEW.md)
are qualified evidence, not an end-to-end adapter implementation. Released **2.3.0**, tag/source
`ee15f502bfc017861b67b076b82e1ccd032c7129`, has real Docker Batch execution. Approved cached
linux/amd64 image manifest:
`sha256:09b72c45f333019adecb302e79c6b746e290135f528016c8514618bc7ab02344`.

Real Node jobs computed13+29=42 after submission clients exited; fresh clients polled the same
job/child, nonzero23 after publication retained bytes. Separate replay transported nine PRIOR
synthetic DML P/U/F packets through S3 and validated/imported them. **No DML ran in those jobs**;
concurrent DML-to-S3 publication, installed combined adapter and acknowledgement-loss behavior
remain to be exercised here. Initial extra-private-EC2/IMDS and negative-oracle corrections stay
qualified, not erased by final exact-profile pass.

Pinned source says no SubmitJob idempotency token; jobName is not uniqueness. Graceful Floci
shutdown stops/removes live jobs; startup reattachment was not found. Persistent records are
not live execution recovery. Cleanup is best-effort; even terminal status does not prove child
removal. Do not replace these gaps with test retries or implied exactly-once/remote survival.

Planning baseline: clean DML **`099d156fb49f81a7da0683898189a85c1172988c`**. Design HEAD28cbff2
has preserved uncommitted Iteration10 delivery and Floci study/status notes. Reinspect before
assignment; no forced reset, unrelated staging or permission inherited from completed turns.

## 3. Recommended transport choice and authority

Recommend an explicitly imported **`daggerml.floci` local-prototype layer**, with fixed Batch
REST-JSON and path-style S3 operations using Python stdlib HTTP. No SDK/global installation,
credential discovery, AWS metadata calls, inherited proxy, redirect following, arbitrary HTTP
method/action/key plugin or generic cloud backend. Dummy local authentication-scope headers are
fixed synthetic inputs; real signing/authentication is **not** implemented or claimed.

This is deliberately **Floci-specific Batch-style execution**, not a production AWS adapter.
A genuine AWS SDK/authenticated transport can be selected in a later authorized design; silently
adding it now would change prerequisites/dependencies/evidence. Exact module/API names remain
refinable; do not build a generic transport framework for hypothetical backends.

Configuration is trusted operational input: explicit http endpoint, bucket, bounded prefix,
queue, exact job-definition revision, expected immutable local worker-image ID and declared POSIX
job interpreter. A fixed bounded DescribeJobDefinitions preflight checks single-container/image
selection; fixture provenance still proves real installed execution, not control-plane assertions.
Reject userinfo/query/
fragment/control/noncanonical spellings; encode bucket/key segments exactly and never accept
incoming endpoint/credential/filename/key substitutions. HTTP calls target only that endpoint.
Fixture isolation, not hostname validation alone, proves no cloud access. Open direct finite
connections without environment-derived proxies, close responses/connections on errors, bound
owned bodies before parsing/materialization; sanitize errors, not payload/credential excerpts.

Owning implemented authorities:
[caller requests](../../../dml/docs/spec-next/caller-requests.md),
[asynchronous exchange](../../../dml/docs/spec-next/asynchronous-execution.md),
[repository execution](../../../dml/docs/spec-next/repository-execution.md),
[local execution](../../../dml/docs/spec-next/local-execution.md),
[transfer](../../../dml/docs/spec-next/transfer.md) and
[Python API](../../../dml/docs/spec-next/python-api.md). These own Q/T/roles/history/validation;
Floci code uses their public descriptions and operations. Preserve original local/SSH behavior.

## 4. Candidate public surface and saved identity

Illustrative operations:

```text
FlociRemote(endpoint, bucket, prefix, queue, job_definition, image, python)
stage_floci_exchange(remote, *, workspace, expected, control, timeout_ms) -> StagedFlociExchange
submit_floci_exchange(staged, *, timeout_ms) -> FlociJob
save_floci_job(new_directory, job) -> None
load_floci_job(directory) -> FlociJob
observe_floci_job(job, *, packet, timeout_ms) -> FlociObservation

# Unchanged authoritative reception of the retrieved ordinary packet:
receive_observation(A, packet=observation.packet, expected=job.expected, ref=explicit_ref)
```

Stage reads closed prepared job/input bytes and public `read_exchange_spec`, requiring caller
Q. It exclusively creates local control and uploads the bounded input objects/manifest; no
SubmitJob, Q/T creation, execution or A writes. Submission is a separate explicit operation.

`FlociJob` owns independent ExchangeSpec, operational remote configuration/control and the
actual acknowledged Batch job UUID. It is not a DML occurrence/content identity, a live Popen,
a cancellation capability or a globally transferable dispatch lock. Save composes public
`save_exchange_handle` for independent expected plus strict Floci metadata written last; load
consults neither endpoint/input/B/A nor process state. Both descriptors retain8192-byte budgets,
exclusive new-directory publication and partial-directory rejection. No duplicate ExchangeSpec
codec. A saved local control path is inert during fresh-client observation, as with SSH identity.

External job ID/attempt1 are also retained in immutable transport manifests linked to the
selected Q/T packet. **This slice does not add those operational fields to local attempt roles
or claim they are new native DML entities.** Ordinary DML history remains authoritative for
computation; retained manifests/saved job preserve the external association outside that graph.

`FlociObservation` can carry the validated ExchangeObservation plus bounded service diagnostic
status/identity. Lifecycle/result/cleanup come exclusively from the packet inspector. No service
status is serialized into the DML completion role. No live caller-owner object is needed.

## 5. One-shot submission and acknowledgement uncertainty

Before SubmitJob: validate config/current local control/staged identity, build fixed command/body
and exclusively create **the local dispatch marker**. Retain it on every spawn/network/status/
parse/response/save error. Repeated submit rejects before another API call. Never auto-clear it.

Submit a fixed installed command (`<declared python> -m daggerml.floci_worker ...`) pointing at
the explicitly staged selection location; no user script/module/command hooks in this adapter.
Force `retryStrategy.attempts=1`, no array/node/dependency/retry-policy options. Endpoint and
queue/definition are already configured; runtime must not provision services/images/dependencies.
Validate the acknowledged job ID/selection and persist a bounded submission receipt. Post-response
local persistence failure may leave a known remote job without a successful saved handle; retain
available acknowledged ID on the error/owned evidence, do not resubmit to repair the receipt.

Lost response can leave a real job even when the caller has no ID. Keep caller Q/staged namespace/
marker/evidence and report uncertainty. **No automatic ListJobs reconciliation/resubmission** in
this turn. Public observation uses an acknowledged saved job; out-of-band inspection of an
ambiguous submission is separate investigation, not permission to recreate a request/attempt.
A copied control/new explicit repository can still submit copied Q elsewhere: no global lock.

## 6. Job-side execution and incremental publication

One installed fixed `floci_worker` entrypoint runs inside the trusted Batch image:

1. Validate actual `AWS_BATCH_JOB_ID`, **attempt1**, fixed operational arguments and bounded input
   manifest. Download closed input objects to newly allocated job-local workspace, hash/length
   check, parse via public `read_exchange_spec`, require exact staged caller Q/selection.
2. Start exactly one fixed existing public `start_exchange(ExchangeHandle(...))`. Retain/reap
   WorkerLaunch. Its installed worker calls unchanged execute/run_request: B imports Cq, registers
   exact Q and creates only T before the computational Python child. No private local/exchange
   calls, duplicate role reader, `retry_step` or replacement Q.
3. While that work proceeds, the job-side program uses public `observe_exchange` to discover
   coherent pinned P/U/F and upload complete closed packets. This loop is **inside the executing
   Batch job**, not an internally polling caller invocation or separate remote service. Fresh
   external observer calls remain bounded. Repeated selected commits need not upload twice.
4. After known local-worker disposition, make a final read-only observation/publication attempt;
   close handles/clean allocated validation packets before reporting successful publication. No
   finalization/repair/reexecution on missing F. On publisher errors retain prior publications
   and own/reap the existing worker; never exit catchably leaving a live unowned local worker.
   Finite trusted child gates and explicit fixture investigation cover uncertain owner disposition;
   no hidden timeout kill of a possibly live computational child for test convenience.

Normal job program returns0 after publishing a valid F, **including recorded computational
failure**. Nonzero job-program status describes transport/bootstrap/publisher failure, not a
fabricated DML outcome. Valid F can coexist with later nonzero job exit; conversely a service
SUCCEEDED without a valid F is still not done. Test both boundaries without installed fault hooks.

B is job-local. Floci removes exited job containers: unlike retained SSH workspaces, an unuploaded
B is **not guaranteed to survive**. Uploaded complete packets preserve selected full history;
unpublished progress/loss remains unknown. No shared LMDB or host path, automatic B recovery,
container-log substitution for history or promise of archive on hard loss. Logs/artifact storage
and external container retirement are separate from recorded local computational scratch cleanup.

## 7. Immutable S3 packet layout — no mutable latest record needed

Recommend deterministic keys under a fresh token-derived prefix, with **one trusted publisher**:

```text
<scope>/<token>/input/job.json
<scope>/<token>/input/input.bundle
<scope>/<token>/input/manifest.json              # last, create-only
<scope>/<token>/snapshots/<commit>/job.json
<scope>/<token>/snapshots/<commit>/observation.json
<scope>/<token>/snapshots/<commit>/snapshot.bundle
<scope>/<token>/phases/<initial|publication|completion>.json  # each last, create-only
```

Input manifest pins file names/lengths/SHA256; phase manifest also pins actual external job/attempt1,
transport token/base, phase and selected immutable commit. Job/input/observation codecs stay
exchange-owned; no transported success/done/result claim. Keys derive from saved scope/token and
validated phase/commit, not arbitrary incoming paths. All file bodies are owned once before PUT
or validation. Digests detect byte substitution, not authentication/truth.

Recommend `If-None-Match: *` create-only object PUTs. Released S3 source checks conditions under
storage locking, but actual conditional-write/same-target/conflict behavior **must be tested**;
study ordinary PUT/GET is not that proof. Repeated already-published same bytes may be explicitly
read/compared, never silently overwritten. Input/stage publication remains one-shot; response loss
can retain partial/full objects. No filesystem/object-store/Batch/DML spanning transaction.

No multi-writer CAS/distributed reservation/latest-progress protocol. Host observation reads up to
three fixed phase manifests (F, U, P preference); absence of a phase object is not failure. It pins
one manifest and downloads that selected commit's fixed files once. F arriving after selection
cannot retarget U; no monotonic-newest guarantee. Fast work may publish only F: its all-parent
history still includes P/accepted U, but there is no fabricated observation of missed phases.
Gated acceptance requires P/U/F each really observed/published.

Descriptors/header/manifest retain8192-byte limits; bundles retain the owning32MiB/profile bounds.
Exact int lengths (not bool), lowercase IDs/digests, duplicate/missing/unknown/deep/UTF8/oversize
JSON rejection, fixed file set/order and strict received-byte counts/hashes/EOF are required.
Limits are not exact RSS/disk/deadline quotas. Keep original limits+one, not only smaller mocks.

## 8. Bounded observation, done and reception

An invocation makes a fixed bounded number of direct HTTP calls, no waiting for job completion
or polling loop. It can describe the saved job for diagnostic identity/status, then select an
immutable phase manifest and fetch its fixed bodies. Specify overall/per-call timeout accounting,
close connections on all paths, and acknowledge ordinary filesystem/native/process calls lack
portable hard deadlines. A failed HTTP call is not permission to submit again.

No manifest yet: working/bootstrap with no packet/snapshot, even if the service reports terminal.
Manifest exists but a file is missing/truncated/mismatched or selected history invalid: error,
not disguised bootstrap/failure/done. Wrong service job identity/attempt count errors likewise do
not invent DML outcomes. No successful packet until complete bounded closed bytes are validated
through public `read_observation` against independently owned exact Cq/Q.

Host validation scratch must be disposed before allocating the final new caller packet. Publish
owned job/snapshot/observation files with receipt last; retain manifest association as a separate
bounded operational file. No A write during observe; concurrent readers use different packets.
Existing `receive_observation` revalidates the SAME owned packet bytes/authority before atomic
explicit-ref import. It requires no Floci/S3/input/B/image/source/live application. Existing main,
submission/Q/sentinel refs stay unchanged; no copied B refs. Same-target repeat is nonexecuting;
P-ref-to-F conflicts, never implicit advancement. Publication remains provisional; computational
and local cleanup outcomes remain separate. `done` is validated retrieved F, not Batch status,
outer job exit or A receipt. Service-owned container cleanup/retained objects are not secretly
folded into that local cleanup role or claimed complete by terminal status.

## 9. Local fixture/profile and work ownership

Future GO must authorize the bounded local fixture/build explicitly; feasibility permission is
complete/stopped. Reuse cached pinned Floci/private internal-bridge/no-host-ports profile, robust
all128 enable-key enumeration/exact four-service check and actual no9169 binding BEFORE submission.
Socket authority is daemon-root-equivalent despite nonroot/cap-drop; pinned trusted emulator and
finite trusted jobs only. No project/A/source/exchange/credential mounts. Use explicit local socket,
new owned IDs/namespace/private data volume, no global service/firewall or exposure workaround.

New requirement vs Node feasibility: build an offline **current installed DML Python job image**
from existing cached bare Nix closure/current reviewed wheel route, no registry push or base pull.
Candidate DML job memory512MiB (not the study's Node128MiB); source/worker/extension/CLI/closure/image
bytes must be proved. Register the new local image by immutable sha256 image ID, never a tag that
would permit hidden Floci image pulls. Floci does not enforce child CPU/PID caps; service cap-drop/
no-new-privileges settings do not automatically apply to spawned job containers either. Inspect
actual job user/caps/security/memory/privilege/mounts and qualify trusted finite multi-process DML
workload, not adversarial confinement. Client processes may run in owned private-bridge containers using copied inputs/saved
identity; Docker control stays fixture-only. Neither runtime library nor captured computation may
import Docker/test hooks. Missing tools/caches/build material/downloads need scoped user decision.

After safe pre-spawn or after-actual-reap barriers only, prove every acquired client/worker/job child
stopped before Floci stop/restart/archive/retirement. Terminal API status is insufficient: independently
verify exact correlated container IDs/namespace. Uncertainty retains owned fixture/evidence as a
blocker. Archive B/packets/diagnostics while available, not arbitrary historical paths; no global prune.

Future existing window-2 worker owns runtime/tests/as-built/example/fixture/RESULTS; coordinator owns
independent REVIEW/COORDINATION/design status. Worker exclusively owns both shared builds through
fresh baseline/implementation; explicit source freeze/release precedes independent checks. Publish
only after independent acceptance and separately authorized focused commit/push/exact-SHA CI.

## 10. Open engineering choices and stop

Names/strict descriptor schemas/connection budget accounting/local acknowledged-ID error shape,
phase publication ordering and image/client packaging are refinable within the bounded plan.
If create-only S3 semantics or a public owning seam is genuinely missing, present evidence and
narrow scope decision; do not expand to SDK/authenticated AWS/native/general recovery by default.

Stop after combined installed actual DML-in-Batch acceptance, standard checks/independent review
and the authorized publication gate if separately granted. Service lifecycle/storage/cleanup gaps
remain honest limitations. Planning alone authorizes none of those operations.
