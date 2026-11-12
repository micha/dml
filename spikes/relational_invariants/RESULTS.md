# Spike results

This is the original map/get experiment. The subsequently requested real request/reuse
comparison is recorded separately in [retained-history results](RETAINED-HISTORY-RESULTS.md).
It measures actual54,628 reads over the exact473 normalized objects;31 combined focused
checks pass, with partial assurance and no convincing elapsed-speedup claim preserved.

## Scope and disposition

Implemented locally in `/work/repos/micha/dml-relational-spike`, branch
`spike/relational-invariants`, based on local master
`15555c01e4db19a20b4de7049f776c4d995bd5e0`. Spike files are UNCOMMITTED; no push or CI.
The main checkout's unrelated Iteration25 work was not edited. No runtime/native/public
API, diagram, existing test, threshold or deadline change. Development GHA remains unused;
this spike does not resume native19 or diagnose VP-001.

**Result: promising proof of the normalization mechanism, not a suite-performance result.**
The three components work on real immutable native DML history. The normalizer reads
unique records once; independent SQL catches selected semantic/structural violations.
Shared values and operation content collapse while source relationships, trace positions
and snapshot contexts remain distinct. See [scope and limitations](README.md#selected-checks).

## Retained positive runs

Evidence is under the ignored worktree directory `build/relational-spike/`.
Final schema/checker runs are `final8/`, `final32/`, `final8-result.json`,
`final32-result.json`, and `final-standalone-check.json`.

| Final run | Recorded checkpoints, excluding base | Unique native objects/read calls | Sum of per-root complete closure sizes | Unique operation descriptions | Current-checkpoint positions |
| --- | ---: | ---: | ---: | ---: | ---: |
| final8 | 8 | 94 | 725 | 4 | 24 |
| final32 | 32 | 118 | 3257 | 4 | 96 |

Both have **zero detected violations**. There are TWO distinct literal-source profiles
with ONE shared MAP value, TWO supported map/get bindings and FOUR operation descriptions
(two sources x two implementations). Repeated A,A calls retain two positions even though
the operation content is identical. There are TWO shared ledgers with THREE positions each.
Every checkpoint retains its separate context; the last checkpoint forks from the base.

The normalizer decodes each unique native record exactly once across supplied roots;
a test instruments `Transaction.get_record` to verify this rather than assuming it
from the normalizer's own counter. Its read leaves data.mdb SHA256 unchanged. It succeeds
with builtin Inspector construction blocked. Missing native records fail extraction.

The per-root closure totals are independently derived by recursive SQL over extracted
edges, including historical ancestors. They are **not measured baseline validator calls**
and are not all contemporaneous computation positions. The inventory's 42/186 historical
trace-position memberships are likewise distinct from the 24/96 current positions above.

Single final invocations took roughly 0.061/0.070s for extraction+DuckDB load, and
0.140/0.149s for checker setup/query/inventory (CLI process startup included). Extraction
alone was about0.0015s each. These are tiny local single observations, not statistical
benchmarks, whole-suite comparisons or an assurance that DuckDB always runs faster.
The real exerciser still invokes unchanged production Recorder validation.

## Focused validation

`tests-final.log` and actual `tests-final.xml`: **16 passed, 8.37s, true exit0**.
The earlier `tests.log`/`tests.xml` retain the initial14-pass stage before the external
position-count completeness check and standalone-unavailable-repository test were added.

Final tests cover:

- native positive history, equal values/distinct sources, repeated positions and fork;
- actual once-per-object record reads, no semantic-validator call, unchanged data.mdb;
- nine deliberate relational mutations: missing objects, missing profile field, wrong
  source name, unsupported URI, wrong result, noncontiguous positions, dropped final
  position against the exerciser's plan, wrong trace target and an empty root set;
- a native-valid but semantically wrong operation written into the actual repository:
  map/get returns43 rather than42; SQL identifies that exact operation ID;
- a nonexistent native root: extraction fails and preserves an error file, no DuckDB
  success database is produced;
- checker subprocess success with the original repository renamed/unavailable;
- 2/32-checkpoint scaling with the same FOUR semantic operation obligations.

No existing full suite, maintained coverage gate, installed acceptance story, platform
matrix or Valgrind was run. This is focused spike evidence, not production acceptance.
The native extension was compiled separately in `build/spike-native` using cached vendored
archives, `--wrap-mode=nodownload` and the unchanged existing project tool environment.
Native build/setup logs are retained; no package download/install/global setup was needed.
The existing tools profile still resolves to the same original generation/store path.

Early8/scaled32 JSON/databases are retained separately from final schema results.
An intermediate Markdown link check reported missing RESULTS.md before this file was
written; the completed links were checked afterward. No test failures occurred in the
focused spike runs. No original project failures are relabelled as fixed.

## Learning and next question

The useful normalization key here is `(native object kind, content ID)` within one
repository, with checkpoint roots/contexts represented separately. Normalization alone
cannot remove all production validation costs, nor decide that different exercised
code paths are redundant tests.

A next spike, if requested, should normalize ONE real Q/T/S/reuse scenario and compare
explicit per-object versus per-selection/per-request authority obligations. It would
need independent root/action/launch observations, old versus requested provenance and
contextual membership rules. Another option is auditing an existing retained scenario
without rerunning its computation. Neither next experiment nor production integration
is authorized by these results.
