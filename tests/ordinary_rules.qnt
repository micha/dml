module ordinary_rules {
  import ordinary_histories.* from "./ordinary_histories"

  type Ref = { name: str, before: str, after: str }
  type Edge = { name: str, dag: str }
  type Input = { name: str, value: int }
  type InputMap = { dag: str, datum: str, sources: List[Edge], args: List[Input] }
  type Env = { dag: str, map: str, mapSource: str, list: str, listSource: str,
    add: str, addMap: str, double: str, doubleMap: str }
  type Getter = { dag: str, func: str, binding: str, source: str, map: str, key: str, value: int }
  type Result = { dag: str, inputs: str, returned: str, value: int, trace: List[Getter] }
  type Native = { id: str, role: str, dag: str, parents: List[str], env: Env, inputs: InputMap,
    target: str, selected: str, doubleSelected: str, mode: str, doubleMode: str, invocation: str,
    attempt: str, result: Result, trace: List[Getter] }
  type Field = { path: str, name: str, value: str }
  type CallEvent = { op: str, handles: List[int], labels: List[str] }
  type Attempt = { op: str, args: List[str], commit: str, code: int, error: str, head: str, main: str,
    refs: List[Ref], created: List[Native], profiles: List[str], report: List[Field],
    unchanged: bool, preserved: bool, transfer: bool, addedObjects: bool, calls: List[CallEvent] }
  type Observation = { attempts: List[Attempt] }

  pure val none: Native = { id: "", role: "", dag: "", parents: List(), target: "", selected: "",
    doubleSelected: "", mode: "", doubleMode: "", invocation: "", attempt: "", trace: List(),
    env: { dag: "", map: "", mapSource: "", list: "", listSource: "", add: "", addMap: "", double: "", doubleMap: "" },
    inputs: { dag: "", datum: "", sources: List(), args: List() },
    result: { dag: "", inputs: "", returned: "", value: 0, trace: List() } }
  pure val mapGet = "dml://builtin/map/get"
  pure val v1 = "dml://source/builtin/map/get/v1"
  pure val v2 = "dml://source/builtin/map/get/v2"
  pure val listV1 = "dml://source/builtin/list/get/v1"
  pure val fresh = "fresh"
  pure val trySelected = "try-selected"
  pure val requireSelected = "require-selected"

  pure def record(a: Attempt, role: str): Native = {
    val found = a.created.foldl(List(), (rows, record) => if (record.role == role) rows.append(record) else rows)
    if (found.length() == 1) found[0] else none
  }
  pure def ids(records: List[Native]): Set[str] = records.foldl(Set(), (seen, r) => seen.union(Set(r.id)))
  pure def native(row: Native, parents: List[str]): bool = row.id != "" and row.dag != "" and row.parents == parents
  pure def one(id: str): List[str] = if (id == "") List() else List(id)
  pure def ref(name: str, before: str, after: str): Ref = { name: name, before: before, after: after }
  pure def newRef(name: str, after: str): Ref = ref(name, "", after)
  pure def changes(a: Attempt, expected: Set[Ref]): bool = a.refs.length() == expected.size()
    and a.refs.foldl(Set(), (seen, delta) => seen.union(Set(delta))) == expected
  pure def published(a: Attempt, name: str, h: str, previous: str, main: str): bool =
    h != "" and a.head == h and a.main == main and changes(a, if (previous == main) Set(newRef(name, h))
      else Set(newRef(name, h), ref("main", previous, main)))
  pure def report(a: Attempt, path: str, name: str): str =
    a.report.foldl("", (value, entry) => if (entry.path == path and entry.name == name) entry.value else value)
  pure def source(input: InputMap, key: str): str =
    input.sources.foldl("", (out, edge) => if (edge.name == key) edge.dag else out)
  pure def returns(a: Attempt): int =
    a.profiles.foldl(0, (total, role) => total + (if (role == "builtin-return-v1") 1 else 0))

  pure def defaultsStep(a: Attempt, old: str, getter: str): bool = {
    val d = record(a, "defaults")
    val e = d.env
    a.created.length() == 1 and native(d, one(old)) and a.commit == d.id and a.head == d.id
      and e.dag == d.dag and e.map != "" and e.list != "" and e.add != "" and e.double != "" and e.add != e.double
      and e.addMap == e.map and e.doubleMap == e.map and e.mapSource == getter and e.listSource == listV1
      and changes(a, Set(ref("defaults", old, d.id)))
  }
  pure def captureStep(a: Attempt, d: Attempt, previous: str): bool = {
    val c = record(a, "capture")
    a.created.length() == 1 and native(c, List(d.commit)) and c.env == record(d, "defaults").env
      and a.commit == c.id and a.profiles == List()
      and published(a, a.args[3], c.id, previous, previous)
  }
  pure def ab(a: int, b: int): List[Input] = List({ name: "a", value: a }, { name: "b", value: b })
  pure def inputView(view: InputMap, args: List[Input]): bool = view.dag != "" and view.datum != ""
    and view.args == args and view.sources.length() == args.length()
    and args.foldl(true, (ok, arg) => ok and source(view, arg.name) != "")
  pure def outerQ(row: Native, cap: Native, inputs: List[Input], mode: str, selected: str,
      doubleMode: str, doubleSelected: str): bool = {
    native(row, List(cap.id).concat(one(selected)).concat(one(doubleSelected)))
      and row.mode == mode and row.selected == selected and row.doubleMode == doubleMode
      and row.doubleSelected == doubleSelected and row.invocation != "" and inputView(row.inputs, inputs)
  }
  pure def getterMatches(getter: Getter, arg: Input, inputs: InputMap, binding: str, uri: str): bool =
    getter.dag != "" and getter.func == mapGet and getter.map == inputs.dag and getter.binding == binding
      and getter.source == uri and getter.key == arg.name and getter.value == arg.value
  pure def traceMatches(trace: List[Getter], inputs: InputMap, binding: str, uri: str): bool =
    trace.length() == inputs.args.length()
      and range(0, trace.length()).foldl(true, (ok, i) => ok and getterMatches(trace[i], inputs.args[i], inputs, binding, uri))
  pure def leafResult(r: Result, q: Native, binding: str, uri: str, value: int): bool =
    r.dag != "" and r.returned != "" and r.inputs == q.inputs.dag and r.value == value
      and traceMatches(r.trace, q.inputs, binding, uri)
  pure def addChain(a: Attempt, cap: Native, expected: List[Input], outerMode: str, outerSel: str,
      innerMode: str, innerSel: str): bool = {
    val q = record(a, "outer-request")
    val start = record(a, "start")
    val aq = record(a, "add-request")
    val at = record(a, "add-attempt")
    val env = cap.env
    outerQ(q, cap, expected, outerMode, outerSel, innerMode, innerSel)
      and native(start, List(q.id)) and native(aq, List(start.id)) and native(at, List(aq.id))
      and start.attempt != "" and aq.invocation != "" and at.attempt != "" and aq.target == env.add
      and aq.inputs == q.inputs and traceMatches(at.trace, q.inputs, env.map, env.mapSource)
      and leafResult(at.result, aq, env.addMap, env.mapSource, expected[0].value + expected[1].value)
  }
  pure def doubleQ(dq: Native, add: Native, target: str): bool =
    native(dq, List(add.id)) and dq.invocation != "" and dq.target == target
      and inputView(dq.inputs, List({ name: "x", value: add.result.value }))
      and source(dq.inputs, "x") == add.result.dag
  pure def finishedChain(a: Attempt, cap: Native, oldDouble: Native, hit: bool): bool = {
    val add = record(a, "add-attempt")
    val dq = record(a, "double-request")
    val number = 2 * add.result.value
    val dt = record(a, if (hit) "double-hit" else "double-attempt")
    val f = record(a, "finished")
    val env = cap.env
    val produced = if (hit) oldDouble.result else dt.result
    val oq = record(a, "outer-request")
    a.created.length() == 7 and doubleQ(dq, add, env.double)
      and (if (hit) native(dt, List(dq.id, oldDouble.id)) and returns(a) == 1 and dt.result == none.result
           else native(dt, List(dq.id)) and dt.attempt != ""
             and leafResult(dt.result, dq, env.doubleMap, env.mapSource, number))
      and native(f, List(dt.id)) and f.result.dag == f.dag and f.result.returned == produced.dag
      and f.result.inputs == oq.inputs.dag and f.result.value == number and f.result.trace == add.trace
      and a.commit == f.id
  }
  pure def successChain(a: Attempt, cap: Native, oldDouble: Native, hit: bool, previous: str): bool =
    finishedChain(a, cap, oldDouble, hit) and published(a, a.args[3], a.commit, previous, a.commit)
  pure def addPrefix(a: Attempt, cap: Native, expected: List[Input], innerMode: str, selected: str,
      previous: str, output: str): bool = a.created.length() == 4 and returns(a) == 1 and a.commit == ""
    and addChain(a, cap, expected, fresh, "", innerMode, selected)
    and published(a, output, record(a, "add-attempt").id, previous, previous)
  pure def missPrefix(a: Attempt, cap: Native, expected: List[Input], innerMode: str, selected: str,
      previous: str): bool = addPrefix(a, cap, expected, innerMode, selected, previous, a.args[3])
  pure def outerHit(a: Attempt, cap: Native, first: Attempt, previous: str): bool = {
    val q = record(a, "outer-request")
    val t = record(a, "hit")
    a.created.length() == 2 and a.profiles == List() and native(t, List(q.id)) and a.commit == t.id
      and outerQ(q, cap, ab(13, 29), requireSelected, first.commit, fresh, "")
      and q.inputs == record(first, "outer-request").inputs and q.id != record(first, "outer-request").id
      and q.invocation != record(first, "outer-request").invocation
      and published(a, a.args[3], t.id, previous, first.commit)
  }
  pure def outerReport(a: Attempt, path: str, q: Native): bool =
    report(a, path, "request") == q.id and report(a, path, "capture") == q.parents[0]
      and report(a, path, "inputs") == q.inputs.dag and report(a, path, "argument_map") == q.inputs.datum
  pure def doubleReport(a: Attempt, path: str, q: Native, add: Native): bool =
    report(a, path, "request") == q.id and report(a, path, "target") == q.target
      and report(a, path, "inputs") == q.inputs.dag and report(a, path, "argument_map") == q.inputs.datum
      and report(a, path, "upstream_attempt") == add.id and report(a, path, "upstream_return") == add.result.dag
  pure def terminalReport(a: Attempt, route: Attempt, producing: Attempt, producerDouble: Attempt,
      status: str): bool = {
    val finish = record(producing, "finished")
    val past = record(producerDouble, "double-attempt")
    a.commit == route.commit and report(a, "", "status") == status and report(a, "", "value") == "84"
      and outerReport(a, "/requested", record(route, "outer-request"))
      and outerReport(a, "/producing", record(producing, "outer-request"))
      and doubleReport(a, "/double/requested", record(producing, "double-request"), record(producing, "add-attempt"))
      and doubleReport(a, "/double/producing", record(producerDouble, "double-request"), record(producerDouble, "add-attempt"))
      and report(a, "/double", "attempt") == past.id and report(a, "/double", "return_dag") == past.result.dag
      and report(a, "", "result") == finish.id and report(a, "", "return_dag") == finish.result.returned
      and report(a, "", "attempt") == record(producing, "start").id
      and report(a, "/trace/0", "operation") == finish.result.trace[0].dag
      and report(a, "/trace/1", "operation") == finish.result.trace[1].dag
      and report(a, "/double/trace/0", "operation") == past.result.trace[0].dag
  }
  pure def prefixReport(a: Attempt, call: Attempt): bool =
    a.commit == call.head and report(a, "", "status") == "add"
      and outerReport(a, "/requested", record(call, "outer-request"))
      and report(a, "/add", "attempt") == record(call, "add-attempt").id
      and report(a, "/add", "return_dag") == record(call, "add-attempt").result.dag
      and report(a, "", "return_dag") == "" and report(a, "/double/requested", "request") == ""
  pure def forge(a: Attempt, original: Attempt, alternate: Attempt, double: bool, previous: str): bool = {
    val oldQ = record(original, "double-request")
    val expected = record(alternate, "double-request").inputs
    val q = record(a, "double-request")
    val oldT = record(original, if (double) "double-attempt" else "double-hit")
    val t = record(a, if (double) "double-attempt" else "double-hit")
    val f = record(a, "finished")
    val oldF = record(original, "finished")
    val tip = if (double) t.id else f.id
    a.created.length() == (if (double) 2 else 3) and a.profiles == List()
      and q.id != oldQ.id and native(q, oldQ.parents) and q.inputs == expected and q.invocation == oldQ.invocation
      and q.inputs.datum == oldQ.inputs.datum and source(q.inputs, "x") != source(oldQ.inputs, "x")
      and t.id != oldT.id and t.dag == oldT.dag and t.result == oldT.result
      and native(t, List(q.id).concat(if (double) List() else List(oldT.parents[1])))
      and (double or (native(f, List(t.id)) and f.dag == oldF.dag and f.result == oldF.result and f.id != oldF.id))
      and a.commit == tip and published(a, a.args[4], tip, previous, previous)
  }

  pure val rejected = Map(
    14 -> "invoke: no selected outer attempt for the capture and argument MAP",
    15 -> "invoke: no selected double attempt for the captured leaf and argument MAP",
    16 -> "invoke: double result is not a signed 64-bit integer",
    17 -> "invoke: output ref does not match the expected commit or absence",
    18 -> "invoke: capture ref does not match the expected commit or absence",
    19 -> "invoke: selection ref does not match the expected commit or absence",
    20 -> "invoke: selection ref does not match the expected commit or absence",
    22 -> "invoke: double did not take the exact add return node",
    24 -> "invoke: double did not take the exact add return node",
    33 -> "inspect: double did not take the exact add return node")

  pure def accepted(rows: List[Attempt], i: int): bool = {
    val a = rows[i]
    val first = rows[2]
    val outer = rows[8]
    val inner = rows[10]
    val oldDouble = record(first, "double-attempt")
    val pastDoubleQ = record(first, "double-request")
    val c1 = record(rows[1], "capture")
    val c2 = record(rows[6], "capture")
    val previous = if (i == 0 or a.args[0] == "replica") "" else rows[i - 1].main
    if (rejected.keys().contains(i)) {
      val failure = a.code == 1 and a.error == rejected.get(i) and a.commit == "" and a.report == List()
      if (i == 15) failure and missPrefix(a, c1, ab(13, 31), requireSelected, oldDouble.id, previous)
      else if (i == 16) failure and missPrefix(a, c1, ab(4611686018427387904, 0), fresh, "", previous)
      else failure and a.unchanged and a.main == previous and a.created == List() and a.profiles == List() and a.refs == List()
        and a.head == (if (i == 17) first.commit else if (i == 33) rows[32].commit else "")
    } else if (a.code != 0 or a.error != "") false
    else if (i == 0) defaultsStep(a, "", v1) and a.main == ""
    else if (i == 1) captureStep(a, rows[0], previous)
    else if (i == 2 or i == 7) {
      val shape = addChain(a, c1, ab(13, 29), fresh, "", fresh, "")
        and successChain(a, c1, none, false, previous)
      if (i == 2) shape and returns(a) == 2
      else shape and a.profiles == List()
        and record(a, "outer-request").inputs == record(first, "outer-request").inputs
        and record(a, "start").attempt != record(first, "start").attempt
        and record(a, "add-attempt").id != record(first, "add-attempt").id
        and record(a, "double-attempt").id != oldDouble.id and record(a, "double-attempt").result == oldDouble.result
    } else if (i == 3) terminalReport(a, first, first, first, "finished")
    else if (i == 4) a.created == List() and a.profiles == List() and a.commit == oldDouble.id
      and published(a, "old-double", oldDouble.id, previous, previous)
    else if (i == 5) defaultsStep(a, rows[0].commit, v2) and a.main == previous
    else if (i == 6) captureStep(a, rows[5], previous) and c2.env.add != c1.env.add and c2.env.double != c1.env.double
      and c2.env.map != c1.env.map and c2.env.list == c1.env.list
    else if (i == 8) outerHit(a, c1, first, previous)
    else if (i == 9) terminalReport(a, outer, first, first, "hit")
    else if (i == 10) {
      val q = record(a, "double-request")
      addChain(a, c1, ab(29, 13), trySelected, first.commit, requireSelected, oldDouble.id)
        and successChain(a, c1, oldDouble, true, previous) and q.id != pastDoubleQ.id
        and q.invocation != pastDoubleQ.invocation and q.inputs.datum == pastDoubleQ.inputs.datum and source(q.inputs, "x") != source(pastDoubleQ.inputs, "x")
        and record(a, "outer-request").inputs.datum != record(first, "outer-request").inputs.datum
    } else if (i == 11) terminalReport(a, inner, inner, first, "finished")
    else if (i == 12) addChain(a, c1, ab(13, 30), fresh, "", trySelected, oldDouble.id)
      and successChain(a, c1, none, false, previous) and returns(a) == 2
      and record(a, "double-request").inputs.datum != pastDoubleQ.inputs.datum
    else if (i == 13) addChain(a, c2, ab(13, 29), trySelected, first.commit, trySelected, oldDouble.id)
      and successChain(a, c2, none, false, previous) and returns(a) == 2
      and record(a, "outer-request").inputs.datum == record(first, "outer-request").inputs.datum
      and record(a, "double-request").inputs.datum == pastDoubleQ.inputs.datum
      and record(a, "double-request").target != pastDoubleQ.target
    else if (i == 21 or i == 32) forge(a, inner, first, false, previous)
    else if (i == 23) forge(a, first, inner, true, previous)
    else if (i == 25 or i == 26) prefixReport(a, rows[i - 10])
    else if (i == 27 or i == 28) {
      val target = if (i == 27) outer.commit else inner.commit
      val expected = if (i == 27) ids(outer.created.concat(first.created).concat(rows[1].created).concat(rows[0].created))
        else ids(inner.created)
      a.transfer and a.commit == target and a.created.length() == expected.size()
        and ids(a.created) == expected and published(a, a.args[2], target, "", "")
    } else if (i == 29) a.transfer and a.commit == "" and a.unchanged and a.refs == List() and a.main == rows[24].main
    else if (i == 30 or i == 31) {
      val original = if (i == 30) rows[9] else rows[11]
      a.main == "" and a.commit == original.commit and a.report == original.report
    } else false
  }

  pure def selectedStep(a: Attempt, name: str, target: str, main: str): bool =
    a.created == List() and not(a.addedObjects) and a.commit == target and published(a, name, target, main, main)
  pure def bookmarkCommit(a: Attempt, add: str, main: str, old: str, replacement: str): bool =
    a.head == add and a.main == main and a.created == List() and not(a.addedObjects)
      and changes(a, Set(ref("selected", old, replacement)))
  pure def pinningAccepted(rows: List[Attempt], i: int): bool = {
    val a = rows[i]
    val c = record(rows[1], "capture")
    val first = rows[2]
    val old = record(first, "double-attempt")
    val alternate = rows[4]
    val replacement = record(alternate, "double-attempt")
    val call = rows[6]
    val prefix = rows[7]
    val add = record(prefix, "add-attempt")
    val previous = alternate.commit
    if (a.code != 0 or a.error != "") false
    else if (i == 0) defaultsStep(a, "", v1) and a.main == ""
    else if (i == 1) captureStep(a, rows[0], "")
    else if (i == 2) addChain(a, c, ab(13, 29), fresh, "", fresh, "")
      and successChain(a, c, none, false, "")
    else if (i == 3) selectedStep(a, "selected", old.id, first.commit)
    else if (i == 4) addChain(a, c, ab(13, 30), fresh, "", fresh, "")
      and successChain(a, c, none, false, first.commit)
      and record(a, "double-request").inputs.datum != record(first, "double-request").inputs.datum
    else if (i == 5) selectedStep(a, "replacement", replacement.id, previous)
    else if (i == 6) finishedChain(a, c, old, true) and a.head == a.commit and a.main == a.commit
      and changes(a, Set(newRef("pinned", a.commit), ref("main", previous, a.commit),
        ref("selected", old.id, replacement.id)))
    else if (i == 7) addPrefix(a, c, ab(29, 13), requireSelected, old.id, previous, "pinned")
      and ids(a.created).subseteq(ids(call.created)) and add.id == record(call, "add-attempt").id
    else if (i == 8) a.commit == replacement.id and a.unchanged
    else if (i == 9) bookmarkCommit(a, add.id, previous, old.id, replacement.id)
    else if (i == 10 and call.code == 0) terminalReport(a, call, call, first, "finished")
    else false
  }

  pure def event(op: str, handles: List[int], labels: List[str]): CallEvent =
    { op: op, handles: handles, labels: labels }
  pure val ownedHandoff: List[CallEvent] = {
    // Python assigns tokens by first observation, not by node value or native ID.
    val original = 0
    val addTarget = 1
    val doubleTarget = 2
    val sum = 3
    val downstream = 4
    val result = 5
    List(
      event("outer", List(original, addTarget, doubleTarget), List()),
      event("invoke", List(addTarget, original), List()),
      event("leaf", List(), List("ordinary-example-add-v1")),
      event("invoke-return", List(sum), List()),
      event("make-arguments", List(sum), List("x")),
      event("arguments-return", List(downstream), List()),
      event("invoke", List(doubleTarget, downstream), List()),
      event("leaf", List(), List("ordinary-example-double-v1")),
      event("invoke-return", List(result), List()),
      event("outer-return", List(result), List())
    )
  }
  pure def ownershipAccepted(rows: List[Attempt], i: int): bool = {
    val a = rows[i]
    val cap = record(rows[1], "capture")
    val call = rows[2]
    if (a.code != 0 or a.error != "") false
    else if (i == 0) defaultsStep(a, "", v1) and a.main == ""
    else if (i == 1) captureStep(a, rows[0], "")
    else if (i == 2) addChain(a, cap, ab(13, 29), fresh, "", fresh, "")
      and successChain(a, cap, none, false, "") and returns(a) == 2
    else if (i == 3) terminalReport(a, call, call, call, "finished")
      and report(a, "/add/requested", "inputs") == record(call, "outer-request").inputs.dag
      and report(a, "/add", "return_dag") == record(call, "add-attempt").result.dag
    else false
  }

  pure def observedStep(a: Attempt, request: Request): str = {
    val read = request.op == "inspect" or request.op == "retire"
    if (a.op != request.op or a.args != request.args) "wrong_step"
    else if (not(a.preserved)) "changed_historical_records"
    else if (read and (not(a.unchanged) or a.created != List() or a.refs != List())) "inspection_wrote_records"
    else if (a.op == "inspect" and a.commit != "" and a.commit != a.head) "wrong_inspection_pin"
    else "ok"
  }
  pure def historyVerdicts(row: Observation): List[str] = {
    val rows = row.attempts
    if (rows.length() == story.length()) range(0, story.length()).foldl(List(), (out, i) => {
      val observed = observedStep(rows[i], story[i])
      out.append(if (observed != "ok") observed
        else if (accepted(rows, i)) "ok" else "wrong_call_boundary_or_history")
    })
    else if (rows.length() == pinning.length()) range(0, pinning.length()).foldl(List(), (out, i) => {
      val observed = observedStep(rows[i], pinning[i])
      out.append(if (observed != "ok") observed
        else if (pinningAccepted(rows, i)) "ok"
        else if (i == 6) "wrong_pinned_double_producer"
        else "wrong_bookmark_interleaving")
    })
    else if (rows.length() == ownership.length()) range(0, ownership.length()).foldl(List(), (out, i) => {
      val observed = observedStep(rows[i], ownership[i])
      val expectedCalls = if (i == 2) ownedHandoff else List()
      out.append(if (observed != "ok") observed
        else if (not(ownershipAccepted(rows, i))) "wrong_owned_call_history"
        else if (rows[i].calls != expectedCalls) "wrong_owned_node_handoff"
        else "ok")
    })
    else List("missing_steps")
  }
  pure def verdictAccepted(result: str): bool = result == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 3 and verdicts.length() == 3
      and verdicts[0].length() == story.length() and verdicts[1].length() == pinning.length()
      and verdicts[2].length() == ownership.length()
      and verdicts.foldl(true, (ok, row) => ok and row.foldl(true, (accepted, result) => accepted and verdictAccepted(result)))
      and report(evidence[0].attempts[9], "", "status") == "hit"
      and record(evidence[0].attempts[10], "double-hit").id != ""
      and record(evidence[0].attempts[15], "add-attempt").id != ""
      and record(evidence[0].attempts[16], "add-attempt").id != ""
      and evidence[0].attempts[30].unchanged and evidence[0].attempts[31].unchanged

  pure val sampleAdd = { ...none, id: "new-add", result: { ...none.result, dag: "new-add-return", value: 42 } }
  pure val sampleQ: Native = { ...none, id: "double-q", dag: "double-request", target: "double", invocation: "inner-attempt",
    parents: List("new-add"), inputs: { dag: "x-input", datum: "x42", args: List({ name: "x", value: 42 }),
      sources: List({ name: "x", dag: "new-add-return" }) } }
  pure val wrongSource = { ...sampleQ, inputs: { ...sampleQ.inputs, sources: List({ name: "x", dag: "old-add-return" }) } }
  pure val controlsPass = doubleQ(sampleQ, sampleAdd, "double") and not(doubleQ(wrongSource, sampleAdd, "double"))
    and not(doubleQ({ ...sampleQ, parents: List("old-add") }, sampleAdd, "double"))
    and not(doubleQ({ ...sampleQ, target: "other" }, sampleAdd, "double"))
}
