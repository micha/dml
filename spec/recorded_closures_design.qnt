// Iteration 23. Three retained default snapshots/captures, two invocation
// MAPs (swapped inputs with equal sum), one old successful attempt, at most
// one new request and execution per path. IDs stand for immutable content
// or occurrences as indicated. Single-writer transactions; no process model.
module recorded_closures_design {
  type Env = { source: int, scale: int, getter: int }
  type Capture = { basis: int, env: Env, key: int }
  type Decision = { q: int, capture: Capture, inputs: int, selected: int, hit: bool }
  type Attempt = { t: int, q: int, capture: Capture, getter: int, result: int, value: int }
  type Repo = { defaults: int, capture: Capture, decision: Decision, pending: bool,
    attempt: Attempt, main: int, executions: int, getters: int }
  type Report = { request: Decision, producer: Attempt }

  // Fixed intent and builtin func URIs: the only varying key field is the
  // I64 scale datum. Exact sources and equivalent getter versions are not keys.
  pure val envs = Map(1 -> { source: 11, scale: 2, getter: 1 },
    2 -> { source: 12, scale: 2, getter: 2 }, 3 -> { source: 13, scale: 3, getter: 2 })
  pure val noEnv: Env = { source: 0, scale: 0, getter: 0 }
  pure val noCapture: Capture = { basis: 0, env: noEnv, key: 0 }
  pure val noDecision: Decision = { q: 0, capture: noCapture, inputs: 0, selected: 0, hit: false }
  pure val noAttempt: Attempt = { t: 0, q: 0, capture: noCapture, getter: 0, result: 0, value: 0 }
  pure val noReport: Report = { request: noDecision, producer: noAttempt }
  pure def capture(basis: int): Capture = {
    val env = envs.get(basis)
    { basis: basis, env: env, key: env.scale }
  }
  pure val historical: Attempt = { t: 8, q: 1, capture: capture(1), getter: 1, result: 18, value: 84 }
  pure def valid(c: Capture): bool = if (envs.keys().contains(c.basis)) {
    c.env == envs.get(c.basis) and c.key == c.env.scale
  } else false
  pure def graft(c: Capture, f: str): Capture =
    if (f == "source-graft") { ...c, env: { ...c.env, source: if (c.env.source == 11) 12 else 11 } }
    else if (f == "binding-graft") { ...c, env: { ...c.env, getter: 3 - c.env.getter } }
    else if (f == "key-graft") { ...c, key: 5 - c.key }
    else c
  pure def selected(t: int): Attempt = if (t == 8) historical
    else { ...historical, t: t, capture: graft(historical.capture, "source-graft") }
  pure def route(c: Capture, m: str, live: int, expected: int, inputs: int, repeat: bool): Decision = {
    val consult = m != "fresh"
    val past = selected(live)
    val hit = consult and live != 0 and c.key == past.capture.key and inputs == 41
    val q = if (repeat and c.basis == 1 and inputs == 41) 1 else 2
    if (not(valid(c)) or (consult and (live != expected or (live != 0 and not(valid(past.capture)))))
        or (m == "require-selected" and not(hit)) or (hit and q == past.q)) noDecision
    else { q: q, capture: c, inputs: inputs, selected: if (consult) live else 0, hit: hit }
  }
  pure def initial(d: int): Repo = { defaults: d, capture: noCapture, decision: noDecision,
    pending: false, attempt: noAttempt, main: 19, executions: 1, getters: 2 }

  var repo: Repo
  var before: Repo
  var phase: str
  var accepted: bool
  var pin: int
  var live: int
  var inputs: int
  var repeat: bool
  var mode: str
  var fault: str
  var report: Report

  action save(r: Repo, p: str, ok: bool, e: int, l: int, i: int, a: bool, m: str, f: str, v: Report): bool = all {
    repo' = r, before' = repo, phase' = p, accepted' = ok, pin' = e, live' = l,
    inputs' = i, repeat' = a, mode' = m, fault' = f, report' = v
  }
  action init = {
    nondet d = envs.keys().oneOf()
    all { repo' = initial(d), before' = initial(d), phase' = "ready", accepted' = false,
      pin' = 0, live' = 0, inputs' = 0, repeat' = false, mode' = "", fault' = "", report' = noReport }
  }
  action step = if (phase == "ready") {
    nondet e = envs.keys().oneOf()
    nondet f = Set("", "late", "source-graft", "binding-graft").oneOf()
    val c = graft(capture(e), f)
    val ok = e == repo.defaults and valid(c) and f != "late"
    save(if (ok) { ...repo, capture: c } else repo, "captured", ok, e, repo.defaults, 0, false, "", f, noReport)
  } else if (phase == "captured" and accepted) {
    nondet d = Set(repo.defaults, 3).oneOf()
    save({ ...repo, defaults: d }, "promoted", true, pin, d, 0, false, "", "", noReport)
  } else if (phase == "promoted") {
    // 0 absence, 8 fully valid history, 9 same role but altered original capture.
    nondet ref = Set(0, 8, 9).oneOf()
    nondet e = Set(0, 8, 9).oneOf()
    nondet i = Set(41, 42).oneOf()
    nondet a = Set(false, true).oneOf()
    nondet m = Set("fresh", "try-selected", "require-selected").oneOf()
    nondet f = Set("", "late", "stale-closure").oneOf()
    val d = route(repo.capture, m, ref, e, i, a)
    val ok = d != noDecision and f == ""
    save(if (ok) { ...repo, decision: d, pending: not(d.hit),
      main: if (d.hit) historical.result else repo.main } else repo, "routed", ok, e, ref, i, a, m, f, noReport)
  } else if (phase == "routed" and accepted and repo.pending) {
    nondet f = Set("", "late").oneOf()
    val d = repo.decision
    val c = d.capture
    val t = { t: 7, q: d.q, capture: c, getter: c.env.getter, result: 17, value: 42 * c.env.scale }
    save(if (f == "") { ...repo, attempt: t, main: t.result, executions: 2, getters: 4 } else repo,
      "worked", f == "", pin, live, inputs, repeat, mode, f, noReport)
  } else if ((phase == "routed" and accepted and repo.decision.hit) or (phase == "worked" and accepted)) {
    nondet f = Set("", "source-graft", "binding-graft", "key-graft", "original-graft").oneOf()
    val d = repo.decision
    val t = if (d.hit) historical else repo.attempt
    val request = { ...d, capture: graft(d.capture, f) }
    val producer = { ...t, capture: graft(t.capture, if (f == "original-graft") "source-graft" else "") }
    val ok = valid(request.capture) and valid(producer.capture)
    save(repo, "offline", ok, pin, live, inputs, repeat, mode, f,
      if (ok) { request: request, producer: producer } else noReport)
  } else save(repo, "done", false, pin, live, inputs, repeat, mode, fault, noReport)

  invariant capturePublication = phase != "captured" or {
    val ok = pin == live and fault == ""
    (accepted iff ok) and repo == (if (ok) { ...before, capture: capture(pin) } else before)
  }
  invariant promotionIsNotRecapture = phase != "promoted" or
    repo == { ...before, defaults: live }
  invariant decisionPublication = phase != "routed" or {
    val hit = live == 8 and mode != "fresh" and before.capture.basis <= 2 and inputs == 41
    val same = repeat and before.capture.basis == 1 and inputs == 41
    val ok = fault == "" and (mode == "fresh" or (live == pin and Set(0, 8).contains(live)))
      and (mode != "require-selected" or hit) and not(hit and same)
    (accepted iff ok) and repo == (if (ok) { ...before, pending: not(hit),
      main: if (hit) 18 else before.main, decision: { q: if (same) 1 else 2,
        capture: before.capture, inputs: inputs, selected: if (mode == "fresh") 0 else live, hit: hit } } else before)
  }
  invariant workUsesCapture = phase != "worked" or {
    val b = before.capture.basis
    (accepted iff fault == "") and repo == (if (accepted) { ...before, main: 17,
      executions: 2, getters: 4, attempt: { t: 7, q: before.decision.q, capture: capture(b),
      getter: if (b == 1) 1 else 2, result: 17, value: if (b == 3) 126 else 84 } } else before)
  }
  invariant offlinePreservesBothChains = phase != "offline" or {
    val hit = repo.decision.hit
    repo == before and (accepted iff fault == "") and repo.executions == (if (hit) 1 else 2)
      and repo.getters == 2 * repo.executions and report == (if (accepted) {
        request: repo.decision, producer: if (hit) historical else repo.attempt } else noReport)
  }

  observation oldAfterPromotion = phase == "offline" and accepted and not(report.request.hit)
    and repo.defaults == 3 and report.producer.getter == 1 and report.producer.value == 84
  observation oldHitAfterPromotion = phase == "offline" and accepted and report.request.hit
    and repo.defaults == 3 and report.request.capture.basis == 1
  observation equivalentNewCaptureHit = phase == "offline" and accepted and report.request.hit
    and report.request.capture.basis == 2 and report.producer.capture.basis == 1
  observation equivalentNewCaptureFresh = phase == "offline" and accepted and mode == "fresh"
    and report.producer.capture.basis == 2 and report.producer.getter == 2 and report.producer.value == 84
  observation changedScaleMiss = phase == "offline" and accepted and mode == "try-selected" and live == 8
    and report.request.inputs == 41 and report.producer.value == 126
  observation fullMapMiss = phase == "worked" and accepted and repo.attempt.capture.basis == 2
    and mode == "try-selected" and live == 8 and inputs == 42 and repo.attempt.value == 84
  observation fullMapRequireMiss = phase == "routed" and not(accepted) and mode == "require-selected"
    and repo.capture.basis == 1 and live == 8 and pin == 8 and inputs == 42 and fault == ""
  observation absentSelection = phase == "routed" and accepted and mode == "try-selected" and live == 0
  observation freshIgnoresPoison = phase == "routed" and accepted and mode == "fresh" and live == 9
  observation poisonOnScaleMismatch = phase == "routed" and not(accepted) and mode == "try-selected"
    and repo.capture.basis == 3 and inputs == 41 and live == 9 and pin == 9 and fault == ""
  observation staleDefaults = phase == "captured" and not(accepted) and pin != live and fault == ""
  observation lateCapture = phase == "captured" and not(accepted) and pin == live and fault == "late"
  observation staleClosure = phase == "routed" and not(accepted) and mode == "fresh" and fault == "stale-closure"
  observation staleSelection = phase == "routed" and not(accepted) and mode == "try-selected"
    and live == 0 and pin == 8 and fault == ""
  observation requireMiss = phase == "routed" and not(accepted) and mode == "require-selected"
    and repo.capture.basis == 3 and inputs == 41 and live == 8 and pin == 8 and fault == ""
  observation duplicateRequest = phase == "routed" and not(accepted) and mode == "require-selected"
    and repo.capture.basis == 1 and inputs == 41 and live == 8 and pin == 8 and repeat and fault == ""
  observation lateHit = phase == "routed" and not(accepted) and mode == "require-selected"
    and repo.capture.basis == 2 and inputs == 41 and live == 8 and pin == 8 and fault == "late"
  observation lateWork = phase == "worked" and not(accepted) and fault == "late"
  observation equalScaleSourceGraft = phase == "offline" and not(accepted) and fault == "source-graft"
    and repo.capture.basis == 2 and repo.decision.hit
  observation equivalentBindingGraft = phase == "offline" and not(accepted) and fault == "binding-graft"
    and repo.decision.hit
  observation keyGraft = phase == "offline" and not(accepted) and fault == "key-graft" and repo.decision.hit
  observation originalGraft = phase == "offline" and not(accepted) and fault == "original-graft" and repo.decision.hit
}
