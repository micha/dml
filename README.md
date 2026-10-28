# DML design

Exploratory, agent-first design discussions for [DML](https://github.com/micha/dml).
This repository preserves design progress separately from the implementation and
its existing draft specifications.

## Start here

- Iteration 8 [design](iterations/08-caller-recorded-requests/DESIGN.md),
  [worked example](iterations/08-caller-recorded-requests/EXAMPLE.md) and
  [conditional handoff](iterations/08-caller-recorded-requests/HANDOFF.md): approved bounded
  plan, included in the requested local design checkpoint. A explicitly records Q before
  launch; B registers imported Q locally and creates only T. Atomic submission/request
  refs, public local seams and pinned-Q validation preserve identity across repositories.
  Plan approval is not implementation/delegation/publication GO.

- Iteration 7 [delivery](iterations/07-asynchronous-local-execution/RESULTS.md) and
  [coordinator review](iterations/07-asynchronous-local-execution/REVIEW.md): asynchronous
  same-machine start/observe/receive and immutable validated P/U/F snapshots are implemented,
  independently accepted and published as `a8d6463`; all six final exact-SHA CI jobs pass
  on the first run. Saved handle/live process ownership, unknown versus failure and
  publication versus completion remain distinct; existing A heads stay unchanged.
  The bounded turn is complete and stopped. [Design](iterations/07-asynchronous-local-execution/DESIGN.md),
  [example](iterations/07-asynchronous-local-execution/EXAMPLE.md) and
  [handoff](iterations/07-asynchronous-local-execution/HANDOFF.md) preserve the approved
  plan/provenance, not permission for another turn. The
  [as-built contract](../dml/docs/spec-next/asynchronous-execution.md) owns actual behavior.

- Iteration 6 [delivery](iterations/06-local-repository-execution/RESULTS.md) and
  [coordinator review](iterations/06-local-repository-execution/REVIEW.md): pinned
  A → B → A execution is implemented and independently accepted, published as
  `a0aa05d`; all six final exact-SHA CI jobs pass on the first run. The bounded turn
  is complete and stopped. Existing A heads stay unchanged; returned selected
  history is validated before atomic publication under an explicit ref.
  The [design](iterations/06-local-repository-execution/DESIGN.md),
  [example](iterations/06-local-repository-execution/EXAMPLE.md) and
  [handoff](iterations/06-local-repository-execution/HANDOFF.md) preserve the approved
  plan, not permission for another feature. The
  [as-built contract](../dml/docs/spec-next/repository-execution.md) owns actual behavior.
- Iteration 5 [delivery](iterations/05-pinned-snapshot-transfer/RESULTS.md) and
  [coordinator review](iterations/05-pinned-snapshot-transfer/REVIEW.md): pinned
  commit/full-history transfer between initialized local repositories is implemented
  and independently accepted, published as `0ec769b`; all six final exact-SHA CI
  jobs pass. The bounded turn is complete and stopped.
  The [design](iterations/05-pinned-snapshot-transfer/DESIGN.md),
  [example](iterations/05-pinned-snapshot-transfer/EXAMPLE.md) and
  [handoff](iterations/05-pinned-snapshot-transfer/HANDOFF.md) preserve the bounded
  approved plan, not additional feature authorization.

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

The user approved Iteration 8's bounded
[design](iterations/08-caller-recorded-requests/DESIGN.md),
[worked example](iterations/08-caller-recorded-requests/EXAMPLE.md) and
[conditional handoff](iterations/08-caller-recorded-requests/HANDOFF.md), and requested a
local checkpoint including accumulated Iteration 7 delivery/review notes. The approved
plan explicitly records Q in A under atomic submission/request refs, transfers pinned
Cq/Q, then registers Q locally in B and atomically creates only T before existing execution.
Exact expected Q extends both synchronous/asynchronous validation; existing A heads and
request refs stay unchanged during return. Public builder/first-attempt seams avoid private
local access or pretending first dispatch is retry. Bootstrap has no selected T while caller
already knows Q. No global replay/exactly-once capability claim. See
[approval checkpoint](discussion.md#iteration-8-plan-approval-and-design-checkpoint).

Approval selects the plan, not implemented behavior or implementation/delegation GO.
Illustrative API/format spellings remain refinable. Planning/approval inspected clean
`a8d6463`; no implementation/spec edits, tests/prototypes, worker restart/assignment or CI.
The checkpoint preserves the accumulated delivery and planning notes; earlier uncommitted/
pending-approval statements retain provenance. No implementation commit/push permission
or design push; do not inherit Iteration 7's completed authorization.

Iteration 7 is implemented, independently accepted and published as `a8d6463`; all
six final exact-SHA CI jobs pass on the first run. The bounded turn is complete and
stopped. The separate explicitly imported exchange helpers start one fixed installed
worker, observe coherent pinned P/U/F history and receive selected validated packets
under explicit A refs without moving existing heads. Saved observation identity is
separate from application-owned live process reaping; fresh clients can exit/reobserve
without relaunching. P/U is working evidence, F is done only after validated recorded
computation/separate cleanup has been retrieved. Unknown never becomes failure merely
from worker exit or elapsed time. No unowned detached lifetime guarantee.

Worker and coordinator fresh standard `-v` checks pass: 831 Python tests, seven C
executables, 2013/2013 Python statements and unchanged native/memory gates; 141 native
CLI Valgrind processes pass. Coordinator's separate installed workflow passes 208
independent checks. Real process barriers, typed-byte oracles, coherent ref races,
concurrent readers, late successful-new-put rollback and genuine post-F profile overflow
are exercised. Host coverage is not installed-child coverage; trust/capture, process,
profile, precise exclusions/runtime suppressions and Python mutation-tool gaps remain
qualified in [RESULTS](iterations/07-asynchronous-local-execution/RESULTS.md) and
[REVIEW](iterations/07-asynchronous-local-execution/REVIEW.md). The
[as-built contract](../dml/docs/spec-next/asynchronous-execution.md) owns actual behavior.

Reviewed 22-file implementation is clean at published `a8d6463`, remote master matches;
[exact-SHA CI](https://github.com/micha/dml/actions/runs/40602956772) passes all six jobs,
no fix needed. No extra worker, release/tag/package publication, cloud/global tooling,
automatic recovery, detached service or later feature turn. Delivery/status notes are
included in the requested local design checkpoint; no design push requested and this
repository has no remote. Earlier planning/GO statements preserve provenance, not
permission to restart the completed worker.

Iteration 6 implements one pinned step in independent local B and exact recorded
history return to A. The separate explicit `daggerml.exchange` layer composes public
prepare/execute/receive stages over unchanged local execution and transfer. Requests
and attempts originate in B; fresh retained one-shot workspaces prevent implicit
reexecution. Receive compares caller-owned selection/token and validates the selected
completion in disposable storage before atomic explicit-ref import. A's existing heads
stay unchanged; no adoption or merge. The
[as-built contract](../dml/docs/spec-next/repository-execution.md) owns actual behavior;
[RESULTS](iterations/06-local-repository-execution/RESULTS.md) and
[REVIEW](iterations/06-local-repository-execution/REVIEW.md) qualify evidence/limits.

Worker and independent coordinator fresh default checks pass: seven C executables,
609 Python tests, 1,639/1,639 Python statements and unchanged retained C coverage/memory
gates; 141 native CLI Valgrind processes pass. Coordinator's separate installed
workflow passes 73 independent checks. Typed wrong-history rejection, real map-full,
late rollback with successful new puts, safe process-loss barriers, recorded failure/
evidence/cleanup, pin/head preservation and offline packet receive are exercised.
Host-helper coverage is not installed-child coverage; narrow existing exclusions/runtime
suppressions, unavailable Python mutation tools, finite local process/platform and
trust/full-environment/profile limits remain qualified.

Reviewed 16-file implementation is committed/pushed as `a0aa05d`; all six jobs in
[exact-SHA CI](https://github.com/micha/dml/actions/runs/40593738345) pass on the first
run. Implementation tree/index are clean and remote master matches. Implementation,
review and publication/CI are complete and stopped. No extra workers, release/package
publication, cloud experiments, automatic recovery/retry, merge/adoption, reuse/facets,
resources/observer work or later feature turn. Delivery notes are included in the
user-requested local design checkpoint alongside Iteration 7's unapproved candidate
plan. Earlier uncommitted/preparation/authorization statements preserve chronological
provenance, not current permission to restart.

Iteration 5 implements pinned DML commit transfer with complete all-parent typed
object closure between local repositories, preserving IDs/bytes and computational
occurrences, with optional atomic destination-ref creation and ordinary Python/CLI
inspection. A narrow public packed-record insertion wrapper reuses native validation;
the separate transfer module uses bounded JSON/base64 bundles and create-or-same-target
refs. Source refs and external resources are not transferred. The
[as-built contract](../dml/docs/spec-next/transfer.md) owns actual API/behavior;
[RESULTS](iterations/05-pinned-snapshot-transfer/RESULTS.md) and
[REVIEW](iterations/05-pinned-snapshot-transfer/REVIEW.md) qualify evidence and limits.

Worker and coordinator fresh default checks pass: seven C executables, 467 Python
tests, 1,163/1,163 Python statements and unchanged retained C coverage gates.
Expanded binding memory and 141 native CLI Valgrind processes pass; coordinator's
separate installed workflow passes 50 checks. Genuine source absence/corruption,
complete-bundle checks despite prepopulated B, late abort/ref conflict, real map-full
and pre/postcommit interruption are exercised. Host coverage is not installed-child
coverage; precise exclusions/runtime suppressions, unavailable Python mutation tools,
local wheel/runtime and trust/profile limits remain qualified.

Reviewed implementation is committed/pushed as `0ec769b`; all six jobs in
[final exact-SHA CI](https://github.com/micha/dml/actions/runs/40556958937) pass
on the first run. Implementation checkout/index are clean and remote master matches.
Implementation, review and publication/CI are complete and stopped. No remote
execution/sync, recovery/merge/thin/resumable/network/cloud,
reuse/facets, resources/observer work, extra workers, release/package publication or
later feature. The user accepted the delivery and requested a local checkpoint of
these design notes as `26c9afa` before discussing Iteration 6. Its separately approved
plan is above, not implementation approval; the requested Iteration 6 checkpoint
includes subsequent discussion/planning notes. This design repository has no remote.

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
no-remote repository. Iteration 4's stop line remains; Iteration 5 is separately
authorized above.
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
