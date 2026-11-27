module recorded_calls_policy_rules {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_policy_histories as h from "./recorded_calls_policy_histories"
  import recorded_calls_rules as r from "./recorded_calls_rules"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  type Marks = str -> Attempt
  type Native = (str, str, str) -> Attempt

  pure val reuseReportFields = List(List("action", "commit", "decision_id", "expected_main", "override", "plan_commit",
    "policy_commit", "policy_default", "reason", "request_commit", "result_commit", "selection_commit", "selection_ref"))
  pure val attemptReportFields = List(List("action", "attempt_commit", "attempt_id", "commit", "decision_id", "expected_main", "override",
    "plan_commit", "policy_commit", "policy_default", "reason", "request_commit", "result_commit", "selection_commit", "selection_ref"))
  pure val freshReportFields = List(List("action", "commit", "decision_id", "expected_main", "override", "plan_commit", "plan_ref",
    "policy_commit", "policy_default", "reason", "request_commit"))
  pure def report(a: Attempt, req: Request, commit: str, portable: str, prior: str, decision: r::Decision,
                  occurrence: r::Occurrence, expectedFields: List[List[str]]): str =
    if (a.reportFields != expectedFields) "wrong_report_fields"
    else r::decisionReadVerdict(a, req, commit, portable, prior, decision, occurrence)

  pure def roleHex(role: str): str =
    if (role == h::policyRole) "7363616c652d696e74656e742d706f6c6963792d7631"
    else if (role == h::decisionRole) "7363616c652d726571756573742d6465636973696f6e2d7631"
    else if (role == h::planRole) "7363616c652d706c616e2d7631"
    else ""
  pure def id(marks: Marks, alias: str): str = {
    val a = marks.get(alias)
    if (a.nativeStatus == "ok") a.nativeValue else a.commit
  }
  pure def nativeValue(rows: Native, scope: str, op: str, alias: str): str = rows.get((scope, op, alias)).nativeValue
  pure def treeMatches(rows: Native, scope: str, tree: str, dag: str, role: str): bool =
    roleHex(role) != "" and rows.get((scope, "object_decode", tree)).nativeCount == 1 and
    rows.get((scope, "object_view_entry", dag)).nativeItems == List(roleHex(role))
  pure def graph(rows: Native, marks: Marks, shape: h::Shape, uuid: str): bool = {
    val scope = shape.name
    val dag = rows.get((scope, "object_decode", "dag-view"))
    rows.get((scope, "object_decode", "shape-view")).nativeCount == shape.parents.length() and
    treeMatches(rows, scope, "shape-tree", "shape-dag", shape.role) and dag.nativeCount == shape.fields.length() and
    dag.nativeValue != "" and dag.nativeValue == nativeValue(rows, scope, "txn_lookup_node", shape.root) and
    shape.parents.indices().forall(i => {
      val alias = shape.parents[i]
      val actual = nativeValue(rows, scope, "object_view_parent", h::parentAliases[i])
      // Generated plan IDs are taken from their native parent edge and checked separately.
      actual != "" and (alias == "" or actual == id(marks, alias))
    }) and shape.fields.indices().forall(i => {
      val pair = shape.fields[i]
      val alias = h::literalAliases.get(pair._1)
      val literal = nativeValue(rows, scope, "txn_get_object", alias)
      val datum = rows.get((scope, "datum_decode", alias))
      literal != "" and literal == nativeValue(rows, scope, "literal_node_encode", alias) and datum.nativeCount == 6 and
      datum.nativeItems == List(if (pair._1 == "decision_id" and pair._2 == "") uuid else pair._2)
    })
  }
  pure def planGraph(rows: Native, scope: str, view: str, tree: str, dag: str, parents: int): bool =
    treeMatches(rows, scope, tree, dag, h::planRole) and rows.get((scope, "object_decode", view)).nativeCount == parents and
    nativeValue(rows, scope, "object_view_entry", dag) == nativeValue(rows, "", "object_view_entry", "request-dag")

  pure def selectionDecision(policy: str, plan: str, slot: str, selection: str, result: str): r::Decision = {
    id: "", canonicalId: true, policy: policy, intent: "", defaultMode: h::reuseDefault,
    override: "default", route: "reuse-selected", reason: "default-selection", plan: plan, planRef: "",
    selectionRef: slot, selection: selection, result: result, implementationOverride: "", implementationReason: ""
  }
  pure def freshDecision(policy: str, plan: str): r::Decision = {
    ...selectionDecision(policy, plan, "", "", ""), override: "fresh", route: "execute-fresh", reason: "override-fresh", planRef: "would-plan"
  }
  pure def reuseInspection(a: Attempt, req: Request, marks: Marks, rows: Native, name: str): str = {
    val shape = h::repeatedShapes.select(s => s.name == name).head()
    val plan = nativeValue(rows, name, "object_view_parent", "shape-parent-0")
    val request = nativeValue(rows, name, "object_view_parent", "plan-request")
    val prior = nativeValue(rows, name, "object_view_parent", "plan-main")
    val result = id(marks, "result")
    val decision = selectionDecision(id(marks, "policy"), plan, "legacy", id(marks, "legacy"), result)
    if (not(graph(rows, marks, shape, a.decision.id)) or
      not(planGraph(rows, name, "plan-view", "plan-tree", "plan-dag", 2)) or
      request != id(marks, "request-id") or prior != id(marks, if (name == h::first.name) "prior-main" else "result")) "wrong_native_graph"
    else if (name == h::repeat.name and (id(marks, name) == id(marks, h::again.name) or
      a.decision.id == marks.get("again-report").decision.id or plan != nativeValue(rows, h::again.name, "object_view_parent", "shape-parent-0")))
      "wrong_decision_identity"
    else report(a, req, id(marks, name), request, prior, decision, r::noOccurrence, reuseReportFields)
  }
  pure def readerInspection(a: Attempt, req: Request, marks: Marks, rows: Native): str = {
    val policy = id(marks, "policy")
    val request = id(marks, "request-id")
    if (req.args[1] == h::valid.name) {
      val result = id(marks, "attempt-result")
      val decision = { ...selectionDecision(policy, id(marks, "plan"), "chosen", id(marks, "chosen"), result), id: h::fixtureUuid }
      val occurrence: r::Occurrence = { id: h::attemptUuid, commit: id(marks, "attempt"), result: result, historicalRef: "" }
      report(a, req, id(marks, h::valid.name), request, "-", decision, occurrence, attemptReportFields)
    } else {
      val plan = id(marks, "fresh-plan")
      if (not(graph(rows, marks, h::fresh, a.decision.id)) or
        not(planGraph(rows, "", "fresh-plan-view", "fresh-plan-tree", "fresh-plan-dag", 1)) or
        nativeValue(rows, "", "object_view_parent", "fresh-plan-request") != request) "wrong_native_graph"
      else report(a, req, id(marks, h::fresh.name), request, "-", freshDecision(policy, plan), r::noOccurrence, freshReportFields)
    }
  }

  pure def historyVerdicts(row: Observation): List[str] = {
    if (not(h::cases.indices().contains(row.scenario))) List("unknown_history")
    else {
      val steps = h::cases[row.scenario]
      val rows = row.attempts
      if (rows.length() != steps.length()) List("missing_steps")
      else {
        val marks = range(0, steps.length()).foldl(Map(), (out, i) => if (steps[i].mark == "") out else out.put(steps[i].mark, rows[i]))
        val native = range(0, steps.length()).foldl(Map(), (out, i) => {
          val scope = steps[i].scope
          val a = rows[i]
          if (a.op == "object_encode" and a.args[0] == "node" and a.args[1] == "literal")
            out.put((scope, "literal_node_encode", a.args[2]), a)
          else if (Set("object_decode", "object_view_entry", "object_view_parent", "txn_lookup_node", "txn_get_object", "datum_decode").contains(a.op))
            out.put((scope, a.op, a.args[a.args.length() - 1]), a) else out
        })
        val producer = id(marks, "producer")
        range(0, steps.length()).foldl(List(), (out, i) => {
          val s = steps[i]
          val a = rows[i]
          val req = s.request
          val op = req.op
          val verdict = if (not(r::sameRequest(a, req))) "wrong_request"
            else if (op == "request_policy_scale") {
              val expectedPolicy = id(marks, req.args[3])
              val selection = id(marks, req.args[9])
              if (a.expectedPolicy != expectedPolicy or a.expectedSelection != selection) "wrong_policy_guard"
              else if (s.label == "rejected") r::existingRejectionVerdict(a, req, producer, a.stderr == s.check)
              else r::intentVerdict(a, req, producer, expectedPolicy, selection, true)
            } else if (op == "define_scale_policy") {
              val basis = if (req.args.length() == 3) "" else id(marks, req.args[3])
              if (s.label == "rejected") r::existingRejectionVerdict(a, req, basis, a.stderr == s.check)
              else r::scaleWriteVerdict(a, req, basis)
            } else if (s.label == "rejected") r::existingRejectionVerdict(a, req, "", a.stderr == s.check)
            else if (s.label == "native_not_found") r::rejectionNativeReadVerdict(a, req, "")
            else if (s.label == "native_ok") {
              if (s.mark != "" and a.nativeValue == "") "missing_native_id"
              else if (op == "txn_ref_get" and s.check != "") {
                val expectedId = id(marks, s.check)
                if (expectedId == "") "missing_expected_id"
                else r::rejectionNativeReadVerdict(a, req, expectedId)
              } else if (row.scenario == 1 and op == "txn_get_object" and req.args[3] == "shape-view" and
                h::forged.append(h::positivePolicy).select(s0 => s.scope == s0.name).length() == 1) {
                val shape = h::forged.append(h::positivePolicy).select(s0 => s.scope == s0.name).head()
                if (not(graph(native, marks, shape, ""))) "wrong_forgery_graph"
                else r::rejectionNativeVerdict(a, req, "ok")
              } else r::rejectionNativeVerdict(a, req, "ok")
            } else if (op == "record_sum") r::writeVerdict(a, req)
            else if (op == "request_scale") r::scaleWriteVerdict(a, req, producer)
            else if (op == "work_scale" or op == "work_scale_attempt") r::scaleWriteVerdict(a, req, id(marks, "request-id"))
            else if (op == "select_scale_result") r::selectVerdict(a, req, id(marks, "plan"), id(marks, "result"), true)
            else if (op == "select_scale_attempt") r::selectAttemptVerdict(a, req, id(marks, "plan"), id(marks, "attempt"), true)
            else if (op == "record_scale") {
              if (a.commit == id(marks, "result")) "wrong_prior_main" else r::scaleWriteVerdict(a, req, producer)
            } else if (op == "inspect") {
              if (row.scenario == 0) reuseInspection(a, req, marks, native, req.args[1])
              else readerInspection(a, req, marks, native)
            } else "unknown_step"
          out.append(verdict)
        })
      }
    }
  }

  pure def verdictAccepted(verdict: str): bool = r::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == h::expected.length() and verdicts == h::expected
  pure val controlReq = h::inspect("decision")
  pure val controlDecision = { ...freshDecision("policy", "plan"), id: h::fixtureUuid }
  pure val sample = { ...r::recorded, op: controlReq.op, args: controlReq.args, code: 0, quiet: true, unchanged: true,
    commit: "decision", expectedMain: "-", requestCommit: "request", decision: controlDecision, reportFields: freshReportFields }
  pure def sampleVerdict(a: Attempt): str = report(a, controlReq, "decision", "request", "-", controlDecision, r::noOccurrence, freshReportFields)
  pure val controlsPass = all {
    sampleVerdict(sample) == "inspected",
    sampleVerdict({ ...sample, reportFields: List(freshReportFields[0].append("selection_ref")) }) == "wrong_report_fields",
    sampleVerdict({ ...sample, expectedMain: "other" }) == "wrong_decision_lineage",
    sampleVerdict({ ...sample, decision: { ...controlDecision, canonicalId: false } }) == "wrong_decision"
  }
}
