module ref_model {
  import ref_rules.* from "./ref_rules"

  // Transition model: it does not call the rule or constrain the rule's verdict.
  pure def create(before: Ref, requested: str): Attempt =
    match before {
      | Absent => { before: before, requested: requested, outcome: Created, after: Target(requested) }
      | Target(_) => { before: before, requested: requested, outcome: Failed("invalid_state"), after: before }
    }

  type History = { current: Ref, attempts: List[Attempt] }

  pure def replay(requests: List[str]): History =
    requests.foldl({ current: Absent, attempts: List() }, (history, requested) => {
      val attempt = create(history.current, requested)
      { current: attempt.after, attempts: history.attempts.append(attempt) }
    })

  // Each round extends every prefix by every target and retains the shorter prefixes.
  pure val histories: Set[List[str]] = range(0, scenario.maxSteps).foldl(Set(List()), (prefixes, _) =>
    scenario.targets.fold(prefixes, (allPrefixes, target) =>
      allPrefixes.union(prefixes.map(prefix => prefix.append(target)))))

  run boundedSafetyTest = and {
    histories.size() == 121,
    histories.forall(requests => replay(requests).attempts.foldl(true, (safe, attempt) =>
      safe and verdict(attempt) != "violation")),
  }

  run matchingWitnessesTest = and {
    verdict(replay(List("a")).attempts[0]) == "unexercised",
    verdict(replay(List("a", "a")).attempts[1]) == "pass",
    verdict(replay(List("a", "b")).attempts[1]) == "pass",
  }
}
