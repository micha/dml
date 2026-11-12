# Connection-local parallel oracle replay

Status: bounded next step complete in the isolated worktree, UNCOMMITTED. No DML
computation/repository replay, native build/API change, dependency installation, main test
runner/configuration change, push/CI/full suite or native19 investigation.

## Ownership and isolation

[parallel_oracle.py](parallel_oracle.py) seeds the immutable shared fact/projection pool
from the SAME44 retained [authority cases](AUTHORITY-RESULTS.md), then closes its writer.
Worker connections open the persisted pool READ_ONLY. Every active availability set, root,
scope table, dependent view and case-materialized join is connection-local TEMP state.
Each worker creates, uses and closes its own connection in its own thread. It reuses the
connection across its assigned cases; no connection is shared between threads.

Activation/admission/loading/materialization is ONE TEMP-state transaction. Failure rolls
back to the previous complete case. Structural projection sharing and case-local
availability protections from [shared replay](SHARED-ORACLE-RESULTS.md) remain. Packet root,
byte fingerprint, receipt/job/expected claims, declared dimensions and depth remain separate
inputs. Eligibility/authority verdicts are recomputed, not globally cached as success.

This resolves the prior shared active-case limitation for this bounded test-oracle profile,
not a general distributed/multi-process writer system. Pool is immutable for a run; adding
facts concurrently is not implemented. No production integration/security sandbox/native
codec independence or complete original-validator equivalence follows.

## Actual isolation controls

[test_parallel_oracle.py](test_parallel_oracle.py): actual XML/log **6PASS,6.63s,true exit0**,
zero failures/errors/skips. Controls include:

- ALL44 frozen cases on two connections reproduce archived scoped verdicts and leave
  persistent pool bytes unchanged.
- Two explicitly synchronized threads hold DIFFERENT cases simultaneously, retaining
  their own counts/verdicts before and after a barrier; no sleep-based ordering.
- Deleting one connection's TEMP availability does not affect the other connection.
- Persistent pool write is rejected by READ_ONLY while TEMP case writes work.
- Deliberately invalid JSON during activation rolls back the entire previous TEMP case.
- Altered packet root remains rejected on a separate reader connection.

The owned smoke also confirmed READ_ONLY+TEMP support on installed DuckDB1.5.2. There were
no failed controls in this slice. Prior scope/extractor failures remain in their reports.

## Finite capacity admission and trials

Read-only machine observation: affinity8 logical CPUs,4 physical cores; active cgroup and
ancestors have unlimited cpu.max/memory.max. Host MemAvailable was about25.0GB at trial
admission. Bounded reader cap=min(4, physical cores, any known quota, memory after1GiB reserve
at1GiB per reader) selected4. This is a host-specific finite probe, not maintained resource
policy/provisioning or a measured peak-memory guarantee. Engine query-thread configuration
stays2 across all connections; it is engine configuration, not a promise of2 reserved CPUs
per worker. No global/CI/runner budget change.

Exactly ONE44-case trial each at1,2,4 reader connections, same input fingerprint/pool/rules.
Static round-robin assignment and exact case-set checks ensure each case is evaluated once
per round. Executor completion joins all worker tasks before the next round; no detached
reader service. Pool setup1.109s is included in the following totals:

| Readers | Checking+connection initialization | Including pool setup |
| --- | ---: | ---: |
| 1 | 5.455s | **6.564s** |
| 2 | 3.364s | **4.473s** |
| 4 | 2.387s | **3.495s** |

All218 archived verdicts, including65 rejections, agree in every round; transition/reuse/
availability faults remain clean. The pool SHA256 is identical before/after all rounds.
No DML module is imported by the trial process. Input fingerprint:
`11e5686985a03309ceb12537dd0287a2925820204a16a146521489b388ff9876`.

Four readers reduce this measured connection-local oracle total by about47% versus one.
This is NOT a whole-suite/five-minute/statistical/hosted-platform speedup. Sequential
1→2→4 order, cache warmth and shared host contention are not causally isolated. The earlier
10.315s sequential-owner replay used persistent mutable case state and a different connection
lifecycle; differences from6.564s cannot be attributed to parallelism. Temporary state also
changes persistence costs; no component-level causal profile was run.

## Evidence and disposition

Ignored owned evidence under `build/relational-spike/`:

- `connection-smoke/`: seeded pool and actual READ_ONLY/TEMP smoke log.
- `connection-tests-v1.log`/XML: six controls and44-case two-reader check.
- `parallel-replay-v1/`: capacity admission, immutable pool, each worker's case/verdict/time
  results at1/2/4, source input fingerprint, unchanged-pool SHA256 and aggregate result.

`oracle_replay.py` gains only an optional TEMP-view-kind hook; its previous default remains
unchanged. No source/test files outside the spike are edited. Original assertions are still
retained, and the SQL assertion map remains partial (packet/record framing/hash/budget/
capture/custody/OS obligations not ported stay unproved).

The next candidate is connecting this bounded oracle to a selected live test collection
without duplicating native extraction/setup, using explicit fixture/case publication and
assertion mapping. That needs a bounded plan; no original tests removed, production/API/
cache-framework expansion, additional workers/services, publication or further run is
triggered by this report. Existing GHA-disabled/native19-PAUSED/VP-001 uncertainty remains.
