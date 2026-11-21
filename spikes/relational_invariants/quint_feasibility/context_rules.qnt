module context_rules {
  import transaction_rules.* from "./transaction_rules"

  type Context = { batch: Attempt, exception: str }

  pure val contextScenario = {
    operations: Set("create_ref", "update_ref"),
    targets: Set("a", "b"),
    maxSteps: 3,
    finishes: Set("normal", "exception"),
  }
  pure val contextRuleIds = Set("stepEffects", "continuity", "freshMarker",
    "normalClean", "normalPoisoned", "exceptionalExit")

  pure def whenNormalClean(c: Context): bool = c.batch.finish == "normal" and not(hasFailure(c.batch))
  pure def expectNormalClean(c: Context): bool =
    c.exception == "none" and c.batch.outcome == Succeeded and
    c.batch.after == c.batch.staged and c.batch.markerAfter == c.batch.markerStaged

  pure def whenNormalPoisoned(c: Context): bool = c.batch.finish == "normal" and hasFailure(c.batch)
  pure def expectNormalPoisoned(c: Context): bool =
    c.exception == "none" and c.batch.outcome == Failed("invalid_state") and
    c.batch.after == c.batch.before and c.batch.markerAfter == c.batch.markerBefore

  pure def whenExceptional(c: Context): bool = c.batch.finish == "exception"
  pure def expectExceptional(c: Context): bool =
    c.exception == "original" and c.batch.outcome == Failed("body_exception") and
    c.batch.after == c.batch.before and c.batch.markerAfter == c.batch.markerBefore

  pure def contextVerdict(rule: str, c: Context): str =
    if (rule == "stepEffects") classify(whenSteps(c.batch), expectSteps(c.batch))
    else if (rule == "continuity") classify(whenContinuity(c.batch), expectContinuity(c.batch))
    else if (rule == "freshMarker") classify(whenMarker(c.batch), expectMarker(c.batch))
    else if (rule == "normalClean") classify(whenNormalClean(c), expectNormalClean(c))
    else if (rule == "normalPoisoned") classify(whenNormalPoisoned(c), expectNormalPoisoned(c))
    else if (rule == "exceptionalExit") classify(whenExceptional(c), expectExceptional(c))
    else "unknown rule"
}
