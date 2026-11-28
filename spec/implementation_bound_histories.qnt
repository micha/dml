module implementation_bound_histories {
  import ordinary_histories as legacy from "./ordinary_histories"

  type Request = { op: str, args: List[str] }
  pure def sourceStep(op, args) = legacy::sourceStep(op, args)
  pure def inspect(repo, target, expected) = legacy::inspect(repo, target, expected)
  pure def outer(mode, target, expected) = legacy::outer(mode, target, expected)
  pure def inner(mode, target, expected) = legacy::inner(mode, target, expected)
  pure def graft(repo, kind, original, alternate, output) = legacy::graft(repo, kind, original, alternate, output)
  pure def replicate(original, output) = legacy::replicate(original, output)

  pure def observed(cap: str, output: str, a: str, b: str, flags: List[str]): Request = {
    val expected = if (cap == "capture-a") "@capture-a" else "@capture-b"
    sourceStep("invoke_observed", List(cap, expected, output, a, b).concat(flags))
  }

  pure val storyBound: List[Request] = List(
    sourceStep("defaults", List("defaults", "1", "--implementation-bound")),                    // 0
    sourceStep("capture", List("defaults", "@defaults", "capture-a")),                           // 1
    observed("capture-a", "first", "13", "29", List()),                                         // 2
    inspect("source", "first", "@first"),                                                       // 3
    sourceStep("select_double", List("first", "@first", "old-double")),                           // 4
    sourceStep("defaults", List("defaults", "2", "--expected", "@defaults")),                    // 5
    sourceStep("capture", List("defaults", "@defaults", "capture-b")),                          // 6
    observed("capture-b", "outer-hit", "13", "29", outer("require-selected", "first", "@first")
      .append("--named-inputs")),                                                                 // 7
    inspect("source", "outer-hit", "@outer-hit"),                                                // 8
    observed("capture-b", "b-fresh", "13", "29", List("--named-inputs")),                                       // 9
    inspect("source", "b-fresh", "@b-fresh"),                                                    // 10
    observed("capture-b", "inner-hit", "13", "29", inner("require-selected", "old-double", "@old-double")), // 11
    inspect("source", "inner-hit", "@inner-hit"),                                                // 12
    observed("capture-a", "still-a", "13", "30", outer("try-selected", "first", "@first")),    // 13
    inspect("source", "still-a", "@still-a"),                                                    // 14
    observed("capture-b", "swapped", "29", "13", outer("require-selected", "first", "@first")), // 15
    observed("capture-b", "stale", "13", "29", outer("try-selected", "first", "@b-fresh")),      // 16
    graft("source", "finished", "inner-hit", "", "bad-finished"),                                // 17
    observed("capture-b", "poisoned", "13", "30",
      outer("try-selected", "bad-finished", "@bad-finished")),                                     // 18
    replicate("outer-hit", "replica-hit"),                                                       // 19
    sourceStep("retire", List()),                                                                 // 20
    inspect("replica", "replica-hit", "@replica-hit")                                             // 21
  )

  var histories: List[List[Request]]
  action init = histories' = List(storyBound)
  action step = histories' = histories
}
