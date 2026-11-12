# Shared exercise repository and immutable indexed contexts

Status: **COMPLETE/ACCEPTED/STOPPED**, isolated/uncommitted. [Results and limitations](../../../../dml-design/maintenance/relational-testing/SHARED-INDEX-RESULTS.md):
ONE demo4cases24getters/275unique reads/complete fork+context transfer; SAME102checks; final194pass.
Original23pass1fail warning/JSON transport and failed UNIT regex preserved, source/diagnostics
archived; COPY separates result data from warning logs. No main/production integration, commit/push,
new native entity/API or restart of completed incremental controller. Owning
[bounded plan](../../../../dml-design/maintenance/relational-testing/SHARED-INDEX-PLAN.md).

One repository contains a parentless P0 with empty index/run declaration, shared fixture F, and
case targets CN. Each target anchors two independently branched checkpoint tips, preserving forks.
Publication PN parents are EXACTLY `(PN-1,CN)`. Its tree binds `exercise-index` to a new immutable
DAG with `case-NNN` → description links, plus immutable run DAG. Earlier snapshots remain exact.
NO mutable exercise/publication refs. External immutable per-publication handles provide retrieval;
external file write + storage commit is not a cross-system crash-atomic protocol.

Each indexed description links native context and observations DAGs and records target/root IDs
as BYTES/LIST data. Context includes scenario/parameters/source scope/captures/limits/expectations.
Observation includes actual returned values/call count/errors and optional deliberate mutation
subject, NOT a historical checker pass/fail supplied to invariant SQL. Exact role/type/root/parent/
occurrence/prefix/fixture custody checked during pure projection of extracted native facts.

- `exercise.py`: fixed builtin map/get scenarios, ordinary profile authoring/publication.
- `project.py`: ONE unchanged generic extraction over final PN; pure indexed profile projection,
  typed per-case availability and old-publication interpretation.
- `check.py`: ONE immutable analytical pool, per-case READ_ONLY/TEMP scoped predicates. Shared bad
  graphs never become available to unrelated cases; context source contract independently checked.
- `run.py`: bounded4-case24-getter demonstration/export/fresh import/case checks, no DB/lock copying.
- `test_shared.py`: native and fact-level corruption/absence/context/boundary/rollback sensitivity.

Initial cases normal42/equal42-fresh/native-valid wrong-result43/normal43. Repeated native computation
content shares storage but never skips fresh calls or collapses actual occurrence/target identities.
The generic native schema/extractor/old invariant SQL and original tests are unchanged. SQL view
scope becomes TEMP only; invariant predicates unchanged. Expectations are outer assertions, not
recorded answers fed into queries. Normalizer interprets BYTES IDs explicitly; parent edges, NOT
those datum values, make final-PN export retain target histories. Cases branch from F, not older
publications, keeping semantic scope separate from publication retention.

Conditional standalone command (NEW directory, prepared worktree/core/runtime required):

```sh
python -I -B spikes/relational_invariants/shared_index/run.py \
  build/relational-spike/shared-index-v1/demo
```

Tests use the same isolated `--noconftest` collection/tool environment as prior spike. Complete
collection still requires existing explicit incremental fixture plugin/pins; this module does not
alter it. Missing tool/native prerequisites stop, no implicit build/download/install. No destructive
storage fault in shared repo; those separate existing foundations remain isolated. No generic
scenario evaluator/cache framework/index role promotion/suite replacement/security/hermeticity/
codec independence/installed/platform/five-minute assurance. No native19/GHA/VP-001 work.
