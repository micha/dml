module builtin_primitive_fixture {
  type Request = { op: str, args: List[str] }
  pure def req(op: str, args: List[str]): Request = { op: op, args: args }
  pure def native(op: str, args: List[str]): Request = req("native", List(op).concat(args))
  pure val writer = List(native("repo_open", List("source", "create")),
    native("txn_begin", List("source", "write", "snapshot")))
  pure val reader = List(native("repo_open", List("source", "existing")),
    native("txn_begin", List("source", "read", "snapshot")))
  pure def close(end: str): List[Request] = List(native(end, List("snapshot")), native("repo_close", List("source")))
  pure def inspect(method: str, dag: str): Request = req("inspect", List("snapshot", method, dag))
  pure def binding(uri: str, id: str): Request = req("binding_put", List("snapshot", uri, id))
  pure def putDatum(kind: str, operands: List[str], id: str): List[Request] = List(
    native("datum_encode", List(kind).concat(operands).append(id)),
    native("txn_put_datum", List("snapshot", id, id)))
  pure def putObject(kind: str, operands: List[str], id: str): List[Request] = List(
    native("object_encode", List(kind).concat(operands).append(id)),
    native("txn_put_object", List("snapshot", kind, id, id)))
  pure def literal(kind: str, operands: List[str], node: str): List[Request] =
    putDatum(kind, operands, "literal-datum").concat(putObject("node", List("literal", "literal-datum"), node))
  pure def lookup(dag: str, name: str, alias: str): Request = native("txn_lookup_node", List("snapshot", dag, name, alias))
  // Packed expected sub-DAG node vs the node actually stored at the named field.
  pure def edge(dag: str, name: str, target: str): List[Request] = List(
    lookup(dag, name, "edge-node"),
    native("txn_get_object", List("snapshot", "node", "edge-node", "actual-edge")),
    native("object_encode", List("node", "subdag", target, "expected-edge")))
  pure def replaceValue(dag: str, otherFields: List[str], replacement: str, result: str): List[Request] = {
    val reads = otherFields.foldl(List(), (out, name) => out.append(lookup(dag, name, name)))
    val bindings = otherFields.foldl(List(replacement, "value", replacement), (out, name) =>
      out.append(name).append(name))
    reads.concat(putObject("dag", bindings, result))
  }
}
