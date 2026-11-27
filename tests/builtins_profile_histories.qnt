module builtins_profile_histories {
  import builtin_primitive_fixture.* from "./builtin_primitive_fixture"

  pure val emptyFunc = "dml://builtin/map/empty"
  pure val insertFunc = "dml://builtin/map/insert"
  pure val getFunc = "dml://builtin/map/get"
  pure val listFunc = "dml://builtin/list/get"
  pure val emptyUri = "dml://source/builtin/map/empty/v1"
  pure val insertUri = "dml://source/builtin/map/insert/v1"
  pure val get1Uri = "dml://source/builtin/map/get/v1"
  pure val get2Uri = "dml://source/builtin/map/get/v2"
  pure val listUri = "dml://source/builtin/list/get/v1"
  pure val unknownUri = "dml://source/builtin/map/get/v99"
  pure val start = List(req("rec_new", List("snapshot", "rec")), req("rec_enter", List("rec")))
  pure val finish = req("rec_exit", List("rec"))
  pure val checkpoint = req("checkpoint", List("source", "committed"))
  pure val compare = req("compare", List("source", "committed"))
  pure def dag(node: str, id: str): Request = req("rec_dag", List("rec", node, id))
  pure def args(alias: str, pairs: List[str]): Request = req("rec_args", List("rec", alias).concat(pairs))
  pure def call(op: str, func: str, bindingId: str, input: str, result: str): Request =
    req(op, List("rec", func, bindingId, input, result))

  type GraphOperation = { dag: str, func: str, binding: str, source: str, args: str, entries: List[(str, str)] }
  pure def insertOperation(output: str, args: str, value: str): GraphOperation =
    { dag: output, func: insertFunc, binding: "insert-binding", source: insertUri, args: args,
      entries: List(("6b6579", "key-dag"), ("6d6170", "empty-dag"), ("76616c7565", value)) }
  pure def getOperation(output: str, bindingId: str, uri: str): GraphOperation =
    { dag: output, func: getFunc, binding: bindingId, source: uri, args: "get-input-dag",
      entries: List(("6b6579", "key-dag"), ("6d6170", "map-right-dag")) }
  pure val graphOperations: List[GraphOperation] = List(
    { dag: "empty-dag", func: emptyFunc, binding: "empty-binding", source: emptyUri, args: "none-dag", entries: [] },
    insertOperation("map-left-dag", "insert-left-dag", "left-source-dag"),
    insertOperation("map-right-dag", "insert-right-dag", "right-source-dag"),
    getOperation("get1-dag", "get1-binding", get1Uri), getOperation("get2-dag", "get2-binding", get2Uri),
    { dag: "answer-dag", func: listFunc, binding: "list-binding", source: listUri, args: "list-input-dag",
      entries: List(("696e646578", "index-dag"), ("6c697374", "get2-dag")) })
  pure val graphEdges = List(
    ("left-source-dag", "source", "left"), ("right-source-dag", "source", "right"),
    ("empty-dag", "arguments", "none-dag"),
    ("map-left-dag", "arguments", "insert-left-dag"), ("map-right-dag", "arguments", "insert-right-dag"),
    ("insert-left-dag", "source-02", "left-source-dag"), ("insert-right-dag", "source-02", "right-source-dag"),
    ("get1-dag", "arguments", "get-input-dag"), ("get2-dag", "arguments", "get-input-dag"),
    ("get-input-dag", "source-01", "map-right-dag"),
    ("answer-dag", "arguments", "list-input-dag"), ("list-input-dag", "source-01", "get2-dag"),
    ("result-dag", "inputs", "get-input-dag"), ("result-dag", "returned", "answer-dag"),
    ("result-dag", "trace", "trace-dag"),
    ("trace-dag", "call-00", "empty-dag"), ("trace-dag", "call-01", "map-left-dag"),
    ("trace-dag", "call-02", "map-right-dag"), ("trace-dag", "call-03", "get1-dag"),
    ("trace-dag", "call-04", "get2-dag"), ("trace-dag", "call-05", "answer-dag"),
    ("empty-dag", "binding", "empty-binding"),
    ("map-left-dag", "binding", "insert-binding"), ("map-right-dag", "binding", "insert-binding"),
    ("get1-dag", "binding", "get1-binding"), ("get2-dag", "binding", "get2-binding"),
    ("answer-dag", "binding", "list-binding"))

  pure val graph = writer.concat(List(binding(emptyUri, "empty-binding"), binding(insertUri, "insert-binding"),
      binding(get1Uri, "get1-binding"), binding(get2Uri, "get2-binding"), binding(listUri, "list-binding")))
    .concat(putDatum("i64", List("42"), "answer-datum"))
    .concat(literal("list", List("answer-datum"), "list-node"))
    .concat(putObject("dag", List("list-node", "item", "list-node", "left", "list-node"), "left"))
    .concat(putObject("dag", List("list-node", "item", "list-node", "right", "list-node"), "right"))
    .concat(start).concat(List(
      req("rec_source", List("rec", "left", "item", "left-source")), dag("left-source", "left-source-dag"),
      req("rec_source", List("rec", "right", "item", "right-source")), dag("right-source", "right-source-dag"),
      args("none", List()), dag("none", "none-dag"),
      call("rec_call", emptyFunc, "empty-binding", "none", "empty"), dag("empty", "empty-dag"),
      req("rec_literal", List("rec", "string", "text:items", "key")), dag("key", "key-dag"),
      args("insert-left", List("text:map", "empty", "text:key", "key", "text:value", "left-source")),
      dag("insert-left", "insert-left-dag"),
      args("insert-right", List("text:map", "empty", "text:key", "key", "text:value", "right-source")),
      dag("insert-right", "insert-right-dag"),
      call("rec_call", insertFunc, "insert-binding", "insert-left", "map-left"), dag("map-left", "map-left-dag"),
      call("rec_call", insertFunc, "insert-binding", "insert-right", "map-right"), dag("map-right", "map-right-dag"),
      args("get-input", List("text:map", "map-right", "text:key", "key")), dag("get-input", "get-input-dag"),
      call("rec_call_observed", getFunc, "get1-binding", "get-input", "get1"), dag("get1", "get1-dag"),
      call("rec_call_observed", getFunc, "get2-binding", "get-input", "get2"), dag("get2", "get2-dag"),
      req("rec_literal", List("rec", "i64", "int:0", "index")), dag("index", "index-dag"),
      args("list-input", List("text:list", "get2", "text:index", "index")), dag("list-input", "list-input-dag"),
      call("rec_call", listFunc, "list-binding", "list-input", "answer"), dag("answer", "answer-dag"),
      req("rec_trace", List("rec", "trace-dag")), req("rec_return", List("rec", "answer", "get-input", "result")),
      dag("result", "result-dag"), finish)).concat(close("txn_commit")).append(checkpoint).concat(reader)
    .concat(List(inspect("node", "left-source-dag"), inspect("node", "right-source-dag"), inspect("arguments", "none-dag"),
      req("inspect_offline", List("snapshot", "returned", "result-dag")),
      native("datum_encode", List("map", "empty-map-packed")), native("datum_decode", List("empty-map-packed"))))
    .concat(graphOperations.foldl(List(), (out, o) => out.append(inspect("operation", o.dag))))
    .concat(graphEdges.foldl(List(), (out, e) => out.concat(edge(e._1, e._2, e._3))))
    .concat(close("txn_abort")).append(compare)

  pure def pairing(uri: str): List[Request] = writer.append(binding(uri, "candidate"))
    .concat(close("txn_commit")).append(checkpoint).concat(reader).append(inspect("binding", "candidate"))
    .concat(close("txn_abort")).concat(writer).concat(start).append(args("none", List()))
    .append(call("rec_call", getFunc, "candidate", "none", "rejected")).append(finish)
    .concat(close("txn_abort")).append(compare)

  pure val badBindings = List(
    ("bad-root", "uri-node", "", "", "builtin profile has wrong root"),
    ("bad-adapter", "bind-role", "adapter", "uri-node", "wrong datum kind in builtin profile"),
    ("bad-interpreter", "bind-role", "interpreter", "text-node", "wrong datum kind in builtin profile"),
    ("bad-timeout", "bind-role", "timeout-ms", "text-node", "wrong datum kind in builtin profile"),
    ("bad-source", "bind-role", "source", "text-node", "wrong datum kind in builtin profile"),
    ("bad-role", "other-role", "role", "other-role", "not a builtin binding role"),
    ("extra-field", "bind-role", "extra", "text-node", "builtin profile has wrong binding count"))
  pure def bindingDag(root: str, replaced: str, node: str, alias: str): List[Request] = {
    val orig = List(("role", "bind-role"), ("adapter", "absent"), ("interpreter", "absent"),
      ("timeout-ms", "absent"), ("source", "uri-node"))
    val bindings = orig.foldl(List(root), (out, f) => out.append(f._1).append(if (f._1 == replaced) node else f._2))
    putObject("dag", if (replaced == "extra") bindings.append("extra").append(node) else bindings, alias)
  }
  pure val malformed = writer.append(binding(get1Uri, "valid-binding"))
    .concat(literal("null", List("none"), "absent"))
    .concat(literal("uri", List(get1Uri), "uri-node"))
    .concat(literal("string", List(get1Uri), "text-node"))
    .concat(literal("string", List("builtin-binding-v1"), "bind-role"))
    .concat(literal("string", List("other"), "other-role"))
    .concat(bindingDag("bind-role", "", "", "native-binding"))
    .concat(badBindings.foldl(List(), (out, b) => out.concat(bindingDag(b._2, b._3, b._4, b._1))))
    .concat(close("txn_commit")).append(checkpoint).concat(reader).append(inspect("binding", "native-binding"))
    .concat(badBindings.foldl(List(), (out, b) => out.append(inspect("binding", b._1))))
    .concat(close("txn_abort")).append(compare)

  pure val lies = List(
    ("truth-source-dag", List("role", "name", "source"), "false-i64", "false-source",
      "literal source node differs from named native binding"),
    ("truth-args-dag", List("role", "key-00", "source-00"), "false-map", "false-args",
      "argument MAP differs from actual source values"),
    ("truth-call-dag", List("role", "func", "binding", "arguments"), "false-i64", "false-call",
      "builtin operation value differs from fixed semantics"),
    ("truth-return-dag", List("role", "returned", "inputs", "trace"), "false-i64", "false-return",
      "builtin return value differs from returned node"))
  pure val falseRecords = writer.append(binding(emptyUri, "empty-binding"))
    .concat(literal("i64", List("44"), "named"))
    .concat(literal("i64", List("45"), "false-i64"))
    .concat(literal("map", List(), "false-map"))
    .concat(putObject("dag", List("named", "item", "named"), "origin"))
    .concat(start).concat(List(req("rec_source", List("rec", "origin", "item", "truth-source")),
      dag("truth-source", "truth-source-dag"), args("truth-args", List("text:item", "truth-source")),
      dag("truth-args", "truth-args-dag"), args("none", List()),
      req("rec_return", List("rec", "truth-source", "none", "truth-return")), dag("truth-return", "truth-return-dag"),
      call("rec_call", emptyFunc, "empty-binding", "none", "truth-call"), dag("truth-call", "truth-call-dag"), finish))
    .concat(lies.foldl(List(), (out, l) => out.concat(replaceValue(l._1, l._2, l._3, l._4))))
    .concat(close("txn_commit")).append(checkpoint).concat(reader)
    .concat(lies.foldl(List(), (out, l) => out.append(inspect("node", l._1))
      .append(lookup(l._4, "value", "forged-value")).append(inspect("node", l._4))))
    .concat(close("txn_abort")).append(compare)

  pure val profileHistories: List[List[Request]] = List(graph, pairing(unknownUri), pairing(listUri), malformed, falseRecords)
}
