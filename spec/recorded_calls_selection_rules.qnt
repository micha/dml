module recorded_calls_selection_checks {
  import recorded_calls_rules.* from "./recorded_calls_rules"
  import recorded_calls_selection_histories as h from "./recorded_calls_selection_histories"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"

  pure val resultRole = "7265717565737465642d7363616c652d7631" // requested-scale-v1
  pure val attemptRole = "7363616c652d617474656d70742d7631" // scale-attempt-v1
  pure val choiceRole = "7363616c652d726573756c742d73656c656374696f6e2d7631" // scale-result-selection-v1
  pure val attemptChoiceRole = "7363616c652d617474656d70742d73656c656374696f6e2d7631" // scale-attempt-selection-v1
  pure val proofRole = "7265636f726465642d73656c65637465642d7363616c652d72657573652d7631" // recorded-selected-scale-reuse-v1

  pure def graph(rows: List[Attempt], role: str, parentIds: List[str], count: int): bool =
    decoded(rows, "head-view").nativeCount == parentIds.length() and
    treeEntry(rows, "tree-view", "graph-dag", role) and decoded(rows, "graph-root").nativeCount == count and
    parentIds.indices().forall(i => parentIds[i] != "" and parentIds[i] == outputId(rows, "object_view_parent",
      if (i == 0) "parent0" else "parent1"))
  pure def rootIs(rows: List[Attempt], alias: str): bool =
    decoded(rows, "graph-root").nativeValue == outputId(rows, "txn_lookup_node", alias)
  pure def stringValue(rows: List[Attempt], alias: str, text: str): bool = {
    val datum = nativeOutput(rows, "datum_decode", alias)
    nativeNodeMatches(rows, alias) and datum.nativeCount == 6 and datum.nativeItems == List(text)
  }
  pure def singleBinding(rows: List[Attempt], role: str, parentIds: List[str], text: str): bool =
    graph(rows, role, parentIds, 1) and rootIs(rows, "field-node") and stringValue(rows, "field-value", text)
  pure def candidate(rows: List[Attempt], request: str, producerDag: str, version: str, factor: str): bool =
    graph(rows, resultRole, List(request), 3) and
    stringValue(rows, "implementation-value", version) and nativeLiteralMatches(rows, "factor-value", 3, factor) and
    nativeNodeMatches(rows, "input-dag") and producerDag != "" and decoded(rows, "input-dag").nativeValue == producerDag and
    nativeLiteralMatches(rows, "output-value", 3, "2400000000000000")
  pure def forgedChoice(rows: List[Attempt], s: h::Shape, p: List[str]): bool =
    graph(rows, choiceRole, p, 1) and
    (if (s.variant == "type") rootIs(rows, "field-node") and nativeLiteralMatches(rows, "field-value", 3, "0700000000000000")
     else stringValue(rows, "field-value", s.value) and
       (if (s.variant == "root") not(rootIs(rows, "field-node")) else rootIs(rows, "field-node")))
  pure def proofGraph(rows: List[Attempt], p: List[str], planName: str, selectionName: str): bool =
    graph(rows, proofRole, p, 2) and rootIs(rows, "plan-node") and
    stringValue(rows, "plan-name", planName) and stringValue(rows, "selection-name", selectionName)

  pure def exactDiagnostic(op: str, cause: str, diagnostic: str): bool = {
    val inspect = op == "inspect"
    val selectResult = op == "select_scale_result"
    val selectAttempt = op == "select_scale_attempt"
    val expected =
      if (cause == h::occupied) {
        if (op == "work_scale_attempt") "work-scale-attempt: ('invalid_state', -30799, 'ref already exists')"
        else "publish-selected-scale: ('invalid_state', -30799, 'ref already exists')"
      } else if (cause == h::wrongVersion) {
        if (inspect) "inspect: expected recorded implementation example.scale@2"
        else if (selectResult) "select-scale-result: expected recorded implementation example.scale@2"
        else if (selectAttempt) "select-scale-attempt: expected recorded implementation example.scale@2"
        else "publish-selected-scale: expected recorded implementation example.scale@2"
      } else if (cause == h::wrongResult) {
        if (inspect) "inspect: result does not retain the expected request commit"
        else if (selectAttempt) "select-scale-attempt: result does not retain the expected request commit"
        else "publish-selected-scale: result does not retain the expected request commit"
      } else if (cause == h::wrongAttempt) {
        if (inspect) "inspect: attempt does not retain the expected request commit"
        else if (selectAttempt) "select-scale-attempt: attempt does not retain the expected request commit"
        else "publish-selected-scale: attempt does not retain the expected request commit"
      } else if (cause == h::badAttemptParents) {
        if (inspect) "inspect: expected a scale-attempt-v1 commit with ordered request and result parents"
        else if (selectAttempt) "select-scale-attempt: expected a scale-attempt-v1 commit with ordered request and result parents"
        else "publish-selected-scale: expected a scale-attempt-v1 commit with ordered request and result parents"
      } else if (cause == h::badUuid) {
        if (inspect) "inspect: attempt ID must be a canonical lowercase UUIDv4 in bytes"
        else if (selectAttempt) "select-scale-attempt: attempt ID must be a canonical lowercase UUIDv4 in bytes"
        else if (op == "work_scale_attempt") "work-scale-attempt: attempt ID must be a canonical lowercase UUIDv4 in bytes"
        else "publish-selected-scale: attempt ID must be a canonical lowercase UUIDv4 in bytes"
      } else if (cause == "reversed") {
        if (inspect) "inspect: expected a scale-request-v1 commit with one producer parent"
        else "publish-selected-scale: selection does not retain the expected request commit"
      } else if (cause == "missing-parent") {
        if (inspect) "inspect: expected a scale-result-selection-v1 commit with ordered request and result parents"
        else "publish-selected-scale: expected a scale-result-selection-v1 commit with ordered request and result parents"
      } else if (cause == "bad-root") {
        if (inspect) "inspect: result selection has the wrong DAG layout"
        else "publish-selected-scale: result selection has the wrong DAG layout"
      } else if (cause == "bad-name") {
        if (inspect) "inspect: result selection has an invalid result ref name"
        else "publish-selected-scale: result selection has an invalid result ref name"
      } else if (cause == "bad-type") {
        if (inspect) "inspect: recorded literal has the wrong datum kind"
        else "publish-selected-scale: recorded literal has the wrong datum kind"
      } else if (cause == "bad-history") {
        if (inspect) "inspect: attempt selection has an invalid attempt ref name"
        else "publish-selected-scale: attempt selection has an invalid attempt ref name"
      } else if (cause == "alias") "work-scale-attempt: incoming, attempt, and main refs must be distinct"
      else if (cause == "name") "work-scale-attempt: attempt ref must be a valid ASCII ref name in bytes"
      else if (cause == "stale") "work-scale-attempt: incoming ref does not point to the expected request commit"
      else if (cause == "overflow") "work-scale-attempt: example.scale@1 result is not a signed 64-bit integer"
      else ""
    expected != "" and diagnostic == expected
  }

  pure val proofFields = List(List("commit", "expected_main", "plan_commit", "plan_ref", "publication_mode",
    "request_commit", "result_commit", "selection_commit", "selection_ref"))
  pure val attemptProofFields = List(List("attempt_commit", "attempt_id", "commit", "expected_main", "plan_commit", "plan_ref",
    "publication_mode", "request_commit", "result_commit", "selection_commit", "selection_ref"))
  pure val choiceFields = List(List("commit", "request_commit", "request_implementation", "result_commit", "result_ref"))
  pure val attemptChoiceFields = List(List("attempt_commit", "attempt_id", "attempt_ref", "commit", "request_commit",
    "request_implementation", "result_commit"))

  pure def proofReport(a: Attempt, req: Request, proofId: str, expected: SelectedPublication, request: str, attempt: str): str = {
    val verdict = selectedProofVerdict(a, req, expected, request, "-")
    if (verdict != "inspected") verdict
    else if (a.commit != proofId or a.reportFields != (if (attempt == "") proofFields else attemptProofFields)) "wrong_proof"
    else if (attempt != "" and a.occurrence != { id: h::occurrenceA, commit: attempt, result: expected.result, historicalRef: "" })
      "wrong_proof_attempt"
    else "inspected"
  }

  pure def selectionVerdicts(row: Observation): List[str] = {
    if (not(h::cases.indices().contains(row.scenario))) List("unknown_history")
    else {
      val steps = h::cases[row.scenario]
      val rows = row.attempts
      if (steps.length() != rows.length()) List("missing_steps")
      else {
        val marks = steps.indices().fold(Map(), (out, i) => if (steps[i].mark == "") out else out.put(steps[i].mark, i))
        val nativeIds = rows.foldl(Map(), (out, a) =>
          if (Set("object_view_parent", "object_view_entry", "txn_ref_get", "txn_put_object").contains(a.op) and a.nativeStatus == "ok")
            out.put(a.args[a.args.length() - 1], a.nativeValue) else out)
        val cliIds = List(("native:request-id", "request-id"), ("native:result-id", "result-id"), ("native:producer-id", "producer-id"),
          ("native:good-result-id", "good-result-id"), ("native:legacy-result-id", "legacy-result-id"), ("native:good-attempt-id", "good-attempt-id"))
          .concat(h::resultShapes.concat(h::badAttempts).concat(h::attemptShapes).foldl(List(), (out, s) => out.append((s.cliId, s.id))))
          .foldl(Map(), (out, a) => out.put(a._1, a._2))
        def marked(s: str): Attempt = rows[marks.get(s)]
        def id(s: str): str =
          if (s == "") ""
          else if (s == "plan:plan") marked("plan").commit
          else if (s == "sum:main") marked("prior").commit
          else if (marks.keys().contains(s) and marked(s).op != "txn_get_object") marked(s).commit
          else if (cliIds.keys().contains(s)) nativeIds.get(cliIds.get(s))
          else nativeIds.get(s)
        def parentIds(s: h::Shape): List[str] = s.parents.foldl(List(), (out, k) => out.append(id(k)))
        def checkGraph(mark: str, window: List[Attempt]): bool =
          if (mark == "choice-graph") id("producer") != id("prior") and id("prior") == id("prior-id") and
            singleBinding(window, choiceRole, List(id("request-id"), id("result")), "returned")
          else if (mark == "first-graph") id("first") != id("second") and id("first") == id("duplicate") and
            singleBinding(window, attemptRole, List(id("request-id"), id("result")), h::occurrenceA)
          else if (mark == "second-graph") singleBinding(window, attemptRole, List(id("request-id"), id("result")), h::occurrenceB)
          else if (mark == "chosen-graph") singleBinding(window, attemptChoiceRole, List(id("request-id"), id("first")), "first")
          else if (mark == "proof-graph") {
            if (row.scenario == 0) id("new-plan") != id("plan") and proofGraph(window, List(id("new-plan"), id("choice")), "new-plan", "imported")
            else proofGraph(window, List(id("plan"), id("chosen")), "plan", "chosen")
          } else if (mark == "good-result-graph") candidate(window, id("request-id"), id("sum-dag"), h::v2, "0300000000000000")
          else if (mark == "legacy-result-graph") id("legacy-result-id") != id("good-result-id") and
            candidate(window, id("request-id"), id("sum-dag"), h::v1, "0300000000000000")
          else if (mark == "foreign-result-graph") id("other-request-id") != id("request-id") and
            candidate(window, id("other-request-id"), id("sum-dag"), h::v2, "0400000000000000")
          else if (row.scenario == 1) {
            val s = h::resultShapes.select(s => s.id == mark).head()
            forgedChoice(window, s, parentIds(s))
          } else {
            val candidates = h::badAttempts.select(s => s.id == mark)
            if (candidates.length() == 1) {
              val s = candidates[0]
              singleBinding(window, attemptRole, parentIds(s), s.value)
            } else {
              val s = h::attemptShapes.select(s => s.id == mark).head()
              singleBinding(window, attemptChoiceRole, parentIds(s), s.value)
            }
          }
        def checkReport(a: Attempt, req: Request, mark: str): str =
          if (mark == "imported-report" or mark == "valid-result-choice") {
            val imported = mark == "imported-report"
            val result = if (imported) id("result") else id("good-result-id")
            val historical = if (imported) "returned" else "good-result"
            val verdict = selectionReadVerdict(a, req, id("choice"), { resultRef: historical, result: result }, id("request-id"),
              if (imported) h::v1 else h::v2)
            if (verdict == "inspected" and a.reportFields != choiceFields) "wrong_choice_fields" else verdict
          } else if (mark == "valid-attempt-choice") {
            val expected = { id: h::occurrenceA, commit: id("good-attempt-id"), result: id("good-result-id"), historicalRef: "good-attempt" }
            val verdict = occurrenceReadVerdict(a, req, id("new"), id("request-id"), expected)
            if (verdict == "inspected" and a.reportFields != attemptChoiceFields) "wrong_choice_fields" else verdict
          } else {
            val transferred = mark == "transfer-proof-report"
            val proof = { mode: "reuse", planRef: if (transferred) "new-plan" else "plan", plan: id(if (transferred) "new-plan" else "plan"),
              selectionRef: if (transferred) "imported" else "chosen", selection: id(if (transferred) "choice" else "chosen"), result: id("result") }
            proofReport(a, req, id("proof-id"), proof, id("request-id"), if (transferred) "" else id("first"))
          }
        range(0, steps.length()).foldl(List(), (out, i) => {
          val s = steps[i]
          val a = rows[i]
          val req = s.request
          val verdict =
            if (not(sameRequest(a, req))) "wrong_request"
            else if (s.label == "native_not_found" or (req.op == "txn_ref_get" and s.expected != ""))
              rejectionNativeReadVerdict(a, req, if (s.label == "native_not_found") "" else id(s.expected))
            else if (s.label == "native_ok") {
              val native = rejectionNativeVerdict(a, req, "ok")
              if (native == "native_ok" and s.mark != "" and not(checkGraph(s.mark, rows.slice(i, rows.length())))) "wrong_native_graph"
              else native
            } else if (s.label == "file_observed") {
              if (matches(a, req) and a.bundlePresent and a.unchanged and a.bundleSize > 0) "file_observed" else "wrong_bundle"
            } else if (s.label == "collected") {
              if (matches(a, req) and (if (s.expected == "zero") a.removed == 0 else a.removed > 0)) "collected" else "wrong_collection"
            } else if (req.op == "stage_input") stageVerdict(a, req, id(s.expected))
            else if (req.op == "record_sum") writeVerdict(a, req)
            else if (Set("request_scale", "work_scale").contains(req.op)) scaleWriteVerdict(a, req, id(s.expected))
            else if (req.op == "work_scale_attempt") {
              if (s.label == "recorded") scaleWriteVerdict(a, req, id(req.args[2]))
              else existingRejectionVerdict(a, req, id(req.args[2]), exactDiagnostic(req.op, s.expected, a.stderr))
            } else if (req.op == "inspect") {
              if (s.label == "inspected") checkReport(a, req, s.mark)
              else existingRejectionVerdict(a, req, "", exactDiagnostic(req.op, s.expected, a.stderr))
            } else {
              val selected = id(req.args[4])
              val plan = id(req.args[2])
              val actual = if (req.op == "select_scale_result") a.expectedResult
                else if (req.op == "select_scale_attempt") a.expectedAttempt else a.expectedSelection
              if (selected == "" or actual != selected) "wrong_selection"
              else if (s.label == "rejected") existingRejectionVerdict(a, req, plan, exactDiagnostic(req.op, s.expected, a.stderr))
              else if (req.op == "select_scale_result") selectVerdict(a, req, plan, selected, true)
              else if (req.op == "select_scale_attempt") selectAttemptVerdict(a, req, plan, selected, true)
              else publishSelectedVerdict(a, req, plan, selected, id(s.expected), true)
            }
          out.append(verdict)
        })
      }
    }
  }

  pure val selectionControls = all {
    exactDiagnostic("select_scale_attempt", h::wrongResult, "select-scale-attempt: result does not retain the expected request commit"),
    not(exactDiagnostic("select_scale_attempt", h::wrongResult, "select-scale-attempt: attempt does not retain the expected request commit")),
    not(exactDiagnostic("inspect", h::badUuid, "inspect: expected a scale-attempt-v1 commit with ordered request and result parents")),
    not(exactDiagnostic("inspect", "unknown", "")),
    h::occurrenceA != h::uppercase
  }
}

module recorded_calls_selection_rules {
  import recorded_calls_rules as common from "./recorded_calls_rules"
  import recorded_calls_selection_checks as checks
  import recorded_calls_selection_histories.expected from "./recorded_calls_selection_histories"

  type Attempt = (common::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  pure def historyVerdicts(row: Observation): List[str] = checks::selectionVerdicts(row)
  pure def verdictAccepted(verdict: str): bool = common::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected
  pure val controlsPass = checks::selectionControls
}
