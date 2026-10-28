# Iteration 10 worked example: inspect one SSH attempt while it runs

Status: **reviewed acceptance plan, not executed**. The user reviewed the bounded plan and
requested a local checkpoint. Separate Iteration 10 implementation/delegation/publication GO
remains pending. [DESIGN.md](DESIGN.md) owns proposed mechanics; [HANDOFF.md](HANDOFF.md) owns
work/evidence requirements. API spellings remain illustrative, not implemented contracts.

## 1. An explicit local remote host and a live application owner

After separate GO, rebuild one owned local SSH-container fixture with current installed
Python/DML, controlled account, ephemeral keys and strict known-hosts from trusted fixture
control. Use the approved loopback-only host-network profile; no A/checkout/exchange/gate/
Docker-socket mounts. It is a separate filesystem/runtime, not network-namespace isolation,
a second physical host or a new Docker execution backend.

The finite application owner holds the **live execution SSHLaunch** until reaped. Observation
clients can start/exit independently. Normal exit of that sole owner while leaving an unowned
SSH connection is not supported. We do not background the remote worker or introduce a daemon.

The fixture/test controller creates a fresh gate directory **inside the container**, for
example `/work/gates/trial-1`, and releases it through explicit fixture control. The remote
path is recorded as an ordinary named input. No host-only gate path is transmitted as a
remote dependency; observation never creates/releases gates. This cooperative test machinery
is outside the public SSH helper and separate from process-loss fault substitutions.

A maintained endpoint-driven example may expose finite owner/observe/receive modes while
the fixture driver controls declared remote gates. The application has no Docker dependency;
ordinary-host users provide equivalent external gate control for this demonstration. Exact
script/command spellings remain engineering refinements, not a generic command API.

## 2. Record Q before launch

Fresh A starts with C/main, sentinel and genuine prior unrelated Q/T/publication history.
Include composite-only reachable children to distinguish complete typed history from mere
DAG/root/CLI inspection. Captured trusted addition source uses the public child context and
publication helpers and asserts installed container interpreter/package/native provenance.
Its binding declares `/opt/dml/bin/python`, not host sys.executable.

Named inputs: left4, right7 and gate `/work/gates/trial-1`. The child:

1. Waits finitely for `initial-release` in that remote gate directory.
2. Constructs/publishes result sub-DAG exposing sum11.
3. Waits finitely for `publication-release`, then returns.

A records Q/Cq with the public caller-request helper under `submission-1`; fresh reader/CLI
checks exact Q/intent/binding/inputs, parents `(C,)`, only added Q, both submission/Q refs at
Cq and no T/outcome. Record a separate never-started Q too. Snapshot all old packed bytes/refs.

Prepare and stage through existing SSH:

```text
spec = prepare_exchange(A, commit=Cq, request=Q, ..., workspace=host_inputs)
job = stage_ssh_exchange(remote, workspace=host_inputs, expected=spec,
                         control=host_control, timeout_ms=transport_budget)
save_ssh_exchange(new_saved_directory, job)
```

Independent fixture inspection finds only remote job/input files, no B/started/reservation/T.
Saving/loading identity neither connects nor dispatches. Saved operational metadata/key paths
stay outside Git/DML records. Partial/malformed saved directories reject, never repair/relaunch.

## 3. Start once, do not wait for computation

The application moves A and already-staged host input artifacts offline; host control/saved
identity/log paths remain online. Then:

```text
launch = start_ssh_exchange(job, connect_timeout_ms=connection_budget)
```

This returns the actual local SSH owner without waiting for remote authentication/bootstrap/T
or computation. The local pre-Popen marker is already retained. Stage-only observation can
report bootstrap; a private finite readiness barrier can demonstrate start-before-readiness
without relying on a short timing window. No fake request/attempt/status is fabricated.

Public synchronous execute and a second start for that same control/job both reject before
Popen. Independent remote started guard rejects direct repeat even through another connection.
Changing control/repository can explicitly attempt copied Q elsewhere: this is not global
exactly-once or transferable dispatch authority.

## 4. Fresh clients retrieve P and U, without taking ownership

A short-lived installed client loads the saved directory and performs one bounded call:

```text
observation = observe_ssh_exchange(load_ssh_exchange(saved),
                                  packet=new_packet, timeout_ms=transport_budget)
```

If bootstrap, no packet/snapshot/ref exists. Otherwise the host independently validates the
complete packet against caller-owned expected before reporting phase/lifecycle. Remote helper
uses public exchange observation/coherent selection, not process status or prefix-ref guesses.

Repeat externally until **initial P** is retrieved while the child is gated:

- working/initial, same exact Q; only fresh T relative to Cq, P parents `(Cq,)`.
- No final computation/cleanup; P is not proof actual external dispatch happened.
- Compare every typed object/packed byte/all parents with independent B/packet-store oracles.
- Client exits; application still owns the execution connection. Loading/polling never starts
  another attempt, and B ref/object state is unchanged by observation itself.

The fixture controller now releases only `initial-release`. A new installed client retrieves
**publication U** into another new packet:

- working/publication; same Q/T and initial field nodes; U parents `(P,)`.
- Provisional result11 is exposed, but no final success/cleanup assertion.
- Child remains gated after publication. Retain earlier P packet byte-identically.
- Concurrent readers use different packet paths; selection/export may race with later progress,
  but each returned packet must describe its selected coherent immutable history.

The owner remains alive; it need not poll internally. Calling `launch.wait` with a short timeout
while the child is deliberately gated raises/retains ownership; it must not kill the connection.
This finite test releases its gates afterward rather than abandoning a live child.

## 5. F retrieval is independent of client reaping and A reception

Release `publication-release`. A fresh client retrieves **F**:

- done/completion only after full validated recorded computation/separate cleanup and successful
  packet retrieval, not from SSH status/elapsed time or remote claims.
- Exact same Q/T, ordered parents `(P,U)`, final T preserves initial association/field nodes.
- Computational success/result11 and cleanup disposition are distinct.
- No A return ref yet. Old P/U packets remain working evidence.

The application explicitly waits/reaps its execution SSHLaunch separately. It reports only
local command status, not an outcome. A safe **private after-child-reap/post-F barrier** can
prove F retrieval while the execution connection still exists; identify that as substituted
loss/ownership evidence, not a normal installed-worker branch or timing-based claim.

Demonstrate independent public observation can retrieve already recorded F even with original
synchronous completion/output files unavailable. This is read-only selected-history export,
not finalization/repair/reexecution. F over unchanged transfer profile still cannot produce a
successful done packet; do not weaken the boundary or turn missing packet into failed computation.

## 6. Receive all three with the endpoint unavailable

Restore A and independently advance main. After known stopped writers, stop the endpoint but
retain B. Fresh installed receiver needs packet plus saved expected only:

```text
receive_observation(A, packet=P_packet, expected=job.expected, ref="trial-1-initial")
receive_observation(A, packet=U_packet, expected=job.expected, ref="trial-1-publication")
receive_observation(A, packet=F_packet, expected=job.expected, ref="trial-1-completion")
```

Inspect via public Python/CLI: same Q/T, preserved old snapshots/bytes, exact full parent
history and computational/cleanup distinction. Main, sentinel, submission and Q refs stay;
B working/attempt refs do not copy. Same-ref/same-target repeat is nonexecuting; returning F
under the existing P ref conflicts and aborts the whole new batch instead of advancing it.

Repeat matching submissions against the same C/binding/inputs using the same remote gate path
only after the prior child/owner is reaped and gates safely reset. Distinct Q/T, equal result
content; later main movement does not alter pinned selection. A separate source publishes
then exits nonzero: U stays provisional, F is computational failure with evidence/separate
cleanup, never silently success. Preserve first-run bytes and the never-started Q.

## 7. Negative history and loss stories

Use finite tests and independently valid packets, not merely malformed JSON:

- Genuine second matching Q packet is independently validated before replacing first-Q
  transport job/token/base claims; host read-only inspector rejects before successful
  observation publication, and authoritative receive rejects before A writes.
- Typed-complete P parented by expected Cq retains expected Q, but T references another
  matching Q; coherent U/F built on it reject at association, not missing-base validation.
- Relabel P/U/F receipts and roots, change ordered parents/final outcome/evidence/cleanup/
  diagnostic shape; remote validation or independent host/receive validation rejects.
- Wrong key/auth/connection before launch dispatch: Q retained, local marker retained,
  no invented T/failure, no automatic start retry.
- Lost observation/truncated/startup-noise frame after remote selection: A/earlier packets
  unchanged; explicit new observation is transport-only, never another attempt. It may
  retrieve newer history, not promise the lost response's exact selected snapshot.
- Safe private execution loss before child spawn leaves unknown P; after actual child reaping
  but before F leaves unknown P/U; missing final fields stays working despite local SSH exit.
- Post-F response loss permits fresh observe of the same Q/T/F, not another execute.
- Genuine production-profile overflow retains B F but no successful done packet.
- Late explicit-ref/raw-ref/map-full/consuming-commit errors after genuinely new actual-A puts
  leave no batch; actual pre/post-storage-commit interruption proves no batch versus complete
  import despite missing response. Retrying transfer is never computational retry.

No killing/disconnecting a worker with a live computational child for test convenience.
On catchable errors release cooperative gates, retain/reap local owner and prove remote writer
stoppage through fixture control before cleanup. If that cannot be proved, retain fixture/B
and report blocker/uncertainty. No arbitrary PID signaling or portable remote-survival claim.

## 8. Evidence and explicit retirement

Record normal installed SSH stream/helper/child/reader provenance separately from host helper
coverage/private barriers. Confirm no shared mount and actual loopback-only listening profile;
inspect current image/bare cached closure/native/wheel bytes, not old package names alone.
Keep secrets out of prompts/logs/Git; packet full-history copying is caller policy.

After review, archive required B/unknown histories/packets and nonsensitive provenance, prove
owned writers stopped, then explicitly retire only owned fixture/private keys. Image/evidence
retention is separate policy. Fixture/transport retirement is not B's recorded scratch cleanup.

This story authorizes no implementation/spec edit, worker, service/container/SSH connection,
experiment/build/provisioning, commit/push/CI or later turn. Its mechanics need review/approval
and separate bounded GO.
