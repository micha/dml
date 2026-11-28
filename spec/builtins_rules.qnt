module builtins_rules {
  import builtins_histories.* from "./builtins_histories"

  type Ref = { name: str, target: str }
  type Q = { commit: str, inputs: str, source: str, value: str, binding: str }
  type Call = { dag: str, func: str, binding: str, args: str, value: str, source: str }
  type Evidence = { op: str, args: List[str], code: int, error: str, commit: str, unchanged: bool,
    refs: List[Ref], requests: int, attempts: int, results: int, requested: Q, producing: Q,
    trace: List[Call], outcome: str, selection: str, attempt: str, result: str, returned: str, value: int }
  type Observation = { scenario: int, attempts: List[Evidence] }

  pure val v1 = "dml://source/builtin/map/get/v1"
  pure val v2 = "dml://source/builtin/map/get/v2"
  pure val listV1 = "dml://source/builtin/list/get/v1"
  pure def ref(a: Evidence, name: str): str = a.refs.foldl("", (id, row) => if (row.name == name) row.target else id)
  pure val counts = List(
    (0, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),
    (1, 1, 1), (1, 1, 1), (2, 1, 1), (2, 1, 1), (3, 1, 1), (3, 1, 1),
    (3, 2, 2), (3, 2, 2), (3, 2, 2), (3, 2, 2), (3, 2, 2), (3, 2, 2), (3, 2, 2), (3, 2, 2),
    (2, 1, 1), (2, 1, 1), (2, 2, 2), (2, 2, 2), (2, 3, 3), (2, 3, 3))
  pure val rejections = Map(
    13 -> "request: unsupported map/get version",
    14 -> "request: selection ref does not match the expected commit or absence",
    15 -> "request: expected a builtin-example-attempt-v1 commit",
    16 -> "request: invalid_state: ref already exists",
    17 -> "request: pending request ref does not match the expected commit or absence",
    18 -> "work: invalid_state: ref already exists",
    22 -> "inspect: getter trace does not match the exact consumed source nodes",
    24 -> "inspect: getter trace does not match the exact consumed source nodes")

  pure def getters(a: Evidence, binding: str): bool = a.trace.length() == 2 and {
    val first = a.trace[0]
    val second = a.trace[1]
    first.func == "dml://builtin/map/get" and first.binding == binding and first.source == a.producing.inputs
      and second.func == "dml://builtin/list/get" and second.binding == listV1 and second.source == first.dag
      and a.returned == second.dag and first.dag != second.dag and first.value != second.value
  }
  pure def validCompatibility(a: Evidence): bool = a.trace.length() == 4 and {
    val empty = a.trace[0]
    val insert = a.trace[1]
    val first = a.trace[2]
    val second = a.trace[3]
    a.value == 42 and empty.func == "dml://builtin/map/empty" and empty.source == ""
      and insert.func == "dml://builtin/map/insert" and insert.source == empty.dag and insert.value != empty.value
      and first.func == "dml://builtin/map/get" and second.func == first.func and first.binding == v1 and second.binding == v2
      and first.source == insert.dag and second.source == insert.dag and first.args == second.args
      and first.value == second.value and first.dag != second.dag
  }
  pure def workRead(a: Evidence, request: str, attempt: str, binding: str, result: int): bool = all {
    a.producing.commit == request, a.producing.binding == binding, a.commit == attempt, a.attempt == attempt,
    a.value == result, a.result != "", a.producing.inputs != "", a.producing.value != "", getters(a, binding)
  }
  pure def hitRead(a: Evidence, old: Evidence, decision: str): str = {
    if (a.commit != decision or a.outcome != "reuse" or a.selection != old.attempt) "wrong_hit_decision"
    else if (a.requested.binding != v2 or a.requested.commit == old.producing.commit
        or a.requested.inputs == old.producing.inputs or a.requested.source == old.producing.source
        or a.requested.value != old.producing.value) "lost_requested_provenance"
    else if (a.producing != old.producing or a.result != old.result or a.attempt != old.attempt
        or a.returned != old.returned or a.value != 42 or a.trace != old.trace) "lost_historical_provenance"
    else "ok"
  }
  pure def acceptedStep(rows: List[Evidence], i: int): str = {
    val a = rows[i]
    if (a.code != 0 or a.error != "" or a.commit == "") "unexpected_failure"
    else if (a.unchanged != (a.op == "inspect")) "wrong_write_boundary"
    else if (i < 5 and ref(a, "main") != "") "unexpected_main"
    else if (i >= 5 and i < 11 and ref(a, "main") != rows[6].result) "wrong_main_before_miss_work"
    else if (i >= 11 and i <= 12 and ref(a, "main") != rows[12].result) "wrong_main_after_work"
    else if (i == 0 or i == 2 or i == 3) {
      if (ref(a, a.args[a.args.length() - 1]) == a.commit) "ok" else "missing_pin"
    } else if (i == 1 or i == 9) {
      if (ref(a, a.args[4]) == a.commit and ref(a, a.args[3]) != "") "ok" else "missing_pending_request"
    } else if (i == 4) {
      if (a.commit == rows[3].commit and validCompatibility(a)) "ok" else "wrong_version_compatibility"
    } else if (i == 5 or i == 11) {
      if (ref(a, a.args[3]) == a.commit) "ok" else "missing_attempt_ref"
    } else if (i == 6) {
      if (workRead(a, ref(rows[1], "p1"), rows[5].commit, v1, 42)) "ok" else "old_pin_changed_after_promotion"
    } else if (i == 7) {
      if (ref(a, "hit") == a.commit and ref(a, "unused") == "") "ok" else "hit_created_pending_work"
    } else if (i == 8) hitRead(a, rows[6], rows[7].commit)
    else if (i == 10) {
      if (a.commit == rows[9].commit and a.outcome == "pending" and a.selection == rows[5].commit
          and a.requested.value != rows[8].requested.value and a.requested.commit == ref(rows[9], "p3")
          and a.requested.binding == v2 and a.attempt == "" and a.trace == []) "ok" else "wrong_miss"
    } else if (i == 12) {
      if (workRead(a, rows[10].requested.commit, rows[11].commit, v2, 43) and a.producing == rows[10].requested)
        "ok" else "changed_value_did_not_work"
    } else if (i == 19) {
      if (a.commit == rows[7].commit and a.refs == List({ name: "snapshot", target: a.commit })) "ok" else "wrong_transfer"
    } else if (i == 20) {
      if (a.requested != rows[8].requested or a.refs != rows[19].refs) "wrong_offline_requested_provenance"
      else hitRead(a, rows[6], rows[19].commit)
    } else if (i == 21 or i == 23) {
      if (ref(a, a.args[1]) == a.commit) "ok" else "missing_control_fixture"
    } else "unchecked_step"
  }
  pure def stepVerdict(rows: List[Evidence], i: int): str = {
    val a = rows[i]
    val wanted = story[i]
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if ((a.requests, a.attempts, a.results) != counts[i]) "wrong_native_occurrence_counts"
    else if (rejections.keys().contains(i)) {
      if (a.code == 1 and a.commit == "" and a.unchanged and a.error == rejections.get(i))
        "ok" else "wrong_rejection_or_rollback"
    } else acceptedStep(rows, i)
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario != 0 or row.attempts.length() != story.length()) List("missing_steps")
    else range(0, story.length()).foldl(List(), (out, i) => out.append(stepVerdict(row.attempts, i)))
  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and verdicts.length() == 1 and verdicts[0].length() == story.length() and
    verdicts[0].foldl(true, (ok, verdict) => ok and verdictAccepted(verdict)) and
    evidence[0].attempts[8].outcome == "reuse" and evidence[0].attempts[10].outcome == "pending"

  pure val q: Q = { commit: "old", inputs: "owned", value: "map", source: "literal", binding: v1 }
  pure val old: Evidence = { op: "", args: [], code: 0, error: "", commit: "old-attempt", unchanged: true,
    refs: [], requests: 0, attempts: 0, results: 0, requested: q, producing: q, trace: [], outcome: "",
    selection: "", attempt: "old-attempt", result: "old-result", returned: "old-node", value: 42 }
  pure val hit = { ...old, commit: "decision", outcome: "reuse", selection: old.attempt,
    requested: { ...q, commit: "new", binding: v2, inputs: "other", source: "named" } }
  pure val controlsPass = hitRead(hit, old, "decision") == "ok" and
    hitRead({ ...hit, producing: hit.requested }, old, "decision") == "lost_historical_provenance" and
    hitRead({ ...hit, requested: { ...hit.requested, source: old.requested.source } }, old, "decision") ==
      "lost_requested_provenance"
}
