module recorded_calls_receipt_histories {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  type ReceiptStep = { request: Request, label: str, mark: str, expected: str }
  pure def receiptStep(request: Request, label: str, mark: str, expected: str): ReceiptStep =
    { request: request, label: label, mark: mark, expected: expected }
  pure def receiptNative(requests: List[Request]): List[ReceiptStep] =
    requests.foldl(List(), (steps, r) => steps.append(receiptStep(r, "native_ok", "", "")))
  pure def receiptWrite(requests: List[Request]): List[ReceiptStep] =
    receiptNative(openNative("write").concat(requests).concat(closeNative("txn_commit")))
  pure def receiptRead(queries: List[ReceiptStep]): List[ReceiptStep] =
    receiptNative(openNative("read")).concat(queries).concat(receiptNative(closeNative("txn_abort")))
  pure def receiptRef(ref: str, expected: str): ReceiptStep =
    receiptStep(refRead(ref, "read-ref"), if (expected == "") "native_not_found" else "native_ok", "", expected)
  pure def receiptRefs(refs: List[(str, str)]): List[ReceiptStep] =
    refs.foldl(List(), (steps, ref) => steps.append(receiptRef(ref._1, ref._2)))
  pure def changeRef(ref: str, id: str): Request = coreRequest("txn_ref_update", List("snapshot", ref, id))
  pure def getCommit(id: str): Request = coreRequest("txn_get_object", List("snapshot", "commit", id, "swept-commit"))

  pure val inputs = List(
    receiptStep(source("record_sum", List("producer", "7", "5")), "recorded", "producer", ""),
    receiptStep(source("record_sum", List("main", "12", "0")), "recorded", "prior", ""),
    receiptStep(source("request_scale", List("producer", "producer", "plan", "3")), "recorded", "plan", ""),
    receiptStep(source("export_request", List("plan", "plan", "request.bundle")), "exported", "request", ""),
    receiptStep(worker("stage_input", List("incoming", "request.bundle")), "staged", "", "request"),
    receiptStep(worker("work_scale", List("incoming", "plan", "result")), "recorded", "result", ""),
    receiptStep(worker("export_scale", List("result", "result", "result.bundle")), "exported", "", "result"),
    receiptStep(source("stage_input", List("returned", "result.bundle")), "staged", "", "result")
  )
  pure def publishWith(planRef: str, plan: str, stageRef: str, result: str, key: str, label: str,
                       expected: str): ReceiptStep =
    receiptStep(source("publish_requested_scale", List(planRef, plan, stageRef, result)
      .concat(if (key == "") List() else List(key))), label, "", expected)
  pure def initialPublish(key: str, label: str, expected: str): ReceiptStep =
    publishWith("plan", "plan", "returned", "result", key, label, expected)
  pure def inspectReceipt(key: str): ReceiptStep =
    receiptStep(source("inspect", List(key)), "inspected", "", key)
  pure val readReceiptId = receiptStep(refRead("ack", "receipt-id"), "native_ok", "", "")
  pure val restoreRefs = List(changeRef("main", "sum:main"), pin("plan", "plan:plan"), pin("returned", "scale:worker:result"))
  pure val readyRefs = List(("main", "prior"), ("plan", "plan"), ("returned", "result"))
  pure val publishedRefs = List(("main", "result"), ("plan", ""), ("returned", ""))

  type ReceiptPath = { id: str, commit: str, tree: str, dag: str, root: str, fields: List[(str, str, str)] }
  pure val genuinePath: ReceiptPath = { id: "receipt-id", commit: "receipt-head", tree: "receipt-tree",
    dag: "receipt-dag", root: "receipt-root", fields: List(
      ("plan_ref", "key-plan-ref", "key-plan-ref-value"), ("plan_commit", "key-plan-id", "key-plan-id-value"),
      ("staging_ref", "key-staging-ref", "key-staging-ref-value"), ("result_commit", "key-result-id", "key-result-id-value")) }
  pure val malformedPath: ReceiptPath = { id: "malformed-id", commit: "malformed-head", tree: "malformed-tree",
    dag: "malformed-dag", root: "malformed-root", fields: List(
      ("plan_ref", "malformed-plan-ref", ""), ("plan_commit", "malformed-plan-id", ""),
      ("staging_ref", "malformed-staging-ref", ""), ("result_commit", "malformed-result-id", "")) }
  pure def inspectReceiptGraph(ref: str, path: ReceiptPath): List[Request] = List(refRead(ref, path.id))
    .concat(snapshotAt(path.id, path.commit, path.tree, path.dag, ""))
    .concat(viewObject("dag", path.dag, path.root))
    .concat(path.fields.foldl(List(), (out, binding) => out.append(lookupNode(path.dag, binding._1, binding._2))
      .concat(if (binding._3 == "") List() else viewLiteral(binding._2, binding._3))))

  // Retry after consumption, with every original guard satisfied again, and
  // after the names point elsewhere and collection has swept the old commits.
  pure val retryIdentity = inputs.append(initialPublish("ack", "published", ""))
    .concat(receiptRead(receiptRefs(publishedRefs).concat(receiptNative(inspectReceiptGraph("ack", genuinePath)))))
    .concat(List(initialPublish("ack", "acknowledged", ""), inspectReceipt("ack")))
    .concat(receiptWrite(restoreRefs)).concat(receiptRead(receiptRefs(readyRefs)))
    .concat(List(initialPublish("ack", "acknowledged", ""), inspectReceipt("ack")))
    .concat(receiptWrite(List(changeRef("main", "sum:producer"), changeRef("plan", "sum:producer"),
      changeRef("returned", "sum:producer"))))
    .append(receiptStep(source("collect", List()), "collected", "", ""))
    .concat(receiptRead(List("sum:main", "plan:plan", "scale:worker:result").foldl(List(), (out, id) =>
      out.append(receiptStep(getCommit(id), "native_not_found", "", "")))
      .concat(receiptRefs(List(("main", "producer"), ("plan", "producer"), ("returned", "producer"), ("ack", "ack"))))))
    .concat(List(initialPublish("ack", "acknowledged", ""), inspectReceipt("ack")))

  // Keep the genuine result's parent and all three argument bindings. Only
  // its stored output changes. Demonstrate readiness by publishing it without a receipt.
  pure val alternateResult = snapshotAt("scale:worker:result", "original-result-head", "original-result-tree",
    "original-result-dag", "original-result-parent")
    .concat(List(lookupNode("original-result-dag", "implementation", "original-implementation"),
      lookupNode("original-result-dag", "input", "original-input"), lookupNode("original-result-dag", "factor", "original-factor")))
    .concat(putLiteral("i64", "99", "alternate-result-datum", "alternate-result-node"))
    .concat(putObject("dag", List("alternate-result-node", "implementation", "original-implementation",
      "input", "original-input", "factor", "original-factor"), "alternate-result-dag"))
    .concat(putObject("tree", List("requested-scale-v1", "alternate-result-dag"), "alternate-result-tree"))
    .concat(putObject("commit", List("alternate-result-tree", "original-result-parent"), "alternate-result"))
    .append(changeRef("returned", "alternate-result"))

  // The first character and final punctuation also exercise the ASCII name boundary.
  pure val maxReceiptRef = "1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa._-"
  pure val wrongKey = "publish-requested-scale: receipt does not match the requested publication"
  pure val keyFields = inputs.append(initialPublish("ack", "published", ""))
    .concat(receiptRead(List(readReceiptId)))
    .concat(receiptWrite(restoreRefs.concat(List(pin("other-plan", "plan:plan"), pin("other-returned", "scale:worker:result")))))
    .concat(receiptRead(receiptRefs(readyRefs.concat(List(("other-plan", "plan"), ("other-returned", "result"))))))
    .concat(List(
      publishWith("other-plan", "plan", "returned", "result", "ack", "rejected", wrongKey),
      publishWith("plan", "plan", "other-returned", "result", "ack", "rejected", wrongKey),
      receiptStep(source("inspect", List("returned")), "inspected", "original-result", "")
    )).concat(receiptWrite(alternateResult))
    .append(receiptStep(source("inspect", List("returned")), "inspected", "altered-result", ""))
    .concat(List(
      publishWith("plan", "plan", "returned", "native:alternate-result", "ack", "rejected", wrongKey),
      publishWith("plan", "plan", "returned", "native:alternate-result", "", "published", "")
    )).concat(receiptRead(receiptRefs(List(("main", "native:alternate-result"), ("plan", ""), ("returned", "")))))
    .concat(receiptWrite(List(changeRef("main", "sum:producer"), pin("returned", "scale:worker:result"))))
    .concat(List(
      receiptStep(source("request_scale", List("producer", "producer", "plan", "3", "next-plan")), "recorded", "next-plan", ""),
      receiptStep(source("inspect", List("plan")), "inspected", "recaptured-plan", ""),
      publishWith("plan", "next-plan", "returned", "result", "ack", "rejected", wrongKey),
      publishWith("plan", "next-plan", "returned", "result", maxReceiptRef, "published", "")
    )).concat(receiptRead(List(receiptStep(refRead(maxReceiptRef, "fresh-id"), "native_ok", "", ""))))
    .concat(List(publishWith("plan", "next-plan", "returned", "result", maxReceiptRef, "acknowledged", ""),
      inspectReceipt(maxReceiptRef), inspectReceipt("ack")))
    .concat(receiptRead(receiptRefs(publishedRefs.concat(List(("other-plan", "plan"), ("other-returned", "result"))))))

  pure val aliasedKey = "publish-requested-scale: receipt, plan, staging, and main refs must be distinct"
  pure val wrongRole = "publish-requested-scale: expected a parentless scale-publication-v1 receipt"
  pure val wrongRoot = "publish-requested-scale: publication receipt has the wrong DAG layout"
  pure val wrongRootInspect = "inspect: publication receipt has the wrong DAG layout"
  pure val forgeRoot = putObject("dag", List("key-plan-id", "plan_ref", "key-plan-ref", "plan_commit", "key-plan-id",
    "staging_ref", "key-staging-ref", "result_commit", "key-result-id"), "forged-dag")
    .concat(putObject("tree", List("scale-publication-v1", "forged-dag"), "forged-tree"))
    .concat(putObject("commit", List("forged-tree"), "forged-receipt"))
    .concat(List(pin("bad-receipt", "forged-receipt"), pin("not-receipt", "sum:producer")))
  pure val keyGuards = inputs.concat(List(
    initialPublish("main", "rejected", aliasedKey), initialPublish("plan", "rejected", aliasedKey),
    initialPublish("returned", "rejected", aliasedKey), initialPublish("ack", "published", "")
  )).concat(receiptRead(receiptNative(inspectReceiptGraph("ack", genuinePath)))).append(inspectReceipt("ack"))
    // Clone the successful receipt's nodes under another ref, changing only the root.
    .concat(receiptWrite(restoreRefs.concat(forgeRoot)))
    .concat(receiptRead(receiptRefs(readyRefs.append(("not-receipt", "producer")))
      .concat(receiptNative(inspectReceiptGraph("bad-receipt", malformedPath)))))
    .concat(List(initialPublish("not-receipt", "rejected", wrongRole), initialPublish("bad-receipt", "rejected", wrongRoot),
      receiptStep(source("inspect", List("bad-receipt")), "rejected", "", wrongRootInspect)))

  pure val movedStage = "publish-requested-scale: ('invalid_state', 0, 'ref target differs from the expected ID')"
  pure val mainAlreadyResult = "publish-requested-scale: main does not point to the expected commit"
  pure val guardRollback = inputs.concat(receiptWrite(List(changeRef("returned", "sum:producer"))))
    .append(initialPublish("ack", "rejected", movedStage))
    .concat(receiptRead(receiptRefs(List(("ack", ""), ("main", "prior"), ("plan", "plan"), ("returned", "producer")))))
    .concat(receiptWrite(List(changeRef("returned", "scale:worker:result"), changeRef("main", "scale:worker:result"))))
    .append(initialPublish("ack", "rejected", mainAlreadyResult))
    .concat(receiptRead(receiptRefs(List(("ack", ""), ("main", "result"), ("plan", "plan"), ("returned", "result")))))
    .concat(receiptWrite(List(changeRef("main", "sum:main"))))
    .append(initialPublish("ack", "published", ""))
    .concat(receiptRead(receiptRefs(publishedRefs).append(readReceiptId)))
    .append(inspectReceipt("ack"))

  pure val receiptCases = List(retryIdentity, keyFields, keyGuards, guardRollback)
  pure val receiptRequests = receiptCases.foldl(List(), (cases, steps) =>
    cases.append(steps.foldl(List(), (requests, step) => requests.append(step.request))))
  pure val receiptExpected = receiptCases.foldl(List(), (cases, steps) =>
    cases.append(steps.foldl(List(), (labels, step) => labels.append(step.label))))
}
