module interpreter_verdict {
  type Change = { kind: str, key: str, before: str, after: str }
  type Attempt = {
    op: str, args: List[str], status: str, value: str, count: int,
    items: List[str], changes: List[Change], otherChanges: List[Change]
  }
  type Observation = { attempts: List[Attempt] }

  pure def historyVerdicts(row: Observation): List[str] = {
    val attempt = row.attempts[0]
    if (attempt.status != "ok" or attempt.op != "datum_encode") List("unexpected_observation")
    else if (attempt.args[1] == "0") List()
    else List("ok")
  }
  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(_rows: List[Observation], _results: List[List[str]]): bool = true
  pure val controlsPass = true
}
