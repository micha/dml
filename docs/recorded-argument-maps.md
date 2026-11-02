# Recorded argument maps and datum-keyed reuse

Status: implemented **example-local prototype**, informative, not core computational primitives.

## Authority boundary

This document owns the fixed ordinary-DAG conventions and cooperative callable interface in
[recorded_maps.py](../examples/recorded_maps.py), [datum_reuse.py](../examples/datum_reuse.py),
[logical funcs](../examples/argument_map_funcs.py) and
[captured binding assembly](../examples/argument_map_binding.py).
[Native datums](spec-next/records.md#datum-model), [objects](spec-next/objects.md),
[Python values/handles](spec-next/python-api.md), [local execution](spec-next/local-execution.md),
[caller Q](spec-next/caller-requests.md), [exchange](spec-next/repository-execution.md) and
[transfer](spec-next/transfer.md) remain authoritative for their unchanged public contracts.
[Successful S selection](versioned-reuse-selection.md) supplies historical success authority.
Old exact-binding/full-input and intent/full-input helper roles/APIs are unchanged.

## Value structure versus construction

Native MAP key/value children are **datum IDs**, never node/provenance IDs. This prototype
restricts the *argument map* to at most16 STRING-key entries; an argument value can itself be
any native typed scalar/collection with complete datum closure. Nested collection traversal
through the callable interface is not implemented. Native STRING NFC, typed identity, MAP
canonical key ordering, LIST order and F64 canonicalization remain unchanged.

Fixed eager Python metadata operations record their performed construction as ordinary DAGs:

| Role / root | Exact fields (all include literal `role`) |
| --- | --- |
| literal-source / result literal | source DAG link, name STRING, node ID BYTES, result literal |
| returned-source / result literal | immutable selection slot STRING, selection S link, returned R link, selected return-node ID BYTES, result literal |
| operation / result literal | opcode STRING `map_empty`, result literal empty MAP |
| operation / result literal | opcode `map_insert`, prior/key/value source DAG links, result literal new MAP |
| operation / result literal | opcode `map_get`, map construction link, key literal STRING, result literal selected datum |
| input I / arguments literal | arguments MAP literal, construction DAG link |
| returned R / return literal | return literal, trace DAG link |
| trace / role literal | owning request Q link, full input I link, ordered `access-00`…`access-15` DAG links |

Exact role constants use prefix `example-recorded-maps-v1`; inspectors reject extra/missing
fields, wrong roots/types/opcodes, incorrect source/value associations and wrong owning Q.
Primitive records are not lazy executable native nodes, general evaluation or separate Q/T.

`literal_source` selects an explicit DAG currently named in the pinned basis tree and an exact
literal node name. Its immutable descriptor retains source DAG/node/name even if that original
direct tree name is subsequently removed. Later inspectors accept the descriptor from complete
pinned **all-parent typed closure**, not a latest ref or an arbitrary unrooted DAG ID. Literal
source values may be collections; when used as a construction/prior, bounded STRING MAP rules
are checked **before** authoring input/insertion, consistently with subsequent inspection.

`returned_source` calls public `reuse_selection.inspect` on an explicit immutable S slot,
requires its original successful F/Q/T/R/full I authority and this exact returned profile, then
selects the declared return literal. Arbitrary equal-root DAGs, failure/evidence, swapped S/R/
node/value and caller-supplied value flags are not authority. The S slot/link and original full
Q remain recorded. Inspection does not replay arbitrary Python arithmetic or certify validity.

Inspection recomputes only empty/immutable insertion/getter recipes; duplicate canonical keys
(including NFC-equivalent strings) and missing keys error. Replacement is deferred. The bounded
reached profile counts operation/source descriptors, selected literal-source DAGs, inputs,
returns/traces and distinct getter recipes, at most64. Sharing is deduplicated by record/role;
trace positions retain repeated accesses. Prospective authoring reserves the new record(s)
**before** publication; the reserve is conservative when output content might already exist.
Complete native closure separately follows every parent, anonymous node and composite child
under the unchanged transfer profile. Profile limits are not repository/runtime quotas.

## Datum-only logical callable

```python
import daggerml as d

def double(arguments, values):
    x = values.map_get(arguments, "x")
    if x.kind != "i64":
        raise ValueError("double requires I64 argument")
    return d.Datum.i64(x.value * 2)
```

`invoke` validates pinned full I, closes native handles, supplies its copied MAP Datum and a
bound `DatumAccess` with only the documented `map_get(arguments, string_key)` method. It returns
a copied Datum, not a node/source/producer handle. It permits only the bound argument-map value,
not arbitrary `get_datum(id)`/graph/ref/context navigation. It associates the access recipe with
**THIS invocation's actual construction**, never a global equal-datum origin registry. A returned
collection Datum still contains value-structure child IDs, not provenance capabilities.

The logical callable explicitly returns Datum. Python arithmetic remains inside its boundary.
The trusted wrapper records actual successful getter recipes in order, pins owning Q/full I,
then authors trace/R and existing public `local.publish_result` in ONE child storage transaction.
Access/validation/arithmetic errors before publication use unchanged local failure outcomes;
durable failed access traces are outside the profile. A discarded trace is not evidence no
access occurred.

[Binding assembly](../examples/argument_map_binding.py) captures the example-local support and
func bytes into standalone source, creates named modules and compiles with their owning source
filenames; children do not read those paths or import uninstalled checkout example modules.
The child uses installed public DML. Captured filenames are diagnostic/coverage attribution,
not captured interpreter/import/environment identities.

This is **cooperative interface separation, not a security sandbox or purity proof**. Trusted
Python can deliberately use imports/globals/introspection; the wrapper retains local-user and
repository recording authority. No complete hidden-dependency prevention/full capture or
scientific/reproducibility guarantee follows.

## Md table, Dd decision and two provenance chains

NEW `example-datum-reuse-table-v1` stores canonical intent URI, fixed profile and an ordinary
entries DAG. Zero to16 rows use `datum-<MAP datum ID>` keys. Each row stores argument-map literal,
original **full I**, immutable successful S slot/link. ALL rows—including a nonmatching row—are
revalidated publicly for original intent/full Q, construction, success and returned profile.
Wrong URI/profile/old Mi role/poisoned rows error, not miss. Literal42 and computed42 can yield
the same MAP datum while their construction/full I differ. Matching in this helper uses canonical
func intent+MAP datum; producing binding is retained separately, not compared as a reuse key.

Explicit `select_entry`, `adopt_entry` and `remove_entry` mutate only one datum key in a new
snapshot, preserving other entries, old immutable S/history and branch choices. Adoption requires
a distinct successful attempt occurrence; equal values/results do not merge occurrences. There
is no automatic history search, selection, adoption, eviction or inferred default update.

`record_request` controls are `try-selected`, `fresh`, `require-selected`. Try misses remain
pending fresh; dispatch is a separate explicit public exchange action. Force fresh ignores table
application framing but not complete native closure. Require selected errors on absence. Dd
records actual basis/requested URI/binding/full I/argument datum/construction/control/action/reason
and consumed table/row/S where applicable. Separate public Q publication records its own **full I**.
Before W, the helper validates actual Cq parent equals THIS authored Dd, exact Q/reservation/
submission refs and native tree delta—not merely returned `RecordedRequest.base` claims.

On reuse, a separate ordinary W links own NEW Q and historical OLD successful T/R. No new T,
getter invocation or completion packet is fabricated. The pinned request reader exposes
`requested` input/construction separately from historical `executed` input and returned access
trace. Reused W is satisfaction association, not a new successful F for its Q. A selected old R
can remain a computed source through its original successful S authority.

## Publication and evidence boundaries

Source/primitive/input/table/Dd, public Q, W and dispatch are separate boundaries. Each new
metadata publication preserves the exact basis tree except its named intended change, has one
exact parent, creates an explicit absent ref and prebuilds its response before storage commit.
Validation handles/scratch close before target writes. Inspection never writes target storage.
Late W failure can leave complete Dd/Q; response loss can leave complete publication. No implicit
repair/retry/relaunch occurs. Files, entire controllers, processes and stores are not one transaction.

The [explicit installed acceptance controller](../tests/argument_maps/README.md) executes exactly
FIVE Q/FOUR synchronous LOCAL attempts: literal42 double84, add13+29 returns42, computed42 double
ownQ/oldT reuse, add13+30 returns43, computed43 pending miss then separately executed double86.
Six successful getter positions (1+2+2+1) actually run; zero support Q/T in that history. Controllers
save incremental Q and direct-child custody/native receipts before later metadata, retain measured
prelaunch source, retire only owned original paths after known reaping, transfer the final pinned
history and inspect SAME immutable evidence with active spawn/transport blockers. Focused fixture
jobs/host publication substitutions/author-only loss actors are separate evidence populations.

No new native entity/storage relationship is added: [the as-built diagram](lmdb-entity-diagram.html)
remains accurate with Literal/SubDAG nodes, datum-only MAP children and ordinary application DAGs.
Local checks do not establish cross-platform health, native fixes or earlier UNKNOWN-cause diagnosis.
See [validation policy](validation-policy.md) and
[Iteration20 results](../../dml-design/iterations/20-recorded-argument-maps/RESULTS.md) for actual
commands/outcomes/provenance/limitations. Development GHA remains intentionally disabled.
