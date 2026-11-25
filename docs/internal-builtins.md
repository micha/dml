# Internal versioned built-ins

## Authority boundary

This document owns the installed `daggerml.builtin` API and its ordinary DAG
profiles. [Objects](spec-next/objects.md), [records](spec-next/records.md), and
[Python core](spec-next/python.md) own the underlying storage and handles.

## Calling convention

A built-in takes a recorded **argument-map node** and returns a recorded **value
node**. The native MAP contains datum IDs, not node IDs. Each named argument also
links its exact source DAG. Equal values can share a datum ID without sharing a
source; a nested getter can take the node returned by a previous getter directly.

| Func under `dml://builtin/` | Exact arguments | Result | Source under `dml://source/builtin/` |
| --- | --- | --- | --- |
| `map/empty` | none | Empty MAP | `map/empty/v1` |
| `map/insert` | `map`, `key`, `value` | New MAP; leaves the input unchanged | `map/insert/v1` |
| `map/get` | `map`, `key` | Selected datum | `map/get/v1`, `map/get/v2` |
| `list/get` | `list`, `index` | Selected datum | `list/get/v1` |

Map operations accept MAPs of at most 16 STRING keys. Inserting an existing
canonical key is an error, including when the original spellings differ but are
NFC-equivalent. A missing key is an error. A list index must be I64 and in bounds;
negative indexing and coercion are not supported. A selected value can itself
be a collection. Native collection formats and limits are unchanged.

The exact func and source URI pair selects a shipped handler. `map/get/v1`
uses linear lookup and `map/get/v2` uses keyed lookup, with the same results and
errors. No URI is fetched or imported, and an unsupported pair never falls back.
An unknown canonical source URI can be stored and inspected without being
executable. There is no mutable registry or implicit default lookup.

## Recorder and reader

- `put_binding(txn, source_uri)` writes an internal binding and returns its DAG
  ID. `inspect_binding(txn, dag)` returns its ID and source URI. URI inputs are
  canonical `bytes` as in the [core binding](spec-next/python.md#public-functions).
- `with Recorder(txn) as recorder:` uses a single, caller-owned write transaction.
  `literal(kind, value)` authors a node; `source(source_dag, name)` pins an exact
  named native literal; `load(dag)` reads an exact supported profile. Each
  returns a `ValueNode` whose `.value` is a copied `Datum(kind, payload)`;
  `as_i64()` reads an I64. Handles are valid for authoring only in their original
  active scope. The copied value can outlive the scope.
- `arguments(entries=())` accepts a mapping or iterable of `(bytes, ValueNode)`
  pairs. It sorts canonical names and retains every exact source. `call(func_uri,
  binding_dag, arguments)` requires an owned argument node and records one
  operation. `dag(node)` returns the node's native DAG ID for trusted publication.
- `operations(map_binding=..., list_binding=...)` gives trusted logical Python
  code `map_get`, `list_get` and scalar `literal` (I64 or STRING) conveniences.
  Getters prepare their own argument nodes and use the same versioned dispatch.
  They do not offer raw datum-ID lookup. This is a cooperative interface, not a
  sandbox against Python introspection or a proof that a call ran.
- `trace()` returns the DAG ID of the ordered successful call positions.
  `returned(node, inputs=argument_node)` records a normal callable's exact returned
  node, value, input node and trace. A surrounding workflow must associate this
  record with its exact request and attempt; this structural profile alone does
  not establish successful attempt provenance.
- Use the transaction on its creating thread. The trusted caller publishes refs
  and commits only after successful scope exit. An escaping exception or a caught
  authoring error aborts the supplied transaction on exit. There are at most 16
  arguments, 16 call positions and 64 distinct reached DAG IDs per recorder.
  Repeated operation IDs count separately as call positions. The DAG limit
  includes newly authored and loaded profiles, bindings, traces and named source
  DAGs; it is not a bound on total bytes or native datum closure.
- `Inspector(txn)` describes immutable profiles via `node`, `arguments`,
  `operation`, `returned`, `trace` and `binding`. Each graph read validates its
  reachable profiles within the same bounds and recomputes fixed operation
  semantics without authoring or running an ordinary callable. Description
  fields are immutable and retain no transaction or native pointer.

### Recorded profiles

All profiles have a `role` STRING binding and use ordinary literal and sub-DAG
nodes. `binding` and `trace` profiles have their `role` as the native root. Each
value-bearing profile binds the literal root as `value`:

| Role (`builtin-…-v1`) | Other fields |
| --- | --- |
| `binding` | `source` URI; `adapter`, `interpreter`, `timeout-ms` all NULL |
| `literal` | None |
| `literal-source` | `source` DAG and `name` of its exact literal binding |
| `arguments` | Contiguous `key-00`/`source-00` pairs in canonical name order |
| `operation` | `func` URI, exact `binding`, `arguments` |
| `trace` | Contiguous `call-00`, `call-01`, … operation links |
| `return` | `inputs`, `returned`, `trace` |

## Example: promote a getter and reuse an ordinary result

**Informative.** With the [wheel installed](../README.md#install-the-python-binding), run
[`recorded_builtins.py`](../examples/recorded_builtins.py) from the checkout:

```sh
builtins() { python examples/recorded_builtins.py "$@"; }
repo=./builtins-demo                       # Use a new path.
initial=$(builtins define-choice "$repo" initial)
builtins request "$repo" initial "$initial" pending first 42
request=$(builtins inspect "$repo" first | python -c 'import json,sys; print(json.load(sys.stdin)["requested"]["request"])')
promoted=$(builtins promote "$repo" initial "$initial" promoted)
builtins compatibility "$repo" promoted "$promoted" versions
builtins inspect "$repo" versions
old=$(builtins work "$repo" pending "$request" old)
builtins request "$repo" promoted "$promoted" unused hit 42 --source named \
  --mode require-selected --selected-ref old --selected "$old"
builtins inspect "$repo" hit
```

The compatibility record links both versions applied to the same argument node;
its report follows their `map/insert` and `map/empty` dependencies. The old
request was pinned before promotion, so `work` still uses `map/get/v1` followed
by `list/get/v1` to return the first list item. The hit requests `map/get/v2`
and uses a different list source, but the argument MAP values match. The
reader reports both constructions and only the old producing trace. No `unused`
ref or fresh attempt is created. Transfer the hit decision to inspect its
closure under a different ref without the original refs or any ordinary work.

Use `43` with `--mode try-selected` to record a miss. `require-selected`
rejects a miss; `fresh` ignores selection. When consulting a selection, pass the
exact attempt commit or omit `--selected` to require that the named ref be absent.
A stale or invalid selection is an error even when the values differ. Outputs
use new refs; `main` changes with successful work or reuse in the same write
transaction. A pending ref pins the immutable request for `work`; it is not a
consumed queue item. This example is a fixed in-process workflow, not a general
ordinary-func dispatcher, worker system, or execution attestation.
