module argument_map_returned_source_rules {
  import argument_map_returned_source_histories.* from "./argument_map_returned_source_histories"

  type Ref = { name: str, target: str }
  type Dag = { dag: str, root: str, fields: int }
  type Snapshot = { dag: str, root: str, fields: int, role: str, parents: List[str], entries: int }
  type NativeResult = { attempt: Snapshot, result: Snapshot, datum: str, kind: int, value: int }
  type Member = { keyHex: str, kind: int, datum: str }
  type NativeRequest = { request: Snapshot, construction: Dag, constructionNode: str, implementationNode: str,
    invocationNode: str, priorNode: str, keyNode: str, keyHex: str, originNode: str, origin: str, sourceNode: str,
    sourceDag: str, input: str, kind: int, members: List[Member] }
  type Attempt = { op: str, args: List[str], code: int, commit: str, unchanged: bool, refs: List[Ref], attempt: str,
    result: str, producingRequest: str, producingImplementation: str, producingInput: str, value: int, request: str,
    input: str, implementation: str, construction: str, sources: List[str], keyHex: List[str], reportDigest: str,
    diagnostics: List[str], stdout: bool, nativeRequest: NativeRequest, nativeResult: NativeResult, additions: int,
    preserved: bool }
  type Observation = { attempts: List[Attempt] }

  pure val mismatch = "inspect: returned source does not match the selected attempt result"
  pure def ref(a, name) = a.refs.foldl("", (target, r) => if (r.name == name) r.target else target)
  pure def otherRefs(a, changed) = a.refs.select(r => not(changed.contains(r.name)))
  pure def accepts(a) = a.code == 0 and a.diagnostics == List() and a.stdout and a.commit != ""
  pure def reads(before, a) = a.unchanged and a.refs == before.refs
  pure def appends(before, a, added) = accepts(a) and not(a.unchanged) and a.preserved and
    otherRefs(a, added) == before.refs
  pure def addsRef(before, a, name) = appends(before, a, Set(name)) and ref(a, name) == a.commit
  pure def acceptedRead(before, a) = accepts(a) and reads(before, a) and a.commit == ref(before, a.args[1]) and
    a.reportDigest != ""
  pure def snapshotIs(s, role, parents, count) = s.role == role and s.entries == 1 and s.parents == parents and
    s.dag != "" and s.root != "" and s.fields == count

  pure def pending(before, a) = {
    val requestRef = a.args[1]
    val decisionRef = a.args[2]
    appends(before, a, Set(requestRef, decisionRef)) and ref(a, decisionRef) == a.commit and
      ref(a, requestRef) != "" and ref(a, requestRef) != a.commit
  }

  pure def producerRead(before: Attempt, a: Attempt, requestRef: str): bool = {
    val native = a.nativeResult
    acceptedRead(before, a) and a.attempt == a.commit and a.result != "" and a.producingRequest != "" and
      a.producingRequest == ref(before, requestRef) and a.producingImplementation == "add@1" and a.producingInput != "" and
      snapshotIs(native.attempt, "argument-map-attempt-v1", List(a.producingRequest, a.result), 1) and
      snapshotIs(native.result, "argument-map-result-v1", List(a.producingRequest), 2) and
      native.datum != "" and native.kind == 3 and native.value == 42 and a.value == native.value
  }

  pure def distinctEqualProducers(exact, donor) =
    exact.attempt != donor.attempt and exact.producingRequest != donor.producingRequest and
    exact.producingInput != donor.producingInput and exact.result != donor.result and
    exact.nativeResult.result.dag != donor.nativeResult.result.dag and exact.nativeResult.datum == donor.nativeResult.datum

  pure def consumerRead(before: Attempt, a: Attempt, exact: Attempt): bool = {
    val native = a.nativeRequest
    // Native datum tags: MAP = 10, STRING = 6, I64 = 3 (`include/dml/record.h`).
    acceptedRead(before, a) and a.request == a.commit and a.implementation == "double@1" and
      a.input == native.input and native.input != "" and a.construction == native.construction.dag and
      a.sources == List(exact.attempt) and a.keyHex == List("78") and
      snapshotIs(native.request, "argument-map-request-v1", List(exact.attempt), 3) and
      native.constructionNode != "" and native.implementationNode != "" and native.invocationNode != "" and
      native.construction.dag != "" and native.construction.root == native.request.root and native.construction.fields == 4 and
      native.priorNode != "" and native.keyNode != "" and native.keyHex == "78" and native.originNode != "" and
      native.origin == exact.attempt and native.sourceNode != "" and native.sourceDag == exact.nativeResult.result.dag and
      native.kind == 10 and native.members == List({ keyHex: "78", kind: 6, datum: exact.nativeResult.datum })
  }

  pure def substituted(base: Attempt, donor: Attempt, a: Attempt): str = {
    val old = base.nativeRequest
    val new = a.nativeRequest
    // The ref, commit, tree, two DAGs and two SUBDAG nodes are the only new entries.
    if (not(addsRef(base, a, a.args[1])) or a.commit == base.commit or a.additions != 7) "wrong_fixture_publication"
    else if (new.request.dag == "" or new.request.dag == old.request.dag or
      new.construction.dag == "" or new.construction.dag == old.construction.dag or
      new.constructionNode == "" or new.constructionNode == old.constructionNode or
      new.sourceNode == "" or new.sourceNode == old.sourceNode or
      new != { ...old, request: { ...old.request, dag: new.request.dag },
        construction: { ...old.construction, dag: new.construction.dag }, constructionNode: new.constructionNode,
        sourceNode: new.sourceNode, sourceDag: donor.nativeResult.result.dag }) "wrong_fixture_source_swap"
    else "ok"
  }

  pure def rejection(before, a) =
    if (a.code != 1 or a.diagnostics != List(mismatch) or a.stdout or a.commit != "") "wrong_inspect_rejection"
    else if (not(reads(before, a))) "wrong_inspect_inventory"
    else "ok"

  pure def stepVerdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val wanted = returnedSourceHistory[i]
    val before = if (i == 0) { ...a, refs: List() } else rows[i - 1]
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if (i == 0 or i == 3 or i == 6) {
      if (pending(before, a)) "ok" else "wrong_pending_publication"
    } else if (i == 1 or i == 4) {
      if (addsRef(before, a, a.args[3])) "ok" else "wrong_attempt_publication"
    } else if (i == 2 or i == 5) {
      if (not(producerRead(before, a, if (i == 2) "p-exact" else "p-other"))) "wrong_producer_read"
      else if (i == 5 and not(distinctEqualProducers(rows[2], a))) "wrong_equal_value_donor"
      else "ok"
    } else if (i == 7) {
      if (consumerRead(before, a, rows[2])) "ok" else "wrong_consumer_read"
    } else if (i == 8) substituted(rows[7], rows[5], a)
    else if (i == 9) {
      val outcome = rejection(before, a)
      if (outcome != "ok") outcome
      else if (a.nativeRequest != before.nativeRequest) "wrong_rejected_request"
      else "ok"
    } else if (consumerRead(before, a, rows[2]) and a.reportDigest == rows[7].reportDigest and
      a.nativeRequest == rows[7].nativeRequest) "ok"
    else "wrong_original_readback"
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.attempts.length() != returnedSourceHistory.length()) List("missing_steps")
    else range(0, returnedSourceHistory.length()).foldl(List(), (out, i) => out.append(stepVerdict(row.attempts, i)))

  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and verdicts.length() == 1 and verdicts[0].length() == returnedSourceHistory.length() and
    verdicts[0].foldl(true, (ok, verdict) => ok and verdictAccepted(verdict))

  pure val refused = { code: 1, diagnostics: List(mismatch), stdout: false, commit: "", unchanged: true,
    refs: List({ name: "substituted", target: "request" }) }
  pure val controlsPass = rejection(refused, refused) == "ok" and
    rejection(refused, { ...refused, diagnostics: List("inspect: invalid object") }) == "wrong_inspect_rejection" and
    rejection(refused, { ...refused, stdout: true }) == "wrong_inspect_rejection" and
    rejection(refused, { ...refused, unchanged: false }) == "wrong_inspect_inventory"
}
