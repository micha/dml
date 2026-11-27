module recorded_calls_table_capacity_cases {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_table_fixture as t from "./recorded_calls_table_fixture"

  type Step = { req: Request, want: str, detail: str }
  pure def step(req: Request, want: str, detail: str): Step = { req: req, want: want, detail: detail }
  pure def recordStep(req: Request): Step = step(req, "recorded", "")
  pure def inspect(pin: str, detail: str): Step = step(t::inspect(pin), "inspected", detail)
  pure def reject(req: Request, diagnostic: str): Step = step(req, "rejected", diagnostic)
  pure def native(reqs: List[Request]): List[Step] = reqs.foldl(List(), (out, req) => out.append(step(req, "native_ok", "")))
  pure def read(steps: List[Step]): List[Step] = native(openNative("read")).concat(steps).concat(native(closeNative("txn_abort")))
  pure def write(reqs: List[Request]): List[Step] = native(openNative("write").concat(reqs).concat(closeNative("txn_commit")))
  pure def ref(pin: str, alias: str, id: str): Step = step(refRead(pin, alias), "native_ok", id)
  pure def absent(pin: str): Step = step(refRead(pin, "absent"), "native_not_found", "")

  // Plan, request alias, request operand, attempt, selection, result alias, UUID, table pin.
  type Choice = (str, str, str, str, str, str, str, str)
  pure val choices: List[Choice] = List(
    ("plan-01", "request-01", "native:request-01", "attempt-01", "selection-01", "result-01", "00000000-0000-4000-8000-000000000001", "table-01"),
    ("plan-02", "request-02", "native:request-02", "attempt-02", "selection-02", "result-02", "00000000-0000-4000-8000-000000000002", "table-02"),
    ("plan-03", "request-03", "native:request-03", "attempt-03", "selection-03", "result-03", "00000000-0000-4000-8000-000000000003", "table-03"),
    ("plan-04", "request-04", "native:request-04", "attempt-04", "selection-04", "result-04", "00000000-0000-4000-8000-000000000004", "table-04"),
    ("plan-05", "request-05", "native:request-05", "attempt-05", "selection-05", "result-05", "00000000-0000-4000-8000-000000000005", "table-05"),
    ("plan-06", "request-06", "native:request-06", "attempt-06", "selection-06", "result-06", "00000000-0000-4000-8000-000000000006", "table-06"),
    ("plan-07", "request-07", "native:request-07", "attempt-07", "selection-07", "result-07", "00000000-0000-4000-8000-000000000007", "table-07"),
    ("plan-08", "request-08", "native:request-08", "attempt-08", "selection-08", "result-08", "00000000-0000-4000-8000-000000000008", "table-08"),
    ("plan-09", "request-09", "native:request-09", "attempt-09", "selection-09", "result-09", "00000000-0000-4000-8000-000000000009", "table-09"),
    ("plan-10", "request-10", "native:request-10", "attempt-10", "selection-10", "result-10", "00000000-0000-4000-8000-000000000010", "table-10"),
    ("plan-11", "request-11", "native:request-11", "attempt-11", "selection-11", "result-11", "00000000-0000-4000-8000-000000000011", "table-11"),
    ("plan-12", "request-12", "native:request-12", "attempt-12", "selection-12", "result-12", "00000000-0000-4000-8000-000000000012", "table-12"),
    ("plan-13", "request-13", "native:request-13", "attempt-13", "selection-13", "result-13", "00000000-0000-4000-8000-000000000013", "table-13"),
    ("plan-14", "request-14", "native:request-14", "attempt-14", "selection-14", "result-14", "00000000-0000-4000-8000-000000000014", "table-14"),
    ("plan-15", "request-15", "native:request-15", "attempt-15", "selection-15", "result-15", "00000000-0000-4000-8000-000000000015", "table-15"),
    ("plan-16", "request-16", "native:request-16", "attempt-16", "selection-16", "result-16", "00000000-0000-4000-8000-000000000016", "table-16"),
    ("plan-17", "request-17", "native:request-17", "attempt-17", "selection-17", "result-17", "00000000-0000-4000-8000-000000000017", "too-many"),
    ("plan-18", "request-18", "native:request-18", "attempt-18", "selection-18", "result-18", "00000000-0000-4000-8000-000000000018", "adopted"))
  pure def choice(factor: str, c: Choice, impl: str): List[Step] =
    t::choice(factor, c._1, c._2, c._3, c._4, c._5, impl, c._7).foldl(List(), (out, req) => out.append(
      if (req.op == "select_scale_attempt") step(req, "selected", "")
      else if (Set("request_scale", "work_scale_attempt").contains(req.op)) recordStep(req)
      else if (req.op == "txn_ref_get") ref(c._1, "choice-plan-id", c._1)
      else step(req, "native_ok", "")))
  pure def choiceRead(c: Choice): List[Step] = List(ref(c._4, "read-attempt", c._4))
    .concat(native(viewObject("commit", "read-attempt", "attempt-view")))
    .append(step(t::parent("attempt-view", "0", "attempt-request"), "native_ok", c._2))
    .append(step(t::parent("attempt-view", "1", c._6), "native_ok", ""))
    .append(ref(c._5, "read-selection", c._5))

  pure val setup = List(recordStep(t::producer), recordStep(t::defineIntent("intent", t::v1, t::reuse)),
    recordStep(t::defineTable("intent", "empty")))
  pure val factors = List("-8", "-7", "-6", "-5", "-4", "-3", "-2", "-1", "0", "1", "2", "3", "4", "5", "6", "7")
  pure val full = "table-16"
  pure val capError = "reuse table cannot contain more than 16 requests"
  pure val keyError = "reuse table key does not match the selection request commit"
  pure val zero = "00000000000000000000000000000000"

  type Delta = { name: str, commit: str, basis: str, selection: str, mode: str, key: str, operand: str }
  pure val overflow: Delta = { name: "forged-overflow", commit: "put-overflow", basis: full, selection: "selection-17",
    mode: "insert", key: "request-17", operand: "native:request-17" }
  pure val wrongKey: Delta = { name: "wrong-key", commit: "put-wrong-key", basis: "one", selection: "selection-02",
    mode: "insert", key: zero, operand: zero }
  pure val buried: Delta = { name: "buried", commit: "put-buried", basis: "wrong-key", selection: "selection-03",
    mode: "adopt", key: "request-01", operand: "native:request-01" }
  pure val deltas = List(overflow, wrongKey, buried)
  pure def persist(delta: Delta, basis: str, selection: str): List[Request] =
    putLiteral("string", delta.mode, "operation-text", "operation-node")
      .concat(putLiteral("string", delta.operand, "key-text", "key-node"))
      .concat(putObject("dag", List("operation-node", "operation", "operation-node", "request_commit", "key-node"), "update-dag"))
      .concat(putObject("tree", List("scale-reuse-table-update-v1", "update-dag"), "update-tree"))
      .concat(putObject("commit", List("update-tree", basis, selection), delta.commit))
      .append(pin(delta.name, delta.commit))
  pure def deltaRead(delta: Delta): List[Request] = snapshotAt(delta.name, "delta-commit", "delta-tree", "delta-dag", "delta-basis")
    .append(t::parent("delta-commit", "1", "delta-selection"))
    .concat(viewObject("dag", "delta-dag", "delta-root"))
    .append(lookupNode("delta-dag", "operation", "delta-operation-node")).concat(viewLiteral("delta-operation-node", "delta-operation"))
    .append(lookupNode("delta-dag", "request_commit", "delta-key-node")).concat(viewLiteral("delta-key-node", "delta-key"))
  pure def deltaEvidence(delta: Delta): List[Step] = List(ref(delta.name, delta.name, delta.commit))
    .concat(native(deltaRead(delta)).replaceAt(0, step(deltaRead(delta)[0], "native_ok", delta.name)))

  pure val capacity = setup.concat(range(0, factors.length()).foldl(List(), (out, i) => {
    val c = choices[i]
    val basis = if (i == 0) "empty" else choices[i - 1]._8
    out.concat(choice(factors[i], c, t::v1)).append(recordStep(t::editTable(basis, c._5, c._8, "insert")))
  })).concat(choice("8", choices[16], t::v1))
    .concat(read(choices.slice(0, 17).foldl(List(), (out, c) => out.concat(choiceRead(c)))
      .concat(List(ref(full, "native-full", full), ref("selection-17", "native-extra", "selection-17")))))
    .concat(List(inspect(full, "full"), reject(t::editTable(full, "selection-17", "too-many", "insert"),
      "update-scale-reuse-table: reuse table cannot contain more than 16 requests")))
    .concat(write(persist(overflow, "native-full", "native-extra")))
    .concat(read(deltaEvidence(overflow).append(absent("too-many"))))
    .append(reject(t::inspect(overflow.name), "inspect: reuse table cannot contain more than 16 requests"))
    .concat(choice("-8", choices[17], t::v1)).concat(read(choiceRead(choices[17])))
    .concat(List(recordStep(t::editTable(full, "selection-18", "adopted", "adopt")), inspect("adopted", "adopted"), inspect(full, "full-again")))

  pure val invalidInsert = setup.concat(choice("2", choices[0], t::v1)).concat(choice("2", choices[1], t::v2))
    .append(recordStep(source("work_scale", List("request-01", "native:request-01", "result-only"))))
    .concat(read(List(ref("result-only", "seen-result-only", "result-only"))))
    .append(step(source("select_scale_result", List("plan-01", "plan-01", "result-only", "native:seen-result-only", "selected-result")), "selected", ""))
    .concat(read(choiceRead(choices[0]).concat(choiceRead(choices[1]))))
    .concat(List(inspect("selected-result", "result-only"), inspect("attempt-02", "v2-attempt"),
      reject(t::editTable("empty", "selected-result", "bad", "insert"), "update-scale-reuse-table: reuse table requires an attempt selection"),
      reject(t::editTable("empty", "selection-02", "bad", "insert"), "update-scale-reuse-table: selection implementation does not match the reuse table")))
    .concat(read(List(ref("empty", "seen-empty", "empty"), absent("bad"))))
    .concat(List(recordStep(t::editTable("empty", "selection-01", "one", "insert")), inspect("one", "v1-counterpart")))

  pure val routeBuried = t::ask("intent", "denied-plan", "denied-decision", "2", "buried", "native:buried", "default", "default")
  pure val fresh = t::ask("intent", "fresh-plan", "decision", "2", "buried", "native:buried", "default", "fresh")
  pure val badHistory = setup.concat(choice("2", choices[0], t::v1)).concat(choice("3", choices[1], t::v1)).concat(choice("2", choices[2], t::v1))
    .concat(List(recordStep(t::editTable("empty", "selection-01", "one", "insert")), recordStep(t::editTable("one", "selection-02", "two", "insert")),
      recordStep(t::editTable("two", "selection-03", "genuine", "adopt"))))
    .concat(read(choiceRead(choices[0]).concat(choiceRead(choices[1])).concat(choiceRead(choices[2]))
      .concat(List(ref("one", "native-one", "one"), ref("selection-02", "native-second", "selection-02"),
        ref("selection-03", "native-replacement", "selection-03")))))
    .concat(write(persist(wrongKey, "native-one", "native-second").concat(persist(buried, "put-wrong-key", "native-replacement"))))
    .concat(read(deltaEvidence(wrongKey).concat(deltaEvidence(buried))))
    .concat(List(inspect("genuine", "valid-chain"), reject(t::inspect("buried"), "inspect: reuse table key does not match the selection request commit"),
      reject(routeBuried, "request-table-scale: reuse table key does not match the selection request commit")))
    .concat(read(List(absent("main"), absent("denied-plan"), absent("denied-decision"))))
    .append(recordStep(fresh))
    .concat(read(List(ref("decision", "seen-decision", "decision"), ref("fresh-plan", "fresh-plan", ""), absent("main"))
      .concat(native(viewObject("commit", "seen-decision", "decision-view")))
      .append(step(t::parent("decision-view", "0", "decision-plan"), "native_ok", "fresh-plan"))
      .append(step(t::parent("decision-view", "1", "decision-intent"), "native_ok", "intent"))
      .concat(native(viewObject("commit", "fresh-plan", "fresh-plan-view")))
      .append(step(t::parent("fresh-plan-view", "0", "fresh-request"), "native_ok", "request-01"))))
    .append(inspect("decision", "fresh"))

  pure val cases = List(capacity, invalidInsert, badHistory)
  pure val requests = cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (reqs, s) => reqs.append(s.req))))
}

module recorded_calls_table_capacity_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_table_capacity_cases.requests

  var histories: List[List[Request]]
  action init = histories' = requests
  action step = histories' = histories
}
