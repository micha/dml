module context_model {
  import transaction_rules.* from "./transaction_rules"
  import transaction_model.advance from "./transaction_model"
  import context_rules.* from "./context_rules"

  // Completion transitions are separate from the asserted context predicates.
  // Ref-operation transitions reuse the independent explicit-transaction model.
  pure def replayContext(before: Ref, requests: List[(str, str)], finish: str): Context = {
    val history = requests.foldl({ current: before, poisoned: false, steps: List() },
      (state, request) => advance(state, request))
    val publish = finish == "normal" and not(history.poisoned)
    { batch: {
        before: before,
        staged: if (history.poisoned) Unreadable("invalid_state") else history.current,
        after: if (publish) history.current else before,
        steps: history.steps, finish: finish,
        outcome: if (finish == "exception") Failed("body_exception")
          else if (history.poisoned) Failed("invalid_state") else Succeeded,
        markerBefore: false, markerStaged: true, markerAfter: publish,
      },
      exception: if (finish == "exception") "original" else "none",
    }
  }

  pure val contextAlphabet = tuples(contextScenario.operations, contextScenario.targets)
  pure val contextHistories = range(0, contextScenario.maxSteps).foldl(Set(List()), (prefixes, _) =>
    contextAlphabet.fold(prefixes, (allPrefixes, request) =>
      allPrefixes.union(prefixes.map(prefix => prefix.append(request)))))
  pure val contextInitials = Set(Absent).union(contextScenario.targets.map(target => Target(target)))

  run boundedContextSafetyTest = and {
    contextHistories.size() == 85,
    contextInitials.forall(before => contextHistories.forall(requests => contextScenario.finishes.forall(finish =>
      contextRuleIds.forall(rule => Set("unexercised", "pass").contains(
        contextVerdict(rule, replayContext(before, requests, finish))))))),
  }

  run everyContextRuleMatchesTest =
    contextRuleIds.forall(rule => contextInitials.exists(before => contextHistories.exists(requests =>
      contextScenario.finishes.exists(finish =>
        contextVerdict(rule, replayContext(before, requests, finish)) == "pass"))))
}
