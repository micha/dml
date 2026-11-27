module recorded_calls_histories {
  type Request = { op: str, args: List[str] }
  type Input = (str, int)
  type Scenario = { a: Input, b: Input, factor: Input }

  // The same sum value must not collapse the histories of different calls.
  pure val scenarios: List[Scenario] = List(
    { a: ("7", 7), b: ("5", 5), factor: ("3", 3) },
    { a: ("-2", -2), b: ("14", 14), factor: ("-2", -2) }
  )
  pure def coreRequest(op: str, args: List[str]): Request = { op: op, args: args }
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

  // Native steps use the same source repository as the CLI, but no native
  // handle stays open across a CLI invocation.
  pure val rejectionOpen = coreRequest("repo_open", List("source", "existing"))
  pure val rejectionClose = coreRequest("repo_close", List("source"))
  pure def rejectionRead(queries: List[Request]): List[Request] = List(
    rejectionOpen, coreRequest("txn_begin", List("source", "read", "read"))
  ).concat(queries).concat(List(coreRequest("txn_abort", List("read")), rejectionClose))
  pure def rejectionRef(ref: str): Request = coreRequest("txn_ref_get", List("read", ref, ref))
  pure val rejectionDatum = coreRequest("txn_get_datum", List("read", "candidate", "stored"))
  pure def rejectionProbe(value: str): List[Request] = List(
    rejectionOpen,
    coreRequest("datum_encode", List("i64", value, "packed")),
    coreRequest("txn_begin", List("source", "write", "probe")),
    coreRequest("txn_put_datum", List("probe", "packed", "candidate")),
    coreRequest("txn_abort", List("probe")),
    rejectionClose
  )

  pure val rejectionPins = rejectionRead(List(
    rejectionRef("producer"), rejectionRef("decoy"), rejectionRef("missing"), rejectionRef("main")
  ))
  pure val pinRejectionRequests: List[Request] = List(
    source("record_sum", List("producer", "7", "5")),
    source("record_sum", List("decoy", "9", "3"))
  ).concat(rejectionPins).concat(List(
    source("record_scale", List("decoy", "producer", "main", "3")),
    source("record_scale", List("missing", "producer", "main", "3"))
  )).concat(rejectionPins)

  pure val writeRejectionCases = List(
    (source("record_sum", List("producer", "43", "77")), "43"),
    (source("record_scale", List("producer", "producer", "producer", "41")), "41"),
    (source("record_scale", List("producer", "producer", "main", "17")), "17"),
    (source("record_scale", List("producer", "producer", "overflow", "4611686018427387904")), "4611686018427387904")
  )
  pure val writeRejectionReads = rejectionRead(List(
    rejectionRef("producer"), rejectionRef("main"), rejectionRef("overflow"), rejectionDatum
  ))
  pure val writeRejectionRequests: List[Request] = writeRejectionCases.foldl(List(
    source("record_sum", List("producer", "7", "5")),
    source("record_scale", List("producer", "producer", "main", "3"))
  ), (out, c) => out.concat(rejectionProbe(c._2)).append(c._1).concat(writeRejectionReads))

  pure val rangeRejectionRequests = List(source("record", List("9223372036854775808", "0", "1")))
  pure val overflowReads = rejectionRead(List(rejectionRef("main"), rejectionDatum))
  pure def overflowRequests(a: str, b: str, factor: str, candidate: str): List[Request] =
    List(source("record", List(a, b, factor))).concat(rejectionProbe(candidate)).concat(overflowReads)
  pure val mainReads = rejectionRead(List(rejectionRef("main")))
  pure val repeatRejectionRequests = List(source("record", List("2", "3", "6")))
    .concat(mainReads).append(source("record", List("13", "17", "41"))).concat(mainReads)

  pure val rejectionRequests: List[List[Request]] = List(
    pinRejectionRequests, writeRejectionRequests, rangeRejectionRequests,
    overflowRequests("9223372036854775807", "1", "1", "9223372036854775807"),
    overflowRequests("-9223372036854775807", "-1", "-1", "-9223372036854775808"),
    repeatRejectionRequests
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

  // Retain a local result once; neither later plan dispatches work or uses a
  // bundle. A parallel plan becomes stale, while a fresh plan can use the same
  // portable request against the new main.
  pure val reuseRequests: List[Request] = retryRequests.slice(0, 7).concat(List(
    source("stage_input", List("saved-result", "result.bundle")),
    source("inspect", List("saved-result")),
    source("request_scale", List("producer", "producer", "parallel", "3")),
    source("request_scale", List("producer", "producer", "wrong-plan", "-2")),
    source("stage_reused_scale", List("wrong-plan", "plan", "saved-result", "result", "returned")),
    source("stage_reused_scale", List("plan", "plan", "producer", "result", "returned")),
    source("stage_reused_scale", List("wrong-plan", "wrong-plan", "saved-result", "result", "returned")),
    source("stage_reused_scale", List("plan", "plan", "saved-result", "result", "returned")),
    source("stage_reused_scale", List("plan", "plan", "saved-result", "result", "returned")),
    source("publish_requested_scale", List("plan", "plan", "returned", "result", "ack")),
    source("inspect", List("returned")),
    source("inspect", List("plan")),
    source("stage_reused_scale", List("parallel", "parallel", "saved-result", "result", "stalled")),
    source("publish_requested_scale", List("parallel", "parallel", "stalled", "result")),
    source("abandon_scale_request", List("parallel", "parallel")),
    source("stage_reused_scale", List("parallel", "parallel", "saved-result", "result", "late")),
    source("publish_requested_scale", List("parallel", "parallel", "stalled", "result")),
    source("inspect", List("stalled")),
    source("request_scale", List("producer", "producer", "next-plan", "3")),
    source("stage_reused_scale", List("next-plan", "next-plan", "saved-result", "result", "returned")),
    source("publish_requested_scale", List("next-plan", "next-plan", "returned", "result")),
    source("inspect", List("saved-result")),
    source("inspect", List()),
    source("inspect", List("ack"))
  ))

  // Ordinary publication and recorded reuse select the same result ID. Only
  // the latter leaves a reuse record. No work or transfer follows publication.
  pure val reusePublicationRequests: List[Request] = retryRequests.slice(0, 7).concat(List(
    source("stage_input", List("saved-result", "result.bundle")),
    source("stage_input", List("returned", "result.bundle")),
    source("request_scale", List("producer", "producer", "parallel", "3")),
    source("publish_requested_scale", List("plan", "plan", "returned", "result", "ack")),
    source("inspect", List()),
    source("inspect", List("reuse-proof")),
    source("publish_reused_scale", List("parallel", "parallel", "saved-result", "result", "reuse-proof")),
    source("inspect", List("reuse-proof")),
    source("abandon_scale_request", List("parallel", "parallel")),
    source("publish_reused_scale", List("parallel", "parallel", "saved-result", "result", "reuse-proof")),
    source("request_scale", List("producer", "producer", "next-plan", "3")),
    source("publish_reused_scale", List("next-plan", "next-plan", "saved-result", "result", "reuse-proof")),
    source("inspect", List("reuse-proof")),
    source("inspect", List()),
    source("inspect", List("saved-result")),
    source("inspect", List("next-plan")),
    source("inspect", List("ack"))
  ))

  // The producer, factor, and output are identical; only the saved implementation
  // differs. The rejected commands carry exact pins, including the wrong result.
  pure val versionRequests: List[Request] = List(
    source("record_sum", List("producer", "7", "5")),
    source("inspect", List("producer")),
    source("request_scale", List("producer", "producer", "v1", "3")),
    source("request_scale", List("producer", "producer", "explicit-v1", "3", "--implementation", "example.scale@1")),
    source("request_scale", List("producer", "producer", "v2", "3", "--implementation", "example.scale@2")),
    source("request_scale", List("producer", "producer", "v3", "3", "--implementation", "example.scale@3")),
    source("export_request", List("v1", "v1", "v1-request.bundle")),
    source("export_request", List("v2", "v2", "v2-request.bundle")),
    source("inspect", List("v2")),
    worker("stage_input", List("v1-in", "v1-request.bundle")),
    worker("work_scale", List("v1-in", "v1", "v1-result")),
    worker("stage_input", List("v2-in", "v2-request.bundle")),
    worker("work_scale", List("v2-in", "v2", "v2-result")),
    worker("inspect", List("v1-result")),
    worker("inspect", List("v2-result")),
    worker("export_scale", List("v1-result", "v1-result", "v1-result.bundle")),
    worker("export_scale", List("v2-result", "v2-result", "v2-result.bundle")),
    source("stage_input", List("older", "v1-result.bundle")),
    source("stage_input", List("saved", "v2-result.bundle")),
    source("publish_requested_scale", List("v2", "v2", "older", "v1-result", "ack")),
    source("stage_reused_scale", List("v2", "v2", "older", "v1-result", "returned")),
    source("publish_reused_scale", List("v2", "v2", "older", "v1-result", "proof")),
    source("stage_reused_scale", List("v2", "v2", "saved", "v2-result", "returned")),
    source("publish_requested_scale", List("v2", "v2", "returned", "v2-result", "ack")),
    source("request_scale", List("producer", "producer", "next", "3", "--implementation", "example.scale@2")),
    source("publish_reused_scale", List("next", "next", "saved", "v2-result", "proof")),
    source("inspect", List()),
    source("inspect", List("proof")),
    source("inspect", List("saved"))
  )

  // Select against exact pins, including a plan whose saved main is stale.
  // Consume the origin plan and result pin, replace main, and collect before
  // publishing with a fresh plan. The old result ref can even name the proof.
  pure val selectionRequests: List[Request] = versionRequests.slice(0, 19).concat(List(
    source("select_scale_result", List("v2", "v2", "older", "v1-result", "chosen-v2")),
    source("select_scale_result", List("v2", "v2", "saved", "v1-result", "chosen-v2")),
    source("select_scale_result", List("v2", "v2", "saved", "v2-result", "chosen-v2")),
    source("select_scale_result", List("v2", "v2", "saved", "v2-result", "chosen-v2")),
    source("inspect", List("chosen-v2")),
    source("inspect", List()),
    source("inspect", List("v2")),
    source("inspect", List("saved")),
    source("select_scale_result", List("v1", "v1", "older", "v1-result", "chosen-v1")),
    source("publish_selected_scale", List("v2", "v2", "chosen-v1", "chosen-v1", "proof")),
    source("publish_requested_scale", List("v1", "v1", "older", "v1-result")),
    source("stage_input", List("also-saved", "v2-result.bundle")),
    source("select_scale_result", List("v2", "v2", "also-saved", "v2-result", "stale-main-choice")),
    source("publish_selected_scale", List("v2", "v2", "chosen-v2", "chosen-v2", "proof")),
    source("inspect", List("proof")),
    source("abandon_scale_request", List("v2", "v2")),
    source("request_scale", List("producer", "producer", "v2-bridge", "3", "--implementation", "example.scale@2")),
    source("select_scale_result", List("v2-bridge", "v2", "saved", "v2-result", "stale-plan-choice")),
    source("publish_requested_scale", List("v2-bridge", "v2-bridge", "also-saved", "v2-result")),
    source("request_scale", List("producer", "producer", "v2-current", "3", "--implementation", "example.scale@2")),
    source("publish_requested_scale", List("v2-current", "v2-current", "saved", "v2-result")),
    source("inspect", List("saved")),
    source("request_scale", List("producer", "producer", "v1-bridge", "3")),
    source("stage_input", List("older", "v1-result.bundle")),
    source("publish_requested_scale", List("v1-bridge", "v1-bridge", "older", "v1-result")),
    source("collect", List()),
    source("inspect", List("chosen-v2")),
    source("request_scale", List("producer", "producer", "fresh-v2", "3", "--implementation", "example.scale@2")),
    // Same request and result as chosen-v2, but a different selection ID.
    source("publish_selected_scale", List("fresh-v2", "fresh-v2", "stale-main-choice", "chosen-v2", "saved")),
    source("publish_selected_scale", List("fresh-v2", "fresh-v2", "chosen-v2", "chosen-v2", "chosen-v1")),
    source("publish_selected_scale", List("fresh-v2", "fresh-v2", "chosen-v2", "chosen-v2", "saved")),
    source("inspect", List("saved")),
    source("inspect", List()),
    source("inspect", List("chosen-v2")),
    source("inspect", List("chosen-v1")),
    source("inspect", List("fresh-v2")),
    source("publish_selected_scale", List("fresh-v2", "fresh-v2", "chosen-v2", "chosen-v2", "saved"))
  ))

  pure val occurrenceA = "00000000-0000-4000-8000-000000000001"
  pure val occurrenceB = "00000000-0000-4000-8000-000000000002"
  pure val occurrenceC = "00000000-0000-4000-8000-000000000003"

  // Two independent worker invocations retain the same deterministic result.
  // Recreate staging and selection refs with the other occurrence. Earlier
  // receipts still select their immutable IDs, not the new ref targets.
  pure val attemptRequests: List[Request] = List(
    source("record_sum", List("producer", "7", "5")),
    source("inspect", List("producer")),
    source("request_scale", List("producer", "producer", "plan", "3", "--implementation", "example.scale@2")),
    source("export_request", List("plan", "plan", "request.bundle")),
    worker("stage_input", List("incoming", "request.bundle")),
    worker("work_scale", List("incoming", "plan", "legacy-result")),
    worker("work_scale_attempt", List("incoming", "plan", "attempt-a", occurrenceA)),
    worker("work_scale_attempt", List("incoming", "plan", "attempt-b", occurrenceB)),
    worker("work_scale_attempt", List("incoming", "plan", "attempt-a", occurrenceA)),
    worker("inspect", List("attempt-a")),
    worker("inspect", List("attempt-b")),
    worker("export_scale_attempt", List("attempt-a", "attempt-a", "a.bundle")),
    worker("export_scale_attempt", List("attempt-b", "attempt-b", "b.bundle")),
    source("stage_input", List("returned", "a.bundle")),
    source("select_scale_attempt", List("plan", "plan", "returned", "attempt-a", "chosen", "first-choice")),
    source("select_scale_attempt", List("plan", "plan", "returned", "attempt-a", "chosen")),
    source("drop_ref", List("returned", "attempt", "attempt-a")),
    source("stage_input", List("returned", "b.bundle")),
    source("select_scale_attempt", List("plan", "plan", "returned", "attempt-a", "would-choose")),
    source("drop_ref", List("chosen", "selection", "first-choice")),
    source("select_scale_attempt", List("plan", "plan", "returned", "attempt-b", "chosen", "second-choice")),
    source("publish_selected_scale", List("plan", "plan", "chosen", "first-choice", "reuse")),
    source("drop_ref", List("returned", "attempt", "attempt-b")),
    source("collect", List()),
    source("inspect", List("chosen")),
    source("request_scale", List("producer", "producer", "parallel", "3", "--implementation", "example.scale@2")),
    source("publish_selected_scale", List("plan", "plan", "chosen", "second-choice", "reuse")),
    source("publish_selected_scale", List("parallel", "parallel", "chosen", "second-choice", "another-reuse")),
    source("inspect", List()),
    source("inspect", List("reuse")),
    source("inspect", List("chosen")),
    source("inspect", List("plan")),
    source("inspect", List("returned"))
  )

  // Execute twice more after the original choice, then adopt on sibling refs.
  // A reversion to the exact first attempt is still a different selection.
  pure val adoptionRequests: List[Request] = attemptRequests.slice(0, 7).concat(List(
    worker("export_scale_attempt", List("attempt-a", "attempt-a", "a.bundle")),
    source("stage_input", List("returned-a", "a.bundle")),
    source("select_scale_attempt", List("plan", "plan", "returned-a", "attempt-a", "base")),
    source("inspect", List("base")),
    worker("work_scale_attempt", List("incoming", "plan", "attempt-b", occurrenceB)),
    worker("work_scale_attempt", List("incoming", "plan", "attempt-c", occurrenceC)),
    worker("inspect", List("attempt-b")),
    worker("inspect", List("attempt-c")),
    worker("export_scale_attempt", List("attempt-b", "attempt-b", "b.bundle")),
    worker("export_scale_attempt", List("attempt-c", "attempt-c", "c.bundle")),
    source("stage_input", List("returned-b", "b.bundle")),
    source("stage_input", List("returned-c", "c.bundle")),
    source("inspect", List("base")),
    source("adopt_scale_attempt", List("base", "base", "returned-a", "attempt-a", "left")),
    source("adopt_scale_attempt", List("base", "base", "returned-b", "attempt-c", "left")),
    source("adopt_scale_attempt", List("base", "base", "returned-b", "attempt-b", "left")),
    source("adopt_scale_attempt", List("left", "base", "returned-c", "attempt-c", "right")),
    source("adopt_scale_attempt", List("base", "base", "returned-b", "attempt-b", "left")),
    source("adopt_scale_attempt", List("base", "base", "returned-c", "attempt-c", "right")),
    source("adopt_scale_attempt", List("left", "left", "returned-a", "attempt-a", "reverted")),
    source("inspect", List("left")),
    source("inspect", List("right")),
    source("inspect", List("reverted")),
    source("inspect", List()),
    source("drop_ref", List("returned-a", "attempt", "attempt-a")),
    source("drop_ref", List("returned-b", "attempt", "attempt-b")),
    source("drop_ref", List("returned-c", "attempt", "attempt-c")),
    source("collect", List()),
    source("publish_selected_scale", List("plan", "plan", "reverted", "base", "old-reuse")),
    source("publish_selected_scale", List("plan", "plan", "base", "base", "old-reuse")),
    source("inspect", List("old-reuse")),
    source("request_scale", List("producer", "producer", "left-plan", "3", "--implementation", "example.scale@2")),
    source("publish_selected_scale", List("left-plan", "left-plan", "left", "left", "left-reuse")),
    source("inspect", List("left-reuse")),
    source("request_scale", List("producer", "producer", "right-plan", "3", "--implementation", "example.scale@2")),
    source("publish_selected_scale", List("right-plan", "right-plan", "right", "right", "right-reuse")),
    source("inspect", List("right-reuse")),
    source("inspect", List("old-reuse")),
    source("inspect", List()),
    source("inspect", List("base"))
  ))

  // Revert to the same attempt via a new immutable choice, then exercise
  // intent on both the stale and exact versions of that choice.
  pure def intent(policy: str, receipt: str, plan: str, decision: str, override: str, slot: List[str]): Request =
    source("request_policy_scale", List("producer", "producer", policy, receipt, plan, decision, "3", override)
      .concat(slot))

  pure val policyRequests: List[Request] = attemptRequests.slice(0, 8).concat(List(
    worker("export_scale_attempt", List("attempt-a", "attempt-a", "a.bundle")),
    worker("export_scale_attempt", List("attempt-b", "attempt-b", "b.bundle")),
    source("stage_input", List("returned-a", "a.bundle")),
    source("stage_input", List("returned-b", "b.bundle")),
    source("select_scale_attempt", List("plan", "plan", "returned-a", "attempt-a", "base")),
    source("adopt_scale_attempt", List("base", "base", "returned-b", "attempt-b", "alternate")),
    source("adopt_scale_attempt", List("alternate", "alternate", "returned-a", "attempt-a", "active")),
    source("define_scale_policy", List("old-policy", "reuse-by-default")),
    source("define_scale_policy", List("reuse-policy", "reuse-by-default", "old-policy", "old-policy")),
    source("define_scale_policy", List("execute-policy", "execute-by-default", "reuse-policy", "reuse-policy")),
    source("inspect", List("execute-policy")),
    intent("reuse-policy", "old-policy", "no-plan", "reuse-decision", "default", List("active", "active")),
    intent("reuse-policy", "reuse-policy", "no-plan", "reuse-decision", "default", List("active")),
    intent("reuse-policy", "reuse-policy", "no-plan", "reuse-decision", "default", List("empty", "active")),
    intent("reuse-policy", "reuse-policy", "no-plan", "reuse-decision", "default", List("active", "base")),
    intent("reuse-policy", "reuse-policy", "no-plan", "reuse-decision", "default", List()),
    intent("reuse-policy", "reuse-policy", "no-plan", "reuse-decision", "reuse-selected", List("empty")),
    intent("reuse-policy", "reuse-policy", "plan", "reuse-decision", "default", List("active", "active")),
    intent("reuse-policy", "reuse-policy", "no-plan", "reuse-decision", "default", List("active", "active")),
    source("inspect", List("reuse-decision")),
    source("inspect", List("no-plan")),
    source("inspect", List()),
    intent("reuse-policy", "reuse-policy", "no-plan", "reuse-decision", "default", List("active", "active")),
    intent("reuse-policy", "reuse-policy", "rolled-back", "reuse-decision", "fresh", List("active", "base")),
    source("inspect", List("rolled-back")),
    intent("reuse-policy", "reuse-policy", "forced-plan", "forced-decision", "fresh", List("active", "base")),
    source("inspect", List("forced-decision")),
    source("inspect", List("forced-plan")),
    intent("execute-policy", "execute-policy", "default-plan", "execution-decision", "default", List("active", "base")),
    source("inspect", List("execution-decision")),
    intent("execute-policy", "execute-policy", "no-plan", "override-decision", "reuse-selected", List("active", "active")),
    source("inspect", List("override-decision")),
    intent("reuse-policy", "reuse-policy", "fallback-plan", "fallback-decision", "default", List("empty")),
    source("inspect", List("fallback-decision")),
    source("export_request", List("fallback-plan", "fallback-plan", "fallback.bundle")),
    worker("work_scale", List("incoming", "fallback-plan", "fallback-result")),
    source("drop_ref", List("reuse-policy", "policy", "reuse-policy")),
    source("drop_ref", List("old-policy", "policy", "old-policy")),
    source("drop_ref", List("execute-policy", "policy", "execute-policy")),
    source("drop_ref", List("base", "selection", "base")),
    source("drop_ref", List("alternate", "selection", "alternate")),
    source("drop_ref", List("active", "selection", "active")),
    source("drop_ref", List("returned-a", "attempt", "attempt-a")),
    source("drop_ref", List("returned-b", "attempt", "attempt-b")),
    source("collect", List()),
    source("inspect", List("reuse-decision")),
    source("inspect", List("fallback-decision"))
  ))

  pure def implementationIntent(definition: str, receipt: str, plan: str, decision: str,
                               implementation: str, override: str, selection: str): Request =
    source("request_intent_scale", List("producer", "producer", definition, receipt, plan, decision, "3",
      implementation, override, selection))

  // Fork the default from one basis, but keep both separately declared slots.
  // Both versions compute 36 with the same inputs; the requests are not interchangeable.
  pure val implementationIntentRequests: List[Request] = attemptRequests.slice(0, 2).concat(List(
    source("define_scale_intent", List("basis", "example.scale@1", "reuse-by-default", "chosen-a", "chosen-b")),
    source("define_scale_intent", List("left", "example.scale@1", "basis", "basis")),
    source("define_scale_intent", List("right", "example.scale@2", "basis", "basis")),
    source("inspect", List("left")),
    source("inspect", List("right")),
    implementationIntent("left", "left", "plan-a", "fresh-a", "default", "default", "-"),
    source("inspect", List("fresh-a")),
    source("export_request", List("plan-a", "plan-a", "request-a.bundle")),
    worker("stage_input", List("incoming-a", "request-a.bundle")),
    worker("work_scale_attempt", List("incoming-a", "plan-a", "attempt-a", occurrenceA)),
    worker("export_scale_attempt", List("attempt-a", "attempt-a", "a.bundle")),
    source("stage_input", List("returned-a", "a.bundle")),
    source("select_scale_attempt", List("plan-a", "plan-a", "returned-a", "attempt-a", "chosen-a")),
    source("select_scale_attempt", List("plan-a", "plan-a", "returned-a", "attempt-a", "chosen-b", "foreign")),
    implementationIntent("right", "right", "no-b-plan", "reuse-b", "default", "default", "foreign"),
    implementationIntent("right", "right", "no-a-plan", "reuse-a", "example.scale@1", "default", "-"),
    implementationIntent("right", "right", "no-a-plan", "reuse-a", "example.scale@1", "default", "chosen-a"),
    source("inspect", List("reuse-a")),
    source("inspect", List()),
    implementationIntent("left", "basis", "plan-b", "fresh-b", "default", "default", "chosen-a"),
    implementationIntent("right", "right", "plan-b", "fresh-b", "typo", "fresh", "-"),
    source("drop_ref", List("chosen-b", "selection", "foreign")),
    implementationIntent("right", "right", "plan-b", "fresh-b", "default", "default", "-"),
    source("inspect", List("fresh-b")),
    source("export_request", List("plan-b", "plan-b", "request-b.bundle")),
    worker("stage_input", List("incoming-b", "request-b.bundle")),
    worker("work_scale_attempt", List("incoming-b", "plan-b", "attempt-b", occurrenceB)),
    worker("export_scale_attempt", List("attempt-b", "attempt-b", "b.bundle")),
    source("stage_input", List("returned-b", "b.bundle")),
    implementationIntent("right", "right", "no-b-plan", "reuse-b", "default", "reuse-selected", "-"),
    source("select_scale_attempt", List("plan-b", "plan-b", "returned-b", "attempt-b", "chosen-b")),
    implementationIntent("right", "right", "no-b-plan", "reuse-b", "default", "default", "foreign"),
    implementationIntent("right", "right", "no-b-plan", "reuse-a", "default", "default", "chosen-b"),
    implementationIntent("right", "right", "no-b-plan", "reuse-b", "default", "default", "chosen-b"),
    source("inspect", List("reuse-b")),
    source("inspect", List()),
    implementationIntent("left", "left", "no-a-plan", "left-a", "default", "default", "chosen-a"),
    source("inspect", List("left-a")),
    source("drop_ref", List("left", "intent", "left")),
    source("drop_ref", List("right", "intent", "right")),
    source("drop_ref", List("basis", "intent", "basis")),
    source("drop_ref", List("chosen-a", "selection", "chosen-a")),
    source("drop_ref", List("chosen-b", "selection", "chosen-b")),
    source("drop_ref", List("returned-a", "attempt", "attempt-a")),
    source("drop_ref", List("returned-b", "attempt", "attempt-b")),
    source("collect", List()),
    source("inspect", List("reuse-a")),
    source("inspect", List("reuse-b")),
    source("inspect", List("fresh-b")),
    source("inspect", List("no-a-plan")),
    source("inspect", List("no-b-plan")),
    source("inspect", List())
  ))

  pure def declareSupersession(basis: str, receipt: str, output: str, evidence: str): Request =
    source("declare_scale_supersession", List(basis, receipt, output, "example.scale@1", "example.scale@2",
      "operational-replacement", "audit", evidence))

  // Keep every definition available. A declaration does not choose v2;
  // promotion is a separate write and uses the already declared v2 slot.
  pure val advisoryRequests: List[Request] = List(
    implementationIntent("left", "left", "no-a-plan", "before-decision", "default", "default", "chosen-a"),
    source("inspect", List()),
    source("inspect", List("before-decision")),
    source("record_sum", List("audit", "8", "4")),
    declareSupersession("left", "basis", "assertion", "audit"),
    declareSupersession("left", "left", "assertion", "producer"),
    declareSupersession("left", "left", "right", "audit"),
    declareSupersession("left", "left", "assertion", "audit"),
    source("inspect", List("assertion")),
    declareSupersession("assertion", "assertion", "stacked", "audit"),
    source("inspect", List("before-decision")),
    source("inspect", List("before-decision", "assertion")),
    implementationIntent("assertion", "assertion", "no-a-plan", "annotated-decision", "default", "default", "chosen-a"),
    source("inspect", List("annotated-decision", "right")),
    source("define_scale_intent", List("promoted", "example.scale@2", "assertion", "assertion")),
    source("inspect", List("promoted")),
    implementationIntent("promoted", "promoted", "plan-b", "default-b", "default", "default", "chosen-a"),
    implementationIntent("promoted", "promoted", "plan-b", "default-b", "default", "default", "-"),
    source("inspect", List("default-b")),
    implementationIntent("promoted", "promoted", "forced-plan", "forced-b", "default", "fresh", "-"),
    source("inspect", List("forced-b", "left")),
    source("export_request", List("plan-b", "plan-b", "request-b.bundle")),
    worker("stage_input", List("incoming-b", "request-b.bundle")),
    worker("work_scale_attempt", List("incoming-b", "plan-b", "attempt-b", occurrenceB)),
    worker("export_scale_attempt", List("attempt-b", "attempt-b", "b.bundle")),
    source("stage_input", List("returned-b", "b.bundle")),
    source("select_scale_attempt", List("plan-b", "plan-b", "returned-b", "attempt-b", "chosen-b")),
    implementationIntent("promoted", "promoted", "no-b-plan", "reuse-b", "default", "default", "chosen-b"),
    source("inspect", List()),
    source("inspect", List("reuse-b")),
    implementationIntent("left", "left", "no-a-plan", "retained-a", "default", "default", "chosen-a"),
    source("inspect", List("retained-a", "promoted")),
    implementationIntent("promoted", "promoted", "no-a-plan", "explicit-a", "example.scale@1", "default", "chosen-a"),
    source("inspect", List("explicit-a"))
  )
  pure val implementationIntentSetupLength = 15
  pure val supersessionRequests = implementationIntentRequests.slice(0, implementationIntentSetupLength)
    .concat(advisoryRequests)

  pure def tableRequest(producer: str, intent: str, plan: str, decision: str, table: str, receipt: str,
                        implementation: str, override: str): Request =
    source("request_table_scale", List(producer, intent, intent, plan, decision, "3", table, receipt,
      implementation, override))

  pure def fromTable(producer: str, plan: str, decision: str, table: str): Request =
    tableRequest(producer, "left", plan, decision, table, table, "default", "default")

  pure def editTable(basis: str, selection: str, output: str, mode: str): Request =
    source("update_scale_reuse_table", List(basis, basis, selection, selection, output, mode))

  // A and B have different producer DAGs and the same stored scalar (12).
  pure val tableBuildRequests: List[Request] = List(
    worker("inspect", List("attempt-a")),
    source("record_sum", List("decoy", "8", "4")),
    source("inspect", List("decoy")),
    source("define_scale_reuse_table", List("left", "left", "example.scale@1", "empty")),
    source("inspect", List("empty")),
    editTable("empty", "chosen-a", "table-a", "insert"),
    fromTable("decoy", "table-plan-b", "miss-b", "table-a"),
    source("inspect", List("miss-b")),
    source("export_request", List("table-plan-b", "table-plan-b", "request-b.bundle")),
    worker("stage_input", List("incoming-b", "request-b.bundle")),
    worker("work_scale_attempt", List("incoming-b", "table-plan-b", "attempt-b", occurrenceB)),
    worker("inspect", List("attempt-b")),
    worker("export_scale_attempt", List("attempt-b", "attempt-b", "b.bundle")),
    source("stage_input", List("returned-b", "b.bundle")),
    source("select_scale_attempt", List("table-plan-b", "table-plan-b", "returned-b", "attempt-b", "second-choice")),
    editTable("table-a", "second-choice", "table-ab", "insert"),
    source("inspect", List("table-ab"))
  )

  pure val tableRoutingRequests: List[Request] = List(
    tableRequest("producer", "right", "unused", "wrong-version", "table-ab", "table-ab", "default", "default"),
    tableRequest("producer", "right", "unused", "hit-a", "table-ab", "table-ab", "example.scale@1", "default"),
    source("inspect", List("hit-a")),
    source("inspect", List()),
    fromTable("decoy", "unused", "hit-b", "table-ab"),
    source("inspect", List("hit-b")),
    source("inspect", List()),
    tableRequest("producer", "left", "unused", "blocked", "table-ab", "table-a", "default", "default"),
    tableRequest("producer", "left", "unused", "blocked", "table-ab", "-", "default", "default"),
    tableRequest("decoy", "left", "unused", "blocked", "table-a", "table-a", "default", "reuse-selected"),
    tableRequest("producer", "left", "unused", "blocked", "decoy", "sum:decoy", "default", "default"),
    tableRequest("producer", "left", "forced-plan", "forced-a", "decoy", "sum:decoy", "default", "fresh"),
    source("inspect", List("forced-a")),
    source("export_request", List("forced-plan", "forced-plan", "fresh-a.bundle")),
    worker("work_scale_attempt", List("incoming-a", "forced-plan", "attempt-c", occurrenceC)),
    worker("inspect", List("attempt-c")),
    worker("export_scale_attempt", List("attempt-c", "attempt-c", "c.bundle")),
    source("stage_input", List("returned-c", "c.bundle")),
    source("select_scale_attempt", List("forced-plan", "forced-plan", "returned-c", "attempt-c", "replacement")),
    editTable("table-a", "second-choice", "table-next", "adopt"),
    editTable("table-ab", "chosen-a", "table-next", "adopt"),
    editTable("table-ab", "replacement", "empty", "adopt"),
    editTable("table-ab", "replacement", "table-next", "adopt"),
    source("inspect", List("table-next")),
    tableRequest("producer", "left", "unused", "adopted-a", "table-next", "table-next", "default", "reuse-selected"),
    source("inspect", List("adopted-a")),
    fromTable("decoy", "unused", "retained-b", "table-next"),
    source("inspect", List("retained-b")),
    fromTable("producer", "unused", "hit-a", "table-next"), // occupied decision: cannot partially publish A
    fromTable("producer", "unused", "retained-a", "table-ab"),
    source("inspect", List("retained-a")),
    tableRequest("producer", "left", "absent-plan", "no-table", "uncreated", "-", "default", "default"),
    source("inspect", List("no-table")),
    source("inspect", List("unused"))
  )

  pure val tableOfflineRequests: List[Request] = List(
    source("drop_ref", List("empty", "table", "empty")),
    source("drop_ref", List("table-a", "table", "table-a")),
    source("drop_ref", List("table-ab", "table", "table-ab")),
    source("drop_ref", List("table-next", "table", "table-next")),
    source("drop_ref", List("chosen-a", "selection", "chosen-a")),
    source("drop_ref", List("second-choice", "selection", "second-choice")),
    source("drop_ref", List("replacement", "selection", "replacement")),
    source("drop_ref", List("returned-a", "attempt", "attempt-a")),
    source("drop_ref", List("returned-b", "attempt", "attempt-b")),
    source("drop_ref", List("returned-c", "attempt", "attempt-c")),
    source("drop_ref", List("left", "intent", "left")),
    source("collect", List()),
    source("inspect", List("adopted-a")),
    source("inspect", List("retained-a")),
    source("inspect", List("miss-b")),
    source("replicate_decision", List("retained-a", "offline")),
    { op: "inspect", args: List("replica", "offline") }
  )

  pure val multiInputRequests = implementationIntentRequests.slice(0, implementationIntentSetupLength)
    .concat(tableBuildRequests).concat(tableRoutingRequests).concat(tableOfflineRequests)

  pure def intentTableRequest(producer: str, intent: str, plan: str, decision: str, factor: str,
                              table: str, receipt: str, override: str): Request =
    source("request_intent_table_scale", List(producer, intent, intent, plan, decision, factor, table, receipt,
      "default", override))

  pure def editIntentTable(basis: str, output: str, mode: str, selection: str): Request =
    source("update_scale_intent_reuse_table", List(basis, basis, output, mode, selection, selection))

  pure def removeIntentTableKey(basis: str, output: str): Request =
    source("update_scale_intent_reuse_table", List(basis, basis, output, "remove", "producer", "3"))

  pure def produceIntentTableChoice(plan: str, decision: str, choice: str, occurrence: str, incoming: str,
                                    attempt: str, returned: str, requestBundle: str, attemptBundle: str): List[Request] =
    List(
      source("inspect", List(decision)),
      source("export_request", List(plan, plan, requestBundle)),
      worker("stage_input", List(incoming, requestBundle)),
      worker("work_scale_attempt", List(incoming, plan, attempt, occurrence)),
      worker("inspect", List(attempt)),
      worker("export_scale_attempt", List(attempt, attempt, attemptBundle)),
      source("stage_input", List(returned, attemptBundle)),
      source("select_scale_attempt", List(plan, plan, returned, attempt, choice))
    )

  pure val intentTableSetup = List(
    worker("inspect", List("attempt-a")),
    source("record_sum", List("decoy", "8", "4")),
    source("inspect", List("decoy")),
    source("define_scale_intent_reuse_table", List("left", "left", "empty-intent-table")),
    source("inspect", List("empty-intent-table")),
    editIntentTable("empty-intent-table", "intent-table-a", "insert", "chosen-a"),
    source("define_scale_reuse_table", List("left", "left", "example.scale@1", "legacy-table"))
  )
  // Same scalar on a different producer, then a different signed factor on the original producer.
  pure val intentTableDecoy = List(
    intentTableRequest("decoy", "left", "decoy-plan", "decoy-miss", "3", "intent-table-a", "intent-table-a", "default")
  ).concat(produceIntentTableChoice("decoy-plan", "decoy-miss", "decoy-choice", occurrenceB,
    "incoming-decoy", "attempt-decoy", "returned-decoy", "decoy-request.bundle", "decoy-attempt.bundle"))
    .append(editIntentTable("intent-table-a", "intent-table-ad", "insert", "decoy-choice"))
  pure val intentTableNegative = List(
    intentTableRequest("producer", "right", "negative-plan", "negative-miss", "-3",
      "intent-table-ad", "intent-table-ad", "default")
  ).concat(produceIntentTableChoice("negative-plan", "negative-miss", "negative-choice", occurrenceC,
    "incoming-negative", "attempt-negative", "returned-negative", "negative-request.bundle", "negative-attempt.bundle"))
  .concat(List(
    editIntentTable("intent-table-ad", "intent-table-adn", "insert", "negative-choice"),
    source("inspect", List("intent-table-adn"))
  ))
  pure val replacementOccurrence = "00000000-0000-4000-8000-000000000004"
  pure val intentTableReplacement = List(
    intentTableRequest("producer", "right", "replacement-plan", "forced-fresh", "3", "legacy-table", "legacy-table", "fresh")
  ).concat(produceIntentTableChoice("replacement-plan", "forced-fresh", "chosen-b", replacementOccurrence,
    "incoming-replacement", "attempt-replacement", "returned-replacement", "replacement-request.bundle", "replacement-attempt.bundle"))

  pure def intentTableA(intent: str, plan: str, decision: str, table: str, override: str): Request =
    intentTableRequest("producer", intent, plan, decision, "3", table, table, override)

  pure val intentTableFlow = List(
    source("define_scale_intent", List("unrelated", "example.scale@2", "reuse-by-default", "unrelated-a", "unrelated-b")),
    intentTableA("unrelated", "unused", "bad-intent", "intent-table-adn", "default"),
    intentTableA("left", "unused", "wrong-role", "legacy-table", "default"),
    fromTable("producer", "unused", "wrong-legacy-role", "intent-table-adn"),
    intentTableRequest("producer", "right", "unused", "stale-table", "3", "intent-table-adn", "intent-table-ad", "default"),
    intentTableA("right", "unused", "cross-hit", "intent-table-adn", "default"),
    source("inspect", List("cross-hit")),
    source("inspect", List()),
    source("inspect", List("unused")),
    editIntentTable("intent-table-adn", "duplicate", "insert", "chosen-b"),
    editIntentTable("intent-table-adn", "intent-table-adopted", "adopt", "chosen-b"),
    source("inspect", List("intent-table-adopted")),
    source("inspect", List("intent-table-adn")),
    removeIntentTableKey("intent-table-adopted", "intent-table-a"),
    removeIntentTableKey("intent-table-adopted", "intent-table-removed"),
    source("inspect", List("intent-table-removed")),
    removeIntentTableKey("intent-table-removed", "still-absent"),
    intentTableA("right", "unused", "explicit-miss", "intent-table-removed", "reuse-selected"),
    intentTableA("right", "removal-plan", "removal-miss", "intent-table-removed", "default"),
    source("inspect", List("removal-miss")),
    source("inspect", List("removal-plan")),
    source("inspect", List()),
    intentTableA("left", "unused", "adopted-hit", "intent-table-adopted", "reuse-selected"),
    source("inspect", List("adopted-hit")),
    source("inspect", List()),
    intentTableRequest("decoy", "left", "unused", "retained-decoy", "3", "intent-table-removed", "intent-table-removed", "default"),
    source("inspect", List("retained-decoy")),
    source("inspect", List()),
    intentTableRequest("producer", "right", "unused", "retained-negative", "-3",
      "intent-table-removed", "intent-table-removed", "default"),
    source("inspect", List("retained-negative")),
    source("inspect", List()),
    editIntentTable("intent-table-removed", "intent-table-reselected", "insert", "chosen-a"),
    source("inspect", List("intent-table-reselected")),
    intentTableRequest("producer", "right", "absent-intent-plan", "absent-intent-table", "3", "uncreated", "-", "default"),
    source("inspect", List("absent-intent-table"))
  )

  pure val intentTableOffline = List(
    source("drop_ref", List("intent-table-adn", "table", "intent-table-adn")),
    source("drop_ref", List("intent-table-removed", "table", "intent-table-removed")),
    source("drop_ref", List("chosen-a", "selection", "chosen-a")),
    source("drop_ref", List("chosen-b", "selection", "chosen-b")),
    source("drop_ref", List("returned-a", "attempt", "attempt-a")),
    source("drop_ref", List("returned-replacement", "attempt", "attempt-replacement")),
    source("drop_ref", List("right", "intent", "right")),
    source("collect", List()),
    source("inspect", List("cross-hit")),
    source("inspect", List("removal-miss")),
    source("replicate_decision", List("cross-hit", "offline-hit")),
    { op: "inspect", args: List("replica", "offline-hit") },
    source("replicate_decision", List("removal-miss", "offline-miss")),
    { op: "inspect", args: List("replica", "offline-miss") }
  )

  pure val intentTableRequests = implementationIntentRequests.slice(0, implementationIntentSetupLength)
    .concat(intentTableSetup).concat(intentTableDecoy).concat(intentTableNegative).concat(intentTableReplacement)
    .concat(intentTableFlow).concat(intentTableOffline)

  // One CoreHistory primitive per native step; its aliases carry IDs returned
  // by the native reads, rather than trusting IDs in the CLI JSON.
  pure def openNative(mode: str): List[Request] = List(
    coreRequest("repo_open", List("source", "existing")),
    coreRequest("txn_begin", List("source", mode, "snapshot"))
  )
  pure def closeNative(end: str): List[Request] = List(
    coreRequest(end, List("snapshot")), coreRequest("repo_close", List("source"))
  )
  pure def refRead(ref: str, id: str): Request = coreRequest("txn_ref_get", List("snapshot", ref, id))
  pure def viewObject(kind: str, id: str, view: str): List[Request] = List(
    coreRequest("txn_get_object", List("snapshot", kind, id, view)),
    coreRequest("object_decode", List(view, view))
  )
  type SnapshotPath = { ref: str, commitView: str, treeView: str, dag: str, parent: str }
  pure val mainPath: SnapshotPath = { ref: "main", commitView: "main-commit", treeView: "main-tree",
    dag: "main-dag", parent: "main-parent" }
  pure val alternatePath: SnapshotPath = { ref: "alternate", commitView: "alternate-commit", treeView: "alternate-tree",
    dag: "alternate-dag", parent: "alternate-parent" }
  pure val producerPath: SnapshotPath = { ref: "producer", commitView: "producer-commit", treeView: "producer-tree",
    dag: "producer-dag", parent: "" }
  pure val decoyPath: SnapshotPath = { ref: "decoy", commitView: "decoy-commit", treeView: "decoy-tree",
    dag: "decoy-dag", parent: "" }
  pure def viewSnapshot(path: SnapshotPath, hasParent: bool): List[Request] =
    List(refRead(path.ref, path.ref)).concat(viewObject("commit", path.ref, path.commitView))
      .concat(viewObject("tree", path.commitView, path.treeView))
      .append(coreRequest("object_view_entry", List(path.treeView, "0", path.dag)))
      .concat(if (hasParent) List(coreRequest("object_view_parent", List(path.commitView, "0", path.parent))) else List())
  pure def lookupNode(dag: str, binding: str, node: str): Request =
    coreRequest("txn_lookup_node", List("snapshot", dag, binding, node))
  pure def encodeNode(kind: str, target: str): Request =
    coreRequest("object_encode", List("node", kind, target, "encoded-node"))
  pure def viewSubdag(dag: str, input: str, producer: str): List[Request] =
    List(lookupNode(dag, "input", input)).concat(viewObject("node", input, producer))
      .append(encodeNode("subdag", producer))
  pure def viewLiteral(node: str, target: str): List[Request] =
    viewObject("node", node, target).append(encodeNode("literal", target))
      .append(coreRequest("txn_get_datum", List("snapshot", target, target)))
      .append(coreRequest("datum_decode", List(target)))

  pure val physicalRecord: Scenario = { a: ("-23", -23), b: ("16", 16), factor: ("-3", -3) }
  // Decoded datum kind and payload (signed I64 little-endian or UTF-8).
  type StoredLiteral = { node: str, target: str, kind: int, payload: str }
  pure val combinedLiterals: List[StoredLiteral] = List(
    { node: "sum-implementation", target: "sum-version", kind: 6, payload: "6578616d706c652e73756d4031" },
    { node: "scale-implementation", target: "scale-version", kind: 6, payload: "6578616d706c652e7363616c654031" },
    { node: "sum-a", target: "a-value", kind: 3, payload: "e9ffffffffffffff" },
    { node: "sum-b", target: "b-value", kind: 3, payload: "1000000000000000" },
    { node: "scale-factor", target: "factor-value", kind: 3, payload: "fdffffffffffffff" },
    { node: "sum-root", target: "sum-value", kind: 3, payload: "f9ffffffffffffff" },
    { node: "scale-root", target: "scale-value", kind: 3, payload: "1500000000000000" }
  )
  pure val combinedGraphRequests = List(requests(physicalRecord)[0]).concat(openNative("read"))
    .concat(viewSnapshot(mainPath, false)).concat(viewObject("dag", "main-dag", "scale-root"))
    .concat(viewSubdag("main-dag", "scale-input", "sum-dag")).concat(viewObject("dag", "sum-dag", "sum-root"))
    .concat(List(lookupNode("sum-dag", "implementation", "sum-implementation"),
      lookupNode("main-dag", "implementation", "scale-implementation"), lookupNode("sum-dag", "a", "sum-a"),
      lookupNode("sum-dag", "b", "sum-b"), lookupNode("main-dag", "factor", "scale-factor")))
    .concat(combinedLiterals.foldl(List(), (out, fixture) => out.concat(viewLiteral(fixture.node, fixture.target))))
    .concat(closeNative("txn_abort")).append(requests(physicalRecord)[1])

  pure val splitGraphSetup = List(
    source("record_sum", List("producer", "7", "5")), source("record_sum", List("decoy", "9", "3")),
    source("record_scale", List("producer", "producer", "main", "3")),
    source("record_scale", List("decoy", "decoy", "alternate", "3")), source("inspect", List("producer"))
  ).concat(openNative("read")).concat(viewSnapshot(producerPath, false)).concat(viewSnapshot(decoyPath, false))
    .concat(viewSnapshot(mainPath, true)).concat(viewSnapshot(alternatePath, true))
    .concat(viewObject("dag", "producer-dag", "producer-root")).concat(viewObject("dag", "decoy-dag", "decoy-root"))
    .concat(viewLiteral("producer-root", "producer-value"))
    .concat(viewSubdag("main-dag", "main-input", "main-source-dag"))
    .concat(viewSubdag("alternate-dag", "alternate-input", "alternate-source-dag"))
    .concat(closeNative("txn_abort"))
  pure val splitGraphReads = List(source("inspect", List()), source("inspect", List("alternate")))
  pure val moveProducer = openNative("write").append(
    coreRequest("txn_ref_update", List("snapshot", "producer", "decoy")))
    .concat(closeNative("txn_commit")).concat(openNative("read"))
    .append(refRead("producer", "moved-producer")).concat(closeNative("txn_abort"))
  pure val releaseProducers = openNative("write").concat(List(
    coreRequest("txn_ref_delete_expected", List("snapshot", "producer", "decoy")),
    coreRequest("txn_ref_delete_expected", List("snapshot", "decoy", "decoy"))
  )).concat(closeNative("txn_commit")).concat(openNative("read"))
    .concat(List(refRead("producer", "released-producer"), refRead("decoy", "released-decoy")))
    .concat(closeNative("txn_abort"))
  pure val splitGraphRequests = splitGraphSetup.concat(splitGraphReads).concat(moveProducer)
    .concat(splitGraphReads).concat(releaseProducers).concat(splitGraphReads)
  pure val physicalRequests = List(combinedGraphRequests, splitGraphRequests)

  var histories: List[List[Request]]
  action init = histories' = scenarios.foldl(List(), (out, s) => out.append(requests(s)))
    .append(splitRequests).append(handoffRequests).append(returnRequests).append(durableRequests).append(retryRequests)
    .append(abandonRequests).append(reuseRequests).append(reusePublicationRequests).append(versionRequests)
    .append(selectionRequests).append(attemptRequests).append(adoptionRequests).append(policyRequests)
    .append(implementationIntentRequests).append(supersessionRequests).append(multiInputRequests).append(intentTableRequests)
    .concat(physicalRequests).concat(rejectionRequests)
  action step = histories' = histories
}
