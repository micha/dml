module argument_maps_rules {
  import argument_maps_histories.* from "./argument_maps_histories"

  type Ref = { name: str, target: str }
  type Attempt = { op: str, args: List[str], code: int, quiet: bool, diagnosed: bool, error: str,
    commit: str, unchanged: bool, refs: List[Ref], requests: int, executions: int, results: int, accesses: int,
    request: str, input: str, construction: str, implementation: str, sources: List[str],
    producingRequest: str, producingInput: str, producingConstruction: str, producingImplementation: str,
    attempt: str, result: str, value: int, gets: List[str], getSources: List[str], outcome: str, table: str }
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure def ref(a: Attempt, name: str): str = {
    a.refs.foldl("", (value, r) => if (r.name == name) r.target else value)
  }

  pure def nativeCounts(a: Attempt): (int, int, int, int) = (a.requests, a.executions, a.results, a.accesses)
  pure val counts = List(
    (1, 0, 0, 0), (1, 1, 1, 1), (1, 1, 1, 1), (1, 1, 1, 1), (1, 1, 1, 1),
    (1, 1, 1, 1), (2, 1, 1, 1), (2, 2, 2, 3), (2, 2, 2, 3),
    (2, 2, 2, 3), (3, 2, 2, 3), (3, 2, 2, 3),
    (3, 2, 2, 3), (3, 2, 2, 3), (3, 2, 2, 3),
    (4, 2, 2, 3), (4, 3, 3, 5), (4, 3, 3, 5), (5, 3, 3, 5), (5, 3, 3, 5),
    (5, 4, 4, 6), (5, 4, 4, 6), (3, 2, 2, 3), (3, 2, 2, 3))

  pure def workRead(a: Attempt, attempt: str, request: str, implementation: str,
                    value: int, names: List[str], sources: List[str]): bool = all {
    a.commit == attempt, a.attempt == attempt, a.producingRequest == request, a.producingImplementation == implementation,
    a.producingInput != "", a.producingConstruction != "", a.result != "",
    a.value == value, a.gets == names, a.getSources == sources
  }
  pure def hitRead(a: Attempt, original: Attempt, upstream: Attempt, decision: str, table: str): str = {
    if (a.commit != decision or a.table != table or a.outcome != "reuse") "wrong_decision"
    else if (a.request == "" or a.request == original.producingRequest or a.implementation != "double@2"
      or a.construction == "" or a.construction == original.producingConstruction
      or a.sources != List(upstream.attempt) or a.input != original.producingInput) "wrong_requested_construction"
    else if (a.producingRequest != original.producingRequest or a.producingImplementation != "double@1"
      or a.producingConstruction != original.producingConstruction or a.producingInput != original.producingInput)
      "wrong_producing_request"
    else if (a.attempt != original.attempt or a.result != original.result or a.value != 84
      or a.gets != List("x") or a.getSources != List("")) "wrong_historical_result_or_trace"
    else "ok"
  }

  pure def decisionCollision(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val retryDecision = story[i + 1].args[2]
    val error = "request: ('invalid_state', -30799, 'ref already exists')"
    if (a.code != 1 or not(a.diagnosed) or a.error != error or a.commit != "")
      "wrong_collision_diagnostic"
    else if (not(a.unchanged) or nativeCounts(a) != counts[i] or ref(a, "d1") != rows[0].commit or ref(a, retryDecision) != ""
      or ref(a, a.args[1]) != "" or ref(a, "main") != "") "wrong_collision_rollback"
    else "ok"
  }

  pure def acceptedStep(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    if (a.code != 0 or not(a.quiet) or a.commit == "") "unexpected_command_failure"
    else if (a.op == "inspect" and not(a.unchanged)) "inspection_wrote"
    else if (a.op != "inspect" and a.unchanged) "expected_write"
    else if (i < 10 and ref(a, "main") != "") "premature_main"
    else if (i >= 10 and i < 22 and ref(a, "main") != rows[2].result) "wrong_main"
    else if (i == 6 and a.refs.select(r => r.name != "p2" and r.name != "d2") != rows[i - 1].refs) "wrong_retry_refs"
    else if (Set(0, 6, 15, 18).contains(i)) {
      if (ref(a, a.args[2]) == a.commit and ref(a, a.args[1]) != "") "ok" else "wrong_pending_refs"
    } else if (i == 10) {
      if (ref(a, "d3") == a.commit and ref(a, "p3") == ""
        and a.refs.select(r => r.name != "main" and r.name != "d3") == rows[i - 1].refs) "ok" else "wrong_hit_refs"
    } else if (a.op == "work") {
      if (ref(a, a.args[3]) == a.commit) "ok" else "wrong_attempt_ref"
    } else if (a.op == "define_table") {
      if (ref(a, "empty") == a.commit) "ok" else "wrong_empty_table"
    } else if (a.op == "update_table") {
      if (ref(a, "selected") == a.commit and ref(a, "empty") == rows[3].commit) "ok" else "wrong_table_update"
    } else if (i == 2) {
      if (workRead(a, rows[1].commit, ref(rows[0], "p1"), "double@1", 84, List("x"), List(""))) "ok" else "wrong_literal_attempt"
    } else if (i == 8) {
      if (workRead(a, rows[7].commit, ref(rows[6], "p2"), "add@1", 42, List("a", "b"), List("", ""))) "ok" else "wrong_42_attempt"
    } else if (i == 11) hitRead(a, rows[2], rows[8], rows[10].commit, rows[4].commit)
    else if (i == 17) {
      if (workRead(a, rows[16].commit, ref(rows[15], "p4"), "add@1", 43, List("a", "b"), List("", ""))) "ok" else "wrong_43_attempt"
    } else if (i == 19) {
      if (a.commit == rows[18].commit and a.request == ref(rows[18], "p5") and a.outcome == "pending"
        and a.table == rows[4].commit and a.sources == List(rows[16].commit) and a.input != rows[11].input
        and a.attempt == "" and a.producingRequest == "" and a.gets == List()) "ok" else "wrong_value_miss"
    } else if (i == 21) {
      if (workRead(a, rows[20].commit, rows[19].request, "double@2", 86, List("x"), List(rows[16].commit))
        and a.producingInput == rows[19].input and a.producingConstruction == rows[19].construction) "ok" else "wrong_fresh_attempt"
    } else if (i == 22) {
      if (a.commit == rows[10].commit and a.refs == List({ name: "snapshot", target: a.commit })) "ok" else "wrong_replica"
    } else if (i == 23) {
      if (a.request != rows[11].request or a.input != rows[11].input or a.construction != rows[11].construction
        or a.refs != rows[22].refs) "wrong_offline_provenance"
      else hitRead(a, rows[2], rows[8], rows[22].commit, rows[4].commit)
    } else "unchecked_step"
  }

  pure def stepVerdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val wanted = story[i]
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if (i == 5 or i == 9) decisionCollision(rows, i)
    else if (nativeCounts(a) != counts[i]) "wrong_native_occurrence_counts"
    else if (Set(12, 13, 14).contains(i)) {
      val error = if (i == 14) "request: table ref does not match the expected commit or absence"
        else "request: no selected attempt for the argument MAP"
      if (a.code == 1 and a.diagnosed and a.commit == "" and a.error == error and a.unchanged) "ok"
      else "wrong_rejection_or_rollback"
    } else acceptedStep(rows, i)
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario != 0 or row.attempts.length() != story.length()) List("missing_steps")
    else range(0, story.length()).foldl(List(), (out, i) => out.append(stepVerdict(row.attempts, i)))
  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and verdicts.length() == 1 and verdicts[0].length() == story.length() and
    verdicts[0].foldl(true, (ok, verdict) => ok and verdictAccepted(verdict)) and
    evidence[0].attempts[11].outcome == "reuse" and
    evidence[0].attempts[19].outcome == "pending"

  pure val fixture: Attempt = { op: "", args: List(), code: 0, quiet: true, diagnosed: false, error: "", commit: "d",
    unchanged: true, refs: List(), requests: 0, executions: 0, results: 0, accesses: 0, request: "q-new", input: "map",
    construction: "from-result", implementation: "double@2", sources: List("upstream"), producingRequest: "q-old",
    producingInput: "map", producingConstruction: "from-literal", producingImplementation: "double@1",
    attempt: "t-old", result: "r-old", value: 84, gets: List("x"), getSources: List(""), outcome: "reuse", table: "table" }
  pure val controlsPass = hitRead(fixture, fixture, { ...fixture, attempt: "upstream" }, "d", "table") == "ok" and
    hitRead({ ...fixture, producingRequest: fixture.request }, fixture, { ...fixture, attempt: "upstream" },
      "d", "table") == "wrong_producing_request"
}
