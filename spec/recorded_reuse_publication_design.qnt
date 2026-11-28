// Direct publication of an explicitly selected local result with durable provenance.
module recorded_reuse_publication_design {
  // One main, plan, result, staging, and create-only reuse slot. Non-aliased
  // names are fixed representatives; all six alias pairs among the four direct
  // publication names form one rejection class. Plan/result IDs below are exact.
  // Valid plans select one portable request and capture an unrelated tip, an
  // absent tip, or the exact result. Two results match structurally; four decoys
  // isolate each validation failure.
  // Wrong request can have the same output value. Arithmetic is not verified.
  pure val absent = 0
  pure val oldMain = 1
  pure val unrelated = 2
  pure val planOld = 3
  pure val planEmpty = 4
  pure val notPlan = 5
  pure val resultA = 6
  pure val resultB = 7
  pure val wrongShape = 8
  pure val wrongRequest = 9
  pure val wrongProducer = 10
  pure val wrongFactor = 11
  pure val request = 12
  pure val producer = 13
  pure val producerDag = 14
  pure val requestDag = 15
  pure val recordCommit = 16
  pure val recordTree = 17
  pure val recordDag = 18
  pure val foreign = 19
  pure val planAtResult = 20
  pure val resultDagA = 21
  pure val resultDagB = 22

  pure val plans = Set(planOld, planEmpty, planAtResult)
  pure val planCandidates = plans.union(Set(notPlan))
  pure val results = Set(resultA, resultB, wrongShape, wrongRequest, wrongProducer, wrongFactor)
  pure val shared = Set(request, requestDag, producer, producerDag)
  pure def capture(plan: int): int =
    if (plan == planOld) oldMain else if (plan == planAtResult) resultA else absent
  pure def resultMatches(result: int): bool = results.contains(result) and result != wrongShape and
    result != wrongRequest and result != wrongProducer and result != wrongFactor

  type Record = { entry: str, parents: List[int], planRef: str, resultRef: str, root: str }
  type Repo = { main: int, plan: int, result: int, stage: int, reuse: int, record: Record }
  type Event = { command: str, before: Repo, plan: int, result: int, alias: bool, fault: str, accepted: bool }
  type Consumption = { command: str, plan: int }
  pure val noConsumption: Consumption = { command: "", plan: absent }
  pure val noRecord: Record = { entry: "", parents: List(), planRef: "", resultRef: "", root: "" }
  pure val empty: Repo = { main: absent, plan: absent, result: absent, stage: absent,
    reuse: absent, record: noRecord }
  pure val noEvent: Event = { command: "", before: empty, plan: absent, result: absent, alias: false,
    fault: "", accepted: false }
  pure val faults = Set("", "main", "consume", "record")

  // Other writers act between transactions and can recreate the exact pins/tip,
  // but this model never changes an occupied reuse ref by hand. Faults after a
  // tentative write expose only rollback. Ordinary one-shot staged publication
  // and abandonment compete for the exact plan; keyed retry is modeled elsewhere.
  // The immutable graph and names abstract bytes, hash identity and native errors.
  // This is a safety/feasibility check, not a liveness or authentication claim.
  var source: Repo
  var event: Event
  var lastConsumption: Consumption // Ghost: reset whenever the plan slot is reinstalled.
  var survivors: Set[int] // Empty before the optional final GC and inspection.

  action init = {
    nondet tip = Set(absent, oldMain).oneOf()
    nondet occupied = Set(absent, foreign).oneOf()
    all {
      source' = { ...empty, main: tip, plan: if (tip == oldMain) planOld else planEmpty,
        result: resultA, stage: resultA, reuse: occupied },
      event' = noEvent, lastConsumption' = noConsumption, survivors' = Set()
    }
  }

  action update(after: Repo, consumption: Consumption): bool = all {
    source' = after, event' = noEvent, lastConsumption' = consumption, survivors' = survivors
  }

  action submit(plan: int, result: int, alias: bool, fault: str): bool = {
    val selected = not(alias) and source.plan == plan and plans.contains(plan) and
      source.result == result and resultMatches(result) and source.main == capture(plan)
    val accepted = selected and source.reuse == absent and fault == ""
    val record = { entry: "recorded-scale-reuse-v1", parents: List(plan, result),
      planRef: "plan", resultRef: "result", root: "plan_ref" }
    // Model the tentative main move, plan deletion, and record publication in
    // order, then expose only committed effects. Occupancy fails at the last write.
    val afterMain = { ...source, main: result }
    val afterConsume = { ...afterMain, plan: absent }
    val afterRecord = { ...afterConsume, reuse: recordCommit, record: record }
    all {
      source' = if (accepted) afterRecord else source,
      event' = { command: "reuse", before: source, plan: plan, result: result, alias: alias,
        fault: fault, accepted: accepted },
      lastConsumption' = if (accepted) { command: "reuse", plan: plan } else lastConsumption,
      survivors' = survivors
    }
  }

  action publish(plan: int, result: int): bool = {
    val accepted = source.plan == plan and plans.contains(plan) and source.stage == result and
      resultMatches(result) and source.main == capture(plan)
    all {
      source' = if (accepted) { ...source, main: result, plan: absent, stage: absent } else source,
      event' = { ...noEvent, command: "staged", before: source, plan: plan, result: result, accepted: accepted },
      lastConsumption' = if (accepted) { command: "staged", plan: plan } else lastConsumption,
      survivors' = survivors
    }
  }

  action abandon(plan: int): bool = {
    val accepted = source.plan == plan and plans.contains(plan)
    all {
      source' = if (accepted) { ...source, plan: absent } else source,
      event' = { ...noEvent, command: "abandon", before: source, plan: plan, accepted: accepted },
      lastConsumption' = if (accepted) { command: "abandon", plan: plan } else lastConsumption,
      survivors' = survivors
    }
  }

  // Fixture closures are resident until collection; no later import is modeled.
  // GC follows both ordinary parent edges, not the historical ref-name strings.
  // Non-selected and decoy subgraphs are abstracted except for their root IDs.
  pure def closure(root: int): Set[int] =
    if (root == absent) Set()
    else if (root == planOld) shared.union(Set(planOld, oldMain))
    else if (root == planEmpty) shared.union(Set(planEmpty))
    else if (root == planAtResult) shared.union(Set(planAtResult, resultA, resultDagA))
    else if (root == resultA) shared.union(Set(resultA, resultDagA))
    else if (root == resultB) shared.union(Set(resultB, resultDagB))
    else Set(root)

  action collect = {
    val roots = Set(source.main, source.plan, source.result, source.stage, source.reuse)
    val keep = roots.fold(Set(), (acc, id) => acc.union(closure(id)))
    val retained = if (source.reuse == recordCommit)
      source.record.parents.foldl(keep.union(Set(recordTree, recordDag)), (acc, id) => acc.union(closure(id)))
      else keep
    all {
      source' = source, event' = noEvent, lastConsumption' = lastConsumption, survivors' = retained
    }
  }

  // Store each observed command's before/after snapshot without multiplying
  // the next-step search by the previous event. Collection is a final readback
  // scenario after independent ref removal/movement; terminal states stutter.
  action step = if (event.command != "" or survivors != Set()) update(source, lastConsumption) else any {
    nondet plan = planCandidates.oneOf()
    nondet result = results.oneOf()
    submit(plan, result, false, ""),
    nondet alias = Set(false, true).oneOf()
    nondet fault = faults.oneOf()
    all { alias or fault != "",
      planCandidates.contains(source.plan), results.contains(source.result),
      submit(source.plan, source.result, alias, fault) },
    nondet plan = plans.oneOf()
    nondet result = Set(resultA, resultB, wrongRequest).oneOf()
    publish(plan, result),
    nondet plan = planCandidates.oneOf()
    abandon(plan),
    nondet main = Set(absent, oldMain, unrelated, resultA, resultB).oneOf()
    update({ ...source, main: main }, lastConsumption),
    nondet plan = planCandidates.oneOf()
    update({ ...source, plan: plan }, noConsumption),
    nondet result = results.union(Set(absent)).oneOf()
    update({ ...source, result: result }, lastConsumption),
    nondet stage = Set(absent, resultA, resultB, wrongRequest).oneOf()
    update({ ...source, stage: stage }, lastConsumption),
    all { source.reuse == recordCommit, collect }
  }

  // Independent fixture oracle: don't call capture, resultMatches, or the
  // transition's record constructor in the contracts.
  val before = event.before
  val submitted = event.command == "reuse"
  val exactPlan = before.plan == event.plan and Set(planOld, planEmpty, planAtResult).contains(event.plan)
  val exactResult = before.result == event.result
  val matching = Set(resultA, resultB).contains(event.result)
  val mainMatches = (event.plan == planOld and before.main == oldMain) or
    (event.plan == planEmpty and before.main == absent) or
    (event.plan == planAtResult and before.main == resultA)
  val ready = exactPlan and exactResult and matching and mainMatches
  val committed = submitted and event.accepted
  val rejected = submitted and not(event.accepted)
  val expectedRecord: Record = { entry: "recorded-scale-reuse-v1", parents: List(event.plan, event.result),
    planRef: "plan", resultRef: "result", root: "plan_ref" }
  invariant exactDecision = not(submitted) or (event.accepted iff
    (ready and not(event.alias) and before.reuse == absent and event.fault == ""))
  invariant atomicPublication = not(committed) or source == { ...before, main: event.result,
    plan: absent, reuse: recordCommit, record: expectedRecord }
  invariant noWritesOnRejection = event.command == "" or event.accepted or source == before
  invariant ordinaryStagedPublication = event.command != "staged" or all {
    event.accepted iff (exactPlan and matching and mainMatches and before.stage == event.result),
    not(event.accepted) or source == { ...before, main: event.result, plan: absent, stage: absent }
  }
  invariant exactAbandonment = event.command != "abandon" or all {
    event.accepted iff exactPlan,
    not(event.accepted) or source == { ...before, plan: absent }
  }
  invariant exclusiveConsumption = lastConsumption == noConsumption or source.plan == absent
  invariant noUnrootedRecordWrite = (source.reuse == recordCommit) iff (source.record != noRecord)
  invariant retainedEvidence = survivors == Set() or all {
    source.reuse == recordCommit,
    Set(recordCommit, recordTree, recordDag, request, requestDag, producer, producerDag).subseteq(survivors),
    source.record.parents.length() == 2,
    survivors.contains(source.record.parents[0]),
    survivors.contains(source.record.parents[1]),
    source.record.parents[0] != planOld or survivors.contains(oldMain),
    source.record.parents[0] != planAtResult or Set(resultA, resultDagA).subseteq(survivors),
    survivors.contains(if (source.record.parents[1] == resultA) resultDagA else resultDagB)
  }

  observation replacesMainWithoutConsumingStage = committed and event.plan == planOld and before.stage == event.result
  observation createsPreviouslyAbsentMain = committed and event.plan == planEmpty
  observation recordsReuseWithMainAlreadyAtResult = committed and before.main == event.result and before.stage == absent
  observation commitsExplicitAlternate = committed and event.result == resultB and before.stage == resultA
  observation foreignDestinationRejected = rejected and ready and before.reuse == foreign and
    not(event.alias) and event.fault == ""
  observation sameRecordRejectedWithGuardsRestored = rejected and ready and before.reuse == recordCommit and
    before.record == expectedRecord and not(event.alias) and event.fault == ""
  observation differentRecordRejectedWithGuardsReady = rejected and ready and before.reuse == recordCommit and
    before.record != expectedRecord and not(event.alias) and event.fault == ""
  val freshRejection = rejected and before.reuse == absent and not(event.alias) and event.fault == ""
  observation movedExistingMainRejected = freshRejection and exactPlan and exactResult and matching and
    event.plan == planOld and before.main == unrelated
  observation removedExistingMainRejected = freshRejection and exactPlan and exactResult and matching and
    event.plan == planOld and before.main == absent
  observation occupiedPreviouslyAbsentMainRejected = freshRejection and exactPlan and exactResult and matching and
    event.plan == planEmpty and before.main == unrelated
  observation movedPlanRejected = freshRejection and before.plan == planEmpty and event.plan == planOld and
    exactResult and matching and mainMatches
  observation malformedPlanRejected = freshRejection and before.plan == notPlan and event.plan == notPlan and
    exactResult and matching and before.main == absent
  observation movedResultRejectedWithoutSubstitution = freshRejection and exactPlan and matching and mainMatches and
    before.result == resultB and event.result == resultA
  observation removedResultRejected = freshRejection and exactPlan and matching and mainMatches and
    before.result == absent
  val wrongResult = freshRejection and exactPlan and exactResult and mainMatches
  observation wrongShapeRejected = wrongResult and event.result == wrongShape
  observation equalOutputWrongRequestRejected = wrongResult and event.result == wrongRequest
  observation wrongProducerRejected = wrongResult and event.result == wrongProducer
  observation wrongFactorRejected = wrongResult and event.result == wrongFactor
  observation aliasRejected = rejected and ready and event.alias and event.fault == "" and before.reuse == absent
  val otherwiseReadyFault = rejected and ready and not(event.alias) and before.reuse == absent
  observation rollbackAfterMain = otherwiseReadyFault and event.fault == "main"
  observation rollbackAfterConsume = otherwiseReadyFault and event.fault == "consume"
  observation rollbackAfterRecord = otherwiseReadyFault and event.fault == "record"
  observation abandonWins = freshRejection and lastConsumption == { command: "abandon", plan: event.plan } and
    before.plan == absent and exactResult and matching and mainMatches
  observation reuseBeatsAbandon = event.command == "abandon" and not(event.accepted) and
    lastConsumption == { command: "reuse", plan: event.plan }
  observation stagedPublicationWins = freshRejection and lastConsumption == { command: "staged", plan: event.plan } and
    before.plan == absent and exactResult and matching and mainMatches
  observation reuseBeatsStagedPublication = event.command == "staged" and not(event.accepted) and
    lastConsumption == { command: "reuse", plan: event.plan } and
    before.stage == event.result and matching and mainMatches
  observation reuseRefAloneRetainsEvidence = survivors != Set() and source.main == absent and
    source.plan == absent and source.stage == absent and source.result == absent and
    source.record.parents == List(planOld, resultA) and Set(resultB, resultDagB, unrelated).intersect(survivors) == Set()
}
