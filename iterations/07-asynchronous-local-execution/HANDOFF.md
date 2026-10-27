# Iteration 7 conditional handoff: asynchronous local execution and progress

Status: user-agreed direction and authorized planning only. The [design](DESIGN.md)
and [example](EXAMPLE.md) are **candidate documents awaiting review/approval**.
No implementation, worker assignment/restart, experiments, implementation commit/push
or CI launch is authorized. Do not inherit Iteration 6's completed GO. This handoff
is ready for review, not permission to send an assignment.

## 1. Goal, authority and stop line

Goal: one fresh local worker/B, bounded start/observe invocations, explicit validated
P/U/F progress/completion return to A, with shared `working`/`done` separate from
computational/cleanup outcome and with the same Q/T throughout observation.
[DESIGN.md](DESIGN.md) owns lifecycle/process/discovery/packet semantics;
[EXAMPLE.md](EXAMPLE.md) owns acceptance. Current as-built
[exchange](../../../dml/docs/spec-next/repository-execution.md),
[local execution](../../../dml/docs/spec-next/local-execution.md) and
[transfer](../../../dml/docs/spec-next/transfer.md) remain authoritative for current
behavior; future changes must have inspected implementation evidence.

Stop after this vertical slice, meaningful failure/installed evidence and independent
acceptance. No automatic retry/recovery/finalization, detached-process supervision
service, scheduler/daemon, network/cloud, distributed locking, process-tree guarantees,
merge/adoption/latest-ref synchronization, reuse/facets, resources/GC/excision,
observer/UI, CLI mutation or general workflow framework. A missing native operation
or material scope change needs a reproducer/proposal and separate approval.

## 2. Review choices before implementation GO

Confirm the candidate plan, particularly:

- Saved handle is observation identity; a separate nonserializable launch object has
  a live application owner responsible for reaping. Fresh clients can exit/reobserve
  while a finite example/application supervisor remains; transparent exit of the sole
  launching process owner is not promised.
- Add bounded readiness receipt after B bootstrap/selection and before local dispatch.
  It distinguishes normal initialization races from malformed ready storage without
  splitting/redesigning the local runner or adding its private callbacks.
- Read coherent working/publication refs in B, then pin/export selected immutable P/U/F.
  No background progress-publishing daemon, private raw decoder or general ref scanner.
- Fresh immutable observer-owned packets, independent caller expected validation,
  explicit create-or-same-target destination refs; never auto-move A's heads.
- `done` requires recorded final computation/cleanup and successful selected-history
  retrieval/validation, not process liveness/worker exit or prior A reception.

These are assistant-origin recommendations, not newly user-agreed contracts. If
caller-independent observation must also promise unowned/detached worker lifetime,
resolve the additional platform/service ownership requirement before implementation.

## 3. Required reading and live preflight after separate GO

Confirm `/work` mounted and follow machine index first. Read completely:

1. Design [AGENTS](../../AGENTS.md), [README](../../README.md), current
   [discussion](../../discussion.md), this handoff/design/example.
2. Implementation [AGENTS](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [as-built instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md),
   [glossary](../../../dml/docs/spec-next/glossary.md), Python/object/record/repository/
   CLI contracts linked by that orientation.
3. Current exchange/local/transfer contracts linked above and their maintained sources,
   examples/tests; [packaging](../../../dml/docs/packaging-and-distribution.md),
   [coverage catalog](../../../dml/tests/coverage-exclusions.md), Iteration 6
   [RESULTS](../06-local-repository-execution/RESULTS.md) and
   [REVIEW](../06-local-repository-execution/REVIEW.md).

Planning inspected clean implementation full SHA
`a0aa05d56b9e70277a98bb03e26514ab6b6f1415`; design has intentionally uncommitted
Iteration 6 delivery/acceptance and Iteration 7 direction/planning notes. Reinspect
HEAD/index/working trees; preserve unrelated work. Prior green CI is not a fresh
baseline. No implementation files changed and no new tests/prototypes ran in planning.

Name implementer/reviewer only after separate delegation authorization. Verify live
Pi pane/process identity through `TMUX_PANE` and targeted captures, not unqualified
tmux display; Iteration 6 caught a sidebar/coordinator misidentification. Start no
extra agents or archived coordination protocol.

Agree exclusive ownership of **both `build/check` and `build/coverage`**. Finish the
clean standard baseline before measured source edits. Worker freezes source/build use
and explicitly releases both directories before independent coordinator default checks.
No overlapping wipe/reconfiguration or source edits contaminating validation.

Consult current stdlib subprocess/file/JSON and library/tool documentation through
available skill; retain declared Python/runtime/platform support. Planning consulted
Context7 `/python/cpython` for process ownership only; that is documentation evidence,
not successful process behavior. Existing credentials may be loaded privately without
printing/dumping secrets. Use fresh test-owned repos/workspaces/packet directories,
bounded local process/build/install scratch; no bootstrap/global install or cloud.

## 4. Candidate source seams

Relative to implementation checkout:

| Seam | Bounded work |
| --- | --- |
| `python/daggerml/daggerml/exchange.py` | Add handle/start/observe/receive descriptions and helpers; share own role validation; add readiness receipt in existing execute |
| New `python/daggerml/daggerml/exchange_worker.py` | Fixed installed worker module invoking public execute once, no arbitrary commands or private executor |
| `meson.build` | Install new runtime module using existing `python-runtime` tag |
| New `examples/asynchronous_execution.py` | Finite one-worker application owner plus short-lived initiating/observing clients; explicit handle/packet/ref flow |
| New trusted slow child example | Existing public child context/result publication, finite demonstration delay; no installed fault/barrier hook |
| New focused Python tests/private fixtures | Launch ownership, framing, progress history, races, selected import, faults and safe actual-process barriers |
| New owning as-built progress document | Actual implemented contract only after code exists; navigation/package orientation links |

No native production/encoding, old `docs/spec/`, adapter scaffold, CLI grammar/JSON,
version/runtime declaration or release workflow changes intended. Do not access private
local/transfer helpers from production. Exchange may share/refactor its **own** role
inspector internally without weakening existing completed-return checks or breaking
current prepare/execute/receive callers. Existing synchronous behavior/tests stay enabled.

## 5. Recommended work sequence

### A. Freeze evidence descriptions and progress inspector first

Implement owned handle/observation/received descriptions and strict bounded framing.
Keep current workspace path/caller expected separate from incoming historical paths.
Handle loading never dispatches or follows serialized PID/commands. Resolve exact
labels/fields, document provisional spelling refinements in RESULTS.

Extend the exchange-owned read-only inspector for P and U, sharing final validation
without a universal schema framework. Require exact base/new names, Q/T associations,
roles/types, preserved trees, ordered parents, publication/result and absence of final
fields for P/U. Both inspector and receivers use public storage/transfer and isolated
validation before A writes. No copied reservation refs required in packets/A.

Test typed-valid wrong selection/occurrence/phase/history packets, not only malformed
JSON. Distinguish publication from result/outcome/cleanup. Preserve Iteration 6 failure/
false-success/cleanup and whole-state rejection tests. Bootstrap has no packet or fake
occurrence; only F has final outcome descriptions.

### B. Bounded coherent discovery and immutable packets

Add readiness publication inside execute after bootstrap/selection/handles close and
before public `run_step`. No pre-dispatch private callback. Exercise receipt IO failure
before dispatch and preserved one-shot state/B.

Observe validates job/readiness/expected, then reads selected B working ref and, where
needed, the fresh attempt publication ref in one storage snapshot. Derive fresh Q/T
through exact differences from C, not a prefix scan across all history. Preserve prior
requests/attempts already in C. Ready-but-missing/corrupt B/ref is an error, not bootstrap.

Close source handles before public export. Hold selected immutable ID across head
movement; export full all-parent closure. Validate independently in disposable storage,
close/clean scratch, then publish full snapshot bundle/descriptor-last into a fresh
observer-owned packet directory. Never overwrite packets, alter B or use execution
source/URI/path values. Profile/file errors are exchange failures; retain B/workspace.

Receive complete packets using independent expected selection with B offline. Validate
again before existing atomic A import/ref creation. Same-ref/target repeats are safe;
progress-to-final under an existing different-target ref conflicts—no auto-update.

### C. Start and explicit owner without waiting for computation

Implement retained exclusive launch marker before one fixed installed worker spawn;
retain execute's independent marker. Check preexisting artifacts and handle/job mismatch
before process invocation. OSError/response loss must not authorize relaunch. PID/process
status never drives observation, failure, completion, signaling from a saved handle or
cleanup of historical paths.

Return/retain a live launch object with explicit application-owned reaping; use inherited
trusted runtime and fixed module command, DEVNULL/file-backed streams and no shell.
Prepare launch wrapper/command/owned streams before spawn where possible; avoid
postspawn receipt writes or response allocations that could lose process ownership.
Exercise catchable setup/launch errors; preserve marker and known direct-process
disposition, and never turn uncertain spawn/response into automatic relaunch.
Do not use `with Popen` inside start and accidentally wait on context exit, suppress
running-child warnings by dropping the object, create hidden registries or ship a daemon.

The maintained example's finite supervisor owns/reaps the worker; independent caller
scripts observe/receive and can exit. Ordinary hard owner loss stays an explicitly
unsupported lifetime/cleanup guarantee. No cancellation/restart API is required.
Worker protocol arguments contain no A path; rename-away proves functional separation,
not access control or inability of trusted source to access other user-owned paths.

### D. Deterministic real processes, races and late rollback

Minimum process evidence with finite waits and finally-owned disposition:

- Start returns while child is held at a cooperative/private barrier; owner retains worker.
- Initial P observation/import while same T has no outcome; repeated polling never spawns.
- Child publishes U and remains active; observation is working, no final success/cleanup.
- Child exits zero/nonzero after U; F is done with correct result or failure evidence.
- Fresh caller exits/reobserves from saved handle while separate supervisor retains worker.
- Private pre-spawn launch-marker loss; actual spawn/ack-loss with known owner.
- Worker loss after P before child spawn; loss after U **and child reaping** before F;
  loss after F/reaping before original completion receipt. Unknown stays unknown; F
  retrieval does not finalize or retry.
- Coherent read snapshot and head/ref movement between selection/export: no mixed
  occurrences/parents, stable pinned bytes. Concurrent readers use distinct packet dirs.
- Receiver barriers before actual A commit after new puts versus after successful
  commit before response; fresh readers distinguish old state from complete import.

Track actual successful **genuinely new** A puts/readback before real map-full, ref
conflict and consuming-commit errors. Exclude validation-import puts and preexisting
rows from the oracle. Fresh independent readers compare every existing/new typed byte,
all relevant refs/raw malformed ref values and absence of the entire new batch.
Larger-map whole receive retry is transfer retry, never another execution.

Also test malformed/partial readiness, packet framing/descriptor limits/file-write/
validation-scratch cleanup, valid swapped same-selection token packets, wrong worker
head/attempt publication targets, lost acknowledgement and real post-completion profile
overflow. Errors do not automatically become computation failure or `done` responses.

Do not kill worker while its real child is running just to simplify cleanup evidence.
Private barriers pause before spawn or after reaping; release cooperative child before
normal ownership cleanup. Qualify unsuccessful barrier/watchdog cleanup separately;
no process-tree/power-loss or arbitrary-kill assurance. Keep workspace/B/packets; remove
only helper/test-owned scratch after proving no writers remain.

### E. Installed freeze and independent review

Build current core/console wheels offline through existing local tools and install into
fresh isolated environments. Run outside checkout with source PYTHONPATH unset and
assert installed handle/helper/worker/child/receiver/reader/console/native provenance.
Rename A offline for worker execution. Copy only selected packets, then B offline;
pass independent expected separately to fresh receivers. Assert no source execution/
historical-path action during observe/receive. Preserve runtime declarations/tag limits.

Execute the full P/U/F story, matching fresh second job, failures/evidence/cleanup and
short-lived caller observations; compare complete independent public typed-byte oracles
with B/packets/A, not transfer's own traversal or CLI prefixes. Existing console agrees
on selected snapshots/history/occurrences/value/outcome, with no new command.

Freeze runtime/tests/as-built source and release both shared builds for coordinator
inspection, separate installed probes and fresh default check. Fix findings with
regressions; stop at acceptance. Passing tests are not publication permission.

## 6. Assurance, standard gate and report

Standard command to reinspect, from implementation:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Keep new runtime modules and maintained examples measured; no source omissions,
meaningful-handler exclusions, weaker thresholds or reduced oversized inputs. Narrow
no-value exclusions require exact rationale under existing policy. Host-helper coverage
is not installed/subprocess branch coverage. Preserve binding and native CLI memory
workloads, existing suppression/invariant qualifications and informational CI `-c`
versus local default/memory `-v` distinction.

Use Hypothesis for bounded descriptors/names, valid/invalid progress history, identity/
repeat receive and snapshot-pin properties; few deterministic process fixtures, not
random kill stress. Use short semantic oversized IDs and report maximum collection IDs.
Recheck existing Python mutation tooling without bootstrap; if absent, use selected
negative-oracle probes for premature done, wrong attempt association, mixed snapshots,
early A publication, lost marker/relaunch and unintended head movement. Report the
gap and probe scope honestly; Mull is not Python mutation assurance.

Worker RESULTS here records live baseline, selected/refined choices, changed files,
commands/exits/populations, real versus substituted faults, successful-new-put rollback,
process ownership/reaping/platform limits, installed source/wheel provenance, coverage/
exclusions/memory/mutation qualifiers and remaining limitations. Coordinator owns
REVIEW/COORDINATION and design status. Update as-built docs only after implementation,
with one owning document and references rather than duplicated local/transfer contracts.
Validate Markdown targets/anchors and whitespace in both checkouts.

## 7. Stop and future assignment gate

This preparation assigns no worker and authorizes no implementation experiment.
Before any eventual assignment: obtain plan approval and separate implementation/
delegation permission, verify live state/panes and agree exclusive build ownership.
Then follow baseline, bounded implementation, installed evidence and independent review
freeze/fixes. Focused implementation commit/push/exact-SHA CI require separate current
user authorization; do not inherit any completed turn. No release/tag/package publication,
cloud/global tooling, extra agents or later feature. The user subsequently requested
a local design checkpoint including these unapproved candidate plans and Iteration 6
delivery notes; that is not plan approval or implementation GO. No design push requested.
