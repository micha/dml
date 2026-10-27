# Iteration 6 handoff: execution across local repositories

Current status: the authorized bounded turn is implemented, independently accepted
and published as `a0aa05d`; all six final exact-SHA CI jobs pass. Work is complete
and stopped. [RESULTS.md](RESULTS.md) and [REVIEW.md](REVIEW.md) own delivery evidence;
[COORDINATION.md](COORDINATION.md) records the fresh-session window-2 assignment.
The user authorized implementation/review/fixes then focused worker commit/push/CI;
that completed authorization superseded planning-only permission statements below,
not the scope/stop line. This plan is not permission to restart or begin another turn.
No extra workers, release/package publication, cloud experiments or later feature.

Planning checkpoint status (historical): the user approved the bounded design/example/handoff and requested a local
checkpoint ready for handoff. **No implementation, worker assignment/restart,
implementation commit/push, CI launch or package publication is authorized.**
Do not inherit Iteration 5's completed delegation/publication request. Illustrative
APIs/provisional engineering details remain refinable within separately authorized
scope; approval does not make them as-built contracts.

## 1. Authority, learning goal and stop line

[DESIGN.md](DESIGN.md) owns candidate APIs, files, validation and failure semantics;
[EXAMPLE.md](EXAMPLE.md) owns acceptance. This handoff owns work order, assurance and
delivery. [Discussion](../../discussion.md) distinguishes agreements from proposals.
Existing [local execution](../../../dml/docs/spec-next/local-execution.md) and
[transfer](../../../dml/docs/spec-next/transfer.md) contracts remain authoritative
for implemented behavior; these plans are not as-built specifications.

Goal: prepare a pinned snapshot from A, execute one fresh step in independent local
B, and return its unchanged recorded history under a caller-chosen ref while leaving
A's existing heads alone. Connect existing public APIs, not invent another executor.

Stop after this slice, meaningful failure tests, installed acceptance and independent
review. No network/cloud/remotes registry, scheduling/polling, automatic execution
retry/recovery, caller-created occurrences continued by B, reuse/facets, merge/adoption,
resources/GC/excision, observer/UI, CLI mutation or general workflow framework.
A missing native operation requires a reproducer and separate scope decision.

## 2. Required reading and live preflight

After **separate implementation authorization**, follow
the machine index, confirm `/work` mounted and read completely:

1. Design [AGENTS.md](../../AGENTS.md), [README.md](../../README.md), current
   [discussion](../../discussion.md), this handoff, [DESIGN.md](DESIGN.md) and
   [EXAMPLE.md](EXAMPLE.md).
2. Implementation [AGENTS.md](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [as-built instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md) and
   [glossary](../../../dml/docs/spec-next/glossary.md).
3. Current [Python API](../../../dml/docs/spec-next/python-api.md),
   [repository](../../../dml/docs/spec-next/repository.md),
   [objects](../../../dml/docs/spec-next/objects.md),
   [records](../../../dml/docs/spec-next/records.md),
   [local execution](../../../dml/docs/spec-next/local-execution.md),
   [transfer](../../../dml/docs/spec-next/transfer.md) and
   [CLI](../../../dml/docs/spec-next/cli.md) contracts.
4. Iteration 5 [RESULTS](../05-pinned-snapshot-transfer/RESULTS.md) and
   [REVIEW](../05-pinned-snapshot-transfer/REVIEW.md), Iteration 4
   [REVIEW](../04-local-recorded-execution/REVIEW.md),
   [coverage catalog](../../../dml/tests/coverage-exclusions.md) and
   [packaging contract](../../../dml/docs/packaging-and-distribution.md).

Planning inspected clean implementation `0ec769b` and design checkpoint `26c9afa`
plus subsequent discussion edits. Reinspect live HEAD/status; preserve unrelated
work. No implementation files or as-built spec were changed and no tests/prototypes
ran during planning. Prior CI is not current-source validation.

Once authorized, identify implementer/reviewer and agree shared `build/check`
ownership before standard checks (they wipe/reconfigure it). **Finish the clean
baseline check before making measured source edits**; Iteration 5's early edit
contaminated its baseline coverage report. Do not repeat that mistake.

Use fresh test-owned repositories, caller-owned workspaces and bounded local
build/install/process scratch. No extra agents/global bootstrap or inherited
publication. Consult current standard-library file/JSON/process documentation using
the available documentation skill before selecting engineering calls. Existing
Context7 credentials may be loaded from shell configuration without printing/dumping
secrets. Preserve declared Python/runtime/platform support; qualify actual evidence.

## 3. Candidate source seams

Paths below are relative to `/work/repos/micha/dml`:

| Seam | Bounded candidate work |
| --- | --- |
| New composition | `python/daggerml/daggerml/exchange.py`, explicitly imported public prepare/execute/receive stages |
| Existing execution | `python/daggerml/daggerml/local.py`: call public `run_step`; inspect conventions, no execution redesign intended |
| Existing exchange | `python/daggerml/daggerml/transfer.py`: call public export/import and owning profile constants; do not expose private parsing/callbacks |
| Repository surface | `python/daggerml/daggerml/__init__.py`: public reads/transactions only; no further primitive intended |
| Installation | `meson.build` adds the new module to `python-runtime` |
| Runnable story | New `examples/repository_execution.py` with worker mode, reusing unchanged `local_add.py` |
| Tests | New focused exchange selection/framing/return-validation/process/acceptance tests and private barriers |
| Documentation | Owning as-built `docs/spec-next/repository-execution.md` after implementation; navigation/package orientation |

Do not edit native production/encodings, old `docs/spec/`, adapter scaffold, CLI
grammar/JSON, runtime/version declarations or release workflows. Retain finite CI
bounds, verbose Windows diagnostics and short test IDs. Use existing raw corruption/
delete fixtures rather than installed fault APIs. If changing any existing public
contract becomes necessary, stop with a precise proposal; do not silently expand it.

## 4. Recommended implementation sequence

### A. Resolve selection and lifecycle without spawning

Implement/freeze the small owned expected-selection description (including a fresh
transport-only exchange token per workspace) and candidate preparation stage.
Resolve binding/input names from the pinned commit tree; exact
IDs and input bundle are stable after head movement. Validate argument/name/type/
path boundaries, require a fresh workspace and initialized A, and close handles
before calling transfer helpers. No source process or A write during preparation.

Test missing selection, unsupported types/URI/ref names, existing workspace,
unrelated source corruption reached by full parent history and preparation file
failure. Filesystem artifacts may remain; do not call preparation atomically rolled
back or delete unrelated paths. Independently enumerate bundle population/bytes.
Record provisional spelling/profile replacements in RESULTS; material policy
changes require user review.

### B. Fresh B and one-shot worker execution

Implement worker stage consuming only workspace descriptor/input bundle. Reject
preexisting B/output or invalid descriptor; acquire exclusive `started` marker before
B initialization/import/dispatch. Require imported root and selected DAGs agree with
job selection and explicit working ref starts at C. Close handles before `run_step`.

Use existing local runner without `_prepare`, `_context`, `_finalize` or private
binding readers. It owns local pre-dispatch/publication/finalization and its scratch.
A completed recorded computational failure is a normal worker completion eligible
for history return. Driver/persistence errors do not fabricate `done` or a receipt.
Do not automatically retry, clear the one-shot marker or invoke `retry_step`.

Export the exact `LocalRun.final_commit` after handles close; publish bounded receipt
last. It identifies history, not stdout value/authoritative outcome. File failure
and full-history profile overflow after computation leave B intact and are reported
as exchange errors. Keep workspace/B on both success and failure. Test second execute
rejection even when the first invocation stopped before creating an attempt.

### C. Read-only selected-completion validation, then receive

Build a small inspector through public descriptions referencing the **existing** local
record contract. It reads completed history without requiring copied reservation refs
or touching stored scratch/interpreter paths. Validate exact base, pre-dispatch,
request/attempt association, preserved tree entries, ordered parents, accepted
publication and typed computational/cleanup outcomes as listed in DESIGN.

Strictly bound file/descriptor reads and compare against independent caller-owned
expected selection. Import output into a **private disposable validation repository**
through public transfer operations; require receipt/root equality and selected-run
checks before opening A for writes. This intentionally duplicates storage validation,
not packed decoding or executor logic. No public partial-staging/callback API.

Close and clean validation scratch before A import. Prepare owned outcome description,
then use unchanged public `import_commit(..., ref=...)` for A's atomic boundary.
No main update, adoption/replacement commit or copying B's refs. Return only after
storage commit; response loss afterward cannot undo it. Receiver can run repeatedly
without execution and needs only return packet plus expected selection, not live B.

Test a valid but wrong-selection packet and a swapped complete packet from an
otherwise-identical workspace (token mismatch), not just malformed JSON; wrong occurrences,
wrong typed DAG fields, swapped result/evidence, incorrect parent order, changed
unrelated tree entry and fabricated success over recorded failure. Each rejection
must leave **all A state unchanged**, including absence of new return objects/ref.
Keep descriptor parsing and consumed-role validation small; do not build a universal
schema framework or validate scientific truth.

### D. Real processes, faults and knowledge boundaries

Maintain a private deterministic barrier fixture, never installed. Minimum evidence:

- Worker pause after initial persistence before computational child spawn: termination
  leaves unknown B attempt and no automatic A publication.
- Worker pause after successful final storage commit **and direct-child reaping**, before
  receipt publication: B has done/result but A has no received outcome.
- Caller pause after completed worker/packet and before receive: A unchanged, workspace
  retained; explicit receive later never starts another attempt.
- Receiver barriers around **actual A storage commit**: precommit loss versus postcommit
  response loss; fresh readers independently compare complete expected state.

Use finite parent/barrier/subprocess waits and finally-owned reap/scratch handling.
Stopping the worker does not guarantee stopping its computational child/descendants.
Do not kill it while a real child is running merely to get easier cleanup evidence.
Private barriers should make ownership/disposition known; separately report any
signal/platform/direct-child limits. No general process-tree recovery/cleanup feature.

Also exercise real B import map-full before dispatch, post-computation export limit
failure, packet write failure, A different/malformed return-ref conflict, real late
A map-full and private consuming-commit fault. Late A failures must insert at least
one genuinely new earlier object and prove fresh-reader absence, preserving main
and unrelated sentinels. B's recorded computation stays intact; no error automatically
becomes a computational failure or new trial. Explicit larger-map **whole import**
retry may demonstrate caller-managed transfer retry, never execution retry.

### E. Installed acceptance and review freeze

Implement EXAMPLE with two separate fresh B workspaces/requests/attempts and shared
result 11, a recorded computational failure and selected interruption stories.
Record complete source/worker/returned typed byte oracles independently of transfer's
own traversal. Prove source C and A's heads are unchanged by helper activity; also
move A's head independently after pin and show it stays at that new target.

Build current core/console wheels through existing project-local packaging tools;
install offline into new isolated environments. Parent, worker driver, computational
child, fresh receiver/reader and console run outside checkout with source PYTHONPATH
unset and assert installed module/extension/console/native paths. Rename A away
while worker runs to prove no input access through A; no sandbox claim. Close B,
copy only complete return packet and pass expected selection independently, then
receive with B renamed away. Ordinary CLI inspection agrees with Python history/
occurrences/result/failure/cleanup. Installed receives must not load/execute captured
source or follow URI/path values. No new tooling bootstrap or package publication.

Then freeze runtime/tests and explicitly release shared build ownership for coordinator
independent inspection/default checks and separate installed probes. Send findings,
fix with regressions, and stop for acceptance. A passing suite is not publication
permission or authorization for a later feature turn.

## 5. Assurance matrix and standard validation

| Area | Required oracle |
| --- | --- |
| Pin/selection | Explicit C/name lookup, exact DAG IDs/bytes, later A head movement irrelevant |
| Bootstrap | Fresh B, explicit work ref, full bundle, no A path/handle required by worker |
| Occurrences | Request/attempt originate in B; two fresh workspaces distinguish them; equal result shared |
| One-shot | Re-execute rejected at every incomplete/completed stage, no silent marker clearing/retry |
| Return matching | Independent expected selection/token, root/base/roles/occurrence/tree/parents/result checks before A writes |
| Outcome separation | Returned recorded failure is exchange success; missing return is unknown at A; cleanup separate |
| A publication | Exact F/ref, no main movement/replacement commits/B refs, late-error whole rollback |
| Interruption | Unknown B initial state, done B without return, A precommit old state/postcommit complete state |
| Files/cleanup | Finite bounded reads, missing/partial/mismatched pair rejected; workspace retained; only allocated validation scratch cleaned |
| Installed/platform | Fresh independent installed processes, source/B offline, actual tested runtimes/platforms qualified |

Use Hypothesis for bounded name/selection/framing/role/history variation and identity/
repeat-receive properties. Use few deterministic real process/fault/map-full fixtures,
not hundreds of random subprocess kills. No giant payload reprs in pytest IDs; verify
maximum collected new IDs, preserving the actual oversized boundary inputs.

Standard command, to reinspect before execution, from implementation checkout:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Keep all new public module/example Python in measured source. Do not omit meaningful
failure handlers or lower gates. Narrow no-value exclusions require exact rationale;
difficult meaningful file/storage/process failures remain tested. Distinguish retained
coverage from excluded code, host helper coverage from uninstrumented installed
worker/child/receiver evidence, local default/memory `-v` from informational CI `-c`.

Retain binding/native CLI memory workloads. Unchanged native tests/Valgrind are not
new process-tree/security assurance. Recheck available Python mutation tools without
bootstrap. If unavailable, report the gap and use selected negative-oracle probes
for wrong-job association, premature A publication, false-success classification,
head update and repeat-execution guards, not a broad mutation score. Existing Mull
is not Python mutation assurance.

## 6. Documentation, report and stop

Only after implementation exists, add the owning as-built exchange document and
update README/Mermaid navigation, package module inventory, Python orientation and
example links. Local roles remain owned by local-execution.md; bundle format/profile
by transfer.md. Document only this layer's selection, files/ownership, selected-run
validation, explicit stages, received descriptions and failure/trust boundaries.
Do not silently redefine glossary terms or amend the old draft spec.

Worker `RESULTS.md` here should record live baseline, selected choices/deviations,
changed files, exact commands/exits/counts, complete-state oracles, real versus
substituted faults, process/platform evidence, installed source/wheel provenance,
coverage populations/exclusions, memory suppressions, mutation gap/probes and
remaining limitations. Coordinator owns REVIEW/COORDINATION and design status.
Validate local Markdown targets/anchors and whitespace in both repositories.

Stop for independent review. No worker is assigned by this preparation. Separate
user authorization is needed for implementation/delegation and any later focused
commit/push/exact-SHA CI monitoring; do not inherit Iteration 5's completed request.
No release/tag/package publication, cloud/global tooling or later feature turn.

## 7. Ready-to-assign checkpoint

The approved bounded plan is prepared for a future authorized implementer. Before
sending any assignment, recheck the user's current authorization and live checkout
state; do not restart a worker simply because this document is ready.

The eventual assignment should name the implementer/reviewer and carry these gates:

1. Read the complete required context, verify baseline and preserve unrelated work.
2. Agree exclusive shared-build ownership; complete baseline checks before edits.
3. Implement only this slice and its evidence; record provisional refinements and
   surface scope changes before making them.
4. Freeze runtime/tests and release the build for independent coordinator review;
   fix findings with regressions until satisfactory.
5. Stop at acceptance unless this turn separately authorizes focused implementation
   commit/push and exact-SHA CI verification/fixes. Never inherit Iteration 5's request.

Preparation verified implementation still clean at full SHA
`0ec769b5e85fde6b6581b628fffdf3465c78a098`. Only design notes changed; no worker
assignment, code/spec edit, build/test/prototype or CI launch. The user requested
this local design checkpoint; the design repository has no remote and no push is
authorized. No completion marker or old archived coordinator protocol is active.
