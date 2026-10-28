# Iteration 7 candidate design: asynchronous local execution and progress

Current status: the user approved this bounded plan and declared GO, including separate
saved handle/live application process ownership. Implementation, independent review,
focused commit/push and exact-SHA CI are complete at `a8d6463`; all six jobs pass. See
[RESULTS.md](RESULTS.md) and [REVIEW.md](REVIEW.md). The turn is complete and stopped;
preparation/GO statements below preserve provenance, not permission to restart.

Status: the user agreed to the direction and authorized preparation of the worked
example, candidate design and handoff. **This plan is not yet approved; implementation,
worker assignment/restart, experiments, implementation commit/push and CI launch are
not authorized.** Exact APIs and the choices below are assistant recommendations.
Iteration 6's completed GO is not inherited.

## 1. Authority, agreements and learning goal

This document owns candidate lifecycle, process ownership, discovery and snapshot
validation. [EXAMPLE.md](EXAMPLE.md) owns acceptance; [HANDOFF.md](HANDOFF.md) owns
future work order and assurance. [Discussion](../../discussion.md#iteration-7-agreed-direction-asynchronous-execution-and-inspectable-progress)
owns agreements; the [glossary](../../../dml/docs/spec-next/glossary.md) owns vocabulary.
Current [local execution](../../../dml/docs/spec-next/local-execution.md),
[exchange](../../../dml/docs/spec-next/repository-execution.md) and
[transfer](../../../dml/docs/spec-next/transfer.md) contracts own implemented behavior.
This is not an as-built specification.

Agreed direction:

- Same machine, separate repositories and the existing local runner.
- Start one fresh worker without waiting for computation; permit bounded subsequent
  observations from an owned saved exchange handle, including a fresh caller process.
- Inspect initial request/attempt, accepted child publication and final outcome.
- Receive explicitly selected snapshots under caller-chosen refs, leaving existing
  A heads and earlier snapshots unchanged. Observations are not new attempts.
- Shared adapter lifecycle `working`/`done`, separate computation/cleanup outcomes.
  Missing final outcome is unknown; `working` is not process liveness.
- No automatic execution retry/recovery/finalization, scheduler/daemon, distributed
  locking, network/cloud, process-tree guarantee, merge/adoption, reuse/facets or
  resource management.

Learning goal: inspect recorded work while it happens without building a second
executor or confusing publication, completed computation and caller reception.

## 2. Live baseline and seams

Planning inspected clean implementation
`a0aa05d56b9e70277a98bb03e26514ab6b6f1415`. Design has uncommitted Iteration 6 delivery
and subsequent discussion/status edits, intentionally preserved. No implementation
or as-built file was changed, no worker restarted and no build/test/prototype ran.
[Iteration 6 results](../06-local-repository-execution/RESULTS.md) and
[review](../06-local-repository-execution/REVIEW.md) are prior evidence, not new tests.

Existing public seams:

- `prepare_exchange`: caller-owned pinned selection/token and retained workspace.
- `execute_exchange`: one-shot B bootstrap, unchanged public `local.run_step`, exact
  completed history/output. No asynchronous driver currently exists.
- Public read transactions: inspect B's working ref, pinned commits/trees and attempt
  publication ref through one coherent read snapshot.
- Public `export_commit` / `import_commit`: pinned full-history bytes and atomic
  create-or-same-target ref. No thin transfer or moving destination-ref policy needed.
- Exchange's own selected-record inspector: extend internally for initial/publication
  snapshots and reuse completion validation without exposing private callbacks or
  reading private local/transfer helpers.

Candidate production changes are Python-only: additive exchange helpers/descriptions,
a tiny installed worker module and one bootstrap-readiness receipt in the existing
exchange driver. Local runner, native APIs/encodings and transfer stay unchanged.
The readiness receipt is a proposed addition to exchange's file/IO behavior, not an
already implemented guarantee. A missing primitive or material contract change needs
an explicit scope decision, not silent expansion.

## 3. Serializable observation identity versus live process ownership

**Recommended choice: separate them.** A frozen `ExchangeHandle` contains normalized
workspace path and caller-owned `ExchangeSpec`. It identifies where to observe this
one prepared job; it owns no repository handle or process and contains no PID,
`Popen`, executable command, recovery permission or timeout-derived failure state.
Caller-controlled persistence is bounded JSON; loading a handle never starts work.
The workspace path is current caller input, unlike historical scratch paths in DAGs.

Starting returns a distinct **nonserializable** `WorkerLaunch` retaining the actual
subprocess object and any launch-owned stream resources until the application reaps
it. The process owner must remain available for supported cleanup. Do not serialize a
PID and later signal it, discard a running `Popen`, hide it in a module-global registry,
rely on finalizers or claim a fresh observer can reap an unrelated process.

For the acceptance story, a finite application-owned supervisor starts/reaps the
worker, while separate initiating/observing caller scripts can exit. This is example
orchestration, not an installed daemon, scheduler or durable supervisor service.
An application that starts directly is itself the process owner and must retain/reap
the launch object. **Transparent detached start followed by exit of the sole process
owner is not promised.** Hard loss of that owner can orphan a worker/child; explicit
observation remains possible where files/B survive, but no cleanup/liveness guarantee
or automatic replacement follows.

This ownership choice is a reviewable refinement of the agreed direction. It permits
fresh caller observations without inventing portable parent-exit process supervision.
If the user instead requires the launching process itself to exit normally without
another owner, revisit the plan before implementation; do not quietly add a service,
double-fork platform restriction or detached-process recovery mechanism.

Documentation consultation during planning: Context7 `/python/cpython` confirms that
`Popen` context-manager exit waits, its destructor warns about a running child, and
explicit `wait`/`poll` establish direct-child exit. Candidate code uses public,
Python >=3.8-compatible operations only; internal polling is not a supported seam.
No environment/configuration/tooling changes or process experiments occurred.

## 4. Illustrative additive surface

Not an as-built API; exact signatures may be refined:

```text
ExchangeHandle(workspace, expected: ExchangeSpec)
start_exchange(handle) -> WorkerLaunch
observe_exchange(handle, *, packet) -> ExchangeObservation
receive_observation(A, *, packet, expected: ExchangeSpec, ref, map_size=0)
    -> ReceivedObservation
```

Preparation remains the existing explicit helper; creating a handle does not dispatch.
The application stores caller-owned expected selection independently of observation
packets. Start is bounded in the sense that it does not wait for computation;
observe performs one read/export/validation, not an internal polling loop. Ordinary
spawn, filesystem/LMDB calls and full-history transfer have no portable hard wall-clock
or RSS guarantee. Use finite limits/waits in examples/tests and preserve existing
transfer profile limits.

`ExchangeObservation` owns `lifecycle`, a descriptive `phase`, optional selected commit,
request/attempt IDs and packet description. Proposed phases are `bootstrap`, `initial`,
`publication`, `completion`; these are **evidence labels**, not additional shared
adapter lifecycle states. Bootstrap has no computational occurrence or packet yet.
`ReceivedObservation` owns derived lifecycle, selected snapshot/phase/occurrences/count/
ref; only completed history has final computation/cleanup fields. Do not manufacture a runnable LocalContext
or represent publication as a successful outcome. Count remains bundle rows.

## 5. Start and readiness: no implicit relaunch

Start validates the handle against the prepared job and existing one-shot state before
launch. It exclusively creates a candidate `launched` marker **before process creation**.
Preexisting launch/start/B/output/readiness artifacts reject start; a rejected repeat
never invokes a subprocess. File or spawn errors retain allocated artifacts/marker.
Loss after marker creation before spawn is ambiguous and cannot be repaired by calling
start again. Neither marker proves computational dispatch.

The worker command is fixed installed Python module invocation, illustratively
`[sys.executable, '-m', 'daggerml.exchange_worker', workspace]`, with no A path or
caller-supplied command/environment descriptor. It calls public `execute_exchange`
once; execute also rejects a preexisting readiness artifact before bootstrap rather
than overwriting it. Use DEVNULL stdin and file-backed launch logs; do not retain pipes requiring
the caller to drain them or use stdout as completion protocol. Logs are caller-owned
transport diagnostics, not new scientific evidence or unbounded-output protection.

Caller-controlled handles use normalized paths and independent expected selection;
observe/receive do not consult live launch objects. Prepare launch wrapper/command/log
resources before spawn where possible, retain them through explicit reaping, and avoid
postspawn acknowledgement-file writes or result allocations as a prerequisite for a
successful start response. Catchable bookkeeping failure must not silently discard a
running process; qualify any uncertain spawn/disposition rather than inventing failure.

The existing worker-side `started` marker still guards actual execute. Keep independent
launch and execute boundaries; start does not reserve an attempt or alter `started`.
Existing direct synchronous execute remains usable; no requirement to have `launched`.

Recommended additive `worker-ready.json`: after successful B initialization/import,
selection/ref validation and handle closure, before calling `run_step`, execute publishes
a bounded closed-temp/replace receipt echoing token/base. It contains no occurrence or
status assertion. This separates normal bootstrap races from an initialized B that
should be readable. A readiness-write failure prevents computational dispatch; B and
markers remain. Existing completion publication remains separate/last.

Observe before readiness returns `working/bootstrap`, no selected computation and no
packet; it does not open a partially initialized LMDB environment. Absence of readiness
is not evidence of health or future progress. Once readiness exists, malformed receipt,
missing/unreadable B, wrong base or corrupt refs raises, not concealed as bootstrap.
Readiness and process exit do not authorize restarting anything.

## 6. One coherent observation, then pin and export

Observe checks caller-owned expected selection/job and readiness. With readiness,
open B for one read storage transaction and read its explicit working ref:

1. If it still targets C, report `working/bootstrap` without an occurrence. This is
   before local pre-dispatch recording, not proof the child has or has not started.
2. If it targets P, derive only the fresh request/attempt entries added to C. Require
   exact base/selection/role/occurrence/tree/parent checks below. Read that attempt's
   publication ref **inside the same read transaction**. If it still targets P, select
   P; if it targets valid U, select U. A malformed/moved arbitrary target is an error,
   not a reason to guess a different attempt or hide the violation.
3. If the working head describes a final attempt, select F and validate its P/optional U
   history. Do not infer completion from child exit, presence of a publication entry,
   a process PID, log text, marker, or output-file existence.

No repository-wide/ref-name scan or private reservation reader is needed. Prior
request/attempt entries in C remain unrelated existing data; fresh entries must be
identified by exact tree differences, not the first matching name prefix. A branch
change or second request at the worker head is rejected, not adopted automatically.

Close B, export the **selected immutable ID** via public transfer, and validate the
owned bundle in private disposable storage. Ref movement between discovery and export
cannot retarget that ID. A later observation may see more progress; the first stays
an honest observation of its pinned snapshot. No sticky mutable latest-status cache
or guarantee that separately selected snapshots are currently newest.

Even complete B history may exceed export limits. If export/validation fails, raise
an exchange error retaining B; do not rewrite it as computation failure or return a
successful `done` observation with missing retrieval. Observation never invokes execution,
changes B refs/records, repairs files or finalizes unknown history.

## 7. Selected progress validation and packet publication

All packets carry existing job selection/token, selected root/phase and, when present,
exact pre-dispatch/request/attempt IDs. Candidate transport uses `job.json`,
`snapshot.bundle`, `observation.json` in a **new caller-selected packet directory**;
8 KiB strict descriptors and owning transfer bounds. No arbitrary filenames/commands,
PID authority, pickle or packed Python codec. Exact labels/keys remain provisional.

Validate using the same native/public import and small exchange-owned read-only role
inspector, not by trusting descriptor phase/status strings:

| Selected snapshot | Required recorded basis | Derived lifecycle |
| --- | --- | --- |
| P / initial | P parents `(C,)`; exact preserved base plus fresh Q/T; selected request/initial attempt association and no final fields | `working` |
| U / publication | Exact valid P above; U parents `(P,)`; exact P tree plus matching attempt publication/result; initial attempt still lacks final outcome | `working` |
| F / completion | Existing complete selected-run checks, exact `(P,)` or `(P,U)` parents, final attempt `done`, computation and separate cleanup disposition | `done` |

Use strict consumed types/field sets and exact field-node preservation where appropriate.
No copied reservation ref is necessary in validation/A; live B ref discovery and
immutable history validation are distinct. Result publication is **provisional evidence**:
if the child later exits nonzero/times out, F may retain that same DAG as failure evidence.
U alone never supplies a final success/exit/cleanup report.

Prepare owned descriptions, close/clean validation scratch, then create the fresh packet,
write the full bundle and publish the bounded observation receipt last. Existing packets
are never replaced. Filesystem errors may leave allocated partial packets; do not call
that filesystem rollback. Bootstrap observations create no packet. Receipt/file presence
alone is not valid input; receivers independently validate every selected snapshot.

A complete observation packet is sufficient for fresh receive with B offline and caller
expected supplied separately. `receive_observation` independently validates in disposable
storage before touching A, then uses unchanged atomic `import_commit(..., ref=...)`.
Different/malformed refs and late errors abort all new A objects/ref writes; same-target
re-receive succeeds. No A head movement, implicit latest ref update or replacement commit.

## 8. What `done` means and what it does not

`done` in an observation means selected F has a structurally validated recorded final
computational outcome and separate cleanup disposition, and its complete history has
been successfully retrieved into that observation packet. It does **not** mean A already
imported it or the outer worker/supervisor process has exited. F is committed after the
runner establishes direct computational-child disposition; execute can still be exporting
its ordinary output afterward. Supervisor reaping is a separate process-owner obligation.

This maps existing local final-attempt `done` to a bounded adapter observation without
adding another mutable status machine. No new polling occurrence is injected into Q/T;
callers may deliberately record observations as ordinary research data, but mandatory
observation DAGs/schema are not part of this slice.

F without original `completion.json` can be explicitly observed/exported and received:
that is retrieval of already-recorded history, not recovery/finalization or another attempt.
If F exists but export fails, B's recorded completion still exists while the adapter
invocation raises and supplies no complete packet. A can receive a stale P/U after F
exists: its returned lifecycle describes that selected snapshot, not current worker state.

Worker loss after P or U with no F leaves future observations `working` at that history,
possibly forever. There is no inactivity timeout/dead PID conversion to failure or done.
Driver errors and computational failure differ: a durably recorded computational failure
is a `done` completion; bootstrap/persistence/IO errors do not fabricate one.

## 9. Failure/trust boundaries and review choices

No transaction spans launch/files/B/A/external effects. One-shot markers sacrifice
transparent launch retry; process status is not durable computational evidence. A may
remain unchanged while B has unknown/publication/final history; response loss after A
commit can leave complete import. Retain workspace/B/packets on all exits.

Only cooperative trusted caller/worker/source and single-owner workspace/packet creation
are supported. Concurrent read-only observers may use independent packet directories;
no adversarial writer/symlink replacement/physical alias/authentication/security guarantee.
Historical paths/code/URI remain inert in observe/receive. Full parent history may be
sensitive; allocation/disk/output/runtime bounds and captured dependency limits remain
those of the owning local/transfer layers.

Review before approval:

1. Application-owned finite supervisor plus nonserializable launch ownership, not
   transparent detached start. Fresh observers own only the saved handle.
2. Readiness marker is additive exchange behavior; no local runner callback/redesign.
3. Coherent live-B discovery followed by pinned public export; no progress-publishing daemon.
4. Immutable P/U/F observation packets and explicit create-or-same-target A refs.
5. `done` means validated recorded completion successfully retrieved, not A adoption,
   outer-worker exit, scientific validity or successful cleanup.

Stop after this vertical slice, meaningful failure assurance and independent review.
No implementation/prototypes, worker restart, publication, cloud/global tooling or
later feature is authorized by preparation of this candidate plan.
