# DML design

Exploratory, agent-first design discussions for [DML](https://github.com/micha/dml).
This repository preserves design progress separately from the implementation and
its existing draft specifications.

## Start here

- **Checkpoint and learning review through Iteration24:**
  [readable synthesis](checkpoints/24-lessons.md) and
  [discussion checkpoint](discussion.md#checkpoint-through-iteration24-retrospective-review).
  Demonstrated capabilities, value/provenance/capture corrections, example-specific reuse identity,
  validation lessons and unresolved questions. User requested a local design checkpoint only;
  no push, implementation restart or next-turn GO. Completed24 stays stopped; older statuses below
  preserve chronology rather than new assignments.

- **Iteration24 COMPLETE AND STOPPED**, independently accepted and normally published
  **[`59b3830`](https://github.com/micha/dml/commit/59b38303fe2f4c89d6fce3b01933f7260eb28320)**:
  [review](iterations/24-captured-ordinary-calls/REVIEW.md),
  [results](iterations/24-captured-ordinary-calls/RESULTS.md),
  [coordination](iterations/24-captured-ordinary-calls/COORDINATION.md) and
  [implemented example](../dml/docs/captured-ordinary-calls.md). Captured ordinary calls/explicit outer
  and inner reuse/separate requested-versus-OLD producer chains/default pinning. Independent2052 SAME
  NONEXECUTING+reporter3; reviewed actual10Q8T5LOCAL14getter, combined3354-pass/rawfull1 + reporter3/
  resumedPython8962/native100. Exact cumulative33/EOF-only source qualification/clean/live remote/
  workflows verified, worker STOP ALL/BOTH returned. Raw failures/warnings/UNKNOWNs preserved;
  GHA disabled/NOTRUN/native19 PAUSED/VP001 OPEN UNKNOWN, no restart/later turn/design publication.
  Older status stages below historical where superseded.

- **Iteration24 GO; existing window-2 agent started in a verified NEW Pi session:** bounded
  [design](iterations/24-captured-ordinary-calls/DESIGN.md),
  [example](iterations/24-captured-ordinary-calls/EXAMPLE.md) and
  [handoff](iterations/24-captured-ordinary-calls/HANDOFF.md) approved for implementation,
  coordinator monitoring/independent review/feedback, then accepted focused worker NORMAL commit/push.
  See [coordination](iterations/24-captured-ordinary-calls/COORDINATION.md). Pre-edit review accepted
  source-sharing B ONLY: add consumes original map NODE, double map retains exact addR, TWO maps,
  unchanged14 actual getter positions/no projection/cap increase. FINAL readiness STATIC accepted;
  ONE bounded installed story+successful-stage SAME readers/final unchanged full-v authorized, no
  automatic replay. FIRST activation RAWfailedcontroller event-envelope collision BEFORE leaflaunch;
  SAME triage0 partialUNKNOWN/zerochildren, ONLY controllerfix+metadataregression approved. Freshreadiness/
  explicitactivation required before story/full. Independent acceptance/publication pending. BOTH builds/source worker-owned until targeted
  freeze/release. GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN; no extra worker/later turn/design
  checkpoint publication. Outcomes pending; older statuses historical where superseded.

- **Iteration24 captured-ordinary-call candidates prepared for review; separate GO pending:**
  [design](iterations/24-captured-ordinary-calls/DESIGN.md),
  [worked example](iterations/24-captured-ordinary-calls/EXAMPLE.md),
  [conditional handoff](iterations/24-captured-ordinary-calls/HANDOFF.md) and
  [agreement/preparation](discussion.md#iteration24-agreed-direction-and-candidate-preparation).
  Captured add/double calls use argument-map NODE -> result NODE; outer/inner reuse preserves actual
  producer chains and pinned dependencies. NEW example-local synchronous in-process outer adapter,
  short-batch node bridge/new outer profiles/conservative B-E identity/10Q8T5LOCAL14getter are assistant
  candidates, not approved engineering or as-built behavior. DML clean965cec4/completed23 stopped/BOTH
  coordinator-owned/GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN. Preparation only; no worker/source/
  build/test/story/reader/CI/investigation/commit/push restart/design publication. Review ALL THREE, then GO.

- **Iteration23 COMPLETE AND STOPPED**, independently accepted and normally published
  **[`965cec4`](https://github.com/micha/dml/commit/965cec450356e5f776b68bc311fa4d7eaf690519)**:
  [results](iterations/23-closure-bound-dependencies/RESULTS.md),
  [review](iterations/23-closure-bound-dependencies/REVIEW.md),
  [coordination](iterations/23-closure-bound-dependencies/COORDINATION.md) and
  [implemented example](../dml/docs/closure-bound-dependencies.md). Immutable getter+I64-scale captures
  stay separate from invocation arguments; capture-aware value reuse retains requested versus OLD
  executed provenance/default-independent pinning. Independent44/1066 SAME464 NONEXECUTING distinct
  from worker78+9/authorizedcompletefull3108/sole6Q4LOCAL8getter. Exact13/current+committed+frozen/
  parent/clean/live remote/workflows verified; worker finalSTOP/BOTH returned/4knownwait0reapedabsent.
  InitialRAWtoolTIMEOUT/groupUNKNOWN/raw63possiblylost/2warnings/EOF+mutant qualifications retained.
  GHA disabled/NOTRUN/notpass/native19 PAUSED/VP001 OPEN UNKNOWN; no restart/later turn/design checkpoint.
  Older status stages below historical where superseded.

- **Iteration23 GO; existing window-2 agent started in a verified NEW Pi session:** bounded
  [design](iterations/23-closure-bound-dependencies/DESIGN.md),
  [example](iterations/23-closure-bound-dependencies/EXAMPLE.md) and
  [handoff](iterations/23-closure-bound-dependencies/HANDOFF.md) approved for implementation,
  coordinator monitoring/independent review/feedback, then accepted focused worker NORMAL commit/push.
  See [coordination](iterations/23-closure-bound-dependencies/COORDINATION.md). BOTH builds/source
  worker-owned until targeted freeze/release; isolated6Q4LOCAL8getter/ONE final unchanged full-v/
  SAME-history NONEXECUTING review. GHA stays disabled/native19 PAUSED/VP001 OPEN UNKNOWN;
  no extra worker/later turn/design checkpoint. Outcomes pending; older statuses historical.

- **Iteration23 closure-bound-dependency candidates prepared for review; separate GO pending:**
  [design](iterations/23-closure-bound-dependencies/DESIGN.md),
  [worked example](iterations/23-closure-bound-dependencies/EXAMPLE.md),
  [conditional handoff](iterations/23-closure-bound-dependencies/HANDOFF.md) and
  [preparation/scope recommendation](discussion.md#iteration23-candidate-preparation).
  Any dependencies may be captured at closure creation; arguments are invocation-supplied.
  Recommended first slice captures getter bindings plus a constant in one scaled-sum func, with
  explicit immutable closure/environment and capture-aware value reuse. SIX-Q/FOUR-local/EIGHT-getter
  and deferring nested ordinary outer/inner requests are assistant candidates, not exact approved
  plan/as-built behavior. DML clean a57125c/completed22 stopped/GHA disabled/native19 PAUSED/VP001 OPEN
  UNKNOWN/BOTH coordinator-owned. No implementation/worker/build/story/reader/CI/investigation/
  commit/push restart or design checkpoint publication; review all three, then separate GO.

- **Iteration 22 COMPLETE AND STOPPED**, independently accepted and normally published
  **[`a57125c`](https://github.com/micha/dml/commit/a57125cdf735310f2330226ce6272b3a67e53f62)**:
  [results](iterations/22-composed-node-calls/RESULTS.md),
  [review](iterations/22-composed-node-calls/REVIEW.md),
  [coordination](iterations/22-composed-node-calls/COORDINATION.md) and
  [implemented composition example](../dml/docs/composed-node-calls.md). Ordinary add/double/node
  composition/value reuse preserves actual requested upstream S/T/R versus OLD executed producer.
  Independent41focused/1607 installed SAME641 NONEXECUTING; worker87+5/full3021/actual8Q6T10getter
  distinct. Exact13/current+committed+accepted/parent/clean/live remote/workflows independently verified;
  six known0wait-reapedabsent children/owned originals retired/evidence retained. Original failures/
  EOF-only test qualifications/reader-oracle corrections/SHA typo preserved. Worker finalSTOP/BOTH
  returned; GHA disabled/NOTRUN/notpass/native19 PAUSED/VP001 OPEN UNKNOWN. No restart/laterturn/
  design checkpoint publication. Older statuses historical where superseded.

- **Iteration 22 independently ACCEPTED exact13; focused worker publication pending:**
  [review](iterations/22-composed-node-calls/REVIEW.md),
  [results](iterations/22-composed-node-calls/RESULTS.md) and
  [coordination](iterations/22-composed-node-calls/COORDINATION.md). Independent41 focused/1607 installed
  SAME641 NONEXECUTING pass; reviewed worker87+5/full3021/actual8Q6T10getter distinct. Exact current/
  frozen13 accepted; worker stagedaudit/normal commitpush/identities/workflowGET/RESULTS/STOP only.
  Original failures/test-only EOF/reader-oracle corrections retained. GHA disabled/NOTRUN/native19
  PAUSED/VP001 OPEN UNKNOWN; no extra computation/laterturn/design publication. Outcomes pending.

- **Iteration 22 GO; existing window-2 agent in a verified NEW Pi session:** bounded
  [design](iterations/22-composed-node-calls/DESIGN.md),
  [example](iterations/22-composed-node-calls/EXAMPLE.md) and
  [handoff](iterations/22-composed-node-calls/HANDOFF.md) approved for implementation, coordinator
  monitoring/independent review/feedback, then accepted focused worker commit/NORMAL existing push.
  See [coordination](iterations/22-composed-node-calls/COORDINATION.md). BOTH builds/source worker-owned
  until targeted freeze/release; isolated installed EIGHT-Q/SIX-local/TEN-getter story/ONE final
  unchanged full-v/SAME-history nonexecuting review. GHA stays disabled/native19 PAUSED/VP001 OPEN
  UNKNOWN; no extra worker/later turn/design checkpoint. Outcomes pending; older statuses historical.

- **Iteration 22 composed-node-call candidates prepared for review; separate GO pending:**
  [design](iterations/22-composed-node-calls/DESIGN.md),
  [worked example](iterations/22-composed-node-calls/EXAMPLE.md),
  [conditional handoff](iterations/22-composed-node-calls/HANDOFF.md) and
  [discussion/corrections](discussion.md#iteration22-composed-node-calls-candidate-preparation).
  Existing installed return-node loading already supports computed sources. Candidate connects
  actual successful add/double steps, separate selected producer witnesses and downstream func/full
  MAP-value reuse, including add(29,13)'s different upstream key/equal42. Recommended new example-local
  C/decision/reader/EIGHT-Q-SIX-local-TEN-getter story needs review, not as-built/implementation GO.
  DML clean a523b0b/completed21 stopped/GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN/BOTH returned.
  No worker/source/build/story/CI/investigation/publication restart or design checkpoint requested.
  Read ALL three candidates, review, then separate GO. Older statuses below historical.

- **Iteration 21 COMPLETE AND STOPPED**, independently accepted and normally published
  **[`a523b0b`](https://github.com/micha/dml/commit/a523b0bfc8c4cc9f96a36b7b62138d9645b3eab3)**:
  [results](iterations/21-internal-builtins/RESULTS.md),
  [review](iterations/21-internal-builtins/REVIEW.md),
  [coordination](iterations/21-internal-builtins/COORDINATION.md) and
  [implemented builtin authority](../dml/docs/internal-builtins.md). Standard argument-map NODE
  calls, internal NULL/versioned URI bindings, shipped empty/insert/map-get-v1-v2/list-get and
  separate source/value provenance with explicit reuse. Independent48 focused/FINAL-installed1424
  NONEXECUTING; reviewed workerfull2929/original3Q2T16/SAME467/final-nojobNaN95. Exact29/current/
  committed/parent/clean source+remote verified. Original-story versus NaN-corrected final runtime
  qualification retained. Development GHA disabled/NOTRUN/notpass/native19 PAUSED/VP001 OPEN
  UNKNOWN; worker explicitSTOP/BOTH returned, no later turn/design checkpoint. Older states historical.

- **Iteration 21 independently ACCEPTED; focused publication pending:**
  [review](iterations/21-internal-builtins/REVIEW.md) and
  [coordination](iterations/21-internal-builtins/COORDINATION.md). Exact frozen29 paths;
  independent48 focused/FINAL-installed1424 NONEXECUTING, reviewed worker full2929 and original
  installed3Q2T16/SAME467 history. Original-story7aab versus final60679 NaN comparator qualification
  preserved; BN001-004 resolved. Worker authorized focused accepted commit/normalpush/exact identity/
  workflow-state/RESULTS/STOP only. GHA disabled/NOTRUN/notpass/native19 PAUSED/VP001 OPEN UNKNOWN;
  no later turn/design checkpoint. Final publication pending; older statuses below historical.

- **Iteration 21 GO; existing window-2 agent in a NEW Pi session:** bounded
  [design](iterations/21-internal-builtins/DESIGN.md),
  [example](iterations/21-internal-builtins/EXAMPLE.md) and
  [handoff](iterations/21-internal-builtins/HANDOFF.md) approved for implementation,
  coordinator monitoring/independent review/feedback, then accepted focused worker commit/normal
  push. See [coordination](iterations/21-internal-builtins/COORDINATION.md). BOTH builds/source
  worker-owned until targeted freeze/release; fresh isolated install/THREE-Q-TWO-local/SIXTEEN
  builtin positions/one final unchanged full-v/SAME-history nonexecuting review. Development GHA
  stays disabled/native investigation PAUSED/VP-001 OPEN UNKNOWN. No extra worker/cloud/global/
  later turn/design checkpoint publication; outcomes pending. Older statuses below historical.

- **Iteration 21 bounded plan reviewed; implementation GO pending:**
  [design](iterations/21-internal-builtins/DESIGN.md),
  [worked example](iterations/21-internal-builtins/EXAMPLE.md) and
  [conditional handoff](iterations/21-internal-builtins/HANDOFF.md).
  Agreed standard argument-map-node calls/internal NULL bindings; recommended shipped Python
  built-in module/ordinary node profiles/exact retained v1-v2 handlers/narrow native dml: reference
  support+external namespace guards/THREE-Q-TWO-local story are candidate mechanics, not as-built.
  See [plan review](discussion.md#iteration21-plan-review) and
  [preparation](discussion.md#iteration21-candidate-preparation). Separate GO remains required;
  no worker/source/build/install/story/CI/native investigation/publication restart. DML clean7e9bf13,
  completed20 stopped/GHA disabled/VP-001 OPEN UNKNOWN preserved. Older statuses below historical.

- **Next direction agreed; no implementation GO:** URI-addressed built-in funcs with
  internal versioned implementations. The user's binding model uses NULL adapter/interpreter/
  timeout and a versioned `dml://source/builtin/...` URI; see
  [discussion summary](discussion.md#next-iteration-built-in-funcs-and-internal-versioned-bindings).
  Agreed [standard invocation](discussion.md#standard-func-invocation-argument-map-node-to-result-node):
  form an argument-map node; every func consumes it and returns a node, with value access separate
  from provenance. Exact profiles/APIs/initial function set and acceptance plan remain open; no prepared handoff
  or implementation restart. Iteration20 remains the completed as-built delivery below.

- **Iteration 20 COMPLETE AND STOPPED**, independently accepted and normally published
  **`7e9bf13`**: [results](iterations/20-recorded-argument-maps/RESULTS.md),
  [review](iterations/20-recorded-argument-maps/REVIEW.md),
  [coordination](iterations/20-recorded-argument-maps/COORDINATION.md) and implemented
  [informative prototype](../dml/docs/recorded-argument-maps.md). Recorded map operations preserve
  actual sources; funcs receive datum-only arguments/access; reuse matches func+MAP datum and
  separates new requested provenance from old executed provenance. Independent37 focused/2424
  installed NONEXECUTING, worker full2798/sole actual FIVE-Q-FOUR-local-SIX-getter story;491 retained
  rows/four reaped children. Exact15/current/committed/live remote verified. Development GHA
  intentionally disabled/NOT RUN, not pass; native investigation PAUSED/VP-001 OPEN UNKNOWN and
  original failures/qualifications retained. The user has
  [reviewed and accepted this delivery](discussion.md#iteration20-user-review).
  No restart/later turn/design checkpoint publication.
  Older statuses below historical where superseded.

- **Iteration 20 GO; existing window-2 agent in a NEW Pi session:** reviewed
  [design](iterations/20-recorded-argument-maps/DESIGN.md),
  [example](iterations/20-recorded-argument-maps/EXAMPLE.md) and
  [handoff](iterations/20-recorded-argument-maps/HANDOFF.md) authorized for bounded implementation,
  coordinator monitoring/independent review/feedback, then accepted focused worker commit/normal
  push. See [coordination](iterations/20-recorded-argument-maps/COORDINATION.md). BOTH builds/source
  worker-owned until targeted freeze/release; FIVE-Q/FOUR synchronous LOCAL/SIX getter story and
  proportionate validation. Development GHA remains disabled (not re-enabled by GO); native
  investigation PAUSED/VP-001 OPEN UNKNOWN preserved. No extra worker/cloud/global/later turn/
  design checkpoint publication. Outcomes pending; older statuses below historical where superseded.

- **Iteration 20 bounded replacement plan reviewed; implementation GO pending:**
  [design](iterations/20-recorded-argument-maps/DESIGN.md),
  [worked example](iterations/20-recorded-argument-maps/EXAMPLE.md) and
  [conditional handoff](iterations/20-recorded-argument-maps/HANDOFF.md).
  Recorded map_empty/map_insert/map_get preserve construction provenance; funcs receive map
  datums and datum-only access; caching matches func+argument-map datum. Recommended ordinary
  source/input/return/trace/Md/Dd/five-Q-four-local mechanics are a reviewed candidate plan,
  not as-built behavior. Separate implementation GO remains required. Prior
  [projection-policy plan](iterations/20-result-based-input-reuse/HANDOFF.md) remains deferred.
  No worker/source/build/story/publication restart; GHA disabled/native investigation paused.
  See [plan review](discussion.md#iteration20-replacement-plan-review) and
  [preparation](discussion.md#iteration20-replacement-candidate-preparation).

- **Latest user decision:** development GHA disabled for the design spiral. GitHub CI workflow
  is verified `disabled_manually`; release workflow remains active. Native investigation is
  PAUSED; private harness incomplete/unexecuted, both builds/source coordinator-owned. No new
  source/build/test/publication permission; raw CI outcomes/UNKNOWN remain. See
  [decision and verified state](iterations/19-intent-scoped-reuse/GHA-DISABLED.md).
  Older statuses below remain historical, not current authorization.

- Iteration 19 [candidate design](iterations/19-intent-scoped-reuse/DESIGN.md),
  [worked example](iterations/19-intent-scoped-reuse/EXAMPLE.md) and
  [conditional handoff](iterations/19-intent-scoped-reuse/HANDOFF.md): intent-scoped reuse across
  different requested/producing bindings, exact full inputs and explicit one-entry removal.
  **GO; existing window-2 agent restarted in a verified NEW Pi session**. The bounded plan is
  approved for implementation; coordinator monitoring/independent review/feedback precede accepted
  worker commit/normal push/exact-SHA CI/fixes. See
  [coordination](iterations/19-intent-scoped-reuse/COORDINATION.md). BOTH builds worker-owned until
  targeted freeze/release; SIX-Q/FOUR synchronous LOCAL-attempt story and proportionate validation.
  VP-001 OPEN UNKNOWN/no standing waiver; no extra worker/cloud/global/release/package/later turn/
  design publication. No acceptance/as-built outcome yet. Earlier reviewed pending-GO state follows:
  **Bounded plan reviewed; implementation GO pending**. Exact spellings remain refinable;
  review is not implementation/delegation/publication permission. Persistent result
  restrictions/deprecation gates deferred. NEW Mi/Di/public S+ownQ/direct ordinary W/six-Q-four-
  local story are candidate mechanics, not as-built/schema approval. DML3b2b370 clean/completed18
  stopped; no worker/source/build/story/CI/publication restart. See
  [preparation](discussion.md#iteration19-candidate-preparation).

- Iteration 18 [candidate design](iterations/18-multi-input-reuse/DESIGN.md),
  [worked example](iterations/18-multi-input-reuse/EXAMPLE.md) and
  [conditional handoff](iterations/18-multi-input-reuse/HANDOFF.md): versioned selections for
  multiple exact intent URI/full binding/full input tuples, own new Q/no T on reuse, separate
  fresh/one-key adoption and preserved other keys/branches. **COMPLETE AND STOPPED through
  `3b2b370`; all six final-SHA CI41182904065 jobs successful**, attempt1. Independent38/
  installed1179 NONEXECUTING pass; reviewed worker163/sole full2489/actual SEVEN-Q/THREE-local
  story/25phases. Final six shared XML/primary/digests/clean source+remote verified, MI-001
  resolved with hosted Windows evidence; reaped local-only evidence retained. Original failed
  probes/private-driver qualifications/coordinator oracle corrections/VP-001 OPEN UNKNOWN
  retained, pass not older diagnosis. See [results](iterations/18-multi-input-reuse/RESULTS.md),
  [review](iterations/18-multi-input-reuse/REVIEW.md) and
  [coordination](iterations/18-multi-input-reuse/COORDINATION.md).
  No restart/later turn/design checkpoint publication. **The user reviewed the completed delivery**;
  work remains stopped. Earlier acceptance state is historical:
  independently ACCEPTED exact frozen ELEVEN; focused publication/final-SHA CI pending. Independent38 focused/installed1179
  NONEXECUTING pass; reviewed worker sole full2489/focused163/actual SEVEN-Q/THREE-local story.
  BOTH builds/source/evidence returned to worker for accepted publication/actualCI/fresh triage.
  See [review](iterations/18-multi-input-reuse/REVIEW.md); original failed probes/private-driver
  qualifications/coordinator oracle corrections retained, VP-001 OPEN UNKNOWN/no waiver.
  Earlier GO: assigned to existing window-2
  agent in a verified NEW Pi session. Bounded plan approved for implementation, exact spellings
  refinable; not as-built/acceptance yet. Coordinator monitors/independently reviews/feedback,
  then accepted worker focused commit/normal push/exact-SHA CI/fixes. See
  [coordination](iterations/18-multi-input-reuse/COORDINATION.md) and
  [authorization](discussion.md#iteration-18-implementation-and-publication-authorization).
  BOTH builds worker-owned until changed-surface/HEAD freeze/release; SEVEN-Q/THREE-local story
  and proportionate validation. VP-001 OPEN/UNKNOWN/no standing waiver. No extra agent/cloud/
  global/release/package/later turn/design checkpoint publication.

- Iteration 17 [candidate design](iterations/17-implementation-supersession/DESIGN.md),
  [worked example](iterations/17-implementation-supersession/EXAMPLE.md) and
  [handoff](iterations/17-implementation-supersession/HANDOFF.md): advisory A→B
  supersession with correctness-fix versus operational-replacement reason/evidence, explicit
  successor default promotion, preserved predecessor/old branches, pinned historical versus
  explicitly selected knowledge views. **COMPLETE AND STOPPED through `9f182be`; all six
  final-SHA CI jobs successful**, attempt1. **User accepted the completed delivery**;
  work remains stopped, no next turn or checkpoint publication authorized.
  Independent37 focused/installed712 NONEXECUTING
  pass, reviewed worker sole full2364/unchanged gates and actual FOUR-Q/TWO-local-attempt
  story. SS-001 resolved, original failed probes/qualified original controller/corrected
  nonexecuting readers retained; VP-001 OPEN/UNKNOWN, pass not earlier diagnosis. Local
  children reaped/evidence retained, no external fixture. See
  [results](iterations/17-implementation-supersession/RESULTS.md),
  [review](iterations/17-implementation-supersession/REVIEW.md) and
  [coordination](iterations/17-implementation-supersession/COORDINATION.md).
  No restart/later turn/release/package/design checkpoint publication; earlier planning/
  GO/publication-pending statements below are historical.

- Iteration 16 [candidate design](iterations/16-versioned-implementation-selection/DESIGN.md),
  [worked example](iterations/16-versioned-implementation-selection/EXAMPLE.md) and
  [conditional handoff](iterations/16-versioned-implementation-selection/HANDOFF.md): one intent,
  two captured implementation bindings, versioned default/explicit override before reuse policy,
  own Q/exact full matching/per-binding known selection slots/no cross-implementation reuse.
  **COMPLETE AND STOPPED through `e008932`; all six final-SHA CI jobs successful**.
  The user [reviewed and accepted the completed delivery](discussion.md#iteration-16-user-acceptance).
  No restart, later turn or design checkpoint publication is authorized.
  Worker finalized RESULTS and explicitly STOPPED ALL activity. Initial14 `7de65ae`
  plus approved2 runner migration; finalCI41123236764 attempt1/sixXML+primary counts/digests
  independently verified, actualMac15arm64 execution proved. Independent32/54/24 pass;
  worker correctedfull2263/unchanged gates and real3-job/9-phase+8readers reviewed.
  Owned fixtures archived/identity-retired, images/evidence retained. Original failed probes,
  reconstructed provenance/false migration receipt correction/initialbrownoutCANCELLED and
  VP-001 OPEN UNKNOWN preserved. See [results](iterations/16-versioned-implementation-selection/RESULTS.md)
  and [review](iterations/16-versioned-implementation-selection/REVIEW.md).
  Earlier publication gate below is historical.
  **Implemented, independently accepted and published through `e008932`; final-SHA CI pending**.
  Initial14 `7de65ae` plus separately approved2-file macOSarm runner migration; all6 actual
  [CI41123236764](https://github.com/micha/dml/actions/runs/41123236764) jobs in progress.
  OriginalCI41120062048 rawCANCELLED/fivepasses/Macarm scheduledbrownout/no test preserved.
  No final all-green/exception claim; owned fixtures archived/identity-retired.
  Earlier independent acceptance:
  Independent32 focused checks and separately authored installed54 nonexecuting checks pass;
  reviewed worker corrected full2263/unweakened gates and actual3-job/9-phase+8reader evidence.
  Exact14 source/builds/stopped fixture returned for focused worker commit/normal push and
  fresh CI triage. See [review](iterations/16-versioned-implementation-selection/REVIEW.md).
  Original AST coverage failure/controller reconstruction/other qualifications preserved;
  VP-001 OPEN/UNKNOWN/not a standing waiver. No final publication/CI success claim.
  Earlier GO authorization: bounded design/example/handoff approved for implementation by the existing window-2
  agent in a NEW Pi session, coordinator monitoring/independent review/feedback, then accepted
  worker commit/normal push/exact-SHA CI fixes. See
  [coordination](iterations/16-versioned-implementation-selection/COORDINATION.md) and
  [authorization](discussion.md#iteration-16-implementation-and-publication-authorization).
  Exact engineering spellings remain refinable; no as-built/acceptance claim yet. BOTH builds
  worker-owned until changed-surface freeze/release. Proportionate validation applies; VP-001
  remains OPEN/UNKNOWN, no standing waiver. No extra worker/cloud/global/release/package/later
  turn or design checkpoint publication.

- **Validation-policy maintenance complete and stopped at `4a053340`, accepted with
  [exception VP-001](maintenance/validation-policy/EXCEPTION-VP-001.md)**:
  [results](maintenance/validation-policy/RESULTS.md), [review](maintenance/validation-policy/REVIEW.md),
  [coordination](maintenance/validation-policy/COORDINATION.md) and the published
  [owning development policy](../dml/docs/validation-policy.md). Focused behavior/concrete
  acceptance primary; one worker full-v and risk-based independent checks, retained platform
  matrix with per-job XML and explicit evidence/risk/follow-up exceptions. Raw
  [CI41098299553](https://github.com/micha/dml/actions/runs/41098299553) FAILED, five jobs successful/
  one old Macarm async-story ENOENT; root cause UNKNOWN, not green/fixed or same Windows cause.
  All15 new report cases pass all6, six report artifacts match primary counts/digests. VP-001
  coordinator-owned OPEN follow-up/revisit, not standing waiver. No worker/source/build/fixture/
  CI restart/runtime feature/extra agent/cloud/global/release/package/design publication.
  [Plan](maintenance/validation-policy/PLAN.md)/[handoff](maintenance/validation-policy/HANDOFF.md)
  preserve authorization chronology; completed GO is not investigation permission.

- Iteration 15 [candidate design](iterations/15-intent-reuse-defaults/DESIGN.md),
  [worked example](iterations/15-intent-reuse-defaults/EXAMPLE.md) and
  [conditional handoff](iterations/15-intent-reuse-defaults/HANDOFF.md): versioned intent-level
  reuse/execute defaults, explicit request overrides, recorded reasons and branch-local defaults.
  **Implemented, independently accepted, published and STOPPED through `664a870`**.
  The user has [reviewed and accepted this delivery](discussion.md#iteration-15-user-acceptance);
  no restart, design checkpoint or next turn is authorized.
  All six final [exact-SHA CI41090059076](https://github.com/micha/dml/actions/runs/41090059076)
  jobs successful, attempt1. Independent full2060/sevenC/4301/unchanged gates, separate actual
  installed780-check four-job/twelve-phase probe and correction233postfix/nine copied-policy
  parser-bootstrap clients pass; worker final correction2067/unweakened gates.
  See [results](iterations/15-intent-reuse-defaults/RESULTS.md),
  [review](iterations/15-intent-reuse-defaults/REVIEW.md),
  [coordination](iterations/15-intent-reuse-defaults/COORDINATION.md),
  [delivery](discussion.md#iteration-15-delivery-final-publication-and-stop) and the implemented
  [example convention](../dml/docs/intent-reuse-defaults.md).
  Ordinary Idef/D/public validation/decision parent, ownQ either path/noT-job on reuse,
  exact full matching/no automatic adoption/branch-local defaults; no native entity/private
  role codec/public policy framework/cache discovery/facets/resources/scheduler/cloud.
  Initial16 plus reviewed3 controller/test/parser rationale files published normally, ALL248
  source/remote/primaryCI/archived-owned-retirement verified. Exact urllib package/parser pure
  parsing allowed; transport/spawn blockers retained. Initial Windows oldcaller ENOENT cause
  UNKNOWN despite final pass, distinct Unix19 bootstrap diagnosis/older UNKNOWN retained.
  Worker explicitly STOPPED ALL activity. Images/evidence retained; no completed-GO restart/
  extra worker/global tooling/release/package/later turn/design checkpoint commit/push.

- Iteration 14 [candidate design](iterations/14-versioned-reuse-selection/DESIGN.md),
  [worked example](iterations/14-versioned-reuse-selection/EXAMPLE.md) and
  [conditional handoff](iterations/14-versioned-reuse-selection/HANDOFF.md): versioned reuse
  selection, explicit selected reuse/fresh control/adoption and two branch-local choices.
  **Implemented, independently accepted, published and STOPPED through `8393a82`**.
  The user has reviewed this completed delivery; no next turn is authorized.
  All six final [exact-SHA CI41025016866](https://github.com/micha/dml/actions/runs/41025016866)
  jobs successful, attempt1. Worker final1867/sevenC/4030/unchanged gates and coordinator corrected
  independent1863 full/242postfix/separate actual installed773-check three-job/branch probe pass.
  See [results](iterations/14-versioned-reuse-selection/RESULTS.md),
  [review](iterations/14-versioned-reuse-selection/REVIEW.md),
  [coordination](iterations/14-versioned-reuse-selection/COORDINATION.md) and the implemented
  [example convention](../dml/docs/versioned-reuse-selection.md).
  Exact full matching retained; ordinary S/V/public revalidation, no native entity/default/cache
  discovery/facets/framework. Explicit occurrence-based adoption preserves old snapshots/choices.
  Source/remote/primaryCI/fixture retirement verified; original failures/Windows UNKNOWN and
  initialMac10cap/UNKNOWNslowdown/WSLprimary/latentCRLF distinction retained. OnlyMacx86 outer20cap
  separately user-approved; all runtime/test/threshold/skip unchanged. No completed-GO restart/
  design commit/push/extra worker/cloud/global/release/package/later turn. Images/evidence retained.

- Iteration 13 [candidate design](iterations/13-explicit-attempt-reuse/DESIGN.md),
  [worked example](iterations/13-explicit-attempt-reuse/EXAMPLE.md) and
  [conditional handoff](iterations/13-explicit-attempt-reuse/HANDOFF.md): new request explicitly
  reuses old selected successful attempt/result, no new attempt/job, then separate fresh control.
  **Implemented, independently accepted, published and STOPPED through `b296fdb`**.
  All six final [exact-SHA CI41006689070](https://github.com/micha/dml/actions/runs/41006689070)
  jobs successful, attempt1. Worker final1706/seven C/3841 and coordinator1692 full/126 correction/
  separate installed466-check three-job gates pass. See
  [results](iterations/13-explicit-attempt-reuse/RESULTS.md),
  [review](iterations/13-explicit-attempt-reuse/REVIEW.md) and
  [coordination](iterations/13-explicit-attempt-reuse/COORDINATION.md).
  Initial matching includes intent/binding/full inputs/producer witness; no automatic cache/facets.

- Iteration 12 [reviewed design](iterations/12-composed-recorded-steps/DESIGN.md),
  [worked example](iterations/12-composed-recorded-steps/EXAMPLE.md) and
  [conditional handoff](iterations/12-composed-recorded-steps/HANDOFF.md): compose two recorded
  steps, preserving result sub-DAG and selected producer occurrence, then ordinary summary.
  Direction agreed; bounded plan/handoff **reviewed**, exact engineering spellings refinable.
  **Implemented, independently accepted, published and STOPPED through `66311fc`**;
  all six final exact-SHA CI40954598093 jobs successful, attempt1. Coordinator full1647/
  3783/seven C and separate actual installed293-check chain pass. See
  [results](iterations/12-composed-recorded-steps/RESULTS.md),
  [review](iterations/12-composed-recorded-steps/REVIEW.md) and
  [coordination](iterations/12-composed-recorded-steps/COORDINATION.md).

- Iteration 11 [approved design](iterations/11-floci-batch-execution/DESIGN.md),
  [worked example](iterations/11-floci-batch-execution/EXAMPLE.md) and
  [conditional handoff](iterations/11-floci-batch-execution/HANDOFF.md): actual installed DML
  in one Floci Batch job, fresh bounded clients and immutable S3 P/U/F history exchange.
  **Implemented, independently accepted, published and stopped through `640cabb`**;
  all six final exact-SHA CI jobs successful. See
  [review](iterations/11-floci-batch-execution/REVIEW.md),
  [results](iterations/11-floci-batch-execution/RESULTS.md) and
  [coordination](iterations/11-floci-batch-execution/COORDINATION.md).
  Original Windows old-reader cause remains unknown; final pass is not its diagnosis.

- Iteration 10 [reviewed design](iterations/10-asynchronous-ssh-execution/DESIGN.md),
  [worked example](iterations/10-asynchronous-ssh-execution/EXAMPLE.md) and
  [conditional handoff](iterations/10-asynchronous-ssh-execution/HANDOFF.md): nonwaiting
  foreground SSH launch and bounded validated P/U/F observation, saved identity separate
  from live execution-client ownership. **Implemented, independently accepted and published
  through `099d156`**, all six final exact-SHA CI jobs successful. Bounded turn complete/stopped;
  no detached-lifetime promise. See [results](iterations/10-asynchronous-ssh-execution/RESULTS.md),
  [review](iterations/10-asynchronous-ssh-execution/REVIEW.md) and
  [coordination](iterations/10-asynchronous-ssh-execution/COORDINATION.md).

- Iteration 9 [delivery](iterations/09-ssh-container-execution/RESULTS.md) and
  [independent review](iterations/09-ssh-container-execution/REVIEW.md): synchronous SSH
  stage/execute/fetch is implemented, independently accepted and published through
  **`29ed39b`**; all six final exact-SHA CI jobs pass after a Windows test-harness correction.
  Docker is local fixture support with approved loopback-only host networking/no shared
  mounts. Exact-Q atomic receive remains authoritative. The bounded turn is complete and
  stopped. [Design](iterations/09-ssh-container-execution/DESIGN.md),
  [example](iterations/09-ssh-container-execution/EXAMPLE.md) and
  [handoff](iterations/09-ssh-container-execution/HANDOFF.md) preserve plan/provenance,
  not permission to restart. [As-built contract](../dml/docs/spec-next/ssh-execution.md).

- Iteration 8 [delivery](iterations/08-caller-recorded-requests/RESULTS.md) and
  [coordinator review](iterations/08-caller-recorded-requests/REVIEW.md): caller-recorded Q,
  imported-Q first attempt and exact pinned request validation are implemented,
  independently accepted and published through `865bb79`; all six final exact-SHA CI jobs
  pass after a reviewed test-only Windows portability fix. A records Q before launch;
  B creates only T. Existing A heads and request refs stay unchanged on return. This
  bounded turn is complete and stopped. The [design](iterations/08-caller-recorded-requests/DESIGN.md),
  [example](iterations/08-caller-recorded-requests/EXAMPLE.md) and
  [handoff](iterations/08-caller-recorded-requests/HANDOFF.md) preserve the approved plan,
  not permission to restart. The [as-built contract](../dml/docs/spec-next/caller-requests.md)
  owns actual behavior.

- Iteration 7 [delivery](iterations/07-asynchronous-local-execution/RESULTS.md) and
  [coordinator review](iterations/07-asynchronous-local-execution/REVIEW.md): asynchronous
  same-machine start/observe/receive and immutable validated P/U/F snapshots are implemented,
  independently accepted and published as `a8d6463`; all six final exact-SHA CI jobs pass
  on the first run. Saved handle/live process ownership, unknown versus failure and
  publication versus completion remain distinct; existing A heads stay unchanged.
  The bounded turn is complete and stopped. [Design](iterations/07-asynchronous-local-execution/DESIGN.md),
  [example](iterations/07-asynchronous-local-execution/EXAMPLE.md) and
  [handoff](iterations/07-asynchronous-local-execution/HANDOFF.md) preserve the approved
  plan/provenance, not permission for another turn. The
  [as-built contract](../dml/docs/spec-next/asynchronous-execution.md) owns actual behavior.

- Iteration 6 [delivery](iterations/06-local-repository-execution/RESULTS.md) and
  [coordinator review](iterations/06-local-repository-execution/REVIEW.md): pinned
  A → B → A execution is implemented and independently accepted, published as
  `a0aa05d`; all six final exact-SHA CI jobs pass on the first run. The bounded turn
  is complete and stopped. Existing A heads stay unchanged; returned selected
  history is validated before atomic publication under an explicit ref.
  The [design](iterations/06-local-repository-execution/DESIGN.md),
  [example](iterations/06-local-repository-execution/EXAMPLE.md) and
  [handoff](iterations/06-local-repository-execution/HANDOFF.md) preserve the approved
  plan, not permission for another feature. The
  [as-built contract](../dml/docs/spec-next/repository-execution.md) owns actual behavior.
- Iteration 5 [delivery](iterations/05-pinned-snapshot-transfer/RESULTS.md) and
  [coordinator review](iterations/05-pinned-snapshot-transfer/REVIEW.md): pinned
  commit/full-history transfer between initialized local repositories is implemented
  and independently accepted, published as `0ec769b`; all six final exact-SHA CI
  jobs pass. The bounded turn is complete and stopped.
  The [design](iterations/05-pinned-snapshot-transfer/DESIGN.md),
  [example](iterations/05-pinned-snapshot-transfer/EXAMPLE.md) and
  [handoff](iterations/05-pinned-snapshot-transfer/HANDOFF.md) preserve the bounded
  approved plan, not additional feature authorization.

- Iteration 4 [delivery](iterations/04-local-recorded-execution/RESULTS.md) and
  [coordinator review](iterations/04-local-recorded-execution/REVIEW.md): one locally
  executed, recorded Python step, published through `d498a6c`; all six final
  exact-SHA CI jobs pass. Implementation/review/publication are complete and stopped.
- Iteration 4 [design](iterations/04-local-recorded-execution/DESIGN.md),
  [worked example](iterations/04-local-recorded-execution/EXAMPLE.md) and
  [handoff](iterations/04-local-recorded-execution/HANDOFF.md) preserve the bounded
  plan and its provenance, not permission to restart or add later features.
- [Iteration 3 delivery](iterations/03-composable-dags/RESULTS.md) and
  [coordinator review](iterations/03-composable-dags/REVIEW.md): named/composable DAGs,
  scoped lookup and nested CLI inspection, published as `9b8fb71`; all six exact-SHA
  CI jobs successful. Implementation and review are complete; work is stopped.
- Iteration 3 [worked example](iterations/03-composable-dags/EXAMPLE.md),
  [design](iterations/03-composable-dags/DESIGN.md) and
  [handoff](iterations/03-composable-dags/HANDOFF.md) preserve the approved plan and
  bounded authorization, not permission to restart or add later features.
- [Iteration 2 delivery](iterations/02-repository-usability/RESULTS.md): low-level
  linked Python repository API and inspection-only native CLI, worker/coordinator
  default checks and local install validation pass; published through `e253249`
  with all six exact-SHA CI jobs successful. See the
  [coordinator review](iterations/02-repository-usability/REVIEW.md).
- [Iteration 2 design](iterations/02-repository-usability/DESIGN.md) and
  [handoff](iterations/02-repository-usability/HANDOFF.md): agreed scope and candidate
  choices for that authorized bounded turn, not additional feature approval.
- [Iteration 1 delivery notes](iterations/01-minimum-viable-repository/RESULTS.md):
  implemented minimum viable repository and bounded review follow-up; default
  validation passes with documented no-value exclusions; stopped for review.
- [Iteration 1 handoff](iterations/01-minimum-viable-repository/HANDOFF.md): detailed
  plan and scope for that authorized turn.
- [Glossary](../dml/docs/spec-next/glossary.md): shared vocabulary for maintained documentation and
  best-effort use in design discussion; provisional terms are marked.
- [New as-built specification](../dml/docs/spec-next/README.md): implemented behavior
  in the evolving new direction.
- [Observer experiment handoff](observer-study/HANDOFF.md): proposed stages,
  evidence corpus, acceptance criteria and delegation; implementation not started.
- [Discussion checkpoint](discussion.md): goals, conceptual agreements,
  tentative directions, corrections, and open questions.
- [Resume point](discussion.md#resume-point): where to continue the conversation.
- [Feasibility study](feasibility/README.md): experiments, counterexamples, and
  [candidate iteration results](feasibility/ITERATION-RESULTS.md).
- [Focused final audit](feasibility/final-review/report.md): independent checks
  of the latest fixes and remaining flaws.
- [Agent guide](AGENTS.md): scope and note-maintenance rules.

The checkpoint is chronological. Later clarifications can supersede earlier
proposals; it is not a finalized specification or implementation approval.

## Current focus

User-requested **checkpoint and retrospective through Iteration24**. Read
[what we have learned](checkpoints/24-lessons.md), then discuss remaining questions before selecting
another turn. Local design commit only; DML unchanged/clean59b3830/completed24 stopped/GHA disabled/
native19 PAUSED/VP-001 OPEN UNKNOWN. No new implementation or push authorization. Older focus
stages below preserve their historical states.

Iteration24 **COMPLETE AND STOPPED through59b38303fe2f4c89d6fce3b01933f7260eb28320**.
See [final delivery](discussion.md#iteration24-final-delivery-and-stop),
[review](iterations/24-captured-ordinary-calls/REVIEW.md) and
[results](iterations/24-captured-ordinary-calls/RESULTS.md). Accepted exact cumulative33/normalpush/
independent2052+3/current-clean-live remote/workflows/workerSTOP/BOTH return verified. Raw originalfull1/
combinedresumed0/EOF-source/oracle/audit/UNKNOWN qualifications preserved. No restart/later turn/design
checkpoint; GHA disabled/native19PAUSED/VP001OPENUNKNOWN. Older focus stages historical.

Iteration24 **GO: existing window2 assigned in a verified NEW session**. Read
[authorization](discussion.md#iteration24-implementation-and-publication-authorization) and
[coordination](iterations/24-captured-ordinary-calls/COORDINATION.md). Pre-edit source-sharing B ONLY
accepted; FINAL readiness STATIC accepted/ONE bounded installed story+successful-stage SAME readers/
final unchanged full-v authorized historically; FIRST activation RAWcontrollerfail BEFORE leaflaunch,
SAME triage0 confirms partialUNKNOWN/zerochildren. ONLY controllerfix+metadataregression GO; fresh
readiness/explicitactivation required before story/full. Originals retained; independent acceptance/
publication pending. Coordinator monitors/reviews/feedback before accepted focused worker
NORMAL commit/push. BOTH builds/source worker-owned; sole10Q8T5LOCAL14getter/one final full-v/SAME
NONEXECUTING review. GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN; no extra worker/later turn/design
checkpoint. Outcomes pending; older focus stages historical where superseded.

Iteration24 **captured-ordinary-call candidates prepared for review; separate GO pending**. Read
[agreement/preparation](discussion.md#iteration24-agreed-direction-and-candidate-preparation) and
ALL THREE [documents](iterations/24-captured-ordinary-calls/HANDOFF.md). Direction agreed; adapter/
profiles/session bridge/key/story are assistant mechanics requiring review, not as-built behavior.
DML clean965cec4/completed23 stopped/BOTH coordinator-owned/GHA disabled/native19 PAUSED/VP001 OPEN
UNKNOWN. No worker/source/build/test/story/reader/CI/investigation/commit/push restart or design checkpoint.
Review candidates, then separate GO. Older focus stages below historical.

Iteration23 **COMPLETE AND STOPPED through965cec450356e5f776b68bc311fa4d7eaf690519**. Read
[delivery](discussion.md#iteration23-final-publication-and-stop),
[review](iterations/23-closure-bound-dependencies/REVIEW.md) and
[results](iterations/23-closure-bound-dependencies/RESULTS.md). Independently accepted exact13/parent/
clean current+committed+frozen/live remote/workflows; worker finalSTOP/BOTH returned. Independent44/
1066 SAME464 NONEXECUTING distinct from worker78+9/completefull3108/sole6Q4LOCAL8getter. Original
incompleteRAWtoolTIMEOUT/groupUNKNOWN/63bytespossiblylost/EOF+mutant qualifiers preserved; GHA disabled/
native19 PAUSED/VP001 OPEN UNKNOWN/no older diagnosis/new turn/design checkpoint. Older focus stages
below historical where superseded.

Iteration23 **GO: existing window2 assigned in a verified NEW session**. Read
[authorization](discussion.md#iteration23-implementation-and-publication-authorization) and
[coordination](iterations/23-closure-bound-dependencies/COORDINATION.md). Monitor/independently
review/feedback before accepted focused worker normal publication. BOTH builds/source worker-owned;
6Q4LOCAL8getter/one full-v/SAME nonexecuting review. GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN;
no extra worker/later turn/design checkpoint. Outcomes pending; older focus states historical.

Iteration23 **candidate DESIGN/EXAMPLE/HANDOFF prepared for review; implementation GO pending**.
Read [preparation](discussion.md#iteration23-candidate-preparation) and all three documents above.
Closure-bound dependencies of any kind are agreed direction; fixed getter+constant capture/scaled-sum/
ordinary descriptors/capture-aware key/SIX-Q-FOUR-local-EIGHT-getter/nested-call deferral are assistant
candidates. No DML/source/worker/build/story/reader/CI/investigation/publication restart. Completed22
stays stopped/GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN/BOTH coordinator-owned. Review then
separate GO; no design checkpoint requested. Older focus blocks below historical where superseded.

Iteration22 **COMPLETE AND STOPPED through `a57125cdf735310f2330226ce6272b3a67e53f62`**.
See [delivery](discussion.md#iteration22-final-publication-and-stop),
[results](iterations/22-composed-node-calls/RESULTS.md) and
[review](iterations/22-composed-node-calls/REVIEW.md). Exact13/current+committed+accepted/parent/clean/
live originmaster/workflows independently verified; worker finalSTOP/BOTH returned. Independent41/
1607 SAME641 NONEXECUTING distinct from worker87+5/full3021/actual8Q6T10getter. GHA disabled/NOTRUN/
native19 PAUSED/VP001 OPEN UNKNOWN/failures+qualifications retained. No newturn/restart/design
checkpoint permission; older focus blocks historical where superseded.

Iteration22 **INDEPENDENTLY ACCEPTED exact13; focused worker publication/STOP pending**.
Read [acceptance](discussion.md#iteration22-independent-acceptance-and-publication-gate) and
[review](iterations/22-composed-node-calls/REVIEW.md). Independent41/1607 installed SAME641 NONEXECUTING
versus reviewed worker87+5/full3021/actual8Q6T10getter. Worker normal publication/exactidentities/
workflowGET/RESULTS/STOP only. GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN; no extra computation/
laterturn/design checkpoint. Original errors+qualifications retained; older states historical.

Iteration22 **GO: bounded implementation delegated to existing window2 in a verified NEW session**.
See [authorization](discussion.md#iteration22-implementation-and-publication-authorization) and
[coordination](iterations/22-composed-node-calls/COORDINATION.md). Monitor/independently review/feedback
before accepted focused worker normal commit/push. BOTH builds/source worker-owned until targeted
freeze/release; isolated8Q6T10getter/one final full-v/SAME-history NONEXECUTING review. GHA disabled/
native19 PAUSED/VP001 OPEN UNKNOWN; no extra worker/later turn/design checkpoint. Outcomes pending;
older focus blocks historical where superseded.

Iteration22 **candidate DESIGN/EXAMPLE/HANDOFF prepared for review; implementation GO pending**.
See [preparation/corrected existing support](discussion.md#iteration22-composed-node-calls-candidate-preparation)
and all three documents linked above. Common node calls/public successful-producer composition/value
reuse; swapped add inputs differ upstream but converge downstream. Recommended ordinary C/decision/
reader/8Q6T10getters not as-built or exact engineering approval. DML clean a523b0b/completed21 stopped;
GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN/BOTH coordinator-owned. No implementation/worker/
build/story/CI/investigation/commit/push restart or checkpoint. Review then separate GO; prior focus
states below historical where superseded.

Iteration21 **COMPLETE AND STOPPED through `a523b0bfc8c4cc9f96a36b7b62138d9645b3eab3`**.
See [delivery](discussion.md#iteration21-final-publication-and-stop),
[results](iterations/21-internal-builtins/RESULTS.md) and
[review](iterations/21-internal-builtins/REVIEW.md). Independently accepted/published/exact29 clean
source+remote verified; worker finalSTOP/BOTH returned. GHA disabled/NOTRUN, native19 PAUSED/
VP001 OPEN UNKNOWN and original/final runtime qualifications preserved. No new turn/checkpoint/
restart permission. Older focus blocks below historical where superseded.

Iteration21 **independently ACCEPTED exact29; accepted worker publication/final STOP pending**.
See [review](iterations/21-internal-builtins/REVIEW.md) and
[acceptance](discussion.md#iteration21-independent-acceptance-and-publication-gate).
Independent48/FINAL-installed1424 NONEXECUTING distinct from workerfull2929/original3Q2T16/SAME467/
final-nojobNaN95. No duplicate computation/full; GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN.
Older focus blocks below historical where superseded.

Iteration21 **GO: bounded implementation delegated to existing window2 in a NEW session**.
See [authorization](discussion.md#iteration21-implementation-and-publication-authorization) and
[coordination](iterations/21-internal-builtins/COORDINATION.md). Coordinator monitors and independently
reviews before accepted focused publication. GHA disabled/native investigation PAUSED/VP-001 OPEN
UNKNOWN; BOTH builds/source worker-owned until targeted freeze/release. Outcomes pending;
older focus blocks below historical where superseded.

Iteration21 **bounded DESIGN/EXAMPLE/HANDOFF reviewed; implementation GO pending**.
See [review checkpoint](discussion.md#iteration21-plan-review). Review does not authorize a worker/
source/build/install/story/CI restart or publication; exact engineering spellings remain refinable.
Read [preparation](discussion.md#iteration21-candidate-preparation) and all three documents above.
Agreed node calling/NULL builtin binding direction, recommended bounded installed/URI/profile/story
mechanics remain distinguishable; no implementation/as-built claim or restart. GHA disabled/
native investigation PAUSED/VP-001 OPEN UNKNOWN; completed20 remains latest implemented work.
Older focus blocks below historical where superseded.

Discuss the agreed [built-in func/internal binding direction](discussion.md#next-iteration-built-in-funcs-and-internal-versioned-bindings).
NULL adapter/source URI identifies internal versioned implementation; exact engineering plan
still open. No implementation GO or restart; GHA disabled/native investigation PAUSED/VP-001 OPEN
UNKNOWN remain. Completed20 below is latest implemented work; older focus states are historical.

Iteration20 **COMPLETE AND STOPPED through `7e9bf133d5d175a492fb1e9d651e91a476358604`**.
See [delivery](discussion.md#iteration20-delivery-publication-and-stop),
[results](iterations/20-recorded-argument-maps/RESULTS.md) and
[review](iterations/20-recorded-argument-maps/REVIEW.md). Bounded local capability independently
accepted/published; GHA disabled/NOT RUN/notpass/native investigation PAUSED/VP-001 OPEN UNKNOWN.
Worker STOP ALL/BOTH source-builds coordinator-owned; no next turn/checkpoint/restart authorized.
Earlier focus blocks below historical where superseded.

Iteration20 **GO: reviewed replacement implementation delegated to existing window2/new session**.
See [coordination](iterations/20-recorded-argument-maps/COORDINATION.md) and
[authorization](discussion.md#iteration20-implementation-and-publication-authorization).
Monitor/independent review/feedback before focused accepted worker publication. GHA disabled/
native investigation PAUSED/VP-001 OPEN UNKNOWN; BOTH builds worker-owned until targeted release.
Final outcomes pending; previous focus blocks below historical where superseded.

Iteration20 **bounded replacement recorded-argument-map plan reviewed; implementation GO pending**.
See [review checkpoint](discussion.md#iteration20-replacement-plan-review). No worker/source/build/
story/CI/native investigation/commit/push restart; prior projection plan deferred/GHA disabled/
VP-001 OPEN UNKNOWN preserved. Earlier focus blocks below are historical where superseded.

Iteration20 **replacement recorded-argument-map candidate design/example/handoff prepared**;
see [preparation](discussion.md#iteration20-replacement-candidate-preparation) and links above.
Direction/prototype agreed, preparation authorized; exact engineering candidates need review,
then separate implementation GO. Old projection candidate deferred. No DML/source/build/story/
worker/CI/investigation/publication restart; GHA disabled/VP-001 OPEN UNKNOWN preserved.
Earlier focus blocks below remain historical where superseded.

Iteration20 **redirected to value arguments and separate provenance**; see
[new direction](discussion.md#iteration20-redirection-value-arguments-and-separate-provenance).
Prior projection-policy candidate DEFERRED; replacement mechanics/plan still need design and
review, then separate GO. No implementation restart, GHA enable/run or native investigation.
Earlier focus blocks below are historical where superseded.

Iteration20 **candidate DESIGN/EXAMPLE/HANDOFF prepared for review; implementation GO pending**.
The user agreed to preserving actual upstream provenance while versioning exact-input versus
result-based downstream reuse identity, then requested preparation. Fixed witnessed-input profile,
ordinary P/Mp/Dp/projection roles, separate tables/public S authorities and SEVEN-Q/SIX synchronous
LOCAL-attempt story are assistant candidates. No generic masks/native facet framework or runtime
fix. DML verified clean HEAD47131da; development GHA disabled, existing worker paused/native
investigation retained/VP-001 OPEN UNKNOWN. No restart or commit/push; review then separate GO.
Older focus blocks below remain historical, not current permission.

Iteration19 **feature accepted/published `a71e89f`; bounded native-CI investigation continues**.
Diagnostic-only `beafc0ee` rawCI41294882995 CANCELLED4pass/Macx oracleFAIL/Windows outer10CANCEL;
actual Macarm nativeSEM mechanism confirmed with full traces, historical causes UNKNOWN.
User explicitly approves Windows outer20 ONLY plus one extra diagnosticround2. Reviewed epoch-
aware pure correction/budget selector published `47131da`; actualCI41299279030 attempt1 running.
Read [investigation](iterations/19-intent-scoped-reuse/CI-INVESTIGATION.md),
[review](iterations/19-intent-scoped-reuse/REVIEW.md) and coordination. No production/native fix
implemented, no exception/green/oldcause diagnosis; original raw evidence/VP001 kept. No further
localnative/full/story or CI rerun beyond reviewed scope; final delivery pending. Earlier states historical.

Iteration19 **published `a71e89f`; user separately authorizes bounded investigation of two
UNKNOWN CI failures**. Read [scoped plan](iterations/19-intent-scoped-reuse/CI-INVESTIGATION.md),
[blockers](iterations/19-intent-scoped-reuse/CI-BLOCKERS.md) and coordination. Existing worker/
current session prepares concrete plan for coordinator review before finite probes/diagnostics/
causal fixes/regressions. RawCI41269736666 FAILED4pass2fail retained; all164new+4cleanup pass
each platform. No timeout/skip/threshold/budget/runner weakening/retryuntilgreen/new feature/
extra agent/cloud/global/later turn/design publication. No exception or diagnosis approved;
BOTH builds worker-owned until targeted freeze/release. Specific plan review/outcomes pending.
Earlier pause/disposition-choice states below are historical.

Iteration19 **implemented/independently accepted/published `a71e89f`; CI FAILED, disposition
BLOCKED pending scoped decision**. [CI blockers](iterations/19-intent-scoped-reuse/CI-BLOCKERS.md),
[review](iterations/19-intent-scoped-reuse/REVIEW.md) and
[coordination](iterations/19-intent-scoped-reuse/COORDINATION.md). ActualCI41269736666 attempt1:
FOUR jobs pass, Windows+Macx86 old async host-client story fails; root causes/attribution UNKNOWN.
ALL164 NEW+4cleanup pass EVERY platform, shared sixXML/primary/digests independently audited.
Independent48/1384 NONEXECUTING and worker209/solefull2657/actual6Q4T26phase remain distinct.
Worker PAUSED ALL/no further tools pending direction; no exception/investigation/rerun authorized,
not finalSTOP/all-green/fixed/inherited. User scoped investigation versus explicit documented
risk-acceptance decision pending. VP-001 OPEN UNKNOWN/no standing waiver; original errors retained.
Earlier acceptance/publication-pending states below are historical.

Iteration19 **independently ACCEPTED exact frozen TWELVE; publication/final-SHA CI pending**.
Read [review](iterations/19-intent-scoped-reuse/REVIEW.md) and
[coordination](iterations/19-intent-scoped-reuse/COORDINATION.md). Independent48 focused/1384
installed NONEXECUTING pass; reviewed worker209/solefull2657/actual6Q4T26phase. IS-001 resolved;
BOTH builds/source/evidence returned for accepted focused worker normal commit/push/actualCI/
fresh triage. Original failures/early91 nonsnapshot qualification/VP-001 OPEN UNKNOWN retained.
No extra full/computation/fixture/later turn/design publication. Final outcome/STOP pending.
Earlier GO/pending states below are historical.

Iteration19 **GO; verified NEW session for existing window-2 agent**. Read
[coordination](iterations/19-intent-scoped-reuse/COORDINATION.md) and
[authorization](discussion.md#iteration19-implementation-and-publication-authorization).
Approved bounded implementation/coordinator independent review/feedback, then accepted worker
focused commit/normal push/final-SHA CI/fixes. BOTH builds worker-owned until targeted freeze/
release; SIX-Q/FOUR-local story/proportionate validation. VP-001 OPEN UNKNOWN/no waiver;
no extra worker/cloud/global/release/package/later turn/design publication. Outcomes pending.
Earlier pending-GO states below are historical.

Iteration 19 **bounded DESIGN/EXAMPLE/HANDOFF reviewed; implementation GO pending**.
Read the three documents linked above and [plan review](discussion.md#iteration19-plan-review).
No worker/source/build/story/CI restart or commit/push; exact engineering spellings remain refinable.
Earlier preparation state below is historical.

Iteration 19 **candidate DESIGN/EXAMPLE/HANDOFF prepared for review; implementation GO pending**.
Read the three documents linked above and [preparation](discussion.md#iteration19-candidate-preparation).
Intent declares result equivalence across implementations; exact full inputs remain. Selected
producer's full provenance differs from requested binding; explicit versioned remove/no history
search/no automatic adoption, old branches/other entries/history preserved. Persistent restrictions
and implementation-deprecation eligibility gates deferred; UX/shared-tree cleanup later. Recommended
new example roles/public S+ownQ/direct W/six-Q-four-local mechanics are candidates, not as-built or
exact schema/API approval. DML clean3b2b370/Iteration18 reviewed complete-stopped; no worker/source/
spec/diagram/build/story/image/CI/experiment/provisioning/commit/push or extra agent/cloud/global/
release/package/design checkpoint. VP-001 OPEN UNKNOWN/no standing waiver/investigation. Review
then separate GO; completed18 permission is not inherited. Earlier delivery state is historical.

Iteration 18 **COMPLETE AND STOPPED through `3b2b370`; all SIX final-SHA CI41182904065 jobs
successful**, attempt1. Read [results](iterations/18-multi-input-reuse/RESULTS.md),
[review](iterations/18-multi-input-reuse/REVIEW.md) and
[coordination](iterations/18-multi-input-reuse/COORDINATION.md). Versioned exact multi-input
selections/new ownQ-W reuse/explicit one-row adoption/old branches delivered; no generic cache/
native entity. Independent38/installed1179 NONEXECUTING distinct from worker163/full2489/
actual SEVEN-Q/THREE-local story/25phases. Final source+remote/shared six XML/primary/digests/
hosted Windows MI-001 verified. Three local children reaped/evidence retained/no external
fixture. Original failed probes/private-driver qualifications/coordinator oracle corrections/
VP-001 OPEN UNKNOWN retained, pass not old diagnosis/waiver. No completed-GO restart/extra agent/
cloud/global/release/package/later turn/design checkpoint publication. Earlier states historical.

Iteration 18 **independently ACCEPTED exact frozen ELEVEN; publication/final-SHA CI pending**.
Read [review](iterations/18-multi-input-reuse/REVIEW.md) and
[coordination](iterations/18-multi-input-reuse/COORDINATION.md). Independent38 focused/1179 installed
NONEXECUTING pass; worker sole full2489/focused163/actual SEVEN-Q/THREE-local story reviewed.
MI-001 resolved, BOTH builds/source/evidence returned for accepted focused worker normal commit/
push/actual final-SHA CI/fresh triage. Original failed probes/qualifications/coordinator oracle
corrections retained, VP-001 OPEN UNKNOWN/no waiver. No extra full/computation/fixture/later turn/
design publication. Final outcome/STOP pending; earlier GO state is historical.

Iteration 18 **GO; assigned to existing window-2 agent in a verified NEW Pi session**.
Read [coordination](iterations/18-multi-input-reuse/COORDINATION.md) and
[authorization](discussion.md#iteration-18-implementation-and-publication-authorization).
Bounded design/example/handoff approved for implementation; coordinator monitoring/independent
review/feedback, then accepted worker focused commit/normal push/actual final-SHA CI/fixes.
BOTH builds worker-owned until changed-surface/HEAD freeze/explicit release. Small current-installed
SEVEN-Q/THREE-local story; owning proportionate validation policy applies. VP-001 OPEN UNKNOWN/
no standing waiver; related changes or recurrence need fresh scope. No extra worker/cloud/global/
release/package/later turn/design checkpoint publication. No as-built/acceptance/outcome yet.
Earlier candidate state below is historical, superseded by GO.

Iteration 18 **direction agreed; candidate design/example/handoff prepared for review**.
Read the three documents linked above and
[planning](discussion.md#iteration-18-agreed-direction-and-candidate-planning). Preserve exact
URI/full binding/full input matching; several selections coexist, explicit adoption changes
only one key, old branches/other entries preserved. Recommended ordinary bounded table/new
selection slots/new decision/strict public validation and SEVEN-Q/THREE-local story are candidate
mechanics, not approved exact schema/API/as-built/implementation GO. No worker/source/spec/
diagram/build/story/image/CI/experiment/provisioning/commit/push started. DML clean9f182be,
completed17 permission not inherited, VP-001 OPEN UNKNOWN/no standing waiver/investigation.
No extra agent/cloud/global/release/package/later turn/design checkpoint. Review then separate GO.
The following completed17 delivery remains latest implemented work, not new-turn permission.

Iteration 17 **COMPLETE AND STOPPED through `9f182be`; ALL SIX final-SHA CI41172108791
jobs successful, attempt1**. Read [RESULTS](iterations/17-implementation-supersession/RESULTS.md),
[REVIEW](iterations/17-implementation-supersession/REVIEW.md) and
[COORDINATION](iterations/17-implementation-supersession/COORDINATION.md). Independent37/
installed712 NONEXECUTING and reviewed worker129/27/full2364/actual TWO-local-attempt story
remain distinct; final six small XML/primary counts/digests/clean source+remote verified.
Reaped local story retained/no external resources; original failures/controller qualifications/
VP-001 OPEN UNKNOWN preserved, pass not earlier diagnosis. No completed-GO restart/new turn/
extra worker/cloud/global/release/package/design checkpoint publication. Earlier states below
are historical.

Iteration 17 **independently ACCEPTED exact frozen12; publication/final-SHA CI pending**.
Read [REVIEW](iterations/17-implementation-supersession/REVIEW.md) and
[COORDINATION](iterations/17-implementation-supersession/COORDINATION.md). Independent37
focused/installed712 NONEXECUTING pass; worker sole full2364 and actual TWO-attempt story
reviewed. BOTH builds/source/evidence returned for accepted worker focused commit/normal
push and exact-SHA CI triage; original failures/qualifications/VP-001 OPEN UNKNOWN retained.
No extra full/fixture/later turn/design publication; final outcome/STOP not claimed yet.
The GO assignment below is historical.

Iteration 17 **GO; implementation assigned in a verified fresh window-2 Pi session**.
Read [coordination](iterations/17-implementation-supersession/COORDINATION.md) and the three
bounded plan documents linked above. Coordinator monitors/independently reviews/feedback until
satisfactory, then accepted worker commit/normal push and actual final-SHA CI/fixes. BOTH builds
worker-owned until changed-surface/HEAD freeze and explicit release. Small installed local
FOUR-Q/TWO-attempt story and proportionate validation apply; no duplicate full/fixture ritual.
VP-001 OPEN/UNKNOWN/no standing waiver. No extra workers/cloud/global/release/package/later
turn or design checkpoint publication. No acceptance or as-built result claimed yet.
The earlier candidate preparation state below is historical, superseded by GO.

Iteration 17 **direction agreed; candidate design/example/handoff ready for review**. Read
[DESIGN](iterations/17-implementation-supersession/DESIGN.md),
[EXAMPLE](iterations/17-implementation-supersession/EXAMPLE.md),
[HANDOFF](iterations/17-implementation-supersession/HANDOFF.md) and
[planning](discussion.md#iteration-17-agreed-direction-and-candidate-planning).
Advisory supersession/reason/evidence and explicit default promotion preserve old code/results/
choices/branches; request's actual as-known-then context is separate from explicit knowledge.
Recommended known-slot ordinary L/captured basis/public readers/four-Q/two-local-attempt story
are assistant candidates, not schema approval/as-built/implementation GO. No automatic
invalidation/ban/cross-binding reuse/adoption or generic lifecycle/installation framework.
DML remains clean published e0089323/all6 finalCI successful; completed16 GO is not inherited.
No worker/source/spec/diagram/build/fixture/image/CI/experiment/provisioning/commit/push or
extra agent/cloud/global/release/package/design publication. VP-001 revisited OPEN/UNKNOWN;
no standing waiver/old runtime diagnosis/investigation permission. Use proportionate policy,
not duplicate-full/Batch-fixture rituals. Review then separate bounded GO.

The following completed Iteration16 delivery remains the latest implemented work.

Iteration 16 **COMPLETE AND STOPPED through `e008932`; all six final-SHA CI41123236764 jobs successful**.
Worker finalized RESULTS and explicitly STOPPED ALL activity. Final source/remote/sixXML+primary
counts/digests/actualMac15arm64 execution and safe archived retirement independently verified.
See [results](iterations/16-versioned-implementation-selection/RESULTS.md) and
[review](iterations/16-versioned-implementation-selection/REVIEW.md). Original failures/
reconstruction/falsemetadata correction/initialbrownoutCANCELLED retained; VP001OPEN UNKNOWN,
not diagnosed by finalpass. No extra full/fixture/worker/cloud/global/release/package/later
turn/design publication. Prior pending state below is historical.

Iteration 16 **published through `e008932`; final-SHA CI41123236764 pending**.
Initial accepted14 `7de65ae` plus approved exact2 runner migration to macos-15 arm64,
normal push/cleanremote verified. All6 final jobs running, not yet all-green. Original
run rawCANCELLED/fivepasses/Macarm brownout/noXML preserved; false migration receipt/failed
regex corrected with independent24 pass, reconstructed receipt qualification retained.
Owned fixtures archived/retired, images/evidence retained. No later turn/design publication.
See [review](iterations/16-versioned-implementation-selection/REVIEW.md).
Earlier independent publication gate below is historical.

Iteration 16 **independently ACCEPTED; focused worker publication/final-SHA CI pending**.
See [review](iterations/16-versioned-implementation-selection/REVIEW.md) and
[coordination](iterations/16-versioned-implementation-selection/COORDINATION.md).
Independent32 focused/installed54 nonexecuting pass; worker correctedfull2263/unchanged gates
and real3-job/9-phase+8correctedreaders reviewed. Exact14/BOTH builds/source/stopped evidence
returned to worker for focused commit/normal push/CI triage. No duplicatefull/fixture or
standing VP-001 waiver. Original failed AST gate/reconstructed provenance/UNKNOWN retained.
No final CI success/later turn/design publication. Earlier GO assignment below is historical.

Iteration 16 **GO; assigned to the existing window-2 agent in a verified NEW Pi session**. Read
[coordination](iterations/16-versioned-implementation-selection/COORDINATION.md) and
[authorization](discussion.md#iteration-16-implementation-and-publication-authorization).
Coordinator monitors/independently reviews/feedback until satisfactory, then accepted worker
commit/normal push/exact-SHA CI evidence and fixes. BOTH builds worker-owned until changed-surface
freeze/release. Published validation policy applies; VP-001 OPEN/UNKNOWN/no standing waiver.
No extra worker/cloud/global/release/package/later turn or design checkpoint publication.
The candidate planning state below is historical, superseded by GO above.

Iteration 16 **direction agreed; candidate design/example/handoff ready for review**.
Read [DESIGN](iterations/16-versioned-implementation-selection/DESIGN.md),
[EXAMPLE](iterations/16-versioned-implementation-selection/EXAMPLE.md),
[HANDOFF](iterations/16-versioned-implementation-selection/HANDOFF.md) and
[planning](discussion.md#iteration-16-agreed-direction-and-candidate-planning).
One intent/two captured bindings/default or explicit implementation, independent reuse override,
exact matching/known per-binding slots/old choices preserved/true branch defaults. Recommended
ordinary Idef/menu/choice/D/public composition/default-only update/three real jobs are candidate
mechanics, not implemented behavior or exact user schema decisions. Review then separate GO.
DML clean4a053340 unchanged; no worker/source/spec/diagram/build/fixture/image/CI/experiment/
provisioning/commit/push. Use published validation policy, not older duplicate-gate rituals.
VP-001 revisited at this planning checkpoint remains OPEN/UNKNOWN; approval only maintenance,
no standing Iteration16 waiver. If async/LMDB/story changes needed, pause/scope investigation.
No extra worker/cloud/global/release/package/later turn/design checkpoint requested.

The following maintenance delivery checkpoint is historical and remains the latest published work.

**Validation-policy maintenance complete and STOPPED at `4a053340`; accepted with VP-001**.
See [delivery](discussion.md#validation-policy-maintenance-delivery-and-exception),
[results](maintenance/validation-policy/RESULTS.md), [review](maintenance/validation-policy/REVIEW.md)
and [exception/follow-up](maintenance/validation-policy/EXCEPTION-VP-001.md).
Published five-file docs/workflow/tests change; worker onefull2082/sevenC/4301/unweakened gates
and coordinator focused23 pass. Actual finalSHA CI fivegreens/one oldMacarmasyncENOENT failure,
all15 newcases pass all6 and sixXMLreport counts/status/digests verified. Raw CI remainsFAILED;
UNKNOWN cause/attribution not disguised as inherited/fixed, follow-up coordinator-owned OPEN.
No repeated CI/full/fixture run just for green, no exception to future failures automatically.
User-delegated evidence-based disposition applied and recorded; worker explicit STOP ALL.
No completed-GO restart/extra agent/cloud/global/runtime/release/package/design publication.
VP-001 revisits next planning checkpoint/before related async-LMDB-reporttiming/story/release
changes or recurrence; investigation needs separate authorization. Prior states below historical.

**Validation-policy maintenance independently accepted; publication/final-SHA CI evidence pending.**
Read [review](maintenance/validation-policy/REVIEW.md),
[coordination](maintenance/validation-policy/COORDINATION.md) and
[plan](maintenance/validation-policy/PLAN.md). Worker onefull2082/sevenC/4301/unweakened gates,
coordinator independent focused23/reportstatus/source/doc checks pass; exact5 accepted/BOTH
builds returned for focusedcommit/normalpush/actualCI reports and triage. No secondfull/fixture/
whole-sourceinventory/automaticallgreen. No exception approved yet. Evidence-based bounded plan
revision authorized, no runtime/extraagent/global/cloud/release/package/design publication.
The following assignment state is historical.

**Validation-policy maintenance GO**, separately authorized after accepted Iteration15.
Read [plan](maintenance/validation-policy/PLAN.md),
[handoff](maintenance/validation-policy/HANDOFF.md),
[coordination](maintenance/validation-policy/COORDINATION.md) and
[authorization](discussion.md#proportionate-validation-maintenance-authorization).
Existing window2/fresh session, focused independent review, accepted worker commit/normal push/
CI evidence and fixes; coordinator judgment may revise bounded plan from observed CI.
No unconditional all-six-green/duplicate-full/fixture rituals; new failures block, explicit
exceptions preserve failed raw CI/risks/UNKNOWN/follow-up. Current gates/thresholds/platforms/
budgets retained. No extra worker/runtime feature/cloud/global/retired fixture/release/package/
design checkpoint publication. Earlier completed status below is historical.

Iteration 15 **implemented, independently accepted, published and STOPPED through `664a870`**;
all six final exact-SHA CI41090059076 jobs successful, attempt1. Worker RESULTS finalized and
explicit ALL-activity STOP observed; final source/remote/primaryCI/disposition independently
verified. See [delivery](discussion.md#iteration-15-delivery-final-publication-and-stop),
[results](iterations/15-intent-reuse-defaults/RESULTS.md),
[review](iterations/15-intent-reuse-defaults/REVIEW.md) and
[coordination](iterations/15-intent-reuse-defaults/COORDINATION.md).
Independent full2060/sevenC/4301/unweakened gates+780 installed four-job/twelve-phase probe,
233correctionpostfix/ninecopiedpolicy-bootstrap clients; worker correction2067. Ordinary
intent defaults/request overrides/pinned reasons/exact full matching/no automatic adoption,
no new native/private codec/public framework. Initial16+3 reviewed controller parser correction;
Unix19 bootstrap established cause distinct WindowsoldcallerENOENT underlyingUNKNOWN despite
finalpass/olderUNKNOWN retained. Both105worker/120own stopped fixtures archived/identity-retired,
images/evidence retained/no prune. Completed GO permits no worker/source/build/fixture/CI restart,
extra worker/global/cloud/release/package/later turn/design checkpoint commit/push. Stop for review.

The following independent acceptance checkpoint is historical.

Iteration 15 **independently accepted; focused publication/exact-SHA CI pending**.
Read [review](iterations/15-intent-reuse-defaults/REVIEW.md),
[coordination](iterations/15-intent-reuse-defaults/COORDINATION.md) and
[acceptance](discussion.md#iteration-15-independent-acceptance-and-publication-gate).
Independent full2060/sevenC/4301/unweakened gates plus separate actual installed780-check
four-job/twelve-phase defaults/overrides/reasons/branches pass; ALL248/exact16 stable.
BOTH builds/source/stopped worker fixture returned for focused worker commit/normal push/
final exact-SHA all-six CI/primary failure evidence+reviewed fixes. Publication pending.
No design publication/extra worker/cloud/global tooling/release/package/later turn; originals/
UNKNOWN preserved. The GO assignment checkpoint below is historical.

Iteration 15 **GO and assigned in a verified fresh window-2 Pi session**.
Read [coordination](iterations/15-intent-reuse-defaults/COORDINATION.md) and
[authorization](discussion.md#iteration-15-implementation-and-publication-authorization).
Coordinator monitors/independently reviews/feedback until satisfactory, then focused worker
commit/normal push and final exact-SHA CI/fixes. BOTH builds worker-owned until ALL-source
freeze/explicit release. Approved bounded plan unchanged; mandatory current-installed defaults/
overrides/branch and native/history/atomicity/loss gates. No acceptance/publication success yet.
No extra worker/cloud/global tooling/generic framework/release/package/later turn/design checkpoint
commit/push; previous notes preserved. Completed Iteration14 permissions are not inherited.

The following plan-approval checkpoint is historical, superseded by GO above.

Iteration 15 **bounded example/design/handoff approved; implementation GO pending**.
The user approved [design](iterations/15-intent-reuse-defaults/DESIGN.md),
[example](iterations/15-intent-reuse-defaults/EXAMPLE.md) and
[handoff](iterations/15-intent-reuse-defaults/HANDOFF.md) as the bounded plan, not as-built behavior.
Exact engineering spellings remain refinable. See [approval](discussion.md#iteration-15-plan-approval).
No worker assignment/restart, source/spec/diagram/build/fixture/image/CI/experiment/provisioning/
commit/push or implementation/delegation/publication GO. DML remains clean8393a82, completed14
permission not inherited, prior notes preserved/no design checkpoint requested.

The following preparation checkpoint is historical, superseded by plan approval above.

Iteration 15 **direction agreed; candidate example/design/handoff ready for review**.
[Design](iterations/15-intent-reuse-defaults/DESIGN.md),
[example](iterations/15-intent-reuse-defaults/EXAMPLE.md) and
[handoff](iterations/15-intent-reuse-defaults/HANDOFF.md) explore one versioned intent default,
explicit fresh/selected-reuse overrides and inspectable why. New request either way/no new attempt
on reuse; absence-driven fresh without automatic adoption; branch-scoped defaults/full matching.
Recommended ordinary Idef/D and separate decision-bearing Q parent/public temporary validation
avoid changing exact normative Q/T/W roles. These and unused-selection/naming rules are candidate
mechanics for review, not additional user decisions/implemented behavior. Recommended normal
acceptance four real jobs/twelve phases is NOT executed. See
[planning](discussion.md#iteration-15-agreed-direction-and-candidate-planning).
No implementation/delegation/publication GO, worker/source/spec/diagram/build/fixture/image/CI/
experiment/provisioning/commit/push; DML clean8393a82, Iteration14 complete-stopped, prior notes
preserved/no design checkpoint requested. Existing as-built CI budgets/runtime/thresholds unchanged.

The following reviewed Iteration14 delivery remains the latest completed implementation;
its earlier no-next-turn wording predates the separately agreed Iteration15 planning above.

Iteration 14 **implemented, independently accepted, published and STOPPED through `8393a82`**.
All six [final exact-SHA CI41025016866](https://github.com/micha/dml/actions/runs/41025016866)
jobs successful, attempt1. Final source/remote/primaryCI/disposition independently verified;
worker RESULTS finalized and explicitly STOPPED ALL activity. The user has reviewed this delivery;
no next turn is selected or authorized. Worker full1867/sevenC/4030;
coordinator independent corrected1863 full/242postfix/separate current installed773-check
three-job durable selection/adoption/branch probe plus read-only scalar/occurrence supplement.
See [results](iterations/14-versioned-reuse-selection/RESULTS.md),
[review](iterations/14-versioned-reuse-selection/REVIEW.md),
[coordination](iterations/14-versioned-reuse-selection/COORDINATION.md) and
[delivery](discussion.md#iteration-14-delivery-final-publication-and-stop).
Ordinary S/V persist bounded public revalidation framing/native all-parent history, selected
reuse creates only newQ/W, explicit fresh leaves selection unchanged, occurrence-based adoption
creates a new snapshot, two branches retain different selected attempts despite equalR84.
No new native/public cache/default/discovery/facet/framework/resource/scheduler/cloud feature.
Original presence-skip exit1/semanticbeforefail/oracle/classifier/formatter/copy/discovery failures
and olderWindowsUNKNOWN preserved. InitialWindowsWSLprimary/latentCRLF/Mac10outercap confirmed;
underlyingMacslowdown UNKNOWN despite finalpass. OnlyMacx86outer20cap separately user-approved,
every runtime/test/threshold/skip unchanged. Owned fixtures archived/identity-retired/images
and evidence retained/no prune. Completed GO permits no source/build/worker/fixture/CI restart/
design checkpoint commit/push/extra worker/cloud/global/release/package/later feature.

The following independent acceptance checkpoint is historical.

Iteration 14 **independently accepted; focused publication/exact-SHA CI pending**.
Final corrected independent1863 Python/sevenC/4030/unchanged gates plus separately authored actual
installed773-check three-job/nine-phase durable selection/adoption/branch probe and read-only
roots/occurrence supplement pass. ALL238/exact18/diagram/package/links/stopped fixture verified;
no outstanding scope finding, BOTH builds/source returned for focused worker commit/normal push/
final exact-SHA all-six CI/reviewed fixes. See
[review](iterations/14-versioned-reuse-selection/REVIEW.md),
[coordination](iterations/14-versioned-reuse-selection/COORDINATION.md) and
[acceptance](discussion.md#iteration-14-independent-acceptance-and-publication-gate).
Original presence-pipeline skipped standardexit1/occurrence policy gap corrected; original other
failures/Windows UNKNOWN preserved. No final publication success/design commit/push/extra worker/
cloud/global tooling/release/package/later turn claimed. Own fixtures retired/worker stopped
fixture returned intact, images/evidence retained.

The following GO assignment checkpoint is historical.

Iteration 14 **GO and assigned** to the existing window-2 agent in a verified fresh Pi session.
Coordinator monitors/independently reviews/provides feedback until satisfactory, then focused worker
commit/normal push and final exact-SHA CI verification/fixes. BOTH builds remain worker-owned until
ALL-source freeze/explicit release. Bounded local current-installed selection/adoption/branch
fixture/build validation is authorized; missing downloads/installations need scoped approval.
Read [coordination](iterations/14-versioned-reuse-selection/COORDINATION.md) and
[authorization](discussion.md#iteration-14-implementation-and-publication-authorization).
No extra workers/cloud/global tooling/generic cache/facets/default/framework/resources/scheduler/
release/package/later turn or design checkpoint commit/push. Prior notes preserved.

The following reviewed-plan checkpoint is historical, superseded by GO above.

Iteration 14 **bounded example/design/handoff reviewed; implementation GO pending**.
[Design](iterations/14-versioned-reuse-selection/DESIGN.md),
[example](iterations/14-versioned-reuse-selection/EXAMPLE.md) and
[handoff](iterations/14-versioned-reuse-selection/HANDOFF.md) explore recording a reusable choice,
explicitly using it, fresh execution without selection change, explicit adoption and two branches
selecting different attempts with equal result84. Initial matching stays exact intent/binding/full
inputs including producer witness; no automatic default/discovery/index/facets/scheduler/resources.
Recommended ordinary S/V retains bounded public expected/job/observation metadata plus native
all-parent completion history, revalidating through existing public inspector/transfer instead
of trusting T/result flags or external paths. User “reviewed” records bounded plan review,
not as-built claims; exact engineering spellings remain refinable.
Read [review checkpoint](discussion.md#iteration-14-plan-review-checkpoint).
No implementation/delegation/publication GO, worker/build/fixture/image/CI restart/DML/spec/diagram
edit/experiment/provisioning/commit/push; DML remains cleanb296fdb, prior notes preserved/no design
checkpoint requested. Completed Iteration13 permissions are not inherited.

The following Iteration13 delivery was the previous completed turn.

Iteration 13 **implemented, independently accepted, published and STOPPED through `b296fdb`**.
All six [final exact-SHA CI41006689070](https://github.com/micha/dml/actions/runs/41006689070)
jobs successful, attempt1. Worker final1706 Python/seven C/3841 statements/unchanged gates;
coordinator independent full1692 plus126-test correction postfix and separate actual installed
466-check three-job offline-reuse/fresh-control pass. ALL228/exact initial14+test-only7 commit
surfaces/clean DML tree-index/matching remote verified; source/runtime/diagram unchanged by
correction. See [results](iterations/13-explicit-attempt-reuse/RESULTS.md),
[review](iterations/13-explicit-attempt-reuse/REVIEW.md),
[coordination](iterations/13-explicit-attempt-reuse/COORDINATION.md) and
[delivery](discussion.md#iteration-13-delivery-final-publication-and-stop).
New Q/ordinary W selects old successful T/result without another attempt/job; explicit fresh
control retains W's old choice despite equalR84. Exact intent/binding/full inputs include producer
witness; no generic cache/facet/adoption/scheduler/resource/cloud framework or new native entity.
Initial Windows confirmed native112 disk-full failure fixed with reviewed scoped test-only
successful-owned-temp disposal; exact original disk inventory absent/older causes UNKNOWN.
Owned fixtures archived/identity-retired, images/evidence retained/no prune. Worker explicitly
STOPPED ALL activity. Completed GO authorizes no worker/build/fixture/CI restart/design checkpoint
commit/push/extra worker/cloud/global tooling/release/package publication/later turn.

The following independent acceptance checkpoint is historical.

Iteration 13 **independently accepted; focused worker publication/exact-SHA CI pending**.
Coordinator independent full1692/seven C/3841 statements/unchanged gates and separate actual
installed466-check three-job offline-reuse/fresh-control pass. ALL226/frozen14-file surface/
current runtime/diagram/links/disposition independently verified. BOTH builds/source/stopped
worker fixture returned for focused commit/normal push/final exact-SHA all-six CI/fixes.
See [review](iterations/13-explicit-attempt-reuse/REVIEW.md) and
[coordination](iterations/13-explicit-attempt-reuse/COORDINATION.md). No final publication success
claimed yet; no design commit/push/extra worker/cloud/global tooling/release/package/later turn.

The following GO assignment checkpoint is historical.

Iteration 13 **GO and assigned** to the existing window-2 agent in a verified fresh Pi session.
Coordinator monitors/independently reviews/feedback until satisfactory, then focused worker commit/
normal push and final exact-SHA CI verification/fixes. Worker owns BOTH builds until ALL-source
freeze and explicit release; see [coordination](iterations/13-explicit-attempt-reuse/COORDINATION.md)
and [authorization](discussion.md#iteration-13-implementation-and-publication-authorization).
Explicitly record a new request satisfied using an old selected successful attempt/result,
without new T/job; separately request fresh execution. Initially match exact intent/binding/
full-input identity including producer witness, not containing commit/request occurrence.
Prefer example-local public APIs; no cache discovery/default/facets/adoption/scheduler/resources/
cloud/global tooling/extra worker/release/package/later turn. Bounded current-installed local
reuse/fresh-control fixture/build validation is authorized; missing downloads/installations need
scoped approval. No design checkpoint commit/push requested; prior notes preserved.

The following plan-review checkpoint is historical, superseded by GO above.

Iteration 13 **bounded example/design/handoff reviewed; implementation GO pending**.
Explicitly record a new request satisfied using an old selected successful attempt/result,
without new T/job; separately request fresh execution. Initially match exact intent/binding/
full-input identity, including producer witness, not containing commit/request occurrence.
No cache discovery/default selection/masks/facets/adoption/scheduler/registry/resource/cloud feature.
Reviewed ordinary W/new-Q association, separate Q/W transactions/example-local public helper/
known-stopped fixture recipe are in [design](iterations/13-explicit-attempt-reuse/DESIGN.md),
[example](iterations/13-explicit-attempt-reuse/EXAMPLE.md) and
[handoff](iterations/13-explicit-attempt-reuse/HANDOFF.md); see
[review checkpoint](discussion.md#iteration-13-plan-review-checkpoint).
The user's “reviewed” is bounded plan review, not implementation/delegation/publication GO;
exact engineering spellings remain refinable. No DML/spec/diagram edits, worker/build/fixture/
image/provisioning/test/CI restart, experiment/commit/push. DML remains clean66311fc; completed
Iteration12 GO not inherited. No design checkpoint requested; accumulated notes preserved.

Latest completed turn follows.

Iteration 12 **implemented, independently accepted, published and STOPPED through `66311fc`**.
All six [final exact-SHA CI40954598093](https://github.com/micha/dml/actions/runs/40954598093)
jobs successful, attempt1. Coordinator full standard1647/seven C/3783 retained statements/unchanged
gates and separately authored actual installed293-check17+25->42->84 chain pass. Published16-file
slice/ALL217 hashes/exact source set/clean tree-index/matching remote verified. See
[results](iterations/12-composed-recorded-steps/RESULTS.md),
[review](iterations/12-composed-recorded-steps/REVIEW.md),
[coordination](iterations/12-composed-recorded-steps/COORDINATION.md) and
[delivery](discussion.md#iteration-12-delivery-final-publication-and-stop).
Actual local Floci add13+29=42, then double consumes R1 plus exact selected producer final attempt
and factor2, returns84. Ordinary summary links selected attempts/result; Python sequences steps,
no generic evaluator/scheduler. Reviewed mechanics and evidence gates are in
[design](iterations/12-composed-recorded-steps/DESIGN.md),
[example](iterations/12-composed-recorded-steps/EXAMPLE.md) and
[handoff](iterations/12-composed-recorded-steps/HANDOFF.md).
Prefer example-local public-API helpers; no new native/role codec/public framework assumed.
The bounded turn is complete. Worker corrected actual5-job/15-phase13+29->42->84, producer23/
consumer23/private final-B and supplemental9fresh offline receive/3CLI evidence remain distinct.
Original census/import/setup/gh-log correction and earlier Windows UNKNOWN causes retained.
Owned fixtures archived/identity-retired; images/evidence retained/no prune. Worker explicitly
STOPPED ALL activity. No worker/build/fixture/CI restart/extra worker/cloud/global tooling/release/
package publication/later turn or design checkpoint commit/push. Reviewed design/example/handoff
retain plan provenance, not restart authorization.

Iteration 11 **implemented, independently accepted, published and stopped through `640cabb`**.
[Final exact-SHA CI40913866835](https://github.com/micha/dml/actions/runs/40913866835) succeeds
all six jobs, attempt1. Separate public Floci stage/one-shot submit/saved identity/bounded immutable
S3 observation composes unchanged exact-Q/public inspector/atomic explicit-ref return.
Coordinator independent full1575/seven C/3536 retained statements/unchanged native-memory gates,
separate current installed380-check17+25 Batch workflow and follow-up225 tests pass. Worker final
1585/seven C/unchanged retained gates, actual current normal3 jobs/9P-U-F/16 artifacts and qualified
private/loss/bootstrap/history/atomicity/race gates remain distinct evidence.

Initial33-file `9ed2270` plus EOF1-test `4bb0bfa` and diagnostic3-test `640cabb` normally published.
Initial CI5green/Windows unchanged old-reader rc1 remains **UNKNOWN**; final Windows pass is not
its diagnosis/fix. Independent exact commit surfaces/ALL206 hashes/clean tree/matching remote/
completed JSON/full logs/finite watch0 verified. All exact stopped owned fixtures archived and
retired; images/nonsensitive evidence retained/no prune. See
[review](iterations/11-floci-batch-execution/REVIEW.md),
[results](iterations/11-floci-batch-execution/RESULTS.md) and
[coordination](iterations/11-floci-batch-execution/COORDINATION.md).
Worker stops after RESULTS-only finalization. No further source/build/fixture/CI restart, extra
workers/cloud/global tooling/release/package publication/later turn/design checkpoint authorized.

The following acceptance/assignment/plan checkpoints preserve chronological provenance.

Iteration 11 **implemented and independently accepted; focused publication/CI pending**.
Separate public Floci stage/one-shot submit/saved identity/bounded immutable S3 observation
composes unchanged exact-Q/public inspector/atomic explicit-ref return. Coordinator fresh standard
1575 Python/seven C/3536 statements/unchanged native-memory gates and separate current installed
17+25 Batch workflow380 checks pass. Worker current actual normal3 jobs/9P-U-F/16 artifacts,
private post-reap/cleanup/original-profile overflow/loss/bootstrap and host strong history/
atomicity/race gates are reviewed, not conflated with coordinator evidence. No outstanding
within-scope finding; both builds/stopped fixtures returned for reviewed33-file focused worker
commit/normal push/final exact-SHA CI. Publication not yet claimed. See
[review](iterations/11-floci-batch-execution/REVIEW.md),
[results](iterations/11-floci-batch-execution/RESULTS.md) and
[coordination](iterations/11-floci-batch-execution/COORDINATION.md).
No extra workers/cloud/global tooling/release/package publication/later turn/design checkpoint.

The following GO assignment and accepted-plan checkpoints preserve chronology.

Iteration 11 **GO and assigned** to the existing window-2 agent in a verified fresh session.
Coordinator monitors/independently reviews/fixes until satisfactory, then directs focused worker
commit/normal push and verifies exact-SHA CI/fixes. Worker owns both shared builds until ALL-source
freeze/explicit release. Bounded offline installed image/private Floci fixture and actual combined
gate are authorized; missing downloads/installations need scoped approval. See
[coordination](iterations/11-floci-batch-execution/COORDINATION.md) and
[authorization](discussion.md#iteration-11-implementation-and-publication-authorization).
No extra workers/cloud/global tooling/release/package publication/later turn/design checkpoint.

The following accepted-plan checkpoint predates GO and preserves planning provenance.

Iteration 11 **bounded plan/handoff accepted**:
[design](iterations/11-floci-batch-execution/DESIGN.md),
[acceptance story](iterations/11-floci-batch-execution/EXAMPLE.md),
[handoff](iterations/11-floci-batch-execution/HANDOFF.md).
Run current installed DML inside one real Batch job after submitter exits; fresh bounded clients
retrieve newly produced immutable P/U/F through S3, validating exact caller request/full history
before existing explicit-ref return. Recommended local Floci-specific stdlib HTTP/no SDK/auth
prototype, one service attempt, saved job/independent selection, manifest-last create-only phase
objects and no service-status-to-DML-done inference. These are accepted planning choices, not
as-built behavior; exact engineering spellings remain refinable.

New combined acceptance/image work goes beyond prior Node jobs/packet replay. Conditional fixture
uses cached pinned emulator/private bridge/no host ports/exact four services/no9169, new installed
DML image and explicit trusted socket/job-security limits. No automatic retry/recovery/cancellation,
cloud/AWS parity, native/resource/cache/UI feature or extra worker. Implementation/delegation/
publication GO remains pending; no fixture/build/CI/experiment restart or design commit/push
requested. See [approval](discussion.md#iteration-11-plan-approval).

**Floci feasibility is complete and stopped: viable with constraints.**
[Report](feasibility/floci/REPORT.md)/[coordinator review](feasibility/floci/REVIEW.md): released
2.3.0 Docker Batch jobs genuinely outlive submitting clients; fresh polling and S3 result exchange
pass. Separate prior synthetic DML P/U/F packet transport/public validation/explicit-ref reception
pass, **not actual DML execution inside Batch or a combined adapter**. Final exact-four-service
private fixture corrects initial extra-private-EC2/IMDS deviation; original evidence stays qualified.
Cleanup best-effort/no idempotent submission/live-restart guarantee; retries1 and substantial
Docker socket authority remain constraints. Owned resources archived/retired; pinned image retained,
DML099d156 clean. No Iteration11 plan/implementation GO or further experiments/pulls/commit/push.
[Handoff](feasibility/floci/HANDOFF.md) preserves bounded authorization/profile history.

Iteration 10 is **implemented, independently accepted, published and stopped** through
**`099d156`**; [final exact-SHA CI40791372333](https://github.com/micha/dml/actions/runs/40791372333)
succeeds all six jobs. See [results](iterations/10-asynchronous-ssh-execution/RESULTS.md),
[review](iterations/10-asynchronous-ssh-execution/REVIEW.md) and
[coordination](iterations/10-asynchronous-ssh-execution/COORDINATION.md). Fixed foreground
nonwaiting SSH launch/live owner, separate saved identity, bounded validated immutable P/U/F
observation and owning read-only packet inspection preserve exact-Q explicit-ref return and
existing caller heads/request refs. No detached remote survival promise.

Worker final stable `-v`1372 Python/seven C,2828/2828/unchanged native/memory/141CLI gates;
coordinator independent full1357, postfix168/33/44 and separate installed178-check actual SSH
workflow. Worker final actual progress396/synchronous271 checks; all13 wheel/independent host/
fixture host/remote artifact bytes match. Reviewed focused precommit changed-host test correction
retains original393 malformed-key qualification. Initial publication Windows new private host-model
defect fixed; subsequent same-SHA attempts fail distinct unchanged old async/caller stories, causes
UNKNOWN despite final pass. Test-only bounded diagnostics do not claim their fix/diagnosis.

Initial24-file `fdba76e`, one-test `6f063d9`, diagnostic3-test `099d156` normally published,
including unchanged prior diagram ancestor `a94e6f5`. Implementation clean/remote master matches
at final checkpoint. Owned stopped fixtures/B archived before container/private-key retirement;
no listener remains, image/nonsensitive evidence retained. Worker stops after RESULTS finalization.
No additional workers/cloud/global tooling/release/package publication/later turn/design commit/push.
Earlier GO and reviewed planning checkpoint below preserve provenance, not restart authorization.

Iteration 10 is **GO and assigned** to the existing window-2 agent in a verified fresh session.
Coordinator monitors, independently reviews and provides fixes until satisfactory, then directs
focused worker commit/normal push and verifies exact-SHA CI/fixes. See
[coordination](iterations/10-asynchronous-ssh-execution/COORDINATION.md) and
[authorization](discussion.md#iteration-10-implementation-and-publication-authorization).
Worker owns both shared builds until explicit source freeze/release; mandatory separate actual
installed SSH/container validation remains required. Preserve/account for existing local diagram
ancestor `a94e6f5`; no extra workers, detached supervisor, cloud/global tooling, release/package
publication or later feature turn. No design checkpoint commit/push requested.

The following plan checkpoint records earlier provenance; its pending-GO statements are
superseded by the authorization above.

Iteration 10's bounded plan is **reviewed and locally checkpointed**:
[design](iterations/10-asynchronous-ssh-execution/DESIGN.md),
[worked example](iterations/10-asynchronous-ssh-execution/EXAMPLE.md) and
[conditional handoff](iterations/10-asynchronous-ssh-execution/HANDOFF.md).
Nonwaiting foreground execution SSH launch, saved identity/live owner separation and one fixed
nonexecuting observe action reuse public coherent P/U/F discovery. A narrow owning packet
inspector validates without writing A; existing exact-Q receive publishes explicit A refs.
Remote gates are controlled out of band, not shared mounts/runtime command hooks. No detached
remote survival promise; exact engineering spellings remain refinable.

The requested checkpoint also includes separately authored diagram/test maintenance in DML
as local **`a94e6f5`**, not pushed: packed byte layouts/hash masking/linked references/datum
variants and simplified navigation, with six focused tests plus JS syntax/DOM-stub checks
passing. No runtime change, real-browser audit or new full-suite/CI claim. Future assignment
must reinspect the clean current DML baseline and account for this ancestor before any push.
See [checkpoint](discussion.md#iteration-10-plan-review-and-local-checkpoint).

Separate Iteration 10 implementation/delegation/publication GO remains pending. No worker,
fixture/SSH, runtime/as-built implementation, experiment/build/provisioning or CI started.
No push in either repository; design has no remote. Earlier candidate/no-checkpoint statements
preserve provenance, not current status or permission to inherit completed Iteration 9 GO.

Iteration 9 is implemented, independently accepted and published through **`29ed39b`**;
[final exact-SHA CI](https://github.com/micha/dml/actions/runs/40701925587) passes all six jobs.
The separate SSH layer/fixed helper stages caller-pinned Cq/Q, executes only new T in B and
fetches nonexecuting candidates for unchanged exact-Q atomic explicit-ref A receive. Caller
heads/request refs stay unchanged; disconnect/status never imply outcome/relaunch permission.
Docker is local fixture support, not runtime backend/shared exchange. Approved loopback-only
host networking demonstrates filesystem/runtime/SSH separation, not network-namespace or
second-host isolation.

Worker stable postfix `-v` passes **1191 Python/seven C**, Python2637/2637 and unchanged
native/memory/141CLI gates. Coordinator fresh full `-v` passes1189/seven C, separate installed
actual SSH **177 checks**, all11 wheel/host/remote artifact bytes, then independent postfix
**104 tests**. Worker bare installed gate **271 checks** and nine selected negative probes
remain distinct evidence. [RESULTS](iterations/09-ssh-container-execution/RESULTS.md) and
[REVIEW](iterations/09-ssh-container-execution/REVIEW.md) qualify trust/capture/profile/process/
platform/coverage/mutation and real versus substituted faults.

Reviewed22-file `f63ac75` plus one-file Windows host-model correction `29ed39b` are normally
pushed, including unchanged prior diagram ancestor `f7113d7`. Initial CI had five jobs green/
Windows three failures: two confirmed new harness bugs are fixed; unchanged prior caller-story
early child reason remains unknown despite final Windows pass. At that publication checkpoint,
implementation tree/index was clean and remote master matched `29ed39b`; later local diagram
maintenance `a94e6f5` is unpushed. Owned stopped fixture/B evidence archived before container/
private-key retirement; no owned listener remains, nonsensitive image/evidence retained.

This bounded turn is **complete and stopped**; see
[coordination](iterations/09-ssh-container-execution/COORDINATION.md). The user accepted the
delivery and requested this local design checkpoint. No push, extra workers, release/package
publication, cloud/global tooling or later feature turn. Earlier preparation/GO/no-checkpoint
statements preserve provenance, not restart permission.

Iteration 8 is implemented, independently accepted and published through **`865bb79`**;
[final exact-SHA CI](https://github.com/micha/dml/actions/runs/40624753242) passes all six jobs.
The bounded turn is complete and stopped. A explicitly records Q/Cq under atomic submission/
request refs before launch; fresh B registers exact imported Q and creates only T before
existing execution. Both return paths pin exact Cq/Q; existing caller heads/request refs stay
unchanged. Public request builder/first-registration seams preserve local ownership, original
fresh-Q mode and bootstrap/unknown/publication/cleanup/live-owner boundaries. Strict v2
job/handle framing requires nullable Q selection; no migration or global replay/exactly-once
claim. The [as-built contract](../dml/docs/spec-next/caller-requests.md) owns actual behavior.

Worker final stable `-v` passes **1085 Python tests/seven C**, Python **2299/2299**, unchanged
native/memory gates and **141 CLI Valgrind processes**. Coordinator initial independent `-v`
passes 1081/seven C, separate installed workflow **302 checks**, then independent **254-test**
postfix caller suite after the test-only correction. Initial Windows CI cancelled with enormous
physical-byte diffs; dependency-supported layout emulation demonstrates the fixture defect,
but capped original logs lost its exact test header. The reviewed comparable-map/compact
exact-byte-assertion fix retains rollback oracles and yields all final CI jobs green.
[RESULTS](iterations/08-caller-recorded-requests/RESULTS.md) and
[REVIEW](iterations/08-caller-recorded-requests/REVIEW.md) preserve evidence and trust/profile/
process/platform/mutation/coverage qualifications; CI informational `-c` is not local `-v`.

Reviewed initial 22-file implementation `509c2f0` plus one-file test correction `865bb79` are
normally pushed; the Iteration 8 publication checkpoint was clean with remote master
matching `865bb79`. Worker finalized RESULTS and stopped. No extra workers, release/tag/
package publication, cloud/global tooling or later feature turn. Earlier planning/GO
statements preserve provenance, not permission to restart. See
[coordination](iterations/08-caller-recorded-requests/COORDINATION.md).

The user accepted Iteration 8 and requested maintenance of the self-contained
[LMDB entity diagram](../dml/docs/lmdb-entity-diagram.html), then storage-identity field
annotations and a local commit. At the earlier maintenance checkpoint, diagram/maintenance/tests
were committed separately in DML as local **`f7113d7`**, not yet pushed; Iteration 9 later
publishes that unchanged ancestor.
Four focused tests, JavaScript syntax/DOM-stub checks and links/whitespace
pass; no new full-suite/CI or real-browser audit claimed. This design checkpoint includes
accumulated Iteration 8 delivery/review/acceptance and diagram-maintenance notes; no design
push or new feature authorization.

Iteration 7 is implemented, independently accepted and published as `a8d6463`; all
six final exact-SHA CI jobs pass on the first run. The bounded turn is complete and
stopped. The separate explicitly imported exchange helpers start one fixed installed
worker, observe coherent pinned P/U/F history and receive selected validated packets
under explicit A refs without moving existing heads. Saved observation identity is
separate from application-owned live process reaping; fresh clients can exit/reobserve
without relaunching. P/U is working evidence, F is done only after validated recorded
computation/separate cleanup has been retrieved. Unknown never becomes failure merely
from worker exit or elapsed time. No unowned detached lifetime guarantee.

Worker and coordinator fresh standard `-v` checks pass: 831 Python tests, seven C
executables, 2013/2013 Python statements and unchanged native/memory gates; 141 native
CLI Valgrind processes pass. Coordinator's separate installed workflow passes 208
independent checks. Real process barriers, typed-byte oracles, coherent ref races,
concurrent readers, late successful-new-put rollback and genuine post-F profile overflow
are exercised. Host coverage is not installed-child coverage; trust/capture, process,
profile, precise exclusions/runtime suppressions and Python mutation-tool gaps remain
qualified in [RESULTS](iterations/07-asynchronous-local-execution/RESULTS.md) and
[REVIEW](iterations/07-asynchronous-local-execution/REVIEW.md). The
[as-built contract](../dml/docs/spec-next/asynchronous-execution.md) owns actual behavior.

Reviewed 22-file implementation is clean at published `a8d6463`, remote master matches;
[exact-SHA CI](https://github.com/micha/dml/actions/runs/40602956772) passes all six jobs,
no fix needed. No extra worker, release/tag/package publication, cloud/global tooling,
automatic recovery, detached service or later feature turn. Delivery/status notes are
included in the requested local design checkpoint; no design push requested and this
repository has no remote. Earlier planning/GO statements preserve provenance, not
permission to restart the completed worker.

Iteration 6 implements one pinned step in independent local B and exact recorded
history return to A. The separate explicit `daggerml.exchange` layer composes public
prepare/execute/receive stages over unchanged local execution and transfer. Requests
and attempts originate in B; fresh retained one-shot workspaces prevent implicit
reexecution. Receive compares caller-owned selection/token and validates the selected
completion in disposable storage before atomic explicit-ref import. A's existing heads
stay unchanged; no adoption or merge. The
[as-built contract](../dml/docs/spec-next/repository-execution.md) owns actual behavior;
[RESULTS](iterations/06-local-repository-execution/RESULTS.md) and
[REVIEW](iterations/06-local-repository-execution/REVIEW.md) qualify evidence/limits.

Worker and independent coordinator fresh default checks pass: seven C executables,
609 Python tests, 1,639/1,639 Python statements and unchanged retained C coverage/memory
gates; 141 native CLI Valgrind processes pass. Coordinator's separate installed
workflow passes 73 independent checks. Typed wrong-history rejection, real map-full,
late rollback with successful new puts, safe process-loss barriers, recorded failure/
evidence/cleanup, pin/head preservation and offline packet receive are exercised.
Host-helper coverage is not installed-child coverage; narrow existing exclusions/runtime
suppressions, unavailable Python mutation tools, finite local process/platform and
trust/full-environment/profile limits remain qualified.

Reviewed 16-file implementation is committed/pushed as `a0aa05d`; all six jobs in
[exact-SHA CI](https://github.com/micha/dml/actions/runs/40593738345) pass on the first
run. Implementation tree/index are clean and remote master matches. Implementation,
review and publication/CI are complete and stopped. No extra workers, release/package
publication, cloud experiments, automatic recovery/retry, merge/adoption, reuse/facets,
resources/observer work or later feature turn. Delivery notes are included in the
user-requested local design checkpoint alongside Iteration 7's unapproved candidate
plan. Earlier uncommitted/preparation/authorization statements preserve chronological
provenance, not current permission to restart.

Iteration 5 implements pinned DML commit transfer with complete all-parent typed
object closure between local repositories, preserving IDs/bytes and computational
occurrences, with optional atomic destination-ref creation and ordinary Python/CLI
inspection. A narrow public packed-record insertion wrapper reuses native validation;
the separate transfer module uses bounded JSON/base64 bundles and create-or-same-target
refs. Source refs and external resources are not transferred. The
[as-built contract](../dml/docs/spec-next/transfer.md) owns actual API/behavior;
[RESULTS](iterations/05-pinned-snapshot-transfer/RESULTS.md) and
[REVIEW](iterations/05-pinned-snapshot-transfer/REVIEW.md) qualify evidence and limits.

Worker and coordinator fresh default checks pass: seven C executables, 467 Python
tests, 1,163/1,163 Python statements and unchanged retained C coverage gates.
Expanded binding memory and 141 native CLI Valgrind processes pass; coordinator's
separate installed workflow passes 50 checks. Genuine source absence/corruption,
complete-bundle checks despite prepopulated B, late abort/ref conflict, real map-full
and pre/postcommit interruption are exercised. Host coverage is not installed-child
coverage; precise exclusions/runtime suppressions, unavailable Python mutation tools,
local wheel/runtime and trust/profile limits remain qualified.

Reviewed implementation is committed/pushed as `0ec769b`; all six jobs in
[final exact-SHA CI](https://github.com/micha/dml/actions/runs/40556958937) pass
on the first run. Implementation checkout/index are clean and remote master matches.
Implementation, review and publication/CI are complete and stopped. No remote
execution/sync, recovery/merge/thin/resumable/network/cloud,
reuse/facets, resources/observer work, extra workers, release/package publication or
later feature. The user accepted the delivery and requested a local checkpoint of
these design notes as `26c9afa` before discussing Iteration 6. Its separately approved
plan is above, not implementation approval; the requested Iteration 6 checkpoint
includes subsequent discussion/planning notes. This design repository has no remote.

Iteration 4 is implemented, independently reviewed and published through `d498a6c`.
It adds a separate explicitly imported `daggerml.local` layer: captured trusted Python
entry bytes, pinned named inputs, ordinary request/attempt/outcome DAGs, cooperative
child result publication, explicit retry and separate computational/cleanup outcomes.
No native evaluator or execution CLI command was added. Unknown outcomes after
interruption remain unknown; capture/trust/cleanup limits remain explicit in the
[as-built contract](../dml/docs/spec-next/local-execution.md).

Worker and coordinator fresh default checks pass: seven C executables, 368 Python
tests, 878/878 Python statements and unchanged retained C coverage/memory gates.
Coordinator's separate installed parent/child/reader/console probes pass 43 checks.
Two Windows-stalled runs were cancelled; a confirmed oversized pytest-ID defect was
fixed without reducing the 1 MiB + 1 byte input or weakening tests. Final exact-SHA
[CI run](https://github.com/micha/dml/actions/runs/40536650838) passes all six jobs.
Cancelled-run log unavailability, direct-helper versus uninstrumented child coverage,
mutation-tooling gaps and platform/install limits remain qualified in
[RESULTS](iterations/04-local-recorded-execution/RESULTS.md) and
[REVIEW](iterations/04-local-recorded-execution/REVIEW.md).

Implementation master is clean at pushed `d498a6c`; this bounded turn is complete
and stopped. No release/package publication or later feature turn. The user accepted
the delivery; its design notes were checkpointed locally as `ee708c4` in this
no-remote repository. Iteration 4's stop line remains; Iteration 5 is separately
authorized above.
Reuse/facets, intent lifecycle,
scheduling, remotes/cloud, resources and observer/UI remain outside this turn.

Iteration 3 is implemented, independently reviewed and published as `9b8fb71`.
It adds scoped named DAG bindings, non-executing sub-DAG-reference nodes, explicit
lookup and bounded nested CLI inspection over the existing C/Python foundation.
The runnable comparison example records Python-produced values and containment,
not captured computational causality or DML execution.

Worker and coordinator fresh default checks pass: 7 C executables, 316 Python tests,
Python 469/469 statements and retained C 1681/1681 lines, 132/132 functions,
1562/1562 outcomes; expanded binding and 141 native CLI memory processes pass.
Coordinator's 49 independent probes and isolated installed workflow also pass.
The first published exact-SHA CI run succeeds in all six jobs. Precise exclusions,
mutation survivors, unsupported finalizer abandonment, presentation/read limits,
platform skips and local installed-package limits remain explicit in the
[delivery](iterations/03-composable-dags/RESULTS.md) and
[review](iterations/03-composable-dags/REVIEW.md).

The implementation checkout is clean at pushed `9b8fb71`; work is stopped after
this bounded turn. No release/tag, package publication or later feature was started.
Design notes are checkpointed locally in this no-remote repository.

Iteration 2 delivers a low-level Python API over the existing C foundation and an
inspection-only native CLI with packaged console forwarding. Worker and independent
coordinator default checks pass; after bounded Windows fixture fixes the fresh
local default run has 7 C executables and 255 Python tests, with retained 100%
C/Python populations and precise exclusions/runtime-memory suppressions. Published
`e253249` passes all six CI jobs, with platform skips and informational CI coverage
kept distinct from the local default/memory evidence. Local staged-source/wheel
install workflows pass; mutation survivors, unsupported foreign-last-owner
abandonment and untested installed-package/runtime coverage remain explicit in the
[delivery notes](iterations/02-repository-usability/RESULTS.md).

Implementation, review, authorized publication and Actions monitoring are complete;
Iteration 2 work is stopped. No tags, releases, package publication or later feature
implementation were performed. Design notes remain local/uncommitted. Higher-level
helpers belong above this low-level API; the runnable
example is composition, not a workflow framework.

The central goal is human visibility into high-throughput agent-led research:
deterministic inspection and progressive visualization of recorded computation,
not another layer of agent reassurance. See the discussion's
[observability motivation](discussion.md#observability-motivation-and-sidecar-observers).

- Independent sidecar observers over uniformly structured research history.
- Immutable computational history with distinct request and attempt occurrences.
- Intent-level reuse defaults, explicit overrides, and versioned reuse selection.
- Bounded execution adapters reporting `working` or `done`.
- Resource ownership, full-history retention, GC, and explicit excision.
- An ordinary OpenTofu IaC Git repository as a regenerable resource-management
  view of DML, deployed through user- or agent-selected tooling.
- HCL composition and installation DAGs that can produce bound execution closures.

The authorized feasibility study and candidate iteration tested these ideas using
local OpenTofu, a real artifact provider, durable journals, process-kill experiments,
and independent audits. Narrow cooperative mechanisms work; automatic real-resource
management still has unresolved authority, input-capture, composition and erasure
gaps. See [the iteration results](feasibility/ITERATION-RESULTS.md) before choosing
next steps. Exact production schemas, APIs and policies remain open.

## Provenance

The user authorized moving `/tmp/dml-tasks/agent-design/` to
`/work/repos/micha/dml-design` and making an initial local checkpoint commit.
`discussion.md` is the migrated `output.md`, updated to reflect its persistent
location. Original task input and acknowledgement are preserved unchanged in
[archive/](archive/); their temporary paths and coordination instructions are
historical, not active directives.

Other task reports and validation artifacts were not migrated. The DML
implementation checkout remains separate at `/work/repos/micha/dml`.
