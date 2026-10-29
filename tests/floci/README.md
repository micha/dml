# Explicit installed local Floci/Batch gate

This fixture is **never default-started, collected by pytest or packaged**. It needs
separate bounded local authorization. Runtime owns only the fixed
[Floci contract](../../docs/spec-next/floci-execution.md); Docker/controller/private
fault support is test-only. Actual installed DML inside Batch is mandatory acceptance,
not replaced by Node study jobs, prior packet replay, mocks or CI.

## Prerequisites and safety

- Explicit existing local `unix:///var/run/docker.sock`, trusted daemon
  `michas-robots`/`/work/docker`, socketGID131; no remote context/daemon/global changes.
- Already cached pinned Floci2.3.0 digest
  `sha256:09b72c45f333019adecb302e79c6b746e290135f528016c8514618bc7ab02344`,
  OCI revision `ee15f502bfc017861b67b076b82e1ccd032c7129`; retained released
  `application.yml` SHA256
  `99f54d4c62c72bfe7a7282d1e37c2613d6486f02730686cad1417eb4c81bc70a`.
- Explicit cached bare Nix Python/closure, project packaging Python/build/backend and
  existing compiler/tools shell. Missing pulls/downloads/installations are blockers
  requiring scoped approval, **not** implicit provisioning or passing skips.
- Fresh owned build root outside both shared builds; complete current dirty-source
  wheel route/host/image/actual-child package bytes. No VCS dirty sdist capture claim,
  tag rewriting, registry publication or arbitrary relocation/platform claim.

The service has daemon-root-equivalent socket authority despite nonroot/GID/cap-drop/
no-new-privileges. Trust the pinned emulator and finite trusted jobs, not hostile users.
Before computational submission prove internal private bridge/no host ports, exact
socket+new private data-volume mounts, user1001:GID131/service512MiB/1CPU/pids256,
robust **ALL128** released enable-key enumeration, effective exactly
Batch/S3/CloudWatchLogs/IAM and actual namespace **no9169**. No inherited host-network
workaround/shared project/A/exchange/runtime/credential mounts or cloud endpoints.

Job image uses current installed DML at `/opt/dml`, user1000:1000, memory512MiB.
Floci does not enforce CPU/PID ceilings or inherit service cap-drop/no-new-privileges
into job containers. Inspect actual user/caps/security/memory/mounts and computational
`/proc` evidence; this is trusted finite workload, **not adversarial confinement**.
Floci removes naturally exited job containers and cleanup is best-effort. Terminal
status is not proof of container/writer retirement or durable live restart.

## Explicit commands

Informative commands inside the existing project tools shell; choose a NEW root:

```sh
bash tests/floci/build.sh "$PWD/build/iteration11-owned" \
  "$PWD/build/iteration2-packaging/bin/python" /run/current-system/sw/bin/python3
python3 -B tests/floci/fixture.py start build/iteration11-owned \
  --application ../dml-design/feasibility/floci/runtime/sources/release/src/main/resources/application.yml
env -u PYTHONPATH build/iteration11-owned/context/rootfs/opt/dml/bin/python -B \
  tests/floci/integration.py build/iteration11-owned build/iteration11-owned/normal-story
# After the normal gate has proved writers stopped and stopped its endpoint:
env -u PYTHONPATH build/iteration11-owned/context/rootfs/opt/dml/bin/python -B \
  tests/floci/retained_integration.py build/iteration11-owned build/iteration11-owned/private-story
env -u PYTHONPATH build/iteration11-owned/context/rootfs/opt/dml/bin/python -B \
  tests/floci/loss_integration.py build/iteration11-owned build/iteration11-owned/loss-story
```

These examples document reproduction, not blanket permission to rerun/provision.
`build.sh` copies only existing bare closure, builds current wheels offline and a local
scratch image without pulls/network, verifies every package/native/CLI/module byte and
keeps image/wheel/artifact inventories. Controllers use immutable local image IDs,
preconfigured bucket/queue/exact revision, installed finite client processes and actual
S3 history transport. Docker cp is fixture input/client-packet/evidence control, **not**
the runtime result exchange or shared LMDB.

Normal gate: genuine prior Q/T/U history and composite-only children; two matching
same-C requests/distinct Q/T/equal42; never-started Q; nonzero23 after U with separate
cleanup/failure evidence while outer publication succeeds. Submitter exits before
initial gate release; fresh clients retrieve actual P/U/F. Independent public all-typed/
every-packed-byte/every-parent oracles compare actual gated B, packet validation and A.
Endpoint-offline receive preserves independently advanced heads/request refs/old bytes,
nonexecuting same-target repeats and no copied B refs.

## Private evidence is separate

`retain.py`/`Retain.Dockerfile` are an explicitly private image ENTRYPOINT outside the
installed package: invoke unchanged installed worker, then finite S3 hold **after its
return/known reap** to copy exact `worker.dml` and compare final B. They demonstrate
valid F while RUNNING/later outerFAILED75, genuine scratch cleanup failure and original
4MiB+1 recorded F export overflow/unreturnable history. Never permission-edit historical
scratch to force a full archive. Exact repository-only archive is distinct from a
successful full workspace copy. Original permission-copy/census failures remain qualified.

`lost_manifest.py` is private committed-phase response suppression after real S3 PUT;
installed package bytes remain unchanged. Caller/client substitutions for accepted
SubmitJob acknowledgement loss, truncated real S3 body and U-selection barriers are
likewise **private test evidence**, not physical packet loss or normal installed branch
coverage. No runtime arbitrary command/plugin/fault API is added. Unknown ack retains
guard/Q and blocks stop until explicit out-of-band exact token/manifest/container/job
correlation and natural reap; no automatic ListJobs repair/resubmit.

## Composed recorded-steps gate

Within separately authorized local scope, [composed_integration.py](composed_integration.py)
uses the same preverified current installed package/private profile: two same-C0/same-intent/
binding/inputs producers, then one selected consumer of actual R1/exact earlier T1f/factor2.
The standalone captured [consumer](../../examples/floci_double.py) computes84. Distinct actual
producer23-after-U42 and consumer23-after-U84 cases preserve failure/evidence without downstream
request or successful summary. Public P/U guards, exact association and all typed bytes/every
parent are checked, not only scalar84/service/digests.

Current cached wheel/host/image/native/module bytes must ALL match before reuse; no image tag
is current-source proof. Selected consumer final-B retention uses the separately verified cached
PRIVATE after-reap wrapper/current package; marker/actual NUL-component `/proc` census precedes
exact repository-only copy. That is not normal ephemeral-B durability. Original census using
literal backslash-x strings is qualified in results, not retroactively called accurate.

With a started, proved profile, run the composition controller. It establishes known
terminal jobs/ALL stopped clients/namespace absence, then archives/stops the service.
Only AFTER that succeeds, run the supplemental offline command:

```sh
env -u PYTHONPATH /current/installed/bin/python -B tests/floci/composed_integration.py \
  build/new-owned-root build/new-owned-root/new-story
env -u PYTHONPATH /current/installed/bin/python -B tests/floci/composed_offline.py \
  build/new-owned-root build/new-owned-root/new-story
```

First command needs a started/proved profile; it stops/archives only after exact writer proofs.
Second command requires that endpoint ALREADY STOPPED: supplemental copied packets/independent
saved selections, nine fresh installed receive processes and three native CLI readers preserve
independently advanced main/fixed refs/all old bytes and complete returned history. It launches
no computation/resume. Same-process repository wrappers in the main controller are separate
from these fresh-client checks. Commands are examples, not permission to provision/rerun.
The maintained [finite application modes](../../docs/composed-recorded-steps.md) expose public
request/stage/submit/observe/receive/basis/summary sequencing without a hidden test-only API.

## Disposition, archive and review

Controller records client NAME/create intent before Docker create and job token/intents
before computational submit. Lost create/submit acknowledgements remain explicit blockers.
Stop requires exact known job terminal identity/single attempt, **ALL owner-client census**
with stopped tracked IDs and no namespace job containers. A single bounded fresh census
can prove IDs naturally disappeared between list/inspect; persistent inspect errors or
newly present IDs are not retried away or silently accepted. Uncertain IO/writers retain
fixture/evidence, not convenient kill/stop/restart.

Release every owned finite gate on catchable errors and reap every client; no live-child
sacrifice. `fixture.py stop` only stops after those proofs, archives a fresh service-data
snapshot/logs and retains exact IDs/images/B/packets for independent review. It does NOT
remove containers/networks/volumes or act on historical scratch strings. Archive all
needed evidence before separately authorized identity-checked retirement of exact stopped
owned resources. No prune/prefix-wide deletion/unrelated-container disposal. Default-safe
[ownership regressions](../python/test_floci_fixture.py) start no Docker.

Actual commands/exits/source/image/platform/coverage/mutation limits and retained/retired
fixture status belong to [Iteration11 RESULTS](../../../dml-design/iterations/11-floci-batch-execution/RESULTS.md).
Full source freeze and explicit release of BOTH shared builds precede independent review;
publication requires explicit acceptance, not this README or a passing private gate.
