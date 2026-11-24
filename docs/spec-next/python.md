# Python core binding

## Authority boundary

This document owns the public `daggerml.core` module: its Python arguments,
results, errors, and handle lifetime. The [C core contracts](README.md#concept-ownership)
own repository and encoding semantics. See [Build and validation](../../README.md#install-the-python-binding)
for installation.

The binding targets GIL-enabled CPython 3.10 or newer in the main interpreter.
It exposes the local operations below, not the entire C API. There are no
implicit ref selections, transactions, retries, or publication workflows.

## Handles and errors

- Repository, transaction, and object view handles are opaque and not
  interchangeable. Repositories and transactions MUST be used and explicitly
  ended on their creating thread before it exits. Do not reuse live handles after
  a fork or open the same physical repository more than once in one process.
- A repository handle permits one active transaction. The binding rejects a
  second begin with `RuntimeError` before calling C; a close with a live
  transaction is rejected by the core without consuming the repository.
- A live transaction keeps its repository alive. `txn_commit` consumes the
  transaction on C success or failure, including when a read or poisoned
  transaction cannot commit. `txn_abort` consumes the transaction and is safe
  on an already consumed handle from the same thread. Neither call implicitly
  closes an independently retained repository handle.
- Finalizing a live transaction on its owner thread aborts it, never commits
  it. If the last reference to a live transaction is dropped on a foreign
  thread, abort is deferred until the owner next calls `txn_begin` or
  `repo_close` on that repository, or finalizes it on that thread. Finalizing
  both handles on a foreign thread is unsupported: the binding reports an
  unraisable error and leaves the native resources open rather than aborting
  on the wrong thread. Use explicit cleanup, not finalization, for lifetime
  control.
- Packed records, IDs, names, and string datum inputs use immutable `bytes`.
  IDs are exactly 16 bytes, not hexadecimal strings. Returned bytes are owned
  by Python. An object view keeps its packed data alive independently of any
  repository or transaction. Decoding a `bytes` subclass copies the bytes
  without retaining the subclass instance.
- A failed C operation raises `daggerml.core.Error` (a `RuntimeError`) with
  `args == (status_name, native_code, detail)`, where status and detail are
  strings and the native code is an integer. The status is the machine-readable
  discriminator. Python conversion and handle misuse raise ordinary Python
  exceptions. If rejected before calling C, an argument does not poison a
  storage transaction; [C write failures](repository.md#transactions) still do.

## Public functions

Arguments are positional. Functions without a listed result return `None`.

| Function | Argument notes or result |
| --- | --- |
| `repo_open(path, create[, map_size])` | Path is `str`, `bytes`, or `os.PathLike`, converted using Python's filesystem encoding before calling C; `create` is `bool`. Returns a repository handle. Omitted or zero `map_size` uses the C default. |
| `repo_close(repo)` | Consumes the repository handle on success. |
| `txn_begin(repo, mode)` | `TXN_READ` or `TXN_WRITE`; returns a transaction handle. |
| `txn_commit(txn)`, `txn_abort(txn)` | End a storage transaction. |
| `txn_ref_create(txn, name, target)`, `txn_ref_update(txn, name, target)`, `txn_ref_delete_expected(txn, name, expected)` | Mutate a ref under the [C ref contract](repository.md#refs). |
| `txn_ref_get(txn, name)` | Commit ID. |
| `txn_put_datum(txn, packed)`, `txn_put_object(txn, type, packed)` | The stored object's ID. |
| `txn_get_datum(txn, id)`, `txn_get_object(txn, type, id)` | The packed record. |
| `txn_lookup_node(txn, dag, name)` | Node ID from the named binding in `dag`. |
| `datum_encode(kind, value)` | Packed datum. Exposed input kinds: `DATUM_I64` (signed 64-bit integer) and `DATUM_STRING` (UTF-8 bytes). |
| `datum_decode(packed)` | `(payload_bytes, kind)`; payload is canonical bytes, not a converted Python value. |
| `object_encode(type, ...)` | Packed object; see operand shapes below. |
| `object_decode(packed)` | `(view, reference_id, count)`; reference and count follow [`dml_object_view`](../../include/dml/object.h). |
| `object_view_entry(view, index)` | `(dag_id, name)` for a tree; index is zero-based. |
| `object_view_parent(view, index)` | Parent commit ID for a commit; index is zero-based. |

`object_encode` accepts these operands after the record type:

- `REC_NODE`: `target` for a literal, or `kind, target` for explicit
  `NODE_LITERAL` or `NODE_SUBDAG`.
- `REC_DAG`: `root`, followed by zero or more `name, node_id` pairs.
- `REC_TREE`: zero or more `name, dag_id` pairs.
- `REC_COMMIT`: `tree`, followed by zero or more parent commit IDs.

## Informative example

Read the commit ID under `main` from an existing repository:

```python
from daggerml import core

repo = core.repo_open("./repo", False)
try:
    txn = core.txn_begin(repo, core.TXN_READ)
    try:
        print(core.txn_ref_get(txn, b"main").hex())
    finally:
        core.txn_abort(txn)
finally:
    core.repo_close(repo)
```
