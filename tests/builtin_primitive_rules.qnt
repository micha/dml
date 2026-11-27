module builtin_primitive_rules {
  import builtin_primitive_evidence.* from "./builtin_primitive_evidence"
  export builtin_primitive_evidence.*
  import builtin_primitive_histories as histories from "./builtin_primitive_histories"
  import builtins_profile_histories as profiles from "./builtins_profile_histories"
  import builtins_profile_rules as p from "./builtins_profile_rules"
  import builtins_values_rules as v from "./builtins_values_rules"

  type Observation = { scenario: int, attempts: List[Attempt] }
  pure def historyVerdicts(row: Observation): List[str] = {
    val split = profiles::profileHistories.length()
    if (row.scenario < 0 or row.scenario >= histories::requested.length()) List("unexpected_history")
    else if (row.scenario < split) p::profileVerdicts(row.scenario, row.attempts)
    else v::valueVerdicts(row.scenario - split, row.attempts)
  }
  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool = all {
    evidence.length() == histories::requested.length(), verdicts.length() == evidence.length(),
    evidence.indices().forall(i => evidence[i].scenario == i and
      verdicts[i].length() == histories::requested[i].length() and
      verdicts[i].foldl(true, (ok, verdict) => ok and verdictAccepted(verdict)))
  }
  pure val controlsPass = p::profileControls and v::valueControls
}
