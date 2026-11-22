module read_context_rules {
  type Step = { operation: str, outcome: str, readAfter: str }
  type Attempt = { before: str, steps: List[Step], exitMode: str, exitOutcome: str,
                   endedRead: str, after: str, probeRef: str }

  pure val scenario = {
    operations: Set("commit", "create_ref", "missing_read"),
    exits: Set("normal", "exception"),
    maxSteps: 3,
  }
  pure val ruleIds = Set("rejectionStatus", "readStillUsable", "contextExit", "noPublication")

  pure def whenSteps(a: Attempt): bool = a.steps.length() != 0

  pure def expectedRejection(s: Step): bool =
    if (s.operation == "missing_read") s.outcome == "not_found"
    else if (s.operation == "commit" or s.operation == "create_ref") s.outcome == "invalid_state"
    else false

  pure def expectRejectionStatus(a: Attempt): bool =
    a.steps.foldl(true, (holds, step) => holds and expectedRejection(step))

  // Compare against the actual pre-context ID, not a model-predicted target.
  pure def expectReadStillUsable(a: Attempt): bool =
    a.steps.foldl(true, (holds, step) => holds and step.readAfter == a.before)

  pure def expectContextExit(a: Attempt): bool =
    a.endedRead == "invalid_state" and
      (if (a.exitMode == "normal") a.exitOutcome == "ok"
       else if (a.exitMode == "exception") a.exitOutcome == "same_exception"
       else false)

  pure def expectNoPublication(a: Attempt): bool =
    a.after == a.before and a.probeRef == "not_found"

  pure def classify(applies: bool, holds: bool): str =
    if (not(applies)) "unexercised" else if (holds) "pass" else "violation"

  pure def verdict(rule: str, a: Attempt): str =
    if (rule == "rejectionStatus") classify(whenSteps(a), expectRejectionStatus(a))
    else if (rule == "readStillUsable") classify(whenSteps(a), expectReadStillUsable(a))
    else if (rule == "contextExit") classify(true, expectContextExit(a))
    else if (rule == "noPublication") classify(true, expectNoPublication(a))
    else "unknown rule"
}
