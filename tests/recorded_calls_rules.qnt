module recorded_calls_rules {
  import recorded_calls_histories.* from "./recorded_calls_histories"
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_stored_histories.* from "./recorded_calls_stored_histories"
  import recorded_calls_outbound_histories.* from "./recorded_calls_outbound_histories"

  type Argument = { name: str, node: str, value: int, producer: str }
  type Call = { dag: str, implementation: str, resultNode: str, resultValue: int, arguments: List[Argument] }
  type Publication = { planRef: str, plan: str, stagingRef: str, result: str }
  type ReusePublication = { mode: str, planRef: str, plan: str, resultRef: str, result: str }
  type Selection = { resultRef: str, result: str }
  type SelectedPublication = { mode: str, planRef: str, plan: str, selectionRef: str, selection: str, result: str }
  type Occurrence = { id: str, commit: str, result: str, historicalRef: str }
  type Policy = { defaultMode: str, previous: str }
  type Intent = { implementation: str, defaultMode: str, v1Selection: str, v2Selection: str, previous: str }
  type Declaration = { commit: str, basis: str, evidence: str, predecessor: str, successor: str, reason: str }
  type Advisory = { intent: str, relation: str, declaration: Declaration }
  type Decision = { id: str, canonicalId: bool, policy: str, intent: str, defaultMode: str, override: str, route: str,
    reason: str, plan: str, planRef: str, selectionRef: str, selection: str, result: str,
    implementationOverride: str, implementationReason: str }
  type ReuseTableEntry = { request: str, selection: str, result: str, attempt: str, attemptId: str }
  type ReuseTable = { intent: str, implementation: str, previous: str, entries: List[ReuseTableEntry] }
  type IntentReuseEntry = { producer: str, factor: int, request: str, implementation: str,
    selection: str, result: str, attempt: str, attemptId: str }
  type IntentReuseTable = { intent: str, genesis: str, previous: str, entries: List[IntentReuseEntry] }
  type Attempt = { op: str, args: List[str], code: int, quiet: bool, diagnosed: bool, missingRef: bool,
    stderr: str, stdoutEmpty: bool, repoExisted: bool, repoExists: bool, errorType: str, pathUses: int,
    nativeStatus: str, nativeDetail: str, nativeValue: str, nativeCount: int, nativeItems: List[str],
    commit: str, calls: List[Call], reportFields: List[List[str]], stdoutHash: str, historicalReportHash: str,
    expectedCommit: str, producerCommit: str, unchanged: bool, removed: int,
    expectedResult: str, expectedSelection: str, expectedAttempt: str, expectedMain: str, previousSelection: str,
    requestCommit: str,
    requestImplementation: str, requestFactor: int, bundlePresent: bool, bundleUnchanged: bool, bundleSize: int,
    publication: Publication,
    reusePublication: ReusePublication, selection: Selection, selectedPublication: SelectedPublication,
    occurrence: Occurrence, policy: Policy, expectedPolicy: str, intent: Intent, expectedIntent: str, decision: Decision,
    expectedEvidence: str, definitionAdvisory: bool, supersession: Declaration, asKnownThen: Advisory, knowledgeView: Advisory,
    expectedTable: str, tableRef: str, tableCommit: str, reuseTable: ReuseTable,
    reuseScope: str, producingRequest: str, producingImplementation: str, intentReuseTable: IntentReuseTable }
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
    else if (write.code != 1 or not(write.diagnosed) or not(write.stdoutEmpty) or write.commit != "") "wrong_rejection"
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

  pure def rejectionNativeVerdict(a: Attempt, req: Request, status: str): str =
    if (not(sameRequest(a, req))) "wrong_native_request"
    else if (a.nativeStatus != status) "wrong_native_status"
    else if (status == "not_found") "native_not_found"
    else "native_ok"

  pure val absentRefDetail = "ref was not found"
  pure val absentDatumDetail = "immutable object was not found"

  pure def rejectionNativeReadVerdict(a: Attempt, req: Request, expected: str): str = {
    val status = if (expected == "") "not_found" else "ok"
    val verdict = rejectionNativeVerdict(a, req, status)
    val absentDetail = if (req.op == "txn_ref_get") absentRefDetail else absentDatumDetail
    if (Set("native_ok", "native_not_found").contains(verdict) and a.nativeValue != expected) "wrong_native_value"
    else if (verdict == "native_not_found" and a.nativeDetail != absentDetail) "wrong_native_detail"
    else verdict
  }

  pure def rejectionReadVerdicts(attempts: List[Attempt], req: List[Request], values: List[str]): List[str] =
    if (req.length() != values.length() + 4) List("wrong_read_frame")
    else range(0, req.length()).foldl(List(), (out, i) => out.append(
      if (i < 2 or i >= req.length() - 2) rejectionNativeVerdict(attempts[i], req[i], "ok")
      else rejectionNativeReadVerdict(attempts[i], req[i], values[i - 2])))

  pure def rejectionProbeVerdicts(attempts: List[Attempt], req: List[Request]): List[str] =
    range(0, req.length()).foldl(List(), (out, i) => {
      val verdict = rejectionNativeVerdict(attempts[i], req[i], "ok")
      out.append(if (verdict == "native_ok" and Set("datum_encode", "txn_put_datum").contains(req[i].op) and
          attempts[i].nativeValue == "") "missing_candidate"
        else verdict)
    })

  pure def cliRejectionVerdict(a: Attempt, req: Request, commit: str, cause: bool): str =
    if (not(sameRequest(a, req)) or a.expectedCommit != commit) "wrong_selection"
    else if (a.code != 1 or not(a.stdoutEmpty) or not(a.diagnosed) or a.stderr == "" or a.commit != "") "wrong_rejection"
    else if (not(cause)) "wrong_diagnostic"
    else "rejected"

  pure def existingRejectionVerdict(a: Attempt, req: Request, commit: str, cause: bool): str = {
    val verdict = cliRejectionVerdict(a, req, commit, cause)
    if (verdict != "rejected") verdict
    else if (not(a.repoExisted and a.repoExists and a.unchanged)) "storage_changed"
    else verdict
  }

  pure def freshRejectionVerdict(a: Attempt, req: Request, diagnostic: str, initializes: bool): str = {
    val verdict = cliRejectionVerdict(a, req, "", a.stderr == diagnostic)
    if (verdict != "rejected") verdict
    else if (a.repoExisted or a.repoExists != initializes) "wrong_repository_presence"
    else verdict
  }

  pure def pinRejectionVerdicts(attempts: List[Attempt]): List[str] = {
    val req = pinRejectionRequests
    val first = attempts[0].commit
    val decoy = attempts[1].commit
    val pinEnd = 2 + rejectionPins.length()
    val pins = List(first, decoy, "", "")
    List(writeVerdict(attempts[0], req[0]),
      if (first == decoy) "collapsed_producers" else writeVerdict(attempts[1], req[1]))
      .concat(rejectionReadVerdicts(attempts.slice(2, pinEnd), rejectionPins, pins))
      .concat(List(
        existingRejectionVerdict(attempts[pinEnd], req[pinEnd], first,
          attempts[pinEnd].stderr == "record-scale: producer pin does not point to the expected commit"),
        existingRejectionVerdict(attempts[pinEnd + 1], req[pinEnd + 1], first, attempts[pinEnd + 1].missingRef)
      )).concat(rejectionReadVerdicts(attempts.slice(pinEnd + 2, attempts.length()), rejectionPins, pins))
  }

  // -30799 is LMDB's MDB_KEYEXIST.
  pure val refExistsDiagnostic = "record-scale: ('invalid_state', -30799, 'ref already exists')"
  pure val writeRejectionDiagnostics = List(
    "record-sum: ('invalid_state', -30799, 'ref already exists')",
    refExistsDiagnostic, refExistsDiagnostic,
    "record-scale: example.scale@1 result is not a signed 64-bit integer"
  )

  pure def writeRejectionVerdicts(attempts: List[Attempt]): List[str] = {
    val req = writeRejectionRequests
    val producer = attempts[0].commit
    val main = attempts[1].commit
    val probeSize = rejectionProbe("0").length()
    val span = probeSize + 1 + writeRejectionReads.length()
    range(0, writeRejectionCases.length()).foldl(List(
      writeVerdict(attempts[0], req[0]), scaleWriteVerdict(attempts[1], req[1], producer)
    ), (out, i) => {
      val start = 2 + i * span
      val write = start + probeSize
      val expected = if (req[write].op == "record_sum") "" else producer
      out.concat(rejectionProbeVerdicts(attempts.slice(start, write), req.slice(start, write)))
        .append(existingRejectionVerdict(attempts[write], req[write], expected,
          attempts[write].stderr == writeRejectionDiagnostics[i]))
        .concat(rejectionReadVerdicts(attempts.slice(write + 1, start + span), writeRejectionReads,
          List(producer, main, "", "")))
    })
  }

  pure def overflowRejectionVerdicts(attempts: List[Attempt], req: List[Request], diagnostic: str): List[str] = {
    val readStart = 1 + rejectionProbe("0").length()
    List(freshRejectionVerdict(attempts[0], req[0], diagnostic, true))
      .concat(rejectionProbeVerdicts(attempts.slice(1, readStart), req.slice(1, readStart)))
      .concat(rejectionReadVerdicts(attempts.slice(readStart, attempts.length()), overflowReads, List("", "")))
  }

  pure def repeatRejectionVerdicts(attempts: List[Attempt]): List[str] = {
    val req = repeatRejectionRequests
    val commit = attempts[0].commit
    val repeat = 1 + mainReads.length()
    List(writeVerdict(attempts[0], req[0]))
      .concat(rejectionReadVerdicts(attempts.slice(1, repeat), mainReads, List(commit)))
      // mkdir's diagnostic includes an OS-specific error and a temporary path.
      .append(existingRejectionVerdict(attempts[repeat], req[repeat], "", true))
      .concat(rejectionReadVerdicts(attempts.slice(repeat + 1, attempts.length()), mainReads, List(commit)))
  }

  pure val rangeDiagnostic = "record: a is not a signed 64-bit integer"
  pure val sumOverflowDiagnostic = "record: example.sum@1 result is not a signed 64-bit integer"
  pure val scaleOverflowDiagnostic = "record: example.scale@1 result is not a signed 64-bit integer"

  pure def rejectionVerdicts(index: int, attempts: List[Attempt]): List[str] =
    if (not(rejectionRequests.indices().contains(index))) List("missing_history")
    else {
      val req = rejectionRequests[index]
      if (attempts.length() != req.length()) List("missing_steps")
      else if (index == 0) pinRejectionVerdicts(attempts)
      else if (index == 1) writeRejectionVerdicts(attempts)
      else if (index == 2) List(freshRejectionVerdict(attempts[0], req[0], rangeDiagnostic, false))
      else if (index == 3) overflowRejectionVerdicts(attempts, req, sumOverflowDiagnostic)
      else if (index == 4) overflowRejectionVerdicts(attempts, req, scaleOverflowDiagnostic)
      else repeatRejectionVerdicts(attempts)
    }

  pure val rejectionProbeExpected = List("native_ok", "native_ok", "native_ok", "native_ok", "native_ok", "native_ok")
  pure val rejectionPinExpected = List("native_ok", "native_ok", "native_ok", "native_ok", "native_not_found",
    "native_not_found", "native_ok", "native_ok")
  pure val rejectionWriteExpected = rejectionProbeExpected.concat(List("rejected", "native_ok", "native_ok", "native_ok",
    "native_ok", "native_not_found", "native_not_found", "native_ok", "native_ok"))
  pure val rejectionOverflowExpected = List("rejected").concat(rejectionProbeExpected).concat(List("native_ok", "native_ok",
    "native_not_found", "native_not_found", "native_ok", "native_ok"))
  pure val rejectionMainExpected = List("native_ok", "native_ok", "native_ok", "native_ok", "native_ok")
  pure val rejectionExpected: List[List[str]] = List(
    List("recorded", "recorded").concat(rejectionPinExpected).concat(List("rejected", "rejected")).concat(rejectionPinExpected),
    List("recorded", "recorded").concat(rejectionWriteExpected).concat(rejectionWriteExpected)
      .concat(rejectionWriteExpected).concat(rejectionWriteExpected),
    List("rejected"), rejectionOverflowExpected, rejectionOverflowExpected,
    List("recorded").concat(rejectionMainExpected).append("rejected").concat(rejectionMainExpected)
  )

  pure def rejectionControls(template: Attempt): bool = {
    val req = rangeRejectionRequests[0]
    val invalid = { ...template, op: req.op, args: req.args, commit: "", expectedCommit: "", code: 1,
      repoExisted: false, repoExists: false, stdoutEmpty: true, diagnosed: true, stderr: rangeDiagnostic }
    val absent = { ...template, op: rejectionDatum.op, args: rejectionDatum.args,
      nativeStatus: "not_found", nativeValue: "", nativeDetail: absentDatumDetail }
    val mainRef = rejectionRef("main")
    val missingRef = { ...absent, op: mainRef.op, args: mainRef.args, nativeDetail: absentRefDetail }
    val wrongRef = { ...missingRef, nativeStatus: "ok", nativeValue: "other", nativeDetail: "" }
    all {
      freshRejectionVerdict(invalid, req, rangeDiagnostic, false) == "rejected",
      freshRejectionVerdict({ ...invalid, repoExists: true }, req, rangeDiagnostic, false) == "wrong_repository_presence",
      freshRejectionVerdict({ ...invalid, stdoutEmpty: false }, req, rangeDiagnostic, false) == "wrong_rejection",
      freshRejectionVerdict({ ...invalid, stderr: scaleOverflowDiagnostic, repoExists: true }, req, sumOverflowDiagnostic, true)
        == "wrong_diagnostic",
      rejectionNativeReadVerdict(absent, rejectionDatum, "") == "native_not_found",
      rejectionNativeReadVerdict({ ...absent, nativeStatus: "ok", nativeValue: "candidate-id" }, rejectionDatum, "")
        == "wrong_native_status",
      rejectionNativeReadVerdict(missingRef, mainRef, "") == "native_not_found",
      rejectionNativeReadVerdict({ ...missingRef, nativeDetail: absentDatumDetail }, mainRef, "") == "wrong_native_detail",
      rejectionNativeReadVerdict(wrongRef, mainRef, "original") == "wrong_native_value"
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
    planReadWithTip(readback, req, plan, portable, factor, sumRead, implementation, "-")

  pure def planReadWithTip(readback: Attempt, req: Request, plan: str, portable: str, factor: int,
                          sumRead: Attempt, implementation: str, priorTip: str): str =
    if (not(matches(readback, req))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit != plan or readback.requestCommit != portable or readback.expectedMain != priorTip)
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

  pure def versionSetupVerdicts(attempts: List[Attempt]): List[str] = {
    val req = versionRequests
    val producer = attempts[0].commit
    val sumRead = attempts[1]
    val firstPlan = attempts[2].commit
    val secondPlan = attempts[4].commit
    val firstRequest = attempts[6].commit
    val secondRequest = attempts[7].commit
    val firstResult = attempts[10].commit
    val secondResult = attempts[12].commit
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
      stageVerdict(attempts[18], req[18], secondResult)
    )
  }

  pure def versionHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = versionRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val secondPlan = attempts[4].commit
      val secondRequest = attempts[7].commit
      val firstResult = attempts[10].commit
      val secondResult = attempts[12].commit
      val nextPlan = attempts[24].commit
      val proof: ReusePublication = { mode: "reuse", planRef: "next", plan: nextPlan,
                                      resultRef: "saved", result: secondResult }
      versionSetupVerdicts(attempts).concat(List(
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
      ))
    }
  }

  pure def selectVerdict(attempt: Attempt, req: Request, plan: str, result: str, accepted: bool): str =
    if (attempt.expectedCommit != plan or attempt.expectedResult != result) "wrong_selection"
    else if (not(accepted)) rejectedWriteVerdict(attempt, req, plan)
    else if (not(matches(attempt, req)) or attempt.commit == "" or attempt.commit == plan or
      attempt.commit == result or attempt.unchanged) "wrong_selection_record"
    else "selected"

  pure def selectionReadVerdict(readback: Attempt, req: Request, receipt: str, expected: Selection,
                                portable: str, implementation: str): str =
    if (not(matches(readback, req))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit != receipt or readback.selection != expected or readback.requestCommit != portable or
      readback.requestImplementation != implementation or readback.expectedMain != "" or readback.calls.length() != 0)
      "wrong_selection_record"
    else "inspected"

  pure def publishSelectedVerdict(attempt: Attempt, req: Request, plan: str, selection: str, result: str,
                                  accepted: bool): str =
    if (attempt.expectedCommit != plan or attempt.expectedSelection != selection) "wrong_selection"
    else if (not(accepted)) rejectedWriteVerdict(attempt, req, plan)
    else if (not(matches(attempt, req)) or attempt.commit != result or attempt.unchanged) "wrong_publication"
    else "published"

  pure def selectedProofVerdict(readback: Attempt, req: Request, expected: SelectedPublication,
                                portable: str, priorTip: str): str =
    if (not(matches(readback, req))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit == "" or Set(expected.plan, expected.selection, expected.result).contains(readback.commit) or
      readback.selectedPublication != expected or readback.requestCommit != portable or readback.expectedMain != priorTip or
      readback.calls.length() != 0) "wrong_reuse_record"
    else "inspected"

  pure def selectionHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = selectionRequests
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
      val secondChoice = attempts[21].commit
      val firstChoice = attempts[27].commit
      val staleMainChoice = attempts[31].commit
      val bridgePlan = attempts[35].commit
      val currentPlan = attempts[38].commit
      val resetPlan = attempts[41].commit
      val freshPlan = attempts[46].commit
      val saved: Selection = { resultRef: "saved", result: secondResult }
      val proof: SelectedPublication = { mode: "reuse", planRef: "fresh-v2", plan: freshPlan,
        selectionRef: "chosen-v2", selection: secondChoice, result: secondResult }
      versionSetupVerdicts(attempts).concat(List(
        selectVerdict(attempts[19], req[19], secondPlan, firstResult, false), // wrong version
        selectVerdict(attempts[20], req[20], secondPlan, firstResult, false), // stale result ID
        selectVerdict(attempts[21], req[21], secondPlan, secondResult, true),
        selectVerdict(attempts[22], req[22], secondPlan, secondResult, false), // exact selection already stored
        selectionReadVerdict(attempts[23], req[23], secondChoice, saved, secondRequest, scaleV2),
        absentRefVerdict(attempts[24], rejectedWriteVerdict(attempts[24], req[24], "")), // no main
        planReadVerdict(attempts[25], req[25], secondPlan, secondRequest, 3, sumRead, scaleV2),
        versionedRequestedRead(selected, attempts[26], req[26], secondResult, secondRequest, sumRead, scaleV2),
        selectVerdict(attempts[27], req[27], firstPlan, firstResult, true),
        publishSelectedVerdict(attempts[28], req[28], secondPlan, firstChoice, firstResult, false), // wrong version
        publishVerdict(attempts[29], req[29], firstResult, firstPlan, "", true),
        stageVerdict(attempts[30], req[30], secondResult),
        selectVerdict(attempts[31], req[31], secondPlan, secondResult, true), // selection ignores moved main
        publishSelectedVerdict(attempts[32], req[32], secondPlan, secondChoice, secondResult, false), // stale main
        absentRefVerdict(attempts[33], rejectedWriteVerdict(attempts[33], req[33], "")), // no proof
        abandonVerdict(attempts[34], req[34], secondPlan),
        scaleWriteVerdict(attempts[35], req[35], producer),
        selectVerdict(attempts[36], req[36], secondPlan, secondResult, false), // same-request stale plan ID
        publishVerdict(attempts[37], req[37], secondResult, bridgePlan, "", true),
        scaleWriteVerdict(attempts[38], req[38], producer),
        publishVerdict(attempts[39], req[39], secondResult, currentPlan, "", true),
        absentRefVerdict(attempts[40], rejectedWriteVerdict(attempts[40], req[40], "")), // old result pin consumed
        scaleWriteVerdict(attempts[41], req[41], producer),
        stageVerdict(attempts[42], req[42], firstResult),
        publishVerdict(attempts[43], req[43], firstResult, resetPlan, "", true),
        if (matches(attempts[44], req[44]) and attempts[44].removed > 0) "collected" else "wrong_collection",
        selectionReadVerdict(attempts[45], req[45], secondChoice, saved, secondRequest, scaleV2),
        scaleWriteVerdict(attempts[46], req[46], producer),
        if (staleMainChoice == secondChoice) "collapsed_selection"
        else publishSelectedVerdict(attempts[47], req[47], freshPlan, secondChoice, secondResult, false),
        publishSelectedVerdict(attempts[48], req[48], freshPlan, secondChoice, secondResult, false), // proof occupied
        publishSelectedVerdict(attempts[49], req[49], freshPlan, secondChoice, secondResult, true),
        selectedProofVerdict(attempts[50], req[50], proof, secondRequest, firstResult),
        versionedRequestedRead(selected, attempts[51], req[51], secondResult, secondRequest, sumRead, scaleV2),
        selectionReadVerdict(attempts[52], req[52], secondChoice, saved, secondRequest, scaleV2),
        selectionReadVerdict(attempts[53], req[53], firstChoice, { resultRef: "older", result: firstResult },
          firstRequest, scaleV1),
        absentRefVerdict(attempts[54], rejectedWriteVerdict(attempts[54], req[54], "")), // publishing plan consumed
        publishSelectedVerdict(attempts[55], req[55], freshPlan, secondChoice, secondResult, false)
      ))
    }
  }

  pure def selectAttemptVerdict(write: Attempt, req: Request, plan: str, occurrence: str, accepted: bool): str =
    if (write.expectedAttempt != occurrence) "wrong_selection"
    else if (not(accepted)) rejectedWriteVerdict(write, req, plan)
    else if (not(matches(write, req)) or write.expectedCommit != plan or write.commit == "" or write.unchanged)
      "wrong_selection_record"
    else "selected"

  pure def occurrenceReadVerdict(read: Attempt, req: Request, commit: str, portable: str, expected: Occurrence): str =
    if (not(matches(read, req))) "wrong_inspect"
    else if (not(read.unchanged)) "storage_changed"
    else if (read.commit != commit or read.requestCommit != portable or read.requestImplementation != scaleV2 or
      read.occurrence != expected or read.calls.length() != 0) "wrong_occurrence"
    else "inspected"

  pure def dropVerdict(drop: Attempt, req: Request, expected: str): str =
    if (not(matches(drop, req)) or drop.expectedCommit != expected or drop.unchanged) "wrong_fixture_drop"
    else "released"

  pure def attemptHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = attemptRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val plan = attempts[2].commit
      val portable = attempts[3].commit
      val result = attempts[5].commit
      val first = attempts[6].commit
      val second = attempts[7].commit
      val firstChoice = attempts[14].commit
      val secondChoice = attempts[20].commit
      val parallel = attempts[25].commit
      val recordedA: Occurrence = { id: occurrenceA, commit: first, result: result, historicalRef: "" }
      val recordedB: Occurrence = { id: occurrenceB, commit: second, result: result, historicalRef: "" }
      val chosenB = { ...recordedB, historicalRef: "returned" }
      val proof: SelectedPublication = { mode: "reuse", planRef: "plan", plan: plan, selectionRef: "chosen",
        selection: secondChoice, result: result }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(selected, sumRead, req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        requestExportVerdict(attempts[3], req[3], plan),
        stageVerdict(attempts[4], req[4], portable),
        scaleWriteVerdict(attempts[5], req[5], portable),
        scaleWriteVerdict(attempts[6], req[6], portable),
        scaleWriteVerdict(attempts[7], req[7], portable),
        rejectedWriteVerdict(attempts[8], req[8], portable), // Occupied by the exact attempt.
        occurrenceReadVerdict(attempts[9], req[9], first, portable, recordedA),
        occurrenceReadVerdict(attempts[10], req[10], second, portable, recordedB),
        exportVerdict(attempts[11], req[11], first),
        exportVerdict(attempts[12], req[12], second),
        stageVerdict(attempts[13], req[13], first),
        selectAttemptVerdict(attempts[14], req[14], plan, first, true),
        selectAttemptVerdict(attempts[15], req[15], plan, first, false), // Occupied by the exact selection.
        dropVerdict(attempts[16], req[16], first),
        stageVerdict(attempts[17], req[17], second),
        selectAttemptVerdict(attempts[18], req[18], plan, first, false), // Same-result attempt has replaced first.
        dropVerdict(attempts[19], req[19], firstChoice),
        selectAttemptVerdict(attempts[20], req[20], plan, second, true),
        publishSelectedVerdict(attempts[21], req[21], plan, firstChoice, result, false), // Moved chosen pin.
        dropVerdict(attempts[22], req[22], second),
        if (matches(attempts[23], req[23]) and attempts[23].removed > 0) "collected" else "wrong_collection",
        occurrenceReadVerdict(attempts[24], req[24], secondChoice, portable, chosenB),
        scaleWriteVerdict(attempts[25], req[25], producer),
        publishSelectedVerdict(attempts[26], req[26], plan, secondChoice, result, true),
        publishSelectedVerdict(attempts[27], req[27], parallel, secondChoice, result, false), // Stale main.
        versionedRequestedRead(selected, attempts[28], req[28], result, portable, sumRead, scaleV2),
        if (attempts[29].occurrence != recordedB) "wrong_occurrence"
        else selectedProofVerdict(attempts[29], req[29], proof, portable, "-"),
        occurrenceReadVerdict(attempts[30], req[30], secondChoice, portable, chosenB),
        absentRefVerdict(attempts[31], rejectedWriteVerdict(attempts[31], req[31], "")),
        absentRefVerdict(attempts[32], rejectedWriteVerdict(attempts[32], req[32], ""))
      )
    }
  }

  pure def adoptVerdict(write: Attempt, req: Request, basis: str, occurrence: str, accepted: bool): str =
    if (write.expectedCommit != basis or write.expectedAttempt != occurrence) "wrong_selection"
    else if (not(accepted)) rejectedWriteVerdict(write, req, basis)
    else if (not(matches(write, req)) or Set("", basis, occurrence).contains(write.commit) or write.unchanged)
      "wrong_adoption_record"
    else "adopted"

  pure def choiceReadVerdict(read: Attempt, req: Request, commit: str, portable: str, expected: Occurrence,
                             previous: str): str =
    if (read.previousSelection != previous) "wrong_predecessor"
    else occurrenceReadVerdict(read, req, commit, portable, expected)

  pure def attemptProofVerdict(read: Attempt, req: Request, expected: SelectedPublication, portable: str,
                               priorTip: str, occurrence: Occurrence): str =
    if (read.occurrence != occurrence or read.previousSelection != "") "wrong_occurrence"
    else selectedProofVerdict(read, req, expected, portable, priorTip)

  pure def adoptionHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = adoptionRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val sumRead = attempts[1]
      val plan = attempts[2].commit
      val portable = attempts[3].commit
      val result = attempts[5].commit
      val first = attempts[6].commit
      val base = attempts[9].commit
      val second = attempts[11].commit
      val third = attempts[12].commit
      val left = attempts[22].commit
      val right = attempts[25].commit
      val reverted = attempts[26].commit
      val leftPlan = attempts[38].commit
      val rightPlan = attempts[41].commit
      val recordedA: Occurrence = { id: occurrenceA, commit: first, result: result, historicalRef: "" }
      val recordedB: Occurrence = { id: occurrenceB, commit: second, result: result, historicalRef: "" }
      val recordedC: Occurrence = { id: occurrenceC, commit: third, result: result, historicalRef: "" }
      val chosenA = { ...recordedA, historicalRef: "returned-a" }
      val chosenB = { ...recordedB, historicalRef: "returned-b" }
      val chosenC = { ...recordedC, historicalRef: "returned-c" }
      val oldProof: SelectedPublication = { mode: "reuse", planRef: "plan", plan: plan, selectionRef: "base",
        selection: base, result: result }
      val leftProof: SelectedPublication = { ...oldProof, planRef: "left-plan", plan: leftPlan,
        selectionRef: "left", selection: left }
      val rightProof: SelectedPublication = { ...oldProof, planRef: "right-plan", plan: rightPlan,
        selectionRef: "right", selection: right }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(selected, sumRead, req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        requestExportVerdict(attempts[3], req[3], plan),
        stageVerdict(attempts[4], req[4], portable),
        scaleWriteVerdict(attempts[5], req[5], portable),
        scaleWriteVerdict(attempts[6], req[6], portable),
        exportVerdict(attempts[7], req[7], first),
        stageVerdict(attempts[8], req[8], first),
        selectAttemptVerdict(attempts[9], req[9], plan, first, true),
        choiceReadVerdict(attempts[10], req[10], base, portable, chosenA, ""),
        scaleWriteVerdict(attempts[11], req[11], portable),
        scaleWriteVerdict(attempts[12], req[12], portable),
        occurrenceReadVerdict(attempts[13], req[13], second, portable, recordedB),
        occurrenceReadVerdict(attempts[14], req[14], third, portable, recordedC),
        exportVerdict(attempts[15], req[15], second),
        exportVerdict(attempts[16], req[16], third),
        stageVerdict(attempts[17], req[17], second),
        stageVerdict(attempts[18], req[18], third),
        choiceReadVerdict(attempts[19], req[19], base, portable, chosenA, ""),
        adoptVerdict(attempts[20], req[20], base, first, false), // Already current.
        adoptVerdict(attempts[21], req[21], base, third, false), // Exact attempt guard, equal result.
        adoptVerdict(attempts[22], req[22], base, second, true),
        adoptVerdict(attempts[23], req[23], base, third, false), // Exact basis guard, equal result.
        adoptVerdict(attempts[24], req[24], base, second, false), // Identical output is occupied.
        adoptVerdict(attempts[25], req[25], base, third, true),
        adoptVerdict(attempts[26], req[26], left, first, true),
        choiceReadVerdict(attempts[27], req[27], left, portable, chosenB, base),
        choiceReadVerdict(attempts[28], req[28], right, portable, chosenC, base),
        choiceReadVerdict(attempts[29], req[29], reverted, portable, chosenA, left),
        absentRefVerdict(attempts[30], rejectedWriteVerdict(attempts[30], req[30], "")),
        dropVerdict(attempts[31], req[31], first),
        dropVerdict(attempts[32], req[32], second),
        dropVerdict(attempts[33], req[33], third),
        collectVerdict(attempts[34], req[34]),
        publishSelectedVerdict(attempts[35], req[35], plan, base, result, false), // Same T is not the same version.
        publishSelectedVerdict(attempts[36], req[36], plan, base, result, true),
        attemptProofVerdict(attempts[37], req[37], oldProof, portable, "-", recordedA),
        scaleWriteVerdict(attempts[38], req[38], producer),
        publishSelectedVerdict(attempts[39], req[39], leftPlan, left, result, true),
        attemptProofVerdict(attempts[40], req[40], leftProof, portable, result, recordedB),
        scaleWriteVerdict(attempts[41], req[41], producer),
        publishSelectedVerdict(attempts[42], req[42], rightPlan, right, result, true),
        attemptProofVerdict(attempts[43], req[43], rightProof, portable, result, recordedC),
        if (attempts[44].commit != attempts[37].commit) "wrong_reuse_record"
        else attemptProofVerdict(attempts[44], req[44], oldProof, portable, "-", recordedA),
        versionedRequestedRead(selected, attempts[45], req[45], result, portable, sumRead, scaleV2),
        choiceReadVerdict(attempts[46], req[46], base, portable, chosenA, "")
      )
    }
  }

  pure val noOccurrence: Occurrence = { id: "", commit: "", result: "", historicalRef: "" }

  pure def intentVerdict(write: Attempt, req: Request, producer: str, policy: str, selection: str,
                         accepted: bool): str =
    if (write.expectedPolicy != policy or write.expectedSelection != selection) "wrong_intent_guard"
    else if (not(accepted)) rejectedWriteVerdict(write, req, producer)
    else if (write.unchanged) "decision_not_written"
    else scaleWriteVerdict(write, req, producer)

  pure def decisionReadVerdict(read: Attempt, req: Request, commit: str, portable: str, priorTip: str,
                              expected: Decision, occurrence: Occurrence): str =
    if (not(matches(read, req)) or not(read.unchanged) or read.commit != commit or read.calls != List())
      "wrong_inspect"
    else if (read.requestCommit != portable or read.expectedMain != priorTip or read.occurrence != occurrence)
      "wrong_decision_lineage"
    else if (read.decision.id == "" or (expected.id != "" and read.decision.id != expected.id) or
      read.decision != { ...expected, id: read.decision.id }) "wrong_decision"
    else "inspected"

  pure def policyHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = policyRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val plan = attempts[2].commit
      val portable = attempts[3].commit
      val result = attempts[5].commit
      val first = attempts[6].commit
      val second = attempts[7].commit
      val base = attempts[12].commit
      val alternate = attempts[13].commit
      val active = attempts[14].commit
      val old = attempts[15].commit
      val reuse = attempts[16].commit
      val execute = attempts[17].commit
      val nextPlan = attempts[35].commit
      val firstAttempt: Occurrence = { id: occurrenceA, commit: first, result: result, historicalRef: "" }
      val defaultReuse: Decision = { id: "", canonicalId: true, policy: reuse, intent: "", defaultMode: "reuse-by-default",
        override: "default", route: "reuse-selected", reason: "default-selection", plan: plan, planRef: "",
        selectionRef: "active", selection: active, result: result, implementationOverride: "", implementationReason: "" }
      val forcedFresh: Decision = { ...defaultReuse, override: "fresh", route: "execute-fresh",
        reason: "override-fresh", plan: nextPlan, planRef: "forced-plan", selectionRef: "", selection: "", result: "" }
      val defaultExecute: Decision = { ...forcedFresh, policy: execute, defaultMode: "execute-by-default",
        override: "default", reason: "default-execution", planRef: "default-plan" }
      val forcedReuse: Decision = { ...defaultReuse, policy: execute, defaultMode: "execute-by-default",
        override: "reuse-selected", reason: "override-selected-reuse", plan: nextPlan }
      val fallback: Decision = { ...forcedFresh, override: "default", reason: "default-no-selection",
        planRef: "fallback-plan", selectionRef: "empty" }
      List(
        writeVerdict(attempts[0], req[0]),
        sumReadVerdict(selected, attempts[1], req[1], producer),
        scaleWriteVerdict(attempts[2], req[2], producer),
        requestExportVerdict(attempts[3], req[3], plan),
        stageVerdict(attempts[4], req[4], portable),
        scaleWriteVerdict(attempts[5], req[5], portable),
        scaleWriteVerdict(attempts[6], req[6], portable),
        scaleWriteVerdict(attempts[7], req[7], portable),
        exportVerdict(attempts[8], req[8], first),
        exportVerdict(attempts[9], req[9], second),
        stageVerdict(attempts[10], req[10], first),
        stageVerdict(attempts[11], req[11], second),
        selectAttemptVerdict(attempts[12], req[12], plan, first, true),
        adoptVerdict(attempts[13], req[13], base, second, true),
        adoptVerdict(attempts[14], req[14], alternate, first, true),
        scaleWriteVerdict(attempts[15], req[15], ""),
        scaleWriteVerdict(attempts[16], req[16], old),
        scaleWriteVerdict(attempts[17], req[17], reuse),
        if (matches(attempts[18], req[18]) and attempts[18].unchanged and attempts[18].commit == execute and
          attempts[18].policy == { defaultMode: "execute-by-default", previous: reuse }) "inspected"
        else "wrong_policy",
        intentVerdict(attempts[19], req[19], producer, old, active, false),
        intentVerdict(attempts[20], req[20], producer, reuse, "", false),
        intentVerdict(attempts[21], req[21], producer, reuse, active, false),
        intentVerdict(attempts[22], req[22], producer, reuse, base, false),
        intentVerdict(attempts[23], req[23], producer, reuse, "", false),
        intentVerdict(attempts[24], req[24], producer, reuse, "", false),
        intentVerdict(attempts[25], req[25], producer, reuse, active, false),
        intentVerdict(attempts[26], req[26], producer, reuse, active, true),
        decisionReadVerdict(attempts[27], req[27], attempts[26].commit, portable, "-", defaultReuse, firstAttempt),
        absentRefVerdict(attempts[28], rejectedWriteVerdict(attempts[28], req[28], "")),
        versionedRequestedRead(selected, attempts[29], req[29], result, portable, attempts[1], scaleV2),
        intentVerdict(attempts[30], req[30], producer, reuse, active, false),
        intentVerdict(attempts[31], req[31], producer, reuse, base, false),
        absentRefVerdict(attempts[32], rejectedWriteVerdict(attempts[32], req[32], "")),
        intentVerdict(attempts[33], req[33], producer, reuse, base, true),
        decisionReadVerdict(attempts[34], req[34], attempts[33].commit, portable, result, forcedFresh, noOccurrence),
        planReadWithTip(attempts[35], req[35], nextPlan, portable, 3, attempts[1], scaleV2, result),
        intentVerdict(attempts[36], req[36], producer, execute, base, true),
        decisionReadVerdict(attempts[37], req[37], attempts[36].commit, portable, result, defaultExecute, noOccurrence),
        intentVerdict(attempts[38], req[38], producer, execute, active, true),
        decisionReadVerdict(attempts[39], req[39], attempts[38].commit, portable, result, forcedReuse, firstAttempt),
        intentVerdict(attempts[40], req[40], producer, reuse, "", true),
        decisionReadVerdict(attempts[41], req[41], attempts[40].commit, portable, result, fallback, noOccurrence),
        if (attempts[42].commit == portable) requestExportVerdict(attempts[42], req[42], nextPlan)
        else "wrong_request_commit",
        if (attempts[43].commit == result) scaleWriteVerdict(attempts[43], req[43], portable)
        else "wrong_result_commit",
        dropVerdict(attempts[44], req[44], reuse),
        dropVerdict(attempts[45], req[45], old),
        dropVerdict(attempts[46], req[46], execute),
        dropVerdict(attempts[47], req[47], base),
        dropVerdict(attempts[48], req[48], alternate),
        dropVerdict(attempts[49], req[49], active),
        dropVerdict(attempts[50], req[50], first),
        dropVerdict(attempts[51], req[51], second),
        collectVerdict(attempts[52], req[52]),
        decisionReadVerdict(attempts[53], req[53], attempts[26].commit, portable, "-",
          { ...defaultReuse, id: attempts[27].decision.id }, firstAttempt),
        decisionReadVerdict(attempts[54], req[54], attempts[40].commit, portable, result,
          { ...fallback, id: attempts[41].decision.id }, noOccurrence)
      )
    }
  }

  pure def implementationIntentVerdict(write: Attempt, req: Request, producer: str, definition: str,
                                       selection: str, accepted: bool): str =
    if (write.expectedIntent != definition) "wrong_intent_guard"
    else intentVerdict(write, req, producer, "", selection, accepted)

  pure def intentReadVerdict(read: Attempt, req: Request, commit: str, expected: Intent): str =
    if (not(matches(read, req)) or not(read.unchanged) or read.commit != commit or read.calls != List() or
      read.intent != expected) "wrong_intent_definition"
    else "inspected"

  pure def intentDecisionReadVerdict(read: Attempt, req: Request, commit: str, portable: str, implementation: str,
                                    priorTip: str, expected: Decision, occurrence: Occurrence): str =
    if (read.requestImplementation != implementation) "wrong_decision_implementation"
    else decisionReadVerdict(read, req, commit, portable, priorTip, expected, occurrence)

  pure def implementationIntentSetupVerdicts(attempts: List[Attempt]): List[str] = {
    val req = implementationIntentRequests
    val producer = attempts[0].commit
    val basis = attempts[2].commit
    val left = attempts[3].commit
    val right = attempts[4].commit
    val aDefinition: Intent = { implementation: scaleV1, defaultMode: "reuse-by-default", v1Selection: "chosen-a",
      v2Selection: "chosen-b", previous: basis }
    val aPlan = attempts[8].decision.plan
    val aRequest = attempts[9].commit
    val aAttempt = attempts[11].commit
    val missA: Decision = { id: "", canonicalId: true, policy: "", intent: left, defaultMode: "reuse-by-default",
      override: "default", route: "execute-fresh", reason: "default-no-selection", plan: aPlan, planRef: "plan-a",
      selectionRef: "chosen-a", selection: "", result: "", implementationOverride: "default",
      implementationReason: "default-implementation" }
    List(
      writeVerdict(attempts[0], req[0]),
      sumReadVerdict(selected, attempts[1], req[1], producer),
      scaleWriteVerdict(attempts[2], req[2], ""),
      scaleWriteVerdict(attempts[3], req[3], basis),
      scaleWriteVerdict(attempts[4], req[4], basis),
      intentReadVerdict(attempts[5], req[5], left, aDefinition),
      intentReadVerdict(attempts[6], req[6], right, { ...aDefinition, implementation: scaleV2 }),
      implementationIntentVerdict(attempts[7], req[7], producer, left, "", true),
      intentDecisionReadVerdict(attempts[8], req[8], attempts[7].commit, aRequest, scaleV1, "-", missA, noOccurrence),
      requestExportVerdict(attempts[9], req[9], aPlan),
      stageVerdict(attempts[10], req[10], aRequest),
      scaleWriteVerdict(attempts[11], req[11], aRequest),
      exportVerdict(attempts[12], req[12], aAttempt),
      stageVerdict(attempts[13], req[13], aAttempt),
      selectAttemptVerdict(attempts[14], req[14], aPlan, aAttempt, true)
    )
  }

  pure def implementationIntentHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    val req = implementationIntentRequests
    if (attempts.length() != req.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val summed = attempts[1]
      val basis = attempts[2].commit
      val left = attempts[3].commit
      val right = attempts[4].commit
      val aPlan = attempts[8].decision.plan
      val aRequest = attempts[9].commit
      val aAttempt = attempts[11].commit
      val aSelection = attempts[14].commit
      val foreign = attempts[15].commit
      val aResult = attempts[20].commit
      val bPlan = attempts[25].decision.plan
      val bRequest = attempts[26].commit
      val bAttempt = attempts[28].commit
      val bSelection = attempts[32].commit
      val bResult = attempts[37].commit
      val recordedA: Occurrence = { id: occurrenceA, commit: aAttempt, result: aResult, historicalRef: "" }
      val recordedB: Occurrence = { id: occurrenceB, commit: bAttempt, result: bResult, historicalRef: "" }
      val missA: Decision = { id: "", canonicalId: true, policy: "", intent: left, defaultMode: "reuse-by-default",
        override: "default", route: "execute-fresh", reason: "default-no-selection", plan: aPlan, planRef: "plan-a",
        selectionRef: "chosen-a", selection: "", result: "", implementationOverride: "default",
        implementationReason: "default-implementation" }
      val overrideA: Decision = { ...missA, intent: right, route: "reuse-selected", reason: "default-selection",
        planRef: "", selection: aSelection, result: aResult, implementationOverride: scaleV1,
        implementationReason: "explicit-implementation" }
      val missB = { ...missA, intent: right, plan: bPlan, planRef: "plan-b", selectionRef: "chosen-b" }
      val reuseB = { ...missB, route: "reuse-selected", reason: "default-selection", planRef: "",
        selection: bSelection, result: bResult }
      val reuseA = { ...overrideA, intent: left, plan: attempts[39].decision.plan, implementationOverride: "default",
        implementationReason: "default-implementation" }
      implementationIntentSetupVerdicts(attempts).concat(List(
        selectAttemptVerdict(attempts[15], req[15], aPlan, aAttempt, true),
        implementationIntentVerdict(attempts[16], req[16], producer, right, foreign, false),
        implementationIntentVerdict(attempts[17], req[17], producer, right, "", false),
        implementationIntentVerdict(attempts[18], req[18], producer, right, aSelection, true),
        intentDecisionReadVerdict(attempts[19], req[19], attempts[18].commit, aRequest, scaleV1, "-", overrideA, recordedA),
        versionedRequestedRead(selected, attempts[20], req[20], aResult, aRequest, summed, scaleV1),
        implementationIntentVerdict(attempts[21], req[21], producer, basis, aSelection, false),
        implementationIntentVerdict(attempts[22], req[22], producer, right, "", false),
        dropVerdict(attempts[23], req[23], foreign),
        implementationIntentVerdict(attempts[24], req[24], producer, right, "", true),
        intentDecisionReadVerdict(attempts[25], req[25], attempts[24].commit, bRequest, scaleV2, aResult, missB, noOccurrence),
        requestExportVerdict(attempts[26], req[26], bPlan),
        stageVerdict(attempts[27], req[27], bRequest),
        scaleWriteVerdict(attempts[28], req[28], bRequest),
        exportVerdict(attempts[29], req[29], bAttempt),
        stageVerdict(attempts[30], req[30], bAttempt),
        implementationIntentVerdict(attempts[31], req[31], producer, right, "", false),
        selectAttemptVerdict(attempts[32], req[32], bPlan, bAttempt, true),
        implementationIntentVerdict(attempts[33], req[33], producer, right, foreign, false),
        implementationIntentVerdict(attempts[34], req[34], producer, right, bSelection, false),
        implementationIntentVerdict(attempts[35], req[35], producer, right, bSelection, true),
        intentDecisionReadVerdict(attempts[36], req[36], attempts[35].commit, bRequest, scaleV2, aResult, reuseB, recordedB),
        versionedRequestedRead(selected, attempts[37], req[37], bResult, bRequest, summed, scaleV2),
        implementationIntentVerdict(attempts[38], req[38], producer, left, aSelection, true),
        intentDecisionReadVerdict(attempts[39], req[39], attempts[38].commit, aRequest, scaleV1, bResult, reuseA, recordedA),
        dropVerdict(attempts[40], req[40], left),
        dropVerdict(attempts[41], req[41], right),
        dropVerdict(attempts[42], req[42], basis),
        dropVerdict(attempts[43], req[43], aSelection),
        dropVerdict(attempts[44], req[44], bSelection),
        dropVerdict(attempts[45], req[45], aAttempt),
        dropVerdict(attempts[46], req[46], bAttempt),
        collectVerdict(attempts[47], req[47]),
        intentDecisionReadVerdict(attempts[48], req[48], attempts[18].commit, aRequest, scaleV1, "-",
          { ...overrideA, id: attempts[19].decision.id }, recordedA),
        intentDecisionReadVerdict(attempts[49], req[49], attempts[35].commit, bRequest, scaleV2, aResult,
          { ...reuseB, id: attempts[36].decision.id }, recordedB),
        intentDecisionReadVerdict(attempts[50], req[50], attempts[24].commit, bRequest, scaleV2, aResult,
          { ...missB, id: attempts[25].decision.id }, noOccurrence),
        absentRefVerdict(attempts[51], rejectedWriteVerdict(attempts[51], req[51], "")),
        absentRefVerdict(attempts[52], rejectedWriteVerdict(attempts[52], req[52], "")),
        versionedRequestedRead(selected, attempts[53], req[53], aResult, aRequest, summed, scaleV1)
      ))
    }
  }

  pure val noDeclaration: Declaration = { commit: "", basis: "", evidence: "", predecessor: "", successor: "", reason: "" }
  pure val noAdvisory: Advisory = { intent: "", relation: "", declaration: noDeclaration }
  pure def unannotated(intent: str): Advisory = { intent: intent, relation: "none", declaration: noDeclaration }

  pure def declarationVerdict(write: Attempt, req: Request, basis: str, evidence: str, ok: bool): str =
    if (write.expectedIntent != basis or write.expectedEvidence != evidence) "wrong_declaration_guard"
    else if (not(ok)) rejectedWriteVerdict(write, req, "")
    else if (write.unchanged) "declaration_not_written"
    else writeVerdict(write, req)

  pure def advisoryDefinitionVerdict(read: Attempt, req: Request, commit: str, intent: Intent,
                                    expected: Declaration): str =
    if (not(read.definitionAdvisory) or read.supersession != expected) "wrong_definition_declaration"
    else intentReadVerdict(read, req, commit, intent)

  pure def advisoryViewVerdict(read: Attempt, verdict: str, historical: Advisory, knowledge: Advisory): str =
    if (verdict != "inspected") verdict
    else if (read.asKnownThen != historical) "wrong_historical_view"
    else if (read.knowledgeView != knowledge or read.expectedIntent != knowledge.intent) "wrong_knowledge_view"
    else "inspected"

  pure def supersessionHistoryVerdicts(attempts: List[Attempt]): List[str] = {
    if (attempts.length() != supersessionRequests.length()) List("missing_steps")
    else {
      val producer = attempts[0].commit
      val basis = attempts[2].commit
      val left = attempts[3].commit
      val right = attempts[4].commit
      val aDefinition: Intent = { implementation: scaleV1, defaultMode: "reuse-by-default", v1Selection: "chosen-a",
        v2Selection: "chosen-b", previous: basis }
      val aRequest = attempts[9].commit
      val aAttempt = attempts[11].commit
      val aSelection = attempts[14].commit
      val steps = attempts.slice(implementationIntentSetupLength, attempts.length())
      val req = advisoryRequests
      val aResult = steps[1].commit
      val audit = steps[3].commit
      val assertion = steps[7].commit
      val promoted = steps[14].commit
      val bPlan = steps[18].decision.plan
      val bRequest = steps[21].commit
      val bAttempt = steps[23].commit
      val bSelection = steps[26].commit
      val bResult = steps[28].commit
      val recordedA: Occurrence = { id: occurrenceA, commit: aAttempt, result: aResult, historicalRef: "" }
      val recordedB: Occurrence = { id: occurrenceB, commit: bAttempt, result: bResult, historicalRef: "" }
      val declaration = { commit: assertion, basis: left, evidence: audit, predecessor: scaleV1, successor: scaleV2,
        reason: "operational-replacement" }
      val predecessorView = { intent: assertion, relation: "predecessor", declaration: declaration }
      val successorView = { intent: promoted, relation: "successor", declaration: declaration }
      val thenBefore = unannotated(left)
      val reuseA: Decision = { id: "", canonicalId: true, policy: "", intent: left, defaultMode: "reuse-by-default",
        override: "default", route: "reuse-selected", reason: "default-selection", plan: steps[2].decision.plan,
        planRef: "", selectionRef: "chosen-a", selection: aSelection, result: aResult, implementationOverride: "default",
        implementationReason: "default-implementation" }
      val exactBefore = { ...reuseA, id: steps[2].decision.id }
      val missB = { ...reuseA, intent: promoted, route: "execute-fresh", reason: "default-no-selection", plan: bPlan,
        planRef: "plan-b", selectionRef: "chosen-b", selection: "", result: "" }
      val forcedB = { ...missB, override: "fresh", reason: "override-fresh", plan: steps[20].decision.plan,
        planRef: "forced-plan", selectionRef: "" }
      val reuseB = { ...reuseA, intent: promoted, plan: steps[29].decision.plan, selectionRef: "chosen-b",
        selection: bSelection, result: bResult }
      val setup = implementationIntentSetupVerdicts(attempts)
        .replaceAt(5, advisoryDefinitionVerdict(attempts[5], implementationIntentRequests[5], left, aDefinition, noDeclaration))
      setup.concat(List(
        implementationIntentVerdict(steps[0], req[0], producer, left, aSelection, true),
        versionedRequestedRead(selected, steps[1], req[1], aResult, aRequest, attempts[1], scaleV1),
        advisoryViewVerdict(steps[2], intentDecisionReadVerdict(steps[2], req[2], steps[0].commit, aRequest, scaleV1, "-",
          reuseA, recordedA), thenBefore, noAdvisory),
        writeVerdict(steps[3], req[3]),
        declarationVerdict(steps[4], req[4], basis, audit, false),
        declarationVerdict(steps[5], req[5], left, producer, false),
        declarationVerdict(steps[6], req[6], left, audit, false),
        declarationVerdict(steps[7], req[7], left, audit, true),
        advisoryDefinitionVerdict(steps[8], req[8], assertion, { ...aDefinition, previous: left }, declaration),
        declarationVerdict(steps[9], req[9], assertion, audit, false),
        advisoryViewVerdict(steps[10], intentDecisionReadVerdict(steps[10], req[10], steps[0].commit, aRequest, scaleV1, "-",
          exactBefore, recordedA), thenBefore, noAdvisory),
        advisoryViewVerdict(steps[11], intentDecisionReadVerdict(steps[11], req[11], steps[0].commit, aRequest, scaleV1, "-",
          exactBefore, recordedA), thenBefore, predecessorView),
        implementationIntentVerdict(steps[12], req[12], producer, assertion, aSelection, true),
        advisoryViewVerdict(steps[13], intentDecisionReadVerdict(steps[13], req[13], steps[12].commit, aRequest, scaleV1,
          aResult, { ...reuseA, intent: assertion, plan: steps[13].decision.plan }, recordedA),
          predecessorView, unannotated(right)),
        scaleWriteVerdict(steps[14], req[14], assertion),
        advisoryDefinitionVerdict(steps[15], req[15], promoted, { ...aDefinition, previous: assertion, implementation: scaleV2 },
          declaration),
        implementationIntentVerdict(steps[16], req[16], producer, promoted, aSelection, false),
        implementationIntentVerdict(steps[17], req[17], producer, promoted, "", true),
        advisoryViewVerdict(steps[18], intentDecisionReadVerdict(steps[18], req[18], steps[17].commit, bRequest, scaleV2,
          aResult, missB, noOccurrence), successorView, noAdvisory),
        implementationIntentVerdict(steps[19], req[19], producer, promoted, "", true),
        advisoryViewVerdict(steps[20], intentDecisionReadVerdict(steps[20], req[20], steps[19].commit, bRequest, scaleV2,
          aResult, forcedB, noOccurrence), successorView, thenBefore),
        requestExportVerdict(steps[21], req[21], bPlan),
        stageVerdict(steps[22], req[22], bRequest),
        scaleWriteVerdict(steps[23], req[23], bRequest),
        exportVerdict(steps[24], req[24], bAttempt),
        stageVerdict(steps[25], req[25], bAttempt),
        selectAttemptVerdict(steps[26], req[26], bPlan, bAttempt, true),
        implementationIntentVerdict(steps[27], req[27], producer, promoted, bSelection, true),
        versionedRequestedRead(selected, steps[28], req[28], bResult, bRequest, attempts[1], scaleV2),
        advisoryViewVerdict(steps[29], intentDecisionReadVerdict(steps[29], req[29], steps[27].commit, bRequest, scaleV2,
          aResult, reuseB, recordedB), successorView, noAdvisory),
        implementationIntentVerdict(steps[30], req[30], producer, left, aSelection, true),
        advisoryViewVerdict(steps[31], intentDecisionReadVerdict(steps[31], req[31], steps[30].commit, aRequest, scaleV1,
          bResult, { ...reuseA, plan: steps[31].decision.plan }, recordedA), thenBefore, { ...predecessorView, intent: promoted }),
        implementationIntentVerdict(steps[32], req[32], producer, promoted, aSelection, true),
        advisoryViewVerdict(steps[33], intentDecisionReadVerdict(steps[33], req[33], steps[32].commit, aRequest, scaleV1,
          aResult, { ...reuseA, intent: promoted, plan: steps[33].decision.plan, implementationOverride: scaleV1,
            implementationReason: "explicit-implementation" }, recordedA), { ...predecessorView, intent: promoted }, noAdvisory)
      ))
    }
  }

  pure def tableWriteVerdict(write: Attempt, req: Request, intent: str, basis: str, selection: str, ok: bool): str =
    if (write.expectedIntent != intent or write.expectedTable != basis or write.expectedSelection != selection)
      "wrong_table_guard"
    else if (not(ok)) rejectedWriteVerdict(write, req, "")
    else if (write.unchanged) "table_not_written"
    else writeVerdict(write, req)

  pure def tableEntry(portable: str, selection: str, attempt: Occurrence): ReuseTableEntry =
    { request: portable, selection: selection, result: attempt.result, attempt: attempt.commit, attemptId: attempt.id }

  pure def tableReadVerdict(read: Attempt, req: Request, commit: str, basis: str, intent: str,
                            entries: Set[ReuseTableEntry]): str =
    if (not(matches(read, req)) or not(read.unchanged) or read.commit != commit or read.calls != List()) "wrong_inspect"
    else if (read.reuseTable.intent != intent or read.reuseTable.previous != basis or
      read.reuseTable.implementation != scaleV1) "wrong_table_scope"
    else if (read.reuseTable.entries.length() != entries.size() or
      not(entries.forall(e => read.reuseTable.entries.indices().exists(i => read.reuseTable.entries[i] == e))))
      "wrong_table_entries"
    else "inspected"

  pure def tableRequestVerdict(write: Attempt, req: Request, producer: str, intent: str, table: str, ok: bool): str =
    if (write.expectedTable != table) "wrong_table_guard"
    else implementationIntentVerdict(write, req, producer, intent, "", ok)

  pure def tableDecision(intent: str, plan: str, planRef: str, selection: str, result: str,
                          implementation: str, override: str, reason: str): Decision = {
    id: "", canonicalId: true, policy: "", intent: intent, defaultMode: "reuse-by-default", override: override,
    route: if (selection == "") "execute-fresh" else "reuse-selected", reason: reason, plan: plan, planRef: planRef,
    selectionRef: "", selection: selection, result: result, implementationOverride: implementation,
    implementationReason: if (implementation == "default") "default-implementation" else "explicit-implementation"
  }

  pure def tableDecisionVerdict(read: Attempt, req: Request, commit: str, portable: str, prior: str,
                                tableRef: str, table: str, decision: Decision, attempt: Occurrence): str =
    if (read.tableRef != tableRef or read.tableCommit != table) "wrong_decision_table"
    else if (read.decision.plan == "" or read.decision.plan == portable) "wrong_decision_plan"
    else advisoryViewVerdict(read,
      intentDecisionReadVerdict(read, req, commit, portable, scaleV1, prior, decision, attempt),
      unannotated(decision.intent), noAdvisory)

  pure def workerTableAttemptVerdict(read: Attempt, req: Request, commit: str, portable: str,
                                    id: str, result: str, implementation: str): str =
    if (not(matches(read, req)) or not(read.unchanged) or read.commit != commit or read.requestCommit != portable or
      read.requestImplementation != implementation or read.calls != List() or result == "" or
      read.occurrence != { id: id, commit: commit, result: result, historicalRef: "" }) "wrong_occurrence"
    else "inspected"

  pure def tableBuildVerdicts(setup: List[Attempt], rows: List[Attempt]): List[str] = {
    val req = tableBuildRequests
    val left = setup[3].commit
    val aRequest = setup[9].commit
    val aAttempt = setup[11].commit
    val aChoice = setup[14].commit
    val root = rows[3].commit
    val tableA = rows[5].commit
    val bPlan = rows[7].decision.plan
    val bRequest = rows[8].commit
    val bAttempt = rows[10].commit
    val bChoice = rows[14].commit
    val expectedRows = Set(tableEntry(aRequest, aChoice, rows[0].occurrence),
      tableEntry(bRequest, bChoice, rows[11].occurrence))
    List(
      workerTableAttemptVerdict(rows[0], req[0], aAttempt, aRequest, occurrenceA, rows[0].occurrence.result, scaleV1),
      writeVerdict(rows[1], req[1]),
      sumReadVerdict(decoy, rows[2], req[2], rows[1].commit),
      tableWriteVerdict(rows[3], req[3], left, "", "", true),
      tableReadVerdict(rows[4], req[4], root, "", left, Set()),
      tableWriteVerdict(rows[5], req[5], "", root, aChoice, true),
      tableRequestVerdict(rows[6], req[6], rows[1].commit, left, tableA, true),
      tableDecisionVerdict(rows[7], req[7], rows[6].commit, bRequest, "-", "table-a", tableA,
        tableDecision(left, bPlan, "table-plan-b", "", "", "default", "default", "default-table-miss"), noOccurrence),
      requestExportVerdict(rows[8], req[8], bPlan),
      stageVerdict(rows[9], req[9], bRequest),
      scaleWriteVerdict(rows[10], req[10], bRequest),
      workerTableAttemptVerdict(rows[11], req[11], bAttempt, bRequest, occurrenceB, rows[11].occurrence.result, scaleV1),
      exportVerdict(rows[12], req[12], bAttempt),
      stageVerdict(rows[13], req[13], bAttempt),
      selectAttemptVerdict(rows[14], req[14], bPlan, bAttempt, true),
      tableWriteVerdict(rows[15], req[15], "", tableA, bChoice, true),
      tableReadVerdict(rows[16], req[16], rows[15].commit, tableA, left, expectedRows)
    )
  }

  pure def tableRoutingVerdicts(setup: List[Attempt], build: List[Attempt], rows: List[Attempt]): List[str] = {
    val req = tableRoutingRequests
    val producer = setup[0].commit
    val left = setup[3].commit
    val right = setup[4].commit
    val aRequest = setup[9].commit
    val aChoice = setup[14].commit
    val a = build[0].occurrence
    val decoyCommit = build[1].commit
    val bRequest = build[8].commit
    val bChoice = build[14].commit
    val b = build[11].occurrence
    val root = build[3].commit
    val tableA = build[5].commit
    val tableAB = build[15].commit
    val freshPlan = rows[12].decision.plan
    val c = rows[15].occurrence
    val cChoice = rows[18].commit
    val tableNext = rows[22].commit
    val expectedRows = Set(tableEntry(aRequest, cChoice, c), tableEntry(bRequest, bChoice, b))
    val hitA = tableDecision(right, rows[2].decision.plan, "", aChoice, a.result, scaleV1, "default", "default-table-hit")
    val hitB = tableDecision(left, rows[5].decision.plan, "", bChoice, b.result, "default", "default", "default-table-hit")
    val forced = tableDecision(left, freshPlan, "forced-plan", "", "", "default", "fresh", "override-fresh")
    val adoptedA = tableDecision(left, rows[25].decision.plan, "", cChoice, a.result,
      "default", "reuse-selected", "override-selected-reuse")
    val retainedA = tableDecision(left, rows[30].decision.plan, "", aChoice, a.result,
      "default", "default", "default-table-hit")
    val absence = tableDecision(left, rows[32].decision.plan, "absent-plan", "", "", "default", "default", "default-no-table")
    List(
      tableRequestVerdict(rows[0], req[0], producer, right, tableAB, false),
      tableRequestVerdict(rows[1], req[1], producer, right, tableAB, true),
      tableDecisionVerdict(rows[2], req[2], rows[1].commit, aRequest, "-", "table-ab", tableAB, hitA, a),
      versionedRequestedRead(selected, rows[3], req[3], a.result, aRequest, setup[1], scaleV1),
      tableRequestVerdict(rows[4], req[4], decoyCommit, left, tableAB, true),
      tableDecisionVerdict(rows[5], req[5], rows[4].commit, bRequest, a.result, "table-ab", tableAB, hitB, b),
      versionedRequestedRead(decoy, rows[6], req[6], b.result, bRequest, build[2], scaleV1),
      tableRequestVerdict(rows[7], req[7], producer, left, tableA, false),
      tableRequestVerdict(rows[8], req[8], producer, left, "", false),
      tableRequestVerdict(rows[9], req[9], decoyCommit, left, tableA, false),
      tableRequestVerdict(rows[10], req[10], producer, left, decoyCommit, false),
      tableRequestVerdict(rows[11], req[11], producer, left, decoyCommit, true),
      tableDecisionVerdict(rows[12], req[12], rows[11].commit, aRequest, b.result, "", "", forced, noOccurrence),
      if (rows[13].commit == aRequest) requestExportVerdict(rows[13], req[13], freshPlan) else "wrong_request_commit",
      scaleWriteVerdict(rows[14], req[14], aRequest),
      workerTableAttemptVerdict(rows[15], req[15], rows[14].commit, aRequest, occurrenceC, a.result, scaleV1),
      exportVerdict(rows[16], req[16], c.commit),
      stageVerdict(rows[17], req[17], c.commit),
      selectAttemptVerdict(rows[18], req[18], freshPlan, c.commit, true),
      tableWriteVerdict(rows[19], req[19], "", tableA, bChoice, false),
      tableWriteVerdict(rows[20], req[20], "", tableAB, aChoice, false),
      tableWriteVerdict(rows[21], req[21], "", tableAB, cChoice, false),
      tableWriteVerdict(rows[22], req[22], "", tableAB, cChoice, true),
      tableReadVerdict(rows[23], req[23], tableNext, tableAB, left, expectedRows),
      tableRequestVerdict(rows[24], req[24], producer, left, tableNext, true),
      tableDecisionVerdict(rows[25], req[25], rows[24].commit, aRequest, b.result, "table-next", tableNext, adoptedA, c),
      tableRequestVerdict(rows[26], req[26], decoyCommit, left, tableNext, true),
      tableDecisionVerdict(rows[27], req[27], rows[26].commit, bRequest, a.result, "table-next", tableNext,
        { ...hitB, plan: rows[27].decision.plan }, b),
      tableRequestVerdict(rows[28], req[28], producer, left, tableNext, false),
      tableRequestVerdict(rows[29], req[29], producer, left, tableAB, true),
      tableDecisionVerdict(rows[30], req[30], rows[29].commit, aRequest, b.result, "table-ab", tableAB, retainedA, a),
      tableRequestVerdict(rows[31], req[31], producer, left, "", true),
      tableDecisionVerdict(rows[32], req[32], rows[31].commit, aRequest, a.result, "uncreated", "", absence, noOccurrence),
      absentRefVerdict(rows[33], rejectedWriteVerdict(rows[33], req[33], ""))
    )
  }

  pure def offlineTableDecisionVerdict(read: Attempt, req: Request, historical: Attempt): str =
    tableDecisionVerdict(read, req, historical.commit, historical.requestCommit, historical.expectedMain,
      historical.tableRef, historical.tableCommit, historical.decision, historical.occurrence)

  pure def tableOfflineVerdicts(setup: List[Attempt], build: List[Attempt], route: List[Attempt],
                                rows: List[Attempt]): List[str] = {
    val req = tableOfflineRequests
    val releases = List(build[3].commit, build[5].commit, build[15].commit, route[22].commit, setup[14].commit,
      build[14].commit, route[18].commit, setup[11].commit, build[10].commit, route[14].commit, setup[3].commit)
    releases.foldl(List(), (out, expected) => {
      val i = out.length()
      out.append(dropVerdict(rows[i], req[i], expected))
    }).concat(List(
      collectVerdict(rows[11], req[11]),
      offlineTableDecisionVerdict(rows[12], req[12], route[25]),
      offlineTableDecisionVerdict(rows[13], req[13], route[30]),
      offlineTableDecisionVerdict(rows[14], req[14], build[7]),
      if (matches(rows[15], req[15]) and rows[15].unchanged and rows[15].expectedCommit == route[29].commit and
        rows[15].commit == route[29].commit) "staged" else "wrong_decision_transfer",
      offlineTableDecisionVerdict(rows[16], req[16], route[30])
    ))
  }

  pure val tableRouteOffset = implementationIntentSetupLength + tableBuildRequests.length()
  pure val tableOfflineOffset = tableRouteOffset + tableRoutingRequests.length()
  pure def multiInputVerdicts(attempts: List[Attempt]): List[str] = {
    if (attempts.length() != multiInputRequests.length()) List("missing_steps")
    else {
      val setup = attempts.slice(0, implementationIntentSetupLength)
      val build = attempts.slice(implementationIntentSetupLength, tableRouteOffset)
      val route = attempts.slice(tableRouteOffset, tableOfflineOffset)
      val offline = attempts.slice(tableOfflineOffset, attempts.length())
      implementationIntentSetupVerdicts(setup).concat(tableBuildVerdicts(setup, build))
        .concat(tableRoutingVerdicts(setup, build, route)).concat(tableOfflineVerdicts(setup, build, route, offline))
    }
  }

  pure def intentTableWriteVerdict(write: Attempt, req: Request, basis: str, selection: str,
                                  producer: str, ok: bool): str =
    if (write.expectedIntent != "" or write.expectedTable != basis or write.expectedSelection != selection or
      write.expectedCommit != producer) "wrong_table_guard"
    else if (not(ok)) rejectedWriteVerdict(write, req, producer)
    else if (write.unchanged) "table_not_written"
    else writeVerdict(write, req)

  pure def intentTableReadVerdict(read: Attempt, req: Request, commit: str, intent: str, genesis: str,
                                 basis: str, entries: Set[IntentReuseEntry]): str =
    if (not(matches(read, req)) or not(read.unchanged) or read.commit != commit or read.calls != List()) "wrong_inspect"
    else if (read.reuseScope != "intent" or read.intentReuseTable.intent != intent or
      read.intentReuseTable.genesis != genesis or read.intentReuseTable.previous != basis) "wrong_table_scope"
    else if (read.intentReuseTable.entries.length() != entries.size() or
      not(entries.forall(e => read.intentReuseTable.entries.indices().exists(i => read.intentReuseTable.entries[i] == e))))
      "wrong_table_entries"
    else "inspected"

  pure def intentTableEntry(producer: str, factor: int, request: str, implementation: str,
                            selection: str, attempt: Occurrence): IntentReuseEntry =
    { producer: producer, factor: factor, request: request, implementation: implementation,
      selection: selection, result: attempt.result, attempt: attempt.commit, attemptId: attempt.id }

  pure def entryOccurrence(row: IntentReuseEntry): Occurrence =
    { id: row.attemptId, commit: row.attempt, result: row.result, historicalRef: "" }

  pure val noProducingEntry = intentTableEntry("", 0, "", "", "", noOccurrence)

  pure def intentTableDecisionVerdict(read: Attempt, req: Request, commit: str, portable: str, implementation: str,
                                      prior: str, tableRef: str, table: str, decision: Decision,
                                      producing: IntentReuseEntry): str =
    if (read.reuseScope != "intent" or read.tableRef != tableRef or read.tableCommit != table) "wrong_decision_table"
    else if (read.producingRequest != producing.request or read.producingImplementation != producing.implementation)
      "wrong_producing_request"
    else if (read.decision.plan == "" or read.decision.plan == portable) "wrong_decision_plan"
    else advisoryViewVerdict(read,
      intentDecisionReadVerdict(read, req, commit, portable, implementation, prior, decision, entryOccurrence(producing)),
      unannotated(decision.intent), noAdvisory)

  pure def offlineIntentDecisionVerdict(read: Attempt, req: Request, historical: Attempt): str = {
    val producing = intentTableEntry("", 0, historical.producingRequest, historical.producingImplementation,
      historical.decision.selection, historical.occurrence)
    intentTableDecisionVerdict(read, req, historical.commit, historical.requestCommit, historical.requestImplementation,
      historical.expectedMain, historical.tableRef, historical.tableCommit, historical.decision, producing)
  }

  pure def decisionTransferVerdict(row: Attempt, req: Request, commit: str): str =
    if (matches(row, req) and row.unchanged and row.expectedCommit == commit and row.commit == commit) "staged"
    else "wrong_decision_transfer"

  pure def intentTableSetupVerdicts(setup: List[Attempt], rows: List[Attempt]): List[str] = {
    val req = intentTableSetup
    val left = setup[3].commit
    val empty = rows[3].commit
    List(
      workerTableAttemptVerdict(rows[0], req[0], setup[11].commit, setup[9].commit, occurrenceA,
        rows[0].occurrence.result, scaleV1),
      writeVerdict(rows[1], req[1]),
      sumReadVerdict(decoy, rows[2], req[2], rows[1].commit),
      tableWriteVerdict(rows[3], req[3], left, "", "", true),
      intentTableReadVerdict(rows[4], req[4], empty, left, setup[2].commit, "", Set()),
      intentTableWriteVerdict(rows[5], req[5], empty, setup[14].commit, "", true),
      tableWriteVerdict(rows[6], req[6], left, "", "", true)
    )
  }

  pure def intentTableBuildChoice(rows: List[Attempt], req: List[Request], producer: str, intent: str,
                                  implementation: str, tableRef: str, table: str, planRef: str, id: str): List[str] = {
    val plan = rows[1].decision.plan
    val portable = rows[2].commit
    val attempt = rows[4].commit
    val override = if (tableRef == "") "fresh" else "default"
    val reason = if (tableRef == "") "override-fresh" else "default-table-miss"
    // A forced fresh route gets a legacy table pin as input but does not retain it.
    val consulted = if (tableRef == "") "" else table
    List(
      tableRequestVerdict(rows[0], req[0], producer, intent, table, true),
      intentTableDecisionVerdict(rows[1], req[1], rows[0].commit, portable, implementation, "-", tableRef, consulted,
        tableDecision(intent, plan, planRef, "", "", "default", override, reason), noProducingEntry),
      requestExportVerdict(rows[2], req[2], plan),
      stageVerdict(rows[3], req[3], portable),
      scaleWriteVerdict(rows[4], req[4], portable),
      workerTableAttemptVerdict(rows[5], req[5], attempt, portable, id, rows[5].occurrence.result, implementation),
      exportVerdict(rows[6], req[6], attempt),
      stageVerdict(rows[7], req[7], attempt),
      selectAttemptVerdict(rows[8], req[8], plan, attempt, true)
    )
  }

  type IntentReplay = { producer: Attempt, other: Attempt, left: str, right: str, genesis: str,
    tableA: str, tableAD: str, tableADN: str, legacy: str, a: IntentReuseEntry, b: IntentReuseEntry,
    d: IntentReuseEntry, n: IntentReuseEntry }

  pure def intentTableHitVerdict(read: Attempt, req: Request, commit: str, portable: str, implementation: str,
                                 prior: str, intent: str, tableRef: str, table: str, producing: IntentReuseEntry,
                                 explicit: bool): str = {
    val reason = if (explicit) "override-selected-reuse" else "default-table-hit"
    val override = if (explicit) "reuse-selected" else "default"
    val decision = tableDecision(intent, read.decision.plan, "", producing.selection, producing.result,
      "default", override, reason)
    intentTableDecisionVerdict(read, req, commit, portable, implementation, prior, tableRef, table, decision, producing)
  }

  pure def intentTableFlowVerdicts(rows: List[Attempt], r: IntentReplay): List[str] = {
    val req = intentTableFlow
    val original = Set(r.a, r.d, r.n)
    val retained = Set(r.d, r.n)
    val producer = r.producer.commit
    val adopted = rows[10].commit
    val removed = rows[14].commit
    val miss = tableDecision(r.right, rows[19].decision.plan, "removal-plan", "", "", "default", "default",
      "default-table-miss")
    val absence = tableDecision(r.right, rows[34].decision.plan, "absent-intent-plan", "", "", "default", "default",
      "default-no-table")
    val negative = { ...selected, factor: ("-3", -3) }
    List(
      scaleWriteVerdict(rows[0], req[0], ""),
      tableRequestVerdict(rows[1], req[1], producer, rows[0].commit, r.tableADN, false),
      tableRequestVerdict(rows[2], req[2], producer, r.left, r.legacy, false),
      tableRequestVerdict(rows[3], req[3], producer, r.left, r.tableADN, false),
      tableRequestVerdict(rows[4], req[4], producer, r.right, r.tableAD, false),
      tableRequestVerdict(rows[5], req[5], producer, r.right, r.tableADN, true),
      intentTableHitVerdict(rows[6], req[6], rows[5].commit, r.b.request, scaleV2, "-", r.right,
        "intent-table-adn", r.tableADN, r.a, false),
      versionedRequestedRead(selected, rows[7], req[7], r.a.result, r.a.request, r.producer, scaleV1),
      absentRefVerdict(rows[8], rejectedWriteVerdict(rows[8], req[8], "")),
      intentTableWriteVerdict(rows[9], req[9], r.tableADN, r.b.selection, "", false),
      intentTableWriteVerdict(rows[10], req[10], r.tableADN, r.b.selection, "", true),
      intentTableReadVerdict(rows[11], req[11], adopted, r.left, r.genesis, r.tableADN, retained.union(Set(r.b))),
      intentTableReadVerdict(rows[12], req[12], r.tableADN, r.left, r.genesis, r.tableAD, original),
      intentTableWriteVerdict(rows[13], req[13], adopted, "", producer, false),
      intentTableWriteVerdict(rows[14], req[14], adopted, "", producer, true),
      intentTableReadVerdict(rows[15], req[15], removed, r.left, r.genesis, adopted, retained),
      intentTableWriteVerdict(rows[16], req[16], removed, "", producer, false),
      tableRequestVerdict(rows[17], req[17], producer, r.right, removed, false),
      tableRequestVerdict(rows[18], req[18], producer, r.right, removed, true),
      intentTableDecisionVerdict(rows[19], req[19], rows[18].commit, r.b.request, scaleV2, r.a.result,
        "intent-table-removed", removed, miss, noProducingEntry),
      planReadWithTip(rows[20], req[20], miss.plan, r.b.request, 3, r.producer, scaleV2, r.a.result),
      versionedRequestedRead(selected, rows[21], req[21], r.a.result, r.a.request, r.producer, scaleV1),
      tableRequestVerdict(rows[22], req[22], producer, r.left, adopted, true),
      intentTableHitVerdict(rows[23], req[23], rows[22].commit, r.a.request, scaleV1, r.a.result, r.left,
        "intent-table-adopted", adopted, r.b, true),
      versionedRequestedRead(selected, rows[24], req[24], r.b.result, r.b.request, r.producer, scaleV2),
      tableRequestVerdict(rows[25], req[25], r.other.commit, r.left, removed, true),
      intentTableHitVerdict(rows[26], req[26], rows[25].commit, r.d.request, scaleV1, r.b.result, r.left,
        "intent-table-removed", removed, r.d, false),
      versionedRequestedRead(decoy, rows[27], req[27], r.d.result, r.d.request, r.other, scaleV1),
      tableRequestVerdict(rows[28], req[28], producer, r.right, removed, true),
      intentTableHitVerdict(rows[29], req[29], rows[28].commit, r.n.request, scaleV2, r.d.result, r.right,
        "intent-table-removed", removed, r.n, false),
      versionedRequestedRead(negative, rows[30], req[30], r.n.result, r.n.request, r.producer, scaleV2),
      intentTableWriteVerdict(rows[31], req[31], removed, r.a.selection, "", true),
      intentTableReadVerdict(rows[32], req[32], rows[31].commit, r.left, r.genesis, removed, original),
      tableRequestVerdict(rows[33], req[33], producer, r.right, "", true),
      intentTableDecisionVerdict(rows[34], req[34], rows[33].commit, r.b.request, scaleV2, r.n.result,
        "uncreated", "", absence, noProducingEntry)
    )
  }

  pure def intentTableOfflineVerdicts(rows: List[Attempt], flow: List[Attempt], r: IntentReplay): List[str] = {
    val req = intentTableOffline
    val releases = List(r.tableADN, flow[14].commit, r.a.selection, r.b.selection, r.a.attempt, r.b.attempt, r.right)
    releases.foldl(List(), (out, expected) => {
      val i = out.length()
      out.append(dropVerdict(rows[i], req[i], expected))
    }).concat(List(
      collectVerdict(rows[7], req[7]),
      offlineIntentDecisionVerdict(rows[8], req[8], flow[6]),
      offlineIntentDecisionVerdict(rows[9], req[9], flow[19]),
      decisionTransferVerdict(rows[10], req[10], flow[5].commit),
      offlineIntentDecisionVerdict(rows[11], req[11], flow[6]),
      decisionTransferVerdict(rows[12], req[12], flow[18].commit),
      offlineIntentDecisionVerdict(rows[13], req[13], flow[19])
    ))
  }

  pure val intentTableDecoyOffset = implementationIntentSetupLength + intentTableSetup.length()
  pure val intentTableNegativeOffset = intentTableDecoyOffset + intentTableDecoy.length()
  pure val intentTableReplacementOffset = intentTableNegativeOffset + intentTableNegative.length()
  pure val intentTableFlowOffset = intentTableReplacementOffset + intentTableReplacement.length()
  pure val intentTableOfflineOffset = intentTableFlowOffset + intentTableFlow.length()

  pure def intentTableVerdicts(rows: List[Attempt]): List[str] = {
    if (rows.length() != intentTableRequests.length()) List("missing_steps")
    else {
      val base = rows.slice(0, implementationIntentSetupLength)
      val setup = rows.slice(implementationIntentSetupLength, intentTableDecoyOffset)
      val d = rows.slice(intentTableDecoyOffset, intentTableNegativeOffset)
      val n = rows.slice(intentTableNegativeOffset, intentTableReplacementOffset)
      val b = rows.slice(intentTableReplacementOffset, intentTableFlowOffset)
      val flow = rows.slice(intentTableFlowOffset, intentTableOfflineOffset)
      val offline = rows.slice(intentTableOfflineOffset, rows.length())
      val producer = base[0].commit
      val other = setup[1].commit
      val aEntry = intentTableEntry(producer, 3, base[9].commit, scaleV1, base[14].commit, setup[0].occurrence)
      val dEntry = intentTableEntry(other, 3, d[2].commit, scaleV1, d[8].commit, d[5].occurrence)
      val nEntry = intentTableEntry(producer, -3, n[2].commit, scaleV2, n[8].commit, n[5].occurrence)
      val bEntry = intentTableEntry(producer, 3, b[2].commit, scaleV2, b[8].commit, b[5].occurrence)
      val r: IntentReplay = { producer: base[1], other: setup[2], left: base[3].commit, right: base[4].commit,
        genesis: base[2].commit, tableA: setup[5].commit, tableAD: d[9].commit, tableADN: n[9].commit,
        legacy: setup[6].commit, a: aEntry, b: bEntry, d: dEntry, n: nEntry }
      implementationIntentSetupVerdicts(base).concat(intentTableSetupVerdicts(base, setup))
        .concat(intentTableBuildChoice(d, intentTableDecoy, other, r.left, scaleV1, "intent-table-a", r.tableA,
          "decoy-plan", occurrenceB))
        .append(intentTableWriteVerdict(d[9], intentTableDecoy[9], r.tableA, r.d.selection, "", true))
        .concat(intentTableBuildChoice(n, intentTableNegative, producer, r.right, scaleV2, "intent-table-ad", r.tableAD,
          "negative-plan", occurrenceC))
        .append(intentTableWriteVerdict(n[9], intentTableNegative[9], r.tableAD, r.n.selection, "", true))
        .append(intentTableReadVerdict(n[10], intentTableNegative[10], r.tableADN, r.left, r.genesis, r.tableAD,
          Set(r.a, r.d, r.n)))
        .concat(intentTableBuildChoice(b, intentTableReplacement, producer, r.right, scaleV2, "", r.legacy,
          "replacement-plan", replacementOccurrence))
        .concat(intentTableFlowVerdicts(flow, r)).concat(intentTableOfflineVerdicts(offline, flow, r))
    }
  }

  // These paths are observations from individual native calls. Compare them
  // to the CLI's claims, never use a report to choose the records to read.
  pure def nativeOutput(rows: List[Attempt], op: str, alias: str): Attempt =
    rows.select(row => row.op == op and row.args[row.args.length() - 1] == alias).head()
  pure def decoded(rows: List[Attempt], alias: str): Attempt = nativeOutput(rows, "object_decode", alias)
  pure def outputId(rows: List[Attempt], op: str, alias: str): str = nativeOutput(rows, op, alias).nativeValue
  pure def nativeNodeMatches(rows: List[Attempt], target: str): bool = {
    val stored = nativeOutput(rows, "txn_get_object", target)
    val encoded = rows.select(row => row.op == "object_encode" and row.args.length() == 4 and
      row.args[0] == "node" and row.args[2] == target).head()
    stored.nativeValue != "" and stored.nativeValue == encoded.nativeValue
  }
  pure def nativeLiteralMatches(rows: List[Attempt], target: str, kind: int, payload: str): bool = {
    val datum = nativeOutput(rows, "datum_decode", target)
    nativeNodeMatches(rows, target) and datum.nativeCount == kind and datum.nativeValue == payload
  }
  pure def nativeSnapshotMatches(rows: List[Attempt], path: SnapshotPath, commit: str,
                                  parents: int, entry: str): bool =
    commit == outputId(rows, "txn_ref_get", path.ref) and decoded(rows, path.commitView).nativeCount == parents and
    decoded(rows, path.treeView).nativeCount == 1 and
    nativeOutput(rows, "object_view_entry", path.dag).nativeItems == List(entry)

  // Preserve exact JSON keys at every object; the report checks below account
  // for all values represented by those keys.
  pure val callFields = List("arguments", "dag", "implementation", "result")
  pure val numericFields = List("node", "value")
  pure val scaleReportFields = List(callFields, List("a", "b"), numericFields, numericFields, numericFields,
    callFields, List("factor", "input"), numericFields, List("call", "node", "value"), numericFields)

  pure def combinedGraphMatches(rows: List[Attempt], report: Attempt): bool = {
    if (not(checkCalls(physicalRecord, report.calls, scaleV1))) false
    else {
      val summed = report.calls[0]
      val scaled = report.calls[1]
      all {
        nativeSnapshotMatches(rows, mainPath, report.commit, 0, "7265636f726465642d63616c6c732d7631"), // recorded-calls-v1
        report.commit == rows[0].commit,
        report.reportFields == List(List("calls", "commit")).concat(scaleReportFields),
        scaled.dag == outputId(rows, "object_view_entry", "main-dag"),
        summed.dag == decoded(rows, "sum-dag").nativeValue and nativeNodeMatches(rows, "sum-dag"),
        decoded(rows, "scale-root").nativeCount == 3 and decoded(rows, "sum-root").nativeCount == 3,
        summed.resultNode == decoded(rows, "sum-root").nativeValue,
        scaled.resultNode == decoded(rows, "scale-root").nativeValue,
        summed.arguments[0].node == outputId(rows, "txn_lookup_node", "sum-a"),
        summed.arguments[1].node == outputId(rows, "txn_lookup_node", "sum-b"),
        scaled.arguments[0].node == outputId(rows, "txn_lookup_node", "scale-factor"),
        scaled.arguments[1].node == outputId(rows, "txn_lookup_node", "scale-input"),
        combinedLiterals.foldl(true, (ok, fixture) =>
          ok and nativeLiteralMatches(rows, fixture.target, fixture.kind, fixture.payload))
      }
    }
  }

  pure val physicalDecoy: Scenario = { a: ("9", 9), b: ("3", 3), factor: ("3", 3) }
  pure val firstScaleRead = splitGraphSetup.length()
  pure val movedScaleRead = firstScaleRead + splitGraphReads.length() + moveProducer.length()
  pure val releasedScaleRead = movedScaleRead + splitGraphReads.length() + releaseProducers.length()

  pure def splitGraphMatches(rows: List[Attempt], report: Attempt, alternate: bool): bool = {
    val sumPath = if (alternate) decoyPath else producerPath
    val scalePath = if (alternate) alternatePath else mainPath
    val sourceDag = if (alternate) "alternate-source-dag" else "main-source-dag"
    val sourceNode = if (alternate) "alternate-input" else "main-input"
    val producer = rows[if (alternate) 1 else 0].commit
    val consumer = rows[if (alternate) 3 else 2].commit
    val scenario = if (alternate) physicalDecoy else selected
    if (not(checkCalls(scenario, report.calls, scaleV1))) false
    else {
      val summed = report.calls[0]
      val scaled = report.calls[1]
      all {
        nativeSnapshotMatches(rows, sumPath, producer, 0, "7265636f726465642d73756d2d7631"), // recorded-sum-v1
        nativeSnapshotMatches(rows, scalePath, consumer, 1, "7265636f726465642d7363616c652d7631"), // recorded-scale-v1
        report.commit == consumer and report.producerCommit == producer,
        report.reportFields == List(List("calls", "commit", "producer_commit")).concat(scaleReportFields),
        outputId(rows, "object_view_parent", scalePath.parent) == producer,
        summed.dag == outputId(rows, "object_view_entry", sumPath.dag),
        scaled.dag == outputId(rows, "object_view_entry", scalePath.dag),
        summed.dag == decoded(rows, sourceDag).nativeValue and nativeNodeMatches(rows, sourceDag),
        scaled.arguments[1].node == outputId(rows, "txn_lookup_node", sourceNode),
        summed.resultNode == decoded(rows, "producer-root").nativeValue,
        summed.resultNode == decoded(rows, "decoy-root").nativeValue,
        nativeLiteralMatches(rows, "producer-value", 3, "0c00000000000000"),
        rows[0].commit != rows[1].commit and rows[2].commit != rows[3].commit,
        outputId(rows, "object_view_entry", producerPath.dag) != outputId(rows, "object_view_entry", decoyPath.dag)
      }
    }
  }

  pure def physicalLabel(req: Request): str =
    if (req.op == "inspect") "inspected"
    else if (Set("record", "record_sum", "record_scale").contains(req.op)) "recorded"
    else if (req.op == "txn_ref_get" and Set("released-producer", "released-decoy").contains(req.args[2])) "native_not_found"
    else "native_ok"

  pure val physicalExpected = physicalRequests.foldl(List(), (out, reqs) =>
    out.append(reqs.foldl(List(), (labels, req) => labels.append(physicalLabel(req)))))

  pure def physicalInspect(rows: List[Attempt], index: int, split: bool): bool = {
    val report = rows[index]
    if (not(split)) combinedGraphMatches(rows, report)
    else if (index == 4) {
      sumReadVerdict(selected, report, splitGraphRequests[index], rows[0].commit) == "inspected" and
      report.calls[0].dag == outputId(rows, "object_view_entry", producerPath.dag)
    } else if (index < movedScaleRead) {
      splitGraphMatches(rows, report, index == firstScaleRead + 1) and
      (index != firstScaleRead or report.calls[0] == rows[4].calls[0])
    } else {
      val phase = if (index < releasedScaleRead) movedScaleRead else releasedScaleRead
      val original = rows[firstScaleRead + index - phase]
      report.commit == original.commit and report.producerCommit == original.producerCommit and
      report.calls == original.calls and report.reportFields == original.reportFields
    }
  }

  pure def physicalVerdicts(phase: int, rows: List[Attempt]): List[str] = {
    val reqs = physicalRequests[phase]
    val labels = physicalExpected[phase]
    if (rows.length() != reqs.length()) List("missing_steps")
    else if (not(reqs.indices().forall(i => sameRequest(rows[i], reqs[i])))) List("wrong_request")
    else range(0, reqs.length()).foldl(List(), (out, i) => {
      val attempt = rows[i]
      val request = reqs[i]
      val label = labels[i]
      val verdict = if (label == "recorded") {
        if (attempt.op == "record_scale") scaleWriteVerdict(attempt, request, rows[i - 2].commit)
        else writeVerdict(attempt, request)
      } else if (label == "inspected") {
        if (not(matches(attempt, request))) "wrong_inspect"
        else if (not(attempt.unchanged)) "storage_changed"
        else if (not(physicalInspect(rows, i, phase == 1))) "wrong_native_graph"
        else "inspected"
      } else if (label == "native_not_found") {
        if (attempt.nativeStatus == "not_found" and attempt.nativeDetail == absentRefDetail and
          attempt.nativeValue == "") label else "pin_not_absent"
      } else if (attempt.nativeStatus != "ok") "native_failure"
      else if (request.op == "txn_ref_get" and request.args[2] == "moved-producer" and
        attempt.nativeValue != rows[1].commit) "wrong_pin_target"
      else label
      out.append(verdict)
    })
  }

  // A persisted forgery shares the real decoy result tree, but has the selected
  // producer as its sole parent. Equal result roots do not make the DAGs interchangeable.
  pure def outboundForgery(rows: List[Attempt], producer: str, decoyCommit: str, other: str): bool = {
    val forged = outputId(rows, "txn_ref_get", "persisted-forgery")
    val forgedTree = decoded(rows, "forged-scale-commit").nativeValue
    val otherTree = decoded(rows, "other-scale-commit").nativeValue
    all {
      forged == outputId(rows, "txn_put_object", "forged-result"), forged != other,
      forgedTree != "", forgedTree == otherTree,
      outputId(rows, "txn_ref_get", "selected-incoming") == producer,
      outputId(rows, "txn_ref_get", "decoy-result-pin") == other,
      decoded(rows, "forged-scale-commit").nativeCount == 1,
      decoded(rows, "other-scale-commit").nativeCount == 1,
      outputId(rows, "object_view_parent", "forged-scale-parent") == producer,
      outputId(rows, "object_view_parent", "other-scale-parent") == decoyCommit,
      decoded(rows, "wrong-input-target").nativeValue == outputId(rows, "object_view_entry", "other-sum-dag"),
      decoded(rows, "wrong-input-target").nativeValue != outputId(rows, "object_view_entry", "selected-sum-dag"),
      nativeNodeMatches(rows, "wrong-input-target"),
      decoded(rows, "other-sum-root").nativeValue != "",
      decoded(rows, "other-sum-root").nativeValue == decoded(rows, "selected-sum-root").nativeValue
    }
  }

  pure val stageOccupiedDiagnostic = "stage-input: ('invalid_state', -30799, 'ref already exists')"
  pure val truncatedBundleDiagnostic = "stage-input: ('invalid_bounds', 0, 'invalid bundle record length')"
  pure val movedInputDiagnostic = "release-input: ('invalid_state', 0, 'ref target differs from the expected ID')"
  pure val movedStagingDiagnostic = "publish-scale: ('invalid_state', 0, 'ref target differs from the expected ID')"

  pure def outboundTruncated(a: Attempt, req: Request, expectedSize: int, fresh: bool): str = {
    val cause = a.stderr == truncatedBundleDiagnostic
    val verdict = if (fresh) cliRejectionVerdict(a, req, "", cause) else existingRejectionVerdict(a, req, "", cause)
    if (verdict != "rejected") verdict
    else if (fresh and a.repoExisted) "wrong_repository_presence"
    else if (not(a.bundlePresent and a.bundleUnchanged and a.bundleSize == expectedSize)) "wrong_bundle"
    else verdict
  }

  pure def outboundRejected(rows: List[Attempt], marks: (str) => Attempt, a: Attempt, s: TransferStep, producer: str): str = {
    val req = s.request
    val mark = s.mark
    if (mark == "wrong-export-pin") {
      val verdict = rejectedExport(a, req, producer, false)
      if (verdict != "rejected" or a.stderr == "export-sum: producer pin does not point to the expected commit") verdict
      else "wrong_diagnostic"
    } else if (mark == "no-clobber") rejectedExport(a, req, marks("decoy").commit, true)
    else if (mark == "same-occupied" or mark == "other-occupied") {
      val verdict = stageVerdict(a, req, "")
      if (verdict != "rejected" or a.stderr == stageOccupiedDiagnostic) verdict else "wrong_diagnostic"
    } else if (mark == "stale-scale") existingRejectionVerdict(a, req, producer,
      a.stderr == "record-scale: producer pin does not point to the expected commit")
    else if (mark == "missing-result") existingRejectionVerdict(a, req, producer, a.missingRef)
    else if (mark == "wrong-parent" or mark == "wrong-input") {
      val diagnostic = if (mark == "wrong-parent") "release-input: result does not retain the expected producer commit"
        else "release-input: scale input DAG does not match the producer parent"
      if (not(outboundForgery(rows, producer, marks("decoy").commit, marks("decoy-scale").commit))) "wrong_forgery"
      else existingRejectionVerdict(a, req, producer, a.stderr == diagnostic)
    } else if (mark == "moved-incoming") existingRejectionVerdict(a, req, producer,
      a.stderr == movedInputDiagnostic and outputId(rows, "txn_ref_get", "valid-result-pin") == marks("scaled").commit)
    else if (mark == "fresh-truncated" or mark == "existing-truncated")
      outboundTruncated(a, req, marks("truncated-copy").bundleSize, mark == "fresh-truncated")
    else if (req.op == "publish_scale") {
      val expectedMain = if (mark == "rollback-create") "-" else producer
      val cause = if (mark == "alias-main") a.stderr == "publish-scale: staging ref must differ from main"
        else if (mark == "missing-staging") a.missingRef else a.stderr == movedStagingDiagnostic
      if (a.expectedResult != marks("scaled").commit or a.expectedMain != expectedMain) "wrong_selection"
      else existingRejectionVerdict(a, req, producer, cause)
    } else "unknown_rejection"
  }

  pure def outboundVerdicts(phase: int, rows: List[Attempt]): List[str] = {
    val steps = outboundCases[phase]
    if (rows.length() != steps.length()) List("missing_steps")
    else {
      val marked = range(0, steps.length()).foldl(Map(), (byMark, i) =>
        if (steps[i].mark == "") byMark else byMark.put(steps[i].mark, rows[i]))
      def marks(mark: str): Attempt = marked.get(mark)
      val producer = if (phase == 0 or phase == 2) outputId(rows, "txn_put_object", "stored-sum-commit")
        else marks("producer").commit
      range(0, steps.length()).foldl(List(), (out, i) => {
        val a = rows[i]
        val s = steps[i]
        val req = s.request
        val mark = s.mark
        val verdict = if (s.label == "native_not_found") rejectionNativeReadVerdict(a, req, "")
          else if (mark == "kept-producer" or mark == "intact-pin") rejectionNativeReadVerdict(a, req, producer)
          else if (mark == "kept-other-pin") rejectionNativeReadVerdict(a, req, marks("other-scale").commit)
          else if (mark == "kept-decoy-pin") rejectionNativeReadVerdict(a, req, marks("decoy").commit)
          else if (s.label == "native_ok") {
            if (mark == "intact-closure" and (outputId(rows, "object_view_entry", "intact-sum-dag") !=
                outputId(rows, "txn_put_object", "stored-sum-dag") or a.nativeValue == "")) "wrong_native_graph"
            else rejectionNativeVerdict(a, req, "ok")
          } else if (s.label == "recorded") {
            if (req.op == "record_scale") scaleWriteVerdict(a, req, if (mark == "decoy-scale") marks("decoy").commit else producer)
            else if (mark == "decoy" and a.commit == producer) "collapsed_producers" else writeVerdict(a, req)
          } else if (s.label == "exported") exportVerdict(a, req, if (mark == "decoy-export") marks("decoy").commit else producer)
          else if (s.label == "staged") stageVerdict(a, req, if (mark == "decoy-stage") marks("decoy").commit else producer)
          else if (s.label == "released") releaseVerdict(a, req, producer)
          else if (s.label == "collected") {
            if (matches(a, req) and a.removed > 0) "collected" else "wrong_collection"
          } else if (s.label == "rejected") outboundRejected(rows, marks, a, s, producer)
          else if (s.label == "inspected") {
            if (not(matches(a, req))) "wrong_inspect"
            else if (not(a.unchanged)) "storage_changed"
            else if (mark == "collected-report") {
              if (storedLinkedReport(rows, a, marks("scaled").commit, true, -102, "9affffffffffffff") and
                  decoded(rows, "origin-decoy-root").nativeValue == outputId(rows, "txn_put_object", "stored-sum-root") and
                  outputId(rows, "object_view_entry", "origin-decoy-dag") != outputId(rows, "txn_put_object", "stored-sum-dag"))
                "inspected" else "wrong_native_graph"
            } else if (a.commit == marks("scaled").commit and a.commit != marks("other-scale").commit and
                a.producerCommit == producer and checkCalls(selected, a.calls, scaleV1)) "inspected" else "wrong_graph"
          } else if (s.label == "file_observed" and matches(a, req)) {
            val fileMatches = if (req.op == "unlink_bundle") not(a.bundlePresent) and a.bundleSize == -1
              else if (req.op == "truncate_bundle") a.bundlePresent and a.bundleUnchanged and a.unchanged and
                a.bundleSize > 0 and a.bundleSize + 1 == marks("selected-export").bundleSize
              else a.repoExists and (req.op == "checkpoint_file" or (req.op == "compare_file" and a.unchanged))
            if (fileMatches) "file_observed" else "wrong_file_observation"
          } else "unknown_transfer_step"
        out.append(verdict)
      })
    }
  }

  pure val sumEntryHex = "7265636f726465642d73756d2d7631"
  pure val scaleEntryHex = "7265636f726465642d7363616c652d7631"
  pure val combinedEntryHex = "7265636f726465642d63616c6c732d7631"
  pure def storedObject(rows: List[Attempt], alias: str): str = outputId(rows, "txn_put_object", alias)
  pure def storedRef(rows: List[Attempt], alias: str): str = outputId(rows, "txn_ref_get", alias)
  pure def treeEntry(rows: List[Attempt], tree: str, dag: str, name: str): bool =
    decoded(rows, tree).nativeCount == 1 and nativeOutput(rows, "object_view_entry", dag).nativeItems == List(name)

  // Inspection preserves stored evidence; it does not validate arithmetic.
  // For a fresh execution the caller supplies -102; for a retained result, -98.
  pure def storedLinkedReport(rows: List[Attempt], readback: Attempt, result: str, split: bool,
                            value: int, payload: str): bool = {
    val sumDag = storedObject(rows, "stored-sum-dag")
    val sumRoot = storedObject(rows, "stored-sum-root")
    val scaleDag = outputId(rows, "object_view_entry", "observed-scale-dag")
    val scaleRoot = decoded(rows, "observed-scale-root").nativeValue
    val input = outputId(rows, "txn_lookup_node", "observed-input")
    val producer = if (split) storedObject(rows, "stored-sum-commit") else ""
    val lineage = if (split) all {
      outputId(rows, "object_view_parent", "observed-scale-parent") == producer,
      decoded(rows, "observed-parent-commit").nativeCount == 0,
      treeEntry(rows, "observed-parent-tree", "observed-parent-dag", sumEntryHex),
      outputId(rows, "object_view_entry", "observed-parent-dag") == sumDag
    } else true
    if (readback.calls.length() != 2) false else {
      val summed = readback.calls[0]
      val scaled = readback.calls[1]
      all {
        readback.commit == result, storedRef(rows, "observed-scale-id") == result,
        readback.producerCommit == producer, lineage,
        readback.reportFields == List(if (split) List("calls", "commit", "producer_commit") else List("calls", "commit"))
          .concat(scaleReportFields),
        decoded(rows, "observed-scale-commit").nativeCount == (if (split) 1 else 0),
        treeEntry(rows, "observed-scale-tree", "observed-scale-dag", if (split) scaleEntryHex else combinedEntryHex),
        decoded(rows, "observed-scale-root").nativeCount == 3,
        decoded(rows, "observed-sum-root").nativeCount == 3,
        nativeNodeMatches(rows, "observed-sum-dag"), decoded(rows, "observed-sum-dag").nativeValue == sumDag,
        decoded(rows, "observed-sum-root").nativeValue == sumRoot,
        nativeLiteralMatches(rows, "observed-sum-value", 3, "efffffffffffffff"),
        nativeLiteralMatches(rows, "observed-scale-value", 3, payload),
        summed == { dag: sumDag, implementation: "example.sum@1", resultNode: sumRoot, resultValue: -17,
          arguments: List({ name: "a", node: storedObject(rows, "stored-a"), value: 2, producer: "" },
            { name: "b", node: storedObject(rows, "stored-b"), value: 3, producer: "" }) },
        scaled.dag == scaleDag, scaled.implementation == scaleV1, scaled.resultNode == scaleRoot, scaled.resultValue == value,
        scaled.arguments.length() == 2 and literal(scaled.arguments[0], "factor", 6) and
          scaled.arguments[1] == { name: "input", node: input, value: -17, producer: sumDag }
      }
    }
  }
  pure def storedScaleIdentity(rows: List[Attempt]): bool = all {
    outputId(rows, "object_view_entry", "observed-scale-dag") == storedObject(rows, "stored-scale-dag"),
    decoded(rows, "observed-scale-root").nativeValue == storedObject(rows, "stored-scale-root"),
    outputId(rows, "txn_lookup_node", "observed-input") == storedObject(rows, "stored-input")
  }
  pure def storedReadVerdict(rows: List[Attempt], a: Attempt, req: Request, result: str, split: bool,
                             value: int, payload: str): str =
    if (not(matches(a, req))) "wrong_inspect"
    else if (not(a.unchanged)) "storage_changed"
    else if (not(storedLinkedReport(rows, a, result, split, value, payload))) "wrong_stored_graph"
    else "inspected"

  pure def mismatchProof(rows: List[Attempt]): bool = all {
    rows[0].commit != rows[1].commit,
    storedRef(rows, "genuine-id") == rows[2].commit,
    outputId(rows, "object_view_parent", "genuine-parent") == rows[0].commit,
    outputId(rows, "object_view_entry", "selected-sum-dag") != outputId(rows, "object_view_entry", "decoy-sum-dag"),
    decoded(rows, "selected-sum-root").nativeValue == decoded(rows, "decoy-sum-root").nativeValue,
    nativeNodeMatches(rows, "genuine-input-dag"),
    decoded(rows, "genuine-input-dag").nativeValue == outputId(rows, "object_view_entry", "selected-sum-dag"),
    storedRef(rows, "persisted-mismatch") == storedObject(rows, "mismatch-id"),
    decoded(rows, "mismatch-commit").nativeValue == decoded(rows, "genuine-commit").nativeValue,
    decoded(rows, "mismatch-commit").nativeCount == 1,
    outputId(rows, "object_view_parent", "mismatch-parent") == rows[1].commit
  }
  pure def equivalentReports(a: Attempt, b: Attempt): bool =
    a.stdoutHash != "" and a.stdoutHash == b.stdoutHash and a.commit == b.commit and
    a.producerCommit == b.producerCommit and a.calls == b.calls and a.reportFields == b.reportFields
  pure def attemptFor(rows: List[Attempt], req: Request): Attempt = rows.select(a => sameRequest(a, req)).head()
  pure def storedNativeExpected(req: Request): str =
    if (req.op == "txn_ref_get" and Set("absent-main", "absent-main-after-wrong-factor", "absent-producer-before-publish",
      "absent-producer", "absent-decoy", "absent-returned", "absent-incoming", "absent-result").contains(req.args[2]))
      "native_not_found"
    else if (req.op == "txn_get_object" and req.args[3] == "swept-decoy") "native_not_found"
    else "native_ok"
  pure def storedExpectedLabel(phase: int, req: Request): str = {
    if (Set("record_sum", "record_scale").contains(req.op)) {
      if (phase == 1) "rejected" else "recorded"
    } else if (req.op == "inspect") {
      if (phase == 4 or (phase == 2 and req.args == List("source", "mismatch"))) "rejected" else "inspected"
    } else if (req.op == "export_scale" and phase == 2) "rejected"
    else if (req.op == "publish_scale") {
      if (phase == 2 or req.args[4] == "5") "rejected" else "published"
    } else if (Set("export_sum", "export_scale").contains(req.op)) "exported"
    else if (req.op == "stage_input") "staged"
    else if (req.op == "collect") "collected"
    else if (Set("unlink_bundle", "checkpoint_file", "compare_file").contains(req.op)) "file_observed"
    else storedNativeExpected(req)
  }
  pure val storedExpected: List[List[str]] = range(0, storedEvidenceRequests.length()).foldl(List(), (out, phase) =>
    out.append(storedEvidenceRequests[phase].foldl(List(), (labels, req) => labels.append(storedExpectedLabel(phase, req)))))

  pure def storedCliVerdict(phase: int, rows: List[Attempt], a: Attempt, req: Request): str = {
    val producer = if (phase == 2) rows[0].commit else if (phase != 3 and phase != 4)
      storedObject(rows, "stored-sum-commit") else ""
    val result = if (phase == 0) attemptFor(rows, source("record_scale", List("producer", producerId, "main", "6"))).commit
      else if (phase >= 3) storedObject(rows, "stored-scale-commit") else ""
    if (phase == 0) {
      if (req.op == "record_scale") scaleWriteVerdict(a, req, producer)
      else storedReadVerdict(rows, a, req, result, true, -102, "9affffffffffffff")
    } else if (phase == 1) {
      if (storedRef(rows, "unsupported-id") != producer or decoded(rows, "unsupported-commit").nativeCount != 0 or
          not(treeEntry(rows, "unsupported-tree", "unsupported-dag", sumEntryHex)) or
          not(nativeLiteralMatches(rows, "unsupported-value", 6, "6578616d706c652e73756d4032"))) "wrong_fixture"
      else existingRejectionVerdict(a, req, producer, a.stderr == "record-scale: expected recorded implementation example.sum@1")
    } else if (phase == 2) {
      val forged = storedObject(rows, "mismatch-id")
      if (req.op == "record_sum") writeVerdict(a, req)
      else if (req.op == "record_scale") scaleWriteVerdict(a, req, producer)
      else if (req == source("inspect", List())) {
        if (matches(a, req) and a.unchanged and a.commit == rows[2].commit and a.producerCommit == producer and
            checkCalls(selected, a.calls, scaleV1)) "inspected" else "wrong_valid_counterpart"
      } else if (not(mismatchProof(rows))) "wrong_fixture"
      else if (req.op == "export_scale" and (a.bundlePresent or not(a.bundleUnchanged))) "wrong_bundle"
      else if (req.op == "publish_scale" and (a.expectedMain != rows[2].commit or a.expectedResult != forged)) "wrong_selection"
      else existingRejectionVerdict(a, req,
        if (req.op == "inspect") "" else if (req.op == "export_scale") forged else rows[1].commit,
        Set("inspect: scale input DAG does not match the producer parent",
          "export-scale: scale input DAG does not match the producer parent",
          "publish-scale: scale input DAG does not match the producer parent").contains(a.stderr))
    } else if (phase == 3 or phase == 4) {
      val decoyDag = storedObject(rows, "equal-root-decoy")
      val sumRoot = storedObject(rows, "stored-sum-root")
      if (decoyDag == storedObject(rows, "stored-sum-dag") or decoded(rows, "equal-root-decoy-root").nativeValue != sumRoot)
        "wrong_fixture"
      else if (phase == 3) {
        if (not(storedScaleIdentity(rows))) "wrong_stored_graph"
        else storedReadVerdict(rows, a, req, result, false, -98, "9effffffffffffff")
      }
      else if (storedRef(rows, "observed-scale-id") != result or
          outputId(rows, "txn_lookup_node", "observed-input") != sumRoot or
          not(treeEntry(rows, "observed-scale-tree", "observed-scale-dag", combinedEntryHex)) or
          not(nativeLiteralMatches(rows, "observed-sum-value", 3, "efffffffffffffff"))) "wrong_fixture"
      else existingRejectionVerdict(a, req, "", a.stderr == "inspect: recorded source has the wrong node kind")
    } else if (req.op == "record_sum") {
      if (a.commit == producer) "collapsed_producers" else writeVerdict(a, req)
    } else if (req.op == "export_sum") exportVerdict(a, req, producer)
    else if (req.op == "export_scale") exportVerdict(a, req, result)
    else if (req.op == "stage_input") stageVerdict(a, req, if (req.args[0] == "worker") producer else result)
    else if (req.op == "inspect") {
      val workerReport = attemptFor(rows, worker("inspect", List("result")))
      if (not(equivalentReports(a, workerReport))) "wrong_return_report"
      else if (not(storedScaleIdentity(rows))) "wrong_stored_graph"
      else storedReadVerdict(rows, a, req, result, true, -98, "9effffffffffffff")
    } else if (req.op == "publish_scale") {
      val factorMatches = req.args[4] == "6"
      val verdict = publishVerdict(a, req, result, producer, "-", factorMatches)
      if (not(factorMatches) and verdict == "rejected" and
          a.stderr != "publish-scale: recorded factor does not match the expected factor") "wrong_diagnostic" else verdict
    } else if (req.op == "collect") {
      if (matches(a, req) and a.removed > 0) "collected" else "wrong_collection"
    } else if (req.op == "unlink_bundle") {
      if (matches(a, req) and not(a.bundlePresent) and a.bundleSize == -1) "file_observed" else "bundle_still_present"
    } else if (matches(a, req) and a.repoExists and (req.op == "checkpoint_file" or a.unchanged)) "file_observed"
    else "wrong_repository_bytes"
  }
  pure def storedVerdicts(phase: int, rows: List[Attempt]): List[str] = {
    val req = storedEvidenceRequests[phase]
    if (rows.length() != req.length()) List("missing_steps")
    else range(0, req.length()).foldl(List(), (out, i) => {
      val a = rows[i]
      val r = req[i]
      val label = storedExpected[phase][i]
      val verdict = if (label == "native_not_found") rejectionNativeReadVerdict(a, r, "")
        else if (label != "native_ok") storedCliVerdict(phase, rows, a, r)
        else if (r.op == "txn_get_object" and r.args[3] == "unrooted-return-decoy" and a.nativeValue == "") "missing_decoy"
        else if (r.op != "txn_ref_get") rejectionNativeVerdict(a, r, "ok")
        else if (r.args[2] == "unchanged-producer") rejectionNativeReadVerdict(a, r, storedObject(rows, "stored-sum-commit"))
        else if (r.args[2] == "unchanged-main") rejectionNativeReadVerdict(a, r, rows[2].commit)
        else if (r.args[2] == "unchanged-mismatch") rejectionNativeReadVerdict(a, r, storedObject(rows, "mismatch-id"))
        else if (Set("staged-result", "retained-result").contains(r.args[2]))
          rejectionNativeReadVerdict(a, r, storedObject(rows, "stored-scale-commit"))
        else rejectionNativeVerdict(a, r, "ok")
      out.append(verdict)
    })
  }

  pure val storedEvidenceOffset = scenarios.length() + 19 + rejectionRequests.length()
  pure val outboundOffset = storedEvidenceOffset + storedEvidenceRequests.length()
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
    else if (row.scenario == scenarios.length() + 9) selectionHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 10) attemptHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 11) adoptionHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 12) policyHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 13) implementationIntentHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 14) supersessionHistoryVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 15) multiInputVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 16) intentTableVerdicts(row.attempts)
    else if (row.scenario >= scenarios.length() + 17 and row.scenario < scenarios.length() + 19)
      physicalVerdicts(row.scenario - scenarios.length() - 17, row.attempts)
    else if (row.scenario >= outboundOffset and row.scenario < outboundOffset + outboundRequests.length())
      outboundVerdicts(row.scenario - outboundOffset, row.attempts)
    else if (row.scenario >= storedEvidenceOffset and row.scenario < outboundOffset)
      storedVerdicts(row.scenario - storedEvidenceOffset, row.attempts)
    else if (row.scenario >= scenarios.length() + 19 and row.scenario < storedEvidenceOffset)
      rejectionVerdicts(row.scenario - scenarios.length() - 19, row.attempts)
    else togetherVerdicts(row)

  pure def verdictAccepted(verdict: str): bool =
    Set("recorded", "inspected", "rejected", "exported", "staged", "released", "collected", "published",
      "acknowledged", "abandoned", "reused", "selected", "adopted", "native_ok", "native_not_found", "file_observed").contains(verdict)

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
    val selections = versioned.slice(0, 19).concat(List("rejected", "rejected", "selected", "rejected",
      "inspected", "rejected", "inspected", "inspected", "selected", "rejected", "published", "staged",
      "selected", "rejected", "rejected", "abandoned", "recorded", "rejected", "published", "recorded",
      "published", "rejected", "recorded", "staged", "published", "collected", "inspected", "recorded",
      "rejected", "rejected", "published", "inspected", "inspected", "inspected", "inspected", "rejected",
      "rejected"))
    val occurrences = List("recorded", "inspected", "recorded", "exported", "staged", "recorded", "recorded",
      "recorded", "rejected", "inspected", "inspected", "exported", "exported", "staged", "selected", "rejected",
      "released", "staged", "rejected", "released", "selected", "rejected", "released", "collected", "inspected",
      "recorded", "published", "rejected", "inspected", "inspected", "inspected", "rejected", "rejected")
    val adoptions = occurrences.slice(0, 7).concat(List("exported", "staged", "selected", "inspected",
      "recorded", "recorded", "inspected", "inspected", "exported", "exported", "staged", "staged", "inspected",
      "rejected", "rejected", "adopted", "rejected", "rejected", "adopted", "adopted", "inspected", "inspected",
      "inspected", "rejected", "released", "released", "released", "collected", "rejected", "published",
      "inspected", "recorded", "published", "inspected", "recorded", "published", "inspected", "inspected",
      "inspected", "inspected"))
    val policies = occurrences.slice(0, 8).concat(List("exported", "exported", "staged", "staged", "selected",
      "adopted", "adopted", "recorded", "recorded", "recorded", "inspected", "rejected", "rejected", "rejected",
      "rejected", "rejected", "rejected", "rejected", "recorded", "inspected", "rejected", "inspected", "rejected",
      "rejected", "rejected", "recorded", "inspected", "inspected", "recorded", "inspected", "recorded", "inspected",
      "recorded", "inspected", "exported", "recorded", "released", "released", "released", "released", "released",
      "released", "released", "released", "collected", "inspected", "inspected"))
    val implementationIntents = List("recorded", "inspected", "recorded", "recorded", "recorded", "inspected",
      "inspected", "recorded", "inspected", "exported", "staged", "recorded", "exported", "staged", "selected",
      "selected", "rejected", "rejected", "recorded", "inspected", "inspected", "rejected", "rejected", "released",
      "recorded", "inspected", "exported", "staged", "recorded", "exported", "staged", "rejected", "selected", "rejected",
      "rejected", "recorded", "inspected", "inspected", "recorded", "inspected", "released", "released", "released",
      "released", "released", "released", "released", "collected", "inspected", "inspected", "inspected", "rejected",
      "rejected", "inspected")
    val supersessions = implementationIntents.slice(0, implementationIntentSetupLength).concat(List(
      "recorded", "inspected", "inspected", "recorded", "rejected", "rejected", "rejected", "recorded",
      "inspected", "rejected", "inspected", "inspected", "recorded", "inspected", "recorded", "inspected",
      "rejected", "recorded", "inspected", "recorded", "inspected", "exported", "staged", "recorded", "exported",
      "staged", "selected", "recorded", "inspected", "inspected", "recorded", "inspected", "recorded", "inspected"))
    val tableBuild = List("inspected", "recorded", "inspected", "recorded", "inspected", "recorded",
      "recorded", "inspected", "exported", "staged", "recorded", "inspected", "exported", "staged", "selected",
      "recorded", "inspected")
    val tableRoute = List("rejected", "recorded", "inspected", "inspected", "recorded", "inspected", "inspected",
      "rejected", "rejected", "rejected", "rejected", "recorded", "inspected", "exported", "recorded", "inspected",
      "exported", "staged", "selected", "rejected", "rejected", "rejected", "recorded", "inspected", "recorded",
      "inspected", "recorded", "inspected", "rejected", "recorded", "inspected", "recorded", "inspected", "rejected")
    val tableOffline = List("released", "released", "released", "released", "released", "released", "released",
      "released", "released", "released", "released", "collected", "inspected", "inspected", "inspected", "staged",
      "inspected")
    val multiInput = implementationIntents.slice(0, implementationIntentSetupLength)
      .concat(tableBuild).concat(tableRoute).concat(tableOffline)
    val intentTableBuild = List("recorded", "inspected", "exported", "staged", "recorded", "inspected",
      "exported", "staged", "selected")
    val intentTable = implementationIntents.slice(0, implementationIntentSetupLength)
      .concat(List("inspected", "recorded", "inspected", "recorded", "inspected", "recorded", "recorded"))
      .concat(intentTableBuild).append("recorded").concat(intentTableBuild).append("recorded").append("inspected")
      .concat(intentTableBuild).concat(List(
        "recorded", "rejected", "rejected", "rejected", "rejected", "recorded", "inspected", "inspected", "rejected",
        "rejected", "recorded", "inspected", "inspected", "rejected", "recorded", "inspected", "rejected", "rejected",
        "recorded", "inspected", "inspected", "inspected", "recorded", "inspected", "inspected", "recorded",
        "inspected", "inspected", "recorded", "inspected", "inspected", "recorded", "inspected", "recorded", "inspected",
        "released", "released", "released", "released", "released", "released", "released", "collected",
        "inspected", "inspected", "staged", "inspected", "staged", "inspected"))
    val expected = List(together, together, separate, handoff, roundTrip, durable, retry, abandon,
      reuse, reusePublication, versioned, selections, occurrences, adoptions, policies, implementationIntents,
      supersessions, multiInput, intentTable).concat(physicalExpected).concat(rejectionExpected)
      .concat(storedExpected).concat(outboundExpected)
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
      val choices = rows[11].attempts
      val worked = rows[12].attempts
      val resultsAndOccurrences = Set(worked[5].commit, worked[6].commit, worked[7].commit)
      val adopted = rows[13].attempts
      val versionsOfChoice = Set(adopted[9].commit, adopted[22].commit, adopted[25].commit, adopted[26].commit)
      val executed = Set(adopted[5].commit, adopted[6].commit, adopted[11].commit, adopted[12].commit)
      val decided = rows[14].attempts
      val occurrenceIds = Set(27, 34, 37, 39, 41).map(index => decided[index].decision.id)
      val decisionCommits = Set(26, 33, 36, 38, 40).map(index => decided[index].commit)
      val intents = rows[15].attempts
      val aCall = intents[20].calls[1]
      val bCall = intents[37].calls[1]
      val intentDecisions = Set(8, 19, 25, 36, 39)
      val advisoryHistory = rows[16].attempts
      val advisory = advisoryHistory.slice(implementationIntentSetupLength, advisoryHistory.length())
      val advisoryDecisions = Set(2, 13, 18, 20, 29, 31, 33)
      val multi = rows[17].attempts
      val tableHistory = multi.slice(implementationIntentSetupLength, tableRouteOffset)
      val tableDecisions = multi.slice(tableRouteOffset, tableOfflineOffset)
      val tableDecisionIds = Set(2, 5, 12, 25, 27, 30, 32).map(i => tableDecisions[i].decision.id)
        .union(Set(tableHistory[7].decision.id))
      val intentRows = rows[18].attempts.slice(intentTableFlowOffset, intentTableOfflineOffset)
      rows.indices().forall(i => rows[i].scenario == i) and
        intentRows[6].requestCommit != intentRows[6].producingRequest and
        intentRows[23].requestCommit != intentRows[23].producingRequest and
        intentRows[7].calls == intentRows[21].calls and
        sameRootNotSameCall(intentRows[7].calls[1], intentRows[24].calls[1]) and
        sameRootNotSameCall(intentRows[7].calls[1], intentRows[27].calls[1]) and
        tableDecisionIds.size() == 8 and
        Set(tableHistory[3].commit, tableHistory[5].commit, tableHistory[15].commit,
          tableDecisions[22].commit).size() == 4 and
        tableHistory[0].occurrence.commit != tableDecisions[15].occurrence.commit and
        tableHistory[0].occurrence.result == tableDecisions[15].occurrence.result and
        tableHistory[0].requestCommit != tableHistory[11].requestCommit and
        tableHistory[0].occurrence.result != tableHistory[11].occurrence.result and
        sameRootNotSameCall(tableDecisions[3].calls[1], tableDecisions[6].calls[1]) and
        advisoryDecisions.map(i => advisory[i].commit).size() == advisoryDecisions.size() and
        advisoryDecisions.map(i => advisory[i].decision.id).size() == advisoryDecisions.size() and
        Set(advisoryHistory[2].commit, advisoryHistory[3].commit, advisoryHistory[4].commit,
          advisory[7].commit, advisory[14].commit).size() == 5 and
        advisoryHistory[0].commit != advisory[3].commit and
        advisoryHistory[9].commit != advisory[21].commit and advisoryHistory[14].commit != advisory[26].commit and
        sameRootNotSameCall(advisory[1].calls[1], advisory[28].calls[1]) and
        intentDecisions.map(i => intents[i].commit).size() == 5 and
        intentDecisions.map(i => intents[i].decision.id).size() == 5 and
        Set(intents[2].commit, intents[3].commit, intents[4].commit).size() == 3 and
        intents[9].commit != intents[26].commit and intents[11].commit != intents[28].commit and
        intents[20].commit != intents[37].commit and intents[8].decision.plan != intents[39].decision.plan and
        sameRootNotSameCall(aCall, bCall) and aCall.arguments == bCall.arguments and
        occurrenceIds.size() == 5 and decisionCommits.size() == 5 and
        Set(decided[15].commit, decided[16].commit, decided[17].commit).size() == 3 and
        Set(decided[12].commit, decided[13].commit, decided[14].commit).size() == 3 and
        decided[2].commit != decided[35].commit and
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
        versions[14].calls == versions[26].calls and versions[26].calls == versions[28].calls and
        sameRootNotSameCall(choices[13].calls[1], choices[14].calls[1]) and
        choices[7].commit != choices[6].commit and choices[4].commit != choices[35].commit and
        choices[35].commit == choices[46].commit and choices[14].calls == choices[51].calls and
        resultsAndOccurrences.size() == 3 and not(resultsAndOccurrences.contains(worked[3].commit)) and
        worked[14].commit != worked[20].commit and worked[2].commit == worked[25].commit and
        versionsOfChoice.size() == 4 and executed.size() == 4 and versionsOfChoice.intersect(executed) == Set()
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
    quiet: true, diagnosed: false, missingRef: false, stderr: "", stdoutEmpty: false,
    repoExisted: false, repoExists: false, errorType: "", pathUses: -1,
    nativeStatus: "", nativeDetail: "", nativeValue: "", nativeCount: 0,
    nativeItems: List(),
    commit: "commit", calls: List(), reportFields: List(), stdoutHash: "", historicalReportHash: "",
    expectedCommit: "", producerCommit: "", unchanged: false,
    removed: -1, expectedResult: "", expectedSelection: "", expectedAttempt: "", expectedMain: "",
    previousSelection: "", requestCommit: "",
    requestImplementation: "", requestFactor: 0, bundlePresent: false, bundleUnchanged: true, bundleSize: -1,
    publication: { planRef: "", plan: "", stagingRef: "", result: "" },
    reusePublication: { mode: "", planRef: "", plan: "", resultRef: "", result: "" },
    selection: { resultRef: "", result: "" },
    selectedPublication: { mode: "", planRef: "", plan: "", selectionRef: "", selection: "", result: "" },
    occurrence: noOccurrence, policy: { defaultMode: "", previous: "" }, expectedPolicy: "",
    intent: { implementation: "", defaultMode: "", v1Selection: "", v2Selection: "", previous: "" }, expectedIntent: "",
    expectedEvidence: "", definitionAdvisory: false, supersession: noDeclaration, asKnownThen: noAdvisory,
    knowledgeView: noAdvisory, expectedTable: "", tableRef: "", tableCommit: "",
    reuseTable: { intent: "", implementation: "", previous: "", entries: List() },
    reuseScope: "", producingRequest: "", producingImplementation: "",
    intentReuseTable: { intent: "", genesis: "", previous: "", entries: List() },
    decision: { id: "", canonicalId: false, policy: "", intent: "", defaultMode: "", override: "", route: "",
      reason: "", plan: "", planRef: "", selectionRef: "", selection: "", result: "", implementationOverride: "",
      implementationReason: "" } }
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
    code: 1, quiet: false, diagnosed: true, stdoutEmpty: true, commit: "", unchanged: true }
  pure val staged: Attempt = { ...recorded, op: "stage_input", args: handoffRequests[12].args,
    bundlePresent: true }
  pure val rejectedExportControl: Attempt = { ...recorded, op: "export_sum", args: handoffRequests[4].args,
    code: 1, quiet: false, diagnosed: true, stdoutEmpty: true, commit: "", expectedCommit: "commit", unchanged: true }
  pure val released: Attempt = { ...recorded, op: "release_input", args: handoffRequests[19].args,
    expectedCommit: "commit" }
  pure val published: Attempt = { ...recorded, op: "publish_scale", args: returnRequests[17].args,
    commit: "result", expectedResult: "result", expectedCommit: "producer", expectedMain: "-" }
  pure val rejectedPublication: Attempt = { ...published, args: returnRequests[21].args, commit: "", expectedMain: "tip",
    code: 1, quiet: false, diagnosed: true, stdoutEmpty: true, unchanged: true }
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
  pure val selectedProof: SelectedPublication = { mode: "reuse", planRef: "fresh-v2", plan: "fresh-plan",
    selectionRef: "chosen-v2", selection: "selection", result: "result" }
  pure val selectedProofRead: Attempt = { ...reuseRead, args: selectionRequests[50].args,
    selectedPublication: selectedProof }
  pure def checkSelectedProof(readback: Attempt): str =
    selectedProofVerdict(readback, selectionRequests[50], selectedProof, "request", "prior")
  pure val savedOccurrence: Occurrence = {
    id: occurrenceB, commit: "attempt-b-commit", result: "same-result", historicalRef: "returned" }
  pure val occurrenceRead: Attempt = { ...recorded, op: "inspect", args: attemptRequests[24].args,
    commit: "chosen", unchanged: true, requestCommit: "request", requestImplementation: scaleV2,
    occurrence: savedOccurrence }
  pure def checkOccurrence(read: Attempt): str =
    occurrenceReadVerdict(read, attemptRequests[24], "chosen", "request", savedOccurrence)
  pure val adoptionRead: Attempt = { ...occurrenceRead, args: adoptionRequests[27].args,
    previousSelection: "base", occurrence: { ...savedOccurrence, historicalRef: "returned-b" } }
  pure def checkAdoption(read: Attempt): str = choiceReadVerdict(read, adoptionRequests[27], "chosen", "request",
    { ...savedOccurrence, historicalRef: "returned-b" }, "base")
  pure val savedDecision: Decision = { id: occurrenceC, canonicalId: true, policy: "policy", intent: "",
    defaultMode: "reuse-by-default", override: "default", route: "reuse-selected", reason: "default-selection",
    plan: "plan", planRef: "", selectionRef: "active", selection: "selection", result: "same-result",
    implementationOverride: "", implementationReason: "" }
  pure val decisionRead: Attempt = { ...occurrenceRead, args: policyRequests[27].args,
    commit: "decision", expectedMain: "-", decision: savedDecision }
  pure def checkDecision(read: Attempt): str = decisionReadVerdict(read, policyRequests[27], "decision", "request",
    "-", savedDecision, savedOccurrence)
  pure val savedIntentDecision: Decision = { ...savedDecision, policy: "", intent: "right", selectionRef: "chosen-a",
    implementationOverride: scaleV1, implementationReason: "explicit-implementation" }
  pure val intentDecisionRead: Attempt = { ...decisionRead, args: implementationIntentRequests[19].args,
    requestImplementation: scaleV1, decision: savedIntentDecision }
  pure def checkIntentDecision(read: Attempt): str = intentDecisionReadVerdict(read, implementationIntentRequests[19],
    "decision", "request", scaleV1, "-", savedIntentDecision, savedOccurrence)
  pure val savedDeclaration: Declaration = { commit: "annotation", basis: "right", evidence: "audit",
    predecessor: scaleV1, successor: scaleV2, reason: "operational-replacement" }
  pure val knownAdvisory: Advisory = { intent: "promoted", relation: "predecessor", declaration: savedDeclaration }
  pure val advisoryRead: Attempt = { ...intentDecisionRead, asKnownThen: unannotated("right"),
    expectedIntent: "promoted", knowledgeView: knownAdvisory }
  pure def checkAdvisory(read: Attempt): str =
    advisoryViewVerdict(read, checkIntentDecision(read), unannotated("right"), knownAdvisory)
  pure val sampleTableRow = tableEntry("request", "selection", savedOccurrence)
  pure val sampleTableRead: Attempt = { ...recorded, op: "inspect", args: tableRoutingRequests[23].args,
    unchanged: true, reuseTable: { intent: "intent", implementation: scaleV1, previous: "basis",
      entries: List(sampleTableRow) } }
  pure def checkTable(read: Attempt): str =
    tableReadVerdict(read, tableRoutingRequests[23], "commit", "basis", "intent", Set(sampleTableRow))
  pure val sampleTableDecision = { ...intentDecisionRead, args: tableRoutingRequests[2].args, tableRef: "table-ab",
    tableCommit: "table", asKnownThen: unannotated("right"),
    decision: tableDecision("right", "plan", "", "selection", "same-result", scaleV1, "default", "default-table-hit") }
  pure def checkTableDecision(read: Attempt): str =
    tableDecisionVerdict(read, tableRoutingRequests[2], "decision", "request", "-", "table-ab", "table",
      sampleTableDecision.decision, savedOccurrence)
  pure val sampleIntentRow = intentTableEntry("producer", -3, "producing-request", scaleV1, "selection", savedOccurrence)
  pure val sampleIntentTable = { ...sampleTableRead, args: intentTableFlow[15].args, reuseScope: "intent",
    intentReuseTable: { intent: "intent", genesis: "genesis", previous: "basis", entries: List(sampleIntentRow) } }
  pure def checkIntentTable(read: Attempt): str =
    intentTableReadVerdict(read, intentTableFlow[15], "commit", "intent", "genesis", "basis", Set(sampleIntentRow))
  pure val sampleIntentTableDecision = { ...sampleTableDecision, args: intentTableFlow[6].args, reuseScope: "intent",
    requestImplementation: scaleV2, producingRequest: sampleIntentRow.request, producingImplementation: scaleV1,
    occurrence: entryOccurrence(sampleIntentRow),
    decision: { ...tableDecision("right", "plan", "", "selection", "same-result", "default", "default", "default-table-hit"),
      id: occurrenceC } }
  pure def checkIntentTableDecision(read: Attempt): str =
    intentTableDecisionVerdict(read, intentTableFlow[6], "decision", "request", scaleV2, "-", "table-ab", "table",
      sampleIntentTableDecision.decision, sampleIntentRow)
  pure val controlsPass = all {
    rejectionControls(recorded),
    checkIntentTable(sampleIntentTable) == "inspected",
    checkIntentTable({ ...sampleIntentTable, intentReuseTable: { ...sampleIntentTable.intentReuseTable,
      genesis: "unrelated" } }) == "wrong_table_scope",
    checkIntentTable({ ...sampleIntentTable, intentReuseTable: { ...sampleIntentTable.intentReuseTable,
      entries: List({ ...sampleIntentRow, factor: 3 }) } }) == "wrong_table_entries",
    checkIntentTable({ ...sampleIntentTable, intentReuseTable: { ...sampleIntentTable.intentReuseTable,
      entries: List({ ...sampleIntentRow, producer: "equal-valued-other-commit" }) } }) == "wrong_table_entries",
    checkIntentTableDecision(sampleIntentTableDecision) == "inspected",
    checkIntentTableDecision({ ...sampleIntentTableDecision, producingRequest: "request" }) == "wrong_producing_request",
    checkIntentTableDecision({ ...sampleIntentTableDecision, producingImplementation: scaleV2 }) == "wrong_producing_request",
    checkIntentTableDecision({ ...sampleIntentTableDecision, requestImplementation: scaleV1 }) == "wrong_decision_implementation",
    checkTable(sampleTableRead) == "inspected",
    checkTable({ ...sampleTableRead, reuseTable: { ...sampleTableRead.reuseTable,
      entries: List({ ...sampleTableRow, request: "equal-valued-foreign-key" }) } }) == "wrong_table_entries",
    checkTable({ ...sampleTableRead, reuseTable: { ...sampleTableRead.reuseTable,
      entries: List({ ...sampleTableRow, attempt: "equal-result-foreign-attempt" }) } }) == "wrong_table_entries",
    checkTable({ ...sampleTableRead, reuseTable: { ...sampleTableRead.reuseTable, previous: "other-branch" } })
      == "wrong_table_scope",
    checkTableDecision({ ...sampleTableDecision, decision: { ...sampleTableDecision.decision, id: occurrenceC } })
      == "inspected",
    checkTableDecision({ ...sampleTableDecision, tableCommit: "newer-version" }) == "wrong_decision_table",
    checkAdvisory(advisoryRead) == "inspected",
    checkAdvisory({ ...advisoryRead, asKnownThen: knownAdvisory }) == "wrong_historical_view",
    checkAdvisory({ ...advisoryRead, knowledgeView: noAdvisory }) == "wrong_knowledge_view",
    checkAdvisory({ ...advisoryRead, expectedIntent: "annotation" }) == "wrong_knowledge_view",
    checkAdvisory({ ...advisoryRead, knowledgeView: { ...knownAdvisory,
      declaration: { ...savedDeclaration, evidence: "wrong-audit" } } }) == "wrong_knowledge_view",
    checkIntentDecision(intentDecisionRead) == "inspected",
    checkIntentDecision({ ...intentDecisionRead, requestImplementation: scaleV2 }) == "wrong_decision_implementation",
    checkIntentDecision({ ...intentDecisionRead, decision: { ...savedIntentDecision,
      implementationOverride: "default" } }) == "wrong_decision",
    checkIntentDecision({ ...intentDecisionRead, decision: { ...savedIntentDecision,
      implementationReason: "default-implementation" } }) == "wrong_decision",
    checkIntentDecision({ ...intentDecisionRead, decision: { ...savedIntentDecision,
      selectionRef: "chosen-b" } }) == "wrong_decision",
    checkDecision(decisionRead) == "inspected",
    checkDecision({ ...decisionRead, decision: { ...savedDecision, id: occurrenceA } }) == "wrong_decision",
    checkDecision({ ...decisionRead, decision: { ...savedDecision, policy: "other-policy" } }) == "wrong_decision",
    checkDecision({ ...decisionRead, decision: { ...savedDecision, selection: "other-selection" } }) == "wrong_decision",
    checkDecision({ ...decisionRead, decision: { ...savedDecision, planRef: "unexpected-plan-ref" } }) == "wrong_decision",
    checkDecision({ ...decisionRead, occurrence: { ...savedOccurrence, commit: "other-attempt" } })
      == "wrong_decision_lineage",
    checkAdoption(adoptionRead) == "inspected",
    checkAdoption({ ...adoptionRead, previousSelection: "other-selection" }) == "wrong_predecessor",
    checkOccurrence(occurrenceRead) == "inspected",
    checkOccurrence({ ...occurrenceRead, occurrence: { ...savedOccurrence, commit: "other-attempt" } })
      == "wrong_occurrence",
    checkOccurrence({ ...occurrenceRead, occurrence: { ...savedOccurrence, result: "other-result" } })
      == "wrong_occurrence",
    checkOccurrence({ ...occurrenceRead, occurrence: { ...savedOccurrence, id: occurrenceA } })
      == "wrong_occurrence",
    checkSelectedProof(selectedProofRead) == "inspected",
    checkSelectedProof({ ...selectedProofRead, selectedPublication: { ...selectedProof, selection: "other" } })
      == "wrong_reuse_record",
    checkSelectedProof({ ...selectedProofRead, selectedPublication: { ...selectedProof, selectionRef: "other" } })
      == "wrong_reuse_record",
    checkSelectedProof({ ...selectedProofRead, selectedPublication: { ...selectedProof, result: "other" } })
      == "wrong_reuse_record",
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
