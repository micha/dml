# Iteration 12 worked example: add, then consume its recorded result

Status: **reviewed bounded acceptance story; not executed, implementation GO pending**.
The user's “reviewed” checkpoint is recorded separately from implementation/delegation/publication.
Earlier candidate wording preserves preparation provenance; exact engineering spellings remain refinable.

Status at preparation: **agreed direction; candidate acceptance story, not executed or implementation GO**.
The user requested this worked example/handoff after agreeing to two-step composition.
[DESIGN.md](DESIGN.md) owns recommended mechanics; [HANDOFF.md](HANDOFF.md) owns evidence gates.
The code/field/ref spellings below are informative, not a newly implemented API or generic DAG
executor. DML remains unchanged at completed Iteration11 `640cabb`.

## 1. The intended computation and the recorded graph

Python orchestrates two separately requested steps, both actually executed in local Floci Batch:

```text
13 ─┐
    ├─ add Python ── R1(root42) ─┐
29 ─┘                          ├─ double Python ── R2(root84)
                             2 ┘
```

These arrows show the proposed numerical dependency, **not** new native operators. The recorded
references are ordinary DAGs, including an explicit producer occurrence/version:

```text
Successful summary E (root -> R2)
├── add    -> final attempt T1f
│            ├── request -> Q1
│            │             ├── intent: urn:example:add
│            │             ├── binding -> captured add source / local Python binding
│            │             └── inputs -> left13, right29, declared fixture arguments
│            ├── outcome -> success -> R1(root42)
│            └── cleanup -> separate disposition
├── double -> final attempt T2f
│            ├── request -> Q2
│            │             ├── intent: urn:example:double
│            │             ├── binding -> captured double source / local Python binding
│            │             └── inputs -> I2
│            │                           ├── value    -> R1
│            │                           ├── producer -> T1f   (same selected DAG)
│            │                           ├── factor: 2
│            │                           └── declared fixture arguments
│            ├── outcome -> success -> R2(root84)
│            └── cleanup -> separate disposition
└── result -> R2   (same node as E's root)
```

A snapshot is still a tree of DAGs, not one executable graph. `value`/`producer` are example-local
input names. Floci saved config/job/manifest association stays outside these native DAG roles,
as in Iteration11. The result and attempt references are graph edges; a commit ID string would
only be an annotation, not a native DAG-to-commit edge.

## 2. Prepare a bounded real fixture and caller history, after GO only

Use a fresh authorized private internal-bridge Floci fixture: pinned cached release/current
installed DML, no host ports/shared execution mounts, exact Batch/S3/CloudWatchLogs/IAM/no9169,
trusted local socket/private volume and one service attempt per job. Preserve all
[Iteration11 constraints](../11-floci-batch-execution/REVIEW.md), not its completed permissions.

A's basis C0 contains `add-binding`, `add-inputs`, `double-binding`, genuine unrelated prior
Q/T/publication history and composite-only children. Retain sentinel and every old reachable
packed byte. Inputs/source declare endpoint/bucket/distinct per-step finite S3 gates and any
runtime-artifact assertion data. The double source is standalone captured Python, not a source
import from the caller checkout. No prebuilt native add/multiply or Batch dependency scheduling.

Record two matching add requests Qa/Qb against the SAME C0/binding/inputs and one never-started
request. Execute Qa and Qb sequentially, naturally reap their jobs/clients; both produce42 but
have distinct Q/T/job IDs. Receive under `add-a-completion`/`add-b-completion`. Their result DAG
IDs should match; their final attempt DAG IDs should not. Keep all packets immutable.

This control prevents mistaking content identity for producer selection. Choose **Qa/Ta**, even
if Qb's F is newer/a deliberately moved convenience ref points at Qb. The selected immutable
packet/expected Qa—not a mutable latest ref or a number42—is the downstream basis.

## 3. Producer progress is not yet consumer eligibility

Before Qa's computation, fresh clients retrieve actual Pa. While its result is published but
its child remains gated, retrieve actual Ua with provisional42. Reobserve through clients that
exit. At both points inspect A and service requests: **no `double-inputs` basis, Q2, T2 or second
SubmitJob** has been created by polling. Consumer construction rejects P/U before A mutation.

Release the producer gate; retrieve validated Fa with computational success and separate cleanup.
Receive it under explicit producer ref. Before accepting Fa, make A/original prepared input
unavailable to the producer as in the existing story. Restore A only for explicit receive.

The fixture additionally establishes actual job/container/client disposition before launching
another job. This is bounded resource ownership, not a service-status definition of DML done.
A fully retrieved valid Fa may already be done before outer service status becomes terminal.

## 4. Build the result-backed input DAG and record Q2

The following shows the central proposed authoring pattern using **existing** public primitives.
It is an excerpt with preconditions, not a complete new library function. `first` is the owned
return of public `receive_observation` on the selected producer packet/independent expected;
A contains that exact F. Public packet validation and completion eligibility precede this
transaction; native result-shape checks inside it precede all puts. The example declares R1's
root must be a literal I64. Recommended success/cleanup-failure eligibility remains explicit
application policy in [DESIGN](DESIGN.md#4-eligibility-is-example-policy-not-a-new-adapter-lifecycle).

```python
import daggerml as d
from daggerml import exchange as ex

# Never infer these fields from a service status or an unvalidated description.
if (first.phase != "completion" or first.completion is None
        or first.lifecycle != "done" or first.completion.outcome != "success"):
    raise ValueError("selected producer is not a successful recorded completion")

with d.Repository(A) as repository, repository.write() as tx:
    producer_snapshot = tx.get_commit(first.commit)
    entries = dict(tx.get_tree(producer_snapshot.tree))
    if "double-inputs" in entries:
        raise ValueError("consumer input name already exists")

    result_dag = tx.get_dag(first.result)
    result_node = tx.get_node(result_dag.root)
    if (not isinstance(result_node, d.LiteralNode)
            or tx.get_datum(result_node.datum).kind != "i64"):
        raise ValueError("producer result does not meet this consumer's I64 contract")

    value_node = tx.put_subdag(first.result)
    producer_node = tx.put_subdag(first.completion.final_attempt)
    factor_node = tx.put_literal(tx.put_datum(2))
    double_inputs = tx.put_dag(
        root=value_node,
        bindings={
            "value": value_node,
            "producer": producer_node,
            "factor": factor_node,
            # endpoint/bucket/double-gate/artifact/exit-policy nodes also declared
        },
    )
    entries["double-inputs"] = double_inputs
    consumer_basis = tx.put_commit(tx.put_tree(entries), parents=(first.commit,))
    tx.create_ref("double-basis", consumer_basis)

# Repository handles are CLOSED before this separate deliberate Q mutation.
recorded = ex.record_exchange_request(
    A,
    commit=consumer_basis,
    binding_name="double-binding",
    inputs_name="double-inputs",
    intent_uri="urn:example:double",
    ref="submission-double",
)
expected2 = ex.prepare_exchange(
    A,
    commit=recorded.commit,
    request=recorded.request,
    binding_name=recorded.binding_name,
    inputs_name=recorded.inputs_name,
    intent_uri=recorded.intent_uri,
    worker_ref="work",
    workspace=fresh_consumer_input_directory,
)
```

C2 has exactly `(Fa,)` parents, preserves Fa's tree and adds only I2. Cq2 then has `(C2,)`
parents and adds only Q2. `main`, sentinel, Qa/Qb/never-started/producer refs remain unchanged.
C2 creation and Q2 recording are separate storage transactions; a Q2/file failure can leave an
inspectable consumer basis, not a fabricated whole-pipeline rollback or an implicit retry.

Construct a counterfactual I2b with every node identical except `producer -> Tb-final`:
R1a equals R1b, but I2a differs from I2b. No need to submit a second consumer to establish this
record-facet distinction. Inspect Q2 and assert its exact R1/Ta/factor2; no newest-result lookup.

## 5. Execute the consumer once, through unchanged Floci exchange

Use existing prepare/stage/submit/save/fresh bounded observe/receive. One fresh B2 imports Cq2's
complete all-parent closure, including selected Fa/Pa/Ua/Qa/Ta. It registers Q2 locally and
creates only T2; copying Ta is not another add attempt. No source operational refs or historical
scratch capabilities become runnable. The unselected Qb branch is retained in A, not implicitly
merged into C2/exported as a new selected dependency.

The consumer's numerical portion uses ordinary public lookup and data reads:

```python
from daggerml.local import child_context, publish_result

context = child_context()
with d.Repository(context.repository_path) as repository, repository.read() as tx:
    value_link = tx.get_node(tx.lookup_node(context.inputs, "value"))
    upstream = tx.get_dag(value_link.dag)  # requires SubDAGNode in real source
    value_node = tx.get_node(upstream.root)  # requires LiteralNode/I64
    value = tx.get_datum(value_node.datum).value
    factor_node = tx.get_node(tx.lookup_node(context.inputs, "factor"))
    factor = tx.get_datum(factor_node.datum).value  # requires I64

# Finite declared gates and exact type checks omitted from this numerical excerpt.
with d.Repository(context.repository_path) as repository, repository.write() as tx:
    answer = tx.put_literal(tx.put_datum(value * factor))
    publish_result(tx, context, tx.put_dag(root=answer, bindings={"result": answer}))
```

The actual new source checks types before calculation, validates/consumes declared endpoints/
keys, closes HTTP resources and has finite cooperative waits. `producer` remains an explicit
opaque occurrence witness; no duplicate private local-role decoder is installed in the child.

Submit client exits before the consumer initial gate. Fresh installed clients retrieve actual
P2, U2/root84 while gated, then F2/success/separate cleanup. All reflect exact Q2/I2/T2. Polling
and same-target imports never spawn/add T or mutate the stored histories. Compare full selected
B2/packet-validation/A bytes and every ordered parent, not only84 or job/status/digest claims.

## 6. Publish a nonexecuting successful summary and inspect offline

Stop the service only after independently proved owned writers/clients/job containers are gone;
archive required objects/packets/B/provenance first. Fresh installed receive uses copied complete
packets and independently saved expected selections only. Advance `main` separately, preserve
all producer/submission/request/sentinel refs and old bytes; no B refs copy. Return repeated
packets under same-target refs nonexecutingly; different-target refs conflict/abort.

Public validation of both selected completions and Q2/I2 associations precedes summary success.
In one A write transaction on pinned F2, preserve its tree and create E/S/explicit summary ref:

```python
with d.Repository(A) as repository, repository.write() as tx:
    entries = dict(tx.get_tree(tx.get_commit(second.commit).tree))
    if "experiment" in entries:
        raise ValueError("summary tree name already exists")
    result = tx.put_subdag(second.result)
    summary = tx.put_dag(root=result, bindings={
        "add": tx.put_subdag(first.completion.final_attempt),
        "double": tx.put_subdag(second.completion.final_attempt),
        "result": result,
    })
    entries["experiment"] = summary
    summary_commit = tx.put_commit(tx.put_tree(entries), parents=(second.commit,))
    tx.create_ref("experiment-result", summary_commit)
```

Tree/ref checks and owned response allocation belong inside the application transaction;
no moving-head selection or repeated dispatch is hidden in this helper. Display the chosen IDs
and use existing Python/CLI (finite presentation is not a full-object validity proof):

```sh
dml --json --repo /owned/story/A.dml snapshot --ref experiment-result
dml --json --repo /owned/story/A.dml walk <summary-dag-id> --limit 200
dml --json --repo /owned/story/A.dml lookup <consumer-input-dag-id> producer
dml --json --repo /owned/story/A.dml log --ref experiment-result --limit 100
```

Inspection follows selected Ta/Qa/input13,29 and T2/Q2/I2/R1/factor2/result84. Show that E's
root/result is a shared sub-DAG reference, not a literal84 hiding the computation. No extra
summary/visualization subsystem or native entity is implied.

## 7. Negative and uncertainty stories

Distinct fresh cases, with finite safe disposition/evidence:

- **P/U or missing F:** no C2/Q2/T2/consumer submit/summary. Service exit or evidence42 is insufficient.
- **Producer exits23 AFTER U:** F1 is done failure with evidence42/separate cleanup; driver stops,
  no downstream Q2 or invented failed T2. Do not launch to make the experiment look complete.
- **Wrong matching producer:** complete other-Q packet claiming expected first transport fields
  rejects before authoring A; independently valid alternate selection produces a DIFFERENT
  I2 witness, never silent interchangeability. A malformed consumer association/summary is not
  accepted just because output remains84.
- **Wrong result shape:** valid producer success whose root is not I64 remains producer success,
  but is rejected by this consumer's contract before downstream request/dispatch.
- **Consumer exits23 AFTER U2:** F2 records failure with evidence84; first success remains intact,
  no successful experiment-result summary. New request/attempt only if user explicitly asks.
- **Authoring/ref/map/commit/IO loss:** meaningful genuinely new actual-A puts then late basis/
  summary ref/commit failure abort the whole local batch; postcommit lost response can leave a
  complete basis/summary. Q2 recording has its own existing atomic boundary. No automatic rewrite,
  ref repair/map growth/request duplication/resubmit to recover a missing acknowledgement.

These tests inspect recorded dependency/selection and trusted source behavior. They do not prove
undeclared environmental capture, hostile-code safety, scientific correctness or global exactly-once.
No fault experiment sacrifices a live computational child or uses an installed test hook.

## 8. Deliverable and stop

A small maintained Python driver/trusted consumer source, focused default-safe tests and a
mandatory actual installed local two-step gate; small authoring helpers only where justified.
Retain qualification of normal versus private/host/installed evidence and Iteration11's old
Windows unknown failures. Stop after the separately authorized bounded turn/publication gates,
not by treating this planning document as GO.
