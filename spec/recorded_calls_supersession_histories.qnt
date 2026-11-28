module recorded_calls_supersession_cases {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  pure val v1 = "example.scale@1"
  pure val v2 = "example.scale@2"
  pure val reuse = "reuse-by-default"
  pure val execute = "execute-by-default"
  pure val fix = "correctness-fix"
  pure val replace = "operational-replacement"
  pure val declarationEntry = "scale-implementation-supersession-v1"

  type Step = { req: Request, want: str, value: str }
  pure def step(req: Request, want: str, value: str): Step = { req: req, want: want, value: value }
  pure def native(reqs: List[Request]): List[Step] = reqs.foldl(List(), (out, req) => out.append(step(req, "native_ok", "")))
  pure def read(role: str, steps: List[Step]): List[Step] =
    native(openRepo(role, "existing", "read")).concat(steps).concat(native(closeRepo(role, "txn_abort")))
  pure def ref(pinName: str, alias: str, expected: str): Step = step(refRead(pinName, alias), "native_ok", expected)
  pure def absent(names: List[str]): List[Step] = names.foldl(List(), (out, n) =>
    out.append(step(refRead(n, "absent-pin"), "native_not_found", "")))
  pure def objectParent(view: str, i: str, alias: str): Request = coreRequest("object_view_parent", List(view, i, alias))
  pure def declare(basis: str, id: str, out: str, pred: str, succ: str, reason: str, evidence: str, audit: str): Request =
    source("declare_scale_supersession", List(basis, id, out, pred, succ, reason, evidence, audit))
  pure def define(version: str, mode: str): Request =
    source("define_scale_intent", List("basis", version, mode, "slot-v1", "slot-v2"))
  type DecisionPath = { name: str, plan: str, pinAlias: str, commit: str, planId: str, intentId: str, planView: str, requestId: str }
  pure val oldPath: DecisionPath = { name: "old", plan: "old-plan", pinAlias: "old-replica-pin", commit: "old-view",
    planId: "old-plan-id", intentId: "old-intent", planView: "old-plan-view", requestId: "old-request" }
  pure val newPath: DecisionPath = { name: "new", plan: "new-plan", pinAlias: "new-replica-pin", commit: "new-view",
    planId: "new-plan-id", intentId: "new-intent", planView: "new-plan-view", requestId: "new-request" }
  pure def ask(intent: str, d: DecisionPath): Request = source("request_intent_scale",
    List("producer", "producer", intent, intent, d.plan, d.name, "3", "default", "default", "-"))
  pure def inspect(role: str, name: str, knowledge: List[str]): Step =
    step(coreRequest("inspect", List(role, name).concat(knowledge)), "inspected", "")
  pure def reject(req: Request, diagnostic: str): Step = step(req, "rejected", diagnostic)

  pure val declarationLiterals = List(("predecessor", "predecessor-node", "predecessor-value"),
    ("successor", "successor-node", "successor-value"), ("reason", "reason-node", "reason-value"))
  pure def declarationReads(pinAlias: str): List[Request] =
    snapshotAt(pinAlias, "declaration-view", "declaration-tree", "declaration-dag", "declaration-basis")
      .append(objectParent("declaration-view", "1", "declaration-evidence"))
      .concat(viewObject("dag", "declaration-dag", "declaration-root"))
      .concat(declarationLiterals.foldl(List(), (out, f) => out.append(lookupNode("declaration-dag", f._1, f._2))
        .concat(viewLiteral(f._2, f._3))))

  pure val valid = declare("basis", "basis", "noted", v1, v2, fix, "producer", "producer")
  pure val aliases = "declare-scale-supersession: intent operation refs, selection slots, and main must be distinct"
  pure val occupied = "declare-scale-supersession: ('invalid_state', -30799, 'ref already exists')"
  pure val aliasedEvidence = reject(declare("basis", "basis", "unused", v1, v2, fix, "slot-v2", "producer"), aliases)
  pure val guardRejections = List(
    reject(declare("basis", "native:producer-id", "unused", v1, v2, fix, "producer", "producer"),
      "declare-scale-supersession: intent ref does not point to the expected intent commit"),
    reject(declare("basis", "basis", "unused", v1, v2, fix, "producer", "native:basis-id"),
      "declare-scale-supersession: evidence ref does not point to the expected evidence commit"),
    reject(declare("basis", "basis", "unused", v1, v2, fix, "empty", "native:empty-id"),
      "declare-scale-supersession: supersession evidence must have a nonempty tree"),
    reject(declare("basis", "basis", "unused", v1, v2, fix, "same-basis", "native:basis-id"),
      "declare-scale-supersession: supersession basis and evidence must be distinct commits"),
    aliasedEvidence,
    reject(declare("basis", "basis", "slot-v1", v1, v2, fix, "producer", "producer"), aliases),
    reject(declare("basis", "basis", "main", v1, v2, fix, "producer", "producer"), aliases),
    reject(declare("basis", "basis", "unused", v1, v1, fix, "producer", "producer"),
      "declare-scale-supersession: supersession endpoints must be distinct implementations"),
    reject(declare("basis", "basis", "unused", v1, "example.scale@3", fix, "producer", "producer"),
      "declare-scale-supersession: unsupported scale implementation b'example.scale@3'; use example.scale@1 or example.scale@2"),
    reject(declare("basis", "basis", "unused", v1, v2, "typo", "producer", "producer"),
      "declare-scale-supersession: supersession reason must be correctness-fix or operational-replacement"),
    reject(declare("basis", "basis", "empty", v1, v2, fix, "producer", "producer"), occupied))
  pure val producer = step(source("record_sum", List("producer", "7", "5")), "recorded", "")
  pure val originPins = List(ref("producer", "producer-id", "producer"), ref("basis", "basis-id", "basis"))
  pure val emptyReads = viewObject("commit", "empty-id", "empty-view").concat(viewObject("tree", "empty-view", "empty-tree-view"))
  pure val guards = List(producer, step(define(v2, reuse), "recorded", ""))
    .concat(read("source", originPins))
    .concat(native(openNative("write").concat(putObject("tree", List(), "empty-tree"))
      .concat(putObject("commit", List("empty-tree"), "empty-id"))
      .concat(List(pin("empty", "empty-id"), pin("same-basis", "basis-id"), pin("slot-v2", "producer-id")))
      .concat(closeNative("txn_commit"))))
    .concat(read("source", List(ref("empty", "empty-pin", "empty-id"), ref("same-basis", "same-pin", "basis"),
      ref("slot-v2", "slot-pin", "producer")).concat(native(emptyReads))
      .concat(absent(List("main", "unused", "slot-v1", "noted")))))
    .concat(guardRejections)
    .concat(List(step(valid, "recorded", ""), inspect("source", "noted", List()), inspect("source", "basis", List()),
      reject(valid, occupied), reject(declare("noted", "noted", "unused", v2, v1, fix, "producer", "producer"),
        "declare-scale-supersession: intent ancestry already has a supersession declaration")))
    .concat(read("source", originPins.concat(List(ref("noted", "noted-pin", "noted"), ref("empty", "empty-pin", "empty-id"),
      ref("same-basis", "same-pin", "basis"), ref("slot-v2", "slot-pin", "producer")))
      .concat(absent(List("main", "unused", "slot-v1"))).concat(native(declarationReads("noted-pin")))))
    .concat(native(openNative("write").append(drop("slot-v2", "producer-id")).concat(closeNative("txn_commit"))))
    .concat(read("source", absent(List("slot-v2")))).append(aliasedEvidence)

  pure def copy(id: str, sourcePin: str, bundle: str, destPin: str, imported: str): List[Step] = List(
    step(coreRequest("repo_export_commit", List("source", sourcePin, bundle)), "native_ok", id),
    step(coreRequest("repo_import_commit_staged", List("replica", bundle, destPin, imported)), "native_ok", id))
  pure def decisionReads(d: DecisionPath): List[Request] =
    viewObject("commit", d.pinAlias, d.commit).append(objectParent(d.commit, "0", d.planId))
      .append(objectParent(d.commit, "1", d.intentId)).concat(viewObject("commit", d.planId, d.planView))
      .append(objectParent(d.planView, "0", d.requestId))
  pure val transferred = List(producer, step(source("record_sum", List("evidence", "-3", "0")), "recorded", ""),
    step(define(v1, execute), "recorded", ""), step(ask("basis", oldPath), "recorded", ""),
    step(declare("basis", "basis", "noted", v1, v2, replace, "evidence", "evidence"), "recorded", ""),
    step(source("define_scale_intent", List("promoted", v2, "noted", "noted")), "recorded", "noted"),
    step(ask("promoted", newPath), "recorded", ""))
    .concat(read("source", List(ref("noted", "noted-id", "noted"))))
    // The evidence parent is itself a declaration, but not part of the intent ancestry.
    .append(step(declare("basis", "basis", "sibling", v2, v1, fix, "noted", "native:noted-id"), "recorded", ""))
    .concat(read("source", List(ref("old", "old-pin", "old"), ref("new", "new-pin", "new"), ref("sibling", "sibling-pin", "sibling"),
      ref("evidence", "evidence-id", "evidence"))))
    .append(step(source("checkpoint_file", List("origin")), "file_observed", ""))
    .concat(native(List(coreRequest("repo_open", List("source", "existing")), coreRequest("repo_open", List("replica", "create")))))
    .concat(copy("old", "old-pin", "old-bundle", "old", "old-import"))
    .concat(copy("new", "new-pin", "new-bundle", "new", "new-import"))
    .concat(copy("sibling", "sibling-pin", "sibling-bundle", "peer-knowledge", "sibling-import"))
    .concat(native(List(coreRequest("repo_close", List("replica")), coreRequest("repo_close", List("source")))))
    .append(step(coreRequest("collect", List("replica")), "collected", ""))
    .concat(read("replica", absent(List("main", "producer", "evidence", "basis", "noted", "promoted", "sibling",
      "old-plan", "new-plan", "slot-v1", "slot-v2"))
      .concat(List(ref("old", "old-replica-pin", "old"), ref("new", "new-replica-pin", "new"),
        ref("peer-knowledge", "sibling-replica-pin", "sibling")))
      .concat(native(viewObject("commit", "evidence-id", "retained-evidence")))
      .concat(native(decisionReads(oldPath).concat(decisionReads(newPath))))
      .concat(native(declarationReads("sibling-replica-pin")))))
    .concat(List(inspect("replica", "old", List()), inspect("replica", "old", List("promoted")),
      inspect("replica", "new", List()), inspect("replica", "new", List("basis")), inspect("replica", "new", List("sibling")),
      step(source("compare_file", List("origin")), "file_observed", "")))

  pure val cases = List(guards, transferred)
  pure val requests = cases.foldl(List(), (out, steps) => out.append(steps.foldl(List(), (reqs, s) => reqs.append(s.req))))
}

module recorded_calls_supersession_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_supersession_cases.requests

  var histories: List[List[Request]]
  action init = histories' = requests
  action step = histories' = histories
}
