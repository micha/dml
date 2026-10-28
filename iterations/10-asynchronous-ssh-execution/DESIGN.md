# Iteration 10 candidate design: asynchronous SSH execution and progress

Status: **reviewed bounded plan; local checkpoint requested**. The user reviewed the plan
and requested a checkpoint, including separate out-of-band diagram maintenance. This is not
Iteration 10 implementation/delegation/publication GO. Candidate/proposed language below
preserves engineering origin; exact spellings remain refinable, not as-built behavior.
No worker, fixture, SSH connection or Iteration 10 experiment/build/implementation started.

## 1. Ownership and goal

This document owns proposed SSH launch/observation/ownership mechanics;
[EXAMPLE.md](EXAMPLE.md) owns the acceptance story and [HANDOFF.md](HANDOFF.md) the conditional
work order/gates. [Discussion](../../discussion.md#iteration-10-agreed-direction-asynchronous-ssh-execution)
owns direction; the [glossary](../../../dml/docs/spec-next/glossary.md) owns vocabulary.
Implemented authorities remain [SSH execution](../../../dml/docs/spec-next/ssh-execution.md),
[asynchronous exchange](../../../dml/docs/spec-next/asynchronous-execution.md),
[caller requests](../../../dml/docs/spec-next/caller-requests.md),
[repository execution](../../../dml/docs/spec-next/repository-execution.md),
[local execution](../../../dml/docs/spec-next/local-execution.md) and
[transfer](../../../dml/docs/spec-next/transfer.md).

Direction selected for this next slice:

- A records and stages pinned Q/Cq as today; B creates only T for that same Q.
- Start one remote attempt without waiting for computation to finish.
- Retrieve immutable initial/publication/completion P/U/F through bounded SSH observations.
- Receive selected packets under explicit A refs, preserving heads/request refs/old snapshots.
- Fresh observation clients use saved job identity without relaunching execution.
- Keep saved identity separate from a live application-owned SSH client/connection.
- No promise of detached remote execution after that owner disappears. Connection loss stays
  uncertain, not computational failure or permission to retry.

Learning goal: make long-running remote computation inspectable without also introducing
remote supervision. Exact API/format choices below are assistant recommendations, not as-built
behavior or separately approved requirements.

## 2. Inspected baseline and existing seams

Planning inspects clean DML **`29ed39be6c1c18e6d57f782dd073acd37939c71c`** and clean design
**`f8e70b4c9371327dbaaa28d1d449aa6011c141ac`** before these planning edits. Iteration 9 is
accepted/published/stopped; its worker must not be restarted by this planning request.
Prior [RESULTS](../09-ssh-container-execution/RESULTS.md) and
[REVIEW](../09-ssh-container-execution/REVIEW.md) are evidence, not a fresh baseline.
During final status checking, a concurrent LMDB diagram edit appeared. The user confirms
another agent owns that separate work and will commit it in DML. It is not a planning blocker;
this coordinator leaves it untouched. Reinspect the completed DML HEAD/tree before any future
assignment rather than treating the initially clean SHA as the eventual implementation baseline.
At the subsequent user-requested checkpoint, the diagram and its six focused tests are locally
committed in DML as **`a94e6f51bb41ad2cfab4fad1dd2e96c97a3e728d`**, not pushed. This is
separate as-built visualization maintenance, not Iteration 10 implementation; account for
this ancestor before any future authorized push. See
[checkpoint](../../discussion.md#iteration-10-plan-review-and-local-checkpoint).

Current public seams inspected in `ssh.py`, `ssh_worker.py` and `exchange.py`:

- SSHRemote/SSHExchange own explicit configuration, independent ExchangeSpec and local control;
  remote workspace is configured POSIX root plus caller token. Stage has no B/dispatch.
- Synchronous execute runs the fixed installed remote `execute` action, retaining local
  pre-Popen `dispatched` and independent remote `started` markers.
- Public `observe_exchange(ExchangeHandle(remote_workspace, expected), packet=...)` already
  discovers coherent B refs, exports a pinned immutable ID, validates history and creates an
  immutable P/U/F packet. Bootstrap has no packet. It never launches/finalizes or changes B.
- Public `receive_observation` independently validates exact Q/history before atomic A import.
  Public save/load_exchange_handle serialize expectation without reading the workspace.
- A public **read-only packet inspector** is missing: current parsing/validation is private
  to exchange or available through receive (which writes a repository). Add only that narrow
  owning-module seam so SSH observation can validate without publishing to A.

The existing SSH fixture was retired after evidence archive. Do not assume a live endpoint,
working credentials or current image/runtime just because ignored build artifacts remain.
Its user-approved loopback-only host-network profile is the recommended local acceptance
profile; no claim of successful bridge/network-namespace isolation. Recheck local prerequisites
only after separate GO; missing downloads/provisioning still require a scoped decision.

Documentation checks: Context7 `/python/cpython` confirms Popen.wait timeout preserves the
process and permits another wait; pipe-backed waits can deadlock. `/openssh/openssh-portable`
confirms SSH exits with remote status or255 and `-f` backgrounds the client. These support
explicit foreground-client ownership, not any claim about remote survival on disconnect.
No new process/network experiment was performed.

## 3. Candidate public surface

Illustrative names/signatures:

```text
# Existing stage returns SSHExchange; original execute/fetch/receive remain usable.
ssh.save_ssh_exchange(directory, job) -> None
ssh.load_ssh_exchange(directory) -> SSHExchange
ssh.start_ssh_exchange(job, *, connect_timeout_ms) -> SSHLaunch
ssh.observe_ssh_exchange(job, *, packet, timeout_ms) -> ExchangeObservation

# Narrow owning exchange seam, usable without SSH:
exchange.read_observation(packet, *, expected) -> ReceivedObservation

# Unchanged authoritative A publication:
exchange.receive_observation(A, packet=packet, expected=job.expected, ref=explicit_ref)
```

Candidate `read_observation` promotes existing strict job/receipt/root/history validation
inside exchange and returns an owned description with `ref=None` (including nested completion).
It imports only into disposable validation storage, closes handles and cleans scratch before
returning. It never opens/writes A or launches, recreates refs, executes source or follows
historical paths. Receive shares those checks, then imports the same owned bundle under its
caller ref. Keep codecs/role validation in exchange; no private cross-layer calls, second
native/descriptor codec or additional C primitive.

If engineering needs a differently shaped public inspector to preserve owned-byte reuse,
record that refinement and test equivalence. No general observer framework is selected.

## 4. Saved identity without a second ExchangeSpec codec

Recommend a new, exclusively created **saved directory**, not a live process serialization:

- `expected.json`: use public save_exchange_handle with
  `ExchangeHandle(job.control, job.expected)`. Here workspace is the retained host control
  location, not the remote B path. Loading uses its public `.workspace`/`.expected` only;
  never pass this local handle to start_exchange/observe_exchange.
- `ssh.json`: new small strict operational metadata, written last, containing format and
  exactly SSHRemote fields. Remote workspace remains derived from root/token, not supplied
  by a server or independently duplicated here.

Load uses public load_exchange_handle, strict bounded SSH metadata parsing and existing
SSHRemote/SSHExchange validation. Each file uses the existing8192-byte descriptor budget;
no arbitrary embedded environment/options/command, PID/live owner/lifecycle/outcome or A path.
Credential **paths**, not key contents, are saved out of band; they are not DML datums and
must not enter Git. All saved files are caller-owned and trusted configuration.

Save/load never connect, consult remote/control/input files, signal a process or dispatch.
Partial saved directories reject; no overwrite/repair/resume. Receipt-last is not an atomic
multi-file/power-loss guarantee. Concurrent hostile writers/symlink aliases remain outside
this trusted single-owner profile. Incoming observation frames cannot rewrite saved identity.

This public saved identity can drive explicit operations, but is not an unowned-lifetime,
remote cancellation or global dispatch capability. Copying it to another control directory
is not promised to preserve a global lock.

## 5. Nonwaiting launch, still a foreground remote command

Start invokes **the existing fixed remote execute action** with a foreground local SSH client.
It does not run remote start_exchange, spawn another worker behind SSH, use `ssh -f`, nohup,
remote shell backgrounding, a service, tmux, ControlMaster or a supervisor.

Recommended sequence:

1. Validate caller-Q job/config/control, prepare fixed strict argv with connect budget and
   file-backed diagnostic streams (empty/DEVNULL stdin).
2. Allocate a nonserializable live SSHLaunch owner before spawn.
3. Exclusively create the same local `dispatched` marker as synchronous execute before Popen.
   Both APIs reject each other's prior dispatch. Preserve marker on every uncertain exit.
4. Spawn once and return the acquired owner without waiting for authentication/readiness/T.
   No postspawn receipt/write/allocation should be required to return ownership.

Returning the launch proves only local spawn returned Popen. SSH auth, remote initialization
and computational dispatch may still fail. B's existing started marker remains independent.
Remote helper still calls public execute once; only T is new for exact Q.

SSHLaunch owns job, actual local Popen and its acquired streams. Recommend `wait(timeout)`
with Python seconds, reporting only local SSH command status and closing streams after known
client disposition. Timeout/other uncertain wait errors retain owner/streams for another wait;
**do not automatically kill this execution connection** on wait timeout. The application
owns finite wait policy. Preserve fixed execute-output integrity: startup stdout must never
be accepted as a protocol/outcome; any normal-exit output check is transport-only and closes
streams once local disposition is known even if that check fails. Exact wait/error spellings
remain implementation refinements to document/test.

No saved owner/PID, finalizer, implicit wait/context cleanup, hidden launch registry or automatic
reconnect/kill/retry. Normal exit of the sole owner leaving an unowned connection is unsupported.
An application may directly manage its acquired local Popen, but that is not remote cancellation
or proof of stopped computational descendants. If an acquired owner cannot be returned on an
exception, preserve ownership explicitly rather than dropping a possibly live process.

## 6. Fixed nonexecuting observe action and framing

Add **one** installed helper action, `observe`, keeping stage/execute/fetch unchanged.
It requires empty input, owns exact job bytes, constructs public ExchangeHandle for that
remote workspace/selection and calls public observe_exchange once. No polling loop or
new B ref discovery/role validator. Readiness/bootstrap, coherent head/publication-ref read,
selected immutable export and unknown/final semantics remain exchange-owned.

Recommend helper-owned temporary packet storage, not retained per-poll directories in B:

- Bootstrap: no snapshot/packet from exchange; own job bytes only.
- P/U/F: read exact closed job/observation/snapshot files from the temporary packet into
  bounded owned bytes. Verify selection matches originally owned job.
- Close handles and clean helper temporary storage **before** emitting a successful reply.
  Cleanup failure is transport/observation error, not a changed computational outcome.
  Hard command loss can leave helper-owned scratch; no universal cleanup guarantee.

Extend existing strict length-header/binary-body ownership with only fixed reply shapes:

| Candidate format | Fixed ordered bodies |
| --- | --- |
| `daggerml-ssh-bootstrap-v1` | job, at most8192 bytes |
| `daggerml-ssh-observation-v1` | job, observation receipt (each8192), snapshot bundle (owning transfer limit) |

Header still has exactly format/sizes, bounded encoded length and exact int counts/EOF.
Accept only these two labels for an observe reply; no generic file/archive/status payload.
Never serialize/trust `done`, success, process state or result assertions in transport.
Bootstrap means **no retrieved snapshot reported**, not verified absence of dispatch/liveness.
Wrong/malformed responses are errors, not bootstrap fallbacks.

Host observe makes one finite SSH invocation using existing client disposal behavior for
this observation-only client. It owns complete frame bytes and matches independent expected.
For P/U/F, materialize them in temporary host scratch and use public read_observation; clean
scratch before allocating final caller packet. Publish the same owned snapshot/job/receipt
with receipt last to a new directory, then return ExchangeObservation with validated snapshot.
Bootstrap returns working/bootstrap with no packet/snapshot and must not create the requested
packet directory. Packet IO failure prevents a successful observation return; A remains unchanged.

These duplicate validation/import/temporary IO costs are deliberate prototype composition,
not exact RSS/deadline/performance claims. Observe timeout can terminate/reap its own local
observation SSH client, **never the launch connection**. Existing rare local retained-Popen
error ownership applies; remote helper disposition remains separately uncertain.

## 7. State and reception boundary

| Retrieved evidence | Report | Not implied |
| --- | --- | --- |
| Bootstrap reply/exact job, no snapshot | working/bootstrap | T exists, worker alive, failure |
| Validated P | working/initial | actual dispatch happened |
| Validated U | working/publication, provisional result | computational success or cleanup |
| Validated F with computation/separate cleanup and complete packet | done/completion | success, cleanup success, A reception, SSH client exit |
| Transport/export/validation/cleanup error | exception; retain prior knowledge | new failed outcome, replacement attempt, done |

A fresh explicit poll can discover F without synchronous completion.json/output.bundle,
using existing public observe semantics. This is read-only retrieval of recorded history,
not finalization/export repair of unknown T. If F itself exceeds the transfer profile,
observation still fails; F stays in B, no successful done packet. Old P/U stay working even
after F exists. No monotonic-latest promise across concurrent polls or mutable packet/ref.

Existing receive_observation revalidates selected exact Cq/Q/T/P/U/F before atomic A import.
Bootstrap cannot be received. Receive P/U/F under distinct explicit refs; same target repeat
is nonexecuting, P-to-F ref advance conflicts. Receive needs no endpoint/input/B/source/live
owner. No implicit main/submission/Q-ref move, merge/adoption or copied B operational refs.

## 8. Fixture/application ownership and stop line

Normal acceptance uses the existing offline local SSH-host fixture rebuilt with **current**
installed runtime. Reuse its approved loopback-only host-network profile, controlled account/
ephemeral credentials/strict known-hosts and no project/exchange/socket mounts. Runtime has
no Docker dependency. Recheck bare cached closure/native/wheel provenance after GO; no pulls
or global service/firewall/tool changes implied by these plans.

A finite application owner retains the execution SSHLaunch while fresh observation clients
exit. Trusted captured source waits at **declared remote gate paths** to make P/U measurable.
The fixture/test owner creates/releases those gates out of band; no shared host gate mount,
new public arbitrary-command/gate-control action or observation-triggered execution. Gates are
application/test input policy, not DML recovery/resource-management primitives. Demonstrate
external control explicitly; do not pass host-only gate paths to the remote child.

On errors the fixture owner releases cooperative gates and proves remote writers/children
stopped before retiring only owned resources. Do not timeout/kill the launch connection with
a live computational child merely to produce a test. Safe private loss barriers are before
spawn or after actual reaping. Hard owner/channel loss remains uncertain and unsupported as
a portable lifetime guarantee; retain B/evidence when disposition cannot be established.

No remote daemon/detached supervisor/async execution service, scheduler, cloud/second host/
remote Docker, automatic retry/recovery/cancellation, generic command/plugin framework,
new native entities/identity facets, environment provisioning, resource/GC/excision, observer
subsystem/UI, version/migration, package publication or later feature turn. Plan approval,
implementation/delegation GO and publication gates remain separate. Existing completed
Iteration 9 permission is not inherited.
