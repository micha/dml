# Iteration 3 candidate design: composable DAGs and named-node lookup

Status: the user reviewed and approved this design and handoff, then authorized
bounded implementation and coordinator review/fixes, followed by commit/push after
acceptance and exact-SHA CI verification/fixes. See [COORDINATION.md](COORDINATION.md).
The assistant-origin choices below are accepted as the bounded design plan, not
as-built behavior; provisional engineering spellings can be recorded during the turn.

**Delivery:** this approved plan has been implemented, independently reviewed and
published as `9b8fb71`, with all six exact-SHA CI jobs successful. See
[RESULTS.md](RESULTS.md) and [REVIEW.md](REVIEW.md). The proposals below preserve
planning provenance; actual behavior belongs to the as-built contracts. Work is
complete and stopped, not an instruction to restart implementation.

## 1. Authority and goal

This document owns the candidate representation, APIs and inspection behavior.
[EXAMPLE.md](EXAMPLE.md) owns the informative worked example;
[HANDOFF.md](HANDOFF.md) owns the conditional work sequence and acceptance evidence.
Implemented contracts remain in the [as-built specification](../../../dml/docs/spec-next/README.md).
The [glossary](../../../dml/docs/spec-next/glossary.md) owns vocabulary.

User-agreed scope: named bindings inside DAGs, explicitly scoped node lookup,
sub-DAG composition, and bounded C/Python/CLI construction and inspection. No
execution engine, intents/closures, requests/attempts, reuse facets, remotes,
resources, observers, UI or general workflow framework.

Goal: record a small nested comparison, inspect its structure and evolve one part
without rewriting or flattening the others. Do not expand this turn to establish
computational causality or execute a graph.

## 2. Inspected baseline

Preparation inspected clean implementation HEAD
`e253249eca70ad588d918d321a54a1413447b8a0`; no tests/builds were rerun.
Iteration 2's [delivery evidence](../02-repository-usability/RESULTS.md) is historical,
not a fresh check of this candidate.

Current seams requiring changes:

- [object.h](../../../dml/include/dml/object.h) / [object.c](../../../dml/src/object.c):
  literal-only nodes; DAG input is a single root; tree entries are name-to-DAG IDs;
  views do not expose node kind or DAG bindings.
- [repo.c](../../../dml/src/repo.c): node direct-reference checks assume datum
  targets; counted object references assume tree entries or commit parents.
- [Python API](../../../dml/docs/spec-next/python-api.md): frozen LiteralNode and
  root-only DAG descriptions, explicit IDs, owned copies and fail-closed mutations.
- [CLI](../../../dml/docs/spec-next/cli.md): node display and snapshot roots assume
  literal nodes. Existing history traversal is separate from computational structure.

Preserve one authoritative C codec/store and one native CLI. No parallel Python
encoding, global scope registry or additional repository object category is needed.

## 3. Candidate structural model

### Nodes and DAGs

Retain literal nodes referencing datums. Add one node kind, provisionally
`SubDAGNode(dag: ObjectId)`, referencing a DAG by immutable content ID.
This node describes nested structure; it is not a call, import protocol, external
resource, late ref resolution or execution result retrieval.

A DAG has:

- One required root node ID, literal or sub-DAG-reference node.
- Zero or more named bindings from names to node IDs.

The root and bound nodes are entry points into recorded structure. Reachability
follows DAG-to-root, DAG-to-binding, and sub-DAG-reference-node-to-DAG edges.
There is no separate node-membership array. A node created in the repository but
not reachable by these edges is not thereby a member of this DAG. Literal datum
references carry values; composite datum references remain value structure, not
new computational edges.

This lets a summary be the root while named trial nodes expose additional content.
It does not imply that the summary depends computationally on those nodes.
General primitive inputs, calls and execution semantics remain deferred.

### Names and scopes

Reuse the existing narrow ASCII name profile and canonical byte ordering.
Reject duplicate names, including duplicates with identical targets. Permit
multiple names targeting the same node and a name targeting the root. An empty
binding set is valid; an absent root is not.

A name is scoped to the exact supplied DAG. There is no inherited/global namespace,
implicit traversal, reserved `root` name or special argument/dependency namespace.
Nested navigation explicitly reads a reference node and supplies its target DAG to
another lookup. Names bind existing nodes, not future selections from moving refs.

### Identity and reference validation

Full-record identity includes node kind/target and all DAG root/name/target content.
Binding input order canonicalizes away. Rename, retarget, add/remove a binding or
change the root changes DAG identity. Aliases remain recorded; their names matter.
No additional facet, mask or reuse identity is introduced.

Proposed direct-reference checks on put/get:

| Object | Expected direct targets |
| --- | --- |
| Literal node | Datum |
| Sub-DAG-reference node | DAG |
| DAG | Root node and every bound node |

Keep existing validation of encoding, typed keyspace and key/content ID. Insert
referenced objects first, including earlier puts in the same transaction. Keep
existing poison/rollback behavior. Direct validation is not whole-graph validation
or a cycle proof; content addressing is not a substitute for integrity checks.
No recursive core validator is proposed for this turn.

### Candidate encoding

Retain the envelope, hash domain, object tags, datum/literal/tree/commit encodings
and typed storage keyspaces. Proposed node kind values: literal 1, sub-DAG reference
2. Both node bodies are `u32 kind + 16-byte target ID` (40-byte records).

Change the DAG body to `16-byte root ID + u32 binding count + bindings`, with
bindings encoded as `u32 name-byte length + name bytes + 16-byte node ID` in strictly
increasing name order. Base record size is 40 bytes; minimum binding size is 21.
Use checked sizes/counts, little-endian integers and exact-length validation.
Unknown node kinds, malformed names, duplicates, unsorted stored bindings, oversized
counts, truncation and trailing bytes are rejected.

This is intentionally incompatible with the existing 36-byte root-only DAG record.
Development stores may be recreated under the pre-1.0 policy; no dual decoder,
version bump or migration is required. Recreating test-owned state is not authority
to delete unrelated repositories. Update affected DAG fixtures/golden IDs visibly;
unchanged datum/literal identities remain independent regression oracles.

## 4. Candidate C and Python surfaces

### C

Introduce a separately typed DAG binding entry (name + node ID), not an API that
mislabels nodes as tree-entry DAGs. Small private shared codec helpers are reasonable;
a generic persisted edge language is not needed.

Extend discriminated object input/view descriptions for node kind/target and DAG
root/bindings. Add a DAG-binding accessor with the same borrowed-byte lifetime as
existing tree accessors. Exact field/function spellings are implementation choices.
Audit every consumer of view `reference`/`count`; the former is now kind-dependent
for nodes and the latter also counts DAG bindings.

Recommend a repository transaction lookup operation taking a DAG ID and validated
name, returning a copied node ID. It uses the normal validated DAG read, searches
that one binding set, and returns `not_found` for an absent binding. Invalid names
are argument errors. No lookup-by-ref convenience or recursive fallback.

### Python

Candidate additions/refinement:

```text
SubDAGNode(dag: ObjectId)                     # frozen owned description
DAG(root: ObjectId, bindings: read_only_mapping)

tx.put_subdag(dag_id) -> ObjectId
tx.put_dag(*, root=node_id, bindings=()) -> ObjectId
tx.lookup_node(dag_id, name) -> ObjectId
```

`get_node()` returns LiteralNode or SubDAGNode. `get_dag()` returns owned immutable
root/bindings data with canonical-order entries. Root-only construction remains
convenient through empty default bindings, not an old-record compatibility layer.
Accept mappings or sequences of name/ID pairs; pair sequences preserve duplicates
until C rejects them. Constructors copy caller containers. No recursive insertion,
auto-loading, implicit conversion to values or Python encoding/hashing.

Lookup is available in read/write transactions; failure is a read failure and does
not poison a write. New mutation conversion/codec/native failures retain the
existing fail-closed contract, even when caught. Preserve current single-active,
thread-affine ownership/context restrictions and copied-description lifetime.
Update native conversion cleanup paths and the Python stub alongside the surface.

## 5. Candidate inspection CLI

Keep inspection-only behavior, explicit repository/IDs, one read transaction,
structured human/JSON output, buffered success results and existing exit codes.
No CLI mutation is added.

### Immediate inspection and lookup

- `show node`: literal fields unchanged; sub-DAG node has `kind: "subdag"` and
  `dag: <id>` instead of `datum`.
- `show dag`: retain `root`, add canonical `bindings: [{name, node}, ...]`.
- New `lookup DAG_ID NAME`: exact scope lookup. JSON:
  `{command: "lookup", dag: <id>, name: <name>, node: <id>}`.
- Adapt `snapshot`: retain entry name/DAG/root IDs, add `root_node` containing
  `{kind: "literal", datum: <id>}` or `{kind: "subdag", dag: <id>}`. For literal
  roots retain existing `datum`/`preview` entry fields; for sub-DAG roots omit them.
  Do not silently follow the sub-DAG or pretend it is a scalar. This is a proposed
  JSON change, not a commitment to pre-1.0 CLI compatibility.
- `log` continues to traverse commits, not nested DAGs.

Human output labels node kind and targets explicitly. Existing datum previews and
escaping remain shared behavior; JSON `show` still exposes complete immediate fields.

### Bounded nested inspection

Recommend one new command, `walk DAG_ID [--limit N]`, default 100, counting distinct
DAG/node records emitted, not scope paths, datums or commits. This is a presentation
helper in the CLI, not a new core query engine or observer subsystem.

Use iterative depth-first preorder:

1. Emit the starting DAG, then visit its root followed by binding targets in canonical
   name order. Root aliases remain in the binding list but do not re-expand a node.
2. Emit a node; for a sub-DAG-reference node visit its target DAG. For a literal,
   include its datum ID and bounded preview, without expanding composite children.
3. Key active/visited tracking by object type and ID. Shared objects emit once;
   referring root/binding/target edges stay explicit in record fields.
4. Reject traversed cycles and missing/corrupt visited records. Check active state
   before suppressing already-visited expansion. Do not use C recursion.
5. Set `truncated` only if unvisited reachable work remains after the limit; exact
   exhaustion at the limit is not truncation. Unexpanded targets remain ID edges,
   not fabricated records. A bounded prefix is not a full validity proof.

Candidate JSON: `{command: "walk", start: <dag-id>, records: [...], truncated: bool}`.
Each record has `type` and `id`; DAGs include root/bindings; nodes include kind and
its datum or DAG target, with `preview` for literals. Traversal order is deterministic,
not execution/time order. This yields both scope edges and nested value previews
without a renderer, domain interpreter or model call.

Record/traversal limits do not bound the underlying C reads, immediate-reference
validation, binding arrays, buffered bytes or all allocation sizes. State this
limitation, use checked growth and meaningful failure tests, and avoid promises of
large-graph performance. A broader streaming/pagination design is deferred.

## 6. Design checkpoints and open questions

Before substantial implementation, record selected choices or small replacements:

1. Confirm root-plus-bindings reachability and the non-executing sub-DAG node model.
   If the example needs general computational input edges, surface that as a scope
   question rather than silently adding calls or provenance claims.
2. Select encoding and C input/view/accessor shapes; reject old DAG shape explicitly.
3. Select Python description/lookup spellings and duplicate-preserving inputs.
4. Fix CLI root presentation, lookup/walk grammar, JSON fields and limit semantics.

One semantic limitation remains deliberately open for later turns: these structural
bindings do not express why a result was produced. The example can demonstrate
recorded values and composition, not a captured execution contract.

Small implementation choices within scope can be recorded as assistant selections.
Material changes to the agreed model or stop line need user review. The subsequent
bounded implementation authorization is recorded in [COORDINATION.md](COORDINATION.md);
it does not turn planned behavior into an as-built contract.
