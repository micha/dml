# Embedded concurrent normalization and checking

Status: isolated continuation complete, UNCOMMITTED on `spike/relational-invariants`.
No maintained DML/native/API changes, commit/push/CI, full suite or historical computation
replay. Original [retained-history comparison](RETAINED-HISTORY-RESULTS.md) remains distinct.

## Architecture exercised

ONE embedded DuckDB-owning process with separate connections:

- One normalizer writer publishes decoded immutable facts, roots, request contexts and
  a publication marker in ONE transaction.
- Checker readers run all their count/invariant queries inside their own read transaction.
- Common schema/views are initialized before concurrent work. Checker reads do not create
  views or mutate facts. Connections are created in their owning threads, with the same
  DB configuration (two engine query threads for this isolated probe).

[embedded.py](embedded.py) and [concurrency_probe.py](concurrency_probe.py) use only the
already-collected473-object history, not live DML repositories. The two overlapping batches
are the complete closures needed by retained requests4 and6. [schema.py](schema.py) holds
pure fact schemas; old normalizer/checker imports were refactored to reuse those definitions
without changing their schema or importing DML into the embedded checker.

The prototype still exercises selected SQL rules, NOT the entire existing public validator.
Embedded loading does not add the packet/capture/budget/custody proofs deferred in the
retained-history report, and these tests do not establish suite speedup.

## Actual synchronized overlap

A finite writer thread pauses on explicit Events, not sleeps. Independent reads happen at
known partial/complete-but-uncommitted points. A long-lived reader also spans the writer's
commit. All writer threads are joined, with finite failure barriers and retained errors.

| Reader observation | Published batches | Objects | Reuse contexts | Roots | Violations |
| --- | ---: | ---: | ---: | ---: | ---: |
| First committed batch | 1 | 368 | 1 | 2 | 0 |
| Writer has staged more objects, uncommitted | 1 | 368 | 1 | 2 | 0 |
| Writer has staged entire second batch AND marker, uncommitted | 1 | 368 | 1 | 2 | 0 |
| Same reader transaction after writer commits | 1 | 368 | 1 | 2 | 0 |
| Fresh reader transaction after commit | 2 | 473 | 2 | 4 | 0 |
| Reopened after ALL connections close cleanly | 2 | 473 | 2 | 4 | 0 |

The second batch contains473 objects including the368 already loaded. The union grows by
ONLY105 objects. Existing checkpoint membership and request occurrences remain distinct.
The probe process confirms DML was not imported. No original repository, PID or execution
adapter is accessed. Native/OS crash, power-loss/fsync and multi-process writer behavior
are not exercised; graceful reopen proves only the stated persistence boundary.

The standalone first probe is retained under `build/relational-spike/concurrency-v1/`;
final-source retained output is `build/relational-spike/concurrency-complete/`. The final
focused test also executes the event-synchronized subprocess against the final source.
It performs no DML computation; its one process internally owns the writer and readers.

## Admission and consistency safeguards

The loader does not blindly ignore primary-key conflicts:

- Existing same-key fact rows must agree exactly before insertion deduplicates them.
- Whole-object SHA256 signatures of the decoded fact sets detect missing/additional
  relationships for an already-loaded object, not just changed values in present rows.
- Identical batch replay is inert; changed content under an existing batch name fails.
- Unknown tables/columns, duplicate incoming keys, conflicting root metadata and missing
  typed edge targets fail, with rollback of staged facts and signatures.
- Publication is last, but remains in the same transaction as ALL supplied facts.
- A marker means **fully loaded**, not **semantically validated**; SQL still checks it.
- A truly empty owner is idle. Committed facts without any marker produce an explicit
  `unpublished_facts` violation rather than being silently treated as idle.

These decoded-fact signatures are NOT native DML content hashes, a security boundary,
full native codec independence, or a generic cross-repository proof cache. The keys and
checkpoint/context namespaces cover this ONE collected history; multi-run/repository
namespacing is not implemented. Readers have logical SELECT-only behavior, not separate
DB-enforced read-only credentials. Direct database edits can bypass loader conventions.

No automatic retries are implemented. The intended owner has one writer; engine support
for multiple writers does not imply concurrent overlapping batch loads are already safe
or conflict-free under the prototype's unique-key/fingerprint checks.

## Focused validation

Initial `embedded-tests-v1.log`/XML:47PASS,36.84s. Additional admission/idle guards then added.
Intermediate `embedded-tests-final.log`/XML:50PASS,38.73s. A final controller guard/test
preserves a writer's original error before readiness barriers rather than substituting
a timeout; its deliberate failure rolls back and joins the writer.
Final `embedded-tests-complete.log` and actual XML: **51PASS,39.91s,true exit0**, zero failures,
errors or skips. Final comprises31 previous spike controls plus20 embedded controls.
No timing assertion, full DML gate, threshold change, coverage exclusion, Valgrind, installed
acceptance or platform matrix. Tests and their stdout/XML are retained separately.

Embedded controls cover:

- Actual separate-thread writer/reader overlap, partial-state invisibility, stable read
  snapshot, fresh visibility, clean-close reopen and joined writer.
- Original pre-barrier writer failure surfaced, rollback preserved and writer joined.
- Rollback after objects, after contexts and after a staged publication marker.
- Identical replay/overlap dedup, changed replay, changed shared scalar, missing shared
  relationship, duplicate key, conflicting root, missing target, unknown table/column.
- Semantic checking after publication, empty idle state and markerless committed facts.
- Overlapping separate writer transactions committing disjoint appends.
- Same-row conflict raising DuckDB TransactionException; explicit losing rollback/no retry.
- **Write skew:** two snapshots both read two available rows, then disable different rows;
  both commit, leaving zero available. This deliberately demonstrates that snapshot
  isolation does NOT enforce an arbitrary cross-row invariant/serializability. The test
  passes by observing that limitation, not by treating the domain invariant as satisfied.

## User-approved isolated dependency preparation

User separately approved installing DuckDB1.5.2 Python bindings in this worktree.
Already-installed CLI is also1.5.2. No global/shared project environment or Nix source/profile
was changed by preparation.

Created `build/relational-spike/duckdb-env/` with stdlib venv without pip (pip is absent).
Downloaded the official PyPI CPython3.13 x86_64 manylinux wheel, verified its published
SHA256 and extracted it ONLY into that venv's site-packages. Wheel/version/provenance:

- `duckdb-1.5.2-cp313-cp313-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl`
- SHA256 `70631c847ca918ee710ec874241b00cf9d2e5be90762cbb2a0389f17823c08f7`
- Actual wheel21,429,837bytes; PyPI metadata, URL, receipt and wheel retained.

Initial smoke RAWexit1: `ImportError: libstdc++.so.6 ... No such file or directory`.
The library already exists in this machine's Nix runtime compatibility directory; adding
that existing path via invocation-local LD_LIBRARY_PATH gives smoke exit0/version1.5.2/
SELECT42. Original failed smoke retained, not overwritten. No new runtime-library download,
ELF/package patch, system/global loader change or hidden installation occurred.

Pytest is borrowed via invocation-local PYTHONPATH from the existing cached project tools
(Python3.13.15/pytest9.0.3), not installed into the new venv. The final test command disables
third-party plugin auto-loading for these focused tests; no maintained runner/config changed.
Old31 tests still execute, including their own imported native metadata mutation, not a
retired computation/fixture restart. Normalizer/checker bodies retain their prior behavior.

Evidence: ignored `build/relational-spike/embedded-preparation/`, `duckdb-env/`,
`concurrency-v1/`, `concurrency-complete/`, and all three actual focused logs/XML. [requirements-embedded.txt](requirements-embedded.txt)
pins the optional spike dependency, not a maintained DML requirement.

## Run the owned prototype

Use the already-prepared worktree environment and a NEW output directory:

```sh
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  build/relational-spike/duckdb-env/bin/python \
  spikes/relational_invariants/concurrency_probe.py \
  build/relational-spike/retained-requests-v1 build/my-concurrency-probe
```

The LD_LIBRARY_PATH prefix is specific to this NixOS host's existing compatibility
libraries. Normal environments with C++ runtime resolution need no such prefix.
Do not overlap independent CLI writers with an open embedded file. This is one-process
ownership, not a server or multi-process shared-file deployment.

## Disposition

Transactional batch publication plus stable concurrent checker snapshots works for this
bounded retained dataset. Keep one writer for now; arbitrary multi-writer domain invariants
need extra coordination. The next proposal could make validation obligations/materialization
explicit and measure equivalent work, but no production integration, removed tests, full-suite
optimization, daemon, commit/push or further native/runtime investigation follows these results.
