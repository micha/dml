# Caller-recorded local requests

Status: implemented by explicitly imported `daggerml.local` and `daggerml.exchange`.

## Authority boundary

This document owns request-only construction, explicit atomic caller recording,
imported submission first registration and the pinned-Q selection delta in both
exchange return paths. [Local execution](local-execution.md) owns ordinary role bytes,
execution/publication/finalization and capture/cleanup limits. [Repository execution](repository-execution.md)
owns workspace framing, synchronous exchange and completed-history checks;
[asynchronous execution](asynchronous-execution.md) owns saved handles/live owners,
coherent discovery and immutable P/U/F packets. [Transfer](transfer.md) owns full
all-parent typed closure and atomic import. [Python API](python-api.md) owns handles;
[repository](repository.md) owns storage transactions. Terms follow the [glossary](glossary.md).
Normative sections describe implemented behavior; the example is informative.

## Public operations and owned description

```python
from daggerml.local import put_local_request, run_request
from daggerml.exchange import record_exchange_request, RecordedRequest

put_local_request(tx, *, request_id: str, intent_uri: str,
                  binding: ObjectId, inputs: ObjectId) -> ObjectId
run_request(repository_path, *, head_ref: str, request_commit: ObjectId,
            request: ObjectId, scratch_dir=None) -> LocalRun
record_exchange_request(repository_path, *, commit: ObjectId,
                        binding_name: str, inputs_name: str, intent_uri: str,
                        ref: str, map_size: int = 0) -> RecordedRequest
# Existing prepare adds optional request=None:
prepare_exchange(repository_path, *, commit, binding_name, inputs_name,
                 intent_uri, worker_ref, workspace, request=None) -> ExchangeSpec
```

The local builder requires the existing `q-` lowercase 32-hex occurrence profile,
exact intent string and ObjectId binding/inputs, validated consumed binding fields
and typed input DAG. Native URI validation requires canonical absolute intent.
It inserts only the existing ordinary request shape through the supplied transaction.
It MUST NOT generate refs, allocate scratch, launch or commit the transaction.
It does not enforce global or repository-wide occurrence uniqueness; re-building
identical content can deduplicate. The transaction caller owns publication/abort.

Frozen `RecordedRequest` owns `base`, submission `commit`, caller `ref`, `request`,
`request_id`, `binding_name`, `inputs_name`, `binding`, `inputs` and `intent_uri`.
It retains no native handle, workspace, correlation token or process. Recording
validates names, canonical URI, explicit commit and existing exchange map-size
profile. It closes its handles and returns only after the storage transaction commits.
All driver calls retain the low-level single-wrapper policy: close other handles first.

## Atomic explicit recording in A

Recording is a deliberate A mutation, separate from preparation/start:

1. In one write transaction, read immutable basis C and resolve the selected tree
   names. Require the explicit submission ref absent; never move an existing head.
2. Generate `q-` UUID hex; bound collision checks to three transactions. Existing
   request reservation or canonical tree name causes retry; exhaustion raises.
   A submission ref identical to its generated request ref rejects. Malformed/dangling
   keys MUST NOT be repaired: unreadable refs error, or native create rejects the
   existing key even when a dangling target read reported not-found.
3. Use public `local.put_local_request`. Cq has exactly `(C,)` parents and exactly
   C's tree plus `request-<qid> -> Q`.
4. Create both caller submission ref and A-local `request-<qid>` reservation at Cq.
   Prebuild the owned response before committing the entire Q/Cq/two-ref batch.

There is no T, dispatch, scratch, publication, computational outcome or cleanup
record. Other refs/old immutable bytes remain unchanged. Late ref, map-full,
allocation or consuming-commit errors abort the batch. Map growth/retry is never
automatic. The reservation is a local association convention, not a transferable
permission or globally unique capability.

Loss before commit leaves no batch; loss after commit before response can leave the
complete submission despite no description. Inspect the explicit ref; MUST NOT
infer failure or automatically record another Q. Re-recording under an existing
submission ref rejects, not idempotent request creation. Later export/prepare/file
failure leaves already-recorded Q/Cq retained. Files and repository commits are not
one transaction; there is no filesystem/power-loss guarantee.

## Pinned submission and first registration in B

Caller-origin `prepare_exchange(request=Q, commit=Cq)` reads without A writes.
Cq MUST have exactly one parent C, preserve C's complete tree and add only Q's
canonical name, absent in C. Exact Q occurrence/root/role/types, intent and selected
named binding/inputs MUST match. An arbitrary snapshot containing historical Q is
not a submission. Copied Cq need not have operational reservation refs for inspection
or preparation. Transfer alone creates neither reservation nor execution permission.

Execute uses the fixed existing worker/public execute invocation. After import,
selection/ref validation and handle closure it publishes readiness, then calls
public `local.run_request`, not private local helpers or `retry_step`.

`run_request` owns one atomic pre-dispatch transaction:

- Current head MUST equal supplied Cq. Validate exact submission/Q with local-owned
  readers; Q's binding/inputs must be present in C's tree values.
- B-local Q reservation MUST be absent. Same-target, different, malformed and dangling
  existing keys reject; this is first registration, not repair or retry.
- Generate only fresh `a-` occurrence, bounded to three attempt collision checks.
- Preserve all Cq entries including exact Q. Add only initial T under its attempt name;
  P has `(Cq,)` parents. Atomically move the explicit worker head to P, create Q
  reservation at Cq and attempt publication ref at P.

No computational launch precedes successful commit. Handles close before child
work. Failed registration leaves imported Q/Cq and no partial T/P/ref/head batch.
After successful registration the existing child reservation check, publication,
reaping, cleanup and finalization operate unchanged. P can survive loss before
actual spawn: T then remains unknown, not proof of dispatch or failure.

Already reserved A requests do not qualify for this operation. An imported Q without
reservation still fails existing `retry_step`. Existing `run_step` creates fresh Q/T;
explicit local retry preserves its previous semantics. A second first registration
in the same B rejects even if its head is deliberately reset. Fresh repositories can
copy Q and explicitly request other attempts; there is **no global exactly-once**,
automatic replay, abandoned-request recovery, cancellation or distributed authority.

## Exact Q through synchronous and asynchronous return

`ExchangeSpec.request` is a required-framing nullable field: API default `None`
preserves original fresh-Q-in-B behavior; ObjectId pins caller Q along with Cq.
Job format is `daggerml-local-exchange-job-v2`; saved-handle format is
`daggerml-local-exchange-handle-v2`. Job/embedded expected includes exact `request`
(JSON null or lowercase 32-hex). Unknown/missing/wrong-type fields reject; no old-file
migration or compatibility mode is provided. Other receipts retain their existing
formats and independently matched token/base claims; tokens are not authentication.

Both return validators share the mode-specific initial-history check:

| Mode | P parents and tree | Discovery |
| --- | --- | --- |
| `request=None` | `(C,)`; C plus exactly fresh Q/T | One fresh request and attempt name relative to C |
| `request=Q` | `(Cq,)`; exact Cq plus only fresh T | Derive Q from expected validated Cq/Q, then one fresh attempt name |

In caller mode T MUST reference exact Q, not another matching computation. Q must
remain byte-identical in every P/U/F tree. Prior unrelated Q/T/publication entries
in C remain preserved. U/F exact tree/ordered-parent, outcome/evidence/diagnostic/
cleanup restrictions are unchanged. Typed-complete history with P parented by expected
Cq and expected Q retained, but T pointing to another matching Q, MUST reject.
Rewriting receipt token/base claims cannot replace independent expected Cq/Q.

Bootstrap still has no selected T/snapshot/packet; caller already knows Q. P/U are
working evidence, publication is provisional, and retrieved validated F is done
only with recorded computation and separate cleanup. Missing outcome/worker exit
never invents failure. Loading/observing/receiving never registers or dispatches Q.

Only explicit received refs are created. A submission/reservation refs remain at Cq,
not P/F; existing heads/earlier refs remain unchanged. The preexisting A reservation
is not a copied B ref. Other B refs do not transfer. Complete copied packets plus
independent expected suffice with B offline; historical paths/source stay inert.
Same-ref/same-target receive is nonexecuting and idempotent; P-to-F ref advance conflicts.
All validation and validation-scratch cleanup precede actual A import; late import
errors abort new records/ref together, while postcommit response loss can retain them.

## Informative example and evidence

```sh
python /path/to/examples/caller_requests.py /fresh/parent/story
dml --json --repo /fresh/parent/story/caller.dml snapshot --ref submission-1
dml --json --repo /fresh/parent/story/caller.dml log --ref trial-1-completion
```

The [finite application](../../examples/caller_requests.py) records two matching
Q submissions and a nonzero-after-U submission, with unrelated prior Q/T/history and
composite-only retained descendants in C. It retains/reaps fixed workers while fresh
clients observe P/U/F, renames A offline, copies packets and receives with B offline.
A separate Q remains never started. Cooperative gates are ordinary declared inputs
in [trusted child source](../../examples/local_slow_add.py), not installed fault hooks.

[Request tests](../../tests/python/test_caller_requests.py),
[history tests](../../tests/python/test_caller_request_history.py),
[safe process tests](../../tests/python/test_caller_request_process.py) and
[example tests](../../tests/python/test_caller_request_example.py) provide evidence.
Actual commands, installed provenance, real versus substituted faults, measured versus
installed coverage/memory and trust/profile/process/platform/mutation qualifications
belong to [Iteration 8 results](../../../dml-design/iterations/08-caller-recorded-requests/RESULTS.md).
No network/cloud, detached service, process-tree cleanup, sandbox/authentication,
full capture, scientific-validity or automatic-recovery guarantee is supplied.
