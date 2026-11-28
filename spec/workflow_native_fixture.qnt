module workflow_native_fixture {
  import recorded_calls_fixtures as core from "./recorded_calls_fixtures"

  pure def step(op: str, args: List[str]): core::Request = { op: "native", args: List(op).concat(args) }
  pure def wrap(r: core::Request): core::Request = step(r.op, r.args)
  pure def wrapList(requests: List[core::Request]): List[core::Request] =
    requests.foldl(List(), (out, r) => out.append(wrap(r)))
  pure def open(mode: str): List[core::Request] = wrapList(core::openNative(mode))
  pure def close(end: str): List[core::Request] = wrapList(core::closeNative(end))
  pure def readRef(ref: str, id: str): core::Request = wrap(core::refRead(ref, id))
  pure def pin(ref: str, id: str): core::Request = wrap(core::pin(ref, id))
  pure def putObject(kind: str, operands: List[str], id: str): List[core::Request] =
    wrapList(core::putObject(kind, operands, id))
  pure def literal(kind: str, value: str, node: str): List[core::Request] =
    wrapList(core::putLiteral(kind, value, "literal-datum", node))
  pure def link(dag: str, id: str): List[core::Request] = putObject("node", List("subdag", dag), id)
  pure def view(kind: str, id: str, alias: str): List[core::Request] = wrapList(core::viewObject(kind, id, alias))
  pure def parent(view: str, index: str, id: str): core::Request = step("object_view_parent", List(view, index, id))
  pure def snapshot(commit: str, commitView: str, dag: str): List[core::Request] =
    wrapList(core::snapshotAt(commit, commitView, "tree-view", dag, ""))
  pure def publish(role: str, dag: str, parents: List[str], id: str): List[core::Request] =
    putObject("tree", List(role, dag), "publication-tree")
      .concat(putObject("commit", List("publication-tree").concat(parents), id))
  pure def lookup(dag: str, binding: str, node: str): core::Request = wrap(core::lookupNode(dag, binding, node))
  pure def targetVia(dag: str, binding: str, node: str, alias: str): List[core::Request] =
    List(lookup(dag, binding, node)).concat(view("node", node, alias))
  pure def target(dag: str, binding: str, alias: str): List[core::Request] =
    targetVia(dag, binding, "target-node", alias)
  pure def readDatum(id: str, alias: str): List[core::Request] = List(
    step("txn_get_datum", List("snapshot", id, alias)), step("datum_decode", List(alias)))

  // Copy known bindings from a real record, replacing one named binding.
  pure def patchDag(before: str, root: str, names: List[str], replaced: str, replacement: str,
      after: str): List[core::Request] = {
    // Names are scratch node aliases for the duration of this edit.
    pure def node(name: str): str = if (name == replaced) replacement else name
    val reads = names.foldl(List(), (out, name) =>
      if (name == replaced) out else out.append(lookup(before, name, node(name))))
    val encoded = names.foldl(List(node(root)), (out, name) => out.append(name).append(node(name)))
    reads.concat(putObject("dag", encoded, after))
  }

  // Locate the observation for a named result (the final operand of each of these calls).
  pure def outputIndex(requests: List[core::Request], op: str, alias: str): int =
    requests.indices().fold(-1, (found, i) => {
      val args = requests[i].args
      if (requests[i].op == "native" and args[0] == op and args[args.length() - 1] == alias) i else found
    })
}
