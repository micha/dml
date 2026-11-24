module recorded_calls_rules {
  import recorded_calls_histories.* from "./recorded_calls_histories"

  type Argument = { name: str, node: str, value: int, producer: str }
  type Call = { dag: str, implementation: str, resultNode: str, resultValue: int, arguments: List[Argument] }
  type Attempt = { op: str, args: List[str], code: int, quiet: bool, diagnosed: bool, commit: str, calls: List[Call],
    expectedCommit: str, producerCommit: str, unchanged: bool, removed: int,
    bundlePresent: bool, bundleUnchanged: bool }
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

  pure def checkCalls(s: Scenario, calls: List[Call]): bool = {
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
          scaled.implementation == "example.scale@1", literal(scaled.arguments[0], "factor", s.factor._2),
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
        else if (not(checkCalls(scenario, readback.calls))) "wrong_graph"
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

  pure def scaleReadVerdict(s: Scenario, readback: Attempt, request: Request, recordedCommit: str,
                           sumRead: Attempt): str =
    if (not(matches(readback, request))) "wrong_inspect"
    else if (not(readback.unchanged)) "storage_changed"
    else if (readback.commit != recordedCommit or readback.producerCommit != sumRead.commit) "wrong_commit"
    else if (not(checkCalls(s, readback.calls))) "wrong_graph"
    else if (sumRead.calls.length() != 1) "missing_producer"
    else if (readback.calls[0] != sumRead.calls[0]) "wrong_producer"
    else "inspected"

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

  pure def exportVerdict(attempt: Attempt, request: Request, expected: str): str =
    if (not(matches(attempt, request)) or attempt.expectedCommit != expected or attempt.commit != expected) "wrong_export"
    else if (not(attempt.unchanged)) "storage_changed"
    else if (not(attempt.bundlePresent) or attempt.bundleUnchanged) "wrong_bundle"
    else "exported"

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

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario == scenarios.length()) separateVerdicts(row.attempts)
    else if (row.scenario == scenarios.length() + 1) handoffVerdicts(row.attempts)
    else togetherVerdicts(row)

  pure def verdictAccepted(verdict: str): bool =
    Set("recorded", "inspected", "rejected", "exported", "staged", "released", "collected").contains(verdict)

  pure def sameRootNotSameCall(first: Call, second: Call): bool =
    first.resultNode == second.resultNode and first.dag != second.dag

  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool = {
    val together = List("recorded", "inspected")
    val separate = List("recorded", "recorded", "inspected", "inspected", "rejected", "rejected", "rejected",
      "recorded", "rejected", "recorded", "inspected", "inspected")
    val handoff = List("recorded", "recorded", "inspected", "inspected", "rejected", "exported", "exported",
      "rejected", "staged", "rejected", "rejected", "inspected", "staged", "rejected", "inspected", "recorded",
      "inspected", "rejected", "rejected", "released", "collected", "rejected", "inspected", "rejected", "inspected")
    if (rows.length() != 4 or verdicts != List(together, together, separate, handoff)) false
    else {
      val split = rows[2].attempts
      val transfer = rows[3].attempts
      rows[0].scenario == 0 and rows[1].scenario == 1 and rows[2].scenario == 2 and rows[3].scenario == 3 and
        sameRootNotSameCall(rows[0].attempts[1].calls[0], rows[1].attempts[1].calls[0]) and
        sameRootNotSameCall(split[2].calls[0], split[3].calls[0]) and split[0].commit != split[1].commit and
        split[7].commit != split[9].commit and transfer[0].commit != transfer[1].commit and
        sameRootNotSameCall(transfer[14].calls[0], transfer[11].calls[0]) and
        transfer[14].calls == transfer[2].calls and transfer[11].calls == transfer[3].calls and
        transfer[16].calls == transfer[22].calls
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
    quiet: true, diagnosed: false, commit: "commit", calls: List(), expectedCommit: "", producerCommit: "", unchanged: false,
    removed: -1, bundlePresent: false, bundleUnchanged: true }
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
  pure val controlsPass = all {
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
    checkCalls(scenarios[0], List(summed, scaled)),
    not(checkCalls(scenarios[0], List(summed, { ...scaled, resultValue: 37 }))),
    not(checkCalls(scenarios[0], List(summed, { ...scaled, implementation: "example.scale@2" }))),
    not(checkCalls(scenarios[0], List(summed, { ...scaled, arguments: List(factor, { ...input,
      producer: "different-call-with-same-value" }) })))
  }
}
