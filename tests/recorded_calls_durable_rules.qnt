module recorded_calls_durable_rules {
  import recorded_calls_rules as common from "./recorded_calls_rules"
  import recorded_calls_plan_histories.planExpected from "./recorded_calls_plan_histories"
  import recorded_calls_plan_rules.planVerdicts from "./recorded_calls_plan_rules"
  import recorded_calls_receipt_histories.receiptExpected from "./recorded_calls_receipt_histories"
  import recorded_calls_receipt_rules as receipts from "./recorded_calls_receipt_rules"

  type Attempt = (common::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure val durableExpected = planExpected.concat(receiptExpected)
  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario < planExpected.length()) planVerdicts(row.scenario, row.attempts)
    else if (row.scenario < durableExpected.length())
      receipts::receiptVerdicts(row.scenario - planExpected.length(), row.attempts)
    else List("unknown_history")

  pure def verdictAccepted(verdict: str): bool = common::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == durableExpected.length() and verdicts == durableExpected
  pure val controlsPass = receipts::receiptControls
}
