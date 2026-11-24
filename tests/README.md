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
