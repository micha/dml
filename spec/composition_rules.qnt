module composition_rules {
  import composition_histories.* from "./composition_histories"
  import workflow_native_fixture as n from "./workflow_native_fixture"

  type Ref = { name: str, before: str, after: str }
  type Native = { id: str, role: str, dag: str, parents: List[str], pin: str, inputs: str }
  type Source = { name: str, dag: str }
  type Upstream = { attempt: str, request: str, result: str, outer: str, map: str }
  type Q = { func: str, request: str, inputs: str, map: str, sources: List[Source],
    composition: str, upstream: Upstream }
  type Getter = { operation: str, func: str, binding: str, inputs: str, datum: str, sources: List[Source], key: str }
  type Attempt = { op: str, args: List[str], code: int, error: str, commit: str, unchanged: bool,
    preserved: bool, transfer: bool, refs: List[Ref], main: str, counts: List[int], profiles: List[str],
    created: List[Native], requested: Q, producing: Q, trace: List[Getter], outcome: str, selection: str,
    attempt: str, result: str, outer: str, value: int,
    nativeStatus: str, nativeValue: str, nativeCount: int, nativeItems: List[str] }
  type Observation = { attempts: List[Attempt] }

  pure val addFunc = "urn:example:node-add"
  pure val doubleFunc = "urn:example:node-double"
  pure val noUpstream: Upstream = { attempt: "", request: "", result: "", outer: "", map: "" }
  pure val noQ: Q = { func: "", request: "", inputs: "", map: "", sources: List(),
    composition: "", upstream: noUpstream }
  pure val noNative: Native = { id: "", role: "", dag: "", parents: List(), pin: "", inputs: "" }
  pure val roles = Map("config" -> "composition-example-config-v1", "request" -> "composition-example-request-v1",
    "result" -> "composition-example-result-v1", "attempt" -> "composition-example-attempt-v1",
    "composition" -> "composition-example-composition-v1", "decision" -> "composition-example-decision-v1")
  pure def record(a: Attempt, name: str): Native = {
    val found = a.created.foldl(List(), (out, n) => if (n.role == roles.get(name)) out.append(n) else out)
    if (found.length() == 1) found[0] else noNative
  }
  pure def native(a: Attempt, name: str, ps: List[str]): bool = {
    val found = record(a, name)
    found.id != "" and found.dag != "" and found.parents == ps
  }
  pure def ref(name: str, before: str, after: str): Ref = { name: name, before: before, after: after }
  pure def createdRef(name: str, target: str): Ref = ref(name, "", target)
  pure def sourceDag(sources: List[Source], name: str): str =
    sources.foldl("", (out, edge) => if (edge.name == name) edge.dag else out)
  pure def getUpstream(a: Attempt): Upstream = { attempt: a.attempt, request: a.producing.request,
    result: a.result, outer: a.outer, map: a.producing.map }

  pure def configRow(a: Attempt): bool =
    a.created.length() == 1 and native(a, "config", List()) and record(a, "config").id == a.commit
      and a.refs == List(createdRef("config", a.commit))
  pure def qrow(a: Attempt, parent: str, pending: str): bool =
    a.created.length() == 1 and native(a, "request", List(parent)) and record(a, "request").id == a.commit
      and a.refs == List(createdRef(pending, a.commit))
  pure def trow(a: Attempt, q: str, pin: str, previous: str): bool = {
    val r = record(a, "result").id
    a.created.length() == 2 and native(a, "result", List(q)) and native(a, "attempt", List(q, r))
      and record(a, "attempt").id == a.commit and a.refs == List(ref("main", previous, r), createdRef(pin, a.commit))
  }
  pure def crow(a: Attempt, t: str, pin: str): bool = {
    val c = record(a, "composition")
    a.created.length() == 1 and native(a, "composition", List(t)) and c.id == a.commit
      and c.pin == t and c.inputs != "" and a.refs == List(createdRef(pin, a.commit))
  }
  pure def drow(a: Attempt, c: str, selected: str, refs: List[Ref]): bool = {
    val q = record(a, "request").id
    val ps = if (selected == "") List(q) else List(q, selected)
    a.created.length() == 2 and native(a, "request", List(c)) and native(a, "decision", ps)
      and record(a, "request").inputs != "" and record(a, "decision").id == a.commit and a.refs == refs
  }

  pure def getters(a: Attempt, names: List[str]): bool = a.trace.length() == names.length() and {
    range(0, names.length()).foldl(true, (ok, i) => {
      val call = a.trace[i]
      ok and call.key == names[i] and call.operation != "" and call.inputs != "" and call.datum != ""
        and call.func == "dml://builtin/map/get" and call.binding == "dml://source/builtin/map/get/v1"
        and call.sources.length() == 2 and sourceDag(call.sources, "map") == a.producing.inputs
        and sourceDag(call.sources, "key") != ""
    })
  }
  pure def composition(q: Q, c: Attempt, upstream: Attempt): bool = {
    val r = record(c, "composition")
    q.func == doubleFunc and q.inputs == r.inputs and q.composition == c.commit and q.upstream == getUpstream(upstream)
      and q.sources == List({ name: "x", dag: upstream.outer }) and q.map != ""
  }
  pure def nativeRequest(q: Q, n: Native): bool = q.request == n.id and q.inputs == n.inputs and q.inputs != ""
  pure def workRead(a: Attempt, t: Attempt, q: Attempt, func: str, value: int): bool = {
    val r = record(t, "result")
    val names = if (func == addFunc) List("a", "b") else List("x")
    a.commit == t.commit and a.attempt == t.commit and a.result == r.id and a.outer == r.dag
      and nativeRequest(a.producing, record(q, "request")) and a.producing.func == func
      and a.producing.map != "" and a.value == value
      and a.producing.sources.foldl(List(), (out, edge) => out.append(edge.name)) == names
      and a.producing.sources.foldl(true, (ok, edge) => ok and edge.dag != "") and getters(a, names)
  }
  pure def pendingRead(a: Attempt, d: Attempt, c: Attempt, upstream: Attempt, selected: str): bool =
    a.commit == d.commit and nativeRequest(a.requested, record(d, "request")) and a.outcome == "pending"
      and a.selection == selected and composition(a.requested, c, upstream) and a.producing == noQ
      and a.attempt == "" and a.result == "" and a.outer == "" and a.trace == List()
  pure def hit(a: Attempt, d: Attempt, c: Attempt, upstream: Attempt, old: Attempt): bool =
    a.commit == d.commit and nativeRequest(a.requested, record(d, "request")) and a.outcome == "reuse"
      and a.selection == old.attempt and composition(a.requested, c, upstream)
      and a.requested.request != a.producing.request and a.requested.composition != a.producing.composition
      and a.requested.upstream.attempt != a.producing.upstream.attempt and a.requested.map == a.producing.map
      and historicalRead(a, old)
  pure def historicalRead(a: Attempt, old: Attempt): bool =
    a.producing == old.producing and a.attempt == old.attempt and a.result == old.result
      and a.outer == old.outer and a.trace == old.trace and a.value == old.value
  pure def replicaRead(a: Attempt, original: Attempt): bool =
    a.commit == original.commit and a.requested == original.requested and a.outcome == original.outcome
      and a.selection == original.selection and historicalRead(a, original)

  pure val rejected = Map(
    2 -> "work: invalid_state: ref already exists",
    13 -> "compose: upstream ref does not match the expected commit or absence",
    14 -> "compose: invalid_state: ref already exists",
    16 -> "request-double: invalid_state: ref already exists",
    17 -> "request-double: pending request ref does not match the expected commit or absence",
    27 -> "work: invalid_state: ref already exists",
    31 -> "request-double: no selected double attempt for the argument MAP",
    32 -> "request-double: selection ref does not match the expected commit or absence",
    33 -> "request-double: attempt has the wrong ordinary func",
    39 -> "request-double: composition producer does not match its pinned attempt",
    42 -> "request-double: reuse needs a new invocation ID, not the producing request",
    47 -> "inspect: composition input does not use the exact producer return DAG",
    49 -> "inspect: composition producer does not match its pinned attempt",
    51 -> "inspect: composition producer does not match its pinned attempt",
    53 -> "inspect: reuse needs a new invocation ID, not the producing request")

  pure def accepted(rows: List[Attempt], i: int): bool = {
    val a = rows[i]
    val old = rows[9]
    val r = record(a, "request").id
    if (i == 0) configRow(a)
    else if (i == 1 or i == 10 or i == 20 or i == 26) qrow(a, rows[0].commit, a.args[3])
    else if (Set(3, 8, 11, 21, 28, 36).contains(i)) {
      val q = if (i == 3 or i == 28) rows[i - 2].commit // Retry the request from before the rejection.
        else if (i == 8) record(rows[6], "request").id
        else if (i == 36) record(rows[34], "request").id else rows[i - 1].commit
      trow(a, q, a.args[3], rows[i - 1].main)
        and (if (i == 11) a.profiles == List() else Set("builtin-operation-v1", "builtin-trace-v1",
          "builtin-return-v1").forall(p => a.profiles.foldl(false, (seen, actual) => seen or actual == p)))
    } else if (i == 4) workRead(a, rows[3], rows[1], addFunc, 42)
    else if (i == 12) workRead(a, rows[11], rows[10], addFunc, 42)
      and a.producing.map == rows[4].producing.map and a.producing.inputs == rows[4].producing.inputs
      and a.producing.request != rows[4].producing.request and a.attempt != rows[4].attempt
      and a.result != rows[4].result and a.outer == rows[4].outer and a.trace == rows[4].trace
    else if (i == 22) workRead(a, rows[21], rows[20], addFunc, 42)
      and a.producing.map != rows[4].producing.map and a.producing.inputs != rows[4].producing.inputs
      and a.outer != rows[4].outer and sourceDag(a.producing.sources, "a") == sourceDag(rows[4].producing.sources, "b")
      and sourceDag(a.producing.sources, "b") == sourceDag(rows[4].producing.sources, "a")
    else if (i == 29) workRead(a, rows[28], rows[26], addFunc, 43)
      and a.producing.map != rows[4].producing.map and a.producing.map != rows[22].producing.map
    else if (i == 5) crow(a, rows[3].commit, "c2")
    else if (i == 15) crow(a, rows[11].commit, "c4") and record(a, "composition").inputs == record(rows[5], "composition").inputs
      and record(a, "composition").dag != record(rows[5], "composition").dag
    else if (i == 23) crow(a, rows[21].commit, "c6") and record(a, "composition").inputs != record(rows[5], "composition").inputs
    else if (i == 30) crow(a, rows[28].commit, "c8")
    else if (i == 6) drow(a, rows[5].commit, "", List(createdRef("d2", a.commit), createdRef("q2", r)))
    else if (i == 7) pendingRead(a, rows[6], rows[5], rows[4], "")
    else if (i == 9) workRead(a, rows[8], rows[6], doubleFunc, 84) and a.producing == rows[7].requested
    else if (i == 18 or i == 24) {
      val c = if (i == 18) 15 else 23
      a.profiles == List() and drow(a, rows[c].commit, old.attempt,
        List(createdRef(a.args[4], a.commit), ref("main", rows[i - 1].main, old.result)))
    } else if (i == 19) hit(a, rows[18], rows[15], rows[12], old)
      and a.requested.inputs == a.producing.inputs and a.requested.sources == a.producing.sources
    else if (i == 25) hit(a, rows[24], rows[23], rows[22], old)
      and a.requested.inputs != a.producing.inputs and a.requested.sources != a.producing.sources
    else if (i == 34) drow(a, rows[30].commit, old.attempt, List(createdRef("d8", a.commit), createdRef("q8", r)))
    else if (i == 35) pendingRead(a, rows[34], rows[30], rows[29], old.attempt)
      and a.requested.map != old.producing.map and a.main == rows[29].result
    else if (i == 37) workRead(a, rows[36], rows[34], doubleFunc, 86) and a.producing == rows[35].requested
      and a.counts == List(8, 6, 6, 4, 4)
      and List(4, 9, 12, 22, 29, 37).foldl(0, (sum, j) => sum + rows[j].trace.length()) == 10
    else if (i == 38) {
      val c = record(a, "composition")
      val t = record(a, "attempt")
      val result = record(a, "result")
      a.created.length() == 4 and native(a, "composition", List(rows[12].attempt))
        and c.dag == record(rows[5], "composition").dag and c.pin == rows[4].attempt
        and c.inputs == record(rows[5], "composition").inputs and t.dag == record(rows[8], "attempt").dag
        and native(a, "request", List(c.id)) and native(a, "result", List(r)) and native(a, "attempt", List(r, result.id))
        and t.id == a.commit and a.refs == List(createdRef("poison", a.commit))
    } else if (i == 40 or i == 41) {
      val d = if (i == 40) rows[18].commit else rows[24].commit
      a.transfer and a.commit == d and a.counts == List(4, 3, 3, 2, 1) and a.created.length() == 14
        and a.refs == List(createdRef(a.args[2], d))
    } else if (i == 43) a.transfer and a.commit == "" and a.unchanged and a.refs == List()
    else if (i == 44) replicaRead(a, rows[19])
    else if (i == 45) replicaRead(a, rows[25])
    else if (i == 46) {
      val c = record(a, "composition")
      val base = record(rows[23], "composition")
      a.created.length() == 1 and native(a, "composition", base.parents) and c.id == a.commit and c.pin == base.pin
        and c.inputs == record(rows[5], "composition").inputs and c.inputs != base.inputs
        and a.refs == List(createdRef("source-graft", a.commit))
    } else if (i == 48) {
      val c = record(a, "composition")
      val base = record(rows[15], "composition")
      a.created.length() == 1 and native(a, "composition", List(rows[4].attempt)) and c.id == a.commit
        and c.dag == base.dag and c.pin == base.pin and c.inputs == base.inputs
        and a.refs == List(createdRef("parent-graft", a.commit))
    } else if (i == 50) {
      val poison = rows[38]
      val d = record(a, "decision")
      a.created.length() == 5 and a.profiles == List() and d.id == a.commit
        and d.dag == record(rows[18], "decision").dag
        and native(a, "decision", List(record(rows[18], "request").id, poison.commit))
        and poison.created.foldl(true, (ok, row) => ok and
          a.created.foldl(false, (found, other) => found or row == other))
        and a.refs == List(createdRef("history-graft", a.commit))
    } else if (i == 52) {
      val d = record(a, "decision")
      a.created.length() == 1 and a.profiles == List() and d.id == a.commit
        and d.dag == record(rows[18], "decision").dag and native(a, "decision", List(old.producing.request, old.attempt))
        and a.refs == List(createdRef("same-id-graft", a.commit)) and a.main == rows[51].main
    } else false
  }

  pure def acceptedOverflow(rows: List[Attempt], i: int): bool = {
    val a = rows[i]
    val addResult = rows[5].result
    if (i == 0) configRow(a) and a.main == ""
    else if (i == 1 or i == 3) qrow(a, rows[0].commit, a.args[3]) and a.main == ""
      and record(a, "request").inputs != ""
    else if (i == 4) trow(a, rows[3].commit, a.args[3], "") and a.main == record(a, "result").id
    else if (i == 5) workRead(a, rows[4], rows[3], addFunc, 9223372036854775807) and a.main == addResult
    else if (i == 6) crow(a, rows[4].commit, a.args[3]) and a.main == addResult
    else if (i == 7) drow(a, rows[6].commit, "",
        List(createdRef(a.args[4], a.commit), createdRef(a.args[3], record(a, "request").id)))
      and a.main == addResult
    else if (i == 9) pendingRead(a, rows[7], rows[6], rows[5], "") and a.main == addResult
    else false
  }

  pure def rejection(a: Attempt, error: str, intact: bool): str =
    if (a.code == 1 and a.error == error and a.commit == "" and a.unchanged
        and a.created == List() and a.refs == List() and intact) "ok" else "wrong_rejection_or_rollback"

  pure def verdict(rows: List[Attempt], i: int, overflow: bool): str = {
    val a = rows[i]
    val wanted = if (overflow) overflowStory[i] else story[i]
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if (not(a.preserved)) "changed_historical_records"
    else if (overflow and (i == 2 or i == 8)) {
      val main = if (i == 2) "" else rows[5].result
      val counts = if (i == 2) List(1, 0, 0, 0, 0) else List(3, 1, 1, 1, 1)
      rejection(a, "work: int too big to convert", a.main == main and rows[i - 1].main == main and a.counts == counts)
    } else if (not(overflow) and rejected.keys().contains(i)) {
      val mainIntact = if (i == 2) a.main == "" and rows[1].main == ""
        else if (i == 27) a.main == rows[26].main and a.main == rows[9].result
        else if (i == 42) a.main == rows[37].result and a.main != rows[9].result else true
      rejection(a, rejected.get(i), mainIntact)
    } else if (a.code != 0 or a.error != "" or (a.op != "retire" and a.commit == "")) "unexpected_failure"
    else if (a.unchanged != Set("inspect", "retire").contains(a.op)) "wrong_write_boundary"
    else if (not(if (overflow) acceptedOverflow(rows, i) else accepted(rows, i))) "wrong_native_or_reported_provenance"
    else "ok"
  }

  pure def namedKeyVerdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val expected = namedKeyStory[i]
    pure def output(op: str, alias: str): Attempt = rows[n::outputIndex(namedKeyStory, op, alias)]
    pure def value(op: str, alias: str): str = output(op, alias).nativeValue
    if (a.op != expected.op or a.args != expected.args) "wrong_step"
    else if (i < 5) verdict(rows, i, false)
    else if (a.op == "native") {
      if (a.nativeStatus == "ok") "ok" else "wrong_native_status"
    } else if (i == namedKeyReject) {
      val old = rows[4]
      val fixture = value("txn_ref_get", "original-attempt") == old.attempt
        and value("txn_ref_get", "stored-attempt") == value("txn_put_object", "new-attempt")
        and value("txn_ref_get", "stored-attempt") != old.attempt
        and value("object_view_entry", "actual-attempt-dag") == value("object_view_entry", "old-attempt-dag")
        and output("object_decode", "actual-attempt-commit").nativeCount == 2
        and output("object_decode", "actual-return-commit").nativeCount == 1
        and value("object_view_parent", "stored-owner") == old.producing.request
        and value("object_view_parent", "stored-result-owner") == old.producing.request
        and value("object_view_parent", "stored-result") == value("txn_put_object", "new-result")
        and value("object_view_parent", "stored-result") != old.result
        and value("object_view_entry", "actual-return-dag") == value("txn_put_object", "new-return")
        and output("datum_decode", "sum-bytes").nativeCount == 3 and value("datum_decode", "sum-bytes") == "2a00000000000000"
        and value("object_decode", "stored-call") != old.trace[0].operation
        and value("object_decode", "stored-key") != sourceDag(old.trace[0].sources, "key")
        and value("txn_lookup_node", "stored-key-value-node") == value("txn_lookup_node", "key-value")
        and value("txn_lookup_node", "stored-named-value") == value("txn_lookup_node", "key-value")
        and value("txn_lookup_node", "stored-key-role-node") == value("txn_put_object", "source-role")
        and output("datum_decode", "key-role-bytes").nativeCount == 6
        and value("datum_decode", "key-role-bytes") == "6275696c74696e2d6c69746572616c2d736f757263652d7631"
        and output("datum_decode", "key-bytes").nativeCount == 6 and value("datum_decode", "key-bytes") == "61"
      if (not(fixture)) "wrong_named_key_fixture" else rejection(a,
        "compose: getter trace does not match the exact request inputs and keys", a.main == old.result)
    } else if (a.code == 0 and a.error == "" and a.preserved and not(a.unchanged)
        and crow(a, rows[4].attempt, "from-forged") and a.main == rows[4].result) "ok"
    else "wrong_valid_composition"
  }

  pure def historyVerdicts(row: Observation): List[str] = {
    val attemptCount = row.attempts.length()
    val overflow = attemptCount == overflowStory.length()
    if (attemptCount == namedKeyStory.length())
      range(0, attemptCount).foldl(List(), (out, i) => out.append(namedKeyVerdict(row.attempts, i)))
    else if (attemptCount != story.length() and not(overflow)) List("missing_steps")
    else range(0, attemptCount).foldl(List(), (out, i) => out.append(verdict(row.attempts, i, overflow)))
  }
  pure def verdictAccepted(value: str): bool = value == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 3 and verdicts.length() == 3
      and verdicts[0].length() == story.length() and verdicts[1].length() == overflowStory.length()
      and verdicts[2].length() == namedKeyStory.length()
      and verdicts.foldl(true, (ok, row) => ok and row.foldl(true, (pass, value) => pass and verdictAccepted(value)))
      and evidence[0].attempts[19].outcome == "reuse" and evidence[0].attempts[25].outcome == "reuse"
      and evidence[0].attempts[35].outcome == "pending" and evidence[0].attempts[45].unchanged
      and evidence[1].attempts[9].outcome == "pending"

  pure val q: Q = { ...noQ, request: "old-q", func: doubleFunc, composition: "old-c", map: "same-map",
    upstream: { ...noUpstream, attempt: "old-add" } }
  pure val old: Attempt = { op: "inspect", args: List(), code: 0, error: "", commit: "old-t", unchanged: true,
    preserved: true, transfer: false, refs: List(), main: "", counts: List(), profiles: List(), created: List(),
    requested: noQ, producing: q, trace: List(), outcome: "", selection: "", attempt: "old-t",
    result: "old-r", outer: "old-outer", value: 84, nativeStatus: "", nativeValue: "", nativeCount: 0, nativeItems: List() }
  pure val requested = { ...q, request: "new-q", composition: "new-c", upstream: { ...q.upstream, attempt: "new-add" } }
  pure val reused = { ...old, commit: "new-d", requested: requested, outcome: "reuse", selection: old.attempt }
  pure val controlsPass = replicaRead(reused, reused)
    and not(replicaRead({ ...reused, producing: requested }, reused))
    and not(replicaRead({ ...reused, requested: q }, reused))
    and not(replicaRead({ ...reused, producing: { ...q, upstream: requested.upstream } }, reused))
}
