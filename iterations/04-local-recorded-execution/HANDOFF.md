# Iteration 4 handoff: one locally executed, recorded step

Status: completed bounded turn, published through `d498a6c` with all six final
exact-SHA CI jobs passing. See [RESULTS.md](RESULTS.md), [REVIEW.md](REVIEW.md) and
[COORDINATION.md](COORDINATION.md). The user authorized the fresh-session window-2
implementation, coordinator monitoring/review/fixes and publication/CI after
acceptance. The plan below preserves that work's scope, not permission to restart.
Package publication and later turns remain unauthorized.

## 1. Authority, goal and stop line

[DESIGN.md](DESIGN.md) owns candidate architecture, ordinary-DAG conventions,
publication and failure semantics. [EXAMPLE.md](EXAMPLE.md) owns the acceptance
story. This handoff owns work sequence, validation and delivery requirements.
The [discussion](../../discussion.md) distinguishes user agreements from proposals.
None of these documents is an as-built specification.

Goal: one trusted local Python implementation consumes pinned named input nodes,
publishes a result sub-DAG, and leaves request/attempt/outcome history that ordinary
Python/CLI readers can inspect. Repeated results may share content identity while
fresh attempts remain distinct.

Stop after that slice and its meaningful failure tests. No arbitrary DAG evaluator,
reuse/cache/facets, intent registry/lifecycle/defaults, installation, scheduler,
remote/network transport, cloud experiment, resource manager, GC/excision, observer
subsystem/UI or general workflow framework. Do not expand the turn merely because
some future recovery/concurrency/security guarantee would be useful.

## 2. Required reading and preflight

Follow the machine-wide index, confirm `/work` is mounted and read completely:

1. Design [AGENTS.md](../../AGENTS.md), [README.md](../../README.md) and
   [resume point](../../discussion.md#resume-point).
2. This handoff, [DESIGN.md](DESIGN.md), [EXAMPLE.md](EXAMPLE.md).
3. Implementation [AGENTS.md](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [as-built instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md) and
   [glossary](../../../dml/docs/spec-next/glossary.md).
4. Current [objects](../../../dml/docs/spec-next/objects.md),
   [repository](../../../dml/docs/spec-next/repository.md),
   [Python API](../../../dml/docs/spec-next/python-api.md) and
   [CLI](../../../dml/docs/spec-next/cli.md) contracts.
5. Iteration 3 [results](../03-composable-dags/RESULTS.md) and
   [review](../03-composable-dags/REVIEW.md),
   [coverage catalog](../../../dml/tests/coverage-exclusions.md) and
   [packaging contract](../../../dml/docs/packaging-and-distribution.md).

Preparation found both checkouts clean: implementation `9b8fb71`, design checkpoint
`cbfcd92`. No build/test suite ran for this candidate and no implementation files
changed. Reinspect rather than assuming that state persists or resetting work.

After separate authorization, identify the implementer/reviewer and agree on shared
`build/check` ownership; standard checks wipe/reconfigure it. Record baseline and
selected candidate details in this directory's `RESULTS.md`. Use fresh test-owned
repositories and bounded project-local/temporary build/process scratch. Do not run
real research scripts or delete unrelated repositories. No system/global bootstrap,
extra agents, publication or inherited Iteration 3 delegation is implied.

Consult current Python standard-library documentation for subprocess lifetime,
argument/path handling, timeout/reaping, tempfile and occurrence-ID APIs before
selecting engineering calls. Use the available documentation skill, not assumed
signatures or a stale adapter scaffold. Preserve existing declared interpreters and
platforms; identify actual tested boundaries rather than weakening declarations.

## 3. Source seams

Paths are relative to `/work/repos/micha/dml`:

| Seam | Inspect / likely bounded changes |
| --- | --- |
| Low-level API | `python/daggerml/daggerml/__init__.py`; no new native access or change to its lifetime policy intended |
| New layer | Candidate `python/daggerml/daggerml/local.py`, own Python descriptions/type hints; no implicit import that runs code |
| Packaging | Root `meson.build` explicitly installs Python sources; include the new module in the existing runtime tag/wheel |
| Examples | Existing `examples/composable_dags.py`; add one executable local-step story and small trusted child source |
| Tests | Real extension setup `tests/conftest.py`, public acceptance/composition/failure tests, and focused new local-execution tests |
| Assurance | `scripts/check.sh`, Python coverage, binding/CLI memory workloads, private fault fixtures and catalog |
| Documentation | New owning local-execution contract under `docs/spec-next/`, navigation map, Python/package orientation |

The existing `python/adapters/` scaffold and old `docs/spec/` are not selected
execution protocols. Leave them unchanged unless a concrete approved need arises.
Core encodings/headers/native CLI are expected to remain unchanged. If a missing
primitive blocks the workflow, show the smallest reproducer and seek a scope decision
before expanding C, ref semantics or CLI capabilities.

## 4. Recommended implementation sequence

### A. Resolve the small integration seam early

Record answers to [design checkpoints](DESIGN.md#7-review-checkpoints-and-stop-line).
Before building broad orchestration helpers, prove that a cooperative subprocess
can import the **current** Python layer/linked extension, read a pinned DAG and
atomically publish an ordinary result through its own transaction.

Use an installed or temporary build-staged runtime for subprocess tests, with explicit
module/extension provenance. Test staging may copy/symlink maintained source/artifacts;
it must not become a second maintained codec or quietly import a stale installed
package. Do not ship test-only import/bootstrap/fault hooks in the runner.

Resolve child argument parsing/publication shape and executable source materialization
before adding lifecycle records. Do not use stdout-only results as an unnoticed
replacement for the durable publication proposal.

### B. Pure descriptions and ordinary records

Implement the selected small Python layer over **public** transaction methods.
Keep occurrence IDs, content IDs and result identity distinct. Validate only roles/
fields this layer consumes, expected node/datum types, URI/source/configuration
bounds and pinned request/binding relationships. No generic schema language.

Build request, initial/final attempt, publication, success/failure and cleanup DAGs
as ordinary data. Tests should inspect them directly with low-level reads, not rely
only on the layer's convenience return value. Keep all existing low-level lifetime,
mutation poison and direct-not-transitive validation distinctions.

### C. Atomic preparation and completion

Implement reservation/publication-ref conventions and exact tree preservation.
Store request/attempt/pre-dispatch commit and head/ref changes together. No subprocess
may launch until the storage transaction has successfully committed and parent
handles are closed. Bounded ID collisions must fail/retry without losing earlier state.

Child publication writes result objects/association/commit/ref in one transaction.
Finalization independently validates pinned identity/association, separates result
from diagnostics/cleanup and writes a new attempt description in a later commit.
Preserve valid child history via parent references even on adapter failure.

Unexpected coordination-head or publication-ref movement must not be overwritten.
A completion persistence error leaves the earlier records inspectable and raises;
it is not an automatic fresh execution, recorded failure or `done` response.

### D. One synchronous local adapter

Launch only explicitly supplied trusted source via an argument vector and selected
executable, without a shell. Execute captured bytes from controlled scratch; support
spaces in paths. Explicitly read context from the supplied pinned commit, not `main`.

Use finite execution timeout, file-backed diagnostics with bounded stored snippets,
direct-child reap/termination and separate cleanup disposition. Preserve the result
if cleanup fails. Do not promise process-tree termination, disk/output memory bounds,
complete environmental capture, secure isolation or recovery after hard interruption.

No automatic retry/resume of an old attempt. Explicit retry creates a new occurrence
using the original recorded request binding/inputs. A changed implementation/config
requires a new request rather than silently changing a retry's binding.

### E. Acceptance, installed workflow and independent review

Implement [EXAMPLE.md](EXAMPLE.md) and fresh-process inspection. Use deterministic
barriers, not timing races, to test parent loss immediately after pre-dispatch and
after child publication but before final commit. Barriers belong in test fixtures/
private test coordination, not production fault flags or a callback/plugin system.

Every process test must have a finite harness timeout and own its child/scratch
cleanup, including assertion/failure paths. Prefer portable termination/barrier tests
where possible; qualify signal-specific evidence separately. Do not leave CI hangs,
orphan fixtures or untracked LMDB directories after negative tests.

Build/install fresh wheels locally through the existing package seam and run both
parent and child outside the checkout. Assert imported module/extension and native
console paths; ordinary CLI snapshot/walk/log inspection should require no new
commands or JSON changes. Ask before tooling bootstrap if existing local tools
cannot supply this smoke route.

## 5. Acceptance and assurance matrix

| Area | Evidence expected |
| --- | --- |
| Successful execution | Real subprocess consumes named I64 inputs 4/7, publishes result DAG rooted in 11, final success/cleanup records and inspectable commit parents |
| Distinct occurrences | Two launches with identical binding/inputs have different requests/attempts and identical result IDs/bytes; no cache substitution |
| Retry | Interrupted request gains new attempt with unchanged binding/inputs; earlier attempt/root ID/bytes remain in history; no implicit re-dispatch |
| Binding capture | Captured entry bytes are what gets executed; later original-file changes do not alter the launch; environment/imports explicitly remain uncaptured |
| Pre-dispatch atomicity | Preparation/ref-create/commit failure means no published occurrence or launch; collision retry bounded; unrelated tree entries survive |
| Child publication | Pinned input/ref association, wrong attempt/request/role/type rejected, unchanged ref or bare stored objects not accepted as result publication |
| Result versus evidence | Zero exit + valid publication is required for success; nonzero exit after publication preserves the DAG/history as evidence |
| Failure and cleanup | Launch/nonzero/zero-without-publication/invalid-publication/timeout paths; successful computation plus explicit cleanup failure |
| Unknown outcomes | Parent loss before launch and after publication; fresh readers see initial attempt with no final status, not inferred failure |
| Storage and conflict | Child/final write abort or map-full; moved head/ref not overwritten; no claimed `done` when final commit fails |
| Diagnostics | Bytes/count/truncation for stdout/stderr; oversized/non-UTF8 output; safe existing CLI previews; no unbounded pipe capture |
| Input/configuration | Exact node/datum/source/URI/runtime types; signed overflow from addition; malformed/corrupt role records; invalid/large timeout/source |
| Isolation limits | Trusted child contract explicit; no false sandbox, complete capture, globally unique ID or exactly-once claim |
| Installed/platform | Current installed parent and child plus console outside checkout; portable CI fixtures; signal/platform/interpreter limits qualified |

Prefer Hypothesis for pure record/round-trip/identity/boundary cases. Real process
tests should use a small deterministic fixture set, not hundreds of random subprocess
kills. Use narrow monkeypatch/private fault fixtures for meaningful storage, spawn,
cleanup, conversion and conflict failure branches, alongside real subprocess success
and timeout/interruption integration. Installed code has no fault controls.

### Standard validation

Use current `scripts/check.sh`, retaining all C/Python thresholds. Prior local pattern:

```sh
nix develop ../dml-build-tools --no-write-lock-file -c bash scripts/check.sh -v
```

Reinspect tooling. Integrate new Python source into measured coverage and packaging;
do not omit the new execution module merely because some paths run in subprocesses.
Explicitly account for direct source tests versus instrumented subprocess versus
installed subprocess evidence. A separate host-side test of child helpers is useful
but not a claim that installed execution was coverage-instrumented. If process
coverage needs private staging/startup configuration, keep it test-only and document
its measured population.

No native additions are intended, so existing C mutation/memory evidence does not
become mutation assurance for the new Python layer. Determine whether useful Python
mutation tooling is already available; if not, report the gap and use explicit
negative-oracle probes rather than pretending Mull tests Python code. Any C changes
would require their own bounded Mull/memory checks and a scope decision.

Retain expanded binding/CLI Valgrind workloads and account for new process-level
memory evidence if claimed. Runtime suppressions and unsupported foreign-last-owner
abandonment remain qualified. Narrow no-value exclusions are allowed under the
existing policy, with precise locations/reasons; meaningful failures need tests and
remaining thresholds stay unchanged. Report every failed/interrupted/unavailable
check honestly rather than calling an informational run the default gate.

## 6. Documentation, delivery and review boundary

Only after implementation exists, add an owning as-built document such as
`docs/spec-next/local-execution.md`. It owns the layer's record/role/ref conventions,
Python APIs, child contract, lifecycle/outcome/cleanup and trust/capture limits.
Reference core object/repository/inspection contracts rather than duplicating them.
Update README's Mermaid/concept map, Python/package orientation and runnable examples
in the same scoped change. Leave old `docs/spec/` unchanged. Glossary definitions
need not change merely because a provisional role has a narrow prototype realization.

`RESULTS.md` here records exact source/status/files, selected choices/deviations,
baseline/final commands/exits/counts, real versus fault/process/installed evidence,
coverage/memory/mutation/platform limits, publication gaps, defects and a suggested
next bounded turn without starting it. Independent review should inspect occurrence
identity, head/ref atomicity, real child imports, parent transaction lifetime,
interruption/timeout cleanup and unknown-versus-failure claims particularly closely.

Update the design resume point when recording a checkpoint. Stop for review once
this slice is satisfactory. Commit/push follows explicit coordinator acceptance;
monitor exact-SHA CI and fix issues within scope under the current user authorization.
No cloud/release/package publication, extra worker or subsequent turn.
