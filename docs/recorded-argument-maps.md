# Recorded argument maps

**Informative example.** [`recorded_argument_maps.py`](../examples/recorded_argument_maps.py)
uses ordinary DAGs and commits through [`daggerml.core`](spec-next/python.md).
It does not change native records, add a general evaluator, or change the
[scale example's exact-input policies](../README.md#share-selected-scale-results-across-implementations-of-one-intent).

## Reuse equal arguments without losing their origins

Run from the repository root with the [Python binding installed](../README.md#install-the-python-binding).
Use a new repository path, such as `./maps-demo`:

```sh
maps() { python examples/recorded_argument_maps.py "$@"; }
repo=./maps-demo

maps request "$repo" literal literal-decision double@1 --arg x=i64:42
# `request` prints a decision ID. Read the exact pending request ID before working it.
literal=$(maps inspect "$repo" literal | python -c 'import json, sys; print(json.load(sys.stdin)["requested"]["request"])')
first=$(maps work "$repo" literal "$literal" first)
empty=$(maps define-table "$repo" empty double)
selected=$(maps update-table "$repo" empty "$empty" selected insert --selected first "$first")

maps request "$repo" sum sum-decision add@1 --arg a=i64:13 --arg b=i64:29
sum=$(maps inspect "$repo" sum | python -c 'import json, sys; print(json.load(sys.stdin)["requested"]["request"])')
computed=$(maps work "$repo" sum "$sum" computed)

maps request "$repo" unused hit double@2 --arg "x=from:computed:$computed" \
  --mode try-selected --table-ref selected --table-commit "$selected"
maps inspect "$repo" hit
```

The hit reports `outcome: "reuse"` and `value: 84`. `requested` describes a
new `double@2` request whose `x` comes from the selected addition attempt.
`producing` describes the old `double@1` request whose `x` was a literal. Their
`argument_map` IDs agree; request and construction IDs differ. `map_gets`
belongs to the old result. The hit moves `main` to that result and leaves
`unused` absent: there is no new result, attempt, or getter trace. Using a
successful addition of `13 + 30` as `x` instead yields `outcome: "pending"`:
that request has a different map and can be run with `work`.

## What is recorded

- `map_empty` and each immutable `map_insert` record have a MAP literal root.
  Each insert also links the previous construction, exact STRING key, and
  inline literal or returned source. A returned source names an exact
  successful attempt matched against its ref and links that result DAG. The
  attempt is a parent of the request, so the association survives transfer.
  The reader checks the construction against the canonical packed map, not
  against a value-to-source lookup. MAP pairs contain only datum IDs.
- The request stores the complete construction, the map, the requested
  implementation, and a UUIDv4 invocation ID. `work` supplies copied datums
  and one bound `map_get` to fixed Python callables, not a repository, request
  handle, or graph API. A successful getter is recorded in order and is tied
  to the exact construction of the producing request. Work publishes the
  result and the UUIDv4 attempt occurrence together in one transaction.
  The CLI generates invocation and attempt IDs by default. If supplying them
  explicitly, use a fresh ID per occurrence; reusing an ID with identical records
  does not distinguish another occurrence. Failed work records neither a
  successful result nor a trace. This is a
  cooperative Python interface, not a sandbox, proof of purity, or attestation
  of execution by an untrusted repository writer.
- An immutable table version belongs to the fixed `add` or `double` intent.
  Each row maps a canonical MAP datum ID to an explicitly selected successful
  attempt. Key, type, and value matter; insertion order and derivation do not.
  `insert` adds an absent key, `adopt` replaces an existing key with a different
  attempt, and `remove --key MAP_ID` removes one existing key without a selection.
  Prior versions stay immutable. Readers validate all edits, even ones on other
  keys or later removed. Selection authorizes reuse; it does not establish
  equivalence between implementation versions.
- `fresh` ignores the table. `try-selected` leaves a pending request on a miss;
  `require-selected` rejects a miss with no publication. Both reuse modes
  require a table ref and either its exact commit or expected absence (omit
  `--table-commit` for absence). There is no discovery or automatic adoption.
  The route, output refs, and any `main` update commit together. An occupied
  output ref rejects the transaction. A decision retains its own request and
  consulted version, plus the original attempt on a hit. Inspecting a decision
  transferred under a new ref does not need the old refs or run a callable.

This profile supports at most 16 named arguments (canonical STRING keys with
no duplicates), 16 live table entries, and 64 reached attempts in a returned
source walk. Sources are inline I64 or STRING literals, or I64 returns from
successful attempts in this profile; arbitrary DAG roots and legacy results
are not sources. The fixed `add@1`, `double@1`, and `double@2` callables read
I64 arguments and return I64. For canonical map values and their closure, see
[records](spec-next/records.md#datum-model) and [transfer](spec-next/transfer.md).
