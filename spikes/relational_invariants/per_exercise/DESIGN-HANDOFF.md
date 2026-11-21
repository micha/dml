# Handoff: invariant-driven DML test-suite design

Status: historical design handoff. The subsequent, explicitly authorized single-case experiment
is recorded in [Quint feasibility](../quint_feasibility/README.md).

## Authority boundary

This note records the test-suite design discussion, its open questions, and an unresolved
review finding. It is not an as-built specification or acceptance record. The existing
[workflow](README.md#linuxnix-portability-continuation) and
[portability results](PORTABILITY-RESULTS.md) retain ownership of executed spike evidence.
[Maintained validation scope](../../../README.md#maintained-validation-scope) owns the
separate standard gate boundary.

## Authorization and repository state

The user made the remainder of this session read-only and the discussion off-record, then
explicitly authorized writing this handoff as a narrow exception. That does not authorize
implementation, dependency installation, test execution, further edits, commits, or pushes.
Confirm the next scope with the user before undertaking implementation.

Immediately before writing this note:

- Working tree was clean.
- Spike branch and its remote tracking ref were
  `971b6304bf7566910a2c608869cb55da4ef9d975`.
- Master and its remote tracking ref were
  `00b7b00dd503476b6f1503c7933d9af42e987682`.
- The spike branch had been force-pushed with an explicit lease after confirming the
  remote-only commits were patch-equivalent to rebased local commits.
- Master had been pushed normally by fast-forward to publish the Nix tooling commit.
- CI remained manually disabled; no hosted validation was claimed.

These are historical observations, not permission to publish subsequent work.

## Agreed architectural direction

The user strongly favors simulation tests governed by universal invariants, rather than
collections of example-specific assertions. An invariant has the form:

> WHEN a state, transition, or history matches X, EXPECT Y.

The oracle need not maintain a parallel Python reference implementation.

```text
Hypothesis generates actions and inputs
    -> exerciser executes actual DML operations
    -> captures complete exercise evidence
    -> matches applicable invariants
    -> retrieves cached verification or performs checks
    -> returns failures to Hypothesis for shrinking
```

### Acceptance and non-vacuity

Across the declared validation scope:

- Every required invariant has at least one matching exercise.
- Every matching exercise satisfies its expectations.
- No match means unexercised, not passed.
- Missing evidence does not silently become a false matching predicate.

Coverage is a suite-level obligation, not something each individual generated history
must satisfy. One match is the minimum for non-vacuity, not proof of universal correctness.

### Always execute; cache verification only

This is a deliberate simplification from the existing spike:

- Every exercise executes; exercise execution itself is not reused.
- Each exercise produces a rooted DML graph retaining relevant history and reachable objects.
- Verification can be reused for an identical graph and identical applicable invariant/checker
  semantics. Relevant predicate, evaluator, and decoding dependencies belong in that identity.
- Matching reflects current invariant definitions; a newly added invariant cannot be hidden
  by a cached matching decision.
- Cached verdicts retain match evidence and counterexample information.

Unnecessary cache misses affect performance, not correctness. Inspecting misses afterward
may reveal accidental nondeterminism or other design issues in DML.

Deterministic graph-local identifiers may improve cacheability, provided distinct occurrences
remain distinct. Do not erase meaningful execution identity or weaken graph equality merely
to obtain cache hits. Reused verification is historical evidence, not fresh checker execution
or fresh coverage measurement.

### Hypothesis and attempted actions

Hypothesis would drive action sequences and input generation. It does not systematically
enumerate every one-node DAG, then every two-node DAG, and so on. A single action may create
multiple objects, read existing objects, or reject without changing target state.

The exerciser keeps available handles and other supporting bookkeeping, not a shadow
repository that independently predicts correct behavior.

Do not pre-filter invalid operations that DML is responsible for rejecting. The exerciser
captures attempted actions, supplied arguments, outcomes/exceptions, and relevant before/after
states. Throwing is not automatically success: invariants judge the rejection and its effects.
Unexpected or harness errors must not be silently reclassified as legitimate rejections.

Preconditions remain appropriate where needed to construct an exercise or control exploration;
DML validity conditions are not automatically generator eligibility conditions.

### Shrinking and reproduction

Verification returns its verdict during the active Hypothesis invocation so automatic shrinking
can work. This is compatible with exact-graph caching: cached counterexamples still cause the
current test to fail, and cached passes still return a verdict.

Arbitrarily deferred whole-suite verification complicates shrinking; it is not an inherent
restriction on content-addressed verification reuse.

Retain associations between graph hashes, generating action traces, invariant witnesses, and
reproduction metadata. Put run-specific reproduction metadata in sidecar receipts rather than
inside the hashed exercise graph. Hypothesis shrinks generated choices and re-executes actions;
it does not directly shrink a stored DML graph merely because it has a pointer to a test case.

### Explicitly shelved

- SQL checking and materialization.
- Shared analytical pools.
- DML debug-tracing instrumentation.

Direct graph inspection and exerciser-owned evidence are the baseline. Revisit additional
layers only for demonstrated value. Attempted-action evidence remains necessary even without
library tracing.

## Specification direction under consideration: Quint

The user wants readable, declarative invariants and potentially one specification serving both
mathematical design analysis and concrete implementation-conformance testing.

Quint is the current candidate, not an adopted dependency:

- It is a standalone specification language/toolchain, normally installed through npm, not a
  demonstrated Python module or ready-made Hypothesis integration.
- A `.qnt` specification is already a mathematical model; lightweight formal methods is an
  approach, not a separate output format called an LFM model.
- It supports executable pure predicates, typed records/collections/outcomes, simulation, and
  model-checking integration.
- Its compiler can parse, resolve imports, type-check, and emit a JSON representation.
- Documented model-based testing includes trace replay and Rust drivers. A suitable concrete
  Python/Hypothesis bridge has not been established.

### Potential compiler architecture

```text
DML specification.qnt
    |-> mathematical analysis
    `-> type-checked JSON representation
            -> deterministic DML-specific compiler
            -> Python/Hypothesis exerciser and invariant checker
```

This could make Quint a build-time dependency rather than a process invoked for every concrete
verification. It remains a proposal, not an integration demonstrated by this spike.

Handwritten bindings map abstract actions to DML API calls and extract actual observations.
They do not independently redefine expected behavior. The generated checker inspects actual
DML outcomes; it does not manufacture observations from the model's next-state calculation.

"Without duplicating meaning" means defining correctness predicates once, not independently
maintaining equivalent-looking Quint and Python assertions. A shared evaluator or faithful
mechanical translation could provide this; neither has yet been selected.

This deliberately introduces a mathematical model, but need not introduce a separately
handwritten Python reference implementation.

### Language subset clarification

A compiler would support the Quint constructs needed by DML's specification, not necessarily
all Quint. This is a backend limitation, not permission to omit DML behavior or weaken rules.

Agreed order:

1. Specify DML naturally.
2. Identify the Quint features used.
3. Support those features faithfully in the generator.

Unsupported constructs fail explicitly; they are not approximated silently. Native arithmetic,
floating-point representations, hashing, and similar details require deliberate modeling or
abstraction. Quint's expressiveness does not itself establish faithful concrete testing.

The compiler and observation adapters are assurance boundaries. Differential evaluation against
Quint is a proposed check on generated Python semantics. Pinning tool versions and canonical
output would be part of deterministic generation, not proof of correctness.

### Mathematical-analysis qualifications

Keep transition definitions and asserted invariants distinct: assuming a desired invariant
and then verifying it would be circular. Rejection outcomes belong explicitly in the model.
Model-checking claims retain their actual bounds and assumptions; they do not automatically
prove every implementation execution. Temporal/liveness properties need separate consideration
from finite state/transition safety checks.

The illustrative conversation example was a create-only storage slot: first creation succeeds;
a later creation rejects and preserves the existing value. Separate pure WHEN and EXPECT
predicates checked recorded attempts. It was not written to a file or executed.

### Sources consulted

- [Quint language reference](https://github.com/quint-co/quint/blob/main/docs/content/docs/lang.md)
- [Quint compilation](https://github.com/quint-co/quint/blob/main/docs/content/docs/quint.md#command-compile)
- [Quint model-based testing](https://github.com/quint-co/quint/blob/main/docs/content/docs/model-based-testing.mdx)
- [Quint model-checker integration](https://github.com/quint-co/quint/blob/main/docs/content/docs/model-checkers.mdx)

The STS paper discussed was [Evolving specifications formally](https://doi.org/10.1109/RE.2011.6051651),
Sampath, Arora, and Ramesh, RE 2011. Only its public abstract and introduction were obtained.
They describe structured requirements specification and refinement; they do not establish a
ready-made concrete testing bridge. Do not attribute unverified tooling capabilities to STS.

## Existing spike evidence and unresolved review findings

Historical results are qualified in [PORTABILITY-RESULTS.md](PORTABILITY-RESULTS.md):

- Portability controls: 79 passed.
- Seven-round ARM64 story: 63 requests, 33 fresh stages, 30 reuse satisfactions.
- Maintained gate: 3423 Python/CLI tests, seven C tests, 100% retained coverage, and passing
  Valgrind workloads.
- Isolated experiments are explicitly outside maintained default discovery/coverage by
  user-approved scope decision. Their older dependency/fixture failures remain unresolved.

The later review checked retained JSON, artifact/pool manifests, bundle hashes, and recorded
process receipts. It was not a new execution story, SQL run, or native semantic re-audit.
Raw evidence under `build/portability-audit/` and `build/scope-audit/` is ignored local data,
not backed up by the published commits.

### Unresolved projection-completeness defect

In [capsules.py](capsules.py), removing a shared `builtin-arguments-v1.value` field from one
retained positive-case capsule still passed capsule validation. Another capsule restored the
field during merging. The merged facts and generated SQL were identical to the accepted
original. [check_case](../shared_index/check.py) checks supplied membership but reads semantic
facts from the pooled database.

This was demonstrated in memory using retained JSON; no new native-store access or SQL
execution was needed. It shows incomplete per-case projections can be concealed by pooling.
The defect is not fixed. Shelving pooling in the proposed architecture does not retroactively
resolve that historical claim.

### Other limitations

- Selective invalidation was demonstrated with prebuilt variants, not a normal edit/reprepare
  workflow. Candidate fingerprints conservatively cover the tracked snapshot.
- End-to-end performance benefit over a well-designed direct graph checker remains unestablished.
- Some original design/results links require an unavailable external `dml-design` checkout.

## Suggested next scope, subject to authorization

Define one small vertical feasibility case before building a general compiler:

1. Select a real DML operation and its specified rejection behavior.
2. Define one shared Quint WHEN/EXPECT rule and a separate transition model.
3. Analyze that model within explicit bounds, including matching witnesses.
4. Define the concrete API binding and observation mapping.
5. Evaluate the same predicates on actual observations, directly or through generated Python.
6. Check translation agreement, match accounting, deliberate bad observations, counterexample
   reporting, and Hypothesis shrinking.

Do not treat the illustrative error labels or field names from the conversation as actual DML
API contracts. No Quint integration, generator, or feasibility execution existed at this handoff;
see the subsequent [direct-evaluation](../quint_feasibility/README.md#direct-evaluation-results)
and [Python generation](../quint_feasibility/README.md#deterministic-python-generation) results.
