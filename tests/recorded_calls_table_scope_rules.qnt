module recorded_calls_table_scope_rules {
  import recorded_calls_rules as r from "./recorded_calls_rules"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_table_fixture as t from "./recorded_calls_table_fixture"
  import recorded_calls_table_scope_cases as h from "./recorded_calls_table_scope_histories"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  type Setup = { producer: str, intent: str, empty: str, full: str, selection: str, request: str, occurrence: r::Occurrence }

  pure def setupIds(rows: List[Attempt]): Setup = { producer: rows[0].commit, intent: rows[2].commit,
    empty: rows[3].commit, full: rows[19].commit, selection: rows[16].commit,
    request: r::outputId(rows, "object_view_parent", "request-one"), occurrence: rows[18].occurrence }
  pure def native(rows: List[Attempt], reqs: List[Request]): List[str] =
    range(0, reqs.length()).foldl(List(), (out, i) => out.append(r::rejectionNativeVerdict(rows[i], reqs[i], "ok")))
  pure def setupVerdicts(rows: List[Attempt], reqs: List[Request], s: Setup, factor: int): List[str] = {
    val scenario = if (factor == 3) r::selected else { ...r::selected, factor: ("2", 2) }
    val plan = rows[5].commit
    val selection = rows[18]
    List(r::writeVerdict(rows[0], reqs[0]), r::sumReadVerdict(scenario, rows[1], reqs[1], s.producer),
      r::scaleWriteVerdict(rows[2], reqs[2], ""), r::tableWriteVerdict(rows[3], reqs[3], s.intent, "", "", true),
      r::tableReadVerdict(rows[4], reqs[4], s.empty, "", s.intent, Set()), r::scaleWriteVerdict(rows[5], reqs[5], s.producer))
      .concat(native(rows.slice(6, 8), reqs.slice(6, 8)))
      .append(r::rejectionNativeReadVerdict(rows[8], reqs[8], plan))
      .concat(native(rows.slice(9, 15), reqs.slice(9, 15)))
      .concat(List(r::scaleWriteVerdict(rows[15], reqs[15], s.request),
        r::selectAttemptVerdict(rows[16], reqs[16], plan, rows[15].commit, true),
        r::planReadVerdict(rows[17], reqs[17], plan, s.request, factor, rows[1], t::v1),
        if (r::matches(selection, reqs[18]) and selection.unchanged and selection.commit == s.selection and
            selection.requestCommit == s.request and selection.requestImplementation == t::v1 and
            s.occurrence == { id: h::uuid, commit: rows[15].commit, result: s.occurrence.result, historicalRef: "attempt-one" } and
            s.occurrence.result != "" and selection.previousSelection == "") "inspected" else "wrong_selection_record",
        r::tableWriteVerdict(rows[19], reqs[19], "", s.empty, s.selection, true),
        r::tableReadVerdict(rows[20], reqs[20], s.full, s.empty, s.intent, Set(r::tableEntry(s.request, s.selection, s.occurrence)))))
  }

  pure val decisionTableFields = Set("table_ref", "table_commit", "selection_commit", "attempt_commit", "attempt_id", "result_commit")
  pure def decisionFields(read: Attempt, reuse: bool): bool = {
    if (read.reportFields.length() == 0) false
    else {
      val reportKeys = read.reportFields[0].foldl(Set(), (out, k) => out.union(Set(k)))
      reportKeys.intersect(decisionTableFields) == (if (reuse) decisionTableFields else Set())
    }
  }

  pure def decisionVerdict(read: Attempt, req: Request, s: Setup, commit: str, plan: str, intent: str,
                            policy: str, table: str, implementation: str, override: str, reason: str): str = {
    val reuse = table != ""
    val expected = { ...r::tableDecision(intent, plan, if (reuse) "" else "fresh", if (reuse) s.selection else "",
      if (reuse) s.occurrence.result else "", implementation, override, reason), defaultMode: policy }
    if (not(decisionFields(read, reuse))) "wrong_decision_fields"
    else r::tableDecisionVerdict(read, req, commit, s.request, "-", if (reuse) "full" else "", table,
      expected, if (reuse) { ...s.occurrence, historicalRef: "" } else r::noOccurrence)
  }

  pure def requestRejection(a: Attempt, req: Request, s: Setup, intent: str, table: str, diagnostic: str): str = {
    val guard = r::tableRequestVerdict(a, req, s.producer, intent, table, false)
    if (guard != "rejected") guard
    else r::existingRejectionVerdict(a, req, s.producer, a.stderr == diagnostic)
  }

  pure def lineageVerdicts(rows: List[Attempt], s: Setup): List[str] = {
    val req = h::lineage
    val other = rows[0].commit
    val sameFields = rows[1].commit
    val promoted = rows[2].commit
    val decision = rows[16].commit
    val definition: r::Intent = { implementation: t::v1, defaultMode: t::reuse, v1Selection: "legacy-v1",
      v2Selection: "legacy-v2", previous: "" }
    val wrongScope = "request-table-scale: reuse table does not match the intent lineage and selected implementation"
    List(if (other == s.intent) "wrong_intent_lineage" else r::scaleWriteVerdict(rows[0], req[0], ""),
      r::scaleWriteVerdict(rows[1], req[1], other),
      r::scaleWriteVerdict(rows[2], req[2], s.intent),
      r::intentReadVerdict(rows[3], req[3], s.intent, definition),
      r::intentReadVerdict(rows[4], req[4], other, { ...definition, implementation: t::v2 }),
      r::intentReadVerdict(rows[5], req[5], sameFields, { ...definition, previous: other }),
      r::intentReadVerdict(rows[6], req[6], promoted, { ...definition, implementation: t::v2, previous: s.intent }),
      requestRejection(rows[7], req[7], s, sameFields, s.full, wrongScope),
      requestRejection(rows[8], req[8], s, promoted, s.full, wrongScope))
      .concat(r::rejectionReadVerdicts(rows.slice(9, 16), req.slice(9, 16), List("", "", "")))
      .concat(List(r::tableRequestVerdict(rows[16], req[16], s.producer, promoted, s.full, true),
        decisionVerdict(rows[17], req[17], s, decision, rows[17].decision.plan, promoted, t::reuse,
          s.full, t::v1, "default", "default-table-hit")))
      .concat(r::rejectionReadVerdicts(rows.slice(18, rows.length()), req.slice(18, req.length()),
        List(s.occurrence.result, decision, "")))
  }

  pure def defaultsVerdicts(rows: List[Attempt], s: Setup, summed: Attempt): List[str] = {
    val req = h::defaults
    val decision = rows[11].commit
    List(r::tableRequestVerdict(rows[0], req[0], s.producer, s.intent, s.producer, true),
      decisionVerdict(rows[1], req[1], s, rows[0].commit, rows[2].commit, s.intent, t::execute,
        "", "default", "default", "default-execution"),
      r::planReadVerdict(rows[2], req[2], rows[1].decision.plan, s.request, 2, summed, t::v1),
      requestRejection(rows[3], req[3], s, s.intent, s.empty,
        "request-table-scale: explicit reuse requires a present selection"))
      .concat(r::rejectionReadVerdicts(rows.slice(4, 11), req.slice(4, 11), List("", "", "")))
      .concat(List(r::tableRequestVerdict(rows[11], req[11], s.producer, s.intent, s.full, true),
        decisionVerdict(rows[12], req[12], s, decision, rows[12].decision.plan, s.intent, t::execute,
          s.full, "default", "reuse-selected", "override-selected-reuse")))
      .concat(r::rejectionReadVerdicts(rows.slice(13, rows.length()), req.slice(13, req.length()),
        List(s.occurrence.result, decision, "")))
  }

  pure def forgeMatches(rows: List[Attempt], s: Setup, decision: str): bool = {
    val genuine = r::decoded(rows, "decision-view")
    val forged = r::decoded(rows, "forged-view")
    val fakeId = r::storedObject(rows, "forged-id")
    val empty = r::storedRef(rows, "empty-id")
    def parent(alias: str): str = r::outputId(rows, "object_view_parent", alias)
    all {
      r::storedRef(rows, "decision-pin") == decision, r::storedRef(rows, "forged-pin") == fakeId,
      fakeId != "" and fakeId != decision,
      genuine.nativeCount == 3 and forged.nativeCount == 3,
      genuine.nativeValue != "" and genuine.nativeValue == forged.nativeValue,
      parent("decision-plan") != "" and parent("forged-plan") == parent("decision-plan"),
      parent("decision-intent") == s.intent and parent("forged-intent") == s.intent,
      parent("decision-table") == s.full and parent("forged-table") == empty and empty == s.empty and empty != s.full,
      r::decoded(rows, "decision-plan-view").nativeCount == 1 and parent("decision-request") == s.request
    }
  }

  pure def forgeryVerdicts(rows: List[Attempt], s: Setup): List[str] = {
    val req = h::forgery
    val rejection = req.length() - 2
    val decision = rows[0].commit
    val plan = r::outputId(rows, "object_view_parent", "decision-plan")
    List(r::tableRequestVerdict(rows[0], req[0], s.producer, s.intent, s.full, true))
      .concat(native(rows.slice(1, rejection), req.slice(1, rejection)))
      .concat(List(
        if (not(forgeMatches(rows, s, decision))) "wrong_forged_table_parent"
        else r::existingRejectionVerdict(rows[rejection], req[rejection], "",
          rows[rejection].stderr == "inspect: intent decision fields do not match the resolved policy"),
        decisionVerdict(rows[rejection + 1], req[rejection + 1], s, decision, plan, s.intent, t::reuse,
          s.full, "default", "default", "default-table-hit")))
  }

  pure def historyVerdicts(row: Observation): List[str] = {
    if (row.scenario < 0 or row.scenario >= h::requests.length()) List("unknown_history")
    else {
      val reqs = h::requests[row.scenario]
      if (row.attempts.length() != reqs.length()) List("missing_steps")
      else {
        val first = row.attempts.slice(0, h::setupLength)
        val steps = row.attempts.slice(h::setupLength, row.attempts.length())
        val s = setupIds(first)
        setupVerdicts(first, reqs.slice(0, h::setupLength), s, if (row.scenario == 2) 3 else 2)
          .concat(if (row.scenario == 0) lineageVerdicts(steps, s)
            else if (row.scenario == 1) defaultsVerdicts(steps, s, first[1]) else forgeryVerdicts(steps, s))
      }
    }
  }

  pure val setupExpected = List("recorded", "inspected", "recorded", "recorded", "inspected", "recorded")
    .concat(range(0, 9).foldl(List(), (out, i) => out.append("native_ok")))
    .concat(List("recorded", "selected", "inspected", "inspected", "recorded", "inspected"))
  pure val noRefs = List("native_ok", "native_ok", "native_not_found", "native_not_found", "native_not_found", "native_ok", "native_ok")
  pure val hit = List("recorded", "inspected", "native_ok", "native_ok", "native_ok", "native_ok", "native_not_found", "native_ok", "native_ok")
  pure val expected = List(
    setupExpected.concat(List("recorded", "recorded", "recorded", "inspected", "inspected", "inspected", "inspected",
      "rejected", "rejected")).concat(noRefs).concat(hit),
    setupExpected.concat(List("recorded", "inspected", "inspected", "rejected")).concat(noRefs).concat(hit),
    setupExpected.append("recorded").concat(range(0, h::forgeWrite.length() + h::forgeRead.length())
      .foldl(List(), (out, i) => out.append("native_ok"))).concat(List("rejected", "inspected")))

  pure def verdictAccepted(verdict: str): bool = r::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected

  pure val omitted = { ...r::recorded, reportFields: List(List("reason")) }
  pure val leaked = { ...omitted, reportFields: List(List("reason", "table_commit")) }
  pure val reused = { ...omitted, reportFields: List(List("reason", "table_ref", "table_commit", "selection_commit",
    "attempt_commit", "attempt_id", "result_commit")) }
  pure val controlsPass = decisionFields(omitted, false) and not(decisionFields(leaked, false)) and
    decisionFields(reused, true) and not(decisionFields(leaked, true))
}
