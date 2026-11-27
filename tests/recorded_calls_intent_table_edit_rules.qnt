module recorded_calls_intent_table_edit_rules {
  import recorded_calls_rules as r from "./recorded_calls_rules"
  import recorded_calls_intent_table_edit_cases as h from "./recorded_calls_intent_table_edit_histories"
  import recorded_calls_table_capacity_cases as c from "./recorded_calls_table_capacity_histories"
  import recorded_calls_table_fixture as t from "./recorded_calls_table_fixture"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  pure def idsFrom(steps: List[h::Step], rows: List[Attempt]): str -> str =
    range(0, steps.length()).foldl(Map(), (out, i) => {
      val req = steps[i].req
      val a = rows[i]
      val op = req.op
      val args = req.args
      if (a.commit != "" and op != "inspect") {
        val pin = if (Set("record_sum", "define_scale_intent").contains(op)) args[1]
          else if (op == "define_scale_reuse_table") args[4]
          else if (Set("select_scale_attempt", "select_scale_result", "request_intent_table_scale").contains(op)) args[5]
          else args[3]
        out.put(pin, a.commit)
      } else if (a.nativeValue != "" and (
        (op == "object_view_parent" and steps[i].detail == "") or (op == "txn_put_object" and args[1] == "commit")))
        out.put(args[args.length() - 1], a.nativeValue)
      else out
    })

  pure def entry(c: c::Choice, factor: int, impl: str, id: (str) => str): r::IntentReuseEntry =
    r::intentTableEntry(id("producer"), factor, id(c._2), impl, id(c._5),
      { id: c._7, commit: id(c._4), result: id(c._6), historicalRef: "" })
  pure def fullEntries(id: (str) => str): List[r::IntentReuseEntry] =
    range(0, 16).foldl(List(), (out, i) => out.append(entry(c::choices[i], i - 8, h::implementation(i), id)))
  pure def exactTable(a: Attempt, req: Request, commit: str, basis: str, intent: str, entries: List[r::IntentReuseEntry]): str = {
    if (commit == "" or basis == "" or intent == "" or entries.indices().exists(i => {
      val e = entries[i]
      e.producer == "" or e.request == "" or e.selection == "" or e.result == "" or e.attempt == ""
    })) "missing_table_evidence"
    else if (a.stdoutEmpty) "wrong_inspect"
    else {
      val verdict = r::intentTableReadVerdict(a, req, commit, intent, intent, basis, entries.indices().map(i => entries[i]))
      if (verdict != "inspected") verdict
      else if (a.intentReuseTable.entries != entries) "wrong_table_order"
      else verdict
    }
  }

  pure val deltaEntryHex = "7363616c652d696e74656e742d72657573652d7461626c652d7570646174652d7631"
  pure def stringMatches(rows: List[Attempt], alias: str, value: str): bool = {
    val literal = r::nativeOutput(rows, "datum_decode", alias)
    r::nativeNodeMatches(rows, alias) and literal.nativeCount == 6 and literal.nativeItems == List(value)
  }
  pure def deltaMatches(rows: List[Attempt], d: h::Delta, id: (str) => str): bool = {
    val basis = id(d.basis)
    val layout = r::decoded(rows, "delta-layout")
    all {
      basis != "" and r::outputId(rows, "object_view_parent", "delta-basis") == basis,
      r::decoded(rows, "delta-commit").nativeCount == (if (d.selection == "") 1 else 2),
      d.selection == "" or (id(d.selection) != "" and
        r::outputId(rows, "object_view_parent", "delta-selection") == id(d.selection)),
      r::treeEntry(rows, "delta-table-tree", "delta-entry", deltaEntryHex),
      layout.nativeCount == 3 and layout.nativeValue == r::outputId(rows, "txn_lookup_node", "read-operation-node"),
      stringMatches(rows, "read-operation", d.operation),
      id("producer") != "" and stringMatches(rows, "read-producer", id("producer")),
      if (d.factorKind == "string") stringMatches(rows, "read-factor", d.factor)
      else r::nativeLiteralMatches(rows, "read-factor", 3, d.i64Payload)
    }
  }

  pure def guardedRejection(s: h::Step, a: Attempt, id: (str) => str): str = {
    val req = s.req
    val args = req.args
    val op = req.op
    val producer = if (op == "request_intent_table_scale") id("producer") else ""
    // The read and route must see the same malformed commit, not a stale pin
    // or some unrelated error that happened to leave the repository unchanged.
    if (op == "request_intent_table_scale") {
      val delta = h::deltas.select(d => d.pin == args[7]).head()
      if (producer == "" or id("intent") == "" or id(delta.id) == "" or a.expectedTable != id(delta.id) or
        a.expectedIntent != id("intent")) "wrong_table_guard"
      else r::existingRejectionVerdict(a, req, producer, a.stderr == s.detail)
    } else if (op == "update_scale_intent_reuse_table" and (id(args[2]) == "" or id(args[6]) == "" or
      a.expectedTable != id(args[2]) or a.expectedSelection != id(args[6]))) "wrong_table_guard"
    else r::existingRejectionVerdict(a, req, producer, a.stderr == s.detail)
  }

  pure def inspectVerdict(s: h::Step, a: Attempt, id: (str) => str, rows: List[Attempt]): str = {
    val req = s.req
    val pin = req.args[1]
    val detail = s.detail
    val first = h::first
    if (Set("full", "full-again", "removed", "refilled").contains(detail)) {
      val full = fullEntries(id)
      val retained = full.slice(1, full.length())
      val added = entry(h::extra, 8, t::v1, id)
      val entries = if (detail == "removed") retained else if (detail == "refilled") retained.append(added) else full
      val basis = if (detail == "removed") h::full else if (detail == "refilled") "removed" else "table-15"
      val verdict = exactTable(a, req, id(pin), id(basis), id("intent"), entries)
      if (verdict != "inspected") verdict
      else if (detail == "full-again" and (a.stdoutHash == "" or a.stdoutHash != rows.select(row => r::sameRequest(row, req)).head().stdoutHash))
        "historical_table_changed"
      else verdict
    } else if (detail == "inserted-both") exactTable(a, req, id(pin), id("one"), id("intent"),
      List(entry(first, -3, t::v1, id), entry(h::other, 3, t::v2, id)))
    else if (detail == "removed-valid") exactTable(a, req, id(pin), id("two"), id("intent"), List(entry(first, -3, t::v1, id)))
    else if (detail == "original-attempt") exactTable(a, req, id(pin), id("intent-empty"), id("intent"), List(entry(first, 3, t::v1, id)))
    else if (detail == "same-attempt") {
      val original = entry(first, 3, t::v1, id)
      val expected = { ...r::entryOccurrence(original), historicalRef: "aliased-attempt" }
      if (id(pin) == "" or id(pin) == original.selection or original.attempt == "" or original.request == "" or
        original.result == "") "wrong_attempt_alias_fixture"
      else if (r::matches(a, req) and a.unchanged and a.commit == id(pin) and a.requestCommit == original.request and
        a.requestImplementation == t::v1 and a.occurrence == expected and a.previousSelection == "") "inspected"
      else "wrong_alias_selection"
    } else if (detail == "result-only") {
      val result = id("result")
      if (result == "" or result != id(first._6) or a.occurrence != r::noOccurrence) "wrong_result_only_fixture"
      else r::selectionReadVerdict(a, req, id(pin), { resultRef: "result", result: result }, id(first._2), t::v1)
    } else "unknown_inspect"
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
        val delta = h::deltas.select(d => d.pin == s.detail).head()
        if (deltaMatches(rows.slice(index, index + h::deltaRead(delta).length()), delta, id)) "native_ok" else "wrong_delta_graph"
      }
    } else if (s.want == "rejected") guardedRejection(s, a, id)
    else if (op == "inspect") inspectVerdict(s, a, id, rows)
    else if (op == "define_scale_reuse_table" or op == "define_scale_intent_reuse_table")
      r::tableWriteVerdict(a, req, id(args[2]), "", "", true)
    else if (op == "update_scale_intent_reuse_table") {
      val removal = args[4] == "remove"
      r::intentTableWriteVerdict(a, req, id(args[2]), if (removal) "" else id(args[6]),
        if (removal) id(args[5]) else "", true)
    } else if (op == "request_intent_table_scale") r::tableRequestVerdict(a, req, id("producer"), id("intent"), id(args[8]), true)
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
        val ids = idsFrom(steps, rows)
        def id(alias: str): str = if (ids.keys().contains(alias)) ids.get(alias) else ""
        range(0, steps.length()).foldl(List(), (out, i) => out.append(stepVerdict(steps[i], rows[i], id, rows, i)))
      }
    }
  }
  pure val expected = h::cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (labels, s) => labels.append(s.want))))
  pure def verdictAccepted(verdict: str): bool = r::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected

  pure val probe = h::reject(h::route("buried", "native:buried"), h::keyErrors._2)
  pure val observed = { ...r::recorded, op: probe.req.op, args: probe.req.args, expectedTable: "put-buried",
    expectedIntent: "intent", expectedCommit: "producer", commit: "", code: 1, diagnosed: true, stdoutEmpty: true,
    unchanged: true, stderr: probe.detail, repoExisted: true, repoExists: true }
  pure def checkProbe(a: Attempt): str = guardedRejection(probe, a, alias => alias)
  pure val read = t::inspect("table-16")
  pure val sample = List(entry(h::first, -8, t::v2, alias => alias), entry(h::extra, 8, t::v1, alias => alias))
  pure val ordered = { ...r::recorded, op: read.op, args: read.args, commit: "full", unchanged: true,
    reuseScope: "intent", intentReuseTable: { intent: "intent", genesis: "intent", previous: "basis", entries: sample } }
  pure def checkOrder(entries: List[r::IntentReuseEntry]): str =
    exactTable({ ...ordered, intentReuseTable: { ...ordered.intentReuseTable, entries: entries } }, read, "full", "basis", "intent", sample)
  pure val controlsPass = all {
    checkProbe(observed) == "rejected",
    checkProbe({ ...observed, unchanged: false }) == "storage_changed",
    checkProbe({ ...observed, expectedTable: "stale" }) == "wrong_table_guard",
    checkProbe({ ...observed, stderr: "request-intent-table-scale: ref is stale" }) == "wrong_diagnostic",
    checkOrder(sample) == "inspected",
    checkOrder(List(sample[1], sample[0])) == "wrong_table_order",
    checkOrder(List(sample[1])) == "wrong_table_entries"
  }
}
