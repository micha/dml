# Iteration 19 candidate design: intent-scoped reuse and selection removal

Status: **planning authorized; candidate for review, implementation GO pending**.
The user agreed the simplified direction and requested preparation. Exact engineering
spellings/record mechanics below are assistant candidates, not approved schema/API or
as-built behavior. Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md). Current DML remains
clean published `3b2b370f4f275d324d9c8cbc93e5a915b9c59149`; completed18 stays stopped.

## 1. Agreed direction and corrections

An intent expresses the user's declaration that its implementations are equivalent with
respect to results for matching computational inputs. Different requested/producing adapters
or implementations do not alone prevent reuse. A deliberate material difference in result
semantics belongs to a different intent; an implementation bug violates its intent. Intent
membership is a declaration, not DML proof of correctness/equivalence/full capture.

Reuse identity in this slice is canonical **intent URI + exact full input DAG ID**. Full
inputs retain typed values, declared arguments and producer witnesses; no scalar-only match,
mask/facet/approximate identity is added. Producing implementation/adapter/full execution binding
remain provenance, not another matching dimension. Explicit independent trial/adapter validation
still requires fresh work. Do not equate result-content deduplication with another trial.

All prior results of an intent are conceptually eligible unless deliberately excluded. The user
subsequently simplified this turn: **remove the selected cache entry**, rather than implement
persistent result restrictions. Eligibility does not automatically select/adopt anything. This
slice still consumes an explicitly selected PUBLIC-validated successful result; failed/unknown
outcomes do not become successes. Implementation deprecation is separate and does not invalidate
prior results. No deprecation gate or persistent result-content prohibition is implemented here.

Removal affects the selected intent/input entry in a new snapshot, not every branch or historic
attempt. No automatic history search rediscovers it. Explicit reselection, or fresh work producing
the same result followed by explicit selection, remains possible. Old result-restriction discussion
(intent+inputs+result affecting equal-result attempts) is deferred, not an implicit runtime ban.
UX/shared-tree organization remains acceptable for now; feasibility is the priority.

## 2. Inspected public authorities and concrete composition gap

- [Implementation selection](../../../dml/docs/versioned-implementation-selection.md) and
  [helper](../../../dml/examples/implementation_selection.py): public strict Idef/menu/choice
  and versioned default/explicit requested binding. Exactly-two menu stays unchanged.
- [S/V selection](../../../dml/docs/versioned-reuse-selection.md) and
  [helper](../../../dml/examples/reuse_selection.py): public `select` captures producer F at a
  NEW S slot; public `inspect` validates exact producing URI/binding/inputs/Q/T/R/F from retained
  repository history. No inspect-by-S-ID, generic producer registry or private role codec.
- [Iteration18 table](../../../dml/docs/multi-input-reuse.md) and
  [helper](../../../dml/examples/multi_input_reuse.py): strict bounded ALL-entry inspection,
  separate capture/insert/adopt/Dm/Q/W and native closure; OLD M has binding scope.
- [Explicit reuse](../../../dml/docs/explicit-attempt-reuse.md) and
  [helper](../../../dml/examples/explicit_reuse.py): original four-field W and separate Q/W
  publication. **Its `reuse_attempt` checks full binding before/after Q.** Likewise
  `reuse_selection.reuse_selected` calls private projection plus exact-binding `_match`.
  Neither existing operation supports this new cross-binding policy unchanged.
- [Caller Q](../../../dml/docs/spec-next/caller-requests.md),
  [public preparation](../../../dml/docs/spec-next/repository-execution.md#preparation-and-retained-workspace),
  [transfer](../../../dml/docs/spec-next/transfer.md),
  [local execution](../../../dml/docs/spec-next/local-execution.md) and
  [Python API](../../../dml/docs/spec-next/python-api.md) retain authority over exact Q,
  successful producing history, native closure/storage/lifetimes and dispatch.

Recommended solution: NEW example-local helper composes PUBLIC `selection.inspect`, public
preparation/`record_exchange_request`, and public native transactions for ordinary W authoring.
Do NOT call old exact-binding reuse with forged producer expected data or weaken its checks.
No need to consume `_projection`/`_definition`, decode S/V headers, expose private success readers
or add a native/runtime mechanism has been established. Direct W authoring duplicates only the
small ordinary association publication, not successful-history decoding; factor a narrow public
example seam only if concretely beneficial and reviewed. Report any genuine seam gap before
expanding scope. Old helpers/tests retain exact-binding behavior; new owner documents the new
policy, not a silent reinterpretation of old helper contracts.

## 3. Recommended ordinary intent table (candidate)

NEW role/table convention Mi, explicitly named in the ordinary snapshot tree:

| Field | Candidate value |
| --- | --- |
| role | literal STRING for new intent-table role |
| intent | canonical URI literal; table root |
| entries | sub-DAG with literal role root and zero to sixteen entry links |

No binding field in Mi. Each row has exact role/inputs/selection/selection-slot, root=selection;
key `input-<full input DAG ID hex>`. This losslessly renders an existing identity, not a new
hash. Retain unique S tree slots/current slot-to-S links. Inspection validates ALL rows through
PUBLIC S inspection at the exact query commit, matches table intent/row inputs, and preserves
each S's ACTUAL producer binding. Rows of different producer bindings may coexist. Do not demand
producer binding equality with the requested choice or membership in the current two-member menu;
validated historical Q's intent and full inputs supply the reuse dimensions. No history search.

Keep strict field/root/node/datum/key/cap/name/collision checks, exact typed full closure and
bounded profile. Old binding-scoped M/old Dm are NOT accepted as Mi/new decision by similarity.
Use new example role names/helper/pinned reader; no migration requirement or silent old-reader
unification. Selection S/V itself stays unchanged and records the producer, never relabelled.

Consumed present malformed/nonmatching invalid row errors, not absence. Valid key/table absence
permits default fresh; explicit selected reuse requires hit. Wrong URI is incompatible, not miss.
Fresh/default-execute ignores unused table application framing but still validates ALL reached
native/all-parent/composite history, requested binding and inputs. Input entry absence is an error.

## 4. Table operations and removal

Recommend explicit finite Python operations (`define_table`, `select_entry`, `adopt_entry`,
`remove_entry`, `inspect_table` are illustrative spellings):

- Define absent empty intent table, no implementation installation or Q/T.
- Capture successful producer F through unchanged public `select` at NEW immutable S slot,
  specifying its ACTUAL producing binding/input names. Separately insert one absent key.
- Adopt a separately captured NEW S for the SAME intent/full inputs and a distinct validated
  attempt occurrence. Binding may differ; equal result content is permitted, no new trial is
  inferred from a changed final-T/F description of the same occurrence.
- Remove explicit exact input ObjectId from a valid present table; require existing row, otherwise
  error (recommended non-idempotent candidate). Replace only Mi; preserve all other rows and tree
  entries, including the removed row's old S/V slot and every Q/T/R/ref/history object. Empty Mi
  remains a valid empty table. No S deletion, tombstone, GC, ban or cross-branch propagation.

Each operation is one storage batch, closes validation handles/scratch BEFORE writes, preserves
non-table entries, uses exact `(C,)` parent/create-only explicit ref/prebuilt response. Other rows
retain IDs. Capture/table adoption/removal/default/decision/Q/W/dispatch remain separate. Removal
is versioned state, not physical deletion. Lost response may leave complete publication; inspect
explicit refs, never repair/retry/search/relaunch automatically. A failed update may leave complete
unindexed S. An already-recorded request is pinned: later removal cannot retarget or unsatisfy it.

## 5. New request decision and two bindings

Recommend new ordinary decision Di capturing strict definition/requested choice/requested full
binding/full inputs; names/independent overrides/reasons/action; consumed Mi/row/S links only when
used (Mi also on valid miss). Its native actual parent pins the basis. Expose requested binding
and validated producer binding separately in owned/read descriptions when reusing; producer
binding can be read from S, need not be copied as a second redundant authoritative record field.
No S on fresh decisions; no false claim requested adapter ran on a reuse hit.

Resolution FIRST chooses requested implementation and publicly prepares it/full inputs without
execution. ALL consumed S histories revalidate. Compare intent/full inputs, NOT producing binding.
Publish Di, then public own Q/Cq with REQUESTED binding and exact actual Di parent. Revalidate
returned exact non-None Q/Cq via public preparation/reservation/ref/tree identity BEFORE W writes.
Then one separate batch adds original four-field W (role/request/attempt/result, root=result) at
`reuse-<new-qid>`, exact `(Cq,)`, only W tree delta/create-only ref/prebuilt response. W links NEW Q
(requested B) to OLD T/R (producing A). T still links its ORIGINAL producing Q_A; do not forge a
completion packet for Q_B, rewrite T/Q_A or feed Q_B as producer expected authority.

Pinned reader recomputes Di from ACTUAL parent and publicly validates both exact requested Q and
selected S producer authority; verifies W's own Q/exact old final T/R and spine. Native/ref/returned
submission and satisfaction identity are compared, not response flags or latest refs. Partial
producer binding/Q/T/R swaps reject, even when scalars match. A coherent other selected successful
result is another deliberate choice, not fraud detected against unstated intentions.

Late returned-Q/W rejection may leave Di/Q/W already published. A W batch failure leaves own Q
pending and no partial W batch; do not infer whole-driver rollback. No automatic adoption/default/
removal while requesting. Removed key default miss creates pending fresh Q; only a separate adapter
action executes it. Explicit reuse on that missing key errors BEFORE new Di/Q. Separate deprecation
metadata is inert advisory state, not result-eligibility authority or lookup input in this helper.

## 6. Concrete evidence and limits

[EXAMPLE](EXAMPLE.md) recommends SIX Q/FOUR synchronous LOCAL attempts: A(2)->4, A(3)->6,
B-request reuses A2, explicit B(2)->4, A-request reuses adopted B2, remove I2 then default B(2)->4.
Two inputs make unrelated-entry preservation real; the fourth attempt specifically proves fresh
execution after removal. Zero support occurrences IN acceptance history. Metadata/branch/offline
transfer/read operations add none; existing focused fixtures are separately reported. No fifth
attempt/producer/Batch/SSH/Docker/image/service needed. This does not claim actual cross-adapter
transport proof; adapter identity no longer partitions semantic reuse, runtime adapters unchanged.

Primary negatives: different intent/full input types/producer witnesses, poisoned nonmatching row,
forged producer authority/oldQ substitutions, requested-vs-producing binding/ref/parent confusion,
old helpers still reject cross-binding, wrong table roles, same occurrence adoption, missing remove
key and failed remove preserving old proof. Representative NEW removal and direct-W atomicity/
author-only loss tests need predicted genuinely absent actual-A rows (including unrooted old bytes),
not a replay of all old S/Q/W/exchange faults. Useful mutations target binding exclusion only in
new policy, mistaken requested-to-producer overwrite, forgotten own-Q validation, remove-other-key,
automatic reselection/adoption. Intended failures must not be collection/import/ref collisions.

Follow [validation policy](../../../dml/docs/validation-policy.md), preserve thresholds/skips/
budgets/runners, one stable worker full-v and risk-based independent checks. No duplicate full/
installed story/source census. Capture controller/copy hashes BEFORE runs; preserve failed oracles/
original scripts/logs before corrections, prefer corrected NONEXECUTING checks on SAME history.
Ordinary Mi/Di/W adds no LMDB keys/boxes; review diagram against actual technical claims, not plans.

VP-001 planning revisit: OPEN/UNKNOWN, Iteration18 green is not prior-runtime diagnosis or standing
waiver. No async/LMDB/affected-story change presumed; pause/separately scope related changes or
recurrence. No worker/source/spec/diagram/build/story/image/CI/experiment/provisioning/commit/push
started. Read three candidates for review, then separate GO. No design checkpoint requested.
