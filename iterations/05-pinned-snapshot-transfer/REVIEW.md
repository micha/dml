# Iteration 5 coordinator review

Status: bounded implementation, independent review, worker publication and final
exact-SHA CI verification are complete. Turn accepted and stopped. Worker evidence is in
[RESULTS.md](RESULTS.md); assignment/authority in [COORDINATION.md](COORDINATION.md).

## Scope and source inspection

Reviewed the public mutation-guarded packed insertion wrapper, explicitly imported
transfer module, install seam, real-attempt example, framing/closure/native-fault/
process-loss tests and owning as-built contract. Native production, encodings,
old spec, CLI grammar/JSON and runtime/release declarations remain unchanged.
Private `core_driver.c` deletion extends test corruption infrastructure only.

Transfer uses public repository operations and native codec/identity/no-overwrite
validation. Typed traversal includes all parents and value/graph edges. Import
requires earlier bundle dependencies even in a populated destination and checks
all-and-only-root reachability before optional ref creation and storage commit.
Readable same-target refs are preserved; different/malformed/dangling refs are not
moved/repaired. Prebuilt owned return data avoids avoidable allocation after commit.
No source execution, historical-path action, ref inference or new occurrence.

Early feedback identified a misleading missing-source test: wrong-key bytes prove
integrity mismatch, not absence. Worker renamed it and added genuine missing parent,
node and composite-only datum-child fixtures using private raw deletion. Added
unhashable-kind and lifetime/owner-thread coverage. This corrected assurance/naming,
not a production defect. No functional defect found in current implementation.

## Independent installed probes

Created separate pip-less `/tmp/dml-iteration5-review-install.*` venv and populated
it offline through the existing project-local packaging tools from worker's fresh
current core/console wheels. No shared build directory or global install touched.
Parent runs outside checkout with PYTHONPATH unset and verifies installed module
and extension provenance. Session-local
`/tmp/dml-iteration5-coordinator-probe.py` passes **50 independent checks**, exit **0**;
log `/tmp/dml-iteration5-coordinator-install.log` and `.exit`.

- Two real local attempts: distinct request/attempt occurrences, equal result rooted
  in 11, successful outcome and ordered two-parent completion history.
- Independent breadth-first enumeration through public descriptions, not transfer
  internals, compares complete typed population, every exact packed byte and parents.
- Source renamed away after closure/export; fresh importer and reader require only
  bundle/B, with identical B re-export and idempotent same-ref/no-ref imports.
- Unrelated destination sentinel preserved; branch-only source datum and main,
  publication and request reservation refs absent.
- Installed console's ordinary ref/snapshot/log/walk JSON succeeds from outside
  checkout. This is parsed-output agreement, not complete closure via CLI prefixes.
- Thin input in populated B, late ID mismatch, extra unreachable object and genuine
  different-ref conflict abort a genuinely new prefix, preserving destination state.

Evidence is local CPython **3.13.15 / Linux x86_64**, current `cp313-abi3` wheel,
not earlier interpreters/other platforms, sdist/release, coverage-instrumented
installed children or hostile-input/security assurance. Worker owns separate
map-full/pre/postcommit process-loss, native fault, memory and negative-oracle evidence.

## Final default validation and acceptance

Worker explicitly froze runtime/tests and released shared `build/check`. Coordinator
then independently ran from `../dml`:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Fresh run exits **0**; `/tmp/dml-iteration5-coordinator-check.{log,exit}`:

- **467 Python tests**, **seven C executables** pass.
- Python **1,163/1,163 statements**, including transfer **167/167** and example
  **109/109**, without new exclusions or weaker thresholds.
- Retained C **1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**.
- Expanded binding Valgrind workload: **zero unsuppressed errors**; exit heap
  500,823 bytes/8,717 blocks, of which existing CPython patterns suppress
  476,387 bytes/8,657 blocks (624 contexts). Runtime retained allocations are not
  claimed absent; unsupported foreign-last-owner abandonment remains qualified.
- **141 native CLI Valgrind processes** pass. No new suppression, native production
  mutation claim or installed-child coverage/security guarantee.

Installed wheel Python sources (`__init__`, transfer, local) exactly match maintained
reviewed sources. Changed Markdown targets/anchors and whitespace pass. Unavailable
Python mutation tools/four bounded negative-oracle probes, source-read allocations,
long read snapshots, profile versus RSS/time bounds and postcommit response-loss
limits remain explicit in RESULTS/as-built documentation.

Implementation is satisfactory for the bounded turn. Coordinator releases shared
build ownership back to worker and authorizes inspection/staging of only the reviewed
19-file implementation slice, focused commit and normal push to existing master/origin,
then automatic exact-SHA CI monitoring and bounded reviewed fixes. No force push,
tag/release/manual release workflow, package publication or later feature turn.
Design notes remain local/uncommitted. Final publication/CI evidence follows.

## Final publication and CI

Worker inspected/staged only the reviewed 19-file slice and committed/pushed
[`0ec769b5e85fde6b6581b628fffdf3465c78a098`](https://github.com/micha/dml/commit/0ec769b5e85fde6b6581b628fffdf3465c78a098)
(`Add atomic pinned commit transfer between local repositories`). Coordinator
independently verified the committed surface (1,672 insertions/8 deletions), exact
remote master SHA and clean implementation checkout/index.

[CI run 40556958937](https://github.com/micha/dml/actions/runs/40556958937) is the
only automatic workflow listed for that SHA, push event. All six jobs complete
**success** on the first run; no CI fix/rerun was needed. Coordinator fetched completed
job/run JSON and full logs, checked exact-SHA workflow list and independently ran
`gh run watch --exit-status` (exit **0**). macOS arm64 was initially queued, then ran
successfully; queue delay is not a test failure or skipped job.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40556958937/job/122375473266) | Success | 7 | 467 passed |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40556958937/job/122375472818) | Success | 7 | 467 passed |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40556958937/job/122375473521) | Success | 7 | 463 passed, 4 existing skips |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40556958937/job/122375473155) | Success | 7 | 463 passed, 4 existing skips |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40556958937/job/122375473267) | Success | 7 | 462 passed, 5 existing skips; 36.03 seconds |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40556958937/job/122375472343) | Success | 7 | 467 passed |

Existing skips concern absent `/dev/full` and the Windows Unix closed-pipe case.
No new skip/suppression, weaker gate, reduced boundary input or CI workflow change.
CI strict-Linux uses informational **`-c`**, not the independent local default/memory
**`-v`** gate. Its Python 1,163/1,163 report does not imply installed-process coverage.
No release/manual workflow, tag, package publication, force push, extra worker or
later feature turn. All earlier assurance/trust/profile qualifications remain.

Session-local coordinator evidence:
`/tmp/dml-iteration5-coordinator-{ci.json,ci.log,runs.json,watch.log}`. Worker was
instructed to finalize RESULTS and stop. Implementation is clean at pushed `0ec769b`;
design notes remain local/uncommitted in the no-remote repository.
