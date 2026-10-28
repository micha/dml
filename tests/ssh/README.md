# Owned local SSH-host acceptance fixture

This is explicit test support, not a DML execution backend or packaged runtime. Normal
pytest/import/checks MUST NOT start Docker or SSH. Acceptance separately requires the
actual installed local SSH/container gate below; missing prerequisites are blockers,
not green skips. Runtime authority: [SSH contract](../../docs/spec-next/ssh-execution.md).

## Prerequisites and safety boundary

Use the already installed local Docker/OpenSSH/Nix tools and existing project packaging
Python/compiler/backend/dependency cache. Commands target **only**
`unix:///var/run/docker.sock`, never inherited context/remote Docker. No downloads,
package/bootstrap/global service/firewall changes or registry/package publication.
The fixture build is `FROM scratch`: copy only the cached Nix Python/OpenSSH/bash store
closure and current installed wheels. No host configuration or credentials are copied.
Missing cached tools/dependencies/ABI support require a separate provisioning decision.

The tested bridge fixture had working container-loopback sshd but blocked host bridge
connectivity. The user explicitly approved **host networking** with sshd bound to
`127.0.0.1` at a dedicated high port. This preserves filesystem/runtime/SSH separation,
**not network-namespace isolation**. Do not silently claim the original published bridge
profile passed or apply host networking to production. No runtime A/source/exchange/Docker
socket mounts. Docker may provide its ordinary container metadata files; no project data
is exposed through shared execution mounts.

One named/labelled container `dml-iteration10-ssh` is owned by this fixture. The unprivileged
`dml` account (uid1000) has a controlled public-key-only sshd profile; root login, password/
keyboard auth and forwarding are disabled. Keys are generated in the ignored fixture root,
not in image layers/Git. Known-hosts derives from the owner-created host public key through
trusted fixture control, not unauthenticated scanning. Use strict checking thereafter.
Never print/copy private key contents into prompts, logs or Git.

## Explicit offline build and start

From the repository, in the existing development tools shell:

```sh
bash tests/ssh/fixture.sh build "$PWD/build/iteration10-owned" \
  "$PWD/build/iteration2-packaging/bin/python" /run/current-system/sw/bin/python3
bash tests/ssh/fixture.sh start "$PWD/build/iteration10-owned" 32769
```

The packaging Python argument MUST identify an **existing** tool environment, not cause
installation. The separate runtime argument explicitly selects a bare cached Nix Python,
not the development Python env/pytest/Hypothesis/coverage closure. Inspect its resolved
store path and compatibility before use. A different caller-owned `build/` root can be used. The root has an ownership
marker; existing nonfixture roots reject. `start` needs a free port and new credential
directory; it never replaces/reuses an existing container or credentials. Port availability
precheck/start is not an atomic network reservation; startup errors retain owned artifacts.
Inspect actual listener/bind and daemon/container state before treating startup as successful.

The build records cached store paths (`closure.txt`), current wheel hashes (`wheels.sha256`)
and local image identity (`image.txt`). Wheels are built from current dirty source with
`--no-isolation`, not a committed VCS sdist/release. No wheel tags are rewritten. Copied
Nix loader/libc paths are image contents, not paths shared with the host. Installed Python
modules/native executable/extension remain exact wheel bytes and require inside-container
functional/provenance checks; host build success alone does not establish ABI compatibility.

The fixture's copied Python venv prefix runs explicitly as `/opt/dml/bin/python`. It is not
a portable general venv relocation mechanism: activation scripts and pip-generated shell
entry launchers can retain build-prefix spelling. The installed console is invoked through
`/opt/dml/bin/python -m daggerml_cli.main`, forwarding to its package-relative native CLI;
do not claim unrelated relocated entry launchers were validated.

## Mandatory installed gate

Using the **current installed host runtime**, outside source PYTHONPATH:

```sh
env -u PYTHONPATH build/iteration10-owned/context/rootfs/opt/dml/bin/python \
  tests/ssh/progress_integration.py build/iteration10-owned /tmp/NEW-DML-SSH-PROGRESS
# The gate stops its endpoint only after writer disposition. Explicitly restart
# that same retained endpoint for the existing synchronous regression gate:
docker --host unix:///var/run/docker.sock start dml-iteration10-ssh
env -u PYTHONPATH build/iteration10-owned/context/rootfs/opt/dml/bin/python \
  tests/ssh/integration.py build/iteration10-owned /tmp/NEW-DML-SSH-STORY
```

The progress gate retains actual SSHLaunch while fresh installed clients load saved identity,
observe P/U/F and exit. Remote named gate paths are created/reset/released explicitly through
out-of-band fixture control, without shared mounts or runtime command/gate actions. A/prepared
inputs are offline during execution. Wait timeout retains the execution connection; separate
observation clients never own it. Public all-typed/all-parent/every-byte oracles compare actual
remote runtime reads, independent packet stores and offline A. Normal finite computation,
provisional U/nonzero-after-U failure, repeated matching Qs, receiptless F, coherent selected
history, independent guards and explicit-ref conflicts remain inspectable.

Normal driver finally releases both gates, **unconditionally** waits/reaps every acquired
execution owner (including already exited clients), restores A and checks writers even when
another cleanup fails. Original assertion/transport errors and actual owner are preserved in
blocker descriptions. Every acquired concurrent observation reader is communicated/reaped on
errors; uncertain disposition retains actual clients as blocker evidence, never authorizes
endpoint retirement. Normal finite gates/binding are distinct from the example application's
potentially indefinite investigation retention after uncertain owner wait.

Normal operations use the actual installed fixed helper and binary SSH stream. The
synchronous regression gate additionally
checks source/native/worker/runtime provenance and an independently asserting computational
child; exact caller Q/only new T, prior real history/composite-only descendants, two matching
requests, success/nonzero-after-publication evidence/launch failure/separate cleanup, genuine
post-F 4 MiB+1 export rejection, strict unknown/changed-host-key/auth rejection and remote
one-shot guard independent of local guard. It checks actual quoted helper/root paths with
no injected side effect and leaves Q's child interpreter unchanged.

Independent public breadth-first oracles inspect every typed object, every packed byte
and every parent from copied stopped-writer B, bundle-validation store and A. They are not
transfer's private traversal or CLI prefixes. Fresh installed receivers operate with the
endpoint stopped, complete packets and independently saved expected, preserving caller
heads/submission/Q refs and absent B refs. Typed-complete expected-Cq/wrong-T-to-matching-Q
and independently validated Q2 packet swaps reject before A writes.

`private_loss.py` is **not installed** or imported by normal runtime. The fixture explicitly
copies it for finite substituted remote commands at stage acknowledgement, before child
spawn, after actual child reaping/before F, after closed completion files and during fetch/
observe. Interrupted observe is nonexecuting retrieval, never a computational retry.
It never sacrifices a live computational child. Gate release/disposition checks run in
`finally` on every error path. Failure to release/prove stopped writers raises a blocker
and leaves container/history retained, not a convenient automatic stop/removal. Private
command substitutions are not normal fixed-helper branch coverage, power-loss or arbitrary
remote-lifetime assurance.

Host default tests separately measure runtime helpers/framing/example and exercise successful
new actual-A puts/readback before late raw/different-ref, real map-full and substituted
consuming-commit errors, with fresh complete-state/compact exact-byte rollback oracles and
actual pre/post-A-storage-commit loss. Those substituted transport tests are not actual
installed SSH evidence. The installed gate is functional/provenance evidence, not host
statement coverage or a new installed-process Valgrind/mutation guarantee.

The gate stops the endpoint only after known owned-writer disposition, retaining B in the
container writable layer. It does **not** remove the container on transport error. Keep the
stopped container/image/endpoint/packets and nonsensitive evidence until independent review;
the coordinator can explicitly restart the same endpoint solely for a separate probe.

## Explicit retirement

After all intended history/evidence is retained and owned writers are proved stopped:

```sh
bash tests/ssh/fixture.sh stop "$PWD/build/iteration10-owned"
bash tests/ssh/fixture.sh remove "$PWD/build/iteration10-owned"
```

`stop` verifies fixture label and stops only its named container. Calling it is not itself
proof a computational child was already stopped. `remove` requires the labelled container
already stopped, explicitly disposes its writable-layer B and removes only fixture-owned
private key artifacts. Evidence/image/build artifacts remain ignored and caller-owned.
No `--rm`, prune/global deletion, arbitrary PID signaling, volume removal or historical-path
cleanup. Fixture retirement is separate from recorded B scratch cleanup/outcome.

Exact commands, counts, tested image/closure/wheel provenance, failures and retained/removed
status belong to [Iteration 9 results](../../../dml-design/iterations/09-ssh-container-execution/RESULTS.md)
and [Iteration 10 results](../../../dml-design/iterations/10-asynchronous-ssh-execution/RESULTS.md).
No second-machine/cloud, security sandbox, full capture, distributed exactly-once,
network-namespace isolation, detached supervision or production cleanup guarantee follows.
