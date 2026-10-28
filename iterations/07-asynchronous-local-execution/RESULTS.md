# Iteration 7 implementation results

Status: bounded implementation, independent review, focused publication and final
exact-SHA CI verification are **complete**. Published as **`a8d6463`**; all six CI jobs
pass on the **first run**. Work is **stopped**. Coordinator owns COORDINATION,
REVIEW and design-status reconciliation; worker owns this report/runtime/tests/as-built docs.
The current user GO supersedes historical planning-only statements in the approved
[handoff](HANDOFF.md), [design](DESIGN.md) and [example](EXAMPLE.md), not their stop line.

## Authority, preflight and fresh baseline

Worker is existing pane **`%215`**, verified through `TMUX_PANE` (unqualified tmux display
returned active coordinator `%197`, not worker identity). `/work` is mounted. Required
machine/design/implementation guidance/contracts and Iteration 6 evidence were read fully.
Implementation initially clean at **`a0aa05d56b9e70277a98bb03e26514ab6b6f1415`**; design
baseline **`93ef0ce`**, coordinator's new untracked COORDINATION preserved. Exclusive worker
ownership of **both `build/check` and `build/coverage`** until explicit freeze/release.

Fresh standard baseline finished **before measured source edits**:

```sh
# from ../dml
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration7-baseline.{log,exit}`, exit **0**: **609 Python**, **seven C executables**;
Python **1639/1639 statements**; retained native **1681/1681 lines**, **132/132 functions**,
**1562/1562 branch outcomes**. Existing binding Valgrind zero unsuppressed errors (624
existing runtime suppressed contexts); **141 native CLI Valgrind processes** pass. Baseline
and progress reported by targeted tmux messages to `%197`; no extra agent/session launched.

## Selected/refined choices

- Additive explicitly imported exchange helpers, public native/local/transfer composition
  only; fixed installed `daggerml.exchange_worker` invokes public execute exactly once.
  No private local/transfer decoder, callback, runner redesign or native expansion in
  production. Exchange refactors its **own** initial/publication inspector and shares it
  with unchanged completed-return checks. Synchronous callers/tests remain enabled.
- Frozen serializable `ExchangeHandle(workspace, expected)` is saved observation identity,
  no PID/command/process/A-path/recovery authority. Explicit bounded exclusive handle
  save/load helpers; loading never dispatches or follows the workspace.
- Separate nonserializable `WorkerLaunch` retains actual subprocess/log resources;
  application-owned `wait` establishes direct-worker disposition and closes streams.
  Timeout retains ownership. No hidden registry/finalizer/context-manager wait, detached
  lifetime service, cancellation/restart or sole-owner-exit guarantee. Hard owner loss
  can orphan processes; surviving observation never authorizes replacement execution.
- Retained exclusive `launched` precedes fixed spawn, separate from execute's `started`.
  Existing artifacts/mismatched job reject before process invocation. Command/logs/live
  wrapper prepared before spawn; no postspawn receipt IO/allocation required for response.
  Catchable setup/spawn errors close acquired streams and retain marker/artifacts. Actual
  spawn/ack-loss evidence keeps the known owner rather than dropping a running `Popen`.
- Additive bounded `worker-ready.json` after B import/selection/handle closure and before
  public dispatch. Receipt-write failure prevents computation and preserves B/one-shot.
  Missing readiness is bootstrap/unknown; malformed ready or ready-but-invalid B/ref is
  an error, not hidden initialization. Existing synchronous receipt/output remain.
- One coherent B read transaction derives the exact fresh Q/T by differences from C and
  reads the associated publication ref. Prior Q/T/publication in C remains preserved.
  Close source, export **pinned immutable** P/U/F, validate through public import/roles in
  private disposable storage, close/clean scratch, then publish fresh observer-owned
  packet descriptor last. No packet overwrite or B mutation during observe.
- Selected lifecycle is derived from history: P/U `working`, F `done` only after recorded
  computation/separate cleanup and successful complete history retrieval/validation.
  U publication is provisional; F failure may retain it as evidence. Missing final
  outcome remains unknown regardless of process exit, elapsed time or marker/log text.
- Exact labels/fields are owned by the new [as-built contract](../../../dml/docs/spec-next/asynchronous-execution.md).
  `ExchangeObservation.snapshot` owns `ReceivedObservation`; only F has optional nested
  `completion: ReceivedRun`. Observer/nested completion refs are `None`, receive supplies
  caller ref; `ReceivedRun.ref` annotation is therefore `Optional[str]`. Bundle row count
  is not new object/attempt count. No runnable LocalContext is manufactured for A.
- Independent caller expected validation and isolated history checks precede actual A
  import. Existing atomic create-or-same-target refs; P-to-F under an existing different
  target conflicts. A heads/earlier refs/bytes stay unchanged. Larger-map whole receive
  is transfer retry, never another execution. Historical source/URI/path data is inert.
- Example initially had two-second phase windows. Coordinator feedback prompted **finite
  cooperative caller-owned gates recorded as a named input** instead. Normal trusted
  example source waits around publication; application releases both gates on errors
  before waiting/reaping. No installed runtime/fault hook or timing/lifetime guarantee.
  Two matching fresh jobs retain identical pinned selection; gate files reused only after
  previous worker reaping. A third nonzero-after-publication job records failure evidence.

Loaded Context7 skill and consulted **`/python/cpython`** for subprocess ownership/wait/
poll, strict JSON hooks and exclusive/temp/replace files. Selected Python >=3.8-compatible
production operations; no 3.12 `delete_on_close` or newer process API. No secrets exposed,
global tooling/bootstrap, native/CLI grammar, old spec, adapter/runtime/version/workflow,
cloud/release/package-publication or later-feature change.

## Host checkpoints and assurance

- Additive refactor synchronous regression: **137 passed**, exit 0;
  `/tmp/dml-iteration7-sync.log`.
- First progress suite: **98 passed / 2 failed**; test-only equality forgot nested
  `ReceivedRun.ref` differs between observer `None` and receiver explicit ref. Corrected
  test normalization (not production classification); `/tmp/dml-iteration7-progress1.log`.
- Real launch/progress/process checkpoint: **137 passed**, exit 0;
  `/tmp/dml-iteration7-focused1.log`.
- Expanded focused host coverage: **357 passed**; exchange **549/549**, installed worker
  **9/9**, original async example **122/122**, original delay child **19/19**. One runpy
  already-imported-module warning corrected by private module-cache setup; no runtime
  suppression/exclusion. `/tmp/dml-iteration7-coverage2.log`.
- After gate refinement/true >4 MiB overflow, **80 focused tests passed**;
  `/tmp/dml-iteration7-focused2.log`. `python -m black` was absent inside tools shell;
  used existing `/run/current-system/sw/bin/black`, no install/bootstrap. Final Black
  checks pass. No source file omitted or threshold reduced.
- First full default `-v`: **826 Python**, **seven C**, Python **2013/2013**;
  `/tmp/dml-iteration7-default1.{log,exit}`, exit **0**. One tmux progress message
  mistakenly said 2004/2004; actual log/final evidence is **2013/2013**, corrected here.
- Coordinator requested explicit concurrent observers, valid same-selection different
  token packet swaps and new receiver cleanup-failure tests. Added those, not production
  changes. Final fresh default `-v` exits **0**:
  `/tmp/dml-iteration7-default2.{log,exit}`: **831 Python tests** (105.88 seconds),
  **seven C executables**, Python **2013/2013 statements**, exchange **549/549**, worker
  **9/9**, maintained async application **131/131**, child **29/29**. Native retained
  populations remain **1681/1681 lines, 132/132 functions, 1562/1562 outcomes**.

Final binding Valgrind has **zero unsuppressed errors/leaks**, retained exit heap
**500823 bytes / 8717 blocks**: existing runtime patterns suppress **476387 bytes / 8657
blocks** (624 contexts), reachable **24436 bytes / 60 blocks**. **141 native CLI Valgrind
processes** pass. No new exclusion/suppression/weaker gate. Existing exact exclusions and
unsupported foreign-last-owner abandonment remain qualified; host-helper statement
coverage is not every Python branch or coverage of installed/staged worker/child processes.
No new installed-process memory or runtime-only/full pair was run.

### Meaningful selected-history/process/file/storage evidence

- Independent public breadth-first typed population/every-packed-byte oracles compare
  B, packet and A, not transfer's private traversal or CLI prefixes. All-parent C/P/U/F
  history and original selection/base/sentinel bytes persist; existing A main can move
  independently. P/U have no final completion; same Q/T persists across poll/import.
- Real previous final C with prior Q/T/publication is the next job's base; exact fresh
  name differences select only new Q2/T2. Prior entries are preserved, never mistaken
  for the current occurrence or rewritten.
- Real coherent-read race: separate process moves **both** head/publication refs after
  observer's first ref read. The second read sees original snapshot P; handles close,
  pinned export still retrieves P after head has advanced to F. Later observer sees F.
- Two actual concurrent read-only observers hold genuine B read transactions at a finite
  private shared barrier, then independently export/validate into distinct fresh packet
  directories. Identical selected bytes/receipts, unchanged B, explicit separate A refs.
- Real computational child held at finite cooperative private initial and postpublication
  barriers: start returns with live owner; fresh short-lived clients exit/reobserve;
  P/U remain working and same Q/T. Release child, worker waits/reaps, F done; zero and
  nonzero-after-U yield correct success or failure evidence/separate cleanup.
- Retained launch marker before actual spawn (private pre-spawn barrier), actual spawn
  followed by application response loss with retained known owner, setup/log/spawn/owner
  allocation substitutions. No repeated start dispatch; no auto-repair or marker clearing.
- Actual worker-loss barriers only **before child spawn** (P) or **after actual child
  reaping** before final storage (U), or after final commit/reaping before original receipt
  (F). P/U stays unknown/working, F retrieved without receipt; none is retried/finalized.
  Owners use finite waits and reap direct processes. Failed watchdog/barrier fallback is
  not passed arbitrary-kill, descendant cleanup, power-loss or portable scheduling proof.
- Strict bounded handle/readiness/packet JSON (duplicate/nonstandard/deep/oversize/types),
  missing/partial packets, exact IDs/phase/root/token association; typed-valid wrong P/U
  selection/roles/root/request/attempt/base/history and all existing F completion negative
  oracles. Actual valid same-selection different-job P/U/F receipt+bundle swaps (not fake
  zero tokens) reject before A writes. Full data-file equality is the rejection oracle.
- Ready malformed/mismatched/missing B, arbitrary head/attempt-ref targets error, not
  bootstrap/fake failure. Readiness IO failure leaves imported C and retained marker
  before any dispatch. Packet/export/descriptor errors retain B/partial owned artifacts;
  no filesystem rollback is claimed. New receiver validation-scratch cleanup denial
  explicitly prohibits actual A import/puts and preserves whole A; cleanup only test-owned
  allocated scratch after helper handles close.
- Genuinely new **actual-A successful puts with exact transaction readback** precede
  different/raw malformed refs and substituted native consuming-commit failure for each
  P/U/F. Validation-store puts/preexisting rows excluded. Fresh independent readers
  verify every old/new typed byte and absent entire batch; whole A data-file equality
  additionally preserves raw malformed/different ref bytes. Existing heads unchanged.
- Actual late **1 MiB map / 2 MiB new publication result** fails after successful-new-A
  puts; fresh full-state reader proves rollback, explicit **8 MiB whole receive** succeeds
  without another computation. Consuming-commit fixture is dependency EIO substitution
  consuming real LMDB handle, not a physical device/disk failure.
- Actual receiver loss after three genuinely new puts/readback **before A commit** versus
  after **successful actual commit before response**, for P/U/F: fresh independent readers
  distinguish no batch from complete publication. Explicit repeat receives are safe and
  nonexecuting. No packet/source head is implicitly adopted.
- Scaled packed-total observation rejection (MAX_PACKED_BYTES=1) is explicitly **not a
  production-limit stress claim**. Separate child records a valid **4 MiB + 1 byte datum**
  whose packed record exceeds unchanged real **MAX_RECORD_BYTES=4 MiB**. Runner actually
  waits/reaps, cleans, commits successful F. Both ordinary execute output and subsequent
  observation export fail the real per-record limit, B stays byte-identical done/success,
  no complete packet/false done response/receipt/retry. Existing synchronous regression
  independently retains failure/false-success/cleanup and postcompletion overflow checks.
- Hypothesis covers generated names/selection pins, progress phases/identity/repeated
  reception and typed-valid extra P/U/history rejection. Private few deterministic process
  fixtures are not random kill stress. Final collection **831** cases; new **222** cases
  maximum full ID **137**, short case ID **99**. Whole existing suite maximum full ID
  **11821**/short **11784** comes from unchanged preexisting CLI JSON buffer inputs, not
  new oversized descriptors/source; all actual 8193-byte/4 MiB+ inputs retained.

## Python mutation gap and selected probes

Fresh tools-shell inspection finds no `mutmut`/`cosmic_ray` command or module; no bootstrap.
Mull is not Python mutation assurance. Private ignored in-memory
`../dml/build/iteration7-oracles/probe.py`, `/tmp/dml-iteration7-oracles.{log,exit}`,
aggregate exit **0**: **six selected probes**, each pytest exit **1 / one intended failure**,
not setup/collection failures:

1. Premature `done` for P: working snapshot oracle fails.
2. Ignore initial attempt association: typed-valid wrong request packet wrongly accepted.
3. Retarget export to newer head: immutable pin oracle fails after actual coherent-read race.
4. Publish A before validation: whole-file oracle catches premature writes despite error.
5. Overwrite retained launch marker: preexisting-marker test catches process invocation.
6. Move A main after receive: independently advanced head-preservation oracle fails.

No maintained source changed for probes. This is selected negative-oracle scope, not a
mutation-framework score, broad branch/installed mutation assurance or equivalent-mutant
claim.

## Offline installed evidence and provenance

Used only existing local packaging environment/toolchain, no bootstrap/global install:

```sh
# inside existing nix develop ../dml-build-tools shell, from implementation
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration7-packaging/dist .
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration7-packaging/dist python/daggerml-cli
build/iteration2-packaging/bin/python -m venv --without-pip \
  build/iteration7-packaging/installed
build/iteration2-packaging/bin/python -m pip \
  --python build/iteration7-packaging/installed/bin/python install \
  --no-index --no-deps build/iteration7-packaging/dist/*.whl
# from /tmp, source PYTHONPATH unset
env -u PYTHONPATH /work/repos/micha/dml/build/iteration7-packaging/installed/bin/python \
  /work/repos/micha/dml/build/iteration7-packaging/installed_probe.py
```

Build/install exit **0**, `/tmp/dml-iteration7-installed-build.{log,exit}`. Private installed
probe initially failed its own independent-expected serializer (stringified asdict's nested
ObjectId dictionary rather than actual ID) before A import; fixed **private harness only**.
Final installed workflow exits **0**, **248 parent check calls**, plus nine fresh observers,
nine fresh receivers and nine fresh public typed readers and real child provenance assertions;
`/tmp/dml-iteration7-installed-probe.{log,exit}`. Evidence retained under
`/tmp/nix-shell.VmT50D/dml-iteration7-installed-story-ct4rz4z3`.

- All package/core/exchange/local/transfer/fixed worker/console/native paths in isolated
  install, source PYTHONPATH absent, clients/workers launched from `/tmp`.
- Real cooperative P/U/F, same Q/T across fresh client exits, separate finite owner reaps
  each fixed worker, two matching selections/equal result 11/distinct occurrences, nonzero
  after U yields failure evidence/cleanup. Actual child asserts installed module/core/runtime
  paths; its persisted stdout confirms provenance. No unowned running object discarded.
- A renamed offline during execution; B renamed offline and copied packet-only receive
  using caller expected file separate from packets; fresh public reader exact complete
  BFS closure/bytes including composite-only datum. Inert historical scratch sentinel
  stays untouched; main independently moved, sentinel/base bytes and absent B refs verified.
- Existing installed console log agrees with selected IDs and every ordered parent;
  same-ref reimport, no repeat start and valid same-selection token swap rejection before
  whole-file unchanged A. No source execution/historical-path action in observe/receive.
- Byte-identically copied maintained example/child outside checkout executes successfully
  from `/tmp` with PYTHONPATH unset; `/tmp/dml-iteration7-installed-example.{log,exit}`,
  exit **0**, retained `/tmp/dml-iteration7-installed-example/story`.

Current wheels:

- `../dml/build/iteration7-packaging/dist/daggerml-0.1.0-cp313-abi3-linux_x86_64.whl`,
  SHA256 **`b83e39fa20bc4ae2c1c6afd742f15f8e4b679f6cfe99fca95effdf662a0008d6`**.
- `../dml/build/iteration7-packaging/dist/daggerml_cli-0.1.0-py3-none-any.whl`,
  SHA256 **`f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`**.

All **five** wheel Python modules match current maintained bytes; no tests/fault controls
packaged. Root dirty-source wheel, not VCS sdist/release evidence. Local CPython **3.13.15 /
Linux x86_64**, `cp313-abi3` not earlier declared runtimes/other platforms/manylinux proof;
Python/core/console runtime declarations and wheel tags unchanged. Installed subprocess
functional/provenance evidence is not coverage-instrumented process/memory/security proof.

Coordinator separately reports **208 independent installed checks**, exit **0** in its own
pip-less review environment, no shared builds: full public typed bytes/composite-only child,
prior Q/T/publication C, P/U/F fresh clients/offline A/B, F without receipt, failure evidence,
repeat refs/unchanged main/sentinel/absent B refs, typed wrong phase whole-file rejection and
console. `/tmp/dml-iteration7-coordinator-probe.{py,log,exit}` is coordinator-owned evidence,
not worker rerun or final acceptance; REVIEW owns independent qualification.

## Changed slice and review gate

Implementation changes (relative to `../dml`):

- `python/daggerml/daggerml/exchange.py`, new `exchange_worker.py`, Meson install inventory.
- New `examples/asynchronous_execution.py`, `examples/local_slow_add.py`.
- New `tests/python/test_exchange_{launch,progress,progress_faults,progress_process}.py`,
  `test_asynchronous_example.py`, private `progress_interruption_parent.py`.
- Existing exchange runtime fixture stages the installed worker; existing synchronous
  completion-IO fixture targets completion rather than failing new readiness publication.
- New owning `docs/spec-next/asynchronous-execution.md`; navigation/reference updates in
  `docs/spec-next/{README,python-api,repository-execution}.md`, `README.md`,
  `docs/{architecture,packaging-and-distribution}.md`, `python/daggerml/README.md`;
  assurance catalog update with **no new coverage exclusion**.

**22 implementation files**; native production/local/transfer/old spec/CLI grammar/JSON,
adapters/runtime/version/workflows unchanged. Index empty; build/probe/install scratch
ignored and test-owned. Coordinator design work preserved; no design commit/push requested.
Worker validation/link/whitespace/source-freeze checkpoint follows below. Commit/push/CI
remain gated on **explicit independent acceptance**. No extra agent, detached/recovery
service, cloud/global tooling, release/tag/package publication, resource/native expansion
or later feature turn.

### Explicit review freeze and build release

Worker final Black check passes **12 Python files**; Markdown validation passes **10
changed documents / 176 local targets and anchors**. `git diff --check` passes in both
checkouts; implementation index empty. Five current wheel Python modules equal maintained
source bytes. Existing unrelated coordinator design edits remain untouched.

After final default `-v`, installed workflow, negative probes and these static checks,
worker **freezes runtime/test/as-built source and all shared build use**, explicitly
**releases both `build/check` and `build/coverage` to coordinator** for independent default
validation/review. Awaiting findings/acceptance; no staging/commit/push/CI launch. No
implementation/build restart without returning ownership through coordinator. Report-only
updates may preserve subsequent review evidence without changing the frozen source.

## Independent acceptance and focused publication

Coordinator explicitly accepts the reviewed bounded **22-file** slice with no outstanding
finding. Independent fresh default `-v` exits **0**, **831 Python / seven C**, Python
**2013/2013** (exchange549/worker9/application131/child29), native retained
**1681 lines / 132 functions / 1562 outcomes**, zero unsuppressed binding errors/unchanged
runtime heaps/624 suppressed contexts and **141 CLI memory processes**. Separate installed
**208 checks**, five wheel-module byte comparisons, **17 changed Markdown documents /
379 local targets/anchors** and whitespace pass. This is coordinator-reported independent
evidence owned by [REVIEW.md](REVIEW.md), not a worker rerun. Both shared builds explicitly
returned to worker; focused commit/push/exact-SHA CI authorized only after acceptance.

Worker verified existing `master` / `origin` (`https://github.com/micha/dml.git`), staged
**only 22 reviewed implementation files**, read complete **2943-line** staged diff,
checked staged whitespace and no unstaged/unrelated implementation files. Slice:
**2594 insertions / 29 deletions**; `/tmp/dml-iteration7-reviewed-staged.diff`.
No design notes or ignored build/probe scratch staged. Focused commit
[`a8d646379a52878d087d28bc216b7baa4f9ef3db`](https://github.com/micha/dml/commit/a8d646379a52878d087d28bc216b7baa4f9ef3db)
(`Observe asynchronous local execution through pinned snapshots`) and normal
`git push origin master` exit **0**. Implementation tree/index clean, exact remote master
matches. No force push/new remote/tag/release/package publication/design commit.

Consulted Context7 **`/websites/cli_github_manual`** for exact-commit run filters, view/jobs/
logs and finite watch exit semantics. Existing `gh` **2.102.0**, no bootstrap/configuration
or secret output. Initial exact-SHA run listing was empty during normal push-trigger delay;
subsequent listing shows sole automatic **push**
[CI run 40602956772](https://github.com/micha/dml/actions/runs/40602956772), exact head SHA
matches commit, all six jobs initially **in progress**. No manual workflow trigger.
Targeted `%197` message supplies full SHA/remote/run ID/current status.

Finite `timeout 900 gh run watch 40602956772 --exit-status --interval 10` monitors the
existing run; `/tmp/dml-iteration7-ci-watch.{log,exit}`. Final delivery remains gated on
**all six exact-SHA jobs successful**. Any bounded CI defect needs diagnosis/regression,
focused coordinator review and appropriate validation before a subsequent push; no
speculative runtime/test edits or later turn. Final CI evidence below supersedes this
in-progress checkpoint, not its scope/stop line.

## Final exact-SHA CI verification and stop

Automatic [CI run 40602956772](https://github.com/micha/dml/actions/runs/40602956772)
completes **success** for exact published SHA
**`a8d646379a52878d087d28bc216b7baa4f9ef3db`**. All **six jobs** pass on the **first run**;
no failure, fix, rerun or subsequent implementation commit/push was needed. Finite
`gh run watch --exit-status` exits **0**, not timeout. Worker fetched complete final
run/job JSON, full logs and exact-commit workflow list; sole automatic **push** CI run,
head SHA and six completed successful jobs verified. Implementation tree/index clean,
remote master exact match. Coordinator independently confirms the same final evidence;
[REVIEW.md](REVIEW.md) owns final independent qualification/acceptance.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40602956772/job/122535365752) | Success | 7 | 831 passed; 63.20 s |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40602956772/job/122535365652) | Success | 7 | 831 passed; 53.08 s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40602956772/job/122535365492) | Success | 7 | 827 passed, 4 existing skips; 224.83 s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40602956772/job/122535366525) | Success | 7 | 827 passed, 4 existing skips; 88.19 s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40602956772/job/122535365829) | Success | 7 | 826 passed, 5 existing skips; 119.30 s |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40602956772/job/122535365773) | Success | 7 | 831 passed; 76.20 s; Python 2013/2013 |

Existing skips concern missing `/dev/full` on macOS/Windows and the Windows Unix
closed-pipe fixture. No new skipped test, coverage exclusion/suppression, weaker gate,
reduced boundary input or workflow change. Windows reports UCRT64 Python **3.14.9**;
Unix uses the existing workflow's Python **3.12** selection. This extends staged
functional platform/runtime evidence, not earlier declared Python or cross-platform
installed wheels, installed process coverage/memory, unowned detached lifetime,
process-tree cleanup, power-loss, sandbox/authentication or full capture assurance.

Strict CI remains informational **`scripts/check.sh -c`**, distinct from worker and
coordinator local default/memory **`-v`**. Reported Python **2013/2013** and native
retained populations are not instrumentation of actual installed child invocations.
Prior precise native exclusions/runtime suppressed allocations, unsupported finalizer
abandonment, unavailable Python mutation tooling/six selected negative probes, scaled
versus genuine profile fault distinctions, consuming-commit substitution and trust/
full-history/unknown/cleanup/acknowledgement limits remain explicit above.

Final evidence: `/tmp/dml-iteration7-final-ci.{json,log}`,
`/tmp/dml-iteration7-final-runs.json`, `/tmp/dml-iteration7-ci-watch.{log,exit}` and
`/tmp/dml-iteration7-reviewed-staged.diff`. Focused implementation publication is one
**22-file / 2594-insertion / 29-deletion** commit. No postacceptance runtime/test/as-built
change, manual/release workflow, force push/new remote/tag/release/package publication,
extra agent, cloud/global tooling or later feature turn. Design notes remain separate,
local/uncommitted; no design commit/push requested.

Coordinator explicitly directs finalization of **only this RESULTS report**, then stop
all implementation/build/staging/commit/push/CI activity. Report finalized; work is
**complete and stopped**. Remaining REVIEW/COORDINATION/design-status reconciliation
belongs to coordinator. No further runtime/build/test/CI rerun or publication is planned.
