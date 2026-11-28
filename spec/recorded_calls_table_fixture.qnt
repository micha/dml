module recorded_calls_table_fixture {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  pure val v1 = "example.scale@1"
  pure val v2 = "example.scale@2"
  pure val reuse = "reuse-by-default"
  pure val execute = "execute-by-default"
  pure val producer = source("record_sum", List("producer", "7", "5"))
  pure def defineIntent(out: str, impl: str, policy: str): Request =
    source("define_scale_intent", List(out, impl, policy, "legacy-v1", "legacy-v2"))
  pure def defineTable(intent: str, out: str): Request =
    source("define_scale_reuse_table", List(intent, intent, v1, out))
  pure def editTable(basis: str, selection: str, out: str, mode: str): Request =
    source("update_scale_reuse_table", List(basis, basis, selection, selection, out, mode))
  pure def ask(intent: str, plan: str, decision: str, factor: str, table: str, receipt: str, impl: str, override: str): Request =
    source("request_table_scale", List("producer", intent, intent, plan, decision, factor, table, receipt, impl, override))
  pure def inspect(pin: str): Request = source("inspect", List(pin))
  pure def parent(view: str, index: str, id: str): Request =
    coreRequest("object_view_parent", List(view, index, id))

  // Pin the immutable request obtained from the plan's actual native edge so
  // the worker can run in the same repository without a bundle round trip.
  pure def choice(factor: str, plan: str, request: str, requestOperand: str, attempt: str,
                  selection: str, impl: str, uuid: str): List[Request] =
    List(source("request_scale", List("producer", "producer", plan, factor, "--implementation", impl)))
      .concat(openNative("write")).append(refRead(plan, "choice-plan-id"))
      .concat(viewObject("commit", "choice-plan-id", "choice-plan"))
      .concat(List(parent("choice-plan", "0", request), pin(request, request)))
      .concat(closeNative("txn_commit"))
      .concat(List(source("work_scale_attempt", List(request, requestOperand, attempt, uuid)),
        source("select_scale_attempt", List(plan, plan, attempt, attempt, selection))))
}
