module recorded_calls_adoption_rules {
  import recorded_calls_rules as common from "./recorded_calls_rules"
  import recorded_calls_adoption_checks as checks from "./recorded_calls_adoption_checks"
  import recorded_calls_adoption_validation as validation from "./recorded_calls_adoption_validation"

  type Attempt = (common::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario == 0) checks::retentionVerdicts(row.attempts)
    else if (row.scenario > 0 and row.scenario <= validation::cases.length())
      validation::verdicts({ ...row, scenario: row.scenario - 1 })
    else if (row.scenario == 1 + validation::cases.length()) checks::deepVerdicts(row.attempts)
    else List("unknown_history")

  pure val expected = List(checks::retentionExpected).concat(validation::expected).append(checks::deepExpected)
  pure def verdictAccepted(verdict: str): bool = common::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected
  pure val controlsPass = checks::controls and validation::controls
}
