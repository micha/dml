module read_context_model {
  import read_context_rules.* from "./read_context_rules"

  // A seeded existing ref and a separate absent probe ref; neither changes in
  // either transition system. Only the active read handle can be consumed.
  pure val seededTarget = "seeded-target"
  type Progress = { active: bool, steps: List[Step] }

  pure def readExisting(active: bool): str =
    if (active) seededTarget else "invalid_state"

  pure def readProbe(active: bool): str =
    if (active) "not_found" else "invalid_state"

  pure def advance(state: Progress, operation: str, endOnCommit: bool): Progress = {
    val outcome = if (operation == "missing_read") readProbe(state.active) else "invalid_state"
    // Fault alternative: commit still reports rejection but ends the handle.
    val active = state.active and not(endOnCommit and operation == "commit")
    { active: active, steps: state.steps.append({ operation: operation, outcome: outcome,
                                                  readAfter: readExisting(active) }) }
  }

  pure def replay(requests: List[str], exitMode: str, endOnCommit: bool): Attempt = {
    val start = { active: true, steps: List() }
    val body = requests.foldl(start, (state, operation) => advance(state, operation, endOnCommit))
    // Exit aborts a live read or does nothing if already ended. In either case
    // the body exception, if any, reaches the caller unchanged.
    val ended = { active: false, steps: body.steps }
    { before: readExisting(start.active), steps: ended.steps, exitMode: exitMode,
      exitOutcome: if (exitMode == "exception") "same_exception" else "ok",
      endedRead: readExisting(ended.active), after: readExisting(true), probeRef: readProbe(true) }
  }

  pure val histories = range(0, scenario.maxSteps).foldl(Set(List()), (prefixes, _) =>
    scenario.operations.fold(prefixes, (allPrefixes, operation) =>
      allPrefixes.union(prefixes.map(prefix => prefix.append(operation)))))
    .filter(requests => requests.length() != 0)

  run boundedReadContextSafetyTest = and {
    histories.size() == 39,
    scenario.exits.size() == 2,
    histories.forall(requests => scenario.exits.forall(exitMode => {
      val attempt = replay(requests, exitMode, false)
      ruleIds.forall(rule => Set("pass", "unexercised").contains(verdict(rule, attempt)))
    })),
  }

  run everyReadContextRuleMatchesTest =
    ruleIds.forall(rule => histories.exists(requests => scenario.exits.exists(exitMode =>
      verdict(rule, replay(requests, exitMode, false)) == "pass")))

  pure def passesWeakRules(attempt: Attempt): bool =
    ruleIds.filter(rule => rule != "readStillUsable").forall(rule => verdict(rule, attempt) == "pass")

  run prematureEndWitnessTest = scenario.exits.forall(exitMode => {
    val good = replay(List("commit"), exitMode, false)
    val premature = replay(List("commit"), exitMode, true)
    passesWeakRules(good) and passesWeakRules(premature) and
      verdict("readStillUsable", good) == "pass" and verdict("readStillUsable", premature) == "violation"
  })

  run boundedPrematureEndCharacterizationTest = scenario.exits.forall(exitMode => and {
    histories.forall(requests => {
      val commitSeen = requests.foldl(false, (seen, operation) => seen or operation == "commit")
      val premature = replay(requests, exitMode, true)
      verdict("readStillUsable", premature) == (if (commitSeen) "violation" else "pass")
    }),
    // Some longer histories also expose the fault through a later missing
    // read's changed status. Count the histories the weak rules still miss.
    histories.filter(requests => {
      val premature = replay(requests, exitMode, true)
      passesWeakRules(premature) and verdict("readStillUsable", premature) == "violation"
    }).size() == 17,
  })
}
