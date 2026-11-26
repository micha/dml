module composition_histories {
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  // A @ref token is resolved from live native receipts by the runner. The
  // ref/pin pairs here are explicit so stale-pin controls can keep their names.
  pure val pendingPins = Map(
    "q1" -> "@q1", "q2" -> "@q2", "q3" -> "@q3", "q5" -> "@q5", "q7" -> "@q7", "q8" -> "@q8",
    "q-overflow" -> "@q-overflow", "q-max" -> "@q-max", "q-double-overflow" -> "@q-double-overflow")
  pure val compositionPins = Map("c2" -> "@c2", "c4" -> "@c4", "c6" -> "@c6", "c8" -> "@c8",
    "c-overflow" -> "@c-overflow")
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
    val selected = if (selection == "") List() else
      List("--selected-ref", selection).concat(if (pin == "") List() else List("--selected", pin))
    val command = List(basis, compositionPins.get(basis), pending, d, "--mode", mode)
    source("request_double", command.concat(selected).concat(invocation(n)))
  }

  // Author eight requests and publish six successful attempts. Controls that author
  // malformed ancestry copy native rows; they do not execute either callable.
  pure val story: List[Request] = List(
    source("define", List("config")),                                             // 0
    add("q1", "13", "29", "1"),                                                  // 1
    work("q1", "config", "1"),                                                   // 2 collision before main exists
    work("q1", "t1", "1"),                                                       // 3 retry the same request and attempt ID
    inspect("source", "t1", "@t1"),                                               // 4
    compose("t1", "@t1", "c2"),                                                   // 5
    double("c2", "q2", "d2", "try-selected", "t2", "", "2"),                     // 6
    inspect("source", "d2", "@d2"),                                               // 7
    work("q2", "t2", "2"),                                                       // 8
    inspect("source", "t2", "@t2"),                                               // 9
    add("q3", "13", "29", "3"),                                                  // 10
    work("q3", "t3", "3"),                                                       // 11
    inspect("source", "t3", "@t3"),                                               // 12
    compose("t3", "@t1", "stale-c"),                                              // 13
    compose("t3", "@t3", "c2"),                                                   // 14 occupied composition pin
    compose("t3", "@t3", "c4"),                                                   // 15
    double("c4", "unused4", "d2", "require-selected", "t2", "@t2", "4"),           // 16 occupied decision pin
    double("c4", "q2", "occupied-hit", "require-selected", "t2", "@t2", "4"),       // 17 occupied hit pending pin
    double("c4", "unused4", "d4", "require-selected", "t2", "@t2", "4"),           // 18
    inspect("source", "d4", "@d4"),                                               // 19
    add("q5", "29", "13", "5"),                                                  // 20
    work("q5", "t4", "4"),                                                       // 21
    inspect("source", "t4", "@t4"),                                               // 22
    compose("t4", "@t4", "c6"),                                                   // 23
    double("c6", "unused6", "d6", "require-selected", "t2", "@t2", "6"),           // 24
    inspect("source", "d6", "@d6"),                                               // 25
    add("q7", "13", "30", "7"),                                                  // 26
    work("q7", "config", "5"),                                                   // 27 collision with a prior main
    work("q7", "t5", "5"),                                                       // 28 retry the same request and attempt ID
    inspect("source", "t5", "@t5"),                                               // 29
    compose("t5", "@t5", "c8"),                                                   // 30
    double("c8", "bad-pending", "bad-mode", "require-selected", "t2", "@t2", "8"), // 31 valid differing MAP
    double("c8", "bad-pending", "bad-pin", "try-selected", "t2", "@t3", "8"),      // 32 stale selected pin
    double("c8", "bad-pending", "bad-func", "try-selected", "t1", "@t1", "8"),     // 33 wrong func on mismatch
    double("c8", "q8", "d8", "try-selected", "t2", "@t2", "8"),                   // 34 valid miss
    inspect("source", "d8", "@d8"),                                               // 35
    work("q8", "t6", "6"),                                                       // 36
    inspect("source", "t6", "@t6"),                                               // 37
    source("graft_selection", List("t2", "t3", "poison")),                         // 38
    double("c8", "bad-pending", "bad-chain", "try-selected", "poison", "@poison", "9"), // 39
    { op: "replicate", args: List("repeat", "d4", "snapshot-repeat") },            // 40
    { op: "replicate", args: List("swapped", "d6", "snapshot-swapped") },          // 41
    double("c2", "same-id-unused", "same-id-decision", "require-selected", "t2", "@t2", "2"), // 42 recreates q2
    { op: "retire", args: List("source") },                                       // 43
    inspect("repeat", "snapshot-repeat", "@snapshot-repeat"),                      // 44
    inspect("swapped", "snapshot-swapped", "@snapshot-swapped"),                    // 45
    { op: "graft_input", args: List("swapped", "snapshot-swapped", "source-graft") }, // 46
    inspect("swapped", "source-graft", "@source-graft"),                            // 47
    { op: "graft_parent", args: List("repeat", "snapshot-repeat", "parent-graft") }, // 48
    inspect("repeat", "parent-graft", "@parent-graft"),                            // 49
    { op: "graft_history", args: List("repeat", "snapshot-repeat", "history-graft") }, // 50
    inspect("repeat", "history-graft", "@history-graft"),                          // 51
    { op: "graft_reuse_request", args: List("repeat", "snapshot-repeat", "same-id-graft") }, // 52
    inspect("repeat", "same-id-graft", "@same-id-graft")                          // 53
  )
  pure val maxI64Arg = "9223372036854775807"
  // Use a clean repository so the rejected add cannot leave or replace main.
  pure val overflowStory: List[Request] = List(
    source("define", List("config")),                                           // 0
    add("q-overflow", maxI64Arg, "1", "1"),                                     // 1
    work("q-overflow", "t-overflow", "1"),                                      // 2 add overflows before main exists
    add("q-max", maxI64Arg, "0", "2"),                                          // 3
    work("q-max", "t-max", "2"),                                                // 4
    inspect("source", "t-max", "@t-max"),                                      // 5
    compose("t-max", "@t-max", "c-overflow"),                                   // 6
    double("c-overflow", "q-double-overflow", "d-overflow", "fresh", "", "", "3"), // 7
    work("q-double-overflow", "t-double-overflow", "3"),                         // 8 double overflows with main at the add result
    inspect("source", "d-overflow", "@d-overflow")                              // 9 double still pending
  )
  var histories: List[List[Request]]
  action init = histories' = List(story, overflowStory)
  action step = histories' = histories
}
