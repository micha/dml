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

## Terminology

- `Executor`: Local DaggerML runtime that invokes an `Execution Adapter` and
  integrates terminal results.
- `Execution Adapter`: Local adapter process invoked by the Executor.
- `Orchestrator`: Remote control-plane service handling idempotent claim,
  submit, and polling logic.
- `Worker Backend`: Remote compute system where jobs run (for example AWS
  Batch).
- `Repository Remote`: Remote DaggerML repository used for snapshot and result
  exchange.
- `Execution Key`: Deterministic idempotency key used by an Orchestrator claim
  namespace.
- `Execution Token`: Opaque continuation token passed between Executor and
  adapter while work is pending.

## 1. Remote Execution Snapshot Protocol

For external execution against a remote:

1. The Executor creates snapshot ref `refs/exec/<uuid>` at current index
   commit.
2. The Executor pushes snapshot ref and missing objects to the
   `Repository Remote`.
3. The Orchestrator executes against that snapshot using a `Worker Backend` and
   writes resulting DAG + exec records.
4. The Orchestrator fast-forwards `refs/exec/<uuid>` to result commit parented
   on snapshot.
5. The Executor fetches `refs/exec/<uuid>`, imports objects, and pins chosen
   exec in local index commit.
6. Exec refs are ephemeral and MAY be pruned after integration.

Local execution SHOULD follow the same protocol via `file://` remotes.

### 1.1 Idempotent claim model

- Orchestrators SHOULD implement idempotent submit using a durable
  `Execution Key` claim boundary.
- A repository-backed claim namespace MAY be used (for example
  `refs/exec-claims/<execution_key>`), with atomic compare-and-swap updates.
- Claim contention MUST be scoped to a per-key claim ref and MUST NOT require
  global ref quiescence.
- Claim records SHOULD include lease metadata so stale owners can be detected
  and safely taken over.
- If a lease-based takeover policy is used, takeover MUST use an atomic
  compare-and-swap update on the claim ref.

### 1.2 Remote Orchestrator state machine

The `Orchestrator` state machine is:

- `lookup_claim`
  - The Orchestrator MUST resolve claim state for `Execution Key`.
  - If no claim exists, attempt atomic claim create and transition to
    `claimed_owner` on success.
  - If a claim exists, transition to `follow_existing`.
- `claimed_owner`
  - The Orchestrator MUST perform idempotent submit to `Worker Backend`.
  - The Orchestrator MUST persist backend job identity and lease metadata.
  - Transition to `job_pending`.
- `follow_existing`
  - The Orchestrator MUST reuse existing claim/job identity for this
    `Execution Key`.
  - If lease is active, transition to `job_pending`.
  - If lease is stale and takeover policy permits, atomically claim takeover and
    transition to `claimed_owner`.
- `job_pending`
  - The Orchestrator MUST poll `Worker Backend` status and refresh lease
    metadata.
  - If job is still queued/running, return `pending(token)` to the
    `Execution Adapter`.
  - If job succeeds, the Orchestrator MUST publish terminal result
    objects/refs and return
    `done(ok, result)`.
  - If job fails, the Orchestrator MUST publish terminal failure payload and
    return
    `done(error, result)`.

Terminal outcomes exposed through adapter responses:

- `done(ok, result)`
- `done(error, result)`

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
- Core computes reachability and missing objects; adapters are IO-only.
- Remote adapters MUST NOT perform reachability decisions or policy-level
  conflict resolution.
