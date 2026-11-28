module recorded_calls_receipt_rules {
  import recorded_calls_rules.* from "./recorded_calls_rules"
  import recorded_calls_receipt_histories as receipt from "./recorded_calls_receipt_histories"
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"

  pure def receiptShape(rows: List[Attempt], path: receipt::ReceiptPath): bool =
    decoded(rows, path.commit).nativeCount == 0 and
    treeEntry(rows, path.tree, path.dag, "7363616c652d7075626c69636174696f6e2d7631") // scale-publication-v1

  pure def receiptNode(rows: List[Attempt], path: receipt::ReceiptPath, i: int): str =
    outputId(rows, "txn_lookup_node", path.fields[i]._2)

  pure def receiptRoot(dag: Attempt, planNode: str, resultNode: str, malformed: bool): bool =
    dag.nativeCount == 4 and planNode != "" and resultNode != "" and planNode != resultNode and
    dag.nativeValue == (if (malformed) planNode else resultNode)

  pure def publicationKey(plan: str, result: str): Publication =
    { planRef: "plan", plan: plan, stagingRef: "returned", result: result }

  pure def exactReceiptGraph(rows: List[Attempt], key: Publication): bool = {
    val values = List(key.planRef, key.plan, key.stagingRef, key.result)
    val path = receipt::genuinePath
    receiptShape(rows, path) and receiptRoot(decoded(rows, path.root), receiptNode(rows, path, 1),
      receiptNode(rows, path, 3), false) and values.indices().forall(i => {
      val target = path.fields[i]._3
      val datum = nativeOutput(rows, "datum_decode", target)
      nativeNodeMatches(rows, target) and datum.nativeCount == 6 and datum.nativeItems == List(values[i]) // STRING
    })
  }

  pure def forgedReceiptGraph(rows: List[Attempt]): bool = {
    val bad = receipt::malformedPath
    val good = receipt::genuinePath
    val forged = storedRef(rows, bad.id)
    forged != "" and forged == storedObject(rows, "forged-receipt") and forged != storedRef(rows, good.id) and
    receiptShape(rows, bad) and receiptRoot(decoded(rows, bad.root), receiptNode(rows, bad, 1), receiptNode(rows, bad, 3), true) and
    bad.fields.indices().forall(i => receiptNode(rows, bad, i) == receiptNode(rows, good, i))
  }

  pure val receiptReportFields = List(List("commit", "plan_commit", "plan_ref", "result_commit", "staging_ref"))
  pure def exactReceiptReport(a: Attempt, req: Request, id: str, key: Publication): str = {
    val verdict = receiptReadVerdict(a, req, key)
    if (verdict != "inspected") verdict
    else if (a.commit != id or a.reportFields != receiptReportFields) "wrong_receipt"
    else verdict
  }

  pure def changedKeyFields(a: Publication, b: Publication): int =
    List(a.planRef == b.planRef, a.plan == b.plan, a.stagingRef == b.stagingRef, a.result == b.result)
      .foldl(0, (n, equal) => if (equal) n else n + 1)

  pure def alteredResultMatches(rows: List[Attempt], original: Attempt, altered: Attempt, portable: str, producer: str): bool = {
    val alteredId = storedObject(rows, "alternate-result")
    if (original.calls.length() != 2 or altered.calls.length() != 2) false
    else {
      val scale = original.calls[1]
      val expectedScale = { ...scale, dag: storedObject(rows, "alternate-result-dag"),
        resultNode: storedObject(rows, "alternate-result-node"), resultValue: 99 }
      all {
        alteredId != "", alteredId != original.commit, altered.commit == alteredId,
        decoded(rows, "original-result-head").nativeCount == 1,
        portable == outputId(rows, "object_view_parent", "original-result-parent"),
        original.requestCommit == portable, altered.requestCommit == portable,
        original.producerCommit == producer, altered.producerCommit == producer,
        scale.resultValue == 36, expectedScale.dag != scale.dag, expectedScale.resultNode != scale.resultNode,
        altered.calls == List(original.calls[0], expectedScale)
      }
    }
  }

  pure def receiptVerdicts(phase: int, rows: List[Attempt]): List[str] = {
    val steps = receipt::receiptCases[phase]
    if (rows.length() != steps.length()) List("missing_steps")
    else {
      val byMark = range(0, steps.length()).foldl(Map(), (out, i) =>
        if (steps[i].mark == "") out else out.put(steps[i].mark, rows[i]))
      def marked(name: str): Attempt = byMark.get(name)
      def id(name: str): str =
        if (name == "") ""
        else if (name == "ack") storedRef(rows, receipt::genuinePath.id)
        else if (name == "native:alternate-result") storedObject(rows, "alternate-result")
        else marked(name).commit
      val originalKey = publicationKey(id("plan"), id("result"))
      range(0, steps.length()).foldl(List(), (out, i) => {
        val s = steps[i]
        val a = rows[i]
        val req = s.request
        val verdict = if (not(sameRequest(a, req))) "wrong_request"
        else if (req.op == "publish_requested_scale") {
          val plan = id(req.args[2])
          val result = id(req.args[4])
          val key = { planRef: req.args[1], plan: plan, stagingRef: req.args[3], result: result }
          if (s.label == "acknowledged") retryVerdict(a, req, plan, result)
          else if (s.label == "published") publishVerdict(a, req, result, plan, "", true)
          else if (a.expectedResult != result) "wrong_selection"
          else if (s.expected == receipt::wrongKey and changedKeyFields(key, originalKey) != 1) "wrong_key_fixture"
          else if (s.expected == receipt::wrongRoot and not(forgedReceiptGraph(rows))) "wrong_forged_receipt"
          else existingRejectionVerdict(a, req, plan, a.stderr == s.expected)
        } else if (req.op == "inspect") {
          if (s.label == "rejected") existingRejectionVerdict(a, req, "", a.stderr == s.expected)
          else if (not(matches(a, req))) "wrong_inspect"
          else if (not(a.unchanged)) "storage_changed"
          else if (s.mark == "original-result") {
            if (a.commit != id("result") or not(checkCalls(selected, a.calls, scaleV1))) "wrong_result"
            else "inspected"
          } else if (s.mark == "altered-result") {
            if (alteredResultMatches(rows, marked("original-result"), a, id("request"), id("producer"))) "inspected"
            else "wrong_altered_result"
          } else if (s.mark == "recaptured-plan") {
            if (a.commit != id("next-plan") or a.commit == id("plan") or a.expectedMain != id("producer") or
              a.requestCommit != id("request") or a.producerCommit != id("producer") or a.requestFactor != 3 or
              a.requestImplementation != scaleV1 or a.expectedMain == id("prior")) "wrong_recaptured_plan"
            else "inspected"
          } else if (s.expected == receipt::maxReceiptRef)
            exactReceiptReport(a, req, storedRef(rows, "fresh-id"), publicationKey(id("next-plan"), id("result")))
          else if ((phase == 0 or phase == 2) and not(exactReceiptGraph(rows, originalKey))) "wrong_receipt_graph"
          else exactReceiptReport(a, req, id("ack"), originalKey)
        } else if (s.label == "native_not_found") rejectionNativeReadVerdict(a, req, "")
        else if (req.op == "txn_ref_get" and req.args[2] == "read-ref") rejectionNativeReadVerdict(a, req, id(s.expected))
        else if (s.label == "native_ok") rejectionNativeVerdict(a, req, "ok")
        else if (req.op == "record_sum") {
          if (id("producer") == id("prior")) "wrong_prior"
          else writeVerdict(a, req)
        } else if (req.op == "request_scale") scaleWriteVerdict(a, req, id("producer"))
        else if (req.op == "export_request") requestExportVerdict(a, req, id("plan"))
        else if (req.op == "work_scale") scaleWriteVerdict(a, req, id("request"))
        else if (req.op == "export_scale") exportVerdict(a, req, id(s.expected))
        else if (req.op == "stage_input") stageVerdict(a, req, id(s.expected))
        else if (req.op == "collect") {
          if (matches(a, req) and a.removed > 0) "collected" else "wrong_collection"
        } else "unknown_step"
        out.append(verdict)
      })
    }
  }

  pure val receiptControls = {
    val key = publicationKey("plan-id", "result-id")
    val read = { ...recorded, op: "inspect", args: List("source", "ack"), unchanged: true,
      commit: "receipt-id", publication: key, reportFields: receiptReportFields }
    val req = { op: read.op, args: read.args }
    val dag = { ...recorded, nativeCount: 4, nativeValue: "result-node" }
    all {
      exactReceiptReport(read, req, "receipt-id", key) == "inspected",
      exactReceiptReport(read, req, "some-other-receipt", key) == "wrong_receipt",
      exactReceiptReport({ ...read, reportFields: List(List("commit")) }, req, "receipt-id", key) == "wrong_receipt",
      exactReceiptReport({ ...read, unchanged: false }, req, "receipt-id", key) == "storage_changed",
      receiptRoot(dag, "plan-node", "result-node", false),
      not(receiptRoot({ ...dag, nativeCount: 5 }, "plan-node", "result-node", false)),
      not(receiptRoot({ ...dag, nativeValue: "plan-node" }, "plan-node", "result-node", false)),
      receiptRoot({ ...dag, nativeValue: "plan-node" }, "plan-node", "result-node", true),
      changedKeyFields(key, key) == 0,
      changedKeyFields({ ...key, planRef: "alias" }, key) == 1,
      changedKeyFields({ ...key, plan: "other-plan", result: "other-result" }, key) == 2
    }
  }
}
