# Floci Batch execution and immutable S3 progress

Status: implemented by explicitly imported `daggerml.floci`, its internal
`floci_http` transport family and fixed installed `floci_worker` job program.
This is an **unsigned local Floci prototype**, not a production AWS SDK adapter.

## Authority boundary

This document owns operational configuration, fixed HTTP/object framing, staging,
one-shot submission/acknowledgement uncertainty, saved external identity and the
installed job-side publisher. [Caller requests](caller-requests.md) owns exact Q/Cq
and imported-Q first registration. [Asynchronous exchange](asynchronous-execution.md)
owns P/U/F selection, packet inspection and atomic explicit-ref reception;
[local execution](local-execution.md) owns computation and separate cleanup.
[Transfer](transfer.md) owns complete typed all-parent history/profile bounds.
[Python API](python-api.md) owns native handle lifetime. Terms follow the [glossary](glossary.md).
Normative sections describe implemented behavior; examples/evidence are informative.

## Public surface and operational profile

```python
from daggerml.floci import (
    FlociRemote, StagedFlociExchange, FlociJob, FlociObservation, FlociError,
    stage_floci_exchange, submit_floci_exchange,
    save_floci_job, load_floci_job, observe_floci_job,
)

FlociRemote(endpoint, bucket, prefix, queue, job_definition, image, python)
stage_floci_exchange(remote, *, workspace, expected, control, timeout_ms)
submit_floci_exchange(staged, *, timeout_ms) -> FlociJob
save_floci_job(new_directory, job) -> None
load_floci_job(directory) -> FlociJob
observe_floci_job(job, *, packet, timeout_ms) -> FlociObservation
# Unchanged owning reception:
exchange.receive_observation(A, packet=observation.packet,
                             expected=job.expected, ref=explicit_ref)
```

Frozen configuration requires exact NFC/UTF-8 strings without controls:

- Explicit canonical `http://host:port`, no credentials/path/query/fragment,
  implicit port, proxy discovery, redirect following or AWS default endpoint.
  Host is lowercase ASCII alphanumeric followed by alphanumeric/dot/colon/hyphen;
  IPv6 brackets are used for admitted alphanumeric-first IPv6 spellings; this is
  a narrow spelling profile, not universal address/hostname support or normalization.
  This validation alone is **not proof of local network isolation**.
- Lowercase bucket3–63 characters in the implemented alphanumeric/dot/hyphen
  profile, no consecutive dots. ASCII prefix1–256 characters using
  alphanumeric/dot/underscore/hyphen/slash, without empty/dot/dot-dot segments.
  Bucket/key segments are individually percent-encoded, never incoming paths.
- Queue1–128 ASCII alphanumeric/underscore/hyphen, alphanumeric first; exact
  `name:revision` definition (positive decimal, at most nine digits), never latest.
- Immutable local image `sha256:` plus64 lowercase hex, not a pullable tag;
  declared normalized absolute **POSIX** job interpreter, independent of host paths.

Bucket/queue/definition/image are precreated trusted prerequisites. Runtime never
provisions services, builds/pulls images or installs dependencies. Fixture/control
and transport files are external application state, **not native LMDB entities**.

`StagedFlociExchange` owns remote, independent caller `ExchangeSpec` and absolute
local control path; pinned caller `expected.request` is mandatory. `FlociJob` adds
acknowledged lowercase UUID `job_id`, not a DML occurrence/content ID. Neither
owns a caller Popen/PID/cancellation capability. Copying Q into another explicit
namespace/control can still request another attempt: no global dispatch lock.

`FlociObservation` owns the validated `ExchangeObservation`, `job_id` and bounded
`service_status`; forwarding properties expose lifecycle/phase/packet/snapshot.
Only exchange inspection derives DML lifecycle/computation/cleanup. Bootstrap has
working/no packet, **including service SUCCEEDED or FAILED without a valid F**.
F can be done while the service is RUNNING or later FAILED. Recorded computational
failure may have successful outer publication/job exit. Status is diagnostic only.

## Direct bounded HTTP

Only fixed Batch POST actions and path-style S3 GET/create-only PUT are used.
Connections are direct `http.client.HTTPConnection`, with fixed synthetic local
scope headers; no real signing/authentication/IAM/SDK/credential discovery is
implemented. Every acquired response/connection closes on catchable paths.
Errors contain fixed messages, not payload/credential/HTTP error excerpts.

`timeout_ms` is exact int1–3,600,000. One invocation accounts an overall monotonic
HTTP budget and a finite call count. Each status/header byte and bounded body
read checks remaining time and sets the socket timeout. Total HTTP status/header
bytes, including informational replies, are limited to8,192. Response framing
requires exactly one canonical decimal Content-Length, no Transfer-Encoding,
and absent or exactly one `Content-Encoding: identity`. The explicit
Connection:close profile reads the raw body to EOF rather than hiding bytes
past Content-Length; truncation, excess, silent/slow writers and profile overflow
raise. Descriptor/Batch response bodies retain8,192 bytes; bundles retain owning
32MiB. These are not portable DNS/filesystem/native/process hard deadlines,
RSS/disk quotas or an adversarial network/security audit.

JSON descriptors reject invalid UTF-8/BOM, duplicates, extra documents, nonstandard
constants, deep JSON, unsupported labels, missing/unknown fields and wrong types.
File counts and attempt require **exact int**, not bool. Owned file rows have exact
ordered names/size/lowercase SHA256; digests detect substitution, not authenticate
workers or certify truth. Incoming metadata cannot rewrite independent config/Q.

## Stage, submit and saved acknowledgement

Stage owns the closed prepared job/input bytes, parses the job through public
`read_exchange_spec` and matches independent exact Q selection before creating
control. It creates control/identity exclusively, uploads two input objects then
manifest last with `If-None-Match: *`, and writes local `staged.json` only afterward.
It creates no Batch job, Q/T, B or A writes. Partial/colliding control/remote objects
remain on error; no overwrite, resume, rollback or implicit stage retry.

Submit requires an actual staged description, not an acknowledged job. It reads
and matches persisted staged config/expected/manifest, prebuilds the fixed command
and acquires exclusive `control/dispatched` **before any API**, including preflight.
Every later error retains that guard. Repeated/mixed submit rejects before HTTP.

Bounded DescribeJobDefinitions requires exactly the configured active revision,
single-container type, immutable image and fixed base command
`[python, '-m', 'daggerml.floci_worker']`, no definition environment/parameters/
node properties/timeout and service attempts1. Submit overrides only the fixed
installed command plus its bounded operational config/token/base arguments and
forces `retryStrategy.attempts=1`; no arrays/MNP/dependencies/arbitrary commands.
Trusted fixture/image provenance remains necessary beyond these service claims.

SubmitJob has no idempotency token. A valid acknowledged UUID is extracted before
other response checks; jobName must match transport token and jobArn must be a
matching Batch ARN. Any later acknowledgement/receipt/description-allocation
failure raises `FlociError` retaining `.job_id`. Absent/invalid response may have
`.job_id is None` **despite a real accepted job**. No automatic ListJobs repair,
resubmit/guard clear or fabricated computational failure occurs. The available
local input/Q/guard/receipt evidence remains caller-owned for separate investigation.

Save exclusively creates a new directory, composes public `save_exchange_handle`
into `expected.json` and writes strict `floci.json` last. Metadata has exactly
format `daggerml-floci-job-v1`, remote operational fields and acknowledged job ID;
both files retain8,192-byte budgets. Load consults neither endpoint/input/control/
B/A nor live processes, and cannot dispatch/signal. Saved control is inert during
fresh observation. Partial directories reject without repair. Metadata-last is
not filesystem/power-loss/multi-service transactional durability.

## Installed job ownership and immutable publication

The fixed worker requires actual service job UUID and attempt string `"1"`.
It fetches a bounded input manifest and closed files once, checks lengths/hashes/
token/base/exact Q and parses the public job before allocating job-local workspace.
It starts exactly one public `ExchangeHandle`/`start_exchange`, retains the actual
`WorkerLaunch` throughout and uses public `observe_exchange`/`read_observation`.
B imports Cq, registers that same Q and creates only T through unchanged local
execution. No private exchange/local/role/native codec or computational retry.

The polling loop is **inside the executing Batch job**, not a blocking caller
observation or extra detached service. Closed packet bytes are validated and all
allocated packet/scratch handles disposed **before** successful S3 publication.
Catchable poll/inspection/upload errors still reap the owner and attempt a final
read-only publication; no missing-history finalization/repair/reexecution occurs.
Primary, reap and final-attempt errors retain owner diagnostics in the worker's
error. Uncertain wait retains/retries the same owner without kill; diagnostic IO/
sleep errors cannot escape that ownership loop, logging is attempted at most once,
and the first secondary error is retained after disposition. Known postreap close
errors do not retry forever. Remaining stream FDs at known job-program exit are
OS-disposed, not a claim that every Python close succeeded. Hard loss/process-tree
or orphan-child cleanup is not guaranteed.

Input keys are `<prefix>/<token>/input/{job.json,input.bundle,manifest.json}`.
Packet keys are `snapshots/<selected-commit>/{job.json,observation.json,snapshot.bundle}`;
phase slots are `phases/{initial,publication,completion}.json`. Input manifest has
exact format/token/base/request/file rows. Phase manifest also has actual job UUID,
attempt1, phase and selected commit; it carries **no trusted done/result assertion**.
All objects are create-only; already-present packet bytes require explicit whole
GET equality, not silent overwrite. Manifests publish last; previous immutable
phases never advance. No mutable latest pointer, multi-writer CAS, distributed
reservation or object-store/DML/Batch spanning transaction is provided.

Job-local B/workspace is retained on catchable errors but is **ephemeral at the
service container boundary**: Floci ordinarily removes exited containers. Only
uploaded complete packets promise selected full-history return; unpublished B/
progress can disappear and remain unknown. Service-owned container/artifact
retirement is not secretly folded into local computational scratch cleanup.

## One fresh observation and offline reception

Observe makes at most **seven** fixed calls: one DescribeJobs, up to three phase
GETs in F/U/P preference, then one selected commit's three fixed files. Describe
checks acknowledged ID/token, configured definition/queue association, image/fixed
command, single-attempt profile and diagnostic status; no status infers DML outcome.
A selected manifest is pinned once. New F after U selection cannot retarget that
U. There is no monotonic-newest guarantee; fast work may expose only F with all its
parent history, not fabricated observations of missed P/U.

Missing phase objects yield bootstrap. A manifest with missing/truncated/wrong
bytes or invalid exact-Q/role/history is an error, never bootstrap/done/failure.
All owning profiles and public `read_observation` validation run on complete owned
bytes in disposable storage. Cleanup precedes final caller packet allocation.
New packets contain snapshot/job, separate `floci-manifest.json` operational
association, then observation receipt **last**. Allocation/IO failure may leave
partial files, but no successful packet or A writes.

Existing `receive_observation` independently revalidates those same owned packet
bytes and exact expected Q before atomic create-or-same-target A import. It needs
no Floci/S3/B/input/source/image/live caller. Existing heads/submission/Q/sentinel
refs and prior bytes remain; B refs do not transfer. Same-target repeat is
nonexecuting; P-ref-to-F conflicts rather than implicit advancement. Return retry
is transfer/import, never another computation. Whole-batch late errors and
pre/post-A-commit response-loss boundaries remain exchange/transfer-owned.

## Informative example modes

Supply trusted explicit operational JSON with the seven FlociRemote fields and a
current installed Python/DML image/definition, then use fresh processes:

```sh
python examples/floci_execution.py prepare /new/story /owned/remote.json \
  /path/to/examples/floci_add.py gates/my-trial
python examples/floci_execution.py submit /new/story
# Provisioning and gate1/gate2 release are external application policy.
python examples/floci_execution.py observe /new/story/saved /new/packet
python examples/floci_execution.py receive /new/story/caller.dml \
  /new/story/saved /new/packet trial-result
```

The [finite driver](../../examples/floci_execution.py) records intent/captured binding/
named inputs before submit, not a general intent/closure registry/evaluator. The
[trusted source](../../examples/floci_add.py) consumes its declared canonical explicit
local endpoint, validates narrow bucket/normalized ASCII gate-key spellings and
percent-encodes each path segment. It closes acquired responses/connections on
catchable errors and has finite example gate waits. Transport dependencies/environment
are not completely captured; source trust remains explicit. Preparation's recorded job
interpreter is POSIX; native-host test binding emulation is separate, not a claim of
actual Windows-to-container execution or a relaxation of original path profiles.

## Informative evidence and limits

[Runtime](../../python/daggerml/daggerml/floci.py),
[fixed worker](../../python/daggerml/daggerml/floci_worker.py),
[wire/framing tests](../../tests/python/test_floci_http.py),
[host composition](../../tests/python/test_floci.py),
[typed history/actual A rollback](../../tests/python/test_floci_history.py),
[owner faults](../../tests/python/test_floci_worker.py) and
[default-safe fixture ownership](../../tests/python/test_floci_fixture.py) provide
bounded evidence. Explicit fixture gates under [tests/floci](../../tests/floci/)
are never default-started or packaged. Normal actual installed execution is distinct
from private post-reap ENTRYPOINT/response-loss substitutions. Exact commands,
source/image/module provenance, original failures, retained resource disposition,
coverage/mutation/platform/trust/profile and runtime qualifications belong to
[Iteration11 RESULTS](../../../dml-design/iterations/11-floci-batch-execution/RESULTS.md).

No AWS/cloud/SigV4/IAM/VPC parity, untrusted-job sandbox/full capture/scientific
validity, automatic retry/recovery/cancellation, scheduler, durable live restart,
global exactly-once, hard memory/disk/deadline guarantee or new native entity.
Floci's trusted local Docker socket is substantial daemon authority; its best-effort
cleanup and terminal statuses require independent owned-writer disposition proof.
