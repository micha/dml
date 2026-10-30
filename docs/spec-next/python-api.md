# Low-level Python repository API

Status: implemented by `daggerml`, backed by the native C codecs and repository.

## Authority boundary

This document owns Python conversions, owned descriptions, exceptions and handle
lifetime/context restrictions. [Records](records.md), [objects](objects.md) and
[repository](repository.md) own C encoding/storage semantics. [CLI](cli.md) owns
inspection presentation; [packaging](../packaging-and-distribution.md) owns builds.
The separate [local-execution layer](local-execution.md) owns trusted Python-step
execution and ordinary request/attempt/publication conventions over this API.
The explicit [transfer layer](transfer.md) owns bounded pinned-commit bundles,
complete typed closure checks and optional atomic ref creation. The explicit
[repository-execution layer](repository-execution.md) composes those public APIs
for one pinned step in independent local B and a validated explicit-ref return to A.
Its additive [asynchronous contract](asynchronous-execution.md) owns saved handles,
live application-owned worker launch, read-only packet inspection and bounded immutable
progress observation/reception. The separate [SSH contract](ssh-execution.md) composes these
public authorities with strict transport, saved SSH identity and a live foreground owner.
The separately imported [Floci contract](floci-execution.md) owns one-shot local Batch
submission/saved external identity and immutable S3 progress, reusing the same owning
exact-Q inspector/explicit-ref return without changing native handles or roles.
The additive [caller-request contract](caller-requests.md) owns request-only construction,
explicit atomic A recording and public imported-Q first registration through these APIs.

## Values and descriptions

`version()` returns the linked C core version. `ObjectId(bytes)` is frozen,
hashable and requires exactly 16 immutable bytes. `ObjectId.from_hex(str)` calls
C's lowercase-hex parser; `str(id)` returns lowercase hex. IDs are untyped; reads
and writes establish expected types. Methods require explicit `ObjectId` values,
not implicit hex strings or integers.

`Datum(kind, value)` is frozen, with lowercase string kinds. `get_datum()` returns
a `Datum`, **not** a bare Python value or recursively dereferenced collection.
Access `.value` explicitly. Constructors are `null()`, `bool(value)`, `i64(value)`,
`f64(value)`, `bytes(value)`, `string(value)`, `uri(value)`, `list(ids)`, `set(ids)`
and `map(pairs)`. Scalar constructors require the exact Python type; I64 requires
signed 64-bit range. Collection constructors copy to tuples of IDs or ID pairs,
without deduplication. C rejects duplicate SET items and MAP keys during insertion.

`put_datum()` accepts a `Datum` or exact scalar types: `None`, bool, int, float,
bytes and str. Bool is not converted to I64. Python list/set/dict and arbitrary
coercible objects are rejected; children must be inserted explicitly first.
Decoded collection values are tuples of IDs, or tuples of `(key_id, value_id)`.

C owns NFC normalization, canonical float encoding and URI validation. A URI
constructor only marks the kind. `canonicalize_uri(str) -> str` calls C's separate
helper; use `Datum.uri(canonicalize_uri(text))` when normalization is intended.

Other frozen descriptions:

| Read | Result |
| --- | --- |
| `get_node(id)` | `LiteralNode(datum: ObjectId)` or `SubDAGNode(dag: ObjectId)` |
| `get_dag(id)` | `DAG(root: ObjectId, bindings: read_only_mapping)` |
| `get_tree(id)` | `Tree`, read-only Mapping with tuple `entries` in stored name order |
| `get_commit(id)` | `Commit(tree: ObjectId, parents: tuple[ObjectId, ...])` |

Descriptions and record bytes are copied while C views are valid. They remain
usable after transaction/repository closure and never retain native pointers.
They do not execute nodes or lazily load references. `DAG` copies a mapping or
sequence of name/ID pairs into a read-only mapping; duplicate description names
are rejected. Retrieved bindings preserve canonical stored order. Root-only
`DAG(root)` descriptions have empty bindings. `SubDAGNode` stores an explicit DAG
ID, not a moving ref or an execution request.

## Repository and transactions

`Repository(path, *, create=False, map_size=0)` opens immediately. It accepts
filesystem path-like values via `os.fspath`/`os.fsdecode`, then sends Unicode as
UTF-8 to C. NUL is rejected; undecodable POSIX byte paths represented by surrogate
escapes cannot cross that UTF-8 boundary. Windows uses the existing C path API, not
a new wide-character filesystem implementation. `create` requires bool;
`map_size` requires int (nonnegative, representable as Python `Py_ssize_t`). Zero
uses the C default. Creation does not create missing parent directories.

`repo.schema`, `repo.read()`, `repo.write()` and `repo.close()` call real native
handles. Transactions begin when `read()`/`write()` returns them. `Transaction`
is an exported description of the type, but direct construction is rejected;
use the repository factories. The wrapper permits only one active transaction
per repository. Multiple wrappers for the same physical repository in a process
are unsupported, not coordinated by a global registry.

Both transaction modes provide:

- Typed `get_datum`, `get_node`, `get_dag`, `get_tree`, `get_commit` and `get_ref(name)`.
- `get_record(kind, id) -> bytes`, for datum/node/dag/tree/commit only, through C's
  validated typed read. This is exact immutable record inspection, not raw LMDB IO.
- `lookup_node(dag_id, name) -> ObjectId`: exact single-scope lookup, not a value.
  Explicit nested descent reads a `SubDAGNode` then looks up in its `.dag`.
  Invalid/missing names are read failures and do not poison writes. See the
  [native lookup contract](repository.md#scoped-node-lookup).
- `abort()` to consume the transaction without publishing its writes.

Write transactions also provide:

```python
put_record(kind, record) -> ObjectId
put_datum(value) -> ObjectId
put_literal(datum_id) -> ObjectId
put_subdag(dag_id) -> ObjectId
put_dag(*, root=node_id, bindings=()) -> ObjectId
put_tree(mapping_or_pairs) -> ObjectId
put_commit(tree_id, *, parents=()) -> ObjectId
create_ref(name, commit_id) -> None
update_ref(name, commit_id) -> None
commit() -> None
```

`put_record(kind, record)` accepts an exact string kind (`datum`, `node`, `dag`,
`tree`, `commit`) and exact immutable `bytes`. It calls existing native packed
insertion, returning the computed content ID. It does not accept metadata, refs,
arbitrary keys, mutable buffers or implicit kind inference. Native encoding/type,
direct dependency and no-overwrite checks apply; existing identical bytes succeed,
corruption is never skipped/repaired. Conversion/native/allocation failure poisons
like other mutations, including a failed ID-return allocation after native insertion.
Read transactions reject it without being ended or poisoned. It does not bypass
ownership/lifetime rules or introduce a Python packed codec.

Tree and DAG-binding input accepts mappings or pair sequences, preserving duplicate
names until C rejects them. Parent order is preserved;
C validates names, duplicates and direct references. No recursive Python value
insertion, automatic map growth or partial retry is performed. Map-full recovery
closes/reopens with a larger map and retries the whole batch.

## Contexts and failure handling

- Repository/transaction entry returns itself. Repeated/nested entry is rejected.
- Normal write-context exit commits the **storage transaction**; exceptional exit
  aborts and propagates the original exception. Read-context exit always aborts.
- Explicit write `commit()` consumes the transaction on success/native failure.
  Read `commit()` is rejected by the wrapper without ending the read transaction.
- `abort()` and successful repository `close()` are idempotent, including after an
  ended transaction's owner was explicitly closed. Other ended-handle operations
  raise `InvalidStateError`. Context exit after explicit endings does not repeat
  completion or mask an unrelated exception.
- Every failed public mutation marks the write transaction unusable, including
  Python conversion/codec failures before a native put. Catching the error does
  not permit earlier writes/ref movement to commit. A later `commit()`/normal
  write-context exit aborts the entire batch and raises `InvalidStateError`.
- Failed reads do not poison a write transaction. Read-write rejection occurs
  before attempting mutation and does not change a read transaction.
- `close()` rejects active transactions. Repository-context exit aborts a still
  active transaction before closing; it never implicitly commits abandoned writes.

## Thread and finalizer policy

Operations require the creating thread. The binding holds the GIL during native
calls; this is not a concurrency protocol or a free-threaded-Python guarantee.
The creating thread must remain alive until handle cleanup. Transactions retain
their repository owner, while the owner keeps only a weak transaction reference;
there is no native-owner reference cycle.

Finalizers are a cleanup fallback, never a supported publication mechanism:

- A transaction dropped on its creating thread aborts.
- A live transaction's last reference dropped on another thread queues its native
  handle on its repository **without ending it**. The next creating-thread native
  repository operation, or creating-thread repository finalization, aborts/reclaims
  that pending transaction. Holding the GIL serializes queue ownership.
- **Unsupported misuse:** dropping the repository's last native owner reference
  on a foreign thread while transactions remain pending leaves no legal cleanup
  invocation. It emits `ResourceWarning` and deliberately abandons native resources
  until process exit rather than ending a transaction from the wrong thread.
  Warnings promoted to errors are reported through the unraisable hook, without
  resurrecting the dying capsule. This case is safe abandonment, **not leak-free
  supported finalization**; tests isolate it in disposable subprocesses.

Always finish contexts and close the owner on its creating thread. An idle native
repository finalizer can close its handle without ending any transaction.

## Errors

`DmlError` carries `code` (C status name), `native_code` (int) and `detail` (str).
`NotFoundError`, `InvalidStateError`, `IntegrityError` and `MapFullError` specialize
corresponding statuses; other native statuses retain the base class, including C
allocation failures. Python argument errors use TypeError/ValueError/OverflowError;
CPython/binding-side allocation failures use MemoryError. C's distinction between
missing composite children (`invalid_kind`) and missing object references
(`not_found`) remains visible.

## Informative example and evidence

[The runnable history example](../../examples/repository_history.py) records 42,
then 43 in a child commit, moves `main`, and creates a fork. It prints IDs and saved
record bytes for [CLI inspection](cli.md). Higher-level helpers can compose this
API; this example is not a library workflow framework. The
[composable DAG example](../../examples/composable_dags.py) records two Python
calculations, shares one trial across child snapshots, and includes a nonliteral
root fixture. It demonstrates containment/values, not captured computational causality.

The [local execution example](../../examples/local_execution.py) uses that separate
layer to execute captured trusted entry bytes, publish results and record outcomes;
it does not add execution semantics to low-level nodes or lookup. The
[pinned transfer example](../../examples/pinned_transfer.py) copies exact recorded
history through the separately imported transfer layer without executing it. The
[repository execution story](../../examples/repository_execution.py) runs trusted
captured source in independent local B, then returns selected history under explicit
A refs without moving A's existing heads. The informative
[composed recorded-steps example](../composed-recorded-steps.md) uses the same public
transactions and validated packet descriptions for result-backed consumer inputs and an
ordinary summary. Its example-local helpers introduce no public framework or native entity.
The informative [explicit historical-attempt reuse example](../explicit-attempt-reuse.md)
records its own new request and, separately, an ordinary association to a validated old
successful attempt/result. It uses these unchanged public transactions and exact packet
inspection, without a public cache API or another native object kind.
The informative [versioned selection/adoption example](../versioned-reuse-selection.md) records
ordinary S/V DAGs, reconstructs bounded public validation framing from pinned repository state
and delegates to the existing Q/W example. It changes no native handle, record kind or public
repository API; fresh execution does not automatically change the recorded choice.
The informative [intent-defaults example](../intent-reuse-defaults.md) adds ordinary Idef/D
and a decision-bearing submission parent, using existing public temporary preparation and
Q/Q-W authority. It changes no public/native API, role or package installation inventory;
its readers require an explicit Q rather than treating fresh-Q preparation as submitted-Q
validation.

Evidence: [native binding](../../python/daggerml/src/_core_module.c),
[Python surface](../../python/daggerml/daggerml/__init__.py),
[public tests](../../tests/python/test_python_api.py),
[fresh-process acceptance](../../tests/python/test_public_acceptance.py),
[failure tests](../../tests/python/test_binding_failures.py) and
[lifetime edges](../../tests/python/test_lifetime_edges.py).
Actual validation and platform limits belong to
[Iteration 2 results](../../../dml-design/iterations/02-repository-usability/RESULTS.md)
and [Iteration 3 results](../../../dml-design/iterations/03-composable-dags/RESULTS.md).
