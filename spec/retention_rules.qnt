module retention_rules {
  import retention_fixture.* from "./retention_fixture"

  type Change = { kind: str, key: str, before: str, after: str }
  type Attempt = {
    op: str, args: List[str], status: str, value: str, count: int,
    items: List[str], changes: List[Change], otherChanges: List[Change]
  }
  type Observation = { attempts: List[Attempt] }
  type Inventory = { objects: Set[str], refs: str -> str }
  type State = {
    opened: Set[str], inventories: str -> Inventory, repo: str, txn: str, mode: str,
    staged: Inventory, poisoned: bool, ids: str -> str, buffers: str -> str, bundles: str -> str
  }
  type Prediction = { state: State, repo: str, status: str, value: str, count: int, label: str, exportRoot: str }

  pure val schemaKey = "6d6574612f736368656d61"
  pure val schema = "444d4c310100010018000000000000000000000001000000"
  pure val refKeys = Map(
    "main" -> "726566732f68656164732f6d61696e",
    "incoming" -> "726566732f68656164732f696e636f6d696e67",
    "returned" -> "726566732f68656164732f72657475726e6564",
    "result-pin" -> "726566732f68656164732f726573756c742d70696e"
  )
  pure val sentinel = "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5"
  pure val untouchedCount = 123456789
  pure val empty: Inventory = { objects: Set(), refs: Map() }
  pure val initial: State = {
    opened: Set(), inventories: Map(), repo: "", txn: "", mode: "", staged: empty, poisoned: false,
    ids: Map(), buffers: Map(), bundles: Map()
  }

  pure def lookup(mapping: str -> str, key: str): str = if (mapping.keys().contains(key)) mapping.get(key) else ""
  pure def inventory(state: State, repo: str): Inventory =
    if (state.inventories.keys().contains(repo)) state.inventories.get(repo) else empty
  pure def rows(state: State, repo: str): str -> str = {
    if (not(state.inventories.keys().contains(repo))) Map()
    else {
      val contents = inventory(state, repo)
      val objects = contents.objects.fold(Map(schemaKey -> schema), (out, id) => {
        val record = byId.get(id)
        out.put(record.key, record.packed)
      })
      contents.refs.keys().fold(objects, (out, ref) => {
        val id = contents.refs.get(ref)
        if (id == "") out else out.put(refKeys.get(ref), id)
      })
    }
  }

  pure def diff(before: str -> str, after: str -> str): Set[Change] =
    before.keys().union(after.keys()).map(key => {
      val old = lookup(before, key)
      val value = lookup(after, key)
      { key: key, before: old, after: value,
        kind: if (old == "") "added" else if (value == "") "removed" else "modified" }
    }).filter(change => change.before != change.after)

  pure def prediction(state: State, repo: str, status: str, value: str, count: int, label: str): Prediction =
    { state: state, repo: repo, status: status, value: value, count: count, label: label, exportRoot: "" }
  pure def success(state: State, repo: str, label: str): Prediction = prediction(state, repo, "ok", "", 0, label)
  pure def unsupported(state: State): Prediction = prediction(state, "", "", "", 0, "unsupported_request")

  pure def operands(state: State, inputs: List[str]): List[str] = {
    val kind = inputs.head()
    if (kind == "dag" or kind == "tree") {
      val firstName = if (kind == "dag") 2 else 1
      inputs.indices().fold(List(), (out, i) => {
        val isId = (kind == "dag" and i == 1) or (i > firstName and (i - firstName) % 2 == 1)
        out.append(if (isId) lookup(state.ids, inputs[i]) else inputs[i])
      })
    } else inputs.tail().foldl(List(kind), (out, id) => out.append(lookup(state.ids, id)))
  }

  pure def encodeRecord(state: State, op: str, args: List[str]): Prediction = {
    val last = args.length() - 1
    val inputs = args.slice(0, last)
    val recipe = if (op == "datum_encode") inputs else operands(state, inputs)
    if (not(recipes.keys().contains(recipe))) unsupported(state)
    else {
      val packed = recipes.get(recipe).packed
      prediction({ ...state, buffers: state.buffers.put(args[last], packed) }, state.repo, "ok", packed, 0, "ok")
    }
  }

  pure def store(state: State, kind: str, source: str, output: str): Prediction = {
    val record = byPacked.get(state.buffers.get(source))
    if (state.mode != "write" or state.poisoned or record.kind != kind or not(record.deps.subseteq(state.staged.objects)))
      unsupported(state)
    else {
      val updated = { ...state, ids: state.ids.put(output, record.id),
        staged: { ...state.staged, objects: state.staged.objects.union(Set(record.id)) } }
      prediction(updated, state.repo, "ok", record.id, 0, "ok")
    }
  }

  pure def idsOf(closureRecords: List[Record]): Set[str] = closureRecords.foldl(Set(), (out, record) => out.union(Set(record.id)))

  pure def exportBundle(state: State, repo: str, root: str, output: str): Prediction = {
    val id = lookup(state.ids, root)
    if (state.repo == repo or not(closure.keys().contains(id))
        or not(idsOf(closure.get(id)).subseteq(inventory(state, repo).objects))) unsupported(state)
    else { ...success({ ...state, bundles: state.bundles.put(output, id) }, repo, "ok"), exportRoot: id }
  }

  pure def importBundle(state: State, repo: str, input: str, ref: str, output: str): Prediction = {
    val bundle = lookup(state.bundles, input)
    val truncated = input == "resultBundle~1" and lookup(state.bundles, "resultBundle") == result.id
    val contents = inventory(state, repo)
    val old = lookup(contents.refs, ref)
    val failure = if (state.repo == repo) "invalid_state"
      else if (ref != "" and not(refKeys.keys().contains(ref))) "invalid_argument"
      else if (truncated) "invalid_bounds" else if (old != "") "invalid_state" else ""
    if (bundle == "" and not(truncated)) unsupported(state)
    else {
      val wanted = if (truncated) Set() else idsOf(closure.get(bundle))
      val added = wanted.exclude(contents.objects).size()
      if (failure != "") {
        val label = if (old != "" and old == bundle and added == 0) "duplicate_same"
          else if (old != "" and old != bundle and added == 7) "duplicate_different"
          else if (failure == "invalid_argument") "bad_ref"
          else if (truncated) "short_bundle" else "unsupported_request"
        prediction(state, repo, failure, sentinel, 0, label)
      } else {
        val label = if (ref == "") "unpinned_import"
          else if (added == 0) "staged_present"
          else if (added == 10 and bundle == selected.id) "staged_fresh" else "staged"
        val refs = if (ref == "") contents.refs else contents.refs.put(ref, bundle)
        val updated = { objects: contents.objects.union(wanted), refs: refs }
        prediction({ ...state, inventories: state.inventories.put(repo, updated), ids: state.ids.put(output, bundle) },
          repo, "ok", bundle, 0, label)
      }
    }
  }

  pure def editRef(state: State, op: str, ref: str, alias: str): Prediction = {
    val id = lookup(state.ids, alias)
    val old = lookup(state.staged.refs, ref)
    val create = op == "txn_ref_create"
    val release = op == "txn_ref_delete_expected"
    if (state.mode != "write" or not(refKeys.keys().contains(ref)) or not(closure.keys().contains(id))) unsupported(state)
    else {
      val status = if (state.poisoned) "invalid_state"
        else if (not(release) and not(state.staged.objects.contains(id))) "not_found"
        else if (create and old != "" or release and old != "" and id != old) "invalid_state"
        else if (not(create) and old == "") "not_found" else "ok"
      if (status != "ok") {
        val label = if (create and status == "not_found") "target_swept" else "unsupported_request"
        prediction({ ...state, poisoned: true }, state.repo, status, "", 0, label)
      } else {
        val staged = { ...state.staged, refs: state.staged.refs.put(ref, if (release) "" else id) }
        val label = if (ref == "result-pin") (if (release) "released_pin" else "created_pin")
          else if (release) "released_ref" else if (create) "created_ref" else "moved_ref"
        success({ ...state, staged: staged }, state.repo, label)
      }
    }
  }

  pure def readRef(state: State, ref: str, output: str): Prediction = {
    val id = lookup(state.staged.refs, ref)
    if (state.poisoned) unsupported(state)
    else if (id == "") prediction(state, state.repo, "not_found", "", 0, "absent_ref")
    else {
      val captured = lookup(state.ids, "expected")
      val label = if (ref == "main" and state.mode == "read" and output == "expected") "captured_main"
        else if (ref == "main" and state.mode == "write" and output == "actual" and captured != "")
          (if (id == captured) "current_main" else "stale_main")
        else if (ref == "main") "read_main" else if (ref == "returned") "read_returned" else "read_incoming"
      prediction({ ...state, ids: state.ids.put(output, id) }, state.repo, "ok", id, 0, label)
    }
  }

  pure def collect(state: State): Prediction = {
    if (state.mode != "write") unsupported(state)
    else if (state.poisoned) prediction(state, state.repo, "invalid_state", "", untouchedCount, "blocked_sweep")
    else {
      val contents = state.staged
      val retained = contents.refs.keys().fold(Set(), (out, ref) => {
        val id = contents.refs.get(ref)
        if (id == "") out else out.union(idsOf(closure.get(id)))
      })
      // Healthy fixtures always contain the full closure of every remaining root.
      if (not(retained.subseteq(contents.objects))) unsupported(state)
      else {
        val removed = contents.objects.exclude(retained).size()
        val label = if (removed == 17) "swept_17" else if (removed == 7) "swept_7"
          else if (Set(0, 5).contains(removed) and lookup(contents.refs, "returned") == result.id) "retained_stage"
          else if (removed == 5 and lookup(contents.refs, "main") == result.id) "retained_main"
          else if (removed == 5) "swept_5"
          else if (removed == 0) "swept_0" else "swept"
        prediction({ ...state, staged: { ...contents, objects: retained } }, state.repo, "ok", "", removed, label)
      }
    }
  }

  pure def finishTxn(state: State, op: str): Prediction = {
    val closed = { ...state, txn: "", mode: "", repo: "", staged: empty, poisoned: false }
    if (op == "txn_abort") success(closed, state.repo, if (state.mode == "write") "aborted_write" else "ok")
    else if (state.poisoned) prediction(closed, state.repo, "invalid_state", "", 0, "poisoned_commit")
    else success({ ...closed, inventories: state.inventories.put(state.repo, state.staged) }, state.repo,
      if (state.txn == "seed") "ok" else "committed")
  }

  pure def txnCall(state: State, op: str, args: List[str]): Prediction = {
    if (state.txn == "" or state.txn != args[0]) unsupported(state)
    else if (op == "txn_commit" or op == "txn_abort") finishTxn(state, op)
    else if (op == "txn_put_datum") store(state, "datum", args[1], args[2])
    else if (op == "txn_put_object") store(state, args[1], args[2], args[3])
    else if (Set("txn_ref_create", "txn_ref_update", "txn_ref_delete_expected").contains(op))
      editRef(state, op, args[1], args[2])
    else if (op == "txn_ref_get") readRef(state, args[1], args[2])
    else if (op == "txn_get_object") {
      val id = lookup(state.ids, args[2])
      if (state.poisoned or not(state.staged.objects.contains(id)) or byId.get(id).kind != args[1]) unsupported(state)
      else {
        val packed = byId.get(id).packed
        prediction({ ...state, buffers: state.buffers.put(args[3], packed) }, state.repo, "ok", packed, 0, "inspected_commit")
      }
    } else if (op == "txn_collect_garbage") collect(state)
    else unsupported(state)
  }

  pure def transition(state: State, op: str, args: List[str]): Prediction = {
    if (op == "repo_open") {
      val repo = args[0]
      if (state.opened.contains(repo)) unsupported(state)
      else if (args[1] == "create" and not(state.inventories.keys().contains(repo)))
        success({ ...state, opened: state.opened.union(Set(repo)), inventories: state.inventories.put(repo, empty) }, repo, "ok")
      else if (args[1] == "existing" and state.inventories.keys().contains(repo))
        success({ ...state, opened: state.opened.union(Set(repo)) }, repo, "reopened")
      else unsupported(state)
    } else if (op == "repo_close") {
      val repo = args[0]
      if (state.opened.contains(repo) and state.repo != repo)
        success({ ...state, opened: state.opened.exclude(Set(repo)) }, repo, "ok")
      else unsupported(state)
    } else if (op == "txn_begin") {
      val repo = args[0]
      if (state.txn == "" and state.opened.contains(repo) and Set("read", "write").contains(args[1]))
        success({ ...state, repo: repo, txn: args[2], mode: args[1], staged: inventory(state, repo) }, repo, "ok")
      else unsupported(state)
    } else if (Set("datum_encode", "object_encode").contains(op)) encodeRecord(state, op, args)
    else if (Set("repo_import_commit", "repo_import_commit_staged", "repo_export_commit").contains(op)) {
      if (not(state.opened.contains(args[0]))) unsupported(state)
      else if (op == "repo_export_commit") exportBundle(state, args[0], args[1], args[2])
      else if (op == "repo_import_commit") importBundle(state, args[0], args[1], "", args[2])
      else importBundle(state, args[0], args[1], args[2], args[3])
    } else txnCall(state, op, args)
  }

  // The adapter decodes only the envelope. Check the actual header root and all
  // frame bytes and enforce dependency-before-consumer without fixing an order
  // for independent frames.
  pure def validExport(root: str, items: List[str]): bool = {
    val expected = closure.get(root)
    val wanted = idsOf(expected)
    if (items.length() != 1 + 3 * expected.length() or items[0] != root) false
    else {
      val scanned = expected.indices().fold({ seen: Set(), valid: true, final: "" }, (out, i) => {
        val id = items[2 + 3 * i]
        if (not(wanted.contains(id))) { ...out, valid: false }
        else {
          val record = byId.get(id)
          { seen: out.seen.union(Set(id)), final: id,
            valid: out.valid and not(out.seen.contains(id)) and record.deps.subseteq(out.seen)
              and items[1 + 3 * i] == record.tag and items[3 + 3 * i] == record.packed }
        }
      })
      scanned.valid and scanned.final == root and scanned.seen == wanted
    }
  }

  pure def stepVerdict(previous: State, predicted: Prediction, attempt: Attempt): str = {
    val expected = diff(rows(previous, predicted.repo), rows(predicted.state, predicted.repo))
    val actual = attempt.changes.foldl(Set(), (out, change) => out.union(Set(change)))
    if (predicted.label == "unsupported_request") predicted.label
    else if (attempt.status != predicted.status) "status"
    else if (attempt.count != predicted.count) "count"
    else if (predicted.exportRoot != "" and (attempt.value == "" or not(validExport(predicted.exportRoot, attempt.items))))
      "export"
    else if (predicted.exportRoot == "" and (attempt.value != predicted.value or attempt.items != List())) "value"
    else if (attempt.otherChanges != List() or actual != expected or attempt.changes.length() != expected.size()) "inventory"
    else predicted.label
  }

  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ state: initial, verdicts: List() }, (out, attempt) => {
      val predicted = transition(out.state, attempt.op, attempt.args)
      { state: predicted.state, verdicts: out.verdicts.append(stepVerdict(out.state, predicted, attempt)) }
    }).verdicts

  pure def checkControl(before: State, attempt: Attempt): str =
    stepVerdict(before, transition(before, attempt.op, attempt.args), attempt)

  pure val noOutput: Attempt = {
    op: "", args: List(), status: "ok", value: "", count: 0, items: List(), changes: List(), otherChanges: List()
  }
}
