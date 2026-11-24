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

  var histories: List[List[Request]]
  action init = histories' = scenarios.foldl(List(), (out, s) => out.append(requests(s)))
  action step = histories' = histories
}
