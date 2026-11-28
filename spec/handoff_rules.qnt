module handoff_rules {
  import handoff_histories.* from "./handoff_histories"

  type Attempt = { op: str, args: List[str], code: int, stdout: List[List[str]],
    stderr: List[List[str]], storage: str, existed: bool }
  type Observation = { scenario: int, attempts: List[Attempt] }
  type Bindings = str -> str
  type Match = { ids: Bindings, valid: bool }

  pure def savedAs(ids: Bindings, alias: str, value: str): bool =
    if (ids.keys().contains(alias)) ids.get(alias) == value else false

  pure def matchCell(before: Match, expected: Cell, value: str): Match = {
    if (not(before.valid)) before
    else if (expected.kind == "text") { ...before, valid: expected.text == value }
    else if (expected.kind == "saved") { ...before, valid: savedAs(before.ids, expected.text, value) }
    else if (expected.kind == "capture" and value != "" and value != "missing" and
      not(before.ids.keys().contains(expected.text)))
      { ...before, ids: before.ids.put(expected.text, value) }
    else { ...before, valid: false }
  }

  pure def matchRow(before: Match, expected: List[Cell], actual: List[str]): Match = {
    if (expected.length() != actual.length()) { ...before, valid: false }
    else range(0, expected.length()).foldl(before, (state, index) => matchCell(state, expected[index], actual[index]))
  }

  pure def matchReport(ids: Bindings, expected: Step, actual: List[List[str]]): Match = {
    val start = { ids: ids, valid: true }
    if (expected.layout == "ignore") start
    else if (expected.report.length() != actual.length()) { ...start, valid: false }
    else if (expected.layout == "ordered") range(0, actual.length()).foldl(start, (state, index) =>
      matchRow(state, expected.report[index], actual[index]))
    else if (expected.layout == "fields") {
      // Expected report fields have distinct keys. Match all of them without
      // depending on print order; length prevents duplicate/extra lines.
      ...start, valid: expected.report.indices().forall(i => actual.indices().exists(j =>
        matchRow(start, expected.report[i], actual[j]).valid))
    }
    else { ...start, valid: false }
  }

  pure def diagnosticMatches(expected: str, detail: str, actual: List[List[str]]): bool = {
    if (expected == "") actual.length() == 0
    else if (actual.length() == 0 or actual[0].length() == 0) false
    // Primary diagnostic (or a detail from the same line), not any later error.
    else if (detail != "") actual[0][0] == expected and actual[0].length() == 3 and actual[0][2] == detail
    else actual[0][0] == expected or (actual[0].length() == 3 and actual[0][2] == expected)
  }

  pure def compareAttempt(ids: Bindings, expected: Step, attempt: Attempt): (Bindings, str) = {
    val report = matchReport(ids, expected, attempt.stdout)
    val verdict = if (expected.call != { op: attempt.op, args: attempt.args }) "wrong_command"
      else if (expected.code != attempt.code) "wrong_exit"
      else if (not(diagnosticMatches(expected.diagnostic, expected.detail, attempt.stderr))) "wrong_diagnostic"
      else if (expected.readOnly and attempt.storage != "unchanged") "not_read_only"
      else if (expected.absentRepo and attempt.existed) "repository_already_exists"
      else if (not(report.valid)) "wrong_report"
      else if (not(expected.distinct.indices().forall(i => {
        val (first, second) = expected.distinct[i]
        if (report.ids.keys().contains(first) and report.ids.keys().contains(second))
          report.ids.get(first) != report.ids.get(second)
        else false
      }))) "identities_collapsed"
      else expected.label
    (report.ids, verdict)
  }

  pure def historyVerdicts(observed: Observation): List[str] = {
    if (not(scenarios.indices().contains(observed.scenario)) or observed.attempts.length() == 0) List("missing_history")
    else {
      val steps = scenarios[observed.scenario].steps
      if (observed.attempts.length() != steps.length()) List("wrong_step_count")
      else range(0, steps.length()).foldl({ ids: Map(), verdicts: List() }, (state, i) => {
        val (ids, verdict) = compareAttempt(state.ids, steps[i], observed.attempts[i])
        { ids: ids, verdicts: state.verdicts.append(verdict) }
      }).verdicts
    }
  }

  // An accepted inspection earns its semantic label only after the CLI/LMDB
  // observations agree. Required cases are explicit so a missing scenario fails.
  pure val requiredInspections = Set(
    "source-inactive", "source-after-publish", "worker-inactive", "request-pinned", "request-staged",
    "result-pinned", "result-retained", "publication-ready", "wrong-parent-before-stale-tip",
    "wrong-implementation", "wrong-implementation-before-stale-tip", "stale-tip", "missing-main",
    "missing-request-pin", "release-blocked",
    "unsupported-operation", "missing-repository", "invalid-role", "no-recompute"
  )
  pure def verdictAccepted(verdict: str): bool = verdict == "ok" or requiredInspections.contains(verdict)
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool = all {
    evidence.length() == scenarios.length(),
    scenarios.indices().map(i => scenarios[i].name).size() == scenarios.length(),
    evidence.indices().forall(i => evidence[i].scenario == i),
    requiredInspections.subseteq(verdicts.indices().fold(Set(), (labels, i) => labels.union(verdicts[i].indices().map(j =>
      verdicts[i][j]))))
  }

  // Negative controls keep the oracle honest independently of runner behavior.
  pure val sample = inspectWorker(worker, notFound, notFound, List(), "worker-inactive", "")
  pure val baseline: Attempt = { op: "handoff", args: List("inspect", "worker", "@worker"),
    code: 0, stdout: List(List("checkpoint", "inactive"), List("incoming", "not found"),
      List("result-pin", "not found")), stderr: List(), storage: "unchanged", existed: true }
  pure def verdictFor(expected: Step, attempt: Attempt): str = compareAttempt(Map(), expected, attempt)._2
  pure val controlsPass = all {
    verdictFor(sample, baseline) == "worker-inactive",
    verdictFor(sample, { ...baseline, code: 1 }) == "wrong_exit",
    verdictFor(sample, { ...baseline, storage: "changed" }) == "not_read_only",
    verdictFor(sample, { ...baseline, storage: "unobserved" }) == "not_read_only",
    verdictFor({ ...sample, absentRepo: true }, baseline) == "repository_already_exists",
    verdictFor(sample, { ...baseline, args: List("inspect", "worker", "@source") }) == "wrong_command",
    verdictFor(sample, { ...baseline, stdout: baseline.stdout.append(baseline.stdout[0]) }) == "wrong_report",
    verdictFor(sample, { ...baseline, stdout: baseline.stdout.tail().append(baseline.stdout[1]) }) == "wrong_report",
    verdictFor(sample, { ...baseline, stdout: baseline.stdout.tail().append(List("checkpoint: inactive")) }) == "wrong_report",
    verdictFor(sample, { ...baseline, stderr: List(List("unexpected")) }) == "wrong_diagnostic",
    verdictFor(reject(sample, wrongParent), { ...baseline, code: 1, stderr: List(List(staleTip), List(wrongParent)) })
      == "wrong_diagnostic"
  }
}
