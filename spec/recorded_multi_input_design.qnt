// Multi-input reuse for recorded scale. Two implementation versions, two
// intent lineages, three v1 requests and one v2 request. The table cap is two
// in this model (sixteen in the example). IDs abstract content identity;
// framing, transfer, collection and worker execution are outside this model.
module recorded_multi_input_design {
  type Intent = { genesis: int, implementation: int, reuse: bool }
  type Selection = { key: int, implementation: int, attempt: int, result: int }
  type Version = { basis: int, intent: int, implementation: int, operation: str, key: int, selection: int }
  type Table = { valid: bool, intent: int, implementation: int, entries: int -> int }
  type Edit = { liveBasis: int, basis: int, liveSelection: int, selection: int, operation: str, obstacle: str }
  type Request = { intent: int, implementation: int, key: int, mode: str, live: int, pin: int, obstacle: str }
  type Decision = { intent: int, implementation: int, key: int, mode: str, table: int, reason: str }
  type Route = { reason: str, selection: int }
  type Store = { tables: int -> Version, main: int, plan: int, decision: Decision, output: int }

  pure val intents = Map(
    1 -> { genesis: 1, implementation: 1, reuse: true },
    2 -> { genesis: 1, implementation: 2, reuse: true },
    3 -> { genesis: 3, implementation: 1, reuse: true },
    4 -> { genesis: 4, implementation: 1, reuse: false })
  // 101 and 102 are distinct attempts for the same request and result.
  // 105 is another way to select the SAME attempt as 101. 106 has no attempt.
  // Different v1 input tuples may have the same result value (here 11/12).
  pure val selections: int -> Selection = Map(
    101 -> { key: 11, implementation: 1, attempt: 201, result: 301 },
    102 -> { key: 11, implementation: 1, attempt: 202, result: 301 },
    103 -> { key: 12, implementation: 1, attempt: 203, result: 302 },
    104 -> { key: 13, implementation: 1, attempt: 204, result: 303 },
    105 -> { key: 11, implementation: 1, attempt: 201, result: 301 },
    106 -> { key: 12, implementation: 1, attempt: 0, result: 302 },
    107 -> { key: 21, implementation: 2, attempt: 207, result: 307 })
  pure val noEntries: int -> int = Map()
  pure val invalid: Table = { valid: false, intent: 0, implementation: 0, entries: noEntries }
  pure val noDecision: Decision = { intent: 0, implementation: 0, key: 0, mode: "", table: 0, reason: "" }
  pure val reject: Route = { reason: "", selection: 0 }
  pure val empty: Version = { basis: 0, intent: 1, implementation: 1, operation: "", key: 0, selection: 0 }
  pure def delta(b: int, op: str, k: int, s: int): Version =
    { basis: b, intent: 0, implementation: 0, operation: op, key: k, selection: s }
  // 14 has a wrong nonmatching entry, and 15 tries to hide it later in ancestry.
  pure val initial: Store = { main: 300, plan: 0, decision: noDecision, output: 0,
    tables: Map(10 -> empty, 11 -> delta(10, "insert", 11, 101), 12 -> delta(11, "insert", 12, 103),
      13 -> { ...empty, implementation: 2 }, 14 -> delta(11, "insert", 13, 103),
      15 -> delta(14, "adopt", 11, 102)) }
  pure val normalEdit: Edit = { liveBasis: 12, basis: 12, liveSelection: 102, selection: 102,
    operation: "adopt", obstacle: "" }
  pure val normalRequest: Request = { intent: 1, implementation: 0, key: 11, mode: "default",
    live: 12, pin: 12, obstacle: "" }

  pure def entry(t: Table, key: int): int = if (t.entries.keys().contains(key)) t.entries.get(key) else 0
  pure def applyEdit(t: Table, v: Version): Table = {
    if (not(t.valid) or not(selections.keys().contains(v.selection))) invalid
    else {
      val s = selections.get(v.selection)
      val old = entry(t, v.key)
      val ok = s.attempt != 0 and s.implementation == t.implementation and s.key == v.key and
        ((v.operation == "insert" and old == 0 and t.entries.keys().size() < 2) or
          (v.operation == "adopt" and old != 0 and selections.get(old).attempt != s.attempt))
      if (ok) { ...t, entries: t.entries.put(v.key, v.selection) } else invalid
    }
  }
  pure def readRoot(v: Version): Table = {
    if (v.basis == 0 and intents.keys().contains(v.intent) and Set(1, 2).contains(v.implementation) and
      v.operation == "" and v.key == 0 and v.selection == 0)
      { valid: true, intent: v.intent, implementation: v.implementation, entries: noEntries }
    else invalid
  }
  // Unroll the finite history bound (genesis and up to four deltas).
  pure def readTable(r: Store, id: int): Table = {
    val walked = List(0, 1, 2, 3, 4).foldl((id, List()), (a, _) => {
      if (a._1 == 0 or not(r.tables.keys().contains(a._1))) a
      else {
        val v = r.tables.get(a._1)
        (v.basis, List(v).concat(a._2))
      }
    })
    if (walked._1 != 0 or walked._2.length() == 0) invalid
    else walked._2.slice(1, walked._2.length()).foldl(readRoot(walked._2[0]), (t, v) => applyEdit(t, v))
  }
  pure def implementation(q: Request): int =
    if (q.implementation == 0) intents.get(q.intent).implementation else q.implementation
  pure def ignoresTable(q: Request): bool = q.mode == "fresh" or (q.mode == "default" and not(intents.get(q.intent).reuse))
  pure def choose(r: Store, q: Request): Route = {
    val im = implementation(q)
    val t = if (ignoresTable(q)) invalid else readTable(r, q.pin)
    val selected = entry(t, q.key)
    if (not(Set(1, 2).contains(im)) or q.key / 10 != im) reject
    else if (q.mode == "fresh") { reason: "override-fresh", selection: 0 }
    else if (ignoresTable(q)) { reason: "default-execution", selection: 0 }
    else if (q.pin != q.live or (q.pin != 0 and (not(t.valid) or t.implementation != im or
      intents.get(t.intent).genesis != intents.get(q.intent).genesis))) reject
    else if (q.mode == "reuse-selected") {
      if (selected == 0) reject else { reason: "override-selected-reuse", selection: selected }
    } else if (selected != 0) { reason: "default-table-hit", selection: selected }
    else { reason: if (q.pin == 0) "default-no-table" else "default-table-miss", selection: 0 }
  }

  var repo: Store
  var before: Store
  var phase: str
  var edit: Edit
  var request: Request
  var accepted: bool
  var report: Route

  action progress(r: Store, b: Store, p: str, e: Edit, q: Request, ok: bool, v: Route): bool = all {
    repo' = r, before' = b, phase' = p, edit' = e, request' = q, accepted' = ok, report' = v
  }
  action init = all {
    repo' = initial, before' = initial, phase' = "ready", edit' = normalEdit,
    request' = normalRequest, accepted' = false, report' = reject
  }
  action update(r: Store, e: Edit, p: str): bool = {
    val v = delta(e.basis, e.operation, selections.get(e.selection).key, e.selection)
    val ok = e.basis == e.liveBasis and e.selection == e.liveSelection and e.obstacle == "" and
      r.output == 0 and applyEdit(readTable(r, e.basis), v).valid
    val pending = { ...r, output: 20, tables: r.tables.put(20, v) }
    progress(if (ok) pending else r, r, p, e, request, ok, reject)
  }
  action route(r: Store, q: Request, p: str): bool = {
    val v = choose(r, q)
    val ok = v != reject and q.obstacle == ""
    val decision: Decision = { intent: q.intent, implementation: q.implementation, key: q.key, mode: q.mode,
      table: if (ignoresTable(q)) 0 else q.pin, reason: v.reason }
    val pending = { ...r, decision: decision, plan: if (v.selection == 0) q.key else 0,
      main: if (v.selection == 0) r.main else selections.get(v.selection).result }
    progress(if (ok) pending else r, r, p, edit, q, ok, reject)
  }
  action inspect(r: Store, d: Decision, live: int, p: str): bool = {
    val q = { ...normalRequest, intent: d.intent, implementation: d.implementation, key: d.key,
      mode: d.mode, live: d.table, pin: d.table }
    val v = choose(r, q)
    val ok = v != reject and d.reason == v.reason and (not(ignoresTable(q)) or d.table == 0)
    // Store the irrelevant live ref in the observation to exercise moved/deleted refs.
    progress(r, r, p, edit, { ...q, live: live }, ok, if (ok) v else reject)
  }

  action step = if (phase == "ready") any {
    {
      nondet basis = Set(10, 11, 12, 13, 14, 15).oneOf()
      nondet selection = selections.keys().oneOf()
      nondet op = Set("insert", "adopt").oneOf()
      nondet obstacle = Set("", "basis-moved", "selection-moved", "occupied", "alias", "late").oneOf()
      val e = { basis: basis, liveBasis: if (obstacle == "basis-moved") 0 else basis,
        selection: selection, liveSelection: if (obstacle == "selection-moved") 0 else selection,
        operation: op, obstacle: if (Set("basis-moved", "selection-moved", "occupied").contains(obstacle)) "" else obstacle }
      update({ ...repo, output: if (obstacle == "occupied") 15 else 0 }, e, "edit")
    },
    {
      nondet ip = Set((1, 0), (2, 0), (2, 1), (3, 0), (4, 0)).oneOf()
      nondet k = Set(11, 12, 13, 21).oneOf()
      nondet t = Set(0, 10, 11, 12, 13, 14, 15).oneOf()
      nondet mode = Set("default", "fresh", "reuse-selected").oneOf()
      nondet obstacle = Set("", "moved", "alias", "occupied-plan", "occupied-decision", "late").oneOf()
      route(repo, { intent: ip._1, implementation: ip._2, key: k, mode: mode, pin: t,
        live: if (obstacle == "moved") (if (t == 0) 12 else 0) else t,
        obstacle: if (obstacle == "moved") "" else obstacle }, "route")
    },
    update(repo, normalEdit, "adopted")
  } else if (phase == "adopted") any {
    route(repo, { ...normalRequest, live: 20, pin: 20 }, "new-row"),
    route(repo, { ...normalRequest, live: 20, pin: 20, key: 12 }, "other-row"),
    route(repo, normalRequest, "old-branch")
  } else if (Set("new-row", "other-row", "old-branch").contains(phase)) any {
    inspect(repo, repo.decision, 0, "offline"),
    inspect(repo, repo.decision, 15, "offline"),
    inspect({ ...repo, decision: { ...repo.decision, table: 14 } }, { ...repo.decision, table: 14 }, 12, "forged"),
    inspect({ ...repo, decision: { ...repo.decision, reason: "default-table-miss" } },
      { ...repo.decision, reason: "default-table-miss" }, 12, "forged")
  } else progress(repo, repo, "done", edit, request, false, reject)

  // Independent scenario oracle: prior valid bounded tables, not readTable.
  pure val original = Map(10 -> noEntries, 11 -> Map(11 -> 101), 12 -> Map(11 -> 101, 12 -> 103), 13 -> noEntries)
  pure def oldRows(id: int): int -> int = if (original.keys().contains(id)) original.get(id) else noEntries
  val baseRows = oldRows(edit.basis)
  val candidate = selections.get(edit.selection)
  val editPinOk = edit.basis == edit.liveBasis and edit.selection == edit.liveSelection
  val editValid = original.keys().contains(edit.basis) and candidate.attempt != 0 and
    (edit.basis == 13 iff edit.selection == 107) and
    (if (edit.operation == "insert") not(baseRows.keys().contains(candidate.key)) and edit.basis != 12
     else candidate.key == 11 and Set(11, 12).contains(edit.basis) and edit.selection == 102)
  invariant exactOneKeyUpdate = not(Set("edit", "adopted").contains(phase)) or {
    val ok = editPinOk and editValid and edit.obstacle == "" and before.output == 0
    (accepted iff ok) and (if (not(ok)) repo == before else
      repo == { ...before, output: 20, tables: before.tables.put(20,
        delta(edit.basis, edit.operation, candidate.key, edit.selection)) } and
      readTable(repo, 20).entries == baseRows.put(candidate.key, edit.selection))
  }

  val useImpl = if (request.implementation != 0) request.implementation else if (request.intent == 2) 2 else 1
  val bypass = request.mode == "fresh" or (request.intent == 4 and request.mode == "default")
  val scopeOk = request.pin == 0 or (original.keys().contains(request.pin) and
    Set(1, 2).contains(request.intent) and (request.pin == 13 iff useImpl == 2))
  val rows = oldRows(request.pin)
  val hit = not(bypass) and rows.keys().contains(request.key)
  val routeValid = (if (useImpl == 1) request.key != 21 else request.key == 21) and
    (bypass or (request.live == request.pin and scopeOk and (request.mode != "reuse-selected" or hit)))
  val expectedReason = if (request.mode == "fresh") "override-fresh" else if (bypass) "default-execution"
    else if (request.mode == "reuse-selected") "override-selected-reuse" else if (hit) "default-table-hit"
    else if (request.pin == 0) "default-no-table" else "default-table-miss"
  invariant exactRouting = phase != "route" or {
    val ok = routeValid and request.obstacle == ""
    (accepted iff ok) and if (not(ok)) repo == before else repo == { ...before,
      main: if (hit) selections.get(rows.get(request.key)).result else before.main,
      plan: if (hit) 0 else request.key,
      decision: { intent: request.intent, implementation: request.implementation, key: request.key,
        mode: request.mode, table: if (bypass) 0 else request.pin, reason: expectedReason } }
  }
  invariant branchIsolation = not(Set("new-row", "other-row", "old-branch").contains(phase)) or {
    accepted and repo.tables == before.tables and repo.plan == 0 and repo.decision.reason == "default-table-hit" and
      readTable(repo, 12).entries == Map(11 -> 101, 12 -> 103) and
      readTable(repo, 20).entries == Map(11 -> 102, 12 -> 103) and
      repo.decision.table == (if (phase == "old-branch") 12 else 20) and
      repo.main == (if (phase == "other-row") 302 else 301)
  }
  invariant inspectPinned = if (phase == "offline") {
    val d = before.decision
    val s = if (d.key == 12) 103 else if (d.table == 20) 102 else 101
    repo == before and accepted and report == { reason: "default-table-hit", selection: s }
  } else phase != "forged" or (repo == before and not(accepted) and report == reject)

  observation insertSecond = phase == "edit" and accepted and edit.basis == 11 and edit.selection == 103
  observation rejectAtCap = phase == "edit" and not(accepted) and editPinOk and edit.basis == 12 and
    edit.selection == 104 and edit.operation == "insert" and edit.obstacle == "" and before.output == 0
  observation rejectSameAttempt = phase == "edit" and not(accepted) and editPinOk and edit.basis == 12 and
    edit.selection == 105 and edit.operation == "adopt" and edit.obstacle == "" and before.output == 0
  observation rejectResultOnly = phase == "edit" and not(accepted) and editPinOk and edit.basis == 11 and
    edit.selection == 106 and edit.operation == "insert" and edit.obstacle == "" and before.output == 0
  observation updateRollsBack = phase == "edit" and not(accepted) and editValid and edit.obstacle == "late"
  observation rejectMovedTable = phase == "route" and not(accepted) and not(bypass) and scopeOk and
    request.pin == 12 and request.live == 0 and request.key == 11 and request.intent == 1
  observation absentVsMiss = phase == "route" and accepted and repo.decision.reason == "default-no-table"
  observation unmatchedExactKey = phase == "route" and accepted and repo.decision.reason == "default-table-miss" and
    request.pin == 12 and request.key == 13
  observation explicitNoFallback = phase == "route" and not(accepted) and request.mode == "reuse-selected" and
    request.pin == 12 and request.live == 12 and request.intent == 1 and request.key == 13 and request.obstacle == ""
  observation hitSecond = phase == "other-row" and accepted
  observation freshIgnoresBadTable = phase == "route" and accepted and request.mode == "fresh" and request.pin == 15
  observation defaultExecuteIgnoresBadTable = phase == "route" and accepted and request.intent == 4 and
    request.mode == "default" and request.pin == 15
  observation rejectsBuriedMalformedRow = phase == "route" and not(accepted) and request.intent == 1 and
    request.mode == "default" and request.pin == 15 and request.live == 15 and request.key == 11 and request.obstacle == ""
  observation crossVersionRejects = phase == "route" and not(accepted) and request.intent == 2 and
    request.implementation == 0 and request.key == 21 and request.pin == 12 and request.live == 12 and
    request.mode == "default" and request.obstacle == ""
  observation explicitOldUnderPromotion = phase == "route" and accepted and request.intent == 2 and
    request.implementation == 1 and repo.decision.reason == "default-table-hit"
  observation requestRollsBack = phase == "route" and not(accepted) and routeValid and hit and request.obstacle == "late"
  observation offlineOldAttempt = phase == "offline" and accepted and request.live == 15 and report.selection == 101
  observation offlineNewAttempt = phase == "offline" and accepted and request.live == 0 and report.selection == 102
  observation rejectsForgedDecision = phase == "forged" and not(accepted)
}
