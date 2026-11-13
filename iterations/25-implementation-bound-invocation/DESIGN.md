# Iteration 25 design candidate: implementation-bound invocation

Status: **bounded plan reviewed; separate implementation GO required**.
The user approved the revised proposal, requested preparation, then reviewed all three candidates;
see [review checkpoint](../../discussion.md#iteration25-plan-review). Exact engineering remains refinable.
The conceptual direction
below is selected; exact schemas, API names, promotion boundaries and story mechanics are assistant
candidates for review, not implemented behavior. Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md).

## Authority boundary

This document owns the proposed capability and engineering boundaries. [EXAMPLE](EXAMPLE.md) owns
proposed acceptance events/counts; [HANDOFF](HANDOFF.md) owns conditional implementation/review steps.
Existing [builtin](../../../dml/docs/internal-builtins.md),
[captured-call](../../../dml/docs/captured-ordinary-calls.md),
[LOCAL](../../../dml/docs/spec-next/local-execution.md),
[exchange](../../../dml/docs/spec-next/repository-execution.md),
[transfer](../../../dml/docs/spec-next/transfer.md) and
[validation](../../../dml/docs/validation-policy.md) documents own current behavior.

## 1. User-selected direction

- Dependencies are captured **only by implementations**, at closure creation time. There are no
  intent-level captures in this slice. Invocation arguments are supplied later.
- Intent defines the computational contract; semantic variability belongs in the argument-map value
  or a different intent, not hidden configuration that changes the promised computation.
- Reuse matches **intent URI + full argument-map value**. Implementation binding, capture graph,
  interpreter, containing commit, sources and producer occurrences do not partition this key.
- Exact requested implementation/captures and actual producing implementation/captures remain recorded.
  Same-intent membership declares equivalent result semantics, not a proof of correctness or purity.
- Every func consumes an argument-map NODE and returns a NODE. Values and actual source relationships
  stay separate. Logical code receives no implicit repository/provenance navigation.
- A new request can reuse an old attempt; no new attempt/job on a hit. Fresh work and explicit adoption
  remain separate. Default changes cannot retarget an already-created closure.
- Test-performance work is postponed. Correctness validation is not postponed.

This direction supersedes the assistant's suggested intent-level capture option and conservative
exact-closure matching **for this new slice only**. Iteration23 computational-capture keys and
Iteration24 exact B/E keys, roles and APIs remain unchanged; they are not silently redefined.

## 2. Current source findings and proposed promotion boundary

Preparation verifies clean LOCAL implementation HEAD
`15555c01e4db19a20b4de7049f776c4d995bd5e0`, not a new remote publication. Local performance commits
remain part of this baseline. Three later read prototypes were rejected/restored; the project-local
pinned tools environment is restored. No executable work was done for this preparation.

Current `builtin.Recorder.call` dispatches fixed builtin URI/version pairs; `ValueNode` belongs to ONE
Recorder scope. `publish_callable` covers one normal LOCAL publication, not nested ordinary dispatch.
Iteration24 supplies an example-local session, opaque node bridge, two-slot call interface, in-process
outer adapter and strict outer history readers. Its `Session.invoke` validates exact captured targets;
its old key includes B/E. LOCAL/exchange and public successful leaf S retain exact profiles and direct
child custody. They do not validate in-process outer attempts.

Recommend a small NEW explicitly imported installed Python module, illustratively `daggerml.calls`,
for the shared **node-call/capture interface**, plus NEW example-local adapter/history/reuse integration.
Do not promote the whole thousand-line Iteration24 validator into an installed generic framework.

Candidate maintained surface:

1. Ordinary implementation-closure construction/structural inspection: intent, executable binding and
   environment links; immutable named captures; no intent environment or computational K descriptor.
   Structural inspection is NOT executable-source validation or successful producer authority.
2. Opaque bound callable tokens and a context-owned copied-value node interface. Exact handle identity,
   owner/thread/ended/poisoned guards and source association belong to the trusted integration.
3. One `invoke(target, argument_node) -> result_node` facade used for BOTH fixed builtins and supported
   ordinary calls. Binding a builtin delegates to its existing exact URI/version dispatch. Binding an
   ordinary callable delegates to the reviewed adapter integration; no import/fetch/exec-by-URI registry.

Names/signatures are illustrative. Trusted integration explicitly binds supported targets/backends;
logical code cannot supply a backend, success receipt, raw DAG ID or arbitrary Python callable to
obtain execution authority. A callback response is not a producer proof: integration validates native
history BEFORE returning an ordinary result handle. Installed code must not import `examples/`.

Conveniences such as `nodes.map_get` may remain, but they route through the same bound invocation facade
with recorded builtin arguments. A rename of `Calls.invoke` while getters bypass the common path would
not demonstrate the proposed capability. Builtins still record primitive operations without per-primitive
Q/T; ordinary calls retain their request/attempt lifecycle. The facade does not erase adapter differences.

## 3. Concrete callable family

Use one fixed outer intent, illustratively `urn:example:implementation-bound-sum-then-double`, and two
fixed leaf intents for add(a,b) and double(x). Exact argument keys and I64 kinds are checked; Python
arithmetic checks intermediate/final I64 range. No scale capture changes their meaning.

Create A and B implementations of each leaf. A captures builtin map-get-v1/list-get-v1; B captures
map-get-v2/list-get-v1. The getter entrypoints are genuinely distinct shipped handlers with the same
semantics. Exact captured E/B/source bytes differ even if the fixed logical arithmetic source is shared.
Outer A captures add-A/double-A/getter-v1; outer B captures add-B/double-B/getter-v2. These are two
implementations of the same outer contract, not two intent definitions with environments.

Logical composition (informative):

```text
sum_then_double(arguments):
    require nodes.map_get(arguments, "a") and nodes.map_get(arguments, "b") are I64
    summed = calls.invoke(captured_add, arguments)
    return calls.invoke(captured_double, nodes.arguments({"x": summed}))
```

Forward the ORIGINAL argument-map node to add. Double's input uses the exact validated returned add
node, not a literal with equal value. Both outer and leaf getter conveniences use the common facade.
No host-script precomputed replacement for this actual logical composition.

## 4. Capture profiles, order and pinning

Recommend NEW ordinary roles rather than reusing old C/E/K schemas:

- E: immutable named dependency DAG links. Leaf E holds exact builtin bindings; outer E holds exact
  leaf closures and getter binding. Two supported dependency forms initially, not arbitrary recursion.
- B: executable binding. Leaves retain existing LOCAL binding shape with source BYTES capturing E's
  identifier and supported wrapper/logical bytes. Outer uses a distinct in-process binding role,
  source BYTES/E link, NULL interpreter/timeout, never a fabricated local-python binding.
- C: role-rooted intent URI, B and E links. No K and no intent-level environment. Source contains no
  future C identifier. Construct dependencies, then E, then B, then C. Links retain captures; ID strings
  embedded in source alone are not retention edges.
- Defaults: convenience tree entries pointing to closures. Metadata promotion preserves C/E/B/history.

Module closure inspection checks exact shape/types and linked binding/environment consistency. The fixed
adapter checks supported intent/source/handler wiring, complete retained closure, and exact capture
relationships before ordinary request publication/dispatch or builtin authoring. Unsupported source
versions fail explicitly, no latest fallback. Structural validity does not declare arbitrary source safe.

No claim of complete environmental capture: installed DML/interpreter/external state can affect behavior.
Versioning/capturing every external dependency is outside this prototype; describe actual capture scope.

## 5. Reuse authority and provenance

Use NEW example-local decisions/outer Q/T/selection/satisfaction roles and readers. Leaf own Q/T and
fresh execution remain unchanged public LOCAL/exchange. Do NOT make old helpers accept intent-only keys.

Recommend ONE known selection slot per supported intent: outer, add, double. No table/discovery index
is needed. A key is exact canonical URI plus full canonical MAP datum identity, recomputed from native
argument profiles; no masks, commutative normalization or value extraction from arbitrary DAG roots.
Source DAG, closure and binding remain in actual request descriptions, not inside MAP child values.

A decision pins requested C/B/E, actual argument node/value, explicit fresh/try-selected/require-selected
control, basis and any known S. Present selections must validate even on explicit fresh/key mismatch;
malformed authority is an error, not a cache miss. Valid mismatch can select fresh work; require-selected
mismatch errors before an attempt/dispatch. No automatic adoption after success.

A consumed S proves the ORIGINAL successful request/attempt/result/complete retained history under its
actual producing C/B/E. A new W links own new Q/requested C/full arguments and selected OLD T/R/S.
Request binding need not equal producer binding, but each independently matches its own recorded closure.
Leaf authority composes public successful S with semantic return/getter and ORIGINAL outer-prefix checks;
outer authority checks the new completion, actual inner witnesses and ordered phases. Equal84 or a response
flag never supplies this authority. Public S remains a leaf validator, not an outer validator.

Outer hits skip adapter invocation, inner requests, getters and new outer attempts. Fresh outer work has
an independently pinned inner selection/control plan, not a moving lookup by logical code. On inner reuse,
NEW argument sources and requested target coexist with OLD executed source/capture/producer chains.
Successful earlier inner work survives a later outer failure.

## 6. Execution, scopes and bounds

Keep the demonstrated execution arrangement: finite application executes fixed outer logical source
through a synchronous in-process adapter; fresh leaves use unchanged synchronous public LOCAL exchange
in isolated owned stores. Every fresh computational child is a direct child of that SAME application.
No outer subprocess, descendants, RPC, asynchronous owner, detached service or thread-based execution.

Trusted recording integration uses short scopes and session-owned copied-value handles. Rebind semantic
nodes into THIS Recorder; never carry ended Recorder/native handles across dispatch. No writer/handle
spans ordinary validation/import/wait. Ordered phase joins retain leaf completion through explicit
`(previous outer phase, leaf F)` parents without copying arbitrary leaf tree state. Existing ref atomicity,
ALL-parent transfer validation and outcome-versus-cleanup distinctions remain.

Keep builtin16 arguments/16 positions/64 distinct reached semantic DAGs, existing transfer limits and
maximum ORIGINAL-authority depth8. Shared invocation must not reset aggregate limits by switching
backends/scopes; builtin preparation maps also count toward actual semantic reach. Fixed outer call
positions remain TWO, outer getter positions TWO; ordinary maps are original plus downstream map.
Getter preparation is separate recorded builtin argument construction, not map-empty/insert invocation.
Exact requested+OLD union/reservations must be measured prospectively before launch. No assumed reuse
of old34/50 counts, source projection, cap increase or unrecorded literal substitution.

Known computational/interface failures stop later slots and poison success. Persistence/publication/
validation/reaping uncertainty leaves actual durable partial history and UNKNOWN, never fabricated
failure/success or automatic retry. Outer has no fake OS exit, cleanup receipt or portable arbitrary-code
timeout. Node-only access is cooperative, not a security sandbox/purity guarantee.

## 7. Review and boundaries

[EXAMPLE](EXAMPLE.md) recommends FIVE outer Q/FOUR outer T/EIGHT leaf Q/SIX LOCAL leaf T: THIRTEEN requests,
TEN attempts/SIX direct launches/SEVENTEEN getters. These are planning counts, not measured results.
A mandatory source-level pre-edit gate and installed readiness gate follow future GO. Missing public seams,
incompatible budget graphs or broader adapter/runtime changes need review before expansion.

Focused behavior and one installed story primary; one final unchanged full-v and risk-based independent
SAME-history NONEXECUTING review per owning validation policy. No test-performance optimization, fixture
rewrite, fast/slow mode/default-parallel change or duplicated full/acceptance ritual. Existing tooling may
be used as-is; dependencies/downloads/installations beyond bounded local DML install need approval.

No native C/storage/low-level repository API/layout/URI change, native callable/opcode entity, generic
registry/evaluator/cache-discovery/mask/equivalence/resource/scheduler framework. Review as-built diagram
claims after future implementation, but ordinary roles are not new native entities. No glossary/spec edits
in preparation. GHA stays disabled/NOT RUN/not pass; no workflow/settings/release change.

VP-001 planning revisit: OPEN/UNKNOWN with existing coordinator owner and revisit conditions, no standing
waiver or diagnosis. This slice does not change async observation/LMDB open/lifetime; related need or
recurrence requires fresh scoped triage. Native19 remains PAUSED/private incomplete-unexecuted candidate
retained. Source/both builds coordinator-owned, old workers stopped. Preparation authorizes no worker/
source/build/install/test/story/reader/investigation/CI restart, commit/push, extra agent/cloud/global/
service/image/release/package/later turn/design checkpoint publication. Review these three docs, then GO.
