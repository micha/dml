module argument_map_returned_source_histories {
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure def inspect(name: str): Request = source("inspect", List(name))
  pure def producer(pending: str, pin: str, decision: str, attempt: str, a: str, b: str,
    invocation: str, id: str): List[Request] = List(
    source("request", List(pending, decision, "add@1", "--arg", a, "--arg", b, "--invocation", invocation)),
    source("work", List(pending, pin, attempt, "--attempt-id", id)),
    inspect(attempt)
  )

  pure val returnedSourceHistory = producer("p-exact", "@p-exact", "d-exact", "t-exact", "a=i64:13", "b=i64:29",
    "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000101")
    .concat(producer("p-other", "@p-other", "d-other", "t-other", "a=i64:12", "b=i64:30",
      "00000000-0000-4000-8000-000000000002", "00000000-0000-4000-8000-000000000102"))
    .concat(List(
      source("request", List("p-consumer", "d-consumer", "double@1", "--arg", "x=from:t-exact:@t-exact",
        "--invocation", "00000000-0000-4000-8000-000000000003")),
      inspect("p-consumer"),
      source("record_returned_source", List("substituted", "@p-consumer", "@t-other")),
      inspect("substituted"),
      inspect("p-consumer")
    ))
  var histories: List[List[Request]]
  action init = histories' = List(returnedSourceHistory)
  action step = histories' = histories
}
