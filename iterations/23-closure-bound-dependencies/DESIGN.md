# Iteration 23 candidate design: closure-bound dependencies

Status: **prepared for review; NOT implementation/delegation/publication GO**.
The user's “proceed” authorized preparing DESIGN/EXAMPLE/HANDOFF. General capture direction and
closure-creation vocabulary are agreed; the bounded profile, identity rule, API and story below
are assistant recommendations, not approved engineering details or as-built claims.
Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md).

## 1. Direction and authority boundary

A closure captures dependencies when it is created. Dependencies need not be callable: constants,
configuration and other computational nodes qualify. Invocation arguments are supplied later.
The logical func/intent may have multiple closures with different captured environments.

```text
scaled_sum closure
  implementation: captured Python source
  dependencies:
    map-get  -> exact internal getter binding, with its func URI
    list-get -> exact internal getter binding, with its func URI
    scale    -> an I64-valued source node

invocation:
  argument-map NODE {a:13, b:29} -> result NODE
```

Capture fixes recorded references, not external contents those references might designate. It is
not a security sandbox, purity certificate, generic evaluator or complete environment preservation.
Terms follow the existing [glossary](../../../dml/docs/spec-next/glossary.md); this plan does not
redefine closure or dependency, select a new native entity or amend the glossary/specification.

### Deliberately narrower than the initial composed-func suggestion

The first assistant proposal was an outer `double_sum` request/attempt with separately recorded
inner ordinary add/double requests and inner reuse. That remains a future direction, NOT this
candidate's acceptance story. Read-only source review finds:

- [Recorder.call](../../../dml/python/daggerml/daggerml/builtin.py) dispatches only fixed internal
  builtins, not arbitrary ordinary funcs. `publish_callable` wraps one normal callable.
- [Local publication](../../../dml/docs/spec-next/local-execution.md#atomic-history-and-publication)
  requires one publication addition to the exact pre-dispatch tree and a fixed ordered completion
  join. [Exchange validation](../../../dml/python/daggerml/daggerml/exchange.py) enforces that shape.
- The runner owns direct-child disposition, NOT termination/reaping of arbitrary descendants.
  Starting nested ordinary workers or changing publication history is not merely binding a dependency.

Recommend first proving captured environments with ONE ordinary local callable per fresh attempt.
Its captured callable dependencies are real shipped builtins; its captured noncallable is a constant.
Arithmetic is explicit Python `(a+b)*scale`, not separately recorded ordinary add/double calls.
This does not claim a general normal-func dependency invoker or demonstrate recursive closures.
This scope reduction is an assistant recommendation for review, not an additional user decision.

## 2. Existing support and proposed surface

Preparation verifies clean DML HEAD `a57125cdf735310f2330226ce6272b3a67e53f62`; completed22 stays stopped.
[Internal builtins](../../../dml/docs/internal-builtins.md) already provide strict ordinary profiles,
recorder-owned values, source/load/arguments, fixed exact-version dispatch, bound operations,
explicit normal return and read-only inspection. [Iteration22 composition](../../../dml/docs/composed-node-calls.md)
already captures getter IDs in source bytes, but has no explicit general closure/environment descriptor.
[Local Q](../../../dml/docs/spec-next/caller-requests.md) links the executable local binding and inputs;
it has no closure field. Existing bindings require their exact five fields.

Recommend NEW example-local authoring/inspection/request helpers and captured logical/wrapper sources,
using public storage/builtin/local/exchange/S operations. Prefer NO installed runtime/native changes.
Old Q/binding/argument/result roles and older example APIs remain unchanged. No private role codec,
new node layout, URI registry, installed evaluator or generic dependency resolver.

A constant source is an existing semantic literal-source or literal node, not a naked datum ID.
For this fixed profile accept only exact I64 scale, exact `a,b` I64 invocation arguments and the
supported map-get-v1/v2/list-get-v1 bindings. BOOL/F64/coercions, malformed/unretained nodes and I64
overflow reject. General computed constants, configuration execution, recursive ordinary-callable
captures and external resources are deferred; this does not narrow the conceptual meaning of dependency.

## 3. Immutable closure and environment (candidate)

Recommended ordinary DAG conventions, illustrative role names:

| Descriptor | Exact fields and interpretation |
| --- | --- |
| Callable dependency F | role STRING `example-captured-builtin-v1`, func URI, binding DAG; role root |
| Environment E | role STRING `example-capture-environment-v1`, map-get F, list-get F, scale semantic node; role root |
| Computational capture key K | role STRING `example-capture-key-v1`, map-get func URI, list-get func URI, scale exact I64 datum literal; role root |
| Closure C | role STRING `example-captured-closure-v1`, intent URI, binding B, environment E, capture-key K; role root |

The explicit closure builder takes exact selected F/scale nodes from a pinned basis, validates
retention/strict supported func-binding pairs and source value, then authors E/K, executable local
binding B and C in one storage transaction. Publish only two absent tree names B/C plus a create-only
ref in a one-parent snapshot; E/K/F remain reachable through C. Constants/getter descriptors are
prepared at earlier explicit bootstrap boundaries. Duplicate names, wrong profiles, missing nodes,
conflicting refs or store errors abort that batch. Validation scratch/native handles close before write.

B's captured source embeds immutable E ID plus exact logical/helper bytes, NOT a moving dependency
name/ref or current default. C links E and B; E is created before B, so there is no self-ID cycle.
No source embeds C's own hash. Ordinary SubDAG links make dependencies transferable even though the
wrapper also records E's ID in source bytes; an ID string alone is not a retention link.

Inspectors reconstruct the fixed wrapper bytes from E and logical source, validate B's unchanged
local role/adapter/interpreter/timeout and recompute K from E. C/E/K are not arbitrary metadata bags.
Creating an equivalent closure may deduplicate records; closure creation's snapshot/ref identifies
authoring context, not an invented unique closure event. Creation makes no Q/T, getter call or job.

The story's mutable default names are convenience authoring choices only. A default change publishes
new versioned tree state; existing C/E/B stay byte-identical. An invocation explicitly selects C at
its pinned basis. The child consumes that exact capture, not whatever defaults are now named there.

## 4. Invocation and separate capture/source provenance (candidate)

Keep public Q unchanged: Q.binding is B; Q.inputs is the invocation argument node I with exactly
`a,b`. Captured scale is NOT silently merged into I, and supplying an invocation argument named
`scale` does not override capture in this profile. Creating a different capture requires a new C.

A NEW strict decision D captures exact C/E/K/B/I, their selected tree names, full invocation MAP,
control/action/reason and any consumed known S. It is separately added before public own-Q recording.
Readers check D's actual one-parent basis/tree delta and ACTUAL Cq parent equals that authored D,
exact Q/ref/reservation/dimensions, before satisfaction. Q alone does not claim to contain C or S;
its decision context supplies the separate capture association.

The trusted child wrapper validates context.B and its pinned decision/C/E/K associations BEFORE
opening the publication write. Public export/selection/path validation closes first. Inside ONE
write transaction and Recorder, load I and E.scale, bind operations to E's exact getter bindings,
and create a Python callable closed over the scale value-node and bound value operations.
Its graph-level invocation remains `func(argument-map NODE) -> result NODE`; Python factory/wrapper
plumbing is not an additional graph argument. It calls map-get for a and b, performs exact I64
arithmetic and returns an owned literal node. No list getter is invoked.

Use existing Recorder.returned and local.publish_result for the unchanged normal result profile.
The captured scale reference remains in C/E and D/history; ordinary literal return does not pretend
to trace every arithmetic or constant read. The trace proves the actual getter bindings and sources;
it does not certify Python arithmetic. No extra fields are added to builtin arguments/trace/return.
Source-distinct equal scales may be value-equal without equal E/C IDs. Wrapper handles do not leak
repository/graph navigation into the logical callable; this remains cooperative trusted Python.

Exact wrapper/inspection plumbing is refinable during implementation AFTER GO. A demonstrated missing
public seam requires coordinator review before expansion; never import a private codec, modify native
Q or implement nested processes to make the candidate work.

## 5. Capture-aware reuse identity (candidate requiring review)

Captured constants can change the computation even when intent URI and invocation MAP remain equal.
Blindly reusing by the old examples' intent+MAP key would incorrectly reuse84 for scale3's expected126.
Recommend this NEW example's effective key:

```text
canonical intent URI + computational capture K + FULL invocation MAP datum ID
```

This refines “func + argument value”: the effective captured func includes its computational environment.
It is NOT a silent reinterpretation of Iteration20–22 helpers, a native facet/mask implementation or a
claim the glossary selects this encoding. K is recomputed, not trusted as a user-supplied cache token.

For the FIXED profile K includes scale's typed datum, and each callable dependency's logical func URI.
It excludes constant derivation/source node identity, exact getter implementation binding, C/E IDs,
creation commit, names and defaults. Exact bindings/source relationships remain captured provenance.
The two supported map-get handlers are declared equivalent under their common builtin func identity.
This is a bounded equivalence declaration, not a general proof for arbitrary captured callables.
Future recursively captured closures cannot be keyed by their intent URI alone; their effective
capture semantics would need a separate design. No arbitrary masking/equivalence inference.

One known S slot is sufficient. Present S must pass public successful Q/T/R/F inspection AND the
ORIGINAL producer D/C/E/K/binding/input/return/trace validation, including on a valid key mismatch.
Poison errors, never a fallback miss. New own Q on fresh/reuse paths; ordinary W links new Q to OLD
T/R without rewriting old inputs/capture/trace. A hit creates no attempt/getter/completion. Requested
C/E/source/getter-v2 versus OLD executed C/E/source/getter-v1 are shown separately. Fresh work does
not auto-adopt; only initial explicit S adoption is needed. Defaults do not pin historical attempts.

## 6. Acceptance scope, limits and stop line

[EXAMPLE](EXAMPLE.md) recommends SIX Q/FOUR synchronous LOCAL attempts/EIGHT child getter positions.
It proves pinned old capture after changed defaults, equivalent new capture reuse, actual fresh v2
execution, and changed scale invalidating eligibility despite identical invocation inputs.
There are no separately recorded inner normal requests, support jobs, nested workers, construction
or compatibility getter calls. Existing16 arguments/16 positions/64 reached semantic DAG caps and
transfer caps remain; descriptor traversal has a small separate fixed field set, no unlimited graph walk.

Focused identity/source/capture/default/own-Q/poison/new-row atomicity checks, one bounded isolated
installed story, one final unchanged worker full-v and independent risk-based SAME-history
NONEXECUTING review follow [validation policy](../../../dml/docs/validation-policy.md) ONLY after GO.
No automatic duplicate full/story, historical fixture restart or whole-source census.

Planning revisits [VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md): OPEN UNKNOWN,
same coordinator owner/revisit conditions/no standing waiver. Proposed examples use unchanged
synchronous lifecycle, not async/LMDB/open repair; related needed changes/recurrence require fresh scope.
Native19 PAUSED/private candidate incomplete-unexecuted retained. Development [GHA disabled](../19-intent-scoped-reuse/GHA-DISABLED.md)/NOT RUN/not pass; no fresh platform assurance or control change.

Preparation edits design notes ONLY. No implementation/glossary/spec/diagram/source/build/test/install/
story/reader/worker/investigation/CI/experiment/service/image/commit/push restart. BOTH builds/source
remain coordinator-owned. Review all three candidates, then separate GO. No extra agent/cloud/global/
release/package/later feature/design checkpoint publication; completed22/paused19 permissions are not inherited.
