# Versioned implementation selection before reuse policy

Status: informative, implemented **example-local** convention over existing public APIs.

## Authority boundary

This page owns [implementation_selection.py](../examples/implementation_selection.py),
not a native entity, URI registry, installation/closure framework or public policy API.
[Intent reuse defaults](intent-reuse-defaults.md) owns the older, unchanged three-field
Idef convention. [Versioned selection](versioned-reuse-selection.md) owns ordinary S/V
and public successful-history revalidation; [explicit reuse](explicit-attempt-reuse.md)
owns the original four-field W. [Caller requests](spec-next/caller-requests.md) owns
Q/Cq publication and exact submission; [public preparation](spec-next/repository-execution.md#preparation-and-retained-workspace)
owns consumed binding/input/Q validation. [Transfer](spec-next/transfer.md) owns complete
all-parent typed history; [Python API](spec-next/python-api.md) owns handles/storage.
Existing explicit [Floci operations](spec-next/floci-execution.md) own actual dispatch.

## Two separate choices, one new request

One named intent declares exactly two captured binding DAGs, a default implementation
label and an independent reuse default. A caller chooses `default` or an explicit menu
label FIRST. THEN the existing `default`/`fresh`/`reuse-selected` override is applied to
that member's explicit known selection slot. The helper records and reads; it NEVER
launches. Pending fresh Q is not execution. Every path has its own distinct new Q.

| Implementation choice | Reuse choice | Meaning |
| --- | --- | --- |
| default | default | Definition's binding, then its reuse default/known slot |
| explicit A or B | default | Selected binding, still eligible for its OWN historical attempt |
| either | fresh | Own pending fresh Q; ignore unused S application framing |
| either | reuse-selected | Require valid matching S in THAT member's slot |

The reuse table/reasons remain [the existing intent-default convention](intent-reuse-defaults.md#captured-default-explicit-override-distinct-request).
Only a missing tree ENTRY is absence. Present unreadable/malformed/failed/incompatible
S on a reuse path errors BEFORE D/Q, not a miss/fresh fallback. Valid A S in its OWN
unselected slot is not inspected as B application authority. The same fully valid A S
forged into B's selected slot errors. Equal result84/intent/inputs cannot cross-bind.
Declared fresh/default-execute ignores unused S framing but still exports complete
reached native/all-parent/composite history; it does not repair, select or adopt S.

Matching is exact **intent URI, actual selected full binding DAG, full input DAG**,
including captured source/interpreter/timeout and exact producer witness/values/types.
Menu/default context records why, not a cache mask or a universal future dependency rule.
Slots each retain one known choice for this exact input tuple, not an input-search index.
Unknown labels never install/fallback; labels are scoped names, not implementation IDs.

## Ordinary definition, menu and captured choice

This NEW convention does not append fields to or reinterpret old Idef records.
The intent tree entry, illustratively `double-intent`, holds:

| Idef field | Node/value |
| --- | --- |
| role | literal STRING `example-implementation-definition-v1` |
| intent | canonical URI; Idef root |
| reuse-default | literal STRING reuse-by-default or execute-by-default |
| implementations | sub-DAG menu |
| default-implementation | literal STRING naming one member |

The menu has exactly `role`, and two named choice links. Its root is the literal STRING
role `example-implementation-menu-v1`. Member labels are safe native-profile names;
`role` and `default` are reserved. Each choice has exactly:

| Choice field | Node/value |
| --- | --- |
| role | literal STRING `example-implementation-choice-v1` |
| binding | captured binding sub-DAG; choice root |
| binding-name | literal STRING explicit tree name |
| selection-slot | literal STRING explicit known S slot |

The two captured binding IDs are distinct. Definition/tree binding names and known slots
are pairwise distinct. Strict field/root/node/datum checks and every declared binding-tree
cross-link are enforced. Definition inspection does not decode unconsumed binding code
semantics; public preparation owns the selected executable fields. No interpreter/resource
availability guarantee or implementation installation occurs.

`define` requires absent Idef and selection slots, two explicit `(label,binding-name,slot)`
triples and canonical URI. It captures pinned tree binding IDs. `update-default` reads the
existing strict definition and changes ONLY its default label: same URI/reuse policy/menu/
choices/bindings/selections/other entries. Each operation atomically publishes ordinary
records/tree/new commit with exact `(C,)` parent/create-only explicit ref/prebuilt response.
Restoring A can deduplicate original Idef content while creating a new snapshot. No Q/T/job.
General menu edits, adding/removing implementations and reuse adoption are deferred here.
The separate [advisory supersession convention](implementation-supersession.md) adds ordinary
L and request-context inspection over this unchanged fixed-menu definition/request authority;
it does not change these exact records or make default resolution interpret L.

## Ordinary decision and actual submitted Q

Each request publishes D at a caller-chosen absent safe name. D has literal STRING role
`example-implementation-decision-v1`, sub-DAG `intent-definition` (also root),
`implementation-choice`, `binding`, `inputs`, and literal STRING:

- `intent-name`, resolved `binding-name`, `inputs-name`, `selection-slot`;
- selected `implementation`, `implementation-override` (`default` or explicit label),
  `implementation-reason` (`default-implementation` or `explicit-implementation`);
- separate reuse `override`, `action`, `reason`.

Sub-DAG `selection` is present ONLY when reusing. The decision name is distinct from
all declared names/slots/input and cannot use request/attempt/publication/reuse occurrence
prefixes. Publication refs are explicit/create-only/distinct. Reuse ref exists ONLY on reuse.

Public temporary `prepare_exchange(request=None)` validates selected source/input/full
native history. No projection execution/B/Q/T; handles and scratch close BEFORE D writes.
S/V inspection validates selected old successful F/owning Q/final T/R from repository history.
Then D adds ONLY its entry on `(C,)`, and unchanged public Q builder or selected-reuse
operation separately publishes own Q and optional W:

```text
C -> Cdec(D) -> Cq(Q) -> Cr(W)       # selected reuse: no new attempt/job
C -> Cdec(D) -> Cq(Q) -> P/U/F       # ONLY explicit application dispatches
```

W remains exactly role/request/attempt/result, linking NEW Q to OLD selected T/R; old T
retains its producing Q. Fresh completion never changes the default or installs/adopts S.

Returned descriptions are NOT authority: the helper checks dimensions, revalidates returned
exact non-None Q/Cq and optional actual W through public preparation/pinned inspection,
and compares actual submission/reservation/ref/tree linkage and returned names/W DAG.
A wrapper returning only a substituted historical Q or W ID errors even with matching
response dimensions. Already-published D/Q/W remain; response rejection is not rollback.

## Pinned readers and branches

`inspect_decision` requires actual one parent, preserved tree plus ONLY absent D, strict
fields/types/root and recomputes both choices/reasons from THAT parent. Stored flags/reported
IDs/latest refs cannot supply authority. `inspect_request` requires exact ObjectId Q, NEVER
None, then public `prepare_exchange(request=Q, commit=Cq)` owns normative submission/Q.
Optional satisfaction requires exact `(Cq,)`, only original four-field W, own Q/selected T/R.
Pending Q inspection does not claim dispatch/satisfaction or infer unknown outcome.

Sibling keep-B/update-A commits can share exact common parent and both selections while
retaining different defaults. Requests on those branches select different old attempts
even when result content deduplicates. Ref movement cannot retarget historical D/Q.
Native transfer retains choices/code/default/decision/S/V/ordered histories. Fresh offline
readers need no original packet/expected/input/B/endpoint/source execution. Temporary IO
is composition cost, not an efficient generic resolver or hard RSS/deadline guarantee.
Content identity does not authenticate authors or certify complete capture/scientific truth.

## Failure boundaries

Definition/default-update/D each have individual atomic batches. Late ref/allocation/real
map-full/consuming-commit errors abort all their new rows. Pre-store authoring loss leaves
no batch; postcommit response loss can leave complete publication. Tests prove predicted
new actual-A keys absent BEFORE failure and preserve known old rooted/unrooted proof rows.
They terminate ONLY finite authoring processes, never a live computational child.

D/Q/W/files/service are separate. Q failure can leave D; W/projection cleanup/response
validation failure can leave pending Q or complete W. Inspect actual explicit refs/history;
no automatic repair/fallback/adoption/retry/new Q/relaunch permission follows an error.
No physical power-loss, global uniqueness, distributed exactly-once or recovery guarantee.

## Finite offline example

Copy `implementation_selection.py`, `reuse_selection.py`, `explicit_reuse.py` together;
use installed DML, not checkout/PYTHONPATH or a policy framework:

```sh
python examples/implementation_selection.py define A.dml <C> double-intent \
  urn:example:double reuse-by-default double-a intent-default \
  --implementation double-a double-a-binding selected-double-a \
  --implementation double-b double-b-binding selected-double-b
python examples/implementation_selection.py request A.dml <Cdef> double-intent \
  double-inputs decision-a default default decision-a submission-a
# Explicit adapter separately dispatches pending Q, returns recorded successful F.
# Explicit existing S/V select records selected-double-a; no automatic adoption.
python examples/implementation_selection.py update-default A.dml <Csel> \
  double-intent double-b default-b
# B slot absent: B request is fresh, despite A selection/result84.
python examples/implementation_selection.py request A.dml <Cboth> double-intent \
  double-inputs decision-explicit-a double-a default decision-explicit-a submission-explicit-a \
  --reuse-ref reused-explicit-a
python examples/implementation_selection.py inspect-request A.dml <Cq> <Q> \
  decision-explicit-a --satisfaction-commit <Cr>
```

## Evidence and limits

[Focused strict capture/pinned tests](../tests/python/test_implementation_selection.py),
[matrix/response/full-history/CLI controls](../tests/python/test_implementation_selection_edges.py),
[new actual-A rollback/loss](../tests/python/test_implementation_selection_atomicity.py) and
[default-safe controller checks](../tests/python/test_implementation_selection_fixture.py)
start no Docker. Existing owning Q/W/exchange fault suites stay owners rather than being
duplicated. The [installed three-job/nine-phase gate](../tests/floci/README.md#versioned-implementation-selection-gate)
executes actual add42, multiplication A84, captured addition B84 with factor2 check,
then offline default/explicit reuse/true siblings/transferred readers without another job.
The controller captures B standalone code from [floci_double.py](../examples/floci_double.py),
replacing the arithmetic with checked addition; binding history retains those actual bytes.

ROOT-source coverage remains unchanged, with no new exclusions. Host statements are not
all branches/platforms/installed-child/process-memory/environment/security assurance.
Ordinary Idef/menu/choices/D add no LMDB keys/boxes; diagram model remains unchanged.
Existing local unsigned-HTTP Floci/socket/job-security/ephemeral-B/finite-profile limitations
remain. Actual commands/provenance/failed probes/installed results/CI/UNKNOWN qualifications
belong to [Iteration16 RESULTS](../../dml-design/iterations/16-versioned-implementation-selection/RESULTS.md);
[coordinator REVIEW](../../dml-design/iterations/16-versioned-implementation-selection/REVIEW.md)
owns independent acceptance, not this page or a passing draft.
