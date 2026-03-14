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
- For execution lifecycle and cache/retry behavior, see
  `docs/spec/execution.md`.
- For remote execution protocol, see `docs/spec/remotes.md`.
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
- Collections lower recursively (post-order) through internal builtin
  constructors.

Lowering examples:

- `dag.literal([1, 2, n])` -> `dml://seq/new`
- `dag.literal({"k": v})` -> `dml://map/new`
- `dag.literal({v1, v2})` -> `dml://set/new`
- `dml://seq/new` returns a `DML_DATUM_LIST` preserving element order.

## 4. Async Call Semantics

- `dag.call(...)` follows the execution lifecycle in
  `docs/spec/execution.md` Section 1 and returns an
  `ExecutionHandle`.
- `wait()` yields a DAG id on success.
- Success/failure record writes follow `docs/spec/object-model.md` Section 7.4.
- On failure, bindings raise a Python exception.
- Default behavior reuses exec pinned in active index commit.
- `cache=False` forces a new attempt.

Builtin execution triggered by literal lowering is synchronous and internal to
the bindings.

## 5. URI Helpers

- `dml.Uri("...")` constructs a boxed Python URI value from canonical URI text.
- `dml.Uri("...")` MUST reject non-canonical input with a Python exception.
- `dml.Uri.from_string(raw)` accepts raw text and canonicalizes to RFC 3986
  form before boxing.
- URI datum creation happens during `dag.literal(...)` lowering (Section 3),
  where boxed `dml.Uri` values are lowered as `DML_DATUM_URI` instead of
  `DML_DATUM_STRING`.
- Callers SHOULD use `dml.Uri.from_string(raw)` at input boundaries (CLI,
  files, network, user input) and `dml.Uri("...")` when canonical form is
  already guaranteed by program invariants.

## 6. Standard Library Builtin URIs

Collection builtins MUST use language-neutral names so core semantics are shared
across bindings. Python dunder behavior is a porcelain mapping layer built on
top of these operations.

Sequence (`seq`, ordered collection):

- `dml://seq/new`
- `dml://seq/len`
- `dml://seq/at`
- `dml://seq/slice`
- `dml://seq/concat`
- `dml://seq/insert_at`
- `dml://seq/remove_at`
- `dml://seq/contains`

Set (`set`, unique unordered collection):

- `dml://set/new`
- `dml://set/len`
- `dml://set/contains`
- `dml://set/add`
- `dml://set/remove`
- `dml://set/union`
- `dml://set/intersection`
- `dml://set/difference`
- `dml://set/symmetric_difference`
- `dml://set/is_subset`
- `dml://set/is_superset`

Map (`map`, key/value collection):

- `dml://map/new`
- `dml://map/len`
- `dml://map/get`
- `dml://map/contains_key`
- `dml://map/set`
- `dml://map/remove`
- `dml://map/merge`
- `dml://map/keys`
- `dml://map/values`
- `dml://map/items`
- `dml://map/project_keys`
- `dml://map/difference_keys`

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
