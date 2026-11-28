module recorded_calls_policy_histories {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  type Step = { request: Request, label: str, mark: str, check: str, scope: str }
  type Shape = { name: str, role: str, parents: List[str], root: str, fields: List[(str, str)] }
  pure def stepFor(req: Request, label: str): Step = { request: req, label: label, mark: "", check: "", scope: "" }
  pure def markStep(req: Request, label: str, name: str): Step = { ...stepFor(req, label), mark: name }
  pure def checkStep(req: Request, label: str, check: str): Step = { ...stepFor(req, label), check: check }
  pure def native(reqs: List[Request]): List[Step] = reqs.foldl(List(), (out, req) => out.append(stepFor(req, "native_ok")))
  pure def read(steps: List[Step]): List[Step] = native(openNative("read")).concat(steps).concat(native(closeNative("txn_abort")))
  pure def write(steps: List[Step]): List[Step] = native(openNative("write")).concat(steps).concat(native(closeNative("txn_commit")))
  pure def reject(req: Request, diagnostic: str): Step = checkStep(req, "rejected", diagnostic)
  pure def ref(name: str, alias: str, id: str): Step = checkStep(refRead(name, alias), "native_ok", id)
  pure def absent(name: str): Step = stepFor(refRead(name, "missing-pin"), "native_not_found")
  pure def inspect(name: str): Request = source("inspect", List(name))
  pure def parent(view: str, i: int, id: str): Request =
    coreRequest("object_view_parent", List(view, List("0", "1", "2")[i], id))

  pure val policyRole = "scale-intent-policy-v1"
  pure val decisionRole = "scale-request-decision-v1"
  pure val planRole = "scale-plan-v1"
  pure val reuseDefault = "reuse-by-default"
  pure val attemptUuid = "a0000000-0000-4000-8000-000000000001"
  pure val fixtureUuid = "b0000000-0000-4000-8000-000000000002"
  pure val requestMismatch = "request-policy-scale: selection does not retain the expected request commit"
  pure val occupied = "request-policy-scale: ('invalid_state', -30799, 'ref already exists')"
  pure val receipts = Map("policy" -> "policy", "bad-policy" -> "native:bad-policy", "legacy" -> "native:legacy", "swapped" -> "native:swapped")

  pure def route(policy: str, plan: str, output: str, factor: str, override: str, selection: str): Request =
    source("request_policy_scale", List("producer", "producer", policy, receipts.get(policy),
      plan, output, factor, override, selection, receipts.get(selection)))
  pure def reuse(output: str, factor: str): Request = route("policy", "would-plan", output, factor, "default", "legacy")
  pure val definePolicy = source("define_scale_policy", List("policy", reuseDefault))
  pure def decision(name: str, parents: List[str], root: str, bindings: List[(str, str)]): Shape =
    { name: name, role: decisionRole, parents: parents, root: root, fields: bindings }
  pure def policy(name: str, parents: List[str], mode: str): Shape =
    { name: name, role: policyRole, parents: parents, root: "default", fields: List(("default", mode)) }
  pure def selectedFields(id: str, slot: str): List[(str, str)] = List(("decision_id", id), ("override", "default"),
    ("reason", "default-selection"), ("selection_ref", slot))

  pure def persist(shape: Shape): List[Step] = {
    val layout = shape.fields.foldl(List(shape.root), (out, pair) => out.concat(List(pair._1, pair._1)))
    val literals = shape.fields.foldl(List(), (out, pair) => out.concat(putLiteral("string", pair._2, "field-datum", pair._1)))
    val commitOps = putObject("commit", List("forged-tree").concat(shape.parents), shape.name)
    native(literals.concat(putObject("dag", layout, "forged-dag")).concat(putObject("tree", List(shape.role, "forged-dag"), "forged-tree"))
      .append(commitOps[0])).append(markStep(commitOps[1], "native_ok", shape.name))
      .concat(native(List(pin(shape.name, shape.name))))
  }
  pure val parentAliases = List("shape-parent-0", "shape-parent-1", "shape-parent-2")
  pure val literalAliases = Map("default" -> "default-literal", "decision_id" -> "uuid-literal", "override" -> "override-literal",
    "reason" -> "reason-literal", "selection_ref" -> "selection-literal", "plan_ref" -> "plan-literal")
  pure def shapeAt(shape: Shape): List[Request] = {
    val entry = snapshotAt("shape-pin", "shape-view", "shape-tree", "shape-dag", "")
    val parents = range(0, shape.parents.length()).foldl(List(), (out, i) => out.append(parent("shape-view", i, parentAliases[i])))
    val literals = shape.fields.foldl(List(), (out, pair) =>
      out.append(lookupNode("shape-dag", pair._1, pair._1)).concat(viewLiteral(pair._1, literalAliases.get(pair._1))))
    entry.concat(parents).concat(viewObject("dag", "shape-dag", "dag-view")).concat(literals)
  }
  pure def scoped(name: str, steps: List[Step]): List[Step] = steps.foldl(List(), (out, s) => out.append({ ...s, scope: name }))
  pure def observe(shape: Shape): List[Step] = scoped(shape.name,
    List(ref(shape.name, "shape-pin", shape.name)).concat(native(shapeAt(shape))))

  // Pin the portable request by its native plan parent, not by CLI inspection.
  pure val setup = List(markStep(source("record_sum", List("producer", "7", "5")), "recorded", "producer"),
    markStep(source("request_scale", List("producer", "producer", "plan", "3", "--implementation", "example.scale@2")), "recorded", "plan"),
    markStep(definePolicy, "recorded", "policy"))
    .concat(write(native(snapshotAt("plan:plan", "old-plan-view", "old-plan-tree", "request-dag", ""))
      .append(markStep(parent("old-plan-view", 0, "request-id"), "native_ok", "request-id"))
      .concat(native(List(pin("incoming", "request-id"))))))
  pure val basisPins = List(ref("producer", "producer", "producer"), ref("plan", "plan", "plan"),
    ref("policy", "policy", "policy"), ref("incoming", "incoming-pin", "request-id"))

  // :1345 — use a legacy (result-only) selection; main starts at a different result.
  pure val reuseSetup = setup.append(markStep(source("work_scale", List("incoming", "native:request-id", "result")), "recorded", "result"))
    .concat(read(List(ref("result", "result", "result")))).concat(List(
    markStep(source("select_scale_result", List("plan", "plan", "result", "native:result", "legacy")), "selected", "legacy"),
    markStep(source("record_scale", List("producer", "producer", "main", "4")), "recorded", "prior-main")))
  pure def reuseShape(name: str): Shape = decision(name, List("", "policy", "legacy"), "decision_id", selectedFields("", "legacy"))
  pure val first = reuseShape("first-decision")
  pure val again = reuseShape("again")
  pure val repeat = reuseShape("repeat")
  pure val repeatedShapes = List(first, again, repeat)
  pure def retained(main: str): List[Step] = basisPins.concat(List(ref("main", "main-pin", main),
    ref("result", "result", "result"), ref("legacy", "legacy", "legacy"), absent("would-plan"), absent("wrong-request")))
  pure def observeReuse(shape: Shape): List[Step] = observe(shape)
    .concat(scoped(shape.name, native(snapshotAt("shape-parent-0", "plan-view", "plan-tree", "plan-dag", "plan-request")
      .append(parent("plan-view", 1, "plan-main")))))
  pure val reuseSteps = reuseSetup.concat(read(retained("prior-main")))
    .concat(List(reject(reuse("wrong-request", "4"), requestMismatch), reject(reuse("result", "3"), occupied)))
    .concat(read(retained("prior-main")))
    .append(markStep(reuse(first.name, "3"), "recorded", first.name))
    .concat(read(retained("result").concat(observeReuse(first))))
    .append(markStep(inspect(first.name), "inspected", "first-report"))
    .concat(List(markStep(reuse(again.name, "3"), "recorded", again.name), markStep(reuse(repeat.name, "3"), "recorded", repeat.name)))
    .concat(read(retained("result").concat(observeReuse(again)).concat(observeReuse(repeat))))
    .concat(List(markStep(inspect(again.name), "inspected", "again-report"), markStep(inspect(repeat.name), "inspected", "repeat-report")))

  // :1403 — forge native records with exactly the intended defects and one valid counterpart.
  pure val malformedPolicy = policy("bad-policy", List("producer"), reuseDefault)
  pure val unknownPolicy = policy("unknown-policy", List(), "typo")
  pure val soundParents = List("plan", "policy", "chosen")
  pure val reuseBindings = selectedFields(fixtureUuid, "chosen")
  pure val valid = decision("valid-decision", soundParents, "decision_id", reuseBindings)
  pure def broken(shape: Shape, cause: str): (Shape, str) = (shape, cause)
  pure val wrongPolicyParent = "inspect: expected a scale-intent-policy-v1 commit with an optional policy parent"
  pure val wrongDecisionFields = "inspect: policy decision fields do not match the resolved policy"
  pure val malformed = List(
    broken(malformedPolicy, wrongPolicyParent),
    broken(unknownPolicy, "inspect: policy default must be reuse-by-default or execute-by-default"),
    broken({ ...valid, name: "swapped", parents: List("policy", "plan", "chosen") },
      "inspect: expected a scale-plan-v1 commit with a request and optional main parent"),
    broken({ ...valid, name: "bad-ancestor", parents: List("plan", "bad-policy", "chosen") }, wrongPolicyParent),
    broken({ ...valid, name: "not-selection", parents: List("plan", "policy", "producer") }, "inspect: expected a scale result or attempt selection commit"),
    broken({ ...valid, name: "wrong-root", root: "reason" }, "inspect: policy decision must have its decision ID as root"),
    broken({ ...valid, name: "wrong-id", fields: reuseBindings.replaceAt(0, ("decision_id", "not-a-uuid")) },
      "inspect: decision ID must be a canonical lowercase UUIDv4 in bytes"),
    broken({ ...valid, name: "wrong-override", fields: reuseBindings.replaceAt(1, ("override", "fresh")) },
      "inspect: fresh execution cannot retain a selection"),
    broken({ ...valid, name: "wrong-reason", fields: reuseBindings.replaceAt(2, ("reason", "default-no-selection")) }, wrongDecisionFields),
    broken({ ...valid, name: "extra-field", fields: reuseBindings.append(("plan_ref", "not-created")) }, wrongDecisionFields),
    broken(decision("aliased-refs", List("plan", "policy"), "decision_id", reuseBindings.replaceAt(2, ("reason", "default-no-selection"))
      .replaceAt(3, ("selection_ref", "fresh")).append(("plan_ref", "fresh"))), "inspect: policy decision has invalid or aliased ref names"))
  pure val forged = malformed.foldl(List(), (out, c) => out.append(c._1)).append(valid)
  pure val verifyForgery = forged.foldl(List(), (out, shape) => out.concat(observe(shape)))
  pure val positivePolicy = policy("policy", List(), reuseDefault)
  pure val createChild = source("define_scale_policy", List("next-policy", "execute-by-default", "bad-policy", "native:bad-policy"))
  pure val validChild = source("define_scale_policy", List("next-policy", "execute-by-default", "policy", "policy"))
  pure val fresh = decision("decision", List("fresh-plan", "policy"), "decision_id", List(("decision_id", ""),
    ("override", "fresh"), ("reason", "override-fresh"), ("plan_ref", "would-plan")))
  pure val readerSetup = setup.concat(List(
    markStep(source("work_scale_attempt", List("incoming", "native:request-id", "attempt", attemptUuid)), "recorded", "attempt"),
    markStep(source("select_scale_attempt", List("plan", "plan", "attempt", "attempt", "chosen")), "selected", "chosen")))
    .concat(read(basisPins.concat(List(ref("attempt", "attempt-pin", "attempt"), ref("chosen", "chosen", "chosen")))
      .concat(native(viewObject("commit", "attempt-pin", "attempt-view")))
      .append(markStep(parent("attempt-view", 1, "attempt-result"), "native_ok", "attempt-result"))))
  pure val ready = basisPins.concat(List(absent("main"), absent("would-plan"), absent("decision"), absent("next-policy")))
  pure val readerSteps = readerSetup.concat(write(forged.foldl(List(), (out, s) => out.concat(persist(s)))))
    .concat(read(ready.concat(observe(positivePolicy)).concat(verifyForgery)))
    .concat(malformed.foldl(List(), (out, c) => out.append(reject(inspect(c._1.name), c._2))))
    .concat(List(reject(createChild, "define-scale-policy: expected a scale-intent-policy-v1 commit with an optional policy parent"),
      reject(route("bad-policy", "would-plan", "decision", "3", "fresh", "swapped"),
        "request-policy-scale: expected a scale-intent-policy-v1 commit with an optional policy parent"),
      reject(route("policy", "would-plan", "decision", "3", "default", "swapped"),
        "request-policy-scale: expected a scale result or attempt selection commit")))
    .concat(read(ready))
    .append(markStep(inspect(valid.name), "inspected", "valid-report"))
    .append(markStep(validChild, "recorded", "next-policy"))
    .append(markStep(route("policy", "would-plan", "decision", "3", "fresh", "swapped"), "recorded", "decision"))
    .concat(read(basisPins.concat(List(absent("main"), markStep(refRead("would-plan", "fresh-plan"), "native_ok", "fresh-plan"),
      ref("next-policy", "next-policy-pin", "next-policy")))
      .concat(observe(fresh)).concat(native(snapshotAt("fresh-plan", "fresh-plan-view", "fresh-plan-tree", "fresh-plan-dag", "fresh-plan-request")))))
    .append(markStep(inspect("decision"), "inspected", "fresh-report"))

  pure val cases = List(reuseSteps, readerSteps)
  pure val expected = cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (labels, s) => labels.append(s.label))))
  var histories: List[List[Request]]
  action init = histories' = cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (reqs, s) => reqs.append(s.request))))
  action step = histories' = histories
}
