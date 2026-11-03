# Iteration 24 candidate design: captured ordinary calls

## GO and reviewed implementation refinement

The user's subsequent Iteration24 GO approves this bounded plan for implementation; see
[coordination](COORDINATION.md). Pre-edit review explicitly selects [PRE-EDIT alternative B](PRE-EDIT.md#3-coordinator-decision-clarification-versus-real-redesign):
outer's two getters validate a,b I64, then `calls.invoke(captured_add, ORIGINAL arguments NODE)`;
construct only double's map from exact returned add node. No reconstructed add map, source projection
or raised64 budget. Original+double gives TWO maps; three remains an upper bound. Exact shared
outer/leaf getter content still records separate owning positions; story remains10Q8T5LOCAL14getter.
Symbolic full requested+ORIGINAL evidence union50 is a planning estimate, not measured/as-built;
actual prospective union/reservations required before installed launch. Pseudocode/count descriptions
below preserve original candidate where superseded by this explicit refinement.

Status: **prepared for review; NOT implementation/delegation/publication GO**.
The user agreed to the revised direction and said “proceed”, authorizing candidate preparation.
Exact adapter, profiles, identities, controls and counts below are assistant recommendations.
Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md). Nothing here is as-built behavior.

## 1. Agreed direction and responsibility distinctions

An ordinary func can invoke ordinary callable dependencies captured at **closure creation time**.
Every call consumes an argument-map NODE and returns a result NODE. Invocation arguments remain
separate from captured dependencies; moving defaults cannot silently retarget an existing closure.

```text
double_sum(arguments):
    a = nodes.map_get(arguments, "a")
    b = nodes.map_get(arguments, "b")
    summed = calls.invoke(captured_add, nodes.arguments({a: a, b: b}))
    return calls.invoke(captured_double, nodes.arguments({x: summed}))
```

Pseudocode keys above denote strings. Proposed `nodes.arguments` uses recorded construction/source
ledgers, not an unrecorded dictionary-to-value shortcut. Neither ordinary invocation nor provenance
is hidden inside a MAP datum. The logical func actually calls its supplied interface; a host script
performing add/double and merely labelling the result an outer call would not meet this goal.

Responsibilities are not new native entities or necessarily separate services:

- Logical func: describe composition and return a node.
- DML call interface: record inner requests, resolve explicit selected reuse and return nodes.
- Execution adapter: perform fresh execution and own execution mechanics/cleanup.
- Recording integration: provide interfaces, retain source relationships and record outcomes.

“Trusted wrapper” in the earlier proposal meant the last responsibility, NOT execution adapter.
Synchronous means an invocation returns a node or reports an error before the func continues; it
need not mean same-process execution. This remains cooperative trusted Python, not a sandbox,
purity certificate, complete environment capture or independent arithmetic certification.

## 2. Read-only findings and recommended first execution arrangement

Preparation verifies clean DML `965cec450356e5f776b68bc311fa4d7eaf690519`. Relevant authorities:
[internal builtins](../../../dml/docs/internal-builtins.md),
[closure example](../../../dml/docs/closure-bound-dependencies.md),
[local execution](../../../dml/docs/spec-next/local-execution.md),
[caller Q](../../../dml/docs/spec-next/caller-requests.md),
[exchange](../../../dml/docs/spec-next/repository-execution.md) and
[transfer](../../../dml/docs/spec-next/transfer.md).

Current `Recorder.call` dispatches fixed builtins only. Recorder handles are owned by ONE write
scope; `publish_callable` holds that scope around ONE normal Python callable. Public local Q,
binding, publication and completion readers accept exact local profiles/tree/parent deltas.
Public S validates that local/exchange history, not arbitrary in-process adapter outcomes.
Local runner custody covers direct children, not descendants. Consequently, no existing API
already supplies the proposed ordinary-call interface or outer completion validation.

Recommend **ONE new example-local synchronous in-process outer adapter**, plus unchanged local
Python execution for the two fixed leaf funcs. The finite calling application runs the outer
logical func itself through that adapter; each fresh leaf call uses public synchronous exchange
in an isolated owned execution repository. All fresh leaf processes are direct children of the
same application. No asynchronous launch/observer, RPC server, outer subprocess, descendant worker,
thread, detached service or production dispatcher is needed.

This is a recommended engineering arrangement, NOT another user decision or an established
feasibility result. Do NOT disguise the in-process outer attempt as `local-python-binding-v1`:
its adapter has different mechanics, no subprocess exit/cleanup and no enforced interpreter timeout.
It receives separate example-local binding/Q/T/completion/selection profiles. It cannot be fed to
old `local.run_request`, exchange F validators or public local S. The leaf paths keep those contracts.

Only the fixed captured logical source is runnable by this adapter. No arbitrary Python evaluator,
URI import, source fetch, recursive closure executor or dynamically installed handler. Fixed finite
straight-line code/call counts are not a portable wall-clock limit on in-process Python. A need for
arbitrary code timeouts/isolation is outside this slice, not permission to weaken existing deadlines.

Prefer NEW example-local files and public APIs, unchanged installed/native runtime. Before coding,
review the concrete adapter/phase/handle design; demonstrated missing seams need coordinator review
BEFORE expansion. This candidate adds ordinary conventions, not a native closure/call entity.

## 3. Captures and bounded callable identity

Recommend strict ordinary descriptors for:

- Leaf closures: fixed add(`a,b`) and double(`x`), exact captured local B/source bytes and supported
  getter bindings. Addition/multiplication enforce I64 including intermediate/final overflow.
- Outer E: exact captured add and double closures plus fixed outer getter bindings.
- Outer B: distinct in-process adapter role/URI, exact captured composition/integration source bytes
  and E association; no claim that old NULL-disallowed local bindings accept this profile.
- Outer C: intent, B, E and a recomputable bounded identity descriptor.

Use graph links for custody, not hashes embedded in strings alone. Build leaves, then outer E,
then B, then C; source can capture E ID but NEVER its future C ID. Authoring context is not a new
closure occurrence; identical immutable content may deduplicate. Creation/default promotion makes
no requests, attempts or primitive invocations. C retains E/B, E retains exact leaf closures/getters.

For this first slice recommend a **conservative NEW key**. The verified descriptor is the exact
binding/environment pair B/E, with the fixed supported profile/source checks applied; an ordinary
key DAG can link B/E after they exist and before C. It never links its own future C:

```text
outer: (outer intent URI, exact verified B/E descriptor, full invocation MAP)
leaf:  (leaf intent URI, exact verified leaf B/E descriptor, full invocation MAP)
```

The descriptor accounts for captured implementation/environment, not just the leaf intent URI.
Use exact supported binding/environment identities initially; do not infer equivalence between arbitrary
ordinary closures or recursively reinterpret Iteration23 K. Different recorded closures may miss
conservatively despite equal behavior. Excluding noncomputational provenance from this descriptor
would need an explicit reviewed fixed-profile rule; it is not silently assumed here.

Swapped operands differ in full add MAP. Both fresh adds return value42, so downstream MAPs `{x:42}`
match with the SAME captured double closure, despite distinct source nodes/producer occurrences.
This story needs no cross-closure equivalence. Default names, containing commit and reuse controls
are not extra key dimensions. Old examples' keys/APIs/profiles stay unchanged.

Callable capture and historical-attempt selection are different. Pin a separate caller-supplied
selection basis/control plan before outer fresh execution; it is NOT a moving lookup inside the
logical func and NOT part of C. Recommend one known outer selection and one known double selection.
Add runs explicitly fresh in this story; no add discovery/index is needed. Poisoned present selections
error even on explicit fresh/key mismatch. Fresh success never adopts automatically.

## 4. Node interface across short recording scopes

The outer logical function receives only its argument node and factory-captured value operations/
callable tokens/call interface. It receives no repository/context/history navigation. This is
cooperative authority separation, not a Python security boundary.

Recommend an example-session opaque node handle with copied value and a PRIVATE per-session
association to the exact retained semantic DAG. No fabricated/foreign/ended-session handles;
no global datum-to-origin registry. Do not pass old Recorder handles across ended scopes or allow
raw DAG/Datum IDs as callable handles. Existing `ValueNode`/Recorder APIs remain unchanged.

Each getter or argument construction opens a short owned write, re-loads the registered sources
into THIS Recorder, records through public APIs and retains the new node in a phase commit before
closing. `nodes.arguments` uses `Recorder.arguments`' actual source ledger; it records construction
but does not claim map_empty/map_insert primitive invocations. Ordered getter positions survive in
an outer session ledger across those scopes; do not reset the bound simply by opening new Recorders.

Before ordinary dispatch all repository handles/transactions close. The bridge validates the
captured target, records the call association/own leaf Q, and executes or reuses synchronously.
A successful leaf R is validated/imported/retained before a session handle is returned. The next
argument ledger uses THAT exact R as its source, not a literal42 substituted because it is equal.

Keep existing per-Recorder 16 arguments/16 builtin positions/64 reached semantic DAG bounds and
transfer bounds. Additionally fix this session to TWO ordinary positions, TWO outer getters and
THREE constructed argument maps (original input/add input/double input), without recursion. Calculate
prospective reached-node bounds on the actual new graphs BEFORE launch; opening smaller scopes is
not license to evade aggregate validation. Stop/review rather than raising inherited caps.

## 5. Occurrences, history and selection authority

Outer request/initial attempt use NEW example roles and distinct occurrences. Recommend distinct
`cq-`/`ca-` UUID payloads to avoid falsely satisfying old local Q/T occurrence/profile readers.
A metadata decision captures exact C/full inputs/controls/selection basis before Q. An outer reuse
hit creates own Q and a NEW outer satisfaction record linking OLD outer attempt/result; no outer T,
logical invocation, inner Q/T, getters or completion. Reuse is not a synthetic new execution ledger.

A fresh outer adapter records initial T BEFORE entering logical code. An immutable ordinary call
ledger has ordered slots0(add),1(double); each associates this outer Q/T, exact captured leaf C,
actual argument node and own inner Q. Link consumed public successful S or new leaf completion
witness separately. A mere inner Q is not proof of dispatch/success. On double reuse its NEW Q/input
source stays separate from OLD selected double T/R and their ORIGINAL producing add chain.

Recommend a coordinator-owned outer phase head with checked transitions. Short authoring commits
add only intended phase nodes. Public leaf F is imported under an absent explicit ref, validated,
then retained through an explicit two-parent integration commit `(previous outer phase, leaf F)`;
this is a defined example history join, NOT a generic tree merge. Preserve unrelated outer entries;
do not copy arbitrary leaf head state into the outer head or alter leaf P/U/F parent rules. Readers
check exact deltas/ordered parents and ALL-parent retention. Ref updates are local storage batches,
not a cross-repository transaction. No active writer/handle survives dispatch/import.

Outer result has a NEW explicit return profile with typed value, exact returned leaf R, outer Q/T/
inputs and ordered call/getter ledger associations. Fixed readers validate that profile using public
native reads plus builtin/leaf inspectors. They do not make `builtin.Inspector` accept arbitrary DAG
roots, broaden its strict return role or execute Python arithmetic during inspection.

Outer success completion is authored only after both calls succeeded and all fresh leaf children
have known disposition. NEW outer S validates actual decision/Q/T/phase/return history and both leaf
witnesses, then retains the completion through history; old public S remains exclusively leaf authority.
No serialized “success” flag or equal84 alone suffices. Avoid self-F IDs in a DAG created inside F;
selection is authored AFTER completion. Exact fields/roots/ref policies need pre-edit review.

## 6. Failures, validation and boundaries

Inner recorded computational failure aborts the composition without invoking later slots. Once
custody is known, record a distinct outer failure retaining the failed call/leaf evidence; no outer
success R or reuse selection. Adapter errors before/after durable publication preserve their actual
boundary. Persistence/validation/reaping uncertainty leaves inspectable partial phases/unknown outer
outcome; it does NOT justify fabricated failure/success, automatic retry or another request.

Previously successful inner work survives later outer failure. Catching an interface error cannot
allow a poisoned session to publish success. Ownership remains with the finite application until
disposition is established; never infer termination from logs or execute cleanup from historical paths.
Focused failure tests, rather than extra acceptance computations, cover these boundaries.

[EXAMPLE](EXAMPLE.md) proposes FOUR outer Q/THREE in-process outer T/SIX leaf Q/FIVE local leaf T:
TEN requests/EIGHT attempts total, FIVE direct fresh leaf launches, FOURTEEN map-get positions.
No helper/support/compatibility/list/primitive-map-construction invocations. These are proposal counts,
not current measurements. Review concrete phase/capability/fault/identity design before implementation.

After separate review/GO only: focused meaningful tests, one isolated installed story, one final
unchanged worker full-v and risk-based SAME stopped-history NONEXECUTING independent review under
[validation policy](../../../dml/docs/validation-policy.md). No duplicated full/computation ritual.
Review the [as-built diagram guidance](../../../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance)
for implemented claims; do not draw candidate roles as native entities.

Development GHA remains disabled/NOT RUN/not pass. Native19 investigation PAUSED/private candidate
incomplete-unexecuted retained; VP-001 planning revisit OPEN UNKNOWN/same coordinator owner/conditions,
no standing waiver or LMDB/open/async/lifetime investigation permission. Related need/recurrence needs
fresh scope/triage. BOTH source/builds remain coordinator-owned during preparation. No DML/source/
spec/glossary/diagram/build/install/test/story/reader/worker/CI/native experiment/service/image/commit/
push restart or extra agent/cloud/global/release/package/later turn/design checkpoint publication.
