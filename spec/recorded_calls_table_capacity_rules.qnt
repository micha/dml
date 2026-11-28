module recorded_calls_table_capacity_rules {
  import recorded_calls_rules as r from "./recorded_calls_rules"
  import recorded_calls_table_capacity_cases as h from "./recorded_calls_table_capacity_histories"
  import recorded_calls_table_fixture as t from "./recorded_calls_table_fixture"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  pure def idsFrom(rows: List[Attempt]): str -> str = rows.foldl(Map(), (out, a) => {
    val op = a.op
    val args = a.args
    if (a.commit != "" and op != "inspect") {
      val pin = if (Set("record_sum", "define_scale_intent").contains(op)) args[1]
        else if (op == "define_scale_reuse_table") args[4]
        else if (Set("work_scale", "work_scale_attempt", "request_scale").contains(op)) args[3]
        else args[5]
      out.put(pin, a.commit)
    } else if (a.nativeValue != "" and (Set("txn_ref_get", "object_view_parent").contains(op) or
      (op == "txn_put_object" and args[1] == "commit"))) out.put(args[args.length() - 1], a.nativeValue)
    else out
  })

  pure def entry(c: h::Choice, id: (str) => str): r::ReuseTableEntry = r::tableEntry(id(c._2), id(c._5),
    { id: c._7, commit: id(c._4), result: id(c._6), historicalRef: "" })
  pure def fullEntries(id: (str) => str): Set[r::ReuseTableEntry] =
    range(0, 16).foldl(Set(), (out, i) => out.union(Set(entry(h::choices[i], id))))
  pure def exactTable(a: Attempt, req: Request, pin: str, basis: str, ids: (str) => str, entries: Set[r::ReuseTableEntry]): str =
    if (ids(pin) == "" or ids(basis) == "" or ids("intent") == "" or
      not(entries.forall(e => e.request != "" and e.selection != "" and e.result != "" and e.attempt != ""))) "missing_table_evidence"
    else if (entries.map(e => e.request).size() != entries.size()) "wrong_table_keys"
    else if (not(r::matches(a, req)) or a.stdoutEmpty) "wrong_inspect"
    else r::tableReadVerdict(a, req, ids(pin), ids(basis), ids("intent"), entries)

  pure val deltaEntry = "7363616c652d72657573652d7461626c652d7570646174652d7631" // scale-reuse-table-update-v1
  pure def stringMatches(rows: List[Attempt], alias: str, value: str): bool = {
    val literal = r::nativeOutput(rows, "datum_decode", alias)
    r::nativeNodeMatches(rows, alias) and literal.nativeCount == 6 and literal.nativeItems == List(value)
  }
  pure def deltaMatches(rows: List[Attempt], delta: h::Delta, id: (str) => str): bool = {
    val key = if (delta.key == h::zero) h::zero else id(delta.key)
    val selectedKey = if (delta.name == h::wrongKey.name) id("request-02")
      else if (delta.name == h::buried.name) id("request-03") else id("request-17")
    val layout = r::decoded(rows, "delta-root")
    all {
      key != "" and selectedKey != "" and (if (delta.name == h::wrongKey.name) key != selectedKey else key == selectedKey),
      r::decoded(rows, "delta-commit").nativeCount == 2,
      r::treeEntry(rows, "delta-tree", "delta-dag", deltaEntry),
      id(delta.basis) != "" and r::outputId(rows, "object_view_parent", "delta-basis") == id(delta.basis),
      id(delta.selection) != "" and r::outputId(rows, "object_view_parent", "delta-selection") == id(delta.selection),
      layout.nativeCount == 2 and layout.nativeValue == r::outputId(rows, "txn_lookup_node", "delta-operation-node"),
      stringMatches(rows, "delta-operation", delta.mode),
      stringMatches(rows, "delta-key", key)
    }
  }
  pure def noTableFields(a: Attempt): bool = a.reportFields.length() > 0 and
    Set("table_ref", "table_commit", "selection_commit").intersect(a.reportFields[0].indices().map(i => a.reportFields[0][i])).size() == 0
  pure def freshRead(a: Attempt, req: Request, id: (str) => str, rows: List[Attempt]): str = {
    val expected = r::tableDecision(id("intent"), id("fresh-plan"), "fresh-plan", "", "", "default", "fresh", "override-fresh")
    val verdict = r::tableDecisionVerdict(a, req, id("decision"), id("request-01"), "-", "", "", expected, r::noOccurrence)
    if (verdict != "inspected") verdict
    else if (not(noTableFields(a))) "unexpected_table_fields"
    else if (r::decoded(rows, "decision-view").nativeCount != 2 or r::decoded(rows, "fresh-plan-view").nativeCount != 1) "wrong_fresh_graph"
    else verdict
  }
  pure def inspectVerdict(s: h::Step, a: Attempt, id: (str) => str, rows: List[Attempt]): str = {
    val req = s.req
    val c = h::choices
    if (s.detail == "full" or s.detail == "full-again") {
      val verdict = exactTable(a, req, h::full, "table-15", id, fullEntries(id))
      if (verdict != "inspected") verdict
      else if (a.reuseTable.entries.length() != 16 or id("request-17") == "" or a.reuseTable.entries.indices().exists(i =>
        a.reuseTable.entries[i].request == id("request-17"))) "wrong_table_capacity"
      else if (s.detail == "full-again" and a.stdoutHash != rows.select(row => r::sameRequest(row, req)).head().stdoutHash)
        "historical_table_changed"
      else verdict
    } else if (s.detail == "adopted") {
      val original = entry(c[0], id)
      val replacement = entry(c[17], id)
      if (original.request != replacement.request or original.result != replacement.result or
        original.selection == replacement.selection or original.attempt == replacement.attempt) "wrong_adoption_fixture"
      else exactTable(a, req, "adopted", h::full, id, fullEntries(id).exclude(Set(original)).union(Set(replacement)))
    } else if (s.detail == "result-only") r::selectionReadVerdict(a, req, id("selected-result"),
      { resultRef: "result-only", result: id("result-only") }, id("request-01"), t::v1)
    else if (s.detail == "v2-attempt") r::workerTableAttemptVerdict(a, req, id("attempt-02"), id("request-02"), c[1]._7, id("result-02"), t::v2)
    else if (s.detail == "v1-counterpart") exactTable(a, req, "one", "empty", id, Set(entry(c[0], id)))
    else if (s.detail == "valid-chain") {
      if (id("request-01") != id("request-03") or id("request-01") == id("request-02") or id("genuine") == id("buried")) "wrong_buried_fixture"
      else exactTable(a, req, "genuine", "two", id, Set(entry(c[2], id), entry(c[1], id)))
    } else if (s.detail == "fresh") freshRead(a, req, id, rows)
    else "unknown_inspect"
  }
  pure def guardedRejection(s: h::Step, a: Attempt, id: (str) => str): str = {
    val req = s.req
    val producer = if (req.op == "request_table_scale") id("producer") else ""
    if (req.op == "update_scale_reuse_table" and (a.expectedTable != id(req.args[2]) or
      a.expectedSelection != id(req.args[4]))) "wrong_table_guard"
    else if (req.op == "request_table_scale" and (a.expectedTable != id("buried") or a.expectedIntent != id("intent"))) "wrong_table_guard"
    else r::existingRejectionVerdict(a, req, producer, a.stderr == s.detail)
  }
  pure def stepVerdict(s: h::Step, a: Attempt, id: (str) => str, rows: List[Attempt], index: int): str = {
    val req = s.req
    val op = req.op
    val args = req.args
    if (not(r::sameRequest(a, req))) "wrong_request"
    else if (s.want == "native_not_found") r::rejectionNativeReadVerdict(a, req, "")
    else if (s.want == "native_ok") {
      if (s.detail == "") r::rejectionNativeVerdict(a, req, "ok")
      else if (op == "txn_ref_get" or op == "object_view_parent") {
        if (id(s.detail) == "") "missing_expected_id" else r::rejectionNativeReadVerdict(a, req, id(s.detail))
      } else {
        val delta = h::deltas.select(d => d.name == s.detail).head()
        if (deltaMatches(rows.slice(index, index + h::deltaRead(delta).length()), delta, id)) "native_ok" else "wrong_delta_graph"
      }
    } else if (s.want == "rejected") guardedRejection(s, a, id)
    else if (op == "inspect") inspectVerdict(s, a, id, rows)
    else if (op == "define_scale_reuse_table") r::tableWriteVerdict(a, req, id(args[2]), "", "", true)
    else if (op == "update_scale_reuse_table") r::tableWriteVerdict(a, req, "", id(args[2]), id(args[4]), true)
    else if (op == "request_table_scale") r::tableRequestVerdict(a, req, id("producer"), id("intent"), id("buried"), true)
    else if (op == "request_scale") r::scaleWriteVerdict(a, req, id("producer"))
    else if (op == "work_scale" or op == "work_scale_attempt") r::scaleWriteVerdict(a, req, id(args[1]))
    else if (op == "select_scale_attempt") r::selectAttemptVerdict(a, req, id(args[2]), id(args[4]), true)
    else if (op == "select_scale_result") r::selectVerdict(a, req, id(args[2]), id(args[3]), true)
    else r::writeVerdict(a, req)
  }
  pure def historyVerdicts(observation: Observation): List[str] = {
    if (not(h::cases.indices().contains(observation.scenario))) List("unknown_history")
    else {
      val steps = h::cases[observation.scenario]
      val rows = observation.attempts
      if (rows.length() != steps.length()) List("missing_steps")
      else {
        val ids = idsFrom(rows)
        def id(alias: str): str = if (ids.keys().contains(alias)) ids.get(alias) else ""
        range(0, steps.length()).foldl(List(), (out, i) => out.append(stepVerdict(steps[i], rows[i], id, rows, i)))
      }
    }
  }
  pure val expected = h::cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (labels, s) => labels.append(s.want))))
  pure def verdictAccepted(verdict: str): bool = r::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected

  pure val probe = h::reject(h::routeBuried, "request-table-scale: reuse table key does not match the selection request commit")
  pure val observed = { ...r::recorded, op: probe.req.op, args: probe.req.args, expectedTable: "buried", expectedIntent: "intent",
    expectedCommit: "producer", commit: "", code: 1, diagnosed: true, stdoutEmpty: true, unchanged: true,
    stderr: probe.detail, repoExisted: true, repoExists: true }
  pure def checkProbe(a: Attempt): str = guardedRejection(probe, a, alias => alias)
  pure val clean = { ...r::recorded, reportFields: List(List("commit", "decision_id", "reason")) }
  pure val controlsPass = all {
    checkProbe(observed) == "rejected",
    checkProbe({ ...observed, unchanged: false }) == "storage_changed",
    checkProbe({ ...observed, expectedTable: "another-table" }) == "wrong_table_guard",
    checkProbe({ ...observed, stderr: "request-table-scale: stale pin" }) == "wrong_diagnostic",
    noTableFields(clean),
    not(noTableFields({ ...clean, reportFields: List(List("commit", "table_ref")) }))
  }
}
