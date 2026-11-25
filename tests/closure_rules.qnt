module closure_rules {
  import closure_histories.* from "./closure_histories"

  type Ref = { name: str, before: str, after: str }
  type Edge = { name: str, dag: str }
  type Input = { name: str, value: int }
  type Capture = { closure: str, descriptor: str, defaults: str, environment: str, captureKey: str,
    func: str, implementation: str, mapBinding: str, mapSource: str, listBinding: str, listSource: str,
    scaleSource: str, scaleOrigin: str, scale: int }
  type Q = { request: str, func: str, inputs: str, map: str, sources: List[Edge], capture: Capture }
  type Call = { operation: str, func: str, binding: str, inputs: str, datum: str, sources: List[Edge] }
  type Native = { id: str, role: str, dag: str, parents: List[str], capture: Capture,
    pin: str, selected: str, mode: str, outcome: str, inputs: str, map: str, func: str,
    sources: List[Edge], args: List[Input], trace: List[Call], traceBindings: List[str], traceKeys: List[str],
    traceValues: List[int], value: int, keyScale: int, keyFuncs: List[str] }
  type Attempt = { op: str, args: List[str], commit: str, code: int, error: str, unchanged: bool,
    main: str, preserved: bool, refs: List[Ref], transfer: bool, counts: List[int], selectedRef: str,
    created: List[Native], profiles: List[str], requested: Q, producing: Q, mode: str, outcome: str,
    selection: str, attempt: str, result: str, outer: str, value: int, trace: List[Call] }
  type Observation = { attempts: List[Attempt] }

  pure val intent = "urn:example:captured-scaled-sum"
  pure val mapGet = "dml://builtin/map/get"
  pure val listGet = "dml://builtin/list/get"
  pure val mapV1 = "dml://source/builtin/map/get/v1"
  pure val mapV2 = "dml://source/builtin/map/get/v2"
  pure val listV1 = "dml://source/builtin/list/get/v1"
  pure val noCapture: Capture = { closure: "", descriptor: "", defaults: "", environment: "", captureKey: "",
    func: "", implementation: "", mapBinding: "", mapSource: "", listBinding: "", listSource: "",
    scaleSource: "", scaleOrigin: "", scale: 0 }
  pure val noQ: Q = { request: "", func: "", inputs: "", map: "", sources: List(), capture: noCapture }
  pure val noNative: Native = { id: "", role: "", dag: "", parents: List(), capture: noCapture, pin: "",
    selected: "", mode: "", outcome: "", inputs: "", map: "", func: "", sources: List(), args: List(),
    trace: List(), traceBindings: List(), traceKeys: List(), traceValues: List(), value: 0, keyScale: 0, keyFuncs: List() }

  pure val roles = Map("defaults" -> "closure-example-defaults-v1", "closure" -> "closure-example-closure-v1",
    "request" -> "closure-example-request-v1", "decision" -> "closure-example-decision-v1",
    "attempt" -> "closure-example-attempt-v1", "result" -> "closure-example-result-v1")
  pure def record(a: Attempt, role: str): Native = {
    val found = a.created.foldl(List(), (out, row) => if (row.role == roles.get(role)) out.append(row) else out)
    if (found.length() == 1) found[0] else noNative
  }
  pure def native(n: Native, ps: List[str]): bool = n.id != "" and n.dag != "" and n.parents == ps
  pure def refDelta(name: str, before: str, after: str): Ref = { name: name, before: before, after: after }
  pure def newRef(name: str, id: str): Ref = refDelta(name, "", id)
  pure def sourceDag(sources: List[Edge], name: str): str =
    sources.foldl("", (out, edge) => if (edge.name == name) edge.dag else out)

  pure def defaultsRow(a: Attempt, previous: str, origin: str, getter: str, scale: int): bool = {
    val d = record(a, "defaults")
    val e = d.capture
    a.created.length() == 1 and native(d, if (previous == "") List() else List(previous))
      and d.id == a.commit and e.defaults == d.id and e.environment == d.dag
      and e.scale == scale and e.scaleOrigin == origin and e.scaleSource != ""
      and e.mapSource == getter and e.mapBinding != "" and e.listSource == listV1 and e.listBinding != ""
      and a.refs == List(refDelta(a.args[1], previous, d.id))
  }
  pure def captureRow(a: Attempt, d: Attempt): bool = {
    val c = record(a, "closure")
    val e = record(d, "defaults").capture
    a.created.length() == 1 and native(c, List(d.commit)) and c.id == a.commit
      and c.capture == { ...e, closure: c.id, descriptor: c.dag, captureKey: c.capture.captureKey,
        func: intent, implementation: "scaled-sum-python-v1" }
      and c.capture.captureKey != "" and c.keyScale == e.scale and c.keyFuncs == List(mapGet, listGet)
      and a.refs == List(newRef(a.args[3], c.id)) and a.profiles == List()
  }
  pure def equalKeyDifferentCapture(c: Capture, old: Capture): bool = c.captureKey == old.captureKey
    and c.closure != old.closure and c.descriptor != old.descriptor and c.environment != old.environment
    and c.mapBinding != old.mapBinding and c.mapSource == mapV2 and old.mapSource == mapV1
    and c.listBinding == old.listBinding and c.scale == old.scale
    and c.scaleOrigin != old.scaleOrigin and c.scaleSource != old.scaleSource

  pure def inputPair(a: int, b: int): List[Input] = List({ name: "a", value: a }, { name: "b", value: b })
  pure val standardInputs = inputPair(13, 29)
  pure val maxI64 = 9223372036854775807

  pure def qSpine(q: Native, c: str, inputs: List[Input]): bool = native(q, List(c)) and q.pin == c and q.func == intent
    and q.inputs != "" and q.map != "" and q.args == inputs
    and q.sources.length() == 2 and sourceDag(q.sources, "a") != "" and sourceDag(q.sources, "b") != ""
  pure def dSpine(d: Native, q: str, mode: str, selected: str, hit: bool): bool =
    native(d, if (selected == "") List(q) else List(q, selected)) and d.pin == q and d.selected == selected
      and d.mode == mode and d.outcome == (if (hit) "reuse" else "pending")
  pure def decisionRow(a: Attempt, c: Attempt, inputs: List[Input], mode: str, selected: str,
      hit: bool, previous: str, oldR: str): bool = {
    val q = record(a, "request")
    val d = record(a, "decision")
    val delta = List(newRef(a.args[4], d.id))
    val refs = if (not(hit)) delta.append(newRef(a.args[3], q.id))
      else if (previous == oldR) delta else delta.append(refDelta("main", previous, oldR))
    a.created.length() == 2 and qSpine(q, c.commit, inputs) and dSpine(d, q.id, mode, selected, hit)
      and d.id == a.commit and a.refs == refs and a.main == (if (hit) oldR else previous)
      and (not(hit) or a.profiles == List())
  }
  pure def workRow(a: Attempt, decision: Attempt, c: Attempt, previous: str, value: int): bool = {
    val q = record(decision, "request")
    val t = record(a, "attempt")
    val r = record(a, "result")
    val captured = record(c, "closure").capture
    a.created.length() == 2 and native(r, List(q.id)) and native(t, List(q.id, r.id))
      and t.id == a.commit and r.value == value and r.inputs == q.inputs
      and r.trace.length() == 2 and r.traceKeys == List("a", "b") and r.traceValues == List(13, 29)
      and r.traceBindings == List(captured.mapBinding, captured.mapBinding)
      and r.trace.foldl(true, (ok, call) => ok and call.operation != "" and call.datum != ""
        and call.inputs != "" and call.func == mapGet and call.binding == captured.mapSource
        and call.sources.length() == 2 and sourceDag(call.sources, "map") == q.inputs
        and sourceDag(call.sources, "key") != "")
      and a.main == r.id and a.refs == List(refDelta("main", previous, r.id), newRef(a.args[3], t.id))
  }

  pure def qRead(q: Q, captured: Capture, raw: Native): bool = q == {
    request: raw.id, func: raw.func, inputs: raw.inputs, map: raw.map, sources: raw.sources, capture: captured
  }
  pure def historicalRead(a: Attempt, old: Attempt): bool = a.producing == old.producing and a.trace == old.trace
    and a.attempt == old.attempt and a.result == old.result and a.outer == old.outer and a.value == old.value
  pure def attemptRead(a: Attempt, t: Attempt, d: Attempt, c: Attempt): bool = {
    val r = record(t, "result")
    a.commit == t.commit and a.attempt == t.commit and a.result == r.id and a.outer == r.dag
      and qRead(a.producing, record(c, "closure").capture, record(d, "request"))
      and a.trace == r.trace and a.value == r.value and a.requested == noQ
  }
  pure def decisionRead(a: Attempt, d: Attempt, c: Attempt): bool = {
    val decision = record(d, "decision")
    a.commit == d.commit and qRead(a.requested, record(c, "closure").capture, record(d, "request"))
      and a.outcome == decision.outcome and a.mode == decision.mode and a.selection == decision.selected
  }
  pure def pendingRead(a: Attempt, d: Attempt, c: Attempt): bool = decisionRead(a, d, c)
    and a.outcome == "pending" and a.producing == noQ and a.attempt == "" and a.result == ""
    and a.outer == "" and a.trace == List()
  pure def hitRead(a: Attempt, d: Attempt, c: Attempt, old: Attempt): bool = decisionRead(a, d, c)
    and a.outcome == "reuse" and a.selection == old.attempt and historicalRead(a, old)
    and a.requested.request != a.producing.request and a.requested.map == a.producing.map
    and a.requested.capture.captureKey == a.producing.capture.captureKey
  pure def replicaRead(a: Attempt, original: Attempt): bool = a.commit == original.commit
    and a.requested == original.requested and a.mode == original.mode and a.outcome == original.outcome
    and a.selection == original.selection and historicalRead(a, original)

  // The fixtures repin every affected commit. The poison is in the exact
  // capture, not in an unrelated dangling link or wrong Q-R-T ownership.
  pure def originalGraft(a: Attempt, old: Attempt, alternate: Capture): bool = {
    val c = record(a, "closure")
    val q = record(a, "request")
    val r = record(a, "result")
    val t = record(a, "attempt")
    val past = old.producing.capture
    native(c, List(alternate.defaults)) and c.dag == past.descriptor and c.id != past.closure
      and c.capture == { ...past, closure: c.id, defaults: alternate.defaults }
      and c.capture.environment != alternate.environment and c.keyScale == past.scale
      and qSpine(q, c.id, standardInputs) and q.map == old.producing.map and q.inputs == old.producing.inputs
      and native(r, List(q.id)) and r.dag == old.outer and r.trace == old.trace
      and native(t, List(q.id, r.id))
  }
  pure def requestGraft(a: Attempt, hit: Attempt, kind: str): bool = {
    val c = record(a, "closure")
    val q = record(a, "request")
    val d = record(a, "decision")
    val requested = hit.requested.capture
    val old = hit.producing.capture
    val changed = { ...requested, closure: c.id, descriptor: c.dag }
    val expected = if (kind == "source") { ...changed, environment: c.capture.environment,
      scaleSource: old.scaleSource, scaleOrigin: old.scaleOrigin }
      else if (kind == "binding") { ...changed, environment: c.capture.environment,
        mapBinding: old.mapBinding, mapSource: old.mapSource }
      else { ...changed, captureKey: c.capture.captureKey }
    a.created.length() == 3 and native(c, List(requested.defaults)) and c.capture == expected
      and c.id != requested.closure and c.dag != requested.descriptor and c.keyFuncs == List(mapGet, listGet)
      and (if (kind == "key") c.keyScale == 3 and c.capture.captureKey != requested.captureKey
           else c.keyScale == 2 and c.capture.environment != requested.environment)
      and qSpine(q, c.id, standardInputs) and q.map == hit.requested.map and q.inputs == hit.requested.inputs
      and dSpine(d, q.id, "require-selected", hit.attempt, true) and d.id == a.commit
      and a.refs == List(newRef(a.args[4], a.commit)) and a.profiles == List()
  }

  pure val rejected = Map(
    7 -> "capture: defaults ref does not match the expected commit or absence",
    15 -> "capture: invalid_state: ref already exists",
    17 -> "request: closure ref does not match the expected commit or absence",
    18 -> "request: selection ref does not match the expected commit or absence",
    19 -> "request: no selected attempt for the capture key and argument MAP",
    20 -> "request: reuse needs a new invocation ID, not the producing request",
    21 -> "request: invalid_state: ref already exists",
    25 -> "work: invalid_state: ref already exists",
    28 -> "request: no selected attempt for the capture key and argument MAP",
    34 -> "request: closure environment does not match its pinned defaults",
    36 -> "work: scaled sum subtotal is not a signed 64-bit integer",
    38 -> "work: scaled sum product is not a signed 64-bit integer",
    45 -> "inspect: closure environment does not match its pinned defaults",
    47 -> "inspect: closure environment does not match its pinned defaults",
    49 -> "inspect: capture key does not match the typed scale datum",
    51 -> "inspect: closure environment does not match its pinned defaults")

  pure def accepted(rows: List[Attempt], i: int): bool = {
    val a = rows[i]
    val first = rows[5]
    val hit = rows[23]
    val capA = record(rows[1], "closure").capture
    val capB = record(rows[16], "closure").capture
    val capC = record(rows[8], "closure").capture
    val previous = if (i > 0) rows[i - 1].main else ""
    if (i == 0) defaultsRow(a, "", "origin-a", mapV1, 2)
    else if (i == 1) captureRow(a, rows[0])
    else if (i == 2) decisionRow(a, rows[1], standardInputs, "fresh", "", false, previous, "")
    else if (i == 3) pendingRead(a, rows[2], rows[1])
    else if (i == 4) workRow(a, rows[2], rows[1], previous, 84)
    else if (i == 5) attemptRead(a, rows[4], rows[2], rows[1])
    else if (i == 6) defaultsRow(a, rows[0].commit, "origin-c", mapV2, 3) and a.main == previous
    else if (i == 8) captureRow(a, rows[6]) and capC.captureKey != capA.captureKey
    else if (i == 9)
      decisionRow(a, rows[1], standardInputs, "require-selected", first.attempt, true, previous, first.result)
    else if (i == 10) hitRead(a, rows[9], rows[1], first) and a.requested.capture == a.producing.capture
    else if (i == 11) decisionRow(a, rows[1], standardInputs, "fresh", "", false, previous, "")
    else if (i == 12) workRow(a, rows[11], rows[1], previous, 84) and a.profiles == List()
    else if (i == 13) attemptRead(a, rows[12], rows[11], rows[1])
      and a.producing.capture == first.producing.capture and a.producing.request != first.producing.request
      and a.result != first.result and a.outer == first.outer and a.trace == first.trace
    else if (i == 14) defaultsRow(a, "", "origin-b", mapV2, 2)
    else if (i == 16) captureRow(a, rows[14]) and equalKeyDifferentCapture(capB, capA)
      and capB.mapBinding == capC.mapBinding and capB.listBinding == capC.listBinding
    else if (i == 22)
      decisionRow(a, rows[16], standardInputs, "require-selected", first.attempt, true, previous, first.result)
    else if (i == 23) hitRead(a, rows[22], rows[16], first)
      and equalKeyDifferentCapture(a.requested.capture, a.producing.capture)
    else if (i == 24) decisionRow(a, rows[16], standardInputs, "fresh", "", false, previous, "")
    else if (i == 26) workRow(a, rows[24], rows[16], previous, 84)
    else if (i == 27) attemptRead(a, rows[26], rows[24], rows[16])
      and a.producing.map == first.producing.map and a.outer != first.outer and a.trace != first.trace
    else if (i == 29) decisionRow(a, rows[8], standardInputs, "try-selected", first.attempt, false, previous, "")
    else if (i == 30) pendingRead(a, rows[29], rows[8]) and a.requested.map == first.producing.map
      and a.requested.capture.captureKey != first.producing.capture.captureKey
    else if (i == 31) workRow(a, rows[29], rows[8], previous, 126)
    else if (i == 32) attemptRead(a, rows[31], rows[29], rows[8]) and a.producing == rows[30].requested
      and a.trace == rows[27].trace and a.counts == List(3, 3, 6, 6, 4, 4)
      and List(5, 13, 27, 32).foldl(0, (total, j) => total + rows[j].trace.length()) == 8
    else if (i == 33) originalGraft(a, first, capB) and a.created.length() == 4
      and a.commit == record(a, "attempt").id and a.profiles == List()
      and a.refs == List(newRef("poison", a.commit))
    else if (i == 35) decisionRow(a, rows[1], inputPair(maxI64, 1), "fresh", "", false, previous, "")
    else if (i == 37) decisionRow(a, rows[1], inputPair(maxI64, 0), "fresh", "", false, previous, "")
    else if (i == 39 or i == 40) {
      val from = if (i == 39) hit else rows[32]
      val counts = if (i == 39) List(2, 2, 2, 1, 1, 1) else List(2, 1, 1, 0, 1, 1)
      a.transfer and a.commit == from.commit and a.counts == counts and a.main == "" and a.selectedRef == ""
        and a.refs == List(newRef(a.args[2], from.commit))
    } else if (i == 41) a.transfer and a.unchanged and a.refs == List() and a.commit == ""
    else if (i == 42) replicaRead(a, hit)
    else if (i == 43) replicaRead(a, rows[32])
    else if (Set(44, 46, 48).contains(i)) requestGraft(a, hit, a.args[1])
    else if (i == 50) {
      val d = record(a, "decision")
      val t = record(a, "attempt")
      originalGraft(a, first, capB) and a.created.length() == 5 and a.profiles == List()
        and t.id == rows[33].commit and dSpine(d, hit.requested.request, "require-selected", t.id, true)
        and a.commit == d.id and a.refs == List(newRef("original-graft", d.id))
    } else false
  }

  pure def verdict(rows: List[Attempt], i: int): str = {
    val a = rows[i]
    val wanted = story[i]
    val read = Set("inspect", "retire").contains(a.op)
    if (a.op != wanted.op or a.args != wanted.args) "wrong_step"
    else if (not(a.preserved)) "changed_historical_records"
    else if (a.args[0] == "source" and i >= 4 and a.selectedRef != rows[4].commit) "changed_selected_ref"
    else if (rejected.keys().contains(i)) {
      if (a.code == 1 and a.error == rejected.get(i) and a.commit == "" and a.unchanged
          and a.created == List() and a.refs == List()) "ok" else "wrong_rejection_or_rollback"
    } else if (a.code != 0 or a.error != "" or (a.op != "retire" and a.commit == "")) "unexpected_failure"
    else if (a.unchanged != read or (read and (a.refs != List() or a.created != List()))) "wrong_write_boundary"
    else if (not(accepted(rows, i))) "wrong_native_or_reported_capture"
    else "ok"
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.attempts.length() != story.length()) List("missing_steps")
    else range(0, story.length()).foldl(List(), (out, i) => out.append(verdict(row.attempts, i)))
  pure def verdictAccepted(value: str): bool = value == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and verdicts.length() == 1 and verdicts[0].length() == story.length()
      and verdicts[0].foldl(true, (ok, value) => ok and verdictAccepted(value))
      and evidence[0].attempts[10].outcome == "reuse" and evidence[0].attempts[23].outcome == "reuse"
      and evidence[0].attempts[30].outcome == "pending" and evidence[0].attempts[32].value == 126
      and evidence[0].attempts[42].unchanged and evidence[0].attempts[43].unchanged

  pure val original = { ...noCapture, closure: "original", descriptor: "original-c", environment: "original-e",
    captureKey: "k2", scale: 2, scaleSource: "origin-a", scaleOrigin: "a", mapBinding: "v1", mapSource: mapV1 }
  pure val equivalent = { ...original, closure: "equivalent", descriptor: "equivalent-c", environment: "equivalent-e",
    scaleSource: "origin-b", scaleOrigin: "b", mapBinding: "v2", mapSource: mapV2 }
  pure val controlsPass = equalKeyDifferentCapture(equivalent, original)
    and not(equalKeyDifferentCapture({ ...equivalent, captureKey: "k3" }, original))
    and not(equalKeyDifferentCapture({ ...equivalent, mapBinding: "v1" }, original))
    and not(equalKeyDifferentCapture({ ...equivalent, scaleSource: "origin-a" }, original))
    and not(qRead({ ...noQ, capture: equivalent }, original, noNative))
}
