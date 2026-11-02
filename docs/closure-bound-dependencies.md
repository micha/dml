# Closure-bound dependencies

Status: informative implemented **example-local** fixed scaled-sum convention, not a generic evaluator.

## Authority boundary

This page owns [closure_calls.py](../examples/closure_calls.py), the captured
[trusted runtime](../examples/closure_runtime.py) and [logical Python closure](../examples/closure_funcs.py).
[Internal builtins](internal-builtins.md) owns value-node calling/semantic profiles/bounds;
[Python storage](spec-next/python-api.md), [caller Q](spec-next/caller-requests.md),
[local publication](spec-next/local-execution.md), [exchange](spec-next/repository-execution.md),
[transfer](spec-next/transfer.md) and [successful selection](versioned-reuse-selection.md)
retain their separate contracts. Ordinary descriptors below add no native entity/layout/opcode/key.
The [glossary](spec-next/glossary.md) supplies closure/dependency vocabulary, not these fixed schemas.

## Fixed computational contract

`urn:example:captured-scaled-sum` invokes an argument-map NODE with EXACT `a,b` I64 values and
returns an owned I64 result node: `(a+b)*captured_scale`. Both addition and multiplication check
signed-I64 range; BOOL/F64/coercion and invocation `scale` overrides reject. Scale is bound at
closure creation, not merged into invocation arguments. Python explicitly performs arithmetic;
there are no separately recorded ordinary inner add/double requests or nested workers.

The Python factory captures THIS recorder's scale handle and bound value operations. Logical
invocation receives only argument node; no repository/context/navigation interface is supplied.
Two map getters use the captured exact version; list-get is a validated support dependency, never
invoked by this func. Returned literal records no arithmetic/scale-read trace it did not author.
This is cooperative trusted Python, **not a sandbox, purity certificate, full environment capture
or scientific/arithmetic certification**. Generic captured dependencies are broader than this
prototype's two supported types: retained I64 literal/source nodes and fixed shipped getter bindings.

## Explicit immutable capture

Role-rooted ordinary DAGs have exactly these fields, including `role` STRING:

| Descriptor | Role | Other fields |
| --- | --- | --- |
| F | `example-captured-builtin-v1` | `func` URI, `binding` DAG |
| E | `example-capture-environment-v1` | `map-get` F, `list-get` F, `scale` semantic node DAG |
| K | `example-capture-key-v1` | `map-get`, `list-get` func URIs; `scale` typed I64 datum literal |
| C | `example-captured-closure-v1` | `intent` URI, `binding` B, `environment` E, `capture-key` K DAGs |

Only map/get v1/v2 and list/get v1 exact func/source pairs qualify. Unsupported roles/versions/pairs,
wrong types/roots/field sets and unretained nodes reject. Inspectors recompute K and reconstruct B
from exact E ID/current trusted-runtime/logical bytes; another source-distinct equal E is not the
same captured provenance. Historical source compatibility beyond this fixed prototype is not supplied.

`initialize` explicitly prepares getters/constants and semantic source wrappers at two bootstrap
storage boundaries, without Q/T/getter calls. `create_closure` validates selected pinned F/scale
BEFORE writing. One transaction authors E, then local executable B, then C; publishes ONLY two
absent tree names B/C with one parent and a create-only ref. C retains B/E/K and E retains F/scale
through actual SubDAG links. Embedded E hash alone is not retention. E predates B; no source contains
C's future hash or creates a self-ID cycle. Equivalent content can deduplicate; snapshot/ref is
creation context, not a fabricated unique closure-occurrence entity.

`promote_defaults` changes ONLY existing convenience `default-map`/`default-scale` tree entries in
a new one-parent snapshot. Explicit invocation chooses immutable C; old C/E/B/K remain byte-identical.
Defaults are not execution-time selectors or historical attempt selectors.

## Separate invocation decisions and own Q

NEW `example-capture-decision-v1` D roots at `inputs` and binds exactly:
`role`, `intent` URI, `closure-name`, `binding-name`, `inputs-name`, `control`, `action`, `reason`
STRINGs; `closure`, `binding`, `environment`, `capture-key`, `inputs` DAGs; `value` full MAP literal;
optional `selection` S iff the known slot is present in the ACTUAL basis. D's one-parent snapshot
adds ONLY D. `fresh` requires execute/explicit-fresh; `require-selected` requires selected reuse;
`try-selected` permits validated hit or absent/valid-mismatch fresh decision.

Public Q remains unchanged: Q.binding is B; Q.inputs is full argument I with exact `a,b`.
D separately supplies capture association. Request recording checks actual Cq parent equals THIS
authored D, exact public submission/tree/Q/dimensions/decision/submission/reservation refs before W;
returned description flags are not authority. Child validates actual native Q/D/C/E/K/B and coherent
control/action/reason BEFORE publication write; public pinned submission validation scratch closes.
Child checks strict capture/submission structure, **not full original-S eligibility re-resolution**:
that is separately the host decision resolver's public-S/original-producer responsibility.

ONE child transaction/Recorder loads exact I and E.scale, binds exact getter operations, invokes
the fixed Python closure, creates unchanged normal return/ordered trace and calls public local
publication. No nested same-store public projection occurs while writing. Existing16arguments/
16positions/64reached-semantic-DAG and transfer bounds remain unchanged; descriptor readers have
fixed fields, and original selection decision recursion is bounded at eight levels.

## Capture-aware reuse with separate provenance

This NEW example key is `(canonical intent URI, recomputed K, FULL invocation MAP datum ID)`.
K includes scale's typed datum plus the two supported builtin func URIs; it excludes scale-source
identity, exact equivalent getter version, C/E identity, defaults/names/creation commit. This bounded
equivalence declaration applies ONLY to these supported shipped getters, not arbitrary callable
URI identity or recursively captured closures. Earlier examples' keys/APIs remain unchanged.

One known `selected-scaled-sum` slot is used. A present S passes public successful Q/T/R/F validation
AND its ORIGINAL native D/C/E/K/B/full-I/normal-return/two-getter trace association, even on explicit
fresh or a key mismatch. Poison is an error, never a fallback miss. Fixed getter inspection recomputes
semantics without recording; it never executes captured Python arithmetic/source bytes.

A hit creates NEW own Q and ordinary unchanged `example-explicit-reuse-v1` W linking new Q to OLD
selected T/R, with no T/getter/job/completion. Requested new v2/source-B capture remains separate
from OLD producing v1/source-A capture. A miss remains pending until separate explicit dispatch.
Fresh success does not auto-adopt. S evidence slots for other completions support offline inspection,
not discovery/adoption. Closure, D, Q, W, files and external child are separate boundaries; W failure
can leave legitimate Q, and lost postcommit acknowledgment can leave complete publication.

## Evidence and limits

[Focused contracts](../tests/python/test_closure_calls.py), [edges](../tests/python/test_closure_edges.py)
and [atomicity](../tests/python/test_closure_atomicity.py) distinguish native absent-row/map-full/
consuming-commit faults from explicit HOST publication/response substitutions.
[Finite mutations](../tests/closures/mutations.py) are measured private sources, not shipped hooks or
an exhaustive score. [Sole installed acceptance](../tests/closures/README.md) has SIX-Q/FOUR synchronous
LOCAL attempts/EIGHT child map-get positions, no list/support/construction/compatibility/nested calls;
SAME retained history goes to fresh blocked NONEXECUTING readers, never repeated computation.

[As-built diagram](lmdb-entity-diagram.html) remains accurate: ordinary DAG descriptors/SubDAG retention
and datum-only MAP children add no native entity/key/hash/layout/relationship. Development GHA stays
disabled/NOT RUN/not pass; native19 PAUSED and VP-001 OPEN UNKNOWN remain. Local evidence does not
supply fresh platform all-green or historical diagnosis/standing waiver. Actual execution, source
qualifications, custody, acceptance/publication belong to
[Iteration23 results](../../dml-design/iterations/23-closure-bound-dependencies/RESULTS.md).
