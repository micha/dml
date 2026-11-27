module recorded_calls_verdicts {
  import recorded_calls_rules as legacy from "./recorded_calls_rules"
  import recorded_calls_outbound_histories.outboundRequests from "./recorded_calls_outbound_histories"
  import recorded_calls_plan_histories.planExpected from "./recorded_calls_plan_histories"
  import recorded_calls_plan_rules.planVerdicts from "./recorded_calls_plan_rules"
  import recorded_calls_receipt_histories.receiptExpected from "./recorded_calls_receipt_histories"
  import recorded_calls_receipt_rules as receipts from "./recorded_calls_receipt_rules"

  type Attempt = (legacy::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure val planOffset = legacy::outboundOffset + outboundRequests.length()
  pure val receiptOffset = planOffset + planExpected.length()
  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario < planOffset) legacy::historyVerdicts(row)
    else if (row.scenario < receiptOffset) planVerdicts(row.scenario - planOffset, row.attempts)
    else if (row.scenario < receiptOffset + receiptExpected.length())
      receipts::receiptVerdicts(row.scenario - receiptOffset, row.attempts)
    else List("unknown_history")

  pure def verdictAccepted(verdict: str): bool = legacy::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == receiptOffset + receiptExpected.length() and
      legacy::coveragePass(rows.slice(0, planOffset), verdicts.slice(0, planOffset)) and
      verdicts.slice(planOffset, verdicts.length()) == planExpected.concat(receiptExpected)
  pure val controlsPass = legacy::controlsPass and receipts::receiptControls
}
