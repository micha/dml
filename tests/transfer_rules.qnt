module transfer_rules {
  import transfer_fixture.* from "./transfer_fixture"

  type Change = { kind: str, key: str, before: str, after: str }
  type Attempt = { op: str, args: List[str], status: str, value: str, count: int,
    items: List[str], changes: List[Change], otherChanges: List[Change] }
  type Observation = { attempts: List[Attempt] }
  type Inventory = str -> str
  type State = {
    inventories: str -> Inventory, open: Set[str], repo: str, txn: str, mode: str, staged: Inventory,
    poisoned: bool, ids: str -> str, buffers: str -> Object, views: str -> Object,
    bundles: str -> str
  }
  type Prediction = { state: State, repo: str, status: str, value: str, count: int, items: List[str] }

  pure val byId = objects.foldl(Map(), (out, row) => out.put(row.id, row))
  pure val byPacked = objects.foldl(Map(), (out, row) => out.put(row.packed, row))
  pure val variantByPacked = variants.foldl(Map(), (out, row) => out.put(row.packed, row))
  pure val refKeys = Map(
    "main" -> "726566732f68656164732f6d61696e",
    "pinned" -> "726566732f68656164732f70696e6e6564",
    "incoming" -> "726566732f68656164732f696e636f6d696e67",
    "result-pin" -> "726566732f68656164732f726573756c742d70696e"
  )
  pure val sentinel = "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5"
  pure val initial: State = { inventories: Map(), open: Set(), repo: "", txn: "", mode: "",
    staged: Map(), poisoned: false, ids: Map(), buffers: Map(), views: Map(), bundles: Map() }

  pure def lookup(rows: Inventory, key: str): str = if (rows.keys().contains(key)) rows.get(key) else ""
  pure def snapshot(s: State, repo: str): Inventory =
    if (s.inventories.keys().contains(repo)) s.inventories.get(repo) else Map()
  pure def save(s: State, repo: str, rows: Inventory): State =
    { ...s, inventories: s.inventories.put(repo, rows) }
  pure def outcome(s: State, repo: str, status: str): Prediction =
    { state: s, repo: repo, status: status, value: "", count: 0, items: List() }
  pure def ok(s: State, repo: str): Prediction = outcome(s, repo, "ok")
  pure def unsupported(s: State): Prediction = outcome(s, "", "unsupported_request")
  pure def idOf(s: State, operand: str): str = if (s.ids.keys().contains(operand)) s.ids.get(operand) else operand
  pure def withId(p: Prediction, alias: str, id: str): Prediction =
    { ...p, value: id, state: { ...p.state, ids: p.state.ids.put(alias, id) } }
  pure def existsIn(rows: Inventory, object: Object): bool = rows.keys().contains(object.key)

  // Fixtures are topologically ordered. Traverse from consumers back to their dependencies.
  pure def reachable(roots: Set[str]): Set[str] =
    range(0, objects.length()).foldl(roots, (seen, i) => {
      val obj = objects[objects.length() - i - 1]
      if (seen.contains(obj.name)) obj.deps.foldl(seen, (out, dep) => out.union(Set(dep))) else seen
    })

  pure def diff(before: Inventory, after: Inventory): Set[Change] =
    before.keys().union(after.keys()).map(key => {
      val old = lookup(before, key)
      val current = lookup(after, key)
      { key: key, before: old, after: current,
        kind: if (old == "") "added" else if (current == "") "removed" else "modified" }
    }).filter(row => row.before != row.after)

  pure def transfer(s: State, op: str, args: List[str]): Prediction = {
    val repo = args[0]
    val stored = snapshot(s, repo)
    if (not(s.open.contains(repo))) unsupported(s)
    else if (op == "repo_export_commit") {
      val root = idOf(s, args[1])
      if (s.repo == repo) outcome(s, repo, "invalid_state")
      else if (not(byId.keys().contains(root))) outcome(s, repo, "not_found")
      else if (not(existsIn(stored, byId.get(root)))) outcome(s, repo, "not_found")
      else ok({ ...s, bundles: s.bundles.put(args[2], byId.get(root).name) }, repo)
    } else {
      val value = args[1]
      val input = if (s.bundles.keys().contains(value)) {status: "ok", target: s.bundles.get(value)}
                  else if (variantByPacked.keys().contains(value)) {
                    val fixture = variantByPacked.get(value)
                    {status: fixture.status, target: fixture.target}
                  } else {status: "unsupported_request", target: ""}
      val status = if (s.repo == repo) "invalid_state" else input.status
      if (status != "ok") { ...outcome(s, repo, status), value: sentinel }
      else {
        val root = byName.get(input.target)
        val imported = reachable(Set(root.name)).fold(stored, (out, name) => {
          val row = byName.get(name)
          out.put(row.key, row.packed)
        })
        withId(ok(save(s, repo, imported), repo), args[2], root.id)
      }
    }
  }

  pure def editRef(s: State, op: str, args: List[str]): Prediction = {
    val key = refKeys.get(args[1])
    val target = idOf(s, args[2])
    val before = lookup(s.staged, key)
    val remove = op == "txn_ref_delete_expected"
    val status = if (not(remove) and not(existsIn(s.staged, byId.get(target)))) "not_found"
                 else if (op == "txn_ref_create") (if (before == "") "ok" else "invalid_state")
                 else if (before == "") "not_found"
                 else if (remove and before != target) "invalid_state"
                 else "ok"
    if (status != "ok") outcome({ ...s, poisoned: true }, s.repo, status)
    else ok({ ...s, staged: if (remove) s.staged.keys().exclude(Set(key)).mapBy(k => s.staged.get(k))
                            else s.staged.put(key, target) }, s.repo)
  }

  pure val decimal = List("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13",
    "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
    "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48")

  pure def checkIntegrity(s: State): Prediction = {
    val rootKeys = refKeys.keys().map(name => refKeys.get(name)).intersect(s.staged.keys())
    val roots = rootKeys.map(key => byId.get(s.staged.get(key)).name)
    val live = reachable(roots)
    val dead = objects.select(row => existsIn(s.staged, row) and not(live.contains(row.name)))
    val report = List(decimal[rootKeys.size()], "0", "0", "0", decimal[live.size()], "0", "0", decimal[dead.length()], "0")
    { ...ok(s, s.repo), items: dead.foldl(report, (out, row) => out.concat(List(row.tag, row.id))) }
  }

  pure def txnStep(s: State, op: str, args: List[str]): Prediction = {
    val repo = s.repo
    if (s.txn == "" or args[0] != s.txn) unsupported(s)
    else if (op == "txn_abort" or op == "txn_commit") {
      val ended = { ...s, repo: "", txn: "", mode: "", staged: Map(), poisoned: false }
      if (op == "txn_abort") ok(ended, repo)
      else if (s.poisoned or s.mode != "write") outcome(ended, repo, "invalid_state")
      else ok(save(ended, repo, s.staged), repo)
    } else if (op == "txn_put_datum" or op == "txn_put_object") {
      val datum = op == "txn_put_datum"
      val row = byPacked.get(if (datum) args[1] else args[2])
      val kind = if (datum) "datum" else args[1]
      if (s.mode != "write" or s.poisoned or row.kind != kind
          or not(row.deps.foldl(true, (present, dep) => present and existsIn(s.staged, byName.get(dep))))) unsupported(s)
      else withId(ok({ ...s, staged: s.staged.put(row.key, row.packed) }, repo),
        if (datum) args[2] else args[3], row.id)
    } else if (Set("txn_ref_create", "txn_ref_update", "txn_ref_delete_expected").contains(op))
      editRef(s, op, args)
    else if (op == "txn_ref_get") {
      val id = lookup(s.staged, refKeys.get(args[1]))
      if (id == "") outcome(s, repo, "not_found") else withId(ok(s, repo), args[2], id)
    } else if (op == "txn_lookup_node") {
      val dag = byId.get(idOf(s, args[1]))
      val binding = dag.entries.select(entry => entry.name == args[2])
      if (binding.length() == 0) outcome(s, repo, "not_found")
      else withId(ok(s, repo), args[3], byName.get(binding.head().target).id)
    } else if (op == "txn_get_object" or op == "txn_get_datum") {
      val datum = op == "txn_get_datum"
      val row = byId.get(idOf(s, if (datum) args[1] else args[2]))
      val kind = if (datum) "datum" else args[1]
      val alias = if (datum) args[2] else args[3]
      if (row.kind != kind or not(existsIn(s.staged, row))) unsupported(s)
      else { ...ok({ ...s, buffers: s.buffers.put(alias, row) }, repo), value: row.packed }
    } else if (op == "txn_check_integrity" and s.mode == "read") checkIntegrity(s)
    else unsupported(s)
  }

  pure def viewStep(s: State, op: str, args: List[str]): Prediction =
    if (op == "object_decode") {
      val row = s.buffers.get(args[0])
      val decoded = { ...s, views: s.views.put(args[1], row), ids: s.ids.put(args[1], row.reference) }
      { ...ok(decoded, ""), value: row.reference, count: row.count }
    } else if (op == "datum_decode") {
      val row = s.buffers.get(args[0])
      { ...ok(s, ""), value: row.payload, count: row.datumKind }
    } else {
      val row = s.views.get(args[0])
      val index = if (args[1] == "0") 0 else 1
      if (op == "object_view_parent") withId(ok(s, ""), args[2], byName.get(row.deps[index + 1]).id)
      else {
        val entry = row.entries[index]
        { ...withId(ok(s, ""), args[2], byName.get(entry.target).id), items: List(entry.hexName) }
      }
    }

  pure def predict(s: State, a: Attempt): Prediction = {
    val args = a.args
    val op = a.op
    if (op == "repo_open") {
      val repo = args[0]
      if (s.open.contains(repo)) unsupported(s)
      else if (args[1] == "create" and not(s.inventories.keys().contains(repo)))
        ok(save({ ...s, open: s.open.union(Set(repo)) }, repo, Map(schemaKey -> schema)), repo)
      else if (args[1] == "existing" and snapshot(s, repo).keys().contains(schemaKey))
        ok({ ...s, open: s.open.union(Set(repo)) }, repo)
      else unsupported(s)
    } else if (op == "repo_close") ok({ ...s, open: s.open.exclude(Set(args[0])) }, args[0])
    else if (op == "txn_begin" and s.txn == "" and s.open.contains(args[0]))
      ok({ ...s, repo: args[0], mode: args[1], txn: args[2], staged: snapshot(s, args[0]) }, args[0])
    else if (Set("repo_export_commit", "repo_import_commit").contains(op)) transfer(s, op, args)
    else if (Set("object_decode", "datum_decode", "object_view_parent", "object_view_entry").contains(op))
      viewStep(s, op, args)
    else txnStep(s, op, args)
  }

  pure def sameDiff(a: Attempt, expected: Set[Change]): bool = a.otherChanges == List()
    and a.changes.length() == expected.size() and a.changes.foldl(Set(), (rows, row) => rows.union(Set(row))) == expected
  pure def pairs(items: List[str], offset: int): Set[List[str]] = items.indices().filter(i => i >= offset and (i - offset) % 2 == 0)
    .map(i => List(items[i], items[i + 1]))
  pure def exportMatches(a: Attempt, root: Object): bool = {
    val needed = reachable(Set(root.name))
    if (a.value == "" or a.items.length() != 1 + 3 * needed.size()) false
    else {
      val rows = range(0, needed.size()).foldl(List(), (out, i) =>
        out.append(List(a.items[3*i + 1], a.items[3*i + 2], a.items[3*i + 3])))
      val actual = rows.foldl({ seen: Set(), valid: true }, (out, frame) => {
        val id = frame[1]
        if (not(byId.keys().contains(id))) { ...out, valid: false }
        else {
          val row = byId.get(id)
          { seen: out.seen.union(Set(row.name)), valid: out.valid and not(out.seen.contains(row.name))
            and frame == List(row.tag, row.id, row.packed)
            and row.deps.foldl(true, (passed, dep) => passed and out.seen.contains(dep)) }
        }
      })
      a.items.head() == root.id and rows[rows.length() - 1][1] == root.id and actual.valid and actual.seen == needed
    }
  }

  pure def verdict(s: State, p: Prediction, a: Attempt, seen: Inventory): str = {
    val expected = diff(snapshot(s, p.repo), snapshot(p.state, p.repo))
    if (p.status == "unsupported_request") "request"
    else if (p.status != a.status) "status"
    else if (not(sameDiff(a, expected))) "inventory"
    else if (a.op == "repo_export_commit" and p.status == "ok") {
      val root = byId.get(idOf(s, a.args[1]))
      if (not(exportMatches(a, root))) "bundle"
      else if (seen.keys().contains(root.id) and seen.get(root.id) != a.value) "determinism"
      else "pass"
    } else if (p.value != a.value or p.count != a.count) "value"
    else if (a.op == "txn_check_integrity") {
      if (a.items.length() == p.items.length() and a.items.slice(0, 9) == p.items.slice(0, 9)
          and pairs(a.items, 9) == pairs(p.items, 9)) "pass" else "integrity"
    } else if (a.items != p.items) "items"
    else "pass"
  }

  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ state: initial, seen: Map(), verdicts: List() }, (out, a) => {
      val p = predict(out.state, a)
      val v = verdict(out.state, p, a, out.seen)
      val seen = if (v == "pass" and a.op == "repo_export_commit" and a.status == "ok")
        out.seen.put(a.items[0], a.value) else out.seen
      { state: p.state, seen: seen, verdicts: out.verdicts.append(v) }
    }).verdicts
  pure def verdictAccepted(verdict: str): bool = verdict == "pass"

  pure def hasMatch(attempts: List[Attempt], predicate: Attempt => bool): bool =
    attempts.select(predicate).length() > 0
  pure def has(attempts: List[Attempt], op: str, args: List[str], status: str, value: str): bool =
    hasMatch(attempts, a => a.op == op and a.args == args and a.status == status and a.value == value)
  pure def exactExport(a: Attempt, repo: str, root: str, alias: str): bool =
    a.op == "repo_export_commit" and a.args == List(repo, root, alias) and a.status == "ok"

  pure def roundTrips(evidence: List[Observation]): bool = {
    val thin = variants.select(v => v.name == "thin").head().packed
    val alternative = variants.select(v => v.name == "alternative").head().packed
    val root = byName.get("root").id
    val direct = evidence.select(row => {
      val a = row.attempts
      val replay = a.select(step => step.op == "repo_export_commit" or step.op == "repo_import_commit")
      if (replay.length() != 6) false
      else all {
        exactExport(replay[0], "source", "root", "exported"),
        has(List(replay[1]), "repo_import_commit", List("dest", "exported", "imported"), "ok", root),
        exactExport(replay[2], "dest", "imported", "reexported"),
        exactExport(replay[3], "source", "root", "repeated"),
        replay[0].value == replay[2].value and replay[0].value == replay[3].value,
        has(List(replay[5]), "repo_import_commit", List("dest", thin, "thinOverExisting"), "invalid_payload", sentinel)
      }
    })
    val reordered = evidence.select(row => {
      val a = row.attempts.select(step => step.op == "repo_export_commit" or step.op == "repo_import_commit")
      if (a.length() != 3) false
      else all {
        has(List(a[0]), "repo_import_commit", List("dest", alternative, "alternative"), "ok", root),
        exactExport(a[1], "dest", "alternative", "altExport"),
        exactExport(a[2], "source", "root", "firstExport"),
        a[1].value == a[2].value
      }
    })
    direct.length() > 0 and reordered.length() > 0
  }

  pure def coveragePass(evidence: List[Observation], _verdicts: List[List[str]]): bool = {
    val ids = byName
    val allAttempts = evidence.foldl(List(), (out, row) => out.concat(row.attempts))
    val imports = allAttempts.select(a => a.op == "repo_import_commit")
    val missing = "ffffffffffffffffffffffffffffffff"
    val rounds = evidence.select(row => {
      val a = row.attempts
      all {
        has(a, "txn_ref_create", List("result", "result-pin", "resultA"), "ok", ""),
        has(a, "txn_ref_create", List("result", "result-pin", "resultB"), "invalid_state", ""),
        has(a, "txn_commit", List("result"), "invalid_state", ""),
        has(a, "repo_import_commit", List("source", "returnedBundle", "returnedAgain"), "ok", ids.get("resultA").id),
        has(a, "txn_ref_get", List("capture", "main", "originalMain"), "ok", ids.get("other").id),
        has(a, "txn_ref_get", List("stale", "main", "staleActual"), "ok", ids.get("other").id),
        ids.get("other").id != ids.get("root").id,
        has(a, "txn_abort", List("stale"), "ok", ""),
        has(a, "txn_ref_get", List("publish", "main", "publishActual"), "ok", ids.get("other").id),
        has(a, "txn_ref_get", List("lineage", "main", "publishedResult"), "ok", ids.get("resultA").id),
        has(a, "txn_ref_get", List("lineage", "result-pin", "releasedResult"), "ok", ids.get("resultA").id),
        has(a, "txn_ref_get", List("noPin", "result-pin", "noPin"), "not_found", ""),
        has(a, "txn_ref_delete_expected", List("release", "incoming", "keep"), "invalid_state", ""),
        has(a, "txn_ref_delete_expected", List("release", "incoming", "imported"), "not_found", ""),
        has(a, "txn_ref_get", List("noStage", "incoming", "noStage"), "not_found", ""),
        a.select(step => step.op == "txn_check_integrity" and step.status == "ok").length() == 4
      }
    }).length() > 0
    all {
      variants.foldl(true, (covered, fixture) => covered
        and hasMatch(imports, a => a.args[1] == fixture.packed and a.status == fixture.status)),
      has(allAttempts, "repo_export_commit", List("dest", missing, "missingBundle"), "not_found", ""),
      has(allAttempts, "repo_export_commit", List("dest", "keep", "busyBundle"), "invalid_state", ""),
      hasMatch(imports, a => a.args[2] == "busyId" and a.status == "invalid_state"),
      hasMatch(allAttempts, a => a.op == "txn_lookup_node" and a.status == "not_found"),
      has(allAttempts, "object_view_parent", List("inputView", "0", "firstParent"), "ok", ids.get("otherParent").id),
      has(allAttempts, "object_view_parent", List("inputView", "1", "secondParent"), "ok", ids.get("oldHead").id),
      hasMatch(allAttempts, a => a.op == "datum_decode" and a.value == ids.get("first").payload),
      hasMatch(allAttempts, a => a.op == "datum_decode" and a.value == ids.get("fifth").payload),
      roundTrips(evidence),
      rounds
    }
  }

  pure val badImport = variants.select(v => v.name == "thin").head()
  pure val dest = { ...initial, open: Set("dest"), inventories: Map("dest" -> Map(schemaKey -> schema)) }
  pure val rejet: Attempt = { op: "repo_import_commit", args: List("dest", badImport.packed, "bad"),
    status: "invalid_payload", value: sentinel, count: 0, items: List(), changes: List(), otherChanges: List() }
  pure val leak = { kind: "added", key: byName.get("ancestor").key, before: "", after: byName.get("ancestor").packed }
  pure val controlsPass = {
    val p = predict(dest, rejet)
    all {
      verdict(dest, p, rejet, Map()) == "pass",
      verdict(dest, p, { ...rejet, changes: List(leak) }, Map()) == "inventory",
      verdict(dest, p, { ...rejet, otherChanges: List(leak) }, Map()) == "inventory",
      verdict(dest, p, { ...rejet, value: byName.get("ancestor").id }, Map()) == "value",
      not(exportMatches({ ...rejet, value: "abcd", items: List(byName.get("oldHead").id) }, byName.get("oldHead")))
    }
  }
}
