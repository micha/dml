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

  // Result and main expectations name earlier worker record_scale receipts.
  // The expected factor comes from the request, not a receipt. The zero sum
  // makes both scales return the same output even with different factors.
  // '-' is an explicit expectation of no main, not an unspecified tip.
  pure val returnRequests: List[Request] = List(
    source("record_sum", List("producer", "7", "-7")),
    source("record_sum", List("decoy", "8", "-8")),
    source("inspect", List("producer")),
    source("export_sum", List("producer", "producer", "sum.bundle")),
    worker("stage_input", List("incoming", "sum.bundle")),
    worker("record_scale", List("incoming", "producer", "result", "3")),
    worker("record_scale", List("incoming", "producer", "revised", "-2")),
    worker("release_input", List("incoming", "producer", "result")),
    worker("collect", List()),
    worker("inspect", List("result")),
    worker("export_scale", List("result", "revised", "wrong.bundle")),
    worker("export_scale", List("result", "result", "result.bundle")),
    worker("export_scale", List("revised", "revised", "revised.bundle")),
    source("stage_input", List("returned", "result.bundle")),
    source("inspect", List("returned")),
    source("publish_scale", List("returned", "result", "decoy", "3", "-")),
    source("publish_scale", List("returned", "result", "producer", "3", "result")),
    source("publish_scale", List("returned", "result", "producer", "3", "-")),
    source("inspect", List("returned")),
    source("inspect", List()),
    source("stage_input", List("returned", "revised.bundle")),
    source("publish_scale", List("returned", "result", "producer", "3", "result")),
    source("publish_scale", List("returned", "revised", "producer", "-2", "-")),
    source("publish_scale", List("returned", "revised", "producer", "-2", "revised")),
    source("publish_scale", List("returned", "revised", "producer", "3", "result")),
    source("publish_scale", List("returned", "revised", "producer", "-2", "result")),
    source("collect", List()),
    source("inspect", List("returned")),
    source("inspect", List()),
    source("inspect", List("producer")),
    worker("inspect", List("result"))
  )

  // Plan, request, and result operands name earlier receipts of that kind.
  // Each command is a fresh process. Two plans capture absent main; publishing
  // either makes the other stale even with the right result staged.
  pure val durableRequests: List[Request] = List(
    source("record_sum", List("producer", "7", "-7")),
    source("inspect", List("producer")),
    source("request_scale", List("producer", "producer", "plan", "3")),
    source("request_scale", List("producer", "producer", "other-plan", "-2")),
    source("inspect", List("plan")),
    source("export_request", List("plan", "plan", "request.bundle")),
    source("export_request", List("other-plan", "other-plan", "other-request.bundle")),
    worker("stage_input", List("other-input", "other-request.bundle")),
    worker("work_scale", List("other-input", "plan", "result")),
    worker("work_scale", List("other-input", "other-plan", "other-result")),
    worker("stage_input", List("incoming", "request.bundle")),
    worker("work_scale", List("incoming", "plan", "result")),
    worker("inspect", List("result")),
    worker("inspect", List("other-result")),
    worker("export_scale", List("result", "result", "result.bundle")),
    worker("export_scale", List("other-result", "other-result", "other-result.bundle")),
    source("stage_input", List("other-return", "other-result.bundle")),
    source("publish_requested_scale", List("plan", "plan", "other-return", "other-result")),
    source("stage_input", List("returned", "result.bundle")),
    source("publish_requested_scale", List("other-plan", "plan", "returned", "result")),
    source("publish_requested_scale", List("plan", "plan", "other-return", "result")),
    source("inspect", List("returned")),
    source("publish_requested_scale", List("plan", "plan", "returned", "result")),
    source("publish_requested_scale", List("other-plan", "other-plan", "other-return", "other-result")),
    source("collect", List()),
    source("inspect", List()),
    source("inspect", List("plan")),
    source("inspect", List("returned")),
    source("inspect", List("other-plan")),
    source("inspect", List("other-return"))
  )

  // Each repeat is a fresh process. A second valid result supersedes main,
  // then collection and retry leave the newer publication in place.
  pure val retryRequests: List[Request] = List(
    source("record_sum", List("producer", "7", "-7")),
    source("inspect", List("producer")),
    source("request_scale", List("producer", "producer", "plan", "3")),
    source("export_request", List("plan", "plan", "request.bundle")),
    worker("stage_input", List("incoming", "request.bundle")),
    worker("work_scale", List("incoming", "plan", "result")),
    worker("export_scale", List("result", "result", "result.bundle")),
    source("stage_input", List("returned", "result.bundle")),
    source("publish_requested_scale", List("plan", "plan", "returned", "result", "ack")),
    source("publish_requested_scale", List("plan", "plan", "returned", "result", "ack")),
    source("publish_requested_scale", List("plan", "plan", "returned", "result", "missing-ack")),
    source("request_scale", List("producer", "producer", "next-plan", "-2")),
    source("export_request", List("next-plan", "next-plan", "next-request.bundle")),
    worker("stage_input", List("next-input", "next-request.bundle")),
    worker("work_scale", List("next-input", "next-plan", "next-result")),
    worker("export_scale", List("next-result", "next-result", "next-result.bundle")),
    source("stage_input", List("next-returned", "next-result.bundle")),
    source("publish_requested_scale", List("next-plan", "next-plan", "next-returned", "next-result", "ack")),
    source("publish_requested_scale", List("next-plan", "next-plan", "next-returned", "next-result")),
    source("collect", List()),
    source("inspect", List("ack")),
    source("abandon_scale_request", List("plan", "plan")), // Publication already consumed this pin.
    source("publish_requested_scale", List("plan", "plan", "returned", "result", "ack")),
    source("inspect", List()),
    source("inspect", List("plan")),
    source("inspect", List("returned"))
  )

  // Abandon before the result is staged. The old and replacement plan IDs
  // are saved under separate receipt aliases even though they use the same ref.
  pure val abandonRequests: List[Request] = retryRequests.slice(0, 7).concat(List(
    source("abandon_scale_request", List("plan", "plan")),
    source("stage_input", List("returned", "result.bundle")),
    source("publish_requested_scale", List("plan", "plan", "returned", "result", "ack")),
    source("inspect", List()),
    source("inspect", List("ack")),
    source("inspect", List("plan")),
    source("request_scale", List("producer", "producer", "plan", "-2", "replacement")),
    source("abandon_scale_request", List("plan", "plan")),
    source("export_request", List("plan", "replacement", "replacement.bundle")),
    source("inspect", List("plan")),
    source("abandon_scale_request", List("plan", "replacement")),
    source("inspect", List("plan")),
    source("inspect", List("returned"))
  ))

  var histories: List[List[Request]]
  action init = histories' = scenarios.foldl(List(), (out, s) => out.append(requests(s)))
    .append(splitRequests).append(handoffRequests).append(returnRequests).append(durableRequests).append(retryRequests)
    .append(abandonRequests)
  action step = histories' = histories
}
