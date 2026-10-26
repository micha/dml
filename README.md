# DML design

Exploratory, agent-first design discussions for [DML](https://github.com/micha/dml).
This repository preserves design progress separately from the implementation and
its existing draft specifications.

## Start here

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
