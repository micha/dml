# Iteration 4 implementation results

Status: implementation and final independent acceptance complete. Published through
**`d498a6c`**; all six jobs in its exact-SHA CI run pass. Work is **stopped**. No release,
tag or package publication; design notes remain local/uncommitted.

## Preflight and baseline

Implementation initially clean at `9b8fb7176e31186621dd5a4c26adadec4d76bc1e`.
`/work` is mounted. Machine index, machine guides, both repository instructions and
all handoff prerequisites were read completely. Coordinator-owned design changes
are preserved; only this report is worker-owned here. No extra agents, global
install, cloud experiments or later feature work.

Baseline from `../dml`:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Completed successfully: 316 Python tests, Python 469/469 statements, seven C
executables under Valgrind, retained C 1681/1681 lines, 132/132 functions and
1562/1562 outcomes. Existing binding and 141 CLI memory workloads pass; binding
has zero unsuppressed errors with existing runtime suppressions. Log:
`/tmp/dml-iteration4-baseline.log`. Worker began adding the new files after the
baseline Python population had run; baseline is not new-module coverage evidence.

## Selected engineering choices

- Separate explicitly imported `daggerml.local`, only public repository calls;
  no native/codec/CLI command additions and no changes to old adapters/specs.
- Candidate v1 role spellings, UUID4 `q-`/`a-` occurrences and ordinary reservation/
  publication refs; three collision tries; exact starting-tree preservation.
- Captured entry bytes (1..1 MiB), absolute interpreter, 1..3,600,000 ms timeout;
  adapter URI `urn:daggerml:local-python-v1`. Imports/runtime/environment remain
  uncaptured. New optional `scratch_dir` selects an existing parent, not deletion
  authority over that directory.
- Four positional child arguments; typed pinned context plus cooperative
  `publish_result` in the child's existing transaction. Parent handles close before
  dispatch/wait; finalization independently verifies role/attempt/tree/parents.
- File-backed binary diagnostics, retained 4096 bytes/count/truncation per stream;
  bounded UTF-8 detail; terminate/wait five seconds, then kill/wait five seconds
  for the direct child. No process-tree, disk-growth or spawn-time deadline claim.
- Frozen `LocalContext` inside frozen `LocalRun`; errors carry the committed initial
  context when available, never claim `done` on failed persistence. Failure and
  cleanup are separate; valid publication on nonzero exit/timeout is evidence.
- Explicit retry uses the reserved immutable request and creates a new attempt.
  Initial descriptions remain outcome/status-free after interruption.

Required documentation skill initially failed with a quota error. Current official
Python `subprocess`, `tempfile`, `uuid` and `os.path` documentation was fetched and
consulted as a fallback. After the user identified existing shell configuration,
the same skill's Context7 lookup/query flow succeeded via authenticated REST with
that existing configuration (no key printed/copied into reports). Selected library
**`/python/cpython`**, authoritative stdlib documentation; three queries cover
subprocess lifetime/arguments/reaping, mkdtemp ownership/absolute paths and UUID4/
hex. No new configuration or global tooling changes. APIs newer than the declared
Python minima were not selected; mkdtemp is explicitly absolutized.

## Implementation checkpoints

- First focused acceptance suite: 20 passed, exit 0; log
  `/tmp/dml-iteration4-local1.log`. Real staged parent/child imports and durable
  addition/publication, retry, failure, timeout, cleanup and diagnostics.
- Expanded deterministic interruption/conflict/storage suite: 36 passed, exit 0;
  `/tmp/dml-iteration4-local2.log`.
- First focused coverage command incorrectly supplied a file as `--source`, so
  coverage warned the local module was not imported. Its 36 tests passed but that
  report is **not** module coverage evidence. Log:
  `/tmp/dml-iteration4-focused-coverage.log`.
- Correct root-source coverage checkpoint: 352 passed, exit 0, 854/872 statements;
  18 missing statements led to meaningful malformed-record/error tests, no exclusions.
  Log: `/tmp/dml-iteration4-coverage1.log`.
- Next root-source coverage checkpoint: **366 passed**, exit 0, Python **872/872**
  statements, including local layer **355/355** and both examples **48/48**.
  Log: `/tmp/dml-iteration4-coverage2.log`. This is Python-only validation, not yet
  the final fresh standard C/Python/memory gate.

During self-review, an outer OSError handler could have mislabeled post-launch
IO/reaping failure as a recorded launch failure. Corrected before review; explicit
post-launch IO and unreaped-child regressions now require unknown/no final status.

## Evidence boundaries

Tests stage maintained Python sources and this build's exact real extension into a
normal package. A fresh process asserts module/extension provenance. Production
runner has no import/bootstrap/fault hooks. Real children execute captured source,
read pinned inputs 4/7 and publish results rooted in 11. Host-side direct child/helper
and example execution supplies measured Python statement coverage; installed/staged
subprocesses are **not** claimed coverage-instrumented.

Deterministic private fixture barriers are immediately before `_execute` and before
`_finalize` (after real child publication/reap), outside production code. Parent
termination leaves initial records with no status/outcome; fresh readers inspect
unknown and explicit retry preserves earlier bytes/attempts. Test-owned scratch is
cleaned in finally blocks with finite process/barrier deadlines. Portable terminate
is used. Local direct evidence is Linux; final CI also exercises these fixtures on
macOS/Windows. That is not a general signal, process-tree or hard-parent-loss cleanup
proof.

Meaningful negative paths include ref-create/commit preparation abort (no launch),
bounded collision retry/exhaustion, real child write abort and real 1 MiB-map child
map-full, invalid publication role/attempt/type/tree/parents, bare objects/unchanged
ref, publication plus nonzero exit, completion abort/map-full substitution, moved
head, malformed consumed role records, non-I64/literal arguments and signed overflow,
oversized/non-UTF8 diagnostics, failed scratch removal and unreaped-child disposition.
Narrow substitutions are private tests over real API/LMDB state, not installed fault
controls or claims that injected commit errors are actual disk-failure reproduction.

No Python mutation framework is currently available in the existing tools shell:
`mutmut`, `cosmic_ray` modules/commands absent. No bootstrap was performed. Existing
Mull/native memory evidence is not mutation assurance for this Python layer. Bounded
negative-oracle probes below supplement, rather than replace, that unavailable tooling.

## Bounded negative-oracle probes

Session-local ignored `../dml/build/iteration4-oracles/run.py` loads four modified
copies under a private module name, without changing maintained source or shipped
child code. Selected regression assertions reject all four: zero exit without
publication incorrectly called success; wrong attempt association accepted;
completion head-conflict guard removed; cleanup failure called `ok`. Each pytest
probe exits **1 at its intended assertion**, not collection/import failure; the
harness exits 0 after checking those failures. The probes were repeated against
final source with the same four intended assertion failures and harness exit 0
(`/tmp/dml-iteration4-oracles2.log`). This is four hand-selected host-side
negative-oracle probes, **not** a broad mutation framework, mutation score or
installed-child mutation coverage. Log: `/tmp/dml-iteration4-oracles.log`; exact
copies and assertion reports remain in that ignored scratch directory.

## Current local installed smoke

Used existing project-local packaging-tools venv with no bootstrap. Initial wheel
build outside the tools shell exits 1 because `patchelf>=0.11.0` was not on PATH,
not because implementation build/tests failed. Log:
`/tmp/dml-iteration4-installed-build.log`. Repeating inside existing `nix develop`
uses the available tool and exits 0. Fresh core and console wheels build; a new
ignored venv is created without pip and populated offline through the existing
installer. Commands, from `../dml` inside the existing tools shell:

```sh
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration4-packaging/dist .
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration4-packaging/dist python/daggerml-cli
build/iteration2-packaging/bin/python -m venv --without-pip \
  build/iteration4-packaging/installed
build/iteration2-packaging/bin/python -m pip \
  --python build/iteration4-packaging/installed/bin/python install \
  --no-index --no-deps build/iteration4-packaging/dist/*.whl
```

Session-local `build/iteration4-packaging/installed_smoke.py` runs from `/tmp` with
PYTHONPATH unset and the new console directory on PATH. Parent/child/reader assert
module, local-layer and native-extension paths in the new venv's site-packages;
console and bundled native paths are verified. Two real additions have distinct
requests/attempts and equal result DAGs rooted in 11. Fresh reader compares saved
initial bytes after head movement. Installed console/native outputs agree exactly
for snapshot by head/pinned commit, request/final-attempt walk, publication ref and
all-parent log. The maintained driver additionally runs outside checkout and
reports four distinct attempts including failure and explicit retry.

Build/install and smoke exit 0; logs `/tmp/dml-iteration4-installed-build2.log` and
`/tmp/dml-iteration4-installed-smoke.log`. After the NFC/shutdown fixes, the core
wheel is freshly rebuilt, both wheels force-reinstalled **only into the new local
venv**, and smoke passes again: `/tmp/dml-iteration4-installed-build3.log` and
`/tmp/dml-iteration4-installed-smoke2.log`. Current wheel hashes/contents remain
local artifacts, not published packages. No sdist or staged archive route was
claimed. Evidence is CPython **3.13.15 / Linux x86_64**, `cp313-abi3-linux_x86_64`
core and `py3-none-any` console; not earlier-interpreter, other-platform, manylinux
or release evidence. Runtime declarations remain unchanged.

Final local wheel SHA256:

- Core: `94a2b4c8ec736065b15f88d66e0929d0b0b0422b8fa4eca949c852c244e06987`.
- Console: `f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`.

## Final validation checkpoints

First fresh default `scripts/check.sh -v` exits **0**: 366 Python tests,
872/872 Python statements, seven C executables, retained C 1681/1681 lines,
132/132 functions, 1562/1562 outcomes, existing binding/141 CLI Valgrind workloads.
Log: `/tmp/dml-iteration4-default1.log`. This predates the final NFC path restriction
and avoiding duplicate shutdown after a failed shutdown; it is not final-source
validation. Native STRING normalization prompted rejecting non-NFC recorded
interpreter/allocated scratch paths before dispatch, rather than retargeting paths.
The existing repository path API is unchanged. Current official `unicodedata`
normalization documentation was consulted; two new regressions cover the restriction.

Fresh final-source default run exits **0** (`/tmp/dml-iteration4-default2.log`;
explicit status `/tmp/dml-iteration4-default2.exit`): **368 Python tests**,
**878/878 statements**, including local layer **361/361** and both examples **48/48**;
**seven C executables** pass under Valgrind; retained C **1681/1681 lines**,
**132/132 functions**, **1562/1562 outcomes**. No new coverage exclusion, suppression
or threshold change. No DML function is excluded; existing exact native/dependency
exclusions remain cataloged, not claimed tested. No fresh marker-free/Mull run is
claimed for unchanged native sources.

Existing binding memory workload passes with **zero unsuppressed errors/leaks**:
exit heap 500,617 bytes/8,713 blocks, comprising existing narrowly suppressed CPython
runtime 476,181 bytes/8,653 blocks and reachable 24,436 bytes/60 blocks; 623 suppressed
runtime contexts. This is not a new runtime-only/full pair or a claim of no retained
Python allocations. Unsupported foreign-last-owner abandonment remains outside
supported leak-free evidence. Existing **141 native CLI Valgrind processes** pass.
No new process-level Valgrind/sanitizer/mutation guarantee is inferred for local
execution; the real children supply functional/publication/disposition evidence.

## Reviewed implementation slice (pre-publication checkpoint)

Implementation paths relative to `../dml`:

- New layer: `python/daggerml/daggerml/local.py`; runtime installation: `meson.build`.
- Examples: `examples/{local_execution,local_add}.py`.
- Tests: `tests/python/test_local_{execution,failures,records}.py` and private
  `tests/python/local_interruption_parent.py`.
- Owning as-built contract: `docs/spec-next/local-execution.md`.
- Navigation/orientation: `README.md`, `docs/architecture.md`,
  `docs/packaging-and-distribution.md`, `docs/spec-next/{README,python-api}.md`,
  `python/daggerml/README.md`; coverage accounting: `tests/coverage-exclusions.md`.

No changes to native sources/headers, low-level API lifetime/codecs, CLI grammar/
JSON, old `docs/spec/`, adapter scaffold, package version/runtime/platform declarations,
release workflows or global tooling. No credentials or raw environment-bearing logs
are copied into reports. At the review pause the implementation index was empty
and all turn files were uncommitted. Build/install/oracle scratch is ignored;
new repository/process scratch is test-owned.

At the worker review pause, whitespace checks passed in both checkouts and automated
validation passed for nine worker-owned changed Markdown documents, 113 local
targets/anchors. HEAD was baseline `9b8fb71` with the 16-file slice uncommitted and an
empty index; no lingering test parent/entry process or untracked repository scratch.
The publication and bounded CI follow-ups below supersede that pre-publication state.

Before acceptance, worker runtime/test edits and `build/check` use were explicitly
paused/released for independent coordinator review/validation. The acceptance below
supersedes that pause and publication block, not the scope/assurance limits. A possible
next bounded turn is inspection-led reconciliation of unknown local outcomes; this
suggestion is not started or authorized and does not imply automatic old-attempt
dispatch.

## Independent coordinator acceptance

The coordinator explicitly accepted the bounded implementation and released
`build/check` back to the worker for authorized publication/CI fixes. No outstanding
functional finding; [REVIEW.md](REVIEW.md) owns independent inspection and evidence.
The following is coordinator-reported, not a new worker rerun:

- Fresh default `scripts/check.sh -v`, exit **0**: **368 Python tests**, **878/878
  statements** (local **361/361**), **seven C executables**, retained C **1681/1681
  lines**, **132/132 functions**, **1562/1562 outcomes**. Existing binding and
  **141 native CLI Valgrind processes** pass. Logs:
  `/tmp/dml-iteration4-coordinator-check.log` and `.exit`.
- Separate current offline-installed venv supplies **43 independent checks**, exit 0,
  including installed parent/real child/fresh reader/console provenance, real timeout
  after durable publication retaining evidence/history, cross-head explicit retry,
  completion-head conflict preserving unknown, duplicate publication rejection,
  saved immutable bytes and ordinary CLI inspection. Log:
  `/tmp/dml-iteration4-coordinator-install.log`.
- Code/spec/test review, Markdown and whitespace checks pass. Existing exclusions,
  process/capture limits, direct-not-transitive validation, unavailable Python
  mutation tooling and local-runtime/platform assurance qualifications remain.

The user/coordinator explicitly authorizes only reviewed implementation staging,
focused commit and normal push to existing `master`/`origin`, plus monitoring/fixing
all automatically triggered workflows for the exact pushed SHA. No force push,
remote creation, tags, release/manual release trigger or package publication.
Publication details follow; design notes are not to be committed.

## Publication checkpoint

All 16 reviewed implementation files were reread/inspected, explicitly staged and
checked; the index contains only that slice (**1,576 insertions, 3 deletions**).
No remaining unstaged/untracked implementation files. Staged whitespace checks pass.
Focused commit
[`efac107a084d1a686f3ce7d47b1b549ade2f0e39`](https://github.com/micha/dml/commit/efac107a084d1a686f3ce7d47b1b549ade2f0e39)
(`Add local recorded Python execution`) is normally pushed to existing
`origin/master`; commit/push exit 0. The unpushed commit message body was corrected
before push, without implementation changes or a force push. Remote master SHA
matches exactly, and implementation worktree/index are clean. Design notes remain
local/uncommitted, preserving coordinator-owned edits.

[Automatic CI run 40532370498](https://github.com/micha/dml/actions/runs/40532370498)
is for exact head `efac107a084d1a686f3ce7d47b1b549ade2f0e39`, push event. All five Unix
jobs have succeeded; Windows Python tests are still in progress at this checkpoint.
No CI failure/fix or rerun yet. This is the only automatic workflow listed for the
SHA; the tag/manual release workflow was not triggered. An initial synchronous
`gh run watch` invocation exceeded its 200-second harness timeout while CI remained
in progress; this is **not a workflow failure**. Monitoring continues with a bounded
background watch and explicit exit file; final job/log counts follow after completion.
No tag, release/manual release trigger, package publication or later feature work.

### Stalled Windows run and bounded diagnostic follow-up

Run **40532370498** did **not** pass. All five Unix jobs succeeded, but Windows's
Python step ran abnormally long (prior Iteration 3 roughly 35 seconds; this run
exceeded nine minutes). Live job logs repeatedly returned unavailable. Coordinator
requested lock/lifetime inspection and authorized cancellation, then forced
cancellation after ordinary cancellation did not finish. Run concludes **cancelled**
at 15:50:15Z; Windows job cancelled, not passed. Job-log retrieval at this checkpoint
still says `log not found`; no localization from that log is claimed. Cancellation
and failed log-fetch history are preserved under `/tmp/dml-iteration4-{cancellation*,
stalled-final.json,windows-*,force-cancel.json}`. The watch's cancelled conclusion is
not a validation success.

Static inspection found no obvious overlapping handles. Session-local public-lifetime
instrumentation (`build/iteration4-oracles/lifetime_probe.py`) runs all **52 new tests**
on Linux, exit 0: **332 opens**, **267 write factories**, **79 actual spawns**, with
no overlapping same-path repository wrappers or live parent repository at a real
spawn; no live handles at suite end. Log `/tmp/dml-iteration4-lifetime-probe.log`.
This helps inspect the test seam but neither bounds nor proves Windows native calls.
Subprocess timeouts alone do not bound same-process LMDB calls.

A concrete lead is the oversized-source case's automatically generated pytest node
ID: **1,048,725 characters**, independently measured by collection. Pytest stores
current IDs in `PYTEST_CURRENT_TEST`; CPython's Windows environment implementation
rejects oversized values. This is a plausible Windows setup/reporting problem, not
yet a diagnosis from a Windows stack trace. No speculative production fix.

Coordinator explicitly accepted a **CI-only diagnostic/finiteness** follow-up:
`.github/workflows/ci.yml` limits matrix jobs to ten minutes and runs Windows with
`python -u -m pytest -vv -o faulthandler_timeout=60`. Tests/thresholds/production code
remain unchanged. Diff/whitespace and installed pytest-option checks pass; no YAML
parser/actionlint was locally available and none was bootstrapped. GitHub accepted
and started the workflow, providing configuration-parse evidence, not test success.
Focused one-file commit
[`b0e3107e2a2c0767f79076b72b8e9e097ad291dc`](https://github.com/micha/dml/commit/b0e3107e2a2c0767f79076b72b8e9e097ad291dc)
(`Bound CI jobs and diagnose stalled Windows tests`) is normally pushed to existing
`origin/master`, exit 0; exact remote SHA and clean implementation checkout verified.
[Diagnostic CI run 40534587951](https://github.com/micha/dml/actions/runs/40534587951)
is the automatic push run for that exact SHA. At that checkpoint it was briefly
pending behind the stalled run's cancellation and then running; final success was
still blocked on meaningful diagnosis/fixes and final exact-SHA CI. No test
skip/suppression, manual workflow/release trigger, package publication or scope
expansion. Its actual cancelled conclusion and missing-log qualification are below.

### Confirmed oversized pytest-ID defect and accepted test-only fix

Current pytest documentation (`/pytest-dev/pytest`, authenticated Context7 lookup
with existing configuration, no secret printed) confirms explicit `ids` and that
pytest stores node IDs/stages in `PYTEST_CURRENT_TEST`. Inspected public CPython
Windows environment implementation enforces `_MAX_ENV`. A private bounded Linux
model applies that documented size rejection to only `PYTEST_CURRENT_TEST`:
`build/iteration4-oracles/windows_env_probe.py`. Before the fix, it exits **1** with
**9 passed, 2 errors** (setup/teardown of the oversized-source case), showing the
portable test defect under the documented environment-size rule. Log:
`/tmp/dml-iteration4-windows-env-probe.log`. This model is not a Windows runtime or
an observed stack trace from the stalled job, whose logs remain unavailable.

Coordinator explicitly accepts the confirmed **test-only** repair without waiting
for a speculative production change: all ten binding-boundary cases have short
semantic IDs; a per-case regression checks the collected `request.node.nodeid` is
at most 160 characters. The original **1 MiB + 1 byte** source and its rejection
assertion are unchanged. After the fix, the same Windows-environment model exits
**0**, **10 passed**; focused new suite exits **0**, **52 passed**. Maximum collected
ID for the whole new execution test module drops from **1,048,725** to **99** chars.
Logs: `/tmp/dml-iteration4-windows-env-probe-after.log`,
`/tmp/dml-iteration4-test-id-fix-focused.log` and `collection-after.log` (each prefixed
`/tmp/dml-iteration4-`). No skipped/reduced input, production change or weaker gate.

Fresh default `scripts/check.sh -v` against this accepted test-only fix exits **0**:
**368 Python tests**, **878/878 statements** (local **361/361**), **seven C executables**,
retained C **1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**, binding
and **141 CLI Valgrind processes**. Logs `/tmp/dml-iteration4-test-id-fix-default.log`
and `.exit`. Existing exact exclusions/suppressions and all assurance limits remain.
The single changed test file's complete staged diff is inspected; no other file is
staged. Focused commit
[`d498a6cd4eea170c2054690880526c2fbb6ebaa6`](https://github.com/micha/dml/commit/d498a6cd4eea170c2054690880526c2fbb6ebaa6)
(`Bound pytest IDs for local binding boundary test cases`) is normally pushed, exit 0.
Exact remote master SHA matches and implementation checkout/index are clean.
[Automatic exact-SHA run 40536650838](https://github.com/micha/dml/actions/runs/40536650838)
was initially pending behind the diagnostic run's shutdown and subsequently passed.
The confirmed ID defect and the unobserved original Windows stack remain distinct;
final evidence follows.

## Final exact-SHA CI and independent acceptance

The bounded diagnostic run **40534587951** completed **cancelled**, not success:
all five Unix jobs succeeded and Windows was cancelled. Its ten-minute configured
matrix-job bound was followed by extended shutdown/cancellation grace; the queued
fixed-ID run started after shutdown completed. No forced cancellation of this second
run was needed: it had already completed when the coordinator authorized force-cancel
if still necessary. The diagnostic watch's separate 900-second harness ended **124**
before the final cancelled result was fetched. That harness timeout is not a test
pass or a replacement for the actual run conclusion. The original cancelled run's
background watch exits **1**; the earlier synchronous watch timeout is recorded above.

Completed Windows log fetches for **both** cancelled runs still return `log not found`
(job IDs `122288354914` and `122297479196`), including the final retries. No earlier
Windows stack trace was obtained. Missing logs establish neither a native-code defect
nor a platform fault, and the exact original stall/log-transport mechanism is not
claimed diagnosed. The confirmed oversized-node-ID defect is demonstrated by the
before/after Windows-environment **model**; the unchanged oversized input then also
passes on actual Windows in the final run. No speculative production repair occurred.

Final implementation SHA is
[`d498a6cd4eea170c2054690880526c2fbb6ebaa6`](https://github.com/micha/dml/commit/d498a6cd4eea170c2054690880526c2fbb6ebaa6).
[CI run 40536650838](https://github.com/micha/dml/actions/runs/40536650838) completes
**success**, exact head SHA verified. Worker bounded `gh run watch --exit-status`
exits **0**; final run/job JSON, completed full logs, remote master and clean checkout
are checked. The only automatic workflow for that SHA is this completed CI run.
No manual workflow, tag or release was triggered.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40536650838/job/122306375439) | Success | 7 | 368 passed |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40536650838/job/122306374559) | Success | 7 | 368 passed |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40536650838/job/122306374113) | Success | 7 | 364 passed, 4 existing skips |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40536650838/job/122306374428) | Success | 7 | 364 passed, 4 existing skips |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40536650838/job/122306374385) | Success | 7 | 363 passed, 5 existing skips; 45.99 seconds |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40536650838/job/122306374931) | Success | 7 | 368 passed |

Four existing macOS skips concern absent `/dev/full`; Windows has those plus the
existing Unix closed-pipe case. No new skip/suppression or reduced input. Windows
uses CPython **3.14.9** in UCRT64; its verbose completed log specifically reports
`test_binding_bounds[oversize-source] PASSED`. This functional/staged-runtime CI
is not installed-wheel, earliest-interpreter, process-memory or sandbox evidence.
Strict Linux is informational **`scripts/check.sh -c`**, not the local default
percentage/memory gate; it reports retained C 1681/1681 lines, 132/132 functions,
1562/1562 outcomes and Python 878/878. Worker/coordinator default `-v` and installed
checks remain separately recorded, with all exclusion/platform/capture limits.

The coordinator independently verifies the final exact SHA, only automatic run,
all six completed jobs/full logs, `gh run watch` exit 0, clean checkout and matching
remote master. It also inspects the test-only fix and independently reruns all
**52 new tests**, exit 0. This is coordinator-reported additional evidence; independent
review/final acceptance is owned by [REVIEW.md](REVIEW.md).

Per final coordinator instruction, retain the accepted ten-minute matrix-job bound,
Windows verbose/unbuffered bounded IDs and sixty-second faulthandler configuration.
The worker's proposed ordinary-output-only follow-up was **not performed**; no fourth
commit/CI cycle. The three published focused commits change **17 unique implementation
files**, 1,583 insertions/4 deletions: the initial reviewed 16-file slice, accepted
CI-only diagnostics and the accepted test-only ID repair. Native sources/headers,
production runtime after `efac107`, old spec, adapters, declarations and releases are
unchanged. Implementation worktree/index are clean at pushed `d498a6c`.

Final session-local evidence: `/tmp/dml-iteration4-fixed-id-{watch.log,watch.exit,
final.json,final.log}`, `/tmp/dml-iteration4-final-run-list.json`, diagnostic-final JSON
and both cancelled Windows last-fetch error files. Raw logs/credentials are not copied
into notes. Final whitespace checks pass in both checkouts; all nine worker-owned
changed Markdown documents pass **115 local target/anchor checks**. No lingering
worker check, child/parent fixture or watch process was observed. Design notes
remain uncommitted; coordinator owns REVIEW/status/resume. Only this RESULTS file
is finalized by the worker. All implementation/build/CI work
is stopped after explicit final acceptance; no further code, feature, commit/push,
agent, release/tag or package publication.
