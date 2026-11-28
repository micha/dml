// Exact version selection for portable scale requests and all three ways to use a result.
module recorded_version_selection_design {
  // One source plan, local result pin, staging pin, reuse record ref and receipt
  // key, with disjoint fixed names. A call carries the selected immutable IDs.
  // Presence and name checks other than those below are unchanged. Setup steps
  // represent imports and other writers' changes between transactions; objects
  // and bundles are abstracted by immutable IDs. No GC, native faults or fairness.
  // All result fixtures have the exact selected sum input, factor and numeric
  // value. In particular, wrongParent deliberately attaches this otherwise
  // matching call to a different same-version request (with different arguments).
  pure val absent = 0
  pure val oldMain = 1
  pure val movedMain = 2
  pure val producer = 3
  pure val request1 = 10
  pure val request2 = 11
  pure val other1 = 12
  pure val other2 = 13
  pure val unsupportedRequest = 14
  pure val good1 = 20
  pure val good2 = 21
  pure val wrongParent1 = 22
  pure val wrongParent2 = 23
  pure val wrongVersion1 = 24 // Exact @1 request parent, @2 implementation.
  pure val wrongVersion2 = 25 // Exact @2 request parent, @1 implementation.
  pure val legacy = 26
  pure val results = Set(good1, good2, wrongParent1, wrongParent2, wrongVersion1, wrongVersion2, legacy)
  pure val omitted = 0
  pure val v1 = 1
  pure val v2 = 2
  pure val unknown = 3
  pure def supported(version: int): bool = Set(v1, v2).contains(version)
  pure def requestFor(version: int): int = if (version == v1) request1 else request2
  pure def requestedVersion(req: int): int =
    if (Set(request1, other1).contains(req)) v1
    else if (Set(request2, other2).contains(req)) v2 else unknown
  pure def resultParent(result: int): int =
    if (Set(good1, wrongVersion1).contains(result)) request1
    else if (Set(good2, wrongVersion2).contains(result)) request2
    else if (result == wrongParent1) other1 else if (result == wrongParent2) other2 else producer
  pure def resultVersion(result: int): int = if (Set(good2, wrongParent2, wrongVersion1).contains(result)) v2 else v1
  pure def resultFits(result: int, req: int): bool =
    results.contains(result) and result != legacy and resultParent(result) == req and
      resultVersion(result) == requestedVersion(req)
  pure def sumValue(_req: int): int = 6
  pure def factor(req: int): int = if (Set(other1, other2).contains(req)) 4 else 3
  pure def resultValue(_result: int): int = 18

  type Plan = { req: int, main: int }
  type Intent = { plan: Plan, result: int }
  type Source = { main: int, plan: Plan, local: int, stage: int, reuse: Intent, receipt: Intent }
  type Worker = { incoming: int, result: int }
  type Event = { command: str, before: Source, workerBefore: Worker, option: int, wanted: Intent,
    request: int, dispatched: int, outcome: str }
  pure val noPlan: Plan = { req: absent, main: absent }
  pure val noIntent: Intent = { plan: noPlan, result: absent }
  pure val occupied: Intent = { ...noIntent, result: movedMain }
  pure val empty: Source = { main: absent, plan: noPlan, local: absent, stage: absent,
    reuse: noIntent, receipt: noIntent }
  pure val noWorker: Worker = { incoming: absent, result: absent }
  pure val noEvent: Event = { command: "", before: empty, workerBefore: noWorker, option: omitted,
    wanted: noIntent, request: absent, dispatched: absent, outcome: "" }

  var source: Source
  var worker: Worker
  var phase: str
  var wantedPlan: Plan
  var call: str
  var wantedResult: int
  var event: Event

  action init = {
    nondet main = Set(absent, oldMain).oneOf()
    all { source' = { ...empty, main: main }, worker' = noWorker, phase' = "request", wantedPlan' = noPlan,
      call' = "", wantedResult' = absent, event' = noEvent }
  }

  action change(after: Source, worked: Worker, nextPhase: str, report: Event): bool = all {
    source' = after, worker' = worked, phase' = nextPhase, event' = report,
    wantedPlan' = wantedPlan, call' = call, wantedResult' = wantedResult
  }

  action record(option: int): bool = {
    val chosen = if (option == omitted) v1 else option
    val plan = if (supported(chosen)) { req: requestFor(chosen), main: source.main } else noPlan
    all {
      wantedPlan' = plan, source' = { ...source, plan: plan }, worker' = worker,
      phase' = if (plan == noPlan) "done" else "workerSetup", call' = call, wantedResult' = wantedResult,
      event' = { ...noEvent, command: "record", option: option, before: source,
        outcome: if (plan == noPlan) "reject" else "record" }
    }
  }

  // An unsupported request can come from import even though the planner rejects
  // creating it. The worker receives only the selected request ID and its pin.
  action work(req: int): bool = {
    val impl = requestedVersion(req)
    val dispatch = if (worker.incoming == req and worker.result == absent and supported(impl)) impl else absent
    val result = if (dispatch == v1) good1 else if (dispatch == v2) good2 else absent
    val after = if (result == absent) worker else { ...worker, result: result }
    change(source, after, "prepare", { ...noEvent, command: "work", before: source,
      workerBefore: worker, request: req, dispatched: dispatch, outcome: if (result == absent) "reject" else "work" })
  }

  // Set up one source call with an exact matching pin pair or one perturbation
  // at a time. The optional continuation sees actual effects of the first call,
  // not a new fixture (except possibly moving main independently).
  pure val calls = Set("stageReuse", "publish", "keyedPublish", "directReuse", "abandon")
  action prepare(command: str, result: int, variation: str): bool = {
    val alternatePlan = { ...wantedPlan, req: if (wantedPlan.req == request1) request2 else request1 }
    val local = if (variation == "movedResult") legacy else result
    val staging = if (command == "stageReuse") {
      if (variation == "occupied") result else absent
    } else local
    val configured = { ...source, local: local, stage: staging,
      plan: if (variation == "movedPlan") alternatePlan else source.plan,
      main: if (variation == "movedMain") movedMain else source.main,
      reuse: if (command == "directReuse" and variation == "occupied") occupied else noIntent,
      receipt: if (command == "keyedPublish" and variation == "occupied") occupied else noIntent }
    all {
      source' = configured, worker' = worker, phase' = "submit", event' = noEvent,
      wantedPlan' = wantedPlan, call' = command, wantedResult' = result
    }
  }

  action submit(command: str, result: int, nextPhase: str): bool = {
    val wanted = { plan: wantedPlan, result: result }
    val exactPlan = source.plan == wanted.plan
    val target = if (Set("publish", "keyedPublish").contains(command)) source.stage else source.local
    val exactResult = target == wanted.result and resultFits(result, wanted.plan.req)
    val currentMain = source.main == wanted.plan.main
    val consume = { ...source, plan: noPlan }
    val publish = { ...consume, main: result, stage: absent }
    val outcome = if (command == "keyedPublish" and source.receipt != noIntent) {
      if (source.receipt == wanted) "retry" else "reject"
    } else if (not(exactPlan)) "reject"
    else if (command == "abandon") "abandon"
    else if (not(exactResult)) "reject"
    else if (command == "stageReuse") {
      if (source.stage == absent) "stageReuse" else "reject"
    } else if (not(currentMain)) "reject"
    else if (command == "directReuse" and source.reuse != noIntent) "reject"
    else command
    val after = if (outcome == "stageReuse") { ...source, stage: result }
      else if (outcome == "directReuse") { ...consume, main: result, reuse: wanted }
      else if (outcome == "publish") publish
      else if (outcome == "keyedPublish") { ...publish, receipt: wanted }
      else if (outcome == "abandon") consume else source
    change(after, worker, nextPhase, { ...noEvent, command: command, before: source, wanted: wanted, outcome: outcome })
  }

  action step = if (event.command != "") change(source, worker, phase, noEvent)
    else if (phase == "request") {
      nondet option = Set(omitted, v1, v2, unknown).oneOf()
      record(option)
    } else if (phase == "workerSetup") {
      nondet incoming = Set(wantedPlan.req, other1, other2, unsupportedRequest).oneOf()
      change(source, { ...worker, incoming: incoming }, "work", noEvent)
    } else if (phase == "work") {
      nondet wanted = Set(wantedPlan.req, unsupportedRequest).oneOf()
      work(wanted)
    } else if (phase == "prepare") {
      nondet command = calls.oneOf()
      nondet result = results.oneOf()
      nondet variation = Set("none", "movedPlan", "movedResult", "movedMain", "occupied").oneOf()
      prepare(command, result, variation)
    } else if (phase == "submit") submit(call, wantedResult, "followup")
    else if (phase == "followup") any {
      nondet command = calls.oneOf()
      nondet result = Set(wantedResult, good1, good2).oneOf()
      submit(command, result, "done"),
      change({ ...source, main: movedMain }, worker, "last", noEvent)
    } else if (phase == "last") submit("keyedPublish", wantedResult, "done")
    else change(source, worker, "done", noEvent)

  // Expected IDs are enumerated independently of dispatch and fixture readers.
  val before = event.before
  val wanted = event.wanted
  val picking = event.command == "record"
  val working = event.command == "work"
  val submitting = calls.contains(event.command)
  val stagedReuse = event.command == "stageReuse"
  val directReuse = event.command == "directReuse"
  val keyed = event.command == "keyedPublish"
  val abandon = event.command == "abandon"
  val publishes = event.command == "publish" or keyed
  val rejects = event.outcome == "reject"
  val exactPlan = before.plan == wanted.plan
  val exactTarget = wanted.result == (if (publishes) before.stage else before.local)
  val exactMain = before.main == wanted.plan.main
  val rightPair = (wanted.plan.req == request1 and wanted.result == good1) or
    (wanted.plan.req == request2 and wanted.result == good2)
  val ready = exactPlan and exactTarget and (stagedReuse or exactMain) and
    (not(stagedReuse) or before.stage == absent) and (not(directReuse) or before.reuse == noIntent) and
    (not(keyed) or before.receipt == noIntent)

  invariant exactPlanning = not(picking) or (if (event.option == unknown)
    rejects and wantedPlan == noPlan and source == before
    else {
      val expected = { req: if (event.option == v2) request2 else request1, main: before.main }
      event.outcome == "record" and wantedPlan == expected and source == { ...before, plan: expected }
    })
  invariant exactWork = not(working) or {
    val input = event.workerBefore
    if (input.incoming == request1 and event.request == request1)
      event.outcome == "work" and event.dispatched == v1 and worker == { ...input, result: good1 }
    else if (input.incoming == request2 and event.request == request2)
      event.outcome == "work" and event.dispatched == v2 and worker == { ...input, result: good2 }
    else rejects and event.dispatched == absent and worker == input
  }
  invariant sameMathDistinctImplementations = all {
    good1 != good2,
    resultValue(good1) == sumValue(request1) * factor(request1),
    resultValue(good2) == sumValue(request2) * factor(request2),
    resultValue(good1) == resultValue(good2)
  }
  invariant exactResultSelection = not(submitting) or event.outcome == (
    if (keyed and before.receipt == wanted) "retry"
    else if (abandon and exactPlan) "abandon"
    else if (not(abandon) and ready and rightPair) event.command else "reject")
  invariant onlyCommittedWrites = not(submitting) or source == (
    if (event.outcome == "stageReuse") { ...before, stage: wanted.result }
    else if (event.outcome == "directReuse") { ...before, main: wanted.result, plan: noPlan, reuse: wanted }
    else if (event.outcome == "publish") { ...before, main: wanted.result, plan: noPlan, stage: absent }
    else if (event.outcome == "keyedPublish")
      { ...before, main: wanted.result, plan: noPlan, stage: absent, receipt: wanted }
    else if (event.outcome == "abandon") { ...before, plan: noPlan } else before)

  observation omittedSelectsV1 = picking and event.option == omitted and source.plan.req == request1
  observation explicitV1SelectsSameRequest = picking and event.option == v1 and source.plan.req == request1
  observation unsupportedOptionRejected = picking and event.option == unknown and rejects
  observation workerExecutesV1 = working and event.dispatched == v1 and worker.result == good1
  observation workerExecutesV2 = working and event.dispatched == v2 and worker.result == good2
  observation unsupportedStagedRequestNeverExecutes = working and event.request == unsupportedRequest and
    event.workerBefore.incoming == event.request and rejects and event.dispatched == absent
  observation otherSameVersionWorkerInputRejected = working and event.request == request2 and
    event.workerBefore.incoming == other2 and rejects and event.dispatched == absent
  observation workerV2ResultPublished = event.outcome == "publish" and worker.result == good2 and wanted.result == good2
  observation stageV2AfterMainMoves = event.outcome == "stageReuse" and wanted.result == good2 and not(exactMain)
  observation directV2ConsumesPlanButNotStage = event.outcome == "directReuse" and wanted.result == good2 and
    source.stage == good2 and source.plan == noPlan
  val wrongVersion = (wanted.plan.req == request1 and wanted.result == wrongVersion1) or
    (wanted.plan.req == request2 and wanted.result == wrongVersion2)
  val wrongParent = (wanted.plan.req == request1 and wanted.result == wrongParent1) or
    (wanted.plan.req == request2 and wanted.result == wrongParent2)
  observation publishRejectsWrongVersion = publishes and ready and wrongVersion and rejects
  observation stagingReuseRejectsWrongVersion = stagedReuse and ready and wrongVersion and rejects
  observation directReuseRejectsWrongVersion = directReuse and ready and wrongVersion and rejects
  observation publishRejectsWrongParent = publishes and ready and wrongParent and rejects
  observation stagingReuseRejectsWrongParent = stagedReuse and ready and wrongParent and rejects
  observation directReuseRejectsWrongParent = directReuse and ready and wrongParent and rejects
  observation staleV2MainBlocksPublication = publishes and not(exactMain) and exactPlan and exactTarget and
    wanted.result == good2 and rightPair and before.receipt == noIntent and rejects
  observation movedPlanBlocksV2Selection = directReuse and not(exactPlan) and before.plan != noPlan and
    exactMain and exactTarget and wanted.result == good2 and rightPair and rejects
  observation movedResultBlocksV2Selection = directReuse and exactPlan and not(exactTarget) and
    exactMain and wanted.result == good2 and rightPair and rejects
  observation sameV2StageCannotBeRecreated = stagedReuse and exactPlan and exactTarget and
    wanted.result == good2 and rightPair and before.stage == good2 and rejects
  observation occupiedReuseRefBlocksV2 = directReuse and exactPlan and exactTarget and exactMain and
    wanted.result == good2 and rightPair and before.reuse == occupied and rejects
  observation v2ReceiptRetryAfterMainMoves = keyed and event.outcome == "retry" and wanted.result == good2 and
    before.main == movedMain and before.plan == noPlan and before.stage == absent
  observation v2ReceiptCannotAcknowledgeAnotherResult = keyed and rejects and before.receipt.result == good2 and
    before.receipt.plan == wanted.plan and wanted.result == good1
  observation v2AbandonedDespiteMainMove = event.outcome == "abandon" and wanted.plan.req == request2 and
    not(exactMain) and source.plan == noPlan
  observation v2RemovedPlanCannotPublish = publishes and rejects and before.plan == noPlan and
    exactMain and exactTarget and rightPair and wanted.result == good2
}
