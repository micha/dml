module recorded_calls_reuse_histories {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  type ReuseStep = { request: Request, label: str, mark: str, expected: str }
  pure def stepFor(request: Request, label: str, mark: str, expected: str): ReuseStep =
    { request: request, label: label, mark: mark, expected: expected }
  pure def mapList(items: List[a], f: (a) => b): List[b] = items.foldl(List(), (out, elem) => out.append(f(elem)))
  pure def native(requests: List[Request]): List[ReuseStep] =
    mapList(requests, r => stepFor(r, "native_ok", "", ""))
  pure def writeNative(requests: List[Request]): List[ReuseStep] =
    native(openNative("write").concat(requests).concat(closeNative("txn_commit")))
  pure def readNative(steps: List[ReuseStep]): List[ReuseStep] =
    native(openNative("read")).concat(steps).concat(native(closeNative("txn_abort")))
  pure def refs(pins: List[(str, str)]): List[ReuseStep] = mapList(pins, p =>
    stepFor(refRead(p._1, "state-ref"), if (p._2 == "") "native_not_found" else "native_ok", "", p._2))
  pure def parent(view: str, index: str, id: str): Request =
    coreRequest("object_view_parent", List(view, index, id))
  pure def move(pin: str, id: str): Request = coreRequest("txn_ref_update", List("snapshot", pin, id))
  pure def commitPresent(id: str, present: bool): ReuseStep =
    stepFor(coreRequest("txn_get_object", List("snapshot", "commit", id, "retention-probe")),
      if (present) "native_ok" else "native_not_found", "", "")
  pure def sum(pin: str, a: str, b: str, mark: str): ReuseStep =
    stepFor(source("record_sum", List(pin, a, b)), "recorded", mark, "")
  pure def requestScale(pin: str, factor: str, implementation: List[str]): ReuseStep =
    stepFor(source("request_scale", List("producer", "producer", pin, factor).concat(implementation)), "recorded", pin, "")
  pure def inspect(pin: str, mark: str): ReuseStep =
    stepFor(source("inspect", if (pin == "") List() else List(pin)), "inspected", mark, "")
  pure def reject(op: str, args: List[str], diagnostic: str): ReuseStep =
    stepFor(source(op, args), "rejected", "", diagnostic)
  pure def publish(plan: str, resultPin: str, receipt: List[str]): ReuseStep =
    stepFor(source("publish_requested_scale", List(plan, plan, resultPin, "native:result").concat(receipt)),
      "published", "", "")
  pure def reuse(op: str, plan: str, resultPin: str, output: str, label: str): ReuseStep =
    stepFor(source(op, List(plan, if (plan == maxName) "long-plan" else plan, resultPin, "native:result", output)),
      label, "", "")
  pure val collect = stepFor(source("collect", List()), "collected", "", "")
  pure val maxName = "1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa._-"
  pure val maxI64 = "9223372036854775807"
  pure val producer = sum("producer", "7", "5", "producer")
  pure val overflowingProducer = sum("producer", maxI64, "0", "producer")
  pure val plan = requestScale("plan", "3", List())
  pure val sumPath = commitAt("sum:producer", ("sum-commit", "sum-tree", "sum-dag", ""))
  pure def planPath(planId: str, capturesMain: bool): List[Request] =
    commitAt(planId, ("plan-commit", "plan-tree", "plan-dag", "request-id"))
      .concat(if (capturesMain) List(parent("plan-commit", "1", "captured-main")) else List())
      .concat(commitAt("request-id", ("request-commit", "request-tree", "request-dag", "request-producer")))
      .concat(viewObject("dag", "request-dag", "request-root"))
      .append(lookupNode("request-dag", "implementation", "request-version"))
      .concat(viewLiteral("request-version", "request-version-value"))
      .append(lookupNode("request-dag", "factor", "request-factor"))
      .concat(viewLiteral("request-factor", "request-factor-value"))

  // Keep the selected request parent independent of the result's version, input, factor and root.
  pure def resultBody(implementation: str, input: str, factor: str, value: str): List[Request] =
    putLiteral("string", implementation, "version-datum", "version-node")
      .concat(putObject("node", List("subdag", input), "input-node"))
      .concat(putLiteral("i64", factor, "factor-datum", "factor-node"))
      .concat(putLiteral("i64", value, "result-datum", "result-node"))
      .concat(putObject("dag", List("result-node", "implementation", "version-node", "input", "input-node",
        "factor", "factor-node"), "result-dag"))
      .concat(putObject("tree", List("requested-scale-v1", "result-dag"), "result-tree"))
  pure def resultCommit(id: str, parents: List[str], pinName: str): List[Request] =
    putObject("commit", List("result-tree").concat(parents), id).append(pin(pinName, id))
  pure def buildResult(id: str, pinName: str, body: List[Request], request: str): List[Request] =
    body.concat(resultCommit(id, List(request), pinName))
  // Read the persisted candidate (not the scratch aliases used to encode it).
  pure def readResult(pinName: str, hasParent: bool): List[Request] = List(refRead(pinName, "candidate-id"))
    .concat(commitAt("candidate-id", ("candidate-commit", "candidate-tree", "candidate-dag",
      if (hasParent) "candidate-parent" else "")))
    .concat(viewObject("dag", "candidate-dag", "candidate-root"))
    .append(lookupNode("candidate-dag", "implementation", "candidate-version"))
    .concat(viewLiteral("candidate-version", "candidate-version-value"))
    .append(lookupNode("candidate-dag", "factor", "candidate-factor"))
    .concat(viewLiteral("candidate-factor", "candidate-factor-value"))
    .concat(viewSubdag("candidate-dag", "candidate-input", "candidate-producer-dag"))
    .concat(viewLiteral("candidate-root", "candidate-result-value"))

  pure val scale1 = "example.scale@1"
  pure val scale2 = "example.scale@2"
  pure val oldBody = resultBody(scale1, "sum-dag", "3", "36")
  pure val overflowBody = resultBody(scale1, "sum-dag", "3", "-98")
  pure val implementationCase = List(producer, sum("main", "12", "0", "prior"),
    requestScale("plan", "3", List("--implementation", scale2)))
    .concat(writeNative(sumPath.concat(planPath("plan:plan", true))
      .concat(buildResult("candidate", "candidate", oldBody, "request-id"))
      .concat(buildResult("matching", "matching", resultBody(scale2, "sum-dag", "3", "36"), "request-id"))))
    .concat(readNative(native(readResult("candidate", true).concat(readResult("matching", true)))))
    .append(inspect("matching", "matching-result"))
    .concat(List(
      reject("inspect", List("candidate"), "inspect: expected recorded implementation example.scale@2"),
      reject("export_scale", List("candidate", "native:candidate", "candidate.dmlb"),
        "export-scale: expected recorded implementation example.scale@2"),
      reject("publish_requested_scale", List("plan", "plan", "candidate", "native:candidate", "ack"),
        "publish-requested-scale: expected recorded implementation example.scale@2"),
      reject("stage_reused_scale", List("plan", "plan", "candidate", "native:candidate", "returned"),
        "stage-reused-scale: expected recorded implementation example.scale@2"),
      reject("publish_reused_scale", List("plan", "plan", "candidate", "native:candidate", "proof"),
        "publish-reused-scale: expected recorded implementation example.scale@2")))
    .concat(readNative(refs(List(("main", "prior"), ("plan", "plan"), ("candidate", "native:candidate"),
      ("ack", ""), ("returned", ""), ("proof", "")))))

  // Both reuse commands receive all five defects. For parentless/wrong-request, reuse
  // the exact valid result tree. The wrong producer stores the same root as the right one.
  pure val candidateDefects = List(
    (List("bad-plan", "native:bad-plan", "good", "native:result", "dest"),
      "stage-reused-scale: plan DAG does not match the request DAG",
      "publish-reused-scale: plan DAG does not match the request DAG"),
    (List("plan", "plan", "bad-shape", "native:bad-shape", "dest"),
      "stage-reused-scale: expected a recorded or requested scale commit with its required parents",
      "publish-reused-scale: expected a recorded or requested scale commit with its required parents"),
    (List("plan", "plan", "wrong-factor", "native:wrong-factor", "dest"),
      "stage-reused-scale: recorded factor does not match the request factor",
      "publish-reused-scale: recorded factor does not match the request factor"),
    (List("plan", "plan", "wrong-producer", "native:wrong-producer", "dest"),
      "stage-reused-scale: scale input DAG does not match the request's producer",
      "publish-reused-scale: scale input DAG does not match the request's producer"),
    (List("plan", "plan", "wrong-request", "native:wrong-request", "dest"),
      "stage-reused-scale: result does not retain the expected request commit",
      "publish-reused-scale: result does not retain the expected request commit"))
  pure val malformedCandidates = List(producer, sum("decoy", "9", "3", "decoy"), plan,
    requestScale("other-plan", "4", List()))
    .concat(writeNative(sumPath.concat(planPath("plan:plan", false))
      .concat(commitAt("sum:decoy", ("decoy-commit", "decoy-tree", "decoy-dag", "")))
      .concat(commitAt("plan:other-plan", ("other-plan-commit", "other-plan-tree", "other-plan-dag", "other-request")))
      .concat(putObject("commit", List("other-plan-commit", "request-id"), "bad-plan")).append(pin("bad-plan", "bad-plan"))
      .concat(buildResult("wrong-factor", "wrong-factor", resultBody(scale1, "sum-dag", "4", "36"), "request-id"))
      .concat(buildResult("wrong-producer", "wrong-producer", resultBody(scale1, "decoy-dag", "3", "36"), "request-id"))
      .concat(buildResult("result", "good", oldBody, "request-id"))
      .concat(resultCommit("bad-shape", List(), "bad-shape"))
      .concat(resultCommit("wrong-request", List("other-request"), "wrong-request"))))
    .concat(readNative(native(
      commitAt("bad-plan", ("bad-plan-commit", "bad-plan-tree", "bad-plan-dag", "bad-plan-request"))
      .concat(commitAt("other-request", ("other-request-commit", "other-request-tree", "other-request-dag", "other-producer")))
      .concat(viewObject("dag", "sum-dag", "sum-root")).concat(viewObject("dag", "decoy-dag", "decoy-root"))
      .concat(readResult("good", true)).concat(readResult("wrong-factor", true)).concat(readResult("wrong-producer", true))
      .append(refRead("bad-shape", "bad-shape-pin")).concat(viewObject("commit", "bad-shape-pin", "bad-shape-head"))
      .append(refRead("wrong-request", "wrong-request-pin"))
      .concat(viewObject("commit", "wrong-request-pin", "wrong-request-head"))
      .append(parent("wrong-request-head", "0", "wrong-request-parent")))))
    .append(inspect("good", "valid-result"))
    .concat(mapList(candidateDefects, c => reject("stage_reused_scale", c._1, c._2)))
    .concat(mapList(candidateDefects, c => reject("publish_reused_scale", c._1, c._3)))
    .append(reject("publish_requested_scale", List("plan", "plan", "wrong-request", "native:wrong-request"),
      "publish-requested-scale: result does not retain the expected request commit"))
    .concat(readNative(refs(List(("dest", ""), ("main", ""), ("plan", "plan"), ("good", "native:result")))))

  pure val stageCase = List(overflowingProducer, inspect("producer", "sum-report"), requestScale("first-plan", "3", List()))
    .concat(writeNative(sumPath.concat(planPath("plan:first-plan", false))
      .concat(buildResult("result", "history", overflowBody, "request-id")).append(pin("returned", "result"))))
    .append(publish("first-plan", "returned", List("ack")))
    .concat(readNative(native(List(refRead("ack", "receipt-id")))))
    .append(sum("unrelated", "2", "0", "prior"))
    .concat(writeNative(List(move("main", "sum:unrelated"))))
    .append(plan)
    .concat(readNative(native(
      commitAt("plan:plan", ("next-plan-commit", "next-plan-tree", "next-plan-dag", "next-plan-request"))
      .append(parent("next-plan-commit", "1", "next-main")).concat(readResult("history", true)))))
    .append(inspect("history", "stored-result"))
    .append(reuse("stage_reused_scale", "plan", "history", maxName, "reused"))
    .concat(readNative(refs(List(("plan", "plan"), ("main", "prior"), ("ack", "ref:receipt-id"),
      ("history", "native:result"), (maxName, "native:result")))))
    .append(inspect(maxName, "staged-result"))
    .concat(writeNative(List(drop("history", "result"))))
    .append(collect)
    .concat(readNative(refs(List(("history", ""), (maxName, "native:result"))).append(commitPresent("plan:first-plan", false))))
    .append(publish("plan", maxName, List()))
    .concat(readNative(refs(List(("main", "native:result"), ("ack", "ref:receipt-id"),
      ("history", ""), ("plan", ""), (maxName, "")))))
    .append(inspect("", "main-result"))

  // Read back the exact proof graph without using IDs supplied by the report.
  pure def readProofLayout(pinName: str, parents: int): List[Request] = List(refRead(pinName, "proof-id"))
    .concat(commitAt("proof-id", ("proof-commit", "proof-tree", "proof-dag", "proof-first")))
    .concat(if (parents == 2) List(parent("proof-commit", "1", "proof-second")) else List())
    .concat(viewObject("dag", "proof-dag", "proof-root"))
    .concat(List(lookupNode("proof-dag", "plan_ref", "proof-plan-node"), lookupNode("proof-dag", "result_ref", "proof-result-node")))
  pure def readProof(pinName: str): List[Request] = readProofLayout(pinName, 2)
    .concat(viewLiteral("proof-plan-node", "proof-plan-value"))
    .concat(viewLiteral("proof-result-node", "proof-result-value"))
  pure def readForgedProof(name: str, parents: int): List[Request] = readProofLayout(name, parents)
    .concat(if (name == "extra-binding") List(lookupNode("proof-dag", "extra", "extra-binding-node"))
      else if (Set("invalid-name", "main-alias", "wrong-type").contains(name)) viewLiteral("proof-result-node", "proof-result-value")
      else List())
  pure val staleResult = "publish-reused-scale: result pin does not point to the expected commit"
  pure val staleMain = "publish-reused-scale: main does not point to the expected commit"
  pure val directCase = List(overflowingProducer, inspect("producer", "sum-report"), sum("main", "2", "0", "prior"),
    stepFor(source("request_scale", List("producer", "producer", maxName, "3", "long-plan")), "recorded", "long-plan", ""))
    .concat(writeNative(sumPath.concat(planPath("plan:long-plan", true))
      .concat(buildResult("result", "history", overflowBody, "request-id"))
      .concat(buildResult("alternate", "staged", resultBody(scale1, "sum-dag", "3", "99"), "request-id"))))
    .concat(readNative(native(readResult("history", true).concat(readResult("staged", true)))))
    .append(inspect("history", "stored-result"))
    .append(reject("publish_reused_scale", List(maxName, "long-plan", "history", "native:alternate", "reuse"), staleResult))
    .concat(writeNative(List(move("main", "sum:producer"))))
    .append(reject("publish_reused_scale", List(maxName, "long-plan", "history", "native:result", "reuse"), staleMain))
    .concat(readNative(refs(List(("main", "producer"), (maxName, "long-plan"), ("reuse", "")))))
    .concat(writeNative(List(move("main", "sum:main"))))
    .concat(readNative(refs(List(("main", "prior"), ("history", "native:result"), ("staged", "native:alternate")))))
    .append(reuse("publish_reused_scale", maxName, "history", "reuse", "published"))
    .concat(readNative(refs(List(("main", "native:result"), (maxName, ""), ("history", "native:result"),
      ("staged", "native:alternate"))).concat(native(readProof("reuse")))))
    .concat(List(inspect("", "main-result"), inspect("reuse", "proof-report"), sum("replacement", "6", "0", "replacement")))
    // After moving/recreating the historical names, only the proof retains either parent.
    .concat(writeNative(List(move("main", "sum:replacement"), move("history", "sum:replacement"),
      pin(maxName, "sum:replacement"), drop("staged", "alternate"), drop("producer", "sum:producer"))))
    .append(collect)
    .concat(readNative(refs(List(("main", "replacement"), ("history", "replacement"), (maxName, "replacement"),
      ("producer", ""), ("staged", ""), ("reuse", "ref:proof-id")))
      .concat(mapList(List("plan:long-plan", "result", "sum:main", "request-id", "sum:producer"), id => commitPresent(id, true)))
      .append(commitPresent("alternate", false))))
    .append(inspect("reuse", "retained-proof"))

  pure val occupied = reject("publish_reused_scale", List("plan", "plan", "history", "native:result", "reuse"),
    "publish-reused-scale: ('invalid_state', -30799, 'ref already exists')")
  pure val occupiedRefs = List(("main", ""), ("plan", "plan"), ("history", "native:result"))
  pure val occupancyCase = List(producer, plan)
    .concat(writeNative(sumPath.concat(planPath("plan:plan", false))
      .concat(buildResult("result", "history", oldBody, "request-id")).append(pin("reuse", "sum:producer"))))
    .append(occupied).concat(readNative(refs(occupiedRefs.append(("reuse", "producer")))))
    .concat(writeNative(List(drop("reuse", "sum:producer"))))
    .append(reuse("publish_reused_scale", "plan", "history", "reuse", "published"))
    .concat(readNative(refs(List(("main", "native:result"), ("plan", ""), ("history", "native:result")))
      .concat(native(readProof("reuse")))))
    .append(inspect("reuse", "proof-report"))
    // Restore ALL guards: identical input against the same proof is not a receipt retry.
    .concat(writeNative(List(drop("main", "result"), pin("plan", "plan:plan"))))
    .concat(readNative(refs(occupiedRefs.append(("reuse", "ref:proof-id")))))
    .append(occupied).concat(readNative(refs(occupiedRefs.append(("reuse", "ref:proof-id")))))

  pure val wrongLayout = "inspect: reuse record has the wrong DAG layout"
  pure val badNames = "inspect: reuse record has invalid ref names"
  pure val proofDefects = List(
    ("reversed-parents", "proof-dag", List("result", "plan:plan"),
      "inspect: expected a scale-plan-v1 commit with a request and optional main parent"),
    ("missing-parent", "proof-dag", List("plan:plan"), "inspect: reuse record must have ordered plan and result parents"),
    ("wrong-request", "proof-dag", List("plan:plan", "other-result"), "inspect: result does not retain the expected request commit"),
    ("wrong-dag-root", "root-dag", List("plan:plan", "result"), wrongLayout),
    ("extra-binding", "extra-dag", List("plan:plan", "result"), wrongLayout),
    ("invalid-name", "invalid-name-dag", List("plan:plan", "result"), badNames),
    ("main-alias", "main-alias-dag", List("plan:plan", "result"), badNames),
    ("plan-alias", "plan-alias-dag", List("plan:plan", "result"), badNames),
    ("wrong-type", "wrong-type-dag", List("plan:plan", "result"), "inspect: recorded literal has the wrong datum kind"))
  pure def proofDag(id: str, root: str, resultNode: str, extra: List[str]): List[Request] =
    putObject("dag", List(root, "plan_ref", "proof-plan-node", "result_ref", resultNode).concat(extra), id)
  pure val malformedProofCase = List(producer, sum("main", "12", "0", "prior"), plan, requestScale("other-plan", "4", List()))
    .concat(writeNative(sumPath.concat(planPath("plan:plan", true))
      .concat(commitAt("plan:other-plan", ("other-plan-commit", "other-plan-tree", "other-plan-dag", "other-request")))
      .concat(buildResult("result", "returned", oldBody, "request-id"))
      .concat(buildResult("other-result", "other-result", resultBody(scale1, "sum-dag", "4", "48"), "other-request"))))
    .append(inspect("other-result", "other-report"))
    .append(reuse("publish_reused_scale", "plan", "returned", "reuse", "published"))
    .concat(readNative(native(readProof("reuse"))))
    .append(inspect("reuse", "proof-report"))
    .concat(writeNative(
      putLiteral("string", "invalid/name", "invalid-datum", "invalid-node")
      .concat(putLiteral("string", "main", "main-datum", "main-node"))
      .concat(putLiteral("i64", "7", "number-datum", "number-node"))
      .concat(proofDag("root-dag", "proof-result-node", "proof-result-node", List()))
      .concat(proofDag("extra-dag", "proof-plan-node", "proof-result-node", List("extra", "number-node")))
      .concat(List(("invalid-name-dag", "invalid-node"), ("main-alias-dag", "main-node"), ("plan-alias-dag", "proof-plan-node"),
        ("wrong-type-dag", "number-node")).foldl(List(), (out, p) => out.concat(proofDag(p._1, "proof-plan-node", p._2, List()))))
      .concat(proofDefects.foldl(List(), (out, p) => out
        .concat(putObject("tree", List("recorded-scale-reuse-v1", p._2), "forged-tree"))
        .concat(putObject("commit", List("forged-tree").concat(p._3), p._1)).append(pin(p._1, p._1))))))
    .concat(readNative(native(proofDefects.foldl(List(), (out, p) => out.concat(readForgedProof(p._1, p._3.length()))))))
    .concat(mapList(proofDefects, p => reject("inspect", List(p._1), p._4)))
    .append(inspect("reuse", "retained-proof"))

  pure val directReuseCases = List(implementationCase, malformedCandidates, stageCase, directCase, occupancyCase, malformedProofCase)
  pure val directReuseRequests = directReuseCases.foldl(List(), (out, steps) =>
    out.append(mapList(steps, s => s.request)))
  pure val directReuseExpected = directReuseCases.foldl(List(), (out, steps) =>
    out.append(mapList(steps, s => s.label)))
  var histories: List[List[Request]]
  action init = histories' = directReuseRequests
  action step = histories' = histories
}
