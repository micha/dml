module argument_map_request_integrity_histories {
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure def request(pending, decision, arg, id) = source("request",
    List(pending, decision, "double@1", "--arg", arg, "--invocation", id))
  pure def inspect(name) = source("inspect", List(name))

  pure val requestIntegrityHistory = List(
    request("p-base", "d-base", "x=i64:42", "00000000-0000-4000-8000-000000000001"),
    request("p-other", "d-other", "x=i64:43", "00000000-0000-4000-8000-000000000002"),
    inspect("p-base"),
    inspect("p-other"),
    source("record_request_root", List("forged", "@p-base", "@p-other")),
    inspect("forged"),
    inspect("p-base")
  )
  var histories: List[List[Request]]
  action init = histories' = List(requestIntegrityHistory)
  action step = histories' = histories
}
