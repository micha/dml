# Quint trace interpreter

[`run_histories.py`](run_histories.py) is the shared entry point for the ref and
transfer suites. Run it through [`scripts/check.sh --quint`](../README.md#quint-behavior-checks).
Meson supplies the adapter, native executables, and Quint history and rule modules.

Quint emits ordered histories of `{ op: str, args: List[str] }` requests. The
interpreter creates a fresh fixture per history, calls registered handlers in
order, and returns one observation per request. A handler records the actual
API status, even on an expected failure. Unknown operations, bad arguments,
and missing observations or verdicts fail the test rather than skipping a step.

The ref suite stages a tree, its commit, and a move of an existing ref in one write
transaction. It checks successful commit, explicit abort, and rollback when a later
update to a missing ref poisons the transaction. It also checks caller-side
conditional publication using the existing C API: two readers observe the same
`main` tip, one writer moves it, and the other writer aborts because the tip no
longer matches. Each writer compares and updates within one write transaction.
An independent LMDB scan checks exact persisted changes, and a fresh native
process resolves the ref and decodes its commit and parent IDs.

The transfer suite checks that import leaves refs alone. A separate write
transaction creates `incoming`, and the LMDB scan checks that only that ref was
added. Fresh native processes resolve `incoming`, read its commit and first
parent, and verify that `main` is unchanged. Explicit publication then moves
`main` in its own transaction. The same tree entry and DAG binding path is absent
at the initial `main` but yields the expected datum ID, kind, and scalar value at
the staged and published tips and their first parent. Each read must leave the
inventory unchanged.

A separate transfer history exercises [the caller's result format](../docs/spec-next/transfer.md#record-a-result-without-publishing-to-main).
The native caller calculates a result from the exact selected commit, then records
and pins it in one transaction. Quint checks the exact new LMDB rows and verifies the
stored value, implementation ID and parent through a fresh native process. A second
computation uses the same pin but stages distinct objects; its duplicate-pin
failure must roll back all of them without disturbing the existing pin, `main`, or
`incoming`.

The [return-trip history](../docs/spec-next/transfer.md#return-and-publish-the-recorded-result)
checks the full exported closure, exact import delta without ref changes, and
inspection by returned commit ID. A stale conditional publication must change
nothing. A matching expectation moves only the original repository's `main`,
which a fresh process resolves to inspect the same stored lineage again. The
worker then rejects a stale release, aborts a matching release, and commits a
matching release of `incoming`. The scan requires exactly one ref row removed
and no object changes. A repeated release fails, and fresh native processes
verify the same stored lineage through the worker's pin and the source's `main`.
The [integrity scan](../docs/spec-next/repository.md#snapshot-integrity-and-reachability)
reports those imported objects as intact but unreachable before staging, and as
reachable once staged and again after release while the pin remains. On the
source, the old `main` closure becomes unreachable after publication. Quint
compares exact typed object IDs and independent LMDB scans require unchanged
inventories during checks. The focused native integrity test covers broken
refs, records, and graph edges.

## Add a request or operation

- To exercise an existing operation, add a request to its `*_histories.qnt`
  module. For example, `createRef("main", "B")` asks the interpreter to call
  the registered `create_ref` handler with arguments `main` and `B`.
- For a new operation, register a handler in the adapter's `Replay.operations`
  mapping. The adapter's `Suite.history()` context manager owns setup and
  cleanup; handlers translate arguments to native calls and collect evidence.
  Add native replay support if the executable cannot yet make that call. No
  dispatch change in `run_histories.py` is needed.
- Update the Quint rules for any new evidence or behavior. A rule module exports
  an `Observation` type (one history with `attempts` and optionally `fixture`),
  `historyVerdicts(observed)`, `verdictAccepted(verdict)`,
  `coveragePass(evidence, verdicts)`, and `controlsPass`. A verdict reports the
  result for one attempt; only the rule module decides which results pass and
  what coverage is required. Keep synthetic controls that show the rules reject
  incorrect evidence.

Use the independent LMDB inventory helper at publication boundaries when checking
persisted state. Encode arbitrary bytes as hex in the evidence; the interpreter can
embed records, lists, booleans, integers, and plain ASCII strings without quotes
or backslashes in generated Quint source.
