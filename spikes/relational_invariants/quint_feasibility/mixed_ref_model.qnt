module mixed_ref_model {
  import mixed_ref_rules.* from "./mixed_ref_rules"

  type Request = (str, str)
  type History = { current: Ref, attempts: List[Attempt] }

  // Model the transition independently of the rule predicates.
  pure def apply(before: Ref, request: Request): Attempt = {
    val operation = request._1
    val requested = request._2
    val outcome = if (operation == "create_ref" and before != Absent) Failed("invalid_state")
      else if (operation == "update_ref" and before == Absent) Failed("not_found")
      else Succeeded
    { operation: operation, before: before, requested: requested, outcome: outcome,
      after: if (outcome == Succeeded) Target(requested) else before }
  }

  pure def replay(requests: List[Request]): History =
    requests.foldl({ current: Absent, attempts: List() }, (history, request) => {
      val attempt = apply(history.current, request)
      { current: attempt.after, attempts: history.attempts.append(attempt) }
    })

  pure val alphabet = tuples(scenario.operations, scenario.targets)
  pure val histories = range(0, scenario.maxSteps).foldl(Set(List()), (prefixes, _) =>
    alphabet.fold(prefixes, (allPrefixes, request) =>
      allPrefixes.union(prefixes.map(prefix => prefix.append(request)))))

  run boundedSafetyTest = and {
    histories.size() == 85,
    histories.forall(requests => replay(requests).attempts.foldl(true, (safe, attempt) =>
      safe and ruleIds.forall(rule => Set("unexercised", "pass").contains(verdict(rule, attempt))))),
  }

  run everyRuleMatchesTest =
    ruleIds.forall(rule => histories.exists(requests =>
      replay(requests).attempts.foldl(false, (matched, attempt) => matched or verdict(rule, attempt) == "pass")))
}
