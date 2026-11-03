# Iteration 24 worked candidate: outer and inner reuse

## Subsequent GO and pre-edit refinement

The user declared Iteration24 GO; [coordination](COORDINATION.md) records implementation authorization.
Reviewed [alternative B](PRE-EDIT.md#3-coordinator-decision-clarification-versus-real-redesign) preserves
this4outerQ/3outerT/6leafQ/5LOCAL/14getter story: actual outer getters enforce a,b I64, then add
receives ORIGINAL exact input-map NODE. Only downstream double map is newly constructed from exact
add R. TWO maps rather than the original THREE; separate outer/leaf owning ledgers keep fourteen
actual positions even where immutable operation content shares. No source projection/cap increase.
Exact prospective union/reservations required before launch; nothing here is executed evidence.
Original candidate prose below retained where superseded by this explicit refinement.

Status: **illustrative plan for review; NOT executed evidence or implementation GO**.
Read [DESIGN](DESIGN.md) and [HANDOFF](HANDOFF.md). The in-process outer adapter, new outer roles,
conservative identity rule, controls and counts are assistant candidates, not as-built behavior.

## 1. Prepare closures without invoking them

Prepare exact I64 add(`a,b`) and double(`x`) leaf closures. Their captured bindings use the existing
local Python adapter and map-get-v1. Leaf arithmetic is Python with checked I64 range, not a new
native operation. Prepare supported map-get-v2 leaf alternatives for the later convenience defaults;
those alternatives are metadata only, not compatibility jobs.

Create outer C-A explicitly capturing old add-A, double-A and outer getter-v1. Its new in-process
binding captures exact composition/integration bytes and immutable environment E-A. No mutable
name is resolved by the running func. Old closure/source/helper APIs remain unchanged.

Create outer input nodes for `{a:13,b:29}` and `{a:29,b:13}` with their actual source ledgers. The
full MAP values differ, although both leaf additions are expected to return42. No Q/T/getter call
is created by bootstrap, closure authoring, default promotion or explicit selection publication.

## 2. Four outer requests

The finite application invokes the fixed outer logical func through the proposed synchronous
in-process adapter. Fresh leaf work uses unchanged synchronous local exchange in separate owned
execution repositories. The application owns/reaps FIVE direct leaf children; no outer worker or
async execution-client owner exists.

| Outer Q | Outer input/control | Inner add | Inner double | Outer satisfaction |
| --- | --- | --- | --- | --- |
| OQ1 | `{a:13,b:29}`, explicit fresh | IQ1 fresh ->42 / IT1 | IQ2 fresh ->84 / IT2 | fresh OT1 ->OR1/value84 |
| OQ2 | SAME full MAP, require selected outer | no inner Q | no inner Q | OLD OT1/OR1/value84; no outer T |
| OQ3 | `{a:29,b:13}`, try selected outer -> mismatch | IQ3 fresh ->42 / IT3 | IQ4 require selected double ->OLD IT2/IR2 | fresh OT3 ->OR3/value84 |
| OQ4 | `{a:13,b:29}`, explicit outer fresh | IQ5 fresh ->42 / IT5 | IQ6 explicit double fresh ->84 / IT6 | fresh OT4 ->OR4/value84 |

Conceptual labels are not actual occurrence IDs or predicted content hashes. The outer and leaf
request/attempt profiles are DISTINCT; old local Q/T validators do not validate OQ/OT.

After OQ1, explicitly adopt its successful outer attempt in `selected-double-sum` using the NEW
outer selection validator. Separately adopt IQ2/IT2's public successful leaf witness under the known
`selected-inner-double` slot. These are metadata actions, not more requests or automatic adoption.

Before OQ2, promote convenience defaults to the new add-B/double-B getter-v2 closures. Keep C-A/E-A/
B-A and old history byte-identical. Every request in the table explicitly chooses C-A. Each fresh
outer request captures an independent selection basis/control plan; the logical func cannot discover
history or reread moving slots. Add is explicitly fresh throughout this story.

OQ2 proves outer reuse makes ZERO inner requests/getters/call-ledger positions. Its new satisfaction
links old execution evidence, not a fabricated “empty fresh composition”.

OQ3 cannot reuse OQ1 because full outer MAP differs. Its add input also differs from IQ1. The new
add result node has value42 but different invocation/source/producer associations. Construct IQ4's
`{x:42}` argument node with THIS new add R as source; its value key matches IQ2's with the SAME
captured double closure. IQ4 gets its own Q and reuse satisfaction but creates no T or getter call.

OQ4 bypasses both eligible outer reuse and eligible double reuse by explicit controls. It proves
actual execution still uses old captured bindings after default changes. Both selected slots remain
at OT1 and IT2; fresh OT3/OT4/IT6 do not adopt. Fresh completion witnesses may be kept for inspection,
not treated as selected reuse entries or discovery candidates.

## 3. Counts and interfaces

```text
outer requests:        4       in-process outer attempts: 3
leaf requests:         6       synchronous LOCAL attempts: 5
total requests:       10       total attempts:             8
fresh OS children:     5       descendants/outer workers:  0
```

Each fresh outer invocation records two map-get positions and constructs two inner argument-map
nodes with source ledgers. Each fresh add records two getters; each fresh double records one:

```text
outer getters:         3 * 2 = 6
leaf add getters:      3 * 2 = 6
leaf double getters:   2 * 1 = 2
total map-get positions:      14
```

There are TWO ordered ordinary call positions per fresh outer attempt, SIX across the story.
These are not builtin trace positions, extra attempts or unique-content-record counts. Argument
construction uses public recorded `Recorder.arguments` ledgers; it is not counted as map_empty/
map_insert dispatch. No list-get, construction primitive, support or compatibility invocations.
Existing semantic/transfer limits apply; the worker must validate prospective reached graphs before
launch and stop/review if the proposed composition exceeds them, not silently raise caps.

The installed story executes the actual captured composition source calling `calls.invoke`; no
host precomputed answer, host-script replacement composition or mocked ordinary dispatcher. Outer
node handles are example-session handles; no ended Recorder handle passes into a later write.
Successful inner results are validated and retained before the logical func receives a node.

## 4. Requested versus executed provenance

OQ3's double slot is expected to retain:

```text
NEW OT3 call position1
  -> NEW IQ4 / captured double-A / argument node {x:42}
     -> source NEW add IR3, selected producer IQ3/IT3
  -> reuse satisfaction selecting OLD double IT2 / IR2
     -> ORIGINAL IQ2 / original argument node {x:42}
        -> source OLD add IR1, selected producer IQ1/IT1
```

MAP structure contains computational datums, not IT3/IT1. The actual input source ledger and the
separate call/witness ledger retain those relationships. Same42 does not merge producers, select an
attempt by itself or authorize a global origin lookup. Outer OR3's explicit returned node is OLD
IR2; outer execution's requested IQ4 remains distinct from IR2's ORIGINAL producing IQ2.

Outer selection validates the whole ORIGINAL outer completion, not just value84 or a serialized
success flag. Leaf selection retains existing public S authority plus fixed ORIGINAL leaf/call
association checks. Outer readers understand the NEW explicit return profile; they do not execute
captured Python arithmetic or make arbitrary DAG roots scalar-valued.

## 5. Failure evidence and SAME-history review after separate GO

Focused small tests cover inner computational failure (no next slot), malformed/reused mismatched
witness, foreign/ended node handle, unbound target/default reread, poisoned session, scope-held
across dispatch, wrong parent/tree/outer-T/slot/source association, ignored captures in keys, and
late native publication/ref/commit failure. Previously committed successful leaf work is retained
if outer execution later fails. Persistence/custody uncertainty stays UNKNOWN; no automatic retry.
Those tests are distinct from this ONE successful installed story, not extra acceptance scenarios.

Record actual incremental Q/T/slot/return/import/PID/wait/failure receipts before later assertions.
After all FIVE direct children are known wait-reaped, retire only owned operational originals and
retain inert source/packet/complete history/evidence. A final ordinary summary links the four outer
requests, three outer attempts, six leaf requests, five leaf attempts, ordered call/getter ledgers,
returns and consumed selections. It is not an eleventh request or another execution.

Fresh blocked installed NONEXECUTING readers inspect SAME complete history through public typed
reads, builtin inspectors, public leaf S and the NEW outer structural validator. They verify actual
source bytes/adapter distinctions/exact ordered phases/old-versus-requested chains/counts/selected
slots/immutable bytes; no source exec, arithmetic rerun, new Q/T/refs/target writes or second story.
Risk-based coordinator checks stay distinct from worker runtime/full evidence.

This is not platform assurance or a native-runtime diagnosis. GHA stays disabled/NOT RUN/not pass;
native19 PAUSED/private candidate incomplete-unexecuted retained/VP-001 OPEN UNKNOWN. Preparation
starts no worker/build/install/test/story/reader/CI/investigation/commit/push activity.
