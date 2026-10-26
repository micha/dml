# Agent-first DML design discussion — checkpoint

Status: Ongoing exploratory discussion at a conceptual checkpoint. Feasibility research and candidate-design experiments are complete; no approval to change DML implementation or its specifications.

## Scope and separation

This is user-led exploratory design work, not an amendment to the existing DML specification. DML implementation code, specs, and documentation have not been changed. The user authorized moving these notes from `/tmp/dml-tasks/agent-design/` into the separate Git repository `/work/repos/micha/dml-design` and making a local checkpoint commit. Future design notes belong here unless the user directs otherwise.

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

## Resume point

Continue by agreeing the implementation scope/location for the first minimum-viable
repository iteration: simplified entities, commit graphs and refs, without executions,
intents, merge or rebase. The assistant's larger execution-oriented first slice was
rejected as too ambitious. The new as-built specification has been created under
`../dml/docs/spec-next/`; only that documentation change is authorized in `../dml` so far.

Favor minimal prototypes and frequent iterations, broad or deep as appropriate.
DML repositories/state are ephemeral until `v1.0.0`, without per-iteration version
increments or required migrations. No implementation sequence or code changes have
been approved.

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

Maintain this work separately from existing repository specs/docs. This checkpoint does not end the discussion or authorize implementation.
