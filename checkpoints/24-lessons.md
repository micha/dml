# Checkpoint through Iteration 24: what we have learned

Date: 2026-11-03. User requested a checkpoint and review of learning so far.
Status: retrospective synthesis, not a new specification, engineering plan or implementation GO.

Implementation is locally verified clean at `59b38303fe2f4c89d6fce3b01933f7260eb28320`.
Iteration24 is independently accepted, published and stopped; its
[review](../iterations/24-captured-ordinary-calls/REVIEW.md) and
[results](../iterations/24-captured-ordinary-calls/RESULTS.md) own delivery evidence and qualifications.
This checkpoint includes accumulated design notes and Iteration20–24 planning/review records,
including the deferred original Iteration20 candidate. Local design commit only; no push or runtime restart.
Checkpoint hygiene removes ONLY terminal blank-line suffixes from Iteration21/23/24 `RESULTS.md`
(4/1/3 LF bytes respectively); their text and substantive historical claims remain unchanged.

## 1. The research goal has stayed stable

DML should make agent-led research inspectable: what was requested, which implementation and inputs
were selected, what actually ran, what was reused, and what evidence was recorded. It supplies low-level
recording, repository and exchange mechanisms—not scientific certification or a research-policy engine.
Python supplies orchestration and control flow. Ordinary result sub-DAGs supply researcher-chosen detail;
sidecar observers can consume history without special producer hooks.

Recording a reference is not capturing its external contents. Capturing some internals is not proof of
complete capture. Neither a graph nor passing tests certify that a methodology or conclusion is sound.
The observer work demonstrated retrospective corpus curation, not a completed generic reader or UI.

## 2. Three identities must not be conflated

| Question | Relevant distinction |
| --- | --- |
| What exact description was recorded? | Immutable record/content identity and retained graph/history |
| Can this request reuse a selected result? | An explicitly defined computation/reuse identity |
| Did another trial actually occur? | Distinct request and attempt occurrence identifiers |

Every reuse hit is a NEW request, but not a new attempt or independent observation. Fresh attempts may
produce content-identical results. Their empirical occurrences remain distinct. Polling, importing,
selection and adoption are not fresh computation.

This separation is demonstrated by the repository/execution/reuse slices, not merely vocabulary.
A generic native identity-facet/mask system remains unimplemented; example-specific keys are not that system.

## 3. Value identity and source provenance belong on separate tracks

The most consequential correction was Iteration20's redirection away from projecting selected fields
out of a provenance-heavy input DAG. Computational argument values and their actual sources need
separate representation from the outset.

- A MAP datum contains typed values via datum IDs, not source-node references.
- Recorded construction/access retains actual source relationships outside that datum structure.
- Equal values do not imply a single global origin. Source association belongs to THIS invocation.
- Standard graph-level invocation is argument-map NODE -> result NODE. Value-oriented callable access
  does not implicitly provide repository/provenance navigation.
- Explicitly supplied provenance data is itself a computational argument and participates in matching.

The [recorded-map prototype](../../dml/docs/recorded-argument-maps.md),
[internal builtins](../../dml/docs/internal-builtins.md) and
[composed-node calls](../../dml/docs/composed-node-calls.md) demonstrate successive bounded versions.
Existing normal-return loading already supported computed sources; a new arbitrary-root extraction
primitive was not needed. Native Datum and Node remain different concepts.

The example is now concrete: `add(13,29)` and `add(29,13)` have different named-argument values and
therefore different upstream keys. Both return42. Their downstream `{x:42}` MAP values match, enabling
selected double reuse while preserving different requested upstream producers and the OLD double's
original executed producer chain. This does not require commutativity normalization.

## 4. Intent equivalence is a declaration, not a correctness proof

The user clarified that same-intent membership declares interchangeable result semantics across
implementations. An accidental defect violates that intent; it does not redefine the intended meaning.
Iteration19 demonstrated intent-scoped reuse across two local bindings and explicit entry removal.
It did not demonstrate actual Docker-to-Batch cross-adapter reuse.

There is no single universal key selected for every prototype:

- Early reuse deliberately required exact intent/binding/full-input matching.
- Iteration19 explored intent/full-input matching across implementations.
- Iteration20–22 explored intent/full argument-MAP VALUE matching with separate provenance.
- Iteration23 added a computational capture key: scale values affect computation; the supported
  equivalent getter versions and equal-valued constant sources retain different provenance without
  necessarily partitioning that key.
- Iteration24 deliberately uses conservative verified binding/environment identity plus full MAP
  value. It does NOT establish arbitrary ordinary-callable or recursive closure equivalence.

These are explicit, separately scoped policies; later examples do not silently change earlier helpers.
Logical intent alone is insufficient when captured constants change the requested computation.
General capture-aware equivalence remains an open design question.

## 5. Selection, fresh work, adoption and lifecycle are independent

Versioned selections can retain several input choices and differ across branches. Fresh work does not
automatically replace the chosen reusable attempt. Adoption is explicit. Removing one entry preserves
other entries, old selections and old branch history; a default miss can request fresh work without
rediscovering or automatically adopting history.

Implementation selection/default promotion is separate from reuse policy. Advisory supersession can
record a correctness fix versus operational replacement without deleting results or automatically
invalidating them. Historical as-known-then knowledge differs from explicitly selected later knowledge.
Persistent result restrictions were considered and deferred, not implemented.

A poisoned selection on a consumed reuse path is not an ordinary miss. Exactly which unused selection
framing is validated on explicit fresh paths differs by documented example; no universal fallback rule
should be inferred from one helper.

## 6. Captures bind dependencies at creation, not invocation

Dependencies can be callable bindings, constants or other nodes. The distinction is binding time,
not dependency type. Invocation arguments are supplied later. Moving convenience defaults must not
retarget an existing closure.

[Iteration23](../../dml/docs/closure-bound-dependencies.md) demonstrates fixed getter/constant captures;
[Iteration24](../../dml/docs/captured-ordinary-calls.md) demonstrates actual captured ordinary add/double
calls. The latter supports separate outer and inner reuse: an outer hit skips all inner requests;
a fresh outer call may create a new inner request satisfied by an old inner attempt.

Actual graph links retain dependencies; embedded ID strings alone are not retention edges. Construction
order and initial-versus-final attempt links avoid self-ID cycles. Source-sharing reduced the composed
semantic graph without raising existing limits: add receives the ORIGINAL argument-map node, and double
receives the exact returned add node.

The installed Iteration24 story recorded10 requests,8 attempts,5 direct LOCAL child launches and14
getter positions. Immutable operation content can deduplicate while separate owning ledgers retain
actual positions. The outer adapter is fixed, example-local and synchronous in-process; leaves use the
unchanged local execution mechanism. This is not a general evaluator, recursive scheduler or sandbox.

## 7. Repository and execution boundaries are part of correctness

The earlier spiral established immutable snapshots, ordered commit history, transactional refs,
Python repository operations, scoped named DAG lookup and inspection. Pinned transfer preserves
complete reachable objects and ALL parent history, not mutable execution authority or external resources.
Explicit returned refs preserve caller heads instead of silently merging execution into orchestration.

Across local, SSH and local Floci Batch profiles, recorded request identity, attempt identity,
provisional publication, validated completion and cleanup remain distinct. A saved observation handle
is not live process ownership. Service success is not DML completion. Missing final history is UNKNOWN,
not invented computational failure. Recorded success can coexist with cleanup failure.

Public successful-history validation supplies producer authority; a plausible return-node shape or
response flag alone does not prove success. Validators must preserve exact requested versus producing
Q/T/R associations, complete parent history and actual publication boundaries. The fixed synchronous
composition work further exposed the need for short recording scopes and explicit direct-child custody.

These demonstrations are bounded cooperative protocols, not exactly-once external execution,
durable detached supervision, production AWS compatibility or general process-tree recovery.

## 8. Validation must serve the question, not become the experiment

The spiral taught us that focused behavioral checks and concrete installed workflows are primary;
CI is complementary portability/regression evidence. Independent inspection of SAME stopped history
can test provenance without repeating computation. Metadata readiness alone can miss a real event path:
Iteration24's first activation failed in controller logging before leaf launch and remains retained
as a separate partial UNKNOWN context.

Reporting/tooling can fail after tests pass. Preserve each stage's actual outcome rather than
collapsing it into a green label. Iteration24's original full command exited1 after native7/pytest3354
passed; generated coverage source labels prevented reporting and later stages. Approved exact label
exclusions, reporter regressions and resumed unchanged remaining stages completed combined validation
without replaying the47-minute suite. The original command remains FAILED and Python JUnit absent.
Maintained canonical code remained measured at100%; excluded scaffolding is not claimed tested.

Failed probes, weak oracles, reconstructed evidence, EOF/source-byte qualifications and warnings matter.
A later pass is neither a diagnosis of an earlier failure nor proof that every branch/platform was tested.
The [owning validation policy](../../dml/docs/validation-policy.md) remains the authority.

## 9. What remains unresolved or outside demonstrated scope

- Native19 investigation is PAUSED. Actual named-resource/semaphore controls established a legal
  ENOENT mechanism, NOT attribution of the original hosted failures or a completed production fix.
  [VP-001](../maintenance/validation-policy/EXCEPTION-VP-001.md) remains OPEN/UNKNOWN, coordinator-owned,
  with its existing revisit conditions and no standing waiver.
- Development GHA remains disabled; Iteration20–24 local evidence is not fresh all-platform assurance.
  Release workflow remains active. This checkpoint does not query or change either workflow.
- Builtins are a fixed installed Python surface with exact version dispatch; native C/CLI invocation,
  a general callable dispatcher/evaluator and arbitrary recursive captures are not demonstrated.
- Reuse remains explicit bounded known-slot/table conventions, not automatic global cache discovery.
- Installation/resource management, general GC/excision and production provisioning remain design or
  isolated feasibility work, not delivered lifecycle systems.
- General deterministic research visualization/UI remains a goal, not a completed observer product.
- Cooperative value-only interfaces are not security isolation or complete dependency-capture guarantees.

## 10. Suggested review questions—not decisions or a next-turn plan

1. Are node calls, value-oriented access, captured dependencies and separate provenance now the right
   conceptual foundation, even though their engineering conventions are still example-local?
2. Should the next learning goal deepen computational closure identity/equivalence, generalize a narrow
   common invocation seam, or make the recorded nested story easier to inspect?
3. Which prototype conventions have earned promotion into maintained reusable APIs, and which should
   remain replaceable examples? Avoid treating accumulated role names as a finalized architecture.
4. How can future acceptance remain proportionate: one meaningful story, targeted independent evidence,
   explicit qualifications and no automatic repeated full-suite/computation rituals?

No option is selected here. All completed workers and runtime activity stay stopped; future planning
and implementation require their own user direction and authorization. Historical notes remain intact.
