// Bounded design: five constructions (two equal, one value change, one
// type change, one key change), up to two active rows, two bindings of double
// and one other intent. One update followed by a request and optional offline
// inspection. IDs stand for native records; framing, arithmetic and transfer
// implementation are outside this model. A failed write rolls back the batch.
module recorded_argument_maps_design {
  type Input = { key: int, source: int }
  type Attempt = { input: int, binding: int, intent: int, attempt: int, result: int, trace: int }
  type Ask = { input: int, binding: int, mode: str, pin: int, live: int, late: bool }
  type Decision = { input: int, binding: int, table: int, disposition: str, attempt: int }
  type State = { rows: int -> int, main: int, pending: int, decision: Decision, executions: int }
  type Edit = { op: str, key: int, attempt: int, late: bool }

  // 2 is computed by an earlier successful result; 1 is a literal.
  pure val inputs: int -> Input = Map(1 -> { key: 42, source: 11 }, 2 -> { key: 42, source: 12 },
    3 -> { key: 43, source: 13 }, 4 -> { key: 1042, source: 14 }, 5 -> { key: 2042, source: 15 })
  pure val attempts: int -> Attempt = Map(
    1 -> { input: 1, binding: 1, intent: 1, attempt: 1, result: 84, trace: 101 },
    2 -> { input: 2, binding: 2, intent: 1, attempt: 2, result: 84, trace: 102 },
    3 -> { input: 3, binding: 1, intent: 1, attempt: 3, result: 86, trace: 103 },
    4 -> { input: 3, binding: 3, intent: 2, attempt: 4, result: 86, trace: 104 })
  pure def scope(binding: int): int = if (binding == 3) 2 else 1
  pure val noDecision: Decision = { input: 0, binding: 0, table: 0, disposition: "", attempt: 0 }
  pure val initial: State = { rows: Map(42 -> 1), main: 70, pending: 0, decision: noDecision, executions: 4 }
  pure val query: Ask = { input: 2, binding: 2, mode: "try-selected", pin: 2, live: 2, late: false }
  pure val noop: Edit = { op: "", key: 0, attempt: 0, late: false }
  pure def table(s: State, pin: int): int -> int = if (pin == 1) initial.rows else if (pin == 2) s.rows
    else if (pin == 3) Map(42 -> 1, 43 -> 4) else Map()
  pure def choose(s: State, q: Ask): Decision = {
    val rows = table(s, q.pin)
    val key = inputs.get(q.input).key
    val consult = q.mode != "fresh"
    val hit = consult and rows.keys().contains(key)
    val valid = not(consult) or (q.live == q.pin and (q.pin == 0 or (
      scope(q.binding) == 1 and rows.keys().forall(k => attempts.get(rows.get(k)).intent == 1 and
        inputs.get(attempts.get(rows.get(k)).input).key == k))))
    if (not(valid) or (q.mode == "require-selected" and not(hit))) noDecision
    else { input: q.input, binding: q.binding, table: if (consult) q.pin else 0,
      disposition: if (hit) "reuse" else "pending", attempt: if (hit) rows.get(key) else 0 }
  }

  var repo: State
  var before: State
  var phase: str
  var edit: Edit
  var queryArgs: Ask
  var accepted: bool
  var report: Decision

  action progress(r: State, b: State, p: str, e: Edit, q: Ask, ok: bool, read: Decision): bool = all {
    repo' = r, before' = b, phase' = p, edit' = e, queryArgs' = q, accepted' = ok, report' = read
  }
  action init = all {
    repo' = initial, before' = initial, phase' = "ready", edit' = noop,
    queryArgs' = query, accepted' = false, report' = noDecision
  }
  action update(e: Edit): bool = {
    val present = repo.rows.keys().contains(e.key)
    val valid = if (e.op == "remove") present and e.attempt == 0
      else if (not(attempts.keys().contains(e.attempt))) false
      else { val a = attempts.get(e.attempt)
        a.intent == 1 and inputs.get(a.input).key == e.key and
          (if (e.op == "insert") not(present) and repo.rows.keys().size() < 2
           else present and repo.rows.get(e.key) != e.attempt) }
    val ok = valid and not(e.late)
    val rows = if (ok and e.op == "remove") repo.rows.keys().exclude(Set(e.key)).mapBy(k => repo.rows.get(k))
      else if (ok) repo.rows.put(e.key, e.attempt) else repo.rows
    progress({ ...repo, rows: rows }, repo, "edited", e, query, ok, noDecision)
  }
  action route(q: Ask): bool = {
    val d = choose(repo, q)
    val ok = not(q.late) and d != noDecision
    val after = if (not(ok)) repo else { ...repo, decision: d,
      pending: if (d.attempt == 0) q.input else 0,
      main: if (d.attempt == 0) repo.main else attempts.get(d.attempt).result }
    progress(after, repo, "routed", edit, q, ok, noDecision)
  }
  action inspect(forge: bool): bool = {
    val d = repo.decision
    val changed = if (forge) { ...d, attempt: if (d.attempt == 0) 1 else 0 } else d
    val verified = choose(repo, { ...queryArgs, live: d.table, pin: d.table, late: false })
    val ok = verified == changed
    progress(repo, repo, if (forge) "forged" else "offline", edit, queryArgs, ok, if (ok) verified else noDecision)
  }
  action step = if (phase == "ready") any {
    {
      nondet p = Set(("adopt", 42, 2), ("adopt", 42, 1), ("insert", 43, 3), ("insert", 43, 4),
        ("insert", 42, 2), ("remove", 42, 0), ("remove", 43, 0)).oneOf()
      nondet late = Bool.oneOf()
      update({ op: p._1, key: p._2, attempt: p._3, late: late })
    },
    progress(repo, repo, "edited", noop, query, false, noDecision)
  } else if (phase == "edited") {
    nondet i = inputs.keys().oneOf()
    nondet b = Set(1, 2, 3).oneOf()
    nondet mode = Set("fresh", "try-selected", "require-selected").oneOf()
    nondet pin = Set(0, 1, 2, 3).oneOf()
    nondet f = Set("", "stale", "late").oneOf()
    route({ input: i, binding: b, mode: mode, pin: pin, live: if (f == "stale") (pin + 1) % 4 else pin,
      late: f == "late" })
  } else if (phase == "routed" and accepted) {
    nondet forge = Bool.oneOf()
    inspect(forge)
  } else progress(repo, repo, "done", noop, query, false, noDecision)

  // Independent fixture oracle: map equality is independent of construction,
  // producing binding, trace and output. No routing step changes any attempt.
  invariant editOrRollback = phase != "edited" or {
    val adopt = edit == { op: "adopt", key: 42, attempt: 2, late: false }
    val insert = edit == { op: "insert", key: 43, attempt: 3, late: false }
    val remove = edit == { op: "remove", key: 42, attempt: 0, late: false }
    (accepted iff adopt or insert or remove) and repo == { ...initial,
      rows: if (adopt) Map(42 -> 2) else if (insert) Map(42 -> 1, 43 -> 3) else if (remove) Map() else initial.rows }
  }
  invariant typedDatumRouting = phase != "routed" or {
    val q = queryArgs
    val consult = q.mode != "fresh"
    val valid = not(consult) or (q.pin == q.live and (q.pin == 0 or (q.pin != 3 and q.binding != 3)))
    val a = if (not(consult)) 0 else if (Set(1, 2).contains(q.input)) {
      if (q.pin == 1) 1 else if (q.pin != 2 or not(before.rows.keys().contains(42))) 0 else before.rows.get(42)
    } else if (q.input == 3 and q.pin == 2 and before.rows.keys().contains(43)) 3 else 0
    val ok = valid and not(q.late) and (q.mode != "require-selected" or a != 0)
    (accepted iff ok) and (if (not(ok)) repo == before else repo == { ...before,
      main: if (a == 0) before.main else if (a == 3) 86 else 84, pending: if (a == 0) q.input else 0,
      decision: { input: q.input, binding: q.binding, table: if (consult) q.pin else 0,
        disposition: if (a == 0) "pending" else "reuse", attempt: a } })
  }
  invariant historicalProvenance = if (phase == "offline") accepted and repo == before and report == repo.decision and
    (report.attempt == 0 or { val producer = attempts.get(report.attempt)
      inputs.get(producer.input).key == inputs.get(report.input).key and repo.main == producer.result and producer.trace != 0 })
    else phase != "forged" or (not(accepted) and repo == before)

  observation computedUsesLiteral = phase == "offline" and report.input == 2 and report.binding == 2 and report.attempt == 1
  observation literalUsesComputed = phase == "offline" and report.input == 1 and report.binding == 1 and report.attempt == 2
  observation differentValue = phase == "routed" and accepted and queryArgs == { ...query, input: 3 } and repo.pending == 3
  observation differentType = phase == "routed" and accepted and queryArgs == { ...query, input: 4 } and repo.pending == 4
  observation differentKey = phase == "routed" and accepted and queryArgs == { ...query, input: 5 } and repo.pending == 5
  observation removed = phase == "routed" and accepted and queryArgs == query and repo.pending == 2
  observation poisonUnrelated = phase == "routed" and not(accepted) and queryArgs == { ...query, pin: 3, live: 3 }
  observation freshBypass = phase == "routed" and accepted and queryArgs == { ...query, pin: 3, live: 0, mode: "fresh" }
  observation rollback = phase == "routed" and not(accepted) and queryArgs == { ...query, late: true }
  observation forgedHit = phase == "forged" and not(accepted) and repo.decision.attempt != 0
}
