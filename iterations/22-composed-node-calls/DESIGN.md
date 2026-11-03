# Iteration 22 candidate design: composed ordinary node calls

Status: **prepared for review; NOT implementation/delegation/publication GO**.
The user's “proceed” authorizes preparation after the corrected composition discussion. Exact
helper/API/role/story mechanics below are assistant recommendations, not as-built behavior or
additional user decisions. Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md).

## 1. Direction and authority boundary

Compose two ordinary funcs through the agreed calling convention:

```text
func(argument-map node) -> result node
add({a: 13, b: 29}) -> node with I64 value42
                     -> double({x: that node}) -> node with I64 value84
```

Python controls sequencing; the existing local adapter executes each fresh ordinary step. Built-in
map getters provide recorded value access inside each callable. Arithmetic remains explicit Python.
The logical callable gets no implicit graph/provenance navigation. This is a cooperative interface,
not a security sandbox, purity certification, scientific-validity or complete-capture guarantee.
Vocabulary follows the [glossary](../../../dml/docs/spec-next/glossary.md).

The user proposed including `add(29,13)`: its named MAP `{a:29,b:13}` differs from `{a:13,b:29}`,
so its add reuse key differs even though both results have value42. Their downstream MAP `{x:42}`
is equal, so downstream double reuse may match. Do not infer commutativity or sort values to normalize
argument permutations. Insertion order of the SAME key/value pairs does not change canonical MAP
identity. A fresh repeated `add(13,29)` separately tests the SAME computation key/different attempt.

Candidate scope: explicit two-func composition, public successful-producer validation, own requests,
one known downstream reuse selection and pinned readers. No new result-extraction primitive is
presumed. Source findings below supersede the assistant's earlier implication that one was missing.

## 2. Existing support and actual gap

Read-only preparation finds clean published DML
`a523b0bfc8c4cc9f96a36b7b62138d9645b3eab3`; Iteration21 is complete/stopped.
Relevant existing authorities:

- [Python API](../../../dml/docs/spec-next/python-api.md) and
  [implementation](../../../dml/python/daggerml/daggerml/__init__.py): `put_datum` returns a DATUM
  ID; `put_literal(datum_id)` returns a native NODE ID. Neither is a computational invocation.
- [Installed builtin authority](../../../dml/docs/internal-builtins.md) and
  [builtin.py](../../../dml/python/daggerml/daggerml/builtin.py): `Recorder.arguments` accepts owned
  semantic value nodes, including operations and normal-return nodes. `Recorder.load` already accepts
  a retained `builtin-return-v1` result DAG. Inspector validates its explicit `returned` link/value,
  trace and owning Q/full inputs. No arbitrary sub-DAG-root scalar extraction is necessary.
- Live `ValueNode` handles belong to their recorder. Loading the recorded DAG in a new recorder
  creates another temporary handle without changing graph identity, rerunning the func or stripping
  provenance. The helper should hide this bookkeeping; it is not a fundamental composition limit.
- A structural return inspector does NOT establish a successful attempt. A result publication can
  exist without successful final disposition. [Public successful S](../../../dml/docs/versioned-reuse-selection.md)
  supplies exact producing Q/T/R/F and retained all-parent history through
  [reuse_selection.py](../../../dml/examples/reuse_selection.py)'s PUBLIC `select`/`inspect`.
- [Current bridge](../../../dml/examples/builtin_workflow.py) hard-codes sum-pair intent, choice,
  binding names and one S. It is not a general ordinary-func dispatcher or computed-source bridge.
  Its old roles/APIs should remain unchanged, rather than acquiring undocumented new meanings.
- [Caller Q](../../../dml/docs/spec-next/caller-requests.md),
  [synchronous exchange](../../../dml/docs/spec-next/repository-execution.md),
  [local execution](../../../dml/docs/spec-next/local-execution.md) and
  [transfer](../../../dml/docs/spec-next/transfer.md) already supply the ordinary-step protocol.

Recommend NEW example-local public-API helpers and captured logical sources, not a new native entity,
installed evaluator, private role reader or arbitrary func registry. No missing C/builtin runtime
operation is established by inspection. Prefer leaving installed builtin/local/exchange/transfer
code unchanged; a demonstrated need must be explained and reviewed before expanding that surface.

## 3. Two explicit normal bindings and value contracts (candidate)

Use two fixed nonreserved intent URIs, illustratively `urn:example:node-add` and
`urn:example:node-double`, each with one captured local-Python binding. Exact spellings are refinable.
Both wrappers use installed `builtin.publish_callable`, immutable pinned map-get-v1/list-get-v1
binding IDs and captured logical source bytes; no checkout-only child imports or mutable ref lookup.
The list binding is required by the existing wrapper interface but no list-get executes in this story.
No builtin-version promotion or generic implementation menu is needed; Iteration21 already covers it.

Logical code reads `a`/`b` through two ordinary `ops.map_get` calls, or `x` through one. Require exact
I64 operands; BOOL/F64/coercions reject. Return `ops.literal(Datum.i64(...))`. Inputs contract:
add EXACT names `a,b`; double EXACT name `x`. Validate declared contract before Q; logical code also
validates kinds. Bounds/overflow remain native I64 rules, not Python unbounded-integer semantics.
The trusted wrapper publishes the explicit normal result profile in the unchanged child batch.
No requirement to record a new arithmetic builtin or every Python arithmetic instruction.

A small common example helper may take explicit func/binding/input names and control, accepting only
these two declared profiles. This is explicit authoring, not dispatch-by-URI, a registry, scheduler,
recursive evaluator or automatic dependency execution. Fresh dispatch stays a separate explicit
existing adapter call after recorded Q. Do not relax reserved `dml:` external-intent guards.

## 4. Successful returned nodes as sources (candidate)

For each completed add, explicitly capture successful S under a NEW immutable known slot. In this
example an upstream S is a validated producer witness, not an instruction to cache or automatically
reuse add. Before downstream argument construction:

1. Complete public S inspection at the pinned caller basis, with validation scratch/native handles
   closed BEFORE the target authoring write. Require this add intent, declared binding/input profile,
   successful exact producing Q/T/R/F and retained history.
2. Inspect R using installed `builtin.Inspector`; require the explicit normal-return role, I64 value,
   owning request/inputs equal to S's original Q/inputs. Unknown/failure/provisional/unretained or
   mismatched evidence rejects; no scalar copying as a fallback.
3. In a new recorder, `load(S.result)` and `arguments({"x": result_handle})`. Use the OUTER normal
   result node as the argument source, not just its inner literal, so R's returned-node/trace/Q chain
   stays reachable. Native storage uses ordinary DAG/SubDAG carriers; conceptual result remains NODE.
4. Publish input I plus a separate composition witness C atomically in one new caller snapshot.
   Require one parent, two previously absent names and ONLY the I/C tree additions; the next decision
   uses THIS composition snapshot as its immediate basis. A reader checks that actual snapshot/parent
   and captured upstream slot, rather than guessing a construction occurrence from equal DAG content.

Recommended ordinary C role, illustratively `example-node-composition-v1`, exact fields:
`role`, `arguments` (I link/root), `key` STRING `x`, `selection-slot` STRING known upstream slot,
`selection` S link and `result` R link. Validate that this captured S equals THAT slot in C's actual
parent basis, R equals S.result, and I's x source is exactly R with the derived value. Capture S as
an immutable graph link, not merely a filename, dataclass flags or an unretained ID datum. C retains
selected T through S; R's own Q alone is insufficient to identify an attempt if several attempts
belong to one Q. Do not rely on differing R IDs to distinguish all possible producer occurrences.

C stays OUTSIDE the MAP datum and the strict existing arguments profile. Full Q inputs remain I,
with their actual R source link. The exact selected upstream attempt is separately versioned in C
and the decision basis. Do not append fields to builtin arguments or silently change native Q.
This separation is analogous to other versioned decision context, not a new implicit argument.
A reader reports I and C together as requested provenance; it must not say Q.inputs alone includes
an attempt witness. Captured C/history remains authoritative if a convenience slot later changes.
For this bounded story there is exactly one computed argument/witness per double and none per add;
general mixed inputs, multi-producer lists and a unified lifecycle reader are deferred.

## 5. Own requests and one downstream reuse choice (candidate)

Effective matching is canonical intent URI + FULL argument MAP datum ID. No new native hash/index
or mask implementation. Full bindings, arguments and C retain provenance but do not partition this
value-based key. Declare this rule explicitly; same-intent membership remains the user's result-
equivalence promise, not DML proof. Binding validation still occurs before a requested fresh/reuse Q.
Only ONE known downstream slot, illustratively `selected-double`, is needed. Upstream slots are
separate known evidence; no table/global discovery/adoption/default-policy framework is added.

Recommend NEW ordinary decision role `example-composed-node-decision-v1`, not old Dn reinterpretation.
Capture intent, exact binding/input names+links, control/action/reason and, for double, its exact C
link/name. When downstream S is present capture slot/name/S link even on a valid value mismatch.
Add is explicitly fresh in the story; do not fabricate add-cache hits or selections. Double controls
can be fixed `fresh`, `try-selected`, `require-selected`; present malformed/wrong-intent/bad-return S
errors even on mismatch, never silently becomes a cache miss. Define exact field sets/root during
implementation; do not leave a permissive arbitrary metadata bag.

Before a double decision compare C against actual retained input/source and public upstream success.
Before consuming selected-double compare its public producing Q/inputs/result/profile and inspect
its ORIGINAL decision/C chain as well, not only its equal scalar84. A poisoned nonmatching selected
entry errors; absence or valid differing MAP leaves recorded pending fresh Q. No automatic adoption.

Decision snapshot adds only its decision. Separate existing public request operation creates its
own Q/Cq. On a reuse hit, separate ordinary W links NEW Q to OLD selected final T/R, without changing
old T's producing Q, old R or old trace. Verify ACTUAL Cq parent equals THIS authored decision,
exact tree/ref/reservation/request/dimensions, before W; returned description flags alone are not
sufficient. Preserve pending Q if later W publication fails; no full-operation rollback promise,
retry/repair or fallback dispatch. Existing W convention can be reused by public ordinary authoring,
not by private selection projection or exact-binding helper delegation that rejects new full inputs.

New pinned readers expose:

- Requested add source, Q/T/R and C used to construct this double request.
- The old producing double Q/T/R and its ORIGINAL add source/C/trace on a reuse hit.
- Equal double argument values despite different actual derivations.

A summary must never present the reused old double as freshly executed with the new producer.
It can show the NEW requested dependency and a separately labelled OLD executed dependency.
Reads use public Q/S/transfer plus installed semantic inspection, not historical Python invocation.

## 6. Concrete learning and validation scope

[EXAMPLE](EXAMPLE.md) recommends EIGHT Q/SIX synchronous LOCAL attempts: initial add42/double84;
forced-repeat add42/downstream reuse84; swapped add42/downstream reuse84; changed add43/double86.
Four actual adds and two actual doubles give TEN child map-get trace positions. Standard argument
preparation/literals create no builtin invocation positions; there are no extra construction or
compatibility calls and no support Q/T. Swapped arguments have a different upstream key; neither
sum result equality nor commutativity authorizes reusing the upstream calculation in this story.

Keep builtin limits16 arguments/16 positions/64 distinct reached semantic DAGs and existing transfer
bounds. Recursively loaded producer R includes its original arguments/trace; count these before puts.
Do not raise caps to accommodate unnecessarily broad source envelopes or all historical selections.
One producer chain suffices. Inspector fixed getter recomputation is NONRECORDING validation, not a
new primitive invocation or another arithmetic execution.

Focused checks: source/return/S association including same-value wrong producer; exact named maps/
canonical ordering; distinct upstream keys/convergent downstream keys; own-Q/W and original-versus-
requested chains; poisoned selection; no new T/trace on reuse; meaningful new input+C batch rollback/
loss. [Validation policy](../../../dml/docs/validation-policy.md) owns proportionate selection: one
final worker unchanged full-v after future GO, one installed story, risk-based independent focused/
SAME-history NONEXECUTING review, not duplicate computation/full or whole-source-inventory rituals.

Development [GHA stays disabled](../19-intent-scoped-reuse/GHA-DISABLED.md), intentionally NOT RUN,
not pass/fresh platform assurance. [VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md)
revisited at planning remains OPEN UNKNOWN with existing owner/conditions; this uses unchanged
synchronous local lifecycle, not async/LMDB/open repair. Related recurrence/needed changes require
fresh scope/triage. Native19 investigation PAUSED/private candidate incomplete-unexecuted retained.

No implementation/source/spec/glossary/diagram changes, tests/build/install/story/worker/native
probe/CI/experiment/service/image/commit/push accompanies preparation. BOTH builds/source remain
coordinator-owned. Read candidates for review, then obtain separate GO. No extra agent/cloud/global/
release/package/later feature/design checkpoint publication; completed21/paused19 scope is not inherited.
