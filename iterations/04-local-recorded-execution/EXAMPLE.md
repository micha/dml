# Iteration 4 worked example: addition, failure and interruption

Status: informative acceptance story prepared before implementation, subsequently
used for the user-authorized bounded turn. See [RESULTS.md](RESULTS.md) and
[REVIEW.md](REVIEW.md) for actual implementation/evidence; illustrative candidate
APIs below are planning provenance, not the owning as-built contract.
[DESIGN.md](DESIGN.md) owns proposed semantics; [HANDOFF.md](HANDOFF.md) owns the
implementation/evidence plan. Nothing here was executed during preparation.

## 1. Inputs and explicit binding

Create a fresh local repository with an initial tree/commit and an explicitly named
head ref. Build an inputs DAG with literal nodes `left = 4` and `right = 7`; choose
one of those nodes as root. The names are scoped arguments under this adapter
contract, not global primitives or a complete list of environmental dependencies.

Capture a small Python entry script as BYTES in a declared local binding DAG. Record
an explicit interpreter path, one adapter contract URI and timeout configuration.
The intent URI is illustratively `urn:example:add-i64`. Capture/execution of that
entry file does not capture its imported Python/DML runtime or arbitrary environment.

Candidate child source, using proposed helpers (not a working API today):

```python
import daggerml as dml
from daggerml.local import child_context, publish_result

ctx = child_context()
with dml.Repository(ctx.repository_path) as repo:
    with repo.write() as tx:
        left_node = tx.get_node(tx.lookup_node(ctx.inputs, "left"))
        right_node = tx.get_node(tx.lookup_node(ctx.inputs, "right"))
        left = tx.get_datum(left_node.datum)
        right = tx.get_datum(right_node.datum)
        if left.kind != "i64" or right.kind != "i64":
            raise ValueError("addition requires recorded I64 arguments")
        # Python performs the arithmetic. C enforces recorded I64 range.
        value = tx.put_datum(left.value + right.value)
        result_node = tx.put_literal(value)
        result = tx.put_dag(root=result_node, bindings={"result": result_node})
        publish_result(tx, ctx, result)
```

The child opens its own handle and explicitly reads the pinned input DAG. Result
objects, publication DAG/commit and attempt ref update commit in one transaction.
The parent holds no open transaction or repository handle while waiting.

## 2. Two matching fresh requests

Run the step twice, deliberately starting two subprocesses with the same binding
and inputs, no reuse. Candidate orchestration surface:

```python
from daggerml.local import run_step

first = run_step(repository_path, head_ref="main", intent_uri=intent_uri,
                 binding=binding_id, inputs=inputs_id)
second = run_step(repository_path, head_ref="main", intent_uri=intent_uri,
                  binding=binding_id, inputs=inputs_id)

assert first.request_id != second.request_id
assert first.attempt_id != second.attempt_id
assert first.result == second.result
```

Both result DAGs are rooted in 11. Equality of result content does not collapse the
two request/attempt occurrences or prove independence beyond the two launches
observed by this local driver. The computation still relies on uncaptured runtime
conditions and the researcher's implementation.

For each request, inspect:

1. Pre-dispatch commit containing the request/initial-attempt definitions, declared
   binding and named inputs; no outcome and no adapter status yet.
2. Child publication ref/commit associating that attempt with its result DAG.
3. Completion commit containing a new description of the same attempt occurrence,
   `done`, success outcome and separate cleanup disposition.
4. Parent links preserving both pre-dispatch and publication history; earlier bytes
   remain unchanged as the orchestration head moves.

Root request/attempt literals identify occurrences. All ordinary result content is
shared normally; no occurrence identifier is smuggled into the result DAG.

## 3. Failure

Use a **new request/binding** for a child script that raises an intentional exception.
A different source is not a retry with secretly changed implementation. Verify that:

- Its request and attempt are recorded before launching.
- The final description refers to that same attempt ID and records adapter-contract
  failure, nonzero exit, bounded diagnostics and cleanup disposition.
- `done` means the outcome/disposition was recorded, not computational success.
- Earlier successful results and attempts remain intact.

Additional boundary fixtures: launch failure, zero exit with no publication, wrong
attempt association, publication followed by nonzero exit, direct-child timeout,
cleanup failure and completion-transaction failure. Preserve a valid published DAG
as evidence even if the overall local adapter contract fails; do not adopt it as a
successful result or silently drop its history.

## 4. Interrupted request and retry

Use a deterministic test barrier immediately after the pre-dispatch commit and
before process launch, then terminate the parent process. A fresh reader verifies:

- The request and initial attempt exist and preserve their explicit binding/inputs.
- There is no final outcome/status. This means **unknown**, not recorded failure.
- No child launch was observed by the test harness in this particular pre-launch
  fixture; the record shape alone does not prove that for arbitrary interruptions.

Explicitly retry that recorded request, keeping the exact original binding/inputs.
The proposed `retry_step` creates a new attempt linked to the same request, executes
once, and records its final outcome. The interrupted attempt is neither overwritten
nor dispatched again. No automatic recovery, cache lookup or exactly-once claim.

Also terminate a parent after a child has durably published but before finalization.
The initial attempt remains without final status, while its child ref/history exposes
the published result. The test harness must clean up its own scratch/children;
this does not demonstrate a production process-recovery or cleanup service.

## 5. Ordinary inspection

No new execution CLI command or observer integration is required. Use existing:

```sh
dml --json --repo execution.dml snapshot --ref main
dml --json --repo execution.dml snapshot --commit <pre-dispatch-commit>
dml --json --repo execution.dml walk <request-dag> --limit 100
dml --json --repo execution.dml walk <final-attempt-dag> --limit 100
dml --json --repo execution.dml ref get <attempt-publication-ref>
dml --json --repo execution.dml log --ref main
```

Follow names/IDs explicitly. `walk` shows recorded structure, not process execution
or a time-ordered activity log. A bounded prefix is not a completeness proof.
Fresh Python readers compare saved bytes and independently count request/attempt
occurrences. Installed parent and child processes should also exercise this workflow
outside the source checkout, with the selected installed interpreter.
