# Execution across local repositories

Status: implemented by explicitly imported `daggerml.exchange`.

## Authority boundary

This document owns pinned selection, workspace files/ownership, one-shot execution,
selected-completion validation and explicit return publication. [Local execution](local-execution.md)
owns the unchanged runner and ordinary role/history conventions; [transfer](transfer.md)
owns bundle framing, profile and atomic import. [Python API](python-api.md) owns native
handles/values, [repository](repository.md) storage and [CLI](cli.md) inspection.
Vocabulary follows the [glossary](glossary.md). The additive
[asynchronous contract](asynchronous-execution.md) owns saved handles/live worker launch,
bootstrap readiness and immutable initial/publication/completion observation packets.
The separate [SSH contract](ssh-execution.md) owns caller-Q SSH transport/fixed invocation and foreground asynchronous SSH ownership;
its fetch candidates use this document's unchanged receive and its P/U/F packets use the
[owning asynchronous inspector/reception](asynchronous-execution.md).
Normative sections describe implemented
behavior; example orchestration is informative. The additive [caller-request contract](caller-requests.md)
owns explicit Q-only A recording, public imported-Q first registration and the exact
Cq/Q selection delta in both return paths. Fresh-Q-in-B behavior below is the default
`request=None` mode.

## Public stages and owned descriptions

```python
from daggerml.exchange import (
    prepare_exchange, read_exchange_spec, execute_exchange, receive_exchange,
    ExchangeSpec, ReceivedRun, ExchangeError,
)

read_exchange_spec(workspace) -> ExchangeSpec
prepare_exchange(repository_path, *, commit: ObjectId, binding_name: str,
                 inputs_name: str, intent_uri: str, worker_ref: str,
                 workspace, request: Optional[ObjectId] = None) -> ExchangeSpec
execute_exchange(workspace, *, map_size: int = 0) -> LocalRun
receive_exchange(repository_path, *, workspace, expected: ExchangeSpec,
                 ref: str, map_size: int = 0) -> ReceivedRun
```

`read_exchange_spec` promotes the existing bounded strict job reader and returns an owned
`ExchangeSpec`. It reads only `job.json`, does not inspect/import B, dispatch, mutate refs or
validate repository history. Both original fresh-Q and caller-Q descriptions remain readable.

All stages close their own repository handles. Callers MUST close other handles for
that physical repository first. Preparation/receive require initialized caller A;
execute creates independent B at `workspace/worker.dml`. No stage automatically
starts another stage. The example starts a fresh worker process, but the public
execute helper itself is synchronous and calls public `local.run_step` in default mode,
or public `local.run_request` with a [caller-pinned Q](caller-requests.md#pinned-submission-and-first-registration-in-b).
No new native operation, execution CLI command or process supervisor is involved.

Frozen `ExchangeSpec` owns `token`, `commit`, `binding_name`, `inputs_name`, `binding`,
`inputs`, `intent_uri`, `worker_ref` and optional pinned `request`. It requires `ObjectId` IDs, exact strings,
the existing ASCII name profile and an already canonical absolute intent URI accepted
by the native URI helper. `token` is fresh UUID4 lowercase hex, a **transport-only
correlation token**, not a DML request/attempt occurrence or authentication. Expected
selection is caller-owned and MUST be passed independently to receive, not inferred
from a worker receipt. The workspace path is out-of-band, not a computational identity.

Paths accept filesystem path-like values, become absolute UTF-8 paths and reject
empty/NUL/unencodable spellings. Historical interpreter/scratch strings are validated
as absolute NFC spelling without NUL; receive never opens or deletes them. `map_size`
is exact int, zero or 1 MiB through `sys.maxsize`, selecting existing repository
map behavior for B initialization/input import or final A import. Unchanged local
execution subsequently opens B with its own existing default repository options;
`map_size` is not an execution/result-size quota. The private validation repository
also uses the existing default map. There is no automatic failed-import growth or
execution retry.

Frozen `ReceivedRun` owns:

- `commit`, `ref`, `object_count`, `pre_dispatch`;
- request/attempt occurrence strings `request_id`, `attempt_id`;
- DAG IDs `request`, `initial_attempt`, `final_attempt`, `outcome_dag`, `cleanup_dag`;
- `outcome` (`success`/`failure`), recorded `exit_code`, optional `reason`/`detail`,
  optional `result`/`evidence`, and separate `cleanup` (`ok`/`failed`).

Count is validated bundle rows, not newly inserted objects or computational attempts.
It is not a runnable `LocalContext`: copied reservation refs/paths are not operational
authority in A. Execute returns the existing owned `LocalRun` describing B. Recorded
computational failure is a normal completion eligible for history return.

`ExchangeError` (`ValueError`) reports framing, selection, one-shot or selected-history
violations with fixed messages, not payload excerpts. Public type errors use
`TypeError`; native, transfer, local persistence and filesystem exceptions retain
their existing types. Exceptions do not fabricate a final outcome/receipt, grow maps,
repair refs, clear one-shot markers or initiate retries. Cleanup failure identifies
helper-owned remaining scratch through the filesystem exception path.

## Preparation and retained workspace

Preparation reads the explicit immutable commit C/tree and resolves both supplied
tree-entry names, not moving refs or unrelated arbitrary DAG IDs. It checks consumed
binding fields against the existing local record contract and reads the input DAG;
it does not impose an argument schema or prove external executable availability.
After handles close, it exports C's complete all-parent typed object closure.
A missing/corrupt reached object or transfer-profile overflow fails before creating
a workspace. Preparation MUST NOT write A or create computational occurrences;
explicit request recording is the separate [A mutation](caller-requests.md#atomic-explicit-recording-in-a).

The workspace must be a new caller-selected directory with an existing parent.
Preparation creates it exclusively, writes `input.bundle`, then publishes `job.json`
last. File errors can leave caller-owned artifacts; there is no filesystem rollback.
An existing directory is not replaced/reused. The fixed workspace files are:

| File | Owner and meaning |
| --- | --- |
| `input.bundle` | Prepared pinned C, existing transfer format |
| `job.json` | Exact selected job; no A path, commands, environment or arbitrary filenames |
| `started` | Exclusive worker one-shot marker, not a DML occurrence |
| `worker.dml` | Fresh initialized B, retained on success/failure |
| `launched`, `worker.stdout`, `worker.stderr` | Optional asynchronous launch marker/logs; [owning contract](asynchronous-execution.md#retained-launch-and-readiness) |
| `worker-ready.json` | Bootstrap readiness before local dispatch; [owning contract](asynchronous-execution.md#retained-launch-and-readiness) |
| `output.bundle` | Exact completed F and full history |
| `completion.json` | Last-published correlation/history receipt, not an outcome assertion |

Descriptors are strictly UTF-8 JSON, limited to 8,192 encoded bytes. Duplicate keys,
nonstandard constants, trailing documents, unknown/missing fields, wrong types,
invalid profiles and unsupported format labels fail. Reads are bounded to limit + one
byte. Bundle file reads use the owning `transfer.MAX_BUNDLE_BYTES`; parsing/record
reads still allocate, so these limits are not exact RSS or runtime bounds.

The job has exactly `format`, `token`, `commit`, `binding_name`, `inputs_name`,
`binding`, `inputs`, `intent_uri`, `worker_ref`, `request`, with format
`daggerml-local-exchange-job-v2`. `request` is required null or lowercase 32-hex;
null preserves fresh-Q mode, an ID pins exact caller Q. No v1 migration is provided.
IDs/token are lowercase 32-hex. Completion has
exactly `format`, `token`, `commit`, `final_commit`, `pre_dispatch`, `request_id`,
`attempt_id`, with format `daggerml-local-exchange-completion-v1`. Occurrences use
the existing `q-`/`a-` lowercase 32-hex profiles. Outcome/result/cleanup are derived
from history, not serialized booleans or stdout.

Job/completion publication writes a closed same-directory temporary file, then
`os.replace`. Bundle writes are ordinary exclusive file writes. Interruption or IO
failure can leave temp/partial files. Receipt-last is not a cross-file/repository
transaction or power-loss durability guarantee. Malicious simultaneous writers,
path aliases/symlink replacement and hostile filesystem input are outside this
trusted single-owner prototype; no filesystem sandbox/locking claim is made.

## Fresh B and one-shot execution

Execute checks the descriptor and rejects preexisting B/output/readiness. Before initializing,
importing or dispatching, it acquires `started` with exclusive creation. A prior
marker prevents re-execution even if no DML attempt was ever created. Markers are
never automatically cleared. A fresh workspace is fresh execution, not an implicit
retry of a prior request. This cooperative one-shot boundary is not distributed
exactly-once execution.

Execute imports C into fresh B under the explicit `worker_ref`, checks input root,
selected binding/input DAGs and ref target, closes handles, publishes bounded bootstrap
readiness, then calls unchanged `local.run_step`. The local runner creates the request/attempt
in B in default mode; [caller mode](caller-requests.md) instead registers exact imported Q
and creates only T. It owns its
newly allocated execution scratch. Source refs are not copied from A.

After the runner returns (including recorded failure), execute exports the exact
`LocalRun.final_commit` F, writes `output.bundle`, then completion receipt last.
Driver/bootstrap/persistence/reaping errors do not create a receipt. Successful
computation may exceed transfer profile or encounter file failure afterward: B
remains done while A has no received outcome. No error initiates another attempt.
The workspace/B are retained on every exit, including success.

## Selected-completion validation before A writes

Receive owns bounded job/receipt/output bytes and requires exact job equality with
caller `expected`, matching receipt token/base, valid IDs/occurrences and bundle root
F equal to receipt F. It imports the complete output into a private disposable
repository using unchanged public transfer operations without a ref. It validates
only consumed selected local records through public descriptions:

- C's selected tree names/IDs match expected; binding/inputs are typed/valid.
- In default mode, pre-dispatch P has exactly `(C,)` as parents. Its tree preserves C and adds only
  this fresh request/initial attempt. Their names do not replace C entries or an
  existing publication name.
- Request root/role/intent/binding/inputs match expected and occurrence. Initial
  attempt root/role/request/publication-ref/scratch match the selected request and
  attempt; no copied reservation ref is required. Caller mode's exact Cq/Q and
  only-new-T requirements are owned by [the selection delta](caller-requests.md#exact-q-through-synchronous-and-asynchronous-return).
- Final attempt preserves exact initial field nodes, adds `status == done`, typed
  outcome/cleanup and the same occurrence. Final tree preserves P except this final
  attempt, plus accepted publication if present.
- Completion parents are exactly `(P,)` or `(P, U)` in that order. U has `(P,)`
  parents and exactly P's tree plus the occurrence-associated publication/result.
- Success has I64 zero exit and result equal to accepted publication. Failure has
  typed exit/reason/detail and optional evidence equal to accepted publication.
  Existing failure reasons are accepted; launch requires NULL exit, child-exit
  nonzero, missing/invalid publication zero. Launch/missing/invalid-publication may
  not retain accepted evidence. Success cannot be synthesized from an unpublished
  recorded failure. Reports are structural evidence, not independent external truth.
- Consumed role field sets/root/type checks follow local conventions. Available
  diagnostic DAGs have exact byte-count/truncated fields, BYTES root and existing
  4,096-byte retained limits. Failure/cleanup detail is bounded likewise. Cleanup
  has separate `ok`/`failed` disposition; only failed cleanup has scratch, matching
  the initial attempt. Failed cleanup never loses/reclassifies success.

All-parent transfer validates typed transitive completeness. This inspector does
not recreate reservation refs, load captured code, follow URI/path values, validate
scientific truth or become a generic schema/executor framework.

The owned received description is prepared, validation handles closed and allocated
validation scratch cleaned **before** any A write. Cleanup failure prevents A import;
caller workspace remains retained. Then the same owned bundle is imported into A
with explicit `ref` using unchanged public atomic transfer import. No main movement,
adoption/merge, replacement DML commit or copying of B refs occurs. A independently
moved main is preserved. Different/malformed return refs, late map-full/commit failure
abort all new A objects/ref changes together. Explicit larger-map whole-import retry
is caller-managed transfer retry, never another computation.

Receive returns only after storage commit. Response loss after commit can leave a
complete received F/ref despite no acknowledgement. Repeated receive is safe and
nonexecuting: same target succeeds, different target conflicts. A copied complete
packet needs only job/completion/output and independent expected selection, not B,
input bundle, original source or historical scratch.

## Process, trust and evidence limits

Missing history at A is unknown, not failed computation. Initial unknown B history,
done B without returned packet, complete packet before receive and A commit without
response are distinct knowledge boundaries. There is no transaction spanning A/B,
files and external effects, no automatic reconciliation/recovery or execution retry.

Only cooperative trusted source/caller/worker is supported. Captured entry bytes are
executed in B through the unchanged local runner; imports, interpreter/DML binaries,
environment and external resources are not captured. No A path is needed by the
worker protocol, but same-user processes retain filesystem authority: hiding/renaming
A is functional separation, not access control or a sandbox. Correlation tokens and
content IDs do not authenticate workers or certify reproducibility/scientific validity.

The example has finite direct-worker waits and finally-owned terminate/kill/reap.
Terminating caller/worker does not portably stop computational children/descendants.
Tests pause before child spawn or after actual child reaping/final persistence;
those safe barriers are not a general process-tree cleanup or power-loss guarantee.
Workspace deletion is caller policy after proving writers have stopped, never an
outcome-dependent helper action.

## Informative story and implementation evidence

```sh
python /path/to/examples/repository_execution.py /fresh/parent/story
dml --json --repo /fresh/parent/story/caller.dml snapshot --ref trial-1
dml --json --repo /fresh/parent/story/caller.dml log --ref trial-1
```

The [story](../../examples/repository_execution.py) runs two additions in separate
fresh worker processes/Bs and a recorded failure, renames A offline during each
worker, moves main independently after pin, then receives copied packets with B
offline. Ordinary Python/CLI inspection exposes distinct occurrences/equal result
11, pinned history, failure and separate cleanup without adopting returned snapshots.

Evidence: [module](../../python/daggerml/daggerml/exchange.py),
[selection/framing/identity tests](../../tests/python/test_exchange.py),
[wrong selected records/history](../../tests/python/test_exchange_records.py),
[process/file/storage faults](../../tests/python/test_exchange_process.py) and
[runnable-story/CLI tests](../../tests/python/test_exchange_example.py).
Actual commands, installed provenance, tested versus excluded populations, host-helper
versus uninstrumented subprocess evidence and runtime/platform limits belong to
[Iteration 6 results](../../../dml-design/iterations/06-local-repository-execution/RESULTS.md).
