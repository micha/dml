module explicit_context_rules {
  import transaction_rules.* from "./transaction_rules"

  type ExplicitContext = {
    batch: Attempt, explicit: Outcome, exception: str,
    endedRef: Ref, endedMarker: bool,
    endRead: Outcome, endWrite: Outcome, endCommit: Outcome, endAbort: Outcome,
    exitCalls: int,
  }

  pure val explicitContextScenario = {
    operations: Set("create_ref", "update_ref"),
    targets: Set("a", "b"),
    maxSteps: 3,
    finishes: Set("commit_normal", "commit_exception", "abort_normal", "abort_exception"),
  }
  pure val explicitContextRuleIds = Set("stepEffects", "continuity", "freshMarker",
    "explicitCleanCommit", "explicitPoisonedCommit", "explicitAbort", "endedHandle", "contextExit")

  pure def isCommit(c: ExplicitContext): bool =
    c.batch.finish == "commit_normal" or c.batch.finish == "commit_exception"
  pure def isExceptional(c: ExplicitContext): bool =
    c.batch.finish == "commit_exception" or c.batch.finish == "abort_exception"

  pure def whenExplicitCleanCommit(c: ExplicitContext): bool = isCommit(c) and not(hasFailure(c.batch))
  pure def expectExplicitCleanCommit(c: ExplicitContext): bool =
    c.explicit == Succeeded and c.endedRef == c.batch.staged and c.endedMarker == c.batch.markerStaged

  pure def whenExplicitPoisonedCommit(c: ExplicitContext): bool = isCommit(c) and hasFailure(c.batch)
  pure def expectExplicitPoisonedCommit(c: ExplicitContext): bool =
    c.explicit == Failed("invalid_state") and c.endedRef == c.batch.before and c.endedMarker == c.batch.markerBefore

  pure def whenExplicitAbort(c: ExplicitContext): bool =
    c.batch.finish == "abort_normal" or c.batch.finish == "abort_exception"
  pure def expectExplicitAbort(c: ExplicitContext): bool =
    c.explicit == Succeeded and c.endedRef == c.batch.before and c.endedMarker == c.batch.markerBefore

  pure def whenEndedHandle(c: ExplicitContext): bool = true
  pure def expectEndedHandle(c: ExplicitContext): bool =
    c.endRead == Failed("invalid_state") and c.endWrite == Failed("invalid_state") and
    c.endCommit == Failed("invalid_state") and c.endAbort == Succeeded

  pure def whenContextExit(c: ExplicitContext): bool = true
  pure def expectContextExit(c: ExplicitContext): bool =
    c.exitCalls == 0 and c.batch.after == c.endedRef and c.batch.markerAfter == c.endedMarker and
    (if (isExceptional(c)) c.exception == "original" and c.batch.outcome == Failed("body_exception")
     else c.exception == "none" and c.batch.outcome == Succeeded)

  pure def explicitContextVerdict(rule: str, c: ExplicitContext): str =
    if (rule == "stepEffects") classify(whenSteps(c.batch), expectSteps(c.batch))
    else if (rule == "continuity") classify(whenContinuity(c.batch), expectContinuity(c.batch))
    else if (rule == "freshMarker") classify(whenMarker(c.batch), expectMarker(c.batch))
    else if (rule == "explicitCleanCommit") classify(whenExplicitCleanCommit(c), expectExplicitCleanCommit(c))
    else if (rule == "explicitPoisonedCommit") classify(whenExplicitPoisonedCommit(c), expectExplicitPoisonedCommit(c))
    else if (rule == "explicitAbort") classify(whenExplicitAbort(c), expectExplicitAbort(c))
    else if (rule == "endedHandle") classify(whenEndedHandle(c), expectEndedHandle(c))
    else if (rule == "contextExit") classify(whenContextExit(c), expectContextExit(c))
    else "unknown rule"
}
