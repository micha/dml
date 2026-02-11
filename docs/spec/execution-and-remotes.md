# Execution and Remotes Specification

Status: Draft.

This document defines async execution behavior, execution caching/pinning, remote
exchange mechanics, and adapter contracts for packed-record repositories.

## 1. Execution Lifecycle

Applies to `DML_NODE_CALL` nodes.

1. A call node is created with deterministic identity from function ref + input
   node ids.
2. Executor checks the active index commit exec map for `node_id`.
3. If an exec is pinned, return completed result without new execution.
4. If execution is already in flight for `node_id`, attach caller to that
   in-flight attempt.
5. Otherwise enqueue a new attempt and poll adapter until completion.
6. On success write `DML_REC_EXEC(status=OK, result_value=<dag_id>)`.
7. On failure write `DML_REC_EXEC(status=ERROR, error_value=<datum_id>)`.
8. Commit pins accepted exec id in its exec map.

No `DML_REC_EXEC` is written while a call is pending.

## 2. Call Result Semantics

- `DML_NODE_CALL` success result is a DAG id in `DML_REC_EXEC.result_value`.
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

## 5. Remote Execution Snapshot Protocol

For external execution against a remote:

1. Create snapshot ref `refs/exec/<uuid>` at current index commit.
2. Push snapshot ref and missing objects to execution remote.
3. Remote executes against that snapshot and writes resulting DAG + exec records.
4. Remote fast-forwards `refs/exec/<uuid>` to result commit parented on snapshot.
5. Local fetches `refs/exec/<uuid>`, imports objects, and pins chosen exec in
   local index commit.
6. Exec refs are ephemeral and MAY be pruned after integration.

Local execution SHOULD follow the same protocol via `file://` remotes.

## 6. Remote Refs and Transfer

### 6.1 Ref model

- Remote tracking refs: `refs/remotes/<remote>/<name>`.
- Remote refs are read-only snapshots maintained by fetch/pull.
- Local writable heads remain under `refs/heads/*`.

### 6.2 Transfer model

- Transfer payload is a stream of length-prefixed packed records plus manifest.
- Receiver applies records atomically.
- Checksums SHOULD be enabled for transfer corruption detection.

### 6.3 Fetch/pull

- Resolve selected remote refs.
- Transfer missing reachable objects.
- Update `refs/remotes/<remote>/...` in one transaction.

### 6.4 Push

- Transfer missing local objects required by target refs.
- Update remote refs atomically.
- Non-fast-forward updates MUST be rejected by default.

## 7. Serverless S3 Remotes

Serverless remotes MAY be implemented with immutable segment objects and
per-ref manifests.

Minimal manifest shape:

```json
{
  "schema": 1,
  "ref": "refs/heads/main",
  "base_commit": "<commit_id>",
  "segments": [
    {"key": "objects/seg-20260207-0001.bin", "format": "packed-bin"}
  ]
}
```

Binary segment format:

- `u32_le length` + `length` packed-record bytes, repeated.
- Segments are immutable; appends create new segments.

Atomicity model:

- Ref pointer stores manifest key.
- Push uploads segments and manifest, then updates ref pointer via conditional
  write (`ETag`/`If-Match`) to enforce fast-forward behavior.

## 8. Adapter Contracts

Adapter URI schemes:

- Execution adapter: `dml+exec://<adapter>/<path>?<query>`
- Remote adapter: `dml+remote://<adapter>/<path>?<query>`

`<adapter>` resolves to an executable on `$PATH`.

### 8.1 Execution adapter protocol

- Adapter is a stateless CLI.
- Inputs include: call node id, function URI, input node ids, snapshot
  ref/remote URI, execution UUID, and optional prior token.
- Adapter returns either:
  - `pending` + opaque token, or
  - `done` + result DAG id / error datum id.
- Executor persists newest token and polls until done.
- Adapter MUST NOT write `DML_REC_EXEC` directly; executor owns exec writes.

### 8.2 Remote adapter protocol

- `list-refs --remote <uri>`
- `get-manifest --remote <uri> --ref <ref>` (optional outside manifest-based)
- `get-object --remote <uri> --id <id>`
- `put-object --remote <uri> --id <id>`
- `update-refs --remote <uri> --refs <r=t,...> --expect <r=old,...>`

Core computes reachability and missing objects; adapters are IO-only.

## 9. Open Questions

1. Should pending execution state move into canonical records?
2. Where should `DML_REC_EXEC_REQUEST` live in keyspace?
3. What is the deterministic tree placement for execution-result DAGs?
