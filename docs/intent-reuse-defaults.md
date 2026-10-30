# Intent reuse defaults and explicit request overrides

Status: informative, implemented **example-local** convention; acceptance gates are pending.

## Authority boundary

This page owns [intent_defaults.py](../examples/intent_defaults.py), not a public policy
framework, intent registry, native entity or new normative Q/T schema.
[Versioned selection](versioned-reuse-selection.md) owns ordinary S/V public revalidation;
[explicit reuse](explicit-attempt-reuse.md) owns unchanged Q/W association.
[Caller requests](spec-next/caller-requests.md) owns atomic Q/Cq publication and exact
submission shape. [Public preparation](spec-next/repository-execution.md#preparation-and-retained-workspace)
owns consumed binding/input and full native-history validation;
[transfer](spec-next/transfer.md) owns complete typed all-parent closure/profile.
[Python API](spec-next/python-api.md) owns native handles/storage boundaries.
Actual dispatch uses existing explicit [Floci](spec-next/floci-execution.md) operations.

## Captured default, explicit override, distinct request

One named intent definition records `reuse-by-default` or `execute-by-default`.
The caller still selects known binding/input/selection names; no discovery, URI registry,
implementation resolver, global cache index, purity classification or facets/masks are added.
Both resolved paths create a **new request Q**. Selected reuse creates no new attempt/job
or empirical observation. Recording an execute-fresh request does not itself execute it.

| Override | Default | Known selection slot | Action / reason |
| --- | --- | --- | --- |
| default | reuse-by-default | absent ENTRY | execute-fresh / default-no-selection |
| default | reuse-by-default | valid matching S | reuse-selected / default-selection |
| default | execute-by-default | unused | execute-fresh / default-execution |
| fresh | either valid default | unused | execute-fresh / override-fresh |
| reuse-selected | either valid default | valid matching S required | reuse-selected / override-selected-reuse |

Present malformed/unreadable/mismatched S on a reuse path raises BEFORE D/Q. Explicit
selected override with absent S also raises. Only a missing tree entry is absence;
no decoder/IO/native/profile exception is caught as a miss or fresh fallback.
Missing/malformed Idef or unknown default/override raises, never supplies an implicit default.

Declared fresh/default-execute deliberately does not inspect **unused S application
framing**. Full reached native history still has to export completely, including every
parent and composite-only datum child, under unchanged transfer limits. Unused S is
neither repaired nor adopted. Another valid binding/full-input triple may execute fresh;
it cannot silently reuse a mismatched old choice.

Matching remains exact **intent URI/full binding DAG/full input DAG**, including captured
source/interpreter/timeout, all declared values/types/factor and exact producer witness.
Equal result42/84 is not an occurrence substitute. This minimal definition is control-only;
changing its default does not change the computational matching tuple. No rule for future
intent definitions with computational dependencies or general equivalence is selected.

## Ordinary Idef and D

The intent tree slot (illustratively `double-intent`) holds an ordinary DAG Idef:

| Binding | Node |
| --- | --- |
| role | literal STRING `example-intent-default-v1` |
| intent | literal canonical URI, also Idef root |
| default | literal STRING reuse-by-default or execute-by-default |

`define` requires an absent slot; `--update` requires an existing valid definition with the
SAME stable URI. One storage batch preserves all other entries/selection, creates a new
Idef/tree/commit parented exactly `(C,)`, creates an explicit absent ref and prebuilds its
owned response before commit. No Q/T/job. Cooperative raw authors are not authenticated.

Each request adds ordinary decision D at a caller-chosen absent name:

| Binding | Node |
| --- | --- |
| role | literal STRING `example-request-policy-decision-v1` |
| intent-definition | sub-DAG Idef reference; also D root |
| binding, inputs | sub-DAG references to full computational dimensions |
| intent-name, binding-name, inputs-name, selection-slot | literal STRING explicit tree names |
| override, action, reason | literal STRING captured decision |
| selection | sub-DAG S reference, present ONLY when reusing |

The five names are safe native-profile names and pairwise distinct. The decision name
cannot use canonical request/attempt/publication/reuse occurrence-name prefixes. Ref
names are explicit, create-only and distinct; a reuse-result ref is supplied ONLY on the
selected-reuse path. There is no global pending slot/automatic replacement/name generation.
Otherwise identical D content may deduplicate; owning Q occurrences remain distinct.

## Public authority and separate publication spine

The helper reads pinned C/Idef, then calls public `prepare_exchange(request=None)` in a
NEW owned temporary workspace. This validates consumed source/full inputs/full history;
it creates only transport files/token. It NEVER starts/executes/observes that workspace,
creates B/Q/T or preserves its token as computational identity. Preparation scratch and
native handles close BEFORE actual-A D authoring. Reuse additionally uses the existing
persisted S/V public-backed inspector, matching exact dimensions and selected successful
F/original Q/final T/result/attempt occurrence; no private local-role codec or old paths.

D publication preserves C/adds ONLY named D, exact `(C,)` parent/create-only decision ref/
prebuilt response in one storage transaction. THEN existing `record_exchange_request`
creates the operation's own Q for fresh, or existing `reuse_selected` delegates its own
Q and separate unchanged W for reuse. The actual owning returned dimensions/T/R are
compared with validated D, not accepted from supplied decision/request/verdict flags.

```text
C -> Cdec(D) -> Cq(Q) -> Cr(W)        # selected reuse; no new T/job
C -> Cdec(D) -> Cq(Q) -> P/U/F in B   # ONLY a separate explicit driver dispatches
```

Q's submission parent pins Cdec. W keeps ONLY role/request/attempt/result, links that
NEW Q to selected OLD final T/R, and has no direct D/S edge. D alone links S. The old T
remains associated with its original producing Q. Successful fresh F does not change
Idef/S, even on initial absence; selection/adoption stay explicit separate operations.

## Pinned readers, not dispatch permissions

`inspect_decision` checks exact one parent/preserved tree plus ONLY D, strict shape/root/
node/datum types, and recomputes action/reason/definition/names/selection against that
ACTUAL parent, not current/latest refs. Public source/native validation and persisted
S/V authority remain owners; every stored D claim must match recomputation.

`inspect_request` requires an **exact ObjectId Q, never None**. Public temporary
`prepare_exchange(request=Q, commit=Cq)` owns normative exact Q/one-parent/preserved-tree-
plus-only-Q validation. None would select original fresh-Q-in-B preparation, which is
NOT submitted-Q authority. The CLI therefore requires an explicit Q positional argument.
An optional satisfaction commit additionally requires exact `(Cq,)`/tree-plus-only-W/
original four fields/own Q/selected T/R. A pending reuse Q can be inspected without W;
this does not claim satisfaction. A fresh Q stays pending until separate recorded work.

Readers need no original packet/expected/input/B/service/interpreter availability,
serialized process, source execution, observe/start or historical path action. Full
public transfer preserves Idef/D/reasons/S/V/W/producing history for fresh readers.
Temporary IO/public export is deliberate composition cost, not a native efficient resolver
or hard deadline/RSS guarantee. All projections close before successful reader return.
A wholly coherent different declaration/own Q is another recorded choice, not detectable
fraud against unstated intention; content IDs do not authenticate authors or certify truth.

## Failure and loss boundaries

Idef and D each have individual atomic storage batches. Late ref/allocation/real map-full/
consuming commit errors abort that batch. Pre-store-commit authoring loss leaves no batch;
postcommit lost response can leave complete publication. Inspect explicit refs; no automatic
repair/retry/duplicate request is authorized by missing acknowledgement.

**D/Q/W/files/service are not one transaction.** Q failure can leave D; W failure can leave
D and pending Q. Existing reuse projection cleanup can fail AFTER complete D/Q/W; mismatched
owning response/lost response also does not undo already committed state. No error causes
fresh fallback, adoption, new Q, ref repair or dispatch. Tests distinguish these boundaries,
not whole-driver atomicity/exclusivity/exactly-once or physical power-loss guarantees.

## Finite offline modes

Copy `intent_defaults.py`, `reuse_selection.py` and `explicit_reuse.py` together; they use
installed DML/public APIs, not a checkout/PYTHONPATH or HTTP/Floci/Docker runtime import.

```sh
python examples/intent_defaults.py define A.dml <C> double-intent \
  urn:example:double reuse-by-default intent-default
python examples/intent_defaults.py request A.dml <Idef-C> double-intent \
  double-binding double-inputs selected-double decision-miss default \
  decision-miss submission-miss
# Pending execute-fresh Q: explicitly prepare/stage/submit/observe/receive separately.
# After explicit selection, the known matching default hit requires a reuse-result ref:
python examples/intent_defaults.py request A.dml <selected-C> double-intent \
  double-binding double-inputs selected-double decision-hit default \
  decision-hit submission-hit --reuse-ref reused-hit
python examples/intent_defaults.py inspect-decision A.dml <Cdec> decision-hit
python examples/intent_defaults.py inspect-request A.dml <Cq> <Q> decision-hit \
  --satisfaction-commit <Cr>
python examples/intent_defaults.py define A.dml <branch-C> double-intent \
  urn:example:double execute-by-default execute-policy --update
```

Keep an unchanged-tree sibling and the new-default snapshot parented by the same pinned C.
Both retain the same S; later default/explicit-selected requests can explain different
branch-local behavior without moving other heads or rewriting old decisions. The helper
never launches; the explicit application alone drives actual fresh work.

## Evidence and limits

[Initial native tests](../tests/python/test_intent_defaults.py),
[strict shapes/Q/W](../tests/python/test_intent_defaults_records.py),
[full matrix/dimensions/native closure](../tests/python/test_intent_defaults_modes.py),
[separate response/cleanup edges](../tests/python/test_intent_defaults_edges.py) and
[actual new-A atomicity/authoring loss](../tests/python/test_intent_defaults_atomicity.py)
start no Docker. The separately mandatory
[actual current-installed four-job/twelve-phase gate](../tests/floci/README.md#intent-defaults-and-request-overrides-gate)
distinguishes real Batch/S3/available gated B from service-OFFLINE policy/readers with
active import/spawn blockers and complete external all-status/persisted job census.
Its worker commands/results are separate from host tests and independent acceptance.

The example stays in unchanged ROOT-source coverage. Host statements are not every branch/
installed-child/platform/process-memory/security/full-capture/scientific assurance. Idef/D/
S/V/W remain ordinary DAGs, not new LMDB keys/boxes. Existing unsigned-local Floci/socket/
job-security/ephemeral-B/profile/lifetime/cleanup limits and all gates/budgets persist.
Original failures and older UNKNOWN causes remain in
[Iteration15 RESULTS](../../dml-design/iterations/15-intent-reuse-defaults/RESULTS.md);
coordinator review owns independent acceptance, not a passing draft or this documentation.
