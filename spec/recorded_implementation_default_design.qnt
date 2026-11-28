// Snapshot-scoped implementation defaults for the recorded-scale example.
module recorded_implementation_default_design {
  // Definitions 1 and 2 share a reuse mode and slot declarations, with
  // different defaults. Definition 3 has its own execute-default lineage.
  // Definition 4 is malformed. Slot 0 is absent; 1/3 are two versions of
  // the same v1 selection, 2 selects v2 (same numeric result as v1),
  // 4 is malformed, 5 has a different producer/factor. Portable request
  // identity is represented by the implementation for one producer/factor.
  // Each invocation is atomic. Ref names/framing, worker execution, hashing,
  // and concurrent operations within a write transaction are out of scope.
  type Call = { expected: int, implementation: int, reuse: str, selection: int, obstacle: str }
  type Decision = { intent: int, implementation: int, requested: int, source: str,
    reason: str, observed: int, selection: int, savedMain: int }
  type Repo = { oldIntent: int, newIntent: int, slotA: int, slotB: int, main: int,
    plans: int, decisions: List[Decision] }
  pure val initial: Repo = { oldIntent: 1, newIntent: 0, slotA: 1, slotB: 0, main: 9,
    plans: 0, decisions: List() }
  pure val defaultCall: Call = { expected: 1, implementation: 0, reuse: "default", selection: 1, obstacle: "none" }
  pure val noDecision: Decision = { intent: 0, implementation: 0, requested: 0, source: "",
    reason: "", observed: -1, selection: 0, savedMain: 0 }
  var repo: Repo
  var before: Repo
  var call: Call
  var pin: int
  var phase: str
  var accepted: bool

  action progress(r: Repo, prior: Repo, c: Call, p: int, stage: str, ok: bool): bool = all {
    repo' = r, before' = prior, call' = c, pin' = p, phase' = stage, accepted' = ok
  }
  action init = all {
    repo' = initial, before' = initial, call' = defaultCall, pin' = 0, phase' = "setup", accepted' = false
  }

  pure def slot(repo: Repo, implementation: int): int = if (implementation == 1) repo.slotA else repo.slotB
  pure def choose(c: Call): int = if (c.implementation != 0) c.implementation else if (c.expected == 1) 1 else 2
  pure def usesSlot(c: Call): bool = c.reuse == "reuse-selected" or (c.reuse == "default" and c.expected != 3)
  pure def evaluate(r: Repo, p: int, c: Call, implementation: int): str = {
    if (p != c.expected or not(Set(1, 2, 3).contains(p)) or not(Set(1, 2).contains(implementation))) "error"
    else if (c.reuse == "fresh") "override-fresh"
    else if (c.reuse == "default" and c.expected == 3) "default-execution"
    else if (not(usesSlot(c)) or slot(r, implementation) != c.selection) "error"
    else if (c.reuse == "default" and c.selection == 0) "default-no-selection"
    else if ((implementation == 1 and Set(1, 3).contains(c.selection)) or
      (implementation == 2 and c.selection == 2)) {
      if (c.reuse == "default") "default-selection" else "override-selected-reuse"
    } else "error"
  }

  action decide(stage: str): bool = {
    val implementation = choose(call)
    val reason = evaluate(repo, pin, call, implementation)
    val ok = reason != "error" and call.obstacle == "none"
    val reusing = Set("default-selection", "override-selected-reuse").contains(reason)
    val d = { intent: call.expected, implementation: implementation, requested: call.implementation,
      source: if (call.implementation == 0) "default-implementation" else "explicit-implementation",
      reason: reason, observed: if (usesSlot(call)) implementation else -1,
      selection: if (reusing) call.selection else 0, savedMain: repo.main }
    val after = { ...repo, decisions: repo.decisions.append(d),
      main: if (reusing) implementation + 10 else repo.main, plans: repo.plans + (if (reusing) 0 else 1) }
    progress(if (ok) after else repo, repo, call, pin, stage, ok)
  }

  action step = if (phase == "setup") any {
    all {
      nondet actual = Set(0, 1, 2, 3, 4).oneOf()
      nondet expected = Set(1, 2, 3, 4).oneOf()
      nondet implementation = Set(0, 1, 2, 3).oneOf()
      nondet reuse = Set("default", "fresh", "reuse-selected", "typo").oneOf()
      nondet slots = Set((0, 0), (1, 0), (0, 2), (1, 2), (2, 1), (3, 2), (4, 2), (1, 4), (5, 5)).oneOf()
      nondet selection = Set(0, 1, 2, 3, 4, 5).oneOf()
      nondet obstacle = Set("none", "producerMoved", "planOccupied", "decisionOccupied", "lateFailure").oneOf()
      val ready = { ...repo, slotA: slots._1, slotB: slots._2 }
      progress(ready, ready, { expected: expected, implementation: implementation, reuse: reuse,
        selection: selection, obstacle: obstacle }, actual, "ready", false)
    },
    // Keep both definition versions pinned. Request from the retained old
    // definition after publishing the new one, then use the new default.
    progress(repo, repo, defaultCall, 1, "version", false)
  } else if (phase == "ready") decide("judged")
  else if (phase == "version") {
    nondet basis = Set(1, 4).oneOf()
    nondet occupied = Set(0, 3).oneOf()
    val ready = { ...repo, newIntent: occupied }
    val ok = basis == repo.oldIntent and occupied == 0
    progress(if (ok) { ...ready, newIntent: 2 } else ready,
      ready, { ...call, expected: basis }, pin, "versioned", ok)
  } else if (phase == "versioned" and accepted) {
    progress(repo, repo, defaultCall, repo.oldIntent, "old", false)
  } else if (phase == "old") decide("oldJudged")
  else if (phase == "oldJudged") {
    progress(repo, repo, { ...defaultCall, expected: 2, selection: 0 }, repo.newIntent, "new", false)
  } else if (phase == "new") decide("newJudged")
  else progress(repo, repo, defaultCall, 0, "done", false)

  // Independent implementation and reuse tables, including exact substitution
  // rejection even when two selection commits select the same attempt.
  val judged = Set("judged", "oldJudged", "newJudged").contains(phase)
  val current = if (repo.decisions.length() == 0) noDecision else repo.decisions[repo.decisions.length() - 1]
  val impl = if (call.implementation == 1 or (call.implementation == 0 and call.expected == 1)) 1 else 2
  val valid = Set(0, 1, 2).contains(call.implementation) and Set(1, 2, 3).contains(call.expected) and pin == call.expected
  val actualSlot = if (impl == 1) before.slotA else before.slotB
  val selectionMatches = call.selection == actualSlot and
    (if (impl == 1) Set(1, 3).contains(actualSlot) else actualSlot == 2)
  val reason = if (call.reuse == "fresh") "override-fresh"
    else if (call.reuse == "default" and call.expected == 3) "default-execution"
    else if (call.reuse == "default" and call.selection == 0 and actualSlot == 0) "default-no-selection"
    else if (call.reuse == "default" and selectionMatches) "default-selection"
    else if (call.reuse == "reuse-selected" and selectionMatches) "override-selected-reuse"
    else "error"
  val reusing = Set("default-selection", "override-selected-reuse").contains(reason)

  invariant exactVersionPublication = phase != "versioned" or {
    val eligible = call.expected == before.oldIntent and before.newIntent == 0
    (accepted iff eligible) and repo == (if (eligible) { ...before, newIntent: 2 } else before)
  }
  invariant exactChoiceAndReuse = not(judged) or (accepted iff (valid and reason != "error" and call.obstacle == "none"))
  invariant atomicDecision = not(judged) or {
    if (not(accepted)) repo == before else {
      val expected = { intent: call.expected, implementation: impl, requested: call.implementation,
        source: if (call.implementation == 0) "default-implementation" else "explicit-implementation",
        reason: reason, observed: if (reusing or reason == "default-no-selection") impl else -1,
        selection: if (reusing) actualSlot else 0, savedMain: before.main }
      repo == { ...before, decisions: before.decisions.append(expected),
        main: if (reusing) impl + 10 else before.main, plans: before.plans + (if (reusing) 0 else 1) }
    }
  }
  invariant retainedSemantics = repo.decisions.indices().forall(i => {
    val d = repo.decisions[i]
    if (d.requested == 0) d.implementation == (if (d.intent == 1) 1 else 2) else d.implementation == d.requested
  })

  val ok = judged and accepted
  val rejected = judged and not(accepted) and call.obstacle == "none"
  observation versionIsCreateOnly = phase == "versioned" and not(accepted) and before.newIntent == 3 and call.expected == 1
  observation versionRejectsMovedBasis = phase == "versioned" and not(accepted) and before.newIntent == 0
  observation oldAndNewDefaults = phase == "newJudged" and accepted and repo.decisions.length() == 2 and
    repo.decisions[0].implementation == 1 and repo.decisions[0].reason == "default-selection" and
    current.implementation == 2 and current.reason == "default-no-selection"
  observation newDefaultReuses = ok and current.intent == 2 and current.requested == 0 and current.selection == 2 and
    current.reason == "default-selection"
  observation overrideAReuses = ok and current.intent == 2 and current.requested == 1 and current.selection == 1 and
    before.slotB == 4 and current.reason == "default-selection"
  observation overrideBReuses = ok and current.intent == 1 and current.requested == 2 and current.selection == 2 and
    current.reason == "default-selection"
  observation freshIgnoresSlots = ok and current.reason == "override-fresh" and current.requested == 1 and before.slotA == 4
  observation executeDefaultIgnoresSlot = ok and current.reason == "default-execution" and before.slotB == 4
  observation explicitReuseOverridesExecute = ok and current.intent == 3 and current.selection == 2
  observation incompatibleIsNotAbsence = rejected and valid and call.reuse == "default" and impl == 2 and
    call.selection == 1 and before.slotB == 1
  observation malformedIsNotAbsence = rejected and valid and call.reuse == "default" and call.selection == 4 and actualSlot == 4
  observation otherInputsAreNotAbsence = rejected and valid and call.reuse == "default" and call.selection == 5 and actualSlot == 5
  observation rejectsExactVersionSubstitution = rejected and valid and impl == 1 and before.slotA == 3 and
    call.selection == 1 and call.reuse == "default"
  observation rejectsMovedDefinition = rejected and pin == 2 and call.expected == 1 and call.implementation == 2 and
    call.reuse == "default" and selectionMatches
  observation rejectsUnknownImplementation = rejected and pin == 2 and call.expected == 2 and call.implementation == 3 and
    call.reuse == "default" and before.slotB == 2 and call.selection == 2
  observation rollsBackPublication = judged and not(accepted) and valid and reusing and call.obstacle == "lateFailure"
}
