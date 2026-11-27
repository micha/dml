module builtins_values_rules {
  import builtin_primitive_evidence.* from "./builtin_primitive_evidence"
  import builtins_values_histories as h from "./builtins_values_histories"

  pure def distinctDags(ids: List[str], n: int): bool = {
    val unique = ids.foldl(Set(), (out, id) => out.union(Set(id)))
    ids.length() == n and unique.size() == n and not(unique.contains(""))
  }
  pure def repeatedTrace(trace: List[str], operation: str): bool =
    operation != "" and trace.length() == 16 and trace.foldl(true, (ok, id) => ok and id == operation)
  pure def exactDatum(a: Attempt, expectedKind: int, expectedPayload: str): bool =
    a.datumKind == expectedKind and a.datumPayload == expectedPayload
  pure def exactNan(id: str, expected: str, kind: int, payload: str): bool =
    expected != "" and id == expected and kind == 4 and payload == "000000000000f87f"
  pure def returnPath(a: Attempt, wrapper: str, inputs: str, mapDag: str, indexDag: str): bool =
    a.value == wrapper and a.inputs == inputs and a.returned == indexDag and a.trace == List(mapDag, indexDag)

  pure val nativeValues = Set("datum_encode", "datum_decode", "txn_put_datum", "txn_get_datum", "object_encode",
    "txn_put_object", "txn_get_object", "txn_ref_get", "txn_lookup_node", "object_decode")
  pure def valueShape(a: Attempt): bool =
    if (Set("binding_put", "rec_dag", "rec_trace").contains(a.op) or
      (a.op == "native" and nativeValues.contains(a.args[0]))) a.value != ""
    else true

  pure def taggedVerdict(tag: str, a: Attempt, observed: str => Attempt, literalDags: List[str]): str = {
    def id(alias: str): str = observed(alias).value
    if (tag == "rollback") {
      if (a.unchanged) "ok" else "native_inventory_changed"
    } else if (tag == "one-arg-read") {
      if (a.value == id("one-arg") and a.datumKind == 10 and
          a.entries == List({ name: "636166c3a9", id: id("zero-dag") })) "ok" else "argument_key_not_canonical"
    } else if (tag == "decomposed-key") {
      if (a.value == id("canonical-key")) "ok" else "literal_key_not_canonical"
    } else if (tag == "old-value-found") {
      if (exactDatum(a, 3, "0300000000000000")) "ok" else "canonical_key_did_not_select_old_entry"
    } else if (tag == "empty-written") {
      if (a.value == id("empty-dag") and a.inputs == id("empty-args") and a.datumKind == 10)
        "ok" else "wrong_staged_operation"
    } else if (tag == "staged-ref") {
      if (a.value == id("publication")) "ok" else "wrong_staged_ref"
    } else if (tag == "staged-return") {
      val staged = h::lateDags.foldl(List(), (out, alias) => out.append(id(alias)))
      if (distinctDags(staged, 7) and returnPath(a, id("return-dag"), id("inputs"), id("map-dag"), id("index-dag"))
          and a.datum == id("member") and exactDatum(a, 3, "e702000000000000")) "ok" else "wrong_staged_return_graph"
    } else if (tag == "known-read") {
      if (a.count == 3 and a.value == "4101000000000000") "ok" else "wrong_known_member"
    } else if (tag == "nan-read") {
      if (exactNan(a.datum, id("member"), a.datumKind, a.datumPayload) and
          returnPath(a, id("return-dag"), id("inputs"), id("map-dag"), id("index-dag")) and
          observed("map-result").datumKind == 8 and exactDatum(observed("indexed"), a.datumKind, a.datumPayload) and
          exactDatum(observed("returned"), a.datumKind, a.datumPayload)) "ok" else "wrong_nan_identity_or_payload"
    } else if (tag == "nan-packed") {
      if (a.value == h::packedNan) "ok" else "wrong_packed_nan"
    } else if (tag == "positions-read") {
      if (repeatedTrace(a.trace, id("operation"))) "ok" else "wrong_repeated_trace_positions"
    } else if (tag == "arguments-read") {
      val order = List("30", "31", "3130", "3131", "3132", "3133", "3134", "3135", "32", "33",
        "34", "35", "36", "37", "38", "39")
      val expectedEntries = order.foldl(List(), (out, key) => out.append({ name: key, id: id("zero-dag") }))
      if (a.value == id("arguments-16") and a.entries == expectedEntries) "ok" else "wrong_sixteen_arguments"
    } else if (tag == "again-dag") {
      if (distinctDags(literalDags, 64) and a.value == literalDags[63]) "ok" else "wrong_distinct_profile_accounting"
    } else "ok"
  }

  pure def valueVerdicts(scenario: int, rows: List[Attempt]): List[str] = {
    val steps = h::valueCases[scenario]
    if (rows.length() != steps.length()) List("missing_steps")
    else {
      val tags = steps.indices() // Use list order when gathering repeated tags below.
      val lookup = tags.fold(Map(), (out, i) => out.put(steps[i].tag, rows[i]))
      def seen(tag: str): Attempt = lookup.get(tag)
      val literalDags = range(0, steps.length()).foldl(List(), (out, i) =>
        if (steps[i].tag == "literal") out.append(rows[i].value) else out)
      range(0, steps.length()).foldl(List(), (out, i) => {
        val step = steps[i]
        val a = rows[i]
        val verdict =
          if (a.op != step.request.op or a.args != step.request.args) "wrong_step"
          else if (a.status != step.want or a.error != step.message) "wrong_status_or_diagnostic"
          else if (step.want != "ok") {
            if (a.value == "" and a.datum == "" and a.datumKind == 0) "ok" else "rejection_returned_value"
          } else if (not(valueShape(a))) "missing_native_value"
          else taggedVerdict(step.tag, a, seen, literalDags)
        out.append(verdict)
      })
    }
  }

  pure val exampleTrace = range(0, 16).foldl(List(), (out, _) => out.append("map-empty"))
  pure val valueControls = all {
    distinctDags(List("one", "two"), 2), not(distinctDags(List("one", "one"), 2)),
    repeatedTrace(exampleTrace, "map-empty"), not(repeatedTrace(exampleTrace.append("map-empty"), "map-empty")),
    not(repeatedTrace(exampleTrace.replaceAt(6, "other"), "map-empty")),
    exactNan("nan-id", "nan-id", 4, "000000000000f87f"),
    not(exactNan("other-id", "nan-id", 4, "000000000000f87f")),
    not(exactNan("nan-id", "nan-id", 4, "010000000000f87f")),
  }
}
