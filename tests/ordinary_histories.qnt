module ordinary_histories {
  type Request = { op: str, args: List[str] }
  pure def sourceStep(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure def invoke(capture: str, expected: str, output: str, a: str, b: str, controls: List[str]): Request =
    sourceStep("invoke", List(capture, expected, output, a, b).concat(controls))
  pure def fromOne(output: str, a: str, b: str, controls: List[str]): Request =
    invoke("capture-one", "@capture-one", output, a, b, controls)
  pure def outer(mode: str, ref: str, expected: str): List[str] =
    List("--mode", mode, "--selected-ref", ref, "--selected", expected)
  pure def inner(mode: str, ref: str, expected: str): List[str] =
    List("--double-mode", mode, "--double-selected-ref", ref, "--double-selected", expected)
  pure def inspect(repo: str, ref: str, expected: str): Request =
    { op: "inspect", args: List(repo, ref, "--expected", expected) }
  pure def graft(repo: str, kind: str, original: str, alternate: str, output: str): Request =
    { op: "graft", args: List(repo, kind, original, alternate, output) }
  pure def replicate(original: str, output: str): Request =
    { op: "replicate", args: List("replica", original, output) }

  pure val story: List[Request] = List(
    sourceStep("defaults", List("defaults", "1")),                                               // 0
    sourceStep("capture", List("defaults", "@defaults", "capture-one")),                         // 1
    fromOne("first", "13", "29", List()),                                                        // 2
    inspect("source", "first", "@first"),                                                        // 3
    sourceStep("select_double", List("first", "@first", "old-double")),                           // 4
    sourceStep("defaults", List("defaults", "2", "--expected", "@defaults")),                      // 5
    sourceStep("capture", List("defaults", "@defaults", "capture-two")),                         // 6
    fromOne("still-pinned", "13", "29", List()),                                                 // 7
    fromOne("outer-hit", "13", "29", outer("require-selected", "first", "@first")),               // 8
    inspect("source", "outer-hit", "@outer-hit"),                                                // 9
    fromOne("inner-hit", "29", "13", outer("try-selected", "first", "@first")
      .concat(inner("require-selected", "old-double", "@old-double"))),                           // 10
    inspect("source", "inner-hit", "@inner-hit"),                                                // 11
    fromOne("inner-miss", "13", "30", inner("try-selected", "old-double", "@old-double")),         // 12
    invoke("capture-two", "@capture-two", "moved", "13", "29", outer("try-selected", "first", "@first")
      .concat(inner("try-selected", "old-double", "@old-double"))),                               // 13
    fromOne("outer-required", "29", "13", outer("require-selected", "first", "@first")),          // 14
    fromOne("add-survives-miss", "13", "31",
      inner("require-selected", "old-double", "@old-double")),                                    // 15
    fromOne("add-survives-overflow", "4611686018427387904", "0", List()),                          // 16
    fromOne("first", "13", "32", List()),                                                        // 17 occupied output
    invoke("capture-one", "@capture-two", "stale-capture", "13", "29", List()),                   // 18
    fromOne("stale-outer", "13", "29", outer("try-selected", "first", "@still-pinned")),           // 19
    fromOne("stale-inner", "13", "29", outer("require-selected", "first", "@first")
      .concat(inner("try-selected", "old-double", "@first"))),                                   // 20 preflight even on hit
    graft("source", "finished", "inner-hit", "", "bad-finished"),                                // 21
    fromOne("poison-outer", "13", "33", outer("try-selected", "bad-finished", "@bad-finished")),   // 22
    graft("source", "double", "old-double", "inner-hit", "bad-double"),                          // 23
    fromOne("poison-inner", "13", "33", inner("try-selected", "bad-double", "@bad-double")),       // 24
    inspect("source", "add-survives-miss", "@add-survives-miss"),                                  // 25
    inspect("source", "add-survives-overflow", "@add-survives-overflow"),                          // 26
    replicate("outer-hit", "replica-outer"),                                                     // 27
    replicate("inner-hit", "replica-inner"),                                                     // 28
    sourceStep("retire", List()),                                                                // 29
    inspect("replica", "replica-outer", "@replica-outer"),                                        // 30
    inspect("replica", "replica-inner", "@replica-inner"),                                        // 31
    graft("replica", "finished", "replica-inner", "", "bad-replica"),                             // 32
    inspect("replica", "bad-replica", "@bad-replica")                                             // 33
  )

  pure val pinning: List[Request] = List(
    sourceStep("defaults", List("defaults", "1")),
    sourceStep("capture", List("defaults", "@defaults", "capture-one")),
    fromOne("first", "13", "29", List()),
    sourceStep("select_double", List("first", "@first", "selected")),
    fromOne("alternate", "13", "30", List()),
    sourceStep("select_double", List("alternate", "@alternate", "replacement")),
    { op: "invoke_live", args: List("caller", "source", "capture-one", "@capture-one", "pinned",
      "29", "13", "require-selected", "selected", "@selected") },
    // While caller's invocation is live: after add commits, before double starts.
    { op: "txn_begin", args: List("bookmark-editor", "edit", "source") },
    { op: "txn_ref_update", args: List("bookmark-editor", "edit", "selected", "@replacement") },
    { op: "txn_commit", args: List("bookmark-editor", "edit") },
    inspect("source", "pinned", "@pinned")
  )

  pure val ownership: List[Request] = List(
    sourceStep("defaults", List("defaults", "1")),
    sourceStep("capture", List("defaults", "@defaults", "capture-one")),
    sourceStep("invoke_observed", List("capture-one", "@capture-one", "owned", "13", "29")),
    inspect("source", "owned", "@owned")
  )

  var histories: List[List[Request]]
  action init = histories' = List(story, pinning, ownership)
  action step = histories' = histories
}
