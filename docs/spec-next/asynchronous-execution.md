# Asynchronous same-machine execution and progress

Status: implemented by explicitly imported `daggerml.exchange` and its fixed installed
`daggerml.exchange_worker` module.

## Authority boundary

This document owns saved observation identity, live process ownership, launch/readiness,
coherent progress discovery, immutable observation packets and selected-progress reception.
[Repository execution](repository-execution.md) owns preparation, selection and synchronous
execute/receive; [local execution](local-execution.md) owns the unchanged runner, recorded
roles and direct-child disposition. [Transfer](transfer.md) owns complete pinned bundles
and atomic create-or-same-target refs. [Python API](python-api.md) owns native handles;
[CLI](cli.md) owns inspection. Vocabulary follows the [glossary](glossary.md).
Normative sections describe implemented behavior; example orchestration is informative.
[Caller requests](caller-requests.md) owns explicit prelaunch Q, imported-Q first
registration and exact Cq/Q mode-specific discovery/validation. This document's
ownership, phases/packets, unknown and done boundaries apply unchanged in both modes.

## Public surface and descriptions

```python
from daggerml.exchange import (
    ExchangeHandle, WorkerLaunch, ExchangeObservation, ReceivedObservation,
    save_exchange_handle, load_exchange_handle,
    start_exchange, observe_exchange, receive_observation,
)

ExchangeHandle(workspace, expected: ExchangeSpec)
save_exchange_handle(file, handle: ExchangeHandle) -> None
load_exchange_handle(file) -> ExchangeHandle
start_exchange(handle: ExchangeHandle) -> WorkerLaunch
observe_exchange(handle: ExchangeHandle, *, packet) -> ExchangeObservation
receive_observation(repository_path, *, packet, expected: ExchangeSpec,
                    ref: str, map_size: int = 0) -> ReceivedObservation
```

Existing prepare/execute/receive remain usable. Creating/loading a handle never dispatches.
Frozen `ExchangeHandle` normalizes its current caller-owned workspace path using exchange's
path profile and owns an `ExchangeSpec`. It contains no A path, command, environment, PID,
process object or recovery authority. `expected` MUST remain caller-owned, independent of
incoming packets. Loading validates bounded fields without consulting the workspace.
Start/observe require exact handle selection equality with the prepared workspace job.

`WorkerLaunch` is a separate **nonserializable live application owner**, retaining `.handle`,
`.process` (the actual `subprocess.Popen`) and its log streams. The application MUST retain
and reap it. `wait(timeout=None)` calls the public process wait and closes both streams
only after direct-worker disposition is established. Timeout/other wait errors retain
ownership/streams; the application can wait again. Process status MUST NOT determine
recorded progress, failure or completion. There is no context-manager wait, finalizer,
hidden registry, signaling from saved identity, cancellation or detached supervisor.

**Normal exit of the sole live launching owner while leaving an unowned worker is not a
supported lifetime/cleanup guarantee.** A separate finite application can own the launch
while short-lived observation clients exit. Hard loss of that owner may orphan workers/
children; surviving files can still be observed without authorizing replacement execution.

Frozen `ExchangeObservation` owns `lifecycle`, `phase`, optional `packet: Path` and optional
`snapshot: ReceivedObservation`. Bootstrap has neither snapshot nor packet; no fake
occurrence is allocated. For a retrieved snapshot, frozen `ReceivedObservation` owns:

- `lifecycle`, `phase`, selected `commit`, `ref`, bundle-row `object_count`;
- `pre_dispatch`, `request_id`, `attempt_id`, `request`, `initial_attempt`;
- optional publication DAG `publication` and provisional/successful `result`;
- optional `completion: ReceivedRun`, containing final computation/cleanup only for F.

During observation `ref` and nested completion's `ref` are `None`; receive supplies the
explicit destination ref. U's result is **provisional publication**, never final success.
F failure's `result` is absent; accepted publication can remain as `completion.evidence`.
Lifecycle is `working` unless validated selected final computation/cleanup is retrieved,
then `done`. Phases `bootstrap`, `initial`, `publication`, `completion` are document-local
evidence labels, not additional shared lifecycle states or process-liveness assertions.

## Retained launch and readiness

Start validates the handle/job and rejects existing started/B/output/readiness/log artifacts.
It creates exclusive `launched` **before** spawn; an existing marker rejects repeat start
without invoking a process. It prepares fixed command, exclusive log streams and live owner
before spawning `[sys.executable, '-m', 'daggerml.exchange_worker', workspace]`, with inherited
trusted runtime/environment, `shell=False`, DEVNULL stdin and file-backed stdout/stderr.
No pipe draining, arbitrary command or A path is part of this protocol. Streams/logs are
transport diagnostics, not recorded computational outcomes or bounded-disk guarantees.

Catchable log/owner/spawn setup errors close acquired streams, propagate and retain artifacts/
marker. There is no postspawn receipt write or wrapper allocation required for a successful
return. Ordinary filesystem/process calls have no portable hard deadline/RSS bound. Hard
owner loss, process creation uncertainty or response loss MUST NOT authorize automatic
relaunch or marker removal. A normal returned live object proves only that spawn returned
its subprocess object, not computational dispatch/readiness.

The worker calls public `execute_exchange` once. Execute retains its separate exclusive
`started` boundary; direct synchronous execute does not require `launched`. Execute rejects
preexisting `worker-ready.json` alongside B/output. After bootstrap/import, selection/ref
validation and repository handle closure, it publishes readiness **before** public
`local.run_step` (default fresh-Q mode) or public `local.run_request` (caller-Q mode). Readiness IO failure prevents dispatch and retains B/markers. Readiness
has exactly `format`, `token`, `commit`, with format `daggerml-local-exchange-ready-v1`.
It conveys no occurrence, outcome or process health. The independent launch and actual
execute markers are cooperative one-shot boundaries, not exactly-once external execution.

## Coherent discovery followed by immutable selection

Observe performs one invocation, not an internal polling loop. It validates job/expected
and readiness. Without readiness it returns `working/bootstrap`, without opening partially
initialized B or creating a packet. With readiness, malformed receipt, wrong token/base,
missing/unreadable B or corrupt refs raises rather than being concealed as bootstrap.

One public read storage transaction in B reads the explicit worker head and, if needed,
its selected attempt publication ref. It derives exactly one fresh request/attempt from
tree-name differences relative to C in default mode; [caller mode](caller-requests.md#exact-q-through-synchronous-and-asynchronous-return)
derives exact Q from pinned submission and requires only one fresh T. Existing prior requests/attempts/publications in C
remain preserved and unrelated. It does not scan repository-wide refs or pick the first
prefix match. A head still at C yields bootstrap. For initial P, an unchanged attempt ref
selects P; a valid publication U selects U. A final head selects F and validates its exact
P/optional U history. Wrong selection, arbitrary head/ref movement or mixed association
raises. No private local/transfer helper or raw decoder is used in production.

The transaction/handles close, then public transfer exports the **selected immutable ID**.
Ref/head movement afterward cannot retarget that ID. Full all-parent bytes are validated
again in disposable storage before allocating the caller-selected fresh packet. Validation
handles close and helper-owned scratch is cleaned before packet publication. IO/profile/
validation/cleanup failure raises and retains B; it is not computational failure or a
successful `done` response. Observation never invokes execution or changes B.

## Selected P/U/F validation

The exchange-owned read-only role inspector shares its initial/publication checks with
existing completed-return validation. It uses public typed descriptions and isolated public
bundle import. Source reservation refs need not exist in the packet or receiving repository.

| Selected history | Required evidence | Lifecycle |
| --- | --- | --- |
| P / initial | Default mode: parents exactly `(C,)`; exact C tree plus only fresh request Q/initial attempt T. Caller mode: exact Cq plus only T linked to pinned Q. Both validate selected intent/binding/inputs, roles/root/types, association, publication ref and inert scratch spelling; no final fields | `working` |
| U / publication | Valid P above; parents exactly `(P,)`; exact P tree plus matching T-associated publication/result; initial T unchanged without final fields | `working` |
| F / completion | Existing full selected-completion validation, final T preserves initial field nodes and adds `done`, computation/cleanup; exact tree and ordered `(P,)` or `(P,U)` parents | `done` |

[Repository execution's completion checks](repository-execution.md#selected-completion-validation-before-a-writes)
own final outcome/exit/result/evidence/cleanup/diagnostic restrictions. Wrong typed-valid
selection, occurrence, phase, parent order, extra history or field association rejects
before A writes. Structural reports do not authenticate a trusted worker or independently
prove scientific/external truth.

## Immutable packets and independent reception

Every nonbootstrap observation allocates a **new** observer-owned directory. Never reuse/
overwrite a packet. It writes complete `snapshot.bundle`, job descriptor, then
`observation.json` last. Partial/temp files may remain on failure; this is not filesystem
rollback, multi-file/repository atomicity or power-loss durability.

Strict bounded UTF-8 JSON descriptor rules and 8,192-byte limit are inherited from
[exchange framing](repository-execution.md#preparation-and-retained-workspace), as are
exchange paths/errors and owning transfer bounds. Saved handles have exactly `format`,
`workspace`, `expected` (the exact job object), format `daggerml-local-exchange-handle-v2`,
and exclusive file creation. Observation receipts have exactly `format`, `token`, `commit`,
`phase`, `selected_commit`, `pre_dispatch`, `request_id`, `attempt_id`, format
`daggerml-local-exchange-observation-v1`. No serialized lifecycle/success/PID assertion is
trusted; lifecycle and outcome are derived from selected history.

Receive requires independent `expected`, exact job/receipt token/base, IDs/occurrences,
phase and bundle-root equality. It revalidates full history in disposable storage, closes/
cleans scratch and prepares the owned description **before** touching A. Then unchanged
public atomic transfer imports the same bundle under caller `ref`. It never moves existing
A heads, synchronizes latest progress, adopts/merges, recreates B refs, executes source or
acts on incoming historical paths. B/input/source can be offline; only complete packet
files and independently supplied selection are required.

Same-ref/same-target reception is idempotent. Receiving F under a ref already pointing to
P/U conflicts, rather than updating it. New progress/final refs are explicit caller choices.
Map-full/ref/commit failures abort all new A records/ref writes; larger-map whole receive
retry is transfer retry, never another computation. Response loss after actual A commit
can leave complete import. Earlier packet/received snapshots remain immutable.

## Completion, unknown and limits

`done` means selected recorded F has final computation **and separate cleanup disposition**
and its complete selected history was successfully retrieved/validated into this packet.
It does not mean A has received it, computation succeeded, cleanup succeeded, or the outer
worker has exited. The local runner commits F after establishing direct computational-child
disposition and attempting cleanup. The outer execute may still be exporting ordinary
synchronous output. F can be retrieved without `completion.json`; this does not finalize an
unknown T, create a new attempt or repair/retry execution.

Worker loss with only P/U can remain `working` forever. Publication is not success;
nonzero exit after publication records failure with evidence. PID exit, logs, marker/receipt
presence, elapsed time and prior A reception never turn unknown into failure/done. Old P/U
packets remain working observations even after a newer F exists. F export/profile failure
preserves recorded completion in B but supplies no successful done packet.

Only cooperative trusted single-owner workspace/packet writers are supported. Independent
readers may use separate packet directories. No adversarial writer/symlink/physical-alias,
authentication/sandbox, network/cloud, general recovery/process-tree or full environmental
capture guarantee. Full-history transfers may contain sensitive data and obey owning
profile/allocation limits. Application/test cleanup follows only owned scratch after known
writer disposition, not arbitrary serialized paths.

## Informative example and evidence

```sh
python /path/to/examples/asynchronous_execution.py /fresh/parent/story
dml --json --repo /fresh/parent/story/caller.dml log --ref trial-1-completion
```

The [finite application](../../examples/asynchronous_execution.py) retains/reaps each fixed
worker while fresh short-lived clients observe/receive. The [trusted child](../../examples/local_slow_add.py)
uses a caller-owned gate directory recorded as a named input, with finite cooperative
release waits around publication; these are ordinary example source/file effects, not an
installed runtime/fault hook. The application releases both gates on errors before waiting,
never kills a worker with a possibly live child. It runs two matching fresh jobs and a
nonzero-after-publication job, renames A offline during worker execution, moves main
independently and receives copied packets with B offline. Gates/disk/timeouts are example
policy, not portable scheduling/lifetime/security assurance.

Evidence: [implementation](../../python/daggerml/daggerml/exchange.py),
[fixed worker](../../python/daggerml/daggerml/exchange_worker.py),
[launch/fresh clients](../../tests/python/test_exchange_launch.py),
[progress/races/rollback](../../tests/python/test_exchange_progress.py),
[framing/typed faults](../../tests/python/test_exchange_progress_faults.py),
[safe process loss](../../tests/python/test_exchange_progress_process.py) and
[maintained example](../../tests/python/test_asynchronous_example.py).
Actual commands/provenance, tested versus excluded coverage, real versus substituted faults
and runtime/platform/process/mutation qualifications belong to
[Iteration 7 results](../../../dml-design/iterations/07-asynchronous-local-execution/RESULTS.md).
