# Remotes Specification

Status: Draft.

This document defines remote execution snapshot exchange mechanics,
remote ref/transfer behavior, and remote adapter contracts for
packed-record repositories.

Authority boundary:

- This document is authoritative for remote execution snapshot flow,
  remote ref model, transfer mechanics, and remote adapter contracts.
- For packed-record schemas, canonical encoding/hashing, keyspace, and
  validation/error semantics, see `docs/spec/object-model.md`.
- For execution lifecycle, cache/retry behavior, in-flight policy, and
  execution adapter contracts, see `docs/spec/execution.md`.
- For CLI command contracts, see `docs/spec/cli.md`.
- For Python API surface and binding behavior, see
  `docs/spec/python-bindings.md`.

## 1. Remote Execution Snapshot Protocol

For external execution against a remote:

1. Create snapshot ref `refs/exec/<uuid>` at current index commit.
2. Push snapshot ref and missing objects to execution remote.
3. Remote executes against that snapshot and writes resulting DAG + exec records.
4. Remote fast-forwards `refs/exec/<uuid>` to result commit parented on
   snapshot.
5. Local fetches `refs/exec/<uuid>`, imports objects, and pins chosen exec in
   local index commit.
6. Exec refs are ephemeral and MAY be pruned after integration.

Local execution SHOULD follow the same protocol via `file://` remotes.

## 2. Remote Refs and Transfer

### 2.1 Ref model

- Remote tracking refs: `refs/remotes/<remote>/<name>`.
- Remote refs are read-only snapshots maintained by fetch/pull.
- Local writable heads remain under `refs/heads/*`.

### 2.2 Transfer model

- Transfer payload is a stream of length-prefixed packed records plus manifest.
- Receiver applies records atomically.
- Checksums SHOULD be enabled for transfer corruption detection.

### 2.3 Fetch/pull

- Resolve selected remote refs.
- Transfer missing reachable objects.
- Update `refs/remotes/<remote>/...` in one transaction.

### 2.4 Push

- Transfer missing local objects required by target refs.
- Update remote refs atomically.
- Non-fast-forward updates MUST be rejected by default.

## 3. Serverless S3 Remotes

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

## 4. Remote Adapter Contract

Adapter URI scheme:

- Remote adapter: `dml+remote://<adapter>/<path>?<query>`

`<adapter>` resolves to an executable on `$PATH`.

- `list-refs --remote <uri>`
- `get-manifest --remote <uri> --ref <ref>` (optional outside manifest-based)
- `get-object --remote <uri> --id <id>`
- `put-object --remote <uri> --id <id>`
- `update-refs --remote <uri> --refs <r=t,...> --expect <r=old,...>`

Core computes reachability and missing objects; adapters are IO-only.
