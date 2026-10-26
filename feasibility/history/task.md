# Computational-history model

Read `../WORKER.md`; you own only `feasibility/history/`. Start immediately.

Build an executable small Python model using the standard library (or pre-existing
project environment) of ordinary immutable content-addressed DAG data, commits,
heads, and occurrence IDs. It is a feasibility model, not DML bindings or an
approved schema. No production DML modifications or heavy C builds.

Exercise deterministic tests for:
- distinct requests and attempts with identical binding/result contents;
- cache hit vs independent fresh trial; explicit reuse despite default-off;
- fresh execution vs adoption as selected reusable execution, branch isolation;
- installation description/HCL -> resolved resources -> resulting bound closure,
  including two installations yielding identical closures vs changed binding;
- one request with multiple attempts, unknown outcomes, and crashed adapter resume;
- bounded working/done calls with incremental DAG publication, recorded failure,
  cleanup failure separate from successful result, later remediation;
- commit/merge event correlation, conflicting selection, and two simultaneously
  recorded lifecycle updates without overwriting observations.

Look actively for ambiguity: closure identity versus incidental resource outputs,
mutable names versus actual artifact versions, retaining reusable execution after
resource excision, identifying each actual external execution when internal retries
are hidden, and representing adapter progress without circular hashes or mutable
records. Demonstrate at least two naive-design counterexamples and candidate fixes,
clearly distinguishing what tests establish from choices baked into your model.

Return scripts/tests runnable with `python3 -m unittest` or equivalent, a compact
scenario transcript/results fixture, and prioritized report. Do not declare that
ordinary DAGs or content IDs alone ensure complete provenance. Include which
minimal assumptions make the model work and which require user design decisions.
