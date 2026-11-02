# Internal versioned builtins and value nodes

Status: implemented additive, explicitly imported Python surface `daggerml.builtin`.

## Authority boundary

This document owns fixed builtin dispatch, semantic value-node profiles, recorder bounds,
cooperative callable access and the selected normal local wrapper. [Records](spec-next/records.md)
owns canonical datums/URI references; [objects](spec-next/objects.md) owns native Literal/SubDAG
storage. [Python API](spec-next/python-api.md) owns native handles and storage transactions.
[Local execution](spec-next/local-execution.md), [caller Q](spec-next/caller-requests.md),
[exchange](spec-next/repository-execution.md), [transfer](spec-next/transfer.md) and
[successful S](versioned-reuse-selection.md) retain their separate authority. The bounded
choice/one-S example below is informative, not a public cache/registry framework.

## Fixed shipped implementations

Every supported builtin consumes an **argument-map node** and returns a **value node**.
Native MAP pairs contain datum IDs, never source-node IDs. Standard preparation retains
actual source associations outside the MAP value. Empty/insert/get/list-get all use the
same URI-bound invoker; preparation itself is eager bootstrap machinery, not recursively
calling map/insert to prepare map/insert. No lazy DAG evaluation/dependency jobs are added.

| Func URI | Exact arguments | Supported source URI suffix under `dml://source/builtin/` |
| --- | --- | --- |
| `dml://builtin/map/empty` | none | `map/empty/v1` |
| `dml://builtin/map/insert` | `map`, `key`, `value` | `map/insert/v1` |
| `dml://builtin/map/get` | `map`, `key` | `map/get/v1`, `map/get/v2` |
| `dml://builtin/list/get` | `list`, `index` | `list/get/v1` |

The role-rooted ordinary binding DAG has exactly `role` STRING `builtin-binding-v1`,
`adapter` NULL, `source` URI, `interpreter` NULL and `timeout-ms` NULL. NULL deliberately
selects internal execution; it is not missing configuration/default/latest. Source URI
identifies exact shipped implementation, not captured bytes or a fetch target. Execution
validates exact func/source pairing before a handler or successful operation record.
Unsupported URI/version rejects explicitly; there is no import-by-URI, mutable registration,
URI substring dispatch or fallback. `put_binding`/`inspect_binding` can store/describe strict
unknown URI references without claiming executable support.

Map-get v1 performs validated linear lookup; v2 performs validated key-ID lookup. They are
real distinct entrypoints shipped together with the same semantics, not aliases, a benchmark,
a claimed fix or evidence of a previous builtin release. MAP operands have at most16 STRING
keys. Insert is immutable and rejects duplicate canonical keys, including NFC equivalents;
replacement is deferred. Get rejects missing keys. List-get requires LIST plus exact I64 index,
nonnegative and below length. BOOL/F64/coercions/negative indexing are not accepted. Values and
nested collections remain typed copied `Datum`s containing child datum IDs, not host containers.
Copied value revalidation uses typed canonical datum equality: F64 NaNs compare equal because
native records encode them as one canonical value; unequal finite values and different kinds
still reject. Collection equality compares their canonical child-ID structure, not nested
host materialization. This adds no native encoding/hash fallback or extra writes.

## Recorder-owned node calling

```python
from daggerml import Datum, builtin

# Trusted authoring inside one existing write transaction and Recorder context:
with builtin.Recorder(tx, commit=pinned_commit) as recorder:
    measurements = recorder.source(named_source_dag, "measurements")
    empty = recorder.call(builtin.MAP_EMPTY, empty_binding, recorder.arguments())
    sample = recorder.call(builtin.MAP_INSERT, insert_binding,
        recorder.arguments({"map": empty, "key": recorder.literal("measurements"),
                            "value": measurements}))
    arguments = recorder.arguments({"sample": sample})
    # Trusted wrapper retains recorder.dag(arguments) and recorder.trace() in history.
```

`ValueNode.value` is copied canonical Datum; it exposes no public source/record/ref/path/context
or arbitrary-ID navigation. Logical code receives that node plus bound `NodeOperations` with
only `literal`, `map_get`, `list_get`. Trusted wrapper keeps the recorder/repository authority.
Each convenience makes its own argument-map node and routes through `Recorder.call`, with
conversion, source validation, preparation and dispatch covered by the same poison guard.

Handle association is exact object identity in THIS recorder, not equality of Datum IDs or a
global origin registry. Foreign, fabricated, ended and value-laundered handles reject. Every
consumption revalidates strict native profiles/value derivation; a host boolean/claimed scalar
is not authority. Equal collections reached via different nodes/key paths retain those actual
sources. A new recorder `load(dag)` reloads retained recorded nodes instead of old live handles.
Copied `.value` can be inspected after closure; authoring through the closed scope rejects.
Nested/repeated Recorder context entry rejects. No native pointers escape in ValueNode.

This is a cooperative Python interface, **not a security sandbox, purity proof or full-capture
guarantee**. Trusted introspection/imports/globals can bypass interface conventions; wrapper and
local child retain ordinary user/repository authority. No arbitrary DAG-root extraction occurs.

## Ordinary semantic profiles

All profiles use existing native DAGs with Literal fields and SubDAG links. Value-oriented
semantic operation nodes can use native SubDAG storage carriers; there is no new native opcode,
node kind, LMDB entity/schema/ABI or C/CLI invocation API. CLI inspection remains available.
Every profile binds its STRING role explicitly; value profiles root at their `value` literal.

| Role | Other exact fields |
| --- | --- |
| `builtin-literal-v1` | `value` literal, explicitly authored by trusted recorder |
| `builtin-literal-source-v1` | `value` literal, `source` DAG, `name` STRING, `node` BYTES actual native selected-node ID |
| `builtin-arguments-v1` | `value` MAP literal, `entries` DAG |
| `builtin-argument-entries-v1` | ordered `arg-00`…`arg-15` entry DAG links; role root |
| `builtin-argument-entry-v1` | `key` STRING literal, `source` actual semantic node DAG; role root |
| `builtin-operation-v1` | `func` URI, exact `binding` DAG, own `arguments` DAG, `value` literal |
| `builtin-trace-v1` | ordered `call-00`…`call-15` operation links; role root; normal traces additionally have owning `request` Q/full `inputs` links |
| `builtin-return-v1` | explicit `returned` node DAG, matching `value` literal, actual `trace`, owning `request` Q/full `inputs` |

Source authoring selects an explicit literal named within a DAG present in the pinned tree.
Descriptor retains source DAG/name/node/value, even if a later snapshot removes that direct tree
name. Literal profile does not claim arithmetic provenance. Normal-return profile designates a
node/value explicitly, not an arbitrary DAG scalar projection. Structural inspection of a return
is not success authority; historical attempt use separately requires public successful S/Q/T/R/F.

`Inspector(tx, commit=...)` validates typed all-parent/native/composite reachability with existing
transfer object/record/packed-byte bounds, and accepts semantic sources/bindings only from retained
DAG closure. It recomputes fixed builtin semantics, argument values and explicit return/trace/Q
association without the recording dispatcher, new records or execution of captured Python source.
It does not certify arbitrary Python arithmetic/scientific correctness. Path-level example readers
add public complete transfer validation before opening target reads.

The semantic profile cap is64 **distinct reached DAG IDs**, including bindings, entry/trace ledgers,
entry/source/argument/operation/return profiles and selected literal source DAGs. Sharing counts once.
Actual successful call positions are independently bounded at16; repeated identical operation
content retains repeated positions rather than invented occurrence IDs. Named arguments and MAP
operands are bounded at16. Conservative prospective reservations include newly authored records
BEFORE puts; content dedup can use less capacity. Native complete closure is a separate bound.
These are application profiles, not byte/RSS/runtime quotas or unlimited traversal APIs.

## One normal callable and atomic publication

The selected wrapper `publish_callable(context, func, map_binding=..., list_binding=...)` loads
Q's exact full argument node; logical func receives node plus bound ops and returns an owned node.
Trusted wrapper produces the explicit normal result-sub-DAG node and publishes through unchanged
`local.publish_result`. Child source/literal/argument/operation/ordered trace/R/publication records
are authored in ONE storage transaction. No public S projection/nested same-store wrapper occurs
while that write is live. Contexts/inspectors finish on their creating thread; failed publication
aborts the whole batch. General dispatch of arbitrary normal funcs/evaluators is not supplied.

Any authoring/invocation/conversion error poisons the Recorder. If logical code catches it, later
completion still rejects; recorder context exit aborts the WHOLE supplied transaction and raises.
Let exceptions escape and use a fresh explicit scope for another computation. This does not add
native mutation semantics or durable failed-call traces; old local failure/unknown/cleanup remains.
Storage, metadata batches, own Q/W, files and external child execution are separate boundaries.

## Informative bounded example and validation

[builtin_workflow.py](../examples/builtin_workflow.py) records a fixed map-get v1/v2 choice and
captured normal sum-pair bindings pinning exact builtin IDs. Inspector checks BOTH normal bindings'
role/root/adapter/captured bytes/interpreter/timeout, including the unselected one. Explicit default
promotion changes only choice in a new snapshot; old bindings/choice/history remain selectable.
[builtin_funcs.py](../examples/builtin_funcs.py) uses successive ordinary map/map/list/list getters,
receives copied values only and returns an explicit literal result node.

ONE known `selected-sum-pair` S is publicly revalidated even on value mismatch. New Dn records actual
basis/requested choice/binding/full arguments/MAP/control/action/reason and consumed S. Separate own
public Q is recorded; before ordinary W, actual Cq parent must equal THIS authored Dn and exact
Q/ref/reservation/tree/dimensions must match. A coherent alternate SAME-name decision cannot be
accepted from returned description flags. Reuse matches sum-pair intent plus full MAP VALUE, retains
requested source/v2 separate from historical source/v1/old trace, creates no T/getter/completion and
never automatically adopts. A miss remains pending until separate explicit fresh dispatch.
Old20/earlier helper roles/APIs are unchanged, not reinterpreted by this bridge.

[Focused tests](../tests/python/test_builtin.py), [profile bounds](../tests/python/test_builtin_profiles.py),
[bridge](../tests/python/test_builtin_workflow.py), [meaningful edges](../tests/python/test_builtin_edges.py)
and [new-row atomicity](../tests/python/test_builtin_atomicity.py) distinguish native rollback and
host publication substitutions from the explicit [installed acceptance](../tests/builtins/README.md).
The sole installed story proves THREE Q/TWO synchronous LOCAL attempts42/reuse42/43 and16 actual
builtin positions: construction6 + child nested8 + postpromotion v1/v2 compatibility2; zero support
Q/T. Blocker-FIRST fresh readers inspect SAME transferred stopped history, with original operational
paths unavailable and immutable data bytes unchanged, not speculative computation repeats.

[Diagram](lmdb-entity-diagram.html) remains accurate: canonical URI rules and ordinary DAG carriers
change no displayed native entity/relationship/hash/layout. Development GHA intentionally remains
disabled/NOT RUN; local installed/host evidence is not fresh platform all-green or native19/VP-001
UNKNOWN-cause diagnosis. Actual runs, provenance, exclusions and independent disposition belong to
[Iteration21 results](../../dml-design/iterations/21-internal-builtins/RESULTS.md).
