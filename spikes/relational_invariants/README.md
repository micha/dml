# Relational invariant testing spike

Status: isolated feasibility spike at local master `15555c01e4db19a20b4de7049f776c4d995bd5e0`.
Branch `spike/relational-invariants`; no production API, existing tests or native code changed.

**Connection-local concurrent oracle:** [results](PARALLEL-ORACLE-RESULTS.md).
READ_ONLY shared pool/TEMP state per reader: all44 cases/218 verdicts agree at1/2/4 connections.
Totals including setup6.56/4.47/3.50s;6 isolation/rollback/read-only controls pass. Single bounded
host trials, NOT suite/portability proof. No DML replay or maintained runner/source changes.

**Shared/materialized SAME-evidence oracle:** [results](SHARED-ORACLE-RESULTS.md).
44 frozen datasets/all218 verdicts including65 rejections agree. Fresh replay17.37s versus
shared+case materialization10.31s INCLUDING setup (~41% less oracle time, not suite speedup).
4,280 pooled objects with case-local availability;8 sensitivity controls pass. Initial SQL
extractor7fail/1pass preserved/corrected. Sequential test-only owner; no DML replay/integration.

**Broader selection authority:** [results](AUTHORITY-RESULTS.md).
32 additional existing negative instances+prior12 and11 guards pass55.218 scoped verdicts,
including65 rejections, agree after a REAL omitted-bundle-input scope defect was caught
and corrected. Initial43pass/1fail retained. Full relational phase26.39s is NOT faster;
next candidate is amortized oracle work, not removed tests or weakened checks.

**Paired existing-test slice:** [results](PAIRED-TESTS-RESULTS.md).
12 existing assertion-body instances pass alongside independent scoped SQL;97 scopes,
including9 rejections, agree.3,454 per-repository extracted objects versus950,633 setup/body
reads (different scopes, NOT an equivalent-work speedup). HOST fixtures/partial assertion
map and remaining direct mechanism tests remain explicit. Two harness guards pass separately.

**Embedded concurrency followup:** [results](CONCURRENCY-RESULTS.md).
Atomic overlapping batch loading, stable reader snapshots and rollback/admission controls
pass51 combined focused tests. ONE normalizer writer/concurrent checker connections;
optional worktree-only DuckDB1.5.2 binding. Snapshot isolation/write skew limitations retained.

**Retained real request/reuse followup:** [results](RETAINED-HISTORY-RESULTS.md).
Current validator54,628 reads versus473 unique extraction reads; exact typed-ID sets and
both positive answers agree.31 focused tests pass, including both systems rejecting an
equal-value/wrong-producer native mutation. Selected SQL rules are not full validator
assurance; elapsed times roughly tie at this scale. No suite speedup or removed tests.

## Authority boundary

This directory owns only this experimental exerciser/normalizer/checker. It does not
replace DML's validators or establish a new application schema. The implemented builtin
profiles are described in [internal-builtins](../../docs/internal-builtins.md).
No new native LMDB entities/relationships are introduced; the existing diagram is unchanged.

## Three components

1. [exerciser.py](exerciser.py) uses real native repository transactions and shipped
   builtin Recorder map/get v1/v2. Two distinct source DAGs carry the same MAP datum
   `{"x": 42}`. Each recording calls get on source A twice, then source B once.
   Captured versions alternate. Immutable checkpoints share structure; the last forks
   from the base. It retains a manifest with checkpoint roots and the planned position
   count. There are no ordinary requests/attempts, process launches or simulated receipts.
2. [normalizer.py](normalizer.py) reads only through public low-level repository getters.
   It traverses all parent commits, tree entries, DAG roots/bindings, nodes and composite
   datums from the supplied roots. A `(native kind, content ID)` set deduplicates extraction
   across roots of ONE repository. Each unique record is read/decoded once. It emits
   explicit-schema JSONL facts and loads them transactionally into DuckDB. It does not
   call builtin Inspector, transfer export or semantic validators. Missing records abort
   extraction with retained error evidence. A 10,000-record safety bound limits this spike.
3. [checker.py](checker.py) imports no DML code and opens no repository. Independent rules
   in [checks.sql](checks.sql) surface counterexamples. It can run with the original
   repository unavailable. It preserves separate checkpoint membership and trace positions
   rather than treating shared operation content as distinct occurrence identifiers.

The bridge [engine.py](engine.py) uses the already-installed DuckDB CLI, not a Python
DuckDB dependency or service. JSONL permits inspecting the normalizer's output separately.

## Selected checks

SQL checks typed edge/root availability, selected profile fields/types/roots, source
DAG/name/native-node/value association, argument MAP versus entry/source values, duplicate
argument keys, exact map/get arguments and supported binding URI, map lookup result,
trace target/position constraints, and current checkpoint position counts against the
exerciser's plan. Every violation has an invariant label, subject identity and detail.

This is an intentionally partial checker, not full equivalence to builtin Inspector.
It does not yet check every ledger/profile shape, arbitrary builtin funcs, semantic
64-record/depth/transfer-byte bounds, cycles, hash independence, membership of dependencies
in the correct *prior* snapshot, reuse Q/T/S authority, mutable ref history, rollback or
execution custody. The normalizer uses the real native decode layer; codec independence
would need separate assurance. The manifest supplies the root/expectation boundary;
no query can discover history deliberately omitted from that boundary without an
independent source. No claim of whole-repository enumeration is made.

## Run

Build only this worktree's native extension using cached vendored archives and existing
project tools. No shared main-checkout build is used. If dependencies are absent, stop
rather than downloading implicitly:

```sh
# From this worktree, with the project's existing Meson/Ninja/Python tools on PATH:
meson setup build/spike-native --wrap-mode=nodownload
ninja -C build/spike-native _core.abi3.so

# All three components; NEW directory required (does not overwrite repositories):
python spikes/relational_invariants/run.py all build/my-relational-spike --checkpoints 8

# Or run the components separately:
python spikes/relational_invariants/run.py exercise build/my-scenario --checkpoints 8
python spikes/relational_invariants/run.py normalize build/my-scenario/manifest.json \
  --output build/my-normalized
python spikes/relational_invariants/run.py check build/my-normalized/facts.duckdb

python -m pytest -q --noconftest spikes/relational_invariants/test_spike.py
```

The bootstrap uses Python files and `_core.abi3.so` from THIS worktree. It is not an
installed-package acceptance or platform-matrix result. The `check` command needs only
stdlib Python and the DuckDB CLI; it does not bootstrap DML. `check`/`all` exit nonzero
when violations are found; CLI/database/extraction failures also remain failures.

## What normalization buys here

Whole-checkpoint reconstruction would revisit shared objects. The normalizer instead
extracts unique facts once; semantic queries process unique operation descriptions.
A recursive SQL inventory counts per-checkpoint memberships separately. These counts
illustrate avoided reconstruction, NOT a measured speedup against the existing suite.
SQL query planning still does work: materializing normalized facts does not automatically
memoize every subquery or eliminate production Recorder's existing validation calls.

Repeated identical builtin calls are still real calls: two A calls share operation
content but remain two ledger positions. Identical whole ledgers can also be shared
across checkpoints; the checker preserves their checkpoint contexts. These are not
ordinary request/attempt occurrence counts.

## Evidence

See [RESULTS.md](RESULTS.md). Focused tests include actual repository corruption at the
semantic level (native-valid map/get with result43 rather than42), deliberate relational
oracle faults, a missing native root, actual extraction read counts, unchanged data.mdb,
checker operation with original repository unavailable, and 2/8/32-checkpoint cases.
No existing full suite/coverage gate/CI or native19 investigation was run or changed.

## Inspect the retained request/reuse comparison

[compare_history.py](compare_history.py) already measured the current validator and
normalized the same retained objects. Its output is under
`build/relational-spike/retained-requests-v1/`. Read the report before interpreting its
counts/timings. To rerun ONLY the SQL checker, with no original repository access:

```sh
python spikes/relational_invariants/reuse_checker.py \
  build/relational-spike/retained-requests-v1/normalized/facts.duckdb
```

For the focused controls using collected evidence and an OWN imported native case store:

```sh
python -m pytest -q --noconftest spikes/relational_invariants/test_spike.py \
  spikes/relational_invariants/test_reuse_spike.py
```

The retained checker is a separate selected profile, not a reinterpretation of the first
map/get-only checker. It has external request contexts loaded into DuckDB, so omitted
roots/contexts can be checked against the known scenario boundary. No retained execution
or current-validator remeasurement is needed to inspect/query the database.

## Embedded concurrent owner

[embedded.py](embedded.py) replaces CLI invocation for the new concurrent experiment,
not for the older frozen runs. It uses separate connections in ONE process and commits
immutable facts, context/root membership and batch publication atomically. It checks
same-key agreement before deduplication, rejects inconsistent replays and rolls back
failures. Checker queries share one snapshot transaction. A loaded marker is not a
semantic success assertion. No live DML access is needed.

[concurrency_probe.py](concurrency_probe.py) provides a finite event-synchronized probe;
[test_embedded.py](test_embedded.py) covers transactions, conflicts and write skew.
See [preparation/run/evidence](CONCURRENCY-RESULTS.md) before use. The Python binding is
isolated in the ignored worktree environment, not added to maintained DML dependencies.
