# Local recorded Python execution

Status: implemented by the explicitly imported `daggerml.local` layer.

## Authority boundary

This document owns this layer's Python API, ordinary-DAG role/ref conventions,
cooperative child contract, publication protocol and outcome/capture limits.
[Python API](python-api.md) owns low-level values, storage contexts and native
lifetime. [Objects](objects.md) and [repository](repository.md) own encoding,
name profiles, direct validation and storage transactions. [CLI](cli.md) owns
ordinary inspection. These roles are document-local conventions, not core kinds,
globally reserved names or permissions. Vocabulary follows the [glossary](glossary.md).

Normative sections describe the implemented synchronous local adapter. The additive
[caller-request contract](caller-requests.md) owns public `put_local_request` and
`run_request`, request-only recording and imported-Q first registration. They reuse
this document's unchanged ordinary roles, child checks and execution/finalization.

## Public surface

```python
from daggerml.local import (
    put_local_binding, run_step, retry_step, child_context, publish_result,
    LocalContext, LocalRun, LocalExecutionError, ProtocolError, ConflictError,
)

put_local_binding(tx, *, source: bytes, interpreter: str, timeout_ms: int) -> ObjectId
run_step(repository_path, *, head_ref: str, intent_uri: str,
         binding: ObjectId, inputs: ObjectId, scratch_dir=None) -> LocalRun
retry_step(repository_path, *, head_ref: str, request: ObjectId,
           scratch_dir=None) -> LocalRun
child_context(argv=None) -> LocalContext
publish_result(tx, context: LocalContext, result: ObjectId) -> ObjectId
```

`put_local_binding` inserts through the caller's existing write transaction. It
requires exact bytes/str/int types, 1–1,048,576 source bytes, an absolute interpreter
path without NUL and timeout 1–3,600,000 milliseconds. It does not check that the
executable exists or that the bytes are valid Python; launch/child failures remain
recorded outcomes. URI datums use the existing native validation, not normalization.

`run_step` requires an existing repository and explicitly supplied coordination head.
Binding/inputs require `ObjectId`; inputs are a supplied named DAG, not converted
Python values. The layer validates its own consumed fields and types, not a generic
argument schema. Repository/scratch paths accept filesystem path-like values, become
absolute UTF-8 paths and reject empty/NUL/unencodable paths. `scratch_dir` selects an
existing parent for newly allocated scratch; default is the stdlib temporary location.
Neither historical scratch strings nor caller directories are deletion targets.
Recorded interpreter and allocated scratch paths MUST already be NFC, because native
STRING datums normalize NFC. The layer rejects non-NFC spellings instead of silently
retargeting filesystem paths; a rejected allocated scratch is cleaned before any
pre-dispatch publication. This narrow path restriction does not change the low-level
repository path API.

A fresh invocation creates a new request and attempt and launches once. `retry_step`
requires an exact reserved request DAG; it selects that request's original binding
and inputs and creates only a new attempt. Changing source/configuration requires
a new binding/request. There is no implicit retry, old-attempt dispatch or result
reuse. Callers MUST close their repository handles before invoking drivers;
the low-level single-wrapper policy remains unchanged.

Frozen `LocalContext` owns `repository_path`, `pre_dispatch`, request/attempt
occurrence strings (`request_id`, `attempt_id`), request/initial-attempt DAG IDs
(`request`, `attempt`), `publication_ref`, `binding`, `inputs` and `scratch`.
Frozen `LocalRun` owns that `context`, `final_commit`, `final_attempt`, `outcome`
(`success` or `failure`), optional `result`/`evidence`, and `cleanup` (`ok` or
`failed`). Its `request_id` and `attempt_id` properties forward occurrence strings.
No returned description retains a live handle.

Recorded computational failure returns `LocalRun`, not an exception. Validation,
coordination, IO/reaping or persistence errors raise; `LocalExecutionError.occurrence`
is the committed initial context when available, otherwise `None`. Its chained
cause retains the underlying exception. The error does not claim a final outcome.
Pre-allocation argument/temp-directory errors can propagate directly. Malformed
roles raise `ProtocolError`; unexpected head/ref movement raises `ConflictError`
at the child helper or as the driver's chained cause. Native low-level errors keep
their existing semantics. Helper validation is not a new mutation-poison policy;
child code SHOULD let publication errors abort its whole write context.

## Ordinary records

Every scalar field is a literal node; DAG fields are sub-DAG-reference nodes.
Role-rooted DAGs bind `role` to that same root node. Occurrence-rooted DAGs have a
STRING occurrence as root and a separate `role` field. Only exact field sets for
binding, request, initial attempt and publication are accepted by consumed-role
readers; this is not a schema registry.

| Record | Root | Named fields |
| --- | --- | --- |
| Binding | `local-python-binding-v1` STRING | `role`, `source` BYTES, `adapter` URI `urn:daggerml:local-python-v1`, `interpreter` STRING, `timeout-ms` I64 |
| Request | `q-` + UUID4 lowercase 32-hex STRING | `role` STRING `local-request-v1`, `intent` URI, `binding` DAG, `inputs` DAG |
| Initial attempt | `a-` + UUID4 lowercase 32-hex STRING | `role` STRING `local-attempt-v1`, `request` DAG, `publication-ref` STRING, `scratch` absolute STRING |
| Final attempt description | Same attempt occurrence STRING | Initial fields plus `status` STRING `done`, `outcome` DAG, `cleanup` DAG |
| Publication | Same attempt occurrence STRING | `role` STRING `local-publication-v1`, `result` DAG |
| Success | `local-success-v1` STRING | `role`, `exit-code` I64 0, `result` DAG, available `stdout`/`stderr` diagnostic DAGs |
| Failure | `local-failure-v1` STRING | `role`, `exit-code` I64 or NULL, `reason`/`detail` STRING, optional `evidence` DAG, available diagnostic DAGs |
| Cleanup | `local-cleanup-v1` STRING | `role`, `disposition` STRING `ok`/`failed`, `detail` STRING; failed cleanup adds `scratch` STRING |
| Diagnostic | Retained BYTES | `byte-count` I64, `truncated` BOOL |

Occurrence identifiers are distinct from content IDs. Role-qualified UUID4 payloads
are checked by repository reservation conventions, not a global uniqueness proof.
Final descriptions create new DAG content IDs without changing occurrence identity.
Result content contains whatever the child constructs; the layer does not inject
occurrence identifiers into results. Matching attempts can have identical result IDs.

An initial attempt deliberately has no `status` or `outcome`. Missing final outcome
is **unknown**, not failure, not proof of dispatch and not proof that no result was
published. `done` means computation and cleanup disposition were persisted, not
computational success. Valid publication after parent loss remains separately
inspectable evidence without automatic finalization.

## Atomic history and publication

The caller owns one coordination head. Tree names and ordinary ref names are
`request-<request-id>` and `attempt-<attempt-id>`; the child publication tree entry
is `publication-<attempt-id>`. These satisfy the core ASCII profile.

1. For `run_step`/`retry_step`, the driver allocates its own scratch and generates occurrence identifiers. One
   write storage transaction creates request/initial attempt, preserves unrelated
   head-tree entries, creates a pre-dispatch DML commit with the previous head as
   parent, moves the head, creates a request reservation ref (fresh requests only)
   and creates the attempt publication ref pointing to that commit. Preparation
   retries at most three ID pairs when a ref/tree-name collision is observed;
   other write/commit failures abort and do not dispatch.
2. Parent transactions and handles are closed before launching/waiting. The driver
   reopens briefly to read captured binding bytes, then closes again before launch.
3. Four positional child arguments are absolute repository path, exact pre-dispatch
   commit hex ID, attempt occurrence and publication ref. `child_context` reads that
   snapshot, not the moving coordination head. It checks the initial attempt, exact
   request association, binding/inputs and reservation snapshot's exact request DAG.
4. Child code owns a separate repository/write transaction, reads pinned named inputs
   and constructs result objects. `publish_result` revalidates the context against
   the snapshot, requires the attempt ref still point at pre-dispatch, rejects an
   existing publication entry, and creates publication DAG/tree/commit with exactly
   pre-dispatch as parent. It updates only the attempt ref in the same transaction.
   The helper returns the DML commit ID; the caller MUST successfully commit the
   storage transaction. Bare objects, stdout or an aborted batch are not publication.
5. After direct-child disposition is established, the driver attempts scratch cleanup.
   Completion uses a fresh write transaction. It requires the head still point at
   pre-dispatch, revalidates the initial context and reads the attempt ref. A moved
   target is accepted only if its single parent is pre-dispatch, its tree is exactly
   the preserved starting tree plus the one expected publication entry, and that
   entry has the proper role/attempt association and a typed result DAG.
6. Completion replaces only this attempt's tree entry with the final description.
   Accepted publication is retained; completion parents are pre-dispatch followed
   by publication. Without accepted publication only pre-dispatch is a parent.
   The head moves atomically with final records. This explicit tree construction
   and ordered history join is not a general merge operation.

Reservation refs are not moved by this layer after creation. A retry checks its
reservation and does not overwrite a different request description at the head.
Neither helper nor driver overwrites an unexpected attempt-ref target. Invalid
publication remains rooted at that ref, but is not adopted as result/evidence.
Moved/missing/corrupt heads or unreadable refs can raise instead of finalizing.
Final write/commit failure leaves initial and child history inspectable and raises,
not a recorded failure or `done` response. Conditional checks inside LMDB write
transactions are bounded cooperative conventions, not a multi-driver coordinator.

Result-DAG validation follows the existing **direct**, not recursive, read contract.
The layer does not certify child methodology, undeclared inputs or a corrupted
repository's transitive integrity.

## Process boundary, observations and cleanup

The driver writes exactly the captured entry bytes to its newly allocated scratch,
uses scratch as cwd and launches `[interpreter, entry, ...contract_args]` with no
shell, inherited environment, DEVNULL stdin and binary file-backed stdout/stderr.
Spaces in paths are ordinary arguments, not shell quoting. No test import/fault
hooks or runtime installation/bootstrap are shipped in the runner.

`Popen.wait` has the binding timeout. On expiry the driver terminates the direct
child and waits up to five seconds; if necessary it kills and waits up to five more.
A failure to establish child disposition raises with an unknown final outcome;
it does not fabricate `done`. Exception handling also attempts direct-child cleanup
when the wait fails. Process creation itself is not portably interruptible by this
timeout. No process-tree termination guarantee is made.

Success requires zero exit **and** accepted durable publication. Failure reasons
are `launch`, `child-exit`, `timeout`, `missing-publication` and
`invalid-publication`. Process failure/timeout takes precedence over publication
classification. A valid published DAG after nonzero exit/timeout is retained as
`evidence`, with its publication parent, not substituted for success. Setup/spawn
failure has no fabricated stream observations. Post-launch IO/reaping failures
raise with unknown outcome rather than being called launch failure.

Each available diagnostic retains at most 4,096 bytes plus file byte count and
truncation. Non-UTF8/control bytes remain BYTES, safe for existing bounded CLI
previews. Detail strings retain at most 4,096 UTF-8 bytes. These are persisted
snippet limits, **not** limits on scratch-disk growth, repository/result size,
child memory or descendant output. Descendants can continue writing after direct
child exit, so counts describe the observation, not guaranteed ultimate output.

Cleanup removes only the directory allocated by this invocation. Ordinary removal
failure records separate `failed` cleanup and the remaining scratch path without
reclassifying a successful computation. Hard parent interruption can leave scratch
or a child behind. Fixture cleanup is not a production recovery service; historical
scratch strings are never followed as deletion authority by retry.

## Trust and capture limits

Only deliberately supplied **trusted** Python source is supported. This is not a
sandbox: the child has local-user authority, repository write access and inherited
environment, and can ignore the cooperative contract. Entry bytes are captured;
imports, interpreter/DML binaries, environment, files, services and full dependency
closure are not. Interpreter path and adapter URI record declared mechanics, not
immutable runtime identity. Inspection alone never launches source. Stored source
and diagnostics can contain sensitive content; the caller owns recording policy.
These records do not establish complete reproducibility, scientific validity or
exactly-once external execution.

## Informative example and evidence

With a current installed runtime and console, from outside the checkout:

```sh
python /path/to/dml/examples/local_execution.py /fresh/parent/execution.dml
dml --json --repo /fresh/parent/execution.dml snapshot --ref main
dml --json --repo /fresh/parent/execution.dml log --ref main
# Use IDs printed by the example:
dml --json --repo /fresh/parent/execution.dml walk <final-attempt> --limit 100
dml --json --repo /fresh/parent/execution.dml snapshot --commit <pre-dispatch>
```

The [driver](../../examples/local_execution.py) records two fresh additions of
4/7, equal results rooted in 11, a new failing binding/request and an explicit
retry. [Child source](../../examples/local_add.py) performs arithmetic in Python
and explicitly publishes its DAG through the public API.

Evidence: [layer](../../python/daggerml/daggerml/local.py),
[acceptance](../../tests/python/test_local_execution.py),
[failure/interruption tests](../../tests/python/test_local_failures.py) and
[malformed-role/storage tests](../../tests/python/test_local_records.py).
Actual checks, measured versus installed subprocess populations and platform limits
belong to [Iteration 4 results](../../../dml-design/iterations/04-local-recorded-execution/RESULTS.md).
