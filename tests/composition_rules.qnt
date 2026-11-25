module composition_rules {
  import composition_histories.* from "./composition_histories"

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
    attempt: str, result: str, outer: str, value: int }
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
    12 -> "compose: upstream ref does not match the expected commit or absence",
    13 -> "compose: invalid_state: ref already exists",
    15 -> "request-double: invalid_state: ref already exists",
    16 -> "request-double: pending request ref does not match the expected commit or absence",
    29 -> "request-double: no selected double attempt for the argument MAP",
    30 -> "request-double: selection ref does not match the expected commit or absence",
    31 -> "request-double: attempt has the wrong ordinary func",
    37 -> "request-double: composition producer does not match its pinned attempt",
    44 -> "inspect: composition input does not use the exact producer return DAG",
    46 -> "inspect: composition producer does not match its pinned attempt",
    48 -> "inspect: composition producer does not match its pinned attempt")

  pure def accepted(rows: List[Attempt], i: int): bool = {
    val a = rows[i]
    val old = rows[8]
    val r = record(a, "request").id
    if (i == 0) a.created.length() == 1 and native(a, "config", List()) and record(a, "config").id == a.commit
      and a.refs == List(createdRef("config", a.commit))
    else if (i == 1 or i == 9 or i == 19 or i == 25) qrow(a, rows[0].commit, a.args[3])
    else if (Set(2, 7, 10, 20, 26, 34).contains(i)) {
      val q = if (i == 7) record(rows[5], "request").id
        else if (i == 34) record(rows[32], "request").id else rows[i - 1].commit
      trow(a, q, a.args[3], rows[i - 1].main)
        and (if (i == 10) a.profiles == List() else Set("builtin-operation-v1", "builtin-trace-v1",
          "builtin-return-v1").forall(p => a.profiles.foldl(false, (seen, actual) => seen or actual == p)))
    } else if (i == 3) workRead(a, rows[2], rows[1], addFunc, 42)
    else if (i == 11) workRead(a, rows[10], rows[9], addFunc, 42)
      and a.producing.map == rows[3].producing.map and a.producing.inputs == rows[3].producing.inputs
      and a.producing.request != rows[3].producing.request and a.attempt != rows[3].attempt
      and a.result != rows[3].result and a.outer == rows[3].outer and a.trace == rows[3].trace
    else if (i == 21) workRead(a, rows[20], rows[19], addFunc, 42)
      and a.producing.map != rows[3].producing.map and a.producing.inputs != rows[3].producing.inputs
      and a.outer != rows[3].outer and sourceDag(a.producing.sources, "a") == sourceDag(rows[3].producing.sources, "b")
      and sourceDag(a.producing.sources, "b") == sourceDag(rows[3].producing.sources, "a")
    else if (i == 27) workRead(a, rows[26], rows[25], addFunc, 43)
      and a.producing.map != rows[3].producing.map and a.producing.map != rows[21].producing.map
    else if (i == 4) crow(a, rows[2].commit, "c2")
    else if (i == 14) crow(a, rows[10].commit, "c4") and record(a, "composition").inputs == record(rows[4], "composition").inputs
      and record(a, "composition").dag != record(rows[4], "composition").dag
    else if (i == 22) crow(a, rows[20].commit, "c6") and record(a, "composition").inputs != record(rows[4], "composition").inputs
    else if (i == 28) crow(a, rows[26].commit, "c8")
    else if (i == 5) drow(a, rows[4].commit, "", List(createdRef("d2", a.commit), createdRef("q2", r)))
    else if (i == 6) pendingRead(a, rows[5], rows[4], rows[3], "")
    else if (i == 8) workRead(a, rows[7], rows[5], doubleFunc, 84) and a.producing == rows[6].requested
    else if (i == 17 or i == 23) {
      val c = if (i == 17) 14 else 22
      a.profiles == List() and drow(a, rows[c].commit, old.attempt,
        List(createdRef(a.args[4], a.commit), ref("main", rows[i - 1].main, old.result)))
    } else if (i == 18) hit(a, rows[17], rows[14], rows[11], old)
      and a.requested.inputs == a.producing.inputs and a.requested.sources == a.producing.sources
    else if (i == 24) hit(a, rows[23], rows[22], rows[21], old)
      and a.requested.inputs != a.producing.inputs and a.requested.sources != a.producing.sources
    else if (i == 32) drow(a, rows[28].commit, old.attempt, List(createdRef("d8", a.commit), createdRef("q8", r)))
    else if (i == 33) pendingRead(a, rows[32], rows[28], rows[27], old.attempt)
      and a.requested.map != old.producing.map and a.main == rows[27].result
    else if (i == 35) workRead(a, rows[34], rows[32], doubleFunc, 86) and a.producing == rows[33].requested
      and a.counts == List(8, 6, 6, 4, 4)
      and List(3, 8, 11, 21, 27, 35).foldl(0, (sum, j) => sum + rows[j].trace.length()) == 10
    else if (i == 36) {
      val c = record(a, "composition")
      val t = record(a, "attempt")
      val result = record(a, "result")
      a.created.length() == 4 and native(a, "composition", List(rows[11].attempt))
        and c.dag == record(rows[4], "composition").dag and c.pin == rows[3].attempt
        and c.inputs == record(rows[4], "composition").inputs and t.dag == record(rows[7], "attempt").dag
        and native(a, "request", List(c.id)) and native(a, "result", List(r)) and native(a, "attempt", List(r, result.id))
        and t.id == a.commit and a.refs == List(createdRef("poison", a.commit))
    } else if (i == 38 or i == 39) {
      val d = if (i == 38) rows[17].commit else rows[23].commit
      a.transfer and a.commit == d and a.counts == List(4, 3, 3, 2, 1) and a.created.length() == 14
        and a.refs == List(createdRef(a.args[2], d))
    } else if (i == 40) a.transfer and a.commit == "" and a.unchanged and a.refs == List()
    else if (i == 41) replicaRead(a, rows[18])
    else if (i == 42) replicaRead(a, rows[24])
    else if (i == 43) {
      val c = record(a, "composition")
      val base = record(rows[22], "composition")
      a.created.length() == 1 and native(a, "composition", base.parents) and c.id == a.commit and c.pin == base.pin
        and c.inputs == record(rows[4], "composition").inputs and c.inputs != base.inputs
        and a.refs == List(createdRef("source-graft", a.commit))
    } else if (i == 45) {
      val c = record(a, "composition")
      val base = record(rows[14], "composition")
      a.created.length() == 1 and native(a, "composition", List(rows[3].attempt)) and c.id == a.commit
        and c.dag == base.dag and c.pin == base.pin and c.inputs == base.inputs
        and a.refs == List(createdRef("parent-graft", a.commit))
    } else if (i == 47) {
      val poison = rows[36]
      val d = record(a, "decision")
      a.created.length() == 5 and a.profiles == List() and d.id == a.commit
        and d.dag == record(rows[17], "decision").dag
        and native(a, "decision", List(record(rows[17], "request").id, poison.commit))
        and poison.created.foldl(true, (ok, row) => ok and
          a.created.foldl(false, (found, other) => found or row == other))
        and a.refs == List(createdRef("history-graft", a.commit))
    } else false
  }

  pure def verdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val wanted = story[i]
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if (not(a.preserved)) "changed_historical_records"
    else if (rejected.keys().contains(i)) {
      if (a.code == 1 and a.error == rejected.get(i) and a.commit == "" and a.unchanged
          and a.created == List() and a.refs == List()) "ok" else "wrong_rejection_or_rollback"
    } else if (a.code != 0 or a.error != "" or (a.op != "retire" and a.commit == "")) "unexpected_failure"
    else if (a.unchanged != Set("inspect", "retire").contains(a.op)) "wrong_write_boundary"
    else if (not(accepted(rows, i))) "wrong_native_or_reported_provenance"
    else "ok"
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.attempts.length() != story.length()) List("missing_steps")
    else range(0, story.length()).foldl(List(), (out, i) => out.append(verdict(row.attempts, i)))
  pure def verdictAccepted(value: str): bool = value == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and verdicts.length() == 1 and verdicts[0].length() == story.length()
      and verdicts[0].foldl(true, (ok, value) => ok and verdictAccepted(value))
      and evidence[0].attempts[18].outcome == "reuse" and evidence[0].attempts[24].outcome == "reuse"
      and evidence[0].attempts[33].outcome == "pending" and evidence[0].attempts[42].unchanged

  pure val q: Q = { ...noQ, request: "old-q", func: doubleFunc, composition: "old-c", map: "same-map",
    upstream: { ...noUpstream, attempt: "old-add" } }
  pure val old: Attempt = { op: "inspect", args: List(), code: 0, error: "", commit: "old-t", unchanged: true,
    preserved: true, transfer: false, refs: List(), main: "", counts: List(), profiles: List(), created: List(),
    requested: noQ, producing: q, trace: List(), outcome: "", selection: "", attempt: "old-t",
    result: "old-r", outer: "old-outer", value: 84 }
  pure val requested = { ...q, request: "new-q", composition: "new-c", upstream: { ...q.upstream, attempt: "new-add" } }
  pure val reused = { ...old, commit: "new-d", requested: requested, outcome: "reuse", selection: old.attempt }
  pure val controlsPass = replicaRead(reused, reused)
    and not(replicaRead({ ...reused, producing: requested }, reused))
    and not(replicaRead({ ...reused, requested: q }, reused))
    and not(replicaRead({ ...reused, producing: { ...q, upstream: requested.upstream } }, reused))
}
