# Quint-driven DML trace interpreter

Status: agreed direction for the next isolated spike; not implemented.

## Authority boundary

This note records design decisions for the proposed interpreter. The [Quint feasibility
README](README.md) owns the evidence from the completed spike.
The [repository contract](../../../docs/spec-next/repository.md#refs) and
[Python API](../../../docs/spec-next/python-api.md#repository-and-transactions) own DML behavior.
This design does not change public APIs, the storage format, or the
[maintained validation scope](../../../README.md#maintained-validation-scope).

## Execution and observation

```text
Quint produces request histories → Python interpreter runs real DML
Quint checks observation records ← interpreter records what happened
```

- A history is an ordered list of attempted operations and their arguments, with enough setup
  information to replay it. Export requests, not predicted outcomes. Keep intentional rejection
  cases in scope: an attempted operation counts as a step even if it fails or leaves state unchanged.
- Map each in-scope action to the corresponding DML API call. The interpreter handles fixtures,
  symbolic IDs, live handles, and transaction boundaries; it does not predict DML behavior. Start
  with `create_ref` and extend the dispatch as new operations are needed. When testing transaction
  completion, model the mutation and the commit or abort as separate operations rather than hiding
  completion inside the mutation.
- Observe actual outcomes and relevant before/after state. Let Quint decide which rules apply and
  whether they pass. Missing evidence or an interpreter error is not a passing or unexercised rule.

Today [`ref_model.qnt`](ref_model.qnt) enumerates 121 bounded histories for its own model tests;
it does not export them for native replay. The [direct evaluator](exercise_ref.py) gets its native
histories from Python and Hypothesis, uses [`ref_binding.py`](ref_binding.py) to observe DML, and
sends those observations to the original Quint rule. Reuse the binding and verdict evaluation
for the first slice, but keep the evaluator importable without the Hypothesis-driven test driver.

## Choosing and replaying histories

- Normalize fixed regressions, bounded exhaustive exports, seeded simulation traces, and
  model-checker witnesses to the same request format. A checker can find a history that reaches
  an interesting condition in the model; replay tests whether DML handles it. A witness is one
  route to the condition, not coverage of every route or a proof about the implementation.
- Retain the exact history that exposed a bug as a fixed regression when useful. Pair it with a
  required generated scenario that keeps the relevant conditions and varies incidental inputs.
  For duplicate-create overwrite, arrange a ref at `A` and try to create the same ref at a distinct
  valid `B`. Vary the ref name and actual commit contents, not just symbolic labels. Require the
  concrete observations to exercise the duplicate rule and pass it; `unexercised` is not a pass.
- Save the original failing setup and requests, the failed rule, and the relevant observations.
  Log the generation seed when choices are random. Re-run saved requests against fresh DML after
  a fix without depending on the generator or seed. This differs from
  [rechecking saved evidence](README.md#replay-a-shrunk-transaction-failure), which evaluates old
  observations without running DML again.
- Shrinking is out of scope for this spike. Replay the original failing history as saved.
  The new generation, replay, and verification path must run without Hypothesis installed.
  Existing Hypothesis-driven spike and maintained tests are unchanged.

## Observe what did not change

Add a *frame condition* to check side effects on the published logical state of an isolated test
repository. With valid targets already stored before the tested operation, successful `create_ref`
adds exactly the intended ref pointing at the requested commit and changes nothing else. A duplicate
returns `invalid_state` and leaves the published inventory unchanged. The existing ref rule only
observes the tested ref; it cannot detect an unrelated change.

For small fixtures, use an independent read-only LMDB scan at transaction boundaries. Compare
stored keys and values, not counts, known-object lookups, or raw database-file bytes. Report added,
removed, and modified entries as evidence. Start with a test-only C executable that can be built
and tested separately from DML; consider linking only if measurement justifies it. The helper
reports changes, not whether they were allowed. Quint owns the rule. Do not add a maintained hash
to DML for this purpose: a stray write could bypass both the intended mutation and its hash update.
A full comparison costs a scan of the stored data, so any cheaper sampled check must make a narrower
claim. Published snapshots do not establish what happened inside an uncommitted transaction.

## First implementation checkpoint

1. Export the directed `create_ref` histories `[A]`, `[A, A]`, and `[A, B]` from Quint. Replay them
   through the existing binding with one fresh repository per history and one write transaction
   per request. Send the resulting records to the existing Quint evaluator.
2. Check `unexercised` on the first create and `pass` on both duplicate attempts. Keep the existing
   fabricated-observation control: `invalid_state` with a changed target is a violation. Change an
   exported history in Quint and verify that Python executes the changed requests without any
   Python changes. Run this checkpoint in an environment without Hypothesis installed.
3. Add the independent inventory helper and frame check as a separate increment. Check the exact
   single-entry diff on success, an empty diff on rejection, and detection of an unrelated change.

A generic VM, a new Quint-to-Python compiler, and maintained-gate integration are out of scope
for this checkpoint.
