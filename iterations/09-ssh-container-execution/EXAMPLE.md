# Iteration 9 worked example: caller Q through SSH to container B

Status: **approved acceptance plan; Iteration 9 GO**. Execution evidence is not yet claimed.
The existing window-2 worker implements in a new Pi session with coordinator independent
review/fixes, then accepted focused commit/push and exact-SHA CI/fixes; see
[COORDINATION.md](COORDINATION.md). The candidate/preparation language below preserves
planning provenance. API names/paths are illustrative, not implemented contracts.

## 1. Fixture: a local remote host, not a Docker adapter

An explicit finite fixture owner creates one local container with an SSH server, controlled
account and current installed Python/DML runtime. Publish its SSH port only on host loopback.
The container has its own `/work/exchanges` parent and `/opt/dml/bin/python` interpreter.
No host A, source checkout, exchange directory or Docker socket is mounted into execution.

Use fixture-owned ephemeral authentication material outside Git. Construct known-hosts from
the host key obtained through trusted container control, not unauthenticated key discovery.
Pin tested image identity and save nonsensitive configuration/runtime provenance as evidence.
Missing cached image/dependency or image ABI compatibility is a preflight blocker, not
permission to pull/install arbitrary tooling. No container or key is created during planning.

The application talks only SSH to this endpoint. Docker-specific control belongs to the
fixture, not public SSH exchange helpers. A compatible ordinary SSH host could satisfy the
same protocol; the local story does not establish arbitrary production-host portability.

## 2. A records the intended remote-interpreter request

Create fresh A with C under main:

- A captured trusted addition entry script using public child context/publication helpers.
- A local-binding description whose **declared interpreter is `/opt/dml/bin/python`**,
  not A's `sys.executable`. The path need not exist on A; it must work in B.
- Named inputs `left=4`, `right=7`, a composite-valued keep DAG, sentinel ref/branch,
  and genuine prior unrelated Q/T/publication history in the selected basis.

The child independently checks installed module/native provenance inside the container and
performs arithmetic in Python. Its result DAG exposes `sum=11`. Diagnostics may record
reported runtime information; that is evidence, not certification of full environmental capture.

Save independent typed all-parent populations/every packed byte for C/sentinel and refs.
Explicitly record Q under `submission-1`:

```text
recorded = record_exchange_request(A, commit=C, binding_name="binding",
    inputs_name="inputs", intent_uri="urn:example:add-i64", ref="submission-1")
```

Fresh readers/ordinary CLI verify Cq parents `(C,)`, exact C tree plus Q, both submission
and request-reservation refs at Cq, unchanged main/sentinel/old bytes and no T/outcome.
An additional Q is deliberately never sent; it remains recorded without a fake status.

## 3. Prepare locally, stage through SSH only

```text
spec = prepare_exchange(A, commit=Cq, request=Q, binding_name="binding",
    inputs_name="inputs", intent_uri="urn:example:add-i64", worker_ref="work",
    workspace=host_workspace)
job = stage_ssh_exchange(remote, workspace=host_workspace, expected=spec,
    timeout_ms=transport_budget)
```

Preparation/staging are separate from request recording. The caller retains independent
expected Cq/Q/token. Stage checks exact local job/expected and caller-Q mode, sends bounded
job/input bytes and creates a fresh exclusive remote workspace. It performs no import,
reservation or computation. Independent fixture inspection verifies remote files, but no B,
`started`, request ref or attempt. A is unchanged.

Prove the path separation: remote workspace is inside the container; host and container
paths are not aliases. Stage succeeds via SSH with no shared mount. Permission/host-key/
authentication/framing errors retain A's Q; partial remote files are not successful dispatch.
Repeat stage against an existing remote path rejects rather than repairing/overwriting it.

## 4. One synchronous invocation; exact Q survives

Rename A offline and move the already-staged host job/input files offline. Retain independent
expected/job description and the caller-owned host control/log directory for its dispatch
marker; do not rename a directory still used by the driver. No A path or host runtime path
is transmitted as a dependency of the worker invocation.

```text
execute_ssh_exchange(job, timeout_ms=transport_budget)
```

Host publishes its one-shot dispatch marker before launching the local SSH client. Remote
fixed helper calls existing public execute once. B imports Cq, reserves exact Q at Cq,
creates T/P and uses the declared remote interpreter for existing execution.

After normal invocation return, fixture inspection through public DML readers confirms:

- Same Q content ID/occurrence as A; P parents `(Cq,)`, exact Cq tree plus only fresh T.
- No replacement request; B Q reservation is Cq, T publication ref is P or U.
- F preserves T occurrence and initial associations, with computational success/result 11
  and separate local scratch-cleanup disposition. Ordered parents `(P,U)` when published.
- Remote B never used host A or a checkout-backed/PYTHONPATH source runtime.
- Host invocation status is not an A outcome. No A return ref exists yet.

Repeat execute for the same job rejects without another SSH launch; retained remote `started`
also rejects direct repeat. The fixture separately records command/attempt counts. A different
fresh explicit job may attempt copied Q again; the test must not claim global exactly-once.

## 5. Explicit nonexecuting retrieval and atomic reception

```text
packet = fetch_ssh_exchange(job, packet=new_host_packet, timeout_ms=transport_budget)
# Complete transport candidate, not an outcome assertion:
received = receive_exchange(A, workspace=packet, expected=spec, ref="trial-1-final")
```

Fetch reads only fixed closed job/completion/output files over SSH. It neither executes
nor imports/recreates refs in B. Validate framing/limits/complete delivery; do not trust
remote stdout as a boolean success/result claim. A fresh packet may contain retained partial
files on IO failure, but no A publication.

Restore A, independently move main to Cnew, then make the SSH endpoint unavailable before
receive. Preserve the container's B/evidence; endpoint unavailability is not removal.
Fresh installed receiver with packet plus independent expected receives exact validated
history under the caller's ref. No SSH/client/worker/source invocation during receive.

Independent public breadth-first oracles compare complete typed populations/every packed
byte for C/Cq/P/U/F at remote B, transferred packet and A, including composite-only children
and every parent. Existing CLI agrees on selected Q/T/result/history, not as closure oracle.
Main stays Cnew; sentinel, submission and A Q refs stay unchanged; B working/attempt refs are
not copied. Same-ref/same-target repeat succeeds without computation; conflicting ref aborts
all new A records/ref together. No new DAG/commit is invented to wrap the return.

## 6. Matching requests, recorded failure and wrong history

Record Q2 against the **same C/binding/inputs/intent**, use a new transport workspace and
fresh B, and return F2. Q/T pairs are distinct; result DAG content may be equal. Preserve
Q1/T1 bytes/refs exactly. Run a separate captured source that publishes a result and exits
nonzero: receive records computational failure with evidence, not success; cleanup stays
separate. A missing remote interpreter after committed P produces the existing recorded
launch failure, distinct from failure to establish SSH before any B attempt.

Negative transport story:

1. Independently validate a genuine Q2 completed packet.
2. Substitute it into Q1 retrieval and rewrite transport token/base receipt assertions to
   expected Q1 while retaining complete Q2 history.
3. Receive against caller-owned expected Q1 rejects **before any A write**.
4. Also construct a typed-complete P parented by expected Cq retaining expected Q in the
   tree, but T referencing another matching Q, with coherent U/F. Both ordinary receive
   association checks and full typed completeness must be exercised, not just malformed JSON.

Also reject wrong runtime-job selection, replaced Q content under the same occurrence,
wrong root/parents/outcome/cleanup, framing extras/truncation/oversized counts and hostile
path/command-like inputs. Do not execute incoming path/source strings during validation.

## 7. Connection-loss stories without unsafe child sacrifice

Distinguish these boundaries using finite private fixtures, never installed fault hooks:

| Boundary | Expected recorded knowledge / permitted action |
| --- | --- |
| Host key/auth/connection failure before remote execution | A retains Q; no invented T/failure; execute marker retained; no automatic retry |
| Stage interruption / lost stage acknowledgement | Partial or complete remote files possible; stage never creates T; no overwrite/resume |
| Remote P committed, before computational child spawn | Q/T exist with unknown outcome; repeated execute rejects |
| Real child reaped, before F | P/U may survive; absence of F stays unknown |
| F and completion files persisted, response/channel lost | Fresh **fetch**, not execute, can retrieve same F/Q/T |
| Fetch interrupted/truncated after remote completion | A unchanged; remote completed history retained; explicit fresh fetch can retry transport only |
| A receive loss before/after real storage commit | No batch versus complete ref/history despite missing response; no new computation |

Fault barriers before spawn/after actual reaping may use separately identified private SSH
harness commands/instrumentation; those are not normal fixed-worker installed coverage.
The normal acceptance path must use the actual installed fixed helper. Do not disconnect/
kill a worker with a live computational child merely to make a convenient test. If a barrier
expires or remote disposition cannot be proved, preserve fixture/evidence and report a
blocker rather than asserting cleanup. Local SSH client reaping is not remote process-tree
reaping. General hard-owner-loss behavior remains explicitly unsupported.

Exercise genuine post-F transfer-profile overflow: B can retain successful recorded F while
export/retrieval yields no valid completion packet. Do not classify SSH nonzero as a failed
computation or turn recorded publication into done. Explicit cleanup-failure history remains
valid without reclassifying computational success.

## 8. Fixture retirement and evidence

Keep remote B until all intended packet/reader evidence is retained and owned writers are
known stopped. Stopping preserves the writable layer; removal destroys it. Explicit fixture
cleanup removes only its named/labelled container and credential/temp artifacts, never other
containers, images, volumes, historical scratch paths or global Docker state.

Container/SSH fixture retirement is not local scratch cleanup recorded in F. It is a separate
application/test obligation; no DML resource-manager or new cleanup schema is introduced.
Record actual cleanup success/failure and any retained owned fixture honestly. No credentials
or sensitive full-history payloads in Git.

No experiment, Docker/SSH provisioning, worker restart, implementation/spec edit, commit/push
or CI is authorized by this planning story. Same-machine real SSH/container evidence must
remain distinct from test substitutions, other platforms, actual second hosts, security,
full capture and remote lifetime guarantees.
