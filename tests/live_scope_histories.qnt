module live_scope_histories {
  import builtin_primitive_fixture.* from "./builtin_primitive_fixture"

  type Step = { request: Request, tag: str, want: str, message: str }
  pure def tagged(request: Request, tag: str): Step = { request: request, tag: tag, want: "ok", message: "" }
  pure def requestStep(op: str, args: List[str]): Step = tagged(req(op, args), "")
  pure def observe(op: str, args: List[str], tag: str): Step = tagged(req(op, args), tag)
  pure def reject(s: Step, want: str, message: str): Step = s.with("want", want).with("message", message)
  pure def plain(requests: List[Request]): List[Step] = requests.foldl(List(), (out, r) => out.append(tagged(r, "")))

  pure val callPoison = "caught error poisoned call scope"
  pure val callInactive = "call scope is foreign, inactive or poisoned"
  pure val callUnbound = "foreign or unbound call target"
  pure val recPoison = "caught error poisoned builtin recording scope"
  pure val recInactive = "builtin recording scope is inactive or poisoned"
  pure val recReentered = "builtin recording scope cannot be reentered"
  pure val getter2 = "dml://source/builtin/map/get/v2"
  pure val mapGet = "dml://builtin/map/get"
  pure val getter1 = "dml://source/builtin/map/get/v1"
  pure val listGet = "dml://source/builtin/list/get/v1"
  pure val unsupported = "dml://source/builtin/map/get/unsupported"
  pure val intent = "urn:dml:test:double"
  pure val implementation = "urn:dml:test:double:v2"

  pure val local = List(
    tagged(native("datum_encode", List("map", "empty-map")), ""),
    requestStep("node_from_datum", List("empty-map", "seed")),
    requestStep("call_enter", List("scope")),
    requestStep("call_copy", List("scope", "seed", "local")),
    observe("node_value", List("local"), "local"))
  pure val nested = local.concat(List(
    requestStep("call_bind", List("scope", "leaf", "argument")),
    requestStep("call_bind", List("scope", "outer", "argument", "leaf")),
    observe("call_invoke", List("scope", "outer", "local", "result"), "nested"),
    requestStep("call_unbind", List("outer")), requestStep("call_unbind", List("leaf")),
    requestStep("call_exit", List("scope")),
    observe("node_value", List("result"), "same-local"),
    reject(observe("call_invoke", List("scope", "outer", "local", "invalid"), "no-entry"), "CallError", callInactive)))

  pure def rejectedOwnership(fabricated: bool): List[Step] = local.concat(List(
    requestStep("call_enter", List("second")), requestStep("call_copy", List("second", "seed", "foreign")),
    observe("node_value", List("foreign"), "equal-local"),
    requestStep("node_fabricate", List("call", "local", "fake")),
    observe("node_value", List("fake"), "equal-local"),
    requestStep("call_bind", List("scope", "target", if (fabricated) "local" else "foreign")),
    reject(observe("call_invoke", List("scope", "target", if (fabricated) "fake" else "local", "invalid"),
      if (fabricated) "no-entry" else "entered-local"), "CallError",
      if (fabricated) "invocation requires an owned argument MAP node" else "invocation returned a foreign node"),
    requestStep("call_unbind", List("target")), requestStep("call_exit", List("second")),
    reject(requestStep("call_exit", List("scope")), "CallError", callPoison)))

  pure val expired = local.concat(List(
    requestStep("call_bind", List("scope", "expired", "argument")), requestStep("call_unbind", List("expired")),
    requestStep("call_bind", List("scope", "catcher", "argument", "expired", "catch")),
    reject(observe("call_invoke", List("scope", "catcher", "local", "invalid"), "caught-expired"), "CallError", callInactive),
    requestStep("call_unbind", List("catcher")), reject(requestStep("call_exit", List("scope")), "CallError", callPoison)))

  pure val affine = local.concat(List(
    requestStep("call_bind", List("scope", "target", "argument")),
    reject(observe("call_invoke", List("scope", "target", "local", "invalid", "worker"), "no-entry"), "CallError", callInactive),
    observe("call_invoke", List("scope", "target", "local", "result"), "owner-entered"),
    requestStep("call_unbind", List("target")), requestStep("call_exit", List("scope"))))

  pure val captures = plain(writer).concat(List(
    tagged(binding(unsupported, "getter"), "getter"),
    observe("closure_put", List("snapshot", intent, implementation, "closure", "get", "getter"), "closure"),
    observe("closure_inspect", List("snapshot", "closure", "get"), "capture"),
    tagged(inspect("binding", "getter"), "unsupported"),
    reject(requestStep("closure_inspect", List("snapshot", "closure")), "BuiltinError", "builtin profile has wrong binding count"),
    reject(requestStep("closure_inspect", List("snapshot", "closure", "wrong")), "BuiltinError", "missing builtin profile field b'wrong'"),
    reject(requestStep("closure_put", List("snapshot", intent, implementation, "invalid", "intent", "getter")),
      "CallError", "closure capture names must be bytes and may not shadow metadata")))
    .concat(List(tagged(lookup("closure", "get", "edge-node"), ""),
      tagged(native("txn_get_object", List("snapshot", "node", "edge-node", "actual-edge")), "actual-edge"),
      tagged(native("object_encode", List("node", "subdag", "getter", "expected-edge")), "capture-edge")))
    .concat(plain(close("txn_commit")))

  pure def builtinTarget(copy: bool): List[Step] = plain(writer).concat(List(
    tagged(binding(getter2, "getter"), "getter"),
    requestStep("rec_new", List("snapshot", "rec")), requestStep("rec_enter", List("rec")),
    requestStep("rec_literal", List("rec", "i64", "int:42", "answer")),
    requestStep("rec_args", List("rec", "map", "text:x", "answer")),
    requestStep("rec_literal", List("rec", "string", "text:x", "key")),
    requestStep("rec_args", List("rec", "prepared", "text:map", "map", "text:key", "key"))))
    .concat(List(observe("rec_dag", List("rec", "prepared", "prepared-dag"), "prepared-dag"),
      requestStep("call_enter", List("scope")),
      requestStep("call_bind_builtin", List("scope", "target", "rec", mapGet, "getter", "prepared", "arg"))))
    .concat(if (copy) List(
      observe("node_value", List("arg"), "prepared"),
      requestStep("call_copy", List("scope", "arg", "copy")),
      observe("node_value", List("copy"), "equal-prepared"),
      reject(requestStep("call_invoke", List("scope", "target", "copy", "invalid")), "CallError",
        "builtin call requires its exact prepared argument node"))
      else List(observe("call_invoke", List("scope", "target", "arg", "result"), "i64-42")))
    .concat(List(requestStep("call_unbind", List("target")),
      if (copy) reject(requestStep("call_exit", List("scope")), "CallError", callPoison) else requestStep("call_exit", List("scope")),
      requestStep("rec_trace", List("rec", "trace")), tagged(inspect("trace", "trace"), if (copy) "trace-empty" else "trace-one"),
      requestStep("rec_exit", List("rec"))))
    .concat(plain(close("txn_commit")))

  pure val opaque = plain(writer.concat(List(binding(getter1, "getter"), binding(listGet, "list")))
    .concat(putDatum("i64", List("42"), "item"))).concat(List(
    requestStep("rec_new", List("snapshot", "rec")), requestStep("rec_enter", List("rec")),
    requestStep("rec_literal", List("rec", "list", "ids:item", "source")),
    requestStep("rec_ops", List("rec", "getter", "list", "ops")),
    observe("ops_list_get", List("ops", "source", "int:0", "answer"), "i64-42"),
    reject(requestStep("node_set_value", List("answer", "source")), "AttributeError", ""),
    observe("node_has_attr", List("answer", "dag"), "opaque"),
    requestStep("rec_exit", List("rec"))))
    .concat(plain(close("txn_commit"))).concat(List(
      observe("node_value", List("answer"), "i64-42"),
      reject(requestStep("rec_dag", List("rec", "answer", "invalid")), "BuiltinError", recInactive)))

  pure val existingWriter = List(native("repo_open", List("source", "existing")), native("txn_begin", List("source", "write", "snapshot")))
  pure val abortedCommit = reject(tagged(native("txn_commit", List("snapshot")), ""), "invalid_argument", "transaction is null")
  pure def rejectedSource(alias: str): List[Step] = plain(existingWriter).concat(List(
    requestStep("rec_new", List("snapshot", "rec")), requestStep("rec_enter", List("rec")),
    reject(requestStep("rec_args", List("rec", "invalid", "text:value", alias)), "BuiltinError", "foreign or fabricated builtin value node"),
    reject(requestStep("rec_exit", List("rec")), "BuiltinError", recPoison),
    abortedCommit, tagged(native("repo_close", List("source")), "")))
  pure val sources = plain(writer).concat(List(
    requestStep("rec_new", List("snapshot", "rec")), requestStep("rec_enter", List("rec")),
    requestStep("rec_literal", List("rec", "i64", "int:17", "old")),
    observe("rec_dag", List("rec", "old", "old-dag"), "old-dag"),
    requestStep("rec_exit", List("rec"))))
    .concat(plain(close("txn_commit"))).concat(List(
      observe("node_value", List("old"), "old"),
      requestStep("node_fabricate", List("recorder", "old", "fake")),
      observe("node_value", List("fake"), "equal-old")))
    .concat(rejectedSource("old")).concat(rejectedSource("fake"))
    .concat(plain(existingWriter)).concat(List(
      requestStep("rec_new", List("snapshot", "rec")), requestStep("rec_enter", List("rec")),
      observe("rec_load", List("rec", "old-dag", "loaded"), "i64-17"),
      observe("node_value", List("loaded"), "equal-old"),
      observe("rec_dag", List("rec", "loaded", "loaded-dag"), "loaded-dag"),
      requestStep("rec_exit", List("rec"))))
    .concat(plain(close("txn_commit")))

  pure val recorder = plain(writer).concat(List(
    requestStep("checkpoint", List("source", "before")),
    requestStep("rec_new", List("snapshot", "rec")),
    reject(requestStep("rec_literal", List("rec", "i64", "int:29", "invalid")), "BuiltinError", recInactive),
    requestStep("rec_enter", List("rec")), requestStep("rec_literal", List("rec", "i64", "int:29", "node")),
    observe("rec_dag", List("rec", "node", "staged"), "staged"),
    tagged(native("txn_get_object", List("snapshot", "dag", "staged", "packed")), "staged-present"),
    reject(requestStep("rec_enter", List("rec")), "BuiltinError", recReentered),
    reject(requestStep("rec_exit", List("rec")), "BuiltinError", recPoison),
    abortedCommit, tagged(native("repo_close", List("source")), ""),
    observe("compare", List("source", "before"), "unchanged")))
    .concat(plain(reader)).concat(List(
      reject(tagged(native("txn_get_object", List("snapshot", "dag", "staged", "missing")), ""),
        "not_found", "immutable object was not found")))
    .concat(plain(close("txn_abort"))).concat(List(reject(requestStep("rec_enter", List("rec")), "BuiltinError", recReentered)))

  pure val cases = List(nested, rejectedOwnership(true), rejectedOwnership(false), expired, affine, captures,
    builtinTarget(false), builtinTarget(true), opaque, sources, recorder)
  pure val requested = cases.foldl(List(), (out, story) =>
    out.append(story.foldl(List(), (requests, s) => requests.append(s.request))))
  var histories: List[List[Request]]
  action init = histories' = requested
  action step = histories' = histories
}
