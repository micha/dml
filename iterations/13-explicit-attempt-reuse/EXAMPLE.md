# Iteration 13 worked example: ask again, reuse explicitly, then execute fresh

Status: **reviewed bounded acceptance story; not executed, implementation GO pending**.
The user's “reviewed” checkpoint is separate from implementation/delegation/publication.
Earlier candidate wording preserves preparation provenance; exact engineering spellings remain refinable.

Status at preparation: **candidate acceptance story; direction agreed, not executed or implementation GO**.
[DESIGN](DESIGN.md) owns candidate mechanics; [HANDOFF](HANDOFF.md) owns work/review gates.
Exact names/signatures are informative. Planning leaves DML clean66311fc and worker stopped.

## 1. Original genuinely executed chain

Start with a current installed, recorded chain using existing composition/public execution:

```text
13,29 -> Q1 / T1 -> R1(root42)
R1, producer T1f, factor2 -> Q2 / T2 -> R2(root84)
```

Q2 selects the captured double binding and complete input DAG I2. Obtain immutable F2 packet
and independently saved expected Cq2/Q2; publicly validate and receive F2 into A. Preserve
prior genuine Q/T/publication history, composite-only children and independent sentinel/head.
Both actual jobs/clients naturally finish before fixture endpoint stop/archive. Existing
recorded request/attempt/computation/cleanup fields and packets remain byte-identical.

## 2. Record another request without another computation

With service/input/B unavailable, explicitly choose T2f from that packet/independent expected.
Use pinned F2 (or a later ordinary snapshot retaining it) as basis. The reuse operation:

1. Publicly validates successful F2 and checks intent/binding/full I2 matching before new Q.
2. Records **new Q3/Cq3** through existing explicit caller request recording.
3. Separately publishes W3/Cr3 under explicit `reused-double` ref.

```text
W3 (root/result -> R2)
├── role: example-explicit-reuse-v1
├── request -> Q3 (NEW occurrence)
├── attempt -> T2f (OLD selected final attempt)
│               └── request -> Q2 (ORIGINAL occurrence)
└── result -> R2 (actual old sub-DAG84)
```

Recommended commit spine (arrows are parent references, not data flow):

```text
Cq3 -> F2
Cr3 -> Cq3
```

Cq3 preserves F2's tree and adds only Q3; Cr3 preserves Cq3 and adds only W3. New submission
and request reservation refs stay at Cq3, reuse-result ref points Cr3. Other heads/refs/bytes
stay unchanged. There is **no T3, B3, external job, source execution or reconstructed literal84**.
The request count increases, the distinct attempt/empirical-trial count does not.

Offline fresh installed clients and ordinary CLI navigate W3/Q3/T2f/Q2/I2 and R2. No source,
historical interpreter/scratch, live service or moving convenience ref is needed. Reinspection/
packet import does not create additional Q/T/W history. Repeating authoring under an existing
submission/ref rejects; no idempotent whole-driver/exactly-once claim.

## 3. Deliberately execute fresh

Separately record Q4 on Cr3 (or another explicit retained snapshot), selecting exactly the same
intent, binding and I2. Prepare/submit through the existing adapter, only by this explicit action.
One real fresh Batch job registers Q4 and creates T4; imported W3/Q3/T2f remain inert history.
Fresh bounded clients retrieve P4/U4/F4 and explicitly receive full selected history in A.

Require:

- Q3, Q4 and original Q2 are distinct request occurrences.
- T4 and T2 are distinct attempts; there is still NO attempt created for Q3 by reuse.
- R4 may equal R2 in content/root84; the equality does not merge their producing trials.
- W3 still references T2f, not T4f. No automatic reuse adoption/default update occurs.
- F4 carries W3 and the original full producer/consumer history unchanged.

The finite fixture may explicitly resume its previously proven-stopped endpoint before Q4's
job, with controlled declared gate keys reset only after known writer disposition. This is not
a DML resume/recovery mechanism; no original computation is relaunched. Expected actual count:
**one add, one original double, one explicitly fresh double = three jobs**, no fourth reuse job.

## 4. Selection controls

Use complete valid old selections, not only absent IDs or malformed descriptors:

- Different intent URI rejects despite same binding/inputs/result84.
- Different source/interpreter/timeout binding ID rejects under initial full matching.
- Different factor/type/declared fixture data or producer witness changes I2 and rejects.
- Another producer returning42 is not a substitute for the exact selected T1f input witness.
- A valid alternate successful double with identical three dimensions can be explicitly
  selected, but W must reference that exact chosen final attempt; a forged equal-result
  association cannot masquerade as the caller's selected one.
- P/U, unknown/missing F and producer failure with evidence84 do not authorize reuse/new Q.
  Public flags/dataclasses and service status cannot manufacture success.
- Successful computation with recorded cleanup failure remains a success; test the explicit
  example policy permitting reuse while retaining that disposition, never repairing cleanup.

Inspect complete typed objects/ordered parents and request/attempt populations. HTTP/job census
and bounded CLI are supplemental, not full-history/correctness proof.

## 5. Persistence and uncertainty

Mismatched/ineligible historical selection rejects before Q3 publication. Inject meaningful
reuse-publication failures only after genuinely new actual-A W/tree/commit puts/readback:
late raw/different ref, consuming store-commit failure, real map-full and response allocation.
The W/Cr/ref transaction rolls back wholly; **previously committed Q3 remains**.

Actual authoring-only pre/post-store-commit barriers distinguish no W batch versus complete
W/Cr/ref despite missing response. There is no computational child to sacrifice. Q3 and W
publication are separate transactions: errors do not imply whole-operation rollback, authorize
another Q or initiate fallback execution. Unknown/pending satisfaction remains inspectable.

## 6. Deliverable

A small maintained example-local explicit reuse operation/finite modes, focused default-safe
native tests, actual installed original/fresh control with service-offline fresh reuse/inspection,
and informative documentation through existing authorities. New shared/public helpers need
concrete evidence/review; no private role decoder, generic cache/scheduler/facet engine or new
native entity is presumed. Separate plan review and bounded implementation GO remain required.
