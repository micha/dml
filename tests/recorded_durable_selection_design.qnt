// Record a result selection now; use it with an exact plan in a separate transaction.
module recorded_durable_selection_design {
  // One ref per role, with disjoint fixed names. Values model content IDs or
  // exact immutable fields, not packed objects. Imports/other writers can move
  // pins between calls. The historical result-ref name is fixed, so selection
  // IDs differ by request, result or layout here. No transfer, GC or native faults.
  pure val absent = 0
  pure val oldMain = 1
  pure val movedMain = 2
  pure val requestV1 = 10
  pure val requestV2 = 11
  pure val otherRequestV2 = 12
  pure val resultV1 = 20
  pure val resultV2 = 21
  pure val otherResultV2 = 22 // Another structurally valid result for the exact request.
  pure val wrongImplementation = 23 // Exact @2 parent, but records @1.
  pure val wrongRequest = 24 // @2 with the same output, but a different request parent.
  pure val candidates = Set(resultV1, resultV2, otherResultV2, wrongImplementation, wrongRequest)

  pure def version(request: int): int = if (request == requestV1) 1 else 2
  pure def parent(result: int): int =
    if (result == resultV1) requestV1 else if (result == wrongRequest) otherRequestV2 else requestV2
  pure def implementation(result: int): int = if (Set(resultV1, wrongImplementation).contains(result)) 1 else 2
  pure def fits(request: int, result: int): bool =
    candidates.contains(result) and parent(result) == request and implementation(result) == version(request)

  type Plan = { request: int, main: int }
  type Selection = { request: int, result: int, layout: bool }
  type Reuse = { plan: Plan, selection: Selection }
  type Refs = { main: int, plan: Plan, result: int, selection: Selection, reuse: Reuse }
  type Event = { op: str, before: Refs, plan: Plan, result: int, selection: Selection, accepted: bool }
  pure val noPlan: Plan = { request: absent, main: absent }
  pure val noSelection: Selection = { request: absent, result: absent, layout: false }
  pure val noReuse: Reuse = { plan: noPlan, selection: noSelection }
  pure val empty: Refs = { main: absent, plan: noPlan, result: absent, selection: noSelection, reuse: noReuse }
  pure val noEvent: Event = { op: "", before: empty, plan: noPlan, result: absent,
    selection: noSelection, accepted: false }
  pure def selectionFor(request: int, result: int): Selection = { request: request, result: result, layout: true }

  var refs: Refs
  var phase: str
  var originalPlan: Plan
  var event: Event

  action init = {
    nondet request = Set(requestV1, requestV2).oneOf()
    nondet main = Set(absent, oldMain).oneOf()
    nondet result = candidates.oneOf()
    val plan = { request: request, main: main }
    all { refs' = { ...empty, main: main, plan: plan, result: result }, originalPlan' = plan,
      phase' = "selectSetup", event' = noEvent }
  }

  action change(after: Refs, nextPhase: str, report: Event): bool = all {
    refs' = after, phase' = nextPhase, originalPlan' = originalPlan, event' = report
  }

  action chooseResult(plan: Plan, result: int): bool = {
    val selection = selectionFor(plan.request, result)
    val accepted = refs.plan == plan and refs.result == result and refs.selection == noSelection and
      fits(plan.request, result)
    val after = if (accepted) { ...refs, selection: selection } else refs
    change(after, "afterSelect", { ...noEvent, op: "select", before: refs, plan: plan,
      result: result, selection: selection, accepted: accepted })
  }

  action publish(plan: Plan, selection: Selection): bool = {
    val reuse = { plan: plan, selection: selection }
    val result = selection.result
    val accepted = refs.plan == plan and refs.selection == selection and selection.layout and
      selection.request == plan.request and fits(selection.request, result) and
      refs.main == plan.main and refs.reuse == noReuse
    val after = if (accepted) { ...refs, main: result, plan: noPlan, reuse: reuse } else refs
    change(after, "done", { ...noEvent, op: "publish", before: refs, plan: plan,
      result: result, selection: selection, accepted: accepted })
  }

  action step = if (phase == "selectSetup") {
    nondet variation = Set("none", "newMain", "newPlan", "noPlan", "occupied").oneOf()
    val after = if (variation == "newMain") { ...refs, main: movedMain }
      else if (variation == "newPlan") { ...refs, plan: { ...originalPlan, main: movedMain } }
      else if (variation == "noPlan") { ...refs, plan: noPlan }
      else if (variation == "occupied") { ...refs, selection: selectionFor(originalPlan.request, refs.result) }
      else refs
    change(after, "select", noEvent)
  } else if (phase == "select") {
    nondet result = candidates.oneOf()
    chooseResult(originalPlan, result)
  } else if (phase == "afterSelect") {
    // Either carry forward the actual recorded selection, or install an independent
    // or malformed record, as from transfer or a raw repository writer.
    nondet selection = Set(refs.selection, selectionFor(requestV1, resultV1), selectionFor(requestV2, resultV2),
      selectionFor(requestV2, otherResultV2), selectionFor(requestV2, wrongImplementation),
      selectionFor(requestV2, wrongRequest), selectionFor(requestV2, resultV1),
      { ...selectionFor(requestV2, resultV2), layout: false }).oneOf()
    nondet state = Set("keep", "dropResult", "replaceResult", "moveMain", "newPlan", "abandon").oneOf()
    val after = if (state == "dropResult") { ...refs, result: absent }
      else if (state == "replaceResult") { ...refs, result: wrongImplementation }
      else if (state == "moveMain") { ...refs, main: movedMain }
      else if (state == "newPlan") { ...refs, main: movedMain, result: absent,
        plan: { ...originalPlan, main: movedMain } }
      else if (state == "abandon") { ...refs, plan: noPlan } else refs
    nondet reuse = Set(noReuse, { plan: after.plan, selection: selection }).oneOf()
    change({ ...after, selection: selection, reuse: reuse }, "publish", noEvent)
  } else if (phase == "publish") {
    nondet plan = Set(originalPlan, { ...originalPlan, main: movedMain }).oneOf()
    nondet selection = Set(refs.selection, selectionFor(requestV1, resultV1), selectionFor(requestV2, resultV2),
      selectionFor(requestV2, otherResultV2)).oneOf()
    publish(plan, selection)
  } else change(refs, "done", noEvent)

  // Independent contract enumerates eligible pairs; no numeric result predicate.
  pure def eligible(request: int, result: int): bool =
    (request == requestV1 and result == resultV1) or
    (request == requestV2 and Set(resultV2, otherResultV2).contains(result))
  val before = event.before
  val checkingSelect = event.op == "select"
  val checkingPublish = event.op == "publish"
  val exactPlan = before.plan == event.plan
  val exactSelection = before.selection == event.selection
  val correctMain = before.main == event.plan.main
  val exactResult = before.result == event.result
  val goodResult = eligible(event.plan.request, event.result)
  val validSelection = event.selection.layout and event.selection.request == event.plan.request
  val accepted = event.accepted
  val rejected = not(accepted)
  val selectReady = exactPlan and exactResult and before.selection == noSelection
  val publishReady = exactPlan and exactSelection and correctMain and before.reuse == noReuse

  invariant exactSelectionCreation = not(checkingSelect) or accepted == (selectReady and goodResult)
  invariant guardedPublication = not(checkingPublish) or accepted == (publishReady and validSelection and goodResult)
  invariant onlyIntendedChanges = if (checkingSelect and accepted) refs == { ...before,
    selection: { request: event.plan.request, result: event.result, layout: true } }
    else if (checkingPublish and accepted) refs == { ...before, main: event.selection.result, plan: noPlan,
      reuse: { plan: event.plan, selection: event.selection } }
    else not(checkingSelect or checkingPublish) or refs == before

  observation v1Selectable = checkingSelect and accepted and event.result == resultV1
  observation v2Selectable = checkingSelect and accepted and event.result == resultV2
  observation otherExactV2Selectable = checkingSelect and accepted and event.result == otherResultV2
  observation chooseWithStaleMain = checkingSelect and accepted and not(correctMain)
  observation cannotReplaceEvenSameSelection = checkingSelect and rejected and exactPlan and exactResult and
    goodResult and exactSelection
  observation staleCreationPlan = checkingSelect and rejected and not(exactPlan) and exactResult and goodResult and
    before.plan != noPlan and before.selection == noSelection
  observation staleOriginalResult = checkingSelect and rejected and not(exactResult) and exactPlan and goodResult and
    before.selection == noSelection
  observation selectRejectsWrongRequest = checkingSelect and selectReady and event.plan.request == requestV2 and
    event.result == wrongRequest and rejected
  observation selectRejectsWrongImplementation = checkingSelect and selectReady and event.plan.request == requestV2 and
    event.result == wrongImplementation and rejected
  observation selectRejectsOtherVersion = checkingSelect and selectReady and event.plan.request == requestV2 and
    event.result == resultV1 and rejected
  observation publishWithoutResultPin = checkingPublish and accepted and before.result == absent
  observation publishWithMovedResultPin = checkingPublish and accepted and before.result == wrongImplementation
  observation publishFromNewPlan = checkingPublish and accepted and event.plan != originalPlan and before.result == absent
  observation publishReplacingMain = checkingPublish and accepted and before.main == movedMain
  observation publishRefusesMovedMain = checkingPublish and rejected and not(correctMain) and exactPlan and
    exactSelection and validSelection and goodResult and before.reuse == noReuse
  observation publishRefusesAbandonedPlan = checkingPublish and rejected and before.plan == noPlan and correctMain and
    exactSelection and validSelection and goodResult and before.reuse == noReuse
  observation publishRefusesSameRequestMovedSelection = checkingPublish and rejected and not(exactSelection) and
    before.selection.layout and before.selection.request == event.selection.request and
    eligible(event.plan.request, before.selection.result) and validSelection and goodResult and exactPlan and
    correctMain and before.reuse == noReuse
  observation publishRefusesOccupiedReuse = checkingPublish and rejected and exactPlan and exactSelection and
    correctMain and validSelection and goodResult and before.reuse == { plan: event.plan, selection: event.selection }
  observation publishRefusesOtherVersionSelection = checkingPublish and rejected and publishReady and
    event.plan.request == requestV2 and event.selection == selectionFor(requestV1, resultV1)
  observation publishRefusesWrongResultRequest = checkingPublish and rejected and publishReady and validSelection and
    event.result == wrongRequest
  observation publishRefusesWrongResultVersion = checkingPublish and rejected and publishReady and validSelection and
    event.result == wrongImplementation
  observation publishRefusesMalformedLayout = checkingPublish and rejected and publishReady and not(event.selection.layout) and
    event.selection.request == event.plan.request and goodResult
}
