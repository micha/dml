// Finite design for quint verify --backend=tlc (not implementation replay).
module recorded_handoff_design {
  // One independently retained expected ID. Two same-valued sums have
  // distinct commit and DAG IDs. Integer IDs stand for immutable records;
  // each DAG ID represents its entire closure, and each commit includes its
  // private tree. A result represents a scale by 3, with both lineage edges.
  // No collisions, I/O failures, ref aliases, or native corruption are modeled.
  pure val expected = 1
  pure val decoy = 2
  pure val sums = Set(expected, decoy)
  pure val plannedResult = 11
  pure val otherResult = 12
  pure val wrongInputResult = 13  // A readable commit with a mismatched input DAG.
  pure val brokenBundle = -1
  pure def sumDag(commit: int): int = 100 + commit
  pure def sumValue(_commit: int): int = 12
  pure def parentOf(result: int): int = if (result == otherResult) decoy else expected
  pure def inputOf(result: int): int = if (result == plannedResult) sumDag(expected) else sumDag(decoy)
  pure def scaleId(parent: int, input: int): int =
    if (parent == decoy) otherResult else if (input == sumDag(expected)) plannedResult else wrongInputResult
  pure def closure(root: int): Set[int] =
    if (root == 0) Set()
    else if (sums.contains(root)) Set(root, sumDag(root))
    else Set(root, parentOf(root), sumDag(parentOf(root)), inputOf(root))

  type Origin = { pin: int, objects: Set[int] }
  type Worker = { incoming: int, result: int, objects: Set[int] }
  type Event = { command: str, argument: int, receipt: int, before: Worker }
  pure val emptyWorker: Worker = { incoming: 0, result: 0, objects: Set() }
  pure val noEvent: Event = { command: "", argument: 0, receipt: 0, before: emptyWorker }
  pure def roots(snapshot: Worker): Set[int] = closure(snapshot.incoming).union(closure(snapshot.result))
  pure def inspect(snapshot: Worker): int = {
    val result = snapshot.result
    if (result != 0 and closure(result).subseteq(snapshot.objects) and inputOf(result) == sumDag(parentOf(result)))
      result
    else 0
  }

  var origin: Origin
  var selected: int   // In-flight export ticket; 0 means no accepted selection.
  var bundle: int     // Last successful export's root, not a ref or an expected ID.
  var worker: Worker
  var event: Event

  action init = all {
    origin' = { pin: expected, objects: closure(expected).union(closure(decoy)) },
    selected' = 0,
    bundle' = 0,
    worker' = emptyWorker,
    event' = noEvent
  }

  // A producer-pin read/validation and export-by-ID can use two snapshots.
  // Pin movement alone cannot change the export ID; collection can remove it.
  action selectSum = {
    val accepted = if (origin.pin == expected) origin.pin else 0
    all {
      selected == 0,
      selected' = accepted,
      bundle' = bundle,
      origin' = origin,
      worker' = worker,
      event' = { ...noEvent, command: "select", receipt: accepted }
    }
  }

  action exportSum = {
    val exported = if (origin.objects.contains(selected)) selected else 0
    all {
      selected != 0,
      selected' = 0,
      bundle' = if (exported != 0) exported else bundle,
      origin' = origin,
      worker' = worker,
      event' = { ...noEvent, command: "export", argument: bundle, receipt: exported }
    }
  }

  action changeOrigin(target: int): bool = all {
    target == 0 or origin.objects.contains(target),
    origin' = { ...origin, pin: target },
    selected' = selected,
    bundle' = bundle,
    worker' = worker,
    event' = noEvent
  }

  action collectOrigin = all {
    origin' = { ...origin, objects: closure(origin.pin) },
    selected' = selected,
    bundle' = bundle,
    worker' = worker,
    event' = noEvent
  }

  action updateWorker(updated: Worker, evidence: Event): bool = all {
    origin' = origin,
    selected' = selected,
    bundle' = bundle,
    worker' = updated,
    event' = evidence
  }

  // The incoming file can be the one exported, a valid but incorrect file,
  // or malformed bytes. Staging does not compare against the plan.
  action stage(actual: int): bool = {
    val accepted = worker.incoming == 0 and actual != brokenBundle
    val updated = if (accepted) { ...worker, incoming: actual, objects: worker.objects.union(closure(actual)) }
      else worker
    updateWorker(updated, { command: "stage", argument: actual, receipt: if (accepted) actual else 0, before: worker })
  }

  action scale = {
    val accepted = worker.incoming == expected and worker.result == 0
    val product = scaleId(worker.incoming, sumDag(worker.incoming))
    val updated = if (accepted) { ...worker, result: product, objects: worker.objects.union(closure(product)) }
      else worker
    updateWorker(updated, { ...noEvent, command: "scale", receipt: if (accepted) product else 0, before: worker })
  }

  action release = {
    // Validate the result in the same write transaction as the expected delete.
    val inspected = inspect(worker)
    val accepted = inspected != 0 and parentOf(inspected) == expected and worker.incoming == expected
    val updated = if (accepted) { ...worker, incoming: 0 } else worker
    updateWorker(updated, { ...noEvent, command: "release", receipt: if (accepted) expected else 0, before: worker })
  }

  action collectWorker = updateWorker({ ...worker, objects: roots(worker) },
    { ...noEvent, command: "collect", before: worker })

  // Other writers can insert an unpinned decoy closure, move an existing
  // incoming pin to a present sum, or occupy the result ref. These actions
  // interleave between commands, never within a worker write transaction.
  action addDecoy = updateWorker({ ...worker, objects: worker.objects.union(closure(decoy)) }, noEvent)
  action moveIncoming(target: int): bool = all {
    worker.incoming != 0 and worker.objects.contains(target),
    updateWorker({ ...worker, incoming: target }, noEvent)
  }
  action occupyResult(result: int): bool = all {
    worker.result == 0,
    updateWorker({ ...worker, result: result, objects: worker.objects.union(closure(result)) }, noEvent)
  }

  action step = any {
    selectSum,
    exportSum,
    nondet target = sums.union(Set(0)).oneOf()
    changeOrigin(target),
    collectOrigin,
    nondet actual = Set(bundle, decoy, brokenBundle).exclude(Set(0)).oneOf()
    stage(actual),
    scale,
    release,
    collectWorker,
    addDecoy,
    nondet target = sums.oneOf()
    moveIncoming(target),
    nondet result = Set(otherResult, wrongInputResult).oneOf()
    occupyResult(result)
  }

  val exactExport = all {
    Set(0, expected).contains(selected),
    Set(0, expected).contains(bundle),
    if (event.command == "select") event.receipt == (if (origin.pin == expected) expected else 0) else true,
    if (event.command == "export") {
      val wanted = if (origin.objects.contains(expected)) expected else 0
      event.receipt == wanted and bundle == (if (wanted == 0) event.argument else expected)
    } else true
  }

  val atomicStage = if (event.command != "stage") true else {
    val before = event.before
    val submitted = event.argument
    if (before.incoming != 0 or submitted == brokenBundle) event.receipt == 0 and worker == before
    else all {
      event.receipt == submitted,
      worker.incoming == submitted,
      worker.result == before.result,
      worker.objects == before.objects.union(closure(submitted))
    }
  }

  val exactScale = if (event.command != "scale") true else {
    val before = event.before
    if (before.incoming != expected or before.result != 0) event.receipt == 0 and worker == before
    else all {
      worker.result != 0,
      event.receipt == worker.result,
      parentOf(worker.result) == expected,
      inputOf(worker.result) == sumDag(expected),
      worker.incoming == before.incoming,
      worker.objects == before.objects.union(closure(worker.result))
    }
  }

  val guardedRelease = if (event.command != "release") true else {
    val before = event.before
    val verified = before.result != 0 and parentOf(before.result) == expected and inputOf(before.result) == sumDag(expected)
    if (verified and before.incoming == expected) all {
      event.receipt == expected,
      worker == { ...before, incoming: 0 }
    } else event.receipt == 0 and worker == before
  }

  val retainedAndInspectable = all {
    closure(origin.pin).subseteq(origin.objects),
    roots(worker).subseteq(worker.objects),
    if (worker.result == plannedResult or worker.result == otherResult) inspect(worker) == worker.result
    else inspect(worker) == 0,
    if (event.command == "collect") worker.objects == roots(event.before) else true
  }

  // These observations must be reachable; they are not invariants.
  observation movedExportRejected = event.command == "select" and origin.pin == decoy and event.receipt == 0
  observation exportSelectedDespiteMove = event.command == "export" and origin.pin == decoy and event.receipt == expected
  observation exportAfterSweepRejected = event.command == "export" and not(origin.objects.contains(expected)) and event.receipt == 0
  observation wrongBundleStaged = event.command == "stage" and event.argument == decoy and event.receipt == decoy
  observation badBundleRejected = event.command == "stage" and event.argument == brokenBundle and event.before.incoming == 0
    and event.receipt == 0
  observation sameBundleRejected = event.command == "stage" and event.before.incoming == expected and event.argument == expected
    and event.receipt == 0
  observation sameValueWrongProducerRejected = event.command == "scale" and event.before.incoming == decoy
    and event.before.result == 0 and sumValue(decoy) == sumValue(expected) and event.receipt == 0
  observation releaseWithoutResultRejected = event.command == "release" and event.before.incoming == expected
    and event.before.result == 0 and event.receipt == 0
  observation wrongParentReleaseRejected = event.command == "release" and event.before.incoming == expected
    and event.before.result == otherResult and event.receipt == 0
  observation wrongInputReleaseRejected = event.command == "release" and event.before.incoming == expected
    and event.before.result == wrongInputResult and event.receipt == 0
  observation movedIncomingReleaseRejected = event.command == "release" and event.before.incoming == decoy
    and event.before.result == plannedResult and event.receipt == 0
  observation readbackAfterReleaseAndSweep = event.command == "collect" and worker.incoming == 0
    and event.before.objects.contains(decoy) and not(worker.objects.contains(decoy)) and inspect(worker) == plannedResult
}
