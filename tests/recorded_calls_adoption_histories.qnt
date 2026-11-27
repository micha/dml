module recorded_calls_adoption_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_adoption_checks as checks from "./recorded_calls_adoption_checks"
  import recorded_calls_adoption_validation as validation from "./recorded_calls_adoption_validation"

  var histories: List[List[Request]]
  action init = histories' = List(checks::retention).concat(validation::cases).append(checks::deep)
  action step = histories' = histories
}
