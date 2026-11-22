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
update to a missing ref poisons the transaction. An independent LMDB scan checks
exact persisted changes, and a fresh native process resolves the ref and decodes its
commit and parent IDs. The transfer suite checks that import leaves the destination
ref alone, then moves it to the imported commit in a separate transaction and
reopens the repository to read the new tip.

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
