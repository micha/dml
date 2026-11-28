module argument_map_budget_rules {
  import argument_map_budget_histories.* from "./argument_map_budget_histories"

  // The unchanged argument-map CLI adapter supplies the full observation shape.
  type Ref = { name: str, target: str }
  type Entry = { key: str, attempt: str }
  type Attempt = { op: str, args: List[str], code: int, quiet: bool, diagnosed: bool, error: str,
    commit: str, unchanged: bool, refs: List[Ref], requests: int, executions: int, results: int, accesses: int,
    request: str, input: str, construction: str, implementation: str, sources: List[str], keyHex: List[str],
    producingRequest: str, producingInput: str, producingConstruction: str, producingImplementation: str,
    attempt: str, result: str, value: int, gets: List[str], getSources: List[str], outcome: str, table: str,
    intent: str, entries: List[Entry], reportDigest: str }
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure val addKeys = List("61", "62", "63", "64", "65", "66", "67", "68", "69", "6a", "6b", "6c", "6d", "6e", "6f")
  pure val budgetError = "request: too many reached argument-map attempts for a new invocation"
  pure def ref(a, name) = a.refs.foldl("", (value, r) => if (r.name == name) r.target else value)
  pure def counts(a) = (a.requests, a.executions, a.results, a.accesses)
  pure def accepts(a: Attempt): bool = a.code == 0 and a.quiet and a.commit != ""
  pure def otherRefs(a: Attempt, changed: Set[str]): List[Ref] = a.refs.select(r => not(changed.contains(r.name)))
  pure def inspectRead(before: Attempt, a: Attempt): bool =
    accepts(a) and a.commit == ref(before, a.args[1]) and a.unchanged and a.refs == before.refs and counts(a) == counts(before)

  pure def pendingRequest(before: Attempt, a: Attempt): str = {
    val pending = a.args[1]
    val decision = a.args[2]
    if (not(accepts(a)) or a.unchanged) "expected_pending_request"
    else if (ref(before, pending) != "" or ref(before, decision) != "" or ref(a, pending) == "" or
      ref(a, pending) == a.commit or ref(a, decision) != a.commit or otherRefs(a, Set(pending, decision)) != before.refs)
      "wrong_pending_refs"
    else if (counts(a) != (before.requests + 1, before.executions, before.results, before.accesses))
      "wrong_native_occurrence_counts"
    else "ok"
  }

  pure def publishAttempt(before: Attempt, a: Attempt, newResults: int, newGets: int): str = {
    val dest = a.args[3]
    if (not(accepts(a)) or a.unchanged) "expected_new_attempt"
    else if (ref(before, dest) != "" or ref(a, dest) != a.commit or otherRefs(a, Set(dest)) != before.refs)
      "wrong_attempt_refs"
    else if (before.refs.select(r => r.target == a.commit).length() != 0) "wrong_budget_attempt_identity"
    else if (counts(a) != (before.requests, before.executions + 1, before.results + newResults, before.accesses + newGets))
      "wrong_native_occurrence_counts"
    else "ok"
  }

  pure def budgetAddVerdict(rows: List[Attempt], i: int, start: int, origins: List[str]): str = {
    val a = rows[i]
    val before = rows[i - 1]
    if (i == start) pendingRequest(before, a)
    else if (i == start + 1) {
      if (inspectRead(before, a) and a.outcome == "pending" and a.table == "" and a.attempt == "" and
        a.request == ref(before, before.args[1]) and a.input != "" and a.construction != "" and
        a.implementation == "add@1" and a.keyHex == addKeys.slice(0, origins.length()) and a.sources == origins)
        "ok" else "wrong_budget_sources"
    } else if (i == start + 2) publishAttempt(before, a, 1, 2)
    else {
      val pending = rows[start + 1]
      if (inspectRead(before, a) and a.attempt == before.commit and a.producingRequest == pending.request and
        a.producingInput == pending.input and a.producingConstruction == pending.construction and
        a.producingImplementation == "add@1" and a.result != "" and a.value == 0 and
        a.gets == List("a", "b") and a.getSources == origins.slice(0, 2)) "ok"
      else "wrong_budget_attempt"
    }
  }

  pure def budgetRejection(before, a) =
    if (a.code != 1 or not(a.diagnosed) or a.commit != "" or a.error != budgetError) "wrong_budget_diagnostic"
    else if (not(a.unchanged) or a.refs != before.refs or counts(a) != counts(before) or
      ref(a, a.args[1]) != "" or ref(a, a.args[2]) != "") "wrong_budget_rollback"
    else "ok"

  pure def budgetVerdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val wanted = reachedBudget[i]
    val before = if (i == 0) { ...a, refs: List(), requests: 0, executions: 0, results: 0, accesses: 0 }
      else rows[i - 1]
    val groupsStart = budgetBase.length()
    val siblingStart = groupsStart + budgetGroups.length()
    val fullStart = siblingStart + budgetSibling.length()
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if (i == 0) pendingRequest(before, a)
    else if (i == 1) publishAttempt(before, a, 1, 1)
    else if (i < groupsStart) publishAttempt(before, a, 0, 0)
    else if (i < siblingStart) {
      val group = (i - groupsStart) / 4
      val origins = budgetLeaves[group].foldl(List(), (out, row) => out.append(ref(rows[groupsStart - 1], row.attempt)))
      if (origins.select(origin => origin == "").length() != 0) "missing_budget_leaf"
      else budgetAddVerdict(rows, i, groupsStart + 4 * group, origins)
    } else if (i == siblingStart) publishAttempt(before, a, 0, 0)
    else if (i == siblingStart + 1) {
      val first = rows[groupsStart + 3]
      if (inspectRead(before, a) and a.attempt == before.commit and a.attempt != first.attempt and
        a.producingRequest == first.producingRequest and a.producingImplementation == first.producingImplementation and
        a.producingInput == first.producingInput and a.producingConstruction == first.producingConstruction and
        a.result == first.result and a.value == first.value and a.gets == first.gets and a.getSources == first.getSources) "ok"
      else "wrong_budget_sibling"
    } else if (i < fullStart + budgetFull.length()) {
      val first = rows[groupsStart + 3].attempt
      val origins = range(1, 4).foldl(List(first, first), (out, j) => out.append(rows[groupsStart + 4 * j + 3].attempt))
      budgetAddVerdict(rows, i, fullStart, origins)
    } else budgetRejection(before, a)
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.scenario != 0 or row.attempts.length() != reachedBudget.length()) List("missing_steps")
    else range(0, reachedBudget.length()).foldl(List(), (out, i) => out.append(budgetVerdict(row.attempts, i)))

  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and verdicts.length() == 1 and verdicts[0].length() == reachedBudget.length() and
    verdicts[0].foldl(true, (ok, verdict) => ok and verdictAccepted(verdict)) and
    evidence[0].attempts.slice(reachedBudget.length() - budgetRejections.length(), reachedBudget.length())
      .foldl(List(), (codes, a) => codes.append(a.code)) == List(1, 1) and
    counts(evidence[0].attempts[reachedBudget.length() - 1]) == (6, 65, 6, 11)

  pure val rejection = { args: List("source", "pending", "decision"), code: 1, diagnosed: true, error: budgetError,
    commit: "", unchanged: true, refs: List({ name: "retained", target: "old" }),
    requests: 6, executions: 65, results: 6, accesses: 11 }
  pure val controlsPass = budgetRejection(rejection, rejection) == "ok" and
    budgetRejection(rejection, { ...rejection, error: "request: over limit" }) == "wrong_budget_diagnostic" and
    budgetRejection(rejection, { ...rejection, unchanged: false }) == "wrong_budget_rollback"
}
