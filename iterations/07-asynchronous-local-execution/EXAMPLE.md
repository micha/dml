# Iteration 7 worked example: start, observe, receive

Status: candidate acceptance story prepared at the user's request, **not executed**.
Direction is agreed; this detailed plan/ownership choice is not yet approved.
No implementation, experiment, delegation or publication authorization.
[DESIGN.md](DESIGN.md) owns candidate semantics; [HANDOFF.md](HANDOFF.md) owns assurance.
All APIs below are illustrative, not as-built contracts.

## 1. Prepare and retain independent expected selection

Use a fresh test-owned caller repository A. Create captured trusted slow-addition
source and named I64 inputs `left=4`, `right=7`, plus a retained `keep` DAG. Record
pinned C under `main`, and a genuinely unrelated branch-only sentinel/ref.

The child uses the existing public local context/result-publication helpers. It can
pause before calculating and, after durably publishing result 11, pause again before
exiting zero. Deterministic fixtures use private finite release barriers; the runnable
story may use finite demonstration delays. No installed source/fault hook or generic
incremental execution API is added.

Save exact source C/tree/binding/inputs/keep bytes and complete independent typed
closure. Prepare through existing `prepare_exchange`, creating new caller-owned W
and expected selection/token. Save the caller-owned handle independently:

```text
handle = ExchangeHandle(workspace=W, expected=prepared_spec)
```

The saved handle contains current workspace path/expected selection, not A's path,
process/PID authority, a future request occurrence or a permission to retry.
No request/attempt is created in A.

## 2. Start without waiting, with an explicit process owner

A finite application-owned supervisor holds the worker launch:

```text
launch = start_exchange(handle)  # returns after spawn, not computation
```

It launches one installed worker module consuming only W. Before spawn, exclusive
`launched` prevents repeat start; worker-side `started` still prevents repeat execute.
Normal start response proves only that this invocation obtained its live subprocess
object, not that B imported C, Q/T exist or the computational child started.

The initiating client can finish its submit interaction and exit because the separate
finite supervisor retains launch ownership. Fresh caller processes subsequently own
only the saved handle. The supervisor itself remains until it reaps the worker.
This is explicit example/application orchestration, not a persistent service or a
claim that an unowned background `Popen` can safely be discarded.

Rename A offline for worker execution; worker arguments contain no A path. After
validated input import under explicit B ref `work`, the worker publishes bootstrap
readiness before calling the unchanged local runner. B creates Q/T and P, not A.

## 3. First bounded observation: initial unknown attempt

Pause the child before arithmetic. A fresh caller process performs one observation:

```text
initial = observe_exchange(handle, packet=new_initial_packet)
```

It reads one coherent B storage snapshot, identifies the fresh Q/T relative to C,
selects P, closes B, exports pinned P and validates the full bundle/selected history
in disposable storage before publishing the immutable packet.

Expected description:

- `lifecycle == working`, `phase == initial`, selected commit P.
- `P.parents == (C,)`, preserved base tree plus exactly Q and initial T.
- Exact selected intent/binding/inputs and occurrence identifiers.
- Initial attempt has **no final status/outcome/cleanup**; unknown is not failure.
- Complete P packet, no process/liveness assertion and no A writes.

Then explicitly receive under `trial-initial`. A's `main` and sentinel remain unchanged;
source reservation/publication refs are absent. Repeated receive under that same ref
is idempotent/nonexecuting. Repeated observation selects the same recorded occurrence,
not another trial; a new packet directory may contain identical snapshot bytes.

Optional early observation before readiness/P returns `working/bootstrap` with no
occurrence/packet. An existing launch marker is not proof of dispatch or health.

## 4. Second bounded observation: publication is not final success

Release arithmetic; the child calculates/publishes R rooted in 11 and pauses before
exit. B's working ref is still P; its selected attempt publication ref now points to U.
One fresh observer reads both refs in the same storage transaction and selects U.

Expected:

- `lifecycle == working`, `phase == publication`, selected commit U.
- `U.parents == (P,)`, exact preserved P tree plus T-associated publication/R.
- Q/T are identical to the initial observation. T still has no final outcome.
- R is inspectable provisional publication, **not yet computational success**.

Receive U explicitly under `trial-publication`; keep `trial-initial` unchanged.
Independently move A's main to Cnew after preparation; neither worker nor observation/
receive restores it to C or adopts the returned history.

If the child instead exits nonzero after publication, final F retains R as **failure
evidence**, not success. Receiving the old U later still describes that selected
working snapshot, not the current final outcome.

## 5. Final bounded observation and process disposition

Release normal child exit. The unchanged runner reaps its direct child, attempts its
scratch cleanup and durably records F with computation/cleanup disposition.
An observer selects F and successfully exports/validates/publishes its complete packet:

- `lifecycle == done`, `phase == completion`, selected F.
- `F.parents == (P,U)` in that order; Q/T occurrences unchanged.
- Final attempt has `done`, successful zero-exit result R and separate cleanup report.
- R is the same DAG published at U, not recomputed/imported as another attempt.

This observation can succeed while outer execute is still exporting its ordinary
Iteration 6 output. It does not promise worker/supervisor exit or A import.
The finite supervisor separately waits/reaps its owned worker with bounded fixture/
example waits; it must not delete W while writers may remain.

Copy only final observation packet files to another test-owned directory. Close/rename
B offline; pass caller expected separately to a fresh receiver and import under
`trial-final`. No original input/source/live B/reservation refs are needed. Import
must not execute captured source or inspect/delete historical interpreter/scratch paths.
Ordinary Python and existing CLI inspection agree on P/U/F, occurrences, result/failure
and cleanup, while A's main remains Cnew.

Compare complete independent typed populations and every packed byte for C/P/U/F at
B, packets and returned A. All earlier snapshots/refs/bytes stay unchanged. CLI bounded
prefixes are presentation checks, not the complete closure oracle.

## 6. Repeat with a distinct fresh job and with failure

Use a different fresh workspace/B for the same pinned selection:

- New transport token, new Q2/T2; result R can deduplicate by content.
- First run's Q/T and explicit initial/publication/final refs remain unchanged.
- Repeated start/execute on either original workspace is rejected before another spawn.
- Repeated observe/receive invokes no computational process.

Run a captured nonzero child and a nonzero-after-publication child. Final observation
is `done` because failure/cleanup were recorded and history retrieved; outcome is
`failure`, result absent and optional R evidence separate. A narrow local cleanup-failure
fixture preserves successful R with `cleanup == failed`.

## 7. Interruption and negative stories

Use finite private barriers and fresh test-owned repositories:

1. Lose start response after actual spawn: supervisor still owns/reaps worker;
   retained handle can observe; start cannot launch another worker.
2. Stop before spawn after exclusive launch marker: no Q/T exists; observe stays
   working/bootstrap, and repeated start rejects. No automatic repair/marker clearing.
3. Pause/stop worker after P persistence before child spawn: initial unknown history
   stays inspectable, no failed/done rewrite and no execution retry.
4. Let child publish and exit, then stop worker before final persistence at a private
   **post-reaping** barrier: U remains evidence, final outcome unknown. This is not
   a test that kills a worker while its real child runs.
5. Stop after F persistence/direct-child reaping but before original completion receipt:
   explicit bounded observation retrieves recorded F without creating/finalizing T.
6. Stop initiating/observing client normally after one invocation; next fresh client
   observes from saved handle while supervisor owns the same worker.
7. Move live refs after coherent selection but before export: pinned selected bytes
   remain stable, and no mixed P/U association is fabricated.
8. Partial/mismatched/swapped token packets; correct generic bundles with wrong Q/T,
   phase, selection, tree or ordered history; malformed readiness/live B refs:
   reject before A writes. Entire A state/new-object absence is the oracle.
9. Late A different/malformed-ref, real map-full and consuming-commit failures after
   genuinely new earlier puts: full rollback. Precommit versus postcommit response
   loss distinguishes no batch from complete import; explicit repeat receive never runs T.
10. Export/profile or packet-write failure after recorded completion: preserve B;
    no successful done packet response, fabricated computational failure or new attempt.

Hard supervisor loss can orphan worker/descendants: report it as an unsupported
process-ownership guarantee, not as a passed cleanup test or automatic recovery case.
Test-owned supervisors reap every process they launch; cleanup removes only owned
scratch after known writer disposition. Live-user filesystem access is not a sandbox.
