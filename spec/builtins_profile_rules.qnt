module builtins_profile_rules {
  import builtin_primitive_evidence.* from "./builtin_primitive_evidence"
  import builtins_profile_histories as story from "./builtins_profile_histories"

  pure def out(rows: List[Attempt], op: str, alias: str): Attempt =
    rows.foldl(rows[0], (found, a) => if (a.op == op and a.args[a.args.length() - 1] == alias) a else found)
  pure def nativeOut(rows: List[Attempt], op: str, alias: str): Attempt =
    rows.foldl(rows[0], (found, a) =>
      if (a.op == "native" and a.args[0] == op and a.args[a.args.length() - 1] == alias) a else found)
  pure def sameValue(a: Attempt, b: Attempt): bool =
    a.datumKind != 0 and a.datumKind == b.datumKind and a.datumPayload == b.datumPayload
  pure def exactEdge(actual: str, expected: str): bool = actual != "" and actual == expected
  pure def exactEntry(events: List[str], name: str): bool = events == List(name)
  pure def exactError(a: Attempt, reason: str): bool = a.status == "BuiltinError" and a.error == reason

  pure def expectedCall(rows: List[Attempt], o: story::GraphOperation): Call = {
    pure def dag(alias: str): str = out(rows, "rec_dag", alias).value
    { dag: dag(o.dag), func: o.func, binding: out(rows, "binding_put", o.binding).value, sourceUri: o.source,
      inputs: dag(o.args), entries: o.entries.foldl(List(), (entries, e) => entries.append({ name: e._1, id: dag(e._2) })) }
  }
  pure def graphReturn(rows: List[Attempt], a: Attempt): bool = {
    val ids = story::graphOperations.foldl(List(), (ordered, o) => ordered.append(out(rows, "rec_dag", o.dag).value))
    all {
      a.value != "", a.value == out(rows, "rec_dag", "result-dag").value,
      a.inputs == out(rows, "rec_dag", "get-input-dag").value, a.returned == ids[5], a.trace == ids,
      ids.foldl(Set(), (seen, id) => seen.union(Set(id))).size() == 6, a.events == [],
      a.datumKind == 3, a.datumPayload == "2a00000000000000",
      a.datum == nativeOut(rows, "txn_put_datum", "answer-datum").value,
      sameValue(a, out(rows, "rec_call", "answer")),
      sameValue(out(rows, "rec_source", "left-source"), out(rows, "rec_source", "right-source")),
      sameValue(out(rows, "rec_call", "map-left"), out(rows, "rec_call", "map-right")),
      sameValue(out(rows, "rec_call_observed", "get1"), out(rows, "rec_call_observed", "get2"))
    }
  }
  pure def graphStep(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    if (a.op == "rec_call_observed") {
      val handler = if (a.args[2] == "get1-binding") "_map_get_v1" else "_map_get_v2"
      if (exactEntry(a.events, handler)) "ok" else "wrong_handler_entry"
    } else if (a.op == "inspect_offline") {
      val expected = story::graphOperations.foldl(List(), (calls, o) => calls.append(expectedCall(rows, o)))
      if (not(graphReturn(rows, a))) "wrong_stored_return_graph"
      else if (a.calls != expected) "wrong_reported_trace_arguments"
      else "ok"
    } else if (a.op == "inspect" and a.args[1] == "node") {
      val origin = if (a.args[2] == "left-source-dag") "left" else "right"
      if (a.value == out(rows, "rec_dag", a.args[2]).value and a.name == "6974656d"
          and a.sourceDag == nativeOut(rows, "txn_put_object", origin).value
          and a.sourceNode == nativeOut(rows, "txn_put_object", "list-node").value
          and nativeOut(rows, "txn_put_object", "left").value != nativeOut(rows, "txn_put_object", "right").value)
        "ok" else "wrong_named_source"
    } else if (a.op == "inspect" and a.args[1] == "arguments") {
      if (a.value == out(rows, "rec_dag", "none-dag").value and a.entries == []) "ok" else "nonempty_arguments"
    } else if (a.op == "inspect" and a.args[1] == "operation") {
      val o = story::graphOperations.foldl(story::graphOperations[0], (found, o) => if (a.args[2] == o.dag) o else found)
      val expected = expectedCall(rows, o)
      if (a.value != "" and { dag: a.value, func: a.func, binding: a.binding, sourceUri: a.sourceUri,
          inputs: a.inputs, entries: a.entries } == expected) "ok" else "wrong_stored_operation"
    } else if (a.op == "native" and a.args[0] == "object_encode" and a.args[4] == "expected-edge") {
      if (exactEdge(rows[i - 1].value, a.value)) "ok" else "wrong_native_subdag_edge"
    } else if (a.op == "rec_call" and a.args[1] == story::emptyFunc) {
      val expected = nativeOut(rows, "datum_decode", "empty-map-packed")
      if (a.datumKind == 10 and a.datumKind == expected.count and a.datumPayload == expected.value) "ok"
      else "wrong_empty_map"
    } else "ok"
  }
  pure def profileExpected(scenario: int, a: Attempt): str = {
    if ((scenario == 1 or scenario == 2) and a.op == "rec_call") "unsupported builtin func/source pairing"
    else if ((scenario == 1 or scenario == 2) and a.op == "rec_exit") "caught error poisoned builtin recording scope"
    else if (scenario == 3 and a.op == "inspect")
      story::badBindings.foldl("", (reason, b) => if (a.args[2] == b._1) b._5 else reason)
    else if (scenario == 4 and a.op == "inspect")
      story::lies.foldl("", (reason, l) => if (a.args[2] == l._4) l._5 else reason)
    else ""
  }
  pure def malformedBinding(rows: List[Attempt], a: Attempt): str = {
    val canonical = out(rows, "binding_put", "valid-binding").value
    val stored = nativeOut(rows, "txn_put_object", a.args[2]).value
    if (a.args[2] == "native-binding") {
      if (canonical != "" and a.value == canonical and stored == canonical and a.sourceUri == story::get1Uri)
        "ok" else "wrong_valid_binding"
    } else if (stored != "" and stored != canonical) "ok" else "missing_malformed_binding"
  }
  pure def persistedLie(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val r = story::lies.foldl(story::lies[0], (found, l) => if (a.args[2] == l._1 or a.args[2] == l._4) l else found)
    val valid = out(rows, "rec_dag", r._1).value
    if (a.args[2] == r._1) {
      if (a.value != "" and a.value == valid) "ok" else "wrong_valid_counterpart"
    } else {
      val forged = nativeOut(rows, "txn_put_object", r._4).value
      val replacement = nativeOut(rows, "txn_put_object", r._3).value
      val stored = rows[i - 1].value
      if (forged != "" and forged != valid and stored != "" and stored == replacement) "ok" else "wrong_forged_record"
    }
  }
  pure def profileStep(scenario: int, rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val r = story::profileHistories[scenario][i]
    val expected = profileExpected(scenario, a)
    if (a.op != r.op or a.args != r.args) "wrong_request"
    else if (expected != "" and not(exactError(a, expected))) "wrong_profile_rejection"
    else if (expected == "" and not(accepted(a))) "unexpected_failure"
    else if (a.op == "compare" and not(a.unchanged)) "changed_committed_inventory"
    else if (scenario == 0) graphStep(rows, i)
    else if ((scenario == 1 or scenario == 2) and a.op == "inspect") {
      val uri = if (scenario == 1) story::unknownUri else story::listUri
      if (a.value != "" and a.value == out(rows, "binding_put", "candidate").value and a.sourceUri == uri)
        "ok" else "wrong_inspectable_binding"
    } else if (scenario == 3 and a.op == "inspect") malformedBinding(rows, a)
    else if (scenario == 4 and a.op == "inspect") persistedLie(rows, i)
    else "ok"
  }
  pure def profileVerdicts(scenario: int, rows: List[Attempt]): List[str] =
    if (rows.length() != story::profileHistories[scenario].length()) List("missing_profile_steps")
    else range(0, rows.length()).foldl(List(), (out, i) => out.append(profileStep(scenario, rows, i)))

  pure val profileControls = exactEdge("aa", "aa") and not(exactEdge("", "")) and not(exactEdge("aa", "bb"))
    and exactEntry(List("_map_get_v2"), "_map_get_v2") and not(exactEntry(List("_map_get_v1"), "_map_get_v2"))
    and not(exactEntry(List("_map_get_v1", "_map_get_v2"), "_map_get_v2"))
}
