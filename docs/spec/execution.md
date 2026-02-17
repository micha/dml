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

## Terminology

- `Caller`: Client that requests execution (for example CLI or language
  bindings).
- `Executor`: Local DaggerML runtime responsible for call-node resolution,
  cache checks, adapter polling, result integration, and pin updates.
- `Execution Adapter`: Local adapter process invoked by the Executor.
- `Orchestrator`: Control-plane service that handles idempotent claim, submit,
  and polling for an execution attempt.
- `Worker Backend`: Compute system where jobs actually run (for example AWS
  Batch).
- `Repository Remote`: Remote DaggerML repository used for snapshots and result
  integration.
- `Execution Token`: Opaque continuation token returned by an Execution Adapter
  while work is pending.
- `Execution Attempt`: One logical run for a call node that can produce one
  `DML_REC_EXEC`.
- `Execution Key`: Deterministic idempotency key used by Orchestrator claim
  logic.

## 1. Execution Lifecycle

Applies to `DML_NODE_CALL` nodes.

1. A call node is created with deterministic identity from function ref + input
   node ids.
2. The Executor checks the active index commit exec map for `node_id`.
3. If an exec is pinned, return completed result without new execution.
4. Otherwise create or resume an `Execution Attempt` and invoke the
   `Execution Adapter` with optional prior `Execution Token`.
5. If the adapter reports `pending`, persist the newest `Execution Token` and
   poll again.
6. If the adapter reports `done`, fetch required result objects from the
   `Repository Remote` and validate result availability.
7. On success write an exec record per `docs/spec/object-model.md` Section 7.4
   (`status=OK`, call result as DAG id).
8. On failure write an exec record per `docs/spec/object-model.md` Section 7.4
   (`status=ERROR`, failure-result DAG id).
9. Commit pins accepted exec id in its exec map.

No `DML_REC_EXEC` is written while a call is pending.

### 1.1 Local Executor state machine

The `Executor` state machine is:

- `resolve_call_node`
  - The Executor MUST build or resolve deterministic `node_id` for the call.
  - If the active index commit already pins `node_id`, transition to
    `pinned_hit`.
  - Otherwise transition to `poll_adapter`.
- `poll_adapter`
  - The Executor MUST invoke `Execution Adapter` with call context and an
    optional prior `Execution Token`.
  - `pending(token)` -> Executor MUST persist newest token and remain in
    `poll_adapter`.
  - `done(ok, result)` -> transition to `integrate_ok`.
  - `done(error, result)` -> transition to `integrate_error`.
  - transient failure -> transition to `retry_wait`.
  - non-retryable failure -> transition to `failed_terminal`.
- `integrate_ok`
  - The Executor MUST fetch required result objects from `Repository Remote`.
  - The Executor MUST validate availability of the terminal result DAG.
  - The Executor MUST write `DML_REC_EXEC(status=OK)` and MUST atomically pin
    the accepted exec id.
  - success -> `completed_ok`; retryable integration failure -> `retry_wait`.
- `integrate_error`
  - The Executor MUST fetch required failure-result DAG objects from
    `Repository Remote`.
  - The Executor MUST validate availability of the terminal failure-result DAG.
  - The Executor MUST write `DML_REC_EXEC(status=ERROR)` and MUST atomically
    pin the accepted exec id.
  - success -> `completed_error`; retryable integration failure -> `retry_wait`.
- `retry_wait`
  - The Executor SHOULD apply backoff and retry budget policy.
  - Resume at last safe state (`poll_adapter`, `integrate_ok`, or
    `integrate_error`).
  - If retry budget is exhausted, transition to `failed_terminal`.

Terminal states:

- `pinned_hit`
- `completed_ok`
- `completed_error`
- `failed_terminal`

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
    objects/refs and return `done(ok, result)`.
  - If job fails, the Orchestrator MUST publish terminal failure-result DAG
    objects/refs and return `done(error, result)`.

Terminal outcomes exposed through adapter responses:

- `done(ok, result)`
- `done(error, result)`

### 1.3 Idempotent claim model

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

## 2. Call Result Semantics

- `DML_NODE_CALL` success result follows `docs/spec/object-model.md` Section
  7.4.
- `DML_NODE_CALL` failure result also follows `docs/spec/object-model.md`
  Section 7.4 as a DAG whose root node encodes failure details.
- The returned value is that DAG's `root_node`.
- Tooling MAY add a convenience name `root`, but correctness MUST NOT depend on
  it.

## 3. Caching and Retries

- Cache key is `node_id` (pure, content-addressed by inputs).
- Cache source for active work is the index commit exec map.
- Multiple exec records MAY exist per node id.
- Retries MUST append new exec records and MUST NOT overwrite prior records.
- `cache=False` semantics MAY force a new execution attempt.
- A `done` result from adapter polling MUST NOT be surfaced as completed until
  integration and pin update succeed.

## 4. In-Flight State

- Canonical packed records do not currently persist pending state.
- Pending state is tracked by `Execution Attempt` metadata and/or adapter
  tokens managed by the Executor.
- Tooling MAY maintain a derived, rebuildable in-flight index under separate
  prefixes.
- Local in-memory in-flight deduplication is an optimization and is not
  required for correctness.

## 5. Execution Adapter Contract

Adapter URI scheme:

- Execution adapter: `dml+exec://<adapter>/<path>?<query>`

`<adapter>` resolves to an executable on `$PATH`.

- The `Execution Adapter` is a stateless CLI.
- Inputs include: call node id, function URI, input node ids, snapshot
  ref/remote URI, execution UUID, and optional prior token.
- Adapter returns either:
  - `pending` + opaque token, or
  - `done` + terminal result id.
- For `CALL`, terminal result id MUST be a DAG id for both success and failure.
- The Executor persists the newest token and polls until done.
- The adapter MUST NOT write `DML_REC_EXEC` directly; the Executor owns exec
  writes.
- The adapter response token MUST be treated as opaque by the Executor.

## 6. Open Questions

1. Should pending execution state move into canonical records?
2. Where should `DML_REC_EXEC_REQUEST` live in keyspace?
3. What is the deterministic tree placement for execution-result DAGs?
