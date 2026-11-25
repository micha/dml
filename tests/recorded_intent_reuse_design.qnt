// Intent-scoped scale reuse: two implementations, two intent lineages, and
// three exact (producer commit, signed factor) keys with a two-key table cap.
// Requests are (key, implementation); selections retain the producing request
// and attempt. Immutable IDs, side effects and ref pins are modeled; native
// framing, worker execution, transfer and collection are not.
module recorded_intent_reuse_design {
  type Intent = { genesis: int, implementation: int, reuse: bool }
  type Selection = { key: int, implementation: int, attempt: int, result: int }
  type Version = { basis: int, genesis: int, operation: str, key: int, selection: int }
  type Table = { genesis: int, rows: int -> int }
  type Edit = { basis: int, live: int, op: str, key: int, selection: int, selected: int, fault: str }
  type Query = { intent: int, override: int, key: int, mode: str, pin: int, live: int, fault: str }
  type Decision = { intent: int, override: int, key: int, implementation: int, mode: str, table: int, reason: str }
  type Route = { reason: str, selection: int }
  type Store = { tables: int -> Version, main: int, plan: (int, int), decision: Decision }

  pure val intents: int -> Intent = Map(
    1 -> { genesis: 1, implementation: 1, reuse: true },
    2 -> { genesis: 1, implementation: 2, reuse: true },
    3 -> { genesis: 3, implementation: 1, reuse: true },
    4 -> { genesis: 4, implementation: 2, reuse: false })
  pure val selections: int -> Selection = Map(
    101 -> { key: 11, implementation: 1, attempt: 201, result: 301 },
    102 -> { key: 11, implementation: 2, attempt: 202, result: 302 },
    103 -> { key: 12, implementation: 2, attempt: 203, result: 303 },
    104 -> { key: 13, implementation: 1, attempt: 204, result: 304 },
    105 -> { key: 11, implementation: 1, attempt: 201, result: 301 },
    106 -> { key: 12, implementation: 1, attempt: 0, result: 305 })
  pure val noRows: int -> int = Map()
  pure val invalid: Table = { genesis: 0, rows: noRows }
  pure val reject: Route = { reason: "", selection: 0 }
  pure val noDecision: Decision = { intent: 0, override: 0, key: 0, implementation: 0, mode: "", table: 0, reason: "" }
  pure def root(g: int): Version = { basis: 0, genesis: g, operation: "", key: 0, selection: 0 }
  pure def delta(b: int, op: str, k: int, s: int): Version =
    { basis: b, genesis: 0, operation: op, key: k, selection: s }
  // 14 inserts a row under a mismatched key. 15 tries to bury it by removal.
  pure val initial: Store = { main: 300, plan: (0, 0), decision: noDecision,
    tables: Map(10 -> root(1), 11 -> delta(10, "insert", 11, 101), 12 -> delta(11, "insert", 12, 103),
      13 -> root(3), 14 -> delta(11, "insert", 13, 103), 15 -> delta(14, "remove", 13, 0)) }
  pure val adopt: Edit = { basis: 12, live: 12, op: "adopt", key: 11, selection: 102, selected: 102, fault: "" }
  pure val remove: Edit = { basis: 20, live: 20, op: "remove", key: 11, selection: 0, selected: 0, fault: "" }
  pure val query: Query = { intent: 2, override: 0, key: 11, mode: "default", pin: 12, live: 12, fault: "" }

  pure def applyDelta(t: Table, v: Version): Table = {
    val present = t.rows.keys().contains(v.key)
    if (t == invalid or v.genesis != 0) invalid
    else if (v.operation == "remove") {
      if (not(present) or v.selection != 0) invalid
      else { ...t, rows: t.rows.keys().exclude(Set(v.key)).mapBy(k => t.rows.get(k)) }
    } else if (not(selections.keys().contains(v.selection))) invalid
    else {
      val s = selections.get(v.selection)
      val permitted = if (v.operation == "insert") not(present) and t.rows.keys().size() < 2
        else v.operation == "adopt" and present and selections.get(t.rows.get(v.key)).attempt != s.attempt
      if (permitted and s.attempt != 0 and s.key == v.key) { ...t, rows: t.rows.put(v.key, v.selection) }
      else invalid
    }
  }
  pure def readTable(r: Store, id: int): Table = {
    // Bound: root and four deltas (including an explicit reselection).
    val walk = List(0, 1, 2, 3, 4, 5).foldl((id, List()), (a, _) => {
      if (a._1 == 0 or not(r.tables.keys().contains(a._1))) a
      else { val v = r.tables.get(a._1) (v.basis, List(v).concat(a._2)) }
    })
    if (walk._1 != 0 or walk._2.length() == 0) invalid
    else {
      val v = walk._2[0]
      if (not(Set(1, 3, 4).contains(v.genesis)) or v != root(v.genesis)) invalid
      else walk._2.slice(1, walk._2.length()).foldl({ genesis: v.genesis, rows: noRows }, (t, d) => applyDelta(t, d))
    }
  }
  pure def requested(q: Query): int = if (q.override == 0) intents.get(q.intent).implementation else q.override
  pure def bypass(q: Query): bool = q.mode == "fresh" or (q.mode == "default" and not(intents.get(q.intent).reuse))
  pure def choose(r: Store, q: Query): Route = {
    if (bypass(q)) { reason: if (q.mode == "fresh") "override-fresh" else "default-execution", selection: 0 }
    else {
      val t = readTable(r, q.pin)
      val hit = t.rows.keys().contains(q.key)
      if (q.pin != q.live or (q.pin != 0 and t.genesis != intents.get(q.intent).genesis)) reject
      else if (q.mode == "reuse-selected" and not(hit)) reject
      else if (hit) { reason: if (q.mode == "reuse-selected") "override-selected-reuse" else "default-table-hit",
        selection: t.rows.get(q.key) }
      else { reason: if (q.pin == 0) "default-no-table" else "default-table-miss", selection: 0 }
    }
  }

  var repo: Store
  var before: Store
  var phase: str
  var edit: Edit
  var q: Query
  var accepted: bool
  var report: Route

  action progress(r: Store, b: Store, p: str, e: Edit, ask: Query, ok: bool, v: Route): bool = all {
    repo' = r, before' = b, phase' = p, edit' = e, q' = ask, accepted' = ok, report' = v
  }
  action init = all {
    repo' = initial, before' = initial, phase' = "ready", edit' = adopt, q' = query, accepted' = false, report' = reject
  }
  action update(r: Store, e: Edit, id: int, p: str): bool = {
    val v = delta(e.basis, e.op, e.key, e.selection)
    val ok = e.live == e.basis and (if (e.op == "remove") e.selected == 0 else e.selected == e.selection) and
      e.fault == "" and applyDelta(readTable(r, e.basis), v) != invalid
    progress(if (ok) { ...r, tables: r.tables.put(id, v) } else r, r, p, e, q, ok, reject)
  }
  action route(r: Store, ask: Query, p: str): bool = {
    val v = choose(r, ask)
    val ok = v != reject and ask.fault == ""
    val d: Decision = { intent: ask.intent, override: ask.override, key: ask.key, implementation: requested(ask),
      mode: ask.mode, table: if (bypass(ask)) 0 else ask.pin, reason: v.reason }
    val pending = { ...r, decision: d, plan: if (v.selection == 0) (ask.key, d.implementation) else (0, 0),
      main: if (v.selection == 0) r.main else selections.get(v.selection).result }
    progress(if (ok) pending else r, r, p, edit, ask, ok, reject)
  }
  action inspect(r: Store, d: Decision, live: int, p: str): bool = {
    val ask: Query = { intent: d.intent, override: d.override, key: d.key, mode: d.mode,
      pin: d.table, live: d.table, fault: "" }
    val v = choose(r, ask)
    val ok = v != reject and v.reason == d.reason and d.implementation == requested(ask) and
      (not(bypass(ask)) or d.table == 0)
    progress(r, r, p, edit, { ...ask, live: live }, ok, if (ok) v else reject)
  }

  action step = if (phase == "ready") any {
    {
      nondet b = Set(10, 11, 12, 13, 14, 15).oneOf()
      nondet s = selections.keys().oneOf()
      nondet op = Set("insert", "adopt", "remove").oneOf()
      nondet removalKey = Set(11, 12, 13).oneOf()
      nondet f = Set("", "basis-moved", "selection-moved", "occupied", "alias", "late").oneOf()
      val k = if (op == "remove") removalKey else selections.get(s).key
      val pin = if (op == "remove") 0 else s
      update(repo, { basis: b, live: if (f == "basis-moved") 0 else b, op: op, key: k, selection: pin,
        selected: if (f == "selection-moved") (if (pin == 0) s else 0) else pin,
        fault: if (Set("basis-moved", "selection-moved").contains(f)) "" else f }, 20, "edit")
    },
    {
      nondet pair = Set((1, 0), (2, 0), (2, 1), (3, 0), (4, 0), (4, 1)).oneOf()
      nondet k = Set(11, 12, 13).oneOf()
      nondet t = Set(0, 10, 11, 12, 13, 15).oneOf()
      nondet m = Set("default", "fresh", "reuse-selected").oneOf()
      nondet f = Set("", "moved", "occupied", "late").oneOf()
      route(repo, { intent: pair._1, override: pair._2, key: k, mode: m, pin: t,
        live: if (f == "moved") (if (t == 0) 12 else 0) else t,
        fault: if (f == "moved") "" else f }, "route")
    },
    update(repo, adopt, 20, "adopted")
  } else if (phase == "adopted") update(repo, remove, 21, "removed")
  else if (phase == "removed") any {
    route(repo, query, "old-hit"),
    route(repo, { ...query, intent: 1, pin: 20, live: 20 }, "adopted-hit"),
    route(repo, { ...query, intent: 1, key: 12, pin: 21, live: 21 }, "other-hit"),
    route(repo, { ...query, pin: 21, live: 21 }, "removed-miss"),
    route(repo, { ...query, pin: 21, live: 21, mode: "reuse-selected" }, "removed-explicit"),
    update(repo, { ...adopt, basis: 21, live: 21, op: "insert", selection: 101, selected: 101 }, 22, "reselected")
  } else if (Set("old-hit", "adopted-hit", "other-hit", "removed-miss").contains(phase)) any {
    inspect(repo, repo.decision, 0, "offline"),
    inspect(repo, repo.decision, 15, "offline"),
    inspect(repo, { ...repo.decision, implementation: 3 - repo.decision.implementation }, 0, "forged"),
    inspect(repo, { ...repo.decision, table: 15 }, 12, "forged")
  } else progress(repo, repo, "done", edit, q, false, reject)

  // Independent oracle for the bounded fixtures (not computed by readTable).
  pure val states = Map(10 -> noRows, 11 -> Map(11 -> 101), 12 -> Map(11 -> 101, 12 -> 103),
    13 -> noRows, 20 -> Map(11 -> 102, 12 -> 103), 21 -> Map(12 -> 103), 22 -> Map(11 -> 101, 12 -> 103))
  val old = if (states.keys().contains(edit.basis)) states.get(edit.basis) else noRows
  val editOk = states.keys().contains(edit.basis) and edit.live == edit.basis and edit.selected == edit.selection and
    edit.fault == "" and (
      if (edit.op == "remove") old.keys().contains(edit.key) and edit.selection == 0
      else edit.selection != 106 and
        (if (edit.op == "adopt") Set(11, 12).contains(edit.basis) and edit.selection == 102
         else not(old.keys().contains(edit.key)) and old.keys().size() != 2))
  invariant oneKeyOrRollback = not(Set("edit", "adopted", "removed", "reselected").contains(phase)) or {
    (accepted iff editOk) and (if (not(editOk)) repo == before else {
      val id = if (phase == "reselected") 22 else if (phase == "removed") 21 else 20
      val expected = if (edit.op == "remove") old.keys().exclude(Set(edit.key)).mapBy(k => old.get(k))
        else old.put(edit.key, edit.selection)
      repo == { ...before, tables: before.tables.put(id, delta(edit.basis, edit.op, edit.key, edit.selection)) } and
        readTable(repo, id).rows == expected
    })
  }

  val ignored = q.mode == "fresh" or (q.mode == "default" and q.intent == 4)
  val rows = if (states.keys().contains(q.pin)) states.get(q.pin) else noRows
  val hit = not(ignored) and rows.keys().contains(q.key)
  val scope = q.pin == 0 or (q.pin == 13 and q.intent == 3) or
    (Set(10, 11, 12, 20, 21).contains(q.pin) and Set(1, 2).contains(q.intent))
  val routeOk = q.fault == "" and (ignored or (q.live == q.pin and scope and (q.mode != "reuse-selected" or hit)))
  val impl = if (q.override != 0) q.override else if (Set(2, 4).contains(q.intent)) 2 else 1
  val reason = if (q.mode == "fresh") "override-fresh" else if (ignored) "default-execution"
    else if (q.mode == "reuse-selected") "override-selected-reuse" else if (hit) "default-table-hit"
    else if (q.pin == 0) "default-no-table" else "default-table-miss"
  invariant pinnedRouting = not(Set("route", "old-hit", "adopted-hit", "other-hit", "removed-miss", "removed-explicit").contains(phase)) or {
    (accepted iff routeOk) and (if (not(routeOk)) repo == before else repo == { ...before,
      main: if (hit) selections.get(rows.get(q.key)).result else before.main,
      plan: if (hit) (0, 0) else (q.key, impl),
      decision: { intent: q.intent, override: q.override, key: q.key, implementation: impl, mode: q.mode,
        table: if (ignored) 0 else q.pin, reason: reason } })
  }
  invariant inspectionKeepsProducer = if (phase == "offline") {
    repo == before and accepted and report == { reason: reason, selection: if (hit) rows.get(q.key) else 0 }
  } else phase != "forged" or (repo == before and not(accepted) and report == reject)
  invariant oldSnapshotsRetained = not(repo.tables.keys().contains(21)) or
    readTable(repo, 12).rows == states.get(12) and readTable(repo, 20).rows == states.get(20) and
      readTable(repo, 21).rows == states.get(21)

  observation v2UsesV1 = phase == "old-hit" and accepted and repo.decision.implementation == 2 and repo.main == 301
  observation v1UsesV2 = phase == "adopted-hit" and accepted and repo.decision.implementation == 1 and repo.main == 302
  observation unrelatedEntrySurvives = phase == "other-hit" and accepted and repo.main == 303
  observation removalFresh = phase == "removed-miss" and accepted and repo.plan == (11, 2)
  observation removalExplicitMiss = phase == "removed-explicit" and not(accepted)
  observation explicitReselection = phase == "reselected" and accepted and readTable(repo, 22).rows == states.get(22)
  observation offlineOriginalProducer = phase == "offline" and q.live == 0 and report.selection == 101
  observation offlineAdoptedProducer = phase == "offline" and q.live == 15 and report.selection == 102
  observation offlineRemovedMiss = phase == "offline" and q.pin == 21 and report.reason == "default-table-miss"
  observation rejectsForgedDecision = phase == "forged" and not(accepted)
  observation rejectSameAttempt = phase == "edit" and not(accepted) and edit.basis == 12 and edit.op == "adopt" and
    edit.selection == 105 and edit.live == 12 and edit.selected == 105 and edit.fault == ""
  observation rejectsResultOnly = phase == "edit" and not(accepted) and edit.basis == 11 and edit.op == "insert" and
    edit.selection == 106 and edit.live == 11 and edit.selected == 106 and edit.fault == ""
  observation rejectsRemoveAbsent = phase == "edit" and not(accepted) and edit == { ...remove, basis: 11, live: 11, key: 12 }
  observation removalRollback = phase == "edit" and not(accepted) and edit == { ...remove, basis: 12, live: 12, fault: "late" }
  observation requestRollback = phase == "route" and not(accepted) and q == { ...query, fault: "late" }
  observation rejectsPoisonedHistory = phase == "route" and not(accepted) and q == { ...query, pin: 15, live: 15 }
  observation wrongLineage = phase == "route" and not(accepted) and q == { ...query, intent: 3 }
  observation stalePin = phase == "route" and not(accepted) and q == { ...query, live: 0 }
  observation freshIgnoresPoison = phase == "route" and accepted and q.mode == "fresh" and q.pin == 15
  observation defaultExecutionIgnoresPoison = phase == "route" and accepted and q.intent == 4 and q.mode == "default" and q.pin == 15
  observation noTable = phase == "route" and accepted and q == { ...query, pin: 0, live: 0 }
}
