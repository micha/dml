# Python Bindings Specification

Status: Draft.

This document defines the proposed high-level Python API over packed records.
Bindings are thin wrappers; core validation and business rules live in the C
library.

Authority boundary:

- This document is authoritative for Python API surface and Python-specific
  binding behavior.
- For packed-record schemas, canonical encoding/hashing, keyspace, and
  validation/error semantics, see `docs/spec/object-model.md`.
- For execution lifecycle, cache/retry behavior, and remote execution protocol,
  see `docs/spec/execution-and-remotes.md`.
- For CLI command contracts, see `docs/spec/cli.md`.

## 1. Scope

- Expose a practical API for DAG construction, execution, and commit workflows.
- Hide packed-record internals by default.
- Allow future low-level escape hatches without changing core semantics.

Implementation target:

- CPython extension, no runtime Python dependencies.
- Prebuilt wheels bundling the static core library.

## 2. Core Types

- `Repository`
  - `open(path, create=True) -> Repository`
  - `head(name) -> Commit`
  - `heads() -> list[str]`
  - `new_dag(name, base="main") -> Dag`
  - `get_commit(commit_id) -> Commit`
  - `fast_forward(head_name, commit_id) -> None`
  - `rebase(commit_id, base_commit_id) -> Commit`

- `Dag`
  - `literal(value, name=None) -> NodeHandle`
  - `call(function_node, args, name=None, cache=True) -> (NodeHandle, ExecutionHandle)`
  - `builtin(function_node, args, name=None) -> NodeHandle`
  - `import(dag_id, name=None) -> NodeHandle`
  - `commit(result_node) -> Commit`

- `NodeHandle`
  - `id`
  - `kind`
  - `name`

- `ExecutionHandle`
  - `wait() -> dml_object_id`
  - `status` (`pending`, `ok`, `error`)
  - `exec_id`

- `Commit`
  - `id`
  - `tree_id`
  - `parents`
  - `exec_map`

## 3. Literal Lowering Rules

- `dag.literal(<datum>)` lowers values into canonical datum/node structures per
  `docs/spec/object-model.md` Section 7.2 and Section 7.3.
- Passing an existing `NodeHandle` to `literal` is a no-op.
- Collections lower recursively (post-order) through builtin constructors.

Lowering examples:

- `dag.literal([1, 2, n])` -> `dml://list/construct`
- `dag.literal({"k": v})` -> `dml://map/construct`
- `dag.literal({v1, v2})` -> `dml://set/construct`
- `dml://list/construct` returns a `DML_DATUM_LIST` preserving element order.

## 4. Async Call Semantics

- `dag.call(...)` follows the execution lifecycle in
  `docs/spec/execution-and-remotes.md` Section 1 and returns an
  `ExecutionHandle`.
- `wait()` yields a DAG id on success.
- Success/failure record writes follow `docs/spec/object-model.md` Section 7.4.
- On failure, bindings raise a Python exception.
- Default behavior reuses exec pinned in active index commit.
- `cache=False` forces a new attempt.

Builtin calls execute synchronously and do not return async handles.

## 5. URI Helpers

- `dml.Uri("...")` constructs URI datum values.
- `dml.Uri.from_string(raw)` canonicalizes to RFC 3986 form before datum
  creation.

## 6. Standard Library Builtin URIs

List:

- `dml://list/construct`
- `dml://list/get`
- `dml://list/add`
- `dml://list/prepend`
- `dml://list/append`
- `dml://list/remove`
- `dml://list/union`

Set:

- `dml://set/construct`
- `dml://set/get`
- `dml://set/add`
- `dml://set/remove`
- `dml://set/union`
- `dml://set/intersection`
- `dml://set/difference`

Map:

- `dml://map/construct`
- `dml://map/get`
- `dml://map/assoc`
- `dml://map/dissoc`
- `dml://map/union`
- `dml://map/intersection`
- `dml://map/difference`

## 7. Example

```python
repo = dml.Repository.open(path)
dag = repo.new_dag("my_dag", base="main")

raw = dag.literal(dml.Uri("s3://bucket/data.csv"), name="raw_uri")
fn = dag.literal(dml.Uri("s3://spark/jobA"), name="fn")
node, run = dag.call(fn, [raw], name="b")
run.wait()

dag.commit(node)
```
