module recorded_calls_intent_cases {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_adoption_fixture as adoption from "./recorded_calls_adoption_fixture"

  pure val v1 = "example.scale@1"
  pure val v2 = "example.scale@2"
  pure val reuse = "reuse-by-default"
  pure val execute = "execute-by-default"
  pure val definition = "scale-intent-definition-v1"
  pure val decision = "scale-intent-decision-v1"
  pure val plan = "scale-plan-v1"
  pure val request = "scale-request-v1"

  type Step = { req: Request, want: str, value: str, graph: str }
  pure def step(req: Request, want: str, value: str): Step = { req: req, want: want, value: value, graph: "" }
  pure def native(reqs: List[Request]): List[Step] = reqs.foldl(List(), (out, req) => out.append(step(req, "native_ok", "")))
  pure def read(steps: List[Step]): List[Step] = native(openNative("read")).concat(steps).concat(native(closeNative("txn_abort")))
  pure def write(reqs: List[Request]): List[Step] = native(openNative("write").concat(reqs).concat(closeNative("txn_commit")))
  pure def refAt(name: str, alias: str, id: str): Step = step(refRead(name, alias), "native_ok", id)
  pure def ref(name: str, id: str): Step = refAt(name, "read-pin", id)
  pure def absent(name: str): Step = step(refRead(name, "absent-pin"), "native_not_found", "")
  pure def inspect(name: str): Request = source("inspect", List(name))
  pure def reject(req: Request, cause: str): Step = step(req, "rejected", cause)
  pure def define(name: str, mode: str, slot: str): Request =
    source("define_scale_intent", List(name, v1, mode, "chosen", slot))
  pure def child(name: str, parent: str, id: str): Request =
    source("define_scale_intent", List(name, v2, parent, id))
  pure def ask(intent: str, id: str, planPin: str, out: str, factor: str, impl: str, override: str, selected: str): Request =
    source("request_intent_scale", List("producer", "producer", intent, id, planPin, out, factor, impl, override, selected))

  // The first field is the root. The same specification drives the native put
  // and independently checks the committed object via reads, not the put aliases.
  type Shape = { name: str, entry: str, parents: List[str], fields: List[(str, str)] }
  pure def intentShape(name: str, parents: List[str], impl: str, mode: str, v1Slot: str): Shape =
    { name: name, entry: definition, parents: parents, fields: List(("default_implementation", impl),
      ("policy_default", mode), ("v1_selection_ref", v1Slot), ("v2_selection_ref", "chosen-b")) }
  pure def decisionShape(name: str, parents: List[str], impl: str, reason: str, bindings: List[(str, str)]): Shape =
    { name: name, entry: decision, parents: parents, fields: List(("decision_id", adoption::firstUuid),
      ("override", "default"), ("implementation_override", impl), ("implementation_reason", reason)).concat(bindings) }
  pure def persist(s: Shape): List[Request] = {
    val literals = s.fields.foldl(List(), (out, entry) => out.concat(putLiteral("string", entry._2, "field-value", entry._1)))
    val bindings = s.fields.foldl(List(s.fields[0]._1), (out, entry) => out.append(entry._1).append(entry._1))
    literals.concat(putObject("dag", bindings, "record-dag"))
      .concat(putObject("tree", List(s.entry, "record-dag"), "record-tree"))
      .concat(putObject("commit", List("record-tree").concat(s.parents), s.name)).append(pin(s.name, s.name))
  }
  pure val parentIndices = List("0", "1", "2")
  type Entry = (str, str, str)
  pure val recordEntry: Entry = ("record-commit", "record-tree", "record-dag")
  pure val missEntry: Entry = ("miss-decision", "miss-tree", "miss-dag")
  pure val planEntry: Entry = ("intent-plan", "plan-tree", "plan-dag")
  pure val requestEntry: Entry = ("intent-request", "request-tree", "request-dag")
  pure def readEntry(id: str, entry: Entry, parents: List[str]): List[Request] =
    snapshotAt(id, entry._1, entry._2, entry._3, "")
      .concat(range(0, parents.length()).foldl(List(), (out, i) =>
        out.append(adoption::parent(entry._1, parentIndices[i], parents[i]))))
  pure def readString(dag: str, name: str): List[Request] =
    List(lookupNode(dag, name, "string-node")).concat(viewLiteral("string-node", "string-value"))
  pure def shapeHeader(s: Shape): List[Request] = readEntry("read-pin", recordEntry, parentIndices.slice(0, s.parents.length()))
    .concat(viewObject("dag", "record-dag", "record-root"))
  pure def readShape(s: Shape): List[Request] = shapeHeader(s)
    .concat(s.fields.foldl(List(), (out, entry) => out.concat(readString("record-dag", entry._1))))
  pure def graph(name: str, reqs: List[Request]): List[Step] =
    List({ ...step(reqs[0], "native_ok", ""), graph: name }).concat(native(reqs.slice(1, reqs.length())))
  pure val planReads = readEntry("miss-pin", missEntry, List("miss-plan", "miss-intent"))
    .concat(readEntry("plan-b-pin", planEntry, List("miss-request")))
    .concat(readEntry("miss-request", requestEntry, List("miss-producer")))
    .concat(viewObject("dag", "request-dag", "request-root"))
    .concat(readString("request-dag", "implementation"))
    .append(lookupNode("request-dag", "factor", "factor-node")).concat(viewLiteral("factor-node", "factor-value"))

  pure val base = intentShape("basis", List(), v1, reuse, "chosen")
  pure val right = intentShape("right", List("basis-id"), v2, reuse, "chosen")
  pure val definitions = List(
    (intentShape("changed-policy", List("basis-id"), v2, execute, "chosen"), "inspect: an intent version must preserve its reuse default and selection slots"),
    (intentShape("changed-slot", List("basis-id"), v2, reuse, "another"), "inspect: an intent version must preserve its reuse default and selection slots"),
    (intentShape("aliased-slots", List("basis-id"), v2, reuse, "chosen-b"), "inspect: intent operation refs, selection slots, and main must be distinct"),
    (intentShape("unknown-version", List("basis-id"), "typo", reuse, "chosen"), "inspect: unsupported scale implementation b'typo'; use example.scale@1 or example.scale@2"),
    (intentShape("wrong-ancestor", List("producer-id"), v2, reuse, "chosen"),
      "inspect: expected a scale-intent-definition-v1 commit with an optional intent parent or a scale supersession declaration"))
  pure def missFields(planPin: str, slot: str): List[(str, str)] =
    List(("reason", "default-no-selection"), ("plan_ref", planPin), ("selection_ref", slot))
  pure val badImplementation = "inspect: intent decision does not match the resolved implementation"
  pure val decisions = List(
    (decisionShape("wrong-definition", List("plan-b-pin", "basis-id"), "default", "default-implementation", missFields("plan-b", "chosen")), badImplementation),
    (decisionShape("wrong-override", List("plan-b-pin", "right-id"), v1, "explicit-implementation", missFields("plan-b", "chosen")), badImplementation),
    (decisionShape("wrong-reason", List("plan-b-pin", "right-id"), v2, "default-implementation", missFields("plan-b", "chosen-b")), badImplementation),
    (decisionShape("wrong-slot", List("plan-b-pin", "right-id"), "default", "default-implementation", missFields("plan-b", "chosen")),
      "inspect: intent decision does not name the resolved selection slot"),
    (decisionShape("aliased-plan", List("plan-b-pin", "right-id"), "default", "default-implementation", missFields("chosen", "chosen-b")),
      "inspect: intent decision has invalid or aliased ref names"),
    (decisionShape("foreign-selection", List("plan-b-pin", "right-id", "chosen-pin"), "default", "default-implementation",
      List(("reason", "default-selection"), ("selection_ref", "chosen-b"))), "inspect: selection does not retain the expected request commit"))
  pure val invalid = definitions.concat(decisions)
  pure val shapes = List(base, right).concat(invalid.foldl(List(), (out, row) => out.append(row._1)))
  pure val normalPins = List(ref("producer", "producer"), ref("plan", "plan"), refAt("chosen", "chosen-pin", "chosen"), absent("main"))
  pure val lineagePins = normalPins.concat(List(refAt("basis", "basis-id", "basis"), refAt("right", "right-id", "right"),
    refAt("miss", "miss-pin", "miss"), absent("chosen-b")))
  pure val lineage = List(step(define("basis", reuse, "chosen-b"), "recorded", ""),
    step(child("right", "basis", "basis"), "recorded", "basis"),
    step(ask("right", "right", "plan-b", "miss", "3", "default", "default", "-"), "recorded", ""))
    .concat(read(lineagePins.concat(List(step(refRead("plan-b", "plan-b-pin"), "native_ok", "")))
      .concat(graph("miss-layout", planReads))))
    .concat(write(invalid.foldl(List(), (out, row) => out.concat(persist(row._1)))))
    .concat(read(shapes.foldl(List(), (out, s) => out.append(ref(s.name, s.name)).concat(graph(s.name, readShape(s))))))
    .concat(invalid.foldl(List(), (out, row) => out.append(reject(inspect(row._1.name), row._2))))
    .concat(List(reject(child("child", "wrong-ancestor", "native:wrong-ancestor"),
      "define-scale-intent: expected a scale-intent-definition-v1 commit with an optional intent parent or a scale supersession declaration"),
      reject(ask("wrong-ancestor", "native:wrong-ancestor", "unused-plan", "unused", "3", "default", "fresh", "-"),
        "request-intent-scale: expected a scale-intent-definition-v1 commit with an optional intent parent or a scale supersession declaration"),
      step(inspect("right"), "inspected", ""), step(inspect("miss"), "inspected", "")))
    .concat(read(lineagePins.concat(List(ref("plan-b", "miss-plan"), absent("child"), absent("unused-plan"), absent("unused")))))

  pure def executableIntent(name: str, planPin: str, factor: str, impl: str, override: str, selected: str): Request =
    ask("intent", "intent", planPin, name, factor, impl, override, selected)
  pure val defaultAsk = executableIntent("default-decision", "default-plan", "3", "default", "default", "chosen")
  pure val freshAsk = executableIntent("fresh-decision", "fresh-plan", "3", "default", "fresh", "chosen")
  pure val reuseAsk = executableIntent("reused", "unused", "3", v1, "reuse-selected", "chosen")
  pure val routingPins = normalPins.concat(List(ref("intent", "intent"), ref("not-selection", "producer")))
  pure val routing = List(step(source("define_scale_intent", List("intent", v2, execute, "chosen", "not-selection")), "recorded", ""))
    .concat(write(List(pin("not-selection", "producer-id"))))
    .concat(read(routingPins.append(refAt("first", "first-pin", "first"))
      .concat(native(viewObject("commit", "first-pin", "attempt-view").append(adoption::parent("attempt-view", "1", "first-result"))))))
    .concat(List(reject(executableIntent("bad", "unused", "3", "default", "reuse-selected", "native:producer-id"),
        "request-intent-scale: expected a scale result or attempt selection commit"),
      reject(executableIntent("plan", "rolled-back", "4", "default", "fresh", "chosen"), "occupied")))
    .concat(read(routingPins.concat(List(absent("rolled-back"), absent("bad"), absent("unused")))))
    .concat(List(step(defaultAsk, "recorded", ""), step(inspect("default-decision"), "inspected", ""),
      step(freshAsk, "recorded", ""), step(inspect("fresh-decision"), "inspected", "")))
    .concat(read(List(absent("main"), ref("not-selection", "producer"))))
    .concat(List(step(reuseAsk, "recorded", ""), step(inspect("reused"), "inspected", "")))
    .concat(read(List(ref("main", "first-result"), ref("not-selection", "producer"), absent("unused"),
      absent("rolled-back"), ref("plan", "plan"), ref("chosen", "chosen"), refAt("reused", "reused-pin", "reused"))
      .concat(native(List(refRead("default-plan", "default-plan-pin"), refRead("fresh-plan", "fresh-plan-pin"))
        .concat(viewObject("commit", "default-plan-pin", "default-plan-view"))
        .append(adoption::parent("default-plan-view", "0", "default-decision-request"))
        .concat(viewObject("commit", "fresh-plan-pin", "fresh-plan-view"))
        .append(adoption::parent("fresh-plan-view", "0", "fresh-decision-request"))
        .concat(viewObject("commit", "reused-pin", "reuse-view"))
        .append(adoption::parent("reuse-view", "0", "reused-plan"))))))

  // Collect an immutable producer ID for native forging without consulting a
  // live pin while assembling any later CLI invocation.
  pure val setup = adoption::setup.concat(openNative("read"))
    .append(refRead("producer", "producer-id")).concat(closeNative("txn_abort"))
  pure val cases = List(lineage, routing)
  pure val requests = cases.foldl(List(), (out, steps) => out.append(steps.foldl(setup, (reqs, s) => reqs.append(s.req))))
}

module recorded_calls_intent_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_intent_cases.requests

  var histories: List[List[Request]]
  action init = histories' = requests
  action step = histories' = histories
}
