module recorded_calls_supersession_invalid_cases {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_intent_cases as i from "./recorded_calls_intent_histories"

  pure val entry = "scale-implementation-supersession-v1"
  pure val reason = "operational-replacement"
  pure val unrelated = "unrelated"
  pure val zero = "00000000000000000000000000000000"
  pure val short = "696e76616c6964"
  pure val zeroOperand = "literal:00000000000000000000000000000000"
  pure val shortOperand = "literal:696e76616c6964"
  pure val producerRead = i::inspect("producer")
  pure def define(name: str, version: str): Request =
    source("define_scale_intent", List(name, version, i::execute, "slot-v1", "slot-v2"))
  pure def know(name: str, id: str): Request = source("inspect", List(name, id))
  pure val setup = List(
    i::step(source("record_sum", List("producer", "7", "5")), "recorded", ""),
    i::step(producerRead, "inspected", ""),
    i::step(define("basis", i::v1), "recorded", ""),
    i::step(define(unrelated, i::v2), "recorded", ""),
    i::step(i::ask("basis", "basis", "pending", "decision", "3", "default", "default", "-"), "recorded", ""),
    i::step(source("declare_scale_supersession", List("basis", "basis", "noted", i::v1, i::v2, reason, "producer", "producer")), "recorded", ""),
    i::step(i::child("promoted", "noted", "noted"), "recorded", "noted"))

  // Take the genuine binding IDs from committed storage. Each forgery changes
  // only one part of this layout; another native read verifies the result.
  pure val getGenuine = i::read(List(i::refAt("noted", "noted-id", "noted"))
    .concat(i::native(snapshotAt("noted-id", "noted-commit", "noted-tree", "noted-dag", "").concat(List(
      lookupNode("noted-dag", "predecessor", "v1-node"), lookupNode("noted-dag", "successor", "v2-node"),
      lookupNode("noted-dag", "reason", "reason-node"))))))

  type Shape = { name: str, root: str, successor: str, reasonNode: str, parents: List[str] }
  pure val genuine: Shape = { name: "noted", root: "v1-node", successor: "v2-node", reasonNode: "reason-node",
    parents: List("basis-id", "producer-id") }
  pure val malformed = List(
    ({ ...genuine, name: "bad-root", root: "v2-node" }, "native:bad-root",
      "inspect: supersession declaration has the wrong DAG layout"),
    ({ ...genuine, name: "bad-type", reasonNode: "i64-node" }, "native:bad-type",
      "inspect: recorded literal has the wrong datum kind"),
    ({ ...genuine, name: "bad-reason", reasonNode: "bogus-node" }, "native:bad-reason",
      "inspect: supersession reason must be correctness-fix or operational-replacement"),
    ({ ...genuine, name: "self-endpoint", successor: "v1-node" }, "native:self-endpoint",
      "inspect: supersession endpoints must be distinct implementations"),
    ({ ...genuine, name: "no-evidence", parents: List("basis-id") }, "native:no-evidence",
      "inspect: supersession must have ordered intent basis and evidence parents"),
    ({ ...genuine, name: "swapped", parents: List("producer-id", "basis-id") }, "native:swapped",
      "inspect: expected a scale-intent-definition-v1 commit with an optional intent parent or a scale supersession declaration"),
    ({ ...genuine, name: "stacked", parents: List("promoted-id", "producer-id") }, "native:stacked",
      "inspect: intent ancestry already has a supersession declaration"))

  pure def persist(s: Shape): List[Request] =
    putObject("dag", List(s.root, "predecessor", "v1-node", "successor", s.successor, "reason", s.reasonNode), "forged-dag")
      .concat(putObject("tree", List(entry, "forged-dag"), "forged-tree"))
      .concat(putObject("commit", List("forged-tree").concat(s.parents), s.name)).append(pin(s.name, s.name))
  pure def readField(binding: str, node: str, value: str): List[Request] =
    List(lookupNode("declaration-dag", binding, node)).concat(viewLiteral(node, value))
  pure val declarationEntry: i::Entry = ("declaration-commit", "declaration-tree", "declaration-dag")
  pure def declarationReads(s: Shape): List[Request] =
    i::readEntry("read-pin", declarationEntry, i::parentIndices.slice(0, s.parents.length()))
      .concat(viewObject("dag", "declaration-dag", "declaration-layout"))
      .concat(readField("predecessor", "predecessor-node", "predecessor-value"))
      .concat(readField("successor", "successor-node", "successor-value"))
      .concat(readField("reason", "observed-reason-node", "reason-value"))

  pure def definition(name: str, version: str, parents: List[str]): i::Shape =
    { name: name, entry: i::definition, parents: parents, fields: List(("default_implementation", version),
      ("policy_default", i::execute), ("v1_selection_ref", "slot-v1"), ("v2_selection_ref", "slot-v2")) }
  pure val definitions = List(definition("basis", i::v1, List()), definition(unrelated, i::v2, List()),
    definition("promoted", i::v2, List("noted")))
  pure val decisionEntry: i::Entry = ("decision-commit", "decision-tree", "decision-dag")
  pure val planEntry: i::Entry = ("pending-commit", "pending-tree", "pending-dag")
  pure val decisionReads = i::readEntry("decision-id", decisionEntry, List("decision-plan", "decision-basis"))
    .concat(i::readEntry("pending-id", planEntry, List("pending-request")))
  pure val zeroRead = coreRequest("txn_get_object", List("snapshot", "commit", zero, "absent-commit"))
  pure val refs = List(i::ref("producer", "producer"), i::ref("basis", "basis"), i::ref(unrelated, unrelated),
    i::ref("decision", "decision"), i::ref("pending", "pending-id"), i::ref("promoted", "promoted"), i::ref("noted", "noted"),
    i::absent("main"), i::absent("slot-v1"), i::absent("slot-v2"))
  pure val shapes = malformed.foldl(List(genuine), (out, row) => out.append(row._1))
  pure val pinsForWrite = i::read(List(i::refAt("basis", "basis-id", "basis"), i::refAt("producer", "producer-id", "producer"),
    i::refAt("promoted", "promoted-id", "promoted")))
  pure val forge = i::write(malformed.foldl(
    putLiteral("string", "looks-valid", "bogus-datum", "bogus-node").concat(putLiteral("i64", "7", "i64-datum", "i64-node")),
    (out, row) => out.concat(persist(row._1))))
  pure val readback = i::read(List(i::refAt("decision", "decision-id", "decision"), i::step(refRead("pending", "pending-id"), "native_ok", ""),
    i::step(zeroRead, "native_not_found", "")).concat(i::graph("decision-layout", decisionReads))
    .concat(definitions.foldl(List(), (out, s) => out.append(i::ref(s.name, s.name)).concat(i::graph(s.name, i::readShape(s)))))
    .concat(shapes.foldl(List(), (out, s) => out.append(i::ref(s.name, s.name)).concat(i::graph(s.name, declarationReads(s))))))
  pure val negatives = malformed.foldl(List(), (out, row) =>
    out.append(i::reject(i::inspect(row._1.name), row._3)).append(i::reject(know("decision", row._2), row._3))).concat(List(
    i::reject(know("decision", unrelated), "inspect: knowledge commit belongs to a different intent lineage"),
    i::reject(know("decision", zeroOperand), "inspect: ('not_found', -30798, 'immutable object was not found')"),
    i::reject(know("decision", shortOperand), "inspect: knowledge commit must be a 32-digit hexadecimal ID"),
    i::reject(know("pending", "noted"), "inspect: a knowledge commit requires an intent decision")))
  pure val counterparts = List(i::inspect("basis"), i::inspect(unrelated), i::inspect("noted"), i::inspect("promoted"),
    i::inspect("pending"), i::inspect("decision"), know("decision", "promoted"))
    .foldl(List(), (out, req) => out.append(i::step(req, "inspected", "")))
  pure val steps = setup.concat(getGenuine).concat(pinsForWrite).concat(forge).concat(readback).concat(negatives).concat(counterparts)
    .concat(i::read(malformed.foldl(refs, (out, row) => out.append(i::ref(row._1.name, row._1.name)))))
  pure val requests = steps.foldl(List(), (out, s) => out.append(s.req))
}

module recorded_calls_supersession_invalid_histories {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_supersession_invalid_cases.requests

  var histories: List[List[Request]]
  action init = histories' = List(requests)
  action step = histories' = histories
}
