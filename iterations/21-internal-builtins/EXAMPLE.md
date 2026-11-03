# Iteration 21 worked example: common node calls and retained built-in versions

Status: **bounded example reviewed; NOT executed; separate implementation GO required**.
The user's “reviewed” records plan review, not execution/delegation/publication permission.
Exact engineering spellings remain refinable.
Read [DESIGN](DESIGN.md) and [HANDOFF](HANDOFF.md). IDs, API sketches and exact names are
illustrative. This starts no worker/build/install/computation/CI/publication.

## 1. Setup

Recommend ONE caller repository A and two fresh synchronous-local workspaces/B stores, using a
fresh isolated install of the future current source. This install contains the new URI-reference
behavior and installed built-in module, not checkout PYTHONPATH or the old cached20 runtime.
All bindings/choices/literals/argument construction/control operations create ZERO Q/T.

Store exact built-in bindings with NULL adapter/interpreter/timeout and these source URI datums:

```text
empty-v1  -> dml://source/builtin/map/empty/v1
insert-v1 -> dml://source/builtin/map/insert/v1
get-v1    -> dml://source/builtin/map/get/v1
get-v2    -> dml://source/builtin/map/get/v2
index-v1  -> dml://source/builtin/list/get/v1
```

The installed release ships ALL five exact handlers. Initially map/get's ordinary versioned choice
contains both bindings and default=v1. The v1/v2 map-get implementations have distinct entrypoints/
lookup algorithms and the same defined semantics. This is not a benchmark or correctness-fix story.

Capture two normal sum-pair local-Python bindings in advance: one wrapper pins get-v1, one get-v2;
both pin index-v1. Each imports installed DML, validates its pinned input node, supplies a value-
oriented argument-node/operation interface to sum_pair, and returns a normal result sub-DAG through
unchanged local publication. Capture selected immutable builtin binding references/configuration
in the normal binding source bytes, not a latest-ref lookup during child execution. Basis contains
all supporting bindings. The example maps map/get choice=v1/v2 to the corresponding captured normal
binding, with explicit declaration/revalidation before Q. This is bounded application wiring, not
new generic closure resolution or implicit source analysis.

Illustrative logical implementation, NOT current API:

```python
def sum_pair(args, ops):
    sample = ops.map_get(args, "sample")
    measurements = ops.map_get(sample, "measurements")
    left = ops.list_get(measurements, 0)
    right = ops.list_get(measurements, 1)
    a, b = left.value, right.value  # copied Datum values, NOT graph/source access
    if a.kind != "i64" or b.kind != "i64":
        raise ValueError("sum_pair requires I64 measurements")
    return ops.literal(Datum.i64(a.value + b.value))  # explicit returned NODE
```

Each convenience uses actual URI-bound execution with its OWN argument-map node. For example:

```text
ops.map_get(sample, "measurements")
  prepare arguments node:
    value MAP { "map": sample.value, "key": STRING("measurements") }
    source edges: sample node, actual key literal node
  invoke dml://builtin/map/get with exact get-v1 or get-v2 binding
  return primitive operation node with LIST datum value
```

The recorder retains source links and concrete binding; the func gets no public source IDs/refs/
repository handle. Equal collection values from two sources do not choose an arbitrary origin.
The implementation returns an owned node; trusted wrapping supplies the explicit normal result
sub-DAG/returned-node/value/ordered trace/actual Q contract, not an arbitrary root scalar extractor.

## 2. Construct nested arguments A and execute Q1

Explicit pinned source DAG A has a named literal LIST[I64(13), I64(29)]. Materialize native children
through trusted authoring and preserve exact source selection. No list-constructor func is added.

Use actual built-in empty/insert through standard argument nodes, not hand-forged opcode rows:

```text
E_A = call(map/empty, empty-v1, arguments({}))
S_A = call(map/insert, insert-v1,
           arguments({ map: E_A, key: literal("measurements"), value: list_source_A }))
I_A = arguments({ sample: S_A })
```

I_A is an argument-map NODE, value `{sample: {measurements: [13,29]}}`. Its argument preparation
DAG is the exact full Q inputs. Preparation uses a native bootstrap recorder, not recursive builtin
calls to prepare those builtin calls. The two actual construction calls have an ordered metadata
ledger/root retained in caller history; this is no computational attempt.

Q1 explicitly selects normal sum-pair binding/get-v1. New local T1 executes sum_pair, four actual
nested builtin calls: get sample, get measurements, list index0, list index1. Returned normal
result-sub-DAG node has I64(42) value and trace pinned to Q1/full I_A/exact bindings.

Direct child known exit0/reaped BEFORE observe/receive. Public successful F1/S1 supplies owning
Q1/T1/R1 authority. Explicitly capture S1 in ONE known slot `selected-sum-pair`; this records no Q/T
and changes no default automatically. Source/recorded values alone are not success authority.

## 3. Promote v2, construct equal values B, reuse Q2

Explicitly publish a new choice snapshot with default=v2, preserving old choice/v1/v2 bindings and
other tree entries. No implementation is overwritten and no request/job runs during promotion.

Source DAG B declares the same LIST[13,29] but has different native DAG identity/source metadata.
Its strict literal source descriptor differs from A's. Build E_B/S_B/I_B with the same two actual
empty/insert calls and ordinary argument preparation. Assert native identities:

```text
value(I_A) datum ID == value(I_B) datum ID
I_A source/argument node record identity != I_B identity
full Q inputs A != full Q inputs B
```

Q2 explicitly records requested normal binding/get-v2 and full I_B/choice-v2. The new example-local
reader/decision publicly validates S1's original success, full I_A and normal result/primitive trace,
then compares sum-pair intent + full argument MAP datum. W2 associates NEW own Q2 with OLD T1/R1.

No new T, sum_pair invocation, four nested getters or Q2 completion packet. Input preparation's two
empty/insert calls happened before Q2 and remain metadata construction; they are not fabricated
execution of sum_pair. Reader exposes requested B/get-v2 separately from executed A/get-v1/old trace.
No automatic re-execution, adoption or cache discovery is introduced.

## 4. Changed values C, Q3 pending miss then fresh43

Source C has LIST[13,30]. Two actual empty/insert calls prepare E_C/S_C and argument node I_C.
Its MAP datum differs from A/B. Valid S1 does not match; new own Q3 remains explicitly pending
fresh with no-entry/value-mismatch reason BEFORE dispatch. Separate local T2 runs the get-v2 normal
binding, four actual getters, and returns I64(43) in its normal result sub-DAG. Public F3/S3 validates
success. Do not automatically replace `selected-sum-pair`: it still chooses T1/R1.

## 5. Historical compatibility after promotion: internal calls only

On the final choice-v2 snapshot, explicitly reload I_A's recorded node into a new owned recorder;
do not reuse an ended/foreign live handle. Prepare ONE arguments node G with `{map: I_A, key: "sample"}`.
Execute BOTH:

```text
old = call(dml://builtin/map/get, explicit get-v1, G)
new = call(dml://builtin/map/get, explicit get-v2, G)
```

Both run the REAL corresponding shipped handler NOW, after promotion, producing equal typed MAP
values `{measurements: [13,29]}`. Actual operation records retain different binding/source versions.
Retain both positions in an ordinary compatibility ledger/summary, even if an old primitive record
content deduplicates. No Q/T, local child or extra empirical trial is created for these two internal
calls. Builtin-only phases block subprocess/transport; the two explicitly dispatched local normal
attempts are a separate allowed process boundary.

Unsupported-v99, non-NULL/wrong-typed binding fields, wrong func/source pairing and reserved identity
redefinition are companion negatives, NOT additional acceptance calls. Store/inspect a canonical
unknown source URI as reference, but ensure actual invocation rejects before success publication and
without any “latest” handler/source load. Historical descriptions alone never claim executable support.

## 6. Exact census and same-history readers

| Outer request | Requested path | New attempt | Satisfied result |
| --- | --- | --- | --- |
| Q1 | source A / get-v1 / [13,29] | T1 |42|
| Q2 | source B / get-v2 / equal [13,29] | none | OLD T1/R1/42|
| Q3 | source C / get-v2 / [13,30] | T2 |43|

Recommend exactly THREE Q/TWO synchronous LOCAL attempts, ZERO support Q/T in acceptance history.
Builtin positions are separate, NOT unique content-node counts:

- Six caller construction positions: empty+insert for A, B and C.
- Eight normal-call trace positions: four inside T1, four inside T2.
- Two compatibility positions: pinned old-v1 and new-v2 after promotion.
- **Sixteen successful built-in invocation positions total**; argument preparation/literals/selection/
  choice/decision/Q/W/summary/transfer/inspection create no hidden builtin calls or Q/T.

Retain original controller/captured normal sources/native+module install hashes BEFORE launch,
incremental Q/child PID/wait/outcome/public native receipts before later metadata. If later assertions
fail, STOP and correct nonexecuting readers on SAME stopped evidence; never repeat the computation
speculatively. Native call records plus actual measured invoker/controller execution are required,
not mock dispatch counters or handwritten operation traces.

After two direct children are known reaped, make only owned original source/workspace/packet/expected
paths unavailable. Transfer the pinned complete final history to a fresh installed repository. Fresh
readers activate spawn/transport blockers BEFORE helpers/runtime loads and verify SAME native bytes:

- New dml: URI datum canonicalization/storage/import; URI presence does not authorize execution.
- All four built-in func bindings/actual standard argument nodes/results/explicit source relationships.
- A/B full map datum equality despite distinct sources, C typed-value difference, native3Q2T census.
- Exact owning Dn/Cq/W spines/ordered parents/only-intended tree deltas/immutable reservations.
- Public S1 versus requested Q2, old trace-v1 versus requested v2; no Q2 getter/T/completion fabrication.
- Real v1/v2 operation bindings and exact semantic value recomputation AFTER default promotion.
- Q3 pending miss before explicit T2/result43, no automatic adoption, old choice/S/history retained.
- Complete typed all-parent/anonymous-node/composite closure, exact captured source/installed module/
  native-library provenance and unchanged target store bytes. Inspector revalidation creates no calls.

This is forward retained-handler support inside one new installation, NOT testing a previous shipped
builtin release (none exists yet), old20 reader compatibility, performance, scientific correctness,
security/full capture or a nativefix. Candidate counts/spellings may be refined during review; no run
is authorized by this document. Development GHA disabled/native investigation PAUSED/VP-001 OPEN UNKNOWN.
