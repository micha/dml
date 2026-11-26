module argument_map_request_integrity_rules {
  import argument_map_request_integrity_histories.* from "./argument_map_request_integrity_histories"

  type Ref = { name: str, target: str }
  type Member = { keyHex: str, keyKind: int, valueKind: int, value: int }
  type MapRoot = { node: str, datum: str, literal: bool, kind: int, members: List[Member] }
  type NativeRequest = { dag: str, role: str, parents: List[str], entries: int, fields: int, bindings: List[str],
    root: MapRoot, construction: str, constructionMap: MapRoot }
  type Attempt = { op: str, args: List[str], code: int, error: str, commit: str, unchanged: bool, refs: List[Ref],
    request: str, input: str, construction: str, implementation: str, reportDigest: str, stdout: bool,
    native: NativeRequest, additions: int, preserved: bool }
  type Observation = { attempts: List[Attempt] }

  pure val mismatch = "inspect: request argument MAP differs from its construction"
  pure def ref(a, name) = a.refs.foldl("", (target, r) => if (r.name == name) r.target else target)
  pure def accepts(a) = a.code == 0 and a.error == "" and a.stdout and a.commit != ""
  pure def reads(before, a) = a.unchanged and a.refs == before.refs
  pure def otherRefs(a, changed) = a.refs.select(r => not(changed.contains(r.name)))

  pure def pending(before: Attempt, a: Attempt): str = {
    val pendingRef = a.args[1]
    val decisionRef = a.args[2]
    if (accepts(a) and not(a.unchanged) and a.preserved and ref(a, decisionRef) == a.commit and
      ref(a, pendingRef) != "" and ref(a, pendingRef) != a.commit and ref(before, pendingRef) == "" and
      ref(before, decisionRef) == "" and otherRefs(a, Set(pendingRef, decisionRef)) == before.refs) "ok"
    else "wrong_pending_publication"
  }

  pure def validInspection(before: Attempt, a: Attempt, expected: int): bool = {
    val shape = a.native
    // Native datum tags: MAP = 10, STRING = 6, I64 = 3 (`include/dml/record.h`).
    accepts(a) and reads(before, a) and a.commit == ref(before, a.args[1]) and a.request == a.commit and
      a.implementation == "double@1" and a.reportDigest != "" and a.input == shape.root.datum and
      a.construction == shape.construction and shape.dag != "" and shape.role == "argument-map-request-v1" and
      shape.entries == 1 and shape.fields == 3 and shape.parents == List() and shape.bindings.length() == 3 and
      shape.construction != "" and shape.root.node != "" and shape.root.datum != "" and shape.root.literal and
      shape.root.kind == 10 and shape.root.members == List({ keyHex: "78", keyKind: 6, valueKind: 3, value: expected }) and
      shape.root == shape.constructionMap
  }

  pure def substituted(base: Attempt, donor: Attempt, a: Attempt): str =
    if (not(accepts(a)) or not(a.preserved) or a.unchanged or a.additions != 4 or a.commit == base.commit or
      a.commit == donor.commit or ref(donor, a.args[1]) != "" or ref(a, a.args[1]) != a.commit or
      otherRefs(a, Set(a.args[1])) != donor.refs) "wrong_fixture_publication"
    else if (a.native.dag == "" or a.native.dag == base.native.dag or a.native.dag == donor.native.dag or
      a.native != { ...base.native, dag: a.native.dag, root: donor.native.root } or
      a.native.root.datum == a.native.constructionMap.datum) "wrong_fixture_root_swap"
    else "ok"

  pure def rejects(before, a) =
    if (a.code != 1 or a.error != mismatch or a.stdout or a.commit != "") "wrong_inspect_rejection"
    else if (not(reads(before, a))) "wrong_inspect_inventory"
    else "ok"

  pure def stepVerdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val wanted = requestIntegrityHistory[i]
    val before = if (i == 0) { ...a, refs: List() } else rows[i - 1]
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if (i < 2) pending(before, a)
    else if (i == 2 or i == 3) {
      if (validInspection(before, a, if (i == 2) 42 else 43)) "ok" else "wrong_clean_inspection"
    } else if (i == 4) substituted(rows[2], rows[3], a)
    else if (i == 5) rejects(before, a)
    else if (validInspection(before, a, 42) and a.reportDigest == rows[2].reportDigest and a.native == rows[2].native)
      "ok"
    else "wrong_original_readback"
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.attempts.length() != requestIntegrityHistory.length()) List("missing_steps")
    else range(0, requestIntegrityHistory.length()).foldl(List(), (out, i) => out.append(stepVerdict(row.attempts, i)))

  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and verdicts.length() == 1 and verdicts[0].length() == requestIntegrityHistory.length() and
    verdicts[0].foldl(true, (ok, verdict) => ok and verdictAccepted(verdict))

  pure val rejection = { code: 1, error: mismatch, stdout: false, commit: "", unchanged: true,
    refs: List({ name: "forged", target: "request" }) }
  pure val controlsPass = rejects(rejection, rejection) == "ok" and
    rejects(rejection, { ...rejection, error: "inspect: invalid object" }) == "wrong_inspect_rejection" and
    rejects(rejection, { ...rejection, stdout: true }) == "wrong_inspect_rejection" and
    rejects(rejection, { ...rejection, unchanged: false }) == "wrong_inspect_inventory"
}
