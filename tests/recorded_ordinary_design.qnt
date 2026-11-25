// Iteration 24. One historical success, one new outer invocation, two fixed slots,
// two immutable captures, four full input MAPs, no recursion or worker process.
// IDs abstract immutable graph links and distinct request/attempt occurrences.
module recorded_ordinary_design {
  type Repo = { defaults: int, capture: int, input: int, head: str, main: int,
    outerQ: int, outerT: int, getters: int, usedCapture: int, addQ: int, addT: int, addInput: int,
    addResult: int, doubleQ: int, doubleT: int, requestedSource: int, producingSource: int,
    doubleResult: int, outerResult: int }
  type Controls = { mode: str, slot: int }
  type Report = { outerQ: int, outerT: int, doubleQ: int, doubleT: int,
    requestedSource: int, producingSource: int, result: int }

  pure val empty: Repo = { defaults: 1, capture: 0, input: 0, head: "absent", main: 79,
    outerQ: 0, outerT: 0, getters: 0, usedCapture: 0, addQ: 0, addT: 0, addInput: 0,
    addResult: 0, doubleQ: 0, doubleT: 0, requestedSource: 0, producingSource: 0,
    doubleResult: 0, outerResult: 0 }
  pure val noReport: Report = { outerQ: 0, outerT: 0, doubleQ: 0, doubleT: 0,
    requestedSource: 0, producingSource: 0, result: 0 }
  // Slot 1 pins valid old history. Slot 2 is present but has an invalid original
  // source chain. No fallback for a poisoned consulted selection, even on mismatch.
  pure val choices = Set({ mode: "fresh", slot: 0 }, { mode: "try", slot: 0 },
    { mode: "try", slot: 1 }, { mode: "try", slot: 2 }, { mode: "require", slot: 1 })
  pure def poisoned(c: Controls): bool = c.mode != "fresh" and c.slot == 2
  pure def matches(c: Controls, sameKey: bool): bool = c.mode != "fresh" and c.slot == 1 and sameKey
  // MAP 1: a=13,b=29; MAP 2: swapped; MAP 3: a=13,b=30; MAP 4: valid add, double overflows.
  // 100 stands for a subtotal that is I64 but is not I64 after doubling.
  pure val overflowingSubtotal = 100
  pure def subtotal(mapId: int): int = if (mapId <= 2) 42 else if (mapId == 3) 43 else overflowingSubtotal
  pure def inspect(r: Repo, source: int): Report = if (r.head == "hit")
    { outerQ: r.outerQ, outerT: 8, doubleQ: 13, doubleT: 14, requestedSource: 60,
      producingSource: 60, result: 80 }
    else if (r.head == "done" and source == r.addResult) {
      outerQ: r.outerQ, outerT: r.outerT, doubleQ: r.doubleQ,
      doubleT: r.doubleT, requestedSource: source, producingSource: r.producingSource,
      result: r.outerResult }
    else noReport

  var repo: Repo
  var before: Repo
  var outer: Controls
  var inner: Controls
  var input: int
  var phase: str
  var fault: str
  var report: Report

  action save(r: Repo, p: str, f: str, v: Report): bool = all {
    repo' = r, before' = repo, phase' = p, fault' = f, report' = v,
    outer' = outer, inner' = inner, input' = input,
  }
  action init = {
    nondet o = choices.oneOf()
    nondet i = choices.oneOf()
    nondet a = Set(1, 2, 3, 4).oneOf()
    nondet d = Set(1, 2).oneOf()
    all { repo' = { ...empty, defaults: d }, before' = empty, outer' = o, inner' = i,
      input' = a, phase' = "ready", fault' = "", report' = noReport }
  }
  action step = if (phase == "ready")
    save({ ...repo, capture: repo.defaults }, "captured", "", noReport)
  else if (phase == "captured") {
    nondet d = Set(1, 2).oneOf()
    save({ ...repo, defaults: d }, "promoted", "", noReport)
  } else if (phase == "promoted") {
    nondet late = Set(false, true).oneOf()
    val hit = matches(outer, repo.capture == 1 and input == 1)
    val ok = not(late or poisoned(outer) or poisoned(inner) or (outer.mode == "require" and not(hit)))
    val routed = if (hit) { ...repo, input: input, outerQ: 21, head: "hit", main: 80, outerResult: 80 }
      else { ...repo, input: input, outerQ: 21, outerT: 22, head: "start" }
    save(if (ok) routed else repo, "routed", if (late) "late" else "", noReport)
  } else if (phase == "routed" and repo.head == "start") {
    nondet late = Set(false, true).oneOf()
    // Commit the outer getter positions and the successful add together. The
    // leaf receives the ORIGINAL input node, not a new MAP with equal datums.
    save(if (late) repo else { ...repo, head: "add", getters: 4, usedCapture: repo.capture,
      addQ: 23, addT: 24, addInput: repo.input, addResult: 61 },
      "added", if (late) "late" else "", noReport)
  } else if (phase == "added" and repo.head == "add") {
    nondet late = Set(false, true).oneOf()
    val hit = matches(inner, repo.capture == 1 and subtotal(repo.input) == 42)
    val failure = if (inner.mode == "require" and not(hit)) "miss"
      else if (subtotal(repo.input) == overflowingSubtotal) "overflow" else if (late) "late" else ""
    val doubled = if (hit) { ...repo, head: "double", doubleQ: 25, doubleT: 14,
      requestedSource: repo.addResult, producingSource: 60, doubleResult: 70 }
      else { ...repo, head: "double", doubleQ: 25, doubleT: 26, getters: repo.getters + 1,
        requestedSource: repo.addResult, producingSource: repo.addResult, doubleResult: 71 }
    save(if (failure == "") doubled else repo, "doubled", failure, noReport)
  } else if (phase == "doubled" and repo.head == "double") {
    nondet late = Set(false, true).oneOf()
    save(if (late) repo else { ...repo, head: "done", main: 81, outerResult: 81 },
      "finished", if (late) "late" else "", noReport)
  } else if (Set("routed", "added", "doubled", "finished").contains(phase)) {
    nondet graft = (if (repo.head == "done") Set(false, true) else Set(false)).oneOf()
    // A chain graft is rejected, not repaired by using an equal-valued source.
    save(repo, "offline", if (graft) "graft" else "", inspect(repo, if (graft) 60 else repo.requestedSource))
  } else save(repo, "end", "", noReport)

  invariant capturedTargets = (phase != "captured" or repo.capture == before.defaults)
    and (phase != "promoted" or repo == { ...before, defaults: repo.defaults })
    and (repo.usedCapture == 0 or repo.usedCapture == repo.capture)
  invariant outerRouting = phase != "routed" or {
    val hit = outer.slot == 1 and before.capture == 1 and input == 1
    val rejects = fault == "late" or outer.slot == 2 or inner.slot == 2 or (outer.mode == "require" and not(hit))
    repo == (if (rejects) before else if (hit) { ...before, input: input, outerQ: 21, head: "hit", main: 80, outerResult: 80 }
      else { ...before, input: input, outerQ: 21, outerT: 22, head: "start" })
  }
  invariant addOwnsOriginalInput = phase != "added" or repo == (if (fault == "late") before
    else { ...before, head: "add", getters: 4, usedCapture: before.capture, addQ: 23, addT: 24,
      addInput: before.input, addResult: 61 })
  invariant doubleRetainsActualSources = phase != "doubled" or {
    val same = before.capture == 1 and before.input <= 2
    val hit = inner.slot == 1 and same
    val reject = (inner.mode == "require" and not(hit)) or before.input == 4 or fault == "late"
    repo == (if (reject) before else { ...before, head: "double", doubleQ: 25,
      doubleT: if (hit) 14 else 26, getters: if (hit) 4 else 5,
      requestedSource: 61, producingSource: if (hit) 60 else 61, doubleResult: if (hit) 70 else 71 })
  }
  invariant onlyTerminalPublishesMain = repo.main == (if (repo.head == "done") 81 else if (repo.head == "hit") 80 else 79)
    and (phase != "finished" or repo == (if (fault == "late") before
      else { ...before, head: "done", main: 81, outerResult: 81 }))
  invariant offlineNoWritesOrSubstitution = phase != "offline" or (repo == before and report ==
    (if (fault == "graft" or not(Set("hit", "done").contains(before.head))) noReport
     else if (before.head == "hit") { outerQ: 21, outerT: 8, doubleQ: 13, doubleT: 14,
       requestedSource: 60, producingSource: 60, result: 80 }
     else { outerQ: 21, outerT: 22, doubleQ: 25, doubleT: before.doubleT,
       requestedSource: 61, producingSource: before.producingSource, result: 81 }))

  observation pinnedAfterPromotion = phase == "finished" and repo.head == "done"
    and repo.defaults == 2 and repo.usedCapture == 1 and repo.doubleT == 26
  observation movedCaptureMisses = phase == "finished" and repo.head == "done"
    and repo.capture == 2 and input == 1 and outer.slot == 1 and inner.slot == 1
  observation outerHitSkipsLeaves = phase == "offline" and report.outerT == 8 and repo.addQ == 0 and repo.doubleQ == 0
  observation swappedInnerHit = phase == "offline" and input == 2 and report.outerT == 22 and report.doubleT == 14
    and report.requestedSource != report.producingSource
  observation changedDownstreamMiss = phase == "finished" and input == 3 and inner.slot == 1 and repo.doubleT == 26
  observation requireOuterMiss = phase == "routed" and outer.mode == "require" and input == 2
    and fault == "" and repo.head == "absent"
  observation requireDoubleMissKeepsAdd = phase == "doubled" and fault == "miss" and repo.head == "add"
  observation doubleOverflowKeepsAdd = phase == "doubled" and fault == "overflow" and repo.head == "add"
  observation poisonOnOuterMismatch = phase == "routed" and fault == "" and outer.slot == 2
    and input == 2 and repo.head == "absent"
  observation poisonOnInnerMismatch = phase == "routed" and fault == "" and inner.slot == 2
    and outer.mode == "fresh" and input == 3 and repo.head == "absent"
  observation lateStartIsAtomic = phase == "routed" and fault == "late" and outer.mode == "fresh" and inner.mode == "fresh"
  observation lateAddKeepsStart = phase == "added" and fault == "late" and repo.head == "start"
  observation lateDoubleKeepsAdd = phase == "doubled" and fault == "late" and repo.head == "add"
  observation lateFinishKeepsDouble = phase == "finished" and fault == "late" and repo.head == "double"
  observation graftRejectedOffline = phase == "offline" and fault == "graft" and repo.head == "done" and report == noReport
}
