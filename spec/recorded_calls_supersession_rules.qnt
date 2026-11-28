module recorded_calls_supersession_rules {
  import recorded_calls_rules as r from "./recorded_calls_rules"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_supersession_cases as h from "./recorded_calls_supersession_histories"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure def idsFrom(rows: List[Attempt]): str -> str = rows.foldl(Map(), (out, a) => {
    val op = a.op
    if (a.commit != "" and Set("record_sum", "define_scale_intent", "declare_scale_supersession", "request_intent_scale").contains(op)) {
      val alias = a.args[if (op == "declare_scale_supersession") 3 else if (op == "request_intent_scale") 6 else 1]
      out.put(alias, a.commit)
    } else if (a.nativeStatus == "ok" and Set("txn_put_object", "txn_ref_get", "object_view_parent").contains(op)) {
      out.put(a.args[a.args.length() - 1], a.nativeValue)
    } else out
  })

  pure def declaration(ids: (str) => str, name: str, transferred: bool): r::Declaration = {
    val sibling = name == "sibling"
    { commit: ids(name), basis: ids("basis"), evidence: ids(if (sibling) "noted" else if (transferred) "evidence" else "producer"),
      predecessor: if (sibling) h::v2 else h::v1, successor: if (sibling) h::v1 else h::v2,
      reason: if (transferred and not(sibling)) h::replace else h::fix }
  }
  pure def declarationGraph(rows: List[Attempt], d: r::Declaration): bool = {
    def literalField(alias: str, text: str): bool = {
      val datum = r::nativeOutput(rows, "datum_decode", alias)
      r::nativeNodeMatches(rows, alias) and datum.nativeCount == 6 and datum.nativeItems == List(text)
    }
    all {
      d.commit != "" and d.basis != "" and d.evidence != "" and d.basis != d.evidence,
      r::decoded(rows, "declaration-view").nativeCount == 2,
      r::treeEntry(rows, "declaration-tree", "declaration-dag", "7363616c652d696d706c656d656e746174696f6e2d737570657273657373696f6e2d7631"),
      r::outputId(rows, "object_view_parent", "declaration-basis") == d.basis,
      r::outputId(rows, "object_view_parent", "declaration-evidence") == d.evidence,
      r::decoded(rows, "declaration-root").nativeCount == 3,
      r::decoded(rows, "declaration-root").nativeValue == r::outputId(rows, "txn_lookup_node", "predecessor-node"),
      literalField("predecessor-value", d.predecessor), literalField("successor-value", d.successor), literalField("reason-value", d.reason)
    }
  }

  pure val declarationFields = List("basis_commit", "commit", "evidence_commit", "predecessor", "reason", "successor")
  pure val viewFields = List("declaration", "intent_commit", "relation")
  pure def viewKeys(view: r::Advisory): List[List[str]] = List(viewFields)
    .concat(if (view.declaration == r::noDeclaration) List() else List(declarationFields))
  pure def decisionKeys(historical: r::Advisory, knowledge: r::Advisory): List[List[str]] = {
    val leading = List("action", "as_known_then", "commit", "decision_id", "expected_main", "implementation_override",
      "implementation_reason", "intent_commit")
    val knowledgeKey = if (knowledge == r::noAdvisory) List() else List("knowledge_view")
    val trailing = List("override", "plan_commit", "plan_ref", "policy_default", "reason", "request_commit", "request_implementation")
    List(leading.concat(knowledgeKey).concat(trailing)).concat(viewKeys(historical))
      .concat(if (knowledge == r::noAdvisory) List() else viewKeys(knowledge))
  }
  pure def unchangedReport(read: Attempt, prior: Attempt): bool =
    prior.historicalReportHash != "" and read.historicalReportHash == prior.historicalReportHash
  pure def decisionRead(a: Attempt, req: Request, rows: List[Attempt], ids: (str) => str): str = {
    val name = req.args[1]
    val old = name == "old"
    val definition = ids(if (old) "basis" else "promoted")
    val path = if (old) h::oldPath else h::newPath
    val expected: r::Decision = { id: "", canonicalId: true, policy: "", intent: definition, defaultMode: h::execute,
      override: "default", route: "execute-fresh", reason: "default-execution", plan: ids(path.planId),
      planRef: path.plan, selectionRef: "", selection: "", result: "", implementationOverride: "default",
      implementationReason: "default-implementation" }
    val saved = ids(path.requestId)
    val annotated: r::Advisory = { intent: ids("promoted"), relation: "successor", declaration: declaration(ids, "noted", true) }
    val historical = if (old) r::unannotated(ids("basis")) else annotated
    val hasKnowledge = req.args.length() == 3
    val knowledge = if (not(hasKnowledge)) r::noAdvisory
      else if (req.args[2] == "promoted") { ...annotated, relation: "predecessor" }
      else if (req.args[2] == "basis") r::unannotated(ids("basis"))
      else { intent: ids("sibling"), relation: "predecessor", declaration: declaration(ids, "sibling", true) }
    val result = r::advisoryViewVerdict(a, r::intentDecisionReadVerdict(a, req, ids(name), saved,
      if (old) h::v1 else h::v2, "-", expected, r::noOccurrence), historical, knowledge)
    val prior = rows.select(b => b.op == "inspect" and b.args == List("replica", name)).head()
    if (result != "inspected") result
    else if (definition == "" or expected.plan == "" or saved == "" or ids(path.intentId) != definition or
        r::decoded(rows, path.commit).nativeCount != 2 or r::decoded(rows, path.planView).nativeCount != 1)
      "wrong_decision_parents"
    else if (a.reportFields != decisionKeys(historical, knowledge)) "wrong_advisory_fields"
    else if (hasKnowledge and not(unchangedReport(a, prior))) "historical_report_changed"
    else result
  }

  pure def stepVerdict(s: h::Step, a: Attempt, rows: List[Attempt], ids: (str) => str): str = {
    val req = s.req
    val op = req.op
    val args = req.args
    if (not(r::sameRequest(a, req))) "wrong_request"
    else if (s.want == "native_not_found") r::rejectionNativeReadVerdict(a, req, "")
    else if (s.want == "native_ok") {
      val verdict = r::rejectionNativeVerdict(a, req, "ok")
      if (verdict != "native_ok") verdict
      else if (op == "repo_export_commit" and (ids(s.value) == "" or a.nativeItems.length() == 0 or a.nativeItems[0] != ids(s.value)))
        "wrong_bundle_root"
      else if (Set("txn_ref_get", "repo_import_commit_staged").contains(op) and (ids(s.value) == "" or a.nativeValue != ids(s.value)))
        "wrong_native_id"
      else if (op == "object_decode" and args[1] == "empty-tree-view" and a.nativeCount != 0) "evidence_not_empty"
      else if (op == "object_decode" and args[1] == "declaration-view") {
        val sibling = ids("sibling") != ""
        val name = if (sibling) "sibling" else "noted"
        if (declarationGraph(rows, declaration(ids, name, sibling))) verdict else "wrong_native_declaration"
      } else verdict
    } else if (op == "declare_scale_supersession") {
      val basis = ids(args[2])
      val evidence = ids(args[8])
      if (basis == "" or evidence == "" or a.expectedIntent != basis or a.expectedEvidence != evidence) "wrong_declaration_guard"
      else if (s.want == "rejected") r::existingRejectionVerdict(a, req, "", a.stderr == s.value)
      else r::declarationVerdict(a, req, basis, evidence, true)
    } else if (op == "record_sum") r::writeVerdict(a, req)
    else if (op == "define_scale_intent") r::scaleWriteVerdict(a, req, ids(s.value))
    else if (op == "request_intent_scale") r::implementationIntentVerdict(a, req, ids("producer"), ids(args[4]), "", true)
    else if (op == "collect") r::collectVerdict(a, req)
    else if (op == "checkpoint_file" or op == "compare_file") {
      if (a.repoExists and (op == "checkpoint_file" or a.unchanged)) "file_observed" else "origin_storage_changed"
    } else if (op == "inspect" and args[0] == "replica") decisionRead(a, req, rows, ids)
    else if (op == "inspect") {
      val name = args[1]
      val annotated = name == "noted"
      val expected: r::Intent = { implementation: h::v2, defaultMode: h::reuse, v1Selection: "slot-v1",
        v2Selection: "slot-v2", previous: if (annotated) ids("basis") else "" }
      val definitionKeys = List(List("commit", "default_implementation", "policy_default", "previous_intent_commit", "supersession",
        "v1_selection_ref", "v2_selection_ref")).concat(if (annotated) List(declarationFields) else List())
      if (a.reportFields != definitionKeys) "wrong_definition_fields"
      else r::advisoryDefinitionVerdict(a, req, ids(name), expected,
        if (annotated) declaration(ids, name, false) else r::noDeclaration)
    } else "unknown_step"
  }

  pure val nativeOperands = Map("native:producer-id" -> "producer-id", "native:basis-id" -> "basis-id",
    "native:empty-id" -> "empty-id", "native:noted-id" -> "noted-id")
  pure def historyVerdicts(row: Observation): List[str] = {
    if (row.scenario < 0 or row.scenario >= h::cases.length()) List("unknown_history")
    else {
      val steps = h::cases[row.scenario]
      val rows = row.attempts
      if (rows.length() != steps.length()) List("missing_steps")
      else {
        val observedIds = idsFrom(rows)
        def ids(alias: str): str = {
          val key = if (nativeOperands.keys().contains(alias)) nativeOperands.get(alias) else alias
          if (observedIds.keys().contains(key)) observedIds.get(key) else ""
        }
        range(0, steps.length()).foldl(List(), (out, i) => out.append(stepVerdict(steps[i], rows[i], rows, ids)))
      }
    }
  }
  pure val expected = h::cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (verdicts, s) => verdicts.append(s.want))))
  pure def verdictAccepted(verdict: str): bool = r::verdictAccepted(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected
  pure val sample = { ...r::recorded, historicalReportHash: "historical-json" }
  pure val controlsPass = unchangedReport(sample, sample) and not(unchangedReport(r::recorded, r::recorded)) and
    not(unchangedReport({ ...sample, historicalReportHash: "overwritten" }, sample))
}
