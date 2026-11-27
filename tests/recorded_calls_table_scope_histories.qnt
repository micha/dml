module recorded_calls_table_scope_cases {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_table_fixture as t from "./recorded_calls_table_fixture"

  pure val uuid = "00000000-0000-4000-8000-000000000001"
  pure def setup(intent: str, policy: str, factor: str): List[Request] = List(
    t::producer, t::inspect("producer"), t::defineIntent(intent, t::v1, policy),
    t::defineTable(intent, "empty"), t::inspect("empty"))
    .concat(t::choice(factor, "plan-one", "request-one", "native:request-one", "attempt-one", "selection-one", t::v1, uuid))
    .concat(List(t::inspect("plan-one"), t::inspect("selection-one"),
      t::editTable("empty", "selection-one", "full", "insert"), t::inspect("full")))

  pure def read(reqs: List[Request]): List[Request] =
    openNative("read").concat(reqs).concat(closeNative("txn_abort"))
  pure def afterHit(decision: str): List[Request] = read(List(refRead("main", "selected-result"),
    refRead(decision, "hit-pin"), refRead("unused", "absent-pin")))

  pure def inherit(name: str, implementation: str, basis: str): Request =
    source("define_scale_intent", List(name, implementation, basis, basis))

  // Same definition fields in another lineage, and the wrong version in the
  // right lineage, are distinct grounds to reject the same pinned table.
  pure val lineage = List(t::defineIntent("other", t::v2, t::reuse), inherit("same-fields", t::v1, "other"),
    inherit("promoted", t::v2, "intent"), t::inspect("intent"), t::inspect("other"),
    t::inspect("same-fields"), t::inspect("promoted"),
    t::ask("same-fields", "unused", "decision", "2", "full", "full", "default", "default"),
    t::ask("promoted", "unused", "decision", "2", "full", "full", "default", "default"))
    .concat(read(List(refRead("main", "absent-pin"), refRead("unused", "absent-pin"),
      refRead("decision", "absent-pin"))))
    .concat(List(t::ask("promoted", "unused", "decision", "2", "full", "full", t::v1, "default"),
      t::inspect("decision"))).concat(afterHit("decision"))

  // The default ignores a stale expected table ID; explicit reuse consults a
  // correctly pinned empty table and fails before either output is created.
  pure val defaults = List(
    t::ask("execute", "fresh", "default-execute", "2", "empty", "sum:producer", "default", "default"),
    t::inspect("default-execute"), t::inspect("fresh"),
    t::ask("execute", "unused", "reuse", "2", "empty", "empty", "default", "reuse-selected"))
    .concat(read(List(refRead("main", "absent-pin"), refRead("unused", "absent-pin"), refRead("reuse", "absent-pin"))))
    .concat(List(t::ask("execute", "unused", "reuse", "2", "full", "full", "default", "reuse-selected"),
      t::inspect("reuse"))).concat(afterHit("reuse"))

  pure def decisionPath(ref: str, pinId: str, view: str, parents: (str, str, str)): List[Request] =
    List(refRead(ref, pinId)).concat(viewObject("commit", pinId, view))
      .concat(List(t::parent(view, "0", parents._1), t::parent(view, "1", parents._2), t::parent(view, "2", parents._3)))

  // Preserve the genuine decision tree and first two parents; substitute a
  // well-formed empty table in the third position and commit a new pin.
  pure val forgeWrite = openNative("write").concat(decisionPath("decision", "decision-pin", "decision-view",
      ("decision-plan", "decision-intent", "decision-table")))
    .append(refRead("empty", "empty-id"))
    .concat(putObject("commit", List("decision-view", "decision-plan", "decision-intent", "empty-id"), "forged-id"))
    .append(pin("forged", "forged-id")).concat(closeNative("txn_commit"))
  pure val forgeRead = read(decisionPath("forged", "forged-pin", "forged-view", ("forged-plan", "forged-intent", "forged-table"))
    .concat(viewObject("commit", "decision-plan", "decision-plan-view"))
    .append(t::parent("decision-plan-view", "0", "decision-request")))
  pure val forgery = List(t::ask("intent", "unused", "decision", "3", "full", "full", "default", "default"))
    .concat(forgeWrite).concat(forgeRead).concat(List(t::inspect("forged"), t::inspect("decision")))

  pure val setupLength = 21
  pure val requests = List(setup("intent", t::reuse, "2").concat(lineage),
    setup("execute", t::execute, "2").concat(defaults), setup("intent", t::reuse, "3").concat(forgery))
}

module recorded_calls_table_scope_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_table_scope_cases.requests

  var histories: List[List[Request]]
  action init = histories' = requests
  action step = histories' = histories
}
