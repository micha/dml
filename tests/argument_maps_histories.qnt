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
  // Only the expected attempt changes on retry. A new first insert makes a prefix commit observable.
  pure def pinnedRequest(returned: str): Request = source("request", List("p-pin", "d-pin", "double@1",
    "--invocation", "00000000-0000-4000-8000-000000000004", "--arg", "prefix=i64:731", "--arg", returned))
  pure val returnedPins: List[Request] = List(
    keyRequest("p-decoy", "d-decoy", "a=i64:12", "b=i64:30"),
    source("work", List("p-decoy", "@p-decoy", "decoy")), source("inspect", List("decoy")),
    pinnedRequest("x=from:t2:@decoy"),
    // A second attempt of p2 shares even the result commit with t2; it still cannot pin t2.
    source("work", List("p2", "@p2", "sibling")), source("inspect", List("sibling")),
    pinnedRequest("x=from:t2:@sibling"), pinnedRequest("x=from:t2:@t2"), source("inspect", List("p-pin")),
    source("work", List("p-pin", "@p-pin", "t-pin")), source("inspect", List("t-pin"))
  )
  pure val sixteenArgs = List("a=i64:901", "b=i64:902", "c=i64:903", "d=i64:904", "e=i64:905", "f=i64:906",
    "g=i64:907", "h=i64:908", "i=i64:909", "j=i64:910", "k=i64:911", "l=i64:912", "m=i64:913", "n=i64:914",
    "o=i64:915", "p=i64:916").foldl(List(), (args, arg) => args.append("--arg").append(arg))
  pure val argumentLimit: List[Request] = List(
    source("request", List("p-arity", "d-arity", "add@1", "--invocation", "00000000-0000-4000-8000-000000000005")
      .concat(sixteenArgs)),
    source("inspect", List("d-arity")),
    // Prepend a new singleton so that committing even the first insert would change the inventory.
    source("request", List("p-arity-over", "d-arity-over", "add@1", "--invocation", "00000000-0000-4000-8000-000000000006",
      "--arg", "q=i64:917").concat(sixteenArgs))
  )
  pure def capacityCase(pending, decision, requestPin, attempt, attemptPin, arg, table, tablePin) = {
    producer: List(
      source("request", List(pending, decision, "double@1", "--arg", arg)),
      source("work", List(pending, requestPin, attempt)),
      source("inspect", List(attempt))
    ),
    selected: List("--selected", attempt, attemptPin),
    table: table,
    tablePin: tablePin
  }
  pure val capacityCases = List(
    capacityCase("p-cap-a", "d-cap-a", "@p-cap-a", "t-cap-a", "@t-cap-a", "x=i64:1000", "cap-a", "@cap-a"),
    capacityCase("p-cap-b", "d-cap-b", "@p-cap-b", "t-cap-b", "@t-cap-b", "x=i64:1001", "cap-b", "@cap-b"),
    capacityCase("p-cap-c", "d-cap-c", "@p-cap-c", "t-cap-c", "@t-cap-c", "x=i64:1002", "cap-c", "@cap-c"),
    capacityCase("p-cap-d", "d-cap-d", "@p-cap-d", "t-cap-d", "@t-cap-d", "x=i64:1003", "cap-d", "@cap-d"),
    capacityCase("p-cap-e", "d-cap-e", "@p-cap-e", "t-cap-e", "@t-cap-e", "x=i64:1004", "cap-e", "@cap-e"),
    capacityCase("p-cap-f", "d-cap-f", "@p-cap-f", "t-cap-f", "@t-cap-f", "x=i64:1005", "cap-f", "@cap-f"),
    capacityCase("p-cap-g", "d-cap-g", "@p-cap-g", "t-cap-g", "@t-cap-g", "x=i64:1006", "cap-g", "@cap-g"),
    capacityCase("p-cap-h", "d-cap-h", "@p-cap-h", "t-cap-h", "@t-cap-h", "x=i64:1007", "cap-h", "@cap-h"),
    capacityCase("p-cap-i", "d-cap-i", "@p-cap-i", "t-cap-i", "@t-cap-i", "x=i64:1008", "cap-i", "@cap-i"),
    capacityCase("p-cap-j", "d-cap-j", "@p-cap-j", "t-cap-j", "@t-cap-j", "x=i64:1009", "cap-j", "@cap-j"),
    capacityCase("p-cap-k", "d-cap-k", "@p-cap-k", "t-cap-k", "@t-cap-k", "x=i64:1010", "cap-k", "@cap-k"),
    capacityCase("p-cap-l", "d-cap-l", "@p-cap-l", "t-cap-l", "@t-cap-l", "x=i64:1011", "cap-l", "@cap-l"),
    capacityCase("p-cap-m", "d-cap-m", "@p-cap-m", "t-cap-m", "@t-cap-m", "x=i64:1012", "cap-m", "@cap-m"),
    capacityCase("p-cap-n", "d-cap-n", "@p-cap-n", "t-cap-n", "@t-cap-n", "x=i64:1013", "cap-n", "@cap-n"),
    capacityCase("p-cap-o", "d-cap-o", "@p-cap-o", "t-cap-o", "@t-cap-o", "x=i64:1014", "cap-o", "@cap-o"),
    capacityCase("p-cap-p", "d-cap-p", "@p-cap-p", "t-cap-p", "@t-cap-p", "x=i64:1015", "cap-p", "@cap-p"),
    capacityCase("p-cap-q", "d-cap-q", "@p-cap-q", "t-cap-q", "@t-cap-q", "x=i64:1016", "cap-over", "@cap-over")
  )
  pure val capacityProducers = capacityCases.foldl(List(), (steps, candidate) => steps.concat(candidate.producer))
  pure val capacityFill = range(0, 16).foldl(List(source("define_table", List("cap-empty", "double"))), (steps, i) => {
    val candidate = capacityCases[i]
    val basis = if (i == 0) List("cap-empty", "@cap-empty")
      else List(capacityCases[i - 1].table, capacityCases[i - 1].tablePin)
    steps.append(source("update_table", basis.concat(List(candidate.table, "insert")).concat(candidate.selected)))
  })
  pure def capacityInsert(basis, pin) = {
    val candidate = capacityCases[16]
    source("update_table", List(basis, pin, candidate.table, "insert").concat(candidate.selected))
  }
  pure val capacityBoundary = List(
    source("inspect", List("cap-p")),
    capacityInsert("cap-p", "@cap-p"),
    source("update_table", List("cap-p", "@cap-p", "cap-reduced", "remove", "--key", "map-of:t-cap-a")),
    source("inspect", List("cap-reduced")),
    // Retry the same insert and output ref against the version with room for it.
    capacityInsert("cap-reduced", "@cap-reduced"),
    source("inspect", List("cap-over")),
    source("inspect", List("cap-p"))
  )
  pure val tableCapacity = capacityProducers.concat(capacityFill).concat(capacityBoundary)
  pure val pinStart = story.length() + tableEdits.length() + workFailures.length() + canonicalKeys.length()
  pure val arityStart = pinStart + returnedPins.length()
  pure val capacityStart = arityStart + argumentLimit.length()
  pure val fullStory = story.concat(tableEdits).concat(workFailures).concat(canonicalKeys).concat(returnedPins)
    .concat(argumentLimit).concat(tableCapacity)
  var histories: List[List[Request]]
  action init = histories' = List(fullStory)
  action step = histories' = histories
}
