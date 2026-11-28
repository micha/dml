module transfer_histories {
  import transfer_fixture.* from "./transfer_fixture"

  type Request = { op: str, args: List[str] }
  pure def call(op: str, args: List[str]): Request = { op: op, args: args }
  pure def open(repo: str, mode: str): Request = call("repo_open", List(repo, mode))
  pure def close(repo: str): Request = call("repo_close", List(repo))
  pure def reopen(repo: str): List[Request] = List(close(repo), open(repo, "existing"))
  pure def begin(repo: str, mode: str, txn: str): Request = call("txn_begin", List(repo, mode, txn))
  pure def commit(txn: str): Request = call("txn_commit", List(txn))
  pure def abort(txn: str): Request = call("txn_abort", List(txn))
  pure def edit(op: str, txn: str, ref: str, id: str): Request = call(op, List(txn, ref, id))
  pure def create(txn: str, ref: str, id: str): Request = edit("txn_ref_create", txn, ref, id)
  pure def update(txn: str, ref: str, id: str): Request = edit("txn_ref_update", txn, ref, id)
  pure def release(txn: str, ref: str, id: str): Request = edit("txn_ref_delete_expected", txn, ref, id)
  pure def read(txn: str, ref: str, id: str): Request = call("txn_ref_get", List(txn, ref, id))
  pure def exportBundle(repo: str, id: str, alias: str): Request = call("repo_export_commit", List(repo, id, alias))
  pure def importBundle(repo: str, bundle: str, id: str): Request = call("repo_import_commit", List(repo, bundle, id))
  pure def fetch(txn: str, kind: str, id: str, packed: str): Request =
    call("txn_get_object", List(txn, kind, id, packed))
  pure def decode(packed: str, view: str): Request = call("object_decode", List(packed, view))
  pure def parent(view: str, index: str, id: str): Request = call("object_view_parent", List(view, index, id))
  pure def entry(view: str, index: str, id: str): Request = call("object_view_entry", List(view, index, id))

  pure def store(txn: str, names: List[str]): List[Request] = names.foldl(List(), (out, name) => {
    val row = byName.get(name)
    out.append(if (row.kind == "datum") call("txn_put_datum", List(txn, row.packed, name))
      else call("txn_put_object", List(txn, row.kind, row.packed, name)))
  })

  pure val seedSource = List(open("source", "create"), begin("source", "write", "seed"))
    .concat(store("seed", source.concat(sourceDetached)))
    .concat(List(create("seed", "main", "other"), create("seed", "pinned", "root"), commit("seed")))
  pure val seedDest = List(open("dest", "create"), begin("dest", "write", "seed"))
    .concat(store("seed", destination)).concat(List(create("seed", "main", "keep"), commit("seed")))
  pure val seedBoth = seedSource.concat(seedDest)
  pure val finish = List(close("source"), close("dest"))
  pure val outbound = List(exportBundle("source", "root", "exported"), importBundle("dest", "exported", "imported"))
  pure val stage = List(begin("dest", "write", "stage"), create("stage", "incoming", "imported"), commit("stage"))

  pure def decodeCommit(txn: str, id: str, view: str): List[Request] = List(
    fetch(txn, "commit", id, "commitPacked"), decode("commitPacked", view))
  pure def treePath(txn: str, view: str): List[Request] = List(
    fetch(txn, "tree", view, "treePacked"), decode("treePacked", "treeView"), entry("treeView", "0", "pathDag"))
  pure def datumPath(txn: str, binding: str): List[Request] = List(
    call("txn_lookup_node", List(txn, "pathDag", binding, "pathNode")),
    fetch(txn, "node", "pathNode", "pathNodePacked"), decode("pathNodePacked", "literalView"),
    call("txn_get_datum", List(txn, "literalView", "valuePacked")), call("datum_decode", List("valuePacked")))
  pure def inputPath(txn: str, id: str): List[Request] = decodeCommit(txn, id, "inputView")
    .concat(treePath(txn, "inputView")).concat(datumPath(txn, "z-bound"))
  pure def snapshot(ref: str, readParents: bool): List[Request] = reopen("dest")
    .concat(List(begin("dest", "read", "snapshot"), read("snapshot", ref, "tip")))
    .concat(if (readParents) inputPath("snapshot", "tip")
      .concat(List(parent("inputView", "0", "firstParent"), parent("inputView", "1", "secondParent")))
      .concat(inputPath("snapshot", "firstParent")).concat(decodeCommit("snapshot", "secondParent", "secondView"))
      else decodeCommit("snapshot", "tip", "inputView").concat(treePath("snapshot", "inputView"))
        .append(call("txn_lookup_node", List("snapshot", "pathDag", "z-bound", "absentNode"))))
    .append(abort("snapshot"))
  pure def inspectLineage(repo: str, ref: str, id: str): List[Request] = reopen(repo)
    .append(begin(repo, "read", "lineage"))
    .concat(if (ref == "") List() else List(read("lineage", ref, id)))
    .concat(decodeCommit("lineage", id, "resultView"))
    .append(parent("resultView", "0", "lineageInput"))
    .concat(inputPath("lineage", "lineageInput"))
    .concat(treePath("lineage", "resultView")).concat(datumPath("lineage", "output"))
    .concat(datumPath("lineage", "implementation")).append(abort("lineage"))
  pure def writeLineage(names: List[str], target: str): List[Request] = List(begin("dest", "write", "result"))
    .concat(store("result", names)).append(create("result", "result-pin", target)).append(commit("result"))
  pure def integrity(repo: str): List[Request] = List(begin(repo, "read", "integrity"),
    call("txn_check_integrity", List("integrity")), abort("integrity"))

  pure val beforeReturn = integrity("dest").concat(stage).concat(integrity("dest"))
    .concat(snapshot("incoming", true))
    .concat(writeLineage(lineageOne, "resultA")).concat(inspectLineage("dest", "result-pin", "pinnedResult"))
    .concat(writeLineage(lineageTwo, "resultB")).concat(inspectLineage("dest", "result-pin", "pinnedResult"))
    .concat(List(begin("source", "read", "capture"), read("capture", "main", "originalMain"), abort("capture"),
      exportBundle("dest", "pinnedResult", "returnedBundle"), importBundle("source", "returnedBundle", "returned"),
      importBundle("source", "returnedBundle", "returnedAgain")))
  pure val returnResult = inspectLineage("source", "", "returned").concat(List(
    begin("source", "write", "stale"), read("stale", "main", "staleActual"), abort("stale"),
    begin("source", "write", "publish"), read("publish", "main", "publishActual"),
    update("publish", "main", "returned"), commit("publish")))
    .concat(inspectLineage("source", "main", "publishedResult"))
    .concat(List(begin("source", "read", "noPin"), read("noPin", "result-pin", "noPin"), abort("noPin")))
  pure val releaseStaging = List(
    begin("dest", "write", "release"), release("release", "incoming", "keep"), commit("release"),
    begin("dest", "write", "release"), release("release", "incoming", "imported"), abort("release"),
    begin("dest", "read", "stillStaged"), read("stillStaged", "incoming", "stillStaged"), abort("stillStaged"),
    begin("dest", "write", "release"), release("release", "incoming", "imported"), commit("release"),
    begin("dest", "write", "release"), release("release", "incoming", "imported"), commit("release"),
    begin("dest", "read", "noStage"), read("noStage", "incoming", "noStage"), abort("noStage"))
    .concat(inspectLineage("dest", "result-pin", "releasedResult"))
    .concat(inspectLineage("source", "main", "publishedResult"))
    .concat(integrity("dest")).concat(integrity("source"))

  pure val alternative = variants.select(v => v.name == "alternative").head().packed
  pure val badVariants = variants.select(v => v.status != "ok")
  pure val minimal = variants.select(v => v.name == "valid").head().packed

  var histories: List[List[Request]]
  action init = histories' = List(
    seedBoth.concat(outbound).concat(List(exportBundle("dest", "imported", "reexported"),
      exportBundle("source", "root", "repeated"), importBundle("dest", alternative, "alternative"),
      importBundle("dest", variants.select(v => v.name == "thin").head().packed, "thinOverExisting"))).concat(finish),
    seedBoth.concat(List(importBundle("dest", alternative, "alternative"),
      exportBundle("dest", "alternative", "altExport"), exportBundle("source", "root", "firstExport"))).concat(finish),
    seedBoth.concat(outbound).concat(snapshot("main", false))
      .concat(List(begin("dest", "read", "absent"), read("absent", "incoming", "absent"), abort("absent")))
      .concat(stage).concat(snapshot("incoming", true)).concat(snapshot("main", false))
      .concat(List(begin("dest", "write", "publish"), update("publish", "main", "imported"), commit("publish")))
      .concat(snapshot("main", true)).concat(finish),
    seedBoth.concat(outbound).concat(beforeReturn).concat(returnResult).concat(releaseStaging).concat(finish),
    seedDest.concat(List(begin("dest", "read", "busy"), importBundle("dest", minimal, "busyId"),
      exportBundle("dest", "keep", "busyBundle"), abort("busy"),
      exportBundle("dest", "ffffffffffffffffffffffffffffffff", "missingBundle")))
      .concat(badVariants.foldl(List(), (out, fixture) => out.append(importBundle("dest", fixture.packed, fixture.name))))
      .concat(List(importBundle("dest", minimal, "minimal"), importBundle("dest", minimal, "minimalAgain"), close("dest")))
  )
  action step = histories' = histories
}
