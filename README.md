# DML design

Exploratory, agent-first design discussions for [DML](https://github.com/micha/dml).
This repository preserves design progress separately from the implementation and
its existing draft specifications.

## Start here

- Iteration 5 [design](iterations/05-pinned-snapshot-transfer/DESIGN.md),
  [worked example](iterations/05-pinned-snapshot-transfer/EXAMPLE.md) and
  [conditional handoff](iterations/05-pinned-snapshot-transfer/HANDOFF.md): approved
  bounded plan for pinned commit/full-history transfer between initialized local
  repositories. Implementation/delegation/publication remain unauthorized;
  illustrative APIs and provisional engineering details are not as-built contracts.

- Iteration 4 [delivery](iterations/04-local-recorded-execution/RESULTS.md) and
  [coordinator review](iterations/04-local-recorded-execution/REVIEW.md): one locally
  executed, recorded Python step, published through `d498a6c`; all six final
  exact-SHA CI jobs pass. Implementation/review/publication are complete and stopped.
- Iteration 4 [design](iterations/04-local-recorded-execution/DESIGN.md),
  [worked example](iterations/04-local-recorded-execution/EXAMPLE.md) and
  [handoff](iterations/04-local-recorded-execution/HANDOFF.md) preserve the bounded
  plan and its provenance, not permission to restart or add later features.
- [Iteration 3 delivery](iterations/03-composable-dags/RESULTS.md) and
  [coordinator review](iterations/03-composable-dags/REVIEW.md): named/composable DAGs,
  scoped lookup and nested CLI inspection, published as `9b8fb71`; all six exact-SHA
  CI jobs successful. Implementation and review are complete; work is stopped.
- Iteration 3 [worked example](iterations/03-composable-dags/EXAMPLE.md),
  [design](iterations/03-composable-dags/DESIGN.md) and
  [handoff](iterations/03-composable-dags/HANDOFF.md) preserve the approved plan and
  bounded authorization, not permission to restart or add later features.
- [Iteration 2 delivery](iterations/02-repository-usability/RESULTS.md): low-level
  linked Python repository API and inspection-only native CLI, worker/coordinator
  default checks and local install validation pass; published through `e253249`
  with all six exact-SHA CI jobs successful. See the
  [coordinator review](iterations/02-repository-usability/REVIEW.md).
- [Iteration 2 design](iterations/02-repository-usability/DESIGN.md) and
  [handoff](iterations/02-repository-usability/HANDOFF.md): agreed scope and candidate
  choices for that authorized bounded turn, not additional feature approval.
- [Iteration 1 delivery notes](iterations/01-minimum-viable-repository/RESULTS.md):
  implemented minimum viable repository and bounded review follow-up; default
  validation passes with documented no-value exclusions; stopped for review.
- [Iteration 1 handoff](iterations/01-minimum-viable-repository/HANDOFF.md): detailed
  plan and scope for that authorized turn.
- [Glossary](../dml/docs/spec-next/glossary.md): shared vocabulary for maintained documentation and
  best-effort use in design discussion; provisional terms are marked.
- [New as-built specification](../dml/docs/spec-next/README.md): implemented behavior
  in the evolving new direction.
- [Observer experiment handoff](observer-study/HANDOFF.md): proposed stages,
  evidence corpus, acceptance criteria and delegation; implementation not started.
- [Discussion checkpoint](discussion.md): goals, conceptual agreements,
  tentative directions, corrections, and open questions.
- [Resume point](discussion.md#resume-point): where to continue the conversation.
- [Feasibility study](feasibility/README.md): experiments, counterexamples, and
  [candidate iteration results](feasibility/ITERATION-RESULTS.md).
- [Focused final audit](feasibility/final-review/report.md): independent checks
  of the latest fixes and remaining flaws.
- [Agent guide](AGENTS.md): scope and note-maintenance rules.

The checkpoint is chronological. Later clarifications can supersede earlier
proposals; it is not a finalized specification or implementation approval.

## Current focus

Iteration 5's bounded plan is approved: transfer one pinned DML commit and its complete
all-parent typed object closure between local repositories, preserving IDs/bytes and
computational occurrences, with optional atomic destination-ref creation and ordinary
Python/CLI inspection. The [design](iterations/05-pinned-snapshot-transfer/DESIGN.md)
and [handoff](iterations/05-pinned-snapshot-transfer/HANDOFF.md) guide the approved plan.
Choices include a narrow public packed-record insertion wrapper over existing native
operations, a separate transfer module, bounded JSON/base64 bundles and create-or-same-
target destination refs. Source refs and external resources are not transferred.

This is not remote execution or automatic synchronization, and it adds no recovery,
merge, thin/shallow/resumable exchange, network/cloud, reuse/facets or resource/observer
work. No implementation, worker assignment, implementation commit/push or CI launch
is authorized. Preparation inspected clean `d498a6c`; no tests/prototypes ran or
implementation files changed. The user requested a local checkpoint of the approved
Iteration 5 plan in this no-remote design repository; no push is authorized.

Iteration 4 is implemented, independently reviewed and published through `d498a6c`.
It adds a separate explicitly imported `daggerml.local` layer: captured trusted Python
entry bytes, pinned named inputs, ordinary request/attempt/outcome DAGs, cooperative
child result publication, explicit retry and separate computational/cleanup outcomes.
No native evaluator or execution CLI command was added. Unknown outcomes after
interruption remain unknown; capture/trust/cleanup limits remain explicit in the
[as-built contract](../dml/docs/spec-next/local-execution.md).

Worker and coordinator fresh default checks pass: seven C executables, 368 Python
tests, 878/878 Python statements and unchanged retained C coverage/memory gates.
Coordinator's separate installed parent/child/reader/console probes pass 43 checks.
Two Windows-stalled runs were cancelled; a confirmed oversized pytest-ID defect was
fixed without reducing the 1 MiB + 1 byte input or weakening tests. Final exact-SHA
[CI run](https://github.com/micha/dml/actions/runs/40536650838) passes all six jobs.
Cancelled-run log unavailability, direct-helper versus uninstrumented child coverage,
mutation-tooling gaps and platform/install limits remain qualified in
[RESULTS](iterations/04-local-recorded-execution/RESULTS.md) and
[REVIEW](iterations/04-local-recorded-execution/REVIEW.md).

Implementation master is clean at pushed `d498a6c`; this bounded turn is complete
and stopped. No release/package publication or later feature turn. The user accepted
the delivery; its design notes were checkpointed locally as `ee708c4` in this
no-remote repository. Iteration 4's stop line remains; Iteration 5 is planning only.
Reuse/facets, intent lifecycle,
scheduling, remotes/cloud, resources and observer/UI remain outside this turn.

Iteration 3 is implemented, independently reviewed and published as `9b8fb71`.
It adds scoped named DAG bindings, non-executing sub-DAG-reference nodes, explicit
lookup and bounded nested CLI inspection over the existing C/Python foundation.
The runnable comparison example records Python-produced values and containment,
not captured computational causality or DML execution.

Worker and coordinator fresh default checks pass: 7 C executables, 316 Python tests,
Python 469/469 statements and retained C 1681/1681 lines, 132/132 functions,
1562/1562 outcomes; expanded binding and 141 native CLI memory processes pass.
Coordinator's 49 independent probes and isolated installed workflow also pass.
The first published exact-SHA CI run succeeds in all six jobs. Precise exclusions,
mutation survivors, unsupported finalizer abandonment, presentation/read limits,
platform skips and local installed-package limits remain explicit in the
[delivery](iterations/03-composable-dags/RESULTS.md) and
[review](iterations/03-composable-dags/REVIEW.md).

The implementation checkout is clean at pushed `9b8fb71`; work is stopped after
this bounded turn. No release/tag, package publication or later feature was started.
Design notes are checkpointed locally in this no-remote repository.

Iteration 2 delivers a low-level Python API over the existing C foundation and an
inspection-only native CLI with packaged console forwarding. Worker and independent
coordinator default checks pass; after bounded Windows fixture fixes the fresh
local default run has 7 C executables and 255 Python tests, with retained 100%
C/Python populations and precise exclusions/runtime-memory suppressions. Published
`e253249` passes all six CI jobs, with platform skips and informational CI coverage
kept distinct from the local default/memory evidence. Local staged-source/wheel
install workflows pass; mutation survivors, unsupported foreign-last-owner
abandonment and untested installed-package/runtime coverage remain explicit in the
[delivery notes](iterations/02-repository-usability/RESULTS.md).

Implementation, review, authorized publication and Actions monitoring are complete;
Iteration 2 work is stopped. No tags, releases, package publication or later feature
implementation were performed. Design notes remain local/uncommitted. Higher-level
helpers belong above this low-level API; the runnable
example is composition, not a workflow framework.

The central goal is human visibility into high-throughput agent-led research:
deterministic inspection and progressive visualization of recorded computation,
not another layer of agent reassurance. See the discussion's
[observability motivation](discussion.md#observability-motivation-and-sidecar-observers).

- Independent sidecar observers over uniformly structured research history.
- Immutable computational history with distinct request and attempt occurrences.
- Intent-level reuse defaults, explicit overrides, and versioned reuse selection.
- Bounded execution adapters reporting `working` or `done`.
- Resource ownership, full-history retention, GC, and explicit excision.
- An ordinary OpenTofu IaC Git repository as a regenerable resource-management
  view of DML, deployed through user- or agent-selected tooling.
- HCL composition and installation DAGs that can produce bound execution closures.

The authorized feasibility study and candidate iteration tested these ideas using
local OpenTofu, a real artifact provider, durable journals, process-kill experiments,
and independent audits. Narrow cooperative mechanisms work; automatic real-resource
management still has unresolved authority, input-capture, composition and erasure
gaps. See [the iteration results](feasibility/ITERATION-RESULTS.md) before choosing
next steps. Exact production schemas, APIs and policies remain open.

## Provenance

The user authorized moving `/tmp/dml-tasks/agent-design/` to
`/work/repos/micha/dml-design` and making an initial local checkpoint commit.
`discussion.md` is the migrated `output.md`, updated to reflect its persistent
location. Original task input and acknowledgement are preserved unchanged in
[archive/](archive/); their temporary paths and coordination instructions are
historical, not active directives.

Other task reports and validation artifacts were not migrated. The DML
implementation checkout remains separate at `/work/repos/micha/dml`.
