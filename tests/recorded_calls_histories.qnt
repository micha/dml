module recorded_calls_histories {
  type Request = { op: str, args: List[str] }
  type Input = (str, int)
  type Scenario = { a: Input, b: Input, factor: Input }

  // The same sum value must not collapse the histories of different calls.
  pure val scenarios: List[Scenario] = List(
    { a: ("7", 7), b: ("5", 5), factor: ("3", 3) },
    { a: ("-2", -2), b: ("14", 14), factor: ("-2", -2) }
  )
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure def worker(op: str, args: List[str]): Request = { op: op, args: List("worker").concat(args) }
  pure def requests(s: Scenario): List[Request] = List(
    source("record", List(s.a._1, s.b._1, s.factor._1)),
    source("inspect", List())
  )

  // In record_scale, the second argument names the prior producer receipt.
  // The adapter substitutes the commit ID returned by that record_sum process.
  pure val splitRequests: List[Request] = List(
    source("record_sum", List("producer", "7", "5")),
    source("record_sum", List("decoy", "8", "4")),
    source("inspect", List("producer")),
    source("inspect", List("decoy")),
    source("record_scale", List("decoy", "producer", "result", "3")),
    source("record_scale", List("missing", "producer", "result", "3")),
    source("record_scale", List("producer", "producer", "result", "4611686018427387904")),
    source("record_scale", List("producer", "producer", "result", "3")),
    source("record_scale", List("decoy", "decoy", "result", "3")),
    source("record_scale", List("decoy", "decoy", "decoy-result", "3")),
    source("inspect", List("result")),
    source("inspect", List("decoy-result"))
  )

  // Expected IDs in export, scale and release refer only to the original
  // record_sum receipts. In particular staging the wrong bundle isn't selection.
  pure val handoffRequests: List[Request] = splitRequests.slice(0, 4).concat(List(
    source("export_sum", List("decoy", "producer", "missing.bundle")),
    source("export_sum", List("producer", "producer", "sum.bundle")),
    source("export_sum", List("decoy", "decoy", "decoy.bundle")),
    source("export_sum", List("decoy", "decoy", "sum.bundle")),
    worker("stage_input", List("other-input", "decoy.bundle")),
    worker("record_scale", List("other-input", "producer", "result", "3")),
    worker("stage_input", List("other-input", "sum.bundle")),
    worker("inspect", List("other-input")),
    worker("stage_input", List("incoming", "sum.bundle")),
    worker("release_input", List("incoming", "producer", "result")),
    worker("inspect", List("incoming")),
    worker("record_scale", List("incoming", "producer", "result", "3")),
    worker("inspect", List("result")),
    worker("release_input", List("other-input", "producer", "result")),
    worker("release_input", List("incoming", "decoy", "result")),
    worker("release_input", List("incoming", "producer", "result")),
    worker("collect", List()),
    worker("inspect", List("incoming")),
    worker("inspect", List("result")),
    worker("inspect", List("main")),
    source("inspect", List("producer"))
  ))

  var histories: List[List[Request]]
  action init = histories' = scenarios.foldl(List(), (out, s) => out.append(requests(s)))
    .append(splitRequests).append(handoffRequests)
  action step = histories' = histories
}
