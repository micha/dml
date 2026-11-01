# Floci feasibility — decision report

**Verdict: viable with constraints for bounded real-job submission/fresh polling and
byte-preserving history transport. An end-to-end DML-in-Batch adapter remains unverified.**
Floci can replace the *foreground connection lifetime* with an external service-owned job;
it does not establish durable host-loss execution, exactly-once dispatch, AWS equivalence,
or DML completion from service status. Recommend one small separately approved Iteration11,
not a production integration or a new DML supervisor. Study complete/stopped; no commit/push.

## Evidence and provenance

- Primary release **2.3.0**, published **2026-10-15**, tag resolved to
  **`ee15f502bfc017861b67b076b82e1ccd032c7129`**. This released source actually contains
  `BatchDockerRunner`; findings below are pinned to it, not moving `main` or marketing.
  Earliest introducing release was not established.
- Context7 `/floci-io/floci` Batch runner/storage queries guided discovery; its moving-main
  snippets were corroborated against pinned primary source. [Release](https://github.com/floci-io/floci/releases/tag/2.3.0),
  [Batch docs](https://github.com/floci-io/floci/blob/ee15f502bfc017861b67b076b82e1ccd032c7129/docs/services/batch.md),
  [service](https://github.com/floci-io/floci/blob/ee15f502bfc017861b67b076b82e1ccd032c7129/src/main/java/io/github/hectorvent/floci/services/batch/BatchService.java),
  [runner](https://github.com/floci-io/floci/blob/ee15f502bfc017861b67b076b82e1ccd032c7129/src/main/java/io/github/hectorvent/floci/services/batch/BatchDockerRunner.java).
- DockerHub `2.3.0` index:
  `sha256:e0b292df4dc9559b7b1bf4f51bdda4bb8e269276236438cd03cae661260ea8a9`.
  Approved **only** linux/amd64 manifest pull:
  `docker.io/floci/floci@sha256:09b72c45f333019adecb302e79c6b746e290135f528016c8514618bc7ab02344`.
  Public manifest SHA256 verified; compressed layers **86,782,013 bytes**. Pull exit0;
  Docker image `Size` **345,463,540 bytes (~329.5 MiB)**, not exact allocated disk usage.
  Postpull OCI revision/version labels match the pinned source/2.3.0 **before execution**.
  This is vendor-image provenance/integrity, not independent binary reproducibility or
  verified signature/attestation. Prepull config-blob HTTP400 is retained; local inspect resolved it.
- Existing local daemon **Docker29.8.1**, `michas-robots`, x86_64, `/work/docker`, explicit
  `unix:///var/run/docker.sock`, socket GID**131**. Job/client image reused without pulling:
  cached Node24.13.1 image **`sha256:00e9195ebd49985a6da8921f419978d85dfe354589755192dc090425ce4da2f7`**.
  No SDK installation: Node built-in HTTP, explicit local endpoints, synthetic identity headers;
  signature validation/IAM enforcement were off. **Not an AWS SDK/authentication parity test.**

Reproducible owned probes: [probe.py](probe.py), [replay.py](replay.py). With the already
approved cached image/profile and pinned `runtime/sources/release/.../application.yml` present:

```sh
python3 -B feasibility/floci/probe.py --accepted-private-profile
# Optional approved PRIOR packet replay, requiring the retained synthetic corpus/wheels:
env -u PYTHONPATH ../dml/build/iteration10-owned/context/rootfs/opt/dml/bin/python -B \
  feasibility/floci/replay.py prepare feasibility/floci/runtime/new-replay
python3 -B feasibility/floci/probe.py --accepted-private-profile \
  --prior-packet-replay feasibility/floci/runtime/new-replay
env -u PYTHONPATH ../dml/build/iteration10-owned/context/rootfs/opt/dml/bin/python -B \
  feasibility/floci/replay.py validate feasibility/floci/runtime/new-replay
```

These commands document bounded reproduction, **not permission for further runs/pulls**.
Prior corpus/runtime/wheels are machine-local prerequisites, not supplied in a fresh clone.
All raw evidence, source copies, logs, data and packets remain ignored under `runtime/`:

| Evidence | Result |
|---|---|
| `probe-profile-final.{log,exit}`, `run-dbc7788721ca459da14127abc55cf89c/` | Final corrected real Docker gate, **exit0**, retired |
| `replay-transport.{log,exit}`, `run-2736fc12f67b4d91a2bdaa805f70a4ed/` | Real S3 transport of prior DML packets, **exit0**, retired; extra-private-EC2 qualification below |
| `replay-prepare2.{log,exit}`, `replay-validate2.{log,exit}`, `replay-validated/` | Fresh nonexecuting installed-client validation, **exit0** |
| `source-evidence.json`, `sources/`, `image-inspect.json`, `pull.{log,exit}` | Hash index of132 primary-source/metadata files and exact approved pull |

Final real-gate `summary.json` SHA256:
`5ebc6aef4718c36745fcb754f951b9eafba3b20309ea50e704b641fe677879d7`;
`commands.json` **`92885e33840414fd50c3be7e1998639989962f71bbcc23b49e97fb1223253d4b`**
records every exact argv/output/exit (**276 Docker commands**, including setup/inspection/retirement,
not276 tests). Final probe SHA256 `ec68c8788e8107267e7540f600bfed6a115953eab2920d050cc40e4f1187ef53`;
replay SHA256 `799c77fd76360d5d30de3f09724ac452f38b5ab757ff409f30481082776e1868`.

## Actual real-job evidence — not `immediate` simulation

Final fixture **`dbc7788721ca459da14127abc55cf89c`**, service Docker ID
`83849937e565306937672e10f5e2d6c0ed449e8bcce1374dccdb98d0261e1b5c`:

| Actual Batch job ID | Computation | Service outcome |
|---|---|---|
| `4f93be62-25fd-4b92-b0a0-5894b54371c3` | S3 input13+29, real Node result42 | `SUCCEEDED`, exit0, one attempt |
| `76c7a7d4-2481-47f6-accb-dc49b806dd19` | Same computation, progress/result uploaded before natural exit23 | `FAILED`, exit23, one attempt; published bytes retained |

For each job: bounded SubmitJob client returned/exited/reaped **before gate1 release**;
real Docker child remained running/gated; independent fresh DescribeJobs clients repeatedly
polled the same ID and same single container. Polls did not compute/relaunch. External S3 gate1
release allowed computation; gate2 retained RUNNING after progress publication. Result42 and
SHA256 of **4096 S3-fetched binary bytes** were computed in the child, not supplied as results:
`c8f5d0341d54d951a71b136e6e2afcb14d11ed8489a7ae126a8fee0df6ecf193`.
Job/attempt environment (`AWS_BATCH_JOB_ID`, attempt1), nonce, container/resource-ID labels,
exit and attempt records agreed. Final child IDs/complete inspections are in the summary.
**40 finite one-shot clients** exited; gates have60s cooperative limits and finally releases.
No timeout/cancellation, live-child kill, execution-channel disconnect, or loss injection.

Floci removed each naturally exited child; independent namespace census confirmed absence
before service stop. Clean **after-reap** restart of the same retained Floci container/private
volume preserved exact final DescribeJobs records and computed S3 result bytes. This tests
ordinary clean storage restart, **not** live-job restart, emulator/host crash or durable lifetime.

## Prior DML history replay — distinct evidence

Only known synthetic Iteration10 coordinator corpus `/tmp/dml-iteration10-independent-story`
was selected: three trials (two successes42, one failure23), each original P/U/F packet;
no old repository/credential/SSH endpoint was opened operationally. Independent expected
Cq/Q came from old caller preparation descriptions, not incoming packet claims. Captured source
was **never executed**. Current reviewed wheel hashes match Iteration10 RESULTS:

- core `767d1032c73f335588f47053cefe4b6f023adf7242ed8975940071aed6394385`;
- CLI `f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`.

Existing cached installed Python client was used read-only; all**13 package artifact bytes**
agreed with reviewed wheels, maintained Python bytes with current read-only DML checkout.
No install/download/build/check/coverage/CI or original-store writes.

Real Floci S3 PUT/GET transported **27 original whole files /115,022 bytes**
(`job.json`, `observation.json`, `snapshot.bundle` for9 packets). Every fetched byte/hash matched
before public `read_observation` and `receive_observation` in a **new study A**. Independent
public breadth-first traversal compared **all typed packed objects/all parents** to the original
complete bundle rows and imported validation stores (**603 rows across9 packets**, duplicates
across packets not603 unique objects). P/U stayed working; F preserved success/failure,
provisional evidence and separate recorded cleanup. Explicit return refs, idempotent repeats,
unchanged sentinel/main and six submission/request refs, old reachable bytes, and absence of
copied B worker/attempt refs passed. Wrong-phase inspection/receive rejected with ExchangeError;
wrong matching-Q packet with rewritten transport claims rejected with **NotFoundError for absent
independent Cq**, not a deeper T-to-Q association-specific oracle. Both left actual A bytes unchanged.
P-ref-to-F conflict likewise left A unchanged. Five expected negative outcomes total.

This proves **packet transport + installed public inspector/receive replay of PRIOR execution**,
not DML executing in a Floci child, concurrent DML publication through S3, a new adapter,
or a complete end-to-end exact-Q Batch execution pass. Per-file source/hash/selection is in
`replay-validated/selection.json` (SHA256
`dca1adea304b3a1288436bd0d8d0138682d213049ea621bb3bcc3e1b37e1e78c`);
result SHA256 `a126ffa3756f29f0a0684abd4cffb7fc1370f32379239444d320c04c38d40c3a`.

## Source-established behavior and gaps

Pinned primary implementation, not additional runtime passes:

- `BatchService.submitJob` lines568+ stores a fresh UUID job, then `dispatchRun`838+
  launches a virtual thread in **docker** mode. `describeJobs`866+ reads only stored details;
  no dispatch path. Default **immediate** instead synchronously fabricates successful execution.
- `runJob`1004+ drives simplified statuses; RUNNING precedes actual container creation.
  `BatchDockerRunner`84+ launches resolved image command/env, polls Docker every250ms,
  captures a `/aws/batch/job` log stream, reports exit0/nonzero. MEMORY is applied; VCPU/capacity
  scheduling, dependencies and IAM/VPC semantics are not faithful. CloudWatch log-stream names
  were observed, but **GetLogEvents/tail completeness not separately tested**.
- Attempts1–10 are supported; nonzero retries automatically until max, while timeout does not
  retry. Timeout minimum60s, direct container stop/remove on expiry/termination. `CancelJob`
  does not stop STARTING/RUNNING; `TerminateJob` marks terminal then requests stop. These branches
  were source-audited, **not** executed: approved study used attempts1/no live-child sacrifice.
  `evaluateOnExit` is not implemented by the attempts-only retry model.
- Submit has **no idempotency token/deduplication**: fresh UUID on every submit, jobName is not
  uniqueness. Lost acknowledgement can leave a live job; do not infer failure/resubmit. Unique
  caller correlation in names/parameters/tags plus ListJobs may aid reconciliation, not guarantee
  exactly-once. Actual acknowledgement-loss/duplicate submission tests were not performed.
- External attempt identity is `(jobId, AWS_BATCH_JOB_ATTEMPT)`/attempt list order; DescribeJobs
  does not expose a stable Docker-container/opaque attempt ID. DML T must remain a distinct
  occurrence. Disable service retries initially; otherwise each external retry needs explicit
  fresh DML occurrence/workspace accounting, not multiple computations silently behind one T.
- [Lifecycle](https://github.com/floci-io/floci/blob/ee15f502bfc017861b67b076b82e1ccd032c7129/src/main/java/io/github/hectorvent/floci/lifecycle/EmulatorLifecycle.java)
  invokes Batch teardown on shutdown: **graceful Floci shutdown stops/removes in-flight jobs**.
  Batch's in-flight map is process-local; no Batch startup rehydrate/reattach path was found.
  Abrupt loss can orphan containers/stale statuses; create-to-map and stop/ack races remain.
  No crash/host-loss or live-restart survival claim.
- Batch calls best-effort `ContainerLifecycleManager.stopAndRemove`, which catches stop/remove
  errors, not its strict variant. Map ownership can be dropped before confirmed removal.
  Service terminal status therefore does **not** prove cleanup/writer disposition. Actual normal
  stopped-container stop calls logged304 warnings, then removal/absence was independently proved.
- [Storage](https://github.com/floci-io/floci/blob/ee15f502bfc017861b67b076b82e1ccd032c7129/docs/configuration/storage.md):
  stock image defaults memory, not durability. Persistent Batch rewrites JSON/rename; errors can
  be logged rather than raised, no power-loss/transactional dispatch proof. S3 bodies/index and
  packet manifest are not one DML/storage/service transaction. Persistence is not job recovery.

## Smallest history exchange and security boundary

**Candidate:** immutable S3 keys for pinned complete input bundle+job, and per-publication
complete P/U/F packet files; publish a small manifest **last** with exact file lengths/digests,
selected commit/phase and transport association. Observer fetches owned bounded bytes once,
validates against independently retained exact Cq/Q/selection, then existing public inspector/
explicit-ref receive. Never trust status/manifest as DML done or overwrite earlier packets.
A missing/unreturnable F remains unknown/unretrieved, even if Batch says SUCCEEDED/FAILED.
Preserve DML computational cleanup separately from outer job/artifact retirement. Existing32MiB
bundle profile still applies; larger/concurrent/partial-publication cases remain untested here.
S3 is the smallest AWS-shaped exchange already exercised; shared LMDB/host mounts are unnecessary.
Docker cp/logs alone are poor result exchange because Floci automatically removes job containers.

Approved profile: **new labelled internal bridge, no host ports/network/listeners**. Namespace-private
HTTP4566/DNS53 was explicitly accepted instead of literal127 inside the service. Final before-submit
inspection proved network.Internal=true, empty PortBindings, user1001:0/socket group131,
cap-dropALL/no-new-privileges, service512MiB/1CPU/pids256, exactly private named data volume+local
socket mounts. All**128 released service-enable keys** were robustly enumerated; effective startup
set was **exactly batch/s3/cloudwatchlogs/iam**. Namespace `/proc/net/{tcp,tcp6,udp,udp6}` explicitly
confirmed **no9169 IMDS binding**. Cached trusted job128MiB had no mounts/socket/privilege/public
ports; lack of job CPU/PID ceilings was observed, not hidden. Internal network/no egress avoids
cloud endpoints but is not a privileged adversary audit. Socket grants Floci daemon-root-equivalent
host authority despite nonroot/cap-drop: trust pinned Floci and never expose it to untrusted jobs/
users. Tokens/content hashes are not worker authentication. No sensitive/shared/A/credential mounts.

### Preserved corrections and disposition

Initial real-job fixture `0d740cbef1d74330bc0a4b4345e20cb3` and packet transport fixture
`2736fc12f67b4d91a2bdaa805f70a4ed` had an owned harness regex defect: EC2's enable field follows
other fields/comments, so EC2+**private9169 IMDS** was additionally enabled. No EC2 calls/children/
public ports occurred; both retired safely. Their Node/S3 evidence remains **qualified by this
extra-service deviation**, not exact-four-service proof. Intermediate explicit-EC2 correction
`probe-final` passed; final `probe-profile-final` supersedes it with robust128-key enumeration,
actual binding evidence and the full natural job gate. No profile/security widening.

First packet validation exit1 after normal replay assertions: negative oracle expected only
ExchangeError, but wrong independent Cq correctly raised native NotFoundError. Private exception
expectation corrected; fresh A/validation sandbox passed, using copies of the **same already
S3-fetched bytes**. Original failed log/sandbox retained; no production change or association-
specific rejection claim. Four owned fixtures total (three real-job runs, one packet-transport
run), all naturally reaped/archived/identity-checked retired. No owned Floci container/network/
volume remains; image and nonsensitive archives retained. Original three unrelated services
untouched. DML remains clean at **`099d156fb49f81a7da0683898189a85c1172988c`**; coordinator notes
preserved. No commit/push/old completion protocol.

## Smallest separately approved Iteration11 recommendation

One additive Batch-style submit/observe/retrieve seam, initially **one single-container job,
service retries1, trusted pinned worker image, explicit local endpoint + synthetic credentials**.
Reuse caller-recorded exact Q, public B execute/immutable P/U/F inspection and unchanged-head
explicit-ref receive; add only bounded object transport and saved external job/selection identity.
Floci owns execution lifetime while alive; caller owns submission ambiguity and artifact/fixture
custody. No automatic retry, cancellation, scheduler, resource subsystem, detached DML supervisor,
AWS/cloud integration or durable restart promise in the first turn.

**Falsifiable acceptance before calling that turn an adapter pass:** actually run installed DML
in the Batch child; gated submitter exits and fresh clients retrieve coherent real P/U/F; prove
exact Q/only-new-T/full typed all-parent bytes, nonzero-after-U evidence/separate cleanup,
unchanged A refs/offline receive, no polling relaunch; reject malformed/partial/wrong history;
handle before-submit and after-reap acknowledgement gaps without resubmission; prove owned-writer
and outer artifact disposition separately. The current study passes mechanics/packet replay,
**not these unexecuted combined criteria**. Stop for coordinator/user review.

## One-screen synthesis

- **Yes, with constraints:** released Floci2.3.0 Docker mode actually runs jobs after SubmitJob
  client exit; fresh polls inspect the same job without computing again. Immediate mode is not evidence.
- **Final exact profile passed:** two real gated Node jobs computed42; exit23 after publication
  preserved result bytes and FAILED/attempt identity. Exact four services/no9169, internal bridge,
  no host ports, approved socket authority. All owned resources archived/retired.
- **History transport passed separately:**27 original P/U/F files from prior synthetic DML execution
  survived real S3 exchange byte-for-byte; current public inspection/atomic explicit-ref receive,
  every typed packed object/all parents and unchanged A refs passed. **No DML-in-Batch execution yet.**
- **Do not overclaim lifetime:** clean after-reap persistence passed; graceful service shutdown
  stops live jobs, crash/host-loss recovery is unverified, cleanup is best-effort and no exactly-once.
- **Initial harness deviations remain:** extra private EC2/IMDS in old Node/S3 runs and native
  wrong-Cq rejection expectation corrected; final exact-profile evidence and fresh replay qualified.
- **Smallest next turn:** one trusted DML Batch child, attempts1, immutable S3 packet/manifest-last
  transport, saved job+independent exact-Q identity, existing inspector/unchanged-head return.
  Require combined actual P/U/F/failure/ambiguity/ownership evidence before an adapter pass.
- **Stopped:** no production/spec/native/build/CI/Iteration11 GO, commit/push or extra workers;
  DML099d156 clean, coordinator notes preserved, only approved image retained.
