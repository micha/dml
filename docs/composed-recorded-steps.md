# Composing two recorded steps

Status: informative, implemented application example over existing public APIs.

## Authority boundary

This page owns the conventions of [composed_execution.py](../examples/composed_execution.py)
and its standalone trusted [floci_double.py](../examples/floci_double.py) consumer. It is not
an executable-DAG schema, evaluator, scheduler or public composition framework. Python
chooses the order. Native structure/transactions remain owned by the
[Python API](spec-next/python-api.md) and [objects](spec-next/objects.md); exact caller Q,
packet validation, transfer and Floci behavior remain owned by
[caller requests](spec-next/caller-requests.md),
[asynchronous exchange](spec-next/asynchronous-execution.md),
[transfer](spec-next/transfer.md) and [Floci](spec-next/floci-execution.md).

## Recorded dependency and explicit selection

The example computes `13 + 29 = 42`, then supplies the **actual result sub-DAG** to
another recorded step that multiplies its literal I64 root by2. Consumer inputs contain:

- `value`: sub-DAG node referencing the selected producer result R1; also the input root.
- `producer`: sub-DAG node referencing that SAME selected final attempt T1f.
- `factor`: literal I64 two.
- `endpoint`, `bucket`, `gate`, `exit-code`, `artifacts`: declared finite example inputs.

Two fresh producer attempts can share R1 while T1f differs. Holding all other nodes fixed,
changing only the witness changes the full-record input DAG ID. This is not a reuse facet
or an independent scientific-validity/capture guarantee. A mutable latest ref, numeric42,
external job ID or historical scratch string never selects the producing occurrence.

Authoring takes immutable packet files plus independently saved expected Cq/Q selections.
It calls public packet validation itself; forgeable received dataclasses/flags are not
validation authority. The SAME owned validated description supplies F1/R1/T1f. F1 must
already be received in A. P/U, unknown/missing/unreturnable F, recorded failure with evidence42
and a non-I64 result cannot publish consumer basis/request or cause dispatch. A nonnumeric
producer success stays a producer success, unsuitable only for this consumer. This example
allows computational success with **recorded cleanup failure**, preserving its history;
fixture launches separately require known writer disposition.

One A transaction preserves pinned F1's tree, adds only `double-inputs`, creates C2 with
parents exactly `(F1,)` and absent `double-basis` ref, allocating the response before commit.
The caller then deliberately invokes existing request recording for Q2/Cq2 in a SEPARATE
transaction. Files, staging, submit, service effects and summary are not atomic with either.
No automatic re-recording/resubmission repairs a missing response.

Before successful summary, both selected packets are publicly validated and Q2's selected
inputs must have exact R1/T1f/factor2/root/shape/types. C2 must retain the exact producer tree
plus I2 and be parented by F1. Equal84 cannot hide a swapped producer/value/factor. A valid
alternative selection is allowed as a different explicit input, not silent interchangeability.

Summary E has root/`result` referencing R2, `add` referencing T1f and `double` referencing T2f.
One transaction preserves F2's tree, adds only `experiment`, creates S parented by `(F2,)`
and absent `experiment-result` ref. It executes nothing. A failed consumer can retain U84/
F failure/evidence/cleanup and producer history, but produces no successful summary. Create-only
name/ref collisions reject, including repeated authoring; packet same-target reception remains
nonexecuting/idempotent under its owning contract.

## Finite runnable modes

Supply preprovisioned trusted explicit `FlociRemote` operational JSON and current installed
runtime. Provisioning, finite declared gate release, resource-disposition waits and polling
order are application/fixture policy, not hidden inside these modes:

```sh
python examples/composed_execution.py init A.dml remote.json \
  examples/floci_add.py examples/floci_double.py gates/add
# Use the printed immutable C0 ID:
python examples/composed_execution.py request A.dml add-step remote.json \
  <C0> add-binding add-inputs urn:example:add submission-add
python examples/composed_execution.py submit add-step
python examples/composed_execution.py observe add-step/saved new-add-packet
# Receive through the existing public explicit-ref mode (service may be offline):
python examples/floci_execution.py receive A.dml add-step/saved \
  final-add-packet add-completion
python examples/composed_execution.py basis A.dml add-step/saved \
  final-add-packet remote.json gates/double
# Use the printed C2 ID; this deliberately records Q2 separately:
python examples/composed_execution.py request A.dml double-step remote.json \
  <C2> double-binding double-inputs urn:example:double submission-double
python examples/composed_execution.py submit double-step
python examples/composed_execution.py observe double-step/saved new-double-packet
python examples/floci_execution.py receive A.dml double-step/saved \
  final-double-packet double-completion
python examples/composed_execution.py summary A.dml add-step/saved \
  final-add-packet double-step/saved final-double-packet
```

Every workspace/packet is new; calls do not implicitly resume, wait until done, release gates,
retry or progress to another mode. Each observation is bounded; the caller chooses repetition.
Do not submit double from a publication packet merely showing42. `init` records sources as bytes
and both bindings before computation; those sources are deliberately trusted, not sandboxed.
Necessary standalone consumer code imports installed DML/stdlib only, never uninstalled example
helpers/private role decoders. Artifact assertion bytes can be supplied to the basis helper by
a controlled application; they do not capture the whole environment.

Existing [inspection CLI](spec-next/cli.md) can navigate E → T2/Q2/I2 → R1/T1/Q1/input13,29:

```sh
dml --json --repo A.dml snapshot --ref experiment-result
dml --json --repo A.dml walk <summary-dag> --limit 200
dml --json --repo A.dml lookup <consumer-input-dag> producer
dml --json --repo A.dml log --ref experiment-result --limit 100
```

Bounded CLI output is not an exhaustive integrity proof. The computational DAG and ordered
commit parents remain different graphs. Input/summary/producer roles are ordinary DAGs,
not additional LMDB entity types.

## Explicitly asking again

The separate [explicit attempt-reuse example](explicit-attempt-reuse.md) can record a new
request satisfied using a selected old successful double attempt/result, without another
attempt/job. It compares exact intent/binding/full inputs, including this example's producer
witness. A deliberate fresh double remains a separate request/dispatch on retained W history;
these conventions do not alter this page's composition or execution authorities.

## Evidence and limits

[Focused native tests](../tests/python/test_composed_execution.py),
[authoring rollback/loss](../tests/python/test_composed_atomicity.py),
[standalone child](../tests/python/test_composed_child.py) and
[finite modes](../tests/python/test_composed_modes.py) run without Docker. The explicit
[installed fixture](../tests/floci/README.md) exercises two matching producers/selected earlier
witness/actual standalone consumer, producer and consumer failure after publication, complete
native bytes/parents and fresh installed endpoint-offline reception. Its private post-reap
final-B retention is separate from normal ephemeral-container behavior.

Host statements are not installed-process/branch/platform coverage. Retained native/memory
thresholds and exclusions remain unchanged. Missing acknowledgements can leave complete
publication despite no response; authoring-only pre/postcommit interruptions do not prove
power-loss durability or whole-workflow exactly-once execution. No automatic scheduler,
recovery/retry/reuse/resource manager/cloud/AWS SDK/authentication or scientific certification.
Floci-specific unsigned/socket/security/ephemeral-B/profile/full-capture qualifications remain
in the owning contract. Actual commands/counts/original failed oracles/fixture disposition and
independent review are recorded in
[Iteration12 RESULTS](../../dml-design/iterations/12-composed-recorded-steps/RESULTS.md) and
[REVIEW](../../dml-design/iterations/12-composed-recorded-steps/REVIEW.md).
