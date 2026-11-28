// Finite safety design for quint verify --backend=tlc (not implementation replay).
module recorded_return_design {
  // IDs represent immutable records and DAG IDs represent entire DAG closures.
  // The two sums have equal values but distinct commit and DAG IDs. A second
  // well-formed scale of the planned producer uses a different factor. Both
  // scales can have the same output (e.g. a zero sum); output is not evidence
  // of the factor. The other three results model valid graphs with wrong application
  // lineage or shape. No malformed bundles, native corruption, ID collisions,
  // or distinct ref names aliasing besides RETURNED == main are modeled.
  pure val absent = 0
  pure val producer = 1
  pure val decoy = 2
  pure val previousMain = 3
  pure val competingMain = 4
  pure val planned = 11
  pure val alternate = 12
  pure val wrongParent = 13
  pure val wrongInput = 14
  pure val wrongShape = 15
  pure val results = Set(planned, alternate, wrongParent, wrongInput, wrongShape)
  pure val plannedFactor = 3
  pure val alternateFactor = -2
  pure def factorOf(result: int): int = if (result == alternate) alternateFactor else plannedFactor
  pure def sumDag(commit: int): int = 100 + commit
  pure def parentOf(result: int): int = if (result == wrongParent) decoy else producer
  pure def inputOf(result: int): int =
    if (result == wrongInput) sumDag(decoy) else sumDag(parentOf(result))

  pure def closure(root: int): Set[int] =
    if (root == absent) Set()
    else if (Set(producer, decoy).contains(root)) Set(root, sumDag(root))
    else if (results.contains(root)) Set(root, parentOf(root), sumDag(parentOf(root)), inputOf(root))
    else Set(root)

  pure def readableScale(root: int, objects: Set[int]): bool = {
    val parent = parentOf(root)
    val input = inputOf(root)
    results.contains(root) and root != wrongShape and objects.contains(root) and
      objects.contains(parent) and objects.contains(input) and input == sumDag(parent)
  }

  type Worker = { pin: int, objects: Set[int], selected: int, bundle: int }
  type Source = { main: int, returned: int, producerPin: int, objects: Set[int] }
  type Event = {
    command: str, wanted: int, receipt: int, oldBundle: int, before: Source,
    expectedMain: int, expectedFactor: int, aliasesMain: bool, failAt: int,
  }
  pure val emptyWorker: Worker = { pin: absent, objects: Set(), selected: absent, bundle: absent }
  pure val initialSource: Source = {
    main: previousMain, returned: absent, producerPin: producer,
    objects: closure(previousMain).union(closure(producer)).union(closure(decoy))
  }
  pure val noEvent: Event = {
    command: "", wanted: absent, receipt: absent, oldBundle: absent, before: initialSource,
    expectedMain: absent, expectedFactor: plannedFactor, aliasesMain: false, failAt: 0
  }
  pure def roots(repo: Source): Set[int] =
    closure(repo.main).union(closure(repo.returned)).union(closure(repo.producerPin))

  var returning: bool
  var worker: Worker
  var source: Source
  var event: Event

  action init = all {
    returning' = false,
    worker' = { ...emptyWorker, pin: planned, objects: results.fold(Set(), (acc, id) => acc.union(closure(id))) },
    source' = initialSource,
    event' = noEvent
  }

  action updateWorker(after: Worker, report: Event): bool = all {
    returning' = false,
    worker' = after,
    source' = source,
    event' = report
  }

  action selectScale(wanted: int): bool = {
    val root = worker.pin
    val selected = if (root == wanted and readableScale(root, worker.objects)) root else absent
    all {
      worker.selected == absent,
      updateWorker({ ...worker, selected: selected },
        { ...noEvent, command: "select", wanted: wanted, receipt: selected })
    }
  }

  // Selection and export are different read snapshots. A moved ref does not
  // affect the immutable selection; intervening collection may remove it.
  action exportScale = {
    val selected = worker.selected
    val exported = if (closure(selected).subseteq(worker.objects)) selected else absent
    all {
      selected != absent,
      updateWorker({ ...worker, selected: absent, bundle: if (exported != absent) exported else worker.bundle },
        { ...noEvent, command: "export", wanted: selected, receipt: exported, oldBundle: worker.bundle })
    }
  }

  action moveWorkerPin(target: int): bool = all {
    target == absent or worker.objects.contains(target),
    updateWorker({ ...worker, pin: target }, noEvent)
  }

  // Worker and source have no shared write transaction. Stop modeling worker
  // actions after the handoff; the file is now independent of worker objects.
  // Source may receive another structurally valid bundle from outside this flow.
  action startReturn = all {
    returning' = true,
    worker' = { ...emptyWorker, bundle: if (worker.bundle == planned) planned else absent },
    source' = source,
    event' = noEvent
  }

  action updateSource(after: Source, report: Event): bool = all {
    returning' = true,
    worker' = worker,
    source' = after,
    event' = report
  }

  action stage(root: int): bool = {
    val open = source.returned == absent
    val after = if (open) { ...source, returned: root, objects: source.objects.union(closure(root)) } else source
    updateSource(after, { ...noEvent, command: "stage", wanted: root, receipt: if (open) root else absent,
      before: source })
  }

  // All writes are serialized within each repository. Model main's conditional
  // create/update, then the expected staging deletion, then commit. The failure
  // flags stand for aborts after either tentative write, not writer interleaving.
  action publish(wanted: int, expectedMain: int, expectedFactor: int, aliasesMain: bool, failAt: int): bool = {
    // The source supplies its own producer and factor expectations.
    val validated = not(aliasesMain) and readableScale(wanted, source.objects) and
      parentOf(wanted) == producer and factorOf(wanted) == expectedFactor
    val writesMain = validated and source.main == expectedMain
    val tentative = if (writesMain) { ...source, main: wanted } else source
    val deletesReturned = writesMain and tentative.returned == wanted and failAt != 1
    val afterDelete = if (deletesReturned) { ...tentative, returned: absent } else tentative
    val committed = deletesReturned and failAt != 2
    updateSource(if (committed) afterDelete else source,
      { ...noEvent, command: "publish", wanted: wanted, receipt: if (committed) wanted else absent,
        before: source, expectedMain: expectedMain, expectedFactor: expectedFactor,
        aliasesMain: aliasesMain, failAt: failAt })
  }

  action workerStep = any {
    nondet wanted = results.oneOf()
    selectScale(wanted),
    exportScale,
    nondet target = results.union(Set(absent)).oneOf()
    moveWorkerPin(target),
    updateWorker({ ...worker, objects: closure(worker.pin) }, noEvent),
    startReturn
  }

  action sourceStep = any {
    nondet root = results.exclude(Set(planned)).union(Set(worker.bundle)).exclude(Set(absent)).oneOf()
    stage(root),
    nondet root = results.oneOf()
    nondet expectedMain = Set(absent, previousMain, planned).oneOf()
    nondet expectedFactor = Set(plannedFactor, alternateFactor).oneOf()
    // Choose ordinary success, two failure points, or a main/staging alias.
    nondet mode = Set(0, 1, 2, 3).oneOf()
    publish(root, expectedMain, expectedFactor, mode == 3, if (mode == 3) 0 else mode),
    nondet target = Set(absent, previousMain, competingMain).oneOf()
    updateSource({ ...source, main: target, objects: source.objects.union(closure(target)) }, noEvent),
    nondet target = Set(absent, decoy).oneOf()
    all {
      source.returned != absent,
      target == absent or source.objects.contains(target),
      updateSource({ ...source, returned: target }, noEvent)
    },
    nondet target = Set(absent, decoy).oneOf()
    updateSource({ ...source, producerPin: target, objects: source.objects.union(closure(target)) }, noEvent),
    updateSource({ ...source, objects: roots(source) }, { ...noEvent, command: "collect", before: source })
  }

  // Check each operation report in its immediate after-state, then discard
  // it before enumerating the next source operation from the same snapshot.
  action step =
    if (not(returning)) workerStep
    else if (event.command != "") updateSource(source, noEvent)
    else sourceStep

  // Fixture-level oracle for shape, deliberately not the operation's inspector.
  pure val exportable = Set(planned, alternate, wrongParent)
  pure val publishable = Set(planned, alternate)
  val exactExport = all {
    exportable.union(Set(absent)).contains(worker.selected),
    exportable.union(Set(absent)).contains(worker.bundle),
    if (event.command == "select") {
      val accepted = worker.pin == event.wanted and exportable.contains(worker.pin)
      event.receipt == (if (accepted) event.wanted else absent) and worker.selected == event.receipt
    } else true,
    if (event.command == "export") {
      val wanted = if (worker.objects.contains(event.wanted)) event.wanted else absent
      event.receipt == wanted and worker.bundle == (if (wanted == absent) event.oldBundle else wanted)
    } else true
  }

  val stageOnly = if (event.command != "stage") true else {
    val before = event.before
    if (before.returned != absent) event.receipt == absent and source == before
    else event.receipt == event.wanted and source ==
      { ...before, returned: event.wanted, objects: before.objects.union(closure(event.wanted)) }
  }

  val atomicPublish = if (event.command != "publish") true else {
    val before = event.before
    val requested = Set((planned, plannedFactor), (alternate, alternateFactor))
    val allowed = not(event.aliasesMain) and event.failAt == 0 and before.main == event.expectedMain and
      before.returned == event.wanted and requested.contains((event.wanted, event.expectedFactor))
    if (allowed) event.receipt == event.wanted and source == { ...before, main: event.wanted, returned: absent }
    else event.receipt == absent and source == before
  }

  val retainedAndReadable = all {
    closure(worker.pin).subseteq(worker.objects),
    roots(source).subseteq(source.objects),
    if (publishable.contains(source.main)) readableScale(source.main, source.objects) else true,
    if (event.command == "collect") source.objects == roots(event.before) else true
  }

  // These scenarios must be reachable, not invariant. Isolate each rejection
  // from other failing preconditions so it checks the intended guard.
  observation wrongExportPinRejected = event.command == "select" and event.wanted == planned and
    worker.pin == alternate and event.receipt == absent
  observation wrongExportInputRejected = event.command == "select" and event.wanted == wrongInput and
    worker.pin == wrongInput and event.receipt == absent
  observation wrongExportShapeRejected = event.command == "select" and event.wanted == wrongShape and
    worker.pin == wrongShape and event.receipt == absent
  observation decoyLineageExportAllowed = event.command == "export" and event.receipt == wrongParent
  observation exportDespiteMove = event.command == "export" and worker.pin == alternate and event.receipt == planned
  observation exportAfterSweepRejected = event.command == "export" and event.wanted == planned and
    not(worker.objects.contains(planned)) and event.receipt == absent

  val factorMatches = factorOf(event.wanted) == event.expectedFactor
  val ordinary = event.command == "publish" and not(event.aliasesMain) and event.failAt == 0
  val normal = ordinary and factorMatches
  val selectedPlanned = event.wanted == planned and event.before.returned == planned
  val mainMatches = event.before.main == event.expectedMain
  observation wrongCandidateStaged = event.command == "stage" and event.receipt == alternate
  observation createMain = normal and selectedPlanned and event.expectedMain == absent and event.receipt == planned
  observation updateMain = normal and selectedPlanned and event.expectedMain == previousMain and event.receipt == planned
  observation matchingAlternateAccepted = normal and event.receipt == alternate
  val wrongFactorRejected = ordinary and mainMatches and event.wanted == alternate and
    event.before.returned == alternate and event.expectedFactor == plannedFactor and event.receipt == absent and
    source == event.before
  observation wrongFactorCannotCreateMain = wrongFactorRejected and event.expectedMain == absent
  observation wrongFactorCannotUpdateMain = wrongFactorRejected and event.expectedMain == planned
  observation publishWithMovedProducerPin = normal and selectedPlanned and event.before.producerPin == decoy and
    event.receipt == planned
  observation wrongCandidateRejected = normal and mainMatches and event.wanted == planned and
    event.before.returned == alternate and event.before.objects.contains(planned) and event.receipt == absent
  observation wrongParentRejected = normal and mainMatches and event.wanted == wrongParent and
    event.before.returned == wrongParent and event.receipt == absent
  observation wrongInputRejected = normal and mainMatches and event.wanted == wrongInput and
    event.before.returned == wrongInput and event.receipt == absent
  observation wrongShapeRejected = normal and mainMatches and event.wanted == wrongShape and
    event.before.returned == wrongShape and event.receipt == absent
  observation movedStageRejected = normal and mainMatches and event.wanted == planned and
    event.before.returned == decoy and event.before.objects.contains(planned) and event.receipt == absent
  observation missingStageRejected = normal and mainMatches and event.wanted == planned and
    event.before.returned == absent and event.before.objects.contains(planned) and event.receipt == absent
  observation duplicatePublishRejected = normal and mainMatches and event.wanted == planned and
    event.expectedMain == planned and event.before.returned == absent and event.receipt == absent
  observation existingMainRejected = normal and selectedPlanned and event.expectedMain == absent and
    event.before.main == previousMain and event.receipt == absent
  observation staleMainRejected = normal and selectedPlanned and event.expectedMain == previousMain and
    event.before.main == competingMain and event.receipt == absent
  observation missingMainRejected = normal and selectedPlanned and event.expectedMain == previousMain and
    event.before.main == absent and event.receipt == absent
  observation aliasedMainRejected = event.command == "publish" and event.aliasesMain and selectedPlanned and
    factorMatches and event.expectedMain == planned and mainMatches and event.receipt == absent
  observation rollbackAfterMain = event.command == "publish" and not(event.aliasesMain) and selectedPlanned and
    factorMatches and mainMatches and event.expectedMain == previousMain and event.failAt == 1 and
    event.receipt == absent and source == event.before
  observation rollbackAfterDelete = event.command == "publish" and not(event.aliasesMain) and selectedPlanned and
    factorMatches and mainMatches and event.expectedMain == absent and event.failAt == 2 and
    event.receipt == absent and source == event.before
  observation readbackAfterSweep = event.command == "collect" and source.main == planned and
    source.returned == absent and source.producerPin == absent and event.before.objects.contains(decoy) and
    not(source.objects.contains(decoy)) and readableScale(planned, source.objects)
}
