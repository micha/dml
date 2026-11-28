module recorded_calls_intent_table_edit_cases {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_table_fixture as t from "./recorded_calls_table_fixture"
  import recorded_calls_table_capacity_cases as c from "./recorded_calls_table_capacity_histories"

  type Step = { req: Request, want: str, detail: str }
  pure def step(req: Request, want: str, detail: str): Step = { req: req, want: want, detail: detail }
  pure def record(req: Request): Step = step(req, "recorded", "")
  pure def inspect(pin: str, detail: str): Step = step(t::inspect(pin), "inspected", detail)
  pure def reject(req: Request, diagnostic: str): Step = step(req, "rejected", diagnostic)
  pure def native(reqs: List[Request]): List[Step] = reqs.foldl(List(), (out, req) => out.append(step(req, "native_ok", "")))
  pure def read(steps: List[Step]): List[Step] = native(openNative("read")).concat(steps).concat(native(closeNative("txn_abort")))
  pure def write(reqs: List[Request]): List[Step] = native(openNative("write").concat(reqs).concat(closeNative("txn_commit")))
  pure def ref(pin: str, alias: str, id: str): Step = step(refRead(pin, alias), "native_ok", id)
  pure def absent(pin: str): Step = step(refRead(pin, "absent"), "native_not_found", "")
  pure def parent(view: str, index: str, alias: str, id: str): Step = step(t::parent(view, index, alias), "native_ok", id)

  pure val setup = List(record(t::producer), record(t::defineIntent("intent", t::v1, t::reuse)),
    record(source("define_scale_intent_reuse_table", List("intent", "intent", "intent-empty"))))
  pure def edit(basis: str, out: str, operation: str, selection: str): Request =
    source("update_scale_intent_reuse_table", List(basis, basis, out, operation, selection, selection))
  pure def remove(basis: str, out: str, factor: str): Request =
    source("update_scale_intent_reuse_table", List(basis, basis, out, "remove", "producer", factor))
  pure def route(table: str, receipt: str): Request = source("request_intent_table_scale",
    List("producer", "intent", "intent", "denied-plan", "denied-decision", "-3", table, receipt, t::v2, "default"))

  pure val first = c::choices[0]
  pure val other = c::choices[1]
  pure val extra = c::choices[16]
  pure def choice(text: str, impl: str, c: c::Choice): List[Step] =
    t::choice(text, c._1, c._2, c._3, c._4, c._5, impl, c._7).foldl(List(), (out, req) => out.append(
      if (req.op == "select_scale_attempt") step(req, "selected", "")
      else if (Set("request_scale", "work_scale_attempt").contains(req.op)) record(req)
      else if (req.op == "txn_ref_get") ref(c._1, "choice-plan-id", c._1)
      else step(req, "native_ok", "")))
  pure def choiceEvidence(c: c::Choice): List[Step] = List(ref(c._4, "attempt-id", c._4))
    .concat(native(viewObject("commit", "attempt-id", "attempt-view")))
    .append(parent("attempt-view", "0", "attempt-request", c._2))
    .append(parent("attempt-view", "1", c._6, ""))
    .append(ref(c._5, "selection-id", c._5))

  // The same put and read paths construct and independently verify each defect.
  // Every delta has exactly the intended graph except the one field/edge varied.
  type Delta = { pin: str, id: str, receipt: str, basis: str, selection: str, operation: str,
    factorKind: str, factor: str, i64Payload: str, diagnostics: (str, str) }
  pure val keyErrors = ("inspect: intent reuse table key does not match the selection inputs",
    "request-intent-table-scale: intent reuse table key does not match the selection inputs")
  pure val parentsErrors = ("inspect: intent reuse table update requires its basis and a selection only for insert or adopt",
    "request-intent-table-scale: intent reuse table update requires its basis and a selection only for insert or adopt")
  pure val deltas: List[Delta] = List(
    { pin: "wrong-key", id: "put-wrong-key", receipt: "", basis: "one", selection: other._5, operation: "insert",
      factorKind: "i64", factor: "-4", i64Payload: "fcffffffffffffff", diagnostics: ("", "") },
    { pin: "buried", id: "put-buried", receipt: "native:buried", basis: "put-wrong-key", selection: "", operation: "remove",
      factorKind: "i64", factor: "-4", i64Payload: "fcffffffffffffff", diagnostics: keyErrors },
    { pin: "extra-parent", id: "put-extra-parent", receipt: "native:extra-parent", basis: "one", selection: first._5, operation: "remove",
      factorKind: "i64", factor: "-3", i64Payload: "fdffffffffffffff", diagnostics: parentsErrors },
    { pin: "missing-parent", id: "put-missing-parent", receipt: "native:missing-parent", basis: "one", selection: "", operation: "insert",
      factorKind: "i64", factor: "3", i64Payload: "0300000000000000", diagnostics: parentsErrors },
    { pin: "wrong-type", id: "put-wrong-type", receipt: "native:wrong-type", basis: "one", selection: "", operation: "remove",
      factorKind: "string", factor: "-3", i64Payload: "", diagnostics: ("inspect: recorded literal has the wrong datum kind",
        "request-intent-table-scale: recorded literal has the wrong datum kind") },
    { pin: "wrong-role", id: "put-wrong-role", receipt: "native:wrong-role", basis: "legacy", selection: first._5, operation: "insert",
      factorKind: "i64", factor: "-3", i64Payload: "fdffffffffffffff",
      diagnostics: ("inspect: expected an intent reuse table or update with its required ordered parents",
        "request-intent-table-scale: expected an intent reuse table or update with its required ordered parents") }
  )
  pure val deltaEntry = "scale-intent-reuse-table-update-v1"
  pure def persist(d: Delta): List[Request] =
    putLiteral("string", d.operation, "operation-data", "operation-node")
      .concat(putLiteral("string", "native:producer-id", "producer-data", "producer-node"))
      .concat(putLiteral(d.factorKind, d.factor, "factor-data", "factor-node"))
      .concat(putObject("dag", List("operation-node", "operation", "operation-node", "producer_commit", "producer-node",
        "factor", "factor-node"), "delta-dag"))
      .concat(putObject("tree", List(deltaEntry, "delta-dag"), "delta-tree"))
      .concat(putObject("commit", List("delta-tree", d.basis).concat(if (d.selection == "") List() else List(d.selection)), d.id))
      .append(pin(d.pin, d.id))
  pure def literalRead(binding: str, node: str, target: str): List[Request] =
    List(lookupNode("delta-entry", binding, node)).concat(viewLiteral(node, target))
  pure def deltaRead(d: Delta): List[Request] = snapshotAt(d.pin, "delta-commit", "delta-table-tree", "delta-entry", "delta-basis")
    .concat(if (d.selection == "") List() else List(t::parent("delta-commit", "1", "delta-selection")))
    .concat(viewObject("dag", "delta-entry", "delta-layout"))
    .concat(literalRead("operation", "read-operation-node", "read-operation"))
    .concat(literalRead("producer_commit", "read-producer-node", "read-producer"))
    .concat(literalRead("factor", "read-factor-node", "read-factor"))
  pure def deltaEvidence(d: Delta): List[Step] = List(ref(d.pin, d.pin, d.id))
    .concat(native(deltaRead(d)).replaceAt(0, step(deltaRead(d)[0], "native_ok", d.pin)))
  pure def rejectionPair(d: Delta): List[Step] = List(reject(t::inspect(d.pin), d.diagnostics._1),
    reject(route(d.pin, d.receipt), d.diagnostics._2))

  pure val malformed = setup.append(record(t::defineTable("intent", "legacy")))
    .concat(choice("-3", t::v1, first)).concat(choice("3", t::v2, other))
    .append(record(edit("intent-empty", "one", "insert", first._5)))
    .concat(read(choiceEvidence(first).concat(choiceEvidence(other)).concat(List(ref("producer", "producer-id", "producer"),
      ref("legacy", "legacy", "legacy"), ref("one", "one", "one"),
      ref(first._5, first._5, first._5), ref(other._5, other._5, other._5)))))
    .concat(write(deltas.foldl(List(), (out, d) => out.concat(persist(d)))))
    .concat(read(deltas.foldl(List(), (out, d) => out.concat(deltaEvidence(d)))))
    .concat(deltas.slice(1, deltas.length()).foldl(List(), (out, d) => out.concat(rejectionPair(d))))
    .concat(read(List(absent("main"), absent("denied-plan"), absent("denied-decision"))))
    .concat(List(record(edit("one", "two", "insert", other._5)), inspect("two", "inserted-both"),
      record(remove("two", "restored", "3")), inspect("restored", "removed-valid"), record(route("restored", "restored"))))
    .concat(read(List(ref("main", "routed-result", first._6), ref("denied-decision", "accepted-decision", "denied-decision"),
      absent("denied-plan"))))

  pure val full = c::full
  pure val capError = "update-scale-intent-reuse-table: reuse table cannot contain more than 16 requests"
  pure def implementation(i: int): str = if (i % 2 == 0) t::v2 else t::v1
  // Fill in reverse key order: report order must follow the signed factors,
  // not insertion order. The original tip stays pinned across removal/refill.
  pure val capacity = setup.concat(range(0, 16).foldl(List(), (out, i) => {
    val choiceIndex = 15 - i
    val selected = c::choices[choiceIndex]
    val basis = if (i == 0) "intent-empty" else c::choices[i - 1]._8
    out.concat(choice(c::factors[choiceIndex], implementation(choiceIndex), selected))
      .append(record(edit(basis, c::choices[i]._8, "insert", selected._5)))
  })).concat(choice("8", t::v1, extra))
    .concat(read(c::choices.slice(0, 17).foldl(List(), (out, selected) => out.concat(choiceEvidence(selected)))))
    .concat(List(inspect(full, "full"), reject(edit(full, "too-many", "insert", extra._5), capError)))
    .concat(read(List(absent("too-many"), ref(full, "full-after-overflow", full))))
    .concat(List(record(remove(full, "removed", "-8")), inspect("removed", "removed"),
      record(edit("removed", "refilled", "insert", extra._5)), inspect("refilled", "refilled"), inspect(full, "full-again")))
    .concat(read(List(ref(full, "full-after-refill", full), ref("removed", "removed-pin", "removed"),
      ref("refilled", "refilled-pin", "refilled"))))

  pure val attemptError = "update-scale-intent-reuse-table: reuse table adoption must change the selected attempt commit"
  pure val resultError = "update-scale-intent-reuse-table: reuse table requires an attempt selection"
  pure def selectionEvidence(pin: str, target: str): List[Step] = List(ref(pin, "read-selection-id", pin))
    .concat(native(viewObject("commit", "read-selection-id", "selection-view")))
    .append(parent("selection-view", "0", "selection-request", first._2))
    .append(parent("selection-view", "1", "selection-target", target))
  pure val identity = setup.concat(choice("3", t::v1, first))
    .append(record(edit("intent-empty", "one", "insert", first._5)))
    .concat(write(List(refRead(first._4, "aliased-id"), pin("aliased-attempt", "aliased-id"))))
    .append(step(source("select_scale_attempt", List(first._1, first._1, "aliased-attempt", first._4, "alias-selection")), "selected", ""))
    .append(record(source("work_scale", List(first._2, first._3, "result"))))
    .concat(read(List(ref("result", "result-id", "result"))))
    .append(step(source("select_scale_result", List(first._1, first._1, "result", "native:result-id", "result-only")), "selected", ""))
    .concat(read(choiceEvidence(first).append(ref("aliased-attempt", "read-alias", first._4))
      .concat(selectionEvidence(first._5, first._4)).concat(selectionEvidence("alias-selection", first._4))
      .concat(selectionEvidence("result-only", "result"))))
    .concat(List(inspect("alias-selection", "same-attempt"), inspect("result-only", "result-only"),
      reject(edit("one", "no-change", "adopt", "alias-selection"), attemptError),
      reject(edit("intent-empty", "bad", "insert", "result-only"), resultError)))
    .concat(read(List(absent("no-change"), absent("bad"), ref("one", "unchanged-one", "one"),
      ref("intent-empty", "unchanged-empty", "intent-empty"))))
    .append(inspect("one", "original-attempt"))

  pure val cases = List(malformed, capacity, identity)
  pure val requests = cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (reqs, s) => reqs.append(s.req))))
}

module recorded_calls_intent_table_edit_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_intent_table_edit_cases.requests

  var histories: List[List[Request]]
  action init = histories' = requests
  action step = histories' = histories
}
