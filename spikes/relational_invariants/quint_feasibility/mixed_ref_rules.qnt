module mixed_ref_rules {
  type Ref = Absent | Target(str)
  type Outcome = Succeeded | Failed(str)
  type Attempt = { operation: str, before: Ref, requested: str, outcome: Outcome, after: Ref }

  pure val scenario = {
    operations: Set("create_ref", "update_ref"),
    targets: Set("a", "b"),
    maxSteps: 3,
  }
  pure val ruleIds = Set("duplicateCreate", "updateMissing", "updateExisting")

  pure def whenDuplicateCreate(a: Attempt): bool =
    a.operation == "create_ref" and a.before != Absent
  pure def expectDuplicateCreate(a: Attempt): bool =
    a.outcome == Failed("invalid_state") and a.after == a.before

  pure def whenUpdateMissing(a: Attempt): bool =
    a.operation == "update_ref" and a.before == Absent
  pure def expectUpdateMissing(a: Attempt): bool =
    a.outcome == Failed("not_found") and a.after == Absent

  pure def whenUpdateExisting(a: Attempt): bool =
    a.operation == "update_ref" and a.before != Absent
  pure def expectUpdateExisting(a: Attempt): bool =
    a.outcome == Succeeded and a.after == Target(a.requested)

  pure def classify(applies: bool, holds: bool): str =
    if (not(applies)) "unexercised" else if (holds) "pass" else "violation"

  pure def verdict(rule: str, a: Attempt): str =
    if (rule == "duplicateCreate") classify(whenDuplicateCreate(a), expectDuplicateCreate(a))
    else if (rule == "updateMissing") classify(whenUpdateMissing(a), expectUpdateMissing(a))
    else if (rule == "updateExisting") classify(whenUpdateExisting(a), expectUpdateExisting(a))
    else "unknown rule"
}
