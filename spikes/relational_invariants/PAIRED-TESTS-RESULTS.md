# Selected existing tests: paired relational comparison

Status: requested three-group slice complete in the isolated worktree, UNCOMMITTED.
No maintained test/source/native API changed, no commit/push/CI/full suite, no installed
story or retired execution restart. This extends, not replaces, the earlier
[concurrency](CONCURRENCY-RESULTS.md) and [retained-history](RETAINED-HISTORY-RESULTS.md) evidence.

## How the comparison was constructed

[test_pairing.py](test_pairing.py) calls the selected existing test functions directly,
with their existing fixtures and original assertion bodies. Selected owner files and
six fixture/helper files are BYTE-EXACT to the worktree's committed base; SHA256 and Git
byte comparisons are retained in the summary. No copied/rephrased assertion body is
substituted for the originals.

For this test-only slice, generic fixture `_execute` is HOST-substituted. Only the fixed
local add/double sources and the deliberate exit23 variant are allowed; their captured
Python code runs in-process with a synthetic child argv. Its observation is HOST-authored,
not evidence of an OS child, deadline enforcement or interpreter/process custody. The
composed-node fixtures already have their own HOST publication seam. ALL OS launches and
socket connections are blocked. This is assertion parity over native graphs, NOT full
assurance parity with the original real-child fixtures.

[paired_trace.py](paired_trace.py) observes public repository reads, successfully committed
roots/refs and selected validator calls without changing their return values or errors.
It keeps only copied IDs/paths/outcomes, not live native handles. Uncommitted/aborted roots
are not published into the extraction census. Setup and assertion-body counts/times are
separate; helper scopes include both stages.

After the original body passes, [paired_runner.py](paired_runner.py) extracts the owning
caller's ALL committed roots once, through low-level native getters. Explicit decoded facts
are loaded into a NEW embedded database. Exerciser observations identify scope boundaries;
original acceptance/action verdicts are saved separately and are NOT inputs to SQL predicates.
[paired_checks.sql](paired_checks.sql) independently computes scoped verdicts and checks
successful state transitions/reuse associations. Normalization leaves each data.mdb hash
unchanged.

## Selected map and assertion boundary

| Group | Existing owner/function family | Instances | Selected independent relational obligations |
| --- | --- | ---: | --- |
| Value eligibility | `test_composed_node_calls`: full MAP hit (same/swapped upstream inputs), value miss/no automatic adoption | 3 | Captured func URI/full MAP matching, declared control/action, own Q/OLD T/R/no T owned by reuse Q |
| Completion eligibility | `test_reuse_selection_records`: nonfinal initial/publication packets, failed F plus successful cleanup failure | 3 | Native final-attempt status/outcome/result and pinned dimensions; incomplete/failure rejected, success despite cleanup failure allowed |
| Provenance | `test_composed_node_calls`: wrong R, inner literal instead of OUTER R, two-parent composition, two attempts for one Q | 4 | Exact selected outer result source, parent/slot/tree framing; selected attempt/occurrence remains separate from value |
| Branch state | `test_reuse_selection_records`: explicit adoption/sibling choices; `test_intent_scoped_edges`: removal and reselection | 2 | One-slot/one-key publication, unchanged other tree/table entries, distinct adopted occurrence, preserved old branch and reusable selected history |

Total: **12 existing test instances**, not12 entire modules. The original bodies' additional
assertions still execute (including bytes, exceptions, public packet validation and refs),
but not every assertion has an independent SQL counterpart. Original tests are not removed.

The SQL scopes do NOT yet independently cover all captured-source/interpreter/timeout
contracts, descriptor/token/raw bundle framing, every error class/message or before-write
boundary, full mutable-ref/byte immutability, all ledger/profile cases, depth/reached/byte
budgets, cleanup/custody/transport/OS truth, or arithmetic/scientific correctness. Carrying
depth in scope identity does NOT itself validate its budget. Original direct mechanism
assertions remain necessary; HOST mode does not upgrade them to actual process evidence.

## Final actual results

`build/relational-spike/paired-final/tests.xml` and log: **12PASS,20.23s,true exit0**, no
failures/errors/skips. Every selected original body ran and its paired comparison passed.
Two pure harness regressions additionally pass0.11s with their own actual XML: contradictory
same-scope verdicts cannot disappear during deduplication, and pytest `current` symlinks
cannot double-count artifacts. These are NOT native scenario tests.

Across the final12:

| Measure | Result |
| --- | ---: |
| Setup public record reads (instrumented) | 329,811 |
| Assertion-body public record reads (instrumented) | 620,822 |
| Per-repository unique normalized records/read calls | 3,454 |
| Observed validator calls before scoped deduplication | 321 |
| Distinct scopes, retaining intent/binding name/depth | 97 |
| Original rejected scopes also independently rejected | 9 |
| Acceptance/action disagreements | 0 |
| Successful publication transitions checked | 5 |
| Reuse associations checked | 6 |
| Distinct object IDs across all12 collected datasets | 2,014 |

All cross-case shared-object decoded-fact signatures agree. That shows a further pooling
opportunity, NOT an implemented global cache: each physical repository is read independently,
roots/context namespaces are still per case and there is no cross-repository proof reuse.

The two nonfinal cases normalize the caller's retained progress history, while the original
body also reads the private worker's later completion before rewinding its ref. Several
other cases include setup-only objects. Therefore **exact baseline/normalizer ID-set equality
is NOT claimed for all12**, unlike the earlier two-request retained comparison. Read counts
include production validation, serialization, private scratch/worker reads and assertions;
not all those reads are duplicate obligations or removable by changing test assertions.

## Timing, including normalization

Single final instrumented run, summed over12 cases:

| Stage | Seconds |
| --- | ---: |
| Existing fixture setup | 4.541 |
| Existing assertion bodies, including actions performed inside them | 7.750 |
| New native extraction | 0.057 |
| Embedded initialization/admission/fact and scope loading | 3.884 |
| Independent SQL setup/queries | 2.452 |
| New extraction + materialization + querying | **6.393** |

Do NOT call7.750 versus6.393 an equivalent-work speedup: original bodies also perform
native authoring/HOST computations and check more obligations. The observed paired test
runtime20.23s includes BOTH paths plus collection/measurement overhead. No five-minute
suite result, statistical timing or platform assurance.

| Family | Cases | Original body seconds | New relational phase seconds |
| --- | ---: | ---: | ---: |
| Eligibility | 6 | 5.493 | 3.218 |
| Provenance | 4 | 1.483 | 2.174 |
| Branch state | 2 | 0.774 | 1.001 |

The relational path is promising on the expensive value-hit/miss scenarios, but currently
slower on small faults/branch checks. Most new time is materialization/query overhead, NOT
native extraction. Fresh per-case DB/view/signature setup is not yet amortized. Scope-based
sharing is real, but the work-count advantage is stronger evidence than the elapsed totals.

## Corrections and limitations retained

- First smoke RAWcollectionERROR: eager imports require `_core_fault`, absent from the
  spike native build/default `build/check` location. No original assertion ran. Built ONLY
  the unchanged private test extension in `build/spike-native` with cached existing tools;
  DML_BIN points there for imports. No installed/runtime fault seam or native19 change.
  No CLI/OS child is invoked. The prepared smoke subsequently passed.
- Initial12-case paired-v1 passed21.11s. Initial summary RAWassertion failure counted pytest
  `current` symlink aliases as extra cases. Corrected ONLY artifact enumeration by resolved
  paths/unique node IDs; no test rerun to hide a failure. The original summary stdout file
  is empty; raw assertion stderr is in the session transcript, not separately captured to
  a disk log. Corrected summary and original case data remain. A dedicated guard tests it.
- Initial dedup count69 omitted depth/intent/binding context from scope identity. Final
  schema retains them and rejects conflicting verdicts for an identical recorded scope;
  corrected final count97 is the current result. Old321/69 remains historical, not promoted
  as sound budget-independent proof reuse. No actual contradictory verdict was observed.
- Baseline timings are instrumented and fixture mechanism is HOST. SQL is intentionally
  partial; no raw failure/unknown cause, native19 or VP-001 is diagnosed or waived here.

## Inspect or reproduce

Evidence directories are ignored and retained under this worktree:

- `paired-smoke/`: first collection error and owned test-extension build log.
- `paired-smoke2/`: prepared smoke's actual XML/native graph/comparison.
- `paired-v1/`: original12-case gate, raw summary failure/corrected summary and scopes.
- `paired-final/`: final12-case XML/log, two guard XML/log, summary/groups, every case's
  baseline, separate original verdicts, scope inputs, native root manifest, decoded JSONL,
  embedded database, verdicts/fault labels/timings and unchanged-data assertion.

A fresh run requires the already prepared spike native extensions, isolated DuckDB binding
and cached pytest/Hypothesis tool path. Use NEW output/basetemp paths to preserve evidence:

```sh
# With the prepared binding, C++ runtime and cached pytest/Hypothesis on the process path:
DML_BIN="$PWD/build/spike-native/dml" python -m pytest -q --noconftest \
  spikes/relational_invariants/test_pairing.py --basetemp=build/NEW-paired-cases
```

The DML_BIN basename is only an import-location hint in this slice; its CLI is not invoked.
[paired_summary.py](paired_summary.py) can summarize retained artifacts without reopening a
repository or rerunning any test. Basetemp case stores are owned by this spike, not historical
fixtures. No design checkpoint publication or production integration is requested/performed.
