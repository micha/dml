module retention_histories {
  type Request = { op: str, args: List[str] }

  pure def request(op: str, args: List[str]): Request = { op: op, args: args }
  pure def open(repo: str, mode: str): Request = request("repo_open", List(repo, mode))
  pure def close(repo: str): Request = request("repo_close", List(repo))
  pure def begin(repo: str, mode: str, txn: str): Request = request("txn_begin", List(repo, mode, txn))
  pure def commit(txn: str): Request = request("txn_commit", List(txn))
  pure def abort(txn: str): Request = request("txn_abort", List(txn))
  pure def exportCommit(repo: str, id: str, bundle: str): Request =
    request("repo_export_commit", List(repo, id, bundle))
  pure def importCommit(repo: str, bundle: str, id: str): Request =
    request("repo_import_commit", List(repo, bundle, id))
  pure def stageCommit(repo: str, bundle: str, ref: str, id: str): Request =
    request("repo_import_commit_staged", List(repo, bundle, ref, id))
  pure def createRef(txn: str, name: str, id: str): Request = request("txn_ref_create", List(txn, name, id))
  pure def moveRef(txn: str, name: str, id: str): Request = request("txn_ref_update", List(txn, name, id))
  pure def dropRef(txn: str, name: str, id: str): Request = request("txn_ref_delete_expected", List(txn, name, id))
  pure def readRef(txn: str, name: str, id: str): Request = request("txn_ref_get", List(txn, name, id))
  pure def getCommit(txn: str, id: str, packed: str): Request = request("txn_get_object", List(txn, "commit", id, packed))
  pure def collect(txn: str): Request = request("txn_collect_garbage", List(txn))

  pure def object(txn: str, kind: str, inputs: List[str], id: str): List[Request] = List(
    request("object_encode", List(kind).concat(inputs).append(id)),
    request("txn_put_object", List(txn, kind, id, id))
  )

  pure def literal(txn: str, kind: str, value: str, datum: str, node: str): List[Request] = List(
    request("datum_encode", List(kind, value, datum)), request("txn_put_datum", List(txn, datum, datum))
  ).concat(object(txn, "node", List(datum), node))

  pure val base = literal("seed", "i64", "41", "baseDatum", "baseNode")
    .concat(object("seed", "dag", List("baseNode", "z-bound", "baseNode"), "baseDag"))
    .concat(object("seed", "tree", List("all", "baseDag"), "baseTree"))
    .concat(object("seed", "commit", List("baseTree"), "base"))

  pure val selected = literal("seed", "i64", "45", "selectedDatum", "selectedNode")
    .concat(object("seed", "dag", List("selectedNode", "z-bound", "selectedNode"), "selectedDag"))
    .concat(object("seed", "tree", List("all", "selectedDag"), "selectedTree"))
    .concat(object("seed", "commit", List("selectedTree", "base"), "selected"))

  // A detached application result extends selected. Its DAG reaches both the
  // output literal and a separate literal naming the implementation.
  pure val result = literal("seed", "i64", "46", "outputDatum", "outputNode")
    .concat(literal("seed", "string", "example.add-one@1", "implementationDatum", "implementationNode"))
    .concat(object("seed", "dag", List("outputNode", "implementation", "implementationNode", "output", "outputNode"),
                   "resultDag"))
    .concat(object("seed", "tree", List("lineage-v1", "resultDag"), "resultTree"))
    .concat(object("seed", "commit", List("resultTree", "selected"), "result"))

  pure val seedWorker = List(open("worker", "create"), begin("worker", "write", "seed"))
    .concat(base).concat(selected).concat(result).append(commit("seed"))

  pure val seedMain = List(open("origin", "create"), begin("origin", "write", "seed"))
    .concat(literal("seed", "i64", "777", "keepDatum", "keepNode"))
    .concat(object("seed", "dag", List("keepNode"), "keepDag"))
    .concat(object("seed", "tree", List("single", "keepDag"), "keepTree"))
    .concat(object("seed", "commit", List("keepTree"), "keep"))
    .concat(List(createRef("seed", "main", "keep"), commit("seed")))

  pure val collectOrigin = List(begin("origin", "write", "sweep"), collect("sweep"), commit("sweep"))
}
