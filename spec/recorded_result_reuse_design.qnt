// Explicit result reuse and subsequent source-local publication.
module recorded_result_reuse_design {
  pure val absent = 0
  pure val planOld = 1
  pure val planNew = 2
  pure val oldMain = 3
  pure val newMain = 4
  pure val good = 5
  pure val alternate = 6
  pure val wrongRequest = 7
  pure val wrongProducer = 8
  pure val wrongFactor = 9
  pure val wrongShape = 10
  pure val malformedPlan = 11

  // Four ref slots (main, plan, source result, destination) and a passive receipt.
  // Two valid plans share an exact portable request but capture different existing
  // main targets. The third plan candidate is malformed. Two result IDs satisfy
  // the request. Other IDs isolate each result validation failure. Every name
  // alias collapses to one rejected input. Other writers can move main, recycle
  // source/plan slots, or occupy/clear the destination.
  // Operations interleave at transaction boundaries. Immutable closures and
  // ref/record encodings are abstracted; native faults, arithmetic/authenticity,
  // and receipt-aware publication/retry are outside this model.
  type Repo = { main: int, plan: int, result: int, stage: int, receipt: bool }
  type Event = { command: str, before: Repo, plan: int, result: int, alias: bool, accepted: bool,
    fromReuse: bool }
  pure val initial: Repo = { main: oldMain, plan: planOld, result: good, stage: absent, receipt: false }
  pure val noEvent: Event = { command: "", before: initial, plan: absent, result: absent,
    alias: false, accepted: false, fromReuse: false }
  pure val plans = Set(planOld, planNew)
  pure val results = Set(good, alternate, wrongRequest, wrongProducer, wrongFactor, wrongShape)

  pure def hasRequestedShape(id: int): bool = results.contains(id) and id != wrongShape
  pure def exactRequest(id: int): bool = id != wrongRequest
  pure def exactProducer(id: int): bool = id != wrongProducer
  pure def exactFactor(id: int): bool = id != wrongFactor
  pure def matchesRequest(id: int): bool =
    hasRequestedShape(id) and exactRequest(id) and exactProducer(id) and exactFactor(id)
  pure def capture(plan: int): int = if (plan == planOld) oldMain else newMain

  var repo: Repo
  var event: Event
  var stagedByReuse: bool // Ghost: how the current destination target got there.

  action init = {
    nondet receipt = Set(false, true).oneOf()
    all { repo' = { ...initial, receipt: receipt }, event' = noEvent, stagedByReuse' = false }
  }

  action change(after: Repo, fromReuse: bool): bool = all {
    repo' = after, event' = noEvent, stagedByReuse' = fromReuse
  }

  action reuse(plan: int, result: int, alias: bool): bool = {
    val accept = not(alias) and repo.plan == plan and plans.contains(plan) and
      repo.result == result and matchesRequest(result) and repo.stage == absent
    all {
      repo' = if (accept) { ...repo, stage: result } else repo,
      event' = { command: "reuse", before: repo, plan: plan, result: result, alias: alias,
        accepted: accept, fromReuse: stagedByReuse },
      stagedByReuse' = (accept or stagedByReuse)
    }
  }

  action publish(plan: int, result: int): bool = {
    val accept = repo.plan == plan and repo.stage == result and matchesRequest(result) and repo.main == capture(plan)
    all {
      repo' = if (accept) { ...repo, main: result, plan: absent, stage: absent } else repo,
      event' = { command: "publish", before: repo, plan: plan, result: result, alias: false,
        accepted: accept, fromReuse: stagedByReuse },
      stagedByReuse' = (not(accept) and stagedByReuse)
    }
  }

  action step = if (event.command != "") change(repo, stagedByReuse) else any {
    nondet plan = plans.union(Set(malformedPlan)).oneOf()
    nondet result = results.oneOf()
    nondet alias = Set(false, true).oneOf()
    reuse(plan, result, alias),
    nondet plan = plans.oneOf()
    nondet result = results.oneOf()
    publish(plan, result),
    all { repo.plan != absent, change({ ...repo, plan: absent }, stagedByReuse) },
    nondet plan = plans.union(Set(malformedPlan)).oneOf()
    change({ ...repo, plan: plan }, stagedByReuse),
    nondet result = results.union(Set(absent)).oneOf()
    change({ ...repo, result: result }, stagedByReuse),
    nondet stage = Set(absent, good, wrongShape).oneOf()
    change({ ...repo, stage: stage }, false),
    nondet main = Set(oldMain, newMain, good, alternate).oneOf()
    change({ ...repo, main: main }, stagedByReuse)
  }

  val before = event.before
  val reused = event.command == "reuse"
  val publishing = event.command == "publish"
  val exactPlan = before.plan == event.plan
  val exactSource = before.result == event.result
  // Independent oracle: the only reusable result IDs in these fixtures.
  val reusable = Set(good, alternate).contains(event.result)
  val readyToStage = exactPlan and event.plan != malformedPlan and exactSource and reusable and not(event.alias)
  invariant exactReuse = not(reused) or (event.accepted iff (readyToStage and before.stage == absent))
  invariant onlyNewDestination = not(reused and event.accepted) or repo == { ...before, stage: event.result }
  invariant noWritesOnRejection = event.command == "" or event.accepted or repo == before
  val mainMatches = (event.plan == planOld and before.main == oldMain) or
    (event.plan == planNew and before.main == newMain)
  invariant guardedPublication = not(publishing) or (event.accepted iff
    (exactPlan and reusable and before.stage == event.result and mainMatches))
  invariant atomicPublication = not(publishing and event.accepted) or
    repo == { ...before, plan: absent, stage: absent, main: event.result }

  val rejectsReuse = reused and not(event.accepted)
  val rejectsOtherwiseReady = rejectsReuse and exactPlan and event.plan != malformedPlan and
    exactSource and before.stage == absent and not(event.alias)
  observation stagedAfterMainMoved = reused and event.accepted and not(mainMatches) and before.receipt
  observation publishFromReuseAfterSourceRemoved = publishing and event.accepted and event.fromReuse and
    before.result == absent
  observation staleMainPreventsPublication = publishing and not(event.accepted) and event.fromReuse and
    exactPlan and before.stage == event.result and not(mainMatches)
  observation abandonPreventsPublication = publishing and not(event.accepted) and event.fromReuse and
    before.plan == absent and before.stage == event.result and mainMatches
  observation absentPlanPreventsReuse = rejectsReuse and before.plan == absent and event.plan != malformedPlan and
    exactSource and reusable and before.stage == absent and not(event.alias)
  observation movedPlanPreventsReuse = rejectsReuse and before.plan == planNew and event.plan == planOld and
    exactSource and reusable and before.stage == absent and not(event.alias)
  observation malformedPlanRejected = rejectsReuse and exactPlan and event.plan == malformedPlan and
    exactSource and reusable and before.stage == absent and not(event.alias)
  observation movedResultPreventsReuse = rejectsReuse and exactPlan and event.plan != malformedPlan and
    before.result == alternate and event.result == good and before.stage == absent and not(event.alias)
  observation occupiedWithExactResultRejected = rejectsReuse and readyToStage and before.stage == event.result
  observation occupiedWithDifferentResultRejected = rejectsReuse and readyToStage and before.stage == wrongShape
  observation aliasesRejected = rejectsReuse and event.alias and exactPlan and event.plan != malformedPlan and
    exactSource and reusable and before.stage == absent
  observation wrongRequestRejected = rejectsOtherwiseReady and event.result == wrongRequest
  observation wrongProducerRejected = rejectsOtherwiseReady and event.result == wrongProducer
  observation wrongFactorRejected = rejectsOtherwiseReady and event.result == wrongFactor
  observation wrongShapeRejected = rejectsOtherwiseReady and event.result == wrongShape
}
