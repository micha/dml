module recorded_calls_intent_table_route_rules {
  import recorded_calls_rules as r from "./recorded_calls_rules"
  import recorded_calls_intent_table_route_cases as h from "./recorded_calls_intent_table_route_histories"
  import recorded_calls_table_fixture as t from "./recorded_calls_table_fixture"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  type Marks = str -> Attempt
  pure def entry(m: Marks, rows: List[Attempt], factor: int): r::IntentReuseEntry =
    r::intentTableEntry(m.get("producer").commit, factor, r::outputId(rows, "object_view_parent", "old-request"), t::v1,
      m.get("selection").commit, { id: h::uuid, commit: m.get("attempt").commit,
        result: r::outputId(rows, "object_view_parent", "attempt-result"), historicalRef: "attempt" })

  pure def collision(a: Attempt, req: Request, producer: str, intent: str, table: str, route: bool): str = {
    val guard = if (route) r::tableRequestVerdict(a, req, producer, intent, table, false)
      else r::intentTableWriteVerdict(a, req, table, "", producer, false)
    val diagnostic = if (route) "request-intent-table-scale: ('invalid_state', -30799, 'ref already exists')"
      else "update-scale-intent-reuse-table: ('invalid_state', -30799, 'ref already exists')"
    if (guard != "rejected") guard
    else r::existingRejectionVerdict(a, req, producer, a.stderr == diagnostic)
  }

  pure def decisionParents(rows: List[Attempt], p: h::Parents, plan: str, intent: str, table: str): bool =
    r::decoded(rows, p.view).nativeCount == 3 and
      r::outputId(rows, "object_view_parent", p.plan) == plan and plan != "" and
      r::outputId(rows, "object_view_parent", p.intent) == intent and intent != "" and
      r::outputId(rows, "object_view_parent", p.table) == table and table != ""

  pure def inspectHit(a: Attempt, req: Request, m: Marks, rows: List[Attempt], producing: r::IntentReuseEntry,
                     routing: bool): str = {
    val intent = m.get("intent").commit
    val table = m.get("one").commit
    val plan = r::outputId(rows, "object_view_parent", "decision-plan")
    val requested = r::outputId(rows, "object_view_parent", if (routing) "v2-request" else "captured-request")
    val prior = if (routing) "-" else m.get("prior").commit
    val expected = r::tableDecision(intent, plan, "", producing.selection, producing.result, t::v2, "default", "default-table-hit")
    val graph = decisionParents(rows, h::decisionPath, plan, intent, table) and requested != "" and requested != producing.request
    val exact = if (routing) plan == m.get("v2-plan").commit and r::decoded(rows, "v2-view").nativeCount == 1 and
      r::decoded(rows, "produced-result-view").nativeCount == 1 and
      r::outputId(rows, "object_view_parent", "result-request") == producing.request
    else prior != "" and prior != producing.result and r::decoded(rows, "captured-plan-view").nativeCount == 2 and
      r::outputId(rows, "object_view_parent", "captured-main") == prior
    if (not(graph and exact)) "wrong_decision_graph"
    else r::intentTableDecisionVerdict(a, req, m.get("decision").commit, requested, t::v2, prior,
      if (routing) "one" else "one-live", table, expected, producing)
  }

  pure def forgedRejection(a: Attempt, req: Request, m: Marks, rows: List[Attempt], swapPlan: bool): str = {
    val forged = if (swapPlan) "bad-plan" else "bad-table"
    val path = if (swapPlan) h::swappedPlan else h::swappedTable
    val plan = if (swapPlan) m.get("old-plan").commit else m.get("v2-plan").commit
    val table = if (swapPlan) m.get("one").commit else m.get("empty").commit
    val tree = r::decoded(rows, "decision-view").nativeValue
    val forgedId = r::storedObject(rows, forged)
    val diagnostic = if (swapPlan) "inspect: intent decision does not match the resolved implementation"
      else "inspect: intent decision fields do not match the resolved policy"
    if (tree == "" or r::decoded(rows, path.view).nativeValue != tree or
      not(decisionParents(rows, path, plan, m.get("intent").commit, table)) or
      forgedId == "" or forgedId == m.get("decision").commit) "wrong_forged_parent"
    else r::existingRejectionVerdict(a, req, "", a.stderr == diagnostic)
  }

  pure def nativeVerdict(s: h::Step, a: Attempt, m: Marks, rows: List[Attempt], result: str): str = {
    val mark = s.mark
    if (mark == "") r::rejectionNativeVerdict(a, s.req, "ok")
    else {
      val id = if (mark == "main-result") result
        else if (mark == "old-main") m.get("prior").commit
        else if (mark == "one-live-pin") m.get("one").commit
        else if (mark == "choice-plan-id") m.get("old-plan").commit
        else if (mark == "bad-plan-pin" or mark == "bad-table-pin") r::storedObject(rows, s.req.args[1])
        else m.get(s.req.args[1]).commit
      if (id == "") "missing_expected_pin" else r::rejectionNativeReadVerdict(a, s.req, id)
    }
  }

  pure def stepVerdict(s: h::Step, a: Attempt, m: Marks, rows: List[Attempt], e: r::IntentReuseEntry, routing: bool): str = {
    val req = s.req
    val mark = s.mark
    val intent = m.get("intent").commit
    val empty = m.get("empty").commit
    val table = m.get("one").commit
    val producer = e.producer
    if (not(r::sameRequest(a, req))) "wrong_request"
    else if (s.want == "native_ok") nativeVerdict(s, a, m, rows, e.result)
    else if (s.want == "native_not_found") r::rejectionNativeReadVerdict(a, req, "")
    else if (s.want == "rejected") {
      if (routing) forgedRejection(a, req, m, rows, mark == "resolved implementation")
      else collision(a, req, producer, intent, table, mark == "occupied decision")
    } else if (mark == "producer") r::writeVerdict(a, req)
    else if (mark == "sum") r::sumReadVerdict(r::selected, a, req, producer)
    else if (mark == "intent") r::scaleWriteVerdict(a, req, "")
    else if (mark == "empty") r::tableWriteVerdict(a, req, intent, "", "", true)
    else if (mark == "old-plan" or mark == "v2-plan" or mark == "prior") r::scaleWriteVerdict(a, req, producer)
    else if (mark == "read-old-plan") r::planReadVerdict(a, req, m.get("old-plan").commit, e.request, e.factor, m.get("sum"), t::v1)
    else if (mark == "read-v2-plan") r::planReadVerdict(a, req, m.get("v2-plan").commit,
      r::outputId(rows, "object_view_parent", "v2-request"), e.factor, m.get("sum"), t::v2)
    else if (mark == "attempt") r::scaleWriteVerdict(a, req, e.request)
    else if (mark == "selection") r::selectAttemptVerdict(a, req, m.get("old-plan").commit, m.get("attempt").commit, true)
    else if (mark == "read-selection") {
      if (r::decoded(rows, "attempt-view").nativeCount != 2 or e.request == "" or e.result == "" or
        r::outputId(rows, "object_view_parent", "attempt-request") != e.request) "wrong_attempt_graph"
      else if (not(r::matches(a, req)) or not(a.unchanged) or a.commit != e.selection or a.requestCommit != e.request or
        a.requestImplementation != t::v1 or a.previousSelection != "" or
        a.occurrence != { ...r::entryOccurrence(e), historicalRef: "attempt" }) "wrong_selection_record"
      else "inspected"
    } else if (mark == "one") r::intentTableWriteVerdict(a, req, empty, e.selection, "", true)
    else if (mark == "read-one" or mark == "read-retained") r::intentTableReadVerdict(a, req, table, intent, intent, empty, Set(e))
    else if (mark == "decision") r::tableRequestVerdict(a, req, producer, intent, table, true)
    else if (mark == "read-decision" or mark == "read-genuine" or mark == "read-after-collision") inspectHit(a, req, m, rows, e, routing)
    else if (mark == "removed") r::intentTableWriteVerdict(a, req, table, "", producer, true)
    else if (mark == "read-removed") r::intentTableReadVerdict(a, req, m.get("removed").commit, intent, intent, table, Set())
    else "unknown_step"
  }

  pure def historyVerdicts(o: Observation): List[str] = {
    if (not(h::cases.indices().contains(o.scenario))) List("unknown_history")
    else {
      val steps = h::cases[o.scenario]
      val rows = o.attempts
      if (rows.length() != steps.length()) List("missing_steps")
      else {
        val m = range(0, steps.length()).foldl(Map(), (out, i) =>
          if (steps[i].mark == "") out else out.put(steps[i].mark, rows[i]))
        val routing = o.scenario == 0
        val e = entry(m, rows, if (routing) -3 else 3)
        range(0, steps.length()).foldl(List(), (out, i) =>
          out.append(stepVerdict(steps[i], rows[i], m, rows, e, routing)))
      }
    }
  }

  pure def verdictAccepted(verdict: str): bool = r::verdictAccepted(verdict)
  pure val expected = h::cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (labels, s) => labels.append(s.want))))
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected

  pure val request = h::ask("one", "3", "one-live")
  pure val rejection = { ...r::recorded, op: request.op, args: request.args, code: 1, commit: "", diagnosed: true,
    stdoutEmpty: true, repoExisted: true, repoExists: true, unchanged: true, expectedCommit: "producer", expectedIntent: "intent",
    expectedTable: "table", stderr: "request-intent-table-scale: ('invalid_state', -30799, 'ref already exists')" }
  pure def probe(a: Attempt): str = collision(a, request, "producer", "intent", "table", true)
  pure val controlsPass = all {
    probe(rejection) == "rejected",
    probe({ ...rejection, stderr: "request-intent-table-scale: plan output ref is already occupied" }) == "wrong_diagnostic",
    probe({ ...rejection, unchanged: false }) == "storage_changed",
    probe({ ...rejection, expectedTable: "wrong-table" }) == "wrong_table_guard"
  }
}
