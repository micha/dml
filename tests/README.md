# Quint trace interpreter

[`run_histories.py`](run_histories.py) is the shared entry point for the ref,
transfer, staged-import, and garbage-collection suites. Run it through
[`scripts/check.sh --quint`](../README.md#quint-behavior-checks).

## Direct core replay

Each history is an ordered list of `{ op: str, args: List[str] }` requests.
Each request names **one DML core function**, without the `dml_` prefix. The
[shared adapter](replay_core.py) resolves handles, object IDs and buffers, then
calls the matching [Python binding](../python/dml_core.c) once. The binding is
private and built only for opt-in tests. Neither layer implicitly begins,
commits or aborts transactions, or decides whether a core outcome passes.

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
