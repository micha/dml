module recorded_calls_supersession_invalid_rules {
  import recorded_calls_rules as r from "./recorded_calls_rules"
  import recorded_calls_supersession_invalid_cases as h from "./recorded_calls_supersession_invalid_histories"
  import recorded_calls_intent_cases as i from "./recorded_calls_intent_histories"
  import recorded_calls_intent_rules as validity from "./recorded_calls_intent_rules"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  pure val entryHex = "7363616c652d696d706c656d656e746174696f6e2d737570657273657373696f6e2d7631"

  pure def stringField(rows: List[Attempt], target: str, text: str): bool = {
    val literal = r::nativeOutput(rows, "datum_decode", target)
    r::nativeNodeMatches(rows, target) and literal.nativeCount == 6 and literal.nativeItems == List(text)
  }
  pure def declarationMatches(rows: List[Attempt], s: h::Shape, ids: (str) => str): bool = {
    val wantedRoot = if (s.root == "v1-node") "predecessor-node" else "successor-node"
    val layout = r::decoded(rows, "declaration-layout")
    all {
      ids(s.name) != "" and (s.name == "noted" or ids(s.name) != ids("noted")),
      r::decoded(rows, h::declarationEntry._1).nativeCount == s.parents.length(),
      r::treeEntry(rows, h::declarationEntry._2, h::declarationEntry._3, entryHex),
      s.parents.indices().forall(j => ids(s.parents[j]) != "" and ids(s.parents[j]) ==
        r::outputId(rows, "object_view_parent", i::parentIndices[j])),
      layout.nativeCount == 3 and layout.nativeValue == r::outputId(rows, "txn_lookup_node", wantedRoot),
      stringField(rows, "predecessor-value", i::v1),
      stringField(rows, "successor-value", if (s.successor == "v1-node") i::v1 else i::v2),
      if (s.reasonNode == "i64-node") r::nativeLiteralMatches(rows, "reason-value", 3, "0700000000000000")
      else stringField(rows, "reason-value", if (s.reasonNode == "bogus-node") "looks-valid" else h::reason)
    }
  }
  pure def decisionMatches(rows: List[Attempt], ids: (str) => str): bool = all {
    validity::entryMatches(rows, h::decisionEntry, i::decision, 2),
    validity::entryMatches(rows, h::planEntry, i::plan, 1),
    ids("pending-id") != "" and ids("pending-id") == ids("decision-plan"),
    ids("pending-request") != "" and ids("pending-request") != ids("pending-id"),
    ids("decision-basis") == ids("basis")
  }
  pure def rejection(a: Attempt, req: Request, id: str, diagnostic: str): str =
    if ((req.args.length() == 3 and id == "") or a.expectedIntent != id) "wrong_knowledge_operand"
    else r::existingRejectionVerdict(a, req, "", a.stderr == diagnostic)

  pure def readDecision(a: Attempt, req: Request, ids: (str) => str, ordinary: Attempt, declaration: r::Declaration): str = {
    val expected: r::Decision = { id: "", canonicalId: true, policy: "", intent: ids("basis"), defaultMode: i::execute,
      override: "default", route: "execute-fresh", reason: "default-execution", plan: ids("pending-id"), planRef: "pending",
      selectionRef: "", selection: "", result: "", implementationOverride: "default", implementationReason: "default-implementation" }
    val historical = r::unannotated(ids("basis"))
    val known = req.args.length() == 3
    val knowledge = if (known) { intent: ids("promoted"), relation: "predecessor", declaration: declaration } else r::noAdvisory
    val verdict = r::advisoryViewVerdict(a, r::intentDecisionReadVerdict(a, req, ids("decision"), ids("pending-request"), i::v1,
      "-", expected, r::noOccurrence), historical, knowledge)
    if (verdict == "inspected" and (a.historicalReportHash == "" or
      (known and a.historicalReportHash != ordinary.historicalReportHash))) "wrong_historical_report"
    else verdict
  }
  pure def inspectVerdict(a: Attempt, req: Request, ids: (str) => str, rows: List[Attempt]): str = {
    val name = req.args[1]
    val declaration: r::Declaration = { commit: ids("noted"), basis: ids("basis"), evidence: ids("producer"),
      predecessor: i::v1, successor: i::v2, reason: h::reason }
    if (name == "producer") r::sumReadVerdict(r::selected, a, req, ids("producer"))
    else if (name == "pending") r::planReadVerdict(a, req, ids("pending-id"), ids("pending-request"), 3,
      rows.select(row => r::sameRequest(row, h::producerRead)).head(), i::v1)
    else if (name == "decision") readDecision(a, req, ids,
      rows.select(row => r::sameRequest(row, i::inspect("decision"))).head(), declaration)
    else {
      val annotated = name == "noted" or name == "promoted"
      val previous = if (name == "noted") ids("basis") else if (name == "promoted") ids("noted") else ""
      val intent: r::Intent = { implementation: if (name == "basis" or name == "noted") i::v1 else i::v2,
        defaultMode: i::execute, v1Selection: "slot-v1", v2Selection: "slot-v2", previous: previous }
      r::advisoryDefinitionVerdict(a, req, ids(name), intent, if (annotated) declaration else r::noDeclaration)
    }
  }
  pure def stepVerdict(s: i::Step, a: Attempt, ids: (str) => str, rows: List[Attempt]): str = {
    val req = s.req
    if (s.want == "rejected") {
      val id = if (req.args.length() == 2) "" else {
        val alias = req.args[2]
        if (alias == h::zeroOperand) h::zero else if (alias == h::shortOperand) h::short
        else ids(alias)
      }
      rejection(a, req, id, s.value)
    } else if (req.op == "inspect") inspectVerdict(a, req, ids, rows)
    else if (req.op == "record_sum") r::writeVerdict(a, req)
    else if (req.op == "declare_scale_supersession") r::declarationVerdict(a, req, ids("basis"), ids("producer"), true)
    else validity::stepVerdict(s, a, ids)
  }
  pure def historyVerdicts(row: Observation): List[str] = {
    val rows = row.attempts
    if (row.scenario != 0) List("unknown_history")
    else if (rows.length() != h::steps.length()) List("missing_steps")
    else {
      val observed = validity::idsFrom(rows).put("noted", rows.select(a => a.op == "declare_scale_supersession").head().commit)
      val aliases = h::malformed.foldl(observed, (out, row) => {
        val name = row._1.name
        if (observed.keys().contains(name)) out.put(row._2, observed.get(name)) else out
      })
      def ids(alias: str): str = if (aliases.keys().contains(alias)) aliases.get(alias) else ""
      range(0, rows.length()).foldl(List(), (out, index) => {
        val s = h::steps[index]
        val verdict = stepVerdict(s, rows[index], ids, rows)
        val graph = s.graph
        val correct = if (graph == "" or verdict != "native_ok") true
          else if (graph == "decision-layout") decisionMatches(rows.slice(index, index + h::decisionReads.length()), ids)
          else if (Set("basis", h::unrelated, "promoted").contains(graph)) {
            val shape = h::definitions.select(d => d.name == graph).head()
            validity::shapeMatches(rows.slice(index, index + i::readShape(shape).length()), shape, ids) and
              (graph != h::unrelated or ids(graph) != ids("basis"))
          } else {
            val shape = h::shapes.select(d => d.name == graph).head()
            declarationMatches(rows.slice(index, index + h::declarationReads(shape).length()), shape, ids)
          }
        out.append(if (correct) verdict else "wrong_native_graph")
      })
    }
  }
  pure val expected = List(h::steps.foldl(List(), (out, s) => out.append(s.want)))
  pure def verdictAccepted(verdict: str): bool = r::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected

  pure val probe = h::negatives[1]
  pure val rejectedProbe = { ...r::recorded, op: probe.req.op, args: probe.req.args, expectedIntent: "forged-commit",
    commit: "", code: 1, stdoutEmpty: true, diagnosed: true, stderr: probe.value, unchanged: true, repoExisted: true, repoExists: true }
  pure val controlsPass = all {
    rejection(rejectedProbe, probe.req, "forged-commit", probe.value) == "rejected",
    rejection(rejectedProbe, probe.req, "genuine-commit", probe.value) == "wrong_knowledge_operand",
    rejection({ ...rejectedProbe, stderr: "inspect: unrelated failure" }, probe.req, "forged-commit", probe.value) == "wrong_diagnostic",
    rejection({ ...rejectedProbe, unchanged: false }, probe.req, "forged-commit", probe.value) == "storage_changed"
  }
}
