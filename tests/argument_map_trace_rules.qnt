module argument_map_trace_rules {
  import argument_map_trace_histories.* from "./argument_map_trace_histories"

  type Ref = { name: str, target: str }
  type Entry = { key: str, attempt: str }
  type Attempt = { op: str, args: List[str], code: int, quiet: bool, diagnosed: bool, error: str,
    commit: str, unchanged: bool, addedRefs: List[Ref], removedRefs: List[Ref], requests: int, executions: int,
    results: int, accesses: int, request: str, input: str, construction: str, implementation: str, sources: List[str],
    keyHex: List[str], producingRequest: str, producingInput: str, producingConstruction: str, producingImplementation: str,
    attempt: str, result: str, value: int, gets: List[str], getSources: List[str], outcome: str, table: str,
    intent: str, entries: List[Entry], reportDigest: str,
    nativeStatus: str, nativeValue: str, nativeCount: int, nativeItems: List[str] }
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure val mismatch = "inspect: map_get trace does not match the producing construction"
  pure val requestRole = "617267756d656e742d6d61702d726571756573742d7631"  // argument-map-request-v1
  pure val resultRole = "617267756d656e742d6d61702d726573756c742d7631"   // argument-map-result-v1
  pure def pin(name: str, target: str): Ref = { name: name, target: target }
  pure def added(a: Attempt, name: str): str =
    a.addedRefs.foldl("", (target, r) => if (r.name == name) r.target else target)
  pure def accepts(a: Attempt): bool = a.code == 0 and a.quiet and a.commit != ""
  pure def pending(a: Attempt): str = added(a, a.args[1])
  pure def writesRequest(a: Attempt): bool = accepts(a) and not(a.unchanged) and a.removedRefs == List() and
    pending(a) != "" and pending(a) != a.commit and a.addedRefs == List(pin(a.args[2], a.commit), pin(a.args[1], pending(a)))
  pure def writesAttempt(a: Attempt): bool = accepts(a) and not(a.unchanged) and a.removedRefs == List() and
    a.addedRefs == List(pin(a.args[3], a.commit))
  pure def reads(a: Attempt): bool = accepts(a) and a.unchanged and a.reportDigest != "" and
    a.addedRefs == List() and a.removedRefs == List()
  pure def attemptRead(a: Attempt, attempt: str, requestId: str, implementation: str, value: int): bool =
    reads(a) and a.commit == attempt and a.attempt == attempt and a.result != "" and
    a.producingRequest == requestId and a.producingImplementation == implementation and a.value == value and
    a.producingInput != "" and a.producingConstruction != ""

  pure def validPair(rows: List[Attempt]): bool = {
    val literal = rows[2]
    val producer = rows[5]
    val returned = rows[8]
    and {
      attemptRead(literal, rows[1].commit, pending(rows[0]), "double@1", 84),
      attemptRead(producer, rows[4].commit, pending(rows[3]), "add@1", 42),
      attemptRead(returned, rows[7].commit, pending(rows[6]), "double@1", 84),
      literal.producingInput == returned.producingInput,
      literal.producingConstruction != returned.producingConstruction,
      literal.producingRequest != returned.producingRequest,
      literal.gets == List("x"),
      literal.getSources == List(""),
      returned.gets == List("x"),
      returned.getSources == List(producer.attempt),
    }
  }

  pure def output(rows: List[Attempt], op: str, alias: str): Attempt =
    rows.select(a => a.op == "native" and a.args[0] == op and a.args[a.args.length() - 1] == alias)[0]
  pure def treeMatches(tree: Attempt, entry: Attempt, role: str): bool =
    tree.nativeCount == 1 and entry.nativeItems == List(role)

  pure def graftLayout(rows: List[Attempt]): bool = {
    val literal = rows[2]
    val returned = rows[8]
    def value(op, alias) = output(rows, op, alias).nativeValue
    def decoded(alias) = output(rows, "object_decode", alias)
    def parentId(alias) = value("object_view_parent", alias)
    val oldResult = decoded("literal-result-view")
    val oldAttempt = decoded("literal-attempt-view")
    val newResult = decoded("grafted-result-view")
    val newAttempt = decoded("grafted-attempt-view")
    val resultId = value("txn_ref_get", "grafted-result-pin")
    val attemptId = value("txn_ref_get", "grafted-attempt-pin")
    val literalConstruction = value("txn_lookup_node", "literal-construction")
    val returnedConstruction = value("txn_lookup_node", "returned-construction")
    and {
      value("txn_ref_get", "literal-attempt") == literal.attempt,
      parentId("literal-request") == literal.producingRequest,
      parentId("literal-result") == literal.result,
      value("txn_ref_get", "returned-request") == returned.producingRequest,
      parentId("returned-origin") == rows[5].attempt,
      decoded("literal-request-view").nativeCount == 0,
      decoded("returned-request-view").nativeCount == 1,
      treeMatches(decoded("literal-request-tree"), output(rows, "object_view_entry", "literal-request-dag"), requestRole),
      treeMatches(decoded("returned-request-tree"), output(rows, "object_view_entry", "returned-request-dag"), requestRole),
      treeMatches(decoded("literal-result-tree"), output(rows, "object_view_entry", "literal-result-dag"), resultRole),
      literalConstruction != "",
      returnedConstruction != "",
      literalConstruction == value("txn_lookup_node", "getter-construction"),
      literalConstruction != returnedConstruction,
      resultId == value("txn_put_object", "new-result"),
      resultId != literal.result,
      attemptId == value("txn_put_object", "new-attempt"),
      attemptId != literal.attempt,
      newResult.nativeCount == 1,
      newAttempt.nativeCount == 2,
      newResult.nativeValue == oldResult.nativeValue,
      newAttempt.nativeValue == oldAttempt.nativeValue,
      parentId("grafted-result-owner") == returned.producingRequest,
      parentId("grafted-attempt-owner") == returned.producingRequest,
      parentId("grafted-attempt-result") == resultId,
    }
  }

  pure def rejectedGraft(a) =
    if (a.code != 1 or not(a.diagnosed) or a.error != mismatch or a.commit != "" or a.reportDigest != "")
      "wrong_getter_diagnostic"
    else if (not(a.unchanged) or a.addedRefs != List() or a.removedRefs != List()) "inspect_changed_repository"
    else "ok"

  pure def graftVerdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val reject = graft.length() - 3
    if (a.op == "request" and not(writesRequest(a))) "wrong_request_publication"
    else if (a.op == "work" and not(writesAttempt(a))) "wrong_attempt_publication"
    else if (i == 2 and not(attemptRead(a, rows[1].commit, pending(rows[0]), "double@1", 84))) "wrong_literal_read"
    else if (i == 5 and not(attemptRead(a, rows[4].commit, pending(rows[3]), "add@1", 42))) "wrong_producer_read"
    else if (i == 8 and not(validPair(rows))) "wrong_equal_inputs"
    else if (i == reject - 1 and not(graftLayout(rows))) "wrong_persisted_getter_graft"
    else if (i == reject) rejectedGraft(a)
    else if (i > reject and not(reads(a) and a.reportDigest == rows[if (i == reject + 1) 2 else 8].reportDigest))
      "wrong_genuine_readback"
    else "ok"
  }

  pure val firstRead = buildChain.length() + openTxn("read").length()
  pure val nextRead = firstRead + readLink(0).length()
  pure val readWidth = readLink(1).length()
  pure def requestEdge(count: int, target: str, predecessor: str): bool =
    if (predecessor == "") count == 0 and target == "" else count == 1 and target == predecessor

  pure def linkMatches(rows: List[Attempt], start: int, level: int): bool = {
    val input = pending(rows[2 * level])
    val previous = if (level == 0) "" else rows[2 * level - 1].commit
    rows[start].nativeValue == rows[2 * level + 1].commit and rows[start + 2].nativeCount == 2 and
      rows[start + 3].nativeValue == input and rows[start + 4].nativeValue != "" and
      rows[start + 5].nativeValue == input and
      requestEdge(rows[start + 7].nativeCount, if (level == 0) "" else rows[start + 8].nativeValue, previous)
  }

  pure def deepVerdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    if (i < buildChain.length()) {
      if (if (i % 2 == 0) writesRequest(a) else writesAttempt(a)) "ok" else "wrong_link_publication"
    } else if (i >= firstRead and i < deep.length() - 3) {
      val level = if (i < nextRead) 0 else 1 + (i - nextRead) / readWidth
      val start = if (level == 0) firstRead else nextRead + (level - 1) * readWidth
      if (i == start + readLink(level).length() - 1 and not(linkMatches(rows, start, level))) "wrong_native_link"
      else "ok"
    } else if (i == deep.length() - 1) {
      val last = links.length() - 1
      val attemptIds = range(0, links.length()).foldl(Set(), (ids, j) => ids.union(Set(rows[2 * j + 1].commit)))
      if (attemptIds.size() == 64 and attemptRead(a, rows[2 * last + 1].commit, pending(rows[2 * last]), "double@1", 0) and
        a.result == rows[nextRead + (last - 1) * readWidth + 4].nativeValue and
        a.gets == List("x") and a.getSources == List(rows[2 * last - 1].commit)) "ok"
      else "wrong_64_deep_tip"
    } else "ok"
  }

  pure def historyVerdicts(row: Observation): List[str] = {
    val wanted = if (row.scenario == 0) graft else deep
    if (row.scenario < 0 or row.scenario > 1 or row.attempts.length() != wanted.length()) List("missing_steps")
    else range(0, wanted.length()).foldl(List(), (out, i) => {
      val a = row.attempts[i]
      val result =
        if (a.op != wanted[i].op or a.args != wanted[i].args) "wrong_step"
        else if (a.op == "native" and a.nativeStatus != "ok") "wrong_native_status"
        else if (row.scenario == 0) graftVerdict(row.attempts, i)
        else deepVerdict(row.attempts, i)
      out.append(result)
    })
  }

  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 2 and verdicts.length() == 2 and evidence[0].scenario == 0 and evidence[1].scenario == 1 and
    verdicts[0].length() == graft.length() and verdicts[1].length() == deep.length() and
    verdicts[0].concat(verdicts[1]).foldl(true, (ok, verdict) => ok and verdictAccepted(verdict))

  pure val refused = { code: 1, diagnosed: true, error: mismatch, commit: "", reportDigest: "", unchanged: true,
    addedRefs: List(), removedRefs: List() }
  pure val controlsPass = rejectedGraft(refused) == "ok" and
    rejectedGraft({ ...refused, error: "inspect: invalid commit" }) == "wrong_getter_diagnostic" and
    rejectedGraft({ ...refused, unchanged: false }) == "inspect_changed_repository" and
    requestEdge(0, "", "") and requestEdge(1, "exact", "exact") and
    not(requestEdge(1, "other", "exact")) and not(requestEdge(2, "exact", "exact"))
}
