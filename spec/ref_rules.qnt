module ref_rules {
  type Change = { kind: str, key: str, before: str, after: str }
  type Attempt = { op: str, args: List[str], status: str, value: str, count: int,
    items: List[str], changes: List[Change], otherChanges: List[Change] }
  type Observation = { attempts: List[Attempt] }
  type GoldenRecord = { kind: str, id: str, key: str, packed: str, deps: List[str] }

  // Known v1 packed records and XXH3-128 IDs from the documented format, not
  // from the replay. Keys are hex-encoded ASCII LMDB keys, values are raw bytes.
  pure val schemaKey = "6d6574612f736368656d61" // meta/schema
  pure val schema = "444d4c310100010018000000000000000000000001000000"
  pure val literal: GoldenRecord = {
    kind: "datum", id: "5b1650c450c489a88e01742a620fa44f",
    key: "6f626a656374732f646174756d732f3562313635306334353063343839613838653031373432613632306661343466",
    packed: "444d4c310100020030000000000000000000000003000000080000000000000028000000000000002a00000000000000",
    deps: List()
  }
  pure val literalNode: GoldenRecord = {
    kind: "node", id: "56676dfed2f8219f744cf74fc5466e2e",
    key: "6f626a656374732f6e6f6465732f3536363736646665643266383231396637343463663734666335343636653265",
    packed: "444d4c3101000300280000000000000000000000010000005b1650c450c489a88e01742a620fa44f",
    deps: List(literal.id)
  }
  pure val graph: GoldenRecord = {
    kind: "dag", id: "b91b388e89c16737097bfb7bb7fd7579",
    key: "6f626a656374732f646167732f6239316233383865383963313637333730393762666237626237666437353739",
    packed: "444d4c310100040028000000000000000000000056676dfed2f8219f744cf74fc5466e2e00000000",
    deps: List(literalNode.id)
  }
  pure val emptyTree: GoldenRecord = {
    kind: "tree", id: "3d59a6a9e972e506439764c073478164",
    key: "6f626a656374732f74726565732f3364353961366139653937326535303634333937363463303733343738313634",
    packed: "444d4c310100050018000000000000000000000000000000",
    deps: List()
  }
  pure val a: GoldenRecord = {
    kind: "commit", id: "d371ef52cac51307726f79c02f367a56",
    key: "6f626a656374732f636f6d6d6974732f6433373165663532636163353133303737323666373963303266333637613536",
    packed: "444d4c31010006002800000000000000000000003d59a6a9e972e506439764c07347816400000000",
    deps: List(emptyTree.id)
  }
  pure val b: GoldenRecord = {
    kind: "commit", id: "964f70d29d2e06523c0fded8f1d94528",
    key: "6f626a656374732f636f6d6d6974732f3936346637306432396432653036353233633066646564386631643934353238",
    packed: "444d4c31010006003800000000000000000000003d59a6a9e972e506439764c07347816401000000d371ef52cac51307726f79c02f367a56",
    deps: List(emptyTree.id, a.id)
  }
  pure val candidateTree: GoldenRecord = {
    kind: "tree", id: "eff6d2a9d417be0b8f3909ae1a472968",
    key: "6f626a656374732f74726565732f6566663664326139643431376265306238663339303961653161343732393638",
    packed: "444d4c3101000500350000000000000000000000010000000900000063616e646964617465b91b388e89c16737097bfb7bb7fd7579",
    deps: List(graph.id)
  }
  pure val c: GoldenRecord = {
    kind: "commit", id: "2e054b709141c932a628678c47ccb1c0",
    key: "6f626a656374732f636f6d6d6974732f3265303534623730393134316339333261363238363738633437636362316330",
    packed: "444d4c3101000600380000000000000000000000eff6d2a9d417be0b8f3909ae1a47296801000000d371ef52cac51307726f79c02f367a56",
    deps: List(candidateTree.id, a.id)
  }
  pure val snapshotTree: GoldenRecord = {
    kind: "tree", id: "ac588f00de4f72a29fc1269fe0ab31d8",
    key: "6f626a656374732f74726565732f6163353838663030646534663732613239666331323639666530616233316438",
    packed: "444d4c31010005003400000000000000000000000100000008000000736e617073686f74b91b388e89c16737097bfb7bb7fd7579",
    deps: List(graph.id)
  }
  pure val fromA: GoldenRecord = {
    kind: "commit", id: "2e2047bdd770e59584af379d81c4f9a5",
    key: "6f626a656374732f636f6d6d6974732f3265323034376264643737306535393538346166333739643831633466396135",
    packed: "444d4c3101000600380000000000000000000000ac588f00de4f72a29fc1269fe0ab31d801000000d371ef52cac51307726f79c02f367a56",
    deps: List(snapshotTree.id, a.id)
  }
  pure val fromB: GoldenRecord = {
    kind: "commit", id: "728a6b2e6e1ff6c495dace1c60b2b579",
    key: "6f626a656374732f636f6d6d6974732f3732386136623265366531666636633439356461636531633630623262353739",
    packed: "444d4c3101000600380000000000000000000000ac588f00de4f72a29fc1269fe0ab31d801000000964f70d29d2e06523c0fded8f1d94528",
    deps: List(snapshotTree.id, b.id)
  }

  pure val recipes = Map(
    List("node", literal.id) -> literalNode,
    List("dag", literalNode.id) -> graph,
    List("tree") -> emptyTree,
    List("tree", "candidate", graph.id) -> candidateTree,
    List("tree", "snapshot", graph.id) -> snapshotTree,
    List("commit", emptyTree.id) -> a,
    List("commit", emptyTree.id, a.id) -> b,
    List("commit", candidateTree.id, a.id) -> c,
    List("commit", snapshotTree.id, a.id) -> fromA,
    List("commit", snapshotTree.id, b.id) -> fromB
  )
  pure val records = List(literal, literalNode, graph, emptyTree, candidateTree, snapshotTree, a, b, c, fromA, fromB)
  pure val byId = records.foldl(Map(), (out, record) => out.put(record.id, record))
  pure val byPacked = records.foldl(Map(), (out, record) => out.put(record.packed, record))
  pure val refKeys = Map(
    "main" -> "726566732f68656164732f6d61696e",
    "candidate-1" -> "726566732f68656164732f63616e6469646174652d31",
    "other" -> "726566732f68656164732f6f74686572",
    "missing" -> "726566732f68656164732f6d697373696e67"
  )

  type Inventory = str -> str
  type State = {
    repo: str, txn: str, mode: str, poisoned: bool,
    committed: Inventory, staged: Inventory,
    ids: str -> str, buffers: str -> str, views: str -> str
  }
  type Prediction = { state: State, status: str, value: str, count: int, label: str }

  pure val initial: State = {
    repo: "", txn: "", mode: "", poisoned: false, committed: Map(), staged: Map(),
    ids: Map(), buffers: Map(), views: Map()
  }

  pure def predict(state: State, status: str, value: str, count: int, label: str): Prediction =
    { state: state, status: status, value: value, count: count, label: label }

  pure def success(state: State, label: str): Prediction = predict(state, "ok", "", 0, label)
  pure def unsupported(state: State): Prediction = predict(state, "", "", 0, "unsupported_request")

  pure def lookup(rows: Inventory, key: str): str = if (rows.keys().contains(key)) rows.get(key) else ""

  pure def diff(before: Inventory, after: Inventory): Set[Change] =
    before.keys().union(after.keys()).map(key => {
      val old = lookup(before, key)
      val current = lookup(after, key)
      { key: key, before: old, after: current,
        kind: if (old == "") "added" else if (current == "") "removed" else "modified" }
    }).filter(row => row.before != row.after)

  pure def encodeRecord(state: State, op: str, args: List[str]): Prediction = {
    val last = args.length() - 1
    val output = args[last]
    val recipe = args.slice(0, last)
    if (op == "datum_encode" and recipe == List("i64", "42")) {
      predict({ ...state, buffers: state.buffers.put(output, literal.packed) }, "ok", literal.packed, 0, "ok")
    } else if (op == "object_encode") {
      val resolved = if (recipe[0] == "tree" and recipe.length() > 1)
        List(recipe[0], recipe[1], state.ids.get(recipe[2]))
      else recipe.tail().foldl(List(recipe[0]), (out, alias) => out.append(state.ids.get(alias)))
      if (not(recipes.keys().contains(resolved))) unsupported(state)
      else {
        val packed = recipes.get(resolved).packed
        predict({ ...state, buffers: state.buffers.put(output, packed) }, "ok", packed, 0, "ok")
      }
    } else unsupported(state)
  }

  pure def store(state: State, kind: str, source: str, output: str): Prediction = {
    val record = byPacked.get(state.buffers.get(source))
    if (state.mode != "write" or state.poisoned or record.kind != kind) unsupported(state)
    else if (record.deps.select(id => not(state.staged.keys().contains(byId.get(id).key))).length() != 0)
      unsupported(state)
    else {
      val label = if (state.staged.keys().contains(record.key)) "ok"
                  else if (record.id == snapshotTree.id) "staged_tree"
                  else if (Set(fromA.id, fromB.id).contains(record.id)) "staged_commit"
                  else "ok"
      predict({ ...state,
        staged: state.staged.put(record.key, record.packed), ids: state.ids.put(output, record.id)
      }, "ok", record.id, 0, label)
    }
  }

  pure def editRef(state: State, op: str, key: str, id: str): Prediction = {
    val existing = lookup(state.staged, key)
    val create = op == "txn_ref_create"
    if (state.mode != "write" or state.poisoned or byId.get(id).kind != "commit"
        or not(state.staged.keys().contains(byId.get(id).key))) unsupported(state)
    else if (create and existing != "") {
      val label = if (existing == id) "duplicate_same" else "duplicate_different"
      predict({ ...state, poisoned: true }, "invalid_state", "", 0, label)
    } else if (not(create) and existing == "") {
      predict({ ...state, poisoned: true }, "not_found", "", 0, "missing_update")
    } else success({ ...state, staged: state.staged.put(key, id) }, if (create) "created" else "updated")
  }

  pure def finishTxn(state: State, op: str): Prediction = {
    val closed = { ...state, txn: "", mode: "", poisoned: false, staged: Map() }
    val changes = diff(state.committed, state.staged)
    if (op == "txn_abort") {
      val label = if (changes.size() > 0) "rolled_back" else if (state.mode == "write") "discarded" else "ok"
      success(closed, label)
    } else if (state.poisoned) predict(closed, "invalid_state", "", 0, "poisoned")
    else {
      val moved = changes.exists(row => row.kind == "modified")
      val added = changes.exists(row => row.kind == "added")
      val label = if (moved and added) "published" else if (moved) "moved" else "ok"
      success({ ...closed, committed: state.staged }, label)
    }
  }

  pure def txnCall(state: State, op: str, args: List[str]): Prediction =
    if (state.txn == "" or state.txn != args[0]) unsupported(state)
    else if (op == "txn_commit" or op == "txn_abort") finishTxn(state, op)
    else if (op == "txn_put_datum") store(state, "datum", args[1], args[2])
    else if (op == "txn_put_object") store(state, args[1], args[2], args[3])
    else if (op == "txn_ref_create" or op == "txn_ref_update")
      editRef(state, op, refKeys.get(args[1]), state.ids.get(args[2]))
    else if (op == "txn_ref_get") {
      val id = lookup(state.staged, refKeys.get(args[1]))
      val label = if (state.mode == "write") "read_for_write" else "read"
      if (id == "") predict(state, "not_found", "", 0, "missing_ref")
      else predict({ ...state, ids: state.ids.put(args[2], id) }, "ok", id, 0, label)
    } else if (op == "txn_get_object") {
      val record = byId.get(state.ids.get(args[2]))
      if (record.kind != args[1] or not(state.staged.keys().contains(record.key))) unsupported(state)
      else predict({ ...state, buffers: state.buffers.put(args[3], record.packed) }, "ok", record.packed, 0, "ok")
    } else unsupported(state)

  pure def transition(state: State, op: str, args: List[str]): Prediction =
    if (op == "repo_open") {
      if (state.repo != "") unsupported(state)
      else if (args[1] == "create" and state.committed == Map())
        success({ ...state, repo: args[0], committed: Map(schemaKey -> schema) }, "ok")
      else if (args[1] == "existing" and state.committed.keys().contains(schemaKey))
        success({ ...state, repo: args[0] }, "reopened")
      else unsupported(state)
    } else if (op == "repo_close") {
      if (state.repo == args[0] and state.txn == "") success({ ...state, repo: "" }, "ok")
      else unsupported(state)
    } else if (op == "txn_begin") {
      if (state.repo != "" and state.repo == args[0] and state.txn == "" and Set("read", "write").contains(args[1]))
        success({ ...state, txn: args[2], mode: args[1], staged: state.committed }, "ok")
      else unsupported(state)
    } else if (Set("datum_encode", "object_encode").contains(op)) encodeRecord(state, op, args)
    else if (op == "object_decode") {
      val record = byPacked.get(state.buffers.get(args[0]))
      if (record.kind != "commit") unsupported(state)
      else predict({ ...state, views: state.views.put(args[1], record.packed) },
        "ok", record.deps.head(), record.deps.length() - 1, "decoded")
    } else if (op == "object_view_parent") {
      val record = byPacked.get(state.views.get(args[0]))
      if (args[1] != "0" or record.deps.length() != 2) unsupported(state)
      else predict({ ...state, ids: state.ids.put(args[2], record.deps[1]) }, "ok", record.deps[1], 0, "parent")
    } else txnCall(state, op, args)

  pure def stepVerdict(previous: State, predicted: Prediction, attempt: Attempt): str = {
    val expected = diff(previous.committed, predicted.state.committed)
    val changes = attempt.changes.foldl(Set(), (out, row) => out.union(Set(row)))
    if (predicted.label == "unsupported_request") predicted.label
    else if (attempt.status != predicted.status) "status"
    else if (attempt.value != predicted.value or attempt.count != predicted.count or attempt.items != List()) "value"
    else if (attempt.otherChanges != List() or changes != expected or attempt.changes.length() != expected.size()) "inventory"
    else predicted.label
  }

  // Neither aliases nor inventory in the expected state are seeded by observations.
  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ state: initial, verdicts: List() }, (out, attempt) => {
      val predicted = transition(out.state, attempt.op, attempt.args)
      { state: predicted.state, verdicts: out.verdicts.append(stepVerdict(out.state, predicted, attempt)) }
    }).verdicts

  pure def verdictAccepted(verdict: str): bool = Set(
    "ok", "reopened", "created", "duplicate_same", "duplicate_different", "updated", "missing_update",
    "missing_ref", "read", "read_for_write", "rolled_back", "discarded", "poisoned", "published", "moved",
    "staged_tree", "staged_commit", "decoded", "parent"
  ).contains(verdict)

  pure val rootReadback = List("reopened", "read", "decoded")
  pure val childReadback = rootReadback.append("parent")
  pure val stage = List("staged_tree", "staged_commit", "updated")
  pure val publish = stage.append("published").concat(childReadback)
  pure val contenderPattern = List("created", "read", "read", "read_for_write", "updated", "moved",
    "read_for_write", "discarded").concat(childReadback)
  pure val required = Set(
    List("created").concat(rootReadback),
    List("created", "duplicate_same", "poisoned").concat(rootReadback),
    List("created", "duplicate_different", "poisoned").concat(rootReadback),
    List("created").concat(publish),
    List("created").concat(stage).append("rolled_back").concat(childReadback).concat(publish),
    List("created").concat(stage).concat(List("missing_update", "poisoned")).concat(childReadback).concat(publish),
    List("created", "created", "duplicate_different", "poisoned").concat(publish).concat(childReadback)
  )

  pure val contenders = Map("B" -> b.id, "C" -> c.id)

  pure def coversContenders(observed: Observation, pattern: List[str], first: str, second: str): bool = {
    val reads = observed.attempts.select(attempt => attempt.op == "txn_ref_get" and attempt.args[1] == "main")
    val updates = observed.attempts.select(attempt => attempt.op == "txn_ref_update")
    val winner = contenders.get(first)
    if (pattern != contenderPattern or reads.length() != 5 or updates.length() != 1) false
    else all {
      reads[0].args[0] == first and reads[2].args[0] == first,
      reads[1].args[0] == second and reads[3].args[0] == second,
      updates[0].args == List(first, "main", first),
      reads[0].value == a.id and reads[1].value == a.id,
      reads[2].value == reads[0].value, // first captured tip still current: update and commit
      reads[3].value != reads[1].value, // second captured tip stale: abort without updating
      reads[3].value == winner and reads[4].value == winner
    }
  }

  // Qualify readback coverage only if the get/decode/parent operands derive from
  // the reopened ref, not from pre-existing aliases for the expected objects.
  pure def linkedReadbacks(attempts: List[Attempt]): bool = attempts.indices().forall(i => {
    val attempt = attempts[i]
    if (attempt.op == "object_decode") {
      if (i < 4) false
      else {
        val reopened = attempts[i - 4]
        val began = attempts[i - 3]
        val tip = attempts[i - 2]
        val fetched = attempts[i - 1]
        all {
          reopened.op == "repo_open" and reopened.args[1] == "existing",
          began.op == "txn_begin" and began.args[1] == "read",
          tip.op == "txn_ref_get" and tip.args[0] == began.args[2],
          fetched.op == "txn_get_object" and fetched.args == List(tip.args[0], "commit", tip.args[2], attempt.args[0])
        }
      }
    } else if (attempt.op == "object_view_parent") {
      if (i == 0) false
      else attempts[i - 1].op == "object_decode" and attempts[i - 1].args[1] == attempt.args[0]
    } else true
  })

  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool = {
    val patterns = verdicts.foldl(List(), (out, row) => out.append(row.select(label => label != "ok")))
    val rows = evidence.indices()
    required.subseteq(rows.map(i => patterns[i]))
      and rows.forall(i => linkedReadbacks(evidence[i].attempts))
      and rows.exists(i => coversContenders(evidence[i], patterns[i], "B", "C"))
      and rows.exists(i => coversContenders(evidence[i], patterns[i], "C", "B"))
  }

  pure val mainKey = refKeys.get("main")
  pure val modelBefore = { ...initial, txn: "publish", mode: "write", committed: Map(mainKey -> b.id),
    staged: Map(mainKey -> fromB.id, snapshotTree.key -> snapshotTree.packed, fromB.key -> fromB.packed) }
  pure val publishCommit: Attempt = {
    op: "txn_commit", args: List("publish"), status: "ok", value: "", count: 0,
    items: List(), otherChanges: List(), changes: List(
      { kind: "modified", key: mainKey, before: b.id, after: fromB.id },
      { kind: "added", key: snapshotTree.key, before: "", after: snapshotTree.packed },
      { kind: "added", key: fromB.key, before: "", after: fromB.packed }
    )
  }
  pure def checkControl(before: State, attempt: Attempt): str =
    stepVerdict(before, transition(before, attempt.op, attempt.args), attempt)

  pure val controlsPass = all {
    checkControl(modelBefore, publishCommit) == "published",
    checkControl(modelBefore, { ...publishCommit, changes: publishCommit.changes.slice(0, 1) }) == "inventory",
    checkControl(modelBefore, { ...publishCommit, changes: publishCommit.changes.append(publishCommit.changes[0]) })
      == "inventory",
    checkControl(modelBefore, { ...publishCommit, op: "txn_abort", changes: List() }) == "rolled_back",
    checkControl(modelBefore, { ...publishCommit, op: "txn_abort" }) == "inventory",
    checkControl({ ...modelBefore, poisoned: true }, { ...publishCommit, changes: List() }) == "status",
    checkControl({ ...modelBefore, poisoned: true }, { ...publishCommit, status: "invalid_state" }) == "inventory",
    checkControl({ ...modelBefore, buffers: Map("packed" -> fromB.packed) },
      { ...publishCommit, op: "object_decode", args: List("packed", "view"),
        value: snapshotTree.id, count: 0, changes: List() }) == "value",
    checkControl(modelBefore, { ...publishCommit, op: "txn_ref_get", args: List("publish", "main", "actual"),
      value: b.id, changes: List() }) == "value"
  }
}
