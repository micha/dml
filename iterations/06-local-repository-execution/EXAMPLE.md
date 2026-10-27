# Iteration 6 worked example: A → B → A

Status: informative acceptance story for the user-approved bounded plan, **not
executed during preparation**. Approval does not authorize implementation/delegation;
illustrative APIs and provisional details are not as-built contracts.
[DESIGN.md](DESIGN.md) owns candidate semantics; [HANDOFF.md](HANDOFF.md) owns work
order and assurance.

## 1. Prepare the caller snapshot

Use a fresh test-owned repository A. Through existing public APIs create:

- Named I64 input nodes `left = 4`, `right = 7`, exposed by an input DAG.
- A local binding capturing the existing trusted
  [addition source](../../../dml/examples/local_add.py), explicit installed Python
  interpreter and finite binding timeout.
- Tree entries illustratively `binding` and `inputs`, plus an unrelated retained
  research DAG `keep`. Commit **C** contains that tree; `main` points to C.

Save exact C/tree/binding/input/keep bytes. Add a genuinely unrelated branch-only
sentinel under another ref so closure transfer can be distinguished from a store copy.
No request/attempt is created in A by preparing the exchange.

## 2. First workspace and independent worker

Illustrative proposed calls, not existing APIs:

```python
from daggerml.exchange import prepare_exchange, receive_exchange

expected = prepare_exchange(
    caller_path,
    commit=C,
    binding_name="binding",
    inputs_name="inputs",
    intent_uri="urn:example:add-i64",
    worker_ref="work",
    workspace=first_workspace,
)
```

Preparation closes A and writes the pinned input bundle and selection descriptor
with a fresh transport-only exchange token in a newly created caller-owned workspace.
It does not execute source or create a DML request/attempt/change refs.
The caller then starts a fresh installed Python process through the maintained
example's `--worker` mode; that process invokes `execute_exchange(workspace)`.
Its arguments/files contain **no A path**. All A handles remain closed.

In a fixture, temporarily rename A away before worker launch and restore it afterward.
B is created at the fixed workspace-relative path, imports C under explicit `work`,
and validates pinned selection before calling existing `run_step`. Computation uses
B, not A or the caller's source filename. Captured entry bytes are what execute;
mutable external imports/environment are not thereby captured.

B creates request **Q1** and attempt **T1**, then initial commit **P1**, child
publication **U1** and final commit **F1**. Completion retains ordered parents
`(P1, U1)` and ordinary success/result/cleanup DAGs. Result **R** is rooted in 11.
The worker exports F1's full history and publishes the bounded completion descriptor
last. The worker is reaped before normal caller receive.

A's restored `main` still points to C. Worker execution has not created a request
in A or copied mutable refs across repositories.

## 3. Receive without adopting or merging

```python
received = receive_exchange(
    caller_path, workspace=first_workspace, expected=expected, ref="trial-1"
)
```

Receive checks the packet against the caller's independent expected selection and
validates the selected computation/history in a helper-owned temporary repository.
Only afterward does it atomically import the output bundle into A under `trial-1`.
It returns owned recorded-outcome information, not a runnable B context.

For a fresh-process receive proof, copy only `job.json`, `completion.json` and
`output.bundle` to a second test-owned directory; pass expected selection separately.
Close/rename B away. Receiver must not need B, input bundle, original entry source,
worker reservation refs or B's historical scratch. This packet copy is ordinary
caller file handling, not a new package transport API.

Ordinary reads in A verify:

1. `main == C` and `trial-1 == F1`; no replacement DML commit was constructed.
2. Every typed record byte reachable from F1 equals an independent B oracle.
3. `P1.parents == (C,)` and `F1.parents == (P1, U1)` in that order.
4. Q1/T1 occurrence strings, request binding/inputs/intent, initial/final attempt
   association, success/result and separate cleanup disposition match B.
5. Initial attempt has no final status; final attempt has `done` and result R.
6. Existing A records, `keep` entry/ref state and unrelated branch remain unchanged.
7. B's `work`, request reservation and attempt publication refs were not copied;
   their stored name/path strings remain data.
8. No result source ran during receive/inspection and no historical path was removed.

If A's `main` moves to a later commit **Cnew** through an independent caller action
between prepare and receive, worker inputs still come from C and receive preserves
`main == Cnew`. The helper does not restore the old head or adopt F1.

## 4. Second fresh workspace, same result

Prepare the same pinned C into a **different fresh workspace/B2**. Execute once
and receive under `trial-2`. Expected outcome:

- Q2 differs from Q1; T2 differs from T1.
- Binding/input IDs are unchanged; result R is shared by content.
- `trial-1` and its original history remain unchanged.
- `main` remains at whichever commit the caller independently selected.

Copying/importing T1 is not T2. Repeating **receive** for the first packet/ref is
idempotent and starts no process. Repeating **execute** in the first workspace is
rejected by the one-shot marker; the fixture verifies no second child launch/new
occurrence. A new workspace is fresh execution, not an automatic retry of Q1.

## 5. Recorded failure is still a valid return

Create a new captured binding in a separate caller commit that raises an exception
or exits nonzero. Prepare a fresh workspace and receive its final history under
`trial-failed`.

The worker driver completes normally because `run_step` durably recorded the
computational failure. Receive succeeds as exchange, while its recorded computation
outcome is `failure`. It must not manufacture a result of 11 or discard reason/detail,
optional evidence or separate cleanup failure. An additional narrow cleanup-failure
fixture can preserve successful result R together with `cleanup == failed`.

This distinguishes a failing computational child from a worker driver that could
not bootstrap, finalize or publish a trustworthy packet.

## 6. Ordinary inspection

With existing installed CLI, no new execution/transfer command:

```sh
dml --json --repo caller.dml ref get main
dml --json --repo caller.dml ref get trial-1
dml --json --repo caller.dml snapshot --ref trial-1
dml --json --repo caller.dml snapshot --commit <P1>
dml --json --repo caller.dml walk <final-attempt-T1> --limit 100
dml --json --repo caller.dml show dag <R>
dml --json --repo caller.dml log --ref trial-1
```

Compare complete ordered history through Python; bounded CLI output is not the
full-population oracle. The return ref is explicit navigation, not merge/adoption.

## 7. Negative and deterministic interruption stories

Use separate test-owned fixtures and finite process/barrier deadlines:

- Invalid/missing input selection, corrupt input bundle or B import/map-full failure:
  no computational child launch. A stays unchanged; workspace artifacts can remain.
- Repeated execute or preexisting B/output collision: reject, never resume/overwrite.
- Stop worker after initial attempt persistence **before child launch**: B retains
  unknown T1, no completion packet is fabricated and A receives nothing. Marker
  prevents another automatic execution in that workspace.
- Stop worker after real child reaping and F1 storage commit **before packet publication**:
  B has `done` although A has no returned outcome. File failure/export-profile overflow
  has the same knowledge distinction; no silent rerun or `failure` rewrite.
- Stop caller after worker completion before receive: B/packet remain; A unchanged.
  Explicit receive later starts no computation.
- Wrong receipt token/root/base/occurrence, a swapped packet from an otherwise-identical
  second workspace, valid wrong-selection bundle, swapped result/evidence,
  malformed typed role/history/parents or truncated files: selected-completion validation
  fails **before any A write**, not after publishing a bad ref.
- Different or malformed A return ref, genuine small-map late import failure and
  consuming storage-commit fault: B's completed history remains valid; earlier new
  A objects/ref roll back together. Preserve A's existing main/sentinel.
- Stop receiver after earlier puts **before A commit** versus **after real A commit
  before return**. Fresh readers distinguish old state from complete imported history.
  Missing acknowledgement is not failed computation or guaranteed rollback; repeating
  receive is safe and never executes again.

Every real interruption test finally reaps owned processes and removes only test-owned
scratch after proving no writers remain. Portable direct-worker termination is not
process-tree/power-loss assurance. Unknown B progress may be inspected manually, but
no reconciliation/retry/resume feature is introduced by the example.
