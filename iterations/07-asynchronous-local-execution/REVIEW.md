# Iteration 7 coordinator review

Status: bounded implementation independently accepted, focused worker commit/push and
final exact-SHA CI verification complete. Turn accepted and stopped.
[RESULTS.md](RESULTS.md) owns worker evidence; [COORDINATION.md](COORDINATION.md) owns
assignment/build gates.

## Source review and feedback

Reviewed the **22-file** implementation slice over `a0aa05d`: additive public-API-only
exchange helpers and shared exchange-owned P/U/F role validation, readiness receipt,
fixed installed worker/Meson inventory, maintained finite application/child, focused
launch/progress/history/file/storage/process tests and owning as-built contract/navigation.
Native production, local/transfer implementations, old spec, CLI grammar/JSON, adapter,
runtime/version declarations and workflows are unchanged. Synchronous callers/tests remain.

Saved handles carry observation identity/independent caller expected, not process/PID,
commands, A path or recovery authority. Start retains the exclusive marker before fixed
spawn, prepares streams/live owner before spawn and returns without computational wait.
Explicit application ownership/reaping is separate from observation. Readiness separates
bootstrap races from malformed ready storage and is published before public dispatch.
Coherent live-B reads select fresh Q/T relative to C; immutable pinned export, isolated
validation and scratch cleanup precede new packet publication. Receivers validate again
before atomic explicit-ref A import; no existing head movement or progress-ref update.
P/U stays working; only validated retrieved F supplies done and final computation/cleanup.
Publication/failure evidence, missing outcome, outer-worker exit and A reception stay distinct.

Early feedback requested prior Q/T/publication-in-C and coherent read/export pin evidence.
Further feedback strengthened true unchanged-production-limit post-F overflow (rather
than merely scaled rejection), replaced timing-sensitive example windows with finite
caller-owned gates, and added actual concurrent observers, valid other-token matching-job
P/U/F packet swaps and new receiver validation-cleanup failure before A writes. Worker
added these regressions/refinements without broadening production scope. Reviewed actual
successful-new-A-put instrumentation, full-state fresh readers, consuming-commit substitution
and safe real-process barriers. No outstanding within-scope functional finding remains.

Example gates are ordinary declared inputs and trusted source effects, not installed
fault hooks. They are released on errors before worker reaping. Worker-loss fixtures
pause before actual child spawn or after actual child reaping, not arbitrary-kill tests
with live computational children. No portable unowned detached lifetime, process-tree
cleanup, exactly-once, automatic recovery or full-environment capture claim is accepted.

## Independent installed evidence

Created a separate pip-less `/tmp/dml-iteration7-review-install.*` environment using existing
project-local packaging tools and current worker-built core/console wheels; no shared build
writes or global install. Context7 `/websites/pip_pypa_io_en_stable` confirmed offline
`--python` install semantics. Session-local
`/tmp/dml-iteration7-coordinator-probe.py` runs outside checkout with PYTHONPATH unset and
passes **208 independent checks**, exit **0**; corresponding `.log`/`.exit` preserve output.

- Installed package/core/local/transfer/exchange/fixed-worker provenance; actual captured
  child independently asserts installed module/core provenance.
- Explicit owner retains/reaps real worker while fresh observer/receiver clients exit;
  cooperative barriers expose actual P/U before child exit. Three fresh jobs retain
  distinct Q/T and identical result content (third is nonzero-after-publication failure).
- A offline during execution; copied complete P/U/F packets received with B offline and
  independently supplied caller expected. Main is independently advanced and preserved;
  sentinel/base packed bytes preserved, B working/reservation/publication refs absent.
- Independent public breadth-first typed closure/every packed byte at B/packet/A, including
  composite-only datum descendants and prior full Q/T/publication tree in later C. No
  transfer private traversal or CLI prefixes used as the closure oracle.
- Same Q/T across P/U/F; repeated receive is equal/nonexecuting, explicit initial/publication/
  completion refs preserved; attempted P-to-F ref advance conflicts.
- F retrieved after removing original completion receipt; failure retains result only as
  evidence with separate cleanup. Ordered P/U/F parent IDs and result 11 inspected.
- Typed-valid publication relabelled completion rejects before A writes, with full A
  data-file equality. Existing installed console history agrees on selected commits.

All five core wheel Python modules match final maintained source bytes. Evidence is local
CPython **3.13.15 / Linux x86_64**, `cp313-abi3` core/pure console, not earlier runtimes,
other platforms, sdist/release, installed process coverage/memory or security assurance.
Worker's separate 248-check installed harness/maintained example are qualified worker
evidence, not a coordinator rerun.

## Independent default gate and acceptance

After explicit worker source freeze and release of **both `build/check` and `build/coverage`**,
coordinator ran from implementation:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Fresh run exits **0**, `/tmp/dml-iteration7-coordinator-check.{log,exit}`:

- **831 Python tests**, **seven C executables** pass; Python tests 105.00 seconds.
- Python **2013/2013 statements**; exchange **549/549**, fixed worker **9/9**, maintained
  application **131/131**, slow child **29/29**.
- Retained C **1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**.
- Binding Valgrind zero unsuppressed errors; existing 624 runtime suppressed contexts.
  Exit heap 500,823 bytes/8,717 blocks: 476,387 bytes/8,657 blocks suppressed;
  24,436 bytes/60 blocks reachable.
- **141 native CLI Valgrind processes** pass. No new exclusion/suppression/weaker gate.

Host statement coverage is not every Python branch or installed-child instrumentation.
Old precise native exclusions/runtime suppressions, unsupported finalizer abandonment,
unavailable Python mutation frameworks and six selected worker negative-oracle probes
remain qualified. Substituted consuming-commit EIO is not a physical device fault; scaled
profile rejection is distinct from actual >4 MiB post-F per-record overflow. Finite safe
process barriers do not establish arbitrary hard-owner-loss/descendant cleanup or power-loss
assurance. Trust, full capture, sensitive full-history transfer and profile limits remain.

Coordinator validates **17 changed Markdown documents / 379 local targets and anchors**
plus whitespace in both checkouts. Implementation index empty; no unrelated implementation
work found. Design notes remain separate/local/uncommitted.

This bounded implementation is **satisfactory and accepted**. Coordinator releases both
shared build directories back to worker and authorizes inspection/staging of only the
reviewed 22 implementation files, focused commit and normal push to existing branch/remote,
then automatic exact-SHA CI monitoring and bounded fixes. Any CI code/test change needs
focused review and appropriate validation before its next push. No force push, new remote,
manual release workflow, tag/release/package publication, extra worker, cloud/global tooling
or later feature turn. Final publication/CI evidence follows.

## Final publication and exact-SHA CI

Worker inspected/staged only the reviewed **22-file** slice (**2594 insertions/29 deletions**)
and normally pushed
[`a8d646379a52878d087d28bc216b7baa4f9ef3db`](https://github.com/micha/dml/commit/a8d646379a52878d087d28bc216b7baa4f9ef3db)
(`Observe asynchronous local execution through pinned snapshots`). Coordinator verifies
committed surface, clean implementation index/tree and exact remote master. No design
notes were committed. No postacceptance runtime/test/spec change or CI fix was needed.

[CI run 40602956772](https://github.com/micha/dml/actions/runs/40602956772) passes on the
**first published run**, exact SHA above, all **six jobs** successful. Coordinator fetched
full run/job JSON and logs, verified the sole exact-SHA automatic push workflow list and
independently completed finite `gh run watch --exit-status`, exit **0**. Context7
`/websites/cli_github_manual` informed current verification syntax. No manual/release
workflow or rerun was triggered.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40602956772/job/122535365752) | Success | 7 | 831 passed; 63.20 s |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40602956772/job/122535365652) | Success | 7 | 831 passed; 53.08 s |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40602956772/job/122535365492) | Success | 7 | 827 passed, 4 existing skips; 224.83 s |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40602956772/job/122535366525) | Success | 7 | 827 passed, 4 existing skips; 88.19 s |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40602956772/job/122535365829) | Success | 7 | 826 passed, 5 existing skips; 119.30 s |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40602956772/job/122535365773) | Success | 7 | 831 passed; 76.20 s |

Existing skips concern absent `/dev/full` and Windows' Unix pipe case. No new skip,
exclusion/suppression, weaker gate, reduced boundary input or workflow change. Strict CI
uses informational **`-c`**, not independent local default/memory **`-v`**. Its reported
Python 2013/2013 statements and native retained totals are not installed-child coverage.
All earlier trust/profile/process/platform/mutation qualifications remain.

Session-local evidence: `/tmp/dml-iteration7-coordinator-{ci.json,ci.log,runs.json}` and
`/tmp/dml-iteration7-coordinator-watch.{log,exit}`. Coordinator instructed worker to finalize
only RESULTS and stop all runtime/build/staging/commit/push/CI activity. Implementation,
review and publication/CI are complete and stopped. No extra worker, force push/new remote,
release/tag/package publication, cloud/global tooling or later feature turn. Design notes
remain local/uncommitted; no design checkpoint/push was requested.
