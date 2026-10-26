# Handoff: observe the feasibility study as a research graph

Status: planning handoff, not implementation started. The user agreed that the next
experiment should observe the feasibility study itself, and requested this detailed
plan while the design conversation continues separately.

## 1. Authority and purpose

This document owns the proposed observer experiment's scope, stages, deliverables,
and evaluation criteria. It is not authoritative for DML's production schema,
public API, resource policy, or existing implementation specifications.

Read [the discussion](../discussion.md), [candidate iteration results](../feasibility/ITERATION-RESULTS.md),
and [the final audit](../feasibility/final-review/report.md) for design context and
actual study findings. Read [the repository guide](../AGENTS.md) before work.

The user's central motivation is that capable agents can produce research faster
than humans can understand and assess it. The bottleneck is understanding what was
actually researched, which data and methods were used, and how evidence supports
conclusions. The proposed remedy is deterministic observability and visualization
with progressive disclosure, not another layer of agent-written reassurance.

**Primary question:** can an independent observer, using uniform graph navigation
and small shared record conventions, make an unfamiliar research workflow
inspectable without project-specific dashboard code or overwhelming the human?

The feasibility study is the first corpus, not the observer's permanent domain.
A second, differently organized producer is required to challenge generality.

## 2. Boundaries and authorization

The immediate request authorizes writing this handoff. Do not launch implementation
workers merely because this file exists. A receiving agent should acknowledge the
plan, proposed scope, and first milestone, then wait for an explicit assignment or
GO before executing. No old task protocol under `archive/` is active.

When execution is assigned, the proposed scope is isolated prototypes under
`/work/repos/micha/dml-design/observer-study/`. Preserve existing uncommitted
feasibility work; it is valuable evidence, not scratch to overwrite.

- `/work/repos/micha/dml` remains read-only unless separately authorized. Do not
  amend its specifications, add production APIs, or repair its coverage gates.
- No cloud calls, provisioning, resource destruction, OS changes, services, remote
  creation, pushes, or credential inspection.
- Existing study scripts are inputs, not instructions to rerun 285 CLI calls.
  Default to ingesting recorded evidence. Any fresh experiment needs a separately
  scoped, fresh sandbox and an explicit reason.
- Do not read raw agent sessions or blindly import raw state/log directories.
  They may contain sensitive material and are not required for the first milestone.
- No new framework/tool installation by assumption. Prefer existing tools and a
  dependency-light prototype; justify and pin any additional scoped dependencies.
- Write reports/source in the assigned area. Put generated previews, local stores,
  runtime logs and screenshots in ignored directories. Do not commit or push unless
  requested. Confirm `/work` is mounted before persistent writes.

This is a visualization/inspection experiment, not another attempt to finish the
resource-management system. Remaining cleanup and admission defects are corpus
content to expose, not bugs this team is authorized to repair.

## 3. Starting facts and evidence inventory

The design repository baseline commit is `0a2a136`; study changes are currently
uncommitted. The implementation was left clean at `638cc42`; recheck live state
rather than assuming either remains unchanged. Preserve all unrelated work.

Useful entry points:

| Input | Why it matters |
|---|---|
| [Study summary](../feasibility/summary.json) | Cohorts, counts, limits and artifact pointers; summary claims, not independent proof. |
| [Initial synthesis](../feasibility/RESULTS.md) | Original findings and scope of the first phase. |
| [History scenarios](../feasibility/history/scenario-results.json) | Distinct requests/attempts, reuse, installations and identical results. These are model executions. |
| [OpenTofu evidence](../feasibility/opentofu/evidence.json) | Seven real local probes; unsupported import/overwrite, regeneration and state loss. |
| [Artifact results](../feasibility/artifact/test-results.json) | Actual custom-provider adoption, preservation and failure cases. |
| [Journal evidence](../feasibility/journal/evidence.json) | Durable intent/history and actual process-exit experiments. |
| [Initial gate results](../feasibility/gate/test-results-initial.json) | Historical vulnerable behavior retained as evidence. |
| [Gate follow-up](../feasibility/gate/followup-test-results.json) | Revised gate, exact-plan-byte fix and original attack replays. |
| [Final audit evidence](../feasibility/final-review/evidence.json) | Seven independent focused cases, including the unfixed `.tofu.json` bypass. |
| [Pinned provider sources](../feasibility/adversarial/sources.json) | Source-only AWS findings; not cloud experiments. |

Older deliveries remain under names such as `journal/*-v1.*` and
`gate/*-initial.*`. Some historical report links name files now revised; use the
recorded source manifests/checksums and archived versions, not today's filename
alone. Raw supporting artifacts live under ignored `runtime/` directories and may
not survive copying the repository. Missing evidence must be displayed as missing,
not replaced with a plausible story.

Metrics have different units: model tests, result groups, CLI invocations, requests,
attempts, actual executions and retained source files. Never add them into a generic
"tests passed" number. A passing counterexample probe can establish an unsafe
behavior; harness success and the tested system's outcome are separate concepts.

## 4. Research scenarios the observer should make understandable

### A. An original flaw, a fix, and a new flaw

Show original checked-plan pathname substitution, the sealed-plan correction,
independent confirmation, and the later `.tofu.json` capture bypass. The human
should be able to inspect the relevant source/config inputs, victim/survivor
identities, recorded operations, and actual outcomes. The new flaw is not evidence
that kernel seals failed.

### B. Adoption is not creation

Show failed ordinary `local_file` import followed by overwrite, then actual
custom-provider adoption that preserves bytes. Expose before/after content or
safe digests and recorded identity checks. Clearly distinguish the built-in
state-only surrogate from the actual artifact provider.

### C. Unknown is not failed, and cleanup is not computation

Show request/attempt/progress, a process exiting after an effect but before receipt,
later observation/recovery, and final disposition. Keep computational result,
cleanup outcome, and what the observer can currently resolve separate.

### D. Reuse is not another independent trial

Show two requests sharing one execution versus two fresh executions returning the
same result. Render request count, attempt count, and recorded execution count
separately. Existing history-model examples are simulations; do not reclassify them
as fresh physical experiments simply because the observer ingested them again.

### E. Evidence class and unavailable material

A source-inspection finding about S3 must not look like a cloud-tested outcome.
Missing source bundles, inaccessible external artifacts and excised data should
remain explicit. The viewer must distinguish recorded historical availability
from a later observation that the resource is now unavailable.

These five stories are an evaluation corpus, not mandatory experiment categories
in DML's core.

## 5. Architecture to explore, not freeze

Separate four layers:

1. **Acquisition/import:** snapshot curated study evidence and normalize legacy
   formats. This layer may know study filenames and fixture schemas.
2. **Uniform repository/graph reader:** navigate immutable snapshots, trees, DAGs,
   records, datums and resource metadata. No feasibility-project path assumptions.
3. **Deterministic observer computations:** discover relationships, produce bounded
   previews, compute structural comparisons and render output.
4. **Presentation:** progressive disclosure for humans, with links back to exact
   source snapshots and recorded facts.

The viewer should never need a path such as `gate/runtime/run-X/` to recognize an
input or result. Such paths belong in imported locators, not viewer logic.

Ordinary graph traversal alone does not reveal semantics of an arbitrary map.
Explore a minimal shared vocabulary for request, binding, attempt, input, result,
reuse and observation relationships, represented with ordinary data/DAGs. Unknown
records should still be inspectable generically. Avoid inventing a mandatory
research-goal schema, universal confidence score or dedicated core record type.

### Native versus model boundary

The existing C implementation has canonical datums and LMDB storage; the higher
DAG/tree/commit/ref layer and real public orchestration bindings are not established
by this study. Do not pretend the observer prototype uses native DML navigation
unless it actually does.

For the first milestone, recommend a clearly labelled content-addressed model
repository behind a narrow read interface. Version its experimental convention,
validate it, and keep the renderer independent of storage. Record the gaps needed
to connect to the native core later. Do not silently make a general graph database
or SQLite schema into DML's production architecture.

An illustrative observer pipeline is:

```text
resolve source head -> pin immutable snapshot -> discover records
                    -> extract bounded views -> render -> publish observation
```

All names are provisional. Navigating an imported computation inspects its
recorded structure and outcomes; it never executes that computation.

## 6. Staged delivery

### Stage 0 — Curate and freeze a small truthful corpus

- Record source paths, original hashes, relevant tool/version metadata, and which
  supporting artifacts actually exist.
- Copy only allowlisted non-secret material into a reproducible fixture package.
  Preserve before/after versions and original failures.
- Define a ground-truth answer sheet for the five scenarios, with citations to
  structured evidence. Human-written claims remain claims.
- Label ingestion as retrospective. Newly generated ingestion occurrences are not
  historical execution IDs. Missing timestamps, inputs, attempts and environment
  capture stay unknown; do not fabricate closure completeness from a script hash.

**Deliverable:** corpus manifest, integrity checker, small fixture package,
provenance notes and answer sheet. No UI yet.

**Gate:** every displayed fact has a source locator; duplicated evidence is not
counted as independent reproduction; no raw state/session sweep.

### Stage 1 — Model the navigation contract and inspect values

- Represent source snapshots, trees and computation records as ordinary immutable
  graph data using the smallest experimental convention.
- Keep content identity distinct from occurrence identity. Records about an attempt
  can accumulate without becoming new attempts or mutating old observations.
- Implement read-only traversal, reference validation, generic datum inspection,
  and bounded expansion. Keep declared missing/unavailable references representable.
- Specify cache inputs for observer transforms: pinned source data, observer
  implementation/convention version and preview/render configuration. A whole
  orchestration Git revision should not invalidate every unchanged computation.

**Deliverable:** reader contract, a model backend, validation/tests, and a textual
inspection path through all five scenarios.

**Gate:** no project-specific directory paths in generic traversal; unsupported
records are surfaced rather than silently dropped; no source writes/execution.

### Stage 2 — A deterministic progressive-disclosure observer

Recommend a small static/local HTML plus SVG/JSON artifact, or equivalent
inspectable output, before a framework-heavy application. Technology is not selected.

- Start with a collapsed computational-step overview, not all primitives.
- Expand sub-DAGs; show named/labelled inputs, recorded outcomes and safe value
  previews beside the relationships carrying them.
- Provide a timeline and comparison lens: what changed in recorded source/binding,
  inputs, reuse choice and result. Label byte changes as byte changes, not inferred
  scientific significance.
- Separate harness result, system behavior, evidence classification and authored
  conclusion. Explain badges in text; do not rely only on colors.
- Every observation view identifies source snapshot, observer implementation and
  preview rules. A breadcrumb/detail path leads to the exact supporting material.
- Do not require a model call to build, render, navigate, diff or explain a status
  label. Optional agent commentary is a separate toggle/layer.

**Deliverable:** reproducible rendering entrypoint, view artifacts, deterministic
projection tests and screenshots/examples of the five stories.

**Gate:** the renderer works without reading experiment-specific Markdown or
filenames; dangerous data is escaped; details are reachable without opening every
log manually. Fix readability problems before expanding functionality.

### Stage 3 — Sidecar independence, progress and generality

- Run two observers with different configurations over the same producer snapshot.
  They write only their own outputs/observer history and require no producer hook.
- Use a bounded source-head replay to model in-progress publication: request and
  inputs appear, attempt progresses, result arrives, later review challenges it.
  Call this replay, not live observation of the historical study.
- Add a small fresh synthetic producer with a different experiment/trial tree
  organization, nested steps and scalar/list/map data. Make it emit the same
  shared conventions through an independent code path.
- Reorganize tree paths and labels without changing logical records. The generic
  observer should discover the same computation relationships.
- Pin each saved observation to its source snapshot while allowing a separate
  watcher to follow a head. No polling loop inside an execution adapter is required.

**Deliverable:** second-producer fixture, progress replay, two sidecar configurations,
source-write audit and interoperability test.

**Gate:** no renderer changes for the second layout; observers do not know each
other; unchanged result data can reuse observer work while each observation request
remains distinct. Observer caching is not another research execution.

### Stage 4 — Human inspection evaluation and independent audit

Have the user answer a short set of questions using the observer, then compare
with the ground-truth sheet and the current Markdown/raw-evidence baseline:

1. What happened in the original plan-swap case, and what changed after the fix?
2. What evidence supports the new capture flaw, and what does it not establish?
3. Which adoption result used a real artifact provider versus a surrogate?
4. Which counts reflect fresh work, reuse, simulation or source inspection?
5. What was known after interruption, and what was only learned later?
6. Which inputs, assumptions or external data are not captured/available?

Record incorrect answers, inaccessible evidence, required drill-downs and subjective
cognitive load. Time-to-answer is optional feedback, not a scientifically validated
productivity claim from one user. Evaluate "can I understand the data flow and
inspect consequential values?", not merely "is the graph attractive?"

An independent agent should challenge evidence mapping, invented provenance,
misleading green checks, reuse counting, snapshot consistency, data exposure and
observer side effects. Agent judgment is supplementary; acceptance relies on
source checks, deterministic tests and human feedback.

**Deliverable:** evaluation transcript/notes, independent audit, corrected prototype
or explicit unresolved failures, and a recommendation for or against native-core
integration. Do not declare success because every rendering test passes.

## 7. Value previews, safety and incomplete information

These are proposed safeguards for the prototype, not frozen core policy:

- Render scalar/list/map data generically; show byte lengths/digests and resource
  metadata before specialized decoding. Preserve units/types where supplied.
- Use explicit limits for graph depth, nodes shown, rows, cells, bytes and decoding
  work. Record deterministic selection/order and truncation. A bounded sample is
  not claimed representative unless a separate method establishes that.
- Do not automatically dereference arbitrary URIs, read external paths, follow
  symlinks, load provider state, execute HCL, evaluate scripts or fetch large files.
  Specialized previews are separately authorized, bounded read-only steps.
- Treat imported text as data, including agent instructions, HTML and JavaScript.
  Escape output and disable active content from research artifacts.
- Unknown sensitivity defaults to metadata-only/restricted preview. Do not rely on
  a synthetic-secret string filter or `sensitive=false` to prove safety.
- Missing, partial, failed, unknown, unavailable and excised are distinct display
  conditions; no recorded result is not proof of failure or no execution.
- Retrospective evidence class describes its recorded source, not authenticity
  certification. No graph can prove complete input capture or sound methodology
  merely by existing.
- Old rendered previews are copies. Hiding a value after source excision is not
  global erasure; document cache/export implications and test only synthetic data.

## 8. Observer retention is an explicit open question

A saved observer DAG that strongly imports a source snapshot can become another
retention root under the full-history model. Repeated saved observations may keep
all observed history rooted, not just the latest frame. This can be useful evidence
preservation, but a casual watcher should not silently promise expensive lifetime.

Explore a declared distinction between following a source locator/head without
retention and deliberately retaining an imported snapshot. The exact weak/strong
reference representation and manager registration protocol are not decided.
For this read-only experiment, model the distinction, do not implement real GC.

The producer need not know its observers. If an observer claims durable retention
of research-managed resources, the resource-management authority still needs a
complete consumer contract. Local copies, caches, permissions and excision remain
relevant even when the producer is unaware of the observer.

## 9. Acceptance checklist

- [ ] All five scenarios are inspectable from overview to original evidence.
- [ ] Same convention works across two independently produced layouts.
- [ ] Producer files/heads remain unchanged; observers write only their own state.
- [ ] A saved observation never silently combines data from different snapshots.
- [ ] Identical results do not collapse distinct requests/attempts; reuse is visible.
- [ ] Harness success does not visually imply the tested system behaved safely.
- [ ] Source inspection, simulation, actual recorded effects and author claims differ.
- [ ] Unknown inputs/closure capture and absent evidence are displayed, not invented.
- [ ] Deterministic projection is byte-reproducible for a fixed input/version/config;
      changing previews invalidates relevant observer reuse, not all research work.
- [ ] Size limits, truncation, unsafe text and unauthorized resource reads are tested.
- [ ] Progress replay distinguishes working, unknown outcome and final recorded result.
- [ ] Retention/copy implications are explicit; no automatic disposal/erasure claims.
- [ ] Human feedback shows useful inspection, or shortcomings are honestly reported.
- [ ] Native versus model evidence is labelled everywhere it affects conclusions.

Suggested adversarial fixtures include identical-output fresh attempts, reused
attempts, missing artifact/source snapshot, conflicting lifecycle observations,
excised input, large nested maps, malicious markup/instruction strings, unexpected
legacy record versions and a changing head during read.

## 10. Delegation and ownership for a receiving coordinator

Protect the coordinator's context with bounded, disjoint specialist tasks. Do not
parallelize before the corpus and reader convention are stable enough to share.

| Role | Suggested owned area | Responsibility |
|---|---|---|
| Corpus/evidence curator | `observer-study/corpus/` | Legacy import, source integrity, scenario answer sheet. |
| Graph/observer kernel | `observer-study/kernel/` | Experimental reader convention, snapshot consistency, deterministic projections. |
| Human-facing viewer | `observer-study/viewer/` | Generic progressive disclosure, value previews, comparisons. |
| Independent evaluator | `observer-study/review/` | Second producer, adversarial tests, evidence and usability review. |
| Coordinator | Index, plan and synthesis | Scope, dependencies, acceptance and consolidated findings. |

Publish a short interface contract before kernel/viewer work diverges. Workers
should not edit one another's areas, commit, delegate recursively, or execute study
scripts by assumption. Reports should contain commands, exact source versions,
measured results, limitations and short machine-readable summaries. Finished
reports precede atomic completion markers; a marker denotes finished work, not
passing every acceptance criterion.

If Pi workers are launched in tmux, read the installed Pi CLI/session documentation
first. Freeze launcher bytes before starting; do not edit a Bash script being read
by an active process. Verify report, marker and process outcome independently;
missing exit records and API errors stay explicit. Close only owned worker windows.

## 11. Deliverables and stopping conditions

Proposed layout (only this plan exists initially):

```text
observer-study/
  HANDOFF.md
  README.md                 # status, evidence boundary, reproduction
  corpus/                   # manifest, sanitized fixtures, legacy importer
  kernel/                   # convention, model reader, deterministic projections
  viewer/                   # renderer and human-facing examples
  review/                   # independent producer/tests/evaluation
  runtime/                  # ignored generated artifacts and logs
  RESULTS.md                # findings, unresolved decisions, next recommendation
```

The receiving team should stop and report a gap rather than expand into production
DAG infrastructure if the convention cannot expose inputs/results generically,
legacy evidence lacks enough facts, the viewer needs per-project special cases,
privacy cannot be bounded, or the UI overwhelms the intended human. Narrow the
corpus or revise the convention openly; do not paper over the problem with an
agent narrative.

Expected handoff output is a small running observer, reproducible tests, a truthful
worked research graph, and human-review evidence. A large frontend or completed
resource manager is not a success criterion.

## 12. Resume and open decisions

Immediate proposed first assignment: **Stage 0 only**. Produce the curated corpus,
answer sheet and evidence-gap inventory; get a brief review before selecting the
shared convention and presentation technology. This reduces schema/UI lock-in and
prevents a large dashboard built on fabricated historical provenance.

Keep these questions open:

- What minimal role/edge conventions make ordinary DAGs universally inspectable?
- What distinguishes generic traversal from domain-specific decoding/interpretation?
- Which grouping is most legible: recursive steps, timeline, comparisons, or a mix?
- How should following, retaining imports and current availability be represented?
- Which observer outputs are themselves reusable steps and retained research data?
- What should be implemented in the native C layer versus client/sidecar libraries?
- What human evidence would justify proceeding beyond this prototype?

The original conversation remains the place to discuss feasibility findings and
resolve conceptual choices. Executing this plan should not silently resolve them.
