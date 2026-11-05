# Agent guide

## Scope

This repository contains user-led exploratory DML design work. Read `README.md`
and `discussion.md` before continuing the discussion. Read the shared
[glossary](../dml/docs/spec-next/glossary.md) for the vocabulary.

- Keep conceptual agreements, tentative directions, assistant suggestions, and
  open questions distinguishable.
- Design discussion is not approval to implement or amend DML specifications.
- The user authorized isolated feasibility prototypes, local sandbox experiments
  and candidate-design evolution under `feasibility/`. Read its index,
  `ITERATION-RESULTS.md` and final audit for completed work and limitations. This
  does not authorize cloud experiments or production integration.
- Keep the implementation repository `/work/repos/micha/dml` unchanged outside
  separately authorized scope. The user has authorized code changes there for
  [Iteration 1](iterations/01-minimum-viable-repository/HANDOFF.md): the minimum viable
  repository, plus the already authorized `docs/spec-next/` documentation. This
  does not authorize later execution/resource/observer work. The user also
  authorized [Iteration 2](iterations/02-repository-usability/HANDOFF.md): the
  low-level Python repository API and inspection-only CLI, including bounded local
  build/install validation and review fixes. No later feature turn is authorized.
  The user also authorized [Iteration 3](iterations/03-composable-dags/HANDOFF.md):
  composable named DAGs and scoped lookup, implementation by the existing Pi agent
  in window 2, coordinator monitoring/review and fixes, then focused commit/push
  after acceptance and exact-SHA CI verification/fixes. This does not authorize
  a release, package publication, additional workers or a later feature turn.
  The user also authorized [Iteration 4](iterations/04-local-recorded-execution/HANDOFF.md):
  one locally executed, recorded Python step by the existing window-2 Pi agent in
  a new session, coordinator monitoring/review and fixes, then focused commit/push
  after acceptance and exact-SHA CI verification/fixes. No extra workers, release,
  package publication, cloud experiments or later feature turn are authorized.
- Iteration 5 [plan and handoff](iterations/05-pinned-snapshot-transfer/HANDOFF.md)
  are approved for pinned snapshot transfer between local repositories. The user
  authorized implementation by the existing window-2 agent in a new session,
  coordinator monitoring/review and fixes, then focused worker commit/push after
  acceptance and exact-SHA CI verification/fixes. No extra workers, release,
  package publication, cloud experiments or later feature turn are authorized.
- Iteration 6's [plan and handoff](iterations/06-local-repository-execution/HANDOFF.md)
  are approved for synchronous execution across local repositories, with the
  unchanged-caller-head/explicit-return-ref boundary. The user authorized implementation
  by the existing window-2 Pi agent in a new session, coordinator monitoring/review
  and fixes until satisfactory, then focused worker commit/push and exact-SHA CI
  verification/fixes. This bounded turn is now complete and stopped at published
  `a0aa05d`, all six exact-SHA CI jobs successful; see
  [review](iterations/06-local-repository-execution/REVIEW.md). This is not permission
  to restart implementation or begin another turn. No extra workers, release/package
  publication, cloud experiments or later feature turn are authorized.
- Iteration 7's [plan and handoff](iterations/07-asynchronous-local-execution/HANDOFF.md)
  are approved for asynchronous same-machine execution and inspectable progress through
  bounded adapter invocations, with separate saved observation handle/live application
  process ownership. The user declared GO and authorized implementation by the existing
  window-2 agent in a new session, coordinator monitoring/independent review and fixes
  until satisfactory, then focused worker commit/push and exact-SHA CI verification/fixes.
  This bounded turn is complete and stopped at published `a8d6463`, all six exact-SHA
  CI jobs successful; see [review](iterations/07-asynchronous-local-execution/REVIEW.md).
  This is not permission to restart implementation or begin another turn. No extra
  workers, release/package publication, cloud experiments, detached supervision service
  or later feature turn are authorized.
  See [coordination](iterations/07-asynchronous-local-execution/COORDINATION.md).
- Iteration 8's [plan and handoff](iterations/08-caller-recorded-requests/HANDOFF.md)
  are approved: A explicitly records Q before launch; B registers imported Q locally
  and creates only T, reusing asynchronous observation/explicit-ref return. The public
  seams, atomic two-ref A publication and pinned-Q validation are the bounded plan;
  illustrative spellings remain refinable. The user subsequently declared Iteration 8 GO
  and authorized implementation by the existing window-2 agent in a new Pi session,
  coordinator monitoring/independent review and fixes until satisfactory, then focused
  worker commit/push and exact-SHA CI verification/fixes. No extra workers, release/package
  publication, cloud experiments or later feature turn are authorized. This bounded turn
  is now complete and stopped through published `865bb79`, all six final exact-SHA CI jobs
  successful after a reviewed test-only portability fix; see
  [review](iterations/08-caller-recorded-requests/REVIEW.md). This is not permission to restart
  implementation or begin another turn. See
  [coordination](iterations/08-caller-recorded-requests/COORDINATION.md).
- Iteration 9's [plan and handoff](iterations/09-ssh-container-execution/HANDOFF.md)
  are approved by the user's Iteration 9 GO. The existing window-2 agent is authorized
  to implement in a new Pi session, with coordinator monitoring/independent review and
  fixes until satisfactory, then focused worker commit/push and exact-SHA CI fixes.
  Local Docker/SSH fixture validation is within this bounded turn; missing prerequisites
  requiring downloads/installations still need scoped approval. The existing local diagram
  commit `f7113d7` is accounted for as an ancestor of the authorized normal push, not new
  runtime work. No extra workers, cloud/second-host or remote-daemon experiments, global
  tooling/services, release/package publication or later feature turn. See
  [coordination](iterations/09-ssh-container-execution/COORDINATION.md). This bounded turn
  is complete and stopped through published `29ed39b`; all six final exact-SHA CI jobs
  succeed after a reviewed test-only Windows harness fix. See
  [review](iterations/09-ssh-container-execution/REVIEW.md). This is not permission to
  restart implementation or begin another turn.
- Iteration 10's [reviewed plan/handoff](iterations/10-asynchronous-ssh-execution/HANDOFF.md)
  is approved by the user's Iteration 10 GO: asynchronous SSH launch and bounded immutable
  P/U/F observation, saved identity separate from live execution-client ownership. The existing
  window-2 agent is authorized to implement in a new Pi session, with coordinator monitoring,
  independent review and fixes until satisfactory, then focused worker commit/push and exact-SHA
  CI verification/fixes. Local Docker/SSH fixture validation uses the approved loopback-only
  host-network/no-shared-mount profile; missing downloads/installations need scoped approval.
  Existing local diagram commit `a94e6f5` is accounted for as an unchanged ancestor of the
  authorized normal push. This bounded turn is complete and stopped through published
  `099d156`; all six final exact-SHA CI jobs succeed after a reviewed Windows test-harness
  correction and test-only diagnostic enrichment. Two earlier unchanged Windows story failure
  causes remain unknown; final pass is not their diagnosis/fix. See
  [review](iterations/10-asynchronous-ssh-execution/REVIEW.md) and
  [coordination](iterations/10-asynchronous-ssh-execution/COORDINATION.md).
  This is not permission to restart implementation or begin another turn. No extra workers,
  detached remote lifetime/supervisor, cloud/global tooling, release/package publication or
  later feature turn.
- The user separately authorized the existing window-2 agent to establish
  [Floci feasibility](feasibility/floci/HANDOFF.md), preserving coordinator context.
  Read-only primary-source investigation and bounded isolated local feasibility probes/report
  are authorized, not Iteration11 GO or production/specification integration. DML remains
  read-only at completed Iteration10; no shared builds/CI/commit/push/additional agents/cloud/
  global service changes. The bounded study is now complete/stopped, **viable with constraints**:
  real Batch Node jobs/fresh polling/S3 and prior DML packet replay pass, not combined DML-in-Batch
  adapter execution. See [report](feasibility/floci/REPORT.md) and [review](feasibility/floci/REVIEW.md).
  One pinned image pull/private internal-profile fixture was approved; owned fixtures retired,
  image/evidence retained. No further runs/pulls or Iteration11 GO; earlier task authorization
  does not authorize restart or production integration.
- Iteration 11's [approved plan/handoff](iterations/11-floci-batch-execution/HANDOFF.md)
  is accepted by the user for actual installed DML inside one Floci Batch job, bounded
  fresh-client observation and immutable S3 progress/history return. The user's GO authorized
  the existing window-2 agent/fresh session, coordinator independent review/fixes, then focused
  worker commit/normal push/exact-SHA CI. This bounded turn is **complete and stopped** through
  published `640cabb05dd9426323069e816621dcbc0c829ae0`, all six final exact-SHA CI jobs successful.
  See [review](iterations/11-floci-batch-execution/REVIEW.md) and
  [coordination](iterations/11-floci-batch-execution/COORDINATION.md). Original Windows old-reader
  rc1 cause remains UNKNOWN; final pass/test-only diagnostics are not its diagnosis/fix.
  Owned fixtures archived/retired, images/evidence retained. Local unsigned/stdlib-HTTP profile
  is Floci-specific, not a production AWS SDK adapter. Completed GO does not authorize worker/
  build/fixture/CI restart or later turn. No extra workers/cloud/global tooling/release/package
  publication/design commit/push unless separately requested.
- Iteration 12's [reviewed example/design/handoff](iterations/12-composed-recorded-steps/HANDOFF.md)
  were prepared at the user's request after agreement on two recorded steps: result sub-DAG42
  plus exact selected producer attempt becomes double's input, producing84 and an ordinary
  success summary. The user subsequently stated “reviewed”; this records bounded plan review,
  not implementation/delegation/publication GO. Exact engineering spellings remain refinable.
  The user subsequently declared **Iteration 12 GO** and authorized the existing window-2
  agent in a new Pi session, coordinator monitoring/independent review and feedback until
  satisfactory, then focused worker commit/normal push and exact-SHA CI verification/fixes.
  See [coordination](iterations/12-composed-recorded-steps/COORDINATION.md). Bounded local
  current-installed two-step fixture/build validation is authorized; missing downloads/
  installations need scoped approval. Prefer public-API example-local helpers; no generic
  evaluator/scheduler/reuse/resource/cloud feature, extra worker, release/package publication
  or later turn. This bounded turn is **complete and stopped** through published
  `66311fcc1a2c652b5e2526c5de78a3cf781e67d6`, all six final exact-SHA CI jobs successful;
  see [review](iterations/12-composed-recorded-steps/REVIEW.md). Owned fixtures archived/
  retired, images/evidence retained. Earlier Windows causes remain UNKNOWN. Completed GO
  does not authorize worker/build/fixture/CI restart or later turn; no design checkpoint
  commit/push requested. Completed Iteration11 permissions are not inherited.
- Iteration 13's [candidate design/example/handoff](iterations/13-explicit-attempt-reuse/HANDOFF.md)
  follow the user's agreement to explicit successful-attempt reuse: new request, old selected
  attempt/result, no new attempt/job; separately requested fresh control. Initial matching is
  exact intent/binding/full-input identity, including producer witness; facets/default/cache
  discovery/adoption are deferred. Direction agreement authorizes planning, not candidate-detail
  approval or implementation/delegation/publication GO. The user subsequently stated
  **“reviewed”**; this records bounded plan/handoff review, not implementation/delegation/
  publication permission. Exact engineering spellings remain refinable. No worker/build/fixture/image/CI restart,
  DML/spec/diagram edits, experiment/provisioning/commit/push. Prefer example-local public APIs;
  no generic framework/private role codec/new native entity assumed. Completed Iteration12
  permissions are not inherited; no design checkpoint commit/push requested.
  The user subsequently declared **Iteration 13 GO** and authorized the existing window-2
  agent in a new Pi session, coordinator monitoring/independent review and feedback until
  satisfactory, then focused worker commit/normal push and exact-SHA CI verification/fixes.
  See [coordination](iterations/13-explicit-attempt-reuse/COORDINATION.md). Bounded local
  current-installed reuse/fresh-control fixture/build validation is authorized; missing
  downloads/installations need scoped approval. No extra workers/cloud/global tooling,
  generic cache/facets/adoption/scheduler/resources, release/package publication or later turn.
  This supersedes pending-GO restrictions above for this bounded turn, not its scope.
  This turn is **complete and stopped** through published
  `b296fdb5acad4b8b1c7608aea3b1c5d0af6bd79c`, all six final exact-SHA CI jobs successful.
  See [review](iterations/13-explicit-attempt-reuse/REVIEW.md) and
  [results](iterations/13-explicit-attempt-reuse/RESULTS.md). Initial Windows native112
  disk-full failure and reviewed test-only successful-owned-temp cleanup are preserved;
  original full disk inventory was not captured, older Windows causes remain UNKNOWN.
  Owned fixtures archived/identity-retired; images/evidence retained. Completed GO does
  not authorize worker/build/fixture/CI restart or later turn; no design checkpoint
  commit/push requested. No extra workers/cloud/global tooling/release/package publication.
- Iteration 14's [candidate design/example/handoff](iterations/14-versioned-reuse-selection/HANDOFF.md)
  follow the user's agreement to versioned reuse selection and explicit reuse adoption: record
  a selected old successful attempt, explicitly reuse it, execute fresh without changing the
  selection, explicitly adopt in a new snapshot, and retain different choices on two branches.
  Exact intent/binding/full-input matching including producer witness remains; no automatic
  cache discovery/default/facets/masks/framework. Agreement authorizes planning, not candidate
  detail approval or implementation/delegation/publication GO. Recommended ordinary S/V and
  captured bounded public validation framing are assistant-origin candidate mechanics, not
  as-built behavior. Exact spellings remain refinable. No worker/build/fixture/image/CI restart,
  DML/spec/diagram edit/experiment/provisioning/commit/push; completed Iteration13 permission
  is not inherited. No design checkpoint requested. Read the three documents before review.
  The user subsequently stated **“reviewed”**; this records bounded plan/handoff review,
  not implementation/delegation/publication GO or as-built behavior. Exact engineering
  spellings remain refinable. No worker/build/fixture/CI/source restart or commit/push.
- The user subsequently declared **Iteration 14 GO** and authorized the existing window-2
  agent in a new Pi session, coordinator monitoring/independent review and feedback until
  satisfactory, then focused worker commit/normal push and exact-SHA CI verification/fixes.
  See [coordination](iterations/14-versioned-reuse-selection/COORDINATION.md). Bounded local
  current-installed selection/adoption/branch fixture/build validation is authorized; missing
  downloads/installations need scoped approval. This supersedes Iteration14 pending-GO
  restrictions above, not its bounded scope. No extra workers/cloud/global tooling/generic
  cache/facets/default/framework/resources/scheduler/release/package/later turn or design
  checkpoint commit/push. BOTH shared builds remain worker-owned until ALL-source freeze
  and explicit release for independent coordinator validation.
  During exact-SHA CI review, the user separately approved raising ONLY macOS x86_64's
  outer matrix-job budget from10 to20 minutes after primary GitHub timeout annotation.
  Other matrix platforms remain10; strict-Linux existing budget, every test/threshold/skip
  policy/runtime timeout remain unchanged. This narrowly supersedes the handoff's
  deadline/workflow prohibition for this outer CI cap only; no fixture restart or later
  turn is authorized. See coordination/review for the separate Windows test-only shell
  resolver/LF-shim correction and exact-SHA gates.
  This bounded turn is **complete and stopped** through published
  `8393a82a14df0e5ac7e9af21e4466d9829f9808d`, all six final exact-SHA CI jobs successful.
  See [review](iterations/14-versioned-reuse-selection/REVIEW.md) and
  [results](iterations/14-versioned-reuse-selection/RESULTS.md). Owned fixtures archived/
  identity-retired, images/evidence retained; initial Mac outer10min cancellation is
  confirmed but underlying slowdown stays UNKNOWN, Windows WSL primary/latent CRLF
  model/older UNKNOWN causes remain distinct. Completed GO authorizes no worker/build/
  source/fixture/CI restart or later turn; no design checkpoint commit/push requested.
- Iteration 15's [candidate design/example/handoff](iterations/15-intent-reuse-defaults/HANDOFF.md)
  follow the user's agreement to intent-level reuse/execute defaults with explicit request
  overrides, distinct new Q on either path, no new T/job on reuse, no automatic adoption,
  absence-driven fresh work and branch-local defaults. This authorizes planning, not exact
  candidate mechanics or implementation/delegation/publication GO. Known selection slot/
  exact URI-binding-full-input identity including producer witness remains; no purity/
  registry/cache discovery/index/facets/masks/framework/resource/cloud feature.
  Recommended ordinary Idef/D, separate decision parent/public temporary preparation,
  naming/transaction/unused-S execution framing are assistant candidates for review, not
  additional user decisions or as-built behavior. Read all three documents before review.
  DML remains clean published8393a82/Iteration14 complete-stopped; no worker/source/spec/
  diagram/build/fixture/image/CI restart/experiment/provisioning/commit/push. Completed GO
  is not inherited, no design checkpoint requested. Future budget/tooling changes need
  their own scope; existing Macx86 outer20/other matrix10/strict budget stays as-built.
  The user subsequently stated **“approved.”** This approves all three documents and
  assistant-origin mechanics as the bounded plan, not as-built behavior or implementation/
  delegation/publication GO. Exact engineering spellings remain refinable. Separate GO
  remains required; no worker/source/build/fixture/CI restart or commit/push. This
  supersedes pending-plan-review wording above, not the scope or stop line.
- The user subsequently declared **Iteration 15 GO** and authorized the existing window-2
  agent in a new Pi session, coordinator monitoring/independent review and feedback until
  satisfactory, then focused worker commit/normal push and exact-SHA CI verification/fixes.
  See [coordination](iterations/15-intent-reuse-defaults/COORDINATION.md). Bounded local
  current-installed defaults/overrides/branch fixture/build validation is authorized;
  missing downloads/installations need scoped approval. This supersedes Iteration15
  pending-GO restrictions above, not its approved scope. BOTH builds remain worker-owned
  until ALL-source freeze and explicit release. No extra workers/cloud/global tooling/
  generic framework/resources/scheduler/release/package/later turn or design checkpoint
  commit/push. Completed Iteration14 permissions are not inherited.
  This bounded turn is **complete and stopped** through published
  `664a87085961b5e24d2b709e057e4a28fe724088`, all six final exact-SHA CI41090059076
  jobs successful, attempt1. See [review](iterations/15-intent-reuse-defaults/REVIEW.md)
  and [results](iterations/15-intent-reuse-defaults/RESULTS.md). Initial16 plus reviewed
  three-file test-controller parser-classification correction published normally; exact
  stdlib urllib package/urllib.parse pure parsing is allowed, all transport/spawn blockers
  retained. Initial Windows oldcaller ENOENT underlying cause remains UNKNOWN despite
  final pass, distinct from established Unix19 bootstrap defect/older UNKNOWN causes.
  Owned fixtures archived/identity-retired, images/evidence retained. Completed GO permits
  no worker/source/build/fixture/CI restart or later turn; no design checkpoint commit/push.
- Iteration 16's [candidate design/example/handoff](iterations/16-versioned-implementation-selection/HANDOFF.md)
  follow the user's agreement to versioned implementation selection: one intent/two captured
  bindings, versioned default/explicit label override, separate reuse/fresh decision, own Q,
  exact selected binding/full inputs and per-binding known slots/no cross-implementation
  reuse/automatic adoption. This authorizes planning only, not exact candidate schema/API
  approval or implementation/delegation/publication GO. Recommended ordinary new Idef/menu/
  choice/D roles, captured tree cross-links/default-only updates/three-job story are assistant
  candidates for review, not as-built claims. Read all three docs before review.
  Current DML stays clean published4a053340, maintenance complete-stopped WITH VP-001/rawCI
  failure, not all-green. Follow the [validation policy](../dml/docs/validation-policy.md).
  VP-001 revisited in planning remains OPEN/UNKNOWN, not extended to Iteration16; separately
  scope investigation if async/LMDB/story changes become necessary, fresh CI failures need
  fresh attribution/decision. No worker/source/spec/diagram/build/fixture/image/CI restart,
  experiment/provisioning/commit/push or extra agent/cloud/global/release/package/later turn.
  Completed maintenance/Iteration15 permissions are not inherited; no checkpoint requested.
- The user subsequently declared **Iteration 16 GO** and authorized the existing window-2
  agent in a NEW Pi session, coordinator monitoring/independent review/feedback until
  satisfactory, then focused worker commit/normal push and exact-SHA CI verification/fixes.
  See [coordination](iterations/16-versioned-implementation-selection/COORDINATION.md).
  This approves the bounded design/example/handoff for implementation, superseding their
  pending-review/GO wording, not scope. BOTH builds remain worker-owned until changed-surface
  freeze and explicit release. Follow the published validation policy; VP-001 remains
  OPEN/UNKNOWN, maintenance-only approval is not a standing Iteration16 waiver. Related
  async/LMDB/story changes require separately scoped investigation. Bounded current-installed
  local three-job selection/branches validation is authorized; missing downloads/installations
  need scoped approval. No extra workers/cloud/global tooling/generic registry/cache/framework/
  resources/scheduler/release/package/later turn or design checkpoint commit/push.
  This turn is independently ACCEPTED for focused publication at exact frozen14;
  see [review](iterations/16-versioned-implementation-selection/REVIEW.md). Independent32
  focused/installed54 nonexecuting pass; worker corrected full2263/unchanged gates and
  actual3-job/9-phase+8readers reviewed. BOTH builds/source/stopped-owned evidence returned
  for focused worker commit/normal existing push/actual final-SHA CI triage and reviewed
  fixes. Original failed AST coverage/controller reconstructed provenance/UNKNOWN preserved;
  VP-001 OPEN/no standing waiver. Final publication/CI/disposition/STOP pending; no extra
  full/fixture/later feature/design publication permission.
  During initial exact-SHA CI41120062048 review, macOS arm64 was cancelled before any
  steps/runner because of GitHub's scheduled macOS14 image brownout (primary annotation,
  official runner-images issue13518). The user separately APPROVED changing ONLY that
  matrix runs_on from macos-14 to macos-15, retaining arm64/all six jobs/tests/thresholds/
  existing budgets. Focused workflow/configuration regression/rationale review, then normal
  worker commit/push after original other jobs finish is within this narrow correction.
  No runtime/fixture/full/budget/release-control/repository-setting change; cancelled raw
  run/no Macarm report retained, not DML test failure/VP-001. New-SHA CI outcome pending.
  This bounded turn is **COMPLETE AND STOPPED** through published
  `e0089323cac3bc29b4301b4d3e7340d345d20d7a`, all six final exact-SHA CI41123236764 jobs
  successful, attempt1. See [review](iterations/16-versioned-implementation-selection/REVIEW.md)
  and [results](iterations/16-versioned-implementation-selection/RESULTS.md). Independent32
  focused/54 installed nonexecuting/24 runner correction checks, reviewed worker real3-job/
  9-phase+8reader/correctedfull2263 evidence remain distinct. Initial14+approved2 migration
  normally published; actual macos15-arm64 runner/native aarch64 execution verified. Owned
  fixtures archived/identity-retired; images/evidence retained. Original cancelled macos14
  brownout/noXML/fivepass CI, AST coverage failure and reviewed correction, weaker oracles/
  reconstructed controller hash, false migration pass/regex failure/corrected actual evidence/
  overwritten bad receipt reconstruction and other uncertainty preserved. VP-001 remains
  OPEN/UNKNOWN; final pass is not earlier runtime diagnosis/fix or standing waiver. Worker
  RESULTS finalized and explicitly STOPPED ALL activity/no further tools. Completed GO permits
  no worker/source/build/fixture/image/CI restart, extra agent/cloud/global/release/package/
  later feature/design checkpoint commit/push; user review does not inherit new-turn permission.
- Iteration 17's [candidate design/example/handoff](iterations/17-implementation-supersession/HANDOFF.md)
  follow the user's agreement to advisory implementation supersession: one intent/two captured
  bindings, structured correctness-fix versus operational-replacement reason/evidence, explicit
  successor default promotion, preserved selectable predecessor/history/branches, as-known-then
  versus separately selected knowledge. No automatic invalidation/deletion/cross-binding reuse/
  fresh work/adoption. Agreement authorizes planning, not exact L/basis/reader/schema/transaction/
  four-Q/two-local-attempt mechanics or implementation/delegation/publication GO. Separate
  known-slot ordinary L, unchanged Idef/menu/choice/D/Q/T/W, public composition/local acceptance
  are assistant candidates for review. Read all three documents before review.
  Current DML remains clean publishede0089323/Iteration16 complete-stopped/all6CI successful;
  no worker/source/spec/diagram/build/fixture/image/CI/experiment/provisioning/commit/push or
  extra agent/cloud/global/release/package/later feature/design checkpoint. Completed GO is
  not inherited. VP-001 planning revisit remains OPEN/UNKNOWN/no standing waiver/investigation
  permission; finalMac15 pass is not earlier runtime diagnosis. Follow published validation
  policy; prefer focused local evidence, no automatic Batch fixture or duplicated full suite.
- The user subsequently declared **Iteration 17 GO** and authorized the existing window-2
  agent in a NEW Pi session, coordinator monitoring/independent review/feedback until
  satisfactory, then focused worker commit/normal push and exact-SHA CI verification/fixes.
  See [coordination](iterations/17-implementation-supersession/COORDINATION.md). This approves
  the bounded design/example/handoff and supersedes pending17 wording above, not scope.
  BOTH builds remain worker-owned until changed-surface/HEAD freeze and explicit release.
  Bounded current-installed FOUR-Q/TWO-local-attempt story is authorized; missing downloads/
  installations need scoped approval. Published proportionate validation policy applies;
  VP-001 OPEN/UNKNOWN/no standing waiver, related changes or recurrence need fresh scope.
  No extra workers/cloud/global tooling/generic lifecycle-cache framework/resources/scheduler/
  native entity/release/package/later turn/design checkpoint commit/push. Acceptance and
  publication outcomes pending; completed Iteration16 permissions are not inherited.
  This turn is now independently ACCEPTED at exact frozen12; see
  [review](iterations/17-implementation-supersession/REVIEW.md). Independent37 focused/
  installed712 NONEXECUTING checks pass, worker sole full2364 and actual FOUR-Q/TWO-local-
  attempt story reviewed; SS-001 resolved, original failures/qualifications retained. BOTH
  builds/source/stopped story returned for focused worker commit/normal existing push and
  actual final-SHA CI evidence/fresh triage. Final publication/CI/disposition/STOP pending;
  no extra full/computation/fixture/later turn/design publication. VP-001 OPEN/UNKNOWN.
  This bounded turn is now **COMPLETE AND STOPPED** through published
  `9f182be635207e03c8cb1cc4f58973632dfe97c9`, all six final exact-SHA CI41172108791 jobs
  successful, attempt1. See [review](iterations/17-implementation-supersession/REVIEW.md)
  and [results](iterations/17-implementation-supersession/RESULTS.md). Independent37/712
  distinct from worker129/27/full2364/actual FOUR-Q/TWO-local-attempt story. Final six XML/
  primary/digests/exact12 clean source+remote verified; SS-001 resolved. Local children reaped/
  native evidence retained/no external fixture. Original failed probes/qualified original
  measured controller/corrected nonexecuting readers/VP-001 OPEN UNKNOWN retained; final
  pass is not older diagnosis or standing waiver. Worker RESULTS finalized and explicitly
  STOPPED ALL activity/no further tools. Completed GO permits no worker/source/build/CI/
  story/computation/image/service/investigation restart, extra agent/cloud/global/release/
  package/later turn/design checkpoint commit/push.
- Iteration 18's [candidate design/example/handoff](iterations/18-multi-input-reuse/HANDOFF.md)
  follow the user's confirmation of versioned multi-input reuse and request to prepare handoff:
  exact intent URI/full binding/full input matching, own new Q/no T on reuse, separate fresh/
  explicit one-key adoption, other entries and old branch choices retained. This authorizes
  planning only, not candidate schema/API approval/implementation/delegation/publication GO.
  Ordinary bounded M/entries/input-ID keys/unique immutable S slots/public slot revalidation/
  new Dm/request reader/sixteen-entry profile/SEVEN-Q-THREE-local story are assistant candidates,
  not as-built behavior or additional user decisions. Read all three documents before review.
  Existing exact Idef/menu/choice/D/Q/T/W/S/V remain; old selection-slot is not a table. No
  global cache/history discovery/eviction/masks/facets/equivalence/framework/resources/scheduler/
  native entity/lifecycle-reader unification assumed. DML clean published9f182be; Iteration17
  accepted complete-stopped. No worker/source/spec/diagram/build/story/image/CI/experiment/
  provisioning/commit/push or extra agent/cloud/global/release/package/later turn/design
  checkpoint. VP-001 planning revisit OPEN/UNKNOWN/no standing waiver/investigation; follow
  proportionate validation policy, no inherited duplicate-full/fixture rituals. Review then GO.
- The user subsequently declared **Iteration 18 GO** and authorized the existing window-2
  agent in a NEW Pi session, coordinator monitoring/independent review/feedback until
  satisfactory, then focused worker commit/normal push and exact-SHA CI verification/fixes.
  See [coordination](iterations/18-multi-input-reuse/COORDINATION.md). This approves the bounded
  design/example/handoff, superseding pending18 wording above, not scope. BOTH builds remain
  worker-owned until changed-surface/HEAD freeze and explicit release. Bounded current-installed
  SEVEN-Q/THREE-local-attempt story is authorized; missing downloads/installations need scoped
  approval. Published proportionate validation policy applies; VP-001 OPEN/UNKNOWN/no standing
  waiver, related changes or recurrence need fresh scope/triage. No extra workers/cloud/global
  tooling/generic cache/framework/resources/scheduler/native entity/release/package/later turn
  or design checkpoint commit/push. Acceptance/publication/CI outcomes pending.
  This turn is independently ACCEPTED at exact frozen ELEVEN paths/HEAD9f182be; see
  [review](iterations/18-multi-input-reuse/REVIEW.md). Independent38 focused/installed1179
  NONEXECUTING pass; worker sole full2489/focused163/actual SEVEN-Q/THREE-local story reviewed.
  MI-001 resolved, original failed probes/private-driver qualifications/coordinator oracle
  corrections retained. BOTH builds/source/stopped evidence returned for accepted focused
  worker commit/normal existing push/actual final-SHA CI triage and reviewed fixes. Final
  publication/CI/disposition/STOP pending; no extra full/computation/fixture/later turn/design
  publication. VP-001 OPEN/UNKNOWN/no standing waiver.
  This bounded turn is **COMPLETE AND STOPPED** through published
  `3b2b370f4f275d324d9c8cbc93e5a915b9c59149`, all six final exact-SHA CI41182904065 jobs
  successful, attempt1. See [review](iterations/18-multi-input-reuse/REVIEW.md) and
  [results](iterations/18-multi-input-reuse/RESULTS.md). Independent38 focused/1179 installed
  NONEXECUTING distinct from worker163/sole full2489/actual SEVEN-Q/THREE-local story/25phases.
  Final six shared XML/primary/digests/exact11 clean source+remote verified; MI-001 resolved
  with hosted Windows evidence. Three local children reaped/evidence retained/no external
  fixture. Original failed probes/private-mutant-driver non-snapshot qualification/coordinator
  oracle corrections/VP-001 OPEN UNKNOWN retained; final pass not older diagnosis/waiver.
  Completed GO permits no worker/source/build/CI/story/computation/image/service/investigation
  restart, extra agent/cloud/global/release/package/later turn/design checkpoint commit/push.
- Iteration 19's [candidate design/example/handoff](iterations/19-intent-scoped-reuse/HANDOFF.md)
  were prepared at the user's request after agreement on intent-scoped cross-implementation
  reuse for exact full inputs and explicit selection removal. Same-intent membership declares
  result equivalence; requested versus producing bindings remain separate provenance. Removal
  preserves other entries/old S/history/branches; default miss fresh work does not auto-adopt.
  Persistent result restrictions/deprecation eligibility gates are deferred, superseding the
  earlier restriction proposal. Preparation is authorized, NOT exact candidate schema/API
  approval/implementation/delegation/publication GO. Read ALL three docs before review.
  Recommended NEW Mi/Di roles/public S+ownQ/direct ordinary W composition, sixteen-entry profile,
  exact-key-present removal and SIX-Q/FOUR-local story are assistant candidates, not as-built
  behavior. Old exact-binding helpers/old roles stay unchanged; no private codec/new native
  entity/generic cache/framework/UX namespace redesign or actual Docker-Batch experiment assumed.
  DML remains clean published3b2b370/Iteration18 reviewed complete-stopped. No worker/source/
  spec/diagram/build/story/image/CI/experiment/provisioning/commit/push or extra agent/cloud/
  global/release/package/later turn/design checkpoint. VP-001 planning revisit OPEN UNKNOWN/
  no standing waiver/investigation; owning proportionate validation policy applies. Review
  then separate GO; completed18 permissions are not inherited.
  The user subsequently stated **“reviewed”**; this records bounded design/example/handoff
  review, NOT implementation/delegation/publication GO or as-built behavior. Exact engineering
  spellings remain refinable. No worker/source/build/story/CI restart or commit/push.
- The user subsequently declared **Iteration 19 GO** and authorized the existing window-2
  agent in a NEW Pi session, coordinator monitoring/independent review/feedback until
  satisfactory, then focused worker commit/normal push and exact-SHA CI verification/fixes.
  See [coordination](iterations/19-intent-scoped-reuse/COORDINATION.md). This approves the bounded
  design/example/handoff and supersedes pending19 wording, not scope. BOTH builds remain
  worker-owned until changed-surface/HEAD freeze and explicit release. Bounded current-installed
  SIX-Q/FOUR synchronous LOCAL-attempt story is authorized; missing downloads/installations
  need scoped approval. Published proportionate validation policy applies; VP-001 OPEN UNKNOWN/
  no standing waiver, related changes or recurrence need fresh scope/triage. No extra worker/
  cloud/global tooling/native entity/generic cache/framework/resources/scheduler/release/package/
  later turn/design checkpoint publication or Batch/SSH/Docker/image/service restart.
  Acceptance/publication/CI outcomes pending; completed18 permissions are not inherited.
  This turn is now independently ACCEPTED exact frozen TWELVE/HEAD3b2b370; see
  [review](iterations/19-intent-scoped-reuse/REVIEW.md). Independent48 focused/1384 installed
  NONEXECUTING pass; worker209/solefull2657/actualSIX-Q-FOUR-local26phase reviewed. IS-001 resolved,
  original failures/early91 nonsnapshot qualification retained. BOTH builds/source/stopped evidence
  returned for accepted focused worker commit/normal push/actual final-SHA CI/fresh triage and
  reviewed fixes. Final publication/CI/disposition/STOP pending; no extra full/computation/fixture/
  later turn/design publication. VP-001 OPEN UNKNOWN/no standing waiver.
  Publication is now exact `a71e89f80f319a4abc4f3d1b57ab1ad8ffe559ed`; actual
  CI41269736666/attempt1 RAW FAILED: four jobs pass, Windows+Macx86 old async host-client
  story fails completion15s/native publication/owner rc1-reaped/truncated LMDB-openENOENT,
  roots/attribution UNKNOWN. ALL164 new+4cleanup pass EVERY platform; independent shared
  sixXML/primary/digests verified. See [CI blockers](iterations/19-intent-scoped-reuse/CI-BLOCKERS.md).
  No exception approved or related-runtime investigation/rerun authorized. Worker explicitly
  PAUSED ALL activity/no further tools pending direction, NOT finalSTOP. User scoped decision
  pending; no source/build/CI/story/computation/investigation restart, old VP-001 waiver or
  new all-green/fix/inherited claim. Original retrieval/attribution oracle corrections retained.
  The user subsequently explicitly chose **Authorize a bounded investigation** for the two
  fresh CI failures. Read [scoped plan](iterations/19-intent-scoped-reuse/CI-INVESTIGATION.md)
  and coordination. Existing worker/current session may first prepare concrete diagnostic plan
  for coordinator review, then finite question-driven probes/causal fixes/regressions/accepted
  normal publication+exactCI. BOTH builds worker-owned until targeted freeze/release. This narrowly
  supersedes related async/LMDB investigation pause where reviewed evidence requires changes,
  not feature scope; no timeout/skip/threshold/budget/runner weakening/retry-until-green/extra
  worker/cloud/global/image/service/new feature/later turn/design publication. Original rawFAILED
  run/UNKNOWN/VP-001 retained; no exception or diagnosis approved, specific plan review pending.
  Investigation P1/P2/P3 now complete: THREE finite exploratory invocations; independent SAME
  stopped evidence confirms copied forced-POSIXSEM legal last-close/new-shared-open errno2 with
  intact files, NOT original hosted attribution/Windows proof/VP-001 diagnosis. All3 slots consumed.
  Coordinator selected A ONLY (actual-platform test-private native controls), B private worker-core
  tracing seam rejected. Exact3 diagnostic source files prepared/frozen/statically reviewed; see
  CI-INVESTIGATION/COORDINATION. Coordinator explicitly scopes ONE unchanged final standard-v
  validation of NEW test tooling as local execution FOUR overall (not relabelled probe3), no
  native pre-run/second full/P3 or installed6Q4T repeat. BOTH builds exclusively worker-owned until
  targeted freeze/release for SAME-evidence review; diagnostics commit/push/CI/fix not yet authorized.
  Provider retries/same-session compaction retained, same model as user requested; no extra agent/
  model/global config/runtime scope change. Actual Mac/Windows evidence and old attribution pending.
  Diagnostic-only exact3 published `beafc0ee5bedbe28f23036f29106334cb2f79b55`, CI41294882995
  attempt1 RAW CANCELLED:4success/Macx new epoch-oracle FAIL/Windows outer10CANCEL-noXML.
  Actual Macarm full native evidence confirms legal named-semaphore ENOENT mechanism with intact
  files, NOT original historical attribution/VP-001 diagnosis; Windows native cases partialstdout
  PASS only, different oldcaller FAIL cause UNKNOWN. Raw fiveXML/primary/digests/proofs retained.
  User says continue and separately APPROVES ONLY WindowsAMD64 outer cap10->20 (all test/runtime
  deadlines/thresholds/skips/runners/other budgets unchanged) and ONE additional diagnosticnewSHA
  round after reviewed oracle correction. See CI-INVESTIGATION/COORDINATION. Exact3 round2 SOURCE
  frozen/released: workflow scalar + owning budget regression + pure per-epoch namespace oracle/
  negatives. Cdriver/header/core/vendored/B unchanged. Proposed first SAME retained Macxreader
  then ninepure cases+oneworkflowcheck, NO compiler/nativeactors/full/P3/installedstory/API run;
  overall gate5 requires explicit review/release. No diagnostic round2 publication or nativefix
  authorization yet; original UNKNOWN/false receipts/qualification retained, no exception/green claim.
  Extra diagnosticround2/pure gate5 accepted/published `47131da927d76b190bb37f4384d887f2edcb65f5`;
  CI41299279030 attempt1 rawCANCELLED fiveSUCCESS/Macx outer20CANCEL despite complete passing
  sixXML/test steps. Independent full actual Mac+Windows named-resource mechanism/nativecontrols
  confirmed, NOT original historical cause/VP001 diagnosis. Windows source bytes individually exact
  LF->CRLF qualified, not rawidentity; raw reports/errors retained. User separately APPROVES ONLY
  Macx outer20->30 FOR reserved reviewed causalfixround, Window20/others10/strict/tests unchanged;
  NO diagnosticthird round. Existing worker READ-ONLY minimal nativefix/regression/provenance/finite
  validation plan before ANY edit/build/run/publication. BOTH/source coordinator-owned while planning.
  No productionfix implemented/approved yet; no generic cache/framework/hidden retainedhandles/
  catchENOENT/bootstrap/sleep/workflowretry. Exact native OS-lock rationale/source/safety/validation
  and independent acceptance required; original rawfail/cancel/UNKNOWN/qualifications preserved.
- Preserve corrections and uncertainty rather than silently turning proposals
  into decisions.
- The user permits narrow coverage exclusions when exercising the precise
  lines/branches/regions adds no useful assurance. Preserve thresholds for the
  remaining code, document each rationale and distinguish tested from excluded
  code. Difficult but meaningful failure paths still need tests. See the
  implementation [testing guidance](../dml/AGENTS.md#testing).
- Files under `archive/` are historical context, not active instructions. Do not
  execute their old coordinator or completion-marker protocols.

## Current separately authorized maintenance

The user agreed to proportionate design-spiral validation and authorized the existing
window-2 agent in a NEW Pi session to implement the [validation-policy maintenance
plan](maintenance/validation-policy/PLAN.md), with coordinator monitoring/independent
review/feedback, focused commit/normal push and CI fixes. Coordinator is authorized to
revise this bounded plan using evidence from CI. Read [handoff](maintenance/validation-policy/HANDOFF.md)
and [coordination](maintenance/validation-policy/COORDINATION.md). This supersedes
completed-turn no-restart wording ONLY for this separate maintenance scope, not DML
runtime features or Iteration16. No extra agents/cloud/global tooling/services/
release/package/design checkpoint publication or retired fixture/image restart.

Focused changed-behavior checks and relevant concrete acceptance are primary; CI is
complementary portability/regression evidence. No automatic all-six-green gate or
repeated full-suite/source-inventory/fixture rituals. Preserve thresholds, raw failures
and uncertainty. New attributable failures block; inherited/unknown failures require
explicit evidence/risk review, named follow-up and recorded acceptance exceptions,
never greenwashing/blanket unchanged-test exemptions/retry-until-green. Worker owns BOTH
builds until changed-surface freeze/explicit release; coordinator validation is focused
and risk-based. Past frozen reports/handoffs retain historical evidence/requirements.
The owning implementation [development validation policy](../dml/docs/validation-policy.md)
is now published; future authorized handoffs should reference that authority rather
than inherit accumulated per-iteration validation rituals. Historical reports stay intact.
This maintenance turn is **complete and stopped** at published
`4a05334058a77e78c8ad9c512726123fc347e352`, accepted **with [exception VP-001](maintenance/validation-policy/EXCEPTION-VP-001.md)**.
Raw CI41098299553 attempt1 FAILED: five jobs successful, one macOS arm64 old async-story
ENOENT failure; root cause/attribution UNKNOWN, not diagnosed inherited or fixed. All15
new reporting cases pass each platform and six actual XML reports preserve raw outcomes.
Read [review](maintenance/validation-policy/REVIEW.md)/[results](maintenance/validation-policy/RESULTS.md).
VP-001 follow-up owner coordinator%197 must revisit at next planning/review checkpoint,
before related async/LMDB/report-timing/story/release-assurance changes or recurrence.
No standing failure waiver or permission to launch investigation/workers/build/fixture/
CI rerun/native/runtime edits follows completed GO. No design checkpoint requested.
No approval to alter release controls or repository settings. See PLAN for exact scope.

## Current user decision: development GHA disabled

The user explicitly requested disabling GHA for the design spiral. Coordinator disabled ONLY
`micha/dml` development workflow CI232868302; GitHub API verifies `disabled_manually`, while
Release Python233518745 stays `active`. See
[decision/state](iterations/19-intent-scoped-reuse/GHA-DISABLED.md). This narrowly supersedes
future design-spiral development-GHA/final-SHA CI launch requirements above; do not re-enable
or run development GHA without a new user decision. No repository-wide Actions shutdown,
release-control or local test/threshold change. Workflow source untouched; DML clean HEAD47131da.
Existing worker explicitly PAUSED ALL/no further tools, BOTH builds/source coordinator-owned.
Private native candidate retained, harness incomplete/unexecuted; no compiler/actors/build/native/
production/package/commit/push permission or reserved fixCI launch. Historical raw failures/
cancellations/UNKNOWN/VP001 retained; disabled CI is not a pass/fix/diagnosis or automatic final
Iteration19 delivery disposition. No design checkpoint commit/push requested.

## Iteration 20 candidate preparation

The user agreed to preserving the actual upstream producer reference while explicitly versioning
exact-input versus result-based downstream reuse matching, then requested **“prep the iteration”**.
Read ALL THREE [design/example/handoff](iterations/20-result-based-input-reuse/HANDOFF.md) documents
before review. Preparation is authorized, NOT exact candidate-schema/API approval or implementation/
delegation/publication GO. Recommended fixed role/value/producer/factor input profile, ordinary
P/Mp/Dp/projection roles, upstream/downstream public S authority, separate full-Q/W provenance,
bounded16 tables and SEVEN-Q/SIX synchronous LOCAL story are assistant candidates, not as-built.
No generic masks/native facet entity/framework/resources/scheduler/restrictions/UX cleanup assumed.
DML verified clean HEAD47131da; feature19 accepted/publisheda71e89f, native investigation PAUSED,
private candidate incomplete/unexecuted retained, BOTH builds/source coordinator-owned. Development
GHA remains disabled; no re-enable/run or nativefix/VP-001 diagnosis/standing waiver. Planning
revisit VP-001 OPEN UNKNOWN, fresh related recurrence needs scoped triage. No worker/source/spec/
diagram/build/story/image/CI/investigation/experiment/provisioning/commit/push restart, extra agent/
cloud/global/release/package/later turn/design checkpoint. Read candidates for review, then separate
GO; completed or paused earlier authorizations are not inherited.

## Iteration 20 redirected direction

The user subsequently raised callable argument/caching concerns and stated **“yes, let's try
this new direction for iteration 20”**. See [direction](discussion.md#iteration20-redirection-value-arguments-and-separate-provenance).
This supersedes the projection-policy candidate as the active direction; its three documents
are DEFERRED/historical, not an implementation handoff. Func means DML callable/logical intent;
caching may mean reuse. Funcs should receive typed computational values, not implicit argument
provenance, with DML source references recorded separately; caching should match func/value
rather than derivation. Explicitly supplied provenance data is a computational argument.
Direction agreed, not exact value/access/API/schema/story approval or implementation GO.
Revised candidate not yet prepared. The user further agreed to recorded argument-map construction/
insertion retaining source-node relationships and callable datum-only map access; see
[argument maps](discussion.md#iteration20-argument-maps-value-structure-versus-construction-provenance).
Current datum-map storage is not a computational construction/access primitive. Exact operation
representation/API/evaluation/acceptance plan remain open; no native operation-node schema or generic
evaluator selected, no implementation GO. Don't assume arbitrary DAG-root scalar extraction or a
security sandbox/full-capture guarantee. No DML/glossary/spec/diagram/source/build/story/worker/
investigation/CI restart or commit/push; development GHA disabled/native investigation PAUSED/
VP-001 OPEN UNKNOWN/BOTH coordinator-owned remain. Future review then separate GO required.

## Iteration 20 recorded-map prototype agreement

The user further stated **“agreed”** to the bounded prototype proposal; see
[agreement](discussion.md#iteration20-agreed-prototype-recorded-map-operations-and-datum-only-callable-access).
Plan direction: ordinary DAG conventions/fixed Python implementations of map_empty, immutable
map_insert and map_get before native operation-node layouts/general evaluator. String argument
keys; duplicate insert/missing access error; replacement deferred. Func receives map datum and
datum-only operation interface, no implicit graph/repository access; recorder associates source
with THIS invocation, not a global origin inferred from equal datum IDs. Explicit returned-datum
contract, no arbitrary DAG-root extraction. Caching func+argument-map datum, source relationships
and old-vs-requested attempt provenance separately retained. Proposed literal42/freshdouble84,
computed13+29/samemap/downstreamreuse, computed43/differentmap/freshdouble86 story remains to be
planned with exact counts/API/schema/validation. Agreement is not implementation GO or a prepared
replacement handoff. Prior projection candidate deferred; no source/worker/build/story/CI/native
investigation/commit/push restart, glossary/spec/diagram change, extra agent/cloud/global/release/
package/later turn. GHA disabled/native investigation PAUSED/VP-001 OPEN UNKNOWN/BOTH coordinator-
owned remain. Review replacement candidates then separate GO; no design checkpoint requested.

## Iteration 20 replacement candidates prepared

After being told replacement design/example/handoff preparation was next and implementation GO
remained separate, the user said **“proceed”**. Read ALL THREE
[replacement documents](iterations/20-recorded-argument-maps/HANDOFF.md) before review; see
[preparation](discussion.md#iteration20-replacement-candidate-preparation). Preparation complete,
not exact candidate-schema/API approval or implementation/delegation/publication GO. Recommended
ordinary primitive/source/input/returned-datum/trace/Md/Dd roles, bound datum-only facade,
16-argument/16-access/64-operation-source profile and FIVE-Q/FOUR synchronous LOCAL story are
assistant candidates. Native MAP children remain datum IDs; actual source associations stay in
construction DAGs; full Q preserved; public S/returned profile supplies computed value authority.
Getter uses THIS invocation source, no global datum-origin registry; logical func lacks implicit
graph/context access, wrapper trusted authority unchanged/not security sandbox. Fixed Python/
ordinary-DAG prototype, no general evaluator/native opcode/entity/framework/cache discovery.
Old projection candidates DEFERRED, old helper APIs unchanged. DML verified clean HEAD47131da;
GHA disabled/native investigation PAUSED/private candidate incomplete-unexecuted/VP-001 OPEN
UNKNOWN/BOTH coordinator-owned remain. No source/glossary/spec/diagram/worker/build/story/CI/
native investigation/experiment/service/image/commit/push restart, extra agent/cloud/global/
release/package/later turn/design checkpoint. Related recurrence needs fresh scope/triage; no
standing waiver or inherited completed-GO permissions. Review replacement plan then separate GO.

The user subsequently stated **“reviewed”**; see
[review checkpoint](discussion.md#iteration20-replacement-plan-review). This records bounded
replacement design/example/handoff review, not implementation/delegation/publication GO or
as-built behavior. Exact engineering spellings remain refinable. Separate GO required; no
source/worker/build/story/CI/investigation restart, commit/push or new design checkpoint.

## Iteration 20 implementation GO

The user subsequently declared **Iteration 20 GO** and authorized the existing window-2
agent in a NEW Pi session to implement the reviewed replacement recorded-argument-map
[design/example/handoff](iterations/20-recorded-argument-maps/HANDOFF.md), coordinator
monitoring/independent review/feedback until satisfactory, then focused worker commit/normal
push and CI fixes. See [coordination](iterations/20-recorded-argument-maps/COORDINATION.md).
This supersedes pending20/no-restart wording ONLY for the bounded replacement scope, not
its limits or the deferred projection plan. BOTH builds/source explicitly handed to worker
until changed-surface/HEAD freeze and release. Bounded installed FIVE-Q/FOUR synchronous LOCAL
attempts/SIX getter trace positions, focused checks/one final unchanged full-v and risk-based
SAME-history nonexecuting independent review authorized; missing installations/downloads need
scoped approval. Development GHA remains disabled; no enable/run/workflow/budget/runner/release
control change. Native investigation PAUSED/private candidate incomplete-unexecuted retained,
VP-001 OPEN UNKNOWN/no standing waiver; recurrence/related changes need fresh scoped triage.
No extra worker/cloud/global/service/image/generic evaluator-cache-framework/native entity/
resources/scheduler/release/package/later turn/design checkpoint commit/push. Acceptance and
publication outcomes pending; completed or paused earlier permissions are not inherited.

This bounded Iteration20 turn is now **COMPLETE AND STOPPED** through normally published
`7e9bf133d5d175a492fb1e9d651e91a476358604`, exact accepted15/parent47131da/clean source-index/
live remote independently verified. See [review](iterations/20-recorded-argument-maps/REVIEW.md)
and [results](iterations/20-recorded-argument-maps/RESULTS.md). Independent37 focused/installed2424
NONEXECUTING distinct from worker v6 167/v7 8/v8 1 focused/full2798/actual FIVE-Q-FOUR-local-SIX-getter/
native135; SAME retained491rows and4known0-reaped-absent children/no external fixture. Two oneLF
EOF-only test repairs/AST equality qualify older gate/test hashes, helpers/story exact; original
failed/weak mutant/oracle/UNKNOWN stderr/message-only unpushed amend/coordinator audit corrections
and65bytes possiblylost retained. Development GHA verified disabled_manually/NOT RUN/notpass,
release workflow active; no platform all-green/nativefix/VP-001 waiver. Native investigation
PAUSED/private candidate incomplete-unexecuted retained/VP-001 OPEN UNKNOWN. Worker final RESULTS
and STOP ALL/no further tools verified, BOTH/source/stopped evidence coordinator-owned. Completed
GO authorizes no worker/source/build/story/computation/reader/CI/native investigation/image/service/
extra agent/cloud/global/release/package/later turn/design checkpoint commit/push restart.

The user subsequently stated **“good work! reviewed”**, recording review and acceptance of
completed Iteration20; see [checkpoint](discussion.md#iteration20-user-review). Work remains
stopped, with no new turn/restart or design checkpoint commit/push permission. Existing
GHA-disabled/native-investigation-PAUSED/VP-001 OPEN UNKNOWN boundaries remain unchanged.

## Next-iteration built-in func direction

The user proposed and agreed to URI-addressed built-in funcs with internal versioned DML
implementations; see [discussion](discussion.md#next-iteration-built-in-funcs-and-internal-versioned-bindings).
Illustrative user model: dml://builtin/map/get -> implementation choice -> ordinary binding DAG
with adapter/interpreter/timeout NULL and source URI dml://source/builtin/map/get/v1. NULL selects
internal execution, source URI identifies exact shipped implementation version (not fetched or
captured bytes); historical handlers may be retained for compatibility, unsupported versions fail
explicitly/no latest fallback. This is conceptual direction agreement, not exact profile/API/
function-set/handoff approval or implementation GO. Initial map_empty/map_insert/map_get/list_get,
distinct binding role/public dispatch/ordinary operation trace/no per-primitive Q/T mechanics are
assistant candidates pending design. Existing value-only access/separate actual provenance/
func-full-argument-map-value reuse remain baseline; no security/full-capture guarantee. No DML/source/
spec/glossary/diagram/worker/build/story/test/CI/native investigation/experiment/commit/push restart
or extra agent/cloud/global/service/image/release/package/later turn/design checkpoint publication.
Iteration20 stays accepted complete-stopped/GHA disabled/native investigation PAUSED/private
candidate incomplete-unexecuted retained/VP-001 OPEN UNKNOWN/BOTH coordinator-owned. Future
bounded plan preparation when requested, review, then separate GO; no prepared next handoff yet.

The user further explicitly agreed to standard func invocation analogous to placing C arguments
on the stack: in DML, form an argument-map NODE whose value is the MAP datum; ALL funcs consume
that node and return a node. Built-ins may return a primitive operation node directly, other funcs
a node representing a result sub-DAG. Source relationships stay outside datum structure; node-based
calls do not grant implicit provenance access, and reuse remains func+full argument-map VALUE.
See [clarification](discussion.md#standard-func-invocation-argument-map-node-to-result-node).
This supersedes assistant shorthand that funcs receive bare datums rather than graph-level nodes,
not current as-built APIs. Exact node/value-access/result/primitive-recording/binding/occurrence
mechanics remain open; no new native layout/general evaluator or implementation GO selected.

## Iteration 21 candidate preparation

The user requested **“good. prep the iteration”** after the built-in/standard-node-invocation
summary. Read ALL THREE [design/example/handoff](iterations/21-internal-builtins/HANDOFF.md)
before review; see [preparation](discussion.md#iteration21-candidate-preparation). Preparation
is complete, NOT exact engineering profile/API/function-set/story approval or implementation/
delegation/publication GO. User's argument-map NODE -> NODE/common call/NULL internal versioned
binding direction is agreed. Recommended additive installed Python builtin module, four funcs/
map-get-v1-v2 handlers, ordinary semantic node profiles/native SubDAG storage carriers/16arguments-
16positions-64reached bounds/single-known-S/new Dn-Q-W/THREE-Q-TWO-local-sixteen-position story are
assistant candidates. Native C/CLI invocation deferred, inspection kept; no new native opcode/entity
or generic evaluator/registry/cache/framework. Native URI code CURRENTLY rejects ALL dml: refs;
candidate narrowly permits references, retains native grammar/canonical/hash/layout/allocation
rules and adds external local/exchange dml:-intent guards to preserve executable reservation.
This includes only URI/namespace validation, not LMDB/open/async/process/lifetime investigation
or relaxing old NULL-disallowed Python binding contracts. Exact engineering remains refinable.

DML verified clean published7e9bf133d5d175a492fb1e9d651e91a476358604; completed20 stays stopped.
No worker/source/spec/glossary/diagram/build/install/story/test/CI/native experiment/provisioning/
commit/push restart. GHA disabled/native19 investigation PAUSED/private candidate incomplete-
unexecuted retained/BOTH coordinator-owned/VP-001 OPEN UNKNOWN/no standing waiver. Related need
or recurrence requires fresh scope/triage. After future GO only: proportionate focused checks,
bounded fresh isolated install/current-installed story, one final unchanged full-v/SAME-history
risk-based independent review; missing dependencies/downloads need scoped approval. No extra
agents/cloud/global/service/image/release/package/later turn/design checkpoint publication.
Review candidate, then separate GO; prior completed/paused permissions are not inherited.

The user subsequently stated **“reviewed”**; see
[checkpoint](discussion.md#iteration21-plan-review). This records bounded Iteration21 design/example/
handoff review, NOT implementation/delegation/publication GO or as-built behavior. Exact engineering
spellings remain refinable. Separate GO required; no worker/source/build/install/story/CI/native
investigation restart or commit/push. Prior completed/paused permissions are not inherited.

## Iteration 21 implementation GO

The user subsequently declared **Iteration 21 GO** and authorized the existing window-2
agent in a NEW Pi session to implement the reviewed bounded internal-builtins
[design/example/handoff](iterations/21-internal-builtins/HANDOFF.md), coordinator monitoring/
independent review/feedback until satisfactory, then focused worker commit/normal push.
See [coordination](iterations/21-internal-builtins/COORDINATION.md). This supersedes pending21/
no-restart wording ONLY for this bounded scope. BOTH builds/source handed to worker until
targeted changed-surface/HEAD freeze and explicit release. Fresh bounded isolated local install,
THREE-Q/TWO synchronous LOCAL/SIXTEEN builtin-position story, focused checks/ONE final unchanged
full-v/risk-based SAME-history NONEXECUTING review authorized; missing downloads/installations
need scoped approval. Narrow native URI reference validation/external namespace guards only,
not LMDB/open/async/process/lifetime repair. Development GHA remains disabled/no enable-run/
workflow/budget/runner/release control change; native19 investigation PAUSED/private candidate
incomplete-unexecuted retained/VP-001 OPEN UNKNOWN/no standing waiver. Related need/recurrence
requires fresh scope. No extra worker/cloud/global/service/image/general evaluator-cache-framework/
native entity/resources/scheduler/release/package/later turn/design checkpoint commit/push.
Acceptance and publication outcomes pending; completed/paused permissions are not inherited.

This bounded Iteration21 turn is now **INDEPENDENTLY ACCEPTED exact frozen29** at parent
`7e9bf133d5d175a492fb1e9d651e91a476358604`; see [review](iterations/21-internal-builtins/REVIEW.md).
Independent48focused/FINAL-installed1424 NONEXECUTING pass; worker146/solefull2929/original-runtime
3Q2T16/SAME467/native506/final installed no-jobNaN95 remain distinct. BN001-004resolved, original
7aab story versus final60679 comparator qualification and failed/weak oracles/tooling preserved.
BOTH/source/prefixes/stopped evidence returned ONLY for exact29 focused stagedaudit/worker commit/
NORMAL existingpush/exact accepted-current-committed-parent-clean-remote identities/workflowGET/
RESULTS/disposition/explicitSTOP. Final publication/STOP pending; no source/test/build/story/read/
computation/CI/native19/later turn/design publication restart. GHA disabled/NOTRUN/notpass/release
control unchanged/VP001 OPEN UNKNOWN/no standing waiver; no fresh platformgreen or older diagnosis.

This bounded Iteration21 turn is now **COMPLETE AND STOPPED** through normally published
`a523b0bfc8c4cc9f96a36b7b62138d9645b3eab3`; exact accepted29/parent7e9bf13/clean source-index/
live originmaster/workflow states independently verified. See [review](iterations/21-internal-builtins/REVIEW.md)
and [results](iterations/21-internal-builtins/RESULTS.md). Independent48focused/FINAL-installed1424
NONEXECUTING distinct from worker146/solefull2929/original7aab-installed3Q2T16/SAME467/native506/
final60679 no-jobNaN95. BN001-004resolved; original versus final comparator/source qualification,
failed/weak oracles/EOF/doc/tooling/install wrapper/oldUNKNOWN preserved. Actual worker stagedaudit/
commit/normalpush0, no force/amend/tag/release/design publication. Independent final publication-
audit0 exact29/current/committed/accepted/source+remote and original/final15/three datahashes/
two known0reaped-absent children. Owned originals unavailable/evidence retained/no externalfixture.
Worker RESULTS finalized/explicitSTOP ALL/no further tools/BOTH/source/prefixes/stopped evidence
returned. GHA verified disabled_manually/NOTRUN/notpass/release workflow active; native19 PAUSED/
privatecandidate incomplete-unexecuted retained/VP001 OPEN UNKNOWN/no earlier diagnosis or standing
waiver/freshplatformgreen. Completed GO permits no worker/source/build/story/computation/reader/CI/
native investigation/image/service/extraagent/cloud/global/release/package/later feature/design
checkpoint commit/push restart; user review does not inherit new-turn permission.

## Iteration 22 candidate preparation

The user requested a next proposal, contributed swapped add(29,13)'s different upstream key/equal42,
then stated **“good, that seemed odd to me -- makes sense now. proceed”** after clarification.
Coordinator explicitly treated proceed as offered candidate preparation, not implementation GO.
Read ALL THREE [design/example/handoff](iterations/22-composed-node-calls/HANDOFF.md) and
[discussion/corrections](discussion.md#iteration22-composed-node-calls-candidate-preparation).
Preparation complete; exact candidate-schema/API/story approval and implementation/delegation/
publication GO pending. Existing `Recorder.load` ALREADY accepts retained normal-return nodes;
put_datum returns DATUM ID, not NODE ID. No missing extraction primitive assumed. New proposal
connects successful ordinary add/double/node arguments/value reuse/separate selected producer
witnesses, not generic evaluation. Recommended example-local C/decision/reader/public S plus
outerR/one known downstream slot/EIGHT-Q-SIX synchronous LOCAL-TEN-getter mechanics are assistant
candidates, not as-built/additional user decisions. Old builtin arguments/Q/helpers unchanged;
Q inputs retain actual R, selected producer T via separate captured C/S, not inside MAP values.

DML verified clean published `a523b0bfc8c4cc9f96a36b7b62138d9645b3eab3`, Iteration21 complete-stopped.
No DML/source/spec/glossary/diagram/worker/build/install/story/test/CI/native investigation/experiment/
service/image/commit/push restart. BOTH builds/source coordinator-owned; development GHA disabled/
NOT RUN/not pass/native19 PAUSED/private candidate incomplete-unexecuted/VP-001 OPEN UNKNOWN.
Planning revisit no standing waiver/investigation permission; related needs/recurrence require fresh
scope/triage. Owning proportionate validation policy after future GO: focused checks/one local
installed story/one worker final unchanged full-v/risk-based SAME-history NONEXECUTING review, not
automatic duplicate-full/computation rituals. No extra agent/cloud/global/generic framework/cache
registry/resources/scheduler/native entity/release/package/later turn/design checkpoint publication.
Review candidates, then separate GO; completed21/paused19 authorizations are not inherited.

## Iteration 22 implementation GO

The user subsequently declared **Iteration 22 GO** and authorized the existing window-2
agent in a NEW Pi session to implement bounded composed-node-call
[design/example/handoff](iterations/22-composed-node-calls/HANDOFF.md), coordinator monitoring/
independent review/feedback until satisfactory, then focused worker commit/NORMAL existing push.
See [coordination](iterations/22-composed-node-calls/COORDINATION.md). This approves the bounded
plan and supersedes pending22/no-restart wording ONLY within scope. BOTH builds/source explicitly
handed to worker until targeted changed-surface/HEAD freeze and release. Fresh isolated installed
EIGHT-Q/SIX synchronous LOCAL/TEN-getter story, focused meaningful checks/ONE final unchanged
worker full-v/risk-based SAME-history NONEXECUTING independent review authorized; missing downloads/
installations require scoped approval. Prefer NEW example-local public-API helpers/unchanged runtime;
missing seam requires coordinator review BEFORE expansion. Development GHA disabled/NOTRUN/notpass/
no enable-run-control change; native19 PAUSED/private candidate incomplete-unexecuted retained/
VP-001 OPEN UNKNOWN/no standing waiver. Related recurrence/needed changes require fresh scope.
No extra worker/cloud/global/service/image/generic evaluator-cache-framework/native entity/resources/
scheduler/release/package/later turn/design checkpoint publication. Acceptance/publication pending;
completed21/paused19 permissions are not inherited.

This bounded Iteration22 turn is now **INDEPENDENTLY ACCEPTED exact frozen13** at parent
`a523b0bfc8c4cc9f96a36b7b62138d9645b3eab3`; see [review](iterations/22-composed-node-calls/REVIEW.md).
Independent41 focused/installed1607 SAME641 NONEXECUTING pass; worker87+5/solefull3021/actual
8Q6T10getter reviewed distinct. Exact13 current/frozen/source/evidence/XML/emptyindex accepted;
original worker faults/test-only EOF qualifications/coordinator reader-oracle corrections retained.
BOTH builds/source/prefix/stopped evidence returned ONLY for focused stagedaudit/worker commit/
NORMAL existing push/exact accepted-current-committed-parent-clean-remote/workflowGET/RESULTS/
disposition/explicitSTOP. Final publication/STOP pending; no source/test/build/reader/story/
computation/GHA/native19/later action. Development GHA disabled/NOTRUN/notpass/release control
unchanged/native19 PAUSED/privatecandidate incomplete-unexecuted/VP001 OPEN UNKNOWN remain;
no older diagnosis/freshplatformgreen/standingwaiver/design checkpoint publication.

## Iteration 22 final delivery

This bounded Iteration22 turn is now **COMPLETE AND STOPPED** through normally published
`a57125cdf735310f2330226ce6272b3a67e53f62`, exact accepted13/parenta523b0b/clean source-index/live
originmaster/workflow states independently verified. See [review](iterations/22-composed-node-calls/REVIEW.md)
and [results](iterations/22-composed-node-calls/RESULTS.md). Independent41 focused/1607 installed
SAME641 NONEXECUTING distinct from worker87+5/solefull3021/actual8Q6T10getter. Full original executed
helper/controller/logical/reader/runtime bytes current; two tests ONE+ONE EOF-only/AST-equal earlier
hash qualifications, original failed/weak test faults/tooling/mutations/coordinator reader-oracle
corrections/expanded-SHA communication typo explicitly preserved. Publication stageaudit/commit/
NORMAL existingpush0; independent publicationaudit0 exact current+committed+accepted13+parent+
remote/installed15/stoppedhistory/six known0wait-reapedabsent children/ownedoriginals retired.
Worker RESULTS finalized/explicitSTOP ALL/no further tools/BOTH/source/prefix/evidence returned.
Development GHA verified disabled_manually/NOTRUN/notpass/releaseworkflow active; native19 PAUSED/
privatecandidate incomplete-unexecuted/VP001 OPEN UNKNOWN/no older diagnosis/freshplatformgreen/
standingwaiver. Completed GO permits no worker/source/build/test/story/computation/reader/GHA/
native investigation/image/service/extraagent/cloud/global/release/package/later turn/design
checkpoint commit/push restart. User review does not inherit new-turn permission.

## Iteration 23 candidate preparation

The user agreed to dependencies of ANY kind (callable bindings, constants, etc.) captured at
**closure creation time**, distinct from invocation arguments, then stated **“proceed”** after the
offer to prepare design/example/handoff with separate implementation GO. Read ALL THREE
[candidate documents](iterations/23-closure-bound-dependencies/HANDOFF.md) before review; see
[preparation](discussion.md#iteration23-candidate-preparation). Preparation complete, NOT exact
schema/API/identity/story approval or implementation/delegation/publication GO.

Read-only source review finds current builtin call dispatch fixed/internal, one normal callable
publication/exact local-exchange tree-parent shapes/direct-child custody. Assistant recommends
FIRST explicit closure/environment captures in ONE fixed scaled-sum ordinary func with internal
getter bindings and an I64 constant source; initial outer/separate-inner ordinary request proposal
DEFERRED as an assistant scope recommendation requiring review, not a user-selected engineering
limit. Generic capture direction is broader than this prototype's two supported dependency types.
Recommended ordinary F/E/K/C/D roles/E-before-B-before-C/no self-ID cycle/pinned child capture/NEW
intent+computational-capture-K+full-invocation-MAP key/one known S/SIX-Q-FOUR-synchronous-LOCAL-EIGHT-
getter story are assistant candidates, not as-built. Constant values partition K; distinct sources/
equivalent getter versions retain provenance but not different computational K. Exact equivalence
rule needs review; no recursive normal-call capture, general evaluator/masks/facets/framework/cache
registry/native entity/private codec or old-helper reinterpretation assumed.

DML verified clean publisheda57125c/Iteration22 complete-stopped; ONLY design-note preparation,
no DML/source/spec/glossary/diagram/worker/build/install/test/story/reader/CI/native investigation/
experiment/service/image/commit/push restart. BOTH source/builds coordinator-owned/GHA disabled/
NOTRUN/notpass/native19 PAUSED/private candidate incomplete-unexecuted retained/VP001 OPEN UNKNOWN.
Planning revisit same follow-up owner/conditions/no standing waiver; related need/recurrence needs
fresh scope/triage. After future review/GO only: owning proportionate validation policy, focused
checks/one isolated installed story/one final unchanged worker full-v/risk-based SAME-history
NONEXECUTING independent review. Missing downloads/installations need separate scope. No extra
agent/cloud/global/release/package/later turn/design checkpoint publication; completed22/paused19
permissions not inherited. Review all three, then separate GO.

## Iteration 23 implementation GO

The user declared **Iteration 23 GO** and authorized the EXISTING window-2 agent in a NEW
Pi session to implement the bounded [design/example/handoff](iterations/23-closure-bound-dependencies/HANDOFF.md),
coordinator monitoring/independent review/feedback until satisfactory, then focused worker commit/
NORMAL existing push. See [coordination](iterations/23-closure-bound-dependencies/COORDINATION.md).
This approves the bounded fixed scaled-sum/getter+constant capture plan and nested ordinary-call
deferral, superseding pending23 wording ONLY within scope. Exact engineering spellings refinable.
BOTH builds/source handed to worker until targeted changed-surface/HEAD freeze and explicit release.
Fresh isolated installed SIX-Q/FOUR synchronous LOCAL/EIGHT-getter story, focused meaningful checks/
ONE final unchanged worker full-v/risk-based SAME-history NONEXECUTING review authorized. Missing
installations/downloads need scoped approval; missing public seam requires review before expansion.
Development GHA disabled/NOTRUN/notpass/no enable-run-control change; native19 PAUSED/privatecandidate
incomplete-unexecuted retained/VP001 OPEN UNKNOWN/no standing waiver. Related need/recurrence requires
fresh scope/triage. No extra worker/cloud/global/service/image/generic evaluator-cache-framework/native
entity/resources/scheduler/release/package/later turn/design checkpoint publication. Acceptance and
publication outcomes pending; completed22/paused19 permissions are not inherited.
Initial final full-v RAW TOOL1000sTIMEOUT at pytest94%/native7pass has NO XML/checkexit/ownerexit/end;
not completed/pass, exact process-group exit disposition not retained. Worker found no active full
owner/check/pytest process and stopped. Coordinator explicitly authorizes ONE additional unchanged
full-v on SAME relevant source/new evidence directory to obtain missing remaining tests/coverage/
XML/true exit; omit optional bash-tool1000s harness cutoff, ALL test/runtime deadlines/thresholds/
skips/standard command unchanged. Read-only owned residual custody first/stop if uncertain; no
installedstory/native19 repeat/further automatic full. Raw incomplete evidence/UNKNOWN preserved;
see coordination. This is bounded validation completion, not a runtime diagnosis or new feature.
Iteration23 now independently ACCEPTED exact frozen13/parenta57125c; [review](iterations/23-closure-bound-dependencies/REVIEW.md).
Independent44focused/installed1066 SAME464 NONEXECUTING pass distinct from reviewed worker78+9/
complete full3108/sole6Q4LOCAL8getter. Actual13/source/evidence/emptyindex/4knownwait0reapedabsent
verified; two test-only ONE-LF EOF/AST-location-equal/earliermutant reconstructed qualifications and
RAWtoolTIMEOUT/groupUNKNOWN/63bytespossiblylost preserved. BOTH/source/prefix/stopped evidence returned
ONLY for accepted focused stagedaudit/worker commit/NORMAL existingpush/exactidentity/workflowGET/
RESULTS/disposition/explicitSTOP. Final publication/STOP pending; no source/test/build/reader/story/
computation/GHA/native19/laterturn/designpublication. GHA disabled/VP001 OPEN UNKNOWN/no waiver.
This bounded Iteration23 is now **COMPLETE AND STOPPED** through normally published
`965cec450356e5f776b68bc311fa4d7eaf690519`, exact accepted13/parenta57125c/clean source-index/live
originmaster/workflow states independently verified. See [review](iterations/23-closure-bound-dependencies/REVIEW.md)
and [results](iterations/23-closure-bound-dependencies/RESULTS.md). Independent44focused/1066 installed
SAME464 NONEXECUTING distinct from worker78+9/complete authorizedfull3108/sole6Q4LOCAL8getter.
InitialRAWfulltool1000sTIMEOUT/noXML/noexit/groupUNKNOWN, raw63bytespossiblylost/2warnings/test-only
ONE+ONE EOF-LF/ASTlocations-equal/earliermutant-reconstructed qualifiers/failed probes preserved.
Actual stageaudit/commit/NORMALpush0; independent publicationaudit0 exact current+committed+frozen13/
parent/remote/install15/SAMEdata/4knownwait0reapedabsent/ownedoriginals unavailable/evidence retained.
Worker finalized RESULTS/explicit FINAL STOP ALL/no further tools/BOTHsource-builds-prefix-evidence
returned. GHA independently disabled_manually/NOTRUN/notpass/release active; native19 PAUSED/private
candidate incomplete-unexecuted retained/VP001 OPEN UNKNOWN/no earlier diagnosis/standingwaiver/
freshplatformgreen. Completed GO permits no source/worker/build/test/story/computation/reader/CI/
native investigation/service/image/extraagent/cloud/global/release/package/laterfeature/design
checkpoint restart; user review does not inherit new-turn permission.

## Iteration 24 candidate preparation

The user agreed to the revised captured-ordinary-call direction and stated **“agreed. proceed”**
after the proposal/offer to prepare candidates. Read ALL THREE
[design/example/handoff](iterations/24-captured-ordinary-calls/HANDOFF.md) and
[agreement/preparation](discussion.md#iteration24-agreed-direction-and-candidate-preparation).
Preparation authorized/complete, NOT exact adapter/schema/API/identity/story approval or implementation/
delegation/publication GO. Captured ordinary funcs/node-to-node invocation/separate outer-inner reuse/
actual producer provenance/default pinning are agreed. “Trusted wrapper” means recording integration,
NOT execution adapter; responsibility distinctions do not predetermine separate services/entities.

Assistant recommends NEW example-local synchronous in-process outer adapter/strict outer Q-T-phase-
return-selection roles, unchanged synchronous LOCAL leaf exchange/direct-child custody, short recording
scopes/session-owned copied node handles, conservative intent+verifiedB/E+fullMAP keys and FOURouterQ/
THREEouterT/SIXleafQ/FIVELOCALleafT/14getter story (10Q8T/5direct launches). These are candidates for
review, NOT as-built/approved engineering/feasibility evidence. Old local/builtin/public S profiles and
helper keys stay unchanged; no fake local outer attempt, arbitrary URI equivalence/recursive evaluator/
cache framework/native entity/RPC/async/nested worker. Prospective graph/capability/publication/custody
pre-edit review after future GO; existing16/16/64 and transfer bounds retained, missing seam needs review.

DML verified clean published965cec4/Iteration23 complete-stopped; ONLY design-note preparation. No
source/spec/glossary/diagram/worker/build/install/test/story/reader/CI/native investigation/experiment/
service/image/commit/push restart or extra agent/cloud/global/release/package/later turn/design checkpoint.
BOTH builds/source coordinator-owned/GHA disabled NOTRUN notpass/native19 PAUSED/private candidate
incomplete-unexecuted retained/VP001 planning revisit OPEN UNKNOWN/same coordinator owner/conditions/
no standing waiver/investigation permission. Related need/recurrence needs fresh scope/triage. Review
candidates, then separate GO; completed23/paused19 permissions not inherited.

## Iteration 24 implementation GO

The user declared **Iteration 24 GO** and authorized the EXISTING window-2 agent in a NEW Pi
session to implement the bounded [design/example/handoff](iterations/24-captured-ordinary-calls/HANDOFF.md),
coordinator monitoring/independent review/feedback until satisfactory, then focused worker commit/
NORMAL existing push. See [coordination](iterations/24-captured-ordinary-calls/COORDINATION.md).
This approves the bounded example-local synchronous in-process outer adapter/unchanged LOCAL leaf
plan, superseding pending24/no-restart wording ONLY within scope. Exact engineering refinable;
mandatory concrete seven-item pre-edit review BEFORE coding/build/run; installed readiness review
BEFORE sole FOURouterQ/THREEouterT/SIXleafQ/FIVELOCALleafT/14getter story. Pre-edit gate subsequently
accepted [source-sharing alternative B ONLY](iterations/24-captured-ordinary-calls/PRE-EDIT.md): outer
getters enforce a,b I64, add receives ORIGINAL exact argument-map NODE, double map uses exact addR
DIRECT. TWO maps/three upperbound/14 actual owning positions remain; symbolic full evidence union50
not measured, actual prospective union/reservations before launch. Projection/new96budget rejected.
NEW example-local draft/focused checks/cache-only isolated install readiness prep authorized; STOP
at installed readiness review, no computation acceptance/publication yet. Coordinator subsequently
approved ONLY new unpublished-helper `MAX_AUTHORITY_DEPTH=8` after RAW focused-v6 required HOSTq4
walkdepth5 rejected draft4; shared propagated original-authority edge guard/actual retained ancestry
negative/prospective final-reader depth before launch. This is draft-schema refinement, not existing
native64/16/16/transfer/testthreshold/deadline/budget waiver; RAW12pass1fail preserved, no reset/skip/
automatic escalation. See coordination. FINAL readiness now independently STATIC accepted exact31/
TEN current copies/installed15/control0/coverage1144+ONEexcluded/ASTsourcequalification/storyABSENT.
Coordinator authorizes ONE exact sanitized installed10Q8T5LOCAL14getter story, known5wait0/reaped/
absent/owned retirement/SAME blocked readers, then successful-stage ONE final unchanged full-v/
targeted freeze-release for independent NONEXECUTING acceptance. Failure/uncertainty STOP/no automatic
secondstory/full rerun; publication STILL needs independent acceptance+explicit focused NORMALpush
instruction. GHA/native19/VP001 unchanged; static audit is not independent runtime assurance.
First authorized installed activation subsequently RAW FAILED controller duplicate-kind logging after
nativeget-a/BEFORE leafQ or OSlaunch. Finite SAME READ-ONLY triage0 confirms1outerQ1T1getter/zeroleaf-
LOCAL-publication-terminal/partialUNKNOWN/dataimmutable/children[]; originalwrapperPIDnotretained.
Coordinator approved ONLY controller event-envelope/consumer correction+ONE blockedmetadata1Q1T1getter
regression/ZEROordinary-LOCAL-OS/targeted controls/newTEN readiness. See
[failure plan](iterations/24-captured-ordinary-calls/ACTIVATION-FAILURE.md). Originals preserved;
NO freshstory/full/publication until new explicit readiness/activation decision, no runtime/native19
scope or retry-until-green. This narrowly supersedes prior successful-stage activation wording.
Corrected controller-only readiness subsequently STATIC accepted exact31/only3causalpaths/TENnewcopies/
regression29/control0/fivehelperunchanged/allfailedbytes in-place+archive. Coordinator separately
EXPLICITLY authorizes ONE NEW context acceptance/corrected/story command, same10Q8T5LOCAL14getter;
failed1Q1T1get ZEROleaf context retained separately/no import-resume-adoption. Failure/uncertainty
STOP/no automaticthirdattempt. Successful-stage known5reap/retirement/SAMEblockedreaders/ONEfinal
unchangedfull-v/freeze-release then independent acceptance; commitpush still gated. See coordination.
Corrected installed story/SAME blocked readers subsequently PASS actual10Q8T5LOCAL14getters/all5known0
reapedabsent. ONE unchanged full-v subsequently RAWTRUEEXIT1: native7/pytest3354+2warnings PASS,
coverage report NoSource synthetic HOST compilefilename, later bindingValgrind/CLI/lcov gates NOT
reached; Mull -m NOT requested. Coordinator authorizes ONLY finite READ-ONLY reporting-source plan/
preservation/inventory, no omission/exclusion/threshold weakening/sourceedit/test/full rerun yet.
Potential missing PythonJUnit must be verified/qualified, not reconstructed-as-actual. Rawfailedfull/
installedproof/firstfailedcontext preserved; see coordination. No native19/VP001 diagnosis/waiver.
User subsequently permits necessary coverage exclusions and asks to wrap ASAP. This narrowly permits
precise documented generatedHOST scaffolding/duplicate source-alias exclusions, canonical maintained
module bytes STILL measured/threshold100 unchanged; no broadomit/tests removed/ignoreerrors/fake source.
Expedited plan: preserved3354-pass/native7/fullcoverage data + minimal reporter correction/regression
and unreached original-stage commands, no automatic47min full replay or relabelled raw exit1 pass.
Exact minimal proposal/completion approval pending; GHA/native19/VP001/custody/publication gates unchanged.
BOTH builds/source handed
to worker until targeted changed-surface/HEAD freeze and explicit release. Focused meaningful checks/
ONE final unchanged worker full-v/risk-based SAME-history NONEXECUTING independent review; no extra
bash-tool1000s cutoff substituting for true completion. Missing installations/downloads need approval;
missing public seam/expansion requires review before changes/experiments. Development GHA disabled/
NOTRUN/notpass/no enable-run-control change; native19 PAUSED/privatecandidate incomplete-unexecuted/
VP001 OPEN UNKNOWN/no standing waiver; related need/recurrence needs fresh scope/triage. No extra
worker/cloud/global/service/image/generic evaluator-cache-framework/native entity/resources/scheduler/
release/package/later turn/design checkpoint publication. Acceptance/publication pending; completed23/
paused19 permissions not inherited.

## Iteration 24 final delivery

Iteration24 is **COMPLETE AND STOPPED** through normally published
`59b38303fe2f4c89d6fce3b01933f7260eb28320`, initial33 commit291d9a5/feature-parent965cec.
See [review](iterations/24-captured-ordinary-calls/REVIEW.md),
[results](iterations/24-captured-ordinary-calls/RESULTS.md) and
[coordination](iterations/24-captured-ordinary-calls/COORDINATION.md). Independent2052 installed SAME979
rows x TWO stores NONEXECUTING + reporter3 checks pass; exact cumulative33/currentcommittedaccepted
EOF-equivalence/clean source-index/live originmaster/workflows verified independently. Worker actual
installed10Q8T5DIRECT LOCAL14getter/SAME readers and original+resumed validation remain distinct.
Original full RAWexit1/native7/pytest3354+2warnings/PythonJUnitABSENT; userapproved EXACT3 generated
reporting-label exclusions and reporter3/resumed0 Python8962/8962/native1667lines131functions1550branches
100 complete requested stages WITHOUT second47min suite, NOT originalstandardpass/platformgreen.
ONEp124 raise exclusion/ASTlocation/sourceB bytequalification and rawcontrollerfirstfailure/partial
UNKNOWN/separate failedcontext/weak oracles/warnings/stageaudit2 unguardedcommit0/EOF wrongcount
correction(1/3/1/1 suffixonly, ASTlocations equal)/coordinator FNF129-vs-summary131 audit correction
preserved. Final normalpush0/publication audit0; no amend/force/tag/release/design publication.
Worker RESULTS finalized/explicitSTOP ALL/no further tools/BOTH source-builds-prefix-stopped evidence
RETURNED. GHA independently disabled_manually/NOTRUN/notpass/releaseactive; native19PAUSED/private
candidate retained/VP001OPENUNKNOWN/no earlier diagnosis/standing waiver. Completed GO authorizes no
worker/source/build/test/reader/story/full/CI/native investigation/image/service/extraagent/cloud/
global/release/package/laterfeature/design checkpoint restart; no design commit/push requested.

## Current design checkpoint

The user requested a checkpoint and review of learning through Iteration24. Read the
[synthesis](checkpoints/24-lessons.md) and updated discussion resume point. This authorizes
local design documentation/checkpoint commit of accumulated Iteration20–24 records only,
not a push, next engineering plan or worker/source/build/test/story/reader/CI/native investigation
restart. DML remains clean59b3830/Iteration24 complete-stopped/BOTH coordinator-owned/GHA disabled/
native19 PAUSED/private candidate retained/VP-001 OPEN UNKNOWN with existing owner/conditions.
Review questions are assistant suggestions, not selected next-turn decisions. Earlier per-turn
no-design-checkpoint-request wording remains historical, superseded only for this local request.

## Current test-performance checkpoint

After the Iteration24 learning review, the user separately authorized timing the Python
suite, optimizing the two slowest tests, then adding pytest-xdist and ONE four-worker trial.
Read [results](maintenance/test-performance/RESULTS.md) and
[checkpoint](checkpoints/test-performance.md). DML is now clean at LOCAL, NOT PUSHED
`55a73e9fa4895cce39a081070ebff906a3b67f19` (parent59b3830): inspection-local successful-proof
reuse, four safety regressions and optional pytest-xdist dependency. Original assertions,
semantic budgets/authority depth/deadlines/coverage thresholds remain. Final focused250/
standardfull3361+native7+memory+100 gates and separate parallel3361/8m58s pass; original warnings,
instrumentation/speedup/report-property qualifications/raw offline preparation failure retained.
External tools flake updated/unversioned with unchanged lockfile; exact bytes preserved. No push/CI.

The user requested a local commit, producing DML55a73e9 and design-results99cd523. After reviewing
the next two slow tests (parallel totals42.7/41.7s, each33.4s setup in an ungrouped fixture-consuming
module), the user requested “let's make a checkpoint here”. This authorizes ONLY local design
checkpoint documentation/commit, not grouping implementation or another optimization/run/push.
Grouping that consumer is an assistant suggestion pending user selection; no maintained parallel
runner/coverage gate selected. Existing workers stopped/source-builds coordinator-owned;
GHA disabled/native19 PAUSED/private candidate retained/VP-001 OPEN UNKNOWN/owner/conditions remain.
No tests/build/install/profile/story/worker/CI/native investigation restart, dependencies/service/
image/cloud/global/release/package/later turn or push authorized. Historical Iteration24 source
identity/status and earlier checkpoint statements remain historical, not current HEAD claims.

## Vocabulary

- Maintained documentation uses glossary terms consistently. Add or clarify a term
  when needed; do not silently give an existing term a different meaning.
- Design conversation follows the glossary on a best-effort basis. Informal phrasing
  is acceptable; clarify ambiguities that affect design and record agreed corrections.
- Keep provisional definitions provisional. Glossary inclusion does not imply an
  implemented feature or select a schema/API.
- Exact code identifiers, quotations, archived reports and frozen evidence may retain
  their original vocabulary. Explain mappings where useful; do not rewrite history.

## Notes and commits

- Maintain design notes here, not under the retired temporary task directory.
- The user requires `../dml/docs/lmdb-entity-diagram.html` to stay aligned with
  implemented LMDB entities/relationships, never proposals or future state. Include
  relevant diagram review in authorized implementation handoffs; follow the
  implementation [maintenance guidance](../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance).
  Design discussion alone does not authorize changing the diagram's technical claims.
- Keep `discussion.md`'s resume point current when recording a checkpoint.
- Use small, focused changes and validate local Markdown links.
- Never commit credentials, secret values, or sensitive research data.
- Make checkpoint commits when requested. Do not create a remote or push unless
  authorized.
