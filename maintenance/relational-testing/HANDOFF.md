# Relational and incremental testing — session handoff

**Current successor state:** bounded incremental prototype is **COMPLETE/ACCEPTED/STOPPED**;
read [results](INCREMENTAL-RESULTS.md) and [coordination](INCREMENTAL-COORDINATION.md) before
continuing.49focus/sole21Q15T4E5P6C6reuse/SAME853/final169 pass, original preparationRAW1 and
intentional sensitivityouterRAW1 preserved. New12 spike files also UNCOMMITTED/base15555c0;
no main integration/commit/push/standing restart permission. Random sampling deferred; GHA/native19/
VP001/main ownership boundaries unchanged. The handoff below preserves the EARLIER unbuilt-controller
state and next planning recommendation; those are historical, not current as-built/authorization.

Status: user requested this handoff because context is large. This is documentation/context
preservation, NOT a new implementation GO, commit/push request, extra-agent delegation or
permission to rerun completed experiments. Completed isolated spike slices are stopped.

Subsequent planning checkpoint: user **“agreed. proceed!”** authorized preparing the proposed
[design](INCREMENTAL-DESIGN.md), [example](INCREMENTAL-EXAMPLE.md) and
[conditional implementation handoff](INCREMENTAL-HANDOFF.md). Candidates prepared for review;
this supersedes “first prepare concrete plan” below only as completed documentation work,
NOT implementation GO or a new run/agent/commit/push. Original evidence and limits stay intact.

The user subsequently stated **“reviewed. GO”** for those bounded candidates. See current
[coordination](INCREMENTAL-COORDINATION.md) and [concrete pre-edit plan](INCREMENTAL-PRE-EDIT.md).
Pre-edit acceptance is pending before coding/runs; GO supersedes historical pending-GO wording
ONLY for this isolated scope, not preservation/main ownership/dependencies/publication limits.

## Read first / authority boundary

1. Machine instructions `/home/ssm-user/AGENTS.md`, admin index, then project AGENTS.
2. This handoff and the spike [README](../../../dml-relational-spike/spikes/relational_invariants/README.md).
3. Latest [parallel replay report](../../../dml-relational-spike/spikes/relational_invariants/PARALLEL-ORACLE-RESULTS.md).
4. [Authority gaps/failure](../../../dml-relational-spike/spikes/relational_invariants/AUTHORITY-RESULTS.md)
   and [paired assertion map](../../../dml-relational-spike/spikes/relational_invariants/PAIRED-TESTS-RESULTS.md).

This document preserves user direction, actual spike behavior, assistant recommendations,
open decisions and scope. It is not a DML specification or an approved next engineering
handoff. Earlier design/performance stops and separate Iteration25 permissions are not
inherited by this work. Owning [validation policy](../../../dml/docs/validation-policy.md) remains.

## Locations / preservation

- Design notes: `/work/repos/micha/dml-design`, HEAD
  `e9194ebbfe32e8e3ffb6c7996d0b403c7aa9a9b9`; pre-existing dirty AGENTS/README/discussion,
  Iteration25 notes and test-performance notes. Do not overwrite/reset/commit unrelated work.
- Isolated implementation worktree: `/work/repos/micha/dml-relational-spike`.
  Branch `spike/relational-invariants`, base/HEAD local master
  `15555c01e4db19a20b4de7049f776c4d995bd5e0`. ALL spike source/docs are UNCOMMITTED under
  `spikes/relational_invariants/`; ignored evidence/build/dependency environment under
  `build/relational-spike/` and `build/spike-native/`. Do not discard/remove this worktree.
- Main `/work/repos/micha/dml`: same Git HEAD at last observation, but unrelated dirty
  Iteration25 implementation by existing window-2 worker. This session did NOT edit its
  maintained files or use/rebuild its shared builds. Read its current coordination before
  any contact/action; both shared builds/source are worker-owned under separate GO.
- No spike commit/push/CI requested/performed. Development GHA remains disabled, no enable/run.
  Native19 investigation PAUSED/private candidate retained; VP-001 OPEN UNKNOWN/no standing
  waiver. Nothing here diagnoses older failures or grants global/cloud/service/image/release scope.

User initially requested read-only discussion, later explicitly authorized an isolated worktree
spike and successive bounded comparisons. Dependency installation was separately approved by
“sure”. This handoff request adds documentation only; seek a bounded next plan/GO before new runs.

## How the idea evolved — conceptual direction

User's central intuition: repeated graph validation should collapse when exercised data are
normalized into relational facts. Architecture agreed in discussion:

1. **Exerciser:** operate on real DML; retain immutable histories plus action/error/before-after/
   supplied-evidence observations needed for assurance not present in final repository state.
2. **Normalizer/indexer:** extract relevant data conservatively, preserve context/errors, load
   objects once and keep distinct occurrences/relationships/snapshot availability.
3. **Checker:** independent invariant queries derive distinct sufficient obligations, evaluate
   shared claims once and map counterexamples to affected cases. SQL does not automatically
   discover the globally minimum proof; each invariant defines relevant grouping/context.

Relational DB is a derived analytical index/projection into full evidence, not replacement
truth or a security/full-capture guarantee. Keep observation rows even when their check work
is deduplicated. Objects may be global/content-addressed; availability remains repository/case
specific. Equal values must not erase selected producer/occurrence/provenance distinctions.

## What actually exists

The spike uses real native low-level getters and separate, independently expressed SQL.
Initial exercises call shipped map/get v1/v2; subsequent work uses retained real Iteration22
history or fresh HOST metadata fixtures calling existing test functions unchanged.

- Normalizer extracts each unique `(native kind, content ID)` once per physical repository;
  traverses all parents/composite children; no builtin Inspector/transfer semantic validation
  during extraction. Missing records fail explicitly.
- Existing original assertion bodies remain byte-exact; fixture execution for paired cases is
  HOST-substituted, not real child/interpreter/deadline/custody assurance. OS launches/network
  blocked. No existing tests removed or thresholds/deadlines weakened.
- Scopes include request/snapshot/control/intent/binding name/depth and packet job/expected/
  receipt/bundle root+fingerprint where relevant. Original verdicts are separate and NOT SQL inputs.
- Shared immutable pool/projections; per-case availability and ancestry checks; object-description
  disagreements rejected. Cached structural projections are NOT cached completed success proofs.
- Concurrent oracle: READ_ONLY persistent pool, TEMP tables/views/materializations per connection;
  each thread owns/reuses its connection; activation transaction rolls back on failure.
- No persistent exercise/verdict caching, dependency invalidation or DML-managed test controller
  has been implemented. Current sharing is within retained-data oracle runs, not skipping future tests.

### Important source files

Under worktree `spikes/relational_invariants/`:

- `exerciser.py`, `normalizer.py`, `checks.sql`, `checker.py`, `run.py`: first map/get pipeline.
- `compare_history.py`, `reuse_checks.sql`, `reuse_checker.py`: retained-request comparison.
- `embedded.py`, `concurrency_probe.py`, `schema.py`, `scope_schema.py`: batch/transaction schemas.
- `paired_trace.py`, `paired_runner.py`, `paired_checks.sql`, `test_pairing.py`: paired test slice.
- `capsules.py`, `selection_checks.sql`, `test_selection_pairing.py`: independent header projection/
  broader authority negatives. Preserve parse errors and exact comparison contexts.
- `oracle_replay.py`: SAME-fact isolated/shared/scoped materialization replay.
- `parallel_oracle.py`: immutable pool and connection-local parallel case readers.
- `test_*` and reports: focused sensitivity controls and actual evidence pointers.

## Actual evidence, not interchangeable gates

| Stage | Result / qualification |
| --- | --- |
| Initial8/32-checkpoint exercise | 94/118 unique objects vs725/3257 summed separate-root memberships;4 operation descriptions,24/96 current trace positions. These are theoretical memberships, NOT measured old validator reads.16 focused pass. |
| Retained real requests4/6 | Actual existing validator54,628 reads of473 distinct IDs; normalizer473 reads and EXACT same typed-ID set.42 exports/24 scans. Partial SQL answers match; both systems reject equal-value/wrong-producer native mutation.31 combined focused pass. Timings roughly tie at this tiny scale. |
| Embedded batch overlap | 368→473 objects across two overlapping batches. Uncommitted partial/marker invisible; old reader snapshot stable after commit; fresh reader sees complete batch.51 combined focused pass. Write skew explicitly demonstrates snapshot isolation is NOT serializability. |
| First paired12 | 12 original-body instances +2 harness guards;97 scopes/9 rejections agree.3,454 per-case normalized records vs950,633 setup+body reads, with DIFFERENT read/assurance scopes. Partial map, HOST fixtures; no equivalent-work/suite speedup. |
| Expanded authority | 32 additional negative instances+prior12+11 pure guards=55 pass48.40s.218 scoped verdicts/65 rejections agree.8,154 memberships/4,280 distinct pooled IDs. Complete relational phase26.393s; broader authority was SLOWER than original selected setup/body. |
| Shared replay | SAME44 frozen cases/rules: fresh per-case17.373s; shared13.059s; shared+scoped10.315s INCLUDING setup.8 sensitivity controls pass8.43s. No native reads/computation/DML import; single timings. |
| Connection-local replay | SAME44/218/65 at1/2/4 readers:6.564/4.473/3.495s INCLUDING1.109s pool setup.6 isolation controls pass6.63s. Persistent pool SHA unchanged; no DML import. One host, ordered single trials, NOT full-suite/statistical/portability proof. |

See each report, not an aggregate invented all-green gate. Latest report and evidence:
`build/relational-spike/parallel-replay-v1/{capacity,result,workers-1,workers-2,workers-4,final-audit}.json`.
Input corpus fingerprint:
`11e5686985a03309ceb12537dd0287a2925820204a16a146521489b388ff9876`.

Other retained evidence: `retained-requests-v1/`, `paired-v1/`, `paired-final/`, `authority-v1/`,
`authority-gap-fix/`, `authority-final/`, `shared-replay-v1/`, `shared-replay-scoped/`, actual
focused XML/logs and source/static audits. ALL under ignored worktree build; don't clean them.

### Failure/correction lessons that must remain visible

- Initial binding smoke failed because libstdc++.so.6 wasn't resolved. Already-installed
  compatibility library path fixes invocation; no system/library install or ELF patch.
- First paired smoke failed collection: eager import needs `_core_fault`. Built only unchanged
  private test extension in OWN spike build; DML_BIN hints that import location. No CLI invoked.
- Summary initially double-counted pytest `current` symlink aliases; resolved paths/unique node IDs
  corrected it. Empty original summary stdout and raw assertion stderr in session transcript;
  standalone stderr disk log was NOT captured. Pure guard now covers artifact aliasing.
- Initial69 scope count omitted intent/binding/depth distinctions; final first-slice97 preserves
  them, and contradictory same-scope verdicts fail closed. Old number is historical.
- **Real oracle defect:** expanded authority gate RAW43pass/1fail. Completion-pointer swap exported
  a different bundle under identical headers. Bundle input was omitted from scope key; guard caught
  conflicting verdicts. Added root+SHA identity and independent root agreement. Raw gate preserved.
  SAME stopped packet roots support attribution; original transient projection bytes/pre-dedup event
  objects were NOT retained. New runs save observed events early. Not a DML runtime bug.
- Scoped materialization controls initially RAW7fail/1pass: regex required space after AS, while SQL
  has newline. Corrected whitespace matching/required-definition check; original XML/log retained.
- URI/name/source/packet framing, native hashes/order/budgets, ALL role cases, refs, true process/
  transport/custody/scientific truth remain incompletely ported. HOST success is not fresh child proof.
- Changing test architecture does NOT remove validation executed by DML during exercising.

## Environment / commands (reference only, not a restart instruction)

- CLI DuckDB1.5.2 exists system-wide. Python binding was separately approved: worktree-only
  `build/relational-spike/duckdb-env/`, stdlib venv without pip, official PyPI wheel extraction.
  Wheel SHA256 `70631c847ca918ee710ec874241b00cf9d2e5be90762cbb2a0389f17823c08f7`;
  metadata/wheel/receipt/raw failed smoke retained in `embedded-preparation/`.
- NixOS invocation prefix:
  `LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"`.
  No global/shared environment/source/profile modification for binding installation.
- Existing cached pytest/Hypothesis borrowed via process-local PYTHONPATH:
  `/nix/store/qx9y6qslvc3pw8mblqx77cm1viv2dyzq-python3-3.13.15-env/lib/python3.13/site-packages`.
- Native import build: `build/spike-native/_core.abi3.so` and `_core_fault.abi3.so`; built with cached
  vendored archives/owned worktree/Meson nodownload. Don't use/rebuild main shared builds.
- Spike targeted pytest used `--noconftest`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
  `PYTHONDONTWRITEBYTECODE=1`; paired test imports additionally need
  `DML_BIN=/work/repos/micha/dml-relational-spike/build/spike-native/dml` (CLI not invoked).
- Use NEW owned output/basetemp directories if a future approved run is needed; no rm/reuse of
  evidence paths or repeated-full-until-faster. Missing downloads/installations still need scope.
- Physical4/affinity8, unrestricted inspected cgroup ancestors, available~25GB supported bounded
 1/2/4 oracle trials.1GiB reserve+1GiB/reader is admission allowance, not guaranteed peak.
  Engine threads2 unchanged; no maintained automatic allocation/runner policy was selected here.

## Latest design conversation: incremental DML-managed testing

User sees opportunity to reuse test results like DML computation results so subsequent runs
can be cheap when only a subset of evidence changes. Direction discussed positively, NOT as-built:

- Reuse at exerciser, projection and assertion-result boundaries, with captured computation code,
  data, applicable context/evidence/limits and relevant dependencies/environment.
- Assertion implementation or indexer changes can reuse exercise evidence while recomputing
  affected downstream work. Implementation changes require fresh affected exercise to discover
  outputs; identical expected outputs alone cannot justify skipping a changed candidate.
- Pinned known controller DML can manage changing candidate DML, analogous to bootstrap compiler.
  Candidate must not grant itself cached passes. Keep independent storage/API/fault foundation,
  separate controller evidence store from fault-injected repositories. No controller revision/build
  has been selected/promoted; current checkout/full-suite validation must not be assumed.
- Basic bounded controller functionality could make pinning feasible; URI reference alone doesn't
  capture bytes/environment. Current common invocation/reuse helpers are not a generic test scheduler.
- Hybrid assurance likely: relational semantic obligations + direct mechanism tests. Moving all
  organization into the framework does not mean every test becomes SQL or fresh custody is cached.
- Cached verdict means historical check with provenance, NOT new exercise/coverage/platform truth.
  Never count retained coverage counters as fresh instrumentation without explicit policy/evidence.

### Property tests / determinism

Read-only review found no explicit @seed/--hypothesis-seed/derandomize project setting in either
worktree or maintained runner. Current cached Hypothesis6.151.10 profile `default`, derandomize=False.
Recent Hypothesis detects CI and defaults to its deterministic CI profile; behavior depends on
version/environment/test code. No seeding setting was changed. Local example DB/random exploration
can affect generated corpus. Stored actual cases/evidence are stronger for exact checker comparison.

User suggested deterministic occurrence IDs (excluding allocation races). No randomness is required
for uniqueness: serialized controller can use counter/sequence; fixed exerciser action trace can have
stable within-scenario identities. Assistant recommends separating stable scenario-position labels
from actual fresh-run provenance. Deterministic does NOT require identical IDs for distinct fresh
actual events. Exact schema, run namespace/counter, comparison rule and current Q/T generation changes
are OPEN, not implemented or silently approved as glossary/spec amendments.

### Explicit latest user decision: random sampling DEFERRED

User: “for now we can forget about ... re-evaluating a random sample of X% -- we can add that later
if necessary.” This supersedes earlier assistant recommendation of sampled fresh re-execution.
Initial proposed harness should use dependency-driven invalidation/reuse plus explicit fresh execution.
Do NOT include random10% audit/configuration in the first plan. No new sampling implementation.

## Resume recommendation — proposed next step, NOT GO

Assistant recommends a bounded end-to-end incremental orchestration prototype rather than more
unbounded oracle-only tuning. First prepare concrete plan for user review:

1. Select/pin exact controller code/build/dependencies and independent bootstrap checks/risk boundary.
2. One small existing test family: exercise evidence, normalization and assertions recorded through
   controller; no generic scheduler/cache discovery/cloud/native/storage change assumed.
3. Start conservatively: ANY candidate build identity change reruns exercise. Precise selective
   dependencies later; don't pretend unrelated code is irrelevant without a dependency model.
4. Demonstrate unchanged request reuses evidence/verdict; checker-only edit reuses evidence but reruns
   checks; candidate change reruns exerciser; explicit fresh request bypasses reuse. Sampling deferred.
5. Define content/provenance/scenario IDs, occurrence/run distinction, cache namespace, exact key inputs,
   versioned selection/adoption and artifact/coverage retention before implementing. Failures/unknowns
   cannot be promoted to cached passes. Preserve actual evidence on disagreement.
6. Keep originals alongside new paths until assertion map and negative controls establish enough
   assurance. No global minimum-proof or complete equivalence assumption from positive match counts.

Fresh session should begin READ-ONLY: read this handoff, inspect the isolated worktree/evidence and
confirm user's desired next bounded plan. This handoff request does NOT authorize implementation,
new suite/native/API runs, worker delegation, main integration, controller promotion, package/tool
changes, commits/pushes, GHA enable/run, global/service/cloud work or paused investigation restart.
