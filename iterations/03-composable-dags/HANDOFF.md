# Iteration 3 handoff: composable DAGs and named-node lookup

Status: reviewed and approved. The user subsequently authorized the existing Pi
agent in window 2 to implement this bounded turn, with coordinator monitoring,
independent review and fixes, then focused commit/push after acceptance and
exact-SHA CI verification/fixes. See [COORDINATION.md](COORDINATION.md). No additional
workers, releases, cloud experiments or package publication are authorized.

**Delivery:** the bounded turn is complete, independently accepted and published as
`9b8fb71`; all six exact-SHA CI jobs pass. See [RESULTS.md](RESULTS.md) and
[REVIEW.md](REVIEW.md). This handoff preserves its plan/authorization history, not
an instruction to restart or continue into another turn.

## 1. Authority and purpose

[DESIGN.md](DESIGN.md) owns candidate representation/API/inspection choices;
[EXAMPLE.md](EXAMPLE.md) owns the worked example. The user-agreed scope is recorded
in the [discussion](../../discussion.md#iteration-3-agreed-direction-composable-dags-and-named-node-lookup).
This handoff owns the proposed sequence, acceptance evidence and stop line.
Neither this plan nor the candidate is an as-built specification.

Goal: construct named, nested DAGs through the C/Python foundation and inspect them
through the native CLI, preserving shared content and immutable snapshots.
No DML execution is needed to satisfy the example.

When separately authorized, use the existing implementation checkout, keep delivery
notes here, and stop after this bounded turn for review. Implementation authorization
does not automatically authorize publication, extra agents, system/global tooling
changes or a subsequent feature turn.

## 2. Required reading and preflight

Read the machine-wide instructions, confirm `/work` is mounted, then read:

1. Design [AGENTS.md](../../AGENTS.md), [README.md](../../README.md) and
   [resume point](../../discussion.md#resume-point).
2. This handoff, [DESIGN.md](DESIGN.md) and [EXAMPLE.md](EXAMPLE.md), completely.
3. Implementation [AGENTS.md](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [spec instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md) and
   [glossary](../../../dml/docs/spec-next/glossary.md).
4. Current [records](../../../dml/docs/spec-next/records.md),
   [objects](../../../dml/docs/spec-next/objects.md),
   [repository](../../../dml/docs/spec-next/repository.md),
   [Python API](../../../dml/docs/spec-next/python-api.md) and
   [CLI](../../../dml/docs/spec-next/cli.md) contracts.
5. Iteration 2 [results](../02-repository-usability/RESULTS.md) and
   [review](../02-repository-usability/REVIEW.md), especially published-source,
   installed-package, mutation, platform and finalizer limitations.
6. The [coverage catalog](../../../dml/tests/coverage-exclusions.md) and
   [packaging contract](../../../dml/docs/packaging-and-distribution.md).

Preparation inspected clean implementation `e253249eca70ad588d918d321a54a1413447b8a0`.
The design checkout contains pre-existing uncommitted notes plus this planning work.
No build/test suite was run for this plan. Reinspect rather than assuming source
state remains unchanged or resetting either checkout.

After authorization, identify the current project-local environment, establish a
baseline and coordinate shared build use. `scripts/check.sh` reconfigures/wipes
`build/check`; do not run competing builds there. Use fresh test-owned repositories
and bounded local scratch, not real research stores. Request any missing tooling
permission rather than installing globally or changing the system.

Pre-1.0 state may be recreated; no version bump, migration or compatibility layer
is required. That is not deletion authority over unrelated data or an exception
to immutable-object semantics within a repository.

## 3. Scope

### Included

- Literal nodes plus one non-executing sub-DAG-reference node kind.
- Required root and canonical name-to-node bindings within each DAG.
- Explicit single-scope lookup, returning a node ID.
- C codecs/views and direct repository validation for the new references.
- Linked low-level Python construction/reads and owned descriptions.
- Native immediate/nested inspection and matching packaged-console behavior.
- A runnable version of the comparison example, public acceptance tests,
  meaningful failures, normal validation integration and as-built documentation.

The exact additions above are candidate choices within the agreed direction;
record selected replacements before substantial coding. Do not infer a mandate to
build a generic graph engine from the proposed CLI `walk` helper.

### Excluded

- Calls, primitive evaluation, execution engines/adapters, automatic Python execution.
- Intent/closure definitions, installation, requests/attempts, reuse selection/facets.
- Remotes, repository IO transport, cloud experiments or resource management.
- GC/excision, merge/rebase, new ref policies, CLI mutation or global namespaces.
- Observer hooks/registries, a visualization UI, domain interpretation or model calls.
- General computational input-edge/provenance schemas or a workflow framework.
- Generic plugins, recursive value auto-insertion, whole-repository validation,
  automatic map growth, schema migration or packaging/release redesign.

Names in the example do not acquire built-in research semantics. Structural edges
are not proof of causal input capture or scientific validity.

## 4. Source map and recommended sequence

Paths in this section are relative to `/work/repos/micha/dml`.

### A. Capture baseline and selected design

Start `RESULTS.md` in this iteration directory when authorized work begins. Record
source/status, baseline commands/outcomes, and choices at
[the design checkpoints](DESIGN.md#6-design-checkpoints-and-open-questions).
Small bounded engineering replacements can be recorded as assistant selections;
material scope/model changes need a user decision.

### B. Implement codecs/views before higher interfaces

Inspect `include/dml/{object,record,repo}.h`,
`src/{object,object_id,record,repo}.c` and their helpers/tests.
Add node-kind discrimination and DAG root/bindings. Keep tree entries distinct
from DAG bindings in public types, even if private name-encoding helpers are shared.
Audit views/accessors, checked lengths, canonical ordering and unknown-kind handling.

Update independent byte/ID oracles in `tests/python/test_objects_hypothesis.py` and
native test bridges where DAG shape deliberately changes. Retain unchanged datum
and literal golden vectors. Explicitly reject the old DAG encoding; do not add a
silent dual interpretation or migration. Keep existing tree/commit semantics.

### C. Repository references and lookup

Update `src/repo.c` to select node target type by kind and validate DAG root and
binding node references. Audit counted-reference loops that currently assume only
tree entries/commit parents. Preserve direct-not-transitive validation and poisoned
write semantics. All references remain visible in the current transaction.

Add the chosen scoped lookup using the validated DAG read. It is a read operation:
invalid/missing names do not poison writes. No name fallback, node execution or
implicit interpretation of a root name.

### D. Linked Python boundary

Update `python/daggerml/src/_core_module.c`,
`python/daggerml/daggerml/{__init__.py,_core.pyi}` and real-extension tests.
Own/copy node kinds, targets and binding entries before native buffers are released.
Preserve duplicate names until C sees them and immutable descriptions afterward.

Keep current transaction/context/thread policy and fail-closed mutation behavior.
Do not expand lifetime/concurrency policy to accommodate new arrays. Review partial
conversion/cleanup paths; test native and Python-side failure after earlier writes.
No second codec or CLI-mediated binding.

### E. Native inspection

Update `src/cli.c` immediate display and snapshot handling for nonliteral roots.
Implement selected lookup/nested inspection syntax from
[DESIGN.md Section 5](DESIGN.md#5-candidate-inspection-cli), or record a small replacement.
Keep commit `log` distinct from computational traversal, and retain one native CLI
behind package-relative console forwarding.

Test deterministic scope/edge presentation, shared-object suppression, active-path
cycle handling, exact/truncated limits, safe previews, no partial success document
on late storage errors, checked growth and output-write failures. Do not claim
record counts bound bytes/read allocation or prove unseen graph validity.

### F. Example, independent acceptance and local install

Add a small example such as `examples/composable_dags.py` using only public Python
operations. It can contain local composition helpers, not a new library framework.
Produce both comparison snapshots and save IDs/records for fresh-process checks.
Include a separate sub-DAG-root fixture; a summary-literal-only example would miss
the existing snapshot assumption.

Repeat a smoke workflow from a bounded local install outside the checkout. Use the
existing packaging seam and bundled native executable; no release redesign or
publication. Confirm imported modules/binary actually come from installed artifacts.

### G. Validate and reconcile documentation

Extend normal validation for the new native/Python/CLI populations. Run independent
probes/review as available, fix bounded issues, document actual behavior and stop.
No production code should be changed merely to inflate coverage; preserve the
narrow no-value exclusion policy and exact assurance accounting.

## 5. Acceptance and tests

Acceptance follows [EXAMPLE.md](EXAMPLE.md), including fresh-process C1/C2 inspection,
scoped trial-result lookup, shared A content, unchanged historical bytes, sub-DAG
roots and atomic rollback. Check both native and packaged console interfaces.

Required evidence categories for the bounded slice:

| Area | Cases |
| --- | --- |
| Names | Empty/invalid/too-long names; case sensitivity; canonical order; duplicates with same/different targets; aliases; root aliases; no reserved root name |
| Scopes | Same name in two DAGs; missing local name despite nested match; explicit descent; lookup returns ID, not value; no moving-ref binding |
| Identity | Permuted input pairs yield same bytes/ID; rename/retarget/root changes differ; shared sub-DAGs remain shared; literal/datum vectors unchanged |
| Encoding | Both node kinds; empty/nonempty bindings; exact length/count; malformed/truncated/trailing/unsorted data; old DAG shape rejected; unknown kind rejected |
| References | Missing/wrong-type/mismatched-ID targets for both node kinds and each DAG reference; child inserted earlier in batch; reinsertion; corrupt records |
| Transactions | Abort and native/Python mutation failures after prior puts/ref movement; caught failures still roll back; missing lookup does not poison writes |
| Ownership | Copied descriptions after closure; caller container mutation; partial binding conversion; allocation failures; ended/thread-affine handles preserved |
| Traversal | Root-first/canonical binding order; alias/shared-object edges; nested root; deep iterative chain; exact/over-limit/partial output; active-cycle rejection |
| Presentation | Both node kinds and DAG bindings in show/snapshot/walk; bounded escaped values; composite values not computationally expanded; CLI read-only behavior |
| Failures | Invalid grammar/IDs/limits/names; late missing/corrupt visited content; buffered growth/output failure; cleanup and structured diagnostics |
| Installed | Fresh installed producer/reader/console outside source paths; package-relative native executable matches core behavior |

Use Hypothesis for public boundary/round-trip/permutation properties and independent
encoding oracles. Use focused C/private fault fixtures for low-level failure paths.
A genuine cyclic content-addressed graph is not easy to construct: use private
simulated-hash/corruption fixtures where appropriate, explicitly distinguishing
those tests from a real hash collision. Do not add public corruption controls.

### Assurance accounting

Use `scripts/check.sh` per implementation guidance. Previously usable local command:

```sh
nix develop ../dml-build-tools --no-write-lock-file -c bash scripts/check.sh -v
```

Verify availability. Report unavailable checks as blockers; do not substitute CI's
informational `-c` for the default gate. Keep retained C/Python thresholds unchanged.
Audit old exclusions whose invariants change and document any new precise no-value
exclusions, separating tested and excluded populations. Meaningful allocation,
rollback, traversal and output failures need tests despite their difficulty.

Extend Valgrind workloads for the new record/binding arrays, copied descriptions,
CLI traversal and fault cleanup. Preserve narrowly scoped CPython suppressions and
unsupported foreign-last-owner abandonment qualifications; do not call runtime-only
or old-literal-only workloads new-code memory evidence.

Run bounded Mull diagnostics on changed targets as directed by the implementation
guide; report survivors/exit codes and limitations honestly. Existing survivor
reports are neither new failures nor assurance for the new code. Do not spend the
turn chasing a score without a useful oracle improvement.

Local install is not platform/interpreter/release proof. Preserve existing platform
fixtures and matrix; do not launch publication/workflows without authorization.
Record actual tested platforms, skipped paths and installed versus instrumented
coverage. Validate Markdown targets/anchors and whitespace before delivery.

## 6. Documentation and delivery

After code exists, update owning as-built documents: `objects.md` for fields/
encoding/names/views, `repository.md` for direct references/lookup, `python-api.md`
for descriptions/API and `cli.md` for presentation/traversal. Update navigation/
concept map and any affected runnable/packaging examples. Reuse existing ownership
rather than inventing a separate execution document. Clarify glossary terms only
if their meanings genuinely need revision. Keep old `docs/spec/` unchanged.

`RESULTS.md` here records exact changed files, source state, selected design,
commands/exits/counts, independent/fresh-process/installed evidence, coverage and
exclusions, failure/memory/mutation/platform limitations, and remaining defects.
Distinguish implemented shortcuts from intended behavior. Do not create a results
report claiming this candidate already works.

Update the design README/discussion resume point when recording delivery. Preserve
historical failed runs and uncertainty. No automatic commit/push; publication is a
separate user decision.

## 7. Stop line

Stop with a reviewed, constructible and inspectable named/nested content graph and
honest evidence boundaries. Do not proceed to execution, intent/closure binding,
reuse, remotes, resources or observers to make the example more impressive.

The user has now authorized implementation and coordinator review/fixes, followed
by commit/push after acceptance and exact-SHA CI verification/fixes. Follow
[COORDINATION.md](COORDINATION.md) for the active assignment and shared-build boundary.
