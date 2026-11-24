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
record and inspect processes and observes the JSON report and committed LMDB
bytes. Quint supplies the [input histories](recorded_calls_histories.qnt) and
[judges the report](recorded_calls_rules.qnt). For split recording, the runner
passes the exact commit ID printed by an earlier sum process, not the current
pin target. Two sums in the same repository share a result node. Quint checks
that each scale report refers to its selected producer commit and reports the
same producer DAG seen in an independent inspection of that sum. Stale and
missing pins, overflow, and a duplicate result ref must leave `data.mdb`
unchanged.

The [focused tests](test_recorded_calls.py) independently read both physical
links with the public binding. They also check that inspection rejects an
inconsistent parent and input DAG, works after the producer pins are moved or
released, and does not recompute results. An intentionally incorrect stored sum
checks that composition consumes the stored value. Both the workflow and
focused tests run in the opt-in Meson gate.

The [one-way bundle handoff](../README.md#compose-from-a-producer-in-another-repository)
exercises the same caller on a second repository through the public binding.
The replay checks read-only export, bundle file preservation, create-only staging,
rejection of a valid same-valued decoy, release guarded by the expected producer,
and readback after release and collection. The focused tests also verify that
both physical links survive while collection removes an unpinned decoy, that
release rejects a result with the correct parent and the wrong input DAG, and
that a deliberately incorrect stored sum is transferred and consumed unchanged.

The [return and publication history](../README.md#return-and-publish-a-recorded-scale)
checks exact result export and staging, rejection of a same-valued wrong producer,
and conditional publication to either an absent or an existing `main`. Two scales
of a zero sum share an output node but record different factors. Even when the
exact result is staged and `main` matches, publication rejects the wrong factor
and accepts the same result with the matching expectation. Any rejection must
leave committed bytes unchanged. Success releases the staging ref and leaves both
calls readable after a sweep that removes the superseded result. The focused tests
exercise rollback after a tentative main create or update, reject a staging alias
of `main` and a mismatched input DAG, and publish a deliberately incorrect stored
output. They read the physical lineage links after collection with no separate
source producer pin.

The [durable-request history](../README.md#save-a-scale-request-before-sending-it)
starts separate processes for planning, dispatch, work, staging, and publication.
It checks two requests with the same zero-valued sum and different factors, and
rejects a wrong request, stale plan, stale staging selection, and stale `main`
without changing committed bytes. The focused tests update an existing `main`,
verify its previous tip is not exported when unrelated to the request, and
resume publication without the bundles or producer pin. They also reject a
forged factor or input edge under the right request parent, and directly check
that the published worker result, request, producer commit, and sub-DAG edge
survive collection.

The [publication retry history](../README.md#retry-publication-if-its-acknowledgment-was-lost)
checks first publication, a matching retry, rejection under a missing or occupied
key, and a retry after a second publication and collection. The retry must return
the first result ID without changing committed bytes or the newer tip. The focused
tests also check atomic rollback of a tentative receipt, reused pin names, a retry
with all first-publication guards satisfied again, and physical reclamation of the
old commits despite the retained receipt.

The [abandonment history](../README.md#abandon-a-scale-request-without-publishing)
checks that a late staged result cannot publish after abandonment, no receipt or
`main` appears, and a stale ID cannot delete a replacement plan under the same
name. Removing the replacement leaves the exact staged result intact. The
publication retry history covers the opposite order: a consumed plan cannot be
abandoned, and the publication receipt still acknowledges success. Focused
checks cover a moved `main`, invalid and non-plan selections, exact ref
preservation, and explicit collection.

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
survives, and that `main` still reports the original graph. Focused tests inspect
the record's parent edges and check retention after collection and rollback on
an occupied reuse ref.

The [version selection history](../README.md#select-a-scale-implementation-version)
checks that the default and explicit `@1` plans have the same ID, then runs `@1`
and `@2` through separate worker commands. The recorded calls share arguments
and an output node, not request, call, or result IDs. Replay checks rejection
without writes for an unsupported version and for cross-version publication
and reuse, then publishes and reuses the matching `@2` result. The focused
checks reject an imported request for an unsupported version and a result
with the exact request parent but the wrong recorded implementation.

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
