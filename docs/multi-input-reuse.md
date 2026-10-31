# Multi-input reuse selection (informative example)

## Authority boundary

This document owns the ordinary bounded table/new-decision convention in
[`examples/multi_input_reuse.py`](../examples/multi_input_reuse.py). It is example-local
public composition, not a native entity, scalable cache index or public policy framework.
[Implementation selection](versioned-implementation-selection.md) owns captured definition/
menu/choice resolution. [Reuse selection](versioned-reuse-selection.md) owns successful S/V
revalidation; [explicit reuse](explicit-attempt-reuse.md) owns original Q/W association.
[Caller requests](spec-next/caller-requests.md), [repository execution](spec-next/repository-execution.md)
and [transfer](spec-next/transfer.md) own exact Q, execution and complete native history.
The [glossary](spec-next/glossary.md) owns vocabulary and
[validation policy](validation-policy.md) owns development assurance/CI disposition.

## Exact identity, bounded known table

One explicitly named tree slot holds M with `role`, canonical URI `intent`, captured full
`binding` (root) and `entries`. The entries sub-DAG has literal role root and at most sixteen
named links. A row has exactly `role`, captured full `inputs`, captured `selection` S (root)
and literal STRING `selection-slot`. Its name is `input-<full input DAG ID hex>`: rendering
an existing ID, not a new hash/facet/mask. The effective identity is canonical intent URI,
full binding DAG ID and full input DAG ID, including typed values and producer witnesses.
Equal scalar results never establish interchangeability across bindings/inputs/attempts.

Each S remains in its own explicitly named tree slot. `inspect_table` validates ALL bounded
rows through PUBLIC `reuse_selection.inspect` at the exact query commit, checks S DAG ID/
URI/binding/full inputs and current tree-slot cross-links. Invalid nonmatching rows reject
when the table is consumed. Malformed/unreadable present state is not absence; a valid table
for another URI/binding is incompatible, not a miss. No other table or history is searched.
Over-cap publication rejects; there is no eviction, deletion, merge or approximate matching.

## Separate capture, insertion and one-key adoption

```python
import multi_input_reuse as tables
import reuse_selection as selections

empty = tables.define_table(
    repository, commit=C, table_name="double-table", intent_uri="urn:example:double",
    binding_name="binding-a", ref="empty-table")
# After a separately executed, completed and received successful F:
selected = selections.select(
    repository, commit=F, slot="selected-2-old", binding_name="binding-a",
    inputs_name="inputs-2", intent_uri="urn:example:double",
    packet=packet, expected_file=expected_file, ref="capture-2")
indexed = tables.select_entry(
    repository, commit=selected.commit, table_name="double-table",
    selection_slot=selected.slot, ref="indexed-2")
```

`define_table` creates an absent empty table. `select_entry` inserts one absent full-input
key into an existing compatible table. Fresh execution never adopts automatically. Capture
fresh successful F with existing `select` at a NEW S slot, then call `adopt_entry` at a basis
containing the old table and both selections. Adoption validates both histories and requires
a distinct owning attempt occurrence (not just a changed T/F description or equal result).
It replaces only the matching row. Old S/V slots remain intact and reachable; do not overwrite
an indexed old S slot first. An unindexed complete new S may survive a table-update error.

Each table-authoring operation closes public projections before writing, creates one commit
with exact `(C,)` parent and a create-only explicit ref, preserves all non-table tree entries,
and constructs its response before storage commit. Existing rows retain their DAG identities.
Native all-parent history supplies retention, not copied bundle bytes or literal success flags.
Definition/S capture/table update/decision/Q/W/execution are SEPARATE transactions. A later
error is not whole-workflow rollback or permission to repair/retry/relaunch automatically.
Inspect explicit refs after an uncertain/lost response. Close other native handles first.

## New Dm, independent implementation and reuse decisions

`record_policy_request` takes explicit intent/input/table/decision names, implementation
`default` or captured label, independent reuse `default`, `fresh` or `reuse-selected`, and
explicit decision/submission/optional reuse refs. It resolves the binding FIRST through PUBLIC
definition inspection and exact full-input preparation, without executing imported source.

- Reuse-by-default consumes the one supplied table. Table/key absence records fresh pending Q;
  explicit `reuse-selected` requires a matching row.
- Explicit `fresh` or execute-by-default does not consume unused table APPLICATION framing.
  Complete reached native/all-parent/composite closure is still mandatory on EVERY path.
- Reuse delegates PUBLIC `reuse_selected` at the actual Dm commit/matched S slot. It creates
  its own new Q and a separate original four-field W selecting old T/R, never another T/job.
- Defaults, M and S never change while requesting. Fresh Q requires a separate explicit
  adapter action; this helper NEVER dispatches.

Dm's new role captures exact Idef/choice/binding/inputs, names, implementation/reuse overrides,
reasons/action; M/row/S links appear only when consumed (M also appears on valid key miss).
`inspect_decision` recomputes from the ACTUAL native one-parent basis and verifies adding ONLY
that Dm. `inspect_request` uses public exact non-None own-Q preparation and optional original
four-field W validation. Returned Q/Cq/W/descriptions/refs are checked against actual pinned
native history, not latest refs or serialized flags. A late rejection preserves earlier
published batches. Old exact D/request/supersession readers are NOT generalized to Dm; existing
choice `selection-slot` still means a single S, never a table. The new table name is independent.

Table/selection/binding/input/definition/decision names used together must not collide.
Missing requested input entries are errors. Publication names/refs use the existing native
profile; separate request refs must differ. This example exposes Python functions only;
there is no new CLI/package/runtime registry or generic evaluator.

## Concrete installed workflow and limitations

[`tests/multi_input/story.py`](../tests/multi_input/story.py) is an explicitly invoked installed
workflow, never default-started. It records A(2)->4, A(3)->6 and separately fresh A(2)->4;
retains two rows; reuses both; captures a new S without changing M; explicitly adopts only I2;
creates true same-parent keep/adopt siblings; then reuses new/old I2 on those branches. Normal
history has SEVEN distinct Q and THREE local attempt occurrences, no support/fourth computation.
I3 retains its old choice on both branches without another request. Equal R4 does not merge T.

Fresh installed processes use copied application policies, not checkout runtime replacement.
The three computational children are synchronous, completed and reaped before public completed
observation/receive. Original packet/expected/workspace/B paths become unavailable only after
successful capture/reaping; original bytes remain inert evidence. Nonexecuting fresh clients
actively block transport imports/process spawning and read transferred complete native history.
This proves bounded composition/history, not external-environment capture, scientific validity,
authentication, purity, cross-binding equivalence, global discovery or generic cache performance.
No Batch/SSH/Docker/image/service is needed. Supersession integration, masks/facets, resource/
scheduler/cache lifecycle and unified readers are deferred. Older UNKNOWN runtime causes and
VP-001 remain separate from this example's evidence; a pass is not their diagnosis or waiver.
