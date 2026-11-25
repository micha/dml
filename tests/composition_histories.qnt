module composition_histories {
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  // A @ref token is resolved from live native receipts by the runner. The
  // ref/pin pairs here are explicit so stale-pin controls can keep their names.
  pure val pendingPins = Map("q1" -> "@q1", "q2" -> "@q2", "q3" -> "@q3", "q5" -> "@q5", "q7" -> "@q7", "q8" -> "@q8")
  pure val compositionPins = Map("c2" -> "@c2", "c4" -> "@c4", "c6" -> "@c6", "c8" -> "@c8")
  pure val ids = Map(
    "1" -> "12345678-abcd-4abc-8abc-123456789ab1", "2" -> "12345678-abcd-4abc-8abc-123456789ab2",
    "3" -> "12345678-abcd-4abc-8abc-123456789ab3", "4" -> "12345678-abcd-4abc-8abc-123456789ab4",
    "5" -> "12345678-abcd-4abc-8abc-123456789ab5", "6" -> "12345678-abcd-4abc-8abc-123456789ab6",
    "7" -> "12345678-abcd-4abc-8abc-123456789ab7", "8" -> "12345678-abcd-4abc-8abc-123456789ab8",
    "9" -> "12345678-abcd-4abc-8abc-123456789ab9")
  pure def inspect(role: str, ref: str, pin: str): Request =
    { op: "inspect", args: List(role, ref, "--expected", pin) }
  pure def invocation(n: str): List[str] = List("--invocation", ids.get(n))
  pure def add(pending: str, a: str, b: str, n: str): Request =
    source("request_add", List("config", "@config", pending, a, b).concat(invocation(n)))
  pure def work(pending: str, t: str, n: str): Request =
    source("work", List(pending, pendingPins.get(pending), t, "--attempt-id", ids.get(n)))
  pure def compose(t: str, pin: str, output: str): Request = source("compose", List(t, pin, output))
  pure def double(basis: str, pending: str, d: str, mode: str, selection: str, pin: str, n: str): Request = {
    val selected = List("--selected-ref", selection).concat(if (pin == "") List() else List("--selected", pin))
    val command = List(basis, compositionPins.get(basis), pending, d, "--mode", mode)
    source("request_double", command.concat(selected).concat(invocation(n)))
  }

  // Author eight requests and execute six attempts. Controls that author
  // malformed ancestry copy native rows; they do not execute either callable.
  pure val story: List[Request] = List(
    source("define", List("config")),                                             // 0
    add("q1", "13", "29", "1"),                                                  // 1
    work("q1", "t1", "1"),                                                       // 2
    inspect("source", "t1", "@t1"),                                               // 3
    compose("t1", "@t1", "c2"),                                                   // 4
    double("c2", "q2", "d2", "try-selected", "t2", "", "2"),                     // 5
    inspect("source", "d2", "@d2"),                                               // 6
    work("q2", "t2", "2"),                                                       // 7
    inspect("source", "t2", "@t2"),                                               // 8
    add("q3", "13", "29", "3"),                                                  // 9
    work("q3", "t3", "3"),                                                       // 10
    inspect("source", "t3", "@t3"),                                               // 11
    compose("t3", "@t1", "stale-c"),                                              // 12
    compose("t3", "@t3", "c2"),                                                   // 13 occupied composition pin
    compose("t3", "@t3", "c4"),                                                   // 14
    double("c4", "unused4", "d2", "require-selected", "t2", "@t2", "4"),           // 15 occupied decision pin
    double("c4", "q2", "occupied-hit", "require-selected", "t2", "@t2", "4"),       // 16 occupied hit pending pin
    double("c4", "unused4", "d4", "require-selected", "t2", "@t2", "4"),           // 17
    inspect("source", "d4", "@d4"),                                                      // 18
    add("q5", "29", "13", "5"),                                                  // 19
    work("q5", "t4", "4"),                                                       // 20
    inspect("source", "t4", "@t4"),                                               // 21
    compose("t4", "@t4", "c6"),                                                   // 22
    double("c6", "unused6", "d6", "require-selected", "t2", "@t2", "6"),           // 23
    inspect("source", "d6", "@d6"),                                                      // 24
    add("q7", "13", "30", "7"),                                                  // 25
    work("q7", "t5", "5"),                                                       // 26
    inspect("source", "t5", "@t5"),                                               // 27
    compose("t5", "@t5", "c8"),                                                   // 28
    double("c8", "bad-pending", "bad-mode", "require-selected", "t2", "@t2", "8"), // 29 valid differing MAP
    double("c8", "bad-pending", "bad-pin", "try-selected", "t2", "@t3", "8"),      // 30 stale selected pin
    double("c8", "bad-pending", "bad-func", "try-selected", "t1", "@t1", "8"),     // 31 wrong func on mismatch
    double("c8", "q8", "d8", "try-selected", "t2", "@t2", "8"),                   // 32 valid miss
    inspect("source", "d8", "@d8"),                                               // 33
    work("q8", "t6", "6"),                                                       // 34
    inspect("source", "t6", "@t6"),                                               // 35
    source("graft_selection", List("t2", "t3", "poison")),                         // 36
    double("c8", "bad-pending", "bad-chain", "try-selected", "poison", "@poison", "9"), // 37
    { op: "replicate", args: List("repeat", "d4", "snapshot-repeat") },            // 38
    { op: "replicate", args: List("swapped", "d6", "snapshot-swapped") },          // 39
    { op: "retire", args: List("source") },                                       // 40
    inspect("repeat", "snapshot-repeat", "@snapshot-repeat"),                      // 41
    inspect("swapped", "snapshot-swapped", "@snapshot-swapped"),                    // 42
    { op: "graft_input", args: List("swapped", "snapshot-swapped", "source-graft") }, // 43
    inspect("swapped", "source-graft", "@source-graft"),                            // 44
    { op: "graft_parent", args: List("repeat", "snapshot-repeat", "parent-graft") }, // 45
    inspect("repeat", "parent-graft", "@parent-graft"),                            // 46
    { op: "graft_history", args: List("repeat", "snapshot-repeat", "history-graft") }, // 47
    inspect("repeat", "history-graft", "@history-graft")                          // 48
  )
  var histories: List[List[Request]]
  action init = histories' = List(story)
  action step = histories' = histories
}
