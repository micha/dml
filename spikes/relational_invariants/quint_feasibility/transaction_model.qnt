module transaction_model {
  import transaction_rules.* from "./transaction_rules"

  type Request = (str, str)
  type Progress = { current: Ref, poisoned: bool, steps: List[Step] }

  // Transitions do not call WHEN/EXPECT predicates.
  pure def advance(history: Progress, request: Request): Progress = {
    val outcome = if (history.poisoned) Failed("invalid_state")
      else if (request._1 == "create_ref" and history.current != Absent) Failed("invalid_state")
      else if (request._1 == "update_ref" and history.current == Absent) Failed("not_found")
      else Succeeded
    val after = if (outcome == Succeeded) Target(request._2) else history.current
    val step = { operation: request._1, requested: request._2,
                 before: if (history.poisoned) Unreadable("invalid_state") else history.current,
                 after: if (outcome == Succeeded) after else Unreadable("invalid_state"),
                 outcome: outcome, poisoned: history.poisoned }
    { current: after, poisoned: history.poisoned or outcome != Succeeded,
      steps: history.steps.append(step) }
  }

  pure def replay(before: Ref, requests: List[Request], finish: str): Attempt = {
    val history = requests.foldl({ current: before, poisoned: false, steps: List() },
      (state, request) => advance(state, request))
    val publish = finish == "commit" and not(history.poisoned)
    { before: before, staged: if (history.poisoned) Unreadable("invalid_state") else history.current,
      after: if (publish) history.current else before,
      steps: history.steps, finish: finish,
      outcome: if (finish == "commit" and history.poisoned) Failed("invalid_state") else Succeeded,
      markerBefore: false, markerStaged: true, markerAfter: publish }
  }

  pure val alphabet = tuples(scenario.operations, scenario.targets)
  pure val histories = range(0, scenario.maxSteps).foldl(Set(List()), (prefixes, _) =>
    alphabet.fold(prefixes, (allPrefixes, request) =>
      allPrefixes.union(prefixes.map(prefix => prefix.append(request)))))
  pure val initials = Set(Absent).union(scenario.targets.map(target => Target(target)))

  run boundedSafetyTest = and {
    histories.size() == 85,
    initials.forall(before => histories.forall(requests => scenario.finishes.forall(finish =>
      ruleIds.forall(rule => Set("unexercised", "pass").contains(verdict(rule, replay(before, requests, finish))))))),
  }

  run everyRuleMatchesTest =
    ruleIds.forall(rule => initials.exists(before => histories.exists(requests =>
      scenario.finishes.exists(finish => verdict(rule, replay(before, requests, finish)) == "pass"))))
}
