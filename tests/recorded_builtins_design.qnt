// Iteration 21 design, not an implementation test. Bounded to one choice
// promotion, one direct internal call OR one new ordinary request, one
// historical selection and at most one fresh execution. IDs abstract immutable
// native records. Argument ordering, types and arithmetic are fixture constants;
// TLC checks routing, exact source links and publication, not native encoding.
module recorded_builtins_design {
  type Input = { mapValue: int, containerValue: int, source: int }
  type Call = { func: int, binding: int, args: int, source: int, value: int }
  type Request = { input: int, choice: int, override: int, binding: int, mode: str, pin: int }
  type Decision = { request: Request, attempt: int }
  type Attempt = { input: int, binding: int, result: int, trace: List[Call] }
  type Repo = { live: int, direct: Call, decision: Decision, pending: bool, main: int,
    produced: Attempt, executions: int }

  // Input 2 is equal by value but has a different exact source edge. Input 3
  // changes the collection value. map/get versions 1 and 2 deliberately agree.
  pure val inputs = Map(1 -> { mapValue: 41, containerValue: 71, source: 11 },
    2 -> { mapValue: 41, containerValue: 71, source: 12 },
    3 -> { mapValue: 42, containerValue: 72, source: 13 })
  pure val noCall: Call = { func: 0, binding: 0, args: 0, source: 0, value: 0 }
  pure val noRequest: Request = { input: 0, choice: 0, override: 0, binding: 0, mode: "", pin: 0 }
  pure val noDecision: Decision = { request: noRequest, attempt: 0 }
  pure val noAttempt: Attempt = { input: 0, binding: 0, result: 0, trace: [] }
  pure val old: Attempt = { input: 1, binding: 1, result: 42, trace: [
    { func: 1, binding: 1, args: 101, source: 11, value: 71 },
    { func: 2, binding: 3, args: 201, source: 1101, value: 42 }] }
  pure val initial: Repo = { live: 1, direct: noCall, decision: noDecision, pending: false,
    main: 0, produced: noAttempt, executions: 1 }

  // Builtin func/source table: 1/2 are exact map/get versions, 3 is list/get,
  // 4 map/empty, 5 map/insert. A binding for another func is not a fallback.
  pure def backend(f: int, b: int): bool = if (f == 1) Set(1, 2).contains(b)
    else b == f + 1 and Set(2, 3, 4).contains(f)
  pure def call(f: int, b: int, i: int): Call = {
    val input = inputs.get(i)
    { func: f, binding: b, args: 100 * f + (if (f == 3) 1 else i),
      source: if (f == 3) 0 else input.source,
      value: if (f == 1) input.containerValue else if (f == 2) 6 else if (f == 3) 70 else 71 }
  }
  pure def attempt(q: Request): Attempt = {
    val getter = call(1, q.binding, q.input)
    val answer = if (getter.value == 71) 42 else 43
    { input: q.input, binding: q.binding, result: answer,
      trace: [getter, { func: 2, binding: 3, args: 200 + q.input,
        source: 1000 * getter.binding + getter.args, value: answer }] }
  }
  pure def resolved(q: Request): int = if (q.override == 0) q.choice else q.override
  pure def route(q: Request, selection: int): Decision = {
    val b = resolved(q)
    val consult = q.mode != "fresh"
    val hit = consult and q.pin == 1 and inputs.get(q.input).mapValue == inputs.get(old.input).mapValue
    if (not(backend(1, b)) or (consult and (q.pin != selection or q.pin == 2))
        or (q.mode == "require-selected" and not(hit))) noDecision
    else { request: { ...q, binding: b, pin: if (consult) q.pin else 0 }, attempt: if (hit) 1 else 0 }
  }

  var repo: Repo
  var before: Repo
  var phase: str
  var accepted: bool
  var asked: Request
  var selection: int
  var offered: Call
  var fault: str
  var report: Attempt

  action advance(r: Repo, p: str, ok: bool, q: Request, s: int, c: Call, f: str, a: Attempt): bool = all {
    repo' = r, before' = repo, phase' = p, accepted' = ok, asked' = q,
    selection' = s, offered' = c, fault' = f, report' = a
  }
  action init = all {
    repo' = initial, before' = initial, phase' = "ready", accepted' = false, asked' = noRequest,
    selection' = 0, offered' = noCall, fault' = "", report' = noAttempt
  }
  action step = if (phase == "ready") {
    nondet promote = Bool.oneOf()
    advance({ ...repo, live: if (promote) 2 else 1 }, "choose", true, noRequest, 0, noCall, "", noAttempt)
  } else if (phase == "choose") any {
    {
      nondet f = Set(1, 2, 3, 4).oneOf()
      nondet override = Set(0, 1, 2, 3, 4, 5, 99).oneOf()
      nondet i = Set(1, 2).oneOf()
      nondet problem = Set("", "graft", "late", "invalid-arguments").oneOf()
      val b = if (override == 0) (if (f == 1) repo.live else f + 1) else override
      val exact = call(f, b, i)
      val supplied = if (problem == "graft" and f != 3)
        { ...exact, source: inputs.get(3 - i).source } else exact
      val ok = backend(f, b) and problem != "late" and problem != "invalid-arguments" and supplied == exact
      advance(if (ok) { ...repo, direct: exact } else repo, "direct", ok, noRequest, 0, supplied, problem, noAttempt)
    },
    {
      nondet i = inputs.keys().oneOf()
      nondet choice = Set(1, repo.live).oneOf()
      nondet override = Set(0, 1, 2, 3, 99).oneOf()
      nondet mode = Set("fresh", "try-selected", "require-selected").oneOf()
      nondet pin = Set(0, 1, 2).oneOf()
      nondet current = Set(0, 1, 2).oneOf()
      nondet late = Bool.oneOf()
      val q = { input: i, choice: choice, override: override, binding: 0, mode: mode, pin: pin }
      val d = route(q, current)
      val ok = not(late) and d != noDecision
      val after = if (not(ok)) repo else { ...repo, decision: d,
        main: if (d.attempt == 1) old.result else 0, pending: d.attempt == 0 }
      advance(after, "routed", ok, q, current, noCall, if (late) "late" else "", noAttempt)
    }
  } else if (phase == "routed" and accepted and repo.pending) {
    nondet f = Set("", "late", "caught-error").oneOf()
    val a = attempt(repo.decision.request)
    advance(if (f == "") { ...repo, pending: false, produced: a, main: a.result,
      executions: repo.executions + 1 } else repo, "worked", f == "", asked, selection, noCall, f, noAttempt)
  } else if ((phase == "routed" and accepted and not(repo.pending)) or (phase == "worked" and accepted)) {
    nondet f = Set("", "graft", "binding", "prior-version-graft").oneOf()
    val owner = if (repo.decision.attempt == 1) old else repo.produced
    val first = owner.trace[0]
    val second = owner.trace[1]
    val candidate = if (f == "graft") { ...owner, trace: [
      { ...first, source: if (first.source == 11) 12 else 11 }, second] }
      else if (f == "binding") { ...owner, binding: 3 - owner.binding }
      else if (f == "prior-version-graft") { ...owner, trace: [first,
        { ...second, source: 1000 * (3 - first.binding) + first.args }] } else owner
    val expected = if (repo.decision.attempt == 1) old else attempt(repo.decision.request)
    val ok = expected == candidate
    advance(repo, "offline", ok, asked, selection, noCall, f, if (ok) candidate else noAttempt)
  } else advance(repo, "done", false, asked, selection, offered, fault, noAttempt)

  // Independent fixture checks: role/binding pairs, identity, and behavior
  // of every transition, including status and the lack of partial publication.
  invariant internalCall = phase != "direct" or {
    val f = offered.func
    val i = offered.args % 100
    val ok = (if (f == 1) offered.binding == 1 or offered.binding == 2 else offered.binding == f + 1)
      and fault != "late" and fault != "invalid-arguments" and (fault != "graft" or f == 3)
    (accepted iff ok) and repo == { ...before,
      direct: if (ok) { func: f, binding: offered.binding, args: offered.args,
        source: if (f == 3) 0 else 10 + i,
        value: if (f == 1 or f == 4) 71 else if (f == 2) 6 else 70 } else noCall }
  }
  invariant routePublication = phase != "routed" or {
    val b = if (asked.override == 0) asked.choice else asked.override
    val consult = asked.mode != "fresh"
    val reused = consult and selection == 1 and asked.input != 3
    val ok = b <= 2 and fault != "late" and (not(consult) or (selection == asked.pin and selection != 2))
      and (asked.mode != "require-selected" or reused)
    (accepted iff ok) and repo == { ...before, main: if (ok and reused) 42 else 0,
      pending: ok and not(reused), decision: if (ok) { attempt: if (reused) 1 else 0,
        request: { ...asked, binding: b, pin: if (consult) selection else 0 } } else noDecision }
  }
  invariant workPublication = phase != "worked" or {
    val i = asked.input
    val b = if (asked.override == 0) asked.choice else asked.override
    val answer = if (i == 3) 43 else 42
    (accepted iff fault == "") and repo == (if (not(accepted)) before else {
      ...before, pending: false, main: answer, executions: 2,
      produced: { input: i, binding: b, result: answer, trace: [
        { func: 1, binding: b, args: 100 + i, source: 10 + i, value: if (i == 3) 72 else 71 },
        { func: 2, binding: 3, args: 200 + i, source: 1000 * b + 100 + i, value: answer }] } })
  }
  invariant inspection = phase != "offline" or {
    val reused = repo.decision.attempt == 1
    (accepted iff fault == "") and repo == before and repo.executions == (if (reused) 1 else 2)
      and report == (if (not(accepted)) noAttempt else if (reused) old else repo.produced)
  }

  observation oldBindingAfterPromotion = phase == "direct" and accepted and repo.live == 2
    and repo.direct.func == 1 and repo.direct.binding == 1
  observation newBindingAfterPromotion = phase == "direct" and accepted and repo.live == 2
    and repo.direct.func == 1 and repo.direct.binding == 2
  observation defaultPinnedAcrossPromotion = phase == "worked" and accepted and repo.live == 2
    and asked.choice == 1 and asked.override == 0 and repo.produced.binding == 1
  observation unsupported = phase == "direct" and not(accepted) and offered.binding == 99 and fault == ""
  observation wrongFunc = phase == "direct" and not(accepted) and offered.func == 1 and offered.binding == 3 and fault == ""
  observation equalSourceGraft = phase == "direct" and not(accepted) and offered.func == 1 and offered.binding == 1 and fault == "graft"
  observation reusedOldTrace = phase == "offline" and accepted and report == old and repo.executions == 1
    and repo.decision.request.input == 2 and repo.decision.request.binding == 2
  observation valueMiss = phase == "worked" and accepted and asked.input == 3 and asked.mode == "try-selected"
    and selection == 1 and repo.main == 43
  observation invalidSelectionOnMiss = phase == "routed" and not(accepted) and asked.input == 3
    and asked.mode == "try-selected" and asked.pin == 2 and selection == 2 and asked.override == 0 and fault == ""
  observation staleSelection = phase == "routed" and not(accepted) and asked.mode == "try-selected"
    and asked.pin == 1 and selection == 0 and asked.override == 0 and fault == ""
  observation caughtError = phase == "worked" and not(accepted) and fault == "caught-error" and repo.pending
  observation lateWork = phase == "worked" and not(accepted) and fault == "late" and repo.pending
  observation offlineGraft = phase == "offline" and not(accepted) and fault == "graft" and repo.decision.attempt == 1
  observation priorVersionGraft = phase == "offline" and not(accepted) and fault == "prior-version-graft"
}
