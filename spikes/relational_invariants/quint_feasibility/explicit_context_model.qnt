module explicit_context_model {
  import transaction_rules.* from "./transaction_rules"
  import transaction_model.advance from "./transaction_model"
  import explicit_context_rules.* from "./explicit_context_rules"

  // Independent transitions: the body catches any explicit-commit rejection,
  // then either returns normally or raises a fresh original exception.
  pure def replayExplicitContext(before: Ref, requests: List[(str, str)], finish: str): ExplicitContext = {
    val history = requests.foldl({ current: before, poisoned: false, steps: List() },
      (state, request) => advance(state, request))
    val commit = finish == "commit_normal" or finish == "commit_exception"
    val exceptional = finish == "commit_exception" or finish == "abort_exception"
    val publish = commit and not(history.poisoned)
    val published = if (publish) history.current else before
    { batch: {
        before: before,
        staged: if (history.poisoned) Unreadable("invalid_state") else history.current,
        after: published,
        steps: history.steps, finish: finish,
        outcome: if (exceptional) Failed("body_exception") else Succeeded,
        markerBefore: false, markerStaged: true, markerAfter: publish,
      },
      explicit: if (commit and history.poisoned) Failed("invalid_state") else Succeeded,
      exception: if (exceptional) "original" else "none",
      endedRef: published, endedMarker: publish,
      endRead: Failed("invalid_state"), endWrite: Failed("invalid_state"),
      endCommit: Failed("invalid_state"), endAbort: Succeeded,
      exitCalls: 0,
    }
  }

  pure val explicitContextAlphabet = tuples(explicitContextScenario.operations, explicitContextScenario.targets)
  pure val explicitContextHistories = range(0, explicitContextScenario.maxSteps).foldl(Set(List()), (prefixes, _) =>
    explicitContextAlphabet.fold(prefixes, (allPrefixes, request) =>
      allPrefixes.union(prefixes.map(prefix => prefix.append(request)))))
  pure val explicitContextInitials = Set(Absent).union(explicitContextScenario.targets.map(target => Target(target)))

  run boundedExplicitContextSafetyTest = and {
    explicitContextHistories.size() == 85,
    explicitContextInitials.forall(before => explicitContextHistories.forall(requests =>
      explicitContextScenario.finishes.forall(finish => explicitContextRuleIds.forall(rule =>
        Set("unexercised", "pass").contains(
          explicitContextVerdict(rule, replayExplicitContext(before, requests, finish))))))),
  }

  run everyExplicitContextRuleMatchesTest =
    explicitContextRuleIds.forall(rule => explicitContextInitials.exists(before =>
      explicitContextHistories.exists(requests => explicitContextScenario.finishes.exists(finish =>
        explicitContextVerdict(rule, replayExplicitContext(before, requests, finish)) == "pass"))))
}
