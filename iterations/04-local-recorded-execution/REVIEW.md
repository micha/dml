# Iteration 4 coordinator review

Status: bounded implementation, independent review, authorized publication and
final exact-SHA CI verification are complete. The turn is accepted and stopped.
Worker evidence/limits are owned by
[RESULTS.md](RESULTS.md); assignment/authorization by [COORDINATION.md](COORDINATION.md).

## Inspection and scope

Reviewed the 16-file implementation slice over clean baseline `9b8fb71`: separate
`daggerml.local`, installation seam, trusted child/driver examples, acceptance,
failure/interruption/malformed-record tests and owning as-built documentation.
The worker explicitly paused runtime/tests and released `build/check` before
coordinator validation. No implementation edits were made by the coordinator.

The layer uses only public repository operations. Parent handles close before
child work; initial request/attempt/head/ref publication is atomic, child result
publication uses its own transaction, and finalization checks the coordination
head, pinned context and exact child tree/parent/association. Computation/cleanup
outcomes remain separate, retry creates a new attempt for the reserved request,
and missing final status remains unknown. Captured bytes are executed rather than
rereading a moving source. NFC restriction avoids filesystem-path retargeting by
native STRING normalization.

No functional defect was found during this independent inspection/probing.
Coordinator provided progress feedback and kept publication blocked until the
independent default run and installed probes completed. Worker self-review fixes,
including post-launch IO/reaping misclassification, are recorded in RESULTS and
have regressions. No native/core/CLI expansion, old-spec/adapter changes, migration,
version bump, release or later feature work was found.

## Independent default validation

From `../dml`:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Fresh coordinator run exits **0**. Logs:
`/tmp/dml-iteration4-coordinator-check.log` and `.exit`.

- **368 Python tests** and **seven C executables** pass.
- Python **878/878 statements** (local layer **361/361**, local examples **48/48**).
- Retained C **1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**.
- Binding memory workload has zero unsuppressed errors/leaks, with existing narrow
  CPython runtime suppressions; **141 native CLI Valgrind processes** pass.
- No new exclusion, suppression or weakened threshold. Host-side measured source
  is distinct from uninstrumented staged/installed children. No coordinator Python
  mutation framework or new process-level memory/sandbox assurance is claimed.

Existing precise exclusions, runtime heap/suppressions, unsupported foreign-last-owner
abandonment, direct-not-transitive validation and unavailable Python mutation tooling
remain qualified. Four worker negative-oracle probes are not a mutation score.

## Independent installed probes

Created a separate `/tmp/dml-iteration4-review-install.*` pip-less venv, populated
offline from current worker-built core/console wheels using the existing local
packaging-tools installer. No global install/bootstrap. Parent executes from `/tmp`
with PYTHONPATH unset; maintained `local.py` bytes match installed source. Parent,
real child, reader and console/native executable paths belong to that new install.

Session-local `/tmp/dml-iteration4-coordinator-probe.py` passes **43 independent
checks**, exit 0; `/tmp/dml-iteration4-coordinator-install.log`.

Evidence includes distinct requests/attempts with identical result content, exact
ordinary-record inspections, immutable saved initial DAG/commit bytes, unrelated
tree preservation, explicit retry on a different coordination head, correct ordered
publication parents, real timeout **after durable publication** retaining evidence
and child history, zero exit without publication rejected, final-head conflict
preserving initial unknown plus published result, duplicate publication rejected,
fresh-process reader and console/native JSON agreement for snapshot/walk/log/ref.
All probe scratch is removed; no real research repository is used.

This is local CPython **3.13.15 / Linux x86_64** installed-wheel evidence, not earlier
interpreter, other platform, manylinux, sdist or release validation. It supplies
functional installed-process evidence, not coverage-instrumented child execution.

## Documentation and acceptance

Code/tests/owning contract consistently distinguish unknown from failure, result
from evidence, computation from cleanup, content from occurrence identity, and
recorded source/inputs from full environmental capture. Trust, direct-child-only
cleanup, timeout/spawn limits, unbounded child/disk/resource effects and lack of
exactly-once guarantees are explicit. Whitespace and local Markdown target/anchor
checks pass in both repositories.

The implementation is satisfactory for this bounded turn. Worker may inspect/stage
only its reviewed implementation slice, commit and normally push the existing
branch/remote, then monitor exact-SHA CI and fix within-scope failures. Design notes
remain local/uncommitted. No tags/releases/package publication or later feature.
Final publication/CI evidence follows below.

## Publication and CI diagnostic follow-up

Worker committed/pushed the reviewed 16-file slice as
`efac107a084d1a686f3ce7d47b1b549ade2f0e39`. Coordinator independently verified the
committed file surface, clean implementation checkout and exact remote master SHA.
[Run 40532370498](https://github.com/micha/dml/actions/runs/40532370498) passed five
Unix jobs but stalled in Windows Python tests, substantially beyond the prior run.
This is **not successful CI**. Coordinator requested investigation and authorized
cancellation to obtain diagnostics, then a narrow CI-only diagnostic/finiteness
follow-up. Ordinary and forced cancellation were requested; the run ultimately
completed cancelled. Windows logs were unavailable at the first completed-run fetch.

Worker's Linux lifetime probe found no overlapping same-path repository handles or
live parent handle at real spawn in all 52 new tests; it does not establish Windows
native-call behavior. No speculative production fix was accepted. CI-only follow-up
`b0e3107e2a2c0767f79076b72b8e9e097ad291dc` adds a ten-minute matrix-job timeout and
unbuffered verbose Windows test IDs with pytest's 60-second faulthandler diagnostic.
Coordinator inspected its exact two-line workflow diff; tests/thresholds are not
skipped or weakened. [Run 40534587951](https://github.com/micha/dml/actions/runs/40534587951)
is the diagnostic run for that exact SHA. It also ultimately completed cancelled;
Windows logs remained unavailable (`log not found`), so no original Windows
stack-trace diagnosis is claimed. See final evidence below.

## Confirmed test defect and final independent verification

Worker identified an oversized pytest-ID defect: the boundary parametrization's
1 MiB + 1 byte source became a **1,048,725-character** node ID, also inserted into
`PYTEST_CURRENT_TEST`. A bounded model of Windows' environment-value length limit
rejected the original case during setup/teardown (9 pass, 2 errors); short semantic
IDs preserve the original large input and rejection assertion while preventing
that overflow. A per-case regression bounds node-ID length. Maximum ID in the new
module is now 99 characters. The after-model passes all ten cases. This is a
confirmed portable test defect, not proof of the unavailable original job stack.

Coordinator explicitly accepted the test-only fix, inspected the full single-file
commit `d498a6cd4eea170c2054690880526c2fbb6ebaa6`, and independently reran all **52 new
tests**, exit 0 (`/tmp/dml-iteration4-coordinator-postfix-focused.log`). Worker fresh
postfix default `-v` also exits 0 with 368 tests, unchanged retained coverage and
binding/141 CLI memory workloads. No production code changed after the reviewed
implementation; no input was reduced, test skipped or threshold weakened.

[Final run 40536650838](https://github.com/micha/dml/actions/runs/40536650838) completes
**success** for exact SHA `d498a6cd4eea170c2054690880526c2fbb6ebaa6`. Coordinator
independently checked completed run/job JSON, full logs, exact-SHA workflow list,
`gh run watch --exit-status` (exit **0**), clean checkout/index and exact remote
master SHA. This is the only automatic workflow for the final SHA.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40536650838/job/122306375439) | Success | 7 | 368 passed |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40536650838/job/122306374559) | Success | 7 | 368 passed |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40536650838/job/122306374113) | Success | 7 | 364 passed, 4 skipped |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40536650838/job/122306374428) | Success | 7 | 364 passed, 4 skipped |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40536650838/job/122306374385) | Success | 7 | 363 passed, 5 skipped |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40536650838/job/122306374931) | Success | 7 | 368 passed |

Windows Python completes in **45.99 seconds**. Existing skips concern `/dev/full`
and the Windows Unix-pipe test; no new skip was added. CI strict-Linux remains
informational `-c`, not the local default/memory gate. The accepted finite-job
bound and verbose Windows/faulthandler diagnostics remain; no extra output-only
commit is required. No release/tag/manual release workflow was triggered.

Session-local diagnostics: `/tmp/dml-iteration4-coordinator-final-ci.{json,log}`
and `/tmp/dml-iteration4-coordinator-final-watch.log`. Cancelled runs remain visible
and are not counted as passing evidence. All earlier coverage/memory/mutation,
installed-runtime, direct-validation, trust/capture and unknown-outcome limits
remain qualified. Final acceptance is complete; worker was instructed to finalize
RESULTS and stop. Design notes remain local/uncommitted.
