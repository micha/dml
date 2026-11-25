// Iteration 22: one composition, one downstream request and at most one
// downstream execution. Historical attempts and arithmetic are fixtures. Commit
// IDs model occurrences; return DAG and MAP IDs model content. Ref/create failures
// are single-transaction aborts. No concurrent workers or process lifecycle.
module recorded_composition_design {
  type Add = { q: int, t: int, r: int, outer: int, map: int, value: int }
  type Composition = { pin: int, parent: int, source: int, map: int }
  type Decision = { q: int, composition: Composition, selected: int, hit: bool }
  type Repo = { composition: Composition, decision: Decision, pending: bool,
    newAttempt: int, main: int, executions: int, getters: int }
  type Report = { requestedQ: int, requestedAdd: int, producingQ: int,
    producingAdd: int, attempt: int, result: int }

  // A fresh repeat retains the same complete return DAG (including trace). A
  // permutation creates another return DAG but yields the same downstream MAP.
  pure val adds = Map(
    1 -> { q: 11, t: 1, r: 21, outer: 31, map: 41, value: 42 },
    2 -> { q: 12, t: 2, r: 22, outer: 31, map: 41, value: 42 },
    3 -> { q: 13, t: 3, r: 23, outer: 33, map: 43, value: 42 },
    4 -> { q: 14, t: 4, r: 24, outer: 34, map: 44, value: 43 })
  pure val none: Composition = { pin: 0, parent: 0, source: 0, map: 0 }
  pure val noDecision: Decision = { q: 0, composition: none, selected: 0, hit: false }
  pure val noReport: Report = { requestedQ: 0, requestedAdd: 0, producingQ: 0,
    producingAdd: 0, attempt: 0, result: 0 }
  // One historical double execution: T=8, Q=18, R=28, using add T=1.
  pure val initial: Repo = { composition: none, decision: noDecision, pending: false,
    newAttempt: 0, main: 27, executions: 1, getters: 1 }

  pure def compose(t: int): Composition = {
    val add = adds.get(t)
    { pin: t, parent: t, source: add.outer, map: add.value }
  }
  pure def valid(c: Composition): bool = {
    if (adds.keys().contains(c.parent)) {
      val add = adds.get(c.parent)
      c.pin == c.parent and c.source == add.outer and c.map == add.value
    } else false
  }
  pure def graft(c: Composition, f: str): Composition =
    if (f == "parent-graft") { ...c, parent: if (c.parent == 1) 2 else 1 }
    else if (f == "source-graft") { ...c, source: if (c.source == 31) 33 else 31 }
    else c
  pure def route(c: Composition, mode: str, current: int, pin: int): Decision = {
    // 0 is absence, 8 is validated historical double, 5 a malformed chain,
    // 1 a valid but wrong-intent add attempt.
    val consult = mode != "fresh"
    val hit = consult and current == 8 and c.map == compose(1).map
    if (not(valid(c)) or (consult and (current != pin or not(Set(0, 8).contains(current))))
        or (mode == "require-selected" and not(hit))) noDecision
    else { q: 19, composition: c, selected: if (consult) current else 0, hit: hit }
  }

  var repo: Repo
  var before: Repo
  var phase: str
  var accepted: bool
  var expected: int
  var live: int
  var mode: str
  var fault: str
  var report: Report

  action advance(r: Repo, p: str, ok: bool, pin: int, ref: int, m: str, f: str, v: Report): bool = all {
    repo' = r, before' = repo, phase' = p, accepted' = ok, expected' = pin, live' = ref,
    mode' = m, fault' = f, report' = v
  }
  action init = all {
    repo' = initial, before' = initial, phase' = "ready", accepted' = false,
    expected' = 0, live' = 0, mode' = "", fault' = "", report' = noReport
  }
  action step = if (phase == "ready") {
    nondet pin = adds.keys().oneOf()
    nondet ref = Set(0, 1, 2, 3, 4, 5).oneOf()
    nondet f = Set("", "late").oneOf()
    val ok = pin == ref and f == ""
    advance(if (ok) { ...repo, composition: compose(pin) } else repo,
      "composed", ok, pin, ref, "", f, noReport)
  } else if (phase == "composed" and accepted) {
    nondet pin = Set(0, 1, 5, 8).oneOf()
    nondet ref = Set(0, 1, 5, 8).oneOf()
    nondet m = Set("fresh", "try-selected", "require-selected").oneOf()
    nondet f = Set("", "late", "parent-graft", "source-graft", "stale-composition", "pending-occupied").oneOf()
    val d = route(graft(repo.composition, f), m, ref, pin)
    val ok = d != noDecision and Set("", "parent-graft", "source-graft").contains(f)
    advance(if (ok) { ...repo, decision: d, pending: not(d.hit),
      main: if (d.hit) 28 else repo.main } else repo,
      "routed", ok, pin, ref, m, f, noReport)
  } else if (phase == "routed" and accepted and repo.pending) {
    nondet f = Set("", "late").oneOf()
    advance(if (f == "") { ...repo, newAttempt: 9, main: 29, executions: repo.executions + 1,
      getters: repo.getters + 1 } else repo, "worked", f == "", expected, live, mode, f, noReport)
  } else if ((phase == "routed" and accepted and repo.decision.hit) or (phase == "worked" and accepted)) {
    nondet f = Set("", "parent-graft", "source-graft", "original-graft").oneOf()
    val d = repo.decision
    val requested = graft(d.composition, f)
    val producing = if (d.hit) graft(compose(1), if (f == "original-graft") "parent-graft" else "")
      else graft(d.composition, if (f == "original-graft") "parent-graft" else "")
    val ok = valid(requested) and valid(producing)
    advance(repo, "offline", ok, expected, live, mode, f, if (ok) {
      requestedQ: d.q, requestedAdd: requested.parent, producingQ: if (d.hit) 18 else d.q,
      producingAdd: producing.parent, attempt: if (d.hit) 8 else repo.newAttempt, result: repo.main
    } else noReport)
  } else advance(repo, "done", false, expected, live, mode, fault, noReport)

  invariant compositionPublication = phase != "composed" or {
    val ok = expected == live and fault == ""
    (accepted iff ok) and repo == (if (ok) { ...before, composition: {
      pin: expected, parent: expected, source: if (expected <= 2) 31 else 30 + expected,
      map: if (expected == 4) 43 else 42 } } else before)
  }
  invariant decisionPublication = phase != "routed" or {
    val hit = mode != "fresh" and live == 8 and before.composition.parent != 4
    val ok = fault == "" and (mode == "fresh" or (expected == live and Set(0, 8).contains(live)))
      and (mode != "require-selected" or hit)
    (accepted iff ok) and repo == (if (ok) { ...before, pending: not(hit),
      main: if (hit) 28 else before.main, decision: {
      q: 19, composition: before.composition, selected: if (mode == "fresh") 0 else live, hit: hit } } else before)
  }
  invariant workPublication = phase != "worked" or {
    (accepted iff fault == "") and repo == (if (accepted) { ...before, newAttempt: 9,
      main: 29, executions: 2, getters: 2 } else before)
  }
  invariant offlineInspection = phase != "offline" or {
    val hit = repo.decision.hit
    val upstream = repo.composition.pin
    repo == before and (accepted iff fault == "") and repo.executions == (if (hit) 1 else 2)
      and repo.getters == repo.executions and report == (if (accepted) {
        requestedQ: 19, requestedAdd: upstream, producingQ: if (hit) 18 else 19,
        producingAdd: if (hit) 1 else upstream, attempt: if (hit) 8 else 9,
        result: if (hit) 28 else 29 } else noReport)
  }

  observation repeatedSourceReuse = phase == "offline" and accepted and report.requestedAdd == 2
    and report.producingAdd == 1 and adds.get(1).outer == adds.get(2).outer and adds.get(1).q != adds.get(2).q
  observation swappedSourceReuse = phase == "offline" and accepted and report.requestedAdd == 3
    and report.producingAdd == 1 and adds.get(1).map != adds.get(3).map
  observation valueMiss = phase == "offline" and accepted and report.requestedAdd == 4
    and report.producingAdd == 4 and mode == "try-selected" and live == 8
  observation absentSelectionMiss = phase == "worked" and accepted and mode == "try-selected" and live == 0
  observation freshIgnoresSelection = phase == "routed" and accepted and mode == "fresh" and live == 5
  observation sameDagParentGraft = phase == "offline" and not(accepted) and fault == "parent-graft"
    and repo.composition.pin == 2 and repo.decision.hit
  observation equalValueSourceGraft = phase == "offline" and not(accepted) and fault == "source-graft"
    and repo.composition.pin == 3 and repo.decision.hit
  observation originalGraft = phase == "offline" and not(accepted) and fault == "original-graft" and repo.decision.hit
  observation staleProducer = phase == "composed" and not(accepted) and expected == 2 and live == 1 and fault == ""
  observation lateComposition = phase == "composed" and not(accepted) and expected == live and fault == "late"
  observation staleComposition = phase == "routed" and not(accepted) and fault == "stale-composition"
  observation requireMiss = phase == "routed" and not(accepted) and mode == "require-selected"
    and repo.composition.pin == 4 and live == 8 and expected == 8 and fault == ""
  observation poisonedSelectionOnMiss = phase == "routed" and not(accepted) and mode == "try-selected"
    and repo.composition.pin == 4 and live == 5 and expected == 5 and fault == ""
  observation wrongIntentOnMiss = phase == "routed" and not(accepted) and mode == "try-selected"
    and repo.composition.pin == 4 and live == 1 and expected == 1 and fault == ""
  observation staleSelection = phase == "routed" and not(accepted) and mode == "try-selected"
    and live == 0 and expected == 8 and fault == ""
  observation lateDecision = phase == "routed" and not(accepted) and expected == 8 and live == 8
    and mode == "require-selected" and repo.composition.pin == 2 and fault == "late"
  observation occupiedHitPending = phase == "routed" and not(accepted) and expected == 8 and live == 8
    and mode == "require-selected" and repo.composition.pin == 2 and fault == "pending-occupied"
  observation lateWork = phase == "worked" and not(accepted) and repo.pending and fault == "late"
}
