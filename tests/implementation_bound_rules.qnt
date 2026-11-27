module implementation_bound_rules {
  import implementation_bound_histories as histories from "./implementation_bound_histories"
  import ordinary_rules as ordinary from "./ordinary_rules"

  type Attempt = { op: str, args: List[str], commit: str, code: int, error: str, head: str, main: str,
    refs: List[ordinary::Ref], created: List[ordinary::Native], profiles: List[str], report: List[ordinary::Field],
    unchanged: bool, preserved: bool, transfer: bool, addedObjects: bool, calls: List[ordinary::CallEvent] }
  type Closure = { dag: str, fields: int, roleAtRoot: bool, role: str, intent: str, implementation: str,
    links: List[ordinary::Edge] }
  type Observation = { attempts: List[Attempt], closures: List[Closure] }

  pure val uris = Map(
    "sum-then-double" -> ("urn:dml:example:ordinary:sum-then-double",
      "urn:dml:example:ordinary:sum-then-double:v1", "urn:dml:example:ordinary:sum-then-double:v2"),
    "add" -> ("urn:dml:example:ordinary:add", "urn:dml:example:ordinary:add:v1", "urn:dml:example:ordinary:add:v2"),
    "double" -> ("urn:dml:example:ordinary:double", "urn:dml:example:ordinary:double:v1",
      "urn:dml:example:ordinary:double:v2"))
  pure def intent(name: str): str = uris.get(name)._1
  pure def implementation(name: str, version: str): str =
    if (version == "v1") uris.get(name)._2 else uris.get(name)._3
  pure def link(name: str, dag: str): ordinary::Edge = { name: name, dag: dag }
  pure def closureMatches(c: Closure, dag: str, name: str, version: str, deps: List[ordinary::Edge]): bool =
    c.dag == dag and dag != "" and c.roleAtRoot and c.role == "implementation-call-closure-v1" and
    c.fields == deps.length() + 3 and c.intent == intent(name) and
    c.implementation == implementation(name, version) and c.links == deps
  pure def captureLinks(closures: List[Closure], env: ordinary::Env, version: str): bool = {
    val primitiveLinks = List(link("list-get", env.list), link("map-get", env.map))
    val outerLinks = List(link("add", env.add), link("double", env.double)).concat(primitiveLinks)
    env.map != "" and env.list != "" and env.addMap == env.map and env.doubleMap == env.map and
      closures.select(c => closureMatches(c, env.dag, "sum-then-double", version, outerLinks)).length() == 1 and
      closures.select(c => closureMatches(c, env.add, "add", version, primitiveLinks)).length() == 1 and
      closures.select(c => closureMatches(c, env.double, "double", version, primitiveLinks)).length() == 1
  }

  pure def defaultsStep(a: Attempt, old: str, getter: str, main: str): bool = {
    val d = ordinary::record(a, "implementation-defaults")
    a.created.length() == 1 and ordinary::native(d, ordinary::one(old)) and a.commit == d.id and a.head == d.id and
      d.env.dag == d.dag and d.env.mapSource == getter and d.env.listSource == ordinary::listV1 and a.main == main and
      ordinary::changes(a, Set(ordinary::ref("defaults", old, d.id)))
  }
  pure def captureStep(a: Attempt, d: Attempt, main: str): bool = {
    val c = ordinary::record(a, "capture")
    a.created.length() == 1 and ordinary::native(c, List(d.commit)) and
      c.env == ordinary::record(d, "implementation-defaults").env and a.commit == c.id and not(a.unchanged) and
      a.profiles == List() and ordinary::published(a, a.args[3], c.id, main, main)
  }

  pure def scopeAt(depth: int): ordinary::CallEvent = ordinary::event("scope-invoke", List(depth), List())
  pure def leafAt(depth: int, kind: str): ordinary::CallEvent =
    ordinary::event("leaf-adapter", List(depth),
      List(if (kind == "add") "ordinary-example-add-v1" else "ordinary-example-double-v1"))
  pure def freshDispatch(doubleReused: bool): List[ordinary::CallEvent] = List(
    scopeAt(0), ordinary::event("outer-adapter", List(1), List()),
    scopeAt(1), scopeAt(1), // outer get(a), get(b)
    scopeAt(1), leafAt(2, "add"), scopeAt(2), scopeAt(2), // add, get(a), get(b)
    scopeAt(1) // double
  ).concat(if (doubleReused) List() else List(leafAt(2, "double"), scopeAt(2)))

  pure def exactInputsDiffer(own: ordinary::InputMap, old: ordinary::InputMap): bool =
    own.dag != old.dag and own.datum == old.datum and own.args == old.args and own.sources != old.sources
  pure def outerReuse(a: Attempt, cap: ordinary::Native, first: Attempt, main: str): bool = {
    val q = ordinary::record(a, "outer-request")
    val oldQ = ordinary::record(first, "outer-request")
    val h = ordinary::record(a, "hit")
    a.created.length() == 2 and ordinary::native(h, List(q.id)) and a.commit == h.id and
      ordinary::outerQ(q, cap, ordinary::ab(13, 29), ordinary::requireSelected, first.commit, ordinary::fresh, "") and
      q.id != oldQ.id and q.invocation != oldQ.invocation and exactInputsDiffer(q.inputs, oldQ.inputs) and
      ordinary::source(q.inputs, "a") != ordinary::source(oldQ.inputs, "a") and
      ordinary::source(q.inputs, "b") != ordinary::source(oldQ.inputs, "b") and
      a.profiles == List("builtin-arguments-v1", "builtin-literal-source-v1", "builtin-literal-source-v1") and
      ordinary::published(a, a.args[3], h.id, main, first.commit) and a.calls == List()
  }
  pure def doubleReuse(a: Attempt, cap: ordinary::Native, first: Attempt, main: str): bool = {
    val oldT = ordinary::record(first, "double-attempt")
    val oldQ = ordinary::record(first, "double-request")
    val q = ordinary::record(a, "double-request")
    q.id != oldQ.id and q.invocation != oldQ.invocation and q.target != oldQ.target and
      exactInputsDiffer(q.inputs, oldQ.inputs) and
      ordinary::addChain(a, cap, ordinary::ab(13, 29), ordinary::fresh, "", ordinary::requireSelected, oldT.id) and
      ordinary::successChain(a, cap, oldT, true, main) and a.calls == freshDispatch(true)
  }

  pure def reportTarget(a: Attempt, path: str, name: str, version: str, idField: str, id: str, uri: str): bool = {
    ordinary::report(a, path, "intent") == intent(name) and
      ordinary::report(a, path, "implementation") == implementation(name, version) and
      ordinary::report(a, path, idField) == id and ordinary::report(a, path, "map_source") == uri
  }
  pure def outerReport(a: Attempt, path: str, c: ordinary::Native, getter: str, version: str): bool =
    reportTarget(a, path, "sum-then-double", version, "environment", c.env.dag, getter)
  pure def doubleReport(a: Attempt, path: str, c: ordinary::Native, getter: str, version: str): bool =
    reportTarget(a, path, "double", version, "target", c.env.double, getter)
  pure def acceptedRead(a: Attempt, main: str): bool = a.unchanged and a.refs == List() and a.created == List() and
    a.profiles == List() and a.calls == List() and a.main == main and a.commit == a.head and a.report != List()
  pure def rejected(a: Attempt, error: str, main: str): bool =
    a.code == 1 and a.error == error and a.commit == "" and a.head == "" and a.main == main and a.unchanged and
      a.refs == List() and a.created == List() and a.profiles == List() and a.report == List() and a.calls == List()

  pure def stepVerdict(row: Observation, i: int): str = {
    val rows = row.attempts
    val a = rows[i]
    val want = histories::storyBound[i]
    val first = rows[2]
    val ca = ordinary::record(rows[1], "capture")
    val cb = ordinary::record(rows[6], "capture")
    val main = if (i == 0) "" else rows[i - 1].main
    if (a.op != want.op or a.args != want.args) "wrong_step"
    else if (i == 15) {
      if (rejected(a, "invoke: no selected outer attempt for the intent and argument MAP", main)) "ok" else "wrong_map_miss"
    } else if (i == 16) {
      if (rejected(a, "invoke: selection ref does not match the expected commit or absence", main)) "ok" else "wrong_pin"
    } else if (i == 18) {
      if (rejected(a, "invoke: double did not take the exact add return node", main)) "ok" else "wrong_poison"
    } else if (a.code != 0 or a.error != "" or not(a.preserved)) "unexpected_outcome"
    else if (i == 0 or i == 5) {
      val old = if (i == 0) "" else rows[0].commit
      val v = if (i == 0) ordinary::v1 else ordinary::v2
      if (defaultsStep(a, old, v, main)) "ok" else "wrong_defaults"
    } else if (i == 1 or i == 6) {
      val e = ordinary::record(a, "capture").env
      val v = if (i == 1) "v1" else "v2"
      if (not(captureStep(a, rows[i - 1], main))) "wrong_capture"
      else if (not(captureLinks(row.closures, e, v))) "wrong_closure_links"
      else if (i == 6 and (e.list != ca.env.list or e.map == ca.env.map or e.dag == ca.env.dag or
          e.add == ca.env.add or e.double == ca.env.double)) "wrong_version_change"
      else "ok"
    } else if (i == 2 or i == 9 or i == 13) {
      val cap = if (i == 9) cb else ca
      val args = ordinary::ab(13, if (i == 13) 30 else 29)
      val mode = if (i == 13) ordinary::trySelected else ordinary::fresh
      val selected = if (i == 13) first.commit else ""
      if (ordinary::addChain(a, cap, args, mode, selected, ordinary::fresh, "") and
          ordinary::successChain(a, cap, ordinary::none, false, main) and a.calls == freshDispatch(false) and
          (i != 9 or (ordinary::record(a, "outer-request").inputs == ordinary::record(rows[7], "outer-request").inputs and
            ordinary::record(a, "start").id != ordinary::record(first, "start").id))) "ok"
      else "wrong_fresh_execution"
    } else if (i == 4) {
      val oldT = ordinary::record(first, "double-attempt")
      if (ordinary::selectedStep(a, "old-double", oldT.id, main)) "ok" else "wrong_selection"
    } else if (i == 7) {
      if (outerReuse(a, cb, first, main)) "ok" else "wrong_outer_reuse"
    } else if (i == 11) {
      if (doubleReuse(a, cb, first, main)) "ok" else "wrong_double_reuse"
    } else if (i == 3 or i == 8 or i == 10 or i == 12) {
      val route = rows[i - 1]
      val producer = if (i == 8) first else route
      val doubleProducer = if (i == 8 or i == 12) first else route
      val generation = if (i == 3) ca else cb
      val producing = if (i == 3 or i == 8) ca else cb
      val doubleVersion = if (i == 10) cb else ca
      if (acceptedRead(a, main) and ordinary::terminalReport(a, route, producer, doubleProducer,
          if (i == 8) "hit" else "finished") and
          outerReport(a, "/requested", generation, generation.env.mapSource, if (i == 3) "v1" else "v2") and
          outerReport(a, "/producing", producing, producing.env.mapSource, if (i == 3 or i == 8) "v1" else "v2") and
          doubleReport(a, "/double/requested", producing, producing.env.mapSource, if (i == 3 or i == 8) "v1" else "v2") and
          doubleReport(a, "/double/producing", doubleVersion, doubleVersion.env.mapSource, if (i == 10) "v2" else "v1")) "ok"
      else "wrong_exact_producer_report"
    } else if (i == 14) {
      if (acceptedRead(a, main) and ordinary::report(a, "", "status") == "finished" and
          ordinary::report(a, "", "value") == "86" and a.commit == rows[13].commit and
          outerReport(a, "/requested", ca, ordinary::v1, "v1") and
          outerReport(a, "/producing", ca, ordinary::v1, "v1")) "ok" else "wrong_pinned_a_readback"
    } else if (i == 17) {
      if (ordinary::forge(a, rows[11], first, false, main)) "ok" else "wrong_source_graft"
    } else if (i == 19) {
      val ancestors = ordinary::ids(rows[0].created.concat(rows[1].created).concat(first.created)
        .concat(rows[5].created).concat(rows[6].created).concat(rows[7].created))
      if (a.transfer and a.commit == rows[7].commit and ordinary::ids(a.created) == ancestors and
          a.created.length() == ancestors.size() and ordinary::published(a, a.args[2], a.commit, "", "")) "ok"
      else "wrong_transfer_root_or_ancestors"
    } else if (i == 20) {
      if (a.transfer and a.unchanged and a.commit == "" and a.refs == List() and a.main == rows[18].main) "ok"
      else "wrong_retirement"
    } else if (i == 21) {
      if (acceptedRead(a, "") and a.commit == rows[8].commit and a.report == rows[8].report) "ok"
      else "wrong_transferred_readback"
    } else "unhandled_step"
  }

  pure def historyVerdicts(row: Observation): List[str] =
    if (row.attempts.length() != histories::storyBound.length()) List("missing_steps")
    else range(0, histories::storyBound.length()).foldl(List(), (out, i) => out.append(stepVerdict(row, i)))
  pure def verdictAccepted(verdict: str): bool = verdict == "ok"
  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool =
    evidence.length() == 1 and evidence[0].closures.length() == 6 and verdicts.length() == 1 and
    verdicts[0].length() == histories::storyBound.length() and verdicts[0].foldl(true, (ok, v) => ok and verdictAccepted(v))

  pure val testMap: ordinary::InputMap = { dag: "new", datum: "equal", sources: List(link("a", "new-source")),
    args: List({ name: "a", value: 13 }) }
  pure val testPrior = { ...testMap, dag: "old", sources: List(link("a", "old-source")) }
  pure val testClosure: Closure = { dag: "A", fields: 3, roleAtRoot: true, role: "implementation-call-closure-v1",
    intent: intent("add"), implementation: implementation("add", "v1"), links: List() }
  pure val controlsPass = exactInputsDiffer(testMap, testPrior) and
    not(exactInputsDiffer(testMap, { ...testPrior, datum: "different" })) and
    not(exactInputsDiffer(testMap, { ...testPrior, sources: testMap.sources })) and
    closureMatches(testClosure, "A", "add", "v1", List()) and
    not(closureMatches({ ...testClosure, roleAtRoot: false }, "A", "add", "v1", List())) and
    not(closureMatches(testClosure, "A", "add", "v2", List()))
}
