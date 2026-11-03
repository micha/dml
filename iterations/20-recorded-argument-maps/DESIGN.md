# Iteration 20 candidate design: recorded argument maps

Status: **implemented, independently accepted, normally published and STOPPED** through
`7e9bf133d5d175a492fb1e9d651e91a476358604`. See [RESULTS](RESULTS.md), [REVIEW](REVIEW.md),
[COORDINATION](COORDINATION.md) and [as-built informative owner](../../../dml/docs/recorded-argument-maps.md).
This design preserves planning provenance; the as-built owner defines actual example mechanics.
Development GHA disabled/NOT RUN, not pass/native investigation PAUSED/VP-001 OPEN UNKNOWN.
Completed GO is not restart/later-turn/design publication permission. Earlier status follows:
**GO: reviewed bounded replacement plan authorized for implementation on2026-11-02**.
Existing window-2 agent/new Pi session, coordinator monitoring/independent review/feedback before
accepted focused worker commit/normal push; see [COORDINATION](COORDINATION.md). Development GHA
stays disabled, native investigation PAUSED, VP-001 OPEN UNKNOWN. GO supersedes pending/no-restart
wording below only within this bounded replacement scope; not as-built behavior. Earlier status:
**bounded replacement plan reviewed; implementation GO pending**.
The user subsequently stated “reviewed”; this records plan review, not implementation/delegation/
publication permission or as-built behavior. Exact engineering spellings remain refinable.
Earlier preparation provenance follows:
The user agreed the bounded prototype direction, then said “proceed” after being told the next
step was replacement design/example/handoff preparation. This authorizes preparation, not source
changes, delegation, experiments or publication. Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md).
Exact roles, interfaces, limits and counts below are assistant-origin candidates for review.

## 1. Authority and agreed direction

This is exploratory application design, not an implemented DML contract. Vocabulary follows
[glossary](../../../dml/docs/spec-next/glossary.md). In this discussion **func** means DML callable/
logical intent, and **caching** can mean reuse of a selected historical attempt/result.

Agreed goal: callable-visible arguments are **datums**. Their source relationships remain in the
recorded computational graph but are not implicitly exposed through the callable's argument
interface. Caching uses func plus argument values, not their derivation. Explicitly supplied
provenance information is itself a computational argument and participates in matching.

Agreed prototype: recorded `map_empty`, immutable `map_insert`, and `map_get`, first as ordinary
DAG conventions and fixed Python implementations. String argument keys; duplicate insert and
missing access error; replacement deferred. A datum-only operation interface supplies callable
map access; source bookkeeping belongs to the recorder. Computed inputs require an explicit
returned-datum contract, not arbitrary DAG-root extraction. Python arithmetic can remain internal
to a recorded func boundary. No general evaluator/native opcode schema/security sandbox selected.

This SUPERSEDES the active role of the [projection-policy candidate](../20-result-based-input-reuse/HANDOFF.md),
which remains DEFERRED/historical. There is no exact-versus-result policy P, Mp/Dp migration or
producer-field mask in this replacement plan. Old helpers and historical matching stay unchanged.

## 2. Read-only feasibility findings and existing authorities

- [Datums](../../../dml/docs/spec-next/records.md): MAP stores key/value **datum IDs**, not node
  IDs. Identity covers canonical typed values; MAP ordering is key-ID byte order. STRING is NFC;
  I64/F64 differ, with native F64 zero/NaN canonicalization unchanged. Datum value structure is
  not computational provenance. `put_datum(Datum.map(...))` alone records no source operation.
- [Python API](../../../dml/docs/spec-next/python-api.md): `get_datum` returns copied Datum;
  collection `.value` contains datum IDs, not recursively materialized values. No computational
  map primitives or callable-value interface currently exists. `put_literal` and `put_subdag`
  can represent values and source relationships in ordinary DAGs.
- [Objects](../../../dml/docs/spec-next/objects.md): only LiteralNode/SubDAGNode exist; a sub-DAG
  link does not execute its target. A wrapper DAG with an operation role, operands and result
  can record a performed fixed primitive without adding a native node kind or lazy evaluation.
- [Local execution](../../../dml/docs/spec-next/local-execution.md) gives trusted child code
  repository/graph access today. A NEW wrapper can keep it out of the **logical callable's**
  supplied arguments. LocalContext/adapter API and trust model remain unchanged; the wrapper,
  unlike the logical callable, necessarily has recording authority.
- [Caller Q](../../../dml/docs/spec-next/caller-requests.md),
  [exchange](../../../dml/docs/spec-next/repository-execution.md),
  [transfer](../../../dml/docs/spec-next/transfer.md), and public
  [S selection](../../../dml/docs/versioned-reuse-selection.md)/
  [helper](../../../dml/examples/reuse_selection.py) supply full requested-Q and successful
  original Q/T/R/F authority. Retained S slots can validate a computed source after original
  packet/workspace paths disappear.
- [Intent reuse](../../../dml/docs/intent-scoped-reuse.md)/
  [helper](../../../dml/examples/intent_scoped_reuse.py) keys by full input DAG ID, not datum ID.
  It cannot be used unchanged for new matching. Its public composition pattern is useful, but
  copying private `_resolve`, `_projection`, role decoding or forged producer expected-Q is not.

Recommend NEW example-local helpers plus captured standalone trusted wrapper/func source, all
using installed public runtime. No native codec/storage/local/exchange change is presumed needed.
If a genuinely missing public seam is found, report it before expansion. Do not import uninstalled
example modules in a child: compose any needed example-local support into the captured binding
source bytes, or propose a reviewed narrow packaging seam before changing installed runtime.

## 3. Source/value association and ordinary primitive records (candidate)

A caller-side owned description carries an exact **source reference plus derived datum ID**.
It is NOT passed to the logical callable and is not a self-authenticating dataclass. Readers
rederive its value from native records/public successful selection before authoring or reuse.
Two bounded source forms:

1. **Literal source:** explicitly selected literal node in an explicitly named, pinned source
   DAG. Record source DAG/node/name and validate the exact literal datum; no latest-ref lookup.
2. **Returned source:** publicly inspect an explicit immutable S slot; require successful R
   conforms to this prototype's return profile; select its declared `return` literal node.
   Record S slot/link, R and selected return node. Its datum comes from that node, not a caller
   supplied scalar. Root-equal arbitrary DAGs, failed evidence and unknown attempts do not qualify.

A primitive result is an ordinary DAG with distinct profile/opcode, literal result root and
explicit operand links. Opcode-specific exact shapes reject aliases/extra fields. Recommended:

| Primitive | Operand relationships | Result |
| --- | --- | --- |
| map_empty | none | literal empty MAP datum |
| map_insert | prior map construction/source, STRING key source, inserted value source | literal new MAP datum |
| map_get | THIS invocation's argument-map construction/source, STRING key literal | literal selected child datum |

Source descriptors and operation records remain outside their result datums. The result literal
node can be reused by content identity while construction DAG IDs differ. Inspector follows the
bounded recorded operation dependencies and recomputes these THREE known behaviors only; it does
not run arbitrary user code or interpret any arbitrary DAG as an operation. Bound traversal and
reject malformed shape/types/cycles/over-depth rather than recurse indefinitely.

Insertion validates the prior map, derives key and value from their actual sources, then produces
new canonical MAP pairs. Duplicate means duplicate canonical key datum ID, including NFC-equivalent
STRING spellings. Existing map remains unchanged; key source contributes provenance but not extra
value identity. Returned datum can be scalar or a collection with complete typed datum closure.

Recommended profile limits: at most sixteen named arguments/entries, sixteen successful map_get
trace positions per call, and sixty-four operation/source records along a reached construction
profile. These are NEW application bounds, not lower native/test budgets. Exact finite checks and
error types remain refinable. Negative collection/normalization cases can be nonexecuting; do not
add a computational job merely for them.

## 4. Full invocation, callable interface and returned datum (candidate)

NEW input I DAG has exact `role`, `arguments` literal MAP, and `construction` sub-DAG; root is
`arguments`. Construction's derived datum ID must equal that literal's datum ID. Native Q still
records the full I, including construction provenance; never put only the datum/cache key on Q.

Illustrative logical callable, NOT current public API:

```python
def double(args, values):
    x = values.map_get(args, "x")  # returns a Datum, not a node or provenance handle
    if x.kind != "i64":
        raise ValueError("double requires I64")
    return Datum.i64(x.value * 2)
```

The trusted child wrapper validates pinned I, derives/copies its reachable datum closure, binds
one datum-only map-access interface to THIS invocation, calls double, then publishes a returned
value plus recorded access trace through the existing adapter. No LocalContext/repository path,
Q/T/source IDs/recording response is supplied to double. Facade exposes map_get, not lookup_node,
get_record, commits, refs or general `get_datum(arbitrary_id)`. Composite IDs inside datums are
value-structure IDs, not provenance capabilities. Only the bound argument map is accessible in
this first facade; arbitrary nested collection traversal/materialization is deferred. Reading an
argument which is itself a collection returns its Datum with child IDs, consistent with current
API, without granting a general store reader.

Map_get internally uses the invocation-bound argument map/source, even if another invocation has
the same map datum ID. Do not keep a global datum-ID-to-source registry, choose an arbitrary equal
source, or embed producer metadata in returned datums. Record successful access recipes in order;
repeated accesses can share operation content but retain trace positions. This is not a new native
primitive occurrence/attempt model. A discarded/unpublished trace is not evidence no access occurred.

Recommended returned-result R profile: exact `role`, `return` literal node (also root), `trace`
sub-DAG. Trace pins actual owning Q and the bounded ordered map_get records; each access checks
that Q's full I and actual construction supply that map. For add, returned I64 plus two accesses;
for double, returned I64 plus one. Python arithmetic remains opaque/internal. Reader checks map
access/value/source association, not scientific validity or arbitrary Python replay. Successful
public F/S supplies occurrence/outcome authority in addition to this application profile.

R's full DAG ID may vary with trace/Q/history while its returned datum ID stays equal. Matching
uses the latter. New computed source extraction only accepts this declared return profile. Parent
Q exists before trace/R; do not create a cycle by linking R to a final T that itself points to R.

Use public primitive evaluation/authoring paths, not hand-authored fake getter traces in the story.
All successful wrapper publication puts trace/R and publication together in one child transaction.
Callable validation/access/arithmetic errors before publication yield the existing local failure
outcome, not false successful return; durable error traces are outside this bounded prototype.

This is a **cooperative interface boundary**, not access-control isolation: trusted Python can
use globals/imports/introspection and child wrapper retains local-user/repository authority.
No hidden-dependency prevention, purity/full-capture or complete reproducibility claim follows.

## 5. Datum-keyed selected reuse and two provenance chains (candidate)

Recommend NEW example-local table Md, decision Dd and pinned reader; names are illustrative.
Table scope: canonical func intent URI plus fixed prototype profile, zero to sixteen entries.
Key `datum-<argument-map datum ID hex>` renders native datum identity, not new hashing/facet.
Row stores argument-map literal, original full I, immutable downstream S slot/link. Inspection
publicly validates ALL S entries, their original intent/I, the input construction/source chain,
and returned result profile; recomputes row key from actual argument-map datum. Do not silently
accept Mi or reinterpret its full-input key.

Requested canonical URI and captured binding remain explicit; no mandatory new menu/registry or
intent-default framework. Existing public implementation/default inspection may be composed if
useful, but do not redesign or weaken its fixed contracts. NEW bounded request controls: try named
selection then pending fresh on absence, force fresh, or require selected reuse. Separate explicit
selection/adoption/removal operations preserve other rows/old immutable S/history/branches; no
automatic discovery/adoption. Adoption replaces one matching datum key with a different successful
attempt occurrence, even if original full input constructions differ. Old helpers still match their
old dimensions. Profile mismatch/wrong URI/invalid nonmatching row errors, not miss.

Dd pins actual basis, requested URI/binding/full I/argument datum/construction, request control/
action/reason, consumed table/row/S where relevant. Public own Q publication is a separate batch;
validate exact actual Q/Cq/reservation/ref/tree before separate ordinary W with ownQ/OLD T/R.
Compare canonical URI plus argument-map datum, not full I or producing binding, only in this NEW
policy. Original T retains its original Q/I/construction. No new T or getter execution on reuse.

Pinned request reader checks exact Dd basis/submission/W spine/deltas and requested full I, then
publicly validates historical S/full I/return. It exposes **requested construction** separately
from **historical executed construction/access trace**. A reuse summary links own Q/W and old
T/R, never fabricates a map_get performed by the new request or a new completion packet. Reused
returned datum can be supplied through the same successful original S as a later computed source;
W is satisfaction association, not an independent successful F for its new Q.

All inspector/scratch work closes before target writes; native complete all-parent/composite
closure on every path. Full Q, primitive authoring, S capture, table mutation, Dd, Q, W and dispatch
are separate boundaries. Single-batch metadata mutation with exact parent/create-only explicit
ref/prebuilt response; late W failure can leave Dd/Q complete. Lost response can leave complete
publication; never repair/retry/relaunch automatically. Inspection never writes target storage.

## 6. Scope, evidence and stop line

EXAMPLE proposes FIVE requests/FOUR synchronous LOCAL attempts: literal-map double84; add13+29
returns42; computed-map double newQ/oldT reuse; add13+30 returns43; computed-map double fresh86.
Construction primitives run as bounded metadata operations, not extra Q/T; successful fresh funcs
record six getter trace positions total. No getter executes on reuse. Focused negatives count
separately; no support computation in acceptance history.

Primary checks: same datum/different construction caching, wrong source/forged association,
returned-profile rejection, canonical typed composite identity, duplicate/missing keys, facade
nonexposure and actual getter provenance, poisoned table rows, ownQ versus historicalQ, no forged
fresh trace or automatic adoption. Representative NEW authoring/publication/metadata rollback and
loss plus existing unchanged S/Q/native evidence, not all prior permutations. Diagram review only
as-built storage: ordinary role records add no native entity types.

Follow [validation policy](../../../dml/docs/validation-policy.md) with
[GHA disable decision](../19-intent-scoped-reuse/GHA-DISABLED.md) superseding development-GHA launch
wording. After future GO: focused local evidence, one final unchanged full gate, risk-based SAME
retained story independent readers. VP-001 planning revisit remains OPEN UNKNOWN; native investigation
PAUSED/private incomplete unexecuted candidate retained. No native/async/LMDB repairs, generic
cache/evaluator/scheduler/resources, extra workers/cloud/global/services/images/release/package,
source/build/story/CI/publication restart or design checkpoint commit/push follows preparation.
