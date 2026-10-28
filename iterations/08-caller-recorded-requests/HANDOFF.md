# Iteration 8 conditional handoff: caller-recorded requests

Status: [DESIGN.md](DESIGN.md), [EXAMPLE.md](EXAMPLE.md) and this bounded handoff are
**approved as the plan**; the user requested a local design checkpoint. This file assigns
no worker and authorizes no implementation/prototype, restart, delegation, implementation
commit/push or CI. Do not inherit Iteration 7's completed GO. Candidate approval gates
below are satisfied; separate implementation/delegation/publication gates remain.

## 1. Goal and stop line

A explicitly records Q before launch; fresh local B creates only T for that exact Q;
existing asynchronous P/U/F observation and explicit-ref reception preserve identity,
unknown/failure distinctions and all existing A heads. [DESIGN.md](DESIGN.md) owns candidate
mechanics and proposed seams; [EXAMPLE.md](EXAMPLE.md) owns acceptance. Current as-built
local/exchange/asynchronous/transfer contracts remain implemented authorities.

Stop after this bounded Python slice, meaningful installed/failure evidence and independent
acceptance. No network/cloud, scheduler/daemon, detached lifetime/process-tree guarantee,
automatic retry/recovery/cancellation, request lifecycle registry, distributed authorization,
reuse/facets, resources/GC/excision, observer/UI, CLI mutation, native/old-spec expansion,
version bump/migration, release/package publication or later feature. A missing primitive
or material scope change needs evidence/proposal and separate approval.

## 2. Candidate choices requiring approval

- Request recording is a separate explicit A mutation: Cq adds only Q to pinned C;
  create-only submission ref and A-local request reservation atomically retain it.
- Public local request builder plus explicit first-attempt operation; don't call private
  local helpers, masquerade first dispatch as retry or synthesize registration in exchange.
- B-local registration happens only in explicit run_request's atomic pre-dispatch; pure
  transfer conveys neither mutable refs nor execution permission. Exact pinned head/Q,
  absent reservation and fresh T checked before launch.
- Expected selection pins Cq/Q, not just matching computational values. Extend strict
  job/handle framing and both synchronous/asynchronous selected-history validation;
  preserve original fresh-Q-in-B callers/checks. No old-file migration obligation.
- Bootstrap has no selected T/packet but caller already has Q. Keep lifecycle working/done
  and live application process ownership unchanged; no new request-only packet phase.
- Local one-shot guard is not a global prohibition on explicitly executing copies of Q
  in new repositories. No automatic replay, recovery or exactly-once claim.

## 3. Required reading and live preflight after separate GO

Follow machine index first and verify `/work` mounted. Read fully:

1. Design [AGENTS](../../AGENTS.md), [README](../../README.md),
   [discussion](../../discussion.md), this handoff/design/example.
2. Implementation [AGENTS](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [as-built instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md),
   [glossary](../../../dml/docs/spec-next/glossary.md), linked Python/object/record/repository/
   CLI contracts.
3. [Local execution](../../../dml/docs/spec-next/local-execution.md),
   [repository execution](../../../dml/docs/spec-next/repository-execution.md),
   [asynchronous execution](../../../dml/docs/spec-next/asynchronous-execution.md),
   [transfer](../../../dml/docs/spec-next/transfer.md), maintained sources/tests/examples,
   [packaging](../../../dml/docs/packaging-and-distribution.md),
   [coverage catalog](../../../dml/tests/coverage-exclusions.md), Iteration 7
   [RESULTS](../07-asynchronous-local-execution/RESULTS.md) and
   [REVIEW](../07-asynchronous-local-execution/REVIEW.md).

Planning inspected clean implementation full SHA
`a8d646379a52878d087d28bc216b7baa4f9ef3db`. Reinspect live tree/index/HEAD; preserve existing
uncommitted design delivery/direction/plans and unrelated work. Prior green CI is not a
fresh baseline. No code/spec edits, tests/build/prototypes or worker activity in preparation.

Name implementer/reviewer only after delegation authorization. Verify Pi pane/process via
`TMUX_PANE`/targeted captures; window-2 sidebar is not Pi. No extra agents or archived
coordination/completion-marker protocols. Start a new worker Pi session only when authorized.

Agree exclusive ownership of **both `build/check` and `build/coverage`**. Complete fresh
standard baseline before measured edits. Worker source/build freeze and explicit release
of both precede independent coordinator checks; no overlapping wipes/reconfiguration/edits.
Use existing toolchains/local scratch only. Consult current library/stdlib/CLI documentation
through the available skill when needed; never print secrets or bootstrap global tooling.

## 4. Candidate source seams

Relative to implementation checkout:

| Seam | Bounded change |
| --- | --- |
| `python/daggerml/daggerml/local.py` | Public request-only builder and explicit first attempt; local-owned validation/preparation reuse; unchanged executor/publication/finalization semantics |
| `python/daggerml/daggerml/exchange.py` | Explicit request-recording helper/description, optional pinned-Q selection, descriptor/handle support, public run_request dispatch, mode-specific initial/discovery checks shared with synchronous receive |
| `python/daggerml/daggerml/exchange_worker.py` | Keep fixed public execute invocation; no custom commands/fault hooks |
| New `examples/caller_requests.py` | Finite owner plus fresh clients, Q-before-launch/P/U/F, two matching Qs, unstarted Q, offline A/B and ordinary CLI |
| Existing trusted slow child | Reuse declared finite cooperative gates; don't add runtime fault hooks |
| Focused Python tests/private fixtures | Request recording/registration, mixed-mode framing, exact identities, rollback and safe actual-process barriers |
| As-built local/request/exchange docs | One owning request-continuation contract after code exists; existing navigation/reference updates |

No new native API/codec, direct raw decoder, transfer private access, generic authority
framework, runtime declaration/tag/workflow change intended. Request/attempt roles remain
ordinary existing DAG shapes. Illustrative API/format refinements must be recorded explicitly,
not silently treated as user-agreed schemas. Preserve current run_step/retry_step behavior.

## 5. Recommended work sequence and evidence

### A. Request builder and atomic caller recording

Freeze the ordinary Q bytes/fields and owned descriptions first. Builder uses only its
local-owned readers/public native operations, no refs/scratch/process/implicit transaction
commit. Caller helper resolves pinned C's names, generates bounded-collision Q, preserves
C's tree and atomically creates Cq/two refs. Prebuild response before commit. Show no dispatch
or T with fresh readers/CLI, including an ordinary copied Cq without operational refs.

Exercise scalar/sub-DAG/role/root/ID/name/path profile boundaries and malformed inputs;
existing/ref-alias/dangling/raw-malformed conflicts and Q-name/ID collision retry/exhaustion.
Use Hypothesis for bounded fresh names/IDs, exact preservation and duplicate-ref rejection.
Track **successful genuinely new actual-A Q/Cq puts/readback** before late ref/map-full/
consuming-commit errors, not merely an error prior to writes. Verify entire batch absence,
all old typed bytes and all relevant refs/raw corruption with fresh independent readers.

Actual request-recording process barriers before storage commit after new puts versus after
successful commit before response establish no batch versus retained Q/Cq/ref. Do not retry
recording automatically after lost response; existing submission ref rejects a fresh record.
Request remains after later prepare/file/export failure. File failure is not A rollback.

### B. Public first attempt and B-local registration

run_request validates exact current head == pinned submission, Q/name/basis, and absent
reservation inside the same pre-dispatch transaction; generate only T. Preserve exact Q;
create Q/attempt refs and P/head atomically before existing executor. No generic retry mode
in worker. Keep child context reservation checks intact; run_step/retry_step regressions
remain. Close native handles before child work as today.

Test wrong/currently-moved head, typed-valid wrong/missing Q/intent/binding/inputs/root,
non-submission history, existing reservation same/different/dangling/raw malformed targets,
T collision exhaustion, real/new-put rollback and consuming-commit failure **without spawn**.
After registration failure B retains imported Cq/Q but no partial T/ref/head publication;
A stays recorded/unmodified. Existing retry_step on pure imported unregistered Q still fails.
Observe/receive must never register Q refs or invoke run_request/any source.

### C. Exact-Q selection through both return paths

Extend expected/spec/strict framing and mode-specific submission/initial inspection, not
just the worker. Original mode still requires fresh Q/T; caller mode requires existing
exact Q and only fresh T. Discovery derives Q from expected pinned history, not prefix scans.
Require prior unrelated Q/T/publication in C, exact trees/ordered parents, and no Q replacement.

Carry Cq/Q in saved independent expectation; loading never starts. Both completed synchronous
return and P/U/F packets must reject valid matching-computation **wrong-Q** history, including
receipt token/base claims rewritten to expected. Add a genuinely typed-complete P parented
by expected Cq with T referencing another matching Q while tree retains expected Q; this
exercises association rather than mere missing-base rejection. Reject different Q content
under the same occurrence spelling and all unchanged final outcome/evidence/cleanup checks.

Preserve working/bootstrap with no T/packet, working P/U, retrieved validated F done, F
without receipt, stale P/U reception, no implicit ref advance/head movement/source/path
execution. Real coherent head/publication changes between reads and after selection/export;
concurrent readers with distinct packet dirs; strict descriptor limits/file/validation-scratch
cleanup failures before A writes. Retain real post-F production-limit overflow evidence.

### D. Deterministic processes and installed story

Finite application owner retains/reaps fixed worker; initiating/observing clients exit and
fresh clients use saved handle. Cooperative initial/U gates demonstrate exact caller Q/T,
publication versus completion and nonzero-after-U evidence. Separate unstarted/outer-spawn
failure before P from computational-child launch failure after P and recorded final failure.
Safe worker-loss barriers before child spawn or after real child reaping; never sacrifice
live computational children. Release gates on errors, establish writers stopped before
removing only test-owned scratch. Qualify watchdog/barrier failures rather than claiming
portable process-tree cleanup. No detached daemon or PID signaling from saved handles.

Build current core/console wheels offline with existing tools, install fresh isolated venv,
run outside checkout with PYTHONPATH unset. Assert installed local/exchange/worker/core/
child/receiver/reader/console/native provenance and wheel/source byte equality. Rename A
offline during execution; copy complete packets then B offline for fresh receive with
independent expected. Two matching Qs/distinct Ts/equal result, prior Q/T history in C,
unstarted Q, failure/evidence/cleanup, receipt loss, same-ref repeat, unchanged main/submission/
A reservation/sentinel and **no newly copied B refs**. A's preexisting Q ref is expected,
not evidence of transferred refs; inspect its unchanged Cq target explicitly.

Compare all C/Cq/P/U/F populations/every packed byte with independent public breadth-first
oracles, including composite-only descendants/all parents, not transfer's traversal or
CLI prefixes. Keep actual-A new-put instrumentation and fresh whole-state return rollback/
map-full/consuming-commit/pre/postcommit response-loss evidence enabled in both modes.

### E. Freeze, review, fixes and stop

Worker records actual choices/changed files/commands/exits/populations, actual versus
substituted faults, successful-new-put atomicity, process disposition, installed provenance,
coverage/memory/mutation/platform/trust/profile limits in RESULTS here. Coordinator owns
REVIEW/COORDINATION/design status. After final worker standard/installed/static checks,
freeze runtime/tests/as-built edits and release both builds. Coordinator independently
inspects/probes/runs fresh default check; regressions accompany findings. Stop at acceptance.
Focused implementation commit/push/exact-SHA CI require separate current authorization.

## 6. Standard assurance and publication gates

Reinspect current command from implementation:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Measure new helpers and maintained example, not just previous modules. No source omission,
reduced oversized input, weaker threshold or meaningful-handler exclusion. Narrow no-value
exclusions require exact rationale under existing policy; tested/excluded populations distinct.
Retain binding/141 CLI memory workloads and runtime suppression/finalizer qualifications.
Host-helper coverage is not installed-child/process branch coverage. Informational CI `-c`
remains separate from default/memory `-v`. Do not assume previous test/statement counts.

Recheck Python mutation tooling without bootstrap; if absent, qualify the gap and run selected
negative oracles for replacement Q, implicit dispatch, precommit launch, moved A ref, mixed
snapshot, registration-on-import/receive and early A publication. Mull is not Python mutation
assurance. Use short semantic oversized pytest IDs and report maximum new/full collection
lengths. Validate Markdown targets/anchors and whitespace in both checkouts.

Before any eventual assignment: obtain candidate-plan approval and implementation/delegation
permission, verify live state/panes, baseline/build ownership. Before publication: independent
acceptance and current focused commit/push/CI permission. No extra agents, design checkpoint
commit/push, release/tag/package publication, cloud/global experiments or later turn authorized
by this planning request.
