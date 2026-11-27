# Quint trace interpreter

[`run_histories.py`](run_histories.py) is the shared entry point for the ref,
transfer, staged-import, and garbage-collection suites. Run it through
[`scripts/check.sh --quint`](../README.md#quint-behavior-checks).

## Direct core replay

Each history is an ordered list of `{ op: str, args: List[str] }` requests.
Each request names **one DML core function**, without the `dml_` prefix. The
[shared adapter](replay_core.py) resolves handles, object IDs and buffers, then
calls the matching [Python binding](../python/dml_core.c) once. Ref replay
imports the same [public module](../docs/spec-next/python.md) that ships in the
wheel. The transfer, staged-import, and collection suites use a private build
with extra output-slot instrumentation, even where a public wrapper exists.
Neither layer implicitly begins, commits or aborts transactions during replay,
or judges the core outcome.

For example, `txn_ref_create` with `List("writer", "main", "A")` uses the
transaction aliased as `writer` and the commit ID aliased as `A`. A separate
`txn_commit` request publishes the change. Repositories have distinct paths in
the test workspace. Histories explicitly end their transactions and close their
repositories. For packed data, bundles and IDs, an operand can reference an
output alias or supply fixture bytes in hex. A bundle operand like `exported~1`
uses the saved bytes with one byte removed from the end.

The adapter records returned statuses and values, including observed output
slots where the API promises to leave them unchanged on failure. The independent
[read-only LMDB scanner](lmdb_inventory.c) observes committed state after every
step, including on other initialized repositories. It cannot see uncommitted
changes. Exported bundles are also read with an independent wire parser. Quint
judges these observations against expected records, dependencies, ref values,
and transaction outcomes. Dispatch errors, missing observations or verdicts,
and insufficient history coverage fail the suite.

## Replay refs against the installed wheel

After [installing the binding](../README.md#install-the-python-binding) in a
clean virtual environment and building the opt-in suite, run from outside the
checkout with no `PYTHONPATH`. Set `source` to the absolute checkout path and
`consumer_python` to the virtual environment's Python. Use the scanner
executable for the platform (`lmdb_inventory.exe` on Windows).

```sh
"$consumer_python" -IB "$source/tests/test_python_binding.py"
"$consumer_python" -EB "$source/tests/run_histories.py" "$(command -v quint)" \
  daggerml.core "$source/build/core-check-quint/lmdb_inventory" \
  "$source/tests/ref_histories.qnt" "$source/tests/ref_rules.qnt" \
  --init init --init changedInit
```

The focused binding tests check Python argument rejection, error mapping,
byte-buffer ownership, explicit handle consumption, and thread-affine cleanup.

## Exercised behavior

- **Refs:** create-only refs, successful atomic snapshot publication, explicit
  abort, poisoned rollback, and conditional publication. Quint's histories show
  two callers reading the same tip, one moving it and the stale caller aborting.
  Readback closes and reopens the repository before resolving commits and parents.
- **Transfer:** exact self-contained export, dependency ordering, deterministic
  re-export, independent input ordering, malformed and thin bundles, and
  explicit import, inspection and publication. The histories check datums at
  the selected and parent snapshots. A separate history records and pins a
  result through individual writes, rejects a distinct duplicate pin, returns
  the result, conditionally publishes it, and releases the staging ref with an
  expected target. Integrity reports and exact typed IDs show what the remaining
  refs retain. The [installed example](../examples/transfer_history.c) separately
  demonstrates invoking an actual caller function.
- **Staged import and collection:** import with or without a retention ref, exact
  rollback of distinct staged results on duplicate refs, stale publication,
  and last-root collection. The histories exercise ref edits before and after
  collection, partial and full sweeps, explicit abort and poisoned commit.
- **Native boundary checks:** separate focused tests exercise raw LMDB corruption,
  map exhaustion, bundle limits and dirty export buffers, and inject allocation
  and deletion failures. These aren't replay requests and do not emulate core
  operations in the adapter.

## Add a history or operation

Compose existing requests in a `*_histories.qnt` module. Add a thin Python
binding and an argument/result mapping to the shared adapter only when exposing
a new **core function**. Do not add an adapter or a native replay executable for
a new suite. Keep application workflows (such as publication) as separate
requests within Quint histories.

Each `*_rules.qnt` exports `Observation`, `historyVerdicts(observed)`,
`verdictAccepted(verdict)`, `coveragePass(evidence, verdicts)`, and `controlsPass`.
Check exact changes rather than counts where practical, require the histories
that exercise rejection, and retain synthetic controls that reject fabricated
success. Meson can pass local rule imports with `--quint-module`. Encode
arbitrary bytes as lowercase hex in evidence.

## Process integration

### Provenance handoff

Start with [the Quint handoff histories](handoff_histories.qnt) for the expected
workflow and [the evidence rules](handoff_rules.qnt) for how a run is judged.
The histories cover request selection, transfer and restart, no-clobber export,
publication guards and their precedence, and retention through cleanup and
collection. Inspection must report the expected checkpoint and request, and
leave the LMDB data file unchanged even when it rejects a staged result. A
fixture result with a matching lineage but a deliberately wrong scalar shows
that these checks do not recompute the output.

The [process runner](run_provenance_handoff.py) executes the requested steps and
records exit codes, report lines, diagnostics, and filesystem observations. The
[C fixture](handoff_fixture.c) uses public APIs to seed and observe committed
refs and lineage independently of the report. Only bundle paths pass between
handoff roles. Quint—not the runner—checks the observations and requires the
inspection scenarios to be exercised. This is a separate workflow suite; the
core replay above still dispatches one public API call per step.

`provenance-handoff` runs in the opt-in Meson suite. To verify the installed
boundary, [install the C library](../README.md#install-and-link-the-c-library)
and run the same test using only the installed headers and archive. Use the
Python and Quint from the [opt-in environment](../README.md#quint-behavior-checks).
For example, with a Unix compiler driver:

```sh
run_dir=$(mktemp -d "$PWD/build/handoff-test.XXXXXX")
cc -std=c11 -Ibuild/install/include examples/provenance_handoff.c \
  build/install/lib/libdml.a -pthread -o "$run_dir/provenance_handoff"
cc -std=c11 -Ibuild/install/include tests/handoff_fixture.c \
  build/install/lib/libdml.a -pthread -o "$run_dir/handoff_fixture"
python3 -B tests/run_provenance_handoff.py "$(command -v quint)" \
  "$run_dir/provenance_handoff" "$run_dir/handoff_fixture" \
  tests/handoff_histories.qnt tests/handoff_rules.qnt
```

### Recorded calls

The [Python example](../README.md#record-two-composed-calls-in-python) uses the
public binding. The [workflow runner](run_recorded_calls.py) launches separate
CLI processes and observes their reports, diagnostics, repository presence, and
changes to `data.mdb`. The [Quint histories](recorded_calls_histories.qnt) also
request individual native reads and fixture writes on the same repositories.
The [rules](recorded_calls_rules.qnt) compare CLI reports to independent native
reads of commit parents, tree entries, and producer DAG edges.

For split recording, the runner passes an explicit immutable ID, never the
current pin target. CLI steps can name a prior receipt or use `native:<alias>`
for a native ID. Native ID operands can use `sum:<ref>`, `scale:<role>:<ref>`,
or `plan:<alias>` for prior CLI receipts. Quint checks that two equal-valued
sums remain distinct producers and that read-only reports stay the same after their
pins move or are deleted. For failed writes, Quint distinguishes stale and
missing pins, occupied refs, overflow, and out-of-range input. It checks file
preservation where applicable and uses native reads to verify that candidate
values and refs were not left behind.

The [stored-evidence histories](recorded_calls_stored_histories.qnt) build a
producer that stores `-17` for `2 + 3`. Inspection preserves that result and a
stored scale result of `-98`; fresh execution with factor 6 instead computes
`-102`. The histories also exercise an unsupported implementation, a result
whose input DAG does not match its equal-root parent, and a literal input used
in place of a sub-DAG edge. The workflow and remaining
[focused tests](test_recorded_calls.py) run in the opt-in Meson gate.

The [one-way bundle handoff](../README.md#compose-from-a-producer-in-another-repository)
exercises the same caller on a second repository through the public binding.
The [outbound histories](recorded_calls_outbound_histories.qnt) check no-clobber
export, create-only staging, and release guarded by the exact parent and input
DAG. They check that both links survive collection while an unpinned decoy is
swept, and that transferring the stored sum does not change the value consumed.
A separate history truncates a copy of a bundle by one byte, checks that it
publishes neither the staging ref nor any object from its closure, and then
imports the intact bundle. The runner only performs the requested file edits
and reports observations; Quint checks the outcomes.

The opt-in Meson gate runs [durable plans](recorded_calls_plan_histories.qnt)
and [receipt histories](recorded_calls_receipt_histories.qnt) under a separate
`recorded-calls-durable` entry, using the same replay runner.

The [return and publication history](../README.md#return-and-publish-a-recorded-scale)
checks exact result export and staging, rejection of a same-valued wrong producer,
and conditional publication to either an absent or an existing `main`. Two scales
of a zero sum share an output node but record different factors. Even when the
exact result is staged and `main` matches, publication rejects the wrong factor
and accepts the same result with the matching expectation. Any rejection must
leave committed bytes unchanged. Success releases the staging ref and leaves both
calls readable after a sweep. The stored-result return history checks that
publication preserves the worker's `-98` and exact report, and that both physical
links survive collection without a source producer pin. The late-guard history
checks that moved and missing staging pins roll back `main` changes and that a
staging alias of `main` is rejected.

The [durable-request history](../README.md#save-a-scale-request-before-sending-it)
starts separate processes for planning, dispatch, work, staging, and publication.
It checks two requests with the same zero-valued sum and different factors, and
rejects a wrong request, stale plan, stale staging selection, and stale `main`
without changing committed bytes. `recorded-calls-durable` verifies that the
captured tip is not exported when unrelated to the request and resumes
publication without the bundles or producer pin. It rejects a future
implementation at work time, and a forged factor or input edge under the
right request parent. Native reads check exact lineage after collection.

The [publication retry history](../README.md#retry-publication-if-its-acknowledgment-was-lost)
checks first publication, a matching retry, rejection under a missing or occupied
key, and a retry after a second publication and collection. The retry must return
the first result ID without changing committed bytes or the newer tip.
`recorded-calls-durable` reads the native receipt DAG, checks each key field
independently, and verifies rollback of tentative receipts. It retries with
all original guards satisfied, then after ref reuse and actual reclamation
of the old commits.

The [abandonment history](../README.md#abandon-a-scale-request-without-publishing)
checks that a late staged result cannot publish after abandonment, no receipt or
`main` appears, and a stale ID cannot delete a replacement plan under the same
name. Removing the replacement leaves the exact staged result intact. The
publication retry history covers the opposite order: a consumed plan cannot be
abandoned, and the publication receipt still acknowledges success.
`recorded-calls-durable` checks abandonment with a moved `main`, invalid and
non-plan selections, exact ref preservation, and explicit collection.

The [reuse history](../README.md#reuse-an-explicitly-selected-local-scale-result)
retains one worker result locally and publishes that same commit through two
exact plans without dispatching more work. Replay rejects stale selections,
a wrong request for a zero-valued sum, and an occupied staging ref even at the
same ID. It also checks that a moved `main` blocks publication but not staging,
that abandonment blocks both commands, and that the original result and
receipt survive unchanged.

The [recorded reuse publication history](../README.md#publish-reuse-with-a-durable-record)
publishes the same result ID first from a freshly staged bundle, then by explicit
reuse. Only the reuse path leaves an inspectable record. Replay also checks
that stale `main` and abandoned plans cannot leave a record, that the result pin
survives, and that `main` still reports the original graph. The separate
[`recorded-calls-reuse` entry](recorded_calls_reuse_histories.qnt) stages and
publishes a stored result whose execution would overflow. It checks the exact
`main` move and stored proof graph, sweeps an unpinned alternate, and verifies
rollback even when the occupied ref holds the proof the caller would create.

The [version selection history](../README.md#select-a-scale-implementation-version)
checks that the default and explicit `@1` plans have the same ID, then runs `@1`
and `@2` through separate worker commands. The recorded calls share arguments
and an output node, not request, call, or result IDs. Replay checks rejection
without writes for an unsupported version and for cross-version publication
and reuse, then publishes and reuses the matching `@2` result. The durable
entry rejects execution of an imported future request. The reuse entry
exercises the exact request parent with a wrong implementation in the body.

The [durable selection history](../README.md#save-a-result-selection-before-publication)
checks that selection works with stale `main`, and that publication through a
new plan still uses the original result after its pin disappears and collection
runs. It distinguishes two selection IDs for the same request and result,
rejects cross-version reuse and occupied outputs without writes, and inspects
both the selection and the completed reuse record. The
[`recorded-calls-selection` entry](recorded_calls_selection_histories.qnt)
transfers a choice without its private plan or prior tip, publishes without
the old result pin, and checks which exact commits the proof keeps after
collection. It also runs select, inspect, and publish against malformed
persisted records with a valid counterpart.

The [execution attempt history](../README.md#distinguish-two-executions-of-the-same-request)
executes the same saved `@2` request twice in separate worker processes and
transfers the two distinct attempt commits. Both retain the same result ID
printed by `work-scale`. The runner uses exact native ref deletions as fixture
steps to simulate another writer. Quint checks rejection without writes after
the attempt or selection pin is replaced by a same-result occurrence and checks
publication from the surviving choice after collection. The selection entry
checks that reusing the same UUID produces the same attempt, reads the ordered
native parents and literal fields, distinguishes malformed nested records and
UUIDs, and checks reachability with the proof as the sole root. The focused
Python boundary tests keep values the CLI cannot pass directly.

The [versioned attempt selection history](../README.md#record-a-new-version-of-an-attempt-selection)
executes new attempts after the initial choice, adopts independently on two
branches, and explicitly reselects the original attempt on a descendant.
Replay checks exact version matching even when two versions select the same
attempt, rejects an occupied ref without writes, and reads reuse records for
the different choices after the attempt pins are removed and collection runs.
The separate [`recorded-calls-adoption` entry](recorded_calls_adoption_histories.qnt)
checks adoption after abandoning the plan, native parent order, and retention
through the adopted version after collection. It runs adopt, inspect, and
publish against malformed stored chains and inspects a valid chain of 1,025
alternating adoption links.

The [intent policy history](../README.md#set-a-reuse-default-for-the-scale-intent)
checks both defaults and overrides using the real CLI. It distinguishes a
missing selection from a moved selection, checks that fresh routes ignore a
moved slot, and verifies that reuse reports the original attempt and leaves no
live plan. Replay checks atomic rejection and decision readback after
collection. The separate [`recorded-calls-policy` entry](recorded_calls_policy_histories.qnt)
reads the captured prior `main` and ordered policy decision parents natively,
checks distinct decision IDs for equal intent, and exercises malformed
persisted policies and decisions.

The [implementation default history](../README.md#choose-an-implementation-from-a-pinned-intent-definition)
checks that pinned versions choose independently, an explicit implementation
can still reuse, and an exact but incompatible selection cannot satisfy a
request. It exercises atomic rejection and offline decision inspection. The
separate [`recorded-calls-intent` entry](recorded_calls_intent_histories.qnt)
checks definition ancestry and malformed stored decisions, and distinguishes
fresh routes that omit selection fields from explicit reuse that publishes the
selected attempt's exact result.

The [supersession history](../README.md#record-advisory-implementation-supersession)
checks that declaring and promoting are separate, that the predecessor can
still reuse its exact selection, and that a supplied knowledge version does
not change the historical decision. The separate
[`recorded-calls-supersession` entry](recorded_calls_supersession_histories.qnt)
checks exact pins, rollback on occupied output, and historical and supplied
views after transferring decisions and sibling knowledge to a replica without
origin refs. The [`recorded-calls-supersession-invalid` entry](recorded_calls_supersession_invalid_histories.qnt)
checks malformed stored declarations both directly and as knowledge, and
rejects invalid knowledge operands without writes. The Python boundary suite
retains the short raw knowledge-ID check.

The [multi-input history](../README.md#keep-reusable-results-for-multiple-scale-requests)
checks that exact request keys coexist and one-key adoption preserves the other
entry and the old branch. It covers routing, rollback, and pinned inspection
after collection and after transfer to a replica without input refs. The
[`recorded-calls-table-capacity` entry](recorded_calls_table_capacity_histories.qnt)
checks a full table, a one-row adoption, and rejection of result-only and
cross-version selections. It builds oversized and mismatched table deltas with
native writes, then checks reader rejection and explicit fresh bypass. The
[`recorded-calls-table-scope` entry](recorded_calls_table_scope_histories.qnt)
distinguishes intent ancestry from equal fields, tests when a table is
consulted, and checks a forged decision whose historical table lacks the key.

The [intent-scoped history](../README.md#share-selected-scale-results-across-implementations-of-one-intent)
checks requested and producing identities independently, exact producer and
signed-factor matching, cross-version adoption, and one-key removal. Replay
checks historical inspection on a replica without the original refs. Focused
checks exercise the live-key cap after removal, same-attempt and result-only
rejections, rollback on occupied output, and malformed deltas that cannot be
hidden by later removal.

The [recorded argument maps example](../docs/recorded-argument-maps.md) uses a
[separate Quint history](argument_maps_histories.qnt). The same typed map from
literal `42` and returned `42` reuses the original `double@1` result for a new
`double@2` request. Changed keys, types, values, and stale pins are tested
separately. The runner collects CLI reports and an independent LMDB inventory;
Quint checks request, result, attempt, and getter counts, exact ref effects,
and both constructions on a replica containing only the transferred hit ref.
A late decision-ref collision must report the exact `ref already exists`
diagnostic without changing the full native inventory. The fresh request leaves no pending
ref; the selected hit leaves `main` absent. Retrying each with the same
invocation ID and a free decision ref publishes the pending request or the reused result.
The same history then adopts a `double@2` attempt for the `42` map. Its getter
reads the returned `42`, not the literal read by `double@1`. Quint checks both
rows before and after adoption. An attempt to re-adopt the current selection
must fail without changing the native inventory. Removing `42` leaves a pending miss on that key; `43`
still routes to its original producer. After both edits and `main` updates,
inspecting the old hit must reproduce its complete pre-edit report.

Pending requests then exercise `work` failures. `double@1` rejects a missing
or STRING `x`, or a result outside the signed I64 range. `add@1` reads a valid
`a` before encountering a missing or STRING `b`. Quint checks each diagnostic
and the unchanged full native inventory: the pending request, its decision, and
`main` retain their targets, with no partial attempt, result, or getter record.

Three `add@1` requests separate key spelling from insertion order. `a=13, é=29`
produces the same MAP ID with composed or decomposed `é`, in either tested order.
Changing only the spelling preserves the construction ID; reversing the inserts
changes it. The history spells UTF-8 key bytes in hex, and the runner decodes them
only for the CLI arguments. Supplying both spellings together, with equal or
conflicting values, must report `request: duplicate canonical argument key` and
leave the full native inventory unchanged. The conflicting request starts with a
new singleton map so a partially committed first insert would be visible.

A returned argument pins an attempt, not its value or result commit. Two `add@1`
requests (`13 + 29` and `12 + 30`) return `42`; executing the first request twice
also yields two attempts with the same result commit. Neither alternative attempt
can pin the original ref. Both stale pins must report the exact mismatch and roll
back the preceding literal insert without changing the full native inventory.
Changing only the pin to the original attempt lets the request succeed. Quint checks
that the inspected `x` argument and the subsequent `double@1` getter name that attempt.

At the request-size boundary, a fresh `add@1` decision retains all sixteen named
literal arguments and points to the published pending request. Adding a new
seventeenth argument must report `request: expected up to sixteen named arguments`
without a receipt, new refs, or any change to the full native inventory. The extra
argument is first in the CLI list so even a partial insert would be visible.

The live-table boundary uses seventeen distinct MAP keys backed by returned
attempts. Quint checks all sixteen key-to-attempt pairs in the full table.
Inserting the seventeenth key must report
`update-table: insert requires an absent key and room in the table` without a
receipt, new refs, or any change to the full native inventory. After removing
one row, the same insert and output ref succeed against the reduced version.
Quint checks the exact mappings in both new versions and confirms the earlier
full version remains unchanged.

The [budget replay](argument_map_budget_histories.qnt) uses the same CLI
runner in a separate suite. It reaches 63 distinct attempts through four
disjoint groups of pinned returns. An `add@1` request pins all four group attempts and uses the
first one twice, so work adds exactly one more reached attempt. Quint checks
the pending source pins and the resulting getter links. A new request cannot
use that 64-attempt result as a source. Replacing the repeated pin with a
sibling that shares its request and result also reaches 64 distinct attempts
and leaves no slot for new work. Both requests must report
`request: too many reached argument-map attempts for a new invocation`, with
no receipt, new refs, or changes to the full native inventory. Each starts with
an unused new literal so a partial insert would be visible.

The [poisoned-table replay](argument_map_poison_histories.qnt) first confirms
that `42` is a hit against a clean table. A test-only native fixture then
inserts the distinct `43` MAP key with the attempt for `42`, and records a
later removal of the `43` key. Quint checks the recorded edits and their
parents. Lookup of `42` against either version must report
`request: selected attempt does not match the table intent and argument MAP`,
with no receipt or change to the full logical LMDB inventory. `fresh` ignores
both an exact and a stale pin to the poisoned history: each decision publishes
a pending request without a table parent or a change to `main`.

The [request integrity replay](argument_map_request_integrity_histories.qnt)
inspects two valid requests for `x=42` and `x=43`. A test-only native fixture
copies the first request, replacing only its root with the second request's
well-formed MAP. Quint checks both MAPs and the preserved construction,
bindings, and parents. CLI inspection must report
`inspect: request argument MAP differs from its construction`, with no
standard output and no changes to the full logical LMDB inventory. The
original request still returns the same inspection report.

The [returned-source replay](argument_map_returned_source_histories.qnt)
records two `add@1` attempts with distinct result DAGs that both return I64
`42`. A test-only native fixture copies a request pinned to the first attempt,
replacing only the construction's source link with the second result DAG.
Quint checks that the stored attempt parent, origin and MAP stay the same. CLI
inspection must report `inspect: returned source does not match the selected attempt result`,
with no standard output and no changes to the full logical LMDB inventory.
The original request still returns the same inspection report.

The [focused tests](test_argument_maps.py) exercise a 64-deep returned-source
chain and reject a getter link from a different construction.

The [versioned built-ins replay](builtins_histories.qnt) runs the
[installed-module workflow](../docs/internal-builtins.md): a pinned v1 request
still works after promotion, v1 and v2 return the same value from the same
argument node with different operation IDs, equal MAPs reuse only the original
ordinary result, and a changed MAP runs a new attempt. Quint checks native
commit counts, full-inventory rollback on late ref collisions, and distinct
requested and producing edges. A read-only CLI verifies the transferred hit
closure and rejects two equal-value trace grafts. [Focused runtime tests](test_builtins.py)
check handler routing, type and lifetime boundaries, and poisoned-scope rollback.
The [finite design model](recorded_builtins_design.qnt) checks routing and exact
source/trace association separately from native encoding and arithmetic:

```sh
mkdir -p build/recorded-builtins-tlc
(cd build/recorded-builtins-tlc && quint verify ../../tests/recorded_builtins_design.qnt \
  --backend=tlc --search-observations)
```

Use Java and Quint 0.34.0 or newer for this standalone design check. Confirm
that all observations were reached; a checker exit alone is not coverage.

The [composed node calls replay](composition_histories.qnt) validates a
[recorded add-to-double workflow](../docs/composed-node-calls.md) with eight
requests and six published attempts. It checks that repeated and swapped adds
converge on the same downstream MAP value, that reused work retains its original
producer and trace, and that changed inputs cause fresh work. Work with an occupied attempt ref
reports the exact collision and leaves the full native inventory unchanged,
both before `main` exists and after it points to a previous result. Each retry
uses the same request and attempt ID at a free ref, publishes the result and
both getter calls, and creates or updates `main`. The replay also checks
read-only inspection of a transferred hit and rejects inconsistent producer
pins and input source edges. On the original composition, `request-double`
rejects reuse with the invocation ID that would recreate the producing request.
Separately, `inspect` rejects a copy of a valid transferred hit whose first
parent was replaced with the selected attempt's producing request. Both commands
must report the identity error and leave the full native inventory unchanged.
A separate history checks I64 overflow in add
(`MAX_I64 + 1`) and double (`MAX_I64 * 2`). Each work command must fail with
`work: int too big to convert` and leave the full native inventory unchanged.
The rejected add leaves `main` absent. The rejected double leaves `main` at the
successful `MAX_I64 + 0` add result and leaves the double decision pending.
A [focused Python test](test_composition.py) checks an equal-value getter-key graft.

The [finite composition model](recorded_composition_design.qnt) covers producer
pins, atomic decisions, rollback, and requested versus producing history. It
models IDs and fixture values, not the native encoder or Python arithmetic.
Run it with Java and Quint 0.34.0 or newer; confirm all 18 observations are reached:

```sh
mkdir -p build/recorded-composition-tlc
(cd build/recorded-composition-tlc && quint verify ../../tests/recorded_composition_design.qnt \
  --backend=tlc --search-observations)
```

The [closure-bound dependency replay](closure_histories.qnt) checks eight
requests and four successful fresh attempts in the [scaled-sum example](../docs/closure-bound-dependencies.md).
It distinguishes captured source and getter version from the full-MAP reuse
key, validates a selected attempt even on a miss, and inspects transferred
history while rejecting capture and original-history grafts. Replay rejects a
reuse request with the producer's invocation ID, work with an occupied attempt
ref, and separate I64 subtotal and product overflows. Each rejection leaves
native storage unchanged. After the collision, replay retries with the same
attempt ID at a free ref and checks the result and getter trace. For overflow,
replay checks the exact stored operands and the distinct CLI diagnostics.
[Focused tests](test_closures.py) check exact I64 and argument boundaries,
inspection without binding work, and rejection of a semantically equivalent but
unpinned getter in the producing trace.

The [finite closure design model](recorded_closures_design.qnt) checks three
captures, two equal-sum MAPs, one historical attempt, and at most one new
request and execution per path. It treats arithmetic values and IDs as
fixtures and does not model the native encoder or process lifecycle. Run it
with Java and Quint 0.34.0 or newer; confirm all 22 observations are reached:

```sh
mkdir -p build/recorded-closures-tlc
(cd build/recorded-closures-tlc && quint verify ../../tests/recorded_closures_design.qnt \
  --backend=tlc --search-observations)
```

The [captured ordinary call replay](ordinary_histories.qnt) exercises the real
[synchronous example](../docs/captured-ordinary-calls.md): captured targets
survive changing defaults; an outer hit skips both children; an inner hit
keeps the new request's add source and the old producer's original add source.
It also checks retained prefixes after failure and read-only transferred
inspection. A separate pinning history moves the double selection with a native
write transaction after add commits and before double starts. Quint checks that
the live call still uses the original producing attempt. The execution history
records in-process adapter entries and object identities. Quint checks one
outer call, add on the original arguments node, and double on the exact MAP
made from add's returned node. An outer hit executes no adapters. On an inner
hit, add runs once and the outer callable invokes double's slot with the new
MAP, but the double adapter does not run. Inspection of either hit executes no
adapters and leaves storage unchanged. If the required double selection is
pinned to an absent ref, the call stops at the double slot without running the
double adapter, retains add's result, and leaves `main` unchanged. An
overflowing add never reaches double, keeps only the start phase, and leaves
`main` on the earlier successful call. Replay checks these live observations
alongside native records and inspection. A separate history rejects an outer
reuse request that repeats the producer's invocation UUID: storage stays
unchanged, the output ref stays absent, and `main` stays on a later call.
Retrying at the same output ref with a different UUID succeeds, moves `main`
back to the selected producer, and reports distinct requested and producing
provenance. The ref-alias history rejects an output that shares the capture
ref, `main`, or an absent double-selection ref. Each rejection leaves native
storage unchanged. Retrying at the same output with a distinct absent selection
records fresh add and double attempts and publishes a new result.
[Focused tests](test_ordinary_calls.py) cover exact I64 inputs and adapter
failures, and inject late update failures after real native writes.

The [finite ordinary call model](recorded_ordinary_design.qnt) bounds each
path to one new outer request, two call slots, two capture versions, four MAP
values, and one historical success. It checks pinning, ordered publication,
rollback to the last committed phase, and requested versus producing history.
It uses symbolic IDs and an overflow sentinel; it does not model encoding,
Python handles, or processes. Run with Java and Quint 0.34.0 or newer and
confirm all 15 observations are reached:

```sh
mkdir -p build/recorded-ordinary-tlc
(cd build/recorded-ordinary-tlc && quint verify ../../tests/recorded_ordinary_design.qnt \
  --backend=tlc --search-observations)
```

The [implementation-bound replay](implementation_bound_histories.qnt) opts in
through the same CLI. Quint checks exact A and B closure links and getter
versions, B reusing A despite new input sources, B running fresh, B requesting
double but reusing A's double, and A still running after promotion. It verifies
actual entries into the common facade and adapters, exact pin and MAP-miss
rejections, rejection of a grafted equal-value source, and identical read-only
inspection of the transferred hit without its source repository.
[Focused ownership tests](test_calls.py) check the installed facade's scope,
thread, and native argument binding boundaries.

The [finite routing model](recorded_implementation_bound_design.qnt) covers two
implementation versions, three MAP values, two source ledgers, one retained A
success, and one new call with two leaf positions. It assumes atomic batches
and validated native histories, and does not model native encoding or resource
limits. Run with Java and Quint 0.34.0 or newer and confirm all nine observations
are reached:

```sh
mkdir -p build/implementation-bound-tlc
(cd build/implementation-bound-tlc && quint verify ../../tests/recorded_implementation_bound_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the split-call design with TLC

The [design model](committed_calls_design.qnt) has two same-valued producer
commits with distinct DAGs, two movable producer pins, one disjoint create-only
result ref, and two classes of factor (valid or overflowing). It models each
workflow write as one transaction and allows other writers to change pins only
between transactions. It checks safety, not liveness, and abstracts away
native writes, malformed records, garbage collection, and ref-name aliases.
The replay and focused tests check those parts of actual behavior relevant to
this example, including the case where a result ref aliases a producer pin.

Run this design check separately from CI, with Java and a Quint CLI supporting
TLC observation search (for example, Quint 0.34.0):

```sh
mkdir -p build/committed-calls-tlc
(cd build/committed-calls-tlc && quint verify ../../tests/committed_calls_design.qnt \
  --backend=tlc --invariants pinsRetainProducers retainedAndConsistent scaleRefAndObjects \
  --search-observations)
```

Both producer selections, stale and missing pin rejection, overflow, duplicate
publication, and readback after pin release must be reachable. TLC checks this
finite design; [runtime replay](../docs/validation-policy.md#design-with-tlc-validate-implementation-with-replay)
checks the implementation on selected histories.

#### Check the one-way handoff design with TLC

The [handoff model](recorded_handoff_design.qnt) has one planned sum and one
same-valued decoy with distinct IDs, a fixed factor, distinct worker refs, and
abstract immutable closures. Source pin movement or collection can interleave
between pin selection and export; worker writes each use one transaction.
The model checks safety, not liveness. It abstracts away wire parsing,
filesystem errors and native corruption.

```sh
mkdir -p build/recorded-handoff-tlc
(cd build/recorded-handoff-tlc && quint verify ../../tests/recorded_handoff_design.qnt \
  --backend=tlc --invariants exactExport atomicStage exactScale guardedRelease retainedAndInspectable \
  --search-observations)
```

The observations include a decoy staging successfully but failing selection,
release rejecting a moved pin or mismatched result, and readback after the
producer pin is released and collection removes the decoy. The design check
runs separately from CI.

#### Check the return and publication design with TLC

The [return model](recorded_return_design.qnt) starts with immutable worker
fixtures: two scales of the selected producer with different factors, and three
results with incorrect parent, input DAG, or application shape. Each publication
chooses a request factor independently of the selected result. Worker pin changes
and collection can interleave between selection and export. Source writes are
serialized. The model checks main's conditional create or update and the expected
staging deletion as a single transaction, including modeled aborts after each
tentative write. It checks safety, not liveness, and abstracts away malformed
bundle bytes, filesystem errors, and native corruption.

```sh
mkdir -p build/recorded-return-tlc
(cd build/recorded-return-tlc && quint verify ../../tests/recorded_return_design.qnt \
  --backend=tlc --invariants exactExport stageOnly atomicPublish retainedAndReadable \
  --search-observations)
```

Observations include export despite pin movement, rejection after intervening
collection, isolated wrong-factor rejection with absent and existing `main`,
rollback after either tentative write, and readback through `main` alone after
collection. Run this design check separately from CI.

#### Check the durable-request design with TLC

The [request model](recorded_request_design.qnt) follows one selected plan from
creation through dispatch, worker execution, staging, and publication. It
covers absent or unrelated existing `main`, two same-valued sums, two factors,
and well-formed but mismatched results. Immutable closures abstract away the
record and bundle bytes. Each repository write is one transaction; concurrent
writers can move refs between commands. The model checks safety, not liveness,
and does not model storage corruption or recreating a consumed plan.

```sh
mkdir -p build/recorded-request-tlc
(cd build/recorded-request-tlc && quint verify ../../tests/recorded_request_design.qnt \
  --backend=tlc --search-observations)
```

Observations include restart after staging, equal-output substitution, a forged
factor under the correct request, rollback after each tentative ref write, and
readback after collection. Run this design check separately from CI.

#### Check the publication retry design with TLC

The [retry model](recorded_publication_retry_design.qnt) starts after staging.
It has one retained receipt key, two pairs of pin names, two exact plans with
different `main` expectations, and both matching and mismatching results.
Another writer may move `main` and recreate pins at the same or different IDs.
The model uses abstract immutable closures and treats first publication as one
transaction, independent of whether the caller observes the acknowledgment.
It checks safety only and does not model rewriting a retained receipt or
corrupting storage.

```sh
mkdir -p build/recorded-publication-retry-tlc
(cd build/recorded-publication-retry-tlc && quint verify ../../tests/recorded_publication_retry_design.qnt \
  --backend=tlc --search-observations)
```

Observations include a retry despite a moved `main` and collected objects, a
no-op retry with every original guard satisfied again, conflicts under the
same key, rejection when only `main` matches, and rollback without a receipt.
Run this design check separately from CI.

#### Check the request abandonment design with TLC

The [abandonment model](recorded_request_abandon_design.qnt) has one original
plan capturing an existing tip, an exact result that may arrive late, one
optional publication receipt, and a reused pin with a different target ID.
Other writers can move `main` between transactions. It checks safety, not
liveness, and abstracts away immutable closures, storage errors, byte-level
validation, and recreating the same name at the same ID.

```sh
mkdir -p build/recorded-request-abandon-tlc
(cd build/recorded-request-abandon-tlc && quint verify ../../tests/recorded_request_abandon_design.qnt \
  --backend=tlc --invariants exactAbandonment onlyPlanRemoved noWritesOnRejectionOrRetry \
  exclusiveConsumption publicationUnaffected --search-observations)
```

Observations include both transaction orders, a late stage, a moved tip, a
matching non-plan ref, `main` pointing to a valid plan, and stale rejection
against a reused pin. Run this design check separately from CI.

#### Check the explicit reuse design with TLC

The [reuse model](recorded_result_reuse_design.qnt) has two valid plans for one
portable request capturing different tips, two eligible result IDs, malformed
selections, and a vacant or occupied destination. It models ref changes only
between transactions and checks that reuse writes only the new destination,
while publication still checks the plan and captured tip. A receipt is passive
state. The model checks safety, not liveness, and abstracts away record bytes,
ref spellings, native failures, and receipt retry.

```sh
mkdir -p build/recorded-result-reuse-tlc
(cd build/recorded-result-reuse-tlc && quint verify ../../tests/recorded_result_reuse_design.qnt \
  --backend=tlc --search-observations)
```

Observations include a moved `main`, rejection after abandonment, publication
after removal of the original result pin, and separately malformed or stale
selections. Run this design check separately from CI.

#### Check the recorded reuse publication design with TLC

The [reuse publication model](recorded_reuse_publication_design.qnt) has one
slot for each ref role, three valid plans for the same request with distinct
`main` expectations, two eligible results, and separate malformed or mismatched
selections. Other writers may move or restore pins between transactions. The
model checks safety: atomic publication or rollback, competition for the plan
with abandonment and ordinary staged publication, and retention through both
ordered record parents. It abstracts record encoding and native errors, models
collection as a final readback, and does not model manually replacing the reuse
ref or retrying a publication receipt.

```sh
mkdir -p build/recorded-reuse-publication-tlc
(cd build/recorded-reuse-publication-tlc && quint verify ../../tests/recorded_reuse_publication_design.qnt \
  --backend=tlc --search-observations)
```

Observations include reuse without a change to the `main` target, rollback after
each tentative write, rejection under an occupied ref at the exact record ID,
and readback with the reuse ref as the sole root. Run this separately from CI.

#### Check the version selection design with TLC

The [version selection model](recorded_version_selection_design.qnt) bounds
planning and work to two supported versions and one unsupported version, with
one ref per role. It checks that dispatch uses the saved version and that each
publication or reuse path requires both the exact request ID and its recorded
implementation. The model also covers stale selections, abandonment, and retry
of a retained receipt. It abstracts bundles, GC, native faults, and ref aliases,
and checks safety, not liveness.

Run separately from CI with Java and Quint 0.34.0 or a compatible release:

```sh
mkdir -p build/recorded-version-selection-tlc
(cd build/recorded-version-selection-tlc && quint verify ../../tests/recorded_version_selection_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the durable result selection design with TLC

The [durable selection model](recorded_durable_selection_design.qnt) has one
name per ref role, two supported versions, and valid and malformed selection
records. Other writers can move refs between transactions. The model checks
exact pin and request matching, separation of selection from publication,
and atomic publication or rejection. It fixes the historical result-ref name
and abstracts record encoding, transfer, GC, and native failures. It checks
safety, not liveness. The command first checks the invariants exhaustively,
then searches for witnesses to the declared observations.

```sh
mkdir -p build/recorded-durable-selection-tlc
(cd build/recorded-durable-selection-tlc && quint verify ../../tests/recorded_durable_selection_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the execution attempt design with TLC

The [attempt model](recorded_attempt_design.qnt) uses two supported versions,
two canonical UUID symbols, two worker outputs, and one origin ref per role
plus a second staged attempt. It checks that distinct occurrences can keep the
same result ID, that exact pins and nested request/implementation checks govern
selection and publication, and that occupied outputs or stale guards preserve
committed state. The model searches for publication after collection of the
unselected attempt as well as readback with only the choice or reuse ref. It
abstracts packed records and bundles, UUID syntax, arithmetic, and native
failures. This is a safety check, not liveness or proof of execution.

```sh
mkdir -p build/recorded-attempt-tlc
(cd build/recorded-attempt-tlc && quint verify ../../tests/recorded_attempt_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the versioned attempt selection design with TLC

The [adoption model](recorded_adoption_design.qnt) bounds the workflow to three
eligible attempts with the same result, a single selection history with two
output refs, and one exact-request plan at a time. It checks adoption and
publication guards, immutable forks, retention through collection, and no
implicit adoption on fresh work. It abstracts ref-name syntax, packed data,
transfer and native faults. This checks safety, not liveness.

With Java and Quint 0.34.0 (the 0.33.1 replay shell lacks observation search):

```sh
mkdir -p build/recorded-adoption-tlc
(cd build/recorded-adoption-tlc && quint verify ../../tests/recorded_adoption_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the intent policy decision design with TLC

The [policy model](recorded_policy_design.qnt) explores one portable request,
two eligible selection versions sharing an attempt, several unusable slot
states, and at most two decisions. It checks the route table, exact version
matching, rollback, and immutable decision history across policy changes. It
abstracts native framing, UUID generation, dispatch, and collection.

With Java and Quint 0.34.0:

```sh
mkdir -p build/recorded-policy-tlc
(cd build/recorded-policy-tlc && quint verify ../../tests/recorded_policy_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the implementation default design with TLC

The [implementation default model](recorded_implementation_default_design.qnt)
uses two implementations for a fixed producer and factor, two selection
slots, three valid definitions, and at most two sequential decisions. It
checks that a new definition leaves the old one usable, that implementation
choice precedes the reuse decision, and that rejection preserves repository
state. Ref names, native framing, ID generation, and worker execution are
outside this safety model.

With Java and Quint 0.34.0:

```sh
mkdir -p build/recorded-implementation-tlc
(cd build/recorded-implementation-tlc && quint verify ../../tests/recorded_implementation_default_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the advisory supersession design with TLC

The [supersession model](recorded_supersession_design.qnt) checks the separation
between declaring supersession, promoting a default, and deciding reuse. It
also checks that a separately supplied knowledge snapshot does not change what
was available at the request's pinned intent version. See the
[CLI example](../README.md#record-advisory-implementation-supersession) for
the on-disk convention. The model abstracts native framing, hashing, evidence
contents, and worker execution.

With Java and Quint 0.34.0:

```sh
mkdir -p build/recorded-supersession-tlc
(cd build/recorded-supersession-tlc && quint verify ../../tests/recorded_supersession_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the multi-input reuse design with TLC

The [multi-input model](recorded_multi_input_design.qnt) uses two versions,
separate intent lineages, exact request and attempt IDs, and a two-key cap to
check insertion, one-key adoption, atomic routing, rollback and pinned
inspection. It abstracts record framing, transfer, collection and worker
execution. Use Java and Quint 0.34.0:

```sh
mkdir -p build/recorded-multi-input-tlc
(cd build/recorded-multi-input-tlc && quint verify ../../tests/recorded_multi_input_design.qnt \
  --backend=tlc --search-observations)
```

The [intent-scoped model](recorded_intent_reuse_design.qnt) uses two
implementations, three exact input keys, a two-key cap, and a history of up to
four deltas. It checks cross-version provenance, one-key updates and rollback,
pinned routing, and historical inspection independent of ref movement. Native
framing, transfer, collection, and worker execution are not modeled. Use Java
and Quint 0.34.0:

```sh
mkdir -p build/recorded-intent-reuse-tlc
(cd build/recorded-intent-reuse-tlc && quint verify ../../tests/recorded_intent_reuse_design.qnt \
  --backend=tlc --search-observations)
```

#### Check the argument-map design with TLC

The [argument-map model](recorded_argument_maps_design.qnt) uses five
constructions, two active rows at most, and a one-edit, one-request, optional
inspection sequence. It checks that equal typed maps can share a result
without replacing provenance, that changed values/types/keys miss, and that
stale pins, poisoned rows, forged decisions, and late faults do not publish.
It abstracts native framing, execution, and transfer; it does not prove
liveness. Use Java and Quint 0.34.0 and check that all ten observations are found:

```sh
mkdir -p build/argument-map-tlc
(cd build/argument-map-tlc && quint verify ../../tests/recorded_argument_maps_design.qnt \
  --backend=tlc --search-observations)
```
