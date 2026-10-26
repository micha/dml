# Computational-history feasibility experiment

## Authority boundary and verdict

This report describes only the informative Python model and executed experiments
in this directory. It is not an approved DML schema, API, or implementation plan.
The design context remains [the discussion](../../discussion.md); scope comes from
[the task](task.md) and [worker contract](../WORKER.md).

**Verdict: the requested history distinctions fit an ordinary immutable DAG in
this small model, but content addressing alone does not supply occurrence identity,
complete provenance, recovery guarantees, or conflict policy.** Twenty-four tests
pass. The strongest counterexamples are two identical trials collapsing into one
content-only execution record, and one recorded attempt hiding two external
executions. A separate allocator test shows that adding an occurrence field still
fails if a restarted issuer repeats its counter.

The experiments support continuing the ordinary-DAG exploration. They do not
establish compatibility with existing DML primitives or authorize implementation.

## Reproduction and observed results

Environment: **Python 3.13.15**, standard library only; no downloads, providers,
cloud calls, Docker access, or production DML changes. Run:

```sh
cd /work/repos/micha/dml-design/feasibility/history
python3 --version
mkdir -p runtime
python3 -m unittest -v > runtime/unittest.log 2>&1
python3 run_scenarios.py > runtime/scenario-rerun.json
cmp scenario-results.json runtime/scenario-rerun.json
```

Observed: `Ran 24 tests in 0.093s`, `OK`; both test and fixture-comparison exit
codes were zero. Timing is incidental. The compact, reproducible
[scenario fixture](scenario-results.json) contains 11 scenario summaries. To
regenerate it deliberately, run `python3 run_scenarios.py --write-fixture`.
The test suite also recomputes and compares the fixture. Raw output is in ignored
[runtime/unittest.log](runtime/unittest.log); temporary object stores and mock
service journals are created under ignored `runtime/` and removed by tests.

## Model and minimal assumptions

[model.py](model.py) implements SHA-256-addressed canonical JSON nodes with an
application label, ordinary value, and named edges to existing nodes. Labels such
as `request` and `observation` are conventions of this program, not proposed core
node types. Existing-only edges allow incremental construction without circular
hashes. Retrieval returns a decoded copy, so changing it does not change stored
bytes. Disk loading detects content corruption.

A request references its binding; an attempt references its request. Observations
reference a subject and optionally earlier observations, partial DAGs, or a final
result. An attempt never contains a mutable pointer to its latest observation.
A commit references an immutable snapshot and parent commits. Snapshots hold an
observation set and a reusable-attempt selection map; only named heads mutate.
Correlation with orchestration/Git is recorded as synthetic tokens in commits or
observations, not by making an event hash depend on its containing commit.

The model assumes collision-resistant hashes, consistent encoding, trustworthy
writers, rooted observation publication, and externally unique occurrence issuers
with durable allocation. Tests use deterministic `issuer:counter` strings, not a
production allocator. It also assumes an application validator understands the
record conventions. Arbitrary ordinary DAGs do not enforce these rules themselves.

The adapter is a finite-state **simulator**. Each tick performs at most one mock
service operation, publishes a bounded progress observation, and returns. This
establishes bounded logical steps, not a wall-clock timeout for real I/O. The mock
service implements idempotent submission keyed by attempt occurrence. Persistence
and head comparison are sufficient for our sequential/interleaved tests, not a
multiprocess transaction protocol or power-loss durability guarantee.

## Evidence map

All test names below are in [test_model.py](test_model.py).

| Claim | Executed evidence | Boundary |
| --- | --- | --- |
| Identical contents can retain distinct request/attempt occurrences | `test_content_dedup_but_distinct_occurrences` | Uniqueness is provided by the allocator assumption. |
| Reuse is not another trial; explicit reuse works with default off | `test_reuse_is_not_independent_trial_and_default_off_override` | Resolver policy is a modeled application function. |
| Intent policy and overrides can be versioned independently of binding | `test_versioned_intent_policy_and_recorded_request_override` | No complete intent/default-selection registry is implemented. |
| Fresh execution does not adopt itself; branches retain separate selections | `test_fresh_is_not_adoption_and_branch_isolation` | Adoption is an explicit modeled state change. |
| A discrepant fresh result stays visible without replacing selection | `test_discrepant_fresh_result_is_visible_without_automatic_adoption` | No scientific interpretation or automatic deprecation. |
| Two installations can yield one closure, while a changed binding changes it | `test_installations_same_closure_despite_incidental_outputs` | HCL is stored text; resolution is supplied synthetic data, not HCL evaluation. |
| One request can retain unknown and successful attempts | `test_one_request_multiple_attempts_unknown_then_success` | Missing terminal evidence is interpreted as unknown. |
| Crash/resume can reconstruct history from disk | `test_crash_resume_from_disk_and_idempotent_submission` | Re-instantiation plus injected exception, not a killed process; mock idempotency matters. |
| Incremental progress, result, cleanup failure, and remediation coexist | `test_bounded_calls_incremental_results_cleanup_failure_remediation` | Remediation is an appended assertion, not demonstrated resource deletion. |
| Failure can be recorded as `done`, separately from unknown | `test_recorded_computation_failure_is_done_not_unknown` | The executor failure itself is simulated. |
| Merge retains observations and rejects competing selections | `test_commit_merge_correlations_and_selection_conflict`, `test_simultaneous_lifecycle_updates_cas_merge_no_observation_loss` | Deterministic interleaving, not actual concurrent processes. |

Additional tests reject missing-result reuse, binding mismatches, failed/unknown
reuse, contradictory flags, conflicting terminal observations, and mutated disk
contents. Progress edges and historical snapshots remain immutable.

## Counterexamples and candidate fixes

### 1. Content-only execution identity loses observations

Two records containing the same binding and result produce the same hash; the
naïve design reports one unique execution for two trials. Adding explicit request
and attempt occurrences gives two attempt nodes sharing one result root, `11`.
A reuse observation references the existing attempt and introduces no new attempt.
However, repeating the same issuer/counter recreates the same request hash. A
candidate fix requires durable allocation or collision-checked random identifiers
and a rule rejecting duplicate occurrence identities across different records.
These are additional protocol assumptions, not properties of hashes.

### 2. Operational outputs make closure identity unstable

Two synthetic installations have identical executable resource bindings but
different creation times. A naïve closure referencing the complete resolved-output
node changes identity unnecessarily. Our closure instead includes implementation,
adapter, execution configuration, and selected binding fields; incidental outputs
remain inspectable through installation history. Changing `worker-v1` to
`worker-v2`, or changing the bound URI, changes the closure.

This split is deliberately baked into the model. An IP classified as incidental
might actually select a different executable service. The tests establish behavior
of the projection, not that the chosen fields are complete. A candidate fix is an
adapter-specific declared binding projection with recorded justification and
validation; the tradeoff is domain knowledge and configuration complexity.

### 3. A mutable name is not an artifact version

Two different synthetic code byte strings behind the same `/latest` URI produce
one URI-only artifact identity. Adding their actual byte digests yields two nodes.
No network dereferencing occurs. Recording a digest does not ensure that a later
executor verifies it, or that old bytes remain available. A possible fix combines
immutable version/digest references with execution-time verification and retention,
at storage and operational cost.

### 4. Attempt identity does not count hidden external retries

One attempt can represent two provider executions if the adapter only reports the
final result. The test explicitly simulates two job identifiers while history has
one attempt. Candidate child execution-occurrence nodes recover a count of two
**only when the adapter reports both**. The transcript's hidden-retry counts are
illustrative simulation values, not observations of a real provider. Discovery,
unknown dispatches, and dishonest or incomplete reporting remain unresolved.

### 5. Last-writer status destroys simultaneous knowledge

A scalar status field overwrites the first update. Our stale-head publication is
rejected; merging proposed commits unions both observations. Competing reusable
selections require an explicit resolution. Two independent adapter progress tips
remain recorded but block automatic continuation until reconciled. Contradictory
terminal observations likewise remain visible and disable reuse. This preserves
knowledge but intentionally sacrifices automatic liveness rather than choosing a
winner by timestamp.

## Resource retirement and reuse

`test_compute_excision_can_retain_selected_result_but_not_fresh_execution` appends
an authorized retirement assertion for compute infrastructure. The selected
execution and result remain reachable and reusable; a simple availability query
marks the bound compute unavailable for fresh execution. This distinguishes reuse
of an already obtained result from executing a historical closure again.

This is **resource retirement simulation, not tombstone substitution or sensitive
content erasure**. Old resource descriptions remain reachable. The model has no
physical cleanup, external-result availability checks, shared-consumer analysis,
GC, backup propagation, or legal erasure mechanism. A retired output artifact would
need different reuse eligibility from retired compute; closure equality does not
settle that policy.

## Prioritized gaps and next experiment

1. **P0: dispatch/accounting and publication durability.** Define what an attempt
   occurrence counts and what external execution evidence is required. Test
   non-idempotent submission, lost acknowledgements, and unrooted publication.
   Idempotency tokens reduce duplicates where supported; unknown outcomes preserve
   honesty but require investigation and may block reuse.
2. **P0: closure identity and artifact integrity.** Decide binding versus incidental
   fields, HCL/configuration inputs, immutable artifact versions, and verification
   responsibilities. Broader identity prevents unsafe reuse but increases churn.
3. **P1: atomic head updates and lifecycle reconciliation.** Implement actual
   transactional compare-and-swap and allocator collision checks; define causal
   reconciliation for multiple progress tips and contradictory terminal evidence.
   Observation union is straightforward; deciding authoritative state is not.
4. **P1: resource retirement versus erasure.** Separate historical closure identity,
   present executability, retained-result availability, and deletion obligations.
   Physical tombstones and sensitive erasure require stronger storage semantics.
5. **P2: policy and validation conventions.** Choose initial adoption behavior,
   intent-policy discovery, cross-implementation reuse rules, record validation,
   and merge-resolution rationale. Current tests record policy snapshots but use
   manually supplied resolver inputs rather than a full registry.

The next small experiment should use two local subprocesses and an ignored durable
mock executor with idempotency disabled, killing the driver at each effect/commit
boundary. Measure duplicate dispatches, lost publications, and conflicting resume
observations, then repeat with idempotency and transactional head updates. This
would test the most consequential gap without cloud resources or DML changes.
