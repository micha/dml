module recorded_calls_durable_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_plan_histories.planRequests from "./recorded_calls_plan_histories"
  import recorded_calls_receipt_histories.receiptRequests from "./recorded_calls_receipt_histories"

  var histories: List[List[Request]]
  action init = histories' = planRequests.concat(receiptRequests)
  action step = histories' = histories
}
