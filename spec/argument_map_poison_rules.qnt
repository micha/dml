module argument_map_poison_rules {
  import argument_map_poison_histories.* from "./argument_map_poison_histories"

  type Ref = { name: str, target: str }
  type Entry = { key: str, attempt: str }
  type Edit = { role: str, operation: str, key: str, keyKind: int, operationKind: int,
    keyLiteral: bool, operationLiteral: bool, fields: int }
  type Attempt = { op: str, args: List[str], code: int, quiet: bool, diagnosed: bool, error: str,
    commit: str, unchanged: bool, refs: List[Ref], requests: int, executions: int, results: int, accesses: int,
    request: str, input: str, construction: str, implementation: str, sources: List[str], keyHex: List[str],
    producingRequest: str, producingInput: str, producingConstruction: str, producingImplementation: str,
    attempt: str, result: str, value: int, gets: List[str], getSources: List[str], outcome: str, table: str,
    intent: str, entries: List[Entry], reportDigest: str, nativeParents: List[str], edit: Edit, preserved: bool }
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure val poisonError = "request: selected attempt does not match the table intent and argument MAP"
  // Native datum tags in include/dml/record.h.
  pure val mapKind = 10
  pure val stringKind = 6
  pure def ref(a, name) = a.refs.foldl("", (value, r) => if (r.name == name) r.target else value)
  pure def counts(a) = (a.requests, a.executions, a.results, a.accesses)
  pure def moreRequests(a) = (a.requests + 1, a.executions, a.results, a.accesses)
  pure def accepts(a: Attempt): bool = a.code == 0 and a.quiet and a.commit != ""
  pure def otherRefs(a: Attempt, changed: Set[str]): List[Ref] = a.refs.select(r => not(changed.contains(r.name)))
  pure def inspectRead(before: Attempt, a: Attempt): bool =
    accepts(a) and a.commit == ref(before, a.args[1]) and a.unchanged and a.refs == before.refs and counts(a) == counts(before)

  pure def appended(before: Attempt, a: Attempt, name: str): bool =
    accepts(a) and not(a.unchanged) and a.preserved and ref(before, name) == "" and ref(a, name) == a.commit and
      otherRefs(a, Set(name)) == before.refs

  pure def pending(before: Attempt, a: Attempt): str = {
    val name = a.args[1]
    val decision = a.args[2]
    val requestId = ref(a, name)
    if (not(accepts(a)) or a.unchanged or not(a.preserved) or counts(a) != moreRequests(before)) "wrong_pending_publication"
    else if (ref(before, name) != "" or ref(before, decision) != "" or requestId == "" or
      ref(a, decision) != a.commit or a.commit == requestId or otherRefs(a, Set(name, decision)) != before.refs)
      "wrong_pending_refs"
    else if (a.nativeParents != List(requestId)) "wrong_fresh_parents"
    else "ok"
  }

  pure def tableEdit(before: Attempt, a: Attempt, key: str, parents: List[str]): str =
    if (not(appended(before, a, a.args[1])) or counts(a) != counts(before)) "wrong_fixture_publication"
    else if (a.edit != { role: "argument-map-table-edit-v1", operation: a.args[2], key: key, keyKind: mapKind,
      operationKind: stringKind, keyLiteral: true, operationLiteral: true, fields: 1 } or a.nativeParents != parents)
      "wrong_fixture_edit"
    else "ok"

  pure def rejects(before, a) =
    if (a.code != 1 or not(a.diagnosed) or a.error != poisonError or a.commit != "") "wrong_poison_diagnostic"
    else if (not(a.unchanged) or a.refs != before.refs or counts(a) != counts(before) or
      ref(a, a.args[1]) != "" or ref(a, a.args[2]) != "") "wrong_poison_rollback"
    else "ok"

  pure def poisonVerdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val wanted = poisonHistory[i]
    val before = if (i == 0) { ...a, refs: List(), requests: 0, executions: 0, results: 0, accesses: 0 } else rows[i - 1]
    val one = rows[2]
    val other = rows[5]
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if (Set(0, 3, 14, 16).contains(i)) pending(before, a)
    else if (i == 1 or i == 4) {
      if (appended(before, a, a.args[3]) and
        counts(a) == (before.requests, before.executions + 1, before.results + 1, before.accesses + 1)) "ok"
      else "wrong_attempt_publication"
    } else if (i == 2 or i == 5) {
      if (inspectRead(before, a) and a.attempt == a.commit and a.producingRequest == ref(before, rows[i - 1].args[1]) and
        a.producingInput != "" and a.producingImplementation == "double@1" and a.result != "" and
        a.nativeParents == List(a.producingRequest, a.result) and a.value == (if (i == 2) 84 else 86) and
        (i == 2 or a.producingInput != one.producingInput)) "ok"
      else "wrong_fixture_attempt"
    } else if (i == 6 or i == 7) {
      val dest = if (i == 6) a.args[1] else a.args[3]
      val parents = if (i == 6) List() else List(before.commit, one.attempt)
      if (appended(before, a, dest) and counts(a) == counts(before) and a.nativeParents == parents) "ok"
      else "wrong_fixture_basis"
    } else if (i == 8) {
      if (accepts(a) and not(a.unchanged) and counts(a) == moreRequests(before) and ref(a, "p-hit") == "" and
        ref(a, "d-hit") == a.commit and ref(a, "main") == one.result and
        otherRefs(a, Set("d-hit", "main")) == otherRefs(before, Set("main"))) "ok"
      else "wrong_clean_hit_publication"
    } else if (i == 9) {
      if (inspectRead(before, a) and a.outcome == "reuse" and a.table == rows[7].commit and
        a.input == one.producingInput and a.attempt == one.attempt and a.result == one.result and a.value == 84 and
        a.request != "" and a.nativeParents == List(a.request, a.table, one.attempt)) "ok"
      else "wrong_clean_hit"
    } else if (i == 10) tableEdit(before, a, other.producingInput, List(rows[7].commit, one.attempt))
    else if (i == 11) tableEdit(before, a, other.producingInput, List(before.commit))
    else if (i == 12 or i == 13) rejects(before, a)
    else {
      if (inspectRead(before, a) and a.outcome == "pending" and a.table == "" and a.attempt == "" and a.result == "" and
        a.request == ref(before, before.args[1]) and a.input == one.producingInput and a.construction != "" and
        a.implementation == "double@1" and a.keyHex == List("78") and a.sources == List("") and
        a.nativeParents == List(a.request)) "ok"
      else "wrong_fresh_bypass"
    }
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario != 0 or row.attempts.length() != poisonHistory.length()) List("missing_steps")
    else range(0, poisonHistory.length()).foldl(List(), (out, i) => out.append(poisonVerdict(row.attempts, i)))

  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and verdicts.length() == 1 and verdicts[0].length() == poisonHistory.length() and
    verdicts[0].foldl(true, (ok, verdict) => ok and verdictAccepted(verdict)) and
    counts(evidence[0].attempts[poisonHistory.length() - 1]) == (5, 2, 2, 2)

  pure val rejection = { args: List("source", "pending", "decision"), code: 1, diagnosed: true, error: poisonError,
    commit: "", unchanged: true, refs: List({ name: "retained", target: "old" }),
    requests: 3, executions: 2, results: 2, accesses: 2 }
  pure val controlsPass = rejects(rejection, rejection) == "ok" and
    rejects(rejection, { ...rejection, error: "request: table moved" }) == "wrong_poison_diagnostic" and
    rejects(rejection, { ...rejection, unchanged: false }) == "wrong_poison_rollback"
}
