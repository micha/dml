module argument_maps_histories {
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure val selection = List("--table-ref", "selected", "--table-commit", "@selected")
  // Each retry changes only the decision ref, not the requested invocation.
  pure def freshAdd(decision: str): Request = source("request", List("p2", decision, "add@1",
    "--invocation", "00000000-0000-4000-8000-000000000002", "--arg", "a=i64:13", "--arg", "b=i64:29"))
  pure def selectedDouble(decision: str): Request = source("request", List("p3", decision, "double@2",
    "--invocation", "00000000-0000-4000-8000-000000000003", "--arg", "x=from:t2:@t2",
    "--mode", "try-selected").concat(selection))
  pure val story: List[Request] = List(
    source("request", List("p1", "d1", "double@1", "--arg", "x=i64:42")),
    source("work", List("p1", "@p1", "t1")),
    source("inspect", List("t1")),
    source("define_table", List("empty", "double")),
    source("update_table", List("empty", "@empty", "selected", "insert", "--selected", "t1", "@t1")),
    freshAdd("d1"), freshAdd("d2"),
    source("work", List("p2", "@p2", "t2")),
    source("inspect", List("t2")),
    selectedDouble("d1"), selectedDouble("d3"),
    source("inspect", List("d3")),
    source("request", List("p-type", "d-type", "double@2", "--arg", "x=string:42",
      "--mode", "require-selected").concat(selection)),
    source("request", List("p-key", "d-key", "double@2", "--arg", "y=i64:42",
      "--mode", "require-selected").concat(selection)),
    source("request", List("p-stale", "d-stale", "double@2", "--arg", "x=i64:42",
      "--mode", "try-selected", "--table-ref", "selected", "--table-commit", "@empty")),
    source("request", List("p4", "d4", "add@1", "--arg", "a=i64:13", "--arg", "b=i64:30")),
    source("work", List("p4", "@p4", "t4")),
    source("inspect", List("t4")),
    source("request", List("p5", "d5", "double@2", "--arg", "x=from:t4:@t4", "--mode", "try-selected").concat(selection)),
    source("inspect", List("d5")),
    source("work", List("p5", "@p5", "t5")),
    source("inspect", List("t5")),
    { op: "replicate", args: List("replica", "d3", "snapshot") },
    { op: "inspect", args: List("replica", "snapshot") }
  )
  var histories: List[List[Request]]
  action init = histories' = List(story)
  action step = histories' = histories
}
