# Execution Specification

Status: Draft.

This document defines async execution behavior, execution caching/pinning,
retry semantics, in-flight policy, and execution adapter contracts.

Authority boundary:

- This document is authoritative for execution lifecycle, call result
  semantics, cache/retry behavior, in-flight policy, and execution adapter
  contracts.
- For packed-record schemas, canonical encoding/hashing, keyspace, and
  validation/error semantics, see `docs/spec/object-model.md`.
- For remote execution snapshot exchange and remote transfer semantics, see
  `docs/spec/remotes.md`.
- For CLI command contracts, see `docs/spec/cli.md`.
- For Python API surface and binding behavior, see
  `docs/spec/python-bindings.md`.

## 1. Execution Lifecycle

Applies to `DML_NODE_CALL` nodes.

1. A call node is created with deterministic identity from function ref + input
   node ids.
2. Executor checks the active index commit exec map for `node_id`.
3. If an exec is pinned, return completed result without new execution.
4. If execution is already in flight for `node_id`, attach caller to that
   in-flight attempt.
5. Otherwise enqueue a new attempt and poll adapter until completion.
6. On success write an exec record per `docs/spec/object-model.md` Section 7.4
   (`status=OK`, call result as DAG id).
7. On failure write an exec record per `docs/spec/object-model.md` Section 7.4
   (`status=ERROR`, error datum id).
8. Commit pins accepted exec id in its exec map.

No `DML_REC_EXEC` is written while a call is pending.

## 2. Call Result Semantics

- `DML_NODE_CALL` success result follows `docs/spec/object-model.md` Section
  7.4.
- The returned value is that DAG's `root_node`.
- Tooling MAY add a convenience name `root`, but correctness MUST NOT depend on
  it.

## 3. Caching and Retries

- Cache key is `node_id` (pure, content-addressed by inputs).
- Cache source for active work is the index commit exec map.
- Multiple exec records MAY exist per node id.
- Retries MUST append new exec records and MUST NOT overwrite prior records.
- `cache=False` semantics MAY force a new execution attempt.

## 4. In-Flight State

- Canonical packed records do not currently persist pending state.
- Pending state is tracked by executor runtime.
- Tooling MAY maintain a derived, rebuildable in-flight index under separate
  prefixes.

## 5. Execution Adapter Contract

Adapter URI scheme:

- Execution adapter: `dml+exec://<adapter>/<path>?<query>`

`<adapter>` resolves to an executable on `$PATH`.

- Adapter is a stateless CLI.
- Inputs include: call node id, function URI, input node ids, snapshot
  ref/remote URI, execution UUID, and optional prior token.
- Adapter returns either:
  - `pending` + opaque token, or
  - `done` + result DAG id / error datum id.
- Executor persists newest token and polls until done.
- Adapter MUST NOT write `DML_REC_EXEC` directly; executor owns exec writes.

## 6. Open Questions

1. Should pending execution state move into canonical records?
2. Where should `DML_REC_EXEC_REQUEST` live in keyspace?
3. What is the deterministic tree placement for execution-result DAGs?
