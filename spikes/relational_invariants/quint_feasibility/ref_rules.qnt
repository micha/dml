module ref_rules {
  type Ref = Absent | Target(str)
  type Outcome = Created | Failed(str)
  type Attempt = { before: Ref, requested: str, outcome: Outcome, after: Ref }

  // The model and concrete test share this action alphabet and exploration bound.
  pure val scenario = { operation: "create_ref", targets: Set("a", "b", "c"), maxSteps: 4 }

  // Applies to create_ref with an already valid target commit, in a fresh write transaction.
  pure def whenRefExists(a: Attempt): bool = a.before != Absent

  pure def expectRejectedAndPreserved(a: Attempt): bool =
    a.outcome == Failed("invalid_state") and a.after == a.before

  pure def verdict(a: Attempt): str =
    if (not(whenRefExists(a))) "unexercised"
    else if (expectRejectedAndPreserved(a)) "pass"
    else "violation"
}
