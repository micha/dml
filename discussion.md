# Agent-first DML design discussion — checkpoint

Latest checkpoint: Iteration 4 implementation, independent review and authorized
publication/CI are complete through `d498a6c`; all six final exact-SHA jobs pass.
The bounded local-recorded-execution turn is accepted and stopped. Iteration 3
remains published as `9b8fb71`, with all six exact-SHA
CI jobs passing. See the [resume point](#resume-point). The status narrative below
and earlier sections preserve chronological provenance.

Status: Ongoing design-spiral discussion. Feasibility studies are complete. The new
as-built specification and glossary exist. Iteration 1's minimum viable repository
and its bounded review follow-up are implemented. The local default coverage gate
passes with meaningful failure tests and documented no-value exclusions. The
reviewed follow-up and URI correction are published as `6ee9329`; all six jobs in
its exact-SHA GitHub CI run pass. Publication is complete. Iteration 2's usability
direction is agreed, and its detailed candidate design/handoff have been reviewed.
The user authorized bounded Iteration 2 implementation in a fresh Pi session in
window 2, with coordinator monitoring and review fixes. That agent implementation
is now finished: the linked low-level Python repository API and inspection-only
native CLI are implemented. Worker and coordinator independent default checks and
local installed workflows pass. Mutation survivors/platform/finalizer limits remain
qualified. Implementation and independent coordinator review are complete. The user
subsequently authorized publication; Iteration 2 is pushed through `e253249` and
its exact-SHA Actions run passes all six jobs after bounded Windows fixture fixes.
Work is stopped for review. See the
[coordinator review](iterations/02-repository-usability/REVIEW.md) and
[publication checkpoint](iterations/02-repository-usability/RESULTS.md#publication-checkpoint).

## Scope and separation

This is user-led exploratory design work, not an amendment to the existing DML
specification. The old `docs/spec/` suite remains unchanged. Later in this discussion,
the user authorized `../dml/docs/spec-next/` and then code changes in `../dml` for
Iteration 1; see the resume point for current scope. The user previously authorized
moving these notes from `/tmp/dml-tasks/agent-design/` into the separate Git repository
`/work/repos/micha/dml-design` and making a local checkpoint commit. Future design
notes belong here unless the user directs otherwise.

The discussion is chronological: later clarifications supersede earlier framing where explicitly noted. Existing DML specs can supply context, but are not authoritative for the new design explored here. See the [resume point](#resume-point) for the latest direction. Original task instructions and acknowledgement are preserved under `archive/` as historical context, not active instructions.

## User-stated goals and design direction

### C core and Python orchestration

- The user values C because it is simple and understandable to them and can produce efficient, fast programs.
- Agents would design experiments and implement them as Python scripts using the DML library.
- Python supplies loops, conditionals, exception handling, and other orchestration control flow.
- A script can launch a pi agent for steps requiring reasoning.
- The example `/work/admin/experiments/graphify-delivery-world/` illustrates the kind of agent-led research being done. Its graph-related subject was coincidental, not a requirement for DML research workflows.

### Research inspection

- A central problem is verifying that agents used appropriate data and methodology: primary sources rather than trusting a README, trial measurement and comparison procedures, scoring methods, etc.
- Visualizations generated from recorded computational graphs are a desired human-facing benefit.
- The user favors a relatively low-level DML that records computational steps, rather than a research-policy engine.
- Agents should assess reproducibility by inspecting the available history in light of the current objective. Predefined reproduction-objective schema fields may overspecify the core.
- Assumptions about external-resource integrity belong at the research-project level, maintained by the user and agents outside DML itself.

### Resources, intent, and implementation

- Resources are generally URIs identifying data outside the DML LMDB store.
- A stable URI can represent the intent of a computational step, such as summing two arguments.
- Its current implementation is represented by another URI.
- The association between intent and implementation is versioned through DML commit history.
- Implementation changes may correct defects or change execution mechanics, such as moving a local implementation to an AWS Batch job for scale.
- Both kinds of change must be supported; changing implementation does not necessarily mean earlier results are incorrect.

### Immutable history and implementation lifecycle

- Results obtained from a buggy implementation remain useful historical results and must be preserved immutably.
- An implementation can be deprecated and a successor installed for future work.
- Implementation selection is scoped to branches/commits, allowing projects to adopt successors at different times.
- Agents must be able to discover deprecations and successors in commit history to understand historical research.
- The reason for supersession should structurally distinguish a correctness fix from an operational replacement, rather than rely only on descriptive prose.
- The exact representation and categories have not been settled.

### Project Git workflow

- The user proposes a well-known project entry point, illustratively `experiment.py`, executed after a Git commit.
- Execution may occur in a clean worktree to avoid ambiguity from ignored or uncommitted files.
- DML reuse/caching should avoid unnecessary duplication when the script runs again.
- Retaining selected executions of unchanged agent steps was considered a reasonable default, with explicit means to request fresh work.
- Python should permit explicit identification of a step as impure.
- An existing pure step can be rerun instead of using its cached result.
- There should be an option to adopt that fresh execution as the newly selected cached result, without rewriting historical snapshots.
- Exact hook, runner, concurrency, Git–DML association, and selection semantics remain open.

### Recursive computational model

- The user clarified that a node is either a sub-DAG or a primitive built-in operation, such as “put datum.”
- Sub-DAGs bottom out in DML primitives.
- A second execution produces a new result DAG; the assistant's earlier hypothetical about mutating a call node's downstream value should not be treated as the intended model.
- The user proposes that primitives can imply purity. Agent invocation does not need to be a primitive.
- Discussion explored a coherent separation between pure internal DAG primitives and potentially impure external resource execution returning a result DAG. Exact structural and execution semantics still need development.

### Reusable computational steps — checkpoint topic

The user wants DML to encourage reusable computational steps to minimize churn across successive trials and experiments. Reuse can increase confidence as steps establish empirical track records.

This is an important core concept and requires focused design work before selecting a representation or API.

## Subsequent discussion: reusable steps and execution closures

### Existing-spec context, not new approval

The existing draft describes execution adapters and repository remotes for input snapshot and result-DAG exchange. Local execution is intended to use the same protocol through `file://` remotes. This is relevant context, not a decision to retain every detail of the current spec.

### Candidate closure model

The user proposed a computational step's “closure” containing intent identity, implementation, and execution adapter. Discussion noted that implementation and adapter are coupled through an execution contract; configuration may also be necessary to make the binding executable. “Closure,” “resolved step,” and “implementation package” are provisional terms, not selected schema or API names.

The assistant proposed distinguishing requested intent, resolved execution closure, and individual execution. A recorded closure would be a declared binding, not proof of complete environmental capture. Closure representation, resolution, configuration scope, and exact identity remain open.

### Latest direction: orchestration versus computational history

The user clarified that the experiment Git repository's main value is providing a structured way to drive and evolve the experiment. The DML repository plus external resources provides the reproducibility basis and history of what has been done.

Resource URIs can refer to code, dependencies, datasets, and execution machinery in different external repositories or services. The experiment Git repository is therefore not necessarily the container of all computational dependencies.

The discussion separates:

- Experiment Git repository: evolving orchestration program, methodology, configuration, and project policies.
- DML repository: immutable computational history and selected resource/implementation bindings.
- External resources: actual code, dependencies, data, and execution machinery, whose integrity and availability remain project-level concerns.

A Git association identifies the program that drove the work, not its complete computational closure. Re-executing an old orchestration program and reproducing a recorded computation are related but distinct operations.

The emerging recommendation is to treat one DML repository per experiment Git repository as a possible workflow convention, not a fundamental core-model constraint. The exact default and support for sharing/splitting repositories have not been decided.

### Conceptual agreement: peer interfaces

The user and assistant agreed that DML benefits from both a `dml` CLI and Python bindings. They should be peer interfaces to the same underlying concepts and semantics, rather than one being a crippled version of the other. Python supports experiment authoring and control flow; the CLI supports user and agent entry, discovery, inspection, repository operations, and workflow invocation. Different interface ergonomics need not imply reduced underlying capability. Exact commands and APIs remain open.

### Conceptual agreement: side-by-side implementations and reuse

The user proposed and then agreed with the following direction:

- One intent URI can have multiple implementations available side by side, rather than only one current implementation.
- An agent can select an implementation for a particular step without losing caching benefits.
- Each selected implementation closure can support reuse of its own pure computations with matching inputs.
- Cross-implementation reuse is a separate, optional capability requiring an explicit basis for treating results as interchangeable; it is not necessary to support side-by-side implementations.
- Independent validation must not be defeated by reusing the other implementation's result. Selecting an implementation to perform an independent check requires fresh execution rather than cross-implementation cache substitution.
- A successor can become the default while a predecessor remains selectable for reproduction or comparison. Deprecation does not erase historical implementations or executions.
- Provenance should preserve the requested intent, selected closure, actual execution or recorded execution reused, and result DAG.

This is conceptual design agreement only. No implementation, repository documentation change, schema, or API has been approved. Defaults, selection policy, equivalence declarations, closure identity, and deprecation mechanics still need design.

## Assistant suggestions, not approved decisions

- Separate purity classification, requesting a fresh execution, and adopting that execution. Avoid overloading a single cache flag with all three meanings.
- Preserve both requested intent and actual implementation in execution provenance.
- Distinguish inspecting a historical snapshot from viewing that history with later deprecation knowledge.
- Consider queryable lifecycle relationships rather than relying on commit-message interpretation.
- Use project Git identity as research context, not automatically as an input to every computation or a global cache-busting key.
- Let a hook submit work to a separate runner rather than embedding long-running orchestration in the hook itself.
- Possible reuse support: discoverable intent URIs, input/output contracts, accessible execution history, and validation evidence recorded as ordinary research DAGs.
- Cached-result reuse does not constitute another independent empirical observation. A step's track record should preserve which implementations and conditions supplied the supporting evidence.
- Avoid assuming a new implementation inherits all confidence in its predecessor or assigning a built-in universal confidence score.

## Corrections and unresolved boundaries

- Do not frame the Graphify example as a request for code-navigation graphs.
- Do not equate every implementation change with invalidation of previous results.
- Do not overwrite, erase, or retroactively reinterpret research history when adopting successors or new executions.
- Do not assume external agent invocation must be a DML primitive.
- Do not assume that a recorded dependency graph proves complete input capture or sound reasoning; project-level assertions and observable evidence remain distinguishable.
- The current draft's node kinds (`LITERAL`, `IMPORT`, `CALL`, `BUILTIN`) and its execution/pinning behavior are context, not approved constraints on this exploratory model.
- The relationship between sub-DAG identity, returned result identity, execution identity, and selection remains to be made precise.
- Exact cross-implementation reuse rules, deprecation effects on future selection, and explicit old-implementation execution remain open.

## Worked example checkpoint

The user agreed to explore a small worked example to clarify identities and history operations. The assistant presented the following illustrative sequence. Names and behavior are exploratory, not an approved API or schema; the user requested a checkpoint before answering its identity question.

### Example: sum two integers

1. A stable intent URI has Local-v1 and Batch-v1 closures available side by side. Each combines an implementation and a compatible execution adapter. Local-v1 is the default. Sharing intent does not by itself authorize cross-implementation cache reuse.
2. A request using Local-v1 with arguments 4 and 7 produces execution E1 and result DAG R1, rooted in 11. A later matching request reuses E1, recording reuse rather than counting another independent trial.
3. A forced execution E2 also produces 11. Its result DAG may have the same content-addressed identity as R1. The script can retain E1 as selected or adopt E2 in a new snapshot; earlier snapshots remain unchanged.
4. Selecting Batch-v1 executes that closure unless a separately justified cross-implementation reuse policy applies. Later matching Batch-v1 requests can reuse its own execution. Independent comparisons must actually execute the implementations rather than substitute the same cached result for both.
5. A later defect is discovered in Local-v1: it incorrectly clamps negative arguments to zero, yielding 4 for inputs 4 and -7 instead of -3. A new commit records a correctness deprecation, installs Local-v2 as successor/default, and preserves all earlier implementations, executions, and research results. Agents can assess affected history using the recorded defect scope; results are not silently replaced.

### Newly exposed open requirement

Distinct execution attempts need to remain distinguishable when result DAGs are content-identical if their empirical track records are to be inspected. The resumed discussion below agrees on explicit occurrence identifiers; their generation and persistence mechanics remain open. Do not assume the existing exec-record schema already distinguishes identical attempts.

### Original pending question — now answered

The user agreed that resolving an intent to a selected closure produces an explicit recorded binding before execution. Intent, selected closure, and inputs should remain inspectable on cache hits and failures to start as well as successful execution.

## Resumed discussion: occurrence identity and reuse policy

These are conceptual agreements, not approved schemas, APIs, or implementation work. This section supersedes earlier purity-based framing and the original pending question.

### Requests, attempts, and observations

- Each request is a distinct recorded occurrence, even when its binding and result match earlier requests.
- A request may start a fresh attempt or reuse a historical attempt. Reuse is not another independent execution or empirical observation.
- Fresh attempts with matching closure and inputs can provide evidence of consistency or reveal discrepancies. Interpretation remains research work; DML does not certify scientific soundness.
- A discrepancy should be discoverable, but does not automatically deprecate an implementation or change the selected reusable execution. Observation, adoption, and implementation lifecycle are separate.
- Request and attempt history is recorded at reusable computational-step boundaries, not separately for every primitive invocation inside a result DAG.

### Reuse behavior, not a core purity classification

- The user clarified that the intended purity declaration was really a default cache-behavior setting. The emerging model uses reuse-by-default or execute-by-default on the intent, without requiring a core purity concept.
- Callers may override the default, including disabling automatic reuse for a selected closure, requesting fresh execution, or deliberately reusing a specified historical execution regardless of the default.
- Fresh execution and adoption as the selected reusable execution remain separate choices. Exact APIs and initial-selection behavior are open.
- Selection is branch/commit-scoped repository state. Different branches can select different executions for the same closure and inputs without rewriting historical snapshots.

### Foundational versioning constraint

- The user emphasized that all recorded research state is immutable, versioned repository state, not just reuse selection. This includes intent definitions, closures, bindings, requests, attempts, outcomes, reuse choices, lifecycle information, and evidence.
- Mutable heads and similar navigation references are exceptions, not mutable research records.
- External-resource references and recorded assertions are versioned; external contents are not necessarily stored in DML.
- Preserving recorded history does not itself guarantee complete capture of external events.

### Explore ordinary DAG representation first

- The user agreed to explore requests, attempts, and outcomes as ordinary DAGs built from DML primitives before introducing dedicated core record types. This is an exploration direction, not a finalized representation.
- The user agreed to explicit occurrence identifiers for requests and attempts, stored as ordinary data. Otherwise-identical occurrences remain distinct, while bindings, inputs, and result DAGs can still deduplicate.
- Repository history records evolving knowledge about an occurrence without changing its identity. An illustrative lifecycle is separate commits recording that attempt A was requested, started, and completed with result R. The exact lifecycle and commit boundaries have not been selected.
- Copying or referencing an attempt does not create a new attempt; a new record about an attempt need not be a new attempt.
- Identifier generation, collision handling, validation, and lifecycle consistency remain open. The assistant favored opaque identifiers rather than timestamps as identity, but no identifier format was selected.

### Interruptions and retries

- The user agreed that one request can have multiple attempts, including attempts whose outcomes remain unknown.
- The illustrative sequence records request Q and its resolved binding, then attempt A before invoking the external executor. If the orchestrator crashes before recording an outcome, A is not automatically treated as failed.
- Recovery may discover success, failure, or remain uncertain. A retry creates a new attempt B linked to Q instead of replacing A.
- Recording an attempt before dispatch is not proof that the external executor started. Exact dispatch, acknowledgement, recovery, and lifecycle representations remain open.

### Adapter lifecycle and polling — latest agreement

This supersedes the assistant's earlier suggestion to avoid all shared core lifecycle states.

- The adapter owns execution mechanics and may call other tools. DML facilitates storing opaque adapter state linked to an attempt in immutable, versioned history.
- The user proposed bounded adapter invocations that return the current lifecycle state and exit, rather than polling internally. Polling can be driven by scripts, CLI runners, schedulers, agents, or other drivers.
- The agreed shared states are `working` and `done`. A separate `created` adapter state is unnecessary: the attempt record establishes existence, and before the first adapter response there may be no recorded adapter status.
- `working` means no final outcome has been recorded yet. `done` means execution has completed and its result or failure has been recorded. External completion alone is insufficient if retrieval or recording remains unfinished.
- Result or failure is separate from lifecycle status. The polling driver decides whether to proceed, abort, retry, or investigate; the adapter does not impose experiment policy.
- Polling and status-query retries are observations about an existing attempt, not additional computational trials. Submission retries can be ambiguous and require adapter-specific handling; exact recovery and internal execution accounting remain open.
- The assistant interpreted immediate exit as returning after one bounded interaction rather than requiring zero-duration external calls. Exact interfaces, persistence/commit ownership, and acknowledgement semantics remain open.

### Incrementally published execution sub-DAG

- The user agreed that recovery mechanics belong to the adapter, without a DML guarantee of exactly-once external execution.
- The user expects recovery to fall naturally out of the design because the execution sub-DAG is pushed to the DML remote (or local) repository as actual work is done.
- Execution history is therefore not necessarily recorded only by the polling adapter. Incremental publication should be explored as the basis for progress inspection and recovery.
- Exact publication/ref conventions, discovery by attempt identifier, synchronization, and gaps between external effects and their recording remain open.
- The user clarified that adapters can record external job identifiers and other recovery/cleanup information in the attempt history.
- The adapter is expected to attempt its own cleanup before returning `done`. The subsequent agreement below allows explicit cleanup failure rather than requiring successful cleanup for lifecycle completion.

### Explicit cleanup failure and out-of-band maintenance

- After considering the tradeoffs, the user agreed to explicit cleanup failure. Keeping an attempt `working` does not ensure another adapter invocation: its driving process may abort or crash.
- `done` means the computational outcome and the adapter's final disposition are recorded. The adapter attempts required cleanup before returning `done`, but may report an explicit cleanup failure.
- Computational and cleanup outcomes are separate. A successful computation can coexist with failed cleanup without losing or reclassifying its result.
- Recorded job IDs, resource references, and cleanup information support a general out-of-band maintenance process, rather than relying on the original experiment driver to remain alive.
- Maintenance should also be able to investigate interrupted attempts with unknown cleanup status, not just explicit cleanup failures.
- Later remediation adds immutable history linked to the same attempt. It does not rewrite the original outcome or create a new computational attempt merely by cleaning up resources.
- Exact cleanup outcome representation, maintenance discovery/coordination, and remediation interfaces remain open.

### Resource datums and optional history-rooted garbage collection

- The user proposed first-class resource datums associated with execution attempts. Resources are project-owned/managed or owned by an external authority; project-owned resources can be eligible for cleanup.
- The user clarified that "no longer referenced" means not reachable from any head, including the full commit history rooted at those heads, not merely their current snapshots.
- The intended workflow permits explicit disposal of low-value, expensive research: do not retain it in merged history, or potentially rebase it away if rebasing is supported, then run an optional repository GC pass.
- Reachable history preserves its resource associations and retention. Intentional removal of history from all heads can make associated project-owned resources collectible; externally owned resources are not deletion targets merely because they are unreachable.
- This qualifies the earlier preservation principle: immutable records are not rewritten in place, but the user may explicitly discard unrooted research history through GC. Rebase support is not decided.
- The user agreed that GC must preserve enough resource information to complete or retry external cleanup before deleting the corresponding datums, avoiding untracked leaks after failed deletion.
- An unmerged experimental branch still retains its history while its head exists. Collection requires that no head retains the discarded history.
- Exact resource schema, adapter publication responsibilities, additional GC roots, failed external deletion recovery, and the relationship to adapter cleanup remain open. This proposal may revise the prior cleanup model; it is not a finalized implementation design.

### Resource managers and shared resource-management history

These are exploratory directions, not implementation approval.

- The user proposed registered resource adapters that make the resource-manager implementation opaque to DML. Terraform/OpenTofu is a concrete candidate, not part of the DML C core.
- Provider-qualified resource types and their schemas could supply an external-resource type vocabulary and contribute to resource URIs. Exact type/instance identity and URI schemes remain open.
- The user proposed versioned external-resource repository data separate from research history. Its current configuration could describe the complete research-managed resource collection, like a single Terraform/OpenTofu root module or stack.
- Multiple research repositories could associate with one resource-management repository, centralizing lifecycle operations, visibility, and out-of-band cleanup.
- The user highlighted resource dependencies that affect create/update/replace/destroy ordering. Specialized manager planning is therefore relevant beyond individual deletion callbacks.
- Assistant suggestions to examine: aggregate retention requirements across associated research histories; distinguish desired configuration from observed operational state; distinguish resource-management audit history from research retention roots; preserve retained research artifacts through replacement rather than merely configuration-equivalent infrastructure.
- The user's latest inclination is to adopt OpenTofu as the first concrete resource-manager backend, behind a seam for future backends. Think concretely in OpenTofu terms to reduce premature abstraction and the explosion of possibilities. This is tentative design direction, not approval to implement or modify specs.
- Direct documentation checks confirmed non-cloud local/Docker providers and provider/dependency/state concepts. The official `tofu-exec` README currently warns that it is not usable or recommended for general-purpose use; provider SDKs and CLI automation are distinct. No tools were installed or infrastructure actions performed.

### Three resource classes and a conventional IaC Git repository

- The user identified three classes: externally managed resources; research-managed resources provisioned by OpenTofu outside execution (for example at closure creation); and research-managed resources adopted after execution (for example result objects in an externally managed bucket).
- Containment does not imply lifecycle ownership: research can manage result objects without managing their externally owned bucket. Provisioned resources can associate with closures before any attempt exists.
- The user proposed a normal Terraform/OpenTofu Git repository for resource management, retaining familiar deployment tooling and safety gates rather than inventing a new repository format.
- Root outputs could map managed OpenTofu resources to DML resource identities. Under the proposed convention, this manifest exports classes 2 and 3, not externally managed class 1 resources. The configuration may still read/reference class 1 resources.
- The user proposed tightening scope to a DML-owned resource-manager configuration, excluding unrelated modifications so conventions need not accommodate arbitrary IaC edits. Exact authorship and coordination mechanisms remain open.

### Deployment freedom — user clarification

- GitHub Actions and approval gates were examples of user/agent-selected deployment mechanisms, not systems DML should understand or orchestrate.
- A user or agent may push configuration to GitHub for a workflow to deploy, apply it using a local CLI, or use another mechanism.
- The assistant's previous characterization of these mechanisms as DML-delegated workflow components, and of operational state as exclusively written through DML's adapter, was too strong. Configuration ownership/conventions must be distinguished from deployment choice and operational state updates.
- No specific deployment backend, CI integration, or approval mechanism has been selected or approved for implementation.

### Out-of-band adoption and the IaC repository as a materialized view

- The user agreed that adoption need not provision a new real-world resource but does require registration in OpenTofu state. Direct CLI import and declarative import via plan/apply are possible; configuration alone is not operational adoption.
- The user proposed out-of-band reconciliation of DML resource records with the IaC repository/state, with DML serving as a WAL-like durable journal of management obligations. Strict write-ahead semantics for external creation and atomicity are not established.
- The user explicitly liked the IaC repository as a materialized resource-management view of DML that can be regenerated at will, rather than a competing authority over research resource requirements.
- The user suggested using Terraform HCL or a CDK-style API as the resource language spoken internally, while permitting other tool formats at materialization. Exact internal representation and translation semantics are not selected.
- This keeps the earlier deployment freedom: generating configuration is distinct from applying it, and users/agents choose their deployment mechanism.
- Operational state regeneration, resource identity preservation, pending-adoption/disposal durability, provider-version/schema capture, and safe backend migration remain open. No implementation or repository-spec changes have been approved.

### HCL storage and closure installation

- The user favored storing actual HCL: closures need the language's expressiveness, and agents can author and inspect it directly. The assistant agreed to explore faithful configuration storage rather than inventing a substitute resource language.
- The user agreed that composition is a key challenge. How closure configurations fit into a shared root, including namespacing, inputs, and provider requirements, remains open. Modules are an assistant-proposed starting point, not a selected mechanism.
- The user's current tentative idea is that research-managed, provisioned resources are created when a closure is "installed," analogous to defining a function before calling it.
- The user proposed that installation could naturally be a DAG in DML, but emphasized that the idea is half-baked and not yet worked through. Installation identity, reuse, deployment coordination, and its relationship to execution-ready closures remain unresolved.
- The user challenged the assistant's example of installing the same closure in small/local and large/shared environments: these appear to be different closures associated with the same intent, not merely installations of one closure. Resource/execution configuration must be considered when determining closure identity; exact identity remains open.

### Installation description versus resulting bound closure

- The assistant explored two models: identify a closure before installation and separately record realized bindings; or let installation produce the closure bound to actual resources.
- Both user and assistant lean toward the second model. This is tentative direction, not finalized identity or API design.
- The installation description contains implementation, execution adapter, HCL, and configuration inputs; its resulting closure includes resolved resource bindings. Distinct installation attempts may yield the same closure if their resulting contents/bindings match.
- The user noted that distinguishing what is to be installed from the resulting closure may be necessary for materializing the resource-management view, rather than an additional conceptual cost.
- Exact binding identity, partial-installation representation, stable IaC declaration identities, and which operational attributes contribute to closure identity remain open.

### Excision, tombstones, and retaining research without infrastructure

- The user proposed excision with tombstones, needed for sensitive-information removal or legal compliance, as a mechanism that could also trigger infrastructure cleanup without discarding research history.
- The user agreed to distinguish ordinary GC (unreachable resources) from authorized excision (withdrawal despite retained references).
- Historical references can resolve to tombstones indicating that a resource existed but is no longer available. Retaining provenance need not require keeping the infrastructure operational forever.
- An excision request and completed physical deletion are distinct. Reconciliation can materialize removal of research-managed resources; user-chosen deployment performs destruction and its outcome is recorded.
- Resource retirement may preserve non-sensitive descriptions and associations. Content erasure removes sensitive stored content itself, not merely its visibility in a newer commit; permissible tombstones must not retain sensitive material.
- Distributed copies/backups limit erasure guarantees. Externally managed resources remain outside DML's deletion authority.
- Exact tombstone representation, excision authority/scope, dependency and shared-consumer impact, propagation, and failure recovery remain open. No existing API/schema is assumed to implement these new semantics already.

## Authorized feasibility study

The user authorized autonomous feasibility research with specialist Pi agents in
new tmux windows, then explicitly allowed evolving and trying candidate designs.
The work is complete: [initial findings](feasibility/RESULTS.md),
[candidate iteration results](feasibility/ITERATION-RESULTS.md), and
[the fresh final audit](feasibility/final-review/report.md) preserve evidence and
limits. Narrow cooperative mechanisms work; production safety is not established.
Candidate behavior is not a new user agreement or approval to modify DML
implementation/specifications.

## Observability motivation and sidecar observers

### User-stated motivation and direction

- Agent capability increases research production faster than humans can understand
  and assess it. The bottleneck is visibility into whether the work researches what
  the human thinks it researches, not merely obtaining more agent analyses.
- Deterministic observability and visualization should expose how research is done
  without overwhelming humans. Agent summaries are not a substitute for evidence.
- Independent sidecar DAGs can import in-progress research and visualize node
  inputs, outputs and data flow. Multiple observers should coexist without the
  research producer needing to know about them.
- Uniform DAG/commit/tree/datum structure should let general observers navigate
  research without discovering each project's experiment/trial directory layout.
- The user agreed that the next experiment should observe the feasibility study
  itself, then requested a detailed handoff plan while discussion continues here.

### Assistant proposals and unresolved boundaries

- Use recursive step collapse/expansion, bounded value previews, comparisons and
  evidence links; deterministic projection should remain usable without model calls.
- Explore small shared record-role/edge conventions in ordinary DAG data. Generic
  traversal supplies structure, not domain interpretation or scientific validity.
- Following a head versus retaining an imported snapshot needs explicit treatment;
  persistent observer imports may become retention roots and rendered values are
  copies relevant to excision/privacy.
- Preserve pinned source snapshots, distinguish reuse from fresh observations, and
  label retrospective ingestion and incomplete capture rather than inventing history.
- [Observer handoff](observer-study/HANDOFF.md) proposes staged corpus curation,
  a model-backed generic reader, deterministic presentation, progress replay,
  a second producer, human evaluation and independent audit. This is a plan,
  not an approved production schema or a directive to start implementation now.

## Researcher control and inspectable limits

### Conceptual agreement

- Sidecar observers are ordinary external consumers enabled by DML's core
  functionality, not a DML subsystem or feature. Do not add observer-specific
  registries, hooks, logging channels or mandatory producer integrations.
- Recording a computational step naturally exposes its recorded boundary inputs
  and result relationships. Internal visibility depends on what is represented as
  further sub-DAGs; external execution can remain opaque to DML.
- An agent can inspect the implementation code/configuration identified by a
  closure and reason about behavior DML itself does not interpret. Inspecting code
  does not establish which external values a particular execution received.
- The researcher controls the degree of observability and reproducibility. This
  flexibility is a feature; DML supplies mechanisms, not a research-policy engine
  or universal completeness requirement.
- DML should nevertheless preserve structural distinctions that make the basis
  and boundaries of recorded evidence inspectable. Readers should be able to assess
  what history supports without mistaking unrecorded events for events that did
  not happen.
- DML cannot automatically expose an undeclared dependency it was never told about,
  prove complete capture, or certify scientific validity. Deterministic tools expose
  recorded structure/values; agents interpret code and methodology; humans judge
  the evidence and conclusions.

### Illustrative distinctions, not a selected schema

Captured values versus external references; explicit code versions versus moving
references; recorded internals versus opaque boundaries; fresh attempts versus
reuse; recorded failure versus unknown outcome; retained versus unavailable or
excised data. These examples express the agreed criterion, not mandatory fields or
new core record types. A mechanism failing its stated capture contract is distinct
from a researcher intentionally choosing less capture.

## Observer Stage 0 checkpoint

The user reported completion of the observer study. Its
[results](observer-study/RESULTS.md) and [independent recheck](observer-study/review/RECHECK.md)
accept **corpus curation only**: five stories, explicit gaps, 39 passing corpus tests
and 16 correctly rejected malformed-input probes after correction. No graph reader
or UI has been implemented. Retrospective curation cannot recover facts that the
original executions did not capture. That limitation is not itself a requirement
for additional observer machinery in DML.

## Execution environments and identity facets

The user requested a checkpoint commit before continuing; `021b077` records the
preceding design notes, feasibility work and Observer Stage 0 corpus. The following
is subsequent conceptual discussion, not an approved schema or implementation.

### Clarification: execution always produces a sub-DAG

- Executing a DML node produces a result sub-DAG. An external Python program either
  builds it using DML, just as the top-level program does, or its adapter wraps the
  returned result in a DAG. A bare external value is not the DML execution result.
- The researcher designs programs and adapters to record the desired detail.
  DML needs no special observability facilities for this: ordinary DAG construction,
  publication and inspection suffice. The assistant's earlier boundary/internals
  framing conflated viewing a sub-DAG at different levels with unrecorded external
  computation; it does not establish separate execution modes or capture policies.

### Proposed execution environment

- The user proposed building and committing the execution sub-DAG under a repository
  ref, illustratively `exec/<execution-id>`. Exact naming and whether this identifier
  denotes an attempt remain open; separate per-attempt refs are an assistant suggestion.
- Explicit arguments are input nodes. Implicit arguments are dependencies captured
  when the intent is created; closure-level dependencies are also being considered.
- Intents and closures are created by a DAG built on a specific commit and included
  in a new commit. Their node references are within that resulting commit, including
  nodes carried forward. A separate source-snapshot pin is not needed merely to fix
  these captured bindings. Transfer into the execution environment remains open.
- The user proposed named and anonymous DAG nodes, with a built-in named-node lookup,
  and potentially requiring arguments/dependencies to be named. Explicit lookup scope
  was provisionally accepted. Separate argument/dependency namespaces and exact lookup
  syntax remain illustrative.
- Caller and callee synchronize through a DML repository remote. Published progress
  is discoverable by involved parties and supports recovery. Launch/publication gaps,
  ref ownership, completion, bootstrap and synchronization semantics remain open.
  Published history is evidence of recorded progress, not exactly-once external effects.

### Conceptual agreement: purpose-specific identity facets

- The discussion now treats full-record identity and reuse/cache identity as two
  facets derived from a node's recorded description, rather than one universal node
  identity plus an exceptional cache key. Additional facets should be motivated by
  concrete operations, not invented in advance.
- The user proposed dimensions and a mask: reuse identity can ignore a dimension
  by substituting a canonical sentinel/NULL before hashing. For example, distinct
  adapter bindings may intentionally share reuse identity. Actual bindings remain
  recorded; ignored does not mean unknown.
- The user agreed that the mask contributes to full node identity. Exact facet
  names, dimension sets, mask ownership/defaults and encoding are not selected.
  Whether all future facets are expressible as masks remains open.
- Equality under one facet has a purpose: reuse equality does not imply full-record
  equality, universal substitutability or another independent observation. Request
  and attempt occurrence identifiers continue to distinguish events even when their
  computational facets match.
- The assistant's prior suggestion to use the full invocation DAG identity directly
  as the reuse key was corrected: a full closure identity could indirectly preserve
  an ignored adapter's contribution. Facet derivation must respect the intended
  projection rather than simply hashing opaque full identities.
- A reused attempt may have different actual bindings in ignored dimensions. Preserve
  the current request's binding and the historical attempt's binding rather than
  treating a shared reuse identity as proof that those records are identical.

## Design spiral and pre-1.0 compatibility policy

- The user proposes developing the full functionality incrementally through a
  design spiral rather than requiring a complete up-front design. The assistant
  suggested concrete vertical slices: design enough for a workflow, prototype it,
  exercise failures, review evidence, and revise. The proposed slice sequence is
  not an approved implementation plan.
- The user favors minimal feature prototypes and more iterations, incrementally
  building toward final functionality. Iterations can go broad to explore integration
  or deep to develop a particular capability, whichever is useful; completing or
  hardening each layer before exploring the next is not required. Prototype shortcuts
  and untested behavior must remain distinguishable from demonstrated functionality.
- The user explicitly directs that DML repositories and other DML development
  state be treated as ephemeral until `v1.0.0`. Spiral iterations should not require
  version increments, data migrations, or backward-compatibility machinery merely
  to accommodate evolving designs. Incompatible development state can be recreated.
- This is a development compatibility policy, not a deletion command or an exception
  to immutable-history semantics within a repository. It does not authorize deleting
  unrelated data, weakening resource-cleanup obligations, modifying the implementation
  checkout, or launching further observer stages.
- Exact post-1.0 compatibility guarantees remain open; this policy establishes the
  absence of a pre-1.0 persistence/compatibility obligation, not a migration design.

## New as-built specification and first-iteration scope

- The user corrected the assistant's initial execution-oriented iteration as too
  ambitious. The first iteration should instead implement a minimum viable repo:
  simplified entities as needed, immutable snapshots, a commit graph and refs pointing
  to commits. Merge, rebase and other advanced repo operations are unnecessary.
  Execution, intents and closures are deferred. Exact implementation scope/location
  still needs approval.
- The user requested a new specification describing actually implemented behavior,
  following the existing documentation guidelines, with `AGENTS.md` for agents and
  `README.md` for human orientation, including a Mermaid document/reference map.
- The user selected `/work/repos/micha/dml/docs/spec-next/` and explicitly authorized
  creation of that new documentation directory. The old `docs/spec/` suite remains
  untouched. This authorization does not extend to implementation changes.
- The initial as-built documents cover the already implemented datum/record foundation
  and LMDB local storage API, inspected at `638cc42`; they do not claim that the first
  iteration has been implemented. Existing tests were inspected, not freshly rerun.
  Technical documents should grow with implemented capabilities rather than serving
  as an up-front design of future subsystems. The user clarified that documented
  functionality itself defines the implemented scope; the spec should not maintain
  a separate "what does not exist yet" inventory. The initial inventory and
  first-iteration planning text were removed from its README, and its agent guidance
  records this convention. See
  [the new spec orientation](../dml/docs/spec-next/README.md).

## Shared glossary and vocabulary policy

- The user requested a glossary before the first implementation iteration and agreed
  that maintained documentation should use its vocabulary consistently. Design
  conversation should follow those terms on a best-effort basis; informal wording
  is sometimes useful and does not need rigid enforcement.
- The [glossary](../dml/docs/spec-next/glossary.md) owns the working terminology.
  At the user's correction it lives with the spec, not in this design repository.
  Provisional meanings are
  marked, and an entry does not claim that its concept is implemented. Technical
  behavior remains owned by the as-built spec. New definitions are a draft of the
  discussion so far, not approval of additional schema or protocol decisions.
- Design and spec agent guides now require consistent documentation vocabulary and
  preserve historical wording in archives, quotations and frozen evidence. The
  as-built spec links to the glossary rather than duplicating it.

## Iteration 1 handoff and implementation authorization

- The user requested a detailed handoff, then explicitly authorized code changes
  to `../dml` for the minimum-viable-repository iteration. This supersedes the earlier
  documentation-only authorization and pending-location discussion for this turn.
- [Iteration 1 handoff](iterations/01-minimum-viable-repository/HANDOFF.md) records the
  scope, suggested implementation approach, validation, as-built documentation work,
  acceptance workflow and stop line. Its representation/API recommendations are
  not a finalized schema; the implementation should stay minimal.
- This handoff preparation did not start implementation. No execution, intent/closure,
  reuse, remote, merge/rebase, GC/excision, resource-management or later observer
  work is authorized by this iteration's scope.

## Iteration 1 implementation delivery

- The user instructed implementation to begin. The bounded turn now supplies
  literal nodes, rooted DAGs, canonical named trees, ordered-parent commits and
  transactional refs in the native C/LMDB foundation. Datum encodings and golden
  IDs remain unchanged. No later execution/resource/observer work was started.
- [Delivery notes](iterations/01-minimum-viable-repository/RESULTS.md) record actual
  representation/API choices, checks, source state and limitations. The narrow
  ASCII name profile and type-discriminated object APIs are assistant implementation
  choices, not broader user-agreed schema decisions.
- The acceptance workflow works across fresh processes, including branching,
  immutable bytes/IDs after ref movement and atomic object/ref rollback. Five C
  executables and 81 Python tests pass. Valgrind reports no errors/leaks in the
  exercised C tests and nine history-driver invocations.
- Required `scripts/check.sh -v` exits 1 at the unchanged coverage gate: 88.2%
  lines, 100% functions, 74.5% branches. The baseline also failed this gate; new
  paths are not exhaustively covered either. This is not a fully green delivery
  or a waiver of coverage requirements.
- The user subsequently requested a commit, GitHub push and Actions monitoring.
  Implementation commit `0bcfe92` is pushed to `micha/dml` branch `master`.
  [CI run 40444854493](https://github.com/micha/dml/actions/runs/40444854493)
  passed all six jobs, including Linux/macOS on both architectures and Windows.
  Each job reports 5 C executables and 81 Python tests passing. The Linux
  validation job uses `scripts/check.sh -c`, so it does not enforce percentage
  gates. Design notes remain uncommitted in this no-remote checkout.

## Iteration 1 bounded review follow-up

- The user authorized focused hardening/documentation, not new functionality or
  another feature iteration. The read-only review found no functional correctness
  defect in the new object/ref implementation. Direct rather than transitive checks,
  ASCII names, ordered parents and
  the small quadratic operations remain accepted first-turn choices.
- The user clarified that coverage is a means, not an end: narrowly justified
  no-value exclusions are permitted without case-by-case approval. Difficulty
  alone is insufficient; keep the remaining threshold, identify exact regions and
  reasons, and distinguish tested from excluded code. This supersedes the earlier
  blanket prohibition. Implementation/design guides and the handoff now record it.
- Added meaningful codec/identity/repository allocation and dependency-failure
  tests, boundary cases and rollback checks. Updated architecture and README
  orientation to the as-built spec. The retained GCC-header claim is corrected
  visibly: LF=10, LH=8 means 2 uncovered lines. Historical totals are preserved.
- Final local `scripts/check.sh -v` exits 0: 7 C executables pass under Valgrind,
  reporting no errors/leaks. The combined current tree has 86 Python tests passing:
  83 in this follow-up's suite plus 3 unrelated concurrent LSP tests.
- Retained coverage is 990/990 lines, 78/78 functions and 835/835 branches (100%).
  Marker-free diagnostic coverage is 999/1006 lines and 881/902 branches. Exclusions
  remove 16 measured lines and 67 outcomes, not entire functions; their precise
  locations and rationales are in the
  [coverage catalog](../dml/tests/coverage-exclusions.md). No claim of testing all
  excluded behavior follows from the gated percentage.
- [Follow-up delivery notes](iterations/01-minimum-viable-repository/RESULTS.md#review-follow-up)
  record commands, interrupted/failed diagnostics, measured populations and limits.
  No new commits, pushes, delegates or feature work were performed. Unrelated LSP
  changes were preserved; a concurrent Meson wipe interrupted one run, and the
  final validation was rerun after it finished.

## Final URI diagnostic correction

- The user accepted the preceding review and authorized only the remaining URI
  size-error diagnostic correction. The pre-existing implementation discarded
  `uriToStringCharsRequiredA()`'s failing code; the new fault fixture had expected
  the preceding `URI_SUCCESS`, incorrectly codifying that behavior.
- The size routine's status is now retained and reported. Its fixture injects the
  representative `URI_ERROR_OUTPUT_TOO_LARGE` and requires that exact native code.
  Cleanup and empty outputs remain intact; no exclusions or thresholds changed.
- The corrected fixture fails before the production fix (exit 1), demonstrating
  the regression. Fresh default `scripts/check.sh -v` passes afterward (exit 0):
  7 C executables under Valgrind, 86 Python tests in the combined tree, and retained
  coverage of 990/990 lines, 78/78 functions and 835/835 branches. All seven C
  processes report no memory errors/leaks. No new platform/remote checks were run.
- [Correction notes](iterations/01-minimum-viable-repository/RESULTS.md#final-uri-diagnostic-correction)
  preserve commands, historical measurements and source state. The fix is
  uncommitted; unrelated LSP and existing design changes remain preserved.

## Follow-up publication checkpoint

- The user explicitly authorized the focused implementation commit, push and
  exact-SHA Actions monitoring. The complete staged diff was inspected. Only the
  17 reviewed hardening/documentation/URI-fix files were committed; README's editor
  section and the unrelated LSP files/ignore entries remained outside the index.
- `6ee93293ea10d7950c1cdc894b18dda695c55baf` is committed and normally pushed to
  existing `micha/dml` branch `master`; push exited 0 and the remote SHA was verified.
  [CI run 40452494677](https://github.com/micha/dml/actions/runs/40452494677)
  completed successfully. Each of its six jobs reports 7 C executables and
  83 Python tests passing, including Windows and both Linux/macOS architectures.
- The Linux CI job is informational `-c`, even though its reported retained
  counts are also 990/990 lines, 78/78 functions and 835/835 branches. It does not
  replace local default `-v` evidence: 7 C executables under Valgrind and 86 Python
  tests in the combined local tree, which included 3 uncommitted LSP tests.
- [Publication notes](iterations/01-minimum-viable-repository/RESULTS.md#follow-up-publication-checkpoint)
  record actual job URLs, source/test population and remaining unstaged work.
  The design checkout remains local and uncommitted, preserving existing edits.
  No tags, releases, force pushes, account/environment changes, delegates or
  subsequent feature turn were made.

## Iteration 2 agreed direction: repository usability

The user selected a usability iteration following completion of Iteration 1.
This is agreed direction for planning, not authorization to begin implementation.
Exact Python APIs, CLI syntax, output contracts and binding mechanism remain open.

- Establish a low-level Python API over the existing C repository foundation:
  construct and read datums, literal nodes, DAGs, trees and commits; read/create/update
  refs; and use explicit storage transactions with atomic writes and abort behavior.
- Preserve the distinction between creating a DML commit and committing a storage
  transaction. Python-appropriate types, exceptions and handle management need not
  hide the repository model or duplicate its semantics.
- Higher-level conveniences can be separate layers composed over this API without
  privileged access. A higher-level experiment-authoring framework is outside this
  iteration.
- The CLI may be inspection-only for this turn: inspect objects, resolve refs,
  display snapshots and traverse commit history, with human-readable and JSON output.
  CLI mutation commands are deferred. This qualifies the earlier peer-interface
  agreement: shared concepts and semantics remain the goal, but capability parity
  is not required in this iteration. The user considers this appropriate for the
  agent-first workflow.
- The acceptance workflow uses Python to record 42, then 43 in a child commit and
  move a ref. The CLI inspects both snapshots and their history; earlier immutable
  objects remain unchanged. The script demonstrates composition rather than
  establishing a new high-level framework.
- Limit the turn to existing repository capabilities. New DAG semantics, execution,
  intents, closures, reuse, remotes and resource/observer work remain outside scope.
  Test-only corruption and fault-injection operations are not public API requirements.

The assistant's preceding Python and CLI sketches were illustrative, not selected
API contracts. In particular, CLI initialization and ref mutation from that sketch
are superseded by the agreed inspection-only scope.

### Iteration 2 detailed design and handoff preparation

At the user's request, the assistant wrote the
[candidate design](iterations/02-repository-usability/DESIGN.md) and
[implementation handoff](iterations/02-repository-usability/HANDOFF.md). Agreed scope
is distinguished from proposed exact APIs, wrapper restrictions, JSON and build
choices. Proposed refinements include typed `Datum` read results, fail-closed write
contexts, a typed `show` command and one native CLI implementation forwarded by the
Python console entry. Those refinements are not separately user-approved decisions.

Preparation inspected the implementation checkout at clean `06bf66e`, which follows
Iteration 1's `6ee9329` and commits the separate language-server setup. Earlier notes
about unstaged LSP work remain historical. No implementation files were changed and
no test/build suite was run. Implementation authorization was pending at preparation.

### Iteration 2 implementation authorization

After reviewing the summary, the user authorized the existing agent in window 2 to
implement this iteration in a new Pi session (not a new tmux session). The coordinator
is to monitor, independently review, give feedback, and have issues fixed until the
work is satisfactory, then report. This authorizes the bounded implementation,
local validation and review fixes described in the handoff. It does not authorize
commits, pushes, package publication, additional workers or later feature turns.

## Iteration 2 delivery and review checkpoint

- [Delivery notes](iterations/02-repository-usability/RESULTS.md) record actual
  selected APIs, capsule ownership/deferred thread-safe cleanup, root native build,
  package-relative forwarding, all changed files and bounded validation.
- Worker and coordinator fresh default `scripts/check.sh -v` both exit 0: 7 C
  executables, 249 Python tests, Python 399/399 statements, retained C 1555/1555
  lines, 125/125 functions and 1409/1409 outcomes. Excluded dependency/invariant
  populations remain distinct from tested code, with unchanged thresholds.
- Binding supported-lifetime memory workload reports zero unsuppressed errors;
  runtime-only and full-workload retained heaps match with narrow CPython runtime
  suppressions. Sixty native CLI Valgrind processes pass, including large full-JSON
  buffer growth. Unsupported foreign-thread last-owner destruction intentionally
  abandons native resources with a warning; it is not leak-free finalization.
- Public Python constructs 42/C1, 43/C2/ref movement and a fork; fresh processes
  inspect snapshots/history and unchanged record bytes. Installed source-wheel and
  console work outside checkout. Coordinator independent probes and a separate
  venv install also pass.
- Regular dirty-tree VCS sdist omits new source, explicitly rejected as current
  evidence. A staged current native-source/dependency archive builds offline to the
  same wheel hash. Local `cp313-abi3` install is not earlier-Python or other-platform
  proof; declarations and the existing release interpreter matrix are preserved.
- Bounded Mull diagnostics have survivors and exit 1, not green mutation gates.
  Meaningful boundary gaps prompted small tests and memory checks. The overshift/
  logical-span mutant remains an honest oracle limitation, not called equivalent.
- Implementation HEAD remains `06bf66e` with all turn changes uncommitted. No old
  spec, schema/encoding/version, execution/resource/observer feature, additional
  worker, publication or system/global tooling change was made. The implementation
  agent is finished; coordinator review, final validation and documentation
  reconciliation are complete. Work is stopped for user review.

## Iteration 2 publication checkpoint

The user accepted the delivery and authorized commit, push and Actions verification.
The reviewed 39-file slice was committed/pushed as `ee0327f`, also publishing the
existing local LSP commit `06bf66e`. Five Unix jobs passed; Windows collection caught
a test-loader glob selecting a linker library. Test-only fix `d9a554c` added exact
interpreter extension-suffix selection. The next run exposed locale-based UTF-8
fixture decoding and POSIX fake-compiler resolution on Windows. Test-only fix
`e253249` made decoding explicit and supplied a native CMD compiler fixture, with
regressions and no disabled tests or changed thresholds.

[Final exact-SHA CI run 40467554833](https://github.com/micha/dml/actions/runs/40467554833)
passes all six jobs. A fresh local default `-v` check passes with 7 C executables,
255 Python tests, Python 399/399 statements and retained C 1555/1555 lines,
125/125 functions and 1409/1409 outcomes; the binding and 60 CLI memory processes
also pass. CI's informational `-c`, platform-specific device/pipe skips and installed
package/runtime limits remain distinct. Both failed runs and fix evidence are in
[publication notes](iterations/02-repository-usability/RESULTS.md#publication-checkpoint).

Implementation master is clean at pushed `e253249eca70ad588d918d321a54a1413447b8a0`.
No force push, tag, release, package publication, additional worker, account/system
change or later feature turn occurred. Design notes remain local/uncommitted in the
no-remote design checkout. Earlier uncommitted/no-CI statements above describe the
pre-publication review, not current implementation status.

## Iteration 3 agreed direction: composable DAGs and named-node lookup

The user agreed to the assistant's proposed next spiral turn. This selects the
bounded direction below for planning, not authorization to begin implementation.
Exact representation, encoding, APIs and CLI presentation remain open.

- Add named bindings inside a DAG, distinct from tree names organizing a repository
  snapshot.
- Provide explicitly scoped named-node lookup against a supplied DAG. Lookup neither
  executes a node nor converts it to a Python value.
- Support sub-DAG composition so a larger DAG can reference smaller DAGs without
  copying or flattening them. A node referencing a sub-DAG is an assistant-proposed
  candidate representation, not a selected schema.
- Extend the C foundation, low-level Python API and inspection CLI only as needed
  to construct and inspect this structure.
- Work through a concrete example before selecting the representation: two trial
  DAGs exposing named input/result nodes, a comparison DAG referencing those trials
  and a recorded summary, then a child snapshot replacing one trial while retaining
  the other. Python and CLI inspection should expose nested structure and scoped
  names; shared sub-DAG identities and earlier immutable records remain unchanged.
- Python performs any arithmetic itself. Recorded structure does not claim DML
  executed the calculation or verified the summary, and nesting alone does not
  establish computational dependency or causality.
- Use the example to learn composition and lookup semantics, inspectability, and
  which small authoring helpers are useful above the low-level API. No general
  workflow framework is selected.
- No intents, closures, requests/attempts, execution adapters, reuse facets, remotes,
  resource management, observer subsystem or visualization UI in this turn. No
  pre-1.0 migration machinery is required.

The next planning task is a worked example and bounded candidate design/handoff.
Scope agreement does not approve an exact schema or authorize implementation.

### Iteration 3 candidate preparation

At the user's instruction to proceed with planning, the assistant prepared the
[worked example](iterations/03-composable-dags/EXAMPLE.md),
[candidate design](iterations/03-composable-dags/DESIGN.md) and conditional
[handoff](iterations/03-composable-dags/HANDOFF.md). The example records two Python
calculations and a comparison, then replaces one trial in a child snapshot while
retaining the other. It deliberately records containment/values rather than
claiming captured computation or causal dependencies.

Assistant-proposed choices include a non-executing sub-DAG-reference node,
root-plus-named-bindings DAG structure, exact single-scope lookup, canonical ASCII
binding names, a changed DAG encoding without migrations, and bounded native CLI
nested inspection. These are reviewable candidate choices, not newly user-approved
schema/API decisions. A separate sub-DAG-root fixture addresses the current CLI's
literal-root assumption.

Preparation inspected clean implementation `e253249`; no implementation files were
changed and no build/test suite was rerun. Planning is complete for review;
implementation, delegation and publication remain unauthorized.

### Iteration 3 design approval

The user reviewed and approved the worked example, design and conditional handoff.
This accepts the assistant-origin candidate choices as the bounded plan, not
implemented behavior. Exact engineering details still marked provisional can be
selected and recorded during an authorized turn. Approval of the plan is recorded
separately from permission to start implementation, which remains pending. No code,
workers, commits, pushes or publication were started by this approval checkpoint.

### Iteration 3 implementation and publication authorization

The user explicitly authorized the existing Pi agent in window 2 to implement
Iteration 3, with this coordinator monitoring, independently reviewing and providing
feedback until satisfactory. Once accepted, have that agent commit and push, monitor
CI workflows for the pushed SHA and fix any issues until successful. This supersedes
the preceding implementation-pending status for this bounded turn, not its stop line.
No extra workers, release/package publication, cloud experiments or later feature
turn are authorized.

[Coordination](iterations/03-composable-dags/COORDINATION.md) records the active
assignment: implementation worker `dml-design:2` pane `%215`, initially empty Pi
conversation; worker owns runtime/tests/as-built docs and RESULTS, coordinator owns
REVIEW and design status notes. Worker has exclusive `build/check` until a review
pause is agreed. Implementation was initially clean at `e253249`. The handoff prompt
was submitted to the existing worker; no new agent or session was launched.

### Iteration 3 delivery and publication checkpoint

The existing window-2 worker implemented the approved bounded slice: named DAG
bindings, non-executing sub-DAG-reference nodes, explicit scoped lookup, owned
Python descriptions and native CLI nested inspection/nonliteral-root handling.
The runnable comparison records Python-produced values/containment, not captured
computational causality. The changed DAG encoding deliberately rejects the former
root-only shape without pre-1.0 migration machinery.

Coordinator feedback corrected DAG errors mislabeled as trees and a generated-name
property-test flake; worker confirmed and removed only its mutation scratch artifacts
before staging. Worker and independent coordinator fresh default checks pass:
7 C executables, 316 Python tests, Python 469/469 statements, retained C 1681/1681
lines, 132/132 functions and 1562/1562 outcomes. Expanded binding memory workload
has zero unsuppressed errors and 141 native CLI Valgrind processes pass. Coordinator
49 independent API/CLI probes and a separate isolated installed workflow pass.
Precise exclusions/suppressions, mutation survivors, direct-not-transitive validation,
read/allocation/presentation bounds, finalizer misuse and platform/install limits
remain qualified in [RESULTS](iterations/03-composable-dags/RESULTS.md) and
[REVIEW](iterations/03-composable-dags/REVIEW.md).

After explicit review acceptance the worker inspected/staged the reviewed 31-file
slice and committed/pushed `9b8fb7176e31186621dd5a4c26adadec4d76bc1e`. Coordinator
verified the commit surface, remote master SHA, clean implementation checkout and
[exact-SHA CI run 40474598485](https://github.com/micha/dml/actions/runs/40474598485).
All six jobs succeed on the first published run; no CI follow-up fix was needed.
All jobs pass 7 C executables; Linux passes 316 Python tests, macOS 312 with 4 existing
skips, Windows 311 with 5 existing skips. CI's informational strict-Linux `-c`
remains distinct from local default/memory evidence. Release Python was not triggered.
No extra agent, force push, tag/release, package publication, system change or later
feature work occurred. Design notes remain local/uncommitted. Work is complete and
stopped for user review.

### User acceptance and design checkpoint

The user accepted the Iteration 3 delivery and requested a local commit of these
design notes. This checkpoint includes the accumulated Iteration 1–3 plans, delivery
and review evidence, scope/coverage guidance and current resume point. Earlier
statements that design notes were uncommitted describe those historical deliveries;
this checkpoint records them locally in the no-remote design repository. The user
also asked for an Iteration 4 proposal; no fourth-turn direction or implementation
is yet approved.

## Iteration 4 agreed direction: one locally executed, recorded step

The user agreed to the proposed next turn and requested plan/handoff documentation.
This selects the bounded direction below for planning, not implementation or exact
record/API approval.

- Execute one explicitly bound local Python implementation using named input nodes.
  Record an explicit intent URI, concrete implementation/adapter binding and inputs
  before dispatch, without a registry or automatic implementation selection.
- Record distinct request and attempt occurrences as ordinary DAG data, not new
  core record types. The subprocess constructs a result sub-DAG through the existing
  API; record result or failure in a later DML commit.
- Preserve missing final outcomes after interruption as unknown, not automatically
  failed. A retry creates a new attempt; two matching fresh calculations may have
  identical result content while their occurrences remain distinct.
- Start with a small Python layer over public repository operations. A demonstrated
  missing C primitive needs a separate scope decision, not automatic core expansion.
- Acceptance includes two matching additions, a failing implementation and a parent
  interruption after the attempt is recorded; ordinary Python/CLI inspection exposes
  bindings, inputs and outcomes.
- No reuse/cache/facets, intent lifecycle/defaults, asynchronous scheduler, remotes,
  cloud execution, resource management, observer/UI or general workflow framework.
  Recorded source/inputs do not prove complete environmental capture or scientific
  validity; no exactly-once external execution is promised.

### Iteration 4 candidate preparation

The assistant prepared [DESIGN](iterations/04-local-recorded-execution/DESIGN.md),
[EXAMPLE](iterations/04-local-recorded-execution/EXAMPLE.md) and conditional
[HANDOFF](iterations/04-local-recorded-execution/HANDOFF.md). Assistant-proposed choices
include a separate `daggerml.local` layer, captured entry-script bytes with explicit
runtime/capture limits, document-local ordinary-DAG role conventions, UUID occurrence
reservation/publication refs, atomic pre-dispatch/final commits, cooperative child
result publication, explicit retry and computational/cleanup-outcome separation.
A two-parent final commit can retain accepted child publication history without
introducing a general merge algorithm. These remain candidate choices for review,
not additional user agreements or implemented behavior.

The plan explicitly addresses closing parent handles before child work, no launch
before committed attempt state, failure of final persistence without false `done`,
unknown outcomes despite possible child publication, bounded stored diagnostic
snippets versus unbounded child/disk/resource effects, trusted code rather than a
sandbox, and private deterministic interruption tests. It defers automatic recovery,
process-tree guarantees and production concurrency/resource management.

Preparation inspected clean implementation `9b8fb71` and clean design checkpoint
`cbfcd92`. No implementation/as-built files were changed, tests/builds rerun, workers
launched or publication performed. New design notes are local/uncommitted. Next is
user review of the candidate and separate implementation authorization.

### Iteration 4 implementation and publication authorization

The user declared Iteration 4 GO and authorized the existing window-2 agent in a
new Pi session to implement the bounded plan, with coordinator monitoring,
independent review and feedback/fixes. Once satisfactory, have the worker commit
and push, then monitor exact-SHA CI and fix issues as needed. This supersedes the
preceding planning-only status, not the scope/stop line. No extra workers,
release/package publication, cloud experiments or later feature turn.

[COORDINATION](iterations/04-local-recorded-execution/COORDINATION.md) records the
assignment and shared-build ownership. Coordinator sent `/new` to pane `%215` and
verified an empty new session; implementation baseline is clean `9b8fb71`.
Worker owns implementation/tests/as-built docs and RESULTS; coordinator owns review
and design status notes. Commit/push waits for explicit coordinator acceptance.

### Iteration 4 delivery and final publication checkpoint

The fresh-session window-2 worker implemented the bounded Python local layer,
ordinary request/attempt/outcome DAGs, pinned context, cooperative child publication,
explicit retry, captured trusted entry bytes, file-backed bounded stored diagnostics
and separate computational/cleanup outcomes. There is no native evaluator, execution
CLI command, registry/reuse/scheduler/remote/resource/observer addition. Initial
attempts have no final status/outcome; interruption preserves unknown rather than
inventing failure. Trust, capture, direct-validation and direct-child-only cleanup
limits remain explicit in the [owning contract](../dml/docs/spec-next/local-execution.md).

Worker and independent coordinator fresh default checks exit 0: seven C executables,
368 Python tests, Python 878/878 statements (local layer 361/361), retained C
1681/1681 lines, 132/132 functions, 1562/1562 outcomes. Existing binding/141 native
CLI Valgrind workloads pass, with no new exclusion/suppression/weaker threshold.
Coordinator's separate offline-installed parent/child/reader/console workflow passes
43 checks, including timeout after publication retaining evidence and final-head
conflict preserving unknown. Measured host-side helpers are distinct from
uninstrumented staged/installed children; unavailable Python mutation tooling,
negative-oracle scope, runtime/finalizer and local installed-platform limits remain
qualified in [RESULTS](iterations/04-local-recorded-execution/RESULTS.md) and
[REVIEW](iterations/04-local-recorded-execution/REVIEW.md).

After explicit coordinator acceptance, worker committed/pushed the reviewed 16-file
slice as `efac107`. Its five Unix CI jobs passed, but Windows stalled. Coordinator
requested investigation/cancellation and accepted narrow CI diagnostic/finiteness
commit `b0e3107` (ten-minute matrix-job bound, unbuffered verbose Windows IDs and
faulthandler). Both runs ultimately completed cancelled; earlier Windows logs were
unavailable, so no original Windows stack-trace diagnosis is claimed.

Worker found a confirmed portable test defect: an oversized source parameter became
a 1,048,725-character pytest ID/PYTEST_CURRENT_TEST value. A bounded Windows-length
model fails before the fix (9 pass/2 errors) and passes afterward (10 pass). Accepted
test-only `d498a6c` gives short semantic IDs and a length regression, retaining the
1 MiB + 1 byte source/rejection assertion. Worker fresh default checks and coordinator
independent 52-test postfix run pass. No production code changed after initial review.

[Final CI run 40536650838](https://github.com/micha/dml/actions/runs/40536650838) passes
all six jobs for exact SHA `d498a6cd4eea170c2054690880526c2fbb6ebaa6`: seven C
executables everywhere; Linux/strict 368 Python tests, macOS 364 with four existing
skips, Windows 363 with five existing skips. Windows Python finishes in 45.99 seconds.
Coordinator independently verifies full logs, completed JSON, exact-SHA workflow list,
watch exit 0, clean checkout/index and matching remote master. CI informational `-c`
remains distinct from the local default/memory gate. No release workflow was triggered.

Implementation, review, authorized publication and final CI are complete. Worker
was instructed to finalize RESULTS and stop. No extra agent, force push, release/tag,
package publication, cloud experiment or later feature turn. Design notes remain
local/uncommitted; no design checkpoint commit was requested for this turn.

### Iteration 4 user acceptance and design checkpoint

The user accepted the delivery and then requested committing the changes. This
local checkpoint includes the Iteration 4 plan/example/handoff, coordination,
delivery/review/CI evidence, bounded authorization and updated resume point.
Earlier uncommitted-design statements preserve their pre-checkpoint provenance.
The design repository has no remote; no push is requested or performed. The
implementation remains clean at already published `d498a6c`. No next turn is
selected or authorized.

## Resume point

Iteration 4 is implemented, independently accepted and published through `d498a6c`;
all six final exact-SHA CI jobs pass. Read
[RESULTS](iterations/04-local-recorded-execution/RESULTS.md),
[REVIEW](iterations/04-local-recorded-execution/REVIEW.md) and the
[as-built local-execution contract](../dml/docs/spec-next/local-execution.md).
Implementation checkout is clean at pushed `d498a6c`. The user accepted the delivery;
work is complete and stopped. No later turn is selected or authorized. Do not restart
the window-2 worker from historical planning/coordination instructions. Design notes
are included in the requested local checkpoint. Capture/unknown/cleanup and assurance
limits remain explicit;
CI success does not supply exactly-once execution or a complete environment model.

The following Iteration 3 and Iteration 2 resume evidence is historical; Iteration 4
above is the current implementation state.

Iteration 3 implementation, independent review, authorized worker commit/push and
final exact-SHA CI verification are complete. Read
[RESULTS](iterations/03-composable-dags/RESULTS.md) and
[REVIEW](iterations/03-composable-dags/REVIEW.md), plus the as-built
[objects](../dml/docs/spec-next/objects.md),
[repository](../dml/docs/spec-next/repository.md),
[Python API](../dml/docs/spec-next/python-api.md) and
[CLI](../dml/docs/spec-next/cli.md) contracts. Implementation master is clean at
pushed `9b8fb71`; all six exact-SHA CI jobs pass. The user accepted the delivery;
Iteration 3 is stopped. Its accumulated design notes were checkpointed locally as
`cbfcd92`; new Iteration 4 planning is uncommitted. No release/package publication
or fourth-turn implementation was performed.

The following Iteration 2 resume evidence is historical.

Iteration 2 implementation, coordinator review and authorized publication are
complete. Read the
[delivery notes](iterations/02-repository-usability/RESULTS.md) and implemented
[Python API](../dml/docs/spec-next/python-api.md),
[inspection CLI](../dml/docs/spec-next/cli.md) and
[packaging](../dml/docs/packaging-and-distribution.md) contracts. The
[coordinator review](iterations/02-repository-usability/REVIEW.md) and
[publication checkpoint](iterations/02-repository-usability/RESULTS.md#publication-checkpoint)
record final acceptance: independent probes/install, fresh local default/memory
validation, final links/status and all six exact-SHA CI jobs pass. The implementation
checkout is clean at pushed `e253249`; design notes remain local/uncommitted.
Work on Iteration 2 is complete. Its clean-source statement above is the initial
Iteration 3 baseline, not a claim that the active worker's checkout remains clean.
No release or package publication was performed.

Prior resume framing (historical, superseded; not active instructions): see the
[scope above](#iteration-2-agreed-direction-repository-usability). The user reviewed
the [candidate design](iterations/02-repository-usability/DESIGN.md) and
[handoff](iterations/02-repository-usability/HANDOFF.md), then authorized bounded
implementation in a fresh Pi session in window 2. Monitor and independently review
that work, send findings for fixes, validate the final state, and report. Record
selected API/build choices and distinguish actual evidence from planned checks.
Higher-level conveniences belong above the low-level API, not inside its contract.

### Completed Iteration 1 checkpoint

Historical publication state, before the later LSP commit `06bf66e` and Iteration
2. The source/unstaged/planning statements below are retained as that earlier
checkpoint, not current status; the Iteration 2 checkpoint above supersedes them.

Publication and Actions monitoring of Iteration 1's reviewed follow-up are
complete. The implementation is now at published `6ee9329`; its exact-SHA CI run
passed all six jobs. Read the
[publication checkpoint](iterations/01-minimum-viable-repository/RESULTS.md#follow-up-publication-checkpoint),
[URI correction notes](iterations/01-minimum-viable-repository/RESULTS.md#final-uri-diagnostic-correction),
[follow-up notes](iterations/01-minimum-viable-repository/RESULTS.md#review-follow-up)
and [coverage catalog](../dml/tests/coverage-exclusions.md). The passing local
default gate and informational CI remain distinct evidence; historical initial
failures and excluded populations remain visible.

Only unrelated LSP work remains unstaged in the implementation checkout:
`.gitignore`, README's C Editor Setup section, `scripts/setup-lsp.sh`, and
`tests/python/test_setup_lsp.py`, plus generated `.wraplock`. Design notes remain
uncommitted with no remote. Earlier `0bcfe92` CI evidence is historical, not the
new commit's run. Iteration 1 stopped after this publication checkpoint. Iteration
2 is now selected for planning only, as recorded above. The as-built [object contracts](../dml/docs/spec-next/objects.md) and
[repository contracts](../dml/docs/spec-next/repository.md) remain the implemented
repository scope. Use the shared [glossary](../dml/docs/spec-next/glossary.md).

Favor minimal prototypes and frequent iterations, broad or deep as appropriate.
DML repositories/state are ephemeral until `v1.0.0`, without per-iteration version
increments or required migrations. Stop after this turn for review; the handoff
is not authorization to continue through subsequent iterations.

Purpose-specific node identity facets remain agreed, initially full-record and reuse
identity. A [draft entity and identity map](design-map.md) provides a visual reference;
its boxes are conceptual roles, not approved core record types. The user found the
full map too much to take in and favors concrete incremental work. Remote execution
remains a major open challenge. Named-node lookup has provisionally explicit DAG scope.

Researcher-controlled detail uses ordinary result sub-DAGs, not special observability
facilities. Observer Stage 0 is complete; do not launch later implementation stages
without further instruction.

The completed study demonstrated narrow cooperative journal/provider/admission
mechanisms and exposed remaining Delete-authority, input-directory capture,
membership, receipt, HCL composition and erasure gaps. Those remain discussion
subjects; no production schema or policy choice has been approved.

Other open topics remain closure identity/configuration scope, cross-implementation reuse evidence, project/repository defaults, and exact execution/adoption semantics.

Maintain design work here and implemented technical contracts in the new as-built
spec. The bounded Iteration 1 authorization does not finalize the broader design or
authorize implementation of later subsystems.
