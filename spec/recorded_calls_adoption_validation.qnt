module recorded_calls_adoption_validation {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_adoption_fixture as f from "./recorded_calls_adoption_fixture"
  import recorded_calls_adoption_checks as checks from "./recorded_calls_adoption_checks"
  import recorded_calls_rules as r from "./recorded_calls_rules"

  type Step = { request: Request, label: str, expected: str, graph: str }
  pure def stepFor(req: Request, label: str, expected: str): Step =
    { request: req, label: label, expected: expected, graph: "" }
  pure def native(reqs: List[Request]): List[Step] =
    reqs.foldl(List(), (out, req) => out.append(stepFor(req, "native_ok", "")))
  pure def write(reqs: List[Request]): List[Step] =
    native(openNative("write").concat(reqs).concat(closeNative("txn_commit")))
  pure def read(steps: List[Step]): List[Step] =
    native(openNative("read")).concat(steps).concat(native(closeNative("txn_abort")))
  pure def ref(name: str, alias: str, id: str): Step = stepFor(refRead(name, alias), "native_ok", id)
  pure def absent(name: str): Step = stepFor(refRead(name, "missing-pin"), "native_not_found", "")
  pure def reject(req: Request, cause: str): Step = stepFor(req, "rejected", cause)
  pure def publish(refName: str, selection: str): Request =
    source("publish_selected_scale", List("plan", "plan", refName, selection, "reuse"))

  pure val adoption = "scale-attempt-adoption-v1"
  pure val attempt = "scale-attempt-v1"
  pure val initial = "scale-attempt-selection-v1"
  pure val legacy = "scale-result-selection-v1"
  pure val result = "requested-scale-v1"
  pure val v1 = "example.scale@1"
  pure val v2 = "example.scale@2"
  pure val wrongRequest = "adopt-scale-attempt: attempt does not retain the expected request commit"

  type Shape = { name: str, role: str, parents: List[str], field: str, text: str }
  pure def link(name: str, parents: List[str], text: str): Shape =
    { name: name, role: adoption, parents: parents, field: "attempt_ref", text: text }
  pure val legacyChoice: Shape = { name: "legacy", role: legacy, parents: List("request-id", "result-id"),
    field: "result_ref", text: "result" }
  pure val buried = List(link("duplicate", List("chosen", "first"), "historical"),
    link("wrong-request", List("chosen", "other"), "historical"), link("bad-name", List("chosen", "second"), "main"))
  pure val validLinks = List(link("valid-middle", List("chosen", "second"), "historical"),
    link("valid-tip", List("valid-middle", "first"), "historical"))

  type Malformed = { tip: Shape, operand: str, candidate: str, errors: (str, str, str) }
  pure def malformed(name: str, operand: str, parents: List[str], candidate: str, errors: (str, str, str)): Malformed =
    { tip: link(name, parents, "historical"), operand: operand, candidate: candidate, errors: errors }
  // For a tip selecting second, propose first: a shallow reader must not pass
  // the duplicate-middle case by rejecting an ordinary same-attempt adoption.
  pure val invalid = List(
    malformed("single-parent", "native:single-parent", List("chosen"), "second",
      ("adopt-scale-attempt: expected a scale-attempt-adoption-v1 commit with ordered selection and attempt parents",
       "inspect: expected a scale-attempt-adoption-v1 commit with ordered selection and attempt parents",
       "publish-selected-scale: expected a scale-attempt-adoption-v1 commit with ordered selection and attempt parents")),
    malformed("swapped-parents", "native:swapped-parents", List("second", "chosen"), "second",
      ("adopt-scale-attempt: expected a scale-attempt-v1 commit with ordered request and result parents",
       "inspect: expected a scale-attempt-v1 commit with ordered request and result parents",
       "publish-selected-scale: expected a scale-attempt-v1 commit with ordered request and result parents")),
    malformed("legacy-root", "native:legacy-root", List("legacy", "second"), "first",
      ("adopt-scale-attempt: adoption history must start with an attempt selection",
       "inspect: adoption history must start with an attempt selection",
       "publish-selected-scale: adoption history must start with an attempt selection")),
    malformed("duplicate-middle", "native:duplicate-middle", List("duplicate", "second"), "first",
      ("adopt-scale-attempt: adoption must change the selected attempt commit",
       "inspect: adoption must change the selected attempt commit",
       "publish-selected-scale: adoption must change the selected attempt commit")),
    malformed("other-middle", "native:other-middle", List("wrong-request", "second"), "first",
      (wrongRequest, "inspect: attempt does not retain the expected request commit",
       "publish-selected-scale: attempt does not retain the expected request commit")),
    malformed("bad-name-middle", "native:bad-name-middle", List("bad-name", "first"), "second",
      ("adopt-scale-attempt: attempt adoption has an invalid attempt ref name",
       "inspect: attempt adoption has an invalid attempt ref name",
       "publish-selected-scale: attempt adoption has an invalid attempt ref name")))
  pure val nativeOperands = invalid.foldl(Map("native:request-id" -> "request-id", "native:other-request-id" -> "other-request-id",
    "native:legacy" -> "legacy", "native:valid-tip" -> "valid-tip"), (out, s) => out.put(s.operand, s.tip.name))
  pure val forged = List(legacyChoice).concat(buried).concat(validLinks)
    .concat(invalid.foldl(List(), (out, s) => out.append(s.tip)))

  pure def persist(s: Shape): List[Request] = putLiteral("string", s.text, "name-datum", "name-node")
    .concat(putObject("dag", List("name-node", s.field, "name-node"), "built-dag"))
    .concat(putObject("tree", List(s.role, "built-dag"), "built-tree"))
    .concat(putObject("commit", List("built-tree").concat(s.parents), s.name)).append(pin(s.name, s.name))
  pure def shapeReads(id: str, parents: int): List[Request] =
    snapshotAt(id, "commit-view", "tree-view", "dag-id", if (parents > 0) "parent0" else "")
      .concat(if (parents > 1) List(f::parent("commit-view", "1", "parent1")) else List())
      .concat(viewObject("dag", "dag-id", "dag-view"))
  pure def fieldReads(name: str): List[Request] =
    List(lookupNode("dag-id", name, "field-node")).concat(viewLiteral("field-node", "field-datum"))
  pure def graphReads(id: str, reqs: List[Request]): List[Step] =
    List({ ...stepFor(reqs[0], "native_ok", ""), graph: id }).concat(native(reqs.slice(1, reqs.length())))
  pure def single(s: Shape): List[Step] =
    graphReads(s.name, shapeReads(s.name, s.parents.length()).concat(fieldReads(s.field)))
  pure def resultReads(id: str): List[Step] = graphReads(id,
    shapeReads(id, 1).concat(fieldReads("implementation")).concat(viewLiteral("dag-view", "result-datum")))
  pure def attemptShape(name: str, request: str, resultId: str, uuid: str): Shape =
    { name: name, role: attempt, parents: List(request, resultId), field: "attempt_id", text: uuid }
  pure val original = List(attemptShape("first", "request-id", "result-id", f::firstUuid),
    attemptShape("second", "request-id", "result-id", f::secondUuid),
    attemptShape("other", "other-request-id", "other-result-id", f::secondUuid),
    { name: "chosen", role: initial, parents: List("request-id", "first"), field: "attempt_ref", text: "first" })
  pure val validAdopted = link("next", List("valid-tip", "second"), "second")
  pure val verifiedShapes = original.concat(forged).append(validAdopted)

  pure val otherSetup = List(stepFor(source("request_scale", List("producer", "producer", "other-plan", "3", "--implementation", v2)),
    "recorded", "producer"))
    .concat(write(viewObject("commit", "plan:other-plan", "other-plan-view")
      .concat(List(f::parent("other-plan-view", "0", "other-request-id"), pin("other-request", "other-request-id")))))
    .append(stepFor(source("work_scale_attempt", List("other-request", "native:other-request-id", "other", f::secondUuid)),
      "recorded", "other-request-id"))
  pure val basisPins = List(ref("producer", "producer-pin", "producer"), ref("plan", "plan-pin", "plan"),
    ref("incoming", "incoming-pin", "request-id"), ref("first", "first", "first"), ref("chosen", "chosen", "chosen"),
    ref("second", "second", "second"), ref("other-plan", "other-plan-pin", "other-plan"),
    ref("other-request", "other-request-pin", "other-request-id"), ref("other", "other", "other"))
  pure val ready = basisPins.concat(List(absent("main"), absent("next"), absent("reuse")))
  pure val construction = read(basisPins.concat(native(viewObject("commit", "first", "first-attempt")
    .append(f::parent("first-attempt", "1", "result-id"))
    .concat(viewObject("commit", "other", "other-attempt")).append(f::parent("other-attempt", "1", "other-result-id")))))
    .concat(write(forged.foldl(List(), (out, s) => out.concat(persist(s)))))
    .concat(read(ready.concat(resultReads("result-id")).concat(resultReads("other-result-id"))
      .concat(original.foldl(List(), (out, s) => out.concat(single(s))))
      .concat(forged.foldl(List(), (out, s) => out.append(ref(s.name, "forged-pin", s.name)).concat(single(s))))))

  pure val rejections = List(
    reject(f::adopt("legacy", "native:legacy", "second", "second", "next"), "adopt-scale-attempt: adoption basis must be an attempt selection"),
    reject(f::adopt("chosen", "chosen", "other", "other", "next"), wrongRequest))
    .concat(invalid.foldl(List(), (out, s) => {
      val name = s.tip.name
      out.concat(List(reject(f::adopt(name, s.operand, s.candidate, s.candidate, "next"), s.errors._1),
        reject(source("inspect", List(name)), s.errors._2), reject(publish(name, s.operand), s.errors._3)))
    }))
  pure val counterparts = List(stepFor(source("inspect", List("valid-tip")), "inspected", ""),
    stepFor(f::adopt("valid-tip", "native:valid-tip", "second", "second", "next"), "adopted", ""))
    .concat(read(List(ref("next", "next", "next")).concat(single(validAdopted))))
    .append(stepFor(publish("valid-tip", "native:valid-tip"), "published", "result-id"))
    .concat(read(List(ref("main", "main-result", "result-id"), absent("plan"), ref("valid-tip", "kept-selection", "valid-tip"))))

  pure val malformedChain = otherSetup.concat(construction).concat(rejections)
    .concat(read(ready.concat(invalid.foldl(List(), (out, s) => out.append(ref(s.tip.name, "kept-forgery", s.tip.name))))))
    .concat(counterparts)
  pure val cases: List[List[Request]] = List(malformedChain.foldl(f::setup, (out, s) => out.append(s.request)))
  pure val expected: List[List[str]] = List(malformedChain.foldl(checks::setupExpected, (out, s) => out.append(s.label)))

  pure def diagnostic(expected: str, actual: str): bool = expected != "" and expected == actual
  pure def roleHex(role: str): str =
    if (role == adoption) "7363616c652d617474656d70742d61646f7074696f6e2d7631"
    else if (role == attempt) "7363616c652d617474656d70742d7631"
    else if (role == initial) "7363616c652d617474656d70742d73656c656374696f6e2d7631"
    else if (role == legacy) "7363616c652d726573756c742d73656c656374696f6e2d7631"
    else if (role == result) "7265717565737465642d7363616c652d7631"
    else ""
  pure def graph(rows: List[r::Attempt], role: str, parents: List[str], bindings: int): bool =
    roleHex(role) != "" and r::decoded(rows, "commit-view").nativeCount == parents.length() and
    r::treeEntry(rows, "tree-view", "dag-id", roleHex(role)) and r::decoded(rows, "dag-view").nativeCount == bindings and
    parents.indices().forall(i => parents[i] != "" and parents[i] ==
      r::outputId(rows, "object_view_parent", if (i == 0) "parent0" else "parent1"))
  pure def fieldEquals(rows: List[r::Attempt], text: str): bool = {
    val datum = r::nativeOutput(rows, "datum_decode", "field-datum")
    r::nativeNodeMatches(rows, "field-datum") and datum.nativeCount == 6 and datum.nativeItems == List(text)
  }

  pure def verdicts(row: r::Observation): List[str] = {
    val allRows = row.attempts
    if (row.scenario != 0 or allRows.length() != cases[0].length()) List("missing_steps")
    else {
      val rows = allRows.slice(f::setup.length(), allRows.length())
      val cliIds = allRows.foldl(Map(), (out, a) =>
        if (Set("record_sum", "request_scale", "work_scale_attempt", "select_scale_attempt", "adopt_scale_attempt").contains(a.op)
          and a.commit != "") {
          val alias = if (a.op == "record_sum") a.args[1] else if (a.op == "request_scale" or a.op == "work_scale_attempt") a.args[3]
            else a.args[5]
          out.put(alias, a.commit)
        } else out)
      val nativeIds = allRows.foldl(Map(), (out, a) =>
        if (Set("object_view_parent", "txn_put_object").contains(a.op) and a.nativeStatus == "ok")
          out.put(a.args[a.args.length() - 1], a.nativeValue) else out)
      def id(alias: str): str = if (cliIds.keys().contains(alias)) cliIds.get(alias)
        else {
          val key = if (nativeOperands.keys().contains(alias)) nativeOperands.get(alias) else alias
          if (nativeIds.keys().contains(key)) nativeIds.get(key) else ""
        }
      def checkGraph(name: str, window: List[r::Attempt]): bool =
        if (name == "result-id" or name == "other-result-id") {
          val foreign = name == "other-result-id"
          val request = id(if (foreign) "other-request-id" else "request-id")
          id("request-id") != id("other-request-id") and id("result-id") != id("other-result-id") and
          graph(window, result, List(request), 3) and fieldEquals(window, if (foreign) v2 else v1) and
          r::nativeLiteralMatches(window, "result-datum", 3, "2400000000000000")
        } else {
          val s = verifiedShapes.select(s => s.name == name).head()
          graph(window, s.role, s.parents.foldl(List(), (out, p) => out.append(id(p))), 1) and
          r::decoded(window, "dag-view").nativeValue == r::outputId(window, "txn_lookup_node", "field-node") and
          fieldEquals(window, s.text)
        }
      range(0, malformedChain.length()).foldl(checks::setupVerdicts(allRows), (out, i) => {
        val s = malformedChain[i]
        val a = rows[i]
        val req = s.request
        val op = req.op
        val isAdopt = op == "adopt_scale_attempt"
        val isPublish = op == "publish_selected_scale"
        val verdict = if (not(r::sameRequest(a, req))) "wrong_request"
          else if (s.label == "native_not_found") r::rejectionNativeReadVerdict(a, req, "")
          else if (op == "txn_ref_get" and s.expected != "") {
            if (id(s.expected) == "") "missing_expected_id" else r::rejectionNativeReadVerdict(a, req, id(s.expected))
          } else if (s.label == "native_ok") {
            val native = r::rejectionNativeVerdict(a, req, "ok")
            if (native == "native_ok" and s.graph != "" and not(checkGraph(s.graph, rows.slice(i, rows.length())))) "wrong_native_graph"
            else native
          } else if (s.label == "rejected") {
            val base = if (isAdopt or isPublish) id(req.args[2]) else ""
            val target = if (isAdopt or isPublish) id(req.args[4]) else ""
            if ((isAdopt or isPublish) and (base == "" or target == "")) "missing_expected_id"
            else if ((isAdopt and a.expectedAttempt != target) or (isPublish and a.expectedSelection != target)) "wrong_selection"
            else r::existingRejectionVerdict(a, req, base, diagnostic(s.expected, a.stderr))
          } else if (op == "request_scale" or op == "work_scale_attempt") r::scaleWriteVerdict(a, req, id(req.args[2]))
          else if (isAdopt) r::adoptVerdict(a, req, id("valid-tip"), id("second"), true)
          else if (isPublish) r::publishSelectedVerdict(a, req, id("plan"), id("valid-tip"), id("result-id"), true)
          else if (op == "inspect") checks::adoptionReport(a, req, id("valid-tip"), id("valid-middle"), id("request-id"),
            id("first"), id("result-id"), f::firstUuid, "historical")
          else "unknown_step"
        out.append(verdict)
      })
    }
  }

  pure val controls = all {
    diagnostic(wrongRequest, "adopt-scale-attempt: attempt does not retain the expected request commit"),
    not(diagnostic(wrongRequest, "adopt-scale-attempt: adoption must change the selected attempt commit")),
    not(diagnostic("inspect: attempt adoption has an invalid attempt ref name",
      "publish-selected-scale: attempt adoption has an invalid attempt ref name"))
  }
}
