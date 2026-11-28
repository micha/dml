// Finite safety design; run with quint verify --backend=tlc --search-observations.
module recorded_request_design {
  // One caller-selected attempt, two equal zero-valued sums, two factors, and
  // disjoint named pins (except for explicit alias rejection). IDs name immutable
  // records; each DAG ID stands for its whole closure. Plan and result refs can
  // move between commands. The attempt starts with absent or unrelated main.
  // A competing writer can publish an alternate result. An ID compare permits
  // ABA; deliberate re-recording/resurrection of a consumed plan is out of scope.
  // No fairness, byte corruption, native errors or hash collisions are modeled.
  pure val absent = 0
  pure val producer = 1
  pure val decoy = 2
  pure val oldMain = 3
  pure val request = 10
  pure val alternate = 11   // Same producer, different factor, same output.
  pure val otherSum = 12    // Same factor and output, different producer commit and DAG.
  pure val planEmpty = 20
  pure val planOld = 21
  pure val good = 30
  pure val otherRequestResult = 31
  pure val badFactor = 32   // Exact request parent, but the wrong typed factor value.
  pure val badInput = 33    // Exact request parent and factor, but wrong direct sub-DAG edge.
  pure val otherStored = 34 // Same shape and lineage, distinct ID; readback does not run arithmetic.
  pure val legacy = 35      // Parent is the sum, not the request; not the result variant.
  pure val requests = Set(request, alternate, otherSum)
  pure val results = Set(good, otherRequestResult, badFactor, badInput, otherStored, legacy)
  pure val plans = Set(planEmpty, planOld)
  pure def dag(id: int): int = 100 + id
  pure def sumValue(_id: int): int = 0
  pure def planFor(main: int): int = if (main == absent) planEmpty else planOld
  pure def captured(plan: int): int = if (plan == planOld) oldMain else absent
  pure def requestOf(plan: int): int = if (plans.contains(plan)) request else absent
  pure def requestDag(req: int): int = dag(if (req == otherSum) request else req)
  pure def producerOf(req: int): int = if (req == otherSum) decoy else producer
  pure def factorOf(req: int): int = if (req == alternate) -2 else 3
  pure def parentOf(result: int): int =
    if (result == otherRequestResult) alternate else if (result == legacy) producer else request
  pure def scaleFactor(result: int): int = if (result == badFactor) -2 else factorOf(parentOf(result))
  pure def inputOf(result: int): int = if (result == badInput) dag(decoy) else dag(producer)
  pure def outputOf(result: int): int = if (result == otherStored) 17 else 0

  pure def previous(main: int): Set[int] = if (main == absent) Set() else Set(main, dag(main))
  pure def portable(req: int): Set[int] = Set(req, requestDag(req), producerOf(req), dag(producerOf(req)))
  pure def closure(root: int): Set[int] =
    if (requests.contains(root)) portable(root)
    // The plan's different tree entry references the same DAG as the request.
    else if (plans.contains(root)) Set(root).union(portable(requestOf(root))).union(previous(captured(root)))
    else if (results.contains(root)) {
      val lineage = if (root == legacy) previous(producer) else portable(parentOf(root))
      Set(root, dag(root), inputOf(root)).union(lineage)
    } else previous(root)

  type Source = { producerPin: int, main: int, plan: int, stage: int, objects: Set[int] }
  type Worker = { incoming: int, result: int, objects: Set[int] }
  type Event = { command: str, wanted: int, receipt: int, mode: int, source: Source, worker: Worker }
  pure val emptySource: Source = { producerPin: absent, main: absent, plan: absent, stage: absent, objects: Set() }
  pure val emptyWorker: Worker = { incoming: absent, result: absent, objects: Set() }
  pure val noEvent: Event = { command: "", wanted: absent, receipt: absent, mode: 0,
    source: emptySource, worker: emptyWorker }
  pure def sourceRoots(repo: Source): Set[int] =
    closure(repo.producerPin).union(closure(repo.main)).union(closure(repo.plan)).union(closure(repo.stage))
  pure def workerRoots(repo: Worker): Set[int] = closure(repo.incoming).union(closure(repo.result))

  var phase: str
  var source: Source
  var worker: Worker
  var event: Event
  var wantedPlan: int // Caller persists the record-plan receipt, not the current pin target.
  var exportedRequest: int // Bundle identity, only set by a successful export.
  var selectedRequest: int // Volatile export selection, discarded on process restart.
  var returnedFile: int // Submitted file, independent of the publisher's candidate ID.
  var restartedWithStage: bool
  var consumed: bool

  action init = {
    nondet main = Set(absent, oldMain).oneOf()
    all {
      phase' = "record",
      source' = { ...emptySource, main: main, producerPin: producer,
        objects: previous(main).union(closure(producer)) },
      worker' = emptyWorker,
      event' = noEvent,
      wantedPlan' = absent,
      exportedRequest' = absent,
      selectedRequest' = absent,
      returnedFile' = absent,
      restartedWithStage' = false,
      consumed' = false
    }
  }

  action keepRestartStatus = restartedWithStage' = restartedWithStage

  action keepTransfer = all {
    wantedPlan' = wantedPlan,
    exportedRequest' = exportedRequest,
    selectedRequest' = selectedRequest,
    returnedFile' = returnedFile
  }

  action updateSource(after: Source, report: Event): bool = all {
    phase' = phase,
    source' = after,
    worker' = worker,
    event' = report,
    keepTransfer,
    keepRestartStatus,
    consumed' = consumed
  }

  // Creating both commits, reading main (including absence), and pinning the
  // plan are part of this single source write. Mode 1 aliases the plan to main.
  action recordPlan(mode: int): bool = {
    val accepted = mode == 0 and source.producerPin == producer and source.plan == absent
    val plan = if (accepted) planFor(source.main) else absent
    all {
      phase' = if (accepted) "export" else phase,
      source' = if (accepted) { ...source, plan: plan, objects: source.objects.union(closure(plan)) } else source,
      worker' = worker,
      wantedPlan' = plan,
      exportedRequest' = exportedRequest,
      selectedRequest' = selectedRequest,
      returnedFile' = returnedFile,
      event' = { ...noEvent, command: "record", receipt: plan, mode: mode, source: source },
      keepRestartStatus,
      consumed' = consumed
    }
  }

  // Pin selection and export-by-ID use different read snapshots. Export uses
  // the request ID obtained from the exact plan, never the plan commit itself.
  action selectRequest = {
    val selected = if (source.plan == wantedPlan) requestOf(wantedPlan) else absent
    all {
      selectedRequest == absent,
      phase' = phase,
      source' = source,
      worker' = worker,
      wantedPlan' = wantedPlan,
      exportedRequest' = exportedRequest,
      selectedRequest' = selected,
      returnedFile' = returnedFile,
      event' = { ...noEvent, command: "select", receipt: selected },
      keepRestartStatus,
      consumed' = consumed
    }
  }

  action exportRequest = {
    val allowed = portable(selectedRequest).subseteq(source.objects)
    val exported = if (allowed) selectedRequest else absent
    all {
      selectedRequest != absent,
      phase' = if (allowed) "worker" else phase,
      source' = source,
      worker' = worker,
      wantedPlan' = wantedPlan,
      exportedRequest' = exported,
      selectedRequest' = absent,
      returnedFile' = returnedFile,
      event' = { ...noEvent, command: "export", wanted: selectedRequest, receipt: exported },
      keepRestartStatus,
      consumed' = consumed
    }
  }

  action updateWorker(after: Worker, report: Event): bool = all {
    phase' = phase,
    source' = source,
    worker' = after,
    event' = report,
    keepTransfer,
    keepRestartStatus,
    consumed' = consumed
  }

  // Staging can succeed for a valid but incorrect request. Work checks the
  // independently carried export ID, never the staging command's receipt.
  action stageRequest(actual: int): bool = {
    val accepted = worker.incoming == absent
    val after = if (accepted) { ...worker, incoming: actual, objects: worker.objects.union(closure(actual)) }
      else worker
    updateWorker(after, { ...noEvent, command: "incoming", wanted: actual,
      receipt: if (accepted) actual else absent, worker: worker })
  }

  action work = {
    val req = worker.incoming
    val accepted = req == exportedRequest and worker.result == absent
    // Within this finite domain those stored arguments identify good uniquely.
    val product = if (parentOf(good) == req and scaleFactor(good) == factorOf(req) and
      inputOf(good) == dag(producerOf(req))) good else absent
    val after = if (accepted) { ...worker, result: product, objects: worker.objects.union(closure(product)) }
      else worker
    updateWorker(after, { ...noEvent, command: "work", receipt: if (accepted) product else absent, worker: worker })
  }

  // Source mutations that do not affect the worker can be scheduled just before
  // its first action or just after return. Legacy export pin interleavings are
  // covered by recorded_return_design. Select one submitted file per execution:
  // either the worker's export or an externally supplied result fixture.
  action returnFile(actual: int): bool = all {
    phase' = "return",
    source' = source,
    worker' = emptyWorker,
    event' = noEvent,
    wantedPlan' = wantedPlan,
    exportedRequest' = exportedRequest,
    selectedRequest' = selectedRequest,
    returnedFile' = actual,
    keepRestartStatus,
    consumed' = consumed
  }

  action stageResult(actual: int): bool = {
    val accepted = source.stage == absent
    val after = if (accepted) { ...source, stage: actual, objects: source.objects.union(closure(actual)) } else source
    updateSource(after, { ...noEvent, command: "stage", wanted: actual,
      receipt: if (accepted) actual else absent, source: source })
  }

  // Check request identity, the typed factor, and direct physical input, then
  // compare main and consume both exact pins in one source write transaction.
  // Modes 1..3 inject an abort after each tentative write; mode 4 aliases refs.
  action publish(wanted: int, mode: int): bool = {
    val plan = wantedPlan
    val req = requestOf(plan)
    val verified = mode != 4 and source.plan == plan and source.objects.contains(wanted) and
      wanted != legacy and parentOf(wanted) == req and scaleFactor(wanted) == factorOf(req) and
      inputOf(wanted) == dag(producerOf(req))
    val writesMain = verified and source.main == captured(plan)
    val mainWritten = if (writesMain) { ...source, main: wanted } else source
    val deletesStage = writesMain and mode != 1 and mainWritten.stage == wanted
    val stageDeleted = if (deletesStage) { ...mainWritten, stage: absent } else mainWritten
    val deletesPlan = deletesStage and mode != 2
    val planDeleted = if (deletesPlan) { ...stageDeleted, plan: absent } else stageDeleted
    val committed = deletesPlan and mode != 3
    all {
      phase' = phase,
      source' = if (committed) planDeleted else source,
      worker' = worker,
      event' = { ...noEvent, command: "publish", wanted: wanted, mode: mode,
        receipt: if (committed) wanted else absent, source: source },
      keepTransfer,
      keepRestartStatus,
      consumed' = (consumed or committed)
    }
  }

  // New invocations have only persistent repository state, immutable files,
  // and explicitly carried IDs. This does not keep an in-memory plan/factor.
  action restart = all {
    (phase == "export" and selectedRequest != absent) or (phase == "return" and source.stage == good),
    phase' = phase,
    source' = source,
    worker' = worker,
    event' = noEvent,
    wantedPlan' = wantedPlan,
    exportedRequest' = exportedRequest,
    selectedRequest' = absent,
    returnedFile' = returnedFile,
    restartedWithStage' = (phase == "return" or restartedWithStage),
    consumed' = consumed
  }

  action moveProducer(target: int): bool = updateSource({ ...source, producerPin: target,
    objects: source.objects.union(closure(target)) }, noEvent)

  action changePlan(target: int): bool = all {
    source.plan != absent,
    updateSource({ ...source, plan: target, objects: source.objects.union(closure(target)) }, noEvent)
  }

  action collectSource = updateSource({ ...source, objects: sourceRoots(source) },
    { ...noEvent, command: "collect", source: source })

  action recordStep = any {
    nondet mode = Set(0, 1).oneOf()
    recordPlan(mode),
    nondet target = Set(absent, producer, decoy).oneOf()
    moveProducer(target)
  }

  action exportStep = any {
    selectRequest,
    exportRequest,
    restart,
    nondet target = Set(absent, planOld, planEmpty).exclude(Set(wantedPlan)).oneOf()
    changePlan(target),
    moveProducer(absent),
    collectSource
  }

  action workerStep = any {
    nondet actual = Set(exportedRequest, alternate, otherSum).oneOf()
    stageRequest(actual),
    work,
    nondet target = Set(absent, alternate).oneOf()
    all {
      worker.incoming != absent,
      updateWorker({ ...worker, incoming: target, objects: worker.objects.union(closure(target)) }, noEvent)
    },
    updateWorker({ ...worker, objects: workerRoots(worker) }, noEvent),
    nondet file = results.exclude(Set(good)).union(Set(worker.result)).exclude(Set(absent)).oneOf()
    returnFile(file)
  }

  action returnStep = any {
    stageResult(returnedFile),
    nondet wanted = results.oneOf()
    nondet mode = Set(0, 1, 2, 3, 4).oneOf()
    publish(wanted, mode),
    nondet target = Set(absent, oldMain, otherRequestResult).oneOf()
    updateSource({ ...source, main: target, objects: source.objects.union(closure(target)) }, noEvent),
    nondet target = Set(absent, planOld, planEmpty).exclude(Set(wantedPlan)).oneOf()
    changePlan(target),
    nondet target = Set(absent, otherStored).oneOf()
    all {
      source.stage != absent,
      updateSource({ ...source, stage: target, objects: source.objects.union(closure(target)) }, noEvent)
    },
    moveProducer(absent),
    collectSource,
    restart
  }

  action step = if (event.command != "") updateSource(source, noEvent) else
    if (phase == "record") recordStep else if (phase == "export") exportStep else
    if (phase == "worker") workerStep else returnStep

  invariant exactPlan = if (event.command != "record") true else {
    val before = event.source
    val accepted = event.mode == 0 and before.producerPin == producer
    val expected = if (before.main == oldMain) planOld else planEmpty
    if (not(accepted)) event.receipt == absent and wantedPlan == absent and source == before
    else all {
      event.receipt == expected,
      wantedPlan == expected,
      source == { ...before, plan: expected, objects: before.objects.union(closure(expected)) },
      captured(expected) == before.main,
      portable(request) == Set(request, dag(request), producer, dag(producer)),
      not(portable(request).contains(before.main)),
      closure(expected).contains(request),
      before.main != absent implies closure(expected).contains(before.main)
    }
  }

  invariant portableExport = all {
    Set(absent, request).contains(selectedRequest),
    Set(absent, request).contains(exportedRequest),
    if (event.command == "select") event.receipt == (if (source.plan == wantedPlan) request else absent) else true,
    if (event.command == "export") {
      event.wanted == request and event.receipt == (if (source.objects.contains(request)) request else absent)
    } else true
  }

  invariant exactWork = if (event.command != "work") true else {
    val before = event.worker
    if (before.incoming != request or before.result != absent) event.receipt == absent and worker == before
    else all {
      event.receipt == good,
      worker == { ...before, result: good, objects: before.objects.union(closure(good)) },
      parentOf(good) == request,
      scaleFactor(good) == factorOf(request),
      inputOf(good) == dag(producer),
      outputOf(good) == sumValue(producer) * factorOf(request)
    }
  }

  invariant stageOnly = if (event.command != "stage") true else {
    val before = event.source
    if (before.stage == absent) event.receipt == event.wanted and
      source == { ...before, stage: event.wanted, objects: before.objects.union(closure(event.wanted)) }
    else event.receipt == absent and source == before
  }

  // Fixture-level oracle: identify precisely the two graph shapes allowed by
  // this request, independently of the publisher's field-by-field validation.
  invariant atomicPublish = if (event.command != "publish") true else {
    val before = event.source
    val wanted = event.wanted
    val mainMatches = (wantedPlan == planEmpty and before.main == absent) or
      (wantedPlan == planOld and before.main == oldMain)
    val allowed = event.mode == 0 and mainMatches and before.plan == wantedPlan and
      before.stage == wanted and Set(good, otherStored).contains(wanted)
    if (allowed) event.receipt == wanted and source == { ...before, main: wanted, stage: absent, plan: absent }
    else event.receipt == absent and source == before
  }

  invariant reachesAndReleases = all {
    sourceRoots(source).subseteq(source.objects),
    workerRoots(worker).subseteq(worker.objects),
    not(consumed) or source.plan == absent,
    if (Set(good, otherStored).contains(source.main))
      closure(source.main) == Set(source.main, dag(source.main), request, dag(request), producer, dag(producer))
    else true,
    if (event.command == "collect") source.objects == sourceRoots(event.source) else true
  }

  observation movedProducerRejected = event.command == "record" and event.mode == 0 and
    event.source.producerPin == decoy and event.receipt == absent
  observation planAliasRejected = event.command == "record" and event.mode == 1 and
    event.source.producerPin == producer and event.receipt == absent
  observation movedExportPlanRejected = event.command == "select" and source.plan != absent and
    source.plan != wantedPlan and event.receipt == absent
  observation immutableRequestExportDespiteMove = event.command == "export" and source.plan != wantedPlan and
    event.receipt == request
  observation sweptRequestRejected = event.command == "export" and not(source.objects.contains(request)) and
    event.receipt == absent
  observation alternateFactorRequestRejected = event.command == "work" and event.worker.incoming == alternate and
    event.worker.result == absent and event.receipt == absent and
    sumValue(producer) * factorOf(alternate) == outputOf(good)
  observation sameValueOtherSumRejected = event.command == "work" and event.worker.incoming == otherSum and
    event.worker.result == absent and event.receipt == absent and sumValue(decoy) == sumValue(producer)
  observation missingIncomingRejected = event.command == "work" and event.worker.incoming == absent and
    event.worker.objects.contains(request) and event.worker.result == absent and event.receipt == absent

  val publishing = event.command == "publish"
  val ordinary = publishing and event.mode == 0
  val mainMatches = event.source.main == captured(wantedPlan)
  val planMatches = event.source.plan == wantedPlan
  val stageMatches = event.source.stage == event.wanted
  val exactGood = ordinary and planMatches and stageMatches and event.wanted == good
  val exactStage = ordinary and planMatches and stageMatches and mainMatches
  observation createMain = exactGood and wantedPlan == planEmpty and event.receipt == good
  observation updateMain = exactGood and wantedPlan == planOld and event.receipt == good
  observation publishAfterRestart = exactGood and restartedWithStage and event.receipt == good
  observation occupiedMainRejected = exactGood and wantedPlan == planEmpty and
    event.source.main == otherRequestResult and event.receipt == absent
  observation movedMainRejected = exactGood and wantedPlan == planOld and
    event.source.main == otherRequestResult and event.receipt == absent
  observation removedMainRejected = exactGood and wantedPlan == planOld and
    event.source.main == absent and event.receipt == absent
  observation otherRequestRejected = exactStage and event.wanted == otherRequestResult and
    outputOf(otherRequestResult) == outputOf(good) and event.receipt == absent
  observation forgedFactorRejected = exactStage and event.wanted == badFactor and
    parentOf(badFactor) == request and outputOf(badFactor) == outputOf(good) and event.receipt == absent
  observation wrongInputRejected = exactStage and event.wanted == badInput and event.receipt == absent
  observation wrongVariantRejected = exactStage and event.wanted == legacy and event.receipt == absent
  observation movedStageRejected = ordinary and planMatches and mainMatches and event.wanted == good and
    event.source.stage == otherStored and event.source.objects.contains(good) and event.receipt == absent
  observation missingStageRejected = ordinary and planMatches and mainMatches and event.wanted == good and
    event.source.stage == absent and event.source.objects.contains(good) and event.receipt == absent
  observation movedPlanRejected = ordinary and mainMatches and stageMatches and event.wanted == good and
    event.source.plan != absent and not(planMatches) and event.source.objects.contains(wantedPlan) and
    event.receipt == absent
  observation missingPlanRejected = ordinary and mainMatches and stageMatches and event.wanted == good and
    event.source.plan == absent and event.source.objects.contains(wantedPlan) and event.receipt == absent
  observation reStagedAfterSuccessRejected = ordinary and consumed and mainMatches and stageMatches and
    event.wanted == good and event.source.plan == absent and event.receipt == absent
  observation rollbackAfterMain = publishing and event.mode == 1 and mainMatches and planMatches and
    stageMatches and event.wanted == good and event.receipt == absent
  observation rollbackAfterStageDelete = publishing and event.mode == 2 and mainMatches and planMatches and
    stageMatches and event.wanted == good and event.receipt == absent
  observation rollbackAfterPlanDelete = publishing and event.mode == 3 and mainMatches and planMatches and
    stageMatches and event.wanted == good and event.receipt == absent
  observation publishAliasRejected = publishing and event.mode == 4 and mainMatches and planMatches and
    stageMatches and event.wanted == good and event.receipt == absent
  observation checkpointRetainsPreviousMain = event.command == "collect" and source.plan == planOld and
    source.main != oldMain and source.objects.contains(oldMain)
  observation collectAfterPublish = event.command == "collect" and consumed and source.main == good and
    source.producerPin == absent and source.stage == absent and event.source.objects.contains(oldMain) and
    event.source.objects.contains(planOld) and source.objects == closure(good)
}
