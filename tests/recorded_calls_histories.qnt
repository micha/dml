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

  var histories: List[List[Request]]
  action init = histories' = scenarios.foldl(List(), (out, s) => out.append(requests(s)))
    .append(splitRequests).append(handoffRequests).append(returnRequests).append(durableRequests).append(retryRequests)
    .append(abandonRequests).append(reuseRequests).append(reusePublicationRequests).append(versionRequests)
    .append(selectionRequests).append(attemptRequests).append(adoptionRequests).append(policyRequests)
    .append(implementationIntentRequests).append(supersessionRequests)
  action step = histories' = histories
}
