module handoff_histories {
  // Application-level scenarios. Only paths cross between the handoff commands.
  // Fixture probes name independently read IDs, never IDs from the handoff report.
  type Request = { op: str, args: List[str] }
  type Cell = { kind: str, text: str }
  type Step = { call: Request, code: int, diagnostic: str, detail: str, layout: str,
    report: List[List[Cell]], distinct: List[(str, str)], readOnly: bool, absentRepo: bool, label: str }
  type Scenario = { name: str, steps: List[Step] }

  pure def text(value: str): Cell = { kind: "text", text: value }
  pure def capture(name: str): Cell = { kind: "capture", text: name }
  pure def saved(name: str): Cell = { kind: "saved", text: name }
  pure def request(op: str, args: List[str]): Step = {
    call: { op: op, args: args }, code: 0, diagnostic: "", detail: "", layout: "ignore",
    report: List(), distinct: List(), readOnly: false, absentRepo: false, label: "ok"
  }
  pure def handoff(args: List[str]): Step = request("handoff", args)
  pure def reject(stepDef: Step, why: str): Step = { ...stepDef, code: 1, diagnostic: why }
  pure def expectRows(stepDef: Step, rows: List[List[Cell]]): Step = { ...stepDef, layout: "ordered", report: rows }
  pure def differ(stepDef: Step, first: str, second: str): Step =
    { ...stepDef, distinct: stepDef.distinct.append((first, second)) }
  pure def probe(args: List[str], rows: List[List[Cell]]): Step = {
    val captures = rows.foldl(List(), (names, row) => row.foldl(names,
      (out, cell) => out.append(if (cell.kind == "capture") cell.text else "")))
    expectRows(request("fixture", args.append("--capture").concat(captures)), rows)
  }
  pure def setup(args: List[str]): Step = request("fixture", args.append("--capture"))
  pure def one(args: List[str], cell: Cell): Step = probe(args, List(List(cell)))

  pure val source = "@source"
  pure val worker = "@worker"
  pure val replica = "@replica"
  pure val reqFile = "@request.dml"
  pure val resultFile = "@result.dml"
  pure val retryFile = "@retry.dml"
  pure val add = "example.add-one@1"
  pure val subtract = "example.subtract-one@1"
  pure val unknown = "example.unknown@1"
  pure val wrongParent = "result parent does not match the original request"
  pure val wrongImplementation = "result implementation does not match the requested operation"
  pure val staleTip = "main no longer points to the original input snapshot"
  pure val missingPin = "resolve original request pin"
  pure val missingMain = "resolve main for publication"
  pure val unsupported = "unsupported request operation"
  pure val cannotRelease = "incoming does not point to the pinned result's request; cannot release input"
  pure val missing = text("missing")                 // fixture
  pure val notFound = text("not found")              // handoff report

  type Selection = { operation: str, entry: str, binding: str, value: str }
  pure val addition: Selection = { operation: add, entry: "snapshot", binding: "value", value: "43" }
  pure val subtraction: Selection = { ...addition, operation: subtract }
  pure val alternateAddition: Selection = {
    ...addition, entry: "alternate-snapshot", binding: "alternate-value", value: "343"
  }
  pure val alternateSubtraction: Selection = { ...alternateAddition, operation: subtract }

  pure def seed(path: str, shape: str, tip: Cell, ancestor: Cell): Step =
    probe(List("seed", path, shape), List(List(tip), List(ancestor)))
  pure val seedSource: Step = seed(source, "original", capture("input"), capture("ancestor"))
  pure def createRequest(path: str, bundle: str, choice: Selection): Step =
    handoff(List("request", path, bundle, choice.operation, choice.entry, choice.binding))
  pure def observeRequest(path: str, refName: str, id: Cell, tip: str, datum: Cell, choice: Selection): Step =
    probe(List("request", path, refName), List(List(id, saved(tip), datum, text(choice.value),
      text(choice.operation), text(choice.entry), text(choice.binding))))
  pure def newRequest(path: str, bundle: str, tip: str, id: str, datum: Cell, choice: Selection): List[Step] = List(
    createRequest(path, bundle, choice), differ(observeRequest(path, "request-pin", capture(id), tip, datum, choice), id, tip)
  )
  pure def defaultRequest(choice: Selection): List[Step] =
    newRequest(source, reqFile, "input", "request", capture("inputDatum"), choice)
  pure def work(path: str, result: str, bundle: str): Step = handoff(List("work", path, result, bundle))
  pure def stageResult(path: str, bundle: str): Step = handoff(List("stage-result", path, bundle))
  pure def publish(path: str): Step = handoff(List("publish", path))
  pure def transferResult(path: str, bundle: str): Step = handoff(List("publish", path, bundle))
  pure def refAt(path: str, refName: str, target: Cell): Step = one(List("ref", path, refName), target)
  pure def sourceRefs(path: str, main: Cell, pinned: Cell, staged: Cell): List[Step] = List(
    refAt(path, "main", main), refAt(path, "request-pin", pinned), refAt(path, "returned", staged)
  )
  pure def workerRefs(path: str, incoming: Cell, pinned: Cell): List[Step] = List(
    refAt(path, "main", missing), refAt(path, "incoming", incoming), refAt(path, "result-pin", pinned)
  )
  pure def changeRef(command: str, path: str, name: str, target: str): Step =
    setup(List(command, path, name, "$", target))
  pure def orphanCycle(path: str, alias: str): List[Step] = List(
    one(List("orphan", path), capture(alias)), one(List("datum", path, "$", alias), text("present")),
    one(List("collect", path), text("1")), one(List("datum", path, "$", alias), missing)
  )
  pure def fileMissing(path: str): Step = expectRows(request("read_file", List(path)), List(List(missing)))
  pure def fileContents(path: str, hex: str): Step =
    expectRows(request("read_file", List(path)), List(List(text("present"), text(hex))))

  type Lineage = { result: Cell, requested: str, snapshot: str, datum: str,
    outputDatum: Cell, operationDatum: Cell, inputValue: str, outputValue: str, implementation: str }
  pure def observeResult(path: str, refName: str, facts: Lineage): Step =
    probe(List("result", path, refName), List(List(facts.result, saved(facts.requested), saved(facts.snapshot),
      saved(facts.datum), facts.outputDatum, facts.operationDatum, text(facts.inputValue),
      text(facts.outputValue), text(facts.implementation))))
  pure def newResult(choice: Selection, output: str): Lineage = {
    result: capture("result"), requested: "request", snapshot: "input", datum: "inputDatum",
    outputDatum: capture("outputDatum"), operationDatum: capture("implementationDatum"),
    inputValue: choice.value, outputValue: output, implementation: choice.operation
  }
  pure def retained(facts: Lineage): Lineage = {
    ...facts, result: saved(facts.result.text), outputDatum: saved(facts.outputDatum.text),
    operationDatum: saved(facts.operationDatum.text)
  }

  // Inspection contract at the process boundary. Refs and request details are
  // checked against independently probed IDs and the requested selection. A
  // report is read-only even when it rejects the checkpoint or the arguments.
  pure def reportField(name: str, cell: Cell): List[Cell] = List(text(name), cell)
  pure def selection(requestId: str, inputId: str, choice: Selection): List[List[Cell]] = List(
    reportField("request", saved(requestId)), reportField("input", saved(inputId)),
    reportField("operation", text(choice.operation)), reportField("input-entry", text(choice.entry)),
    reportField("input-binding", text(choice.binding))
  )
  pure def inspect(role: str, path: str, label: str, report: List[List[Cell]], blocker: str): Step = {
    val invocation = handoff(List("inspect", role, path))
    val outcome = if (blocker == "") invocation else reject(invocation, blocker)
    { ...outcome, readOnly: true, layout: "fields", report: report, label: label }
  }
  pure def inspectSource(path: str, main: Cell, pinned: Cell, staged: Cell,
                         details: List[List[Cell]], label: str, blocker: str): Step = {
    // This is readiness *in the observed snapshot*, not permission to write later.
    val checkpoint = if (staged != notFound) "result-staged" else if (pinned != notFound) "request-pinned" else "inactive"
    val readiness = if (staged == notFound) "not staged" else if (blocker == "") "ready in this snapshot" else "blocked"
    inspect("source", path, label, List(
      reportField("main", main), reportField("request-pin", pinned), reportField("returned", staged),
      reportField("checkpoint", text(checkpoint)), reportField("publication", text(readiness))
    ).concat(details), blocker)
  }
  // Ordered source checks for fixture-probed lineage of valid shape. Aliases
  // here name identities that the earlier probes require to match or differ.
  pure def publicationBlocker(main: Cell, pinned: Cell, inputId: str, operation: str, facts: Lineage): str =
    if (pinned == notFound) missingPin
    else if (pinned != saved(facts.requested)) wrongParent
    else if (operation != facts.implementation) wrongImplementation
    else if (main == notFound) missingMain
    else if (main != saved(inputId)) staleTip
    else ""
  pure def inspectStaged(path: str, main: Cell, pinned: Cell, inputId: str,
                         choice: Selection, facts: Lineage, label: str): Step = {
    val details = if (pinned == notFound) List() else selection(pinned.text, inputId, choice)
    inspectSource(path, main, pinned, facts.result, details, label,
      publicationBlocker(main, pinned, inputId, choice.operation, facts))
  }
  pure def inspectWorker(path: str, incoming: Cell, pinned: Cell,
                         details: List[List[Cell]], label: str, blocker: str): Step = {
    val checkpoint = if (pinned != notFound) "result-pinned" else if (incoming != notFound) "request-staged" else "inactive"
    inspect("worker", path, label, List(
      reportField("incoming", incoming), reportField("result-pin", pinned), reportField("checkpoint", text(checkpoint))
    ).concat(details), blocker)
  }
  pure def inspectPinnedWorker(path: str, incoming: Cell, choice: Selection, facts: Lineage, label: str): Step = {
    val expectedRequest = saved(facts.requested)
    val blocker = if (incoming == notFound or incoming == expectedRequest) "" else cannotRelease
    inspectWorker(path, incoming, facts.result, selection(facts.requested, facts.snapshot, choice), label, blocker)
  }

  pure val direct: Scenario = {
    val result = newResult(alternateAddition, "344")
    { name: "direct", steps: List(seedSource).concat(defaultRequest(alternateAddition)).concat(List(
      work(worker, resultFile, reqFile), transferResult(source, resultFile),
      observeResult(worker, "result-pin", result), observeResult(source, "main", retained(result))
    )).concat(sourceRefs(source, saved("result"), missing, missing))
      .concat(workerRefs(worker, saved("request"), saved("result"))) }
  }

  pure val distinctOperations: Scenario = {
    val subtractBundle = "@subtract.dml"
    val subtractResult = "@subtract-result.dml"
    val subtractWorker = "@subtract-worker"
    val addResult = newResult(addition, "44")
    val result = { ...newResult(subtraction, "42"), requested: "subtractRequest", result: capture("subResult"),
      outputDatum: capture("subOutputDatum"), operationDatum: capture("subImplementationDatum") }
    { name: "distinct-operations", steps: List(seedSource, seed(replica, "original", saved("input"), saved("ancestor")))
      .concat(defaultRequest(addition)).concat(List(
        createRequest(replica, subtractBundle, subtraction),
        differ(observeRequest(replica, "request-pin", capture("subtractRequest"), "input", saved("inputDatum"),
          subtraction), "request", "subtractRequest"),
        work(worker, resultFile, reqFile), observeResult(worker, "result-pin", addResult),
        work(subtractWorker, subtractResult, subtractBundle), observeResult(subtractWorker, "result-pin", result),
        transferResult(replica, subtractResult), observeResult(replica, "main", retained(result))
      )).concat(sourceRefs(replica, saved("subResult"), missing, missing))
      // Same input snapshot and datum, different computation request.
      .append(reject(transferResult(source, subtractResult), wrongParent))
      .concat(sourceRefs(source, saved("input"), saved("request"), saved("subResult")))
      .concat(List(observeResult(source, "returned", retained(result)),
        differ(one(List("compete", source), capture("competitor")), "input", "competitor"),
        // Even if main is stale, an unrelated result must fail on its parent first.
        inspectStaged(source, saved("competitor"), saved("request"), "input", addition,
          retained(result), "wrong-parent-before-stale-tip"),
        reject(publish(source), wrongParent)
      )) }
  }

  pure val restart: Scenario = {
    val choice = alternateSubtraction
    val details = selection("request", "input", choice)
    val pinned = saved("request")
    val staged = saved("result")
    val result = newResult(choice, "342")
    { name: "restart-and-collect", steps: List(seedSource,
        { ...inspect("worker", worker, "missing-repository", List(), worker), absentRepo: true,
          detail: "repository path does not exist" },
        { ...inspect("other", worker, "invalid-role", List(), "usage:"), absentRepo: true },
        inspectWorker(source, notFound, notFound, List(), "worker-inactive", ""),
        inspectSource(source, saved("input"), notFound, notFound, List(), "source-inactive", "")
      ).concat(defaultRequest(choice)).concat(sourceRefs(source, saved("input"), pinned, missing))
      .append(inspectSource(source, saved("input"), pinned, notFound, details, "request-pinned", ""))
      .concat(orphanCycle(source, "sourceOrphan")).concat(List(
        setup(List("stage-input", worker, reqFile)), request("remove_file", List(reqFile))
      )).concat(workerRefs(worker, pinned, missing))
      .append(inspectWorker(worker, pinned, notFound, details, "request-staged", ""))
      .concat(orphanCycle(worker, "stagedOrphan")).concat(List(
        request("write_file", List(resultFile, "do not overwrite")),
        reject(handoff(List("work", worker, resultFile)), resultFile),
        fileContents(resultFile, "646f206e6f74206f7665727772697465"),
        observeResult(worker, "result-pin", result),
        inspectPinnedWorker(worker, pinned, choice, retained(result), "result-pinned")
      )).concat(orphanCycle(worker, "pinnedOrphan")).append(handoff(List("work", worker, retryFile)))
      .concat(workerRefs(worker, pinned, staged)).concat(List(
        stageResult(source, retryFile), request("remove_file", List(retryFile))
      )).concat(sourceRefs(source, saved("input"), pinned, staged)).concat(orphanCycle(source, "returnedOrphan"))
      .concat(List(observeResult(source, "returned", retained(result)),
        inspectStaged(source, saved("input"), pinned, "input", choice, retained(result), "publication-ready"), publish(source)
      )).concat(sourceRefs(source, staged, missing, missing))
      .append(inspectSource(source, staged, notFound, notFound, List(), "source-after-publish", ""))
      .concat(orphanCycle(source, "publishedOrphan")).concat(List(
        observeResult(source, "main", retained(result)), changeRef("retarget", worker, "incoming", "input"),
        inspectPinnedWorker(worker, saved("input"), choice, retained(result), "release-blocked"),
        reject(handoff(List("release-input", worker)), "release inspected staging ref")
      )).concat(workerRefs(worker, saved("input"), staged)).concat(List(
        observeResult(worker, "result-pin", retained(result)), changeRef("retarget", worker, "incoming", "request"),
        handoff(List("release-input", worker))
      )).concat(workerRefs(worker, missing, staged))
      .append(inspectPinnedWorker(worker, notFound, choice, retained(result), "result-retained"))
      .concat(orphanCycle(worker, "releasedOrphan")).append(observeResult(worker, "result-pin", retained(result))) }
  }

  pure val wrongSnapshot: Scenario = {
    val other = "@alternate"
    val otherRequest = "@alternate.dml"
    val otherWorker = "@wrong-worker"
    val otherBundle = "@wrong.dml"
    val correct = newResult(addition, "44")
    // Same scalar values and datums, different request/result ancestry.
    val wrong = { ...retained(correct), result: capture("wrongResult"),
      requested: "otherRequest", snapshot: "otherInput" }
    { name: "wrong-snapshot", steps: List(seedSource,
        differ(seed(other, "alternate", capture("otherInput"), capture("otherAncestor")), "input", "otherInput")
      ).concat(defaultRequest(addition)).concat(List(
        work(worker, resultFile, reqFile), observeResult(worker, "result-pin", correct)
      )).concat(newRequest(other, otherRequest, "otherInput", "otherRequest", saved("inputDatum"), addition))
      .concat(List(work(otherWorker, otherBundle, otherRequest),
        differ(differ(observeResult(otherWorker, "result-pin", wrong), "result", "wrongResult"),
          "request", "otherRequest"), reject(transferResult(source, otherBundle), wrongParent)
      )).concat(sourceRefs(source, saved("input"), saved("request"), saved("wrongResult")))
      .concat(orphanCycle(source, "orphan")).append(observeResult(source, "returned", retained(wrong))) }
  }

  pure val wrongClaim: Scenario = {
    val result = { ...newResult(addition, "44"), result: saved("result"), implementation: subtract }
    { name: "wrong-implementation", steps: List(seedSource).concat(defaultRequest(addition)).concat(List(
      setup(List("stage-input", worker, reqFile)),
      one(List("forge-result", worker, resultFile), capture("result")),
      observeResult(worker, "fixture-result", result), stageResult(source, resultFile),
      inspectStaged(source, saved("input"), saved("request"), "input", addition, retained(result), "wrong-implementation"),
      reject(publish(source), wrongImplementation)
    )).concat(sourceRefs(source, saved("input"), saved("request"), saved("result")))
      .append(observeResult(source, "returned", retained(result))).concat(List(
        differ(one(List("compete", source), capture("competitor")), "input", "competitor"),
        inspectStaged(source, saved("competitor"), saved("request"), "input", addition, retained(result),
          "wrong-implementation-before-stale-tip"), reject(publish(source), wrongImplementation)
      )).concat(sourceRefs(source, saved("competitor"), saved("request"), saved("result"))) }
  }

  pure val unknownOperation: Scenario = {
    val choice = { ...addition, operation: unknown }
    val noPins = sourceRefs(source, saved("input"), missing, missing)
    { name: "unsupported-operation", steps: List(seedSource,
      reject(handoff(List("request", source, reqFile)), "recover request pin"), fileMissing(reqFile)
    ).concat(noPins).concat(List(reject(createRequest(source, reqFile, choice), unsupported), fileMissing(reqFile)))
      .concat(noPins).concat(List(one(List("forge-request", source, reqFile), capture("request")),
        differ(observeRequest(source, "fixture-request", saved("request"), "input", capture("inputDatum"), choice),
          "input", "request"),
        reject(work(worker, resultFile, reqFile), unsupported), fileMissing(resultFile)
      )).concat(workerRefs(worker, saved("request"), missing))
      .append(inspectWorker(worker, saved("request"), notFound, List(), "unsupported-operation", unsupported)) }
  }

  pure val noRecompute: Scenario = {
    // The fixture claims the right operation and exact parent, but its scalar
    // is not add-one(43). Inspect and publish check lineage, not execution.
    val result = { ...newResult(addition, "900"), result: saved("result") }
    { name: "does-not-recompute", steps: List(seedSource).concat(defaultRequest(addition)).concat(List(
      setup(List("stage-input", worker, reqFile)),
      one(List("forge-output", worker, resultFile), capture("result")),
      observeResult(worker, "fixture-result", result), stageResult(source, resultFile),
      inspectStaged(source, saved("input"), saved("request"), "input", addition, retained(result), "no-recompute"),
      publish(source), observeResult(source, "main", retained(result))
    )).concat(sourceRefs(source, saved("result"), missing, missing)) }
  }

  pure val withoutPin: Scenario = {
    val result = newResult(addition, "44")
    { name: "no-request-pin", steps: List(seedSource).concat(defaultRequest(addition)).concat(List(
      work(worker, resultFile, reqFile), observeResult(worker, "result-pin", result),
      seed(replica, "original", saved("input"), saved("ancestor")), stageResult(replica, resultFile),
      inspectStaged(replica, saved("input"), notFound, "input", addition, retained(result), "missing-request-pin"),
      reject(publish(replica), missingPin)
    )).concat(sourceRefs(replica, saved("input"), missing, saved("result"))) }
  }

  pure val stale: Scenario = {
    val occupied = "@occupied.dml"
    val result = newResult(addition, "44")
    val pinned = saved("request")
    val staged = saved("result")
    val competitor = saved("competitor")
    { name: "stale-tip", steps: List(seedSource, request("write_file", List(occupied, "already here")),
      reject(createRequest(source, occupied, addition), occupied), fileContents(occupied, "616c72656164792068657265"),
      differ(observeRequest(source, "request-pin", capture("request"), "input", capture("inputDatum"), addition),
        "input", "request"),
      differ(one(List("compete", source), capture("competitor")), "input", "competitor")
    ).concat(sourceRefs(source, competitor, pinned, missing)).concat(List(
      reject(createRequest(source, reqFile, subtraction), "request-pin already exists; omit the operation and selector to resume"),
      fileMissing(reqFile)
    )).concat(sourceRefs(source, competitor, pinned, missing)).concat(orphanCycle(source, "beforeReturn"))
      .concat(List(handoff(List("request", source, reqFile)), work(worker, resultFile, reqFile),
        observeResult(worker, "result-pin", result), stageResult(source, resultFile),
        inspectStaged(source, competitor, pinned, "input", addition, retained(result), "stale-tip"),
        reject(publish(source), staleTip)
      )).concat(sourceRefs(source, competitor, pinned, staged)).concat(orphanCycle(source, "afterReject"))
      .concat(List(observeResult(source, "returned", retained(result)), changeRef("drop-ref", source, "main", "competitor"),
        inspectStaged(source, notFound, pinned, "input", addition, retained(result), "missing-main"),
        reject(publish(source), missingMain)
      )).concat(sourceRefs(source, missing, pinned, staged)) }
  }

  pure val scenarios: List[Scenario] = List(direct, distinctOperations, restart, wrongSnapshot, wrongClaim,
    unknownOperation, withoutPin, stale, noRecompute)
  var histories: List[List[Request]]
  action init = histories' = scenarios.foldl(List(), (out, scenario) =>
    out.append(scenario.steps.foldl(List(), (calls, stepDef) => calls.append(stepDef.call))))
  action step = histories' = histories
}
