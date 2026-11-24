module recorded_calls_rules {
  import recorded_calls_histories.* from "./recorded_calls_histories"

  type Argument = { name: str, node: str, value: int, producer: str }
  type Call = { dag: str, implementation: str, resultNode: str, resultValue: int, arguments: List[Argument] }
  type Publication = { planRef: str, plan: str, stagingRef: str, result: str }
  type ReusePublication = { mode: str, planRef: str, plan: str, resultRef: str, result: str }
  type Attempt = { op: str, args: List[str], code: int, quiet: bool, diagnosed: bool, missingRef: bool,
    commit: str, calls: List[Call],
    expectedCommit: str, producerCommit: str, unchanged: bool, removed: int,
    expectedResult: str, expectedMain: str, requestCommit: str, requestImplementation: str, requestFactor: int,
    bundlePresent: bool, bundleUnchanged: bool, publication: Publication, reusePublication: ReusePublication }
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure def literal(arg: Argument, name: str, value: int): bool =
    arg.name == name and arg.producer == "" and arg.node != "" and arg.value == value

  pure def checkSum(s: Scenario, summed: Call): bool =
    if (summed.arguments.length() != 2) false
    else all {
      summed.dag != "", summed.resultNode != "", summed.implementation == "example.sum@1",
      literal(summed.arguments[0], "a", s.a._2), literal(summed.arguments[1], "b", s.b._2),
      summed.resultValue == s.a._2 + s.b._2
    }

  pure val scaleV1 = "example.scale@1"
  pure val scaleV2 = "example.scale@2"

  pure def checkCalls(s: Scenario, calls: List[Call], implementation: str): bool = {
    if (calls.length() != 2) false
    else {
      val summed = calls[0]
      val scaled = calls[1]
      if (not(checkSum(s, summed)) or scaled.arguments.length() != 2) false
      else {
        val combined = s.a._2 + s.b._2
        val input = scaled.arguments[1] // Runner sorts the argument names.
        all {
          scaled.dag != "", scaled.dag != summed.dag, scaled.resultNode != "",
          scaled.implementation == implementation, literal(scaled.arguments[0], "factor", s.factor._2),
          input.name == "input", input.producer == summed.dag, input.node != "", input.node != summed.resultNode,
          input.value == combined, scaled.resultValue == combined * s.factor._2
        }
      }
    }
  }

  pure def sameRequest(attempt: Attempt, request: Request): bool =
    attempt.op == request.op and attempt.args == request.args

  pure def matches(attempt: Attempt, request: Request): bool =
    sameRequest(attempt, request) and attempt.code == 0 and attempt.quiet

  pure def writeVerdict(write: Attempt, request: Request): str =
    if (matches(write, request) and write.commit != "") "recorded" else "wrong_record"

  pure def togetherVerdicts(row: Observation): List[str] = {
    if (not(scenarios.indices().contains(row.scenario)) or row.attempts.length() != 2) List("missing_steps")
    else {
      val scenario = scenarios[row.scenario]
      val expected = requests(scenario)
      val write = row.attempts[0]
      val readback = row.attempts[1]
      List(
        writeVerdict(write, expected[0]),
        if (not(matches(readback, expected[1]))) "wrong_inspect"
        else if (not(readback.unchanged)) "storage_changed"
        else if (readback.commit != write.commit) "wrong_commit"
        else if (not(checkCalls(scenario, readback.calls, scaleV1))) "wrong_graph"
        else "inspected"
      )
    }
  }

  pure val selected: Scenario = { a: ("7", 7), b: ("5", 5), factor: ("3", 3) }
  pure val decoy: Scenario = { a: ("8", 8), b: ("4", 4), factor: ("3", 3) }

  pure def sumReadVerdict(s: Scenario, readback: Attempt, request: Request, recordedCommit: str): str =
    if (not(matches(readback, request))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit != recordedCommit or readback.producerCommit != "") "wrong_commit"
    else if (readback.calls.length() != 1) "wrong_graph"
    else if (checkSum(s, readback.calls[0])) "inspected" else "wrong_graph"

  pure def versionedScaleRead(s: Scenario, readback: Attempt, request: Request, recordedCommit: str,
                              sumRead: Attempt, implementation: str): str =
    if (not(matches(readback, request))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit != recordedCommit or readback.producerCommit != sumRead.commit) "wrong_commit"
    else if (not(checkCalls(s, readback.calls, implementation))) "wrong_graph"
    else if (sumRead.calls.length() != 1) "missing_producer"
    else if (readback.calls[0] != sumRead.calls[0]) "wrong_producer"
    else "inspected"

  pure def scaleReadVerdict(s: Scenario, readback: Attempt, request: Request, recordedCommit: str,
                            sumRead: Attempt): str =
    versionedScaleRead(s, readback, request, recordedCommit, sumRead, scaleV1)

  pure def scaleWriteVerdict(write: Attempt, request: Request, expectedCommit: str): str =
    if (write.expectedCommit != expectedCommit) "wrong_selection" else writeVerdict(write, request)

  pure def rejectedWriteVerdict(write: Attempt, request: Request, expectedCommit: str): str =
    if (not(sameRequest(write, request)) or write.expectedCommit != expectedCommit) "wrong_selection"
    else if (write.code != 1 or not(write.diagnosed) or write.commit != "") "wrong_rejection"
    else if (not(write.unchanged)) "storage_changed"
    else "rejected"

  pure def separateVerdicts(attempts: List[Attempt]): List[str] = {
    if (attempts.length() != splitRequests.length()) List("missing_steps")
    else {
      val first = attempts[0].commit
      val second = attempts[1].commit
      val firstRead = attempts[2]
      val secondRead = attempts[3]
      List(
        writeVerdict(attempts[0], splitRequests[0]),
        writeVerdict(attempts[1], splitRequests[1]),
        sumReadVerdict(selected, firstRead, splitRequests[2], first),
        sumReadVerdict(decoy, secondRead, splitRequests[3], second),
        rejectedWriteVerdict(attempts[4], splitRequests[4], first),  // stale pin
        rejectedWriteVerdict(attempts[5], splitRequests[5], first),  // missing pin
        rejectedWriteVerdict(attempts[6], splitRequests[6], first),  // overflow
        scaleWriteVerdict(attempts[7], splitRequests[7], first),
        rejectedWriteVerdict(attempts[8], splitRequests[8], second), // existing result ref
        scaleWriteVerdict(attempts[9], splitRequests[9], second),
        scaleReadVerdict(selected, attempts[10], splitRequests[10], attempts[7].commit, firstRead),
        scaleReadVerdict(decoy, attempts[11], splitRequests[11], attempts[9].commit, secondRead)
      )
    }
  }

  pure def exportedBundle(attempt: Attempt): str =
    if (not(attempt.unchanged)) "storage_changed"
    else if (not(attempt.bundlePresent) or attempt.bundleUnchanged) "wrong_bundle"
    else "exported"

  pure def exportVerdict(attempt: Attempt, request: Request, expected: str): str =
    if (not(matches(attempt, request)) or attempt.expectedCommit != expected or attempt.commit != expected) "wrong_export"
    else exportedBundle(attempt)

  pure def rejectedExport(attempt: Attempt, request: Request, expected: str, existed: bool): str = {
    val verdict = rejectedWriteVerdict(attempt, request, expected)
    if (verdict != "rejected") verdict
    else if (attempt.bundlePresent != existed or not(attempt.bundleUnchanged)) "wrong_bundle"
    else verdict
  }

  pure def stageVerdict(attempt: Attempt, request: Request, actual: str): str =
    if (not(attempt.bundlePresent) or not(attempt.bundleUnchanged)) "wrong_bundle"
    else if (actual == "") rejectedWriteVerdict(attempt, request, "") // occupied staging name
    else if (not(matches(attempt, request)) or attempt.commit != actual) "wrong_stage"
    else "staged"

  pure def releaseVerdict(attempt: Attempt, request: Request, expected: str): str =
    if (not(matches(attempt, request)) or attempt.expectedCommit != expected or attempt.commit != expected) "wrong_release"
    else "released"

  pure def collectVerdict(attempt: Attempt, request: Request): str =
    if (matches(attempt, request) and attempt.removed == 0) "collected" else "wrong_collection"

  pure def handoffVerdicts(attempts: List[Attempt]): List[str] = {
    val req = handoffRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val other = attempts[1].commit
      val sumRead = attempts[2]
      val result = attempts[15].commit
      List(
        writeVerdict(attempts[0], req[0]),
        writeVerdict(attempts[1], req[1]),
        sumReadVerdict(selected, sumRead, req[2], producer),
        sumReadVerdict(decoy, attempts[3], req[3], other),
        rejectedExport(attempts[4], req[4], producer, false),
        exportVerdict(attempts[5], req[5], producer),
        exportVerdict(attempts[6], req[6], other),
        rejectedExport(attempts[7], req[7], other, true),
        stageVerdict(attempts[8], req[8], other),
        rejectedWriteVerdict(attempts[9], req[9], producer),
        stageVerdict(attempts[10], req[10], ""),
        sumReadVerdict(decoy, attempts[11], req[11], other),
        stageVerdict(attempts[12], req[12], producer),
        rejectedWriteVerdict(attempts[13], req[13], producer), // no result yet
        sumReadVerdict(selected, attempts[14], req[14], producer),
        scaleWriteVerdict(attempts[15], req[15], producer),
        scaleReadVerdict(selected, attempts[16], req[16], result, sumRead),
        rejectedWriteVerdict(attempts[17], req[17], producer), // same-valued but wrong pin
        rejectedWriteVerdict(attempts[18], req[18], other), // wrong result parent
        releaseVerdict(attempts[19], req[19], producer),
        collectVerdict(attempts[20], req[20]),
        rejectedWriteVerdict(attempts[21], req[21], ""), // incoming is gone
        scaleReadVerdict(selected, attempts[22], req[22], result, sumRead),
        rejectedWriteVerdict(attempts[23], req[23], ""), // main never published
        sumReadVerdict(selected, attempts[24], req[24], producer)
      )
    }
  }

  pure def publishVerdict(attempt: Attempt, request: Request, result: str, producer: str, main: str,
                          accepted: bool): str =
    if (attempt.expectedResult != result or attempt.expectedMain != main or attempt.expectedCommit != producer)
      "wrong_selection"
    else if (not(accepted)) rejectedWriteVerdict(attempt, request, producer)
    else if (not(matches(attempt, request)) or attempt.commit != result or attempt.unchanged) "wrong_publication"
    else "published"

  pure def returnVerdicts(attempts: List[Attempt]): List[str] = {
    val req = returnRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val decoyCommit = attempts[1].commit
      val sumRead = attempts[2]
      val result = attempts[5].commit
      val revised = attempts[6].commit
      val originalCall: Scenario = { ...selected, b: ("-7", -7) }
      val revisedCall = { ...originalCall, factor: ("-2", -2) }
      List(
        writeVerdict(attempts[0], req[0]),
        writeVerdict(attempts[1], req[1]),
        sumReadVerdict(originalCall, sumRead, req[2], producer),
        exportVerdict(attempts[3], req[3], producer),
        stageVerdict(attempts[4], req[4], producer),
        scaleWriteVerdict(attempts[5], req[5], producer),
        scaleWriteVerdict(attempts[6], req[6], producer),
        releaseVerdict(attempts[7], req[7], producer),
        collectVerdict(attempts[8], req[8]),
        scaleReadVerdict(originalCall, attempts[9], req[9], result, sumRead),
        rejectedExport(attempts[10], req[10], revised, false),
        exportVerdict(attempts[11], req[11], result),
        exportVerdict(attempts[12], req[12], revised),
        stageVerdict(attempts[13], req[13], result),
        scaleReadVerdict(originalCall, attempts[14], req[14], result, sumRead),
        publishVerdict(attempts[15], req[15], result, decoyCommit, "-", false), // wrong producer
        publishVerdict(attempts[16], req[16], result, producer, result, false), // missing main
        publishVerdict(attempts[17], req[17], result, producer, "-", true),
        rejectedWriteVerdict(attempts[18], req[18], ""), // staging ref released
        scaleReadVerdict(originalCall, attempts[19], req[19], result, sumRead),
        stageVerdict(attempts[20], req[20], revised),
        publishVerdict(attempts[21], req[21], result, producer, result, false), // moved staging
        publishVerdict(attempts[22], req[22], revised, producer, "-", false), // main exists
        publishVerdict(attempts[23], req[23], revised, producer, revised, false), // main moved
        publishVerdict(attempts[24], req[24], revised, producer, result, false), // wrong factor, exact result
        publishVerdict(attempts[25], req[25], revised, producer, result, true),
        if (matches(attempts[26], req[26]) and attempts[26].removed > 0) "collected" else "wrong_collection",
        rejectedWriteVerdict(attempts[27], req[27], ""),
        scaleReadVerdict(revisedCall, attempts[28], req[28], revised, sumRead),
        sumReadVerdict(originalCall, attempts[29], req[29], producer),
        scaleReadVerdict(originalCall, attempts[30], req[30], result, sumRead)
      )
    }
  }

  pure def planReadVerdict(readback: Attempt, req: Request, plan: str, portable: str, factor: int,
                          sumRead: Attempt, implementation: str): str =
    if (not(matches(readback, req))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit != plan or readback.requestCommit != portable or readback.expectedMain != "-")
      "wrong_plan"
    else if (readback.producerCommit != sumRead.commit or readback.calls != sumRead.calls or
             readback.requestImplementation != implementation or readback.requestFactor != factor)
      "wrong_request"
    else "inspected"

  pure def versionedRequestedRead(s: Scenario, readback: Attempt, req: Request, result: str, portable: str,
                                  sumRead: Attempt, implementation: str): str =
    if (readback.requestCommit != portable) "wrong_request"
    else versionedScaleRead(s, readback, req, result, sumRead, implementation)

  pure def requestedReadVerdict(s: Scenario, readback: Attempt, req: Request, result: str, portable: str,
                               sumRead: Attempt): str =
    versionedRequestedRead(s, readback, req, result, portable, sumRead, scaleV1)

  pure def requestExportVerdict(attempt: Attempt, req: Request, plan: str): str =
    if (not(matches(attempt, req)) or attempt.expectedCommit != plan or attempt.commit == "" or attempt.commit == plan)
      "wrong_export"
    else exportedBundle(attempt)

  pure def durableVerdicts(attempts: List[Attempt]): List[str] = {
    val req = durableRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val plan = attempts[2].commit
      val otherPlan = attempts[3].commit
      val portable = attempts[5].commit
      val otherPortable = attempts[6].commit
      val result = attempts[11].commit
      val otherResult = attempts[9].commit
      val original: Scenario = { ...selected, b: ("-7", -7) }
      val revised = { ...original, factor: ("-2", -2) }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(original, sumRead, req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        scaleWriteVerdict(attempts[3], req[3], producer),
        planReadVerdict(attempts[4], req[4], plan, portable, 3, sumRead, scaleV1),
        requestExportVerdict(attempts[5], req[5], plan),
        requestExportVerdict(attempts[6], req[6], otherPlan),
        stageVerdict(attempts[7], req[7], otherPortable),
        rejectedWriteVerdict(attempts[8], req[8], portable),
        scaleWriteVerdict(attempts[9], req[9], otherPortable),
        stageVerdict(attempts[10], req[10], portable),
        scaleWriteVerdict(attempts[11], req[11], portable),
        requestedReadVerdict(original, attempts[12], req[12], result, portable, sumRead),
        requestedReadVerdict(revised, attempts[13], req[13], otherResult, otherPortable, sumRead),
        exportVerdict(attempts[14], req[14], result),
        exportVerdict(attempts[15], req[15], otherResult),
        stageVerdict(attempts[16], req[16], otherResult),
        publishVerdict(attempts[17], req[17], otherResult, plan, "", false), // wrong request
        stageVerdict(attempts[18], req[18], result),
        publishVerdict(attempts[19], req[19], result, plan, "", false), // stale plan pin
        publishVerdict(attempts[20], req[20], result, plan, "", false), // stale staging pin
        requestedReadVerdict(original, attempts[21], req[21], result, portable, sumRead),
        publishVerdict(attempts[22], req[22], result, plan, "", true),
        publishVerdict(attempts[23], req[23], otherResult, otherPlan, "", false), // stale main
        if (matches(attempts[24], req[24]) and attempts[24].removed > 0) "collected" else "wrong_collection",
        requestedReadVerdict(original, attempts[25], req[25], result, portable, sumRead),
        rejectedWriteVerdict(attempts[26], req[26], ""), // consumed plan
        rejectedWriteVerdict(attempts[27], req[27], ""), // consumed staging pin
        planReadVerdict(attempts[28], req[28], otherPlan, otherPortable, -2, sumRead, scaleV1),
        requestedReadVerdict(revised, attempts[29], req[29], otherResult, otherPortable, sumRead)
      )
    }
  }

  pure def retryVerdict(attempt: Attempt, req: Request, plan: str, result: str): str =
    if (attempt.expectedCommit != plan or attempt.expectedResult != result) "wrong_selection"
    else if (not(matches(attempt, req)) or attempt.commit != result) "wrong_acknowledgment"
    else if (not(attempt.unchanged)) "storage_changed"
    else "acknowledged"

  pure def receiptReadVerdict(readback: Attempt, req: Request, expected: Publication): str =
    if (not(matches(readback, req))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit == "" or readback.commit == expected.plan or readback.commit == expected.result or
      readback.publication != expected or readback.calls.length() != 0) "wrong_receipt"
    else "inspected"

  pure def abandonVerdict(write: Attempt, req: Request, plan: str): str =
    if (write.expectedCommit != plan) "wrong_selection"
    else if (not(matches(write, req)) or write.commit != plan or write.unchanged) "wrong_abandonment"
    else "abandoned"

  pure def absentRefVerdict(attempt: Attempt, verdict: str): str =
    if (verdict != "rejected") verdict
    else if (not(attempt.missingRef)) "wrong_absence"
    else verdict

  pure def retryHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = retryRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val plan = attempts[2].commit
      val portable = attempts[3].commit
      val result = attempts[5].commit
      val nextPlan = attempts[11].commit
      val nextRequest = attempts[12].commit
      val nextResult = attempts[14].commit
      val original: Scenario = { ...selected, b: ("-7", -7) }
      val revised = { ...original, factor: ("-2", -2) }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(original, sumRead, req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        requestExportVerdict(attempts[3], req[3], plan),
        stageVerdict(attempts[4], req[4], portable),
        scaleWriteVerdict(attempts[5], req[5], portable),
        exportVerdict(attempts[6], req[6], result),
        stageVerdict(attempts[7], req[7], result),
        publishVerdict(attempts[8], req[8], result, plan, "", true),
        retryVerdict(attempts[9], req[9], plan, result),
        publishVerdict(attempts[10], req[10], result, plan, "", false), // main alone is not evidence
        scaleWriteVerdict(attempts[11], req[11], producer),
        requestExportVerdict(attempts[12], req[12], nextPlan),
        stageVerdict(attempts[13], req[13], nextRequest),
        scaleWriteVerdict(attempts[14], req[14], nextRequest),
        exportVerdict(attempts[15], req[15], nextResult),
        stageVerdict(attempts[16], req[16], nextResult),
        publishVerdict(attempts[17], req[17], nextResult, nextPlan, "", false), // retained key belongs to first attempt
        publishVerdict(attempts[18], req[18], nextResult, nextPlan, "", true),
        if (matches(attempts[19], req[19]) and attempts[19].removed > 0) "collected" else "wrong_collection",
        receiptReadVerdict(attempts[20], req[20], { planRef: "plan", plan: plan, stagingRef: "returned", result: result }),
        absentRefVerdict(attempts[21], rejectedWriteVerdict(attempts[21], req[21], plan)), // Publication won.
        retryVerdict(attempts[22], req[22], plan, result),
        requestedReadVerdict(revised, attempts[23], req[23], nextResult, nextRequest, sumRead),
        rejectedWriteVerdict(attempts[24], req[24], ""),
        rejectedWriteVerdict(attempts[25], req[25], "")
      )
    }
  }

  pure def abandonHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = abandonRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val plan = attempts[2].commit
      val portable = attempts[3].commit
      val result = attempts[5].commit
      val replacement = attempts[13].commit
      val replacementRequest = attempts[15].commit
      val original: Scenario = { ...selected, b: ("-7", -7) }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(original, sumRead, req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        requestExportVerdict(attempts[3], req[3], plan),
        stageVerdict(attempts[4], req[4], portable),
        scaleWriteVerdict(attempts[5], req[5], portable),
        exportVerdict(attempts[6], req[6], result),
        abandonVerdict(attempts[7], req[7], plan),
        stageVerdict(attempts[8], req[8], result),
        absentRefVerdict(attempts[9], publishVerdict(attempts[9], req[9], result, plan, "", false)), // Late result.
        absentRefVerdict(attempts[10], rejectedWriteVerdict(attempts[10], req[10], "")), // No main.
        absentRefVerdict(attempts[11], rejectedWriteVerdict(attempts[11], req[11], "")), // No receipt.
        absentRefVerdict(attempts[12], rejectedWriteVerdict(attempts[12], req[12], "")), // No plan.
        scaleWriteVerdict(attempts[13], req[13], producer),
        rejectedWriteVerdict(attempts[14], req[14], plan), // Same name, original plan ID.
        requestExportVerdict(attempts[15], req[15], replacement),
        planReadVerdict(attempts[16], req[16], replacement, replacementRequest, -2, sumRead, scaleV1),
        abandonVerdict(attempts[17], req[17], replacement),
        absentRefVerdict(attempts[18], rejectedWriteVerdict(attempts[18], req[18], "")),
        requestedReadVerdict(original, attempts[19], req[19], result, portable, sumRead)
      )
    }
  }

  pure def reuseStageVerdict(attempt: Attempt, req: Request, plan: str, result: str, accepted: bool): str =
    if (attempt.expectedCommit != plan or attempt.expectedResult != result) "wrong_selection"
    else if (not(accepted)) rejectedWriteVerdict(attempt, req, plan)
    else if (not(matches(attempt, req)) or attempt.commit != result or attempt.unchanged) "wrong_reuse"
    else "reused"

  pure def reuseHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = reuseRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val plan = attempts[2].commit
      val portable = attempts[3].commit
      val result = attempts[5].commit
      val parallel = attempts[9].commit
      val wrongPlan = attempts[10].commit
      val nextPlan = attempts[25].commit
      val original: Scenario = { ...selected, b: ("-7", -7) }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(original, sumRead, req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        requestExportVerdict(attempts[3], req[3], plan),
        stageVerdict(attempts[4], req[4], portable),
        scaleWriteVerdict(attempts[5], req[5], portable),
        exportVerdict(attempts[6], req[6], result),
        stageVerdict(attempts[7], req[7], result),
        requestedReadVerdict(original, attempts[8], req[8], result, portable, sumRead),
        scaleWriteVerdict(attempts[9], req[9], producer),
        scaleWriteVerdict(attempts[10], req[10], producer),
        reuseStageVerdict(attempts[11], req[11], plan, result, false), // stale plan
        reuseStageVerdict(attempts[12], req[12], plan, result, false), // stale result
        reuseStageVerdict(attempts[13], req[13], wrongPlan, result, false), // wrong request
        reuseStageVerdict(attempts[14], req[14], plan, result, true),
        reuseStageVerdict(attempts[15], req[15], plan, result, false), // occupied by the exact result
        publishVerdict(attempts[16], req[16], result, plan, "", true),
        absentRefVerdict(attempts[17], rejectedWriteVerdict(attempts[17], req[17], "")),
        absentRefVerdict(attempts[18], rejectedWriteVerdict(attempts[18], req[18], "")),
        reuseStageVerdict(attempts[19], req[19], parallel, result, true), // staging ignores current main
        publishVerdict(attempts[20], req[20], result, parallel, "", false), // stale main
        abandonVerdict(attempts[21], req[21], parallel),
        absentRefVerdict(attempts[22], reuseStageVerdict(attempts[22], req[22], parallel, result, false)),
        absentRefVerdict(attempts[23], publishVerdict(attempts[23], req[23], result, parallel, "", false)),
        requestedReadVerdict(original, attempts[24], req[24], result, portable, sumRead),
        scaleWriteVerdict(attempts[25], req[25], producer),
        reuseStageVerdict(attempts[26], req[26], nextPlan, result, true),
        publishVerdict(attempts[27], req[27], result, nextPlan, "", true),
        requestedReadVerdict(original, attempts[28], req[28], result, portable, sumRead),
        requestedReadVerdict(original, attempts[29], req[29], result, portable, sumRead),
        receiptReadVerdict(attempts[30], req[30], { planRef: "plan", plan: plan, stagingRef: "returned", result: result })
      )
    }
  }

  pure def reuseRecordVerdict(readback: Attempt, req: Request, expected: ReusePublication,
                              portable: str, priorTip: str): str =
    if (not(matches(readback, req))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit == "" or readback.commit == expected.plan or readback.commit == expected.result or
      readback.reusePublication != expected or readback.requestCommit != portable or
      readback.expectedMain != priorTip or readback.calls.length() != 0) "wrong_reuse_record"
    else "inspected"

  pure def reusePublicationVerdicts(attempts: List[Attempt]): List[str] = {
    val req = reusePublicationRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val plan = attempts[2].commit
      val portable = attempts[3].commit
      val result = attempts[5].commit
      val parallel = attempts[9].commit
      val nextPlan = attempts[17].commit
      val original: Scenario = { ...selected, b: ("-7", -7) }
      val proof: ReusePublication = { mode: "reuse", planRef: "next-plan", plan: nextPlan,
                                      resultRef: "saved-result", result: result }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(original, sumRead, req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        requestExportVerdict(attempts[3], req[3], plan),
        stageVerdict(attempts[4], req[4], portable),
        scaleWriteVerdict(attempts[5], req[5], portable),
        exportVerdict(attempts[6], req[6], result),
        stageVerdict(attempts[7], req[7], result),
        stageVerdict(attempts[8], req[8], result),
        scaleWriteVerdict(attempts[9], req[9], producer),
        publishVerdict(attempts[10], req[10], result, plan, "", true),
        requestedReadVerdict(original, attempts[11], req[11], result, portable, sumRead),
        absentRefVerdict(attempts[12], rejectedWriteVerdict(attempts[12], req[12], "")),
        publishVerdict(attempts[13], req[13], result, parallel, "", false), // stale main
        absentRefVerdict(attempts[14], rejectedWriteVerdict(attempts[14], req[14], "")),
        abandonVerdict(attempts[15], req[15], parallel),
        absentRefVerdict(attempts[16], publishVerdict(attempts[16], req[16], result, parallel, "", false)),
        scaleWriteVerdict(attempts[17], req[17], producer),
        publishVerdict(attempts[18], req[18], result, nextPlan, "", true),
        reuseRecordVerdict(attempts[19], req[19], proof, portable, result),
        requestedReadVerdict(original, attempts[20], req[20], result, portable, sumRead),
        requestedReadVerdict(original, attempts[21], req[21], result, portable, sumRead),
        absentRefVerdict(attempts[22], rejectedWriteVerdict(attempts[22], req[22], "")),
        receiptReadVerdict(attempts[23], req[23],
          { planRef: "plan", plan: plan, stagingRef: "returned", result: result })
      )
    }
  }

  pure def versionHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = versionRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val firstPlan = attempts[2].commit
      val secondPlan = attempts[4].commit
      val firstRequest = attempts[6].commit
      val secondRequest = attempts[7].commit
      val firstResult = attempts[10].commit
      val secondResult = attempts[12].commit
      val nextPlan = attempts[24].commit
      val proof: ReusePublication = { mode: "reuse", planRef: "next", plan: nextPlan,
                                      resultRef: "saved", result: secondResult }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(selected, sumRead, req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        scaleWriteVerdict(attempts[3], req[3], producer),
        scaleWriteVerdict(attempts[4], req[4], producer),
        rejectedWriteVerdict(attempts[5], req[5], producer),
        requestExportVerdict(attempts[6], req[6], firstPlan),
        requestExportVerdict(attempts[7], req[7], secondPlan),
        planReadVerdict(attempts[8], req[8], secondPlan, secondRequest, 3, sumRead, scaleV2),
        stageVerdict(attempts[9], req[9], firstRequest),
        scaleWriteVerdict(attempts[10], req[10], firstRequest),
        stageVerdict(attempts[11], req[11], secondRequest),
        scaleWriteVerdict(attempts[12], req[12], secondRequest),
        requestedReadVerdict(selected, attempts[13], req[13], firstResult, firstRequest, sumRead),
        versionedRequestedRead(selected, attempts[14], req[14], secondResult, secondRequest, sumRead, scaleV2),
        exportVerdict(attempts[15], req[15], firstResult),
        exportVerdict(attempts[16], req[16], secondResult),
        stageVerdict(attempts[17], req[17], firstResult),
        stageVerdict(attempts[18], req[18], secondResult),
        publishVerdict(attempts[19], req[19], firstResult, secondPlan, "", false),
        reuseStageVerdict(attempts[20], req[20], secondPlan, firstResult, false),
        publishVerdict(attempts[21], req[21], firstResult, secondPlan, "", false),
        reuseStageVerdict(attempts[22], req[22], secondPlan, secondResult, true),
        publishVerdict(attempts[23], req[23], secondResult, secondPlan, "", true),
        scaleWriteVerdict(attempts[24], req[24], producer),
        publishVerdict(attempts[25], req[25], secondResult, nextPlan, "", true),
        versionedRequestedRead(selected, attempts[26], req[26], secondResult, secondRequest, sumRead, scaleV2),
        reuseRecordVerdict(attempts[27], req[27], proof, secondRequest, secondResult),
        versionedRequestedRead(selected, attempts[28], req[28], secondResult, secondRequest, sumRead, scaleV2)
      )
    }
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario == scenarios.length()) separateVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 1) handoffVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 2) returnVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 3) durableVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 4) retryHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 5) abandonHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 6) reuseHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 7) reusePublicationVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 8) versionHistoryVerdicts(row.attempts)
    else togetherVerdicts(row)

  pure def verdictAccepted(verdict: str): bool =
    Set("recorded", "inspected", "rejected", "exported", "staged", "released", "collected", "published",
      "acknowledged", "abandoned", "reused").contains(verdict)

  pure def sameRootNotSameCall(first: Call, second: Call): bool =
    first.resultNode == second.resultNode and first.dag != second.dag

  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool = {
    val together = List("recorded", "inspected")
    val separate = List("recorded", "recorded", "inspected", "inspected", "rejected", "rejected", "rejected",
      "recorded", "rejected", "recorded", "inspected", "inspected")
    val handoff = List("recorded", "recorded", "inspected", "inspected", "rejected", "exported", "exported",
      "rejected", "staged", "rejected", "rejected", "inspected", "staged", "rejected", "inspected", "recorded",
      "inspected", "rejected", "rejected", "released", "collected", "rejected", "inspected", "rejected", "inspected")
    val roundTrip = List("recorded", "recorded", "inspected", "exported", "staged", "recorded", "recorded", "released",
      "collected", "inspected", "rejected", "exported", "exported", "staged", "inspected", "rejected", "rejected",
      "published", "rejected", "inspected", "staged", "rejected", "rejected", "rejected", "rejected", "published",
      "collected", "rejected", "inspected", "inspected", "inspected")
    val durable = List("recorded", "inspected", "recorded", "recorded", "inspected", "exported", "exported",
      "staged", "rejected", "recorded", "staged", "recorded", "inspected", "inspected", "exported", "exported",
      "staged", "rejected", "staged", "rejected", "rejected", "inspected", "published", "rejected", "collected",
      "inspected", "rejected", "rejected", "inspected", "inspected")
    val retry = List("recorded", "inspected", "recorded", "exported", "staged", "recorded", "exported",
      "staged", "published", "acknowledged", "rejected", "recorded", "exported", "staged", "recorded", "exported",
      "staged", "rejected", "published", "collected", "inspected", "rejected", "acknowledged", "inspected",
      "rejected", "rejected")
    val abandon = List("recorded", "inspected", "recorded", "exported", "staged", "recorded", "exported",
      "abandoned", "staged", "rejected", "rejected", "rejected", "rejected", "recorded", "rejected", "exported",
      "inspected", "abandoned", "rejected", "inspected")
    val reuse = List("recorded", "inspected", "recorded", "exported", "staged", "recorded", "exported",
      "staged", "inspected", "recorded", "recorded", "rejected", "rejected", "rejected", "reused", "rejected",
      "published", "rejected", "rejected", "reused", "rejected", "abandoned", "rejected", "rejected", "inspected",
      "recorded", "reused", "published", "inspected", "inspected", "inspected")
    val reusePublication = List("recorded", "inspected", "recorded", "exported", "staged", "recorded", "exported",
      "staged", "staged", "recorded", "published", "inspected", "rejected", "rejected", "rejected", "abandoned",
      "rejected", "recorded", "published", "inspected", "inspected", "inspected", "rejected", "inspected")
    val versioned = List("recorded", "inspected", "recorded", "recorded", "recorded", "rejected", "exported",
      "exported", "inspected", "staged", "recorded", "staged", "recorded", "inspected", "inspected",
      "exported", "exported", "staged", "staged", "rejected", "rejected", "rejected", "reused", "published",
      "recorded", "published", "inspected", "inspected", "inspected")
    val expected = List(together, together, separate, handoff, roundTrip, durable, retry, abandon,
      reuse, reusePublication, versioned)
    if (rows.length() != expected.length() or verdicts != expected) false
    else {
      val split = rows[2].attempts
      val transfer = rows[3].attempts
      val returned = rows[4].attempts
      val planned = rows[5].attempts
      val retried = rows[6].attempts
      val abandoned = rows[7].attempts
      val reused = rows[8].attempts
      val reusePublished = rows[9].attempts
      val versions = rows[10].attempts
      rows.indices().forall(i => rows[i].scenario == i) and
        sameRootNotSameCall(rows[0].attempts[1].calls[0], rows[1].attempts[1].calls[0]) and
        sameRootNotSameCall(split[2].calls[0], split[3].calls[0]) and split[0].commit != split[1].commit and
        split[7].commit != split[9].commit and transfer[0].commit != transfer[1].commit and
        sameRootNotSameCall(transfer[14].calls[0], transfer[11].calls[0]) and
        transfer[14].calls == transfer[2].calls and transfer[11].calls == transfer[3].calls and
        transfer[16].calls == transfer[22].calls and returned[0].commit != returned[1].commit and
        returned[5].commit != returned[6].commit and returned[9].calls == returned[14].calls and
        returned[9].calls == returned[19].calls and returned[9].calls == returned[30].calls and
        sameRootNotSameCall(returned[19].calls[1], returned[28].calls[1]) and
        planned[2].commit != planned[3].commit and planned[5].commit != planned[6].commit and
        planned[9].commit != planned[11].commit and sameRootNotSameCall(planned[12].calls[1], planned[13].calls[1]) and
        planned[12].calls == planned[21].calls and planned[12].calls == planned[25].calls and
        retried[2].commit != retried[11].commit and retried[5].commit != retried[14].commit and
        abandoned[2].commit != abandoned[13].commit and abandoned[3].commit != abandoned[15].commit and
        reused[2].commit == reused[9].commit and reused[2].commit != reused[10].commit and
        reused[2].commit != reused[25].commit and reused[8].calls == reused[24].calls and
        reused[8].calls == reused[28].calls and reused[8].calls == reused[29].calls and
        reusePublished[2].commit == reusePublished[9].commit and
        reusePublished[2].commit != reusePublished[17].commit and
        reusePublished[11].calls == reusePublished[20].calls and
        reusePublished[20].calls == reusePublished[21].calls and
        versions[2].commit == versions[3].commit and versions[2].commit != versions[4].commit and
        versions[4].commit != versions[24].commit and versions[6].commit != versions[7].commit and
        versions[10].commit != versions[12].commit and
        sameRootNotSameCall(versions[13].calls[1], versions[14].calls[1]) and
        versions[13].calls[1].arguments == versions[14].calls[1].arguments and
        versions[14].calls == versions[26].calls and versions[26].calls == versions[28].calls
    }
  }

  pure val a: Argument = { name: "a", node: "a-node", value: 7, producer: "" }
  pure val b: Argument = { name: "b", node: "b-node", value: 5, producer: "" }
  pure val factor: Argument = { name: "factor", node: "factor-node", value: 3, producer: "" }
  pure val input: Argument = { name: "input", node: "source-node", value: 12, producer: "sum-call" }
  pure val summed: Call = { dag: "sum-call", implementation: "example.sum@1", resultNode: "literal-12",
    resultValue: 12, arguments: List(a, b) }
  pure val scaled: Call = { dag: "scale-call", implementation: "example.scale@1", resultNode: "literal-36",
    resultValue: 36, arguments: List(factor, input) }
  pure val recorded: Attempt = { op: "record", args: List("source", "7", "5", "3"), code: 0,
    quiet: true, diagnosed: false, missingRef: false, commit: "commit", calls: List(),
    expectedCommit: "", producerCommit: "", unchanged: false,
    removed: -1, expectedResult: "", expectedMain: "", requestCommit: "", requestImplementation: "",
    requestFactor: 0, bundlePresent: false, bundleUnchanged: true,
    publication: { planRef: "", plan: "", stagingRef: "", result: "" },
    reusePublication: { mode: "", planRef: "", plan: "", resultRef: "", result: "" } }
  pure val inspected: Attempt = { ...recorded, op: "inspect", args: List("source"), calls: List(summed, scaled),
    unchanged: true }
  pure def inspectVerdict(readback: Attempt): str =
    historyVerdicts({ scenario: 0, attempts: List(recorded, readback) })[1]
  pure val sumRead: Attempt = { ...inspected, calls: List(summed) }
  pure val scaleRead: Attempt = { ...inspected, args: List("source", "result"), commit: "scaled", producerCommit: "commit" }
  pure val substituted: Attempt = { ...scaleRead, calls: List(
    { ...summed, dag: "equal-valued-decoy" },
    { ...scaled, arguments: List(factor, { ...input, producer: "equal-valued-decoy" }) }) }
  pure val scaleWrite: Attempt = { ...recorded, op: "record_scale", args: splitRequests[7].args,
    commit: "scaled", expectedCommit: "commit" }
  pure val staleWrite: Attempt = { ...scaleWrite, args: splitRequests[4].args,
    code: 1, quiet: false, diagnosed: true, commit: "", unchanged: true }
  pure val staged: Attempt = { ...recorded, op: "stage_input", args: handoffRequests[12].args,
    bundlePresent: true }
  pure val rejectedExportControl: Attempt = { ...recorded, op: "export_sum", args: handoffRequests[4].args,
    code: 1, quiet: false, diagnosed: true, commit: "", expectedCommit: "commit", unchanged: true }
  pure val released: Attempt = { ...recorded, op: "release_input", args: handoffRequests[19].args,
    expectedCommit: "commit" }
  pure val published: Attempt = { ...recorded, op: "publish_scale", args: returnRequests[17].args,
    commit: "result", expectedResult: "result", expectedCommit: "producer", expectedMain: "-" }
  pure val rejectedPublication: Attempt = { ...published, args: returnRequests[21].args, commit: "", expectedMain: "tip",
    code: 1, quiet: false, diagnosed: true, unchanged: true }
  pure val acknowledged: Attempt = { ...published, op: "publish_requested_scale", args: retryRequests[9].args,
    expectedCommit: "plan", unchanged: true }
  pure val publication: Publication = { planRef: "plan", plan: "plan", stagingRef: "returned", result: "result" }
  pure val receiptRead: Attempt = { ...recorded, op: "inspect", args: retryRequests[20].args,
    commit: "receipt", unchanged: true, publication: publication }
  pure val abandoned: Attempt = { ...recorded, op: "abandon_scale_request", args: abandonRequests[7].args,
    commit: "plan", expectedCommit: "plan" }
  pure val reused: Attempt = { ...recorded, op: "stage_reused_scale", args: reuseRequests[14].args,
    expectedCommit: "plan", expectedResult: "result", commit: "result" }
  pure val reuseProof: ReusePublication = { mode: "reuse", planRef: "next-plan", plan: "next-plan-id",
    resultRef: "saved-result", result: "result" }
  pure val reuseRead: Attempt = { ...recorded, op: "inspect", args: reusePublicationRequests[19].args,
    commit: "reuse-record", unchanged: true, requestCommit: "request", expectedMain: "prior",
    reusePublication: reuseProof }
  pure def checkReuseProof(readback: Attempt): str =
    reuseRecordVerdict(readback, reusePublicationRequests[19], reuseProof, "request", "prior")
  pure val controlsPass = all {
    checkReuseProof(reuseRead) == "inspected",
    checkReuseProof({ ...reuseRead, reusePublication: { ...reuseProof, mode: "" } }) == "wrong_reuse_record",
    checkReuseProof({ ...reuseRead, reusePublication: { ...reuseProof, result: "other" } }) == "wrong_reuse_record",
    checkReuseProof({ ...reuseRead, reusePublication: { ...reuseProof, plan: "other" } }) == "wrong_reuse_record",
    checkReuseProof({ ...reuseRead, requestCommit: "other" }) == "wrong_reuse_record",
    checkReuseProof({ ...reuseRead, expectedMain: "other" }) == "wrong_reuse_record",
    reuseStageVerdict(reused, reuseRequests[14], "plan", "result", true) == "reused",
    reuseStageVerdict({ ...reused, expectedResult: "other" }, reuseRequests[14], "plan", "result", true)
      == "wrong_selection",
    reuseStageVerdict({ ...reused, commit: "other" }, reuseRequests[14], "plan", "result", true) == "wrong_reuse",
    reuseStageVerdict({ ...reused, unchanged: true }, reuseRequests[14], "plan", "result", true) == "wrong_reuse",
    reuseStageVerdict(reused, reuseRequests[14], "plan", "result", false) == "wrong_rejection",
    abandonVerdict(abandoned, abandonRequests[7], "plan") == "abandoned",
    abandonVerdict({ ...abandoned, unchanged: true }, abandonRequests[7], "plan") == "wrong_abandonment",
    abandonVerdict({ ...abandoned, commit: "replacement" }, abandonRequests[7], "plan") == "wrong_abandonment",
    abandonVerdict({ ...abandoned, expectedCommit: "replacement" }, abandonRequests[7], "plan") == "wrong_selection",
    absentRefVerdict({ ...recorded, missingRef: true }, "rejected") == "rejected",
    absentRefVerdict(recorded, "rejected") == "wrong_absence",
    receiptReadVerdict(receiptRead, retryRequests[20], publication) == "inspected",
    receiptReadVerdict({ ...receiptRead, calls: List(summed) }, retryRequests[20], publication) == "wrong_receipt",
    receiptReadVerdict({ ...receiptRead, publication: { ...publication, planRef: "other" } },
      retryRequests[20], publication) == "wrong_receipt",
    retryVerdict(acknowledged, retryRequests[9], "plan", "result") == "acknowledged",
    retryVerdict({ ...acknowledged, unchanged: false }, retryRequests[9], "plan", "result") == "storage_changed",
    retryVerdict({ ...acknowledged, commit: "next-result" },
      retryRequests[9], "plan", "result") == "wrong_acknowledgment",
    publishVerdict(published, returnRequests[17], "result", "producer", "-", true) == "published",
    publishVerdict({ ...published, commit: "decoy" }, returnRequests[17], "result", "producer", "-", true)
      == "wrong_publication",
    publishVerdict({ ...published, expectedMain: "tip" }, returnRequests[17], "result", "producer", "-", true)
      == "wrong_selection",
    publishVerdict(rejectedPublication, returnRequests[21], "result", "producer", "tip", false) == "rejected",
    publishVerdict({ ...rejectedPublication, unchanged: false }, returnRequests[21], "result", "producer", "tip", false)
      == "storage_changed",
    stageVerdict(staged, handoffRequests[12], "commit") == "staged",
    stageVerdict({ ...staged, commit: "decoy" }, handoffRequests[12], "commit") == "wrong_stage",
    stageVerdict({ ...staged, bundleUnchanged: false }, handoffRequests[12], "commit") == "wrong_bundle",
    rejectedExport(rejectedExportControl, handoffRequests[4], "commit", false) == "rejected",
    rejectedExport({ ...rejectedExportControl, bundlePresent: true }, handoffRequests[4], "commit", false) == "wrong_bundle",
    releaseVerdict(released, handoffRequests[19], "commit") == "released",
    releaseVerdict({ ...released, commit: "decoy" }, handoffRequests[19], "commit") == "wrong_release",
    scaleWriteVerdict(scaleWrite, splitRequests[7], "commit") == "recorded",
    scaleWriteVerdict({ ...scaleWrite, expectedCommit: "decoy" }, splitRequests[7], "commit") == "wrong_selection",
    rejectedWriteVerdict(staleWrite, splitRequests[4], "commit") == "rejected",
    rejectedWriteVerdict({ ...staleWrite, expectedCommit: "decoy" }, splitRequests[4], "commit") == "wrong_selection",
    rejectedWriteVerdict({ ...staleWrite, unchanged: false }, splitRequests[4], "commit") == "storage_changed",
    rejectedWriteVerdict({ ...staleWrite, diagnosed: false }, splitRequests[4], "commit") == "wrong_rejection",
    scaleReadVerdict(selected, scaleRead, splitRequests[10], "scaled", sumRead) == "inspected",
    scaleReadVerdict(selected, { ...scaleRead, producerCommit: "decoy" }, splitRequests[10], "scaled", sumRead)
      == "wrong_commit",
    scaleReadVerdict(selected, substituted, splitRequests[10], "scaled", sumRead) == "wrong_producer",
    inspectVerdict(inspected) == "inspected",
    inspectVerdict({ ...inspected, unchanged: false }) == "storage_changed",
    inspectVerdict({ ...inspected, commit: "different-commit" }) == "wrong_commit",
    checkCalls(scenarios[0], List(summed, scaled), scaleV1),
    not(checkCalls(scenarios[0], List(summed, scaled), scaleV2)),
    checkCalls(scenarios[0], List(summed, { ...scaled, implementation: scaleV2 }), scaleV2),
    not(checkCalls(scenarios[0], List(summed, { ...scaled, resultValue: 37 }), scaleV1)),
    not(checkCalls(scenarios[0], List(summed, { ...scaled, implementation: scaleV2 }), scaleV1)),
    not(checkCalls(scenarios[0], List(summed, { ...scaled, arguments: List(factor, { ...input,
      producer: "different-call-with-same-value" }) }), scaleV1))
  }
}
