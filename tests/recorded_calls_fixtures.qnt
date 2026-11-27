module recorded_calls_fixtures {
  type Request = { op: str, args: List[str] }
  pure def coreRequest(op: str, args: List[str]): Request = { op: op, args: args }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure def worker(op: str, args: List[str]): Request = { op: op, args: List("worker").concat(args) }

  // Native aliases persist between calls but no handles cross a CLI invocation.
  pure def openRepo(role: str, create: str, mode: str): List[Request] = List(
    coreRequest("repo_open", List(role, create)), coreRequest("txn_begin", List(role, mode, "snapshot"))
  )
  pure def closeRepo(role: str, end: str): List[Request] = List(
    coreRequest(end, List("snapshot")), coreRequest("repo_close", List(role))
  )
  pure def openNative(mode: str): List[Request] = openRepo("source", "existing", mode)
  pure def closeNative(end: str): List[Request] = closeRepo("source", end)
  pure def refRead(ref: str, id: str): Request = coreRequest("txn_ref_get", List("snapshot", ref, id))
  pure def viewObject(kind: str, id: str, view: str): List[Request] = List(
    coreRequest("txn_get_object", List("snapshot", kind, id, view)), coreRequest("object_decode", List(view, view))
  )
  pure def snapshotAt(commit: str, view: str, tree: str, dag: str, parent: str): List[Request] =
    viewObject("commit", commit, view).concat(viewObject("tree", view, tree))
      .append(coreRequest("object_view_entry", List(tree, "0", dag)))
      .concat(if (parent != "") List(coreRequest("object_view_parent", List(view, "0", parent))) else List())
  pure def commitAt(commit: str, path: (str, str, str, str)): List[Request] =
    snapshotAt(commit, path._1, path._2, path._3, path._4)
  pure def lookupNode(dag: str, binding: str, node: str): Request =
    coreRequest("txn_lookup_node", List("snapshot", dag, binding, node))
  pure def encodeNode(kind: str, target: str): Request = coreRequest("object_encode", List("node", kind, target, "encoded-node"))
  pure def viewSubdag(dag: str, input: str, producer: str): List[Request] =
    List(lookupNode(dag, "input", input)).concat(viewObject("node", input, producer)).append(encodeNode("subdag", producer))
  pure def viewLiteral(node: str, target: str): List[Request] =
    viewObject("node", node, target).append(encodeNode("literal", target))
      .append(coreRequest("txn_get_datum", List("snapshot", target, target))).append(coreRequest("datum_decode", List(target)))

  pure def putObject(kind: str, operands: List[str], id: str): List[Request] = List(
    coreRequest("object_encode", List(kind).concat(operands).append(id)),
    coreRequest("txn_put_object", List("snapshot", kind, id, id))
  )
  pure def putLiteral(kind: str, value: str, datum: str, node: str): List[Request] = List(
    coreRequest("datum_encode", List(kind, value, datum)),
    coreRequest("txn_put_datum", List("snapshot", datum, datum))
  ).concat(putObject("node", List("literal", datum), node))
  pure def pin(ref: str, id: str): Request = coreRequest("txn_ref_create", List("snapshot", ref, id))
  pure def drop(ref: str, id: str): Request = coreRequest("txn_ref_delete_expected", List("snapshot", ref, id))

  // Deliberate non-arithmetic evidence: the producer stores -17, not 2 + 3.
  pure def sumGraph(implementation: str): List[Request] =
    putLiteral("string", implementation, "stored-sum-implementation-datum", "stored-sum-implementation")
      .concat(putLiteral("i64", "2", "stored-a-datum", "stored-a"))
      .concat(putLiteral("i64", "3", "stored-b-datum", "stored-b"))
      .concat(putLiteral("i64", "-17", "stored-sum-root-datum", "stored-sum-root"))
      .concat(putObject("dag", List("stored-sum-root", "implementation", "stored-sum-implementation",
         "a", "stored-a", "b", "stored-b"), "stored-sum-dag"))
  pure def storedSum(role: str, ref: str, implementation: str): List[Request] =
    openRepo(role, "create", "write").concat(sumGraph(implementation))
      .concat(putObject("tree", List("recorded-sum-v1", "stored-sum-dag"), "stored-sum-tree"))
      .concat(putObject("commit", List("stored-sum-tree"), "stored-sum-commit"))
      .append(pin(ref, "stored-sum-commit")).concat(closeRepo(role, "txn_commit"))
}
