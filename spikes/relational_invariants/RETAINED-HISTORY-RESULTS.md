# Retained request/reuse comparison

Status: bounded spike extension complete, UNCOMMITTED in the isolated worktree.
No push, CI, installed-story replay or production validator replacement.

## Actual history, not a newly fabricated scenario

Used stopped Iteration22 `story/replica.dml`, with its retained receipt and helper
source hashes. Existing real reuse requests4 and6 both select the original successful
double attempt2. Their requested upstream results come from producers3 and5; the OLD
executed double input came from producer1. All three upstream values are42. Their
source/result node identities differ and remain visible.

The relevant all-parent prefix contains **6 requests, 4 attempt occurrences** (8 initial/
final attempt DAG versions), 4 selections, 3 compositions, 5 distinct builtin operation
DAGs and7 trace positions. This is a prefix of the historical full8Q/6T/10-position story,
not a claim to have rerun that story or inspected its entire final641-object closure.

Four roots delimit the comparison: each reuse request's own submission Cq and satisfaction W.
The measured current helper bytes exactly match the receipt's four historical helper
hashes. The native extension is the independently compiled spike-worktree build, not the
old installed binary; no installed/hosted portability claim is made.

## Measured work on those same objects

ONE instrumented invocation of existing `composed_node_calls.inspect_request` for each
of the two reuse requests succeeded. Public read counters and whole-work counters were
installed only in that invocation, without modifying maintained code.

| Measure | Current public/example validator | Normalized extraction |
| --- | ---: | ---: |
| Record reads | 54,628 | 473 |
| Distinct typed object IDs read | 473 | 473 |
| Full transfer exports | 42 over21 distinct roots | 0 |
| Builtin retained-history scans | 24 over9 distinct roots | 0 |
| Mutable ref reads | 0 | 0 |

The **exact sets of `(kind, ID)` agree**, not just the two counts. Normalization extracts
those473 records once; it performs its own ONE union traversal, rather than calling the
production exports/scans. Record-read ratio is about115.5:1. The summed independent
per-root closure sizes are1672; that theoretical count is kept separate from the now
actually measured54,628 reads.

Counters include reads in public validation's temporary imported stores as well as the
retained source store. Content IDs deduplicate across those copies for this comparison;
this is not a general cross-repository proof cache. Serialization, packet framing,
occurrence/basis checks and budget enforcement are stronger/different obligations than
object decoding; their repeated reads are NOT all automatically redundant obligations.

## Independent relational checks

[reuse_checks.sql](reuse_checks.sql), through [reuse_checker.py](reuse_checker.py), checks
selected graph obligations: roots/contexts, selected profile shapes, own Q dimensions,
pinned selected slot, intent/full-MAP value matching, own-Q/OLD-T/R satisfaction, no T
owned by the reuse Q, successful S/Q/T/outcome/result ownership, selected completion's
basis ancestry, argument/source value agreement, exact selected upstream result links,
returned-node/value/trace ownership, fixed v1 map/get lookup, trace positions/counts,
single submission/satisfaction parent and exact W tree delta.

The positive checker reports **zero violations**, and both requested/selected answers
match the current validator's returned answers. Its provenance report shows different
requested upstream nodes for4/6, the same OLD producing upstream node, and equal datum
IDs for all three values. It does not collapse these relationships into a datum-origin
registry or make a new attempt on reuse.

**This is NOT equivalent assurance to the full public validator.** It does not yet
independently validate embedded V packet/header framing, complete captured-source/
interpreter/timeout binding contracts, all role/type/ledger combinations, every decision
control/reason/basis rule, all publication stages and parent/tree deltas, native codec/
hash independence, all depth/reached/transfer-byte bounds, cleanup/custody/external job
absence, every source-snapshot authority boundary, or scientific correctness of arbitrary
captured Python. Equal positive answers and one shared native negative do not establish
full behavioral equivalence. No existing tests or production checks have been removed.

## Native negative and focused tests

Combined original+extension suite: actual `retained-tests-v1.xml`/log **31PASS,25.96s,
true exit0**, no errors/failures/skips. These are focused spike tests, not a maintained
full gate/coverage/Valgrind run. An intermediate static whitespace audit flagged ONE
extra blank line at the end of the expanded spike README; the documentation-only suffix
was corrected before the final audit. This was not a test failure or runtime change.

Extension includes12 deliberate relational faults: wrong W request, wrong W attempt,
invalid producer request, new T owned by reuse Q, missing completion ancestry, wrong
equal-valued source, wrong builtin result, dropped getter, extra W tree entry, incomplete
selection shape, missing required root and empty contexts. Each specified invariant
actually catches its fault. The standalone checker returns0 for valid data and1 for
violations and consumes only DuckDB facts, not original repositories.

A further **native-valid equal-value/wrong-producer mutation** is built in an OWN case
store by public snapshot import (no database/lockfile copying). Its argument value stays
`{"x":42}`, but its selected producer3 relationship is replaced with producer1's result42.
The current validator rejects the exact-source mismatch; independently, SQL identifies
that exact malformed composition while the argument-value equality check still holds.
This distinguishes provenance authority from computational value reuse eligibility.

ONE extra public export after measurement supplies the473-record test fixture. Its reads
are explicitly outside the baseline measurement, not hidden in the extraction counts.
All original data.mdb hashes before/after baseline, normalization and fixture export agree.
Public baseline scratch stores are allowed ONLY under the spike's scratch directory;
original writes, process launches and network IO are blocked during measurement. No
historical PID is acted upon, no source is dispatched, no ordinary Q/T is created.

## Timing is not yet a speedup

Single instrumented baseline: about0.615s. Normalization including DuckDB load:0.118s;
reviewed checker including view setup, multiple CLI invocations and queries:0.489s.
That is **roughly the same elapsed time** at this small scale, not a convincing speedup.
The initial checker0.418s preceded added rules; it is not the final-check timing. No
statistical study or five-minute suite claim. Instrumentation and different assurance
scope prevent treating these timings as an equivalent-work benchmark.

The result is much stronger evidence for **redundant reads/work sharing potential** than
for elapsed performance. The next issue is making proof obligations explicit and keeping
the independent checker complete enough for the tests it would replace, while avoiding
repeated relational subqueries as well as graph traversals. That remains a proposal,
not permission to remove validation or expand runtime scope.

## Files and evidence

- [compare_history.py](compare_history.py): finite current-validator counters, guards and
  same-history extraction. Re-running it is NOT needed for inspecting these results.
- [test_reuse_spike.py](test_reuse_spike.py): collected-fact oracle faults and own-store
  native provenance mutation. Expects this worktree's retained spike evidence.
- Ignored `build/relational-spike/retained-requests-v1/`: provenance, baseline/per-object
  counts, manifest, explicit-schema JSONL/load SQL/DuckDB, first/intermediate/reviewed
  checker outputs, exact-ID/answer audit, summary, original-data hash receipts and fixture.
- `build/relational-spike/retained-tests-v1.log` and actual XML retain the31-test result.

Main DML checkout and its unrelated Iteration25 work remain unedited by this spike.
GHA remains unused; native19/VP-001 uncertainty is not investigated or diagnosed here.
