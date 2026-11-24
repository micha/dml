module recorded_calls_rules {
  import recorded_calls_histories.* from "./recorded_calls_histories"

  type Argument = { name: str, node: str, value: int, producer: str }
  type Call = { dag: str, implementation: str, resultNode: str, resultValue: int, arguments: List[Argument] }
  type Attempt = { op: str, args: List[str], code: int, quiet: bool, commit: str, calls: List[Call], unchanged: bool }
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure def literal(arg: Argument, name: str, value: int): bool =
    arg.name == name and arg.producer == "" and arg.node != "" and arg.value == value

  pure def checkCalls(s: Scenario, calls: List[Call]): bool = {
    if (calls.length() != 2) false
    else {
      val summed = calls[0]
      val scaled = calls[1]
      if (summed.arguments.length() != 2 or scaled.arguments.length() != 2) false
      else {
        val combined = s.a._2 + s.b._2
        val input = scaled.arguments[1] // Runner sorts the argument names.
        all {
          summed.dag != "", scaled.dag != "", scaled.dag != summed.dag,
          summed.resultNode != "", scaled.resultNode != "",
          summed.implementation == "example.sum@1", scaled.implementation == "example.scale@1",
          literal(summed.arguments[0], "a", s.a._2), literal(summed.arguments[1], "b", s.b._2),
          literal(scaled.arguments[0], "factor", s.factor._2),
          input.name == "input", input.producer == summed.dag, input.node != "", input.node != summed.resultNode,
          summed.resultValue == combined, input.value == combined, scaled.resultValue == combined * s.factor._2
        }
      }
    }
  }

  pure def matches(attempt: Attempt, request: Request): bool =
    attempt.op == request.op and attempt.args == request.args and attempt.code == 0 and attempt.quiet

  pure def historyVerdicts(row: Observation): List[str] = {
    if (not(scenarios.indices().contains(row.scenario)) or row.attempts.length() != 2) List("missing_steps")
    else {
      val scenario = scenarios[row.scenario]
      val expected = requests(scenario)
      val write = row.attempts[0]
      val readback = row.attempts[1]
      List(
        if (matches(write, expected[0]) and write.commit != "") "recorded" else "wrong_record",
        if (not(matches(readback, expected[1]))) "wrong_inspect"
        else if (not(readback.unchanged)) "storage_changed"
        else if (readback.commit != write.commit) "wrong_commit"
        else if (not(checkCalls(scenario, readback.calls))) "wrong_graph"
        else "inspected"
      )
    }
  }

  pure def verdictAccepted(verdict: str): bool = verdict == "recorded" or verdict == "inspected"
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool = {
    if (rows.length() != 2 or verdicts != List(List("recorded", "inspected"), List("recorded", "inspected"))) false
    else {
      val first = rows[0].attempts[1].calls[0]
      val second = rows[1].attempts[1].calls[0]
      rows[0].scenario == 0 and rows[1].scenario == 1 and
        first.resultNode == second.resultNode and first.dag != second.dag
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
  pure val recorded: Attempt = { op: "record", args: List("7", "5", "3"), code: 0,
    quiet: true, commit: "commit", calls: List(), unchanged: false }
  pure val inspected: Attempt = { ...recorded, op: "inspect", args: List(), calls: List(summed, scaled),
    unchanged: true }
  pure def inspectVerdict(readback: Attempt): str =
    historyVerdicts({ scenario: 0, attempts: List(recorded, readback) })[1]
  pure val controlsPass = all {
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
