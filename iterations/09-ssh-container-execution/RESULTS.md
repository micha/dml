# Iteration 9 implementation results

Status: **bounded implementation, independent acceptance, focused publication and final
exact-SHA CI are COMPLETE AND STOPPED** through
**`29ed39be6c1c18e6d57f782dd073acd37939c71c`**, all six final jobs successful. Initial
`f63ac75` CI had five successes/Windows three failures; accepted one-file correction is
test-only. Prior unchanged caller-story early-completion reason remains **UNKNOWN**, not
called fixed/diagnosed merely because the final case passes. Fixture retirement is complete.
The user's GO supersedes
historical planning-only status in HANDOFF/DESIGN/EXAMPLE, not their stop line. Worker %215
owns implementation/tests/as-built/fixture/example and this report; coordinator %197 owns
review/design status. Shared-build freeze/release is recorded below. Publication requires
explicit coordinator acceptance.

## Preflight and fresh baseline

Read machine index/admin placement guidance, complete design instructions/discussion/
plan/example/handoff, implementation instructions/documentation guidance, required as-built
contracts/glossary, packaging/coverage catalog and Iteration 8 RESULTS/REVIEW. `/work` mounted.
`TMUX_PANE=%215` and process ancestry confirm existing worker (default tmux display instead
identified active coordinator %197). DML initially clean at
`f7113d7acb3a0fe35eed6cb0013d3074533aef51`; that existing local six-file diagram/maintenance
commit is unchanged and explicitly accounted for by coordinator as ancestor of an eventual
accepted normal push. Coordinator-owned design status changes remain preserved.

Fresh standard baseline, before measured source edits:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration9-baseline.{log,exit}`, **exit0**: **1089 Python tests** (159.16 seconds),
**seven C**, Python **2299/2299 statements**, retained native **1681/1681 lines,
132/132 functions,1562/1562 outcomes**, binding zero unsuppressed errors/existing624 runtime
contexts and **141 native CLI Valgrind processes**. The four diagram tests account for the
increase over Iteration 8's published1085; no prior CI substituted for this baseline.
Worker exclusively owned BOTH build/check and build/coverage throughout implementation.

Explicit `docker --host unix:///var/run/docker.sock info` confirms the local Linux x86_64
michas-robots daemon, `/work/docker`; no inherited DOCKER variables. Cached node22-bookworm
lacks sshd/build-package helpers. A labelled owned no-network preflight container exited,
was inspected (no mounts/no writer) and removed. No pulls/installations/global changes.

Coordinator approved an offline FROM scratch fixture using cached Nix runtime components.
Initial bare Python/OpenSSH/bash prerequisite image loaded current baseline wheels at
`/opt/dml`, proving loader/module availability before SSH claims. No host credentials or
configuration were copied. The bridge-mode fixture's container-loopback sshd produced the
correct banner, but host loopback-published32768 accepted TCP without a banner and direct
bridge-IP connection timed out. This is recorded as a failed bridge prerequisite, not a
passing namespace experiment or a diagnosed host firewall defect.

The user **explicitly approved host networking** with sshd bound to `127.0.0.1:32769`,
without host firewall/service changes or mounts. Actual bind/listener inspection passes.
This preserves filesystem/runtime/SSH separation, **not network-namespace isolation**.
The failed bridge fixture was inspected writer-free, stopped and removed before replacement.

## Actual engineering choices

- Narrow public `exchange.read_exchange_spec(workspace)` promotes the existing bounded strict
  job parser, returning owned ExchangeSpec without B/import/ref/dispatch. Original local
  fresh-Q and caller-Q modes remain readable; unchanged execute/receive remain authoritative.
- Separate public `daggerml.ssh`: frozen explicit SSHRemote/SSHExchange, caller-Q-only
  stage/execute/fetch, independent expected and separate retained host control directory.
  Remote workspace is configured POSIX root plus caller token, never server-selected.
- Fixed installed `daggerml.ssh_worker` has only stage, execute, fetch. Stage creates only
  job/input; execute calls public existing exchange once; fetch never registers, executes,
  finalizes or repairs. SSH-layer framing helpers are shared inside that ownership boundary;
  no private exchange/local/transfer or duplicate native/job/role codec is used in runtime.
- Four-byte big-endian header length, strict <=8192 UTF-8 JSON with exact format/sizes,
  fixed binary bodies bounded by existing descriptor/transfer limits and required EOF.
  Stage gets empty-body ack; execute requires empty streams; fetch yields only a transport
  candidate. Owned job bytes are parsed through public exchange in allocated temporary
  scratch, not a second read of a mutable source file. Receipt-last files may remain partial
  on filesystem errors; neither framing nor SSH status asserts computational outcome/done.
- Fixed local OpenSSH argv uses shell=False/-F none/-T, explicit strict known-host/identity,
  noninteractive public-key-only auth, no agent/global-known-hosts/updates/proxy/jump/
  forwarding and finite connection/wait budgets. Remote command tokens use POSIX quoting.
  Remote paths are POSIX/NFC/control-free independent of caller OS; endpoint/user injection
  and credential SSH-expansion characters reject. Native local separators become forward
  slashes in credential options; actual Windows OpenSSH invocation is not claimed.
- Local dispatch marker is acquired after arguments/streams and **before Popen**; retained
  on spawn, SSH255/auth/key/timeout/response loss. Remote existing started marker remains
  independent. Repeat local dispatch has no second Popen; direct fixed remote repeat also
  rejects without another recorded T or computational-start counter increment. No global
  exactly-once/capability, marker clearing, automatic retry/reconnect-and-execute or recovery.
- File-backed stdin/stdout/stderr avoid pipe-write/unread-stderr deadlock and unbounded
  in-memory diagnostics; logs/disk and ordinary spawn/filesystem calls are not hard quotas.
  Normal error cleanup reaps only acquired **local SSH client**, not remote processes.
  If disposition cannot be established, SSHError.process retains the actual local Popen for
  explicit caller ownership/reaping, with a fixed actionable message. Other SSHError.process
  is None; normal TimeoutExpired remains after successful local cleanup. This is not a saved
  remote PID/process-recovery seam.
- Endpoint-driven maintained example records two matching Qs from the same C, nonzero-after-U
  failure/evidence and never-started Q, with real prior Q/T/publication and composite-only
  descendants. A and staged inputs go offline while separate control remains available.
  Caller-owned main movement is independent; exact explicit-ref receive preserves Q/submission/
  sentinel refs. No Docker/runtime dependency or general framework is added.

As-built authority is [ssh-execution.md](../../../dml/docs/spec-next/ssh-execution.md);
[fixture instructions](../../../dml/tests/ssh/README.md) own explicit local test operations.
Native/core/local/transfer/CLI/old-spec/version/adapter/workflows remain unchanged. Reviewed
LMDB diagram: transport/fixture/control files introduce no native entity, key family, packed
field/hash-facet or displayed ownership change; leave the existing as-built diagram unchanged.
Its four focused tests remain in the passing default suite.

## Host tests and meaningful failure distinctions

Final focused suite **100 passed**, `/tmp/dml-iteration9-focused7.log`. Earlier checkpoints
are preserved: first75 cases had three private harness unpacking errors (caller fixture has
five fields); later fetched rollback had two private fresh-reader assumptions that conflicting
refs were absent. Corrected to independent whole typed-batch absence plus preserved different/
raw-ref checks, never ref repair/deletion or a production defect claim.

Host tests cover strict endpoint/path/command profiles, quote/config construction, original
8192/32MiB exact limits and boundary+one, malformed/deep/duplicate/UTF8/constant/bool/overflow/
missing/unknown/truncated/extra/startup-noise framing, partial reads, acquired-stream/file/
receipt-last failures, absent completion, exact fetched job selection, local spawn/wait/
terminate/kill/reap and explicit retained-owner failure. Actual local subprocess tests write
1MiB stderr without pipes and safely terminate/reap a sleeping local child on timeout. These
are not actual remote-child failures or process-memory evidence.

Fetched candidates exercise **successful genuinely new actual-A puts/readback** before late
return-ref conflict, raw malformed ref and substituted native consuming-commit EIO; validation
store/preexisting Q rows do not count. Fresh independent readers prove old typed bytes and
entire new-batch absence; compact exact whole-file equality preserves raw corruption.
Real 1MiB-map A receives a genuinely new 2MiB computed result and fails after successful new
puts; restore comparable original map extent before exact-byte comparison (Windows portability),
then explicit whole receive with8MiB succeeds with no further SSH/computation. Actual receive
processes pause before storage commit versus after successful commit/before response: absent
batch versus complete import, with no live computational child. Consuming-commit EIO is private
native dependency substitution, not physical disk/power failure.

Default tests also retain typed-complete expected-Cq P/retained expected Q/T-to-other-matching-Q
association rejection, independently valid Q2 token/base rewrites and unchanged authoritative
outcome/evidence/diagnostic/cleanup restrictions. Receive/fetch no-registration/no-execution spies
and full typed byte oracles remain distinct from transfer traversal/CLI prefixes.

## Actual installed local SSH gate

Build uses only existing packaging tools and cached runtime, from implementation/tools shell:

```sh
bash tests/ssh/fixture.sh build "$PWD/build/iteration9-bare" \
  "$PWD/build/iteration2-packaging/bin/python" /run/current-system/sw/bin/python3
bash tests/ssh/fixture.sh start "$PWD/build/iteration9-bare" 32769
env -u PYTHONPATH build/iteration9-bare/context/rootfs/opt/dml/bin/python \
  tests/ssh/integration.py build/iteration9-bare /tmp/dml-iteration9-integration-final
```

All final build/start/gate **exit0**. Final gate **271 explicit check calls** plus actual child,
fresh receiver and CLI assertions; `/tmp/dml-iteration9-integration-final.{log,exit}`.
This is worker evidence, not coordinator rerun or instrumented installed-process coverage.

Final local image **`sha256:c6d943eed99071c46e4f1cb292cba705d614330713033e317bcf2b4969e7bcff`**.
Explicitly bare cached Python3.13.15/OpenSSH10.5p1 and tools-shell noninteractive bash closure:
**36 store paths/~240MiB**, no pytest/Hypothesis/coverage/tool-env closure. The initial estimate
was37/~248MiB with the interactive system bash; these are measured different cached shell roots,
not downloads. Exact paths are in `../dml/build/iteration9-bare/closure.txt`.

- Core wheel `daggerml-0.1.0-cp313-abi3-linux_x86_64.whl`, SHA256
  **`c4a88e87dbeba89b77ad3c455249872863b13e09a9290f60fcffa86eef9ec4e3`**.
- Console wheel `daggerml_cli-0.1.0-py3-none-any.whl`, SHA256
  **`f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`**.

Final runtime/image contains current wheel modules, native core and package-relative CLI,
not a checkout-backed/PYTHONPATH runtime or stale published package. All **seven core modules**
match maintained source bytes through independent container control; normal computational child
independently checks `/opt/dml/bin/python`, installed package/native path and emits provenance.
Copied Nix loader/libc paths are image contents; actual inside-container module/core/worker/console
execution and empty runtime mount inspection prove local compatibility. Native extension/executable
exact wheel-byte comparison and final inventory/static checks are recorded below. No tag rewriting,
committed VCS sdist, earlier-Python/manylinux/other-platform installed claim. The copied venv is an
explicit tested fixture prefix, not general portable relocation: console is invoked through
`python -m daggerml_cli.main`, not unvalidated pip-generated relocated shell entry launchers.

A prior reproducible fixture build inadvertently inferred the development Python env:46 cached
paths/~272MiB including nine unnecessary test dependencies. Gate3 passed271 functional checks,
but that was not the final only-needed runtime. Audit corrected fixture build to require explicit
bare runtime argument; coordinator authorized bounded stopped-container replacement after archive.
Old `/work`/B and nonsensitive provenance/logs are retained under `build/iteration9-final/retained-work`
and `/tmp/dml-iteration9-replaced-final-provenance.log`; old credentials remain protected, never logged.
Only the labelled stopped owned container was removed. No global image prune/deletion.

### Normal installed versus private loss evidence

- Normal path uses actual fixed installed stage/execute/fetch through binary SSH. Stage-only
  inspection finds only job/input, no B/T. A and host input files are offline during execution.
  Exact Q survives; only fresh T/P relative to Cq, ordered P/U/F, two matching requests/distinct
  Q/T/equal11, nonzero-after-U failure/evidence and separate cleanup, and missing child interpreter
  after P as recorded launch failure. Host invocation exit is never an A outcome.
- Independent public breadth-first **all typed objects/every packed byte/every parent** at
  stopped-writer copied B, independent packet store and A; prior genuine Q/T/pub and composite-only
  descendants included. Mutable B refs are not copied. Ordinary CLI confirms selected history,
  not used as closure oracle. Actual local guard and direct installed remote repeat keep start
  counter and exact history unchanged.
- Actual unknown/changed host keys and wrong authentication key yield finite SSH255 before B/T;
  Q and dispatch marker remain. Actual helper and root contain spaces/apostrophes/semicolons/
  command substitution with no injected side effect. Initial quoted single-interpreter symlink
  lacked adjacent venv config and failed import (fixture error, not quoting defect); fixed by
  quoting a complete compatible venv root while Q's child interpreter stays `/opt/dml/bin/python`.
- Real unchanged production **4MiB+1** result is published, real child reaped, computation/cleanup
  recorded in B F; export fails and no completion/output candidate is available. Fetch never
  fabricates failure/done or repairs export. This is distinct from scaled limits/mocked errors.
- Explicit **private remote command** `tests/ssh/private_loss.py` (copied by fixture, not packaged,
  installed fault import or normal worker branch) barriers cover lost stage ack, before child
  spawn P, after actual child reaping/before F P/U, closed F/files before response and interrupted
  fetch. Local SSH is timed out/reaped; remote disposition is inspected separately. `finally`
  releases gates/proves owned writers stopped on all error paths; failure would retain blocker,
  not conveniently stop an unknown writer. No live computational child is sacrificed. Fresh
  normal fetch after response/fetch loss returns identical closed Q/T/F files without execution.
  Unknown P/U fetch errors leave history unchanged/no fake packet.
- Endpoint is **stopped but B retained before fresh installed packet-only receivers** with
  independent saved expected. Main independently advances; sentinel/submission/Q refs remain,
  B refs absent, exact same-ref repeat nonexecuting. Valid Q2 receipt token/base rewrites reject
  before A changes. A genuinely typed-complete P parented by expected Cq retaining expected Q,
  but T referencing another matching Q with coherent U/F, rejects specifically initial association,
  not missing-base/foreign-Cq; full independent typed-byte validation precedes that rejection.

Final stopped container/B/image/endpoint/credentials remain **retained for independent review**.
`build/iteration9-bare/endpoint.json`, image/closure/wheel metadata and final story provenance/
summary/packets/expected are retained. Credentials are protected in ignored700 directory; no key
values enter Git/logs. The coordinator can explicitly restart only this endpoint for an independent
new-workspace probe. No final removal until coordinator fixture release. Previous prerequisite/
intermediate fixtures were stopped/writer-free and evidence retained before bounded retirement.
Fixture retirement is separate from recorded B computational scratch cleanup.

## Mutation gap and selected negative oracles

Existing tools shell has neither mutmut/cosmic_ray command/module; no bootstrap. Mull does not
supply Python mutation assurance. Private ignored `build/iteration9-oracles/probe.py` uses only
in-memory substitutions, leaving maintained/installed source unchanged. Aggregate
`/tmp/dml-iteration9-oracles.{log,exit}` **exit0**: **nine selected mutants**, each pytest **exit1 /
one intended test failure**, not collection/setup errors:

1. Ignore exact initial T-to-Q association.
2. Overwrite dispatch marker and permit repeat Popen.
3. Remove remote POSIX quoting.
4. Confuse configured remote helper interpreter with host interpreter.
5. Disable strict host-key enforcement option.
6. Ignore exact frame EOF.
7. Execute/register during fetch (blocked by no-execution spy).
8. Treat nonzero invocation as normal transport completion.
9. Publish actual A rows before selected-history validation.

This is selected oracle effectiveness, not a framework mutation score, broad security audit,
installed branch coverage or equivalent-mutant assertion.

## Stable default, static and source-freeze gates

Final stable runtime/tests/example standard:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration9-standard1.{log,exit}`, **exit0**: **1189 Python** (163.10 seconds),
**seven C**, Python **2637/2637 statements** (SSH226/fixed helper41/example69;
public exchange reader adds2), retained native **1681/1681 lines,132/132 functions,
1562/1562 outcomes**, zero unsuppressed binding errors/existing624 runtime contexts and
**141 CLI Valgrind processes**. No runtime/test/example source change during this run.
No new coverage exclusion, source omission, suppression, gate weakening or reduced boundary input.
Host statements are not every Python branch or instrumented installed SSH/child coverage/memory.
Existing precise native exclusions/runtime suppressions/unsupported finalizer abandonment remain.
An intentional runpy test emits the existing-module RuntimeWarning; it is not a skipped/failing gate.

Final Black check covers nine new runtime/example/test-support Python files; shell syntax,
whitespace and **17 changed Markdown documents/450 local targets and anchors** pass across
both checkouts. Collection has **1189 total/100 new SSH cases**, maximum new full ID **128**;
oversized binary inputs retain explicit short IDs. Final core/console/source comparisons pass:
all seven wheel/maintained/installed modules equal, console forwarding equals maintained source,
and **remote native extension/executable equal every wheel byte** after copying from the stopped
bare container. Wheel inventory has only seven runtime modules, core/CLI/type data/metadata;
no test/private fault/fixture/key/image support is packaged. Credentials are ignored; index empty.

Exact final **22-file** source hash manifest:
`../dml/build/iteration9-bare/source-freeze.json`. It covers runtime/example, four host test files,
five fixture/support files, existing public job seam/install inventory and owning/navigation/
coverage documentation; no native/local/transfer/CLI/old-spec/workflow/schema/version/diagram edit.
The final bare runtime/image/endpoint paths are those above; stopped container is
`dml-iteration9-ssh`, host installed Python
`../dml/build/iteration9-bare/context/rootfs/opt/dml/bin/python`, endpoint
`../dml/build/iteration9-bare/endpoint.json`. Native/source/installed evidence is retained;
no final fixture removal until coordinator release.

Worker now **freezes all 22 implementation files and all shared build use**, and explicitly
**releases BOTH build/check AND build/coverage to coordinator** for independent full standard
and installed local fixture review/probe. No overlapping wipes/reconfiguration/edits. Any needed
resumption waits for returned ownership; report-only updates may record review evidence.
No staging/commit/push before explicit coordinator acceptance. Publication/final exact-SHA CI
remain pending. No extra agents, cloud/second-machine/remote Docker, global tooling/services,
detached supervision, release/tag/package publication, native entity expansion or later turn.

## Independent acceptance and focused publication

Coordinator accepts the frozen **22-file** slice with no outstanding within-scope finding;
[REVIEW.md](REVIEW.md) owns independent evidence. Fresh coordinator standard **exit0**:
**1189 Python/seven C**, Python **2637/2637**, unchanged native/memory/141CLI gates. Separate
offline coordinator venv/custom actual SSH new-workspace workflow **177 checks/exit0** computes42,
exercises two Qs/failure/launch/offline return/independent typed bytes. All **11 package artifacts**
match every wheel/host/remote byte; all22 frozen hashes remain unchanged. Initial independent
private oracle expected too narrow an exception on foreign-Cq and was corrected/rerun, not a
production fix. Coordinator returns BOTH builds and authorizes focused publication and final
fixture retirement; this is reported independent evidence, not worker rerun.

Worker verifies existing **master/origin https://github.com/micha/dml.git**, initially empty
index, exact22 accepted source hashes and no other implementation changes. Stages **only** those
22 files; reads the full **3228-line** staged diff, `/tmp/dml-iteration9-reviewed-staged.diff`.
Staged whitespace passes; **2976 insertions/3 deletions**. No design notes/credentials/ignored
scratch/image/install evidence staged. Focused commit
[`f63ac75fa03f78ce74c4ce8e3ff041a937a792a9`](https://github.com/micha/dml/commit/f63ac75fa03f78ce74c4ce8e3ff041a937a792a9)
(`Execute caller-pinned requests through synchronous SSH`) and normal `git push origin master`
**exit0**. Implementation tree/index clean; exact remote master matches.

Push fast-forwards published `865bb79` through two commits: the **unchanged pre-existing
six-file diagram/maintenance `f7113d7`** and the new accepted **22-file runtime/transport/test/docs
`f63ac75`**. Prior f7113d7 is explicitly authorized ancestor, not Iteration9 runtime work, and
was neither amended nor dropped. No force push/new remote/tag/release/package publication.

### Authorized final fixture retirement

After coordinator's stopped/writer-free independent probe, worker independently verifies final
container label, **State.Running=false**, exact bare image and empty mounts. Archives final `/work`
(including all B/unknown/completed histories and coordinator workspaces) to
`../dml/build/iteration9-bare/retained-work`, nonsensitive container provenance to
`retirement-provenance.json` and sshd logs to `/tmp/dml-iteration9-retired-sshd.log`.
Runs only `tests/ssh/fixture.sh remove` for this owned stopped container, removing its final private
key artifacts; verifies final host/client private files absent. Also retires **14 explicit
worker-created prerequisite/intermediate and private wrong-auth key artifacts**, by fixed
owned file names only (no historical path authority); public known-host/probe evidence remains.
No labelled fixture container or32769 listener remains. Bare image and nonsensitive
packets/expected/closure/wheel/native/probe evidence remain. No global prune/image/volume deletion,
arbitrary PID/historical scratch deletion or computational cleanup reclassification.

### Exact-SHA CI monitoring

Existing gh2.102.0/Context7 `/websites/cli_github_manual` confirms exact-commit run/job/log/watch
semantics; no bootstrap/configuration/secret output. Exact-SHA list reports sole automatic **push**
[CI run40699187591](https://github.com/micha/dml/actions/runs/40699187591), matching published SHA,
with all six expected jobs in progress. No manual dispatch/rerun/release workflow.
Finite `timeout 900 gh run watch 40699187591 --repo micha/dml --exit-status --interval 10`
is active; `/tmp/dml-iteration9-ci-watch.{log,exit}`, current run/jobs JSON and exact-commit list
are retained. Final completion requires **all six exact-SHA jobs successful**, final clean tree
and matching remote. Any CI failure will be diagnosed and a focused fix proposed for review;
no speculative source edits, disabled tests or weakened gates. Final results follow.

## Initial CI failure and bounded test-only correction

Initial [run40699187591](https://github.com/micha/dml/actions/runs/40699187591) completes **failure**
for exact `f63ac75`: five Unix/strict jobs successful; [Windows job122854042778](https://github.com/micha/dml/actions/runs/40699187591/job/122854042778)
fails **three tests**, **1180 pass/five existing skips**,167.44 seconds. Finite watch exits1.
Full final run/job JSON/logs/exact-SHA list are preserved, not a cancelled/lost-header situation.
Initial gh job-log request correctly refused while the overall run was in progress; bounded
read-only REST retrieval required explicit terminal-escape permission to a file, then sanitized
before displaying bounded summaries. Actual Windows log is269466 bytes, not a huge padding diff;
`/tmp/dml-iteration9-windows-{api,sanitized}.log` and final complete CI logs remain retained.

Two **new** SSH example host-harness failures are confirmed: `replace(endpoint, python=sys.executable)`
sets the POSIX remote helper to Windows `D:/.../python.exe`, correctly rejected by production
POSIX validation before either story can run. This is a private test-model portability defect,
not a production validation bug or permission to relax the remote profile. Coordinator approves
only a test seam translating the example's endpoint-declared child binding to the actual host
interpreter while the public SSHRemote remains POSIX. Different explicit interpreter spelling
is preserved. Two short-ID POSIX/Windows-spelling regressions test that translation and retain
production rejection of Windows spelling as a POSIX remote helper. Normal installed/runtime/
example/fixture/wheel bytes remain unchanged.

Proposed **one test file/+63/-5**, `tests/python/test_ssh_example.py`, is reviewed with no outstanding
patch finding. Focused **102 passed**,exit0,6.23 seconds;
`/tmp/dml-iteration9-ci-fix-focused.{log,exit}`. Stable fix standard
`/tmp/dml-iteration9-ci-fix-standard.{log,exit}` **exit0**: **1191 Python/seven C**,
159.35 seconds, Python **2637/2637**, unchanged native1681/132/1562, zero unsuppressed
binding errors/existing624 runtime contexts and141CLI memory processes. No source changes
during the run. Black/whitespace pass; index empty. One changed test SHA is frozen at
`../dml/build/iteration9-bare/ci-fix-source-freeze.json`; other21 original hashes are unchanged.
Worker **freezes the fix/all source and explicitly releases BOTH build/check AND build/coverage**
to coordinator for the short independent postfix suite. No further standard rerun needed;
no fix staging/commit/push before explicit acceptance.
Proposed diff: `/tmp/dml-iteration9-ci-fix-proposed.diff`; no other implementation file changed.
No gate/skip/input weakening, runtime/old-source/workflow edit or new installed-runtime claim.

The third failure is **unchanged prior caller story**, `test_caller_story_host_helpers_full_typed_bytes_cli`:
handle2 asked for publication but observed completion. Timestamp evidence places the whole test's
failure approximately0.84 seconds after the preceding malformed-decoding case; this is **not evidence
of the fifteen-second gate expiring**. Its underlying child outcome/reason is **unknown**: temp B/
child stderr was not uploaded. No timing/flakiness/production-defect diagnosis is claimed.
Five separate local repetitions of that case plus its immediately preceding native malformed
case pass (**ten tests**, each2-case run roughly2.5 seconds),
`/tmp/dml-iteration9-old-caller-repeat{,-1,-2,-3,-4,-5}.log`/`.exit`.
These Linux repetitions are not a Windows reproduction or cause explanation. No prior example/
runtime/test source was changed. Coordinator directs preserving uncertainty and checking whether
it recurs on the next exact-SHA CI; repeated failure requires narrowly reviewed diagnostics,
not an assumed deadline increase, weakened test or automatic computational retry.

## Focused correction acceptance and publication

Coordinator independently validates the frozen SSH suite plus unchanged caller example:
**104 tests passed**, **exit0/7.99 seconds**, all22 combined original/fix hashes and whitespace
verified. No outstanding one-file adapter finding. Coordinator accepts only that correction,
returns BOTH builds and authorizes focused commit/push/new exact-SHA CI, not other source work.
The initial Windows caller reason stays unknown; if repeated, focused diagnostics need review.

Worker verifies original21 and accepted fix1 hashes, empty index and existing master/origin;
stages only `tests/python/test_ssh_example.py`, reads complete staged diff at
`/tmp/dml-iteration9-ci-fix-staged.diff`, staged whitespace passes. Normally commits/pushes
[`29ed39be6c1c18e6d57f782dd073acd37939c71c`](https://github.com/micha/dml/commit/29ed39be6c1c18e6d57f782dd073acd37939c71c)
(`Keep SSH example host tests separate from POSIX endpoints`), **exit0**, **one file/+63/-5**.
Implementation tree/index clean and exact remote master matches. Original runtime/example/
fixture/old source/wheels unchanged; no further installed build or actual fixture rerun needed
or claimed for this test-only correction. Prior f7113d7 remains unchanged ancestor.

Exact new SHA list reports sole automatic **push**
[CI run40701925587](https://github.com/micha/dml/actions/runs/40701925587), queued/in-progress.
Finite900-second `gh run watch --exit-status --interval10` monitors it; evidence at
`/tmp/dml-iteration9-postfix-ci-watch.{log,exit}` and `postfix-{ci,runs}.json`.
No manual dispatch/rerun/release. Final all-six exact-SHA success and clean matching remote
remain mandatory. No speculative old runtime/deadline/gate/skip change or later turn.

## Final exact-SHA success and stop

[Automatic CI40701925587](https://github.com/micha/dml/actions/runs/40701925587) finishes
**completed/success** for exact published SHA
**`29ed39be6c1c18e6d57f782dd073acd37939c71c`**, all **six** jobs completed successfully.
Worker's retained final job JSON and finite watch **exit0** independently confirm exact SHA,
six successes and automatic push event. Coordinator independently verifies its own direct
finite watch exit0, full final logs/completed JSON/exact-commit workflow list, clean implementation
tree/index and matching remote master, then directs RESULTS-only finalization and complete stop.
No further source/build/staging/commit/push/CI activity is needed or authorized by that directive.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40701925587/job/122863722474) | Success | 7 | 1191 passed,1 intentional warning;112.80s |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40701925587/job/122863722278) | Success | 7 | 1191 passed,1 intentional warning;91.28s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40701925587/job/122863722326) | Success | 7 | 1187 passed,4 existing skips,1 warning;278.05s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40701925587/job/122863722202) | Success | 7 | 1187 passed,4 existing skips,1 warning;145.38s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40701925587/job/122863722150) | Success | 7 | 1185 passed,5 existing skips,1 warning;172.15s |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40701925587/job/122863722036) | Success | 7 | 1191 passed,1 warning;129.00s;Python2637/2637 |

Counts/timings are verified in coordinator's saved final summary/full logs. Existing skips cover
unavailable `/dev/full`/Unix pipe support; Windows additionally has **one conditionally absent
POSIX literal-backslash credential-path parameter**, because native Windows separators become
forward slashes. It is a profile-specific parameter, not a failed test converted to skip or a
new blanket exclusion. Both new adapter regressions and the corrected story cases pass;
production/normal installed runtime/fixture/example/old source remain unchanged. CI strict is
informational **`-c`**, not local standard/memory `-v` or mandatory actual SSH gate evidence.
The runpy warning is the intentionally exercised existing-module main guard, not a hidden failure.

Final Windows log explicitly reports **PASS** for the unchanged prior caller-story case and both
new SSH example story cases. This validates current final behavior but **does not establish why
the old case ended early on initial CI**. Its first recorded failure, missing child reason and
five passing Linux repetitions remain preserved; there was no old-source/runtime/deadline fix.
No further CI fix, manual rerun/workflow or speculative diagnosis was performed.

Evidence: worker `/tmp/dml-iteration9-postfix-ci.json`, `postfix-ci-watch.{log,exit}` and initial
complete logs/job JSON/first Windows sanitized trace; independent coordinator
`/tmp/dml-iteration9-coordinator-final-{ci.json,ci.log,ci-summary.log,runs.json,watch.log,watch.exit}`.
Final publication is initial accepted **22-file/+2976/-3 `f63ac75`**, then accepted **one-test-file/
+63/-5 `29ed39b`**, preserving the prior separately authorized unchanged **six-file `f7113d7`**
ancestor. Unique Iteration9 implementation surface remains22 files. No design checkpoint/push,
force push/new remote, tag/release/package publication or later feature turn.

Final owned SSH container/private credentials are retired after known stopped-writer disposition
and full `/work`/B archive. Image, source/native/wheel metadata and nonsensitive packet/reader/log
proof remain ignored and retained; no global prune/unrelated resources/historical-path deletion.
Host-network deviation, only-needed36-path cached runtime, actual versus private transport/fault,
whole typed/raw/new-A-put atomicity, profile overflow, local-client versus remote reaping, rare
retained local owner, precise existing exclusions/memory suppressions/finalizer misuse, mutation
framework gap/nine selected probes, staged/installed/platform/security/full-capture/power-loss/
exactly-once and cleanup-versus-retirement qualifications remain explicit above.

**RESULTS is finalized. COMPLETE AND STOPPED.** No further source edits, builds/tests, staging,
commit/push, CI polling/reruns, fixture launch, design commit/push, additional worker, global
changes, release/package publication or later turn. Coordinator owns final REVIEW/COORDINATION/
design status reconciliation.
