module live_scope_rules {
  import builtin_primitive_evidence.* from "./builtin_primitive_evidence"
  export builtin_primitive_evidence.*
  import live_scope_histories as h from "./live_scope_histories"

  type Observation = { scenario: int, attempts: List[Attempt] }
  pure def sameValue(a: Attempt, b: Attempt): bool =
    a.datumKind != 0 and a.datumKind == b.datumKind and a.datumPayload == b.datumPayload
  pure def sameNode(a: Attempt, b: Attempt): bool =
    a.identity != "" and a.identity == b.identity and sameValue(a, b)
  pure def distinctEqualNode(a: Attempt, b: Attempt): bool =
    a.identity != "" and b.identity != "" and a.identity != b.identity and sameValue(a, b)
  pure def exactEntries(entered: List[EntryEvent], targets: List[str], node: str): bool =
    node != "" and entered == targets.foldl(List(), (out, target) => out.append({ target: target, node: node }))
  pure def singleCall(a: Attempt, prepared: str, getter: str): bool =
    if (a.trace.length() != 1 or a.calls.length() != 1) false
    else all {
      a.trace[0] != "", a.calls[0].dag == a.trace[0], prepared != "", getter != "",
      a.calls[0].inputs == prepared, a.calls[0].binding == getter,
      a.calls[0].sourceUri == h::getter2, a.calls[0].func == h::mapGet,
    }
  pure def datumMatches(a: Attempt, kind: int, payload: str): bool =
    a.datumKind == kind and a.datumPayload == payload

  pure def facts(tag: str, a: Attempt, seen: str => Attempt): str = {
    def identity(alias: str): str = seen(alias).identity
    def id(alias: str): str = seen(alias).value
    if (tag == "local") {
      if (a.identity != "" and datumMatches(a, 10, "00000000")) "ok" else "wrong_empty_map"
    } else if (tag == "nested" or tag == "owner-entered") {
      val targets = if (tag == "nested") List("outer", "leaf") else List("target")
      if (sameNode(a, seen("local")) and exactEntries(a.entered, targets, identity("local")) and a.caught == List())
        "ok" else "wrong_adapter_entry_or_identity"
    } else if (tag == "same-local") {
      if (sameNode(a, seen("local"))) "ok" else "wrong_escaped_copy"
    } else if (tag == "equal-local" or tag == "equal-old" or tag == "equal-prepared") {
      val base = if (tag == "equal-local") "local" else if (tag == "equal-prepared") "prepared" else "old"
      if (distinctEqualNode(a, seen(base))) "ok" else "not_distinct_equal_nodes"
    } else if (tag == "no-entry") {
      if (a.entered == List() and a.caught == List()) "ok" else "unexpected_adapter_entry"
    } else if (tag == "entered-local") {
      if (exactEntries(a.entered, List("target"), identity("local")) and a.caught == List())
        "ok" else "wrong_adapter_entry"
    } else if (tag == "caught-expired") {
      if (exactEntries(a.entered, List("catcher"), identity("local")) and a.caught == List(h::callUnbound))
        "ok" else "wrong_nested_rejection"
    } else if (tag == "capture") {
      if (a.value == id("closure") and id("getter") != "" and a.intent == h::intent and a.implementation == h::implementation
          and a.entries == List({ name: "676574", id: id("getter") })) "ok" else "wrong_capture_description"
    } else if (tag == "capture-edge") {
      if (a.value != "" and a.value == id("actual-edge")) "ok" else "wrong_physical_capture"
    } else if (tag == "unsupported") {
      if (a.value == id("getter") and a.sourceUri == h::unsupported) "ok" else "wrong_unsupported_binding"
    } else if (tag == "trace-one") {
      if (singleCall(a, id("prepared-dag"), id("getter"))) "ok" else "wrong_prepared_call"
    } else if (tag == "trace-empty") {
      if (a.trace == List() and a.calls == List()) "ok" else "unexpected_recorded_call"
    } else if (tag == "i64-42") {
      if (datumMatches(a, 3, "2a00000000000000")) "ok" else "wrong_42_value"
    } else if (tag == "i64-17" or tag == "old") {
      if (datumMatches(a, 3, "1100000000000000")) "ok" else "wrong_17_value"
    } else if (tag == "opaque") {
      if (not(a.present)) "ok" else "exposes_dag_attribute"
    } else if (tag == "loaded-dag") {
      if (a.value != "" and a.value == id("old-dag")) "ok" else "wrong_reloaded_dag"
    } else if (tag == "unchanged") {
      if (a.unchanged) "ok" else "changed_committed_inventory"
    } else if (Set("getter", "closure", "prepared-dag", "old-dag", "staged", "staged-present").contains(tag)) {
      if (a.value != "") "ok" else "missing_id_or_record"
    } else "ok"
  }

  pure def historyVerdicts(row: Observation): List[str] = {
    if (row.scenario < 0 or row.scenario >= h::cases.length()) List("unexpected_history")
    else {
      val steps = h::cases[row.scenario]
      val rows = row.attempts
      if (steps.length() != rows.length()) List("missing_steps")
      else {
        val tags = steps.indices().fold(Map(), (out, i) => out.put(steps[i].tag, rows[i]))
        range(0, steps.length()).foldl(List(), (out, i) => {
          val s = steps[i]
          val a = rows[i]
          val verdict = if (a.op != s.request.op or a.args != s.request.args) "wrong_step"
          else if (a.status != s.want or (if (s.want == "AttributeError") a.error == "" else a.error != s.message))
            "wrong_status_or_diagnostic"
          else if (s.want != "ok" and (a.value != "" or a.identity != "" or a.datumKind != 0)) "rejected_step_returned_value"
          else facts(s.tag, a, tag => tags.get(tag))
          out.append(verdict)
        })
      }
    }
  }
  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool = all {
    evidence.length() == h::requested.length(), verdicts.length() == evidence.length(),
    evidence.indices().forall(i => evidence[i].scenario == i and verdicts[i].length() == h::requested[i].length()
      and verdicts[i].foldl(true, (ok, verdict) => ok and verdictAccepted(verdict))),
  }
  pure val exampleEntries = List({ target: "outer", node: "one" }, { target: "leaf", node: "one" })
  pure val controlsPass = all {
    exactEntries(exampleEntries, List("outer", "leaf"), "one"),
    not(exactEntries(exampleEntries, List("leaf", "outer"), "one")),
    not(exactEntries(exampleEntries, List("outer", "leaf"), "two")),
  }
}
