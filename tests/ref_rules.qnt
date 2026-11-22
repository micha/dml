module ref_rules {
  type Change = { kind: str, key: str, before: str, after: str }
  type Attempt = {
    refKey: str,
    targetId: str,
    createStatus: str,
    commitStatus: str,
    changes: List[Change]
  }

  type Observation = { attempts: List[Attempt] }

  pure def verdictAccepted(verdict: str): bool = verdict == "created" or verdict == "duplicate"

  pure def coveragePass(_evidence: List[Observation], verdicts: List[List[str]]): bool = {
    val seen = verdicts.foldl(Set(), (allSeen, row) =>
      row.foldl(allSeen, (seen, verdict) => seen.union(Set(verdict))))
    Set("created", "duplicate").subseteq(seen)
  }

  pure def addition(key: str, value: str): Change =
    { kind: "added", key: key, before: "", after: value }

  pure def stepVerdict(occupied: bool, attempt: Attempt): str =
    if (occupied) {
      if (attempt.createStatus != "invalid_state" or attempt.commitStatus != "invalid_state")
        "duplicate_status"
      else if (attempt.changes != List()) "duplicate_inventory"
      else "duplicate"
    } else {
      if (attempt.createStatus != "ok" or attempt.commitStatus != "ok") "create_status"
      else if (attempt.changes != List(addition(attempt.refKey, attempt.targetId)))
        "create_inventory"
      else "created"
    }

  // The expected state follows the requests, not the statuses returned by the implementation.
  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ keys: Set(), verdicts: List() }, (state, attempt) => {
      keys: state.keys.union(Set(attempt.refKey)),
      verdicts: state.verdicts.append(stepVerdict(state.keys.contains(attempt.refKey), attempt))
    }).verdicts

  // Synthetic controls exercise the oracle, not the storage implementation.
  pure val refKey = "726566732f68656164732f6d61696e"
  pure val targetA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  pure val targetB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  pure val controlsPass = all {
    stepVerdict(true, {
      refKey: refKey, targetId: targetB, createStatus: "invalid_state", commitStatus: "invalid_state",
      changes: List({ kind: "modified", key: refKey, before: targetA, after: targetB })
    }) == "duplicate_inventory",
    stepVerdict(false, {
      refKey: refKey, targetId: targetA, createStatus: "ok", commitStatus: "ok",
      changes: List(addition(refKey, targetA), addition("756e72656c61746564", "00"))
    }) == "create_inventory"
  }
}
