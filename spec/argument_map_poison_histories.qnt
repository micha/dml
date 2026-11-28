module argument_map_poison_histories {
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure val ids = List(
    "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002",
    "00000000-0000-4000-8000-000000000003", "00000000-0000-4000-8000-000000000004",
    "00000000-0000-4000-8000-000000000005", "00000000-0000-4000-8000-000000000006",
    "00000000-0000-4000-8000-000000000007", "00000000-0000-4000-8000-000000000008",
    "00000000-0000-4000-8000-000000000009")
  pure def request(pending, decision, arg, n, route) = source("request",
    List(pending, decision, "double@1", "--arg", arg, "--invocation", ids[n - 1]).concat(route))
  pure def work(pending, pin, attempt, n) = source("work", List(pending, pin, attempt, "--attempt-id", ids[n - 1]))
  pure def inspect(ref) = source("inspect", List(ref))
  pure def route(mode, table, pin) = List("--mode", mode, "--table-ref", table, "--table-commit", pin)

  pure val poisonHistory = List(
    request("p-one", "d-one", "x=i64:42", 1, List()),
    work("p-one", "@p-one", "t-one", 2),
    inspect("t-one"),
    request("p-other", "d-other", "x=i64:43", 3, List()),
    work("p-other", "@p-other", "t-other", 4),
    inspect("t-other"),
    source("define_table", List("empty", "double")),
    source("update_table", List("empty", "@empty", "selected", "insert", "--selected", "t-one", "@t-one")),
    request("p-hit", "d-hit", "x=i64:42", 5, route("try-selected", "selected", "@selected")),
    inspect("d-hit"),
    // Keep the live 42 entry. Insert a 43 key that incorrectly selects the 42 attempt.
    source("record_table_edit", List("poison", "insert", "@selected", "map-of:t-other", "@t-one")),
    source("record_table_edit", List("buried", "remove", "@poison", "map-of:t-other")),
    request("p-poisoned", "d-poisoned", "x=i64:42", 6, route("try-selected", "poison", "@poison")),
    request("p-buried", "d-buried", "x=i64:42", 7, route("try-selected", "buried", "@buried")),
    request("p-fresh", "d-fresh", "x=i64:42", 8, route("fresh", "buried", "@buried")),
    inspect("d-fresh"),
    request("p-stale", "d-stale", "x=i64:42", 9, route("fresh", "buried", "@poison")),
    inspect("d-stale")
  )
  var histories: List[List[Request]]
  action init = histories' = List(poisonHistory)
  action step = histories' = histories
}
