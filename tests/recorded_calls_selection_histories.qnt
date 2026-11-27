module recorded_calls_selection_histories {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  type Step = { request: Request, label: str, mark: str, expected: str }
  pure def stepFor(request: Request, label: str, mark: str, expected: str): Step =
    { request: request, label: label, mark: mark, expected: expected }
  pure def cli(role: str, op: str, args: List[str], label: str, mark: str, expected: str): Step =
    stepFor(coreRequest(op, List(role).concat(args)), label, mark, expected)
  pure def native(reqs: List[Request]): List[Step] = reqs.foldl(List(), (out, r) => out.append(stepFor(r, "native_ok", "", "")))
  pure def write(role: str, reqs: List[Request]): List[Step] =
    native(openRepo(role, "existing", "write").concat(reqs).concat(closeRepo(role, "txn_commit")))
  pure def read(role: str, steps: List[Step]): List[Step] = native(openRepo(role, "existing", "read"))
    .concat(steps).concat(native(closeRepo(role, "txn_abort")))
  pure def ref(name: str, alias: str, expected: str): Step =
    stepFor(refRead(name, alias), if (expected == "") "native_not_found" else "native_ok", "", expected)
  pure def absent(name: str): Step = ref(name, "absent-ref", "")
  pure def object(id: str, present: bool): Step = stepFor(
    coreRequest("txn_get_object", List("snapshot", "commit", id, "object-check")),
    if (present) "native_ok" else "native_not_found", "", "")
  pure def parent(view: str, index: str, alias: str): Request =
    coreRequest("object_view_parent", List(view, index, alias))
  pure def update(name: str, id: str): Request = coreRequest("txn_ref_update", List("snapshot", name, id))
  pure def inspect(ref: str, mark: str): Step = cli("source", "inspect", List(ref), "inspected", mark, "")
  pure def collect(role: str, count: str): Step = cli(role, "collect", List(), "collected", "", count)
  pure def sum(name: str, a: str, b: str, mark: str): Step = cli("source", "record_sum", List(name, a, b), "recorded", mark, "")
  pure def plan(name: str, factor: str, version: str): Step =
    cli("source", "request_scale", List("producer", "producer", name, factor, "--implementation", version), "recorded", name, "producer")
  pure def work(pin: str, id: str, label: str, expected: str): Step =
    cli("source", "work_scale_attempt", List("incoming", "native:request-id", pin, id), label,
      if (label == "recorded") pin else "", expected)
  pure def choose(op: str, pin: str, id: str, output: str, label: str, expected: str): Step =
    cli("source", op, List("plan", "plan", pin, id, output), label, if (label == "selected") output else "", expected)
  pure def publish(role: str, planRef: str, pin: str, id: str, proof: str, label: str, expected: str): Step =
    cli(role, "publish_selected_scale", List(planRef, planRef, pin, id, proof), label, "", expected)

  pure val occurrenceA = "a0000000-0000-4000-8000-000000000001"
  pure val occurrenceB = "b0000000-0000-4000-8000-000000000002"
  pure val uppercase = "A0000000-0000-4000-8000-000000000001"
  pure val v1 = "example.scale@1"
  pure val v2 = "example.scale@2"
  pure val occupied = "occupied"
  pure val wrongVersion = "wrong-version"
  pure val wrongResult = "wrong-result"
  pure val wrongAttempt = "wrong-attempt"
  pure val badAttemptParents = "bad-attempt-parents"
  pure val badUuid = "bad-uuid"

  // A marked graph read starts at its first native call; its scratch aliases
  // can be reused by the next read. No CLI output supplies a graph edge.
  pure def graphShape(id: str, p0: bool, p1: bool): List[Request] =
    snapshotAt(id, "head-view", "tree-view", "graph-dag", if (p0) "parent0" else "")
      .concat(if (p1) List(parent("head-view", "1", "parent1")) else List())
      .concat(viewObject("dag", "graph-dag", "graph-root"))
  pure def dagField(name: str, alias: str, datum: str): List[Request] =
    List(lookupNode("graph-dag", name, alias)).concat(viewLiteral(alias, datum))
  pure def checkGraph(id: str, mark: str, count: int, reads: List[Request]): List[Step] = {
    val requests = graphShape(id, count > 0, count > 1).concat(reads)
    List(stepFor(requests[0], "native_ok", mark, "")).concat(native(requests.slice(1, requests.length())))
  }
  pure def single(id: str, mark: str, name: str, count: int): List[Step] =
    checkGraph(id, mark, count, dagField(name, "field-node", "field-value"))
  pure def proof(pin: str, mark: str): List[Step] = native(List(refRead(pin, "proof-id")))
    .concat(checkGraph("proof-id", mark, 2, dagField("plan_ref", "plan-node", "plan-name")
      .concat(dagField("selection_ref", "selection-node", "selection-name"))))

  // Choose against stale main; transfer only the choice's reachable history.
  // In the target the proof uses the historical result name as its own pin.
  pure val transfer = List(sum("producer", "7", "5", "producer"), sum("main", "12", "0", "prior"), plan("plan", "3", v1))
    .concat(write("source", viewObject("commit", "plan:plan", "old-plan-view").concat(List(
      parent("old-plan-view", "0", "request-id"), parent("old-plan-view", "1", "prior-id"),
      pin("incoming", "request-id"), update("main", "sum:producer")))))
    .append(cli("source", "work_scale", List("incoming", "native:request-id", "returned"), "recorded", "result", "request-id"))
    .concat(read("source", List(ref("returned", "result-id", "result"))))
    .append(choose("select_scale_result", "returned", "native:result-id", "choice", "selected", ""))
    .concat(read("source", List(ref("choice", "choice-id", "choice"), ref("main", "stale-main", "producer"),
      ref("plan", "kept-old-plan", "plan"), ref("returned", "kept-result", "result"))
      .concat(single("choice-id", "choice-graph", "result_ref", 2))))
    .concat(write("source", List(drop("plan", "plan:plan"), drop("returned", "result-id"),
      drop("producer", "sum:producer"), drop("incoming", "request-id"), drop("main", "sum:producer"))))
    .append(collect("source", "positive"))
    .concat(native(openNative("read"))).concat(List(object("plan:plan", false), object("sum:main", false),
      object("result-id", true), object("request-id", true)))
    .concat(native(List(coreRequest("txn_abort", List("snapshot")),
      coreRequest("repo_export_commit", List("source", "choice-id", "choice-bundle")), coreRequest("repo_close", List("source")))))
    .append(stepFor(coreRequest("write_bundle", List("choice-bundle", "choice.dmlb")), "file_observed", "", ""))
    .append(cli("worker", "stage_input", List("imported", "choice.dmlb"), "staged", "", "choice"))
    .concat(read("worker", List(ref("imported", "imported-id", "choice"), absent("plan"), absent("returned"), absent("main"),
      object("plan:plan", false), object("sum:main", false))))
    .append(cli("worker", "inspect", List("imported"), "inspected", "imported-report", ""))
    .concat(write("worker", List(pin("producer", "sum:producer"))))
    .append(cli("worker", "request_scale", List("producer", "producer", "new-plan", "3"), "recorded", "new-plan", "producer"))
    .append(publish("worker", "new-plan", "imported", "choice", "returned", "published", "result"))
    .concat(read("worker", List(ref("main", "published-main", "result"), absent("new-plan"), ref("imported", "kept-import", "choice"))
      .concat(proof("returned", "proof-graph"))))
    .concat(write("worker", List(drop("main", "result-id"), pin("new-plan", "plan:new-plan"))))
    .append(publish("worker", "new-plan", "imported", "choice", "returned", "rejected", occupied))
    .concat(read("worker", List(absent("main"), ref("new-plan", "restored-plan", "new-plan"), ref("returned", "original-proof", "proof-id"))))
    .concat(write("worker", List(drop("new-plan", "plan:new-plan"), drop("imported", "choice-id"), drop("producer", "sum:producer"))))
    .append(collect("worker", "zero"))
    .concat(read("worker", List(ref("returned", "proof-only", "proof-id"), absent("main"), absent("new-plan"),
      absent("imported"), absent("producer"), object("plan:new-plan", true), object("choice-id", true),
      object("request-id", true), object("result-id", true))))
    .append(cli("worker", "inspect", List("returned"), "inspected", "transfer-proof-report", ""))

  pure def singleDag(name: str, value: str): List[Request] = putLiteral("string", value, "name-datum", "name-node")
    .concat(putObject("dag", List("name-node", name, "name-node"), "built-dag"))
  pure def persist(pinName: str, role: str, parents: List[str], id: str): List[Request] =
    putObject("tree", List(role, "built-dag"), "built-tree")
      .concat(putObject("commit", List("built-tree").concat(parents), id)).append(pin(pinName, id))
  pure def resultBody(pinName: str, id: str, request: str, version: str, factor: str): List[Request] =
    putLiteral("string", version, "version-data", "version-node")
      .concat(putLiteral("i64", factor, "factor-data", "factor-node"))
      .concat(putObject("dag", List("output", "implementation", "version-node", "input", "result-input",
        "factor", "factor-node"), "built-dag"))
      .concat(persist(pinName, "requested-scale-v1", List(request), id))
  pure def readResult(id: str, mark: str): List[Step] = checkGraph(id, mark, 1,
    dagField("implementation", "implementation-node", "implementation-value")
      .concat(dagField("factor", "factor-node", "factor-value"))
      .concat(viewSubdag("graph-dag", "input-node", "input-dag"))
      .concat(viewLiteral("graph-root", "output-value")))
  pure val versionFixture = List(sum("producer", "7", "5", "producer"), plan("plan", "3", v2), plan("other-plan", "4", v2))
    .concat(write("source", viewObject("commit", "plan:plan", "plan-view")
      .concat(viewObject("commit", "plan:other-plan", "other-plan-view"))
      .concat(List(parent("plan-view", "0", "request-id"), parent("other-plan-view", "0", "other-request-id")))
      .concat(snapshotAt("sum:producer", "sum-view", "sum-tree", "sum-dag", ""))
      .concat(putObject("node", List("subdag", "sum-dag"), "result-input"))
      .concat(putLiteral("i64", "36", "output-datum", "output"))
      .concat(resultBody("good-result", "good-result-id", "request-id", v2, "3"))
      .concat(resultBody("legacy-body", "legacy-result-id", "request-id", v1, "3"))
      .concat(resultBody("foreign-result", "foreign-result-id", "other-request-id", v2, "4"))))
    .concat(read("source", List(ref("good-result", "good-result-pin", "good-result-id"),
      ref("legacy-body", "legacy-result-pin", "legacy-result-id"), ref("foreign-result", "foreign-result-pin", "foreign-result-id"))
      .concat(readResult("good-result-id", "good-result-graph"))
      .concat(readResult("legacy-result-id", "legacy-result-graph")).concat(readResult("foreign-result-id", "foreign-result-graph"))))

  type Shape = { ref: str, id: str, cliId: str, parents: List[str], value: str, variant: str, error: str }
  pure def shape(ref: str, id: str, cliId: str, parents: List[str], value: str, layout: str, error: str): Shape =
    { ref: ref, id: id, cliId: cliId, parents: parents, value: value, variant: layout, error: error }
  pure def resultShape(ref: str, cliId: str, result: str, error: str): Shape =
    shape(ref, ref, cliId, List("request-id", result), "history", "normal", error)
  pure val resultShapes = List(resultShape("wrong-version", "native:wrong-version", "legacy-result-id", wrongVersion),
    resultShape("wrong-parent", "native:wrong-parent", "foreign-result-id", wrongResult),
    shape("reversed", "reversed", "native:reversed", List("good-result-id", "request-id"), "history", "normal", "reversed"),
    shape("missing-parent", "missing-parent", "native:missing-parent", List("request-id"), "history", "normal", "missing-parent"),
    shape("bad-root", "bad-root", "native:bad-root", List("request-id", "good-result-id"), "history", "root", "bad-root"),
    shape("bad-name", "bad-name", "native:bad-name", List("request-id", "good-result-id"), "main", "normal", "bad-name"),
    shape("bad-type", "bad-type", "native:bad-type", List("request-id", "good-result-id"), "7", "type", "bad-type"))
  pure def resultDag(s: Shape): List[Request] =
    if (s.variant == "normal") singleDag("result_ref", s.value)
    else putLiteral("i64", "7", "number-datum", "number")
      .concat(if (s.variant == "root") putLiteral("string", s.value, "name-datum", "name-node") else List())
      .concat(putObject("dag", List("number", "result_ref", if (s.variant == "root") "name-node" else "number"), "built-dag"))
  pure def rejectSelection(s: Shape): List[Step] = List(cli("source", "inspect", List(s.ref), "rejected", "", s.error),
    publish("source", "plan", s.ref, s.cliId, "reuse", "rejected", s.error))
  pure val resultValidation = versionFixture.concat(write("source", resultShapes.foldl(List(), (out, s) =>
    out.concat(resultDag(s)).concat(persist(s.ref, "scale-result-selection-v1", s.parents, s.id)))))
    .concat(read("source", resultShapes.foldl(List(), (out, s) =>
      out.append(ref(s.ref, "forgery-pin", s.id)).concat(single(s.id, s.id, "result_ref", s.parents.length())))))
    .append(choose("select_scale_result", "legacy-body", "native:legacy-result-id", "choice", "rejected", wrongVersion))
    .concat(resultShapes.foldl(List(), (out, s) => out.concat(rejectSelection(s))))
    .concat(read("source", List(absent("main"), absent("choice"), absent("reuse"), ref("plan", "valid-plan", "plan"))))
    .append(choose("select_scale_result", "good-result", "native:good-result-id", "choice", "selected", ""))
    .append(inspect("choice", "valid-result-choice"))
    .append(publish("source", "plan", "choice", "choice", "reuse", "published", "good-result-id"))

  pure def workerSetup(factor: str): List[Step] = List(sum("producer", "7", "5", "producer"), plan("plan", factor, v1))
    .concat(write("source", viewObject("commit", "plan:plan", "plan-view")
      .concat(List(parent("plan-view", "0", "request-id"), pin("incoming", "request-id")))))
  pure val attempts = workerSetup("3").append(work("producer", occurrenceA, "rejected", occupied))
    .append(cli("source", "work_scale", List("incoming", "native:request-id", "legacy-result"), "recorded", "result", "request-id"))
    .concat(List(work("first", occurrenceA, "recorded", ""), work("second", occurrenceB, "recorded", ""), work("duplicate", occurrenceA, "recorded", "")))
    .concat(read("source", List(ref("first", "first-id", "first"), ref("second", "second-id", "second"),
      ref("duplicate", "duplicate-id", "first"), ref("legacy-result", "result-id", "result"), ref("producer", "kept-producer", "producer"))
      .concat(single("first-id", "first-graph", "attempt_id", 2)).concat(single("second-id", "second-graph", "attempt_id", 2))))
    .append(choose("select_scale_attempt", "first", "first", "chosen", "selected", ""))
    .concat(read("source", List(ref("chosen", "chosen-id", "chosen"), ref("plan", "kept-plan", "plan"), absent("main"))
      .concat(single("chosen-id", "chosen-graph", "attempt_ref", 2))))
    .concat(write("source", List(drop("first", "first-id"), drop("second", "second-id"), drop("duplicate", "duplicate-id"),
      drop("legacy-result", "result-id"), drop("incoming", "request-id"))))
    .append(collect("source", "positive"))
    .concat(read("source", List(object("second-id", false), object("first-id", true), object("result-id", true), object("request-id", true))))
    .append(publish("source", "plan", "chosen", "chosen", "reuse", "published", "result"))
    .append(collect("source", "zero"))
    .concat(read("source", List(ref("main", "published-main", "result"), absent("plan")).concat(proof("reuse", "proof-graph"))))
    .concat(write("source", List(drop("main", "result-id"), drop("chosen", "chosen-id"), drop("producer", "sum:producer"))))
    .append(collect("source", "zero"))
    .concat(read("source", List(absent("main"), absent("chosen"), absent("producer"), absent("plan"), ref("reuse", "proof-only", "proof-id"))))
    .append(inspect("reuse", "attempt-proof-report"))

  pure def badAttempt(name: str, cliId: str, request: str, result: str, uuid: str, error: str): Shape =
    shape(name, name, cliId, if (result == "") List(request) else List(request, result), uuid, "", error)
  pure val badAttempts = List(badAttempt("wrong-version", "native:wrong-version", "request-id", "legacy-result-id", occurrenceA, wrongVersion),
    badAttempt("wrong-result", "native:wrong-result", "request-id", "foreign-result-id", occurrenceA, wrongResult),
    badAttempt("wrong-request", "native:wrong-request", "other-request-id", "foreign-result-id", occurrenceA, wrongAttempt),
    badAttempt("wrong-count", "native:wrong-count", "request-id", "", occurrenceA, badAttemptParents),
    badAttempt("wrong-id", "native:wrong-id", "request-id", "good-result-id", uppercase, badUuid))
  pure def attemptChoice(name: str, cliId: str, attempt: str, value: str, error: str): Shape =
    shape(name, name, cliId, List("request-id", attempt), value, "normal", error)
  pure val attemptShapes = List(attemptChoice("select-version", "native:select-version", "wrong-version", "historical", wrongVersion),
    attemptChoice("select-result", "native:select-result", "wrong-result", "historical", wrongResult),
    attemptChoice("select-request", "native:select-request", "wrong-request", "historical", wrongAttempt),
    attemptChoice("select-count", "native:select-count", "wrong-count", "historical", badAttemptParents),
    attemptChoice("select-id", "native:select-id", "wrong-id", "historical", badUuid),
    attemptChoice("bad-history", "native:bad-history", "good-attempt-id", "main", "bad-history"),
    attemptChoice("not-attempt", "native:not-attempt", "good-result-id", "historical", badAttemptParents))
  pure val attemptValidation = versionFixture.concat(write("source",
    badAttempts.foldl(List(), (out, a) => out.concat(singleDag("attempt_id", a.value))
      .concat(persist(a.ref, "scale-attempt-v1", a.parents, a.id)))
      .concat(singleDag("attempt_id", occurrenceA))
      .concat(persist("good-attempt", "scale-attempt-v1", List("request-id", "good-result-id"), "good-attempt-id"))
      .concat(attemptShapes.foldl(List(), (out, s) => out.concat(singleDag("attempt_ref", s.value))
        .concat(persist(s.ref, "scale-attempt-selection-v1", s.parents, s.id))))))
    .concat(read("source", badAttempts.foldl(List(), (out, a) =>
      out.append(ref(a.ref, "forgery-pin", a.id)).concat(single(a.id, a.id, "attempt_id", a.parents.length())))
      .concat(attemptShapes.foldl(List(), (out, s) =>
        out.append(ref(s.ref, "forgery-pin", s.id)).concat(single(s.id, s.id, "attempt_ref", 2))))))
    .concat(badAttempts.foldl(List(), (out, a) => out.append(choose("select_scale_attempt", a.ref, a.cliId, "new", "rejected", a.error))))
    .concat(attemptShapes.foldl(List(), (out, s) => out.concat(rejectSelection(s))))
    .concat(read("source", List(absent("main"), absent("new"), absent("reuse"), ref("plan", "valid-plan", "plan"))))
    .append(choose("select_scale_attempt", "good-attempt", "native:good-attempt-id", "new", "selected", ""))
    .append(inspect("new", "valid-attempt-choice"))
    .append(publish("source", "plan", "new", "new", "reuse", "published", "good-result-id"))

  pure val guard = workerSetup("4611686018427387904")
    .concat(read("source", List(ref("producer", "producer-id", "producer"))))
    .concat(List(work("attempt", uppercase, "rejected", badUuid), work("attempt", "a0000000-0000-4000-7000-000000000001", "rejected", badUuid),
      work("incoming", occurrenceA, "rejected", "alias"), work("main", occurrenceA, "rejected", "alias"),
      work("-invalid", occurrenceA, "rejected", "name"),
      cli("source", "work_scale_attempt", List("incoming", "native:producer-id", "attempt", occurrenceA), "rejected", "", "stale"),
      work("attempt", occurrenceA, "rejected", "overflow")))
    .concat(read("source", List(ref("incoming", "kept-incoming", "request-id"), ref("plan", "kept-plan", "plan"),
      ref("producer", "kept-producer", "producer"), absent("attempt"), absent("main"))))

  pure val cases = List(transfer, resultValidation, attempts, attemptValidation, guard)
  pure val expected = cases.foldl(List(), (rows, c) => rows.append(c.foldl(List(), (out, s) => out.append(s.label))))
  var histories: List[List[Request]]
  action init = histories' = cases.foldl(List(), (rows, c) => rows.append(c.foldl(List(), (out, s) => out.append(s.request))))
  action step = histories' = histories
}
