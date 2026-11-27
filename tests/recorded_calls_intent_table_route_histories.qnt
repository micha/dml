module recorded_calls_intent_table_route_cases {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_table_fixture as t from "./recorded_calls_table_fixture"

  type Step = { req: Request, want: str, mark: str }
  pure def step(req: Request, want: str, mark: str): Step = { req: req, want: want, mark: mark }
  pure def write(req: Request, mark: str): Step = step(req, "recorded", mark)
  pure def inspect(pin: str, mark: str): Step = step(t::inspect(pin), "inspected", mark)
  pure def native(reqs: List[Request]): List[Step] = reqs.foldl(List(), (out, req) => out.append(step(req, "native_ok", "")))
  pure def read(steps: List[Step]): List[Step] = native(openNative("read")).concat(steps).concat(native(closeNative("txn_abort")))
  pure def ref(pin: str, alias: str): Step = step(refRead(pin, alias), "native_ok", alias)
  pure def absent(pin: str): Step = step(refRead(pin, "absent"), "native_not_found", "")

  pure val uuid = "00000000-0000-4000-8000-000000000001"
  pure val insert: Request = source("update_scale_intent_reuse_table", List("empty", "empty", "one", "insert", "selection", "selection"))
  pure def remove(out: str): Request = source("update_scale_intent_reuse_table", List("one-live", "one", out, "remove", "producer", "3"))
  pure def ask(out: str, factor: str, table: str): Request = source("request_intent_table_scale",
    List("producer", "intent", "intent", "unused", out, factor, table, "one", t::v2, "default"))

  pure val attemptPath = viewObject("commit", "attempt-pin", "attempt-view")
    .concat(List(t::parent("attempt-view", "0", "attempt-request"), t::parent("attempt-view", "1", "attempt-result")))
  pure def setup(factor: str): List[Step] = List(write(t::producer, "producer"), inspect("producer", "sum"),
    write(t::defineIntent("intent", t::v1, t::reuse), "intent"),
    write(source("define_scale_intent_reuse_table", List("intent", "intent", "empty")), "empty"))
    .concat(t::choice(factor, "old-plan", "old-request", "native:old-request", "attempt", "selection", t::v1, uuid)
      .foldl(List(), (out, req) => out.append(
        if (req.op == "request_scale") write(req, "old-plan")
        else if (req.op == "work_scale_attempt") write(req, "attempt")
        else if (req.op == "select_scale_attempt") step(req, "selected", "selection")
        else if (req.op == "txn_ref_get") step(req, "native_ok", "choice-plan-id")
        else step(req, "native_ok", ""))))
    .concat(read(List(ref("attempt", "attempt-pin")).concat(native(attemptPath))))
    .concat(List(inspect("old-plan", "read-old-plan"), inspect("selection", "read-selection"),
      write(insert, "one"), inspect("one", "read-one")))

  type Parents = { view: str, plan: str, intent: str, table: str }
  pure val decisionPath = { view: "decision-view", plan: "decision-plan", intent: "decision-intent", table: "decision-table" }
  pure val swappedPlan = { view: "swapped-plan-view", plan: "swapped-plan-plan", intent: "swapped-plan-intent", table: "swapped-plan-table" }
  pure val swappedTable = { view: "swapped-table-view", plan: "swapped-table-plan", intent: "swapped-table-intent", table: "swapped-table-table" }
  pure def commitPath(commit: str, p: Parents): List[Request] = viewObject("commit", commit, p.view)
    .concat(List(t::parent(p.view, "0", p.plan), t::parent(p.view, "1", p.intent), t::parent(p.view, "2", p.table)))

  pure val referencePlan = source("request_scale", List("producer", "producer", "v2-plan", "-3", "--implementation", t::v2))
  // Keep the decision tree intact. In each forgery only one of its ordered parents changes.
  pure val forge = native(openNative("write").append(refRead("empty", "empty-pin"))
    .concat(putObject("commit", List("decision-view", "choice-plan-id", "decision-intent", "decision-table"), "bad-plan"))
    .append(pin("bad-plan", "bad-plan"))
    .concat(putObject("commit", List("decision-view", "decision-plan", "decision-intent", "empty-pin"), "bad-table"))
    .append(pin("bad-table", "bad-table")).concat(closeNative("txn_commit")))
  pure val routing = setup("-3").concat(List(write(referencePlan, "v2-plan"),
    write(ask("decision", "-3", "one"), "decision")))
    .concat(read(List(ref("decision", "decision-pin"), ref("v2-plan", "v2-plan-pin"), ref("main", "main-result"), absent("unused"))
      .concat(native(commitPath("decision-pin", decisionPath)
        .concat(viewObject("commit", "v2-plan-pin", "v2-view"))
        .append(t::parent("v2-view", "0", "v2-request"))
        .concat(viewObject("commit", "main-result", "produced-result-view"))
        .append(t::parent("produced-result-view", "0", "result-request"))))))
    .concat(List(inspect("v2-plan", "read-v2-plan"), inspect("decision", "read-decision")))
    .concat(forge)
    .concat(read(List(ref("bad-plan", "bad-plan-pin"), ref("bad-table", "bad-table-pin"))
      .concat(native(commitPath("bad-plan-pin", swappedPlan).concat(commitPath("bad-table-pin", swappedTable))))))
    .concat(List(step(t::inspect("bad-plan"), "rejected", "resolved implementation"),
      step(t::inspect("bad-table"), "rejected", "resolved policy"), inspect("decision", "read-genuine")))

  // A distinct prior main and another table pin keep both failures past the
  // ref-name checks. Each operation is then repeated with a free output.
  pure val rollbackPins = read(List(ref("main", "old-main"), ref("one", "one-pin"), ref("one-live", "one-live-pin"),
    ref("producer", "producer-pin"), ref("intent", "intent-pin"), ref("selection", "selection-pin"), absent("unused")))
  pure val rollback = setup("3")
    .append(write(source("record_scale", List("producer", "producer", "main", "4")), "prior"))
    .concat(native(openNative("write").append(refRead("one", "original-table-pin")).append(pin("one-live", "original-table-pin"))
      .concat(closeNative("txn_commit"))))
    .concat(rollbackPins)
    .append(step(ask("one", "3", "one-live"), "rejected", "occupied decision")).concat(rollbackPins)
    .append(step(remove("one"), "rejected", "occupied edit")).concat(rollbackPins)
    .concat(List(write(ask("decision", "3", "one-live"), "decision"), write(remove("removed"), "removed")))
    .concat(read(List(ref("main", "main-result"), ref("one", "one-pin"), ref("one-live", "one-live-pin"),
      ref("decision", "decision-pin"), ref("removed", "removed-pin"), absent("unused"))
      .concat(native(commitPath("decision-pin", decisionPath).concat(viewObject("commit", "decision-plan", "captured-plan-view"))
        .concat(List(t::parent("captured-plan-view", "0", "captured-request"),
          t::parent("captured-plan-view", "1", "captured-main")))))))
    .concat(List(inspect("decision", "read-after-collision"), inspect("removed", "read-removed"), inspect("one", "read-retained")))

  pure val cases = List(routing, rollback)
  pure val requests = cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (reqs, s) => reqs.append(s.req))))
}

module recorded_calls_intent_table_route_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_intent_table_route_cases.requests

  var histories: List[List[Request]]
  action init = histories' = requests
  action step = histories' = histories
}
