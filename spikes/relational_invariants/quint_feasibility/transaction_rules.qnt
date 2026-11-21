module transaction_rules {
  type Ref = Absent | Target(str) | Unreadable(str)
  type Outcome = Succeeded | Failed(str)
  type Step = { operation: str, requested: str, before: Ref, after: Ref,
                outcome: Outcome, poisoned: bool }
  type Attempt = { before: Ref, staged: Ref, after: Ref, steps: List[Step],
                   finish: str, outcome: Outcome, markerBefore: bool,
                   markerStaged: bool, markerAfter: bool }

  pure val scenario = {
    operations: Set("create_ref", "update_ref"),
    targets: Set("a", "b"),
    maxSteps: 3,
    finishes: Set("commit", "abort"),
  }
  pure val ruleIds = Set("stepEffects", "continuity", "freshMarker", "commitClean", "commitPoisoned", "explicitAbort")

  pure def hasFailure(a: Attempt): bool =
    a.steps.foldl(false, (failed, step) => failed or step.outcome != Succeeded)

  pure def expectedStep(s: Step): bool =
    if (s.poisoned) s.outcome == Failed("invalid_state") and
      s.before == Unreadable("invalid_state") and s.after == Unreadable("invalid_state")
    else if (s.operation == "create_ref" and s.before != Absent)
      s.outcome == Failed("invalid_state") and s.after == Unreadable("invalid_state")
    else if (s.operation == "update_ref" and s.before == Absent)
      s.outcome == Failed("not_found") and s.after == Unreadable("invalid_state")
    else s.outcome == Succeeded and s.after == Target(s.requested)

  pure def whenSteps(a: Attempt): bool = a.steps.length() != 0
  pure def expectSteps(a: Attempt): bool =
    a.steps.foldl(true, (holds, step) => holds and expectedStep(step))

  pure def whenContinuity(a: Attempt): bool = true
  pure def expectContinuity(a: Attempt): bool = {
    // Carry observed snapshots, not a predicted implementation state.
    val chain = a.steps.foldl({ holds: true, last: a.before, failed: false }, (prior, step) => {
      holds: prior.holds and step.before == prior.last and step.poisoned == prior.failed,
      last: step.after,
      failed: prior.failed or step.outcome != Succeeded,
    })
    chain.holds and chain.last == a.staged
  }

  pure def whenMarker(a: Attempt): bool = true
  pure def expectMarker(a: Attempt): bool = not(a.markerBefore) and a.markerStaged

  pure def whenCommitClean(a: Attempt): bool = a.finish == "commit" and not(hasFailure(a))
  pure def expectCommitClean(a: Attempt): bool =
    a.outcome == Succeeded and a.after == a.staged and a.markerAfter == a.markerStaged

  pure def whenCommitPoisoned(a: Attempt): bool = a.finish == "commit" and hasFailure(a)
  pure def expectCommitPoisoned(a: Attempt): bool =
    a.outcome == Failed("invalid_state") and a.after == a.before and a.markerAfter == a.markerBefore

  pure def whenAbort(a: Attempt): bool = a.finish == "abort"
  pure def expectAbort(a: Attempt): bool =
    a.outcome == Succeeded and a.after == a.before and a.markerAfter == a.markerBefore

  pure def classify(applies: bool, holds: bool): str =
    if (not(applies)) "unexercised" else if (holds) "pass" else "violation"

  pure def verdict(rule: str, a: Attempt): str =
    if (rule == "stepEffects") classify(whenSteps(a), expectSteps(a))
    else if (rule == "continuity") classify(whenContinuity(a), expectContinuity(a))
    else if (rule == "freshMarker") classify(whenMarker(a), expectMarker(a))
    else if (rule == "commitClean") classify(whenCommitClean(a), expectCommitClean(a))
    else if (rule == "commitPoisoned") classify(whenCommitPoisoned(a), expectCommitPoisoned(a))
    else if (rule == "explicitAbort") classify(whenAbort(a), expectAbort(a))
    else "unknown rule"
}
