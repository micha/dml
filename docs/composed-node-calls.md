# Composed ordinary node calls and value reuse

Status: informative implemented **example-local** convention, not an installed evaluator/cache API.

## Authority boundary

This page owns [composed_node_calls.py](../examples/composed_node_calls.py) and the two
[value-only logical funcs](../examples/composed_node_funcs.py). [Internal builtins](internal-builtins.md)
owns recorder-owned argument-map NODE → result NODE calls, explicit return profiles and semantic
inspection. [Successful selection](versioned-reuse-selection.md) owns public S/Q/T/R/F validation;
[caller requests](spec-next/caller-requests.md), [local execution](spec-next/local-execution.md),
[exchange](spec-next/repository-execution.md), [transfer](spec-next/transfer.md) and
[Python storage](spec-next/python-api.md) retain their separate contracts. These ordinary roles
add no native entity, opcode, layout or repository key.

## Two explicit funcs, no dependency evaluator

Python explicitly sequences two captured local bindings:

```text
urn:example:node-add({a:13,b:29}) → outer result node R with I64 value42
urn:example:node-double({x:R})   → result node with I64 value84
```

Both wrappers use installed `builtin.publish_callable`, pinned map-get-v1/list-get-v1 binding
IDs and captured `composed_node_funcs.py` bytes. Add reads exactly `a,b` through two map getters;
double reads exactly `x` through one. Arithmetic is explicit Python, returning `ops.literal` with
`Datum.i64`; BOOL/F64/coercion and signed-I64 overflow reject. No arithmetic builtin is introduced.
The list binding is validated by the existing wrapper but no list getter is invoked here.

Literal/MAP preparation is bootstrap authoring, not a primitive invocation. The logical callable
gets owned semantic nodes and a bound value-access interface, not implicit graph/provenance access.
This is cooperative trusted Python, **not** a sandbox, purity proof, complete capture or arithmetic/
scientific certification. `put_datum` returns a DATUM ID, not a semantic NODE handle.

## Successful computed sources and separate selected-attempt witness

`compose_double` first publicly validates the explicit upstream S slot at the pinned basis, including
retained successful exact Q/T/R/F. It separately inspects R's explicit normal-return/value/trace/Q/
full-input association and the ORIGINAL producing add decision. A structurally valid R or provisional
publication alone is insufficient success authority. Validation scratch/handles close BEFORE write.

Inside a new recorder, `load(S.result)` reloads the **outer R**, then `arguments({"x": Rhandle})`
retains that source without rerunning add or copying a naked scalar. Reload changes temporary handle
ownership, not native graph identity. Native MAP keys/values remain datum IDs.

One storage batch publishes two previously absent tree names: arguments I and separate composition C,
with one actual parent and a create-only ref. C is role-rooted `example-node-composition-v1`, exactly:

| Field | Value/link |
| --- | --- |
| `role` | STRING role |
| `arguments` | I DAG |
| `key` | STRING `x` |
| `selection-slot` | STRING explicit upstream slot |
| `selection` | captured S DAG |
| `result` | outer R DAG |

A reader checks C's ACTUAL snapshot/parent adds ONLY I/C, S equals THAT slot in THAT parent, R equals
S.result and I.x's source equals exact outer R with its value. S retains the selected T; Q/R alone
need not distinguish multiple attempts of one request. C stays outside the unchanged strict arguments
profile and MAP value. Q.inputs retains I/R, while selected attempt provenance is separately captured
through its decision/C. Convenience ref movement does not change captured C/history.

## Own Q on fresh and reuse paths

Effective matching is **canonical intent URI + full computational argument MAP datum ID**. Full
bindings/source DAGs and composition remain provenance, not this example's value key. Same-intent
membership declares result equivalence; DML does not prove it. One known `selected-double` S is used;
upstream immutable S slots are producer evidence, not automatically discovered add-cache entries.

Add is explicitly `fresh`; double accepts `fresh`, `try-selected`, `require-selected`. Present S is
publicly and structurally validated even on value mismatch, INCLUDING its original double decision/C/
upstream-S chain. A poisoned selected entry errors rather than silently becoming a miss. Producer
chain depth is bounded at four recursive decision levels in this fixed two-func profile.

NEW ordinary decision `example-composed-node-decision-v1` binds `role`, `intent` URI,
`binding-name`, `inputs-name`, `control`, `action`, `reason` STRINGs; `binding`, `inputs` DAG links;
`value` full MAP datum literal. Its root is `inputs`. Double additionally captures `composition-name`
STRING and `composition` C DAG. A present selected-double additionally captures `selection-slot`
STRING and `selection` S DAG, including on valid mismatch/fresh control. Exact field set is recomputed
from the actual one-parent basis; only the decision is added to its snapshot.

Public request recording then creates its own Q/Cq separately. BEFORE W, actual Cq parent must equal
THIS authored decision; exact tree/request/dimensions/submission/decision/reservation refs are checked,
not response flags. On a hit, ordinary `example-explicit-reuse-v1` W binds new `request` Q to OLD
`attempt` T and `result` R (also W root). It adds only satisfaction to Cq in a separate storage batch.
No new T, callable/getter/completion or rewriting of historical result/trace occurs.

Absent/valid-mismatch selection leaves pending Q before a separate explicit adapter dispatch.
Fresh work does NOT automatically adopt its result. Input+C, decision, Q, W, files and child execution
are separate boundaries: W failure may leave legitimate pending Q; postcommit acknowledgement loss
may leave complete publication. No whole-operation rollback/retry/idempotent authoring promise.

## Requested source versus OLD executed source

For fresh repeated add42 followed by reused double84:

```text
NEW requested Q4 → I4 → actual R3; captured C4 → S3 → selected add T3
NEW satisfaction W4 → OLD double T2/R2 → original Q2/I2/C2 → original add S1/T1/R1
```

Readers show BOTH chains, never present the old double as executed with the new add. Swapped
`{a:29,b:13}` has a different add MAP key from `{a:13,b:29}`, even though add returns42. Both give
downstream `{x:42}`, so the double key matches. No commutativity inference, operand normalization or
upstream reuse occurs. Reversing insertion order of the SAME pairs preserves canonical MAP identity.

## Evidence and limitations

[Explicit installed controller/reader](../tests/composed_nodes/README.md) is opt-in and requires
separate authorization. Its bounded story has EIGHT Q/SIX synchronous LOCAL attempts: FOUR adds/
TWO doubles/TEN successful child map-get positions, zero support Q/T/construction/compatibility calls.
Two downstream hits reuse old84; changed add43 misses and fresh double returns86 without adoption.
A role-rooted ordinary summary links eight requests/selected results/attempts, four compositions and
two W satisfactions. It is not an additional LMDB entity or a historical execution rewrite.

Focused [contracts/associations](../tests/python/test_composed_node_calls.py),
[producer/own-Q edges](../tests/python/test_composed_node_edges.py),
[exact profiles/original-chain](../tests/python/test_composed_node_profiles.py) and
[new-row atomicity](../tests/python/test_composed_node_atomicity.py) use native storage and
explicit HOST publication substitutes. [Finite mutations](../tests/composed_nodes/mutations.py)
measure private sources before predicted failures; they are not shipped hooks or exhaustive scores.
Existing16argument/16position/64reached-semantic-DAG and transfer caps remain unchanged.

[Diagram](lmdb-entity-diagram.html) remains accurate: ordinary DAG carriers and datum-only MAP
children change no displayed entity/key/layout/hash/relationship. Development GHA intentionally
stays disabled/NOT RUN/not pass; local evidence is not fresh platform all-green or diagnosis of
native19/VP-001 UNKNOWN causes. Actual commands, source versions, failures, custody, independent
acceptance and publication belong to [Iteration22 results](../../dml-design/iterations/22-composed-node-calls/RESULTS.md)
and [coordination](../../dml-design/iterations/22-composed-node-calls/COORDINATION.md).
