# Iteration 6 implementation results

Status: bounded implementation, independent review, focused publication and final
exact-SHA CI verification are **complete**. Published as **`a0aa05d`**; all six CI jobs
pass on the first run. Work is **stopped**. Coordinator owns COORDINATION/REVIEW/design
status; worker owns this report. No release/tag/package publication or later feature.
No extra workers, release/tag/package publication, cloud or later feature work.

## Authority, preflight and clean baseline

User declared Iteration 6 GO in this new existing-worker session, authorizing bounded
implementation, monitoring/review fixes until satisfactory, then worker commit/push
and exact-SHA CI fixes. Publication waits for explicit coordinator acceptance.
Worker is pane `%215` (`TMUX_PANE` and parent process verified); unqualified tmux display
reflects the active coordinator window and was not used as worker identity. `/work`
is mounted. Required machine/design/implementation instructions and handoff context
were read completely. Implementation initially clean at
`0ec769b5e85fde6b6581b628fffdf3465c78a098`; coordinator design edits are preserved.
Coordinator explicitly grants exclusive worker `build/check` and `build/coverage`
ownership until review freeze/release.

Clean standard baseline completed **before all measured source edits**:

```sh
# from ../dml
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration6-baseline.{log,exit}`, exit **0**: **467 Python tests**, seven C
executables, Python **1163/1163 statements**, retained C **1681/1681 lines**,
**132/132 functions**, **1562/1562 outcomes**. Existing binding Valgrind has zero
unsuppressed errors (624 existing CPython runtime contexts suppressed); **141 native
CLI Valgrind processes** pass. No baseline edits/coverage contamination.

## Selected implementation choices

- Explicitly imported `daggerml.exchange`, public repository/local/transfer operations
  only. No private runtime helper/callback, packed codec/hash or native expansion.
- Frozen `ExchangeSpec`: fresh UUID4 transport-only token, explicit commit/tree names,
  selected DAG IDs, canonical intent URI, explicit B ref. Candidate descriptor labels,
  8 KiB limits/fixed filenames and one-shot marker retained. Exact fields documented
  in [owning contract](../../../dml/docs/spec-next/repository-execution.md).
- New caller-owned retained workspace/B; prepare is read-only at A, execute acquires
  exclusive marker before B bootstrap/import/dispatch. No auto-retry/marker clearing.
- Unchanged public `local.run_step`, occurrences created in B; exact F export and
  receipt-last publication after real runner completion, including recorded failure.
  IO/profile failure afterward does not lose B or rewrite computation as failure.
- Receive compares independently owned expected selection/token, imports output into
  private disposable validation storage through public transfer, checks consumed
  typed roles/tree/parents/result/evidence/cleanup, closes/cleans scratch before
  unchanged atomic A import under explicit ref. No A head update/adoption/merge,
  operational copied refs/paths or runnable LocalContext manufactured at A.
- Descriptions own commit/count/occurrences/typed DAG IDs and computation/cleanup
  fields. Native/local/transfer/filesystem exceptions retain existing types;
  `ExchangeError` handles fixed-message layer framing/association violations.
- No native production, original local/transfer public contract, old spec, CLI
  grammar/JSON, adapter, runtime/version or workflow changes.
- Refinement: execute's `map_size` controls B initialization/input import. The unchanged
  local runner reopens with its own existing default options; this argument is not
  an execution/result-size quota. Receive's option controls final A import, not private
  default-sized validation. Documented explicitly; no existing public contract changed.

### Documentation consultation

Loaded required Context7 skill and queried **`/python/cpython`** successfully via
available tools: same-directory temporary-file/replace and exclusive/bounded file IO,
strict JSON duplicate-key/nonstandard-constant hooks, and subprocess finite wait/
terminate/kill/reap semantics. Selected only declared Python >=3.8-compatible APIs;
no `delete_on_close` (3.12+) or 3.15 process APIs. No credentials printed or global
configuration/tooling changed.

## Host checkpoints and review refinements

- First focused selection/packet/work suite: **59 passed**, exit 0;
  `/tmp/dml-iteration6-focused1.log`.
- Initial focused coverage invocation incorrectly used a file as `--source` module
  name, collected no data and reports no coverage evidence. Corrected directory
  invocation: **59 passed**, new layer **315/344 statements**;
  `/tmp/dml-iteration6-focused-coverage{,2}.log`.
- Expanded fault/role/history checkpoint: **131 passed, 2 failed**. Test-only defects:
  private raw-write fixture used nonexistent keyword, and parentless modified pre
  omitted C from closure, causing native not-found before intended parent oracle.
  Corrected data argument and retained C with deliberately wrong two-parent P.
  `/tmp/dml-iteration6-focused2.log`.
- Next checkpoint: **133 passed**, new module **344/344 statements**, no exclusions;
  `/tmp/dml-iteration6-focused3.log`. This is host-helper coverage, not coverage of
  staged/installed subprocess invocations.
- Coordinator early read-only review found no production issue and requested stronger
  late fault/new-put/raw-ref, separate-worker caller pause, actual false-success and
  generated history/repeat-receive evidence. Added successful new actual-A put tracking,
  whole-file raw-state equality, actual separate completed/reaped worker caller barrier,
  genuine recorded failure relabelled success and generated history/reimport properties.
- Runnable story/host helper checkpoint: **140 passed, 1 collection error**. Hypothesis
  positional arguments consumed trailing monkeypatch fixture rather than `name`;
  switched to explicit keyword strategies. Example **132/132**, layer **344/344** at
  this preceding checkpoint; error is not green final validation.
  `/tmp/dml-iteration6-focused4.log`.

## Final host validation and meaningful fault evidence

After keyword-strategy correction and actual post-computation record-limit test,
focused **142 tests pass**, exit **0**; `/tmp/dml-iteration6-focused5.log`.
Fresh full standard command above exits **0**:
`/tmp/dml-iteration6-default1.{log,exit}`. **609 Python tests** (59.36 seconds),
**seven C executables**, Python **1639/1639 statements** (exchange **344/344**, example
**132/132**), retained C **1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**.
No measured source edits occurred during/after this final default run. Native
production and coverage exclusions/thresholds are unchanged; no new suppression.

Existing binding Valgrind workload has **zero unsuppressed errors/leaks**, exit heap
**500823 bytes/8717 blocks**: existing runtime patterns suppress **476387 bytes/8657
blocks**, reachable **24436 bytes/60 blocks**, **624 suppressed contexts**. Existing
**141 native CLI Valgrind processes** pass. No new runtime-only/full pair, installed
process-memory, Python mutation or process-tree/security assurance is inferred.
Unsupported foreign-last-owner abandonment remains explicitly outside supported
leak-free finalization.

- Independent breadth-first typed oracles through public descriptions enumerate every
  source/worker/returned object and exact byte, not transfer's internal edges or CLI
  prefixes. Input closure excludes branch-only sentinel; all ordered parent history
  returns unchanged. Saved initial/final objects remain immutable after head movement.
- Two fresh B workspaces have distinct request/attempt occurrences and equal result 11;
  unchanged binding/input selection and later independently moved A main are preserved.
  Receive is nonexecuting/repeatable with B/input/source offline, and historical scratch
  sentinels stay untouched. No B working/reservation/publication ref is copied.
- Actual nonzero/zero-without-publication and nonzero-after-publication outcomes return
  as computation failure, optional evidence separate from result. A separately induced
  local cleanup failure preserves computation success/result and failed cleanup.
- Strict bounded descriptors, missing/partial output, swapped otherwise-identical-job
  token, valid wrong-intent completion, wrong occurrence/typed role/result/evidence,
  tree changes and ordered-parent violations are rejected in isolated storage before
  **any** A write. Entire A `data.mdb` is byte-identical, not merely no bad ref.
  An actual recorded nonzero failure packet with synthesized success/result is rejected
  while B's original final failure/ref remains intact. This is structural validation,
  not external-truth authentication when a trusted worker fabricates all consistent data.
- Real B **1 MiB-map / 2 MiB input** fails before dispatch; retained marker prevents
  reexecution even without a computational occurrence. Source reached-parent genuine
  raw deletion fails preparation. Private fixture deletion is existing infrastructure,
  not an installed fault/deletion API.
- Post-computation scaled packed-total profile overflow and an **actual 4 MiB + 1 byte
  result datum** exceeding the owning packed-record profile both retain done/success in
  B, no fabricated receipt/A outcome and no reexecution. Scaled total is not a 16 MiB
  stress claim; actual per-record bound is separately exercised.
- Actual file-open/rename failures at preparation/input/job and worker/output/receipt
  boundaries retain caller-owned files/B. Validation-scratch cleanup failure prevents
  A publication and only helper-allocated scratch is cleaned by fixture afterward.
- Real late A **1 MiB-map / 2 MiB new result** failure and private substituted consuming
  native storage-commit failure track **successful genuinely new actual-A puts** (not
  validation-store puts or preexisting duplicates), including exact readback in that
  transaction **before** the failure. Fresh independent process then proves absence
  of every new returned record/ref and preservation of every saved original record,
  main/sentinel. Explicit **8 MiB whole receive/import retry** succeeds, never execution
  retry. Commit substitution returns dependency EIO/consumes the real handle; it is
  not an actual disk/device failure.
- Different-target and raw wrong-width return refs likewise fail late after successful
  new puts. Entire A `data.mdb` byte equality preserves **raw ref bytes** (including
  malformed content), plus fresh public readable-target/integrity-error checks. No
  overwrite/repair of a malformed ref is claimed.
- Private real-process barriers: initial persisted unknown B **before child spawn**;
  done B **after actual child reaping/final commit**, before packet; separate real
  worker process **completed/reaped** before interrupted caller pauses; A after three
  successful genuinely new puts before commit versus **after actual successful A
  storage commit** before return. Finite waits/finally terminate/kill/reap, fresh full
  byte/ref readers distinguish old from complete A state. Receiver re-read never
  dispatches. These are safe local cooperative barriers, not arbitrary-child-kill,
  descendant cleanup, power-loss, exactly-once or automatic recovery assurance.
- Hypothesis covers bounded names/selection identities, generated extra final-history
  entries and multiple arbitrary explicit return refs/repeated receives. Shared immutable
  completion fixture is intentional for reimport properties; generated history starts
  from the original F each time and asserts byte-identical A on rejection.

## Mutation gap and selected negative-oracle probes

Current existing tools shell has no `mutmut`/`cosmic_ray` modules or commands; no
bootstrap. Existing Mull is not Python mutation assurance. Five private **in-memory**
source guard/order probes in ignored `build/iteration6-oracles/probe.py` each produce
pytest exit **1 / one intended failing test**, aggregate harness exit **0**:
`/tmp/dml-iteration6-oracles.log`.

1. Ignore request-selection mismatch: valid wrong-intent packet is wrongly accepted.
2. Publish A before isolated selected-record validation: complete A byte-state oracle
   catches premature writes even though the validation exception still occurs.
3. Ignore success/publication/exit check: actual failure relabelled success is accepted.
4. Update A main after receive: independent caller-head preservation oracle fails.
5. Replace exclusive marker creation with overwrite: prestarted workspace executes.

These five selected negative oracles are not a broad mutation score, equivalent-mutant
claim or independent installed mutation coverage. No source file was altered by probes.

## Fresh installed acceptance and wheel provenance

Existing project-local packaging tools only; no bootstrap/global install/package
publication. Current core/console build and offline pip-less install exit **0**:
`/tmp/dml-iteration6-installed-build.{log,exit}`. Commands, from implementation:

```sh
# inside the existing nix develop ../dml-build-tools shell
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration6-packaging/dist .
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration6-packaging/dist python/daggerml-cli
build/iteration2-packaging/bin/python -m venv --without-pip \
  build/iteration6-packaging/installed
build/iteration2-packaging/bin/python -m pip \
  --python build/iteration6-packaging/installed/bin/python install \
  --no-index --no-deps build/iteration6-packaging/dist/*.whl
env -u PYTHONPATH build/iteration6-packaging/installed/bin/python \
  build/iteration6-packaging/installed_smoke.py
```

Private ignored harness launches fresh installed parent, three worker drivers,
three receivers and reader from `/tmp` with source PYTHONPATH unset. All module/
extension/console/bundled-native paths belong to the new install; actual computational
children assert installed interpreter/module/extension paths, verified in recorded
stdout. Independent public BFS byte/population/parent oracles, A renamed offline
through worker, independent caller head advancement after pin, B renamed offline and
packet-only receive with separate caller expected input, equal result 11/distinct
occurrences, failure and cleanup, absent B refs, inert scratch sentinels and ordinary
console/native JSON agreement all pass. **252 harness check calls across reported
installed modes**, plus byte-identically copied maintained example outside checkout,
exit **0**: `/tmp/dml-iteration6-installed-smoke.log`. Test-owned retained evidence
`/tmp/dml-iteration6-installed-story-5fabsxdm`; all owned child processes completed/
reaped normally. Harness assertions are finite functional evidence, not installed
process coverage or access-control assurance.

Wheel paths supplied to coordinator before review freeze:

- `../dml/build/iteration6-packaging/dist/daggerml-0.1.0-cp313-abi3-linux_x86_64.whl`,
  SHA256 `5b4c5505c0a5f35310a0e066c7154bc2c91fb504165cb7e16939c73a34296a6c`.
- `../dml/build/iteration6-packaging/dist/daggerml_cli-0.1.0-py3-none-any.whl`,
  SHA256 `f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`.

All four wheel Python modules (`__init__`, exchange, local, transfer) equal current
maintained bytes; no test/fault controls packaged. Wheels are current uncommitted-root
builds, not dirty-tree VCS sdist evidence or releases. Local CPython **3.13.15 / Linux
x86_64**, `cp313-abi3` tag is not earlier declared Python/other-platform/manylinux/
sdist validation. Runtime/tag/version declarations remain unchanged.

Coordinator separately reports **73 passing independent installed checks**, exit 0,
using its own offline-populated `/tmp` venv, no shared build writes: independent typed
population/bytes, separate worker with A offline, fresh receiver/separate expected
with B offline, moved-main preservation, repeat receive/no repeat execute, CLI log,
nonzero-after-publication evidence, swapped token and valid wrong-intent rejection
before A writes. It verifies four wheel-module byte equality. This is coordinator-
reported evidence, not a worker rerun; REVIEW owns independent qualification.

## Changed slice, links and review freeze

Relative to implementation `../dml`:

- New `python/daggerml/daggerml/exchange.py`, `meson.build` install inventory.
- New `examples/repository_execution.py`, unchanged `local_add.py` reused.
- New `tests/python/test_exchange{,_records,_process,_example}.py` and private
  `tests/python/exchange_interruption_parent.py`.
- New owning `docs/spec-next/repository-execution.md`, orientation/navigation in
  `docs/spec-next/{README,python-api}.md`, `README.md`, `docs/architecture.md`,
  `docs/packaging-and-distribution.md`, `python/daggerml/README.md`, and assurance
  rationale in `tests/coverage-exclusions.md` (no exclusion added).

**16 files**, no native production/test-core, old-spec, existing public contracts,
adapter/CLI grammar/JSON, runtime/version or workflow edits. Index empty; build/install/
probe scratch is ignored and test-owned. Black passes. New collection **142 cases**,
maximum test-ID length **119**, preserving actual large profile input; no huge repr
exported to environment. Worker Markdown validation passes **9 documents / 141 local
targets/anchors**; whitespace checks pass in both checkouts. Coordinator-owned design
changes are preserved; no design commit/push is requested.

At the review checkpoint, worker explicitly froze all runtime/test/as-built source
edits and build use, released both shared `build/check` and `build/coverage` to
coordinator ownership, and paused for independent review/default validation. No
staging/commit/push/CI launch occurred before explicit acceptance. No extra workers,
release/tag/package publication, cloud/global tooling, automatic recovery or later
feature. Coverage is retained host-helper statement coverage, not every Python
branch/installed child invocation; precise old native exclusions/runtime suppressions,
mutation gap and trust/capture/full-history-profile/storage-acknowledgement limits
remain explicit. Subsequent accepted publication below supersedes the pause, not scope.

## Independent acceptance and focused publication

Coordinator explicitly accepted the reviewed **16-file** slice with no outstanding
finding after independent default `scripts/check.sh -v` exits **0**: **609 Python**,
**seven C executables**, Python **1639/1639** (exchange **344**, example **132**), retained
C **1681 lines / 132 functions / 1562 outcomes**, zero unsuppressed binding errors,
**141 CLI Valgrind processes**. Its separate installed **73 checks**, four wheel-module
byte comparison and **16 Markdown documents / 323 local targets/anchors** pass.
This is coordinator-reported independent evidence, owned by [REVIEW.md](REVIEW.md),
not another worker rerun. Both build directories returned to worker ownership.

Worker re-read the complete staged reviewed diff and verified existing branch
`master`/`origin` (`micha/dml`), clean unstaged state, staged whitespace and only
approved files. Exactly **16 files / 2830 insertions / 4 deletions** staged;
`/tmp/dml-iteration6-reviewed-staged.diff`. No design notes/build scratch staged.
Focused commit
[`a0aa05d56b9e70277a98bb03e26514ab6b6f1415`](https://github.com/micha/dml/commit/a0aa05d56b9e70277a98bb03e26514ab6b6f1415)
(`Execute pinned steps across independent local repositories`) and normal
`git push origin master` exit **0**. Exact remote master matches; implementation
worktree/index clean. No force push/new remote/tag/release/package publication.

Consulted current GitHub CLI docs through Context7 **`/websites/cli_github_manual`**
for exact-commit run filtering, view/jobs/logs and watch exit status. Existing CLI
**2.102.0**, no bootstrap/configuration/credentials output. Exact-SHA `gh run list
--commit <full-sha> --limit 100 --json ...` returns only automatic push
[CI run 40593738345](https://github.com/micha/dml/actions/runs/40593738345). Verified
head SHA equals the commit; all six jobs are initially **in progress**, not passing
completion evidence. A finite `timeout 900 gh run watch ... --exit-status --interval 10`
monitors; `/tmp/dml-iteration6-ci-watch.{log,exit}`. No manual workflow launch.

Coordinator `%197` received commit/remote/run link and current status; prior `%216`
sidebar target correction is honored. No follow-up commit/push without reviewed
bounded diagnosis/regression if CI fails. No later feature turn or design commit.
Final exact-SHA CI evidence remained pending at that checkpoint; completion below
supersedes it.

## Final exact-SHA CI verification and stop

Automatic [CI run 40593738345](https://github.com/micha/dml/actions/runs/40593738345)
completes **success** for exact published SHA
**`a0aa05d56b9e70277a98bb03e26514ab6b6f1415`**. All six jobs pass on the **first run**;
no CI failure, fix, rerun or follow-up commit was needed. Finite `gh run watch
--exit-status` exits **0**, not timeout. Worker fetched complete final run/job JSON,
full logs and exact-commit workflow list, verifying sole automatic **push** run,
head SHA and all six completed successful jobs.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40593738345/job/122504244182) | Success | 7 | 609 passed; 23.92 s |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40593738345/job/122504243877) | Success | 7 | 609 passed; 31.02 s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40593738345/job/122504244150) | Success | 7 | 605 passed, 4 existing skips; 121.60 s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40593738345/job/122504244001) | Success | 7 | 605 passed, 4 existing skips; 60.27 s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40593738345/job/122504243964) | Success | 7 | 604 passed, 5 existing skips; 71.60 s |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40593738345/job/122504243605) | Success | 7 | 609 passed; 48.36 s |

Existing skips concern absent `/dev/full` (macOS/Windows) and the Windows Unix
closed-pipe case. No new skip/exclusion/suppression or reduced boundary input.
Windows verbose log confirms new exchange tests, including safe real-process barriers,
late genuine map-full/whole retry, consuming-commit rollback, wrong typed history,
actual profile overflow and generated repeat/history properties. Unix CI uses
configured Python **3.12**; Windows UCRT64 reports **3.14.9**. This extends staged
functional runtime/platform evidence, not installed-wheel/earliest-declared-Python,
power-loss, descendant cleanup, process-memory, sandbox or adversarial authentication
assurance.

Strict Linux remains informational **`scripts/check.sh -c`**, not local default
percentage/memory **`-v`**. Its Python **1639/1639** report and unchanged retained C
populations are not coverage of actual installed subprocess invocations. Worker and
coordinator default gates, independent installed 73 checks and worker installed
252-check harness remain separately qualified. Precise prior native exclusions,
runtime retained allocations/suppressions, unavailable Python mutation frameworks/
five selected probes and trust/capture/full-history-size/response-loss limits remain.

Coordinator independently confirms complete final JSON/full logs, sole exact-SHA
push workflow list, watch exit **0**, clean implementation tree/index and matching
remote master. Its counts agree above; [REVIEW.md](REVIEW.md) owns final independent
acceptance. Coordinator explicitly directs finalization of **only RESULTS** and stop
all runtime/build/staging/commit/push activity; remaining design status reconciliation
belongs to coordinator. No design commit is requested.

Implementation remains clean at published `a0aa05d`; focused publication is one
16-file commit. No postacceptance runtime/test/doc change, manual/release workflow,
force push/new remote/tag/release/package publication, extra worker, cloud/global
tooling change or later feature. Design notes remain separate, local/uncommitted.
Session-local final evidence: `/tmp/dml-iteration6-final-ci.{json,log}`,
`/tmp/dml-iteration6-final-runs.json`, `/tmp/dml-iteration6-ci-watch.{log,exit}` and
`/tmp/dml-iteration6-reviewed-staged.diff`. No runtime/build/test/CI rerun is planned;
all implementation/publication/monitoring work is **stopped** after final acceptance.
