# Iteration 10 implementation results

Status: **COMPLETE AND STOPPED** through published
**`099d156fb49f81a7da0683898189a85c1172988c`**; all six final exact-SHA CI jobs succeed.
Earlier fixture/CI failures remain qualified below; final old-story passes are **not diagnosis
or an established fix** of their unknown Windows causes. User GO
supersedes historical pending-GO statements in DESIGN/EXAMPLE/HANDOFF, not scope/stop lines.
Worker %215 owns runtime/tests/as-built/example/fixture and this report; coordinator %197
owns REVIEW/COORDINATION/design status. No commit/push before explicit acceptance.

## Preflight and fresh baseline

Machine instruction index/admin indexes and placement guidance, complete design instructions,
README/discussion/Iteration10 DESIGN/EXAMPLE/HANDOFF/COORDINATION, implementation instructions,
documentation guidance/as-built contracts/glossary, packaging/coverage/fixture guidance and
Iteration7/8/9 RESULTS/REVIEW read. `/work` mounted. `TMUX_PANE=%215`, Pi491011 verified;
DML clean at `a94e6f51bb41ad2cfab4fad1dd2e96c97a3e728d`. Existing separately authorized
unpublished diagram/test maintenance is preserved unchanged as eventual normal-push ancestor.
Design baseline `28cbff2`; coordinator-owned AGENTS/COORDINATION edits preserved.
Worker exclusively owns **both build/check and build/coverage** until source freeze/release.

Fresh standard baseline completed before measured edits:

```sh
cd ../dml
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration10-baseline.{log,exit}`, **exit0**: **1193 Python tests** (159.04s),
**seven C executables**, Python **2637/2637 statements**, retained native **1681/1681 lines,
132/132 functions,1562/1562 outcomes**. Binding zero unsuppressed errors/existing624 runtime
contexts; **141 CLI Valgrind processes**. Intentional existing-module runpy warning retained.
No prior CI substituted for baseline; no threshold/exclusion/suppression change.

Explicit local Docker `unix:///var/run/docker.sock` reports michas-robots Linux x86_64,
`/work/docker`; cached fixture image exists, no previous labelled container or32769 listener.
Existing packaging Python and bare cached Python3.13.15 available. Old image is not current
installed-source evidence; rebuild/current provenance/actual gate still pending. No pulls,
installation/global service/firewall changes. Approved fixture remains loopback-only host
network/no shared mounts, not network-namespace isolation or second-host proof.

Context7 `/python/cpython` confirms Popen.wait timeout can be caught/retried and PIPE-backed
wait deadlock risk; production uses file-backed streams and retains live execution ownership.
No detached lifetime/supervisor promise, automatic retry/cancellation or later turn.

## Actual engineering choices

- Public `exchange.read_observation(packet, expected=...)` shares the existing owning
  packet/history authority with receive. A private internal read returns owned bundle plus
  description once; receive atomically imports those same bytes, not a second file read.
  Inspection imports only into disposable validation storage, closes/cleans before return,
  has ref=None/nested completion ref=None and never opens/writes A or executes source.
- Saved SSH directory composes public exchange handle save/load at `expected.json`
  (`workspace` means host control) plus strict bounded operational `ssh.json` last.
  Exactly format/seven SSHRemote fields; remote B remains derived from root/token, no duplicate
  ExchangeSpec/role/native codec. Each file keeps8,192-byte budget. Save/load never consult
  control/input/A/B/endpoint, connect/signal/dispatch or serialize PID/live state. Credential
  paths only, out of band/ignored; trusted single-owner files, no partial repair/overwrite.
- `start_ssh_exchange(connect_timeout_ms=...)` uses the **same fixed foreground execute**,
  preallocated argv/file-backed stdout/stderr/SSHLaunch, DEVNULL stdin and shared local
  dispatched guard before Popen. No wait for auth/readiness/T/computation, postspawn receipt
  IO/owner allocation, remote backgrounding, service/supervisor or hidden registry/finalizer.
  Synchronous execute and second start reject each other's marker; remote started is separate.
- `SSHLaunch.job/process` retains actual local Popen/acquired resources. Wait uses seconds,
  transport status/empty stdout only; timeout/uncertain errors preserve owner/streams and never
  automatically kill/disconnect. Known disposition disposes all streams even on status/noise/
  seek/read/stack-close error; repeat returns cached status or cached postreap error. Acquired
  observation-client shutdown uncertainty instead retains SSHError.process, never targets
  this execution connection or proves remote computational descendants stopped.
- Fixed installed helper adds only nonexecuting `observe`, public coherent ExchangeHandle/
  observe_exchange once. It fully owns bounded job/observation/snapshot bytes in temporary
  packet storage, matches owned expected and disposes scratch before emitting successful frame.
  Bootstrap has only exact job/no snapshot; malformed readiness/history is error, not fallback.
  New fixed `bootstrap`/`observation` frame labels retain existing exact sizes/EOF authority;
  no transported lifecycle/process/result/success claim is trusted.
- Host owns full frame, matches caller expected and uses public read_observation in temporary
  scratch; cleanup precedes new final packet allocation. Same owned snapshot/job/receipt bytes
  published receipt-last; IO/profile/validation/cleanup failures never report successful done
  or write A. Duplicate validation/temp IO is deliberate composition, not RSS/deadline/disk quota.
- Existing coherent immutable P/U/F selection, exact Q/Cq/only T, unknown/provisional versus
  recorded computation/separate cleanup and atomic explicit-ref A receive remain unchanged.
  Heads/submission/Q refs stay; B refs do not copy. Receiptless F is retrieval, not repair or
  finalizing unknown T. Old packets/ref targets never advance implicitly; import retry is not
  computational retry. No native/local/transfer/CLI/old-spec/workflow/version change.
- Maintained `ssh_progress.py` supplies prepare/own/observe/receive modes with a declared remote
  gate path and captured trusted finite source; gate control is externally owned, no Docker
  application import/shared mount/runtime command action. Normal gates/binding and waits are
  finite. On uncertain live-owner wait the application explicitly retains ownership/repeats
  bounded waits rather than killing/exiting; **investigation retention may be indefinite**,
  not a detached guarantee or hard normal-completion deadline. Coordinator accepts this refinement.

## Host checks and meaningful faults

`/tmp/dml-iteration10-focused1.{log,exit}`: **144 passed**, exit0; expanded exchange/caller/SSH
regression **766 passed**, `/tmp/dml-iteration10-focused-coverage.log`. That focused source
measurement reached exchange642/642, SSH326/328, helper57/58; the three meaningful misses
(saved original-profile overflow/host wrong observed job/remote owned-job substitution) then
received explicit tests, not exclusions. Additional initial focused **134 passed**, exit0,
`focused2`; example/fixture cleanup **21 passed**, `example-ownership`. Final new focused suite
**164 passed**, exit0/25.23s, `/tmp/dml-iteration10-focused-final.{log,exit}`. No failing new
functional test or excluded meaningful path at these checkpoints.

Tests exercise uncertain wait OSError/TimeoutExpired preserving streams/actual owner, known
reap status/noise/seek/read/close/repeated-error disposal, actual cooperative local nonwaiting
child/1MiB stderr, log/owner/spawn allocation failures and mixed start/synchronous guards.
Observation-only rare retained Popen is separately covered. Original metadata/frame8192 and
32MiB budgets/boundary+one, strict JSON/UTF8/duplicate/deep/type/unsupported/body-count/EOF/
noise/profile, offline saved identity and partial files remain meaningful rejection oracles.
Remote/host scratch cleanup failure precedes reply/packet; final packet IO retains partial
artifacts without successful return. No observer/executor/ref/A mutation is permitted.

Public inspector/host transport retain all existing typed-valid final role/parent/outcome/
evidence/diagnostic/cleanup checks. Real matching-Q2 history is independently validated before
swapping/relabeling; typed-complete expected-Cq retains expected Q but T references another
matching Q with coherent U/F, rejecting specifically initial association, not missing base.
Selected immutable pin is exercised through fixed helper transport while refs advance after
selection; existing actual coherent ref-race/concurrent-reader tests remain enabled.

Each P/U/F observed packet tracks **successful genuinely new actual-A puts/readback** before
late different/raw ref and substituted consuming-commit failure. Validation-store/preexisting Q
rows do not count. Fresh full typed/raw/compact exact-byte oracles prove entire batch absence.
Observed genuine1MiB-map/2MiB-result receive fails after new puts; reopening comparable original
map restores physical layout before exact equality, not research data. Explicit8MiB whole
receive succeeds with no SSH/computational retry. Actual receiver pre/post-storage-commit
barriers for all phases distinguish no batch from complete ref/history despite lost response.
Consuming-commit EIO is a private native dependency substitution, not physical disk/power failure.

## Current installed local fixture and actual gates

Commands from implementation/tools shell, no downloads/installations/global changes:

```sh
bash tests/ssh/fixture.sh build "$PWD/build/iteration10-owned" \
  "$PWD/build/iteration2-packaging/bin/python" /run/current-system/sw/bin/python3
bash tests/ssh/fixture.sh start "$PWD/build/iteration10-owned" 32769
env -u PYTHONPATH build/iteration10-owned/context/rootfs/opt/dml/bin/python \
  tests/ssh/progress_integration.py build/iteration10-owned /tmp/dml-iteration10-installed-progress3
# Same retained stopped endpoint explicitly restarted for synchronous regression:
docker --host unix:///var/run/docker.sock start dml-iteration10-ssh
env -u PYTHONPATH build/iteration10-owned/context/rootfs/opt/dml/bin/python \
  tests/ssh/integration.py build/iteration10-owned /tmp/dml-iteration10-installed-sync
```

Build/start exit0; logs `/tmp/dml-iteration10-fixture-{build,start}.{log,exit}`. Cached bare
Python3.13.15/OpenSSH10.5p1/bash **36-store-path** closure, no development/pytest/Hypothesis/
coverage runtime closure. Image **`sha256:b9f045cd2b65b6070a434035f52e04e5d9fa55709ef1dab987c0b76ad4fa179e`**.
Core wheel `daggerml-0.1.0-cp313-abi3-linux_x86_64.whl`, SHA256
**`767d1032c73f335588f47053cefe4b6f023adf7242ed8975940071aed6394385`**;
console wheel SHA256 **`f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`**.
Dirty current-source wheel, not committed VCS sdist/release/older-Python/other-platform evidence.
Copied Nix closure/venv at explicit tested `/opt/dml` prefix is image contents, not shared
runtime paths/general relocation promise. Console uses module forwarding, not unvalidated
relocated pip-generated entry launchers. Current wheel/host/remote eleven artifact bytes and
seven maintained source modules agree; computational child independently asserts installed
interpreter/package/native provenance and persists its diagnostic.

Final progress gate **393 explicit checks**, exit0,
`/tmp/dml-iteration10-installed-progress3.{log,exit}`. Separate synchronous regression
**271 checks**, exit0, `installed-sync.{log,exit}`; it preserves actual unknown/changed-host-key/
auth/quoting/remote repeat/production overflow/safe loss/offline exact-Q synchronous behavior.
Gate1 **276 checks** and gate2 **370 checks** are earlier successful normal workflows, not final
error-path assurance. Coordinator's read-only review identified missing unconditional finally
wait on already-exited owner and possible restoration/writer-check skips. The driver now
tries all gate releases/unconditional reaping/A restoration/stopped-writer checks, preserves
original/transport cleanup errors/actual owner and retains fixture/evidence on blockers.
Every acquired concurrent observation reader is communicated/reaped on catchable errors;
failure retains actual clients, not silently dropped ownership. Nine private fixture ownership
regressions are default-tested without Docker startup. Final393 gate uses these fixes.

Normal installed stream evidence:

- Exact stage-only job/input/no B/T; saved identity and fresh bootstrap client exit without
  dispatch. A and already-staged host inputs offline during actual fixed foreground execute.
- Finite out-of-band declared **remote** gates expose P then U while actual child remains gated.
  Fresh installed clients load saved directory/observe/exit; concurrent clients have distinct
  packets. Wait timeout retains execution owner/connection. External release permits F/cleanup,
  with explicit local reaping separate from retrieval and later A reception.
- Independent public breadth-first **all typed objects/every packed byte/every parent** compare
  actual remote reads, packet rows, independent validation store and A. Genuine prior Q/T/pub
  and composite-only children, exact Cq parent/only fresh T, preserved Q/initial fields, ordered
  P/U/F parents and result11. Two matching Q/T distinct/equal result; never-started Q retained;
  nonzero after U yields failure/evidence with separate cleanup.
- Existing synchronous completion/output removed after reaping: fresh observe still retrieves
  exact F without execute/ref/export repair. Old P/U remain unchanged/working. Direct remote
  execute repeat independently rejects; no additional T/history.
- Actual asynchronous unknown/changed host keys and wrong auth return255 before B/T, retaining
  caller Q/local marker and disposed known-reaped owner streams; no automatic retry.
- Real unchanged production **4MiB+1** result lets the child publish/reap and B record F, but
  execute export and fresh observe fail/no successful done packet. B retained; no profile waiver.
- Proven writer disposition precedes endpoint stop. Fresh installed packet-only P/U/F receivers
  with saved independent expected preserve advanced main/sentinel/submission/Q refs/old bytes,
  omit B refs and support nonexecuting same-target repeats. P-ref-to-F conflicts whole-batch.
  Independent validQ2 and typed-complete expected-Cq wrong-T-to-Q tests run at inspector/receive
  with whole actual-A physical-byte preservation.

Private command substitutions remain **separate** evidence: pre-readiness before T, pre-child
P, after actual child reaping/pre-F U and post-F/files keep foreground owner alive, then release
cooperatively and reap status75. P/U remains unknown/working; post-F retrieval is done despite
live owner. Interrupted observe sends only a frame prefix, times out/reaps its own observation
client, releases noncomputational helper gate, and fresh fixed observe retrieves same gated P
while the execution owner remains live. No live computational child is killed/disconnected for
convenience. These are private fixture scripts, not installed fault hooks or normal fixed-helper
branch coverage, physical power-loss or portable detached remote survival.

Final endpoint **stopped** with B/unknown/completed histories/image/keys/packets/evidence retained
for coordinator's separately prepared independent probe. Container `dml-iteration10-ssh`, label
`dml.fixture=iteration10`, empty mounts, host network, actual server bind127.0.0.1:32769; no final
listener. This is filesystem/runtime/SSH separation, **not network-namespace/second-host isolation**.
No retire/remove/prune until coordinator release after archive/stopped-writer proof. Fixture
retirement is separate from B's recorded computational scratch cleanup.

## Standard/static/mutation and independent review gates

Final stable standard:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration10-standard.{log,exit}`, **exit0**: **1357 Python tests** (187.33s),
**seven C executables**, Python **2828/2828 statements** (exchange642, SSH328, fixed helper58,
progress example66), unchanged retained native **1681/1681 lines,132/132 functions,1562/1562
outcomes**, binding zero unsuppressed errors/existing624 runtime contexts, **141 native CLI
Valgrind processes**. Runtime/tests/example sources were stable throughout this run; no new
exclusion/source omission/suppression/weaker threshold/boundary reduction. Host statement
coverage is not every Python branch or installed helper/child/memory instrumentation. Existing
precise native exclusions/runtime suppressions and unsupported foreign-last-owner abandonment
remain qualified; CI informational `-c` will not replace this local `-v` or actual installed gate.

Fresh tools-shell inspection finds neither mutmut/cosmic_ray command/module; no bootstrap.
Mull is not Python mutation assurance. Private ignored in-memory
`../dml/build/iteration10-oracles/probe.py` changes no maintained/installed source. Final
`/tmp/dml-iteration10-oracles-final.{log,exit}`, aggregate **exit0**, **eleven selected probes**:
each pytest **exit1/one intended test failure**, not collection/setup errors:

1. Kill execution connection on wait timeout.
2. Permit repeat dispatch/mixed guard.
3. Ignore exact T-to-Q association.
4. Execute during observe.
5. Trust nonzero local status as normal transport completion.
6. Remove remote POSIX quoting.
7. Disable strict host-key enforcement.
8. Ignore exact frame EOF.
9. Report done from initial P.
10. Export mutable current head instead of selected immutable pin.
11. Publish actual A rows before history validation.

This is selected oracle effectiveness, not a mutation-framework score/installed branch or
security audit/complete Python mutation assurance. The earlier nine-probe pass remains a
separate intermediate checkpoint; final eleven adds lifecycle/pin oracles.

Final Black check **ten new/changed Python files**, shell syntax, whitespace in both checkouts
and **12 Markdown documents/244 local targets+anchors** pass. All **eleven wheel/host artifacts**,
seven maintained Python module bytes and console source match; actual gate independently
compares those eleven host/remote bytes. Wheel inventory contains runtime/core/CLI/types only,
not tests/fixture/key/private-loss support. Credentials and all build/evidence artifacts are
ignored; implementation index is empty.

Final **24-file** implementation manifest:
`../dml/build/iteration10-owned/source-freeze.json`. It covers the three runtime modules, new
endpoint example/five host test files, fixture ownership tests/support/gates, owning/navigation
as-built docs and assurance catalog. Native/core/local/transfer/CLI/old-spec/workflow/schema/
version sources and the existing LMDB diagram are unchanged. Reviewed diagram/native model:
no new LMDB key/entity/body/hash/relationship or displayed boundary; saved SSH/owner/packet/
fixture files remain external application/transport state. No proposal boxes/native primitive
needed. All six diagram focused checks remain in the passing full suite; no new real-browser
or rendering claim.

Worker **freezes all implementation sources and all shared build use** and explicitly
**releases BOTH build/check AND build/coverage to coordinator** for independent review/fresh
standard/probe. Current stopped owned fixture/image/keys/B/evidence are also released for
coordinator's explicit independent restart/new-workspace probe, never retirement of uncertain
writers. Installed host Python:
`../dml/build/iteration10-owned/context/rootfs/opt/dml/bin/python`; endpoint:
`../dml/build/iteration10-owned/endpoint.json`. No further worker edits/builds/fixture operations
until ownership is returned. Report-only evidence reconciliation may continue. No staging/
commit/push before explicit independent acceptance. No extra workers, cloud/second-host/remote
Docker/global service/tooling/detached supervisor, release/tag/package publication or later turn.

## Post-acceptance staged audit finding (publication paused)

Independent acceptance returned both builds and stopped fixture, authorizing focused24-file
publication. Worker verified all24 accepted hashes/exact changed surface, empty starting index,
master/existing origin and absence of private-key markers. Only24 files staged; complete3304-line
staged diff read, `/tmp/dml-iteration10-reviewed-staged.diff`, staged whitespace passes.

That final staged read found a **fixture evidence defect before commit/push**:
`progress_integration.py` wrote literal backslash-n in changed_hosts instead of a newline.
AST and retained-file checks confirm no terminal newline; actual `ssh-keygen -l -f` rejects
that retained known-host file with255. Therefore the final393 gate's asynchronous changed-key
case is **malformed/unknown-host rejection**, not demonstrated genuine changed-key rejection.
Its earlier wording above is qualified by this finding. The existing271 synchronous gate
uses a proper newline and separately exercises genuine changed-key rejection; runtime argv/
strict enforcement and all other progress/independent evidence are unchanged. No production
bug or confirmed broken host-key verification is inferred.

Worker reported this immediately to coordinator and paused publication, requesting a focused
fixture-only newline/parse-oracle/regression correction and actual valid changed-key start
recheck. No commit/push has occurred. The stopped fixture had already been explicitly retired
under acceptance after full B/coordinator/unknown/completed archive and stopped identity proof;
any fresh validation uses only bounded owned local fixture/credentials, not global provisioning.

## Focused support-only post-audit correction

Coordinator approved correction of only `tests/ssh/progress_integration.py` and
`tests/python/test_ssh_fixture_ownership.py`, fresh protected local fixture using the unchanged
reviewed cached image/runtime, stable standard and actual gate, then revised source freeze/
independent postfix review before any commit. Other22 reviewed hashes/runtime/package bytes
remain unchanged; index was normally unstaged, no ancestor amended.

Fixture-only `write_changed_hosts` now writes explicit UTF-8/LF bytes, invokes actual
`ssh-keygen -l -E sha256 -f` for generated public key **and** known-host file, and requires
fingerprint equality before SSH. Genuine changed-key rejection additionally requires dedicated
`REMOTE HOST IDENTIFICATION HAS CHANGED` and `Offending ED25519 key` diagnostics in the actual
known-reaped owner's stderr, plus changed fingerprint different from the trusted fixture host.
Status255 alone is not that oracle. Context7 `/openssh/openssh-portable` confirms explicit
SHA256 fingerprint display/format; current actual tool parsing remains the decisive evidence.

Default support regressions check exact newlines/file bytes, parser rejection and fingerprint
mismatch without starting Docker/SSH. A Windows text-newline model demonstrated an initial
fixture exact-byte portability issue: its one focused case **exit1/one intended assertion
failure** with CRLF versus expected LF, `/tmp/dml-iteration10-key-windows-before.{log,exit}`.
Binary UTF-8/LF write fixes that model without weakening comparisons; **13 focused cases
pass/exit0**, `/tmp/dml-iteration10-audit-fix-postbyte-focused.{log,exit}`. This is a text-IO
model/fixture regression, not actual Windows OpenSSH or a new production/platform claim.

Fresh root `../dml/build/iteration10-postaudit` has an ownership marker, new protected credentials
and the unchanged reviewed image identity. Its host context symlink reuses the existing audited
installation; the container has **no shared mounts**, not a new image/build/download/global service.
Old stopped fixture was already archived under `iteration10-owned/retained-work-final`, with
`retirement-provenance.json`, then explicitly removed/private keys retired under acceptance.
That retired provenance and all unknown/completed/coordinator B histories remain preserved.

Full actual current progress gate rerun:

```sh
env -u PYTHONPATH build/iteration10-postaudit/context/rootfs/opt/dml/bin/python \
  tests/ssh/progress_integration.py build/iteration10-postaudit \
  /tmp/dml-iteration10-installed-postaudit-final
```

**396 checks/exit0**, `/tmp/dml-iteration10-installed-postaudit-final.{log,exit}`; explicit log
reports genuine asynchronous changed-host-key rejection with parsed/fingerprinted key and
specific diagnostics. Full P/U/F/ownership/typed bytes/offline/wrong-history/safe-loss/profile
workflow reruns, not merely a mocked255. Earlier396 text-write run is separately retained at
`installed-postaudit`; final396 uses deterministic byte write. Existing271 synchronous genuine
changed-key evidence stays distinct, not a rerun/repair claim. Final fresh endpoint is stopped
after writer checks with B/keys/evidence retained pending postfix review/release.

An intermediate standard started before the deterministic-byte refinement passes1360/7C;
`/tmp/dml-iteration10-postaudit-standard.{log,exit}` is explicitly **pre-byte/intermediate**,
not final stable-source evidence. Fresh final stable
`/tmp/dml-iteration10-postaudit-standard-final.{log,exit}` **exit0**: **1361 Python tests**
(186.78s), **seven C**, unchanged Python **2828/2828**, retained native **1681/132/1562** at100%,
zero unsuppressed binding errors/existing624 runtime contexts and **141 CLI Valgrind processes**.
No source changes during this final run. No production/as-built/native/threshold/exclusion/
package change; no commit/push/CI has started.

Black/whitespace/static checks pass; unchanged runtime/wheel/host bytes and244 Markdown targets
remain valid. Revised24-file freeze manifest:
`../dml/build/iteration10-owned/source-freeze-postaudit.json` (also current source-freeze.json and
`iteration10-postaudit/source-freeze.json`). Original accepted hashes are preserved separately
in `source-freeze-initial.json`; comparison confirms exactly the two approved support/test files
changed, other22 unchanged. Focused124-line diff over the exact initially staged blobs:
`/tmp/dml-iteration10-postaudit-proposed.diff`. Index empty, original a94e6f5 ancestor unchanged.

Worker **freezes revised sources/all build use and explicitly releases BOTH build/check and
build/coverage** to coordinator for independent postfix review/validation. Fresh stopped
`dml-iteration10-ssh` under `build/iteration10-postaudit`, unchanged cached image/no mounts,
B/keys/evidence retained for scoped review/release, no32769 listener. Await focused acceptance;
no re-staging/commit/push or further fixture/build operations before ownership is returned.


## Independent review in progress

Coordinator reports a separate offline venv installation from reviewed wheels and custom
actual installed SSH workflow **178 checks/exit0**: captured13+29=42, two matching exact Q/T
jobs plus nonzero23 failure retaining evidence, P/U/F/fresh clients, retained owner after wait
timeout, independent all-typed/every-byte/all-parent remote/packet/A oracles, offline A/inputs,
receiptless F and endpoint-offline reception preserving heads/Q refs, wrong matching-Q rejection
and atomic ref conflict. Endpoint is again stopped after writer checks; B/evidence retained.
All24 frozen source hashes are unchanged. These are **coordinator-reported independent results**,
not worker reruns; REVIEW owns qualification. Separate artifact audit and independent standard
are still pending/in progress. **No acceptance yet**; source/build/fixture freeze remains in force.

## Independent acceptance, postfix review and focused publication

Coordinator independently accepts the bounded slice after fresh standard **1357/7C**, Python
2828/2828, unchanged native1681/132/1562, zero binding/existing624 runtime contexts and141CLI;
separate installed **178 checks**, all **13 wheel/independent-host/fixture-host/remote package
artifact bytes** and244 independent Markdown targets/anchors match. REVIEW owns that evidence,
not a worker rerun. The staged newline finding paused publication before any commit, as above.

Coordinator then independently reviews/accepts the exact124-line two-support-file correction,
passes **168 progress/launch/example/fixture tests** in25.10s, verifies every revised24 hash,
only2 approved support files changed and actual ssh-keygen matching retained public/host-file
fingerprints, final396 dedicated changed-key log and stopped/no-mount/no-listener fixture.
Initial393 malformed-key evidence remains qualified, not retroactively genuine. Coordinator
returns both builds/fresh stopped fixture and explicitly reauthorizes focused publication.

Worker rechecks master/existing origin, baseline `a94e6f5`, empty index and exact24 changed
surface/revised hashes/private-key marker exclusions. Re-stages **only24 reviewed files**,
verifies every staged byte against the accepted revised manifest and no unstaged/untracked
implementation work. Original complete3304-line diff and focused124-line correction were read;
final3393-line combined staged diff is preserved and exact accepted staged bytes verified at
`/tmp/dml-iteration10-final-reviewed-staged.diff`. Staged whitespace passes. No design notes,
ignored fixture/scratch/credentials or unrelated/native/old-spec/workflow changes staged.

Focused commit [`fdba76e9820f6bf03a6902c46d3eed603ea84568`](https://github.com/micha/dml/commit/fdba76e9820f6bf03a6902c46d3eed603ea84568)
(`Observe asynchronous SSH execution through pinned snapshots`), **24 files/+2825/-74**,
and normal `git push origin master` **exit0**. Implementation tree/index clean and exact remote
master matches. Push fast-forwards published29ed39b through the **unchanged separately authorized
local two-file diagram/test maintenance ancestor `a94e6f5`** and this focused implementation.
No amendment/drop of ancestor, force/new-remote/tag/release/package publication/design commit.

### Authorized fixture retirement after archive

Under initial acceptance, original stopped labelled/no-mount/current-image fixture was archived
in `../dml/build/iteration10-owned/retained-work-final` (all B/unknown/completed/coordinator
histories), with `retirement-provenance.json` and `/tmp/dml-iteration10-retired-sshd.log`, then
only its stopped container/private credentials and explicitly named worker wrong-auth private
key artifacts retired. The later approved fresh unchanged-image fixture and its new credentials
are separate provenance, not erased/reused original ownership.

After postfix acceptance, worker rechecks fresh labeliteration10, State.Running=false, exact
unchanged reviewed image, empty mounts/approved host network and archives all `/work` under
`../dml/build/iteration10-postaudit/retained-work-final`, with separate
`retirement-provenance.json` and `/tmp/dml-iteration10-postaudit-retired-sshd.log`. Explicit
fixture remove disposes **only** that stopped owned container/private keys; separately fixed
worker-owned wrong-key filenames in the two post-audit story roots are retired. No owned
container/32769 listener remains. Image/nonsensitive packets/public-key comparison/closure/wheel/
source/native/B evidence remains ignored and retained; no global prune/image/volume deletion,
arbitrary PID/historical-scratch deletion or cleanup-outcome reclassification.

### Exact-SHA automatic CI monitoring

Existing gh2.102.0 and Context7 `/websites/cli_github_manual` confirm exact-commit run/job/log/
watch semantics; no bootstrap/configuration or credential output. Exact-SHA lookup reports
sole automatic **push** [CI run40785659063](https://github.com/micha/dml/actions/runs/40785659063),
matching `fdba76e9820f6bf03a6902c46d3eed603ea84568`, initially queued/in progress. No manual/
release workflow/rerun. Finite900-second `gh run watch --exit-status --interval10` monitors it;
`/tmp/dml-iteration10-ci-watch.{log,exit}`, `ci-initial.json` and `published-runs.json` retain
worker evidence. Final publication acceptance still requires **all six exact-SHA jobs
successful** and clean matching remote. Failures require bounded diagnosis/proposed focused
review/validation, never speculative fixes, weakened gates, hidden uncertainty or later turn.

## Initial exact-SHA CI failure and focused test-only correction

Initial [CI40785659063](https://github.com/micha/dml/actions/runs/40785659063) completes **failure**
for exact published `fdba76e`: **five jobs successful**, Windows one new prepare-harness failure.
Finite watch **exit1**. Completed job JSON and full original/sanitized Windows logs retained:
`/tmp/dml-iteration10-ci-final-first.json`, `windows-first.log`, `windows-first-sanitized.log`
(**369470 bytes**, no lost header) and log exit0. Windows **1354 passed/one failed/five existing
skips/one warning**,155.92s; actual traceback explicitly identifies
`test_ssh_progress_example::test_example_prepare_real_caller_q_prior_history` at
`local._binding_values(interpreter='/opt/dml/bin/python')`, native Windows isabs rejection.
This is a confirmed private host-model mismatch, not a production SSH outcome or permission
to relax local/POSIX path profiles. Old caller-story case explicitly **passes** in this run;
Iteration9's earlier unknown failure cause stays unknown, not called diagnosed by this pass.

Coordinator independently confirms primary traceback and requests only the reviewed Iter9
private binding-adapter pattern. Proposed **one test file**,
`tests/python/test_ssh_progress_example.py`, keeps SSHRemote/declared endpoint POSIX and maps
**only** the in-process example's selected binding interpreter to actual host sys.executable.
Other explicitly supplied interpreter spelling remains unchanged. Two short semantic POSIX/
Windows-spelling regressions capture mapping/preservation and retain production rejection of
Windows spelling as POSIX remote helper. No runtime/example/local/fixture/package/workflow/
profile/skip/threshold/boundary-input change, no new actual Windows SSH/installed evidence claim.

Focused **170 passed/exit0**,24.97s, `/tmp/dml-iteration10-ci-fix-focused.{log,exit}`. Proposed
one-file **+57/-1** diff: `/tmp/dml-iteration10-ci-fix-proposed.diff`. Fresh final stable
`/tmp/dml-iteration10-ci-fix-standard.{log,exit}` **exit0**: **1363 Python tests** (185.95s),
**seven C**, Python **2828/2828**, unchanged retained native **1681/132/1562** at100%, zero
unsuppressed binding errors/existing624 runtime contexts and **141 CLI Valgrind processes**.
No source changes during this run, exclusions/omissions/suppressions/threshold weakening.
Black/whitespace pass; index empty. Other23 revised frozen hashes/runtime/package bytes are
unchanged, so no new installed runtime/fixture rebuild evidence is needed or claimed.

Final CI-fix24-file hash manifest: `../dml/build/iteration10-owned/ci-fix-source-freeze.json`.
Worker **freezes the one-file correction/all sources/build use and explicitly releases BOTH
build/check and build/coverage** to coordinator for independent postfix validation/review.
No fix commit/push before focused acceptance; no speculative old runtime/caller/deadline change,
manual/release workflow, disabled/relaxed Windows test or later feature turn.

## Focused CI-fix acceptance and publication

Coordinator independently reviews the exact **one-test-file/+57/-1** adapter/regressions,
passes **33 progress/fixture/old SSH/caller-example tests**,4.51s, and verifies all24 CI-fix
hashes/only1 changed test/whitespace. No outstanding fix finding. Both builds returned;
focused test-only commit/push/new exact-SHA automatic CI authorized, not additional work.

Worker verifies all24 accepted hashes, existing master/origin, publishedfdba76 base and empty
index; stages only `tests/python/test_ssh_progress_example.py`. Complete staged diff exactly
matches the reviewed proposed patch (`cmp` exit0), `/tmp/dml-iteration10-ci-fix-staged.diff`;
staged whitespace and no unrelated implementation changes pass. Focused commit
[`6f063d94a9bf724b314f89597a78a86ad2824b9e`](https://github.com/micha/dml/commit/6f063d94a9bf724b314f89597a78a86ad2824b9e)
(`Keep SSH progress preparation tests host-native and endpoint POSIX`) and normal push **exit0**,
**one file/+57/-1**. Implementation tree/index clean; exact remote master matches. Runtime/
example/fixture/wheels/old caller/workflows unchanged; no extra installed rebuild claim.
Prior separately authorized `a94e6f5` remains an unchanged ancestor, no published amendment.

Exact new SHA lookup reports sole automatic **push**
[CI40787706542](https://github.com/micha/dml/actions/runs/40787706542), exact6f063d94a9bf724b314f89597a78a86ad2824b9e,
queued/in progress. Finite900-second `gh run watch --exit-status --interval10` monitors;
`/tmp/dml-iteration10-postfix-watch.{log,exit}`, `postfix-runs.json` and
`postfix-ci-initial.json`. No manual rerun/release workflow. Final all-six exact-SHA success,
clean implementation and matching remote remain mandatory; no further speculative source work.

## Unchanged asynchronous-story failure and authorized diagnostic rerun

Second [CI40787706542](https://github.com/micha/dml/actions/runs/40787706542), **attempt1**, completes
**failure** at unchanged exact6f063d9: **five jobs successful**, Windows sole failure in the
**unchanged** `test_asynchronous_example::test_maintained_async_story_host_client_helpers_full_bytes_cli`.
The corrected new prepare case and its two regressions pass. Windows1356 pass/one fail/five
existing skips/one warning,195.05s; finite watch exit1. Full primary traceback identifies trial3
workspace worker.dml: coherent discovery read completes, then pinned `transfer.export_commit`
reopens the same repository and native repo_open reports `storage_error`, code2, opening LMDB.
No selected phase/receipt/worker/child/temp-store artifacts are present to establish why.
**Cause remains UNKNOWN**; not called gate expiry, proven missing directory or a new runtime defect.

Bounded read-only inspection of maintained native repo open/close, vendored LMDB Windows file/
lock setup and unchanged observation/worker/scratch/rename boundaries found no reproducible
specific bug. DML had passed its path/data prechecks before the mdb_env_open error; Windows
code2 can also originate from `OpenMutexA` named-lock setup. That is a **plausible error source,
not diagnosis**; the traceback alone does not prove B was removed. Owned scratch removal
and B-offline rename order were reviewed, not changed. Five fresh Linux repetitions of the
old async story all pass (~1.9–2.1s), `/tmp/dml-iteration10-old-async-repeat-{1..5}.{log,exit}`;
these are qualification, **not Windows reproduction or cause explanation**. No native/local/
transfer/example/test source edit, gate increase or runtime retry was made.

Coordinator explicitly authorizes **exactly ONE failed-job-only rerun at the same exact SHA**
as diagnostic verification before any diagnostic source edit. Worker first preserves attempt1
completed exact-SHA six-job JSON and **771564-byte full all-job logs** at
`/tmp/dml-iteration10-attempt1-preserved.json`, `attempt1-full.{log,err}` (log exit0), in addition
to original failed/sanitized logs/watch/JSON. Then, with clean unchanged HEAD6f063d9:

```sh
gh run rerun 40787706542 --repo micha/dml --failed
```

Request succeeds once. Immediate view briefly returns old attempt1 with queued/no jobs;
a local assertion detects that API transition, not a CI failure or second rerun. Refreshed
view verifies **attempt2**, same exact SHA/eventpush, Windows in progress and five prior
successful results already completed. No second request, new commit, source change, release
or workflow dispatch. Context7 current CLI docs confirm failed-jobs/dependencies scope.

Finite900-second watch monitors attempt2, `/tmp/dml-iteration10-attempt2-watch.{log,exit}`;
`attempt2-initial.json` preserves the transient view and `attempt2-current.json` the confirmed
attempt2 state. This is **authorized diagnostic verification, not a fix/first-run-green claim**.
A repeated failure requires a proposed narrow diagnostic-preservation/rethrow test diff for
review, never speculative native/local fixes or silent runtime retry. Final completion still
requires success/clean matching remote **with explicit prior-failure/unknown-cause qualification**.

## Diagnostic rerun failure and approved test-only evidence enrichment

Authorized same-SHA attempt2 also completes **failure**, finite watchexit1, five successful
results/Windows sole **different unchanged case**:
`test_caller_request_example::test_caller_story_host_helpers_full_typed_bytes_cli`.
Primary trace shows all requested P/U/F observations returned, then
`assert launch.wait(timeout=15) == 0` fails at unchanged caller_requests.py:216. Actual returned
code/owned worker stderr/stdout/B outcome are absent from that trace; **outer-worker failure
reason remains UNKNOWN**, not the earlier publication-miss or a gate-expiry diagnosis.
The old async ENOENT and fixed prepare cases **pass** on attempt2. Windows1356 passed/one failed/
five existing skips/one warning,140.53s. `attempt2-final.json`, full failed/sanitized step logs
(**290657 bytes**) and watch/log exits are retained. Exactly one rerun was requested; no further
rerun/code/retry/gate increase was used to hide this result. No final green claim.

Coordinator approves narrowly bounded **TEST-ONLY diagnostic enrichment**, not a runtime/local/
native/example fix. Proposed three files: new `tests/python/story_diagnostics.py`, focused
`test_story_diagnostics.py`, and a two-line shared harness integration in
`test_asynchronous_example.py`. The caller-Q harness already reuses that same old-story
function, so **both** cases gain diagnostics without changing caller tests/examples/runtime.

The shared wrapper invokes the story **once** and, only on an unexpected error, attaches one
bounded escaped JSON note then **bare-raises the ORIGINAL exception** (same object/type/args/
primary traceback). Context7 `/python/cpython` confirms add_note/bare-raise semantics. Evidence:
selected phase/receipt where available, synthetic relative workspace, fixed file existence,
actual owner poll/returncode and512-byte tails/size/truncation of owned worker stdout/stderr.
Public typed final outcome/cleanup reads happen only with known-reaped owner and a small
owned story profile; unreadable/native errors are recorded, not retried/masked. Live/unknown
owner skips the store read. No arbitrary serialized scratch/resource traversal, environment/
physical MDB/record-byte dump, dispatch/import/ref repair, process signaling/wait, timeout or
gate policy change. Note cap8192 bytes; overflow shrinks already-owned text, never reopens B
or polls/reads twice to conceal the first error. Diagnostics are synthetic test-only data,
not a general observer/framework or packaged runtime component.

Nine focused regressions check both source contexts/selected receipt, real typed B result/
cleanup, no mutation/executor/import spies, live-owner skip, native-read error preserving the
primary, original exception identity/message, owned-path restrictions, large synthetic log
bounding/control escaping and single invocation/no diagnostic on success. Together with both
old harnesses **17 tests pass**,4.57s, `/tmp/dml-iteration10-diagnostics-focused-final.{log,exit}`.
Proposed diff `/tmp/dml-iteration10-diagnostics-proposed.diff`; all prior24 reviewed/runtime/
example hashes are unchanged. First full standard **1372 tests passed**,188.51s, but **exit1**
at the source-coverage gate: synthetic compile co_filenames (`asynchronous_execution.py`,
`caller_requests.py`, `exchange.py`) were relative and became phantom root source entries,
causing coverage's `No source for code` error. `/tmp/dml-iteration10-diagnostics-standard.{log,exit}`
is **not a passing full gate**; subsequent memory/native coverage stages did not complete.
No freeze/build release occurred at that failed checkpoint.

Coordinator's read-only review confirms the synthetic regression harness defect. Corrected
**only** synthetic compile filenames to absolute owned pytest temporary paths **outside** the
checkout source profile, retaining basename recognition. Generated bytecode is not mapped to
real maintained example sources, and no production coverage/source omission/omit-pattern/
threshold change is made. Postpath focused **17 pass/exit0**,4.48s,
`/tmp/dml-iteration10-diagnostics-focused-postpath.{log,exit}`. Fresh stable standard now runs
at `diagnostics-standard-postpath.{log,exit}` and **passes exit0**: **1372 Python tests**,
188.33s, **seven C**, unchanged Python **2828/2828**, retained native **1681/132/1562** at100%,
zero unsuppressed binding errors/existing624 runtime contexts and **141 CLI Valgrind processes**.
No source changes during this final run. Existing coverage profile/omits/thresholds and memory
suppressions remain unchanged; helpers/regressions are test-only, not added production coverage.
Black/whitespace pass, index empty; every prior24 reviewed source/runtime/example hash remains
unchanged. No wheel/runtime/fixture rebuild or additional installed claim is needed.

Corrected proposed three-file diff `/tmp/dml-iteration10-diagnostics-proposed.diff` and final
**27-file aggregate** source manifest `../dml/build/iteration10-owned/diagnostics-source-freeze.json`
are frozen. Intermediate prepath hashes are separately retained as diagnostic harness evidence,
not an accepted source-freeze checkpoint. Worker **freezes all sources/build use and explicitly
releases BOTH build/check and build/coverage** for independent diagnostic postfix review/validation.
No diagnostic stage/commit/push before focused acceptance; no further rerun or speculative
runtime/native/example work. This may expose the real failure if repeated; **it does not claim
a fix or established cause**.

## Diagnostic acceptance and focused publication

Coordinator reviews the approved three-test-file scope, original rethrow/bounded fixed-owned
reads/no retry-dispatch-repair-signal and synthetic absolute temporary-path correction.
Independent **44 diagnostic/old async/caller/progress/fixture tests pass**,5.45s; all27 aggregate
hashes stable/prior24 unchanged/whitespace pass. Both builds returned and focused diagnostic
commit/push/new exact-SHA automatic CI explicitly authorized. This is **evidence enrichment,
not an established fix or diagnosis of either old Windows failure**; no further same-SHA
reruns/production/native expansion/skip/gate extension implied.

Worker reads the full proposed helper/regression/shared-harness diff, verifies all27 accepted
hashes/exact clean6f063d9 baseline/master/existing origin/empty index and absence of private-key
markers, and stages **only the three reviewed test files**. Every staged byte matches its
accepted hash; staged whitespace passes. `/tmp/dml-iteration10-diagnostics-staged.diff` retains
the inspected staging. Focused commit
[`099d156fb49f81a7da0683898189a85c1172988c`](https://github.com/micha/dml/commit/099d156fb49f81a7da0683898189a85c1172988c)
(`Preserve bounded evidence for unexpected old-story test failures`), **three files/+511/-1**,
and normal push **exit0**. Implementation tree/index clean; exact remote master matches.
Initial24 runtime/docs/support, previous one-test correction, actual fixture evidence/wheels/
examples/local/native/workflow/profiles remain unchanged. Prior a94e6f5 remains unchanged ancestor.

Exact099d156 lookup reports sole automatic **push**
[CI40791372333](https://github.com/micha/dml/actions/runs/40791372333), queued/in progress;
finite900-second `gh run watch --exit-status --interval10`,
`/tmp/dml-iteration10-diagnostics-watch.{log,exit}`, `diagnostics-runs.json` and
`diagnostics-ci-initial.json`. No manual rerun/release. If failure recurs, new primary diagnostic
must be inspected before proposing a bounded fix. Final completion still requires all-six
exact-SHA success/clean remote and explicit preservation of earlier failures/unknown causes.

## Final exact-SHA success and stop

[Final automatic CI40791372333](https://github.com/micha/dml/actions/runs/40791372333) completes
**SUCCESS for exact `099d156fb49f81a7da0683898189a85c1172988c`**, all **six jobs successful**.
Worker and coordinator direct finite watches exit0, not timeout; completed exact-SHA job JSON,
full logs and sole automatic push run list are verified. This final diagnostic-commit workflow
passes on its first attempt, **not a first-run-green claim for the turn**. Prior failed commits/
attempts are preserved, not replaced by this final success.

Final verification commands (already completed before stop):

```sh
gh run view 40791372333 --repo micha/dml \
  --json attempt,headSha,status,conclusion,event,jobs,url
gh run view 40791372333 --repo micha/dml --log
gh run list --repo micha/dml \
  --commit 099d156fb49f81a7da0683898189a85c1172988c \
  --json databaseId,headSha,status,conclusion,event,workflowName,url,attempt
# Finite watch used throughout; exit0:
timeout 900 gh run watch 40791372333 --repo micha/dml \
  --exit-status --interval 10
git status --short
git rev-parse HEAD
git ls-remote origin refs/heads/master
```

| Final job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Strict Linux](https://github.com/micha/dml/actions/runs/40791372333/job/123177134472) | Success | 7 | 1372 passed,1 warning;151.38s;Python2828/2828 |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40791372333/job/123177134577) | Success | 7 | 1372 passed,1 warning;116.46s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40791372333/job/123177134628) | Success | 7 | 1368 passed,4 existing skips,1 warning;324.76s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40791372333/job/123177134641) | Success | 7 | 1368 passed,4 existing skips,1 warning;156.92s |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40791372333/job/123177134700) | Success | 7 | 1372 passed,1 warning;124.61s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40791372333/job/123177134826) | Success | 7 | 1366 passed,5 existing skips,1 warning;196.12s |

Existing skips concern platform device/Unix pipe availability; Windows additionally omits the
existing POSIX literal-backslash credential-path parameter under native separator semantics.
No meaningful failed case was skipped, threshold/input relaxed or production profile weakened.
Strict CI uses informational **`-c`**, not worker/coordinator local standard/memory **`-v`** or
mandatory actual installed SSH gates. Host statements are not every Python branch or actual
installed helper/child/process-memory instrumentation. Final full worker postpath `-v` passes
1372/seven C,2828/2828, retained native1681/132/1562, zero binding/existing624 runtime contexts
and141CLI, as recorded above. No new exclusions/source omissions/memory suppressions.

Actual final Windows verbose log explicitly **passes both old async/caller stories and the
fixed progress prepare case/regressions**. This verifies final CI behavior, **not why the old
failures occurred or a demonstrated fix of them**. Preserve these distinct qualifications:

- Original393 progress gate's malformed changed-host file is not genuine changed-key evidence.
  Reviewed support newline/parser/fingerprint correction and final396 actual dedicated changed-key
  diagnostics establish the corrected evidence; existing synchronous271 stays distinct.
- Initialfdba76 Windows failure is a **confirmed new private prepare-harness host/POSIX mismatch**,
  fixed only by the reviewed one-test adapter/regressions. Runtime/local/SSH profiles were unchanged.
- Exact6f063d9 attempt1 old async discovery-to-export native open/code2 failure remains **UNKNOWN**.
  Windows OpenMutexA is only a plausible error source, not diagnosis; five Linux passes are not
  Windows reproduction. Attempt1 full JSON/all-job logs were preserved before the authorized rerun.
- Exactly one authorized same-SHA failed-job diagnostic rerun (attempt2) failed a **different old
  caller outer-worker status assertion after P/U/F**. Its returncode/worker logs were absent then;
  reason remains **UNKNOWN**, not a publication-miss/gate-expiry explanation. No further rerun used.
- Reviewed test-only diagnostics preserve/rethrow the original error and bounded owned evidence
  if it recurs. They do not modify runtime/example/gates, retry or claim to fix either old cause.
  Their synthetic phantom-source coverage failure was corrected in the test harness only; the
  failed intermediate gate stays recorded rather than being called final stable validation.

Final evidence: `/tmp/dml-iteration10-final-ci.json`, full **762353-byte** `final-ci.{log,err}`
(log exit0), bounded `final-ci-summary.log`, `final-runs.json` and `diagnostics-watch.{log,exit}`.
Earlier fdba76/6f063d9 attempt1/attempt2 full failed/sanitized logs, completed JSON, finite watches,
source-freeze manifests/proposed/staged diffs, actual fixture/independent probes and retired B
archives remain separate evidence. Coordinator independently confirms final direct watch0/full
logs/all-six exact SHA/sole automatic push/clean matching remote and directs RESULTS-only
finalization followed by complete stop.

Final implementation **tree/index clean**, remote master exact099d156, all27 accepted aggregate
source hashes unchanged. Publication is reviewed24-file **fdba76e**, reviewed one-test **6f063d9**,
then reviewed three-test diagnostic **099d156**, preserving unchanged user-authorized diagram/test
ancestor **a94e6f5**. Unique turn surface27 files; production/runtime/example/fixture profiles
have not changed since the initial accepted implementation/support correction. No native/old-spec/
workflow/version change, new remote/force push/tag/release/package publication/design commit.

Owned original and fresh local fixtures/private keys are explicitly retired only after stopped
writer proof and B/unknown/completed/coordinator/provenance archive. Image/nonsensitive public
comparison/packets/source/native/closure/wheel/B evidence remain ignored and retained; no listener,
unowned writer disposal/global prune/unrelated resource or historical scratch deletion. Retirement
is separate from recorded computational cleanup. Loopback-only host networking/no shared mounts
remain **not network-namespace/second-host isolation**. Existing exact exclusions/runtime finalizer
limits, unavailable Python mutation tools/eleven selected negative probes, real versus substituted
failure paths, all-typed/new-A-put rollback, profile/full-history/trust/capture/security/portable
remote-lifetime/process-tree/power-loss/RSS/disk/deadline qualifications remain explicit.

**RESULTS is finalized. COMPLETE AND STOPPED.** No further source edits, builds/tests, staging,
commit/push, CI polling/reruns, fixture operation, design commit/push, extra worker, global change,
release/package publication or later turn. Coordinator owns final REVIEW/COORDINATION/design
reconciliation. Final success is qualified evidence, not erasure or diagnosis of prior failures.





