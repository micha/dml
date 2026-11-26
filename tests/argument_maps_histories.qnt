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
  // Continue in the source repo: two producers for 42 and a surviving row for 43.
  pure val removedTable = List("--table-ref", "removed", "--table-commit", "@removed")
  pure val tableEdits: List[Request] = List(
    source("request", List("p6", "d6", "double@2", "--arg", "x=from:t2:@t2")),
    source("work", List("p6", "@p6", "t6")),
    source("inspect", List("t6")),
    source("update_table", List("selected", "@selected", "both", "insert", "--selected", "t5", "@t5")),
    source("inspect", List("both")),
    source("update_table", List("both", "@both", "same", "adopt", "--selected", "t1", "@t1")),
    source("update_table", List("both", "@both", "adopted", "adopt", "--selected", "t6", "@t6")),
    source("inspect", List("adopted")),
    source("request", List("p7", "d7", "double@1", "--arg", "x=i64:42", "--mode", "require-selected",
      "--table-ref", "adopted", "--table-commit", "@adopted")),
    source("inspect", List("d7")),
    source("update_table", List("adopted", "@adopted", "removed", "remove", "--key", "map-of:t1")),
    source("inspect", List("removed")),
    source("request", List("p8", "d8", "double@1", "--arg", "x=i64:42", "--mode", "try-selected").concat(removedTable)),
    source("inspect", List("d8")),
    source("request", List("p9", "d9", "double@1", "--arg", "x=i64:43", "--mode", "require-selected").concat(removedTable)),
    source("inspect", List("d9")),
    source("inspect", List("d3"))
  )
  // The first add getter succeeds before the missing key or wrong type at b.
  pure val workFailures: List[Request] = List(
    source("request", List("p-missing", "d-missing", "add@1", "--arg", "a=i64:13")),
    source("work", List("p-missing", "@p-missing", "t-missing")),
    source("request", List("p-typed", "d-typed", "add@1", "--arg", "a=i64:13", "--arg", "b=string:29")),
    source("work", List("p-typed", "@p-typed", "t-typed")),
    source("request", List("p-overflow", "d-overflow", "double@1", "--arg", "x=i64:4611686018427387904")),
    source("work", List("p-overflow", "@p-overflow", "t-overflow")),
    // Preserve the single-getter double cases as well as the failures after add read a.
    source("request", List("p-no-x", "d-no-x", "double@1", "--arg", "y=i64:42")),
    source("work", List("p-no-x", "@p-no-x", "t-no-x")),
    source("request", List("p-string-x", "d-string-x", "double@1", "--arg", "x=string:42")),
    source("work", List("p-string-x", "@p-string-x", "t-string-x"))
  )
  // Spell the key bytes explicitly; only the CLI --arg values are decoded for execution.
  pure val composed = "key-hex:c3a9=i64:29"
  pure val decomposed = "key-hex:65cc81=i64:29"
  pure def keyRequest(pending: str, decision: str, first: str, second: str): Request =
    source("request", List(pending, decision, "add@1", "--arg", first, "--arg", second))
  pure val canonicalKeys: List[Request] = List(
    keyRequest("p-nfc", "d-nfc", "a=i64:13", composed), source("inspect", List("p-nfc")),
    keyRequest("p-reversed", "d-reversed", decomposed, "a=i64:13"), source("inspect", List("p-reversed")),
    keyRequest("p-nfd", "d-nfd", "a=i64:13", decomposed), source("inspect", List("p-nfd")),
    keyRequest("p-duplicate", "d-duplicate", composed, decomposed),
    // Stage a new singleton before the duplicate: the reversed request already stored {é: 29}.
    keyRequest("p-conflict", "d-conflict", "key-hex:c3a9=i64:30", decomposed)
  )
  pure val fullStory = story.concat(tableEdits).concat(workFailures).concat(canonicalKeys)
  var histories: List[List[Request]]
  action init = histories' = List(fullStory)
  action step = histories' = histories
}
