# Iteration 8 coordinator review

Status: bounded implementation **independently accepted**, focused publication and final
exact-SHA CI complete through `865bb79`, all six jobs successful. Turn complete and stopped.
[RESULTS.md](RESULTS.md) owns worker evidence;
[COORDINATION.md](COORDINATION.md) owns assignment/shared-build gates.

## Source review and feedback

Reviewed bounded public local request-only builder/imported-Q first registration, explicit
atomic A recording and shared exact-Q selection through both exchange return paths.
A creates Q/Cq and two create-only refs separately from launch. B atomically registers
exact imported Q at Cq, creates only T/P and closes handles before existing execution.
The existing runner/publication/finalization is preserved; import/inspection/receive
neither synthesizes operational refs nor dispatches. Original fresh-Q-in-B mode remains.

Strict v2 job/handle framing with required nullable request is an accepted engineering
refinement, not pre-1.0 migration machinery. Initial validation preserves exact Cq plus
only fresh T and validates T-to-exact-Q association, shared by sync F and async P/U/F.
Expected Cq/Q is caller-owned; transport tokens are correlation, not authentication.
Bootstrap has no T/packet while Q is already known. Unknown/failure, provisional publication,
retrieved final computation/separate cleanup, A reception and live-worker reaping remain
separate. Caller heads and submission/request refs are not advanced by reception.

Early feedback requested typed-complete expected-Cq/T-to-another-matching-Q association
cases, separately from foreign-Cq/missing-base rejection, imported unregistered retry rejection
and late successful-new-T/P reservation failure. Worker added these regressions and qualified
substituted early raw-ref reads. Coordinator requested reducing unrelated whole-file formatting;
worker restored unchanged local implementation spelling. No outstanding functional finding
identified so far; final default review gate remains pending.

## Independent installed evidence

A separate pip-less `/tmp/dml-iteration8-review-install.3M57gd` environment consumes current
worker-built core/console wheels offline with existing local packaging tools. Context7
`/websites/pip_pypa_io_en_stable` confirmed offline `--python` install semantics.
`/tmp/dml-iteration8-coordinator-probe.py` runs outside checkout with PYTHONPATH unset,
passing **302 independent checks**, exit **0**; corresponding `.log`/`.exit` preserve evidence.

- Installed package/native core/local/transfer/exchange/fixed-worker provenance; captured
  computational child independently asserts installed package/local/core provenance.
- Explicit Q recording before any worker, two exact matching submissions from the same C
  with distinct Q IDs, atomic two-ref targets, unstarted Q and unchanged main/sentinel.
  Plain transferred Cq has no operational reservation and existing retry rejects it.
- Finite application retains/reaps real fixed workers; fresh observer/receiver clients exit.
  Cooperative barriers expose P/U before child exit. Same exact Q/T across P/U/F, distinct
  attempts/equal result 11, nonzero-after-U failure retains evidence/separate cleanup.
- A offline during work; complete copied packets received with B offline and independent
  expected. Main independently advanced/preserved, all A request refs unchanged at Cq,
  no copied B working/attempt refs. F retrieved after receipt removal; same-target receive
  is repeatable, P-to-F ref advance conflicts.
- Independent public breadth-first all-parent typed object populations/every packed byte
  at B/packet/A, including composite-only children and genuine prior full Q/T history in
  later C. No transfer private traversal or CLI prefixes used as closure oracle. Installed
  console history agrees on selected IDs.
- Matching-computation Q2 packet swaps with rewritten token/base claims reject before A
  writes. Typed-complete expected-Cq P retaining exact expected Q but T referencing Q2 also
  rejects; whole A data-file equality is checked.
- Public synchronous continuation explicitly attempts copied Q in another fresh B (allowed
  local-only guard, not automatic/global replay), preserving Q and producing fresh T/equal
  result. Offline synchronous return/repeat passes; complete expected-Cq wrong-T-association
  F rejects before A writes.

Initial coordinator harness incorrectly expected only ExchangeError on foreign-Cq rejection;
updated it to allow documented native DmlError for missing expected base. The rejection
occurred correctly; no production defect was found. Local installed evidence is CPython
3.13.15/Linux x86_64, not earlier runtime/other platform/install-process coverage/memory,
security, exactly-once or full-environment assurance.

Final comparison verifies all **22 frozen implementation file hashes**, all five core wheel/
maintained source/installed module bytes and console forwarding bytes. Core wheel SHA256:
`4886d617212bb1522137c6b2ad4011b7bdb5ee4011910996e6a9de1288213585`; console:
`f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`.

## Independent default gate and acceptance

After explicit worker source freeze and release of **both `build/check` and `build/coverage`**,
coordinator ran from implementation:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Fresh `/tmp/dml-iteration8-coordinator-check.{log,exit}` exits **0**:

- **1081 Python tests** pass in 152.13 seconds; **seven C executables** pass.
- Python **2299/2299 statements**: local **394/394**, exchange **634/634**, maintained
  caller application **168/168**, with unchanged source gate.
- Retained native **1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**.
- Binding Valgrind zero unsuppressed errors, existing **624 runtime suppressed contexts**.
  Exit heap 500,823 bytes/8,717 blocks: 476,387 bytes/8,657 blocks suppressed,
  24,436 bytes/60 blocks reachable. **141 native CLI Valgrind processes** pass.
- No new exclusion, suppression, source omission, reduced boundary input or weaker gate.

Coordinator validates **17 changed Markdown documents / 427 local targets and anchors**
and whitespace in both checkouts. Implementation index empty; no unrelated work found.
Reviewed **22-file** surface covers two runtime modules, the finite example, focused tests/
private barriers, one owning request contract and dependent navigation/evidence updates.
Native production, transfer/fixed worker/CLI/old spec/runtime/version/workflows are unchanged.

Host statement coverage is not every Python branch or installed-process instrumentation.
Worker's **528-check** installed workflow/maintained example, eight selected intended-negative
probes and unavailable Python mutation frameworks remain qualified worker evidence, not a
coordinator rerun. Precise existing native exclusions/runtime suppressions and unsupported
finalizer abandonment remain. Consuming-commit EIO and early raw-ref substitutions are not
physical device failure/naturally concurrent corruption. Real map pressure after successful
new Q/Cq or T/P is private workload, not naturally huge Q. Safe finite real-process barriers,
actual post-F production-limit overflow, trust/capture/full-history/profile/acknowledgement
and platform limits remain as recorded in RESULTS. No global single-dispatch/recovery claim.

The bounded slice is **satisfactory and independently accepted**. Coordinator releases both
builds to worker and directs inspection/staging of only the reviewed 22 implementation files,
focused commit and normal push to the existing branch/remote, then exact-SHA automatic CI
monitoring and bounded fixes. Any CI code/test change needs focused review and appropriate
validation before its next push. No extra worker, design commit/push, force push/new remote,
release/tag/package publication, cloud/global tooling or later feature turn. Publication/CI
completion is still pending.

## Initial publication and Windows CI investigation

Worker inspected/staged only the reviewed **22 files / 2673 insertions / 67 deletions**,
read the complete staged diff and normally pushed
[`509c2f0921e4251da8b2b46f048e540c21b15ad4`](https://github.com/micha/dml/commit/509c2f0921e4251da8b2b46f048e540c21b15ad4).
An unpublished commit-message correction before push changed no tree/published history.
Coordinator verifies committed surface, clean implementation and exact remote master.

[Initial exact-SHA CI 40621755388](https://github.com/micha/dml/actions/runs/40621755388)
completed **cancelled**: five Unix/strict jobs successful, Windows cancelled near its existing
ten-minute job bound. This is not final green CI. Completed log capture contains enormous
raw bytes-assertion zero-padding diffs and lacks the original failing test header; no
precise Windows stack/test diagnosis is claimed from that capped log. Coordinator's first
full-log retrieval timed out after 60 seconds leaving partial evidence. A first watch wrapper
had a local `wait`-ownership error; corrected direct finite watch confirms cancelled status.
Neither tool issue is treated as CI success or a production failure.

Coordinator independently inspects vendored LMDB `mdb_env_map`: Windows non-readonly open
sets data-file extent to configured map size (`SetFilePointer`/`SetEndOfFile`); Unix ordinary
non-WRITEMAP open does not. The new A map-full fixture snapshots default 64 MiB then opens
1 MiB and compares physical bytes without restoring original layout. This provides a
specific dependency-supported explanation; lost Windows header remains a qualification.

Worker's bounded Linux layout emulation reproduces the old map-full fixture failure:
physical lengths **67,108,864 versus 1,048,576**, while fresh complete typed rollback and
old-ref checks pass. Coordinator approves bounded local test-only correction/regression:
restore comparable default map before exact-byte comparison, compute exact equality into
a boolean for bounded diagnostics, retain successful-new-put, real 2 MiB native pressure,
full typed/raw-malformed rollback checks. No runtime/native/workflow/skip/threshold change.
Focused review, fresh validation and a new exact-SHA publication/CI were pending at that
checkpoint.

## Test-only correction review and acceptance

Reviewed **one test file / 72 insertions / one deletion**: small-map fixture reopens the
original default map before full physical equality; private helper uses **exact byte equality**
as a boolean and supplies bounded lengths/SHA256 diagnostics (hashes are not the criterion).
Three helper cases check equality, an altered last raw byte and changed extent; the maintained
layout regression exercises the genuine small-map rollback fixture. All previous successful
new Q/Cq puts, 2 MiB native map pressure, complete typed/raw-corruption and ref checks remain.
No production/native/workflow/skip/threshold/oversized-input change.

Coordinator identified a portability concern in the initial emulation: redundant truncation
of an already live mapped Windows file. Worker guarded the private layout operation with
current extent inequality; actual Windows already applies native extent, no redundant truncate.
The postguard patch is satisfactory. Old Linux-emulated failure is a demonstrated fixture
issue, not proof of the precise cancelled Windows test whose header was lost.

Worker fresh **stable postguard standard** exits 0: **1085 Python/seven C**, Python
**2299/2299**, unchanged retained native/memory gates; focused **254** pass. The earlier
preguard standard is explicitly labelled, not silently called final evidence. After explicit
source freeze/release of both builds, coordinator independently runs all **254 caller tests**,
exit **0**, **43.13 seconds**, `/tmp/dml-iteration8-coordinator-postfix.{log,exit}`.
Source comparison verifies other 21 original accepted hashes/runtime wheel bytes unchanged.

Coordinator accepts the focused correction, releases both builds back to worker and directs
only this test-file commit/normal push, then all final exact-SHA automatic CI verification.
Any further issue returns through review/validation; no broader scope authorization.

## Final publication and exact-SHA CI

Worker staged/inspected only the accepted correction file and normally pushed
[`865bb7933616133acf10d9b14ca0f5fe711c5850`](https://github.com/micha/dml/commit/865bb7933616133acf10d9b14ca0f5fe711c5850)
(`Keep rollback byte checks comparable across map layouts`). Coordinator verifies that
one-file +72/-1 correction surface, clean implementation index/tree and matching remote
master. Runtime/native/workflows and the accepted initial implementation remain unchanged.

[Final exact-SHA CI 40624753242](https://github.com/micha/dml/actions/runs/40624753242)
passes **all six jobs**, after the initial cancelled Windows run and reviewed test-only
correction. Coordinator fetches full final logs/job JSON, verifies sole automatic exact-SHA
push workflow list and direct finite `gh run watch --exit-status`, exit **0**. No manual
workflow, retry of the initial run or release/package publication.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889381) | Success | 7 | 1085 passed; 69.69 s |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889478) | Success | 7 | 1085 passed; 100.42 s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889534) | Success | 7 | 1081 passed, 4 existing skips; 371.11 s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889434) | Success | 7 | 1081 passed, 4 existing skips; 117.16 s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40624753242/job/122606889356) | Success | 7 | 1080 passed, 5 existing skips; 176.26 s |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40624753242/job/122606889247) | Success | 7 | 1085 passed; 77.04 s; Python 2299/2299 |

Existing skips concern unavailable `/dev/full` and Windows Unix pipe fixture. No new skips,
exclusion/suppression, weaker threshold, reduced boundary input or workflow change. Windows
reports UCRT64 Python **3.14.9**; Unix retains existing workflow Python selection. CI strict
uses informational **`-c`**, not independent local default/memory **`-v`**. Final green CI
extends staged platform evidence, not installed cross-platform wheels/coverage/memory,
arbitrary owner-loss cleanup, power-loss, exactly-once, authentication or full capture.
The original cancelled Windows exact-case header remains unavailable; the confirmed
layout-emulation defect and subsequent portable correction are not rewritten as a captured
original Windows trace.

The final Windows verbose log explicitly reports **PASSED** for the corrected small-map
fixture and all four new regression cases (equal bytes, altered raw byte, changed extent,
Windows-layout map-full model). This verifies final portable behavior without recovering the
lost original failure header. After final status reconciliation, coordinator validates
**17 changed Markdown documents / 441 local targets and anchors** and whitespace in both
checkouts. Worker finalizes RESULTS and explicitly acknowledges all work stopped.

Evidence: `/tmp/dml-iteration8-coordinator-final-{ci.json,ci.log,runs.json,watch.log,watch.exit}`.
Coordinator directs worker to finalize only RESULTS and stop all implementation/build/
staging/commit/push/CI activity. Implementation, independent review and publication/CI are
complete and stopped. No additional workers, design checkpoint commit/push, new remote/
force push, release/tag/package publication, cloud/global tooling or later feature turn.
