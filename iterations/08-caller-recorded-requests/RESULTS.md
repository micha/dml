# Iteration 8 implementation results

Status: **bounded implementation, independent acceptance, focused publication and final
exact-SHA CI are complete and stopped** at **`865bb79`**. All six final CI jobs succeed.
First CI at `509c2f0` finished five successful jobs/Windows cancelled; its exact Windows
failedcase remains uncertain. The accepted follow-up is test-only: runtime/native/as-built/
wheel bytes remain unchanged. No further implementation/build/publication activity.
Worker owns runtime/tests/as-built docs and this report; coordinator owns REVIEW,
COORDINATION and design status. Current GO supersedes historical planning-only statuses
in [HANDOFF](HANDOFF.md), [DESIGN](DESIGN.md) and [EXAMPLE](EXAMPLE.md), not the stop line.
No staging/commit/push until explicit independent coordinator acceptance.

## Preflight and fresh baseline

Existing worker **%215**, verified with `TMUX_PANE`; unqualified tmux display identified
active coordinator %197 instead. `/work` mounted; machine index/admin instructions,
design instructions/discussion and full required implementation contracts/Iteration 7
RESULTS/REVIEW read. Implementation initially clean at
`a8d646379a52878d087d28bc216b7baa4f9ef3db`; design baseline
`31fe1087c838ebddad56f08be860de14bfa94d86`. Coordinator-owned uncommitted design status
changes preserved. Worker exclusively owns **both build/check and build/coverage** until
source freeze and explicit release for independent checks.

Fresh standard baseline completed **before measured edits**, from implementation:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

`/tmp/dml-iteration8-baseline.{log,exit}`, exit **0**: **831 Python** (105.03 seconds),
**seven C executables**, Python **2013/2013 statements**, retained native **1681/1681
lines, 132/132 functions, 1562/1562 branch outcomes**. Binding Valgrind zero unsuppressed
errors/624 existing runtime suppressed contexts; **141 native CLI memory processes** pass.
Baseline/progress communicated via targeted tmux messages to %197. No extra agent/session.

## Actual engineering choices

- Public `local.put_local_request` builds only ordinary Q through its caller transaction;
  exact occurrence/string/ID/consumed binding/input validation, no refs/scratch/commit/dispatch.
  Existing run_step reuses it without changing Q bytes or fresh-Q behavior.
- Public `local.run_request` is imported-Q **first registration**, not retry: same atomic
  pre-dispatch transaction requires current head exactly Cq, exact submission/Q and absent
  local reservation; generates only T, preserves Q and all Cq entries, reserves Q at Cq,
  publishes P/head/attempt ref before unchanged child/executor/finalizer. It additionally
  requires Q binding/input IDs occur in basis C tree values. Exchange never invokes private
  local functions or synthesizes registration refs. Existing run_step/retry remain.
- Explicit `exchange.record_exchange_request` resolves immutable C names, validates consumed
  inputs, bounds Q collision attempts to three, atomically creates Q/Cq plus caller submission
  and A-local reservation refs at Cq. Create-only refs, no existing heads moved. Frozen
  `RecordedRequest` response is prebuilt before commit; no token/workspace/process authority.
- `ExchangeSpec.request` optional ObjectId (default None) selects exact caller Q/Cq;
  original fresh-Q-in-B mode preserved. **Required nullable request field in v2 job/handle**
  framing is an engineering refinement explicitly accepted by coordinator: JSON null or
  lowercase Q content ID; no v1 migration/legacy mode. Other receipts remain v1. Loading
  still never dispatches. Exact spellings/fields belong to new as-built
  [caller-request contract](../../../dml/docs/spec-next/caller-requests.md).
- Shared mode-specific initial-history validator extends **both synchronous F and async
  P/U/F**. Caller mode adds only T to expected Cq; Q derives from expected validated
  submission, not fresh-name scans. Original mode still requires both fresh Q/T. Exact
  T->Q association, original fields, ordered parents, outcome/evidence/cleanup restrictions
  remain. Bootstrap no packet/T, but caller already knows Q. No request-only packet phase.
- A submission/Q refs stay at Cq during return. Preexisting A reservation is not a copied
  B ref; other worker refs stay absent. Complete offline packets + independent expected
  suffice. Unknown/working/done, publication versus final success and application-owned
  live process versus saved observation handle remain unchanged.
- Maintained `examples/caller_requests.py` uses existing finite declared cooperative child
  gates, three jobs (two matching plus nonzero after U), genuine prior Q/T/publication in C,
  composite-only retained descendants and a never-started Q. Fresh clients can exit while
  finite application retains/reaps each fixed worker. A/B offline packet return; receipt-loss
  retrieval; no process-tree/sole-owner-loss lifetime promise.

Context7 skill loaded; `/python/cpython` consulted for public subprocess wait/poll,
timeout, destructor/ownership and reaping semantics; `/websites/pip_pypa_io_en_stable`
confirmed offline `--python` installation into a pip-less environment. Existing APIs remain Python >=3.8
compatible in production. No secrets/global tooling/native/CLI grammar/old-spec/runtime/
version/adapter/workflow/network/cloud/release/package-publication or later-feature change.

## Worker checkpoints and meaningful assurance

- Original local/exchange regression **212 passed**, exit 0:
  `/tmp/dml-iteration8-regression.{log,exit}`.
- First 54 new request cases: **47 pass/7 fresh-reader harness failures** because test's
  `monkeypatch.undo()` removed staged PYTHONPATH. Corrected private harness, no production
  bug/failure claim. `/tmp/dml-iteration8-requests1.{log,exit}`.
- Expanded **220 passed/1 test failure**: reused concurrent observer test ran after helper
  left head P but expected F. Explicitly restored real work/publication refs before concurrent
  readers; private test sequencing fix. `/tmp/dml-iteration8-focused2.{log,exit}`.
- Host coverage checkpoint **639 passed**, local **394/394**, maintained caller application
  **164/164**, exchange **631/632** (one meaningful fresh-attempt discovery error remaining,
  then new test added; not excluded). `/tmp/dml-iteration8-coverage1.{log,exit}`.
- Accidental whole-file Black formatting expanded local diff. Coordinator requested focused
  restoration; unchanged binding/context/executor/finalizer/run_step/retry/import formatting
  restored surgically, changed preparation/new blocks retained. No runtime semantic change
  from this formatting correction.

### Fault and identity distinctions

- Actual successful genuinely new **A Q/Cq** puts/readback precede late second-ref,
  dangling keys/native create, real map-full, substituted native consuming-commit EIO and
  owned-response allocation failure. Whole data-file equality preserves raw ref corruption;
  fresh independent public readers verify old bytes and entire new-batch absence.
- Real map-full here is a late fixture's additional native oversized put **after** successful
  Q/Cq (1 MiB configured A / 2 MiB put) or T/P (default 64 MiB B / 65 MiB put).
  It is a genuine LMDB capacity failure, but the added pressure operation is private test
  workload, not a naturally oversized Q. No automatic growth or retry.
- Successful new **B T/P** puts/readback precede dangling/raw reservation native-create,
  late ref/map-full/consuming-commit failure, with computational spawn prohibited. Q/Cq
  stays imported; no partial T/ref/head. Raw malformed-ref **late** tests hide only its early
  read via a private NotFound substitution; native create still sees actual malformed key.
  This is explicitly substituted early behavior, not a naturally concurrent raw writer.
  Same/different reservation and ordinary malformed early reads reject without new writes.
- Recording-only actual processes pause after new Q/Cq puts before storage commit versus
  after successful actual commit before response. Reaped before fresh inspection; no child
  process. Retained submission repeat rejects, never automatic new-Q creation.
- Typed-complete P parented by **expected Cq**, with **expected Q retained in its tree**,
  T referencing another matching Q via complete typed edges: sync F and async P/U/F all
  reject specifically initial association. Distinct full valid Q2/Cq2 packet swaps (first
  validated as real Q2 history), receipt token/base rewritten to Q1 expected, replacement
  Q content under same spelling and missing Q also reject before whole-file unchanged A.
- Independent breadth-first public typed population/every-packed-byte oracles cover every
  parent, DAG root/binding, nested node and composite-only descendant; not transfer traversal
  or CLI prefixes. Ordinary CLI confirms selected IDs/ordered parents but is not closure oracle.
- Both return modes retain actual-A successful-new-put tracking before late conflicts,
  consuming-commit and genuine 1 MiB map / 2 MiB result failure. Fresh full-state readers
  prove rollback; explicit 8 MiB whole receive succeeds, never another computation.
  Actual pre/post-A-commit loss retains no batch versus complete import despite no response.
- Real finite computational gates expose P/U and nonzero-after-U. Safe worker loss only
  pre-child-spawn or after actual child reaping/cleanup/final commit; no live child sacrificed.
  Separate outer-spawn bootstrap/unknown versus child-spawn after P recorded failure.
  Validation cleanup errors prohibit any A write. Request survives later file/export errors.
- Genuine unchanged production **4 MiB + 1 byte result datum** leaves successful recorded F
  in B after real child reaping/cleanup, then synchronous/observation export rejects real
  per-record transfer limit; no false done packet, retry or fabricated Q failure.

Host statement coverage is not every Python branch or instrumented installed-child coverage.
Existing exact exclusions/native memory/runtime suppressions and unsupported foreign-thread
last-owner abandonment remain qualified; no new exclusions/omissions/weaker threshold.
Consuming-commit EIO is dependency substitution consuming real native handle, not physical
power/device failure. Finite process barriers/watchdogs are not arbitrary hard-owner-loss,
portable process-tree cleanup, sandbox/authentication/scientific/full-capture assurance.

## Offline installed evidence

Using existing project-local packaging tools, no bootstrap/global install:

```sh
# inside existing nix develop ../dml-build-tools shell, from implementation
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration8-packaging/dist .
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration8-packaging/dist python/daggerml-cli
build/iteration2-packaging/bin/python -m venv --without-pip \
  build/iteration8-packaging/installed
build/iteration2-packaging/bin/python -m pip \
  --python build/iteration8-packaging/installed/bin/python install \
  --no-index --no-deps build/iteration8-packaging/dist/*.whl
# from /tmp, source PYTHONPATH unset
env -u PYTHONPATH /work/repos/micha/dml/build/iteration8-packaging/installed/bin/python \
  /work/repos/micha/dml/build/iteration8-packaging/installed_probe.py
```

Build/install **exit 0**, `/tmp/dml-iteration8-installed-build.{log,exit}`. Initial installed
probe **522 parent checks** pass. Added preserved prior A operational-ref checks; final
private installed workflow **528 parent check calls**, plus **12 fresh observers, nine
receivers, nine typed readers** and actual computational-child installed provenance assertions,
exit **0**. `/tmp/dml-iteration8-installed-probe-final.log` and
`/tmp/dml-iteration8-installed-final.exit`; retained story
`/tmp/dml-iteration8-installed-story-ri5dadzk`. All finite process owners reap; no running
object discarded. Main/sentinel/prior and current request/attempt refs preserved; current
A Q reservations explicitly remain Cq, not evidence of transferred refs.

- Installed package/core/local/transfer/exchange/fixed-worker/console/native provenance
  asserted under isolated prefix, clients/workers run from `/tmp`, PYTHONPATH absent.
  Captured child checks installed module/core/runtime provenance and records stdout evidence.
- Q-before-workspace/two refs, two matching submissions on the **same C**, exact caller Q/T
  P/U/F, equal result 11/distinct occurrences, nonzero-after-U failure evidence and separate
  cleanup; genuine prior Q/T/publication plus composite-only descendants in C.
- A offline during execution; B offline before packet-only fresh receivers with independent
  expected file. Independent all-parent public breadth-first typed-byte oracle at B/packet/A
  and fresh reader, not transfer traversal. Historical scratch sentinel stays inert.
- F after original receipt loss, explicit same-ref repeat, P-to-F conflict, unstarted Q and
  valid matching Q2 packet rejection even after token/base rewrite, whole-file unchanged A.
  Existing installed console log agrees with selected IDs/every ordered parent.
- Byte-identically copied maintained caller application plus local_add/local_slow_add execute
  outside checkout with source PYTHONPATH unset. Final formatted current example also passes:
  `/tmp/dml-iteration8-installed-example-current.{log,exit}`, exit **0**; retained
  `/tmp/dml-iteration8-installed-example-final/story-current`.

Current wheels:

- `../dml/build/iteration8-packaging/dist/daggerml-0.1.0-cp313-abi3-linux_x86_64.whl`,
  SHA256 **`4886d617212bb1522137c6b2ad4011b7bdb5ee4011910996e6a9de1288213585`**.
- `../dml/build/iteration8-packaging/dist/daggerml_cli-0.1.0-py3-none-any.whl`,
  SHA256 **`f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`**.

All **five core Python modules plus console forwarding** match maintained source bytes;
no tests/fault controls packaged. Current dirty-source wheels, not committed VCS sdist
or release evidence. Local CPython **3.13.15/Linux x86_64**, cp313-abi3 not earlier declared
runtimes/other platforms/manylinux evidence; declarations/tags unchanged. Installed functional
provenance is not instrumented process coverage/memory/security/full capture assurance.

Coordinator independently initially reported **295 installed checks**, then expanded its
separate probe to **302 checks**, exit **0**, including public synchronous copied-Q
continuation and complete expected-Cq wrong-association F rejection. Its pip-less environment
is `/tmp/dml-iteration8-review-install.3M57gd`, outside checkout/PYTHONPATH unset. Coordinator
also confirms five runtime wheel/source/installed module bytes equal and core/console wheel
hashes match above. Its initial harness expected only ExchangeError for foreign-Cq; corrected
to documented native DmlError when expected base is absent. Independent wrong-Q association/
typed bytes/offline/ref/lifetime evidence belongs to REVIEW, not a worker rerun or final
acceptance. Coordinator acknowledged freeze/release, owns **both shared builds** and is
running fresh independent default validation. Worker source/build freeze remains in force.

## Mutation gap and selected negative oracles

Fresh tools-shell inspection: no `mutmut`/`cosmic_ray` command or module, no bootstrap.
Mull supplies no Python mutation assurance. Private ignored
`../dml/build/iteration8-oracles/probe.py` uses in-memory substitutions only;
`/tmp/dml-iteration8-oracles.{log,exit}` aggregate **exit 0**: **eight selected probes**,
each pytest **exit 1 / one intended test failure**, not setup/collection errors:

1. Ignore exact initial T->Q association: expected-Cq/retained-Q typed-complete sync oracle.
2. Replace caller dispatch with fresh-Q mode: exact caller Q computational-child-launch case.
3. Publish A before selected validation: wrong-Q whole-file no-write oracle.
4. Launch before pre-dispatch commit: no-spawn late registration fixture.
5. Move A Q reservation to received F: explicit unchanged-Cq ref oracle.
6. Register request ref on pure transfer import: copied-unregistered Q oracle.
7. Retarget selected export to newer head: genuine coherent snapshot/pin oracle.
8. Invoke run_request on receipt: explicit no-registration/no-execution reception monitor.

No maintained source changed by probes. Selected negative-oracle scope, not a framework
score, broad mutation/installed-branch guarantee or equivalent-mutant claim.

## Standard validation and source-freeze gate

Intermediate full standard **1078 tests pass** (153.54 seconds), then **exit 2** at Python
coverage gate: maintained example had changed during that intermediate run, making its
line map stale (**23 missed**, not hidden/excluded). `/tmp/dml-iteration8-default1.{log,exit}`.
This is not green final evidence. Stable-runtime/example rerun **exit 0**:
`/tmp/dml-iteration8-default2.{log,exit}`, **1078 Python** (153.59 seconds), **seven C**,
Python **2299/2299 statements** (exchange **634/634**, local **394/394**, caller example
**168/168**), native retained **1681/1681 lines,132/132 functions,1562/1562 outcomes**.
Binding memory zero unsuppressed errors: exit heap **500823 bytes/8717 blocks**, existing
runtime suppressions **476387 bytes/8657 blocks /624 contexts**, reachable **24436 bytes/60
blocks**; **141 CLI memory processes** pass. No new exclusion/suppression/threshold change.

After that run, formatted final caller example and added three test-only early raw-reservation
(no new T) and attempt/publication tree-collision cases, tidied test imports. Final fresh
standard3 on **stable runtime/tests/example** exits **0**:
`/tmp/dml-iteration8-default3.{log,exit}`: **1081 Python tests** (153.95 seconds), **seven C
executables**, Python **2299/2299 statements**, exchange **634/634**, local **394/394**, caller
application **168/168**; unchanged native retained **1681/1681 lines,132/132 functions,
1562/1562 outcomes**. Binding heap/suppressions/zero errors and **141 CLI memory processes**
match the preceding run exactly. No source changes during this final run, no omission,
new exclusion/suppression, weaker threshold or reduced boundary input.

Final collection `/tmp/dml-iteration8-collection.log`: **1081 total /250 new cases**,
maximum new full ID **133**, short **88**; full-suite maximum **11821** from unchanged
preexisting CLI giant-JSON parameters. Original tests remain enabled. No new skipped tests
or oldest-runtime/cross-platform installed claim.

Current changed slice is **22 implementation files**:

- `python/daggerml/daggerml/{local,exchange}.py`;
- new `examples/caller_requests.py`;
- new `tests/python/test_caller_request_{example,history,process}.py`,
  `test_caller_requests.py`, `request_interruption_parent.py`;
- existing test-only `exchange_interruption_parent.py`, `progress_interruption_parent.py`,
  `test_exchange_process.py` (nullable Q expectation/readback/real postcommit barrier support);
- new owning `docs/spec-next/caller-requests.md`; reference/navigation updates in
  `docs/spec-next/{README,local-execution,repository-execution,asynchronous-execution,python-api}.md`,
  `README.md`, `docs/{architecture,packaging-and-distribution}.md`, `python/daggerml/README.md`
  and `tests/coverage-exclusions.md` (no new exclusions).

Native/core/transfer/fixed-worker/CLI/old-spec/version/runtime/adapter/workflows unchanged.
Index empty. Worker Black check passes **seven formatted new/changed Python files**;
unchanged local.py functions retain original style rather than broad reformatting.
Current Markdown links/anchors and whitespace in both repositories pass; final counts
will be recorded after report completion. Coordinator design work preserved.

Final Markdown validation passes **17 changed documents /427 local links/anchors** across
both checkouts; `git diff --check` passes in both, index empty. Five runtime wheel modules
and console bytes still equal maintained source; final installed example/child copies equal
maintained bytes. Runtime/coverage process checks are finished, retained finite workers/clients
reaped; scratch/evidence remains test-owned/ignored. Source hash manifest covers exactly the
22 implementation files at `../dml/build/iteration8-packaging/source-freeze.json`.

Worker now **freezes runtime/tests/as-built source and all shared build use** and explicitly
**releases BOTH build/check and build/coverage to coordinator** for independent review and
fresh default validation. No overlapping reconfiguration/wipes/edits; any needed source/build
resumption waits for returned ownership. Report-only updates may record review evidence.
No stage/commit/push before explicit acceptance. Focused publication and all final exact-SHA
CI success remain later gates; no extra workers, design commit/push, release/tag/package
publication, cloud/global tooling, recovery service or later feature turn.

## Independent acceptance and focused publication

Coordinator explicitly accepts the bounded **22-file** slice with no outstanding finding;
[REVIEW.md](REVIEW.md) owns independent qualification. Fresh independent
`/tmp/dml-iteration8-coordinator-check.{log,exit}` exits **0**: **1081 Python** (152.13
seconds), **seven C**, Python **2299/2299** (local394/exchange634/application168), native
retained **1681 lines/132 functions/1562 outcomes**, zero unsuppressed binding errors/
unchanged existing624 runtime contexts/heaps and **141 CLI memory processes**. Separate
installed **302 checks**, 22 frozen hashes, five core+console wheel/source/installed
comparisons, **17 Markdown/427 targets** and whitespace pass. Coordinator returns **both
builds** and explicitly authorizes focused publication. This is coordinator-reported
independent evidence, not a worker rerun.

Worker verifies existing **master** and **origin https://github.com/micha/dml.git**, all
22 source-freeze hashes unchanged, index initially empty and no unrelated implementation
work. Stages **only those 22 files**, reads complete **3262-line** staged diff,
`/tmp/dml-iteration8-reviewed-staged.diff`; staged whitespace passes. Slice: **2673
insertions/67 deletions**. No design notes or ignored install/probe/scratch staged.
An unpublished commit message had literal newline escapes; amended only its message to
proper line breaks **before push**, with no code/tree change and no published rewrite.

Final focused commit
[`509c2f0921e4251da8b2b46f048e540c21b15ad4`](https://github.com/micha/dml/commit/509c2f0921e4251da8b2b46f048e540c21b15ad4)
(`Record caller requests before local repository execution`) and normal `git push origin
master` exit **0**. Implementation tree/index clean; exact remote master matches. No
force push/new remote/tag/release/package publication/design commit or postreview source change.

Context7 `/websites/cli_github_manual` consulted for current exact-commit run filtering,
run/job/log inspection and watch exit semantics. Existing gh **2.102.0**, no global tooling,
configuration/bootstrap or secret output. Exact-SHA run list reports sole automatic **push**
[CI run 40621755388](https://github.com/micha/dml/actions/runs/40621755388), matching final
head SHA above, initially queued/in progress. No manual workflow triggered. Full SHA/run/
status/clean remote reported to coordinator %197.

Finite `timeout 900 gh run watch 40621755388 --repo micha/dml --exit-status --interval 10`
is monitoring; `/tmp/dml-iteration8-ci-watch.{log,exit}`. Final verification remains
pending **all six exact-SHA jobs successful**; failures require diagnosis/proposed focused
fix and coordinator review/appropriate validation before another push. No speculative
source/test edits, build restarts or later turn. Final CI evidence will follow.

## First CI interruption and bounded test-only follow-up

Initial exact-SHA `509c2f0` [run 40621755388](https://github.com/micha/dml/actions/runs/40621755388)
finished **cancelled**: both Linux/macOS architectures and strict Linux **success**, Windows
**cancelled**. This is **not accepted final green CI**. Finite watch exits **1**, not a green
watch. No production defect is established from a missing/cancelled outcome.

`gh run view --job --log` initially refused in-progress logs. Direct read-only REST job-log
retrieval unexpectedly succeeded; captured **660194494 bytes /6085327 lines** at
`/tmp/dml-iteration8-windows-api.log`, preserved. It begins **midway through a huge physical
`data.mdb` bytes assertion diff**, with repeated zero padding. Completed gh log retrieval
exited **1/EOF** after a partial **24383813-byte** capture, preserved at
`/tmp/dml-iteration8-windows-final.{log,err}`. Bounded streaming scans find no retained test
headers/FAILED lines; a **262144-byte Range request starting at byte zero** also begins in
the same diff. These capped/partial logs do **not** establish the exact Windows failed case.
No huge byte payload is copied into this report. Coordinator independently confirms the
lost-header limitation. Successful-job logs and run JSON are preserved separately.

**Dependency-supported inference:** new
`test_record_late_q_cq_puts_whole_abort[map-full]` snapshots default 64 MiB layout, opens A
with 1 MiB map, then compares entire raw file immediately after abort. Vendored LMDB
`mdb_env_map` (`subprojects/lmdb-LMDB_0.9.35/libraries/liblmdb/mdb.c`, Windows block around
4067–4090) uses `SetEndOfFile` to set configured map extent **during open**. Unix non-WRITEMAP
mapping does not truncate to that extent. Different physical padding/extent after reopen
can therefore fail file equality even with complete logical rollback; verbose pytest can
then expand tens of MiB into enormous diffs. This is a confirmed fixture portability defect
under a matching local dependency-layout model, **not proof that it was the exact cancelled
Windows case**. Native/runtime source and workflow are unchanged.

### Demonstrated before/after and proposed patch

Private `build/iteration8-oracles/windows_extent.py` models only that open-time extent effect
on real Linux/native repositories/maps; no production hooks or alternate codec. Original
exact fixture fails **exit 1 /one intended failure**, bounded with `--assert=plain`:
`/tmp/dml-iteration8-extent-before.{log,exit}` (**3893 bytes**). Enhanced diagnostic run
`/tmp/dml-iteration8-extent-logical-before.{log,exit}` prints **before67108864/after1048576**
physical lengths, then independently verifies **all fresh typed old bytes/new-batch absence
and old refs pass**, before retaining the original physical-comparison failure. This
separates layout from research-state rollback rather than accepting partial records.
Same private model after correction: **one passed**, exit **0**, 0.35 seconds,
`/tmp/dml-iteration8-extent-after.{log,exit}`.

Only `tests/python/test_caller_requests.py` is modified locally:

- For the small-map recording case, reopen/close with the same original default map **before
  full exact-byte comparison**; no transaction/research-state writes. This restores comparable
  physical layout, not refs or immutable data. Successful genuinely new actual-A Q/Cq puts,
  all old typed bytes, entire batch absence, raw malformed refs, heads and real 2 MiB pressure
  assertions remain unchanged.
- Private `assert_file_unchanged` assigns **exact `actual == before`** to a boolean before
  asserting. Failure text is bounded lengths/SHA256 summary; hashes are **diagnostics only**,
  never the equality criterion. Equal input passes; a changed **last raw byte** and a changed
  extent fail, with message **under512 characters**. No subset/prefix/normalization/hash-only
  replacement or reduced boundary input.
- A maintained dependency-layout emulation regression exercises the real map-full fixture.
  Coordinator identified redundant truncation of a live Windows mapped section as a potential
  portability issue; emulation now touches the file **only when stat().st_size differs from
  requested extent**. Actual Windows already set it, so exercises native behavior without
  redundant truncation. No platform skip or runtime/native fault hook.

Initial focused caller suite: **254 passed**, exit0, 43.40 seconds;
`/tmp/dml-iteration8-ci-fix-focused.{log,exit}`. The first standard loaded the **preguard**
fixture; it passes **1085 Python/seven C**, Python **2299/2299**, unchanged retained/native/
memory gates, but is labelled preguard rather than final validation:
`/tmp/dml-iteration8-ci-fix-default.{log,exit}`.

After guard adjustment, focused **254 passed**, exit0, 43.32 seconds:
`/tmp/dml-iteration8-ci-fix-focused-postguard.{log,exit}`. Fresh final **stable postguard**
standard exits **0**, `/tmp/dml-iteration8-ci-fix-default-postguard.{log,exit}`:
**1085 Python tests** (151.37 seconds), **seven C**, Python **2299/2299 statements**
(local394/exchange634/application168), native **1681/1681 lines,132/132 functions,
1562/1562 outcomes**, binding zero unsuppressed errors/unchanged500823-byte heap/624 runtime
contexts and **141 CLI memory processes**. No source changes during this final run.
Final collection **1085 total/254 new**, maximum new fullID **133**, short **88**, existing
whole-suite maximum **11821** unchanged; `/tmp/dml-iteration8-ci-fix-collection.log`.

Black and whitespace pass, one-file **72 insertions/one deletion** proposed patch retained
at `/tmp/dml-iteration8-ci-proposed-postguard.diff`. Other **21** initial frozen file hashes
and all five runtime wheel/source bytes are unchanged; no production/wheel rebuild needed
or claimed. The single modified test file's final hash is saved in
`../dml/build/iteration8-packaging/ci-fix-source-freeze.json`; implementation index empty.
Worker now **freezes that test file and all other implementation source/build use**, and
explicitly **releases BOTH build/check and build/coverage** to coordinator for independent
postfix targeted validation/review. No fix staging/commit/push until explicit focused
acceptance. No exclusions, blanket skips, native/workflow/production change, gate weakening
or later turn. Exact original Windows failedcase remains the qualified inference above.

## Focused CI follow-up acceptance and publication

Coordinator independently runs the final guarded **254-test** caller suite: **exit0**,43.13
seconds, `/tmp/dml-iteration8-coordinator-postfix.{log,exit}`. Focused one-file **+72/-1**
patch accepted with no outstanding finding, preserved exact-byte/new-put/raw/full typed
oracles and unchanged original21/fix1 hashes. Coordinator verifies worker stable **1085/
seven C** plus unchanged gates, records exact-Windows-case uncertainty in REVIEW/COORDINATION,
returns **both builds** and explicitly authorizes only this focused test commit/push/CI.
No production/wheel rebuild or new install evidence is needed for a test-only change.

Worker verifies original21 and accepted fix1 hashes, existing master/origin and empty index;
stages **only `tests/python/test_caller_requests.py`**, reads the complete staged diff
`/tmp/dml-iteration8-ci-fix-staged.diff`, validates staged whitespace and absent unrelated
unstaged implementation work. Focused commit
[`865bb7933616133acf10d9b14ca0f5fe711c5850`](https://github.com/micha/dml/commit/865bb7933616133acf10d9b14ca0f5fe711c5850)
(`Keep rollback byte checks comparable across map layouts`) and normal push exit **0**.
Implementation tree/index clean; exact remote master matches. One file **72 insertions/one
deletion**; no runtime/native/workflow/skip/gate change, design notes or scratch included.

Initial exact-SHA run list empty during normal push-trigger delay; subsequent list shows
sole automatic **push** [CI run 40624753242](https://github.com/micha/dml/actions/runs/40624753242),
exact head SHA `865bb7933616133acf10d9b14ca0f5fe711c5850`, in progress. SHA/run/status/clean
remote reported to %197. No manual dispatch/rerun/release workflow. Finite **900-second**
watch with `--exit-status --interval10` runs; `/tmp/dml-iteration8-postfix-ci-watch.{log,exit}`.
Final acceptance delivery still requires **all six final exact-SHA jobs successful**.
Any further proposed fix needs focused review/validation before another push; no speculative
source edits, production/native expansion, extra workers, release/tag/package publication,
design commit/push, cloud/global tooling or later turn. Final exact-SHA evidence follows.

## Final exact-SHA verification and stop

Automatic [CI run 40624753242](https://github.com/micha/dml/actions/runs/40624753242) finishes
**success** for exact published SHA **`865bb7933616133acf10d9b14ca0f5fe711c5850`**. All **six
jobs** complete successfully after the focused test-only follow-up. Worker finite watch
exits **0**, not timeout. Full final run/job JSON, complete logs and exact-commit workflow
list are fetched and checked: sole automatic **push** CI, exact head SHA, six completed
successful jobs. Implementation checkout/index clean; exact remote master matches.
Coordinator independently confirms its own finite watch exit0/full logs/job JSON/workflow
list/clean remote, accepts the completed turn and directs only this report finalization
then stop. This is final acceptance, not another implementation authorization.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889381) | Success | 7 | 1085 passed;69.69 s |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889478) | Success | 7 | 1085 passed;100.42 s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889534) | Success | 7 | 1081 passed,4 existing skips;371.11 s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889434) | Success | 7 | 1081 passed,4 existing skips;117.16 s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889356) | Success | 7 | 1080 passed,5 existing skips;176.26 s |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40624753242/job/122606889247) | Success | 7 | 1085 passed;77.04 s;Python2299/2299 |

Existing skips cover absent `/dev/full` and the Windows Unix closed-pipe fixture; no new
skip, exclusion, source omission, reduced boundary input, memory suppression or weaker
gate. Strict CI is informational **scripts/check.sh -c**, not worker/coordinator default
memory **-v**. Windows uses existing UCRT64 Python **3.14.9**, pytest9.1.1; Unix uses the
unchanged Python3.12 selection. These are staged platform/runtime functional checks, not
older declared runtimes/other-platform installed wheels, installed-process instrumentation/
memory/security or full-environment capture proof.

Final Windows verbose logs explicitly show **PASS** for the inferred small-map recording
case, all three exact-byte compact-comparison cases and the guarded dependency-layout
regression. This confirms current portability behavior; it does **not** recover the missing
original Windows failure header. The first cancelled run's capped/partial huge bytes-diff
logs and dependency-supported inference remain qualified above, not reclassified as a
confirmed exact-case diagnosis or erased. No runtime/native/workflow change or further
fix after the accepted one-file patch was needed.

Final evidence: `/tmp/dml-iteration8-final-ci.{json,log,err}`,
`/tmp/dml-iteration8-final-ci-summary.log` (bounded ANSI-sanitized summary),
`/tmp/dml-iteration8-final-runs.json`, `/tmp/dml-iteration8-postfix-ci-watch.{log,exit}`,
initial/fix staged diffs, source-freeze manifests, first-run successful-job logs and the
preserved capped Windows logs. During final monitoring, ordinary gh log retrieval waited
for complete run; a bounded REST attempt refused terminal escapes. Complete final `gh
run view --log` then succeeds, with no raw ANSI/huge physical bytes displayed. No credential
values, diagnostic payloads or ignored scratch are committed.

Publication is **two focused implementation commits**: initial accepted **22-file/+2673/-67**
`509c2f0`, followed by accepted **one-test-file/+72/-1** `865bb79`. Unique changed surface
remains 22 files. Source/runtime/assertion/capture/typed-validation, prior precise exclusions/
runtime suppressions, unsupported finalizer abandonment, mutation-tool gap/eight selected
negative oracles, installed-versus-host coverage, genuine versus substituted faults,
process/unknown/publication/cleanup/acknowledgement and full-history/profile limits remain
explicit. No global single-dispatch/exactly-once/recovery, portable detached ownership,
process-tree cleanup, power-loss, authentication/sandbox or scientific-validity guarantee.

RESULTS is finalized. **Work is complete and stopped.** No further implementation, source
edits, builds/tests, staging/commit/push, CI polling/reruns, design commit/push, extra worker,
force push/new remote, release/tag/package publication, cloud/global tooling or later turn.
Coordinator owns final REVIEW/COORDINATION/design status reconciliation.
