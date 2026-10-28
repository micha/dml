# SSH execution and immutable progress

Status: implemented by separately imported `daggerml.ssh` and the fixed installed
`daggerml.ssh_worker` helper. Docker is local acceptance support, not a runtime backend.

## Authority boundary

This document owns SSH endpoint/invocation profiles, binary transport framing, local
client ownership, saved SSH identity and stage/execute/start/fetch/observe boundaries.
[Asynchronous exchange](asynchronous-execution.md) owns coherent immutable P/U/F discovery,
packet validation/read-only inspection and explicit-ref reception. [Caller requests](caller-requests.md)
owns explicit Q/Cq and imported-Q first registration. [Repository execution](repository-execution.md)
owns job/completion descriptions and authoritative selected-history reception;
[local execution](local-execution.md) owns the unchanged computational child, outcomes
and scratch cleanup. [Transfer](transfer.md) owns bundles/full typed all-parent closure
and atomic import. [Python API](python-api.md) owns repository handles. Terms follow the
[glossary](glossary.md). Normative sections describe implemented behavior; fixture/story
instructions are informative.

## Public surface and identity

```python
from daggerml.ssh import (
    SSHRemote, SSHExchange, SSHError, SSHLaunch,
    stage_ssh_exchange, execute_ssh_exchange, fetch_ssh_exchange,
    save_ssh_exchange, load_ssh_exchange, start_ssh_exchange, observe_ssh_exchange,
)
from daggerml.exchange import read_exchange_spec, receive_exchange

SSHRemote(host, port, user, identity_file, known_hosts_file, python, workspace_root)
stage_ssh_exchange(remote, *, workspace, expected, control, timeout_ms) -> SSHExchange
execute_ssh_exchange(job, *, timeout_ms) -> None
fetch_ssh_exchange(job, *, packet, timeout_ms) -> Path
save_ssh_exchange(directory, job) -> None
load_ssh_exchange(directory) -> SSHExchange
start_ssh_exchange(job, *, connect_timeout_ms) -> SSHLaunch
observe_ssh_exchange(job, *, packet, timeout_ms) -> ExchangeObservation
receive_exchange(A, workspace=packet, expected=job.expected, ref=return_ref)
# Progress reception uses existing exchange.receive_observation:
receive_observation(A, packet=progress_packet, expected=job.expected, ref=explicit_ref)
```

Frozen `SSHRemote` owns operational endpoint/runtime configuration; frozen `SSHExchange`
owns that remote, independent caller `ExchangeSpec` and absolute local `control: Path`.
Its remote `workspace` is exactly `workspace_root / expected.token`, never a server-selected
path. The new SSH path MUST have caller-pinned `expected.request`, not fresh-Q-in-B mode.
These descriptions hold no repository handle/live remote process/PID/recovery authority.
They are not computational identities, serialized capabilities or a global dispatch lock.
Creating another explicit control/workspace/repository can attempt copied Q again.

Control is a separate new host directory. It MUST remain available even when A and
prepared input artifacts are offline. Fetch/observe never read those input files or A. Independent
expected remains caller-owned; incoming packets cannot select their own expected Q/Cq.
Original local fresh-Q, synchronous and asynchronous APIs remain unchanged.

## Endpoint and command profile

The supported remote filesystem/shell profile is POSIX. Remote Python/root are explicit
normalized absolute strings: no `//` prefix, `..`, collapsed separators, trailing separator
(except `/`), non-NFC spelling, controls or unencodable Unicode. They do not depend on the
caller's OS path parser. Spaces, apostrophes and shell metacharacters are quoted with
`shlex.quote` as individual tokens in one fixed remote command:

```text
<configured Python> -m daggerml.ssh_worker <stage|execute|fetch|observe> <configured workspace>
```

Host is nonempty `[A-Za-z0-9][A-Za-z0-9.:-]*`; user is
`[A-Za-z_][A-Za-z0-9_-]*`. Option-like hosts, `@`, whitespace/shell fragments reject.
Port requires exact int 1..65535; bool is not int. Operational strings MUST be NFC,
UTF-8 encodable and contain no ASCII/C1 controls. Local path-like inputs become absolute
host paths. Credential paths reject `%`, `$`, double quotes and literal backslashes remaining
in their forward-slash spelling, preventing SSH token/environment/config expansion.
Native Windows separators are converted to forward slashes in SSH options. Paths are trusted
operational inputs, not credential contents to record in DAGs.

Each invocation runs local `ssh` through `shell=False` with `-F none` and no PTY (`-T`).
It explicitly enables batch mode, strict host-key checking, identities-only public-key auth,
configured identity/known-hosts, no agent/global known-hosts/host-key updates/password/keyboard
interaction, no inherited proxy/jump/forwarding and one connection attempt. The connection
budget is rounded up to integer seconds; the separate local process wait uses exact
`timeout_ms / 1000`. Timeout requires exact int 1..3,600,000. No arbitrary SSH options,
commands, environment, modules or Docker operations are public runtime inputs.

The selected SSH executable and installed remote runtime are trusted prerequisites, not
captured binaries. Q's recorded binding interpreter starts the computational child;
`remote.python` starts the transport helper. Neither is silently substituted for the other.
Tokens/IDs do not authenticate computation; SSH host authentication does not certify scientific
truth, complete capture or sound trusted source.

## Fixed binary framing

SSH stdin/stdout are binary. A frame begins with a four-byte big-endian unsigned header
length (1..8,192), followed by exactly that many UTF-8 JSON bytes. Header fields MUST be
exactly `format` and `sizes`; `sizes` is an exact list of exact nonnegative int counts.
Duplicate/unknown/missing fields, bool counts, invalid UTF-8/JSON/constants/deep JSON,
wrong labels/counts, excessive lengths, truncated bodies and any bytes after the bodies
MUST reject. Startup noise is not a response. Bounded whitespace is accepted in JSON.

| Action/format | Ordered binary bodies and limits |
| --- | --- |
| `daggerml-ssh-stage-v1` | job (8,192), input bundle (`transfer.MAX_BUNDLE_BYTES`) |
| `daggerml-ssh-ack-v1` | no bodies; acknowledgement only |
| `daggerml-ssh-fetch-v1` | job (8,192), completion (8,192), output bundle (`transfer.MAX_BUNDLE_BYTES`) |
| `daggerml-ssh-bootstrap-v1` | job (8,192), only for observe |
| `daggerml-ssh-observation-v1` | job (8,192), observation receipt (8,192), snapshot bundle (`transfer.MAX_BUNDLE_BYTES`), only for observe |

Observe input MUST be empty and only the two observation reply formats are accepted.
No transported lifecycle, process state, result or success assertion is accepted.
Execute input/output MUST be empty. Bundle/descriptors keep their existing owning codecs;
this framing does not decode native records or assert an outcome. Transfer limits are not
exact RSS/time/disk quotas. Received bodies are owned bytes before publication. Exchange's
public job reader parses those exact owned descriptor bytes in helper-owned temporary scratch;
the SSH layer has no second job/role/native codec. Scratch cleanup errors propagate.

## Saved identity and live foreground launch

`save_ssh_exchange` creates a new directory exclusively. `expected.json` composes public
`save_exchange_handle(ExchangeHandle(job.control, job.expected))`; its workspace is the host
control path, **not** remote B. `ssh.json`, written last, has exactly `format` plus the seven
SSHRemote fields: `host`, `port`, `user`, `identity_file`, `known_hosts_file`, `python`,
`workspace_root`. Format is `daggerml-ssh-exchange-v1`; both files have the unchanged8,192-byte
budget and strict JSON/type/profile checks. Credential paths, not contents, are operational
configuration outside Git/DML records. Save/load never consult control/input/B/A/endpoint,
connect, signal, dispatch or serialize a PID/process/lifecycle. Partial/colliding directories
reject without repair; metadata-last is not multi-file/power-loss atomicity. Trusted caller
configuration and single-owner files remain required. Do not use its local expected handle
with local exchange start/observe; public load returns the SSHExchange identity instead.

`start_ssh_exchange` prepares fixed **foreground execute** argv, file-backed stdout/stderr
and SSHLaunch before acquiring the shared local `dispatched` guard and Popen. Stdin is
DEVNULL. It returns without waiting for authentication/readiness/T/computation; no postspawn
receipt IO or owner allocation is required. Start and synchronous execute reject each other's
prior dispatch before another Popen. The existing remote `started` guard remains independent.
There is no remote background worker, `ssh -f`, nohup, service, ControlMaster or supervisor.

`SSHLaunch` owns `.job`, actual local `.process` and acquired streams. The application MUST
retain and explicitly reap it. `wait(timeout=None)` uses Python seconds and returns only local
SSH status0 after empty execute stdout is checked; nonzero status/noise raises SSHError, not a
computational outcome. Known disposition closes all acquired streams even when status, seek,
read or close checks fail. A repeated wait returns the cached status or raises the cached
postreap error. **Timeout/uncertain wait errors retain the process and streams**, permitting
another wait; they MUST NOT automatically kill/disconnect this execution connection. There
is no saved live owner, hidden registry/finalizer/context cancellation or implicit wait.
Normal exit of the sole owner leaving a live unowned connection is unsupported. Hard owner/
channel loss does not establish remote-child disposition or authorize replacement execution.

## One bounded nonexecuting observation

The installed fixed `observe` calls public `observe_exchange` once, with exact owned job bytes
and remote ExchangeHandle. It adds no polling, ref discovery, role codec, execution, finalization
or repair. Its temporary packet is read into bounded owned job/receipt/bundle bytes, exact job
matched, and all helper scratch disposed **before** successful frame emission. Bootstrap
carries only the matching job: no retrieved snapshot is reported, not proof of no dispatch or
liveness. Malformed readiness/history is an error, never a bootstrap fallback.

Host observation owns the full reply frame, matches independent expected, materializes P/U/F
in disposable scratch and calls public `read_observation`. Scratch cleanup precedes final packet
allocation. It publishes the same owned `snapshot.bundle`, `job.json`, `observation.json` (last)
in a new caller packet, then returns ExchangeObservation with validated snapshot/ref=None.
Bootstrap has no packet/snapshot and does not allocate the caller packet directory. Receipt/
profile/export/validation/cleanup/IO failure prevents a successful observation; A is unchanged.
Duplicate remote/host/receive validation and temporary IO are deliberate composition costs,
not an exact deadline/RSS/disk bound. Hard command loss may leave helper scratch.

P/U stays working/provisional; F is done only after full validated recorded computation and
separate cleanup have been retrieved. SSH status, elapsed time, stdout or a prior receive do
not determine lifecycle. F can be observed without original completion/output files; this is
read-only retrieval, not finalizing unknown T or export repair. Overflowing F remains in B but
supplies no successful done packet. Old packets remain immutable; concurrent clients use
separate packet paths, with no monotonic-newest promise. Coherent read followed by pinned
immutable export remains [exchange-owned](asynchronous-execution.md#coherent-discovery-followed-by-immutable-selection).

Existing authoritative `receive_observation` independently revalidates exact Q/P/U/F before
atomic explicit-ref A import, with no endpoint/input/B/live owner required. Heads/submission/
request refs stay unchanged; B refs do not copy. Same-target repeats are nonexecuting; P-to-F
under an existing P ref conflicts instead of advancing it. Bootstrap cannot be received.

## Stage, dispatch and fetch

Stage reads bounded owned local job/input bytes and uses the public strict job reader to
match independent expected before allocating control or starting SSH. It creates control
exclusively, sends only those bytes and requires a complete empty-body acknowledgement.
Remote stage validates caller-Q job, creates its workspace exclusively, writes input then
job last. Stage MUST NOT initialize B, reserve Q, create T or execute source. Existing/partial
remote directories reject without overwrite/repair/resume. Lost acknowledgement can retain
complete files; it never authorizes another stage/dispatch. A Q already exists independently
and remains retained on later preparation/transport/file errors.

Execute prepares arguments and file streams, then exclusively creates local `control/dispatched`
**before Popen**. The marker survives spawn, host-key/auth/connection failures, timeout and
lost response. A second execute rejects without Popen; it may allocate further local logs.
No marker is automatically cleared. The remote fixed helper calls public `execute_exchange`
once, retaining its independent `started` guard, imported-Q selection and unchanged first
registration/child/finalization. Only T is new for exact imported Q. B is retained on every
exit. Recorded computational failure is a normal remote completion eligible for return.
An invocation returning normally returns `None`, never a LocalRun/outcome/`done` assertion.

Fetch reads only closed fixed `job.json`, `completion.json`, `output.bundle`; it never
registers, dispatches, finalizes, repairs or reconstructs missing receipts. It requires EOF
input, bounded closed file bytes and complete framing. The caller checks fetched job against
independent expected before creating a new packet directory, then writes output/job and
completion last. Filesystem errors can leave partial artifacts; no automatic reuse/rollback
or power-loss durability is supplied. A complete packet is only a **transport candidate**.

Existing public receive independently validates complete exact Cq/Q/T/P/U/F and outcome/
evidence/separate cleanup in disposable storage, then atomically imports under an explicit
A ref. No A heads/submission/request refs advance and no B refs copy. Same-ref/same-target
receive is nonexecuting; conflicting refs abort rather than merge/adopt/advance. Missing
completion/export/profile failure or SSH status MUST NOT fabricate failure or `done`.
Full recorded F in B can survive a failed export and remain unreturnable here.

## Local client and remote lifetime

Synchronous stage/execute/fetch and bounded observe invocations use file-backed
stdin/stdout/stderr under control, finite wait and direct
local-client terminate/wait (five seconds), then kill/wait (five seconds) if needed. Streams
close on catchable errors. This avoids blocking parent pipe writes/unread stderr deadlocks
and unbounded in-memory diagnostics; retained log files can grow without a hard disk quota.
Ordinary filesystem calls/process creation are not portably interruptible by the wait budget.

Transport/profile/selection/status violations raise `SSHError` (`ValueError`) with fixed
messages and no payload/credential excerpts. Argument type errors use TypeError; native,
exchange, filesystem and ordinary timeout exceptions retain their types. On failure to
establish **local** SSH-client disposition, SSHError retains `.process` (the actual Popen)
for explicit caller ownership/reaping and reports that uncertainty. Other SSHError instances
have `.process is None`. This rare **observation/synchronous client** owner is distinct from
SSHLaunch and never targets the execution connection. It is an acquired local Popen, not a
remote PID, saved execution identity or remote-process recovery seam.

Closing/reaping SSH does not prove remote command/child termination. Connection loss can
leave no B/T, unknown P/U, recorded F or complete return files. No automatic relaunch,
reconnect-and-execute, retry/recovery/cancellation or detached
supervision is provided. Saved observation identity does not promise remote survival after
loss of the foreground execution owner. Single trusted cooperative workspace/packet writers are assumed;
hostile filesystem/symlink/concurrent descriptor replacement is outside this profile.

B's recorded cleanup is the existing computational scratch disposition. Transport-stream
disposal and later container/workspace retirement are separate caller/fixture ownership,
not secretly folded into that cleanup DAG or computational failure. Retain unknown B until
explicit inspection/disposal policy and known owned-writer disposition.

## Informative example and local evidence

[The endpoint-driven story](../../examples/ssh_execution.py) records two matching caller Qs
against the same basis with distinct T/equal result, a nonzero-after-publication failure,
prior genuine Q/T history, composite-only children and a never-started Q. A/staged inputs
are offline during execution; control is retained. Explicit packet reception preserves
independently advanced main and request/submission/sentinel refs. No Docker import is needed.

[The progress application](../../examples/ssh_progress.py) supplies endpoint-driven prepare,
foreground-own, fresh observe and endpoint-offline receive modes. Its declared **remote**
finite gates are released out of band by the application/fixture controller, never by observe
or a runtime arbitrary-command hook. Normal trusted gates/binding are finite; on uncertain
owner wait the application retains ownership with bounded repeated waits rather than killing
or exiting. This investigation/blocker retention can be indefinite and is not a detached
service, hard deadline or normal finite-completion guarantee.

[Owned fixture instructions](../../tests/ssh/README.md) describe the separately mandatory
installed SSH/container gate. That local fixture uses copied cached Nix runtime/image contents,
not shared A/source/exchange/socket mounts or downloads. Its approved loopback-only **host
network** deviation avoids blocked Docker bridge connectivity; it demonstrates filesystem/
runtime/SSH separation, **not network-namespace isolation or another physical host**.
Normal installed helper evidence is distinct from private finite before-spawn/after-reap
loss substitutions and host helper coverage. No installed fault hooks are supplied.

Evidence: [SSH layer](../../python/daggerml/daggerml/ssh.py),
[fixed helper](../../python/daggerml/daggerml/ssh_worker.py),
[host tests](../../tests/python/test_ssh.py), [fault tests](../../tests/python/test_ssh_faults.py),
[atomic fetched-return tests](../../tests/python/test_ssh_return.py),
[story tests](../../tests/python/test_ssh_example.py),
[launch ownership](../../tests/python/test_ssh_launch.py),
[progress/inspector](../../tests/python/test_ssh_progress.py),
[progress history/atomicity](../../tests/python/test_ssh_progress_faults.py),
[progress example](../../tests/python/test_ssh_progress_example.py),
[fixture ownership regressions](../../tests/python/test_ssh_fixture_ownership.py),
[synchronous installed gate](../../tests/ssh/integration.py) and
[progress installed gate](../../tests/ssh/progress_integration.py). Actual commands/provenance/counts,
real versus substituted faults, retained/cleaned fixture status and coverage/memory/mutation/
platform/trust/profile limits belong to
[Iteration 9 results](../../../dml-design/iterations/09-ssh-container-execution/RESULTS.md) and
[Iteration 10 results](../../../dml-design/iterations/10-asynchronous-ssh-execution/RESULTS.md).
