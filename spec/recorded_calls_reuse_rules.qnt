module recorded_calls_reuse_check {
  import recorded_calls_rules.* from "./recorded_calls_rules"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_reuse_histories as reuse from "./recorded_calls_reuse_histories"

  pure def parentId(rows: List[Attempt], alias: str): str = outputId(rows, "object_view_parent", alias)
  pure def nodeId(rows: List[Attempt], alias: str): str = outputId(rows, "txn_lookup_node", alias)
  pure def dagId(rows: List[Attempt], alias: str): str = outputId(rows, "object_view_entry", alias)
  pure def stringLiteral(rows: List[Attempt], alias: str, value: str): bool = {
    val datum = nativeOutput(rows, "datum_decode", alias)
    nativeNodeMatches(rows, alias) and datum.nativeCount == 6 and datum.nativeItems == List(value)
  }
  pure def readWindow(rows: List[Attempt], reqs: List[Request]): List[Attempt] = {
    val start = range(0, rows.length()).select(i => sameRequest(rows[i], reqs[0])).head()
    rows.slice(start, start + reqs.length())
  }
  pure def resultRows(rows: List[Attempt], pin: str): List[Attempt] = readWindow(rows, reuse::readResult(pin, true))
  pure val planEntry = "7363616c652d706c616e2d7631"
  pure val requestEntry = "7363616c652d726571756573742d7631"
  pure val resultEntry = "7265717565737465642d7363616c652d7631"
  pure val reuseEntry = "7265636f726465642d7363616c652d72657573652d7631"
  pure val three = "0300000000000000"
  pure val four = "0400000000000000"
  pure val thirtySix = "2400000000000000"
  pure val minusNinetyEight = "9effffffffffffff"

  pure def planLayout(rows: List[Attempt], producer: str, prior: str, implementation: str): bool = all {
    decoded(rows, "plan-commit").nativeCount == (if (prior == "-") 1 else 2),
    if (prior == "-") true else parentId(rows, "captured-main") == prior,
    treeEntry(rows, "plan-tree", "plan-dag", planEntry),
    decoded(rows, "request-commit").nativeCount == 1,
    treeEntry(rows, "request-tree", "request-dag", requestEntry),
    dagId(rows, "request-dag") == dagId(rows, "plan-dag"),
    parentId(rows, "request-producer") == producer,
    treeEntry(rows, "sum-tree", "sum-dag", sumEntryHex),
    decoded(rows, "request-root").nativeCount == 2,
    decoded(rows, "request-root").nativeValue == nodeId(rows, "request-version"),
    stringLiteral(rows, "request-version-value", implementation),
    nativeLiteralMatches(rows, "request-factor-value", 3, three)
  }

  pure def resultLayout(rows: List[Attempt], id: str, request: str, implementation: str, input: str,
                        factor: str, value: str): bool = all {
    storedRef(rows, "candidate-id") == id,
    decoded(rows, "candidate-commit").nativeCount == 1,
    parentId(rows, "candidate-parent") == request,
    treeEntry(rows, "candidate-tree", "candidate-dag", resultEntry),
    decoded(rows, "candidate-root").nativeCount == 3,
    stringLiteral(rows, "candidate-version-value", implementation),
    nativeLiteralMatches(rows, "candidate-factor-value", 3, factor),
    nativeNodeMatches(rows, "candidate-producer-dag"),
    decoded(rows, "candidate-producer-dag").nativeValue == input,
    nativeLiteralMatches(rows, "candidate-result-value", 3, value)
  }

  pure def malformedCandidateLayouts(rows: List[Attempt], request: str, producer: str): bool = {
    val good = resultRows(rows, "good")
    val goodTree = decoded(good, "candidate-commit").nativeValue
    val sumDag = dagId(rows, "sum-dag")
    val decoyDag = dagId(rows, "decoy-dag")
    val otherRequest = parentId(rows, "other-request")
    all {
      decoded(rows, "bad-plan-commit").nativeCount == 1,
      treeEntry(rows, "bad-plan-tree", "bad-plan-dag", planEntry),
      dagId(rows, "bad-plan-dag") == dagId(rows, "other-plan-dag"),
      dagId(rows, "bad-plan-dag") != dagId(rows, "request-dag"),
      parentId(rows, "bad-plan-request") == request,
      otherRequest != request, parentId(rows, "other-producer") == producer,
      decoded(rows, "other-request-commit").nativeCount == 1,
      treeEntry(rows, "other-request-tree", "other-request-dag", requestEntry),
      dagId(rows, "other-request-dag") == dagId(rows, "bad-plan-dag"),
      sumDag != decoyDag, decoded(rows, "sum-root").nativeValue == decoded(rows, "decoy-root").nativeValue,
      resultLayout(good, storedObject(rows, "result"), request, scaleV1, sumDag, three, thirtySix),
      resultLayout(resultRows(rows, "wrong-factor"), storedObject(rows, "wrong-factor"), request, scaleV1, sumDag, four, thirtySix),
      resultLayout(resultRows(rows, "wrong-producer"), storedObject(rows, "wrong-producer"), request, scaleV1, decoyDag, three, thirtySix),
      storedRef(rows, "bad-shape-pin") == storedObject(rows, "bad-shape"),
      decoded(rows, "bad-shape-head").nativeCount == 0, decoded(rows, "bad-shape-head").nativeValue == goodTree,
      storedRef(rows, "wrong-request-pin") == storedObject(rows, "wrong-request"),
      decoded(rows, "wrong-request-head").nativeCount == 1, decoded(rows, "wrong-request-head").nativeValue == goodTree,
      parentId(rows, "wrong-request-parent") == otherRequest
    }
  }

  pure def resultReport(a: Attempt, reads: List[Attempt], commit: str, request: str, producer: str,
                        implementation: str, factor: int, input: int, value: int): bool =
    if (a.calls.length() != 2) false
    else all {
      a.commit == commit, a.requestCommit == request, a.producerCommit == producer,
      a.reportFields == List(List("calls", "commit", "producer_commit", "request_commit")).concat(scaleReportFields),
      a.calls[0].dag == decoded(reads, "candidate-producer-dag").nativeValue, a.calls[0].resultValue == input,
      a.calls[1] == { dag: dagId(reads, "candidate-dag"), implementation: implementation,
        resultNode: decoded(reads, "candidate-root").nativeValue, resultValue: value,
        arguments: List({ name: "factor", node: nodeId(reads, "candidate-factor"), value: factor, producer: "" },
          { name: "input", node: nodeId(reads, "candidate-input"), value: input, producer: a.calls[0].dag }) }
    }

  pure def proofShape(rows: List[Attempt], parents: int, first: str, second: str): bool = all {
    decoded(rows, "proof-commit").nativeCount == parents,
    parentId(rows, "proof-first") == first,
    if (parents == 2) parentId(rows, "proof-second") == second else true,
    treeEntry(rows, "proof-tree", "proof-dag", reuseEntry)
  }
  pure def proofGraph(rows: List[Attempt], expected: ReusePublication): bool = all {
    proofShape(rows, 2, expected.plan, expected.result),
    decoded(rows, "proof-root").nativeCount == 2,
    decoded(rows, "proof-root").nativeValue == nodeId(rows, "proof-plan-node"),
    stringLiteral(rows, "proof-plan-value", expected.planRef),
    stringLiteral(rows, "proof-result-value", expected.resultRef)
  }
  pure val proofFields = List(List("commit", "expected_main", "plan_commit", "plan_ref", "publication_mode",
    "request_commit", "result_commit", "result_ref"))
  pure def exactProofReport(a: Attempt, r: Request, proofId: str, expected: ReusePublication, request: str, prior: str): str = {
    val verdict = reuseRecordVerdict(a, r, expected, request, prior)
    if (verdict != "inspected") verdict
    else if (a.commit != proofId or a.reportFields != proofFields) "wrong_reuse_record"
    else "inspected"
  }

  pure def malformedProofGraph(rows: List[Attempt], name: str, proof: ReusePublication): bool = {
    val spec = reuse::proofDefects.select(p => p._1 == name).head()
    val count = spec._3.length()
    val good = readWindow(rows, reuse::readProof("reuse"))
    val bad = readWindow(rows, reuse::readForgedProof(name, count))
    val first = if (name == "reversed-parents") proof.result else proof.plan
    val second = if (name == "reversed-parents") proof.plan else if (name == "wrong-request") storedObject(rows, "other-result") else proof.result
    val planNode = nodeId(bad, "proof-plan-node")
    val resultNode = nodeId(bad, "proof-result-node")
    val goodResultNode = nodeId(good, "proof-result-node")
    val goodDag = dagId(good, "proof-dag")
    val sameDag = Set("reversed-parents", "missing-parent", "wrong-request").contains(name)
    all {
      proofShape(bad, count, first, second),
      storedRef(bad, "proof-id") == storedObject(rows, name),
      storedRef(bad, "proof-id") != storedRef(good, "proof-id"),
      planNode == nodeId(good, "proof-plan-node"),
      (dagId(bad, "proof-dag") == goodDag) == sameDag,
      decoded(bad, "proof-root").nativeValue == (if (name == "wrong-dag-root") resultNode else planNode),
      decoded(bad, "proof-root").nativeCount == (if (name == "extra-binding") 3 else 2),
      if (name == "extra-binding") nodeId(bad, "extra-binding-node") == storedObject(rows, "number-node") else true,
      if (name == "invalid-name") stringLiteral(bad, "proof-result-value", "invalid/name")
      else if (name == "main-alias") stringLiteral(bad, "proof-result-value", "main")
      else if (name == "plan-alias") resultNode == planNode
      else if (name == "wrong-type") nativeLiteralMatches(bad, "proof-result-value", 3, "0700000000000000")
      else resultNode == goodResultNode
    }
  }

  pure def directReuseVerdicts(phase: int, rows: List[Attempt]): List[str] = {
    val steps = reuse::directReuseCases[phase]
    if (rows.length() != steps.length()) List("missing_steps")
    else {
      val marks = range(0, steps.length()).foldl(Map(), (out, i) =>
        if (steps[i].mark == "") out else out.put(steps[i].mark, rows[i]))
      def marked(key: str): Attempt = marks.get(key)
      val built = if (phase == 0) Map("native:candidate" -> "candidate")
        else if (phase == 1) Map("native:bad-plan" -> "bad-plan", "native:bad-shape" -> "bad-shape",
          "native:wrong-factor" -> "wrong-factor", "native:wrong-producer" -> "wrong-producer", "native:wrong-request" -> "wrong-request")
        else if (phase == 3) Map("native:alternate" -> "alternate") else Map()
      def id(key: str): str =
        if (key == "") ""
        else if (key == "ref:proof-id") storedRef(rows, "proof-id")
        else if (key == "ref:receipt-id") storedRef(rows, "receipt-id")
        else if (key == "native:result") storedObject(rows, "result")
        else if (built.keys().contains(key)) storedObject(rows, built.get(key))
        else marked(key).commit
      val request = parentId(rows, "request-id")
      val producer = id("producer")
      val prior = if (Set(0, 2, 3, 5).contains(phase)) id("prior") else "-"
      val initialPrior = if (phase == 2) "-" else prior
      val planName = if (phase == 3) reuse::maxName else "plan"
      val planId = id(if (phase == 3) "long-plan" else "plan")
      val sumDag = dagId(rows, "sum-dag")
      val result = if (phase == 0) storedObject(rows, "matching") else id("native:result")
      val proof: ReusePublication = { mode: "reuse", planRef: planName, plan: planId,
        resultRef: if (phase == 5) "returned" else "history", result: result }
      val overflow = phase == 2 or phase == 3
      val implementation = if (phase == 0) scaleV2 else scaleV1
      val fixtures = planLayout(rows, producer, initialPrior, implementation) and
        (if (phase == 0) all {
          resultLayout(resultRows(rows, "candidate"), id("native:candidate"), request, scaleV1, sumDag, three, thirtySix),
          resultLayout(resultRows(rows, "matching"), result, request, scaleV2, sumDag, three, thirtySix)
        } else if (phase == 1) malformedCandidateLayouts(rows, request, producer)
        else if (overflow) all {
          resultLayout(resultRows(rows, "history"), result, request, scaleV1, sumDag, three, minusNinetyEight),
          prior != result, prior != producer,
          if (phase == 2) all { planId != id("first-plan"), decoded(rows, "next-plan-commit").nativeCount == 2,
            treeEntry(rows, "next-plan-tree", "next-plan-dag", planEntry), dagId(rows, "next-plan-dag") == dagId(rows, "request-dag"),
            parentId(rows, "next-plan-request") == request, parentId(rows, "next-main") == prior }
          else resultLayout(resultRows(rows, "staged"), id("native:alternate"), request, scaleV1, sumDag, three, "6300000000000000") and
            id("native:alternate") != result
        } else true)
      reuse::mapList(range(0, steps.length()), i => {
        val s = steps[i]
        val a = rows[i]
        val req = s.request
        if (not(sameRequest(a, req))) "wrong_request"
        else if (s.label == "native_not_found") rejectionNativeReadVerdict(a, req, "")
        else if (req.op == "txn_ref_get" and req.args[2] == "state-ref") {
          val target = id(s.expected)
          if (target == "") "missing_pin_target" else rejectionNativeReadVerdict(a, req, target)
        } else if (s.label == "native_ok") {
          if (req.op == "txn_get_object" and a.nativeValue == "") "missing_object"
          else rejectionNativeVerdict(a, req, "ok")
        } else if (s.label == "recorded") {
          if (req.op == "request_scale") scaleWriteVerdict(a, req, producer) else writeVerdict(a, req)
        } else if (s.label == "collected") {
          if (matches(a, req) and a.removed > 0 and not(a.stdoutEmpty)) "collected" else "wrong_collection"
        } else if (not(fixtures)) "wrong_reuse_fixture"
        else if (s.label == "rejected") {
          val sourceId = if (req.op == "inspect") "" else id(req.args[2])
          val bundle = req.op == "export_scale"
          val selectsResult = Set("stage_reused_scale", "publish_reused_scale", "publish_requested_scale").contains(req.op)
          if (selectsResult and a.expectedResult != id(req.args[4])) "wrong_selection"
          else if (bundle and (a.bundlePresent or not(a.bundleUnchanged) or a.bundleSize != -1)) "wrong_bundle"
          else if (phase == 5 and not(malformedProofGraph(rows, req.args[1], proof))) "wrong_proof_fixture"
          else existingRejectionVerdict(a, req, sourceId, a.stderr == s.expected)
        } else if (req.op == "publish_requested_scale" or req.op == "publish_reused_scale")
          publishVerdict(a, req, result, id(req.args[2]), "", true)
        else if (req.op == "stage_reused_scale")
          reuseStageVerdict(a, req, planId, result, true)
        else if (not(matches(a, req))) "wrong_inspect"
        else if (not(a.unchanged)) "storage_changed"
        else if (s.mark == "proof-report" or s.mark == "retained-proof") {
          if (not(proofGraph(readWindow(rows, reuse::readProof("reuse")), proof))) "wrong_reuse_graph"
          else exactProofReport(a, req, id("ref:proof-id"), proof, request, prior)
        } else if (s.mark == "sum-report")
          sumReadVerdict({ ...selected, a: (reuse::maxI64, 9223372036854775807), b: ("0", 0) }, a, req, producer)
        else if (s.mark == "stored-result") {
          if (resultReport(a, resultRows(rows, "history"), result, request, producer,
            scaleV1, 3, 9223372036854775807, -98) and a.calls[0] == marked("sum-report").calls[0]) "inspected"
          else "wrong_stored_graph"
        } else if (s.mark == "staged-result" or s.mark == "main-result") {
          if (equivalentReports(a, marked("stored-result"))) "inspected" else "wrong_stored_report"
        } else if (s.mark == "matching-result" or s.mark == "valid-result") {
          if (resultReport(a, resultRows(rows, req.args[1]), result, request, producer, implementation, 3, 12, 36)) "inspected"
          else "wrong_result_graph"
        } else if (s.mark == "other-report") {
          if (a.commit == storedObject(rows, "other-result") and a.requestCommit == parentId(rows, "other-request") and
              a.requestCommit != request and a.producerCommit == producer and a.calls.length() == 2 and
              a.calls[1].resultValue == 48 and a.calls[1].implementation == scaleV1) "inspected"
          else "wrong_nested_result"
        } else "unclassified_reuse_step"
      })
    }
  }

  pure val directReuseControls = {
    val proof: ReusePublication = { mode: "reuse", planRef: "plan", plan: "plan-id", resultRef: "history", result: "result-id" }
    val report = { ...recorded, op: "inspect", args: List("source", "reuse"), commit: "proof-id", unchanged: true,
      reusePublication: proof, reportFields: proofFields, requestCommit: "request-id", expectedMain: "-" }
    val req: Request = { op: report.op, args: report.args }
    all {
      exactProofReport(report, req, "proof-id", proof, "request-id", "-") == "inspected",
      exactProofReport(report, req, "other-proof", proof, "request-id", "-") == "wrong_reuse_record",
      exactProofReport({ ...report, reportFields: List(List("commit")) }, req, "proof-id", proof, "request-id", "-") == "wrong_reuse_record",
      exactProofReport({ ...report, unchanged: false }, req, "proof-id", proof, "request-id", "-") == "storage_changed"
    }
  }
}

module recorded_calls_reuse_rules {
  import recorded_calls_reuse_check as check
  import recorded_calls_rules as common from "./recorded_calls_rules"
  import recorded_calls_reuse_histories.directReuseExpected from "./recorded_calls_reuse_histories"

  type Attempt = (common::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }
  pure def historyVerdicts(row: Observation): List[str] =
    if (directReuseExpected.indices().contains(row.scenario)) check::directReuseVerdicts(row.scenario, row.attempts)
    else List("unknown_history")
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == directReuseExpected.length() and verdicts == directReuseExpected
  pure def verdictAccepted(verdict: str): bool = common::verdictAccepted(verdict)
  pure val controlsPass = check::directReuseControls
}
