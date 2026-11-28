module builtin_primitive_histories {
  import builtin_primitive_fixture.* from "./builtin_primitive_fixture"
  import builtins_profile_histories as profiles from "./builtins_profile_histories"
  import builtins_values_histories as values from "./builtins_values_histories"

  pure val requested = profiles::profileHistories.concat(values::valueHistories)
  var histories: List[List[Request]]
  action init = histories' = requested
  action step = histories' = histories
}
