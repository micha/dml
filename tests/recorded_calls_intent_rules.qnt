module recorded_calls_intent_rules {
  import recorded_calls_rules as r from "./recorded_calls_rules"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_adoption_checks as adoption from "./recorded_calls_adoption_checks"
  import recorded_calls_adoption_fixture.firstUuid from "./recorded_calls_adoption_fixture"
  import recorded_calls_intent_cases as h from "./recorded_calls_intent_histories"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure def stringMatches(rows: List[Attempt], text: str): bool = {
    val literal = r::nativeOutput(rows, "datum_decode", "string-value")
    r::nativeNodeMatches(rows, "string-value") and literal.nativeCount == 6 and literal.nativeItems == List(text)
  }
  pure def roleHex(entry: str): str =
    if (entry == h::definition) "7363616c652d696e74656e742d646566696e6974696f6e2d7631"
    else if (entry == h::decision) "7363616c652d696e74656e742d6465636973696f6e2d7631"
    else if (entry == h::plan) "7363616c652d706c616e2d7631"
    else "7363616c652d726571756573742d7631"
  pure def entryMatches(rows: List[Attempt], entry: h::Entry, role: str, parents: int): bool =
    r::decoded(rows, entry._1).nativeCount == parents and r::treeEntry(rows, entry._2, entry._3, roleHex(role))
  pure def shapeMatches(rows: List[Attempt], s: h::Shape, ids: (str) => str): bool = {
    val start = h::shapeHeader(s).length()
    val width = h::readString("record-dag", s.fields[0]._1).length()
    all {
      entryMatches(rows, h::recordEntry, s.entry, s.parents.length()),
      s.parents.indices().forall(i => ids(s.parents[i]) != "" and ids(s.parents[i]) ==
        r::outputId(rows, "object_view_parent", h::parentIndices[i])),
      r::decoded(rows, "record-root").nativeCount == s.fields.length(),
      r::decoded(rows, "record-root").nativeValue == r::outputId(rows, "txn_lookup_node", "string-node"),
      s.fields.indices().forall(i => stringMatches(rows.slice(start + i * width, start + (i + 1) * width), s.fields[i]._2))
    }
  }
  pure def missLayout(rows: List[Attempt], ids: (str) => str): bool = all {
    entryMatches(rows, h::missEntry, h::decision, 2),
    ids("miss-plan") != "" and ids("miss-plan") == ids("plan-b-pin"),
    r::outputId(rows, "object_view_parent", "miss-intent") == ids("right"),
    entryMatches(rows, h::planEntry, h::plan, 1),
    entryMatches(rows, h::requestEntry, h::request, 1),
    r::outputId(rows, "object_view_entry", "plan-dag") == r::outputId(rows, "object_view_entry", "request-dag"),
    r::outputId(rows, "object_view_parent", "miss-producer") == ids("producer"),
    ids("miss-request") != "" and ids("miss-request") != ids("request-id"),
    r::decoded(rows, "request-root").nativeCount == 2,
    r::decoded(rows, "request-root").nativeValue == r::outputId(rows, "txn_lookup_node", "string-node"),
    stringMatches(rows, h::v2),
    r::nativeLiteralMatches(rows, "factor-value", 3, "0300000000000000")
  }

  pure def decisionRead(a: Attempt, req: Request, ids: (str) => str): str = {
    val name = req.args[1]
    val miss = name == "miss"
    val reused = name == "reused"
    val fresh = name == "fresh-decision"
    val definition = ids(if (miss) "right" else "intent")
    val version = if (reused) h::v1 else h::v2
    val saved = ids(if (miss) "miss-request" else if (reused) "request-id"
      else if (fresh) "fresh-decision-request" else "default-decision-request")
    val planPin = if (miss) "plan-b" else if (fresh) "fresh-plan" else "default-plan"
    val planId = ids(if (miss) "miss-plan" else if (reused) "reused-plan"
      else if (fresh) "fresh-plan-pin" else "default-plan-pin")
    val expected: r::Decision = { id: "", canonicalId: true, policy: "", intent: definition,
      defaultMode: if (miss) h::reuse else h::execute,
      override: if (reused) "reuse-selected" else if (fresh) "fresh" else "default",
      route: if (reused) "reuse-selected" else "execute-fresh",
      reason: if (miss) "default-no-selection" else if (reused) "override-selected-reuse"
        else if (fresh) "override-fresh" else "default-execution",
      plan: planId, planRef: if (reused) "" else planPin,
      selectionRef: if (miss) "chosen-b" else if (reused) "chosen" else "",
      selection: if (reused) ids("chosen") else "", result: if (reused) ids("first-result") else "",
      implementationOverride: if (reused) h::v1 else "default",
      implementationReason: if (reused) "explicit-implementation" else "default-implementation" }
    val occurrence: r::Occurrence = if (not(reused)) r::noOccurrence else
      { id: firstUuid, commit: ids("first"), result: ids("first-result"), historicalRef: "" }
    val verdict = r::intentDecisionReadVerdict(a, req, ids(name), saved, version, "-", expected, occurrence)
    if (saved == "" or planId == "") "missing_native_lineage"
    else if (verdict != "inspected") verdict
    else if (not(selectionFields(a, miss or reused, reused))) "wrong_selection_fields"
    else verdict
  }
  pure def selectionFields(a: Attempt, hasRef: bool, hasCommit: bool): bool =
    a.reportFields.length() > 0 and
    (a.reportFields[0].select(k => k == "selection_ref") == List("selection_ref")) == hasRef and
    (a.reportFields[0].select(k => k == "selection_commit") == List("selection_commit")) == hasCommit

  pure def idsFrom(rows: List[Attempt]): str -> str =
    rows.foldl(Map(), (out, a) => {
      val op = a.op
      if (a.commit != "" and Set("record_sum", "define_scale_intent", "request_scale", "work_scale_attempt",
        "select_scale_attempt", "request_intent_scale").contains(op)) {
        val alias = a.args[if (op == "record_sum" or op == "define_scale_intent") 1
          else if (op == "request_scale" or op == "work_scale_attempt") 3 else if (op == "select_scale_attempt") 5 else 6]
        out.put(alias, a.commit)
      } else if (a.nativeStatus == "ok" and Set("txn_put_object", "txn_ref_get", "object_view_parent").contains(op)) {
        val alias = a.args[a.args.length() - 1]
        out.put(alias, a.nativeValue)
      } else out
    })
  pure def stepVerdict(s: h::Step, a: Attempt, ids: (str) => str): str = {
    val req = s.req
    val op = req.op
    val args = req.args
    if (not(r::sameRequest(a, req))) "wrong_request"
    else if (s.want == "native_not_found") r::rejectionNativeReadVerdict(a, req, "")
    else if (s.want == "native_ok") {
      if (op == "txn_ref_get" and s.value != "") {
        if (ids(s.value) == "") "missing_expected_id" else r::rejectionNativeReadVerdict(a, req, ids(s.value))
      } else r::rejectionNativeVerdict(a, req, "ok")
    } else if (op == "request_intent_scale" and (ids(args[4]) == "" or a.expectedIntent != ids(args[4]) or
      (args[10] != "-" and ids(args[10]) == "") or a.expectedSelection != ids(args[10]))) "wrong_intent_guard"
    else if (s.want == "rejected") {
      val expected = if (op == "define_scale_intent") ids(args[4]) else if (op == "request_intent_scale") ids("producer") else ""
      val diagnostic = if (s.value == "occupied") "request-intent-scale: ('invalid_state', -30799, 'ref already exists')" else s.value
      r::existingRejectionVerdict(a, req, expected, a.stderr == diagnostic)
    } else if (op == "define_scale_intent") r::scaleWriteVerdict(a, req, ids(s.value))
    else if (op == "request_intent_scale") r::implementationIntentVerdict(a, req, ids("producer"), ids(args[4]), ids(args[10]), true)
    else if (op == "inspect" and args[1] == "right") r::intentReadVerdict(a, req, ids("right"),
      { implementation: h::v2, defaultMode: h::reuse, v1Selection: "chosen", v2Selection: "chosen-b", previous: ids("basis") })
    else if (op == "inspect") decisionRead(a, req, ids)
    else "unknown_step"
  }
  pure def historyVerdicts(row: Observation): List[str] = {
    val start = h::setup.length()
    if (row.scenario < 0 or row.scenario >= h::cases.length()) List("unknown_history")
    else {
      val steps = h::cases[row.scenario]
      val allRows = row.attempts
      if (allRows.length() != start + steps.length()) List("missing_steps")
      else {
        val rows = allRows.slice(start, allRows.length())
        val observedIds = idsFrom(allRows)
        def ids(alias: str): str = {
          val key = if (alias == "native:producer-id") "producer-id"
            else if (alias == "native:wrong-ancestor") "wrong-ancestor" else alias
          if (observedIds.keys().contains(key)) observedIds.get(key) else ""
        }
        val producerRead = adoption::setupExpected.length() + 2
        val setup = adoption::setupVerdicts(allRows).concat(range(adoption::setupExpected.length(), start).foldl(List(), (out, i) =>
          out.append(if (i == producerRead) r::rejectionNativeReadVerdict(allRows[i], h::setup[i], ids("producer"))
            else r::rejectionNativeVerdict(allRows[i], h::setup[i], "ok"))))
        range(0, steps.length()).foldl(setup, (out, i) => {
          val s = steps[i]
          val verdict = stepVerdict(s, rows[i], ids)
          val graphOK = if (s.graph == "" or verdict != "native_ok") true
            else if (s.graph == "miss-layout") missLayout(rows.slice(i, i + h::planReads.length()), ids)
            else {
              val shape = h::shapes.select(shape => shape.name == s.graph).head()
              shapeMatches(rows.slice(i, i + h::readShape(shape).length()), shape, ids)
            }
          out.append(if (graphOK) verdict else "wrong_native_graph")
        })
      }
    }
  }

  pure val expected = h::cases.foldl(List(), (out, steps) => out.append(steps.foldl(
    adoption::setupExpected.concat(List("native_ok", "native_ok", "native_ok", "native_ok", "native_ok")), (labels, s) => labels.append(s.want))))
  pure def verdictAccepted(verdict: str): bool = r::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected
  pure val sample = { ...r::recorded, reportFields: List(List("commit", "selection_ref")) }
  pure val controlsPass = selectionFields(sample, true, false) and not(selectionFields(sample, false, false)) and
    not(selectionFields({ ...sample, reportFields: List(List("commit", "selection_ref", "selection_commit")) }, true, false))
}
