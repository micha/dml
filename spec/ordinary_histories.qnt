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
  pure def selection(mode: str, ref: str, expected: str): List[str] = List(mode, ref, expected)
  pure val noSelection = selection("fresh", "", "")
  pure def invokeObserved(output: str, a: str, b: str, outer: List[str], double: List[str]): Request =
    sourceStep("invoke_observed", List("capture-one", "@capture-one", output, a, b).concat(outer).concat(double))
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

  pure val execution: List[Request] = List(
    sourceStep("defaults", List("defaults", "1")),                                              // 0
    sourceStep("capture", List("defaults", "@defaults", "capture-one")),                        // 1
    invokeObserved("owned", "13", "29", noSelection, noSelection),                             // 2
    inspect("source", "owned", "@owned"),                                                      // 3
    invokeObserved("outer-hit", "13", "29", selection("require-selected", "owned", "@owned"),
      noSelection),                                                                             // 4
    sourceStep("inspect_observed", List("outer-hit", "@outer-hit")),                            // 5
    invokeObserved("add-overflow", "9223372036854775807", "1", noSelection, noSelection),        // 6
    inspect("source", "add-overflow", "@add-overflow"),                                         // 7
    inspect("source", "main", "@owned"),                                                       // 8
    sourceStep("select_double", List("owned", "@owned", "selected")),                           // 9
    invokeObserved("inner-hit", "29", "13", noSelection,
      selection("require-selected", "selected", "@selected")),                                  // 10
    sourceStep("inspect_observed", List("inner-hit", "@inner-hit")),                             // 11
    invokeObserved("double-absent", "30", "12", noSelection,
      selection("require-selected", "absent", "")),                                            // 12
    inspect("source", "double-absent", "@double-absent")                                       // 13
  )

  pure val producerInvocation = "90000000-0000-4000-8000-000000000001"
  pure val retryInvocation = "90000000-0000-4000-8000-000000000002"
  pure val requestIdentity: List[Request] = {
    val reuse = outer("require-selected", "producer", "@producer")
    List(
      sourceStep("defaults", List("defaults", "1")),
      sourceStep("capture", List("defaults", "@defaults", "capture-one")),
      fromOne("producer", "13", "29", List("--invocation", producerInvocation)),
      fromOne("later", "13", "30", List()),
      fromOne("retry", "13", "29", reuse.concat(List("--invocation", producerInvocation))),
      fromOne("retry", "13", "29", reuse.concat(List("--invocation", retryInvocation))),
      inspect("source", "retry", "@retry")
    )
  }

  pure val refAliases: List[Request] = List(
    sourceStep("defaults", List("defaults", "1")),
    sourceStep("capture", List("defaults", "@defaults", "capture-one")),
    fromOne("first", "13", "30", List()),
    // Both slots expect absence, so pin checks alone cannot reject the alias.
    fromOne("retry", "13", "29", List("--double-mode", "try-selected", "--double-selected-ref", "retry")),
    fromOne("capture-one", "13", "29", List()),
    fromOne("main", "13", "29", List()),
    fromOne("retry", "13", "29", List("--double-mode", "try-selected", "--double-selected-ref", "absent")),
    inspect("source", "retry", "@retry")
  )

  pure def scripted(output: str, a: str, b: str, instructions: List[str]): Request =
    sourceStep("invoke_callbacks", List("capture-one", "@capture-one", output, a, b).concat(instructions))
  pure val guestAdd = List("get:a", "get:b", "invoke:add:arguments:sum")
  pure val callbackLifecycle: List[Request] = story.slice(0, 3).concat(List(
    scripted("poisoned", "29", "13", guestAdd.concat(List("escape:poisoned:sum", "copy:sum:foreign",
      "make-arguments:x:foreign:invalid", "make-arguments:x:sum:valid", "return:sum"))),
    inspect("source", "poisoned", "@poisoned"),
    sourceStep("escaped_arguments", List("poisoned", "x")),
    scripted("ended", "30", "12", guestAdd.concat(List("escape:ended:sum", "return:sum"))),
    inspect("source", "ended", "@ended"),
    sourceStep("escaped_arguments", List("ended", "x")),
    inspect("source", "main", "@first")
  ))

  pure def refFault(output: str, a: str, b: str, checkpoint: str, ref: str, role: str): Request =
    sourceStep("invoke_ref_fault", List("capture-one", "@capture-one", output, a, b, checkpoint, ref, role))
  pure val lateRollback: List[Request] = story.slice(0, 3).concat(List(
    refFault("rollback-add", "29", "13", "add", "rollback-add", "ordinary-example-double-attempt-v1"),
    inspect("source", "rollback-add", "@rollback-add"),
    inspect("source", "main", "@first"),
    refFault("rollback-double", "31", "11", "double", "main", "ordinary-example-finished-v1"),
    inspect("source", "rollback-double", "@rollback-double"),
    inspect("source", "main", "@first")
  ))

  pure val typedInputs = List("bool:true", "float:1.5", "int:9223372036854775808", "int:-9223372036854775809")
  pure val typedStory = typedInputs.foldl(story.slice(0, 2), (out, value) =>
    out.append(sourceStep("python_call", List("invoke", "bytes:capture-one", "id:capture-one", "bytes:call", value, "int:29"))))

  var histories: List[List[Request]]
  action init = histories' = List(story, pinning, execution, requestIdentity, refAliases, callbackLifecycle, lateRollback, typedStory)
  action step = histories' = histories
}
