module recorded_calls_histories {
  type Request = { op: str, args: List[str] }
  type Input = (str, int)
  type Scenario = { a: Input, b: Input, factor: Input }

  // The same sum value must not collapse the histories of different calls.
  pure val scenarios: List[Scenario] = List(
    { a: ("7", 7), b: ("5", 5), factor: ("3", 3) },
    { a: ("-2", -2), b: ("14", 14), factor: ("-2", -2) }
  )
  pure def requests(s: Scenario): List[Request] = List(
    { op: "record", args: List(s.a._1, s.b._1, s.factor._1) },
    { op: "inspect", args: List() }
  )

  // In record_scale, the second argument names the prior producer receipt.
  // The adapter substitutes the commit ID returned by that record_sum process.
  pure val splitRequests: List[Request] = List(
    { op: "record_sum", args: List("producer", "7", "5") },
    { op: "record_sum", args: List("decoy", "8", "4") },
    { op: "inspect", args: List("producer") },
    { op: "inspect", args: List("decoy") },
    { op: "record_scale", args: List("decoy", "producer", "result", "3") },
    { op: "record_scale", args: List("missing", "producer", "result", "3") },
    { op: "record_scale", args: List("producer", "producer", "result", "4611686018427387904") },
    { op: "record_scale", args: List("producer", "producer", "result", "3") },
    { op: "record_scale", args: List("decoy", "decoy", "result", "3") },
    { op: "record_scale", args: List("decoy", "decoy", "decoy-result", "3") },
    { op: "inspect", args: List("result") },
    { op: "inspect", args: List("decoy-result") }
  )

  var histories: List[List[Request]]
  action init = histories' = scenarios.foldl(List(), (out, s) => out.append(requests(s))).append(splitRequests)
  action step = histories' = histories
}
