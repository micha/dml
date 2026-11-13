# Holistic assurance and validation-work review

Continuation after [local checkpoint](../../checkpoints/holistic-test-performance.md).
DML remains CLEAN local15555c0; no executable changes since the checkpoint. This is a
source/evidence review and ONE representative profile, not a new implementation or
five-minute result. Candidate engineering below is assistant-origin pending scope review.

## Assurance ownership map

These layers describe existing evidence obligations, NOT a new pytest mode, exemptions,
removed tests or automatically approved rewrite of every module.

| Obligation | Representative existing owners | Minimal sufficient exercise |
| --- | --- | --- |
| Native storage/transaction identity and errors | `tests/python/test_repository*`, native tests, `test_transfer*` | Real native API/records/transactions; exact typed identity and failure/publication checks |
| Fixed semantics and value/source relations | `test_builtin.py`, `test_builtin_profiles.py`, `test_recorded_maps.py` | Small real native graph; operation recomputation, source relation and cap/poison controls |
| Request/selection/decision profiles | `test_datum_reuse.py`, `test_implementation_selection_edges.py`, record/response guard modules | Real valid pinned history plus an isolated native mutation or explicitly labelled HOST response fault; repeated producer launches usually not the assertion's subject |
| Composition authority and occurrence identity | `test_captured_calls.py`, `test_captured_call_edges.py`, phase/authority/history guards | Real native Q/T/spine/selection links and ALL-parent retention; equal values must not launder wrong producer/occurrence; depth/budget boundary preserved |
| Execution/transport/custody | LOCAL/exchange/process/SSH/Floci stories and owning acceptance records | Actual mechanism when execution/transport/lifetime is the assertion; HOST substitutions/frozen PID receipts cannot replace it |

The large implementation-choice parametrization currently obtains menu/selected through
producer/double (actual setup), although its main obligation is choice/reuse publication.
Further fixture pooling is possible in principle, but the last experiment did not establish
whole-suite benefit. Do not expand test setup machinery blindly or remove integration
assertions merely because another test covers a similar line.

## Concrete repeated validation chain

Read current public/native boundary and example source, not just test names:

1. `examples/captured_calls.py` has successful operation-local proof/read memoization already;
   repeated TOP-LEVEL operations reset it. Its builtin Inspector memo shares only SAME actual
   transaction/commit; each new short transaction still constructs a new retained scan.
2. `python/daggerml/daggerml/builtin.py:Inspector.__init__` traverses the complete typed native
   closure via `_retained`, ALL parents included. Semantic `node/_arguments/trace` recompute
   source/value/binding relations; `seen` bounds semantic union, NOT a completed-proof cache.
3. `transfer.export_commit` independently traverses raw records and descriptions, detects
   active cycles/count/raw+encoded byte limits, serializes base64+JSON. A membership set is
   NOT interchangeable with this stronger transfer framing/cycle/size proof.
4. `reuse_selection._projection` reads stored S/V fields, `_history` walks parent commits
   and exports the basis, exports F separately, materializes temporary files, then runs the
   PUBLIC exchange observation validator. Cleanup/occurrence/response checks remain useful.
5. Public exchange preparation/observation has independent boundary checks. The outer example
   cannot safely mark these public seams "already validated" by passing its own unchecked flag.

There are65 textual `transfer.export_commit`/builtin Inspector use sites across example
modules (read-only search; not65 measured runtime calls). A coherent solution should distinguish
native record availability/typed closure/serialization/semantic proofs/occurrence authority,
not scatter unrelated cache dictionaries or collapse them into one boolean success.

## ONE current representative profile

Question: do redundant closure/export scans remain on current checkpoint sources after memoization?
Target: `test_captured_calls.py::test_actual_logical_calls_direct_sources_shared_content_but_distinct_positions`.
It performs native metadata writes and TWO explicitly HOST-substituted leaf publications; NO
actual OS computational child/custody/installed acceptance claim. No native compilation/full suite/
coverage.py/Valgrind/mutation/CI/native19 probe. Native counters redirected to isolated evidence.

Evidence: `../dml/build/holistic-performance/20261107T191318Z-representative/`.
Initial `nix develop --offline` RAWexit1 BEFORE pytest: unexpected dependency bootstrap builds,
fixed-output source hash mismatch, no profile/XML/native counters/test run. Secondary attempted
pstats read RAWFileNotFoundError; empty profile-summary retained. NOT a failed DML test and no
runtime attribution. No explicit dependency repair/hash bypass/install/flake edit/second Nix
attempt performed. Offline preparation unexpectedly attempted source/bootstrap derivations;
raw logs retained, no claim that it made zero source-acquisition/network attempts.
Tools flake and lock SHA256 equal prior retained final/before bytes.

Read-only discovery found cached serial Python environment
`/nix/store/a1nqcxh6a6976bf6ivjz8x83wvgjjanp-python3-3.13.15-env` with pytest9.0.3 and
Hypothesis6.151.10; xdist/pytest-cov/psutil ABSENT. Direct use suffices for this single serial,
no-Python-coverage target. This is NOT the full parallel tools environment. `cached-serial/`
TRUEexit0, actual XML ONEpass,6.48s pytest/5.25s call/.05s setup. Profiler8,947,952 calls
(8,603,091 primitive),6.609s; timings include instrumentation and nested costs overlap.

| Current profiled work | Calls | Cumulative seconds |
| --- | ---: | ---: |
| builtin `_retained` |132|1.394|
| `transfer.export_commit` |63|1.276|
| selection `_projection` generator entries/resumptions |24|1.249|
| native-wrapper `get_record` |106095|1.508|
| native-wrapper `get_ref` |99281|.624|
| binding `_call` |290903|2.468|

24 projection generator entries/resumptions are NOT necessarily24 independent full selections.
No distinct-root/repository/scan multiplicity measurement yet. Record/get_ref counts include
all consumers, not proof that every call is redundant. Setup negligible in THIS representative
case; cannot generalize its percentages to all3421 tests. Older ancestry profile4164scans/
7.47million reads remains earlier-source evidence, not relabelled current results.

This confirms substantial Python validation orchestration remains even for one simple outer
call. It does NOT establish native storage inefficiency or justify removing authority checks.

## Candidate coherent approach and scope gate

Preferred next candidate over more fixture pooling: a narrow shared Python read-only validation
context, with separately named typed-record/closure/serialization/semantic proof obligations.
Keep it operation-local, exact repository/pinned identity/native owner state; explicitly carry
semantic unions and recheck live object/raw/encoded/semantic/depth budgets. Keep active-cycle
and occurrence-specific checks, uncached refs/failures, separate writer and external packet
boundaries. No durable cache, supplied unchecked retained flag, live-handle escape, arbitrary
transaction/repository caching or purity/equivalence assumption.

A concrete installed-Python `builtin/transfer` internal integration could address costs across
modules without changing C/storage or the low-level Repository API. That is a broader owning
runtime surface than prior example-only memoization: review exact context lifetime, call-site
integration/guards/measurement plan BEFORE edits; no blanket API/native permission inferred.
Alternative confined example orchestration may be feasible, but cannot safely bypass public
selection/exchange validation or claim all132 scans/63 exports disappear.

Deterministic work-count regressions should identify exact unique roots/records/proof scopes,
then show repeated access does not retraverse them; independently test fresh scopes, changed
bounds, mixed repos/commits, active cycles, bad profiles, stale/ended/wrong-thread native state,
mutated HOST responses and exact original versus requested authority. Do not assert arbitrary
machine-specific speed thresholds or change existing200ms deadlines. Preserve original tests.

Full-gate tooling is currently BLOCKED at environment preparation if using current Nix tools;
no permission to repair source hashes/provision new dependencies. Cached serial environment
supports focused investigation only, not parallel full coverage. Before engineering/full-v
validation, choose a scoped reproducible cached full environment or request preparation approval.
No further automatic profile/full/story or implementation change after this bounded review.
Both builds/source/evidence coordinator-owned, old coding workers stopped; GHA disabled/native19
PAUSED/private candidate retained/VP001 OPEN UNKNOWN/owner/conditions unchanged. New design notes
remain uncommitted; initial checkpoint remains intact, no further commit/push requested.
