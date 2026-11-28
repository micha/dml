module recorded_calls_plan_histories {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  type PlanStep = { request: Request, label: str, mark: str, target: str }
  pure def planStep(req: Request, label: str, mark: str): PlanStep =
    { request: req, label: label, mark: mark, target: "" }
  pure def native(reqs: List[Request]): List[PlanStep] =
    reqs.foldl(List(), (out, r) => out.append(planStep(r, "native_ok", "")))
  pure def begin(role: str, mode: str): List[PlanStep] = native(openRepo(role, "existing", mode))
  pure def end(role: str, op: str): List[PlanStep] = native(closeRepo(role, op))
  pure def ref(ref: str, mark: str, target: str): PlanStep =
    { ...planStep(refRead(ref, mark), if (target == "") "native_not_found" else "native_ok", mark), target: target }
  pure def object(id: str, alias: str, present: bool): PlanStep =
    planStep(coreRequest("txn_get_object", List("snapshot", "commit", id, alias)),
      if (present) "native_ok" else "native_not_found", alias)
  pure def move(ref: str, id: str): Request = coreRequest("txn_ref_update", List("snapshot", ref, id))
  pure def parent(view: str, index: str, alias: str): Request =
    coreRequest("object_view_parent", List(view, index, alias))
  pure def recordSum(pin: str, a: str, b: str, mark: str): PlanStep =
    planStep(source("record_sum", List(pin, a, b)), "recorded", mark)
  pure def makePlan(pin: str, factor: str, mark: str, ok: bool): PlanStep =
    planStep(source("request_scale", List("producer", "producer", pin, factor)), if (ok) "recorded" else "rejected", mark)
  pure def publishPlan(pin: str, result: str, expected: str, label: str, mark: str): PlanStep =
    planStep(source("publish_requested_scale", List("plan", "plan", pin, result)
      .concat(if (expected == "") List() else List(expected))), label, mark)
  pure def removePlan(pin: str, id: str, label: str, mark: str): PlanStep =
    planStep(source("abandon_scale_request", List(pin, id)), label, mark)
  pure def readPlan(pin: str, mark: str): PlanStep = planStep(source("inspect", List(pin)), "inspected", mark)
  pure val sumReport = planStep(source("inspect", List("producer")), "inspected", "sum-report")
  pure val requestExport = planStep(source("export_request", List("plan", "plan", "request.dmlb")), "exported", "request-export")
  pure val requestImport = planStep(worker("stage_input", List("incoming", "request.dmlb")), "staged", "request-import")
  pure val requestWork = planStep(worker("work_scale", List("incoming", "plan", "result")), "recorded", "result")
  pure val resultTransfer = List(requestWork,
    planStep(worker("export_scale", List("result", "result", "result.dmlb")), "exported", "result-export"),
    planStep(source("stage_input", List("returned", "result.dmlb")), "staged", "result-stage"))
  pure val priorSetup = List(recordSum("producer", "7", "5", "producer"), sumReport,
    recordSum("main", "12", "0", "prior"))
  pure val collectSource = planStep(source("collect", List()), "collected", "collect")

  // Move main and drop the original producer pin before dispatch. Only the
  // local plan keeps the prior main alive; only the portable closure travels.
  pure val durableTipCase = priorSetup.concat(List(makePlan("plan", "-3", "plan", true), readPlan("plan", "plan-report")))
    .concat(begin("source", "write")).concat(native(
      commitAt("sum:producer", ("producer-commit", "producer-tree", "producer-dag", ""))
        .concat(List(drop("producer", "sum:producer"), move("main", "sum:producer")))))
    .concat(end("source", "txn_commit")).append(collectSource)
    .concat(begin("source", "read")).append(object("sum:main", "prior-through-plan", true))
    .concat(native(commitAt("plan:plan", ("local-plan", "local-plan-tree", "local-plan-dag", "local-request"))
      .append(parent("local-plan", "1", "local-prior")))).concat(end("source", "txn_abort"))
    .concat(List(requestExport, requestImport)).concat(begin("worker", "read"))
    .concat(List(ref("main", "worker-main", ""), object("plan:plan", "private-plan-in-worker", false),
      object("sum:main", "private-prior-in-worker", false), ref("incoming", "worker-incoming", "request-export")))
    .concat(end("worker", "txn_abort")).concat(resultTransfer)
    .append(planStep(worker("inspect", List("result")), "inspected", "worker-report"))
    .concat(List("request.dmlb", "result.dmlb").foldl(List(), (out, file) =>
      out.append(planStep(coreRequest("unlink_bundle", List(file)), "file_observed", ""))))
    .append(publishPlan("returned", "result", "", "rejected", "stale-main"))
    .concat(begin("source", "write")).concat(List(ref("main", "moved-main", "producer"),
      ref("plan", "retained-plan", "plan"), ref("returned", "retained-result", "result")))
    .concat(native(List(move("main", "sum:main")))).concat(end("source", "txn_commit"))
    .append(publishPlan("returned", "result", "", "published", "publish"))
    .append(planStep(source("collect", List()), "collected", "reclaim"))
    .concat(begin("source", "read")).concat(List(ref("main", "published-main", "result"),
      ref("plan", "consumed-plan", ""), ref("returned", "consumed-return", ""), ref("producer", "released-producer", ""),
      object("plan:plan", "swept-plan", false), object("sum:main", "swept-prior", false)))
    .concat(native(commitAt("published-main", ("result-commit", "result-tree", "result-dag", "result-request"))
      .concat(commitAt("result-request", ("request-commit", "request-tree", "request-dag", "request-producer")))
      .concat(viewSubdag("result-dag", "result-input", "result-source"))))
    .concat(end("source", "txn_abort")).append(planStep(source("inspect", List()), "inspected", "published-report"))

  // Reuse scratch aliases within a candidate; only its commit ID survives to the CLI steps.
  pure def buildCandidate(name: str, id: str, factor: str, input: str, result: str): List[Request] =
    putObject("node", List("subdag", input), "candidate-source")
      .concat(putLiteral("i64", factor, "factor-datum", "multiplier"))
      .concat(putLiteral("i64", result, "result-datum", "stored-value"))
      .concat(putObject("dag", List("stored-value", "implementation", "version", "input", "candidate-source",
        "factor", "multiplier"), "built-dag"))
      .concat(putObject("tree", List("requested-scale-v1", "built-dag"), "built-tree"))
      .concat(putObject("commit", List("built-tree", "request-parent"), id)).append(pin(name, id))
  pure def readCandidate(name: str): List[Request] = List(refRead(name, "candidate-pin"))
    .concat(commitAt("candidate-pin", ("candidate-commit", "candidate-tree", "candidate-dag", "candidate-request")))
    .concat(viewObject("dag", "candidate-dag", "candidate-root"))
    .concat(List(lookupNode("candidate-dag", "implementation", "candidate-version"),
      lookupNode("candidate-dag", "factor", "candidate-factor")))
    .concat(viewLiteral("candidate-factor", "observed-factor"))
    .concat(viewSubdag("candidate-dag", "candidate-input", "candidate-sum"))
    .concat(viewLiteral("candidate-root", "observed-value"))

  pure val candidateCase = List(recordSum("producer", "7", "-7", "producer"), sumReport,
    recordSum("decoy", "8", "-8", "decoy"), makePlan("plan", "3", "plan", true), readPlan("plan", "plan-report"))
    .concat(begin("source", "write")).concat(native(
      commitAt("plan:plan", ("local-plan", "local-plan-tree", "local-plan-dag", "request-parent"))
        .append(lookupNode("local-plan-dag", "implementation", "version"))
        .concat(commitAt("sum:producer", ("producer-commit", "producer-tree", "producer-dag", "")))
        .concat(commitAt("sum:decoy", ("decoy-commit", "decoy-tree", "decoy-dag", "")))
        .concat(viewObject("dag", "producer-dag", "producer-root"))
        .concat(viewObject("dag", "decoy-dag", "decoy-root"))
        .concat(buildCandidate("wrong-factor", "wrong-factor-id", "-2", "producer-dag", "0"))
        .concat(buildCandidate("wrong-input", "wrong-input-id", "3", "decoy-dag", "0"))
        .concat(buildCandidate("returned", "returned-id", "3", "producer-dag", "-98"))))
    .concat(end("source", "txn_commit")).concat(begin("source", "read"))
    .concat(native(readCandidate("wrong-factor").concat(readCandidate("wrong-input")).concat(readCandidate("returned"))))
    .concat(end("source", "txn_abort")).concat(List(
      publishPlan("wrong-factor", "native:wrong-factor-id", "", "rejected", "wrong-factor"),
      publishPlan("wrong-input", "native:wrong-input-id", "", "rejected", "wrong-input"),
      publishPlan("plan", "native:returned-id", "", "rejected", "alias-plan"),
      planStep(source("publish_scale", List("returned", "native:returned-id", "producer", "3", "-")), "rejected", "direct-publish"),
      publishPlan("returned", "native:returned-id", "", "published", "publish")))
    .concat(begin("source", "read")).append(ref("main", "published-main", "accepted-candidate"))
    .concat(end("source", "txn_abort")).append(planStep(source("inspect", List()), "inspected", "stored-report"))

  pure val guardCase = List(recordSum("producer", "2", "0", "producer"),
    makePlan("main", "3", "alias-main", false), makePlan("plan", "9223372036854775808", "factor-range", false),
    makePlan("plan", "4611686018427387904", "plan", true), makePlan("plan", "3", "occupied-plan", false),
    requestExport, planStep(source("export_request", List("producer", "plan", "wrong.dmlb")), "rejected", "wrong-export-pin"),
    planStep(source("stage_input", List("main", "request.dmlb")), "staged", "source-import"),
    makePlan("second-plan", "4611686018427387904", "request-is-main", false), requestImport,
    planStep(requestWork.request, "rejected", "worker-overflow"))
    .concat(begin("worker", "read")).concat(List(ref("result", "no-result", ""), ref("incoming", "kept-incoming", "request-export")))
    .concat(end("worker", "txn_abort")).concat(begin("source", "read"))
    .concat(List(ref("plan", "kept-plan", "plan"), ref("main", "kept-main", "request-export"),
      ref("producer", "kept-producer", "producer"), ref("second-plan", "no-second-plan", "")))
    .concat(end("source", "txn_abort"))

  // Bypass the CLI planner (which correctly disallows future versions), not
  // the import or worker. The bundle comes from an actual native export.
  pure val futureRequestCase = List(recordSum("producer", "7", "5", "producer"))
    .concat(begin("source", "write")).concat(native(
      putLiteral("string", "example.scale@3", "future-version-datum", "future-version")
        .concat(putLiteral("i64", "3", "future-factor-datum", "future-factor"))
        .concat(putObject("dag", List("future-version", "implementation", "future-version", "factor", "future-factor"), "future-built-dag"))
        .concat(putObject("tree", List("scale-request-v1", "future-built-dag"), "future-built-tree"))
        .concat(putObject("commit", List("future-built-tree", "sum:producer"), "future-request"))
        .append(pin("portable", "future-request"))
        .concat(List(coreRequest("txn_commit", List("snapshot")),
          coreRequest("repo_export_commit", List("source", "future-request", "future-bundle")),
          coreRequest("repo_close", List("source"))))))
    .concat(List(planStep(coreRequest("write_bundle", List("future-bundle", "future.dmlb")), "file_observed", "future-file"),
      planStep(worker("stage_input", List("incoming", "future.dmlb")), "staged", "future-import")))
    .concat(begin("worker", "read")).append(ref("incoming", "future-imported-pin", "future-request"))
    .concat(native(commitAt("future-imported-pin", ("future-commit", "future-tree", "future-dag", "future-producer"))
      .concat(viewObject("dag", "future-dag", "future-root"))
      .append(lookupNode("future-dag", "implementation", "imported-implementation"))
      .append(lookupNode("future-dag", "factor", "imported-factor"))
      .concat(viewLiteral("imported-implementation", "future-name"))
      .concat(viewLiteral("imported-factor", "future-number"))))
    .concat(end("worker", "txn_abort"))
    .append(planStep(worker("work_scale", List("incoming", "native:future-request", "result")), "rejected", "future-work"))
    .concat(begin("worker", "read")).concat(List(ref("result", "no-result", ""), ref("incoming", "kept-incoming", "future-request")))
    .concat(end("worker", "txn_abort"))

  pure val abandonStagedCase = priorSetup.slice(0, 1).append(priorSetup[2])
    .concat(List(makePlan("plan", "3", "plan", true), requestExport, requestImport)).concat(resultTransfer)
    .concat(begin("source", "write")).concat(native(List(move("main", "sum:producer"), pin("other-plan", "plan:plan"))))
    .concat(end("source", "txn_commit"))
    .append(planStep(worker("checkpoint_file", List("worker")), "file_observed", "worker-before"))
    .concat(List(removePlan("plan", "plan", "abandoned", "abandon"), removePlan("plan", "plan", "rejected", "missing-plan")))
    .concat(begin("source", "write")).concat(List(ref("plan", "abandoned-plan", ""), ref("other-plan", "alias-pin", "plan"),
      ref("main", "moved-main", "producer"), ref("producer", "producer-pin", "producer"), ref("returned", "result-pin", "result")))
    .concat(native(List(move("main", "sum:main")))).concat(end("source", "txn_commit"))
    .append(publishPlan("returned", "result", "ack", "rejected", "missing-plan-publish"))
    .concat(begin("source", "write")).concat(List(ref("ack", "no-ack", ""), ref("main", "restored-main", "prior")))
    .concat(native(List(move("main", "sum:producer"), drop("other-plan", "plan:plan"))))
    .concat(end("source", "txn_commit")).append(collectSource)
    .concat(begin("source", "read")).concat(List(ref("returned", "staged-result", "result"),
      object("scale:worker:result", "unswept-result", true), object("plan:plan", "swept-plan", false),
      object("sum:main", "swept-prior", false))).concat(end("source", "txn_abort"))
    .append(planStep(worker("compare_file", List("worker")), "file_observed", "worker-after"))

  // Exactly 128 ASCII bytes, including the permitted punctuation at the end.
  pure val longPlanPin = "1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa._-"
  pure val abandonExplicitCase = List(recordSum("producer", "7", "5", "producer"), sumReport,
    makePlan(longPlanPin, "3", "plan", true), readPlan(longPlanPin, "plan-report"))
    .concat(begin("source", "read")).append(ref(longPlanPin, "max-plan-id", "plan")).concat(native(
      commitAt("max-plan-id", ("local-plan", "local-plan-tree", "local-plan-dag", "local-request"))))
    .concat(end("source", "txn_abort")).append(removePlan(longPlanPin, longPlanPin, "abandoned", "abandon"))
    .concat(begin("source", "read")).concat(List(ref(longPlanPin, "abandoned-plan", ""), ref("main", "no-main", ""),
      ref("producer", "producer-before", "producer"), object("max-plan-id", "uncollected-plan", true),
      object("local-request", "uncollected-request", true))).concat(end("source", "txn_abort")).append(collectSource)
    .concat(begin("source", "read")).concat(List(ref("producer", "producer-after", "producer"),
      object("max-plan-id", "swept-plan", false), object("local-request", "swept-request", false)))
    .concat(end("source", "txn_abort"))

  pure val abandonGuardsCase = List(recordSum("producer", "7", "5", "producer"), sumReport,
    makePlan("plan", "3", "plan", true), readPlan("plan", "plan-report"), makePlan("other-plan", "4", "replacement", true))
    .concat(begin("source", "write")).append(ref("producer", "producer-pin", "producer")).concat(native(
      commitAt("plan:plan", ("local-plan", "local-plan-tree", "local-plan-dag", "local-request"))
        .concat(commitAt("plan:other-plan", ("replacement-plan", "replacement-tree", "replacement-dag", "replacement-request")))
        .concat(List(move("plan", "plan:other-plan"), pin("main", "plan:plan")))
        .concat(putObject("commit", List("local-plan", "replacement-request"), "malformed-plan"))
        .append(pin("malformed", "malformed-plan"))))
    .concat(end("source", "txn_commit")).concat(begin("source", "read"))
    .concat(native(commitAt("malformed-plan", ("malformed-commit", "malformed-tree", "malformed-dag", "malformed-request"))
      .concat(commitAt("malformed-request", ("wrong-request-commit", "wrong-request-tree", "wrong-request-dag", "same-producer")))))
    .concat(end("source", "txn_abort")).concat(List(
      removePlan("plan", "plan", "rejected", "replaced-pin"), removePlan("main", "plan", "rejected", "reserved-main"),
      removePlan("producer", "native:producer-pin", "rejected", "wrong-role"),
      removePlan("malformed", "native:malformed-plan", "rejected", "wrong-dag")))
    .concat(begin("source", "read")).concat(List(ref("plan", "replacement-pin", "replacement"), ref("main", "main-pin", "plan"),
      ref("producer", "producer-after", "producer"), ref("malformed", "malformed-pin", "malformed-plan")))
    .concat(end("source", "txn_abort"))

  pure val planCases = List(durableTipCase, candidateCase, guardCase, futureRequestCase,
    abandonStagedCase, abandonExplicitCase, abandonGuardsCase)
  pure val planRequests: List[List[Request]] = planCases.foldl(List(), (out, steps) =>
    out.append(steps.foldl(List(), (reqs, s) => reqs.append(s.request))))
  pure val planExpected: List[List[str]] = planCases.foldl(List(), (out, steps) =>
    out.append(steps.foldl(List(), (labels, s) => labels.append(s.label))))
}
