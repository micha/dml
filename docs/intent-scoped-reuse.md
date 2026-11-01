# Intent-scoped reuse and explicit selection removal

Status: informative **example-local** convention over existing public APIs.

## Authority boundary

This page owns [`intent_scoped_reuse.py`](../examples/intent_scoped_reuse.py)'s NEW Mi/Di
conventions and intent-only matching policy. It is not a native entity, cache framework,
registry or execution adapter. [Implementation selection](versioned-implementation-selection.md)
owns the unchanged fixed two-member definition/menu/choice. [Selection](versioned-reuse-selection.md)
owns successful producer S/V inspection. [Caller requests](spec-next/caller-requests.md),
[preparation](spec-next/repository-execution.md#preparation-and-retained-workspace),
[transfer](spec-next/transfer.md) and [Python API](spec-next/python-api.md) own exact Q,
complete native history and storage/lifetimes. [Glossary](spec-next/glossary.md) owns vocabulary;
[validation policy](validation-policy.md) owns assurance/CI disposition.

## Declared equivalence, two distinct authorities

This example treats same-intent membership as the user's declaration of result equivalence.
Reuse matching is canonical **intent URI + exact full input DAG ID**, including typed values,
all declared arguments and producer witnesses. Producing binding is historical provenance,
not an additional matching dimension. A deliberate material change in result semantics belongs
to another intent; an implementation defect violates its declared intent. This policy is not
DML proof of scientific correctness, environmental capture or equivalence. Independent trials
and adapter validation require explicit fresh work, not reuse or result-content deduplication.

Resolve the requested implementation through PUBLIC definition inspection/preparation FIRST.
A reused result has two independent authorities:

- NEW own Q records the requested full binding and exact full inputs.
- PUBLIC `reuse_selection.inspect` validates the selected historical producer's actual
  binding/Q/T/R/F. Producer binding need not remain in the current menu.

NEW ordinary W keeps the original four fields/root and links NEW requested-binding Q to exact
OLD producing-binding T/R. Old T still links its ORIGINAL producing Q; no new T, fabricated
completion packet, adapter launch or cleanup occurs. The NEW helper authors W directly with
public native transactions AFTER exact own-Q validation. It never passes forged expected data
into old helpers. Existing [exact-binding reuse](explicit-attempt-reuse.md), S/V selected-reuse
and [binding-scoped table](multi-input-reuse.md) APIs and roles remain unchanged and continue
rejecting cross-binding requests. Mi/Di are not a silent reinterpretation of M/Dm or old D.

## Strict bounded Mi, immutable producer slots

One explicitly named tree slot holds Mi with exactly `role` STRING
`example-intent-scoped-table-v1`, canonical URI `intent` (root), and sub-DAG `entries`.
There is no binding field. Entries has literal STRING role root
`example-intent-scoped-entries-v1` and zero to sixteen named entry links. Each row has exactly:

| Field | Node |
| --- | --- |
| role | literal STRING `example-intent-scoped-entry-v1` |
| inputs | exact full input sub-DAG |
| selection | captured producer S sub-DAG, row root |
| selection-slot | literal STRING identifying S's unique current tree slot |

Row key `input-<full input DAG ID hex>` renders an existing identity, not a new hash/facet/mask.
Inspection validates ALL rows through PUBLIC S inspection at the exact query commit, checks
S DAG ID/intent/full inputs and current slot cross-links, retaining actual producer binding.
Multiple producer bindings can coexist. Invalid nonmatching rows, shape/root/type/key/cap/name/
slot mismatches or wrong intent error, not fallback. No history or other table is searched.
Complete reached native/all-parent/composite closure remains mandatory on every path.

## Separate capture, adoption and removal

```python
import intent_scoped_reuse as tables
import reuse_selection as selections

empty = tables.define_table(repository, commit=C, table_name="table",
    intent_uri="urn:example:double", ref="empty")
# Separately execute/receive successful F using actual producing binding A.
s = selections.select(repository, commit=F, slot="selected-a2",
    binding_name="binding-a", inputs_name="inputs-2", intent_uri="urn:example:double",
    packet=packet, expected_file=expected, ref="captured-a2")
indexed = tables.select_entry(repository, commit=s.commit, table_name="table",
    selection_slot=s.slot, ref="indexed-a2")
removed = tables.remove_entry(repository, commit=indexed.commit, table_name="table",
    inputs=s.inputs, ref="removed-a2")
```

`define_table` requires an absent slot. `select_entry` inserts ONE absent exact-input key.
Capture through unchanged public `select` at a NEW immutable S slot is separate from indexing.
`adopt_entry` requires a matching old key/same intent/full inputs and a distinct PUBLIC owning
attempt occurrence, even when result content is equal or producer binding differs. Another
final-T/F description of the same attempt is not fresh work. Adoption changes only one row.

`remove_entry` requires an exact ObjectId key PRESENT in a valid table; absent key errors.
It removes ONLY that row, preserving all other row IDs/non-table entries/old S/V slots/Q/T/R/
refs/history. Removing the last row leaves a valid empty Mi. Removal is versioned state, not
S deletion, GC, a tombstone, content ban or cross-branch invalidation. Old branches and pinned
requests remain unchanged. Explicit reselection is permitted. No request automatically
rediscovers, adopts or reinserts removed results. Advisory supersession/deprecation metadata
is inert to this helper; persistent result restrictions are deferred.

Each table operation closes validation handles/scratch before a single authoring batch, has
exact `(C,)` parent/create-only explicit ref and prebuilt response. Capture/table/decision/Q/W/
execution remain SEPARATE boundaries. An unindexed complete S can survive failed adoption.

## NEW Di and exact requested own Q before W

`record_policy_request` accepts explicit intent/input/table/decision names, requested
implementation `default` or menu label, independent reuse `default`, `fresh` or
`reuse-selected`, and distinct decision/submission/optional reuse refs. It never dispatches.

- Reuse default consumes the named table; valid table/key absence records pending fresh Q.
  Explicit selected reuse requires a hit BEFORE Di/Q.
- Fresh or execute-by-default ignores unused table APPLICATION framing but still validates
  all reached native history/requested binding/inputs. Missing input tree entry is an error.
- No default/table/S change or automatic adoption occurs while requesting.

Di has role `example-intent-scoped-decision-v1`, captured definition/choice/requested binding/
full inputs, names/overrides/reasons/action, and table/row/S links only when consumed (table on
valid miss too). Actual one-parent basis pins its decision. Di adds ONLY its absent named entry.
Public Q recording then adds exact own Q. Before W, the helper checks ACTUAL Cq parent is
THIS newly authored Di commit, public exact non-None Q/prepared dimensions, returned fields,
submission/reservation/tree identity. A coherent different Di/Cq with a lying response base
rejects; comparing response flags alone is insufficient.

The pinned reader recomputes Di from its ACTUAL parent, publicly validates requested Q separately
from historical producer S, and verifies original W's own-Q/exact T/R/only-W delta and exact
`(Cq,)` parent. Returned W IDs/refs/description dimensions are also checked. Moving refs or later
removal cannot retarget already-recorded Q. Partial producer authority/Q/T/R swaps reject; a
coherent different deliberately selected successful result is not fraud detected against
unstated intentions. Names use existing profile/collision rules; functions only, no new CLI.

## Failure and evidence limits

A late direct-W failure can leave complete Di and pending own Q while the entire W batch aborts.
Late response validation can leave complete Di/Q/W. Table/removal failure leaves prior state;
precommit author-only loss leaves no batch, postcommit response loss can leave complete publication.
Inspect explicit refs; no automatic repair/retry/relaunch or whole-driver rollback follows.
Existing native profiles/handles/maps/transfer limits apply. No physical power-loss,
distributed exactly-once, authentication or process-tree supervision claim is added.

[Focused authority controls](../tests/python/test_intent_scoped_reuse.py),
[two-authority/removal regressions](../tests/python/test_intent_scoped_edges.py),
[representative NEW direct-W/removal atomicity/loss](../tests/python/test_intent_scoped_atomicity.py)
and [default-safe controller checks](../tests/python/test_intent_scoped_story.py) distinguish
real native checks from substituted fault controls. Existing unchanged S/Q/native/exchange
fault suites retain ownership. No new coverage exclusion/threshold/skip/budget/runner change.
Ordinary Mi/Di/W introduce no LMDB entity/key family; diagram storage model stays unchanged.

The explicit installed [story](../tests/intent_scoped/story.py) captures A=`2*n`, B=`n+n`:
SIX normal Q / FOUR synchronous LOCAL attempt occurrences / zero acceptance support occurrences.
A2->4, A3->6, B reuses A2, fresh B2->4, A reuses explicitly adopted B2, remove I2 then default
B2 actually executes fresh4 without adoption. I3 survives; true common-parent keep/adopt siblings
retain A/B choices. Reaped children precede public completed observation/receive/capture;
original paths become unavailable only after those required actions. Fresh copied installed
nonexecuting clients actively block transports/spawning and read transferred native history.
Controller/policy copies and hashes are retained BEFORE runs. No fifth computation or Batch/
SSH/Docker/image/service; this is not actual cross-adapter transport evidence. Commands/results/
original failures/qualifications belong to [Iteration19 RESULTS](../../dml-design/iterations/19-intent-scoped-reuse/RESULTS.md),
independent acceptance to [REVIEW](../../dml-design/iterations/19-intent-scoped-reuse/REVIEW.md).
VP-001 stays OPEN UNKNOWN; a pass is not older-runtime diagnosis or a standing waiver.
