module builtins_values_histories {
  type ValueRequest = { op: str, args: List[str] }
  type ValueStep = { request: ValueRequest, want: str, message: str, tag: str }

  pure def actionStep(op: str, args: List[str]): ValueStep =
    { request: { op: op, args: args }, want: "ok", message: "", tag: "" }
  pure def native(op: str, args: List[str]): ValueStep = actionStep("native", List(op).concat(args))
  pure def mark(tag: str, s: ValueStep): ValueStep = { ...s, tag: tag }
  pure def expectError(s: ValueStep, status: str, detail: str): ValueStep =
    { ...s, want: status, message: detail }
  pure def denied(s: ValueStep, detail: str): ValueStep = expectError(s, "BuiltinError", detail)

  pure def putBinding(source: str, alias: str): ValueStep = actionStep("binding_put", List("setup", source, alias))
  pure val emptyBinding = putBinding("dml://source/builtin/map/empty/v1", "empty")
  pure val insertBinding = putBinding("dml://source/builtin/map/insert/v1", "insert")
  pure val get1Binding = putBinding("dml://source/builtin/map/get/v1", "get1")
  pure val get2Binding = putBinding("dml://source/builtin/map/get/v2", "get2")
  pure val indexBinding = putBinding("dml://source/builtin/list/get/v1", "index")
  pure val mapEmpty = "dml://builtin/map/empty"
  pure val mapInsert = "dml://builtin/map/insert"
  pure val mapSelect = "dml://builtin/map/get"
  pure val operationBindings = List(get1Binding, indexBinding)

  pure def setup(steps: List[ValueStep]): List[ValueStep] = List(
    native("repo_open", List("repo", "create")), native("txn_begin", List("repo", "write", "setup")))
    .concat(steps).append(native("txn_commit", List("setup")))
  pure val start = List(native("txn_begin", List("repo", "write", "tx")),
    actionStep("rec_new", List("tx", "r")), actionStep("rec_enter", List("r")))
  pure val exit = actionStep("rec_exit", List("r"))
  pure val keep = List(exit, native("txn_commit", List("tx")))
  pure val abortedCommit = expectError(native("txn_commit", List("tx")), "invalid_argument", "transaction is null")
  pure val caughtAbort = List(denied(exit, "caught error poisoned builtin recording scope"), abortedCommit)
  pure val checkpoint = actionStep("checkpoint", List("repo", "before"))
  pure val compare = mark("rollback", actionStep("compare", List("repo", "before")))
  pure val readStart = native("txn_begin", List("repo", "read", "rd"))
  pure val close = native("repo_close", List("repo"))
  pure val readStop = native("txn_abort", List("rd"))
  pure val readEnd = List(readStop, close)

  pure def lit(kind: str, typed: str, node: str): ValueStep = actionStep("rec_literal", List("r", kind, typed, node))
  pure def args(node: str, entries: List[str]): ValueStep = actionStep("rec_args", List("r", node).concat(entries))
  pure def call(func: str, binding: str, arguments: str, node: str): ValueStep =
    actionStep("rec_call", List("r", func, binding, arguments, node))
  pure val ops = actionStep("rec_ops", List("r", "get1", "index", "ops"))
  pure def mapGet(container: str, key: str, out: str): ValueStep =
    actionStep("ops_map_get", List("ops", container, key, out))
  pure def listGet(container: str, index: str, out: str): ValueStep =
    actionStep("ops_list_get", List("ops", container, index, out))
  pure def logicalLiteral(kind: str, typed: str, out: str): ValueStep =
    actionStep("ops_literal", List("ops", kind, typed, out))
  pure def dag(node: str, id: str): ValueStep = mark(id, actionStep("rec_dag", List("r", node, id)))
  pure def inspect(txn: str, method: str, id: str, tag: str): ValueStep =
    mark(tag, actionStep("inspect", List(txn, method, id)))
  pure def storeI64(txn: str, n: str, id: str): List[ValueStep] = List(
    native("datum_encode", List("i64", n, "packed-i64")),
    mark(id, native("txn_put_datum", List(txn, "packed-i64", id))))
  pure def getDag(txn: str, id: str): ValueStep = native("txn_get_object", List(txn, "dag", id, "dag-packed"))
  pure def missingDag(id: str): ValueStep =
    expectError(getDag("rd", id), "not_found", "immutable object was not found")
  pure def target(container: str, slot: str, id: str): List[ValueStep] = List(
    native("txn_lookup_node", List("tx", container, slot, "node")),
    native("txn_get_object", List("tx", "node", "node", "node-packed")),
    mark(id, native("object_decode", List("node-packed", id))))

  // One real invalid call per scope, so no failure can be explained by earlier poison.
  pure val wrongNames = setup(List(emptyBinding)).concat(start).concat(List(
    lit("i64", "int:0", "zero"), args("args", List("text:extra", "zero")),
    denied(call(mapEmpty, "empty", "args", "bad"), "builtin exact argument names differ")))
    .concat(caughtAbort).append(close)
  pure def mapShape(kind: str, typed: str, detail: str): List[ValueStep] =
    setup(operationBindings).concat(start).concat(List(ops, lit(kind, typed, "container"),
      denied(mapGet("container", "text:absent", "bad"), detail))).concat(caughtAbort).append(close)
  pure def get2Shape(keyKind: str, key: str, detail: str): List[ValueStep] =
    setup(List(get2Binding)).concat(start).concat(List(lit("map", "ids:", "container"),
      lit(keyKind, key, "key"), args("args", List("text:map", "container", "text:key", "key")),
      denied(call(mapSelect, "get2", "args", "bad"), detail))).concat(caughtAbort).append(close)
  pure def badIndex(index: str, detail: str): List[ValueStep] =
    setup(operationBindings.concat(storeI64("setup", "5", "member"))).concat(start).concat(List(
      lit("list", "ids:member", "container"), ops, denied(listGet("container", index, "bad"), detail)))
      .concat(caughtAbort).append(close)

  pure val decomposed = "hex:63616665cc81"
  pure val composed = "hex:636166c3a9"
  pure val nfcArguments = setup(List()).concat(start).concat(List(
    lit("i64", "int:0", "zero"), dag("zero", "zero-dag"),
    args("good", List(decomposed, "zero")), dag("good", "one-arg"),
    inspect("tx", "arguments", "one-arg", "one-arg-read"),
    denied(args("bad", List(decomposed, "zero", composed, "zero")), "duplicate canonical argument key")))
    .concat(caughtAbort).append(close)
  pure val nfcInsert = setup(List(insertBinding, get1Binding)).concat(start)
    .concat(storeI64("tx", "3", "old-value"))
    .concat(List(lit("string", composed, "canonical"), dag("canonical", "canonical-key")))
    .concat(target("canonical-key", "value", "key-datum"))
    .concat(List(lit("map", "ids:key-datum,old-value", "map"), lit("string", decomposed, "key"),
      dag("key", "decomposed-key"), args("lookup", List("text:map", "map", "text:key", "key")),
      mark("old-value-found", call(mapSelect, "get1", "lookup", "found")), lit("i64", "int:9", "new-value"),
      args("insert-args", List("text:map", "map", "text:key", "key", "text:value", "new-value")),
      denied(call(mapInsert, "insert", "insert-args", "bad"), "duplicate canonical key")))
    .concat(caughtAbort).append(close)

  pure val caughtConversion = setup(List(emptyBinding).concat(operationBindings)).append(checkpoint).concat(start)
    .concat(List(args("none", List()), dag("none", "empty-args"), call(mapEmpty, "empty", "none", "empty"),
      dag("empty", "empty-dag"), inspect("tx", "operation", "empty-dag", "empty-written"),
      native("object_encode", List("tree", "primitive", "empty-dag", "tree-packed")),
      native("txn_put_object", List("tx", "tree", "tree-packed", "tree")),
      native("object_encode", List("commit", "tree", "commit-packed")),
      mark("publication", native("txn_put_object", List("tx", "commit", "commit-packed", "publication"))),
      native("txn_ref_create", List("tx", "partial", "publication")),
      getDag("tx", "empty-dag"), getDag("tx", "empty-args"),
      native("txn_get_object", List("tx", "commit", "publication", "staged-commit")),
      mark("staged-ref", native("txn_ref_get", List("tx", "partial", "staged-ref"))), ops,
      expectError(mapGet("empty", "none", "bad"), "TypeError", "expected bytes, NoneType found"),
      denied(actionStep("rec_trace", List("r", "bad-trace")), "builtin recording scope is inactive or poisoned")))
    .concat(caughtAbort).concat(List(compare, readStart, missingDag("empty-dag"), missingDag("empty-args"),
      expectError(native("txn_get_object", List("rd", "commit", "publication", "rolled-back-commit")),
        "not_found", "immutable object was not found"),
      expectError(native("txn_ref_get", List("rd", "partial", "rolled-back-ref")), "not_found", "ref was not found")))
    .concat(readEnd)

  pure val getItem = List(lit("list", "ids:member", "list"), args("input", List("text:items", "list")), ops,
    mark("map-result", mapGet("input", "text:items", "selected-list")),
    mark("indexed", listGet("selected-list", "int:0", "item")),
    mark("returned", actionStep("rec_return", List("r", "item", "input", "return"))),
    dag("input", "inputs"), dag("selected-list", "map-dag"), dag("item", "index-dag"), dag("return", "return-dag"))
  pure val lateDags = List("map-args", "index-args", "inputs", "map-dag", "index-dag", "trace-dag", "return-dag")
  pure val lateFailure = setup(operationBindings).append(checkpoint).concat(start).concat(storeI64("tx", "743", "member"))
    .concat(getItem)
    .concat(target("map-dag", "arguments", "map-args"))
    .concat(target("index-dag", "arguments", "index-args"))
    .concat(target("return-dag", "trace", "trace-dag"))
    .concat(lateDags.foldl(List(), (out, id) => out.append(getDag("tx", id))))
    .append(inspect("tx", "returned", "return-dag", "staged-return"))
    .append(expectError(actionStep("rec_exit", List("r", "deliberate late failure")), "RuntimeError", "deliberate late failure"))
    .append(abortedCommit).append(compare).append(readStart)
    .concat(lateDags.foldl(List(), (out, id) => out.append(missingDag(id)))).concat(readEnd)

  pure val noNativeLiteral = setup(operationBindings.concat(storeI64("setup", "321", "known")))
    .append(checkpoint).concat(start).concat(List(ops, logicalLiteral("i64", "int:42", "value"),
      dag("value", "partial"), getDag("tx", "partial"),
      denied(logicalLiteral("list", "ids:known", "bad"), "logical literal requires I64 or STRING, not native IDs")))
    .concat(caughtAbort).concat(List(compare, readStart, missingDag("partial"),
      native("txn_get_datum", List("rd", "known", "known-packed")),
      mark("known-read", native("datum_decode", List("known-packed"))))).concat(readEnd)

  // Format-v1 packed canonical F64 NaN; do not round-trip through a Python float.
  pure val packedNan = "444d4c31010002003000000000000000000000000400000008000000000000002800000000000000000000000000f87f"
  pure val nan = setup(operationBindings).concat(start).append(
      mark("member", native("txn_put_datum", List("tx", packedNan, "member"))))
    .concat(getItem).concat(keep).append(checkpoint).append(readStart)
    .concat(List(inspect("rd", "returned", "return-dag", "nan-read"),
      mark("nan-packed", native("txn_get_datum", List("rd", "member", "nan-packed")))))
    .append(readStop).append(compare).append(close)

  pure val positionCalls = range(0, 16).foldl(List(args("args", List())), (out, _) =>
    out.append(call(mapEmpty, "empty", "args", "call")))
  pure val positions = setup(List(emptyBinding)).concat(start).concat(positionCalls).concat(List(
      dag("call", "operation"), actionStep("rec_trace", List("r", "trace"))))
    .concat(keep).append(readStart).append(inspect("rd", "trace", "trace", "positions-read"))
    .append(readStop).append(checkpoint).concat(start).concat(positionCalls).append(
      denied(call(mapEmpty, "empty", "args", "bad"), "builtin call position limit exceeded"))
    .concat(caughtAbort).append(compare).append(close)
  pure val argPairs = List("text:0", "text:1", "text:2", "text:3", "text:4", "text:5", "text:6", "text:7", "text:8",
    "text:9", "text:10", "text:11", "text:12", "text:13", "text:14", "text:15")
    .foldl(List(), (out, key) => out.append(key).append("value"))
  pure val argumentCounts = setup(List()).concat(start).concat(List(lit("i64", "int:0", "value"), dag("value", "zero-dag"),
      args("args", argPairs), dag("args", "arguments-16"), inspect("tx", "arguments", "arguments-16", "arguments-read")))
    .concat(keep).append(checkpoint).concat(start).concat(List(lit("i64", "int:0", "value"),
      denied(args("bad", argPairs.append("text:16").append("value")), "builtin argument limit exceeded")))
    .concat(caughtAbort).append(compare).append(close)
  pure val literals = List(
    "int:1000", "int:1001", "int:1002", "int:1003", "int:1004", "int:1005", "int:1006", "int:1007",
    "int:1008", "int:1009", "int:1010", "int:1011", "int:1012", "int:1013", "int:1014", "int:1015",
    "int:1016", "int:1017", "int:1018", "int:1019", "int:1020", "int:1021", "int:1022", "int:1023",
    "int:1024", "int:1025", "int:1026", "int:1027", "int:1028", "int:1029", "int:1030", "int:1031",
    "int:1032", "int:1033", "int:1034", "int:1035", "int:1036", "int:1037", "int:1038", "int:1039",
    "int:1040", "int:1041", "int:1042", "int:1043", "int:1044", "int:1045", "int:1046", "int:1047",
    "int:1048", "int:1049", "int:1050", "int:1051", "int:1052", "int:1053", "int:1054", "int:1055",
    "int:1056", "int:1057", "int:1058", "int:1059", "int:1060", "int:1061", "int:1062", "int:1063")
  pure val profileCount = setup(List()).append(checkpoint).concat(start)
    .concat(literals.foldl(List(), (out, typed) => out.append(lit("i64", typed, "value")).append(dag("value", "literal"))))
    .concat(List(lit("i64", "int:1063", "again"), dag("again", "again-dag"),
      denied(lit("i64", "int:1064", "bad"), "builtin reached profile limit exceeded")))
    .concat(caughtAbort).append(compare).append(readStart).append(missingDag("literal")).concat(readEnd)

  pure val valueCases: List[List[ValueStep]] = List(
    wrongNames, mapShape("map", "ids:", "missing MAP key"), get2Shape("string", "text:absent", "missing MAP key"),
    mapShape("i64", "int:0", "expected a MAP container"), get2Shape("i64", "int:0", "builtin key must be STRING"),
    badIndex("int:-1", "LIST index out of range"), badIndex("int:1", "LIST index out of range"),
    badIndex("bool:true", "I64 literal requires an integer, not coercion"),
    badIndex("float:0.0", "I64 literal requires an integer, not coercion"),
    nfcArguments, nfcInsert, caughtConversion, lateFailure, noNativeLiteral, nan, positions, argumentCounts, profileCount)
  pure val valueHistories: List[List[ValueRequest]] = valueCases.foldl(List(), (out, steps) =>
    out.append(steps.foldl(List(), (requests, s) => requests.append(s.request))))
}
