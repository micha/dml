# Maintainability Assessment Specification

Status: Draft.

Authority boundary:

- This document is authoritative for maintainability assessment criteria,
  success measures, and AI-heavy weighting used for repository evaluation.
- For documentation ownership and writing rules, see
  `docs/documentation-guidelines.md`.
- For implementation behavior of the DaggerML object model, execution model,
  remotes, CLI, and Python bindings, see the corresponding documents listed in
  `docs/spec/overview.md`.

## 1. Scope

This document defines how maintainability MUST be assessed for this repository
and related codebases.

It covers:

- assessment dimensions
- evidence and measurement expectations
- success criteria
- additional requirements for AI-heavy authoring workflows

It does not redefine product behavior or API semantics.

## 2. Conformance

A maintainability assessment conforms to this specification when it:

- evaluates all required dimensions in Section 3
- uses both repository evidence and workflow evidence as defined in Section 4
- reports success using measurable outcomes as defined in Section 5
- applies the AI-heavy adjustments in Section 6 when AI agents author most code
  or tests
- records exceptions and unknowns explicitly as defined in Section 7

## 3. Assessment Dimensions

Each assessment MUST evaluate the following dimensions.

### 3.1 Code clarity

The assessment MUST evaluate whether code is easy to read and explain.

Evidence SHOULD include:

- function size and scope
- control-flow complexity and nesting depth
- naming quality
- readability of public APIs and error messages

Success indicators:

- most functions can be explained in one or two sentences
- review feedback focuses on design and correctness more than code deciphering
- complex logic is isolated rather than repeated across modules

### 3.2 Modularity and boundaries

The assessment MUST evaluate whether changes remain local and interfaces are
clear.

Evidence SHOULD include:

- module dependency shape
- circular dependency count
- number of files touched for routine changes
- stability of public interfaces relative to internal code

Success indicators:

- small changes stay local
- module boundaries are explicit
- public contracts change less often than implementations

### 3.3 Testability and verification quality

The assessment MUST evaluate whether behavior is protected by trustworthy,
maintainable tests.

Evidence SHOULD include:

- line, branch, and function coverage
- mutation testing results when available
- regression tests for fixed defects
- determinism and readability of tests
- ratio of behavioral tests to mock-heavy or incidental tests

Success indicators:

- critical behavior is protected by deterministic tests
- test failures are actionable
- tests constrain behavior rather than only executing code paths

### 3.4 Change safety

The assessment MUST evaluate whether refactors and feature work can be done with
confidence.

Evidence SHOULD include:

- CI reliability
- build reproducibility
- escaped defect rate
- release rollback or hotfix frequency
- time from change to validated result

Success indicators:

- most regressions are caught before merge or release
- CI is trusted by contributors
- releases do not depend on manual heroics

### 3.5 Documentation and intent capture

The assessment MUST evaluate whether repository intent is explicit and current.

Evidence SHOULD include:

- source-of-truth documentation coverage
- architecture and API contract documentation
- rationale captured in docs, issues, commits, or tests
- onboarding ability from repository materials alone

Success indicators:

- common design and operational questions are answered by repository docs
- source-of-truth boundaries are clear
- contributors can recover intent without relying on tribal knowledge

### 3.6 Consistency

The assessment MUST evaluate whether similar problems are solved in similar
ways.

Evidence SHOULD include:

- formatter and linter compliance
- number of competing patterns for imports, naming, error handling, and tests
- duplicated implementations that differ only in style or structure

Success indicators:

- contributors can predict how new code should look
- review comments about style or pattern drift are rare
- the codebase feels coherent rather than patchwork

### 3.7 Dependency and build hygiene

The assessment MUST evaluate whether tooling and dependencies are controlled and
repeatable.

Evidence SHOULD include:

- dependency count and update cadence
- known vulnerability backlog
- reproducibility of build and test commands
- setup time for a new contributor
- environment-specific failure frequency

Success indicators:

- new contributors can build and test quickly
- dependency updates are routine rather than disruptive
- local and CI behavior is broadly aligned

### 3.8 Observability and diagnosability

The assessment MUST evaluate whether failures can be understood from available
signals.

Evidence SHOULD include:

- quality of error messages
- usefulness of logs and telemetry
- ability to identify root cause from existing evidence
- need for ad hoc debug instrumentation

Success indicators:

- failures are explainable
- debugging starts from evidence rather than guesswork
- external-input boundaries emit actionable information without exposing
  sensitive data

### 3.9 Architectural integrity

The assessment MUST evaluate whether the implementation still reflects intended
architecture and invariants.

Evidence SHOULD include:

- documented invariants and their enforcement points
- architecture violations or layer crossings
- complexity growth per delivered feature
- divergence between code and source-of-truth docs

Success indicators:

- the codebase can grow without forcing major rewrites for routine changes
- important invariants remain visible and enforced
- design intent remains legible over time

### 3.10 Team workflow fit

The assessment MUST evaluate whether the codebase supports collaborative change.

Evidence SHOULD include:

- review turnaround time
- average change size
- merge conflict frequency
- ownership concentration or bus-factor risk
- amount of manual release or validation work

Success indicators:

- work does not bottleneck on one maintainer
- contributors can make safe changes without extensive handholding
- routine workflows are automated and documented

## 4. Evidence Model

An assessment MUST use evidence from all of the following classes.

### 4.1 Static evidence

Static evidence includes repository properties that can be inspected without
observing production operation.

Examples:

- complexity measures
- dependency graphs
- duplication analysis
- lint, type-check, build, and coverage results
- test suite composition

### 4.2 Workflow evidence

Workflow evidence includes change-process outcomes.

Examples:

- CI pass rate and flake rate
- review latency
- change size distribution
- release failure or hotfix frequency
- time required to validate a routine change

### 4.3 Human evidence

Human evidence includes maintainers' direct experience with the repository.

Examples:

- onboarding feedback
- areas routinely avoided because they feel risky
- repeated questions that indicate missing documentation
- disagreement between expected and actual system behavior

An assessment SHOULD avoid relying on any single evidence class in isolation.

## 5. Success Measures

An assessment report MUST describe success using outcomes, not only subjective
impressions.

Recommended outcome measures include:

- lead time for routine changes
- escaped defect rate
- regression rate after refactors
- onboarding time to first safe contribution
- first-pass CI success rate
- flaky test rate
- median files touched per routine task
- review turnaround time

The report SHOULD distinguish:

- strong signals, which are hard to game and map directly to maintenance cost
- weak signals, which are useful only when paired with stronger evidence

### 5.1 Strong signals

Strong signals typically include:

- escaped defect rate
- mutation score on critical modules
- flaky test rate
- first-pass CI success rate
- median files touched per task
- review turnaround time
- frequency of substantial rewrites during review

### 5.2 Weak signals

Weak signals typically include:

- raw line coverage without mutation or invariant evidence
- raw test count
- raw lines of code added
- commit count
- unstructured impressions of cleanliness

Weak signals MAY be reported, but they MUST NOT be the primary basis for a
maintainability conclusion.

## 6. AI-Heavy Authoring Adjustments

This section applies when AI agents author most code or tests.

### 6.1 Additional priorities

For AI-heavy workflows, assessments MUST increase the relative weight of:

- documentation and explicit intent capture
- consistency of patterns and terminology
- boundary clarity and machine-checkable contracts
- deterministic tooling and strong automated guardrails
- locality of change and limited context requirements
- reviewability of generated diffs
- test quality over test quantity

### 6.2 Additional required checks

An AI-heavy assessment MUST evaluate the following capabilities.

#### 6.2.1 Machine-readable guidance

The repository MUST provide enough checked-in guidance for an agent to discover
how to build, test, and validate changes.

Evidence SHOULD include:

- agent instructions or contributor workflow docs
- stable validation entrypoints
- examples and golden tests
- schema files, typed interfaces, or explicit contracts

#### 6.2.2 Determinism

The repository SHOULD minimize nondeterminism that makes generated changes hard
to validate.

Evidence SHOULD include:

- reproducible builds and tests
- consistent formatting and lint results
- stable fixtures and error messages
- low test flake rate

#### 6.2.3 Anti-bloat resilience

The repository SHOULD resist common generation failure modes such as unnecessary
abstraction, speculative extensibility, wrapper proliferation, and test bloat.

Evidence SHOULD include:

- code growth relative to delivered behavior
- unused or weakly justified abstractions
- dead code or orphan modules
- duplicated helper layers with little value

#### 6.2.4 Reviewability

Generated changes MUST remain reviewable by humans.

Evidence SHOULD include:

- average diff size
- unrelated churn rate
- frequency of requests to split or simplify changes
- percentage of generated changes requiring substantial manual rewrite

### 6.3 AI-heavy success indicators

In AI-heavy workflows, success is indicated when:

- agents can complete correct local changes with limited context
- automated checks catch incorrect changes early
- humans can review generated output quickly
- repository materials encode enough intent that agents do not need to guess
- generated code and tests remain constrained, minimal, and consistent

## 7. Reporting and Exceptions

A conforming assessment report MUST include:

- the scope of the assessment
- the evidence used
- a finding for each dimension in Section 3
- explicit notes for missing evidence or unresolved uncertainty
- AI-heavy applicability, including whether Section 6 was applied
- concrete next improvements for the highest-risk dimensions

Scoring is optional. If scores are used, the report SHOULD pair each score with:

- supporting evidence
- current risk
- recommended next action

Informative example dimensions for a scorecard:

- clarity
- modularity
- verification quality
- change safety
- documentation
- consistency
- build hygiene
- observability
- architectural integrity
- workflow fit

## 8. Informative Summary

A maintainable codebase is one in which contributors can change the system
cheaply and safely over time.

In AI-heavy environments, this extends to the repository's ability to shape
agent behavior toward correct, minimal, and reviewable outcomes.
