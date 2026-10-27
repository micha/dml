# Iteration 5 implementation results

Status: bounded implementation, independent coordinator acceptance, publication and
exact-SHA CI verification are **complete**. Published as **`0ec769b`**; all six CI
jobs pass. Work is **stopped**. No release/tag/package publication or later feature.
Design notes remain local/uncommitted. Coordinator owns COORDINATION/REVIEW/status.

## Preflight, authority and baseline

- `/work` mounted. Machine index/guides, repository instructions and every handoff
  required document were read completely. Implementation initially clean at
  `d498a6cd4eea170c2054690880526c2fbb6ebaa6`, empty index; no unrelated work found.
- The user explicitly authorized the existing window-2 agent in this new Pi session
  to implement the approved bounded plan. Planning-only text is superseded, not the
  stop line. No extra workers, cloud, global bootstrap, release/tag/package
  publication, later feature work or unauthorized native production changes.
- Initial standard run:
  `nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file -c bash scripts/check.sh -v`
  from `../dml`; `/tmp/dml-iteration5-baseline.{log,exit}`. Exit **1**, **contaminated**:
  wrapper edits occurred before Python coverage finished. Its 368 passing tests
  measured the new untested wrapper (887 statements/17 missing). This is neither
  clean-baseline failure nor final-source validation. Fresh final gates remain required.
- Session naming was initially misdirected to coordinator `%198` because unqualified
  tmux display reflected the active pane. Acknowledged; sent
  `/name dml-iteration5-implementation` explicitly to worker `%215`. No session-file
  manipulation, extra agent or restart. Coordinator-owned design edits are preserved.

## Selected engineering choices

- Public `Transaction.put_record(kind, record)` is a narrow mutation-guarded wrapper
  over existing native insertion. Exact string kind/exact bytes, explicit immutable
  type, native computed ID, native dependency/no-overwrite checks; conversion/native/
  return-allocation failure poisons. Read rejection, owner-thread and ended-handle
  rules remain unchanged. No packed Python codec/hash, native API or encoding change.
- Explicit `daggerml.transfer`, using public operations only. One typed edge enumerator
  over owned descriptions follows every ordered commit parent, canonical tree entry,
  DAG root/binding, literal/sub-DAG target and LIST/SET/MAP child/key/value.
- Deterministic iterative active/completed DFS, dependency-first emission and typed
  deduplication. One pinned source read transaction; fixed ID, not moving refs.
- Candidate format `daggerml-commit-bundle-v1`, exact JSON fields, lowercase IDs,
  strict canonical base64, no duplicate keys/nonstandard constants/trailing document.
  Retained candidate profile: 32 MiB encoded, 4 MiB per packed record, 16 MiB total
  packed records, 100,000 rows. Constants owned by the transfer module.
- One helper-owned import write transaction validates **every** row even for existing
  keys, checks computed ID/exact bytes, requires earlier typed **bundle** dependencies
  and all-and-only-root reachability. Destination contents cannot replace omitted rows.
- Optional ref is create-or-readable-same-target only under that write lock. Different,
  malformed/dangling/corrupt targets fail; no overwrite/repair/ref inference.
  Prebuilt frozen `ImportResult` counts validated rows, not new objects/attempts.
- Real local transfer story reuses existing `local_add.py`, records two actual distinct
  requests/attempts with result 11, exports pinned history, moves A's head and imports/
  inspects in fresh processes. Source reservation/publication refs and branch-only
  content are absent; transferred paths/code/URI values remain data.

### Documentation consultation

Read the required skill. Built-in Context7 resolve returned quota exceeded; the
skill's authenticated REST resolve/query workflow succeeded using existing shell
configuration without printing/copying the credential. Selected **`/python/cpython`**.
Three queries cover JSON duplicate-key/nonstandard-constant hooks, strict base64,
and subprocess lifetime/timeouts/reaping. Results:
`/tmp/dml-iteration5-doc-{search.json,json.txt,base64.txt,process.txt}`.
Python 3.15-only canonical/padding APIs were deliberately not selected: base64
canonicality uses re-encoding equality with declared Python >=3.8 APIs. No global
configuration/tool install. Existing Black formats only new maintained Python files.

## Implementation and host validation checkpoints

- First focused suite: **27 passed**, exit 0; `/tmp/dml-iteration5-focused1.log`.
- Expanded second/third checkpoints: exits **1**, **78/85 passed and one failed**.
  A test's proposed independent row permutation actually moved a datum behind a
  dependent node. The corrected fixture moves independent leaves before dependents;
  no order validation was waived and this was not a production defect. Logs:
  `/tmp/dml-iteration5-focused{2,3}.log`.
- Full root-source Python coverage checkpoint: **464 passed**, exit **0**,
  **1,163/1,163 statements**, transfer **167/167**, example **109/109**.
  `/tmp/dml-iteration5-coverage1.log`. Later tests add explicit wrapper owner-thread/
  missing-dependency checks and actual configured encoded/per-record bounds; this
  checkpoint is not their final validation.
- Coordinator requested genuine deletion rather than calling wrong-key bytes
  "missing". Explicitly authorized private `tests/c/core_driver.c` `raw-delete`
  extends existing corruption infrastructure, never installed. Wrong-key parent
  test renamed honestly; genuine missing parent, node and composite-only LIST child
  now fail export through real stored missing keys. Native production unchanged.

## Meaningful failure and atomicity evidence

Tests use fresh test-owned repositories and preserve unrelated destination `keep`
records/ref bytes. Late failures introduce a genuinely new earlier object and inspect
its absence after abort; preexisting dependencies are never the rollback oracle.

- Exact all-ten-kind insertion, NaN/infinity/zero byte equality, I64 extrema,
  NFC STRING/canonical URI, LIST duplicates, SET/MAP order, shared/nested/root-only/
  named graphs, ordered parents, poison on invalid/unhashable kind and nonbytes,
  invalid native record and ID-return allocation failure.
- Actual malformed packed header/version/type/length/flags/checksum, float zero/NaN,
  non-NFC text, URI and SET/MAP/name ordering fail native validation. No alternate
  packed codec or cryptographic collision claim.
- Exact typed population and unrelated exclusion, head movement/pin stability,
  repeated deterministic export/re-export, Hypothesis bounded sharing/round trips,
  1,100-deep parent history beyond Python recursion limits. Final generated fixture
  specifically isolates disjoint I64 LIST children from STRING SET children: MAP
  key and value are their only paths, with no alternate scalar bindings.
- Thin child/parent input despite prepopulated B, forward row, duplicate, wrong
  root, late ID/type/packed failure, extra unreachable row and ref conflict abort
  earlier new writes. Corrupt immutable keys are not skipped or repaired; wrong-
  width/dangling destination refs fail without replacement.
- Invalid UTF-8/JSON, duplicate keys, NaN, deep nesting, huge integers, truncated/
  trailing documents, field/type/ID/base64/padding/unused-bit violations fail cleanly
  before opening destination. Messages contain no input payload excerpts. Actual
  configured encoded/per-record overflow plus scaled exact limits/count/packed-total
  boundaries are distinguished; no 100,000-row stress or exact-RSS claim.
- Real **1 MiB-map** import of a **2 MiB** datum fails map-full after earlier new
  insertion. Fresh process/public reads see old state; explicit full retry with
  **8 MiB** map succeeds. No automatic growth.
- Existing private native write fault on third put and consuming storage-commit
  fault abort whole batches, including attempted ref creation. These are real
  LMDB transactions with substituted dependency error codes, not actual disk-fault
  reproductions. Stored-byte mismatch and synthetic traversal cycle are separately
  substituted defensive-path fixtures, not real hash collisions/corrupt-cycle proofs.
- Private process barriers after **three real puts before commit** and after **actual
  successful storage commit before return**. Portable `terminate`, finite barrier/
  wait deadlines, finally kill/reap. Fresh independent process validates every typed
  record and ref: precommit loss leaves old state; postcommit response loss leaves
  complete publication. Same-target reimport succeeds in both cases. Missing
  acknowledgement is never treated as proof of rollback.
- Real-attempt tests prohibit process launch during transfer/inspection and recreate
  test-owned historical scratch sentinels which remain untouched. Export/import/
  inspection never launch copied source, create new occurrences or infer source refs.

Functional process tests use staged maintained sources/current extension and assert
provenance. Host coverage directly measures helpers/example separately; staged and
installed subprocesses are **not coverage-instrumented**. Local termination evidence
is Linux, not SIGKILL/power-loss, Windows/macOS, process-tree, security or all platform
assurance. No recovery/resume/exactly-once claim.

## Bounded negative-oracle probes and mutation gap

Existing tools contain neither `mutmut` nor `cosmic_ray` modules/commands; no bootstrap.
Mull is not Python mutation assurance. Four session-local hand-selected probes in
ignored `build/iteration5-oracles/probe.py` all fail at their intended assertions
(`DID NOT RAISE`), each pytest exit **1**, aggregate harness exit **0**;
`/tmp/dml-iteration5-oracles.log`, repeated with final fixtures in
`/tmp/dml-iteration5-final-property-oracles.log`:

1. Silently substitute preexisting B children for earlier bundle dependencies.
2. Remove computed-ID comparison, with a synthetic wrong public insertion return
   while real correct bytes are stored (not a native hash/collision reproduction).
3. Remove different-ref conflict guard.
4. Commit successful native writes despite a late layer conflict; fresh-reader
   absence oracle rejects the published earlier object.

These are four selected boundary/negative-oracle probes, not a mutation score,
broad framework, independent installed mutation or exhaustive guard assurance.
Other native/byte/dependency checks can independently reject some invalid IDs;
these probes do not claim every guard removal permits invalid publication.

## Installed fresh-process acceptance

Used existing ignored project packaging-tools venv; no bootstrap/global install.
Initial current core/console build and offline pip-less install exit **0**:
`/tmp/dml-iteration5-installed-build.{log,exit}`. Postformat installed smoke exits
**0**, `/tmp/dml-iteration5-installed-smoke.log`. Final source wheel rebuild, offline
force-reinstall only into the new ignored venv, enhanced independent-byte oracle
and smoke also exit **0**: `/tmp/dml-iteration5-installed-final.{log,exit}`.

Commands from `../dml` inside the existing tools shell:

```sh
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration5-packaging/dist .
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration5-packaging/dist python/daggerml-cli
build/iteration2-packaging/bin/python -m venv --without-pip \
  build/iteration5-packaging/installed
build/iteration2-packaging/bin/python -m pip \
  --python build/iteration5-packaging/installed/bin/python install \
  --no-index --no-deps build/iteration5-packaging/dist/*.whl
# Final reinstall additionally uses --force-reinstall.
env -u PYTHONPATH build/iteration2-packaging/bin/python \
  build/iteration5-packaging/installed_smoke.py
```

Session-local harness launches installed exporter, importer and reader from `/tmp`
with source PYTHONPATH unset; verifies module/transfer/extension/console/bundled-native
paths in the fresh install and exact installed transfer bytes. Exporter independently
enumerates all typed edges through ordinary public reads (not transfer's edge helper
or CLI prefixes), saves every source byte and compares exact population with bundle.
A is closed then renamed away before importer; importer receives only bundle/B,
not A or source manifest. Fresh reader compares every independently saved typed ID/
byte, both occurrences/result 11, ordered pre/publication parents and unchanged
sentinels/absent source refs. Reimport and B re-export match. Six existing CLI commands
(ref, head/pinned snapshots, walk, result show, all-parent log) agree exactly between
installed console and bundled native. Maintained full driver separately runs outside
checkout and uses fresh importer/reader. Wheel inventories exclude test/fault controls.

Evidence is CPython **3.13.15 / Linux x86_64**, `cp313-abi3-linux_x86_64` core and
`py3-none-any` console, not earlier declared Python, other platforms, manylinux,
sdist/staged archive, release or installed-process coverage. Runtime/tag declarations
are unchanged. No packages published. Final local SHA256:

- Core: `135c38ee5e3952804251e70f26f857e452037dfc3f9f43a517d9671d470513a9`.
- Console: `f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`.

Coordinator independently reports **50 passing installed checks** in a separate
`/tmp` offline-populated venv using current wheels, without touching `build/check`:
independent BFS typed population/bytes/parents, two real equal-result attempts,
source-offline fresh import/reader, absent source refs/unrelated data, idempotence,
console JSON and prepopulated thin/late-ID/extra/ref-conflict rollback with genuinely
new prefix. This is **coordinator-reported**, not a worker rerun; REVIEW owns its
independent evidence/qualification.

Coordinator also reports **15 changed Markdown documents/280 local targets** and
current whitespace pass, with no runtime finding at that checkpoint. These are
coordinator-reported populations, distinct from the worker's nine-document check.
Independent default validation/acceptance subsequently completed successfully;
the publication checkpoint below supersedes the review pause.

## Final standard validation

Runtime source is frozen. First launch combined background formatting/gate did not
create a check log or start a surviving gate; foreground Black verified unchanged
files, then the fully redirected standard run started correctly.

- `/tmp/dml-iteration5-default1.{log,exit}` exits **0**: **467 Python tests**,
  **1,163/1,163 Python statements**, transfer **167/167**, example **109/109**;
  **seven C executables** under Valgrind, retained C **1681/1681 lines**,
  **132/132 functions**, **1562/1562 outcomes**. Expanded binding and existing
  **141 native CLI Valgrind processes** pass.
- Before review release, self-review strengthened the generated round-trip fixture
  from LIST-only to nested LIST/SET/MAP. Focused **33 passed**, exit **0**,
  `/tmp/dml-iteration5-composite-property.log`; second standard gate started.
- After that gate's Python phase completed (**467 passed**), final assurance refinement
  makes MAP key/value child paths disjoint, isolating LIST and SET traversal. This is
  **test-only**, no runtime/wheel changes. Focused **33 passed** and all four negative
  oracles reject, harness exit **0**; `/tmp/dml-iteration5-final-property-oracles.log`.
  Second gate exits **0** with the same tests/retained coverage/memory population:
  `/tmp/dml-iteration5-default2.{log,exit}`. It is a preceding-fixture checkpoint,
  not final-test-source validation.
- **Final frozen-source standard run exits 0**:
  `/tmp/dml-iteration5-final-default.{log,exit}`. **467 Python tests**,
  **1,163/1,163 Python statements** (transfer **167/167**, example **109/109**),
  **seven C executables** under Valgrind; retained C **1681/1681 lines**,
  **132/132 functions**, **1562/1562 outcomes**. Expanded binding and existing
  **141 native CLI Valgrind processes** pass. Final binding heap/suppression
  counts match the first run below. No further unchanged standard rerun is planned.

No coverage exclusion, source omission, memory suppression or threshold reduction.
Existing exact native/dependency exclusions remain distinct from tested code; no
new marker-free/Mull or production-native/platform guarantee is inferred. First
expanded binding workload has **zero unsuppressed errors/leaks**, exit heap
**500,823 bytes/8,717 blocks**: existing narrowly suppressed CPython runtime
**476,387 bytes/8,657 blocks**, reachable **24,436 bytes/60 blocks**,
**624 suppressed runtime contexts**. This is not a fresh runtime-only/full pair or
no-retained-Python-allocation claim. Unsupported foreign-last-owner abandonment
remains outside supported leak-free finalization evidence. No process-level Valgrind
claim for installed/staged transfer processes.

## Changed implementation slice and review boundary

Relative to `../dml`:

- `python/daggerml/daggerml/{__init__,transfer}.py`, `meson.build`.
- `examples/pinned_transfer.py` (reuses unchanged `local_add.py`).
- `tests/python/test_transfer{,_framing,_process,_example}.py`, private
  `transfer_interruption_parent.py`, existing `binding_memory.py`.
- Private deletion fixture `tests/c/core_driver.c`, no native production changes.
- Owning `docs/spec-next/transfer.md`, Python contract/navigation in
  `docs/spec-next/{python-api,README}.md`.
- Orientation `README.md`, `docs/{architecture,packaging-and-distribution}.md`,
  `python/daggerml/README.md`; assurance catalog `tests/coverage-exclusions.md`.

No native production sources/headers/extension changes, old `docs/spec/`, adapter code, CLI
commands/JSON, encoding/schema/version/runtime declarations, CI/release workflows,
credentials, global environment, unrelated checkout work or later feature work.
Index remains empty; build/install/oracle scratch is ignored and test-owned.
Markdown validation passes **9 worker-owned documents/132 local targets/anchors**
at this checkpoint; whitespace checks pass. New test collection has **99 cases**,
maximum node-ID length **109**, `/tmp/dml-iteration5-collection.log`; explicit short
IDs retain oversized inputs without exporting giant reprs to the environment.
No outstanding functional finding. Worker explicitly releases `build/check` to
coordinator ownership and pauses all runtime/test edits and worker build use for
independent review/default validation. No further standard rerun, implementation
change, staging, commit, push or CI launch before coordinator feedback/acceptance.
The bounded stop line remains; no extra agents or later feature work. The subsequent
explicit acceptance/publication authorization below supersedes the pause, not scope.

## Independent acceptance and publication checkpoint

Coordinator explicitly accepted this bounded implementation after its independent
fresh default `scripts/check.sh -v` exits **0**: **467 Python tests**, **seven C
executables**, Python **1163/1163 statements**, retained C **1681/1681 lines**,
**132/132 functions**, **1562/1562 outcomes**, zero unsuppressed binding errors and
**141 CLI Valgrind processes**. Separate installed **50 checks** pass; wheel
`__init__`, transfer and local bytes match reviewed maintained sources. This is
coordinator-reported evidence, owned by [REVIEW.md](REVIEW.md), not another worker
rerun. Coordinator released `build/check` back to the worker and authorized only
reviewed staging, focused normal commit/push and exact-SHA automatic CI monitoring/
bounded fixes, with diagnosis/regressions reviewed before any follow-up commit.

Inspected/re-read the complete reviewed slice; explicitly staged exactly **19 files**,
**1,672 insertions/8 deletions**. Staged whitespace passes; no unstaged/untracked
implementation work or unrelated content. Full staged diff remains session-local
`/tmp/dml-iteration5-reviewed-staged.diff`. No design notes staged/committed.

Focused commit
[`0ec769b5e85fde6b6581b628fffdf3465c78a098`](https://github.com/micha/dml/commit/0ec769b5e85fde6b6581b628fffdf3465c78a098)
(`Add atomic pinned commit transfer between local repositories`) and normal
`git push origin master` exit **0**. Exact remote `refs/heads/master` matches;
implementation worktree/index are clean. No force push, remote creation, tags,
manual workflow or release/package publication.

Consulted current GitHub CLI documentation through the same privately authenticated
Context7 skill workflow, selected `/websites/cli_github_manual` for exact-commit
run filtering, job/log inspection and `watch --exit-status`. Documentation artifacts
`/tmp/dml-iteration5-gh-doc-{search.json,monitor.txt}`. Existing CLI **2.102.0**;
no bootstrap/configuration changes or credential output.

Automatic [CI run 40556958937](https://github.com/micha/dml/actions/runs/40556958937)
is the sole listed workflow for exact pushed SHA, `push` event, initially queued.
`gh run list --commit <full-sha> --limit 100 --json ...` verifies every listed head
matches; `/tmp/dml-iteration5-pushed-runs.json`. CI was **not yet green** at that
initial checkpoint; monitoring continued, with final run/job/log evidence below.
No failure/fix or manual workflow launch at this checkpoint. Subsequent status:
**five jobs succeeded** (strict Linux, both Linux architectures, Windows AMD64,
macOS x86_64); **macOS arm64 remains queued**, not failed/running. An individual
completed Windows job-log request exits **1** because GitHub withholds logs until
the overall run completes; this is not a Windows test failure or a final missing-log
claim. A finite `timeout 900 gh run watch <id> --exit-status --interval 10` runs in
session-local background with `/tmp/dml-iteration5-ci-watch.{log,exit}`. Final
completion below supersedes this pending checkpoint.

## Final exact-SHA CI and stop

[Run 40556958937](https://github.com/micha/dml/actions/runs/40556958937) completes
**success** for exact SHA
**`0ec769b5e85fde6b6581b628fffdf3465c78a098`**. All **six** jobs complete successfully
on the first published run. macOS arm64 progressed from queued to success without
intervention. The finite `gh run watch --exit-status` exits **0**, not timeout.
Complete run/job JSON and full logs are fetched and inspected after completion;
the earlier pending-run log refusal resolves normally, with no final missing-log gap.
No CI failure, rerun, source fix or follow-up commit was needed.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40556958937/job/122375473266) | Success | 7 | 467 passed; 17.71 s |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40556958937/job/122375472818) | Success | 7 | 467 passed; 16.57 s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40556958937/job/122375473521) | Success | 7 | 463 passed, 4 existing skips; 102.09 s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40556958937/job/122375473155) | Success | 7 | 463 passed, 4 existing skips; 33.15 s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40556958937/job/122375473267) | Success | 7 | 462 passed, 5 existing skips; 36.03 s |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40556958937/job/122375472343) | Success | 7 | 467 passed; 27.43 s |

Existing skips are four `/dev/full` output-device cases on macOS/Windows and the
Unix pipe/SIGPIPE case on Windows. No new skip, exclusion or reduced input. The
completed Windows verbose log explicitly shows all **99 new cases passing**,
including genuine missing keys, nested composite-only property, both actual-commit
process-loss barriers, real map-full/whole retry and the configured large bounds.
Unix CI uses configured Python **3.12**; Windows UCRT64 uses **3.14.9**. This extends
staged functional platform/runtime evidence, not installed-wheel/earliest-declared-
interpreter, process-memory, power-loss, hard-kill/process-tree or security assurance.

Strict Linux remains informational **`scripts/check.sh -c`**, not the local default
percentage/memory gate. It reports Python **1163/1163** statements and retained C
**1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**. Worker and
coordinator default `-v`/installed evidence remain separately qualified above.
Existing exclusions/suppressions, unavailable Python mutation framework/four selected
negative oracles and source-allocation/trust/capture/response-loss limits remain.

Coordinator independently verifies the same exact SHA, all six completed jobs,
full logs/job JSON, sole automatic run list, watch exit **0**, clean implementation
worktree/index and matching remote master. Its confirmed counts/timings agree with
the table. This is coordinator-reported final verification; [REVIEW.md](REVIEW.md)
owns independent evidence/acceptance. Coordinator explicitly instructs the worker
to finalize only this report and stop all runtime/build/commit/push activity; no
design checkpoint commit is requested.

Final `gh run list --commit <full-sha> --limit 100 --json ...` contains exactly this
one completed successful automatic **push** workflow. Exact remote master and local
HEAD match, and implementation worktree/index are clean. Focused publication remains
one **19-file** commit; no postacceptance runtime/test/doc changes. Design notes were
not staged/committed and remain local/uncommitted, preserving coordinator edits.
No manual workflow/release trigger, force push, tag/release/package publication,
new remote, extra agent, global bootstrap, cloud experiment or later feature work.

Session-local evidence: `/tmp/dml-iteration5-final-ci.{json,log}`,
`/tmp/dml-iteration5-final-runs.json`, `/tmp/dml-iteration5-final-remote.txt` and
`/tmp/dml-iteration5-ci-watch.{log,exit}`. Final worker validation passes for
**nine worker-owned Markdown documents/134 local targets/anchors**; whitespace
passes in both checkouts, implementation HEAD remains the pushed exact SHA with
clean worktree/index, and no worker watcher/interruption fixture/probe remains.
No additional build/test/CI rerun or design commit. After successful exact-SHA CI
verification and final coordinator confirmation, all implementation/publication/
monitoring work is **stopped**. Coordinator owns final REVIEW/status/resume
reconciliation.
