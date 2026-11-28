// Save an execution occurrence without changing the deterministic requested result.
module recorded_attempt_design {
  // Two supported request versions, two valid UUIDv4 symbols, two worker outputs,
  // and one origin ref per role plus a bystander attempt. Structural values stand
  // for content IDs: record fields stand for ordered parents and fixed DAG values.
  // Names are fixed and distinct; packing, UUID syntax, arithmetic, native faults,
  // and other ref aliases are not modeled. All result fixtures have equal output.
  // Safety only: bounded transactions with one perturbation per setup step.
  pure val absent = 0
  pure val oldMain = 1
  pure val movedMain = 2
  pure val req1 = 10
  pure val req2 = 11
  pure val otherReq = 12 // A distinct @2 request, not selectable for req2.
  pure val unknownReq = 13
  pure val result1 = 20
  pure val result2 = 21
  pure val otherResult = 22 // @2, same output, wrong request parent.
  pure val wrongImpl = 23 // Exact req2 parent, but records @1.
  pure val uuidA = "A"
  pure val uuidB = "B"
  pure val invalidUuid = "invalid"

  pure def version(request: int): int =
    if (request == req1) 1 else if (Set(req2, otherReq).contains(request)) 2 else 0
  pure def resultFor(request: int): int =
    if (request == req1) result1 else if (request == req2) result2
    else if (request == otherReq) otherResult else absent
  pure def resultRequest(result: int): int =
    if (result == result1) req1 else if (Set(result2, wrongImpl).contains(result)) req2
    else if (result == otherResult) otherReq else absent
  pure def resultVersion(result: int): int =
    if (Set(result1, wrongImpl).contains(result)) 1 else if (Set(result2, otherResult).contains(result)) 2 else 0
  pure def matches(request: int, result: int): bool = version(request) != 0 and
    resultRequest(result) == request and resultVersion(result) == version(request)
  pure def canonical(uuid: str): bool = Set(uuidA, uuidB).contains(uuid)

  type Plan = { request: int, tip: int }
  type Attempt = { request: int, result: int, uuid: str }
  // The historical ref name literal is fixed per layout and is never resolved.
  type Selection = { kind: str, request: int, attempt: Attempt, legacyResult: int }
  type Reuse = { plan: Plan, selection: Selection }
  type Worker = { incoming: int, first: Attempt, second: Attempt, legacy: int }
  type Origin = { main: int, plan: Plan, returned: Attempt, bystander: Attempt, chosen: Selection, reuse: Reuse }
  type World = { worker: Worker, origin: Origin, bundle: Attempt }
  type Event = { op: str, snapshot: World, plan: Plan, attempt: Attempt, selection: Selection,
    slot: int, ok: bool }
  type Reach = { plans: Set[Plan], selections: Set[Selection], attempts: Set[Attempt],
    results: Set[int], requests: Set[int], tips: Set[int] }
  pure val noPlan: Plan = { request: absent, tip: absent }
  pure val noAttempt: Attempt = { request: absent, result: absent, uuid: "" }
  pure val noSelection: Selection = { kind: "", request: absent, attempt: noAttempt, legacyResult: absent }
  pure val noReuse: Reuse = { plan: noPlan, selection: noSelection }
  pure val empty: Origin = { main: absent, plan: noPlan, returned: noAttempt, bystander: noAttempt,
    chosen: noSelection, reuse: noReuse }
  pure val blank: World = { worker: { incoming: absent, first: noAttempt, second: noAttempt, legacy: absent },
    origin: empty, bundle: noAttempt }
  pure val noEvent: Event = { op: "", snapshot: blank, plan: noPlan, attempt: noAttempt, selection: noSelection,
    slot: 0, ok: false }
  pure val noReach: Reach = { plans: Set(), selections: Set(), attempts: Set(), results: Set(),
    requests: Set(), tips: Set() }
  pure def attemptFor(request: int, uuid: str): Attempt = { request: request, result: resultFor(request), uuid: uuid }
  pure def chooseFor(plan: Plan, attempt: Attempt): Selection =
    { kind: "attempt", request: plan.request, attempt: attempt, legacyResult: absent }
  pure def fits(request: int, attempt: Attempt): bool = attempt.request == request and canonical(attempt.uuid) and
    matches(request, attempt.result)
  pure def target(worker: Worker, slot: int): Attempt = if (slot == 1) worker.first else worker.second

  var phase: str
  var original: Plan
  var world: World
  var event: Event
  var retained: Reach

  action init = {
    nondet request = Set(req1, req2).oneOf()
    nondet tip = Set(absent, oldMain).oneOf()
    val plan = { request: request, tip: tip }
    all {
      original' = plan, phase' = "workSetup", event' = noEvent, retained' = noReach,
      world' = { ...blank, worker: { ...blank.worker, incoming: request, legacy: resultFor(request) },
        origin: { ...empty, main: tip, plan: plan } }
    }
  }

  action progress(after: World, nextPhase: str, report: Event): bool = all {
    world' = after, phase' = nextPhase, event' = report, original' = original, retained' = retained
  }

  action work(request: int, uuid: str, slot: int): bool = {
    val candidate = attemptFor(request, uuid)
    val worker = world.worker
    val ok = worker.incoming == request and version(request) != 0 and canonical(uuid) and
      target(worker, slot) == noAttempt
    val worked = if (not(ok)) worker else if (slot == 1) { ...worker, first: candidate }
      else { ...worker, second: candidate }
    val nextPhase = if (not(ok)) "done" else if (slot == 1) "workAgain"
      else if (worked.first == worked.second) "done" else "export"
    progress({ ...world, worker: worked }, nextPhase,
      { ...noEvent, op: "work", snapshot: world, attempt: candidate, slot: slot, ok: ok })
  }

  action exportAttempt(slot: int): bool = {
    val expected = world.worker.first
    val ok = target(world.worker, slot) == expected and fits(expected.request, expected)
    progress(if (ok) { ...world, bundle: expected } else world, if (ok) "stage" else "done",
      { ...noEvent, op: "export", snapshot: world, attempt: expected, slot: slot, ok: ok })
  }

  action selectAttempt(plan: Plan, attempt: Attempt): bool = {
    val source = world.origin
    val selection = chooseFor(plan, attempt)
    val ok = source.plan == plan and source.returned == attempt and source.chosen == noSelection and
      fits(plan.request, attempt)
    val after = if (ok) { ...world, origin: { ...source, chosen: selection } } else world
    progress(after, if (ok) "publishSetup" else "done",
      { ...noEvent, op: "select", snapshot: world, plan: plan, attempt: attempt, selection: selection, ok: ok })
  }

  action publish(plan: Plan, selection: Selection): bool = {
    val source = world.origin
    val result = if (selection.kind == "attempt") selection.attempt.result else selection.legacyResult
    val valid = if (selection.kind == "attempt") fits(selection.request, selection.attempt)
      else selection.kind == "result" and matches(selection.request, result)
    val ok = source.plan == plan and source.chosen == selection and source.main == plan.tip and
      source.reuse == noReuse and plan.request == selection.request and valid
    val published = { ...source, main: result, plan: noPlan, reuse: { plan: plan, selection: selection } }
    progress(if (ok) { ...world, origin: published } else world, if (ok) "collectReuse" else "done",
      { ...noEvent, op: "publish", snapshot: world, plan: plan, selection: selection, ok: ok })
  }

  // Transfer is staging the exact bundle root, not a second execution. Its
  // abstract closure includes the selected attempt's request/result. The
  // independently staged bystander is present on the origin before collection.
  action stage = progress({ ...world, origin: { ...world.origin, returned: world.bundle,
    bystander: world.worker.second } }, "selectSetup", noEvent)

  // Sole-root GC: follow directed parent edges rather than search by request,
  // UUID or result. Request producer edges and non-commit objects are elided.
  pure def closure(source: Origin): Reach = {
    val plans = Set(source.plan, source.reuse.plan).exclude(Set(noPlan))
    val selections = Set(source.chosen, source.reuse.selection).exclude(Set(noSelection))
    val attempts = Set(source.returned, source.bystander).union(selections.map(s => s.attempt)).exclude(Set(noAttempt))
    val results = attempts.map(a => a.result).union(selections.map(s => s.legacyResult)).exclude(Set(absent))
    val requests = plans.map(p => p.request).union(selections.map(s => s.request))
      .union(attempts.map(a => a.request)).union(results.map(resultRequest)).exclude(Set(absent))
    val tips = plans.map(p => p.tip).union(Set(source.main)).exclude(Set(absent))
    { plans: plans, selections: selections, attempts: attempts, results: results, requests: requests, tips: tips }
  }

  // Exercise normal publication after both staged attempts have been unpinned
  // and collected, while the plan/main precondition still holds.
  action collectBeforePublish = {
    val source = { ...world.origin, returned: noAttempt, bystander: noAttempt }
    all {
      world' = { ...world, origin: source }, retained' = closure(source), phase' = "publish", original' = original,
      event' = { ...noEvent, op: "prepareGc", snapshot: world }
    }
  }

  action collect(reuse: bool): bool = {
    val source = if (reuse) { ...empty, reuse: world.origin.reuse } else { ...empty, chosen: world.origin.chosen }
    all {
      world' = { ...world, origin: source }, retained' = closure(source), phase' = "done", original' = original,
      event' = { ...noEvent, op: "collect", snapshot: world }
    }
  }

  action step = if (phase == "workSetup") {
    nondet variation = Set("normal", "wrongPin", "unknown", "occupied").oneOf()
    val worker = world.worker
    val configured = if (variation == "wrongPin") { ...worker, incoming: otherReq }
      else if (variation == "unknown") { ...worker, incoming: unknownReq }
      else if (variation == "occupied") { ...worker, first: attemptFor(original.request, uuidA) }
      else worker
    progress({ ...world, worker: configured }, "work", noEvent)
  } else if (phase == "work") {
    nondet uuid = Set(uuidA, invalidUuid).oneOf()
    work(if (world.worker.incoming == unknownReq) unknownReq else original.request, uuid, 1)
  } else if (phase == "workAgain") {
    nondet uuid = Set(uuidA, uuidB).oneOf()
    nondet slot = Set(1, 2).oneOf()
    work(original.request, uuid, slot)
  } else if (phase == "export") {
    nondet slot = Set(1, 2).oneOf()
    exportAttempt(slot)
  } else if (phase == "stage") stage
  else if (phase == "selectSetup") {
    nondet variation = Set("normal", "pickSecond", "staleMain", "stalePlan", "movedAttempt", "occupied",
      "otherRequest", "wrongInnerRequest", "wrongImplementation", "badUuid").oneOf()
    val source = world.origin
    val first = source.returned
    val prepared = if (variation == "pickSecond") { ...source, returned: source.bystander, bystander: first }
      else if (variation == "staleMain") { ...source, main: movedMain }
      else if (variation == "stalePlan") { ...source, plan: { ...original, tip: movedMain } }
      else if (variation == "movedAttempt") { ...source, returned: source.bystander }
      else if (variation == "occupied") { ...source, chosen: chooseFor(original, first) }
      else if (variation == "otherRequest") { ...source, returned: attemptFor(otherReq, uuidA) }
      else if (variation == "wrongInnerRequest") { ...source, returned: { ...first, result: otherResult } }
      else if (variation == "wrongImplementation" and original.request == req2)
        { ...source, returned: { ...first, result: wrongImpl } }
      else if (variation == "badUuid") { ...source, returned: { ...first, uuid: invalidUuid } }
      else source
    progress({ ...world, origin: prepared }, if (variation == "movedAttempt") "selectOld" else "select", noEvent)
  } else if (phase == "select" or phase == "selectOld") {
    selectAttempt(original, if (phase == "selectOld") world.bundle else world.origin.returned)
  } else if (phase == "publishSetup") any {
    collect(false),
    all { world.origin.main == world.origin.plan.tip, collectBeforePublish },
    nondet variation = Set("normal", "dropAttempts", "moveAttemptPin", "staleMain", "removedPlan", "stalePlan",
      "newPlan", "occupied", "movedSelection", "legacy", "wrongSelectionRequest", "wrongInnerRequest",
      "wrongImplementation", "malformedSelection").oneOf()
    val source = world.origin
    val selected = source.chosen
    val chosen = if (variation == "movedSelection") { ...selected, attempt: source.bystander }
      else if (variation == "legacy") { ...noSelection, kind: "result", request: selected.request,
        legacyResult: selected.attempt.result }
      else if (variation == "wrongSelectionRequest") { ...selected, request: otherReq }
      else if (variation == "wrongInnerRequest") { ...selected, attempt: { ...selected.attempt, result: otherResult } }
      else if (variation == "wrongImplementation" and original.request == req2)
        { ...selected, attempt: { ...selected.attempt, result: wrongImpl } }
      else if (variation == "malformedSelection") { ...selected, kind: "malformed" }
      else selected
    val updated = { ...source, chosen: chosen }
    val refreshed = { ...original, tip: movedMain }
    val prepared = if (variation == "dropAttempts") { ...updated, returned: noAttempt, bystander: noAttempt }
      else if (variation == "moveAttemptPin") { ...updated, returned: source.bystander }
      else if (variation == "staleMain") { ...updated, main: movedMain }
      else if (variation == "removedPlan") { ...updated, plan: noPlan }
      else if (variation == "stalePlan") { ...updated, plan: refreshed }
      else if (variation == "newPlan") { ...updated, main: movedMain, plan: refreshed }
      else if (variation == "occupied") { ...updated, reuse: { plan: original, selection: selected } }
      else updated
    val nextPhase = if (variation == "movedSelection") "publishOld"
      else if (variation == "newPlan") "publishNew" else "publish"
    progress({ ...world, origin: prepared }, nextPhase,
      if (nextPhase == "publishOld") { ...noEvent, selection: selected } else noEvent)
  } else if (Set("publish", "publishOld", "publishNew").contains(phase)) {
    publish(if (phase == "publishNew") world.origin.plan else original,
      if (phase == "publishOld") event.selection else world.origin.chosen)
  } else if (phase == "collectReuse") collect(true)
  else progress(world, "done", noEvent)

  // Independent fixture oracle: eligible request/result pairs are enumerated,
  // not computed with the readers or record constructors used by the actions.
  pure def eligible(request: int, result: int): bool =
    (request == req1 and result == result1) or (request == req2 and result == result2) or
    (request == otherReq and result == otherResult)
  pure def validAttempt(request: int, attempt: Attempt): bool = attempt.request == request and
    eligible(request, attempt.result) and (attempt.uuid == uuidA or attempt.uuid == uuidB)
  val prior = event.snapshot
  val source = prior.origin
  val attemptArg = event.attempt
  val planArg = event.plan
  val selectionArg = event.selection
  val exactPlan = source.plan == planArg
  val exactChosen = source.chosen == selectionArg
  val exactAttempt = source.returned == attemptArg
  val exactMain = source.main == planArg.tip
  val selecting = event.op == "select"
  val publishing = event.op == "publish"
  val collecting = event.op == "collect"
  val accepted = event.ok
  val selectReady = exactPlan and exactAttempt and source.chosen == noSelection
  val publishReady = exactPlan and exactChosen and exactMain and source.reuse == noReuse
  val publishedResult = if (selectionArg.kind == "attempt") selectionArg.attempt.result else selectionArg.legacyResult
  val validSelection = selectionArg.request == planArg.request and (
    (selectionArg.kind == "attempt" and validAttempt(planArg.request, selectionArg.attempt)) or
    (selectionArg.kind == "result" and eligible(planArg.request, selectionArg.legacyResult)))

  invariant workUsesExactRequestAndFreshOutput = event.op != "work" or {
    val input = prior.worker
    val free = if (event.slot == 1) input.first == noAttempt else input.second == noAttempt
    val expectedResult = if (attemptArg.request == req1) result1 else result2
    val expected = { request: attemptArg.request, result: expectedResult, uuid: attemptArg.uuid }
    (accepted iff (free and input.incoming == attemptArg.request and Set(req1, req2).contains(input.incoming) and
      Set(uuidA, uuidB).contains(attemptArg.uuid))) and (not(accepted) or {
      val worker = if (event.slot == 1) { ...input, first: expected } else { ...input, second: expected }
      world == { ...prior, worker: worker } and expected.result == input.legacy
    })
  }
  invariant exportKeepsExactOccurrence = event.op != "export" or all {
    accepted iff event.slot == 1,
    not(accepted) or world == { ...prior, bundle: prior.worker.first }
  }
  invariant stagingKeepsExactOccurrence = phase != "selectSetup" or
    (world.origin.returned == world.bundle and world.bundle == world.worker.first and
      world.origin.bystander == world.worker.second)
  invariant onlySelectionCreation = not(selecting) or all {
    accepted iff (selectReady and validAttempt(planArg.request, attemptArg)),
    not(accepted) or world == { ...prior, origin: { ...source, chosen: { kind: "attempt",
      request: planArg.request, attempt: attemptArg, legacyResult: absent } } }
  }
  invariant publishesOriginalResultButRetainsExactSelection = not(publishing) or all {
    accepted iff (publishReady and validSelection),
    not(accepted) or world == { ...prior, origin: { ...source, main: publishedResult, plan: noPlan,
      reuse: { plan: planArg, selection: selectionArg } } }
  }
  invariant rejectionsAreAtomic = not(Set("work", "export", "select", "publish").contains(event.op)) or
    accepted or world == prior
  invariant collectionPreservesExactChoice = event.op != "prepareGc" or all {
    world == { ...prior, origin: { ...source, returned: noAttempt, bystander: noAttempt } },
    retained.plans == Set(source.plan),
    retained.selections == Set(source.chosen),
    retained.attempts == Set(source.chosen.attempt),
    retained.results == Set(source.chosen.attempt.result),
    retained.requests == Set(source.chosen.request)
  }
  invariant soleRootRetainsOnlySelectedEvidence = not(collecting) or {
    val reuse = source.reuse != noReuse
    val selected = if (reuse) source.reuse.selection else source.chosen
    val result = if (selected.kind == "attempt") selected.attempt.result else selected.legacyResult
    world.origin == (if (reuse) { ...empty, reuse: source.reuse } else { ...empty, chosen: source.chosen }) and
      retained == { plans: if (reuse) Set(source.reuse.plan) else Set(), selections: Set(selected),
        attempts: if (selected.kind == "attempt") Set(selected.attempt) else Set(), results: Set(result),
        requests: Set(selected.request),
        tips: if (reuse and source.reuse.plan.tip != absent) Set(source.reuse.plan.tip) else Set() }
  }

  observation v1UsesUnchangedResult = event.op == "work" and accepted and attemptArg.request == req1
  observation v2UsesSavedVersion = event.op == "work" and accepted and attemptArg.request == req2
  observation twoOccurrencesShareResult = event.op == "work" and accepted and event.slot == 2 and
    world.worker.first != world.worker.second and world.worker.first.result == world.worker.second.result
  observation duplicateUuidFreshRefSameCommit = event.op == "work" and accepted and event.slot == 2 and
    world.worker.first == world.worker.second
  observation occupiedAttemptRejectsEvenSameCommit = event.op == "work" and not(accepted) and event.slot == 1 and
    prior.worker.first == attemptArg and prior.worker.incoming == attemptArg.request
  observation invalidUuidRejected = event.op == "work" and not(accepted) and attemptArg.uuid == invalidUuid and
    prior.worker.incoming == attemptArg.request and attemptArg.request == req2 and prior.worker.first == noAttempt
  observation wrongPinnedRequestRejected = event.op == "work" and not(accepted) and attemptArg.request == req2 and
    prior.worker.incoming == otherReq and attemptArg.uuid == uuidA and prior.worker.first == noAttempt
  observation unsupportedRequestRejected = event.op == "work" and not(accepted) and
    attemptArg.request == unknownReq and prior.worker.incoming == unknownReq and attemptArg.uuid == uuidA
  observation exportRejectsMovedSameResult = event.op == "export" and not(accepted) and event.slot == 2 and
    prior.worker.second.result == attemptArg.result and prior.worker.second != attemptArg
  observation staleMainDoesNotBlockChoice = selecting and accepted and not(exactMain)
  observation alternateOccurrenceCanBeChosen = selecting and accepted and attemptArg == prior.worker.second
  observation selectRefusesMovedSameResult = selecting and not(accepted) and not(exactAttempt) and exactPlan and
    source.chosen == noSelection and source.returned.result == attemptArg.result and
    validAttempt(planArg.request, source.returned) and validAttempt(planArg.request, attemptArg)
  observation selectRefusesOccupiedChoice = selecting and not(accepted) and exactPlan and exactAttempt and
    source.chosen == selectionArg and validAttempt(planArg.request, attemptArg)
  observation selectRefusesOtherRequest = selecting and selectReady and not(accepted) and
    attemptArg.request == otherReq and planArg.request == req2
  observation selectRefusesWrongResultRequest = selecting and selectReady and not(accepted) and
    attemptArg.request == planArg.request and planArg.request == req2 and attemptArg.result == otherResult
  observation selectRefusesWrongVersion = selecting and selectReady and not(accepted) and attemptArg.result == wrongImpl
  observation publishWithoutAttemptPins = publishing and accepted and source.returned == noAttempt and
    source.bystander == noAttempt and selectionArg.kind == "attempt"
  observation publishAfterCollection = publishing and accepted and source.returned == noAttempt and
    source.bystander == noAttempt and retained.attempts == Set(selectionArg.attempt)
  observation publishWithMovedAttemptPin = publishing and accepted and selectionArg.kind == "attempt" and
    source.returned != selectionArg.attempt and source.returned.result == selectionArg.attempt.result
  observation publishFromNewPlan = publishing and accepted and planArg != original and selectionArg.kind == "attempt"
  observation legacySelectionStillPublishes = publishing and accepted and selectionArg.kind == "result"
  observation publishRefusesMovedSameResultChoice = publishing and not(accepted) and exactPlan and exactMain and
    not(exactChosen) and source.reuse == noReuse and validSelection and source.chosen.kind == "attempt" and
    validAttempt(planArg.request, source.chosen.attempt) and source.chosen.attempt.result == selectionArg.attempt.result
  observation publishRefusesStaleMain = publishing and not(accepted) and exactPlan and exactChosen and not(exactMain) and
    source.reuse == noReuse and validSelection
  observation publishRefusesOccupiedReuse = publishing and not(accepted) and exactPlan and exactChosen and exactMain and
    validSelection and source.reuse == { plan: planArg, selection: selectionArg }
  observation publishRefusesWrongSelectionRequest = publishing and publishReady and not(accepted) and
    selectionArg.request == otherReq and validAttempt(planArg.request, selectionArg.attempt)
  observation publishRefusesWrongResultRequest = publishing and publishReady and not(accepted) and
    selectionArg.request == planArg.request and selectionArg.attempt.request == req2 and publishedResult == otherResult
  observation publishRefusesWrongVersion = publishing and publishReady and not(accepted) and publishedResult == wrongImpl
  observation publishRefusesMalformedLayout = publishing and publishReady and not(accepted) and
    selectionArg.kind == "malformed" and validAttempt(planArg.request, selectionArg.attempt)
  observation choiceAloneExcludesOtherOccurrence = collecting and source.reuse == noReuse and
    source.bystander != noAttempt and source.bystander.result == source.chosen.attempt.result and
    retained.attempts == Set(source.chosen.attempt) and not(retained.attempts.contains(source.bystander))
  observation reuseAloneExcludesOtherOccurrence = collecting and source.reuse != noReuse and
    source.bystander != noAttempt and source.bystander.result == source.reuse.selection.attempt.result and
    retained.attempts == Set(source.reuse.selection.attempt) and not(retained.attempts.contains(source.bystander))
}
