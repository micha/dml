module ref_histories {
  type Request = { op: str, args: List[str] }

  pure def request(op: str, args: List[str]): Request = { op: op, args: args }
  pure def open(mode: str): Request = request("repo_open", List("repo", mode))
  pure val close = request("repo_close", List("repo"))
  pure def begin(mode: str, txn: str): Request = request("txn_begin", List("repo", mode, txn))
  pure def commit(txn: str): Request = request("txn_commit", List(txn))
  pure def abort(txn: str): Request = request("txn_abort", List(txn))
  pure def encode(args: List[str]): Request = request("object_encode", args)
  pure def storeObject(txn: str, kind: str, packed: str, id: str): Request =
    request("txn_put_object", List(txn, kind, packed, id))
  pure def create(txn: str, name: str, id: str): Request = request("txn_ref_create", List(txn, name, id))
  pure def update(txn: str, name: str, id: str): Request = request("txn_ref_update", List(txn, name, id))
  pure def readRef(txn: str, name: str, id: str): Request = request("txn_ref_get", List(txn, name, id))

  // The initially unreferenced siblings B and C share parent A, but not its tree in C's case.
  pure val fixture = List(
    open("create"), begin("write", "seed"),
    request("datum_encode", List("i64", "42", "datum")),
    request("txn_put_datum", List("seed", "datum", "literal")),
    encode(List("node", "literal", "node")), storeObject("seed", "node", "node", "root"),
    encode(List("dag", "root", "dag")), storeObject("seed", "dag", "dag", "graph"),
    encode(List("tree", "empty")), storeObject("seed", "tree", "empty", "emptyTree"),
    encode(List("commit", "emptyTree", "rootCommit")), storeObject("seed", "commit", "rootCommit", "A"),
    encode(List("commit", "emptyTree", "A", "siblingB")), storeObject("seed", "commit", "siblingB", "B"),
    encode(List("tree", "candidate", "graph", "candidate")),
    storeObject("seed", "tree", "candidate", "candidateTree"),
    encode(List("commit", "candidateTree", "A", "siblingC")), storeObject("seed", "commit", "siblingC", "C"),
    commit("seed")
  )

  pure def createRef(name: str, id: str): List[Request] =
    List(begin("write", "create"), create("create", name, id), commit("create"))

  pure def readback(name: str, hasParent: bool): List[Request] = List(
    close, open("existing"), begin("read", "readback"), readRef("readback", name, "tip"),
    request("txn_get_object", List("readback", "commit", "tip", "commitRecord")),
    request("object_decode", List("commitRecord", "commitView"))
  ).concat(if (hasParent) List(request("object_view_parent", List("commitView", "0", "parent"))) else List())
   .append(abort("readback"))

  pure def publish(name: str, parent: str, finish: str): List[Request] = List(
    begin("write", "publish"),
    encode(List("tree", "snapshot", "graph", "snapshot")),
    storeObject("publish", "tree", "snapshot", "snapshotTree"),
    encode(List("commit", "snapshotTree", parent, "snapshotCommit")),
    storeObject("publish", "commit", "snapshotCommit", "snapshotTip"),
    update("publish", name, "snapshotTip")
  ).concat(if (finish == "poison") List(update("publish", "missing", "snapshotTip")) else List())
   .append(if (finish == "abort") abort("publish") else commit("publish"))
   .concat(readback(name, true))

  pure val createA = createRef("main", "A")
  pure val createB = createRef("main", "B")
  pure val publishMain = publish("main", "B", "commit")

  // Both callers capture the starting tip before either attempts publication. Each
  // then reads the tip again in the same write transaction used to update or abort.
  // The callers' transaction aliases name their intended targets. These paths
  // attempt both orderings; the rules judge the actual comparisons.
  pure def contenders(first: str, second: str): List[Request] = createA.concat(List(
    begin("read", first), readRef(first, "main", "firstExpected"), abort(first),
    begin("read", second), readRef(second, "main", "secondExpected"), abort(second),
    begin("write", first), readRef(first, "main", "firstActual"),
    update(first, "main", first), commit(first),
    begin("write", second), readRef(second, "main", "secondActual"), abort(second)
  )).concat(readback("main", true))

  pure def withFixture(steps: List[Request]): List[Request] = fixture.concat(steps).append(close)

  var histories: List[List[Request]]

  action init = histories' = List(
    withFixture(createA.concat(readback("main", false))),
    withFixture(createA.concat(createA).concat(readback("main", false))),
    withFixture(createA.concat(createB).concat(readback("main", false))),
    withFixture(createB.concat(publishMain)),
    withFixture(createB.concat(publish("main", "B", "abort")).concat(publishMain)),
    withFixture(createB.concat(publish("main", "B", "poison")).concat(publishMain)),
    withFixture(contenders("B", "C")),
    withFixture(contenders("C", "B"))
  )

  action changedInit = histories' = List(withFixture(
    createRef("candidate-1", "B")
      .concat(createRef("other", "A"))
      .concat(createRef("candidate-1", "A"))
      .concat(publish("other", "A", "commit"))
      .concat(readback("candidate-1", true))
  ))

  action step = histories' = histories
}
