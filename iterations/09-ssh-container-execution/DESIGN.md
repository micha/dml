# Iteration 9 candidate design: SSH execution against a local container

Status: **approved bounded plan; Iteration 9 GO**. The existing window-2 agent implements
in a new Pi session with coordinator independent review/fixes, then accepted focused commit/
push and exact-SHA CI/fixes; see [COORDINATION.md](COORDINATION.md). Docker is an SSH-host
fixture, not a DML backend. Candidate/preparation language below preserves planning provenance;
exact engineering spellings remain refinable, and actual behavior belongs to as-built docs.

## 1. Ownership and learning goal

This document owns candidate SSH transport, invocation and ownership mechanics.
[EXAMPLE.md](EXAMPLE.md) owns acceptance; [HANDOFF.md](HANDOFF.md) owns conditional work
order/gates. [Discussion](../../discussion.md#iteration-9-agreed-direction-ssh-execution-against-a-local-container)
owns agreements; the [glossary](../../../dml/docs/spec-next/glossary.md) owns vocabulary.
Current [caller requests](../../../dml/docs/spec-next/caller-requests.md),
[repository execution](../../../dml/docs/spec-next/repository-execution.md),
[local execution](../../../dml/docs/spec-next/local-execution.md) and
[transfer](../../../dml/docs/spec-next/transfer.md) own implemented behavior.

Agreed direction:

- A records Q/Cq before launch; B creates only T for that exact imported Q.
- Carry job/history through SSH, not a shared exchange-directory bind mount.
- B lives inside a same-machine container with its own filesystem and installed runtime.
- Use synchronous execution first; remote asynchronous observation is deferred.
- Receive validated completion under an explicit A ref; existing heads/request refs stay.
- Retain B history until explicit fixture cleanup. Disconnect is not computational failure
  or permission to relaunch.
- Docker is test setup. The SSH layer should apply to an ordinary compatible SSH host.

Learning goal: preserve request identity and explicit return publication across an SSH
transport and separate filesystem/runtime boundary. This local fixture is not proof of
arbitrary remote-host portability, complete environmental capture or production supervision.

## 2. Inspected baseline and relevant limits

Planning inspected clean implementation **`f7113d7acb3a0fe35eed6cb0013d3074533aef51`**:
Iteration 8 is published through `865bb79`; the subsequent diagram/maintenance commit is
local and unpushed. Design has the preserved uncommitted Iteration 9 direction notes over
`74a7bcd`. Prior [RESULTS](../08-caller-recorded-requests/RESULTS.md) and
[REVIEW](../08-caller-recorded-requests/REVIEW.md) are prior evidence, not a fresh baseline.

Current seams:

- Public `record_exchange_request` records Q/Cq/two A refs. Public `prepare_exchange`
  writes a fresh local workspace containing bounded `job.json` and `input.bundle`.
- Public `execute_exchange` accepts such a workspace on its own filesystem, initializes B,
  validates pinned selection and calls public `local.run_request` in caller-Q mode.
- The fixed installed `exchange_worker` merely invokes execute. Local execution captures
  entry bytes, but its interpreter path is an absolute declared path, not a portable runtime
  package. The binding can name a container-side path without requiring it to exist on A.
- Public `receive_exchange` needs only job/completion/output files and independent expected;
  it validates selected history in disposable storage before atomic explicit-ref import.
- Job v2/completion v1 and transfer framing already exist. Production SSH transport must
  not call private exchange/local/transfer helpers or duplicate selected-history validation.
- A narrow public job reader is currently missing: `_job` is exchange-private. A proposed
  public `read_exchange_spec(workspace)` can promote that existing strict reader within its
  owning module, without inventing a second descriptor codec.

Read-only live inspection found Docker **29.8.1**, active Docker service/socket accessible
through the existing docker group, and OpenSSH **10.5p1** client tools. No daemon/container
operation, image inventory/pull/build, SSH connection, key generation or experiment occurred.
Cached image/build dependencies and container runtime compatibility are **not verified**.

Current documentation checks informed the plan:

- OpenSSH `/openssh/openssh-portable`: remote command quoting is distinct from local argv;
  remote shell interpretation must be handled. SSH returns remote status or 255 on an error;
  status alone cannot establish a recorded computational outcome.
- Docker `/docker/docs`: publish explicitly to host loopback, not all interfaces; bind mounts
  refer to the daemon host; stopping retains a container's writable layer, removing destroys it.

## 3. Recommended layer and illustrative public stages

Add a separately imported **SSH exchange composition layer**, not Docker operations in the
runtime API. Candidate names are illustrative:

```text
exchange.read_exchange_spec(workspace) -> ExchangeSpec

ssh.SSHRemote(host, port, user, identity_file, known_hosts_file,
              python, workspace_root)
ssh.stage_ssh_exchange(remote, *, workspace, expected, timeout_ms) -> SSHExchange
ssh.execute_ssh_exchange(job, *, timeout_ms) -> None
ssh.fetch_ssh_exchange(job, *, packet, timeout_ms) -> Path

# Existing authoritative receive, unchanged:
exchange.receive_exchange(A, workspace=packet, expected=job.expected, ref=return_ref)
```

`SSHRemote` owns caller-supplied connection/runtime configuration. Credential paths are
operational inputs, not credentials to record in a DML DAG or commit. Exact validation,
public error/result spellings and SSH executable selection remain engineering choices.
No arbitrary command, extra SSH option list, environment injection or Docker client is an
entry point. `SSHExchange` owns independent expected, endpoint, explicitly selected remote
workspace and caller-owned host control/log location; it holds no native handle or live
remote process, and is not recovery authority. Host control artifacts must remain available
for dispatch guarding even if the prepared input files or A are moved offline.

The bounded new SSH path should require `expected.request` present: this turn tests explicit
caller-Q continuation. Original local fresh-Q and asynchronous APIs/tests remain unchanged;
there is no obligation to add every local mode to SSH in this first turn.

`execute_ssh_exchange` is synchronous transport invocation, **not a returned LocalRun**.
It must not interpret command exit as computational success/failure. Recorded failure can
finish normally in B. `fetch` returns a complete **transport candidate**, not `done` or a
validated outcome; only existing receive establishes the selected recorded completion in A.
This avoids duplicating validation or adding another lifecycle model.

## 4. Fixed remote helper over SSH

Recommend a small installed `daggerml.ssh_worker` with only three fixed actions:

1. **stage**: exclusively create the chosen remote workspace, consume bounded job/input
   bytes, write input then job last; no repository import, reservation, T or computation.
2. **execute**: invoke public `exchange.execute_exchange` once on that exact workspace.
   Preserve its exclusive `started` marker, readiness, B-local registration and outcomes.
3. **fetch**: read only fixed job/completion/output files with existing limits, and transmit
   them. No execute, registration, ref movement, finalization or historical-path action.

Invoke only configured absolute Python plus this fixed module/action/path. This is a
transport helper, not a persistent RPC server, arbitrary-command runner or custom executor.
It must not require the implementation checkout or test hooks. The existing local runner
still owns the computational child, scratch cleanup and recorded final disposition.

Use OpenSSH client with **no PTY**, local `shell=False`, and correctly quoted fixed remote
command tokens for the supported POSIX remote-shell profile. Local argv separation does
not eliminate remote shell parsing. Validate endpoint/user/port/path types and profiles;
reject NUL/control/unencodable inputs and option-like endpoint injection. Test spaces,
quotes and shell metacharacters without executing injected commands. Remote Python/workspace
paths are explicit operational choices, not paths taken from incoming history.

Recommend noninteractive, fail-closed connection settings: explicit identity and known-hosts
file, strict host-key checking, batch mode, finite connect attempts/timeouts, no inherited
user configuration/proxy/forwarding or interactive password/host-key prompts. Exact portable
flags/config-file mechanics belong to implementation review. Do not disable host-key checks
for convenience. User-selected SSH binaries/runtime are trusted prerequisites, not captured
computational dependencies.

### Suggested transport framing

Prefer a bounded header plus exact-length binary file bodies through SSH stdin/stdout,
not shell `cat`, remote tar extraction or a second base64 copy of the already framed bundle.

- Small strict UTF-8 JSON header: explicit format and fixed file byte counts; duplicate/
  unknown/missing fields, bool-as-size, negatives, oversized sizes and unsupported labels
  reject. Header limit follows the existing 8,192-byte descriptor profile.
- Stage bodies: job bytes (at most 8,192), then input bundle (at most owning transfer limit).
- Fetch bodies: job, completion (each at most 8,192), then output bundle (at most owning
  transfer limit). Fixed filenames only; no archive paths, arbitrary file requests or A path.
- Exact lengths and EOF required. Truncation, extra bytes, startup/banner stdout, invalid
  headers and IO failure are transport errors, never partial successful retrieval.
- Use existing public profile constants and job reader. Own bytes before publication/return;
  bounded transport framing does not replace native object or exact-Q history validation.

Specific header labels/field names remain candidate engineering details. This transport
format is not a native record or migration obligation. Test normal production limits, not
only scaled substitutes. The whole bundle already has a byte API; no streaming repository
codec, exact RSS limit or universal runtime quota is promised.

## 5. Stage, invoke, fetch and receive boundaries

### Stage

A already has Q/Cq and a public prepared local workspace. Check exact local job/expected
and caller-Q mode before sending. Select a fresh child path under the explicit existing
remote workspace root (for example using the transport token). Never adopt a path supplied
by a server response. Require exclusive remote creation; no overwrite/resume/repair on
collision or lost acknowledgement. Stage failure may leave partial remote files; A's Q
remains. Stage-only success creates no B, Q reservation or T.

The job reader and owned-byte handling should prevent mixing descriptors during a read;
this is not a hostile concurrent-writer/symlink defense. All source/destination workspace
writers are trusted and cooperative. Keep independent expected outside incoming transport.

### Execute

Create a caller-local **dispatch marker before starting SSH**, after prebuilding invocation
arguments/streams. Retain it on failure or response loss. A second execute for that job
rejects without another launch; B's existing `started` marker remains its independent guard.
If native SSH spawn or connection establishment failed, do not guess that remote dispatch
was impossible and clear the marker. A fresh explicit workspace can attempt copied Q again;
there is no global single-dispatch guarantee.

Call fixed remote execute; B imports Cq, validates exact Q, reserves it at Cq, publishes only
T/P and runs existing captured source. Configured `remote.python` starts the transport
helper; Q's recorded binding interpreter starts the computational child. They may coincide
in the fixture, but neither is silently substituted for the other or rewritten after Q.
Use container-side declared interpreter and inputs, not host `sys.executable` or undeclared
host file paths. Existing outcome/evidence/cleanup
and F/export rules remain. An SSH zero status only says the invocation returned normally;
A has not yet received a computational outcome.

### Fetch and receive

A fresh explicit fetch invocation retrieves closed files from the same selected remote
workspace. It does not reexecute, finalize an unknown T or reconstruct an absent receipt.
Missing completion/output is an error/absent returned evidence, not a fabricated failed Q.
Recorded F without exported files remains inspectable in B but is not automatically made
returnable by this turn; existing full-profile export limits still apply.

Allocate a new caller-owned packet directory, publish files only from complete bounded
owned transport bytes and publish receipt last. Partial local files can remain after IO
failure; never reuse them automatically. Then existing `receive_exchange` revalidates exact
Cq/Q/token/history/outcome/separate cleanup before atomic A import. Main/submission/Q refs
stay unchanged. Packet-only repeat receive is nonexecuting and same-target idempotent;
conflicting return refs abort all new A rows. Keep packet/B offline or unavailable during
independent receiver tests to prove no accidental shared-filesystem dependence.

## 6. Connection/process/retention ownership

Each host invocation owns and reaps its **local SSH client**. Recommend file-backed stdin,
stdout and stderr to avoid pipe deadlock/unbounded in-memory `communicate` output; require
finite invocation wait and bounded retained diagnostics. Timeout/error cleanup may terminate/
kill/reap the local client only. File-backed logs can grow; this is not a hard disk quota.
Spawn itself is not portably interruptible. Closing SSH is not a portable remote-process
termination guarantee.

Remote command/channel/child lifetimes can diverge. If the client exits or disconnects,
B may have no T, unknown T, published U, or recorded/exported F. Do not infer a phase from
SSH return code, elapsed time, container liveness or missing host response. No automatic
reconnect-and-execute or general remote child supervision is added.

The **fixture owner** owns Docker/sshd lifetime separately. B lives in the container's
writable layer with no shared host exchange mount. Keep the container and B until explicit
retrieval/inspection policy permits cleanup; stopping does not erase B, removal does. Do
not use automatic container removal that destroys unknown history. Fixture teardown proves
owned writers/children stopped and preserves needed evidence first. It never follows
historical scratch strings as authority or deletes unrelated containers/volumes.

LocalRun's cleanup is computational scratch cleanup in B. SSH stream disposal and later
container/workspace retirement are **transport/fixture ownership**, not secretly folded
into that recorded cleanup DAG or reclassified as computational failure. This iteration
adds no resource manager or new cleanup record scheme. Document this boundary explicitly.

## 7. Local fixture and scope limits

- Explicitly target the existing **local** Docker daemon. No remote context/daemon/cloud.
- One owned container, loopback-only published SSH port, fresh ephemeral fixture credentials,
  controlled sshd/account and separately installed current DML/Python runtime.
- Pin/record tested image identity in fixture evidence. Obtain its SSH host key through the
  trusted fixture control channel; do not trust an unauthenticated first connection/key scan.
- No bind mount of A, implementation checkout, exchange workspace, Docker socket or broad
  host directories into execution. Image-build staging is separate from runtime visibility.
- Prove wheel/source/module/native provenance and runtime/ABI compatibility inside the
  image. Host Nix-built wheels are not automatically compatible with another image/libc;
  build compatible current wheels in a bounded fixture build if necessary. Do not rewrite
  tags or substitute a stale published package.
- Prefer existing cached images/tools/dependencies. Missing base image/sshd/build tools
  requires a scoped provisioning decision before network pulls/installations; planning
  has not established that an offline image is available. No host/global service changes.

No public Docker adapter, asynchronous SSH handle/polling service, detached supervisor,
remote registry, scheduler, automatic retry/recovery/cancellation, arbitrary command/plugin
framework, environment installer, cloud/second-host experiment, native/old-spec expansion,
reuse/facets, resource management, observer/UI, version bump/migration, package publication
or later feature turn. No broad sandbox/authentication audit/full capture claim.

A material missing primitive/scope change needs a reproducer/proposal and separate approval.
The detailed mechanics above need user plan approval, then separate bounded GO.
